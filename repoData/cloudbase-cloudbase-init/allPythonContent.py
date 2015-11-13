__FILENAME__ = init
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import sys

from oslo.config import cfg

from cloudbaseinit.metadata import factory as metadata_factory
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base as plugins_base
from cloudbaseinit.plugins import factory as plugins_factory

opts = [
    cfg.BoolOpt('allow_reboot', default=True, help='Allows OS reboots '
                'requested by plugins'),
    cfg.BoolOpt('stop_service_on_exit', default=True, help='In case of '
                'execution as a service, specifies if the service '
                'must be gracefully stopped before exiting'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class InitManager(object):
    _PLUGINS_CONFIG_SECTION = 'Plugins'

    def _get_plugins_section(self, instance_id):
        if not instance_id:
            return self._PLUGINS_CONFIG_SECTION
        else:
            return instance_id + "/" + self._PLUGINS_CONFIG_SECTION

    def _get_plugin_status(self, osutils, instance_id, plugin_name):
        return osutils.get_config_value(plugin_name,
                                        self._get_plugins_section(instance_id))

    def _set_plugin_status(self, osutils, instance_id, plugin_name, status):
        osutils.set_config_value(plugin_name, status,
                                 self._get_plugins_section(instance_id))

    def _exec_plugin(self, osutils, service, plugin, instance_id, shared_data):
        plugin_name = plugin.get_name()

        status = self._get_plugin_status(osutils, instance_id, plugin_name)
        if status == plugins_base.PLUGIN_EXECUTION_DONE:
            LOG.debug('Plugin \'%s\' execution already done, skipping',
                      plugin_name)
        else:
            LOG.info('Executing plugin \'%s\'', plugin_name)
            try:
                (status, reboot_required) = plugin.execute(service,
                                                           shared_data)
                self._set_plugin_status(osutils, instance_id, plugin_name,
                                        status)
                return reboot_required
            except Exception, ex:
                LOG.error('plugin \'%(plugin_name)s\' failed with error '
                          '\'%(ex)s\'', {'plugin_name': plugin_name, 'ex': ex})
                LOG.exception(ex)

    def _check_plugin_os_requirements(self, osutils, plugin):
        supported = False
        plugin_name = plugin.get_name()

        (required_platform, min_os_version) = plugin.get_os_requirements()
        if required_platform and sys.platform != required_platform:
            LOG.debug('Skipping plugin: \'%s\'. Platform not supported' %
                      plugin_name)
        else:
            if not min_os_version:
                supported = True
            else:
                os_major, os_minor = min_os_version
                if osutils.check_os_version(os_major, os_minor):
                    supported = True
                else:
                    LOG.debug('Skipping plugin: \'%s\'. OS version not '
                              'supported' % plugin_name)
        return supported

    def configure_host(self):
        osutils = osutils_factory.get_os_utils()
        osutils.wait_for_boot_completion()

        service = metadata_factory.get_metadata_service()
        LOG.info('Metadata service loaded: \'%s\'' %
                 service.get_name())

        instance_id = service.get_instance_id()
        LOG.debug('Instance id: %s', instance_id)

        plugins = plugins_factory.load_plugins()
        plugins_shared_data = {}

        reboot_required = False
        try:
            for plugin in plugins:
                if self._check_plugin_os_requirements(osutils, plugin):
                    if self._exec_plugin(osutils, service, plugin,
                                         instance_id, plugins_shared_data):
                        reboot_required = True
                        if CONF.allow_reboot:
                            break
        finally:
            service.cleanup()

        if reboot_required and CONF.allow_reboot:
            try:
                osutils.reboot()
            except Exception, ex:
                LOG.error('reboot failed with error \'%s\'' % ex)
        elif CONF.stop_service_on_exit:
            osutils.terminate()

########NEW FILE########
__FILENAME__ = factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.utils import classloader

opts = [
    cfg.ListOpt(
        'metadata_services',
        default=[
            'cloudbaseinit.metadata.services.httpservice.HttpService',
            'cloudbaseinit.metadata.services.configdrive.ConfigDriveService',
            'cloudbaseinit.metadata.services.ec2service.EC2Service',
            'cloudbaseinit.metadata.services.maasservice.MaaSHttpService'
        ],
        help='List of enabled metadata service classes, '
        'to be tested fro availability in the provided order. '
        'The first available service will be used to retrieve '
        'metadata')
]

CONF = cfg.CONF
CONF.register_opts(opts)
LOG = logging.getLogger(__name__)


def get_metadata_service():
    # Return the first service that loads correctly
    cl = classloader.ClassLoader()
    for class_path in CONF.metadata_services:
        service = cl.load_class(class_path)()
        try:
            if service.load():
                return service
        except Exception, ex:
            LOG.error("Failed to load metadata service '%s'" % class_path)
            LOG.exception(ex)
    raise Exception("No available service found")

########NEW FILE########
__FILENAME__ = base
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import abc
import time

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging

opts = [
    cfg.IntOpt('retry_count', default=5,
               help='Max. number of attempts for fetching metadata in '
               'case of transient errors'),
    cfg.FloatOpt('retry_count_interval', default=4,
                 help='Interval between attempts in case of transient errors, '
                 'expressed in seconds'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class NotExistingMetadataException(Exception):
    pass


class BaseMetadataService(object):
    def __init__(self):
        self._cache = {}
        self._enable_retry = False

    def get_name(self):
        return self.__class__.__name__

    def load(self):
        self._cache = {}

    @abc.abstractmethod
    def _get_data(self, path):
        pass

    def _exec_with_retry(self, action):
        i = 0
        while True:
            try:
                return action()
            except NotExistingMetadataException:
                raise
            except:
                if self._enable_retry and i < CONF.retry_count:
                    i += 1
                    time.sleep(CONF.retry_count_interval)
                else:
                    raise

    def _get_cache_data(self, path):
        if path in self._cache:
            LOG.debug("Using cached copy of metadata: '%s'" % path)
            return self._cache[path]
        else:
            data = self._exec_with_retry(lambda: self._get_data(path))
            self._cache[path] = data
            return data

    def get_instance_id(self):
        pass

    def get_content(self, name):
        pass

    def get_user_data(self):
        pass

    def get_host_name(self):
        pass

    def get_public_keys(self):
        pass

    def get_network_config(self):
        pass

    def get_admin_password(self):
        pass

    @property
    def can_post_password(self):
        return False

    @property
    def is_password_set(self):
        return False

    def post_password(self, enc_password_b64):
        pass

    def get_client_auth_certs(self):
        pass

    def cleanup(self):
        pass

########NEW FILE########
__FILENAME__ = baseopenstackservice
# Copyright 2014 Cloudbase Solutions Srl
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

import json
import posixpath

from oslo.config import cfg

from cloudbaseinit.metadata.services import base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.utils import x509constants

opts = [
    cfg.StrOpt('metadata_base_url', default='http://169.254.169.254/',
               help='The base URL where the service looks for metadata'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class BaseOpenStackService(base.BaseMetadataService):

    def get_content(self, name):
        path = posixpath.normpath(
            posixpath.join('openstack', 'content', name))
        return self._get_cache_data(path)

    def get_user_data(self):
        path = posixpath.normpath(
            posixpath.join('openstack', 'latest', 'user_data'))
        return self._get_cache_data(path)

    def _get_meta_data(self, version='latest'):
        path = posixpath.normpath(
            posixpath.join('openstack', version, 'meta_data.json'))
        data = self._get_cache_data(path)
        if type(data) is str:
            return json.loads(self._get_cache_data(path))
        else:
            return data

    def get_instance_id(self):
        return self._get_meta_data().get('uuid')

    def get_host_name(self):
        return self._get_meta_data().get('hostname')

    def get_public_keys(self):
        public_keys = self._get_meta_data().get('public_keys')
        if public_keys:
            return public_keys.values()

    def get_network_config(self):
        return self._get_meta_data().get('network_config')

    def get_admin_password(self):
        meta_data = self._get_meta_data()
        meta = meta_data.get('meta')

        if meta and 'admin_pass' in meta:
            password = meta['admin_pass']
        elif 'admin_pass' in meta_data:
            password = meta_data['admin_pass']
        else:
            password = None

        return password

    def get_client_auth_certs(self):
        cert_data = None

        meta_data = self._get_meta_data()
        meta = meta_data.get('meta')

        if meta:
            i = 0
            while True:
                # Chunking is necessary as metadata items can be
                # max. 255 chars long
                cert_chunk = meta.get('admin_cert%d' % i)
                if not cert_chunk:
                    break
                if not cert_data:
                    cert_data = cert_chunk
                else:
                    cert_data += cert_chunk
                i += 1

        if not cert_data:
            # Look if the user_data contains a PEM certificate
            try:
                user_data = self.get_user_data()
                if user_data.startswith(x509constants.PEM_HEADER):
                    cert_data = user_data
            except base.NotExistingMetadataException:
                LOG.debug("user_data metadata not present")

        if cert_data:
            return [cert_data]

########NEW FILE########
__FILENAME__ = configdrive
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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
import shutil
import tempfile
import uuid

from oslo.config import cfg

from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import baseopenstackservice
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.metadata.services.osconfigdrive import factory

opts = [
    cfg.BoolOpt('config_drive_raw_hhd', default=True,
                help='Look for an ISO config drive in raw HDDs'),
    cfg.BoolOpt('config_drive_cdrom', default=True,
                help='Look for a config drive in the attached cdrom drives'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class ConfigDriveService(baseopenstackservice.BaseOpenStackService):
    def __init__(self):
        super(ConfigDriveService, self).__init__()
        self._metadata_path = None

    def load(self):
        super(ConfigDriveService, self).load()

        target_path = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))

        mgr = factory.get_config_drive_manager()
        found = mgr.get_config_drive_files(target_path,
                                           CONF.config_drive_raw_hhd,
                                           CONF.config_drive_cdrom)
        if found:
            self._metadata_path = target_path
            LOG.debug('Metadata copied to folder: \'%s\'' %
                      self._metadata_path)
        return found

    def _get_data(self, path):
        norm_path = os.path.normpath(os.path.join(self._metadata_path, path))
        try:
            with open(norm_path, 'rb') as f:
                return f.read()
        except IOError:
            raise base.NotExistingMetadataException()

    def cleanup(self):
        if self._metadata_path:
            LOG.debug('Deleting metadata folder: \'%s\'' % self._metadata_path)
            shutil.rmtree(self._metadata_path, True)
            self._metadata_path = None

########NEW FILE########
__FILENAME__ = ec2service
# Copyright 2014 Cloudbase Solutions Srl
# Copyright 2012 Mirantis Inc.
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

import posixpath
import urllib2

from oslo.config import cfg

from cloudbaseinit.metadata.services import base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.utils import network

opts = [
    cfg.StrOpt('ec2_metadata_base_url',
               default='http://169.254.169.254/',
               help='The base URL where the service looks for metadata'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class EC2Service(base.BaseMetadataService):
    _metadata_version = '2009-04-04'

    def __init__(self):
        super(EC2Service, self).__init__()
        self._enable_retry = True

    def load(self):
        super(EC2Service, self).load()
        network.check_metadata_ip_route(CONF.ec2_metadata_base_url)

        try:
            self.get_host_name()
            return True
        except Exception, ex:
            LOG.exception(ex)
            LOG.debug('Metadata not found at URL \'%s\'' %
                      CONF.ec2_metadata_base_url)
            return False

    def _get_response(self, req):
        try:
            return urllib2.urlopen(req)
        except urllib2.HTTPError as ex:
            if ex.code == 404:
                raise base.NotExistingMetadataException()
            else:
                raise

    def _get_data(self, path):
        norm_path = posixpath.join(CONF.ec2_metadata_base_url, path)

        LOG.debug('Getting metadata from: %(norm_path)s',
                  {'norm_path': norm_path})
        req = urllib2.Request(norm_path)
        response = self._get_response(req)
        return response.read()

    def get_host_name(self):
        return self._get_cache_data('%s/meta-data/local-hostname' %
                                    self._metadata_version)

    def get_instance_id(self):
        return self._get_cache_data('%s/meta-data/instance-id' %
                                    self._metadata_version)

    def get_public_keys(self):
        ssh_keys = []

        keys_info = self._get_cache_data(
            '%s/meta-data/public-keys' %
            self._metadata_version).split("\n")

        for key_info in keys_info:
            (idx, key_name) = key_info.split('=')

            ssh_key = self._get_cache_data(
                '%(version)s/meta-data/public-keys/%(idx)s/openssh-key' %
                {'version': self._metadata_version, 'idx': idx})
            ssh_keys.append(ssh_key)

        return ssh_keys

    def get_network_config(self):
        # TODO(alexpilotti): add static network support
        pass

########NEW FILE########
__FILENAME__ = httpservice
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import posixpath
import urllib2

from oslo.config import cfg

from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import baseopenstackservice
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.utils import network

opts = [
    cfg.StrOpt('metadata_base_url', default='http://169.254.169.254/',
               help='The base URL where the service looks for metadata'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class HttpService(baseopenstackservice.BaseOpenStackService):
    _POST_PASSWORD_MD_VER = '2013-04-04'

    def __init__(self):
        super(HttpService, self).__init__()
        self._enable_retry = True

    def load(self):
        super(HttpService, self).load()
        network.check_metadata_ip_route(CONF.metadata_base_url)

        try:
            self._get_meta_data()
            return True
        except Exception:
            LOG.debug('Metadata not found at URL \'%s\'' %
                      CONF.metadata_base_url)
            return False

    def _get_response(self, req):
        try:
            return urllib2.urlopen(req)
        except urllib2.HTTPError as ex:
            if ex.code == 404:
                raise base.NotExistingMetadataException()
            else:
                raise

    def _get_data(self, path):
        norm_path = posixpath.join(CONF.metadata_base_url, path)
        LOG.debug('Getting metadata from: %s', norm_path)
        req = urllib2.Request(norm_path)
        response = self._get_response(req)
        return response.read()

    def _post_data(self, path, data):
        norm_path = posixpath.join(CONF.metadata_base_url, path)
        LOG.debug('Posting metadata to: %s', norm_path)
        req = urllib2.Request(norm_path, data=data)
        self._get_response(req)
        return True

    def _get_password_path(self):
        return 'openstack/%s/password' % self._POST_PASSWORD_MD_VER

    @property
    def can_post_password(self):
        try:
            self._get_meta_data(self._POST_PASSWORD_MD_VER)
            return True
        except base.NotExistingMetadataException:
            return False

    @property
    def is_password_set(self):
        path = self._get_password_path()
        return len(self._get_data(path)) > 0

    def post_password(self, enc_password_b64):
        try:
            path = self._get_password_path()
            action = lambda: self._post_data(path, enc_password_b64)
            return self._exec_with_retry(action)
        except urllib2.HTTPError as ex:
            if ex.code == 409:
                # Password already set
                return False
            else:
                raise

########NEW FILE########
__FILENAME__ = maasservice
# Copyright 2014 Cloudbase Solutions Srl
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

import posixpath
import time
import urllib2

from oauth import oauth
from oslo.config import cfg

from cloudbaseinit.metadata.services import base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.utils import x509constants

opts = [
    cfg.StrOpt('maas_metadata_url', default=None,
               help='The base URL for MaaS metadata'),
    cfg.StrOpt('maas_oauth_consumer_key', default="",
               help='The MaaS OAuth consumer key'),
    cfg.StrOpt('maas_oauth_consumer_secret', default="",
               help='The MaaS OAuth consumer secret'),
    cfg.StrOpt('maas_oauth_token_key', default="",
               help='The MaaS OAuth token key'),
    cfg.StrOpt('maas_oauth_token_secret', default="",
               help='The MaaS OAuth token secret'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class MaaSHttpService(base.BaseMetadataService):
    _METADATA_2012_03_01 = '2012-03-01'

    def __init__(self):
        super(MaaSHttpService, self).__init__()
        self._enable_retry = True
        self._metadata_version = self._METADATA_2012_03_01

    def load(self):
        super(MaaSHttpService, self).load()

        if not CONF.maas_metadata_url:
            LOG.debug('MaaS metadata url not set')
        else:
            try:
                self._get_data('%s/meta-data/' % self._metadata_version)
                return True
            except Exception, ex:
                LOG.exception(ex)
                LOG.debug('Metadata not found at URL \'%s\'' %
                          CONF.maas_metadata_url)
        return False

    def _get_response(self, req):
        try:
            return urllib2.urlopen(req)
        except urllib2.HTTPError as ex:
            if ex.code == 404:
                raise base.NotExistingMetadataException()
            else:
                raise

    def _get_oauth_headers(self, url):
        consumer = oauth.OAuthConsumer(CONF.maas_oauth_consumer_key,
                                       CONF.maas_oauth_consumer_secret)
        token = oauth.OAuthToken(CONF.maas_oauth_token_key,
                                 CONF.maas_oauth_token_secret)

        parameters = {'oauth_version': "1.0",
                      'oauth_nonce': oauth.generate_nonce(),
                      'oauth_timestamp': int(time.time()),
                      'oauth_token': token.key,
                      'oauth_consumer_key': consumer.key}

        req = oauth.OAuthRequest(http_url=url, parameters=parameters)
        req.sign_request(oauth.OAuthSignatureMethod_PLAINTEXT(), consumer,
                         token)

        return req.to_header()

    def _get_data(self, path):
        norm_path = posixpath.join(CONF.maas_metadata_url, path)
        oauth_headers = self._get_oauth_headers(norm_path)

        LOG.debug('Getting metadata from: %(norm_path)s',
                  {'norm_path': norm_path})
        req = urllib2.Request(norm_path, headers=oauth_headers)
        response = self._get_response(req)
        return response.read()

    def get_host_name(self):
        return self._get_cache_data('%s/meta-data/local-hostname' %
                                    self._metadata_version)

    def get_instance_id(self):
        return self._get_cache_data('%s/meta-data/instance-id' %
                                    self._metadata_version)

    def _get_list_from_text(self, text, delimiter):
        return [v + delimiter for v in text.split(delimiter)]

    def get_public_keys(self):
        return self._get_list_from_text(
            self._get_cache_data('%s/meta-data/public-keys' %
                                 self._metadata_version), "\n")

    def get_client_auth_certs(self):
        return self._get_list_from_text(
            self._get_cache_data('%s/meta-data/x509' % self._metadata_version),
            "%s\n" % x509constants.PEM_FOOTER)

    def get_user_data(self):
        return self._get_cache_data('%s/user-data' % self._metadata_version)

########NEW FILE########
__FILENAME__ = base
# Copyright 2014 Cloudbase Solutions Srl
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

import abc


class BaseConfigDriveManager(object):
    @abc.abstractmethod
    def get_config_drive_files(self, target_path, check_raw_hhd=True,
                               check_cdrom=True):
        pass

########NEW FILE########
__FILENAME__ = factory
# Copyright 2014 Cloudbase Solutions Srl
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

import sys

from cloudbaseinit.utils import classloader


def get_config_drive_manager():
    class_paths = {
        'win32': 'cloudbaseinit.metadata.services.osconfigdrive.windows.'
        'WindowsConfigDriveManager',
    }

    class_path = class_paths.get(sys.platform)
    if not class_path:
        raise NotImplementedError('ConfigDrive is not supported on '
                                  'this platform: %s' % sys.platform)

    cl = classloader.ClassLoader()
    return cl.load_class(class_path)()

########NEW FILE########
__FILENAME__ = windows
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import ctypes
import os
import shutil
import sys
import tempfile
import uuid

from ctypes import wintypes
from oslo.config import cfg

from cloudbaseinit.metadata.services.osconfigdrive import base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.utils.windows import physical_disk

opts = [
    cfg.StrOpt('bsdtar_path', default='bsdtar.exe',
               help='Path to "bsdtar", used to extract ISO ConfigDrive '
                    'files'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class WindowsConfigDriveManager(base.BaseConfigDriveManager):

    def _get_config_drive_cdrom_mount_point(self):
        osutils = osutils_factory.get_os_utils()

        for drive in osutils.get_cdrom_drives():
            label = osutils.get_volume_label(drive)
            if label == "config-2" and \
                os.path.exists(os.path.join(drive,
                                            'openstack\\latest\\'
                                            'meta_data.json')):
                return drive
        return None

    def _c_char_array_to_c_ushort(self, buf, offset):
        low = ctypes.cast(buf[offset],
                          ctypes.POINTER(wintypes.WORD)).contents
        high = ctypes.cast(buf[offset + 1],
                           ctypes.POINTER(wintypes.WORD)).contents
        return (high.value << 8) + low.value

    def _get_iso_disk_size(self, phys_disk):
        geom = phys_disk.get_geometry()

        if geom.MediaType != physical_disk.Win32_DiskGeometry.FixedMedia:
            return None

        disk_size = geom.Cylinders * geom.TracksPerCylinder * \
            geom.SectorsPerTrack * geom.BytesPerSector

        boot_record_off = 0x8000
        id_off = 1
        volume_size_off = 80
        block_size_off = 128
        iso_id = 'CD001'

        offset = boot_record_off / geom.BytesPerSector * geom.BytesPerSector
        bytes_to_read = geom.BytesPerSector

        if disk_size <= offset + bytes_to_read:
            return None

        phys_disk.seek(offset)
        (buf, bytes_read) = phys_disk.read(bytes_to_read)

        buf_off = boot_record_off - offset + id_off
        if iso_id != buf[buf_off: buf_off + len(iso_id)]:
            return None

        buf_off = boot_record_off - offset + volume_size_off
        num_blocks = self._c_char_array_to_c_ushort(buf, buf_off)

        buf_off = boot_record_off - offset + block_size_off
        block_size = self._c_char_array_to_c_ushort(buf, buf_off)

        return num_blocks * block_size

    def _write_iso_file(self, phys_disk, path, iso_file_size):
        with open(path, 'wb') as f:
            geom = phys_disk.get_geometry()
            offset = 0
            # Get a multiple of the sector byte size
            bytes_to_read = 4096 / geom.BytesPerSector * geom.BytesPerSector

            while offset < iso_file_size:
                phys_disk.seek(offset)
                bytes_to_read = min(bytes_to_read, iso_file_size - offset)
                (buf, bytes_read) = phys_disk.read(bytes_to_read)
                f.write(buf)
                offset += bytes_read

    def _extract_iso_files(self, osutils, iso_file_path, target_path):
        os.makedirs(target_path)

        args = [CONF.bsdtar_path, '-xf', iso_file_path, '-C', target_path]
        (out, err, exit_code) = osutils.execute_process(args, False)

        if exit_code:
            raise Exception('Failed to execute "bsdtar" from path '
                            '"%(bsdtar_path)s" with exit code: %(exit_code)s\n'
                            '%(out)s\n%(err)s' %
                            {'bsdtar_path': CONF.bsdtar_path,
                             'exit_code': exit_code,
                             'out': out, 'err': err})

    def _extract_iso_disk_file(self, osutils, iso_file_path):
        iso_disk_found = False
        for path in osutils.get_physical_disks():
            phys_disk = physical_disk.PhysicalDisk(path)
            try:
                phys_disk.open()
                iso_file_size = self._get_iso_disk_size(phys_disk)
                if iso_file_size:
                    LOG.debug('ISO9660 disk found on raw HDD: %s' % path)
                    self._write_iso_file(phys_disk, iso_file_path,
                                         iso_file_size)
                    iso_disk_found = True
                    break
            except Exception:
                # Ignore exception
                pass
            finally:
                phys_disk.close()
        return iso_disk_found

    def get_config_drive_files(self, target_path, check_raw_hhd=True,
                               check_cdrom=True):
        config_drive_found = False
        if check_raw_hhd:
            LOG.debug('Looking for Config Drive in raw HDDs')
            config_drive_found = self._get_conf_drive_from_raw_hdd(
                target_path)

        if not config_drive_found and check_cdrom:
            LOG.debug('Looking for Config Drive in cdrom drives')
            config_drive_found = self._get_conf_drive_from_cdrom_drive(
                target_path)
        return config_drive_found

    def _get_conf_drive_from_cdrom_drive(self, target_path):
        cdrom_mount_point = self._get_config_drive_cdrom_mount_point()
        if cdrom_mount_point:
            shutil.copytree(cdrom_mount_point, target_path)
            return True
        return False

    def _get_conf_drive_from_raw_hdd(self, target_path):
        config_drive_found = False
        iso_file_path = os.path.join(tempfile.gettempdir(),
                                     str(uuid.uuid4()) + '.iso')
        try:
            osutils = osutils_factory.get_os_utils()

            if self._extract_iso_disk_file(osutils, iso_file_path):
                self._extract_iso_files(osutils, iso_file_path, target_path)
                config_drive_found = True
        finally:
            if os.path.exists(iso_file_path):
                os.remove(iso_file_path)
        return config_drive_found

########NEW FILE########
__FILENAME__ = context
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

"""
Simple class that stores security context information in the web request.

Projects should subclass this class if they wish to enhance the request
context or provide additional information in their specific WSGI pipeline.
"""

import itertools
import uuid


def generate_request_id():
    return 'req-%s' % str(uuid.uuid4())


class RequestContext(object):

    """Helper class to represent useful information about a request context.

    Stores information about the security context under which the user
    accesses the system, as well as additional request information.
    """

    user_idt_format = '{user} {tenant} {domain} {user_domain} {p_domain}'

    def __init__(self, auth_token=None, user=None, tenant=None, domain=None,
                 user_domain=None, project_domain=None, is_admin=False,
                 read_only=False, show_deleted=False, request_id=None,
                 instance_uuid=None):
        self.auth_token = auth_token
        self.user = user
        self.tenant = tenant
        self.domain = domain
        self.user_domain = user_domain
        self.project_domain = project_domain
        self.is_admin = is_admin
        self.read_only = read_only
        self.show_deleted = show_deleted
        self.instance_uuid = instance_uuid
        if not request_id:
            request_id = generate_request_id()
        self.request_id = request_id

    def to_dict(self):
        user_idt = (
            self.user_idt_format.format(user=self.user or '-',
                                        tenant=self.tenant or '-',
                                        domain=self.domain or '-',
                                        user_domain=self.user_domain or '-',
                                        p_domain=self.project_domain or '-'))

        return {'user': self.user,
                'tenant': self.tenant,
                'domain': self.domain,
                'user_domain': self.user_domain,
                'project_domain': self.project_domain,
                'is_admin': self.is_admin,
                'read_only': self.read_only,
                'show_deleted': self.show_deleted,
                'auth_token': self.auth_token,
                'request_id': self.request_id,
                'instance_uuid': self.instance_uuid,
                'user_identity': user_idt}


def get_admin_context(show_deleted=False):
    context = RequestContext(None,
                             tenant=None,
                             is_admin=True,
                             show_deleted=show_deleted)
    return context


def get_context_from_function_and_args(function, args, kwargs):
    """Find an arg of type RequestContext and return it.

       This is useful in a couple of decorators where we don't
       know much about the function we're wrapping.
    """

    for arg in itertools.chain(kwargs.values(), args):
        if isinstance(arg, RequestContext):
            return arg

    return None

########NEW FILE########
__FILENAME__ = eventlet_backdoor
# Copyright (c) 2012 OpenStack Foundation.
# Administrator of the National Aeronautics and Space Administration.
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

from __future__ import print_function

import errno
import gc
import os
import pprint
import socket
import sys
import traceback

import eventlet
import eventlet.backdoor
import greenlet
from oslo.config import cfg

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging

help_for_backdoor_port = (
    "Acceptable values are 0, <port>, and <start>:<end>, where 0 results "
    "in listening on a random tcp port number; <port> results in listening "
    "on the specified port number (and not enabling backdoor if that port "
    "is in use); and <start>:<end> results in listening on the smallest "
    "unused port number within the specified range of port numbers.  The "
    "chosen port is displayed in the service's log file.")
eventlet_backdoor_opts = [
    cfg.StrOpt('backdoor_port',
               default=None,
               help="Enable eventlet backdoor.  %s" % help_for_backdoor_port)
]

CONF = cfg.CONF
CONF.register_opts(eventlet_backdoor_opts)
LOG = logging.getLogger(__name__)


class EventletBackdoorConfigValueError(Exception):
    def __init__(self, port_range, help_msg, ex):
        msg = ('Invalid backdoor_port configuration %(range)s: %(ex)s. '
               '%(help)s' %
               {'range': port_range, 'ex': ex, 'help': help_msg})
        super(EventletBackdoorConfigValueError, self).__init__(msg)
        self.port_range = port_range


def _dont_use_this():
    print("Don't use this, just disconnect instead")


def _find_objects(t):
    return [o for o in gc.get_objects() if isinstance(o, t)]


def _print_greenthreads():
    for i, gt in enumerate(_find_objects(greenlet.greenlet)):
        print(i, gt)
        traceback.print_stack(gt.gr_frame)
        print()


def _print_nativethreads():
    for threadId, stack in sys._current_frames().items():
        print(threadId)
        traceback.print_stack(stack)
        print()


def _parse_port_range(port_range):
    if ':' not in port_range:
        start, end = port_range, port_range
    else:
        start, end = port_range.split(':', 1)
    try:
        start, end = int(start), int(end)
        if end < start:
            raise ValueError
        return start, end
    except ValueError as ex:
        raise EventletBackdoorConfigValueError(port_range, ex,
                                               help_for_backdoor_port)


def _listen(host, start_port, end_port, listen_func):
    try_port = start_port
    while True:
        try:
            return listen_func((host, try_port))
        except socket.error as exc:
            if (exc.errno != errno.EADDRINUSE or
               try_port >= end_port):
                raise
            try_port += 1


def initialize_if_enabled():
    backdoor_locals = {
        'exit': _dont_use_this,      # So we don't exit the entire process
        'quit': _dont_use_this,      # So we don't exit the entire process
        'fo': _find_objects,
        'pgt': _print_greenthreads,
        'pnt': _print_nativethreads,
    }

    if CONF.backdoor_port is None:
        return None

    start_port, end_port = _parse_port_range(str(CONF.backdoor_port))

    # NOTE(johannes): The standard sys.displayhook will print the value of
    # the last expression and set it to __builtin__._, which overwrites
    # the __builtin__._ that gettext sets. Let's switch to using pprint
    # since it won't interact poorly with gettext, and it's easier to
    # read the output too.
    def displayhook(val):
        if val is not None:
            pprint.pprint(val)
    sys.displayhook = displayhook

    sock = _listen('localhost', start_port, end_port, eventlet.listen)

    # In the case of backdoor port being zero, a port number is assigned by
    # listen().  In any case, pull the port number out here.
    port = sock.getsockname()[1]
    LOG.info(_('Eventlet backdoor listening on %(port)s for process %(pid)d') %
             {'port': port, 'pid': os.getpid()})
    eventlet.spawn_n(eventlet.backdoor.backdoor_server, sock,
                     locals=backdoor_locals)
    return port

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

from cloudbaseinit.openstack.common.gettextutils import _


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
    can be used to suppress the exception.  For example::

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

    from cloudbaseinit.openstack.common.gettextutils import _
"""

import copy
import gettext
import locale
from logging import handlers
import os
import re

from babel import localedata
import six

_localedir = os.environ.get('cloudbaseinit'.upper() + '_LOCALEDIR')
_t = gettext.translation('cloudbaseinit', localedir=_localedir, fallback=True)

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
        return Message(msg, domain='cloudbaseinit')
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
        def _lazy_gettext(msg):
            """Create and return a Message object.

            Lazy gettext function for a given domain, it is a factory method
            for a project/module to get a lazy gettext function for its own
            translation domain (i.e. nova, glance, cinder, etc.)

            Message encapsulates a string so that we can translate
            it later when needed.
            """
            return Message(msg, domain=domain)

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


class Message(six.text_type):
    """A Message object is a unicode object that can be translated.

    Translation of Message is done explicitly using the translate() method.
    For all non-translation intents and purposes, a Message is simply unicode,
    and can be treated as such.
    """

    def __new__(cls, msgid, msgtext=None, params=None,
                domain='cloudbaseinit', *args):
        """Create a new Message object.

        In order for translation to work gettext requires a message ID, this
        msgid will be used as the base unicode text. It is also possible
        for the msgid and the base unicode text to be different by passing
        the msgtext parameter.
        """
        # If the base msgtext is not given, we use the default translation
        # of the msgid (which is in English) just in case the system locale is
        # not English, so that the base text will be in that locale by default.
        if not msgtext:
            msgtext = Message._translate_msgid(msgid, domain)
        # We want to initialize the parent unicode with the actual object that
        # would have been plain unicode if 'Message' was not enabled.
        msg = super(Message, cls).__new__(cls, msgtext)
        msg.msgid = msgid
        msg.domain = domain
        msg.params = params
        return msg

    def translate(self, desired_locale=None):
        """Translate this message to the desired locale.

        :param desired_locale: The desired locale to translate the message to,
                               if no locale is provided the message will be
                               translated to the system's default locale.

        :returns: the translated message in unicode
        """

        translated_message = Message._translate_msgid(self.msgid,
                                                      self.domain,
                                                      desired_locale)
        if self.params is None:
            # No need for more translation
            return translated_message

        # This Message object may have been formatted with one or more
        # Message objects as substitution arguments, given either as a single
        # argument, part of a tuple, or as one or more values in a dictionary.
        # When translating this Message we need to translate those Messages too
        translated_params = _translate_args(self.params, desired_locale)

        translated_message = translated_message % translated_params

        return translated_message

    @staticmethod
    def _translate_msgid(msgid, domain, desired_locale=None):
        if not desired_locale:
            system_locale = locale.getdefaultlocale()
            # If the system locale is not available to the runtime use English
            if not system_locale[0]:
                desired_locale = 'en_US'
            else:
                desired_locale = system_locale[0]

        locale_dir = os.environ.get(domain.upper() + '_LOCALEDIR')
        lang = gettext.translation(domain,
                                   localedir=locale_dir,
                                   languages=[desired_locale],
                                   fallback=True)
        if six.PY3:
            translator = lang.gettext
        else:
            translator = lang.ugettext

        translated_message = translator(msgid)
        return translated_message

    def __mod__(self, other):
        # When we mod a Message we want the actual operation to be performed
        # by the parent class (i.e. unicode()), the only thing  we do here is
        # save the original msgid and the parameters in case of a translation
        params = self._sanitize_mod_params(other)
        unicode_mod = super(Message, self).__mod__(params)
        modded = Message(self.msgid,
                         msgtext=unicode_mod,
                         params=params,
                         domain=self.domain)
        return modded

    def _sanitize_mod_params(self, other):
        """Sanitize the object being modded with this Message.

        - Add support for modding 'None' so translation supports it
        - Trim the modded object, which can be a large dictionary, to only
        those keys that would actually be used in a translation
        - Snapshot the object being modded, in case the message is
        translated, it will be used as it was when the Message was created
        """
        if other is None:
            params = (other,)
        elif isinstance(other, dict):
            params = self._trim_dictionary_parameters(other)
        else:
            params = self._copy_param(other)
        return params

    def _trim_dictionary_parameters(self, dict_param):
        """Return a dict that only has matching entries in the msgid."""
        # NOTE(luisg): Here we trim down the dictionary passed as parameters
        # to avoid carrying a lot of unnecessary weight around in the message
        # object, for example if someone passes in Message() % locals() but
        # only some params are used, and additionally we prevent errors for
        # non-deepcopyable objects by unicoding() them.

        # Look for %(param) keys in msgid;
        # Skip %% and deal with the case where % is first character on the line
        keys = re.findall('(?:[^%]|^)?%\((\w*)\)[a-z]', self.msgid)

        # If we don't find any %(param) keys but have a %s
        if not keys and re.findall('(?:[^%]|^)%[a-z]', self.msgid):
            # Apparently the full dictionary is the parameter
            params = self._copy_param(dict_param)
        else:
            params = {}
            # Save our existing parameters as defaults to protect
            # ourselves from losing values if we are called through an
            # (erroneous) chain that builds a valid Message with
            # arguments, and then does something like "msg % kwds"
            # where kwds is an empty dictionary.
            src = {}
            if isinstance(self.params, dict):
                src.update(self.params)
            src.update(dict_param)
            for key in keys:
                params[key] = self._copy_param(src[key])

        return params

    def _copy_param(self, param):
        try:
            return copy.deepcopy(param)
        except TypeError:
            # Fallback to casting to unicode this will handle the
            # python code-like objects that can't be deep-copied
            return six.text_type(param)

    def __add__(self, other):
        msg = _('Message objects do not support addition.')
        raise TypeError(msg)

    def __radd__(self, other):
        return self.__add__(other)

    def __str__(self):
        # NOTE(luisg): Logging in python 2.6 tries to str() log records,
        # and it expects specifically a UnicodeError in order to proceed.
        msg = _('Message objects do not support str() because they may '
                'contain non-ascii characters. '
                'Please use unicode() or translate() instead.')
        raise UnicodeError(msg)


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
    # this check when the master list updates to >=1.0, and update all projects
    list_identifiers = (getattr(localedata, 'list', None) or
                        getattr(localedata, 'locale_identifiers'))
    locale_identifiers = list_identifiers()

    for i in locale_identifiers:
        if find(i) is not None:
            language_list.append(i)

    # NOTE(luisg): Babel>=1.0,<1.3 has a bug where some OpenStack supported
    # locales (e.g. 'zh_CN', and 'zh_TW') aren't supported even though they
    # are perfectly legitimate locales:
    #     https://github.com/mitsuhiko/babel/issues/37
    # In Babel 1.3 they fixed the bug and they support these locales, but
    # they are still not explicitly "listed" by locale_identifiers().
    # That is  why we add the locales here explicitly if necessary so that
    # they are listed as supported.
    aliases = {'zh': 'zh_CN',
               'zh_Hant_HK': 'zh_HK',
               'zh_Hant': 'zh_TW',
               'fil': 'tl_PH'}
    for (locale, alias) in six.iteritems(aliases):
        if locale in language_list and alias not in language_list:
            language_list.append(alias)

    _AVAILABLE_LANGUAGES[domain] = language_list
    return copy.copy(language_list)


def translate(obj, desired_locale=None):
    """Gets the translated unicode representation of the given object.

    If the object is not translatable it is returned as-is.
    If the locale is None the object is translated to the system locale.

    :param obj: the object to translate
    :param desired_locale: the locale to translate the message to, if None the
                           default system locale will be used
    :returns: the translated object in unicode, or the original object if
              it could not be translated
    """
    message = obj
    if not isinstance(message, Message):
        # If the object to translate is not already translatable,
        # let's first get its unicode representation
        message = six.text_type(obj)
    if isinstance(message, Message):
        # Even after unicoding() we still need to check if we are
        # running with translatable unicode before translating
        return message.translate(desired_locale)
    return obj


def _translate_args(args, desired_locale=None):
    """Translates all the translatable elements of the given arguments object.

    This method is used for translating the translatable values in method
    arguments which include values of tuples or dictionaries.
    If the object is not a tuple or a dictionary the object itself is
    translated if it is translatable.

    If the locale is None the object is translated to the system locale.

    :param args: the args to translate
    :param desired_locale: the locale to translate the args to, if None the
                           default system locale will be used
    :returns: a new args object with the translated contents of the original
    """
    if isinstance(args, tuple):
        return tuple(translate(v, desired_locale) for v in args)
    if isinstance(args, dict):
        translated_dict = {}
        for (k, v) in six.iteritems(args):
            translated_v = translate(v, desired_locale)
            translated_dict[k] = translated_v
        return translated_dict
    return translate(args, desired_locale)


class TranslationHandler(handlers.MemoryHandler):
    """Handler that translates records before logging them.

    The TranslationHandler takes a locale and a target logging.Handler object
    to forward LogRecord objects to after translating them. This handler
    depends on Message objects being logged, instead of regular strings.

    The handler can be configured declaratively in the logging.conf as follows:

        [handlers]
        keys = translatedlog, translator

        [handler_translatedlog]
        class = handlers.WatchedFileHandler
        args = ('/var/log/api-localized.log',)
        formatter = context

        [handler_translator]
        class = openstack.common.log.TranslationHandler
        target = translatedlog
        args = ('zh_CN',)

    If the specified locale is not available in the system, the handler will
    log in the default locale.
    """

    def __init__(self, locale=None, target=None):
        """Initialize a TranslationHandler

        :param locale: locale to use for translating messages
        :param target: logging.Handler object to forward
                       LogRecord objects to after translation
        """
        # NOTE(luisg): In order to allow this handler to be a wrapper for
        # other handlers, such as a FileHandler, and still be able to
        # configure it using logging.conf, this handler has to extend
        # MemoryHandler because only the MemoryHandlers' logging.conf
        # parsing is implemented such that it accepts a target handler.
        handlers.MemoryHandler.__init__(self, capacity=0, target=target)
        self.locale = locale

    def setFormatter(self, fmt):
        self.target.setFormatter(fmt)

    def emit(self, record):
        # We save the message from the original record to restore it
        # after translation, so other handlers are not affected by this
        original_msg = record.msg
        original_args = record.args

        try:
            self._translate_and_log_record(record)
        finally:
            record.msg = original_msg
            record.args = original_args

    def _translate_and_log_record(self, record):
        record.msg = translate(record.msg, self.locale)

        # In addition to translating the message, we also need to translate
        # arguments that were passed to the log method that were not part
        # of the main message e.g., log.info(_('Some message %s'), this_one))
        record.args = _translate_args(record.args, self.locale)

        self.target.emit(record)

########NEW FILE########
__FILENAME__ = importutils
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

'''
JSON related utilities.

This module provides a few things:

    1) A handy function for getting an object down to something that can be
    JSON serialized.  See to_primitive().

    2) Wrappers around loads() and dumps().  The dumps() wrapper will
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
    # NOTE(jaypipes): xmlrpclib was renamed to xmlrpc.client in Python3
    #                 however the function and object call signatures
    #                 remained the same. This whole try/except block should
    #                 be removed and replaced with a call to six.moves once
    #                 six 1.4.2 is released. See http://bit.ly/1bqrVzu
    import xmlrpc.client as xmlrpclib

import six

from cloudbaseinit.openstack.common import gettextutils
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import timeutils

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
    #  51817 <type 'bool'>
    #  26164 <type 'list'>
    #   6491 <type 'float'>
    #    283 <type 'tuple'>
    #     19 <type 'long'>
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
    #              tests that raise an exception in a mocked method that
    #              has a @wrap_exception with a notifier will fail. If
    #              we up the dependency to 0.5.4 (when it is released) we
    #              can remove this workaround.
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
            return dict((k, recursive(v)) for k, v in six.iteritems(value))
        elif isinstance(value, (list, tuple)):
            return [recursive(lv) for lv in value]

        # It's not clear why xmlrpclib created their own DateTime type, but
        # for our purposes, make it a datetime type which is explicitly
        # handled
        if isinstance(value, xmlrpclib.DateTime):
            value = datetime.datetime(*tuple(value.timetuple())[:6])

        if convert_datetime and isinstance(value, datetime.datetime):
            return timeutils.strtime(value)
        elif isinstance(value, gettextutils.Message):
            return value.data
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
__FILENAME__ = log
# Copyright 2011 OpenStack Foundation.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Openstack logging handler.

This module adds to logging functionality by adding the option to specify
a context object when calling the various log methods.  If the context object
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
import re
import sys
import traceback

from oslo.config import cfg
import six
from six import moves

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import jsonutils
from cloudbaseinit.openstack.common import local


_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_SANITIZE_KEYS = ['adminPass', 'admin_pass', 'password', 'admin_password']

# NOTE(ldbragst): Let's build a list of regex objects using the list of
# _SANITIZE_KEYS we already have. This way, we only have to add the new key
# to the list of _SANITIZE_KEYS and we can generate regular expressions
# for XML and JSON automatically.
_SANITIZE_PATTERNS = []
_FORMAT_PATTERNS = [r'(%(key)s\s*[=]\s*[\"\']).*?([\"\'])',
                    r'(<%(key)s>).*?(</%(key)s>)',
                    r'([\"\']%(key)s[\"\']\s*:\s*[\"\']).*?([\"\'])',
                    r'([\'"].*?%(key)s[\'"]\s*:\s*u?[\'"]).*?([\'"])']

for key in _SANITIZE_KEYS:
    for pattern in _FORMAT_PATTERNS:
        reg_ex = re.compile(pattern % {'key': key}, re.DOTALL)
        _SANITIZE_PATTERNS.append(reg_ex)


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
    cfg.StrOpt('log-config-append',
               metavar='PATH',
               deprecated_name='log-config',
               help='The name of logging configuration file. It does not '
                    'disable existing loggers, but just appends specified '
                    'logging configuration to any other existing logging '
                    'options. Please see the Python logging module '
                    'documentation for details on logging configuration '
                    'files.'),
    cfg.StrOpt('log-format',
               default=None,
               metavar='FORMAT',
               help='DEPRECATED. '
                    'A logging.Formatter log message format string which may '
                    'use any of the available logging.LogRecord attributes. '
                    'This option is deprecated.  Please use '
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
                help='Use syslog for logging. '
                     'Existing syslog format is DEPRECATED during I, '
                     'and then will be changed in J to honor RFC5424'),
    cfg.BoolOpt('use-syslog-rfc-format',
                # TODO(bogdando) remove or use True after existing
                #    syslog format deprecation in J
                default=False,
                help='(Optional) Use syslog rfc5424 format for logging. '
                     'If enabled, will add APP-NAME (RFC5424) before the '
                     'MSG part of the syslog message.  The old format '
                     'without APP-NAME is deprecated in I, '
                     'and will be removed in J.'),
    cfg.StrOpt('syslog-log-facility',
               default='LOG_USER',
               help='Syslog facility to receive log lines')
]

generic_log_opts = [
    cfg.BoolOpt('use_stderr',
                default=True,
                help='Log output to standard error')
]

log_opts = [
    cfg.StrOpt('logging_context_format_string',
               default='%(asctime)s.%(msecs)03d %(process)d %(levelname)s '
                       '%(name)s [%(request_id)s %(user_identity)s] '
                       '%(instance)s%(message)s',
               help='Format string to use for log messages with context'),
    cfg.StrOpt('logging_default_format_string',
               default='%(asctime)s.%(msecs)03d %(process)d %(levelname)s '
                       '%(name)s [-] %(instance)s%(message)s',
               help='Format string to use for log messages without context'),
    cfg.StrOpt('logging_debug_format_suffix',
               default='%(funcName)s %(pathname)s:%(lineno)d',
               help='Data to append to log format when level is DEBUG'),
    cfg.StrOpt('logging_exception_prefix',
               default='%(asctime)s.%(msecs)03d %(process)d TRACE %(name)s '
               '%(instance)s',
               help='Prefix each line of exception output with this format'),
    cfg.ListOpt('default_log_levels',
                default=[
                    'amqp=WARN',
                    'amqplib=WARN',
                    'boto=WARN',
                    'qpid=WARN',
                    'sqlalchemy=WARN',
                    'suds=INFO',
                    'iso8601=WARN',
                    'requests.packages.urllib3.connectionpool=WARN'
                ],
                help='List of logger=LEVEL pairs'),
    cfg.BoolOpt('publish_errors',
                default=False,
                help='Publish error events'),
    cfg.BoolOpt('fatal_deprecations',
                default=False,
                help='Make deprecations fatal'),

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
#                module aware of it so it acts like other levels.
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

    return None


def mask_password(message, secret="***"):
    """Replace password with 'secret' in message.

    :param message: The string which includes security information.
    :param secret: value with which to replace passwords.
    :returns: The unicode value of message with the password fields masked.

    For example:

    >>> mask_password("'adminPass' : 'aaaaa'")
    "'adminPass' : '***'"
    >>> mask_password("'admin_pass' : 'aaaaa'")
    "'admin_pass' : '***'"
    >>> mask_password('"password" : "aaaaa"')
    '"password" : "***"'
    >>> mask_password("'original_password' : 'aaaaa'")
    "'original_password' : '***'"
    >>> mask_password("u'original_password' :   u'aaaaa'")
    "u'original_password' :   u'***'"
    """
    message = six.text_type(message)

    # NOTE(ldbragst): Check to see if anything in message contains any key
    # specified in _SANITIZE_KEYS, if not then just return the message since
    # we don't have to mask any passwords.
    if not any(key in message for key in _SANITIZE_KEYS):
        return message

    secret = r'\g<1>' + secret + r'\g<2>'
    for pattern in _SANITIZE_PATTERNS:
        message = re.sub(pattern, secret, message)
    return message


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
        # NOTE(mrodden): catch any Message/other object and
        #                coerce to unicode before they can get
        #                to the python logging and possibly
        #                cause string encoding trouble
        if not isinstance(msg, six.string_types):
            msg = six.text_type(msg)

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
        extra['instance'] = instance_extra

        extra.setdefault('user_identity', kwargs.pop('user_identity', None))

        extra['project'] = self.project
        extra['version'] = self.version
        extra['extra'] = extra.copy()
        return msg, kwargs


class JSONFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        # NOTE(jkoelker) we ignore the fmt argument, but its still there
        #                since logging.config.fileConfig passes it.
        self.datefmt = datefmt

    def formatException(self, ei, strip_newlines=True):
        lines = traceback.format_exception(*ei)
        if strip_newlines:
            lines = [moves.filter(
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
    def logging_excepthook(exc_type, value, tb):
        extra = {}
        if CONF.verbose or CONF.debug:
            extra['exc_info'] = (exc_type, value, tb)
        getLogger(product_name).critical(
            "".join(traceback.format_exception_only(exc_type, value)),
            **extra)
    return logging_excepthook


class LogConfigError(Exception):

    message = _('Error loading logging config %(log_config)s: %(err_msg)s')

    def __init__(self, log_config, err_msg):
        self.log_config = log_config
        self.err_msg = err_msg

    def __str__(self):
        return self.message % dict(log_config=self.log_config,
                                   err_msg=self.err_msg)


def _load_log_config(log_config_append):
    try:
        logging.config.fileConfig(log_config_append,
                                  disable_existing_loggers=False)
    except moves.configparser.Error as exc:
        raise LogConfigError(log_config_append, str(exc))


def setup(product_name, version='unknown'):
    """Setup logging."""
    if CONF.log_config_append:
        _load_log_config(CONF.log_config_append)
    else:
        _setup_logging_from_conf(product_name, version)
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


class RFCSysLogHandler(logging.handlers.SysLogHandler):
    def __init__(self, *args, **kwargs):
        self.binary_name = _get_binary_name()
        super(RFCSysLogHandler, self).__init__(*args, **kwargs)

    def format(self, record):
        msg = super(RFCSysLogHandler, self).format(record)
        msg = self.binary_name + ' ' + msg
        return msg


def _setup_logging_from_conf(project, version):
    log_root = getLogger(None).logger
    for handler in log_root.handlers:
        log_root.removeHandler(handler)

    if CONF.use_syslog:
        facility = _find_facility_from_conf()
        # TODO(bogdando) use the format provided by RFCSysLogHandler
        #   after existing syslog format deprecation in J
        if CONF.use_syslog_rfc_format:
            syslog = RFCSysLogHandler(address='/dev/log',
                                      facility=facility)
        else:
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

    elif not logpath:
        # pass sys.stdout as a positional argument
        # python2.6 calls the argument strm, in 2.7 it's stream
        streamlog = logging.StreamHandler(sys.stdout)
        log_root.addHandler(streamlog)

    if CONF.publish_errors:
        handler = importutils.import_object(
            "cloudbaseinit.openstack.common.log_handler.PublishErrorsHandler",
            logging.ERROR)
        log_root.addHandler(handler)

    datefmt = CONF.log_date_format
    for handler in log_root.handlers:
        # NOTE(alaski): CONF.log_format overrides everything currently.  This
        # should be deprecated in favor of context aware formatting.
        if CONF.log_format:
            handler.setFormatter(logging.Formatter(fmt=CONF.log_format,
                                                   datefmt=datefmt))
            log_root.info('Deprecated: log_format is now deprecated and will '
                          'be removed in the next release')
        else:
            handler.setFormatter(ContextFormatter(project=project,
                                                  version=version,
                                                  datefmt=datefmt))

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
        self.logger.log(self.level, msg.rstrip())


class ContextFormatter(logging.Formatter):
    """A context.RequestContext aware formatter configured through flags.

    The flags used to set format strings are: logging_context_format_string
    and logging_default_format_string.  You can also specify
    logging_debug_format_suffix to append extra formatting if the log level is
    debug.

    For information about what variables are available for the formatter see:
    http://docs.python.org/library/logging.html#formatter

    If available, uses the context value stored in TLS - local.store.context

    """

    def __init__(self, *args, **kwargs):
        """Initialize ContextFormatter instance

        Takes additional keyword arguments which can be used in the message
        format string.

        :keyword project: project name
        :type project: string
        :keyword version: project version
        :type version: string

        """

        self.project = kwargs.pop('project', 'unknown')
        self.version = kwargs.pop('version', 'unknown')

        logging.Formatter.__init__(self, *args, **kwargs)

    def format(self, record):
        """Uses contextstring if request_id is set, otherwise default."""

        # store project info
        record.project = self.project
        record.version = self.version

        # store request info
        context = getattr(local.store, 'context', None)
        if context:
            d = _dictify_context(context)
            for k, v in d.items():
                setattr(record, k, v)

        # NOTE(sdague): default the fancier formatting params
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

        # Cache this on the record, Logger will respect our formatted copy
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
__FILENAME__ = loopingcall
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
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

import sys

from eventlet import event
from eventlet import greenthread

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import timeutils

LOG = logging.getLogger(__name__)


class LoopingCallDone(Exception):
    """Exception to break out and stop a LoopingCall.

    The poll-function passed to LoopingCall can raise this exception to
    break out of the loop normally. This is somewhat analogous to
    StopIteration.

    An optional return-value can be included as the argument to the exception;
    this return-value will be returned by LoopingCall.wait()

    """

    def __init__(self, retvalue=True):
        """:param retvalue: Value that LoopingCall.wait() should return."""
        self.retvalue = retvalue


class LoopingCallBase(object):
    def __init__(self, f=None, *args, **kw):
        self.args = args
        self.kw = kw
        self.f = f
        self._running = False
        self.done = None

    def stop(self):
        self._running = False

    def wait(self):
        return self.done.wait()


class FixedIntervalLoopingCall(LoopingCallBase):
    """A fixed interval looping call."""

    def start(self, interval, initial_delay=None):
        self._running = True
        done = event.Event()

        def _inner():
            if initial_delay:
                greenthread.sleep(initial_delay)

            try:
                while self._running:
                    start = timeutils.utcnow()
                    self.f(*self.args, **self.kw)
                    end = timeutils.utcnow()
                    if not self._running:
                        break
                    delay = interval - timeutils.delta_seconds(start, end)
                    if delay <= 0:
                        LOG.warn(_('task run outlasted interval by %s sec') %
                                 -delay)
                    greenthread.sleep(delay if delay > 0 else 0)
            except LoopingCallDone as e:
                self.stop()
                done.send(e.retvalue)
            except Exception:
                LOG.exception(_('in fixed duration looping call'))
                done.send_exception(*sys.exc_info())
                return
            else:
                done.send(True)

        self.done = done

        greenthread.spawn_n(_inner)
        return self.done


# TODO(mikal): this class name is deprecated in Havana and should be removed
# in the I release
LoopingCall = FixedIntervalLoopingCall


class DynamicLoopingCall(LoopingCallBase):
    """A looping call which sleeps until the next known event.

    The function called should return how long to sleep for before being
    called again.
    """

    def start(self, initial_delay=None, periodic_interval_max=None):
        self._running = True
        done = event.Event()

        def _inner():
            if initial_delay:
                greenthread.sleep(initial_delay)

            try:
                while self._running:
                    idle = self.f(*self.args, **self.kw)
                    if not self._running:
                        break

                    if periodic_interval_max is not None:
                        idle = min(idle, periodic_interval_max)
                    LOG.debug(_('Dynamic looping call sleeping for %.02f '
                                'seconds'), idle)
                    greenthread.sleep(idle)
            except LoopingCallDone as e:
                self.stop()
                done.send(e.retvalue)
            except Exception:
                LOG.exception(_('in dynamic looping call'))
                done.send_exception(*sys.exc_info())
                return
            else:
                done.send(True)

        self.done = done

        greenthread.spawn(_inner)
        return self.done

########NEW FILE########
__FILENAME__ = network_utils
# Copyright 2012 OpenStack Foundation.
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
Network-related utilities and helper functions.
"""

from cloudbaseinit.openstack.common.py3kcompat import urlutils


def parse_host_port(address, default_port=None):
    """Interpret a string as a host:port pair.

    An IPv6 address MUST be escaped if accompanied by a port,
    because otherwise ambiguity ensues: 2001:db8:85a3::8a2e:370:7334
    means both [2001:db8:85a3::8a2e:370:7334] and
    [2001:db8:85a3::8a2e:370]:7334.

    >>> parse_host_port('server01:80')
    ('server01', 80)
    >>> parse_host_port('server01')
    ('server01', None)
    >>> parse_host_port('server01', default_port=1234)
    ('server01', 1234)
    >>> parse_host_port('[::1]:80')
    ('::1', 80)
    >>> parse_host_port('[::1]')
    ('::1', None)
    >>> parse_host_port('[::1]', default_port=1234)
    ('::1', 1234)
    >>> parse_host_port('2001:db8:85a3::8a2e:370:7334', default_port=1234)
    ('2001:db8:85a3::8a2e:370:7334', 1234)

    """
    if address[0] == '[':
        # Escaped ipv6
        _host, _port = address[1:].split(']')
        host = _host
        if ':' in _port:
            port = _port.split(':')[1]
        else:
            port = default_port
    else:
        if address.count(':') == 1:
            host, port = address.split(':')
        else:
            # 0 means ipv4, >1 means ipv6.
            # We prohibit unescaped ipv6 addresses with port.
            host = address
            port = default_port

    return (host, None if port is None else int(port))


def urlsplit(url, scheme='', allow_fragments=True):
    """Parse a URL using urlparse.urlsplit(), splitting query and fragments.
    This function papers over Python issue9374 when needed.

    The parameters are the same as urlparse.urlsplit.
    """
    scheme, netloc, path, query, fragment = urlutils.urlsplit(
        url, scheme, allow_fragments)
    if allow_fragments and '#' in path:
        path, fragment = path.split('#', 1)
    if '?' in path:
        path, query = path.split('?', 1)
    return urlutils.SplitResult(scheme, netloc, path, query, fragment)

########NEW FILE########
__FILENAME__ = api
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

import socket
import uuid

from oslo.config import cfg

from cloudbaseinit.openstack.common import context
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import jsonutils
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import timeutils


LOG = logging.getLogger(__name__)

notifier_opts = [
    cfg.MultiStrOpt('notification_driver',
                    default=[],
                    help='Driver or drivers to handle sending notifications'),
    cfg.StrOpt('default_notification_level',
               default='INFO',
               help='Default notification level for outgoing notifications'),
    cfg.StrOpt('default_publisher_id',
               default=None,
               help='Default publisher_id for outgoing notifications'),
]

CONF = cfg.CONF
CONF.register_opts(notifier_opts)

WARN = 'WARN'
INFO = 'INFO'
ERROR = 'ERROR'
CRITICAL = 'CRITICAL'
DEBUG = 'DEBUG'

log_levels = (DEBUG, WARN, INFO, ERROR, CRITICAL)


class BadPriorityException(Exception):
    pass


def notify_decorator(name, fn):
    """Decorator for notify which is used from utils.monkey_patch().

        :param name: name of the function
        :param function: - object of the function
        :returns: function -- decorated function

    """
    def wrapped_func(*args, **kwarg):
        body = {}
        body['args'] = []
        body['kwarg'] = {}
        for arg in args:
            body['args'].append(arg)
        for key in kwarg:
            body['kwarg'][key] = kwarg[key]

        ctxt = context.get_context_from_function_and_args(fn, args, kwarg)
        notify(ctxt,
               CONF.default_publisher_id or socket.gethostname(),
               name,
               CONF.default_notification_level,
               body)
        return fn(*args, **kwarg)
    return wrapped_func


def publisher_id(service, host=None):
    if not host:
        try:
            host = CONF.host
        except AttributeError:
            host = CONF.default_publisher_id or socket.gethostname()
    return "%s.%s" % (service, host)


def notify(context, publisher_id, event_type, priority, payload):
    """Sends a notification using the specified driver

    :param publisher_id: the source worker_type.host of the message
    :param event_type:   the literal type of event (ex. Instance Creation)
    :param priority:     patterned after the enumeration of Python logging
                         levels in the set (DEBUG, WARN, INFO, ERROR, CRITICAL)
    :param payload:       A python dictionary of attributes

    Outgoing message format includes the above parameters, and appends the
    following:

    message_id
      a UUID representing the id for this notification

    timestamp
      the GMT timestamp the notification was sent at

    The composite message will be constructed as a dictionary of the above
    attributes, which will then be sent via the transport mechanism defined
    by the driver.

    Message example::

        {'message_id': str(uuid.uuid4()),
         'publisher_id': 'compute.host1',
         'timestamp': timeutils.utcnow(),
         'priority': 'WARN',
         'event_type': 'compute.create_instance',
         'payload': {'instance_id': 12, ... }}

    """
    if priority not in log_levels:
        raise BadPriorityException(
            _('%s not in valid priorities') % priority)

    # Ensure everything is JSON serializable.
    payload = jsonutils.to_primitive(payload, convert_instances=True)

    msg = dict(message_id=str(uuid.uuid4()),
               publisher_id=publisher_id,
               event_type=event_type,
               priority=priority,
               payload=payload,
               timestamp=str(timeutils.utcnow()))

    for driver in _get_drivers():
        try:
            driver.notify(context, msg)
        except Exception as e:
            LOG.exception(_("Problem '%(e)s' attempting to "
                            "send to notification system. "
                            "Payload=%(payload)s")
                          % dict(e=e, payload=payload))


_drivers = None


def _get_drivers():
    """Instantiate, cache, and return drivers based on the CONF."""
    global _drivers
    if _drivers is None:
        _drivers = {}
        for notification_driver in CONF.notification_driver:
            try:
                driver = importutils.import_module(notification_driver)
                _drivers[notification_driver] = driver
            except ImportError:
                LOG.exception(_("Failed to load notifier %s. "
                                "These notifications will not be sent.") %
                              notification_driver)
    return _drivers.values()


def _reset_drivers():
    """Used by unit tests to reset the drivers."""
    global _drivers
    _drivers = None

########NEW FILE########
__FILENAME__ = log_notifier
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

from oslo.config import cfg

from cloudbaseinit.openstack.common import jsonutils
from cloudbaseinit.openstack.common import log as logging


CONF = cfg.CONF


def notify(_context, message):
    """Notifies the recipient of the desired event given the model.

    Log notifications using OpenStack's default logging system.
    """

    priority = message.get('priority',
                           CONF.default_notification_level)
    priority = priority.lower()
    logger = logging.getLogger(
        'cloudbaseinit.openstack.common.notification.%s' %
        message['event_type'])
    getattr(logger, priority)(jsonutils.dumps(message))

########NEW FILE########
__FILENAME__ = no_op_notifier
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


def notify(_context, message):
    """Notifies the recipient of the desired event given the model."""
    pass

########NEW FILE########
__FILENAME__ = proxy
# Copyright 2013 Red Hat, Inc.
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
A temporary helper which emulates cloudbaseinit.messaging.Notifier.

This helper method allows us to do the tedious porting to the new Notifier API
as a standalone commit so that the commit which switches us to
cloudbaseinit.messaging
is smaller and easier to review. This file will be removed as part of that
commit.
"""

from oslo.config import cfg

from cloudbaseinit.openstack.common.notifier import api as notifier_api

CONF = cfg.CONF


class Notifier(object):

    def __init__(self, publisher_id):
        super(Notifier, self).__init__()
        self.publisher_id = publisher_id

    _marker = object()

    def prepare(self, publisher_id=_marker):
        ret = self.__class__(self.publisher_id)
        if publisher_id is not self._marker:
            ret.publisher_id = publisher_id
        return ret

    def _notify(self, ctxt, event_type, payload, priority):
        notifier_api.notify(ctxt,
                            self.publisher_id,
                            event_type,
                            priority,
                            payload)

    def audit(self, ctxt, event_type, payload):
        # No audit in old notifier.
        self._notify(ctxt, event_type, payload, 'INFO')

    def debug(self, ctxt, event_type, payload):
        self._notify(ctxt, event_type, payload, 'DEBUG')

    def info(self, ctxt, event_type, payload):
        self._notify(ctxt, event_type, payload, 'INFO')

    def warn(self, ctxt, event_type, payload):
        self._notify(ctxt, event_type, payload, 'WARN')

    warning = warn

    def error(self, ctxt, event_type, payload):
        self._notify(ctxt, event_type, payload, 'ERROR')

    def critical(self, ctxt, event_type, payload):
        self._notify(ctxt, event_type, payload, 'CRITICAL')


def get_notifier(service=None, host=None, publisher_id=None):
    if not publisher_id:
        publisher_id = "%s.%s" % (service, host or CONF.host)
    return Notifier(publisher_id)

########NEW FILE########
__FILENAME__ = rpc_notifier
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

from oslo.config import cfg

from cloudbaseinit.openstack.common import context as req_context
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import rpc

LOG = logging.getLogger(__name__)

notification_topic_opt = cfg.ListOpt(
    'notification_topics', default=['notifications', ],
    help='AMQP topic used for OpenStack notifications')

CONF = cfg.CONF
CONF.register_opt(notification_topic_opt)


def notify(context, message):
    """Sends a notification via RPC."""
    if not context:
        context = req_context.get_admin_context()
    priority = message.get('priority',
                           CONF.default_notification_level)
    priority = priority.lower()
    for topic in CONF.notification_topics:
        topic = '%s.%s' % (topic, priority)
        try:
            rpc.notify(context, topic, message)
        except Exception:
            LOG.exception(_("Could not send notification to %(topic)s. "
                            "Payload=%(message)s"),
                          {"topic": topic, "message": message})

########NEW FILE########
__FILENAME__ = rpc_notifier2
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

'''messaging based notification driver, with message envelopes'''

from oslo.config import cfg

from cloudbaseinit.openstack.common import context as req_context
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import rpc

LOG = logging.getLogger(__name__)

notification_topic_opt = cfg.ListOpt(
    'topics', default=['notifications', ],
    help='AMQP topic(s) used for OpenStack notifications')

opt_group = cfg.OptGroup(name='rpc_notifier2',
                         title='Options for rpc_notifier2')

CONF = cfg.CONF
CONF.register_group(opt_group)
CONF.register_opt(notification_topic_opt, opt_group)


def notify(context, message):
    """Sends a notification via RPC."""
    if not context:
        context = req_context.get_admin_context()
    priority = message.get('priority',
                           CONF.default_notification_level)
    priority = priority.lower()
    for topic in CONF.rpc_notifier2.topics:
        topic = '%s.%s' % (topic, priority)
        try:
            rpc.notify(context, topic, message, envelope=True)
        except Exception:
            LOG.exception(_("Could not send notification to %(topic)s. "
                            "Payload=%(message)s"),
                          {"topic": topic, "message": message})

########NEW FILE########
__FILENAME__ = test_notifier
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

NOTIFICATIONS = []


def notify(_context, message):
    """Test notifier, stores notifications in memory for unittests."""
    NOTIFICATIONS.append(message)

########NEW FILE########
__FILENAME__ = urlutils
#
# Copyright 2013 Canonical Ltd.
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
#

"""
Python2/Python3 compatibility layer for OpenStack
"""

import six

if six.PY3:
    # python3
    import urllib.error
    import urllib.parse
    import urllib.request

    urlencode = urllib.parse.urlencode
    urljoin = urllib.parse.urljoin
    quote = urllib.parse.quote
    quote_plus = urllib.parse.quote_plus
    parse_qsl = urllib.parse.parse_qsl
    unquote = urllib.parse.unquote
    unquote_plus = urllib.parse.unquote_plus
    urlparse = urllib.parse.urlparse
    urlsplit = urllib.parse.urlsplit
    urlunsplit = urllib.parse.urlunsplit
    SplitResult = urllib.parse.SplitResult

    urlopen = urllib.request.urlopen
    URLError = urllib.error.URLError
    pathname2url = urllib.request.pathname2url
else:
    # python2
    import urllib
    import urllib2
    import urlparse

    urlencode = urllib.urlencode
    quote = urllib.quote
    quote_plus = urllib.quote_plus
    unquote = urllib.unquote
    unquote_plus = urllib.unquote_plus

    parse = urlparse
    parse_qsl = parse.parse_qsl
    urljoin = parse.urljoin
    urlparse = parse.urlparse
    urlsplit = parse.urlsplit
    urlunsplit = parse.urlunsplit
    SplitResult = parse.SplitResult

    urlopen = urllib2.urlopen
    URLError = urllib2.URLError
    pathname2url = urllib.pathname2url

########NEW FILE########
__FILENAME__ = amqp
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2011 - 2012, Red Hat, Inc.
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
Shared code between AMQP based openstack.common.rpc implementations.

The code in this module is shared between the rpc implementations based on
AMQP. Specifically, this includes impl_kombu and impl_qpid. impl_carrot also
uses AMQP, but is deprecated and predates this code.
"""

import collections
import inspect
import sys
import uuid

from eventlet import greenpool
from eventlet import pools
from eventlet import queue
from eventlet import semaphore
from oslo.config import cfg
import six


from cloudbaseinit.openstack.common import excutils
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import local
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common.rpc import common as rpc_common


amqp_opts = [
    cfg.BoolOpt('amqp_durable_queues',
                default=False,
                deprecated_name='rabbit_durable_queues',
                deprecated_group='DEFAULT',
                help='Use durable queues in amqp.'),
    cfg.BoolOpt('amqp_auto_delete',
                default=False,
                help='Auto-delete queues in amqp.'),
]

cfg.CONF.register_opts(amqp_opts)

UNIQUE_ID = '_unique_id'
LOG = logging.getLogger(__name__)


class Pool(pools.Pool):
    """Class that implements a Pool of Connections."""
    def __init__(self, conf, connection_cls, *args, **kwargs):
        self.connection_cls = connection_cls
        self.conf = conf
        kwargs.setdefault("max_size", self.conf.rpc_conn_pool_size)
        kwargs.setdefault("order_as_stack", True)
        super(Pool, self).__init__(*args, **kwargs)
        self.reply_proxy = None

    # TODO(comstud): Timeout connections not used in a while
    def create(self):
        LOG.debug(_('Pool creating new connection'))
        return self.connection_cls(self.conf)

    def empty(self):
        while self.free_items:
            self.get().close()
        # Force a new connection pool to be created.
        # Note that this was added due to failing unit test cases. The issue
        # is the above "while loop" gets all the cached connections from the
        # pool and closes them, but never returns them to the pool, a pool
        # leak. The unit tests hang waiting for an item to be returned to the
        # pool. The unit tests get here via the tearDown() method. In the run
        # time code, it gets here via cleanup() and only appears in service.py
        # just before doing a sys.exit(), so cleanup() only happens once and
        # the leakage is not a problem.
        self.connection_cls.pool = None


_pool_create_sem = semaphore.Semaphore()


def get_connection_pool(conf, connection_cls):
    with _pool_create_sem:
        # Make sure only one thread tries to create the connection pool.
        if not connection_cls.pool:
            connection_cls.pool = Pool(conf, connection_cls)
    return connection_cls.pool


class ConnectionContext(rpc_common.Connection):
    """The class that is actually returned to the create_connection() caller.

    This is essentially a wrapper around Connection that supports 'with'.
    It can also return a new Connection, or one from a pool.

    The function will also catch when an instance of this class is to be
    deleted.  With that we can return Connections to the pool on exceptions
    and so forth without making the caller be responsible for catching them.
    If possible the function makes sure to return a connection to the pool.
    """

    def __init__(self, conf, connection_pool, pooled=True, server_params=None):
        """Create a new connection, or get one from the pool."""
        self.connection = None
        self.conf = conf
        self.connection_pool = connection_pool
        if pooled:
            self.connection = connection_pool.get()
        else:
            self.connection = connection_pool.connection_cls(
                conf,
                server_params=server_params)
        self.pooled = pooled

    def __enter__(self):
        """When with ConnectionContext() is used, return self."""
        return self

    def _done(self):
        """If the connection came from a pool, clean it up and put it back.
        If it did not come from a pool, close it.
        """
        if self.connection:
            if self.pooled:
                # Reset the connection so it's ready for the next caller
                # to grab from the pool
                self.connection.reset()
                self.connection_pool.put(self.connection)
            else:
                try:
                    self.connection.close()
                except Exception:
                    pass
            self.connection = None

    def __exit__(self, exc_type, exc_value, tb):
        """End of 'with' statement.  We're done here."""
        self._done()

    def __del__(self):
        """Caller is done with this connection.  Make sure we cleaned up."""
        self._done()

    def close(self):
        """Caller is done with this connection."""
        self._done()

    def create_consumer(self, topic, proxy, fanout=False):
        self.connection.create_consumer(topic, proxy, fanout)

    def create_worker(self, topic, proxy, pool_name):
        self.connection.create_worker(topic, proxy, pool_name)

    def join_consumer_pool(self, callback, pool_name, topic, exchange_name,
                           ack_on_error=True):
        self.connection.join_consumer_pool(callback,
                                           pool_name,
                                           topic,
                                           exchange_name,
                                           ack_on_error)

    def consume_in_thread(self):
        self.connection.consume_in_thread()

    def __getattr__(self, key):
        """Proxy all other calls to the Connection instance."""
        if self.connection:
            return getattr(self.connection, key)
        else:
            raise rpc_common.InvalidRPCConnectionReuse()


class ReplyProxy(ConnectionContext):
    """Connection class for RPC replies / callbacks."""
    def __init__(self, conf, connection_pool):
        self._call_waiters = {}
        self._num_call_waiters = 0
        self._num_call_waiters_wrn_threshold = 10
        self._reply_q = 'reply_' + uuid.uuid4().hex
        super(ReplyProxy, self).__init__(conf, connection_pool, pooled=False)
        self.declare_direct_consumer(self._reply_q, self._process_data)
        self.consume_in_thread()

    def _process_data(self, message_data):
        msg_id = message_data.pop('_msg_id', None)
        waiter = self._call_waiters.get(msg_id)
        if not waiter:
            LOG.warn(_('No calling threads waiting for msg_id : %(msg_id)s'
                       ', message : %(data)s'), {'msg_id': msg_id,
                                                 'data': message_data})
            LOG.warn(_('_call_waiters: %s') % str(self._call_waiters))
        else:
            waiter.put(message_data)

    def add_call_waiter(self, waiter, msg_id):
        self._num_call_waiters += 1
        if self._num_call_waiters > self._num_call_waiters_wrn_threshold:
            LOG.warn(_('Number of call waiters is greater than warning '
                       'threshold: %d. There could be a MulticallProxyWaiter '
                       'leak.') % self._num_call_waiters_wrn_threshold)
            self._num_call_waiters_wrn_threshold *= 2
        self._call_waiters[msg_id] = waiter

    def del_call_waiter(self, msg_id):
        self._num_call_waiters -= 1
        del self._call_waiters[msg_id]

    def get_reply_q(self):
        return self._reply_q


def msg_reply(conf, msg_id, reply_q, connection_pool, reply=None,
              failure=None, ending=False, log_failure=True):
    """Sends a reply or an error on the channel signified by msg_id.

    Failure should be a sys.exc_info() tuple.

    """
    with ConnectionContext(conf, connection_pool) as conn:
        if failure:
            failure = rpc_common.serialize_remote_exception(failure,
                                                            log_failure)

        msg = {'result': reply, 'failure': failure}
        if ending:
            msg['ending'] = True
        _add_unique_id(msg)
        # If a reply_q exists, add the msg_id to the reply and pass the
        # reply_q to direct_send() to use it as the response queue.
        # Otherwise use the msg_id for backward compatibility.
        if reply_q:
            msg['_msg_id'] = msg_id
            conn.direct_send(reply_q, rpc_common.serialize_msg(msg))
        else:
            conn.direct_send(msg_id, rpc_common.serialize_msg(msg))


class RpcContext(rpc_common.CommonRpcContext):
    """Context that supports replying to a rpc.call."""
    def __init__(self, **kwargs):
        self.msg_id = kwargs.pop('msg_id', None)
        self.reply_q = kwargs.pop('reply_q', None)
        self.conf = kwargs.pop('conf')
        super(RpcContext, self).__init__(**kwargs)

    def deepcopy(self):
        values = self.to_dict()
        values['conf'] = self.conf
        values['msg_id'] = self.msg_id
        values['reply_q'] = self.reply_q
        return self.__class__(**values)

    def reply(self, reply=None, failure=None, ending=False,
              connection_pool=None, log_failure=True):
        if self.msg_id:
            msg_reply(self.conf, self.msg_id, self.reply_q, connection_pool,
                      reply, failure, ending, log_failure)
            if ending:
                self.msg_id = None


def unpack_context(conf, msg):
    """Unpack context from msg."""
    context_dict = {}
    for key in list(msg.keys()):
        # NOTE(vish): Some versions of python don't like unicode keys
        #             in kwargs.
        key = str(key)
        if key.startswith('_context_'):
            value = msg.pop(key)
            context_dict[key[9:]] = value
    context_dict['msg_id'] = msg.pop('_msg_id', None)
    context_dict['reply_q'] = msg.pop('_reply_q', None)
    context_dict['conf'] = conf
    ctx = RpcContext.from_dict(context_dict)
    rpc_common._safe_log(LOG.debug, _('unpacked context: %s'), ctx.to_dict())
    return ctx


def pack_context(msg, context):
    """Pack context into msg.

    Values for message keys need to be less than 255 chars, so we pull
    context out into a bunch of separate keys. If we want to support
    more arguments in rabbit messages, we may want to do the same
    for args at some point.

    """
    if isinstance(context, dict):
        context_d = dict([('_context_%s' % key, value)
                          for (key, value) in six.iteritems(context)])
    else:
        context_d = dict([('_context_%s' % key, value)
                          for (key, value) in
                          six.iteritems(context.to_dict())])

    msg.update(context_d)


class _MsgIdCache(object):
    """This class checks any duplicate messages."""

    # NOTE: This value is considered can be a configuration item, but
    #       it is not necessary to change its value in most cases,
    #       so let this value as static for now.
    DUP_MSG_CHECK_SIZE = 16

    def __init__(self, **kwargs):
        self.prev_msgids = collections.deque([],
                                             maxlen=self.DUP_MSG_CHECK_SIZE)

    def check_duplicate_message(self, message_data):
        """AMQP consumers may read same message twice when exceptions occur
           before ack is returned. This method prevents doing it.
        """
        if UNIQUE_ID in message_data:
            msg_id = message_data[UNIQUE_ID]
            if msg_id not in self.prev_msgids:
                self.prev_msgids.append(msg_id)
            else:
                raise rpc_common.DuplicateMessageError(msg_id=msg_id)


def _add_unique_id(msg):
    """Add unique_id for checking duplicate messages."""
    unique_id = uuid.uuid4().hex
    msg.update({UNIQUE_ID: unique_id})
    LOG.debug(_('UNIQUE_ID is %s.') % (unique_id))


class _ThreadPoolWithWait(object):
    """Base class for a delayed invocation manager.

    Used by the Connection class to start up green threads
    to handle incoming messages.
    """

    def __init__(self, conf, connection_pool):
        self.pool = greenpool.GreenPool(conf.rpc_thread_pool_size)
        self.connection_pool = connection_pool
        self.conf = conf

    def wait(self):
        """Wait for all callback threads to exit."""
        self.pool.waitall()


class CallbackWrapper(_ThreadPoolWithWait):
    """Wraps a straight callback.

    Allows it to be invoked in a green thread.
    """

    def __init__(self, conf, callback, connection_pool,
                 wait_for_consumers=False):
        """Initiates CallbackWrapper object.

        :param conf: cfg.CONF instance
        :param callback: a callable (probably a function)
        :param connection_pool: connection pool as returned by
                                get_connection_pool()
        :param wait_for_consumers: wait for all green threads to
                                   complete and raise the last
                                   caught exception, if any.

        """
        super(CallbackWrapper, self).__init__(
            conf=conf,
            connection_pool=connection_pool,
        )
        self.callback = callback
        self.wait_for_consumers = wait_for_consumers
        self.exc_info = None

    def _wrap(self, message_data, **kwargs):
        """Wrap the callback invocation to catch exceptions.
        """
        try:
            self.callback(message_data, **kwargs)
        except Exception:
            self.exc_info = sys.exc_info()

    def __call__(self, message_data):
        self.exc_info = None
        self.pool.spawn_n(self._wrap, message_data)

        if self.wait_for_consumers:
            self.pool.waitall()
            if self.exc_info:
                six.reraise(self.exc_info[1], None, self.exc_info[2])


class ProxyCallback(_ThreadPoolWithWait):
    """Calls methods on a proxy object based on method and args."""

    def __init__(self, conf, proxy, connection_pool):
        super(ProxyCallback, self).__init__(
            conf=conf,
            connection_pool=connection_pool,
        )
        self.proxy = proxy
        self.msg_id_cache = _MsgIdCache()

    def __call__(self, message_data):
        """Consumer callback to call a method on a proxy object.

        Parses the message for validity and fires off a thread to call the
        proxy object method.

        Message data should be a dictionary with two keys:
            method: string representing the method to call
            args: dictionary of arg: value

        Example: {'method': 'echo', 'args': {'value': 42}}

        """
        # It is important to clear the context here, because at this point
        # the previous context is stored in local.store.context
        if hasattr(local.store, 'context'):
            del local.store.context
        rpc_common._safe_log(LOG.debug, _('received %s'), message_data)
        self.msg_id_cache.check_duplicate_message(message_data)
        ctxt = unpack_context(self.conf, message_data)
        method = message_data.get('method')
        args = message_data.get('args', {})
        version = message_data.get('version')
        namespace = message_data.get('namespace')
        if not method:
            LOG.warn(_('no method for message: %s') % message_data)
            ctxt.reply(_('No method for message: %s') % message_data,
                       connection_pool=self.connection_pool)
            return
        self.pool.spawn_n(self._process_data, ctxt, version, method,
                          namespace, args)

    def _process_data(self, ctxt, version, method, namespace, args):
        """Process a message in a new thread.

        If the proxy object we have has a dispatch method
        (see rpc.dispatcher.RpcDispatcher), pass it the version,
        method, and args and let it dispatch as appropriate.  If not, use
        the old behavior of magically calling the specified method on the
        proxy we have here.
        """
        ctxt.update_store()
        try:
            rval = self.proxy.dispatch(ctxt, version, method, namespace,
                                       **args)
            # Check if the result was a generator
            if inspect.isgenerator(rval):
                for x in rval:
                    ctxt.reply(x, None, connection_pool=self.connection_pool)
            else:
                ctxt.reply(rval, None, connection_pool=self.connection_pool)
            # This final None tells multicall that it is done.
            ctxt.reply(ending=True, connection_pool=self.connection_pool)
        except rpc_common.ClientException as e:
            LOG.debug(_('Expected exception during message handling (%s)') %
                      e._exc_info[1])
            ctxt.reply(None, e._exc_info,
                       connection_pool=self.connection_pool,
                       log_failure=False)
        except Exception:
            # sys.exc_info() is deleted by LOG.exception().
            exc_info = sys.exc_info()
            LOG.error(_('Exception during message handling'),
                      exc_info=exc_info)
            ctxt.reply(None, exc_info, connection_pool=self.connection_pool)


class MulticallProxyWaiter(object):
    def __init__(self, conf, msg_id, timeout, connection_pool):
        self._msg_id = msg_id
        self._timeout = timeout or conf.rpc_response_timeout
        self._reply_proxy = connection_pool.reply_proxy
        self._done = False
        self._got_ending = False
        self._conf = conf
        self._dataqueue = queue.LightQueue()
        # Add this caller to the reply proxy's call_waiters
        self._reply_proxy.add_call_waiter(self, self._msg_id)
        self.msg_id_cache = _MsgIdCache()

    def put(self, data):
        self._dataqueue.put(data)

    def done(self):
        if self._done:
            return
        self._done = True
        # Remove this caller from reply proxy's call_waiters
        self._reply_proxy.del_call_waiter(self._msg_id)

    def _process_data(self, data):
        result = None
        self.msg_id_cache.check_duplicate_message(data)
        if data['failure']:
            failure = data['failure']
            result = rpc_common.deserialize_remote_exception(self._conf,
                                                             failure)
        elif data.get('ending', False):
            self._got_ending = True
        else:
            result = data['result']
        return result

    def __iter__(self):
        """Return a result until we get a reply with an 'ending' flag."""
        if self._done:
            raise StopIteration
        while True:
            try:
                data = self._dataqueue.get(timeout=self._timeout)
                result = self._process_data(data)
            except queue.Empty:
                self.done()
                raise rpc_common.Timeout()
            except Exception:
                with excutils.save_and_reraise_exception():
                    self.done()
            if self._got_ending:
                self.done()
                raise StopIteration
            if isinstance(result, Exception):
                self.done()
                raise result
            yield result


def create_connection(conf, new, connection_pool):
    """Create a connection."""
    return ConnectionContext(conf, connection_pool, pooled=not new)


_reply_proxy_create_sem = semaphore.Semaphore()


def multicall(conf, context, topic, msg, timeout, connection_pool):
    """Make a call that returns multiple times."""
    LOG.debug(_('Making synchronous call on %s ...'), topic)
    msg_id = uuid.uuid4().hex
    msg.update({'_msg_id': msg_id})
    LOG.debug(_('MSG_ID is %s') % (msg_id))
    _add_unique_id(msg)
    pack_context(msg, context)

    with _reply_proxy_create_sem:
        if not connection_pool.reply_proxy:
            connection_pool.reply_proxy = ReplyProxy(conf, connection_pool)
    msg.update({'_reply_q': connection_pool.reply_proxy.get_reply_q()})
    wait_msg = MulticallProxyWaiter(conf, msg_id, timeout, connection_pool)
    with ConnectionContext(conf, connection_pool) as conn:
        conn.topic_send(topic, rpc_common.serialize_msg(msg), timeout)
    return wait_msg


def call(conf, context, topic, msg, timeout, connection_pool):
    """Sends a message on a topic and wait for a response."""
    rv = multicall(conf, context, topic, msg, timeout, connection_pool)
    # NOTE(vish): return the last result from the multicall
    rv = list(rv)
    if not rv:
        return
    return rv[-1]


def cast(conf, context, topic, msg, connection_pool):
    """Sends a message on a topic without waiting for a response."""
    LOG.debug(_('Making asynchronous cast on %s...'), topic)
    _add_unique_id(msg)
    pack_context(msg, context)
    with ConnectionContext(conf, connection_pool) as conn:
        conn.topic_send(topic, rpc_common.serialize_msg(msg))


def fanout_cast(conf, context, topic, msg, connection_pool):
    """Sends a message on a fanout exchange without waiting for a response."""
    LOG.debug(_('Making asynchronous fanout cast...'))
    _add_unique_id(msg)
    pack_context(msg, context)
    with ConnectionContext(conf, connection_pool) as conn:
        conn.fanout_send(topic, rpc_common.serialize_msg(msg))


def cast_to_server(conf, context, server_params, topic, msg, connection_pool):
    """Sends a message on a topic to a specific server."""
    _add_unique_id(msg)
    pack_context(msg, context)
    with ConnectionContext(conf, connection_pool, pooled=False,
                           server_params=server_params) as conn:
        conn.topic_send(topic, rpc_common.serialize_msg(msg))


def fanout_cast_to_server(conf, context, server_params, topic, msg,
                          connection_pool):
    """Sends a message on a fanout exchange to a specific server."""
    _add_unique_id(msg)
    pack_context(msg, context)
    with ConnectionContext(conf, connection_pool, pooled=False,
                           server_params=server_params) as conn:
        conn.fanout_send(topic, rpc_common.serialize_msg(msg))


def notify(conf, context, topic, msg, connection_pool, envelope):
    """Sends a notification event on a topic."""
    LOG.debug(_('Sending %(event_type)s on %(topic)s'),
              dict(event_type=msg.get('event_type'),
                   topic=topic))
    _add_unique_id(msg)
    pack_context(msg, context)
    with ConnectionContext(conf, connection_pool) as conn:
        if envelope:
            msg = rpc_common.serialize_msg(msg)
        conn.notify_send(topic, msg)


def cleanup(connection_pool):
    if connection_pool:
        connection_pool.empty()


def get_control_exchange(conf):
    return conf.control_exchange

########NEW FILE########
__FILENAME__ = common
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2011 Red Hat, Inc.
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

import copy
import sys
import traceback

from oslo.config import cfg
import six

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import jsonutils
from cloudbaseinit.openstack.common import local
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import versionutils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


_RPC_ENVELOPE_VERSION = '2.0'
'''RPC Envelope Version.

This version number applies to the top level structure of messages sent out.
It does *not* apply to the message payload, which must be versioned
independently.  For example, when using rpc APIs, a version number is applied
for changes to the API being exposed over rpc.  This version number is handled
in the rpc proxy and dispatcher modules.

This version number applies to the message envelope that is used in the
serialization done inside the rpc layer.  See serialize_msg() and
deserialize_msg().

The current message format (version 2.0) is very simple.  It is::

    {
        'cloudbaseinit.version': <RPC Envelope Version as a String>,
        'cloudbaseinit.message': <Application Message Payload, JSON encoded>
    }

Message format version '1.0' is just considered to be the messages we sent
without a message envelope.

So, the current message envelope just includes the envelope version.  It may
eventually contain additional information, such as a signature for the message
payload.

We will JSON encode the application message payload.  The message envelope,
which includes the JSON encoded application message body, will be passed down
to the messaging libraries as a dict.
'''

_VERSION_KEY = 'cloudbaseinit.version'
_MESSAGE_KEY = 'cloudbaseinit.message'

_REMOTE_POSTFIX = '_Remote'


class RPCException(Exception):
    msg_fmt = _("An unknown RPC related exception occurred.")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_('Exception in string format operation'))
                for name, value in six.iteritems(kwargs):
                    LOG.error("%s: %s" % (name, value))
                # at least get the core message out if something happened
                message = self.msg_fmt

        super(RPCException, self).__init__(message)


class RemoteError(RPCException):
    """Signifies that a remote class has raised an exception.

    Contains a string representation of the type of the original exception,
    the value of the original exception, and the traceback.  These are
    sent to the parent as a joined string so printing the exception
    contains all of the relevant info.

    """
    msg_fmt = _("Remote error: %(exc_type)s %(value)s\n%(traceback)s.")

    def __init__(self, exc_type=None, value=None, traceback=None):
        self.exc_type = exc_type
        self.value = value
        self.traceback = traceback
        super(RemoteError, self).__init__(exc_type=exc_type,
                                          value=value,
                                          traceback=traceback)


class Timeout(RPCException):
    """Signifies that a timeout has occurred.

    This exception is raised if the rpc_response_timeout is reached while
    waiting for a response from the remote side.
    """
    msg_fmt = _('Timeout while waiting on RPC response - '
                'topic: "%(topic)s", RPC method: "%(method)s" '
                'info: "%(info)s"')

    def __init__(self, info=None, topic=None, method=None):
        """Initiates Timeout object.

        :param info: Extra info to convey to the user
        :param topic: The topic that the rpc call was sent to
        :param rpc_method_name: The name of the rpc method being
                                called
        """
        self.info = info
        self.topic = topic
        self.method = method
        super(Timeout, self).__init__(
            None,
            info=info or _('<unknown>'),
            topic=topic or _('<unknown>'),
            method=method or _('<unknown>'))


class DuplicateMessageError(RPCException):
    msg_fmt = _("Found duplicate message(%(msg_id)s). Skipping it.")


class InvalidRPCConnectionReuse(RPCException):
    msg_fmt = _("Invalid reuse of an RPC connection.")


class UnsupportedRpcVersion(RPCException):
    msg_fmt = _("Specified RPC version, %(version)s, not supported by "
                "this endpoint.")


class UnsupportedRpcEnvelopeVersion(RPCException):
    msg_fmt = _("Specified RPC envelope version, %(version)s, "
                "not supported by this endpoint.")


class RpcVersionCapError(RPCException):
    msg_fmt = _("Specified RPC version cap, %(version_cap)s, is too low")


class Connection(object):
    """A connection, returned by rpc.create_connection().

    This class represents a connection to the message bus used for rpc.
    An instance of this class should never be created by users of the rpc API.
    Use rpc.create_connection() instead.
    """
    def close(self):
        """Close the connection.

        This method must be called when the connection will no longer be used.
        It will ensure that any resources associated with the connection, such
        as a network connection, and cleaned up.
        """
        raise NotImplementedError()

    def create_consumer(self, topic, proxy, fanout=False):
        """Create a consumer on this connection.

        A consumer is associated with a message queue on the backend message
        bus.  The consumer will read messages from the queue, unpack them, and
        dispatch them to the proxy object.  The contents of the message pulled
        off of the queue will determine which method gets called on the proxy
        object.

        :param topic: This is a name associated with what to consume from.
                      Multiple instances of a service may consume from the same
                      topic. For example, all instances of nova-compute consume
                      from a queue called "compute".  In that case, the
                      messages will get distributed amongst the consumers in a
                      round-robin fashion if fanout=False.  If fanout=True,
                      every consumer associated with this topic will get a
                      copy of every message.
        :param proxy: The object that will handle all incoming messages.
        :param fanout: Whether or not this is a fanout topic.  See the
                       documentation for the topic parameter for some
                       additional comments on this.
        """
        raise NotImplementedError()

    def create_worker(self, topic, proxy, pool_name):
        """Create a worker on this connection.

        A worker is like a regular consumer of messages directed to a
        topic, except that it is part of a set of such consumers (the
        "pool") which may run in parallel. Every pool of workers will
        receive a given message, but only one worker in the pool will
        be asked to process it. Load is distributed across the members
        of the pool in round-robin fashion.

        :param topic: This is a name associated with what to consume from.
                      Multiple instances of a service may consume from the same
                      topic.
        :param proxy: The object that will handle all incoming messages.
        :param pool_name: String containing the name of the pool of workers
        """
        raise NotImplementedError()

    def join_consumer_pool(self, callback, pool_name, topic, exchange_name):
        """Register as a member of a group of consumers.

        Uses given topic from the specified exchange.
        Exactly one member of a given pool will receive each message.

        A message will be delivered to multiple pools, if more than
        one is created.

        :param callback: Callable to be invoked for each message.
        :type callback: callable accepting one argument
        :param pool_name: The name of the consumer pool.
        :type pool_name: str
        :param topic: The routing topic for desired messages.
        :type topic: str
        :param exchange_name: The name of the message exchange where
                              the client should attach. Defaults to
                              the configured exchange.
        :type exchange_name: str
        """
        raise NotImplementedError()

    def consume_in_thread(self):
        """Spawn a thread to handle incoming messages.

        Spawn a thread that will be responsible for handling all incoming
        messages for consumers that were set up on this connection.

        Message dispatching inside of this is expected to be implemented in a
        non-blocking manner.  An example implementation would be having this
        thread pull messages in for all of the consumers, but utilize a thread
        pool for dispatching the messages to the proxy objects.
        """
        raise NotImplementedError()


def _safe_log(log_func, msg, msg_data):
    """Sanitizes the msg_data field before logging."""
    SANITIZE = ['_context_auth_token', 'auth_token', 'new_pass']

    def _fix_passwords(d):
        """Sanitizes the password fields in the dictionary."""
        for k in six.iterkeys(d):
            if k.lower().find('password') != -1:
                d[k] = '<SANITIZED>'
            elif k.lower() in SANITIZE:
                d[k] = '<SANITIZED>'
            elif isinstance(d[k], list):
                for e in d[k]:
                    if isinstance(e, dict):
                        _fix_passwords(e)
            elif isinstance(d[k], dict):
                _fix_passwords(d[k])
        return d

    return log_func(msg, _fix_passwords(copy.deepcopy(msg_data)))


def serialize_remote_exception(failure_info, log_failure=True):
    """Prepares exception data to be sent over rpc.

    Failure_info should be a sys.exc_info() tuple.

    """
    tb = traceback.format_exception(*failure_info)
    failure = failure_info[1]
    if log_failure:
        LOG.error(_("Returning exception %s to caller"),
                  six.text_type(failure))
        LOG.error(tb)

    kwargs = {}
    if hasattr(failure, 'kwargs'):
        kwargs = failure.kwargs

    # NOTE(matiu): With cells, it's possible to re-raise remote, remote
    # exceptions. Lets turn it back into the original exception type.
    cls_name = str(failure.__class__.__name__)
    mod_name = str(failure.__class__.__module__)
    if (cls_name.endswith(_REMOTE_POSTFIX) and
            mod_name.endswith(_REMOTE_POSTFIX)):
        cls_name = cls_name[:-len(_REMOTE_POSTFIX)]
        mod_name = mod_name[:-len(_REMOTE_POSTFIX)]

    data = {
        'class': cls_name,
        'module': mod_name,
        'message': six.text_type(failure),
        'tb': tb,
        'args': failure.args,
        'kwargs': kwargs
    }

    json_data = jsonutils.dumps(data)

    return json_data


def deserialize_remote_exception(conf, data):
    failure = jsonutils.loads(str(data))

    trace = failure.get('tb', [])
    message = failure.get('message', "") + "\n" + "\n".join(trace)
    name = failure.get('class')
    module = failure.get('module')

    # NOTE(ameade): We DO NOT want to allow just any module to be imported, in
    # order to prevent arbitrary code execution.
    if module not in conf.allowed_rpc_exception_modules:
        return RemoteError(name, failure.get('message'), trace)

    try:
        mod = importutils.import_module(module)
        klass = getattr(mod, name)
        if not issubclass(klass, Exception):
            raise TypeError("Can only deserialize Exceptions")

        failure = klass(*failure.get('args', []), **failure.get('kwargs', {}))
    except (AttributeError, TypeError, ImportError):
        return RemoteError(name, failure.get('message'), trace)

    ex_type = type(failure)
    str_override = lambda self: message
    new_ex_type = type(ex_type.__name__ + _REMOTE_POSTFIX, (ex_type,),
                       {'__str__': str_override, '__unicode__': str_override})
    new_ex_type.__module__ = '%s%s' % (module, _REMOTE_POSTFIX)
    try:
        # NOTE(ameade): Dynamically create a new exception type and swap it in
        # as the new type for the exception. This only works on user defined
        # Exceptions and not core python exceptions. This is important because
        # we cannot necessarily change an exception message so we must override
        # the __str__ method.
        failure.__class__ = new_ex_type
    except TypeError:
        # NOTE(ameade): If a core exception then just add the traceback to the
        # first exception argument.
        failure.args = (message,) + failure.args[1:]
    return failure


class CommonRpcContext(object):
    def __init__(self, **kwargs):
        self.values = kwargs

    def __getattr__(self, key):
        try:
            return self.values[key]
        except KeyError:
            raise AttributeError(key)

    def to_dict(self):
        return copy.deepcopy(self.values)

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    def deepcopy(self):
        return self.from_dict(self.to_dict())

    def update_store(self):
        local.store.context = self

    def elevated(self, read_deleted=None, overwrite=False):
        """Return a version of this context with admin flag set."""
        # TODO(russellb) This method is a bit of a nova-ism.  It makes
        # some assumptions about the data in the request context sent
        # across rpc, while the rest of this class does not.  We could get
        # rid of this if we changed the nova code that uses this to
        # convert the RpcContext back to its native RequestContext doing
        # something like nova.context.RequestContext.from_dict(ctxt.to_dict())

        context = self.deepcopy()
        context.values['is_admin'] = True

        context.values.setdefault('roles', [])

        if 'admin' not in context.values['roles']:
            context.values['roles'].append('admin')

        if read_deleted is not None:
            context.values['read_deleted'] = read_deleted

        return context


class ClientException(Exception):
    """Encapsulates actual exception expected to be hit by a RPC proxy object.

    Merely instantiating it records the current exception information, which
    will be passed back to the RPC client without exceptional logging.
    """
    def __init__(self):
        self._exc_info = sys.exc_info()


def catch_client_exception(exceptions, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if type(e) in exceptions:
            raise ClientException()
        else:
            raise


def client_exceptions(*exceptions):
    """Decorator for manager methods that raise expected exceptions.

    Marking a Manager method with this decorator allows the declaration
    of expected exceptions that the RPC layer should not consider fatal,
    and not log as if they were generated in a real error scenario. Note
    that this will cause listed exceptions to be wrapped in a
    ClientException, which is used internally by the RPC layer.
    """
    def outer(func):
        def inner(*args, **kwargs):
            return catch_client_exception(exceptions, func, *args, **kwargs)
        return inner
    return outer


# TODO(sirp): we should deprecate this in favor of
# using `versionutils.is_compatible` directly
def version_is_compatible(imp_version, version):
    """Determine whether versions are compatible.

    :param imp_version: The version implemented
    :param version: The version requested by an incoming message.
    """
    return versionutils.is_compatible(version, imp_version)


def serialize_msg(raw_msg):
    # NOTE(russellb) See the docstring for _RPC_ENVELOPE_VERSION for more
    # information about this format.
    msg = {_VERSION_KEY: _RPC_ENVELOPE_VERSION,
           _MESSAGE_KEY: jsonutils.dumps(raw_msg)}

    return msg


def deserialize_msg(msg):
    # NOTE(russellb): Hang on to your hats, this road is about to
    # get a little bumpy.
    #
    # Robustness Principle:
    #    "Be strict in what you send, liberal in what you accept."
    #
    # At this point we have to do a bit of guessing about what it
    # is we just received.  Here is the set of possibilities:
    #
    # 1) We received a dict.  This could be 2 things:
    #
    #   a) Inspect it to see if it looks like a standard message envelope.
    #      If so, great!
    #
    #   b) If it doesn't look like a standard message envelope, it could either
    #      be a notification, or a message from before we added a message
    #      envelope (referred to as version 1.0).
    #      Just return the message as-is.
    #
    # 2) It's any other non-dict type.  Just return it and hope for the best.
    #    This case covers return values from rpc.call() from before message
    #    envelopes were used.  (messages to call a method were always a dict)

    if not isinstance(msg, dict):
        # See #2 above.
        return msg

    base_envelope_keys = (_VERSION_KEY, _MESSAGE_KEY)
    if not all(map(lambda key: key in msg, base_envelope_keys)):
        #  See #1.b above.
        return msg

    # At this point we think we have the message envelope
    # format we were expecting. (#1.a above)

    if not version_is_compatible(_RPC_ENVELOPE_VERSION, msg[_VERSION_KEY]):
        raise UnsupportedRpcEnvelopeVersion(version=msg[_VERSION_KEY])

    raw_msg = jsonutils.loads(msg[_MESSAGE_KEY])

    return raw_msg

########NEW FILE########
__FILENAME__ = dispatcher
# Copyright 2012 Red Hat, Inc.
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
Code for rpc message dispatching.

Messages that come in have a version number associated with them.  RPC API
version numbers are in the form:

    Major.Minor

For a given message with version X.Y, the receiver must be marked as able to
handle messages of version A.B, where:

    A = X

    B >= Y

The Major version number would be incremented for an almost completely new API.
The Minor version number would be incremented for backwards compatible changes
to an existing API.  A backwards compatible change could be something like
adding a new method, adding an argument to an existing method (but not
requiring it), or changing the type for an existing argument (but still
handling the old type as well).

The conversion over to a versioned API must be done on both the client side and
server side of the API at the same time.  However, as the code stands today,
there can be both versioned and unversioned APIs implemented in the same code
base.

EXAMPLES
========

Nova was the first project to use versioned rpc APIs.  Consider the compute rpc
API as an example.  The client side is in nova/compute/rpcapi.py and the server
side is in nova/compute/manager.py.


Example 1) Adding a new method.
-------------------------------

Adding a new method is a backwards compatible change.  It should be added to
nova/compute/manager.py, and RPC_API_VERSION should be bumped from X.Y to
X.Y+1.  On the client side, the new method in nova/compute/rpcapi.py should
have a specific version specified to indicate the minimum API version that must
be implemented for the method to be supported.  For example::

    def get_host_uptime(self, ctxt, host):
        topic = _compute_topic(self.topic, ctxt, host, None)
        return self.call(ctxt, self.make_msg('get_host_uptime'), topic,
                version='1.1')

In this case, version '1.1' is the first version that supported the
get_host_uptime() method.


Example 2) Adding a new parameter.
----------------------------------

Adding a new parameter to an rpc method can be made backwards compatible.  The
RPC_API_VERSION on the server side (nova/compute/manager.py) should be bumped.
The implementation of the method must not expect the parameter to be present.::

    def some_remote_method(self, arg1, arg2, newarg=None):
        # The code needs to deal with newarg=None for cases
        # where an older client sends a message without it.
        pass

On the client side, the same changes should be made as in example 1.  The
minimum version that supports the new parameter should be specified.
"""

import six

from cloudbaseinit.openstack.common.rpc import common as rpc_common
from cloudbaseinit.openstack.common.rpc import serializer as rpc_serializer


class RpcDispatcher(object):
    """Dispatch rpc messages according to the requested API version.

    This class can be used as the top level 'manager' for a service.  It
    contains a list of underlying managers that have an API_VERSION attribute.
    """

    def __init__(self, callbacks, serializer=None):
        """Initialize the rpc dispatcher.

        :param callbacks: List of proxy objects that are an instance
                          of a class with rpc methods exposed.  Each proxy
                          object should have an RPC_API_VERSION attribute.
        :param serializer: The Serializer object that will be used to
                           deserialize arguments before the method call and
                           to serialize the result after it returns.
        """
        self.callbacks = callbacks
        if serializer is None:
            serializer = rpc_serializer.NoOpSerializer()
        self.serializer = serializer
        super(RpcDispatcher, self).__init__()

    def _deserialize_args(self, context, kwargs):
        """Helper method called to deserialize args before dispatch.

        This calls our serializer on each argument, returning a new set of
        args that have been deserialized.

        :param context: The request context
        :param kwargs: The arguments to be deserialized
        :returns: A new set of deserialized args
        """
        new_kwargs = dict()
        for argname, arg in six.iteritems(kwargs):
            new_kwargs[argname] = self.serializer.deserialize_entity(context,
                                                                     arg)
        return new_kwargs

    def dispatch(self, ctxt, version, method, namespace, **kwargs):
        """Dispatch a message based on a requested version.

        :param ctxt: The request context
        :param version: The requested API version from the incoming message
        :param method: The method requested to be called by the incoming
                       message.
        :param namespace: The namespace for the requested method.  If None,
                          the dispatcher will look for a method on a callback
                          object with no namespace set.
        :param kwargs: A dict of keyword arguments to be passed to the method.

        :returns: Whatever is returned by the underlying method that gets
                  called.
        """
        if not version:
            version = '1.0'

        had_compatible = False
        for proxyobj in self.callbacks:
            # Check for namespace compatibility
            try:
                cb_namespace = proxyobj.RPC_API_NAMESPACE
            except AttributeError:
                cb_namespace = None

            if namespace != cb_namespace:
                continue

            # Check for version compatibility
            try:
                rpc_api_version = proxyobj.RPC_API_VERSION
            except AttributeError:
                rpc_api_version = '1.0'

            is_compatible = rpc_common.version_is_compatible(rpc_api_version,
                                                             version)
            had_compatible = had_compatible or is_compatible

            if not hasattr(proxyobj, method):
                continue
            if is_compatible:
                kwargs = self._deserialize_args(ctxt, kwargs)
                result = getattr(proxyobj, method)(ctxt, **kwargs)
                return self.serializer.serialize_entity(ctxt, result)

        if had_compatible:
            raise AttributeError("No such RPC function '%s'" % method)
        else:
            raise rpc_common.UnsupportedRpcVersion(version=version)

########NEW FILE########
__FILENAME__ = impl_fake
#    Copyright 2011 OpenStack Foundation
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

"""Fake RPC implementation which calls proxy methods directly with no
queues.  Casts will block, but this is very useful for tests.
"""

import inspect
# NOTE(russellb): We specifically want to use json, not our own jsonutils.
# jsonutils has some extra logic to automatically convert objects to primitive
# types so that they can be serialized.  We want to catch all cases where
# non-primitive types make it into this code and treat it as an error.
import json
import time

import eventlet
import six

from cloudbaseinit.openstack.common.rpc import common as rpc_common

CONSUMERS = {}


class RpcContext(rpc_common.CommonRpcContext):
    def __init__(self, **kwargs):
        super(RpcContext, self).__init__(**kwargs)
        self._response = []
        self._done = False

    def deepcopy(self):
        values = self.to_dict()
        new_inst = self.__class__(**values)
        new_inst._response = self._response
        new_inst._done = self._done
        return new_inst

    def reply(self, reply=None, failure=None, ending=False):
        if ending:
            self._done = True
        if not self._done:
            self._response.append((reply, failure))


class Consumer(object):
    def __init__(self, topic, proxy):
        self.topic = topic
        self.proxy = proxy

    def call(self, context, version, method, namespace, args, timeout):
        done = eventlet.event.Event()

        def _inner():
            ctxt = RpcContext.from_dict(context.to_dict())
            try:
                rval = self.proxy.dispatch(context, version, method,
                                           namespace, **args)
                res = []
                # Caller might have called ctxt.reply() manually
                for (reply, failure) in ctxt._response:
                    if failure:
                        six.reraise(failure[0], failure[1], failure[2])
                    res.append(reply)
                # if ending not 'sent'...we might have more data to
                # return from the function itself
                if not ctxt._done:
                    if inspect.isgenerator(rval):
                        for val in rval:
                            res.append(val)
                    else:
                        res.append(rval)
                done.send(res)
            except rpc_common.ClientException as e:
                done.send_exception(e._exc_info[1])
            except Exception as e:
                done.send_exception(e)

        thread = eventlet.greenthread.spawn(_inner)

        if timeout:
            start_time = time.time()
            while not done.ready():
                eventlet.greenthread.sleep(1)
                cur_time = time.time()
                if (cur_time - start_time) > timeout:
                    thread.kill()
                    raise rpc_common.Timeout()

        return done.wait()


class Connection(object):
    """Connection object."""

    def __init__(self):
        self.consumers = []

    def create_consumer(self, topic, proxy, fanout=False):
        consumer = Consumer(topic, proxy)
        self.consumers.append(consumer)
        if topic not in CONSUMERS:
            CONSUMERS[topic] = []
        CONSUMERS[topic].append(consumer)

    def close(self):
        for consumer in self.consumers:
            CONSUMERS[consumer.topic].remove(consumer)
        self.consumers = []

    def consume_in_thread(self):
        pass


def create_connection(conf, new=True):
    """Create a connection."""
    return Connection()


def check_serialize(msg):
    """Make sure a message intended for rpc can be serialized."""
    json.dumps(msg)


def multicall(conf, context, topic, msg, timeout=None):
    """Make a call that returns multiple times."""

    check_serialize(msg)

    method = msg.get('method')
    if not method:
        return
    args = msg.get('args', {})
    version = msg.get('version', None)
    namespace = msg.get('namespace', None)

    try:
        consumer = CONSUMERS[topic][0]
    except (KeyError, IndexError):
        raise rpc_common.Timeout("No consumers available")
    else:
        return consumer.call(context, version, method, namespace, args,
                             timeout)


def call(conf, context, topic, msg, timeout=None):
    """Sends a message on a topic and wait for a response."""
    rv = multicall(conf, context, topic, msg, timeout)
    # NOTE(vish): return the last result from the multicall
    rv = list(rv)
    if not rv:
        return
    return rv[-1]


def cast(conf, context, topic, msg):
    check_serialize(msg)
    try:
        call(conf, context, topic, msg)
    except Exception:
        pass


def notify(conf, context, topic, msg, envelope):
    check_serialize(msg)


def cleanup():
    pass


def fanout_cast(conf, context, topic, msg):
    """Cast to all consumers of a topic."""
    check_serialize(msg)
    method = msg.get('method')
    if not method:
        return
    args = msg.get('args', {})
    version = msg.get('version', None)
    namespace = msg.get('namespace', None)

    for consumer in CONSUMERS.get(topic, []):
        try:
            consumer.call(context, version, method, namespace, args, None)
        except Exception:
            pass

########NEW FILE########
__FILENAME__ = impl_kombu
#    Copyright 2011 OpenStack Foundation
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
import itertools
import socket
import ssl
import time
import uuid

import eventlet
import greenlet
import kombu
import kombu.connection
import kombu.entity
import kombu.messaging
from oslo.config import cfg
import six

from cloudbaseinit.openstack.common import excutils
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import network_utils
from cloudbaseinit.openstack.common.rpc import amqp as rpc_amqp
from cloudbaseinit.openstack.common.rpc import common as rpc_common
from cloudbaseinit.openstack.common import sslutils

kombu_opts = [
    cfg.StrOpt('kombu_ssl_version',
               default='',
               help='If SSL is enabled, the SSL version to use. Valid '
                    'values are TLSv1, SSLv23 and SSLv3. SSLv2 might '
                    'be available on some distributions.'
               ),
    cfg.StrOpt('kombu_ssl_keyfile',
               default='',
               help='SSL key file (valid only if SSL enabled)'),
    cfg.StrOpt('kombu_ssl_certfile',
               default='',
               help='SSL cert file (valid only if SSL enabled)'),
    cfg.StrOpt('kombu_ssl_ca_certs',
               default='',
               help=('SSL certification authority file '
                     '(valid only if SSL enabled)')),
    cfg.StrOpt('rabbit_host',
               default='localhost',
               help='The RabbitMQ broker address where a single node is used'),
    cfg.IntOpt('rabbit_port',
               default=5672,
               help='The RabbitMQ broker port where a single node is used'),
    cfg.ListOpt('rabbit_hosts',
                default=['$rabbit_host:$rabbit_port'],
                help='RabbitMQ HA cluster host:port pairs'),
    cfg.BoolOpt('rabbit_use_ssl',
                default=False,
                help='Connect over SSL for RabbitMQ'),
    cfg.StrOpt('rabbit_userid',
               default='guest',
               help='The RabbitMQ userid'),
    cfg.StrOpt('rabbit_password',
               default='guest',
               help='The RabbitMQ password',
               secret=True),
    cfg.StrOpt('rabbit_virtual_host',
               default='/',
               help='The RabbitMQ virtual host'),
    cfg.IntOpt('rabbit_retry_interval',
               default=1,
               help='How frequently to retry connecting with RabbitMQ'),
    cfg.IntOpt('rabbit_retry_backoff',
               default=2,
               help='How long to backoff for between retries when connecting '
                    'to RabbitMQ'),
    cfg.IntOpt('rabbit_max_retries',
               default=0,
               help='Maximum number of RabbitMQ connection retries. '
                    'Default is 0 (infinite retry count)'),
    cfg.BoolOpt('rabbit_ha_queues',
                default=False,
                help='Use HA queues in RabbitMQ (x-ha-policy: all). '
                     'If you change this option, you must wipe the '
                     'RabbitMQ database.'),

]

cfg.CONF.register_opts(kombu_opts)

LOG = rpc_common.LOG


def _get_queue_arguments(conf):
    """Construct the arguments for declaring a queue.

    If the rabbit_ha_queues option is set, we declare a mirrored queue
    as described here:

      http://www.rabbitmq.com/ha.html

    Setting x-ha-policy to all means that the queue will be mirrored
    to all nodes in the cluster.
    """
    return {'x-ha-policy': 'all'} if conf.rabbit_ha_queues else {}


class ConsumerBase(object):
    """Consumer base class."""

    def __init__(self, channel, callback, tag, **kwargs):
        """Declare a queue on an amqp channel.

        'channel' is the amqp channel to use
        'callback' is the callback to call when messages are received
        'tag' is a unique ID for the consumer on the channel

        queue name, exchange name, and other kombu options are
        passed in here as a dictionary.
        """
        self.callback = callback
        self.tag = str(tag)
        self.kwargs = kwargs
        self.queue = None
        self.ack_on_error = kwargs.get('ack_on_error', True)
        self.reconnect(channel)

    def reconnect(self, channel):
        """Re-declare the queue after a rabbit reconnect."""
        self.channel = channel
        self.kwargs['channel'] = channel
        self.queue = kombu.entity.Queue(**self.kwargs)
        self.queue.declare()

    def _callback_handler(self, message, callback):
        """Call callback with deserialized message.

        Messages that are processed without exception are ack'ed.

        If the message processing generates an exception, it will be
        ack'ed if ack_on_error=True. Otherwise it will be .requeue()'ed.
        """

        try:
            msg = rpc_common.deserialize_msg(message.payload)
            callback(msg)
        except Exception:
            if self.ack_on_error:
                LOG.exception(_("Failed to process message"
                                " ... skipping it."))
                message.ack()
            else:
                LOG.exception(_("Failed to process message"
                                " ... will requeue."))
                message.requeue()
        else:
            message.ack()

    def consume(self, *args, **kwargs):
        """Actually declare the consumer on the amqp channel.  This will
        start the flow of messages from the queue.  Using the
        Connection.iterconsume() iterator will process the messages,
        calling the appropriate callback.

        If a callback is specified in kwargs, use that.  Otherwise,
        use the callback passed during __init__()

        If kwargs['nowait'] is True, then this call will block until
        a message is read.

        """

        options = {'consumer_tag': self.tag}
        options['nowait'] = kwargs.get('nowait', False)
        callback = kwargs.get('callback', self.callback)
        if not callback:
            raise ValueError("No callback defined")

        def _callback(raw_message):
            message = self.channel.message_to_python(raw_message)
            self._callback_handler(message, callback)

        self.queue.consume(*args, callback=_callback, **options)

    def cancel(self):
        """Cancel the consuming from the queue, if it has started."""
        try:
            self.queue.cancel(self.tag)
        except KeyError as e:
            # NOTE(comstud): Kludge to get around a amqplib bug
            if str(e) != "u'%s'" % self.tag:
                raise
        self.queue = None


class DirectConsumer(ConsumerBase):
    """Queue/consumer class for 'direct'."""

    def __init__(self, conf, channel, msg_id, callback, tag, **kwargs):
        """Init a 'direct' queue.

        'channel' is the amqp channel to use
        'msg_id' is the msg_id to listen on
        'callback' is the callback to call when messages are received
        'tag' is a unique ID for the consumer on the channel

        Other kombu options may be passed
        """
        # Default options
        options = {'durable': False,
                   'queue_arguments': _get_queue_arguments(conf),
                   'auto_delete': True,
                   'exclusive': False}
        options.update(kwargs)
        exchange = kombu.entity.Exchange(name=msg_id,
                                         type='direct',
                                         durable=options['durable'],
                                         auto_delete=options['auto_delete'])
        super(DirectConsumer, self).__init__(channel,
                                             callback,
                                             tag,
                                             name=msg_id,
                                             exchange=exchange,
                                             routing_key=msg_id,
                                             **options)


class TopicConsumer(ConsumerBase):
    """Consumer class for 'topic'."""

    def __init__(self, conf, channel, topic, callback, tag, name=None,
                 exchange_name=None, **kwargs):
        """Init a 'topic' queue.

        :param channel: the amqp channel to use
        :param topic: the topic to listen on
        :paramtype topic: str
        :param callback: the callback to call when messages are received
        :param tag: a unique ID for the consumer on the channel
        :param name: optional queue name, defaults to topic
        :paramtype name: str

        Other kombu options may be passed as keyword arguments
        """
        # Default options
        options = {'durable': conf.amqp_durable_queues,
                   'queue_arguments': _get_queue_arguments(conf),
                   'auto_delete': conf.amqp_auto_delete,
                   'exclusive': False}
        options.update(kwargs)
        exchange_name = exchange_name or rpc_amqp.get_control_exchange(conf)
        exchange = kombu.entity.Exchange(name=exchange_name,
                                         type='topic',
                                         durable=options['durable'],
                                         auto_delete=options['auto_delete'])
        super(TopicConsumer, self).__init__(channel,
                                            callback,
                                            tag,
                                            name=name or topic,
                                            exchange=exchange,
                                            routing_key=topic,
                                            **options)


class FanoutConsumer(ConsumerBase):
    """Consumer class for 'fanout'."""

    def __init__(self, conf, channel, topic, callback, tag, **kwargs):
        """Init a 'fanout' queue.

        'channel' is the amqp channel to use
        'topic' is the topic to listen on
        'callback' is the callback to call when messages are received
        'tag' is a unique ID for the consumer on the channel

        Other kombu options may be passed
        """
        unique = uuid.uuid4().hex
        exchange_name = '%s_fanout' % topic
        queue_name = '%s_fanout_%s' % (topic, unique)

        # Default options
        options = {'durable': False,
                   'queue_arguments': _get_queue_arguments(conf),
                   'auto_delete': True,
                   'exclusive': False}
        options.update(kwargs)
        exchange = kombu.entity.Exchange(name=exchange_name, type='fanout',
                                         durable=options['durable'],
                                         auto_delete=options['auto_delete'])
        super(FanoutConsumer, self).__init__(channel, callback, tag,
                                             name=queue_name,
                                             exchange=exchange,
                                             routing_key=topic,
                                             **options)


class Publisher(object):
    """Base Publisher class."""

    def __init__(self, channel, exchange_name, routing_key, **kwargs):
        """Init the Publisher class with the exchange_name, routing_key,
        and other options
        """
        self.exchange_name = exchange_name
        self.routing_key = routing_key
        self.kwargs = kwargs
        self.reconnect(channel)

    def reconnect(self, channel):
        """Re-establish the Producer after a rabbit reconnection."""
        self.exchange = kombu.entity.Exchange(name=self.exchange_name,
                                              **self.kwargs)
        self.producer = kombu.messaging.Producer(exchange=self.exchange,
                                                 channel=channel,
                                                 routing_key=self.routing_key)

    def send(self, msg, timeout=None):
        """Send a message."""
        if timeout:
            #
            # AMQP TTL is in milliseconds when set in the header.
            #
            self.producer.publish(msg, headers={'ttl': (timeout * 1000)})
        else:
            self.producer.publish(msg)


class DirectPublisher(Publisher):
    """Publisher class for 'direct'."""
    def __init__(self, conf, channel, msg_id, **kwargs):
        """init a 'direct' publisher.

        Kombu options may be passed as keyword args to override defaults
        """

        options = {'durable': False,
                   'auto_delete': True,
                   'exclusive': False}
        options.update(kwargs)
        super(DirectPublisher, self).__init__(channel, msg_id, msg_id,
                                              type='direct', **options)


class TopicPublisher(Publisher):
    """Publisher class for 'topic'."""
    def __init__(self, conf, channel, topic, **kwargs):
        """init a 'topic' publisher.

        Kombu options may be passed as keyword args to override defaults
        """
        options = {'durable': conf.amqp_durable_queues,
                   'auto_delete': conf.amqp_auto_delete,
                   'exclusive': False}
        options.update(kwargs)
        exchange_name = rpc_amqp.get_control_exchange(conf)
        super(TopicPublisher, self).__init__(channel,
                                             exchange_name,
                                             topic,
                                             type='topic',
                                             **options)


class FanoutPublisher(Publisher):
    """Publisher class for 'fanout'."""
    def __init__(self, conf, channel, topic, **kwargs):
        """init a 'fanout' publisher.

        Kombu options may be passed as keyword args to override defaults
        """
        options = {'durable': False,
                   'auto_delete': True,
                   'exclusive': False}
        options.update(kwargs)
        super(FanoutPublisher, self).__init__(channel, '%s_fanout' % topic,
                                              None, type='fanout', **options)


class NotifyPublisher(TopicPublisher):
    """Publisher class for 'notify'."""

    def __init__(self, conf, channel, topic, **kwargs):
        self.durable = kwargs.pop('durable', conf.amqp_durable_queues)
        self.queue_arguments = _get_queue_arguments(conf)
        super(NotifyPublisher, self).__init__(conf, channel, topic, **kwargs)

    def reconnect(self, channel):
        super(NotifyPublisher, self).reconnect(channel)

        # NOTE(jerdfelt): Normally the consumer would create the queue, but
        # we do this to ensure that messages don't get dropped if the
        # consumer is started after we do
        queue = kombu.entity.Queue(channel=channel,
                                   exchange=self.exchange,
                                   durable=self.durable,
                                   name=self.routing_key,
                                   routing_key=self.routing_key,
                                   queue_arguments=self.queue_arguments)
        queue.declare()


class Connection(object):
    """Connection object."""

    pool = None

    def __init__(self, conf, server_params=None):
        self.consumers = []
        self.consumer_thread = None
        self.proxy_callbacks = []
        self.conf = conf
        self.max_retries = self.conf.rabbit_max_retries
        # Try forever?
        if self.max_retries <= 0:
            self.max_retries = None
        self.interval_start = self.conf.rabbit_retry_interval
        self.interval_stepping = self.conf.rabbit_retry_backoff
        # max retry-interval = 30 seconds
        self.interval_max = 30
        self.memory_transport = False

        if server_params is None:
            server_params = {}
        # Keys to translate from server_params to kombu params
        server_params_to_kombu_params = {'username': 'userid'}

        ssl_params = self._fetch_ssl_params()
        params_list = []
        for adr in self.conf.rabbit_hosts:
            hostname, port = network_utils.parse_host_port(
                adr, default_port=self.conf.rabbit_port)

            params = {
                'hostname': hostname,
                'port': port,
                'userid': self.conf.rabbit_userid,
                'password': self.conf.rabbit_password,
                'virtual_host': self.conf.rabbit_virtual_host,
            }

            for sp_key, value in six.iteritems(server_params):
                p_key = server_params_to_kombu_params.get(sp_key, sp_key)
                params[p_key] = value

            if self.conf.fake_rabbit:
                params['transport'] = 'memory'
            if self.conf.rabbit_use_ssl:
                params['ssl'] = ssl_params

            params_list.append(params)

        self.params_list = params_list

        self.memory_transport = self.conf.fake_rabbit

        self.connection = None
        self.reconnect()

    def _fetch_ssl_params(self):
        """Handles fetching what ssl params should be used for the connection
        (if any).
        """
        ssl_params = dict()

        # http://docs.python.org/library/ssl.html - ssl.wrap_socket
        if self.conf.kombu_ssl_version:
            ssl_params['ssl_version'] = sslutils.validate_ssl_version(
                self.conf.kombu_ssl_version)
        if self.conf.kombu_ssl_keyfile:
            ssl_params['keyfile'] = self.conf.kombu_ssl_keyfile
        if self.conf.kombu_ssl_certfile:
            ssl_params['certfile'] = self.conf.kombu_ssl_certfile
        if self.conf.kombu_ssl_ca_certs:
            ssl_params['ca_certs'] = self.conf.kombu_ssl_ca_certs
            # We might want to allow variations in the
            # future with this?
            ssl_params['cert_reqs'] = ssl.CERT_REQUIRED

        # Return the extended behavior or just have the default behavior
        return ssl_params or True

    def _connect(self, params):
        """Connect to rabbit.  Re-establish any queues that may have
        been declared before if we are reconnecting.  Exceptions should
        be handled by the caller.
        """
        if self.connection:
            LOG.info(_("Reconnecting to AMQP server on "
                     "%(hostname)s:%(port)d") % params)
            try:
                self.connection.release()
            except self.connection_errors:
                pass
            # Setting this in case the next statement fails, though
            # it shouldn't be doing any network operations, yet.
            self.connection = None
        self.connection = kombu.connection.BrokerConnection(**params)
        self.connection_errors = self.connection.connection_errors
        if self.memory_transport:
            # Kludge to speed up tests.
            self.connection.transport.polling_interval = 0.0
        self.consumer_num = itertools.count(1)
        self.connection.connect()
        self.channel = self.connection.channel()
        # work around 'memory' transport bug in 1.1.3
        if self.memory_transport:
            self.channel._new_queue('ae.undeliver')
        for consumer in self.consumers:
            consumer.reconnect(self.channel)
        LOG.info(_('Connected to AMQP server on %(hostname)s:%(port)d') %
                 params)

    def reconnect(self):
        """Handles reconnecting and re-establishing queues.
        Will retry up to self.max_retries number of times.
        self.max_retries = 0 means to retry forever.
        Sleep between tries, starting at self.interval_start
        seconds, backing off self.interval_stepping number of seconds
        each attempt.
        """

        attempt = 0
        while True:
            params = self.params_list[attempt % len(self.params_list)]
            attempt += 1
            try:
                self._connect(params)
                return
            except (IOError, self.connection_errors) as e:
                pass
            except Exception as e:
                # NOTE(comstud): Unfortunately it's possible for amqplib
                # to return an error not covered by its transport
                # connection_errors in the case of a timeout waiting for
                # a protocol response.  (See paste link in LP888621)
                # So, we check all exceptions for 'timeout' in them
                # and try to reconnect in this case.
                if 'timeout' not in str(e):
                    raise

            log_info = {}
            log_info['err_str'] = str(e)
            log_info['max_retries'] = self.max_retries
            log_info.update(params)

            if self.max_retries and attempt == self.max_retries:
                msg = _('Unable to connect to AMQP server on '
                        '%(hostname)s:%(port)d after %(max_retries)d '
                        'tries: %(err_str)s') % log_info
                LOG.error(msg)
                raise rpc_common.RPCException(msg)

            if attempt == 1:
                sleep_time = self.interval_start or 1
            elif attempt > 1:
                sleep_time += self.interval_stepping
            if self.interval_max:
                sleep_time = min(sleep_time, self.interval_max)

            log_info['sleep_time'] = sleep_time
            LOG.error(_('AMQP server on %(hostname)s:%(port)d is '
                        'unreachable: %(err_str)s. Trying again in '
                        '%(sleep_time)d seconds.') % log_info)
            time.sleep(sleep_time)

    def ensure(self, error_callback, method, *args, **kwargs):
        while True:
            try:
                return method(*args, **kwargs)
            except (self.connection_errors, socket.timeout, IOError) as e:
                if error_callback:
                    error_callback(e)
            except Exception as e:
                # NOTE(comstud): Unfortunately it's possible for amqplib
                # to return an error not covered by its transport
                # connection_errors in the case of a timeout waiting for
                # a protocol response.  (See paste link in LP888621)
                # So, we check all exceptions for 'timeout' in them
                # and try to reconnect in this case.
                if 'timeout' not in str(e):
                    raise
                if error_callback:
                    error_callback(e)
            self.reconnect()

    def get_channel(self):
        """Convenience call for bin/clear_rabbit_queues."""
        return self.channel

    def close(self):
        """Close/release this connection."""
        self.cancel_consumer_thread()
        self.wait_on_proxy_callbacks()
        self.connection.release()
        self.connection = None

    def reset(self):
        """Reset a connection so it can be used again."""
        self.cancel_consumer_thread()
        self.wait_on_proxy_callbacks()
        self.channel.close()
        self.channel = self.connection.channel()
        # work around 'memory' transport bug in 1.1.3
        if self.memory_transport:
            self.channel._new_queue('ae.undeliver')
        self.consumers = []

    def declare_consumer(self, consumer_cls, topic, callback):
        """Create a Consumer using the class that was passed in and
        add it to our list of consumers
        """

        def _connect_error(exc):
            log_info = {'topic': topic, 'err_str': str(exc)}
            LOG.error(_("Failed to declare consumer for topic '%(topic)s': "
                      "%(err_str)s") % log_info)

        def _declare_consumer():
            consumer = consumer_cls(self.conf, self.channel, topic, callback,
                                    six.next(self.consumer_num))
            self.consumers.append(consumer)
            return consumer

        return self.ensure(_connect_error, _declare_consumer)

    def iterconsume(self, limit=None, timeout=None):
        """Return an iterator that will consume from all queues/consumers."""

        info = {'do_consume': True}

        def _error_callback(exc):
            if isinstance(exc, socket.timeout):
                LOG.debug(_('Timed out waiting for RPC response: %s') %
                          str(exc))
                raise rpc_common.Timeout()
            else:
                LOG.exception(_('Failed to consume message from queue: %s') %
                              str(exc))
                info['do_consume'] = True

        def _consume():
            if info['do_consume']:
                queues_head = self.consumers[:-1]  # not fanout.
                queues_tail = self.consumers[-1]  # fanout
                for queue in queues_head:
                    queue.consume(nowait=True)
                queues_tail.consume(nowait=False)
                info['do_consume'] = False
            return self.connection.drain_events(timeout=timeout)

        for iteration in itertools.count(0):
            if limit and iteration >= limit:
                raise StopIteration
            yield self.ensure(_error_callback, _consume)

    def cancel_consumer_thread(self):
        """Cancel a consumer thread."""
        if self.consumer_thread is not None:
            self.consumer_thread.kill()
            try:
                self.consumer_thread.wait()
            except greenlet.GreenletExit:
                pass
            self.consumer_thread = None

    def wait_on_proxy_callbacks(self):
        """Wait for all proxy callback threads to exit."""
        for proxy_cb in self.proxy_callbacks:
            proxy_cb.wait()

    def publisher_send(self, cls, topic, msg, timeout=None, **kwargs):
        """Send to a publisher based on the publisher class."""

        def _error_callback(exc):
            log_info = {'topic': topic, 'err_str': str(exc)}
            LOG.exception(_("Failed to publish message to topic "
                          "'%(topic)s': %(err_str)s") % log_info)

        def _publish():
            publisher = cls(self.conf, self.channel, topic, **kwargs)
            publisher.send(msg, timeout)

        self.ensure(_error_callback, _publish)

    def declare_direct_consumer(self, topic, callback):
        """Create a 'direct' queue.
        In nova's use, this is generally a msg_id queue used for
        responses for call/multicall
        """
        self.declare_consumer(DirectConsumer, topic, callback)

    def declare_topic_consumer(self, topic, callback=None, queue_name=None,
                               exchange_name=None, ack_on_error=True):
        """Create a 'topic' consumer."""
        self.declare_consumer(functools.partial(TopicConsumer,
                                                name=queue_name,
                                                exchange_name=exchange_name,
                                                ack_on_error=ack_on_error,
                                                ),
                              topic, callback)

    def declare_fanout_consumer(self, topic, callback):
        """Create a 'fanout' consumer."""
        self.declare_consumer(FanoutConsumer, topic, callback)

    def direct_send(self, msg_id, msg):
        """Send a 'direct' message."""
        self.publisher_send(DirectPublisher, msg_id, msg)

    def topic_send(self, topic, msg, timeout=None):
        """Send a 'topic' message."""
        self.publisher_send(TopicPublisher, topic, msg, timeout)

    def fanout_send(self, topic, msg):
        """Send a 'fanout' message."""
        self.publisher_send(FanoutPublisher, topic, msg)

    def notify_send(self, topic, msg, **kwargs):
        """Send a notify message on a topic."""
        self.publisher_send(NotifyPublisher, topic, msg, None, **kwargs)

    def consume(self, limit=None):
        """Consume from all queues/consumers."""
        it = self.iterconsume(limit=limit)
        while True:
            try:
                six.next(it)
            except StopIteration:
                return

    def consume_in_thread(self):
        """Consumer from all queues/consumers in a greenthread."""
        @excutils.forever_retry_uncaught_exceptions
        def _consumer_thread():
            try:
                self.consume()
            except greenlet.GreenletExit:
                return
        if self.consumer_thread is None:
            self.consumer_thread = eventlet.spawn(_consumer_thread)
        return self.consumer_thread

    def create_consumer(self, topic, proxy, fanout=False):
        """Create a consumer that calls a method in a proxy object."""
        proxy_cb = rpc_amqp.ProxyCallback(
            self.conf, proxy,
            rpc_amqp.get_connection_pool(self.conf, Connection))
        self.proxy_callbacks.append(proxy_cb)

        if fanout:
            self.declare_fanout_consumer(topic, proxy_cb)
        else:
            self.declare_topic_consumer(topic, proxy_cb)

    def create_worker(self, topic, proxy, pool_name):
        """Create a worker that calls a method in a proxy object."""
        proxy_cb = rpc_amqp.ProxyCallback(
            self.conf, proxy,
            rpc_amqp.get_connection_pool(self.conf, Connection))
        self.proxy_callbacks.append(proxy_cb)
        self.declare_topic_consumer(topic, proxy_cb, pool_name)

    def join_consumer_pool(self, callback, pool_name, topic,
                           exchange_name=None, ack_on_error=True):
        """Register as a member of a group of consumers for a given topic from
        the specified exchange.

        Exactly one member of a given pool will receive each message.

        A message will be delivered to multiple pools, if more than
        one is created.
        """
        callback_wrapper = rpc_amqp.CallbackWrapper(
            conf=self.conf,
            callback=callback,
            connection_pool=rpc_amqp.get_connection_pool(self.conf,
                                                         Connection),
            wait_for_consumers=not ack_on_error
        )
        self.proxy_callbacks.append(callback_wrapper)
        self.declare_topic_consumer(
            queue_name=pool_name,
            topic=topic,
            exchange_name=exchange_name,
            callback=callback_wrapper,
            ack_on_error=ack_on_error,
        )


def create_connection(conf, new=True):
    """Create a connection."""
    return rpc_amqp.create_connection(
        conf, new,
        rpc_amqp.get_connection_pool(conf, Connection))


def multicall(conf, context, topic, msg, timeout=None):
    """Make a call that returns multiple times."""
    return rpc_amqp.multicall(
        conf, context, topic, msg, timeout,
        rpc_amqp.get_connection_pool(conf, Connection))


def call(conf, context, topic, msg, timeout=None):
    """Sends a message on a topic and wait for a response."""
    return rpc_amqp.call(
        conf, context, topic, msg, timeout,
        rpc_amqp.get_connection_pool(conf, Connection))


def cast(conf, context, topic, msg):
    """Sends a message on a topic without waiting for a response."""
    return rpc_amqp.cast(
        conf, context, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def fanout_cast(conf, context, topic, msg):
    """Sends a message on a fanout exchange without waiting for a response."""
    return rpc_amqp.fanout_cast(
        conf, context, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def cast_to_server(conf, context, server_params, topic, msg):
    """Sends a message on a topic to a specific server."""
    return rpc_amqp.cast_to_server(
        conf, context, server_params, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def fanout_cast_to_server(conf, context, server_params, topic, msg):
    """Sends a message on a fanout exchange to a specific server."""
    return rpc_amqp.fanout_cast_to_server(
        conf, context, server_params, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def notify(conf, context, topic, msg, envelope):
    """Sends a notification event on a topic."""
    return rpc_amqp.notify(
        conf, context, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection),
        envelope)


def cleanup():
    return rpc_amqp.cleanup(Connection.pool)

########NEW FILE########
__FILENAME__ = impl_qpid
#    Copyright 2011 OpenStack Foundation
#    Copyright 2011 - 2012, Red Hat, Inc.
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
import itertools
import time

import eventlet
import greenlet
from oslo.config import cfg
import six

from cloudbaseinit.openstack.common import excutils
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import jsonutils
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common.rpc import amqp as rpc_amqp
from cloudbaseinit.openstack.common.rpc import common as rpc_common

qpid_codec = importutils.try_import("qpid.codec010")
qpid_messaging = importutils.try_import("qpid.messaging")
qpid_exceptions = importutils.try_import("qpid.messaging.exceptions")

LOG = logging.getLogger(__name__)

qpid_opts = [
    cfg.StrOpt('qpid_hostname',
               default='localhost',
               help='Qpid broker hostname'),
    cfg.IntOpt('qpid_port',
               default=5672,
               help='Qpid broker port'),
    cfg.ListOpt('qpid_hosts',
                default=['$qpid_hostname:$qpid_port'],
                help='Qpid HA cluster host:port pairs'),
    cfg.StrOpt('qpid_username',
               default='',
               help='Username for qpid connection'),
    cfg.StrOpt('qpid_password',
               default='',
               help='Password for qpid connection',
               secret=True),
    cfg.StrOpt('qpid_sasl_mechanisms',
               default='',
               help='Space separated list of SASL mechanisms to use for auth'),
    cfg.IntOpt('qpid_heartbeat',
               default=60,
               help='Seconds between connection keepalive heartbeats'),
    cfg.StrOpt('qpid_protocol',
               default='tcp',
               help="Transport to use, either 'tcp' or 'ssl'"),
    cfg.BoolOpt('qpid_tcp_nodelay',
                default=True,
                help='Disable Nagle algorithm'),
    # NOTE(russellb) If any additional versions are added (beyond 1 and 2),
    # this file could probably use some additional refactoring so that the
    # differences between each version are split into different classes.
    cfg.IntOpt('qpid_topology_version',
               default=1,
               help="The qpid topology version to use.  Version 1 is what "
                    "was originally used by impl_qpid.  Version 2 includes "
                    "some backwards-incompatible changes that allow broker "
                    "federation to work.  Users should update to version 2 "
                    "when they are able to take everything down, as it "
                    "requires a clean break."),
]

cfg.CONF.register_opts(qpid_opts)

JSON_CONTENT_TYPE = 'application/json; charset=utf8'


def raise_invalid_topology_version(conf):
    msg = (_("Invalid value for qpid_topology_version: %d") %
           conf.qpid_topology_version)
    LOG.error(msg)
    raise Exception(msg)


class ConsumerBase(object):
    """Consumer base class."""

    def __init__(self, conf, session, callback, node_name, node_opts,
                 link_name, link_opts):
        """Declare a queue on an amqp session.

        'session' is the amqp session to use
        'callback' is the callback to call when messages are received
        'node_name' is the first part of the Qpid address string, before ';'
        'node_opts' will be applied to the "x-declare" section of "node"
                    in the address string.
        'link_name' goes into the "name" field of the "link" in the address
                    string
        'link_opts' will be applied to the "x-declare" section of "link"
                    in the address string.
        """
        self.callback = callback
        self.receiver = None
        self.session = None

        if conf.qpid_topology_version == 1:
            addr_opts = {
                "create": "always",
                "node": {
                    "type": "topic",
                    "x-declare": {
                        "durable": True,
                        "auto-delete": True,
                    },
                },
                "link": {
                    "durable": True,
                    "x-declare": {
                        "durable": False,
                        "auto-delete": True,
                        "exclusive": False,
                    },
                },
            }
            addr_opts["node"]["x-declare"].update(node_opts)
        elif conf.qpid_topology_version == 2:
            addr_opts = {
                "link": {
                    "x-declare": {
                        "auto-delete": True,
                        "exclusive": False,
                    },
                },
            }
        else:
            raise_invalid_topology_version()

        addr_opts["link"]["x-declare"].update(link_opts)
        if link_name:
            addr_opts["link"]["name"] = link_name

        self.address = "%s ; %s" % (node_name, jsonutils.dumps(addr_opts))

        self.connect(session)

    def connect(self, session):
        """Declare the receiver on connect."""
        self._declare_receiver(session)

    def reconnect(self, session):
        """Re-declare the receiver after a qpid reconnect."""
        self._declare_receiver(session)

    def _declare_receiver(self, session):
        self.session = session
        self.receiver = session.receiver(self.address)
        self.receiver.capacity = 1

    def _unpack_json_msg(self, msg):
        """Load the JSON data in msg if msg.content_type indicates that it
           is necessary.  Put the loaded data back into msg.content and
           update msg.content_type appropriately.

        A Qpid Message containing a dict will have a content_type of
        'amqp/map', whereas one containing a string that needs to be converted
        back from JSON will have a content_type of JSON_CONTENT_TYPE.

        :param msg: a Qpid Message object
        :returns: None
        """
        if msg.content_type == JSON_CONTENT_TYPE:
            msg.content = jsonutils.loads(msg.content)
            msg.content_type = 'amqp/map'

    def consume(self):
        """Fetch the message and pass it to the callback object."""
        message = self.receiver.fetch()
        try:
            self._unpack_json_msg(message)
            msg = rpc_common.deserialize_msg(message.content)
            self.callback(msg)
        except Exception:
            LOG.exception(_("Failed to process message... skipping it."))
        finally:
            # TODO(sandy): Need support for optional ack_on_error.
            self.session.acknowledge(message)

    def get_receiver(self):
        return self.receiver

    def get_node_name(self):
        return self.address.split(';')[0]


class DirectConsumer(ConsumerBase):
    """Queue/consumer class for 'direct'."""

    def __init__(self, conf, session, msg_id, callback):
        """Init a 'direct' queue.

        'session' is the amqp session to use
        'msg_id' is the msg_id to listen on
        'callback' is the callback to call when messages are received
        """

        link_opts = {
            "auto-delete": conf.amqp_auto_delete,
            "exclusive": True,
            "durable": conf.amqp_durable_queues,
        }

        if conf.qpid_topology_version == 1:
            node_name = "%s/%s" % (msg_id, msg_id)
            node_opts = {"type": "direct"}
            link_name = msg_id
        elif conf.qpid_topology_version == 2:
            node_name = "amq.direct/%s" % msg_id
            node_opts = {}
            link_name = None
        else:
            raise_invalid_topology_version()

        super(DirectConsumer, self).__init__(conf, session, callback,
                                             node_name, node_opts, link_name,
                                             link_opts)


class TopicConsumer(ConsumerBase):
    """Consumer class for 'topic'."""

    def __init__(self, conf, session, topic, callback, name=None,
                 exchange_name=None):
        """Init a 'topic' queue.

        :param session: the amqp session to use
        :param topic: is the topic to listen on
        :paramtype topic: str
        :param callback: the callback to call when messages are received
        :param name: optional queue name, defaults to topic
        """

        exchange_name = exchange_name or rpc_amqp.get_control_exchange(conf)
        link_opts = {
            "auto-delete": conf.amqp_auto_delete,
            "durable": conf.amqp_durable_queues,
        }

        if conf.qpid_topology_version == 1:
            node_name = "%s/%s" % (exchange_name, topic)
        elif conf.qpid_topology_version == 2:
            node_name = "amq.topic/topic/%s/%s" % (exchange_name, topic)
        else:
            raise_invalid_topology_version()

        super(TopicConsumer, self).__init__(conf, session, callback, node_name,
                                            {}, name or topic, link_opts)


class FanoutConsumer(ConsumerBase):
    """Consumer class for 'fanout'."""

    def __init__(self, conf, session, topic, callback):
        """Init a 'fanout' queue.

        'session' is the amqp session to use
        'topic' is the topic to listen on
        'callback' is the callback to call when messages are received
        """
        self.conf = conf

        link_opts = {"exclusive": True}

        if conf.qpid_topology_version == 1:
            node_name = "%s_fanout" % topic
            node_opts = {"durable": False, "type": "fanout"}
        elif conf.qpid_topology_version == 2:
            node_name = "amq.topic/fanout/%s" % topic
            node_opts = {}
        else:
            raise_invalid_topology_version()

        super(FanoutConsumer, self).__init__(conf, session, callback,
                                             node_name, node_opts, None,
                                             link_opts)


class Publisher(object):
    """Base Publisher class."""

    def __init__(self, conf, session, node_name, node_opts=None):
        """Init the Publisher class with the exchange_name, routing_key,
        and other options
        """
        self.sender = None
        self.session = session

        if conf.qpid_topology_version == 1:
            addr_opts = {
                "create": "always",
                "node": {
                    "type": "topic",
                    "x-declare": {
                        "durable": False,
                        # auto-delete isn't implemented for exchanges in qpid,
                        # but put in here anyway
                        "auto-delete": True,
                    },
                },
            }
            if node_opts:
                addr_opts["node"]["x-declare"].update(node_opts)

            self.address = "%s ; %s" % (node_name, jsonutils.dumps(addr_opts))
        elif conf.qpid_topology_version == 2:
            self.address = node_name
        else:
            raise_invalid_topology_version()

        self.reconnect(session)

    def reconnect(self, session):
        """Re-establish the Sender after a reconnection."""
        self.sender = session.sender(self.address)

    def _pack_json_msg(self, msg):
        """Qpid cannot serialize dicts containing strings longer than 65535
           characters.  This function dumps the message content to a JSON
           string, which Qpid is able to handle.

        :param msg: May be either a Qpid Message object or a bare dict.
        :returns: A Qpid Message with its content field JSON encoded.
        """
        try:
            msg.content = jsonutils.dumps(msg.content)
        except AttributeError:
            # Need to have a Qpid message so we can set the content_type.
            msg = qpid_messaging.Message(jsonutils.dumps(msg))
        msg.content_type = JSON_CONTENT_TYPE
        return msg

    def send(self, msg):
        """Send a message."""
        try:
            # Check if Qpid can encode the message
            check_msg = msg
            if not hasattr(check_msg, 'content_type'):
                check_msg = qpid_messaging.Message(msg)
            content_type = check_msg.content_type
            enc, dec = qpid_messaging.message.get_codec(content_type)
            enc(check_msg.content)
        except qpid_codec.CodecException:
            # This means the message couldn't be serialized as a dict.
            msg = self._pack_json_msg(msg)
        self.sender.send(msg)


class DirectPublisher(Publisher):
    """Publisher class for 'direct'."""
    def __init__(self, conf, session, msg_id):
        """Init a 'direct' publisher."""

        if conf.qpid_topology_version == 1:
            node_name = msg_id
            node_opts = {"type": "direct"}
        elif conf.qpid_topology_version == 2:
            node_name = "amq.direct/%s" % msg_id
            node_opts = {}
        else:
            raise_invalid_topology_version()

        super(DirectPublisher, self).__init__(conf, session, node_name,
                                              node_opts)


class TopicPublisher(Publisher):
    """Publisher class for 'topic'."""
    def __init__(self, conf, session, topic):
        """Init a 'topic' publisher.
        """
        exchange_name = rpc_amqp.get_control_exchange(conf)

        if conf.qpid_topology_version == 1:
            node_name = "%s/%s" % (exchange_name, topic)
        elif conf.qpid_topology_version == 2:
            node_name = "amq.topic/topic/%s/%s" % (exchange_name, topic)
        else:
            raise_invalid_topology_version()

        super(TopicPublisher, self).__init__(conf, session, node_name)


class FanoutPublisher(Publisher):
    """Publisher class for 'fanout'."""
    def __init__(self, conf, session, topic):
        """Init a 'fanout' publisher.
        """

        if conf.qpid_topology_version == 1:
            node_name = "%s_fanout" % topic
            node_opts = {"type": "fanout"}
        elif conf.qpid_topology_version == 2:
            node_name = "amq.topic/fanout/%s" % topic
            node_opts = {}
        else:
            raise_invalid_topology_version()

        super(FanoutPublisher, self).__init__(conf, session, node_name,
                                              node_opts)


class NotifyPublisher(Publisher):
    """Publisher class for notifications."""
    def __init__(self, conf, session, topic):
        """Init a 'topic' publisher.
        """
        exchange_name = rpc_amqp.get_control_exchange(conf)
        node_opts = {"durable": True}

        if conf.qpid_topology_version == 1:
            node_name = "%s/%s" % (exchange_name, topic)
        elif conf.qpid_topology_version == 2:
            node_name = "amq.topic/topic/%s/%s" % (exchange_name, topic)
        else:
            raise_invalid_topology_version()

        super(NotifyPublisher, self).__init__(conf, session, node_name,
                                              node_opts)


class Connection(object):
    """Connection object."""

    pool = None

    def __init__(self, conf, server_params=None):
        if not qpid_messaging:
            raise ImportError("Failed to import qpid.messaging")

        self.session = None
        self.consumers = {}
        self.consumer_thread = None
        self.proxy_callbacks = []
        self.conf = conf

        if server_params and 'hostname' in server_params:
            # NOTE(russellb) This enables support for cast_to_server.
            server_params['qpid_hosts'] = [
                '%s:%d' % (server_params['hostname'],
                           server_params.get('port', 5672))
            ]

        params = {
            'qpid_hosts': self.conf.qpid_hosts,
            'username': self.conf.qpid_username,
            'password': self.conf.qpid_password,
        }
        params.update(server_params or {})

        self.brokers = params['qpid_hosts']
        self.username = params['username']
        self.password = params['password']
        self.connection_create(self.brokers[0])
        self.reconnect()

    def connection_create(self, broker):
        # Create the connection - this does not open the connection
        self.connection = qpid_messaging.Connection(broker)

        # Check if flags are set and if so set them for the connection
        # before we call open
        self.connection.username = self.username
        self.connection.password = self.password

        self.connection.sasl_mechanisms = self.conf.qpid_sasl_mechanisms
        # Reconnection is done by self.reconnect()
        self.connection.reconnect = False
        self.connection.heartbeat = self.conf.qpid_heartbeat
        self.connection.transport = self.conf.qpid_protocol
        self.connection.tcp_nodelay = self.conf.qpid_tcp_nodelay

    def _register_consumer(self, consumer):
        self.consumers[str(consumer.get_receiver())] = consumer

    def _lookup_consumer(self, receiver):
        return self.consumers[str(receiver)]

    def reconnect(self):
        """Handles reconnecting and re-establishing sessions and queues."""
        attempt = 0
        delay = 1
        while True:
            # Close the session if necessary
            if self.connection.opened():
                try:
                    self.connection.close()
                except qpid_exceptions.ConnectionError:
                    pass

            broker = self.brokers[attempt % len(self.brokers)]
            attempt += 1

            try:
                self.connection_create(broker)
                self.connection.open()
            except qpid_exceptions.ConnectionError as e:
                msg_dict = dict(e=e, delay=delay)
                msg = _("Unable to connect to AMQP server: %(e)s. "
                        "Sleeping %(delay)s seconds") % msg_dict
                LOG.error(msg)
                time.sleep(delay)
                delay = min(2 * delay, 60)
            else:
                LOG.info(_('Connected to AMQP server on %s'), broker)
                break

        self.session = self.connection.session()

        if self.consumers:
            consumers = self.consumers
            self.consumers = {}

            for consumer in six.itervalues(consumers):
                consumer.reconnect(self.session)
                self._register_consumer(consumer)

            LOG.debug(_("Re-established AMQP queues"))

    def ensure(self, error_callback, method, *args, **kwargs):
        while True:
            try:
                return method(*args, **kwargs)
            except (qpid_exceptions.Empty,
                    qpid_exceptions.ConnectionError) as e:
                if error_callback:
                    error_callback(e)
                self.reconnect()

    def close(self):
        """Close/release this connection."""
        self.cancel_consumer_thread()
        self.wait_on_proxy_callbacks()
        try:
            self.connection.close()
        except Exception:
            # NOTE(dripton) Logging exceptions that happen during cleanup just
            # causes confusion; there's really nothing useful we can do with
            # them.
            pass
        self.connection = None

    def reset(self):
        """Reset a connection so it can be used again."""
        self.cancel_consumer_thread()
        self.wait_on_proxy_callbacks()
        self.session.close()
        self.session = self.connection.session()
        self.consumers = {}

    def declare_consumer(self, consumer_cls, topic, callback):
        """Create a Consumer using the class that was passed in and
        add it to our list of consumers
        """
        def _connect_error(exc):
            log_info = {'topic': topic, 'err_str': str(exc)}
            LOG.error(_("Failed to declare consumer for topic '%(topic)s': "
                      "%(err_str)s") % log_info)

        def _declare_consumer():
            consumer = consumer_cls(self.conf, self.session, topic, callback)
            self._register_consumer(consumer)
            return consumer

        return self.ensure(_connect_error, _declare_consumer)

    def iterconsume(self, limit=None, timeout=None):
        """Return an iterator that will consume from all queues/consumers."""

        def _error_callback(exc):
            if isinstance(exc, qpid_exceptions.Empty):
                LOG.debug(_('Timed out waiting for RPC response: %s') %
                          str(exc))
                raise rpc_common.Timeout()
            else:
                LOG.exception(_('Failed to consume message from queue: %s') %
                              str(exc))

        def _consume():
            nxt_receiver = self.session.next_receiver(timeout=timeout)
            try:
                self._lookup_consumer(nxt_receiver).consume()
            except Exception:
                LOG.exception(_("Error processing message.  Skipping it."))

        for iteration in itertools.count(0):
            if limit and iteration >= limit:
                raise StopIteration
            yield self.ensure(_error_callback, _consume)

    def cancel_consumer_thread(self):
        """Cancel a consumer thread."""
        if self.consumer_thread is not None:
            self.consumer_thread.kill()
            try:
                self.consumer_thread.wait()
            except greenlet.GreenletExit:
                pass
            self.consumer_thread = None

    def wait_on_proxy_callbacks(self):
        """Wait for all proxy callback threads to exit."""
        for proxy_cb in self.proxy_callbacks:
            proxy_cb.wait()

    def publisher_send(self, cls, topic, msg):
        """Send to a publisher based on the publisher class."""

        def _connect_error(exc):
            log_info = {'topic': topic, 'err_str': str(exc)}
            LOG.exception(_("Failed to publish message to topic "
                          "'%(topic)s': %(err_str)s") % log_info)

        def _publisher_send():
            publisher = cls(self.conf, self.session, topic)
            publisher.send(msg)

        return self.ensure(_connect_error, _publisher_send)

    def declare_direct_consumer(self, topic, callback):
        """Create a 'direct' queue.
        In nova's use, this is generally a msg_id queue used for
        responses for call/multicall
        """
        self.declare_consumer(DirectConsumer, topic, callback)

    def declare_topic_consumer(self, topic, callback=None, queue_name=None,
                               exchange_name=None):
        """Create a 'topic' consumer."""
        self.declare_consumer(functools.partial(TopicConsumer,
                                                name=queue_name,
                                                exchange_name=exchange_name,
                                                ),
                              topic, callback)

    def declare_fanout_consumer(self, topic, callback):
        """Create a 'fanout' consumer."""
        self.declare_consumer(FanoutConsumer, topic, callback)

    def direct_send(self, msg_id, msg):
        """Send a 'direct' message."""
        self.publisher_send(DirectPublisher, msg_id, msg)

    def topic_send(self, topic, msg, timeout=None):
        """Send a 'topic' message."""
        #
        # We want to create a message with attributes, e.g. a TTL. We
        # don't really need to keep 'msg' in its JSON format any longer
        # so let's create an actual qpid message here and get some
        # value-add on the go.
        #
        # WARNING: Request timeout happens to be in the same units as
        # qpid's TTL (seconds). If this changes in the future, then this
        # will need to be altered accordingly.
        #
        qpid_message = qpid_messaging.Message(content=msg, ttl=timeout)
        self.publisher_send(TopicPublisher, topic, qpid_message)

    def fanout_send(self, topic, msg):
        """Send a 'fanout' message."""
        self.publisher_send(FanoutPublisher, topic, msg)

    def notify_send(self, topic, msg, **kwargs):
        """Send a notify message on a topic."""
        self.publisher_send(NotifyPublisher, topic, msg)

    def consume(self, limit=None):
        """Consume from all queues/consumers."""
        it = self.iterconsume(limit=limit)
        while True:
            try:
                six.next(it)
            except StopIteration:
                return

    def consume_in_thread(self):
        """Consumer from all queues/consumers in a greenthread."""
        @excutils.forever_retry_uncaught_exceptions
        def _consumer_thread():
            try:
                self.consume()
            except greenlet.GreenletExit:
                return
        if self.consumer_thread is None:
            self.consumer_thread = eventlet.spawn(_consumer_thread)
        return self.consumer_thread

    def create_consumer(self, topic, proxy, fanout=False):
        """Create a consumer that calls a method in a proxy object."""
        proxy_cb = rpc_amqp.ProxyCallback(
            self.conf, proxy,
            rpc_amqp.get_connection_pool(self.conf, Connection))
        self.proxy_callbacks.append(proxy_cb)

        if fanout:
            consumer = FanoutConsumer(self.conf, self.session, topic, proxy_cb)
        else:
            consumer = TopicConsumer(self.conf, self.session, topic, proxy_cb)

        self._register_consumer(consumer)

        return consumer

    def create_worker(self, topic, proxy, pool_name):
        """Create a worker that calls a method in a proxy object."""
        proxy_cb = rpc_amqp.ProxyCallback(
            self.conf, proxy,
            rpc_amqp.get_connection_pool(self.conf, Connection))
        self.proxy_callbacks.append(proxy_cb)

        consumer = TopicConsumer(self.conf, self.session, topic, proxy_cb,
                                 name=pool_name)

        self._register_consumer(consumer)

        return consumer

    def join_consumer_pool(self, callback, pool_name, topic,
                           exchange_name=None, ack_on_error=True):
        """Register as a member of a group of consumers for a given topic from
        the specified exchange.

        Exactly one member of a given pool will receive each message.

        A message will be delivered to multiple pools, if more than
        one is created.
        """
        callback_wrapper = rpc_amqp.CallbackWrapper(
            conf=self.conf,
            callback=callback,
            connection_pool=rpc_amqp.get_connection_pool(self.conf,
                                                         Connection),
            wait_for_consumers=not ack_on_error
        )
        self.proxy_callbacks.append(callback_wrapper)

        consumer = TopicConsumer(conf=self.conf,
                                 session=self.session,
                                 topic=topic,
                                 callback=callback_wrapper,
                                 name=pool_name,
                                 exchange_name=exchange_name)

        self._register_consumer(consumer)
        return consumer


def create_connection(conf, new=True):
    """Create a connection."""
    return rpc_amqp.create_connection(
        conf, new,
        rpc_amqp.get_connection_pool(conf, Connection))


def multicall(conf, context, topic, msg, timeout=None):
    """Make a call that returns multiple times."""
    return rpc_amqp.multicall(
        conf, context, topic, msg, timeout,
        rpc_amqp.get_connection_pool(conf, Connection))


def call(conf, context, topic, msg, timeout=None):
    """Sends a message on a topic and wait for a response."""
    return rpc_amqp.call(
        conf, context, topic, msg, timeout,
        rpc_amqp.get_connection_pool(conf, Connection))


def cast(conf, context, topic, msg):
    """Sends a message on a topic without waiting for a response."""
    return rpc_amqp.cast(
        conf, context, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def fanout_cast(conf, context, topic, msg):
    """Sends a message on a fanout exchange without waiting for a response."""
    return rpc_amqp.fanout_cast(
        conf, context, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def cast_to_server(conf, context, server_params, topic, msg):
    """Sends a message on a topic to a specific server."""
    return rpc_amqp.cast_to_server(
        conf, context, server_params, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def fanout_cast_to_server(conf, context, server_params, topic, msg):
    """Sends a message on a fanout exchange to a specific server."""
    return rpc_amqp.fanout_cast_to_server(
        conf, context, server_params, topic, msg,
        rpc_amqp.get_connection_pool(conf, Connection))


def notify(conf, context, topic, msg, envelope):
    """Sends a notification event on a topic."""
    return rpc_amqp.notify(conf, context, topic, msg,
                           rpc_amqp.get_connection_pool(conf, Connection),
                           envelope)


def cleanup():
    return rpc_amqp.cleanup(Connection.pool)

########NEW FILE########
__FILENAME__ = impl_zmq
#    Copyright 2011 Cloudscaling Group, Inc
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
import pprint
import re
import socket
import sys
import types
import uuid

import eventlet
import greenlet
from oslo.config import cfg
import six
from six import moves

from cloudbaseinit.openstack.common import excutils
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import jsonutils
from cloudbaseinit.openstack.common.rpc import common as rpc_common

zmq = importutils.try_import('eventlet.green.zmq')

# for convenience, are not modified.
pformat = pprint.pformat
Timeout = eventlet.timeout.Timeout
LOG = rpc_common.LOG
RemoteError = rpc_common.RemoteError
RPCException = rpc_common.RPCException

zmq_opts = [
    cfg.StrOpt('rpc_zmq_bind_address', default='*',
               help='ZeroMQ bind address. Should be a wildcard (*), '
                    'an ethernet interface, or IP. '
                    'The "host" option should point or resolve to this '
                    'address.'),

    # The module.Class to use for matchmaking.
    cfg.StrOpt(
        'rpc_zmq_matchmaker',
        default=('cloudbaseinit.openstack.common.rpc.'
                 'matchmaker.MatchMakerLocalhost'),
        help='MatchMaker driver',
    ),

    # The following port is unassigned by IANA as of 2012-05-21
    cfg.IntOpt('rpc_zmq_port', default=9501,
               help='ZeroMQ receiver listening port'),

    cfg.IntOpt('rpc_zmq_contexts', default=1,
               help='Number of ZeroMQ contexts, defaults to 1'),

    cfg.IntOpt('rpc_zmq_topic_backlog', default=None,
               help='Maximum number of ingress messages to locally buffer '
                    'per topic. Default is unlimited.'),

    cfg.StrOpt('rpc_zmq_ipc_dir', default='/var/run/openstack',
               help='Directory for holding IPC sockets'),

    cfg.StrOpt('rpc_zmq_host', default=socket.gethostname(),
               help='Name of this node. Must be a valid hostname, FQDN, or '
                    'IP address. Must match "host" option, if running Nova.')
]


CONF = cfg.CONF
CONF.register_opts(zmq_opts)

ZMQ_CTX = None  # ZeroMQ Context, must be global.
matchmaker = None  # memorized matchmaker object


def _serialize(data):
    """Serialization wrapper.

    We prefer using JSON, but it cannot encode all types.
    Error if a developer passes us bad data.
    """
    try:
        return jsonutils.dumps(data, ensure_ascii=True)
    except TypeError:
        with excutils.save_and_reraise_exception():
            LOG.error(_("JSON serialization failed."))


def _deserialize(data):
    """Deserialization wrapper."""
    LOG.debug(_("Deserializing: %s"), data)
    return jsonutils.loads(data)


class ZmqSocket(object):
    """A tiny wrapper around ZeroMQ.

    Simplifies the send/recv protocol and connection management.
    Can be used as a Context (supports the 'with' statement).
    """

    def __init__(self, addr, zmq_type, bind=True, subscribe=None):
        self.sock = _get_ctxt().socket(zmq_type)
        self.addr = addr
        self.type = zmq_type
        self.subscriptions = []

        # Support failures on sending/receiving on wrong socket type.
        self.can_recv = zmq_type in (zmq.PULL, zmq.SUB)
        self.can_send = zmq_type in (zmq.PUSH, zmq.PUB)
        self.can_sub = zmq_type in (zmq.SUB, )

        # Support list, str, & None for subscribe arg (cast to list)
        do_sub = {
            list: subscribe,
            str: [subscribe],
            type(None): []
        }[type(subscribe)]

        for f in do_sub:
            self.subscribe(f)

        str_data = {'addr': addr, 'type': self.socket_s(),
                    'subscribe': subscribe, 'bind': bind}

        LOG.debug(_("Connecting to %(addr)s with %(type)s"), str_data)
        LOG.debug(_("-> Subscribed to %(subscribe)s"), str_data)
        LOG.debug(_("-> bind: %(bind)s"), str_data)

        try:
            if bind:
                self.sock.bind(addr)
            else:
                self.sock.connect(addr)
        except Exception:
            raise RPCException(_("Could not open socket."))

    def socket_s(self):
        """Get socket type as string."""
        t_enum = ('PUSH', 'PULL', 'PUB', 'SUB', 'REP', 'REQ', 'ROUTER',
                  'DEALER')
        return dict(map(lambda t: (getattr(zmq, t), t), t_enum))[self.type]

    def subscribe(self, msg_filter):
        """Subscribe."""
        if not self.can_sub:
            raise RPCException("Cannot subscribe on this socket.")
        LOG.debug(_("Subscribing to %s"), msg_filter)

        try:
            self.sock.setsockopt(zmq.SUBSCRIBE, msg_filter)
        except Exception:
            return

        self.subscriptions.append(msg_filter)

    def unsubscribe(self, msg_filter):
        """Unsubscribe."""
        if msg_filter not in self.subscriptions:
            return
        self.sock.setsockopt(zmq.UNSUBSCRIBE, msg_filter)
        self.subscriptions.remove(msg_filter)

    def close(self):
        if self.sock is None or self.sock.closed:
            return

        # We must unsubscribe, or we'll leak descriptors.
        if self.subscriptions:
            for f in self.subscriptions:
                try:
                    self.sock.setsockopt(zmq.UNSUBSCRIBE, f)
                except Exception:
                    pass
            self.subscriptions = []

        try:
            # Default is to linger
            self.sock.close()
        except Exception:
            # While this is a bad thing to happen,
            # it would be much worse if some of the code calling this
            # were to fail. For now, lets log, and later evaluate
            # if we can safely raise here.
            LOG.error(_("ZeroMQ socket could not be closed."))
        self.sock = None

    def recv(self, **kwargs):
        if not self.can_recv:
            raise RPCException(_("You cannot recv on this socket."))
        return self.sock.recv_multipart(**kwargs)

    def send(self, data, **kwargs):
        if not self.can_send:
            raise RPCException(_("You cannot send on this socket."))
        self.sock.send_multipart(data, **kwargs)


class ZmqClient(object):
    """Client for ZMQ sockets."""

    def __init__(self, addr):
        self.outq = ZmqSocket(addr, zmq.PUSH, bind=False)

    def cast(self, msg_id, topic, data, envelope):
        msg_id = msg_id or 0

        if not envelope:
            self.outq.send(map(bytes,
                           (msg_id, topic, 'cast', _serialize(data))))
            return

        rpc_envelope = rpc_common.serialize_msg(data[1], envelope)
        zmq_msg = moves.reduce(lambda x, y: x + y, rpc_envelope.items())
        self.outq.send(map(bytes,
                       (msg_id, topic, 'impl_zmq_v2', data[0]) + zmq_msg))

    def close(self):
        self.outq.close()


class RpcContext(rpc_common.CommonRpcContext):
    """Context that supports replying to a rpc.call."""
    def __init__(self, **kwargs):
        self.replies = []
        super(RpcContext, self).__init__(**kwargs)

    def deepcopy(self):
        values = self.to_dict()
        values['replies'] = self.replies
        return self.__class__(**values)

    def reply(self, reply=None, failure=None, ending=False):
        if ending:
            return
        self.replies.append(reply)

    @classmethod
    def marshal(self, ctx):
        ctx_data = ctx.to_dict()
        return _serialize(ctx_data)

    @classmethod
    def unmarshal(self, data):
        return RpcContext.from_dict(_deserialize(data))


class InternalContext(object):
    """Used by ConsumerBase as a private context for - methods."""

    def __init__(self, proxy):
        self.proxy = proxy
        self.msg_waiter = None

    def _get_response(self, ctx, proxy, topic, data):
        """Process a curried message and cast the result to topic."""
        LOG.debug(_("Running func with context: %s"), ctx.to_dict())
        data.setdefault('version', None)
        data.setdefault('args', {})

        try:
            result = proxy.dispatch(
                ctx, data['version'], data['method'],
                data.get('namespace'), **data['args'])
            return ConsumerBase.normalize_reply(result, ctx.replies)
        except greenlet.GreenletExit:
            # ignore these since they are just from shutdowns
            pass
        except rpc_common.ClientException as e:
            LOG.debug(_("Expected exception during message handling (%s)") %
                      e._exc_info[1])
            return {'exc':
                    rpc_common.serialize_remote_exception(e._exc_info,
                                                          log_failure=False)}
        except Exception:
            LOG.error(_("Exception during message handling"))
            return {'exc':
                    rpc_common.serialize_remote_exception(sys.exc_info())}

    def reply(self, ctx, proxy,
              msg_id=None, context=None, topic=None, msg=None):
        """Reply to a casted call."""
        # NOTE(ewindisch): context kwarg exists for Grizzly compat.
        #                  this may be able to be removed earlier than
        #                  'I' if ConsumerBase.process were refactored.
        if type(msg) is list:
            payload = msg[-1]
        else:
            payload = msg

        response = ConsumerBase.normalize_reply(
            self._get_response(ctx, proxy, topic, payload),
            ctx.replies)

        LOG.debug(_("Sending reply"))
        _multi_send(_cast, ctx, topic, {
            'method': '-process_reply',
            'args': {
                'msg_id': msg_id,  # Include for Folsom compat.
                'response': response
            }
        }, _msg_id=msg_id)


class ConsumerBase(object):
    """Base Consumer."""

    def __init__(self):
        self.private_ctx = InternalContext(None)

    @classmethod
    def normalize_reply(self, result, replies):
        #TODO(ewindisch): re-evaluate and document this method.
        if isinstance(result, types.GeneratorType):
            return list(result)
        elif replies:
            return replies
        else:
            return [result]

    def process(self, proxy, ctx, data):
        data.setdefault('version', None)
        data.setdefault('args', {})

        # Method starting with - are
        # processed internally. (non-valid method name)
        method = data.get('method')
        if not method:
            LOG.error(_("RPC message did not include method."))
            return

        # Internal method
        # uses internal context for safety.
        if method == '-reply':
            self.private_ctx.reply(ctx, proxy, **data['args'])
            return

        proxy.dispatch(ctx, data['version'],
                       data['method'], data.get('namespace'), **data['args'])


class ZmqBaseReactor(ConsumerBase):
    """A consumer class implementing a centralized casting broker (PULL-PUSH).

    Used for RoundRobin requests.
    """

    def __init__(self, conf):
        super(ZmqBaseReactor, self).__init__()

        self.proxies = {}
        self.threads = []
        self.sockets = []
        self.subscribe = {}

        self.pool = eventlet.greenpool.GreenPool(conf.rpc_thread_pool_size)

    def register(self, proxy, in_addr, zmq_type_in,
                 in_bind=True, subscribe=None):

        LOG.info(_("Registering reactor"))

        if zmq_type_in not in (zmq.PULL, zmq.SUB):
            raise RPCException("Bad input socktype")

        # Items push in.
        inq = ZmqSocket(in_addr, zmq_type_in, bind=in_bind,
                        subscribe=subscribe)

        self.proxies[inq] = proxy
        self.sockets.append(inq)

        LOG.info(_("In reactor registered"))

    def consume_in_thread(self):
        @excutils.forever_retry_uncaught_exceptions
        def _consume(sock):
            LOG.info(_("Consuming socket"))
            while True:
                self.consume(sock)

        for k in self.proxies.keys():
            self.threads.append(
                self.pool.spawn(_consume, k)
            )

    def wait(self):
        for t in self.threads:
            t.wait()

    def close(self):
        for s in self.sockets:
            s.close()

        for t in self.threads:
            t.kill()


class ZmqProxy(ZmqBaseReactor):
    """A consumer class implementing a topic-based proxy.

    Forwards to IPC sockets.
    """

    def __init__(self, conf):
        super(ZmqProxy, self).__init__(conf)
        pathsep = set((os.path.sep or '', os.path.altsep or '', '/', '\\'))
        self.badchars = re.compile(r'[%s]' % re.escape(''.join(pathsep)))

        self.topic_proxy = {}

    def consume(self, sock):
        ipc_dir = CONF.rpc_zmq_ipc_dir

        data = sock.recv(copy=False)
        topic = data[1].bytes

        if topic.startswith('fanout~'):
            sock_type = zmq.PUB
            topic = topic.split('.', 1)[0]
        elif topic.startswith('zmq_replies'):
            sock_type = zmq.PUB
        else:
            sock_type = zmq.PUSH

        if topic not in self.topic_proxy:
            def publisher(waiter):
                LOG.info(_("Creating proxy for topic: %s"), topic)

                try:
                    # The topic is received over the network,
                    # don't trust this input.
                    if self.badchars.search(topic) is not None:
                        emsg = _("Topic contained dangerous characters.")
                        LOG.warn(emsg)
                        raise RPCException(emsg)

                    out_sock = ZmqSocket("ipc://%s/zmq_topic_%s" %
                                         (ipc_dir, topic),
                                         sock_type, bind=True)
                except RPCException:
                    waiter.send_exception(*sys.exc_info())
                    return

                self.topic_proxy[topic] = eventlet.queue.LightQueue(
                    CONF.rpc_zmq_topic_backlog)
                self.sockets.append(out_sock)

                # It takes some time for a pub socket to open,
                # before we can have any faith in doing a send() to it.
                if sock_type == zmq.PUB:
                    eventlet.sleep(.5)

                waiter.send(True)

                while(True):
                    data = self.topic_proxy[topic].get()
                    out_sock.send(data, copy=False)

            wait_sock_creation = eventlet.event.Event()
            eventlet.spawn(publisher, wait_sock_creation)

            try:
                wait_sock_creation.wait()
            except RPCException:
                LOG.error(_("Topic socket file creation failed."))
                return

        try:
            self.topic_proxy[topic].put_nowait(data)
        except eventlet.queue.Full:
            LOG.error(_("Local per-topic backlog buffer full for topic "
                        "%(topic)s. Dropping message.") % {'topic': topic})

    def consume_in_thread(self):
        """Runs the ZmqProxy service."""
        ipc_dir = CONF.rpc_zmq_ipc_dir
        consume_in = "tcp://%s:%s" % \
            (CONF.rpc_zmq_bind_address,
             CONF.rpc_zmq_port)
        consumption_proxy = InternalContext(None)

        try:
            os.makedirs(ipc_dir)
        except os.error:
            if not os.path.isdir(ipc_dir):
                with excutils.save_and_reraise_exception():
                    LOG.error(_("Required IPC directory does not exist at"
                                " %s") % (ipc_dir, ))
        try:
            self.register(consumption_proxy,
                          consume_in,
                          zmq.PULL)
        except zmq.ZMQError:
            if os.access(ipc_dir, os.X_OK):
                with excutils.save_and_reraise_exception():
                    LOG.error(_("Permission denied to IPC directory at"
                                " %s") % (ipc_dir, ))
            with excutils.save_and_reraise_exception():
                LOG.error(_("Could not create ZeroMQ receiver daemon. "
                            "Socket may already be in use."))

        super(ZmqProxy, self).consume_in_thread()


def unflatten_envelope(packenv):
    """Unflattens the RPC envelope.

    Takes a list and returns a dictionary.
    i.e. [1,2,3,4] => {1: 2, 3: 4}
    """
    i = iter(packenv)
    h = {}
    try:
        while True:
            k = six.next(i)
            h[k] = six.next(i)
    except StopIteration:
        return h


class ZmqReactor(ZmqBaseReactor):
    """A consumer class implementing a consumer for messages.

    Can also be used as a 1:1 proxy
    """

    def __init__(self, conf):
        super(ZmqReactor, self).__init__(conf)

    def consume(self, sock):
        #TODO(ewindisch): use zero-copy (i.e. references, not copying)
        data = sock.recv()
        LOG.debug(_("CONSUMER RECEIVED DATA: %s"), data)

        proxy = self.proxies[sock]

        if data[2] == 'cast':  # Legacy protocol
            packenv = data[3]

            ctx, msg = _deserialize(packenv)
            request = rpc_common.deserialize_msg(msg)
            ctx = RpcContext.unmarshal(ctx)
        elif data[2] == 'impl_zmq_v2':
            packenv = data[4:]

            msg = unflatten_envelope(packenv)
            request = rpc_common.deserialize_msg(msg)

            # Unmarshal only after verifying the message.
            ctx = RpcContext.unmarshal(data[3])
        else:
            LOG.error(_("ZMQ Envelope version unsupported or unknown."))
            return

        self.pool.spawn_n(self.process, proxy, ctx, request)


class Connection(rpc_common.Connection):
    """Manages connections and threads."""

    def __init__(self, conf):
        self.topics = []
        self.reactor = ZmqReactor(conf)

    def create_consumer(self, topic, proxy, fanout=False):
        # Register with matchmaker.
        _get_matchmaker().register(topic, CONF.rpc_zmq_host)

        # Subscription scenarios
        if fanout:
            sock_type = zmq.SUB
            subscribe = ('', fanout)[type(fanout) == str]
            topic = 'fanout~' + topic.split('.', 1)[0]
        else:
            sock_type = zmq.PULL
            subscribe = None
            topic = '.'.join((topic.split('.', 1)[0], CONF.rpc_zmq_host))

        if topic in self.topics:
            LOG.info(_("Skipping topic registration. Already registered."))
            return

        # Receive messages from (local) proxy
        inaddr = "ipc://%s/zmq_topic_%s" % \
            (CONF.rpc_zmq_ipc_dir, topic)

        LOG.debug(_("Consumer is a zmq.%s"),
                  ['PULL', 'SUB'][sock_type == zmq.SUB])

        self.reactor.register(proxy, inaddr, sock_type,
                              subscribe=subscribe, in_bind=False)
        self.topics.append(topic)

    def close(self):
        _get_matchmaker().stop_heartbeat()
        for topic in self.topics:
            _get_matchmaker().unregister(topic, CONF.rpc_zmq_host)

        self.reactor.close()
        self.topics = []

    def wait(self):
        self.reactor.wait()

    def consume_in_thread(self):
        _get_matchmaker().start_heartbeat()
        self.reactor.consume_in_thread()


def _cast(addr, context, topic, msg, timeout=None, envelope=False,
          _msg_id=None):
    timeout_cast = timeout or CONF.rpc_cast_timeout
    payload = [RpcContext.marshal(context), msg]

    with Timeout(timeout_cast, exception=rpc_common.Timeout):
        try:
            conn = ZmqClient(addr)

            # assumes cast can't return an exception
            conn.cast(_msg_id, topic, payload, envelope)
        except zmq.ZMQError:
            raise RPCException("Cast failed. ZMQ Socket Exception")
        finally:
            if 'conn' in vars():
                conn.close()


def _call(addr, context, topic, msg, timeout=None,
          envelope=False):
    # timeout_response is how long we wait for a response
    timeout = timeout or CONF.rpc_response_timeout

    # The msg_id is used to track replies.
    msg_id = uuid.uuid4().hex

    # Replies always come into the reply service.
    reply_topic = "zmq_replies.%s" % CONF.rpc_zmq_host

    LOG.debug(_("Creating payload"))
    # Curry the original request into a reply method.
    mcontext = RpcContext.marshal(context)
    payload = {
        'method': '-reply',
        'args': {
            'msg_id': msg_id,
            'topic': reply_topic,
            # TODO(ewindisch): safe to remove mcontext in I.
            'msg': [mcontext, msg]
        }
    }

    LOG.debug(_("Creating queue socket for reply waiter"))

    # Messages arriving async.
    # TODO(ewindisch): have reply consumer with dynamic subscription mgmt
    with Timeout(timeout, exception=rpc_common.Timeout):
        try:
            msg_waiter = ZmqSocket(
                "ipc://%s/zmq_topic_zmq_replies.%s" %
                (CONF.rpc_zmq_ipc_dir,
                 CONF.rpc_zmq_host),
                zmq.SUB, subscribe=msg_id, bind=False
            )

            LOG.debug(_("Sending cast"))
            _cast(addr, context, topic, payload, envelope)

            LOG.debug(_("Cast sent; Waiting reply"))
            # Blocks until receives reply
            msg = msg_waiter.recv()
            LOG.debug(_("Received message: %s"), msg)
            LOG.debug(_("Unpacking response"))

            if msg[2] == 'cast':  # Legacy version
                raw_msg = _deserialize(msg[-1])[-1]
            elif msg[2] == 'impl_zmq_v2':
                rpc_envelope = unflatten_envelope(msg[4:])
                raw_msg = rpc_common.deserialize_msg(rpc_envelope)
            else:
                raise rpc_common.UnsupportedRpcEnvelopeVersion(
                    _("Unsupported or unknown ZMQ envelope returned."))

            responses = raw_msg['args']['response']
        # ZMQError trumps the Timeout error.
        except zmq.ZMQError:
            raise RPCException("ZMQ Socket Error")
        except (IndexError, KeyError):
            raise RPCException(_("RPC Message Invalid."))
        finally:
            if 'msg_waiter' in vars():
                msg_waiter.close()

    # It seems we don't need to do all of the following,
    # but perhaps it would be useful for multicall?
    # One effect of this is that we're checking all
    # responses for Exceptions.
    for resp in responses:
        if isinstance(resp, types.DictType) and 'exc' in resp:
            raise rpc_common.deserialize_remote_exception(CONF, resp['exc'])

    return responses[-1]


def _multi_send(method, context, topic, msg, timeout=None,
                envelope=False, _msg_id=None):
    """Wraps the sending of messages.

    Dispatches to the matchmaker and sends message to all relevant hosts.
    """
    conf = CONF
    LOG.debug(_("%(msg)s") % {'msg': ' '.join(map(pformat, (topic, msg)))})

    queues = _get_matchmaker().queues(topic)
    LOG.debug(_("Sending message(s) to: %s"), queues)

    # Don't stack if we have no matchmaker results
    if not queues:
        LOG.warn(_("No matchmaker results. Not casting."))
        # While not strictly a timeout, callers know how to handle
        # this exception and a timeout isn't too big a lie.
        raise rpc_common.Timeout(_("No match from matchmaker."))

    # This supports brokerless fanout (addresses > 1)
    for queue in queues:
        (_topic, ip_addr) = queue
        _addr = "tcp://%s:%s" % (ip_addr, conf.rpc_zmq_port)

        if method.__name__ == '_cast':
            eventlet.spawn_n(method, _addr, context,
                             _topic, msg, timeout, envelope,
                             _msg_id)
            return
        return method(_addr, context, _topic, msg, timeout,
                      envelope)


def create_connection(conf, new=True):
    return Connection(conf)


def multicall(conf, *args, **kwargs):
    """Multiple calls."""
    return _multi_send(_call, *args, **kwargs)


def call(conf, *args, **kwargs):
    """Send a message, expect a response."""
    data = _multi_send(_call, *args, **kwargs)
    return data[-1]


def cast(conf, *args, **kwargs):
    """Send a message expecting no reply."""
    _multi_send(_cast, *args, **kwargs)


def fanout_cast(conf, context, topic, msg, **kwargs):
    """Send a message to all listening and expect no reply."""
    # NOTE(ewindisch): fanout~ is used because it avoid splitting on .
    # and acts as a non-subtle hint to the matchmaker and ZmqProxy.
    _multi_send(_cast, context, 'fanout~' + str(topic), msg, **kwargs)


def notify(conf, context, topic, msg, envelope):
    """Send notification event.

    Notifications are sent to topic-priority.
    This differs from the AMQP drivers which send to topic.priority.
    """
    # NOTE(ewindisch): dot-priority in rpc notifier does not
    # work with our assumptions.
    topic = topic.replace('.', '-')
    cast(conf, context, topic, msg, envelope=envelope)


def cleanup():
    """Clean up resources in use by implementation."""
    global ZMQ_CTX
    if ZMQ_CTX:
        ZMQ_CTX.term()
    ZMQ_CTX = None

    global matchmaker
    matchmaker = None


def _get_ctxt():
    if not zmq:
        raise ImportError("Failed to import eventlet.green.zmq")

    global ZMQ_CTX
    if not ZMQ_CTX:
        ZMQ_CTX = zmq.Context(CONF.rpc_zmq_contexts)
    return ZMQ_CTX


def _get_matchmaker(*args, **kwargs):
    global matchmaker
    if not matchmaker:
        mm = CONF.rpc_zmq_matchmaker
        if mm.endswith('matchmaker.MatchMakerRing'):
            mm.replace('matchmaker', 'matchmaker_ring')
            LOG.warn(_('rpc_zmq_matchmaker = %(orig)s is deprecated; use'
                       ' %(new)s instead') % dict(
                     orig=CONF.rpc_zmq_matchmaker, new=mm))
        matchmaker = importutils.import_object(mm, *args, **kwargs)
    return matchmaker

########NEW FILE########
__FILENAME__ = matchmaker
#    Copyright 2011 Cloudscaling Group, Inc
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
The MatchMaker classes should except a Topic or Fanout exchange key and
return keys for direct exchanges, per (approximate) AMQP parlance.
"""

import contextlib

import eventlet
from oslo.config import cfg

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging


matchmaker_opts = [
    cfg.IntOpt('matchmaker_heartbeat_freq',
               default=300,
               help='Heartbeat frequency'),
    cfg.IntOpt('matchmaker_heartbeat_ttl',
               default=600,
               help='Heartbeat time-to-live.'),
]

CONF = cfg.CONF
CONF.register_opts(matchmaker_opts)
LOG = logging.getLogger(__name__)
contextmanager = contextlib.contextmanager


class MatchMakerException(Exception):
    """Signified a match could not be found."""
    message = _("Match not found by MatchMaker.")


class Exchange(object):
    """Implements lookups.

    Subclass this to support hashtables, dns, etc.
    """
    def __init__(self):
        pass

    def run(self, key):
        raise NotImplementedError()


class Binding(object):
    """A binding on which to perform a lookup."""
    def __init__(self):
        pass

    def test(self, key):
        raise NotImplementedError()


class MatchMakerBase(object):
    """Match Maker Base Class.

    Build off HeartbeatMatchMakerBase if building a heartbeat-capable
    MatchMaker.
    """
    def __init__(self):
        # Array of tuples. Index [2] toggles negation, [3] is last-if-true
        self.bindings = []

        self.no_heartbeat_msg = _('Matchmaker does not implement '
                                  'registration or heartbeat.')

    def register(self, key, host):
        """Register a host on a backend.

        Heartbeats, if applicable, may keepalive registration.
        """
        pass

    def ack_alive(self, key, host):
        """Acknowledge that a key.host is alive.

        Used internally for updating heartbeats, but may also be used
        publicly to acknowledge a system is alive (i.e. rpc message
        successfully sent to host)
        """
        pass

    def is_alive(self, topic, host):
        """Checks if a host is alive."""
        pass

    def expire(self, topic, host):
        """Explicitly expire a host's registration."""
        pass

    def send_heartbeats(self):
        """Send all heartbeats.

        Use start_heartbeat to spawn a heartbeat greenthread,
        which loops this method.
        """
        pass

    def unregister(self, key, host):
        """Unregister a topic."""
        pass

    def start_heartbeat(self):
        """Spawn heartbeat greenthread."""
        pass

    def stop_heartbeat(self):
        """Destroys the heartbeat greenthread."""
        pass

    def add_binding(self, binding, rule, last=True):
        self.bindings.append((binding, rule, False, last))

    #NOTE(ewindisch): kept the following method in case we implement the
    #                 underlying support.
    #def add_negate_binding(self, binding, rule, last=True):
    #    self.bindings.append((binding, rule, True, last))

    def queues(self, key):
        workers = []

        # bit is for negate bindings - if we choose to implement it.
        # last stops processing rules if this matches.
        for (binding, exchange, bit, last) in self.bindings:
            if binding.test(key):
                workers.extend(exchange.run(key))

                # Support last.
                if last:
                    return workers
        return workers


class HeartbeatMatchMakerBase(MatchMakerBase):
    """Base for a heart-beat capable MatchMaker.

    Provides common methods for registering, unregistering, and maintaining
    heartbeats.
    """
    def __init__(self):
        self.hosts = set()
        self._heart = None
        self.host_topic = {}

        super(HeartbeatMatchMakerBase, self).__init__()

    def send_heartbeats(self):
        """Send all heartbeats.

        Use start_heartbeat to spawn a heartbeat greenthread,
        which loops this method.
        """
        for key, host in self.host_topic:
            self.ack_alive(key, host)

    def ack_alive(self, key, host):
        """Acknowledge that a host.topic is alive.

        Used internally for updating heartbeats, but may also be used
        publicly to acknowledge a system is alive (i.e. rpc message
        successfully sent to host)
        """
        raise NotImplementedError("Must implement ack_alive")

    def backend_register(self, key, host):
        """Implements registration logic.

        Called by register(self,key,host)
        """
        raise NotImplementedError("Must implement backend_register")

    def backend_unregister(self, key, key_host):
        """Implements de-registration logic.

        Called by unregister(self,key,host)
        """
        raise NotImplementedError("Must implement backend_unregister")

    def register(self, key, host):
        """Register a host on a backend.

        Heartbeats, if applicable, may keepalive registration.
        """
        self.hosts.add(host)
        self.host_topic[(key, host)] = host
        key_host = '.'.join((key, host))

        self.backend_register(key, key_host)

        self.ack_alive(key, host)

    def unregister(self, key, host):
        """Unregister a topic."""
        if (key, host) in self.host_topic:
            del self.host_topic[(key, host)]

        self.hosts.discard(host)
        self.backend_unregister(key, '.'.join((key, host)))

        LOG.info(_("Matchmaker unregistered: %(key)s, %(host)s"),
                 {'key': key, 'host': host})

    def start_heartbeat(self):
        """Implementation of MatchMakerBase.start_heartbeat.

        Launches greenthread looping send_heartbeats(),
        yielding for CONF.matchmaker_heartbeat_freq seconds
        between iterations.
        """
        if not self.hosts:
            raise MatchMakerException(
                _("Register before starting heartbeat."))

        def do_heartbeat():
            while True:
                self.send_heartbeats()
                eventlet.sleep(CONF.matchmaker_heartbeat_freq)

        self._heart = eventlet.spawn(do_heartbeat)

    def stop_heartbeat(self):
        """Destroys the heartbeat greenthread."""
        if self._heart:
            self._heart.kill()


class DirectBinding(Binding):
    """Specifies a host in the key via a '.' character.

    Although dots are used in the key, the behavior here is
    that it maps directly to a host, thus direct.
    """
    def test(self, key):
        return '.' in key


class TopicBinding(Binding):
    """Where a 'bare' key without dots.

    AMQP generally considers topic exchanges to be those *with* dots,
    but we deviate here in terminology as the behavior here matches
    that of a topic exchange (whereas where there are dots, behavior
    matches that of a direct exchange.
    """
    def test(self, key):
        return '.' not in key


class FanoutBinding(Binding):
    """Match on fanout keys, where key starts with 'fanout.' string."""
    def test(self, key):
        return key.startswith('fanout~')


class StubExchange(Exchange):
    """Exchange that does nothing."""
    def run(self, key):
        return [(key, None)]


class LocalhostExchange(Exchange):
    """Exchange where all direct topics are local."""
    def __init__(self, host='localhost'):
        self.host = host
        super(Exchange, self).__init__()

    def run(self, key):
        return [('.'.join((key.split('.')[0], self.host)), self.host)]


class DirectExchange(Exchange):
    """Exchange where all topic keys are split, sending to second half.

    i.e. "compute.host" sends a message to "compute.host" running on "host"
    """
    def __init__(self):
        super(Exchange, self).__init__()

    def run(self, key):
        e = key.split('.', 1)[1]
        return [(key, e)]


class MatchMakerLocalhost(MatchMakerBase):
    """Match Maker where all bare topics resolve to localhost.

    Useful for testing.
    """
    def __init__(self, host='localhost'):
        super(MatchMakerLocalhost, self).__init__()
        self.add_binding(FanoutBinding(), LocalhostExchange(host))
        self.add_binding(DirectBinding(), DirectExchange())
        self.add_binding(TopicBinding(), LocalhostExchange(host))


class MatchMakerStub(MatchMakerBase):
    """Match Maker where topics are untouched.

    Useful for testing, or for AMQP/brokered queues.
    Will not work where knowledge of hosts is known (i.e. zeromq)
    """
    def __init__(self):
        super(MatchMakerStub, self).__init__()

        self.add_binding(FanoutBinding(), StubExchange())
        self.add_binding(DirectBinding(), StubExchange())
        self.add_binding(TopicBinding(), StubExchange())

########NEW FILE########
__FILENAME__ = matchmaker_redis
#    Copyright 2013 Cloudscaling Group, Inc
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
The MatchMaker classes should accept a Topic or Fanout exchange key and
return keys for direct exchanges, per (approximate) AMQP parlance.
"""

from oslo.config import cfg

from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common.rpc import matchmaker as mm_common

redis = importutils.try_import('redis')


matchmaker_redis_opts = [
    cfg.StrOpt('host',
               default='127.0.0.1',
               help='Host to locate redis'),
    cfg.IntOpt('port',
               default=6379,
               help='Use this port to connect to redis host.'),
    cfg.StrOpt('password',
               default=None,
               help='Password for Redis server. (optional)'),
]

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='matchmaker_redis',
                         title='Options for Redis-based MatchMaker')
CONF.register_group(opt_group)
CONF.register_opts(matchmaker_redis_opts, opt_group)
LOG = logging.getLogger(__name__)


class RedisExchange(mm_common.Exchange):
    def __init__(self, matchmaker):
        self.matchmaker = matchmaker
        self.redis = matchmaker.redis
        super(RedisExchange, self).__init__()


class RedisTopicExchange(RedisExchange):
    """Exchange where all topic keys are split, sending to second half.

    i.e. "compute.host" sends a message to "compute" running on "host"
    """
    def run(self, topic):
        while True:
            member_name = self.redis.srandmember(topic)

            if not member_name:
                # If this happens, there are no
                # longer any members.
                break

            if not self.matchmaker.is_alive(topic, member_name):
                continue

            host = member_name.split('.', 1)[1]
            return [(member_name, host)]
        return []


class RedisFanoutExchange(RedisExchange):
    """Return a list of all hosts."""
    def run(self, topic):
        topic = topic.split('~', 1)[1]
        hosts = self.redis.smembers(topic)
        good_hosts = filter(
            lambda host: self.matchmaker.is_alive(topic, host), hosts)

        return [(x, x.split('.', 1)[1]) for x in good_hosts]


class MatchMakerRedis(mm_common.HeartbeatMatchMakerBase):
    """MatchMaker registering and looking-up hosts with a Redis server."""
    def __init__(self):
        super(MatchMakerRedis, self).__init__()

        if not redis:
            raise ImportError("Failed to import module redis.")

        self.redis = redis.Redis(
            host=CONF.matchmaker_redis.host,
            port=CONF.matchmaker_redis.port,
            password=CONF.matchmaker_redis.password)

        self.add_binding(mm_common.FanoutBinding(), RedisFanoutExchange(self))
        self.add_binding(mm_common.DirectBinding(), mm_common.DirectExchange())
        self.add_binding(mm_common.TopicBinding(), RedisTopicExchange(self))

    def ack_alive(self, key, host):
        topic = "%s.%s" % (key, host)
        if not self.redis.expire(topic, CONF.matchmaker_heartbeat_ttl):
            # If we could not update the expiration, the key
            # might have been pruned. Re-register, creating a new
            # key in Redis.
            self.register(self.topic_host[host], host)

    def is_alive(self, topic, host):
        if self.redis.ttl(host) == -1:
            self.expire(topic, host)
            return False
        return True

    def expire(self, topic, host):
        with self.redis.pipeline() as pipe:
            pipe.multi()
            pipe.delete(host)
            pipe.srem(topic, host)
            pipe.execute()

    def backend_register(self, key, key_host):
        with self.redis.pipeline() as pipe:
            pipe.multi()
            pipe.sadd(key, key_host)

            # No value is needed, we just
            # care if it exists. Sets aren't viable
            # because only keys can expire.
            pipe.set(key_host, '')

            pipe.execute()

    def backend_unregister(self, key, key_host):
        with self.redis.pipeline() as pipe:
            pipe.multi()
            pipe.srem(key, key_host)
            pipe.delete(key_host)
            pipe.execute()

########NEW FILE########
__FILENAME__ = matchmaker_ring
#    Copyright 2011-2013 Cloudscaling Group, Inc
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
The MatchMaker classes should except a Topic or Fanout exchange key and
return keys for direct exchanges, per (approximate) AMQP parlance.
"""

import itertools
import json

from oslo.config import cfg

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common.rpc import matchmaker as mm


matchmaker_opts = [
    # Matchmaker ring file
    cfg.StrOpt('ringfile',
               deprecated_name='matchmaker_ringfile',
               deprecated_group='DEFAULT',
               default='/etc/cloudbaseinit/matchmaker_ring.json',
               help='Matchmaker ring file (JSON)'),
]

CONF = cfg.CONF
CONF.register_opts(matchmaker_opts, 'matchmaker_ring')
LOG = logging.getLogger(__name__)


class RingExchange(mm.Exchange):
    """Match Maker where hosts are loaded from a static JSON formatted file.

    __init__ takes optional ring dictionary argument, otherwise
    loads the ringfile from CONF.mathcmaker_ringfile.
    """
    def __init__(self, ring=None):
        super(RingExchange, self).__init__()

        if ring:
            self.ring = ring
        else:
            with open(CONF.matchmaker_ring.ringfile, 'r') as fh:
                self.ring = json.load(fh)

        self.ring0 = {}
        for k in self.ring.keys():
            self.ring0[k] = itertools.cycle(self.ring[k])

    def _ring_has(self, key):
        return key in self.ring0


class RoundRobinRingExchange(RingExchange):
    """A Topic Exchange based on a hashmap."""
    def __init__(self, ring=None):
        super(RoundRobinRingExchange, self).__init__(ring)

    def run(self, key):
        if not self._ring_has(key):
            LOG.warn(
                _("No key defining hosts for topic '%s', "
                  "see ringfile") % (key, )
            )
            return []
        host = next(self.ring0[key])
        return [(key + '.' + host, host)]


class FanoutRingExchange(RingExchange):
    """Fanout Exchange based on a hashmap."""
    def __init__(self, ring=None):
        super(FanoutRingExchange, self).__init__(ring)

    def run(self, key):
        # Assume starts with "fanout~", strip it for lookup.
        nkey = key.split('fanout~')[1:][0]
        if not self._ring_has(nkey):
            LOG.warn(
                _("No key defining hosts for topic '%s', "
                  "see ringfile") % (nkey, )
            )
            return []
        return map(lambda x: (key + '.' + x, x), self.ring[nkey])


class MatchMakerRing(mm.MatchMakerBase):
    """Match Maker where hosts are loaded from a static hashmap."""
    def __init__(self, ring=None):
        super(MatchMakerRing, self).__init__()
        self.add_binding(mm.FanoutBinding(), FanoutRingExchange(ring))
        self.add_binding(mm.DirectBinding(), mm.DirectExchange())
        self.add_binding(mm.TopicBinding(), RoundRobinRingExchange(ring))

########NEW FILE########
__FILENAME__ = proxy
# Copyright 2012-2013 Red Hat, Inc.
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
A helper class for proxy objects to remote APIs.

For more information about rpc API version numbers, see:
    rpc/dispatcher.py
"""

import six

from cloudbaseinit.openstack.common import rpc
from cloudbaseinit.openstack.common.rpc import common as rpc_common
from cloudbaseinit.openstack.common.rpc import serializer as rpc_serializer


class RpcProxy(object):
    """A helper class for rpc clients.

    This class is a wrapper around the RPC client API.  It allows you to
    specify the topic and API version in a single place.  This is intended to
    be used as a base class for a class that implements the client side of an
    rpc API.
    """

    # The default namespace, which can be overridden in a subclass.
    RPC_API_NAMESPACE = None

    def __init__(self, topic, default_version, version_cap=None,
                 serializer=None):
        """Initialize an RpcProxy.

        :param topic: The topic to use for all messages.
        :param default_version: The default API version to request in all
               outgoing messages.  This can be overridden on a per-message
               basis.
        :param version_cap: Optionally cap the maximum version used for sent
               messages.
        :param serializer: Optionaly (de-)serialize entities with a
               provided helper.
        """
        self.topic = topic
        self.default_version = default_version
        self.version_cap = version_cap
        if serializer is None:
            serializer = rpc_serializer.NoOpSerializer()
        self.serializer = serializer
        super(RpcProxy, self).__init__()

    def _set_version(self, msg, vers):
        """Helper method to set the version in a message.

        :param msg: The message having a version added to it.
        :param vers: The version number to add to the message.
        """
        v = vers if vers else self.default_version
        if (self.version_cap and not
                rpc_common.version_is_compatible(self.version_cap, v)):
            raise rpc_common.RpcVersionCapError(version_cap=self.version_cap)
        msg['version'] = v

    def _get_topic(self, topic):
        """Return the topic to use for a message."""
        return topic if topic else self.topic

    def can_send_version(self, version):
        """Check to see if a version is compatible with the version cap."""
        return (not self.version_cap or
                rpc_common.version_is_compatible(self.version_cap, version))

    @staticmethod
    def make_namespaced_msg(method, namespace, **kwargs):
        return {'method': method, 'namespace': namespace, 'args': kwargs}

    def make_msg(self, method, **kwargs):
        return self.make_namespaced_msg(method, self.RPC_API_NAMESPACE,
                                        **kwargs)

    def _serialize_msg_args(self, context, kwargs):
        """Helper method called to serialize message arguments.

        This calls our serializer on each argument, returning a new
        set of args that have been serialized.

        :param context: The request context
        :param kwargs: The arguments to serialize
        :returns: A new set of serialized arguments
        """
        new_kwargs = dict()
        for argname, arg in six.iteritems(kwargs):
            new_kwargs[argname] = self.serializer.serialize_entity(context,
                                                                   arg)
        return new_kwargs

    def call(self, context, msg, topic=None, version=None, timeout=None):
        """rpc.call() a remote method.

        :param context: The request context
        :param msg: The message to send, including the method and args.
        :param topic: Override the topic for this message.
        :param version: (Optional) Override the requested API version in this
               message.
        :param timeout: (Optional) A timeout to use when waiting for the
               response.  If no timeout is specified, a default timeout will be
               used that is usually sufficient.

        :returns: The return value from the remote method.
        """
        self._set_version(msg, version)
        msg['args'] = self._serialize_msg_args(context, msg['args'])
        real_topic = self._get_topic(topic)
        try:
            result = rpc.call(context, real_topic, msg, timeout)
            return self.serializer.deserialize_entity(context, result)
        except rpc.common.Timeout as exc:
            raise rpc.common.Timeout(
                exc.info, real_topic, msg.get('method'))

    def multicall(self, context, msg, topic=None, version=None, timeout=None):
        """rpc.multicall() a remote method.

        :param context: The request context
        :param msg: The message to send, including the method and args.
        :param topic: Override the topic for this message.
        :param version: (Optional) Override the requested API version in this
               message.
        :param timeout: (Optional) A timeout to use when waiting for the
               response.  If no timeout is specified, a default timeout will be
               used that is usually sufficient.

        :returns: An iterator that lets you process each of the returned values
                  from the remote method as they arrive.
        """
        self._set_version(msg, version)
        msg['args'] = self._serialize_msg_args(context, msg['args'])
        real_topic = self._get_topic(topic)
        try:
            result = rpc.multicall(context, real_topic, msg, timeout)
            return self.serializer.deserialize_entity(context, result)
        except rpc.common.Timeout as exc:
            raise rpc.common.Timeout(
                exc.info, real_topic, msg.get('method'))

    def cast(self, context, msg, topic=None, version=None):
        """rpc.cast() a remote method.

        :param context: The request context
        :param msg: The message to send, including the method and args.
        :param topic: Override the topic for this message.
        :param version: (Optional) Override the requested API version in this
               message.

        :returns: None.  rpc.cast() does not wait on any return value from the
                  remote method.
        """
        self._set_version(msg, version)
        msg['args'] = self._serialize_msg_args(context, msg['args'])
        rpc.cast(context, self._get_topic(topic), msg)

    def fanout_cast(self, context, msg, topic=None, version=None):
        """rpc.fanout_cast() a remote method.

        :param context: The request context
        :param msg: The message to send, including the method and args.
        :param topic: Override the topic for this message.
        :param version: (Optional) Override the requested API version in this
               message.

        :returns: None.  rpc.fanout_cast() does not wait on any return value
                  from the remote method.
        """
        self._set_version(msg, version)
        msg['args'] = self._serialize_msg_args(context, msg['args'])
        rpc.fanout_cast(context, self._get_topic(topic), msg)

    def cast_to_server(self, context, server_params, msg, topic=None,
                       version=None):
        """rpc.cast_to_server() a remote method.

        :param context: The request context
        :param server_params: Server parameters.  See rpc.cast_to_server() for
               details.
        :param msg: The message to send, including the method and args.
        :param topic: Override the topic for this message.
        :param version: (Optional) Override the requested API version in this
               message.

        :returns: None.  rpc.cast_to_server() does not wait on any
                  return values.
        """
        self._set_version(msg, version)
        msg['args'] = self._serialize_msg_args(context, msg['args'])
        rpc.cast_to_server(context, server_params, self._get_topic(topic), msg)

    def fanout_cast_to_server(self, context, server_params, msg, topic=None,
                              version=None):
        """rpc.fanout_cast_to_server() a remote method.

        :param context: The request context
        :param server_params: Server parameters.  See rpc.cast_to_server() for
               details.
        :param msg: The message to send, including the method and args.
        :param topic: Override the topic for this message.
        :param version: (Optional) Override the requested API version in this
               message.

        :returns: None.  rpc.fanout_cast_to_server() does not wait on any
                  return values.
        """
        self._set_version(msg, version)
        msg['args'] = self._serialize_msg_args(context, msg['args'])
        rpc.fanout_cast_to_server(context, server_params,
                                  self._get_topic(topic), msg)

########NEW FILE########
__FILENAME__ = serializer
#    Copyright 2013 IBM Corp.
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

"""Provides the definition of an RPC serialization handler"""

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class Serializer(object):
    """Generic (de-)serialization definition base class."""

    @abc.abstractmethod
    def serialize_entity(self, context, entity):
        """Serialize something to primitive form.

        :param context: Security context
        :param entity: Entity to be serialized
        :returns: Serialized form of entity
        """
        pass

    @abc.abstractmethod
    def deserialize_entity(self, context, entity):
        """Deserialize something from primitive form.

        :param context: Security context
        :param entity: Primitive to be deserialized
        :returns: Deserialized form of entity
        """
        pass


class NoOpSerializer(Serializer):
    """A serializer that does nothing."""

    def serialize_entity(self, context, entity):
        return entity

    def deserialize_entity(self, context, entity):
        return entity

########NEW FILE########
__FILENAME__ = service
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2011 Red Hat, Inc.
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

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import rpc
from cloudbaseinit.openstack.common.rpc import dispatcher as rpc_dispatcher
from cloudbaseinit.openstack.common import service


LOG = logging.getLogger(__name__)


class Service(service.Service):
    """Service object for binaries running on hosts.

    A service enables rpc by listening to queues based on topic and host.
    """
    def __init__(self, host, topic, manager=None, serializer=None):
        super(Service, self).__init__()
        self.host = host
        self.topic = topic
        self.serializer = serializer
        if manager is None:
            self.manager = self
        else:
            self.manager = manager

    def start(self):
        super(Service, self).start()

        self.conn = rpc.create_connection(new=True)
        LOG.debug(_("Creating Consumer connection for Service %s") %
                  self.topic)

        dispatcher = rpc_dispatcher.RpcDispatcher([self.manager],
                                                  self.serializer)

        # Share this same connection for these Consumers
        self.conn.create_consumer(self.topic, dispatcher, fanout=False)

        node_topic = '%s.%s' % (self.topic, self.host)
        self.conn.create_consumer(node_topic, dispatcher, fanout=False)

        self.conn.create_consumer(self.topic, dispatcher, fanout=True)

        # Hook to allow the manager to do other initializations after
        # the rpc connection is created.
        if callable(getattr(self.manager, 'initialize_service_hook', None)):
            self.manager.initialize_service_hook(self)

        # Consume from all consumers in a thread
        self.conn.consume_in_thread()

    def stop(self):
        # Try to shut the connection down, but if we get any sort of
        # errors, go ahead and ignore them.. as we're shutting down anyway
        try:
            self.conn.close()
        except Exception:
            pass
        super(Service, self).stop()

########NEW FILE########
__FILENAME__ = zmq_receiver
#    Copyright 2011 OpenStack Foundation
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

import eventlet
eventlet.monkey_patch()

import contextlib
import sys

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import rpc
from cloudbaseinit.openstack.common.rpc import impl_zmq

CONF = cfg.CONF
CONF.register_opts(rpc.rpc_opts)
CONF.register_opts(impl_zmq.zmq_opts)


def main():
    CONF(sys.argv[1:], project='cloudbaseinit')
    logging.setup("cloudbaseinit")

    with contextlib.closing(impl_zmq.ZmqProxy(CONF)) as reactor:
        reactor.consume_in_thread()
        reactor.wait()

########NEW FILE########
__FILENAME__ = service
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
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

"""Generic Node base class for all workers that run on hosts."""

import errno
import logging as std_logging
import os
import random
import signal
import sys
import time

try:
    # Importing just the symbol here because the io module does not
    # exist in Python 2.6.
    from io import UnsupportedOperation  # noqa
except ImportError:
    # Python 2.6
    UnsupportedOperation = None

import eventlet
from eventlet import event
from oslo.config import cfg

from cloudbaseinit.openstack.common import eventlet_backdoor
from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import importutils
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import threadgroup


rpc = importutils.try_import('cloudbaseinit.openstack.common.rpc')
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _sighup_supported():
    return hasattr(signal, 'SIGHUP')


def _is_daemon():
    # The process group for a foreground process will match the
    # process group of the controlling terminal. If those values do
    # not match, or ioctl() fails on the stdout file handle, we assume
    # the process is running in the background as a daemon.
    # http://www.gnu.org/software/bash/manual/bashref.html#Job-Control-Basics
    try:
        is_daemon = os.getpgrp() != os.tcgetpgrp(sys.stdout.fileno())
    except OSError as err:
        if err.errno == errno.ENOTTY:
            # Assume we are a daemon because there is no terminal.
            is_daemon = True
        else:
            raise
    except UnsupportedOperation:
        # Could not get the fileno for stdout, so we must be a daemon.
        is_daemon = True
    return is_daemon


def _is_sighup_and_daemon(signo):
    if not (_sighup_supported() and signo == signal.SIGHUP):
        # Avoid checking if we are a daemon, because the signal isn't
        # SIGHUP.
        return False
    return _is_daemon()


def _signo_to_signame(signo):
    signals = {signal.SIGTERM: 'SIGTERM',
               signal.SIGINT: 'SIGINT'}
    if _sighup_supported():
        signals[signal.SIGHUP] = 'SIGHUP'
    return signals[signo]


def _set_signals_handler(handler):
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    if _sighup_supported():
        signal.signal(signal.SIGHUP, handler)


class Launcher(object):
    """Launch one or more services and wait for them to complete."""

    def __init__(self):
        """Initialize the service launcher.

        :returns: None

        """
        self.services = Services()
        self.backdoor_port = eventlet_backdoor.initialize_if_enabled()

    def launch_service(self, service):
        """Load and start the given service.

        :param service: The service you would like to start.
        :returns: None

        """
        service.backdoor_port = self.backdoor_port
        self.services.add(service)

    def stop(self):
        """Stop all services which are currently running.

        :returns: None

        """
        self.services.stop()

    def wait(self):
        """Waits until all services have been stopped, and then returns.

        :returns: None

        """
        self.services.wait()

    def restart(self):
        """Reload config files and restart service.

        :returns: None

        """
        cfg.CONF.reload_config_files()
        self.services.restart()


class SignalExit(SystemExit):
    def __init__(self, signo, exccode=1):
        super(SignalExit, self).__init__(exccode)
        self.signo = signo


class ServiceLauncher(Launcher):
    def _handle_signal(self, signo, frame):
        # Allow the process to be killed again and die from natural causes
        _set_signals_handler(signal.SIG_DFL)
        raise SignalExit(signo)

    def handle_signal(self):
        _set_signals_handler(self._handle_signal)

    def _wait_for_exit_or_signal(self, ready_callback=None):
        status = None
        signo = 0

        LOG.debug(_('Full set of CONF:'))
        CONF.log_opt_values(LOG, std_logging.DEBUG)

        try:
            if ready_callback:
                ready_callback()
            super(ServiceLauncher, self).wait()
        except SignalExit as exc:
            signame = _signo_to_signame(exc.signo)
            LOG.info(_('Caught %s, exiting'), signame)
            status = exc.code
            signo = exc.signo
        except SystemExit as exc:
            status = exc.code
        finally:
            self.stop()
            if rpc:
                try:
                    rpc.cleanup()
                except Exception:
                    # We're shutting down, so it doesn't matter at this point.
                    LOG.exception(_('Exception during rpc cleanup.'))

        return status, signo

    def wait(self, ready_callback=None):
        while True:
            self.handle_signal()
            status, signo = self._wait_for_exit_or_signal(ready_callback)
            if not _is_sighup_and_daemon(signo):
                return status
            self.restart()


class ServiceWrapper(object):
    def __init__(self, service, workers):
        self.service = service
        self.workers = workers
        self.children = set()
        self.forktimes = []


class ProcessLauncher(object):
    def __init__(self, wait_interval=0.01):
        """Constructor.

        :param wait_interval: The interval to sleep for between checks
                              of child process exit.
        """
        self.children = {}
        self.sigcaught = None
        self.running = True
        self.wait_interval = wait_interval
        rfd, self.writepipe = os.pipe()
        self.readpipe = eventlet.greenio.GreenPipe(rfd, 'r')
        self.handle_signal()

    def handle_signal(self):
        _set_signals_handler(self._handle_signal)

    def _handle_signal(self, signo, frame):
        self.sigcaught = signo
        self.running = False

        # Allow the process to be killed again and die from natural causes
        _set_signals_handler(signal.SIG_DFL)

    def _pipe_watcher(self):
        # This will block until the write end is closed when the parent
        # dies unexpectedly
        self.readpipe.read()

        LOG.info(_('Parent process has died unexpectedly, exiting'))

        sys.exit(1)

    def _child_process_handle_signal(self):
        # Setup child signal handlers differently
        def _sigterm(*args):
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            raise SignalExit(signal.SIGTERM)

        def _sighup(*args):
            signal.signal(signal.SIGHUP, signal.SIG_DFL)
            raise SignalExit(signal.SIGHUP)

        signal.signal(signal.SIGTERM, _sigterm)
        if _sighup_supported():
            signal.signal(signal.SIGHUP, _sighup)
        # Block SIGINT and let the parent send us a SIGTERM
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _child_wait_for_exit_or_signal(self, launcher):
        status = 0
        signo = 0

        # NOTE(johannes): All exceptions are caught to ensure this
        # doesn't fallback into the loop spawning children. It would
        # be bad for a child to spawn more children.
        try:
            launcher.wait()
        except SignalExit as exc:
            signame = _signo_to_signame(exc.signo)
            LOG.info(_('Caught %s, exiting'), signame)
            status = exc.code
            signo = exc.signo
        except SystemExit as exc:
            status = exc.code
        except BaseException:
            LOG.exception(_('Unhandled exception'))
            status = 2
        finally:
            launcher.stop()

        return status, signo

    def _child_process(self, service):
        self._child_process_handle_signal()

        # Reopen the eventlet hub to make sure we don't share an epoll
        # fd with parent and/or siblings, which would be bad
        eventlet.hubs.use_hub()

        # Close write to ensure only parent has it open
        os.close(self.writepipe)
        # Create greenthread to watch for parent to close pipe
        eventlet.spawn_n(self._pipe_watcher)

        # Reseed random number generator
        random.seed()

        launcher = Launcher()
        launcher.launch_service(service)
        return launcher

    def _start_child(self, wrap):
        if len(wrap.forktimes) > wrap.workers:
            # Limit ourselves to one process a second (over the period of
            # number of workers * 1 second). This will allow workers to
            # start up quickly but ensure we don't fork off children that
            # die instantly too quickly.
            if time.time() - wrap.forktimes[0] < wrap.workers:
                LOG.info(_('Forking too fast, sleeping'))
                time.sleep(1)

            wrap.forktimes.pop(0)

        wrap.forktimes.append(time.time())

        pid = os.fork()
        if pid == 0:
            launcher = self._child_process(wrap.service)
            while True:
                self._child_process_handle_signal()
                status, signo = self._child_wait_for_exit_or_signal(launcher)
                if not _is_sighup_and_daemon(signo):
                    break
                launcher.restart()

            os._exit(status)

        LOG.info(_('Started child %d'), pid)

        wrap.children.add(pid)
        self.children[pid] = wrap

        return pid

    def launch_service(self, service, workers=1):
        wrap = ServiceWrapper(service, workers)

        LOG.info(_('Starting %d workers'), wrap.workers)
        while self.running and len(wrap.children) < wrap.workers:
            self._start_child(wrap)

    def _wait_child(self):
        try:
            # Don't block if no child processes have exited
            pid, status = os.waitpid(0, os.WNOHANG)
            if not pid:
                return None
        except OSError as exc:
            if exc.errno not in (errno.EINTR, errno.ECHILD):
                raise
            return None

        if os.WIFSIGNALED(status):
            sig = os.WTERMSIG(status)
            LOG.info(_('Child %(pid)d killed by signal %(sig)d'),
                     dict(pid=pid, sig=sig))
        else:
            code = os.WEXITSTATUS(status)
            LOG.info(_('Child %(pid)s exited with status %(code)d'),
                     dict(pid=pid, code=code))

        if pid not in self.children:
            LOG.warning(_('pid %d not in child list'), pid)
            return None

        wrap = self.children.pop(pid)
        wrap.children.remove(pid)
        return wrap

    def _respawn_children(self):
        while self.running:
            wrap = self._wait_child()
            if not wrap:
                # Yield to other threads if no children have exited
                # Sleep for a short time to avoid excessive CPU usage
                # (see bug #1095346)
                eventlet.greenthread.sleep(self.wait_interval)
                continue
            while self.running and len(wrap.children) < wrap.workers:
                self._start_child(wrap)

    def wait(self):
        """Loop waiting on children to die and respawning as necessary."""

        LOG.debug(_('Full set of CONF:'))
        CONF.log_opt_values(LOG, std_logging.DEBUG)

        while True:
            self.handle_signal()
            self._respawn_children()
            if self.sigcaught:
                signame = _signo_to_signame(self.sigcaught)
                LOG.info(_('Caught %s, stopping children'), signame)
            if not _is_sighup_and_daemon(self.sigcaught):
                break

            for pid in self.children:
                os.kill(pid, signal.SIGHUP)
            self.running = True
            self.sigcaught = None

        for pid in self.children:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                if exc.errno != errno.ESRCH:
                    raise

        # Wait for children to die
        if self.children:
            LOG.info(_('Waiting on %d children to exit'), len(self.children))
            while self.children:
                self._wait_child()


class Service(object):
    """Service object for binaries running on hosts."""

    def __init__(self, threads=1000):
        self.tg = threadgroup.ThreadGroup(threads)

        # signal that the service is done shutting itself down:
        self._done = event.Event()

    def reset(self):
        # NOTE(Fengqian): docs for Event.reset() recommend against using it
        self._done = event.Event()

    def start(self):
        pass

    def stop(self):
        self.tg.stop()
        self.tg.wait()
        # Signal that service cleanup is done:
        if not self._done.ready():
            self._done.send()

    def wait(self):
        self._done.wait()


class Services(object):

    def __init__(self):
        self.services = []
        self.tg = threadgroup.ThreadGroup()
        self.done = event.Event()

    def add(self, service):
        self.services.append(service)
        self.tg.add_thread(self.run_service, service, self.done)

    def stop(self):
        # wait for graceful shutdown of services:
        for service in self.services:
            service.stop()
            service.wait()

        # Each service has performed cleanup, now signal that the run_service
        # wrapper threads can now die:
        if not self.done.ready():
            self.done.send()

        # reap threads:
        self.tg.stop()

    def wait(self):
        self.tg.wait()

    def restart(self):
        self.stop()
        self.done = event.Event()
        for restart_service in self.services:
            restart_service.reset()
            self.tg.add_thread(self.run_service, restart_service, self.done)

    @staticmethod
    def run_service(service, done):
        """Service start wrapper.

        :param service: service to run
        :param done: event to wait on until a shutdown is triggered
        :returns: None

        """
        service.start()
        done.wait()


def launch(service, workers=1):
    if workers is None or workers == 1:
        launcher = ServiceLauncher()
        launcher.launch_service(service)
    else:
        launcher = ProcessLauncher()
        launcher.launch_service(service, workers=workers)

    return launcher

########NEW FILE########
__FILENAME__ = sslutils
# Copyright 2013 IBM Corp.
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
import ssl

from oslo.config import cfg

from cloudbaseinit.openstack.common.gettextutils import _


ssl_opts = [
    cfg.StrOpt('ca_file',
               default=None,
               help="CA certificate file to use to verify "
                    "connecting clients"),
    cfg.StrOpt('cert_file',
               default=None,
               help="Certificate file to use when starting "
                    "the server securely"),
    cfg.StrOpt('key_file',
               default=None,
               help="Private key file to use when starting "
                    "the server securely"),
]


CONF = cfg.CONF
CONF.register_opts(ssl_opts, "ssl")


def is_enabled():
    cert_file = CONF.ssl.cert_file
    key_file = CONF.ssl.key_file
    ca_file = CONF.ssl.ca_file
    use_ssl = cert_file or key_file

    if cert_file and not os.path.exists(cert_file):
        raise RuntimeError(_("Unable to find cert_file : %s") % cert_file)

    if ca_file and not os.path.exists(ca_file):
        raise RuntimeError(_("Unable to find ca_file : %s") % ca_file)

    if key_file and not os.path.exists(key_file):
        raise RuntimeError(_("Unable to find key_file : %s") % key_file)

    if use_ssl and (not cert_file or not key_file):
        raise RuntimeError(_("When running server in SSL mode, you must "
                             "specify both a cert_file and key_file "
                             "option value in your configuration file"))

    return use_ssl


def wrap(sock):
    ssl_kwargs = {
        'server_side': True,
        'certfile': CONF.ssl.cert_file,
        'keyfile': CONF.ssl.key_file,
        'cert_reqs': ssl.CERT_NONE,
    }

    if CONF.ssl.ca_file:
        ssl_kwargs['ca_certs'] = CONF.ssl.ca_file
        ssl_kwargs['cert_reqs'] = ssl.CERT_REQUIRED

    return ssl.wrap_socket(sock, **ssl_kwargs)


_SSL_PROTOCOLS = {
    "tlsv1": ssl.PROTOCOL_TLSv1,
    "sslv23": ssl.PROTOCOL_SSLv23,
    "sslv3": ssl.PROTOCOL_SSLv3
}

try:
    _SSL_PROTOCOLS["sslv2"] = ssl.PROTOCOL_SSLv2
except AttributeError:
    pass


def validate_ssl_version(version):
    key = version.lower()
    try:
        return _SSL_PROTOCOLS[key]
    except KeyError:
        raise RuntimeError(_("Invalid SSL version : %s") % version)

########NEW FILE########
__FILENAME__ = threadgroup
# Copyright 2012 Red Hat, Inc.
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
import threading

import eventlet
from eventlet import greenpool

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.openstack.common import loopingcall


LOG = logging.getLogger(__name__)


def _thread_done(gt, *args, **kwargs):
    """Callback function to be passed to GreenThread.link() when we spawn()
    Calls the :class:`ThreadGroup` to notify if.

    """
    kwargs['group'].thread_done(kwargs['thread'])


class Thread(object):
    """Wrapper around a greenthread, that holds a reference to the
    :class:`ThreadGroup`. The Thread will notify the :class:`ThreadGroup` when
    it has done so it can be removed from the threads list.
    """
    def __init__(self, thread, group):
        self.thread = thread
        self.thread.link(_thread_done, group=group, thread=self)

    def stop(self):
        self.thread.kill()

    def wait(self):
        return self.thread.wait()

    def link(self, func, *args, **kwargs):
        self.thread.link(func, *args, **kwargs)


class ThreadGroup(object):
    """The point of the ThreadGroup class is to:

    * keep track of timers and greenthreads (making it easier to stop them
      when need be).
    * provide an easy API to add timers.
    """
    def __init__(self, thread_pool_size=10):
        self.pool = greenpool.GreenPool(thread_pool_size)
        self.threads = []
        self.timers = []

    def add_dynamic_timer(self, callback, initial_delay=None,
                          periodic_interval_max=None, *args, **kwargs):
        timer = loopingcall.DynamicLoopingCall(callback, *args, **kwargs)
        timer.start(initial_delay=initial_delay,
                    periodic_interval_max=periodic_interval_max)
        self.timers.append(timer)

    def add_timer(self, interval, callback, initial_delay=None,
                  *args, **kwargs):
        pulse = loopingcall.FixedIntervalLoopingCall(callback, *args, **kwargs)
        pulse.start(interval=interval,
                    initial_delay=initial_delay)
        self.timers.append(pulse)

    def add_thread(self, callback, *args, **kwargs):
        gt = self.pool.spawn(callback, *args, **kwargs)
        th = Thread(gt, self)
        self.threads.append(th)
        return th

    def thread_done(self, thread):
        self.threads.remove(thread)

    def stop(self):
        current = threading.current_thread()

        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x is current:
                # don't kill the current thread.
                continue
            try:
                x.stop()
            except Exception as ex:
                LOG.exception(ex)

        for x in self.timers:
            try:
                x.stop()
            except Exception as ex:
                LOG.exception(ex)
        self.timers = []

    def wait(self):
        for x in self.timers:
            try:
                x.wait()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)
        current = threading.current_thread()

        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x is current:
                continue
            try:
                x.wait()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)

########NEW FILE########
__FILENAME__ = timeutils
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
        raise ValueError(six.text_type(e))
    except TypeError as e:
        raise ValueError(six.text_type(e))


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
    else:
        before = before.replace(tzinfo=None)

    return utcnow() - before > datetime.timedelta(seconds=seconds)


def is_newer_than(after, seconds):
    """Return True if after is newer than seconds."""
    if isinstance(after, six.string_types):
        after = parse_strtime(after).replace(tzinfo=None)
    else:
        after = after.replace(tzinfo=None)

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
    """Returns a iso8601 formatted date from timestamp."""
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
    return total_seconds(delta)


def total_seconds(delta):
    """Return the total seconds of datetime.timedelta object.

    Compute total seconds of datetime.timedelta, datetime.timedelta
    doesn't have method total_seconds in Python2.6, calculate it manually.
    """
    try:
        return delta.total_seconds()
    except AttributeError:
        return ((delta.days * 24 * 3600) + delta.seconds +
                float(delta.microseconds) / (10 ** 6))


def is_soon(dt, window):
    """Determines if time is going to happen in the next window seconds.

    :param dt: the time
    :param window: minimum seconds to remain to consider the time not soon

    :return: True if expiration is within the given duration
    """
    soon = (utcnow() + datetime.timedelta(seconds=window))
    return normalize_time(dt) <= soon

########NEW FILE########
__FILENAME__ = versionutils
# Copyright (c) 2013 OpenStack Foundation
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
Helpers for comparing version strings.
"""

import functools
import pkg_resources

from cloudbaseinit.openstack.common.gettextutils import _
from cloudbaseinit.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class deprecated(object):
    """A decorator to mark callables as deprecated.

    This decorator logs a deprecation message when the callable it decorates is
    used. The message will include the release where the callable was
    deprecated, the release where it may be removed and possibly an optional
    replacement.

    Examples:

    1. Specifying the required deprecated release

    >>> @deprecated(as_of=deprecated.ICEHOUSE)
    ... def a(): pass

    2. Specifying a replacement:

    >>> @deprecated(as_of=deprecated.ICEHOUSE, in_favor_of='f()')
    ... def b(): pass

    3. Specifying the release where the functionality may be removed:

    >>> @deprecated(as_of=deprecated.ICEHOUSE, remove_in=+1)
    ... def c(): pass

    """

    FOLSOM = 'F'
    GRIZZLY = 'G'
    HAVANA = 'H'
    ICEHOUSE = 'I'

    _RELEASES = {
        'F': 'Folsom',
        'G': 'Grizzly',
        'H': 'Havana',
        'I': 'Icehouse',
    }

    _deprecated_msg_with_alternative = _(
        '%(what)s is deprecated as of %(as_of)s in favor of '
        '%(in_favor_of)s and may be removed in %(remove_in)s.')

    _deprecated_msg_no_alternative = _(
        '%(what)s is deprecated as of %(as_of)s and may be '
        'removed in %(remove_in)s. It will not be superseded.')

    def __init__(self, as_of, in_favor_of=None, remove_in=2, what=None):
        """Initialize decorator

        :param as_of: the release deprecating the callable. Constants
            are define in this class for convenience.
        :param in_favor_of: the replacement for the callable (optional)
        :param remove_in: an integer specifying how many releases to wait
            before removing (default: 2)
        :param what: name of the thing being deprecated (default: the
            callable's name)

        """
        self.as_of = as_of
        self.in_favor_of = in_favor_of
        self.remove_in = remove_in
        self.what = what

    def __call__(self, func):
        if not self.what:
            self.what = func.__name__ + '()'

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            msg, details = self._build_message()
            LOG.deprecated(msg, details)
            return func(*args, **kwargs)
        return wrapped

    def _get_safe_to_remove_release(self, release):
        # TODO(dstanek): this method will have to be reimplemented once
        #    when we get to the X release because once we get to the Y
        #    release, what is Y+2?
        new_release = chr(ord(release) + self.remove_in)
        if new_release in self._RELEASES:
            return self._RELEASES[new_release]
        else:
            return new_release

    def _build_message(self):
        details = dict(what=self.what,
                       as_of=self._RELEASES[self.as_of],
                       remove_in=self._get_safe_to_remove_release(self.as_of))

        if self.in_favor_of:
            details['in_favor_of'] = self.in_favor_of
            msg = self._deprecated_msg_with_alternative
        else:
            msg = self._deprecated_msg_no_alternative
        return msg, details


def is_compatible(requested_version, current_version, same_major=True):
    """Determine whether `requested_version` is satisfied by
    `current_version`; in other words, `current_version` is >=
    `requested_version`.

    :param requested_version: version to check for compatibility
    :param current_version: version to check against
    :param same_major: if True, the major version must be identical between
        `requested_version` and `current_version`. This is used when a
        major-version difference indicates incompatibility between the two
        versions. Since this is the common-case in practice, the default is
        True.
    :returns: True if compatible, False if not
    """
    requested_parts = pkg_resources.parse_version(requested_version)
    current_parts = pkg_resources.parse_version(current_version)

    if same_major and (requested_parts[0] != current_parts[0]):
        return False

    return current_parts >= requested_parts

########NEW FILE########
__FILENAME__ = base
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import base64
import os
import subprocess


class BaseOSUtils(object):
    PROTOCOL_TCP = "TCP"
    PROTOCOL_UDP = "UDP"

    def reboot(self):
        raise NotImplementedError()

    def user_exists(self, username):
        raise NotImplementedError()

    def generate_random_password(self, length):
        # On Windows os.urandom() uses CryptGenRandom, which is a
        # cryptographically secure pseudorandom number generator
        b64_password = base64.b64encode(os.urandom(256))
        return b64_password.replace('/', '').replace('+', '')[:length]

    def execute_process(self, args, shell=True):
        p = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=shell)
        (out, err) = p.communicate()
        return (out, err, p.returncode)

    def sanitize_shell_input(self, value):
        raise NotImplementedError()

    def create_user(self, username, password, password_expires=False):
        raise NotImplementedError()

    def set_user_password(self, username, password, password_expires=False):
        raise NotImplementedError()

    def add_user_to_local_group(self, username, groupname):
        raise NotImplementedError()

    def set_host_name(self, new_host_name):
        raise NotImplementedError()

    def get_user_home(self, username):
        raise NotImplementedError()

    def get_network_adapters(self):
        raise NotImplementedError()

    def set_static_network_config(self, adapter_name, address, netmask,
                                  broadcast, gateway, dnsnameservers):
        raise NotImplementedError()

    def set_config_value(self, name, value, section=None):
        raise NotImplementedError()

    def get_config_value(self, name, section=None):
        raise NotImplementedError()

    def wait_for_boot_completion(self):
        pass

    def terminate(self):
        pass

    def get_default_gateway(self):
        raise NotImplementedError()

    def check_static_route_exists(self, destination):
        raise NotImplementedError()

    def add_static_route(self, destination, mask, next_hop, interface_index,
                         metric):
        raise NotImplementedError()

    def check_os_version(self, major, minor, build=0):
        raise NotImplementedError()

    def get_volume_label(self, drive):
        raise NotImplementedError()

    def firewall_create_rule(self, name, port, protocol, allow=True):
        raise NotImplementedError()

    def firewall_remove_rule(self, name, port, protocol, allow=True):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

from cloudbaseinit.utils import classloader


def get_os_utils():
    osutils_class_paths = {
        'nt': 'cloudbaseinit.osutils.windows.WindowsUtils',
        'posix': 'cloudbaseinit.osutils.posix.PosixUtils'
    }

    cl = classloader.ClassLoader()
    return cl.load_class(osutils_class_paths[os.name])()

########NEW FILE########
__FILENAME__ = posix
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

from cloudbaseinit.osutils import base


class PosixUtil(base.BaseOSUtils):
    def reboot(self):
        os.system('reboot')

########NEW FILE########
__FILENAME__ = windows
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import _winreg
import ctypes
import os
import re
import time
import win32process
import win32security
import wmi

from ctypes import windll
from ctypes import wintypes
from win32com import client

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import base

LOG = logging.getLogger(__name__)

advapi32 = windll.advapi32
kernel32 = windll.kernel32
netapi32 = windll.netapi32
userenv = windll.userenv
iphlpapi = windll.iphlpapi
Ws2_32 = windll.Ws2_32
setupapi = windll.setupapi
msvcrt = ctypes.cdll.msvcrt


class Win32_PROFILEINFO(ctypes.Structure):
    _fields_ = [
        ('dwSize',          wintypes.DWORD),
        ('dwFlags',         wintypes.DWORD),
        ('lpUserName',      wintypes.LPWSTR),
        ('lpProfilePath',   wintypes.LPWSTR),
        ('lpDefaultPath',   wintypes.LPWSTR),
        ('lpServerName',    wintypes.LPWSTR),
        ('lpPolicyPath',    wintypes.LPWSTR),
        ('hprofile',        wintypes.HANDLE)
    ]


class Win32_LOCALGROUP_MEMBERS_INFO_3(ctypes.Structure):
    _fields_ = [
        ('lgrmi3_domainandname', wintypes.LPWSTR)
    ]


class Win32_MIB_IPFORWARDROW(ctypes.Structure):
    _fields_ = [
        ('dwForwardDest', wintypes.DWORD),
        ('dwForwardMask', wintypes.DWORD),
        ('dwForwardPolicy', wintypes.DWORD),
        ('dwForwardNextHop', wintypes.DWORD),
        ('dwForwardIfIndex', wintypes.DWORD),
        ('dwForwardType', wintypes.DWORD),
        ('dwForwardProto', wintypes.DWORD),
        ('dwForwardAge', wintypes.DWORD),
        ('dwForwardNextHopAS', wintypes.DWORD),
        ('dwForwardMetric1', wintypes.DWORD),
        ('dwForwardMetric2', wintypes.DWORD),
        ('dwForwardMetric3', wintypes.DWORD),
        ('dwForwardMetric4', wintypes.DWORD),
        ('dwForwardMetric5', wintypes.DWORD)
    ]


class Win32_MIB_IPFORWARDTABLE(ctypes.Structure):
    _fields_ = [
        ('dwNumEntries', wintypes.DWORD),
        ('table', Win32_MIB_IPFORWARDROW * 1)
    ]


class Win32_OSVERSIONINFOEX_W(ctypes.Structure):
    _fields_ = [
        ('dwOSVersionInfoSize', wintypes.DWORD),
        ('dwMajorVersion', wintypes.DWORD),
        ('dwMinorVersion', wintypes.DWORD),
        ('dwBuildNumber', wintypes.DWORD),
        ('dwPlatformId', wintypes.DWORD),
        ('szCSDVersion', wintypes.WCHAR * 128),
        ('wServicePackMajor', wintypes.DWORD),
        ('wServicePackMinor', wintypes.DWORD),
        ('wSuiteMask', wintypes.DWORD),
        ('wProductType', wintypes.BYTE),
        ('wReserved', wintypes.BYTE)
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.wintypes.DWORD),
        ("data2", ctypes.wintypes.WORD),
        ("data3", ctypes.wintypes.WORD),
        ("data4", ctypes.c_byte * 8)]

    def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
        self.data1 = l
        self.data2 = w1
        self.data3 = w2
        self.data4[0] = b1
        self.data4[1] = b2
        self.data4[2] = b3
        self.data4[3] = b4
        self.data4[4] = b5
        self.data4[5] = b6
        self.data4[6] = b7
        self.data4[7] = b8


class Win32_SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('InterfaceClassGuid', GUID),
        ('Flags', wintypes.DWORD),
        ('Reserved', ctypes.POINTER(wintypes.ULONG))
    ]


class Win32_SP_DEVICE_INTERFACE_DETAIL_DATA_W(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('DevicePath', ctypes.c_byte * 2)
    ]


class Win32_STORAGE_DEVICE_NUMBER(ctypes.Structure):
    _fields_ = [
        ('DeviceType', wintypes.DWORD),
        ('DeviceNumber', wintypes.DWORD),
        ('PartitionNumber', wintypes.DWORD)
    ]


msvcrt.malloc.argtypes = [ctypes.c_size_t]
msvcrt.malloc.restype = ctypes.c_void_p

msvcrt.free.argtypes = [ctypes.c_void_p]
msvcrt.free.restype = None

kernel32.VerifyVersionInfoW.argtypes = [
    ctypes.POINTER(Win32_OSVERSIONINFOEX_W),
    wintypes.DWORD, wintypes.ULARGE_INTEGER]
kernel32.VerifyVersionInfoW.restype = wintypes.BOOL

kernel32.VerSetConditionMask.argtypes = [wintypes.ULARGE_INTEGER,
                                         wintypes.DWORD,
                                         wintypes.BYTE]
kernel32.VerSetConditionMask.restype = wintypes.ULARGE_INTEGER

kernel32.SetComputerNameExW.argtypes = [ctypes.c_int, wintypes.LPCWSTR]
kernel32.SetComputerNameExW.restype = wintypes.BOOL

kernel32.GetLogicalDriveStringsW.argtypes = [wintypes.DWORD, wintypes.LPWSTR]
kernel32.GetLogicalDriveStringsW.restype = wintypes.DWORD

kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
kernel32.GetDriveTypeW.restype = wintypes.UINT

kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                 wintypes.DWORD, wintypes.LPVOID,
                                 wintypes.DWORD, wintypes.DWORD,
                                 wintypes.HANDLE]
kernel32.CreateFileW.restype = wintypes.HANDLE

kernel32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                     wintypes.LPVOID, wintypes.DWORD,
                                     wintypes.LPVOID, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.DWORD),
                                     wintypes.LPVOID]
kernel32.DeviceIoControl.restype = wintypes.BOOL

kernel32.GetProcessHeap.argtypes = []
kernel32.GetProcessHeap.restype = wintypes.HANDLE

# Note: wintypes.ULONG must be replaced with a 64 bit variable on x64
kernel32.HeapAlloc.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                               wintypes.ULONG]
kernel32.HeapAlloc.restype = wintypes.LPVOID

kernel32.HeapFree.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                              wintypes.LPVOID]
kernel32.HeapFree.restype = wintypes.BOOL

iphlpapi.GetIpForwardTable.argtypes = [
    ctypes.POINTER(Win32_MIB_IPFORWARDTABLE),
    ctypes.POINTER(wintypes.ULONG),
    wintypes.BOOL]
iphlpapi.GetIpForwardTable.restype = wintypes.DWORD

Ws2_32.inet_ntoa.restype = ctypes.c_char_p

setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID),
                                          wintypes.LPCWSTR,
                                          wintypes.HANDLE,
                                          wintypes.DWORD]
setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE

setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.POINTER(GUID),
    wintypes.DWORD,
    ctypes.POINTER(Win32_SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL

setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(Win32_SP_DEVICE_INTERFACE_DATA),
    ctypes.POINTER(Win32_SP_DEVICE_INTERFACE_DETAIL_DATA_W),
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.LPVOID]
setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL

setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

VER_MAJORVERSION = 1
VER_MINORVERSION = 2
VER_BUILDNUMBER = 4

VER_GREATER_EQUAL = 3

GUID_DEVINTERFACE_DISK = GUID(0x53f56307L, 0xb6bf, 0x11d0, 0x94, 0xf2,
                              0x00, 0xa0, 0xc9, 0x1e, 0xfb, 0x8b)


class WindowsUtils(base.BaseOSUtils):
    NERR_GroupNotFound = 2220
    ERROR_ACCESS_DENIED = 5
    ERROR_INSUFFICIENT_BUFFER = 122
    ERROR_NO_DATA = 232
    ERROR_NO_SUCH_MEMBER = 1387
    ERROR_MEMBER_IN_ALIAS = 1378
    ERROR_INVALID_MEMBER = 1388
    ERROR_OLD_WIN_VERSION = 1150
    ERROR_NO_MORE_FILES = 18

    INVALID_HANDLE_VALUE = 0xFFFFFFFF

    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2

    OPEN_EXISTING = 3

    IOCTL_STORAGE_GET_DEVICE_NUMBER = 0x002D1080

    MAX_PATH = 260

    DIGCF_PRESENT = 2
    DIGCF_DEVICEINTERFACE = 0x10

    DRIVE_CDROM = 5

    SERVICE_STATUS_STOPPED = "Stopped"
    SERVICE_STATUS_START_PENDING = "Start Pending"
    SERVICE_STATUS_STOP_PENDING = "Stop Pending"
    SERVICE_STATUS_RUNNING = "Running"
    SERVICE_STATUS_CONTINUE_PENDING = "Continue Pending"
    SERVICE_STATUS_PAUSE_PENDING = "Pause Pending"
    SERVICE_STATUS_PAUSED = "Paused"
    SERVICE_STATUS_UNKNOWN = "Unknown"

    SERVICE_START_MODE_AUTOMATIC = "Automatic"
    SERVICE_START_MODE_MANUAL = "Manual"
    SERVICE_START_MODE_DISABLED = "Disabled"

    ComputerNamePhysicalDnsHostname = 5

    _config_key = 'SOFTWARE\\Cloudbase Solutions\\Cloudbase-Init\\'
    _service_name = 'cloudbase-init'

    _FW_IP_PROTOCOL_TCP = 6
    _FW_IP_PROTOCOL_UDP = 17
    _FW_SCOPE_ALL = 0
    _FW_SCOPE_LOCAL_SUBNET = 1

    def _enable_shutdown_privilege(self):
        process = win32process.GetCurrentProcess()
        token = win32security.OpenProcessToken(
            process,
            win32security.TOKEN_ADJUST_PRIVILEGES |
            win32security.TOKEN_QUERY)
        priv_luid = win32security.LookupPrivilegeValue(
            None, win32security.SE_SHUTDOWN_NAME)
        privilege = [(priv_luid, win32security.SE_PRIVILEGE_ENABLED)]
        win32security.AdjustTokenPrivileges(token, False, privilege)

    def reboot(self):
        self._enable_shutdown_privilege()

        ret_val = advapi32.InitiateSystemShutdownW(0, "Cloudbase-Init reboot",
                                                   0, True, True)
        if not ret_val:
            raise Exception("Reboot failed")

    def _get_user_wmi_object(self, username):
        conn = wmi.WMI(moniker='//./root/cimv2')
        username_san = self._sanitize_wmi_input(username)
        q = conn.query('SELECT * FROM Win32_Account where name = '
                       '\'%s\'' % username_san)
        if len(q) > 0:
            return q[0]
        return None

    def user_exists(self, username):
        return self._get_user_wmi_object(username) is not None

    def _create_or_change_user(self, username, password, create,
                               password_expires):
        username_san = self.sanitize_shell_input(username)
        password_san = self.sanitize_shell_input(password)

        args = ['NET', 'USER', username_san, password_san]
        if create:
            args.append('/ADD')

        (out, err, ret_val) = self.execute_process(args)
        if not ret_val:
            self._set_user_password_expiration(username, password_expires)
        else:
            if create:
                msg = "Create user failed: %s"
            else:
                msg = "Set user password failed: %s"
            raise Exception(msg % err)

    def _sanitize_wmi_input(self, value):
        return value.replace('\'', '\'\'')

    def _set_user_password_expiration(self, username, password_expires):
        r = self._get_user_wmi_object(username)
        if not r:
            return False
        r.PasswordExpires = password_expires
        r.Put_()
        return True

    def create_user(self, username, password, password_expires=False):
        self._create_or_change_user(username, password, True,
                                    password_expires)

    def set_user_password(self, username, password, password_expires=False):
        self._create_or_change_user(username, password, False,
                                    password_expires)

    def _get_user_sid_and_domain(self, username):
        sid = ctypes.create_string_buffer(1024)
        cbSid = wintypes.DWORD(ctypes.sizeof(sid))
        domainName = ctypes.create_unicode_buffer(1024)
        cchReferencedDomainName = wintypes.DWORD(
            ctypes.sizeof(domainName) / ctypes.sizeof(wintypes.WCHAR))
        sidNameUse = wintypes.DWORD()

        ret_val = advapi32.LookupAccountNameW(
            0, unicode(username), sid, ctypes.byref(cbSid), domainName,
            ctypes.byref(cchReferencedDomainName), ctypes.byref(sidNameUse))
        if not ret_val:
            raise Exception("Cannot get user SID")

        return (sid, domainName.value)

    def add_user_to_local_group(self, username, groupname):

        lmi = Win32_LOCALGROUP_MEMBERS_INFO_3()
        lmi.lgrmi3_domainandname = unicode(username)

        ret_val = netapi32.NetLocalGroupAddMembers(0, unicode(groupname), 3,
                                                   ctypes.addressof(lmi), 1)

        if ret_val == self.NERR_GroupNotFound:
            raise Exception('Group not found')
        elif ret_val == self.ERROR_ACCESS_DENIED:
            raise Exception('Access denied')
        elif ret_val == self.ERROR_NO_SUCH_MEMBER:
            raise Exception('Username not found')
        elif ret_val == self.ERROR_MEMBER_IN_ALIAS:
            # The user is already a member of the group
            pass
        elif ret_val == self.ERROR_INVALID_MEMBER:
            raise Exception('Invalid user')
        elif ret_val != 0:
            raise Exception('Unknown error')

    def get_user_sid(self, username):
        r = self._get_user_wmi_object(username)
        if not r:
            return None
        return r.SID

    def create_user_logon_session(self, username, password, domain='.',
                                  load_profile=True):
        token = wintypes.HANDLE()
        ret_val = advapi32.LogonUserW(unicode(username), unicode(domain),
                                      unicode(password), 2, 0,
                                      ctypes.byref(token))
        if not ret_val:
            raise Exception("User logon failed")

        if load_profile:
            pi = Win32_PROFILEINFO()
            pi.dwSize = ctypes.sizeof(Win32_PROFILEINFO)
            pi.lpUserName = unicode(username)
            ret_val = userenv.LoadUserProfileW(token, ctypes.byref(pi))
            if not ret_val:
                kernel32.CloseHandle(token)
                raise Exception("Cannot load user profile")

        return token

    def close_user_logon_session(self, token):
        kernel32.CloseHandle(token)

    def get_user_home(self, username):
        user_sid = self.get_user_sid(username)
        if user_sid:
            with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\'
                                 'Microsoft\\Windows NT\\CurrentVersion\\'
                                 'ProfileList\\%s' % user_sid) as key:
                return _winreg.QueryValueEx(key, 'ProfileImagePath')[0]
        LOG.debug('Home directory not found for user \'%s\'' % username)
        return None

    def sanitize_shell_input(self, value):
        return value.replace('"', '\\"')

    def set_host_name(self, new_host_name):
        ret_val = kernel32.SetComputerNameExW(
            self.ComputerNamePhysicalDnsHostname,
            unicode(new_host_name))
        if not ret_val:
            raise Exception("Cannot set host name")

    def get_network_adapters(self):
        l = []
        conn = wmi.WMI(moniker='//./root/cimv2')
        # Get Ethernet adapters only
        wql = ('SELECT * FROM Win32_NetworkAdapter WHERE '
               'AdapterTypeId = 0 AND MACAddress IS NOT NULL')

        if self.check_os_version(6, 0):
            wql += ' AND PhysicalAdapter = True'

        q = conn.query(wql)
        for r in q:
            l.append(r.Name)
        return l

    def get_dhcp_hosts_in_use(self):
        dhcp_hosts = []
        conn = wmi.WMI(moniker='//./root/cimv2')
        for net_cfg in conn.Win32_NetworkAdapterConfiguration(
                DHCPEnabled=True):
            if net_cfg.DHCPServer:
                dhcp_hosts.append(str(net_cfg.DHCPServer))
        return dhcp_hosts

    def set_ntp_client_config(self, ntp_host):
        if self.check_sysnative_dir_exists():
            base_dir = self.get_sysnative_dir()
        else:
            base_dir = self.get_system32_dir()

        w32tm_path = os.path.join(base_dir, "w32tm.exe")

        args = [w32tm_path, '/config', '/manualpeerlist:%s' % ntp_host,
                '/syncfromflags:manual', '/update']

        (out, err, ret_val) = self.execute_process(args, False)
        if ret_val:
            raise Exception('w32tm failed to configure NTP.\n'
                            'Output: %(out)s\nError: %(err)s' %
                            {'out': out, 'err': err})

    def set_static_network_config(self, adapter_name, address, netmask,
                                  broadcast, gateway, dnsnameservers):
        conn = wmi.WMI(moniker='//./root/cimv2')

        adapter_name_san = self._sanitize_wmi_input(adapter_name)
        q = conn.query('SELECT * FROM Win32_NetworkAdapter WHERE '
                       'MACAddress IS NOT NULL AND '
                       'Name = \'%s\'' % adapter_name_san)
        if not len(q):
            raise Exception("Network adapter not found")

        adapter_config = q[0].associators(
            wmi_result_class='Win32_NetworkAdapterConfiguration')[0]

        LOG.debug("Setting static IP address")
        (ret_val,) = adapter_config.EnableStatic([address], [netmask])
        if ret_val > 1:
            raise Exception("Cannot set static IP address on network adapter")
        reboot_required = (ret_val == 1)

        LOG.debug("Setting static gateways")
        (ret_val,) = adapter_config.SetGateways([gateway], [1])
        if ret_val > 1:
            raise Exception("Cannot set gateway on network adapter")
        reboot_required = reboot_required or ret_val == 1

        LOG.debug("Setting static DNS servers")
        (ret_val,) = adapter_config.SetDNSServerSearchOrder(dnsnameservers)
        if ret_val > 1:
            raise Exception("Cannot set DNS on network adapter")
        reboot_required = reboot_required or ret_val == 1

        return reboot_required

    def _get_config_key_name(self, section):
        key_name = self._config_key
        if section:
            key_name += section.replace('/', '\\') + '\\'
        return key_name

    def set_config_value(self, name, value, section=None):
        key_name = self._get_config_key_name(section)

        with _winreg.CreateKey(_winreg.HKEY_LOCAL_MACHINE,
                               key_name) as key:
            if type(value) == int:
                regtype = _winreg.REG_DWORD
            else:
                regtype = _winreg.REG_SZ
            _winreg.SetValueEx(key, name, 0, regtype, value)

    def get_config_value(self, name, section=None):
        key_name = self._get_config_key_name(section)

        try:
            with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                 key_name) as key:
                (value, regtype) = _winreg.QueryValueEx(key, name)
                return value
        except WindowsError:
            return None

    def wait_for_boot_completion(self):
        try:
            with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                 "SYSTEM\\Setup\\Status\\SysprepStatus", 0,
                                 _winreg.KEY_READ) as key:
                while True:
                    gen_state = _winreg.QueryValueEx(key,
                                                     "GeneralizationState")[0]
                    if gen_state == 7:
                        break
                    time.sleep(1)
                    LOG.info('Waiting for sysprep completion. '
                             'GeneralizationState: %d' % gen_state)
        except WindowsError, ex:
            if ex.winerror == 2:
                LOG.debug('Sysprep data not found in the registry, '
                          'skipping sysprep completion check.')
            else:
                raise ex

    def _get_service(self, service_name):
        conn = wmi.WMI(moniker='//./root/cimv2')
        service_list = conn.Win32_Service(Name=service_name)
        if len(service_list):
            return service_list[0]

    def check_service_exists(self, service_name):
        return self._get_service(service_name) is not None

    def get_service_status(self, service_name):
        service = self._get_service(service_name)
        return service.State

    def get_service_start_mode(self, service_name):
        service = self._get_service(service_name)
        return service.StartMode

    def set_service_start_mode(self, service_name, start_mode):
        #TODO(alexpilotti): Handle the "Delayed Start" case
        service = self._get_service(service_name)
        (ret_val,) = service.ChangeStartMode(start_mode)
        if ret_val != 0:
            raise Exception('Setting service %(service_name)s start mode '
                            'failed with return value: %(ret_val)d' %
                            {'service_name': service_name, 'ret_val': ret_val})

    def start_service(self, service_name):
        LOG.debug('Starting service %s' % service_name)
        service = self._get_service(service_name)
        (ret_val,) = service.StartService()
        if ret_val != 0:
            raise Exception('Starting service %(service_name)s failed with '
                            'return value: %(ret_val)d' %
                            {'service_name': service_name, 'ret_val': ret_val})

    def stop_service(self, service_name):
        LOG.debug('Stopping service %s' % service_name)
        service = self._get_service(service_name)
        (ret_val,) = service.StopService()
        if ret_val != 0:
            raise Exception('Stopping service %(service_name)s failed with '
                            'return value: %(ret_val)d' %
                            {'service_name': service_name, 'ret_val': ret_val})

    def terminate(self):
        # Wait for the service to start. Polling the service "Started" property
        # is not enough
        time.sleep(3)
        self.stop_service(self._service_name)

    def get_default_gateway(self):
        default_routes = [r for r in self._get_ipv4_routing_table()
                          if r[0] == '0.0.0.0']
        if default_routes:
            return (default_routes[0][3], default_routes[0][2])
        else:
            return (None, None)

    def _get_ipv4_routing_table(self):
        routing_table = []

        heap = kernel32.GetProcessHeap()

        size = wintypes.ULONG(ctypes.sizeof(Win32_MIB_IPFORWARDTABLE))
        p = kernel32.HeapAlloc(heap, 0, size)
        if not p:
            raise Exception('Unable to allocate memory for the IP forward '
                            'table')
        p_forward_table = ctypes.cast(
            p, ctypes.POINTER(Win32_MIB_IPFORWARDTABLE))

        try:
            err = iphlpapi.GetIpForwardTable(p_forward_table,
                                             ctypes.byref(size), 0)
            if err == self.ERROR_INSUFFICIENT_BUFFER:
                kernel32.HeapFree(heap, 0, p_forward_table)
                p = kernel32.HeapAlloc(heap, 0, size)
                if not p:
                    raise Exception('Unable to allocate memory for the IP '
                                    'forward table')
                p_forward_table = ctypes.cast(
                    p, ctypes.POINTER(Win32_MIB_IPFORWARDTABLE))

            err = iphlpapi.GetIpForwardTable(p_forward_table,
                                             ctypes.byref(size), 0)
            if err != self.ERROR_NO_DATA:
                if err:
                    raise Exception('Unable to get IP forward table. '
                                    'Error: %s' % err)

                forward_table = p_forward_table.contents
                table = ctypes.cast(
                    ctypes.addressof(forward_table.table),
                    ctypes.POINTER(Win32_MIB_IPFORWARDROW *
                                   forward_table.dwNumEntries)).contents

                i = 0
                while i < forward_table.dwNumEntries:
                    row = table[i]
                    routing_table.append((
                        Ws2_32.inet_ntoa(row.dwForwardDest),
                        Ws2_32.inet_ntoa(row.dwForwardMask),
                        Ws2_32.inet_ntoa(row.dwForwardNextHop),
                        row.dwForwardIfIndex,
                        row.dwForwardMetric1))
                    i += 1

            return routing_table
        finally:
            kernel32.HeapFree(heap, 0, p_forward_table)

    def check_static_route_exists(self, destination):
        return len([r for r in self._get_ipv4_routing_table()
                    if r[0] == destination]) > 0

    def add_static_route(self, destination, mask, next_hop, interface_index,
                         metric):
        args = ['ROUTE', 'ADD', destination, 'MASK', mask, next_hop]
        (out, err, ret_val) = self.execute_process(args)
        # Cannot use the return value to determine the outcome
        if ret_val or err:
            raise Exception('Unable to add route: %s' % err)

    def check_os_version(self, major, minor, build=0):
        vi = Win32_OSVERSIONINFOEX_W()
        vi.dwOSVersionInfoSize = ctypes.sizeof(Win32_OSVERSIONINFOEX_W)

        vi.dwMajorVersion = major
        vi.dwMinorVersion = minor
        vi.dwBuildNumber = build

        mask = 0
        for type_mask in [VER_MAJORVERSION, VER_MINORVERSION, VER_BUILDNUMBER]:
            mask = kernel32.VerSetConditionMask(mask, type_mask,
                                                VER_GREATER_EQUAL)

        type_mask = VER_MAJORVERSION | VER_MINORVERSION | VER_BUILDNUMBER
        ret_val = kernel32.VerifyVersionInfoW(ctypes.byref(vi), type_mask,
                                              mask)
        if ret_val:
            return True
        else:
            err = kernel32.GetLastError()
            if err == self.ERROR_OLD_WIN_VERSION:
                return False
            else:
                raise Exception("VerifyVersionInfo failed with error: %s" %
                                err)

    def get_volume_label(self, drive):
        max_label_size = 261
        label = ctypes.create_unicode_buffer(max_label_size)
        ret_val = kernel32.GetVolumeInformationW(unicode(drive), label,
                                                 max_label_size, 0, 0, 0, 0, 0)
        if ret_val:
            return label.value

    def generate_random_password(self, length):
        while True:
            pwd = super(WindowsUtils, self).generate_random_password(length)
            # Make sure that the Windows complexity requirements are met:
            # http://technet.microsoft.com/en-us/library/cc786468(v=ws.10).aspx
            valid = True
            for r in ["[a-z]", "[A-Z]", "[0-9]"]:
                if not re.search(r, pwd):
                    valid = False
            if valid:
                return pwd

    def _split_str_buf_list(self, buf, buf_len):
        i = 0
        value = ''
        values = []
        while i < buf_len:
            c = buf[i]
            if c != '\x00':
                value += c
            else:
                values.append(value)
                value = ''
            i += 1

        return values

    def _get_logical_drives(self):
        buf_size = self.MAX_PATH
        buf = ctypes.create_unicode_buffer(buf_size + 1)
        buf_len = kernel32.GetLogicalDriveStringsW(buf_size, buf)
        if not buf_len:
            raise Exception("GetLogicalDriveStringsW failed")

        return self._split_str_buf_list(buf, buf_len)

    def get_cdrom_drives(self):
        drives = self._get_logical_drives()
        return [d for d in drives if kernel32.GetDriveTypeW(d) ==
                self.DRIVE_CDROM]

    def get_physical_disks(self):
        physical_disks = []

        disk_guid = GUID_DEVINTERFACE_DISK
        handle_disks = setupapi.SetupDiGetClassDevsW(
            ctypes.byref(disk_guid), None, None,
            self.DIGCF_PRESENT | self.DIGCF_DEVICEINTERFACE)
        if handle_disks == self.INVALID_HANDLE_VALUE:
            raise Exception("SetupDiGetClassDevs failed")

        try:
            did = Win32_SP_DEVICE_INTERFACE_DATA()
            did.cbSize = ctypes.sizeof(Win32_SP_DEVICE_INTERFACE_DATA)

            index = 0
            while setupapi.SetupDiEnumDeviceInterfaces(
                    handle_disks, None, ctypes.byref(disk_guid), index,
                    ctypes.byref(did)):
                index += 1
                handle_disk = self.INVALID_HANDLE_VALUE

                required_size = wintypes.DWORD()
                if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                        handle_disks, ctypes.byref(did), None, 0,
                        ctypes.byref(required_size), None):
                    if (kernel32.GetLastError() !=
                            self.ERROR_INSUFFICIENT_BUFFER):
                        raise Exception("SetupDiGetDeviceInterfaceDetailW "
                                        "failed")

                pdidd = ctypes.cast(
                    msvcrt.malloc(required_size),
                    ctypes.POINTER(Win32_SP_DEVICE_INTERFACE_DETAIL_DATA_W))

                try:
                    # NOTE(alexpilotti): the size provided by ctypes.sizeof
                    # is not the expected one
                    #pdidd.contents.cbSize = ctypes.sizeof(
                    #    Win32_SP_DEVICE_INTERFACE_DETAIL_DATA_W)
                    pdidd.contents.cbSize = 6

                    if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                            handle_disks, ctypes.byref(did), pdidd,
                            required_size, None, None):
                        raise Exception("SetupDiGetDeviceInterfaceDetailW "
                                        "failed")

                    device_path = ctypes.cast(
                        pdidd.contents.DevicePath, wintypes.LPWSTR).value

                    handle_disk = kernel32.CreateFileW(
                        device_path, 0, self.FILE_SHARE_READ,
                        None, self.OPEN_EXISTING, 0, 0)
                    if handle_disk == self.INVALID_HANDLE_VALUE:
                        raise Exception('CreateFileW failed')

                    sdn = Win32_STORAGE_DEVICE_NUMBER()

                    b = wintypes.DWORD()
                    if not kernel32.DeviceIoControl(
                            handle_disk, self.IOCTL_STORAGE_GET_DEVICE_NUMBER,
                            None, 0, ctypes.byref(sdn), ctypes.sizeof(sdn),
                            ctypes.byref(b), None):
                        raise Exception('DeviceIoControl failed')

                    physical_disks.append(
                        r"\\.\PHYSICALDRIVE%d" % sdn.DeviceNumber)
                finally:
                    msvcrt.free(pdidd)
                    if handle_disk != self.INVALID_HANDLE_VALUE:
                        kernel32.CloseHandle(handle_disk)
        finally:
            setupapi.SetupDiDestroyDeviceInfoList(handle_disks)

        return physical_disks

    def _get_fw_protocol(self, protocol):
        if protocol == self.PROTOCOL_TCP:
            fw_protocol = self._FW_IP_PROTOCOL_TCP
        elif protocol == self.PROTOCOL_UDP:
            fw_protocol = self._FW_IP_PROTOCOL_UDP
        else:
            raise NotImplementedError("Unsupported protocol")
        return fw_protocol

    def firewall_create_rule(self, name, port, protocol, allow=True):
        if not allow:
            raise NotImplementedError()

        fw_port = client.Dispatch("HNetCfg.FWOpenPort")
        fw_port.Name = name
        fw_port.Protocol = self._get_fw_protocol(protocol)
        fw_port.Port = port
        fw_port.Scope = self._FW_SCOPE_ALL
        fw_port.Enabled = True

        fw_mgr = client.Dispatch("HNetCfg.FwMgr")
        fw_profile = fw_mgr.LocalPolicy.CurrentProfile
        fw_profile = fw_profile.GloballyOpenPorts.Add(fw_port)

    def firewall_remove_rule(self, name, port, protocol, allow=True):
        if not allow:
            raise NotImplementedError()

        fw_mgr = client.Dispatch("HNetCfg.FwMgr")
        fw_profile = fw_mgr.LocalPolicy.CurrentProfile

        fw_protocol = self._get_fw_protocol(protocol)
        fw_profile = fw_profile.GloballyOpenPorts.Remove(port, fw_protocol)

    def is_wow64(self):
        ret_val = wintypes.BOOL()
        if not kernel32.IsWow64Process(kernel32.GetCurrentProcess(),
                                       ctypes.byref(ret_val)):
            raise Exception("IsWow64Process failed")
        return bool(ret_val.value)

    def get_system32_dir(self):
        return os.path.expandvars('%windir%\\system32')

    def get_sysnative_dir(self):
        return os.path.expandvars('%windir%\\sysnative')

    def check_sysnative_dir_exists(self):
        sysnative_dir_exists = os.path.isdir(self.get_sysnative_dir())
        if not sysnative_dir_exists and self.is_wow64():
            LOG.warning('Unable to validate sysnative folder presence. '
                        'If Target OS is Server 2003 x64, please ensure '
                        'you have KB942589 installed')
        return sysnative_dir_exists

    def execute_powershell_script(self, script_path, sysnative=True):
        if sysnative and self.check_sysnative_dir_exists():
            base_dir = self.get_sysnative_dir()
        else:
            base_dir = self.get_system32_dir()

        powershell_path = os.path.join(base_dir,
                                       'WindowsPowerShell\\v1.0\\'
                                       'powershell.exe')

        args = [powershell_path, '-ExecutionPolicy', 'RemoteSigned',
                '-NonInteractive', '-File', script_path]

        return self.execute_process(args, False)

########NEW FILE########
__FILENAME__ = base
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

PLUGIN_EXECUTION_DONE = 1
PLUGIN_EXECUTE_ON_NEXT_BOOT = 2


class BasePlugin(object):
    def get_name(self):
        return self.__class__.__name__

    def get_os_requirements(self):
        return (None, None)

    def execute(self, service, shared_data):
        pass

########NEW FILE########
__FILENAME__ = constants
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

SHARED_DATA_USERNAME = "admin_user"
SHARED_DATA_PASSWORD = "admin_password"

########NEW FILE########
__FILENAME__ = factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

from oslo.config import cfg

from cloudbaseinit.utils import classloader

opts = [
    cfg.ListOpt(
        'plugins',
        default=[
            'cloudbaseinit.plugins.windows.ntpclient.NTPClientPlugin',
            'cloudbaseinit.plugins.windows.sethostname.SetHostNamePlugin',
            'cloudbaseinit.plugins.windows.createuser.CreateUserPlugin',
            'cloudbaseinit.plugins.windows.networkconfig.NetworkConfigPlugin',
            'cloudbaseinit.plugins.windows.licensing.WindowsLicensingPlugin',
            'cloudbaseinit.plugins.windows.sshpublickeys.'
            'SetUserSSHPublicKeysPlugin',
            'cloudbaseinit.plugins.windows.extendvolumes.ExtendVolumesPlugin',
            'cloudbaseinit.plugins.windows.userdata.UserDataPlugin',
            'cloudbaseinit.plugins.windows.setuserpassword.'
            'SetUserPasswordPlugin',
            'cloudbaseinit.plugins.windows.winrmlistener.'
            'ConfigWinRMListenerPlugin',
            'cloudbaseinit.plugins.windows.winrmcertificateauth.'
            'ConfigWinRMCertificateAuthPlugin',
        ],
        help='List of enabled plugin classes, '
        'to executed in the provided order'),
]

CONF = cfg.CONF
CONF.register_opts(opts)


def load_plugins():
    plugins = []
    cl = classloader.ClassLoader()
    for class_path in CONF.plugins:
        plugins.append(cl.load_class(class_path)())
    return plugins

########NEW FILE########
__FILENAME__ = createuser
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins import constants

opts = [
    cfg.StrOpt('username', default='Admin', help='User to be added to the '
               'system or updated if already existing'),
    cfg.ListOpt('groups', default=['Administrators'], help='List of local '
                'groups to which the user specified in \'username\' will '
                'be added'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class CreateUserPlugin(base.BasePlugin):
    def _get_password(self, osutils):
        # Generate a temporary random password to be replaced
        # by SetUserPasswordPlugin (starting from Grizzly)
        return osutils.generate_random_password(14)

    def execute(self, service, shared_data):
        user_name = CONF.username
        shared_data[constants.SHARED_DATA_USERNAME] = user_name

        osutils = osutils_factory.get_os_utils()
        password = self._get_password(osutils)

        if osutils.user_exists(user_name):
            LOG.info('Setting password for existing user "%s"' % user_name)
            osutils.set_user_password(user_name, password)
        else:
            LOG.info('Creating user "%s" and setting password' % user_name)
            osutils.create_user(user_name, password)
            # Create a user profile in order for other plugins
            # to access the user home, etc
            token = osutils.create_user_logon_session(user_name,
                                                      password,
                                                      True)
            osutils.close_user_logon_session(token)

            # TODO(alexpilotti): encrypt with DPAPI
            shared_data[constants.SHARED_DATA_PASSWORD] = password

        for group_name in CONF.groups:
            try:
                osutils.add_user_to_local_group(user_name, group_name)
            except Exception as ex:
                LOG.exception(ex)
                LOG.error('Cannot add user to group "%s"' % group_name)

        return (base.PLUGIN_EXECUTION_DONE, False)

########NEW FILE########
__FILENAME__ = extendvolumes
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Cloudbase Solutions Srl
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

import ctypes
import re

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins import base
from cloudbaseinit.utils.windows import vds

ole32 = ctypes.windll.ole32
ole32.CoTaskMemFree.restype = None
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]

opts = [
    cfg.ListOpt('volumes_to_extend',
                default=None,
                help='List of volumes that need to be extended '
                'if contiguous space is available on the disk. By default '
                'all the available volumes can be extended. Volumes must '
                'be specified using a comma separated list of volume indexes, '
                'e.g.: "1,2"'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class ExtendVolumesPlugin(base.BasePlugin):
    def _extend_volumes(self, pack, volume_idxs=None):
        enum = pack.QueryVolumes()
        while True:
            (unk, c) = enum.Next(1)
            if not c:
                break
            volume = unk.QueryInterface(vds.IVdsVolume)
            volume_prop = volume.GetProperties()
            try:
                extend_volume = True
                if volume_idxs is not None:
                    volume_name = ctypes.wstring_at(volume_prop.pwszName)
                    volume_idx = self._get_volume_index(volume_name)
                    if not volume_idx in volume_idxs:
                        extend_volume = False

                if extend_volume:
                    self._extend_volume(pack, volume, volume_prop)
            finally:
                ole32.CoTaskMemFree(volume_prop.pwszName)

    def _get_volume_index(self, volume_name):
        m = re.match(r"[^0-9]+([0-9]+)$", volume_name)
        if m:
            return int(m.group(1))

    def _extend_volume(self, pack, volume, volume_prop):
        volume_extents = self._get_volume_extents_to_resize(pack,
                                                            volume_prop.id)
        input_disks = []

        for (volume_extent, volume_extend_size) in volume_extents:
            input_disk = vds.VDS_INPUT_DISK()
            input_disks.append(input_disk)

            input_disk.diskId = volume_extent.diskId
            input_disk.memberIdx = volume_extent.memberIdx
            input_disk.plexId = volume_extent.plexId
            input_disk.ullSize = volume_extend_size

        if input_disks:
            extend_size = sum([i.ullSize for i in input_disks])
            volume_name = ctypes.wstring_at(volume_prop.pwszName)
            LOG.info('Extending volume "%s" with %s bytes' %
                     (volume_name, extend_size))

            input_disks_ar = (vds.VDS_INPUT_DISK *
                              len(input_disks))(*input_disks)
            async = volume.Extend(input_disks_ar, len(input_disks))
            async.Wait()

    def _get_volume_extents_to_resize(self, pack, volume_id):
        volume_extents = []

        enum = pack.QueryDisks()
        while True:
            (unk, c) = enum.Next(1)
            if not c:
                break
            disk = unk.QueryInterface(vds.IVdsDisk)

            (extents_p, num_extents) = disk.QueryExtents()
            try:
                extents_array_type = vds.VDS_DISK_EXTENT * num_extents
                extents_array = extents_array_type.from_address(
                    ctypes.addressof(extents_p.contents))

                volume_extent_extend_size = None

                for extent in extents_array:
                    if extent.volumeId == volume_id:
                        # Copy the extent in order to return it safely
                        # after the source is deallocated
                        extent_copy = vds.VDS_DISK_EXTENT()
                        ctypes.pointer(extent_copy)[0] = extent

                        volume_extent_extend_size = [extent_copy, 0]
                        volume_extents.append(volume_extent_extend_size)
                    elif (volume_extent_extend_size and
                          extent.type == vds.VDS_DET_FREE):
                        volume_extent_extend_size[1] += extent.ullSize
                    else:
                        volume_extent_extend_size = None
            finally:
                ole32.CoTaskMemFree(extents_p)

        # Return only the extents that need to be resized
        return [ve for ve in volume_extents if ve[1] > 0]

    def _query_providers(self, svc):
        providers = []
        enum = svc.QueryProviders(vds.VDS_QUERY_SOFTWARE_PROVIDERS)
        while True:
            (unk, c) = enum.Next(1)
            if not c:
                break
            providers.append(unk.QueryInterface(vds.IVdsSwProvider))
        return providers

    def _query_packs(self, provider):
        packs = []
        enum = provider.QueryPacks()
        while True:
            (unk, c) = enum.Next(1)
            if not c:
                break
            packs.append(unk.QueryInterface(vds.IVdsPack))
        return packs

    def _get_volumes_to_extend(self):
        if CONF.volumes_to_extend is not None:
            return map(int, CONF.volumes_to_extend)

    def execute(self, service, shared_data):
        svc = vds.load_vds_service()
        providers = self._query_providers(svc)

        volumes_to_extend = self._get_volumes_to_extend()

        for provider in providers:
            packs = self._query_packs(provider)
            for pack in packs:
                self._extend_volumes(pack, volumes_to_extend)

        return (base.PLUGIN_EXECUTE_ON_NEXT_BOOT, False)

    def get_os_requirements(self):
        return ('win32', (5, 2))

########NEW FILE########
__FILENAME__ = licensing
# Copyright 2014 Cloudbase Solutions Srl
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

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base

opts = [
    cfg.BoolOpt('activate_windows', default=False,
                help='Activates Windows automatically'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class WindowsLicensingPlugin(base.BasePlugin):
    def _run_slmgr(self, osutils, args):
        if osutils.check_sysnative_dir_exists():
            cscript_dir = osutils.get_sysnative_dir()
        else:
            cscript_dir = osutils.get_system32_dir()

        # Not SYSNATIVE, as it is already executed by a x64 process
        slmgr_dir = osutils.get_system32_dir()

        cscript_path = os.path.join(cscript_dir, "cscript.exe")
        slmgr_path = os.path.join(slmgr_dir, "slmgr.vbs")

        (out, err, exit_code) = osutils.execute_process(
            [cscript_path, slmgr_path] + args, False)

        if exit_code:
            raise Exception('slmgr.vbs failed with error code %(exit_code)s.\n'
                            'Output: %(out)s\nError: %(err)s' %
                            {'exit_code': exit_code, 'out': out, 'err': err})
        return out

    def execute(self, service, shared_data):
        osutils = osutils_factory.get_os_utils()

        license_info = self._run_slmgr(osutils, ['/dlv'])
        LOG.info('Microsoft Windows license info:\n%s' % license_info)

        if CONF.activate_windows:
            LOG.info("Activating Windows")
            activation_result = self._run_slmgr(osutils, ['/ato'])
            LOG.debug("Activation result:\n%s" % activation_result)

        return (base.PLUGIN_EXECUTION_DONE, False)

########NEW FILE########
__FILENAME__ = networkconfig
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import re

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base

LOG = logging.getLogger(__name__)

opts = [
    cfg.StrOpt('network_adapter', default=None, help='Network adapter to '
               'configure. If not specified, the first available ethernet '
               'adapter will be chosen'),
]

CONF = cfg.CONF
CONF.register_opts(opts)


class NetworkConfigPlugin(base.BasePlugin):
    def execute(self, service, shared_data):
        network_config = service.get_network_config()
        if not network_config:
            return (base.PLUGIN_EXECUTION_DONE, False)

        if 'content_path' not in network_config:
            return (base.PLUGIN_EXECUTION_DONE, False)

        content_path = network_config['content_path']
        content_name = content_path.rsplit('/', 1)[-1]
        debian_network_conf = service.get_content(content_name)

        LOG.debug('network config content:\n%s' % debian_network_conf)

        # TODO (alexpilotti): implement a proper grammar
        m = re.search(r'iface eth0 inet static\s+'
                      r'address\s+(?P<address>[^\s]+)\s+'
                      r'netmask\s+(?P<netmask>[^\s]+)\s+'
                      r'broadcast\s+(?P<broadcast>[^\s]+)\s+'
                      r'gateway\s+(?P<gateway>[^\s]+)\s+'
                      r'dns\-nameservers\s+(?P<dnsnameservers>[^\r\n]+)\s+',
                      debian_network_conf)
        if not m:
            raise Exception("network_config format not recognized")

        address = m.group('address')
        netmask = m.group('netmask')
        broadcast = m.group('broadcast')
        gateway = m.group('gateway')
        dnsnameservers = m.group('dnsnameservers').strip().split(' ')

        osutils = osutils_factory.get_os_utils()

        network_adapter_name = CONF.network_adapter
        if not network_adapter_name:
            # Get the first available one
            available_adapters = osutils.get_network_adapters()
            if not len(available_adapters):
                raise Exception("No network adapter available")
            network_adapter_name = available_adapters[0]

        LOG.info('Configuring network adapter: \'%s\'' % network_adapter_name)

        reboot_required = osutils.set_static_network_config(
            network_adapter_name, address, netmask, broadcast,
            gateway, dnsnameservers)

        return (base.PLUGIN_EXECUTION_DONE, reboot_required)

########NEW FILE########
__FILENAME__ = ntpclient
# Copyright 2014 Cloudbase Solutions Srl
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

import socket
import time

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base
from cloudbaseinit.utils import dhcp

opts = [
    cfg.BoolOpt('ntp_use_dhcp_config', default=False,
                help='Configures NTP client time synchronization using '
                     'the NTP servers provided via DHCP'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class NTPClientPlugin(base.BasePlugin):
    def _check_w32time_svc_status(self, osutils):
        _W32TIME_SERVICE = "w32time"

        svc_start_mode = osutils.get_service_start_mode(
            _W32TIME_SERVICE)

        if svc_start_mode != osutils.SERVICE_START_MODE_AUTOMATIC:
            osutils.set_service_start_mode(
                _W32TIME_SERVICE,
                osutils.SERVICE_START_MODE_AUTOMATIC)

        svc_status = osutils.get_service_status(_W32TIME_SERVICE)
        if svc_status == osutils.SERVICE_STATUS_STOPPED:
            osutils.start_service(_W32TIME_SERVICE)

            i = 0
            max_retries = 30
            while svc_status != osutils.SERVICE_STATUS_RUNNING:
                if i >= max_retries:
                    raise Exception('Service %s did not start' %
                                    _W32TIME_SERVICE)
                time.sleep(1)
                svc_status = osutils.get_service_status(_W32TIME_SERVICE)
                i += 1

    def execute(self, service, shared_data):
        if CONF.ntp_use_dhcp_config:
            osutils = osutils_factory.get_os_utils()
            dhcp_hosts = osutils.get_dhcp_hosts_in_use()

            ntp_option_data = None

            for dhcp_host in dhcp_hosts:
                options_data = dhcp.get_dhcp_options(dhcp_host,
                                                     [dhcp.OPTION_NTP_SERVERS])
                if options_data:
                    ntp_option_data = options_data.get(dhcp.OPTION_NTP_SERVERS)
                    if ntp_option_data:
                        break

            if not ntp_option_data:
                LOG.debug("Could not obtain the NTP configuration via DHCP")
                return (base.PLUGIN_EXECUTE_ON_NEXT_BOOT, False)

            # TODO(alexpilotti): support multiple NTP servers
            ntp_host = socket.inet_ntoa(ntp_option_data[:4])

            self._check_w32time_svc_status(osutils)
            osutils.set_ntp_client_config(ntp_host)

            LOG.info('NTP client configured. Server: %s' % ntp_host)

        return (base.PLUGIN_EXECUTION_DONE, False)

########NEW FILE########
__FILENAME__ = sethostname
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import platform

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base

opts = [
    cfg.BoolOpt('netbios_host_name_compatibility', default=True,
                help='Truncates the hostname to 15 characters for Netbios '
                     'compatibility'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)

NETBIOS_HOST_NAME_MAX_LEN = 15


class SetHostNamePlugin(base.BasePlugin):
    def execute(self, service, shared_data):
        osutils = osutils_factory.get_os_utils()

        metadata_host_name = service.get_host_name()
        if not metadata_host_name:
            LOG.debug('Hostname not found in metadata')
            return (base.PLUGIN_EXECUTION_DONE, False)

        metadata_host_name = metadata_host_name.split('.', 1)[0]

        if (len(metadata_host_name) > NETBIOS_HOST_NAME_MAX_LEN and
                CONF.netbios_host_name_compatibility):
            new_host_name = metadata_host_name[:NETBIOS_HOST_NAME_MAX_LEN]
            LOG.warn('Truncating host name for Netbios compatibility. '
                     'Old name: %(metadata_host_name)s, new name: '
                     '%(new_host_name)s' %
                     {'metadata_host_name': metadata_host_name,
                      'new_host_name': new_host_name})
        else:
            new_host_name = metadata_host_name

        if platform.node().lower() == new_host_name.lower():
            LOG.debug("Hostname already set to: %s" % new_host_name)
            reboot_required = False
        else:
            LOG.info("Setting hostname: %s" % new_host_name)
            osutils.set_host_name(new_host_name)
            reboot_required = True

        return (base.PLUGIN_EXECUTION_DONE, reboot_required)

########NEW FILE########
__FILENAME__ = setuserpassword
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins import constants
from cloudbaseinit.utils import crypt

opts = [
    cfg.BoolOpt('inject_user_password', default=True, help='Set the password '
                'provided in the configuration. If False or no password is '
                'provided, a random one will be set'),
]

CONF = cfg.CONF
CONF.register_opts(opts)
CONF.import_opt('username', 'cloudbaseinit.plugins.windows.createuser')

LOG = logging.getLogger(__name__)


class SetUserPasswordPlugin(base.BasePlugin):
    def _encrypt_password(self, ssh_pub_key, password):
        cm = crypt.CryptManager()
        with cm.load_ssh_rsa_public_key(ssh_pub_key) as rsa:
            enc_password = rsa.public_encrypt(password)
        return base64.b64encode(enc_password)

    def _get_ssh_public_key(self, service):
        public_keys = service.get_public_keys()
        if public_keys:
            return public_keys[0]

    def _get_password(self, service, osutils):
        if CONF.inject_user_password:
            password = service.get_admin_password()
        else:
            password = None

        if password:
            LOG.warn('Using admin_pass metadata user password. Consider '
                     'changing it as soon as possible')
        else:
            # TODO(alexpilotti): setting a random password can be skipped
            # if it's already present in the shared_data, as it has already
            # been set by the CreateUserPlugin
            LOG.debug('Generating a random user password')
            # Generate a random password
            # Limit to 14 chars for compatibility with NT
            password = osutils.generate_random_password(14)

        return password

    def _set_metadata_password(self, password, service):
        ssh_pub_key = self._get_ssh_public_key(service)
        if ssh_pub_key:
            enc_password_b64 = self._encrypt_password(ssh_pub_key,
                                                      password)
            return service.post_password(enc_password_b64)
        else:
            LOG.info('No SSH public key available for password encryption')
            return True

    def _set_password(self, service, osutils, user_name):
        password = self._get_password(service, osutils)
        LOG.info('Setting the user\'s password')
        osutils.set_user_password(user_name, password)
        return password

    def execute(self, service, shared_data):
        # TODO(alexpilotti): The username selection logic must be set in the
        # CreateUserPlugin instead if using CONF.username
        user_name = shared_data.get(constants.SHARED_DATA_USERNAME,
                                    CONF.username)

        if service.can_post_password and service.is_password_set:
            LOG.debug('User\'s password already set in the instance metadata')
        else:
            osutils = osutils_factory.get_os_utils()
            if osutils.user_exists(user_name):
                password = self._set_password(service, osutils, user_name)
                # TODO(alexpilotti): encrypt with DPAPI
                shared_data[constants.SHARED_DATA_PASSWORD] = password

                if not service.can_post_password:
                    LOG.info('Cannot set the password in the metadata as it '
                             'is not supported by this service')
                    return (base.PLUGIN_EXECUTION_DONE, False)
                else:
                    self._set_metadata_password(password, service)

        return (base.PLUGIN_EXECUTE_ON_NEXT_BOOT, False)

########NEW FILE########
__FILENAME__ = sshpublickeys
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base

CONF = cfg.CONF
CONF.import_opt('username', 'cloudbaseinit.plugins.windows.createuser')
LOG = logging.getLogger(__name__)


class SetUserSSHPublicKeysPlugin(base.BasePlugin):
    def execute(self, service, shared_data):
        public_keys = service.get_public_keys()
        if not public_keys:
            LOG.debug('Public keys not found in metadata')
            return (base.PLUGIN_EXECUTION_DONE, False)

        username = CONF.username

        osutils = osutils_factory.get_os_utils()
        user_home = osutils.get_user_home(username)

        if not user_home:
            raise Exception("User profile not found!")

        LOG.debug("User home: %s" % user_home)

        user_ssh_dir = os.path.join(user_home, '.ssh')
        if not os.path.exists(user_ssh_dir):
            os.makedirs(user_ssh_dir)

        authorized_keys_path = os.path.join(user_ssh_dir, "authorized_keys")
        LOG.info("Writing SSH public keys in: %s" % authorized_keys_path)
        with open(authorized_keys_path, 'w') as f:
            for public_key in public_keys:
                f.write(public_key)

        return (base.PLUGIN_EXECUTION_DONE, False)

########NEW FILE########
__FILENAME__ = userdata
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import email
import gzip
import StringIO

from cloudbaseinit.metadata.services import base as metadata_services_base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import userdatautils
from cloudbaseinit.plugins.windows.userdataplugins import factory

LOG = logging.getLogger(__name__)


class UserDataPlugin(base.BasePlugin):
    _PART_HANDLER_CONTENT_TYPE = "text/part-handler"
    _GZIP_MAGIC_NUMBER = '\x1f\x8b'

    def execute(self, service, shared_data):
        try:
            user_data = service.get_user_data()
        except metadata_services_base.NotExistingMetadataException:
            return (base.PLUGIN_EXECUTION_DONE, False)

        if not user_data:
            return (base.PLUGIN_EXECUTION_DONE, False)

        user_data = self._check_gzip_compression(user_data)

        return self._process_user_data(user_data)

    def _check_gzip_compression(self, user_data):
        if user_data[:2] == self._GZIP_MAGIC_NUMBER:
            sio = StringIO.StringIO(user_data)
            with gzip.GzipFile(fileobj=sio, mode='rb') as f:
                user_data = f.read()

        return user_data

    def _parse_mime(self, user_data):
        return email.message_from_string(user_data).walk()

    def _process_user_data(self, user_data):
        plugin_status = base.PLUGIN_EXECUTION_DONE
        reboot = False

        LOG.debug('User data content:\n%s' % user_data)
        if user_data.startswith('Content-Type: multipart'):
            user_data_plugins = factory.load_plugins()
            user_handlers = {}

            for part in self._parse_mime(user_data):
                (plugin_status, reboot) = self._process_part(part,
                                                             user_data_plugins,
                                                             user_handlers)
                if reboot:
                    break

            if not reboot:
                for handler_func in list(set(user_handlers.values())):
                    self._end_part_process_event(handler_func)

            return (plugin_status, reboot)
        else:
            return self._process_non_multi_part(user_data)

    def _process_part(self, part, user_data_plugins, user_handlers):
        ret_val = None
        try:
            content_type = part.get_content_type()

            handler_func = user_handlers.get(content_type)
            if handler_func:
                LOG.debug("Calling user part handler for content type: %s" %
                          content_type)
                handler_func(None, content_type, part.get_filename(),
                             part.get_payload())
            else:
                user_data_plugin = user_data_plugins.get(content_type)
                if not user_data_plugin:
                    LOG.info("Userdata plugin not found for content type: %s" %
                             content_type)
                else:
                    LOG.debug("Executing userdata plugin: %s" %
                              user_data_plugin.__class__.__name__)

                    if content_type == self._PART_HANDLER_CONTENT_TYPE:
                        new_user_handlers = user_data_plugin.process(part)
                        self._add_part_handlers(user_data_plugins,
                                                user_handlers,
                                                new_user_handlers)
                    else:
                        ret_val = user_data_plugin.process(part)
        except Exception, ex:
            LOG.error('Exception during multipart part handling: '
                      '%(content_type)s, %(filename)s' %
                      {'content_type': part.get_content_type(),
                       'filename': part.get_filename()})
            LOG.exception(ex)

        return self._get_plugin_return_value(ret_val)

    def _add_part_handlers(self, user_data_plugins, user_handlers,
                           new_user_handlers):
        handler_funcs = set()

        for (content_type,
             handler_func) in new_user_handlers.items():
            if not user_data_plugins.get(content_type):
                LOG.info("Adding part handler for content "
                         "type: %s" % content_type)
                user_handlers[content_type] = handler_func
                handler_funcs.add(handler_func)
            else:
                LOG.info("Skipping part handler for content type \"%s\" as it "
                         "is already managed by a plugin" % content_type)

        for handler_func in handler_funcs:
            self._begin_part_process_event(handler_func)

    def _begin_part_process_event(self, handler_func):
        LOG.debug("Calling part handler \"__begin__\" event")
        handler_func(None, "__begin__", None, None)

    def _end_part_process_event(self, handler_func):
        LOG.debug("Calling part handler \"__end__\" event")
        handler_func(None, "__end__", None, None)

    def _get_plugin_return_value(self, ret_val):
        plugin_status = base.PLUGIN_EXECUTION_DONE
        reboot = False

        if ret_val >= 1001 and ret_val <= 1003:
            reboot = bool(ret_val & 1)
            if ret_val & 2:
                plugin_status = base.PLUGIN_EXECUTE_ON_NEXT_BOOT

        return (plugin_status, reboot)

    def _process_non_multi_part(self, user_data):
        ret_val = userdatautils.execute_user_data_script(user_data)
        return self._get_plugin_return_value(ret_val)

########NEW FILE########
__FILENAME__ = base
# Copyright 2014 Cloudbase Solutions Srl
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

import abc


class BaseUserDataPlugin(object):
    def __init__(self, mime_type):
        self._mime_type = mime_type

    def get_mime_type(self):
        return self._mime_type

    @abc.abstractmethod
    def process(self, part):
        pass

########NEW FILE########
__FILENAME__ = cloudboothook
# Copyright 2014 Cloudbase Solutions Srl
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

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins.windows.userdataplugins import base

LOG = logging.getLogger(__name__)


class CloudBootHookPlugin(base.BaseUserDataPlugin):
    def __init__(self):
        super(CloudBootHookPlugin, self).__init__("text/cloud-boothook")

    def process(self, part):
        LOG.info("%s content is currently not supported" %
                 self.get_mime_type())

########NEW FILE########
__FILENAME__ = cloudconfig
# Copyright 2013 Mirantis Inc.
# Copyright 2014 Cloudbase Solutions Srl
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

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins.windows.userdataplugins import base

LOG = logging.getLogger(__name__)


class CloudConfigPlugin(base.BaseUserDataPlugin):
    def __init__(self):
        super(CloudConfigPlugin, self).__init__("text/cloud-config")

    def process(self, part):
        LOG.info("%s content is currently not supported" %
                 self.get_mime_type())

########NEW FILE########
__FILENAME__ = factory
# Copyright 2014 Cloudbase Solutions Srl
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

from oslo.config import cfg

from cloudbaseinit.utils import classloader

opts = [
    cfg.ListOpt(
        'user_data_plugins',
        default=[
            'cloudbaseinit.plugins.windows.userdataplugins.parthandler.'
            'PartHandlerPlugin',
            'cloudbaseinit.plugins.windows.userdataplugins.cloudconfig.'
            'CloudConfigPlugin',
            'cloudbaseinit.plugins.windows.userdataplugins.cloudboothook.'
            'CloudBootHookPlugin',
            'cloudbaseinit.plugins.windows.userdataplugins.shellscript.'
            'ShellScriptPlugin',
            'cloudbaseinit.plugins.windows.userdataplugins.multipartmixed.'
            'MultipartMixedPlugin',
            'cloudbaseinit.plugins.windows.userdataplugins.heat.'
            'HeatPlugin',
        ],
        help='List of enabled userdata content plugins'),
]

CONF = cfg.CONF
CONF.register_opts(opts)


def load_plugins():
    plugins = {}
    cl = classloader.ClassLoader()
    for class_path in CONF.user_data_plugins:
        plugin = cl.load_class(class_path)()
        plugins[plugin.get_mime_type()] = plugin
    return plugins

########NEW FILE########
__FILENAME__ = heat
# Copyright 2013 Mirantis Inc.
# Copyright 2014 Cloudbase Solutions Srl
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

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins.windows.userdataplugins import base
from cloudbaseinit.plugins.windows import userdatautils

opts = [
    cfg.StrOpt('heat_config_dir', default='C:\\cfn', help='The directory '
               'where the Heat configuration files must be saved'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class HeatPlugin(base.BaseUserDataPlugin):
    _heat_user_data_filename = "cfn-userdata"

    def __init__(self):
        super(HeatPlugin, self).__init__("text/x-cfninitdata")

    def _check_heat_config_dir(self):
        if not os.path.exists(CONF.heat_config_dir):
            os.makedirs(CONF.heat_config_dir)

    def process(self, part):
        self._check_heat_config_dir()

        file_name = os.path.join(CONF.heat_config_dir, part.get_filename())
        with open(file_name, 'wb') as f:
            f.write(part.get_payload())

        if part.get_filename() == self._heat_user_data_filename:
            return userdatautils.execute_user_data_script(part.get_payload())

########NEW FILE########
__FILENAME__ = multipartmixed
# Copyright 2014 Cloudbase Solutions Srl
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

from cloudbaseinit.plugins.windows.userdataplugins import base


class MultipartMixedPlugin(base.BaseUserDataPlugin):
    def __init__(self):
        super(MultipartMixedPlugin, self).__init__("multipart/mixed")

    def process(self, part):
        pass

########NEW FILE########
__FILENAME__ = parthandler
# Copyright 2013 Mirantis Inc.
# Copyright 2014 Cloudbase Solutions Srl
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
import tempfile

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins.windows.userdataplugins import base
from cloudbaseinit.utils import classloader

LOG = logging.getLogger(__name__)


class PartHandlerPlugin(base.BaseUserDataPlugin):
    def __init__(self):
        super(PartHandlerPlugin, self).__init__("text/part-handler")

    def process(self, part):
        temp_dir = tempfile.gettempdir()
        part_handler_path = os.path.join(temp_dir, part.get_filename())

        with open(part_handler_path, "wb") as f:
            f.write(part.get_payload())

        part_handler = classloader.ClassLoader().load_module(part_handler_path)

        if (part_handler and
                hasattr(part_handler, "list_types") and
                hasattr(part_handler, "handle_part")):
            part_handlers_dict = {}
            for handled_type in part_handler.list_types():
                part_handlers_dict[handled_type] = part_handler.handle_part
            return part_handlers_dict

########NEW FILE########
__FILENAME__ = shellscript
# Copyright 2013 Mirantis Inc.
# Copyright 2014 Cloudbase Solutions Srl
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

import tempfile
import os

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins.windows.userdataplugins import base

LOG = logging.getLogger(__name__)


class ShellScriptPlugin(base.BaseUserDataPlugin):
    def __init__(self):
        super(ShellScriptPlugin, self).__init__("text/x-shellscript")

    def process(self, part):
        osutils = osutils_factory.get_os_utils()

        file_name = part.get_filename()
        target_path = os.path.join(tempfile.gettempdir(), file_name)

        shell = False
        powershell = False

        if file_name.endswith(".cmd"):
            args = [target_path]
            shell = True
        elif file_name.endswith(".sh"):
            args = ['bash.exe', target_path]
        elif file_name.endswith(".py"):
            args = ['python.exe', target_path]
        elif file_name.endswith(".ps1"):
            powershell = True
        else:
            # Unsupported
            LOG.warning('Unsupported script type')
            return 0

        try:
            with open(target_path, 'wb') as f:
                f.write(part.get_payload())

            if powershell:
                (out, err,
                 ret_val) = osutils.execute_powershell_script(target_path)
            else:
                (out, err, ret_val) = osutils.execute_process(args, shell)

            LOG.info('User_data script ended with return code: %d' % ret_val)
            LOG.debug('User_data stdout:\n%s' % out)
            LOG.debug('User_data stderr:\n%s' % err)

            return ret_val
        except Exception, ex:
            LOG.warning('An error occurred during user_data execution: \'%s\''
                        % ex)
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)

########NEW FILE########
__FILENAME__ = userdatautils
# Copyright 2014 Cloudbase Solutions Srl
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
import re
import tempfile
import uuid

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory

LOG = logging.getLogger(__name__)


def execute_user_data_script(user_data):
    osutils = osutils_factory.get_os_utils()

    shell = False
    powershell = False
    sysnative = True

    target_path = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
    if re.search(r'^rem cmd\s', user_data, re.I):
        target_path += '.cmd'
        args = [target_path]
        shell = True
    elif re.search(r'^#!/usr/bin/env\spython\s', user_data, re.I):
        target_path += '.py'
        args = ['python.exe', target_path]
    elif re.search(r'^#!', user_data, re.I):
        target_path += '.sh'
        args = ['bash.exe', target_path]
    elif re.search(r'^#(ps1|ps1_sysnative)\s', user_data, re.I):
        target_path += '.ps1'
        powershell = True
    elif re.search(r'^#ps1_x86\s', user_data, re.I):
        target_path += '.ps1'
        powershell = True
        sysnative = False
    else:
        # Unsupported
        LOG.warning('Unsupported user_data format')
        return 0

    try:
        with open(target_path, 'wb') as f:
            f.write(user_data)

        if powershell:
            (out, err,
             ret_val) = osutils.execute_powershell_script(target_path,
                                                          sysnative)
        else:
            (out, err, ret_val) = osutils.execute_process(args, shell)

        LOG.info('User_data script ended with return code: %d' % ret_val)
        LOG.debug('User_data stdout:\n%s' % out)
        LOG.debug('User_data stderr:\n%s' % err)

        return ret_val
    except Exception, ex:
        LOG.warning('An error occurred during user_data execution: \'%s\''
                    % ex)
    finally:
        if os.path.exists(target_path):
            os.remove(target_path)

########NEW FILE########
__FILENAME__ = winrmcertificateauth
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins import constants
from cloudbaseinit.utils.windows import winrmconfig
from cloudbaseinit.utils.windows import x509

LOG = logging.getLogger(__name__)


class ConfigWinRMCertificateAuthPlugin(base.BasePlugin):
    def _get_credentials(self, shared_data):
        user_name = shared_data.get(constants.SHARED_DATA_USERNAME)
        if not user_name:
            raise Exception("Cannot execute plugin as the username has "
                            "not been set in the plugins shared data")

        password = shared_data.get(constants.SHARED_DATA_PASSWORD)
        if not password:
            raise Exception("Cannot execute plugin as the password has "
                            "not been set in the plugins shared data")

        # For security reasons unset the password in the shared_data
        # as it is currently not needed by other plugins
        shared_data[constants.SHARED_DATA_PASSWORD] = None

        return (user_name, password)

    def execute(self, service, shared_data):
        user_name, password = self._get_credentials(shared_data)

        certs_data = service.get_client_auth_certs()
        if not certs_data:
            LOG.info("WinRM certificate authentication cannot be configured "
                     "as a certificate has not been provided in the metadata")
            return (base.PLUGIN_EXECUTION_DONE, False)

        winrm_config = winrmconfig.WinRMConfig()
        winrm_config.set_auth_config(certificate=True)

        for cert_data in certs_data:
            cert_manager = x509.CryptoAPICertManager()
            cert_thumprint, cert_upn = cert_manager.import_cert(
                cert_data, store_name=x509.STORE_NAME_ROOT)

            if not cert_upn:
                LOG.error("WinRM certificate authentication cannot be "
                          "configured as the provided certificate lacks a "
                          "subject alt name containing an UPN (OID "
                          "1.3.6.1.4.1.311.20.2.3)")
                continue

            if winrm_config.get_cert_mapping(cert_thumprint, cert_upn):
                winrm_config.delete_cert_mapping(cert_thumprint, cert_upn)

            LOG.info("Creating WinRM certificate mapping for user "
                     "%(user_name)s with UPN %(cert_upn)s",
                     {'user_name': user_name, 'cert_upn': cert_upn})
            winrm_config.create_cert_mapping(cert_thumprint, cert_upn,
                                             user_name, password)

        return (base.PLUGIN_EXECUTION_DONE, False)

########NEW FILE########
__FILENAME__ = winrmlistener
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins import base
from cloudbaseinit.utils.windows import winrmconfig
from cloudbaseinit.utils.windows import x509

LOG = logging.getLogger(__name__)

opts = [
    cfg.BoolOpt('winrm_enable_basic_auth', default=True,
                help='Enables basic authentication for the WinRM '
                'HTTPS listener'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class ConfigWinRMListenerPlugin(base.BasePlugin):
    _cert_subject = "CN=Cloudbase-Init WinRM"
    _winrm_service_name = "WinRM"

    def _check_winrm_service(self, osutils):
        if not osutils.check_service_exists(self._winrm_service_name):
            LOG.warn("Cannot configure the WinRM listener as the service "
                     "is not available")
            return False

        start_mode = osutils.get_service_start_mode(self._winrm_service_name)
        if start_mode in [osutils.SERVICE_START_MODE_MANUAL,
                          osutils.SERVICE_START_MODE_DISABLED]:
            # TODO(alexpilotti) Set to "Delayed Start"
            osutils.set_service_start_mode(
                self._winrm_service_name,
                osutils.SERVICE_START_MODE_AUTOMATIC)

        service_status = osutils.get_service_status(self._winrm_service_name)
        if service_status == osutils.SERVICE_STATUS_STOPPED:
            osutils.start_service(self._winrm_service_name)

        return True

    def execute(self, service, shared_data):
        osutils = osutils_factory.get_os_utils()

        if not self._check_winrm_service(osutils):
            return (base.PLUGIN_EXECUTE_ON_NEXT_BOOT, False)

        winrm_config = winrmconfig.WinRMConfig()
        winrm_config.set_auth_config(basic=CONF.winrm_enable_basic_auth)

        cert_manager = x509.CryptoAPICertManager()
        cert_thumbprint = cert_manager.create_self_signed_cert(
            self._cert_subject)

        protocol = winrmconfig.LISTENER_PROTOCOL_HTTPS

        if winrm_config.get_listener(protocol=protocol):
            winrm_config.delete_listener(protocol=protocol)

        winrm_config.create_listener(
            cert_thumbprint=cert_thumbprint,
            protocol=protocol)

        listener_config = winrm_config.get_listener(protocol=protocol)
        listener_port = listener_config.get("Port")

        rule_name = "WinRM %s" % protocol
        osutils.firewall_create_rule(rule_name, listener_port,
                                     osutils.PROTOCOL_TCP)

        return (base.PLUGIN_EXECUTION_DONE, False)

########NEW FILE########
__FILENAME__ = shell
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import sys

from oslo.config import cfg

from cloudbaseinit import init
from cloudbaseinit.utils import log as logging

CONF = cfg.CONF


def main():
    CONF(sys.argv[1:])
    logging.setup('cloudbaseinit')

    init.InitManager().configure_host()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = fake_json_response
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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


def get_fake_metadata_json(version):
    if version == '2013-04-04':
        return {"random_seed":
                "Wn51FGjZa3vlZtTxJuPr96oCf+X8jqbA9U2XR5wNdnApy1fz"
                "/2NNssUwPoNzG6etw9RBn+XiZ0zKWnFzMsTopaN7WwYjWTnIsVw3cpIk"
                "Td579wQgoEr1ANqhfO3qTvkOVNMhzTAw1ps+wqRmkLxH+1qYJnX06Gcd"
                "KRRGkWTaOSlTkieA0LO2oTGFlbFDWcOW2vT5BvSBmqP7vNLzbLDMTc7M"
                "IWRBzwmtcVPC17QL6EhZJTUcZ0mTz7l0R0DocLmFwHEXFEEr+q4WaJjt"
                "1ejOOxVM3tiT7D8YpRZnnGNPfvEhq1yVMUoi8yv9pFmMmXicNBhm6zDK"
                "VjcWk0gfbvaQcMnnOLrrE1VxAAzyNyPIXBI/H7AAHz2ECz7dgd2/4ocv"
                "3bmTRY3hhcUKtNuat2IOvSGgMBUGdWnLorQGFz8t0/bcYhE0Dve35U6H"
                "mtj78ydV/wmQWG0iq49NX6hk+VUmZtSZztlkbsaa7ajNjZ+Md9oZtlhX"
                "Z5vJuhRXnHiCm7dRNO8Xo6HffEBH5A4smQ1T2Kda+1c18DZrY7+iQJRi"
                "fa6witPCw0tXkQ6nlCLqL2weJD1XMiTZLSM/XsZFGGSkKCKvKLEqQrI/"
                "XFUq/TA6B4aLGFlmmhOO/vMJcht06O8qVU/xtd5Mv/MRFzYaSG568Z/m"
                "hk4vYLYdQYAA+pXRW9A=",
                "uuid": "4b32ddf7-7941-4c36-a854-a1f5ac45b318",
                "availability_zone": "nova",
                "hostname": "windows.novalocal",
                "launch_index": 0,
                "public_keys": {"key": "ssh-rsa "
                                       "AAAAB3NzaC1yc2EAAAADAQABAAABA"
                                "QDf7kQHq7zvBod3yIZs0tB/AOOZz5pab7qt/h"
                                "78VF7yi6qTsFdUnQxRue43R/75wa9EEyokgYR"
                                "LKIN+Jq2A5tXNMcK+rNOCzLJFtioAwEl+S6VL"
                                "G9jfkbUv++7zoSMOsanNmEDvG0B79MpyECFCl"
                                "th2DsdE4MQypify35U5ri5Qi7E6PEYAsU65LF"
                                "MG2boeCIB29BEooE6AgPr2DuJeJ+2uw+YScF9"
                                "FV3og4Wyz5zipPVh8YpVev6dlg0tRWUrCtZF9"
                                "IODpCTrT3vsPRG3xz7CppR+vGi/1gLXHtJCRj"
                                "frHwkY6cXyhypNmkU99K/wMqSv30vsDwdnsQ1"
                                "q3YhLarMHB Generated by Nova\n",
                                0: "windows"},
                "network_config": {"content_path": "network",
                                   'debian_config': 'iface eth0 inet static'
                                                    'address 10.11.12.13'
                                                    'broadcast 0.0.0.0'
                                                    'netmask 255.255.255.255'
                                                    'gateway 1.2.3.4'
                                                    'dns-nameserver 8.8.8.8'}}

########NEW FILE########
__FILENAME__ = test_factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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


import mock
import sys
import unittest

from cloudbaseinit.metadata.services.osconfigdrive import factory


class ClassloaderTest(unittest.TestCase):

    @mock.patch('cloudbaseinit.utils.classloader.ClassLoader.load_class')
    def _test_get_config_drive_manager(self, mock_load_class, platform):
        sys.platform = platform
        if platform is not "win32":
            self.assertRaises(NotImplementedError,
                              factory.get_config_drive_manager)
        else:
            response = factory.get_config_drive_manager()
            mock_load_class.assert_called_once_with(
                'cloudbaseinit.metadata.services.osconfigdrive.'
                'windows.WindowsConfigDriveManager')
            self.assertIsNotNone(response)

    def test_get_config_drive_manager(self):
        self._test_get_config_drive_manager(platform="win32")

    def test_get_config_drive_manager_exception(self):
        self._test_get_config_drive_manager(platform="other")

########NEW FILE########
__FILENAME__ = test_windows
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import os
import sys
import unittest

if sys.platform == 'win32':
    from cloudbaseinit.metadata.services.osconfigdrive import windows
    from cloudbaseinit.utils.windows import physical_disk
from oslo.config import cfg

CONF = cfg.CONF


@unittest.skipUnless(sys.platform == "win32", "requires Windows")
class TestWindowsConfigDriveManager(unittest.TestCase):

    def setUp(self):
        self._config_manager = windows.WindowsConfigDriveManager()

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('os.path.exists')
    def _test_get_config_drive_cdrom_mount_point(self, mock_join,
                                                 mock_get_os_utils, exists):
        mock_osutils = mock.MagicMock()
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.get_cdrom_drives.return_value = ['fake drive']
        mock_osutils.get_volume_label.return_value = 'config-2'
        mock_join.return_value = exists

        response = self._config_manager._get_config_drive_cdrom_mount_point()

        mock_osutils.get_cdrom_drives.assert_called_once_with()
        mock_osutils.get_volume_label.assert_called_once_with('fake drive')

        if exists:
            self.assertEqual(response, 'fake drive')
        else:
            self.assertIsNone(response)

    def test_get_config_drive_cdrom_mount_point_exists_true(self):
        self._test_get_config_drive_cdrom_mount_point(exists=True)

    def test_get_config_drive_cdrom_mount_point_exists_false(self):
        self._test_get_config_drive_cdrom_mount_point(exists=False)

    @mock.patch('ctypes.cast')
    @mock.patch('ctypes.POINTER')
    @mock.patch('ctypes.wintypes.WORD')
    def test_c_char_array_to_c_ushort(self, mock_WORD, mock_POINTER,
                                      mock_cast):
        mock_buf = mock.MagicMock()

        response = self._config_manager._c_char_array_to_c_ushort(mock_buf,
                                                                  1)

        self.assertEqual(mock_cast.call_count, 2)
        mock_POINTER.assert_called_with(mock_WORD)
        mock_cast.assert_called_with(mock_buf.__getitem__(), mock_POINTER())
        self.assertEqual(response,
                         mock_cast().contents.value.__lshift__().__add__())

    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._c_char_array_to_c_ushort')
    def _test_get_iso_disk_size(self, mock_c_char_array_to_c_ushort,
                                media_type, value, iso_id):

        boot_record_off = 0x8000
        volume_size_off = 80
        block_size_off = 128

        mock_phys_disk = mock.MagicMock()
        mock_buff = mock.MagicMock()
        mock_geom = mock.MagicMock()

        mock_phys_disk.get_geometry.return_value = mock_geom
        mock_geom.MediaType = media_type
        mock_geom.Cylinders = value
        mock_geom.TracksPerCylinder = 2
        mock_geom.SectorsPerTrack = 2
        mock_geom.BytesPerSector = 2
        mock_phys_disk.read.return_value = (mock_buff, 'fake value')
        mock_buff.__getitem__.return_value = iso_id
        mock_c_char_array_to_c_ushort.return_value = 100

        disk_size = mock_geom.Cylinders * mock_geom.TracksPerCylinder * \
            mock_geom.SectorsPerTrack * mock_geom.BytesPerSector

        offset = boot_record_off / mock_geom.BytesPerSector * \
            mock_geom.BytesPerSector

        buf_off_volume = boot_record_off - offset + volume_size_off
        buf_off_block = boot_record_off - offset + block_size_off

        response = self._config_manager._get_iso_disk_size(mock_phys_disk)
        mock_phys_disk.get_geometry.assert_called_once_with()
        if mock_geom.MediaType != physical_disk.Win32_DiskGeometry.FixedMedia:
            self.assertIsNone(response)
        elif disk_size <= offset + mock_geom.BytesPerSector:
            self.assertIsNone(response)
        else:
            mock_phys_disk.seek.assert_called_once_with(offset)
            mock_phys_disk.read.assert_called_once_with(
                mock_geom.BytesPerSector)
            if iso_id != 'CD001':
                self.assertIsNone(response)
            else:
                mock_c_char_array_to_c_ushort.assert_has_calls(
                    mock.call(mock_buff, buf_off_volume),
                    mock.call(mock_buff, buf_off_block))
                self.assertEqual(response, 10000)

    def test_test_get_iso_disk_size(self):
        self._test_get_iso_disk_size(
            media_type=physical_disk.Win32_DiskGeometry.FixedMedia,
            value=100, iso_id='CD001')

    def test_test_get_iso_disk_size_other_media_type(self):
        self._test_get_iso_disk_size(media_type="fake media type", value=100,
                                     iso_id='CD001')

    def test_test_get_iso_disk_size_other_disk_size_too_small(self):
        self._test_get_iso_disk_size(
            media_type=physical_disk.Win32_DiskGeometry.FixedMedia, value=0,
            iso_id='CD001')

    def test_test_get_iso_disk_size_other_id(self):
        self._test_get_iso_disk_size(
            media_type=physical_disk.Win32_DiskGeometry.FixedMedia,
            value=100, iso_id='other id')

    def test_write_iso_file(self):
        mock_buff = mock.MagicMock()
        mock_geom = mock.MagicMock()
        mock_geom.BytesPerSector = 2

        mock_phys_disk = mock.MagicMock()
        mock_phys_disk.read.return_value = (mock_buff, 10)

        fake_path = os.path.join('fake', 'path')

        mock_phys_disk.get_geometry.return_value = mock_geom
        with mock.patch('__builtin__.open', mock.mock_open(),
                        create=True) as f:
            self._config_manager._write_iso_file(mock_phys_disk, fake_path,
                                                 10)
            f().write.assert_called_once_with(mock_buff)
        mock_phys_disk.seek.assert_called_once_with(0)
        mock_phys_disk.read.assert_called_once_with(10)

    @mock.patch('os.makedirs')
    def _test_extract_iso_files(self, mock_makedirs, exit_code):
        fake_path = os.path.join('fake', 'path')
        fake_target_path = os.path.join(fake_path, 'target')
        args = [CONF.bsdtar_path, '-xf', fake_path, '-C', fake_target_path]
        mock_os_utils = mock.MagicMock()

        mock_os_utils.execute_process.return_value = ('fake out', 'fake err',
                                                      exit_code)
        if exit_code:
            self.assertRaises(Exception,
                              self._config_manager._extract_iso_files,
                              mock_os_utils, fake_path, fake_target_path)
        else:
            self._config_manager._extract_iso_files(mock_os_utils, fake_path,
                                                    fake_target_path)

        mock_os_utils.execute_process.assert_called_once_with(args, False)
        mock_makedirs.assert_called_once_with(fake_target_path)

    def test_extract_iso_files(self):
        self._test_extract_iso_files(exit_code=None)

    def test_extract_iso_files_exception(self):
        self._test_extract_iso_files(exit_code=1)

    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._get_iso_disk_size')
    @mock.patch('cloudbaseinit.utils.windows.physical_disk.PhysicalDisk')
    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._write_iso_file')
    def _test_extract_iso_disk_file(self, mock_write_iso_file,
                                    mock_PhysicalDisk, mock_get_iso_disk_size,
                                    exception):
        mock_osutils = mock.MagicMock()
        fake_path = os.path.join('fake', 'path')
        fake_path_physical = os.path.join(fake_path, 'physical')
        mock_osutils.get_physical_disks.return_value = [fake_path_physical]
        mock_get_iso_disk_size.return_value = 'fake iso size'

        if exception:
            mock_PhysicalDisk().open.side_effect = [Exception]

        response = self._config_manager._extract_iso_disk_file(
            osutils=mock_osutils, iso_file_path=fake_path)
        print mock_PhysicalDisk().open.mock_calls

        if not exception:
            mock_get_iso_disk_size.assert_called_once_with(
                mock_PhysicalDisk())
            mock_write_iso_file.assert_called_once_with(mock_PhysicalDisk(),
                                                        fake_path,
                                                        'fake iso size')
            self.assertTrue(response)
        else:
            self.assertFalse(response)

        mock_PhysicalDisk().open.assert_called_once_with()
        mock_osutils.get_physical_disks.assert_called_once_with()
        mock_PhysicalDisk().close.assert_called_once_with()

    def test_extract_iso_disk_file_disk_found(self):
        self._test_extract_iso_disk_file(exception=False)

    def test_extract_iso_disk_file_disk_not_found(self):
        self._test_extract_iso_disk_file(exception=True)

    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._get_conf_drive_from_raw_hdd')
    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._get_conf_drive_from_cdrom_drive')
    def test_get_config_drive_files(self,
                                    mock_get_conf_drive_from_cdrom_drive,
                                    mock_get_conf_drive_from_raw_hdd):

        fake_path = os.path.join('fake', 'path')
        mock_get_conf_drive_from_raw_hdd.return_value = False
        mock_get_conf_drive_from_cdrom_drive.return_value = True

        response = self._config_manager.get_config_drive_files(
            target_path=fake_path)

        mock_get_conf_drive_from_raw_hdd.assert_called_once_with(fake_path)
        mock_get_conf_drive_from_cdrom_drive.assert_called_once_with(
            fake_path)
        self.assertTrue(response)

    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager.'
                '_get_config_drive_cdrom_mount_point')
    @mock.patch('shutil.copytree')
    def _test_get_conf_drive_from_cdrom_drive(self, mock_copytree,
                                              mock_get_config_cdrom_mount,
                                              mount_point):
        fake_path = os.path.join('fake', 'path')
        mock_get_config_cdrom_mount.return_value = mount_point

        response = self._config_manager._get_conf_drive_from_cdrom_drive(
            fake_path)

        mock_get_config_cdrom_mount.assert_called_once_with()

        if mount_point:
            mock_copytree.assert_called_once_with(mount_point, fake_path)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_get_conf_drive_from_cdrom_drive_with_mountpoint(self):
        self._test_get_conf_drive_from_cdrom_drive(
            mount_point='fake mount point')

    def test_get_conf_drive_from_cdrom_drive_without_mountpoint(self):
        self._test_get_conf_drive_from_cdrom_drive(
            mount_point=None)

    @mock.patch('os.remove')
    @mock.patch('os.path.exists')
    @mock.patch('tempfile.gettempdir')
    @mock.patch('uuid.uuid4')
    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._extract_iso_disk_file')
    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.windows.'
                'WindowsConfigDriveManager._extract_iso_files')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def _test_get_conf_drive_from_raw_hdd(self, mock_get_os_utils,
                                          mock_extract_iso_files,
                                          mock_extract_iso_disk_file,
                                          mock_uuid4, mock_gettempdir,
                                          mock_exists, mock_remove,
                                          found_drive):
        fake_target_path = os.path.join('fake', 'path')
        fake_iso_path = os.path.join('fake_dir', 'fake_id' + '.iso')

        mock_uuid4.return_value = 'fake_id'
        mock_gettempdir.return_value = 'fake_dir'
        mock_extract_iso_disk_file.return_value = found_drive
        mock_exists.return_value = found_drive

        response = self._config_manager._get_conf_drive_from_raw_hdd(
            fake_target_path)

        mock_get_os_utils.assert_called_once_with()
        mock_gettempdir.assert_called_once_with()
        mock_extract_iso_disk_file.assert_called_once_with(
            mock_get_os_utils(), fake_iso_path)
        if found_drive:
            mock_extract_iso_files.assert_called_once_with(
                mock_get_os_utils(), fake_iso_path, fake_target_path)
            mock_exists.assert_called_once_with(fake_iso_path)
            mock_remove.assert_called_once_with(fake_iso_path)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_get_conf_drive_from_raw_hdd_found_drive(self):
        self._test_get_conf_drive_from_raw_hdd(found_drive=True)

    def test_get_conf_drive_from_raw_hdd_no_drive_found(self):
        self._test_get_conf_drive_from_raw_hdd(found_drive=False)

########NEW FILE########
__FILENAME__ = test_baseopenstackservice
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import posixpath
import unittest

from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import baseopenstackservice
from cloudbaseinit.utils import x509constants
from oslo.config import cfg

CONF = cfg.CONF


class BaseOpenStackServiceTest(unittest.TestCase):
    def setUp(self):
        CONF.set_override('retry_count_interval', 0)
        self._service = baseopenstackservice.BaseOpenStackService()

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_cache_data")
    def test_get_content(self, mock_get_cache_data):
        response = self._service.get_content('fake name')
        path = posixpath.join('openstack', 'content', 'fake name')
        mock_get_cache_data.assert_called_once_with(path)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_cache_data")
    def test_get_user_data(self, mock_get_cache_data):
        response = self._service.get_user_data()
        path = posixpath.join('openstack', 'latest', 'user_data')
        mock_get_cache_data.assert_called_once_with(path)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_cache_data")
    @mock.patch('json.loads')
    def _test_get_meta_data(self, mock_loads, mock_get_cache_data, data):
        mock_get_cache_data.return_value = data
        response = self._service._get_meta_data(
            version='fake version')
        path = posixpath.join('openstack', 'fake version', 'meta_data.json')
        mock_get_cache_data.assert_called_with(path)
        if type(data) is str:
            mock_loads.assert_called_once_with(mock_get_cache_data())
            self.assertEqual(response, mock_loads())
        else:
            self.assertEqual(response, data)

    def test_get_meta_data_string(self):
        self._test_get_meta_data(data='fake data')

    def test_get_meta_data_dict(self):
        self._test_get_meta_data(data={'fake': 'data'})

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_meta_data")
    def test_get_instance_id(self, mock_get_meta_data):
        response = self._service.get_instance_id()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('uuid')
        self.assertEqual(response, mock_get_meta_data().get())

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_meta_data")
    def test_get_host_name(self, mock_get_meta_data):
        response = self._service.get_host_name()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('hostname')
        self.assertEqual(response, mock_get_meta_data().get())

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_meta_data")
    def test_get_public_keys(self, mock_get_meta_data):
        response = self._service.get_public_keys()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('public_keys')
        self.assertEqual(response, mock_get_meta_data().get().values())

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_meta_data")
    def test_get_network_config(self, mock_get_meta_data):
        response = self._service.get_network_config()
        mock_get_meta_data.assert_called_once_with()
        mock_get_meta_data().get.assert_called_once_with('network_config')
        self.assertEqual(response, mock_get_meta_data().get())

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_meta_data")
    def _test_get_admin_password(self, mock_get_meta_data, meta_data):
        mock_get_meta_data.return_value = meta_data
        response = self._service.get_admin_password()
        mock_get_meta_data.assert_called_once_with()
        if meta_data and 'admin_pass' in meta_data:
            self.assertEqual(response, meta_data['admin_pass'])
        elif meta_data and 'admin_pass' in meta_data.get('meta'):
            self.assertEqual(response, meta_data.get('meta')['admin_pass'])
        else:
            self.assertEqual(response, None)

    def test_get_admin_pass(self):
        self._test_get_admin_password(meta_data={'admin_pass': 'fake pass'})

    def test_get_admin_pass_in_meta(self):
        self._test_get_admin_password(
            meta_data={'meta': {'admin_pass': 'fake pass'}})

    def test_get_admin_pass_no_pass(self):
        self._test_get_admin_password(meta_data={})

    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService._get_meta_data")
    @mock.patch("cloudbaseinit.metadata.services.baseopenstackservice"
                ".BaseOpenStackService.get_user_data")
    def _test_get_client_auth_certs(self, mock_get_user_data,
                                    mock_get_meta_data, meta_data,
                                    ret_value=None):
        mock_get_meta_data.return_value = meta_data
        mock_get_user_data.side_effect = [ret_value]
        response = self._service.get_client_auth_certs()
        mock_get_meta_data.assert_called_once_with()
        if 'meta' in meta_data:
            self.assertEqual(response, ['fake cert'])
        elif type(ret_value) is str and ret_value.startswith(
                x509constants.PEM_HEADER):
            mock_get_user_data.assert_called_once_with()
            self.assertEqual(response, [ret_value])
        elif ret_value is base.NotExistingMetadataException:
            self.assertEqual(response, None)

    def test_get_client_auth_certs(self):
        self._test_get_client_auth_certs(
            meta_data={'meta': {'admin_cert0': 'fake cert'}})

    def test_get_client_auth_certs_no_cert_data(self):
        self._test_get_client_auth_certs(
            meta_data={}, ret_value=x509constants.PEM_HEADER)

    def test_get_client_auth_certs_no_cert_data_exception(self):
        self._test_get_client_auth_certs(
            meta_data={}, ret_value=base.NotExistingMetadataException)

########NEW FILE########
__FILENAME__ = test_configdrive
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import importlib
import mock
import os
import sys
import unittest
import uuid

from oslo.config import cfg

CONF = cfg.CONF
_win32com_mock = mock.MagicMock()
_ctypes_mock = mock.MagicMock()
_ctypes_util_mock = mock.MagicMock()
_win32com_client_mock = mock.MagicMock()
_pywintypes_mock = mock.MagicMock()
_mock_dict = {'win32com': _win32com_mock,
              'ctypes': _ctypes_mock,
              'ctypes.util': _ctypes_util_mock,
              'win32com.client': _win32com_client_mock,
              'pywintypes': _pywintypes_mock}


class ConfigDriveServiceTest(unittest.TestCase):
    @mock.patch.dict(sys.modules, _mock_dict)
    def setUp(self):
        configdrive = importlib.import_module('cloudbaseinit.metadata.services'
                                              '.configdrive')
        self._config_drive = configdrive.ConfigDriveService()

    def tearDown(self):
        reload(uuid)

    @mock.patch('tempfile.gettempdir')
    @mock.patch('cloudbaseinit.metadata.services.osconfigdrive.factory.'
                'get_config_drive_manager')
    def test_load(self, mock_get_config_drive_manager,
                  mock_gettempdir):
        mock_manager = mock.MagicMock()
        mock_manager.get_config_drive_files.return_value = True
        mock_get_config_drive_manager.return_value = mock_manager
        mock_gettempdir.return_value = 'fake'
        uuid.uuid4 = mock.MagicMock(return_value='fake_id')
        fake_path = os.path.join('fake', str('fake_id'))

        response = self._config_drive.load()

        mock_gettempdir.assert_called_once_with()
        mock_get_config_drive_manager.assert_called_once_with()
        mock_manager.get_config_drive_files.assert_called_once_with(
            fake_path, CONF.config_drive_raw_hhd, CONF.config_drive_cdrom)
        self.assertEqual(response, True)
        self.assertEqual(self._config_drive._metadata_path, fake_path)

    @mock.patch('os.path.normpath')
    @mock.patch('os.path.join')
    def test_get_data(self, mock_join, mock_normpath):
        fake_path = os.path.join('fake', 'path')
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data='fake data'), create=True):
            response = self._config_drive._get_data(fake_path)
            self.assertEqual(response, 'fake data')
            mock_join.assert_called_with(
                self._config_drive._metadata_path, fake_path)

    @mock.patch('shutil.rmtree')
    def test_cleanup(self, mock_rmtree):
        fake_path = os.path.join('fake', 'path')
        self._config_drive._metadata_path = fake_path
        self._config_drive.cleanup()
        self.assertEqual(self._config_drive._metadata_path, None)

########NEW FILE########
__FILENAME__ = test_ec2service
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import posixpath
import unittest
import urllib2

from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import ec2service
from oslo.config import cfg

CONF = cfg.CONF


class EC2ServiceTest(unittest.TestCase):
    def setUp(self):
        CONF.set_override('retry_count_interval', 0)
        self._service = ec2service.EC2Service()

    @mock.patch('cloudbaseinit.utils.network.check_metadata_ip_route')
    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '.get_host_name')
    def _test_load(self, mock_get_host_name, mock_check_metadata_ip_route,
                   side_effect):
        mock_get_host_name.side_effect = [side_effect]
        response = self._service.load()
        mock_check_metadata_ip_route.assert_called_once_with(
            CONF.ec2_metadata_base_url)
        mock_get_host_name.assert_called_once()
        if side_effect is Exception:
            self.assertFalse(response)
        else:
            self.assertTrue(response)

    def test_load(self):
        self._test_load(side_effect=None)

    def test_load_exception(self):
        self._test_load(side_effect=Exception)

    @mock.patch('urllib2.urlopen')
    def _test_get_response(self, mock_urlopen, ret_value):
        req = mock.MagicMock()
        mock_urlopen.side_effect = [ret_value]
        is_instance = isinstance(ret_value, urllib2.HTTPError)
        if is_instance and ret_value.code == 404:
            self.assertRaises(base.NotExistingMetadataException,
                              self._service._get_response, req)
        elif is_instance and ret_value.code != 404:
            self.assertRaises(urllib2.HTTPError,
                              self._service._get_response, req)
        else:
            response = self._service._get_response(req)
            self.assertEqual(response, ret_value)
        mock_urlopen.assert_called_once_with(req)

    def test_get_response(self):
        self._test_get_response(ret_value=None)

    def test_get_response_error_404(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 404,
                                'test error 404', {}, None)
        self._test_get_response(ret_value=err)

    def test_get_response_error_other(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 409,
                                'test error 409', {}, None)
        self._test_get_response(ret_value=err)

    @mock.patch('urllib2.Request')
    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_response')
    def test_get_data(self, mock_get_response, mock_Request):
        response = self._service._get_data('fake')
        fake_path = posixpath.join(CONF.ec2_metadata_base_url, 'fake')
        mock_Request.assert_called_once_with(fake_path)
        mock_get_response.assert_called_once_with(mock_Request())
        self.assertEqual(response, mock_get_response().read())

    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_cache_data')
    def test_get_host_name(self, mock_get_cache_data):
        response = self._service.get_host_name()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/local-hostname' % self._service._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_cache_data')
    def test_get_instance_id(self, mock_get_cache_data):
        response = self._service.get_instance_id()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/instance-id' % self._service._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch('cloudbaseinit.metadata.services.ec2service.EC2Service'
                '._get_cache_data')
    def test_get_public_keys(self, mock_get_cache_data):
        mock_get_cache_data.side_effect = ['key=info', 'fake key']
        response = self._service.get_public_keys()
        expected = [
            mock.call('%s/meta-data/public-keys' %
                      self._service._metadata_version),
            mock.call('%(version)s/meta-data/public-keys/%('
                      'idx)s/openssh-key' %
                      {'version': self._service._metadata_version,
                       'idx': 'key'})]
        self.assertEqual(mock_get_cache_data.call_args_list, expected)
        self.assertEqual(response, ['fake key'])

########NEW FILE########
__FILENAME__ = test_httpservice
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import os
import unittest
import urllib2

from oslo.config import cfg

from cloudbaseinit.metadata.services import httpservice
from cloudbaseinit.metadata.services import base

CONF = cfg.CONF


class HttpServiceTest(unittest.TestCase):
    def setUp(self):
        CONF.set_override('retry_count_interval', 0)
        self._httpservice = httpservice.HttpService()

    @mock.patch('cloudbaseinit.utils.network.check_metadata_ip_route')
    @mock.patch('cloudbaseinit.metadata.services.httpservice.HttpService'
                '._get_meta_data')
    def _test_load(self, mock_get_meta_data, mock_check_metadata_ip_route,
                   side_effect):
        mock_get_meta_data.side_effect = [side_effect]
        response = self._httpservice.load()
        mock_check_metadata_ip_route.assert_called_once_with(
            CONF.metadata_base_url)
        mock_get_meta_data.assert_called_once_with()
        if side_effect:
            self.assertEqual(response, False)
        else:
            self.assertEqual(response, True)

    def test_load(self):
        self._test_load(side_effect=None)

    def test_load_exception(self):
        self._test_load(side_effect=Exception)

    @mock.patch('urllib2.urlopen')
    def _test_get_response(self, mock_urlopen, side_effect):
        mock_req = mock.MagicMock
        if side_effect and side_effect.code is 404:
            mock_urlopen.side_effect = [side_effect]
            self.assertRaises(base.NotExistingMetadataException,
                              self._httpservice._get_response,
                              mock_req)
        elif side_effect and side_effect.code:
            mock_urlopen.side_effect = [side_effect]
            self.assertRaises(Exception, self._httpservice._get_response,
                              mock_req)
        else:
            mock_urlopen.return_value = 'fake url'
            response = self._httpservice._get_response(mock_req)
            self.assertEqual(response, 'fake url')

    def test_get_response_fail_HTTPError(self):
        error = urllib2.HTTPError("http://169.254.169.254/", 404,
                                  'test error 404', {}, None)
        self._test_get_response(side_effect=error)

    def test_get_response_fail_other_exception(self):
        error = urllib2.HTTPError("http://169.254.169.254/", 409,
                                  'test error 409', {}, None)
        self._test_get_response(side_effect=error)

    def test_get_response(self):
        self._test_get_response(side_effect=None)

    @mock.patch('cloudbaseinit.metadata.services.httpservice.HttpService'
                '._get_response')
    @mock.patch('posixpath.join')
    @mock.patch('urllib2.Request')
    def test_get_data(self, mock_Request, mock_posix_join,
                      mock_get_response):
        fake_path = os.path.join('fake', 'path')
        mock_data = mock.MagicMock()
        mock_norm_path = mock.MagicMock()
        mock_req = mock.MagicMock()
        mock_get_response.return_value = mock_data
        mock_posix_join.return_value = mock_norm_path
        mock_Request.return_value = mock_req

        response = self._httpservice._get_data(fake_path)

        mock_posix_join.assert_called_with(CONF.metadata_base_url, fake_path)
        mock_Request.assert_called_once_with(mock_norm_path)
        mock_get_response.assert_called_once_with(mock_req)
        self.assertEqual(response, mock_data.read())

    @mock.patch('cloudbaseinit.metadata.services.httpservice.HttpService'
                '._get_response')
    @mock.patch('posixpath.join')
    @mock.patch('urllib2.Request')
    def test_post_data(self, mock_Request, mock_posix_join,
                       mock_get_response):
        fake_path = os.path.join('fake', 'path')
        fake_data = 'fake data'
        mock_data = mock.MagicMock()
        mock_norm_path = mock.MagicMock()
        mock_req = mock.MagicMock()
        mock_get_response.return_value = mock_data
        mock_posix_join.return_value = mock_norm_path
        mock_Request.return_value = mock_req

        response = self._httpservice._post_data(fake_path, fake_data)

        mock_posix_join.assert_called_with(CONF.metadata_base_url,
                                           fake_path)
        mock_Request.assert_called_once_with(mock_norm_path, data=fake_data)
        mock_get_response.assert_called_once_with(mock_req)
        self.assertEqual(response, True)

    def test_get_password_path(self):
        response = self._httpservice._get_password_path()
        self.assertEqual(
            response, 'openstack/%s/password' %
                      self._httpservice._POST_PASSWORD_MD_VER)

    @mock.patch('cloudbaseinit.metadata.services.httpservice.HttpService'
                '._get_password_path')
    @mock.patch('cloudbaseinit.metadata.services.httpservice.HttpService'
                '._post_data')
    @mock.patch('cloudbaseinit.metadata.services.httpservice.HttpService'
                '._exec_with_retry')
    def _test_post_password(self, mock_exec_with_retry, mock_post_data,
                            mock_get_password_path, ret_val):
        mock_exec_with_retry.side_effect = [ret_val]
        if isinstance(ret_val, urllib2.HTTPError) and ret_val.code == 409:
            response = self._httpservice.post_password(
                enc_password_b64='fake')
            self.assertEqual(response, False)
        elif isinstance(ret_val, urllib2.HTTPError) and ret_val.code != 409:
            self.assertRaises(urllib2.HTTPError,
                              self._httpservice.post_password, 'fake')
        else:
            response = self._httpservice.post_password(
                enc_password_b64='fake')
            mock_get_password_path.assert_called_once_with()
            self.assertEqual(response, ret_val)

    def test_post_password(self):
        self._test_post_password(ret_val='fake return')

    def test_post_password_HTTPError_409(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 409,
                                'test error 409', {}, None)
        self._test_post_password(ret_val=err)

    def test_post_password_other_HTTPError(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 404,
                                'test error 404', {}, None)
        self._test_post_password(ret_val=err)

########NEW FILE########
__FILENAME__ = test_maasservice
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import os
import posixpath
import unittest
import urllib2

from oslo.config import cfg
from cloudbaseinit.metadata.services import base
from cloudbaseinit.metadata.services import maasservice
from cloudbaseinit.utils import x509constants

CONF = cfg.CONF


class MaaSHttpServiceTest(unittest.TestCase):
    def setUp(self):
        self.mock_oauth = mock.MagicMock()
        maasservice.oauth = self.mock_oauth
        self._maasservice = maasservice.MaaSHttpService()

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_data")
    def _test_load(self, mock_get_data, ip):
        CONF.set_override('maas_metadata_url', ip)
        response = self._maasservice.load()
        if ip is not None:
            mock_get_data.assert_called_once_with(
                '%s/meta-data/' % self._maasservice._metadata_version)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_load(self):
        self._test_load(ip='196.254.196.254')

    def test_load_no_ip(self):
        self._test_load(ip=None)

    @mock.patch('urllib2.urlopen')
    def _test_get_response(self, mock_urlopen, ret_val):
        mock_request = mock.MagicMock()
        mock_urlopen.side_effect = [ret_val]
        if isinstance(ret_val, urllib2.HTTPError) and ret_val.code == 404:
            self.assertRaises(base.NotExistingMetadataException,
                              self._maasservice._get_response, mock_request)
        elif isinstance(ret_val, urllib2.HTTPError) and ret_val.code != 404:
            self.assertRaises(urllib2.HTTPError,
                              self._maasservice._get_response, mock_request)
        else:
            response = self._maasservice._get_response(req=mock_request)
            mock_urlopen.assert_called_once_with(mock_request)
            self.assertEqual(response, ret_val)

    def test_get_response(self):
        self._test_get_response(ret_val='fake response')

    def test_get_response_error_404(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 404,
                                'test error 404', {}, None)
        self._test_get_response(ret_val=err)

    def test_get_response_error_not_404(self):
        err = urllib2.HTTPError("http://169.254.169.254/", 409,
                                'test other error', {}, None)
        self._test_get_response(ret_val=err)

    @mock.patch('time.time')
    def test_get_oauth_headers(self, mock_time):
        mock_token = mock.MagicMock()
        mock_consumer = mock.MagicMock()
        mock_req = mock.MagicMock()
        self.mock_oauth.OAuthConsumer.return_value = mock_consumer
        self.mock_oauth.OAuthToken.return_value = mock_token
        self.mock_oauth.OAuthRequest.return_value = mock_req
        mock_time.return_value = 0
        self.mock_oauth.generate_nonce.return_value = 'fake nounce'
        response = self._maasservice._get_oauth_headers(url='196.254.196.254')
        self.mock_oauth.OAuthConsumer.assert_called_once_with(
            CONF.maas_oauth_consumer_key, CONF.maas_oauth_consumer_secret)
        self.mock_oauth.OAuthToken.assert_called_once_with(
            CONF.maas_oauth_token_key, CONF.maas_oauth_token_secret)
        parameters = {'oauth_version': "1.0",
                      'oauth_nonce': 'fake nounce',
                      'oauth_timestamp': int(0),
                      'oauth_token': mock_token.key,
                      'oauth_consumer_key': mock_consumer.key}
        self.mock_oauth.OAuthRequest.assert_called_once_with(
            http_url='196.254.196.254', parameters=parameters)
        mock_req.sign_request.assert_called_once_with(
            self.mock_oauth.OAuthSignatureMethod_PLAINTEXT(), mock_consumer,
            mock_token)
        self.assertEqual(response, mock_req.to_header())

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_oauth_headers")
    @mock.patch("urllib2.Request")
    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_response")
    def test_get_data(self, mock_get_response, mock_Request,
                      mock_get_oauth_headers):
        CONF.set_override('maas_metadata_url', '196.254.196.254')
        fake_path = os.path.join('fake', 'path')
        mock_get_oauth_headers.return_value = 'fake headers'
        response = self._maasservice._get_data(path=fake_path)
        norm_path = posixpath.join(CONF.maas_metadata_url, fake_path)
        mock_get_oauth_headers.assert_called_once_with(norm_path)
        mock_Request.assert_called_once_with(norm_path,
                                             headers='fake headers')
        mock_get_response.assert_called_once_with(mock_Request())
        self.assertEqual(response, mock_get_response().read())

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_host_name(self, mock_get_cache_data):
        response = self._maasservice.get_host_name()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/local-hostname' %
            self._maasservice._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_instance_id(self, mock_get_cache_data):
        response = self._maasservice.get_instance_id()
        mock_get_cache_data.assert_called_once_with(
            '%s/meta-data/instance-id' % self._maasservice._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

    def test_get_list_from_text(self):
        response = self._maasservice._get_list_from_text('fake:text', ':')
        self.assertEqual(response, ['fake:', 'text:'])

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_list_from_text")
    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_public_keys(self, mock_get_cache_data,
                             mock_get_list_from_text):
        response = self._maasservice.get_public_keys()
        mock_get_cache_data.assert_called_with(
            '%s/meta-data/public-keys' % self._maasservice._metadata_version)
        mock_get_list_from_text.assert_called_once_with(mock_get_cache_data(),
                                                        "\n")
        self.assertEqual(response, mock_get_list_from_text())

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_list_from_text")
    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_client_auth_certs(self, mock_get_cache_data,
                                   mock_get_list_from_text):
        response = self._maasservice.get_client_auth_certs()
        mock_get_cache_data.assert_called_with(
            '%s/meta-data/x509' % self._maasservice._metadata_version)
        mock_get_list_from_text.assert_called_once_with(
            mock_get_cache_data(), "%s\n" % x509constants.PEM_FOOTER)
        self.assertEqual(response, mock_get_list_from_text())

    @mock.patch("cloudbaseinit.metadata.services.maasservice.MaaSHttpService"
                "._get_cache_data")
    def test_get_user_data(self, mock_get_cache_data):
        response = self._maasservice.get_user_data()
        mock_get_cache_data.assert_called_once_with(
            '%s/user-data' %
            self._maasservice._metadata_version)
        self.assertEqual(response, mock_get_cache_data())

########NEW FILE########
__FILENAME__ = test_factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from cloudbaseinit.metadata import factory


class MetadataServiceFactoryTests(unittest.TestCase):

    @mock.patch('cloudbaseinit.utils.classloader.ClassLoader.load_class')
    def _test_get_metadata_service(self, mock_load_class, ret_value):
        mock_load_class.side_effect = ret_value
        if ret_value is Exception:
            self.assertRaises(Exception, factory.get_metadata_service)
        else:
            response = factory.get_metadata_service()
            self.assertEqual(response, mock_load_class()())

    def test_get_metadata_service(self):
        m = mock.MagicMock()
        self._test_get_metadata_service(ret_value=m)

    def test_get_metadata_service_exception(self):
        self._test_get_metadata_service(ret_value=Exception)

########NEW FILE########
__FILENAME__ = test_factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import os
import unittest

from cloudbaseinit.osutils import factory


class OSUtilsFactory(unittest.TestCase):

    @mock.patch('cloudbaseinit.utils.classloader.ClassLoader.load_class')
    def _test_get_os_utils(self, mock_load_class, fake_name):
        os.name = fake_name
        factory.get_os_utils()
        if fake_name == 'nt':
            mock_load_class.assert_called_with(
                'cloudbaseinit.osutils.windows.WindowsUtils')
        elif fake_name == 'posix':
            mock_load_class.assert_called_with(
                'cloudbaseinit.osutils.posix.PosixUtils')

    def test_get_os_utils_windows(self):
        self._test_get_os_utils(fake_name='nt')

    def test_get_os_utils_posix(self):
        self._test_get_os_utils(fake_name='posix')

########NEW FILE########
__FILENAME__ = test_windows
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import ctypes
import mock
import os
import time
import sys
import unittest

from oslo.config import cfg

if sys.platform == 'win32':
    import _winreg
    import win32process
    import win32security
    import wmi

    from ctypes import windll
    from ctypes import wintypes
    from cloudbaseinit.osutils import windows as windows_utils

CONF = cfg.CONF


@unittest.skipUnless(sys.platform == "win32", "requires Windows")
class WindowsUtilsTest(unittest.TestCase):
    '''Tests for the windows utils class'''

    _CONFIG_NAME = 'FakeConfig'
    _DESTINATION = '192.168.192.168'
    _GATEWAY = '10.7.1.1'
    _NETMASK = '255.255.255.0'
    _PASSWORD = 'Passw0rd'
    _SECTION = 'fake_section'
    _USERNAME = 'Admin'

    def setUp(self):
        self._winutils = windows_utils.WindowsUtils()
        self._conn = mock.MagicMock()

    def test_enable_shutdown_privilege(self):
        fake_process = mock.MagicMock()
        fake_token = True
        private_LUID = 'fakeid'
        win32process.GetCurrentProcess = mock.MagicMock(
            return_value=fake_process)
        win32security.OpenProcessToken = mock.MagicMock(
            return_value=fake_token)
        win32security.LookupPrivilegeValue = mock.MagicMock(
            return_value=private_LUID)
        win32security.AdjustTokenPrivileges = mock.MagicMock()
        self._winutils._enable_shutdown_privilege()
        privilege = [(private_LUID, win32security.SE_PRIVILEGE_ENABLED)]
        win32security.AdjustTokenPrivileges.assert_called_with(
            fake_token,
            False,
            privilege)

        win32security.OpenProcessToken.assert_called_with(
            fake_process,
            win32security.TOKEN_ADJUST_PRIVILEGES |
            win32security.TOKEN_QUERY)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._enable_shutdown_privilege')
    def _test_reboot(self, mock_enable_shutdown_privilege, ret_value):
        windll.advapi32.InitiateSystemShutdownW = mock.MagicMock(
            return_value=ret_value)

        if not ret_value:
            self.assertRaises(Exception, self._winutils.reboot)
        else:
            self._winutils.reboot()

            windll.advapi32.InitiateSystemShutdownW.assert_called_with(
                0,
                "Cloudbase-Init reboot",
                0, True, True)

    def test_reboot(self):
        self._test_reboot(ret_value=True)

    def test_reboot_failed(self):
        self._test_reboot(ret_value=None)

    @mock.patch('wmi.WMI')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._sanitize_wmi_input')
    def _test_get_user_wmi_object(self, mock_sanitize_wmi_input, mock_WMI,
                                  returnvalue):
        mock_WMI.return_value = self._conn
        mock_sanitize_wmi_input.return_value = self._USERNAME
        self._conn.query.return_value = returnvalue
        response = self._winutils._get_user_wmi_object(self._USERNAME)
        self._conn.query.assert_called_with("SELECT * FROM Win32_Account "
                                            "where name = \'%s\'" %
                                            self._USERNAME)
        mock_sanitize_wmi_input.assert_called_with(self._USERNAME)
        mock_WMI.assert_called_with(moniker='//./root/cimv2')
        if returnvalue:
            self.assertTrue(response is not None)
        else:
            self.assertTrue(response is None)

    def test_get_user_wmi_object(self):
        caption = 'fake'
        self._test_get_user_wmi_object(returnvalue=caption)

    def test_no_user_wmi_object(self):
        empty_caption = ''
        self._test_get_user_wmi_object(returnvalue=empty_caption)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_user_wmi_object')
    def _test_user_exists(self, mock_get_user_wmi_object, returnvalue):
        mock_get_user_wmi_object.return_value = returnvalue
        response = self._winutils.user_exists(returnvalue)
        mock_get_user_wmi_object.assert_called_with(returnvalue)
        if returnvalue:
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_user_exists(self):
        self._test_user_exists(returnvalue=self._USERNAME)

    def test_username_does_not_exist(self):
        self._test_user_exists(returnvalue=None)

    def test_sanitize_wmi_input(self):
        unsanitised = ' \' '
        response = self._winutils._sanitize_wmi_input(unsanitised)
        sanitised = ' \'\' '
        self.assertEqual(response, sanitised)

    def test_sanitize_shell_input(self):
        unsanitised = ' " '
        response = self._winutils.sanitize_shell_input(unsanitised)
        sanitised = ' \\" '
        self.assertEqual(response, sanitised)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._set_user_password_expiration')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_create_or_change_user(self, mock_execute_process,
                                    mock_set_user_password_expiration,
                                    create, password_expires, ret_value=0):
        args = ['NET', 'USER', self._USERNAME, self._PASSWORD]
        if create:
            args.append('/ADD')
        mock_execute_process.return_value = (None, None, ret_value)
        if not ret_value:
            self._winutils._create_or_change_user(self._USERNAME,
                                                  self._PASSWORD, create,
                                                  password_expires)
            mock_set_user_password_expiration.assert_called_with(
                self._USERNAME, password_expires)
        else:
            self.assertRaises(
                Exception, self._winutils._create_or_change_user,
                self._USERNAME, self._PASSWORD, create, password_expires)
        mock_execute_process.assert_called_with(args)

    def test_create_user_and_add_password_expire_true(self):
        self._test_create_or_change_user(create=True, password_expires=True)

    def test_create_user_and_add_password_expire_false(self):
        self._test_create_or_change_user(create=True, password_expires=False)

    def test_add_password_expire_true(self):
        self._test_create_or_change_user(create=False, password_expires=True)

    def test_add_password_expire_false(self):
        self._test_create_or_change_user(create=False, password_expires=False)

    def test_create_user_and_add_password_expire_true_with_ret_value(self):
        self._test_create_or_change_user(create=True, password_expires=True,
                                         ret_value=1)

    def test_create_user_and_add_password_expire_false_with_ret_value(self):
        self._test_create_or_change_user(create=True,
                                         password_expires=False, ret_value=1)

    def test_add_password_expire_true_with_ret_value(self):
        self._test_create_or_change_user(create=False,
                                         password_expires=True, ret_value=1)

    def test_add_password_expire_false_with_ret_value(self):
        self._test_create_or_change_user(create=False,
                                         password_expires=False, ret_value=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_user_wmi_object')
    def _test_set_user_password_expiration(self, mock_get_user_wmi_object,
                                           fake_obj):
        mock_get_user_wmi_object.return_value = fake_obj
        response = self._winutils._set_user_password_expiration(
            self._USERNAME, True)
        if fake_obj:
            self.assertTrue(fake_obj.PasswordExpires)
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_set_password_expiration(self):
        fake = mock.Mock()
        self._test_set_user_password_expiration(fake_obj=fake)

    def test_set_password_expiration_no_object(self):
        self._test_set_user_password_expiration(fake_obj=None)

    def _test_get_user_sid_and_domain(self, ret_val):
        cbSid = mock.Mock()
        sid = mock.Mock()
        size = 1024
        cchReferencedDomainName = mock.Mock()
        domainName = mock.Mock()
        sidNameUse = mock.Mock()

        ctypes.create_string_buffer = mock.MagicMock(return_value=sid)
        ctypes.sizeof = mock.MagicMock(return_value=size)
        wintypes.DWORD = mock.MagicMock(return_value=cchReferencedDomainName)
        ctypes.create_unicode_buffer = mock.MagicMock(return_value=domainName)

        ctypes.byref = mock.MagicMock()

        windll.advapi32.LookupAccountNameW = mock.MagicMock(
            return_value=ret_val)
        if ret_val is None:
            self.assertRaises(
                Exception, self._winutils._get_user_sid_and_domain,
                self._USERNAME)
        else:
            response = self._winutils._get_user_sid_and_domain(self._USERNAME)

            windll.advapi32.LookupAccountNameW.assert_called_with(
                0, unicode(self._USERNAME), sid, ctypes.byref(cbSid),
                domainName, ctypes.byref(cchReferencedDomainName),
                ctypes.byref(sidNameUse))
            self.assertEqual(response, (sid, domainName.value))

    def test_get_user_sid_and_domain(self):
        fake_obj = mock.Mock()
        self._test_get_user_sid_and_domain(ret_val=fake_obj)

    def test_get_user_sid_and_domain_no_return_value(self):
        self._test_get_user_sid_and_domain(ret_val=None)

    def _test_add_user_to_local_group(self, ret_value):
        windows_utils.Win32_LOCALGROUP_MEMBERS_INFO_3 = mock.MagicMock()
        lmi = windows_utils.Win32_LOCALGROUP_MEMBERS_INFO_3()
        group_name = 'Admins'

        windll.netapi32.NetLocalGroupAddMembers = mock.MagicMock(
            return_value=ret_value)

        if ret_value is not 0:
            self.assertRaises(
                Exception, self._winutils.add_user_to_local_group,
                self._USERNAME, group_name)
        else:
            ctypes.addressof = mock.MagicMock()
            self._winutils.add_user_to_local_group(self._USERNAME,
                                                   group_name)
            windll.netapi32.NetLocalGroupAddMembers.assert_called_with(
                0, unicode(group_name), 3, ctypes.addressof(lmi), 1)
            self.assertEqual(lmi.lgrmi3_domainandname, unicode(self._USERNAME))

    def test_add_user_to_local_group_no_error(self):
        self._test_add_user_to_local_group(ret_value=0)

    def test_add_user_to_local_group_not_found(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.NERR_GroupNotFound)

    def test_add_user_to_local_group_access_denied(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_ACCESS_DENIED)

    def test_add_user_to_local_group_no_member(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_NO_SUCH_MEMBER)

    def test_add_user_to_local_group_member_in_alias(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_MEMBER_IN_ALIAS)

    def test_add_user_to_local_group_invalid_member(self):
        self._test_add_user_to_local_group(
            ret_value=self._winutils.ERROR_INVALID_MEMBER)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_user_wmi_object')
    def _test_get_user_sid(self, mock_get_user_wmi_object, fail):
        r = mock.Mock()
        if not fail:
            mock_get_user_wmi_object.return_value = None
            response = self._winutils.get_user_sid(self._USERNAME)
            self.assertTrue(response is None)
        else:
            mock_get_user_wmi_object.return_value = r
            response = self._winutils.get_user_sid(self._USERNAME)
            self.assertTrue(response is not None)
        mock_get_user_wmi_object.assert_called_with(self._USERNAME)

    def test_get_user_sid(self):
        self._test_get_user_sid(fail=False)

    def test_get_user_sid_fail(self):
        self._test_get_user_sid(fail=True)

    def _test_create_user_logon_session(self, logon, loaduser,
                                        load_profile=True):
        wintypes.HANDLE = mock.MagicMock()
        pi = windows_utils.Win32_PROFILEINFO()
        windll.advapi32.LogonUserW = mock.MagicMock(return_value=logon)
        ctypes.byref = mock.MagicMock()

        if not logon:
            self.assertRaises(
                Exception, self._winutils.create_user_logon_session,
                self._USERNAME, self._PASSWORD, domain='.',
                load_profile=load_profile)

        elif load_profile and not loaduser:
            windll.userenv.LoadUserProfileW = mock.MagicMock(
                return_value=None)
            windll.kernel32.CloseHandle = mock.MagicMock(return_value=None)
            self.assertRaises(Exception,
                              self._winutils.create_user_logon_session,
                              self._USERNAME, self._PASSWORD, domain='.',
                              load_profile=load_profile)

            windll.userenv.LoadUserProfileW.assert_called_with(
                wintypes.HANDLE(), ctypes.byref(pi))
            windll.kernel32.CloseHandle.assert_called_with(wintypes.HANDLE())

        elif not load_profile:
            response = self._winutils.create_user_logon_session(
                self._USERNAME, self._PASSWORD, domain='.',
                load_profile=load_profile)
            self.assertTrue(response is not None)
        else:
            size = 1024
            windll.userenv.LoadUserProfileW = mock.MagicMock()
            ctypes.sizeof = mock.MagicMock(return_value=size)
            windows_utils.Win32_PROFILEINFO = mock.MagicMock(
                return_value=loaduser)

            response = self._winutils.create_user_logon_session(
                self._USERNAME, self._PASSWORD, domain='.',
                load_profile=load_profile)

            windll.userenv.LoadUserProfileW.assert_called_with(
                wintypes.HANDLE(), ctypes.byref(pi))
            self.assertTrue(response is not None)

    def test_create_user_logon_session_fail_load_false(self):
        self._test_create_user_logon_session(0, 0, True)

    def test_create_user_logon_session_fail_load_true(self):
        self._test_create_user_logon_session(0, 0, False)

    def test_create_user_logon_session_load_true(self):
        m = mock.Mock()
        n = mock.Mock()
        self._test_create_user_logon_session(m, n, True)

    def test_create_user_logon_session_load_false(self):
        m = mock.Mock()
        n = mock.Mock()
        self._test_create_user_logon_session(m, n, False)

    def test_create_user_logon_session_no_load_true(self):
        m = mock.Mock()
        self._test_create_user_logon_session(m, None, True)

    def test_create_user_logon_session_no_load_false(self):
        m = mock.Mock()
        self._test_create_user_logon_session(m, None, False)

    def test_close_user_logon_session(self):
        token = mock.Mock()
        windll.kernel32.CloseHandle = mock.MagicMock()
        self._winutils.close_user_logon_session(token)
        windll.kernel32.CloseHandle.assert_called_with(token)

    @mock.patch('ctypes.windll.kernel32.SetComputerNameExW')
    def _test_set_host_name(self, mock_SetComputerNameExW, ret_value):
        mock_SetComputerNameExW.return_value = ret_value
        if not ret_value:
            self.assertRaises(Exception, self._winutils.set_host_name,
                              'fake name')
        else:
            self._winutils.set_host_name('fake name')
        mock_SetComputerNameExW.assert_called_with(
            self._winutils.ComputerNamePhysicalDnsHostname,
            unicode('fake name'))

    def test_set_host_name(self):
        self._test_set_host_name(ret_value='fake response')

    def test_set_host_exception(self):
        self._test_set_host_name(ret_value=None)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_user_sid')
    def _test_get_user_home(self, mock_get_user_sid, user_sid):
        key = mock.MagicMock()
        mock_get_user_sid.return_value = user_sid
        _winreg.OpenKey = mock.MagicMock(return_value=key)
        _winreg.QueryValueEx = mock.MagicMock()
        response = self._winutils.get_user_home(self._USERNAME)
        if user_sid:
            mock_get_user_sid.assert_called_with(self._USERNAME)
            _winreg.OpenKey.assert_called_with(
                _winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows '
                                            'NT\\CurrentVersion\\ProfileList\\'
                                            '%s' % mock_get_user_sid())
            self.assertTrue(response is not None)
            _winreg.QueryValueEx.assert_called_with(
                _winreg.OpenKey().__enter__(), 'ProfileImagePath')
        else:
            self.assertTrue(response is None)

    def test_get_user_home(self):
        user = mock.MagicMock()
        self._test_get_user_home(user_sid=user)

    def test_get_user_home_fail(self):
        self._test_get_user_home(user_sid=None)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.check_os_version')
    @mock.patch('wmi.WMI')
    def _test_get_network_adapters(self, is_xp_2003, mock_WMI,
                                   mock_check_os_version):
        mock_WMI.return_value = self._conn
        mock_response = mock.MagicMock()
        self._conn.query.return_value = [mock_response]

        mock_check_os_version.return_value = not is_xp_2003

        wql = ('SELECT * FROM Win32_NetworkAdapter WHERE '
               'AdapterTypeId = 0 AND MACAddress IS NOT NULL')

        if not is_xp_2003:
            wql += ' AND PhysicalAdapter = True'

        response = self._winutils.get_network_adapters()
        self._conn.query.assert_called_with(wql)
        self.assertEqual(response, [mock_response.Name])

    def test_get_network_adapters(self):
        self._test_get_network_adapters(False)

    def test_get_network_adapters_xp_2003(self):
        self._test_get_network_adapters(True)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._sanitize_wmi_input')
    def _test_set_static_network_config(self, mock_sanitize_wmi_input,
                                        adapter, ret_val1=None,
                                        ret_val2=None, ret_val3=None):
        wmi.WMI = mock.MagicMock(return_value=self._conn)
        address = '10.10.10.10'
        adapter_name = 'adapter_name'
        broadcast = '0.0.0.0'
        dns_list = ['8.8.8.8']

        if not adapter:
            self.assertRaises(
                Exception, self._winutils.set_static_network_config,
                adapter_name, address, self._NETMASK,
                broadcast, self._GATEWAY, dns_list)
        else:
            mock_sanitize_wmi_input.return_value = adapter_name
            self._conn.query.return_value = adapter
            adapter_config = adapter[0].associators()[0]
            adapter_config.EnableStatic = mock.MagicMock(return_value=ret_val1)
            adapter_config.SetGateways = mock.MagicMock(return_value=ret_val2)
            adapter_config.SetDNSServerSearchOrder = mock.MagicMock(
                return_value=ret_val3)
            adapter.__len__ = mock.MagicMock(return_value=1)
            if ret_val1[0] > 1:
                self.assertRaises(
                    Exception, self._winutils.set_static_network_config,
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)

            elif ret_val2[0] > 1:
                self.assertRaises(
                    Exception, self._winutils.set_static_network_config,
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)

            elif ret_val3[0] > 1:
                self.assertRaises(
                    Exception, self._winutils.set_static_network_config,
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)

            else:
                response = self._winutils.set_static_network_config(
                    adapter_name, address, self._NETMASK,
                    broadcast, self._GATEWAY, dns_list)
                if ret_val1[0] or ret_val2[0] or ret_val3[0] == 1:
                    self.assertTrue(response)
                else:
                    self.assertFalse(response)
                adapter_config.EnableStatic.assert_called_with(
                    [address], [self._NETMASK])
                adapter_config.SetGateways.assert_called_with(
                    [self._GATEWAY], [1])
                adapter_config.SetDNSServerSearchOrder.assert_called_with(
                    dns_list)

                self._winutils._sanitize_wmi_input.assert_called_with(
                    adapter_name)
                adapter[0].associators.assert_called_with(
                    wmi_result_class='Win32_NetworkAdapterConfiguration')
                self._conn.query.assert_called_with(
                    'SELECT * FROM Win32_NetworkAdapter WHERE MACAddress IS '
                    'NOT NULL AND Name = \'%(adapter_name_san)s\'' %
                    {'adapter_name_san': adapter_name})

    def test_set_static_network_config(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (1,)
        ret_val3 = (0,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2,
                                             ret_val3=ret_val3)

    def test_set_static_network_config_query_fail(self):
        self._test_set_static_network_config(adapter=None)

    def test_set_static_network_config_cannot_set_ip(self):
        adapter = mock.MagicMock()
        ret_val1 = (2,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1)

    def test_set_static_network_config_cannot_set_gateway(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (2,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2)

    def test_set_static_network_config_cannot_set_DNS(self):
        adapter = mock.MagicMock()
        ret_val1 = (1,)
        ret_val2 = (1,)
        ret_val3 = (2,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2,
                                             ret_val3=ret_val3)

    def test_set_static_network_config_no_reboot(self):
        adapter = mock.MagicMock()
        ret_val1 = (0,)
        ret_val2 = (0,)
        ret_val3 = (0,)
        self._test_set_static_network_config(adapter=adapter,
                                             ret_val1=ret_val1,
                                             ret_val2=ret_val2,
                                             ret_val3=ret_val3)

    def _test_get_config_key_name(self, section):
        response = self._winutils._get_config_key_name(section)
        if section:
            self.assertEqual(
                response, self._winutils._config_key + section + '\\')
        else:
            self.assertEqual(response, self._winutils._config_key)

    def test_get_config_key_name_with_section(self):
        self._test_get_config_key_name(self._SECTION)

    def test_get_config_key_name_no_section(self):
        self._test_get_config_key_name(None)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_config_key_name')
    def _test_set_config_value(self, mock_get_config_key_name, value):
        key = mock.MagicMock()
        key_name = self._winutils._config_key + self._SECTION + '\\' + self\
            ._CONFIG_NAME
        mock_get_config_key_name.return_value = key_name

        _winreg.CreateKey = mock.MagicMock()
        _winreg.REG_DWORD = mock.Mock()
        _winreg.REG_SZ = mock.Mock()
        _winreg.SetValueEx = mock.MagicMock()

        self._winutils.set_config_value(self._CONFIG_NAME, value,
                                        self._SECTION)

        _winreg.CreateKey.__enter__.return_value = key
        with _winreg.CreateKey as m:
            assert m == key

        _winreg.CreateKey.__enter__.assert_called_with()
        _winreg.CreateKey.__exit__.assert_called_with(None, None, None)
        _winreg.CreateKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                             key_name)
        mock_get_config_key_name.assert_called_with(self._SECTION)
        if type(value) == int:
            _winreg.SetValueEx.assert_called_with(
                _winreg.CreateKey().__enter__(), self._CONFIG_NAME, 0,
                _winreg.REG_DWORD, value)
        else:
            _winreg.SetValueEx.assert_called_with(
                _winreg.CreateKey().__enter__(), self._CONFIG_NAME, 0,
                _winreg.REG_SZ, value)

    def test_set_config_value_int(self):
        self._test_set_config_value(value=1)

    def test_set_config_value_not_int(self):
        self._test_set_config_value(value='1')

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_config_key_name')
    def _test_get_config_value(self, mock_get_config_key_name, value):
        key_name = self._winutils._config_key + self._SECTION + '\\'
        key_name += self._CONFIG_NAME
        _winreg.OpenKey = mock.MagicMock()
        _winreg.REG_DWORD = mock.Mock()
        _winreg.REG_SZ = mock.Mock()
        if type(value) == int:
            regtype = _winreg.REG_DWORD
        else:
            regtype = _winreg.REG_SZ
        _winreg.QueryValueEx = mock.MagicMock(return_value=(value, regtype))
        if value is None:
            mock_get_config_key_name.side_effect = [WindowsError]
            self.assertRaises(WindowsError, self._winutils.get_config_value,
                              self._CONFIG_NAME, None)
        else:
            mock_get_config_key_name.return_value = key_name
            response = self._winutils.get_config_value(self._CONFIG_NAME,
                                                       self._SECTION)
            _winreg.OpenKey.assert_called_with(_winreg.HKEY_LOCAL_MACHINE,
                                               key_name)
            mock_get_config_key_name.assert_called_with(self._SECTION)
            _winreg.QueryValueEx.assert_called_with(
                _winreg.OpenKey().__enter__(), self._CONFIG_NAME)
            self.assertEqual(response, value)

    def test_get_config_value_type_int(self):
        self._test_get_config_value(value=1)

    def test_get_config_value_type_str(self):
        self._test_get_config_value(value='fake')

    def test_get_config_value_type_error(self):
        self._test_get_config_value(value=None)

    def _test_wait_for_boot_completion(self, ret_val):
        key = mock.MagicMock()
        time.sleep = mock.MagicMock()
        _winreg.OpenKey = mock.MagicMock()
        _winreg.QueryValueEx = mock.MagicMock()
        _winreg.QueryValueEx.side_effect = ret_val
        self._winutils.wait_for_boot_completion()
        _winreg.OpenKey.__enter__.return_value = key
        _winreg.OpenKey.assert_called_with(
            _winreg.HKEY_LOCAL_MACHINE,
            "SYSTEM\\Setup\\Status\\SysprepStatus", 0, _winreg.KEY_READ)

        _winreg.QueryValueEx.assert_called_with(
            _winreg.OpenKey().__enter__(), "GeneralizationState")

    def test_wait_for_boot_completion(self):
        ret_val = [[7]]
        self._test_wait_for_boot_completion(ret_val)

    @mock.patch('wmi.WMI')
    def test_get_service(self, mock_WMI):
        mock_WMI.return_value = self._conn
        self._conn.Win32_Service.return_value = ['fake name']
        response = self._winutils._get_service('fake name')
        mock_WMI.assert_called_with(moniker='//./root/cimv2')
        self._conn.Win32_Service.assert_called_with(Name='fake name')
        self.assertEqual(response, 'fake name')

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def test_check_service_exists(self, mock_get_service):
        mock_get_service.return_value = 'not None'
        response = self._winutils.check_service_exists('fake name')
        self.assertEqual(response, True)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def test_get_service_status(self, mock_get_service):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        response = self._winutils.get_service_status('fake name')
        self.assertEqual(response, mock_service.State)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def test_get_service_start_mode(self, mock_get_service):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        response = self._winutils.get_service_start_mode('fake name')
        self.assertEqual(response, mock_service.StartMode)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def _test_set_service_start_mode(self, mock_get_service, ret_val):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.ChangeStartMode.return_value = (ret_val,)
        if ret_val != 0:
            self.assertRaises(Exception,
                              self._winutils.set_service_start_mode,
                              'fake name', 'fake mode')
        else:
            self._winutils.set_service_start_mode('fake name', 'fake mode')
        mock_service.ChangeStartMode.assert_called_once_with('fake mode')

    def test_set_service_start_mode(self):
        self._test_set_service_start_mode(ret_val=0)

    def test_set_service_start_mode_exception(self):
        self._test_set_service_start_mode(ret_val=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def _test_start_service(self, mock_get_service, ret_val):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.StartService.return_value = (ret_val,)
        if ret_val != 0:
            self.assertRaises(Exception,
                              self._winutils.start_service,
                              'fake name')
        else:
            self._winutils.start_service('fake name')
        mock_service.StartService.assert_called_once_with()

    def test_start_service(self):
        self._test_set_service_start_mode(ret_val=0)

    def test_start_service_exception(self):
        self._test_set_service_start_mode(ret_val=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_service')
    def _test_stop_service(self, mock_get_service, ret_val):
        mock_service = mock.MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.StopService.return_value = (ret_val,)
        if ret_val != 0:
            self.assertRaises(Exception,
                              self._winutils.stop_service,
                              'fake name')
        else:
            self._winutils.stop_service('fake name')
        mock_service.StopService.assert_called_once_with()

    def test_stop_service(self):
        self._test_stop_service(ret_val=0)

    def test_stop_service_exception(self):
        self._test_stop_service(ret_val=1)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.stop_service')
    def test_terminate(self, mock_stop_service):
        time.sleep = mock.MagicMock()
        self._winutils.terminate()
        mock_stop_service.assert_called_with(self._winutils._service_name)
        time.sleep.assert_called_with(3)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_ipv4_routing_table')
    def _test_get_default_gateway(self, mock_get_ipv4_routing_table,
                                  routing_table):
        mock_get_ipv4_routing_table.return_value = [routing_table]
        response = self._winutils.get_default_gateway()
        mock_get_ipv4_routing_table.assert_called_once_with()
        if routing_table[0] == '0.0.0.0':
            self.assertEqual(response, (routing_table[3], routing_table[2]))
        else:
            self.assertEqual(response, (None, None))

    def test_get_default_gateway(self):
        routing_table = ['0.0.0.0', '1.1.1.1', self._GATEWAY, '8.8.8.8']
        self._test_get_default_gateway(routing_table=routing_table)

    def test_get_default_gateway_error(self):
        routing_table = ['1.1.1.1', '1.1.1.1', self._GATEWAY, '8.8.8.8']
        self._test_get_default_gateway(routing_table=routing_table)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '._get_ipv4_routing_table')
    def _test_check_static_route_exists(self, mock_get_ipv4_routing_table,
                                        routing_table):
        mock_get_ipv4_routing_table.return_value = [routing_table]
        response = self._winutils.check_static_route_exists(self._DESTINATION)
        mock_get_ipv4_routing_table.assert_called_once_with()
        if routing_table[0] == self._DESTINATION:
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_check_static_route_exists_true(self):
        routing_table = [self._DESTINATION, '1.1.1.1', self._GATEWAY,
                         '8.8.8.8']
        self._test_check_static_route_exists(routing_table=routing_table)

    def test_check_static_route_exists_false(self):
        routing_table = ['0.0.0.0', '1.1.1.1', self._GATEWAY, '8.8.8.8']
        self._test_check_static_route_exists(routing_table=routing_table)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_add_static_route(self, mock_execute_process, err):
        next_hop = '10.10.10.10'
        interface_index = 1
        metric = 9
        args = ['ROUTE', 'ADD', self._DESTINATION, 'MASK', self._NETMASK,
                next_hop]
        mock_execute_process.return_value = (None, err, None)
        if err:
            self.assertRaises(Exception, self._winutils.add_static_route,
                              self._DESTINATION, self._NETMASK, next_hop,
                              interface_index, metric)
        else:
            self._winutils.add_static_route(self._DESTINATION, self._NETMASK,
                                            next_hop, interface_index, metric)
            mock_execute_process.assert_called_with(args)

    def test_add_static_route(self):
        self._test_add_static_route(err=404)

    def test_add_static_route_fail(self):
        self._test_add_static_route(err=None)

    @mock.patch('ctypes.sizeof')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.windll.kernel32.VerSetConditionMask')
    @mock.patch('ctypes.windll.kernel32.VerifyVersionInfoW')
    @mock.patch('ctypes.windll.kernel32.GetLastError')
    def _test_check_os_version(self, mock_GetLastError,
                               mock_VerifyVersionInfoW,
                               mock_VerSetConditionMask, mock_byref,
                               mock_sizeof, ret_value, error_value=None):
        mock_VerSetConditionMask.return_value = 2
        mock_VerifyVersionInfoW.return_value = ret_value
        mock_GetLastError.return_value = error_value
        old_version = self._winutils.ERROR_OLD_WIN_VERSION
        if error_value and error_value is not old_version:
            self.assertRaises(Exception, self._winutils.check_os_version, 3,
                              1, 2)
            mock_GetLastError.assert_called_once_with()
        else:
            response = self._winutils.check_os_version(3, 1, 2)
            mock_sizeof.assert_called_once_with(
                windows_utils.Win32_OSVERSIONINFOEX_W)
            self.assertEqual(mock_VerSetConditionMask.call_count, 3)
            mock_VerifyVersionInfoW.assert_called_with(mock_byref(),
                                                       1 | 2 | 3 | 7,
                                                       2)
            if error_value is old_version:
                mock_GetLastError.assert_called_with()
                self.assertEqual(response, False)
            else:
                self.assertEqual(response, True)

    def test_check_os_version(self):
        m = mock.MagicMock()
        self._test_check_os_version(ret_value=m)

    def test_check_os_version_expect_False(self):
        self._test_check_os_version(
            ret_value=None, error_value=self._winutils.ERROR_OLD_WIN_VERSION)

    def test_check_os_version_exception(self):
        self._test_check_os_version(ret_value=None, error_value=9999)

    def _test_get_volume_label(self, ret_val):
        label = mock.MagicMock()
        max_label_size = 261
        drive = 'Fake_drive'
        ctypes.create_unicode_buffer = mock.MagicMock(return_value=label)
        ctypes.windll.kernel32.GetVolumeInformationW = mock.MagicMock(
            return_value=ret_val)
        response = self._winutils.get_volume_label(drive)
        if ret_val:
            self.assertTrue(response is not None)
        else:
            self.assertTrue(response is None)

        ctypes.create_unicode_buffer.assert_called_with(max_label_size)
        ctypes.windll.kernel32.GetVolumeInformationW.assert_called_with(
            drive, label, max_label_size, 0, 0, 0, 0, 0)

    def test_get_volume_label(self):
        self._test_get_volume_label('ret')

    def test_get_volume_label_no_return_value(self):
        self._test_get_volume_label(None)

    @mock.patch('re.search')
    @mock.patch('cloudbaseinit.osutils.base.BaseOSUtils.'
                'generate_random_password')
    def test_generate_random_password(self, mock_generate_random_password,
                                      mock_search):
        length = 14
        mock_search.return_value = True
        mock_generate_random_password.return_value = 'Passw0rd'
        response = self._winutils.generate_random_password(length)
        mock_generate_random_password.assert_called_once_with(length)
        self.assertEqual(response, 'Passw0rd')

    @mock.patch('ctypes.create_unicode_buffer')
    @mock.patch('ctypes.windll.kernel32.GetLogicalDriveStringsW')
    def _test_get_logical_drives(self, mock_GetLogicalDriveStringsW,
                                 mock_create_unicode_buffer, buf_length):
        mock_buf = mock.MagicMock()
        mock_buf.__getitem__.side_effect = ['1', '\x00']
        mock_create_unicode_buffer.return_value = mock_buf
        mock_GetLogicalDriveStringsW.return_value = buf_length
        if buf_length is None:
            self.assertRaises(Exception, self._winutils._get_logical_drives)
        else:
            response = self._winutils._get_logical_drives()
            print mock_buf.mock_calls
            mock_create_unicode_buffer.assert_called_with(261)
            mock_GetLogicalDriveStringsW.assert_called_with(260, mock_buf)
            self.assertEqual(response, ['1'])

    def test_get_logical_drives_exception(self):
        self._test_get_logical_drives(buf_length=None)

    def test_get_logical_drives(self):
        self._test_get_logical_drives(buf_length=2)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils.'
                '_get_logical_drives')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32')
    def test_get_cdrom_drives(self, mock_kernel32, mock_get_logical_drives):
        mock_get_logical_drives.return_value = ['drive']
        mock_kernel32.GetDriveTypeW.return_value = self._winutils.DRIVE_CDROM
        response = self._winutils.get_cdrom_drives()
        mock_get_logical_drives.assert_called_with()
        self.assertEqual(response, ['drive'])

    @mock.patch('cloudbaseinit.osutils.windows.msvcrt')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32')
    @mock.patch('cloudbaseinit.osutils.windows.setupapi')
    @mock.patch('cloudbaseinit.osutils.windows.Win32_STORAGE_DEVICE_NUMBER')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.sizeof')
    @mock.patch('ctypes.wintypes.DWORD')
    @mock.patch('ctypes.cast')
    @mock.patch('ctypes.POINTER')
    def _test_get_physical_disks(self, mock_POINTER, mock_cast,
                                 mock_DWORD, mock_sizeof, mock_byref,
                                 mock_sdn, mock_setupapi, mock_kernel32,
                                 mock_msvcrt, handle_disks, last_error,
                                 interface_detail, disk_handle, io_control):

        sizeof_calls = [mock.call(
            windows_utils.Win32_SP_DEVICE_INTERFACE_DATA),
                        mock.call(mock_sdn())]
        device_interfaces_calls = [mock.call(handle_disks, None, mock_byref(),
                                             0, mock_byref()),
                                   mock.call(handle_disks, None, mock_byref(),
                                             1, mock_byref())]
        cast_calls = [mock.call(),
                      mock.call(mock_msvcrt.malloc(), mock_POINTER()),
                      mock.call(mock_cast().contents.DevicePath,
                                wintypes.LPWSTR)]

        mock_setup_interface = mock_setupapi.SetupDiGetDeviceInterfaceDetailW

        mock_setupapi.SetupDiGetClassDevsW.return_value = handle_disks
        mock_kernel32.GetLastError.return_value = last_error
        mock_setup_interface.return_value = interface_detail
        mock_kernel32.CreateFileW.return_value = disk_handle
        mock_kernel32.DeviceIoControl.return_value = io_control

        mock_setupapi.SetupDiEnumDeviceInterfaces.side_effect = [True, False]

        if handle_disks == self._winutils.INVALID_HANDLE_VALUE \
            or last_error != self._winutils.ERROR_INSUFFICIENT_BUFFER \
            and not interface_detail \
            or disk_handle == self._winutils.INVALID_HANDLE_VALUE \
            or not io_control:

            self.assertRaises(Exception, self._winutils.get_physical_disks)

        else:
            response = self._winutils.get_physical_disks()
            self.assertEqual(mock_sizeof.call_args_list, sizeof_calls)
            self.assertEqual(
                mock_setupapi.SetupDiEnumDeviceInterfaces.call_args_list,
                device_interfaces_calls)
            if not interface_detail:
                mock_kernel32.GetLastError.assert_called_once_with()

            mock_POINTER.assert_called_with(
                windows_utils.Win32_SP_DEVICE_INTERFACE_DETAIL_DATA_W)
            mock_msvcrt.malloc.assert_called_with(mock_DWORD())

            self.assertEqual(mock_cast.call_args_list, cast_calls)

            mock_setup_interface.assert_called_with(handle_disks, mock_byref(),
                                                    mock_cast(),mock_DWORD(),
                                                    None, None)
            mock_kernel32.CreateFileW.assert_called_with(
                mock_cast().value, 0, self._winutils.FILE_SHARE_READ, None,
                self._winutils.OPEN_EXISTING, 0, 0)
            mock_sdn.assert_called_with()

            mock_kernel32.DeviceIoControl.assert_called_with(
                disk_handle, self._winutils.IOCTL_STORAGE_GET_DEVICE_NUMBER,
                None, 0, mock_byref(), mock_sizeof(), mock_byref(), None)
            self.assertEqual(response, ["\\\\.\PHYSICALDRIVE1"])
            mock_setupapi.SetupDiDestroyDeviceInfoList.assert_called_once_with(
                handle_disks)

        mock_setupapi.SetupDiGetClassDevsW.assert_called_once_with(
            mock_byref(), None, None, self._winutils.DIGCF_PRESENT |
            self._winutils.DIGCF_DEVICEINTERFACE)



    def test_get_physical_disks(self):
        mock_handle_disks = mock.MagicMock()
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=mock_disk_handle, io_control=True)

    def test_get_physical_disks_other_error_and_no_interface_detail(self):
        mock_handle_disks = mock.MagicMock()
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error='other', interface_detail=None,
            disk_handle=mock_disk_handle, io_control=True)

    def test_get_physical_disks_invalid_disk_handle(self):
        mock_handle_disks = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=self._winutils.INVALID_HANDLE_VALUE, io_control=True)

    def test_get_physical_disks_io_control(self):
        mock_handle_disks = mock.MagicMock()
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=mock_handle_disks,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=mock_disk_handle, io_control=False)

    def test_get_physical_disks_handle_disks_invalid(self):
        mock_disk_handle = mock.MagicMock()
        self._test_get_physical_disks(
            handle_disks=self._winutils.INVALID_HANDLE_VALUE ,
            last_error=self._winutils.ERROR_INSUFFICIENT_BUFFER,
            interface_detail='fake interface detail',
            disk_handle=mock_disk_handle, io_control=True)

    @mock.patch('win32com.client.Dispatch')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils._get_fw_protocol')
    def _test_firewall_create_rule(self, mock_get_fw_protocol, mock_Dispatch):
        self._winutils.firewall_create_rule(
            name='fake name', port=9999, protocol=self._winutils.PROTOCOL_TCP)
        expected = [mock.call("HNetCfg.FWOpenPort"),
                    mock.call("HNetCfg.FwMgr")]
        self.assertEqual(mock_Dispatch.call_args_list, expected)
        mock_get_fw_protocol.assert_called_once_with(
            self._winutils.PROTOCOL_TCP)

    @mock.patch('win32com.client.Dispatch')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils._get_fw_protocol')
    def test_firewall_remove_rule(self, mock_get_fw_protocol, mock_Dispatch):
        self._winutils.firewall_remove_rule(
            name='fake name', port=9999, protocol=self._winutils.PROTOCOL_TCP)
        mock_Dispatch.assert_called_once_with("HNetCfg.FwMgr")
        mock_get_fw_protocol.assert_called_once_with(
            self._winutils.PROTOCOL_TCP)

    @mock.patch('ctypes.wintypes.BOOL')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32.IsWow64Process')
    @mock.patch('cloudbaseinit.osutils.windows.kernel32.GetCurrentProcess')
    @mock.patch('ctypes.byref')
    def _test_is_wow64(self, mock_byref, mock_GetCurrentProcess,
                       mock_IsWow64Process, mock_BOOL, ret_val):
        mock_IsWow64Process.return_value = ret_val
        mock_BOOL().value = ret_val
        if ret_val is False:
            self.assertRaises(Exception, self._winutils.is_wow64)
        else:
            response = self._winutils.is_wow64()
            mock_byref.assert_called_once_with(mock_BOOL())
            mock_IsWow64Process.assert_called_once_with(
                mock_GetCurrentProcess(), mock_byref())
            self.assertEqual(response, True)

    def test_is_wow64(self):
        self._test_is_wow64(ret_val=True)

    def test_is_wow64_exception(self):
        self._test_is_wow64(ret_val=False)

    @mock.patch('os.path.expandvars')
    def test_get_system32_dir(self, mock_expandvars):
        mock_expandvars.return_value = 'fake_system32'
        response = self._winutils.get_system32_dir()
        self.assertEqual(response, 'fake_system32')

    @mock.patch('os.path.expandvars')
    def test_get_sysnative_dir(self, mock_expandvars):
        mock_expandvars.return_value = 'fake_sysnative'
        response = self._winutils.get_sysnative_dir()
        self.assertEqual(response, 'fake_sysnative')

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_sysnative_dir')
    @mock.patch('os.path.isdir')
    def test_check_sysnative_dir_exists(self, mock_isdir,
                                        mock_get_sysnative_dir):
        mock_get_sysnative_dir.return_value = 'fake_sysnative'
        mock_isdir.return_value = True
        response = self._winutils.check_sysnative_dir_exists()
        self.assertEqual(response, True)

    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.check_sysnative_dir_exists')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_sysnative_dir')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.get_system32_dir')
    @mock.patch('cloudbaseinit.osutils.windows.WindowsUtils'
                '.execute_process')
    def _test_execute_powershell_script(self, mock_execute_process,
                                        mock_get_system32_dir,
                                        mock_get_sysnative_dir,
                                        mock_check_sysnative_dir_exists,
                                        ret_val):
        mock_check_sysnative_dir_exists.return_value = ret_val
        mock_get_sysnative_dir.return_value = 'fake'
        mock_get_system32_dir.return_value = 'fake'
        fake_path = os.path.join('fake', 'WindowsPowerShell\\v1.0\\'
                                         'powershell.exe')
        args = [fake_path, '-ExecutionPolicy', 'RemoteSigned',
                '-NonInteractive', '-File', 'fake_script_path']
        response = self._winutils.execute_powershell_script(
            script_path='fake_script_path')
        if ret_val is True:
            mock_get_sysnative_dir.assert_called_once_with()
        else:
            mock_get_system32_dir.assert_called_once_with()
        mock_execute_process.assert_called_with(args, False)
        self.assertEqual(response, mock_execute_process())

    def test_execute_powershell_script_sysnative(self):
        self._test_execute_powershell_script(ret_val=True)

    def test_execute_powershell_script_system32(self):
        self._test_execute_powershell_script(ret_val=False)

########NEW FILE########
__FILENAME__ = test_factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import factory

CONF = cfg.CONF


class PluginFactoryTests(unittest.TestCase):

    @mock.patch('cloudbaseinit.utils.classloader.ClassLoader.load_class')
    def test_load_plugins(self, mock_load_class):
        expected = []
        for path in CONF.plugins:
            expected.append(mock.call(path))
        response = factory.load_plugins()
        self.assertEqual(mock_load_class.call_args_list, expected)
        self.assertTrue(response is not None)

########NEW FILE########
__FILENAME__ = test_createuser
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import createuser

CONF = cfg.CONF


class CreateUserPluginTests(unittest.TestCase):

    def setUp(self):
        self._create_user = createuser.CreateUserPlugin()

    def test_get_password(self):
        mock_osutils = mock.MagicMock()
        mock_osutils.generate_random_password.return_value = 'fake password'
        response = self._create_user._get_password(mock_osutils)
        mock_osutils.generate_random_password.assert_called_once_with(14)
        self.assertEqual(response, 'fake password')

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('cloudbaseinit.plugins.windows.createuser.CreateUserPlugin'
                '._get_password')
    def _test_execute(self, mock_get_password, mock_get_os_utils,
                      user_exists=True):
        CONF.set_override('groups', ['Admins'])
        shared_data = {}
        mock_token = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        mock_service = mock.MagicMock()
        mock_get_password.return_value = 'password'
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.user_exists.return_value = user_exists
        mock_osutils.create_user_logon_session.return_value = mock_token

        response = self._create_user.execute(mock_service, shared_data)

        mock_get_os_utils.assert_called_once_with()
        mock_get_password.assert_called_once_with(mock_osutils)
        mock_osutils.user_exists.assert_called_once_with(CONF.username)
        if user_exists:
            mock_osutils.set_user_password.assert_called_once_with(
                CONF.username, 'password')
        else:
            mock_osutils.create_user.assert_called_once_with(CONF.username,
                                                             'password')
            mock_osutils.create_user_logon_session.assert_called_once_with(
                CONF.username, 'password', True)
            mock_osutils.close_user_logon_session.assert_called_once_with(
                mock_token)
        mock_osutils.add_user_to_local_group.assert_called_once_with(
            CONF.username, CONF.groups[0])
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_execute_user_exists(self):
        self._test_execute(user_exists=True)

    def test_execute_no_user(self):
        self._test_execute(user_exists=False)

########NEW FILE########
__FILENAME__ = test_extendvolumes
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Cloudbase Solutions Srl
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

import importlib
import mock
import re
import sys
import unittest

from oslo.config import cfg

CONF = cfg.CONF

_ctypes_mock = mock.MagicMock()
_comtypes_mock = mock.MagicMock()


class ExtendVolumesPluginTests(unittest.TestCase):
    @mock.patch.dict(sys.modules, {'comtypes': _comtypes_mock,
                                   'ctypes': _ctypes_mock})
    def setUp(self):
        extendvolumes = importlib.import_module('cloudbaseinit.plugins.'
                                                'windows.extendvolumes')
        self._extend_volumes = extendvolumes.ExtendVolumesPlugin()

    def tearDown(self):
        reload(sys)

    @mock.patch('cloudbaseinit.plugins.windows.extendvolumes'
                '.ExtendVolumesPlugin._get_volume_index')
    @mock.patch('cloudbaseinit.plugins.windows.extendvolumes'
                '.ExtendVolumesPlugin._extend_volume')
    @mock.patch('cloudbaseinit.utils.windows.vds.IVdsVolume')
    def test_extend_volumes(self, _vds_mock, mock_extend_volume,
                            mock_get_volume_index):
        mock_pack = mock.MagicMock()
        mock_volume_idxs = mock.MagicMock()
        mock_enum = mock.MagicMock()
        mock_unk = mock.MagicMock()
        mock_c = mock.MagicMock()
        mock_volume = mock.MagicMock()
        mock_properties = mock.MagicMock()
        mock_pack.QueryVolumes.return_value = mock_enum
        mock_enum.Next.side_effect = [(mock_unk, mock_c), (None, None)]
        mock_unk.QueryInterface.return_value = mock_volume
        mock_volume.GetProperties.return_value = mock_properties
        _ctypes_mock.wstring_at.return_value = 'fake name'
        mock_get_volume_index.return_value = mock_volume_idxs
        self._extend_volumes._extend_volumes(mock_pack, [mock_volume_idxs])
        mock_pack.QueryVolumes.assert_called_once_with()
        mock_enum.Next.assert_called_with(1)
        mock_unk.QueryInterface.assert_called_once_with(_vds_mock)
        mock_volume.GetProperties.assert_called_once_with()
        _ctypes_mock.wstring_at.assert_called_with(mock_properties.pwszName)
        mock_get_volume_index.assert_called_once_with('fake name')
        mock_extend_volume.assert_called_once_with(mock_pack, mock_volume,
                                                   mock_properties)
        _ctypes_mock.windll.ole32.CoTaskMemFree.assert_called_once_with(
            mock_properties.pwszName)

    def test_get_volume_index(self):
        mock_value = mock.MagicMock()
        re.match = mock.MagicMock(return_value=mock_value)
        mock_value.group.return_value = '9999'
        response = self._extend_volumes._get_volume_index('$2')
        mock_value.group.assert_called_once_with(1)
        self.assertTrue(response == 9999)

    @mock.patch('cloudbaseinit.plugins.windows.extendvolumes'
                '.ExtendVolumesPlugin._get_volume_extents_to_resize')
    @mock.patch('cloudbaseinit.utils.windows.vds.VDS_INPUT_DISK')
    def test_extend_volume(self, mock_VDS_INPUT_DISK,
                           mock_get_volume_extents_to_resize):
        mock_disk = mock.MagicMock()
        mock_pack = mock.MagicMock()
        mock_volume = mock.MagicMock()
        mock_properties = mock.MagicMock()
        mock_volume_extent = mock.MagicMock()
        mock_async = mock.MagicMock()
        mock_get_volume_extents_to_resize.return_value = [(mock_volume_extent,
                                                           9999)]
        mock_VDS_INPUT_DISK.return_value = mock_disk
        mock_volume.Extend.return_value = mock_async

        self._extend_volumes._extend_volume(mock_pack, mock_volume,
                                            mock_properties)

        mock_get_volume_extents_to_resize.assert_called_once_with(
            mock_pack, mock_properties.id)
        _ctypes_mock.wstring_at.assert_called_with(mock_properties.pwszName)
        mock_volume.Extend.assert_called_once_with(
            mock_VDS_INPUT_DISK.__mul__()(), 1)
        mock_async.Wait.assert_called_once_with()

    @mock.patch('cloudbaseinit.utils.windows.vds.IVdsDisk')
    @mock.patch('cloudbaseinit.utils.windows.vds.VDS_DISK_EXTENT')
    def test_get_volume_extents_to_resize(self, mock_VDS_DISK_EXTENT,
                                          mock_IVdsDisk):
        mock_pack = mock.MagicMock()
        mock_extents_p = mock.MagicMock()
        mock_unk = mock.MagicMock()
        mock_c = mock.MagicMock()
        mock_disk = mock.MagicMock()
        mock_enum = mock.MagicMock()
        fake_volume_id = '$1'
        mock_array = mock.MagicMock()
        mock_array.volumeId = fake_volume_id
        mock_pack.QueryDisks.return_value = mock_enum
        mock_enum.Next.side_effect = [(mock_unk, mock_c), (None, None)]
        mock_unk.QueryInterface.return_value = mock_disk
        mock_disk.QueryExtents.return_value = (mock_extents_p,
                                               1)
        mock_VDS_DISK_EXTENT.__mul__().from_address.return_value = [mock_array]

        response = self._extend_volumes._get_volume_extents_to_resize(
            mock_pack, fake_volume_id)

        mock_pack.QueryDisks.assert_called_once_with()
        mock_enum.Next.assert_called_with(1)
        mock_unk.QueryInterface.assert_called_once_with(mock_IVdsDisk)
        _ctypes_mock.addressof.assert_called_with(mock_extents_p.contents)
        mock_VDS_DISK_EXTENT.__mul__().from_address.assert_called_with(
            _ctypes_mock.addressof(mock_extents_p.contents))

        _ctypes_mock.pointer.assert_called_once_with(
            mock_VDS_DISK_EXTENT())
        self.assertEqual(response, [])

        _ctypes_mock.windll.ole32.CoTaskMemFree.assert_called_with(
            mock_extents_p)

    @mock.patch('cloudbaseinit.utils.windows.vds.'
                'VDS_QUERY_SOFTWARE_PROVIDERS')
    @mock.patch('cloudbaseinit.utils.windows.vds.IVdsSwProvider')
    def test_query_providers(self, mock_IVdsSwProvider,
                             mock_VDS_QUERY_SOFTWARE_PROVIDERS):
        mock_svc = mock.MagicMock()
        mock_enum = mock.MagicMock()
        mock_unk = mock.MagicMock()
        mock_c = mock.MagicMock()
        mock_svc.QueryProviders.return_value = mock_enum
        mock_enum.Next.side_effect = [(mock_unk, mock_c), (None, None)]
        mock_unk.QueryInterface.return_value = 'fake providers'

        response = self._extend_volumes._query_providers(mock_svc)
        mock_svc.QueryProviders.assert_called_once_with(
            mock_VDS_QUERY_SOFTWARE_PROVIDERS)
        mock_enum.Next.assert_called_with(1)
        mock_unk.QueryInterface.assert_called_once_with(mock_IVdsSwProvider)
        self.assertEqual(response, ['fake providers'])

    @mock.patch('cloudbaseinit.utils.windows.vds.IVdsPack')
    def test_query_packs(self, mock_IVdsPack):
        mock_provider = mock.MagicMock()
        mock_enum = mock.MagicMock()
        mock_unk = mock.MagicMock()
        mock_c = mock.MagicMock()
        mock_provider.QueryPacks.return_value = mock_enum
        mock_enum.Next.side_effect = [(mock_unk, mock_c), (None, None)]
        mock_unk.QueryInterface.return_value = 'fake packs'

        response = self._extend_volumes._query_packs(mock_provider)

        mock_provider.QueryPacks.assert_called_once_with()
        mock_enum.Next.assert_called_with(1)
        mock_unk.QueryInterface.assert_called_once_with(mock_IVdsPack)
        self.assertEqual(response, ['fake packs'])

    def test_get_volumes_to_extend(self):
        CONF.set_override('volumes_to_extend', '1')
        response = self._extend_volumes._get_volumes_to_extend()
        self.assertEqual(response, [1])

    @mock.patch('cloudbaseinit.utils.windows.vds.load_vds_service')
    @mock.patch('cloudbaseinit.plugins.windows.extendvolumes.'
                'ExtendVolumesPlugin._query_providers')
    @mock.patch('cloudbaseinit.plugins.windows.extendvolumes.'
                'ExtendVolumesPlugin._query_packs')
    @mock.patch('cloudbaseinit.plugins.windows.extendvolumes.'
                'ExtendVolumesPlugin._extend_volumes')
    def test_execute(self, mock_extend_volumes, mock_query_packs,
                     mock_query_providers, mock_load_vds_service):
        CONF.set_override('volumes_to_extend', '1')
        mock_svc = mock.MagicMock()
        fake_providers = ['fake providers']
        fake_packs = ['fake packs']
        mock_service = mock.MagicMock()
        fake_data = 'fake data'
        mock_load_vds_service.return_value = mock_svc
        mock_query_providers.return_value = fake_providers
        mock_query_packs.return_value = fake_packs

        self._extend_volumes.execute(mock_service, fake_data)

        mock_query_providers.assert_called_once_with(mock_svc)
        mock_query_packs.assert_called_once_with('fake providers')
        mock_extend_volumes.assert_called_with('fake packs', [1])

########NEW FILE########
__FILENAME__ = test_licensing
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import os
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import licensing

CONF = cfg.CONF


class WindowsLicensingPluginTests(unittest.TestCase):

    def setUp(self):
        self._licensing = licensing.WindowsLicensingPlugin()

    def _test_run_slmgr(self, sysnative, exit_code):
        mock_osutils = mock.MagicMock()
        get_system32_dir_calls = [mock.call()]
        cscript_path = os.path.join('cscrypt path', "cscript.exe")
        slmgr_path = os.path.join('slmgr path', "slmgr.vbs")

        mock_osutils.check_sysnative_dir_exists.return_value = sysnative
        mock_osutils.get_sysnative_dir.return_value = 'cscrypt path'
        if not sysnative:
            mock_osutils.get_system32_dir.side_effect = ['cscrypt path',
                                                         'slmgr path']
        else:
            mock_osutils.get_system32_dir.return_value = 'slmgr path'
        mock_osutils.execute_process.return_value = ('fake output', None,
                                                     exit_code)

        if exit_code:
            self.assertRaises(Exception, self._licensing._run_slmgr,
                              mock_osutils, ['fake args'])
        else:
            response = self._licensing._run_slmgr(osutils=mock_osutils,
                                                  args=['fake args'])
            self.assertEqual(response, 'fake output')

        mock_osutils.check_sysnative_dir_exists.assert_called_once_with()
        if sysnative:
            mock_osutils.get_sysnative_dir.assert_called_once_with()
        else:
            get_system32_dir_calls.append(mock.call())

        mock_osutils.execute_process.assert_called_once_with(
            [cscript_path, slmgr_path, 'fake args'], False)
        self.assertEqual(mock_osutils.get_system32_dir.call_args_list,
                         get_system32_dir_calls)

    def test_run_slmgr_sysnative(self):
        self._test_run_slmgr(sysnative=True, exit_code=None)

    def test_run_slmgr_not_sysnative(self):
        self._test_run_slmgr(sysnative=False, exit_code=None)

    def test_run_slmgr_exit_code(self):
        self._test_run_slmgr(sysnative=True, exit_code='fake exit code')

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('cloudbaseinit.plugins.windows.licensing'
                '.WindowsLicensingPlugin._run_slmgr')
    def _test_execute(self, mock_run_slmgr, mock_get_os_utils,
                      activate_windows):
        mock_osutils = mock.MagicMock()
        run_slmgr_calls = [mock.call(mock_osutils, ['/dlv'])]
        CONF.set_override('activate_windows', activate_windows)
        mock_get_os_utils.return_value = mock_osutils

        response = self._licensing.execute(service=None, shared_data=None)

        mock_get_os_utils.assert_called_once_with()
        if activate_windows:
            run_slmgr_calls.append(mock.call(mock_osutils, ['/ato']))

        self.assertEqual(mock_run_slmgr.call_args_list, run_slmgr_calls)
        self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_execute_activate_windows_true(self):
        self._test_execute(activate_windows=True)

    def test_execute_activate_windows_false(self):
        self._test_execute(activate_windows=False)

########NEW FILE########
__FILENAME__ = test_networkconfig
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import re
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import networkconfig
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class NetworkConfigPluginPluginTests(unittest.TestCase):

    def setUp(self):
        self._network_plugin = networkconfig.NetworkConfigPlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def _test_execute(self, mock_get_os_utils, search_result, no_adapters):
        CONF.set_override('network_adapter', 'fake adapter')
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        re.search = mock.MagicMock(return_value=search_result)
        fake_shared_data = 'fake shared data'
        network_config = self.fake_data['network_config']
        mock_service.get_network_config.return_value = network_config
        mock_service.get_content.return_value = search_result
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.set_static_network_config.return_value = False
        if search_result is None:
            self.assertRaises(Exception, self._network_plugin.execute,
                              mock_service, fake_shared_data)
        elif no_adapters:
            CONF.set_override('network_adapter', None)
            mock_osutils.get_network_adapters.return_value = None
            self.assertRaises(Exception, self._network_plugin.execute,
                              mock_service, fake_shared_data)

        else:
            response = self._network_plugin.execute(mock_service,
                                                    fake_shared_data)

            mock_service.get_network_config.assert_called_once_with()
            mock_service.get_content.assert_called_once_with(
                network_config['content_path'])
            mock_osutils.set_static_network_config.assert_called_once_with(
                'fake adapter', search_result.group('address'),
                search_result.group('netmask'),
                search_result.group('broadcast'),
                search_result.group('gateway'),
                search_result.group('dnsnameservers').strip().split(' '))
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_execute(self):
        m = mock.MagicMock()
        self._test_execute(search_result=m, no_adapters=False)

    def test_execute_no_debian(self):
        self._test_execute(search_result=None, no_adapters=False)

    def test_execute_no_adapters(self):
        m = mock.MagicMock()
        self._test_execute(search_result=m, no_adapters=True)

########NEW FILE########
__FILENAME__ = test_sethostname
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import sethostname
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class SetHostNamePluginPluginTests(unittest.TestCase):

    def setUp(self):
        self._sethostname_plugin = sethostname.SetHostNamePlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('platform.node')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def _test_execute(self, mock_get_os_utils, mock_node, hostname_exists=True,
                      hostname_already_set=False, new_hostname_length=1):
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        fake_shared_data = 'fake data'
        new_hostname = 'x' * new_hostname_length

        if hostname_exists:
            mock_service.get_host_name.return_value = new_hostname
        else:
            mock_service.get_host_name.return_value = None

        CONF.set_override('netbios_host_name_compatibility', True)
        mock_get_os_utils.return_value = mock_osutils

        if hostname_exists is True:
            length = sethostname.NETBIOS_HOST_NAME_MAX_LEN
            hostname = new_hostname.split('.', 1)[0]
            if len(new_hostname) > length:
                hostname = hostname[:length]

            if hostname_already_set:
                mock_node.return_value = hostname
            else:
                mock_node.return_value = 'fake_old_value'

        response = self._sethostname_plugin.execute(mock_service,
                                                    fake_shared_data)

        mock_service.get_host_name.assert_called_once_with()

        if hostname_exists is True:
            mock_get_os_utils.assert_called_once_with()
            if hostname_already_set:
                self.assertFalse(mock_osutils.set_host_name.called)
            else:
                mock_osutils.set_host_name.assert_called_once_with(hostname)

        self.assertEqual(
            response, (base.PLUGIN_EXECUTION_DONE,
                       hostname_exists and not hostname_already_set))

    def test_execute_hostname_already_set(self):
        self._test_execute(hostname_already_set=True)

    def test_execute_hostname_to_be_truncated(self):
        self._test_execute(
            new_hostname_length=sethostname.NETBIOS_HOST_NAME_MAX_LEN + 1)

    def test_execute_no_truncate_needed(self):
        self._test_execute(
            new_hostname_length=sethostname.NETBIOS_HOST_NAME_MAX_LEN)

    def test_execute_no_hostname(self):
        self._test_execute(hostname_exists=False)

########NEW FILE########
__FILENAME__ = test_setuserpassword
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import constants
from cloudbaseinit.plugins.windows import setuserpassword
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class SetUserPasswordPluginTests(unittest.TestCase):

    def setUp(self):
        self._setpassword_plugin = setuserpassword.SetUserPasswordPlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('base64.b64encode')
    @mock.patch('cloudbaseinit.utils.crypt.CryptManager'
                '.load_ssh_rsa_public_key')
    def test_encrypt_password(self, mock_load_ssh_key, mock_b64encode):
        mock_rsa = mock.MagicMock()
        fake_ssh_pub_key = 'fake key'
        fake_password = 'fake password'
        mock_load_ssh_key.return_value = mock_rsa
        mock_rsa.__enter__().public_encrypt.return_value = 'public encrypted'
        mock_b64encode.return_value = 'encrypted password'

        response = self._setpassword_plugin._encrypt_password(
            fake_ssh_pub_key, fake_password)
        print mock_rsa.mock_calls

        mock_load_ssh_key.assert_called_with(fake_ssh_pub_key)
        mock_rsa.__enter__().public_encrypt.assert_called_with('fake password')
        mock_b64encode.assert_called_with('public encrypted')
        self.assertEqual(response, 'encrypted password')

    def _test_get_ssh_public_key(self, data_exists):
        mock_service = mock.MagicMock()
        public_keys = self.fake_data['public_keys']
        mock_service.get_public_keys.return_value = public_keys
        response = self._setpassword_plugin._get_ssh_public_key(mock_service)
        mock_service.get_public_keys.assert_called_with()
        self.assertEqual(response, public_keys[0])

    def test_get_ssh_plublic_key(self):
        self._test_get_ssh_public_key(data_exists=True)

    def test_get_ssh_plublic_key_no_pub_keys(self):
        self._test_get_ssh_public_key(data_exists=False)

    def _test_get_password(self, inject_password):
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        mock_service.get_admin_password.return_value = 'Passw0rd'
        CONF.set_override('inject_user_password', inject_password)
        mock_osutils.generate_random_password.return_value = 'Passw0rd'
        response = self._setpassword_plugin._get_password(mock_service,
                                                          mock_osutils)
        if inject_password:
            mock_service.get_admin_password.assert_called_with()
        else:
            mock_osutils.generate_random_password.assert_called_once_with(14)
        self.assertEqual(response, 'Passw0rd')

    def test_get_password_inject_true(self):
        self._test_get_password(inject_password=True)

    def test_get_password_inject_false(self):
        self._test_get_password(inject_password=False)

    @mock.patch('cloudbaseinit.plugins.windows.setuserpassword.'
                'SetUserPasswordPlugin._get_ssh_public_key')
    @mock.patch('cloudbaseinit.plugins.windows.setuserpassword.'
                'SetUserPasswordPlugin._encrypt_password')
    def _test_set_metadata_password(self, mock_encrypt_password,
                                    mock_get_key, ssh_pub_key):
        fake_passw0rd = 'fake Passw0rd'
        mock_service = mock.MagicMock()
        mock_get_key.return_value = ssh_pub_key
        mock_encrypt_password.return_value = 'encrypted password'
        mock_service.post_password.return_value = 'value'
        response = self._setpassword_plugin._set_metadata_password(
            fake_passw0rd, mock_service)
        if ssh_pub_key is None:
            self.assertEqual(response, True)
        else:
            mock_get_key.assert_called_once_with(mock_service)
            mock_encrypt_password.assert_called_once_with(ssh_pub_key,
                                                          fake_passw0rd)
            mock_service.post_password.assert_called_with(
                'encrypted password')
            self.assertEqual(response, 'value')

    def test_set_metadata_password_with_ssh_key(self):
        fake_key = 'fake key'
        self._test_set_metadata_password(ssh_pub_key=fake_key)

    def test_set_metadata_password_no_ssh_key(self):
        self._test_set_metadata_password(ssh_pub_key=None)

    @mock.patch('cloudbaseinit.plugins.windows.setuserpassword.'
                'SetUserPasswordPlugin._get_password')
    def test_set_password(self, mock_get_password):
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        mock_get_password.return_value = 'fake password'
        response = self._setpassword_plugin._set_password(mock_service,
                                                          mock_osutils,
                                                          'fake user')
        mock_get_password.assert_called_once_with(mock_service, mock_osutils)
        mock_osutils.set_user_password.assert_called_once_with('fake user',
                                                               'fake password')
        self.assertEqual(response, 'fake password')

    @mock.patch('cloudbaseinit.plugins.windows.setuserpassword.'
                'SetUserPasswordPlugin._set_password')
    @mock.patch('cloudbaseinit.plugins.windows.setuserpassword.'
                'SetUserPasswordPlugin._set_metadata_password')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def test_execute(self, mock_get_os_utils, mock_set_metadata_password,
                     mock_set_password):
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        fake_shared_data = mock.MagicMock()
        fake_shared_data.get.return_value = 'fake username'
        mock_service.is_password_set = False
        mock_service.can_post_password = True
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.user_exists.return_value = True
        mock_set_password.return_value = 'fake password'
        response = self._setpassword_plugin.execute(mock_service,
                                                    fake_shared_data)
        print mock_service.mock_calls
        mock_get_os_utils.assert_called_once_with()
        fake_shared_data.get.assert_called_with(
            constants.SHARED_DATA_USERNAME, CONF.username)
        mock_osutils.user_exists.assert_called_once_with('fake username')
        mock_set_password.assert_called_once_with(mock_service, mock_osutils,
                                                  'fake username')
        mock_set_metadata_password.assert_called_once_with('fake password',
                                                           mock_service)
        self.assertEqual(response, (2, False))

########NEW FILE########
__FILENAME__ = test_sshpublickeys
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import os
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import sshpublickeys
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class SetUserSSHPublicKeysPluginTests(unittest.TestCase):

    def setUp(self):
        self._set_ssh_keys_plugin = sshpublickeys.SetUserSSHPublicKeysPlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('os.path')
    @mock.patch('os.makedirs')
    def _test_execute(self, mock_os_makedirs, mock_os_path,
                      mock_get_os_utils, user_home):
        mock_service = mock.MagicMock()
        mock_osutils = mock.MagicMock()
        fake_shared_data = 'fake data'
        mock_service.get_public_keys.return_value = self.fake_data
        CONF.set_override('username', 'fake user')
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.get_user_home.return_value = user_home
        mock_os_path.exists.return_value = False

        if user_home is None:
            self.assertRaises(Exception, self._set_ssh_keys_plugin,
                              mock_service, fake_shared_data)
        else:
            with mock.patch('cloudbaseinit.plugins.windows.sshpublickeys'
                            '.open',
                            mock.mock_open(), create=True):
                response = self._set_ssh_keys_plugin.execute(mock_service,
                                                             fake_shared_data)
                mock_service.get_public_keys.assert_called_with()
                mock_osutils.get_user_home.assert_called_with('fake user')
                self.assertEqual(mock_os_path.join.call_count, 2)
                mock_os_makedirs.assert_called_once_with(mock_os_path.join())

                self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE,
                                            False))

    def test_execute_with_user_home(self):
        fake_user_home = os.path.join('fake', 'home')
        self._test_execute(user_home=fake_user_home)

    def test_execute_with_no_user_home(self):
        self._test_execute(user_home=None)

########NEW FILE########
__FILENAME__ = test_userdata
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.metadata.services import base as metadata_services_base
from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import userdata
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class UserDataPluginTest(unittest.TestCase):

    def setUp(self):
        self._userdata = userdata.UserDataPlugin()
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._process_user_data')
    def _test_execute(self, mock_process_user_data, user_data_in,
                      user_data_out=None):
        mock_service = mock.MagicMock()
        mock_service.get_user_data.side_effect = [user_data_in]
        response = self._userdata.execute(service=mock_service,
                                          shared_data=None)
        mock_service.get_user_data.assert_called_once_with()
        if user_data_in is metadata_services_base.NotExistingMetadataException:
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))
        elif user_data_in is None:
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))
        else:
            if user_data_out:
                user_data = user_data_out
            else:
                user_data = user_data_in

            mock_process_user_data.assert_called_once_with(user_data)
            self.assertEqual(response, mock_process_user_data())

    def test_execute(self):
        self._test_execute(user_data_in='fake data')

    def test_execute_gzipped_user_data(self):
        fake_user_data_in = ('\x1f\x8b\x08\x00\x8c\xdc\x14S\x02\xffKK'
                             '\xccNUHI,I\x04\x00(\xc9\xcfI\t\x00\x00\x00')
        fake_user_data_out = 'fake data'

        self._test_execute(user_data_in=fake_user_data_in,
                           user_data_out=fake_user_data_out)

    def test_execute_NotExistingMetadataException(self):
        self._test_execute(
            user_data_in=metadata_services_base.NotExistingMetadataException)

    def test_execute_not_user_data(self):
        self._test_execute(user_data_in=None)

    @mock.patch('email.message_from_string')
    def test_parse_mime(self, mock_message_from_string):
        fake_user_data = 'fake data'
        response = self._userdata._parse_mime(user_data=fake_user_data)
        mock_message_from_string.assert_called_once_with(fake_user_data)
        self.assertEqual(response, mock_message_from_string().walk())

    @mock.patch('cloudbaseinit.plugins.windows.userdataplugins.factory.'
                'load_plugins')
    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._parse_mime')
    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._process_part')
    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._end_part_process_event')
    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._process_non_multi_part')
    def _test_process_user_data(self, mock_process_non_multi_part,
                                mock_end_part_process_event,
                                mock_process_part, mock_parse_mime,
                                mock_load_plugins, user_data, reboot):
        mock_part = mock.MagicMock()
        mock_parse_mime.return_value = [mock_part]
        mock_process_part.return_value = (base.PLUGIN_EXECUTION_DONE, reboot)

        response = self._userdata._process_user_data(user_data=user_data)
        if user_data.startswith('Content-Type: multipart'):
            mock_load_plugins.assert_called_once_with()
            mock_parse_mime.assert_called_once_with(user_data)
            mock_process_part.assert_called_once_with(mock_part,
                                                      mock_load_plugins(), {})
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, reboot))
        else:
            mock_process_non_multi_part.assert_called_once_with(user_data)
            self.assertEqual(response, mock_process_non_multi_part())

    def test_process_user_data_multipart_reboot_true(self):
        self._test_process_user_data(user_data='Content-Type: multipart',
                                     reboot=True)

    def test_process_user_data_multipart_reboot_false(self):
        self._test_process_user_data(user_data='Content-Type: multipart',
                                     reboot=False)

    def test_process_user_data_non_multipart(self):
        self._test_process_user_data(user_data='Content-Type: non-multipart',
                                     reboot=False)

    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._add_part_handlers')
    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._get_plugin_return_value')
    def _test_process_part(self, mock_get_plugin_return_value,
                           mock_add_part_handlers,
                           handler_func, user_data_plugin, content_type):
        mock_part = mock.MagicMock()
        mock_user_data_plugins = mock.MagicMock()
        mock_user_handlers = mock.MagicMock()
        mock_user_handlers.get.side_effect = [handler_func]
        mock_user_data_plugins.get.side_effect = [user_data_plugin]
        if content_type:
            _content_type = self._userdata._PART_HANDLER_CONTENT_TYPE
            mock_part.get_content_type.return_value = _content_type
        else:
            _content_type = 'other content type'
            mock_part.get_content_type.return_value = _content_type

        response = self._userdata._process_part(
            part=mock_part, user_data_plugins=mock_user_data_plugins,
            user_handlers=mock_user_handlers)
        mock_part.get_content_type.assert_called_once_with()
        mock_user_handlers.get.assert_called_once_with(
            _content_type)
        if handler_func and handler_func is Exception:
            self.assertEqual(mock_part.get_content_type.call_count, 2)
            self.assertEqual(mock_part.get_filename.call_count, 2)
        elif handler_func:
            handler_func.assert_called_once_with(None, _content_type,
                                                 mock_part.get_filename(),
                                                 mock_part.get_payload())

            self.assertEqual(mock_part.get_content_type.call_count, 1)
            self.assertEqual(mock_part.get_filename.call_count, 2)
        else:
            mock_user_data_plugins.get.assert_called_once_with(_content_type)
            if user_data_plugin and content_type:
                user_data_plugin.process.assert_called_with(mock_part)
                mock_add_part_handlers.assert_called_with(
                    mock_user_data_plugins, mock_user_handlers,
                    user_data_plugin.process())
            elif user_data_plugin and not content_type:
                mock_get_plugin_return_value.assert_called_once_with(
                    user_data_plugin.process())
                self.assertEqual(response, mock_get_plugin_return_value())

    def test_process_part(self):
        handler_func = mock.MagicMock()
        self._test_process_part(handler_func=handler_func,
                                user_data_plugin=None, content_type=False)

    def test_process_part_no_handler_func(self):
        user_data_plugin = mock.MagicMock()
        self._test_process_part(handler_func=None,
                                user_data_plugin=user_data_plugin,
                                content_type=True)

    def test_process_part_not_content_type(self):
        user_data_plugin = mock.MagicMock()
        self._test_process_part(handler_func=None,
                                user_data_plugin=user_data_plugin,
                                content_type=False)

    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._begin_part_process_event')
    def _test_add_part_handlers(self, mock_begin_part_process_event, ret_val):
        mock_user_data_plugins = mock.MagicMock(spec=dict)
        mock_new_user_handlers = mock.MagicMock(spec=dict)
        mock_user_handlers = mock.MagicMock(spec=dict)
        mock_handler_func = mock.MagicMock()

        mock_new_user_handlers.items.return_value = [('fake content type',
                                                     mock_handler_func)]
        if ret_val:
            mock_user_data_plugins.get.return_value = mock_handler_func
        else:
            mock_user_data_plugins.get.return_value = None

        self._userdata._add_part_handlers(
            user_data_plugins=mock_user_data_plugins,
            user_handlers=mock_user_handlers,
            new_user_handlers=mock_new_user_handlers)
        mock_user_data_plugins.get.assert_called_with('fake content type')
        if ret_val is None:
            mock_user_handlers.__setitem__.assert_called_once_with(
                'fake content type', mock_handler_func)
            mock_begin_part_process_event.assert_called_with(mock_handler_func)

    def test_add_part_handlers(self):
        self._test_add_part_handlers(ret_val=None)

    def test_add_part_handlers_skip_part_handler(self):
        mock_func = mock.MagicMock()
        self._test_add_part_handlers(ret_val=mock_func)

    def test_begin_part_process_event(self):
        mock_handler_func = mock.MagicMock()
        self._userdata._begin_part_process_event(
            handler_func=mock_handler_func)
        mock_handler_func.assert_called_once_with(None, "__begin__", None,
                                                  None)

    def test_end_part_process_event(self):
        mock_handler_func = mock.MagicMock()
        self._userdata._end_part_process_event(
            handler_func=mock_handler_func)
        mock_handler_func.assert_called_once_with(None, "__end__", None,
                                                  None)

    @mock.patch('cloudbaseinit.plugins.windows.userdatautils'
                '.execute_user_data_script')
    @mock.patch('cloudbaseinit.plugins.windows.userdata.UserDataPlugin'
                '._get_plugin_return_value')
    def test_process_non_multi_part(self, mock_get_plugin_return_value,
                                    mock_execute_user_data_script):
        user_data = 'fake'
        response = self._userdata._process_non_multi_part(user_data=user_data)
        mock_execute_user_data_script.assert_called_once_with(user_data)
        mock_get_plugin_return_value.assert_called_once_with(
            mock_execute_user_data_script())
        self.assertEqual(response, mock_get_plugin_return_value())

########NEW FILE########
__FILENAME__ = test_userdatautils
# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import os
import uuid
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows import userdatautils
from cloudbaseinit.tests.metadata import fake_json_response

CONF = cfg.CONF


class UserDataUtilsTest(unittest.TestCase):

    def setUp(self):
        self.fake_data = fake_json_response.get_fake_metadata_json(
            '2013-04-04')

    def tearDown(self):
        reload(uuid)

    @mock.patch('re.search')
    @mock.patch('tempfile.gettempdir')
    @mock.patch('os.remove')
    @mock.patch('os.path.exists')
    @mock.patch('os.path.expandvars')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def _test_execute_user_data_script(self, mock_get_os_utils,
                                       mock_path_expandvars,
                                       mock_path_exists, mock_os_remove,
                                       mock_gettempdir, mock_re_search,
                                       fake_user_data):
        mock_osutils = mock.MagicMock()
        mock_gettempdir.return_value = 'fake_temp'
        uuid.uuid4 = mock.MagicMock(return_value='randomID')
        match_instance = mock.MagicMock()
        path = os.path.join('fake_temp', 'randomID')
        args = None
        powershell = False
        mock_get_os_utils.return_value = mock_osutils
        mock_path_exists.return_value = True
        if fake_user_data == '^rem cmd\s':
            side_effect = [match_instance]
            number_of_calls = 1
            extension = '.cmd'
            args = [path + extension]
            shell = True
        elif fake_user_data == '^#!/usr/bin/env\spython\s':
            side_effect = [None, match_instance]
            number_of_calls = 2
            extension = '.py'
            args = ['python.exe', path + extension]
            shell = False
        elif fake_user_data == '#!':
            side_effect = [None, None, match_instance]
            number_of_calls = 3
            extension = '.sh'
            args = ['bash.exe', path + extension]
            shell = False
        elif fake_user_data == '#ps1_sysnative\s':
            side_effect = [None, None, None, match_instance]
            number_of_calls = 4
            extension = '.ps1'
            sysnative = True
            powershell = True
        elif fake_user_data == '#ps1_x86\s':
            side_effect = [None, None, None, None, match_instance]
            number_of_calls = 5
            extension = '.ps1'
            shell = False
            sysnative = False
            powershell = True
        else:
            side_effect = [None, None, None, None, None]
            number_of_calls = 5

        mock_re_search.side_effect = side_effect

        with mock.patch('cloudbaseinit.plugins.windows.userdatautils.open',
                        mock.mock_open(), create=True):
            response = userdatautils.execute_user_data_script(fake_user_data)
        mock_gettempdir.assert_called_once_with()
        self.assertEqual(mock_re_search.call_count, number_of_calls)
        if args:
            mock_osutils.execute_process.assert_called_with(args, shell)
            mock_os_remove.assert_called_once_with(path + extension)
            self.assertEqual(response, None)
        elif powershell:
            mock_osutils.execute_powershell_script.assert_called_with(
                path + extension, sysnative)
            mock_os_remove.assert_called_once_with(path + extension)
            self.assertEqual(response, None)
        else:
            self.assertEqual(response, 0)

    def test_handle_batch(self):
        fake_user_data = '^rem cmd\s'
        self._test_execute_user_data_script(fake_user_data=fake_user_data)

    def test_handle_python(self):
        self._test_execute_user_data_script(fake_user_data='^#!/usr/bin/env'
                                                           '\spython\s')

    def test_handle_shell(self):
        self._test_execute_user_data_script(fake_user_data='^#!')

    def test_handle_powershell(self):
        self._test_execute_user_data_script(fake_user_data='^#ps1\s')

    def test_handle_powershell_sysnative(self):
        self._test_execute_user_data_script(fake_user_data='#ps1_sysnative\s')

    def test_handle_powershell_sysnative_no_sysnative(self):
        self._test_execute_user_data_script(fake_user_data='#ps1_x86\s')

    def test_handle_unsupported_format(self):
        self._test_execute_user_data_script(fake_user_data='unsupported')

########NEW FILE########
__FILENAME__ = test_winrmcertificateauth
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import importlib
import mock
import sys
import unittest

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins import constants

from oslo.config import cfg

CONF = cfg.CONF
_ctypes_mock = mock.MagicMock()
_win32com_mock = mock.MagicMock()
_pywintypes_mock = mock.MagicMock()
mock_dict = {'ctypes': _ctypes_mock,
             'win32com': _win32com_mock,
             'pywintypes': _pywintypes_mock}


class ConfigWinRMCertificateAuthPluginTests(unittest.TestCase):
    @mock.patch.dict(sys.modules, mock_dict)
    def setUp(self):
        self.winrmcert = importlib.import_module(
            'cloudbaseinit.plugins.windows.winrmcertificateauth')
        self._certif_auth = self.winrmcert.ConfigWinRMCertificateAuthPlugin()

    def tearDown(self):
        reload(sys)

    def _test_get_credentials(self, fake_user, fake_password):
        mock_shared_data = mock.MagicMock()
        mock_shared_data.get.side_effect = [fake_user, fake_password]
        if fake_user is None or fake_password is None:
            self.assertRaises(Exception,
                              self._certif_auth._get_credentials,
                              mock_shared_data)
        else:
            response = self._certif_auth._get_credentials(mock_shared_data)
            expected = [mock.call(constants.SHARED_DATA_USERNAME),
                        mock.call(constants.SHARED_DATA_PASSWORD)]
            self.assertEqual(mock_shared_data.get.call_args_list, expected)
            mock_shared_data.__setitem__.assert_called_once_with(
                'admin_password', None)
            self.assertEqual(response, (fake_user, fake_password))

    def test_test_get_credentials(self):
        self._test_get_credentials(fake_user='fake user',
                                   fake_password='fake password')

    def test_test_get_credentials_no_user(self):
        self._test_get_credentials(fake_user=None,
                                   fake_password='fake password')

    def test_test_get_credentials_no_password(self):
        self._test_get_credentials(fake_user='fake user',
                                   fake_password=None)

    @mock.patch('cloudbaseinit.plugins.windows.winrmcertificateauth'
                '.ConfigWinRMCertificateAuthPlugin._get_credentials')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig')
    @mock.patch('cloudbaseinit.utils.windows.x509.CryptoAPICertManager.'
                'import_cert')
    def _test_execute(self, mock_import_cert, mock_WinRMConfig,
                      mock_get_credentials, cert_data, cert_upn):
        mock_service = mock.MagicMock()
        mock_cert_thumprint = mock.MagicMock()
        fake_credentials = ('fake user', 'fake password')
        mock_get_credentials.return_value = fake_credentials
        mock_import_cert.return_value = (mock_cert_thumprint, cert_upn)
        mock_WinRMConfig.get_cert_mapping.return_value = True
        mock_service.get_client_auth_certs.return_value = [cert_data]

        response = self._certif_auth.execute(mock_service,
                                             shared_data='fake data')
        mock_service.get_client_auth_certs.assert_called_once_with()
        if not cert_data:
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))
        else:
            mock_get_credentials.assert_called_once_with('fake data')
            mock_import_cert.assert_called_once_with(
                cert_data, store_name=self.winrmcert.x509.STORE_NAME_ROOT)

            mock_WinRMConfig().set_auth_config.assert_called_once_with(
                certificate=True)
            mock_WinRMConfig().get_cert_mapping.assert_called_once_with(
                mock_cert_thumprint, cert_upn)
            mock_WinRMConfig().delete_cert_mapping.assert_called_once_with(
                mock_cert_thumprint, cert_upn)
            mock_WinRMConfig().create_cert_mapping.assert_called_once_with(
                mock_cert_thumprint, cert_upn, 'fake user',
                'fake password')
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_execute(self):
        cert_data = 'fake cert data'
        cert_upn = mock.MagicMock()
        self._test_execute(cert_data=cert_data, cert_upn=cert_upn)

    def test_execute_no_cert_data(self):
        cert_upn = mock.MagicMock()
        self._test_execute(cert_data=None, cert_upn=cert_upn)

########NEW FILE########
__FILENAME__ = test_winrmlistener
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import importlib
import mock
import sys
import unittest

from cloudbaseinit.plugins import base
from oslo.config import cfg

CONF = cfg.CONF
_mock_wintypes = mock.MagicMock()
_mock_pywintypes = mock.MagicMock()
_mock_win32 = mock.MagicMock()
mock_dict = {'ctypes': _mock_wintypes,
             'ctypes.wintypes': _mock_wintypes,
             'pywintypes': _mock_pywintypes,
             'win32com': _mock_win32}


class ConfigWinRMListenerPluginTests(unittest.TestCase):
    @mock.patch.dict(sys.modules, mock_dict)
    def setUp(self):
        winrmlistener = importlib.import_module('cloudbaseinit.plugins.'
                                                'windows.winrmlistener')
        self._winrmlistener = winrmlistener.ConfigWinRMListenerPlugin()

    def _test_check_winrm_service(self, service_exists):
        mock_osutils = mock.MagicMock()
        mock_osutils.check_service_exists.return_value = service_exists
        mock_osutils.SERVICE_START_MODE_MANUAL = 'fake start'
        mock_osutils.SERVICE_START_MODE_DISABLED = 'fake start'
        mock_osutils.SERVICE_STATUS_STOPPED = 'fake status'
        mock_osutils.get_service_start_mode.return_value = 'fake start'
        mock_osutils.get_service_status.return_value = 'fake status'

        response = self._winrmlistener._check_winrm_service(mock_osutils)
        if not service_exists:
            self.assertEqual(response, False)
        else:

            mock_osutils.get_service_start_mode.assert_called_once_with(
                self._winrmlistener._winrm_service_name)
            mock_osutils.get_service_start_mode.assert_called_once_with(
                self._winrmlistener._winrm_service_name)
            mock_osutils.set_service_start_mode.assert_called_once_with(
                self._winrmlistener._winrm_service_name,
                mock_osutils .SERVICE_START_MODE_AUTOMATIC)
            mock_osutils.get_service_status.assert_called_once_with(
                self._winrmlistener._winrm_service_name)
            mock_osutils.start_service.assert_called_once_with(
                self._winrmlistener._winrm_service_name)
            self.assertEqual(response, True)

    def test_check_winrm_service(self):
        self._test_check_winrm_service(service_exists=True)

    def test_check_winrm_service_no_service(self):
        self._test_check_winrm_service(service_exists=False)

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('cloudbaseinit.plugins.windows.winrmlistener.'
                'ConfigWinRMListenerPlugin._check_winrm_service')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig')
    @mock.patch('cloudbaseinit.utils.windows.x509.CryptoAPICertManager'
                '.create_self_signed_cert')
    def _test_execute(self, mock_create_cert, mock_WinRMConfig,
                      mock_check_winrm_service, mock_get_os_utils,
                      service_status):
        mock_service = mock.MagicMock()
        mock_listener_config = mock.MagicMock()
        mock_cert_thumbprint = mock.MagicMock()
        shared_data = 'fake data'
        mock_osutils = mock.MagicMock()
        mock_get_os_utils.return_value = mock_osutils
        mock_check_winrm_service.return_value = service_status
        mock_create_cert.return_value = mock_cert_thumbprint
        mock_WinRMConfig().get_listener.return_value = mock_listener_config
        mock_listener_config.get.return_value = 9999

        response = self._winrmlistener.execute(mock_service, shared_data)

        mock_get_os_utils.assert_called_once_with()
        mock_check_winrm_service.assert_called_once_with(mock_osutils)

        if not service_status:
            self.assertEqual(response, (base.PLUGIN_EXECUTE_ON_NEXT_BOOT,
                                        service_status))
        else:
            mock_WinRMConfig().set_auth_config.assert_called_once_with(
                basic=CONF.winrm_enable_basic_auth)
            mock_create_cert.assert_called_once_with(
                self._winrmlistener._cert_subject)

            mock_WinRMConfig().get_listener.assert_called_with(
                protocol="HTTPS")
            mock_WinRMConfig().delete_listener.assert_called_once_with(
                protocol="HTTPS")
            mock_WinRMConfig().create_listener.assert_called_once_with(
                protocol="HTTPS", cert_thumbprint=mock_cert_thumbprint)
            mock_listener_config.get.assert_called_once_with("Port")
            mock_osutils.firewall_create_rule.assert_called_once_with(
                "WinRM HTTPS", 9999, mock_osutils.PROTOCOL_TCP)
            self.assertEqual(response, (base.PLUGIN_EXECUTION_DONE, False))

    def test_execute(self):
        self._test_execute(service_status=True)

    def test_execute_service_status_is_false(self):
        self._test_execute(service_status=False)

########NEW FILE########
__FILENAME__ = test_cloudboothook
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows.userdataplugins import cloudboothook

CONF = cfg.CONF


class CloudBootHookPluginTests(unittest.TestCase):

    def setUp(self):
        self._cloud_hook = cloudboothook.CloudBootHookPlugin()

    @mock.patch('cloudbaseinit.plugins.windows.userdataplugins.base'
                '.BaseUserDataPlugin.get_mime_type')
    def test_process(self, mock_get_mime_type):
        mock_part = mock.MagicMock()
        self._cloud_hook.process(mock_part)
        mock_get_mime_type.assert_called_once_with()

########NEW FILE########
__FILENAME__ = test_cloudconfig
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows.userdataplugins import cloudconfig

CONF = cfg.CONF


class CloudConfigPluginTests(unittest.TestCase):

    def setUp(self):
        self._cloudconfig = cloudconfig.CloudConfigPlugin()

    @mock.patch('cloudbaseinit.plugins.windows.userdataplugins.base'
                '.BaseUserDataPlugin.get_mime_type')
    def test_process(self, mock_get_mime_type):
        mock_part = mock.MagicMock()
        self._cloudconfig.process(mock_part)
        mock_get_mime_type.assert_called_once_with()

########NEW FILE########
__FILENAME__ = test_factory
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows.userdataplugins import factory

CONF = cfg.CONF


class UserDataPluginsFactoryTests(unittest.TestCase):

    @mock.patch('cloudbaseinit.utils.classloader.ClassLoader.load_class')
    def test_process(self, mock_load_class):
        response = factory.load_plugins()
        self.assertTrue(response is not None)

########NEW FILE########
__FILENAME__ = test_heat
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows.userdataplugins import heat

CONF = cfg.CONF


class HeatUserDataHandlerTests(unittest.TestCase):

    def setUp(self):
        self._heat = heat.HeatPlugin()

    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    def test_check_heat_config_dir(self, mock_makedirs, mock_exists):
        mock_exists.return_value = False
        self._heat._check_heat_config_dir()
        mock_exists.assert_called_once_with(CONF.heat_config_dir)
        mock_makedirs.assert_called_once_with(CONF.heat_config_dir)

    @mock.patch('cloudbaseinit.plugins.windows.userdatautils'
                '.execute_user_data_script')
    @mock.patch('cloudbaseinit.plugins.windows.userdataplugins.heat'
                '.HeatPlugin._check_heat_config_dir')
    def _test_process(self, mock_check_heat_config_dir,
                      mock_execute_user_data_script, filename):
        mock_part = mock.MagicMock()
        mock_part.get_filename.return_value = filename
        with mock.patch('__builtin__.open', mock.mock_open(),
                        create=True) as handle:
            response = self._heat.process(mock_part)
            handle().write.assert_called_once_with(mock_part.get_payload())
        mock_check_heat_config_dir.assert_called_once_with()
        mock_part.get_filename.assert_called_with()
        if filename == self._heat._heat_user_data_filename:
            mock_execute_user_data_script.assert_called_with(
                mock_part.get_payload())
            self.assertEqual(response, mock_execute_user_data_script())
        else:
            self.assertTrue(response is None)

    def test_process(self):
        self._test_process(filename=self._heat._heat_user_data_filename)

    def test_process_content_other_data(self):
        self._test_process(filename='other data')

########NEW FILE########
__FILENAME__ = test_parthandler
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import os
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows.userdataplugins import parthandler

CONF = cfg.CONF


class PartHandlerPluginTests(unittest.TestCase):

    def setUp(self):
        self._parthandler = parthandler.PartHandlerPlugin()

    @mock.patch('tempfile.gettempdir')
    @mock.patch('cloudbaseinit.utils.classloader.ClassLoader.load_module')
    def test_process(self, mock_load_module, mock_gettempdir):
        mock_part = mock.MagicMock()
        mock_part_handler = mock.MagicMock()
        mock_part.get_filename.return_value = 'fake_name'
        mock_gettempdir.return_value = 'fake_directory'
        mock_load_module.return_value = mock_part_handler
        mock_part_handler.list_types.return_value = ['fake part']

        with mock.patch('cloudbaseinit.plugins.windows.userdataplugins.'
                        'parthandler.open',
                        mock.mock_open(read_data='fake data'), create=True):
            response = self._parthandler.process(mock_part)

        mock_part.get_filename.assert_called_once_with()
        mock_load_module.assert_called_once_with(os.path.join(
            'fake_directory', 'fake_name'))
        mock_part_handler.list_types.assert_called_once_with()
        self.assertEqual(response, {'fake part':
                                    mock_part_handler.handle_part})

########NEW FILE########
__FILENAME__ = test_shellscript
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import os
import unittest

from oslo.config import cfg

from cloudbaseinit.plugins.windows.userdataplugins import shellscript

CONF = cfg.CONF


class ShellScriptPluginTests(unittest.TestCase):

    def setUp(self):
        self._shellscript = shellscript.ShellScriptPlugin()

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('tempfile.gettempdir')
    def _test_process(self, mock_gettempdir, mock_get_os_utils, filename,
                      exception=False):
        fake_dir_path = os.path.join("fake", "dir")
        mock_osutils = mock.MagicMock()
        mock_part = mock.MagicMock()
        mock_part.get_filename.return_value = filename
        mock_gettempdir.return_value = fake_dir_path
        mock_get_os_utils.return_value = mock_osutils
        fake_target = os.path.join(fake_dir_path, filename)
        if exception:
            mock_osutils.execute_process.side_effect = [Exception]
        with mock.patch("cloudbaseinit.plugins.windows.userdataplugins."
                        "shellscript.open", mock.mock_open(), create=True):
            response = self._shellscript.process(mock_part)
        mock_part.get_filename.assert_called_once_with()
        mock_gettempdir.assert_called_once_with()
        if filename.endswith(".cmd"):
            mock_osutils.execute_process.assert_called_once_with(
                [fake_target], True)
        elif filename.endswith(".sh"):
            mock_osutils.execute_process.assert_called_once_with(
                ['bash.exe', fake_target], False)
        elif filename.endswith(".py"):
            mock_osutils.execute_process.assert_called_once_with(
                ['python.exe', fake_target], False)
        elif filename.endswith(".ps1"):
            mock_osutils.execute_powershell_script.assert_called_once_with(
                fake_target)
        else:
            self.assertEqual(response, 0)

    def test_process_cmd(self):
        self._test_process(filename='fake.cmd')

    def test_process_sh(self):
        self._test_process(filename='fake.sh')

    def test_process_py(self):
        self._test_process(filename='fake.py')

    def test_process_ps1(self):
        self._test_process(filename='fake.ps1')

    def test_process_other(self):
        self._test_process(filename='fake.other')

    def test_process_exception(self):
        self._test_process(filename='fake.cmd', exception=True)

########NEW FILE########
__FILENAME__ = test_init
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import unittest
import sys

from oslo.config import cfg

from cloudbaseinit import init
from cloudbaseinit.plugins import base

CONF = cfg.CONF
_win32com_mock = mock.MagicMock()
_comtypes_mock = mock.MagicMock()
_pywintypes_mock = mock.MagicMock()
_ctypes_mock = mock.MagicMock()
_ctypes_util_mock = mock.MagicMock()
mock_dict = {'ctypes.util': _ctypes_util_mock,
             'win32com': _win32com_mock,
             'comtypes': _comtypes_mock,
             'pywintypes': _pywintypes_mock,
             'ctypes': _ctypes_mock}


class InitManagerTest(unittest.TestCase):
    @mock.patch.dict(sys.modules, mock_dict)
    def setUp(self):
        self.osutils = mock.MagicMock()
        self.plugin = mock.MagicMock()
        self._init = init.InitManager()

    def tearDown(self):
        reload(sys)
        reload(init)

    def _test_get_plugin_section(self, instance_id):
        response = self._init._get_plugins_section(instance_id=instance_id)
        if not instance_id:
            self.assertEqual(response, self._init._PLUGINS_CONFIG_SECTION)
        else:
            self.assertEqual(
                response,
                instance_id + "/" + self._init._PLUGINS_CONFIG_SECTION)

    @mock.patch('cloudbaseinit.init.InitManager._get_plugins_section')
    def test_get_plugin_status(self, mock_get_plugins_section):
        self.osutils.get_config_value.return_value = 1
        response = self._init._get_plugin_status(self.osutils, 'fake id',
                                                 'fake plugin')
        mock_get_plugins_section.assert_called_once_with('fake id')
        self.osutils.get_config_value.assert_called_once_with(
            'fake plugin', mock_get_plugins_section())
        self.assertTrue(response == 1)

    @mock.patch('cloudbaseinit.init.InitManager._get_plugins_section')
    def test_set_plugin_status(self, mock_get_plugins_section):
        self._init._set_plugin_status(self.osutils, 'fake id',
                                      'fake plugin', 'status')
        mock_get_plugins_section.assert_called_once_with('fake id')
        self.osutils.set_config_value.assert_called_once_with(
            'fake plugin', 'status', mock_get_plugins_section())

    @mock.patch('cloudbaseinit.init.InitManager._get_plugin_status')
    @mock.patch('cloudbaseinit.init.InitManager._set_plugin_status')
    def _test_exec_plugin(self, status, mock_set_plugin_status,
                          mock_get_plugin_status):
        fake_name = 'fake name'
        self.plugin.get_name.return_value = fake_name
        self.plugin.execute.return_value = (status, True)
        mock_get_plugin_status.return_value = status

        response = self._init._exec_plugin(osutils=self.osutils,
                                           service='fake service',
                                           plugin=self.plugin,
                                           instance_id='fake id',
                                           shared_data='shared data')

        mock_get_plugin_status.assert_called_once_with(self.osutils,
                                                       'fake id',
                                                       fake_name)
        if status is base.PLUGIN_EXECUTE_ON_NEXT_BOOT:
            self.plugin.execute.assert_called_once_with('fake service',
                                                        'shared data')
            mock_set_plugin_status.assert_called_once_with(self.osutils,
                                                           'fake id',
                                                           fake_name, status)
            self.assertTrue(response)

    def test_test_exec_plugin_execution_done(self):
        self._test_exec_plugin(base.PLUGIN_EXECUTION_DONE)

    def test_test_exec_plugin(self):
        self._test_exec_plugin(base.PLUGIN_EXECUTE_ON_NEXT_BOOT)

    def _test_check_plugin_os_requirements(self, requirements):
        sys.platform = 'win32'
        fake_name = 'fake name'
        self.plugin.get_name.return_value = fake_name
        self.plugin.get_os_requirements.return_value = requirements

        response = self._init._check_plugin_os_requirements(self.osutils,
                                                            self.plugin)

        self.plugin.get_name.assert_called_once_with()
        self.plugin.get_os_requirements.assert_called_once_with()
        if requirements[0] == 'win32':
            self.assertTrue(response)
        else:
            self.assertFalse(response)

    def test_check_plugin_os_requirements(self):
        self._test_check_plugin_os_requirements(('win32', (5, 2)))

    def test_check_plugin_os_requirements_other_requirenments(self):
        self._test_check_plugin_os_requirements(('linux', (5, 2)))

    @mock.patch('cloudbaseinit.init.InitManager'
                '._check_plugin_os_requirements')
    @mock.patch('cloudbaseinit.init.InitManager._exec_plugin')
    @mock.patch('cloudbaseinit.plugins.factory.load_plugins')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('cloudbaseinit.metadata.factory.get_metadata_service')
    def test_configure_host(self, mock_get_metadata_service,
                            mock_get_os_utils, mock_load_plugins,
                            mock_exec_plugin,
                            mock_check_os_requirements):
        fake_service = mock.MagicMock()
        fake_plugin = mock.MagicMock()
        mock_load_plugins.return_value = [fake_plugin]
        mock_get_os_utils.return_value = self.osutils
        mock_get_metadata_service.return_value = fake_service
        fake_service.get_name.return_value = 'fake name'
        fake_service.get_instance_id.return_value = 'fake id'

        self._init.configure_host()

        self.osutils.wait_for_boot_completion.assert_called_once()
        mock_get_metadata_service.assert_called_once_with()
        fake_service.get_name.assert_called_once_with()
        mock_check_os_requirements.assert_called_once_with(self.osutils,
                                                           fake_plugin)
        mock_exec_plugin.assert_called_once_with(self.osutils, fake_service,
                                                 fake_plugin, 'fake id', {})
        fake_service.cleanup.assert_called_once_with()
        self.osutils.reboot.assert_called_once_with()

########NEW FILE########
__FILENAME__ = test_log
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Cloudbase Solutions Srl
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

import mock
import unittest

from oslo.config import cfg

from cloudbaseinit.utils import log

CONF = cfg.CONF


class SerialPortHandlerTests(unittest.TestCase):
    @mock.patch('serial.Serial')
    def setUp(self, mock_Serial):
        CONF.set_override('logging_serial_port_settings', "COM1,115200,N,8")
        self._serial_port_handler = log.SerialPortHandler()
        self._serial_port_handler._port = mock.MagicMock()

    @mock.patch('serial.Serial')
    def test_init(self, mock_Serial):
        mock_Serial().isOpen.return_value = False
        log.SerialPortHandler()
        print mock_Serial.mock_calls
        mock_Serial.assert_called_with(bytesize=8, baudrate=115200,
                                       port='COM1', parity='N')
        mock_Serial().isOpen.assert_called_once_with()
        mock_Serial().open.assert_called_once_with()

    def test_close(self):
        self._serial_port_handler._port.isOpen.return_value = True
        self._serial_port_handler.close()
        self._serial_port_handler._port.isOpen.assert_called_once_with()
        self._serial_port_handler._port.close.assert_called_once_with()


@mock.patch('cloudbaseinit.openstack.common.log.setup')
@mock.patch('cloudbaseinit.openstack.common.log.getLogger')
@mock.patch('cloudbaseinit.utils.log.SerialPortHandler')
@mock.patch('cloudbaseinit.openstack.common.log.ContextFormatter')
def test_setup(mock_ContextFormatter, mock_SerialPortHandler, mock_getLogger,
               mock_setup):
    log.setup(product_name='fake name')
    mock_setup.assert_called_once_with('fake name')
    mock_getLogger.assert_called_once_with('fake name')
    mock_getLogger().logger.addHandler.assert_called_once_with(
        mock_SerialPortHandler())
    mock_ContextFormatter.assert_called_once_with(
        project='fake name', datefmt=CONF.log_date_format)
    mock_SerialPortHandler().setFormatter.assert_called_once_with(
        mock_ContextFormatter())

########NEW FILE########
__FILENAME__ = test_network
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import sys
import unittest

from oslo.config import cfg

from cloudbaseinit.utils import network

CONF = cfg.CONF


class NetworkUtilsTest(unittest.TestCase):
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    @mock.patch('urlparse.urlparse')
    def _test_check_metadata_ip_route(self, mock_urlparse, mock_get_os_utils,
                                      side_effect):
        mock_utils = mock.MagicMock()
        mock_split = mock.MagicMock()
        sys.platform = 'win32'
        mock_get_os_utils.return_value = mock_utils
        mock_utils.check_os_version.return_value = True
        mock_urlparse().netloc.split.return_value = mock_split
        mock_split[0].startswith.return_value = True
        mock_utils.check_static_route_exists.return_value = False
        mock_utils.get_default_gateway.return_value = (1, '0.0.0.0')
        mock_utils.add_static_route.side_effect = [side_effect]
        network.check_metadata_ip_route('196.254.196.254')
        mock_utils.check_os_version.assert_called_once_with(6, 0)
        mock_urlparse.assert_called_with('196.254.196.254')
        mock_split[0].startswith.assert_called_once_with("169.254.")
        mock_utils.check_static_route_exists.assert_called_once_with(
            mock_split[0])
        mock_utils.get_default_gateway.assert_called_once_with()
        mock_utils.add_static_route.assert_called_once_with(
            mock_split[0], "255.255.255.255", '0.0.0.0', 1, 10)

    def test_test_check_metadata_ip_route(self):
        self._test_check_metadata_ip_route(side_effect=None)

    def test_test_check_metadata_ip_route_fail(self):
        self._test_check_metadata_ip_route(side_effect=Exception)

########NEW FILE########
__FILENAME__ = test_winrmconfig
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import sys
import unittest

from oslo.config import cfg

if sys.platform == 'win32':
    from cloudbaseinit.utils.windows import winrmconfig

CONF = cfg.CONF


@unittest.skipUnless(sys.platform == "win32", "requires Windows")
class WinRMConfigTests(unittest.TestCase):

    def setUp(self):
        self._winrmconfig = winrmconfig.WinRMConfig()

    @mock.patch('win32com.client.Dispatch')
    def test_get_wsman_session(self, mock_Dispatch):
        mock_wsman = mock.MagicMock()
        mock_Dispatch.return_value = mock_wsman
        response = self._winrmconfig._get_wsman_session()
        mock_Dispatch.assert_called_once_with('WSMan.Automation')
        mock_wsman.CreateSession.assert_called_once_with()
        self.assertEqual(response, mock_wsman.CreateSession())

    @mock.patch('re.match')
    def test_get_node_tag(self, mock_match):
        mock_tag = mock.MagicMock()
        response = self._winrmconfig._get_node_tag(mock_tag)
        mock_match.assert_called_once_with("^{.*}(.*)$", mock_tag)
        self.assertEqual(response, mock_match().groups().__getitem__())

    @mock.patch('xml.etree.ElementTree.fromstring')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_node_tag')
    def _test_parse_listener_xml(self, mock_get_node_tag, mock_fromstring,
                                 data_xml, tag=None, text='Fake'):
        mock_node = mock.MagicMock()
        mock_node.tag = tag
        mock_node.text = text
        fake_tree = [mock_node]
        mock_get_node_tag.return_value = tag
        mock_fromstring.return_value = fake_tree
        response = self._winrmconfig._parse_listener_xml(data_xml=data_xml)
        if data_xml is None:
            self.assertEqual(response, None)
        else:
            mock_fromstring.assert_called_once_with(data_xml)
            mock_get_node_tag.assert_called_once_with(tag)
            if tag is "ListeningOn":
                self.assertEqual(response, {'ListeningOn': ['Fake']})
            elif tag is "Enabled":
                if text is 'true':
                    self.assertEqual(response, {'ListeningOn': [],
                                                'Enabled': True})
                else:
                    self.assertEqual(response, {'ListeningOn': [],
                                                'Enabled': False})
            elif tag is 'Port':
                self.assertEqual(response, {'ListeningOn': [],
                                            'Port': int(text)})
            else:
                self.assertEqual(response, {'ListeningOn': [],
                                            tag: text})

    def test_parse_listener_xml_no_data(self):
        self._test_parse_listener_xml(data_xml=None)

    def test_parse_listener_xml_listening_on(self):
        self._test_parse_listener_xml(data_xml='fake data', tag="ListeningOn")

    def test_parse_listener_xml_enabled_true(self):
        self._test_parse_listener_xml(data_xml='fake data',
                                      tag="Enabled", text='true')

    def test_parse_listener_xml_enabled_false(self):
        self._test_parse_listener_xml(data_xml='fake data', tag='Enabled',
                                      text='false')

    def test_parse_listener_xml_port(self):
        self._test_parse_listener_xml(data_xml='fake data', tag='Port',
                                      text='9999')

    def test_parse_listener_xml_other_tag(self):
        self._test_parse_listener_xml(data_xml='fake data', tag='fake tag',
                                      text='fake text')

    @mock.patch('xml.etree.ElementTree.fromstring')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig'
                '._get_node_tag')
    def _test_parse_cert_mapping_xml(self, mock_get_node_tag,
                                     mock_fromstring, data_xml, tag=None,
                                     text='Fake'):
        mock_node = mock.MagicMock()
        mock_node.tag = tag
        mock_node.text = text
        fake_tree = [mock_node]
        mock_get_node_tag.return_value = tag
        mock_fromstring.return_value = fake_tree
        response = self._winrmconfig._parse_cert_mapping_xml(data_xml=data_xml)
        if data_xml is None:
            self.assertEqual(response, None)
        else:
            mock_fromstring.assert_called_once_with(data_xml)
            mock_get_node_tag.assert_called_once_with(tag)
            if tag is "Enabled":
                if text is 'true':
                    self.assertEqual(response, {'Enabled': True})
                else:
                    self.assertEqual(response, {'Enabled': False})
            else:
                self.assertEqual(response, {tag: text})

    def test_parse_cert_mapping_xml_no_data(self):
        self._test_parse_cert_mapping_xml(data_xml=None)

    def test_parse_cert_mapping_xml_enabled_true(self):
        self._test_parse_listener_xml(data_xml='fake data',
                                      tag="Enabled", text='true')

    def test_parse_cert_mapping_xml_enabled_false(self):
        self._test_parse_listener_xml(data_xml='fake data', tag='Enabled',
                                      text='false')

    def test_parse_cert_mapping_xml_other_tag(self):
        self._test_parse_listener_xml(data_xml='fake data', tag='fake tag',
                                      text='fake text')

    def _test_get_xml_bool(self, value):
        response = self._winrmconfig._get_xml_bool(value)
        if value:
            self.assertEqual(response, 'true')
        else:
            self.assertEqual(response, 'false')

    def test_get_xml_bool_true(self):
        self._test_get_xml_bool(value='fake value')

    def test_get_xml_bool_false(self):
        self._test_get_xml_bool(value=None)

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_wsman_session')
    def _test_get_resource(self, mock_get_wsman_session, resource):
        fake_session = mock.MagicMock()
        fake_uri = 'fake:\\uri'
        fake_session.Get.side_effect = [resource]
        mock_get_wsman_session.return_value = fake_session
        if resource is Exception:
            self.assertRaises(Exception, self._winrmconfig._get_resource,
                              fake_uri)
        else:
            response = self._winrmconfig._get_resource(fake_uri)
            mock_get_wsman_session.assert_called_once_with()
            fake_session.Get.assert_called_once_with(fake_uri)
            self.assertEqual(response, resource)

    def test_get_resource(self):
        self._test_get_resource(resource='fake resource')

    def test_get_resource_exception(self):
        self._test_get_resource(resource=Exception)

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_wsman_session')
    def test_delete_resource(self, mock_get_wsman_session):
        fake_session = mock.MagicMock()
        fake_uri = 'fake:\\uri'
        mock_get_wsman_session.return_value = fake_session
        self._winrmconfig._delete_resource(fake_uri)
        fake_session.Delete.assert_called_once_with(fake_uri)

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_wsman_session')
    def test_create_resource(self, mock_get_wsman_session):
        fake_session = mock.MagicMock()
        fake_uri = 'fake:\\uri'
        mock_get_wsman_session.return_value = fake_session
        self._winrmconfig._create_resource(fake_uri, 'fake data')
        fake_session.Create.assert_called_once_with(fake_uri, 'fake data')

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_parse_cert_mapping_xml')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_resource')
    def test_get_cert_mapping(self, mock_get_resource,
                              mock_parse_cert_mapping_xml):
        fake_dict = {'issuer': 'issuer',
                     'subject': 'subject',
                     'uri': 'fake:\\uri'}
        mock_parse_cert_mapping_xml.return_value = 'fake response'
        mock_get_resource.return_value = 'fake resource'
        response = self._winrmconfig.get_cert_mapping('issuer', 'subject',
                                                      uri='fake:\\uri')
        mock_parse_cert_mapping_xml.assert_called_with('fake resource')
        mock_get_resource.assert_called_with(
            self._winrmconfig._SERVICE_CERTMAPPING_URI % fake_dict)
        self.assertEqual(response, 'fake response')

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_delete_resource')
    def test_delete_cert_mapping(self, mock_delete_resource):
        fake_dict = {'issuer': 'issuer',
                     'subject': 'subject',
                     'uri': 'fake:\\uri'}
        self._winrmconfig.delete_cert_mapping('issuer', 'subject',
                                              uri='fake:\\uri')
        mock_delete_resource.assert_called_with(
            self._winrmconfig._SERVICE_CERTMAPPING_URI % fake_dict)

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_xml_bool')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_create_resource')
    def test_create_cert_mapping(self, mock_create_resource,
                                 mock_get_xml_bool):
        fake_dict = {'issuer': 'issuer',
                     'subject': 'subject',
                     'uri': 'fake:\\uri'}
        mock_get_xml_bool.return_value = True
        self._winrmconfig.create_cert_mapping(
            issuer='issuer', subject='subject', username='fake user',
            password='fake password', uri='fake:\\uri', enabled=True)
        mock_get_xml_bool.assert_called_once_with(True)
        mock_create_resource.assert_called_once_with(
            self._winrmconfig._SERVICE_CERTMAPPING_URI % fake_dict,
            '<p:certmapping xmlns:p="http://schemas.microsoft.com/wbem/wsman/'
            '1/config/service/certmapping.xsd">'
            '<p:Enabled>%(enabled)s</p:Enabled>'
            '<p:Password>%(password)s</p:Password>'
            '<p:UserName>%(username)s</p:UserName>'
            '</p:certmapping>' % {'enabled': True,
                                  'username': 'fake user',
                                  'password': 'fake password'})

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_resource')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_parse_listener_xml')
    def test_get_listener(self, mock_parse_listener_xml, mock_get_resource):
        dict = {'protocol': 'HTTPS',
                'address': 'fake:\\address'}
        mock_get_resource.return_value = 'fake resource'
        mock_parse_listener_xml.return_value = 'fake response'
        response = self._winrmconfig.get_listener(protocol='HTTPS',
                                                  address="fake:\\address")
        mock_get_resource.assert_called_with(
            self._winrmconfig._SERVICE_LISTENER_URI % dict)
        mock_parse_listener_xml.assert_called_once_with('fake resource')
        self.assertEqual(response, 'fake response')

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_delete_resource')
    def test_delete_listener(self, mock_delete_resource):
        dict = {'protocol': 'HTTPS',
                'address': 'fake:\\address'}
        self._winrmconfig.delete_listener(protocol='HTTPS',
                                          address="fake:\\address")
        mock_delete_resource.assert_called_with(
            self._winrmconfig._SERVICE_LISTENER_URI % dict)

    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_create_resource')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_xml_bool')
    def test_create_listener(self, mock_get_xml_bool, mock_create_resource):
        dict = {'protocol': 'HTTPS',
                'address': 'fake:\\address'}
        mock_get_xml_bool.return_value = True
        self._winrmconfig.create_listener(protocol='HTTPS',
                                          cert_thumbprint=None,
                                          address="fake:\\address",
                                          enabled=True)
        mock_create_resource.assert_called_once_with(
            self._winrmconfig._SERVICE_LISTENER_URI % dict,
            '<p:Listener xmlns:p="http://schemas.microsoft.com/'
            'wbem/wsman/1/config/listener.xsd">'
            '<p:Enabled>%(enabled)s</p:Enabled>'
            '<p:CertificateThumbPrint>%(cert_thumbprint)s'
            '</p:CertificateThumbPrint>'
            '<p:URLPrefix>wsman</p:URLPrefix>'
            '</p:Listener>' % {"enabled": True,
                               "cert_thumbprint": None})

    @mock.patch('xml.etree.ElementTree.fromstring')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_node_tag')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_resource')
    def test_get_auth_config(self, mock_get_resource, mock_get_node_tag,
                             mock_fromstring):
        mock_node = mock.MagicMock()
        mock_node.tag = 'tag'
        mock_node.text = 'value'
        fake_tree = [mock_node]
        mock_get_resource.return_value = 'fake data xml'
        mock_fromstring.return_value = fake_tree
        mock_get_node_tag.return_value = 'tag'

        response = self._winrmconfig.get_auth_config()

        mock_get_resource.assert_called_with(
            self._winrmconfig._SERVICE_AUTH_URI)
        mock_fromstring.assert_called_once_with('fake data xml')
        mock_get_node_tag.assert_called_once_with(mock_node.tag)
        self.assertEqual(response, {'tag': 'value'})

    @mock.patch('xml.etree.ElementTree.fromstring')
    @mock.patch('xml.etree.ElementTree.tostring')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_wsman_session')
    @mock.patch('cloudbaseinit.utils.windows.winrmconfig.WinRMConfig.'
                '_get_xml_bool')
    def test_set_auth_config(self, mock_get_xml_bool, mock_get_wsman_session,
                             mock_tostring, mock_fromstring):
        mock_session = mock.MagicMock()
        mock_tree = mock.MagicMock()
        mock_node = mock.MagicMock()
        base_url = 'http://schemas.microsoft.com/wbem/wsman/1/config/service/'
        expected_find = [
            mock.call('.//cfg:Certificate', namespaces={
                'cfg': base_url + 'auth'}),
            mock.call('.//cfg:Kerberos',
                      namespaces={'cfg': base_url + 'auth'}),
            mock.call('.//cfg:CbtHardeningLevel',
                      namespaces={'cfg': base_url + 'auth'}),
            mock.call('.//cfg:Negotiate',
                      namespaces={'cfg': base_url + 'auth'}),
            mock.call('.//cfg:CredSSP',
                      namespaces={'cfg': base_url + 'auth'}),
            mock.call('.//cfg:Basic',
                      namespaces={'cfg': base_url + 'auth'})]
        expected_get_xml_bool = [mock.call('certificate'),
                                 mock.call('kerberos'),
                                 mock.call('cbt_hardening_level'),
                                 mock.call('negotiate'),
                                 mock.call('credSSP'),
                                 mock.call('basic')]

        mock_get_wsman_session.return_value = mock_session
        mock_session.Get.return_value = 'fake xml'
        mock_fromstring.return_value = mock_tree
        mock_get_xml_bool.return_value = 'true'
        mock_tostring.return_value = 'fake xml'
        mock_tree.find.return_value = mock_node
        mock_node.text.lower.return_value = 'old value'

        self._winrmconfig.set_auth_config(
            basic='basic', kerberos='kerberos', negotiate='negotiate',
            certificate='certificate', credSSP='credSSP',
            cbt_hardening_level='cbt_hardening_level')
        self.assertEqual(mock_tree.find.call_args_list, expected_find)
        self.assertEqual(mock_get_xml_bool.call_args_list,
                         expected_get_xml_bool)

        mock_get_wsman_session.assert_called_once_with()
        mock_session.Get.assert_called_with(
            self._winrmconfig._SERVICE_AUTH_URI)
        mock_fromstring.assert_called_once_with('fake xml')
        mock_session.Put.assert_called_with(
            self._winrmconfig._SERVICE_AUTH_URI, 'fake xml')

########NEW FILE########
__FILENAME__ = test_x509
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import mock
import sys
import unittest

from oslo.config import cfg

from cloudbaseinit.utils import x509constants
if sys.platform == 'win32':
    from cloudbaseinit.utils.windows import cryptoapi
    from cloudbaseinit.utils.windows import x509

CONF = cfg.CONF


@unittest.skipUnless(sys.platform == "win32", "requires Windows")
class CryptoAPICertManagerTests(unittest.TestCase):

    def setUp(self):
        self._x509 = x509.CryptoAPICertManager()

    @mock.patch('cloudbaseinit.utils.windows.x509.free')
    @mock.patch('ctypes.c_ubyte')
    @mock.patch('ctypes.POINTER')
    @mock.patch('ctypes.cast')
    @mock.patch('cloudbaseinit.utils.windows.x509.malloc')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.wintypes.DWORD')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertGetCertificateContextProperty')
    def _test_get_cert_thumprint(self, mock_CertGetCertificateContextProperty,
                                 mock_DWORD, mock_byref, mock_malloc,
                                 mock_cast, mock_POINTER, mock_c_ubyte,
                                 mock_free, ret_val):

        mock_pointer = mock.MagicMock()
        fake_cert_context_p = 'fake context'
        mock_DWORD().value = 10
        mock_CertGetCertificateContextProperty.return_value = ret_val
        mock_POINTER.return_value = mock_pointer
        mock_cast().contents = [16]
        if not ret_val:
            self.assertRaises(cryptoapi.CryptoAPIException,
                              self._x509._get_cert_thumprint,
                              fake_cert_context_p)
        else:
            expected = [mock.call(fake_cert_context_p,
                                  cryptoapi.CERT_SHA1_HASH_PROP_ID,
                                  None, mock_byref()),
                        mock.call(fake_cert_context_p,
                                  cryptoapi.CERT_SHA1_HASH_PROP_ID,
                                  mock_malloc(), mock_byref())]
            response = self._x509._get_cert_thumprint(fake_cert_context_p)
            self.assertEqual(
                mock_CertGetCertificateContextProperty.call_args_list,
                expected)
            mock_malloc.assert_called_with(mock_DWORD())
            mock_cast.assert_called_with(mock_malloc(), mock_pointer)
            mock_free.assert_called_with(mock_malloc())
            self.assertEqual(response, '10')

    def test_get_cert_thumprint(self):
        self._test_get_cert_thumprint(ret_val=True)

    def test_get_cert_thumprint_GetCertificateContextProperty_exception(self):
        self._test_get_cert_thumprint(ret_val=False)

    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.CryptDestroyKey')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.CryptReleaseContext')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.CryptGenKey')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.CryptAcquireContext')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.wintypes.HANDLE')
    def _test_generate_key(self, mock_HANDLE, mock_byref,
                           mock_CryptAcquireContext, mock_CryptGenKey,
                           mock_CryptReleaseContext, mock_CryptDestroyKey,
                           acquired_context, generate_key_ret_val):
        mock_CryptAcquireContext.return_value = acquired_context
        mock_CryptGenKey.return_value = generate_key_ret_val
        if not acquired_context:
            self.assertRaises(cryptoapi.CryptoAPIException,
                              self._x509._generate_key,
                              'fake container', True)
        else:
            if generate_key_ret_val is None:
                self.assertRaises(cryptoapi.CryptoAPIException,
                                  self._x509._generate_key, 'fake container',
                                  True)
                mock_byref.assert_called_with(mock_HANDLE())
            else:
                self._x509._generate_key('fake container', True)
                mock_CryptAcquireContext.assert_called_with(
                    mock_byref(), 'fake container', None,
                    cryptoapi.PROV_RSA_FULL, cryptoapi.CRYPT_MACHINE_KEYSET)
                mock_CryptGenKey.assert_called_with(mock_HANDLE(),
                                                    cryptoapi.AT_SIGNATURE,
                                                    0x08000000, mock_HANDLE())
                mock_CryptDestroyKey.assert_called_once_with(
                    mock_HANDLE())
                mock_CryptReleaseContext.assert_called_once_with(
                    mock_HANDLE(), 0)

    def test_generate_key(self):
        self._test_generate_key(acquired_context=True,
                                generate_key_ret_val='fake key')

    def test_generate_key_GetCertificateContextProperty_exception(self):
        self._test_generate_key(acquired_context=False,
                                generate_key_ret_val='fake key')

    def test_generate_key_CryptGenKey_exception(self):
        self._test_generate_key(acquired_context=True,
                                generate_key_ret_val=None)

    @mock.patch('cloudbaseinit.utils.windows.x509.free')
    @mock.patch('copy.copy')
    @mock.patch('ctypes.byref')
    @mock.patch('cloudbaseinit.utils.windows.x509.malloc')
    @mock.patch('ctypes.POINTER')
    @mock.patch('ctypes.cast')
    @mock.patch('cloudbaseinit.utils.windows.x509.CryptoAPICertManager'
                '._generate_key')
    @mock.patch('cloudbaseinit.utils.windows.x509.CryptoAPICertManager'
                '._get_cert_thumprint')
    @mock.patch('uuid.uuid4')
    @mock.patch('ctypes.wintypes.DWORD')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertStrToName')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CRYPTOAPI_BLOB')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CRYPT_KEY_PROV_INFO')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CRYPT_ALGORITHM_IDENTIFIER')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'SYSTEMTIME')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'GetSystemTime')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertCreateSelfSignCertificate')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertAddEnhancedKeyUsageIdentifier')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertOpenStore')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertAddCertificateContextToStore')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertCloseStore')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertFreeCertificateContext')
    def _test_create_self_signed_cert(self, mock_CertFreeCertificateContext,
                                      mock_CertCloseStore,
                                      mock_CertAddCertificateContextToStore,
                                      mock_CertOpenStore,
                                      mock_CertAddEnhancedKeyUsageIdentifier,
                                      mock_CertCreateSelfSignCertificate,
                                      mock_GetSystemTime, mock_SYSTEMTIME,
                                      mock_CRYPT_ALGORITHM_IDENTIFIER,
                                      mock_CRYPT_KEY_PROV_INFO,
                                      mock_CRYPTOAPI_BLOB,
                                      mock_CertStrToName, mock_DWORD,
                                      mock_uuid4, mock_get_cert_thumprint,
                                      mock_generate_key, mock_cast,
                                      mock_POINTER, mock_malloc, mock_byref,
                                      mock_copy, mock_free, certstr,
                                      certificate, enhanced_key,
                                      store_handle, context_to_store):

        mock_uuid4.return_value = 'fake_name'
        mock_CertCreateSelfSignCertificate.return_value = certificate
        mock_CertAddEnhancedKeyUsageIdentifier.return_value = enhanced_key
        mock_CertStrToName.return_value = certstr
        mock_CertOpenStore.return_value = store_handle
        mock_CertAddCertificateContextToStore.return_value = context_to_store
        if (certstr is None or certificate is None or enhanced_key is None
                or store_handle is None or context_to_store is None):
            self.assertRaises(cryptoapi.CryptoAPIException,
                              self._x509.create_self_signed_cert,
                              'fake subject', 10, True, x509.STORE_NAME_MY)
        else:
            response = self._x509.create_self_signed_cert(
                subject='fake subject')
            mock_cast.assert_called_with(mock_malloc(), mock_POINTER())
            mock_CRYPTOAPI_BLOB.assert_called_once_with()
            mock_CRYPT_KEY_PROV_INFO.assert_called_once_with()
            mock_CRYPT_ALGORITHM_IDENTIFIER.assert_called_once_with()
            mock_SYSTEMTIME.assert_called_once_with()
            mock_GetSystemTime.assert_called_once_with(mock_byref())
            mock_copy.assert_called_once_with(mock_SYSTEMTIME())
            mock_CertCreateSelfSignCertificate.assert_called_once_with(
                None, mock_byref(), 0, mock_byref(),
                mock_byref(), mock_byref(), mock_byref(), None)
            mock_CertAddEnhancedKeyUsageIdentifier.assert_called_with(
                mock_CertCreateSelfSignCertificate(),
                cryptoapi.szOID_PKIX_KP_SERVER_AUTH)
            mock_CertOpenStore.assert_called_with(
                cryptoapi.CERT_STORE_PROV_SYSTEM, 0, 0,
                cryptoapi.CERT_SYSTEM_STORE_LOCAL_MACHINE,
                unicode(x509.STORE_NAME_MY))
            mock_get_cert_thumprint.assert_called_once_with(
                mock_CertCreateSelfSignCertificate())

            mock_CertCloseStore.assert_called_once_with(store_handle, 0)
            mock_CertFreeCertificateContext.assert_called_once_with(
                mock_CertCreateSelfSignCertificate())
            mock_free.assert_called_once_with(mock_cast())

            self.assertEqual(response, mock_get_cert_thumprint())

        mock_generate_key.assert_called_once_with('fake_name', True)

    def test_create_self_signed_cert(self):
        self._test_create_self_signed_cert(certstr='fake cert name',
                                           certificate='fake certificate',
                                           enhanced_key='fake key',
                                           store_handle='fake handle',
                                           context_to_store='fake context')

    def test_create_self_signed_cert_CertStrToName_fail(self):
        self._test_create_self_signed_cert(certstr=None,
                                           certificate='fake certificate',
                                           enhanced_key='fake key',
                                           store_handle='fake handle',
                                           context_to_store='fake context')

    def test_create_self_signed_cert_CertCreateSelfSignCertificate_fail(self):
        self._test_create_self_signed_cert(certstr='fake cert name',
                                           certificate=None,
                                           enhanced_key='fake key',
                                           store_handle='fake handle',
                                           context_to_store='fake context')

    def test_create_self_signed_cert_AddEnhancedKeyUsageIdentifier_fail(self):
        self._test_create_self_signed_cert(certstr='fake cert name',
                                           certificate='fake certificate',
                                           enhanced_key=None,
                                           store_handle='fake handle',
                                           context_to_store='fake context')

    def test_create_self_signed_cert_CertOpenStore_fail(self):
        self._test_create_self_signed_cert(certstr='fake cert name',
                                           certificate='fake certificate',
                                           enhanced_key='fake key',
                                           store_handle=None,
                                           context_to_store='fake context')

    def test_create_self_signed_cert_AddCertificateContextToStore_fail(self):
        self._test_create_self_signed_cert(certstr='fake cert name',
                                           certificate='fake certificate',
                                           enhanced_key='fake key',
                                           store_handle='fake handle',
                                           context_to_store=None)

    def test_get_cert_base64(self):
        fake_cert_data = ''
        fake_cert_data += x509constants.PEM_HEADER + '\n'
        fake_cert_data += 'fake cert' + '\n'
        fake_cert_data += x509constants.PEM_FOOTER
        response = self._x509._get_cert_base64(fake_cert_data)
        self.assertEqual(response, 'fake cert')

    @mock.patch('cloudbaseinit.utils.windows.x509.free')
    @mock.patch('cloudbaseinit.utils.windows.x509.CryptoAPICertManager'
                '._get_cert_thumprint')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertCloseStore')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertFreeCertificateContext')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertGetNameString')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertAddEncodedCertificateToStore')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CertOpenStore')
    @mock.patch('cloudbaseinit.utils.windows.cryptoapi.'
                'CryptStringToBinaryA')
    @mock.patch('cloudbaseinit.utils.windows.x509.CryptoAPICertManager'
                '._get_cert_base64')
    @mock.patch('ctypes.POINTER')
    @mock.patch('cloudbaseinit.utils.windows.x509.malloc')
    @mock.patch('ctypes.cast')
    @mock.patch('ctypes.byref')
    @mock.patch('ctypes.wintypes.DWORD')
    @mock.patch('ctypes.create_unicode_buffer')
    def _test_import_cert(self, mock_create_unicode_buffer, mock_DWORD,
                          mock_byref, mock_cast,
                          mock_malloc, mock_POINTER, mock_get_cert_base64,
                          mock_CryptStringToBinaryA, mock_CertOpenStore,
                          mock_CertAddEncodedCertificateToStore,
                          mock_CertGetNameString,
                          mock_CertFreeCertificateContext,
                          mock_CertCloseStore, mock_get_cert_thumprint,
                          mock_free, crypttstr, store_handle, add_enc_cert,
                          upn_len):
        fake_cert_data = ''
        fake_cert_data += x509constants.PEM_HEADER + '\n'
        fake_cert_data += 'fake cert' + '\n'
        fake_cert_data += x509constants.PEM_FOOTER
        mock_get_cert_base64.return_value = 'fake cert'
        mock_CryptStringToBinaryA.return_value = crypttstr
        mock_CertOpenStore.return_value = store_handle
        mock_CertAddEncodedCertificateToStore.return_value = add_enc_cert
        mock_CertGetNameString.side_effect = [2, upn_len]

        expected = [mock.call('fake cert', len('fake cert'),
                              cryptoapi.CRYPT_STRING_BASE64, None,
                              mock_byref(), None, None),
                    mock.call('fake cert', len('fake cert'),
                              cryptoapi.CRYPT_STRING_BASE64, mock_cast(),
                              mock_byref(), None, None)]
        expected2 = [mock.call(mock_POINTER()(), cryptoapi.CERT_NAME_UPN_TYPE,
                               0, None, None, 0),
                     mock.call(mock_POINTER()(), cryptoapi.CERT_NAME_UPN_TYPE,
                               0, None, mock_create_unicode_buffer(), 2)]

        if (not crypttstr or store_handle is None or add_enc_cert is None or
                upn_len != 2):
            self.assertRaises(cryptoapi.CryptoAPIException,
                              self._x509.import_cert, fake_cert_data, True,
                              x509.STORE_NAME_MY)
        else:
            response = self._x509.import_cert(fake_cert_data)
            mock_cast.assert_called_with(mock_malloc(), mock_POINTER())
            self.assertEqual(mock_CryptStringToBinaryA.call_args_list,
                             expected)
            mock_CertOpenStore.assert_called_with(
                cryptoapi.CERT_STORE_PROV_SYSTEM, 0, 0,
                cryptoapi.CERT_SYSTEM_STORE_LOCAL_MACHINE,
                unicode(x509.STORE_NAME_MY))
            mock_CertAddEncodedCertificateToStore.assert_called_with(
                mock_CertOpenStore(),
                cryptoapi.X509_ASN_ENCODING | cryptoapi.PKCS_7_ASN_ENCODING,
                mock_cast(), mock_DWORD(),
                cryptoapi.CERT_STORE_ADD_REPLACE_EXISTING, mock_byref())
            mock_create_unicode_buffer.assert_called_with(2)
            self.assertEqual(mock_CertGetNameString.call_args_list, expected2)
            mock_get_cert_thumprint.assert_called_once_with(mock_POINTER()())
            mock_CertFreeCertificateContext.assert_called_once_with(
                mock_POINTER()())
            mock_CertCloseStore.assert_called_once_with(
                mock_CertOpenStore(), 0)
            mock_free.assert_called_once_with(mock_cast())
            self.assertEqual(response, (mock_get_cert_thumprint(),
                                        mock_create_unicode_buffer().value))
        mock_get_cert_base64.assert_called_with(fake_cert_data)

    def test_import_cert(self):
        self._test_import_cert(crypttstr=True, store_handle='fake handle',
                               add_enc_cert='fake encoded cert', upn_len=2)

    def test_import_cert_CryptStringToBinaryA_fail(self):
        self._test_import_cert(crypttstr=False, store_handle='fake handle',
                               add_enc_cert='fake encoded cert', upn_len=2)

    def test_import_cert_CertOpenStore_fail(self):
        self._test_import_cert(crypttstr=False, store_handle=None,
                               add_enc_cert='fake encoded cert', upn_len=2)

    def test_import_cert_CertAddEncodedCertificateToStore_fail(self):
        self._test_import_cert(crypttstr=True, store_handle='fake handle',
                               add_enc_cert=None, upn_len=2)

    def test_import_cert_CertGetNameString_fail(self):
        self._test_import_cert(crypttstr=True, store_handle='fake handle',
                               add_enc_cert='fake encoded cert', upn_len=3)

########NEW FILE########
__FILENAME__ = classloader
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import imp
import os

from cloudbaseinit.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class ClassLoader(object):
    def load_class(self, class_path):
        LOG.debug('Loading class \'%s\'' % class_path)
        parts = class_path.rsplit('.', 1)
        module = __import__(parts[0], fromlist=parts[1])
        return getattr(module, parts[1])

    def load_module(self, path):
        module_name, file_ext = os.path.splitext(os.path.split(path)[-1])

        if file_ext.lower() == '.py':
            module = imp.load_source(module_name, path)
        elif file_ext.lower() == '.pyc':
            module = imp.load_compiled(module_name, path)

        return module

########NEW FILE########
__FILENAME__ = crypt
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import base64
import ctypes
import ctypes.util
import struct
import sys

if sys.platform == "win32":
    openssl_lib_path = "libeay32.dll"
else:
    openssl_lib_path = ctypes.util.find_library("ssl")

openssl = ctypes.CDLL(openssl_lib_path)
clib = ctypes.CDLL(ctypes.util.find_library("c"))


class RSA(ctypes.Structure):
    _fields_ = [
        ("pad", ctypes.c_int),
        ("version", ctypes.c_long),
        ("meth", ctypes.c_void_p),
        ("engine", ctypes.c_void_p),
        ("n", ctypes.c_void_p),
        ("e", ctypes.c_void_p),
        ("d", ctypes.c_void_p),
        ("p", ctypes.c_void_p),
        ("q", ctypes.c_void_p),
        ("dmp1", ctypes.c_void_p),
        ("dmq1", ctypes.c_void_p),
        ("iqmp", ctypes.c_void_p),
        ("sk", ctypes.c_void_p),
        ("dummy", ctypes.c_int),
        ("references", ctypes.c_int),
        ("flags", ctypes.c_int),
        ("_method_mod_n", ctypes.c_void_p),
        ("_method_mod_p", ctypes.c_void_p),
        ("_method_mod_q", ctypes.c_void_p),
        ("bignum_data", ctypes.c_char_p),
        ("blinding", ctypes.c_void_p),
        ("mt_blinding", ctypes.c_void_p)
    ]

openssl.RSA_PKCS1_PADDING = 1

openssl.RSA_new.restype = ctypes.POINTER(RSA)

openssl.BN_bin2bn.restype = ctypes.c_void_p
openssl.BN_bin2bn.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]

openssl.BN_new.restype = ctypes.c_void_p

openssl.RSA_size.restype = ctypes.c_int
openssl.RSA_size.argtypes = [ctypes.POINTER(RSA)]

openssl.RSA_free.argtypes = [ctypes.POINTER(RSA)]

openssl.PEM_write_RSAPublicKey.restype = ctypes.c_int
openssl.PEM_write_RSAPublicKey.argtypes = [ctypes.c_void_p,
                                           ctypes.POINTER(RSA)]

openssl.ERR_get_error.restype = ctypes.c_long
openssl.ERR_get_error.argtypes = []

openssl.ERR_error_string_n.restype = ctypes.c_void_p
openssl.ERR_error_string_n.argtypes = [ctypes.c_long,
                                       ctypes.c_char_p,
                                       ctypes.c_int]

openssl.ERR_load_crypto_strings.restype = ctypes.c_int
openssl.ERR_load_crypto_strings.argtypes = []

clib.fopen.restype = ctypes.c_void_p
clib.fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

clib.fclose.restype = ctypes.c_int
clib.fclose.argtypes = [ctypes.c_void_p]


class CryptException(Exception):
    pass


class OpenSSLException(CryptException):
    def __init__(self):
        message = self._get_openssl_error_msg()
        super(OpenSSLException, self).__init__(message)

    def _get_openssl_error_msg(self):
        openssl.ERR_load_crypto_strings()
        errno = openssl.ERR_get_error()
        errbuf = ctypes.create_string_buffer(1024)
        openssl.ERR_error_string_n(errno, errbuf, 1024)
        return errbuf.value.decode("ascii")


class RSAWrapper(object):
    def __init__(self, rsa_p):
        self._rsa_p = rsa_p

    def __enter__(self):
        return self

    def __exit__(self, tp, value, tb):
        self.free()

    def free(self):
        openssl.RSA_free(self._rsa_p)

    def public_encrypt(self, clear_text):
        flen = len(clear_text)
        rsa_size = openssl.RSA_size(self._rsa_p)
        enc_text = ctypes.create_string_buffer(rsa_size)

        enc_text_len = openssl.RSA_public_encrypt(flen,
                                                  clear_text,
                                                  enc_text,
                                                  self._rsa_p,
                                                  openssl.RSA_PKCS1_PADDING)
        if enc_text_len == -1:
            raise OpenSSLException()

        return enc_text[:enc_text_len]


class CryptManager(object):
    def load_ssh_rsa_public_key(self, ssh_pub_key):
        ssh_rsa_prefix = "ssh-rsa "

        if not ssh_pub_key.startswith(ssh_rsa_prefix):
            raise CryptException('Invalid SSH key')

        s = ssh_pub_key[len(ssh_rsa_prefix):]
        idx = s.find(' ')
        if idx >= 0:
            b64_pub_key = s[:idx]
        else:
            b64_pub_key = s

        pub_key = base64.b64decode(b64_pub_key)

        offset = 0

        key_type_len = struct.unpack('>I', pub_key[offset:offset + 4])[0]
        offset += 4

        key_type = pub_key[offset:offset + key_type_len]
        offset += key_type_len

        if not key_type in ['ssh-rsa', 'rsa', 'rsa1']:
            raise CryptException('Unsupported SSH key type "%s". '
                                 'Only RSA keys are currently supported'
                                 % key_type)

        rsa_p = openssl.RSA_new()
        try:
            rsa_p.contents.e = openssl.BN_new()
            rsa_p.contents.n = openssl.BN_new()

            e_len = struct.unpack('>I', pub_key[offset:offset + 4])[0]
            offset += 4

            e_key_bin = pub_key[offset:offset + e_len]
            offset += e_len

            if not openssl.BN_bin2bn(e_key_bin, e_len, rsa_p.contents.e):
                raise OpenSSLException()

            n_len = struct.unpack('>I', pub_key[offset:offset + 4])[0]
            offset += 4

            n_key_bin = pub_key[offset:offset + n_len]
            offset += n_len

            if offset != len(pub_key):
                raise CryptException('Invalid SSH key')

            if not openssl.BN_bin2bn(n_key_bin, n_len, rsa_p.contents.n):
                raise OpenSSLException()

            return RSAWrapper(rsa_p)
        except:
            openssl.RSA_free(rsa_p)
            raise

########NEW FILE########
__FILENAME__ = dhcp
# Copyright 2014 Cloudbase Solutions Srl
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

import datetime
import netifaces
import random
import socket
import struct

_DHCP_COOKIE = b'\x63\x82\x53\x63'
_OPTION_END = b'\xff'

OPTION_NTP_SERVERS = 42


def _get_dhcp_request_data(id_req, mac_address_b, requested_options,
                           vendor_id):
    # See: http://www.ietf.org/rfc/rfc2131.txt
    data = b'\x01'
    data += b'\x01'
    data += b'\x06'
    data += b'\x00'
    data += struct.pack('!L', id_req)
    data += b'\x00\x00'
    data += b'\x00\x00'
    data += b'\x00\x00\x00\x00'
    data += b'\x00\x00\x00\x00'
    data += b'\x00\x00\x00\x00'
    data += b'\x00\x00\x00\x00'
    data += mac_address_b
    data += b'\x00' * 10
    data += b'\x00' * 64
    data += b'\x00' * 128
    data += _DHCP_COOKIE
    data += b'\x35\x01\x01'

    if vendor_id:
        vendor_id_b = vendor_id.encode('ascii')
        data += b'\x3c' + struct.pack('b', len(vendor_id_b)) + vendor_id_b

    data += b'\x3d\x07\x01' + mac_address_b
    data += b'\x37' + struct.pack('b', len(requested_options))

    for option in requested_options:
        data += struct.pack('b', option)

    data += _OPTION_END
    return data


def _parse_dhcp_reply(data, id_req):
    message_type = struct.unpack('b', data[0])[0]

    if message_type != 2:
        return (False, {})

    id_reply = struct.unpack('!L', data[4:8])[0]
    if id_reply != id_req:
        return (False, {})

    if data[236:240] != _DHCP_COOKIE:
        return (False, {})

    options = {}

    i = 240
    while data[i] != _OPTION_END:
        id_option = struct.unpack('b', data[i])[0]
        option_data_len = struct.unpack('b', data[i + 1])[0]
        i += 2
        options[id_option] = data[i: i + option_data_len]
        i += option_data_len

    return (True, options)


def _get_mac_address_by_local_ip(ip_addr):
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        for addr in addrs[netifaces.AF_INET]:
            if addr['addr'] == ip_addr:
                return addrs[netifaces.AF_LINK][0]['addr']


def get_dhcp_options(dhcp_host, requested_options=[], timeout=5.0,
                     vendor_id='cloudbase-init'):
    id_req = random.randint(0, 2 ** 32 - 1)
    options = None

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(('', 68))
        s.settimeout(timeout)
        s.connect((dhcp_host, 67))

        local_ip_addr = s.getsockname()[0]
        mac_address = _get_mac_address_by_local_ip(local_ip_addr)

        data = _get_dhcp_request_data(id_req, mac_address, requested_options,
                                      vendor_id)
        s.send(data)

        start = datetime.datetime.now()
        now = start
        replied = False
        while (not replied and
                now - start < datetime.timedelta(seconds=timeout)):
            data = s.recv(1024)
            (replied, options) = _parse_dhcp_reply(data, id_req)
            now = datetime.datetime.now()
    except socket.timeout:
        pass
    finally:
        s.close()

    return options

########NEW FILE########
__FILENAME__ = log
# Copyright 2014 Cloudbase Solutions Srl
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

import logging
import serial

from oslo.config import cfg

from cloudbaseinit.openstack.common import log as openstack_logging

opts = [
    cfg.StrOpt('logging_serial_port_settings', default=None,
               help='Serial port logging settings. Format: '
               '"port,baudrate,parity,bytesize", e.g.: "COM1,115200,N,8". '
               'Set to None (default) to disable.'),
]

CONF = cfg.CONF
CONF.register_opts(opts)
CONF.import_opt('log_date_format', 'cloudbaseinit.openstack.common.log')


class SerialPortHandler(logging.StreamHandler):
    def __init__(self):
        if CONF.logging_serial_port_settings:
            settings = CONF.logging_serial_port_settings.split(',')

            self._port = serial.Serial(port=settings[0],
                                       baudrate=int(settings[1]),
                                       parity=settings[2],
                                       bytesize=int(settings[3]))
            if not self._port.isOpen():
                self._port.open()

            super(SerialPortHandler, self).__init__(self._port)

    def close(self):
        if self._port and self._port.isOpen():
            self._port.close()


def setup(product_name):
    openstack_logging.setup(product_name)

    if CONF.logging_serial_port_settings:
        log_root = openstack_logging.getLogger(product_name).logger

        serialportlog = SerialPortHandler()
        log_root.addHandler(serialportlog)

        datefmt = CONF.log_date_format
        serialportlog.setFormatter(
            openstack_logging.ContextFormatter(project=product_name,
                                               datefmt=datefmt))

########NEW FILE########
__FILENAME__ = network
# Copyright 2012 Cloudbase Solutions Srl
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

import sys
import urllib2
import urlparse

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory

LOG = logging.getLogger(__name__)

MAX_URL_CHECK_RETRIES = 3


def check_url(url, retries_count=MAX_URL_CHECK_RETRIES):
    for i in range(0, MAX_URL_CHECK_RETRIES):
        try:
            LOG.debug("Testing url: %s" % url)
            urllib2.urlopen(url)
            return True
        except Exception:
            pass
    return False


def check_metadata_ip_route(metadata_url):
    '''
    Workaround for: https://bugs.launchpad.net/quantum/+bug/1174657
    '''
    osutils = osutils_factory.get_os_utils()

    if sys.platform == 'win32' and osutils.check_os_version(6, 0):
        # 169.254.x.x addresses are not getting routed starting from
        # Windows Vista / 2008
        metadata_netloc = urlparse.urlparse(metadata_url).netloc
        metadata_host = metadata_netloc.split(':')[0]

        if metadata_host.startswith("169.254."):
            if (not osutils.check_static_route_exists(metadata_host) and
                    not check_url(metadata_url)):
                (interface_index, gateway) = osutils.get_default_gateway()
                if gateway:
                    try:
                        LOG.debug('Setting gateway for host: %s',
                                  metadata_host)
                        osutils.add_static_route(metadata_host,
                                                 "255.255.255.255",
                                                 gateway,
                                                 interface_index,
                                                 10)
                    except Exception, ex:
                        # Ignore it
                        LOG.exception(ex)

########NEW FILE########
__FILENAME__ = cryptoapi
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import ctypes

from ctypes import windll
from ctypes import wintypes


class CryptoAPIException(Exception):
    def __init__(self):
        message = self._get_windows_error()
        super(CryptoAPIException, self).__init__(message)

    def _get_windows_error(self):
        err_code = GetLastError()
        return "CryptoAPI error: 0x%0x" % err_code


class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ('wYear',           wintypes.WORD),
        ('wMonth',          wintypes.WORD),
        ('wDayOfWeek',      wintypes.WORD),
        ('wDay',            wintypes.WORD),
        ('wHour',           wintypes.WORD),
        ('wMinute',         wintypes.WORD),
        ('wSecond',         wintypes.WORD),
        ('wMilliseconds',   wintypes.WORD),
    ]


class CERT_CONTEXT(ctypes.Structure):
    _fields_ = [
        ('dwCertEncodingType',  wintypes.DWORD),
        ('pbCertEncoded',  ctypes.POINTER(wintypes.BYTE)),
        ('cbCertEncoded',  wintypes.DWORD),
        ('pCertInfo',  ctypes.c_void_p),
        ('hCertStore',  wintypes.HANDLE),
    ]


class CRYPTOAPI_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData',  wintypes.DWORD),
        ('pbData',  ctypes.POINTER(wintypes.BYTE)),
    ]


class CRYPT_ALGORITHM_IDENTIFIER(ctypes.Structure):
    _fields_ = [
        ('pszObjId',    wintypes.LPSTR),
        ('Parameters',  CRYPTOAPI_BLOB),
    ]


class CRYPT_KEY_PROV_PARAM(ctypes.Structure):
    _fields_ = [
        ('dwParam', wintypes.DWORD),
        ('pbData',  ctypes.POINTER(wintypes.BYTE)),
        ('cbData',  wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
    ]


class CRYPT_KEY_PROV_INFO(ctypes.Structure):
    _fields_ = [
        ('pwszContainerName',   wintypes.LPWSTR),
        ('pwszProvName',        wintypes.LPWSTR),
        ('dwProvType',          wintypes.DWORD),
        ('dwFlags',             wintypes.DWORD),
        ('cProvParam',          wintypes.DWORD),
        ('cProvParam',          ctypes.POINTER(CRYPT_KEY_PROV_PARAM)),
        ('dwKeySpec',           wintypes.DWORD),
    ]


AT_SIGNATURE = 2
CERT_NAME_UPN_TYPE = 8
CERT_SHA1_HASH_PROP_ID = 3
CERT_STORE_ADD_REPLACE_EXISTING = 3
CERT_STORE_PROV_SYSTEM = wintypes.LPSTR(10)
CERT_SYSTEM_STORE_CURRENT_USER = 65536
CERT_SYSTEM_STORE_LOCAL_MACHINE = 131072
CERT_X500_NAME_STR = 3
CRYPT_MACHINE_KEYSET = 32
CRYPT_NEWKEYSET = 8
CRYPT_STRING_BASE64 = 1
PKCS_7_ASN_ENCODING = 65536
PROV_RSA_FULL = 1
X509_ASN_ENCODING = 1
szOID_PKIX_KP_SERVER_AUTH = "1.3.6.1.5.5.7.3.1"
szOID_RSA_SHA1RSA = "1.2.840.113549.1.1.5"

advapi32 = windll.advapi32
crypt32 = windll.crypt32
kernel32 = windll.kernel32

advapi32.CryptAcquireContextW.restype = wintypes.BOOL
advapi32.CryptAcquireContextW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR,
                                          wintypes.LPCWSTR, wintypes.DWORD,
                                          wintypes.DWORD]
CryptAcquireContext = advapi32.CryptAcquireContextW

advapi32.CryptReleaseContext.restype = wintypes.BOOL
advapi32.CryptReleaseContext.argtypes = [wintypes.HANDLE, wintypes.DWORD]
CryptReleaseContext = advapi32.CryptReleaseContext

advapi32.CryptGenKey.restype = wintypes.BOOL
advapi32.CryptGenKey.argtypes = [wintypes.HANDLE,
                                 wintypes.DWORD,
                                 wintypes.DWORD,
                                 ctypes.POINTER(wintypes.HANDLE)]
CryptGenKey = advapi32.CryptGenKey

advapi32.CryptDestroyKey.restype = wintypes.BOOL
advapi32.CryptDestroyKey.argtypes = [wintypes.HANDLE]
CryptDestroyKey = advapi32.CryptDestroyKey

crypt32.CertStrToNameW.restype = wintypes.BOOL
crypt32.CertStrToNameW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR,
                                   wintypes.DWORD, ctypes.c_void_p,
                                   ctypes.POINTER(wintypes.BYTE),
                                   ctypes.POINTER(wintypes.DWORD),
                                   ctypes.POINTER(wintypes.LPCWSTR)]
CertStrToName = crypt32.CertStrToNameW

# TODO(alexpilotti): this is not a CryptoAPI funtion, putting it in a separate
# module would be more correct
kernel32.GetSystemTime.restype = None
kernel32.GetSystemTime.argtypes = [ctypes.POINTER(SYSTEMTIME)]
GetSystemTime = kernel32.GetSystemTime

# TODO(alexpilotti): this is not a CryptoAPI funtion, putting it in a separate
# module would be more correct
kernel32.GetLastError.restype = wintypes.DWORD
kernel32.GetLastError.argtypes = []
GetLastError = kernel32.GetLastError

crypt32.CertCreateSelfSignCertificate.restype = ctypes.POINTER(CERT_CONTEXT)
crypt32.CertCreateSelfSignCertificate.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CRYPTOAPI_BLOB),
    wintypes.DWORD,
    ctypes.POINTER(CRYPT_KEY_PROV_INFO),
    ctypes.POINTER(CRYPT_ALGORITHM_IDENTIFIER),
    ctypes.POINTER(SYSTEMTIME),
    ctypes.POINTER(SYSTEMTIME),
    # PCERT_EXTENSIONS
    ctypes.c_void_p]
CertCreateSelfSignCertificate = crypt32.CertCreateSelfSignCertificate

crypt32.CertAddEnhancedKeyUsageIdentifier.restype = wintypes.BOOL
crypt32.CertAddEnhancedKeyUsageIdentifier.argtypes = [
    ctypes.POINTER(CERT_CONTEXT),
    wintypes.LPCSTR]
CertAddEnhancedKeyUsageIdentifier = crypt32.CertAddEnhancedKeyUsageIdentifier

crypt32.CertOpenStore.restype = wintypes.HANDLE
crypt32.CertOpenStore.argtypes = [wintypes.LPCSTR, wintypes.DWORD,
                                  wintypes.HANDLE, wintypes.DWORD,
                                  ctypes.c_void_p]
CertOpenStore = crypt32.CertOpenStore

crypt32.CertAddCertificateContextToStore.restype = wintypes.BOOL
crypt32.CertAddCertificateContextToStore.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(CERT_CONTEXT),
    wintypes.DWORD,
    ctypes.POINTER(CERT_CONTEXT)]
CertAddCertificateContextToStore = crypt32.CertAddCertificateContextToStore

crypt32.CryptStringToBinaryA.restype = wintypes.BOOL
crypt32.CryptStringToBinaryA.argtypes = [wintypes.LPCSTR,
                                         wintypes.DWORD,
                                         wintypes.DWORD,
                                         ctypes.POINTER(wintypes.BYTE),
                                         ctypes.POINTER(wintypes.DWORD),
                                         ctypes.POINTER(wintypes.DWORD),
                                         ctypes.POINTER(wintypes.DWORD)]
CryptStringToBinaryA = crypt32.CryptStringToBinaryA

crypt32.CertAddEncodedCertificateToStore.restype = wintypes.BOOL
crypt32.CertAddEncodedCertificateToStore.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.BYTE),
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.POINTER(CERT_CONTEXT))]
CertAddEncodedCertificateToStore = crypt32.CertAddEncodedCertificateToStore

crypt32.CertGetNameStringW.restype = wintypes.DWORD
crypt32.CertGetNameStringW.argtypes = [ctypes.POINTER(CERT_CONTEXT),
                                       wintypes.DWORD,
                                       wintypes.DWORD,
                                       ctypes.c_void_p,
                                       wintypes.LPWSTR,
                                       wintypes.DWORD]
CertGetNameString = crypt32.CertGetNameStringW

crypt32.CertFreeCertificateContext.restype = wintypes.BOOL
crypt32.CertFreeCertificateContext.argtypes = [ctypes.POINTER(CERT_CONTEXT)]
CertFreeCertificateContext = crypt32.CertFreeCertificateContext

crypt32.CertCloseStore.restype = wintypes.BOOL
crypt32.CertCloseStore.argtypes = [wintypes.HANDLE, wintypes.DWORD]
CertCloseStore = crypt32.CertCloseStore

crypt32.CertGetCertificateContextProperty.restype = wintypes.BOOL
crypt32.CertGetCertificateContextProperty.argtypes = [
    ctypes.POINTER(CERT_CONTEXT),
    wintypes.DWORD,
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.DWORD)]
CertGetCertificateContextProperty = crypt32.CertGetCertificateContextProperty

########NEW FILE########
__FILENAME__ = physical_disk
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import ctypes

from ctypes import windll
from ctypes import wintypes

kernel32 = windll.kernel32


class Win32_DiskGeometry(ctypes.Structure):
    FixedMedia = 12

    _fields_ = [
        ('Cylinders',         wintypes.LARGE_INTEGER),
        ('MediaType',         wintypes.DWORD),
        ('TracksPerCylinder', wintypes.DWORD),
        ('SectorsPerTrack',   wintypes.DWORD),
        ('BytesPerSector',    wintypes.DWORD),
    ]


class PhysicalDisk(object):
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 1
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_READONLY = 1
    INVALID_HANDLE_VALUE = -1
    IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x70000
    FILE_BEGIN = 0
    INVALID_SET_FILE_POINTER = 0xFFFFFFFFL

    def __init__(self, path):
        self._path = path
        self._handle = 0
        self._geom = None

    def open(self):
        if self._handle:
            self.close()

        handle = kernel32.CreateFileW(
            ctypes.c_wchar_p(self._path),
            self.GENERIC_READ,
            self.FILE_SHARE_READ,
            0,
            self.OPEN_EXISTING,
            self.FILE_ATTRIBUTE_READONLY,
            0)
        if handle == self.INVALID_HANDLE_VALUE:
            raise Exception('Cannot open file')
        self._handle = handle

    def close(self):
        kernel32.CloseHandle(self._handle)
        self._handle = 0
        self._geom = None

    def get_geometry(self):
        if not self._geom:
            geom = Win32_DiskGeometry()
            bytes_returned = wintypes.DWORD()
            ret_val = kernel32.DeviceIoControl(
                self._handle,
                self.IOCTL_DISK_GET_DRIVE_GEOMETRY,
                0,
                0,
                ctypes.byref(geom),
                ctypes.sizeof(geom),
                ctypes.byref(bytes_returned),
                0)
            if not ret_val:
                raise Exception("Cannot get disk geometry")
            self._geom = geom
        return self._geom

    def seek(self, offset):
        high = wintypes.DWORD(offset >> 32)
        low = wintypes.DWORD(offset & 0xFFFFFFFFL)

        ret_val = kernel32.SetFilePointer(self._handle, low,
                                          ctypes.byref(high),
                                          self.FILE_BEGIN)
        if ret_val == self.INVALID_SET_FILE_POINTER:
            raise Exception("Seek error")

    def read(self, bytes_to_read):
        buf = ctypes.create_string_buffer(bytes_to_read)
        bytes_read = wintypes.DWORD()
        ret_val = kernel32.ReadFile(self._handle, buf, bytes_to_read,
                                    ctypes.byref(bytes_read), 0)
        if not ret_val:
            raise Exception("Read exception")
        return (buf, bytes_read.value)

########NEW FILE########
__FILENAME__ = vds
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Cloudbase Solutions Srl
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

import comtypes
import ctypes

from comtypes import client
from ctypes import wintypes

VDS_QUERY_SOFTWARE_PROVIDERS = 1
VDS_DET_FREE = 1

CLSID_VdsLoader = '{9C38ED61-D565-4728-AEEE-C80952F0ECDE}'

msvcrt = ctypes.cdll.msvcrt
msvcrt.memcmp.restype = ctypes.c_int
msvcrt.memcmp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]


class GUID(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.wintypes.DWORD),
        ("data2", ctypes.wintypes.WORD),
        ("data3", ctypes.wintypes.WORD),
        ("data4", ctypes.c_byte * 8)]

    def __eq__(self, other):
        if type(other) != GUID:
            return False
        return not msvcrt.memcmp(ctypes.addressof(self),
                                 ctypes.addressof(other),
                                 ctypes.sizeof(GUID))

    def __ne__(self, other):
        return not self.__eq__(other)


class VDS_DISK_PROP_SWITCH_TYPE(ctypes.Union):
    _fields_ = [
        ("dwSignature", wintypes.DWORD),
        ("DiskGuid", GUID),
    ]


class VDS_DISK_PROP(ctypes.Structure):
    _fields_ = [
        ("id", GUID),
        ("status", ctypes.c_int),
        ("ReserveMode", ctypes.c_int),
        ("health", ctypes.c_int),
        ("dwDeviceType", wintypes.DWORD),
        ("dwMediaType", wintypes.DWORD),
        ("ullSize", wintypes.ULARGE_INTEGER),
        ("ulBytesPerSector", wintypes.ULONG),
        ("ulSectorsPerTrack", wintypes.ULONG),
        ("ulTracksPerCylinder", wintypes.ULONG),
        ("ulFlags", wintypes.ULONG),
        ("BusType", ctypes.c_int),
        ("PartitionStyle", ctypes.c_int),
        ("switch_type", VDS_DISK_PROP_SWITCH_TYPE),
        ("pwszDiskAddress", wintypes.c_void_p),
        ("pwszName", wintypes.c_void_p),
        ("pwszFriendlyName", wintypes.c_void_p),
        ("pwszAdaptorName", wintypes.c_void_p),
        ("pwszDevicePath", wintypes.c_void_p),
    ]


class VDS_DISK_EXTENT(ctypes.Structure):
    _fields_ = [
        ("diskId", GUID),
        ("type", ctypes.c_int),
        ("ullOffset", wintypes.ULARGE_INTEGER),
        ("ullSize", wintypes.ULARGE_INTEGER),
        ("volumeId", GUID),
        ("plexId", GUID),
        ("memberIdx", wintypes.ULONG),
    ]


class VDS_VOLUME_PROP(ctypes.Structure):
    _fields_ = [
        ("id", GUID),
        ("type", ctypes.c_int),
        ("status", ctypes.c_int),
        ("health", ctypes.c_int),
        ("TransitionState", ctypes.c_int),
        ("ullSize", wintypes.ULARGE_INTEGER),
        ("ulFlags", wintypes.ULONG),
        ("RecommendedFileSystemType", ctypes.c_int),
        ("pwszName", wintypes.c_void_p),
    ]


class VDS_INPUT_DISK(ctypes.Structure):
    _fields_ = [
        ("diskId", GUID),
        ("ullSize", wintypes.ULARGE_INTEGER),
        ("plexId", GUID),
        ("memberIdx", wintypes.ULONG),
    ]


class VDS_ASYNC_OUTPUT_cp(ctypes.Structure):
    _fields_ = [
        ("ullOffset", wintypes.ULARGE_INTEGER),
        ("volumeId", GUID),
    ]


class VDS_ASYNC_OUTPUT_cv(ctypes.Structure):
    _fields_ = [
        ("pVolumeUnk", wintypes.ULARGE_INTEGER),
    ]


class VDS_ASYNC_OUTPUT_bvp(ctypes.Structure):
    _fields_ = [
        ("pVolumeUnk", ctypes.POINTER(comtypes.IUnknown)),
    ]


class VDS_ASYNC_OUTPUT_sv(ctypes.Structure):
    _fields_ = [
        ("ullReclaimedBytes", wintypes.ULARGE_INTEGER),
    ]


class VDS_ASYNC_OUTPUT_cl(ctypes.Structure):
    _fields_ = [
        ("pLunUnk", ctypes.POINTER(comtypes.IUnknown)),
    ]


class VDS_ASYNC_OUTPUT_ct(ctypes.Structure):
    _fields_ = [
        ("pTargetUnk", ctypes.POINTER(comtypes.IUnknown)),
    ]


class VDS_ASYNC_OUTPUT_cpg(ctypes.Structure):
    _fields_ = [
        ("pPortalGroupUnk", ctypes.POINTER(comtypes.IUnknown)),
    ]


class VDS_ASYNC_OUTPUT_SWITCH_TYPE(ctypes.Union):
    _fields_ = [
        ("cp", VDS_ASYNC_OUTPUT_cp),
        ("cv", VDS_ASYNC_OUTPUT_cv),
        ("bvp", VDS_ASYNC_OUTPUT_bvp),
        ("sv", VDS_ASYNC_OUTPUT_sv),
        ("cl", VDS_ASYNC_OUTPUT_cl),
        ("ct", VDS_ASYNC_OUTPUT_ct),
        ("cpg", VDS_ASYNC_OUTPUT_cpg),
    ]


class VDS_ASYNC_OUTPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("switch_type", VDS_ASYNC_OUTPUT_SWITCH_TYPE),
    ]


class IEnumVdsObject(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{118610b7-8d94-4030-b5b8-500889788e4e}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'Next',
                           (['in'], wintypes.ULONG, 'celt'),
                           (['out'], ctypes.POINTER(ctypes.POINTER(
                                                    comtypes.IUnknown)),
                            'ppObjectArray'),
                           (['out'], ctypes.POINTER(wintypes.ULONG),
                            'pcFetched')),
    ]


class IVdsService(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{0818a8ef-9ba9-40d8-a6f9-e22833cc771e}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'IsServiceReady'),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'WaitForServiceReady'),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProperties',
                           (['out'], ctypes.c_void_p, 'pServiceProp')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryProviders',
                           (['in'], wintypes.DWORD, 'masks'),
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(IEnumVdsObject)),
                            'ppEnum'))
    ]


class IVdsServiceLoader(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{e0393303-90d4-4a97-ab71-e9b671ee2729}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'LoadService',
                           (['in'], wintypes.LPCWSTR, 'pwszMachineName'),
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(IVdsService)),
                            'ppService'))
    ]


class IVdsSwProvider(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{9aa58360-ce33-4f92-b658-ed24b14425b8}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryPacks',
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(IEnumVdsObject)),
                            'ppEnum'))
    ]


class IVdsPack(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{3b69d7f5-9d94-4648-91ca-79939ba263bf}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProperties',
                           (['out'], ctypes.c_void_p, 'pPackProp')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProvider',
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(comtypes.IUnknown)),
                            'ppProvider')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryVolumes',
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(IEnumVdsObject)),
                            'ppEnum')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryDisks',
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(IEnumVdsObject)),
                            'ppEnum'))
    ]


class IVdsDisk(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{07e5c822-f00c-47a1-8fce-b244da56fd06}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProperties',
                           (['out'], ctypes.POINTER(VDS_DISK_PROP),
                            'pDiskProperties')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetPack',
                           (['out'], ctypes.POINTER(ctypes.POINTER(IVdsPack)),
                            'ppPack')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetIdentificationData',
                           (['out'], ctypes.c_void_p, 'pLunInfo')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryExtents',
                           (['out'], ctypes.POINTER(ctypes.POINTER(
                                                    VDS_DISK_EXTENT)),
                            'ppExtentArray'),
                           (['out'], ctypes.POINTER(wintypes.LONG),
                            'plNumberOfExtents')),
    ]


class IVdsAsync(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{d5d23b6d-5a55-4492-9889-397a3c2d2dbc}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'Cancel'),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'Wait',
                           (['out'], ctypes.POINTER(
                            wintypes.HRESULT), 'pHrResult'),
                           (['out'], ctypes.POINTER(VDS_ASYNC_OUTPUT),
                            'pAsyncOut')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryStatus',
                           (['out'], ctypes.POINTER(
                            wintypes.HRESULT), 'pHrResult'),
                           (['out'], ctypes.POINTER(wintypes.ULONG),
                            'pulPercentCompleted')),
    ]


class IVdsVolume(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{88306bb2-e71f-478c-86a2-79da200a0f11}")

    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProperties',
                           (['out'], ctypes.POINTER(VDS_VOLUME_PROP),
                            'pVolumeProperties')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetPack',
                           (['out'], ctypes.POINTER(ctypes.POINTER(IVdsPack)),
                            'ppPack')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'QueryPlexes',
                           (['out'],
                            ctypes.POINTER(ctypes.POINTER(IEnumVdsObject)),
                            'ppEnum')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'Extend',
                           (['in'], ctypes.POINTER(
                            VDS_INPUT_DISK), 'pInputDiskArray'),
                           (['in'], wintypes.LONG, 'lNumberOfDisks'),
                           (['out'], ctypes.POINTER(
                            ctypes.POINTER(IVdsAsync)), 'ppAsync'),
                           ),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'Shrink',
                           (['in'], wintypes.ULARGE_INTEGER,
                            'ullNumberOfBytesToRemove'),
                           (['out'], ctypes.POINTER(ctypes.POINTER(IVdsAsync)),
                            'ppAsync')),
    ]


def load_vds_service():
    loader = client.CreateObject(CLSID_VdsLoader, interface=IVdsServiceLoader)
    svc = loader.LoadService(None)
    svc.WaitForServiceReady()
    return svc

########NEW FILE########
__FILENAME__ = virtual_disk
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import ctypes

from ctypes import windll
from ctypes import wintypes

kernel32 = windll.kernel32
# VirtDisk.dll is available starting from Windows Server 2008 R2 / Windows7
virtdisk = None


class Win32_GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8)]


def get_WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MICROSOFT():
    guid = Win32_GUID()
    guid.Data1 = 0xec984aec
    guid.Data2 = 0xa0f9
    guid.Data3 = 0x47e9
    ByteArray8 = wintypes.BYTE * 8
    guid.Data4 = ByteArray8(0x90, 0x1f, 0x71, 0x41, 0x5a, 0x66, 0x34, 0x5b)
    return guid


class Win32_VIRTUAL_STORAGE_TYPE(ctypes.Structure):
    _fields_ = [
        ('DeviceId', wintypes.DWORD),
        ('VendorId', Win32_GUID)
    ]


class VirtualDisk(object):
    VIRTUAL_STORAGE_TYPE_DEVICE_ISO = 1
    VIRTUAL_DISK_ACCESS_ATTACH_RO = 0x10000
    VIRTUAL_DISK_ACCESS_READ = 0xd0000
    OPEN_VIRTUAL_DISK_FLAG_NONE = 0
    DETACH_VIRTUAL_DISK_FLAG_NONE = 0
    ATTACH_VIRTUAL_DISK_FLAG_READ_ONLY = 1
    ATTACH_VIRTUAL_DISK_FLAG_NO_DRIVE_LETTER = 2

    def __init__(self, path):
        self._path = path
        self._handle = 0

    def _load_virtdisk_dll(self):
        global virtdisk
        if not virtdisk:
            virtdisk = windll.virtdisk

    def open(self):
        if self._handle:
            self.close()

        self._load_virtdisk_dll()

        vst = Win32_VIRTUAL_STORAGE_TYPE()
        vst.DeviceId = self.VIRTUAL_STORAGE_TYPE_DEVICE_ISO
        vst.VendorId = get_WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MICROSOFT()

        handle = wintypes.HANDLE()
        ret_val = virtdisk.OpenVirtualDisk(ctypes.byref(vst),
                                           ctypes.c_wchar_p(self._path),
                                           self.VIRTUAL_DISK_ACCESS_ATTACH_RO |
                                           self.VIRTUAL_DISK_ACCESS_READ,
                                           self.OPEN_VIRTUAL_DISK_FLAG_NONE, 0,
                                           ctypes.byref(handle))
        if ret_val:
            raise Exception("Cannot open virtual disk")
        self._handle = handle

    def attach(self):
        ret_val = virtdisk.AttachVirtualDisk(
            self._handle, 0, self.ATTACH_VIRTUAL_DISK_FLAG_READ_ONLY, 0, 0, 0)
        if ret_val:
            raise Exception("Cannot attach virtual disk")

    def detach(self):
        ret_val = virtdisk.DetachVirtualDisk(
            self._handle, self.DETACH_VIRTUAL_DISK_FLAG_NONE, 0)
        if ret_val:
            raise Exception("Cannot detach virtual disk")

    def get_physical_path(self):
        buf = ctypes.create_unicode_buffer(1024)
        bufLen = wintypes.DWORD(ctypes.sizeof(buf))
        ret_val = virtdisk.GetVirtualDiskPhysicalPath(self._handle,
                                                      ctypes.byref(bufLen),
                                                      buf)
        if ret_val:
            raise Exception("Cannot get virtual disk physical path")
        return buf.value

    def get_cdrom_drive_mount_point(self):

        mount_point = None

        buf = ctypes.create_unicode_buffer(2048)
        buf_len = kernel32.GetLogicalDriveStringsW(
            ctypes.sizeof(buf) / ctypes.sizeof(wintypes.WCHAR), buf)
        if not buf_len:
            raise Exception("Cannot enumerate logical devices")

        cdrom_dev = self.get_physical_path().rsplit('\\')[-1].upper()

        i = 0
        while not mount_point and i < buf_len:
            curr_drive = ctypes.wstring_at(ctypes.addressof(buf) + i *
                                           ctypes.sizeof(wintypes.WCHAR))[:-1]

            dev = ctypes.create_unicode_buffer(2048)
            ret_val = kernel32.QueryDosDeviceW(curr_drive, dev,
                                               ctypes.sizeof(dev) /
                                               ctypes.sizeof(wintypes.WCHAR))
            if not ret_val:
                raise Exception("Cannot query NT device")

            if dev.value.rsplit('\\')[-1].upper() == cdrom_dev:
                mount_point = curr_drive
            else:
                i += len(curr_drive) + 2

        return mount_point

    def close(self):
        kernel32.CloseHandle(self._handle)
        self._handle = 0

########NEW FILE########
__FILENAME__ = winrmconfig
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
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

import pywintypes
import re

from win32com import client
from xml.etree import ElementTree


CBT_HARDENING_LEVEL_NONE = "none"
CBT_HARDENING_LEVEL_RELAXED = "relaxed"
CBT_HARDENING_LEVEL_STRICT = "strict"

LISTENER_PROTOCOL_HTTP = "HTTP"
LISTENER_PROTOCOL_HTTPS = "HTTPS"


class WinRMConfig(object):
    _SERVICE_AUTH_URI = 'winrm/Config/Service/Auth'
    _SERVICE_LISTENER_URI = ('winrm/Config/Listener?Address='
                             '%(address)s+Transport=%(protocol)s')
    _SERVICE_CERTMAPPING_URI = ('winrm/Config/Service/certmapping?Issuer='
                                '%(issuer)s+Subject=%(subject)s+Uri=%(uri)s')

    def _get_wsman_session(self):
        wsman = client.Dispatch('WSMan.Automation')
        return wsman.CreateSession()

    def _get_node_tag(self, tag):
        return re.match("^{.*}(.*)$", tag).groups(1)[0]

    def _parse_listener_xml(self, data_xml):
        if not data_xml:
            return None

        listening_on = []
        data = {"ListeningOn": listening_on}

        ns = {'cfg':
              'http://schemas.microsoft.com/wbem/wsman/1/config/listener'}
        tree = ElementTree.fromstring(data_xml)
        for node in tree:
            tag = self._get_node_tag(node.tag)
            if tag == "ListeningOn":
                listening_on.append(node.text)
            elif tag == "Enabled":
                if node.text == "true":
                    value = True
                else:
                    value = False
                data[tag] = value
            elif tag == "Port":
                data[tag] = int(node.text)
            else:
                data[tag] = node.text

        return data

    def _parse_cert_mapping_xml(self, data_xml):
        if not data_xml:
            return None

        data = {}

        ns = {'cfg':
              'http://schemas.microsoft.com/wbem/wsman/1/config/service/'
              'certmapping.xsd'}
        tree = ElementTree.fromstring(data_xml)
        for node in tree:
            tag = self._get_node_tag(node.tag)
            if tag == "Enabled":
                if node.text == "true":
                    value = True
                else:
                    value = False
                data[tag] = value
            else:
                data[tag] = node.text

        return data

    def _get_xml_bool(self, value):
        if value:
            return "true"
        else:
            return "false"

    def _get_resource(self, resource_uri):
        session = self._get_wsman_session()
        try:
            return session.Get(resource_uri)
        except pywintypes.com_error, ex:
            if len(ex.excepinfo) > 5 and ex.excepinfo[5] == -2144108544:
                return None
            else:
                raise

    def _delete_resource(self, resource_uri):
        session = self._get_wsman_session()
        session.Delete(resource_uri)

    def _create_resource(self, resource_uri, data_xml):
        session = self._get_wsman_session()
        session.Create(resource_uri, data_xml)

    def get_cert_mapping(self, issuer, subject, uri="*"):
        resource_uri = self._SERVICE_CERTMAPPING_URI % {'issuer': issuer,
                                                        'subject': subject,
                                                        'uri': uri}
        return self._parse_cert_mapping_xml(self._get_resource(resource_uri))

    def delete_cert_mapping(self, issuer, subject, uri="*"):
        resource_uri = self._SERVICE_CERTMAPPING_URI % {'issuer': issuer,
                                                        'subject': subject,
                                                        'uri': uri}
        self._delete_resource(resource_uri)

    def create_cert_mapping(self, issuer, subject, username, password,
                            uri="*", enabled=True):
        resource_uri = self._SERVICE_CERTMAPPING_URI % {'issuer': issuer,
                                                        'subject': subject,
                                                        'uri': uri}
        self._create_resource(
            resource_uri,
            '<p:certmapping xmlns:p="http://schemas.microsoft.com/wbem/wsman/'
            '1/config/service/certmapping.xsd">'
            '<p:Enabled>%(enabled)s</p:Enabled>'
            '<p:Password>%(password)s</p:Password>'
            '<p:UserName>%(username)s</p:UserName>'
            '</p:certmapping>' % {'enabled': self._get_xml_bool(enabled),
                                  'username': username,
                                  'password': password})

    def get_listener(self, protocol=LISTENER_PROTOCOL_HTTPS, address="*"):
        resource_uri = self._SERVICE_LISTENER_URI % {'protocol': protocol,
                                                     'address': address}
        return self._parse_listener_xml(self._get_resource(resource_uri))

    def delete_listener(self, protocol=LISTENER_PROTOCOL_HTTPS, address="*"):
        resource_uri = self._SERVICE_LISTENER_URI % {'protocol': protocol,
                                                     'address': address}
        self._delete_resource(resource_uri)

    def create_listener(self, protocol=LISTENER_PROTOCOL_HTTPS,
                        cert_thumbprint=None, address="*", enabled=True):
        resource_uri = self._SERVICE_LISTENER_URI % {'protocol': protocol,
                                                     'address': address}
        self._create_resource(
            resource_uri,
            '<p:Listener xmlns:p="http://schemas.microsoft.com/'
            'wbem/wsman/1/config/listener.xsd">'
            '<p:Enabled>%(enabled)s</p:Enabled>'
            '<p:CertificateThumbPrint>%(cert_thumbprint)s'
            '</p:CertificateThumbPrint>'
            '<p:URLPrefix>wsman</p:URLPrefix>'
            '</p:Listener>' % {"enabled": self._get_xml_bool(enabled),
                               "cert_thumbprint": cert_thumbprint})

    def get_auth_config(self):
        data = {}

        data_xml = self._get_resource(self._SERVICE_AUTH_URI)
        tree = ElementTree.fromstring(data_xml)
        for node in tree:
            tag = self._get_node_tag(node.tag)
            value_str = node.text.lower()
            if value_str == "true":
                value = True
            elif value_str == "false":
                value = False
            else:
                value = value_str
            data[tag] = value

        return data

    def set_auth_config(self, basic=None, kerberos=None, negotiate=None,
                        certificate=None, credSSP=None,
                        cbt_hardening_level=None):

        tag_map = {'Basic': basic,
                   'Kerberos': kerberos,
                   'Negotiate': negotiate,
                   'Certificate': certificate,
                   'CredSSP': credSSP,
                   'CbtHardeningLevel': cbt_hardening_level}

        session = self._get_wsman_session()
        data_xml = session.Get(self._SERVICE_AUTH_URI)

        ns = {'cfg':
              'http://schemas.microsoft.com/wbem/wsman/1/config/service/auth'}
        tree = ElementTree.fromstring(data_xml)

        for (tag, value) in tag_map.items():
            if value is not None:
                node = tree.find('.//cfg:%s' % tag, namespaces=ns)

                new_value = self._get_xml_bool(value)
                if node.text.lower() != new_value:
                    node.text = new_value
                    data_xml = ElementTree.tostring(tree)
                    session.Put(self._SERVICE_AUTH_URI, data_xml)

########NEW FILE########
__FILENAME__ = x509
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import copy
import ctypes
import uuid

from ctypes import wintypes

from cloudbaseinit.utils.windows import cryptoapi
from cloudbaseinit.utils import x509constants

malloc = ctypes.cdll.msvcrt.malloc
malloc.restype = ctypes.c_void_p
malloc.argtypes = [ctypes.c_size_t]

free = ctypes.cdll.msvcrt.free
free.restype = None
free.argtypes = [ctypes.c_void_p]

STORE_NAME_MY = "My"
STORE_NAME_ROOT = "Root"
STORE_NAME_TRUSTED_PEOPLE = "TrustedPeople"


class CryptoAPICertManager(object):
    def _get_cert_thumprint(self, cert_context_p):
        thumbprint = None

        try:
            thumprint_len = wintypes.DWORD()

            if not cryptoapi.CertGetCertificateContextProperty(
                    cert_context_p,
                    cryptoapi.CERT_SHA1_HASH_PROP_ID,
                    None, ctypes.byref(thumprint_len)):
                raise cryptoapi.CryptoAPIException()

            thumbprint = malloc(thumprint_len)

            if not cryptoapi.CertGetCertificateContextProperty(
                    cert_context_p,
                    cryptoapi.CERT_SHA1_HASH_PROP_ID,
                    thumbprint, ctypes.byref(thumprint_len)):
                raise cryptoapi.CryptoAPIException()

            thumbprint_ar = ctypes.cast(
                thumbprint,
                ctypes.POINTER(ctypes.c_ubyte *
                               thumprint_len.value)).contents

            thumbprint_str = ""
            for b in thumbprint_ar:
                thumbprint_str += "%02x" % b
            return thumbprint_str
        finally:
            if thumbprint:
                free(thumbprint)

    def _generate_key(self, container_name, machine_keyset):
        crypt_prov_handle = wintypes.HANDLE()
        key_handle = wintypes.HANDLE()

        try:
            flags = 0
            if machine_keyset:
                flags |= cryptoapi.CRYPT_MACHINE_KEYSET

            if not cryptoapi.CryptAcquireContext(
                    ctypes.byref(crypt_prov_handle),
                    container_name,
                    None,
                    cryptoapi.PROV_RSA_FULL,
                    flags):
                flags |= cryptoapi.CRYPT_NEWKEYSET
                if not cryptoapi.CryptAcquireContext(
                        ctypes.byref(crypt_prov_handle),
                        container_name,
                        None,
                        cryptoapi.PROV_RSA_FULL,
                        flags):
                    raise cryptoapi.CryptoAPIException()

            # RSA 2048 bits
            if not cryptoapi.CryptGenKey(crypt_prov_handle,
                                         cryptoapi.AT_SIGNATURE,
                                         0x08000000, key_handle):
                raise cryptoapi.CryptoAPIException()
        finally:
            if key_handle:
                cryptoapi.CryptDestroyKey(key_handle)
            if crypt_prov_handle:
                cryptoapi.CryptReleaseContext(crypt_prov_handle, 0)

    def create_self_signed_cert(self, subject, validity_years=10,
                                machine_keyset=True, store_name=STORE_NAME_MY):
        subject_encoded = None
        cert_context_p = None
        store_handle = None

        container_name = str(uuid.uuid4())
        self._generate_key(container_name, machine_keyset)

        try:
            subject_encoded_len = wintypes.DWORD()

            if not cryptoapi.CertStrToName(cryptoapi.X509_ASN_ENCODING,
                                           subject,
                                           cryptoapi.CERT_X500_NAME_STR, None,
                                           None,
                                           ctypes.byref(subject_encoded_len),
                                           None):
                raise cryptoapi.CryptoAPIException()

            subject_encoded = ctypes.cast(malloc(subject_encoded_len),
                                          ctypes.POINTER(wintypes.BYTE))

            if not cryptoapi.CertStrToName(cryptoapi.X509_ASN_ENCODING,
                                           subject,
                                           cryptoapi.CERT_X500_NAME_STR, None,
                                           subject_encoded,
                                           ctypes.byref(subject_encoded_len),
                                           None):
                raise cryptoapi.CryptoAPIException()

            subject_blob = cryptoapi.CRYPTOAPI_BLOB()
            subject_blob.cbData = subject_encoded_len
            subject_blob.pbData = subject_encoded

            key_prov_info = cryptoapi.CRYPT_KEY_PROV_INFO()
            key_prov_info.pwszContainerName = container_name
            key_prov_info.pwszProvName = None
            key_prov_info.dwProvType = cryptoapi.PROV_RSA_FULL
            key_prov_info.cProvParam = None
            key_prov_info.rgProvParam = None
            key_prov_info.dwKeySpec = cryptoapi.AT_SIGNATURE

            if machine_keyset:
                key_prov_info.dwFlags = cryptoapi.CRYPT_MACHINE_KEYSET
            else:
                key_prov_info.dwFlags = 0

            sign_alg = cryptoapi.CRYPT_ALGORITHM_IDENTIFIER()
            sign_alg.pszObjId = cryptoapi.szOID_RSA_SHA1RSA

            start_time = cryptoapi.SYSTEMTIME()
            cryptoapi.GetSystemTime(ctypes.byref(start_time))

            end_time = copy.copy(start_time)
            end_time.wYear += validity_years

            cert_context_p = cryptoapi.CertCreateSelfSignCertificate(
                None, ctypes.byref(subject_blob), 0,
                ctypes.byref(key_prov_info),
                ctypes.byref(sign_alg), ctypes.byref(start_time),
                ctypes.byref(end_time), None)
            if not cert_context_p:
                raise cryptoapi.CryptoAPIException()

            if not cryptoapi.CertAddEnhancedKeyUsageIdentifier(
                    cert_context_p, cryptoapi.szOID_PKIX_KP_SERVER_AUTH):
                raise cryptoapi.CryptoAPIException()

            if machine_keyset:
                flags = cryptoapi.CERT_SYSTEM_STORE_LOCAL_MACHINE
            else:
                flags = cryptoapi.CERT_SYSTEM_STORE_CURRENT_USER

            store_handle = cryptoapi.CertOpenStore(
                cryptoapi.CERT_STORE_PROV_SYSTEM, 0, 0, flags,
                unicode(store_name))
            if not store_handle:
                raise cryptoapi.CryptoAPIException()

            if not cryptoapi.CertAddCertificateContextToStore(
                    store_handle, cert_context_p,
                    cryptoapi.CERT_STORE_ADD_REPLACE_EXISTING, None):
                raise cryptoapi.CryptoAPIException()

            return self._get_cert_thumprint(cert_context_p)

        finally:
            if store_handle:
                cryptoapi.CertCloseStore(store_handle, 0)
            if cert_context_p:
                cryptoapi.CertFreeCertificateContext(cert_context_p)
            if subject_encoded:
                free(subject_encoded)

    def _get_cert_base64(self, cert_data):
        base64_cert_data = cert_data
        if base64_cert_data.startswith(x509constants.PEM_HEADER):
            base64_cert_data = base64_cert_data[len(x509constants.PEM_HEADER):]
        if base64_cert_data.endswith(x509constants.PEM_FOOTER):
            base64_cert_data = base64_cert_data[:len(base64_cert_data) -
                                                len(x509constants.PEM_FOOTER)]
        return base64_cert_data.replace("\n", "")

    def import_cert(self, cert_data, machine_keyset=True,
                    store_name=STORE_NAME_MY):

        base64_cert_data = self._get_cert_base64(cert_data)

        cert_encoded = None
        store_handle = None
        cert_context_p = None

        try:
            cert_encoded_len = wintypes.DWORD()

            if not cryptoapi.CryptStringToBinaryA(
                    base64_cert_data, len(base64_cert_data),
                    cryptoapi.CRYPT_STRING_BASE64,
                    None, ctypes.byref(cert_encoded_len),
                    None, None):
                raise cryptoapi.CryptoAPIException()

            cert_encoded = ctypes.cast(malloc(cert_encoded_len),
                                       ctypes.POINTER(wintypes.BYTE))

            if not cryptoapi.CryptStringToBinaryA(
                    base64_cert_data, len(base64_cert_data),
                    cryptoapi.CRYPT_STRING_BASE64,
                    cert_encoded, ctypes.byref(cert_encoded_len),
                    None, None):
                raise cryptoapi.CryptoAPIException()

            if machine_keyset:
                flags = cryptoapi.CERT_SYSTEM_STORE_LOCAL_MACHINE
            else:
                flags = cryptoapi.CERT_SYSTEM_STORE_CURRENT_USER

            store_handle = cryptoapi.CertOpenStore(
                cryptoapi.CERT_STORE_PROV_SYSTEM, 0, 0, flags,
                unicode(store_name))
            if not store_handle:
                raise cryptoapi.CryptoAPIException()

            cert_context_p = ctypes.POINTER(cryptoapi.CERT_CONTEXT)()

            if not cryptoapi.CertAddEncodedCertificateToStore(
                    store_handle,
                    cryptoapi.X509_ASN_ENCODING |
                    cryptoapi.PKCS_7_ASN_ENCODING,
                    cert_encoded, cert_encoded_len,
                    cryptoapi.CERT_STORE_ADD_REPLACE_EXISTING,
                    ctypes.byref(cert_context_p)):
                raise cryptoapi.CryptoAPIException()

            # Get the UPN (1.3.6.1.4.1.311.20.2.3 OID) from the
            # certificate subject alt name
            upn = None
            upn_len = cryptoapi.CertGetNameString(
                cert_context_p,
                cryptoapi.CERT_NAME_UPN_TYPE, 0,
                None, None, 0)
            if upn_len > 1:
                upn_ar = ctypes.create_unicode_buffer(upn_len)
                if cryptoapi.CertGetNameString(
                        cert_context_p,
                        cryptoapi.CERT_NAME_UPN_TYPE,
                        0, None, upn_ar, upn_len) != upn_len:
                    raise cryptoapi.CryptoAPIException()
                upn = upn_ar.value

            thumbprint = self._get_cert_thumprint(cert_context_p)
            return (thumbprint, upn)
        finally:
            if cert_context_p:
                cryptoapi.CertFreeCertificateContext(cert_context_p)
            if store_handle:
                cryptoapi.CertCloseStore(store_handle, 0)
            if cert_encoded:
                free(cert_encoded)

########NEW FILE########
__FILENAME__ = x509constants
# Copyright 2014 Cloudbase Solutions Srl
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

PEM_HEADER = "-----BEGIN CERTIFICATE-----"
PEM_FOOTER = "-----END CERTIFICATE-----"

########NEW FILE########
