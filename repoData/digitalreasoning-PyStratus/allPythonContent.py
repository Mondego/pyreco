__FILENAME__ = cluster
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Classes for controlling a cluster of cloud instances.
"""

from __future__ import with_statement

import gzip
import StringIO
import urllib
import providers

from cloud.storage import Storage

CLUSTER_PROVIDER_MAP = {}

def _build_provider_map() :
    from pkgutil import iter_modules
    it = iter_modules(providers.__path__, 'providers.')
    for module in it :
        try :
            provider = __import__(module[1], globals(), locals(), ['CLOUD_PROVIDER']).CLOUD_PROVIDER
        except :
            pass
        else :
            CLUSTER_PROVIDER_MAP[provider[0]] = provider[1]

def get_cluster(provider):
  """
  Retrieve the Cluster class for a provider.
  """
  if not len(CLUSTER_PROVIDER_MAP):
    _build_provider_map()
  mod_name, driver_name = CLUSTER_PROVIDER_MAP[provider]
  _mod = __import__(mod_name, globals(), locals(), [driver_name])
  return getattr(_mod, driver_name)

class Cluster(object):
  """
  A cluster of server instances. A cluster has a unique name.
  One may launch instances which run in a certain role.
  """

  def __init__(self, name, config_dir, region):
    self.name = name
    self.config_dir = config_dir
    self.region = region

  def get_provider_code(self):
    """
    The code that uniquely identifies the cloud provider.
    """
    raise Exception("Unimplemented")

  def authorize_role(self, role, from_port, to_port, cidr_ip):
    """
    Authorize access to machines in a given role from a given network.
    """
    pass

  def get_instances_in_role(self, role, state_filter=None):
    """
    Get all the instances in a role, filtered by state.

    @param role: the name of the role
    @param state_filter: the state that the instance should be in
    (e.g. "running"), or None for all states
    """
    raise Exception("Unimplemented")

  def print_status(self, roles=None, state_filter="running"):
    """
    Print the status of instances in the given roles, filtered by state.
    """
    pass

  def check_running(self, role, number):
    """
    Check that a certain number of instances in a role are running.
    """
    instances = self.get_instances_in_role(role, "running")
    if len(instances) != number:
      print "Expected %s instances in role %s, but was %s %s" % \
        (number, role, len(instances), instances)
      return False
    else:
      return instances

  def launch_instances(self, roles, number, image_id, size_id,
                       instance_user_data, **kwargs):
    """
    Launch instances (having the given roles) in the cluster.
    Returns a list of IDs for the instances started.
    """
    pass

  def wait_for_instances(self, instance_ids, timeout=600):
    """
    Wait for instances to start.
    Raise TimeoutException if the timeout is exceeded.
    """
    pass

  def terminate(self):
    """
    Terminate all instances in the cluster.
    """
    pass

  def delete(self):
    """
    Delete the cluster permanently. This operation is only permitted if no
    instances are running.
    """
    pass

  def get_storage(self):
    """
    Return the external storage for the cluster.
    """
    return Storage(self)

class InstanceUserData(object):
  """
  The data passed to an instance on start up.
  """

  def __init__(self, filename, replacements={}):
    self.filename = filename
    self.replacements = replacements

  def _read_file(self, filename):
    """
    Read the user data.
    """
    return urllib.urlopen(filename).read()

  def read(self):
    """
    Read the user data, making replacements.
    """
    contents = self._read_file(self.filename)
    for (match, replacement) in self.replacements.iteritems():
      if replacement == None:
        replacement = ''
      contents = contents.replace(match, replacement)
    return contents

  def read_as_gzip_stream(self):
    """
    Read and compress the data.
    """
    output = StringIO.StringIO()
    compressed = gzip.GzipFile(mode='wb', fileobj=output)
    compressed.write(self.read())
    compressed.close()
    return output.getvalue()

class Instance(object):
  """
  A server instance.
  """
  def __init__(self, id, role, public_ip, private_ip, launch_time, instance_type, zone):
    self.id = id
    self.role = role
    self.public_ip = public_ip
    self.private_ip = private_ip
    self.launch_time = launch_time
    self.instance_type = instance_type
    self.zone = zone 

class RoleSyntaxException(Exception):
  """
  Raised when a role name is invalid. Role names may consist of a sequence
  of alphanumeric characters and underscores. Dashes are not permitted in role
  names.
  """
  def __init__(self, message):
    super(RoleSyntaxException, self).__init__()
    self.message = message
  def __str__(self):
    return repr(self.message)

class TimeoutException(Exception):
  """
  Raised when a timeout is exceeded.
  """
  pass

class InstanceTerminatedException(Exception):
    """
    Raised when an instance that should start goes to a terminated state.
    """
    pass

########NEW FILE########
__FILENAME__ = decorators
import signal
from cloud.cluster import TimeoutException

def timeout(seconds_before_timeout):
    """
    Borrowed from http://www.saltycrane.com/blog/2010/04/using-python-timeout-decorator-uploading-s3/
    """
    def decorate(f):
        def handler(signum, frame):
            raise TimeoutException()
        def new_f(*args, **kwargs):
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds_before_timeout)
            try:
                result = f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old)
            signal.alarm(0)
            return result
        new_f.func_name = f.func_name
        return new_f
    return decorate


########NEW FILE########
__FILENAME__ = exception
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class VolumesStillInUseException(Exception):
    pass

class InvalidSpotConfigurationException(Exception):
    pass

########NEW FILE########
__FILENAME__ = plugin
import itertools
import os
import subprocess
import sys
import logging
import time

from optparse import OptionParser
from optparse import make_option
from yapsy.IPlugin import IPlugin
from prettytable import PrettyTable

from cloud.cluster import InstanceUserData
from cloud.util import xstr
from cloud.util import build_env_string
from cloud.exception import VolumesStillInUseException

from cloud import VERSION

CONFIG_DIR_OPTION = \
  make_option("--config-dir", metavar="CONFIG-DIR",
    help="The configuration directory.")

PROVIDER_OPTION = \
  make_option("--cloud-provider", metavar="PROVIDER",
    help="The cloud provider, e.g. 'ec2' for Amazon EC2.")

AVAILABILITY_ZONE_OPTION = \
  make_option("-z", "--availability-zone", metavar="ZONE",
    help="The availability zone to run the instances in.")

REGION_OPTION = \
  make_option("-r", "--region", metavar="REGION",
    help="The region run the instances in.")

FORCE_OPTION = \
  make_option("--force", metavar="FORCE", 
              action="store_true", default=False,
              help="Force the command without prompting.")

BASIC_OPTIONS = [
  CONFIG_DIR_OPTION,
  PROVIDER_OPTION,
  AVAILABILITY_ZONE_OPTION,
  REGION_OPTION,
]

class CLIPlugin(IPlugin):
    """
    """
    USAGE = None

    def __init__(self, service=None):
        self.service = service
        self.logger = logging #logging.getLogger(self.__class__.__name__)

    def print_help(self, exitCode=1):
        if self.USAGE is None:
            raise RuntimeError("USAGE has not been defined.")

        print self.USAGE
        sys.exit(exitCode)

    def parse_options(self, command, argv, option_list=[], expected_arguments=[],
                      unbounded_args=False):
        """
        Parse the arguments to command using the given option list.

        If unbounded_args is true then there must be at least as many extra arguments
        as specified by extra_arguments (the first argument is always CLUSTER).
        Otherwise there must be exactly the same number of arguments as
        extra_arguments.
        """

        usage = "%%prog CLUSTER [options] %s" % \
            (" ".join([command] + expected_arguments[:]),)

        parser = OptionParser(usage=usage, version="%%prog %s" % VERSION,
                            option_list=option_list)

        parser.disable_interspersed_args()
        (options, args) = parser.parse_args(argv)
        if unbounded_args:
            if len(args) < len(expected_arguments):
                parser.error("incorrect number of arguments")
        elif len(args) != len(expected_arguments):
            parser.error("incorrect number of arguments")

        return (vars(options), args)

    def _prompt(self, prompt):
        """
        Returns true if user responds "yes" to prompt.
        """
        return raw_input("%s [yes or no]: " % prompt).lower() == "yes"
    
    def execute_command(self, argv, options_dict):
        """
        Should be overridden by the subclass to handle
        command specific options.
        """
        raise RuntimeError("Not implemented.")

    def create_storage(self, argv, options_dict):
        raise RuntimeError("Not implemented.")

    def terminate_cluster(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, [FORCE_OPTION])

        if not self.service.get_instances():
            print "No running instances. Aborting."
            return

        if opt.get("force"):
            print "Terminating cluster..."
            self.service.terminate_cluster()
        else:
            self.print_instances()
            if not self._prompt("Terminate all instances?"):
                print "Not terminating cluster."
            else:
                print "Terminating cluster..."
                self.service.terminate_cluster()

    def simple_print_instances(self, argv, options_dict):
        opt, fields = self.parse_options(self._command_name, argv, expected_arguments=['FIELD*'], unbounded_args=True)

        for instance in self.service.get_instances():
            print("|".join([instance.__getattribute__(field) for field in fields]))

    def print_instances(self):
        if not self.service.get_instances():
            print "No running instances. Aborting."
            return

        table = PrettyTable()
        table.set_field_names(("Role", "Instance Id", "Image Id", 
                               "Public DNS", "Private DNS", "State", 
                               "Key", "Instance Type", "Launch Time", 
                               "Zone", "Region"))
        
        for i in self.service.get_instances():
            table.add_row((
                i.role, i.id, i.image_id, i.public_dns_name, 
                i.private_dns_name, i.state, i.key_name, i.instance_type,
                i.launch_time, i.placement, i.region.name))

        table.printt()

    def print_storage(self):
        storage = self.service.get_storage()
        
        table = PrettyTable()
        table.set_field_names(("Role", "Instance ID", "Volume Id", 
                               "Volume Size", "Snapshot Id", "Zone", 
                               "Status", "Device", "Create Time", 
                               "Attach Time"))

        for (r, v) in storage.get_volumes():
            table.add_row((r, v.attach_data.instance_id, v.id, 
                           str(v.size), v.snapshot_id, v.zone,
                           "%s / %s" % (v.status, v.attach_data.status), 
                           v.attach_data.device, str(v.create_time),
                           str(v.attach_data.attach_time)))
            
        if len(table.rows) > 0:
            s = 0
            for r in table.rows:
                s += int(r[3])

            table.printt()
            print "Total volumes: %d" % len(table.rows)
            print "Total size:    %d" % s
        else:
            print "No volumes defined."
    
    def delete_storage(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, [FORCE_OPTION])

        storage = self.service.get_storage()
        volumes = storage.get_volumes()

        if not volumes:
            print "No volumes defined."
            sys.exit()

        if opt.get('force'):
            print "Deleting storage..."
            try:
                storage.delete(storage.get_roles())
            except VolumesStillInUseException, e:
                print e.message
                sys.exit(1)
        else:
            self.print_storage()
            if not self._prompt("Delete all storage volumes? THIS WILL PERMANENTLY DELETE ALL DATA"):
                print "Not deleting storage."
            else:
                print "Deleting storage..."
                try:
                    storage.delete(storage.get_roles())
                except VolumesStillInUseException, e:
                    print e.message
                    sys.exit(1)

    def login(self, argv, options_dict):
        """
        """
        instances = self.service.get_instances()
        if not instances:
            print "No running instances. Aborting."
            return

        table = PrettyTable()
        table.set_field_names(("", "ROLE", "INSTANCE ID", "PUBLIC IP", "PRIVATE IP"))

        for instance in instances:
            table.add_row((len(table.rows)+1, 
                           instance.role,
                           instance.id, 
                           instance.public_dns_name, 
                           instance.private_dns_name))

        table.printt()

        while True:
            try:
                choice = raw_input("Instance to login to [Enter = quit]: ")
                if choice == "":
                    sys.exit(0)
                choice = int(choice)
                if choice > 0 and choice <= len(table.rows):
                    instance = instances[choice-1]
                    self.service.login(instance, options_dict.get('ssh_options'))
                    break
                else:
                    print "Not a valid choice. Try again."
            except ValueError:
                print "Not a valid choice. Try again."

    def transfer_files(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, expected_arguments=['FILE_NAME*'], unbounded_args=True)
        result = self.service.transfer_files(args, options_dict.get('ssh_options'))

        table = PrettyTable()
        table.set_field_names(("INSTANCE ID", "PUBLIC IP", "PRIVATE IP", "FILE NAME", "RESULT"))
        for instance, file, retcode in result:
            table.add_row((instance.id,
                           instance.public_dns_name,
                           instance.private_dns_name,
                           file,
                           retcode
                           ))
        table.printt()

    def run_command(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, expected_arguments=['COMMAND'])
        result = self.service.run_command(args[0], options_dict.get('ssh_options'))

        table = PrettyTable()
        table.set_field_names(("INSTANCE ID", "PUBLIC IP", "PRIVATE IP", "RESULT"))
        for instance, retcode in result:
            table.add_row((instance.id,
                           instance.public_dns_name,
                           instance.private_dns_name,
                           retcode
                           ))
        table.printt()



class ServicePlugin(object):
    def __init__(self, cluster=None):
        self.cluster = cluster
        self.logger = logging #logging.getLogger(self.__class__.__name__)

    def get_roles(self):
        """
        Returns a list of role identifiers for this service type.
        """
        raise RuntimeError("Not implemented.")

    def get_instances(self):
        """
        Returns a list of running Instance objects from the cluster

        self.cluster.get_instances_in_role(ROLE, "running")
        """
        raise RuntimeError("Not implemented.")

    def launch_cluster(self):
        raise RuntimeError("Not implemented.")
        
    def terminate_cluster(self):
        """
        Terminates all instances in the cluster
        """
        # TODO: Clear all tags
        self.logger.info("Terminating cluster")
        self.cluster.terminate()

    def get_storage(self):
        return self.cluster.get_storage()
    
    def print_storage_status(self):
        storage = self.get_storage()
        if not os.path.isfile(storage._get_storage_filename()):
            storage.print_status(volumes=self._get_cluster_volumes(storage))
        else:
            storage.print_status()

    def _get_standard_ssh_command(self, instance, ssh_options, remote_command=None):
        """
        Returns the complete SSH command ready for execution on the instance.
        """
        cmd = "ssh %s %s" % (xstr(ssh_options), instance.public_dns_name)
        
        if remote_command is not None:
            cmd += " '%s'" % remote_command

        return cmd

    def _attach_storage(self, roles):
        storage = self.cluster.get_storage()
        if storage.has_any_storage(roles):
            print "Waiting 10 seconds before attaching storage"
            time.sleep(10)
            for role in roles:
                storage.attach(role, self.cluster.get_instances_in_role(role, 'running'))
            storage.print_status(roles)

    def _launch_instances(self, instance_template, exclude_roles=[]):
        it = instance_template
        user_data_file_template = it.user_data_file_template
        
        if it.user_data_file_template == None:
            user_data_file_template = self._get_default_user_data_file_template()

        ebs_mappings = []
        storage = self.cluster.get_storage()
        for role in it.roles:
            if role in exclude_roles:
                continue 
            if storage.has_any_storage((role,)):
                ebs_mappings.append(storage.get_mappings_string_for_role(role))

        replacements = {
            "%ENV%": build_env_string(it.env_strings, {
                "ROLES": ",".join(it.roles),
                "USER_PACKAGES": it.user_packages,
                "AUTO_SHUTDOWN": it.auto_shutdown,
                "EBS_MAPPINGS": ";".join(ebs_mappings),
            })
        }
        self.logger.debug("EBS Mappings: %s" % ";".join(ebs_mappings))
        instance_user_data = InstanceUserData(user_data_file_template, replacements)

        self.logger.debug("InstanceUserData gzipped length: %d" % len(instance_user_data.read_as_gzip_stream()))

        instance_ids = self.cluster.launch_instances(it.roles, 
                                                     it.number, 
                                                     it.image_id,
                                                     it.size_id,
                                                     instance_user_data,
                                                     key_name=it.key_name,
                                                     public_key=it.public_key,
                                                     placement=it.placement,
                                                     security_groups=it.security_groups, 
                                                     spot_config=it.spot_config)

        self.logger.debug("Instance ids reported to start: %s" % str(instance_ids))
        return instance_ids

    def delete_storage(self, force=False):
        storage = self.cluster.get_storage()
        self._print_storage_status(storage)
        if not force and not self._prompt("Delete all storage volumes? THIS WILL \
    PERMANENTLY DELETE ALL DATA"):
            print "Not deleting storage volumes."
        else:
            print "Deleting storage"
            storage.delete(storage.get_roles())
    
    def create_storage(self, role, number_of_instances, availability_zone, spec_file):
        storage = self.get_storage()
        storage.create(role, number_of_instances, availability_zone, spec_file)

    def run_command(self, command, ssh_options):
        instances = self.get_instances()
        ssh_commands = [self._get_standard_ssh_command(instance, ssh_options=ssh_options, remote_command=command)
                    for instance in instances]
        procs = [subprocess.Popen(ssh_command, shell=True) for ssh_command in ssh_commands]
        retcodes = [proc.wait() for proc in procs]
        return zip(instances, retcodes)

    def _get_transfer_command(self, instance, file_name, ssh_options):
        transfer_command = "scp %s %s %s:" % (xstr(ssh_options), file_name, instance.public_dns_name)
#        transfer_command = self._get_standard_ssh_command(instance, ssh_options, "cat > %s" % file_name) + " < %s" % file_name
        self.logger.debug("Transfer command: %s" % transfer_command)
        return transfer_command

    def transfer_files(self, file_names, ssh_options):
        instances = self.get_instances()
        operations = list(itertools.product(instances, file_names))
        ssh_commands = [self._get_transfer_command(instance, file_name, ssh_options) for instance, file_name in
                        operations]
        procs = [subprocess.Popen(ssh_command, shell=True) for ssh_command in ssh_commands]
        retcodes = [proc.wait() for proc in procs]
        return [(operation[0], operation[1], retcode) for operation, retcode in zip(operations, retcodes)]

    def login(self, instance, ssh_options):
        ssh_command = self._get_standard_ssh_command(instance, ssh_options)
        subprocess.call(ssh_command, shell=True)
    

########NEW FILE########
__FILENAME__ = ec2
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from boto.exception import EC2ResponseError
from cloud.cluster import Cluster
from cloud.cluster import Instance
from cloud.cluster import RoleSyntaxException
from cloud.cluster import TimeoutException
from cloud.cluster import InstanceTerminatedException
from cloud.storage import JsonVolumeManager
from cloud.storage import JsonVolumeSpecManager
from cloud.storage import MountableVolume
from cloud.storage import Storage
from cloud.exception import VolumesStillInUseException
from cloud.util import xstr
from cloud.util import get_ec2_connection
from cloud.util import log_cluster_action
from cloud.util import FULL_HIDE
from cloud.util import ssh_available
from cloud.decorators import timeout
from prettytable import PrettyTable
from fabric.api import *
import logging
import os
import paramiko
import re
import subprocess
import sys
import time

logger = logging.getLogger(__name__)

CLOUD_PROVIDER = ("ec2", ('cloud.providers.ec2', 'Ec2Cluster'))

def _run_command_on_instance(instance, ssh_options, command):
  print "Running ssh %s %s '%s'" % \
    (ssh_options, instance.public_dns_name, command)
  retcode = subprocess.call("ssh %s %s '%s'" %
                           (ssh_options, instance.public_dns_name, command),
                           shell=True)
  print "Command running on %s returned with value %s" % \
    (instance.public_dns_name, retcode)

def _wait_for_volume(ec2_connection, volume_id):
  """
  Waits until a volume becomes available.
  """
  while True:
    volumes = ec2_connection.get_all_volumes([volume_id,])
    if volumes[0].status == 'available':
      break
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(1)

class Ec2Cluster(Cluster):
  """
  A cluster of EC2 instances. A cluster has a unique name.

  Instances running in the cluster run in a security group with the cluster's
  name, and also a name indicating the instance's role, e.g. <cluster-name>-foo
  to show a "foo" instance.
  """

  @staticmethod
  def get_clusters_with_role(role, state="running", region="us-east-1"):
    all_instances = get_ec2_connection(region).get_all_instances()
    clusters = []
    for res in all_instances:
      instance = res.instances[0]
      for group in res.groups:
        if group.name.endswith("-" + role) and instance.state == state:
          clusters.append(re.sub("-%s$" % re.escape(role), "", group.name))
    return clusters

  def __init__(self, name, config_dir, region):
    super(Ec2Cluster, self).__init__(name, config_dir, region)

    self.ec2Connection = get_ec2_connection(region)

  def get_provider_code(self):
    return "ec2"

  def _get_cluster_group_name(self):
    return self.name

  def _check_role_name(self, role):
    if not re.match("^[a-zA-Z0-9_+]+$", role):
      raise RoleSyntaxException("Invalid role name '%s'" % role)

  def _group_name_for_role(self, role):
    """
    Return the security group name for an instance in a given role.
    """
    self._check_role_name(role)
    return "%s-%s" % (self.name, role)

  def _get_group_names(self, roles):
    group_names = [self._get_cluster_group_name()]
    for role in roles:
      group_names.append(self._group_name_for_role(role))
    return group_names

  def _get_all_group_names(self):
    security_groups = self.ec2Connection.get_all_security_groups()
    security_group_names = \
      [security_group.name for security_group in security_groups]
    return security_group_names

  def _get_all_group_names_for_cluster(self):
    all_group_names = self._get_all_group_names()
    r = []
    if self.name not in all_group_names:
      return r
    for group in all_group_names:
      if re.match("^%s(-[a-zA-Z0-9_+]+)?$" % self.name, group):
        r.append(group)
    return r

  def _create_custom_security_groups(self, security_groups=[]):
    """
    For each security group that doesn't exist we create it
    """

    all_groups = self._get_all_group_names()

    for group in security_groups:
        if group not in all_groups:
            self.ec2Connection.create_security_group(group,
                 "Custom group: %s" % group)

  def _create_groups(self, role):
    """
    Create the security groups for a given role, including a group for the
    cluster if it doesn't exist.
    """
    self._check_role_name(role)
    security_group_names = self._get_all_group_names()

    cluster_group_name = self._get_cluster_group_name()
    if not cluster_group_name in security_group_names:
      self.ec2Connection.create_security_group(cluster_group_name,
                                               "Cluster (%s)" % (self.name))
      self.ec2Connection.authorize_security_group(cluster_group_name,
                                                  cluster_group_name)
      # Allow SSH from anywhere
      self.ec2Connection.authorize_security_group(cluster_group_name,
                                                  ip_protocol="tcp",
                                                  from_port=22, to_port=22,
                                                  cidr_ip="0.0.0.0/0")

    role_group_name = self._group_name_for_role(role)
    if not role_group_name in security_group_names:
      self.ec2Connection.create_security_group(role_group_name,
        "Role %s (%s)" % (role, self.name))

  def authorize_role(self, role, from_port, to_port, cidr_ip):
    """
    Authorize access to machines in a given role from a given network.
    """
    self._check_role_name(role)
    role_group_name = self._group_name_for_role(role)
    # Revoke first to avoid InvalidPermission.Duplicate error
    self.ec2Connection.revoke_security_group(role_group_name,
                                             ip_protocol="tcp",
                                             from_port=from_port,
                                             to_port=to_port, cidr_ip=cidr_ip)
    self.ec2Connection.authorize_security_group(role_group_name,
                                                ip_protocol="tcp",
                                                from_port=from_port,
                                                to_port=to_port,
                                                cidr_ip=cidr_ip)

  def _get_instances(self, group_name, state_filter=None):
    """
    Get all the instances in a group, filtered by state.

    @param group_name: the name of the group
    @param state_filter: the state that the instance should be in
      (e.g. "running"), or None for all states
    """
    all_instances = self.ec2Connection.get_all_instances()
    instances = []
    for res in all_instances:
      for group in res.groups:
        if group.name == group_name:
          for instance in res.instances:
            if state_filter == None or instance.state == state_filter:
              instances.append(instance)
    return instances

  def get_instances_in_role(self, role, state_filter=None):
    """
    Get all the instances in a role, filtered by state.

    @param role: the name of the role
    @param state_filter: the state that the instance should be in
      (e.g. "running"), or None for all states
    """
    self._check_role_name(role)

    instances = self._get_instances(self._group_name_for_role(role),
                               state_filter)
    for i in instances:
        i.__setattr__('role', role)
    return instances
    """
    instances = []
    for instance in self._get_instances(self._group_name_for_role(role),
                                        state_filter):
      instances.append(Instance(instance.id, role, instance.dns_name,
                                instance.private_dns_name,
                                instance.launch_time,
                                instance.instance_type,
                                instance.placement))
    return instances
    """

  def _print_instance(self, role, instance):
    print "\t".join((role, instance.id,
      instance.image_id,
      instance.dns_name, instance.private_dns_name,
      instance.state, xstr(instance.key_name), instance.instance_type,
      str(instance.launch_time), instance.placement))

  def _get_instance_status_headers(self):
    return ("Role", "Instance Id", "Image Id", "Public DNS", "Private DNS",
            "State", "Key", "Instance Type", "Launch Time", "Zone")

  def _get_instance_status(self, role, instance):
    return (role, instance.id,
            instance.image_id,
            instance.dns_name, instance.private_dns_name,
            instance.state, xstr(instance.key_name), instance.instance_type,
            str(instance.launch_time), instance.placement)

  def get_instances(self, roles=None, state_filter="running"):
    """
    Returns a list of Instance objects in this cluster
    """
    if roles is None:
      return self._get_instances(self._get_cluster_group_name(), state_filter)
    else:
      instances = []
      for role in roles:
        instances.extend(self._get_instances(self._group_name_for_role(role),
                                        state_filter))
      return instances

  def print_status(self, roles=None, state_filter="running"):
    """
    Print the status of instances in the given roles, filtered by state.
    """
    table = PrettyTable()
    table.set_field_names(self._get_instance_status_headers())
    if not roles:
      for instance in self._get_instances(self._get_cluster_group_name(),
                                          state_filter):
        table.add_row(self._get_instance_status("", instance))
    else:
      for role in roles:
        for instance in self._get_instances(self._group_name_for_role(role),
                                            state_filter):
          table.add_row(self._get_instance_status(role, instance))

    if len(table.rows):
        table.printt()
        print "Total instances: %d" % len(table.rows)
    else:
        print "No running instances."

  def launch_instances(self, roles, number, image_id, size_id,
                       instance_user_data, **kwargs):
    for role in roles:
      self._check_role_name(role)
      self._create_groups(role)

    user_data = instance_user_data.read_as_gzip_stream()
    security_groups = self._get_group_names(roles) + kwargs.get('security_groups', [])

    # create groups from config that may not exist
    self._create_custom_security_groups(security_groups)

    spot_config = kwargs.get("spot_config", None)

    if spot_config and spot_config["spot_cluster"]:
        print("Placing a spot instance bid")

        max_price = spot_config.get("max_price", None)
        launch_group = spot_config.get("launch_group", None)
        if not max_price or not launch_group:
            raise InvalidSpotConfigurationException("Must specify both max_price and launch_group")

        # if we need to set these on a cluster-by-cluster basis we can pull
        # them out into the config as well, but I think all we need is the above 
        valid_from = None
        valid_until = None
        availability_zone_group = None
        reservation_type = "one-time" 

        results = self.ec2Connection.request_spot_instances(max_price, image_id, number, 
            reservation_type, valid_from, valid_until, launch_group, availability_zone_group, key_name=kwargs.get('key_name', None),
            security_groups=security_groups, user_data=user_data, instance_type=size_id, placement=kwargs.get('placement', None),
            kernel_id=kwargs.get('kernel_id', None),
            ramdisk_id=kwargs.get('ramdisk_i', None),
            monitoring_enabled=kwargs.get('monitoring_enabled', False),
            subnet_id=kwargs.get('subnet_id', None))     
        return [instance_request.id for instance_request in results]

    else:
        reservation = self.ec2Connection.run_instances(image_id, min_count=number,
            max_count=number, key_name=kwargs.get('key_name', None),
            security_groups=security_groups, user_data=user_data,
            instance_type=size_id, placement=kwargs.get('placement', None))
        return [instance.id for instance in reservation.instances]

  @timeout(600)
  def wait_for_instances(self, instance_ids, fail_on_terminated=True):
    wait_time = 3
    while True:
      try:
        if self._all_started(self.ec2Connection.get_all_instances(instance_ids), fail_on_terminated):
          break
      # don't timeout for race condition where instance is not yet registered
      except EC2ResponseError, e:
        pass
      logging.info("Sleeping for %d seconds..." % wait_time)
      time.sleep(wait_time)
    
  def _all_started(self, reservations, fail_on_terminated=True):
    for res in reservations:
      for instance in res.instances:
        # check for terminated
        if fail_on_terminated and instance.state == "terminated":
            raise InstanceTerminatedException(instance.state_reason['message'])

        if instance.state != "running":
          logging.info("Instance %s state = %s" % (instance, instance.state))
          return False

        if not ssh_available(env.user, env.key_filename, instance.public_dns_name):
            logging.info("SSH unavailable...")
            logging.info("User=%s; Host=%s; Key=%s" % (env.user, instance.public_dns_name, env.key_filename))
            return False

    return True

  def terminate(self):
    instances = self._get_instances(self._get_cluster_group_name(), "running")
    if instances:
      log_cluster_action(self.config_dir, self._get_cluster_group_name(), 
        "terminate-cluster", len(instances))
      self.ec2Connection.terminate_instances([i.id for i in instances])

  def delete(self):
    """
    Delete the security groups for each role in the cluster, and the group for
    the cluster.
    """
    group_names = self._get_all_group_names_for_cluster()
    for group in group_names:
      self.ec2Connection.delete_security_group(group)

  def get_storage(self):
    """
    Return the external storage for the cluster.
    """
    return Ec2Storage(self)


class Ec2Storage(Storage):
  """
  Storage volumes for an EC2 cluster. The storage is associated with a named
  cluster. Metadata for the storage volumes is kept in a JSON file on the client
  machine (in a file called "ec2-storage-<cluster-name>.json" in the
  configuration directory).
  """

  @staticmethod
  def create_formatted_snapshot(cluster, size, availability_zone, image_id,
                                key_name, ssh_options):
    """
    Creates a formatted snapshot of a given size. This saves having to format
    volumes when they are first attached.
    """
    conn = cluster.ec2Connection
    print "Starting instance"
    reservation = conn.run_instances(image_id, key_name=key_name,
                                     placement=availability_zone)
    instance = reservation.instances[0]
    print "Waiting for instance %s" % instance
    try:
      cluster.wait_for_instances([instance.id,])
      print "Started instance %s" % instance.id
    except TimeoutException:
      terminated = conn.terminate_instances([instance.id,])
      print "Timeout...shutting down %s" % terminated
      return
    print
    print "Waiting 60 seconds before attaching storage"
    time.sleep(60)
    # Re-populate instance object since it has more details filled in
    instance.update()

    print "Creating volume of size %s in %s" % (size, availability_zone)
    volume = conn.create_volume(size, availability_zone)
    print "Created volume %s" % volume
    print "Attaching volume to %s" % instance.id
    volume.attach(instance.id, '/dev/sdj')

    _run_command_on_instance(instance, ssh_options, """
      while true ; do
        echo 'Waiting for /dev/sdj...';
        if [ -e /dev/sdj ]; then break; fi;
        sleep 1;
      done;
      mkfs.ext3 -F -m 0.5 /dev/sdj
    """)

    print "Detaching volume"
    conn.detach_volume(volume.id, instance.id)
    print "Creating snapshot"
    description = "Formatted %dGB snapshot created by PyStratus" % size
    snapshot = volume.create_snapshot(description=description)
    print "Created snapshot %s" % snapshot.id
    _wait_for_volume(conn, volume.id)
    print
    print "Deleting volume"
    volume.delete()
    print "Deleted volume"
    print "Stopping instance"
    terminated = conn.terminate_instances([instance.id,])
    print "Stopped instance %s" % terminated

  def __init__(self, cluster):
    super(Ec2Storage, self).__init__(cluster)
    self.config_dir = cluster.config_dir

  def _get_storage_filename(self):
    # create the storage directory if it doesn't already exist
    p = os.path.join(self.config_dir, ".storage")
    if not os.path.isdir(p):
        os.makedirs(p)
    return os.path.join(p, "ec2-storage-%s.json" % (self.cluster.name))

  def create(self, role, number_of_instances, availability_zone, spec_filename):
    spec_file = open(spec_filename, 'r')
    volume_spec_manager = JsonVolumeSpecManager(spec_file)
    volume_manager = JsonVolumeManager(self._get_storage_filename())
    for dummy in range(number_of_instances):
      mountable_volumes = []
      volume_specs = volume_spec_manager.volume_specs_for_role(role)
      for spec in volume_specs:
        logger.info("Creating volume of size %s in %s from snapshot %s" % \
                    (spec.size, availability_zone, spec.snapshot_id))
        volume = self.cluster.ec2Connection.create_volume(spec.size,
                                                          availability_zone,
                                                          spec.snapshot_id)
        mountable_volumes.append(MountableVolume(volume.id, spec.mount_point,
                                                 spec.device))
      volume_manager.add_instance_storage_for_role(role, mountable_volumes)

  def _get_mountable_volumes(self, role):
    storage_filename = self._get_storage_filename()
    volume_manager = JsonVolumeManager(storage_filename)
    return volume_manager.get_instance_storage_for_role(role)

  def get_mappings_string_for_role(self, role):
    mappings = {}
    mountable_volumes_list = self._get_mountable_volumes(role)
    for mountable_volumes in mountable_volumes_list:
      for mountable_volume in mountable_volumes:
        mappings[mountable_volume.mount_point] = mountable_volume.device
    return ";".join(["%s,%s,%s" % (role, mount_point, device) for (mount_point, device)
                     in mappings.items()])

  def _has_storage(self, role):
    return self._get_mountable_volumes(role)

  def has_any_storage(self, roles):
    for role in roles:
      if self._has_storage(role):
        return True
    return False

  def get_roles(self):
    storage_filename = self._get_storage_filename()
    volume_manager = JsonVolumeManager(storage_filename)
    return volume_manager.get_roles()

  def _get_ec2_volumes_dict(self, mountable_volumes):
    volume_ids = [mv.volume_id for mv in sum(mountable_volumes, [])]
    volumes = self.cluster.ec2Connection.get_all_volumes(volume_ids)
    volumes_dict = {}
    for volume in volumes:
      volumes_dict[volume.id] = volume
    return volumes_dict

  def get_volumes(self, roles=None, volumes=None):
    result = []
    if volumes is not None:
      for r, v in volumes:
        result.append((r,v))
    else:
      if roles is None:
        storage_filename = self._get_storage_filename()
        volume_manager = JsonVolumeManager(storage_filename)
        roles = volume_manager.get_roles()
      for role in roles:
        mountable_volumes_list = self._get_mountable_volumes(role)
        ec2_volumes = self._get_ec2_volumes_dict(mountable_volumes_list)
        for mountable_volumes in mountable_volumes_list:
          for mountable_volume in mountable_volumes:
            result.append((role, ec2_volumes[mountable_volume.volume_id]))
    return result

  def _replace(self, string, replacements):
    for (match, replacement) in replacements.iteritems():
      string = string.replace(match, replacement)
    return string

  def check(self):
    storage_filename = self._get_storage_filename()
    volume_manager = JsonVolumeManager(storage_filename)

    all_mountable_volumes = []
    roles = volume_manager.get_roles()
    for r in roles:
        all_mountable_volumes.extend(sum(self._get_mountable_volumes(r),[]))

    if not all_mountable_volumes:
        print "No EBS volumes found. Have you executed 'create-storage' first?"
        return

    error = False

    # disable boto ERROR logging for now
    boto_logging = logging.getLogger('boto')
    level = boto_logging.level
    boto_logging.setLevel(logging.FATAL)

    for vid in [v.volume_id for v in all_mountable_volumes]:
        try:
            self.cluster.ec2Connection.get_all_volumes([vid])
        except:
            error = True
            print "Volume does not exist: %s" % vid

    if not error:
        print "Congrats! All volumes exist!"

    # reset boto logging
    boto_logging.setLevel(level)

  def attach(self, role, instances):
    mountable_volumes_list = self._get_mountable_volumes(role)
    if not mountable_volumes_list:
      return
    ec2_volumes = self._get_ec2_volumes_dict(mountable_volumes_list)

    available_mountable_volumes_list = []

    available_instances_dict = {}
    for instance in instances:
      available_instances_dict[instance.id] = instance

    # Iterate over mountable_volumes and retain those that are not attached
    # Also maintain a list of instances that have no attached storage
    # Note that we do not fill in "holes" (instances that only have some of
    # their storage attached)
    for mountable_volumes in mountable_volumes_list:
      available = True
      for mountable_volume in mountable_volumes:
        if ec2_volumes[mountable_volume.volume_id].status != 'available':
          available = False
          attach_data = ec2_volumes[mountable_volume.volume_id].attach_data
          instance_id = attach_data.instance_id
          if available_instances_dict.has_key(instance_id):
            del available_instances_dict[instance_id]
      if available:
        available_mountable_volumes_list.append(mountable_volumes)

    if len(available_instances_dict) != len(available_mountable_volumes_list):
      logger.warning("Number of available instances (%s) and volumes (%s) \
        do not match." \
        % (len(available_instances_dict),
           len(available_mountable_volumes_list)))

    for (instance, mountable_volumes) in zip(available_instances_dict.values(),
                                             available_mountable_volumes_list):
      print "Attaching storage to %s" % instance.id
      for mountable_volume in mountable_volumes:
        volume = ec2_volumes[mountable_volume.volume_id]
        print "Attaching %s to %s" % (volume.id, instance.id)
        volume.attach(instance.id, mountable_volume.device)

  def delete(self, roles=[]):
    storage_filename = self._get_storage_filename()
    volume_manager = JsonVolumeManager(storage_filename)
    for role in roles:
      mountable_volumes_list = volume_manager.get_instance_storage_for_role(role)
      ec2_volumes = self._get_ec2_volumes_dict(mountable_volumes_list)
      all_available = True
      for volume in ec2_volumes.itervalues():
        if volume.status != 'available':
          all_available = False
          logger.warning("Volume %s is not available.", volume)
      if not all_available:
        msg = "Some volumes are still in use. Aborting delete."
        logger.warning(msg)
        raise VolumesStillInUseException(msg)
      for volume in ec2_volumes.itervalues():
        volume.delete()
      volume_manager.remove_instance_storage_for_role(role)

  def create_snapshot_of_all_volumes(self, cluster_name, volumes=[]):
    for r, v in volumes:
      description=",".join((v.id, r, cluster_name))
      print "Creating snapshot with description %s" % description
      self.cluster.ec2Connection.create_snapshot(v.id, description=description)

########NEW FILE########
__FILENAME__ = service
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Classes for running services on a cluster.
"""

