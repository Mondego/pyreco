__FILENAME__ = app
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
API application handler for Cloudkeep's Barbican
"""
import json

import pecan
from webob import exc as webob_exc

try:
    import newrelic.agent
    newrelic_loaded = True
except ImportError:
    newrelic_loaded = False

from oslo.config import cfg

from barbican.api.controllers import containers
from barbican.api.controllers import orders
from barbican.api.controllers import performance
from barbican.api.controllers import secrets
from barbican.api.controllers import transportkeys
from barbican.api.controllers import versions
from barbican.common import config
from barbican.crypto import extension_manager as ext
from barbican.openstack.common import log
from barbican import queue

if newrelic_loaded:
    newrelic.agent.initialize('/etc/newrelic/newrelic.ini')


class JSONErrorHook(pecan.hooks.PecanHook):

    def on_error(self, state, exc):
        if isinstance(exc, webob_exc.HTTPError):
            exc.body = json.dumps({
                'code': exc.status_int,
                'title': exc.title,
                'description': exc.detail
            })
            return exc.body


class PecanAPI(pecan.Pecan):

    # For performance testing only
    performance_uri = 'mu-1a90dfd0-7e7abba4-4e459908-fc097d60'
    performance_controller = performance.PerformanceController()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('hooks', []).append(JSONErrorHook())
        super(PecanAPI, self).__init__(*args, **kwargs)

    def route(self, req, node, path):
        # Pop the tenant ID from the path
        path = path.split('/')[1:]
        first_path = path.pop(0)

        # Route to the special performance controller
        if first_path == self.performance_uri:
            return self.performance_controller.index, []

        path = '/%s' % '/'.join(path)
        controller, remainder = super(PecanAPI, self).route(req, node, path)

        # Pass the tenant ID as the first argument to the controller
        remainder = list(remainder)
        remainder.insert(0, first_path)
        return controller, remainder


def create_main_app(global_config, **local_conf):
    """uWSGI factory method for the Barbican-API application."""

    # Configure oslo logging and configuration services.
    config.parse_args()
    log.setup('barbican')
    config.setup_remote_pydev_debug()
    # Crypto Plugin Manager
    crypto_mgr = ext.CryptoExtensionManager()

    # Queuing initialization
    CONF = cfg.CONF
    queue.init(CONF)

    class RootController(object):
        secrets = secrets.SecretsController(crypto_mgr)
        orders = orders.OrdersController()
        containers = containers.ContainersController()
        transport_keys = transportkeys.TransportKeysController()

    wsgi_app = PecanAPI(RootController(), force_canonical=False)
    if newrelic_loaded:
        wsgi_app = newrelic.agent.WSGIApplicationWrapper(wsgi_app)
    return wsgi_app


def create_admin_app(global_config, **local_conf):
    config.parse_args()
    wsgi_app = pecan.make_app(versions.VersionController())
    return wsgi_app


create_version_app = create_admin_app

########NEW FILE########
__FILENAME__ = containers
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import pecan

from barbican import api
from barbican.api.controllers import handle_exceptions
from barbican.api.controllers import handle_rbac
from barbican.api.controllers import hrefs
from barbican.common import exception
from barbican.common import resources as res
from barbican.common import utils
from barbican.common import validators
from barbican.model import models
from barbican.model import repositories as repo
from barbican.openstack.common import gettextutils as u

LOG = utils.getLogger(__name__)


def _container_not_found():
    """Throw exception indicating container not found."""
    pecan.abort(404, u._('Not Found. Sorry but your container is in '
                         'another castle.'))


class ContainerController(object):
    """Handles Container entity retrieval and deletion requests."""

    def __init__(self, container_id, tenant_repo=None, container_repo=None):
        self.container_id = container_id
        self.tenant_repo = tenant_repo or repo.TenantRepo()
        self.container_repo = container_repo or repo.ContainerRepo()
        self.validator = validators.ContainerValidator()

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Container retrieval'))
    @handle_rbac('container:get')
    def index(self, keystone_id):
        container = self.container_repo.get(entity_id=self.container_id,
                                            keystone_id=keystone_id,
                                            suppress_exception=True)
        if not container:
            _container_not_found()

        dict_fields = container.to_dict_fields()

        for secret_ref in dict_fields['secret_refs']:
            hrefs.convert_to_hrefs(keystone_id, secret_ref)

        return hrefs.convert_to_hrefs(
            keystone_id,
            hrefs.convert_to_hrefs(keystone_id, dict_fields)
        )

    @index.when(method='DELETE', template='')
    @handle_exceptions(u._('Container deletion'))
    @handle_rbac('container:delete')
    def on_delete(self, keystone_id):

        try:
            self.container_repo.delete_entity_by_id(
                entity_id=self.container_id,
                keystone_id=keystone_id
            )
        except exception.NotFound:
            LOG.exception('Problem deleting container')
            _container_not_found()


class ContainersController(object):
    """Handles Container creation requests."""

    def __init__(self, tenant_repo=None, container_repo=None,
                 secret_repo=None):

        self.tenant_repo = tenant_repo or repo.TenantRepo()
        self.container_repo = container_repo or repo.ContainerRepo()
        self.secret_repo = secret_repo or repo.SecretRepo()
        self.validator = validators.ContainerValidator()

    @pecan.expose()
    def _lookup(self, container_id, *remainder):
        return ContainerController(container_id, self.tenant_repo,
                                   self.container_repo), remainder

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Containers(s) retrieval'))
    @handle_rbac('containers:get')
    def index(self, keystone_id, **kw):
        LOG.debug('Start containers on_get '
                  'for tenant-ID {0}:'.format(keystone_id))

        result = self.container_repo.get_by_create_date(
            keystone_id,
            offset_arg=kw.get('offset', 0),
            limit_arg=kw.get('limit', None),
            suppress_exception=True
        )

        containers, offset, limit, total = result

        if not containers:
            resp_ctrs_overall = {'containers': [], 'total': total}
        else:
            resp_ctrs = [
                hrefs.convert_to_hrefs(keystone_id, c.to_dict_fields())
                for c in containers
            ]
            resp_ctrs_overall = hrefs.add_nav_hrefs('containers',
                                                    keystone_id, offset,
                                                    limit, total,
                                                    {'containers': resp_ctrs})
            resp_ctrs_overall.update({'total': total})

        return resp_ctrs_overall

    @index.when(method='POST', template='json')
    @handle_exceptions(u._('Container creation'))
    @handle_rbac('containers:post')
    def on_post(self, keystone_id):

        tenant = res.get_or_create_tenant(keystone_id, self.tenant_repo)

        data = api.load_body(pecan.request, validator=self.validator)
        LOG.debug('Start on_post...{0}'.format(data))

        new_container = models.Container(data)
        new_container.tenant_id = tenant.id

        #TODO(hgedikli): performance optimizations
        for secret_ref in new_container.container_secrets:
            secret = self.secret_repo.get(entity_id=secret_ref.secret_id,
                                          keystone_id=keystone_id,
                                          suppress_exception=True)
            if not secret:
                pecan.abort(404, u._("Secret provided for '%s'"
                                     " doesn't exist." % secret_ref.name))

        self.container_repo.create_from(new_container)

        pecan.response.status = 202
        pecan.response.headers['Location'] = '/{0}/containers/{1}'.format(
            keystone_id, new_container.id
        )
        url = hrefs.convert_container_to_href(keystone_id, new_container.id)
        return {'container_ref': url}

########NEW FILE########
__FILENAME__ = hrefs
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from barbican.common import utils


def convert_secret_to_href(keystone_id, secret_id):
    """Convert the tenant/secret IDs to a HATEOS-style href."""
    if secret_id:
        resource = 'secrets/' + secret_id
    else:
        resource = 'secrets/????'
    return utils.hostname_for_refs(keystone_id=keystone_id, resource=resource)


def convert_order_to_href(keystone_id, order_id):
    """Convert the tenant/order IDs to a HATEOS-style href."""
    if order_id:
        resource = 'orders/' + order_id
    else:
        resource = 'orders/????'
    return utils.hostname_for_refs(keystone_id=keystone_id, resource=resource)


def convert_container_to_href(keystone_id, container_id):
    """Convert the tenant/container IDs to a HATEOS-style href."""
    if container_id:
        resource = 'containers/' + container_id
    else:
        resource = 'containers/????'
    return utils.hostname_for_refs(keystone_id=keystone_id, resource=resource)


def convert_transport_key_to_href(keystone_id, transport_key_id):
    """Convert the transport key IDs to a HATEOS-style href."""
    if transport_key_id:
        resource = 'transport_keys/' + transport_key_id
    else:
        resource = 'transport_keys/????'
    return utils.hostname_for_refs(keystone_id=keystone_id, resource=resource)


#TODO(hgedikli) handle list of fields in here
def convert_to_hrefs(keystone_id, fields):
    """Convert id's within a fields dict to HATEOS-style hrefs."""
    if 'secret_id' in fields:
        fields['secret_ref'] = convert_secret_to_href(keystone_id,
                                                      fields['secret_id'])
        del fields['secret_id']

    if 'order_id' in fields:
        fields['order_ref'] = convert_order_to_href(keystone_id,
                                                    fields['order_id'])
        del fields['order_id']

    if 'container_id' in fields:
        fields['container_ref'] = \
            convert_container_to_href(keystone_id, fields['container_id'])
        del fields['container_id']

    return fields


def convert_list_to_href(resources_name, keystone_id, offset, limit):
    """Supports pretty output of paged-list hrefs.

    Convert the tenant ID and offset/limit info to a HATEOS-style href
    suitable for use in a list navigation paging interface.
    """
    resource = '{0}?limit={1}&offset={2}'.format(resources_name, limit,
                                                 offset)
    return utils.hostname_for_refs(keystone_id=keystone_id, resource=resource)


def previous_href(resources_name, keystone_id, offset, limit):
    """Supports pretty output of previous-page hrefs.

    Create a HATEOS-style 'previous' href suitable for use in a list
    navigation paging interface, assuming the provided values are the
    currently viewed page.
    """
    offset = max(0, offset - limit)
    return convert_list_to_href(resources_name, keystone_id, offset, limit)


def next_href(resources_name, keystone_id, offset, limit):
    """Supports pretty output of next-page hrefs.

    Create a HATEOS-style 'next' href suitable for use in a list
    navigation paging interface, assuming the provided values are the
    currently viewed page.
    """
    offset = offset + limit
    return convert_list_to_href(resources_name, keystone_id, offset, limit)


def add_nav_hrefs(resources_name, keystone_id, offset, limit,
                  total_elements, data):
    """Adds next and/or previous hrefs to paged list responses.

    :param resources_name: Name of api resource
    :param keystone_id: Keystone id of the tenant
    :param offset: Element number (ie. index) where current page starts
    :param limit: Max amount of elements listed on current page
    :param num_elements: Total number of elements
    :returns: augmented dictionary with next and/or previous hrefs
    """
    if offset > 0:
        data.update({'previous': previous_href(resources_name,
                                               keystone_id,
                                               offset,
                                               limit)})
    if total_elements > (offset + limit):
        data.update({'next': next_href(resources_name,
                                       keystone_id,
                                       offset,
                                       limit)})
    return data

########NEW FILE########
__FILENAME__ = orders
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import pecan

from barbican import api
from barbican.api.controllers import handle_exceptions
from barbican.api.controllers import handle_rbac
from barbican.api.controllers import hrefs
from barbican.common import exception
from barbican.common import resources as res
from barbican.common import utils
from barbican.common import validators
from barbican.model import models
from barbican.model import repositories as repo
from barbican.openstack.common import gettextutils as u
from barbican.queue import client as async_client

LOG = utils.getLogger(__name__)


def _order_not_found():
    """Throw exception indicating order not found."""
    pecan.abort(404, u._('Not Found. Sorry but your order is in '
                         'another castle.'))


def _secret_not_in_order():
    """Throw exception that secret info is not available in the order."""
    pecan.abort(400, u._("Secret metadata expected but not received."))


def _order_update_not_supported():
    """Throw exception that PUT operation is not supported for orders."""
    pecan.abort(405, u._("Order update is not supported."))


class OrderController(object):

    """Handles Order retrieval and deletion requests."""

    def __init__(self, order_id, order_repo=None):
        self.order_id = order_id
        self.repo = order_repo or repo.OrderRepo()

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Order retrieval'))
    @handle_rbac('order:get')
    def index(self, keystone_id):
        order = self.repo.get(entity_id=self.order_id, keystone_id=keystone_id,
                              suppress_exception=True)
        if not order:
            _order_not_found()

        return hrefs.convert_to_hrefs(keystone_id, order.to_dict_fields())

    @index.when(method='PUT')
    @handle_exceptions(u._('Order update'))
    def on_put(self, keystone_id):
        _order_update_not_supported()

    @index.when(method='DELETE')
    @handle_exceptions(u._('Order deletion'))
    @handle_rbac('order:delete')
    def on_delete(self, keystone_id):

        try:
            self.repo.delete_entity_by_id(entity_id=self.order_id,
                                          keystone_id=keystone_id)
        except exception.NotFound:
            LOG.exception('Problem deleting order')
            _order_not_found()


class OrdersController(object):
    """Handles Order requests for Secret creation."""

    def __init__(self, tenant_repo=None, order_repo=None,
                 queue_resource=None):

        LOG.debug('Creating OrdersController')
        self.tenant_repo = tenant_repo or repo.TenantRepo()
        self.order_repo = order_repo or repo.OrderRepo()
        self.queue = queue_resource or async_client.TaskClient()
        self.validator = validators.NewOrderValidator()

    @pecan.expose()
    def _lookup(self, order_id, *remainder):
        return OrderController(order_id, self.order_repo), remainder

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Order(s) retrieval'))
    @handle_rbac('orders:get')
    def index(self, keystone_id, **kw):
        LOG.debug('Start orders on_get '
                  'for tenant-ID {0}:'.format(keystone_id))

        result = self.order_repo \
            .get_by_create_date(keystone_id,
                                offset_arg=kw.get('offset', 0),
                                limit_arg=kw.get('limit', None),
                                suppress_exception=True)
        orders, offset, limit, total = result

        if not orders:
            orders_resp_overall = {'orders': [],
                                   'total': total}
        else:
            orders_resp = [
                hrefs.convert_to_hrefs(keystone_id, o.to_dict_fields())
                for o in orders
            ]
            orders_resp_overall = hrefs.add_nav_hrefs('orders', keystone_id,
                                                      offset, limit, total,
                                                      {'orders': orders_resp})
            orders_resp_overall.update({'total': total})

        return orders_resp_overall

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Order update'))
    @handle_rbac('orders:put')
    def on_put(self, keystone_id):
        _order_update_not_supported()

    @index.when(method='POST', template='json')
    @handle_exceptions(u._('Order creation'))
    @handle_rbac('orders:post')
    def on_post(self, keystone_id):

        tenant = res.get_or_create_tenant(keystone_id, self.tenant_repo)

        body = api.load_body(pecan.request, validator=self.validator)
        LOG.debug('Start on_post...{0}'.format(body))

        if 'secret' not in body:
            _secret_not_in_order()
        secret_info = body['secret']
        name = secret_info.get('name')
        LOG.debug('Secret to create is {0}'.format(name))

        new_order = models.Order()
        new_order.secret_name = secret_info.get('name')
        new_order.secret_algorithm = secret_info.get('algorithm')
        new_order.secret_bit_length = secret_info.get('bit_length', 0)
        new_order.secret_mode = secret_info.get('mode')
        new_order.secret_payload_content_type = secret_info.get(
            'payload_content_type')

        new_order.secret_expiration = secret_info.get('expiration')
        new_order.tenant_id = tenant.id
        self.order_repo.create_from(new_order)

        # Send to workers to process.
        self.queue.process_order(order_id=new_order.id,
                                 keystone_id=keystone_id)

        pecan.response.status = 202
        pecan.response.headers['Location'] = '/{0}/orders/{1}'.format(
            keystone_id, new_order.id
        )
        url = hrefs.convert_order_to_href(keystone_id, new_order.id)
        return {'order_ref': url}

########NEW FILE########
__FILENAME__ = performance
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import pecan

from barbican.common import utils

LOG = utils.getLogger(__name__)


class PerformanceController(object):

    def __init__(self):
        LOG.debug('=== Creating PerformanceController ===')

    @pecan.expose()
    def index(self):
        return '42'

########NEW FILE########
__FILENAME__ = secrets
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import mimetypes
import urllib

import pecan

from barbican import api
from barbican.api.controllers import handle_exceptions
from barbican.api.controllers import handle_rbac
from barbican.api.controllers import hrefs
from barbican.api.controllers import is_json_request_accept
from barbican.common import exception
from barbican.common import resources as res
from barbican.common import utils
from barbican.common import validators
from barbican.crypto import mime_types
from barbican.model import repositories as repo
from barbican.openstack.common import gettextutils as u

LOG = utils.getLogger(__name__)


def allow_all_content_types(f):
    cfg = pecan.util._cfg(f)
    for value in mimetypes.types_map.values():
        cfg.setdefault('content_types', {})[value] = ''
    return f


def _secret_not_found():
    """Throw exception indicating secret not found."""
    pecan.abort(404, u._('Not Found. Sorry but your secret is in '
                         'another castle.'))


def _secret_already_has_data():
    """Throw exception that the secret already has data."""
    pecan.abort(409, u._("Secret already has data, cannot modify it."))


class SecretController(object):
    """Handles Secret retrieval and deletion requests."""

    def __init__(self, secret_id, crypto_manager,
                 tenant_repo=None, secret_repo=None, datum_repo=None,
                 kek_repo=None):
        LOG.debug('=== Creating SecretController ===')
        self.secret_id = secret_id
        self.crypto_manager = crypto_manager
        self.tenant_repo = tenant_repo or repo.TenantRepo()
        self.repo = secret_repo or repo.SecretRepo()
        self.datum_repo = datum_repo or repo.EncryptedDatumRepo()
        self.kek_repo = kek_repo or repo.KEKDatumRepo()

    @pecan.expose(generic=True)
    @allow_all_content_types
    @handle_exceptions(u._('Secret retrieval'))
    @handle_rbac('secret:get')
    def index(self, keystone_id):

        secret = self.repo.get(entity_id=self.secret_id,
                               keystone_id=keystone_id,
                               suppress_exception=True)
        if not secret:
            _secret_not_found()

        if is_json_request_accept(pecan.request):
            # Metadata-only response, no decryption necessary.
            pecan.override_template('json', 'application/json')
            secret_fields = mime_types.augment_fields_with_content_types(
                secret)
            return hrefs.convert_to_hrefs(keystone_id, secret_fields)
        else:
            tenant = res.get_or_create_tenant(keystone_id, self.tenant_repo)
            pecan.override_template('', pecan.request.accept.header_value)
            return self.crypto_manager.decrypt(
                pecan.request.accept.header_value,
                secret,
                tenant
            )

    @index.when(method='PUT')
    @allow_all_content_types
    @handle_exceptions(u._('Secret update'))
    @handle_rbac('secret:put')
    def on_put(self, keystone_id):

        if not pecan.request.content_type or \
                pecan.request.content_type == 'application/json':
            pecan.abort(
                415,
                u._("Content-Type of '{0}' is not supported for PUT.").format(
                    pecan.request.content_type
                )
            )

        secret = self.repo.get(entity_id=self.secret_id,
                               keystone_id=keystone_id,
                               suppress_exception=True)
        if not secret:
            _secret_not_found()

        if secret.encrypted_data:
            _secret_already_has_data()

        tenant = res.get_or_create_tenant(keystone_id, self.tenant_repo)
        content_type = pecan.request.content_type
        content_encoding = pecan.request.headers.get('Content-Encoding')

        res.create_encrypted_datum(secret,
                                   pecan.request.body,
                                   content_type,
                                   content_encoding,
                                   tenant,
                                   self.crypto_manager,
                                   self.datum_repo,
                                   self.kek_repo)

    @index.when(method='DELETE')
    @handle_exceptions(u._('Secret deletion'))
    @handle_rbac('secret:delete')
    def on_delete(self, keystone_id):

        try:
            self.repo.delete_entity_by_id(entity_id=self.secret_id,
                                          keystone_id=keystone_id)
        except exception.NotFound:
            LOG.exception('Problem deleting secret')
            _secret_not_found()


class SecretsController(object):
    """Handles Secret creation requests."""

    def __init__(self, crypto_manager,
                 tenant_repo=None, secret_repo=None,
                 tenant_secret_repo=None, datum_repo=None, kek_repo=None):
        LOG.debug('Creating SecretsController')
        self.tenant_repo = tenant_repo or repo.TenantRepo()
        self.secret_repo = secret_repo or repo.SecretRepo()
        self.tenant_secret_repo = tenant_secret_repo or repo.TenantSecretRepo()
        self.datum_repo = datum_repo or repo.EncryptedDatumRepo()
        self.kek_repo = kek_repo or repo.KEKDatumRepo()
        self.crypto_manager = crypto_manager
        self.validator = validators.NewSecretValidator()

    @pecan.expose()
    def _lookup(self, secret_id, *remainder):
        return SecretController(secret_id, self.crypto_manager,
                                self.tenant_repo, self.secret_repo,
                                self.datum_repo, self.kek_repo), remainder

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Secret(s) retrieval'))
    @handle_rbac('secrets:get')
    def index(self, keystone_id, **kw):
        LOG.debug('Start secrets on_get '
                  'for tenant-ID {0}:'.format(keystone_id))

        name = kw.get('name', '')
        if name:
            name = urllib.unquote_plus(name)

        bits = kw.get('bits', 0)
        try:
            bits = int(bits)
        except ValueError:
            # as per Github issue 171, if bits is invalid then
            # the default should be used.
            bits = 0

        result = self.secret_repo.get_by_create_date(
            keystone_id,
            offset_arg=kw.get('offset', 0),
            limit_arg=kw.get('limit', None),
            name=name,
            alg=kw.get('alg'),
            mode=kw.get('mode'),
            bits=bits,
            suppress_exception=True
        )

        secrets, offset, limit, total = result

        if not secrets:
            secrets_resp_overall = {'secrets': [],
                                    'total': total}
        else:
            secret_fields = lambda s: mime_types\
                .augment_fields_with_content_types(s)
            secrets_resp = [
                hrefs.convert_to_hrefs(keystone_id, secret_fields(s))
                for s in secrets
            ]
            secrets_resp_overall = hrefs.add_nav_hrefs(
                'secrets', keystone_id, offset, limit, total,
                {'secrets': secrets_resp}
            )
            secrets_resp_overall.update({'total': total})

        return secrets_resp_overall

    @index.when(method='POST', template='json')
    @handle_exceptions(u._('Secret creation'))
    @handle_rbac('secrets:post')
    def on_post(self, keystone_id):
        LOG.debug('Start on_post for tenant-ID {0}:...'.format(keystone_id))

        data = api.load_body(pecan.request, validator=self.validator)
        tenant = res.get_or_create_tenant(keystone_id, self.tenant_repo)

        new_secret = res.create_secret(data, tenant, self.crypto_manager,
                                       self.secret_repo,
                                       self.tenant_secret_repo,
                                       self.datum_repo,
                                       self.kek_repo)

        pecan.response.status = 201
        pecan.response.headers['Location'] = '/{0}/secrets/{1}'.format(
            keystone_id, new_secret.id
        )
        url = hrefs.convert_secret_to_href(keystone_id, new_secret.id)
        LOG.debug('URI to secret is {0}'.format(url))
        return {'secret_ref': url}

########NEW FILE########
__FILENAME__ = transportkeys
# Copyright (c) 2014 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import urllib

import pecan

from barbican import api
from barbican.api.controllers import handle_exceptions
from barbican.api.controllers import handle_rbac
from barbican.api.controllers import hrefs
from barbican.common import exception
from barbican.common import utils
from barbican.common import validators
from barbican.model import models
from barbican.model import repositories as repo
from barbican.openstack.common import gettextutils as u

LOG = utils.getLogger(__name__)


def _transport_key_not_found():
    """Throw exception indicating transport key not found."""
    pecan.abort(404, u._('Not Found. Transport Key not found.'))


class TransportKeyController(object):
    """Handles transport key retrieval requests."""

    def __init__(self, transport_key_id, transport_key_repo=None):
        LOG.debug('=== Creating TransportKeyController ===')
        self.transport_key_id = transport_key_id
        self.repo = transport_key_repo or repo.TransportKeyRepo()

    @pecan.expose(generic=True)
    @handle_exceptions(u._('Transport Key retrieval'))
    @handle_rbac('transport_key:get')
    def index(self, keystone_id):
        LOG.debug("== Getting transport key for %s" % keystone_id)
        transport_key = self.repo.get(entity_id=self.transport_key_id)
        if not transport_key:
            _transport_key_not_found()

        pecan.override_template('json', 'application/json')
        return transport_key

    @index.when(method='DELETE')
    @handle_exceptions(u._('Transport Key deletion'))
    @handle_rbac('transport_key:delete')
    def on_delete(self, keystone_id):
        LOG.debug("== Deleting transport key ===")
        try:
            self.repo.delete_entity_by_id(entity_id=self.transport_key_id,
                                          keystone_id=keystone_id)
            # TODO(alee) response should be 204 on success
            # pecan.response.status = 204
        except exception.NotFound:
            LOG.exception('Problem deleting transport_key')
            _transport_key_not_found()


class TransportKeysController(object):
    """Handles transport key list requests."""

    def __init__(self, transport_key_repo=None):
        LOG.debug('Creating TransportKeyController')
        self.repo = transport_key_repo or repo.TransportKeyRepo()
        self.validator = validators.NewTransportKeyValidator()

    @pecan.expose()
    def _lookup(self, transport_key_id, *remainder):
        return TransportKeyController(transport_key_id, self.repo), remainder

    @pecan.expose(generic=True, template='json')
    @handle_exceptions(u._('Transport Key(s) retrieval'))
    @handle_rbac('transport_keys:get')
    def index(self, keystone_id, **kw):
        LOG.debug('Start transport_keys on_get')

        plugin_name = kw.get('plugin_name', None)
        if plugin_name is not None:
            plugin_name = urllib.unquote_plus(plugin_name)

        result = self.repo.get_by_create_date(
            plugin_name=plugin_name,
            offset_arg=kw.get('offset', 0),
            limit_arg=kw.get('limit', None),
            suppress_exception=True
        )

        transport_keys, offset, limit, total = result

        if not transport_keys:
            transport_keys_resp_overall = {'transport_keys': [],
                                           'total': total}
        else:
            transport_keys_resp = [
                hrefs.convert_transport_key_to_href(keystone_id, s.id)
                for s in transport_keys
            ]
            transport_keys_resp_overall = hrefs.add_nav_hrefs(
                'transport_keys', keystone_id, offset, limit, total,
                {'transport_keys': transport_keys_resp}
            )
            transport_keys_resp_overall.update({'total': total})

        return transport_keys_resp_overall

    @index.when(method='POST', template='json')
    @handle_exceptions(u._('Transport Key Creation'))
    @handle_rbac('transport_keys:post')
    def on_post(self, keystone_id):
        LOG.debug('Start transport_keys on_post')

        # TODO(alee) POST should determine the plugin name and call the
        # relevant get_transport_key() call.  We will implement this once
        # we figure out how the plugins will be enumerated.

        data = api.load_body(pecan.request, validator=self.validator)

        new_key = models.TransportKey(data.get('plugin_name'),
                                      data.get('transport_key'))

        self.repo.create_from(new_key)

        pecan.response.status = 201
        pecan.response.headers['Location'] = '/{0}/transport_keys/{1}'.format(
            keystone_id, new_key.id
        )
        url = hrefs.convert_transport_key_to_href(keystone_id, new_key.id)
        LOG.debug('URI to transport key is {0}'.format(url))
        return {'transport_key_ref': url}

########NEW FILE########
__FILENAME__ = versions
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import pecan

from barbican.api.controllers import handle_exceptions
from barbican.api.controllers import handle_rbac
from barbican.common import utils
from barbican.openstack.common import gettextutils as u
from barbican import version

LOG = utils.getLogger(__name__)


class VersionController(object):

    def __init__(self):
        LOG.debug('=== Creating VersionController ===')

    @pecan.expose('json')
    @handle_exceptions(u._('Version retrieval'))
    @handle_rbac('version:get')
    def index(self):
        return {
            'v1': 'current',
            'build': version.__version__
        }

########NEW FILE########
__FILENAME__ = context
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011-2012 OpenStack LLC.
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

import json
import webob.exc

from oslo.config import cfg

from barbican.api import middleware as mw
from barbican.common import utils
import barbican.context
from barbican.openstack.common import gettextutils as u
from barbican.openstack.common import policy

LOG = utils.getLogger(__name__)

# TODO(jwood) Need to figure out why config is ignored in this module.
context_opts = [
    cfg.BoolOpt('owner_is_tenant', default=True,
                help=u._('When true, this option sets the owner of an image '
                         'to be the tenant. Otherwise, the owner of the '
                         ' image will be the authenticated user issuing the '
                         'request.')),
    cfg.StrOpt('admin_role', default='admin',
               help=u._('Role used to identify an authenticated user as '
                        'administrator.')),
    cfg.BoolOpt('allow_anonymous_access', default=False,
                help=u._('Allow unauthenticated users to access the API with '
                         'read-only privileges. This only applies when using '
                         'ContextMiddleware.')),
]


CONF = cfg.CONF
CONF.register_opts(context_opts)


# TODO(jwood): I'd like to get the utils.getLogger(...) working instead:
#  LOG = logging.getLogger(__name__)


class BaseContextMiddleware(mw.Middleware):
    def process_response(self, resp):
        try:
            request_id = resp.request.context.request_id
        except AttributeError:
            LOG.warn(u._('Unable to retrieve request id from context'))
        else:
            resp.headers['x-openstack-request-id'] = 'req-%s' % request_id
        return resp


class ContextMiddleware(BaseContextMiddleware):
    def __init__(self, app):
        self.policy_enforcer = policy.Enforcer()
        super(ContextMiddleware, self).__init__(app)

    def process_request(self, req):
        """Convert authentication information into a request context

        Generate a barbican.context.RequestContext object from the available
        authentication headers and store on the 'context' attribute
        of the req object.

        :param req: wsgi request object that will be given the context object
        :raises webob.exc.HTTPUnauthorized: when value of the X-Identity-Status
                                            header is not 'Confirmed' and
                                            anonymous access is disallowed
        """
        if req.headers.get('X-Identity-Status') == 'Confirmed':
            req.context = self._get_authenticated_context(req)
            LOG.debug("==== Inserted barbican auth "
                      "request context: %s ====" % (req.context.to_dict()))
        elif CONF.allow_anonymous_access:
            req.context = self._get_anonymous_context()
            LOG.debug("==== Inserted barbican unauth "
                      "request context: %s ====" % (req.context.to_dict()))
        else:
            raise webob.exc.HTTPUnauthorized()

        # Ensure that down wind mw.Middleware/app can see this context.
        req.environ['barbican.context'] = req.context

    def _get_anonymous_context(self):
        kwargs = {
            'user': None,
            'tenant': None,
            'roles': [],
            'is_admin': False,
            'read_only': True,
            'policy_enforcer': self.policy_enforcer,
        }
        return barbican.context.RequestContext(**kwargs)

    def _get_authenticated_context(self, req):
        #NOTE(bcwaldon): X-Roles is a csv string, but we need to parse
        # it into a list to be useful
        roles_header = req.headers.get('X-Roles', '')
        roles = [r.strip().lower() for r in roles_header.split(',')]

        #NOTE(bcwaldon): This header is deprecated in favor of X-Auth-Token
        #(mkbhanda) keeping this just-in-case for swift
        deprecated_token = req.headers.get('X-Storage-Token')

        service_catalog = None
        if req.headers.get('X-Service-Catalog') is not None:
            try:
                catalog_header = req.headers.get('X-Service-Catalog')
                service_catalog = json.loads(catalog_header)
            except ValueError:
                raise webob.exc.HTTPInternalServerError(
                    u._('Invalid service catalog json.'))

        kwargs = {
            'user': req.headers.get('X-User-Id'),
            'tenant': req.headers.get('X-Tenant-Id'),
            'roles': roles,
            'is_admin': CONF.admin_role.strip().lower() in roles,
            'auth_tok': req.headers.get('X-Auth-Token', deprecated_token),
            'owner_is_tenant': CONF.owner_is_tenant,
            'service_catalog': service_catalog,
            'policy_enforcer': self.policy_enforcer,
        }

        return barbican.context.RequestContext(**kwargs)


class UnauthenticatedContextMiddleware(BaseContextMiddleware):
    def process_request(self, req):
        """Create a context without an authorized user."""
        kwargs = {
            'user': None,
            'tenant': None,
            'roles': [],
            'is_admin': True,
        }

        req.context = barbican.context.RequestContext(**kwargs)

########NEW FILE########
__FILENAME__ = simple
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
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
A filter middleware that just outputs to logs, for instructive/sample
purposes only.
"""

from oslo.config import cfg

from barbican.api.middleware import Middleware
from barbican.common import utils

LOG = utils.getLogger(__name__)
CONF = cfg.CONF


class SimpleFilter(Middleware):

    def __init__(self, app):
        super(SimpleFilter, self).__init__(app)

    def process_request(self, req):
        """Just announce we have been called."""
        LOG.debug("Calling SimpleFilter")
        return None

########NEW FILE########
__FILENAME__ = config
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Configuration setup for Barbican.
"""

import logging
import logging.config
import logging.handlers
import os
import sys

from oslo.config import cfg

from barbican.openstack.common.gettextutils import _
from barbican.version import __version__

CONF = cfg.CONF
CONF.import_opt('verbose', 'barbican.openstack.common.log')
CONF.import_opt('debug', 'barbican.openstack.common.log')
CONF.import_opt('log_dir', 'barbican.openstack.common.log')
CONF.import_opt('log_file', 'barbican.openstack.common.log')
CONF.import_opt('log_config_append', 'barbican.openstack.common.log')
CONF.import_opt('log_format', 'barbican.openstack.common.log')
CONF.import_opt('log_date_format', 'barbican.openstack.common.log')
CONF.import_opt('use_syslog', 'barbican.openstack.common.log')
CONF.import_opt('syslog_log_facility', 'barbican.openstack.common.log')

LOG = logging.getLogger(__name__)


def parse_args(args=None, usage=None, default_config_files=None):
    CONF(args=args,
         project='barbican',
         prog='barbican-api',
         version=__version__,
         usage=usage,
         default_config_files=default_config_files)

    CONF.pydev_debug_host = os.environ.get('PYDEV_DEBUG_HOST')
    CONF.pydev_debug_port = os.environ.get('PYDEV_DEBUG_PORT')


def setup_logging():
    """Sets up the logging options."""

    if CONF.log_config_append:
        # Use a logging configuration file for all settings...
        if os.path.exists(CONF.log_config_append):
            logging.config.fileConfig(CONF.log_config_append)
            return
        else:
            raise RuntimeError("Unable to locate specified logging "
                               "config file: %s" % CONF.log_config_append)

    root_logger = logging.root
    if CONF.debug:
        root_logger.setLevel(logging.DEBUG)
    elif CONF.verbose:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.WARNING)

    formatter = logging.Formatter(CONF.log_format, CONF.log_date_format)

    if CONF.use_syslog:
        try:
            facility = getattr(logging.handlers.SysLogHandler,
                               CONF.syslog_log_facility)
        except AttributeError:
            raise ValueError(_("Invalid syslog facility"))

        handler = logging.handlers.SysLogHandler(address='/dev/log',
                                                 facility=facility)
    elif CONF.log_file:
        logfile = CONF.log_file
        if CONF.log_dir:
            logfile = os.path.join(CONF.log_dir, logfile)
        handler = logging.handlers.WatchedFileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def setup_remote_pydev_debug():
    """Required setup for remote debugging."""

    if CONF.pydev_debug_host and CONF.pydev_debug_port:
        try:
            try:
                from pydev import pydevd
            except ImportError:
                import pydevd

            pydevd.settrace(CONF.pydev_debug_host,
                            port=int(CONF.pydev_debug_port),
                            stdoutToServer=True,
                            stderrToServer=True)
        except Exception:
            LOG.exception('Unable to join debugger, please '
                          'make sure that the debugger processes is '
                          'listening on debug-host \'%s\' debug-port \'%s\'.',
                          CONF.pydev_debug_host, CONF.pydev_debug_port)
            raise

########NEW FILE########
__FILENAME__ = exception
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Barbican exception subclasses
"""

import urlparse

from barbican.openstack.common.gettextutils import _

_FATAL_EXCEPTION_FORMAT_ERRORS = False


class RedirectException(Exception):
    def __init__(self, url):
        self.url = urlparse.urlparse(url)


class BarbicanException(Exception):
    """Base Barbican Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred")

    def __init__(self, message=None, *args, **kwargs):
        if not message:
            message = self.message
        try:
            message = message % kwargs
        except Exception as e:
            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise e
            else:
                # at least get the core message out if something happened
                pass
        super(BarbicanException, self).__init__(message)


class MissingArgumentError(BarbicanException):
    message = _("Missing required argument.")


class MissingCredentialError(BarbicanException):
    message = _("Missing required credential: %(required)s")


class BadAuthStrategy(BarbicanException):
    message = _("Incorrect auth strategy, expected \"%(expected)s\" but "
                "received \"%(received)s\"")


class NotFound(BarbicanException):
    message = _("An object with the specified identifier was not found.")


class UnknownScheme(BarbicanException):
    message = _("Unknown scheme '%(scheme)s' found in URI")


class BadStoreUri(BarbicanException):
    message = _("The Store URI was malformed.")


class Duplicate(BarbicanException):
    message = _("An object with the same identifier already exists.")


class StorageFull(BarbicanException):
    message = _("There is not enough disk space on the image storage media.")


class StorageWriteDenied(BarbicanException):
    message = _("Permission to write image storage media denied.")


class AuthBadRequest(BarbicanException):
    message = _("Connect error/bad request to Auth service at URL %(url)s.")


class AuthUrlNotFound(BarbicanException):
    message = _("Auth service at URL %(url)s not found.")


class AuthorizationFailure(BarbicanException):
    message = _("Authorization failed.")


class NotAuthenticated(BarbicanException):
    message = _("You are not authenticated.")


class Forbidden(BarbicanException):
    message = _("You are not authorized to complete this action.")


class NotSupported(BarbicanException):
    message = _("Operation is not supported.")


class ForbiddenPublicImage(Forbidden):
    message = _("You are not authorized to complete this action.")


class ProtectedImageDelete(Forbidden):
    message = _("Image %(image_id)s is protected and cannot be deleted.")


#NOTE(bcwaldon): here for backwards-compatibility, need to deprecate.
class NotAuthorized(Forbidden):
    message = _("You are not authorized to complete this action.")


class Invalid(BarbicanException):
    message = _("Data supplied was not valid.")


class NoDataToProcess(BarbicanException):
    message = _("No data supplied to process.")


class InvalidSortKey(Invalid):
    message = _("Sort key supplied was not valid.")


class InvalidFilterRangeValue(Invalid):
    message = _("Unable to filter using the specified range.")


class ReadonlyProperty(Forbidden):
    message = _("Attribute '%(property)s' is read-only.")


class ReservedProperty(Forbidden):
    message = _("Attribute '%(property)s' is reserved.")


class AuthorizationRedirect(BarbicanException):
    message = _("Redirecting to %(uri)s for authorization.")


class DatabaseMigrationError(BarbicanException):
    message = _("There was an error migrating the database.")


class ClientConnectionError(BarbicanException):
    message = _("There was an error connecting to a server")


class ClientConfigurationError(BarbicanException):
    message = _("There was an error configuring the client.")


class MultipleChoices(BarbicanException):
    message = _("The request returned a 302 Multiple Choices. This generally "
                "means that you have not included a version indicator in a "
                "request URI.\n\nThe body of response returned:\n%(body)s")


class LimitExceeded(BarbicanException):
    message = _("The request returned a 413 Request Entity Too Large. This "
                "generally means that rate limiting or a quota threshold was "
                "breached.\n\nThe response body:\n%(body)s")

    def __init__(self, *args, **kwargs):
        super(LimitExceeded, self).__init__(*args, **kwargs)
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)


class ServiceUnavailable(BarbicanException):
    message = _("The request returned 503 Service Unavilable. This "
                "generally occurs on service overload or other transient "
                "outage.")

    def __init__(self, *args, **kwargs):
        super(ServiceUnavailable, self).__init__(*args, **kwargs)
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)


class ServerError(BarbicanException):
    message = _("The request returned 500 Internal Server Error.")


class UnexpectedStatus(BarbicanException):
    message = _("The request returned an unexpected status: %(status)s."
                "\n\nThe response body:\n%(body)s")


class InvalidContentType(BarbicanException):
    message = _("Invalid content type %(content_type)s")


class InvalidContentEncoding(BarbicanException):
    message = _("Invalid content encoding %(content_encoding)s")


class PayloadDecodingError(BarbicanException):
    message = _("Error while attempting to decode payload.")


class BadRegistryConnectionConfiguration(BarbicanException):
    message = _("Registry was not configured correctly on API server. "
                "Reason: %(reason)s")


class BadStoreConfiguration(BarbicanException):
    message = _("Store %(store_name)s could not be configured correctly. "
                "Reason: %(reason)s")


class BadDriverConfiguration(BarbicanException):
    message = _("Driver %(driver_name)s could not be configured correctly. "
                "Reason: %(reason)s")


class StoreDeleteNotSupported(BarbicanException):
    message = _("Deleting images from this store is not supported.")


class StoreAddDisabled(BarbicanException):
    message = _("Configuration for store failed. Adding images to this "
                "store is disabled.")


class InvalidNotifierStrategy(BarbicanException):
    message = _("'%(strategy)s' is not an available notifier strategy.")


class MaxRedirectsExceeded(BarbicanException):
    message = _("Maximum redirects (%(redirects)s) was exceeded.")


class InvalidRedirect(BarbicanException):
    message = _("Received invalid HTTP redirect.")


class NoServiceEndpoint(BarbicanException):
    message = _("Response from Keystone does not contain a Barbican endpoint.")


class RegionAmbiguity(BarbicanException):
    message = _("Multiple 'image' service matches for region %(region)s. This "
                "generally means that a region is required and you have not "
                "supplied one.")


class WorkerCreationFailure(BarbicanException):
    message = _("Server worker creation failed: %(reason)s.")


class SchemaLoadError(BarbicanException):
    message = _("Unable to load schema: %(reason)s")


class InvalidObject(BarbicanException):
    message = _("Provided object does not match schema "
                "'%(schema)s': %(reason)s")

    def __init__(self, *args, **kwargs):
        super(InvalidObject, self).__init__(*args, **kwargs)
        self.invalid_property = kwargs.get('property')


class UnsupportedField(BarbicanException):
    message = _("No support for value set on field '%(field)s' on "
                "schema '%(schema)s': %(reason)s")

    def __init__(self, *args, **kwargs):
        super(UnsupportedField, self).__init__(*args, **kwargs)
        self.invalid_field = kwargs.get('field')


class UnsupportedHeaderFeature(BarbicanException):
    message = _("Provided header feature is unsupported: %(feature)s")


class InUseByStore(BarbicanException):
    message = _("The image cannot be deleted because it is in use through "
                "the backend store outside of Barbican.")


class ImageSizeLimitExceeded(BarbicanException):
    message = _("The provided image is too large.")

########NEW FILE########
__FILENAME__ = resources
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Shared business logic.
"""
from barbican.common import exception
from barbican.common import utils
from barbican.common import validators
from barbican.model import models


LOG = utils.getLogger(__name__)


def get_or_create_tenant(keystone_id, tenant_repo):
    """Returns tenant with matching keystone_id.

    Creates it if it does not exist.
    :param keystone_id: The external-to-Barbican ID for this tenant.
    :param tenant_repo: Tenant repository.
    :return: Tenant model instance
    """
    tenant = tenant_repo.find_by_keystone_id(keystone_id,
                                             suppress_exception=True)
    if not tenant:
        LOG.debug('Creating tenant for {0}'.format(keystone_id))
        tenant = models.Tenant()
        tenant.keystone_id = keystone_id
        tenant.status = models.States.ACTIVE
        tenant_repo.create_from(tenant)
    return tenant


def create_secret(data, tenant, crypto_manager,
                  secret_repo, tenant_secret_repo, datum_repo, kek_repo,
                  ok_to_generate=False):
    """Common business logic to create a secret."""
    time_keeper = utils.TimeKeeper('Create Secret Resource')
    new_secret = models.Secret(data)
    time_keeper.mark('after Secret model create')
    new_datum = None
    content_type = data.get('payload_content_type',
                            'application/octet-stream')

    if 'payload' in data:
        payload = data.get('payload')
        content_encoding = data.get('payload_content_encoding')

        LOG.debug('Encrypting payload...')
        new_datum = crypto_manager.encrypt(payload,
                                           content_type,
                                           content_encoding,
                                           new_secret,
                                           tenant,
                                           kek_repo,
                                           enforce_text_only=True)
        time_keeper.mark('after encrypt')

    elif ok_to_generate:
        LOG.debug('Generating new secret...')
        # TODO(atiwari): With new typed Order API proposal
        # we need to translate new_secret to meta
        # currently it is working as meta will have same attributes
        new_datum = crypto_manager. \
            generate_symmetric_encryption_key(new_secret,
                                              content_type,
                                              tenant,
                                              kek_repo)
        time_keeper.mark('after secret generate')

    else:
        LOG.debug('Creating metadata only for the new secret. '
                  'A subsequent PUT is required')

    # Create Secret entities in datastore.
    secret_repo.create_from(new_secret)
    time_keeper.mark('after Secret datastore create')
    new_assoc = models.TenantSecret()
    time_keeper.mark('after TenantSecret model create')
    new_assoc.tenant_id = tenant.id
    new_assoc.secret_id = new_secret.id
    new_assoc.role = "admin"
    new_assoc.status = models.States.ACTIVE
    tenant_secret_repo.create_from(new_assoc)
    time_keeper.mark('after TenantSecret datastore create')
    if new_datum:
        new_datum.secret_id = new_secret.id
        datum_repo.create_from(new_datum)
        time_keeper.mark('after Datum datastore create')

    time_keeper.dump()

    return new_secret


def create_encrypted_datum(secret, payload,
                           content_type, content_encoding,
                           tenant, crypto_manager, datum_repo, kek_repo):
    """Modifies the secret to add the plain_text secret information.

    :param secret: the secret entity to associate the secret data to
    :param payload: secret data to store
    :param content_type: payload content mime type
    :param content_encoding: payload content encoding
    :param tenant: the tenant (entity) who owns the secret
    :param crypto_manager: the crypto plugin manager
    :param datum_repo: the encrypted datum repository
    :param kek_repo: the KEK metadata repository
    :retval The response body, None if N/A
    """
    if not payload:
        raise exception.NoDataToProcess()

    if validators.secret_too_big(payload):
        raise exception.LimitExceeded()

    if secret.encrypted_data:
        raise ValueError('Secret already has encrypted data stored for it.')

    # Encrypt payload
    LOG.debug('Encrypting secret payload...')
    new_datum = crypto_manager.encrypt(payload,
                                       content_type,
                                       content_encoding,
                                       secret,
                                       tenant,
                                       kek_repo)
    datum_repo.create_from(new_datum)

    return new_datum

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Common utilities for Barbican.
"""

import time
import uuid

from oslo.config import cfg

import barbican.openstack.common.log as logging


host_opts = [
    cfg.StrOpt('host_href', default='http://localhost:9311'),
]

CONF = cfg.CONF
CONF.register_opts(host_opts)


# Current API version
API_VERSION = 'v1'


def hostname_for_refs(keystone_id=None, resource=None):
    """Return the HATEOS-style return URI reference for this service."""
    ref = ['{0}/{1}'.format(CONF.host_href, API_VERSION)]
    if not keystone_id:
        return ref[0]
    ref.append('/' + keystone_id)
    if resource:
        ref.append('/' + resource)
    return ''.join(ref)


# Return a logger instance.
#   Note: Centralize access to the logger to avoid the dreaded
#   'ArgsAlreadyParsedError: arguments already parsed: cannot
#   register CLI option'
#   error.
def getLogger(name):
    return logging.getLogger(name)


def get_accepted_encodings(req):
    """Returns a list of client acceptable encodings sorted by q value.

    For details see: http://tools.ietf.org/html/rfc2616#section-14.3

    :param req: request object
    :returns: list of client acceptable encodings sorted by q value.
    """
    header = req.get_header('Accept-Encoding')

    return get_accepted_encodings_direct(header)


def get_accepted_encodings_direct(content_encoding_header):
    """Returns a list of client acceptable encodings sorted by q value.

    For details see: http://tools.ietf.org/html/rfc2616#section-14.3

    :param req: request object
    :returns: list of client acceptable encodings sorted by q value.
    """
    if content_encoding_header is None:
        return None

    encodings = list()
    for enc in content_encoding_header.split(','):
        if ';' in enc:
            encoding, q = enc.split(';')
            try:
                q = q.split('=')[1]
                quality = float(q.strip())
            except ValueError:
                # can't convert quality to float
                return None
            if quality > 1.0 or quality < 0.0:
                # quality is outside valid range
                return None
            if quality > 0.0:
                encodings.append((encoding.strip(), quality))
        else:
            encodings.append((enc.strip(), 1))

    return [enc[0] for enc in sorted(encodings,
                                     cmp=lambda a, b: cmp(b[1], a[1]))]


def generate_fullname_for(o):
    """Produce a fully qualified class name for the specified instance.

    :param o: The instance to generate information from.
    :return: A string providing the package.module information for the
    instance.
    """
    if not o:
        return 'None'

    module = o.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return o.__class__.__name__
    return module + '.' + o.__class__.__name__


class TimeKeeper(object):
    """Keeps track of elapsed times and then allows for dumping a summary to
    logs. This class can be used to profile a method as a fine grain level.
    """

    def __init__(self, name, logger=None):
        self.logger = logger or getLogger(__name__)
        self.name = name
        self.time_start = time.time()
        self.time_last = self.time_start
        self.elapsed = []

    def mark(self, note=None):
        """Mark a moment in time, with an optional note as to what is
        occurring at the time.
        :param note: Optional note
        """
        time_curr = time.time()
        self.elapsed.append((time_curr, time_curr - self.time_last, note))
        self.time_last = time_curr

    def dump(self):
        """Dump the elapsed time(s) to log."""
        self.logger.debug("Timing output for '{0}'".format(self.name))
        for timec, timed, note in self.elapsed:
            self.logger.debug("    time current/elapsed/notes:"
                              "{0:.3f}/{1:.0f}/{2}".format(timec,
                                                           timed * 1000.,
                                                           note))
        time_current = time.time()
        total_elapsed = time_current - self.time_start
        self.logger.debug("    Final time/elapsed:"
                          "{0:.3f}/{1:.0f}".format(time_current,
                                                   total_elapsed * 1000.))


def generate_uuid():
    return str(uuid.uuid4())

########NEW FILE########
__FILENAME__ = validators
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
"""
API JSON validators.
"""

import abc

import jsonschema as schema
from oslo.config import cfg
import six

from barbican.common import exception
from barbican.common import utils
from barbican.crypto import mime_types
from barbican.openstack.common.gettextutils import _
from barbican.openstack.common import timeutils


LOG = utils.getLogger(__name__)
DEFAULT_MAX_SECRET_BYTES = 10000
common_opts = [
    cfg.IntOpt('max_allowed_secret_in_bytes',
               default=DEFAULT_MAX_SECRET_BYTES),
]

CONF = cfg.CONF
CONF.register_opts(common_opts)


def secret_too_big(data):
    if isinstance(data, six.text_type):
        return len(data.encode('UTF-8')) > CONF.max_allowed_secret_in_bytes
    else:
        return len(data) > CONF.max_allowed_secret_in_bytes


def get_invalid_property(validation_error):
    # we are interested in the second item which is the failed propertyName.
    if validation_error.schema_path and len(validation_error.schema_path) > 1:
        return validation_error.schema_path[1]


@six.add_metaclass(abc.ABCMeta)
class ValidatorBase(object):
    """Base class for validators."""

    name = ''

    @abc.abstractmethod
    def validate(self, json_data, parent_schema=None):
        """Validate the input JSON.

        :param json_data: JSON to validate against this class' internal schema.
        :param parent_schema: Name of the parent schema to this schema.
        :returns: dict -- JSON content, post-validation and
        :                 normalization/defaulting.
        :raises: schema.ValidationError on schema violations.

        """

    def _full_name(self, parent_schema=None):
        """Returns the full schema name for this validator,
        including parent name.
        """
        schema_name = self.name
        if parent_schema:
            schema_name = _("{0}' within '{1}").format(self.name,
                                                       parent_schema)
        return schema_name


class NewSecretValidator(ValidatorBase):
    """Validate a new secret."""

    def __init__(self):
        self.name = 'Secret'

        # TODO(jfwood): Get the list of mime_types from the crypto plugins?
        self.schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "algorithm": {"type": "string"},
                "mode": {"type": "string"},
                "bit_length": {"type": "integer", "minimum": 0},
                "expiration": {"type": "string"},
                "payload": {"type": "string"},
                "payload_content_type": {"type": "string"},
                "payload_content_encoding": {
                    "type": "string",
                    "enum": [
                        "base64"
                    ]
                },
            },
        }

    def validate(self, json_data, parent_schema=None):
        schema_name = self._full_name(parent_schema)

        try:
            schema.validate(json_data, self.schema)
        except schema.ValidationError as e:
            raise exception.InvalidObject(schema=schema_name,
                                          reason=e.message,
                                          property=get_invalid_property(e))

        # Validate/normalize 'name'.
        name = json_data.get('name', '').strip()
        if not name:
            name = None
        json_data['name'] = name

        # Validate/convert 'expiration' if provided.
        expiration = self._extract_expiration(json_data, schema_name)
        if expiration:
            # Verify not already expired.
            utcnow = timeutils.utcnow()
            if expiration <= utcnow:
                raise exception.InvalidObject(schema=schema_name,
                                              reason=_("'expiration' is "
                                                       "before current time"),
                                              property="expiration")
        json_data['expiration'] = expiration

        # Validate/convert 'payload' if provided.
        if 'payload' in json_data:
            content_type = json_data.get('payload_content_type')
            if content_type is None:
                raise exception.InvalidObject(
                    schema=schema_name,
                    reason=_("If 'payload' is supplied, 'payload_content_type'"
                             " must also be supplied."),
                    property="payload_content_type"
                )

            if content_type.lower() not in mime_types.SUPPORTED:
                raise exception.InvalidObject(
                    schema=schema_name,
                    reason=_("payload_content_type is not one of "
                             "{0}").format(mime_types.SUPPORTED),
                    property="payload_content_type"
                )

            content_encoding = json_data.get('payload_content_encoding')
            if content_type == 'application/octet-stream' and \
                    content_encoding is None:
                raise exception.InvalidObject(
                    schema=schema_name,
                    reason=_("payload_content_encoding must be specified "
                             "when payload_content_type is application/"
                             "octet-stream."),
                    property="payload_content_encoding"
                )

            if content_type.startswith('text/plain') and \
                    content_encoding is not None:
                raise exception.InvalidObject(
                    schema=schema_name,
                    reason=_("payload_content_encoding must not be specified "
                             "when payload_content_type is text/plain"),
                    property="payload_content_encoding"
                )

            payload = json_data['payload']
            if secret_too_big(payload):
                raise exception.LimitExceeded()

            payload = payload.strip()
            if not payload:
                raise exception.InvalidObject(schema=schema_name,
                                              reason=_("If 'payload' "
                                                       "specified, must be "
                                                       "non empty"),
                                              property="payload")

            json_data['payload'] = payload
        elif 'payload_content_type' in json_data and \
                parent_schema is None:
                raise exception.InvalidObject(
                    schema=schema_name,
                    reason=_("payload must be provided "
                             "when payload_content_type is specified"),
                    property="payload"
                )

        return json_data

    def _extract_expiration(self, json_data, schema_name):
        """Extracts and returns the expiration date from the JSON data."""
        expiration = None
        expiration_raw = json_data.get('expiration', None)
        if expiration_raw and expiration_raw.strip():
            try:
                expiration_tz = timeutils.parse_isotime(expiration_raw)
                expiration = timeutils.normalize_time(expiration_tz)
            except ValueError:
                LOG.exception("Problem parsing expiration date")
                raise exception.InvalidObject(schema=schema_name,
                                              reason=_("Invalid date "
                                                       "for 'expiration'"),
                                              property="expiration")

        return expiration


class NewOrderValidator(ValidatorBase):
    """Validate a new order."""

    def __init__(self):
        self.name = 'Order'
        self.schema = {
            "type": "object",
            "properties": {
            },
        }
        self.secret_validator = NewSecretValidator()

    def validate(self, json_data, parent_schema=None):
        schema_name = self._full_name(parent_schema)

        try:
            schema.validate(json_data, self.schema)
        except schema.ValidationError as e:
            raise exception.InvalidObject(schema=schema_name, reason=e.message,
                                          property=get_invalid_property(e))

        secret = json_data.get('secret')
        if secret is None:
            raise exception.InvalidObject(schema=schema_name,
                                          reason=_("'secret' attributes "
                                                   "are required"),
                                          property="secret")

        # If secret group is provided, validate it now.
        self.secret_validator.validate(secret, parent_schema=self.name)
        if 'payload' in secret:
            raise exception.InvalidObject(schema=schema_name,
                                          reason=_("'payload' not "
                                                   "allowed for secret "
                                                   "generation"),
                                          property="secret")

        # Validation secret generation related fields.
        # TODO(jfwood): Invoke the crypto plugin for this purpose

        if secret.get('payload_content_type') != 'application/octet-stream':
            raise exception.UnsupportedField(field='payload_content_type',
                                             schema=schema_name,
                                             reason=_("Only 'application/oc"
                                                      "tet-stream' supported"))

        if secret.get('mode', '').lower() != 'cbc':
            raise exception.UnsupportedField(field="mode",
                                             schema=schema_name,
                                             reason=_("Only 'cbc' "
                                                      "supported"))

        if secret.get('algorithm', '').lower() != 'aes':
            raise exception.UnsupportedField(field="algorithm",
                                             schema=schema_name,
                                             reason=_("Only 'aes' "
                                                      "supported"))

        # TODO(reaperhulk): Future API change will move from bit to byte_length
        bit_length = int(secret.get('bit_length', 0))
        if bit_length <= 0:
            raise exception.UnsupportedField(field="bit_length",
                                             schema=schema_name,
                                             reason=_("Must have non-zero "
                                                      "positive bit_length "
                                                      "to generate secret"))
        if bit_length % 8 != 0:
            raise exception.UnsupportedField(field="bit_length",
                                             schema=schema_name,
                                             reason=_("Must be a positive "
                                                      "integer that is a "
                                                      "multiple of 8"))

        return json_data


class ContainerValidator(ValidatorBase):
    """ Validator for all types of Container"""

    def __init__(self):
        self.name = 'Container'
        self.schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {
                    "type": "string",
                    #TODO: (hgedikli) move this to a common location
                    "enum": ["generic", "rsa"]
                },
                "secret_refs": {"type": "array", "items": {
                    "type": "object",
                    "required": ["secret_ref"],
                    "properties": {
                        "secret_ref": {"type": "string", "minLength": 1}
                    }
                }
                }
            },
            "required": ["type"]
        }

    def validate(self, json_data, parent_schema=None):
        schema_name = self._full_name(parent_schema)

        try:
            schema.validate(json_data, self.schema)
        except schema.ValidationError as e:
            raise exception.InvalidObject(schema=schema_name,
                                          reason=e.message,
                                          property=get_invalid_property(e))

        container_type = json_data.get('type')
        secret_refs = json_data.get('secret_refs')

        if secret_refs:
            secret_refs_names = [secret_ref['name']
                                 if 'name' in secret_ref else ''
                                 for secret_ref in secret_refs]

            if len(set(secret_refs_names)) != len(secret_refs):
                raise exception.\
                    InvalidObject(schema=schema_name,
                                  reason=_("Duplicate reference names"
                                           " are not allowed"),
                                  property="secret_refs")

            if container_type == 'rsa':
                supported_names = ('public_key',
                                   'private_key',
                                   'private_key_passphrase')

                if self.contains_unsupported_names(secret_refs,
                                                   supported_names) or len(
                        secret_refs) > 3:
                    raise exception.\
                        InvalidObject(schema=schema_name,
                                      reason=_("only 'private_key',"
                                               " 'public_key'"
                                               " and 'private_key_passphrase'"
                                               " reference names are allowed"
                                               " for RSA type"),
                                      property="secret_refs")

        return json_data

    def contains_unsupported_names(self, secret_refs, supported_names):
        for secret_ref in secret_refs:
                if secret_ref.get('name') not in supported_names:
                    return True


class NewTransportKeyValidator(ValidatorBase):
    """Validate a new transport key."""

    def __init__(self):
        self.name = 'Transport Key'

        self.schema = {
            "type": "object",
            "properties": {
                "plugin_name": {"type": "string"},
                "transport_key": {"type": "string"},
            },
        }

    def validate(self, json_data, parent_schema=None):
        schema_name = self._full_name(parent_schema)

        try:
            schema.validate(json_data, self.schema)
        except schema.ValidationError as e:
            raise exception.InvalidObject(schema=schema_name,
                                          reason=e.message,
                                          property=get_invalid_property(e))

        # Validate/normalize 'name'.
        plugin_name = json_data.get('plugin_name', '').strip()
        if not plugin_name:
            raise exception.InvalidObject(
                schema=schema_name,
                reason=_("plugin_name must be provided"),
                property="plugin_name"
            )
        json_data['plugin_name'] = plugin_name

        # Validate 'transport_key'.
        transport_key = json_data.get('transport_key', '').strip()
        if not transport_key:
            raise exception.InvalidObject(
                schema=schema_name,
                reason=_("transport_key must be provided"),
                property="transport_key"
            )
        json_data['transport_key'] = transport_key

        return json_data

########NEW FILE########
__FILENAME__ = context
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright  2011-2012 OpenStack LLC.
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

from barbican.common import utils
from barbican.openstack.common import local
from barbican.openstack.common import policy


class RequestContext(object):
    """Stores information about the security context under which the user
    accesses the system, as well as additional request information.
    """

    def __init__(self, auth_tok=None, user=None, tenant=None, roles=None,
                 is_admin=False, read_only=False, show_deleted=False,
                 owner_is_tenant=True, service_catalog=None,
                 policy_enforcer=None):
        self.auth_tok = auth_tok
        self.user = user
        self.tenant = tenant
        self.roles = roles or []
        self.read_only = read_only
        # TODO(jwood): self._show_deleted = show_deleted
        # (mkbhanda) possibly domain could be owner
        # brings us to the key scope question
        self.owner_is_tenant = owner_is_tenant
        self.request_id = utils.generate_uuid()
        self.service_catalog = service_catalog
        self.policy_enforcer = policy_enforcer or policy.Enforcer()
        self.is_admin = is_admin
        # TODO(jwood): Is this needed?
        #        if not self.is_admin:
        #            self.is_admin = \
        #                self.policy_enforcer.check_is_admin(self)

        if not hasattr(local.store, 'context'):
            self.update_store()

    def to_dict(self):
        # NOTE(ameade): These keys are named to correspond with the default
        # format string for logging the context in openstack common
        return {
            'request_id': self.request_id,

            #NOTE(bcwaldon): openstack-common logging expects 'user'
            'user': self.user,
            'user_id': self.user,

            #NOTE(bcwaldon): openstack-common logging expects 'tenant'
            'tenant': self.tenant,
            'tenant_id': self.tenant,
            'project_id': self.tenant,
            # TODO(jwood):            'is_admin': self.is_admin,
            # TODO(jwood):            'read_deleted': self.show_deleted,
            'roles': self.roles,
            'auth_token': self.auth_tok,
            'service_catalog': self.service_catalog,
        }

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    def update_store(self):
        local.store.context = self

    @property
    def owner(self):
        """Return the owner to correlate with key."""
        return self.tenant if self.owner_is_tenant else self.user

# TODO(jwood):
#    @property
#    def show_deleted(self):
#        """Admins can see deleted by default"""
#        if self._show_deleted or self.is_admin:
#            return True
#        return False

########NEW FILE########
__FILENAME__ = dogtag_crypto
# Copyright (c) 2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import os
import uuid

from oslo.config import cfg
import pki
from pki.client import PKIConnection
import pki.cryptoutil as cryptoutil
import pki.key as key
from pki.kraclient import KRAClient

from barbican.common import exception
from barbican.crypto import plugin
from barbican.openstack.common.gettextutils import _

CONF = cfg.CONF

dogtag_crypto_plugin_group = cfg.OptGroup(name='dogtag_crypto_plugin',
                                          title="Dogtag Crypto Plugin Options")
dogtag_crypto_plugin_opts = [
    cfg.StrOpt('pem_path',
               default=None,
               help=_('Path to PEM file for authentication')),
    cfg.StrOpt('pem_password',
               default=None,
               help=_('Password to unlock PEM file')),
    cfg.StrOpt('drm_host',
               default="localhost",
               help=_('Hostname for the DRM')),
    cfg.StrOpt('drm_port',
               default="8443",
               help=_('Port for the DRM')),
    cfg.StrOpt('nss_db_path',
               default=None,
               help=_('Path to the NSS certificate database')),
    cfg.StrOpt('nss_password',
               default=None,
               help=_('Password for NSS certificate database'))
]

CONF.register_group(dogtag_crypto_plugin_group)
CONF.register_opts(dogtag_crypto_plugin_opts, group=dogtag_crypto_plugin_group)


class DogtagPluginAlgorithmException(exception.BarbicanException):
    message = _("Invalid algorithm passed in")


class DogtagCryptoPlugin(plugin.CryptoPluginBase):
    """Dogtag implementation of the crypto plugin with DRM as the backend."""

    TRANSPORT_NICK = "DRM transport cert"

    def __init__(self, conf=CONF):
        """Constructor - create the keyclient."""
        pem_path = conf.dogtag_crypto_plugin.pem_path
        if pem_path is None:
            raise ValueError(_("pem_path is required"))

        pem_password = conf.dogtag_crypto_plugin.pem_password
        if pem_password is None:
            raise ValueError(_("pem_password is required"))

        crypto = None
        create_nss_db = False

        nss_db_path = conf.dogtag_crypto_plugin.nss_db_path
        if nss_db_path is not None:
            nss_password = conf.dogtag_crypto_plugin.nss_password
            if nss_password is None:
                raise ValueError(_("nss_password is required"))

            if not os.path.exists(nss_db_path):
                create_nss_db = True
                cryptoutil.NSSCryptoUtil.setup_database(
                    nss_db_path, nss_password, over_write=True)

            crypto = cryptoutil.NSSCryptoUtil(nss_db_path, nss_password)

        # set up connection
        connection = PKIConnection('https',
                                   conf.dogtag_crypto_plugin.drm_host,
                                   conf.dogtag_crypto_plugin.drm_port,
                                   'kra')
        connection.set_authentication_cert(pem_path)

        # what happened to the password?
        # until we figure out how to pass the password to requests, we'll
        # just use -nodes to create the admin cert pem file.  Any required
        # code will end up being in the DRM python client

        #create kraclient
        kraclient = KRAClient(connection, crypto)
        self.keyclient = kraclient.keys
        self.systemcert_client = kraclient.system_certs

        if crypto is not None:
            if create_nss_db:
                # Get transport cert and insert in the certdb
                transport_cert = self.systemcert_client.get_transport_cert()
                tcert = transport_cert[
                    len(pki.CERT_HEADER):
                    len(transport_cert) - len(pki.CERT_FOOTER)]
                crypto.import_cert(DogtagCryptoPlugin.TRANSPORT_NICK,
                                   base64.decodestring(tcert), "u,u,u")

            crypto.initialize()
            self.keyclient.set_transport_cert(
                DogtagCryptoPlugin.TRANSPORT_NICK)

    def encrypt(self, encrypt_dto, kek_meta_dto, keystone_id):
        """Store a secret in the DRM

        This will likely require another parameter which includes the wrapped
        session key to be passed.  Until that is added, we will call
        archive_key() which relies on the DRM python client to create the
        session keys.

        We may also be able to be more specific in terms of the data_type
        if we know that the data being stored is a symmetric key.  Until
        then, we need to assume that the secret is pass_phrase_type.
        """
        data_type = key.KeyClient.PASS_PHRASE_TYPE
        client_key_id = uuid.uuid4().hex
        response = self.keyclient.archive_key(client_key_id,
                                              data_type,
                                              encrypt_dto.unencrypted,
                                              key_algorithm=None,
                                              key_size=None)
        return plugin.ResponseDTO(response.get_key_id(), None)

    def decrypt(self, decrypt_dto, kek_meta_dto, kek_meta_extended,
                keystone_id):
        """Retrieve a secret from the DRM

        The encrypted parameter simply contains the plain text key_id by which
        the secret is known to the DRM.  The remaining parameters are not
        used.

        Note: There are two ways to retrieve secrets from the DRM.

        The first, which is implemented here, will call retrieve_key without
        a wrapping key.  This relies on the DRM client to generate a wrapping
        key (and wrap it with the DRM transport cert), and is completely
        transparent to the Barbican server.  What is returned to the caller
        is the unencrypted secret.

        The second way is to provide a wrapping key that ideally would be
        generated on the barbican client.  That way only the client will be
        able to unwrap the secret.  This is not yet implemented because
        decrypt() and the barbican API still need to be changed to pass the
        wrapping key.
        """
        key_id = decrypt_dto.encrypted
        key = self.keyclient.retrieve_key(key_id)
        return key.data

    def bind_kek_metadata(self, kek_meta_dto):
        """This function is not used by this plugin."""
        return kek_meta_dto

    def generate_symmetric(self, generate_dto, kek_meta_dto, keystone_id):
        """Generate a symmetric key

        This calls generate_symmetric_key() on the DRM passing in the
        algorithm, bit_length and id (used as the client_key_id) from
        the secret.  The remaining parameters are not used.

        Returns a keyId which will be stored in an EncryptedDatum
        table for later retrieval.
        """

        usages = [key.SymKeyGenerationRequest.DECRYPT_USAGE,
                  key.SymKeyGenerationRequest.ENCRYPT_USAGE]

        client_key_id = uuid.uuid4().hex
        algorithm = self._map_algorithm(generate_dto.algorithm.lower())

        if algorithm is None:
            raise DogtagPluginAlgorithmException

        response = self.keyclient.generate_symmetric_key(
            client_key_id,
            algorithm,
            generate_dto.bit_length,
            usages)
        return plugin.ResponseDTO(response.get_key_id(), None)

    def generate_asymmetric(self, generate_dto, kek_meta_dto, keystone_id):
        """Generate an asymmetric key."""
        raise NotImplementedError("Feature not implemented for dogtag crypto")

    def supports(self, type_enum, algorithm=None, bit_length=None,
                 mode=None):
        """Specifies what operations the plugin supports."""
        if type_enum == plugin.PluginSupportTypes.ENCRYPT_DECRYPT:
            return True
        elif type_enum == plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION:
            return self._is_algorithm_supported(algorithm,
                                                bit_length)
        elif type_enum == plugin.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION:
            return False
        else:
            return False

    @staticmethod
    def _map_algorithm(algorithm):
        """Map Barbican algorithms to Dogtag plugin algorithms."""
        if algorithm == "aes":
            return key.KeyClient.AES_ALGORITHM
        elif algorithm == "des":
            return key.KeyClient.DES_ALGORITHM
        elif algorithm == "3des":
            return key.KeyClient.DES3_ALGORITHM
        else:
            return None

    def _is_algorithm_supported(self, algorithm, bit_length=None):
        """Check if algorithm and bit length are supported

        For now, we will just check the algorithm. When dogtag adds a
        call to check the bit length per algorithm, we can modify to
        make that call
        """
        return self._map_algorithm(algorithm) is not None

########NEW FILE########
__FILENAME__ = extension_manager
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64

from oslo.config import cfg
from stevedore import named

from barbican.common import exception
from barbican.common import utils
from barbican.crypto import mime_types
from barbican.crypto import plugin as plugin_mod
from barbican.model import models
from barbican.openstack.common import gettextutils as u


CONF = cfg.CONF
DEFAULT_PLUGIN_NAMESPACE = 'barbican.crypto.plugin'
DEFAULT_PLUGINS = ['simple_crypto']

crypto_opt_group = cfg.OptGroup(name='crypto',
                                title='Crypto Plugin Options')
crypto_opts = [
    cfg.StrOpt('namespace',
               default=DEFAULT_PLUGIN_NAMESPACE,
               help=u._('Extension namespace to search for plugins.')
               ),
    cfg.MultiStrOpt('enabled_crypto_plugins',
                    default=DEFAULT_PLUGINS,
                    help=u._('List of crypto plugins to load.')
                    )
]
CONF.register_group(crypto_opt_group)
CONF.register_opts(crypto_opts, group=crypto_opt_group)


class CryptoContentTypeNotSupportedException(exception.BarbicanException):
    """Raised when support for payload content type is not available."""
    def __init__(self, content_type):
        super(CryptoContentTypeNotSupportedException, self).__init__(
            u._("Crypto Content Type "
                "of '{0}' not supported").format(content_type)
        )
        self.content_type = content_type


class CryptoContentEncodingNotSupportedException(exception.BarbicanException):
    """Raised when support for payload content encoding is not available."""
    def __init__(self, content_encoding):
        super(CryptoContentEncodingNotSupportedException, self).__init__(
            u._("Crypto Content-Encoding of '{0}' not supported").format(
                content_encoding)
        )
        self.content_encoding = content_encoding


class CryptoAcceptNotSupportedException(exception.BarbicanException):
    """Raised when requested decrypted content-type is not available."""
    def __init__(self, accept):
        super(CryptoAcceptNotSupportedException, self).__init__(
            u._("Crypto Accept of '{0}' not supported").format(accept)
        )
        self.accept = accept


class CryptoAlgorithmNotSupportedException(exception.BarbicanException):
    """Raised when support for an algorithm is not available."""
    def __init__(self, algorithm):
        super(CryptoAlgorithmNotSupportedException, self).__init__(
            u._("Crypto algorithm of '{0}' not supported").format(
                algorithm)
        )
        self.algorithm = algorithm


class CryptoPayloadDecodingError(exception.BarbicanException):
    """Raised when payload could not be decoded."""
    def __init__(self):
        super(CryptoPayloadDecodingError, self).__init__(
            u._("Problem decoding payload")
        )


class CryptoSupportedPluginNotFound(exception.BarbicanException):
    """Raised when no plugins are found that support the requested
    operation.
    """
    message = "Crypto plugin not found for requested operation."


class CryptoPluginNotFound(exception.BarbicanException):
    """Raised when no plugins are installed."""
    message = u._("Crypto plugin not found.")


class CryptoNoPayloadProvidedException(exception.BarbicanException):
    """Raised when secret information is not provided."""
    def __init__(self):
        super(CryptoNoPayloadProvidedException, self).__init__(
            u._('No secret information provided to encrypt.')
        )


class CryptoNoSecretOrDataFoundException(exception.BarbicanException):
    """Raised when secret information could not be located."""
    def __init__(self, secret_id):
        super(CryptoNoSecretOrDataFoundException, self).__init__(
            u._('No secret information located for '
                'secret {0}').format(secret_id)
        )
        self.secret_id = secret_id


class CryptoContentEncodingMustBeBase64(exception.BarbicanException):
    """Raised when encoding must be base64."""
    def __init__(self):
        super(CryptoContentEncodingMustBeBase64, self).__init__(
            u._("Encoding type must be 'base64' for text-based payloads.")
        )


class CryptoKEKBindingException(exception.BarbicanException):
    """Raised when the bind_kek_metadata method from a plugin returns None."""
    def __init__(self, plugin_name=u._('Unknown')):
        super(CryptoKEKBindingException, self).__init__(
            u._('Failed to bind kek metadata for '
                'plugin: {0}').format(plugin_name)
        )
        self.plugin_name = plugin_name


class CryptoGeneralException(exception.BarbicanException):
    """Raised when a system fault has occurred."""
    def __init__(self, reason=u._('Unknown')):
        super(CryptoGeneralException, self).__init__(
            u._('Problem seen during crypto processing - '
                'Reason: {0}').format(reason)
        )
        self.reason = reason


def normalize_before_encryption(unencrypted, content_type, content_encoding,
                                enforce_text_only=False):
    """Normalize unencrypted prior to plugin encryption processing."""
    if not unencrypted:
        raise CryptoNoPayloadProvidedException()

    # Validate and normalize content-type.
    normalized_mime = mime_types.normalize_content_type(content_type)
    if not mime_types.is_supported(normalized_mime):
        raise CryptoContentTypeNotSupportedException(content_type)

    # Process plain-text type.
    if normalized_mime in mime_types.PLAIN_TEXT:
        # normalize text to binary string
        unencrypted = unencrypted.encode('utf-8')

    # Process binary type.
    else:
        # payload has to be decoded
        if mime_types.is_base64_processing_needed(content_type,
                                                  content_encoding):
            try:
                unencrypted = base64.b64decode(unencrypted)
            except TypeError:
                raise CryptoPayloadDecodingError()
        elif enforce_text_only:
            # For text-based protocols (such as the one-step secret POST),
            #   only 'base64' encoding is possible/supported.
            raise CryptoContentEncodingMustBeBase64()
        elif content_encoding:
            # Unsupported content-encoding request.
            raise CryptoContentEncodingNotSupportedException(content_encoding)

    return unencrypted, normalized_mime


def analyze_before_decryption(content_type):
    """Determine support for desired content type."""
    if not mime_types.is_supported(content_type):
        raise CryptoAcceptNotSupportedException(content_type)


def denormalize_after_decryption(unencrypted, content_type):
    """Translate the decrypted data into the desired content type."""
    # Process plain-text type.
    if content_type in mime_types.PLAIN_TEXT:
        # normalize text to binary string
        try:
            unencrypted = unencrypted.decode('utf-8')
        except UnicodeDecodeError:
            raise CryptoAcceptNotSupportedException(content_type)

    # Process binary type.
    elif content_type not in mime_types.BINARY:
        raise CryptoGeneralException(
            u._("Unexpected content-type: '{0}'").format(content_type))

    return unencrypted


class CryptoExtensionManager(named.NamedExtensionManager):
    def __init__(self, conf=CONF, invoke_on_load=True,
                 invoke_args=(), invoke_kwargs={}):
        super(CryptoExtensionManager, self).__init__(
            conf.crypto.namespace,
            conf.crypto.enabled_crypto_plugins,
            invoke_on_load=invoke_on_load,
            invoke_args=invoke_args,
            invoke_kwds=invoke_kwargs
        )

    def encrypt(self, unencrypted, content_type, content_encoding,
                secret, tenant, kek_repo, enforce_text_only=False):
        """Delegates encryption to first plugin that supports it."""

        if len(self.extensions) < 1:
            raise CryptoPluginNotFound()

        for ext in self.extensions:
            if ext.obj.supports(plugin_mod.PluginSupportTypes.ENCRYPT_DECRYPT):
                encrypting_plugin = ext.obj
                break
        else:
            raise CryptoSupportedPluginNotFound()

        unencrypted, content_type = normalize_before_encryption(
            unencrypted, content_type, content_encoding,
            enforce_text_only=enforce_text_only)

        # Find or create a key encryption key metadata.
        kek_datum, kek_meta_dto = self._find_or_create_kek_objects(
            encrypting_plugin, tenant, kek_repo)

        encrypt_dto = plugin_mod.EncryptDTO(unencrypted)
        # Create an encrypted datum instance and add the encrypted cypher text.
        datum = models.EncryptedDatum(secret, kek_datum)
        datum.content_type = content_type
        response_dto = encrypting_plugin.encrypt(
            encrypt_dto, kek_meta_dto, tenant.keystone_id
        )

        datum.cypher_text = response_dto.cypher_text
        datum.kek_meta_extended = response_dto.kek_meta_extended

        # Convert binary data into a text-based format.
        #TODO(jwood) Figure out by storing binary (BYTEA) data in Postgres
        #  isn't working.
        datum.cypher_text = base64.b64encode(datum.cypher_text)

        return datum

    def decrypt(self, content_type, secret, tenant):
        """Delegates decryption to active plugins."""

        if not secret or not secret.encrypted_data:
            raise CryptoNoSecretOrDataFoundException(secret.id)

        analyze_before_decryption(content_type)

        for ext in self.extensions:
            decrypting_plugin = ext.obj
            for datum in secret.encrypted_data:
                if self._plugin_supports(decrypting_plugin,
                                         datum.kek_meta_tenant):
                    # wrap the KEKDatum instance in our DTO
                    kek_meta_dto = plugin_mod.KEKMetaDTO(datum.kek_meta_tenant)

                    # Convert from text-based storage format to binary.
                    #TODO(jwood) Figure out by storing binary (BYTEA) data in
                    #  Postgres isn't working.
                    encrypted = base64.b64decode(datum.cypher_text)
                    decrypt_dto = plugin_mod.DecryptDTO(encrypted)

                    # Decrypt the secret.
                    unencrypted = decrypting_plugin \
                        .decrypt(decrypt_dto,
                                 kek_meta_dto,
                                 datum.kek_meta_extended,
                                 tenant.keystone_id)

                    # Denormalize the decrypted info per request.
                    return denormalize_after_decryption(unencrypted,
                                                        content_type)
        else:
            raise CryptoPluginNotFound()

    def generate_symmetric_encryption_key(self, secret, content_type, tenant,
                                          kek_repo):
        """Delegates generating a key to the first supported plugin.

        Note that this key can be used by clients for their encryption
        processes. This generated key is then be encrypted via
        the plug-in key encryption process, and that encrypted datum
        is then returned from this method.
        """
        encrypting_plugin = \
            self._determine_crypto_plugin(secret.algorithm,
                                          secret.bit_length,
                                          secret.mode)

        kek_datum, kek_meta_dto = self._find_or_create_kek_objects(
            encrypting_plugin, tenant, kek_repo)

        # Create an encrypted datum instance and add the created cypher text.
        datum = models.EncryptedDatum(secret, kek_datum)
        datum.content_type = content_type

        generate_dto = plugin_mod.GenerateDTO(secret.algorithm,
                                              secret.bit_length,
                                              secret.mode, None)
        # Create the encrypted meta.
        response_dto = encrypting_plugin.generate_symmetric(generate_dto,
                                                            kek_meta_dto,
                                                            tenant.keystone_id)

        # Convert binary data into a text-based format.
        # TODO(jwood) Figure out by storing binary (BYTEA) data in Postgres
        #  isn't working.
        datum.cypher_text = base64.b64encode(response_dto.cypher_text)
        datum.kek_meta_extended = response_dto.kek_meta_extended
        return datum

    def generate_asymmetric_encryption_keys(self, meta, content_type, tenant,
                                            kek_repo):
        """Delegates generating a asymmteric keys to the first
        supported plugin based on `meta`. meta will provide extra
        information to help key generation.
        Based on passpharse in meta this method will return a tuple
        with two/three objects.

        Note that this key can be used by clients for their encryption
        processes. This generated key is then be encrypted via
        the plug-in key encryption process, and that encrypted datum
        is then returned from this method.
        """
        encrypting_plugin = \
            self._determine_crypto_plugin(meta.algorithm,
                                          meta.bit_length,
                                          meta.passphrase)

        kek_datum, kek_meta_dto = self._find_or_create_kek_objects(
            encrypting_plugin, tenant, kek_repo)

        generate_dto = plugin_mod.GenerateDTO(meta.algorithm,
                                              meta.bit_length,
                                              None, meta.passphrase)
        # generate the secret.
        private_key_dto, public_key_dto, passwd_dto = \
            encrypting_plugin.generate_asymmetric(
                generate_dto,
                kek_meta_dto,
                tenant.keystone_id)

        # Create an encrypted datum instances for each secret type
        # and add the created cypher text.
        priv_datum = models.EncryptedDatum(None, kek_datum)
        priv_datum.content_type = content_type
        priv_datum.cypher_text = base64.b64encode(private_key_dto.cypher_text)
        priv_datum.kek_meta_extended = private_key_dto.kek_meta_extended

        public_datum = models.EncryptedDatum(None, kek_datum)
        public_datum.content_type = content_type
        public_datum.cypher_text = base64.b64encode(public_key_dto.cypher_text)
        public_datum.kek_meta_extended = public_key_dto.kek_meta_extended

        passwd_datum = None
        if passwd_dto:
            passwd_datum = models.EncryptedDatum(None, kek_datum)
            passwd_datum.content_type = content_type
            passwd_datum.cypher_text = base64.b64encode(passwd_dto.cypher_text)
            passwd_datum.kek_meta_extended = \
                passwd_dto.kek_meta_extended

        return (priv_datum, public_datum, passwd_datum)

    def _determine_type(self, algorithm):
        """Determines the type (symmetric and asymmetric for now)
        based on algorithm
        """
        symmetric_algs = plugin_mod.PluginSupportTypes.SYMMETRIC_ALGORITHMS
        asymmetric_algs = plugin_mod.PluginSupportTypes.ASYMMETRIC_ALGORITHMS
        if algorithm.lower() in symmetric_algs:
            return plugin_mod.PluginSupportTypes.SYMMETRIC_KEY_GENERATION
        elif algorithm.lower() in asymmetric_algs:
            return plugin_mod.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION
        else:
            raise CryptoAlgorithmNotSupportedException(algorithm)

    #TODO(atiwari): Use meta object instead of individual attribute
    #This has to be done while integration rest resources
    def _determine_crypto_plugin(self, algorithm, bit_length=None,
                                 mode=None):
        """Determines the generation type and encrypting plug-in
            which supports the generation of secret based on
            generation type
        """
        if len(self.extensions) < 1:
            raise CryptoPluginNotFound()

        generation_type = self._determine_type(algorithm)
        for ext in self.extensions:
            if ext.obj.supports(generation_type, algorithm,
                                bit_length,
                                mode):
                encrypting_plugin = ext.obj
                break
        else:
            raise CryptoSupportedPluginNotFound()

        return encrypting_plugin

    def _plugin_supports(self, plugin_inst, kek_metadata_tenant):
        """Tests for plugin support.

        Tests if the supplied plugin supports operations on the supplied
        key encryption key (KEK) metadata.

        :param plugin_inst: The plugin instance to test.
        :param kek_metadata: The KEK metadata to test.
        :return: True if the plugin can support operations on the KEK metadata.

        """
        plugin_name = utils.generate_fullname_for(plugin_inst)
        return plugin_name == kek_metadata_tenant.plugin_name

    def _find_or_create_kek_objects(self, plugin_inst, tenant, kek_repo):
        # Find or create a key encryption key.
        full_plugin_name = utils.generate_fullname_for(plugin_inst)
        kek_datum = kek_repo.find_or_create_kek_datum(tenant,
                                                      full_plugin_name)

        # Bind to the plugin's key management.
        # TODO(jwood): Does this need to be in a critical section? Should the
        # bind operation just be declared idempotent in the plugin contract?
        kek_meta_dto = plugin_mod.KEKMetaDTO(kek_datum)
        if not kek_datum.bind_completed:
            kek_meta_dto = plugin_inst.bind_kek_metadata(kek_meta_dto)

            # By contract, enforce that plugins return a
            # (typically modified) DTO.
            if kek_meta_dto is None:
                raise CryptoKEKBindingException(full_plugin_name)

            plugin_mod.indicate_bind_completed(kek_meta_dto, kek_datum)
            kek_repo.save(kek_datum)

        return kek_datum, kek_meta_dto

########NEW FILE########
__FILENAME__ = mime_types
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Barbican defined mime-types
"""

from barbican.common import utils


# Supported content types
#   Note: These types may be provided by clients.
PLAIN_TEXT = ['text/plain',
              'text/plain;charset=utf-8',
              'text/plain; charset=utf-8']
PLAIN_TEXT_CHARSETS = ['utf-8']
BINARY = ['application/octet-stream']
SUPPORTED = PLAIN_TEXT + BINARY

# Normalizes client types to internal types.
INTERNAL_CTYPES = {'text/plain': 'text/plain',
                   'text/plain;charset=utf-8': 'text/plain',
                   'text/plain; charset=utf-8': 'text/plain',
                   'application/octet-stream': 'application/octet-stream',
                   'application/aes': 'application/aes'}

# Maps mime-types used to specify secret data formats to the types that can
#   be requested for secrets via GET calls.
#   Note: Raw client types are converted into the 'INTERNAL_CTYPES' types
#   which are then used as the keys to the 'CTYPES_MAPPINGS' below.
CTYPES_PLAIN = {'default': 'text/plain'}
CTYPES_BINARY = {'default': 'application/octet-stream'}
CTYPES_AES = {'default': 'application/aes'}
CTYPES_MAPPINGS = {'text/plain': CTYPES_PLAIN,
                   'application/octet-stream': CTYPES_BINARY,
                   'application/aes': CTYPES_AES}

# Supported encodings
ENCODINGS = ['base64']

# Maps normalized content-types to supported encoding(s)
CTYPES_TO_ENCODINGS = {'text/plain': None,
                       'application/octet-stream': ['base64'],
                       'application/aes': None}


def normalize_content_type(mime_type):
    """Normalize the supplied content-type to an internal form."""
    stripped = map(lambda x: x.strip(), mime_type.split(';'))
    mime = stripped[0].lower()
    if len(stripped) > 1:
        # mime type includes charset
        charset_type = stripped[1].lower()
        if '=' not in charset_type:
            # charset is malformed
            return mime_type
        else:
            charset = map(lambda x: x.strip(), charset_type.split('='))[1]
            if charset not in PLAIN_TEXT_CHARSETS:
                # unsupported charset
                return mime_type
    return INTERNAL_CTYPES.get(mime, mime_type)


def is_supported(mime_type):
    return mime_type in SUPPORTED


def is_base64_encoding_supported(mime_type):
    if is_supported(mime_type):
        encodings = CTYPES_TO_ENCODINGS[INTERNAL_CTYPES[mime_type]]
        return encodings and ('base64' in encodings)
    return False


def is_base64_processing_needed(content_type, content_encoding):
    content_encodings = utils.get_accepted_encodings_direct(content_encoding)
    if content_encodings:
        if 'base64' not in content_encodings:
            return False
        if is_supported(content_type):
            encodings = CTYPES_TO_ENCODINGS[INTERNAL_CTYPES[content_type]]
            return encodings and 'base64' in encodings
    return False


def augment_fields_with_content_types(secret):
    """Add content-types and encodings information to a Secret's fields.

    Generate a dict of content types based on the data associated
    with the specified secret.

    :param secret: The models.Secret instance to add 'content_types' to.
    """

    fields = secret.to_dict_fields()

    if not secret.encrypted_data:
        return fields

    # TODO(jwood): How deal with merging more than one datum instance?
    for datum in secret.encrypted_data:
        if datum.content_type in CTYPES_MAPPINGS:
            fields.update(
                {'content_types': CTYPES_MAPPINGS[datum.content_type]}
            )
            break

    return fields

########NEW FILE########
__FILENAME__ = p11_crypto
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

try:
    import PyKCS11
except ImportError:
    PyKCS11 = {}  # TODO(reaperhulk): remove testing workaround


import base64

from oslo.config import cfg

from barbican.common import exception
from barbican.crypto import plugin

from barbican.openstack.common.gettextutils import _
from barbican.openstack.common import jsonutils as json


CONF = cfg.CONF

p11_crypto_plugin_group = cfg.OptGroup(name='p11_crypto_plugin',
                                       title="PKCS11 Crypto Plugin Options")
p11_crypto_plugin_opts = [
    cfg.StrOpt('library_path',
               default=None,
               help=_('Path to vendor PKCS11 library')),
    cfg.StrOpt('login',
               default=None,
               help=_('Password to login to PKCS11 session'))
]
CONF.register_group(p11_crypto_plugin_group)
CONF.register_opts(p11_crypto_plugin_opts, group=p11_crypto_plugin_group)


class P11CryptoPluginKeyException(exception.BarbicanException):
    message = _("More than one key found for label")


class P11CryptoPluginException(exception.BarbicanException):
    message = _("General exception")


class P11CryptoPlugin(plugin.CryptoPluginBase):
    """PKCS11 supporting implementation of the crypto plugin.
    Generates a key per tenant and encrypts using AES-256-GCM.
    This implementation currently relies on an unreleased fork of PyKCS11.
    """

    def __init__(self, conf=cfg.CONF):
        self.block_size = 16  # in bytes
        self.kek_key_length = 32  # in bytes (256-bit)
        self.algorithm = 0x8000011c  # CKM_AES_GCM vendor prefixed.
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        if conf.p11_crypto_plugin.library_path is None:
            raise ValueError(_("library_path is required"))
        else:
            self.pkcs11.load(conf.p11_crypto_plugin.library_path)
        # initialize the library. PyKCS11 does not supply this for free
        self._check_error(self.pkcs11.lib.C_Initialize())
        self.session = self.pkcs11.openSession(1)
        self.session.login(conf.p11_crypto_plugin.login)
        self.rw_session = self.pkcs11.openSession(1, PyKCS11.CKF_RW_SESSION)
        self.rw_session.login(conf.p11_crypto_plugin.login)

    def _check_error(self, value):
        if value != PyKCS11.CKR_OK:
            raise PyKCS11.PyKCS11Error(value)

    def _get_key_by_label(self, key_label):
        template = (
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
            (PyKCS11.CKA_LABEL, key_label))
        keys = self.session.findObjects(template)
        if len(keys) == 1:
            return keys[0]
        elif len(keys) == 0:
            return None
        else:
            raise P11CryptoPluginKeyException()

    def _generate_iv(self):
        iv = self.session.generateRandom(self.block_size)
        iv = b''.join(chr(i) for i in iv)
        if len(iv) != self.block_size:
            raise P11CryptoPluginException()
        return iv

    def _build_gcm_params(self, iv):
        gcm = PyKCS11.LowLevel.CK_AES_GCM_PARAMS()
        gcm.pIv = iv
        gcm.ulIvLen = len(iv)
        gcm.ulIvBits = len(iv) * 8
        gcm.ulTagBits = 128
        return gcm

    def _generate_kek(self, kek_label):
        # TODO(reaperhulk): review template to ensure it's what we want
        template = (
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
            (PyKCS11.CKA_VALUE_LEN, self.kek_key_length),
            (PyKCS11.CKA_LABEL, kek_label),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_ENCRYPT, True),
            (PyKCS11.CKA_DECRYPT, True),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_WRAP, True),
            (PyKCS11.CKA_UNWRAP, True),
            (PyKCS11.CKA_EXTRACTABLE, False))
        ckattr = self.session._template2ckattrlist(template)

        m = PyKCS11.LowLevel.CK_MECHANISM()
        m.mechanism = PyKCS11.LowLevel.CKM_AES_KEY_GEN

        key = PyKCS11.LowLevel.CK_OBJECT_HANDLE()
        self._check_error(
            self.pkcs11.lib.C_GenerateKey(
                self.rw_session.session,
                m,
                ckattr,
                key
            )
        )

    def encrypt(self, encrypt_dto, kek_meta_dto, keystone_id):
        key = self._get_key_by_label(kek_meta_dto.kek_label)
        iv = self._generate_iv()
        gcm = self._build_gcm_params(iv)
        mech = PyKCS11.Mechanism(self.algorithm, gcm)
        encrypted = self.session.encrypt(key, encrypt_dto.unencrypted, mech)
        cyphertext = b''.join(chr(i) for i in encrypted)
        kek_meta_extended = json.dumps({
            'iv': base64.b64encode(iv)
        })

        return plugin.ResponseDTO(cyphertext, kek_meta_extended)

    def decrypt(self, decrypt_dto, kek_meta_dto, kek_meta_extended,
                keystone_id):
        key = self._get_key_by_label(kek_meta_dto.kek_label)
        meta_extended = json.loads(kek_meta_extended)
        iv = base64.b64decode(meta_extended['iv'])
        gcm = self._build_gcm_params(iv)
        mech = PyKCS11.Mechanism(self.algorithm, gcm)
        decrypted = self.session.decrypt(key, decrypt_dto.encrypted, mech)
        secret = b''.join(chr(i) for i in decrypted)
        return secret

    def bind_kek_metadata(self, kek_meta_dto):
        # Enforce idempotency: If we've already generated a key for the
        # kek_label, leave now.
        key = self._get_key_by_label(kek_meta_dto.kek_label)
        if not key:
            self._generate_kek(kek_meta_dto.kek_label)
            # To be persisted by Barbican:
            kek_meta_dto.algorithm = 'AES'
            kek_meta_dto.bit_length = self.kek_key_length * 8
            kek_meta_dto.mode = 'GCM'
            kek_meta_dto.plugin_meta = None

        return kek_meta_dto

    def generate_symmetric(self, generate_dto, kek_meta_dto, keystone_id):
        byte_length = generate_dto.bit_length / 8
        rand = self.session.generateRandom(byte_length)
        if len(rand) != byte_length:
            raise P11CryptoPluginException()
        return self.encrypt(plugin.EncryptDTO(rand), kek_meta_dto, keystone_id)

    def generate_asymmetric(self, generate_dto, kek_meta_dto, keystone_id):
        raise NotImplementedError("Feature not implemented for PKCS11")

    def supports(self, type_enum, algorithm=None, bit_length=None, mode=None):
        if type_enum == plugin.PluginSupportTypes.ENCRYPT_DECRYPT:
            return True
        elif type_enum == plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION:
            return True
        elif type_enum == plugin.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION:
            return False
        else:
            return False

########NEW FILE########
__FILENAME__ = plugin
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc

from Crypto.Cipher import AES
from Crypto.PublicKey import DSA
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Util import asn1

from oslo.config import cfg

import six

from barbican.common import utils
from barbican.openstack.common.gettextutils import _

LOG = utils.getLogger(__name__)

CONF = cfg.CONF

simple_crypto_plugin_group = cfg.OptGroup(name='simple_crypto_plugin',
                                          title="Simple Crypto Plugin Options")
simple_crypto_plugin_opts = [
    cfg.StrOpt('kek',
               default=b'sixteen_byte_key',
               help=_('Key encryption key to be used by Simple Crypto Plugin'))
]
CONF.register_group(simple_crypto_plugin_group)
CONF.register_opts(simple_crypto_plugin_opts, group=simple_crypto_plugin_group)


class PluginSupportTypes(object):
    """Class to hold the type enumeration that plugins may support."""
    ENCRYPT_DECRYPT = "ENCRYPT_DECRYPT"
    SYMMETRIC_KEY_GENERATION = "SYMMETRIC_KEY_GENERATION"
    # A list of symmetric algorithms that are used to determine type of key gen
    SYMMETRIC_ALGORITHMS = ['aes', 'des', '3des', 'hmacsha1',
                            'hmacsha256', 'hmacsha384', 'hmacsha512']
    SYMMETRIC_KEY_LENGTHS = [64, 128, 192, 256]

    ASYMMETRIC_KEY_GENERATION = "ASYMMETRIC_KEY_GENERATION"
    ASYMMETRIC_ALGORITHMS = ['rsa', 'dsa']
    ASYMMETRIC_KEY_LENGTHS = [1024, 2048, 4096]


class KEKMetaDTO(object):
    """Key Encryption Keys (KEKs) in Barbican are intended to represent a
    distinct key that is used to perform encryption on secrets for a particular
    project (tenant).

    ``KEKMetaDTO`` objects are provided to cryptographic backends by Barbican
    to allow plugins to persist metadata related to the project's (tenant's)
    KEK.

    For example, a plugin that interfaces with a Hardware Security Module (HSM)
    may want to use a different encryption key for each tenant. Such a plugin
    could use the ``KEKMetaDTO`` object to save the key ID used for that
    tenant.  Barbican will persist the KEK metadata and ensure that it is
    provided to the plugin every time a request from that same tenant is
    processed.

    .. attribute:: plugin_name

        String attribute used by Barbican to identify the plugin that is bound
        to the KEK metadata.  Plugins should not change this attribute.

    .. attribute:: kek_label

        String attribute used to label the project's (tenant's) KEK by the
        plugin.  The value of this attribute should be meaningful to the
        plugin.  Barbican does not use this value.

    .. attribute:: algorithm

        String attribute used to identify the encryption algorithm used by the
        plugin. e.g. "AES", "3DES", etc.  This value should be meaningful to
        the plugin.  Barbican does not use this value.

    .. attribute:: mode

        String attribute used to identify the algorithm mode used by the
        plugin.  e.g. "CBC", "GCM", etc.  This value should be meaningful to
        the plugin.  Barbican does not use this value.

    .. attribute:: bit_length

        Integer attribute used to identify the bit length of the KEK by the
        plugin.  This value should be meaningful to the plugin.  Barbican does
        not use this value.

    .. attribute:: plugin_meta

       String attribute used to persist any additional metadata that does not
       fit in any other attribute.  The value of this attribute is defined by
       the plugin.  It could be used to store external system references, such
       as Key IDs in an HSM, URIs to an external service, or any other data
       that the plugin deems necessary to persist.  Because this is just a
       plain text field, a plug in may even choose to persist data such as key
       value pairs in a JSON object.
   """

    def __init__(self, kek_datum):
        """kek_datum is typically a barbican.model.models.EncryptedDatum
        instance.  Plugins should never have to create their own instance of
        this class.
        """
        self.kek_label = kek_datum.kek_label
        self.plugin_name = kek_datum.plugin_name
        self.algorithm = kek_datum.algorithm
        self.bit_length = kek_datum.bit_length
        self.mode = kek_datum.mode
        self.plugin_meta = kek_datum.plugin_meta


class GenerateDTO(object):
    """Data Transfer Object used to pass all the necessary data for the plugin
    to generate a secret on behalf of the user.

    .. attribute:: generation_type

        String attribute used to identify the type of secret that should be
        generated. This will be either ``"symmetric"`` or ``"asymmetric"``.

    .. attribute:: algoritm

        String attribute used to specify what type of algorithm the secret will
        be used for.  e.g. ``"AES"`` for a ``"symmetric"`` type, or ``"RSA"``
        for ``"asymmetric"``.

    .. attribute:: mode

        String attribute used to specify what algorithm mode the secret will be
        used for.  e.g. ``"CBC"`` for ``"AES"`` algorithm.

    .. attribute:: bit_length

        Integer attribute used to specify the bit length of the secret.  For
        example, this attribute could specify the key length for an encryption
        key to be used in AES-CBC.
    """

    def __init__(self, algorithm, bit_length, mode, passphrase=None):
        self.algorithm = algorithm
        self.bit_length = bit_length
        self.mode = mode
        self.passphrase = passphrase


class ResponseDTO(object):
    """Data transfer object for secret generation response."""

    def __init__(self, cypher_text, kek_meta_extended=None):
        self.cypher_text = cypher_text
        self.kek_meta_extended = kek_meta_extended


class DecryptDTO(object):
    """Data Transfer Object used to pass all the necessary data for the plugin
    to perform decryption of a secret.

    Currently, this DTO only contains the data produced by the plugin during
    encryption, but in the future this DTO will contain more information, such
    as a transport key for secret wrapping back to the client.

    .. attribute:: encrypted

        The data that was produced by the plugin during encryption.  For some
        plugins this will be the actual bytes that need to be decrypted to
        produce the secret.  In other implementations, this may just be a
        reference to some external system that can produce the unencrypted
        secret.
    """

    def __init__(self, encrypted):
        self.encrypted = encrypted


class EncryptDTO(object):
    """Data Transfer Object used to pass all the necessary data for the plugin
    to perform encryption of a secret.

    Currently, this DTO only contains the raw bytes to be encrypted by the
    plugin, but in the future this may contain more information.

    .. attribute:: unencrypted

        The secret data in Bytes to be encrypted by the plugin.
    """

    def __init__(self, unencrypted):
        self.unencrypted = unencrypted


def indicate_bind_completed(kek_meta_dto, kek_datum):
    """Updates the supplied kek_datum instance per the contents of the supplied
    kek_meta_dto instance. This function is typically used once plugins have
    had a chance to bind kek_meta_dto to their crypto systems.

    :param kek_meta_dto:
    :param kek_datum:
    :return: None

    """
    kek_datum.bind_completed = True
    kek_datum.algorithm = kek_meta_dto.algorithm
    kek_datum.bit_length = kek_meta_dto.bit_length
    kek_datum.mode = kek_meta_dto.mode
    kek_datum.plugin_meta = kek_meta_dto.plugin_meta


@six.add_metaclass(abc.ABCMeta)
class CryptoPluginBase(object):
    """Base class for all Crypto plugins.  Implementations of this abstract
    base class will be used by Barbican to perform cryptographic operations on
    secrets.

    Barbican requests operations by invoking the methods on an instance of the
    implementing class.  Barbican's plugin manager handles the life-cycle of
    the Data Transfer Objects (DTOs) that are passed into these methods, and
    persist the data that is assigned to these DTOs by the plugin.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def encrypt(self, encrypt_dto, kek_meta_dto, keystone_id):
        """This method will be called by Barbican when requesting an encryption
        operation on a secret on behalf of a project (tenant).

        :param encrypt_dto: :class:`EncryptDTO` instance containing the raw
            secret byte data to be encrypted.
        :type encrypt_dto: :class:`EncryptDTO`
        :param kek_meta_dto: :class:`KEKMetaDTO` instance containing
            information about the project's (tenant's) Key Encryption Key (KEK)
            to be used for encryption.  Plugins may assume that binding via
            :meth:`bind_kek_metadata` has already taken place before this
            instance is passed in.
        :type kek_meta_dto: :class:`KEKMetaDTO`
        :param keystone_id: Project (tenant) ID associated with the unencrypted
            data.
        :return: A tuple containing two items ``(ciphertext,
            kek_metadata_extended)``.  In a typical plugin implementation, the
            first item in the tuple should be the ciphertext byte data
            resulting from the encryption of the secret data.  The second item
            is an optional String object to be persisted alongside the
            ciphertext.

            Barbican guarantees that both the ``ciphertext`` and
            ``kek_metadata_extended`` will be persisted and then given back to
            the plugin when requesting a decryption operation.

            It should be noted that Barbican does not require that the data
            returned for the ``ciphertext`` be the actual encrypted
            bytes of the secret data.  The only requirement is that the plugin
            is able to use whatever data it chooses to return in ``ciphertext``
            to produce the secret data during decryption.  This allows more
            complex plugins to make decisions regarding the storage of the
            encrypted data.  For example, the DogTag plugin stores the
            encrypted bytes in an external system and uses Barbican to store an
            identifier to the external system in ``ciphertext``.  During
            decryption, Barbican gives the external identifier back to the
            DogTag plugin, and then the plugin is able to use the identifier to
            retrieve the secret data from the external storage system.

            ``kek_metadata_extended`` takes the idea of Key Encryption Key
            (KEK) metadata further by giving plugins the option to store
            secret-level KEK metadata.  One example of using secret-level KEK
            metadata would be plugins that want to use a unique KEK for every
            secret that is encrypted.  Such a plugin could use
            ``kek_metadata_extended`` to store the Key ID for the KEK used to
            encrypt this particular secret.
        :rtype: tuple
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def decrypt(self, decrypt_dto, kek_meta_dto, kek_meta_extended,
                keystone_id):
        """Decrypt encrypted_datum in the context of the provided tenant.

        :param decrypt_dto: data transfer object containing the cyphertext
               to be decrypted.
        :param kek_meta_dto: Key encryption key metadata to use for decryption
        :param kek_meta_extended: Optional per-secret KEK metadata to use for
        decryption.
        :param keystone_id: keystone_id associated with the encrypted datum.
        :returns: str -- unencrypted byte data

        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def bind_kek_metadata(self, kek_meta_dto):
        """Bind a key encryption key (KEK) metadata to the sub-system
        handling encryption/decryption, updating information about the
        key encryption key (KEK) metadata in the supplied 'kek_metadata'
        data-transfer-object instance, and then returning this instance.

        This method is invoked prior to the encrypt() method above.
        Implementors should fill out the supplied 'kek_meta_dto' instance
        (an instance of KEKMetadata above) as needed to completely describe
        the kek metadata and to complete the binding process. Barbican will
        persist the contents of this instance once this method returns.

        :param kek_meta_dto: Key encryption key metadata to bind, with the
               'kek_label' attribute guaranteed to be unique, and the
               and 'plugin_name' attribute already configured.
        :returns: kek_meta_dto: Returns the specified DTO, after
                  modifications.
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def generate_symmetric(self, generate_dto, kek_meta_dto, keystone_id):
        """Generate a new key.

        :param generate_dto: data transfer object for the record
               associated with this generation request.  Some relevant
               parameters can be extracted from this object, including
               bit_length, algorithm and mode
        :param kek_meta_dto: Key encryption key metadata to use for decryption
        :param keystone_id: keystone_id associated with the data.
        :returns: An object of type ResponseDTO containing encrypted data and
        kek_meta_extended, the former the resultant cypher text, the latter
        being optional per-secret metadata needed to decrypt (over and above
        the per-tenant metadata managed outside of the plugins)
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def generate_asymmetric(self, generate_dto,
                            kek_meta_dto, keystone_id):
        """Create a new asymmetric key.

        :param generate_dto: data transfer object for the record
               associated with this generation request.  Some relevant
               parameters can be extracted from this object, including
               bit_length, algorithm and passphrase
        :param kek_meta_dto: Key encryption key metadata to use for decryption
        :param keystone_id: keystone_id associated with the data.
        :returns: A tuple containing  objects for private_key, public_key and
        optionally one for passphrase. The objects will be of type ResponseDTO.
        Each object containing encrypted data and kek_meta_extended, the former
        the resultant cypher text, the latter being optional per-secret
        metadata needed to decrypt (over and above the per-tenant metadata
        managed outside of the plugins)
        """
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def supports(self, type_enum, algorithm=None, bit_length=None,
                 mode=None):
        """Used to determine if the plugin supports the requested operation.

        :param type_enum: Enumeration from PluginSupportsType class
        :param algorithm: String algorithm name if needed
        """
        raise NotImplementedError  # pragma: no cover


class SimpleCryptoPlugin(CryptoPluginBase):
    """Insecure implementation of the crypto plugin."""

    def __init__(self, conf=CONF):
        self.kek = conf.simple_crypto_plugin.kek
        self.block_size = AES.block_size

    def _pad(self, unencrypted):
        """Adds padding to unencrypted byte string."""
        pad_length = self.block_size - (
            len(unencrypted) % self.block_size
        )
        return unencrypted + (chr(pad_length) * pad_length)

    def _strip_pad(self, unencrypted):
        pad_length = ord(unencrypted[-1:])
        unpadded = unencrypted[:-pad_length]
        return unpadded

    def encrypt(self, encrypt_dto, kek_meta_dto, keystone_id):
        unencrypted = encrypt_dto.unencrypted
        if not isinstance(unencrypted, str):
            raise ValueError('Unencrypted data must be a byte type, '
                             'but was {0}'.format(type(unencrypted)))
        padded_data = self._pad(unencrypted)
        iv = Random.get_random_bytes(self.block_size)
        encryptor = AES.new(self.kek, AES.MODE_CBC, iv)

        cyphertext = iv + encryptor.encrypt(padded_data)

        return ResponseDTO(cyphertext, None)

    def decrypt(self, encrypted_dto, kek_meta_dto, kek_meta_extended,
                keystone_id):
        encrypted = encrypted_dto.encrypted
        iv = encrypted[:self.block_size]
        cypher_text = encrypted[self.block_size:]
        decryptor = AES.new(self.kek, AES.MODE_CBC, iv)
        padded_secret = decryptor.decrypt(cypher_text)
        return self._strip_pad(padded_secret)

    def bind_kek_metadata(self, kek_meta_dto):
        kek_meta_dto.algorithm = 'aes'
        kek_meta_dto.bit_length = 128
        kek_meta_dto.mode = 'cbc'
        kek_meta_dto.plugin_meta = None
        return kek_meta_dto

    def generate_symmetric(self, generate_dto, kek_meta_dto, keystone_id):
        byte_length = int(generate_dto.bit_length) / 8
        unencrypted = Random.get_random_bytes(byte_length)

        return self.encrypt(EncryptDTO(unencrypted),
                            kek_meta_dto,
                            keystone_id)

    def generate_asymmetric(self, generate_dto, kek_meta_dto, keystone_id):
        """Generate asymmetric keys based on below rule
        - RSA, with passphrase (supported)
        - RSA, without passphrase (supported)
        - DSA, without passphrase (supported)
        - DSA, with passphrase (not supported)

        Note: PyCrypto is not capable of serializing DSA
        keys and DER formated keys. Such keys will be
        serialized to Base64 PEM to store in DB.

        TODO (atiwari/reaperhulk): PyCrypto is not capable to serialize
        DSA keys and DER formated keys, later we need to pick better
        crypto lib.
        """
        if generate_dto.algorithm is None\
                or generate_dto.algorithm.lower() == 'rsa':
            private_key = RSA.generate(
                generate_dto.bit_length, None, None, 65537)
        elif generate_dto.algorithm.lower() == 'dsa':
            private_key = DSA.generate(generate_dto.bit_length, None, None)

        public_key = private_key.publickey()

        # Note (atiwari): key wrapping format PEM only supported
        if generate_dto.algorithm.lower() == 'rsa':
            public_key, private_key = self._wrap_key(public_key, private_key,
                                                     generate_dto.passphrase)
        if generate_dto.algorithm.lower() == 'dsa':
            if generate_dto.passphrase:
                raise ValueError('Passphrase not supported for DSA key')
            public_key, private_key = self._serialize_dsa_key(public_key,
                                                              private_key)
        private_dto = self.encrypt(EncryptDTO(private_key),
                                   kek_meta_dto,
                                   keystone_id)

        public_dto = self.encrypt(EncryptDTO(public_key),
                                  kek_meta_dto,
                                  keystone_id)

        passphrase_dto = None
        if generate_dto.passphrase:
            passphrase_dto = self.encrypt(EncryptDTO(generate_dto.passphrase),
                                          kek_meta_dto,
                                          keystone_id)

        return private_dto, public_dto, passphrase_dto

    def supports(self, type_enum, algorithm=None, bit_length=None,
                 mode=None):
        if type_enum == PluginSupportTypes.ENCRYPT_DECRYPT:
            return True

        if type_enum == PluginSupportTypes.SYMMETRIC_KEY_GENERATION:
            return self._is_algorithm_supported(algorithm,
                                                bit_length)
        elif type_enum == PluginSupportTypes.ASYMMETRIC_KEY_GENERATION:
            return self._is_algorithm_supported(algorithm,
                                                bit_length)
        else:
            return False

    def _wrap_key(self, public_key, private_key,
                  passphrase):
        pkcs = 8
        key_wrap_format = 'PEM'

        private_key = private_key.exportKey(key_wrap_format, passphrase, pkcs)
        public_key = public_key.exportKey()

        return (public_key, private_key)

    def _serialize_dsa_key(self, public_key, private_key):

        pub_seq = asn1.DerSequence()
        pub_seq[:] = [0, public_key.p, public_key.q,
                      public_key.g, public_key.y]
        public_key = "-----BEGIN DSA PUBLIC KEY-----\n%s"\
            "-----END DSA PUBLIC KEY-----" % pub_seq.encode().encode("base64")

        prv_seq = asn1.DerSequence()
        prv_seq[:] = [0, private_key.p, private_key.q,
                      private_key.g, private_key.y, private_key.x]
        private_key = "-----BEGIN DSA PRIVATE KEY-----\n%s"\
            "-----END DSA PRIVATE KEY-----" % prv_seq.encode().encode("base64")

        return (public_key, private_key)

    def _is_algorithm_supported(self, algorithm=None, bit_length=None):
        """check if algorithm and bit_length combination is supported."""
        if algorithm is None or bit_length is None:
            return False

        if algorithm.lower() in PluginSupportTypes.SYMMETRIC_ALGORITHMS \
                and bit_length in PluginSupportTypes.SYMMETRIC_KEY_LENGTHS:
            return True
        elif algorithm.lower() in PluginSupportTypes.ASYMMETRIC_ALGORITHMS \
                and bit_length in PluginSupportTypes.ASYMMETRIC_KEY_LENGTHS:
            return True
        else:
            return False

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import create_engine, pool
from barbican.model.models import BASE

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# Note that the 'config' instance is not available in for unit testing.
try:
    config = context.config
except Exception:
    config = None


# WARNING! The following was autogenerated by Alembic as part of setting up
#   the initial environment. Unfortunately it also **clobbers** the logging
#   for the rest of this applicaton, so please do not use it!
# Interpret the config file for Python logging.
# This line sets up loggers basically.
#fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = BASE.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_sqlalchemy_url():
    return config.barbican_sqlalchemy_url or config \
                 .get_main_option("sqlalchemy.url")


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(url=get_sqlalchemy_url())

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = create_engine(
        get_sqlalchemy_url(),
        poolclass=pool.NullPool)
    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


if config:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()

########NEW FILE########
__FILENAME__ = 13d127569afa_create_secret_store_metadata_table
# Copyright (c) 2014 The Johns Hopkins University/Applied Physics Laboratory
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

"""create_secret_store_metadata_table

Revision ID: 13d127569afa
Revises: 1a0c2cdafb38
Create Date: 2014-04-24 13:15:41.858266

"""

# revision identifiers, used by Alembic.
revision = '13d127569afa'
down_revision = '1a0c2cdafb38'

from alembic import op
import sqlalchemy as sa

from barbican.model import repositories as rep


def upgrade():
    meta = sa.MetaData()
    meta.reflect(bind=rep._ENGINE, only=['secret_store_metadata'])
    if 'secret_store_metadata' not in meta.tables.keys():
        op.create_table(
            'secret_store_metadata',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('deleted', sa.Boolean(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('secret_id', sa.String(length=36), nullable=False),
            sa.Column('key', sa.String(length=255), nullable=False),
            sa.Column('value', sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(['secret_id'], ['secrets.id'],),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade():
    op.drop_table('secret_store_metadata')

########NEW FILE########
__FILENAME__ = 1a0c2cdafb38_initial_version
"""create test table

   Revision ID: 1a0c2cdafb38
   Revises: None
   Create Date: 2013-06-17 16:42:13.634746

"""

# revision identifiers, used by Alembic.
revision = '1a0c2cdafb38'
down_revision = None


def upgrade():
    pass


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = commands
"""
Interace to the Alembic migration process and environment.

Concepts in this file are based on Quantum's Alembic approach.

Available Alembic commands are detailed here:
https://alembic.readthedocs.org/en/latest/api.html#module-alembic.command
"""

import os

from alembic import command as alembic_command
from alembic import config as alembic_config
from oslo.config import cfg

from barbican.common import utils

LOG = utils.getLogger(__name__)


db_opts = [
    cfg.StrOpt('sql_connection', default=None),
]

CONF = cfg.CONF
CONF.register_opts(db_opts)


def init_config(sql_url=None):
    """Initialize and return the Alembic configuration."""
    sqlalchemy_url = sql_url or CONF.sql_connection
    if 'sqlite' in sqlalchemy_url:
        LOG.warn('!!! No support for migrating sqlite databases...'
                 'skipping migration processing !!!')
        return None

    config = alembic_config.Config(
        os.path.join(os.path.dirname(__file__), 'alembic.ini')
    )
    config.barbican_sqlalchemy_url = sqlalchemy_url
    config.set_main_option('script_location',
                           'barbican.model.migration:alembic_migrations')
    return config


def upgrade(to_version='head', sql_url=None):
    """Upgrade to the specified version."""
    alembic_cfg = init_config(sql_url)
    if alembic_cfg:
        alembic_command.upgrade(alembic_cfg, to_version)


def downgrade(to_version, sql_url=None):
    """Downgrade to the specified version."""
    alembic_cfg = init_config(sql_url)
    if alembic_cfg:
        alembic_command.downgrade(alembic_cfg, to_version)


def stamp(to_version='head', sql_url=None):
    """Stamp the specified version, with no migration performed."""
    alembic_cfg = init_config(sql_url)
    if alembic_cfg:
        alembic_command.stamp(alembic_cfg, to_version)


def generate(autogenerate=True, message='generate changes', sql_url=None):
    """Generate a version file."""
    alembic_cfg = init_config(sql_url)
    if alembic_cfg:
        alembic_command.revision(alembic_cfg, message=message,
                                 autogenerate=autogenerate)

########NEW FILE########
__FILENAME__ = models
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Defines database models for Barbican
"""
import sqlalchemy as sa
from sqlalchemy.ext import compiler
from sqlalchemy.ext import declarative
from sqlalchemy import orm

from barbican.common import exception
from barbican.common import utils
from barbican.openstack.common import timeutils


LOG = utils.getLogger(__name__)
BASE = declarative.declarative_base()


# Allowed entity states
class States(object):
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'
    ERROR = 'ERROR'

    @classmethod
    def is_valid(cls, state_to_test):
        """Tests if a state is a valid one."""
        return state_to_test in cls.__dict__


@compiler.compiles(sa.BigInteger, 'sqlite')
def compile_big_int_sqlite(type_, compiler, **kw):
    return 'INTEGER'


class ModelBase(object):
    """Base class for Nova and Barbican Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False
    __protected_attributes__ = set([
        "created_at", "updated_at", "deleted_at", "deleted"])

    id = sa.Column(sa.String(36), primary_key=True,
                   default=utils.generate_uuid)

    created_at = sa.Column(sa.DateTime, default=timeutils.utcnow,
                           nullable=False)
    updated_at = sa.Column(sa.DateTime, default=timeutils.utcnow,
                           nullable=False, onupdate=timeutils.utcnow)
    deleted_at = sa.Column(sa.DateTime)
    deleted = sa.Column(sa.Boolean, nullable=False, default=False)

    status = sa.Column(sa.String(20), nullable=False, default=States.PENDING)

    def save(self, session=None):
        """Save this object."""
        # import api here to prevent circular dependency problem
        import barbican.model.repositories
        session = session or barbican.model.repositories.get_session()
        session.add(self)
        session.flush()

    def delete(self, session=None):
        """Delete this object."""
        import barbican.model.repositories
        session = session or barbican.model.repositories.get_session()
        self.deleted = True
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)

        self._do_delete_children(session)

    def _do_delete_children(self, session):
        """Sub-class hook: delete children relationships."""
        pass

    def update(self, values):
        """dict.update() behaviour."""
        for k, v in values.iteritems():
            self[k] = v

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __iter__(self):
        self._i = iter(orm.object_mapper(self).sa.Columns)
        return self

    def next(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        return self.__dict__.copy()

    def to_dict_fields(self):
        """Returns a dictionary of just the db fields of this entity."""
        dict_fields = {'created': self.created_at,
                       'updated': self.updated_at,
                       'status': self.status}
        if self.deleted_at:
            dict_fields['deleted'] = self.deleted_at
        if self.deleted:
            dict_fields['is_deleted'] = True
        dict_fields.update(self._do_extra_dict_fields())
        return dict_fields

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {}


class TenantSecret(BASE, ModelBase):
    """Represents an association between a Tenant and a Secret."""

    __tablename__ = 'tenant_secret'

    tenant_id = sa.Column(sa.String(36), sa.ForeignKey('tenants.id'),
                          primary_key=True)
    secret_id = sa.Column(sa.String(36), sa.ForeignKey('secrets.id'),
                          primary_key=True)
    role = sa.Column(sa.String(255))
    secret = orm.relationship("Secret", backref="tenant_assocs")

    __table_args__ = (sa.UniqueConstraint('tenant_id', 'secret_id',
                                          name='_tenant_secret_uc'),)


class ContainerSecret(BASE):
    """Represents an association between a Container and a Secret."""

    __tablename__ = 'container_secret'

    container_id = sa.Column(sa.String(36), sa.ForeignKey('containers.id'),
                             primary_key=True)
    secret_id = sa.Column(sa.String(36), sa.ForeignKey('secrets.id'),
                          primary_key=True)
    name = sa.Column(sa.String(255), nullable=True)

    container = orm.relationship('Container',
                                 backref=orm.backref('container_secrets',
                                                     lazy='joined'))
    secrets = orm.relationship('Secret',
                               backref=orm.backref('container_secrets'))

    __table_args__ = (sa.UniqueConstraint('container_id', 'secret_id', 'name',
                                          name='_container_secret_name_uc'),)


class Tenant(BASE, ModelBase):
    """Represents a Tenant in the datastore.

    Tenants are users that wish to store secret information within
    Cloudkeep's Barbican.
    """

    __tablename__ = 'tenants'

    keystone_id = sa.Column(sa.String(255), unique=True)

    orders = orm.relationship("Order", backref="tenant")
    secrets = orm.relationship("TenantSecret", backref="tenants")
    keks = orm.relationship("KEKDatum", backref="tenant")
    containers = orm.relationship("Container", backref="tenant")

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'keystone_id': self.keystone_id}


class Secret(BASE, ModelBase):
    """Represents a Secret in the datastore.

    Secrets are any information Tenants wish to store within
    Cloudkeep's Barbican, though the actual encrypted data
    is stored in one or more EncryptedData entities on behalf
    of a Secret.
    """

    __tablename__ = 'secrets'

    name = sa.Column(sa.String(255))
    expiration = sa.Column(sa.DateTime, default=None)
    algorithm = sa.Column(sa.String(255))
    bit_length = sa.Column(sa.Integer)
    mode = sa.Column(sa.String(255))

    # TODO(jwood): Performance - Consider avoiding full load of all
    #   datum attributes here. This is only being done to support the
    #   building of the list of supported content types when secret
    #   metadata is retrieved.
    #   See barbican.api.resources.py::SecretsResource.on_get()
    encrypted_data = orm.relationship("EncryptedDatum", lazy='joined')
    secret_store_metadata = orm.relationship("SecretStoreMetadatum",
                                             lazy='joined')

    def __init__(self, parsed_request=None):
        """Creates secret from a dict."""
        super(Secret, self).__init__()

        if parsed_request:
            self.name = parsed_request.get('name')
            self.expiration = parsed_request.get('expiration')
            self.algorithm = parsed_request.get('algorithm')
            self.bit_length = parsed_request.get('bit_length')
            self.mode = parsed_request.get('mode')

        self.status = States.ACTIVE

    def _do_delete_children(self, session):
        """Sub-class hook: delete children relationships."""
        for datum in self.secret_store_metadata:
            datum.delete(session)

        for datum in self.encrypted_data:
            datum.delete(session)

        for secret_ref in self.container_secrets:
                session.delete(secret_ref)

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'secret_id': self.id,
                'name': self.name or self.id,
                'expiration': self.expiration,
                'algorithm': self.algorithm,
                'bit_length': self.bit_length,
                'mode': self.mode}


class SecretStoreMetadatum(BASE, ModelBase):
    """Represents Secret Store metadatum for a single key-value pair"""

    __tablename__ = "secret_store_metadata"

    secret_id = sa.Column(sa.String(36), sa.ForeignKey('secrets.id'),
                          nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.String(255), nullable=False)

    def __init__(self, secret, key, value):
        super(SecretStoreMetadatum, self).__init__()

        msg = ("Must supply non-None {0} argument "
               "for SecretStoreMetadatum entry.")

        if secret is None:
            raise exception.MissingArgumentError(msg.format("secret"))
        self.secret_id = secret.id

        if key is None:
            raise exception.MissingArgumentError(msg.format("key"))
        self.key = key

        if value is None:
            raise exception.MissingArgumentError(msg.format("value"))
        self.value = value

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'key': self.key,
                'value': self.value}


class EncryptedDatum(BASE, ModelBase):
    """Represents the encrypted data for a Secret."""

    __tablename__ = 'encrypted_data'

    secret_id = sa.Column(sa.String(36), sa.ForeignKey('secrets.id'),
                          nullable=False)
    kek_id = sa.Column(sa.String(36), sa.ForeignKey('kek_data.id'),
                       nullable=False)
    content_type = sa.Column(sa.String(255))

    # TODO(jwood) Why LargeBinary on Postgres (BYTEA) not work correctly?
    cypher_text = sa.Column(sa.Text)

    kek_meta_extended = sa.Column(sa.Text)
    kek_meta_tenant = orm.relationship("KEKDatum")

    def __init__(self, secret=None, kek_datum=None):
        """Creates encrypted datum from a secret and KEK metadata."""
        super(EncryptedDatum, self).__init__()

        if secret:
            self.secret_id = secret.id

        if kek_datum:
            self.kek_id = kek_datum.id
            self.kek_meta_tenant = kek_datum

        self.status = States.ACTIVE

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'content_type': self.content_type}


class KEKDatum(BASE, ModelBase):
    """Key encryption key (KEK) metadata model.

    Represents the key encryption key (KEK) metadata associated with a process
    used to encrypt/decrypt secret information.

    When a secret is encrypted, in addition to the cypher text, the Barbican
    encryption process produces a KEK metadata object. The cypher text is
    stored via the EncryptedDatum model above, whereas the metadata is stored
    within this model. Decryption processes utilize this KEK metadata
    to decrypt the associated cypher text.

    Note that this model is intended to be agnostic to the specific means used
    to encrypt/decrypt the secret information, so please do not place vendor-
    specific attributes here.

    Note as well that each Tenant will have at most one 'active=True' KEKDatum
    instance at a time, representing the most recent KEK metadata instance
    to use for encryption processes performed on behalf of the Tenant.
    KEKDatum instances that are 'active=False' are associated to previously
    used encryption processes for the Tenant, that eventually should be
    rotated and deleted with the Tenant's active KEKDatum.
    """

    __tablename__ = 'kek_data'

    plugin_name = sa.Column(sa.String(255))
    kek_label = sa.Column(sa.String(255))

    tenant_id = sa.Column(sa.String(36), sa.ForeignKey('tenants.id'),
                          nullable=False)

    active = sa.Column(sa.Boolean, nullable=False, default=True)
    bind_completed = sa.Column(sa.Boolean, nullable=False, default=False)
    algorithm = sa.Column(sa.String(255))
    bit_length = sa.Column(sa.Integer)
    mode = sa.Column(sa.String(255))
    plugin_meta = sa.Column(sa.Text)

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'algorithm': self.algorithm}


class Order(BASE, ModelBase):
    """Represents an Order in the datastore.

    Orders are requests for Barbican to create secret information,
    ranging from simple AES key generation requests to automated
    requests to Certificate Authorities to generate SSL certificates.
    """

    __tablename__ = 'orders'

    tenant_id = sa.Column(sa.String(36), sa.ForeignKey('tenants.id'),
                          nullable=False)

    error_status_code = sa.Column(sa.String(16))
    error_reason = sa.Column(sa.String(255))

    secret_name = sa.Column(sa.String(255))
    secret_algorithm = sa.Column(sa.String(255))
    secret_bit_length = sa.Column(sa.Integer)
    secret_mode = sa.Column(sa.String(255))
    secret_payload_content_type = sa.Column(sa.String(255), nullable=False)
    secret_expiration = sa.Column(sa.DateTime, default=None)

    secret_id = sa.Column(sa.String(36), sa.ForeignKey('secrets.id'),
                          nullable=True)

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        ret = {'secret': {'name': self.secret_name or self.secret_id,
                          'algorithm': self.secret_algorithm,
                          'bit_length': self.secret_bit_length,
                          'mode': self.secret_mode,
                          'expiration': self.secret_expiration,
                          'payload_content_type':
                          self.secret_payload_content_type},
               'secret_id': self.secret_id,
               'order_id': self.id}
        if self.error_status_code:
            ret['error_status_code'] = self.error_status_code
        if self.error_reason:
            ret['error_reason'] = self.error_reason
        return ret


class Container(BASE, ModelBase):
    """Represents a Container for Secrets in the datastore.

    Containers store secret references. Containers are owned by Tenants.
    Containers can be generic or have a predefined type. Predefined typed
    containers allow users to store structured key relationship
    inside Barbican.
    """

    __tablename__ = 'containers'

    name = sa.Column(sa.String(255))
    type = sa.Column(sa.Enum('generic', 'rsa', name='container_types'))
    tenant_id = sa.Column(sa.String(36), sa.ForeignKey('tenants.id'),
                          nullable=False)

    def __init__(self, parsed_request=None):
        """Creates a Container entity from a dict."""
        super(Container, self).__init__()

        if parsed_request:
            self.name = parsed_request.get('name')
            self.type = parsed_request.get('type')
            self.status = States.ACTIVE

            secret_refs = parsed_request.get('secret_refs')
            if secret_refs:
                for secret_ref in parsed_request.get('secret_refs'):
                    container_secret = ContainerSecret()
                    container_secret.name = secret_ref.get('name')
                    #TODO(hgedikli) move this into a common location
                    #TODO(hgedikli) validate provided url
                    #TODO(hgedikli) parse out secret_id with regex
                    secret_id = secret_ref.get('secret_ref')
                    if secret_id.endswith('/'):
                        secret_id = secret_id.rsplit('/', 2)[1]
                    elif '/' in secret_id:
                        secret_id = secret_id.rsplit('/', 1)[1]
                    else:
                        secret_id = secret_id
                    container_secret.secret_id = secret_id
                    self.container_secrets.append(container_secret)

    def _do_delete_children(self, session):
        """Sub-class hook: delete children relationships."""
        for container_secret in self.container_secrets:
            session.delete(container_secret)

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'container_id': self.id,
                'name': self.name or self.id,
                'type': self.type,
                'secret_refs': [
                    {
                        'secret_id': container_secret.secret_id,
                        'name': container_secret.name
                        if hasattr(container_secret, 'name') else None
                    } for container_secret in self.container_secrets]}


class TransportKey(BASE, ModelBase):
    """Represents the transport key used for wrapping secrets in transit
    to/from clients when storing/retrieving secrets.
    """

    __tablename__ = 'transport_keys'

    plugin_name = sa.Column(sa.String(255), nullable=False)
    transport_key = sa.Column(sa.Text, nullable=False)

    def __init__(self, plugin_name, transport_key):
        """Creates transport key entity ."""
        super(TransportKey, self).__init__()

        msg = "Must supply non-None {0} argument for TransportKey entry."

        if plugin_name is None:
            raise exception.MissingArgumentError(msg.format("plugin_name"))
        else:
            self.plugin_name = plugin_name

        if transport_key is None:
            raise exception.MissingArgumentError(msg.format("transport_key"))
        else:
            self.transport_key = transport_key

        self.status = States.ACTIVE

    def _do_extra_dict_fields(self):
        """Sub-class hook method: return dict of fields."""
        return {'transport_key_id': self.id,
                'plugin_name': self.plugin_name}

# Keep this tuple synchronized with the models in the file
MODELS = [TenantSecret, Tenant, Secret, EncryptedDatum, Order, Container,
          ContainerSecret, TransportKey]


def register_models(engine):
    """Creates database tables for all models with the given engine."""
    LOG.debug("Models: {0}".format(repr(MODELS)))
    for model in MODELS:
        model.metadata.create_all(engine)


def unregister_models(engine):
    """Drops database tables for all models with the given engine."""
    for model in MODELS:
        model.metadata.drop_all(engine)

########NEW FILE########
__FILENAME__ = repositories
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Defines interface for DB access that Resource controllers may reference

TODO: The top part of this file was 'borrowed' from Glance, but seems
quite intense for sqlalchemy, and maybe could be simplified.
"""


import logging
import time
import uuid

from oslo.config import cfg

import sqlalchemy
from sqlalchemy import or_
import sqlalchemy.orm as sa_orm

from barbican.common import exception
from barbican.common import utils
from barbican.model.migration import commands
from barbican.model import models
from barbican.openstack.common.gettextutils import _
from barbican.openstack.common import timeutils

LOG = utils.getLogger(__name__)


_ENGINE = None
_MAKER = None
_MAX_RETRIES = None
_RETRY_INTERVAL = None
BASE = models.BASE
sa_logger = None


db_opts = [
    cfg.IntOpt('sql_idle_timeout', default=3600),
    cfg.IntOpt('sql_max_retries', default=60),
    cfg.IntOpt('sql_retry_interval', default=1),
    cfg.BoolOpt('db_auto_create', default=True),
    cfg.StrOpt('sql_connection', default=None),
    cfg.IntOpt('max_limit_paging', default=100),
    cfg.IntOpt('default_limit_paging', default=10),
]

CONF = cfg.CONF
CONF.register_opts(db_opts)
CONF.import_opt('debug', 'barbican.openstack.common.log')

_CONNECTION = None
_IDLE_TIMEOUT = None


def setup_db_env():
    """Setup configuration for database."""
    global sa_logger, _IDLE_TIMEOUT, _MAX_RETRIES, _RETRY_INTERVAL, _CONNECTION

    _IDLE_TIMEOUT = CONF.sql_idle_timeout
    _MAX_RETRIES = CONF.sql_max_retries
    _RETRY_INTERVAL = CONF.sql_retry_interval
    _CONNECTION = CONF.sql_connection
    LOG.debug("Sql connection = {0}".format(_CONNECTION))
    sa_logger = logging.getLogger('sqlalchemy.engine')
    if CONF.debug:
        sa_logger.setLevel(logging.DEBUG)


def configure_db():
    """Establish the database, create an engine if needed, and
    register the models.
    """
    setup_db_env()
    get_engine()


def get_session(autocommit=True, expire_on_commit=False):
    """Helper method to grab session."""
    global _MAKER
    if not _MAKER:
        get_engine()
        get_maker(autocommit, expire_on_commit)
        assert(_MAKER)
    session = _MAKER()
    return session


def get_engine():
    """Return a SQLAlchemy engine."""
    """May assign _ENGINE if not already assigned"""
    global _ENGINE, sa_logger, _CONNECTION, _IDLE_TIMEOUT, _MAX_RETRIES, \
        _RETRY_INTERVAL

    if not _ENGINE:
        if not _CONNECTION:
            raise exception.BarbicanException('No _CONNECTION configured')

    #TODO(jfwood) connection_dict = sqlalchemy.engine.url.make_url(_CONNECTION)

        engine_args = {
            'pool_recycle': _IDLE_TIMEOUT,
            'echo': False,
            'convert_unicode': True}

        try:
            LOG.debug("Sql connection: {0}; Args: {1}".format(_CONNECTION,
                                                              engine_args))
            _ENGINE = sqlalchemy.create_engine(_CONNECTION, **engine_args)

        #TODO(jfwood): if 'mysql' in connection_dict.drivername:
        #TODO(jfwood): sqlalchemy.event.listen(_ENGINE, 'checkout',
        #TODO(jfwood):                         ping_listener)

            _ENGINE.connect = wrap_db_error(_ENGINE.connect)
            _ENGINE.connect()
        except Exception as err:
            msg = _("Error configuring registry database with supplied "
                    "sql_connection. Got error: %s") % err
            LOG.exception(msg)
            raise

        sa_logger = logging.getLogger('sqlalchemy.engine')
        if CONF.debug:
            sa_logger.setLevel(logging.DEBUG)

        if CONF.db_auto_create:
            meta = sqlalchemy.MetaData()
            meta.reflect(bind=_ENGINE)
            tables = meta.tables
            if tables and 'alembic_version' in tables:
                # Upgrade the database to the latest version.
                LOG.info(_('Updating schema to latest version'))
                commands.upgrade()
            else:
                # Create database tables from our models.
                LOG.info(_('Auto-creating barbican registry DB'))
                models.register_models(_ENGINE)

                # Sync the alembic version 'head' with current models.
                commands.stamp()

        else:
            LOG.info(_('not auto-creating barbican registry DB'))

    return _ENGINE


def get_maker(autocommit=True, expire_on_commit=False):
    """Return a SQLAlchemy sessionmaker."""
    """May assign __MAKER if not already assigned"""
    global _MAKER, _ENGINE
    assert _ENGINE
    if not _MAKER:
        _MAKER = sa_orm.sessionmaker(bind=_ENGINE,
                                     autocommit=autocommit,
                                     expire_on_commit=expire_on_commit)
    return _MAKER


def is_db_connection_error(args):
    """Return True if error in connecting to db."""
    # NOTE(adam_g): This is currently MySQL specific and needs to be extended
    #               to support Postgres and others.
    conn_err_codes = ('2002', '2003', '2006')
    for err_code in conn_err_codes:
        if args.find(err_code) != -1:
            return True
    return False


def wrap_db_error(f):
    """Retry DB connection. Copied from nova and modified."""
    def _wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlalchemy.exc.OperationalError as e:
            if not is_db_connection_error(e.args[0]):
                raise

            remaining_attempts = _MAX_RETRIES
            while True:
                LOG.warning(_('SQL connection failed. %d attempts left.'),
                            remaining_attempts)
                remaining_attempts -= 1
                time.sleep(_RETRY_INTERVAL)
                try:
                    return f(*args, **kwargs)
                except sqlalchemy.exc.OperationalError as e:
                    if (remaining_attempts == 0 or not
                            is_db_connection_error(e.args[0])):
                        raise
                except sqlalchemy.exc.DBAPIError:
                    raise
        except sqlalchemy.exc.DBAPIError:
            raise
    _wrap.func_name = f.func_name
    return _wrap


def clean_paging_values(offset_arg=0, limit_arg=CONF.default_limit_paging):
    """Cleans and safely limits raw paging offset/limit values."""
    offset_arg = offset_arg or 0
    limit_arg = limit_arg or CONF.default_limit_paging

    try:
        offset = int(offset_arg)
        offset = offset if offset >= 0 else 0
    except ValueError:
        offset = 0

    try:
        limit = int(limit_arg)
        if limit < 1:
            limit = 1
        if limit > CONF.max_limit_paging:
            limit = CONF.max_limit_paging
    except ValueError:
        limit = CONF.default_limit_paging

    LOG.debug("Clean paging values limit={0}, offset={1}".format(
        limit, offset
    ))

    return offset, limit


class BaseRepo(object):
    """Base repository for the barbican entities.

    This class provides template methods that allow sub-classes to hook
    specific functionality as needed.
    """

    def __init__(self):
        LOG.debug("BaseRepo init...")
        configure_db()

    def get_session(self, session=None):
        LOG.debug("Getting session...")
        return session or get_session()

    def get(self, entity_id, keystone_id=None,
            force_show_deleted=False,
            suppress_exception=False, session=None):
        """Get an entity or raise if it does not exist."""
        session = self.get_session(session)

        try:
            query = self._do_build_get_query(entity_id,
                                             keystone_id, session)

            # filter out deleted entities if requested
            if not force_show_deleted:
                query = query.filter_by(deleted=False)

            entity = query.one()

        except sa_orm.exc.NoResultFound:
            LOG.exception("Not found for {0}".format(entity_id))
            entity = None
            if not suppress_exception:
                raise exception.NotFound("No %s found with ID %s"
                                         % (self._do_entity_name(), entity_id))

        return entity

    def create_from(self, entity):
        """Sub-class hook: create from entity."""
        start = time.time()  # DEBUG
        if not entity:
            msg = "Must supply non-None {0}.".format(self._do_entity_name)
            raise exception.Invalid(msg)

        if entity.id:
            msg = "Must supply {0} with id=None(i.e. new entity).".format(
                self._do_entity_name)
            raise exception.Invalid(msg)

        LOG.debug("Begin create from...")
        session = get_session()
        with session.begin():

            # Validate the attributes before we go any further. From my
            # (unknown Glance developer) investigation, the @validates
            # decorator does not validate
            # on new records, only on existing records, which is, well,
            # idiotic.
            values = self._do_validate(entity.to_dict())

            try:
                LOG.debug("Saving entity...")
                entity.save(session=session)
            except sqlalchemy.exc.IntegrityError:
                LOG.exception('Problem saving entity for create')
                raise exception.Duplicate("Entity ID %s already exists!"
                                          % values['id'])
        LOG.debug('Elapsed repo '
                  'create secret:{0}'.format(time.time() - start))  # DEBUG

        return entity

    def save(self, entity):
        """Saves the state of the entity.

        :raises NotFound if entity does not exist.
        """
        session = get_session()
        with session.begin():
            entity.updated_at = timeutils.utcnow()

            # Validate the attributes before we go any further. From my
            # (unknown Glance developer) investigation, the @validates
            # decorator does not validate
            # on new records, only on existing records, which is, well,
            # idiotic.
            self._do_validate(entity.to_dict())

            try:
                entity.save(session=session)
            except sqlalchemy.exc.IntegrityError:
                LOG.exception('Problem saving entity for update')
                raise exception.NotFound("Entity ID %s not found"
                                         % entity.id)

    def update(self, entity_id, values, purge_props=False):
        """Set the given properties on an entity and update it.

        :raises NotFound if entity does not exist.
        """
        return self._update(entity_id, values, purge_props)

    def delete_entity_by_id(self, entity_id, keystone_id):
        """Remove the entity by its ID."""

        session = get_session()
        with session.begin():

            entity = self.get(entity_id=entity_id, keystone_id=keystone_id,
                              session=session)

            try:
                entity.delete(session=session)
            except sqlalchemy.exc.IntegrityError:
                LOG.exception('Problem finding entity to delete')
                raise exception.NotFound("Entity ID %s not found"
                                         % entity_id)

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "Entity"

    def _do_create_instance(self):
        """Sub-class hook: return new entity instance (in Python, not in db).
        """
        return None

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return None

    def _do_convert_values(self, values):
        """Sub-class hook: convert text-based values to target types for the
        database.
        """
        pass

    def _do_validate(self, values):
        """Sub-class hook: validate values.

        Validates the incoming data and raises a Invalid exception
        if anything is out of order.

        :param values: Mapping of entity metadata to check
        """
        status = values.get('status', None)
        if not status:
            #TODO(jfwood): I18n this!
            msg = "{0} status is required.".format(self._do_entity_name())
            raise exception.Invalid(msg)

        if not models.States.is_valid(status):
            msg = "Invalid status '{0}' for {1}.".format(
                status, self._do_entity_name())
            raise exception.Invalid(msg)

        return values

    def _update(self, entity_id, values, purge_props=False):
        """Used internally by update()

        :param values: A dict of attributes to set
        :param entity_id: If None, create the entity, otherwise,
                          find and update it
        """
        session = get_session()
        with session.begin():

            if entity_id:
                entity_ref = self.get(entity_id, session=session)
                values['updated_at'] = timeutils.utcnow()
            else:
                self._do_convert_values(values)
                entity_ref = self._do_create_instance()

            # Need to canonicalize ownership
            if 'owner' in values and not values['owner']:
                values['owner'] = None

            entity_ref.update(values)

            # Validate the attributes before we go any further. From my
            # (unknown Glance developer) investigation, the @validates
            # decorator does not validate
            # on new records, only on existing records, which is, well,
            # idiotic.
            self._do_validate(entity_ref.to_dict())
            self._update_values(entity_ref, values)

            try:
                entity_ref.save(session=session)
            except sqlalchemy.exc.IntegrityError:
                LOG.exception('Problem saving entity for _update')
                if entity_id:
                    raise exception.NotFound("Entity ID %s not found"
                                             % entity_id)
                else:
                    raise exception.Duplicate("Entity ID %s already exists!"
                                              % values['id'])

        return self.get(entity_ref.id)

    def _update_values(self, entity_ref, values):
        for k in values:
            if getattr(entity_ref, k) != values[k]:
                setattr(entity_ref, k, values[k])


class TenantRepo(BaseRepo):
    """Repository for the Tenant entity."""

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "Tenant"

    def _do_create_instance(self):
        return models.Tenant()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.Tenant).filter_by(id=entity_id)

    def find_by_keystone_id(self, keystone_id, suppress_exception=False,
                            session=None):
        session = self.get_session(session)

        try:
            query = session.query(models.Tenant).filter_by(keystone_id=
                                                           keystone_id)

            entity = query.one()

        except sa_orm.exc.NoResultFound:
            LOG.exception("Problem getting Tenant {0}".format(keystone_id))
            entity = None
            if not suppress_exception:
                raise exception.NotFound("No %s found with keystone-ID %s"
                                         % (self._do_entity_name(),
                                            keystone_id))

        return entity


class SecretRepo(BaseRepo):
    """Repository for the Secret entity."""

    def get_by_create_date(self, keystone_id, offset_arg=None, limit_arg=None,
                           name=None, alg=None, mode=None, bits=0,
                           suppress_exception=False, session=None):
        """Returns a list of secrets, ordered by the date they were created at
        and paged based on the offset and limit fields. The keystone_id is
        external-to-Barbican value assigned to the tenant by Keystone.
        """

        offset, limit = clean_paging_values(offset_arg, limit_arg)

        session = self.get_session(session)
        utcnow = timeutils.utcnow()

        try:
            query = session.query(models.Secret) \
                           .order_by(models.Secret.created_at) \
                           .filter_by(deleted=False)

            # Note: Must use '== None' below, not 'is None'.
            query = query.filter(or_(models.Secret.expiration == None,
                                     models.Secret.expiration > utcnow))

            if name:
                query = query.filter(models.Secret.name.like(name))
            if alg:
                query = query.filter(models.Secret.algorithm.like(alg))
            if mode:
                query = query.filter(models.Secret.mode.like(mode))
            if bits > 0:
                query = query.filter(models.Secret.bit_length == bits)

            query = query.join(models.TenantSecret,
                               models.Secret.tenant_assocs) \
                         .join(models.Tenant, models.TenantSecret.tenants) \
                         .filter(models.Tenant.keystone_id == keystone_id)

            start = offset
            end = offset + limit
            LOG.debug('Retrieving from {0} to {1}'.format(start, end))
            total = query.count()
            entities = query[start:end]
            LOG.debug('Number entities retrieved: {0} out of {1}'.format(
                len(entities), total
            ))

        except sa_orm.exc.NoResultFound:
            entities = None
            total = 0
            if not suppress_exception:
                raise exception.NotFound("No %s's found"
                                         % (self._do_entity_name()))

        return entities, offset, limit, total

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "Secret"

    def _do_create_instance(self):
        return models.Secret()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        utcnow = timeutils.utcnow()

        # Note: Must use '== None' below, not 'is None'.
        # TODO(jfwood): Performance? Is the many-to-many join needed?
        return session.query(models.Secret).filter_by(id=entity_id) \
                      .filter_by(deleted=False) \
                      .filter(or_(models.Secret.expiration == None,
                                  models.Secret.expiration > utcnow)) \
                      .join(models.TenantSecret, models.Secret.tenant_assocs)\
                      .join(models.Tenant, models.TenantSecret.tenants) \
                      .filter(models.Tenant.keystone_id == keystone_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass


class EncryptedDatumRepo(BaseRepo):
    """Repository for the EncryptedDatum entity (that stores encrypted
    information on behalf of a Secret).
    """

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "EncryptedDatum"

    def _do_create_instance(self):
        return models.EncryptedDatum()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.EncryptedDatum).filter_by(id=entity_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass


class KEKDatumRepo(BaseRepo):
    """Repository for the KEKDatum entity (that stores key encryption key (KEK)
    metadata used by crypto plugins to encrypt/decrypt secrets).
    """

    def find_or_create_kek_datum(self, tenant,
                                 plugin_name,
                                 suppress_exception=False,
                                 session=None):
        """Find or create a KEK datum instance."""

        kek_datum = None

        session = self.get_session(session)

        # TODO(jfwood): Reverse this...attempt insert first, then get on fail.
        try:
            query = session.query(models.KEKDatum) \
                           .filter_by(tenant_id=tenant.id) \
                           .filter_by(plugin_name=plugin_name) \
                           .filter_by(active=True) \
                           .filter_by(deleted=False)

            kek_datum = query.one()

        except sa_orm.exc.NoResultFound:
            kek_datum = models.KEKDatum()

            kek_datum.kek_label = "tenant-{0}-key-{1}".format(
                tenant.keystone_id, uuid.uuid4())
            kek_datum.tenant_id = tenant.id
            kek_datum.plugin_name = plugin_name
            kek_datum.status = models.States.ACTIVE

            self.save(kek_datum)

        return kek_datum

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "KEKDatum"

    def _do_create_instance(self):
        return models.KEKDatum()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.KEKDatum).filter_by(id=entity_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass


class TenantSecretRepo(BaseRepo):
    """Repository for the TenantSecret entity."""

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "TenantSecret"

    def _do_create_instance(self):
        return models.TenantSecret()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.TenantSecret).filter_by(id=entity_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass


class OrderRepo(BaseRepo):
    """Repository for the Order entity."""

    def get_by_create_date(self, keystone_id, offset_arg=None, limit_arg=None,
                           suppress_exception=False, session=None):
        """Returns a list of orders, ordered by the date they were created at
        and paged based on the offset and limit fields.

        :param keystone_id: The keystone id for the tenant.
        :param offset_arg: The entity number where the query result should
                           start.
        :param limit_arg: The maximum amount of entities in the result set.
        :param suppress_exception: Whether NoResultFound exceptions should be
                                   suppressed.
        :param session: SQLAlchemy session object.

        :returns: Tuple consisting of (list_of_entities, offset, limit, total).
        """

        offset, limit = clean_paging_values(offset_arg, limit_arg)

        session = self.get_session(session)

        try:
            query = session.query(models.Order) \
                           .order_by(models.Order.created_at)
            query = query.filter_by(deleted=False) \
                         .join(models.Tenant, models.Order.tenant) \
                         .filter(models.Tenant.keystone_id == keystone_id)

            start = offset
            end = offset + limit
            LOG.debug('Retrieving from {0} to {1}'.format(start, end))
            total = query.count()
            entities = query[start:end]
            LOG.debug('Number entities retrieved: {0} out of {1}'.format(
                len(entities), total
            ))

        except sa_orm.exc.NoResultFound:
            entities = None
            total = 0
            if not suppress_exception:
                raise exception.NotFound("No %s's found"
                                         % (self._do_entity_name()))

        return entities, offset, limit, total

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "Order"

    def _do_create_instance(self):
        return models.Order()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.Order).filter_by(id=entity_id) \
                      .filter_by(deleted=False) \
                      .join(models.Tenant, models.Order.tenant) \
                      .filter(models.Tenant.keystone_id == keystone_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass


class ContainerRepo(BaseRepo):
    """Repository for the Container entity."""

    def get_by_create_date(self, keystone_id, offset_arg=None, limit_arg=None,
                           suppress_exception=False, session=None):
        """Returns a list of containers, ordered by the date they were
        created at and paged based on the offset and limit fields. The
        keystone_id is external-to-Barbican value assigned to the tenant
        by Keystone.
        """

        offset, limit = clean_paging_values(offset_arg, limit_arg)

        session = self.get_session(session)

        try:
            query = session.query(models.Container) \
                           .order_by(models.Container.created_at)
            query = query.filter_by(deleted=False) \
                         .join(models.Tenant, models.Container.tenant) \
                         .filter(models.Tenant.keystone_id == keystone_id)

            start = offset
            end = offset + limit
            LOG.debug('Retrieving from {0} to {1}'.format(start, end))
            total = query.count()
            entities = query[start:end]
            LOG.debug('Number entities retrieved: {0} out of {1}'.format(
                len(entities), total
            ))

        except sa_orm.exc.NoResultFound:
            entities = None
            total = 0
            if not suppress_exception:
                raise exception.NotFound("No %s's found"
                                         % (self._do_entity_name()))

        return entities, offset, limit, total

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "Container"

    def _do_create_instance(self):
        return models.Container()

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.Container).filter_by(id=entity_id)\
            .filter_by(deleted=False)\
            .join(models.Tenant, models.Container.tenant)\
            .filter(models.Tenant.keystone_id == keystone_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass


class TransportKeyRepo(BaseRepo):
    """Repository for the TransportKey entity (that stores transport keys
    for wrapping the secret data to/from a barbican client).
    """

    def _do_entity_name(self):
        """Sub-class hook: return entity name, such as for debugging."""
        return "TransportKey"

    def _do_create_instance(self):
        return models.TransportKey()

    def get_by_create_date(self, plugin_name=None,
                           offset_arg=None, limit_arg=None,
                           suppress_exception=False, session=None):
        """Returns a list of transport keys, ordered from latest created first.
        The search accepts plugin_id as an optional parameter for the search.
        """

        offset, limit = clean_paging_values(offset_arg, limit_arg)

        session = self.get_session(session)

        try:
            query = session.query(models.TransportKey) \
                           .order_by(models.TransportKey.created_at)
            if plugin_name is not None:
                query = session.query(models.TransportKey).\
                    filter_by(deleted=False, plugin_name=plugin_name)
            else:
                query = query.filter_by(deleted=False)

            start = offset
            end = offset + limit
            LOG.debug('Retrieving from {0} to {1}'.format(start, end))
            total = query.count()
            entities = query[start:end]
            LOG.debug('Number of entities retrieved: {0} out of {1}'.format(
                len(entities), total))

        except sa_orm.exc.NoResultFound:
            entities = None
            total = 0
            if not suppress_exception:
                raise exception.NotFound("No {0}'s found".format(
                    self._do_entity_name()))

        return entities, offset, limit, total

    def _do_build_get_query(self, entity_id, keystone_id, session):
        """Sub-class hook: build a retrieve query."""
        return session.query(models.TransportKey).filter_by(id=entity_id)

    def _do_validate(self, values):
        """Sub-class hook: validate values."""
        pass

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


def is_user_context(context):
    """Indicates if the request context is a normal user."""
    if not context:
        return False
    if context.is_admin:
        return False
    if not context.user_id or not context.project_id:
        return False
    return True

########NEW FILE########
__FILENAME__ = utils
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import base64

from Crypto.Hash import HMAC
from Crypto import Random

from barbican.openstack.common.gettextutils import _  # noqa
from barbican.openstack.common import importutils


class CryptoutilsException(Exception):
    """Generic Exception for Crypto utilities."""

    message = _("An unknown error occurred in crypto utils.")


class CipherBlockLengthTooBig(CryptoutilsException):
    """The block size is too big."""

    def __init__(self, requested, permitted):
        msg = _("Block size of %(given)d is too big, max = %(maximum)d")
        message = msg % {'given': requested, 'maximum': permitted}
        super(CryptoutilsException, self).__init__(message)


class HKDFOutputLengthTooLong(CryptoutilsException):
    """The amount of Key Material asked is too much."""

    def __init__(self, requested, permitted):
        msg = _("Length of %(given)d is too long, max = %(maximum)d")
        message = msg % {'given': requested, 'maximum': permitted}
        super(CryptoutilsException, self).__init__(message)


class HKDF(object):
    """An HMAC-based Key Derivation Function implementation (RFC5869)

    This class creates an object that allows to use HKDF to derive keys.
    """

    def __init__(self, hashtype='SHA256'):
        self.hashfn = importutils.import_module('Crypto.Hash.' + hashtype)
        self.max_okm_length = 255 * self.hashfn.digest_size

    def extract(self, ikm, salt=None):
        """An extract function that can be used to derive a robust key given
        weak Input Key Material (IKM) which could be a password.
        Returns a pseudorandom key (of HashLen octets)

        :param ikm: input keying material (ex a password)
        :param salt: optional salt value (a non-secret random value)
        """
        if salt is None:
            salt = '\x00' * self.hashfn.digest_size

        return HMAC.new(salt, ikm, self.hashfn).digest()

    def expand(self, prk, info, length):
        """An expand function that will return arbitrary length output that can
        be used as keys.
        Returns a buffer usable as key material.

        :param prk: a pseudorandom key of at least HashLen octets
        :param info: optional string (can be a zero-length string)
        :param length: length of output keying material (<= 255 * HashLen)
        """
        if length > self.max_okm_length:
            raise HKDFOutputLengthTooLong(length, self.max_okm_length)

        N = (length + self.hashfn.digest_size - 1) / self.hashfn.digest_size

        okm = ""
        tmp = ""
        for block in range(1, N + 1):
            tmp = HMAC.new(prk, tmp + info + chr(block), self.hashfn).digest()
            okm += tmp

        return okm[:length]


MAX_CB_SIZE = 256


class SymmetricCrypto(object):
    """Symmetric Key Crypto object.

    This class creates a Symmetric Key Crypto object that can be used
    to encrypt, decrypt, or sign arbitrary data.

    :param enctype: Encryption Cipher name (default: AES)
    :param hashtype: Hash/HMAC type name (default: SHA256)
    """

    def __init__(self, enctype='AES', hashtype='SHA256'):
        self.cipher = importutils.import_module('Crypto.Cipher.' + enctype)
        self.hashfn = importutils.import_module('Crypto.Hash.' + hashtype)

    def new_key(self, size):
        return Random.new().read(size)

    def encrypt(self, key, msg, b64encode=True):
        """Encrypt the provided msg and returns the cyphertext optionally
        base64 encoded.

        Uses AES-128-CBC with a Random IV by default.

        The plaintext is padded to reach blocksize length.
        The last byte of the block is the length of the padding.
        The length of the padding does not include the length byte itself.

        :param key: The Encryption key.
        :param msg: the plain text.

        :returns encblock: a block of encrypted data.
        """
        iv = Random.new().read(self.cipher.block_size)
        cipher = self.cipher.new(key, self.cipher.MODE_CBC, iv)

        # CBC mode requires a fixed block size. Append padding and length of
        # padding.
        if self.cipher.block_size > MAX_CB_SIZE:
            raise CipherBlockLengthTooBig(self.cipher.block_size, MAX_CB_SIZE)
        r = len(msg) % self.cipher.block_size
        padlen = self.cipher.block_size - r - 1
        msg += '\x00' * padlen
        msg += chr(padlen)

        enc = iv + cipher.encrypt(msg)
        if b64encode:
            enc = base64.b64encode(enc)
        return enc

    def decrypt(self, key, msg, b64decode=True):
        """Decrypts the provided ciphertext, optionally base 64 encoded, and
        returns the plaintext message, after padding is removed.

        Uses AES-128-CBC with an IV by default.

        :param key: The Encryption key.
        :param msg: the ciphetext, the first block is the IV
        """
        if b64decode:
            msg = base64.b64decode(msg)
        iv = msg[:self.cipher.block_size]
        cipher = self.cipher.new(key, self.cipher.MODE_CBC, iv)

        padded = cipher.decrypt(msg[self.cipher.block_size:])
        l = ord(padded[-1]) + 1
        plain = padded[:-l]
        return plain

    def sign(self, key, msg, b64encode=True):
        """Signs a message string and returns a base64 encoded signature.

        Uses HMAC-SHA-256 by default.

        :param key: The Signing key.
        :param msg: the message to sign.
        """
        h = HMAC.new(key, msg, self.hashfn)
        out = h.digest()
        if b64encode:
            out = base64.b64encode(out)
        return out

########NEW FILE########
__FILENAME__ = eventlet_backdoor
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from barbican.openstack.common.gettextutils import _  # noqa
from barbican.openstack.common import log as logging

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
    return filter(lambda o: isinstance(o, t), gc.get_objects())


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

from barbican.openstack.common.gettextutils import _LE


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
            logging.error(_LE('Original exception being dropped: %s'),
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
                        _LE('Unexpected exception occurred %d time(s)... '
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
import tempfile

from barbican.openstack.common import excutils
from barbican.openstack.common import log as logging

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
        LOG.debug("Reloading cached file %s" % filename)
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


def write_to_tempfile(content, path=None, suffix='', prefix='tmp'):
    """Create temporary file or use existing file.

    This util is needed for creating temporary file with
    specified content, suffix and prefix. If path is not None,
    it will be used for writing content. If the path doesn't
    exist it'll be created.

    :param content: content for temporary file.
    :param path: same as parameter 'dir' for mkstemp
    :param suffix: same as parameter 'suffix' for mkstemp
    :param prefix: same as parameter 'prefix' for mkstemp

    For example: it can be used in database tests for creating
    configuration files.
    """
    if path:
        ensure_tree(path)

    (fd, path) = tempfile.mkstemp(suffix=suffix, dir=path, prefix=prefix)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    return path

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

    from barbican.openstack.common.gettextutils import _
"""

import copy
import functools
import gettext
import locale
from logging import handlers
import os
import re

from babel import localedata
import six

_localedir = os.environ.get('barbican'.upper() + '_LOCALEDIR')
_t = gettext.translation('barbican', localedir=_localedir, fallback=True)

# We use separate translation catalogs for each log level, so set up a
# mapping between the log level name and the translator. The domain
# for the log level is project_name + "-log-" + log_level so messages
# for each level end up in their own catalog.
_t_log_levels = dict(
    (level, gettext.translation('barbican' + '-log-' + level,
                                localedir=_localedir,
                                fallback=True))
    for level in ['info', 'warning', 'error', 'critical']
)

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
        return Message(msg, domain='barbican')
    else:
        if six.PY3:
            return _t.gettext(msg)
        return _t.ugettext(msg)


def _log_translation(msg, level):
    """Build a single translation of a log message
    """
    if USE_LAZY:
        return Message(msg, domain='barbican' + '-log-' + level)
    else:
        translator = _t_log_levels[level]
        if six.PY3:
            return translator.gettext(msg)
        return translator.ugettext(msg)

# Translators for log levels.
#
# The abbreviated names are meant to reflect the usual use of a short
# name like '_'. The "L" is for "log" and the other letter comes from
# the level.
_LI = functools.partial(_log_translation, level='info')
_LW = functools.partial(_log_translation, level='warning')
_LE = functools.partial(_log_translation, level='error')
_LC = functools.partial(_log_translation, level='critical')


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
                domain='barbican', *args):
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


def import_versioned_module(version, submodule=None):
    module = 'barbican.v%s' % version
    if submodule:
        module = '.'.join((module, submodule))
    return import_module(module)


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

from barbican.openstack.common import gettextutils
from barbican.openstack.common import importutils
from barbican.openstack.common import timeutils

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

"""OpenStack logging handler.

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

from barbican.openstack.common.gettextutils import _
from barbican.openstack.common import importutils
from barbican.openstack.common import jsonutils
from barbican.openstack.common import local


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
        self._deprecated_messages_sent = dict()

    @property
    def handlers(self):
        return self.logger.handlers

    def deprecated(self, msg, *args, **kwargs):
        """Call this method when a deprecated feature is used.

        If the system is configured for fatal deprecations then the message
        is logged at the 'critical' level and :class:`DeprecatedConfig` will
        be raised.

        Otherwise, the message will be logged (once) at the 'warn' level.

        :raises: :class:`DeprecatedConfig` if the system is configured for
                 fatal deprecations.

        """
        stdmsg = _("Deprecated: %s") % msg
        if CONF.fatal_deprecations:
            self.critical(stdmsg, *args, **kwargs)
            raise DeprecatedConfig(msg=stdmsg)

        # Using a list because a tuple with dict can't be stored in a set.
        sent_args = self._deprecated_messages_sent.setdefault(msg, list())

        if args in sent_args:
            # Already logged this message, so don't log it again.
            return

        sent_args.append(args)
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
        instance_uuid = (extra.get('instance_uuid') or
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
            "barbican.openstack.common.log_handler.PublishErrorsHandler",
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

        if record.__dict__.get('request_id'):
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
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from barbican.openstack.common.gettextutils import _  # noqa
from barbican.openstack.common import log as logging
from barbican.openstack.common import timeutils

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
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import urlparse


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
    scheme, netloc, path, query, fragment = urlparse.urlsplit(
        url, scheme, allow_fragments)
    if allow_fragments and '#' in path:
        path, fragment = path.split('#', 1)
    if '?' in path:
        path, query = path.split('?', 1)
    return urlparse.SplitResult(scheme, netloc, path, query, fragment)

########NEW FILE########
__FILENAME__ = policy
# Copyright (c) 2012 OpenStack Foundation.
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
Common Policy Engine Implementation

Policies can be expressed in one of two forms: A list of lists, or a
string written in the new policy language.

In the list-of-lists representation, each check inside the innermost
list is combined as with an "and" conjunction--for that check to pass,
all the specified checks must pass.  These innermost lists are then
combined as with an "or" conjunction.  This is the original way of
expressing policies, but there now exists a new way: the policy
language.

In the policy language, each check is specified the same way as in the
list-of-lists representation: a simple "a:b" pair that is matched to
the correct code to perform that check.  However, conjunction
operators are available, allowing for more expressiveness in crafting
policies.

As an example, take the following rule, expressed in the list-of-lists
representation::

    [["role:admin"], ["project_id:%(project_id)s", "role:projectadmin"]]

In the policy language, this becomes::

    role:admin or (project_id:%(project_id)s and role:projectadmin)

The policy language also has the "not" operator, allowing a richer
policy rule::

    project_id:%(project_id)s and not role:dunce

It is possible to perform policy checks on the following user
attributes (obtained through the token): user_id, domain_id or
project_id::

    domain_id:<some_value>

Attributes sent along with API calls can be used by the policy engine
(on the right side of the expression), by using the following syntax::

    <some_value>:user.id

Contextual attributes of objects identified by their IDs are loaded
from the database. They are also available to the policy engine and
can be checked through the `target` keyword::

    <some_value>:target.role.name

All these attributes (related to users, API calls, and context) can be
checked against each other or against constants, be it literals (True,
<a_number>) or strings.

Finally, two special policy checks should be mentioned; the policy
check "@" will always accept an access, and the policy check "!" will
always reject an access.  (Note that if a rule is either the empty
list ("[]") or the empty string, this is equivalent to the "@" policy
check.)  Of these, the "!" policy check is probably the most useful,
as it allows particular rules to be explicitly disabled.
"""

import abc
import ast
import re

from oslo.config import cfg
import six
import six.moves.urllib.parse as urlparse
import six.moves.urllib.request as urlrequest

from barbican.openstack.common import fileutils
from barbican.openstack.common.gettextutils import _, _LE
from barbican.openstack.common import jsonutils
from barbican.openstack.common import log as logging


policy_opts = [
    cfg.StrOpt('policy_file',
               default='policy.json',
               help=_('JSON file containing policy')),
    cfg.StrOpt('policy_default_rule',
               default='default',
               help=_('Rule enforced when requested rule is not found')),
]

CONF = cfg.CONF
CONF.register_opts(policy_opts)

LOG = logging.getLogger(__name__)

_checks = {}


class PolicyNotAuthorized(Exception):

    def __init__(self, rule):
        msg = _("Policy doesn't allow %s to be performed.") % rule
        super(PolicyNotAuthorized, self).__init__(msg)


class Rules(dict):
    """A store for rules. Handles the default_rule setting directly."""

    @classmethod
    def load_json(cls, data, default_rule=None):
        """Allow loading of JSON rule data."""

        # Suck in the JSON data and parse the rules
        rules = dict((k, parse_rule(v)) for k, v in
                     jsonutils.loads(data).items())

        return cls(rules, default_rule)

    def __init__(self, rules=None, default_rule=None):
        """Initialize the Rules store."""

        super(Rules, self).__init__(rules or {})
        self.default_rule = default_rule

    def __missing__(self, key):
        """Implements the default rule handling."""

        if isinstance(self.default_rule, dict):
            raise KeyError(key)

        # If the default rule isn't actually defined, do something
        # reasonably intelligent
        if not self.default_rule:
            raise KeyError(key)

        if isinstance(self.default_rule, BaseCheck):
            return self.default_rule

        # We need to check this or we can get infinite recursion
        if self.default_rule not in self:
            raise KeyError(key)

        elif isinstance(self.default_rule, six.string_types):
            return self[self.default_rule]

    def __str__(self):
        """Dumps a string representation of the rules."""

        # Start by building the canonical strings for the rules
        out_rules = {}
        for key, value in self.items():
            # Use empty string for singleton TrueCheck instances
            if isinstance(value, TrueCheck):
                out_rules[key] = ''
            else:
                out_rules[key] = str(value)

        # Dump a pretty-printed JSON representation
        return jsonutils.dumps(out_rules, indent=4)


class Enforcer(object):
    """Responsible for loading and enforcing rules.

    :param policy_file: Custom policy file to use, if none is
                        specified, `CONF.policy_file` will be
                        used.
    :param rules: Default dictionary / Rules to use. It will be
                  considered just in the first instantiation. If
                  `load_rules(True)`, `clear()` or `set_rules(True)`
                  is called this will be overwritten.
    :param default_rule: Default rule to use, CONF.default_rule will
                         be used if none is specified.
    """

    def __init__(self, policy_file=None, rules=None, default_rule=None):
        self.rules = Rules(rules, default_rule)
        self.default_rule = default_rule or CONF.policy_default_rule

        self.policy_path = None
        self.policy_file = policy_file or CONF.policy_file

    def set_rules(self, rules, overwrite=True):
        """Create a new Rules object based on the provided dict of rules.

        :param rules: New rules to use. It should be an instance of dict.
        :param overwrite: Whether to overwrite current rules or update them
                          with the new rules.
        """

        if not isinstance(rules, dict):
            raise TypeError(_("Rules must be an instance of dict or Rules, "
                            "got %s instead") % type(rules))

        if overwrite:
            self.rules = Rules(rules, self.default_rule)
        else:
            self.rules.update(rules)

    def clear(self):
        """Clears Enforcer rules, policy's cache and policy's path."""
        self.set_rules({})
        self.default_rule = None
        self.policy_path = None

    def load_rules(self, force_reload=False):
        """Loads policy_path's rules.

        Policy file is cached and will be reloaded if modified.

        :param force_reload: Whether to overwrite current rules.
        """

        if not self.policy_path:
            self.policy_path = self._get_policy_path()

        reloaded, data = fileutils.read_cached_file(self.policy_path,
                                                    force_reload=force_reload)
        if reloaded or not self.rules:
            rules = Rules.load_json(data, self.default_rule)
            self.set_rules(rules)
            LOG.debug("Rules successfully reloaded")

    def _get_policy_path(self):
        """Locate the policy json data file.

        :param policy_file: Custom policy file to locate.

        :returns: The policy path

        :raises: ConfigFilesNotFoundError if the file couldn't
                 be located.
        """
        policy_file = CONF.find_file(self.policy_file)

        if policy_file:
            return policy_file

        raise cfg.ConfigFilesNotFoundError((self.policy_file,))

    def enforce(self, rule, target, creds, do_raise=False,
                exc=None, *args, **kwargs):
        """Checks authorization of a rule against the target and credentials.

        :param rule: A string or BaseCheck instance specifying the rule
                    to evaluate.
        :param target: As much information about the object being operated
                    on as possible, as a dictionary.
        :param creds: As much information about the user performing the
                    action as possible, as a dictionary.
        :param do_raise: Whether to raise an exception or not if check
                        fails.
        :param exc: Class of the exception to raise if the check fails.
                    Any remaining arguments passed to check() (both
                    positional and keyword arguments) will be passed to
                    the exception class. If not specified, PolicyNotAuthorized
                    will be used.

        :return: Returns False if the policy does not allow the action and
                exc is not provided; otherwise, returns a value that
                evaluates to True.  Note: for rules using the "case"
                expression, this True value will be the specified string
                from the expression.
        """

        # NOTE(flaper87): Not logging target or creds to avoid
        # potential security issues.
        LOG.debug("Rule %s will be now enforced" % rule)

        self.load_rules()

        # Allow the rule to be a Check tree
        if isinstance(rule, BaseCheck):
            result = rule(target, creds, self)
        elif not self.rules:
            # No rules to reference means we're going to fail closed
            result = False
        else:
            try:
                # Evaluate the rule
                result = self.rules[rule](target, creds, self)
            except KeyError:
                LOG.debug("Rule [%s] doesn't exist" % rule)
                # If the rule doesn't exist, fail closed
                result = False

        # If it is False, raise the exception if requested
        if do_raise and not result:
            if exc:
                raise exc(*args, **kwargs)

            raise PolicyNotAuthorized(rule)

        return result


@six.add_metaclass(abc.ABCMeta)
class BaseCheck(object):
    """Abstract base class for Check classes."""

    @abc.abstractmethod
    def __str__(self):
        """String representation of the Check tree rooted at this node."""

        pass

    @abc.abstractmethod
    def __call__(self, target, cred, enforcer):
        """Triggers if instance of the class is called.

        Performs the check. Returns False to reject the access or a
        true value (not necessary True) to accept the access.
        """

        pass


class FalseCheck(BaseCheck):
    """A policy check that always returns False (disallow)."""

    def __str__(self):
        """Return a string representation of this check."""

        return "!"

    def __call__(self, target, cred, enforcer):
        """Check the policy."""

        return False


class TrueCheck(BaseCheck):
    """A policy check that always returns True (allow)."""

    def __str__(self):
        """Return a string representation of this check."""

        return "@"

    def __call__(self, target, cred, enforcer):
        """Check the policy."""

        return True


class Check(BaseCheck):
    """A base class to allow for user-defined policy checks."""

    def __init__(self, kind, match):
        """Initiates Check instance.

        :param kind: The kind of the check, i.e., the field before the
                     ':'.
        :param match: The match of the check, i.e., the field after
                      the ':'.
        """

        self.kind = kind
        self.match = match

    def __str__(self):
        """Return a string representation of this check."""

        return "%s:%s" % (self.kind, self.match)


class NotCheck(BaseCheck):
    """Implements the "not" logical operator.

    A policy check that inverts the result of another policy check.
    """

    def __init__(self, rule):
        """Initialize the 'not' check.

        :param rule: The rule to negate.  Must be a Check.
        """

        self.rule = rule

    def __str__(self):
        """Return a string representation of this check."""

        return "not %s" % self.rule

    def __call__(self, target, cred, enforcer):
        """Check the policy.

        Returns the logical inverse of the wrapped check.
        """

        return not self.rule(target, cred, enforcer)


class AndCheck(BaseCheck):
    """Implements the "and" logical operator.

    A policy check that requires that a list of other checks all return True.
    """

    def __init__(self, rules):
        """Initialize the 'and' check.

        :param rules: A list of rules that will be tested.
        """

        self.rules = rules

    def __str__(self):
        """Return a string representation of this check."""

        return "(%s)" % ' and '.join(str(r) for r in self.rules)

    def __call__(self, target, cred, enforcer):
        """Check the policy.

        Requires that all rules accept in order to return True.
        """

        for rule in self.rules:
            if not rule(target, cred, enforcer):
                return False

        return True

    def add_check(self, rule):
        """Adds rule to be tested.

        Allows addition of another rule to the list of rules that will
        be tested.  Returns the AndCheck object for convenience.
        """

        self.rules.append(rule)
        return self


class OrCheck(BaseCheck):
    """Implements the "or" operator.

    A policy check that requires that at least one of a list of other
    checks returns True.
    """

    def __init__(self, rules):
        """Initialize the 'or' check.

        :param rules: A list of rules that will be tested.
        """

        self.rules = rules

    def __str__(self):
        """Return a string representation of this check."""

        return "(%s)" % ' or '.join(str(r) for r in self.rules)

    def __call__(self, target, cred, enforcer):
        """Check the policy.

        Requires that at least one rule accept in order to return True.
        """

        for rule in self.rules:
            if rule(target, cred, enforcer):
                return True
        return False

    def add_check(self, rule):
        """Adds rule to be tested.

        Allows addition of another rule to the list of rules that will
        be tested.  Returns the OrCheck object for convenience.
        """

        self.rules.append(rule)
        return self


def _parse_check(rule):
    """Parse a single base check rule into an appropriate Check object."""

    # Handle the special checks
    if rule == '!':
        return FalseCheck()
    elif rule == '@':
        return TrueCheck()

    try:
        kind, match = rule.split(':', 1)
    except Exception:
        LOG.exception(_LE("Failed to understand rule %s") % rule)
        # If the rule is invalid, we'll fail closed
        return FalseCheck()

    # Find what implements the check
    if kind in _checks:
        return _checks[kind](kind, match)
    elif None in _checks:
        return _checks[None](kind, match)
    else:
        LOG.error(_LE("No handler for matches of kind %s") % kind)
        return FalseCheck()


def _parse_list_rule(rule):
    """Translates the old list-of-lists syntax into a tree of Check objects.

    Provided for backwards compatibility.
    """

    # Empty rule defaults to True
    if not rule:
        return TrueCheck()

    # Outer list is joined by "or"; inner list by "and"
    or_list = []
    for inner_rule in rule:
        # Elide empty inner lists
        if not inner_rule:
            continue

        # Handle bare strings
        if isinstance(inner_rule, six.string_types):
            inner_rule = [inner_rule]

        # Parse the inner rules into Check objects
        and_list = [_parse_check(r) for r in inner_rule]

        # Append the appropriate check to the or_list
        if len(and_list) == 1:
            or_list.append(and_list[0])
        else:
            or_list.append(AndCheck(and_list))

    # If we have only one check, omit the "or"
    if not or_list:
        return FalseCheck()
    elif len(or_list) == 1:
        return or_list[0]

    return OrCheck(or_list)


# Used for tokenizing the policy language
_tokenize_re = re.compile(r'\s+')


def _parse_tokenize(rule):
    """Tokenizer for the policy language.

    Most of the single-character tokens are specified in the
    _tokenize_re; however, parentheses need to be handled specially,
    because they can appear inside a check string.  Thankfully, those
    parentheses that appear inside a check string can never occur at
    the very beginning or end ("%(variable)s" is the correct syntax).
    """

    for tok in _tokenize_re.split(rule):
        # Skip empty tokens
        if not tok or tok.isspace():
            continue

        # Handle leading parens on the token
        clean = tok.lstrip('(')
        for i in range(len(tok) - len(clean)):
            yield '(', '('

        # If it was only parentheses, continue
        if not clean:
            continue
        else:
            tok = clean

        # Handle trailing parens on the token
        clean = tok.rstrip(')')
        trail = len(tok) - len(clean)

        # Yield the cleaned token
        lowered = clean.lower()
        if lowered in ('and', 'or', 'not'):
            # Special tokens
            yield lowered, clean
        elif clean:
            # Not a special token, but not composed solely of ')'
            if len(tok) >= 2 and ((tok[0], tok[-1]) in
                                  [('"', '"'), ("'", "'")]):
                # It's a quoted string
                yield 'string', tok[1:-1]
            else:
                yield 'check', _parse_check(clean)

        # Yield the trailing parens
        for i in range(trail):
            yield ')', ')'


class ParseStateMeta(type):
    """Metaclass for the ParseState class.

    Facilitates identifying reduction methods.
    """

    def __new__(mcs, name, bases, cls_dict):
        """Create the class.

        Injects the 'reducers' list, a list of tuples matching token sequences
        to the names of the corresponding reduction methods.
        """

        reducers = []

        for key, value in cls_dict.items():
            if not hasattr(value, 'reducers'):
                continue
            for reduction in value.reducers:
                reducers.append((reduction, key))

        cls_dict['reducers'] = reducers

        return super(ParseStateMeta, mcs).__new__(mcs, name, bases, cls_dict)


def reducer(*tokens):
    """Decorator for reduction methods.

    Arguments are a sequence of tokens, in order, which should trigger running
    this reduction method.
    """

    def decorator(func):
        # Make sure we have a list of reducer sequences
        if not hasattr(func, 'reducers'):
            func.reducers = []

        # Add the tokens to the list of reducer sequences
        func.reducers.append(list(tokens))

        return func

    return decorator


@six.add_metaclass(ParseStateMeta)
class ParseState(object):
    """Implement the core of parsing the policy language.

    Uses a greedy reduction algorithm to reduce a sequence of tokens into
    a single terminal, the value of which will be the root of the Check tree.

    Note: error reporting is rather lacking.  The best we can get with
    this parser formulation is an overall "parse failed" error.
    Fortunately, the policy language is simple enough that this
    shouldn't be that big a problem.
    """

    def __init__(self):
        """Initialize the ParseState."""

        self.tokens = []
        self.values = []

    def reduce(self):
        """Perform a greedy reduction of the token stream.

        If a reducer method matches, it will be executed, then the
        reduce() method will be called recursively to search for any more
        possible reductions.
        """

        for reduction, methname in self.reducers:
            if (len(self.tokens) >= len(reduction) and
                    self.tokens[-len(reduction):] == reduction):
                # Get the reduction method
                meth = getattr(self, methname)

                # Reduce the token stream
                results = meth(*self.values[-len(reduction):])

                # Update the tokens and values
                self.tokens[-len(reduction):] = [r[0] for r in results]
                self.values[-len(reduction):] = [r[1] for r in results]

                # Check for any more reductions
                return self.reduce()

    def shift(self, tok, value):
        """Adds one more token to the state.  Calls reduce()."""

        self.tokens.append(tok)
        self.values.append(value)

        # Do a greedy reduce...
        self.reduce()

    @property
    def result(self):
        """Obtain the final result of the parse.

        Raises ValueError if the parse failed to reduce to a single result.
        """

        if len(self.values) != 1:
            raise ValueError("Could not parse rule")
        return self.values[0]

    @reducer('(', 'check', ')')
    @reducer('(', 'and_expr', ')')
    @reducer('(', 'or_expr', ')')
    def _wrap_check(self, _p1, check, _p2):
        """Turn parenthesized expressions into a 'check' token."""

        return [('check', check)]

    @reducer('check', 'and', 'check')
    def _make_and_expr(self, check1, _and, check2):
        """Create an 'and_expr'.

        Join two checks by the 'and' operator.
        """

        return [('and_expr', AndCheck([check1, check2]))]

    @reducer('and_expr', 'and', 'check')
    def _extend_and_expr(self, and_expr, _and, check):
        """Extend an 'and_expr' by adding one more check."""

        return [('and_expr', and_expr.add_check(check))]

    @reducer('check', 'or', 'check')
    def _make_or_expr(self, check1, _or, check2):
        """Create an 'or_expr'.

        Join two checks by the 'or' operator.
        """

        return [('or_expr', OrCheck([check1, check2]))]

    @reducer('or_expr', 'or', 'check')
    def _extend_or_expr(self, or_expr, _or, check):
        """Extend an 'or_expr' by adding one more check."""

        return [('or_expr', or_expr.add_check(check))]

    @reducer('not', 'check')
    def _make_not_expr(self, _not, check):
        """Invert the result of another check."""

        return [('check', NotCheck(check))]


def _parse_text_rule(rule):
    """Parses policy to the tree.

    Translates a policy written in the policy language into a tree of
    Check objects.
    """

    # Empty rule means always accept
    if not rule:
        return TrueCheck()

    # Parse the token stream
    state = ParseState()
    for tok, value in _parse_tokenize(rule):
        state.shift(tok, value)

    try:
        return state.result
    except ValueError:
        # Couldn't parse the rule
        LOG.exception(_LE("Failed to understand rule %r") % rule)

        # Fail closed
        return FalseCheck()


def parse_rule(rule):
    """Parses a policy rule into a tree of Check objects."""

    # If the rule is a string, it's in the policy language
    if isinstance(rule, six.string_types):
        return _parse_text_rule(rule)
    return _parse_list_rule(rule)


def register(name, func=None):
    """Register a function or Check class as a policy check.

    :param name: Gives the name of the check type, e.g., 'rule',
                 'role', etc.  If name is None, a default check type
                 will be registered.
    :param func: If given, provides the function or class to register.
                 If not given, returns a function taking one argument
                 to specify the function or class to register,
                 allowing use as a decorator.
    """

    # Perform the actual decoration by registering the function or
    # class.  Returns the function or class for compliance with the
    # decorator interface.
    def decorator(func):
        _checks[name] = func
        return func

    # If the function or class is given, do the registration
    if func:
        return decorator(func)

    return decorator


@register("rule")
class RuleCheck(Check):
    def __call__(self, target, creds, enforcer):
        """Recursively checks credentials based on the defined rules."""

        try:
            return enforcer.rules[self.match](target, creds, enforcer)
        except KeyError:
            # We don't have any matching rule; fail closed
            return False


@register("role")
class RoleCheck(Check):
    def __call__(self, target, creds, enforcer):
        """Check that there is a matching role in the cred dict."""

        return self.match.lower() in [x.lower() for x in creds['roles']]


@register('http')
class HttpCheck(Check):
    def __call__(self, target, creds, enforcer):
        """Check http: rules by calling to a remote server.

        This example implementation simply verifies that the response
        is exactly 'True'.
        """

        url = ('http:' + self.match) % target
        data = {'target': jsonutils.dumps(target),
                'credentials': jsonutils.dumps(creds)}
        post_data = urlparse.urlencode(data)
        f = urlrequest.urlopen(url, post_data)
        return f.read() == "True"


@register(None)
class GenericCheck(Check):
    def __call__(self, target, creds, enforcer):
        """Check an individual match.

        Matches look like:

            tenant:%(tenant_id)s
            role:compute:admin
            True:%(user.enabled)s
            'Member':%(role.name)s
        """

        # TODO(termie): do dict inspection via dot syntax
        try:
            match = self.match % target
        except KeyError:
            # While doing GenericCheck if key not
            # present in Target return false
            return False

        try:
            # Try to interpret self.kind as a literal
            leftval = ast.literal_eval(self.kind)
        except ValueError:
            try:
                leftval = creds[self.kind]
            except KeyError:
                return False
        return match == six.text_type(leftval)

########NEW FILE########
__FILENAME__ = processutils
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
System-level utilities and helper functions.
"""

import logging
import random
import shlex

from eventlet.green import subprocess
from eventlet import greenthread

from barbican.openstack.common.gettextutils import _


LOG = logging.getLogger(__name__)


class UnknownArgumentError(Exception):
    def __init__(self, message=None):
        super(UnknownArgumentError, self).__init__(message)


class ProcessExecutionError(Exception):
    def __init__(self, stdout=None, stderr=None, exit_code=None, cmd=None,
                 description=None):
        if description is None:
            description = "Unexpected error while running command."
        if exit_code is None:
            exit_code = '-'
        message = ("%s\nCommand: %s\nExit code: %s\nStdout: %r\nStderr: %r"
                   % (description, cmd, exit_code, stdout, stderr))
        super(ProcessExecutionError, self).__init__(message)


def execute(*cmd, **kwargs):
    """
    Helper method to shell out and execute a command through subprocess with
    optional retry.

    :param cmd:             Passed to subprocess.Popen.
    :type cmd:              string
    :param process_input:   Send to opened process.
    :type proces_input:     string
    :param check_exit_code: Defaults to 0. Will raise
                            :class:`ProcessExecutionError`
                            if the command exits without returning this value
                            as a returncode
    :type check_exit_code:  int
    :param delay_on_retry:  True | False. Defaults to True. If set to True,
                            wait a short amount of time before retrying.
    :type delay_on_retry:   boolean
    :param attempts:        How many times to retry cmd.
    :type attempts:         int
    :param run_as_root:     True | False. Defaults to False. If set to True,
                            the command is prefixed by the command specified
                            in the root_helper kwarg.
    :type run_as_root:      boolean
    :param root_helper:     command to prefix all cmd's with
    :type root_helper:      string
    :returns:               (stdout, stderr) from process execution
    :raises:                :class:`UnknownArgumentError` on
                            receiving unknown arguments
    :raises:                :class:`ProcessExecutionError`
    """

    process_input = kwargs.pop('process_input', None)
    check_exit_code = kwargs.pop('check_exit_code', 0)
    delay_on_retry = kwargs.pop('delay_on_retry', True)
    attempts = kwargs.pop('attempts', 1)
    run_as_root = kwargs.pop('run_as_root', False)
    root_helper = kwargs.pop('root_helper', '')
    if len(kwargs):
        raise UnknownArgumentError(_('Got unknown keyword args '
                                     'to utils.execute: %r') % kwargs)
    if run_as_root:
        cmd = shlex.split(root_helper) + list(cmd)
    cmd = map(str, cmd)

    while attempts > 0:
        attempts -= 1
        try:
            LOG.debug(_('Running cmd (subprocess): %s'), ' '.join(cmd))
            _PIPE = subprocess.PIPE  # pylint: disable=E1101
            obj = subprocess.Popen(cmd,
                                   stdin=_PIPE,
                                   stdout=_PIPE,
                                   stderr=_PIPE,
                                   close_fds=True)
            result = None
            if process_input is not None:
                result = obj.communicate(process_input)
            else:
                result = obj.communicate()
            obj.stdin.close()  # pylint: disable=E1101
            _returncode = obj.returncode  # pylint: disable=E1101
            if _returncode:
                LOG.debug(_('Result was %s') % _returncode)
                if (isinstance(check_exit_code, int) and
                    not isinstance(check_exit_code, bool) and
                        _returncode != check_exit_code):
                    (stdout, stderr) = result
                    raise ProcessExecutionError(exit_code=_returncode,
                                                stdout=stdout,
                                                stderr=stderr,
                                                cmd=' '.join(cmd))
            return result
        except ProcessExecutionError:
            if not attempts:
                raise
            else:
                LOG.debug(_('%r failed. Retrying.'), cmd)
                if delay_on_retry:
                    greenthread.sleep(random.randint(20, 200) / 100.0)
        finally:
            # NOTE(termie): this appears to be necessary to let the subprocess
            #               call clean something up in between calls, without
            #               it two execute calls in a row hangs the second one
            greenthread.sleep(0)

########NEW FILE########
__FILENAME__ = service
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
import os
import random
import signal
import sys
import time

import eventlet
from eventlet import event
import logging as std_logging
from oslo.config import cfg

from barbican.openstack.common import eventlet_backdoor
from barbican.openstack.common.gettextutils import _  # noqa
from barbican.openstack.common import importutils
from barbican.openstack.common import log as logging
from barbican.openstack.common import threadgroup


rpc = importutils.try_import('barbican.openstack.common.rpc')
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


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
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_DFL)

        raise SignalExit(signo)

    def handle_signal(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, self._handle_signal)

    def _wait_for_exit_or_signal(self):
        status = None
        signo = 0

        LOG.debug(_('Full set of CONF:'))
        CONF.log_opt_values(LOG, std_logging.DEBUG)

        try:
            super(ServiceLauncher, self).wait()
        except SignalExit as exc:
            signame = {signal.SIGTERM: 'SIGTERM',
                       signal.SIGINT: 'SIGINT',
                       signal.SIGHUP: 'SIGHUP'}[exc.signo]
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

    def wait(self):
        while True:
            self.handle_signal()
            status, signo = self._wait_for_exit_or_signal()
            if signo != signal.SIGHUP:
                return status
            self.restart()


class ServiceWrapper(object):
    def __init__(self, service, workers):
        self.service = service
        self.workers = workers
        self.children = set()
        self.forktimes = []


class ProcessLauncher(object):
    def __init__(self):
        self.children = {}
        self.sigcaught = None
        self.running = True
        rfd, self.writepipe = os.pipe()
        self.readpipe = eventlet.greenio.GreenPipe(rfd, 'r')
        self.handle_signal()

    def handle_signal(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, self._handle_signal)

    def _handle_signal(self, signo, frame):
        self.sigcaught = signo
        self.running = False

        # Allow the process to be killed again and die from natural causes
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_DFL)

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
        signal.signal(signal.SIGHUP, _sighup)
        # Block SIGINT and let the parent send us a SIGTERM
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _child_wait_for_exit_or_signal(self, launcher):
        status = None
        signo = 0

        try:
            launcher.wait()
        except SignalExit as exc:
            signame = {signal.SIGTERM: 'SIGTERM',
                       signal.SIGINT: 'SIGINT',
                       signal.SIGHUP: 'SIGHUP'}[exc.signo]
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
            # NOTE(johannes): All exceptions are caught to ensure this
            # doesn't fallback into the loop spawning children. It would
            # be bad for a child to spawn more children.
            launcher = self._child_process(wrap.service)
            while True:
                self._child_process_handle_signal()
                status, signo = self._child_wait_for_exit_or_signal(launcher)
                if signo != signal.SIGHUP:
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
                eventlet.greenthread.sleep(.01)
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
                signame = {signal.SIGTERM: 'SIGTERM',
                           signal.SIGINT: 'SIGINT',
                           signal.SIGHUP: 'SIGHUP'}[self.sigcaught]
                LOG.info(_('Caught %s, stopping children'), signame)
            if self.sigcaught != signal.SIGHUP:
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


def launch(service, workers=None):
    if workers:
        launcher = ProcessLauncher()
        launcher.launch_service(service, workers=workers)
    else:
        launcher = ServiceLauncher()
        launcher.launch_service(service)
    return launcher

########NEW FILE########
__FILENAME__ = sslutils
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from barbican.openstack.common.gettextutils import _  # noqa


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
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import eventlet
from eventlet import greenpool
from eventlet import greenthread

from barbican.openstack.common import log as logging
from barbican.openstack.common import loopingcall


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


class ThreadGroup(object):
    """The point of the ThreadGroup classis to:

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

    def thread_done(self, thread):
        self.threads.remove(thread)

    def stop(self):
        current = greenthread.getcurrent()
        for x in self.threads:
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
        current = greenthread.getcurrent()
        for x in self.threads:
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
__FILENAME__ = client
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Client-side (i.e. API side) classes and logic.
"""
from barbican.common import utils
from barbican import queue
from barbican.queue import server

LOG = utils.getLogger(__name__)


class TaskClient(object):
    """API-side client interface to asynchronous queuing services.

    The class delegates calls to the oslo.messaging RPC framework.
    """
    def __init__(self):
        super(TaskClient, self).__init__()

        # Establish either an asynchronous messaging/queuing client
        #   interface (via Oslo's RPC messaging) or else allow for
        #   synchronously invoking worker processes in support of a
        #   standalone single-node mode for Barbican.
        self._client = queue.get_client() or _DirectTaskInvokerClient()

    def process_order(self, order_id, keystone_id):
        """Process Order."""

        self._cast('process_order', order_id=order_id,
                   keystone_id=keystone_id)

    def _cast(self, name, **kwargs):
        """Asynchronous call handler. Barbican probably only needs casts.

        :param name: Method name to invoke.
        :param kwargs: Arguments for the method invocation.
        :return:
        """
        return self._client.cast({}, name, **kwargs)

    def _call(self, name, **kwargs):
        """Synchronous call handler. Barbican probably *never* uses calls."""
        return self._client.call({}, name, **kwargs)


class _DirectTaskInvokerClient(object):
    """Allows for direct invocation of queue.server Tasks.

    This class supports a standalone single-node mode of operation for
    Barbican, whereby typically asynchronous requests to Barbican are
    handled synchronously.
    """

    def __init__(self):
        super(_DirectTaskInvokerClient, self).__init__()

        self._tasks = server.Tasks()

    def cast(self, context, method_name, **kwargs):
        try:
            getattr(self._tasks, method_name)(context, **kwargs)
        except Exception:
            LOG.exception(">>>>> Task exception seen for synchronous task "
                          "invocation, so handling exception to mimic "
                          "asynchronous behavior.")

    def call(self, context, method_name, **kwargs):
        raise ValueError("No support for call() client methods.")

########NEW FILE########
__FILENAME__ = server
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Server-side (i.e. worker side) classes and logic.
"""
from oslo.config import cfg

from barbican.common import utils
from barbican.openstack.common import service
from barbican import queue
from barbican.tasks import resources


LOG = utils.getLogger(__name__)

CONF = cfg.CONF


class Tasks(object):
    """Tasks that can be invoked asynchronously in Barbican.

    Only place task methods and implementations on this class, as they can be
    called directly from the client side for non-asynchronous standalone
    single-node operation.

    The TaskServer class below extends this class to implement a worker-side
    server utilizing Oslo messaging's RPC server. This RPC server can invoke
    methods on itself, which include the methods in this class.
    """
    def process_order(self, context, order_id, keystone_id):
        """Process Order."""
        LOG.debug('Order id is {0}'.format(order_id))
        task = resources.BeginOrder()
        try:
            task.process(order_id, keystone_id)
        except Exception:
            LOG.exception(">>>>> Task exception seen, details reported "
                          "on the Orders entity.")


class TaskServer(Tasks, service.Service):
    """Server to process asynchronous tasking from Barbican API nodes.

    This server is an Oslo service that exposes task methods that can
    be invoked from the Barbican API nodes. It delegates to an Oslo
    RPC messaging server to invoke methods asynchronously on this class.
    Since this class also extends the Tasks class above, its task-based
    methods are hence available to the RPC messaging server.
    """
    def __init__(self):
        super(TaskServer, self).__init__()

        # This property must be defined for the 'endpoints' specified below,
        #   as the oslo.messaging RPC server will ask for it.
        self.target = queue.get_target()

        # Create an oslo RPC server, that calls back on to this class
        #   instance to invoke tasks, such as 'process_order()' on the
        #   extended Tasks class above.
        self._server = queue.get_server(target=self.target,
                                        endpoints=[self])

    def start(self):
        self._server.start()
        super(TaskServer, self).start()

    def stop(self):
        super(TaskServer, self).stop()
        self._server.stop()

########NEW FILE########
__FILENAME__ = resources
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Task resources for the Barbican API.
"""
import abc

import six

from barbican import api
from barbican.common import resources as res
from barbican.common import utils
from barbican.crypto import extension_manager as em
from barbican.model import models
from barbican.model import repositories as rep
from barbican.openstack.common import gettextutils as u

LOG = utils.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseTask(object):
    """Base asychronous task."""

    @abc.abstractmethod
    def get_name(self):
        """A hook method to return a short localized name for this task.
        The returned name in the form 'u.('Verb Noun')'. For example:
            u._('Create Secret')
        """

    def process(self, *args, **kwargs):
        """A template method for all asynchronous tasks.

        This method should not be overridden by sub-classes. Rather the
        abstract methods below should be overridden.

        :param args: List of arguments passed in from the client.
        :param kwargs: Dict of arguments passed in from the client.
        :return: None
        """
        name = self.get_name()

        # Retrieve the target entity (such as an models.Order instance).
        try:
            entity = self.retrieve_entity(*args, **kwargs)
        except Exception as e:
            # Serious error!
            LOG.exception(u._("Could not retrieve information needed to "
                              "process task '{0}'.").format(name))
            raise e

        # Process the target entity.
        try:
            self.handle_processing(entity, *args, **kwargs)
        except Exception as e_orig:
            LOG.exception(u._("Could not perform processing for "
                              "task '{0}'.").format(name))

            # Handle failure to process entity.
            try:
                status, message = api \
                    .generate_safe_exception_message(name, e_orig)
                self.handle_error(entity, status, message, e_orig,
                                  *args, **kwargs)
            except Exception:
                LOG.exception(u._("Problem handling an error for task '{0}', "
                                  "raising original "
                                  "exception.").format(name))
            raise e_orig

        # Handle successful conclusion of processing.
        try:
            self.handle_success(entity, *args, **kwargs)
        except Exception as e:
            LOG.exception(u._("Could not process after successfully executing"
                              " task '{0}'.").format(name))
            raise e

    @abc.abstractmethod
    def retrieve_entity(self, *args, **kwargs):
        """A hook method to retrieve an entity for processing.

        :param args: List of arguments passed in from the client.
        :param kwargs: Dict of arguments passed in from the client.
        :return: Entity instance to process in subsequent hook methods.
        """

    @abc.abstractmethod
    def handle_processing(self, entity, *args, **kwargs):
        """A hook method to handle processing on behalf of an entity.

        :param args: List of arguments passed in from the client.
        :param kwargs: Dict of arguments passed in from the client.
        :return: None
        """

    @abc.abstractmethod
    def handle_error(self, entity, status, message, exception,
                     *args, **kwargs):
        """A hook method to deal with errors seen during processing.

        This method could be used to mark entity as being in error, and/or
        to record an error cause.

        :param entity: Entity retrieved from _retrieve_entity() above.
        :param status: Status code for exception.
        :param message: Reason/message for the exception.
        :param exception: Exception raised from handle_processing() above.
        :param args: List of arguments passed in from the client.
        :param kwargs: Dict of arguments passed in from the client.
        :return: None
        """

    @abc.abstractmethod
    def handle_success(self, entity, *args, **kwargs):
        """A hook method to post-process after successful entity processing.

        This method could be used to mark entity as being active, or to
        add information/references to the entity.

        :param entity: Entity retrieved from _retrieve_entity() above.
        :param args: List of arguments passed in from the client.
        :param kwargs: Dict of arguments passed in from the client.
        :return: None
        """


class BeginOrder(BaseTask):
    """Handles beginning processing an Order"""

    def get_name(self):
        return u._('Create Secret')

    def __init__(self, crypto_manager=None, tenant_repo=None, order_repo=None,
                 secret_repo=None, tenant_secret_repo=None,
                 datum_repo=None, kek_repo=None):
        LOG.debug('Creating BeginOrder task processor')
        self.order_repo = order_repo or rep.OrderRepo()
        self.tenant_repo = tenant_repo or rep.TenantRepo()
        self.secret_repo = secret_repo or rep.SecretRepo()
        self.tenant_secret_repo = tenant_secret_repo or rep.TenantSecretRepo()
        self.datum_repo = datum_repo or rep.EncryptedDatumRepo()
        self.kek_repo = kek_repo or rep.KEKDatumRepo()
        self.crypto_manager = crypto_manager or em.CryptoExtensionManager()

    def retrieve_entity(self, order_id, keystone_id):
        return self.order_repo.get(entity_id=order_id,
                                   keystone_id=keystone_id)

    def handle_processing(self, order, *args, **kwargs):
        self.handle_order(order)

    def handle_error(self, order, status, message, exception,
                     *args, **kwargs):
        order.status = models.States.ERROR
        order.error_status_code = status
        order.error_reason = message
        self.order_repo.save(order)

    def handle_success(self, order, *args, **kwargs):
        order.status = models.States.ACTIVE
        self.order_repo.save(order)

    def handle_order(self, order):
        """Handle secret creation.

        Either creates a secret item here, or else begins the extended
        process of creating a secret (such as for SSL certificate
        generation.

        :param order: Order to process on behalf of.
        """
        order_info = order.to_dict_fields()
        secret_info = order_info['secret']

        # Retrieve the tenant.
        tenant = self.tenant_repo.get(order.tenant_id)

        # Create Secret
        new_secret = res.create_secret(secret_info, tenant,
                                       self.crypto_manager, self.secret_repo,
                                       self.tenant_secret_repo,
                                       self.datum_repo, self.kek_repo,
                                       ok_to_generate=True)
        order.secret_id = new_secret.id

        LOG.debug("...done creating order's secret.")

########NEW FILE########
__FILENAME__ = test_middleware
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import mock

from barbican.api.middleware.simple import SimpleFilter


class WhenTestingSimpleMiddleware(unittest.TestCase):

    def setUp(self):
        self.app = mock.MagicMock()
        self.middle = SimpleFilter(self.app)
        self.req = mock.MagicMock()

    def test_should_process_request(self):
        self.middle.process_request(self.req)

########NEW FILE########
__FILENAME__ = test_resources
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This test module focuses on typical-flow business logic tests with the API
resource classes. For RBAC tests of these classes, see the
'resources_policy_test.py' module.
"""

import base64
import urllib

import mock
import pecan
import testtools
import webtest

from barbican.api import app
from barbican.api import controllers
from barbican.api import strip_whitespace
from barbican.common import exception as excep
from barbican.common import utils
from barbican.common import validators
from barbican.crypto import extension_manager as em
from barbican.model import models
from barbican.tests.crypto import test_plugin as ctp


def create_secret(id_ref="id", name="name",
                  algorithm=None, bit_length=None,
                  mode=None, encrypted_datum=None):
    """Generate a Secret entity instance."""
    info = {'id': id_ref,
            'name': name,
            'algorithm': algorithm,
            'bit_length': bit_length,
            'mode': mode}
    secret = models.Secret(info)
    secret.id = id_ref
    if encrypted_datum:
        secret.encrypted_data = [encrypted_datum]
    return secret


def create_order(id_ref="id",
                 name="name",
                 algorithm=None,
                 bit_length=None,
                 mode=None):
    """Generate an Order entity instance."""
    order = models.Order()
    order.id = id_ref
    order.secret_name = name
    order.secret_algorithm = algorithm
    order.secret_bit_length = bit_length
    order.secret_mode = mode
    return order


def validate_datum(test, datum):
    test.assertIsNone(datum.kek_meta_extended)
    test.assertIsNotNone(datum.kek_meta_tenant)
    test.assertTrue(datum.kek_meta_tenant.bind_completed)
    test.assertIsNotNone(datum.kek_meta_tenant.plugin_name)
    test.assertIsNotNone(datum.kek_meta_tenant.kek_label)


def create_container(id_ref):
    """Generate a Container entity instance."""
    container = models.Container()
    container.id = id_ref
    container.name = 'test name'
    container.type = 'rsa'
    container_secret = models.ContainerSecret()
    container_secret.container_id = id
    container_secret.secret_id = '123'
    container.container_secrets.append(container_secret)
    return container


class FunctionalTest(testtools.TestCase):

    def setUp(self):
        super(FunctionalTest, self).setUp()
        root = self.root
        config = {'app': {'root': root}}
        pecan.set_config(config, overwrite=True)
        self.app = webtest.TestApp(pecan.make_app(root))

    def tearDown(self):
        super(FunctionalTest, self).tearDown()
        pecan.set_config({}, overwrite=True)

    @property
    def root(self):
        return controllers.versions.VersionController()


class WhenTestingVersionResource(FunctionalTest):

    def test_should_return_200_on_get(self):
        resp = self.app.get('/')
        self.assertEqual(200, resp.status_int)

    def test_should_return_version_json(self):
        resp = self.app.get('/')

        self.assertTrue('v1' in resp.json)
        self.assertEqual('current', resp.json['v1'])


class BaseSecretsResource(FunctionalTest):
    """Base test class for the Secrets resource."""

    def setUp(self):
        super(BaseSecretsResource, self).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            secrets = controllers.secrets.SecretsController(
                self.crypto_mgr, self.tenant_repo, self.secret_repo,
                self.tenant_secret_repo, self.datum_repo, self.kek_repo
            )

        return RootController()

    def _init(self, payload=b'not-encrypted',
              payload_content_type='text/plain',
              payload_content_encoding=None):
        self.name = 'name'
        self.payload = payload
        self.payload_content_type = payload_content_type
        self.payload_content_encoding = payload_content_encoding
        self.secret_algorithm = 'AES'
        self.secret_bit_length = 256
        self.secret_mode = 'CBC'
        self.secret_req = {'name': self.name,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode}
        if payload:
            self.secret_req['payload'] = payload
        if payload_content_type:
            self.secret_req['payload_content_type'] = payload_content_type
        if payload_content_encoding:
            self.secret_req['payload_content_encoding'] = \
                payload_content_encoding

        self.keystone_id = 'keystone1234'
        self.tenant_entity_id = 'tid1234'
        self.tenant = models.Tenant()
        self.tenant.id = self.tenant_entity_id
        self.tenant.keystone_id = self.keystone_id
        self.tenant_repo = mock.MagicMock()
        self.tenant_repo.find_by_keystone_id.return_value = self.tenant

        self.secret_repo = mock.MagicMock()
        self.secret_repo.create_from.return_value = None

        self.tenant_secret_repo = mock.MagicMock()
        self.tenant_secret_repo.create_from.return_value = None

        self.datum_repo = mock.MagicMock()
        self.datum_repo.create_from.return_value = None

        self.kek_datum = models.KEKDatum()
        self.kek_datum.plugin_name = utils.generate_fullname_for(
            ctp.TestCryptoPlugin())
        self.kek_datum.kek_label = "kek_label"
        self.kek_datum.bind_completed = False
        self.kek_repo = mock.MagicMock()
        self.kek_repo.find_or_create_kek_metadata.return_value = self.kek_datum

        self.conf = mock.MagicMock()
        self.conf.crypto.namespace = 'barbican.test.crypto.plugin'
        self.conf.crypto.enabled_crypto_plugins = ['test_crypto']
        self.crypto_mgr = em.CryptoExtensionManager(conf=self.conf)

    def _test_should_add_new_secret_with_expiration(self):
        expiration = '2114-02-28 12:14:44.180394-05:00'
        self.secret_req.update({'expiration': expiration})

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )

        self.assertEqual(resp.status_int, 201)

        args, kwargs = self.secret_repo.create_from.call_args
        secret = args[0]
        expected = expiration[:-6].replace('12', '17', 1)
        self.assertEqual(expected, str(secret.expiration))

    def _test_should_add_new_secret_one_step(self, check_tenant_id=True):
        """Test the one-step secret creation.

        :param check_tenant_id: True if the retrieved Tenant id needs to be
        verified, False to skip this check (necessary for new-Tenant flows).
        """
        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )
        self.assertEqual(resp.status_int, 201)

        args, kwargs = self.secret_repo.create_from.call_args
        secret = args[0]
        self.assertIsInstance(secret, models.Secret)
        self.assertEqual(secret.name, self.name)
        self.assertEqual(secret.algorithm, self.secret_algorithm)
        self.assertEqual(secret.bit_length, self.secret_bit_length)
        self.assertEqual(secret.mode, self.secret_mode)

        args, kwargs = self.tenant_secret_repo.create_from.call_args
        tenant_secret = args[0]
        self.assertIsInstance(tenant_secret, models.TenantSecret)
        if check_tenant_id:
            self.assertEqual(tenant_secret.tenant_id, self.tenant_entity_id)
        self.assertEqual(tenant_secret.secret_id, secret.id)

        args, kwargs = self.datum_repo.create_from.call_args
        datum = args[0]
        self.assertIsInstance(datum, models.EncryptedDatum)
        self.assertEqual(base64.b64encode('cypher_text'), datum.cypher_text)
        self.assertEqual(self.payload_content_type, datum.content_type)

        validate_datum(self, datum)

    def _test_should_add_new_secret_if_tenant_does_not_exist(self):
        self.tenant_repo.get.return_value = None
        self.tenant_repo.find_by_keystone_id.return_value = None

        self._test_should_add_new_secret_one_step(check_tenant_id=False)

        args, kwargs = self.tenant_repo.create_from.call_args
        tenant = args[0]
        self.assertIsInstance(tenant, models.Tenant)
        self.assertEqual(self.keystone_id, tenant.keystone_id)

    def _test_should_add_new_secret_metadata_without_payload(self):
        self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            {'name': self.name}
        )

        args, kwargs = self.secret_repo.create_from.call_args
        secret = args[0]
        self.assertIsInstance(secret, models.Secret)
        self.assertEqual(secret.name, self.name)

        args, kwargs = self.tenant_secret_repo.create_from.call_args
        tenant_secret = args[0]
        self.assertIsInstance(tenant_secret, models.TenantSecret)
        self.assertEqual(tenant_secret.tenant_id, self.tenant_entity_id)
        self.assertEqual(tenant_secret.secret_id, secret.id)

        self.assertFalse(self.datum_repo.create_from.called)

    def _test_should_add_new_secret_payload_almost_too_large(self):
        if validators.DEFAULT_MAX_SECRET_BYTES % 4:
            raise ValueError('Tests currently require max secrets divides by '
                             '4 evenly, due to base64 encoding.')

        big_text = ''.join(['A' for x
                            in xrange(validators.DEFAULT_MAX_SECRET_BYTES -
                                      8)])

        self.secret_req = {'name': self.name,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': big_text,
                           'payload_content_type': self.payload_content_type}
        if self.payload_content_encoding:
            self.secret_req['payload_content_encoding'] = \
                self.payload_content_encoding
        self.app.post_json('/%s/secrets/' % self.keystone_id, self.secret_req)

    def _test_should_fail_due_to_payload_too_large(self):
        big_text = ''.join(['A' for x
                            in xrange(validators.DEFAULT_MAX_SECRET_BYTES +
                                      10)])

        self.secret_req = {'name': self.name,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': big_text,
                           'payload_content_type': self.payload_content_type}
        if self.payload_content_encoding:
            self.secret_req['payload_content_encoding'] = \
                self.payload_content_encoding

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 413)

    def _test_should_fail_due_to_empty_payload(self):
        self.secret_req = {'name': self.name,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': ''}
        if self.payload_content_type:
            self.secret_req['payload_content_type'] = self.payload_content_type
        if self.payload_content_encoding:
            self.secret_req['payload_content_encoding'] = \
                self.payload_content_encoding

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        assert resp.status_int == 400


class WhenCreatingPlainTextSecretsUsingSecretsResource(BaseSecretsResource):

    def test_should_add_new_secret_one_step(self):
        self._test_should_add_new_secret_one_step()

    def test_should_add_new_secret_with_expiration(self):
        self._test_should_add_new_secret_with_expiration()

    def test_should_add_new_secret_if_tenant_does_not_exist(self):
        self._test_should_add_new_secret_if_tenant_does_not_exist()

    def test_should_add_new_secret_metadata_without_payload(self):
        self._test_should_add_new_secret_metadata_without_payload()

    def test_should_add_new_secret_payload_almost_too_large(self):
        self._test_should_add_new_secret_payload_almost_too_large()

    def test_should_fail_due_to_payload_too_large(self):
        self._test_should_fail_due_to_payload_too_large()

    def test_should_fail_due_to_empty_payload(self):
        self._test_should_fail_due_to_empty_payload()

    def test_should_fail_due_to_unsupported_payload_content_type(self):
        self.secret_req = {'name': self.name,
                           'payload_content_type': 'somethingbogushere',
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_create_secret_content_type_text_plain(self):
        # payload_content_type has trailing space
        self.secret_req = {'name': self.name,
                           'payload_content_type': 'text/plain ',
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )
        self.assertEqual(resp.status_int, 201)

        self.secret_req = {'name': self.name,
                           'payload_content_type': '  text/plain',
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )
        self.assertEqual(resp.status_int, 201)

    def test_create_secret_content_type_text_plain_space_charset_utf8(self):
        # payload_content_type has trailing space
        self.secret_req = {'name': self.name,
                           'payload_content_type':
                           'text/plain; charset=utf-8 ',
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )
        self.assertEqual(resp.status_int, 201)

        self.secret_req = {'name': self.name,
                           'payload_content_type':
                           '  text/plain; charset=utf-8',
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )
        self.assertEqual(resp.status_int, 201)

    def test_create_secret_with_only_content_type(self):
        # No payload just content_type
        self.secret_req = {'payload_content_type':
                           'text/plain'}
        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

        self.secret_req = {'payload_content_type':
                           'text/plain',
                           'payload': 'somejunk'}
        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req
        )
        self.assertEqual(resp.status_int, 201)


class WhenCreatingBinarySecretsUsingSecretsResource(BaseSecretsResource):

    @property
    def root(self):
        self._init(payload="...lOtfqHaUUpe6NqLABgquYQ==",
                   payload_content_type='application/octet-stream',
                   payload_content_encoding='base64')
        return super(WhenCreatingBinarySecretsUsingSecretsResource, self).root

    def test_should_add_new_secret_one_step(self):
        self._test_should_add_new_secret_one_step()

    def test_should_add_new_secret_with_expiration(self):
        self._test_should_add_new_secret_with_expiration()

    def test_should_add_new_secret_if_tenant_does_not_exist(self):
        self._test_should_add_new_secret_if_tenant_does_not_exist()

    def test_should_add_new_secret_metadata_without_payload(self):
        self._test_should_add_new_secret_metadata_without_payload()

    def test_should_add_new_secret_payload_almost_too_large(self):
        self._test_should_add_new_secret_payload_almost_too_large()

    def test_should_fail_due_to_payload_too_large(self):
        self._test_should_fail_due_to_payload_too_large()

    def test_should_fail_due_to_empty_payload(self):
        self._test_should_fail_due_to_empty_payload()

    def test_create_secret_fails_with_binary_payload_no_encoding(self):
        self.secret_req = {
            'name': self.name,
            'algorithm': self.secret_algorithm,
            'bit_length': self.secret_bit_length,
            'mode': self.secret_mode,
            'payload': 'lOtfqHaUUpe6NqLABgquYQ==',
            'payload_content_type': 'application/octet-stream'
        }
        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_create_secret_fails_with_binary_payload_bad_encoding(self):
        self.secret_req = {
            'name': self.name,
            'algorithm': self.secret_algorithm,
            'bit_length': self.secret_bit_length,
            'mode': self.secret_mode,
            'payload': 'lOtfqHaUUpe6NqLABgquYQ==',
            'payload_content_type': 'application/octet-stream',
            'payload_content_encoding': 'bogus64'
        }

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_create_secret_fails_with_binary_payload_no_content_type(self):
        self.secret_req = {
            'name': self.name,
            'algorithm': self.secret_algorithm,
            'bit_length': self.secret_bit_length,
            'mode': self.secret_mode,
            'payload': 'lOtfqHaUUpe6NqLABgquYQ==',
            'payload_content_encoding': 'base64'
        }

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_create_secret_fails_with_bad_payload(self):
        self.secret_req = {
            'name': self.name,
            'algorithm': self.secret_algorithm,
            'bit_length': self.secret_bit_length,
            'mode': self.secret_mode,
            'payload': 'AAAAAAAAA',
            'payload_content_type': 'application/octet-stream',
            'payload_content_encoding': 'base64'
        }

        resp = self.app.post_json(
            '/%s/secrets/' % self.keystone_id,
            self.secret_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)


class WhenGettingSecretsListUsingSecretsResource(FunctionalTest):

    def setUp(self):
        super(WhenGettingSecretsListUsingSecretsResource, self).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            secrets = controllers.secrets.SecretsController(
                self.crypto_mgr, self.tenant_repo, self.secret_repo,
                self.tenant_secret_repo, self.datum_repo, self.kek_repo
            )

        return RootController()

    def _init(self):
        self.tenant_id = 'tenant1234'
        self.keystone_id = 'keystone1234'
        self.name = 'name 1234 !@#$%^&*()_+=-{}[];:<>,./?'
        self.secret_algorithm = "AES"
        self.secret_bit_length = 256
        self.secret_mode = "CBC"

        self.num_secrets = 10
        self.offset = 2
        self.limit = 2

        secret_params = {'name': self.name,
                         'algorithm': self.secret_algorithm,
                         'bit_length': self.secret_bit_length,
                         'mode': self.secret_mode,
                         'encrypted_datum': None}

        self.secrets = [create_secret(id_ref='id' + str(id),
                                      **secret_params) for
                        id in xrange(self.num_secrets)]
        self.total = len(self.secrets)

        self.secret_repo = mock.MagicMock()
        self.secret_repo.get_by_create_date.return_value = (self.secrets,
                                                            self.offset,
                                                            self.limit,
                                                            self.total)

        self.tenant_repo = mock.MagicMock()

        self.tenant_secret_repo = mock.MagicMock()
        self.tenant_secret_repo.create_from.return_value = None

        self.datum_repo = mock.MagicMock()
        self.datum_repo.create_from.return_value = None

        self.kek_repo = mock.MagicMock()

        self.conf = mock.MagicMock()
        self.conf.crypto.namespace = 'barbican.test.crypto.plugin'
        self.conf.crypto.enabled_crypto_plugins = ['test_crypto']
        self.crypto_mgr = em.CryptoExtensionManager(conf=self.conf)

        self.params = {'offset': self.offset,
                       'limit': self.limit,
                       'name': None,
                       'alg': None,
                       'bits': 0,
                       'mode': None}

    def test_should_list_secrets_by_name(self):
        # Quote the name parameter to simulate how it would be
        # received in practice via a REST-ful GET query.
        self.params['name'] = urllib.quote_plus(self.name)

        resp = self.app.get(
            '/%s/secrets/' % self.keystone_id,
            dict((k, v) for k, v in self.params.items() if v is not None)
        )
        # Verify that the name is unquoted correctly in the
        # secrets.on_get function prior to searching the repo.
        self.secret_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True,
                                     name=self.name,
                                     alg=None, mode=None,
                                     bits=0)

        self.assertIn('secrets', resp.namespace)
        secrets = resp.namespace['secrets']
        # The result should be the unquoted name
        self.assertEqual(secrets[0]['name'], self.name)

    def test_should_get_list_secrets(self):
        resp = self.app.get(
            '/%s/secrets/' % self.keystone_id,
            dict((k, v) for k, v in self.params.items() if v is not None)
        )

        self.secret_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True,
                                     name='', alg=None, mode=None,
                                     bits=0)

        self.assertTrue('previous' in resp.namespace)
        self.assertTrue('next' in resp.namespace)

        url_nav_next = self._create_url(self.keystone_id,
                                        self.offset + self.limit, self.limit)
        self.assertTrue(resp.body.count(url_nav_next) == 1)

        url_nav_prev = self._create_url(self.keystone_id,
                                        0, self.limit)
        self.assertTrue(resp.body.count(url_nav_prev) == 1)

        url_hrefs = self._create_url(self.keystone_id)
        self.assertTrue(resp.body.count(url_hrefs) ==
                        (self.num_secrets + 2))

    def test_response_should_include_total(self):
        resp = self.app.get(
            '/%s/secrets/' % self.keystone_id,
            dict((k, v) for k, v in self.params.items() if v is not None)
        )

        self.assertIn('total', resp.namespace)
        self.assertEqual(resp.namespace['total'], self.total)

    def test_should_handle_no_secrets(self):

        del self.secrets[:]

        resp = self.app.get(
            '/%s/secrets/' % self.keystone_id,
            dict((k, v) for k, v in self.params.items() if v is not None)
        )

        self.secret_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True,
                                     name='', alg=None, mode=None,
                                     bits=0)

        self.assertFalse('previous' in resp.namespace)
        self.assertFalse('next' in resp.namespace)

    def _create_url(self, keystone_id, offset_arg=None, limit_arg=None):
        if limit_arg:
            offset = int(offset_arg)
            limit = int(limit_arg)
            return '/{0}/secrets?limit={1}&offset={2}'.format(keystone_id,
                                                              limit,
                                                              offset)
        else:
            return '/{0}/secrets'.format(keystone_id)


class WhenGettingPuttingOrDeletingSecretUsingSecretResource(FunctionalTest):
    def setUp(self):
        super(
            WhenGettingPuttingOrDeletingSecretUsingSecretResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            secrets = controllers.secrets.SecretsController(
                self.crypto_mgr, self.tenant_repo, self.secret_repo,
                self.tenant_secret_repo, self.datum_repo, self.kek_repo
            )

        return RootController()

    def _init(self):
        self.tenant_id = 'tenantid1234'
        self.keystone_id = 'keystone1234'
        self.name = 'name1234'

        secret_id = "idsecret1"
        datum_id = "iddatum1"
        kek_id = "idkek1"

        self.secret_algorithm = "AES"
        self.secret_bit_length = 256
        self.secret_mode = "CBC"

        self.kek_tenant = models.KEKDatum()
        self.kek_tenant.id = kek_id
        self.kek_tenant.active = True
        self.kek_tenant.bind_completed = False
        self.kek_tenant.kek_label = "kek_label"
        self.kek_tenant.plugin_name = utils.generate_fullname_for(
            ctp.TestCryptoPlugin())

        self.datum = models.EncryptedDatum()
        self.datum.id = datum_id
        self.datum.secret_id = secret_id
        self.datum.kek_id = kek_id
        self.datum.kek_meta_tenant = self.kek_tenant
        self.datum.content_type = "text/plain"
        self.datum.cypher_text = "aaaa"  # base64 value.

        self.secret = create_secret(id_ref=secret_id,
                                    name=self.name,
                                    algorithm=self.secret_algorithm,
                                    bit_length=self.secret_bit_length,
                                    mode=self.secret_mode,
                                    encrypted_datum=self.datum)

        self.tenant = models.Tenant()
        self.tenant.id = self.tenant_id
        self.keystone_id = self.keystone_id
        self.tenant_repo = mock.MagicMock()
        self.tenant_repo.get.return_value = self.tenant

        self.secret_repo = mock.MagicMock()
        self.secret_repo.get.return_value = self.secret
        self.secret_repo.delete_entity_by_id.return_value = None

        self.tenant_secret_repo = mock.MagicMock()

        self.datum_repo = mock.MagicMock()
        self.datum_repo.create_from.return_value = None

        self.kek_repo = mock.MagicMock()

        self.conf = mock.MagicMock()
        self.conf.crypto.namespace = 'barbican.test.crypto.plugin'
        self.conf.crypto.enabled_crypto_plugins = ['test_crypto']
        self.crypto_mgr = em.CryptoExtensionManager(conf=self.conf)

    def test_should_get_secret_as_json(self):
        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
        )
        self.secret_repo \
            .get.assert_called_once_with(entity_id=self.secret.id,
                                         keystone_id=self.keystone_id,
                                         suppress_exception=True)
        self.assertEqual(resp.status_int, 200)

        self.assertNotIn('content_encodings', resp.namespace)
        self.assertIn('content_types', resp.namespace)
        self.assertIn(self.datum.content_type,
                      resp.namespace['content_types'].itervalues())
        self.assertNotIn('mime_type', resp.namespace)

    def test_should_get_secret_as_plain(self):
        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={'Accept': 'text/plain'}
        )

        self.secret_repo \
            .get.assert_called_once_with(entity_id=self.secret.id,
                                         keystone_id=self.keystone_id,
                                         suppress_exception=True)
        self.assertEqual(resp.status_int, 200)

        self.assertIsNotNone(resp.body)

    def test_should_get_secret_meta_for_binary(self):
        self.datum.content_type = "application/octet-stream"
        self.datum.cypher_text = 'aaaa'

        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
        )

        self.secret_repo \
            .get.assert_called_once_with(entity_id=self.secret.id,
                                         keystone_id=self.keystone_id,
                                         suppress_exception=True)

        self.assertEqual(resp.status_int, 200)

        self.assertIsNotNone(resp.namespace)
        self.assertIn('content_types', resp.namespace)
        self.assertIn(self.datum.content_type,
                      resp.namespace['content_types'].itervalues())

    def test_should_get_secret_as_binary(self):
        self.datum.content_type = "application/octet-stream"
        self.datum.cypher_text = 'aaaa'

        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={
                'Accept': 'application/octet-stream',
                'Accept-Encoding': 'gzip'
            }
        )

        self.assertEqual(resp.body, 'unencrypted_data')

    def test_should_throw_exception_for_get_when_secret_not_found(self):
        self.secret_repo.get.return_value = None

        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip'},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

    def test_should_throw_exception_for_get_when_accept_not_supported(self):
        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={'Accept': 'bogusaccept', 'Accept-Encoding': 'gzip'},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 406)

    def test_should_throw_exception_for_get_when_datum_not_available(self):
        self.secret.encrypted_data = []

        resp = self.app.get(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            headers={'Accept': 'text/plain'},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

    def test_should_put_secret_as_plain(self):
        self.secret.encrypted_data = []

        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            'plain text',
            headers={'Accept': 'text/plain', 'Content-Type': 'text/plain'},
        )

        self.assertEqual(resp.status_int, 200)

        args, kwargs = self.datum_repo.create_from.call_args
        datum = args[0]
        self.assertIsInstance(datum, models.EncryptedDatum)
        self.assertEqual(base64.b64encode('cypher_text'), datum.cypher_text)

        validate_datum(self, datum)

    def test_should_put_secret_as_binary(self):
        self.secret.encrypted_data = []

        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            'plain text',
            headers={
                'Accept': 'text/plain',
                'Content-Type': 'application/octet-stream'
            },
        )

        self.assertEqual(resp.status_int, 200)

        args, kwargs = self.datum_repo.create_from.call_args
        datum = args[0]
        self.assertIsInstance(datum, models.EncryptedDatum)

    def test_should_put_encoded_secret_as_binary(self):
        self.secret.encrypted_data = []
        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            base64.b64encode('plain text'),
            headers={
                'Accept': 'text/plain',
                'Content-Type': 'application/octet-stream',
                'Content-Encoding': 'base64'
            },
        )

        self.assertEqual(resp.status_int, 200)

    def test_should_fail_to_put_secret_with_unsupported_encoding(self):
        self.secret.encrypted_data = []
        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            'plain text',
            headers={
                'Accept': 'text/plain',
                'Content-Type': 'application/octet-stream',
                'Content-Encoding': 'bogusencoding'
            },
            expect_errors=True
        )

        self.assertEqual(resp.status_int, 400)

    def test_should_fail_put_secret_as_json(self):
        self.secret.encrypted_data = []
        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            'plain text',
            headers={
                'Accept': 'text/plain',
                'Content-Type': 'application/json'
            },
            expect_errors=True
        )

        self.assertEqual(resp.status_int, 415)

    def test_should_fail_put_secret_not_found(self):
        # Force error, due to secret not found.
        self.secret_repo.get.return_value = None

        self.secret.encrypted_data = []
        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            'plain text',
            headers={'Accept': 'text/plain', 'Content-Type': 'text/plain'},
            expect_errors=True
        )

        self.assertEqual(resp.status_int, 404)

    def test_should_fail_put_secret_no_payload(self):
        self.secret.encrypted_data = []
        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            # response.body = None
            headers={'Accept': 'text/plain', 'Content-Type': 'text/plain'},
            expect_errors=True
        )

        self.assertEqual(resp.status_int, 400)

    def test_should_fail_put_secret_with_existing_datum(self):
        # Force error due to secret already having data
        self.secret.encrypted_data = [self.datum]

        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            'plain text',
            headers={'Accept': 'text/plain', 'Content-Type': 'text/plain'},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 409)

    def test_should_fail_due_to_empty_payload(self):
        self.secret.encrypted_data = []

        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            '',
            headers={'Accept': 'text/plain', 'Content-Type': 'text/plain'},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_should_fail_due_to_plain_text_too_large(self):
        big_text = ''.join(['A' for x in xrange(
            2 * validators.DEFAULT_MAX_SECRET_BYTES)])

        self.secret.encrypted_data = []

        resp = self.app.put(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            big_text,
            headers={'Accept': 'text/plain', 'Content-Type': 'text/plain'},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 413)

    def test_should_delete_secret(self):
        self.app.delete(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id)
        )
        self.secret_repo.delete_entity_by_id \
            .assert_called_once_with(entity_id=self.secret.id,
                                     keystone_id=self.keystone_id)

    def test_should_throw_exception_for_delete_when_secret_not_found(self):
        self.secret_repo.delete_entity_by_id.side_effect = excep.NotFound(
            "Test not found exception")

        resp = self.app.delete(
            '/%s/secrets/%s/' % (self.keystone_id, self.secret.id),
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)


class WhenCreatingOrdersUsingOrdersResource(FunctionalTest):
    def setUp(self):
        super(
            WhenCreatingOrdersUsingOrdersResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            orders = controllers.orders.OrdersController(self.tenant_repo,
                                                         self.order_repo,
                                                         self.queue_resource)

        return RootController()

    def _init(self):
        self.secret_name = 'name'
        self.secret_payload_content_type = 'application/octet-stream'
        self.secret_algorithm = "aes"
        self.secret_bit_length = 128
        self.secret_mode = "cbc"

        self.tenant_internal_id = 'tenantid1234'
        self.tenant_keystone_id = 'keystoneid1234'

        self.tenant = models.Tenant()
        self.tenant.id = self.tenant_internal_id
        self.tenant.keystone_id = self.tenant_keystone_id

        self.tenant_repo = mock.MagicMock()
        self.tenant_repo.get.return_value = self.tenant

        self.order_repo = mock.MagicMock()
        self.order_repo.create_from.return_value = None

        self.queue_resource = mock.MagicMock()
        self.queue_resource.process_order.return_value = None

        self.order_req = {
            'secret': {
                'name': self.secret_name,
                'payload_content_type':
                self.secret_payload_content_type,
                'algorithm': self.secret_algorithm,
                'bit_length': self.secret_bit_length,
                'mode': self.secret_mode
            }
        }

    def test_should_add_new_order(self):
        resp = self.app.post_json(
            '/%s/orders/' % self.tenant_keystone_id,
            self.order_req
        )
        self.assertEqual(resp.status_int, 202)

        self.queue_resource.process_order \
            .assert_called_once_with(order_id=None,
                                     keystone_id=self.tenant_keystone_id)

        args, kwargs = self.order_repo.create_from.call_args
        order = args[0]
        self.assertIsInstance(order, models.Order)

    def test_should_fail_add_new_order_no_secret(self):
        resp = self.app.post_json(
            '/%s/orders/' % self.tenant_keystone_id,
            {},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_should_fail_add_new_order_bad_json(self):
        resp = self.app.post(
            '/%s/orders/' % self.tenant_keystone_id,
            '',
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)


class WhenGettingOrdersListUsingOrdersResource(FunctionalTest):
    def setUp(self):
        super(
            WhenGettingOrdersListUsingOrdersResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            orders = controllers.orders.OrdersController(self.tenant_repo,
                                                         self.order_repo,
                                                         self.queue_resource)

        return RootController()

    def _init(self):
        self.tenant_id = 'tenant1234'
        self.keystone_id = 'keystoneid1234'
        self.name = 'name1234'
        self.mime_type = 'text/plain'
        self.secret_algorithm = "algo"
        self.secret_bit_length = 512
        self.secret_mode = "cytype"
        self.params = {'offset': 2, 'limit': 2}

        self.num_orders = 10
        self.offset = 2
        self.limit = 2

        order_params = {'name': self.name,
                        'algorithm': self.secret_algorithm,
                        'bit_length': self.secret_bit_length,
                        'mode': self.secret_mode}

        self.orders = [create_order(id_ref='id' + str(id), **order_params) for
                       id in xrange(self.num_orders)]
        self.total = len(self.orders)
        self.order_repo = mock.MagicMock()
        self.order_repo.get_by_create_date.return_value = (self.orders,
                                                           self.offset,
                                                           self.limit,
                                                           self.total)
        self.tenant_repo = mock.MagicMock()

        self.queue_resource = mock.MagicMock()
        self.queue_resource.process_order.return_value = None

        self.params = {
            'offset': self.offset,
            'limit': self.limit
        }

    def test_should_get_list_orders(self):
        resp = self.app.get('/%s/orders/' % self.keystone_id, self.params)

        self.order_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True)

        self.assertTrue('previous' in resp.namespace)
        self.assertTrue('next' in resp.namespace)

        url_nav_next = self._create_url(self.keystone_id,
                                        self.offset + self.limit, self.limit)
        self.assertTrue(resp.body.count(url_nav_next) == 1)

        url_nav_prev = self._create_url(self.keystone_id,
                                        0, self.limit)
        self.assertTrue(resp.body.count(url_nav_prev) == 1)

        url_hrefs = self._create_url(self.keystone_id)
        self.assertTrue(resp.body.count(url_hrefs) ==
                        (self.num_orders + 2))

    def test_response_should_include_total(self):
        resp = self.app.get('/%s/orders/' % self.keystone_id, self.params)
        self.assertIn('total', resp.namespace)
        self.assertEqual(resp.namespace['total'], self.total)

    def test_should_handle_no_orders(self):

        del self.orders[:]

        resp = self.app.get('/%s/orders/' % self.keystone_id, self.params)

        self.order_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True)

        self.assertFalse('previous' in resp.namespace)
        self.assertFalse('next' in resp.namespace)

    def _create_url(self, keystone_id, offset_arg=None, limit_arg=None):
        if limit_arg:
            offset = int(offset_arg)
            limit = int(limit_arg)
            return '/{0}/orders?limit={1}&offset={2}'.format(keystone_id,
                                                             limit,
                                                             offset)
        else:
            return '/{0}/orders'.format(self.keystone_id)


class WhenGettingOrDeletingOrderUsingOrderResource(FunctionalTest):
    def setUp(self):
        super(
            WhenGettingOrDeletingOrderUsingOrderResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            orders = controllers.orders.OrdersController(self.tenant_repo,
                                                         self.order_repo,
                                                         self.queue_resource)

        return RootController()

    def _init(self):
        self.tenant_keystone_id = 'keystoneid1234'
        self.requestor = 'requestor1234'

        self.order = create_order(id_ref="id1", name="name")

        self.order_repo = mock.MagicMock()
        self.order_repo.get.return_value = self.order
        self.order_repo.delete_entity_by_id.return_value = None

        self.tenant_repo = mock.MagicMock()
        self.queue_resource = mock.MagicMock()

    def test_should_get_order(self):
        self.app.get('/%s/orders/%s/' % (self.tenant_keystone_id,
                                         self.order.id))

        self.order_repo.get \
            .assert_called_once_with(entity_id=self.order.id,
                                     keystone_id=self.tenant_keystone_id,
                                     suppress_exception=True)

    def test_should_delete_order(self):
        self.app.delete('/%s/orders/%s/' % (self.tenant_keystone_id,
                                            self.order.id))
        self.order_repo.delete_entity_by_id \
            .assert_called_once_with(entity_id=self.order.id,
                                     keystone_id=self.tenant_keystone_id)

    def test_should_throw_exception_for_get_when_order_not_found(self):
        self.order_repo.get.return_value = None
        resp = self.app.get(
            '/%s/orders/%s/' % (self.tenant_keystone_id, self.order.id),
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

    def test_should_throw_exception_for_delete_when_order_not_found(self):
        self.order_repo.delete_entity_by_id.side_effect = excep.NotFound(
            "Test not found exception")
        resp = self.app.delete(
            '/%s/orders/%s/' % (self.tenant_keystone_id, self.order.id),
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)


class WhenAddingNavigationHrefs(testtools.TestCase):

    def setUp(self):
        super(WhenAddingNavigationHrefs, self).setUp()

        self.resource_name = 'orders'
        self.keystone_id = '12345'
        self.num_elements = 100
        self.data = dict()

    def test_add_nav_hrefs_adds_next_only(self):
        offset = 0
        limit = 10

        data_with_hrefs = controllers.hrefs.add_nav_hrefs(self.resource_name,
                                                          self.keystone_id,
                                                          offset, limit,
                                                          self.num_elements,
                                                          self.data)

        self.assertNotIn('previous', data_with_hrefs)
        self.assertIn('next', data_with_hrefs)

    def test_add_nav_hrefs_adds_both_next_and_previous(self):
        offset = 10
        limit = 10

        data_with_hrefs = controllers.hrefs.add_nav_hrefs(self.resource_name,
                                                          self.keystone_id,
                                                          offset, limit,
                                                          self.num_elements,
                                                          self.data)

        self.assertIn('previous', data_with_hrefs)
        self.assertIn('next', data_with_hrefs)

    def test_add_nav_hrefs_adds_previous_only(self):
        offset = 90
        limit = 10

        data_with_hrefs = controllers.hrefs.add_nav_hrefs(self.resource_name,
                                                          self.keystone_id,
                                                          offset, limit,
                                                          self.num_elements,
                                                          self.data)

        self.assertIn('previous', data_with_hrefs)
        self.assertNotIn('next', data_with_hrefs)


class TestingJsonSanitization(testtools.TestCase):

    def test_json_sanitization_without_array(self):
        json_without_array = {"name": "name", "algorithm": "AES",
                              "payload_content_type": "  text/plain   ",
                              "mode": "CBC", "bit_length": 256,
                              "payload": "not-encrypted"}

        self.assertTrue(json_without_array['payload_content_type']
                        .startswith(' '), "whitespace should be there")
        self.assertTrue(json_without_array['payload_content_type']
                        .endswith(' '), "whitespace should be there")
        strip_whitespace(json_without_array)
        self.assertFalse(json_without_array['payload_content_type']
                         .startswith(' '), "whitespace should be gone")
        self.assertFalse(json_without_array['payload_content_type']
                         .endswith(' '), "whitespace should be gone")

    def test_json_sanitization_with_array(self):
        json_with_array = {"name": "name", "algorithm": "AES",
                           "payload_content_type": "text/plain",
                           "mode": "CBC", "bit_length": 256,
                           "payload": "not-encrypted",
                           "an-array":
                           [{"name": " item 1"},
                            {"name": "item2 "}]}

        self.assertTrue(json_with_array['an-array'][0]['name']
                        .startswith(' '), "whitespace should be there")
        self.assertTrue(json_with_array['an-array'][1]['name']
                        .endswith(' '), "whitespace should be there")
        strip_whitespace(json_with_array)
        self.assertFalse(json_with_array['an-array'][0]['name']
                         .startswith(' '), "whitespace should be gone")
        self.assertFalse(json_with_array['an-array'][1]['name']
                         .endswith(' '), "whitespace should be gone")


class WhenCreatingContainersUsingContainersResource(FunctionalTest):
    def setUp(self):
        super(
            WhenCreatingContainersUsingContainersResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            containers = controllers.containers.ContainersController(
                self.tenant_repo, self.container_repo, self.secret_repo
            )

        return RootController()

    def _init(self):
        self.name = 'test container name'
        self.type = 'generic'
        self.secret_refs = [
            {
                'name': 'test secret 1',
                'secret_ref': '123'
            },
            {
                'name': 'test secret 2',
                'secret_ref': '123'
            },
            {
                'name': 'test secret 3',
                'secret_ref': '123'
            }
        ]

        self.tenant_internal_id = 'tenantid1234'
        self.tenant_keystone_id = 'keystoneid1234'

        self.tenant = models.Tenant()
        self.tenant.id = self.tenant_internal_id
        self.tenant.keystone_id = self.tenant_keystone_id

        self.tenant_repo = mock.MagicMock()
        self.tenant_repo.get.return_value = self.tenant

        self.container_repo = mock.MagicMock()
        self.container_repo.create_from.return_value = None

        self.secret_repo = mock.MagicMock()
        self.secret_repo.create_from.return_value = None

        self.container_req = {'name': self.name,
                              'type': self.type,
                              'secret_refs': self.secret_refs}

    def test_should_add_new_container(self):
        resp = self.app.post_json(
            '/%s/containers/' % self.tenant_keystone_id,
            self.container_req
        )
        self.assertEqual(resp.status_int, 202)

        args, kwargs = self.container_repo.create_from.call_args
        container = args[0]
        self.assertIsInstance(container, models.Container)

    def test_should_fail_container_bad_json(self):
        resp = self.app.post(
            '/%s/containers/' % self.tenant_keystone_id,
            '',
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_should_throw_exception_when_secret_ref_doesnt_exist(self):
        self.secret_repo.get.return_value = None
        resp = self.app.post_json(
            '/%s/containers/' % self.tenant_keystone_id,
            self.container_req,
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)


class WhenGettingOrDeletingContainerUsingContainerResource(FunctionalTest):
    def setUp(self):
        super(
            WhenGettingOrDeletingContainerUsingContainerResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            containers = controllers.containers.ContainersController(
                self.tenant_repo, self.container_repo, self.secret_repo
            )

        return RootController()

    def _init(self):
        self.tenant_keystone_id = 'keystoneid1234'
        self.tenant_internal_id = 'tenantid1234'

        self.tenant = models.Tenant()
        self.tenant.id = self.tenant_internal_id
        self.tenant.keystone_id = self.tenant_keystone_id

        self.tenant_repo = mock.MagicMock()
        self.tenant_repo.get.return_value = self.tenant

        self.container = create_container(id_ref='id1')

        self.container_repo = mock.MagicMock()
        self.container_repo.get.return_value = self.container
        self.container_repo.delete_entity_by_id.return_value = None

        self.secret_repo = mock.MagicMock()

    def test_should_get_container(self):
        self.app.get('/%s/containers/%s/' % (
            self.tenant_keystone_id, self.container.id
        ))

        self.container_repo.get \
            .assert_called_once_with(entity_id=self.container.id,
                                     keystone_id=self.tenant_keystone_id,
                                     suppress_exception=True)

    def test_should_delete_container(self):
        self.app.delete('/%s/containers/%s/' % (
            self.tenant_keystone_id, self.container.id
        ))

        self.container_repo.delete_entity_by_id \
            .assert_called_once_with(entity_id=self.container.id,
                                     keystone_id=self.tenant_keystone_id)

    def test_should_throw_exception_for_get_when_container_not_found(self):
        self.container_repo.get.return_value = None
        resp = self.app.get('/%s/containers/%s/' % (
            self.tenant_keystone_id, self.container.id
        ), expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_should_throw_exception_for_delete_when_container_not_found(self):
        self.container_repo.delete_entity_by_id.side_effect = excep.NotFound(
            "Test not found exception")

        resp = self.app.delete('/%s/containers/%s/' % (
            self.tenant_keystone_id, self.container.id
        ), expect_errors=True)
        self.assertEqual(resp.status_int, 404)


class WhenGettingContainersListUsingResource(FunctionalTest):
    def setUp(self):
        super(
            WhenGettingContainersListUsingResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            containers = controllers.containers.ContainersController(
                self.tenant_repo, self.container_repo, self.secret_repo
            )

        return RootController()

    def _init(self):
        self.tenant_id = 'tenant1234'
        self.keystone_id = 'keystoneid1234'

        self.num_containers = 10
        self.offset = 2
        self.limit = 2

        self.containers = [create_container(id_ref='id' + str(id_ref)) for
                           id_ref in xrange(self.num_containers)]
        self.total = len(self.containers)
        self.container_repo = mock.MagicMock()
        self.container_repo.get_by_create_date.return_value = (self.containers,
                                                               self.offset,
                                                               self.limit,
                                                               self.total)
        self.tenant_repo = mock.MagicMock()
        self.secret_repo = mock.MagicMock()

        self.params = {
            'offset': self.offset,
            'limit': self.limit,
        }

    def test_should_get_list_containers(self):
        resp = self.app.get(
            '/%s/containers/' % self.keystone_id,
            self.params
        )

        self.container_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True)

        self.assertTrue('previous' in resp.namespace)
        self.assertTrue('next' in resp.namespace)

        url_nav_next = self._create_url(self.keystone_id,
                                        self.offset + self.limit, self.limit)
        self.assertTrue(resp.body.count(url_nav_next) == 1)

        url_nav_prev = self._create_url(self.keystone_id,
                                        0, self.limit)
        self.assertTrue(resp.body.count(url_nav_prev) == 1)

        url_hrefs = self._create_url(self.keystone_id)
        self.assertTrue(resp.body.count(url_hrefs) ==
                        (self.num_containers + 2))

    def test_response_should_include_total(self):
        resp = self.app.get(
            '/%s/containers/' % self.keystone_id,
            self.params
        )
        self.assertIn('total', resp.namespace)
        self.assertEqual(resp.namespace['total'], self.total)

    def test_should_handle_no_containers(self):

        del self.containers[:]

        resp = self.app.get(
            '/%s/containers/' % self.keystone_id,
            self.params
        )

        self.container_repo.get_by_create_date \
            .assert_called_once_with(self.keystone_id,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True)

        self.assertFalse('previous' in resp.namespace)
        self.assertFalse('next' in resp.namespace)

    def _create_url(self, keystone_id, offset_arg=None, limit_arg=None):
        if limit_arg:
            offset = int(offset_arg)
            limit = int(limit_arg)
            return '/{0}/containers' \
                   '?limit={1}&offset={2}'.format(keystone_id,
                                                  limit, offset)
        else:
            return '/{0}/containers'.format(self.keystone_id)

########NEW FILE########
__FILENAME__ = test_resources_policy
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This test module focuses on RBAC interactions with the API resource classes.
For typical-flow business logic tests of these classes, see the
'resources_test.py' module.
"""

import os

import testtools

import mock
from oslo.config import cfg
from webob import exc

from barbican.api.controllers import orders
from barbican.api.controllers import secrets
from barbican.api.controllers import versions
from barbican import context
from barbican.openstack.common import policy


CONF = cfg.CONF

# Point to the policy.json file located in source control.
TEST_VAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '../../../etc', 'barbican'))

ENFORCER = policy.Enforcer()


class TestableResource(object):

    def __init__(self, *args, **kwargs):
        self.controller = self.controller_cls(*args, **kwargs)

    def on_get(self, req, resp, *args, **kwargs):
        with mock.patch('pecan.request', req):
            with mock.patch('pecan.response', resp):
                return self.controller.index(*args, **kwargs)

    def on_post(self, req, resp, *args, **kwargs):
        with mock.patch('pecan.request', req):
            with mock.patch('pecan.response', resp):
                return self.controller.on_post(*args, **kwargs)

    def on_put(self, req, resp, *args, **kwargs):
        with mock.patch('pecan.request', req):
            with mock.patch('pecan.response', resp):
                return self.controller.on_put(*args, **kwargs)

    def on_delete(self, req, resp, *args, **kwargs):
        with mock.patch('pecan.request', req):
            with mock.patch('pecan.response', resp):
                return self.controller.on_delete(*args, **kwargs)


class VersionResource(TestableResource):
    controller_cls = versions.VersionController


class SecretsResource(TestableResource):
    controller_cls = secrets.SecretsController


class SecretResource(TestableResource):
    controller_cls = secrets.SecretController


class OrdersResource(TestableResource):
    controller_cls = orders.OrdersController


class OrderResource(TestableResource):
    controller_cls = orders.OrderController


class BaseTestCase(testtools.TestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        CONF(args=['--config-dir', TEST_VAR_DIR])
        self.policy_enforcer = ENFORCER
        self.policy_enforcer.load_rules(True)
        self.resp = mock.MagicMock()

    def _generate_req(self, roles=None, accept=None):
        """Generate a fake HTTP request with security context added to it."""
        req = mock.MagicMock()
        req.get_param.return_value = None

        kwargs = {
            'user': None,
            'tenant': None,
            'roles': roles or [],
            'policy_enforcer': self.policy_enforcer,
        }
        req.environ = {}
        req.environ['barbican.context'] = context.RequestContext(**kwargs)
        if accept:
            req.accept.header_value.return_value = accept
        else:
            req.accept = None

        return req

    def _generate_stream_for_exit(self):
        """Mock HTTP stream generator, to force RBAC-pass exit.

        Generate a fake HTTP request stream that forces an IOError to
        occur, which short circuits API resource processing when RBAC
        checks under test here pass.
        """
        stream = mock.MagicMock()
        read = mock.MagicMock(return_value=None, side_effect=IOError())
        stream.read = read
        return stream

    def _assert_post_rbac_exception(self, exception, role):
        """Assert that we received the expected RBAC-passed exception."""
        self.assertEqual(500, exception.status_int)

    def _generate_get_error(self):
        """Falcon exception generator to throw from early-exit mocks.

        Creates an exception that should be raised by GET tests that pass
        RBAC. This allows such flows to short-circuit normal post-RBAC
        processing that is not tested in this module.

        :return: Python exception that should be raised by repo get methods.
        """
        # The 'Read Error' clause needs to match that asserted in
        #    _assert_post_rbac_exception() above.
        return exc.HTTPInternalServerError(message='Read Error')

    def _assert_pass_rbac(self, roles, method_under_test, accept=None):
        """Assert that RBAC authorization rules passed for the specified roles.

        :param roles: List of roles to check, one at a time
        :param method_under_test: The test method to invoke for each role.
        :param accept Optional Accept header to set on the HTTP request
        :return: None
        """
        for role in roles:
            self.req = self._generate_req(roles=[role] if role else [],
                                          accept=accept)

            # Force an exception early past the RBAC passing.
            self.req.body_file = self._generate_stream_for_exit()
            exception = self.assertRaises(exc.HTTPInternalServerError,
                                          method_under_test)
            self._assert_post_rbac_exception(exception, role)

            self.setUp()  # Need to re-setup

    def _assert_fail_rbac(self, roles, method_under_test, accept=None):
        """Assert that RBAC rules failed for one of the specified roles.

        :param roles: List of roles to check, one at a time
        :param method_under_test: The test method to invoke for each role.
        :param accept Optional Accept header to set on the HTTP request
        :return: None
        """
        for role in roles:
            self.req = self._generate_req(roles=[role] if role else [],
                                          accept=accept)

            exception = self.assertRaises(exc.HTTPForbidden, method_under_test)
            self.assertEqual(403, exception.status_int)

            self.setUp()  # Need to re-setup


class WhenTestingVersionResource(BaseTestCase):
    """RBAC tests for the barbican.api.resources.VersionResource class."""
    def setUp(self):
        super(WhenTestingVersionResource, self).setUp()

        self.resource = VersionResource()

    def test_rules_should_be_loaded(self):
        self.assertIsNotNone(self.policy_enforcer.rules)

    def test_should_pass_get_version(self):
        # Can't use base method that short circuits post-RBAC processing here,
        # as version GET is trivial
        for role in ['admin', 'observer', 'creator', 'audit']:
            self.req = self._generate_req(roles=[role] if role else [])
            self._invoke_on_get()
            self.setUp()  # Need to re-setup

    def test_should_pass_get_version_with_bad_roles(self):
        self.req = self._generate_req(roles=[None, 'bunkrolehere'])
        self._invoke_on_get()

    def test_should_pass_get_version_with_no_roles(self):
        self.req = self._generate_req()
        self._invoke_on_get()

    def test_should_pass_get_version_multiple_roles(self):
        self.req = self._generate_req(roles=['admin', 'observer', 'creator',
                                             'audit'])
        self._invoke_on_get()

    def _invoke_on_get(self):
        self.resource.on_get(self.req, self.resp)


class WhenTestingSecretsResource(BaseTestCase):
    """RBAC tests for the barbican.api.resources.SecretsResource class."""
    def setUp(self):
        super(WhenTestingSecretsResource, self).setUp()

        self.keystone_id = '12345'

        # Force an error on GET calls that pass RBAC, as we are not testing
        #   such flows in this test module.
        self.secret_repo = mock.MagicMock()
        get_by_create_date = mock.MagicMock(return_value=None,
                                            side_effect=self
                                            ._generate_get_error())
        self.secret_repo.get_by_create_date = get_by_create_date

        self.resource = SecretsResource(crypto_manager=mock.MagicMock(),
                                        tenant_repo=mock.MagicMock(),
                                        secret_repo=self.secret_repo,
                                        tenant_secret_repo=mock
                                        .MagicMock(),
                                        datum_repo=mock.MagicMock(),
                                        kek_repo=mock.MagicMock())

    def test_rules_should_be_loaded(self):
        self.assertIsNotNone(self.policy_enforcer.rules)

    def test_should_pass_create_secret(self):
        self._assert_pass_rbac(['admin', 'creator'], self._invoke_on_post)

    def test_should_fail_create_secret(self):
        self._assert_fail_rbac([None, 'audit', 'observer', 'bogus'],
                               self._invoke_on_post)

    def test_should_pass_get_secrets(self):
        self._assert_pass_rbac(['admin', 'observer', 'creator'],
                               self._invoke_on_get)

    def test_should_fail_get_secrets(self):
        self._assert_fail_rbac([None, 'audit', 'bogus'],
                               self._invoke_on_get)

    def _invoke_on_post(self):
        self.resource.on_post(self.req, self.resp, self.keystone_id)

    def _invoke_on_get(self):
        self.resource.on_get(self.req, self.resp, self.keystone_id)


class WhenTestingSecretResource(BaseTestCase):
    """RBAC tests for the barbican.api.resources.SecretResource class."""
    def setUp(self):
        super(WhenTestingSecretResource, self).setUp()

        self.keystone_id = '12345tenant'
        self.secret_id = '12345secret'

        # Force an error on GET and DELETE calls that pass RBAC,
        #   as we are not testing such flows in this test module.
        self.secret_repo = mock.MagicMock()
        fail_method = mock.MagicMock(return_value=None,
                                     side_effect=self._generate_get_error())
        self.secret_repo.get = fail_method
        self.secret_repo.delete_entity_by_id = fail_method

        self.resource = SecretResource(self.secret_id,
                                       crypto_manager=mock.MagicMock(),
                                       tenant_repo=mock.MagicMock(),
                                       secret_repo=self.secret_repo,
                                       datum_repo=mock.MagicMock(),
                                       kek_repo=mock.MagicMock())

    def test_rules_should_be_loaded(self):
        self.assertIsNotNone(self.policy_enforcer.rules)

    def test_should_pass_decrypt_secret(self):
        self._assert_pass_rbac(['admin', 'observer', 'creator'],
                               self._invoke_on_get,
                               accept='notjsonaccepttype')

    def test_should_fail_decrypt_secret(self):
        self._assert_fail_rbac([None, 'audit', 'bogus'],
                               self._invoke_on_get,
                               accept='notjsonaccepttype')

    def test_should_pass_get_secret(self):
        self._assert_pass_rbac(['admin', 'observer', 'creator', 'audit'],
                               self._invoke_on_get)

    def test_should_fail_get_secret(self):
        self._assert_fail_rbac([None, 'bogus'],
                               self._invoke_on_get)

    def test_should_pass_put_secret(self):
        self._assert_pass_rbac(['admin', 'creator'], self._invoke_on_put)

    def test_should_fail_put_secret(self):
        self._assert_fail_rbac([None, 'audit', 'observer', 'bogus'],
                               self._invoke_on_put)

    def test_should_pass_delete_secret(self):
        self._assert_pass_rbac(['admin'], self._invoke_on_delete)

    def test_should_fail_delete_secret(self):
        self._assert_fail_rbac([None, 'audit', 'observer', 'creator', 'bogus'],
                               self._invoke_on_delete)

    def _invoke_on_get(self):
        self.resource.on_get(self.req, self.resp,
                             self.keystone_id)

    def _invoke_on_put(self):
        self.resource.on_put(self.req, self.resp,
                             self.keystone_id)

    def _invoke_on_delete(self):
        self.resource.on_delete(self.req, self.resp,
                                self.keystone_id)


class WhenTestingOrdersResource(BaseTestCase):
    """RBAC tests for the barbican.api.resources.OrdersResource class."""
    def setUp(self):
        super(WhenTestingOrdersResource, self).setUp()

        self.keystone_id = '12345'

        # Force an error on GET calls that pass RBAC, as we are not testing
        #   such flows in this test module.
        self.order_repo = mock.MagicMock()
        get_by_create_date = mock.MagicMock(return_value=None,
                                            side_effect=self
                                            ._generate_get_error())
        self.order_repo.get_by_create_date = get_by_create_date

        self.resource = OrdersResource(tenant_repo=mock.MagicMock(),
                                       order_repo=self.order_repo,
                                       queue_resource=mock.MagicMock())

    def test_rules_should_be_loaded(self):
        self.assertIsNotNone(self.policy_enforcer.rules)

    def test_should_pass_create_order(self):
        self._assert_pass_rbac(['admin', 'creator'], self._invoke_on_post)

    def test_should_fail_create_order(self):
        self._assert_fail_rbac([None, 'audit', 'observer', 'bogus'],
                               self._invoke_on_post)

    def test_should_pass_get_orders(self):
        self._assert_pass_rbac(['admin', 'observer', 'creator'],
                               self._invoke_on_get)

    def test_should_fail_get_orders(self):
        self._assert_fail_rbac([None, 'audit', 'bogus'],
                               self._invoke_on_get)

    def _invoke_on_post(self):
        self.resource.on_post(self.req, self.resp, self.keystone_id)

    def _invoke_on_get(self):
        self.resource.on_get(self.req, self.resp, self.keystone_id)


class WhenTestingOrderResource(BaseTestCase):
    """RBAC tests for the barbican.api.resources.OrderResource class."""
    def setUp(self):
        super(WhenTestingOrderResource, self).setUp()

        self.keystone_id = '12345tenant'
        self.order_id = '12345order'

        # Force an error on GET and DELETE calls that pass RBAC,
        #   as we are not testing such flows in this test module.
        self.order_repo = mock.MagicMock()
        fail_method = mock.MagicMock(return_value=None,
                                     side_effect=self._generate_get_error())
        self.order_repo.get = fail_method
        self.order_repo.delete_entity_by_id = fail_method

        self.resource = OrderResource(self.order_id,
                                      order_repo=self.order_repo)

    def test_rules_should_be_loaded(self):
        self.assertIsNotNone(self.policy_enforcer.rules)

    def test_should_pass_get_order(self):
        self._assert_pass_rbac(['admin', 'observer', 'creator', 'audit'],
                               self._invoke_on_get)

    def test_should_fail_get_order(self):
        self._assert_fail_rbac([None, 'bogus'],
                               self._invoke_on_get)

    def test_should_pass_delete_order(self):
        self._assert_pass_rbac(['admin'], self._invoke_on_delete)

    def test_should_fail_delete_order(self):
        self._assert_fail_rbac([None, 'audit', 'observer', 'creator', 'bogus'],
                               self._invoke_on_delete)

    def _invoke_on_get(self):
        self.resource.on_get(self.req, self.resp, self.keystone_id)

    def _invoke_on_delete(self):
        self.resource.on_delete(self.req, self.resp, self.keystone_id)

########NEW FILE########
__FILENAME__ = test_transport_keys_resource
# Copyright (c) 2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This test module focuses on typical-flow business logic tests with the
transport key resource classes.
"""

import mock
import pecan
import testtools
import webtest

from barbican.api import app
from barbican.api import controllers
from barbican.common import exception as excep
from barbican.model import models

SAMPLE_TRANSPORT_KEY = """
    -----BEGIN CERTIFICATE-----
    MIIDlDCCAnygAwIBAgIBGDANBgkqhkiG9w0BAQsFADBCMR8wHQYDVQQKDBZ0b21j
    YXQgMjggZG9tYWluIHRyeSAzMR8wHQYDVQQDDBZDQSBTaWduaW5nIENlcnRpZmlj
    YXRlMB4XDTE0MDMyNzA0MTU0OFoXDTE2MDMxNjA0MTU0OFowRTEfMB0GA1UECgwW
    dG9tY2F0IDI4IGRvbWFpbiB0cnkgMzEiMCAGA1UEAwwZRFJNIFRyYW5zcG9ydCBD
    ZXJ0aWZpY2F0ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANEjiTHn
    xWKKnzgBzR8kHo5YKXDbYi01ar0pAiJQ8Xx4MXj3Uf6ckfxvJ7Icb2PhigAgINLe
    td8butAXM0164kHeEMJWI2TG/+2f42Kla2KeU0bdgKbw1egyZreDvhGk/3P46LQt
    LtRBCb5eQWS2gTFocgA5phzRQnmSS4BRTh1MnGxaFLZsPOXqZKptAYaeXyLG63vL
    woBwFVGoodHrRrpYpCd+D6JABBdUEgSCaYG9JBDC5ElSjJnBlCNrUZ2kxokxbsQp
    UHm70LV9c+5n0o1VLJSqnUDuOkoovVWytlKbz0dw0KiTUDjkb4F4D6s+IePV1ufJ
    6cXvXCLLSQa42AcCAwEAAaOBkTCBjjAfBgNVHSMEGDAWgBSiQq7mBrAcTqqsPRvn
    l8pk4uZCWTBGBggrBgEFBQcBAQQ6MDgwNgYIKwYBBQUHMAGGKmh0dHA6Ly9hbGVl
    LXdvcmtwYy5yZWRoYXQuY29tOjgyODAvY2Evb2NzcDAOBgNVHQ8BAf8EBAMCBPAw
    EwYDVR0lBAwwCgYIKwYBBQUHAwIwDQYJKoZIhvcNAQELBQADggEBALmAtjactFHA
    d4nBFpwpwh3tGhkfwoSCuKThX54UXsJawQrx5gaxP0JE7YVLDRe4jn+RHjkXxdxX
    Xt4IugdTsPNq0nvWVAzwZwoGlJZjqghHpD3AB4E5DEoOnVnmJRLFLF0Xg/R5Sw3F
    j9wdVE/hGShrF+fOqNZhTG2Mf4f9TUR1Y8PtoBmtkwnFUoeiaI+Nq6Dd1Qw8ysar
    i/sOzOOjou4vcbYnrKnn2hlSgF6toza0BCGVA8fMyGBh16JtTR1REL7Bf0m3ZQDy
    4hjmPjvUTN3YO2RlLVZXArhhmqcQzCl94P37pAEN/JhAIYvQ2PPM/ofK9XHc9u9j
    rQJGkMpu7ck=
    -----END CERTIFICATE-----"""


def create_transport_key(id_ref="id",
                         plugin_name="default_plugin",
                         transport_key=None):
    """Generate a transport cert entity instance."""
    tkey = models.TransportKey(plugin_name, transport_key)
    tkey.id = id_ref
    return tkey


class FunctionalTest(testtools.TestCase):

    def setUp(self):
        super(FunctionalTest, self).setUp()
        root = self.root
        config = {'app': {'root': root}}
        pecan.set_config(config, overwrite=True)
        self.app = webtest.TestApp(pecan.make_app(root))

    def tearDown(self):
        super(FunctionalTest, self).tearDown()
        pecan.set_config({}, overwrite=True)

    @property
    def root(self):
        return controllers.versions.VersionController()


class WhenGettingTransKeysListUsingTransportKeysResource(FunctionalTest):
    def setUp(self):
        super(
            WhenGettingTransKeysListUsingTransportKeysResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            transport_keys = controllers.transportkeys.\
                TransportKeysController(self.repo)

        return RootController()

    def _init(self):
        self.plugin_name = "default_plugin"
        self.keystone_id = 'keystoneid1234'
        self.params = {'offset': 2, 'limit': 2}

        self.transport_key = SAMPLE_TRANSPORT_KEY
        self.num_keys = 10
        self.offset = 2
        self.limit = 2

        tk_params = {'plugin_name': self.plugin_name,
                     'transport_key': self.transport_key}

        self.tkeys = [create_transport_key(
            id_ref='id' + str(tkid), **tk_params)
            for tkid in xrange(self.num_keys)]
        self.total = len(self.tkeys)
        self.repo = mock.MagicMock()
        self.repo.get_by_create_date.return_value = (self.tkeys,
                                                     self.offset,
                                                     self.limit,
                                                     self.total)
        self.params = {
            'offset': self.offset,
            'limit': self.limit
        }

    def test_should_get_list_transport_keys(self):
        resp = self.app.get('/%s/transport_keys/' %
                            self.keystone_id, self.params)

        self.repo.get_by_create_date \
            .assert_called_once_with(plugin_name=None,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True)

        self.assertTrue('previous' in resp.namespace)
        self.assertTrue('next' in resp.namespace)

        url_nav_next = self._create_url(self.keystone_id,
                                        self.offset + self.limit, self.limit)
        self.assertTrue(resp.body.count(url_nav_next) == 1)

        url_nav_prev = self._create_url(self.keystone_id,
                                        0, self.limit)
        self.assertTrue(resp.body.count(url_nav_prev) == 1)

        url_hrefs = self._create_url(self.keystone_id)
        self.assertTrue(resp.body.count(url_hrefs) ==
                        (self.num_keys + 2))

    def test_response_should_include_total(self):
        resp = self.app.get('/%s/transport_keys/' %
                            self.keystone_id, self.params)
        self.assertIn('total', resp.namespace)
        self.assertEqual(resp.namespace['total'], self.total)

    def test_should_handle_no_transport_keys(self):

        del self.tkeys[:]

        resp = self.app.get('/%s/transport_keys/' %
                            self.keystone_id, self.params)

        self.repo.get_by_create_date \
            .assert_called_once_with(plugin_name=None,
                                     offset_arg=u'{0}'.format(self.offset),
                                     limit_arg=u'{0}'.format(self.limit),
                                     suppress_exception=True)

        self.assertFalse('previous' in resp.namespace)
        self.assertFalse('next' in resp.namespace)

    def _create_url(self, keystone_id, offset_arg=None, limit_arg=None):
        if limit_arg:
            offset = int(offset_arg)
            limit = int(limit_arg)
            return '/{0}/transport_keys?limit={1}&offset={2}'.format(
                keystone_id, limit, offset)
        else:
            return '/{0}/transport_keys'.format(self.keystone_id)


class WhenCreatingTransKeysListUsingTransportKeysResource(FunctionalTest):
    def setUp(self):
        super(
            WhenCreatingTransKeysListUsingTransportKeysResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            transport_keys = controllers.transportkeys.\
                TransportKeysController(self.repo)

        return RootController()

    def _init(self):
        self.plugin_name = "default_plugin"
        self.keystone_id = 'keystoneid1234'

        self.repo = mock.MagicMock()
        self.transport_key_req = {
            'plugin_name': self.plugin_name,
            'transport_key': SAMPLE_TRANSPORT_KEY
        }

    def test_should_add_new_transport_key(self):
        resp = self.app.post_json(
            '/%s/transport_keys/' % self.keystone_id,
            self.transport_key_req
        )
        self.assertEqual(resp.status_int, 201)

        args, kwargs = self.repo.create_from.call_args
        order = args[0]
        self.assertIsInstance(order, models.TransportKey)

    def test_should_fail_add_new_transport_key_no_secret(self):
        resp = self.app.post_json(
            '/%s/transport_keys/' % self.keystone_id,
            {},
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)

    def test_should_fail_add_new_transport_key_bad_json(self):
        resp = self.app.post(
            '/%s/transport_keys/' % self.keystone_id,
            '',
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 400)


class WhenGettingOrDeletingTransKeyUsingTransportKeyResource(FunctionalTest):

    def setUp(self):
        super(
            WhenGettingOrDeletingTransKeyUsingTransportKeyResource, self
        ).setUp()
        self.app = webtest.TestApp(app.PecanAPI(self.root))

    @property
    def root(self):
        self._init()

        class RootController(object):
            transport_keys = controllers.transportkeys.\
                TransportKeysController(self.repo)

        return RootController()

    def _init(self):
        self.tenant_keystone_id = 'keystoneid1234'
        self.transport_key = SAMPLE_TRANSPORT_KEY
        self.tkey_id = "id1"

        self.tkey = create_transport_key(
            id_ref=self.tkey_id,
            plugin_name="default_plugin",
            transport_key=self.transport_key)

        self.repo = mock.MagicMock()
        self.repo.get.return_value = self.tkey

    def test_should_get_transport_key(self):
        self.app.get('/%s/transport_keys/%s/' % (self.tenant_keystone_id,
                                                 self.tkey.id))

        self.repo.get.assert_called_once_with(entity_id=self.tkey.id)

    def test_should_throw_exception_for_get_when_trans_key_not_found(self):
        self.repo.get.return_value = None
        resp = self.app.get(
            '/%s/transport_keys/%s/' % (self.tenant_keystone_id, self.tkey.id),
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

    def test_should_delete_transport_key(self):
        self.app.delete('/%s/transport_keys/%s/' % (self.tenant_keystone_id,
                                                    self.tkey.id))
        self.repo.delete_entity_by_id \
            .assert_called_once_with(entity_id=self.tkey.id,
                                     keystone_id=self.tenant_keystone_id)

    def test_should_throw_exception_for_delete_when_trans_key_not_found(self):
        self.repo.delete_entity_by_id.side_effect = excep.NotFound(
            "Test not found exception")
        resp = self.app.delete(
            '/%s/transport_keys/%s/' % (self.tenant_keystone_id, self.tkey.id),
            expect_errors=True
        )
        self.assertEqual(resp.status_int, 404)

########NEW FILE########
__FILENAME__ = test_utils
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import mock
import testtools

from barbican.common import utils


class WhenTestingAcceptEncodingGetter(testtools.TestCase):

    def setUp(self):
        super(WhenTestingAcceptEncodingGetter, self).setUp()

        self.req = mock.Mock()

    def test_parses_accept_encoding_header(self):
        self.req.get_header.return_value = '*'
        ae = utils.get_accepted_encodings(self.req)
        self.req.get_header.assert_called_once_with('Accept-Encoding')
        self.assertEqual(ae, ['*'])

    def test_returns_none_for_empty_encoding(self):
        self.req.get_header.return_value = None
        ae = utils.get_accepted_encodings(self.req)
        self.assertIsNone(ae)

    def test_parses_single_accept_with_quality_value(self):
        self.req.get_header.return_value = 'base64;q=0.7'
        ae = utils.get_accepted_encodings(self.req)
        self.assertEqual(ae, ['base64'])

    def test_parses_more_than_one_encoding(self):
        self.req.get_header.return_value = 'base64, gzip'
        ae = utils.get_accepted_encodings(self.req)
        self.assertEqual(ae, ['base64', 'gzip'])

    def test_can_sort_by_quality_value(self):
        self.req.get_header.return_value = 'base64;q=0.5, gzip;q=0.6, compress'
        ae = utils.get_accepted_encodings(self.req)
        self.assertEqual(ae, ['compress', 'gzip', 'base64'])

########NEW FILE########
__FILENAME__ = test_validators
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import unittest

import testtools

from barbican.common import exception as excep
from barbican.common import validators


def suite():
    suite = unittest.TestSuite()

    suite.addTest(WhenTestingSecretValidator())

    return suite


class WhenTestingValidatorsFunctions(testtools.TestCase):

    def test_secret_too_big_is_false_for_small_secrets(self):
        data = b'\xb0'

        is_too_big = validators.secret_too_big(data)

        self.assertFalse(is_too_big)

    def test_secret_too_big_is_true_for_big_secrets(self):
        data = b'\x01' * validators.CONF.max_allowed_secret_in_bytes
        data += b'\x01'

        is_too_big = validators.secret_too_big(data)

        self.assertTrue(is_too_big)

    def test_secret_too_big_is_true_for_big_unicode_secrets(self):
        beer = u'\U0001F37A'
        data = beer * (validators.CONF.max_allowed_secret_in_bytes / 4)
        data += u'1'

        is_too_big = validators.secret_too_big(data)

        self.assertTrue(is_too_big)


class WhenTestingSecretValidator(testtools.TestCase):

    def setUp(self):
        super(WhenTestingSecretValidator, self).setUp()

        self.name = 'name'
        self.payload = b'not-encrypted'
        self.payload_content_type = 'text/plain'
        self.secret_algorithm = 'algo'
        self.secret_bit_length = 512
        self.secret_mode = 'cytype'

        self.secret_req = {'name': self.name,
                           'payload_content_type': self.payload_content_type,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        self.validator = validators.NewSecretValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.secret_req)

    def test_should_validate_no_name(self):
        del self.secret_req['name']
        self.validator.validate(self.secret_req)

    def test_should_validate_empty_name(self):
        self.secret_req['name'] = '    '
        self.validator.validate(self.secret_req)

    def test_should_validate_no_payload(self):
        del self.secret_req['payload']
        del self.secret_req['payload_content_type']
        result = self.validator.validate(self.secret_req)

        self.assertFalse('payload' in result)

    def test_should_validate_payload_with_whitespace(self):
        self.secret_req['payload'] = '  ' + self.payload + '    '
        result = self.validator.validate(self.secret_req)

        self.assertEqual(self.payload, result['payload'])

    def test_should_validate_future_expiration(self):
        self.secret_req['expiration'] = '2114-02-28T19:14:44.180394'
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))

    def test_should_validate_future_expiration_no_t(self):
        self.secret_req['expiration'] = '2114-02-28 19:14:44.180394'
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))

    def test_should_validate_expiration_with_z(self):
        expiration = '2114-02-28 19:14:44.180394Z'
        self.secret_req['expiration'] = expiration
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))
        self.assertEqual(expiration[:-1], str(result['expiration']))

    def test_should_validate_expiration_with_tz(self):
        expiration = '2114-02-28 12:14:44.180394-05:00'
        self.secret_req['expiration'] = expiration
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))
        expected = expiration[:-6].replace('12', '17', 1)
        self.assertEqual(expected, str(result['expiration']))

    def test_should_validate_expiration_extra_whitespace(self):
        expiration = '2114-02-28 12:14:44.180394-05:00      '
        self.secret_req['expiration'] = expiration
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))
        expected = expiration[:-12].replace('12', '17', 1)
        self.assertEqual(expected, str(result['expiration']))

    def test_should_validate_empty_expiration(self):
        self.secret_req['expiration'] = '  '
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(not result['expiration'])

    def test_should_fail_numeric_name(self):
        self.secret_req['name'] = 123

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('name', exception.invalid_property)

    def test_should_fail_negative_bit_length(self):
        self.secret_req['bit_length'] = -23

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('bit_length', exception.invalid_property)

    def test_should_fail_non_integer_bit_length(self):
        self.secret_req['bit_length'] = "23"

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('bit_length', exception.invalid_property)

    def test_validation_should_fail_with_empty_payload(self):
        self.secret_req['payload'] = '   '

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('payload', exception.invalid_property)

    def test_should_fail_already_expired(self):
        self.secret_req['expiration'] = '2004-02-28T19:14:44.180394'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('expiration', exception.invalid_property)

    def test_should_fail_expiration_nonsense(self):
        self.secret_req['expiration'] = 'nonsense'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('expiration', exception.invalid_property)

    def test_should_fail_all_nulls(self):
        self.secret_req = {'name': None,
                           'algorithm': None,
                           'bit_length': None,
                           'mode': None}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_fail_all_empties(self):
        self.secret_req = {'name': '',
                           'algorithm': '',
                           'bit_length': '',
                           'mode': ''}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_fail_no_payload_content_type(self):
        del self.secret_req['payload_content_type']

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_fail_with_message_w_bad_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'plain/text'

        try:
            self.validator.validate(self.secret_req)
        except excep.InvalidObject as e:
            self.assertNotEqual(str(e), 'None')
            self.assertIsNotNone(e.message)
            self.assertNotEqual(e.message, 'None')
        else:
            self.fail('No validation exception was raised')

    def test_should_validate_mixed_case_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TeXT/PlaiN'
        self.validator.validate(self.secret_req)

    def test_should_validate_upper_case_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TEXT/PLAIN'
        self.validator.validate(self.secret_req)

    def test_should_fail_with_mixed_case_wrong_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TeXT/PlaneS'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_fail_with_upper_case_wrong_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TEXT/PLANE'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_fail_with_plain_text_and_encoding(self):
        self.secret_req['payload_content_encoding'] = 'base64'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_fail_with_wrong_encoding(self):
        self.secret_req['payload_content_type'] = 'application/octet-stream'
        self.secret_req['payload_content_encoding'] = 'unsupported'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_validate_with_wrong_encoding(self):
        self.secret_req['payload_content_type'] = 'application/octet-stream'
        self.secret_req['payload_content_encoding'] = 'base64'

        self.validator.validate(self.secret_req)


class WhenTestingOrderValidator(testtools.TestCase):

    def setUp(self):
        super(WhenTestingOrderValidator, self).setUp()

        self.name = 'name'
        self.secret_algorithm = 'aes'
        self.secret_bit_length = 128
        self.secret_mode = 'cbc'
        self.secret_payload_content_type = 'application/octet-stream'

        self.secret_req = {'name': self.name,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload_content_type':
                           self.secret_payload_content_type}
        self.order_req = {'secret': self.secret_req}

        self.validator = validators.NewOrderValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.order_req)

    def test_should_validate_no_name(self):
        del self.secret_req['name']
        result = self.validator.validate(self.order_req)

        self.assertTrue('secret' in result)

    def test_should_validate_empty_name(self):
        self.secret_req['name'] = '    '
        result = self.validator.validate(self.order_req)

        self.assertTrue('secret' in result)

    def test_should_validate_future_expiration(self):
        self.secret_req['expiration'] = '2114-02-28T19:14:44.180394'
        result = self.validator.validate(self.order_req)

        self.assertTrue('secret' in result)
        result = result['secret']
        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))

    def test_should_validate_empty_expiration(self):
        self.secret_req['expiration'] = '  '
        result = self.validator.validate(self.order_req)

        self.assertTrue('secret' in result)
        result = result['secret']
        self.assertTrue('expiration' in result)
        self.assertTrue(not result['expiration'])

    def test_should_fail_numeric_name(self):
        self.secret_req['name'] = 123

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('name', exception.invalid_property)

    def test_should_fail_bad_mode(self):
        self.secret_req['mode'] = 'badmode'

        exception = self.assertRaises(
            excep.UnsupportedField,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('mode', exception.invalid_field)

    def test_should_fail_negative_bit_length(self):
        self.secret_req['bit_length'] = -23

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('bit_length', exception.invalid_property)

    def test_should_fail_non_integer_bit_length(self):
        self.secret_req['bit_length'] = "23"

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('bit_length', exception.invalid_property)

    def test_should_fail_non_multiple_eight_bit_length(self):
        self.secret_req['bit_length'] = 129

        exception = self.assertRaises(
            excep.UnsupportedField,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('bit_length', exception.invalid_field)

    def test_should_fail_secret_not_order_schema_provided(self):
        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

        self.assertEqual('secret', exception.invalid_property)

    def test_should_fail_payload_provided(self):
        self.secret_req['payload'] = '  '

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

        self.assertTrue('payload' in exception.invalid_property)

    def test_should_fail_already_expired(self):
        self.secret_req['expiration'] = '2004-02-28T19:14:44.180394'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('expiration', exception.invalid_property)

    def test_should_fail_expiration_nonsense(self):
        self.secret_req['expiration'] = 'nonsense'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('expiration', exception.invalid_property)

    def test_should_fail_all_nulls(self):
        self.secret_req = {'name': None,
                           'algorithm': None,
                           'bit_length': None,
                           'mode': None}
        self.order_req = {'secret': self.secret_req}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

    def test_should_fail_all_empties(self):
        self.secret_req = {'name': '',
                           'algorithm': '',
                           'bit_length': '',
                           'mode': ''}
        self.order_req = {'secret': self.secret_req}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.order_req,
        )

    def test_should_fail_no_payload_content_type(self):
        del self.secret_req['payload_content_type']

        self.assertRaises(
            excep.UnsupportedField,
            self.validator.validate,
            self.order_req,
        )

    def test_should_fail_unsupported_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'text/plain'

        self.assertRaises(
            excep.UnsupportedField,
            self.validator.validate,
            self.order_req,
        )

    def test_should_fail_empty_mode(self):
        del self.secret_req['mode']

        exception = self.assertRaises(
            excep.UnsupportedField,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('mode', exception.invalid_field)

    def test_should_fail_empty_algorithm(self):
        del self.secret_req['algorithm']

        exception = self.assertRaises(
            excep.UnsupportedField,
            self.validator.validate,
            self.order_req,
        )

        self.assertEqual('algorithm', exception.invalid_field)


class WhenTestingContainerValidator(testtools.TestCase):

    def setUp(self):
        super(WhenTestingContainerValidator, self).setUp()

        self.name = 'name'
        self.type = 'generic'
        self.secret_refs = [
            {
                'name': 'testname',
                'secret_ref': '123'
            },
            {
                'name': 'testname2',
                'secret_ref': '123'
            }
        ]

        self.container_req = {'name': self.name,
                              'type': self.type,
                              'secret_refs': self.secret_refs}

        self.validator = validators.ContainerValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.container_req)

    def test_should_validate_no_name(self):
        del self.container_req['name']
        self.validator.validate(self.container_req)

    def test_should_validate_empty_name(self):
        self.container_req['name'] = '    '
        self.validator.validate(self.container_req)

    def test_should_fail_no_type(self):
        del self.container_req['type']

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        #TODO(hgedikli): figure out why invalid_property is null here
        #self.assertEqual('type', e.exception.invalid_property)

    def test_should_fail_empty_type(self):
        self.container_req['type'] = ''

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('type', exception.invalid_property)

    def test_should_fail_not_supported_type(self):
        self.container_req['type'] = 'testtype'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('type', exception.invalid_property)

    def test_should_fail_numeric_name(self):
        self.container_req['name'] = 123

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('name', exception.invalid_property)

    def test_should_fail_all_nulls(self):
        self.container_req = {'name': None,
                              'type': None,
                              'bit_length': None,
                              'secret_refs': None}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_fail_all_empties(self):
        self.container_req = {'name': '',
                              'type': '',
                              'secret_refs': []}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_validate_empty_secret_refs(self):
        self.container_req['secret_refs'] = []
        self.validator.validate(self.container_req)

    def test_should_fail_no_secret_ref_in_secret_refs(self):
        del self.container_req['secret_refs'][0]['secret_ref']

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_fail_empty_secret_ref_in_secret_refs(self):
        self.container_req['secret_refs'][0]['secret_ref'] = ''

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_fail_numeric_secret_ref_in_secret_refs(self):
        self.container_req['secret_refs'][0]['secret_ref'] = 123

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_fail_duplicate_names_in_secret_refs(self):
        self.container_req['secret_refs'].append(
            self.container_req['secret_refs'][0])

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)


class WhenTestingRSAContainerValidator(testtools.TestCase):

    def setUp(self):
        super(WhenTestingRSAContainerValidator, self).setUp()

        self.name = 'name'
        self.type = 'rsa'
        self.secret_refs = [
            {
                'name': 'public_key',
                'secret_ref': '123'
            },
            {
                'name': 'private_key',
                'secret_ref': '123'
            },
            {
                'name': 'private_key_passphrase',
                'secret_ref': '123'
            }
        ]

        self.container_req = {'name': self.name,
                              'type': self.type,
                              'secret_refs': self.secret_refs}

        self.validator = validators.ContainerValidator()

    def test_should_fail_no_names_in_secret_refs(self):
        del self.container_req['secret_refs'][0]['name']

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_fail_empty_names_in_secret_refs(self):
        self.container_req['secret_refs'][0]['name'] = ''

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_fail_unsupported_names_in_secret_refs(self):
        self.container_req['secret_refs'][0]['name'] = 'testttt'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_fail_more_than_3_secret_refs(self):
        new_secret_ref = {
            'name': 'new secret ref',
            'secret_ref': '234234'
        }
        self.container_req['secret_refs'].append(new_secret_ref)

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dogtag_crypto
# Copyright (c) 2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import os
import tempfile
import testtools

try:
    from barbican.crypto.dogtag_crypto import DogtagCryptoPlugin
    from barbican.crypto.dogtag_crypto import DogtagPluginAlgorithmException
    from barbican.crypto import plugin as plugin_import
    from barbican.model import models
    imports_ok = True
except ImportError:
    # dogtag imports probably not available
    imports_ok = False


class WhenTestingDogtagCryptoPlugin(testtools.TestCase):

    def setUp(self):
        super(WhenTestingDogtagCryptoPlugin, self).setUp()
        if not imports_ok:
            return

        self.keyclient_mock = mock.MagicMock(name="KeyClient mock")
        self.patcher = mock.patch('pki.cryptoutil.NSSCryptoUtil')
        self.patcher.start()

        # create nss db for test only
        self.nss_dir = tempfile.mkdtemp()

        self.cfg_mock = mock.MagicMock(name='config mock')
        self.cfg_mock.dogtag_crypto_plugin = mock.MagicMock(
            nss_db_path=self.nss_dir)
        self.plugin = DogtagCryptoPlugin(self.cfg_mock)
        self.plugin.keyclient = self.keyclient_mock

    def tearDown(self):
        super(WhenTestingDogtagCryptoPlugin, self).tearDown()
        if not imports_ok:
            return
        self.patcher.stop()
        os.rmdir(self.nss_dir)

    def test_generate(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        secret = models.Secret()
        secret.bit_length = 128
        secret.algorithm = "AES"
        generate_dto = plugin_import.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            None,
            None)
        self.plugin.generate_symmetric(
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )

        self.keyclient_mock.generate_symmetric_key.assert_called_once_with(
            mock.ANY,
            secret.algorithm.upper(),
            secret.bit_length,
            mock.ANY)

    def test_generate_non_supported_algorithm(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        secret = models.Secret()
        secret.bit_length = 128
        secret.algorithm = "hmacsha256"
        generate_dto = plugin_import.GenerateDTO(
            plugin_import.PluginSupportTypes.SYMMETRIC_KEY_GENERATION,
            secret.algorithm,
            secret.bit_length,
            None)
        self.assertRaises(
            DogtagPluginAlgorithmException,
            self.plugin.generate_symmetric,
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )

    def test_raises_error_with_no_pem_path(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        m = mock.MagicMock()
        m.dogtag_crypto_plugin = mock.MagicMock(pem_path=None)
        self.assertRaises(
            ValueError,
            DogtagCryptoPlugin,
            m,
        )

    def test_raises_error_with_no_pem_password(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        m = mock.MagicMock()
        m.dogtag_crypto_plugin = mock.MagicMock(pem_password=None)
        self.assertRaises(
            ValueError,
            DogtagCryptoPlugin,
            m,
        )

    def test_raises_error_with_no_nss_password(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        m = mock.MagicMock()
        m.dogtag_crypto_plugin = mock.MagicMock(nss_password=None)
        self.assertRaises(
            ValueError,
            DogtagCryptoPlugin,
            m,
        )

    def test_encrypt(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        payload = 'encrypt me!!'
        encrypt_dto = plugin_import.EncryptDTO(payload)
        self.plugin.encrypt(encrypt_dto,
                            mock.MagicMock(),
                            mock.MagicMock())
        self.keyclient_mock.archive_key.assert_called_once_with(
            mock.ANY,
            "passPhrase",
            payload,
            key_algorithm=None,
            key_size=None)

    def test_decrypt(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        key_id = 'key1'
        decrypt_dto = plugin_import.DecryptDTO(key_id)
        self.plugin.decrypt(decrypt_dto,
                            mock.MagicMock(),
                            mock.MagicMock(),
                            mock.MagicMock())

        self.keyclient_mock.retrieve_key.assert_called_once_with(key_id)

    def test_supports_encrypt_decrypt(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        self.assertTrue(
            self.plugin.supports(
                plugin_import.PluginSupportTypes.ENCRYPT_DECRYPT
            )
        )

    def test_supports_symmetric_key_generation(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        self.assertTrue(
            self.plugin.supports(
                plugin_import.PluginSupportTypes.SYMMETRIC_KEY_GENERATION,
                'aes', 256
            )
        )

    def test_supports_symmetric_hmacsha256_key_generation(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        self.assertFalse(
            self.plugin.supports(
                plugin_import.PluginSupportTypes.SYMMETRIC_KEY_GENERATION,
                'hmacsha256', 128
            )
        )

    def test_supports_asymmetric_key_generation(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        self.assertFalse(
            self.plugin.supports(
                plugin_import.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION
            )
        )

    def test_does_not_support_unknown_type(self):
        if not imports_ok:
            self.skipTest("Dogtag imports not available")
        self.assertFalse(
            self.plugin.supports("SOMETHING_RANDOM")
        )

########NEW FILE########
__FILENAME__ = test_extension_manager
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import mock
import testtools

from barbican.crypto import extension_manager as em
from barbican.crypto import mime_types as mt
from barbican.crypto.plugin import CryptoPluginBase
from barbican.crypto.plugin import PluginSupportTypes
from barbican.crypto.plugin import SimpleCryptoPlugin


class TestSupportsCryptoPlugin(CryptoPluginBase):
    """Crypto plugin for testing supports."""

    def encrypt(self, encrypt_dto, kek_meta_dto, tenant):
        raise NotImplementedError()

    def decrypt(self, decrypt_dto, kek_meta_dto, kek_meta_extended, tenant):
        raise NotImplementedError()

    def bind_kek_metadata(self, kek_meta_dto):
        return None

    def generate_symmetric(self, generate_dto,
                           kek_meta_dto, keystone_id):
        raise NotImplementedError()

    def generate_asymmetric(self, generate_dto,
                            kek_meta_dto, keystone_id):
        raise NotImplementedError("Feature not implemented for PKCS11")

    def supports(self, type_enum, algorithm=None, bit_length=None, mode=None):
        return False


class WhenTestingNormalizeBeforeEncryptionForBinary(testtools.TestCase):

    def setUp(self):
        super(WhenTestingNormalizeBeforeEncryptionForBinary, self).setUp()
        self.unencrypted = 'AAAAAAAA'
        self.content_type = 'application/octet-stream'
        self.content_encoding = 'base64'
        self.enforce_text_only = False

    def test_encrypt_binary_from_base64(self):
        unenc, content = em.normalize_before_encryption(self.unencrypted,
                                                        self.content_type,
                                                        self.content_encoding,
                                                        self.enforce_text_only)
        self.assertEqual(self.content_type, content)
        self.assertEqual(base64.b64decode(self.unencrypted), unenc)

    def test_encrypt_binary_directly(self):
        self.content_encoding = None
        unenc, content = em.normalize_before_encryption(self.unencrypted,
                                                        self.content_type,
                                                        self.content_encoding,
                                                        self.enforce_text_only)
        self.assertEqual(self.content_type, content)
        self.assertEqual(self.unencrypted, unenc)

    def test_encrypt_fail_binary_unknown_encoding(self):
        self.content_encoding = 'gzip'

        ex = self.assertRaises(
            em.CryptoContentEncodingNotSupportedException,
            em.normalize_before_encryption,
            self.unencrypted,
            self.content_type,
            self.content_encoding,
            self.enforce_text_only,
        )
        self.assertEqual(self.content_encoding, ex.content_encoding)

    def test_encrypt_fail_binary_force_text_based_no_encoding(self):
        self.content_encoding = None
        self.enforce_text_only = True
        self.assertRaises(
            em.CryptoContentEncodingMustBeBase64,
            em.normalize_before_encryption,
            self.unencrypted,
            self.content_type,
            self.content_encoding,
            self.enforce_text_only,
        )

    def test_encrypt_fail_unknown_content_type(self):
        self.content_type = 'bogus'
        ex = self.assertRaises(
            em.CryptoContentTypeNotSupportedException,
            em.normalize_before_encryption,
            self.unencrypted,
            self.content_type,
            self.content_encoding,
            self.enforce_text_only,
        )
        self.assertEqual(self.content_type, ex.content_type)


class WhenTestingNormalizeBeforeEncryptionForText(testtools.TestCase):

    def setUp(self):
        super(WhenTestingNormalizeBeforeEncryptionForText, self).setUp()

        self.unencrypted = 'AAAAAAAA'
        self.content_type = 'text/plain'
        self.content_encoding = 'base64'
        self.enforce_text_only = False

    def test_encrypt_text_ignore_encoding(self):
        unenc, content = em.normalize_before_encryption(self.unencrypted,
                                                        self.content_type,
                                                        self.content_encoding,
                                                        self.enforce_text_only)
        self.assertEqual(self.content_type, content)
        self.assertEqual(self.unencrypted, unenc)

    def test_encrypt_text_not_normalized_ignore_encoding(self):
        self.content_type = 'text/plain;charset=utf-8'
        unenc, content = em.normalize_before_encryption(self.unencrypted,
                                                        self.content_type,
                                                        self.content_encoding,
                                                        self.enforce_text_only)
        self.assertEqual(mt.normalize_content_type(self.content_type),
                         content)
        self.assertEqual(self.unencrypted.encode('utf-8'), unenc)

    def test_raises_on_bogus_content_type(self):
        content_type = 'text/plain; charset=ISO-8859-1'

        self.assertRaises(
            em.CryptoContentTypeNotSupportedException,
            em.normalize_before_encryption,
            self.unencrypted,
            content_type,
            self.content_encoding,
            self.enforce_text_only
        )

    def test_raises_on_no_payload(self):
        content_type = 'text/plain; charset=ISO-8859-1'
        self.assertRaises(
            em.CryptoNoPayloadProvidedException,
            em.normalize_before_encryption,
            None,
            content_type,
            self.content_encoding,
            self.enforce_text_only
        )


class WhenTestingAnalyzeBeforeDecryption(testtools.TestCase):

    def setUp(self):
        super(WhenTestingAnalyzeBeforeDecryption, self).setUp()

        self.content_type = 'application/octet-stream'

    def test_decrypt_fail_bogus_content_type(self):
        self.content_type = 'bogus'

        ex = self.assertRaises(
            em.CryptoAcceptNotSupportedException,
            em.analyze_before_decryption,
            self.content_type,
        )
        self.assertEqual(self.content_type, ex.accept)


class WhenTestingDenormalizeAfterDecryption(testtools.TestCase):

    def setUp(self):
        super(WhenTestingDenormalizeAfterDecryption, self).setUp()

        self.unencrypted = 'AAAAAAAA'
        self.content_type = 'application/octet-stream'

    def test_decrypt_fail_binary(self):
        unenc = em.denormalize_after_decryption(self.unencrypted,
                                                self.content_type)
        self.assertEqual(self.unencrypted, unenc)

    def test_decrypt_text(self):
        self.content_type = 'text/plain'
        unenc = em.denormalize_after_decryption(self.unencrypted,
                                                self.content_type)
        self.assertEqual(self.unencrypted.decode('utf-8'), unenc)

    def test_decrypt_fail_unknown_content_type(self):
        self.content_type = 'bogus'
        self.assertRaises(
            em.CryptoGeneralException,
            em.denormalize_after_decryption,
            self.unencrypted,
            self.content_type,
        )

    def test_decrypt_fail_binary_as_plain(self):
        self.unencrypted = '\xff'
        self.content_type = 'text/plain'
        self.assertRaises(
            em.CryptoAcceptNotSupportedException,
            em.denormalize_after_decryption,
            self.unencrypted,
            self.content_type,
        )


class WhenTestingCryptoExtensionManager(testtools.TestCase):

    def setUp(self):
        super(WhenTestingCryptoExtensionManager, self).setUp()
        self.manager = em.CryptoExtensionManager()

    def test_create_supported_algorithm(self):
        skg = PluginSupportTypes.SYMMETRIC_KEY_GENERATION
        self.assertEqual(skg, self.manager._determine_type('AES'))
        self.assertEqual(skg, self.manager._determine_type('aes'))
        self.assertEqual(skg, self.manager._determine_type('DES'))
        self.assertEqual(skg, self.manager._determine_type('des'))

    def test_create_unsupported_algorithm(self):
        self.assertRaises(
            em.CryptoAlgorithmNotSupportedException,
            self.manager._determine_type,
            'faux_alg',
        )

    def test_create_asymmetric_supported_algorithm(self):
        skg = PluginSupportTypes.ASYMMETRIC_KEY_GENERATION
        self.assertEqual(skg, self.manager._determine_type('RSA'))
        self.assertEqual(skg, self.manager._determine_type('rsa'))
        self.assertEqual(skg, self.manager._determine_type('DSA'))
        self.assertEqual(skg, self.manager._determine_type('dsa'))

    def test_encrypt_no_plugin_found(self):
        self.manager.extensions = []
        self.assertRaises(
            em.CryptoPluginNotFound,
            self.manager.encrypt,
            'payload',
            'content_type',
            'content_encoding',
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_encrypt_no_supported_plugin(self):
        plugin = TestSupportsCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]
        self.assertRaises(
            em.CryptoSupportedPluginNotFound,
            self.manager.encrypt,
            'payload',
            'content_type',
            'content_encoding',
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_encrypt_response_dto(self):
        plugin = SimpleCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]

        response_dto = self.manager.encrypt(
            'payload', 'text/plain', None, mock.MagicMock(), mock.MagicMock(),
            mock.MagicMock(), False
        )

        self.assertIsNotNone(response_dto)

    def test_decrypt_no_plugin_found(self):
        """Passing mocks here causes CryptoPluginNotFound because the mock
        won't match any of the available plugins.
        """
        self.assertRaises(
            em.CryptoPluginNotFound,
            self.manager.decrypt,
            'text/plain',
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_decrypt_no_supported_plugin_found(self):
        """Similar to test_decrypt_no_plugin_found, but in this case
        no plugin can be found that supports the specified secret's
        encrypted data.
        """
        fake_secret = mock.MagicMock()
        fake_datum = mock.MagicMock()
        fake_datum.kek_meta_tenant = mock.MagicMock()
        fake_secret.encrypted_data = [fake_datum]
        self.assertRaises(
            em.CryptoPluginNotFound,
            self.manager.decrypt,
            'text/plain',
            fake_secret,
            mock.MagicMock(),
        )

    def test_generate_data_encryption_key_no_plugin_found(self):
        self.manager.extensions = []
        self.assertRaises(
            em.CryptoPluginNotFound,
            self.manager.generate_symmetric_encryption_key,
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_generate_symmetric_encryption_key(self):
        secret = mock.MagicMock(algorithm='aes', bit_length=128)
        content_type = 'application/octet-stream'
        tenant = mock.MagicMock()
        kek_repo = mock.MagicMock(name='kek_repo')

        plugin = SimpleCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]

        datum = self.manager.generate_symmetric_encryption_key(
            secret, content_type, tenant, kek_repo
        )
        self.assertIsNotNone(datum)

    def test_generate_data_encryption_key_no_supported_plugin(self):
        plugin = TestSupportsCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]
        self.assertRaises(
            em.CryptoSupportedPluginNotFound,
            self.manager.generate_symmetric_encryption_key,
            mock.MagicMock(algorithm='AES'),
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_find_or_create_kek_objects_bind_returns_none(self):
        plugin = TestSupportsCryptoPlugin()
        kek_repo = mock.MagicMock(name='kek_repo')
        bind_completed = mock.MagicMock(bind_completed=False)
        kek_repo.find_or_create_kek_datum.return_value = bind_completed
        self.assertRaises(
            em.CryptoKEKBindingException,
            self.manager._find_or_create_kek_objects,
            plugin,
            mock.MagicMock(),
            kek_repo,
        )

    def test_find_or_create_kek_objects_saves_to_repo(self):
        kek_repo = mock.MagicMock(name='kek_repo')
        bind_completed = mock.MagicMock(bind_completed=False)
        kek_repo.find_or_create_kek_datum.return_value = bind_completed
        self.manager._find_or_create_kek_objects(
            mock.MagicMock(),
            mock.MagicMock(),
            kek_repo
        )
        kek_repo.save.assert_called_once()

    def generate_asymmetric_encryption_keys_no_plugin_found(self):
        self.manager.extensions = []
        self.assertRaises(
            em.CryptoPluginNotFound,
            self.manager.generate_asymmetric_encryption_keys,
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def generate_asymmetric_encryption_keys_no_supported_plugin(self):
        plugin = TestSupportsCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]
        self.assertRaises(
            em.CryptoSupportedPluginNotFound,
            self.manager.generate_asymmetric_encryption_keys,
            mock.MagicMock(algorithm='DSA'),
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock()
        )

    def generate_asymmetric_encryption_rsa_keys_ensure_encoding(self):
        plugin = SimpleCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]

        meta = mock.MagicMock(algorithm='rsa',
                              bit_length=1024,
                              passphrase=None)

        private_datum, public_datum, passphrase_datum = \
            self.manager.generate_asymmetric_encryption_keys(meta,
                                                             mock.MagicMock(),
                                                             mock.MagicMock(),
                                                             mock.MagicMock())
        self.assertIsNotNone(private_datum)
        self.assertIsNotNone(public_datum)
        self.assertIsNone(passphrase_datum)

        try:
            base64.b64decode(private_datum.cypher_text)
            base64.b64decode(public_datum.cypher_text)
            if passphrase_datum:
                base64.b64decode(passphrase_datum.cypher_text)
            isB64Encoding = True
        except Exception:
            isB64Encoding = False

        self.assertTrue(isB64Encoding)

    def generate_asymmetric_encryption_dsa_keys_ensure_encoding(self):
        plugin = SimpleCryptoPlugin()
        plugin_mock = mock.MagicMock(obj=plugin)
        self.manager.extensions = [plugin_mock]

        meta = mock.MagicMock(algorithm='rsa',
                              bit_length=1024,
                              passphrase=None)

        private_datum, public_datum, passphrase_datum = \
            self.manager.generate_asymmetric_encryption_keys(meta,
                                                             mock.MagicMock(),
                                                             mock.MagicMock(),
                                                             mock.MagicMock())
        self.assertIsNotNone(private_datum)
        self.assertIsNotNone(public_datum)
        self.assertIsNone(passphrase_datum)

        try:
            base64.b64decode(private_datum.cypher_text)
            base64.b64decode(public_datum.cypher_text)
            if passphrase_datum:
                base64.b64decode(passphrase_datum.cypher_text)
            isB64Encoding = True
        except Exception:
            isB64Encoding = False

        self.assertTrue(isB64Encoding)

########NEW FILE########
__FILENAME__ = test_mime_types
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import testtools

from barbican.crypto import mime_types
from barbican.model import models


class WhenTestingIsBase64ProcessingNeeded(testtools.TestCase):

    def test_is_base64_needed(self):
        r = mime_types.is_base64_processing_needed('application/octet-stream',
                                                   'base64')
        self.assertTrue(r)

    def test_is_base64_plus_needed(self):
        r = mime_types.is_base64_processing_needed('application/octet-stream',
                                                   'base64;q=0.5, '
                                                   'gzip;q=0.6, compress')
        self.assertTrue(r)

    def test_not_base64_needed_binary(self):
        r = mime_types.is_base64_processing_needed('application/octet-stream',
                                                   None)
        self.assertFalse(r)

    def test_not_base64_needed_invalid_content_type(self):
        r = mime_types.is_base64_processing_needed('bababooey',
                                                   'base64')
        self.assertFalse(r)

    def test_not_base64_needed_text(self):
        r = mime_types.is_base64_processing_needed('text/plain',
                                                   'base64')
        self.assertFalse(r)


class WhenTestingIsBase64ProcessingSupported(testtools.TestCase):

    def test_is_base64_supported_application_octet_stream(self):
        r = mime_types.is_base64_encoding_supported('application/octet-stream')
        self.assertTrue(r)

    def test_is_base64_supported_with_unsupported_values(self):
        mimes_where_base64_is_not_supported = ['text/plain',
                                               'bogus']
        for mime in mimes_where_base64_is_not_supported:
            r = mime_types.is_base64_encoding_supported(mime)
            self.assertFalse(r)


class WhenTestingAugmentFieldsWithContentTypes(testtools.TestCase):

    def setUp(self):
        super(WhenTestingAugmentFieldsWithContentTypes, self).setUp()

        self.secret = models.Secret({})
        self.secret.secret_id = "secret#1"
        self.datum = models.EncryptedDatum(self.secret)
        self.secret.encrypted_data = [self.datum]

    def test_static_supported_plain_text(self):
        for pt in mime_types.PLAIN_TEXT:
            self.assertEqual('text/plain', mime_types.INTERNAL_CTYPES[pt])

    def test_static_supported_binary(self):
        for bin in mime_types.BINARY:
            self.assertEqual('application/octet-stream',
                             mime_types.INTERNAL_CTYPES[bin])

    def test_static_content_to_encodings(self):
        self.assertIn('text/plain', mime_types.CTYPES_TO_ENCODINGS)
        self.assertIsNone(mime_types.CTYPES_TO_ENCODINGS['text/plain'])

        self.assertIn('application/aes', mime_types.CTYPES_TO_ENCODINGS)
        self.assertIsNone(mime_types.CTYPES_TO_ENCODINGS['application/aes'])

        self.assertIn('application/octet-stream',
                      mime_types.CTYPES_TO_ENCODINGS)
        self.assertEqual(['base64'], mime_types.CTYPES_TO_ENCODINGS[
            'application/octet-stream'])

    def test_secret_with_matching_datum(self):
        for ct in mime_types.SUPPORTED:
            self._test_secret_and_datum_for_content_type(ct)

    def test_secret_with_non_matching_datum(self):
        self.datum.content_type = "bababooey"
        fields = mime_types.augment_fields_with_content_types(self.secret)
        self.assertNotIn("bababooey", fields)

    def _test_secret_and_datum_for_content_type(self, content_type):
        self.assertIn(content_type, mime_types.INTERNAL_CTYPES)
        self.datum.content_type = mime_types.INTERNAL_CTYPES[content_type]
        fields = mime_types.augment_fields_with_content_types(self.secret)

        self.assertIn('content_types', fields)
        content_types = fields['content_types']
        self.assertIn('default', content_types)
        self.assertEqual(self.datum.content_type, content_types['default'])


class WhenTestingNormalizationOfMIMETypes(testtools.TestCase):

    def test_plain_text_normalization(self):
        mimes = ['text/plain',
                 '   text/plain  ',
                 'text/plain;charset=utf-8',
                 'text/plain;charset=UTF-8',
                 'text/plain; charset=utf-8',
                 'text/plain; charset=UTF-8',
                 'text/plain;  charset=utf-8',
                 'text/plain;  charset=UTF-8',
                 'text/plain ; charset = utf-8',
                 'text/plain ; charset = UTF-8']
        for mime in mimes:
            self._test_plain_text_mime_type(mime)

    def _test_plain_text_mime_type(self, mime):
        r = mime_types.normalize_content_type(mime)
        self.assertEqual(r, 'text/plain')

    def test_unsupported_charset_in_plain_text_mime(self):
        mime = 'text/plain; charset=ISO-8859-1'
        r = mime_types.normalize_content_type(mime)
        self.assertEqual(r, mime)

    def test_malformed_charset_in_plain_text_mime(self):
        mime = 'text/plain; charset is ISO-8859-1'
        r = mime_types.normalize_content_type(mime)
        self.assertEqual(r, mime)

    def test_binary_normalization(self):
        mime = 'application/octet-stream'
        r = mime_types.normalize_content_type(mime)
        self.assertEqual(r, 'application/octet-stream')

    def test_bogus_mime_normalization(self):
        mime = 'something/bogus'
        r = mime_types.normalize_content_type(mime)
        self.assertEqual(r, 'something/bogus')

########NEW FILE########
__FILENAME__ = test_p11_crypto
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

import testtools

from barbican.crypto import p11_crypto
from barbican.crypto import plugin as plugin_import
from barbican.model import models


class WhenTestingP11CryptoPlugin(testtools.TestCase):

    def setUp(self):
        super(WhenTestingP11CryptoPlugin, self).setUp()

        self.p11_mock = mock.MagicMock(CKR_OK=0, CKF_RW_SESSION='RW',
                                       name='PyKCS11 mock')
        self.patcher = mock.patch('barbican.crypto.p11_crypto.PyKCS11',
                                  new=self.p11_mock)
        self.patcher.start()
        self.pkcs11 = self.p11_mock.PyKCS11Lib()
        self.p11_mock.PyKCS11Error.return_value = Exception()
        self.pkcs11.lib.C_Initialize.return_value = self.p11_mock.CKR_OK
        self.cfg_mock = mock.MagicMock(name='config mock')
        self.plugin = p11_crypto.P11CryptoPlugin(self.cfg_mock)
        self.session = self.pkcs11.openSession()

    def tearDown(self):
        super(WhenTestingP11CryptoPlugin, self).tearDown()
        self.patcher.stop()

    def test_generate_calls_generate_random(self):
        self.session.generateRandom.return_value = [1, 2, 3, 4, 5, 6, 7,
                                                    8, 9, 10, 11, 12, 13,
                                                    14, 15, 16]
        secret = models.Secret()
        secret.bit_length = 128
        secret.algorithm = "AES"
        generate_dto = plugin_import.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            None, None)
        self.plugin.generate_symmetric(
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )
        self.session.generateRandom.assert_called_twice_with(16)

    def test_generate_errors_when_rand_length_is_not_as_requested(self):
        self.session.generateRandom.return_value = [1, 2, 3, 4, 5, 6, 7]
        secret = models.Secret()
        secret.bit_length = 192
        secret.algorithm = "AES"
        generate_dto = plugin_import.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            None, None)
        self.assertRaises(
            p11_crypto.P11CryptoPluginException,
            self.plugin.generate_symmetric,
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )

    def test_raises_error_with_no_library_path(self):
        m = mock.MagicMock()
        m.p11_crypto_plugin = mock.MagicMock(library_path=None)
        self.assertRaises(
            ValueError,
            p11_crypto.P11CryptoPlugin,
            m,
        )

    def test_raises_error_with_bad_library_path(self):
        m = mock.MagicMock()
        self.pkcs11.lib.C_Initialize.return_value = 12345
        m.p11_crypto_plugin = mock.MagicMock(library_path="/dev/null")

        # TODO(reaperhulk): Really raises PyKCS11.PyKCS11Error
        pykcs11error = Exception
        self.assertRaises(
            pykcs11error,
            p11_crypto.P11CryptoPlugin,
            m,
        )

    def test_init_builds_sessions_and_login(self):
        self.pkcs11.openSession.assert_any_call(1)
        self.pkcs11.openSession.assert_any_call(1, 'RW')
        self.assertTrue(self.session.login.called)

    def test_get_key_by_label_with_two_keys(self):
        self.session.findObjects.return_value = ['key1', 'key2']
        self.assertRaises(
            p11_crypto.P11CryptoPluginKeyException,
            self.plugin._get_key_by_label,
            'mylabel',
        )

    def test_get_key_by_label_with_one_key(self):
        key = 'key1'
        self.session.findObjects.return_value = [key]
        key_label = self.plugin._get_key_by_label('mylabel')
        self.assertEqual(key, key_label)

    def test_get_key_by_label_with_no_keys(self):
        self.session.findObjects.return_value = []
        result = self.plugin._get_key_by_label('mylabel')
        self.assertIsNone(result)

    def test_generate_iv_calls_generate_random(self):
        self.session.generateRandom.return_value = [1, 2, 3, 4, 5, 6, 7,
                                                    8, 9, 10, 11, 12, 13,
                                                    14, 15, 16]
        iv = self.plugin._generate_iv()
        self.assertEqual(len(iv), self.plugin.block_size)
        self.session.generateRandom.\
            assert_called_once_with(self.plugin.block_size)

    def test_generate_iv_with_invalid_response_size(self):
        self.session.generateRandom.return_value = [1, 2, 3, 4, 5, 6, 7]
        self.assertRaises(
            p11_crypto.P11CryptoPluginException,
            self.plugin._generate_iv,
        )

    def test_build_gcm_params(self):
        class GCM_Mock(object):
            def __init__(self):
                self.pIv = None
                self.ulIvLen = None
                self.ulIvBits = None
                self.ulTagBits = None

        self.p11_mock.LowLevel.CK_AES_GCM_PARAMS.return_value = GCM_Mock()
        iv = b'sixteen_byte_iv_'
        gcm = self.plugin._build_gcm_params(iv)
        self.assertEqual(iv, gcm.pIv)
        self.assertEqual(len(iv), gcm.ulIvLen)
        self.assertEqual(len(iv) * 8, gcm.ulIvBits)
        self.assertEqual(128, gcm.ulIvBits)

    def test_encrypt(self):
        key = 'key1'
        payload = 'encrypt me!!'
        self.session.findObjects.return_value = [key]
        self.session.generateRandom.return_value = [1, 2, 3, 4, 5, 6, 7,
                                                    8, 9, 10, 11, 12, 13,
                                                    14, 15, 16]
        mech = mock.MagicMock()
        self.p11_mock.Mechanism.return_value = mech
        self.session.encrypt.return_value = [1, 2, 3, 4, 5]
        encrypt_dto = plugin_import.EncryptDTO(payload)
        response_dto = self.plugin.encrypt(encrypt_dto,
                                           mock.MagicMock(),
                                           mock.MagicMock())

        self.session.encrypt.assert_called_once_with(key,
                                                     payload,
                                                     mech)
        self.assertEqual(b'\x01\x02\x03\x04\x05', response_dto.cypher_text)
        self.assertEqual('{"iv": "AQIDBAUGBwgJCgsMDQ4PEA=="}',
                         response_dto.kek_meta_extended)

    def test_decrypt(self):
        key = 'key1'
        ct = mock.MagicMock()
        self.session.findObjects.return_value = [key]
        self.session.decrypt.return_value = [100, 101, 102, 103]
        mech = mock.MagicMock()
        self.p11_mock.Mechanism.return_value = mech
        kek_meta_extended = '{"iv": "AQIDBAUGBwgJCgsMDQ4PEA=="}'
        decrypt_dto = plugin_import.DecryptDTO(ct)
        payload = self.plugin.decrypt(decrypt_dto,
                                      mock.MagicMock(),
                                      kek_meta_extended,
                                      mock.MagicMock())
        self.assertTrue(self.p11_mock.Mechanism.called)
        self.session.decrypt.assert_called_once_with(key,
                                                     ct,
                                                     mech)
        self.assertEqual(b'defg', payload)

    def test_bind_kek_metadata_without_existing_key(self):
        self.session.findObjects.return_value = []  # no existing key
        self.pkcs11.lib.C_GenerateKey.return_value = self.p11_mock.CKR_OK

        self.plugin.bind_kek_metadata(mock.MagicMock())

        self.assertTrue(self.session._template2ckattrlist.called)
        self.assertTrue(self.p11_mock.LowLevel.CK_MECHANISM.called)

    def test_bind_kek_metadata_with_existing_key(self):
        self.session.findObjects.return_value = ['key1']  # one key

        self.plugin.bind_kek_metadata(mock.MagicMock())

        gk = self.pkcs11.lib.C_Generate_Key
        # this is a way to test to make sure methods are NOT called
        self.assertEqual([], gk.call_args_list)
        t = self.session._template2ckattrlist
        self.assertEqual([], t.call_args_list)
        m = self.p11_mock.LowLevel.CK_MECHANISM
        self.assertEqual([], m.call_args_list)

    def test_supports_encrypt_decrypt(self):
        self.assertTrue(
            self.plugin.supports(
                plugin_import.PluginSupportTypes.ENCRYPT_DECRYPT
            )
        )

    def test_supports_symmetric_key_generation(self):
        self.assertTrue(
            self.plugin.supports(
                plugin_import.PluginSupportTypes.SYMMETRIC_KEY_GENERATION
            )
        )

    def test_does_not_support_unknown_type(self):
        self.assertFalse(
            self.plugin.supports("SOMETHING_RANDOM")
        )

########NEW FILE########
__FILENAME__ = test_plugin
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from Crypto.PublicKey import DSA
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Util import asn1

import mock

import testtools

from barbican.crypto import plugin
from barbican.model import models


class TestCryptoPlugin(plugin.CryptoPluginBase):
    """Crypto plugin implementation for testing the plugin manager."""

    def encrypt(self, encrypt_dto, kek_meta_dto, keystone_id):
        cypher_text = b'cypher_text'
        return plugin.ResponseDTO(cypher_text, None)

    def decrypt(self, decrypt_dto, kek_meta_dto, kek_meta_extended,
                keystone_id):
        return b'unencrypted_data'

    def bind_kek_metadata(self, kek_meta_dto):
        kek_meta_dto.algorithm = 'aes'
        kek_meta_dto.bit_length = 128
        kek_meta_dto.mode = 'cbc'
        kek_meta_dto.plugin_meta = None
        return kek_meta_dto

    def generate_symmetric(self, generate_dto, kek_meta_dto, keystone_id):
        return plugin.ResponseDTO("encrypted insecure key", None)

    def generate_asymmetric(self, generate_dto, kek_meta_dto, keystone_id):
        return (plugin.ResponseDTO('insecure_private_key', None),
                plugin.ResponseDTO('insecure_public_key', None),
                None)

    def supports(self, type_enum, algorithm=None, bit_length=None, mode=None):
        if type_enum == plugin.PluginSupportTypes.ENCRYPT_DECRYPT:
            return True
        elif type_enum == plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION:
            return True
        else:
            return False


class WhenTestingSimpleCryptoPlugin(testtools.TestCase):

    def setUp(self):
        super(WhenTestingSimpleCryptoPlugin, self).setUp()
        self.plugin = plugin.SimpleCryptoPlugin()

    def test_pad_binary_string(self):
        binary_string = b'some_binary_string'
        padded_string = (
            b'some_binary_string' +
            b'\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e'
        )
        self.assertEqual(self.plugin._pad(binary_string), padded_string)

    def test_pad_random_bytes(self):
        random_bytes = Random.get_random_bytes(10)
        padded_bytes = random_bytes + b'\x06\x06\x06\x06\x06\x06'
        self.assertEqual(self.plugin._pad(random_bytes), padded_bytes)

    def test_strip_padding_from_binary_string(self):
        binary_string = b'some_binary_string'
        padded_string = (
            b'some_binary_string' +
            b'\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e'
        )
        self.assertEqual(self.plugin._strip_pad(padded_string), binary_string)

    def test_strip_padding_from_random_bytes(self):
        random_bytes = Random.get_random_bytes(10)
        padded_bytes = random_bytes + b'\x06\x06\x06\x06\x06\x06'
        self.assertEqual(self.plugin._strip_pad(padded_bytes), random_bytes)

    def test_encrypt_unicode_raises_value_error(self):
        unencrypted = u'unicode_beer\U0001F37A'
        encrypt_dto = plugin.EncryptDTO(unencrypted)
        secret = mock.MagicMock()
        secret.mime_type = 'text/plain'
        self.assertRaises(
            ValueError,
            self.plugin.encrypt,
            encrypt_dto,
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_byte_string_encryption(self):
        unencrypted = b'some_secret'
        encrypt_dto = plugin.EncryptDTO(unencrypted)
        response_dto = self.plugin.encrypt(encrypt_dto,
                                           mock.MagicMock(),
                                           mock.MagicMock())
        decrypt_dto = plugin.DecryptDTO(response_dto.cypher_text)
        decrypted = self.plugin.decrypt(decrypt_dto, mock.MagicMock(),
                                        response_dto.kek_meta_extended,
                                        mock.MagicMock())
        self.assertEqual(unencrypted, decrypted)

    def test_random_bytes_encryption(self):
        unencrypted = Random.get_random_bytes(10)
        encrypt_dto = plugin.EncryptDTO(unencrypted)
        response_dto = self.plugin.encrypt(encrypt_dto,
                                           mock.MagicMock(),
                                           mock.MagicMock())
        decrypt_dto = plugin.DecryptDTO(response_dto.cypher_text)
        decrypted = self.plugin.decrypt(decrypt_dto, mock.MagicMock(),
                                        response_dto.kek_meta_extended,
                                        mock.MagicMock())
        self.assertEqual(unencrypted, decrypted)

    def test_generate_256_bit_key(self):
        secret = models.Secret()
        secret.bit_length = 256
        secret.algorithm = "AES"
        generate_dto = plugin.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            secret.mode, None)
        response_dto = self.plugin.generate_symmetric(
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )
        decrypt_dto = plugin.DecryptDTO(response_dto.cypher_text)
        key = self.plugin.decrypt(decrypt_dto, mock.MagicMock(),
                                  response_dto.kek_meta_extended,
                                  mock.MagicMock())
        self.assertEqual(len(key), 32)

    def test_generate_192_bit_key(self):
        secret = models.Secret()
        secret.bit_length = 192
        secret.algorithm = "AES"
        generate_dto = plugin.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            None, None)
        response_dto = self.plugin.generate_symmetric(
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )
        decrypt_dto = plugin.DecryptDTO(response_dto.cypher_text)
        key = self.plugin.decrypt(decrypt_dto, mock.MagicMock(),
                                  response_dto.kek_meta_extended,
                                  mock.MagicMock())
        self.assertEqual(len(key), 24)

    def test_generate_128_bit_key(self):
        secret = models.Secret()
        secret.bit_length = 128
        secret.algorithm = "AES"
        generate_dto = plugin.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            None, None)
        response_dto = self.plugin.generate_symmetric(
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )
        decrypt_dto = plugin.DecryptDTO(response_dto.cypher_text)
        key = self.plugin.decrypt(decrypt_dto, mock.MagicMock(),
                                  response_dto.kek_meta_extended,
                                  mock.MagicMock())
        self.assertEqual(len(key), 16)

    def test_supports_encrypt_decrypt(self):
        self.assertTrue(
            self.plugin.supports(plugin.PluginSupportTypes.ENCRYPT_DECRYPT)
        )

    def test_supports_symmetric_key_generation(self):
        self.assertTrue(
            self.plugin.supports(
                plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION, 'AES', 64)
        )
        self.assertFalse(
            self.plugin.supports(
                plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION, 'AES')
        )
        self.assertTrue(
            self.plugin.supports(
                plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION,
                'hmacsha512', 128)
        )
        self.assertFalse(
            self.plugin.supports(
                plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION,
                'hmacsha512', 12)
        )
        self.assertFalse(
            self.plugin.supports(
                plugin.PluginSupportTypes.SYMMETRIC_KEY_GENERATION,
                'Camillia', 128)
        )

    def test_does_not_support_unknown_type(self):
        self.assertFalse(
            self.plugin.supports("SOMETHING_RANDOM")
        )

    def test_bind_kek_metadata(self):
        kek_metadata_dto = mock.MagicMock()
        kek_metadata_dto = self.plugin.bind_kek_metadata(kek_metadata_dto)

        self.assertEqual(kek_metadata_dto.algorithm, 'aes')
        self.assertEqual(kek_metadata_dto.bit_length, 128)
        self.assertEqual(kek_metadata_dto.mode, 'cbc')
        self.assertIsNone(kek_metadata_dto.plugin_meta)

    def test_supports_asymmetric_key_generation(self):
        self.assertTrue(
            self.plugin.supports(
                plugin.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION,
                'DSA', 1024)
        )
        self.assertTrue(
            self.plugin.supports(
                plugin.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION,
                "RSA", 1024)
        )
        self.assertFalse(
            self.plugin.supports(
                plugin.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION,
                "DSA", 512)
        )
        self.assertFalse(
            self.plugin.supports(
                plugin.PluginSupportTypes.ASYMMETRIC_KEY_GENERATION,
                "RSA", 64)
        )

    def test_generate_512_bit_RSA_key(self):
        generate_dto = plugin.GenerateDTO('rsa', 512, None, None)
        self.assertRaises(ValueError,
                          self.plugin.generate_asymmetric,
                          generate_dto,
                          mock.MagicMock(),
                          mock.MagicMock())

    def test_generate_2048_bit_DSA_key(self):
        generate_dto = plugin.GenerateDTO('dsa', 2048, None, None)
        self.assertRaises(ValueError, self.plugin.generate_asymmetric,
                          generate_dto,
                          mock.MagicMock(),
                          mock.MagicMock())

    def test_generate_2048_bit_DSA_key_with_passphrase(self):
        generate_dto = plugin.GenerateDTO('dsa', 2048, None, 'Passphrase')
        self.assertRaises(ValueError, self.plugin.generate_asymmetric,
                          generate_dto,
                          mock.MagicMock(),
                          mock.MagicMock())

    def test_generate_asymmetric_1024_bit_key(self):
        generate_dto = plugin.GenerateDTO('rsa', 1024, None, None)

        private_dto, public_dto, passwd_dto = self.plugin.generate_asymmetric(
            generate_dto, mock.MagicMock(), mock.MagicMock())

        decrypt_dto = plugin.DecryptDTO(private_dto.cypher_text)
        private_dto = self.plugin.decrypt(decrypt_dto,
                                          mock.MagicMock(),
                                          private_dto.kek_meta_extended,
                                          mock.MagicMock())

        decrypt_dto = plugin.DecryptDTO(public_dto.cypher_text)
        public_dto = self.plugin.decrypt(decrypt_dto,
                                         mock.MagicMock(),
                                         public_dto.kek_meta_extended,
                                         mock.MagicMock())

        public_dto = RSA.importKey(public_dto)
        private_dto = RSA.importKey(private_dto)
        self.assertEqual(public_dto.size(), 1023)
        self.assertEqual(private_dto.size(), 1023)
        self.assertTrue(private_dto.has_private)

    def test_generate_1024_bit_RSA_key_in_pem(self):
        generate_dto = plugin.GenerateDTO('rsa', 1024, None, 'changeme')

        private_dto, public_dto, passwd_dto = \
            self.plugin.generate_asymmetric(generate_dto,
                                            mock.MagicMock(),
                                            mock.MagicMock())
        decrypt_dto = plugin.DecryptDTO(private_dto.cypher_text)
        private_dto = self.plugin.decrypt(decrypt_dto,
                                          mock.MagicMock(),
                                          private_dto.kek_meta_extended,
                                          mock.MagicMock())

        private_dto = RSA.importKey(private_dto, 'changeme')
        self.assertTrue(private_dto.has_private())

    def test_generate_1024_DSA_key_in_pem_and_reconstruct_key_der(self):
        generate_dto = plugin.GenerateDTO('dsa', 1024, None, None)

        private_dto, public_dto, passwd_dto = \
            self.plugin.generate_asymmetric(generate_dto,
                                            mock.MagicMock(),
                                            mock.MagicMock())

        decrypt_dto = plugin.DecryptDTO(private_dto.cypher_text)
        private_dto = self.plugin.decrypt(decrypt_dto,
                                          mock.MagicMock(),
                                          private_dto.kek_meta_extended,
                                          mock.MagicMock())

        prv_seq = asn1.DerSequence()
        data = "\n".join(private_dto.strip().split("\n")
                         [1:-1]).decode("base64")
        prv_seq.decode(data)
        p, q, g, y, x = prv_seq[1:]

        private_dto = DSA.construct((y, g, p, q, x))
        self.assertTrue(private_dto.has_private())

    def test_generate_128_bit_hmac_key(self):
        secret = models.Secret()
        secret.bit_length = 128
        secret.algorithm = "hmacsha256"
        generate_dto = plugin.GenerateDTO(
            secret.algorithm,
            secret.bit_length,
            None, None)
        response_dto = self.plugin.generate_symmetric(
            generate_dto,
            mock.MagicMock(),
            mock.MagicMock()
        )
        decrypt_dto = plugin.DecryptDTO(response_dto.cypher_text)
        key = self.plugin.decrypt(decrypt_dto, mock.MagicMock(),
                                  response_dto.kek_meta_extended,
                                  mock.MagicMock())
        self.assertEqual(len(key), 16)

########NEW FILE########
__FILENAME__ = test_models
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import testtools

from barbican.model import models


class WhenCreatingNewSecret(testtools.TestCase):
    def setUp(self):
        super(WhenCreatingNewSecret, self).setUp()
        self.parsed_secret = {'name': 'name',
                              'algorithm': 'algorithm',
                              'bit_length': 512,
                              'mode': 'mode',
                              'plain_text': 'not-encrypted'}

        self.parsed_order = {'secret': self.parsed_secret}

    def test_new_secret_is_created_from_dict(self):
        secret = models.Secret(self.parsed_secret)
        self.assertEqual(secret.name, self.parsed_secret['name'])
        self.assertEqual(secret.algorithm, self.parsed_secret['algorithm'])
        self.assertEqual(secret.bit_length, self.parsed_secret['bit_length'])
        self.assertEqual(secret.mode, self.parsed_secret['mode'])


class WhenCreatingNewContainer(testtools.TestCase):
    def setUp(self):
        super(WhenCreatingNewContainer, self).setUp()
        self.parsed_container = {'name': 'name',
                                 'type': 'generic',
                                 'secret_refs': [
                                     {'name': 'test secret 1',
                                      'secret_ref': '123'},
                                     {'name': 'test secret 2',
                                      'secret_ref': '123'},
                                     {'name': 'test secret 3',
                                      'secret_ref': '123'}
                                 ]}

    def test_new_container_is_created_from_dict(self):
        container = models.Container(self.parsed_container)
        self.assertEqual(container.name, self.parsed_container['name'])
        self.assertEqual(container.type, self.parsed_container['type'])
        self.assertEqual(len(container.container_secrets),
                         len(self.parsed_container['secret_refs']))

        self.assertEqual(container.container_secrets[0].name,
                         self.parsed_container['secret_refs'][0]['name'])
        self.assertEqual(container.container_secrets[0].secret_id,
                         self.parsed_container['secret_refs'][0]['secret_ref'])

        self.assertEqual(container.container_secrets[1].name,
                         self.parsed_container['secret_refs'][1]['name'])
        self.assertEqual(container.container_secrets[1].secret_id,
                         self.parsed_container['secret_refs'][1]['secret_ref'])

        self.assertEqual(container.container_secrets[2].name,
                         self.parsed_container['secret_refs'][2]['name'])
        self.assertEqual(container.container_secrets[2].secret_id,
                         self.parsed_container['secret_refs'][2]['secret_ref'])

    def test_parse_secret_ref_uri(self):
        self.parsed_container['secret_refs'][0]['secret_ref'] =\
            'http://localhost:9110/123/secrets/123456'
        container = models.Container(self.parsed_container)
        self.assertEqual(container.container_secrets[0].secret_id, '123456')

        self.parsed_container['secret_refs'][0]['secret_ref'] =\
            'http://localhost:9110/123/secrets/123456/'
        container = models.Container(self.parsed_container)
        self.assertEqual(container.container_secrets[0].secret_id, '123456')

########NEW FILE########
__FILENAME__ = test_repositories
# Copyright 2013-2014 Rackspace, Inc.
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
from oslo.config import cfg
import testtools

from barbican.model import repositories


class WhenCleaningRepositoryPagingParameters(testtools.TestCase):

    def setUp(self):
        super(WhenCleaningRepositoryPagingParameters, self).setUp()
        self.CONF = cfg.CONF

    def test_parameters_not_assigned(self):
        """The cleaner should use defaults when params are not specified."""
        clean_offset, clean_limit = repositories.clean_paging_values()

        self.assertEqual(clean_offset, 0)
        self.assertEqual(clean_limit, self.CONF.default_limit_paging)

    def test_limit_as_none(self):
        """When Limit is set to None it should use the default limit."""
        offset = 0
        clean_offset, clean_limit = repositories.clean_paging_values(
            offset_arg=offset,
            limit_arg=None)

        self.assertEqual(clean_offset, offset)
        self.assertIsNotNone(clean_limit)

    def test_offset_as_none(self):
        """When Offset is set to None it should use an offset of 0."""
        limit = self.CONF.default_limit_paging
        clean_offset, clean_limit = repositories.clean_paging_values(
            offset_arg=None,
            limit_arg=limit)

        self.assertIsNotNone(clean_offset)
        self.assertEqual(clean_limit, limit)

    def test_limit_as_uncastable_str(self):
        """When Limit cannot be cast to an int, expect the default."""
        clean_offset, clean_limit = repositories.clean_paging_values(
            offset_arg=0,
            limit_arg='boom')
        self.assertEqual(clean_offset, 0)
        self.assertEqual(clean_limit, self.CONF.default_limit_paging)

    def test_offset_as_uncastable_str(self):
        """When Offset cannot be cast to an int, it should be zero."""
        limit = self.CONF.default_limit_paging
        clean_offset, clean_limit = repositories.clean_paging_values(
            offset_arg='boom',
            limit_arg=limit)
        self.assertEqual(clean_offset, 0)
        self.assertEqual(clean_limit, limit)

    def test_limit_is_less_than_one(self):
        """Offset should default to 1."""
        limit = -1
        clean_offset, clean_limit = repositories.clean_paging_values(
            offset_arg=1,
            limit_arg=limit)
        self.assertEqual(clean_offset, 1)
        self.assertEqual(clean_limit, 1)

    def test_limit_ist_too_big(self):
        """Limit should max out at configured value."""
        limit = self.CONF.max_limit_paging + 10
        clean_offset, clean_limit = repositories.clean_paging_values(
            offset_arg=1,
            limit_arg=limit)
        self.assertEqual(clean_limit, self.CONF.max_limit_paging)

########NEW FILE########
__FILENAME__ = test_client
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import mock

from barbican import queue
from barbican.queue import client
from barbican.tests import utils


class WhenUsingAsyncTaskClient(utils.BaseTestCase):
    """Test using the asynchronous task client."""

    def setUp(self):
        super(WhenUsingAsyncTaskClient, self).setUp()

        self.mock_client = mock.MagicMock()
        self.mock_client.cast.return_value = None

        queue.get_client = mock.MagicMock(return_value=self.mock_client)

        self.client = client.TaskClient()

    def test_should_process_order(self):
        self.client.process_order(order_id=self.order_id,
                                  keystone_id=self.keystone_id)
        queue.get_client.assert_called_with()
        self.mock_client.cast.assert_called_with({}, 'process_order',
                                                 order_id=self.order_id,
                                                 keystone_id=self.keystone_id)


class WhenCreatingDirectTaskClient(utils.BaseTestCase):
    """Test using the synchronous task client (i.e. standalone mode)."""

    def setUp(self):
        super(WhenCreatingDirectTaskClient, self).setUp()

        queue.get_client = mock.MagicMock(return_value=None)

        self.client = client.TaskClient()

    def test_should_use_direct_task_client(self):
        self.assertIsInstance(self.client._client,
                              client._DirectTaskInvokerClient)

########NEW FILE########
__FILENAME__ = test_server
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import mock

from barbican import queue
from barbican.queue import server
from barbican.tests import utils


class WhenUsingBeginOrderTask(utils.BaseTestCase):
    """Test using the Tasks class for 'order' task."""

    def setUp(self):
        super(WhenUsingBeginOrderTask, self).setUp()

        self.tasks = server.Tasks()

    @mock.patch('barbican.tasks.resources.BeginOrder')
    def test_should_process_order(self, mock_begin_order):
        mock_begin_order.return_value.process.return_value = None
        self.tasks.process_order(context=None,
                                 order_id=self.order_id,
                                 keystone_id=self.keystone_id)
        mock_begin_order.return_value.process\
            .assert_called_with(self.order_id, self.keystone_id)


class WhenUsingTaskServer(utils.BaseTestCase):
    """Test using the asynchronous task client."""

    def setUp(self):
        super(WhenUsingTaskServer, self).setUp()

        self.target = 'a target value here'
        queue.get_target = mock.MagicMock(return_value=self.target)

        self.server_mock = mock.MagicMock()
        self.server_mock.start.return_value = None
        self.server_mock.stop.return_value = None

        queue.get_server = mock.MagicMock(return_value=self.server_mock)

        self.server = server.TaskServer()

    def test_should_start(self):
        self.server.start()
        queue.get_target.assert_called_with()
        queue.get_server.assert_called_with(target=self.target,
                                            endpoints=[self.server])
        self.server_mock.start.assert_called_with()

    def test_should_stop(self):
        self.server.stop()
        queue.get_target.assert_called_with()
        queue.get_server.assert_called_with(target=self.target,
                                            endpoints=[self.server])
        self.server_mock.stop.assert_called_with()

########NEW FILE########
__FILENAME__ = test_resources
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import testtools

from barbican.crypto import extension_manager as em
from barbican.model import models
from barbican.openstack.common import gettextutils as u
from barbican.openstack.common import timeutils
from barbican.tasks import resources


class WhenBeginningOrder(testtools.TestCase):

    def setUp(self):
        super(WhenBeginningOrder, self).setUp()

        self.requestor = 'requestor1234'
        self.order = models.Order()
        self.order.id = "id1"
        self.order.requestor = self.requestor

        self.secret_name = "name"
        self.secret_algorithm = "AES"
        self.secret_bit_length = 256
        self.secret_mode = "CBC"
        self.secret_expiration = timeutils.utcnow()
        self.secret_payload_content_type = 'application/octet-stream'

        self.keystone_id = 'keystone1234'
        self.tenant_id = 'tenantid1234'
        self.tenant = models.Tenant()
        self.tenant.id = self.tenant_id
        self.tenant.keystone_id = self.keystone_id
        self.tenant_repo = mock.MagicMock()
        self.tenant_repo.get.return_value = self.tenant

        self.order.status = models.States.PENDING
        self.order.tenant_id = self.tenant_id
        self.order.secret_name = self.secret_name
        self.order.secret_algorithm = self.secret_algorithm
        self.order.secret_bit_length = self.secret_bit_length
        self.order.secret_mode = self.secret_mode
        self.order.secret_expiration = self.secret_expiration
        self.order.secret_payload_content_type = self\
            .secret_payload_content_type

        self.order_repo = mock.MagicMock()
        self.order_repo.get.return_value = self.order

        self.secret_repo = mock.MagicMock()
        self.secret_repo.create_from.return_value = None

        self.tenant_secret_repo = mock.MagicMock()
        self.tenant_secret_repo.create_from.return_value = None

        self.datum_repo = mock.MagicMock()
        self.datum_repo.create_from.return_value = None

        self.kek_repo = mock.MagicMock()

        self.conf = mock.MagicMock()
        self.conf.crypto.namespace = 'barbican.test.crypto.plugin'
        self.conf.crypto.enabled_crypto_plugins = ['test_crypto']
        self.crypto_mgr = em.CryptoExtensionManager(conf=self.conf)

        self.resource = resources.BeginOrder(self.crypto_mgr,
                                             self.tenant_repo, self.order_repo,
                                             self.secret_repo,
                                             self.tenant_secret_repo,
                                             self.datum_repo, self.kek_repo)

    def test_should_process_order(self):
        self.resource.process(self.order.id, self.keystone_id)

        self.order_repo.get \
            .assert_called_once_with(entity_id=self.order.id,
                                     keystone_id=self.keystone_id)
        self.assertEqual(self.order.status, models.States.ACTIVE)

        args, kwargs = self.secret_repo.create_from.call_args
        secret = args[0]
        self.assertIsInstance(secret, models.Secret)
        self.assertEqual(secret.name, self.secret_name)
        self.assertEqual(secret.expiration, self.secret_expiration)

        args, kwargs = self.tenant_secret_repo.create_from.call_args
        tenant_secret = args[0]
        self.assertIsInstance(tenant_secret, models.TenantSecret)
        self.assertEqual(tenant_secret.tenant_id, self.tenant_id)
        self.assertEqual(tenant_secret.secret_id, secret.id)

        args, kwargs = self.datum_repo.create_from.call_args
        datum = args[0]
        self.assertIsInstance(datum, models.EncryptedDatum)
        self.assertIsNotNone(datum.cypher_text)

        self.assertIsNone(datum.kek_meta_extended)
        self.assertIsNotNone(datum.kek_meta_tenant)
        self.assertTrue(datum.kek_meta_tenant.bind_completed)
        self.assertIsNotNone(datum.kek_meta_tenant.plugin_name)
        self.assertIsNotNone(datum.kek_meta_tenant.kek_label)

    def test_should_fail_during_retrieval(self):
        # Force an error during the order retrieval phase.
        self.order_repo.get = mock.MagicMock(return_value=None,
                                             side_effect=ValueError())

        self.assertRaises(
            ValueError,
            self.resource.process,
            self.order.id,
            self.keystone_id,
        )

        # Order state doesn't change because can't retrieve it to change it.
        self.assertEqual(models.States.PENDING, self.order.status)

    def test_should_fail_during_processing(self):
        # Force an error during the processing handler phase.
        self.tenant_repo.get = mock.MagicMock(return_value=None,
                                              side_effect=ValueError())

        self.assertRaises(
            ValueError,
            self.resource.process,
            self.order.id,
            self.keystone_id,
        )

        self.assertEqual(models.States.ERROR, self.order.status)
        self.assertEqual(500, self.order.error_status_code)
        self.assertEqual(u._('Create Secret failure seen - please contact '
                             'site administrator.'), self.order.error_reason)

    def test_should_fail_during_success_report_fail(self):
        # Force an error during the processing handler phase.
        self.order_repo.save = mock.MagicMock(return_value=None,
                                              side_effect=ValueError())

        self.assertRaises(
            ValueError,
            self.resource.process,
            self.order.id,
            self.keystone_id,
        )

    def test_should_fail_during_error_report_fail(self):
        # Force an error during the error-report handling after
        # error in processing handler phase.

        # Force an error during the processing handler phase.
        self.tenant_repo.get = mock.MagicMock(return_value=None,
                                              side_effect=TypeError())

        # Force exception in the error-reporting phase.
        self.order_repo.save = mock.MagicMock(return_value=None,
                                              side_effect=ValueError())

        # Should see the original exception (TypeError) instead of the
        # secondary one (ValueError).
        self.assertRaises(
            TypeError,
            self.resource.process,
            self.order.id,
            self.keystone_id,
        )

########NEW FILE########
__FILENAME__ = test_middleware_auth
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import httplib


host = "localhost"
port = 9311
method = "GET"
timeout = 1000
body = None
path = "/"
headers = ""

expected_response = {"v1": "current", "build": "0.1.34dev"}


# Typically an authenticated user session will make a request for a key to
# barbican
# The restful request in all likelihood contain an auth token
# this test mimics such a request provided a token

# if pki tokens are used, the token is rather large
# uuid tokens are smaller and easier to test with
# assume there is a "demo" user with only member role

# curl -XPOST -d '{"auth":{"passwordCredentials":{"username": "demo", \
# "password": "secret"}, "tenantName": "demo"}}' \
# -H "Content-type: application/json" http://localhost:35357/v2.0/tokens
#
# pull out the token_id from above and use in ping_barbican
#

#TODO(malini) flesh this out
def get_demo_token(password):
    pass


def ping_barbican(token_id):
    headers = {'X_AUTH_TOKEN': token_id, 'X_IDENTITY_STATUS': 'Confirmed'}
    connection = httplib.HTTPConnection(host, port, timeout=timeout)
    connection.request(method, path, None, headers)
    response = connection.getresponse().read()
    connection.close()
    return response

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import testtools


class BaseTestCase(testtools.TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.order_id = 'order1234'
        self.keystone_id = 'keystone1234'

    def tearDown(self):
        super(BaseTestCase, self).tearDown()

########NEW FILE########
__FILENAME__ = version
# Copyright 2010-2011 OpenStack LLC.
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

import pbr.version

version_info = pbr.version.VersionInfo('barbican')
__version__ = version_info.release_string()

########NEW FILE########
__FILENAME__ = barbican-db-manage
#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import os
import sys
import argparse

sys.path.insert(0, os.getcwd())

from barbican.model.migration import commands
from barbican.openstack.common import log


class DatabaseManager:
    """
    Builds and executes a CLI parser to manage the Barbican database,
    using Alembic commands.
    """

    def __init__(self):
        self.parser = self.get_main_parser()
        self.subparsers = self.parser.add_subparsers(title='subcommands',
                                                     description=
                                                     'Action to perform')
        self.add_revision_args()
        self.add_downgrade_args()
        self.add_upgrade_args()

    def get_main_parser(self):
        """Create top-level parser and arguments."""
        parser = argparse.ArgumentParser(description='Barbican DB manager.')
        parser.add_argument('--dburl', '-d', default=None,
                             help='URL to the database.')

        return parser

    def add_revision_args(self):
        """Create 'revision' command parser and arguments."""
        create_parser = self.subparsers.add_parser('revision', help='Create a '
                                                   'new DB version file.')
        create_parser.add_argument('--message', '-m', default='DB change',
                                   help='the message for the DB change')
        create_parser.add_argument('--autogenerate',
                                   help='autogenerate from models',
                                   action='store_true')
        create_parser.set_defaults(func=self.revision)

    def add_upgrade_args(self):
        """Create 'upgrade' command parser and arguments."""
        create_parser = self.subparsers.add_parser('upgrade',
                                                   help='Upgrade to a '
                                                   'future version DB '
                                                   'version file')
        create_parser.add_argument('--version', '-v', default='head',
                                   help='the version to upgrade to, or else '
                                        'the latest/head if not specified.')
        create_parser.set_defaults(func=self.upgrade)

    def add_downgrade_args(self):
        """Create 'downgrade' command parser and arguments."""
        create_parser = self.subparsers.add_parser('downgrade',
                                                   help='Downgrade to a '
                                                   'previous DB '
                                                   'version file.')
        create_parser.add_argument('--version', '-v', default='need version',
                                   help='the version to downgrade back to.')
        create_parser.set_defaults(func=self.downgrade)

    def revision(self, args):
        """Process the 'revision' Alembic command."""
        commands.generate(autogenerate=args.autogenerate,
                          message=args.message,
                          sql_url=args.dburl)

    def upgrade(self, args):
        """Process the 'upgrade' Alembic command."""
        commands.upgrade(to_version=args.version,
                         sql_url=args.dburl)

    def downgrade(self, args):
        """Process the 'downgrade' Alembic command."""
        commands.downgrade(to_version=args.version,
                           sql_url=args.dburl)

    def execute(self):
        """Parse the command line arguments."""
        args = self.parser.parse_args()

        # Perform other setup here...

        args.func(args)


def main():
    # Import and configure logging.
    log.setup('barbican-db-manage')
    LOG = log.getLogger(__name__)
    LOG.debug("Performing database schema migration...")

    dm = DatabaseManager()
    dm.execute()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = barbican-worker
#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Barbican worker server.
"""

import eventlet
import gettext
import os
import sys

# Oslo messaging RPC server uses eventlet.
eventlet.monkey_patch()

# 'Borrowed' from the Glance project:
# If ../barbican/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'barbican', '__init__.py')):
    sys.path.insert(0, possible_topdir)


gettext.install('barbican', unicode=1)

from barbican.common import config
from barbican.openstack.common import log
from barbican.openstack.common import service
from barbican import queue
from barbican.queue import server
from oslo.config import cfg


def fail(returncode, e):
    sys.stderr.write("ERROR: {0}\n".format(e))
    sys.exit(returncode)


if __name__ == '__main__':
    try:
        config.parse_args()

        # Import and configure logging.
        log.setup('barbican')
        LOG = log.getLogger(__name__)
        LOG.debug("Booting up Barbican worker node...")

        # Queuing initialization
        CONF = cfg.CONF
        queue.init(CONF)

        service.launch(
            server.TaskServer()
        ).wait()
    except RuntimeError as e:
        fail(1, e)


########NEW FILE########
__FILENAME__ = versionbuild
#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Version build stamping script.

This module generates and inserts a patch component of the semantic version
stamp for Barbican, intended to ensure that a strictly monotonically increasing
version is produced for consecutive development releases. Some repositories
such as yum use this increasing semantic version to select the latest
package for installations.

This process may not be required if a bug in the 'pbr' library is fixed:
https://bugs.launchpad.net/pbr/+bug/1206730
"""
import os

from datetime import datetime
from time import mktime


# Determine version of this application.
SETUP_FILE = 'setup.cfg'
VERSIONFILE = os.path.join(SETUP_FILE)
current_dir = os.getcwd()
if current_dir.endswith('bin'):
    VERSIONFILE = os.path.join('..', SETUP_FILE)


def get_patch():
    """Return a strictly monotonically increasing version patch.

    This method is providing the 'patch' component of the semantic version
    stamp for Barbican. It currently returns an epoch in seconds, but
    could use a build id from the build system.
    """
    dt = datetime.now()
    return int(mktime(dt.timetuple()))


def update_versionfile(patch):
    """Update the 'patch' version information per the provided patch."""
    temp_name = VERSIONFILE + '~'
    file_new = open(temp_name, 'w')
    try:
        with open(VERSIONFILE, 'r') as file_old:
            for line in file_old:
                if line.startswith('version ='):
                    subs = line.split('.')
                    if len(subs) <= 2:
                        file_new.write(''.join([line[:-1], '.',
                                                str(patch), '\n']))
                    else:
                        subs[2] = str(patch)
                        file_new.write('.'.join(subs))
                        if len(subs) == 3:
                            file_new.write('\n')
                else:
                    file_new.write(line)
    finally:
        file_new.close()
        os.rename(temp_name, VERSIONFILE)

if __name__ == '__main__':
    patch = get_patch()
    print 'patch: ', patch
    update_versionfile(patch)

########NEW FILE########
__FILENAME__ = config
config = {
    'sqlalchemy': {
        'url': 'sqlite:////tmp/barbican.db',
        'echo': True,
        'echo_pool': False,
        'pool_recycle': 3600,
        'encoding': 'utf-8'
    }
}

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    #'sphinx.ext.intersphinx',
    'oslosphinx'
]

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Barbican'
copyright = u'2014, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme_path = ["."]
# html_theme = '_theme'
# html_static_path = ['static']

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     '%s.tex' % project,
     u'%s Documentation' % project,
     u'OpenStack Foundation', 'manual'),
]

# Example configuration for intersphinx: refer to the Python standard library.
#intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
