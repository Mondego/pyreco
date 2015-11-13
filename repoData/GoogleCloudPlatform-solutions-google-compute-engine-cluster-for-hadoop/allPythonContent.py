__FILENAME__ = compute_cluster_for_hadoop
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Start up Hadoop on Google Compute Engine."""



import argparse
import logging
import re
import sys

import oauth2client

import gce_cluster


class ComputeClusterForHadoop(object):
  """Class to manage Hadoop on Google Compute Engine."""

  @staticmethod
  def SetUp(flags):
    """Set up environment for Hadoop on Compute."""
    gce_cluster.GceCluster(flags).EnvironmentSetUp()

  @staticmethod
  def Start(flags):
    """Starts Google Compute Engine cluster with Hadoop set up."""
    gce_cluster.GceCluster(flags).StartCluster()

  @staticmethod
  def ShutDown(flags):
    """Deletes all instances included in the Hadoop cluster."""
    gce_cluster.GceCluster(flags).TeardownCluster()

  @staticmethod
  def MapReduce(flags):
    """Starts MapReduce job."""
    gce_cluster.GceCluster(flags).StartMapReduce()

  def __init__(self):
    self._parser = argparse.ArgumentParser()

    # Specify --noauth_local_webserver as instructed when you use remote
    # terminal such as ssh.
    class SetNoAuthLocalWebserverAction(argparse.Action):
      def __call__(self, parser, namespace, values, option_string=None):
        oauth2client.tools.gflags.FLAGS.auth_local_webserver = False

    self._parser.add_argument(
        '--noauth_local_webserver', nargs=0,
        action=SetNoAuthLocalWebserverAction,
        help='Do not attempt to open browser on local machine.')

    self._parser.add_argument(
        '--debug', action='store_true',
        help='Debug mode.  Shows verbose log.')

    self._subparsers = self._parser.add_subparsers(
        title='Sub-commands', dest='subcommand')

  def _AddSetUpSubcommand(self):
    """Sets up parameters for 'setup' subcommand."""
    parser_setup = self._subparsers.add_parser(
        'setup',
        help='Sets up environment of project and bucket.  Setup must be '
        'performed once per same project/bucket pair.')
    parser_setup.set_defaults(handler=self.SetUp, prefix='')
    parser_setup.add_argument(
        'project',
        help='Project ID to start Google Compute Engine instances in.')
    parser_setup.add_argument(
        'bucket',
        help='Google Cloud Storage bucket name for temporary use.')

  def _AddStartSubcommand(self):
    """Sets up parameters for 'start' subcommand."""
    parser_start = self._subparsers.add_parser(
        'start',
        help='Start Hadoop cluster.')
    parser_start.set_defaults(handler=self.Start)
    parser_start.add_argument(
        'project',
        help='Project ID to start Google Compute Engine instances in.')
    parser_start.add_argument(
        'bucket',
        help='Google Cloud Storage bucket name for temporary use.')
    parser_start.add_argument(
        'num_workers', default=5, type=int, nargs='?',
        help='Number of worker instances in Hadoop cluster. (default 5)')
    parser_start.add_argument(
        '--prefix', default='',
        help='Name prefix of Google Compute Engine instances. (default "")')
    parser_start.add_argument(
        '--zone', default='',
        help='Zone name where to add Hadoop cluster.')
    parser_start.add_argument(
        '--image', default='',
        help='Machine image of Google Compute Engine instance.')
    parser_start.add_argument(
        '--machinetype', default='',
        help='Machine type of Google Compute Engine instance.')
    parser_start.add_argument(
        '--data-disk-gb', default=0, type=int,
        help='Size of persistent disk for data per instance in GB.')
    parser_start.add_argument(
        '--command', default='',
        help='Additional command to run on each instance.')
    parser_start.add_argument(
        '--external-ip', choices=['all', 'master'], default='all',
        help=('Indicates which instance has external IP addresses. '
              '["all" or "master"] (default "all")'))

  def _AddShutdownSubcommand(self):
    """Sets up parameters for 'shutdown' subcommand."""
    parser_shutdown = self._subparsers.add_parser(
        'shutdown',
        help='Tear down Hadoop cluster.')
    parser_shutdown.set_defaults(handler=self.ShutDown,
                                 image='', machinetype='')
    parser_shutdown.add_argument(
        'project',
        help='Project ID where Hadoop cluster lives.')
    parser_shutdown.add_argument(
        '--prefix', default='',
        help='Name prefix of Google Compute Engine instances. (default "")')
    parser_shutdown.add_argument(
        '--zone', default='',
        help='Zone name where Hadoop cluster lives.')

  def _AddMapReduceSubcommand(self):
    """Sets up parameters for 'mapreduce' subcommand."""
    parser_mapreduce = self._subparsers.add_parser(
        'mapreduce',
        help='Start MapReduce job.')
    parser_mapreduce.set_defaults(handler=self.MapReduce,
                                  image='', machinetype='')
    parser_mapreduce.add_argument(
        'project',
        help='Project ID where Hadoop cluster lives.')
    parser_mapreduce.add_argument(
        'bucket',
        help='Google Cloud Storage bucket name for temporary use.')
    parser_mapreduce.add_argument(
        '--zone', default='',
        help='Zone name where Hadoop cluster lives.')
    parser_mapreduce.add_argument(
        '--prefix', default='',
        help='Name prefix of Google Compute Engine instances. (default "")')
    parser_mapreduce.add_argument(
        '--mapper',
        help='Mapper program file either on local or on Cloud Storage.')
    parser_mapreduce.add_argument(
        '--reducer',
        help='Reducer program file either on local or on Cloud Storage.')
    parser_mapreduce.add_argument(
        '--input', required=True,
        help='Input data directory on Cloud Storage.')
    parser_mapreduce.add_argument(
        '--output', required=True,
        help='Output data directory on Cloud Storage.')
    parser_mapreduce.add_argument(
        '--mapper-count', type=int, dest='mapper_count', default=5,
        help='Number of mapper tasks.')
    parser_mapreduce.add_argument(
        '--reducer-count', type=int, dest='reducer_count', default=1,
        help='Number of reducer tasks.  Make this 0 to skip reducer.')

  def ParseArgumentsAndExecute(self, argv):
    """Parses command-line arguments and executes sub-command handler."""
    self._AddSetUpSubcommand()
    self._AddStartSubcommand()
    self._AddShutdownSubcommand()
    self._AddMapReduceSubcommand()

    # Parse command-line arguments and execute corresponding handler function.
    params = self._parser.parse_args(argv)

    # Check prefix length.
    if hasattr(params, 'prefix') and params.prefix:
      # Prefix:
      #   - 15 characters or less.
      #   - May use lower case, digits or hyphen.
      #   - First character must be lower case alphabet.
      #   - May use hyphen at the end, since actual hostname continues.
      if not re.match('^[a-z][-a-z0-9]{0,14}$', params.prefix):
        logging.critical('Invalid prefix pattern.  Prefix must be 15 '
                         'characters or less.  Only lower case '
                         'alphabets, numbers and hyphen ("-") can be '
                         'used.  The first character must be '
                         'lower case alphabet.')
        sys.exit(1)

    # Set debug mode.
    if params.debug:
      logging.basicConfig(
          level=logging.DEBUG,
          format='%(asctime)s [%(module)s:%(levelname)s] '
          '(%(filename)s:%(funcName)s:%(lineno)d) %(message)s')
    else:
      logging.basicConfig(
          level=logging.INFO,
          format='%(asctime)s [%(module)s:%(levelname)s] %(message)s')

    logging.debug('***** DEBUG LOGGING MODE *****')

    # Execute handler function.
    # Handler functions are set as default parameter value of "handler"
    # by each subparser's set_defaults() method.
    params.handler(params)


def main():
  ComputeClusterForHadoop().ParseArgumentsAndExecute(sys.argv[1:])


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = compute_cluster_for_hadoop_test
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests of compute_cluster_for_hadoop.py."""



import argparse
import unittest

import mock

import compute_cluster_for_hadoop