from __future__ import with_statement

from cloud.settings import SERVICE_PROVIDER_MAP
from cloud.cluster import get_cluster
from cloud.cluster import InstanceUserData
from cloud.cluster import TimeoutException
from cloud.providers.ec2 import Ec2Storage
from cloud.util import build_env_string
from cloud.util import url_get
from cloud.util import xstr
from prettytable import PrettyTable
from datetime import datetime
import logging
import types
import os
import re
import socket
import subprocess
import sys
import time
import tempfile
import simplejson

logger = logging.getLogger(__name__) 

class InstanceTemplate(object):
  """
  A template for creating server instances in a cluster.
  """
  def __init__(self, roles, number, image_id, size_id,
                     key_name, public_key,
                     user_data_file_template=None, placement=None,
                     user_packages=None, auto_shutdown=None, env_strings=[],
                     security_groups=[], spot_config=None):
    self.roles = roles
    self.number = number
    self.image_id = image_id
    self.size_id = size_id
    self.key_name = key_name
    self.public_key = public_key
    self.user_data_file_template = user_data_file_template
    self.placement = placement
    self.user_packages = user_packages
    self.auto_shutdown = auto_shutdown
    self.env_strings = env_strings
    self.security_groups = security_groups
    self.spot_config = spot_config

    t = type(self.security_groups)
    if t is types.NoneType:
        self.security_groups = []
    elif t is types.StringType:
        self.security_groups = [security_groups]

  def add_env_strings(self, env_strings):
    new_env_strings = list(self.env_strings or [])
    new_env_strings.extend(env_strings)
    self.env_strings = new_env_strings

def get_service(service, provider):
    """
    Retrieve the Service class for a service and provider.
    """
    mod_name, service_classname = SERVICE_PROVIDER_MAP[service][provider]
    _mod = __import__(mod_name, globals(), locals(), [service_classname])
    return getattr(_mod, service_classname)

########NEW FILE########
__FILENAME__ = settings
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

SERVICE_PROVIDER_MAP = {
  "cassandra": {
    "ec2": ('cassandra.service', 'CassandraService')
  },
  "hadoop": {
    "ec2": ('hadoop.service', 'HadoopService'),
    "ec2_spot": ('hadoop.service', 'HadoopService'),
  },
  "hadoop_cassandra_hybrid": {
    "ec2": ('hadoop_cassandra_hybrid.service', 'HadoopCassandraHybridService')
  },
}


########NEW FILE########
__FILENAME__ = storage
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Classes for controlling external cluster storage.
"""

import logging
import sys
import simplejson as json

logger = logging.getLogger(__name__)

class VolumeSpec(object):
  """
  The specification for a storage volume, encapsulating all the information
  needed to create a volume and ultimately mount it on an instance.
  """
  def __init__(self, size, mount_point, device, snapshot_id):
    self.size = size
    self.mount_point = mount_point
    self.device = device
    self.snapshot_id = snapshot_id


class JsonVolumeSpecManager(object):
  """
  A container for VolumeSpecs. This object can read VolumeSpecs specified in
  JSON.
  """
  def __init__(self, spec_file):
    self.spec = json.load(spec_file)

  def volume_specs_for_role(self, role):
    return [VolumeSpec(d["size_gb"], d["mount_point"], d["device"],
                       d["snapshot_id"]) for d in self.spec[role]]

  def get_mappings_string_for_role(self, role):
    """
    Returns a short string of the form
    "role,mount_point1,device1;role,mount_point2,device2;..."
    which is useful for passing as an environment variable.
    """
    return ";".join(["%s,%s,%s" % (role, d["mount_point"], d["device"])
                     for d in self.spec[role]])


class MountableVolume(object):
  """
  A storage volume that has been created. It may or may not have been attached
  or mounted to an instance.
  """
  def __init__(self, volume_id, mount_point, device):
    self.volume_id = volume_id
    self.mount_point = mount_point
    self.device = device


class JsonVolumeManager(object):

  def __init__(self, filename):
    self.filename = filename

  def _load(self):
    try:
      return json.load(open(self.filename, "r"))
    except IOError:
      logger.debug("File %s does not exist.", self.filename)
      return {}

  def _store(self, obj):
    return json.dump(obj, open(self.filename, "w"), sort_keys=True, indent=2)
  
  def get_roles(self):
    json_dict = self._load()
    return json_dict.keys()

  def add_instance_storage_for_role(self, role, mountable_volumes):
    json_dict = self._load()
    mv_dicts = [mv.__dict__ for mv in mountable_volumes]
    json_dict.setdefault(role, []).append(mv_dicts)
    self._store(json_dict)

  def remove_instance_storage_for_role(self, role):
    json_dict = self._load()
    del json_dict[role]
    self._store(json_dict)

  def get_instance_storage_for_role(self, role):
    """
    Returns a list of lists of MountableVolume objects. Each nested list is
    the storage for one instance.
    """
    try:
      json_dict = self._load()
      instance_storage = []
      for instance in json_dict[role]:
        vols = []
        for vol in instance:
          vols.append(MountableVolume(vol["volume_id"], vol["mount_point"],
                                      vol["device"]))
        instance_storage.append(vols)
      return instance_storage
    except KeyError:
      return []

class Storage(object):
  """
  Storage volumes for a cluster. The storage is associated with a named
  cluster. Many clusters just have local storage, in which case this is
  not used.
  """

  def __init__(self, cluster):
    self.cluster = cluster

  def create(self, role, number_of_instances, availability_zone, spec_filename):
    """
    Create new storage volumes for instances with the given role, according to
    the mapping defined in the spec file.
    """
    pass

  def get_mappings_string_for_role(self, role):
    """
    Returns a short string of the form
    "mount_point1,device1;mount_point2,device2;..."
    which is useful for passing as an environment variable.
    """
    raise Exception("Unimplemented")

  def has_any_storage(self, roles):
    """
    Return True if any of the given roles has associated storage
    """
    return False

  def get_roles(self):
    """
    Return a list of roles that have storage defined.
    """
    return []

  def print_status(self, roles=None):
    """
    Print the status of storage volumes for the given roles.
    """
    pass

  def attach(self, role, instances):
    """
    Attach volumes for a role to instances. Some volumes may already be
    attached, in which case they are ignored, and we take care not to attach
    multiple volumes to an instance.
    """
    pass

  def delete(self, roles=[]):
    """
    Permanently delete all the storage for the given roles.
    """
    pass

########NEW FILE########
__FILENAME__ = util
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility functions.
"""

import os
import csv
import time
import ConfigParser
import socket
import urllib2
import paramiko
import logging

from subprocess import Popen, PIPE, CalledProcessError
from boto.ec2 import regions as EC2Regions
from fabric.api import *

FULL_HIDE = hide("running", "stdout", "stderr", "warnings")

def get_ec2_connection(regionName):
    for region in EC2Regions():
        if region.name == regionName:
            return region.connect()

    raise RuntimeError("Unknown region name: %s" % regionName)

def bash_quote(text):
  """Quotes a string for bash, by using single quotes."""
  if text == None:
    return ""
  return "'%s'" % text.replace("'", "'\\''")

def bash_quote_env(env):
  """Quotes the value in an environment variable assignment."""
  if env.find("=") == -1:
    return env
  (var, value) = env.split("=", 1)
  return "%s=%s" % (var, bash_quote(value))

def build_env_string(env_strings=[], pairs={}):
  """Build a bash environment variable assignment"""
  env = ''
  if env_strings:
    for env_string in env_strings:
      env += "%s " % bash_quote_env(env_string)
  if pairs:
    for key, val in pairs.items():
      env += "%s=%s " % (key, bash_quote(val))
  return env[:-1]

def get_all_cluster_names_from_config_file(config):
  return config.sections()

def merge_config_with_options(section_name, config, options):
  """
  Merge configuration options with a dictionary of options.
  Keys in the options dictionary take precedence.
  """
  res = {}
  try:
    for (key, value) in config.items(section_name):
      if value.find("\n") != -1:
        res[key] = value.split("\n")
      else:
        res[key] = value
  except ConfigParser.NoSectionError:
    pass
  except ValueError, e:
    # incomplete format error usually means you forgot
    # to include the type for interpolation
    if "incomplete format" in e.message:
       msg = "Section '%s'. Double check that your formatting " \
             "contains the format type after the closing parantheses. " \
             "Example: %%(foo)s" % section_name
       raise ConfigParser.InterpolationError(options, section_name, msg)

  for key in options:
    if options[key] != None:
      res[key] = options[key]
  return res

def url_get(url, timeout=10, retries=0):
  """
  Retrieve content from the given URL.
  """
   # in Python 2.6 we can pass timeout to urllib2.urlopen
  socket.setdefaulttimeout(timeout)
  attempts = 0
  while True:
    try:
      return urllib2.urlopen(url).read()
    except urllib2.URLError:
      attempts = attempts + 1
      if attempts > retries:
        raise

def xstr(string):
  """Sane string conversion: return an empty string if string is None."""
  return '' if string is None else str(string)

def check_output(*popenargs, **kwargs):
  r"""Run command with arguments and return its output as a byte string.

  If the exit code was non-zero it raises a CalledProcessError.  The
  CalledProcessError object will have the return code in the returncode
  attribute and output in the output attribute.

  The arguments are the same as for the Popen constructor.  Example:

  >>> check_output(["ls", "-l", "/dev/null"])
  'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

  The stdout argument is not allowed as it is used internally.
  To capture standard error in the result, use stderr=STDOUT.

  >>> check_output(["/bin/sh", "-c",
  ...               "ls -l non_existent_file ; exit 0"],
  ...              stderr=STDOUT)
  'ls: non_existent_file: No such file or directory\n'

  NOTE: copied from 2.7 standard library so that we maintain our compatibility with 2.5
  """
  if 'stdout' in kwargs:
      raise ValueError('stdout argument not allowed, it will be overridden.')
  process = Popen(stdout=PIPE, *popenargs, **kwargs)
  output, unused_err = process.communicate()
  retcode = process.poll()
  if retcode:
      cmd = kwargs.get("args")
      if cmd is None:
          cmd = popenargs[0]
      raise CalledProcessError(retcode, cmd)
  return output

def log_cluster_action(config_dir, cluster_name, command, number,
instance_type=None, provider=None, plugin=None):
    """Log details of cluster launching or termination to a csv file.
    """

    csv_file = open(os.path.join(config_dir, "launch_log.csv"), "a+b")
    csv_log = csv.writer(csv_file)
    csv_log.writerow([cluster_name, command, number, instance_type, provider, plugin, time.strftime("%Y-%m-%d %H:%M:%S %Z")])
    csv_file.close()

def ssh_available(user, private_key, host, port=22, timeout=10):
    client = paramiko.SSHClient()

    # Load known host keys (e.g. ~/.ssh/known_hosts) unless user says not to.
    if not env.disable_known_hosts:
        client.load_system_host_keys()
    # Unless user specified not to, accept/add new, unknown host keys
    if not env.reject_unknown_hosts:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            port=port,
            username=user,
            key_filename=private_key,
            timeout=timeout,
            allow_agent=not env.no_agent,
            look_for_keys=not env.no_keys
        )
        return True
    except Exception, e:
        logging.warn(e)
        return False

def exec_command(cmd, **kwargs):
    c = sudo if use_sudo() else run
    return c(cmd, **kwargs)

def use_sudo():
    return env.user != "root"

########NEW FILE########
__FILENAME__ = cli
import sys
import logging
import urllib

from optparse import make_option

from cloud.plugin import CLIPlugin
from cloud.plugin import BASIC_OPTIONS
from cloud.service import InstanceTemplate
from cloud.util import log_cluster_action
from optparse import make_option
from prettytable import PrettyTable
from pprint import pprint

# Add options here to override what's in the clusters.cfg file
# TODO

class CassandraServiceCLI(CLIPlugin):
    USAGE = """Cassandra service usage: CLUSTER COMMAND [OPTIONS]
where COMMAND and [OPTIONS] may be one of:
            
                               CASSANDRA COMMANDS
  ----------------------------------------------------------------------------------
  start-cassandra                     starts the cassandra service on all nodes
  stop-cassandra                      stops the cassandra service on all nodes
  print-ring [INSTANCE_IDX]           displays the cluster's ring information
  rebalance                           recalculates tokens evenly and moves nodes
  remove-down-nodes                   removes nodes that are down from the ring

                               CLUSTER COMMANDS
  ----------------------------------------------------------------------------------
  details                             list instances in CLUSTER
  launch-cluster NUM_NODES            launch NUM_NODES Cassandra nodes
  expand-cluster NUM_NODES            adds new nodes
  terminate-cluster                   terminate all instances in CLUSTER
  login                               log in to the master in CLUSTER over SSH

                               STORAGE COMMANDS
  ----------------------------------------------------------------------------------
  list-storage                        list storage volumes for CLUSTER
  create-storage NUM_INSTANCES        create volumes for NUM_INSTANCES instances
    SPEC_FILE                           for CLUSTER, using SPEC_FILE
  delete-storage                      delete all storage volumes for CLUSTER
"""
    
    def __init__(self):
        super(CassandraServiceCLI, self).__init__()

        #self._logger = logging.getLogger("CassandraServiceCLI")
 
    def execute_command(self, argv, options_dict):
        if len(argv) < 2:
            self.print_help()

        self._cluster_name = argv[0]
        self._command_name = argv[1]

        # strip off the cluster name and command from argv
        argv = argv[2:]

        # handle all known commands and error on an unknown command
        if self._command_name == "details":
            self.print_instances()
            
        elif self._command_name == "simple-details":
            self.simple_print_instances(argv, options_dict)

        elif self._command_name == "terminate-cluster":
            self.terminate_cluster(argv, options_dict)

        elif self._command_name == "launch-cluster":
            self.launch_cluster(argv, options_dict)

        elif self._command_name == "expand-cluster":
            self.expand_cluster(argv, options_dict)

        elif self._command_name == "replace-down-nodes":
            self.replace_down_nodes(argv, options_dict)

        elif self._command_name == "login":
            self.login(argv, options_dict)

        elif self._command_name == "run-command":
            self.run_command(argv, options_dict)

        elif self._command_name == "transfer-files":
            self.transfer_files(argv, options_dict)

        elif self._command_name == "create-storage":
            self.create_storage(argv, options_dict)

        elif self._command_name == "delete-storage":
            self.delete_storage(argv, options_dict)

        elif self._command_name == "list-storage":
            self.print_storage()

        elif self._command_name == "stop-cassandra":
            self.stop_cassandra(argv, options_dict)

        elif self._command_name == "start-cassandra":
            self.start_cassandra(argv, options_dict)

        elif self._command_name == "print-ring":
            self.print_ring(argv, options_dict)

        elif self._command_name == "hack-config-for-multi-region":
            self.hack_config_for_multi_region(argv, options_dict)
            
        elif self._command_name == "rebalance":
            self.rebalance(argv, options_dict)

        elif self._command_name == "remove-down-nodes":
            self.remove_down_nodes(argv, options_dict)
        else:
            self.print_help()

    def expand_cluster(self, argv, options_dict):
        expected_arguments = ["NUM_INSTANCES"]
        opt, args = self.parse_options(self._command_name,
                                       argv,
                                       expected_arguments=expected_arguments,
                                       unbounded_args=True)
        opt.update(options_dict)

        number_of_nodes = int(args[0])
        instance_template = InstanceTemplate(
            (self.service.CASSANDRA_NODE,),
            number_of_nodes,
            opt.get('image_id'),
            opt.get('instance_type'),
            opt.get('key_name'),
            opt.get('public_key'),
            opt.get('user_data_file'),
            opt.get('availability_zone'),
            opt.get('user_packages'),
            opt.get('auto_shutdown'),
            opt.get('env'),
            opt.get('security_groups'))
#        instance_template.add_env_strings(["CLUSTER_SIZE=%d" % number_of_nodes])

        print "Expanding cluster by %d instance(s)...please wait." % number_of_nodes

        self.service.expand_cluster(instance_template)

    def replace_down_nodes(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name,
                                       argv)
        opt.update(options_dict)

        # test files
        for key in ['cassandra_config_file']:
            if opt.get(key) is not None:
                try:
                    url = urllib.urlopen(opt.get(key))
                    data = url.read()
                except:
                    raise
                    print "The file defined by %s (%s) does not exist. Aborting." % (key, opt.get(key))
                    sys.exit(1)

        number_of_nodes = len(self.service.calc_down_nodes())
        instance_template = InstanceTemplate(
            (self.service.CASSANDRA_NODE,),
            number_of_nodes,
            opt.get('image_id'),
            opt.get('instance_type'),
            opt.get('key_name'),
            opt.get('public_key'),
            opt.get('user_data_file'),
            opt.get('availability_zone'),
            opt.get('user_packages'),
            opt.get('auto_shutdown'),
            opt.get('env'),
            opt.get('security_groups'))