class ComputeClusterForHadoopTest(unittest.TestCase):
  """Unit test class for ComputeClusterForHadoop."""

  def _GetFlags(self, mock_cluster):
    flags = mock_cluster.call_args[0][0]
    self.assertIsInstance(flags, argparse.Namespace)
    return flags

  def testSetUp(self):
    """Setup sub-command unit test."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'setup', 'project-name', 'bucket-name'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-name', flags.project)
      self.assertEqual('bucket-name', flags.bucket)
      mock_cluster.return_value.EnvironmentSetUp.assert_called_once_with()

  def testSetUp_NoBucket(self):
    """Setup sub-command unit test with no bucket option."""
    with mock.patch('gce_cluster.GceCluster'):
      # Fails to execute sub-command.
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['setup', 'project-name'])

  def testStart(self):
    """Start sub-command unit test."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'start', 'project-name', 'bucket-name', '10'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-name', flags.project)
      self.assertEqual('bucket-name', flags.bucket)
      self.assertEqual(10, flags.num_workers)
      self.assertEqual('all', flags.external_ip)
      mock_cluster.return_value.StartCluster.assert_called_once_with()

  def testStart_DefaultClusterSize(self):
    """Start sub-command unit test with default cluster size."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'start', 'project-foo', 'bucket-bar'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-foo', flags.project)
      self.assertEqual('bucket-bar', flags.bucket)
      self.assertEqual(5, flags.num_workers)
      self.assertEqual('all', flags.external_ip)
      mock_cluster.return_value.StartCluster.assert_called_once_with()

  def testStart_OptionalParams(self):
    """Start sub-command unit test with optional params."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'start', 'project-name', 'bucket-name', '--prefix', 'fuga',
          '--zone', 'piyo', '--command', '"additional command"',
          '--external-ip=master'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-name', flags.project)
      self.assertEqual('bucket-name', flags.bucket)
      self.assertEqual(5, flags.num_workers)
      self.assertEqual('fuga', flags.prefix)
      self.assertEqual('piyo', flags.zone)
      self.assertEqual('"additional command"', flags.command)
      self.assertEqual('master', flags.external_ip)
      mock_cluster.return_value.StartCluster.assert_called_once_with()

  def testStart_Prefix(self):
    """Start sub-command unit test with long prefix."""
    with mock.patch('gce_cluster.GceCluster'):
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'start', 'project-piyo', 'bucket-bar',
          '--prefix', 'a6b-c'])
      hadoop_cluster.ParseArgumentsAndExecute([
          'start', 'project-piyo', 'bucket-bar',
          '--prefix', 'ends-with-dash-'])

      # Invalid patterns.
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['start', 'project-piyo', 'bucket-bar',
                         '--prefix', 'insanely-long-prefix'])
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['start', 'project-piyo', 'bucket-bar',
                         '--prefix', 'upperCase'])
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['start', 'project-piyo', 'bucket-bar',
                         '--prefix', 'invalid*char'])
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['start', 'project-piyo', 'bucket-bar',
                         '--prefix', '0number'])

  def testStart_NoBucket(self):
    """Start sub-command unit test with no bucket option."""
    with mock.patch('gce_cluster.GceCluster'):
      # Fails to execute sub-command.
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['start', 'project-hoge'])

  def testStart_InvalidExternalIp(self):
    """Start sub-command unit test with no bucket option."""
    with mock.patch('gce_cluster.GceCluster'):
      # Fails to execute sub-command.
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['start', 'project-piyo', 'bucket-bar',
                         '--external-ip', 'foo'])

  def testShutdown(self):
    """Shutdown sub-command unit test."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'shutdown', 'project-name'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-name', flags.project)
      mock_cluster.return_value.TeardownCluster.assert_called_once_with()

  def testShutdown_OptionalParams(self):
    """Shutdown sub-command unit test with optional params."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'shutdown', 'project-name', '--prefix', 'foo',
          '--zone', 'abc'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-name', flags.project)
      self.assertEqual('foo', flags.prefix)
      self.assertEqual('abc', flags.zone)
      mock_cluster.return_value.TeardownCluster.assert_called_once_with()

  def testShutdown_MissingParamValue(self):
    """Shutdown sub-command unit test with missing param value."""
    with mock.patch('gce_cluster.GceCluster'):
      # Fails to execute sub-command.
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['shutdown', 'project-name', '--prefix'])

  def testShutdown_InvalidOption(self):
    """Shutdown sub-command unit test with invalid optional param."""
    with mock.patch('gce_cluster.GceCluster'):
      # Fails to execute sub-command.
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['shutdown', 'project-name', '--image', 'foo'])

  def testMapReduce(self):
    """MapReduce sub-command unit test."""
    with mock.patch('gce_cluster.GceCluster') as mock_cluster:
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      hadoop_cluster.ParseArgumentsAndExecute([
          'mapreduce', 'project-name', 'bucket-name',
          '--input', 'gs://some-bucket/inputs',
          '--output', 'gs://some-bucket/outputs'])

      self.assertEqual(1, mock_cluster.call_count)
      flags = self._GetFlags(mock_cluster)
      self.assertEqual('project-name', flags.project)
      self.assertEqual('bucket-name', flags.bucket)
      self.assertEqual('gs://some-bucket/inputs', flags.input)
      self.assertEqual('gs://some-bucket/outputs', flags.output)
      mock_cluster.return_value.StartMapReduce.assert_called_once_with()

  def testMapReduce_NoInputOutput(self):
    """MapReduce sub-command unit test."""
    with mock.patch('gce_cluster.GceCluster'):
      hadoop_cluster = compute_cluster_for_hadoop.ComputeClusterForHadoop()
      self.assertRaises(SystemExit,
                        hadoop_cluster.ParseArgumentsAndExecute,
                        ['mapreduce', 'project-name', 'bucket-name'])


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = gce_api
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module to provide Google Client API wrapper for Google Compute Engine."""



import logging
import os
import os.path

import apiclient.discovery
import apiclient.errors
import httplib2

import oauth2client.client
import oauth2client.file
import oauth2client.tools


class ResourceZoning(object):
  """Constants to indicate which zone type the resource belongs to."""
  NONE = 0
  GLOBAL = 1
  ZONE = 2


class GceApi(object):
  """Google Client API wrapper for Google Compute Engine."""

  COMPUTE_ENGINE_SCOPE = 'https://www.googleapis.com/auth/compute'
  COMPUTE_ENGINE_API_VERSION = 'v1'

  def __init__(self, name, client_id, client_secret, project, zone):
    """Constructor.

    Args:
      name: Name of the user of the class.  Used for credentials filename.
      client_id: Client ID of the user of the class.
      client_secret: Client secret of the user of the class.
      project: Project ID.
      zone: Zone name, e.g. 'us-east-a'
    """
    self._name = name
    self._client_id = client_id
    self._client_secret = client_secret
    self._project = project
    self._zone = zone

  def GetApi(self):
    """Does OAuth2 authorization and prepares Google Compute Engine API.

    Since access keys may expire at any moment, call the function every time
    making API call.

    Returns:
      Google Client API object for Google Compute Engine.
    """
    # First, check local file for credentials.
    homedir = os.environ['HOME']
    storage = oauth2client.file.Storage(
        os.path.join(homedir, '.%s.credentials' % self._name))
    credentials = storage.get()

    if not credentials or credentials.invalid:
      # If local credentials are not valid, do OAuth2 dance.
      flow = oauth2client.client.OAuth2WebServerFlow(
          self._client_id, self._client_secret, self.COMPUTE_ENGINE_SCOPE)
      credentials = oauth2client.tools.run(flow, storage)

    # Set up http with the credentials.
    authorized_http = credentials.authorize(httplib2.Http())
    return apiclient.discovery.build(
        'compute', self.COMPUTE_ENGINE_API_VERSION, http=authorized_http)

  @staticmethod
  def IsNotFoundError(http_error):
    """Checks if HttpError reason was 'not found'.

    Args:
      http_error: HttpError
    Returns:
      True if the error reason was 'not found', otherwise False.
    """
    return http_error.resp['status'] == '404'

  @classmethod
  def _ResourceUrlFromPath(cls, path):
    """Creates full resource URL from path."""
    return 'https://www.googleapis.com/compute/%s/%s' % (
        cls.COMPUTE_ENGINE_API_VERSION, path)

  def _ResourceUrl(self, resource_type, resource_name,
                   zoning=ResourceZoning.ZONE, project=None):
    """Creates URL to indicate Google Compute Engine resource.

    Args:
      resource_type: Resource type.
      resource_name: Resource name.
      zoning: Which zone type the resource belongs to.
      project: Overrides project for the resource.
    Returns:
      URL in string to represent the resource.
    """
    if not project:
      project = self._project

    if zoning == ResourceZoning.NONE:
      resource_path = 'projects/%s/%s/%s' % (
          project, resource_type, resource_name)
    elif zoning == ResourceZoning.GLOBAL:
      resource_path = 'projects/%s/global/%s/%s' % (
          project, resource_type, resource_name)
    else:
      resource_path = 'projects/%s/zones/%s/%s/%s' % (
          project, self._zone, resource_type, resource_name)

    return self._ResourceUrlFromPath(resource_path)

  def _ParseOperation(self, operation, title):
    """Parses operation result and log warnings and errors if any.

    Args:
      operation: Operation object as result of operation.
      title: Title used for log.
    Returns:
      Boolean to indicate whether the operation was successful.
    """
    if 'error' in operation and 'errors' in operation['error']:
      for e in operation['error']['errors']:
        logging.error('%s: %s: %s',
                      title, e.get('code', 'NO ERROR CODE'),
                      e.get('message', 'NO ERROR MESSAGE'))
      return False

    if 'warnings' in operation:
      for w in operation['warnings']:
        logging.warning('%s: %s: %s',
                        title, w.get('code', 'NO WARNING CODE'),
                        w.get('message', 'NO WARNING MESSAGE'))
    return True

  def GetInstance(self, instance_name):
    """Gets instance information.

    Args:
      instance_name: Name of the instance to get information of.
    Returns:
      Google Compute Engine instance resource.  None if error.
      https://developers.google.com/compute/docs/reference/latest/instances
    """
    try:
      return self.GetApi().instances().get(
          project=self._project, zone=self._zone,
          instance=instance_name).execute()
    except apiclient.errors.HttpError as e:
      if self.IsNotFoundError(e):
        logging.warning('Get instance: %s not found', instance_name)
        return None
      raise

  def ListInstances(self, filter_string=None):
    """Lists instances that matches filter condition.

    Format of filter string can be found in the following URL.
    http://developers.google.com/compute/docs/reference/latest/instances/list

    Args:
      filter_string: Filtering condition.
    Returns:
      List of compute#instance.
    """
    result = self.GetApi().instances().list(
        project=self._project, zone=self._zone, filter=filter_string).execute()
    return result.get('items', [])

  def CreateInstance(self, instance_name, machine_type, boot_disk, disks=None,
                     startup_script='', service_accounts=None,
                     external_ip=True, metadata=None, tags=None,
                     can_ip_forward=False):
    """Creates Google Compute Engine instance.

    Args:
      instance_name: Name of the new instance.
      machine_type: Machine type.  e.g. 'n1-standard-2'
      boot_disk: Name of the persistent disk to be used as a boot disk.
          The disk must preexist in the same zone as the instance.
      disks: List of the names of the extra persistent disks attached to
          the instance in addition to the boot disk.
      startup_script: Content of start up script to run on the new instance.
      service_accounts: List of scope URLs to give to the instance with
          the service account.
      external_ip: Boolean value to indicate whether the new instance has
          an external IP address.
      metadata: Additional key-value pairs in dictionary to add as
          instance metadata.
      tags: String list of tags to attach to the new instance.
      can_ip_forward: Boolean to indicate if the new instance can forward IP
          packets.
    Returns:
      Boolean to indicate whether the instance creation was successful.
    """
    params = {
        'kind': 'compute#instance',
        'name': instance_name,
        'zone': self._ResourceUrl('zones', self._zone,
                                  zoning=ResourceZoning.NONE),
        'machineType': self._ResourceUrl('machineTypes', machine_type),
        'disks': [
            {
                'kind': 'compute#attachedDisk',
                'boot': True,
                'source': self._ResourceUrl('disks', boot_disk),
                'mode': 'READ_WRITE',
                'type': 'PERSISTENT',
            },
        ],
        'metadata': {
            'kind': 'compute#metadata',
            'items': [
                {
                    'key': 'startup-script',
                    'value': startup_script,
                },
            ],
        },
        'canIpForward': can_ip_forward,
        'networkInterfaces': [
            {
                'kind': 'compute#instanceNetworkInterface',
                'accessConfigs': [],
                'network': self._ResourceUrl('networks', 'default',
                                             zoning=ResourceZoning.GLOBAL)
            },
        ],
        'serviceAccounts': [
            {
                'kind': 'compute#serviceAccount',
                'email': 'default',
                'scopes': service_accounts or [],
            },
        ],
    }

    # Attach extra disks.
    if disks:
      for disk in disks:
        params['disks'].append({
            'kind': 'compute#attachedDisk',
            'boot': False,
            'source': self._ResourceUrl('disks', disk),
            'deviceName': disk,
            'mode': 'READ_WRITE',
            'type': 'PERSISTENT',
        })

    # Request external IP address if necessary.
    if external_ip:
      params['networkInterfaces'][0]['accessConfigs'].append({
          'kind': 'compute#accessConfig',
          'type': 'ONE_TO_ONE_NAT',
          'name': 'External NAT',
      })

    # Add metadata.
    if metadata:
      for key, value in metadata.items():
        params['metadata']['items'].append({'key': key, 'value': value})

    # Add tags.
    if tags:
      params['tags'] = {'items': tags}

    operation = self.GetApi().instances().insert(
        project=self._project, zone=self._zone, body=params).execute()

    return self._ParseOperation(
        operation, 'Instance creation: %s' % instance_name)

  def DeleteInstance(self, instance_name):
    """Deletes Google Compute Engine instance.

    Args:
      instance_name: Name of the instance to delete.
    Returns:
      Boolean to indicate whether the instance deletion was successful.
    """
    try:
      operation = self.GetApi().instances().delete(
          project=self._project, zone=self._zone,
          instance=instance_name).execute()
      return self._ParseOperation(
          operation, 'Instance deletion: %s' % instance_name)
    except apiclient.errors.HttpError as e:
      if self.IsNotFoundError(e):
        logging.warning('Delete instance: %s not found', instance_name)
        return False
      raise

  def GetDisk(self, disk_name):
    """Gets persistent disk information.

    Args:
      disk_name: Name of the persistent disk to get information about.
    Returns:
      Google Compute Engine disk resource.  None if not found.
      https://developers.google.com/compute/docs/reference/latest/disks
    Raises:
      HttpError on API error, except for 'resource not found' error.
    """
    try:
      return self.GetApi().disks().get(
          project=self._project, zone=self._zone, disk=disk_name).execute()
    except apiclient.errors.HttpError as e:
      if self.IsNotFoundError(e):
        return None
      raise

  def ListDisks(self, filter_string=None):
    """Lists disks that match filter condition.

    Format of filter string can be found in the following URL.
    https://developers.google.com/compute/docs/reference/latest/disks/list

    Args:
      filter_string: Filtering condition.
    Returns:
      List of compute#disk.
    """
    result = self.GetApi().disks().list(
        project=self._project, zone=self._zone, filter=filter_string).execute()
    return result.get('items', [])

  def CreateDisk(self, disk_name, size_gb=10, image=None):
    """Creates persistent disk in the zone of this API.

    Args:
      disk_name: Name of the new persistent disk.
      size_gb: Size of the new persistent disk in GB.
      image: Machine image name for the new disk to base upon.
          e.g. 'projects/debian-cloud/global/images/debian-7-wheezy-v20131014'
    Returns:
      Boolean to indicate whether the disk creation was successful.
    """
    params = {
        'kind': 'compute#disk',
        'sizeGb': '%d' % size_gb,
        'name': disk_name,
    }
    source_image = self._ResourceUrlFromPath(image) if image else None
    operation = self.GetApi().disks().insert(
        project=self._project, zone=self._zone, body=params,
        sourceImage=source_image).execute()
    return self._ParseOperation(
        operation, 'Disk creation %s' % disk_name)

  def DeleteDisk(self, disk_name):
    """Deletes persistent disk.

    Args:
      disk_name: Name of the persistent disk to delete.
    Returns:
      Boolean to indicate whether the disk deletion was successful.
    """
    operation = self.GetApi().disks().delete(
        project=self._project, zone=self._zone, disk=disk_name).execute()

    return self._ParseOperation(
        operation, 'Disk deletion: %s' % disk_name)

  def AddRoute(self, route_name, next_hop_instance,
               network='default', dest_range='0.0.0.0/0',
               tags=None, priority=100):
    """Adds route to the specified instance.

    Args:
      route_name: Name of the new route.
      next_hop_instance: Instance name of the next hop.
      network: Network to which to add the route.
      dest_range: Destination IP range for the new route.
      tags: List of strings of instance tags.
      priority: Priority of the route.
    Returns:
      Boolean to indicate whether the route creation was successful.
    """
    params = {
        'kind': 'compute#route',
        'name': route_name,
        'destRange': dest_range,
        'priority': priority,
        'network': self._ResourceUrl(
            'networks', network, zoning=ResourceZoning.GLOBAL),
        'nextHopInstance': self._ResourceUrl('instances', next_hop_instance),
    }

    if tags:
      params['tags'] = tags

    operation = self.GetApi().routes().insert(
        project=self._project, body=params).execute()
    return self._ParseOperation(operation, 'Route creation: %s' % route_name)

  def DeleteRoute(self, route_name):
    """Deletes route by name.

    Args:
      route_name: Name of the route to delete.
    Returns:
      Boolean to indicate whether the route deletion was successful.
    """
    try:
      operation = self.GetApi().routes().delete(
          project=self._project, route=route_name).execute()
      return self._ParseOperation(operation, 'Route deletion: %s' % route_name)
    except apiclient.errors.HttpError as e:
      if self.IsNotFoundError(e):
        logging.warning('Delete route: %s not found', route_name)
        return False
      raise

########NEW FILE########
__FILENAME__ = gce_api_test
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests of gce_api.py."""



import unittest

import apiclient
import mock
import oauth2client
import oauth2client.client

import gce_api


class GceApiTest(unittest.TestCase):
  """Unit test class of GceApi."""

  def setUp(self):
    self.gce_api = gce_api.GceApi('gce_api_test', 'CLIENT_ID', 'CLIENT_SECRET',
                                  'project-name', 'zone-name')

  def tearDown(self):
    mock.patch.stopall()

  def _MockGoogleClientApi(self, credentials_validity=True):
    """Sets up mocks for Google Client API library.

    Args:
      credentials_validity: Type/validity of locally cached credentials.
          None for no local credentials, False for invalid local credentials,
          True for valid local credentials.
    Returns:
      Dictionary that holds mocks created.
    """
    mock_local_credentials = mock.MagicMock(
        spec=oauth2client.client.Credentials, name='Mock Credentials')
    mock_http_local = mock.MagicMock(
        name='HTTP authorized by local credentials')
    mock_local_credentials.authorize.return_value = mock_http_local

    mock_new_credentials = mock.MagicMock(
        spec=oauth2client.client.Credentials, name='Mock New Credentials')
    mock_http_new = mock.MagicMock(name='HTTP authorized by new credentials')
    mock_new_credentials.authorize.return_value = mock_http_new
    mock_api = mock.MagicMock(name='Google Client API')

    mock_storage_class = mock.patch('oauth2client.file.Storage').start()
    mock_flow_class = mock.patch(
        'oauth2client.client.OAuth2WebServerFlow').start()
    mock.patch('oauth2client.tools.run',
               return_value=mock_new_credentials).start()
    mock.patch('apiclient.discovery.build', return_value=mock_api).start()
    mock.patch('httplib2.Http').start()

    mock_storage = mock_storage_class.return_value
    if credentials_validity is None:
      mock_storage.get.return_value = None
    else:
      mock_storage.get.return_value = mock_local_credentials
      mock_local_credentials.invalid = not credentials_validity
    mock_flow = mock_flow_class.return_value
    apiclient.discovery.build = mock.MagicMock(return_value=mock_api)

    return {'api': mock_api,
            'storage_class': mock_storage_class,
            'storage': mock_storage,
            'flow_class': mock_flow_class,
            'flow': mock_flow,
            'local_credentials': mock_local_credentials,
            'http_authorized_by_local_credentials': mock_http_local,
            'new_credentials': mock_new_credentials,
            'http_authorized_by_new_credentials': mock_http_new}

  def testGetApi_CachedCredentials(self):
    """Unit test of GetApi().  Local credentials are valid."""
    my_mocks = self._MockGoogleClientApi()

    api = self.gce_api.GetApi()

    self.assertEqual(my_mocks['api'], api)
    self.assertEqual(1, my_mocks['storage_class'].call_count)
    # When cached credentials are valid, OAuth2 dance won't happen.
    self.assertFalse(my_mocks['flow_class'].called)
    self.assertFalse(oauth2client.tools.run.called)
    self.assertEqual(1, my_mocks['local_credentials'].authorize.call_count)
    apiclient.discovery.build.assert_called_once_with(
        'compute', mock.ANY,
        http=my_mocks['http_authorized_by_local_credentials'])
    self.assertRegexpMatches(
        apiclient.discovery.build.call_args[0][1], '^v\\d')

  def testGetApi_InvalidCachedCredentials(self):
    """Unit test of GetApi().  Local credentials are invalid."""
    my_mocks = self._MockGoogleClientApi(False)

    api = self.gce_api.GetApi()

    self.assertEqual(my_mocks['api'], api)
    self.assertEqual(1, my_mocks['storage_class'].call_count)
    self.assertTrue(my_mocks['flow_class'].called)
    oauth2client.tools.run.assert_called_once_with(
        my_mocks['flow'], my_mocks['storage'])
    # New credentials are used.
    self.assertEqual(1, my_mocks['new_credentials'].authorize.call_count)
    apiclient.discovery.build.assert_called_once_with(
        'compute', mock.ANY,
        http=my_mocks['http_authorized_by_new_credentials'])
    self.assertRegexpMatches(
        apiclient.discovery.build.call_args[0][1], '^v\\d')

  def testGetApi_NoCachedCredentials(self):
    """Unit test of GetApi().  Local credentials are invalid."""
    my_mocks = self._MockGoogleClientApi(None)

    api = self.gce_api.GetApi()

    self.assertEqual(my_mocks['api'], api)
    self.assertEqual(1, my_mocks['storage_class'].call_count)
    self.assertTrue(my_mocks['flow_class'].called)
    oauth2client.tools.run.assert_called_once_with(
        my_mocks['flow'], my_mocks['storage'])
    # New credentials are used.
    self.assertEqual(1, my_mocks['new_credentials'].authorize.call_count)
    apiclient.discovery.build.assert_called_once_with(
        'compute', mock.ANY,
        http=my_mocks['http_authorized_by_new_credentials'])
    self.assertRegexpMatches(
        apiclient.discovery.build.call_args[0][1], '^v\\d')

  def testGetInstance(self):
    """Unit test of GetInstance()."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)

    instance_info = self.gce_api.GetInstance('instance-name')

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.get.assert_called_once_with(
        project='project-name', zone='zone-name', instance='instance-name')
    (mock_api.instances.return_value.get.return_value.execute.
     assert_called_once_with())
    self.assertEqual(mock_api.instances.return_value.get.return_value.
                     execute.return_value,
                     instance_info)

  def testListInstances_NoFilter(self):
    """Unit test of ListInstances() without filter string."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.instances.return_value.list.return_value.execute.return_value = {
        'items': ['dummy', 'list']
    }

    instance_list = self.gce_api.ListInstances()

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.list.assert_called_once_with(
        project='project-name', zone='zone-name', filter=None)
    (mock_api.instances.return_value.list.return_value.execute.
     assert_called_once_with())
    self.assertEqual(['dummy', 'list'], instance_list)

  def testListInstances_Filter(self):
    """Unit test of ListInstances() with filter string."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.instances.return_value.list.return_value.execute.return_value = {
        'items': ['dummy', 'list']
    }

    instance_list = self.gce_api.ListInstances('filter condition')

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.list.assert_called_once_with(
        project='project-name', zone='zone-name', filter='filter condition')
    (mock_api.instances.return_value.list.return_value.execute.
     assert_called_once_with())
    self.assertEqual(['dummy', 'list'], instance_list)

  def testCreateInstance_Success(self):
    """Unit test of CreateInstance() with success result."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.instances.return_value.insert.return_value.execute.return_value = {
        'name': 'instance-name'
    }

    self.assertTrue(self.gce_api.CreateInstance(
        'instance-name', 'machine-type', 'image-name'))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.insert.assert_called_once_with(
        project='project-name', zone='zone-name', body=mock.ANY)
    (mock_api.instances.return_value.insert.return_value.execute.
     assert_called_once_with())

  def testCreateInstance_SuccessWithWarning(self):
    """Unit test of CreateInstance() with warning."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.instances.return_value.insert.return_value.execute.return_value = {
        'name': 'instance-name',
        'warnings': [
            {
                'code': 'some warning code',
                'message': 'some warning message'
            }
        ]
    }

    # CreateInstance() returns True for warning.
    self.assertTrue(self.gce_api.CreateInstance(
        'instance-name', 'machine-type', 'image-name'))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.insert.assert_called_once_with(
        project='project-name', zone='zone-name', body=mock.ANY)
    (mock_api.instances.return_value.insert.return_value.execute.
     assert_called_once_with())

  def testCreateInstance_Error(self):
    """Unit test of CreateInstance() with error."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.instances.return_value.insert.return_value.execute.return_value = {
        'name': 'instance-name',
        'error': {
            'errors': [
                {
                    'code': 'some error code',
                    'message': 'some error message'
                }
            ]
        }
    }

    # CreateInstance() returns False.
    self.assertFalse(self.gce_api.CreateInstance(
        'instance-name', 'machine-type', 'image-name'))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.insert.assert_called_once_with(
        project='project-name', zone='zone-name', body=mock.ANY)
    (mock_api.instances.return_value.insert.return_value.execute.
     assert_called_once_with())

  def testDeleteInstance(self):
    """Unit test of DeleteInstance()."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.instances.return_value.delete.return_value.execute.return_value = {
        'status': 'RUNNING'
    }

    self.assertTrue(self.gce_api.DeleteInstance('instance-name'))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.instances.return_value.delete.assert_called_once_with(
        project='project-name', zone='zone-name', instance='instance-name')
    (mock_api.instances.return_value.delete.return_value.execute.
     assert_called_once_with())

  def testGetDisk(self):
    """Unit test of GetDisk()."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)

    disk_info = self.gce_api.GetDisk('disk-name')

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.disks.return_value.get.assert_called_once_with(
        project='project-name', zone='zone-name', disk='disk-name')
    (mock_api.disks.return_value.get.return_value.execute.
     assert_called_once_with())
    self.assertEqual(mock_api.disks.return_value.get.return_value.
                     execute.return_value,
                     disk_info)

  def testListDisks_NoFilter(self):
    """Unit test of ListDisks() without filter string."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.disks.return_value.list.return_value.execute.return_value = {
        'items': ['dummy', 'list']
    }

    instance_list = self.gce_api.ListDisks()

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.disks.return_value.list.assert_called_once_with(
        project='project-name', zone='zone-name', filter=None)
    (mock_api.disks.return_value.list.return_value.execute.
     assert_called_once_with())
    self.assertEqual(['dummy', 'list'], instance_list)

  def testListInstance_Filter(self):
    """Unit test of ListDisks() with filter string."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.disks.return_value.list.return_value.execute.return_value = {
        'items': ['dummy', 'list']
    }

    instance_list = self.gce_api.ListDisks('filter condition')

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.disks.return_value.list.assert_called_once_with(
        project='project-name', zone='zone-name', filter='filter condition')
    (mock_api.disks.return_value.list.return_value.execute.
     assert_called_once_with())
    self.assertEqual(['dummy', 'list'], instance_list)

  def testCreateDisk_WithImage(self):
    """Unit test of CreateDisk() with image."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.disks.return_value.insert.return_value.execute.return_value = {
        'name': 'disk-name'
    }

    self.assertTrue(self.gce_api.CreateDisk(
        'disk-name', image='path/to/image'))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.disks.return_value.insert.assert_called_once_with(
        project='project-name', zone='zone-name', body=mock.ANY,
        sourceImage='https://www.googleapis.com/compute/v1/path/to/image')
    params = mock_api.disks.return_value.insert.call_args[1]['body']
    self.assertEqual(10, int(params['sizeGb']))
    self.assertEqual('disk-name', params['name'])
    (mock_api.disks.return_value.insert.return_value.execute.
     assert_called_once_with())

  def testCreateDisk_WithSizeWithNoImage(self):
    """Unit test of CreateDisk() with size."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.disks.return_value.insert.return_value.execute.return_value = {
        'name': 'disk-name'
    }

    self.assertTrue(self.gce_api.CreateDisk(
        'disk-name', size_gb=1234))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.disks.return_value.insert.assert_called_once_with(
        project='project-name', zone='zone-name', body=mock.ANY,
        sourceImage=None)
    params = mock_api.disks.return_value.insert.call_args[1]['body']
    self.assertEqual(1234, int(params['sizeGb']))
    self.assertEqual('disk-name', params['name'])
    (mock_api.disks.return_value.insert.return_value.execute.
     assert_called_once_with())

  def testDeleteDisk(self):
    """Unit test of DeleteDisk()."""
    mock_api = mock.MagicMock(name='Mock Google Client API')
    self.gce_api.GetApi = mock.MagicMock(return_value=mock_api)
    mock_api.disks.return_value.delete.return_value.execute.return_value = {
        'status': 'RUNNING'
    }

    self.assertTrue(self.gce_api.DeleteDisk('disk-name'))

    self.assertEqual(1, self.gce_api.GetApi.call_count)
    mock_api.disks.return_value.delete.assert_called_once_with(
        project='project-name', zone='zone-name', disk='disk-name')
    (mock_api.disks.return_value.delete.return_value.execute.
     assert_called_once_with())


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = gce_cluster
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Manipulate Hadoop cluster on Google Compute Engine."""



import logging
import os
import os.path
import subprocess
import time

import gce_api


def MakeScriptRelativePath(relative_path):
  """Converts file path relative to this script to valid path for OS."""
  return os.path.join(os.path.dirname(__file__), relative_path)


class ClusterSetUpError(Exception):
  """Error during Hadoop cluster set-up."""


class ClusterDeletionTimeout(Exception):
  """Time out during cluster deletion."""


class EnvironmentSetUpError(Exception):
  """Exception raised when environment set-up script has an error."""


class RemoteExecutionError(Exception):
  """Remote command execution has an error."""


class MapReduceError(Exception):
  """MapReduce job start failure."""


class GceCluster(object):
  """Class to start Compute Engine server farm for Hadoop cluster.

  This class starts up Compute Engines with appropriate configuration for
  Hadoop cluster.  The server farm consists of 1 'master' and multiple
  'workers'.  Hostnames are set by /etc/hosts so that master and workers
  can recognize each other by hostnames.  The common SSH key is distributed
  so that user hadoop can ssh with each other without password.  (SSH is
  the way Hadoop uses for communication.)
  """

  CLIENT_ID = '{{{{ client_id }}}}'
  CLIENT_SECRET = '{{{{ client_secret }}}}'

  DEFAULT_ZONE = 'us-central1-a'
  DEFAULT_IMAGE = ('projects/debian-cloud/global/images/'
                   'debian-7-wheezy-v20131120')
  DEFAULT_MACHINE_TYPE = 'n1-highcpu-4'
  DEFAULT_DATA_DISK_SIZE_GB = 500
  COMPUTE_STARTUP_SCRIPT = 'startup-script.sh'

  LOCAL_TMP_DIR = '.'
  SSH_KEY_DIR_NAME = 'ssh-key'
  PRIVATE_KEY_NAME = 'id_rsa'
  PUBLIC_KEY_NAME = PRIVATE_KEY_NAME + '.pub'
  PRIVATE_KEY_FILE = os.path.join(
      LOCAL_TMP_DIR, SSH_KEY_DIR_NAME, PRIVATE_KEY_NAME)
  PUBLIC_KEY_FILE = os.path.join(
      LOCAL_TMP_DIR, SSH_KEY_DIR_NAME, PUBLIC_KEY_NAME)

  MASTER_NAME = 'hm'
  WORKER_NAME_CORE = 'hw'
  WORKER_TAG_CORE = 'hadoop-workers'
  ROUTE_NAME_CORE = 'hadoop-worker-route'

  INSTANCE_ROLES = {
      'master': ['NameNode', 'JobTracker'],
      'worker': ['DataNode', 'TaskTracker'],
  }

  # Appendix of the name of the data disk.
  DATA_DISK_APPENDIX = '-data'

  DISK_CREATION_WAIT_INTERVAL = 3
  DISK_CREATION_MAX_WAIT_TIMES = 100
  INSTANCE_STATUS_CHECK_INTERVAL = 15
  MAX_MASTER_STATUS_CHECK_TIMES = 40  # Waits up to 10min (15s x 40)
  MAX_WORKERS_CHECK_TIMES = 120  # Waits up to 30min (15s x 120)
  DELETION_CHECK_INTERVAL = 5
  DELETION_MAX_CHECK_TIMES = 24

  def __init__(self, flags):
    self.api = None
    self.flags = flags
    if getattr(flags, 'bucket', ''):
      self.tmp_storage = 'gs://%s/mapreduce/tmp' % flags.bucket

    if getattr(flags, 'prefix', ''):
      self.master_name = flags.prefix + '-' + self.MASTER_NAME
      self.worker_name_template = '%s-%s-%%03d' % (
          flags.prefix, self.WORKER_NAME_CORE)
      self.worker_name_pattern = '%s-%s-\\d+' % (
          flags.prefix, self.WORKER_NAME_CORE)
      self.worker_tag = '%s-%s' % (flags.prefix, self.WORKER_TAG_CORE)
      self.route_name = '%s-%s' % (flags.prefix, self.ROUTE_NAME_CORE)
    else:
      self.master_name = self.MASTER_NAME
      self.worker_name_template = self.WORKER_NAME_CORE + '-%03d'
      self.worker_name_pattern = '%s-\\d+' % self.WORKER_NAME_CORE
      self.worker_tag = self.WORKER_TAG_CORE
      self.route_name = self.ROUTE_NAME_CORE

    self.zone = getattr(self.flags, 'zone', None) or self.DEFAULT_ZONE
    self.data_disk_size_gb = getattr(self.flags, 'data_disk_gb', 0)
    if self.data_disk_size_gb <= 0:
      self.data_disk_size_gb = self.DEFAULT_DATA_DISK_SIZE_GB
    self.startup_script = None
    self.private_key = None
    self.public_key = None
    logging.debug('Current directory: %s', os.getcwd())

  def EnvironmentSetUp(self):
    """Sets up Hadoop-on-Compute environment.

    Must be run once per project/Cloud Storage bucket pair.

    Raises:
      EnvironmentSetUpError: Script failed.
    """
    command = ' '.join([MakeScriptRelativePath('preprocess.sh'),
                        self.LOCAL_TMP_DIR, self.flags.project,
                        self.tmp_storage])
    logging.debug('Environment set-up command: %s', command)
    if subprocess.call(command, shell=True):
      # Non-zero return code indicates an error.
      raise EnvironmentSetUpError('Environment set up failed.')

  def _WorkerName(self, index):
    """Returns Hadoop worker name with specified worker index."""
    return self.worker_name_template % index

  def _GetApi(self):
    if not self.api:
      self.api = gce_api.GceApi('hadoop_on_compute',
                                self.CLIENT_ID, self.CLIENT_SECRET,
                                self.flags.project, self.zone)
    return self.api

  def _WaitForDiskReady(self, disk_name):
    """Waits for the persistent disk get ready.

    Args:
      disk_name: Name of the persistent disk.
    Raises:
      ClusterSetUpError: persistent disk didn't get ready until timeout.
    """
    for _ in xrange(self.DISK_CREATION_MAX_WAIT_TIMES):
      logging.info('Waiting for boot disk %s getting ready...', disk_name)
      disk_status = self._GetApi().GetDisk(disk_name)
      if disk_status and disk_status.get('status', None) == 'READY':
        logging.info('Disk %s created successfully.', disk_name)
        break
      time.sleep(self.DISK_CREATION_WAIT_INTERVAL)
    else:
      raise ClusterSetUpError(
          'Persistent disk %s creation timed out.' % disk_name)

  def _StartInstance(self, instance_name, role):
    """Starts single Compute Engine instance.

    Args:
      instance_name: Name of the instance.
      role: Instance role name.  Must be one of the keys of INSTANCE_ROLES.
    Raises:
      ClusterSetUpError: Role name was invalid.
    """
    logging.info('Starting instance: %s', instance_name)

    # Use the same disk name as instance name.
    boot_disk_name = instance_name
    data_disk_name = instance_name + self.DATA_DISK_APPENDIX

    # If the boot disk doesn't already exist, create.
    if not self._GetApi().GetDisk(boot_disk_name):
      image = self.flags.image or self.DEFAULT_IMAGE
      if not self._GetApi().CreateDisk(boot_disk_name, image=image):
        raise ClusterSetUpError(
            'Failed to create boot disk: %s' % boot_disk_name)
      self._WaitForDiskReady(boot_disk_name)

    # If the data disk doesn't already exist, create.
    if not self._GetApi().GetDisk(data_disk_name):
      if not self._GetApi().CreateDisk(data_disk_name,
                                       size_gb=self.data_disk_size_gb):
        raise ClusterSetUpError(
            'Failed to create data disk: %s' % data_disk_name)
      self._WaitForDiskReady(data_disk_name)

    # Load start-up script.
    if not self.startup_script:
      self.startup_script = open(
          MakeScriptRelativePath(self.COMPUTE_STARTUP_SCRIPT)).read()

    # Load SSH keys.
    if not self.private_key:
      self.private_key = open(self.PRIVATE_KEY_FILE).read()
    if not self.public_key:
      self.public_key = open(self.PUBLIC_KEY_FILE).read()

    metadata = {
        'num-workers': self.flags.num_workers,
        'hadoop-master': self.master_name,
        'hadoop-worker-template': self.worker_name_template,
        'tmp-cloud-storage': self.tmp_storage,
        'custom-command': self.flags.command,
        'hadoop-private-key': self.private_key,
        'hadoop-public-key': self.public_key,
        'worker-external-ip': int(self.flags.external_ip == 'all'),
        'data-disk-id': data_disk_name,
    }

    if role not in self.INSTANCE_ROLES:
      raise ClusterSetUpError('Invalid instance role name: %s' % role)
    for command in self.INSTANCE_ROLES[role]:
      metadata[command] = 1

    # Assign an external IP to the master all the time, and to the worker
    # with external IP address.
    external_ip = False
    if role == 'master' or self.flags.external_ip == 'all':
      external_ip = True

    can_ip_forward = False
    if role == 'master' and self.flags.external_ip == 'master':
      # Enable IP forwarding on master with workers without
      # external IP addresses.
      can_ip_forward = True

    # Assign a tag to workers for routing.
    tags = None
    if role == 'worker':
      tags = [self.worker_tag]

    self._GetApi().CreateInstance(
        instance_name,
        self.flags.machinetype or self.DEFAULT_MACHINE_TYPE,
        boot_disk=boot_disk_name,
        disks=[data_disk_name],
        startup_script=self.startup_script,
        service_accounts=[
            'https://www.googleapis.com/auth/devstorage.full_control'],
        external_ip=external_ip,
        metadata=metadata, tags=tags,
        can_ip_forward=can_ip_forward)

  def _CheckInstanceRunning(self, instance_name):
    """Checks if instance status is 'RUNNING'."""
    instance_info = self._GetApi().GetInstance(instance_name)
    if not instance_info:
      logging.info('Instance %s has not yet started', instance_name)
      return False
    instance_status = instance_info.get('status', None)
    logging.info('Instance %s status: %s', instance_name, instance_status)
    return True if instance_status == 'RUNNING' else False

  def _CheckSshReady(self, instance_name):
    """Checks if the instance is ready to connect via SSH.

    Hadoop-on-Compute uses SSH to copy script files and execute remote commands.
    Connects with SSH and exits immediately to see if SSH connection works.

    Args:
      instance_name: Name of the instance.
    Returns:
      Boolean to indicate whether the instance is ready to SSH.
    """
    command = ('gcutil ssh --project=%s --zone=%s '
               '--ssh_arg "-o ConnectTimeout=10" '
               '--ssh_arg "-o StrictHostKeyChecking=no" '
               '%s exit') % (self.flags.project, self.zone, instance_name)
    logging.debug('SSH availability check command: %s', command)
    if subprocess.call(command, shell=True):
      # Non-zero return code indicates an error.
      logging.info('SSH is not yet ready on %s', instance_name)
      return False
    else:
      return True

  def _MasterSshChecker(self):
    """Returns generator that indicates whether master is ready to SSH.

    Yields:
      False until master is ready to SSH.
    """
    while not self._CheckInstanceRunning(self.master_name):
      yield False
    while not self._CheckSshReady(self.master_name):
      yield False

  def _WaitForMasterSsh(self):
    """Waits until the master instance is ready to SSH.

    Raises:
      ClusterSetUpError: Master set-up timed out.
    """
    wait_counter = 0
    for _ in self._MasterSshChecker():
      if wait_counter >= self.MAX_MASTER_STATUS_CHECK_TIMES:
        logging.critical('Hadoop master set up time out')
        raise ClusterSetUpError('Hadoop master set up time out')
      logging.info('Waiting for the master instance to get ready...')
      time.sleep(self.INSTANCE_STATUS_CHECK_INTERVAL)
      wait_counter += 1

  def _WorkerStatusChecker(self):
    """Returns generator that indicates how many workers are RUNNING.

    The returned generator finishes iteration when all workers are in
    RUNNING status.

    Yields:
      Number of RUNNING workers.
    """
    workers = [self._WorkerName(i) for i in xrange(self.flags.num_workers)]
    while True:
      running_workers = 0
      for worker_name in workers:
        if self._CheckInstanceRunning(worker_name):
          running_workers += 1
      if running_workers == self.flags.num_workers:
        return
      yield running_workers

  def _WaitForWorkersReady(self):
    """Waits until all workers are in RUNNING status.

    Raises:
      ClusterSetUpError: Workers set-up timed out.
    """
    wait_counter = 0
    for running_workers in self._WorkerStatusChecker():
      logging.info('%d out of %d workers RUNNING',
                   running_workers, self.flags.num_workers)
      if wait_counter >= self.MAX_WORKERS_CHECK_TIMES:
        logging.critical('Hadoop worker set up time out')
        raise ClusterSetUpError('Hadoop worker set up time out')
      logging.info('Waiting for the worker instances to start...')
      time.sleep(self.INSTANCE_STATUS_CHECK_INTERVAL)
      wait_counter += 1
    logging.info('All workers are RUNNING now.')

  def StartCluster(self):
    """Starts Hadoop cluster on Compute Engine."""
    # Create a route if no external IP addresses are assigned to the workers.
    if self.flags.external_ip == 'all':
      self._GetApi().DeleteRoute(self.route_name)
    else:
      self._GetApi().AddRoute(self.route_name, self.master_name,
                              tags=[self.worker_tag])

    # Start master instance.
    self._StartInstance(self.master_name, role='master')
    self._WaitForMasterSsh()

    # Start worker instances.
    for i in xrange(self.flags.num_workers):
      self._StartInstance(self._WorkerName(i), role='worker')

    self._WaitForWorkersReady()
    self._ShowHadoopInformation()

  @classmethod
  def _DeleteResource(cls, filter_string, list_method,
                      delete_method, get_method):
    """Deletes Compute Engine resources that match the filter.

    Args:
      filter_string: Filter string of the resource.
      list_method: Method to list the resources.
      delete_method: Method to delete the single resource.
      get_method: Method to get the status of the single resource.
    Raises:
      ClusterDeletionTimeout: the resource deletion times out.
    """
    while True:
      list_of_resources = list_method(filter_string)
      resource_names = [i['name'] for i in list_of_resources]
      if not resource_names:
        break
      for name in resource_names:
        logging.info('  %s', name)
        delete_method(name)

      for _ in xrange(cls.DELETION_MAX_CHECK_TIMES):
        still_alive = []
        for name in resource_names:
          if get_method(name):
            still_alive.append(name)
          else:
            logging.info('Deletion complete: %s', name)
        if not still_alive:
          break
        resource_names = still_alive
        time.sleep(cls.DELETION_CHECK_INTERVAL)
      else:
        raise ClusterDeletionTimeout('Resource deletion time out')

  def TeardownCluster(self):
    """Deletes Compute Engine instances with likely names."""
    # Delete route that might have been created at start up time.
    self._GetApi().DeleteRoute(self.route_name)

    # Delete instances and boot disk.
    instance_name_filter = 'name eq "^(%s|%s)$"' % (
        self.master_name, self.worker_name_pattern)
    logging.info('Delete instances:')
    self._DeleteResource(
        instance_name_filter, self._GetApi().ListInstances,
        self._GetApi().DeleteInstance, self._GetApi().GetInstance)

    # Delete persistent disks (boot disks and data disks).
    disk_name_filter = 'name eq "^(%s|%s)(%s)?$"' % (
        self.master_name, self.worker_name_pattern, self.DATA_DISK_APPENDIX)
    logging.info('Delete persistent disks:')
    self._DeleteResource(
        disk_name_filter, self._GetApi().ListDisks,
        self._GetApi().DeleteDisk, self._GetApi().GetDisk)

  def _StartScriptAtMaster(self, script, *params):
    """Injects script to master instance and runs it as hadoop user.

    run-script-remote.sh script copies the specified file to the master
    instance, and executes it on the master with specified parameters.
    Additinal parameters are passed to the script.

    Args:
      script: Script file to be run on master instance.
      *params: Additional parameters to be passed to the script.
    Raises:
      RemoteExecutionError: Remote command has an error.
    """
    command = ' '.join([
        MakeScriptRelativePath('run-script-remote.sh'),
        self.flags.project or '""', self.zone or '""',
        self.master_name, script, 'hadoop'] + list(params))
    logging.debug('Remote command at master: %s', command)
    if subprocess.call(command, shell=True):
      # Non-zero return code indicates an error.
      raise RemoteExecutionError('Remote execution error')

  def _ShowHadoopInformation(self):
    """Shows Hadoop master information."""
    instance = self._GetApi().GetInstance(self.master_name)
    external_ip = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
    logging.info('')
    logging.info('Hadoop cluster is set up, and workers will be eventually '
                 'recognized by the master.')
    logging.info('HDFS Console  http://%s:50070/', external_ip)
    logging.info('MapReduce Console  http://%s:50030/', external_ip)
    logging.info('')

  def _SetUpMapperReducer(self, mr_file, mr_dir):
    """Prepares mapper or reducer program.

    If local program is specified as mapper or reducer, uploads it to Cloud
    Storage so that Hadoop master downloads it.  If program is already on
    Cloud Storage, just use it.  If empty, use 'cat' command as identity
    mapper/reducer.

    Args:
      mr_file: Mapper or reducer program on local, on Cloud Storage or empty.
      mr_dir: Location on Cloud Storage to store mapper or reducer program.
    Returns:
      Mapper or reducer to be passed to MapReduce script to run on master.
    Raises:
      MapReduceError: Error on copying mapper or reducer to Cloud Storage.
    """
    if mr_file:
      if mr_file.startswith('gs://'):
        return mr_file
      else:
        mr_on_storage = mr_dir + '/mapper-reducer/' + os.path.basename(mr_file)
        copy_command = 'gsutil cp %s %s' % (mr_file, mr_on_storage)
        logging.debug('Mapper/Reducer copy command: %s', copy_command)
        if subprocess.call(copy_command, shell=True):
          # Non-zero return code indicates an error.
          raise MapReduceError('Mapper/Reducer copy error: %s' % mr_file)
        return mr_on_storage
    else:
      # In streaming, 'cat' works as identity mapper/reducer (nop).
      return 'cat'

  def StartMapReduce(self):
    """Starts MapReduce job with specified mapper, reducer, input, output."""
    mapreduce_dir = 'gs://%s/mapreduce' % self.flags.bucket
    if self.flags.input:
      # Remove trailing '/' if any.
      if self.flags.input[-1] == '/':
        input_dir = self.flags.input[:-1]
      else:
        input_dir = self.flags.input
    else:
      input_dir = mapreduce_dir + '/inputs'

    if self.flags.output:
      # Remove trailing '/' if any.  mapreduce__at__master.sh adds '/' to
      # the output and treat it as directory.
      if self.flags.output[-1] == '/':
        output_dir = self.flags.output[:-1]
      else:
        output_dir = self.flags.output
    else:
      output_dir = mapreduce_dir + '/outputs'

    mapper = self._SetUpMapperReducer(self.flags.mapper, mapreduce_dir)
    reducer = self._SetUpMapperReducer(self.flags.reducer, mapreduce_dir)

    # Upload mappers to copy files between Google Cloud Storage and HDFS.
    command = 'gsutil cp %s %s %s' % (
        MakeScriptRelativePath('gcs_to_hdfs_mapper.sh'),
        MakeScriptRelativePath('hdfs_to_gcs_mapper.sh'),
        mapreduce_dir + '/mapper-reducer/')
    logging.debug('GCS-HDFS mappers upload command: %s', command)
    if subprocess.call(command, shell=True):
      # Non-zero return code indicates an error.
      raise MapReduceError('GCS/HDFS copy mapper upload error')

    self._StartScriptAtMaster(
        'mapreduce__at__master.sh', self.flags.bucket,
        mapper, str(self.flags.mapper_count),
        reducer, str(self.flags.reducer_count),
        input_dir, output_dir)

########NEW FILE########
__FILENAME__ = gce_cluster_test
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests of gce_cluster.py."""