#        instance_template.add_env_strings(["CLUSTER_SIZE=%d" % number_of_nodes])

        print "Replacing %d down instance(s)...please wait." % number_of_nodes

        self.service.replace_down_nodes(instance_template,
                                        opt.get('cassandra_config_file'))

    def launch_cluster(self, argv, options_dict):
        """
        """
        expected_arguments = ["NUM_INSTANCES"]
        opt, args = self.parse_options(self._command_name, 
                                      argv,
                                      expected_arguments=expected_arguments)
        opt.update(options_dict)

        if self.service.get_instances() :
            print "This cluster is already running.  It must be terminated prior to being launched again."
            sys.exit(1)

        number_of_nodes = int(args[0])
        instance_template = InstanceTemplate(
            (self.service.CASSANDRA_NODE,), 
            number_of_nodes,
            opt.get('image_id'),
            opt.get('instance_type'),
            opt.get('key_name'),
            opt.get('public_key'), 
            opt.get('user_data_file'),
            opt.get('availability_zone'), 
            opt.get('user_packages'),
            opt.get('auto_shutdown'), 
            opt.get('env'),
            opt.get('security_groups'))
        instance_template.add_env_strings(["CLUSTER_SIZE=%d" % number_of_nodes])

        print "Launching cluster with %d instance(s)...please wait." % number_of_nodes

        self.service.launch_cluster(instance_template, opt)


        log_cluster_action(opt.get('config_dir'), self._cluster_name,
            "launch-cluster", number_of_nodes, opt.get("instance_type"),
            None, "cassandra")

    def stop_cassandra(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        print "Stopping Cassandra service on %d instance(s)...please wait." % len(instances)
        self.service.stop_cassandra(instances=instances)

    def start_cassandra(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        print "Starting Cassandra service on %d instance(s)...please wait." % len(instances)
        self.service.start_cassandra(instances=instances)

    def print_ring(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            print("No running instances. Aborting.")
            sys.exit(1)

        idx = 0
        if len(argv) > 0 :
            idx = int(argv[0])

        print(self.service.print_ring(instances[idx]))

    def hack_config_for_multi_region(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        opt_list = BASIC_OPTIONS + [make_option("--seeds", metavar="SEEDS", action="store", type="str", default="",  help="explicit comma separated seed list")]
        opt, args = self.parse_options(self._command_name, argv, opt_list)

        self.service.hack_config_for_multi_region(options_dict.get('ssh_options'), opt['seeds'])
        
    def rebalance(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        opt, args = self.parse_options(self._command_name, argv, [make_option("--offset", metavar="OFFSET", action="store", type=int, default=0, help="token offset")])
        self.service.rebalance(offset=opt['offset'])

    def remove_down_nodes(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        self.service.remove_down_nodes()

    def create_storage(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS,
                                       ["NUM_INSTANCES", "SPEC_FILE"])
        opt.update(options_dict)

        role = self.service.CASSANDRA_NODE
        number_of_instances = int(args[0])
        spec_file = args[1]

        # FIXME
        # check_options_set(opt, ['availability_zone'])

        self.service.create_storage(role, 
                                    number_of_instances,
                                    opt.get('availability_zone'),
                                    spec_file)
        self.print_storage()

########NEW FILE########
__FILENAME__ = service
import os
import sys
import time
import subprocess
import urllib
import tempfile
import socket

from fabric.api import *
from fabric.contrib import files

from cloud.cluster import TimeoutException
from cloud.service import InstanceTemplate
from cloud.plugin import ServicePlugin 
from cloud.util import exec_command
from cloud.util import use_sudo
from cloud.util import xstr
from cloud.util import check_output
from cloud.util import FULL_HIDE
from cloud.decorators import timeout

from yaml import load as parse_yaml
from yaml import dump as dump_yaml

try:
    from cElementTree import parse as parse_xml
    from cElementTree import tostring as dump_xml
    from cElementTree import Element
except:
    try:
        from xml.etree.cElementTree import parse as parse_xml
        from xml.etree.cElementTree import tostring as dump_xml
        from xml.etree.cElementTree import Element
    except:
        print "*"*80
        print "WARNING: cElementTree module does not exist. Defaulting to elementtree instead."
        print "It's recommended that you install the cElementTree module for faster XML parsing."
        print "*"*80
        from elementtree.ElementTree import parse as parse_xml
        from elementtree.ElementTree import parse as parse_xml
        from elementtree.ElementTree import Element

def find_new_token(existing_tokens):
    range = max(zip([(existing_tokens[-1] - 2**127)] + existing_tokens[:-1], existing_tokens[:]), key=lambda x: x[1] - x[0])
    return range[0] + (range[1]-range[0])/2

def parse_nodeline(nodeline) :
    fields = ("ip", "datacenter", "rack", "status", "state", "load", "distribution", "token")
    values = nodeline.split()
    values = values[:5] + [" ".join(values[5:7])] + values[7:]
    return dict(zip(fields, values))

class CassandraService(ServicePlugin):
    """
    """
    CASSANDRA_NODE = "cn"
    MAX_RESTART_ATTEMPTS = 3
    current_attempt = 1

    def __init__(self):
        super(CassandraService, self).__init__()

    def get_roles(self):
        return [self.CASSANDRA_NODE]

    def get_instances(self):
        return self.cluster.get_instances_in_role(self.CASSANDRA_NODE, "running")

    def _get_new_tokens_for_n_instances(self, existing_tokens, n):
        all_tokens = existing_tokens[:]
        for i in range(0, n):
            all_tokens.sort()
            new_token = find_new_token(all_tokens)
            all_tokens.append(new_token)
        return [token for token in all_tokens if token not in existing_tokens]

    def expand_cluster(self, instance_template, new_tokens=None):
        instances = self.get_instances()
        if instance_template.number > len(instances):
            raise Exception("The best we can do is double the cluster size at one time.  Please specify %d instances or less." % len(instances))
        if new_tokens is None:
            existing_tokens = [node['token'] for node in self._discover_ring()]
            self.logger.debug("Tokens: %s" % str(existing_tokens))
            if len(instances) != len(existing_tokens):
                raise Exception("There are %d existing instances, we need that many existing tokens..." % len(instances))
            new_tokens = self._get_new_tokens_for_n_instances([int(token) for token in existing_tokens], instance_template.number)
        elif len(new_tokens) != instance_template.number:
            raise Exception("We are creating %d new instances, we need that many new tokens..." % instance_template.number)

        instance_ids = self._launch_instances(instance_template)

        if len(instance_ids) != instance_template.number:
            self.logger.warn("Number of reported instance ids (%d) " \
                             "does not match requested number (%d)" % \
                             (len(instance_ids), instance_template.number))
        self.logger.debug("Waiting for %s instance(s) to start: %s" % \
            (instance_template.number, ", ".join(instance_ids)))
        time.sleep(1)

        try:
            self.cluster.wait_for_instances(instance_ids)
            self.logger.debug("%d instances started" % (instance_template.number,))
        except TimeoutException:
            self.logger.error("Timeout while waiting for %s instance to start." % \
                ",".join(instance_template.roles))

        instances = self.get_instances()
        self.logger.debug("We have %d current instances...", len(instances))
        new_instances = [instance for instance in instances if instance.id in instance_ids]
        if(len(new_instances) != len(instance_ids)) :
            raise Exception("Could only find %d new instances, expected %s" % (len(new_instances), str(instance_ids)))

        self.logger.info("Instances started: %s" % (str(new_instances),))

        self._attach_storage(instance_template.roles)

        # pull the remote cassandra.yaml file, modify it, and push it back out
        self._modify_

        first = True
        for instance in new_instances:
            if not first:
                self.logger.info("Waiting 2 minutes before starting the next instance...")
                time.sleep(2*60)
            else:
                first = False
            self.logger.info("Starting cassandra on instance %s." % instance.id)
            self.start_cassandra(instances=[instance], print_ring=False)

        self.print_ring(instances[0])


    def launch_cluster(self, instance_template, options):
        """
        """
        if self.get_instances() :
            raise Exception("This cluster is already running.  It must be terminated prior to being launched again.")

        instance_ids = self._launch_instances(instance_template)

        if len(instance_ids) != instance_template.number:
            self.logger.warn("Number of reported instance ids (%d) " \
                             "does not match requested number (%d)" % \
                             (len(instance_ids), instance_template.number))
        self.logger.debug("Waiting for %s instance(s) to start: %s" % \
            (instance_template.number, ", ".join(instance_ids)))
        time.sleep(1)

        try:
            self.cluster.wait_for_instances(instance_ids)
            self.logger.debug("%d instances started" % (instance_template.number,))
        except TimeoutException:
            self.logger.error("Timeout while waiting for %s instance to start." % \
                ",".join(instance_template.roles))

        instances = self.get_instances()
        self.logger.debug("We have %d current instances...", len(instances))
        new_instances = [instance for instance in instances if instance.id in instance_ids]
        if(len(new_instances) != len(instance_ids)) :
            raise Exception("Could only find %d new instances, expected %s" % (len(new_instances), str(instance_ids)))

        self.logger.debug("Instances started: %s" % (str(new_instances),))
        
        # attach storage
        self._attach_storage(instance_template.roles)

        new_cluster = (len(instances) == len(instance_ids))

        # configure the individual instances
        self._configure_cassandra(new_instances, new_cluster=new_cluster)

        # start up the service
        self.start_cassandra(instances=new_instances)
    
    def _configure_cassandra(self, instances, new_cluster=True, tokens=None):
        """
        """
        # we need all instances for seeds, but we should only transfer to new instances!
        all_instances = self.get_instances()
        if new_cluster :
            potential_seeds = all_instances
        else :
            potential_seeds = [instance for instance in all_instances if instance not in instances]

        self.logger.debug("Configuring %d Cassandra instances..." % len(instances))

        seed_ips = [str(instance.private_dns_name) for instance in potential_seeds[:2]]
        if tokens == None :
            tokens = self._get_evenly_spaced_tokens_for_n_instances(len(instances))

        # wait for all instances to be ready
        print "WAITING FOR ALL INSTANCES"
        while all_instances:
            i = all_instances[-1]
            home = self.get_cassandra_home(i)
            print home

            if home == "":
                continue
            all_instances.pop()

        # for each instance, generate a config file from the original file and upload it to
        # the cluster node
        for i, instance in enumerate(instances):
            self._configure_cassandra_instance(instance=instance, 
                                               seed_ips=seed_ips, 
                                               token=str(tokens[i]), 
                                               auto_bootstrap=not new_cluster)

        #self.logger.debug("Waiting for %d Cassandra instance(s) to install..." % len(instances))
        #for instance in instances:
        #    self._wait_for_cassandra_service(instance)

    @timeout(600)
    def _wait_for_cassandra_service(self, instance):
        """
        Waiting for the cassandra.pid file
        """
        wait_time = 3
        with settings(host_string=instance.public_dns_name, warn_only=True):
            with FULL_HIDE:
                try:
                    while not files.exists("/var/run/cassandra.pid", use_sudo=use_sudo()):
                        self.logger.debug("Sleeping for %d seconds..." % wait_time)
                        time.sleep(wait_time)
                # catch SystemExit because paramiko will call abort when it detects a failure
                # in establishing an SSH connection
                except SystemExit:
                    pass

    def _configure_cassandra_instance(self, instance, seed_ips, token, set_tokens=True, auto_bootstrap=False):
        self.logger.debug("Configuring %s..." % instance.id)
        yaml_file = os.path.join("/tmp", "cassandra.yaml")
        cassandra_home = self.get_cassandra_home(instance)

        self.logger.debug("Local cassandra.yaml file: %s" % yaml_file)
        with settings(host_string=instance.public_dns_name, warn_only=True): #, hide("everything"):

            cassandra_data = os.path.join("/mnt", "cassandra-data")
            cassandra_logs = os.path.join("/mnt", "cassandra-logs")

            # create directories and log files
            exec_command("mkdir -p %s" % cassandra_data)
            exec_command("mkdir -p %s" % cassandra_logs)

            # set permissions
            exec_command("chown -R cassandra:cassandra %s %s" % (cassandra_data, cassandra_logs))

            try:
                # get yaml file
                get(os.path.join(cassandra_home, "conf", "cassandra.yaml"), "/tmp")

                # modify it
                f = open(yaml_file)
                yaml = parse_yaml(f)
                f.close()

                yaml['seed_provider'][0]['parameters'][0]['seeds'] = ",".join(seed_ips)
                if set_tokens is True :
                    yaml['initial_token'] = token
                if auto_bootstrap :
                    yaml['auto_bootstrap'] = 'true'
                yaml['data_file_directories'] = [cassandra_data]
                yaml['commitlog_directory'] = cassandra_logs
                yaml['listen_address'] = str(instance.private_dns_name)
                yaml['rpc_address'] = str(instance.public_dns_name)

                f = open(yaml_file, "w")
                f.write(dump_yaml(yaml))
                f.close()

                # put modified yaml file
                put(yaml_file, os.path.join(cassandra_home, "conf", "cassandra.yaml"), use_sudo=use_sudo())
            except SystemExit, e:
                raise
                pass

        os.unlink(yaml_file)

    def hack_config_for_multi_region(self, ssh_options, seeds):
        instances = self.get_instances()
        downloaded_file = os.path.join("/tmp", "cassandra.yaml.downloaded")
        for instance in instances:
            with settings(host_string=instance.public_dns_name, warn_only=True):
                # download config file
                print "downloading config from %s" % instance.public_dns_name
                get("/etc/cassandra/cassandra.yaml", downloaded_file)

                print "modifying config from %s" % instance.public_dns_name
                yaml = parse_yaml(urllib.urlopen(downloaded_file))
                yaml['seed_provider'][0]['parameters'][0]['seeds'] = seeds
                yaml['listen_address'] = str(instance.public_dns_name)
                yaml['rpc_address'] = str(instance.public_dns_name)
                yaml['broadcast_address'] = socket.gethostbyname(str(instance.public_dns_name))
                yaml['endpoint_snitch'] = 'org.apache.cassandra.locator.Ec2MultiRegionSnitch'
                
                print "saving config from %s" % instance.public_dns_name
                fd, temp_file = tempfile.mkstemp(prefix='cassandra.yaml_', text=True)
                os.write(fd, dump_yaml(yaml))
                os.close(fd)

                #upload config file
                print "uploading new config to %s" % instance.public_dns_name
                put(temp_file, "/etc/cassandra/cassandra.yaml", use_sudo=use_sudo())

                os.unlink(temp_file)
                os.unlink(downloaded_file)

    def _get_evenly_spaced_tokens_for_n_instances(self, n):
        return [i*(2**127/n) for i in range(1,n+1)]

    def _get_config_value(self, config_file, yaml_name, xml_name):
        if config_file.endswith(".xml") :
            xml = parse_xml(urllib.urlopen(config_file)).getroot()
            return xml.find(xml_name).text
        elif config_file.endswith(".yaml") :
            yaml = parse_yaml(urllib.urlopen(config_file))
            return yaml[yaml_name]
        else:
            raise Exception("Configuration file must be on of xml or yaml")

    def print_ring(self, instance=None):
        # check to see if cassandra is running
        if not self.is_running(instance):
            return "Cassandra does not appear to be running."

        print "\nRing configuration..."
        print "NOTE: May not be accurate if the cluster just started or expanded.\n"
        return self._run_nodetool("ring", instance)

    def _run_nodetool(self, ntcommand, instance=None):
        if instance is None:
            instance = self.get_instances()[0]

        self.logger.debug("running nodetool on instance %s", instance.id)
        with settings(host_string=instance.public_dns_name, warn_only=True), hide("everything"):
            output = exec_command("nodetool -h %s %s" % (instance.private_dns_name, ntcommand))

        return output

    def _discover_ring(self, instance=None):
        if instance is None:
            instance = self.get_instances()[0]

        with settings(host_string=instance.public_dns_name, warn_only=True), hide("everything"):
            status = exec_command("service cassandra status")

            if status.failed:
                raise RuntimeException("Cassandra does not appear to be running.")

            self.logger.debug("Discovering ring...")
            retcode, output = self._run_nodetool("ring", instance)
            self.logger.debug("node tool output:\n%s" % output)
            lines = output.split("\n")[2:]

            assert len(lines) > 0, "Ring output must have more than two lines."

            self.logger.debug("Found %d nodes" % len(lines))
        
            return [parse_nodeline(line) for line in lines]

    def calc_down_nodes(self, instance=None):
        nodes = self._discover_ring(instance)
        return [node['token'] for node in nodes if node['status'] == 'Down']

    def replace_down_nodes(self, instance_template, config_file):
        down_tokens = self.calc_down_nodes()
        instance_template.number = len(down_tokens)
        self.expand_cluster(instance_template, config_file, [x-1 for x in down_tokens])
        self.remove_down_nodes()

    def remove_down_nodes(self, instance=None):
        nodes = self._discover_ring(instance)
        for node in nodes:
            if node['status'] == 'Down' and node['state'] == 'Normal':
                print "Removing node %s." % node['token']
                self._run_nodetool('removetoken %s' % node['token'], instance)

    def rebalance(self, offset=0):
        instances = self.get_instances()
        tokens = self._get_evenly_spaced_tokens_for_n_instances(len(instances))
        
        for token in tokens:
            #print "%s  --->  %s" % (token, (int(token)+offset))
            assert (int(token)+offset) <= 2**127, "Failed token: %s" % str((int(token)+offset))

        self.logger.info("new token space: %s" % str(tokens))
        for i, instance in enumerate(instances):
            token = str(int(tokens[i]) + offset)
            self.logger.info("Moving instance %s to token %s" % (instance.id, token))
            retcode, output = self._run_nodetool("move %s" % token, instance=instance)
            if retcode != 0 :
                self.logger.warn("Move failed for instance %s with return code %d..." % (instance.id, retcode))
                self.logger.warn(output)
            else :
                self.logger.info("Move succeeded for instance %s..." % instance.id)

    def _validate_ring(self, instance):
        """
        Run nodetool to verify that a ring is valid.
        """

        ring_output = exec_command("nodetool --host %s ring" % instance.private_dns_name)

        if ring_output.failed:
            return ring_output.return_code

        # some nodes can be down, but nodetool will still exit cleanly,
        # so doing some extra validation to ensure that all nodes of 
        # the ring are "Up" and "Normal" and manually set a bad return 
        # code otherwise
        retcode = 0
        for node in ring_output.splitlines()[3:]:
            #host = node[:16].strip()
            #data_center = node[16:28].strip()
            #rack = node[28:40].strip()
            #status = node[40:47].strip()
            #state = node[47

            nodesplit = node.split()

            self.logger.debug("Node %s is %s and %s" % (nodesplit[0], nodesplit[3], nodesplit[4]))
            if nodesplit[3].lower() != "up" and nodesplit[4].lower() != "normal":
                self.logger.debug("Node %s ring is not healthy" % nodesplit[0])
                self.logger.debug("Ring status:")
                self.logger.debug(ring_output)
                retcode = 200

        return retcode

    @timeout(600)
    def start_cassandra(self, instances=None, print_ring=True, retry=False):
        """Start Cassandra services on instances.
        To validate that Cassandra is running, this will check the output of
        nodetool ring, make sure that gossip and thrift are running, and check
        that nodetool info reports Normal mode.  If these tests do not pass
        within the timeout threshold, it will retry up to
        self.MAX_RESTART_ATTEMPTS times to restart.  If after meeting the max
        allowed, it will raise a TimeoutException.
        """

        if retry:
            self.logger.info("Attempting to start again (%s of %s)" % (self.current_attempt-1, self.MAX_RESTART_ATTEMPTS))
            print("Cassandra failed to start - attempting to start again (%s of %s)" % (self.current_attempt-1, self.MAX_RESTART_ATTEMPTS))

        if instances is None:
            instances = self.get_instances()

        for instance in instances:
            with settings(host_string=instance.public_dns_name, warn_only=True): #, hide("everything"):
                errors = -1
                self.logger.info("Starting Cassandra service on %s..." % instance.id)

                while True:
                    try:
                        # check to see if cassandra is running

                        if self.is_running(instance):
                            self.logger.info("Cassandra is running.")
                            break

                        # start it if this is the first time
                        if errors < 0:
                            self.logger.info("Cassandra is not running. Attempting to start now...")
                            print("Cassandra is not running. Attempting to start now...")
                            exec_command("service cassandra start", pty=False)
                        elif errors >= 5:
                            #tail = sudo("tail -n 50 /var/log/cassandra/output.log")
                            #self.logger.error(tail)
                            raise RuntimeError("Unable to start cassandra. Check the logs for more information.")
                        self.logger.info("Error detecting Cassandra status...will try again in 3 seconds.")
                        errors += 1
                        time.sleep(3)

                    except SystemExit, e:
                        self.logger.error(str(e))

        # test connection
        self.logger.debug("Testing connection to each Cassandra instance...")

        temp_instances = instances[:]
        while len(temp_instances) > 0:
            instance = temp_instances[-1]

            with settings(host_string=instance.public_dns_name, warn_only=True), hide("everything"):
                # does the ring look ok?
                ring_retcode = self._validate_ring(instance)

                # is gossip running?
                gossip_retcode = exec_command("nodetool -h %s info | grep Gossip | grep true" % instance.private_dns_name).return_code

                # are the netstats looking ok?
                netstats_retcode = exec_command("nodetool -h %s netstats | grep 'Mode: NORMAL'" % instance.private_dns_name).return_code

                # is thrift running?
                thrift_retcode = exec_command("/bin/netstat -an | grep 9160").return_code

                if ring_retcode == 0 and gossip_retcode == 0 and netstats_retcode == 0 and thrift_retcode == 0:
                    temp_instances.pop()
                else:
                    if ring_retcode != 0:
                        self.logger.warn("Return code for 'nodetool ring' on '%s': %d" % (temp_instances[-1].id, ring_retcode))
                    if gossip_retcode != 0:
                        self.logger.warn("Return code for 'nodetool info | grep Gossip' on '%s': %d" % (temp_instances[-1].id, gossip_retcode))
                    if netstats_retcode != 0:
                        self.logger.warn("Return code for 'nodetool netstats | grep Normal' on '%s': %d" % (temp_instances[-1].id, netstats_retcode))
                    if thrift_retcode != 0:
                        self.logger.warn("Return code for 'netstat | grep 9160' (thrift) on '%s': %d" % (temp_instances[-1].id, thrift_retcode))

                    time.sleep(3)

        # print ring after everything started
        if print_ring:
            print self.print_ring(instances[0])

        self.logger.debug("Startup complete.")

    def stop_cassandra(self, instances=None):
        if instances is None:
          instances = self.get_instances()

        for instance in instances:
            self.logger.info("Stopping Cassandra on %s" % instance.id)
            with settings(host_string=instance.public_dns_name, warn_only=True), hide("everything"):
                result = exec_command("service cassandra stop")
                self.logger.info(result)

        self.logger.debug("Shutdown complete.")

    def get_cassandra_pid(self, instance):
        with settings(host_string=instance.public_dns_name, warn_only=True):
            pid = exec_command("cat /var/run/cassandra.pid")
            if pid.failed:
                return None
            return pid

    def is_running(self, instance):
        with settings(host_string=instance.public_dns_name), hide("everything"):
            return "is running" in exec_command("service cassandra status")

        #pid = self.get_cassandra_pid(instance)
        #if pid is None:
        #    return False
        #
        #with settings(host_string=instance.public_dns_name, warn_only=True):
        #    return exec_command("ps auxw | grep -v grep | grep %s" % pid).succeeded
        

    def get_cassandra_home(self, instance):
        with settings(host_string=instance.public_dns_name, warn_only=True):
            return exec_command("echo $CASSANDRA_HOME")
        

########NEW FILE########
__FILENAME__ = cli
import sys
import os
import logging
import urllib

from cloud.plugin import CLIPlugin
from cloud.plugin import BASIC_OPTIONS
from cloud.service import InstanceTemplate
from cloud.util import log_cluster_action
from optparse import make_option
from prettytable import PrettyTable

class HadoopServiceCLI(CLIPlugin):
    USAGE = """Hadoop service usage: CLUSTER COMMAND [OPTIONS]
where COMMAND and [OPTIONS] may be one of:
            
                               HADOOP COMMANDS
  ----------------------------------------------------------------------------------
  launch-master                       launch or find a master in CLUSTER
  launch-slaves NUM_SLAVES            launch NUM_SLAVES slaves in CLUSTER
  terminate-dead-nodes                find and terminate dead nodes in CLUSTER
  start-hadoop                        starts all processes on namenode and datanodes
  stop-hadoop                         stops all processes on namenode and datanodes
  send-config-files                   sends the given config files to each node and
                                        overwrites the existing file in the hadoop
                                        conf directory (BE CAREFUL!)
  get-config-files                    gets the given config files from the namenode
                                        and stores them in the cwd 

                               HBASE COMMANDS
  ----------------------------------------------------------------------------------
  start-hbase                         starts processes on namenode and datanodes
  stop-hbase                          stops processes on namenode and datanodes
  send-hbase-config-files             sends the given config files to each node and
                                        overwrites the existing file in the hadoop
                                        conf directory (BE CAREFUL!)
  get-hbase-config-files              gets the given config files from the namenode
                                        and stores them in the cwd 

                             CLOUDBASE COMMANDS
  ----------------------------------------------------------------------------------
  start-cloudbase                     starts processes on namenode and datanodes
  stop-cloudbase                      stops proceses on namenode and datanodes

                               CLUSTER COMMANDS
  ----------------------------------------------------------------------------------
  details                             list instances in CLUSTER
  launch-cluster NUM_SLAVES           launch a master and NUM_SLAVES slaves in 
                                        CLUSTER
  terminate-cluster                   terminate all instances in CLUSTER
  login                               log in to the master in CLUSTER over SSH
  proxy                               start a SOCKS proxy on localhost into the
                                        CLUSTER

                               STORAGE COMMANDS
  ----------------------------------------------------------------------------------
  list-storage                        list storage volumes for CLUSTER
  create-storage ROLE NUM_INSTANCES   create volumes for NUM_INSTANCES instances of
    SPEC_FILE                           type ROLE for CLUSTER, using SPEC_FILE
  delete-storage                      delete all storage volumes for CLUSTER
"""
    
    def __init__(self):
        super(HadoopServiceCLI, self).__init__()
 
    def execute_command(self, argv, options_dict):
        if len(argv) < 2:
            self.print_help()

        self._cluster_name = argv[0]
        self._command_name = argv[1]

        # strip off the cluster name and command from argv
        argv = argv[2:]

        # get spot configuration
        self._spot_config = {
                "spot_cluster": True if os.environ.get("SPOT_CLUSTER", options_dict.get("spot_cluster", "false")).lower() == "true" else False,
                "master_spot": True if options_dict.get("master_spot", "false").lower() == "true" else False,
                "max_price": options_dict.get("max_price", None),
                "launch_group": options_dict.get("launch_group", None),
            }

        # handle all known commands and error on an unknown command
        if self._command_name == "details":
            self.print_instances()

        elif self._command_name == "simple-details":
            self.simple_print_instances(argv, options_dict)

        elif self._command_name == "proxy":
            self.proxy(argv, options_dict)

        elif self._command_name == "terminate-cluster":
            self.terminate_cluster(argv, options_dict)

        elif self._command_name == "launch-cluster":        
            self.launch_cluster(argv, options_dict)

        elif self._command_name == "terminate-dead-nodes":
            self.terminate_dead_nodes(argv, options_dict)

        elif self._command_name == "launch-master":
            self.launch_master(argv, options_dict)

        elif self._command_name == "launch-slaves":
            self.launch_slaves(argv, options_dict)

        elif self._command_name == "start-hadoop":
            self.start_hadoop(argv, options_dict)

        elif self._command_name == "stop-hadoop":
            self.stop_hadoop(argv, options_dict)

        elif self._command_name == "start-hbase":
            self.start_hbase(argv, options_dict)

        elif self._command_name == "stop-hbase":
            self.stop_hbase(argv, options_dict)

        elif self._command_name == "send-config-files":
            self.send_config_files(argv, options_dict)

        elif self._command_name == "get-config-files":
            self.get_config_files(argv, options_dict)

        elif self._command_name == "send-hbase-config-files":
            self.send_hbase_config_files(argv, options_dict)

        elif self._command_name == "get-hbase-config-files":
            self.get_hbase_config_files(argv, options_dict)

        elif self._command_name == "login":
            self.login(argv, options_dict)

        elif self._command_name == "run-command":
            self.run_command(argv, options_dict)

        elif self._command_name == "transfer-files":
            self.transfer_files(argv, options_dict)

        elif self._command_name == "create-storage":
            self.create_storage(argv, options_dict)

        elif self._command_name == "delete-storage":
            self.delete_storage(argv, options_dict)

        elif self._command_name == "list-storage":
            self.print_storage()

        elif self._command_name == "start-cloudbase":
            self.start_cloudbase(argv, options_dict)

        elif self._command_name == "stop-cloudbase":
            self.stop_cloudbase(argv, options_dict)
            
        else:
            self.print_help()

    def launch_cluster(self, argv, options_dict):
        """
        """

        expected_arguments = ["NUM_SLAVES"]
        opt, args = self.parse_options(self._command_name,
                                       argv,
                                       expected_arguments=expected_arguments)
        opt.update(options_dict)

        # if PROVIDER is set in the environment that takes precedence over
        # anything in the clusters.cfg; hbase is the default if nothing is set
        provider = os.environ.get("PROVIDER", opt.get("provider", "hbase")).lower()

        # default for spot clusters is for the master to NOT be spot; munging
        # some things around here if the opposite is specified
        spot_cluster_orig = self._spot_config["spot_cluster"]
        if spot_cluster_orig and self._spot_config["master_spot"]:
            self._spot_config["spot_cluster"] = True
        else:
            self._spot_config["spot_cluster"] = False

        number_of_slaves = int(args[0])
        master_templates = [
            InstanceTemplate(
                (
                    self.service.NAMENODE, 
                    self.service.SECONDARY_NAMENODE, 
                    self.service.JOBTRACKER
                ),
                1,
                opt.get('image_id'),
                opt.get('instance_type'), 
                opt.get('key_name'),
                opt.get('public_key'), 
                opt.get('user_data_file'),
                opt.get('availability_zone'), 
                opt.get('user_packages'),
                opt.get('auto_shutdown'), 
                opt.get('env'),
                opt.get('security_groups'),
                self._spot_config)   # don't want the master to be a spot instance
        ]
        for it in master_templates:
            it.add_env_strings([
                "CLUSTER_SIZE=%d" % (number_of_slaves+1),
                "PROVIDER=%s" % (provider)
            ])

        print "Using %s as the backend datastore" % (provider)

        print "Launching cluster with %d instance(s) - starting master...please wait." % (number_of_slaves+1)
        
        master = self.service.launch_cluster(master_templates, opt.get('client_cidr'), opt.get('config_dir'))

        if master is None:
            print "An error occurred starting the master node. Check the logs for more information."
            sys.exit(1)

        log_cluster_action(opt.get('config_dir'), self._cluster_name,
            "launch-cluster", 1, opt.get("instance_type"),
            provider, "hadoop")

        print "Master now running at %s - starting slaves" % master.public_dns_name

        self._spot_config["spot_cluster"] = spot_cluster_orig

        slave_templates = [
            InstanceTemplate(
                (
                    self.service.DATANODE, 
                    self.service.TASKTRACKER
                ), 
                number_of_slaves,
                opt.get('image_id'),
                opt.get('instance_type'),
                opt.get('key_name'),
                opt.get('public_key'),
                opt.get('user_data_file'),
                opt.get('availability_zone'),
                opt.get('user_packages'),
                opt.get('auto_shutdown'),
                opt.get('env'),
                opt.get('security_groups'),
                self._spot_config)
        ]

        for it in slave_templates:
            it.add_env_strings([
                "CLUSTER_SIZE=%d" % (number_of_slaves+1),
                "NN_HOST=%s" % master.private_dns_name,
                "JT_HOST=%s" % master.private_dns_name,
                "ZOOKEEPER_QUORUM=%s" % master.private_dns_name,
                "PROVIDER=%s" % (provider)
            ])

        print "Launching %d slave instance(s)...please wait." % (number_of_slaves)
        slave = self.service.launch_cluster(slave_templates, opt.get('client_cidr'), opt.get('config_dir'))        
        
        if slave is None:
            print "An error occurred starting the slave nodes.  Check the logs for more details"
            sys.exit(1)
            
        log_cluster_action(opt.get('config_dir'), self._cluster_name,
            "launch-cluster", number_of_slaves, opt.get("instance_type"),
            provider, "hadoop")

        #Once the cluster is up, if the provider is Cloudbase, we need to ensure that Cloudbase has been initialized
        #and launch the servers
        if provider == "cloudbase":

            #log in to the master and run a startup script
            print "Provider is cloudbase - starting cloudbase processes ... please wait"
            self.service.start_cloudbase(options_dict,
                options_dict.get("hadoop_user", "hadoop"), 
                options_dict.get("ssh_user", "root"))
            
        print "Finished - browse the cluster at http://%s/" % master.public_dns_name
 
        self.logger.debug("Startup complete.")

    def launch_master(self, argv, options_dict):
        """Launch the master node of a CLUSTER."""

        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)
        
        provider = opt.get("provider")
        if provider is None:
            provider = "hbase"
        else:
            provider.lower()

        # default for spot clusters is for the master to NOT be spot; munging
        # some things around here if the opposite is specified
        spot_cluster_orig = self._spot_config["spot_cluster"]
        if spot_cluster_orig and self._spot_config["master_spot"]:
            self._spot_config["spot_cluster"] = True
        else:
            self._spot_config["spot_cluster"] = False

        master_templates = [
            InstanceTemplate(
                (
                    self.service.NAMENODE, 
                    self.service.SECONDARY_NAMENODE, 
                    self.service.JOBTRACKER
                ),
                1,
                opt.get('image_id'),
                opt.get('instance_type'), 
                opt.get('key_name'),
                opt.get('public_key'), 
                opt.get('user_data_file'),
                opt.get('availability_zone'), 
                opt.get('user_packages'),
                opt.get('auto_shutdown'), 
                opt.get('env'),
                opt.get('security_groups'),
                self._spot_config)
            ]

        for it in master_templates:
            it.add_env_strings([
                "PROVIDER=%s" % (provider)
            ])

        print "Launching cluster master...please wait." 
        jobtracker = self.service.launch_cluster(master_templates, 
                                                 opt.get('client_cidr'),
                                                 opt.get('config_dir'))

        if jobtracker is None:
            print "An error occurred started the Hadoop service. Check the logs for more information."
            sys.exit(1)

        print "Browse the cluster at http://%s/" % jobtracker.public_dns_name
        self.logger.debug("Startup complete.")

    def launch_slaves(self, argv, options_dict):
        """Launch slave/datanodes in CLUSTER."""

        expected_arguments = ["NUM_SLAVES"]
        opt, args = self.parse_options(self._command_name,
                                       argv,
                                       expected_arguments=expected_arguments)
        opt.update(options_dict)

        provider = opt.get("provider")
        if provider is None:
            provider = "hbase"
        else:
            provider.lower()

        try:
            number_of_slaves = int(args[0])
        except ValueError:
            print("Number of slaves must be an integer")
            return

        instance_templates = [
            InstanceTemplate(
                (
                    self.service.DATANODE, 
                    self.service.TASKTRACKER
                ), 
                number_of_slaves,
                opt.get('image_id'),
                opt.get('instance_type'),
                opt.get('key_name'),
                opt.get('public_key'),
                opt.get('user_data_file'),
                opt.get('availability_zone'),
                opt.get('user_packages'),
                opt.get('auto_shutdown'),
                opt.get('env'),
                opt.get('security_groups'),
                self._spot_config)
            ]

        # @todo - this is originally passed in when creating a cluster from
        # scratch, need to figure out what to do if we're growing a cluster
        #instance_template.add_env_strings([
        #    "CLUSTER_SIZE=%d" % (number_of_slaves+1)
        #])

        print("Launching %s slave%s for %s" % (number_of_slaves, 
            "" if number_of_slaves==1 else "s", self._cluster_name))

        # this is needed to filter the jobtracker/namenode down into
        # hadoop-site.xml for the new nodes
        namenode = self.service.get_namenode()
        jobtracker = self.service.get_jobtracker()
        for instance_template in instance_templates:
            instance_template.add_env_strings([
                "NN_HOST=%s" % namenode.public_dns_name,
                "JT_HOST=%s" % jobtracker.public_dns_name,
                "ZOOKEEPER_QUORUM=%s" % namenode.private_dns_name,
                "PROVIDER=%s" % (provider)
            ])

        # I think this count can be wrong if run too soon after running
        # terminate_dead_nodes
        existing_tasktrackers = self.service.get_tasktrackers()
        num_tasktrackers = len(existing_tasktrackers) if existing_tasktrackers else 0
        self.service.launch_cluster(instance_templates, 
            opt.get('client_cidr'), opt.get('config_dir'),
            num_existing_tasktrackers=num_tasktrackers)

    def start_cloudbase(self, argv, options_dict):
        """Start the various cloudbase processes on the namenode and slave nodes - initialize the cloudbase instance, if necessary"""
        
        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        self.service.start_cloudbase(options_dict,
            options_dict.get("hadoop_user", "hadoop"), 
            options_dict.get("ssh_user", "root"))

    def stop_cloudbase(self, argv, options_dict):
        """Stop the various cloudbase processes on the namenode and slave
        nodes"""
        
        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        self.service.stop_cloudbase(options_dict)
    
    def start_hadoop(self, argv, options_dict):
        """Start the various processes on the namenode and slave nodes"""

        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        print "Starting hadoop..."
        self.service.start_hadoop(options_dict.get("hadoop_user", "hadoop"))

    def stop_hadoop(self, argv, options_dict):
        """Stop the various processes on the namenode and slave nodes"""

        x = "n"
        while True:
            try:
                x = raw_input("Are you sure you want to stop Hadoop? (Y/n) ").lower()
                if x in ["y", "n"]:
                    break
                print "Value must be either y or n. Try again."
            except KeyboardInterrupt:
                x = "n"
                print ""
                break
        
        if x == "n":
            print "Quitting"
            sys.exit(1)

        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        print "Stopping hadoop..."
        self.service.stop_hadoop(options_dict.get("hadoop_user", "hadoop"))

    def start_hbase(self, argv, options_dict):
        """Start the various hbase processes on the namenode and slave nodes"""

        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        print "Starting hbase..."
        self.service.start_hbase(options_dict.get("hadoop_user", "hadoop"))

    def stop_hbase(self, argv, options_dict):
        """Stop the various hbase processes on the namenode and slave nodes"""

        x = "n"
        while True:
            try:
                x = raw_input("Are you sure you want to stop HBase? (Y/n) ").lower()
                if x in ["y", "n"]:
                    break
                print "Value must be either y or n. Try again."
            except KeyboardInterrupt:
                x = "n"
                print ""
                break
        
        if x == "n":
            print "Quitting"
            sys.exit(1)

        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        print "Stopping hbase..."
        self.service.stop_hbase(options_dict.get("hadoop_user", "hadoop"))

    def get_config_files(self, argv, options_dict):
        """
        Gets the given config files from the name node and writes them
        to the local directory.
        """

        opt, args = self.parse_options(self._command_name, argv, expected_arguments=["FILE*"], unbounded_args=True)
        opt.update(options_dict)

        self.service.get_config_files(args, options_dict)

    def send_config_files(self, argv, options_dict):
        """
        Sends the given config file to each node in the cluster, overwriting
        the file located in hadoop/conf directory.
        """

        opt, args = self.parse_options(self._command_name, argv, expected_arguments=["FILE*"], unbounded_args=True)
        opt.update(options_dict)

        self.service.send_config_files(args, options_dict)

    def get_hbase_config_files(self, argv, options_dict):
        """
        Gets the given config files from the hbase master node and 
        writes them to the local directory.
        """

        opt, args = self.parse_options(self._command_name, argv, expected_arguments=["FILE*"], unbounded_args=True)
        opt.update(options_dict)

        self.service.get_hbase_config_files(args, options_dict)

    def send_hbase_config_files(self, argv, options_dict):
        """
        Sends the given config file to each node in the cluster, overwriting
        the file located in hadoop/conf directory.
        """

        opt, args = self.parse_options(self._command_name, argv, expected_arguments=["FILE*"], unbounded_args=True)
        opt.update(options_dict)

        self.service.send_hbase_config_files(args, options_dict)

    def terminate_dead_nodes(self, argv, options_dict):
        """Find and terminate dead nodes in CLUSTER."""

        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS)
        opt.update(options_dict)

        print("Looking for dead nodes in %s" % self._cluster_name)
        dead_nodes = self.service.find_dead_nodes(self._cluster_name, opt)
        if not dead_nodes:
            print("No dead nodes found")
            return 

        print ("Found %s dead nodes" % len(dead_nodes))
        self.service.terminate_nodes(dead_nodes, opt)

    def create_storage(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS,
                                       ["ROLE", "NUM_INSTANCES", "SPEC_FILE"])

        opt.update(options_dict)

        role = args[0]
        number_of_instances = int(args[1])
        spec_file = args[2]

        valid_roles = (self.service.NAMENODE, self.service.DATANODE)
        if role not in valid_roles:
            raise RuntimeError("Role must be one of '%s' or '%s'" % valid_roles)

        self.service.create_storage(role, 
                                    number_of_instances,
                                    opt.get('availability_zone'),
                                    spec_file)
        self.print_storage()
    
    def proxy(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            "No running instances. Aborting."
            sys.exit(1)

        result = self.service.proxy(ssh_options=options_dict.get('ssh_options'),   
                                    instances=instances)

        if result is None:
            print "Unable to create proxy. Check logs for more information."
            sys.exit(1)

        print "Proxy created..."
        print """export HADOOP_CLOUD_PROXY_PID=%s;
echo Proxy pid %s;""" % (result, result)

########NEW FILE########
__FILENAME__ = service
from __future__ import with_statement

import os
import sys
import time
import datetime
import subprocess
import urllib
import tempfile
import socket
import re

from fabric.api import *
from fabric.contrib import files
from fabric.state import output

from cloud.cluster import TimeoutException
from cloud.service import InstanceTemplate
from cloud.plugin import ServicePlugin
from cloud.util import xstr
from cloud.util import url_get
from cloud.decorators import timeout

# fabric output settings
output.running = False
output.stdout = False
output.stderr = False

class HadoopService(ServicePlugin):
    """
        """
    NAMENODE = "nn"
    SECONDARY_NAMENODE = "snn"
    JOBTRACKER = "jt"
    DATANODE = "dn"
    TASKTRACKER = "tt"
    
    def __init__(self):
        super(HadoopService, self).__init__()
    
    def get_roles(self):
        return [self.NAMENODE]
    
    def get_instances(self):
        """
            Return a list of tuples resembling (role_of_instance, instance)
            """
        return self.cluster.get_instances_in_role(self.NAMENODE, "running") + \
            self.cluster.get_instances_in_role(self.DATANODE, "running")
    
    def launch_cluster(self, instance_templates, client_cidr, config_dir, num_existing_tasktrackers=0):
        number_of_tasktrackers = num_existing_tasktrackers
        roles = []
        for it in instance_templates:
            roles.extend(it.roles)
            if self.TASKTRACKER in it.roles:
                number_of_tasktrackers += it.number
        
        singleton_hosts = []
        started_instance_ids = []
        expected_instance_count = sum([it.number for it in instance_templates])
    
        for instance_template in instance_templates:
            self.logger.debug("Launching %d instance(s) with role(s) %s..." % (
                                                                               instance_template.number,
                                                                               str(instance_template.roles),
                                                                               ))
            self.logger.debug("Instance(s) will have extra environment variables: %s" % (
                                                                                         singleton_hosts,
                                                                                         ))
            instance_template.add_env_strings(singleton_hosts)
            instance_ids = self._launch_instances(instance_template)
            
            if instance_template.number == 1:
                if len(instance_ids) != 1:
                    logger.error("Expected a single '%s' instance, but found %s.",
                                 "".join(instance_template.roles),
                                 len(instance_ids))
                    return False
                else:
                    # wait for the instances to start
                    self.cluster.wait_for_instances(instance_ids)
                    instance = self.get_instances()[0]
                    
                    for role in instance_template.roles:
                        singleton_host_env = "%s_HOST=%s" % (
                                                             self._sanitize_role_name(role),
                                                             instance.public_dns_name,
                                                             )
                        singleton_hosts.append(singleton_host_env)
            
            started_instance_ids.extend(instance_ids)
    
        if len(started_instance_ids) != expected_instance_count:
            self.logger.warn("Total number of reported instance ids (%d) " \
                             "does not match total requested number (%d)" % \
                             (len(started_instance_ids), instance_template.number))
    
        self.logger.debug("Waiting for %s instance(s) to start: %s" % \
                          (len(started_instance_ids), ", ".join(started_instance_ids)))
        time.sleep(1)
    
        try:
            self.cluster.wait_for_instances(started_instance_ids)
        except TimeoutException:
            self.logger.error("Timeout while waiting for %d instances to start." % \
                              len(started_instance_ids))
    
        instances = self.get_instances()
        
        self.logger.debug("Instances started: %s" % (str(instances),))
        
        #self._create_client_hadoop_site_file(config_dir)
        self._authorize_client_ports(client_cidr)
        self._attach_storage(roles)
        try:
            self._wait_for_hadoop(number_of_tasktrackers)
        except TimeoutException:
            print "Timeout while waiting for Hadoop to start. Please check logs on" + \
                " cluster."
        return self.get_jobtracker()

    def terminate_nodes(self, nodes, options):
        """Terminate a subset of nodes from a cluster.
            nodes is a list of boto.ec2.instance.Instance objects"""
        
        exclude_hosts = ""
        for node in nodes:
            print("Terminating instance %s ... " % node.id),
            exclude_hosts += node.private_dns_name + "\n"
            node.terminate()
            print("done")
        
        print("Removing nodes from hadoop ..."),
        env.host_string = self.get_namenode().public_dns_name
        env.user = "root"
        env.key_filename = options["private_key"]
        hadoop_home = self.get_hadoop_home(env.key_filename)
        run('echo "%s" > %s/conf/exclude' % (exclude_hosts.strip(), hadoop_home))
        fab_output = run("sudo -u hadoop %s/bin/hadoop dfsadmin -refreshNodes" %
                         hadoop_home)
        fab_output = run("sudo -u hadoop %s/bin/hadoop mradmin -refreshNodes" %
                         hadoop_home)
        print("done")

    def _extract_dfs(self, dfs_output):
        """Clean up and extract some info from dfsadmin output."""
        
        # trim off the top cruft
        dfs_lines = dfs_output.splitlines()
        for line in dfs_lines:
            if line.startswith("---"):
                break
        datanode_lines = dfs_lines[dfs_lines.index(line)+1:]
        dfs_summary = datanode_lines[0]
        
        # now pull out info for each node
        nodes = []
        node_info_lines = "\n".join(datanode_lines[2:]).split("\n\n\n")
        for node in node_info_lines:
            node_info = [{line.split(": ")[0].strip().lower():line.split(": ")[1].strip()}
                         for line in node.splitlines()]
            nodes.append(
                         {"private_ip": node_info[0]["name"].split(":")[0],
                         "last_contact": time.strptime(
                                                       node_info[8]["last contact"],"%a %b %d %H:%M:%S %Z %Y")})
        
        return nodes
    
    def find_dead_nodes(self, cluster_name, options):
        """Find a list of nodes that are dead."""
        instances = self.get_instances()
        name_nodes = self.cluster.get_instances_in_role(self.NAMENODE, "running")
        if not name_nodes:
            print("No name node found.")
            return False
        
        env.host_string = name_nodes[0].public_dns_name
        env.user = "root"
        env.key_filename = options["private_key"]
        fab_output = run("sudo -u hadoop %s/bin/hadoop dfsadmin -report" %
                         self.get_hadoop_home(env.key_filename))
        
        # list of hdfs nodes
        dfs_nodes = self._extract_dfs(fab_output)
        dead_nodes = []
        for node in dfs_nodes:
            
            # hadoop appears to consider a node dead if it loses the heartbeat
            # for 630 seconds (10.5 minutes)
            time_lapse = (datetime.timedelta(seconds=time.mktime(time.gmtime()))
                          - datetime.timedelta(seconds=time.mktime(node["last_contact"])))
            if time_lapse.seconds > 630:
                for instance in instances:
                    if instance.private_ip_address == node["private_ip"]:
                        dead_nodes.append(instance)
                        break
        
        return dead_nodes
    
    def _sanitize_role_name(self, role):
        """
            Replace characters in role name with ones allowed in bash variable names
            """
        return role.replace('+', '_').upper()
    
    def get_hadoop_home(self, private_key):
        """Find out what HADOOP_HOME is on the namenode.  You must provide the
            private_key necessary to connect to the namenode."""
        
        if not private_key:
            return None
        
        with settings(host_string=self.get_namenode().public_dns_name):
            env.user = "root"
            env.key_filename = private_key
            fab_output = run("echo $HADOOP_HOME")
            return fab_output.rstrip() if fab_output else None
    
    def get_hbase_home(self, private_key):
        """Find out what HBASE_HOME is on the namenode.  You must provide the
            private_key necessary to connect to the namenode."""
        
        if not private_key:
            return None
        
        with settings(host_string=self.get_namenode().public_dns_name):
            env.user = "root"
            env.key_filename = private_key
            fab_output = run("echo $HBASE_HOME")
            return fab_output.rstrip() if fab_output else None
    
    def get_namenode(self):
        instances = self.cluster.get_instances_in_role(self.NAMENODE, "running")
        if not instances:
            return None
        return instances[0]
    
    def get_jobtracker(self):
        instances = self.cluster.get_instances_in_role(self.JOBTRACKER, "running")
        if not instances:
            return None
        return instances[0]
    
    def get_datanodes(self):
        instances = self.cluster.get_instances_in_role(self.DATANODE, "running")
        if not instances:
            return None
        return instances

    def get_tasktrackers(self):
        instances = self.cluster.get_instances_in_role(self.TASKTRACKER, "running")
        if not instances:
            return None
        return instances

    def _create_client_hadoop_site_file(self, config_dir):
        namenode = self.get_namenode()
        jobtracker = self.get_jobtracker()
        cluster_dir = os.path.join(config_dir, ".hadoop", self.cluster.name)
        aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        
        if not os.path.exists(cluster_dir):
            os.makedirs(cluster_dir)
        
        params = {
            'namenode': namenode.public_dns_name,
            'jobtracker': jobtracker.public_dns_name,
            'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY']
        }
        self.logger.debug("hadoop-site.xml params: %s" % str(params))
        
        with open(os.path.join(cluster_dir, 'hadoop-site.xml'), 'w') as f:
            f.write("""<?xml version="1.0"?>
                <?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
                <!-- Put site-specific property overrides in this file. -->
                <configuration>
                <property>
                <name>hadoop.job.ugi</name>
                <value>root,root</value>
                </property>
                <property>
                <name>fs.default.name</name>
                <value>hdfs://%(namenode)s:8020/</value>
                </property>
                <property>
                <name>mapred.job.tracker</name>
                <value>%(jobtracker)s:8021</value>
                </property>
                <property>
                <name>hadoop.socks.server</name>
                <value>localhost:6666</value>
                </property>
                <property>
                <name>hadoop.rpc.socket.factory.class.default</name>
                <value>org.apache.hadoop.net.SocksSocketFactory</value>
                </property>
                <property>
                <name>fs.s3.awsAccessKeyId</name>
                <value>%(aws_access_key_id)s</value>
                </property>
                <property>
                <name>fs.s3.awsSecretAccessKey</name>
                <value>%(aws_secret_access_key)s</value>
                </property>
                <property>
                <name>fs.s3n.awsAccessKeyId</name>
                <value>%(aws_access_key_id)s</value>
                </property>
                <property>
                <name>fs.s3n.awsSecretAccessKey</name>
                <value>%(aws_secret_access_key)s</value>
                </property>
                </configuration>""" % params)

    def _authorize_client_ports(self, client_cidrs=[]):
        if not client_cidrs:
            self.logger.debug("No client CIDRs specified, using local address.")
            client_ip = url_get('http://checkip.amazonaws.com/').strip()
            client_cidrs = ("%s/32" % client_ip,)
        self.logger.debug("Client CIDRs: %s", client_cidrs)
        
        namenode = self.get_namenode()
        jobtracker = self.get_jobtracker()
        
        for client_cidr in client_cidrs:
            # Allow access to port 80 on namenode from client
            self.cluster.authorize_role(self.NAMENODE, 80, 80, client_cidr)
            
            # Allow access to jobtracker UI on master from client
            # (so we can see when the cluster is ready)
            self.cluster.authorize_role(self.JOBTRACKER, 50030, 50030, client_cidr)
        
        # Allow access to namenode and jobtracker via public address from each other
        namenode_ip = socket.gethostbyname(namenode.public_dns_name)
        jobtracker_ip = socket.gethostbyname(jobtracker.public_dns_name)
        self.cluster.authorize_role(self.NAMENODE, 8020, 8020, "%s/32" % namenode_ip)
        self.cluster.authorize_role(self.NAMENODE, 8020, 8020, "%s/32" % jobtracker_ip)
        self.cluster.authorize_role(self.JOBTRACKER, 8021, 8021, "%s/32" % namenode_ip)
        self.cluster.authorize_role(self.JOBTRACKER, 8021, 8021,
                                    "%s/32" % jobtracker_ip)

    @timeout(600)
    def _wait_for_hadoop(self, number):
        wait_time = 3
        jobtracker = self.get_jobtracker()
        if not jobtracker:
            self.logger.debug("No jobtracker found")
            return
        
        self.logger.debug("Waiting for jobtracker to start...")
        previous_running = 0
        while True:
            try:
                actual_running = self._number_of_tasktrackers(jobtracker.public_dns_name, 1)
                break
            except IOError:
                pass
            self.logger.debug("Sleeping for %d seconds..." % wait_time)
            time.sleep(wait_time)
        if number > 0:
            self.logger.debug("Waiting for %d tasktrackers to start" % number)
            while actual_running < number:
                self.logger.debug("actual_running: %s" % actual_running)
                self.logger.debug("number: %s" % number)
                try:
                    actual_running = self._number_of_tasktrackers(jobtracker.public_dns_name, 5, 2)
                    self.logger.debug("Sleeping for %d seconds..." % wait_time)
                    time.sleep(wait_time)
                    previous_running = actual_running
                except IOError:
                    pass
            self.logger.debug("actual_running = number (%s = %s)" % (actual_running, number))

    # The optional ?type=active is a difference between Hadoop 0.18 and 0.20
    _NUMBER_OF_TASK_TRACKERS = re.compile(r'<a href="machines.jsp(?:\?type=active)?">(\d+)</a>')

    def _number_of_tasktrackers(self, jt_hostname, timeout, retries=0):
        url = "http://%s:50030/jobtracker.jsp" % jt_hostname
        jt_page = url_get(url, timeout, retries)
        m = self._NUMBER_OF_TASK_TRACKERS.search(jt_page)
        if m:
            return int(m.group(1))
        return 0

    def proxy(self, ssh_options, instances=None):
        if instances is None:
            return None
        
        namenode = self.get_namenode()
        if namenode is None:
            self.logger.error("No namenode running. Aborting.")
            return None

        options = '-o "ConnectTimeout 10" -o "ServerAliveInterval 60" ' \
            '-N -D 6666'
        process = subprocess.Popen('ssh %s %s %s' % (
                                                     xstr(ssh_options),
                                                     options,
                                                     namenode.public_dns_name
                                                     ),
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True)

        return process.pid
    
    def _daemon_control(self, instance, service, daemon, action, as_user="hadoop"):
        #command = "su -s /bin/bash - %s -c \"%s-daemon.sh %s %s\"" % (as_user, service, action, daemon)
        #ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
        #subprocess.call(ssh_command, shell=True)
        with settings(host_string=instance.public_dns_name): #hide("everything"):
            #print sudo("su -s /bin/bash - %s -c '%s-daemon.sh %s %s'" % (as_user, service, action, daemon))
            print sudo("%s-daemon.sh %s %s" % (service, action, daemon), user=as_user)
    
    def stop_hadoop(self, as_user="hadoop"):
        namenode = self.get_namenode()
        if namenode is None:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        datanodes = self.get_datanodes()
        if datanodes is None:
            self.logger.error("No datanodes running. Aborting.")
            return None
        
        # kill processes on data node
        i = 1
        for datanode in datanodes:
            print "Stopping datanode #%d processes..." % i
            self._daemon_control(datanode, "hadoop", "tasktracker", "stop", as_user=as_user)
            self._daemon_control(datanode, "hadoop", "datanode", "stop", as_user=as_user)
            i += 1
        
        # kill namenode processes
        print "Stopping namenode processes..."
        self._daemon_control(namenode, "hadoop", "jobtracker", "stop", as_user=as_user)
        self._daemon_control(namenode, "hadoop", "secondarynamenode", "stop", as_user=as_user)
        self._daemon_control(namenode, "hadoop", "namenode", "stop", as_user=as_user)
    
    def start_hadoop(self, as_user="hadoop"):
        namenode = self.get_namenode()
        if namenode is None:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        datanodes = self.get_datanodes()
        if datanodes is None:
            self.logger.error("No datanodes running. Aborting.")
            return None
        
        # start namenode processes
        print "Starting namenode processes..."
        
        # make sure PID directory exists and permissions are right
        with settings(host_string=namenode.public_dns_name):
            sudo("mkdir -p /var/run/hadoop")
            sudo("chown -R %s:%s /var/run/hadoop" % (as_user, as_user))
        
        self._daemon_control(namenode, "hadoop", "jobtracker", "start", as_user=as_user)
        self._daemon_control(namenode, "hadoop", "secondarynamenode", "start", as_user=as_user)
        self._daemon_control(namenode, "hadoop", "namenode", "start", as_user=as_user)
        
        # start processes on data node
        i = 1
        for datanode in datanodes:
            print "Starting datanode #%d processes..." % i
            
            # make sure PID directory exists and permissions are right
            with settings(host_string=datanode.public_dns_name), hide("everything"):
                sudo("mkdir -p /var/run/hadoop")
                sudo("chown -R %s:%s /var/run/hadoop" % (as_user, as_user))
            
            self._daemon_control(datanode, "hadoop", "tasktracker", "start", as_user=as_user)
            self._daemon_control(datanode, "hadoop", "datanode", "start", as_user=as_user)
            i += 1
    
    def stop_hbase(self, as_user="hadoop"):
        namenode = self.get_namenode()
        if namenode is None:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        datanodes = self.get_datanodes()
        if datanodes is None:
            self.logger.error("No datanodes running. Aborting.")
            return None
        
        # kill processes on data node
        i = 1
        for datanode in datanodes:
            print "Stopping regionserver #%d processes..." % i
            print "user = %s" % as_user
            self._daemon_control(datanode, "hbase", "regionserver", "stop", as_user=as_user)
            i += 1
        
        # kill namenode processes
        print "Stopping namenode processes..."
        self._daemon_control(namenode, "hbase", "zookeeper", "stop", as_user=as_user)
        self._daemon_control(namenode, "hbase", "master", "stop", as_user=as_user)
    
    def start_hbase(self, as_user="hadoop"):
        namenode = self.get_namenode()
        if namenode is None:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        datanodes = self.get_datanodes()
        if datanodes is None:
            self.logger.error("No datanodes running. Aborting.")
            return None
        
        # start namenode processes
        print "Starting namenode processes..."
        
        # make sure PID directory exists and permissions are right
        #with settings(host_string=namenode.public_dns_name):
        #    sudo("mkdir -p /var/run/hadoop")
        #    sudo("chown -R %s:%s /var/run/hadoop" % (as_user, as_user))
        
        self._daemon_control(namenode, "hbase", "zookeeper", "start", as_user=as_user)
        self._daemon_control(namenode, "hbase", "master", "start", as_user=as_user)
        
        # start processes on data node
        i = 1
        for datanode in datanodes:
            print "Starting datanode #%d processes..." % i
            
            # make sure PID directory exists and permissions are right
            #with settings(host_string=datanode.public_dns_name), hide("everything"):
            #    sudo("mkdir -p /var/run/hadoop")
            #    sudo("chown -R %s:%s /var/run/hadoop" % (as_user, as_user))
            
            self._daemon_control(datanode, "hbase", "regionserver", "start", as_user=as_user)
            i += 1
    
    def _wrap_user(self, cmd, as_user):
        """Wrap a command with the proper sudo incantation to run as as_user"""
        return 'sudo -i -u %(as_user)s %(cmd)s' % locals()
    
    def _create_tempfile(self, content):
        """Create a tempfile, and fill it with content, return the tempfile
            object for closing when done."""
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write(content)
        tmpfile.file.flush()
        return tmpfile
    
    def start_cloudbase(self, options, as_user="hadoop", ssh_user="root"):
        
        namenode = self.get_namenode()
        if not namenode:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        datanodes = self.get_datanodes()
        if not datanodes:
            self.logger.error("No datanodes running. Aborting.")
            return None
        
        # get list of slaves for the slaves file
        slaves = "\n".join([dn.public_dns_name for dn in datanodes])
        
        # fabric configuration
        env.key_filename = options.get("private_key", "--")
        if env.key_filename == "--":
            print("Option private_key not found, unable to start cloudbase")
            return False
        env.user = ssh_user
        env.disable_known_hosts = True
        
        print("Updating ssh keys and master/slave config files...")
        
        # start namenode processes
        env.host_string = namenode.public_dns_name
        
        # create keypair - but only copy it to the slaves if it's new
        ssh_dir = "/home/%s/.ssh" % as_user
        key_filename = "%s/id_rsa" % ssh_dir
        auth_file = "%s/authorized_keys" % ssh_dir
        ssh_config = "%s/config" % ssh_dir
        ssh_cmd = ("function f() { mkdir -p /home/%(as_user)s/.ssh; "
                   "if [ ! -f %(key_filename)s ]; then "
                   "ssh-keygen -f %(key_filename)s -N '' -q; else return 1; fi; }; "
                   "f" % locals())
        
        tmpfile = self._create_tempfile(ssh_cmd)
        
        with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
            
            # dump ssh_cmd to a temp file
            temp_file = run(self._wrap_user("mktemp", ssh_user))
            put(tmpfile.name, temp_file.stdout)
            run('sudo chmod 755 %(temp_file)s' % locals())
            fab_output = run(self._wrap_user('%(temp_file)s' % locals(), as_user))
            sudo("rm %s" % temp_file.stdout)
            
            if fab_output.return_code:
                self.logger.debug("Using existing keypair")
                copy_keyfile = False
            else:
                self.logger.debug("Creating new keypair")
                # piping output into tee b/c redirecting in the original sudo
                # command doesn't work consistently across various configurations
                run(self._wrap_user("cat %(key_filename)s.pub | sudo -i -u %(as_user)s tee -a %(auth_file)s" % locals(), as_user))
                run(self._wrap_user("echo StrictHostKeyChecking=no | sudo -i -u %(as_user)s tee -a %(ssh_config)s" % locals(), as_user))
                copy_keyfile = True
                keypair = run(self._wrap_user("cat %(key_filename)s" % locals(), as_user))
                keypair_pub = run(self._wrap_user("cat %(key_filename)s.pub" % locals(), as_user))
                
                # once everything's inplace, set the owner to as_user
                sudo("sudo chown -R %(as_user)s:%(as_user)s %(ssh_dir)s" % locals())
        
        tmpfile.close()
        cb_running=-1
        cb_alive_cmd = "ps aux | grep 'cloudbase\.' | wc -l"
        print "Starting cloudbase..."
        
        while cb_running!=1:
            if cb_running==0:
                print "Cloudbase still not fully up, trying again..."
            
            fab_output = run(cb_alive_cmd)
            
            cb_running=1
            if fab_output != "0":
                self.logger.info("Cloudbase already running on master %s" % env.host_string)
            else:
                cb_running=0
                self.logger.info("Cloudbase not running on master %s, setting up" % env.host_string)
                self.logger.info("Updating the master slaves file (%s)" % slaves)
                sudo('echo "%s" > /usr/local/cloudbase/conf/slaves' % slaves)
                
                self.logger.debug("Initializing cloudbase")
                run(self._wrap_user("/usr/bin/drsi-init-master.sh", as_user))
            
            # start processes on data node
            for i, datanode in enumerate(datanodes):
                
                env.host_string = datanode.public_dns_name
                
                if copy_keyfile:
                    
                    run(self._wrap_user("mkdir -p /home/%s/.ssh" % as_user, as_user))
                    
                    temp_keyfile = self._create_tempfile(keypair)
                    put(temp_keyfile.name, key_filename, use_sudo=True)
                    temp_keyfile.close()
                    temp_pubfile = self._create_tempfile(keypair_pub)
                    put(temp_pubfile.name, "%s.pub" % key_filename, use_sudo=True)
                    temp_pubfile.close()
                    
                    cmd = ('chmod 600 %(key_filename)s && '
                           'cat %(key_filename)s.pub >> %(auth_file)s' % locals())
                    sudo(cmd)
                    run(self._wrap_user("echo StrictHostKeyChecking=no | sudo -i -u %(as_user)s tee -a %(ssh_config)s" % locals(), as_user))
                    # once everything's inplace, set the owner to as_user
                    fab_output = run("sudo chown -R %(as_user)s:%(as_user)s %(ssh_dir)s" % locals())
                
                fab_output = run(cb_alive_cmd)
                if fab_output != "0":
                    self.logger.info("Cloudbase already running on datanode %s" % env.host_string)
                else:
                    cb_running=0
                    self.logger.info("Cloudbase not running on datanode %s, setting up" % env.host_string)
                    self.logger.info("Updating the datanode slaves file (%s)" % slaves)
                    sudo('echo "%s" > /usr/local/cloudbase/conf/slaves' % slaves)
            
                #the perception is that CB is running, but it is possible the INIT was done improperly, check it
                if cb_running==1:
                    fab_output = run("echo tables | /usr/local/cloudbase/bin/cbshell -u root -p cloudbase")
                    
                    if "cloudbase.core.client.CBSecurityException: Error BAD_CREDENTIALS - Username or Password is Invalid" in fab_output:
                        cb_running=0
                        
                        #stop CB since its install is broken
                        self.stop_cloudbase(options)
                        
                        #init was not proper, delete old install
                        self.logger.info("Recreating the cloudbase install, since it appears broken")
                        cmd = "sudo -u hadoop hadoop fs -rmr /cloudbase"
                        fab_output = run(cmd)
                        self.logger.info("Removing old cloudbase install: %s" % fab_output)
                        
                        #recreate CB install by reinitializing
                        run(self._wrap_user("/usr/bin/drsi-init-master.sh overwrite", as_user))
                        self.logger.info("Reinitializing cloudbase: %s" % fab_output)

            
            env.host_string = namenode.public_dns_name
            self.logger.info("Starting Cloudbase on master: %s" % env.host_string)
            run(self._wrap_user("/usr/local/cloudbase/bin/start-all.sh", as_user))
            time.sleep(60) #wait interval to allow CB to initialize
        
        print "Cloudbase successfully started"
    
    def stop_cloudbase(self, options):
        """Stop cloudbase processes."""
        
        # just killing the pids associated with cloudbase (vs using stop-all.sh
        # which actually stops all of the hadoop processes as well)
        cmd = "ps aux | grep 'cloudbase\.' | awk '{print $2}' | xargs kill"
        
        namenode = self.get_namenode()
        if not namenode:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        datanodes = self.get_datanodes()
        if not datanodes:
            self.logger.error("No datanodes running. Aborting.")
            return None
        
        env.key_filename = options.get("private_key", "--")
        if env.key_filename == "--":
            print("Option private_key not found, unable to start cloudbase")
            return False
        env.user = options.get("ssh_user", "root")
        env.disable_known_hosts = True
        env.warn_only = True
        
        print("Stopping cloudbase on %s datanode%s" % (len(datanodes),
                                                       "s" if len(datanodes) > 1 else ""))
        for datanode in datanodes:
            env.host_string = datanode.public_dns_name
            with hide("running", "stdout", "stderr", "warnings"):
                fab_output = sudo(cmd)
            if fab_output.return_code == 123:
                print("  No cloudbase processes on %s" % env.host_string)
        
        print("Stopping cloudbase on the masternode")
        env.host_string = namenode.public_dns_name
        with hide("running", "stdout", "stderr", "warnings"):
            fab_output = sudo(cmd)
        if fab_output.return_code == 123:
            print("  No cloudbase processes on %s" % env.host_string)

    def get_config_files(self, file_paths, options):
        env.user = "root"
        env.key_filename = options["private_key"]
        hadoop_home = self.get_hadoop_home(env.key_filename)
        conf_path = os.path.join(hadoop_home, "conf")
        
        print "Downloading %d file(s) from namenode..." % len(file_paths)
        with settings(host_string=self.get_namenode().public_dns_name):
            for file_path in file_paths:
                get(os.path.join(conf_path, file_path))
        print "Done."
    
    def send_config_files(self, file_paths, options):
        hosts = [i.public_dns_name for i in self.get_instances()]
        if len(hosts) == 0:
            print "No instances running. Aborting"
            return None
        
        env.user = options.get("ssh_user")
        env.key_filename = options["private_key"]
        hadoop_home = self.get_hadoop_home(env.key_filename)
        conf_path = os.path.join(hadoop_home, "conf")
        
        print "Uploading %d file(s) to %d node(s)..." % (len(file_paths), len(hosts))
        
        for h in hosts:
            with settings(host_string=h):
                for file_path in file_paths:
                    put(file_path, conf_path)
        
        print "Done. Upload location: %s" % conf_path
    
    def get_hbase_config_files(self, file_paths, options):
        env.user = "root"
        env.key_filename = options["private_key"]
        hbase_home = self.get_hbase_home(env.key_filename)
        conf_path = os.path.join(hbase_home, "conf")
        
        print "Downloading %d file(s) from master..." % len(file_paths)
        with settings(host_string=self.get_namenode().public_dns_name):
            for file_path in file_paths:
                get(os.path.join(conf_path, file_path))
        print "Done."
    
    def send_hbase_config_files(self, file_paths, options):
        hosts = [i.public_dns_name for i in self.get_instances()]
        if len(hosts) == 0:
            print "No instances running. Aborting"
            return None
        
        env.user = "root"
        env.key_filename = options["private_key"]
        hbase_home = self.get_hbase_home(env.key_filename)
        conf_path = os.path.join(hbase_home, "conf")
        
        print "Uploading %d file(s) to %d node(s)..." % (len(file_paths), len(hosts))
        
        for h in hosts:
            with settings(host_string=h):
                for file_path in file_paths:
                    put(file_path, conf_path)
        
        print "Done. Upload location: %s" % conf_path

########NEW FILE########
__FILENAME__ = cli
import sys
import logging
import urllib

from cloud.plugin import CLIPlugin
from cloud.plugin import BASIC_OPTIONS
from cloud.service import InstanceTemplate
from optparse import make_option
from prettytable import PrettyTable

class HadoopCassandraServiceCLI(CLIPlugin):
    USAGE = """Hadoop service usage: CLUSTER COMMAND [OPTIONS]
where COMMAND and [OPTIONS] may be one of:
            
                               HADOOP COMMANDS
  ----------------------------------------------------------------------------------
  launch-master                       launch or find a master in CLUSTER
  launch-slaves NUM_SLAVES            launch NUM_SLAVES slaves in CLUSTER

                               CASSANDRA COMMANDS
  ----------------------------------------------------------------------------------
  start-cassandra                     starts the cassandra service on all nodes
  stop-cassandra                      stops the cassandra service on all nodes
  print-ring                          displays the cluster's ring information

                               CLUSTER COMMANDS
  ----------------------------------------------------------------------------------
  details                             list instances in CLUSTER
  launch-cluster NUM_SLAVES           launch a master and NUM_SLAVES slaves in 
                                        CLUSTER
  terminate-cluster                   terminate all instances in CLUSTER
  login                               log in to the master in CLUSTER over SSH
  proxy                               start a SOCKS proxy on localhost into the
                                        CLUSTER

                               STORAGE COMMANDS
  ----------------------------------------------------------------------------------
  list-storage                        list storage volumes for CLUSTER
  create-storage ROLE NUM_INSTANCES   create volumes for NUM_INSTANCES instances of
    SPEC_FILE                           type ROLE for CLUSTER, using SPEC_FILE
  delete-storage                      delete all storage volumes for CLUSTER
"""
    
    def __init__(self):
        super(HadoopCassandraServiceCLI, self).__init__()
 
    def execute_command(self, argv, options_dict):
        if len(argv) < 2:
            self.print_help()

        self._cluster_name = argv[0]
        self._command_name = argv[1]

        # strip off the cluster name and command from argv
        argv = argv[2:]

        # handle all known commands and error on an unknown command
        if self._command_name == "details":
            self.print_instances()

        elif self._command_name == "simple-details":
            self.simple_print_instances(argv, options_dict)

        elif self._command_name == "proxy":
            self.proxy(argv, options_dict)

        elif self._command_name == "terminate-cluster":
            self.terminate_cluster(argv, options_dict)

        elif self._command_name == "launch-cluster":
            self.launch_cluster(argv, options_dict)

        elif self._command_name == "login":
            self.login(argv, options_dict)

        elif self._command_name == "run-command":
            self.run_command(argv, options_dict)

        elif self._command_name == "transfer-files":
            self.transfer_files(argv, options_dict)

        elif self._command_name == "create-storage":
            self.create_storage(argv, options_dict)

        elif self._command_name == "delete-storage":
            self.delete_storage(argv, options_dict)

        elif self._command_name == "list-storage":
            self.print_storage()

        elif self._command_name == "stop-cassandra":
            self.stop_cassandra(argv, options_dict)

        elif self._command_name == "start-cassandra":
            self.start_cassandra(argv, options_dict)

        elif self._command_name == "print-ring":
            self.print_ring(argv, options_dict)

        else:
            self.print_help()

    def launch_cluster(self, argv, options_dict):
        """
        """

        expected_arguments = ["NUM_SLAVES"]
        opt, args = self.parse_options(self._command_name,
                                       argv,
                                       expected_arguments=expected_arguments)
        opt.update(options_dict)

        # check for the cassandra-specific files
        if opt.get('cassandra_config_file') is None:
            print "ERROR: No cassandra_config_file configured. Aborting."
            sys.exit(1)

        if opt.get('keyspace_definitions_file') is None:
            print "WARNING: No keyspace_definitions_file configured. You can ignore this for Cassandra v0.6.x"

        # test files
        for key in ['cassandra_config_file', 'keyspace_definitions_file']:
            if opt.get(key) is not None:
                try:
                    url = urllib.urlopen(opt.get(key))
                    data = url.read()
                except: 
                    raise
                    print "The file defined by %s (%s) does not exist. Aborting." % (key, opt.get(key))
                    sys.exit(1)

        number_of_slaves = int(args[0])
        instance_templates = [
            InstanceTemplate(
                (
                    self.service.NAMENODE, 
                    self.service.SECONDARY_NAMENODE, 
                    self.service.JOBTRACKER,
                    self.service.HADOOP_CASSANDRA_NODE,
                ),
                1,
                opt.get('image_id'),
                opt.get('instance_type'), 
                opt.get('key_name'),
                opt.get('public_key'), 
                opt.get('user_data_file'),
                opt.get('availability_zone'), 
                opt.get('user_packages'),
                opt.get('auto_shutdown'), 
                opt.get('env'),
                opt.get('security_groups')),
            InstanceTemplate(
                (
                    self.service.DATANODE, 
                    self.service.TASKTRACKER,
                    self.service.CASSANDRA_NODE,
                ), 
                number_of_slaves,
                opt.get('image_id'),
                opt.get('instance_type'),
                opt.get('key_name'),
                opt.get('public_key'),
                opt.get('user_data_file'),
                opt.get('availability_zone'),
                opt.get('user_packages'),
                opt.get('auto_shutdown'),
                opt.get('env'),
                opt.get('security_groups'))
        ]

        for it in instance_templates:
            it.add_env_strings([
                "CLUSTER_SIZE=%d" % (number_of_slaves+1)
            ])

        print "Launching cluster with %d instance(s)...please wait." % (number_of_slaves+1)
        jobtracker = self.service.launch_cluster(instance_templates,
                                                 opt.get('client_cidr'),
                                                 opt.get('config_dir'),
                                                 opt.get('ssh_options'),
                                                 opt.get('cassandra_config_file'),
                                                 opt.get('keyspace_definitions_file'))

        if jobtracker is None:
            print "An error occurred started the Hadoop service. Check the logs for more information."
            sys.exit(1)

        print "Browse the cluster at http://%s/" % jobtracker.public_dns_name
        self.logger.debug("Startup complete.")

    def create_storage(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS,
                                       ["ROLE", "NUM_INSTANCES", "SPEC_FILE"])

        opt.update(options_dict)

        role = args[0]
        number_of_instances = int(args[1])
        spec_file = args[2]

        valid_roles = (self.service.NAMENODE, self.service.DATANODE, self.service.CASSANDRA_NODE)
        if role not in valid_roles:
            raise RuntimeError("Role must be one of %s" % str(valid_roles))

        self.service.create_storage(role, 
                                    number_of_instances,
                                    opt.get('availability_zone'),
                                    spec_file)
        self.print_storage()

    def proxy(self, argv, options_dict):
        instances = self.service.get_instances()
        if not instances:
            "No running instances. Aborting."
            sys.exit(1)

        result = self.service.proxy(ssh_options=options_dict.get('ssh_options'),   
                                    instances=instances)

        if result is None:
            print "Unable to create proxy. Check logs for more information."
            sys.exit(1)

        print "Proxy created..."
        print """export HADOOP_CLOUD_PROXY_PID=%s;
echo Proxy pid %s;""" % (result, result)

    def stop_cassandra(self, argv, options_dict):
        instances = self.service.cluster.get_instances_in_role(self.service.DATANODE, "running")
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        print "Stopping Cassandra service on %d instance(s)...please wait." % len(instances)
        self.service.stop_cassandra(options_dict.get('ssh_options'), instances=instances)

    def start_cassandra(self, argv, options_dict):
        instances = self.service.cluster.get_instances_in_role(self.service.DATANODE, "running")
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        print "Starting Cassandra service on %d instance(s)...please wait." % len(instances)
        self.service.start_cassandra(options_dict.get('ssh_options'), instances=instances)

    def print_ring(self, argv, options_dict):
        instances = self.service.cluster.get_instances_in_role(self.service.DATANODE, "running")
        if not instances:
            print "No running instances. Aborting."
            sys.exit(1)

        self.service.print_ring(options_dict.get('ssh_options'), instances[0])

########NEW FILE########
__FILENAME__ = service
from __future__ import with_statement

import os
import sys
import time
import subprocess
import urllib
import tempfile
import socket
import re

from cloud.cluster import TimeoutException
from cloud.service import InstanceTemplate
from cloud.plugin import ServicePlugin 
from cloud.util import xstr
from cloud.util import url_get

from yaml import load as parse_yaml
from yaml import dump as dump_yaml

try:
    from cElementTree import parse as parse_xml
    from cElementTree import tostring as dump_xml
    from cElementTree import Element
except:
    try:
        from xml.etree.cElementTree import parse as parse_xml
        from xml.etree.cElementTree import tostring as dump_xml
        from xml.etree.cElementTree import Element
    except:
        print "*"*80
        print "WARNING: cElementTree module does not exist. Defaulting to elementtree instead."
        print "It's recommended that you install the cElementTree module for faster XML parsing."
        print "*"*80
        from elementtree.ElementTree import parse as parse_xml
        from elementtree.ElementTree import parse as parse_xml
        from elementtree.ElementTree import Element

class HadoopCassandraService(ServicePlugin):
    """
    """
    NAMENODE = "hybrid_nn"
    SECONDARY_NAMENODE = "hybrid_snn"
    JOBTRACKER = "hybrid_jt"
    DATANODE = "hybrid_dn"
    TASKTRACKER = "hybrid_tt"
    CASSANDRA_NODE = "hybrid_cn"
    HADOOP_CASSANDRA_NODE = "hcn"

    def __init__(self):
        super(HadoopCassandraService, self).__init__()

    def get_roles(self):
        return [self.NAMENODE]

    def get_instances(self):
        """
        Return a list of tuples resembling (role_of_instance, instance)
        """
        return self.cluster.get_instances_in_role(self.NAMENODE, "running") + \
               self.cluster.get_instances_in_role(self.DATANODE, "running")

    def launch_cluster(self, instance_templates, client_cidr, config_dir,
                             ssh_options, cassandra_config_file,
                             cassandra_keyspace_file=None):

        number_of_tasktrackers = 0
        roles = []
        for it in instance_templates:
          roles.extend(it.roles)
          if self.TASKTRACKER in it.roles:
            number_of_tasktrackers += it.number

        singleton_hosts = []
        started_instance_ids = [] 
        expected_instance_count = sum([it.number for it in instance_templates])

        for instance_template in instance_templates:
            self.logger.debug("Launching %d instance(s) with role(s) %s..." % (
                instance_template.number,
                str(instance_template.roles),
            ))
            self.logger.debug("Instance(s) will have extra environment variables: %s" % (
                singleton_hosts,
            ))
            instance_template.add_env_strings(singleton_hosts)
            instance_ids = self._launch_instances(instance_template)

            if instance_template.number == 1:
                if len(instance_ids) != 1:
                    logger.error("Expected a single '%s' instance, but found %s.",
                                 "".join(instance_template.roles), 
                                 len(instance_ids))
                    return False
                else:
                    # wait for the instances to start
                    self.cluster.wait_for_instances(instance_ids)
                    instance = self.get_instances()[0]

                    for role in instance_template.roles:
                        singleton_host_env = "%s_HOST=%s" % (
                            self._sanitize_role_name(role),
                            instance.public_dns_name,
                        )
                        singleton_hosts.append(singleton_host_env)

            started_instance_ids.extend(instance_ids)

        if len(started_instance_ids) != expected_instance_count:
            self.logger.warn("Total number of reported instance ids (%d) " \
                             "does not match total requested number (%d)" % \
                             (len(started_instance_ids), instance_template.number))

        self.logger.debug("Waiting for %s instance(s) to start: %s" % \
            (len(started_instance_ids), ", ".join(started_instance_ids)))
        time.sleep(1)
        
        try:
            self.cluster.wait_for_instances(started_instance_ids)
        except TimeoutException:
            self.logger.error("Timeout while waiting for %d instances to start." % \
                              len(started_instance_ids))

        instances = self.get_instances()

        self.logger.debug("Instances started: %s" % (str(instances),))

        self._create_client_hadoop_site_file(config_dir)
        self._authorize_client_ports(client_cidr)
        self._attach_storage(roles)
        try:
            self._wait_for_hadoop(number_of_tasktrackers)
        except TimeoutException:
            print "Timeout while waiting for Hadoop to start. Please check logs on" + \
                  " cluster."

        # cassandra specific instances and setup
        cassandra_instances = self.cluster.get_instances_in_role(self.DATANODE, "running")
        self._transfer_config_files(ssh_options, 
                                    cassandra_config_file, 
                                    cassandra_keyspace_file, 
                                    instances=cassandra_instances)
        self.start_cassandra(ssh_options, 
                             create_keyspaces=(cassandra_keyspace_file is not None), 
                             instances=cassandra_instances)

        return self._get_jobtracker()

    def _sanitize_role_name(self, role):
        """
        Replace characters in role name with ones allowed in bash variable names
        """
        return role.replace('+', '_').upper()
    

    def _get_namenode(self):
        instances = self.cluster.get_instances_in_role(self.NAMENODE, "running")
        if not instances:
          return None
        return instances[0]

    def _get_jobtracker(self):
        instances = self.cluster.get_instances_in_role(self.JOBTRACKER, "running")
        if not instances:
          return None
        return instances[0]
    
    def _create_client_hadoop_site_file(self, config_dir):
        namenode = self._get_namenode()
        jobtracker = self._get_jobtracker()
        cluster_dir = os.path.join(config_dir, ".hadoop", self.cluster.name)
        aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']

        if not os.path.exists(cluster_dir):
          os.makedirs(cluster_dir)

        params = {
            'namenode': self._get_namenode().public_dns_name,
            'jobtracker': self._get_jobtracker().public_dns_name,
            'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY']
        }
        self.logger.debug("hadoop-site.xml params: %s" % str(params))

        with open(os.path.join(cluster_dir, 'hadoop-site.xml'), 'w') as f:
            f.write("""<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<!-- Put site-specific property overrides in this file. -->
<configuration>
    <property>
        <name>hadoop.job.ugi</name>
        <value>root,root</value>
    </property>
    <property>
        <name>fs.default.name</name>
        <value>hdfs://%(namenode)s:8020/</value>
    </property>
    <property>
        <name>mapred.job.tracker</name>
        <value>%(jobtracker)s:8021</value>
    </property>
    <property>
        <name>hadoop.socks.server</name>
        <value>localhost:6666</value>
    </property>
    <property>
        <name>hadoop.rpc.socket.factory.class.default</name>
        <value>org.apache.hadoop.net.SocksSocketFactory</value>
    </property>
    <property>
        <name>fs.s3.awsAccessKeyId</name>
        <value>%(aws_access_key_id)s</value>
    </property>
    <property>
        <name>fs.s3.awsSecretAccessKey</name>
        <value>%(aws_secret_access_key)s</value>
    </property>
    <property>
        <name>fs.s3n.awsAccessKeyId</name>
        <value>%(aws_access_key_id)s</value>
    </property>
    <property>
        <name>fs.s3n.awsSecretAccessKey</name>
        <value>%(aws_secret_access_key)s</value>
    </property>
</configuration>""" % params)

    def _authorize_client_ports(self, client_cidrs=[]):
        if not client_cidrs:
            self.logger.debug("No client CIDRs specified, using local address.")
            client_ip = url_get('http://checkip.amazonaws.com/').strip()
            client_cidrs = ("%s/32" % client_ip,)
        self.logger.debug("Client CIDRs: %s", client_cidrs)

        namenode = self._get_namenode()
        jobtracker = self._get_jobtracker()

        for client_cidr in client_cidrs:
            # Allow access to port 80 on namenode from client
            self.cluster.authorize_role(self.NAMENODE, 80, 80, client_cidr)

            # Allow access to jobtracker UI on master from client
            # (so we can see when the cluster is ready)
            self.cluster.authorize_role(self.JOBTRACKER, 50030, 50030, client_cidr)

        # Allow access to namenode and jobtracker via public address from each other
        namenode_ip = socket.gethostbyname(namenode.public_dns_name)
        jobtracker_ip = socket.gethostbyname(jobtracker.public_dns_name)
        self.cluster.authorize_role(self.NAMENODE, 8020, 8020, "%s/32" % namenode_ip)
        self.cluster.authorize_role(self.NAMENODE, 8020, 8020, "%s/32" % jobtracker_ip)
        self.cluster.authorize_role(self.JOBTRACKER, 8021, 8021, "%s/32" % namenode_ip)
        self.cluster.authorize_role(self.JOBTRACKER, 8021, 8021,
                                    "%s/32" % jobtracker_ip)

    def _wait_for_hadoop(self, number, timeout=600):
        wait_time = 3
        start_time = time.time()
        jobtracker = self._get_jobtracker()
        if not jobtracker:
            return

        self.logger.debug("Waiting for jobtracker to start...")
        previous_running = 0
        while True:
            if (time.time() - start_time >= timeout):
                raise TimeoutException()
            try:
                actual_running = self._number_of_tasktrackers(jobtracker.public_dns_name, 1)
                break
            except IOError:
                pass
            self.logger.debug("Sleeping for %d seconds..." % wait_time)
            time.sleep(wait_time)
        if number > 0:
            self.logger.debug("Waiting for %d tasktrackers to start" % number)
            while actual_running < number:
                if (time.time() - start_time >= timeout):
                    raise TimeoutException()
                try:
                    actual_running = self._number_of_tasktrackers(jobtracker.public_dns_name, 5, 2)
                    self.logger.debug("Sleeping for %d seconds..." % wait_time)
                    time.sleep(wait_time)
                    previous_running = actual_running
                except IOError:
                    pass
        
    # The optional ?type=active is a difference between Hadoop 0.18 and 0.20
    _NUMBER_OF_TASK_TRACKERS = re.compile(r'<a href="machines.jsp(?:\?type=active)?">(\d+)</a>')
  
    def _number_of_tasktrackers(self, jt_hostname, timeout, retries=0):
        url = "http://%s:50030/jobtracker.jsp" % jt_hostname
        jt_page = url_get(url, timeout, retries)
        m = self._NUMBER_OF_TASK_TRACKERS.search(jt_page)
        if m:
            return int(m.group(1))
        return 0

    def proxy(self, ssh_options, instances=None):
        if instances is None:
            return None

        namenode = self._get_namenode()
        if namenode is None:
            self.logger.error("No namenode running. Aborting.")
            return None
        
        options = '-o "ConnectTimeout 10" -o "ServerAliveInterval 60" ' \
                  '-N -D 6666'
        process = subprocess.Popen('ssh %s %s %s' % (
                xstr(ssh_options), 
                options, 
                namenode.public_dns_name
            ),
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            shell=True)
        
        return process.pid 

    def _wait_for_cassandra_install(self, instance, ssh_options):
        """
        Simply wait for the cassandra directory to be available so that we can begin configuring
        the service before starting it
        """
        wait_time = 3
        command = "ls /usr/local/apache-cassandra"
        ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
        self.logger.debug(ssh_command)
        timeout = 600

        start_time = time.time()
        while True:
            if (time.time() - start_time >= timeout):
                raise TimeoutException()
            retcode = subprocess.call(ssh_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            if retcode == 0:
                break
            self.logger.debug("Sleeping for %d seconds..." % wait_time)
            time.sleep(wait_time)

    def _transfer_config_files(self, ssh_options, config_file, keyspace_file=None, 
                                     instances=None):
        """
        """
        if instances is None:
            instances = self.get_instances()

        self.logger.debug("Waiting for %d Cassandra instance(s) to install..." % len(instances))
        for instance in instances:
            self._wait_for_cassandra_install(instance, ssh_options)

        self.logger.debug("Copying configuration files to %d Cassandra instances..." % len(instances))

        seed_ips = [str(instance.private_dns_name) for instance in instances[:2]]
        tokens = self._get_evenly_spaced_tokens_for_n_instances(len(instances))

        # for each instance, generate a config file from the original file and upload it to
        # the cluster node
        for i in range(len(instances)):
            local_file, remote_file = self._modify_config_file(instances[i], config_file, seed_ips, str(tokens[i]))

            # Upload modified config file
            scp_command = 'scp %s -r %s %s:/usr/local/apache-cassandra/conf/%s' % (xstr(ssh_options),
                                                     local_file, instances[i].public_dns_name, remote_file)
            subprocess.call(scp_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            # delete temporary file
            os.unlink(local_file)

        if keyspace_file:
            keyspace_data = urllib.urlopen(keyspace_file).read()
            fd, temp_keyspace_file = tempfile.mkstemp(prefix="keyspaces.txt_", text=True)
            os.write(fd, keyspace_data)
            os.close(fd)

            self.logger.debug("Copying keyspace definition file to first Cassandra instance...")

            # Upload keyspace definitions file
            scp_command = 'scp %s -r %s %s:/usr/local/apache-cassandra/conf/keyspaces.txt' % \
                          (xstr(ssh_options), temp_keyspace_file, instances[0].public_dns_name)
            subprocess.call(scp_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            # remove temporary file
            os.unlink(temp_keyspace_file)

    def _modify_config_file(self, instance, config_file, seed_ips, token):
        # XML (0.6.x) 
        if config_file.endswith(".xml"):
            remote_file = "storage-conf.xml"

            xml = parse_xml(urllib.urlopen(config_file)).getroot()

            #  Seeds
            seeds = xml.find("Seeds")
            if seeds is not None:
                while seeds.getchildren():
                    seeds.remove(seeds.getchildren()[0])
            else:
                seeds = Element("Seeds")
                xml.append(seeds)

            for seed_ip in seed_ips:
                seed = Element("Seed")
                seed.text = seed_ip
                seeds.append(seed)

            # Initial token
            initial_token = xml.find("InitialToken")
            if initial_token is None:
                initial_token = Element("InitialToken")
                xml.append(initial_token)
            initial_token.text = token

            # Logs
            commit_log_directory = xml.find("CommitLogDirectory")
            if commit_log_directory is None:
                commit_log_directory = Element("CommitLogDirectory")
                xml.append(commit_log_directory)
            commit_log_directory.text = "/mnt/cassandra-logs"

            # Data 
            data_file_directories = xml.find("DataFileDirectories")
            if data_file_directories is not None:
                while data_file_directories.getchildren():
                    data_file_directories.remove(data_file_directories.getchildren()[0])
            else:
                data_file_directories = Element("DataFileDirectories")
                xml.append(data_file_directories)
            data_file_directory = Element("DataFileDirectory")
            data_file_directory.text = "/mnt/cassandra-data"
            data_file_directories.append(data_file_directory)


            # listen address
            listen_address = xml.find("ListenAddress")
            if listen_address is None:
                listen_address = Element("ListenAddress")
                xml.append(listen_address)
            listen_address.text = ""

            # thrift address
            thrift_address = xml.find("ThriftAddress")
            if thrift_address is None:
                thrift_address = Element("ThriftAddress")
                xml.append(thrift_address)
            thrift_address.text = ""

            fd, temp_file = tempfile.mkstemp(prefix='storage-conf.xml_', text=True)
            os.write(fd, dump_xml(xml))
            os.close(fd)
            
        # YAML (0.7.x)
        elif config_file.endswith(".yaml"):
            remote_file = "cassandra.yaml"

            yaml = parse_yaml(urllib.urlopen(config_file))
            yaml['seeds'] = seed_ips
            yaml['initial_token'] = token
            yaml['data_file_directories'] = ['/mnt/cassandra-data']
            yaml['commitlog_directory'] = '/mnt/cassandra-logs'
            yaml['listen_address'] = str(instance.private_dns_name)
            yaml['rpc_address'] = str(instance.public_dns_name)

            fd, temp_file = tempfile.mkstemp(prefix='cassandra.yaml_', text=True)
            os.write(fd, dump_yaml(yaml))
            os.close(fd)
        else:
            raise Exception("Configuration file must be one of xml or yaml") 

        return temp_file, remote_file
    
    def _get_evenly_spaced_tokens_for_n_instances(self, n):
        return [i*(2**127/n) for i in range(1,n+1)]

    def _create_keyspaces_from_definitions_file(self, instance, ssh_options):
        # TODO: Keyspaces could already exist...how do I check this?
        # TODO: Can it be an arbitrary node?

        self.logger.debug("Creating keyspaces using Thrift API via keyspaces_definitions_file...")

        # test for the keyspace file first
        command = "ls /usr/local/apache-cassandra/conf/keyspaces.txt"
        ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
        retcode = subprocess.call(ssh_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        if retcode != 0:
            self.logger.warn("Unable to find /usr/local/apache-cassandra/conf/keyspaces.txt. Skipping keyspace generation.")
            return
        else:
            self.logger.debug("Found keyspaces.txt...Proceeding with keyspace generation.")

        command = "/usr/local/apache-cassandra/bin/cassandra-cli --host %s --batch " \
                  "< /usr/local/apache-cassandra/conf/keyspaces.txt" % instance.private_dns_name
        ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
        retcode = subprocess.call(ssh_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        # TODO: do this or not?
        # remove keyspace file
        #command = "rm -rf /usr/local/apache-cassandra/conf/keyspaces.txt"
        #ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
        #subprocess.call(ssh_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    def print_ring(self, ssh_options, instance=None):
        if instance is None:
          instance = self.get_instances()[0]

        print "\nRing configuration..."
        print "NOTE: May not be accurate if the cluster just started."
        command = "/usr/local/apache-cassandra/bin/nodetool -h localhost ring"
        ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
        subprocess.call(ssh_command, shell=True)

    def start_cassandra(self, ssh_options, create_keyspaces=False, instances=None):
        if instances is None:
            instances = self.get_instances()

        self.logger.debug("Starting Cassandra service on %d instance(s)..." % len(instances))

        for instance in instances:
            # if checks to see if cassandra is already running 
            command = "if [ ! -f /root/cassandra.pid ]; then `nohup /usr/local/apache-cassandra/bin/cassandra -p /root/cassandra.pid &> /root/cassandra.out &`; fi"
            ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
            retcode = subprocess.call(ssh_command, shell=True)

            if retcode != 0:
                self.logger.warn("Return code for starting Cassandra: %d" % retcode)

        # test connection
        self.logger.debug("Testing connection to each Cassandra instance...")

        timeout = 600
        temp_instances = instances[:]
        start_time = time.time()
        while len(temp_instances) > 0:
            if (time.time() - start_time >= timeout):
                raise TimeoutException()
            
            command = "/usr/local/apache-cassandra/bin/nodetool -h %s ring" % temp_instances[-1].private_dns_name
            ssh_command = self._get_standard_ssh_command(temp_instances[-1], ssh_options, command)
            retcode = subprocess.call(ssh_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            if retcode == 0:
                temp_instances.pop()
            else:
                self.logger.warn("Return code for 'nodetool ring' on '%s': %d" % (temp_instances[-1].id, retcode))

        if create_keyspaces:
            self._create_keyspaces_from_definitions_file(instances[0], ssh_options)
        else:
            self.logger.debug("create_keyspaces is False. Skipping keyspace generation.")
        
        # TODO: Do I need to wait for the keyspaces to propagate before printing the ring?
        # print ring after everything started
        self.print_ring(ssh_options, instances[0])

        self.logger.debug("Startup complete.")

    def stop_cassandra(self, ssh_options, instances=None):
        if instances is None:
            instances = self.get_instances()

        for instance in instances:
            command = "kill `cat /root/cassandra.pid`"
            ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)
            retcode = subprocess.call(ssh_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    def login(self, instance, ssh_options):
        ssh_command = self._get_standard_ssh_command(instance, ssh_options)
        subprocess.call(ssh_command, shell=True)

########NEW FILE########
__FILENAME__ = cli
import os
import sys
import logging
import urllib

from cloud.plugin import CLIPlugin
from cloud.plugin import BASIC_OPTIONS
from cloud.service import InstanceTemplate
from optparse import make_option
from prettytable import PrettyTable
from pprint import pprint

# Add options here to override what's in the clusters.cfg file
# TODO

class SimpleServiceCLI(CLIPlugin):
    USAGE = """Simple service usage: CLUSTER COMMAND [OPTIONS]
where COMMAND and [OPTIONS] may be one of:
            
                               APPLICATION COMMANDS
  ----------------------------------------------------------------------------------
  launch-load-balancer                launch a load balancer for CLUSTER
  launch-nodes NUM_NODES              launch NUM_NODES nodes in CLUSTER
  start-nodes                         start the nodes
  stop-nodes                          stop the nodes
  start-load-balancer                 start the load balancer
  stop-load-balancer                  stop the load balancer

                               CLUSTER COMMANDS
  ----------------------------------------------------------------------------------
  details                             list instances in CLUSTER
  launch-cluster NUM_NODES            launch NUM_NODES Cassandra nodes
  expand-cluster NUM_NODES            adds new nodes
  terminate-cluster                   terminate all instances in CLUSTER
  login                               log in to the master in CLUSTER over SSH

                               STORAGE COMMANDS
  ----------------------------------------------------------------------------------
  list-storage                        list storage volumes for CLUSTER
  create-storage NUM_INSTANCES        create volumes for NUM_INSTANCES instances
    SPEC_FILE                           for CLUSTER, using SPEC_FILE
  delete-storage                      delete all storage volumes for CLUSTER
"""
#  transfer FILE DESTINATION           transfer a file to all nodes
#  execute COMMAND                     execute a command on all nodes

    def __init__(self):
        super(SimpleServiceCLI, self).__init__()

        #self._logger = logging.getLogger("CassandraServiceCLI")
 
    def execute_command(self, argv, options_dict):
        if len(argv) < 2:
            self.print_help()

        self._cluster_name = argv[0]
        self._command_name = argv[1]

        # strip off the cluster name and command from argv
        argv = argv[2:]

        # get spot configuration
        self._spot_config = {
                "spot_cluster": True if os.environ.get("SPOT_CLUSTER", options_dict.get("spot_cluster", "false")).lower() == "true" else False,
                "max_price": options_dict.get("max_price", None),
                "launch_group": options_dict.get("launch_group", None),
         }

        # handle all known commands and error on an unknown command
        if self._command_name == "details":
            self.print_instances()

        elif self._command_name == "simple-details":
            self.simple_print_instances(argv, options_dict)

        elif self._command_name == "terminate-cluster":
            self.terminate_cluster(argv, options_dict)

        elif self._command_name == "launch-cluster":
            self.launch_cluster(argv, options_dict)

        elif self._command_name == "expand-cluster":
            self.expand_cluster(argv, options_dict)

        elif self._command_name == "login":
            self.login(argv, options_dict)

        elif self._command_name == "run-command":
            self.run_command(argv, options_dict)

        elif self._command_name == "transfer-files":
            self.transfer_files(argv, options_dict)

        elif self._command_name == "create-storage":
            self.create_storage(argv, options_dict)

        elif self._command_name == "delete-storage":
            self.delete_storage(argv, options_dict)

        elif self._command_name == "list-storage":
            self.print_storage()

        else:
            self.print_help()

    def expand_cluster(self, argv, options_dict):
        expected_arguments = ["NUM_INSTANCES"]
        opt, args = self.parse_options(self._command_name,
                                       argv,
                                       expected_arguments=expected_arguments,
                                       unbounded_args=True)
        opt.update(options_dict)

        number_of_nodes = int(args[0])
        instance_template = InstanceTemplate(
            (self.service.SIMPLE_NODE,),
            number_of_nodes,
            opt.get('image_id'),
            opt.get('instance_type'),
            opt.get('key_name'),
            opt.get('public_key'),
            opt.get('user_data_file'),
            opt.get('availability_zone'),
            opt.get('user_packages'),
            opt.get('auto_shutdown'),
            opt.get('env'),
            opt.get('security_groups'),
            self._spot_config
        )

#        instance_template.add_env_strings(["CLUSTER_SIZE=%d" % number_of_nodes])

        print "Expanding cluster by %d instance(s)...please wait." % number_of_nodes

        self.service.expand_cluster(instance_template,
                                    opt.get('ssh_options'),opt.get('wait_dir', '/'))

    def launch_cluster(self, argv, options_dict):
        """
        """
        expected_arguments = ["NUM_INSTANCES"]
        opt, args = self.parse_options(self._command_name, 
                                      argv,
                                      expected_arguments=expected_arguments)
        opt.update(options_dict)

        number_of_nodes = int(args[0])
        instance_template = InstanceTemplate(
            (self.service.SIMPLE_NODE,),
            number_of_nodes,
            opt.get('image_id'),
            opt.get('instance_type'),
            opt.get('key_name'),
            opt.get('public_key'), 
            opt.get('user_data_file'),
            opt.get('availability_zone'), 
            opt.get('user_packages'),
            opt.get('auto_shutdown'), 
            opt.get('env'),
            opt.get('security_groups'),
            self._spot_config
        )

        instance_template.add_env_strings(["CLUSTER_SIZE=%d" % number_of_nodes])

        print "Launching cluster with %d instance(s)...please wait." % number_of_nodes

        self.service.launch_cluster(instance_template,
                                    opt.get('ssh_options'),opt.get('wait_dir', '/'))

    def create_storage(self, argv, options_dict):
        opt, args = self.parse_options(self._command_name, argv, BASIC_OPTIONS,
                                       ["NUM_INSTANCES", "SPEC_FILE"])
        opt.update(options_dict)

        role = self.service.SIMPLE_NODE
        number_of_instances = int(args[0])
        spec_file = args[1]

        # FIXME
        # check_options_set(opt, ['availability_zone'])

        self.service.create_storage(role, 
                                    number_of_instances,
                                    opt.get('availability_zone'),
                                    spec_file)
        self.print_storage()

########NEW FILE########
__FILENAME__ = service
import os
import sys
import time
import subprocess
import urllib
import tempfile

from cloud.cluster import TimeoutException
from cloud.service import InstanceTemplate
from cloud.plugin import ServicePlugin 
from cloud.util import xstr

from yaml import load as parse_yaml
from yaml import dump as dump_yaml

try:
    from cElementTree import parse as parse_xml
    from cElementTree import tostring as dump_xml
    from cElementTree import Element
except:
    try:
        from xml.etree.cElementTree import parse as parse_xml
        from xml.etree.cElementTree import tostring as dump_xml
        from xml.etree.cElementTree import Element
    except:
        print "*"*80
        print "WARNING: cElementTree module does not exist. Defaulting to elementtree instead."
        print "It's recommended that you install the cElementTree module for faster XML parsing."
        print "*"*80
        from elementtree.ElementTree import parse as parse_xml
        from elementtree.ElementTree import parse as parse_xml
        from elementtree.ElementTree import Element

class SimpleService(ServicePlugin):
    """
    """
    SIMPLE_NODE = "sn"

    def __init__(self):
        super(SimpleService, self).__init__()

    def get_roles(self):
        return [self.SIMPLE_NODE]

    def get_instances(self):
        return self.cluster.get_instances_in_role(self.SIMPLE_NODE, "running")

    def _wait_for_install(self, instance, ssh_options, wait_dir):
        """
        Simply wait for the 'wait' directory to be available so that we can begin configuring
        the service before starting it
        """
        wait_time = 3
        errcount = 0
        command = "ls %s" % wait_dir
        ssh_command = self._get_standard_ssh_command(instance, ssh_options, command)

        self.logger.info("Waiting for install with command %s" % ssh_command)
        while True:
            if errcount >= 10:
                raise TimeoutException("Maximum errors exceeded.")
            try:
                subprocess.check_output(ssh_command, shell=True, stderr=subprocess.STDOUT)
                break
            except subprocess.CalledProcessError, e:
                error = e.output.strip()
                retcode = e.returncode
                if retcode != 255:
                    print error
                    print "Return code: %d" % retcode
                elif retcode == 255 and "connection refused" in error.lower():
                    print "Connection refused error. Typically means SSH services have not been started yet. Retrying."
                    errcount += 1
                else:
                    print "SSH error. Cause: %s" % e.output.strip()
                    print "Return code: %d" % retcode
                    raise

            self.logger.debug("Sleeping for %d seconds..." % wait_time)
            time.sleep(wait_time)

    def expand_cluster(self, instance_template, ssh_options, wait_dir):
        instances = self.get_instances()

        instance_ids = self._launch_instances(instance_template)

        if len(instance_ids) != instance_template.number:
            self.logger.warn("Number of reported instance ids (%d) " \
                             "does not match requested number (%d)" % \
                             (len(instance_ids), instance_template.number))
        self.logger.debug("Waiting for %s instance(s) to start: %s" % \
            (instance_template.number, ", ".join(instance_ids)))
        time.sleep(1)

        try:
            self.cluster.wait_for_instances(instance_ids)
            self.logger.debug("%d instances started" % (instance_template.number,))
        except TimeoutException:
            self.logger.error("Timeout while waiting for %s instance to start." % \
                ",".join(instance_template.roles))

        instances = self.get_instances()
        self.logger.debug("We have %d current instances...", len(instances))
        new_instances = [instance for instance in instances if instance.id in instance_ids]
        if(len(new_instances) != len(instance_ids)) :
            raise Exception("Could only find %d new instances, expected %s" % (len(new_instances), str(instance_ids)))

        for instance in instances:
            self._wait_for_install(instance, ssh_options, wait_dir)
        self.logger.info("Instances started: %s" % (str(new_instances),))

        self._attach_storage(instance_template.roles)


    def launch_cluster(self, instance_template, ssh_options, wait_dir):
        """
        """
        if self.get_instances() :
            raise Exception("This cluster is already running.  It must be terminated prior to being launched again.")

        self.expand_cluster(instance_template, ssh_options, wait_dir)

########NEW FILE########