import argparse
import unittest

import mock

import gce_cluster
from gce_cluster import GceCluster


class GceClusterTest(unittest.TestCase):
  """Unit test class for GceCluster."""

  def tearDown(self):
    mock.patch.stopall()

  def _SetUpMocksForClusterStart(self):
    """Sets up mocks for cluster start tests.

    Returns:
      Parent mock that enables calls of other mocks.
    """
    # Patch functions.
    mock_gce_api_class = mock.patch('gce_api.GceApi').start()
    mock_subprocess_call = mock.patch('subprocess.call', return_value=0).start()
    mock_popen = mock.patch('subprocess.Popen').start()
    mock_popen.return_value.returncode = None
    mock_popen.return_value.poll.return_value = 0
    mock_builtin_open = mock.patch('__builtin__.open').start()
    mock_sleep = mock.patch('time.sleep').start()

    # Create parent mock and attach other mocks to it, so that we can
    # track call order of all mocks.
    parent_mock = mock.MagicMock()
    parent_mock.attach_mock(mock_gce_api_class, 'GceApi')
    parent_mock.attach_mock(
        mock_gce_api_class.return_value.CreateInstance,
        'CreateInstance')
    parent_mock.attach_mock(
        mock_gce_api_class.return_value.GetInstance,
        'GetInstance')
    parent_mock.attach_mock(
        mock_gce_api_class.return_value.CreateDisk,
        'CreateDisk')
    parent_mock.attach_mock(
        mock_gce_api_class.return_value.GetDisk,
        'GetDisk')
    parent_mock.attach_mock(mock_subprocess_call, 'subprocess_call')
    parent_mock.attach_mock(mock_popen, 'Popen')
    parent_mock.attach_mock(mock_popen.return_value.poll, 'poll')
    parent_mock.attach_mock(mock_builtin_open, 'open')
    parent_mock.attach_mock(mock_sleep, 'sleep')

    mock_gce_api_class.return_value.GetInstance.return_value = {
        'status': 'RUNNING',
        'networkInterfaces': [{
            'accessConfigs': [{
                'natIP': '1.2.3.4',
            }],
        }],
    }

    # Total 6 disks (2 per instance x 3 instances).
    mock_gce_api_class.return_value.GetDisk.side_effect = [
        None,
        {'status': 'READY'},
        None,
        {'status': 'READY'},
        None,
        {'status': 'READY'},
        None,
        {'status': 'READY'},
        None,
        {'status': 'READY'},
        None,
        {'status': 'READY'},
    ]

    return parent_mock

  def testEnvironmentSetUp_Success(self):
    """Unit test of EnvironmentSetUp()."""
    with mock.patch('subprocess.call', return_value=0) as mock_subprocess_call:
      GceCluster(
          argparse.Namespace(project='project-foo',
                             bucket='bucket-bar')).EnvironmentSetUp()
      mock_subprocess_call.assert_called_once_with(mock.ANY, shell=True)
      self.assertRegexpMatches(
          mock_subprocess_call.call_args[0][0],
          '/preprocess.sh \\S+ project-foo gs://bucket-bar/mapreduce/tmp$')

  def testEnvironmentSetUp_Error(self):
    """Unit test of EnvironmentSetUp() with non-zero return value."""
    # subprocess.call() returns 1.
    with mock.patch('subprocess.call', return_value=1) as mock_subprocess_call:
      # Return value 1 causes EnvironmentSetUpError.
      self.assertRaises(
          gce_cluster.EnvironmentSetUpError,
          GceCluster(
              argparse.Namespace(project='project-foo', bucket='bucket-bar')
              ).EnvironmentSetUp)
      mock_subprocess_call.assert_called_once_with(mock.ANY, shell=True)
      self.assertRegexpMatches(
          mock_subprocess_call.call_args[0][0],
          '/preprocess.sh \\S+ project-foo gs://bucket-bar/mapreduce/tmp$')

  def testStartCluster(self):
    """Unit test of StartCluster()."""
    parent_mock = self._SetUpMocksForClusterStart()

    GceCluster(argparse.Namespace(
        project='project-hoge', bucket='bucket-fuga',
        machinetype='', image='', zone='us-central2-a', num_workers=2,
        command='', external_ip='all')).StartCluster()

    # Make sure internal calls are made with expected order with
    # expected arguments.
    method_calls = parent_mock.method_calls.__iter__()
    # Create GceApi.
    call = method_calls.next()
    self.assertEqual('GceApi', call[0])
    # See if boot disk exists.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hm', call[1][0])
    # Create boot disk.
    call = method_calls.next()
    self.assertEqual('CreateDisk', call[0])
    self.assertEqual('hm', call[1][0])
    # See if boot disk is ready.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hm', call[1][0])
    # See if data disk exists.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hm-data', call[1][0])
    # Create data disk.
    call = method_calls.next()
    self.assertEqual('CreateDisk', call[0])
    self.assertEqual('hm-data', call[1][0])
    # See if data disk is ready.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hm-data', call[1][0])
    # Open start up script for Compute Engine instance.
    call = method_calls.next()
    self.assertEqual('open', call[0])
    self.assertRegexpMatches(call[1][0], 'startup-script\\.sh$')
    # Open private key to pass to Compute Engine instance.
    call = method_calls.next()
    self.assertEqual('open', call[0])
    self.assertRegexpMatches(call[1][0], 'id_rsa$')
    # Open private key to pass to Compute Engine instance.
    call = method_calls.next()
    self.assertEqual('open', call[0])
    self.assertRegexpMatches(call[1][0], 'id_rsa\\.pub$')
    # Create master instance.
    call = method_calls.next()
    self.assertEqual('CreateInstance', call[0])
    self.assertEqual('hm', call[1][0])
    self.assertTrue(call[2]['external_ip'])
    self.assertFalse(call[2]['can_ip_forward'])
    # Check master status.
    call = method_calls.next()
    self.assertEqual('GetInstance', call[0])
    self.assertEqual('hm', call[1][0])
    # Check if master is ready to SSH.
    call = method_calls.next()
    self.assertEqual('subprocess_call', call[0])
    self.assertRegexpMatches(call[1][0], '^gcutil ssh')
    # See if boot disk for worker instance #000 exists.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-000', call[1][0])
    # Create boot disk.
    call = method_calls.next()
    self.assertEqual('CreateDisk', call[0])
    self.assertEqual('hw-000', call[1][0])
    # See if boot disk is ready.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-000', call[1][0])
    # See if data disk exists.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-000-data', call[1][0])
    # Create data disk.
    call = method_calls.next()
    self.assertEqual('CreateDisk', call[0])
    self.assertEqual('hw-000-data', call[1][0])
    # See if data disk is ready.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-000-data', call[1][0])
    # Create worker instance #000.
    call = method_calls.next()
    self.assertEqual('CreateInstance', call[0])
    self.assertEqual('hw-000', call[1][0])
    self.assertTrue(call[2]['external_ip'])
    self.assertFalse(call[2]['can_ip_forward'])
    # See if boot disk for worker instance #001 exists.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-001', call[1][0])
    # Create boot disk.
    call = method_calls.next()
    self.assertEqual('CreateDisk', call[0])
    self.assertEqual('hw-001', call[1][0])
    # See if boot disk is ready.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-001', call[1][0])
    # See if data disk exists.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-001-data', call[1][0])
    # Create data disk.
    call = method_calls.next()
    self.assertEqual('CreateDisk', call[0])
    self.assertEqual('hw-001-data', call[1][0])
    # See if data disk is ready.
    call = method_calls.next()
    self.assertEqual('GetDisk', call[0])
    self.assertEqual('hw-001-data', call[1][0])
    # Create worker instance #001.
    call = method_calls.next()
    self.assertEqual('CreateInstance', call[0])
    self.assertEqual('hw-001', call[1][0])
    self.assertTrue(call[2]['external_ip'])
    self.assertFalse(call[2]['can_ip_forward'])
    # Check worker 000's status
    call = method_calls.next()
    self.assertEqual('GetInstance', call[0])
    self.assertEqual('hw-000', call[1][0])
    # Check worker 001's status
    call = method_calls.next()
    self.assertEqual('GetInstance', call[0])
    self.assertEqual('hw-001', call[1][0])
    # Get master's external IP address.
    call = method_calls.next()
    self.assertEqual('GetInstance', call[0])
    self.assertEqual('hm', call[1][0])
    # End of call list.
    self.assertRaises(StopIteration, method_calls.next)

  def testStartCluster_NoExternalIp(self):
    """Unit test of StartCluster() with no external IP addresses for workers."""
    parent_mock = self._SetUpMocksForClusterStart()

    GceCluster(argparse.Namespace(
        project='project-hoge', bucket='bucket-fuga',
        machinetype='', image='', zone='us-central2-a', num_workers=2,
        command='', external_ip='master')).StartCluster()

    # Just check parameters of CreateInstance.
    # Master instance.
    call = parent_mock.method_calls[10]
    self.assertEqual('CreateInstance', call[0])
    self.assertEqual('hm', call[1][0])
    self.assertTrue(call[2]['external_ip'])
    self.assertTrue(call[2]['can_ip_forward'])

    # Worker 000.
    call = parent_mock.method_calls[19]
    self.assertEqual('CreateInstance', call[0])
    self.assertEqual('hw-000', call[1][0])
    self.assertFalse(call[2]['external_ip'])
    self.assertFalse(call[2]['can_ip_forward'])

    # Worker 001.
    call = parent_mock.method_calls[26]
    self.assertEqual('CreateInstance', call[0])
    self.assertEqual('hw-001', call[1][0])
    self.assertFalse(call[2]['external_ip'])
    self.assertFalse(call[2]['can_ip_forward'])

  def testStartCluster_InstanceStatusError(self):
    """Unit test of StartCluster() instance status error.

    This unit test simulates the situation where status of one of the instances
    doesn't turn into RUNNING.
    """
    parent_mock = self._SetUpMocksForClusterStart()

    # Set hw-000's status to forever STAGING.
    parent_mock.GceApi.return_value.GetInstance.return_value = {
        'status': 'STAGING',
    }

    self.assertRaises(
        gce_cluster.ClusterSetUpError,
        gce_cluster.GceCluster(argparse.Namespace(
            project='project-hoge', bucket='bucket-fuga',
            machinetype='', image='', zone='', num_workers=2,
            command='', external_ip='all')).StartCluster)

    # Ensure ListInstances() and sleep() are called more than 120 times.
    self.assertLessEqual(40, parent_mock.GetInstance.call_count)
    self.assertLessEqual(40, parent_mock.sleep.call_count)

  def testTeardownCluster(self):
    """Unit test of TeardownCluster()."""
    with mock.patch('gce_api.GceApi') as mock_gce_api_class:
      mock_gce_api_class.return_value.ListInstances.side_effect = [
          [
              {'name': 'fugafuga'},
              {'name': 'hogehoge'},
              {'name': 'piyopiyo'},
          ], []
      ]
      mock_gce_api_class.return_value.ListDisks.side_effect = [
          [
              {'name': 'fugafuga-data'},
              {'name': 'hogehoge-data'},
              {'name': 'piyopiyo-data'},
          ], []
      ]
      mock_gce_api_class.return_value.GetInstance.return_value = None
      mock_gce_api_class.return_value.GetDisk.return_value = None

      GceCluster(argparse.Namespace(
          project='project-hoge', zone='zone-fuga')).TeardownCluster()

      mock_gce_api_class.assert_called_once_with(
          'hadoop_on_compute', mock.ANY, mock.ANY,
          'project-hoge', 'zone-fuga')
      (mock_gce_api_class.return_value.ListInstances.
       assert_called_with('name eq "^(hm|hw-\\d+)$"'))
      (mock_gce_api_class.return_value.ListDisks.
       assert_called_with('name eq "^(hm|hw-\\d+)(-data)?$"'))
      # Make sure DeleteInstance() is called for each instance.
      self.assertEqual(
          [mock.call('fugafuga'), mock.call('hogehoge'),
           mock.call('piyopiyo')],
          mock_gce_api_class.return_value.DeleteInstance.call_args_list)
      self.assertEqual(
          [mock.call('fugafuga-data'), mock.call('hogehoge-data'),
           mock.call('piyopiyo-data')],
          mock_gce_api_class.return_value.DeleteDisk.call_args_list)

  def testTeardownCluster_WithPrefix(self):
    """Unit test of TeardownCluster() with prefix."""
    with mock.patch('gce_api.GceApi') as mock_gce_api_class:
      mock_gce_api_class.return_value.ListInstances.side_effect = [
          [{'name': 'wahoooo'}], []
      ]
      mock_gce_api_class.return_value.ListDisks.side_effect = [
          [{'name': 'wahoooo-data'}], []
      ]
      mock_gce_api_class.return_value.GetInstance.return_value = None
      mock_gce_api_class.return_value.GetDisk.return_value = None

      GceCluster(argparse.Namespace(
          project='project-hoge', zone='zone-fuga',
          prefix='boo')).TeardownCluster()

      mock_gce_api_class.assert_called_once_with(
          'hadoop_on_compute', mock.ANY, mock.ANY,
          'project-hoge', 'zone-fuga')
      # Make sure prefix is included in instance name patterns.
      (mock_gce_api_class.return_value.ListInstances.
       assert_called_with('name eq "^(boo-hm|boo-hw-\\d+)$"'))
      (mock_gce_api_class.return_value.ListDisks.
       assert_called_with('name eq "^(boo-hm|boo-hw-\\d+)(-data)?$"'))
      self.assertEqual(
          [mock.call('wahoooo')],
          mock_gce_api_class.return_value.DeleteInstance.call_args_list)
      self.assertEqual(
          [mock.call('wahoooo-data')],
          mock_gce_api_class.return_value.DeleteDisk.call_args_list)

  def testTeardownCluster_NoInstance(self):
    """Unit test of TeardownCluster() with no instance returned by list."""
    with mock.patch('gce_api.GceApi') as mock_gce_api_class:
      # ListInstances() and ListDisks() return empty list.
      mock_gce_api_class.return_value.ListInstances.return_value = []
      mock_gce_api_class.return_value.ListDisks.return_value = []

      GceCluster(argparse.Namespace(
          project='project-hoge', zone='zone-fuga')).TeardownCluster()

      mock_gce_api_class.assert_called_once_with(
          'hadoop_on_compute', mock.ANY, mock.ANY,
          'project-hoge', 'zone-fuga')
      (mock_gce_api_class.return_value.ListInstances.
       assert_called_once_with('name eq "^(hm|hw-\\d+)$"'))
      (mock_gce_api_class.return_value.ListDisks.
       assert_called_once_with('name eq "^(hm|hw-\\d+)(-data)?$"'))
      # Make sure DeleteInstance() is not called.
      self.assertFalse(
          mock_gce_api_class.return_value.DeleteInstance.called)
      # Make sure DeleteDisk() is not called.
      self.assertFalse(
          mock_gce_api_class.return_value.DeleteDisk.called)

  def testStartMapReduce(self):
    """Unit test of StartMapReduce()."""
    mock_subprocess_call = mock.patch('subprocess.call', return_value=0).start()
    mock.patch('gce_cluster.MakeScriptRelativePath',
               side_effect=lambda x: '/path/to/program/' + x).start()

    GceCluster(argparse.Namespace(
        project='project-hoge', bucket='tmp-bucket', zone='zone-fuga',
        input='gs://data/inputs', output='gs://data/outputs',
        mapper='mapper.exe', reducer='reducer.exe',
        mapper_count=5, reducer_count=1,
        prefix='boo')).StartMapReduce()

    # Check all subprocess.call() calls have expected arguments.
    self.assertEqual(4, mock_subprocess_call.call_count)
    self.assertEqual(
        mock.call('gsutil cp mapper.exe '
                  'gs://tmp-bucket/mapreduce/mapper-reducer/mapper.exe',
                  shell=True),
        mock_subprocess_call.call_args_list[0])
    self.assertEqual(
        mock.call('gsutil cp reducer.exe '
                  'gs://tmp-bucket/mapreduce/mapper-reducer/reducer.exe',
                  shell=True),
        mock_subprocess_call.call_args_list[1])
    self.assertEqual(
        mock.call('gsutil cp /path/to/program/gcs_to_hdfs_mapper.sh '
                  '/path/to/program/hdfs_to_gcs_mapper.sh '
                  'gs://tmp-bucket/mapreduce/mapper-reducer/',
                  shell=True),
        mock_subprocess_call.call_args_list[2])
    self.assertEqual(
        mock.call('/path/to/program/run-script-remote.sh project-hoge '
                  'zone-fuga boo-hm mapreduce__at__master.sh hadoop '
                  'tmp-bucket '
                  'gs://tmp-bucket/mapreduce/mapper-reducer/mapper.exe 5 '
                  'gs://tmp-bucket/mapreduce/mapper-reducer/reducer.exe 1 '
                  'gs://data/inputs gs://data/outputs',
                  shell=True),
        mock_subprocess_call.call_args_list[3])


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = shortest-to-longest-mapper
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Mapper sample.

The mapper takes arbitrary text as input.
With the corresponding reducer, the MapReduce task counts occurrence
of the word in the original text.
The output is sorted by the length of the word, and then in alphabetical
order if the length of the word is the same.
"""

import re
import sys


word_pattern = re.compile('[a-z]+')

for line in sys.stdin:
  for match in word_pattern.finditer(line.lower()):
    word = match.group()
    print '%03d:%s\t%s' % (len(word), word, 1)

########NEW FILE########
__FILENAME__ = shortest-to-longest-reducer
#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Reducer sample.

The word is already sorted in the desirable order.
The reducer counts the occurrence of each word and outputs the word
and its occurrence.
"""

import sys


class Word(object):
  """Class to keep current word's occurrence."""

  def __init__(self, word):
    self.word = word
    self.count = 0

  def Print(self):
    print '%s\t%d' % (self.word, self.count)

  def Increment(self, count=1):
    self.count += count


class ShortestToLongestReducer(object):
  """Class to accumulate counts from reducer input lines."""

  def __init__(self):
    self.current_word = None

  def PrintCurrentWord(self):
    """Outputs word count of the currently processing word."""
    if self.current_word:
      self.current_word.Print()

  def ProcessLine(self, line):
    """Process an input line.

    Args:
      line: Input line.
    """
    # Split input to key and value.
    key = line.split('\t', 1)[0]

    # Split key to word-length and word.
    word = key.split(':', 1)[1]

    if not self.current_word:
      self.current_word = Word(word)
    elif self.current_word.word != word:
      self.current_word.Print()
      self.current_word = Word(word)

    self.current_word.Increment()


def main(input_lines):
  reducer = ShortestToLongestReducer()

  for line in input_lines:
    reducer.ProcessLine(line)

  reducer.PrintCurrentWord()


if __name__ == '__main__':
  main(sys.stdin)

########NEW FILE########
