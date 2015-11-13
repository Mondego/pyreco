__FILENAME__ = devices
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

import logging

from openstack.common import exception
from openstack.common import wsgi
from balancer import utils
from balancer.core import api as core_api
import balancer.db.api as db_api

LOG = logging.getLogger(__name__)


class Controller(object):
    def __init__(self, conf):
        LOG.debug("Creating device controller with config: %s", conf)
        self.conf = conf

    @utils.require_admin
    def index(self, req):
        try:
            LOG.debug("Got index request. Request: %s", req)
            result = core_api.device_get_index(self.conf)
            LOG.debug("Obtained response: %s" % result)
            return {'devices': result}
        except exception.NotFound:
            msg = "Element not found"
            LOG.debug(msg)
            raise webob.exc.HTTPNotFound(msg)
        except exception.NotAuthorized:
            msg = _("Unauthorized access")
            LOG.debug(msg)
            raise webob.exc.HTTPForbidden(msg)

    @utils.require_admin
    def create(self, req, body):
        LOG.debug("Got create request. Request: %s", req)
        params = body
        LOG.debug("Request params: %s" % params)
        self._validate_params(params)
        device = core_api.device_create(self.conf, **params)
        return {"device": db_api.unpack_extra(device)}

    @utils.require_admin
    def show(self, req, device_id):
        LOG.debug("Got device data request. Request: %s" % req)
        device_ref = db_api.device_get(self.conf, device_id)
        return {'device': db_api.unpack_extra(device_ref)}

    def device_status(self, req, **args):
        # NOTE(yorik-sar): broken, there is no processing anymore
        try:
            shared = SharedObjects.Instance(self.conf)
            id = args['id']
            pool = shared.getDevicePoolbyID(id)
            stats = {}
            thr_stat = {}
            if pool:
                stats['command_queue_lenth'] = pool.getQueueSize()
                stats['threads'] = pool.getThreadCount()
                for i in range(pool.getThreadCount()):
                    thr_stat[i] = pool.get_status(i)
                stats['thread_status'] = thr_stat
                return {'device_command_status': stats}
            else:
                return {'device_command_status': 'not available'}
        except exception.NotFound:
            msg = "Device with id %s not found" % args['id']
            LOG.debug(msg)
            raise webob.exc.HTTPNotFound(msg)
        except exception.NotAuthorized:
            msg = _("Unauthorized access")
            LOG.debug(msg)
            raise webob.exc.HTTPForbidden(msg)
        finally:
            pass

    @utils.require_admin
    def info(self, req, **args):
        try:
            args['query_params'] = req.GET
            if worker.type == SYNCHRONOUS_WORKER:
                result = core_api.device_info(args)
                return {'devices': result}
        except exception.NotFound:
            msg = "Element not found"
            LOG.debug(msg)
            raise webob.exc.HTTPNotFound(msg)
        except exception.NotAuthorized:
            msg = _("Unauthorized access")
            LOG.debug(msg)
            raise webob.exc.HTTPForbidden(msg)
        return {'devices': list}

    @utils.http_success_code(204)
    @utils.require_admin
    def delete(self, req, device_id):
        LOG.debug("Got delete request. Request: %s", req)
        core_api.device_delete(self.conf, device_id)

    def show_algorithms(self, req):
        LOG.debug("Got algorithms request. Request: %s", req)
        algorithms = core_api.device_show_algorithms(self.conf)
        return {'algorithms': algorithms}

    def show_protocols(self, req):
        LOG.debug("Got protocols request. Request: %s", req)
        protocols = core_api.device_show_protocols(self.conf)
        return {'protocols': protocols}

    def _validate_params(self, params):
        pass


def create_resource(conf):
    """Devices  resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(Controller(conf), deserializer, serializer)

########NEW FILE########
__FILENAME__ = filters
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012, Piston Cloud Computing, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def validate(filter, value):
    return FILTER_FUNCTIONS.get(filter, lambda v: True)(value)


def validate_int_in_range(min=0, max=None):
    def _validator(v):
        try:
            if max is None:
                return min <= int(v)
            return min <= int(v) <= max
        except ValueError:
            return False
    return _validator


def validate_boolean(v):
    return v.lower() in ('none', 'true', 'false', '1', '0')


FILTER_FUNCTIONS = {'size_max': validate_int_in_range(),  # build validator
                    'size_min': validate_int_in_range(),  # build validator
                    'min_ram': validate_int_in_range(),  # build validator
                    'protected': validate_boolean,
                    'is_public': validate_boolean, }

########NEW FILE########
__FILENAME__ = loadbalancers
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

import logging

from openstack.common import wsgi

from balancer import utils
from balancer.core import api as core_api
from balancer.db import api as db_api

LOG = logging.getLogger(__name__)


class Controller(object):
    def __init__(self, conf):
        LOG.debug("Creating loadbalancers controller with config:"
                                                "loadbalancers.py %s", conf)
        self.conf = conf

    @utils.verify_tenant
    def findLBforVM(self, req, tenant_id, vm_id):
        LOG.debug("Got index request. Request: %s", req)
        result = core_api.lb_find_for_vm(self.conf, tenant_id, vm_id)
        return {'loadbalancers': result}

    @utils.verify_tenant
    def index(self, req, tenant_id):
        LOG.debug("Got index request. Request: %s", req)
        result = core_api.lb_get_index(self.conf, tenant_id)
        return {'loadbalancers': result}

    @utils.http_success_code(202)
    @utils.verify_tenant
    def create(self, req, tenant_id, body):
        LOG.debug("Got create request. Request: %s", req)
        #here we need to decide which device should be used
        params = body.copy()
        LOG.debug("Headers: %s", req.headers)
        # We need to create LB object and return its id
        params['tenant_id'] = tenant_id
        lb_id = core_api.create_lb(self.conf, params)
        return {'loadbalancer': {'id': lb_id}}

    @utils.http_success_code(204)
    @utils.verify_tenant
    def delete(self, req, tenant_id, lb_id):
        LOG.debug("Got delete request. Request: %s", req)
        core_api.delete_lb(self.conf, tenant_id, lb_id)

    @utils.verify_tenant
    def show(self, req, tenant_id, lb_id):
        LOG.debug("Got loadbalancerr info request. Request: %s", req)
        result = core_api.lb_get_data(self.conf, tenant_id, lb_id)
        return {'loadbalancer': result}

    @utils.verify_tenant
    def details(self, req, tenant_id, lb_id):
        LOG.debug("Got loadbalancerr info request. Request: %s", req)
        result = core_api.lb_show_details(self.conf, tenant_id, lb_id)
        return result

    @utils.http_success_code(202)
    @utils.verify_tenant
    def update(self, req, tenant_id, lb_id, body):
        LOG.debug("Got update request. Request: %s", req)
        core_api.update_lb(self.conf, tenant_id, lb_id, body)
        return {'loadbalancer': {'id': lb_id}}


def create_resource(conf):
    """Loadbalancers resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(Controller(conf), deserializer, serializer)

########NEW FILE########
__FILENAME__ = nodes
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

import logging

from openstack.common import wsgi

from balancer import utils
from balancer.core import api as core_api
from balancer.db import api as db_api

LOG = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, conf):
        LOG.debug("Creating nodes controller with config:"
                                                "nodes.py %s", conf)
        self.conf = conf

    @utils.verify_tenant
    def create(self, req, tenant_id, lb_id, body):
        LOG.debug("Got addNode request. Request: %s", req)
        return {'nodes': core_api.lb_add_nodes(self.conf, tenant_id, lb_id,
            body['nodes'])}

    @utils.verify_tenant
    def index(self, req, tenant_id, lb_id):
        LOG.debug("Got showNodes request. Request: %s", req)
        return {'nodes': core_api.lb_show_nodes(self.conf, tenant_id, lb_id)}

    @utils.verify_tenant
    def show(self, req, tenant_id, lb_id, node_id):
        LOG.debug("Got showNode request. Request: %s", req)
        return {'node': db_api.unpack_extra(
            db_api.server_get(self.conf, node_id, lb_id, tenant_id=tenant_id))}

    @utils.http_success_code(204)
    @utils.verify_tenant
    def delete(self, req, tenant_id, lb_id, node_id):
        LOG.debug("Got deleteNode request. Request: %s", req)
        core_api.lb_delete_node(self.conf, tenant_id, lb_id, node_id)

    @utils.verify_tenant
    def changeNodeStatus(self, req, tenant_id, lb_id, node_id, status, body):
        LOG.debug("Got changeNodeStatus request. Request: %s", req)
        result = core_api.lb_change_node_status(self.conf,
                tenant_id, lb_id, node_id, status)
        return {"node": result}

    @utils.verify_tenant
    def update(self, req, tenant_id, lb_id, node_id, body):
        LOG.debug("Got updateNode request. Request: %s", req)
        result = core_api.lb_update_node(self.conf,
                tenant_id, lb_id, node_id, body)
        return {"node": result}


def create_resource(conf):
    """Nodes resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(Controller(conf), deserializer, serializer)

########NEW FILE########
__FILENAME__ = probes
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

import logging

from openstack.common import wsgi

from balancer import utils
from balancer.core import api as core_api
from balancer.db import api as db_api

LOG = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, conf):
        LOG.debug("Creating probes controller with config:"
                                                "probes.py %s", conf)
        self.conf = conf

    @utils.verify_tenant
    def index(self, req, tenant_id, lb_id):
        LOG.debug("Got showMonitoring request. Request: %s", req)
        result = core_api.lb_show_probes(self.conf, tenant_id, lb_id)
        return result

    @utils.verify_tenant
    def show(self, req, tenant_id, lb_id, probe_id):
        LOG.debug("Got showProbe request. Request: %s", req)
        probe = db_api.probe_get(self.conf, probe_id, tenant_id=tenant_id)
        return {"healthMonitoring": db_api.unpack_extra(probe)}

    @utils.verify_tenant
    def create(self, req, tenant_id, lb_id, body):
        LOG.debug("Got addProbe request. Request: %s", req)
        probe = core_api.lb_add_probe(self.conf, tenant_id, lb_id,
                                      body['healthMonitoring'])
        LOG.debug("Return probe: %r", probe)
        return {'healthMonitoring': probe}

    @utils.http_success_code(204)
    @utils.verify_tenant
    def delete(self, req, tenant_id, lb_id, probe_id):
        LOG.debug("Got deleteProbe request. Request: %s", req)
        core_api.lb_delete_probe(self.conf, tenant_id, lb_id, probe_id)


def create_resource(conf):
    """Health monitoring resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(Controller(conf), deserializer, serializer)

########NEW FILE########
__FILENAME__ = router
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

import logging

import routes

from . import loadbalancers
from . import devices
from . import nodes
from . import vips
from . import probes
from . import stickies
#from . import tasks


from openstack.common import wsgi


logger = logging.getLogger(__name__)


class API(wsgi.Router):

    """WSGI router for balancer v1 API requests."""

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        tenant_mapper = mapper.submapper(path_prefix="/{tenant_id}")

        lb_resource = loadbalancers.create_resource(self.conf)
        lb_collection = tenant_mapper.collection(
                "loadbalancers", "loadbalancer",
                controller=lb_resource, member_prefix="/{lb_id}",
                formatted=False)
        lb_collection.member.link('details')

        lb_collection.connect("/find_for_VM/{vm_id}",
                       action="findLBforVM", conditions={'method': ["GET"]})

        nd_resource = nodes.create_resource(self.conf)
        nd_collection = lb_collection.member.collection('nodes', 'node',
                controller=nd_resource, member_prefix="/{node_id}",
                formatted=False)
        nd_collection.member.connect("/{status}", action="changeNodeStatus",
                   conditions={'method': ["PUT"]})

        pb_resource = probes.create_resource(self.conf)

        lb_collection.member.collection('healthMonitoring', '',
                controller=pb_resource, member_prefix="/{probe_id}",
                formatted=False)

        st_resource = stickies.create_resource(self.conf)

        lb_collection.member.collection('sessionPersistence', '',
                controller=st_resource, member_prefix="/{sticky_id}",
                formatted=False)

        vip_resource = vips.create_resource(self.conf)

        lb_collection.member.collection('virtualIps', 'virtualIp',
                controller=vip_resource, member_prefix="/{vip_id}",
                formatted=False)

        device_resource = devices.create_resource(self.conf)

        device_collection = mapper.collection('devices', 'device',
                controller=device_resource, member_prefix="/{device_id}",
                formatted=False)
        device_collection.member.link('info')

        # NOTE(yorik-sar): broken
        #mapper.connect("/devices/{id}/status", controller=device_resource,
        #               action="device_status")

        mapper.connect("/algorithms",
                       controller=device_resource,
                       action="show_algorithms",
                       conditions={'method': ["GET"]})
        mapper.connect("/protocols",
                       controller=device_resource,
                       action="show_protocols",
                       conditions={'method': ["GET"]})

        super(API, self).__init__(mapper)

########NEW FILE########
__FILENAME__ = stickies
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

import logging

from openstack.common import wsgi

from balancer import utils
from balancer.core import api as core_api
from balancer.db import api as db_api

LOG = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, conf):
        LOG.debug("Creating sessionPersistence controller with config:"
                                                "stickies.py %s", conf)
        self.conf = conf

    @utils.verify_tenant
    def index(self, req, tenant_id, lb_id):
        LOG.debug("Got showStickiness request. Request: %s", req)
        result = core_api.lb_show_sticky(self.conf, tenant_id, lb_id)
        return result

    @utils.verify_tenant
    def show(self, req, tenant_id, lb_id, sticky_id):
        LOG.debug("Got showStickiness request. Request: %s", req)
        sticky = db_api.sticky_get(self.conf, sticky_id, tenant_id=tenant_id)
        return {"sessionPersistence": db_api.unpack_extra(sticky)}

    @utils.verify_tenant
    def create(self, req, tenant_id, lb_id, body):
        LOG.debug("Got addSticky request. Request: %s", req)
        sticky = core_api.lb_add_sticky(self.conf, tenant_id, lb_id, body)
        return {"sessionPersistence": db_api.unpack_extra(sticky)}

    @utils.http_success_code(204)
    @utils.verify_tenant
    def delete(self, req, tenant_id, lb_id, sticky_id):
        LOG.debug("Got deleteSticky request. Request: %s", req)
        core_api.lb_delete_sticky(self.conf, tenant_id, lb_id, sticky_id)


def create_resource(conf):
    """Session persistence resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(Controller(conf), deserializer, serializer)

########NEW FILE########
__FILENAME__ = vips
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

import logging

from openstack.common import wsgi

from balancer import utils
from balancer.core import api as core_api
from balancer.db import api as db_api

LOG = logging.getLogger('balancer.api.v1.vips')


class Controller(object):
    def __init__(self, conf):
        LOG.debug("Creating virtualIps controller with config:"
                                                "vips.py %s", conf)
        self.conf = conf

    @utils.http_success_code(200)
    @utils.verify_tenant
    def index(self, req, tenant_id, lb_id):
        LOG.debug("Got index request. Request: %s", req)
        vips = map(db_api.unpack_extra,
                   db_api.virtualserver_get_all_by_lb_id(self.conf,
                       lb_id, tenant_id=tenant_id))
        return {"virtualIps": vips}

    @utils.verify_tenant
    def create(self, req, tenant_id, lb_id, body):
        LOG.debug("Called create(), req: %r, lb_id: %s, body: %r",
                     req, lb_id, body)
        vip = core_api.lb_add_vip(self.conf,
                tenant_id, lb_id, body['virtualIp'])
        return {'virtualIp': vip}

    @utils.verify_tenant
    def show(self, req, tenant_id, lb_id, vip_id):
        LOG.debug("Called show(), req: %r, lb_id: %s, vip_id: %s",
                     req, lb_id, vip_id)
        vip_ref = db_api.virtualserver_get(self.conf,
                vip_id, tenant_id=tenant_id)
        return {'virtualIp': db_api.unpack_extra(vip_ref)}

    @utils.http_success_code(204)
    @utils.verify_tenant
    def delete(self, req, tenant_id, lb_id, vip_id):
        LOG.debug("Called delete(), req: %r, lb_id: %s, vip_id: %s",
                     req, lb_id, vip_id)
        core_api.lb_delete_vip(self.conf, tenant_id, lb_id, vip_id)


def create_resource(conf):
    """Virtual IPs resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(Controller(conf), deserializer, serializer)

########NEW FILE########
__FILENAME__ = versions
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
Controller that returns information on the Glance API versions
"""

import httplib
import json

import webob.dec


class Controller(object):

    """
    A controller that produces information on the Glance API versions.
    """

    def __init__(self, conf):
        self.conf = conf

    @webob.dec.wsgify
    def __call__(self, req):
        """Respond to a request for all OpenStack API versions."""
        version_objs = [
            {
                "id": "v1.0",
                "status": "CURRENT",
                "links": [
                    {
                        "rel": "self",
                        "href": self.get_href(req)}]},
            {
                "id": "v1.1",
                "status": "SUPPORTED",
                "links": [
                    {
                        "rel": "self",
                        "href": self.get_href(req)}]}]

        body = json.dumps(dict(versions=version_objs))

        response = webob.Response(request=req,
                                  status=httplib.MULTIPLE_CHOICES,
                                  content_type='application/json')
        response.body = body

        return response

    def get_href(self, req):
        return "%s/v1/" % req.host_url

########NEW FILE########
__FILENAME__ = cfg
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

r"""
Configuration options which may be set on the command line or in config files.

The schema for each option is defined using the Opt sub-classes e.g.

    common_opts = [
        cfg.StrOpt('bind_host',
                   default='0.0.0.0',
                   help='IP address to listen on'),
        cfg.IntOpt('bind_port',
                   default=9292,
                   help='Port number to listen on')
    ]

Options can be strings, integers, floats, booleans, lists or 'multi strings':

    enabled_apis_opt = \
        cfg.ListOpt('enabled_apis',
                    default=['ec2', 'osapi'],
                    help='List of APIs to enable by default')

    DEFAULT_EXTENSIONS = [
        'nova.api.openstack.contrib.standard_extensions'
    ]
    osapi_extension_opt = \
        cfg.MultiStrOpt('osapi_extension',
                        default=DEFAULT_EXTENSIONS)

Option schemas are registered with with the config manager at runtime, but
before the option is referenced:

    class ExtensionManager(object):

        enabled_apis_opt = cfg.ListOpt(...)

        def __init__(self, conf):
            self.conf = conf
            self.conf.register_opt(enabled_apis_opt)
            ...

        def _load_extensions(self):
            for ext_factory in self.conf.osapi_extension:
                ....

A common usage pattern is for each option schema to be defined in the module or
class which uses the option:

    opts = ...

    def add_common_opts(conf):
        conf.register_opts(opts)

    def get_bind_host(conf):
        return conf.bind_host

    def get_bind_port(conf):
        return conf.bind_port

An option may optionally be made available via the command line. Such options
must registered with the config manager before the command line is parsed (for
the purposes of --help and CLI arg validation):

    cli_opts = [
        cfg.BoolOpt('verbose',
                    short='v',
                    default=False,
                    help='Print more verbose output'),
        cfg.BoolOpt('debug',
                    short='d',
                    default=False,
                    help='Print debugging output'),
    ]

    def add_common_opts(conf):
        conf.register_cli_opts(cli_opts)

The config manager has a single CLI option defined by default, --config-file:

    class ConfigOpts(object):

        config_file_opt = \
            MultiStrOpt('config-file',
                        ...

        def __init__(self, ...):
            ...
            self.register_cli_opt(self.config_file_opt)

Option values are parsed from any supplied config files using SafeConfigParser.
If none are specified, a default set is used e.g. balancer-api.conf and
balancer-common.conf:

    balancer-api.conf:
      [DEFAULT]
      bind_port = 9292

    balancer-common.conf:
      [DEFAULT]
      bind_host = 0.0.0.0

Option values in config files override those on the command line. Config files
are parsed in order, with values in later files overriding those in earlier
files.

The parsing of CLI args and config files is initiated by invoking the config
manager e.g.

    conf = ConfigOpts()
    conf.register_opt(BoolOpt('verbose', ...))
    conf(sys.argv[1:])
    if conf.verbose:
        ...

Options can be registered as belonging to a group:

    rabbit_group = cfg.OptionGroup(name='rabbit',
                                   title='RabbitMQ options')

    rabbit_host_opt = \
        cfg.StrOpt('host',
                   group='rabbit',
                   default='localhost',
                   help='IP/hostname to listen on'),
    rabbit_port_opt = \
        cfg.IntOpt('port',
                   default=5672,
                   help='Port number to listen on')
    rabbit_ssl_opt = \
        conf.BoolOpt('use_ssl',
                     default=False,
                     help='Whether to support SSL connections')

    def register_rabbit_opts(conf):
        conf.register_group(rabbit_group)
        # options can be registered under a group in any of these ways:
        conf.register_opt(rabbit_host_opt)
        conf.register_opt(rabbit_port_opt, group='rabbit')
        conf.register_opt(rabbit_ssl_opt, group=rabbit_group)

If no group is specified, options belong to the 'DEFAULT' section of config
files:

    balancer-api.conf:
      [DEFAULT]
      bind_port = 9292
      ...

      [rabbit]
      host = localhost
      port = 5672
      use_ssl = False
      userid = guest
      password = guest
      virtual_host = /

Command-line options in a group are automatically prefixed with the group name:

    --rabbit-host localhost --rabbit-use-ssl False

Option values in the default group are referenced as attributes/properties on
the config manager; groups are also attributes on the config manager, with
attributes for each of the options associated with the group:

    server.start(app, conf.bind_port, conf.bind_host, conf)

    self.connection = kombu.connection.BrokerConnection(
        hostname=conf.rabbit.host,
        port=conf.rabbit.port,
        ...)

Option values may reference other values using PEP 292 string substitution:

    opts = [
        cfg.StrOpt('state_path',
                   default=os.path.join(os.path.dirname(__file__), '../'),
                   help='Top-level directory for maintaining nova state'),
        cfg.StrOpt('sqlite_db',
                   default='nova.sqlite',
                   help='file name for sqlite'),
        cfg.StrOpt('sql_connection',
                   default='sqlite:///$state_path/$sqlite_db',
                   help='connection string for sql database'),
    ]

Note that interpolation can be avoided by using '$$'.
"""

import sys
import ConfigParser
import copy
import optparse
import os
import string


class Error(Exception):
    """Base class for cfg exceptions."""

    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        return self.msg


class ArgsAlreadyParsedError(Error):
    """Raised if a CLI opt is registered after parsing."""

    def __str__(self):
        ret = "arguments already parsed"
        if self.msg:
            ret += ": " + self.msg
        return ret


class NoSuchOptError(Error):
    """Raised if an opt which doesn't exist is referenced."""

    def __init__(self, opt_name, group=None):
        self.opt_name = opt_name
        self.group = group

    def __str__(self):
        if self.group is None:
            return "no such option: %s" % self.opt_name
        else:
            return "no such option in group %s: %s" % (self.group.name,
                                                       self.opt_name)


class NoSuchGroupError(Error):
    """Raised if a group which doesn't exist is referenced."""

    def __init__(self, group_name):
        self.group_name = group_name

    def __str__(self):
        return "no such group: %s" % self.group_name


class DuplicateOptError(Error):
    """Raised if multiple opts with the same name are registered."""

    def __init__(self, opt_name):
        self.opt_name = opt_name

    def __str__(self):
        return "duplicate option: %s" % self.opt_name


class TemplateSubstitutionError(Error):
    """Raised if an error occurs substituting a variable in an opt value."""

    def __str__(self):
        return "template substitution error: %s" % self.msg


class ConfigFilesNotFoundError(Error):
    """Raised if one or more config files are not found."""

    def __init__(self, config_files):
        self.config_files = config_files

    def __str__(self):
        return 'Failed to read some config files: %s' % \
            string.join(self.config_files, ',')


class ConfigFileParseError(Error):
    """Raised if there is an error parsing a config file."""

    def __init__(self, config_file, msg):
        self.config_file = config_file
        self.msg = msg

    def __str__(self):
        return 'Failed to parse %s: %s' % (self.config_file, self.msg)


class ConfigFileValueError(Error):
    """Raised if a config file value does not match its opt type."""
    pass


def find_config_files(project=None, prog=None, filetype="conf"):
    """Return a list of default configuration files.

    We default to two config files: [${project}.conf, ${prog}.conf]

    And we look for those config files in the following directories:

      ~/.${project}/
      ~/
      /etc/${project}/
      /etc/

    We return an absolute path for (at most) one of each the default config
    files, for the topmost directory it exists in.

    For example, if project=foo, prog=bar and /etc/foo/foo.conf, /etc/bar.conf
    and ~/.foo/bar.conf all exist, then we return ['/etc/foo/foo.conf',
    '~/.foo/bar.conf']

    If no project name is supplied, we only look for ${prog.conf}.

    :param project: an optional project name
    :param prog: the program name, defaulting to the basename of sys.argv[0]
    """
    if prog is None:
        prog = os.path.basename(sys.argv[0])

    fix_path = lambda p: os.path.abspath(os.path.expanduser(p))

    cfg_dirs = [
        fix_path(os.path.join('~', '.' + project)) if project else None,
        fix_path('~'),
        os.path.join('/etc', project) if project else None,
        '/etc',
        'etc',
        ]
    cfg_dirs = filter(bool, cfg_dirs)

    def search_dirs(dirs, basename):
        for d in dirs:
            path = os.path.join(d, basename)
            if os.path.exists(path):
                return path

    config_files = []

    if project:
        project_config = search_dirs(cfg_dirs, '%s.%s' % (project, filetype))
        config_files.append(project_config)

    config_files.append(search_dirs(cfg_dirs, '%s.%s' % (prog, filetype)))

    return filter(bool, config_files)


def _is_opt_registered(opts, opt):
    """Check whether an opt with the same name is already registered.

    The same opt may be registered multiple times, with only the first
    registration having any effect. However, it is an error to attempt
    to register a different opt with the same name.

    :param opts: the set of opts already registered
    :param opt: the opt to be registered
    :returns: True if the opt was previously registered, False otherwise
    :raises: DuplicateOptError if a naming conflict is detected
    """
    if opt.dest in opts:
        if opts[opt.dest]['opt'] is not opt:
            raise DuplicateOptError(opt.name)
        return True
    else:
        return False


class Opt(object):

    """Base class for all configuration options.

    An Opt object has no public methods, but has a number of public string
    properties:

      name:
        the name of the option, which may include hyphens
      dest:
        the (hyphen-less) ConfigOpts property which contains the option value
      short:
        a single character CLI option name
      default:
        the default value of the option
      metavar:
        the name shown as the argument to a CLI option in --help output
      help:
        an string explaining how the options value is used
    """

    def __init__(self, name, dest=None, short=None,
                 default=None, metavar=None, help=None):
        """Construct an Opt object.

        The only required parameter is the option's name. However, it is
        common to also supply a default and help string for all options.

        :param name: the option's name
        :param dest: the name of the corresponding ConfigOpts property
        :param short: a single character CLI option name
        :param default: the default value of the option
        :param metavar: the option argument to show in --help
        :param help: an explanation of how the option is used
        """
        self.name = name
        if dest is None:
            self.dest = self.name.replace('-', '_')
        else:
            self.dest = dest
        self.short = short
        self.default = default
        self.metavar = metavar
        self.help = help

    def _get_from_config_parser(self, cparser, section):
        """Retrieves the option value from a ConfigParser object.

        This is the method ConfigOpts uses to look up the option value from
        config files. Most opt types override this method in order to perform
        type appropriate conversion of the returned value.

        :param cparser: a ConfigParser object
        :param section: a section name
        """
        return cparser.get(section, self.dest)

    def _add_to_cli(self, parser, group=None):
        """Makes the option available in the command line interface.

        This is the method ConfigOpts uses to add the opt to the CLI interface
        as appropriate for the opt type. Some opt types may extend this method,
        others may just extend the helper methods it uses.

        :param parser: the CLI option parser
        :param group: an optional OptGroup object
        """
        container = self._get_optparse_container(parser, group)
        kwargs = self._get_optparse_kwargs(group)
        prefix = self._get_optparse_prefix('', group)
        self._add_to_optparse(container, self.name, self.short, kwargs, prefix)

    def _add_to_optparse(self, container, name, short, kwargs, prefix=''):
        """Add an option to an optparse parser or group.

        :param container: an optparse.OptionContainer object
        :param name: the opt name
        :param short: the short opt name
        :param kwargs: the keyword arguments for add_option()
        :param prefix: an optional prefix to prepend to the opt name
        :raises: DuplicateOptError if a naming confict is detected
        """
        args = ['--' + prefix + name]
        if short:
            args += ['-' + short]
        for a in args:
            if container.has_option(a):
                raise DuplicateOptError(a)
        container.add_option(*args, **kwargs)

    def _get_optparse_container(self, parser, group):
        """Returns an optparse.OptionContainer.

        :param parser: an optparse.OptionParser
        :param group: an (optional) OptGroup object
        :returns: an optparse.OptionGroup if a group is given, else the parser
        """
        if group is not None:
            return group._get_optparse_group(parser)
        else:
            return parser

    def _get_optparse_kwargs(self, group, **kwargs):
        """Build a dict of keyword arguments for optparse's add_option().

        Most opt types extend this method to customize the behaviour of the
        options added to optparse.

        :param group: an optional group
        :param kwargs: optional keyword arguments to add to
        :returns: a dict of keyword arguments
        """
        dest = self.dest
        if group is not None:
            dest = group.name + '_' + dest
        kwargs.update({
                'dest': dest,
                'metavar': self.metavar,
                'help': self.help,
                })
        return kwargs

    def _get_optparse_prefix(self, prefix, group):
        """Build a prefix for the CLI option name, if required.

        CLI options in a group are prefixed with the group's name in order
        to avoid conflicts between similarly named options in different
        groups.

        :param prefix: an existing prefix to append to (e.g. 'no' or '')
        :param group: an optional OptGroup object
        :returns: a CLI option prefix including the group name, if appropriate
        """
        if group is not None:
            return group.name + '-' + prefix
        else:
            return prefix


class StrOpt(Opt):
    """
    String opts do not have their values transformed and are returned as
    str objects.
    """
    pass


class BoolOpt(Opt):

    """
    Bool opts are set to True or False on the command line using --optname or
    --noopttname respectively.

    In config files, boolean values are case insensitive and can be set using
    1/0, yes/no, true/false or on/off.
    """

    def _get_from_config_parser(self, cparser, section):
        """Retrieve the opt value as a boolean from ConfigParser."""
        return cparser.getboolean(section, self.dest)

    def _add_to_cli(self, parser, group=None):
        """Extends the base class method to add the --nooptname option."""
        super(BoolOpt, self)._add_to_cli(parser, group)
        self._add_inverse_to_optparse(parser, group)

    def _add_inverse_to_optparse(self, parser, group):
        """Add the --nooptname option to the option parser."""
        container = self._get_optparse_container(parser, group)
        kwargs = self._get_optparse_kwargs(group, action='store_false')
        prefix = self._get_optparse_prefix('no', group)
        kwargs["help"] = "The inverse of --" + self.name
        self._add_to_optparse(container, self.name, None, kwargs, prefix)

    def _get_optparse_kwargs(self, group, action='store_true', **kwargs):
        """Extends the base optparse keyword dict for boolean options."""
        return super(BoolOpt,
                     self)._get_optparse_kwargs(group, action=action, **kwargs)


class IntOpt(Opt):

    """Int opt values are converted to integers using the int() builtin."""

    def _get_from_config_parser(self, cparser, section):
        """Retrieve the opt value as a integer from ConfigParser."""
        return cparser.getint(section, self.dest)

    def _get_optparse_kwargs(self, group, **kwargs):
        """Extends the base optparse keyword dict for integer options."""
        return super(IntOpt,
                     self)._get_optparse_kwargs(group, type='int', **kwargs)


class FloatOpt(Opt):

    """Float opt values are converted to floats using the float() builtin."""

    def _get_from_config_parser(self, cparser, section):
        """Retrieve the opt value as a float from ConfigParser."""
        return cparser.getfloat(section, self.dest)

    def _get_optparse_kwargs(self, group, **kwargs):
        """Extends the base optparse keyword dict for float options."""
        return super(FloatOpt,
                     self)._get_optparse_kwargs(group, type='float', **kwargs)


class ListOpt(Opt):

    """
    List opt values are simple string values separated by commas. The opt value
    is a list containing these strings.
    """

    def _get_from_config_parser(self, cparser, section):
        """Retrieve the opt value as a list from ConfigParser."""
        return cparser.get(section, self.dest).split(',')

    def _get_optparse_kwargs(self, group, **kwargs):
        """Extends the base optparse keyword dict for list options."""
        return super(ListOpt,
                     self)._get_optparse_kwargs(group,
                                                type='string',
                                                action='callback',
                                                callback=self._parse_list,
                                                **kwargs)

    def _parse_list(self, option, opt, value, parser):
        """An optparse callback for parsing an option value into a list."""
        setattr(parser.values, self.dest, value.split(','))


class MultiStrOpt(Opt):

    """
    Multistr opt values are string opts which may be specified multiple times.
    The opt value is a list containing all the string values specified.
    """

    def _get_from_config_parser(self, cparser, section):
        """Retrieve the opt value as a multistr from ConfigParser."""
        # FIXME(markmc): values spread across the CLI and multiple
        #                config files should be appended
        value = \
            super(MultiStrOpt, self)._get_from_config_parser(cparser, section)
        return value if value is None else [value]

    def _get_optparse_kwargs(self, group, **kwargs):
        """Extends the base optparse keyword dict for multi str options."""
        return super(MultiStrOpt,
                     self)._get_optparse_kwargs(group, action='append')


class OptGroup(object):

    """
    Represents a group of opts.

    CLI opts in the group are automatically prefixed with the group name.

    Each group corresponds to a section in config files.

    An OptGroup object has no public methods, but has a number of public string
    properties:

      name:
        the name of the group
      title:
        the group title as displayed in --help
      help:
        the group description as displayed in --help
    """

    def __init__(self, name, title=None, help=None):
        """Constructs an OptGroup object.

        :param name: the group name
        :param title: the group title for --help
        :param help: the group description for --help
        """
        self.name = name
        if title is None:
            self.title = "%s options" % title
        else:
            self.title = title
        self.help = help

        self._opts = {}  # dict of dicts of {opt:, override:, default:)
        self._optparse_group = None

    def _register_opt(self, opt):
        """Add an opt to this group.

        :param opt: an Opt object
        :returns: False if previously registered, True otherwise
        :raises: DuplicateOptError if a naming conflict is detected
        """
        if _is_opt_registered(self._opts, opt):
            return False

        self._opts[opt.dest] = {'opt': opt, 'override': None, 'default': None}

        return True

    def _get_optparse_group(self, parser):
        """Build an optparse.OptionGroup for this group."""
        if self._optparse_group is None:
            self._optparse_group = \
                optparse.OptionGroup(parser, self.title, self.help)
        return self._optparse_group


class ConfigOpts(object):

    """
    Config options which may be set on the command line or in config files.

    ConfigOpts is a configuration option manager with APIs for registering
    option schemas, grouping options, parsing option values and retrieving
    the values of options.
    """

    def __init__(self,
                 project=None,
                 prog=None,
                 version=None,
                 usage=None,
                 default_config_files=None):
        """Construct a ConfigOpts object.

        Automatically registers the --config-file option with either a supplied
        list of default config files, or a list from find_config_files().

        :param project: the toplevel project name, used to locate config files
        :param prog: the name of the program (defaults to sys.argv[0] basename)
        :param version: the program version (for --version)
        :param usage: a usage string (%prog will be expanded)
        :param default_config_files: config files to use by default
        """
        if prog is None:
            prog = os.path.basename(sys.argv[0])

        if default_config_files is None:
            default_config_files = find_config_files(project, prog)

        self.project = project
        self.prog = prog
        self.version = version
        self.usage = usage
        self.default_config_files = default_config_files

        self._opts = {}  # dict of dicts of (opt:, override:, default:)
        self._groups = {}

        self._args = None
        self._cli_values = {}

        self._oparser = optparse.OptionParser(prog=self.prog,
                                              version=self.version,
                                              usage=self.usage)
        self._cparser = None

        self.register_cli_opt(\
            MultiStrOpt('config-file',
                        default=self.default_config_files,
                        metavar='PATH',
                        help='Path to a config file to use. Multiple config '
                             'files can be specified, with values in later '
                             'files taking precedence. The default files used '
                             'are: %s' % (self.default_config_files, )))

    def __call__(self, args=None):
        """Parse command line arguments and config files.

        Calling a ConfigOpts object causes the supplied command line arguments
        and config files to be parsed, causing opt values to be made available
        as attributes of the object.

        The object may be called multiple times, each time causing the previous
        set of values to be overwritten.

        :params args: command line arguments (defaults to sys.argv[1:])
        :returns: the list of arguments left over after parsing options
        :raises: SystemExit, ConfigFilesNotFoundError, ConfigFileParseError
        """
        self.reset()

        self._args = args

        (values, args) = self._oparser.parse_args(self._args)

        self._cli_values = vars(values)

        if self.config_file:
            self._parse_config_files(self.config_file)

        return args

    def __getattr__(self, name):
        """Look up an option value and perform string substitution.

        :param name: the opt name (or 'dest', more precisely)
        :returns: the option value (after string subsititution) or a GroupAttr
        :raises: NoSuchOptError,ConfigFileValueError,TemplateSubstitutionError
        """
        return self._substitute(self._get(name))

    def reset(self):
        """Reset the state of the object to before it was called."""
        self._args = None
        self._cli_values = None
        self._cparser = None

    def register_opt(self, opt, group=None):
        """Register an option schema.

        Registering an option schema makes any option value which is previously
        or subsequently parsed from the command line or config files available
        as an attribute of this object.

        :param opt: an instance of an Opt sub-class
        :param group: an optional OptGroup object or group name
        :return: False if the opt was already register, True otherwise
        :raises: DuplicateOptError
        """
        if group is not None:
            return self._get_group(group)._register_opt(opt)

        if _is_opt_registered(self._opts, opt):
            return False

        self._opts[opt.dest] = {'opt': opt, 'override': None, 'default': None}

        return True

    def register_opts(self, opts, group=None):
        """Register multiple option schemas at once."""
        for opt in opts:
            self.register_opt(opt, group)

    def register_cli_opt(self, opt, group=None):
        """Register a CLI option schema.

        CLI option schemas must be registered before the command line and
        config files are parsed. This is to ensure that all CLI options are
        show in --help and option validation works as expected.

        :param opt: an instance of an Opt sub-class
        :param group: an optional OptGroup object or group name
        :return: False if the opt was already register, True otherwise
        :raises: DuplicateOptError, ArgsAlreadyParsedError
        """
        if self._args != None:
            raise ArgsAlreadyParsedError("cannot register CLI option")

        if not self.register_opt(opt, group):
            return False

        if group is not None:
            group = self._get_group(group)

        opt._add_to_cli(self._oparser, group)

        return True

    def register_cli_opts(self, opts, group=None):
        """Register multiple CLI option schemas at once."""
        for opt in opts:
            self.register_cli_opt(opt, group)

    def register_group(self, group):
        """Register an option group.

        An option group must be registered before options can be registered
        with the group.

        :param group: an OptGroup object
        """
        if group.name in self._groups:
            return

        self._groups[group.name] = copy.copy(group)

    def set_override(self, name, override, group=None):
        """Override an opt value.

        Override the command line, config file and default values of a
        given option.

        :param name: the name/dest of the opt
        :param override: the override value
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        opt_info = self._get_opt_info(name, group)
        opt_info['override'] = override

    def set_default(self, name, default, group=None):
        """Override an opt's default value.

        Override the default value of given option. A command line or
        config file value will still take precedence over this default.

        :param name: the name/dest of the opt
        :param default: the default value
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        opt_info = self._get_opt_info(name, group)
        opt_info['default'] = default

    def log_opt_values(self, logger, lvl):
        """Log the value of all registered opts.

        It's often useful for an app to log its configuration to a log file at
        startup for debugging. This method dumps to the entire config state to
        the supplied logger at a given log level.

        :param logger: a logging.Logger object
        :param lvl: the log level (e.g. logging.DEBUG) arg to logger.log()
        """
        logger.log(lvl, "*" * 80)
        logger.log(lvl, "Configuration options gathered from:")
        logger.log(lvl, "command line args: %s", self._args)
        logger.log(lvl, "config files: %s", self.config_file)
        logger.log(lvl, "=" * 80)

        for opt_name in sorted(self._opts):
            logger.log(lvl, "%-30s = %s", opt_name, getattr(self, opt_name))

        for group_name in self._groups:
            group_attr = self.GroupAttr(self, group_name)
            for opt_name in sorted(self._groups[group_name]._opts):
                logger.log(lvl, "%-30s = %s",
                           "%s.%s" % (group_name, opt_name),
                           getattr(group_attr, opt_name))

        logger.log(lvl, "*" * 80)

    def print_usage(self, file=None):
        """Print the usage message for the current program."""
        self._oparser.print_usage(file)

    def _get(self, name, group=None):
        """Look up an option value.

        :param name: the opt name (or 'dest', more precisely)
        :param group: an option OptGroup
        :returns: the option value, or a GroupAttr object
        :raises: NoSuchOptError, NoSuchGroupError, ConfigFileValueError,
                 TemplateSubstitutionError
        """
        if group is None and name in self._groups:
            return self.GroupAttr(self, name)

        if group is not None:
            group = self._get_group(group)

        info = self._get_opt_info(name, group)
        default, opt, override = map(lambda k: info[k], sorted(info.keys()))

        if override is not None:
            return override

        if self._cparser is not None:
            section = group.name if group is not None else 'DEFAULT'
            try:
                return opt._get_from_config_parser(self._cparser, section)
            except (ConfigParser.NoOptionError,
                    ConfigParser.NoSectionError):
                pass
            except ValueError, ve:
                raise ConfigFileValueError(str(ve))

        name = name if group is None else group.name + '_' + name
        value = self._cli_values.get(name, None)
        if value is not None:
            return value

        if default is not None:
            return default

        return opt.default

    def _substitute(self, value):
        """Perform string template substitution.

        Substititue any template variables (e.g. $foo, ${bar}) in the supplied
        string value(s) with opt values.

        :param value: the string value, or list of string values
        :returns: the substituted string(s)
        """
        if isinstance(value, list):
            return [self._substitute(i) for i in value]
        elif isinstance(value, str):
            tmpl = string.Template(value)
            return tmpl.safe_substitute(self.StrSubWrapper(self))
        else:
            return value

    def _get_group(self, group_or_name):
        """Looks up a OptGroup object.

        Helper function to return an OptGroup given a parameter which can
        either be the group's name or an OptGroup object.

        The OptGroup object returned is from the internal dict of OptGroup
        objects, which will be a copy of any OptGroup object that users of
        the API have access to.

        :param group_or_name: the group's name or the OptGroup object itself
        :raises: NoSuchGroupError
        """
        if isinstance(group_or_name, OptGroup):
            group_name = group_or_name.name
        else:
            group_name = group_or_name

        if not group_name in self._groups:
            raise NoSuchGroupError(group_name)

        return self._groups[group_name]

    def _get_opt_info(self, opt_name, group=None):
        """Return the (opt, override, default) dict for an opt.

        :param opt_name: an opt name/dest
        :param group: an optional group name or OptGroup object
        :raises: NoSuchOptError, NoSuchGroupError
        """
        if group is None:
            opts = self._opts
        else:
            group = self._get_group(group)
            opts = group._opts

        if not opt_name in opts:
            raise NoSuchOptError(opt_name, group)

        return opts[opt_name]

    def _parse_config_files(self, config_files):
        """Parse the supplied configuration files.

        :raises: ConfigFilesNotFoundError, ConfigFileParseError
        """
        self._cparser = ConfigParser.SafeConfigParser()

        try:
            read_ok = self._cparser.read(config_files)
        except ConfigParser.ParsingError, cpe:
            raise ConfigFileParseError(cpe.filename, cpe.message)

        if read_ok != config_files:
            not_read_ok = filter(lambda f: f not in read_ok, config_files)
            raise ConfigFilesNotFoundError(not_read_ok)

    class GroupAttr(object):

        """
        A helper class representing the option values of a group as attributes.
        """

        def __init__(self, conf, group):
            """Construct a GroupAttr object.

            :param conf: a ConfigOpts object
            :param group: a group name or OptGroup object
            """
            self.conf = conf
            self.group = group

        def __getattr__(self, name):
            """Look up an option value and perform template substitution."""
            return self.conf._substitute(self.conf._get(name, self.group))

    class StrSubWrapper(object):

        """
        A helper class exposing opt values as a dict for string substitution.
        """

        def __init__(self, conf):
            """Construct a StrSubWrapper object.

            :param conf: a ConfigOpts object
            """
            self.conf = conf

        def __getitem__(self, key):
            """Look up an opt value from the ConfigOpts object.

            :param key: an opt name
            :returns: an opt value
            :raises: TemplateSubstitutionError if attribute is a group
            """
            value = getattr(self.conf, key)
            if isinstance(value, self.conf.GroupAttr):
                raise TemplateSubstitutionError(
                    'substituting group %s not supported' % key)
            return value


class CommonConfigOpts(ConfigOpts):

    DEFAULT_LOG_FORMAT = ('%(asctime)s %(process)d %(levelname)8s '
                          '[%(name)s] %(message)s')
    DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    common_cli_opts = [
        BoolOpt('debug',
                short='d',
                default=False,
                help='Print debugging output'),
        BoolOpt('verbose',
                short='v',
                default=False,
                help='Print more verbose output'),
        ]

    logging_cli_opts = [
        StrOpt('log-config',
               metavar='PATH',
               help='If this option is specified, the logging configuration '
                    'file specified is used and overrides any other logging '
                    'options specified. Please see the Python logging module '
                    'documentation for details on logging configuration '
                    'files.'),
        StrOpt('log-format',
               default=DEFAULT_LOG_FORMAT,
               metavar='FORMAT',
               help='A logging.Formatter log message format string which may '
                    'use any of the available logging.LogRecord attributes. '
                    'Default: %default'),
        StrOpt('log-date-format',
               default=DEFAULT_LOG_DATE_FORMAT,
               metavar='DATE_FORMAT',
               help='Format string for %(asctime)s in log records. '
                    'Default: %default'),
        StrOpt('log-file',
               metavar='PATH',
               help='(Optional) Name of log file to output to. '
                    'If not set, logging will go to stdout.'),
        StrOpt('log-dir',
               help='(Optional) The directory to keep log files in '
                    '(will be prepended to --logfile)'),
        BoolOpt('use-syslog',
                default=False,
                help='Use syslog for logging.'),
        StrOpt('syslog-log-facility',
               default='LOG_USER',
               help='syslog facility to receive log lines')
        ]

    def __init__(self, **kwargs):
        super(CommonConfigOpts, self).__init__(**kwargs)
        self.register_cli_opts(self.common_cli_opts)
        self.register_cli_opts(self.logging_cli_opts)

########NEW FILE########
__FILENAME__ = client
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2011 OpenStack, LLC
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

# HTTPSClientAuthConnection code comes courtesy of ActiveState website:
# http://code.activestate.com/recipes/
#   577548-https-httplib-client-connection-with-certificate-v/

import collections
import errno
import functools
import httplib
import os
import select
import urllib
import urlparse

try:
    from eventlet.green import socket, ssl
except ImportError:
    import socket
    import ssl

try:
    import sendfile
    SENDFILE_SUPPORTED = True
except ImportError:
    SENDFILE_SUPPORTED = False

#from glance.common import auth
#from glance.common import exception, utils


# common chunk size for get and put
CHUNKSIZE = 65536


def handle_unauthorized(func):
    """
    Wrap a function to re-authenticate and retry.
    """
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except exception.NotAuthorized:
            self._authenticate(force_reauth=True)
            return func(self, *args, **kwargs)
    return wrapped


def handle_redirects(func):
    """
    Wrap the _do_request function to handle HTTP redirects.
    """
    MAX_REDIRECTS = 5

    @functools.wraps(func)
    def wrapped(self, method, url, body, headers):
        for _ in xrange(MAX_REDIRECTS):
            try:
                return func(self, method, url, body, headers)
            except exception.RedirectException as redirect:
                if redirect.url is None:
                    raise exception.InvalidRedirect()
                url = redirect.url
        raise exception.MaxRedirectsExceeded(redirects=MAX_REDIRECTS)
    return wrapped


class ImageBodyIterator(object):

    """
    A class that acts as an iterator over an image file's
    chunks of data.  This is returned as part of the result
    tuple from `glance.client.Client.get_image`
    """

    def __init__(self, source):
        """
        Constructs the object from a readable image source
        (such as an HTTPResponse or file-like object)
        """
        self.source = source

    def __iter__(self):
        """
        Exposes an iterator over the chunks of data in the
        image file.
        """
        while True:
            chunk = self.source.read(CHUNKSIZE)
            if chunk:
                yield chunk
            else:
                break


class SendFileIterator:
    """
    Emulate iterator pattern over sendfile, in order to allow
    send progress be followed by wrapping the iteration.
    """
    def __init__(self, connection, body):
        self.connection = connection
        self.body = body
        self.offset = 0
        self.sending = True

    def __iter__(self):
        class OfLength:
            def __init__(self, len):
                self.len = len

            def __len__(self):
                return self.len

        while self.sending:
            try:
                sent = sendfile.sendfile(self.connection.sock.fileno(),
                                         self.body.fileno(),
                                         self.offset,
                                         CHUNKSIZE)
            except OSError as e:
                # suprisingly, sendfile may fail transiently instead of
                # blocking, in which case we select on the socket in order
                # to wait on its return to a writeable state before resuming
                # the send loop
                if e.errno in (errno.EAGAIN, errno.EBUSY):
                    wlist = [self.connection.sock.fileno()]
                    rfds, wfds, efds = select.select([], wlist, [])
                    if wfds:
                        continue
                raise

            self.sending = (sent != 0)
            self.offset += sent
            yield OfLength(sent)


class HTTPSClientAuthConnection(httplib.HTTPSConnection):
    """
    Class to make a HTTPS connection, with support for
    full client-based SSL Authentication

    :see http://code.activestate.com/recipes/
            577548-https-httplib-client-connection-with-certificate-v/
    """

    def __init__(self, host, port, key_file, cert_file,
                 ca_file, timeout=None, insecure=False):
        httplib.HTTPSConnection.__init__(self, host, port, key_file=key_file,
                                         cert_file=cert_file)
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_file = ca_file
        self.timeout = timeout
        self.insecure = insecure

    def connect(self):
        """
        Connect to a host on a given (SSL) port.
        If ca_file is pointing somewhere, use it to check Server Certificate.

        Redefined/copied and extended from httplib.py:1105 (Python 2.6.x).
        This is needed to pass cert_reqs=ssl.CERT_REQUIRED as parameter to
        ssl.wrap_socket(), which forces SSL to check server certificate against
        our client certificate.
        """
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # Check CA file unless 'insecure' is specificed
        if self.insecure is True:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        cert_reqs=ssl.CERT_NONE)
        else:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        ca_certs=self.ca_file,
                                        cert_reqs=ssl.CERT_REQUIRED)


class BaseClient(object):

    """A base client class"""

    DEFAULT_PORT = 80
    DEFAULT_DOC_ROOT = None
    # Standard CA file locations for Debian/Ubuntu, RedHat/Fedora,
    # Suse, FreeBSD/OpenBSD
    DEFAULT_CA_FILE_PATH = '/etc/ssl/certs/ca-certificates.crt:'\
        '/etc/pki/tls/certs/ca-bundle.crt:'\
        '/etc/ssl/ca-bundle.pem:'\
        '/etc/ssl/cert.pem'

    OK_RESPONSE_CODES = (
        httplib.OK,
        httplib.CREATED,
        httplib.ACCEPTED,
        httplib.NO_CONTENT,
    )

    REDIRECT_RESPONSE_CODES = (
        httplib.MOVED_PERMANENTLY,
        httplib.FOUND,
        httplib.SEE_OTHER,
        httplib.USE_PROXY,
        httplib.TEMPORARY_REDIRECT,
    )

    def __init__(self, host, port=None, use_ssl=False, auth_tok=None,
                 creds=None, doc_root=None, key_file=None,
                 cert_file=None, ca_file=None, insecure=False,
                 configure_via_auth=True):
        """
        Creates a new client to some service.

        :param host: The host where service resides
        :param port: The port where service resides
        :param use_ssl: Should we use HTTPS?
        :param auth_tok: The auth token to pass to the server
        :param creds: The credentials to pass to the auth plugin
        :param doc_root: Prefix for all URLs we request from host
        :param key_file: Optional PEM-formatted file that contains the private
                         key.
                         If use_ssl is True, and this param is None (the
                         default), then an environ variable
                         GLANCE_CLIENT_KEY_FILE is looked for. If no such
                         environ variable is found, ClientConnectionError
                         will be raised.
        :param cert_file: Optional PEM-formatted certificate chain file.
                          If use_ssl is True, and this param is None (the
                          default), then an environ variable
                          GLANCE_CLIENT_CERT_FILE is looked for. If no such
                          environ variable is found, ClientConnectionError
                          will be raised.
        :param ca_file: Optional CA cert file to use in SSL connections
                        If use_ssl is True, and this param is None (the
                        default), then an environ variable
                        GLANCE_CLIENT_CA_FILE is looked for.
        :param insecure: Optional. If set then the server's certificate
                         will not be verified.
        """
        self.host = host
        self.port = port or self.DEFAULT_PORT
        self.use_ssl = use_ssl
        self.auth_tok = auth_tok
        self.creds = creds or {}
        self.connection = None
        self.configure_via_auth = configure_via_auth
        # doc_root can be a nullstring, which is valid, and why we
        # cannot simply do doc_root or self.DEFAULT_DOC_ROOT below.
        self.doc_root = (doc_root if doc_root is not None
                         else self.DEFAULT_DOC_ROOT)
        self.auth_plugin = self.make_auth_plugin(self.creds)

        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_file = ca_file
        self.insecure = insecure
        self.connect_kwargs = self.get_connect_kwargs()

    def get_connect_kwargs(self):
        connect_kwargs = {}
        if self.use_ssl:
            if self.key_file is None:
                self.key_file = os.environ.get('BALANCER_CLIENT_KEY_FILE')
            if self.cert_file is None:
                self.cert_file = os.environ.get('BALANCER_CLIENT_CERT_FILE')
            if self.ca_file is None:
                self.ca_file = os.environ.get('BALANCER_CLIENT_CA_FILE')

            # Check that key_file/cert_file are either both set or both unset
            if self.cert_file is not None and self.key_file is None:
                msg = _("You have selected to use SSL in connecting, "
                        "and you have supplied a cert, "
                        "however you have failed to supply either a "
                        "key_file parameter or set the "
                        "BALANCER_CLIENT_KEY_FILE environ variable")
                raise exception.ClientConnectionError(msg)

            if self.key_file is not None and self.cert_file is None:
                msg = _("You have selected to use SSL in connecting, "
                        "and you have supplied a key, "
                        "however you have failed to supply either a "
                        "cert_file parameter or set the "
                        "BALANCER_CLIENT_CERT_FILE environ variable")
                raise exception.ClientConnectionError(msg)

            if (self.key_file is not None and
                not os.path.exists(self.key_file)):
                msg = _("The key file you specified %s does not "
                        "exist") % self.key_file
                raise exception.ClientConnectionError(msg)
            connect_kwargs['key_file'] = self.key_file

            if (self.cert_file is not None and
                not os.path.exists(self.cert_file)):
                msg = _("The cert file you specified %s does not "
                        "exist") % self.cert_file
                raise exception.ClientConnectionError(msg)
            connect_kwargs['cert_file'] = self.cert_file

            if (self.ca_file is not None and
                not os.path.exists(self.ca_file)):
                msg = _("The CA file you specified %s does not "
                        "exist") % self.ca_file
                raise exception.ClientConnectionError(msg)

            if self.ca_file is None:
                for ca in self.DEFAULT_CA_FILE_PATH.split(":"):
                    if os.path.exists(ca):
                        self.ca_file = ca
                        break

            connect_kwargs['ca_file'] = self.ca_file
            connect_kwargs['insecure'] = self.insecure

        return connect_kwargs

    def set_auth_token(self, auth_tok):
        """
        Updates the authentication token for this client connection.
        """
        # FIXME(sirp): Nova image/glance.py currently calls this. Since this
        # method isn't really doing anything useful[1], we should go ahead and
        # rip it out, first in Nova, then here. Steps:
        #
        #       1. Change auth_tok in Glance to auth_token
        #       2. Change image/glance.py in Nova to use client.auth_token
        #       3. Remove this method
        #
        # [1] http://mail.python.org/pipermail/tutor/2003-October/025932.html
        self.auth_tok = auth_tok

    def configure_from_url(self, url):
        """
        Setups the connection based on the given url.

        The form is:

            <http|https>://<host>:port/doc_root
        """
        parsed = urlparse.urlparse(url)
        self.use_ssl = parsed.scheme == 'https'
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.doc_root = parsed.path

        # ensure connection kwargs are re-evaluated after the service catalog
        # publicURL is parsed for potential SSL usage
        self.connect_kwargs = self.get_connect_kwargs()

    def make_auth_plugin(self, creds):
        """
        Returns an instantiated authentication plugin.
        """
        strategy = creds.get('strategy', 'noauth')
        plugin = auth.get_plugin_from_strategy(strategy, creds)
        return plugin

    def get_connection_type(self):
        """
        Returns the proper connection type
        """
        if self.use_ssl:
            return HTTPSClientAuthConnection
        else:
            return httplib.HTTPConnection

    def _authenticate(self, force_reauth=False):
        """
        Use the authentication plugin to authenticate and set the auth token.

        :param force_reauth: For re-authentication to bypass cache.
        """
        auth_plugin = self.auth_plugin

        if not auth_plugin.is_authenticated or force_reauth:
            auth_plugin.authenticate()

        self.auth_tok = auth_plugin.auth_token

        management_url = auth_plugin.management_url
        if management_url and self.configure_via_auth:
            self.configure_from_url(management_url)

    @handle_unauthorized
    def do_request(self, method, action, body=None, headers=None,
                   params=None):
        """
        Make a request, returning an HTTP response object.

        :param method: HTTP verb (GET, POST, PUT, etc.)
        :param action: Requested path to append to self.doc_root
        :param body: Data to send in the body of the request
        :param headers: Headers to send with the request
        :param params: Key/value pairs to use in query string
        :returns: HTTP response object
        """
        if not self.auth_tok:
            self._authenticate()

        url = self._construct_url(action, params)
        return self._do_request(method=method, url=url, body=body,
                                headers=headers)

    def _construct_url(self, action, params=None):
        """
        Create a URL object we can use to pass to _do_request().
        """
        path = '/'.join([self.doc_root or '', action.lstrip('/')])
        scheme = "https" if self.use_ssl else "http"
        netloc = "%s:%d" % (self.host, self.port)

        if isinstance(params, dict):
            for (key, value) in params.items():
                if value is None:
                    del params[key]
            query = urllib.urlencode(params)
        else:
            query = None

        return urlparse.ParseResult(scheme, netloc, path, '', query, '')

    @handle_redirects
    def _do_request(self, method, url, body, headers):
        """
        Connects to the server and issues a request.  Handles converting
        any returned HTTP error status codes to OpenStack/Glance exceptions
        and closing the server connection. Returns the result data, or
        raises an appropriate exception.

        :param method: HTTP method ("GET", "POST", "PUT", etc...)
        :param url: urlparse.ParsedResult object with URL information
        :param body: data to send (as string, filelike or iterable),
                     or None (default)
        :param headers: mapping of key/value pairs to add as headers

        :note

        If the body param has a read attribute, and method is either
        POST or PUT, this method will automatically conduct a chunked-transfer
        encoding and use the body as a file object or iterable, transferring
        chunks of data using the connection's send() method. This allows large
        objects to be transferred efficiently without buffering the entire
        body in memory.
        """
        if url.query:
            path = url.path + "?" + url.query
        else:
            path = url.path

        try:
            connection_type = self.get_connection_type()
            headers = headers or {}

            if 'x-auth-token' not in headers and self.auth_tok:
                headers['x-auth-token'] = self.auth_tok

            c = connection_type(url.hostname, url.port, **self.connect_kwargs)

            def _pushing(method):
                return method.lower() in ('post', 'put')

            def _simple(body):
                return body is None or isinstance(body, basestring)

            def _filelike(body):
                return hasattr(body, 'read')

            def _sendbody(connection, iter):
                connection.endheaders()
                for sent in iter:
                    # iterator has done the heavy lifting
                    pass

            def _chunkbody(connection, iter):
                connection.putheader('Transfer-Encoding', 'chunked')
                connection.endheaders()
                for chunk in iter:
                    connection.send('%x\r\n%s\r\n' % (len(chunk), chunk))
                connection.send('0\r\n\r\n')

            # Do a simple request or a chunked request, depending
            # on whether the body param is file-like or iterable and
            # the method is PUT or POST
            #
            if not _pushing(method) or _simple(body):
                # Simple request...
                c.request(method, path, body, headers)
            elif _filelike(body) or self._iterable(body):
                c.putrequest(method, path)

                for header, value in headers.items():
                    c.putheader(header, value)

                iter = self.image_iterator(c, headers, body)

                if self._sendable(body):
                    # send actual file without copying into userspace
                    _sendbody(c, iter)
                else:
                    # otherwise iterate and chunk
                    _chunkbody(c, iter)
            else:
                raise TypeError('Unsupported image type: %s' % body.__class__)

            res = c.getresponse()
            status_code = self.get_status_code(res)
            if status_code in self.OK_RESPONSE_CODES:
                return res
            elif status_code in self.REDIRECT_RESPONSE_CODES:
                raise exception.RedirectException(res.getheader('Location'))
            elif status_code == httplib.UNAUTHORIZED:
                raise exception.NotAuthorized(res.read())
            elif status_code == httplib.FORBIDDEN:
                raise exception.NotAuthorized(res.read())
            elif status_code == httplib.NOT_FOUND:
                raise exception.NotFound(res.read())
            elif status_code == httplib.CONFLICT:
                raise exception.Duplicate(res.read())
            elif status_code == httplib.BAD_REQUEST:
                raise exception.Invalid(res.read())
            elif status_code == httplib.MULTIPLE_CHOICES:
                raise exception.MultipleChoices(body=res.read())
            elif status_code == httplib.INTERNAL_SERVER_ERROR:
                raise Exception("Internal Server error: %s" % res.read())
            else:
                raise Exception("Unknown error occurred! %s" % res.read())

        except (socket.error, IOError), e:
            raise exception.ClientConnectionError(e)

    def _seekable(self, body):
        # pipes are not seekable, avoids sendfile() failure on e.g.
        #   cat /path/to/image | glance add ...
        # or where add command is launched via popen
        try:
            os.lseek(body.fileno(), 0, os.SEEK_SET)
            return True
        except OSError as e:
            return (e.errno != errno.ESPIPE)

    def _sendable(self, body):
        return (SENDFILE_SUPPORTED and hasattr(body, 'fileno') and
                self._seekable(body) and not self.use_ssl)

    def _iterable(self, body):
        return isinstance(body, collections.Iterable)

    def image_iterator(self, connection, headers, body):
        if self._sendable(body):
            return SendFileIterator(connection, body)
        elif self._iterable(body):
            return utils.chunkreadable(body)
        else:
            return ImageBodyIterator(body)

    def get_status_code(self, response):
        """
        Returns the integer status code from the response, which
        can be either a Webob.Response (used in testing) or httplib.Response
        """
        if hasattr(response, 'status_int'):
            return response.status_int
        else:
            return response.status

    def _extract_params(self, actual_params, allowed_params):
        """
        Extract a subset of keys from a dictionary. The filters key
        will also be extracted, and each of its values will be returned
        as an individual param.

        :param actual_params: dict of keys to filter
        :param allowed_params: list of keys that 'actual_params' will be
                               reduced to
        :retval subset of 'params' dict
        """
        try:
            # expect 'filters' param to be a dict here
            result = dict(actual_params.get('filters'))
        except TypeError:
            result = {}

        for allowed_param in allowed_params:
            if allowed_param in actual_params:
                result[allowed_param] = actual_params[allowed_param]

        return result

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
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
Routines for configuring balancer
"""

import logging
import logging.config
import logging.handlers
import os
import sys

from balancer.common import cfg
from balancer.common import wsgi
from balancer import version


paste_deploy_group = cfg.OptGroup('paste_deploy')
paste_deploy_opts = [
    cfg.StrOpt('flavor'),
    cfg.StrOpt('config_file')
    ]


class BalancerConfigOpts(cfg.CommonConfigOpts):
    def __init__(self, default_config_files=None, **kwargs):
        super(BalancerConfigOpts, self).__init__(
            project='balancer',
            version='%%prog %s' % version.version_string(),
            default_config_files=default_config_files,
            **kwargs)


class BalancerCacheConfigOpts(BalancerConfigOpts):

    def __init__(self, **kwargs):
        config_files = cfg.find_config_files(project='balancer',
                                             prog='balancer-cache')
        super(BalancerCacheConfigOpts, self).__init__(config_files, **kwargs)


def setup_logging(conf):
    """
    Sets up the logging options for a log with supplied name

    :param conf: a cfg.ConfOpts object
    """

    if conf.log_config:
        # Use a logging configuration file for all settings...
        if os.path.exists(conf.log_config):
            logging.config.fileConfig(conf.log_config)
            return
        else:
            raise RuntimeError("Unable to locate specified logging "
                               "config file: %s" % conf.log_config)

    root_logger = logging.root
    if conf.debug:
        root_logger.setLevel(logging.DEBUG)
    elif conf.verbose:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.WARNING)

    formatter = logging.Formatter(conf.log_format, conf.log_date_format)

    if conf.use_syslog:
        try:
            facility = getattr(logging.handlers.SysLogHandler,
                               conf.syslog_log_facility)
        except AttributeError:
            raise ValueError(_("Invalid syslog facility"))

        handler = logging.handlers.SysLogHandler(address='/dev/log',
                                                 facility=facility)
    elif conf.log_file:
        logfile = conf.log_file
        if conf.log_dir:
            logfile = os.path.join(conf.log_dir, logfile)
        handler = logging.handlers.WatchedFileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def _register_paste_deploy_opts(conf):
    """
    Idempotent registration of paste_deploy option group

    :param conf: a cfg.ConfigOpts object
    """
    conf.register_group(paste_deploy_group)
    conf.register_opts(paste_deploy_opts, group=paste_deploy_group)


def _get_deployment_flavor(conf):
    """
    Retrieve the paste_deploy.flavor config item, formatted appropriately
    for appending to the application name.

    :param conf: a cfg.ConfigOpts object
    """
    _register_paste_deploy_opts(conf)
    flavor = conf.paste_deploy.flavor
    return '' if not flavor else ('-' + flavor)


def _get_deployment_config_file(conf):
    """
    Retrieve the deployment_config_file config item, formatted as an
    absolute pathname.

   :param conf: a cfg.ConfigOpts object
    """
    _register_paste_deploy_opts(conf)
    config_file = conf.paste_deploy.config_file
    if not config_file:
        # Assume paste config is in a paste.ini file corresponding
        # to the last config file
        path = conf.config_file[-1].replace(".conf", "-paste.ini")
    else:
        path = config_file
    return os.path.abspath(path)


def load_paste_app(conf, app_name=None):
    """
    Builds and returns a WSGI app from a paste config file.

    We assume the last config file specified in the supplied ConfigOpts
    object is the paste config file.

    :param conf: a cfg.ConfigOpts object
    :param app_name: name of the application to load

    :raises RuntimeError when config file cannot be located or application
            cannot be loaded from config file
    """
    if app_name is None:
        app_name = conf.prog

    # append the deployment flavor to the application name,
    # in order to identify the appropriate paste pipeline
    app_name += _get_deployment_flavor(conf)

    conf_file = _get_deployment_config_file(conf)

    try:
        # Setup logging early
        setup_logging(conf)

        app = wsgi.paste_deploy_app(conf_file, app_name, conf)

        # Log the options used when starting if we're in debug mode...
        if conf.debug:
            conf.log_opt_values(logging.getLogger(app_name), logging.DEBUG)

        return app
    except (LookupError, ImportError), e:
        raise RuntimeError("Unable to load %(app_name)s from "
                           "configuration file %(conf_file)s."
                           "\nGot: %(e)r" % locals())

########NEW FILE########
__FILENAME__ = context
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

from balancer.common import cfg
from balancer.common import exception
from balancer.common import utils
from balancer.common import wsgi


class RequestContext(object):
    """
    Stores information about the security context under which the user
    accesses the system, as well as additional request information.
    """

    def __init__(self, auth_tok=None, user=None, user_id=None, tenant=None,
            tenant_id=None, roles=None, is_admin=False, read_only=False,
            show_deleted=False, owner_is_tenant=True):
        self.auth_tok = auth_tok
        self.user = user
        self.user_id = user_id
        self.tenant = tenant
        self.tenant_id = tenant_id
        self.roles = roles or []
        self.is_admin = is_admin
        self.read_only = read_only
        self._show_deleted = show_deleted
        self.owner_is_tenant = owner_is_tenant

    @property
    def owner(self):
        """Return the owner to correlate with an image."""
        return self.tenant if self.owner_is_tenant else self.user

    @property
    def show_deleted(self):
        """Admins can see deleted by default"""
        if self._show_deleted or self.is_admin:
            return True
        return False


class ContextMiddleware(wsgi.Middleware):

    opts = [
        cfg.BoolOpt('owner_is_tenant', default=True),
        ]

    def __init__(self, app, conf, **local_conf):
        self.conf = conf
        self.conf.register_opts(self.opts)

        # Determine the context class to use
        self.ctxcls = RequestContext
        if 'context_class' in local_conf:
            self.ctxcls = utils.import_class(local_conf['context_class'])

        super(ContextMiddleware, self).__init__(app)

    def make_context(self, *args, **kwargs):
        """
        Create a context with the given arguments.
        """
        kwargs.setdefault('owner_is_tenant', self.conf.owner_is_tenant)

        return self.ctxcls(*args, **kwargs)

    def process_request(self, req):
        """
        Extract any authentication information in the request and
        construct an appropriate context from it.

        A few scenarios exist:

        1. If X-Auth-Token is passed in, then consult TENANT and ROLE headers
           to determine permissions.

        2. An X-Auth-Token was passed in, but the Identity-Status is not
           confirmed. For now, just raising a NotAuthorized exception.

        3. X-Auth-Token is omitted. If we were using Keystone, then the
           tokenauth middleware would have rejected the request, so we must be
           using NoAuth. In that case, assume that is_admin=True.
        """
        # TODO(sirp): should we be using the balancer_tokeauth shim from
        # Keystone here? If we do, we need to make sure it handles the NoAuth
        # case
        auth_tok = req.headers.get('X-Auth-Token',
                                   req.headers.get('X-Storage-Token'))
        if auth_tok:
            if req.headers.get('X-Identity-Status') == 'Confirmed':
                # 1. Auth-token is passed, check other headers
                user = req.headers.get('X-User-Name')
                user_id = req.headers.get('X-User-Id')
                tenant = req.headers.get('X-Tenant-Name')
                tenant_id = req.headers.get('X-Tenant-Id')
                roles = [r.strip()
                         for r in req.headers.get('X-Role', '').split(',')]
                is_admin = any(role.lower() == 'admin' for role in roles)
            else:
                # 2. Indentity-Status not confirmed
                # FIXME(sirp): not sure what the correct behavior in this case
                # is; just raising NotAuthorized for now
                raise exception.NotAuthorized()
        else:
            # 3. Auth-token is ommited, assume NoAuth
            user = None
            user_id = None
            tenant = None
            tenant_id = None
            roles = []
            is_admin = True

        req.context = self.make_context(auth_tok=auth_tok, user=user,
                user_id=user_id, tenant=tenant, tenant_id=tenant_id,
                roles=roles, is_admin=is_admin)

########NEW FILE########
__FILENAME__ = exception
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Glance exception subclasses"""

import urlparse


class RedirectException(Exception):
    def __init__(self, url):
        self.url = urlparse.urlparse(url)


class GlanceException(Exception):
    """
    Base Glance Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = "An unknown exception occurred"

    def __init__(self, *args, **kwargs):
        try:
            self._error_string = self.message % kwargs
        except Exception:
            # at least get the core message out if something happened
            self._error_string = self.message
        if len(args) > 0:
            # If there is a non-kwarg parameter, assume it's the error
            # message or reason description and tack it on to the end
            # of the exception message
            # Convert all arguments into their string representations...
            args = ["%s" % arg for arg in args]
            self._error_string = (self._error_string +
                                  "\nDetails: %s" % '\n'.join(args))

    def __str__(self):
        return self._error_string


class MissingArgumentError(GlanceException):
    message = "Missing required argument."


class MissingCredentialError(GlanceException):
    message = "Missing required credential: %(required)s"


class BadAuthStrategy(GlanceException):
    message = "Incorrect auth strategy, expected \"%(expected)s\" but "


class NotFound(GlanceException):
    message = "An object with the specified identifier was not found."


class UnknownScheme(GlanceException):
    message = "Unknown scheme '%(scheme)s' found in URI"


class BadStoreUri(GlanceException):
    message = "The Store URI %(uri)s was malformed. Reason: %(reason)s"


class Duplicate(GlanceException):
    message = "An object with the same identifier already exists."


class StorageFull(GlanceException):
    message = "There is not enough disk space on the image storage media."


class StorageWriteDenied(GlanceException):
    message = "Permission to write image storage media denied."


class ImportFailure(GlanceException):
    message = "Failed to import requested object/class: '%(import_str)s'. \
    Reason: %(reason)s"


class AuthBadRequest(GlanceException):
    message = "Connect error/bad request to Auth service at URL %(url)s."


class AuthUrlNotFound(GlanceException):
    message = "Auth service at URL %(url)s not found."


class AuthorizationFailure(GlanceException):
    message = "Authorization failed."


class NotAuthorized(GlanceException):
    message = "You are not authorized to complete this action."


class NotAuthorizedPublicImage(NotAuthorized):
    message = "You are not authorized to complete this action."


class Invalid(GlanceException):
    message = "Data supplied was not valid."


class AuthorizationRedirect(GlanceException):
    message = "Redirecting to %(uri)s for authorization."


class DatabaseMigrationError(GlanceException):
    message = "There was an error migrating the database."


class ClientConnectionError(GlanceException):
    message = "There was an error connecting to a server"


class ClientConfigurationError(GlanceException):
    message = "There was an error configuring the client."


class MultipleChoices(GlanceException):
    message = "The request returned a 302 Multiple Choices. This generally "


class InvalidContentType(GlanceException):
    message = "Invalid content type %(content_type)s"


class BadRegistryConnectionConfiguration(GlanceException):
    message = "Registry was not configured correctly on API server. "


class BadStoreConfiguration(GlanceException):
    message = "Store %(store_name)s could not be configured correctly. "


class BadDriverConfiguration(GlanceException):
    message = "Driver %(driver_name)s could not be configured correctly. "


class StoreDeleteNotSupported(GlanceException):
    message = "Deleting images from this store is not supported."


class StoreAddDisabled(GlanceException):
    message = "Configuration for store failed. Adding images to this "


class InvalidNotifierStrategy(GlanceException):
    message = "'%(strategy)s' is not an available notifier strategy."


class MaxRedirectsExceeded(GlanceException):
    message = "Maximum redirects (%(redirects)s) was exceeded."


class InvalidRedirect(GlanceException):
    message = "Received invalid HTTP redirect."


class NoServiceEndpoint(GlanceException):
    message = "Response from Keystone does not contain a Glance endpoint."


class RegionAmbiguity(GlanceException):
    message = "Multiple 'image' service matches for region %(region)s. This "

########NEW FILE########
__FILENAME__ = policy
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 OpenStack, LLC.
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

"""Common Policy Engine Implementation"""

import json


class NotAuthorized(Exception):
    pass


_BRAIN = None


def set_brain(brain):
    """Set the brain used by enforce().

    Defaults use Brain() if not set.

    """
    global _BRAIN
    _BRAIN = brain


def reset():
    """Clear the brain used by enforce()."""
    global _BRAIN
    _BRAIN = None


def enforce(match_list, target_dict, credentials_dict):
    """Enforces authorization of some rules against credentials.

    :param match_list: nested tuples of data to match against
    The basic brain supports three types of match lists:
        1) rules
            looks like: ('rule:compute:get_instance',)
            Retrieves the named rule from the rules dict and recursively
            checks against the contents of the rule.
        2) roles
            looks like: ('role:compute:admin',)
            Matches if the specified role is in credentials_dict['roles'].
        3) generic
            ('tenant_id:%(tenant_id)s',)
            Substitutes values from the target dict into the match using
            the % operator and matches them against the creds dict.

    Combining rules:
        The brain returns True if any of the outer tuple of rules match
        and also True if all of the inner tuples match. You can use this to
        perform simple boolean logic.  For example, the following rule would
        return True if the creds contain the role 'admin' OR the if the
        tenant_id matches the target dict AND the the creds contains the
        role 'compute_sysadmin':

        {
            "rule:combined": (
                'role:admin',
                ('tenant_id:%(tenant_id)s', 'role:compute_sysadmin')
            )
        }


    Note that rule and role are reserved words in the credentials match, so
    you can't match against properties with those names. Custom brains may
    also add new reserved words. For example, the HttpBrain adds http as a
    reserved word.

    :param target_dict: dict of object properties
    Target dicts contain as much information as we can about the object being
    operated on.

    :param credentials_dict: dict of actor properties
    Credentials dicts contain as much information as we can about the user
    performing the action.

    :raises NotAuthorized if the check fails

    """
    global _BRAIN
    if not _BRAIN:
        _BRAIN = Brain()
    if not _BRAIN.check(match_list, target_dict, credentials_dict):
        raise NotAuthorized()


class Brain(object):
    """Implements policy checking."""
    @classmethod
    def load_json(cls, data, default_rule=None):
        """Init a brain using json instead of a rules dictionary."""
        rules_dict = json.loads(data)
        return cls(rules=rules_dict, default_rule=default_rule)

    def __init__(self, rules=None, default_rule=None):
        self.rules = rules or {}
        self.default_rule = default_rule

    def add_rule(self, key, match):
        self.rules[key] = match

    def _check(self, match, target_dict, cred_dict):
        match_kind, match_value = match.split(':', 1)
        try:
            f = getattr(self, '_check_%s' % match_kind)
        except AttributeError:
            if not self._check_generic(match, target_dict, cred_dict):
                return False
        else:
            if not f(match_value, target_dict, cred_dict):
                return False
        return True

    def check(self, match_list, target_dict, cred_dict):
        """Checks authorization of some rules against credentials.

        Detailed description of the check with examples in policy.enforce().

        :param match_list: nested tuples of data to match against
        :param target_dict: dict of object properties
        :param credentials_dict: dict of actor properties

        :returns: True if the check passes

        """
        if not match_list:
            return True
        for and_list in match_list:
            if isinstance(and_list, basestring):
                and_list = (and_list,)
            if all([self._check(item, target_dict, cred_dict)
                    for item in and_list]):
                return True
        return False

    def _check_rule(self, match, target_dict, cred_dict):
        """Recursively checks credentials based on the brains rules."""
        try:
            new_match_list = self.rules[match]
        except KeyError:
            if self.default_rule and match != self.default_rule:
                new_match_list = ('rule:%s' % self.default_rule,)
            else:
                return False

        return self.check(new_match_list, target_dict, cred_dict)

    def _check_role(self, match, target_dict, cred_dict):
        """Check that there is a matching role in the cred dict."""
        return match in cred_dict['roles']

    def _check_generic(self, match, target_dict, cred_dict):
        """Check an individual match.

        Matches look like:

            tenant:%(tenant_id)s
            role:compute:admin

        """

        # TODO(termie): do dict inspection via dot syntax
        match = match % target_dict
        key, value = match.split(':', 1)
        if key in cred_dict:
            return value == cred_dict[key]
        return False

########NEW FILE########
__FILENAME__ = utils
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""
System-level utilities and helper functions.
"""

import datetime
import errno
import logging
import os
import platform
import subprocess
import sys
import uuid

import iso8601

from balancer.common import exception


logger = logging.getLogger(__name__)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from and the
    type of the singleton instance cannot be checked with `isinstance`..

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self, conf):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated(conf)
            return self._instance

    def __call__(self):
        """
        Call method that raises an exception in order to prevent creation
        of multiple instances of the singleton. The `Instance` method should
        be used instead.

        """
        raise TypeError(
            'Singletons must be accessed through the `Instance` method.')


def checkNone(obj):
    if bool(obj):
        if obj != 'None':
            return True
    return False


def chunkreadable(iter, chunk_size=65536):
    """
    Wrap a readable iterator with a reader yielding chunks of
    a preferred size, otherwise leave iterator unchanged.

    :param iter: an iter which may also be readable
    :param chunk_size: maximum size of chunk
    """
    return chunkiter(iter, chunk_size) if hasattr(iter, 'read') else iter


def chunkiter(fp, chunk_size=65536):
    """
    Return an iterator to a file-like obj which yields fixed size chunks

    :param fp: a file-like object
    :param chunk_size: maximum size of chunk
    """
    while True:
        chunk = fp.read(chunk_size)
        if chunk:
            yield chunk
        else:
            break


def image_meta_to_http_headers(image_meta):
    """
    Returns a set of image metadata into a dict
    of HTTP headers that can be fed to either a Webob
    Request object or an httplib.HTTP(S)Connection object

    :param image_meta: Mapping of image metadata
    """
    headers = {}
    for k, v in image_meta.items():
        if v is not None:
            if k == 'properties':
                for pk, pv in v.items():
                    if pv is not None:
                        headers["x-image-meta-property-%s"
                                % pk.lower()] = unicode(pv)
            else:
                headers["x-image-meta-%s" % k.lower()] = unicode(v)
    return headers


def add_features_to_http_headers(features, headers):
    """
    Adds additional headers representing balancer features to be enabled.

    :param headers: Base set of headers
    :param features: Map of enabled features
    """
    if features:
        for k, v in features.items():
            if v is not None:
                headers[k.lower()] = unicode(v)


def get_image_meta_from_headers(response):
    """
    Processes HTTP headers from a supplied response that
    match the x-image-meta and x-image-meta-property and
    returns a mapping of image metadata and properties

    :param response: Response to process
    """
    result = {}
    properties = {}

    if hasattr(response, 'getheaders'):  # httplib.HTTPResponse
        headers = response.getheaders()
    else:  # webob.Response
        headers = response.headers.items()

    for key, value in headers:
        key = str(key.lower())
        if key.startswith('x-image-meta-property-'):
            field_name = key[len('x-image-meta-property-'):].replace('-', '_')
            properties[field_name] = value or None
        elif key.startswith('x-image-meta-'):
            field_name = key[len('x-image-meta-'):].replace('-', '_')
            result[field_name] = value or None
    result['properties'] = properties
    if 'size' in result:
        try:
            result['size'] = int(result['size'])
        except ValueError:
            raise exception.Invalid
    for key in ('is_public', 'deleted', 'protected'):
        if key in result:
            result[key] = bool_from_header_value(result[key])
    return result


def bool_from_header_value(value):
    """
    Returns True if value is a boolean True or the
    string 'true', case-insensitive, False otherwise
    """
    if isinstance(value, bool):
        return value
    elif isinstance(value, (basestring, unicode)):
        if str(value).lower() == 'true':
            return True
    return False


def bool_from_string(subject):
    """
    Interpret a string as a boolean.

    Any string value in:
        ('True', 'true', 'On', 'on', '1')
    is interpreted as a boolean True.

    Useful for JSON-decoded stuff and config file parsing
    """
    if isinstance(subject, bool):
        return subject
    elif isinstance(subject, int):
        return subject == 1
    if hasattr(subject, 'startswith'):  # str or unicode...
        if subject.strip().lower() in ('true', 'on', '1'):
            return True
    return False


def import_class(import_str):
    """Returns a class from a string including module and class"""
    mod_str, _sep, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ImportError, ValueError, AttributeError), e:
        raise exception.ImportFailure(import_str=import_str,
                                      reason=e)


def import_object(import_str):
    """Returns an object including a module or module and class"""
    try:
        __import__(import_str)
        return sys.modules[import_str]
    except ImportError:
        cls = import_class(import_str)
        return cls()


def generate_uuid():
    return str(uuid.uuid4())


def is_uuid_like(value):
    try:
        uuid.UUID(value)
        return True
    except Exception:
        return False


def isotime(at=None):
    """Stringify time in ISO 8601 format"""
    if not at:
        at = datetime.datetime.utcnow()
    str = at.strftime(TIME_FORMAT)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    str += ('Z' if tz == 'UTC' else tz)
    return str


def parse_isotime(timestr):
    """Parse time from ISO 8601 format"""
    try:
        return iso8601.parse_date(timestr)
    except iso8601.ParseError as e:
        raise ValueError(e.message)
    except TypeError as e:
        raise ValueError(e.message)


def normalize_time(timestamp):
    """Normalize time in arbitrary timezone to UTC"""
    offset = timestamp.utcoffset()
    return timestamp.replace(tzinfo=None) - offset if offset else timestamp


def safe_mkdirs(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


def safe_remove(path):
    try:
        os.remove(path)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise


class PrettyTable(object):
    """Creates an ASCII art table for use in bin/balancer

    Example:

        ID  Name              Size         Hits
        --- ----------------- ------------ -----
        122 image                       22     0
    """
    def __init__(self):
        self.columns = []

    def add_column(self, width, label="", just='l'):
        """Add a column to the table

        :param width: number of characters wide the column should be
        :param label: column heading
        :param just: justification for the column, 'l' for left,
                     'r' for right
        """
        self.columns.append((width, label, just))

    def make_header(self):
        label_parts = []
        break_parts = []
        for width, label, _ in self.columns:
            # NOTE(sirp): headers are always left justified
            label_part = self._clip_and_justify(label, width, 'l')
            label_parts.append(label_part)

            break_part = '-' * width
            break_parts.append(break_part)

        label_line = ' '.join(label_parts)
        break_line = ' '.join(break_parts)
        return '\n'.join([label_line, break_line])

    def make_row(self, *args):
        row = args
        row_parts = []
        for data, (width, _, just) in zip(row, self.columns):
            row_part = self._clip_and_justify(data, width, just)
            row_parts.append(row_part)

        row_line = ' '.join(row_parts)
        return row_line

    @staticmethod
    def _clip_and_justify(data, width, just):
        # clip field to column width
        clipped_data = str(data)[:width]

        if just == 'r':
            # right justify
            justified = clipped_data.rjust(width)
        else:
            # left justify
            justified = clipped_data.ljust(width)

        return justified


def get_terminal_size():

    def _get_terminal_size_posix():
        import fcntl
        import struct
        import termios

        height_width = None

        try:
            height_width = struct.unpack('hh', fcntl.ioctl(sys.stderr.fileno(),
                                        termios.TIOCGWINSZ,
                                        struct.pack('HH', 0, 0)))
        except:
            pass

        if not height_width:
            try:
                p = subprocess.Popen(['stty', 'size'],
                                    shell=False,
                                    stdout=subprocess.PIPE)
                return tuple(int(x) for x in p.communicate()[0].split())
            except:
                pass

        return height_width

    def _get_terminal_size_win32():
        try:
            from ctypes import windll, create_string_buffer
            handle = windll.kernel32.GetStdHandle(-12)
            csbi = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(handle, csbi)
        except:
            return None
        if res:
            import struct
            unpack_tmp = struct.unpack("hhhhHhhhhhh", csbi.raw)
            (bufx, bufy, curx, cury, wattr,
            left, top, right, bottom, maxx, maxy) = unpack_tmp
            height = bottom - top + 1
            width = right - left + 1
            return (height, width)
        else:
            return None

    def _get_terminal_size_unknownOS():
        raise NotImplementedError

    func = {'posix': _get_terminal_size_posix,
            'win32': _get_terminal_size_win32}

    height_width = func.get(platform.os.name, _get_terminal_size_unknownOS)()

    if height_width == None:
        raise exception.Invalid()

    for i in height_width:
        if not isinstance(i, int) or i <= 0:
            raise exception.Invalid()

    return height_width[0], height_width[1]

########NEW FILE########
__FILENAME__ = wsgi
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2010 OpenStack LLC.
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
Utility methods for working with WSGI servers
"""

import datetime
import errno
import json
import logging
import os
import signal
import sys
import time

import eventlet
import eventlet.greenio
from eventlet.green import socket, ssl
import eventlet.wsgi
from paste import deploy
import routes
import routes.middleware
import webob.dec
import webob.exc

from balancer.common import cfg
from balancer.common import exception
from balancer.common import utils


bind_opts = [
    cfg.StrOpt('bind_host', default='0.0.0.0'),
    cfg.IntOpt('bind_port'),
]

socket_opts = [
    cfg.IntOpt('backlog', default=4096),
    cfg.StrOpt('cert_file'),
    cfg.StrOpt('key_file'),
]

workers_opt = cfg.IntOpt('workers', default=0)


class WritableLogger(object):
    """A thin wrapper that responds to `write` and logs."""

    def __init__(self, logger, level=logging.DEBUG):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg.strip("\n"))


def get_bind_addr(conf, default_port=None):
    """Return the host and port to bind to."""
    conf.register_opts(bind_opts)
    return (conf.bind_host, conf.bind_port or default_port)


def get_socket(conf, default_port):
    """
    Bind socket to bind ip:port in conf

    note: Mostly comes from Swift with a few small changes...

    :param conf: a cfg.ConfigOpts object
    :param default_port: port to bind to if none is specified in conf

    :returns : a socket object as returned from socket.listen or
               ssl.wrap_socket if conf specifies cert_file
    """
    bind_addr = get_bind_addr(conf, default_port)

    # TODO(jaypipes): eventlet's greened socket module does not actually
    # support IPv6 in getaddrinfo(). We need to get around this in the
    # future or monitor upstream for a fix
    address_family = [addr[0] for addr in socket.getaddrinfo(bind_addr[0],
            bind_addr[1], socket.AF_UNSPEC, socket.SOCK_STREAM)
            if addr[0] in (socket.AF_INET, socket.AF_INET6)][0]

    conf.register_opts(socket_opts)

    cert_file = conf.cert_file
    key_file = conf.key_file
    use_ssl = cert_file or key_file
    if use_ssl and (not cert_file or not key_file):
        raise RuntimeError(_("When running server in SSL mode, you must "
                             "specify both a cert_file and key_file "
                             "option value in your configuration file"))

    sock = None
    retry_until = time.time() + 30
    while not sock and time.time() < retry_until:
        try:
            sock = eventlet.listen(bind_addr, backlog=conf.backlog,
                                   family=address_family)
            if use_ssl:
                sock = ssl.wrap_socket(sock, certfile=cert_file,
                                       keyfile=key_file)
        except socket.error, err:
            if err.args[0] != errno.EADDRINUSE:
                raise
            eventlet.sleep(0.1)
    if not sock:
        raise RuntimeError(_("Could not bind to %s:%s after trying for 30 "
                             "seconds") % bind_addr)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # in my experience, sockets can hang around forever without keepalive
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    # This option isn't available in the OS X version of eventlet
    if hasattr(socket, 'TCP_KEEPIDLE'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 600)

    return sock


class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, threads=1000):
        self.threads = threads
        self.children = []
        self.running = True

    def start(self, application, conf, default_port):
        """
        Run a WSGI server with the given application.

        :param application: The application to run in the WSGI server
        :param conf: a cfg.ConfigOpts object
        :param default_port: Port to bind to if none is specified in conf
        """
        def kill_children(*args):
            """Kills the entire process group."""
            self.logger.error(_('SIGTERM received'))
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            self.running = False
            os.killpg(0, signal.SIGTERM)

        def hup(*args):
            """
            Shuts down the server, but allows running requests to complete
            """
            self.logger.error(_('SIGHUP received'))
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            self.running = False

        self.application = application
        self.sock = get_socket(conf, default_port)
        conf.register_opt(workers_opt)

        self.logger = logging.getLogger('eventlet.wsgi.server')

        if conf.workers == 0:
            # Useful for profiling, test, debug etc.
            self.pool = eventlet.GreenPool(size=self.threads)
            self.pool.spawn_n(self._single_run, application, self.sock)
            return

        self.logger.info(_("Starting %d workers") % conf.workers)
        signal.signal(signal.SIGTERM, kill_children)
        signal.signal(signal.SIGHUP, hup)
        while len(self.children) < conf.workers:
            self.run_child()

    def wait_on_children(self):
        while self.running:
            try:
                pid, status = os.wait()
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    self.logger.error(_('Removing dead child %s') % pid)
                    self.children.remove(pid)
                    self.run_child()
            except OSError, err:
                if err.errno not in (errno.EINTR, errno.ECHILD):
                    raise
            except KeyboardInterrupt:
                sys.exit(1)
                self.logger.info(_('Caught keyboard interrupt. Exiting.'))
                break
        eventlet.greenio.shutdown_safe(self.sock)
        self.sock.close()
        self.logger.debug(_('Exited'))

    def wait(self):
        """Wait until all servers have completed running."""
        try:
            if self.children:
                self.wait_on_children()
            else:
                self.pool.waitall()
        except KeyboardInterrupt:
            pass

    def run_child(self):
        pid = os.fork()
        if pid == 0:
            signal.signal(signal.SIGHUP, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            self.run_server()
            self.logger.info(_('Child %d exiting normally') % os.getpid())
            return
        else:
            self.logger.info(_('Started child %s') % pid)
            self.children.append(pid)

    def run_server(self):
        """Run a WSGI server."""
        eventlet.wsgi.HttpProtocol.default_request_version = "HTTP/1.0"
        eventlet.hubs.use_hub('poll')
        eventlet.patcher.monkey_patch(all=False, socket=True)
        self.pool = eventlet.GreenPool(size=self.threads)
        try:
            eventlet.wsgi.server(self.sock, self.application,
                    log=WritableLogger(self.logger), custom_pool=self.pool)
        except socket.error, err:
            if err[0] != errno.EINVAL:
                raise
        self.pool.waitall()

    def _single_run(self, application, sock):
        """Start a WSGI server in a new green thread."""
        self.logger.info(_("Starting single process server"))
        eventlet.wsgi.server(sock, application, custom_pool=self.pool,
                             log=WritableLogger(self.logger))


class Middleware(object):
    """
    Base WSGI middleware wrapper. These classes require an application to be
    initialized that will be called next.  By default the middleware will
    simply call its wrapped app, or you can override __call__ to customize its
    behavior.
    """

    def __init__(self, application):
        self.application = application

    def process_request(self, req):
        """
        Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.

        """
        return None

    def process_response(self, response):
        """Do whatever you'd like to the response."""
        return response

    @webob.dec.wsgify
    def __call__(self, req):
        response = self.process_request(req)
        if response:
            return response
        response = req.get_response(self.application)
        return self.process_response(response)


class Debug(Middleware):
    """
    Helper class that can be inserted into any WSGI application chain
    to get information about the request and response.
    """

    @webob.dec.wsgify
    def __call__(self, req):
        print ("*" * 40) + " REQUEST ENVIRON"
        for key, value in req.environ.items():
            print key, "=", value
        print
        resp = req.get_response(self.application)

        print ("*" * 40) + " RESPONSE HEADERS"
        for (key, value) in resp.headers.iteritems():
            print key, "=", value
        print

        resp.app_iter = self.print_generator(resp.app_iter)

        return resp

    @staticmethod
    def print_generator(app_iter):
        """
        Iterator that prints the contents of a wrapper string iterator
        when iterated.
        """
        print ("*" * 40) + " BODY"
        for part in app_iter:
            sys.stdout.write(part)
            sys.stdout.flush()
            yield part
        print


class Router(object):
    """
    WSGI middleware that maps incoming requests to WSGI apps.
    """

    def __init__(self, mapper):
        """
        Create a router for the given routes.Mapper.

        Each route in `mapper` must specify a 'controller', which is a
        WSGI app to call.  You'll probably want to specify an 'action' as
        well and have your controller be a wsgi.Controller, who will route
        the request to the action method.

        Examples:
          mapper = routes.Mapper()
          sc = ServerController()

          # Explicit mapping of one route to a controller+action
          mapper.connect(None, "/svrlist", controller=sc, action="list")

          # Actions are all implicitly defined
          mapper.resource("server", "servers", controller=sc)

          # Pointing to an arbitrary WSGI app.  You can specify the
          # {path_info:.*} parameter so the target app can be handed just that
          # section of the URL.
          mapper.connect(None, "/v1.0/{path_info:.*}", controller=BlogApp())
        """
        self.map = mapper
        self._router = routes.middleware.RoutesMiddleware(self._dispatch,
                                                          self.map)

    @webob.dec.wsgify
    def __call__(self, req):
        """
        Route the incoming request to a controller based on self.map.
        If no match, return a 404.
        """
        return self._router

    @staticmethod
    @webob.dec.wsgify
    def _dispatch(req):
        """
        Called by self._router after matching the incoming request to a route
        and putting the information into req.environ.  Either returns 404
        or the routed WSGI app's response.
        """
        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            return webob.exc.HTTPNotFound()
        app = match['controller']
        return app


class Request(webob.Request):
    """Add some Openstack API-specific logic to the base webob.Request."""

    def best_match_content_type(self):
        """Determine the requested response content-type."""
        supported = ('application/json',)
        bm = self.accept.best_match(supported)
        return bm or 'application/json'

    def get_content_type(self, allowed_content_types):
        """Determine content type of the request body."""
        if not "Content-Type" in self.headers:
            raise exception.InvalidContentType(content_type=None)

        content_type = self.content_type

        if content_type not in allowed_content_types:
            raise exception.InvalidContentType(content_type=content_type)
        else:
            return content_type


class JSONRequestDeserializer(object):
    def has_body(self, request):
        """
        Returns whether a Webob.Request object will possess an entity body.

        :param request:  Webob.Request object
        """
        if 'transfer-encoding' in request.headers:
            return True
        elif request.content_length > 0:
            return True

        return False

    def from_json(self, datastring):
        return json.loads(datastring)

    def default(self, request):
        if self.has_body(request):
            return {'body': self.from_json(request.body)}
        else:
            return {}


class JSONResponseSerializer(object):

    def to_json(self, data):
        def sanitizer(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return obj

        return json.dumps(data, default=sanitizer)

    def default(self, response, result):
        response.content_type = 'application/json'
        response.body = self.to_json(result)


class Resource(object):
    """
    WSGI app that handles (de)serialization and controller dispatch.

    Reads routing information supplied by RoutesMiddleware and calls
    the requested action method upon its deserializer, controller,
    and serializer. Those three objects may implement any of the basic
    controller action methods (create, update, show, index, delete)
    along with any that may be specified in the api router. A 'default'
    method may also be implemented to be used in place of any
    non-implemented actions. Deserializer methods must accept a request
    argument and return a dictionary. Controller methods must accept a
    request argument. Additionally, they must also accept keyword
    arguments that represent the keys returned by the Deserializer. They
    may raise a webob.exc exception or return a dict, which will be
    serialized by requested content type.
    """
    def __init__(self, controller, deserializer, serializer):
        """
        :param controller: object that implement methods created by routes lib
        :param deserializer: object that supports webob request deserialization
                             through controller-like actions
        :param serializer: object that supports webob response serialization
                           through controller-like actions
        """
        self.controller = controller
        self.serializer = serializer
        self.deserializer = deserializer

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        """WSGI method that controls (de)serialization and method dispatch."""
        action_args = self.get_action_args(request.environ)
        action = action_args.pop('action', None)

        deserialized_request = self.dispatch(self.deserializer,
                                             action, request)
        action_args.update(deserialized_request)

        action_result = self.dispatch(self.controller, action,
                                      request, **action_args)
        try:
            response = webob.Response(request=request)
            self.dispatch(self.serializer, action, response, action_result)
            return response

        # return unserializable result (typically a webob exc)
        except Exception:
            return action_result

    def dispatch(self, obj, action, *args, **kwargs):
        """Find action-specific method on self and call it."""
        try:
            method = getattr(obj, action)
        except AttributeError:
            method = getattr(obj, 'default')

        return method(*args, **kwargs)

    def get_action_args(self, request_environment):
        """Parse dictionary created by routes library."""
        try:
            args = request_environment['wsgiorg.routing_args'][1].copy()
        except Exception:
            return {}

        try:
            del args['controller']
        except KeyError:
            pass

        try:
            del args['format']
        except KeyError:
            pass

        return args


class BasePasteFactory(object):

    """A base class for paste app and filter factories.

    Sub-classes must override the KEY class attribute and provide
    a __call__ method.
    """

    KEY = None

    def __init__(self, conf):
        self.conf = conf

    def __call__(self, global_conf, **local_conf):
        raise NotImplementedError

    def _import_factory(self, local_conf):
        """Import an app/filter class.

        Lookup the KEY from the PasteDeploy local conf and import the
        class named there. This class can then be used as an app or
        filter factory.

        Note we support the <module>:<class> format.

        Note also that if you do e.g.

          key =
              value

        then ConfigParser returns a value with a leading newline, so
        we strip() the value before using it.
        """
        class_name = local_conf[self.KEY].replace(':', '.').strip()
        return utils.import_class(class_name)


class AppFactory(BasePasteFactory):

    """A Generic paste.deploy app factory.

    This requires balancer.app_factory to be set to a callable which returns a
    WSGI app when invoked. The format of the name is <module>:<callable> e.g.

      [app:apiv1app]
      paste.app_factory = balancer.common.wsgi:app_factory
      balancer.app_factory = balancer.api.v1:API

    The WSGI app constructor must accept a ConfigOpts object and a local config
    dict as its two arguments.
    """

    KEY = 'balancer.app_factory'

    def __call__(self, global_conf, **local_conf):
        """The actual paste.app_factory protocol method."""
        factory = self._import_factory(local_conf)
        return factory(self.conf, **local_conf)


class FilterFactory(AppFactory):

    """A Generic paste.deploy filter factory.

    This requires balancer.filter_factory to be set to a callable which returns
    a WSGI filter when invoked. The format is <module>:<callable> e.g.

      [filter:cache]
      paste.filter_factory = balancer.common.wsgi:filter_factory
      balancer.filter_factory = balancer.api.middleware.cache:CacheFilter

    The WSGI filter constructor must accept a WSGI app, a ConfigOpts object and
    a local config dict as its three arguments.
    """

    KEY = 'balancer.filter_factory'

    def __call__(self, global_conf, **local_conf):
        """The actual paste.filter_factory protocol method."""
        factory = self._import_factory(local_conf)

        def filter(app):
            return factory(app, self.conf, **local_conf)

        return filter


def setup_paste_factories(conf):
    """Set up the generic paste app and filter factories.

    Set things up so that:

      paste.app_factory = balancer.common.wsgi:app_factory

    and

      paste.filter_factory = balancer.common.wsgi:filter_factory

    work correctly while loading PasteDeploy configuration.

    The app factories are constructed at runtime to allow us to pass a
    ConfigOpts object to the WSGI classes.

    :param conf: a ConfigOpts object
    """
    global app_factory, filter_factory
    app_factory = AppFactory(conf)
    filter_factory = FilterFactory(conf)


def teardown_paste_factories():
    """Reverse the effect of setup_paste_factories()."""
    global app_factory, filter_factory
    del app_factory
    del filter_factory


def paste_deploy_app(paste_config_file, app_name, conf):
    """Load a WSGI app from a PasteDeploy configuration.

    Use deploy.loadapp() to load the app from the PasteDeploy configuration,
    ensuring that the supplied ConfigOpts object is passed to the app and
    filter constructors.

    :param paste_config_file: a PasteDeploy config file
    :param app_name: the name of the app/pipeline to load from the file
    :param conf: a ConfigOpts object to supply to the app and its filters
    :returns: the WSGI app
    """
    setup_paste_factories(conf)
    try:
        return deploy.loadapp("config:%s" % paste_config_file, name=app_name)
    finally:
        teardown_paste_factories()

########NEW FILE########
__FILENAME__ = api
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
import functools
import eventlet
import copy

from openstack.common import exception
import balancer.exception as exc

from balancer.core import commands
from balancer.core import lb_status
from balancer.core import scheduler
from balancer import drivers
from balancer.db import api as db_api
from balancer import utils


LOG = logging.getLogger(__name__)


def asynchronous(func):
    @functools.wraps(func)
    def _inner(*args, **kwargs):
        if kwargs.pop('async', True):
            eventlet.spawn(func, *args, **kwargs)
        else:
            return func(*args, **kwargs)
    return _inner


def lb_get_index(conf, tenant_id):
    lbs = db_api.loadbalancer_get_all_by_project(conf, tenant_id)
    lbs = [db_api.unpack_extra(lb) for lb in lbs]

    for lb in lbs:
        if 'virtualIps' in lb:
            lb.pop('virtualIps')
    return lbs


def lb_find_for_vm(conf, tenant_id, vm_id):
    lbs = db_api.loadbalancer_get_all_by_vm_id(conf, tenant_id, vm_id)
    lbs = [db_api.unpack_extra(lb) for lb in lbs]
    return lbs


def lb_get_data(conf, tenant_id, lb_id):
    LOG.debug("Getting information about loadbalancer with id: %s" % lb_id)
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    lb_dict = db_api.unpack_extra(lb)
    if 'virtualIps' in lb_dict:
        lb_dict.pop("virtualIps")
    LOG.debug("Got information: %s" % list)
    return lb_dict


def lb_show_details(conf, tenant_id, lb_id):
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sf = db_api.serverfarm_get_all_by_lb_id(conf, lb_id)[0]
    vips = db_api.virtualserver_get_all_by_sf_id(conf, sf['id'])
    rs = db_api.server_get_all_by_sf_id(conf, sf['id'])
    probes = db_api.probe_get_all_by_sf_id(conf, sf['id'])
    stickies = db_api.sticky_get_all_by_sf_id(conf, sf['id'])

    lb_ref = db_api.unpack_extra(lb)
    lb_ref['nodes'] = [db_api.unpack_extra(rserver) for rserver in rs]
    lb_ref['virtualIps'] = [db_api.unpack_extra(vip) for vip in vips]
    lb_ref['healthMonitor'] = [db_api.unpack_extra(probe) for probe in probes]
    lb_ref['sessionPersistence'] = [db_api.unpack_extra(sticky)\
            for sticky in stickies]
    return lb_ref


def create_lb(conf, params):
    node_values = params.pop('nodes', [])
    probe_values = params.pop('healthMonitor', [])
    vip_values = params.pop('virtualIps', [])
    lb_values = db_api.loadbalancer_pack_extra(params)

    lb_ref = db_api.loadbalancer_create(conf, lb_values)
    sf_ref = db_api.serverfarm_create(conf, {'lb_id': lb_ref['id']})
    db_api.predictor_create(conf, {'sf_id': sf_ref['id'],
                                   'type': lb_ref['algorithm']})
    vip_update_values = {'protocol': lb_ref['protocol']}

    vips = []
    for vip in vip_values:
        vip = db_api.virtualserver_pack_extra(vip)
        db_api.pack_update(vip, vip_update_values)
        vip['lb_id'] = lb_ref['id']
        vip['sf_id'] = sf_ref['id']
        vips.append(db_api.virtualserver_create(conf, vip))

    servers = []
    for server in node_values:
        server = db_api.server_pack_extra(server)
        server['sf_id'] = sf_ref['id']
        servers.append(db_api.server_create(conf, server))

    probes = []
    for probe in probe_values:
        probe = db_api.probe_pack_extra(probe)
        probe['lb_id'] = lb_ref['id']
        probe['sf_id'] = sf_ref['id']
        probes.append(db_api.probe_create(conf, probe))

    device_ref = scheduler.schedule(conf, lb_ref)
    db_api.loadbalancer_update(conf, lb_ref['id'],
                               {'device_id': device_ref['id']})
    device_driver = drivers.get_device_driver(conf, device_ref['id'])
    with device_driver.request_context() as ctx:
        try:
            commands.create_loadbalancer(ctx, sf_ref, vips, servers, probes,
                                         [])
        except Exception:
            with utils.save_and_reraise_exception():
                db_api.loadbalancer_update(conf, lb_ref['id'],
                                           {'status': lb_status.ERROR,
                                            'deployed': False})
    db_api.loadbalancer_update(conf, lb_ref['id'],
                               {'status': lb_status.ACTIVE,
                                'deployed': True})
    return lb_ref['id']


@asynchronous
def update_lb(conf, tenant_id, lb_id, lb_body):
    lb_ref = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    old_lb_ref = copy.deepcopy(lb_ref)
    db_api.pack_update(lb_ref, lb_body)
    lb_ref = db_api.loadbalancer_update(conf, lb_id, lb_ref)
    if (lb_ref['algorithm'] == old_lb_ref['algorithm'] and
        lb_ref['protocol'] == old_lb_ref['protocol']):
        LOG.debug("In LB %r algorithm and protocol have not changed, "
                     "nothing to do on the device %r.",
                     lb_ref['id'], lb_ref['device_id'])
        return

    sf_ref = db_api.serverfarm_get_all_by_lb_id(conf, lb_ref['id'])[0]
    if lb_ref['algorithm'] != old_lb_ref['algorithm']:
        predictor_ref = db_api.predictor_get_by_sf_id(conf, sf_ref['id'])
        db_api.predictor_update(conf, predictor_ref['id'],
                                {'type': lb_ref['algorithm']})

    vips = db_api.virtualserver_get_all_by_sf_id(conf, sf_ref['id'])
    if lb_ref['protocol'] != old_lb_ref['protocol']:
        vip_update_values = {'protocol': lb_ref['protocol']}
        for vip in vips:
            db_api.pack_update(vip, vip_update_values)
            db_api.virtualserver_update(conf, vip['id'], vip)

    servers = db_api.server_get_all_by_sf_id(conf, sf_ref['id'])
    probes = db_api.probe_get_all_by_sf_id(conf, sf_ref['id'])
    stickies = db_api.sticky_get_all_by_sf_id(conf, sf_ref['id'])

    device_ref = scheduler.reschedule(conf, lb_ref)
    if device_ref['id'] != lb_ref['device_id']:
        from_driver = drivers.get_device_driver(conf, lb_ref['device_id'])
        to_driver = drivers.get_device_driver(conf, device_ref['id'])
        lb_ref = db_api.loadbalancer_update(conf, lb_ref['id'],
                                            {'device_id': device_ref['id']})
    else:
        from_driver = drivers.get_device_driver(conf, device_ref['id'])
        to_driver = from_driver

    with from_driver.request_context() as ctx:
        try:
            commands.delete_loadbalancer(ctx, sf_ref, vips, servers, probes,
                                         stickies)
        except Exception:
            with utils.save_and_reraise_exception():
                db_api.loadbalancer_update(conf, lb_ref['id'],
                                           {'status': lb_status.ERROR})
    with to_driver.request_context() as ctx:
        try:
            commands.create_loadbalancer(ctx, sf_ref, vips, servers, probes,
                                         stickies)
        except Exception:
            with utils.save_and_reraise_exception():
                db_api.loadbalancer_update(conf, lb_ref['id'],
                                           {'status': lb_status.ERROR})
    db_api.loadbalancer_update(conf, lb_ref['id'],
                               {'status': lb_status.ACTIVE})


def delete_lb(conf, tenant_id, lb_id):
    lb_ref = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sf_ref = db_api.serverfarm_get_all_by_lb_id(conf, lb_ref['id'])[0]
    vips = db_api.virtualserver_get_all_by_sf_id(conf, sf_ref['id'])
    servers = db_api.server_get_all_by_sf_id(conf, sf_ref['id'])
    probes = db_api.probe_get_all_by_sf_id(conf, sf_ref['id'])
    stickies = db_api.sticky_get_all_by_sf_id(conf, sf_ref['id'])
    device_driver = drivers.get_device_driver(conf, lb_ref['device_id'])
    with device_driver.request_context() as ctx:
        commands.delete_loadbalancer(ctx, sf_ref, vips, servers, probes,
                                     stickies)
    db_api.probe_destroy_by_sf_id(conf, sf_ref['id'])
    db_api.sticky_destroy_by_sf_id(conf, sf_ref['id'])
    db_api.server_destroy_by_sf_id(conf, sf_ref['id'])
    db_api.virtualserver_destroy_by_sf_id(conf, sf_ref['id'])
    db_api.predictor_destroy_by_sf_id(conf, sf_ref['id'])
    db_api.serverfarm_destroy(conf, sf_ref['id'])
    db_api.loadbalancer_destroy(conf, lb_ref['id'])


def lb_add_nodes(conf, tenant_id, lb_id, nodes):
    nodes_list = []
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sf = db_api.serverfarm_get_all_by_lb_id(conf, lb_id)[0]
    for node in nodes:
        values = db_api.server_pack_extra(node)
        values['sf_id'] = sf['id']
        if not values['status']:
            values['status'] = 'INSERVICE'
        rs_ref = db_api.server_create(conf, values)
        device_driver = drivers.get_device_driver(conf, lb['device_id'])
        with device_driver.request_context() as ctx:
            commands.add_node_to_loadbalancer(ctx, sf, rs_ref)
        nodes_list.append(db_api.unpack_extra(rs_ref))
    return nodes_list


def lb_show_nodes(conf, tenant_id, lb_id):
    node_list = []
    sf = db_api.serverfarm_get_all_by_lb_id(conf,
            lb_id, tenant_id=tenant_id)[0]
    node_list = map(db_api.unpack_extra,
                    db_api.server_get_all_by_sf_id(conf, sf['id']))
    return node_list


def lb_delete_node(conf, tenant_id, lb_id, lb_node_id):
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sf = db_api.serverfarm_get_all_by_lb_id(conf, lb_id)[0]
    rs = db_api.server_get(conf, lb_node_id)
    db_api.server_destroy(conf, lb_node_id)
    device_driver = drivers.get_device_driver(conf, lb['device_id'])
    with device_driver.request_context() as ctx:
        commands.remove_node_from_loadbalancer(ctx, sf, rs)
    return lb_node_id


def lb_change_node_status(conf, tenant_id, lb_id, lb_node_id, lb_node_status):
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    rs = db_api.server_get(conf, lb_node_id)
    sf = db_api.serverfarm_get(conf, rs['sf_id'])
    if rs['state'] == lb_node_status:
        return "OK"

    rs['state'] = lb_node_status
    rsname = rs['name']
    if rs['parent_id'] != "":
        rs['name'] = rs['parent_id']
    LOG.debug("Changing RServer status to: %s" % lb_node_status)
    device_driver = drivers.get_device_driver(conf, lb['device_id'])
    with device_driver.request_context() as ctx:
        if lb_node_status == "inservice":
            commands.activate_rserver(ctx, sf, rs)
        else:
            commands.suspend_rserver(ctx, sf, rs)

    rs['name'] = rsname
    db_api.server_update(conf, rs['id'], rs)
    return db_api.unpack_extra(rs)


def lb_update_node(conf, tenant_id, lb_id, lb_node_id, lb_node):
    rs = db_api.server_get(conf, lb_node_id, tenant_id=tenant_id)

    lb = db_api.loadbalancer_get(conf, lb_id)
    device_driver = drivers.get_device_driver(conf, lb['device_id'])
    sf = db_api.serverfarm_get(conf, rs['sf_id'])

    with device_driver.request_context() as ctx:
        commands.delete_rserver_from_server_farm(ctx, sf, rs)
        db_api.pack_update(rs, lb_node)
        new_rs = db_api.server_update(conf, rs['id'], rs)
        commands.add_rserver_to_server_farm(ctx, sf, new_rs)
    return db_api.unpack_extra(new_rs)


def lb_show_probes(conf, tenant_id, lb_id):
    try:
        sf_ref = db_api.serverfarm_get_all_by_lb_id(conf, lb_id,
                tenant_id=tenant_id)[0]
    except IndexError:
        raise exc.ServerFarmNotFound

    probes = db_api.probe_get_all_by_sf_id(conf, sf_ref['id'])

    list = []
    dict = {"healthMonitoring": {}}
    for probe in probes:
        list.append(db_api.unpack_extra(probe))
    dict['healthMonitoring'] = list
    return dict


def lb_add_probe(conf, tenant_id, lb_id, probe_dict):
    LOG.debug("Got new probe description %s" % probe_dict)
    # NOTE(akscram): historically strange validation, wrong place for it.
    if probe_dict['type'] is None:
        return

    lb_ref = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    # NOTE(akscram): server farms are really only create problems than
    #                they solve multiply use of the virtual IPs.
    try:
        sf_ref = db_api.serverfarm_get_all_by_lb_id(conf, lb_ref['id'])[0]
    except IndexError:
        raise exc.ServerFarmNotFound

    values = db_api.probe_pack_extra(probe_dict)
    values['lb_id'] = lb_ref['id']
    values['sf_id'] = sf_ref['id']
    probe_ref = db_api.probe_create(conf, values)
    device_driver = drivers.get_device_driver(conf, lb_ref['device_id'])
    with device_driver.request_context() as ctx:
        commands.add_probe_to_loadbalancer(ctx, sf_ref, probe_ref)
    return db_api.unpack_extra(probe_ref)


def lb_delete_probe(conf, tenant_id, lb_id, probe_id):
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sf = db_api.serverfarm_get_all_by_lb_id(conf, lb_id)[0]
    probe = db_api.probe_get(conf, probe_id)
    db_api.probe_destroy(conf, probe_id)
    device_driver = drivers.get_device_driver(conf, lb['device_id'])
    with device_driver.request_context() as ctx:
        commands.remove_probe_from_server_farm(ctx, sf, probe)
    return probe_id


def lb_show_sticky(conf, tenant_id, lb_id):
    try:
        sf_ref = db_api.serverfarm_get_all_by_lb_id(conf, lb_id,
                tenant_id=tenant_id)[0]
    except IndexError:
        raise  exc.ServerFarmNotFound

    stickies = db_api.sticky_get_all_by_sf_id(conf, sf_ref['id'])

    list = []
    dict = {"sessionPersistence": {}}
    for sticky in stickies:
        list.append(db_api.unpack_extra(sticky))
    dict['sessionPersistence'] = list
    return dict


def lb_add_sticky(conf, tenant_id, lb_id, st):
    LOG.debug("Got new sticky description %s" % st)
    if st['type'] is None:
        return
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sf = db_api.serverfarm_get_all_by_lb_id(conf, lb_id)[0]
    values = db_api.sticky_pack_extra(st)
    values['sf_id'] = sf['id']
    sticky_ref = db_api.sticky_create(conf, values)
    device_driver = drivers.get_device_driver(conf, lb['device_id'])
    with device_driver.request_context() as ctx:
        commands.add_sticky_to_loadbalancer(ctx, lb, sticky_ref)
    return db_api.unpack_extra(sticky_ref)


def lb_delete_sticky(conf, tenant_id, lb_id, sticky_id):
    lb = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    sticky = db_api.sticky_get(conf, sticky_id)
    device_driver = drivers.get_device_driver(conf, lb['device_id'])
    with device_driver.request_context() as ctx:
        commands.remove_sticky_from_loadbalancer(ctx, lb, sticky)
    db_api.sticky_destroy(conf, sticky_id)
    return sticky_id


def lb_add_vip(conf, tenant_id, lb_id, vip_dict):
    LOG.debug("Called lb_add_vip(), conf: %r, lb_id: %s, vip_dict: %r",
                 conf, lb_id, vip_dict)
    lb_ref = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    # NOTE(akscram): server farms are really only create problems than
    #                they solve multiply use of the virtual IPs.
    try:
        sf_ref = db_api.serverfarm_get_all_by_lb_id(conf, lb_ref['id'])[0]
    except IndexError:
        raise exc.ServerFarmNotFound

    values = db_api.virtualserver_pack_extra(vip_dict)
    values['lb_id'] = lb_ref['id']
    values['sf_id'] = sf_ref['id']
    # XXX(akscram): Set default protocol from LoadBalancer to
    #               VirtualServer if it is not present.
    if not values.get('extra'):
        values['extra'] = {'protocol': lb_ref['protocol']}
    elif 'protocol' not in values['extra']:
        values['extra']['protocol'] = lb_ref['protocol']
    vip_ref = db_api.virtualserver_create(conf, values)
    device_driver = drivers.get_device_driver(conf, lb_ref['device_id'])
    with device_driver.request_context() as ctx:
        commands.create_vip(ctx, vip_ref, sf_ref)
    return db_api.unpack_extra(vip_ref)


def lb_delete_vip(conf, tenant_id, lb_id, vip_id):
    LOG.debug("Called lb_delete_vip(), conf: %r, lb_id: %s, vip_id: %s",
                 conf, lb_id, vip_id)
    lb_ref = db_api.loadbalancer_get(conf, lb_id, tenant_id=tenant_id)
    vip_ref = db_api.virtualserver_get(conf, vip_id)
    device_driver = drivers.get_device_driver(conf, lb_ref['device_id'])
    with device_driver.request_context() as ctx:
        commands.delete_vip(ctx, vip_ref)
    db_api.virtualserver_destroy(conf, vip_id)


def device_get_index(conf):
    devices = db_api.device_get_all(conf)
    devices = [db_api.unpack_extra(dev) for dev in devices]
    return devices


def device_create(conf, **params):
    device_dict = db_api.device_pack_extra(params)
    device = db_api.device_create(conf, device_dict)
    return device


def device_info(params):
    query = params['query_params']
    LOG.debug("DeviceInfoWorker start with Params: %s Query: %s",
                                                            params, query)
    return


def device_show_algorithms(conf):
    devices = db_api.device_get_all(conf)
    algorithms = []
    for device in devices:
        try:
            device_driver = drivers.get_device_driver(conf, device['id'])
            capabilities = device_driver.get_capabilities()
            if capabilities is not None:
                algorithms += [a for a in capabilities.get('algorithms', [])
                               if a not in algorithms]
        except Exception:
            LOG.warn('Failed to get supported algorithms of device %s',
                     device['name'], exc_info=True)
    return algorithms


def device_show_protocols(conf):
    devices = db_api.device_get_all(conf)
    protocols = []
    for device in devices:
        try:
            device_driver = drivers.get_device_driver(conf, device['id'])
            capabilities = device_driver.get_capabilities()
            if capabilities is not None:
                protocols += [a for a in capabilities.get('protocols', [])
                              if a not in protocols]
        except Exception:
            LOG.warn('Failed to get supported protocols of device %s',
                     device['name'], exc_info=True)
    return protocols


def device_delete(conf, device_id):
    try:
        lb_refs = db_api.loadbalancer_get_all_by_device_id(conf, device_id)
    except exc.LoadBalancerNotFound:
        db_api.device_destroy(conf, device_id)
        drivers.delete_device_driver(conf, device_id)
        return
    lbs = []
    for lb_ref in lb_refs:
        lb = db_api.unpack_extra(lb_ref)
        lbs.append(lb['id'])
    raise exc.DeviceConflict('Device %s is in use now by loadbalancers %s' %
                             (device_id, ', '.join(lbs)))

########NEW FILE########
__FILENAME__ = commands
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
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

import functools
import logging
import types

import balancer.db.api as db_api
from balancer import utils

LOG = logging.getLogger(__name__)


class RollbackContext(object):
    def __init__(self):
        self.rollback_stack = []

    def add_rollback(self, rollback):
        self.rollback_stack.append(rollback)


class RollbackContextManager(object):
    def __init__(self, context=None):
        if context is None:
            self.context = RollbackContext()
        else:
            self.context = context

    def __enter__(self):
        return self.context

    def __exit__(self, exc_type, exc_value, exc_tb):
        good = exc_type is None
        if not good:
            LOG.error("Rollback because of: %s", exc_value,
                    exc_info=(exc_value, exc_type, exc_tb))
        rollback_stack = self.context.rollback_stack
        while rollback_stack:
            rollback_stack.pop()(good)
        if not good:
            raise exc_type, exc_value, exc_tb


class Rollback(Exception):
    pass


def with_rollback(func):
    @functools.wraps(func)
    def __inner(ctx, *args, **kwargs):
        gen = func(ctx, *args, **kwargs)
        if not isinstance(gen, types.GeneratorType):
            LOG.critical("Expected generator, got %r instead", gen)
            raise RuntimeError(
                    "Commands with rollback must be generator functions")
        try:
            res = gen.next()
        except StopIteration:
            LOG.warn("Command %s finished w/o yielding", func.__name__)
        else:
            def fin(good):
                if good:
                    gen.close()
                else:
                    try:
                        gen.throw(Rollback)
                    except Rollback:
                        pass
                    except Exception:
                        LOG.exception("Exception during rollback.")
            ctx.add_rollback(fin)
        return res
    return __inner


def ignore_exceptions(func):
    @functools.wraps(func)
    def __inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            LOG.exception("Got exception while executing %s. Ignored.",
                                                                 func.__name__)
    return __inner


@with_rollback
def create_rserver(ctx, rs):
    try:
        # We can't create multiple RS with the same IP. So parent_id points to
        # RS which already deployed and has this IP
        LOG.debug("Creating rserver command execution with rserver: %s", rs)
        LOG.debug("RServer parent_id: %s", rs['parent_id'])
        if not rs['parent_id']:
            ctx.device.create_real_server(rs)
            rs['deployed'] = 'True'
            db_api.server_update(ctx.conf, rs['id'], rs)
        yield
    except Exception:
        with utils.save_and_reraise_exception():
            ctx.device.delete_real_server(rs)
            rs['deployed'] = 'False'
            db_api.server_update(ctx.conf, rs['id'], rs)


@ignore_exceptions
def delete_rserver(ctx, rs):
    rss = []
    LOG.debug("Got delete RS request")
    if rs['parent_id'] == "":
        rss = db_api.server_get_all_by_parent_id(ctx.conf, rs['id'])
        LOG.debug("List of servers: %s", rss)
        ctx.device.delete_real_server(rs)
        if len(rss) > 0:
            for rs_child in rss:
                db_api.server_update(ctx.conf, rs_child['id'],
                                     {'parent_id': rss[-1]['id']})
            db_api.server_update(ctx.conf, rss[-1]['id'],
                                     {'parent_id': '', 'deployed': 'True'})
            ctx.device.create_real_server(rss[-1])


def create_sticky(ctx, sticky):
    ctx.device.create_stickiness(sticky)
    sticky['deployed'] = 'True'
    db_api.sticky_update(ctx.conf, sticky['id'], sticky)


@ignore_exceptions
def delete_sticky(ctx, sticky):
    ctx.device.delete_stickiness(sticky)
    sticky['deployed'] = 'False'
    db_api.sticky_update(ctx.conf, sticky['id'], sticky)


@ignore_exceptions
def delete_server_farm(ctx, sf):
    ctx.device.delete_server_farm(sf)
    sf['deployed'] = 'False'
    db_api.serverfarm_update(ctx.conf, sf['id'], sf)


@with_rollback
def create_server_farm(ctx, sf_ref):
    try:
        predictor_ref = db_api.predictor_get_by_sf_id(ctx.conf, sf_ref['id'])
        ctx.device.create_server_farm(sf_ref, predictor_ref)
        db_api.serverfarm_update(ctx.conf, sf_ref['id'], {'deployed': True})
        yield
    except Exception:
        with utils.save_and_reraise_exception():
            delete_server_farm(ctx, sf_ref)


@with_rollback
def add_rserver_to_server_farm(ctx, server_farm, rserver):
    try:
        if (rserver.get('parent_id') and rserver['parent_id'] != ""):
            #Nasty hack. We need to think how todo this more elegant
            rserver['name'] = rserver['parent_id']
        ctx.device.add_real_server_to_server_farm(server_farm, rserver)
        yield
    except Exception:
        with utils.save_and_reraise_exception():
            ctx.device.delete_real_server_from_server_farm(server_farm,
                    rserver)


@ignore_exceptions
def delete_rserver_from_server_farm(ctx, server_farm, rserver):
    ctx.device.delete_real_server_from_server_farm(server_farm, rserver)


@ignore_exceptions
def delete_probe(ctx, probe):
    ctx.device.delete_probe(probe)
    probe['deployed'] = 'False'
    db_api.probe_update(ctx.conf, probe['id'], probe)


@with_rollback
def create_probe(ctx, probe):
    try:
        ctx.device.create_probe(probe)
        db_api.probe_update(ctx.conf, probe['id'], {'deployed': True})
        yield
    except Exception:
        with utils.save_and_reraise_exception():
            delete_probe(ctx, probe)


@with_rollback
def add_probe_to_server_farm(ctx, server_farm, probe):
    try:
        ctx.device.add_probe_to_server_farm(server_farm, probe)
        yield
    except Exception:
        with utils.save_and_reraise_exception():
            ctx.device.delete_probe_from_server_farm(server_farm, probe)


@ignore_exceptions
def remove_probe_from_server_farm(ctx, server_farm, probe):
    ctx.device.delete_probe_from_server_farm(server_farm, probe)


def activate_rserver(ctx, server_farm, rserver):
    ctx.device.activate_real_server(server_farm, rserver)


def suspend_rserver(ctx, server_farm, rserver):
    ctx.device.suspend_real_server(server_farm, rserver)


@ignore_exceptions
def delete_vip(ctx, vip):
    ctx.device.delete_virtual_ip(vip)
    vip['deployed'] = 'False'
    db_api.virtualserver_update(ctx.conf, vip['id'], vip)


@with_rollback
def create_vip(ctx, vip, server_farm):
    try:
        ctx.device.create_virtual_ip(vip, server_farm)
        db_api.virtualserver_update(ctx.conf, vip['id'], {'deployed': True})
        yield
    except Exception:
        with utils.save_and_reraise_exception():
            delete_vip(ctx, vip)


def create_loadbalancer(ctx, sf_ref, vips, servers, probes, stickies):
    create_server_farm(ctx, sf_ref)
    for vip_ref in vips:
        create_vip(ctx, vip_ref, sf_ref)
    for server_ref in servers:
        add_node_to_loadbalancer(ctx, sf_ref, server_ref)
    for probe_ref in probes:
        add_probe_to_loadbalancer(ctx, sf_ref, probe_ref)
    for sticky_ref in stickies:
        create_sticky(ctx, sticky_ref)


def delete_loadbalancer(ctx, sf_ref, vips, servers, probes, stickies):
    for vip_ref in vips:
        delete_vip(ctx, vip_ref)
    for server_ref in servers:
        remove_node_from_loadbalancer(ctx, sf_ref, server_ref)
    for probe_ref in probes:
        remove_probe_from_loadbalancer(ctx, sf_ref, probe_ref)
    for sticky_ref in stickies:
        delete_sticky(ctx, sticky_ref)
    delete_server_farm(ctx, sf_ref)


def add_node_to_loadbalancer(ctx, sf, rserver):
    create_rserver(ctx, rserver)
    add_rserver_to_server_farm(ctx, sf, rserver)


def remove_node_from_loadbalancer(ctx, sf, rserver):
    delete_rserver_from_server_farm(ctx, sf, rserver)
    delete_rserver(ctx, rserver)


def add_probe_to_loadbalancer(ctx, sf_ref, probe_ref):
    create_probe(ctx, probe_ref)
    add_probe_to_server_farm(ctx, sf_ref, probe_ref)


def remove_probe_from_loadbalancer(ctx, sf_ref, probe_ref):
    remove_probe_from_server_farm(ctx, sf_ref, probe_ref)
    delete_probe(ctx, probe_ref)


def add_sticky_to_loadbalancer(ctx, balancer, sticky):
    create_sticky(ctx, sticky)


def remove_sticky_from_loadbalancer(ctx, balancer, sticky):
    delete_sticky(ctx, sticky)

########NEW FILE########
__FILENAME__ = lb_status
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""Possible load balancer statuses."""

BUILD = "BUILD"
ACTIVE = "ACTIVE"
PENDING_UPDATE = "PENDING_UPDATE"
ERROR = "ERROR"

########NEW FILE########
__FILENAME__ = policy
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


import balancer.common.cfg


class PolicyConfig(balancer.common.cfg.ConfigOpts):
    def __init__(self, **kwargs):
        config_files = cfg.find_config_files(project='balancer',
                                             prog='balancer-policy')
        super(PolicyConfig, self).__init__(config_files, **kwargs)

########NEW FILE########
__FILENAME__ = scheduler
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
import logging

from balancer.db import api as db_api
from balancer import exception as exp
from balancer.common import cfg, utils
from balancer import drivers

LOG = logging.getLogger(__name__)

bind_opts = [
    cfg.ListOpt('device_filters',
        default=['balancer.core.scheduler.filter_capabilities']),
    cfg.ListOpt('device_cost_functions',
        default=['balancer.core.scheduler.lbs_on']),
]


def _process_config(conf):
    conf.register_opts(bind_opts)
    device_filters = [utils.import_class(foo) for foo in conf.device_filters]
    cost_functions = []
    for fullname in conf.device_cost_functions:
        conf_name = 'device_cost_%s_weight' % fullname.rpartition('.')[-1]
        try:
            weight = getattr(conf, conf_name)
        except cfg.NoSuchOptError:
            conf.register_opt(cfg.FloatOpt(conf_name, default=1.))
            weight = getattr(conf, conf_name)
        cost_functions.append((utils.import_class(fullname), weight))
    return device_filters, cost_functions


def _filter_devices(conf, lb_ref, devices, filters):
    filtered_devices = [device_ref for device_ref in devices
                            if all(filter(conf, lb_ref, device_ref)
                                   for filter in filters)]
    if not filtered_devices:
        raise exp.NoValidDevice
    return filtered_devices


def _weight_devices(conf, lb_ref, devices, cost_functions):
    weighted = []
    for device_ref in devices:
        weight = 0.0
        for cost_func, cost_weight in cost_functions:
            weight += cost_weight * cost_func(conf, lb_ref, device_ref)
        weighted.append((weight, device_ref))
    weighted.sort()
    return weighted


def schedule(conf, lb_ref):
    filters, cost_functions = _process_config(conf)
    devices = db_api.device_get_all(conf)
    if not devices:
        raise exp.DeviceNotFound
    filtered = _filter_devices(conf, lb_ref, devices, filters)
    weighted = _weight_devices(conf, lb_ref, filtered, cost_functions)
    return weighted[0][1]


def reschedule(conf, lb_ref):
    filters, cost_functions = _process_config(conf)
    device_ref = db_api.device_get(conf, lb_ref['device_id'])
    try:
        _filter_devices(conf, lb_ref, [device_ref], filters)
    except exp.NoValidDevice:
        devices = db_api.device_get_all(conf)
        devices = [dev_ref for dev_ref in devices
                       if dev_ref['id'] != device_ref['id']]
        filtered = _filter_devices(conf, lb_ref, devices, filters)
        weighted = _weight_devices(conf, lb_ref, filtered, cost_functions)
        return weighted[0][1]
    else:
        return device_ref


def filter_capabilities(conf, lb_ref, dev_ref):
    try:
        device_filter_capabilities = conf.device_filter_capabilities
    except cfg.NoSuchOptError:
        conf.register_opt(cfg.ListOpt('device_filter_capabilities',
                                      default=['algorithm']))
        device_filter_capabilities = conf.device_filter_capabilities
    device_driver = drivers.get_device_driver(conf, dev_ref['id'])
    capabilities = device_driver.get_capabilities()
    if capabilities is None:
        capabilities = {}
    for opt in device_filter_capabilities:
        lb_req = lb_ref.get(opt)
        if not lb_req:
            continue
        dev_caps = capabilities.get(opt + 's', [])
        if not (lb_req in dev_caps):
            LOG.debug('Device %s does not support %s "%s"', dev_ref['id'], opt,
                    lb_req)
            return False
    return True


def lbs_on(conf, lb_ref, dev_ref):
    return db_api.lb_count_active_by_device(conf, dev_ref['id'])

########NEW FILE########
__FILENAME__ = api
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""Database storage API."""

import functools
import datetime

from balancer.db import models
from balancer.db.session import get_session
from balancer import exception
from balancer.core import lb_status


# XXX(akscram): pack_ and unpack_ are helper methods to compatibility
def pack_extra(model, values):
    obj_ref = model()
    pack_update(obj_ref, values)
    return obj_ref


def unpack_extra(obj_ref):
    obj_dict = dict(obj_ref.iteritems())
    obj_dict.update(obj_dict.pop('extra', None) or {})
    return obj_dict


def pack_update(obj_ref, values):
    obj_dict = values.copy()
    for k, v in values.iteritems():
        if k in obj_ref.keys():
            obj_ref[k] = obj_dict.pop(k)
    if obj_dict:
        if obj_ref['extra'] is not None:
            obj_ref['extra'].update(obj_dict)
        else:
            obj_ref['extra'] = obj_dict.copy()


device_pack_extra = functools.partial(pack_extra, models.Device)
loadbalancer_pack_extra = functools.partial(pack_extra, models.LoadBalancer)
serverfarm_pack_extra = functools.partial(pack_extra, models.ServerFarm)
virtualserver_pack_extra = functools.partial(pack_extra, models.VirtualServer)
server_pack_extra = functools.partial(pack_extra, models.Server)
probe_pack_extra = functools.partial(pack_extra, models.Probe)
sticky_pack_extra = functools.partial(pack_extra, models.Sticky)
predictor_pack_extra = functools.partial(pack_extra, models.Predictor)

# Device


def device_get(conf, device_id, session=None):
    session = session or get_session(conf)
    device_ref = session.query(models.Device).\
                         filter_by(id=device_id).first()
    if not device_ref:
        raise exception.DeviceNotFound(device_id=device_id)
    return device_ref


def device_get_all(conf):
    session = get_session(conf)
    query = session.query(models.Device)
    return query.all()


def device_create(conf, values):
    session = get_session(conf)
    with session.begin():
        device_ref = models.Device()
        device_ref.update(values)
        session.add(device_ref)
        return device_ref


def device_update(conf, device_id, values):
    session = get_session(conf)
    with session.begin():
        device_ref = device_get(conf, device_id, session=session)
        device_ref.update(values)
        return device_ref


def device_destroy(conf, device_id):
    session = get_session(conf)
    with session.begin():
        device_ref = device_get(conf, device_id, session=session)
        session.delete(device_ref)

# LoadBalancer


def loadbalancer_get(conf, loadbalancer_id, tenant_id=None, session=None):
    session = session or get_session(conf)
    query = session.query(models.LoadBalancer).filter_by(id=loadbalancer_id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    loadbalancer_ref = query.first()
    if not loadbalancer_ref:
        raise exception.LoadBalancerNotFound(loadbalancer_id=loadbalancer_id)
    return loadbalancer_ref


def loadbalancer_get_all_by_project(conf, tenant_id):
    session = get_session(conf)
    query = session.query(models.LoadBalancer).filter_by(tenant_id=tenant_id)
    return query.all()


def loadbalancer_get_all_by_vm_id(conf, tenant_id, vm_id):
    session = get_session(conf)
    query = session.query(models.LoadBalancer).distinct().\
                    filter_by(tenant_id=tenant_id).\
                    filter(models.LoadBalancer.id ==
                           models.ServerFarm.lb_id).\
                    filter(models.Server.sf_id ==
                           models.ServerFarm.id).\
                    filter(models.Server.vm_id == vm_id)
    return query.all()


def loadbalancer_get_all_by_device_id(conf, device_id):
    session = get_session(conf)
    query = session.query(models.LoadBalancer).filter_by(device_id=device_id)
    lb_refs = query.all()
    if not lb_refs:
        raise exception.LoadBalancerNotFound('No loadbalancer '
                                             'for the device %s found'
                                             % device_id)
    return lb_refs


def loadbalancer_create(conf, values):
    session = get_session(conf)
    with session.begin():
        lb_ref = models.LoadBalancer()
        lb_ref.update(values)
        session.add(lb_ref)
        return lb_ref


def loadbalancer_update(conf, lb_id, values):
    session = get_session(conf)
    with session.begin():
        lb_ref = loadbalancer_get(conf, lb_id, session=session)
        lb_ref.update(values)
        lb_ref['updated_at'] = datetime.datetime.utcnow()
        return lb_ref


def loadbalancer_destroy(conf, lb_id):
    session = get_session(conf)
    with session.begin():
        lb_ref = loadbalancer_get(conf, lb_id, session=session)
        session.delete(lb_ref)


def lb_count_active_by_device(conf, device_id):
    session = get_session(conf)
    with session.begin():
        lbs_count = session.query(models.LoadBalancer).\
                                  filter_by(device_id=device_id).\
                                  filter_by(status=lb_status.ACTIVE).\
                                  count()
        return lbs_count


# Probe


def probe_get(conf, probe_id, tenant_id=None, session=None):
    session = session or get_session(conf)
    query = session.query(models.Probe).filter_by(id=probe_id)
    if tenant_id:
        query = query.filter(models.Probe.sf_id == models.ServerFarm.id).\
                  filter(models.LoadBalancer.id == models.ServerFarm.lb_id).\
                  filter(models.LoadBalancer.tenant_id == tenant_id)
    probe_ref = query.first()
    if not probe_ref:
        raise exception.ProbeNotFound(probe_id=probe_id)
    return probe_ref


def probe_get_all(conf):
    session = get_session(conf)
    query = session.query(models.Probe)
    return query.all()


def probe_get_all_by_sf_id(conf, sf_id):
    session = get_session(conf)
    query = session.query(models.Probe).filter_by(sf_id=sf_id)
    return query.all()


def probe_create(conf, values):
    session = get_session(conf)
    with session.begin():
        probe_ref = models.Probe()
        probe_ref.update(values)
        session.add(probe_ref)
        return probe_ref


def probe_update(conf, probe_id, values):
    session = get_session(conf)
    with session.begin():
        probe_ref = probe_get(conf, probe_id, session=session)
        probe_ref.update(values)
        return probe_ref


def probe_destroy(conf, probe_id):
    session = get_session(conf)
    with session.begin():
        probe_ref = probe_get(conf, probe_id, session=session)
        session.delete(probe_ref)


def probe_destroy_by_sf_id(conf, sf_id, session=None):
    session = session or get_session(conf)
    with session.begin():
        session.query(models.Probe).filter_by(sf_id=sf_id).delete()

# Sticky


def sticky_get(conf, sticky_id, tenant_id=None, session=None):
    session = session or get_session(conf)
    query = session.query(models.Sticky).filter_by(id=sticky_id)
    if tenant_id:
        query = query.filter(models.Sticky.sf_id == models.ServerFarm.id).\
                  filter(models.LoadBalancer.id == models.ServerFarm.lb_id).\
                  filter(models.LoadBalancer.tenant_id == tenant_id)
    sticky_ref = query.first()
    if not sticky_ref:
        raise exception.StickyNotFound(sticky_id=sticky_id)
    return sticky_ref


def sticky_get_all(conf):
    session = get_session(conf)
    query = session.query(models.Sticky)
    return query.all()


def sticky_get_all_by_sf_id(conf, sf_id):
    session = get_session(conf)
    query = session.query(models.Sticky).filter_by(sf_id=sf_id)
    return query.all()


def sticky_create(conf, values):
    session = get_session(conf)
    with session.begin():
        sticky_ref = models.Sticky()
        sticky_ref.update(values)
        session.add(sticky_ref)
        return sticky_ref


def sticky_update(conf, sticky_id, values):
    session = get_session(conf)
    with session.begin():
        sticky_ref = sticky_get(conf, sticky_id, session=session)
        sticky_ref.update(values)
        return sticky_ref


def sticky_destroy(conf, sticky_id):
    session = get_session(conf)
    with session.begin():
        sticky_ref = sticky_get(conf, sticky_id, session=session)
        session.delete(sticky_ref)


def sticky_destroy_by_sf_id(conf, sf_id, session=None):
    session = session or get_session(conf)
    with session.begin():
        session.query(models.Sticky).filter_by(sf_id=sf_id).delete()

# Server


def server_get(conf, server_id, lb_id=None, tenant_id=None, session=None):
    session = session or get_session(conf)
    query = session.query(models.Server).filter_by(id=server_id)
    if lb_id:
        query = query.filter(models.ServerFarm.lb_id == lb_id).\
                      filter(models.Server.sf_id == models.ServerFarm.id)
        if tenant_id:
            query = query.filter(models.LoadBalancer.id == lb_id).\
                          filter(models.LoadBalancer.tenant_id == tenant_id)
    elif tenant_id:
        query = query.filter(models.Server.sf_id == models.ServerFarm.id).\
                  filter(models.LoadBalancer.id == models.ServerFarm.lb_id).\
                  filter(models.LoadBalancer.tenant_id == tenant_id)
    server_ref = query.first()
    if not server_ref:
        raise exception.ServerNotFound(server_id=server_id)
    return server_ref


def server_get_all(conf):
    session = get_session(conf)
    query = session.query(models.Server)
    return query.all()


def server_get_by_address(conf, server_address):
    session = get_session(conf)
    server_ref = session.query(models.Server).\
                         filter_by(address=server_address).\
                         filter_by(deployed='True').first()
    if not server_ref:
        raise exception.ServerNotFound(server_address=server_address)
    return server_ref


def server_get_by_address_on_device(conf, server_address, device_id):
    session = get_session(conf)
    server_refs = session.query(models.Server).\
                         filter_by(address=server_address).\
                         filter_by(deployed='True')
    for server_ref in server_refs:
        sf = serverfarm_get(conf, server_ref['sf_id'], session=session)
        lb = loadbalancer_get(conf, sf['lb_id'])
        if device_id == lb['device_id']:
            return server_ref
    raise exception.ServerNotFound(server_address=server_address,
                                   device_id=device_id)


def server_get_all_by_parent_id(conf, parent_id):
    session = get_session(conf)
    query = session.query(models.Server).filter_by(parent_id=parent_id)
    return query.all()


def server_get_all_by_sf_id(conf, sf_id):
    session = get_session(conf)
    query = session.query(models.Server).filter_by(sf_id=sf_id)
    return query.all()


def server_create(conf, values):
    session = get_session(conf)
    with session.begin():
        server_ref = models.Server()
        server_ref.update(values)
        session.add(server_ref)
        return server_ref


def server_update(conf, server_id, values):
    session = get_session(conf)
    with session.begin():
        server_ref = server_get(conf, server_id, session=session)
        server_ref.update(values)
        return server_ref


def server_destroy(conf, server_id):
    session = get_session(conf)
    with session.begin():
        server_ref = server_get(conf, server_id, session=session)
        session.delete(server_ref)


def server_destroy_by_sf_id(conf, sf_id, session=None):
    session = session or get_session(conf)
    with session.begin():
        session.query(models.Server).filter_by(sf_id=sf_id).delete()

# ServerFarm


def serverfarm_get(conf, serverfarm_id, session=None):
    session = session or get_session(conf)
    serverfarm_ref = session.query(models.ServerFarm).\
                             filter_by(id=serverfarm_id).first()
    if not serverfarm_ref:
        raise exception.ServerFarmNotFound(serverfarm_id=serverfarm_id)
    return serverfarm_ref


def serverfarm_get_all_by_lb_id(conf, lb_id, tenant_id=None):
    session = get_session(conf)
    query = session.query(models.ServerFarm).filter_by(lb_id=lb_id)
    if tenant_id:
        query = query.filter(models.LoadBalancer.id == lb_id).\
                      filter(models.LoadBalancer.tenant_id == tenant_id)
    return query.all()


def serverfarm_create(conf, values):
    session = get_session(conf)
    with session.begin():
        serverfarm_ref = models.ServerFarm()
        serverfarm_ref.update(values)
        session.add(serverfarm_ref)
        return serverfarm_ref


def serverfarm_update(conf, serverfarm_id, values):
    session = get_session(conf)
    with session.begin():
        serverfarm_ref = serverfarm_get(conf, serverfarm_id, session=session)
        serverfarm_ref.update(values)
        return serverfarm_ref


def serverfarm_destroy(conf, serverfarm_id):
    session = get_session(conf)
    with session.begin():
        serverfarm_ref = serverfarm_get(conf, serverfarm_id, session=session)
        session.delete(serverfarm_ref)

# Predictor


def predictor_get(conf, predictor_id, session=None):
    session = session or get_session(conf)
    predictor_ref = session.query(models.Predictor).\
                            filter_by(id=predictor_id).first()
    if not predictor_ref:
        raise exception.PredictorNotFound(predictor_id=predictor_id)
    return predictor_ref


def predictor_get_by_sf_id(conf, sf_id):
    session = get_session(conf)
    predictor_ref = session.query(models.Predictor).\
                            filter_by(sf_id=sf_id).\
                            first()
    if not predictor_ref:
        raise exception.PredictorNotFound(sf_id=sf_id)
    return predictor_ref


def predictor_create(conf, values):
    session = get_session(conf)
    with session.begin():
        predictor_ref = models.Predictor()
        predictor_ref.update(values)
        session.add(predictor_ref)
        return predictor_ref


def predictor_update(conf, predictor_id, values):
    session = get_session(conf)
    with session.begin():
        predictor_ref = predictor_get(conf, predictor_id, session=session)
        predictor_ref.update(values)
        return predictor_ref


def predictor_destroy(conf, predictor_id):
    session = get_session(conf)
    with session.begin():
        predictor_ref = predictor_get(conf, predictor_id, session=session)
        session.delete(predictor_ref)


def predictor_destroy_by_sf_id(conf, sf_id, session=None):
    session = session or get_session(conf)
    with session.begin():
        session.query(models.Predictor).filter_by(sf_id=sf_id).delete()

# VirtualServer


def virtualserver_get(conf, vserver_id, tenant_id=None, session=None):
    session = session or get_session(conf)
    query = session.query(models.VirtualServer).filter_by(id=vserver_id)
    if tenant_id:
        query = query.\
                  filter(models.VirtualServer.sf_id == models.ServerFarm.id).\
                  filter(models.LoadBalancer.id == models.ServerFarm.lb_id).\
                  filter(models.LoadBalancer.tenant_id == tenant_id)
    vserver_ref = query.first()
    if not vserver_ref:
        raise exception.VirtualServerNotFound(virtualserver_id=vserver_id)
    return vserver_ref


def virtualserver_get_all_by_sf_id(conf, sf_id):
    session = get_session(conf)
    query = session.query(models.VirtualServer).filter_by(sf_id=sf_id)
    return query.all()


def virtualserver_get_all_by_lb_id(conf, lb_id, tenant_id=None):
    session = get_session(conf)
    query = session.query(models.VirtualServer).\
                  filter(models.ServerFarm.lb_id == lb_id).\
                  filter_by(sf_id=models.ServerFarm.id)
    if tenant_id:
        query = query.\
                  filter(models.LoadBalancer.id == models.ServerFarm.lb_id).\
                  filter(models.LoadBalancer.tenant_id == tenant_id)
    vips = query.all()
    return vips


def virtualserver_create(conf, values):
    session = get_session(conf)
    with session.begin():
        vserver_ref = models.VirtualServer()
        vserver_ref.update(values)
        session.add(vserver_ref)
        return vserver_ref


def virtualserver_update(conf, vserver_id, values):
    session = get_session(conf)
    with session.begin():
        vserver_ref = virtualserver_get(conf, vserver_id, session=session)
        vserver_ref.update(values)
        return vserver_ref


def virtualserver_destroy(conf, vserver_id):
    session = get_session(conf)
    with session.begin():
        vserver_ref = virtualserver_get(conf, vserver_id, session=session)
        session.delete(vserver_ref)


def virtualserver_destroy_by_sf_id(conf, sf_id, session=None):
    session = session or get_session(conf)
    with session.begin():
        session.query(models.VirtualServer).filter_by(sf_id=sf_id).delete()

########NEW FILE########
__FILENAME__ = base
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""Base classes and custome fields for balancer models."""

import json

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import object_mapper
from sqlalchemy.types import TypeDecorator
from sqlalchemy import Text


Base = declarative_base()


class DictBase(object):
    def to_dict(self):
        return dict(self.iteritems())

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __iter__(self):
        return (col.name for col in object_mapper(self).columns)

    def keys(self):
        return list(self)

    def update(self, values):
        for key, value in values.iteritems():
            if isinstance(value, dict):
                value = value.copy()
            setattr(self, key, value)

    def iteritems(self):
        items = []
        for key in self:
            value = getattr(self,  key)
            if isinstance(value, dict):
                value = value.copy()
            items.append((key, value))
        return iter(items)


class JsonBlob(TypeDecorator):

    impl = Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from migrate.versioning.shell import main

if __name__ == '__main__':
    main(debug='False')

########NEW FILE########
__FILENAME__ = 001_Add_initial_tables
from sqlalchemy.schema import MetaData, Table, Column, ForeignKey
from sqlalchemy.types import Integer, String, Text, DateTime


meta = MetaData()

Table('device', meta,
    Column('id', String(32), primary_key=True),
    Column('name', String(255)),
    Column('type', String(255)),
    Column('version', String(255)),
    Column('ip', String(255)),
    Column('port', Integer),
    Column('user', String(255)),
    Column('password', String(255)),
    Column('extra', Text()),
)

Table('loadbalancer', meta,
    Column('id', String(32), primary_key=True),
    Column('device_id', String(32), ForeignKey('device.id')),
    Column('name', String(255)),
    Column('algorithm', String(255)),
    Column('protocol', String(255)),
    Column('status', String(255)),
    Column('tenant_id', String(255)),
    Column('created_at', DateTime, nullable=False),
    Column('updated_at', DateTime, nullable=False),
    Column('deployed', String(40)),
    Column('extra', Text()),
)

Table('serverfarm', meta,
    Column('id', String(32), primary_key=True),
    Column('lb_id', String(32), ForeignKey('loadbalancer.id')),
    Column('name', String(255)),
    Column('type', String(255)),
    Column('status', String(255)),
    Column('deployed', String(40)),
    Column('extra', Text()),
)

Table('virtualserver', meta,
    Column('id', String(32), primary_key=True),
    Column('sf_id', String(32), ForeignKey('serverfarm.id')),
    Column('lb_id', String(32), ForeignKey('loadbalancer.id')),
    Column('name', String(255)),
    Column('address', String(255)),
    Column('mask', String(255)),
    Column('port', String(255)),
    Column('status', String(255)),
    Column('deployed', String(40)),
    Column('extra', Text()),
)

Table('server', meta,
    Column('id', String(32), primary_key=True),
    Column('sf_id', String(32), ForeignKey('serverfarm.id')),
    Column('name', String(255)),
    Column('type', String(255)),
    Column('address', String(255)),
    Column('port', String(255)),
    Column('weight', Integer),
    Column('status', String(255)),
    Column('parent_id', Integer),
    Column('deployed', String(40)),
    Column('vm_id', Integer),
    Column('extra', Text()),
)

Table('probe', meta,
    Column('id', String(32), primary_key=True),
    Column('sf_id', String(32), ForeignKey('serverfarm.id')),
    Column('name', String(255)),
    Column('type', String(255)),
    Column('deployed', String(40)),
    Column('extra', Text()),
)

Table('sticky', meta,
    Column('id', String(32), primary_key=True),
    Column('sf_id', String(32), ForeignKey('serverfarm.id')),
    Column('name', String(255)),
    Column('type', String(255)),
    Column('deployed', String(40)),
    Column('extra', Text()),
)

Table('predictor', meta,
    Column('id', String(32), primary_key=True),
    Column('sf_id', String(32), ForeignKey('serverfarm.id')),
    Column('type', String(255)),
    Column('deployed', String(40)),
    Column('extra', Text()),
)


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    meta.create_all()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    meta.drop_all()

########NEW FILE########
__FILENAME__ = models
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""SQLAlchemy models for balancer data."""

import datetime
import uuid

from sqlalchemy.orm import relationship, backref
from sqlalchemy import (Column, ForeignKey, Integer, String, Boolean,
                        DateTime)

from balancer.db.base import Base, DictBase, JsonBlob


def create_uuid():
    return uuid.uuid4().hex


class Device(DictBase, Base):
    """
    Represents a load balancer appliance - a physical device (like F5 BigIP) or
    a software system (such as HAProxy) that can perform load balancing
    functions
    """

    __tablename__ = 'device'
    id = Column(String(32), primary_key=True, default=create_uuid)
    name = Column(String(255))
    type = Column(String(255))
    version = Column(String(255))
    ip = Column(String(255))
    port = Column(Integer)
    user = Column(String(255))
    password = Column(String(255))
    extra = Column(JsonBlob())


class LoadBalancer(DictBase, Base):
    """
    Represents an instance of load balancer appliance for a tenant.
    This is a subsystem behind a virtual IP, i.e. the VIP itself,
    the load balancer instance serving this particular VIP,
    the server farm behind it, and the health probes.

    :var name: string
    :var algorithm: string - load balancing algorithm (e.g. RoundRobin)
    :var protocol: string - load balancing protocol (e.g. TCP, HTTP)
    :var tenant_id: string - OpenStack tenant ID
    :var extra: dictionary - additional attributes
    """

    __tablename__ = 'loadbalancer'
    id = Column(String(32), primary_key=True, default=create_uuid)
    device_id = Column(String(32), ForeignKey('device.id'))
    name = Column(String(255))
    algorithm = Column(String(255))
    protocol = Column(String(255))
    status = Column(String(255))
    tenant_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow,
                        nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow,
                        nullable=False)
    deployed = Column(String(40))
    extra = Column(JsonBlob())

    device = relationship(Device,
                          backref=backref('loadbalancers', order_by=id),
                          uselist=False)


class ServerFarm(DictBase, Base):
    """
    Represents a server farm - a set of servers providing the same backend
    application, managed by a single LB pool.

    :var name: string
    :var extra: dictionary - additional attributes
    """

    __tablename__ = 'serverfarm'
    id = Column(String(32), primary_key=True, default=create_uuid)
    lb_id = Column(String(32), ForeignKey('loadbalancer.id'))
    name = Column(String(255))
    type = Column(String(255))
    status = Column(String(255))
    deployed = Column(String(40))
    extra = Column(JsonBlob())

    loadbalancer = relationship(LoadBalancer,
                                backref=backref('serverfarms', order_by=id),
                                uselist=False)


class VirtualServer(DictBase, Base):
    """
    Represents a Virtual IP - an IP address on which the LB Appliance listens
    to traffic from clients. This is the address seen by the clients.
    Client requests to this IP are routed by the load balancer to backend
    application instances.

    :var name: string
    :var address: string - IP address of VIP to accept traffic
    :var mask: string - network mask
    :var port: string - tcp port
    :var extra: dictionary - additional attributes
    """

    __tablename__ = 'virtualserver'
    id = Column(String(32), primary_key=True, default=create_uuid)
    sf_id = Column(String(32), ForeignKey('serverfarm.id'))
    lb_id = Column(String(32), ForeignKey('loadbalancer.id'))
    name = Column(String(255))
    address = Column(String(255))
    mask = Column(String(255))
    port = Column(String(255))
    status = Column(String(255))
    deployed = Column(String(40))
    extra = Column(JsonBlob())

    serverfarm = relationship(ServerFarm,
                              backref=backref('virtualservers', order_by=id),
                              uselist=False)
    loadbalancer = relationship(LoadBalancer,
                                backref=backref('loadbalancers', order_by=id),
                                uselist=False)


class Server(DictBase, Base):
    """
    Represents a real server (Node) - a single server providing a single
    backend application instance.

    :var name: string
    :var type: string (not used!)
    :var address: string - IPv4 or IPv6 Address of the node
    :var port: string - application port on which the node listens
    :var weight: integer - weight of the node with respect to other nodes in \
    the same SF. Semantics of weight depends on the particular balancer \
    algorithm
    :var status: string - current health status of the node
    :var extra: dictionary - additional attributes
    """

    __tablename__ = 'server'
    id = Column(String(32), primary_key=True, default=create_uuid)
    sf_id = Column(String(32), ForeignKey('serverfarm.id'))
    name = Column(String(255))
    type = Column(String(255))
    address = Column(String(255))
    port = Column(String(255))
    weight = Column(Integer)
    status = Column(String(255))
    parent_id = Column(Integer)
    deployed = Column(String(40))
    vm_id = Column(Integer)
    extra = Column(JsonBlob())

    serverfarm = relationship(ServerFarm,
                              backref=backref('servers', order_by=id),
                              uselist=False)


class Probe(DictBase, Base):
    """
    Represents a health monitoring. The probe can be implemented by ICMP ping,
    or more sophisticated way, like sending HTTP GET to specified URL

    :var type: string - type of probe (HTTP, HTTPS, ICMP, CONNECT, etc.) \
    - real set depends on driver support
    :var extra: dictionary - additional attributes
    """

    __tablename__ = 'probe'
    id = Column(String(32), primary_key=True, default=create_uuid)
    sf_id = Column(String(32), ForeignKey('serverfarm.id'))
    name = Column(String(255))
    type = Column(String(255))
    deployed = Column(String(40))
    extra = Column(JsonBlob())

    serverfarm = relationship(ServerFarm,
                              backref=backref('probes', order_by=id),
                              uselist=False)


class Sticky(DictBase, Base):
    """
    Represents a persistent session.
    """

    __tablename__ = 'sticky'
    id = Column(String(32), primary_key=True, default=create_uuid)
    sf_id = Column(String(32), ForeignKey('serverfarm.id'))
    name = Column(String(255))
    type = Column(String(255))
    deployed = Column(String(40))
    extra = Column(JsonBlob())

    serverfarm = relationship(ServerFarm,
                              backref=backref('stickies', order_by=id),
                              uselist=False)


class Predictor(DictBase, Base):
    """
    Represents an algorithm of selecting server by load balancer.

    :var type: string - the algorithm, e.g. RoundRobin
    """

    __tablename__ = 'predictor'
    id = Column(String(32), primary_key=True, default=create_uuid)
    sf_id = Column(String(32), ForeignKey('serverfarm.id'))
    type = Column(String(255))
    deployed = Column(String(40))
    extra = Column(JsonBlob())

    serverfarm = relationship(ServerFarm,
                              backref=backref('predictors', order_by=id),
                              uselist=False)


def register_models(engine):
    """Create tables for models."""

    Base.metadata.create_all(engine)

########NEW FILE########
__FILENAME__ = session
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""Session management functions."""

import os
import logging

from migrate.versioning import api as versioning_api
from migrate import exceptions as versioning_exceptions
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import DisconnectionError

from balancer.common import cfg
from balancer.db import migrate_repo


DB_GROUP_NAME = 'sql'
DB_OPTIONS = (
    cfg.IntOpt('idle_timeout', default=3600),
    cfg.StrOpt('connection', default='sqlite:///balancer.sqlite'),
)

MAKER = None
ENGINE = None


class MySQLPingListener(object):
    """
    Ensures that MySQL connections checked out of the
    pool are alive.

    Borrowed from:
    http://groups.google.com/group/sqlalchemy/msg/a4ce563d802c929f

    Error codes caught:
    * 2006 MySQL server has gone away
    * 2013 Lost connection to MySQL server during query
    * 2014 Commands out of sync; you can't run this command now
    * 2045 Can't open shared memory; no answer from server (%lu)
    * 2055 Lost connection to MySQL server at '%s', system error: %d

    from http://dev.mysql.com/doc/refman/5.6/en/error-messages-client.html
    """

    def checkout(self, dbapi_con, con_record, con_proxy):
        try:
            dbapi_con.cursor().execute('select 1')
        except dbapi_con.OperationalError, ex:
            if ex.args[0] in (2006, 2013, 2014, 2045, 2055):
                logging.warn('Got mysql server has gone away: %s', ex)
                raise DisconnectionError("Database server went away")
            else:
                raise


def get_session(conf, autocommit=True, expire_on_commit=False):
    """Return a SQLAlchemy session."""
    global MAKER

    if MAKER is None:
        MAKER = sessionmaker(autocommit=autocommit,
                             expire_on_commit=expire_on_commit)
    engine = get_engine(conf)
    MAKER.configure(bind=engine)
    session = MAKER()
    return session


def get_engine(conf):
    """Return a SQLAlchemy engine."""
    global ENGINE

    register_conf_opts(conf)
    connection_url = make_url(conf.sql.connection)
    if ENGINE is None or not ENGINE.url == connection_url:
        engine_args = {'pool_recycle': conf.sql.idle_timeout,
                       'echo': False,
                       'convert_unicode': True
                       }
        if 'sqlite' in connection_url.drivername:
            engine_args['poolclass'] = NullPool
        if 'mysql' in connection_url.drivername:
            engine_args['listeners'] = [MySQLPingListener()]
        ENGINE = create_engine(conf.sql.connection, **engine_args)
    return ENGINE


def register_conf_opts(conf, options=DB_OPTIONS, group=DB_GROUP_NAME):
    """Register database options."""

    conf.register_group(cfg.OptGroup(name=group))
    conf.register_opts(options, group=group)


def sync(conf):
    register_conf_opts(conf)
    repo_path = os.path.abspath(os.path.dirname(migrate_repo.__file__))
    try:
        versioning_api.upgrade(conf.sql.connection, repo_path)
    except versioning_exceptions.DatabaseNotControlledError:
        versioning_api.version_control(conf.sql.connection, repo_path)
        versioning_api.upgrade(conf.sql.connection, repo_path)

########NEW FILE########
__FILENAME__ = ANMDriver
import logging

from balancer.drivers.cisco_ace.Context import Context
from balancer.drivers.base_driver import is_sequence
from balancer.drivers.cisco_ace.ace_5x_driver import AceDriver

from suds.client import Client

logger = logging.getLogger(__name__)


class ANMSpecificContext(Context):
    def __init__(self, ip, port, login, password, contextName):
        super(ANMSpecificContext, self).__init__(ip, port, login, password)
        self.contextName = contextName
        self.templateInstances = {}


class ANMDriver(AceDriver):
    def __init__(self, anmIp, anmLogin, anmPassword):
        super(ANMDriver, self).__init__()
        self.anmIp = anmIp
        self.anmLogin = anmLogin
        self.anmPassword = anmPassword
        self.operationClient = Client(
            "http://%s:8080/anm/OperationManager?wsdl" % self.anmIp)
        self.templateClient = Client(
            "http://%s:8080/anm/ApplicationTemplateManager?wsdl" % self.anmIp)

    def getContext(self,  dev):
        logger.debug("Creating context with params: IP %s, Port: %s",
                dev.ip, dev.port)
        return ANMSpecificContext(dev.ip, dev.port, dev.user, dev.password,
                    "dmitryme")

######## Work Methods
######## Commented out methods are inherited

#   def createRServer(self,  context,  rserver):

#   def deleteRServer(self,  context,  rserver):

#    def activateRServer(self,  context,  serverfarm,  rserver):
#        sid = self.login()
#        try:
#            deviceId = self.createSudsDeviceID(context)
#            sfRServer = self.createSudsServerFarmRServer(serverfarm, rserver)
#            self.operationClient.service.activateServerfarmRserver(sid,
#                deviceId, sfRServer, "OpenstackLB wants this rserver up!")
#        finally:
#            self.logout(sid)

#    def suspendRServer(self,  context,  serverfarm,  rserver):
#        sid = self.login()
#        try:
#            deviceId = self.createSudsDeviceID(context)
#            sfRServer = self.createSudsServerFarmRServer(serverfarm, rserver)
#            self.operationClient.service.suspendServerfarmRserver(sid,
#                deviceId, sfRServer, "Suspend",
#                "OpenstackLB wants this rserver down!")
#        finally:
#            self.logout(sid)

#    def createProbe(self,  context,  probe):
#        raise NotImplementedError("ANM Driver can not create probes")

#    def deleteProbe(self,  context,  probe):
#        raise NotImplementedError("ANM Driver can not delete probes")

#   def createServerFarm(self,  context,  serverfarm):

#   def deleteServerFarm(self,  context,  serverfarm):

    # backup-rserver is not supported
#    def addRServerToSF(self,  context,  serverfarm,  rserver):
#        sid = self.login()
#        try:
#            deviceId = self.createSudsDeviceID(context)
#            rServer = self.createSudsRServer(rserver)
#            port = 0
#            if hasattr(rserver, 'port'):
#                port = rserver.port
#            self.operationClient.service.addRserverToServerfarm(sid, deviceId,
#                serverfarm.name, rServer, port)
#        finally:
#            self.logout(sid)

#    def deleteRServerFromSF(self, context,  serverfarm,  rserver):
#        sid = self.login()
#        try:
#            deviceId = self.createSudsDeviceID(context)
#            sfRServer = self.createSudsServerFarmRServer(serverfarm, rserver)
#            self.operationClient.service.removeRserverFromServerfarm(sid,
#                deviceId, sfRServer)
#        finally:
#            self.logout(sid)

#    def addProbeToSF(self,  context,  serverfarm,  probe):
#        raise NotImplementedError(
#            "ANM Driver can not add probes to server farm")

 #   def deleteProbeFromSF(self,  context,  serverfarm,  probe):
 #       raise NotImplementedError(
#            "ANM Driver can not delete probes from server farm")

    def create_stickiness(self, sticky):
        raise NotImplementedError("ANM Driver can not enable stickness")

    def delete_stickiness(self, sticky):
        raise NotImplementedError("ANM Driver can not disable stickness")

    def createVIP(self,  context,  vip,  sfarm):
        values = {}
        values["service"] = {}
        values["network"] = {}
        values["service"]["name"] = vip.name
        values["service"]["vip"] = vip.address
        values["service"]["port"] = vip.port
        values["service"]["sfarm_name"] = sfarm.name
        if hasattr(vip, 'backupServerFarm') and vip.backupServerFarm != "":
            values["service"]["use_backup_sfarm"] = "true"
            values["service"]["backup_sfarm_name"] = vip.backupServerFarm
        else:
            values["service"]["use_backup_sfarm"] = "false"
            values["service"]["backup_sfarm_name"] = ""

        values["service"]["sticky"] = "false"

        values["network"]["device"] = ""
        if self.checkNone(vip.allVLANs):
            values["network"]["vlans"] = "ALL_VLAN"
        elif is_sequence(vip.VLAN):
            values["network"]["vlans"] = ",".join(vip.VLAN)
        else:
            values["network"]["vlans"] = vip.VLAN
        values["network"]["autoNat"] = "true"

        sid = self.login()
        try:
            definition = self.fetchTemplateDefinition(sid,
                    "OpenstackLB-Basic-HTTP-adv")
            inputs = self.fetchTemplateImputs(sid, definition)
            self.fillTemplateInputs(inputs, values)
            deviceId = self.createSudsDeviceID(context)
            instance = self.templateClient.service.createTemplateInstance(sid,
                    deviceId, definition, inputs)
            context.templateInstances[vip.name] = instance
        finally:
            self.logout(sid)

    def deleteVIP(self,  context,  vip):
        sid = self.login()
        try:
            instance = context.templateInstances[vip.name]
            deviceId = self.createSudsDeviceID(context)
            self.templateClient.service.deleteTemplateInstance(sid, deviceId,
                    instance)
        finally:
            self.logout(sid)

######## Utilities
    def login(self):
        return self.operationClient.service.login(self.anmLogin,
                self.anmPassword)

    def logout(self, sid):
        self.operationClient.service.logout(sid)

    def createSudsDeviceID(self, context):
        deviceId = self.operationClient.factory.create('DeviceID')
        deviceId.name = context.contextName
        deviceId.ipAddr = context.ip
        deviceId.deviceType.value = "VIRTUAL_CONTEXT"
        return deviceId

    def createSudsServerFarmRServer(self, serverfarm, rserver):
        sfRServer = self.operationClient.factory.create('SfRserver')
        sfRServer.serverfarmName = serverfarm.name
        sfRServer.realserverName = rserver.name
        sfRServer.adminState.value = "IS"
        if hasattr(rserver, "port"):
            sfRServer.port = rserver.port
        else:
            sfRServer.port = 0

        if hasattr(rserver, "weight"):
            sfRServer.weight = rserver.weight
        else:
            sfRServer.weight = 8

        return sfRServer

    def createSudsRServer(self, rserver):
        rServer = self.operationClient.factory.create('Rserver')
        rServer.name = rserver.name
        if hasattr(rserver, 'state'):
            if rserver.state.lower() == "inservice":
                rServer.state = "IS"
            elif rserver.state.lower() == "standby":
                rServer.state = "ISS"
            else:
                rServer.state = "OOS"
        else:
            rServer.state = "IS"

        if hasattr(rserver, "weight"):
            rServer.weight = rserver.weight
        else:
            rServer.weight = 8

        return rServer

    def fetchTemplateDefinition(self, sid, templateName):
        listOfDefs = self.templateClient.service.listTemplateDefinitions(sid)
        for definition in listOfDefs['item']:
            if definition.name == templateName:
                return definition
        raise RuntimeError("No such template found: %s" % templateName)

    def fetchTemplateImputs(self, sid, templateDefinition):
        return self.templateClient.service.getTemplateDefinitionMetadata(sid,
                templateDefinition)

    def fillTemplateInputs(self, templateInputs, values):
        for inputGroup in templateInputs['item']:
            if inputGroup.name in values:
                self.fillTemplateGroupInputs(inputGroup, inputGroup.name,
                        values[inputGroup.name])
            else:
                print "Ops, don't have group %s in values" % inputGroup.name

    def fillTemplateGroupInputs(self, element, groupName, mapping):
        if not hasattr(element, 'childElements'):
            return
        for inp in element.childElements:
            if hasattr(inp, 'name'):
                if inp.name in mapping:
                    inp.userData = mapping[inp.name]
                else:
                    print "Ops, don't have value for group %s, input %s" % (
                                                        groupName, inp.name)
            self.fillTemplateGroupInputs(inp, groupName, mapping)



#values = {}
#values["service"] = {}
#values["network"] = {}
#values["service"]["name"] = "OpenstackLB-app"
#values["service"]["vip"] = "10.4.15.33"
#values["service"]["port"] = "110"
#values["service"]["sfarm_name"] = "sftest"
#values["service"]["use_backup_sfarm"] = "true"
#values["service"]["backup_sfarm_name"] = "sftest-backup"
#values["service"]["sticky"] = "false"

#values["network"]["device"] = "ace30:dmitryme"
#values["network"]["vlans"] = "2"
#values["network"]["autoNat"] = "true"

########NEW FILE########
__FILENAME__ = base_driver
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
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
from balancer.core import commands


class DeviceRequestContext(commands.RollbackContext):
    def __init__(self, conf, device):
        super(DeviceRequestContext, self).__init__()
        self.conf = conf
        self.device = device


class BaseDriver(object):
    def __init__(self, conf, device_ref):
        self.conf = conf
        self.device_ref = device_ref

    def request_context(self):
        return commands.RollbackContextManager(
                DeviceRequestContext(self.conf, self))

    def checkNone(self, obj):
        if bool(obj):
            if obj != 'None':
                return True
        return False

    def import_certificate_or_key(self):
        """
        not used in API
        """
        raise NotImplementedError

    def create_ssl_proxy(self, ssl_proxy):
        """
        not used in API
        """
        raise NotImplementedError

    def delete_ssl_proxy(self, ssl_proxy):
        """
        not used in API
        """
        raise NotImplementedError

    def add_ssl_proxy_to_virtual_ip(self, vip, ssl_proxy):
        """
        not used in API
        """
        raise NotImplementedError

    def remove_ssl_proxy_from_virtual_ip(self, vip, ssl_proxy):
        """
        not used in API
        """
        raise NotImplementedError

    def create_real_server(self, rserver):
        """
        Create a new real server (node)

        :param rserver: Server \
         - see :py:class:`balancer.db.models.Server`
        """
        raise NotImplementedError

    def delete_real_server(self, rserver):
        """
        Delete real server (node)

        :param rserver: Server \
         - see :py:class:`balancer.db.models.Server`
        """
        raise NotImplementedError

    def activate_real_server(self, serverfarm, rserver):
        """
        Put node into active state (activate)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        raise NotImplementedError

    def activate_real_server_global(self, rserver):
        """
        not used in API. deprecated
        """
        raise NotImplementedError

    def suspend_real_server(self, serverfarm, rserver):
        """
        Put node into inactive state (suspend)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        raise NotImplementedError

    def suspend_real_server_global(self, rserver):
        """
        not used in API. deprecated
        """
        raise NotImplementedError

    def create_probe(self, probe):
        """
        Create probe for health monitoring

        :param probe: Probe \
        - see :py:class:`balancer.db.models.Probe`
        :return:
        """
        raise NotImplementedError

    def delete_probe(self, probe):
        """
        Delete probe

        :param probe: Probe \
        - see :py:class:`balancer.db.models.Probe`
        :return:
        """
        raise NotImplementedError

    def create_server_farm(self, serverfarm, predictor):
        """
        Create a new loadbalancer (server farm)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param predictor: Predictor \
        - see :py:class:`balancer.db.models.Predictor`
        """
        raise NotImplementedError

    def delete_server_farm(self, serverfarm):
        """
        Delete a load balancer (server farm)
        """
        raise NotImplementedError

    def add_real_server_to_server_farm(self, serverfarm, rserver):
        """
        Add a node (rserver) into load balancer (serverfarm)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        raise NotImplementedError

    def delete_real_server_from_server_farm(self, serverfarm, rserver):
        """
        Delete node (rserver) from the specified loadbalancer (serverfarm)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        raise NotImplementedError

    def add_probe_to_server_farm(self, serverfarm, probe):
        """
        Add a probe into server farm

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param probe: Probe \
        - see :py:class:`balancer.db.models.Probe`
        """
        raise NotImplementedError

    def delete_probe_from_server_farm(self, serverfarm, probe):
        """
        Delete probe from server farm

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param probe: Probe \
        - see :py:class:`balancer.db.models.Probe`
        """
        raise NotImplementedError

    def create_stickiness(self, sticky):
        """
        Create a new stickiness object

        :param sticky: Sticky \
         - see :py:class:`balancer.db.models.Sticky`
        """
        raise NotImplementedError

    def delete_stickiness(self, sticky):
        """
        Delete a stickiness object

        :param sticky: Sticky \
         - see :py:class:`balancer.db.models.Sticky`
        """
        raise NotImplementedError

    def create_virtual_ip(self, vip, serverfarm):
        """
        Create a new vip (virtual IP)

        :param virtualserver: VirtualServer \
        - see :py:class:`balancer.db.models.VirtualServer`
        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        """
        raise NotImplementedError

    def delete_virtual_ip(self, vip):
        """
        Delete vip from loadbalancer

        :param virtualserver: VirtualServer \
        - see :py:class:`balancer.db.models.VirtualServer`
        """
        raise NotImplementedError

    def get_statistics(self, serverfarm, rserver):
        raise NotImplementedError

    def get_capabilities(self):
        try:
            return self.device_ref['extra'].get('capabilities')
        except KeyError, TypeError:
            return None


def is_sequence(arg):
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))

########NEW FILE########
__FILENAME__ = ace_driver
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
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

from hashlib import md5
import urllib2
import base64
import logging
import ipaddr
from balancer.drivers.base_driver import BaseDriver
from balancer.drivers.base_driver import is_sequence


LOG = logging.getLogger(__name__)

ALGORITHMS_MAPPING = {
    'ROUND_ROBIN': 'roundrobin',
    'RESPONSE': 'response',
    'LEAST_CONNECTION': 'leastconnections',
    'LEAST_BANDWIDTH': 'leastbandwidth',
    'LEAST_LOADED': 'leastloaded',
    'HASH_ADDRESS': 'hash address',
    'HASH_URL': 'hash url',
    'HASH_COOKIE': 'hash cookie',
    'HASH_CONTENT': 'hash content',
    'HASH_HEADER': 'hash header',
    'HASH_LAYER4_PAYLOAD': 'hash layer4-payload',
}


class AceDriver(BaseDriver):

    """
    This is the driver for Cisco ACE (cisco.com)
    """

    algorithms = ALGORITHMS_MAPPING
    default_algorithm = ALGORITHMS_MAPPING['ROUND_ROBIN']

    def __init__(self,  conf,  device_ref):
        #super(AceDriver, self).__init__(conf, device_ref) ???
        url = "https://%s:%s/bin/xml_agent" % (device_ref['ip'], \
                                               device_ref['port'])
        base64str = base64.encodestring('%s:%s' % \
            (device_ref['user'], device_ref['password']))[:-1]
        authheader = "Basic %s" % base64str
        self.request = urllib2.Request(url).add_header("Authorization", \
                                                               authheader)

    def deployConfig(self, s):
        data = 'xml_cmd=<request_raw>\nconfigure\n%s\nend\n</request_raw>' % s
        LOG.debug('send data to ACE:\n' + data)
        try:
            response = urllib2.urlopen(self.request, data).read()
        except Exception:
            raise
        LOG.debug('data from ACE:\n' + response)
        if 'XML_CMD_SUCCESS' in response:
            return 'OK'
        return 'Error'

    def getConfig(self, s):
        data = 'xml_cmd=<request_raw>\nshow runn %s\n</request_raw>' % s
        LOG.debug('send data to ACE:\n' + data)
        try:
            response = urllib2.urlopen(self.request, data).read()
        except Exception:
            raise
        LOG.debug("data from ACE:\n" + response)
        return response

    def get_statistics(self, server_farm):
        # TODO: Need to check work of this function with real device
        data = 'xml_cmd=<request_raw>\nshow serverfarm %s' % server_farm['id']
        data += '\n</request_raw>'
        try:
            response = urllib2.urlopen(self.request, data).read()
        except Exception:
            raise
        LOG.debug("data from ACE:\n" + response)
        return response

    def create_nat_pool(self, nat_pool):
        cmd = "int vlan " + str(nat_pool['vlan']) + \
            "\nnat-pool " + str(nat_pool['id']) + " %s" % nat_pool['ip1']
        if nat_pool.get('ip2'):
            cmd += " " + nat_pool['ip2']
        cmd += " " + nat_pool['netmask']
        if nat_pool.get('pat'):
            cmd += " pat"
        self.deployConfig(cmd)

    def delete_nat_pool(self, nat_pool):
        cmd = "int vlan " + nat_pool['vlan'] + "\nno nat-pool " + \
              nat_pool['id']
        self.deployConfig(cmd)

    def add_nat_pool_to_vip(self, nat_pool, vip):
        cmd = "policy-map multi-match "
        vip_extra = vip.get('extra') or {}
        if vip_extra.get('allVLANs'):
            cmd += "global"
        else:
            cmd += "int-" + str(md5(vip_extra['VLAN']).hexdigest())
        cmd += "\nclass " + vip['id'] + \
               "\nnat dynamic " + str(nat_pool['id']) + \
               " vlan " + str(nat_pool['vlan'])
        self.deployConfig(cmd)

    def delete_nat_pool_from_vip(self, nat_pool, vip):
        cmd = "policy-map multi-match "
        vip_extra = vip.get('extra') or {}
        if vip_extra.get('allVLANs'):
            cmd += "global"
        else:
            cmd += "int-" + str(md5(vip_extra['VLAN']).hexdigest())
        cmd += "\nclass " + vip['id'] + \
               "\nno nat dynamic " + nat_pool['number'] + \
               " vlan " + nat_pool['vlan']
        self.deployConfig(cmd)

    def get_nat_pools(self):
        vlan_interfaces = self.getConfig("| i interface vlan").split('\n')
        result = []
        for vlan in vlan_interfaces:
            s = self.getConfig("int vlan %s | i nat-pool" % vlan).split('\n')
            for f in s:
                f = f.split()
            r = []
            for w in f:
                if len(w) > 4:
                    r.append(w)
            if len(r) > 0:
                res = {}
                res['vlan'] = vlan[-1]
                res['id'] = r[0]
                res['ip1'] = r[1]
                if len(r) > 3:
                    res['ip2'] = r[2]
                    res['netmask'] = r[3]
                else:
                    res['ip2'] = r[1]
                    res['netmask'] = r[2]
                result.append(res)
        return result

    def find_nat_pool_for_vip(self, vip):
        if '4' in vip.get('ipVersion'):
            ip = ipaddr.IPv4Address(vip['address'])
            network = ipaddr.IPv4Network(vip['address'] + "/" + vip['mask'])
        else:
            ip = ipaddr.IPv6Address(vip['address'])
            network = ipaddr.IPv6Network(vip['address'] + "/" + vip['mask'])
        nat_pools = self.get_nat_pools()
        for nat_pool in nat_pools:
            if (nat_pool['ip1'] in network.iterhosts() and
                nat_pool['ip2'] in network.iterhosst()):
                ip = nat_pool['ip1']
                network_nat = ipaddr.ip_network(ip + "/" + nat_pool['netmask'])
                if ip in network_nat:
                    return nat_pool
        return None

    def generate_nat_pool_for_vip(self, vip):
        nat_pool = {}
        vip_extra = vip.get('extra') or {}
        if not vip_extra.get('allVLANs'):
            nat_pool['vlan'] = vip_extra.get('VLAN')[-1]
        else:
            LOG.warning("\n\n Can't generate NAT Pool for All VLANs! \n\n")
            nat_pool['vlan'] = '-1'
        nat_pool['netmask'] = vip['mask']
        if '4' in vip.get('ipVersion'):
            network = ipaddr.IPv4Network(vip['address'] + "/" + vip['mask'])
        else:
            network = ipaddr.IPv6Network(vip['address'] + "/" + vip['mask'])
        ips = []
        for ip in network.iterhosts():
            ips.append(ip)
        nat_pool['ip1'] = ips[-1]
        ids = []
        for i in self.get_nat_pools():
            ids.append(i.get('id'))
        for i in range(1, 2000):
            if not i in ids:
                nat_pool['id'] = i
        nat_pool['pat'] = True
        return nat_pool

    def import_certificate_or_key(self):
        dev_extra = self.device_ref.get('extra') or {}
        cmd = "do crypto import " + dev_extra['protocol'] + " "
        if dev_extra.get('passphrase'):
            cmd += "passphrase " + dev_extra['passphrase'] + " "
        cmd += dev_extra['server_ip'] + " " + dev_extra['server_user'] + \
               " " + dev_extra['file_name'] + " " + dev_extra['file_name'] + \
               "\n" + dev_extra['server_password']
        self.deployConfig(cmd)

    def create_ssl_proxy(self, ssl_proxy):
        cmd = "ssl-proxy service " + ssl_proxy['id']
        if ssl_proxy.get('cert'):
            cmd += "\ncert " + ssl_proxy['cert']
        if ssl_proxy.get('key'):
            cmd += "\nkey " + ssl_proxy['key']
        if ssl_proxy.get('authGroup'):
            cmd += "\nauthgroup " + ssl_proxy['authGroup']
        if ssl_proxy.get('ocspServer'):
            cmd += "\nocspserver " + ssl_proxy['ocspServer']
        if ssl_proxy.get('ocspBestEffort'):
            cmd += "\noscpserver " + ssl_proxy['ocspBestEffort']
        if ssl_proxy.get('crl'):
            cmd += "\ncrl " + ssl_proxy['crl']
        if ssl_proxy.get('crlBestEffort'):
            cmd += "\ncrl best-effort"
        if ssl_proxy.get('chainGroup'):
            cmd += "\nchaingroup " + ssl_proxy['chainGroup']
        if ssl_proxy.get('CheckPriority'):
            cmd += "\nrevcheckprion " + ssl_proxy['CheckPriority']
        self.deployConfig(cmd)

    def delete_ssl_proxy(self, ssl_proxy):
        cmd = "no ssl-proxy service " + ssl_proxy['id']
        self.deployConfig(cmd)

    def add_ssl_proxy_to_virtual_ip(self, vip, ssl_proxy):
        cmd = "policy-map multi-match global\nclass " + vip['id'] + \
              "\nssl-proxy server " + ssl_proxy['id']
        self.deployConfig(cmd)

    def remove_ssl_proxy_from_virtual_ip(self, vip, ssl_proxy):
        cmd = "policy-map multi-match global\nclass " + vip['id'] + \
              "\nno ssl-proxy server " + ssl_proxy['id']
        self.deployConfig(cmd)

    def create_vlan(self, vlan):
        cmd = "int vlan " + vlan['number'] + "\nip address" + vlan['ip'] + \
              " " + vlan['netmask'] + "\nno shutdown"
        self.deployConfig(cmd)

    def delete_vlan(self, vlan):
        cmd = "no int vlan " + vlan['number']
        self.deployConfig(cmd)

    def create_real_server(self, rserver):
        srv_type = rserver['type'].lower()
        srv_extra = rserver.get('extra') or {}
        cmd = "\nrserver " + srv_type + " " + rserver['id']
        if srv_extra.get('description'):
            cmd += "\ndescription " + srv_extra['description']
        if (srv_type == "host"):
            if rserver.get('address'):
                cmd += "\nip address " + rserver['address']
            if srv_extra.get('failOnAll'):
                cmd += "\nfail-on-all"
            if srv_extra.get('weight'):
                cmd += "\nweight " + str(srv_extra['weight'])
        else:
            if srv_extra.get('webHostRedir'):
                cmd += "\nwebhost-redirection " + srv_extra['webHostRedir']
                if srv_extra.get('redirectionCode'):
                    cmd += " " + str(srv_extra['redirectionCode'])
        if (srv_extra.get('maxCon') and srv_extra.get('minCon')):
            cmd += "\nconn-limit max " + str(srv_extra['maxCon']) + \
                " min " + str(srv_extra['minCon'])
        if srv_extra.get('rateConnection'):
            cmd += "\nrate-limit connection " + \
                   str(srv_extra['rateConnection'])
        if srv_extra.get('rateBandwidth'):
            cmd += "\nrate-limit bandwidth " + str(srv_extra['rateBandwidth'])
        if (rserver['state'] == "In Service"):
            cmd += "\ninservice"
        self.deployConfig(cmd)

    def delete_real_server(self, rserver):
        cmd = "no rserver " + rserver['id']
        self.deployConfig(cmd)

    def activate_real_server(self, serverfarm, rserver):
        cmd = "serverfarm " + serverfarm['id'] + "\n" + \
              "rserver " + rserver['id']
        if rserver.get('port'):
            cmd += " " + rserver['port']
        cmd += "\ninservice"
        self.deployConfig(cmd)

    def activate_real_server_global(self, rserver):
        cmd = "rserver " + rserver['id'] + "\ninservice"
        self.deployConfig(cmd)

    def suspend_real_server(self, serverfarm, rserver):
        cmd = "serverfarm " + serverfarm['id'] + "\n" + \
              "rserver " + rserver['id']
        if rserver.get('port'):
            cmd += " " + rserver['port']
        if (rserver.get('state') == "standby"):
            cmd += "\ninservice standby"
        else:
            cmd += "\nno inservice"
        self.deployConfig(cmd)

    def suspend_real_server_global(self, rserver):
        cmd = "rserver " + rserver['id'] + "\nno inservice"
        self.deployConfig(cmd)

    def create_probe(self, probe):
        pr_extra = probe.get('extra') or {}
        pr_type = probe['type'].lower().replace('-', ' ')
        if pr_type == "connect":
            pr_type = "tcp"
        pr_sd = ['echo udp', 'echo tcp',  'finger',  'tcp',  'udp']
        pr_tm = ['echo tcp', 'finger',  'tcp',  'rtsp',  'http',
                 'https', 'imap',  'pop',  'sip-tcp',  'smtp',  'telnet']
        pr_cr = ['http', 'https',  'imap',  'pop', 'radius']
        pr_rg = ['http', 'https',  'sip-tcp',  'sip-udp',  'tcp',  'udp']
        cmd = "\nprobe " + pr_type + " " + probe['id']
        if pr_extra.get('description'):
            cmd += "\ndescription " + pr_extra['description']
        if pr_extra.get('probeInterval'):
            cmd += "\ninterval " + str(pr_extra['probeInterval'])
        if (pr_type != 'vm'):
            if pr_extra.get('passDetectInterval'):
                cmd += "\npassdetect interval " + \
                       str(pr_extra['passDetectInterval'])
            if pr_extra.get('passDetectCount'):
                cmd += "\npassdetect count " + str(pr_extra['passDetectCount'])
            if pr_extra.get('failDetect'):
                cmd += "\nfaildetect " + str(pr_extra['failDetect'])
            if pr_extra.get('receiveTimeout'):
                cmd += "\nreceive " + str(pr_extra['receiveTimeout'])
            if ((pr_type != 'icmp') and pr_extra.get('port')):
                cmd += "\nport " + str(pr_extra['port'])
            if (pr_type != 'scripted'):
                if pr_extra.get('destIP'):
                    cmd += "\nip address " + pr_extra['destIP']
                    if ((pr_type != 'rtsp') and (pr_type != 'sip tcp') and \
                        (pr_type != 'sip udp') and pr_extra.get('isRoute')):
                            cmd += " routed"
            if (pr_type == "dns"):
                if pr_extra.get('domainName'):
                    cmd += "\ndomain " + pr_extra['domainName']
            if (pr_sd.count(pr_type) > 0):
                if pr_extra.get('sendData'):
                    cmd += "\nsend-data " + pr_extra['sendData']
            if (pr_tm.count(pr_type) > 0):
                if pr_extra.get('openTimeout'):
                    cmd += "\nopen " + str(pr_extra['openTimeout'])
                if pr_extra.get('tcpConnTerm'):
                    cmd += "\nconnection term forced"
            if (pr_cr.count(pr_type) > 0):
                if (pr_extra.get('userName') and pr_extra.get('password')):
                    cmd += "\ncredentials " + pr_extra['userName'] + \
                           " " + pr_extra['password']
                    if (pr_type == 'radius'):
                        if pr_extra.get('userSecret'):
                            cmd += " secret " + pr_extra['userSecret']
            if (pr_rg.count(pr_type) > 0):
                if pr_extra.get('expectRegExp'):
                    cmd += "\nexpect regex " + pr_extra['expectRegExp']
                    if pr_extra.get('expectRegExpOffset'):
                        cmd += " offset " + str(pr_extra['expectRegExpOffset'])
            if ((pr_type == 'http') or (pr_type == 'https')):
                if pr_extra.get('requestMethodType'):
                    cmd += "\nrequest method " + \
                        pr_extra['requestMethodType'].lower() + \
                        " url " + pr_extra['requestHTTPurl'].lower()
                if pr_extra.get('appendPortHostTag'):
                    cmd += "\nappend-port-hosttag"
                if pr_extra.get('hash'):
                    cmd += "\nhash "
                    if pr_extra.get('hashString'):
                        cmd += pr_extra['hashString']
                if (pr_type == 'https'):
                    if pr_extra.get('cipher'):
                        cmd += "\nssl cipher " + pr_extra['cipher']
                    if pr_extra.get('SSLversion'):
                        cmd += "\nssl version " + pr_extra['SSLversion']
            if ((pr_type == 'pop') or (pr_type == 'imap')):
                if pr_extra.get('requestComman'):
                    cmd += "\nrequest command " + pr_extra['requestComman']
                if (pr_type == 'imap'):
                    if pr_extra.get('mailbox'):
                        cmd += "\ncredentials mailbox " + pr_extra['mailbox']
            if (pr_type == 'radius'):
                if pr_extra.get('NASIPaddr'):
                    cmd += "\nnas ip address " + pr_extra['NASIPaddr']
            if (pr_type == 'rtsp'):
                if pr_extra.get('equareHeaderValue'):
                    cmd += "\nheader require header-value " + \
                        pr_extra['equareHeaderValue']
                if pr_extra.get('proxyRequareHeaderValue'):
                    cmd += "\nheader proxy-require header-value " + \
                        pr_extra['proxyRequareHeaderValue']
                if pr_extra.get('requestURL'):
                    if pr_extra.get('requestMethodType'):
                        cmd += "\nrequest method " + \
                            str(pr_extra['requestMethodType']) + \
                            " url " + pr_extra['requestURL']
            if (pr_type == 'scripted'):
                if pr_extra.get('scriptName'):
                    cmd += "\nscript " + pr_extra['scriptName']
                    if pr_extra.get('scriptArgv'):
                        cmd += " " + pr_extra['scriptArgv']
            if ((pr_type == 'sip-udp') and pr_extra.get('Rport')):
                cmd += "\nrport enable"
            if (type == 'snmp'):
                if pr_extra.get('SNMPver'):
                    cmd += "\nversion " + pr_extra['SNMPver']
                    if pr_extra.get('SNMPComm'):
                        cmd += "\ncommunity " + pr_extra['SNMPComm']
        else:  # for type == vm
            if pr_extra.get('VMControllerName'):
                cmd += "vm-controller " + pr_extra['VMControllerName']
                if (pr_extra.get('maxCPUburstThresh') and \
                    pr_extra.get('minCPUburstThresh')):
                    cmd += "\nload cpu burst-threshold max " + \
                        pr_extra['maxCPUburstThresh'] + " min " + \
                        pr_extra['minCPUburstThresh']
                if (pr_extra.get('maxMemBurstThresh') and \
                    pr_extra.get('minMemBurstThresh')):
                    cmd += "\nload mem burst-threshold max " + \
                        pr_extra['maxMemBurstThresh'] + " min " + \
                        pr_extra['minMemBurstThresh']
        self.deployConfig(cmd)

    def delete_probe(self, probe):
        pr_type = probe['type'].lower().replace('-', ' ')
        if pr_type == "connect":
            pr_type = "tcp"
        cmd = "no probe " + pr_type + " " + probe['id']
        self.deployConfig(cmd)

    def create_server_farm(self, sf, predictor):
        sf_type = sf['type'].lower()
        sf_extra = sf['extra'] or {}
        cmd = "serverfarm " + sf_type + " " + sf['id']
        if sf_extra.get('description'):
            cmd += "\ndescription " + sf_extra['description']
        if sf_extra.get('failAction'):
            cmd += "\nfailaction " + sf_extra['failAction']
        if predictor.get('type'):
            type_ = predictor['type'].lower()
            predictor_extra = predictor['extra'] or {}
            if (type_ == "leastbandwidth"):
                type_ = "least-bandwidth"
                accessTime = predictor_extra.get('accessTime')
                if accessTime:
                    type_ += " assess-time " + str(accessTime)
                if sf_extra.get('accessTime'):
                    type_ += " samples " + predictor_extra.get('sample')
            elif (type_ == "leastconnections"):
                type_ = "leastconns slowstart " + \
                        predictor_extra.get('slowStartDur')
            elif (type_ == "leastloaded"):
                type_ = "least-loaded probe " + \
                        predictor_extra.get('snmpProbe')
            elif (type_ == "hashaddress"):
                type_ = "hash address "
                if predictor_extra.get('netmask'):
                    type_ += predictor_extra['netmask']
                    if predictor_extra.get('prefix'):
                        type_ += "\npredictor hash address v6-prefix " + \
                                predictor_extra['prefix']
                elif predictor_extra.get('prefix'):
                    type_ += predictor_extra['prefix']
            cmd += "\npredictor " + type_
        if (sf_type == "host"):
            if sf_extra.get('failOnAll'):
                cmd += "\nfail-on-all"
            if sf_extra.get('transparen'):
                cmd += "\ntransparent"
            if sf_extra.get('partialThreshPercentage') and \
               sf_extra.get('backInservice'):
                cmd += "\npartial-threshold " + \
                    str(sf_extra['partialThreshPercentage']) + " back-" + \
                    "inservice " + str(sf_extra['backInservice'])
            if sf_extra.get('inbandHealthCheck'):
                h_check = sf_extra['inbandHealthCheck'].lower()
                if sf_extra.get('inbandHealthMonitoringThreshold'):
                    cmd += "\ninband-health check " + h_check + " " + \
                           sf_extra['inbandHealthMonitoringThreshold']
                if sf_extra.get('resetTimeout') and \
                   sf_extra.get('connFailureThreshCount'):
                    cmd += " " + str(sf_extra['connFailureThreshCount']) + \
                           " reset " + str(sf_extra['resetTimeout'])
                if (h_check == "remove" and \
                    sf_extra.get('resumeService') and \
                    sf_extra.get('connFailureThreshCount')):
                    cmd += " " + str(sf_extra['connFailureThreshCount']) + \
                        " resume-service " + str(sf_extra['resumeService'])
            if sf_extra.get('dynamicWorkloadScale'):
                cmd += "\ndws " + sf_extra['dynamicWorkloadScale']
                if (sf_extra['dynamicWorkloadScale'] == "burst") and \
                    sf_extra.get('VMprobe'):
                    cmd += " probe " + sf_extra['VMprobe']
        self.deployConfig(cmd)

    def delete_server_farm(self, sf):
        cmd = "no serverfarm " + sf['id']
        self.deployConfig(cmd)

    def add_real_server_to_server_farm(self, sf, rserver):
        rs_extra = rserver.get('extra') or {}
        cmd = "serverfarm " + sf['id'] + "\nrserver " + rserver['id']
        if rs_extra.get('port'):
            cmd += " " + rs_extra['port']
        if rs_extra.get('weight'):
            cmd += "\nweight " + str(rs_extra['weight'])
        if rs_extra.get('backupRS'):
            cmd += "\nbackup-rserver " + rs_extra['backupRS']
            if rs_extra.get('backupRSport'):
                cmd += " " + str(rs_extra['backupRSport'])
        if rs_extra.get('maxCon') and rs_extra.get('minCon'):
            cmd += "\nconn-limit max " + str(rs_extra['maxCon']) + \
                   " min " + str(rs_extra['minCon'])
        if rs_extra.get('rateConnection'):
            cmd += "\nrate-limit connection " + \
                   str(rs_extra['rateConnection'])
        if rs_extra.get('rateBandwidth'):
            cmd += "\nrate-limit bandwidth " + str(rs_extra['rateBandwidth'])
        if rs_extra.get('cookieStr'):
            cmd += "\ncookie-string " + rs_extra['cookieStr']
        if rs_extra.get('failOnAll'):
            cmd += "\nfail-on-all"
        if rs_extra.get('state'):
            cmd += "\ninservice"
            if rs_extra.get('state').lower() == "standby":
                cmd += " standby"
        self.deployConfig(cmd)

    def delete_real_server_from_server_farm(self, sf, rserver):
        cmd = "serverfarm " + sf['id'] + "\nno rserver " + rserver['id']
        if rserver.get('port'):
            cmd += " " + rserver['port']
        self.deployConfig(cmd)

    def add_probe_to_server_farm(self, sf, probe):
        cmd = "serverfarm " + sf['id'] + "\nprobe " + probe['id']
        self.deployConfig(cmd)

    def delete_probe_from_server_farm(self, sf, probe):
        cmd = "serverfarm " + sf['id'] + "\nno probe " + probe['id']
        self.deployConfig(cmd)

    def create_stickiness(self, sticky):
        name = sticky['id']
        sticky_type = sticky['type'].lower().replace('httpc', 'http-c')
        sticky_type = sticky_type.replace('header', '-header')
        sticky_type = sticky_type.replace('l4', 'layer4-')
        st_extra = sticky.get('extra') or {}
        cmd = "sticky " + sticky_type + " "
        if (sticky_type == "http-content"):
            cmd += name + "\n"
            if st_extra.get('offset'):
                cmd += "content offset " + str(st_extra['offset']) + "\n"
            if st_extra.get('length'):
                cmd += "content length " + str(st_extra['length']) + "\n"
            if st_extra.get('beginPattern'):
                cmd += "content begin-pattern " + st_extra['beginPattern']
                if st_extra.get('endPattern'):
                    cmd += " end-pattern " + st_extra['endPattern']
        elif sticky_type == "http-cookie":
            cmd += st_extra['cookieName'] + " " + name
            if st_extra.get('enableInsert'):
                cmd += "\ncookie insert"
                if st_extra.get('browserExpire'):
                    cmd += " browser-expire"
            if st_extra.get('offset'):
                cmd += "\ncookie offset " + str(st_extra['offset'])
                if st_extra.get('length'):
                    cmd += " length " + str(st_extra['length'])
            if st_extra.get('secondaryName'):
                cmd += "\ncookie secondary " + st_extra['secondaryName']
        elif sticky_type == "http-header":
            cmd += st_extra.get('headerName') + " " + name
            if st_extra.get('offset'):
                cmd += "\nheader offset " + str(st_extra['offset'])
                if st_extra.get('length'):
                    cmd += " length " + str(st_extra['length'])
        elif sticky_type == "ip-netmask":
            cmd += str(st_extra['netmask']) + " address " + \
                st_extra['addrType'] + " " + name
            if st_extra.get('ipv6PrefixLength'):
                cmd += "\nv6-prefix " + str(st_extra['ipv6PrefixLength'])
        elif sticky_type == "v6prefix":
            cmd += str(st_extra['prefixLength']) + " address " + \
                st_extra.get('addressType').lower() + " " + name
            if st_extra.get('netmask'):
                cmd += "\nip-netmask " + str(st_extra['netmask'])
        elif sticky_type == "layer4-payload":
            cmd += name + "\n"
            if st_extra.get('enableStickyForResponse'):
                cmd += "response sticky"
            if st_extra.get('offset') or st_extra.get('length') \
                or st_extra.get('endPattern') or st_extra.get('beginPattern'):
                cmd += "\nlayer4-payload"
                if st_extra.get('offset'):
                    cmd += " offset " + str(st_extra['offset'])
                if st_extra.get('length'):
                    cmd += " length " + str(st_extra['length'])
                if st_extra.get('beginPattern'):
                    cmd += " begin-pattern " + st_extra['beginPattern']
                if st_extra.get('endPattern') and not st_extra.get('length'):
                    cmd += " end-pattern " + st_extra['endPattern']
        elif sticky_type == "radius":
            cmd += "framed-ip " + name
        elif sticky_type == "rtsp-header":
            cmd += " Session " + name
            if st_extra.get('offset'):
                cmd += "\nheader offset " + str(st_extra['offset'])
                if st_extra.get('length'):
                    cmd += " length " + str(st_extra['length'])
        elif sticky_type == "sip-header":
            cmd += " Call-ID" + name
        if st_extra.get('timeout'):
            cmd += "\ntimeout " + str(st_extra['timeout']) + ""
        if st_extra.get('timeoutActiveConn'):
            cmd += "\ntimeout activeconns"
        if st_extra.get('replicateOnHAPeer'):
            cmd += "\nreplicate sticky"
        if st_extra.get('sf_id'):
            cmd += "\nserverfarm " + st_extra['sf_id']
            if st_extra.get('backupServerFarm'):
                cmd += " backup " + st_extra['backupServerFarm']
                if st_extra.get('enableStyckyOnBackupSF'):
                    cmd += " sticky"
                if st_extra.get('aggregateState'):
                    cmd += " aggregate-state"
        self.deployConfig(cmd)

    def delete_stickiness(self, sticky):
        name = sticky['id']
        st_extra = sticky.get('extra') or {}
        sticky_type = sticky['type'].lower().replace('httpc', 'http-c')
        sticky_type = sticky_type.replace('header', '-header')
        sticky_type = sticky_type.replace('l4', 'layer4-')
        cmd = "no sticky " + sticky_type + " "
        if sticky_type in ("http-content", "layer4-payload", "radius"):
            cmd += name
        elif sticky_type == "http-cookie":
            cmd += st_extra['cookieName'] + " " + name
        elif sticky_type == "http-header":
            cmd += st_extra['headerName'] + " " + name
        elif sticky_type == "ip-netmask":
            cmd += str(st_extra['netmask']) + " address " + \
                st_extra['addrType'] + " " + name
        elif sticky_type == "rtsp-header":
            cmd += " Session " + name
        elif sticky_type == "sip-header":
            cmd += " Call-ID" + name
        self.deployConfig(cmd)

    def create_virtual_ip(self, vip, sfarm):
        vip_extra = vip.get('extra') or {}
        if vip_extra.get('allVLANs'):
            pmap = "global"
        else:
            pmap = "int-" + str(md5(vip_extra['VLAN']).hexdigest())
        cmd = "access-list vip-acl extended permit ip any host " + \
              vip['address']
        self.deployConfig(cmd)
        appProto = vip_extra.get('appProto')
        if appProto.lower() in ('other', 'http'):
            appProto = ""
        else:
            appProto = "_" + appProto.lower()
        cmd = "policy-map type loadbalance " + appProto + \
              " first-match " + vip['id'] + "-l7slb\n"
        if vip_extra.get('description'):
            cmd += "description " + vip_extra.get('description') + "\n"
        cmd += "class class-default\nserverfarm " + sfarm['id']
        if vip_extra.get('backupServerFarm'):
            cmd += " backup " + vip_extra['backupServerFarm']
        cmd += "\nexit\nexit\nclass-map match-all " + vip['id'] + "\n"
        cmd += "match virtual-address " + vip['address'] + " " + \
               str(vip['mask']) + " " + vip_extra['proto'].lower()
        if vip_extra['proto'].lower() != "any" and vip_extra.get('port'):
            cmd += " eq " + str(vip_extra['port'])
        cmd += "\nexit\npolicy-map multi-match " + pmap + "\nclass " + \
               vip['id']
        if vip.get('status'):
            cmd += "\nloadbalance vip " + vip['status'].lower()
        cmd += "\nloadbalance policy " + vip['id'] + "-l7slb"
        if vip_extra.get('ICMPreply'):
            cmd += "\nloadbalance vip icmp-reply"
        self.deployConfig(cmd)
        if vip_extra.get('allVLANs'):
            cmd = "service-policy input " + pmap
            try:
                self.deployConfig(cmd)
            except:
                LOG.warning("Got exception on acl set")
        else:
            VLAN = vip_extra['VLAN']
            if is_sequence(VLAN):
                for i in VLAN:
                    cmd = "interface vlan " + str(i) + \
                          "\nservice-policy input " + pmap
                    self.deployConfig(cmd)
                    cmd = "interface vlan " + str(i) + \
                          "\naccess-group input vip-acl"
                    try:
                        self.deployConfig(cmd)
                    except:
                        LOG.warning("Got exception on acl set")
            else:
                    cmd = "interface vlan " + str(VLAN) + \
                          "\nservice-policy input " + pmap
                    self.deployConfig(cmd)
                    cmd = "interface vlan " + str(VLAN) + \
                          "\naccess-group input vip-acl"
                    try:
                        self.deployConfig(cmd)
                    except:
                        LOG.warning("Got exception on acl set")
        nat_pool = self.find_nat_pool_for_vip(vip)
        if nat_pool:
            self.add_nat_pool_to_vip(nat_pool, vip)
        else:
            nat_pool = self.generate_nat_pool_for_vip(vip)
            self.create_nat_pool(nat_pool)
            self.add_nat_pool_to_vip(nat_pool, vip)

    def delete_virtual_ip(self, vip):
        vip_extra = vip['extra'] or {}
        if vip_extra.get('allVLANs'):
            pmap = "global"
        else:
            pmap = "int-" + str(md5(vip_extra['VLAN']).hexdigest())
        cmd = "policy-map multi-match " + pmap + "\nno class " + vip['id']
        self.deployConfig(cmd)
        cmd = "no class-map match-all " + vip['id'] + "\n"
        self.deployConfig(cmd)
        cmd = "no policy-map type loadbalance first-match " + \
              vip['id'] + "-l7slb"
        self.deployConfig(cmd)
        if (self.getConfig("policy-map %s" % pmap).find("class") <= 0):
            if vip_extra.get('allVLANs'):
                cmd = "no service-policy input " + pmap
                self.deployConfig(cmd)
            else:
                VLAN = vip_extra['VLAN']
                if is_sequence(VLAN):
                    for i in VLAN:
                        cmd = "interface vlan " + str(i) + \
                              "\nno service-policy input " + pmap
                        self.deployConfig(cmd)
                else:
                        cmd = "interface vlan " + str(VLAN) + \
                              "\nno service-policy input " + pmap
                        self.deployConfig(cmd)
            cmd = "no policy-map multi-match " + pmap
            self.deployConfig(cmd)
        cmd = "no access-list vip-acl extended permit ip any host " + \
              vip['address']
        self.deployConfig(cmd)

    def get_capabilities(self):
        capabilities = {}
        capabilities['algorithms'] = list(self.algorithms.keys())
        capabilities['protocols'] = ['HTTP', 'TCP', 'HTTPS', 'RTSP', \
                                     'SIP-TCP', 'SIP-UDP', 'UDP', \
                                     'FTP', 'Generic', 'RDP', 'DNS', \
                                     'RADIUS', ]
        return capabilities

########NEW FILE########
__FILENAME__ = dummy
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
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
import logging

from balancer.drivers.base_driver import BaseDriver

logger = logging.getLogger(__name__)


class DummyDriver(BaseDriver):
    def import_certificate_or_key(self):
        logger.debug("Called DummyDriver(%r).import_certificate_or_key().",
                     self.device_ref['id'])

    def create_ssl_proxy(self, ssl_proxy):
        logger.debug("Called DummyDriver(%r).create_ssl_proxy(%r).",
                     self.device_ref['id'], ssl_proxy)

    def delete_ssl_proxy(self, ssl_proxy):
        logger.debug("Called DummyDriver(%r).delete_ssl_proxy(%r).",
                     self.device_ref['id'], ssl_proxy)

    def add_ssl_proxy_to_virtual_ip(self, vip, ssl_proxy):
        logger.debug("Called DummyDriver(%r)."
                     "add_ssl_proxy_to_virtual_ip(%r, %r).",
                     self.device_ref['id'], vip, ssl_proxy)

    def remove_ssl_proxy_from_virtual_ip(self, vip, ssl_proxy):
        logger.debug("Called DummyDriver(%r)."
                     "remove_ssl_proxy_from_virtual_ip(%r, %r).",
                     self.device_ref['id'], vip, ssl_proxy)

    def create_real_server(self, rserver):
        logger.debug("Called DummyDriver(%r).create_real_server(%r).",
                     self.device_ref['id'], rserver)

    def delete_real_server(self, rserver):
        logger.debug("Called DummyDriver(%r).delete_real_server(%r).",
                     self.device_ref['id'], rserver)

    def activate_real_server(self, serverfarm, rserver):
        logger.debug("Called DummyDriver(%r).activate_real_server(%r, %r).",
                     self.device_ref['id'], serverfarm, rserver)

    def activate_real_server_global(self, rserver):
        logger.debug("Called DummyDriver(%r).activate_real_server_global(%r).",
                     self.device_ref['id'], rserver)

    def suspend_real_server(self, serverfarm, rserver):
        logger.debug("Called DummyDriver(%r).suspend_real_server(%r, %r).",
                     self.device_ref['id'], serverfarm, rserver)

    def suspend_real_server_global(self, rserver):
        logger.debug("Called DummyDriver(%r).suspend_real_server_global(%r).",
                     self.device_ref['id'], rserver)

    def create_probe(self, probe):
        logger.debug("Called DummyDriver(%r).create_probe(%r).",
                     self.device_ref['id'], probe)

    def delete_probe(self, probe):
        logger.debug("Called DummyDriver(%r).delete_probe(%r).",
                     self.device_ref['id'], probe)

    def create_server_farm(self, serverfarm, predictor):
        logger.debug("Called DummyDriver(%r).create_server_farm(%r).",
                     self.device_ref['id'], serverfarm)

    def delete_server_farm(self, serverfarm):
        logger.debug("Called DummyDriver(%r).delete_server_farm(%r).",
                     self.device_ref['id'], serverfarm)

    def add_real_server_to_server_farm(self, serverfarm, rserver):
        logger.debug("Called DummyDriver(%r)."
                     "add_real_server_to_server_farm(%r, %r).",
                     self.device_ref['id'], serverfarm, rserver)

    def delete_real_server_from_server_farm(self, serverfarm, rserver):
        logger.debug("Called DummyDriver(%r)."
                     "delete_real_server_from_server_farm(%r, %r).",
                     self.device_ref['id'], serverfarm, rserver)

    def add_probe_to_server_farm(self, serverfarm, probe):
        logger.debug("Called DummyDriver(%r)."
                     "add_probe_to_server_farm(%r, %r).",
                     self.device_ref['id'], serverfarm, probe)

    def delete_probe_from_server_farm(self, serverfarm, probe):
        logger.debug("Called DummyDriver(%r)."
                     "delete_probe_from_server_farm(%r, %r).",
                     self.device_ref['id'], serverfarm, probe)

    def create_stickiness(self, sticky):
        logger.debug("Called DummyDriver(%r).create_stickiness(%r).",
                     self.device_ref['id'], sticky)

    def delete_stickiness(self, sticky):
        logger.debug("Called DummyDriver(%r).delete_stickiness(%r).",
                     self.device_ref['id'], sticky)

    def create_virtual_ip(self, vip, serverfarm):
        logger.debug("Called DummyDriver(%r).create_virtual_ip(%r, %r).",
                     self.device_ref['id'], vip, serverfarm)

    def delete_virtual_ip(self, vip):
        logger.debug("Called DummyDriver(%r).delete_virtual_ip(%r).",
                     self.device_ref['id'], vip)

    def get_statistics(self, serverfarm, rserver):
        logger.debug("Called DummyDriver(%r).get_statistics(%r, %r).",
                     self.device_ref['id'], serverfarm, rserver)

########NEW FILE########
__FILENAME__ = config_manager
import logging
import os.path

LOG = logging.getLogger(__name__)


class ConfigManager(object):
    def __init__(self, device_ref, remote_ctrl):
        device_extra = device_ref.get('extra') or {}
        self.remote_config_path = (device_extra.get('remote_config_path') or
                            '/etc/haproxy/haproxy.cfg')
        self.local_config_path = '/tmp/haproxy.cfg'
        self.remote_control = remote_ctrl
        self.config = {}
        self.need_deploy = False

    def __del__(self):
        if os.path.exists(self.local_config_path):
            os.remove(self.local_config_path)

    def deploy_config(self):
        if self.need_deploy:
            LOG.debug("Deploying configuration")
            tmp_path = '/tmp/haproxy.cfg.remote'
            self.remote_control.put_file(self.local_config_path,
                                         tmp_path)
            if self._validate_config(tmp_path):
                self.remote_control.perform('sudo mv {0} {1}'
                                            .format(tmp_path,
                                                    self.remote_config_path))
                self.need_deploy = False

            return not self.need_deploy
        else:
            return False

    def add_lines_to_block(self, block, lines):
        self._fetch_config()
        LOG.debug('Adding lines to {0} {1}: {2}'.format(block.type, block.name,
                                                        lines))
        for key in self.config:
            if block.type in key and block.name in key:
                for line in lines:
                    self.config[key].append('\t' + line)

        self._apply_config()

    def del_lines_from_block(self, block, lines):
        '''
            For every <del_line> in <lines> deletes the whole line from <block>
            if this line contains <del_line>
        '''
        self._fetch_config()
        LOG.debug('Deleting lines from {0} {1}: {2}'
                  .format(block.type, block.name, lines))
        for key in self.config:
            if block.type in key and block.name in key:
                for del_line in lines:
                    for line in self.config[key]:
                        if del_line in line:
                            self.config[key].remove(line)
        self._apply_config()

    def add_rserver(self, backend_name, server):
        if not backend_name:
            LOG.warn('Empty backend name')
            return

        server_line = ('server {0} {1}:{2} {3} maxconn {4} '
                       'inter {5} rise {6} fall {7}'
                       .format(server.name, server.address,
                              server.port, server.check,
                              server.maxconn, server.inter,
                              server.rise, server.fall))
        if server.disabled:
            server_line += ' disabled'
        self.add_lines_to_block(HaproxyBackend(backend_name), (server_line,))

    def delete_rserver(self, backend_name, server_name):
        if not backend_name:
            LOG.warn('Empty backend name')
            return

        self.del_lines_from_block(HaproxyBackend(backend_name), (server_name,))

    def enable_rserver(self, backend_name, server_name, enable=True):
        '''
            Enables or disables server in serverfarm
        '''
        if backend_name == '':
            LOG.warn('Empty backend name')
            return

        self._fetch_config()
        for block in self.config:
            if 'backend' in block and backend_name in block:
                for line in self.config[block]:
                    if 'server' in line and server_name in line:
                        if not enable:
                            new_line = line + ' disabled'
                        else:
                            new_line = line.replace(' disabled', '')
                        self.config[block][self.config[block].index(line)] =\
                            new_line
        self._apply_config()

    def add_frontend(self, fronted, backend=None):
        if fronted.name == '':
            LOG.warn('Empty fronted name')
            return
        elif fronted.bind_address == '' or fronted.bind_port == '':
            LOG.warn('Empty bind adrress or port')
            return

        self._fetch_config()
        LOG.debug('Adding frontend %s' % fronted.name)
        frontend_block = []
        frontend_block.append('\tbind %s:%s' % (fronted.bind_address,
                                           fronted.bind_port))
        frontend_block.append('\tmode %s' % fronted.mode)
        if backend is not None:
            frontend_block.append('\tdefault_backend %s' %
                                           backend.name)
        self.config['frontend %s' % fronted.name] = frontend_block
        self._apply_config()

        return fronted.name

    def add_backend(self, backend):
        if backend.name == '':
            LOG.warn('Empty backend name')
            return
        self._fetch_config()
        LOG.debug('Adding backend {0}'.format(backend.name))
        backend_block = []
        backend_block.append('\tbalance %s' % backend.balance)
        self.config['backend %s' % backend.name] = backend_block
        self._apply_config()

        return backend.name

    def delete_block(self, block):
        if block.name == '':
            LOG.warn('Empty block name')
            return

        self._fetch_config()
        for key in self.config.keys():
            if block.type in key and block.name in key:
                LOG.debug('Delete block {0} {1}'.format(block.type,
                                                        block.name))
                del self.config[key]
        self._apply_config()

    def find_string_in_any_block(self, string, block_type=None):
        self._fetch_config()
        for key in self.config:
            if block_type is None or block_type in key:
                if string in self.config[key]:
                    return True

        return False

    def _fetch_config(self):
        if not self.need_deploy:
            LOG.debug('Fetching configuration from {0}'
                      .format(self.remote_config_path))

            self.remote_control.get_file(self.remote_config_path,
                                         self.local_config_path)

            config_file = open(self.local_config_path, 'r')
            self.config = {}
            cur_block = ''
            for line in config_file:
                line = line.rstrip()

                if line.find('global') == 0:
                    cur_block = line
                    self.config[cur_block] = []
                elif line.find('defaults') == 0:
                    cur_block = line
                    self.config[cur_block] = []
                elif line.find('listen') == 0:
                    cur_block = line
                    self.config[cur_block] = []
                elif line.find('backend') == 0:
                    cur_block = line
                    self.config[cur_block] = []
                elif line.find('frontend') == 0:
                    cur_block = line
                    self.config[cur_block] = []
                elif cur_block == '':
                    cur_block = 'comments'
                    self.config[cur_block] = [line]
                else:
                    self.config[cur_block].append(line)

            config_file.close()

    def _apply_config(self):
        LOG.debug('writing configuration to %s' %
                  self.local_config_path)
        config_file = open(self.local_config_path, 'w')

        for line in self.config.get('comments', []):
            config_file.write(line + '\n')
        for section in ['global', 'defaults']:
            config_file.write(section + '\n')
            for line in (self.config.get(section, [])):
                config_file.write(line + '\n')

        for block in sorted(self.config):
            if block not in ['comments', 'global', 'defaults']:
                config_file.write('%s\n' % block)
                for line in sorted(self.config[block]):
                    config_file.write('%s\n' % line)

        config_file.close()
        self.need_deploy = True

    def _validate_config(self, filepath):
        command = 'haproxy -c -f {0}'.format(filepath)
        output = self.remote_control.perform(command)[1]
        if 'Configuration file is valid' in output:
            LOG.debug('Remote configuration is valid: {0}'.format(filepath))
            return True
        else:
            LOG.error('Invalid configuration in {0}: {1}'.format(filepath,
                                                                 output))
            return False


class HaproxyConfigBlock(object):
    def __init__(self, name='', type=''):
        self.name = name
        self.type = type


class HaproxyFronted(HaproxyConfigBlock):
    def __init__(self, vip_ref):
        super(HaproxyFronted, self).__init__(vip_ref['id'], 'frontend')
        self.bind_address = vip_ref['address']
        self.bind_port = vip_ref['port']
        self.default_backend = ''
        self.mode = vip_ref.get('extra', {}).get('protocol', 'http').lower()


class HaproxyBackend(HaproxyConfigBlock):
    def __init__(self, name=''):
        super(HaproxyBackend, self).__init__(name, 'backend')
        self.mode = ''
        self.balance = 'roundrobin'


class HaproxyListen(HaproxyConfigBlock):
    def __init__(self, name=''):
        super(HaproxyListen, self).__init__(name, 'listen')
        self.mode = ''
        self.balance = 'source'


class HaproxyRserver():
    def __init__(self, rserver_ref):
        extra_params = rserver_ref.get('extra', {})
        self.name = rserver_ref['id']
        self.address = rserver_ref.get('address', '')
        self.check = 'check'
        self.cookie = rserver_ref.get('extra', {}).get('cookie', '')
        self.disabled =\
            extra_params.get('condition', 'enabled').lower() != 'enabled'
        self.error_limit = extra_params.get('error_limit', 10)
        self.fall = extra_params.get('fall', 3)
        self.id = extra_params.get('id', '')
        self.inter = extra_params.get('inter', 2000)
        self.fastinter = extra_params.get('fastinter', 2000)
        self.downinter = extra_params.get('downinter', 2000)
        self.maxconn = extra_params.get('maxconn', 32)
        self.minconn = extra_params.get('minconn', 0)
        self.observe = extra_params.get('observe', '')
        self.on_error = extra_params.get('on_error', '')
        self.port = rserver_ref.get('port', '')
        self.redir = extra_params.get('redir', '')
        self.rise = extra_params.get('rise', 2)
        self.slowstart = extra_params.get('slowstart', 0)
        self.source_addres = extra_params.get('source_addres', '')
        self.source_min_port = extra_params.get('source_min_port', '')
        self.source_max_port = extra_params.get('source_max_port', '')
        self.track = extra_params.get('track', '')
        self.weight = extra_params.get('weight', 1)

########NEW FILE########
__FILENAME__ = haproxy_driver
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
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

import logging

from balancer.drivers import base_driver
from remote_control import *
from config_manager import *


LOG = logging.getLogger(__name__)

ALGORITHMS_MAPPING = {
    'ROUND_ROBIN': 'roundrobin',
    'LEAST_CONNECTION': 'leastconn',
    'HASH_SOURCE': 'source',
    'HASH_URI': 'uri',
    'STATIC_RR': 'static-rr',
}


class HaproxyDriver(base_driver.BaseDriver):
    """
    This is the driver for HAProxy loadbalancer (http://haproxy.1wt.eu/)
    """

    algorithms = ALGORITHMS_MAPPING
    default_algorithm = ALGORITHMS_MAPPING['ROUND_ROBIN']

    def __init__(self, conf, device_ref):
        super(HaproxyDriver, self).__init__(conf, device_ref)

        self._remote_ctrl = RemoteControl(device_ref)
        self.remote_socket = RemoteSocketOperation(device_ref,
                                                   self._remote_ctrl)
        self.remote_interface = RemoteInterface(device_ref, self._remote_ctrl)
        self.remote_service = RemoteService(self._remote_ctrl)
        self.config_manager = ConfigManager(device_ref, self._remote_ctrl)

    def request_context(self):
        mgr = super(HaproxyDriver, self).request_context()
        mgr.context.add_rollback(self.finalize_config)
        return mgr

    def add_probe_to_server_farm(self, serverfarm, probe):
        """
        Add a probe into server farm

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param probe: Probe \
        - see :py:class:`balancer.db.models.Probe`
        """
        probe_type = probe['type'].lower()
        if probe_type not in ('http', 'https', 'tcp', 'connect'):
            LOG.debug('unsupported probe type %s, exit',
                         probe_type)
            return

        backend = HaproxyBackend(serverfarm['id'])

        new_lines = []
        if probe_type == 'http':
            option = 'option httpchk'
            method = (probe.get('extra') or {}).get('method')
            option = option + ' ' + (method if method else 'GET')

            HTTPurl = (probe.get('extra') or {}).get('path')
            option = option + ' ' + (HTTPurl if HTTPurl else '/')

            new_lines.append(option)

        # TODO: add handling of 'expected' field
        # from probe ('http-check expect ...')
        elif probe_type == 'tcp' or probe_type == 'connect':
            new_lines.append('option httpchk')
        elif probe_type == 'https':
            new_lines.append('option ssl-hello-chk')

        if new_lines:
            self.config_manager.add_lines_to_block(backend, new_lines)

    def delete_probe_from_server_farm(self, serverfarm, probe):
        """
        Delete probe from server farm

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param probe: Probe \
        - see :py:class:`balancer.db.models.Probe`
        """
        backend = HaproxyBackend(serverfarm['id'])

        probe_type = probe['type'].lower()
        del_lines = []
        if probe_type in ('http', 'tcp', 'connect'):
            del_lines = ['option httpchk', 'http-check expect']
        elif probe_type == 'https':
            del_lines = ['option ssl-hello-chk', ]

        if del_lines:
            self.config_manager.del_lines_from_block(backend, del_lines)

    # For compatibility with drivers for other devices
    def create_real_server(self, rserver):
        pass

    def delete_real_server(self, rserver):
        pass

    def create_probe(self, probe):
        pass

    def delete_probe(self, probe):
        pass

    def create_stickiness(self, sticky):
        pass

    def delete_stickiness(self, sticky):
        pass

    def add_real_server_to_server_farm(self, serverfarm, rserver):
        """
        Add a node (rserver) into load balancer (serverfarm)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        haproxy_rserver = HaproxyRserver(rserver)
        LOG.debug('Creating rserver %s in the '
                     'backend block %s' %
                     (haproxy_rserver.name, serverfarm['id']))

        self.config_manager.add_rserver(serverfarm['id'],
                                        haproxy_rserver)

    def delete_real_server_from_server_farm(self, serverfarm, rserver):
        """
        Delete node (rserver) from the specified loadbalancer (serverfarm)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        haproxy_rserver = HaproxyRserver(rserver)
        #Modify remote config file, check and restart remote haproxy
        LOG.debug('Deleting rserver %s in the '
                     'backend block %s' %
                     (haproxy_rserver.name, serverfarm['id']))

        self.config_manager.delete_rserver(serverfarm['id'],
                                           haproxy_rserver.name)

    def create_virtual_ip(self, virtualserver, serverfarm):
        """
        Create a new vip (virtual IP)

        :param virtualserver: VirtualServer \
        - see :py:class:`balancer.db.models.VirtualServer`
        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        """
        if not bool(virtualserver['id']):
            LOG.error('Virtualserver name is empty')
            return
        frontend = HaproxyFronted(virtualserver)
        backend = HaproxyBackend(serverfarm['id'])
        LOG.debug('Create VIP %s' % backend.name)
        self.remote_interface.add_ip(frontend)
        self.config_manager.add_frontend(frontend,
                                         backend)

    def delete_virtual_ip(self, virtualserver):
        """
        Delete vip from loadbalancer

        :param virtualserver: VirtualServer \
        - see :py:class:`balancer.db.models.VirtualServer`
        """
        LOG.debug('Delete VIP')
        if not bool(virtualserver['id']):
            LOG.error('Virtualserver name is empty')
            return
        frontend = HaproxyFronted(virtualserver)
        #Check ip for using in the another frontend
        if not (self.config_manager.
                find_string_in_any_block(frontend.bind_address,
                                         'frontend')):
            LOG.debug('ip %s is not used in any '
                         'frontend, deleting it from remote interface' %
                         frontend.bind_address)
            self.remote_interface.del_ip(frontend)
        self.config_manager.delete_block(frontend)

    def get_statistics(self, serverfarm, rserver):
        # TODO: Need to check work of this function with real device
        out = self.remote_socket.get_statistics(serverfarm['id'],
                                                rserver['id'])
        statistics = {}
        if out:
            status_line = out.split(",")
            stat_count = len(status_line)
            statistics['weight'] = status_line[18] if stat_count > 18 else ''
            statistics['state'] = status_line[17] if stat_count > 17 else ''
            statistics['connCurrent'] = (status_line[4] if stat_count > 4
                                         else '')
            statistics['connTotal'] = status_line[7] if stat_count > 7 else ''
            statistics['connFail'] = status_line[13] if stat_count > 13 else ''
            statistics['connMax'] = status_line[5] if stat_count > 5 else ''
            statistics['connRateLimit'] = (status_line[34] if stat_count > 34
                                           else '')
            statistics['bandwRateLimit'] = (status_line[35] if stat_count > 35
                                            else '')
        return statistics

    def suspend_real_server(self, serverfarm, rserver):
        """
        Put node into inactive state (suspend)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        self._operationWithRServer(serverfarm, rserver, 'suspend')

    def activate_real_server(self, serverfarm, rserver):
        """
        Put node into active state (activate)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param rserver: Server \
        - see :py:class:`balancer.db.models.Server`
        """
        self._operationWithRServer(serverfarm, rserver, 'activate')

    def _operationWithRServer(self, serverfarm, rserver, type_of_operation):
        haproxy_rserver = HaproxyRserver(rserver)
        haproxy_serverfarm = HaproxyBackend(serverfarm['id'])

        if type_of_operation == 'suspend':
            self.config_manager.enable_rserver(haproxy_serverfarm.name,
                                               haproxy_rserver.name, False)
            self.remote_socket.suspend_server(haproxy_serverfarm, rserver)
        elif type_of_operation == 'activate':
            self.config_manager.enable_rserver(haproxy_serverfarm.name,
                                               haproxy_rserver.name, True)
            self.remote_socket.activate_server(haproxy_serverfarm, rserver)

    def create_server_farm(self, serverfarm, predictor):
        """
        Create a new loadbalancer (server farm)

        :param serverfarm: ServerFarm \
        - see :py:class:`balancer.db.models.ServerFarm`
        :param predictor: Predictor \
        - see :py:class:`balancer.db.models.Predictor`
        """
        if not bool(serverfarm['id']):
            LOG.error('Serverfarm name is empty')
            return
        haproxy_serverfarm = HaproxyBackend(serverfarm['id'])

        if isinstance(predictor, list):
            predictor = predictor[0]

        predictor_type = predictor['type'].upper()
        algorithm = self.algorithms.get(predictor_type)
        if algorithm is not None:
            haproxy_serverfarm.balance = algorithm
        else:
            LOG.warning("Unknown algorithm %r, used default value %r.",
                           predictor_type, self.default_algorithm)
            haproxy_serverfarm.balance = self.default_algorithm

        self.config_manager.add_backend(haproxy_serverfarm)

    def delete_server_farm(self, serverfarm):
        """
        Delete a load balancer (server farm)
        """
        if not bool(serverfarm['id']):
            LOG.error('Serverfarm name is empty')
            return
        haproxy_serverfarm = HaproxyBackend(serverfarm['id'])

        self.config_manager.delete_block(haproxy_serverfarm)

    def finalize_config(self, good):
        """
           Store config on the haproxy VM
        """
        if good:
            if self.config_manager.deploy_config():
                if not self.remote_service.restart():
                    LOG.error("Failed to restart haproxy")

        self._remote_ctrl.close()
        return True

    def get_capabilities(self):
        capabilities = {}
        capabilities['algorithms'] = list(self.algorithms.keys())
        capabilities['protocols'] = ['HTTP', 'TCP']
        return capabilities

########NEW FILE########
__FILENAME__ = remote_control
import logging
import paramiko


LOG = logging.getLogger(__name__)


class RemoteControl(object):
    def __init__(self, device_ref):
        self.host = device_ref['ip']
        self.user = device_ref['user']
        self.password = device_ref['password']
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.closed = True

    def open(self):
        if self.closed:
            self._ssh.connect(self.host, username=self.user,
                              password=self.password)
            self.closed = False

    def close(self):
        if not self.closed:
            self._ssh.close()
            self.closed = True

    def perform(self, command):
        self.open()
        LOG.debug('performing command: {0}'.format(command))
        stdout, stderr = self._ssh.exec_command(command)[1:]
        status = stdout.channel.recv_exit_status()
        out = stdout.read()
        err = stderr.read()
        LOG.debug('command exit status: {0}, stdout: {1}, stderr: {2}'
                  .format(status, out, err))

        return status, out, err

    def get_file(self, remote_path, local_path):
        self.open()
        LOG.debug('Copying remote file {0} to local {1}'.format(remote_path,
                                                                local_path))
        sftp = self._ssh.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        return True

    def put_file(self, local_path, remote_path):
        self.open()

        LOG.debug('Copying local file {0} to remote {1}'.format(local_path,
                                                                remote_path))
        sftp = self._ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        return True


class RemoteService(object):
    '''
    Operations with haproxy daemon
    '''
    def __init__(self, remote_ctrl):
        self.remote_ctrl = remote_ctrl

    def start(self):
        LOG.debug('Starting service haproxy')
        return self.remote_ctrl.perform('sudo service haproxy start')[0] == 0

    def stop(self):
        LOG.debug('Stopping service haproxy')
        return self.remote_ctrl.perform('sudo service haproxy stop')[0] == 0

    def restart(self):
        LOG.debug('Restarting haproxy')
        status = self.remote_ctrl.perform('sudo haproxy'
                              ' -f /etc/haproxy/haproxy.cfg'
                              ' -p /var/run/haproxy.pid'
                              ' -sf $(cat /var/run/haproxy.pid)')[0]

        return status == 0


class RemoteInterface(object):
    def __init__(self, device_ref, remote_ctrl):
        device_extra = device_ref.get('extra') or {}
        self.interface = device_extra.get('interface') or 'eth0'
        self.remote_ctrl = remote_ctrl

    def add_ip(self, frontend):
        self.IP = frontend.bind_address
        LOG.debug('Trying to add IP-%s to inteface %s' %
                  (self.IP,  self.interface))
        ssh_out = self.remote_ctrl.perform('ip addr show dev %s' %
                                           self.interface)[1]
        if ssh_out.find(self.IP) < 0:
            self.remote_ctrl.perform('sudo ip addr add %s/32 dev %s' %
                                     (self.IP, self.interface))
            LOG.debug('Added ip %s to inteface %s' %
                      (self.IP, self.interface))
        else:
            LOG.debug('Remote ip %s is already configured on the %s' %
                      (self.IP, self.interface))
        return True

    def del_ip(self, frontend):
        self.IP = frontend.bind_address
        ssh_out = self.remote_ctrl.perform('ip addr show dev %s' %
                                           (self.interface))[1]
        if  ssh_out.find(self.IP) >= 0:
            LOG.debug('Remote delete ip %s from inteface %s' %
                                    (self.IP, self.interface))
            self.remote_ctrl.perform('sudo ip addr del %s/32 dev %s' %
                                     (self.IP, self.interface))
        else:
            LOG.debug('Remote ip %s is not configured on the %s' %
                                    (self.IP, self.interface))
        return True


class RemoteSocketOperation(object):
    '''
    Remote operations via haproxy socket
    '''
    def __init__(self, device_ref, remote_ctrl):
        device_extra = device_ref.get('extra') or {}
        self.interface = device_extra.get('interface') or 'eth0'
        self.haproxy_socket = device_extra.get('socket') or '/tmp/haproxy.sock'
        self.remote_ctrl = remote_ctrl

    def suspend_server(self, backend, rserver):
        self._operation_with_server_via_socket('disable', backend.name,
                                               rserver['id'])
        return True

    def activate_server(self, backend, rserver):
        self._operation_with_server_via_socket('enable', backend.name,
                                                rserver['id'])
        return True

    def _operation_with_server_via_socket(self, operation, backend_name,
                                          server_name):
        ssh_out = self.remote_ctrl.perform(
                'echo %s server %s/%s | sudo socat stdio unix-connect:%s' %
                (operation,  backend_name,
                 server_name, self.haproxy_socket))[1]
        if  ssh_out == "":
            out = 'ok'
        else:
            out = 'is not ok'
        LOG.debug('Disable server %s/%s. Result is "%s"' %
                      (backend_name, server_name, out))

    def get_statistics(self, backend_name, server_name):
        """
            Get statistics from rserver / server farm
            for all server farms use BACKEND as self.rserver_name
        """
        ssh_out = self.remote_ctrl.perform(
           'echo show stat | sudo socat stdio unix-connect:%s | grep %s,%s' %
            (self.haproxy_socket, backend_name, server_name))[1]
        LOG.debug('Get statistics about reserver %s/%s.'
                    ' Result is \'%s\' ', backend_name, ssh_out)
        return ssh_out

########NEW FILE########
__FILENAME__ = exception
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""Balancer base exception handling."""

import webob.exc as exception


class NotFound(exception.HTTPNotFound):
    message = 'Resource not found.'

    def __init__(self, message=None, **kwargs):
        super(NotFound, self).__init__(message)
        self.kwargs = kwargs


class DeviceNotFound(NotFound):
    message = 'Device not found'


class NoValidDevice(NotFound):
    message = 'Suitable device not found'


class LoadBalancerNotFound(NotFound):
    message = 'LoadBalancer not found'


class ProbeNotFound(NotFound):
    message = 'Probe not found'


class StickyNotFound(NotFound):
    message = 'Sticky not found'


class ServerNotFound(NotFound):
    message = 'Server not found'


class ServerFarmNotFound(NotFound):
    message = 'Server Farm not found'


class PredictorNotFound(NotFound):
    message = 'Predictor not found'


class VirtualServerNotFound(NotFound):
    message = 'Virtual Server not found'


class DeviceConflict(exception.HTTPConflict):
    message = 'Conflict while device deleting'

    def __init__(self, message=None, **kwargs):
        super(DeviceConflict, self).__init__(message)
        self.kwargs = kwargs

########NEW FILE########
__FILENAME__ = test_acedriver
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import unittest
import urllib2
import mock

from balancer.drivers.cisco_ace.ace_driver import AceDriver

dev = {'ip': '10.4.15.21', 'port': '10443', \
       'user': 'admin', 'password': 'cisco123'}

conf = []

rs_host = {'type': 'host', 'id': 'LB_test_rs01', \
          'address': '172.250.0.1', 'state': 'inservice'}
rs_host['extra'] = {'description': 'Created by test. RS type Host', \
                  'minCon': '2000000', 'maxCon': '3000000', \
                  'weight': '7', 'rateBandwidth': '500000', \
                  'rateConnection': '5000', 'failOnAll': 'True', \
                  'port': '80', 'cookieStr': 'stringcookie', \
                  'state': 'In Service'}

rs_redirect = {'type': 'redirect', 'id': 'LB_test_rs02', \
              'address': '172.250.0.2', 'state': 'outofservice'}
rs_redirect['extra'] = {'description': 'Created by test. RS type Redirect', \
                      'minCon': '2000000', 'maxCon': '3000000', \
                      'weight': '1', 'rateBandwidth': '100000', \
                      'rateConnection': '999', 'redirectionCode': '301', \
                      'webHostRedir': 'www.cisco.com', 'port': '100500'}

rs_test3 = {'type': 'host', 'id': 'LB_test_rs03', \
           'address': '10.4.15.231', 'state': 'outofservice'}
rs_test3['extra'] = {'description': 'Created by test. RS type Host', \
                   'weight': '70', 'rateBandwidth': '5000', \
                   'rateConnection': '5000', \
                   'port': '809', 'cookieStr': 'stringcookie'}

rs_test4 = {'type': 'redirect', 'id': 'LB_test_rs02', \
           'address': '172.250.0.2', 'state': 'inservice'}
rs_test4['extra'] = {'description': 'Created by test. RS type Redirect', \
                   'weight': '100', 'redirectionCode': '301', \
                   'webHostRedir': 'www.cisco.com'}

probe_dns = {'type': 'DNS', 'id': 'LB_test_ProbeDNS'}
probe_dns['extra'] = {'description': 'Created by test. Probe type DNS', \
                    'probeInterval': '2', 'passDetectInterval': '2', \
                    'failDetect': '1', 'domainName': 'test-org', \
                    'passDetectCount': '1', 'receiveTimeout': '1', \
                    'destIP': '1.1.1.1', 'port': '1'}

probe_echoUDP = {'type': 'ECHO-UDP', 'id': 'LB_test_ProbeECHOUDP'}
probe_echoUDP['extra'] = {'description': 'Created by test. ', \
                        'probeInterval': '65535', \
                        'passDetectInterval': '65535', \
                        'failDetect': '65535', 'sendData': 'SendingData', \
                        'passDetectCount': '65535', \
                        'receiveTimeout': '65535', 'destIP': '1.1.1.1', \
                        'isRouted': 'True', 'port': '65535'}

probe_echoTCP = {'type': 'ECHO-TCP', 'id': 'LB_test_ProbeECHOTCP'}
probe_echoTCP['extra'] = {'description': 'Probe type ECHOTCP', \
                        'probeInterval': '15', 'passDetectInterval': '60', \
                        'failDetect': '3', 'sendData': 'SendingData', \
                        'passDetectCount': '3', 'receiveTimeout': '10', \
                        'destIP': '1.1.1.1', 'isRouted': 'True', \
                        'port': '500', 'tcpConnTerm': 'True', \
                        'openTimeout': '10'}

probe_finger = {'type': 'FINGER', 'id': 'LB_test_ProbeFinger'}
probe_finger['extra'] = {'description': 'Probe type Finger', \
                       'probeInterval': '20', \
                       'passDetectInterval': '50', \
                       'failDetect': '5', 'sendData': 'SendingData', \
                       'passDetectCount': '3', 'receiveTimeout': '10', \
                       'destIP': '1.1.1.1', 'isRouted': 'True', \
                       'port': '501', 'openTimeout': '1'}

probe_ftp = {'type': 'FTP', 'id': 'LB_test_ProbeFTP'}
probe_ftp['extra'] = {'description': 'Created by test. Probe type FTP', \
                    'probeInterval': '20', 'passDetectInterval': '50', \
                    'failDetect': '5', 'passDetectCount': '5', \
                    'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                    'isRouted': 'True', 'port': '502', \
                    'tcpConnTerm': 'True', 'openTimeout': '65535'}

probe_http = {'type': 'HTTP', 'id': 'LB_test_ProbeHTTP'}
probe_http['extra'] = {'description': 'Created by test. Probe type HTTP', \
                     'probeInterval': '20', 'passDetectInterval': '50', \
                     'failDetect': '5', 'port': '80', \
                     'requestMethodType': 'GET', 'destIP': '1.1.1.1', \
                     'requestHTTPurl': 'cisco.com', 'isRouted': 'True', \
                     'passDetectCount': '5', 'tcpConnTerm': 'True', \
                     'probe_http.receiveTimeout': '15', \
                     'appendPortHostTag': 'True', 'openTimeout': '2', \
                     'userName': 'user', 'password': 'password', \
                     'expectRegExp': '.*', 'expectRegExpOffset': '1', \
                     'hash': 'True', \
                     'hashString': '01020304010203040102030401020304'}

probe_https = {'type': 'HTTPS', 'id': 'LB_test_ProbeHTTPS'}
probe_https['extra'] = {'description': 'Created by test. Probe type HTTPS', \
                      'probeInterval': '20', 'passDetectInterval': '50', \
                      'failDetect': '5', 'port': '8080', \
                      'requestMethodType': 'HEAD', \
                      'requestHTTPurl': 'cisco.com', 'SSLversion': 'ALL', \
                      'passDetectCount': '5', 'receiveTimeout': '15', \
                      'destIP': '1.1.1.1', 'isRouted': 'True', \
                      'tcpConnTerm': 'True', 'appendPortHostTag': 'True', \
                      'openTimeout': '2', 'userName': 'user', \
                      'password': 'password', 'expectRegExp': '.*', \
                      'expectRegExpOffset': '1', 'hash': 'True', \
                      'hashString': '01020304010203040102030401020304'}

probe_icmp = {'type': 'ICMP', 'id': 'LB_test_ProbeICMP'}
probe_icmp['extra'] = {'description': 'Created by test. Probe type ICMP', \
                     'probeInterval': '2', 'passDetectInterval': '2', \
                     'failDetect': '1', 'passDetectCount': '1', \
                     'receiveTimeout': '1', 'destIP': '1.1.1.1'}

probe_imap = {'type': 'IMAP', 'id': 'LB_test_ProbeIMAP'}
probe_imap['extra'] = {'description': 'Created by test. Probe type IMAP', \
                     'probeInterval': '20', 'passDetectInterval': '50', \
                     'failDetect': '5', 'userName': 'user', \
                     'password': 'password', 'maibox': 'dhl.org',
                     'requestCommand': 'request', 'passDetectCount': '5', \
                     'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                     'isRouted': 'True', 'port': '503', \
                     'tcpConnTerm': 'True', 'openTimeout': '60'}

probe_pop = {'type': 'POP', 'id': 'LB_test_ProbePOP'}
probe_pop['extra'] = {'description': 'Created by test. Probe type POP', \
                    'probeInterval': '20', 'passDetectInterval': '50', \
                    'failDetect': '5', 'userName': 'user', \
                    'password': 'password', 'requestCommand': 'request', \
                    'passDetectCount': '5', 'receiveTimeout': '15', \
                    'destIP': '1.1.1.1', 'isRouted': 'True', \
                    'port': '504', 'tcpConnTerm': 'True', \
                    'openTimeout': '60'}

probe_radius = {'type': 'RADIUS', 'id': 'LB_test_ProbeRADIUS'}
probe_radius['extra'] = {'description': 'Probe type Radius', \
                       'probeInterval': '30', \
                       'passDetectInterval': '100', \
                       'failDetect': '5', 'userSecret': 'topsecret', \
                       'userName': 'user', 'password': 'password', \
                       'requestCommand': 'request', \
                       'passDetectCount': '5', 'receiveTimeout': '15', \
                       'destIP': '1.1.1.1', 'isRouted': 'True', \
                       'port': '505', 'NASIPaddr': '2.2.2.2'}

probe_rtsp = {'type': 'RTSP', 'id': 'LB_test_ProbeRTSP'}
probe_rtsp['extra'] = {'description': 'Created by test. Probe type RTSP', \
                     'probeInterval': '30', 'passDetectInterval': '100', \
                     'failDetect': '5', 'requestURL': 'cisco.com', \
                     'requareHeaderValue': 'headervalue', \
                     'proxyRequareHeaderValue': 'requarevalue', \
                     'requestMethodType': 'True', \
                     'passDetectCount': '5', 'receiveTimeout': '15', \
                     'destIP': '1.1.1.1', 'port': '506', \
                     'tcpConnTerm': 'True', 'openTimeout': '60'}

probe_scripted = {'type': 'SCRIPTED', 'id': 'LB_test_ProbeSCRIPTED'}
probe_scripted['extra'] = {'description': 'Probe type SCRIPTED', \
                        'probeInterval': '30', \
                        'passDetectInterval': '100', \
                        'failDetect': '5', 'port': '507', \
                        'scriptName': 'script.py', 'scriptArgv': 'a1', \
                        'passDetectCount': '5', 'receiveTimeout': '15', \
                        'copied': 'True', 'proto': 'FTP', \
                        'userName': 'user', 'password': 'password', \
                        'sourceFileName': 'root/script.py'}

probe_sipUDP = {'type': 'SIP-UDP', 'id': 'LB_test_ProbeSIPUDP'}
probe_sipUDP['extra'] = {'description': 'Probe type SIPUDP', \
                       'probeInterval': '30', \
                       'passDetectInterval': '100', 'failDetect': '5', \
                       'passDetectCount': '5', 'receiveTimeout': '15', \
                       'destIP': '1.1.1.1', 'port': '508', \
                       'rport': 'True', 'expectRegExp': '.*', \
                       'expectRegExpOffset': '4000'}

probe_sipTCP = {'type': 'SIP-TCP', 'id': 'LB_test_ProbeSIPTCP'}
probe_sipTCP['extra'] = {'description': 'Probe type SIPTCP', \
                       'probeInterval': '30', \
                       'passDetectInterval': '100', \
                       'failDetect': '5', 'passDetectCount': '5', \
                       'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                       'port': '509', 'tcpConnTerm': 'True', \
                       'openTimeout': '60', 'expectRegExp': '.*', \
                       'expectRegExpOffset': '4000'}

probe_smtp = {'type': 'SMTP', 'id': 'LB_test_ProbeSMTP'}
probe_smtp['extra'] = {'description': 'Created by test. Probe type SMTP', \
                     'probeInterval': '30', 'passDetectInterval': '100', \
                     'failDetect': '5', 'passDetectCount': '5', \
                     'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                     'isRouted': 'True', 'port': '510', \
                     'tcpConnTerm': 'True', 'openTimeout': '60'}

probe_snmp = {'type': 'SNMP', 'id': 'LB_test_ProbeSNMP'}
probe_snmp['extra'] = {'description': 'Created by test. Probe type SNMP', \
                     'probeInterval': '30', 'passDetectInterval': '100', \
                     'failDetect': '5', 'SNMPComm': 'public', \
                     'passDetectCount': '5', 'receiveTimeout': '15', \
                     'destIP': '1.1.1.1', 'isRouted': 'True', \
                     'port': '511', 'tcpConnTerm': 'True', \
                     'openTimeout': '60'}

probe_tcp = {'type': 'TCP', 'id': 'LB_test_ProbeTCP'}
probe_tcp['extra'] = {'description': 'Created by test. Probe type TCP', \
                    'probeInterval': '20', 'passDetectInterval': '50', \
                    'failDetect': '5', 'port': '512', \
                    'sendData': 'SendingData', 'passDetectCount': '5', \
                    'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                    'isRouted': 'True', 'tcpConnTerm': 'True', \
                    'openTimeout': '60', 'expectRegExp': '.*', \
                    'expectRegExpOffset': '500'}

probe_telnet = {'type': 'TELNET', 'id': 'LB_test_ProbeTELNET'}
probe_telnet['extra'] = {'description': 'Probe type TELNET', \
                       'probeInterval': '20', 'passDetectInterval': '50', \
                       'failDetect': '5', 'passDetectCount': '5', \
                       'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                       'isRouted': 'True', 'port': '513', \
                       'tcpConnTerm': 'True', 'openTimeout': '60'}

probe_udp = {'type': 'UDP', 'id': 'LB_test_ProbeUDP'}
probe_udp['extra'] = {'description': 'Created by test. Probe type UDP', \
                    'probeInterval': '20', 'passDetectInterval': '50', \
                    'failDetect': '5', 'port': '514', \
                    'sendData': 'SendingData', 'passDetectCount': '5', \
                    'receiveTimeout': '15', 'destIP': '1.1.1.1', \
                    'isRouted': 'True', 'expectRegExp': '.*', \
                    'expectRegExpOffset': '500'}

probe_vm = {'type': 'VM', 'id': 'LB_test_ProbeVM'}
probe_vm['extra'] = {'description': 'Created by test. Probe type VM', \
                   'probeInterval': '600', 'maxCPUburstThresh': '97', \
                   'minCPUburstThresh': '97', 'maxMemBurstThresh': '97', \
                   'minMemBurstThresh': '97'}

predictor = {'id': 'test_pr', 'type': 'roudrobin'}
predictor['extra'] = {}

predictor_bandwidth = {'id': 'test_pr', 'type': 'leastbandwidth'}
predictor_bandwidth['extra'] = {'accessTime': '10'}

predictor_connections = {'id': 'test_pr', 'type': 'leastconnections'}
predictor_connections['extra'] = {'slowStartDur': '10'}

predictor_loaded = {'id': 'test_pr', 'type': 'leastloaded'}
predictor_loaded['extra'] = {'snmpProbe': 'unitTest-snmpProbe'}

sf_host = {'type': 'Host', 'id': 'LB_test_sfarm01'}
sf_host['extra'] = {'description': 'Created by test. Sfarm type Host', \
                  'failAction': 'reassign', 'failOnAll': 'True', \
                  'inbandHealthCheck': 'Remove', \
                  'connFailureThreshCount': '5', 'resetTimeout': '200', \
                  'resumeService': '40', 'transparent': 'True', \
                  'dynamicWorkloadScale': 'burst', \
                  'VMprobe': 'AAA-utit-test',
                  'partialThreshPercentage': '11', 'backInservice': '22'}

sf_redirect = {'type': 'Redirect', 'id': 'LB_test_sfarm02'}
sf_redirect['extra'] = {'description': 'SFarm type Redirect', \
                      'failAction': 'purge'}

sticky_httpContent = {'type': 'HTTPContent', \
                    'id': 'LB_test_stickyHTTPContent'}
sticky_httpContent['extra'] = {'offset': '0', \
                            'beginPattern': 'beginpaternnn', \
                            'endPattern': 'endpaternnnn', \
                            'serverFarm': 'LB_test_sfarm01',\
                            'backupServerFarm': 'LB_test_sfarm02', \
                            'replicateOnHAPeer': 'True', \
                            'timeout': '2880', \
                            'timeoutActiveConn': 'True',
                            'sf_id': 'SF-01'}

sticky_httpCookie = {'type': 'HTTPCookie', \
                   'id': 'LB_test_stickyHTTPCookie'}
sticky_httpCookie['extra'] = {'cookieName': 'cookieshmuki', \
                           'enableInsert': 'True', \
                           'browserExpire': 'True', 'offset': '999', \
                           'length': '1000', \
                           'secondaryName': 'stickysecname', \
                           'serverFarm': 'LB_test_sfarm01', \
                           'backupServerFarm': 'LB_test_sfarm02', \
                           'replicateOnHAPeer': 'True', \
                           'timeout': '2880', \
                           'timeoutActiveConn': 'True'}

sticky_httpHeader = {'type': 'HTTPHeader', \
                   'id': 'LB_test_stickyHTTPHeader'}
sticky_httpHeader['extra'] = {'headerName': 'authorization', \
                           'offset': '50', 'length': '150', \
                           'serverFarm': 'LB_test_sfarm01', \
                           'backupServerFarm': 'LB_test_sfarm02', \
                           'replicateOnHAPeer': 'True', \
                           'timeout': '2880', \
                           'timeoutActiveConn': 'True'}

sticky_ipnetmask = {'type': 'IPNetmask', 'id': 'LB_test_stickyIPNetmask'}
sticky_ipnetmask['extra'] = {'netmask': '255.255.255.128', 'timeout': '1', \
                          'ipv6PrefixLength': '96', \
                          'addressType': 'Both', \
                          'serverFarm': 'LB_test_sfarm01', \
                          'backupServerFarm': 'LB_test_sfarm02', \
                          'replicateOnHAPeer': 'True', \
                          'timeoutActiveConn': 'True'}

sticky_v6prefix = {'type': 'v6prefix', 'id': 'LB_test_stickyV6prefix'}
sticky_v6prefix['extra'] = {'prefixLength': '96', \
                         'netmask': '255.255.255.128', \
                         'addressType': 'destination', \
                         'serverFarm': 'LB_test_sfarm01', \
                         'backupServerFarm': 'LB_test_sfarm02', \
                         'replicateOnHAPeer': 'True', \
                         'timeout': '65535', 'timeoutActiveConn': 'True'}

sticky_l4payload = {'type': 'l4payload', 'id': 'LB_test_stickyL4payload'}
sticky_l4payload['extra'] = {'offset': '50', 'length': '200', \
                          'beginPattern': 'beginpaternnn', \
                          'enableStickyForResponse': 'True', \
                          'serverFarm': 'LB_test_sfarm01', \
                          'backupServerFarm': 'LB_test_sfarm02', \
                          'replicateOnHAPeer': 'True', \
                          'timeout': '2880', 'timeoutActiveConn': 'True'}

sticky_radius = {'type': 'radius', 'id': 'LB_test_stickyRadius'}
sticky_radius['extra'] = {'serverFarm': 'LB_test_sfarm01', \
                        'backupServerFarm': 'LB_test_sfarm02', \
                        'replicateOnHAPeer': 'True', 'timeout': '2880', \
                        'timeoutActiveConn': 'True'}

sticky_rtspHeader = {'type': 'RTSPHeader', \
                   'id': 'LB_test_stickyRTSPHeader'}
sticky_rtspHeader['extra'] = {'offset': '50', 'length': '200', \
                           'serverFarm': 'LB_test_sfarm01', \
                           'backupServerFarm': 'LB_test_sfarm02', \
                           'replicateOnHAPeer': 'True', \
                           'timeout': '2880', \
                           'timeoutActiveConn': 'True'}

sticky_sipHeader = {'type': 'SIPHeader', 'id': 'LB_test_stickySIPHeader'}
sticky_sipHeader['extra'] = {'serverFarm': 'LB_test_sfarm01', \
                          'backupServerFarm': 'LB_test_sfarm02', \
                          'replicateOnHAPeer': 'True',\
                          'timeout': '2880', \
                          'timeoutActiveConn': 'True'}

vip_loadbalance = {'id': 'LB_test_VIP1', 'ipVersion': 'IPv4', \
                 'address': '10.250.250.250', 'mask': '255.255.255.0'}
vip_loadbalance['extra'] = {'proto': 'TCP', 'appProto': 'HTTP', \
                         'port': '20', 'VLAN': "2",
                         'description': 'simple vip for unit test'}

vip_sticky = {'id': 'LB_test_VIP2', 'ipVersion': 'IPv4', \
             'address': '10.250.250.251', 'mask': '255.255.255.0'}
vip_sticky['extra'] = {'proto': 'TCP', 'appProto': 'HTTPS', \
                     'port': '5077', 'allVLANs': True}

vip_test = {'id': 'test3', 'ipVersion': 'IPv4', \
            'address': '10.250.250.253', 'mask': '255.255.255.0'}
vip_test['extra'] = {'proto': 'TCP', 'appProto': 'RTSP', \
            'port': '507', 'allVLANs': True}

ssl_proxy = {'id': 'ssl_proxy01', 'cert': '1.crt', 'key': 'secutity', \
            'authGroup': 'test01', 'ocspServer': '1.com', \
            'crl': 'A-test', 'crlBestEffort': True, \
            'chainGroup': '1', 'CheckPriority': 'ddffdfd'}


class Ace_DriverTestCase(unittest.TestCase):
    def setUp(self):
        urllib2.urlopen = mock.Mock()
        urllib2.urlopen().read = mock.Mock(return_value="str")
        self.driver = AceDriver(conf, dev)

    def test_01a_createRServer_typeHost(self):
        self.driver.create_real_server(rs_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_01b_createRServer_typeRedirect(self):
        self.driver.create_real_server(rs_redirect)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_01c_createRServer_typeHost(self):
        self.driver.create_real_server(rs_test3)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_01d_createRServer_typeRedirect(self):
        self.driver.create_real_server(rs_test4)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02a_createDNSProbe(self):
        self.driver.create_probe(probe_dns)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02b_createECHOUDPprobe(self):
        self.driver.create_probe(probe_echoUDP)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02c_createECHOTCPprobe(self):
        self.driver.create_probe(probe_echoTCP)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02d_createFINGERprobe(self):
        self.driver.create_probe(probe_finger)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02e_createFTPprobe(self):
        self.driver.create_probe(probe_ftp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02f_createHTTPprobe(self):
        self.driver.create_probe(probe_http)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02g_createHTTPSprobe(self):
        self.driver.create_probe(probe_https)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02h_createICMPprobe(self):
        self.driver.create_probe(probe_icmp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02i_createIMAPprobe(self):
        self.driver.create_probe(probe_imap)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02j_createPOPprobe(self):
        self.driver.create_probe(probe_pop)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02k_createRADIUSprobe(self):
        self.driver.create_probe(probe_radius)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02l_createRTSPprobe(self):
        self.driver.create_probe(probe_rtsp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02m_createSCRIPTEDprobe(self):
        self.driver.create_probe(probe_scripted)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02n_createSIPUDPprobe(self):
        self.driver.create_probe(probe_sipUDP)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02o_createSMTPprobe(self):
        self.driver.create_probe(probe_smtp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02p_createSNMPprobe(self):
        self.driver.create_probe(probe_snmp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02r_createTCPprobe(self):
        self.driver.create_probe(probe_tcp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02s_createTELNETprobe(self):
        self.driver.create_probe(probe_telnet)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02t_createUDPprobe(self):
        self.driver.create_probe(probe_udp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_02u_createVMprobe(self):
        self.driver.create_probe(probe_vm)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_03a_createServerFarm_typeHost(self):
        self.driver.create_server_farm(sf_host, predictor)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_03b_createServerFarm_typeRedirect(self):
        self.driver.create_server_farm(sf_redirect, predictor)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_03c_createServerFarm_with_predictor_leastbandwidth(self):
        self.driver.create_server_farm(sf_host, predictor_bandwidth)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_03d_createServerFarm_with_predictor_leastconnections(self):
        self.driver.create_server_farm(sf_redirect, predictor_connections)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_03e_createServerFarm_with_predictor_leastloaded(self):
        self.driver.create_server_farm(sf_redirect, predictor_loaded)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_04_addRServerToSF(self):
        self.driver.add_real_server_to_server_farm(sf_host,  rs_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_05_addProbeToSF(self):
        self.driver.add_probe_to_server_farm(sf_host, probe_http)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06a_createHTTPContentStickiness(self):
        self.driver.create_stickiness(sticky_httpContent)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06b_createHTTPCookieStickiness(self):
        self.driver.create_stickiness(sticky_httpCookie)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06c_createHTTPHeaderStickiness(self):
        self.driver.create_stickiness(sticky_httpHeader)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06d_createIPNetmaskStickiness(self):
        self.driver.create_stickiness(sticky_ipnetmask)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06e_createV6prefixStickiness(self):
        self.driver.create_stickiness(sticky_v6prefix)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06f_createL4payloadStickiness(self):
        self.driver.create_stickiness(sticky_l4payload)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06g_createRadiusStickiness(self):
        self.driver.create_stickiness(sticky_radius)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06h_createRTSPHeaderStickiness(self):
        self.driver.create_stickiness(sticky_rtspHeader)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_06i_createSIPHeaderStickiness(self):
        self.driver.create_stickiness(sticky_sipHeader)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_07a_createVIP_loadbalancer(self):
        self.driver.create_virtual_ip(vip_loadbalance, sf_host)
        self.assertTrue(urllib2.urlopen().read.call_count > 1)

    def test_07b_createVIP_sticky(self):
        self.driver.create_virtual_ip(vip_sticky, sf_redirect)
        self.assertTrue(urllib2.urlopen().read.call_count > 1)

    def test_07c_createVIP_loadbalancer(self):
        self.driver.create_virtual_ip(vip_test,  sf_host)
        self.assertTrue(urllib2.urlopen().read.call_count > 1)

    def test_08_suspendRServer(self):
        self.driver.suspend_real_server(sf_host, rs_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_08a_suspendRServerGlobal(self):
        self.driver.suspend_real_server_global(rs_redirect)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_09_activateRServer(self):
        self.driver.activate_real_server(sf_host, rs_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_09a_activateRServerGlobal(self):
        self.driver.activate_real_server_global(rs_redirect)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_10a_deleteVIP_loadbalance(self):
        self.driver.delete_virtual_ip(vip_loadbalance)
        self.assertTrue(urllib2.urlopen().read.call_count > 1)

    def test_10b_deleteVIP_sticky(self):
        self.driver.delete_virtual_ip(vip_sticky)
        self.assertTrue(urllib2.urlopen().read.call_count > 1)

    def test_11a_deleteHTTPContentStickiness(self):
        self.driver.delete_stickiness(sticky_httpContent)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11b_deleteHTTPCookieStickiness(self):
        self.driver.delete_stickiness(sticky_httpCookie)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11c_deleteHTTPHeaderStickiness(self):
        self.driver.delete_stickiness(sticky_httpHeader)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11d_deleteIPNetmaskStickiness(self):
        self.driver.delete_stickiness(sticky_ipnetmask)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11e_deleteV6prefixStickiness(self):
        self.driver.delete_stickiness(sticky_v6prefix)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11f_deleteL4payloadStickiness(self):
        self.driver.delete_stickiness(sticky_l4payload)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11g_deleteRadiusStickiness(self):
        self.driver.delete_stickiness(sticky_radius)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11h_deleteRTSPHeaderStickiness(self):
        self.driver.delete_stickiness(sticky_rtspHeader)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_11i_deleteSIPHeaderStickiness(self):
        self.driver.delete_stickiness(sticky_sipHeader)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_12_deleteProbeFromSF(self):
        self.driver.delete_probe_from_server_farm(sf_host, probe_http)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_13_deleteRServerFromSF(self):
        self.driver.delete_real_server_from_server_farm(sf_host, rs_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_14a_deleteServerFarm_typeHost(self):
        self.driver.delete_server_farm(sf_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_14b_deleteServerFarm_typeRedirect(self):
        self.driver.delete_server_farm(sf_redirect)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15a_deleteDNSProbe(self):
        self.driver.delete_probe(probe_dns)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15b_deleteECHOUDPprobe(self):
        self.driver.delete_probe(probe_echoUDP)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15c_deleteECHOTCPprobe(self):
        self.driver.delete_probe(probe_echoTCP)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15d_deleteFINGERprobe(self):
        self.driver.delete_probe(probe_finger)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15e_deleteFTPprobe(self):
        self.driver.delete_probe(probe_ftp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15f_deleteHTTPprobe(self):
        self.driver.delete_probe(probe_http)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15g_deleteHTTPSprobe(self):
        self.driver.delete_probe(probe_https)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15h_deleteICMPprobe(self):
        self.driver.delete_probe(probe_icmp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15i_deleteIMAPprobe(self):
        self.driver.delete_probe(probe_imap)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15j_deletePOPprobe(self):
        self.driver.delete_probe(probe_pop)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15k_deleteRADIUSprobe(self):
        self.driver.delete_probe(probe_radius)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15l_deleteRTSPprobe(self):
        self.driver.delete_probe(probe_rtsp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15m_deleteSCRIPTEDprobe(self):
        self.driver.delete_probe(probe_scripted)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15n_deleteSIPUDPprobe(self):
        self.driver.delete_probe(probe_sipUDP)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15o_deleteSMTPprobe(self):
        self.driver.delete_probe(probe_smtp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15p_deleteSNMPprobe(self):
        self.driver.delete_probe(probe_snmp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15r_deleteTCPprobe(self):
        self.driver.delete_probe(probe_tcp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15s_deleteTELNETprobe(self):
        self.driver.delete_probe(probe_telnet)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15t_deleteUDPprobe(self):
        self.driver.delete_probe(probe_udp)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_15u_deleteVMprobe(self):
        self.driver.delete_probe(probe_vm)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_16a_deleteRServer_typeHost(self):
        self.driver.delete_real_server(rs_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_16b_deleteRServer_typeRedirect(self):
        self.driver.delete_real_server(rs_redirect)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_get_statistics(self):
        self.driver.get_statistics(sf_host)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_create_ssl_proxy(self):
        self.driver.create_ssl_proxy(ssl_proxy)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_delete_ssl_proxy(self):
        self.driver.delete_ssl_proxy(ssl_proxy)
        self.assertTrue(urllib2.urlopen().read.call_count == 1)

    def test_get_capabilities(self):
        protocols = ['HTTP', 'TCP', 'HTTPS', 'RTSP', \
                     'SIP-TCP', 'SIP-UDP', 'UDP', \
                     'FTP', 'Generic', 'RDP', 'DNS', \
                     'RADIUS', ]
        algorithms = list(self.driver.algorithms.keys())

        self.assertTrue(self.driver.algorithms)
        self.assertTrue(self.driver.default_algorithm)

        test = self.driver.get_capabilities()

        self.assertListEqual(test['algorithms'], algorithms)
        self.assertListEqual(test['protocols'], protocols)

########NEW FILE########
__FILENAME__ = test_api
import unittest
import mock
import logging
import balancer.exception as exception
from openstack.common import wsgi
from balancer.api.v1 import loadbalancers
from balancer.api.v1 import nodes
from balancer.api.v1 import vips
from balancer.api.v1 import probes
from balancer.api.v1 import stickies
from balancer.api.v1 import devices
from balancer.api.v1 import router

LOG = logging.getLogger()


class TestLoadBalancersController(unittest.TestCase):
    def setUp(self):
        super(TestLoadBalancersController, self).setUp()
        self.conf = mock.Mock()
        self.controller = loadbalancers.Controller(self.conf)
        self.req = mock.Mock(spec=['headers'])

    def code_assert(self, code, func):
        self.assertTrue(hasattr(func, "wsgi_code"),
                "has not redifined HTTP status code")
        self.assertTrue(func.wsgi_code == code,
                "incorrect HTTP status code")

    @mock.patch('balancer.core.api.lb_find_for_vm', autospec=True)
    def test_find_lb_for_vm(self, mock_lb_find_for_vm):
        mock_lb_find_for_vm.return_value = 'foo'
        resp = self.controller.findLBforVM(self.req, 'fake_tenant', '123')
        self.assertTrue(mock_lb_find_for_vm.called)
        mock_lb_find_for_vm.assert_called_once_with(self.conf,
                'fake_tenant', '123')
        self.assertEqual(resp, {'loadbalancers': 'foo'})

    @mock.patch('balancer.core.api.lb_get_index', autospec=True)
    def test_index(self, mock_lb_get_index):
        mock_lb_get_index.return_value = 'foo'
        resp = self.controller.index(self.req, 'fake_tenant')
        self.assertTrue(mock_lb_get_index.called)
        mock_lb_get_index.assert_called_once_with(self.conf, 'fake_tenant')
        self.assertEqual(resp, {'loadbalancers': 'foo'})

    @mock.patch('balancer.core.api.create_lb', autospec=True)
    def test_create(self, mock_create_lb):
        mock_create_lb.return_value = '1'
        resp = self.controller.create(self.req, 'fake_tenant', {})
        self.assertTrue(mock_create_lb.called)
        mock_create_lb.assert_called_once_with(
                    self.conf,
                    {'tenant_id': 'fake_tenant'})
        self.assertEqual(resp, {'loadbalancer': {'id': '1'}})
        self.code_assert(202, self.controller.create)

    @mock.patch('balancer.core.api.delete_lb', autospec=True)
    def test_delete(self, mock_delete_lb):
        resp = self.controller.delete(self.req, 'fake_tenant', 1)
        self.assertTrue(mock_delete_lb.called)
        self.code_assert(204, self.controller.delete)
        mock_delete_lb.assert_called_once_with(self.conf, 'fake_tenant', 1)
        self.assertEqual(resp, None)

    @mock.patch('balancer.core.api.lb_get_data', autospec=True)
    def test_show(self, mock_lb_get_data):
        mock_lb_get_data.return_value = 'foo'
        resp = self.controller.show(self.req, 'fake_tenant', 1)
        self.assertTrue(mock_lb_get_data.called)
        mock_lb_get_data.assert_called_once_with(self.conf, 'fake_tenant', 1)
        self.assertEqual(resp, {'loadbalancer': 'foo'})

    @mock.patch('balancer.core.api.lb_show_details', autospec=True)
    def test_details(self, mock_lb_show_details):
        mock_lb_show_details.return_value = 'foo'
        resp = self.controller.details(self.req, 'fake_tenant', 1)
        self.assertTrue(mock_lb_show_details.called)
        mock_lb_show_details.assert_called_once_with(self.conf,
                'fake_tenant', 1)
        self.assertEqual('foo', resp)

    @mock.patch('balancer.core.api.update_lb', autospec=True)
    def test_update(self, mock_update_lb):
        resp = self.controller.update(self.req, 'fake_tenant', 1, {})
        self.assertTrue(mock_update_lb.called)
        self.code_assert(202, self.controller.update)
        mock_update_lb.assert_called_once_with(self.conf, 'fake_tenant', 1, {})
        self.assertEquals(resp, {"loadbalancer": {"id": 1}})


class TestNodesController(unittest.TestCase):
    def setUp(self):
        super(TestNodesController, self).setUp()
        self.conf = mock.Mock()
        self.controller = nodes.Controller(self.conf)
        self.req = mock.Mock(spec=['headers'])

    def code_assert(self, code, func):
        self.assertTrue(hasattr(func, "wsgi_code"),
                "has not redifined HTTP status code")
        self.assertTrue(func.wsgi_code == code,
                "incorrect HTTP status code")

    @mock.patch('balancer.core.api.lb_add_nodes', autospec=True)
    def test_create(self, mock_lb_add_nodes):
        mock_lb_add_nodes.return_value = 'foo'
        body = {'nodes': 'foo'}
        resp = self.controller.create(self.req, 'fake_tenant', 1, body)
        self.assertTrue(mock_lb_add_nodes.called)
        mock_lb_add_nodes.assert_called_once_with(self.conf,
                'fake_tenant', 1, 'foo')
        self.assertEqual(resp, {'nodes': 'foo'})

    @mock.patch('balancer.core.api.lb_show_nodes', autospec=True)
    def test_index(self, mock_lb_show_nodes):
        mock_lb_show_nodes.return_value = 'foo'
        resp = self.controller.index(self.req, 'fake_tenant', 1)
        self.assertTrue(mock_lb_show_nodes.called)
        mock_lb_show_nodes.assert_called_once_with(self.conf, 'fake_tenant', 1)
        self.assertEqual(resp, {'nodes': 'foo'})

    @mock.patch("balancer.db.api.server_get")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_show(self, mock_unpack, mock_server_get):
        mock_server_get.return_value = ['foo']
        mock_unpack.return_value = 'foo'
        resp = self.controller.show(self.req, 'fake_tenant', '123', '123')
        self.assertTrue(mock_server_get.called)
        self.assertTrue(mock_unpack.called)
        mock_server_get.assert_called_once_with(self.conf,
                '123', '123', tenant_id='fake_tenant')
        mock_unpack.assert_called_once_with(['foo'])
        self.assertEqual(resp, {'node': 'foo'})

    @mock.patch('balancer.core.api.lb_delete_node', autospec=True)
    def test_delete(self, mock_lb_delete_node):
        resp = self.controller.delete(self.req, 'fake_tenant', 1, 1)
        self.assertTrue(mock_lb_delete_node.called)
        mock_lb_delete_node.assert_called_once_with(self.conf,
                'fake_tenant', 1, 1)
        self.assertEqual(resp, None)
        self.code_assert(204, self.controller.delete)

    @mock.patch('balancer.core.api.lb_change_node_status', autospec=True)
    def test_change_node_status(self, mock_lb_change_node_status):
        mock_lb_change_node_status.return_value = {'nodeID': '1',
                                                   'status': 'Foostatus'}
        resp = self.controller.changeNodeStatus(self.req,
                'fake_tenant', 1, 1, 'Foostatus', {})
        self.assertTrue(mock_lb_change_node_status.called)
        mock_lb_change_node_status.assert_called_once_with(self.conf,
                'fake_tenant', 1, 1, 'Foostatus')
        self.assertFalse(hasattr(
            self.controller.changeNodeStatus, "wsgi_code"),
            "has not redifined HTTP status code")
        self.assertEqual(resp, {"node": {'nodeID': '1',
                                         'status': 'Foostatus'}})

    @mock.patch('balancer.core.api.lb_update_node', autospec=True)
    def test_update(self, mock_lb_update_node):
        req_kwargs = {'tenant_id': 'fake_tenant',
                      'lb_id': '1',
                      'node_id': '1',
                      'body': {'node': 'node'}}
        mock_lb_update_node.return_value = {'nodeID': '1'}
        resp = self.controller.update(self.req, **req_kwargs)
        self.assertTrue(mock_lb_update_node.called)
        mock_lb_update_node.assert_called_once_with(self.conf,
                'fake_tenant', '1', '1', {'node': 'node'})
        self.assertFalse(hasattr(self.controller.update, "wsgi_code"),
            "has not redifined HTTP status code")
        self.assertEqual(resp, {"node": {'nodeID': '1'}})


class TestVIPsController(unittest.TestCase):
    def setUp(self):
        super(TestVIPsController, self).setUp()
        self.conf = mock.Mock()
        self.controller = vips.Controller(self.conf)
        self.req = mock.Mock(spec=['headers'])

    def code_assert(self, code, func):
        self.assertTrue(hasattr(func, "wsgi_code"),
                "has not redifined HTTP status code")
        self.assertTrue(func.wsgi_code == code,
                "incorrect HTTP status code")

    @mock.patch('balancer.db.api.unpack_extra', autospec=True)
    @mock.patch('balancer.db.api.virtualserver_get_all_by_lb_id',
                                                            autospec=True)
    def test_index0(self, mock_get, mock_unpack):
        """VIPs should be found"""
        mock_get.return_value = ['foo']
        mock_unpack.return_value = 'foo1'
        resp = self.controller.index(self.req, 'fake_tenant', '1')
        self.assertTrue(mock_get.called)
        self.assertTrue(mock_unpack.called)
        mock_get.assert_called_once_with(self.conf,
                '1', tenant_id='fake_tenant')
        mock_unpack.assert_called_once_with('foo')
        self.assertEqual(resp, {'virtualIps': ['foo1']})

    @mock.patch('balancer.db.api.virtualserver_get_all_by_lb_id',
                                                           autospec=True)
    def test_index1(self, mock_get):
        """Should raise exception"""
        mock_get.side_effect = exception.VirtualServerNotFound()
        with self.assertRaises(exception.VirtualServerNotFound):
            resp = self.controller.index(self.req, 'fake_tenant', '1')
            self.assertEqual(resp, None)

    @mock.patch('balancer.core.api.lb_add_vip', autospec=True)
    def test_create(self, mock_lb_add_vip):
        mock_lb_add_vip.return_value = 'fakevip'
        resp = self.controller.create(self.req,
                'fake_tenant', 'fakelbid', {'virtualIp': 'fakebody'})
        self.assertTrue(mock_lb_add_vip.called)
        mock_lb_add_vip.assert_called_once_with(self.conf,
                'fake_tenant', 'fakelbid', 'fakebody')
        self.assertEqual(resp, {'virtualIp': 'fakevip'})

    @mock.patch('balancer.db.api.unpack_extra', autospec=True)
    @mock.patch('balancer.db.api.virtualserver_get', autospec=True)
    def test_show(self, mock_virtualserver_get, mock_unpack_extra):
        mock_virtualserver_get.return_value = 'fakevip'
        mock_unpack_extra.return_value = 'packedfakevip'
        resp = self.controller.show(self.req,
                'fake_tenant', 'fakelbid', 'fakeid')
        self.assertTrue(mock_virtualserver_get.called)
        self.assertTrue(mock_unpack_extra.called)
        mock_virtualserver_get.assert_called_once_with(self.conf,
                'fakeid', tenant_id='fake_tenant')
        mock_unpack_extra.assert_called_once_with('fakevip')
        self.assertEqual(resp, {'virtualIp': 'packedfakevip'})

    @mock.patch('balancer.core.api.lb_delete_vip', autospec=True)
    def test_delete(self, mock_lb_delete_vip):
        resp = self.controller.delete(self.req,
                'fake_tenant', 'fakelbid', 'fakeid')
        self.assertTrue(mock_lb_delete_vip.called)
        mock_lb_delete_vip.assert_called_once_with(self.conf,
                'fake_tenant', 'fakelbid', 'fakeid')
        self.code_assert(204, self.controller.delete)


class TestProbesController(unittest.TestCase):
    def setUp(self):
        super(TestProbesController, self).setUp()
        self.conf = mock.Mock()
        self.controller = probes.Controller(self.conf)
        self.req = mock.Mock(spec=['headers'])

    def code_assert(self, code, func):
        self.assertTrue(hasattr(func, "wsgi_code"),
                "has not redifined HTTP status code")
        self.assertTrue(func.wsgi_code == code,
                "incorrect HTTP status code")

    @mock.patch('balancer.core.api.lb_show_probes', autospec=True)
    def test_index(self, mock_lb_show_probes):
        mock_lb_show_probes.return_value = 'foo'
        resp = self.controller.index(self.req, 'fake_tenant', 1)
        self.assertTrue(mock_lb_show_probes.called)
        mock_lb_show_probes.assert_called_once_with(self.conf,
                'fake_tenant', 1)
        self.assertEqual(resp, 'foo')

    @mock.patch('balancer.db.api.unpack_extra', autospec=True)
    @mock.patch('balancer.db.api.probe_get', autospec=True)
    def test_show(self, mock_lb_show_probe_by_id, mock_extra):
        mock_lb_show_probe_by_id.return_value = ['foo']
        mock_extra.return_value = 'foo'
        resp = self.controller.show(self.req, 'fake_tenant', 1, 1)
        self.assertTrue(mock_lb_show_probe_by_id.called)
        self.assertTrue(mock_extra.called)
        mock_lb_show_probe_by_id.assert_called_once_with(self.conf,
                1, tenant_id='fake_tenant')
        mock_extra.assert_called_once_with(['foo'])
        self.assertEqual(resp, {'healthMonitoring': 'foo'})

    @mock.patch('balancer.core.api.lb_add_probe', autospec=True)
    def test_create(self, mock_lb_add_probe):
        mock_lb_add_probe.return_value = {'id': '2'}
        body = {'healthMonitoring': {'probe': 'foo'}}
        resp = self.controller.create(self.req, 'fake_tenant', '1', body)
        self.assertTrue(mock_lb_add_probe.called)
        mock_lb_add_probe.assert_called_once_with(self.conf,
                'fake_tenant', '1', {'probe': 'foo'})
        self.assertEqual(resp, {'healthMonitoring': {'id': '2'}})

    @mock.patch('balancer.core.api.lb_delete_probe', autospec=True)
    def test_delete(self, mock_lb_delete_probe):
        resp = self.controller.delete(self.req, 'fake_tenant', 1, 1)
        self.assertTrue(mock_lb_delete_probe.called)
        mock_lb_delete_probe.assert_called_once_with(self.conf,
                'fake_tenant', 1, 1)
        self.assertEqual(resp, None)
        self.code_assert(204, self.controller.delete)


class TestStickiesController(unittest.TestCase):
    def setUp(self):
        super(TestStickiesController, self).setUp()
        self.conf = mock.Mock()
        self.controller = stickies.Controller(self.conf)
        self.req = mock.Mock(spec=['headers'])

    def code_assert(self, code, func):
        self.assertTrue(hasattr(func, "wsgi_code"),
                "has not redifined HTTP status code")
        self.assertTrue(func.wsgi_code == code,
                "incorrect HTTP status code")

    @mock.patch('balancer.core.api.lb_show_sticky', autospec=True)
    def test_index(self, mock_lb_show_sticky):
        mock_lb_show_sticky.return_value = 'foo'
        resp = self.controller.index(self.req, 'fake_tenant', 1)
        self.assertTrue(mock_lb_show_sticky.called)
        mock_lb_show_sticky.assert_called_once_with(self.conf,
                'fake_tenant', 1)
        self.assertEqual(resp, 'foo')

    @mock.patch('balancer.db.api.unpack_extra', autospec=True)
    @mock.patch('balancer.db.api.sticky_get', autospec=True)
    def test_show(self, mock_func, mock_extra):
        mock_extra.return_value = 'foo'
        resp = self.controller.show(self.req, 'fake_tenant', 1, 1)
        self.assertTrue(mock_func.called)
        self.assertTrue(mock_extra.called)
        mock_func.assert_called_once_with(self.conf,
                1, tenant_id='fake_tenant')
        mock_extra.assert_called_once_with(mock_func.return_value)
        self.assertEqual(resp, {'sessionPersistence': 'foo'})

    @mock.patch('balancer.db.api.unpack_extra', autospec=True)
    @mock.patch('balancer.core.api.lb_add_sticky', autospec=True)
    def test_create(self, mock_lb_add_sticky, mock_unpack):
        mock_unpack.return_value = '1'
        mock_lb_add_sticky.return_value = ['1']
        resp = self.controller.create(self.req,
                'fake_tenant', 1, {'sessionPersistence': 'foo'})
        self.assertTrue(mock_lb_add_sticky.called)
        mock_lb_add_sticky.assert_called_once_with(self.conf,
                'fake_tenant', 1, {'sessionPersistence': 'foo'})
        mock_unpack.assert_called_once_with(['1'])
        self.assertEqual(resp, {"sessionPersistence": "1"})

    @mock.patch('balancer.core.api.lb_delete_sticky', autospec=True)
    def test_delete(self, mock_lb_delete_sticky):
        resp = self.controller.delete(self.req, 'fake_tenant', 1, 1)
        self.assertTrue(mock_lb_delete_sticky.called)
        mock_lb_delete_sticky.assert_called_once_with(self.conf,
                'fake_tenant', 1, 1)
        self.assertEqual(resp, None)
        self.code_assert(204, self.controller.delete)


class TestDeviceController(unittest.TestCase):
    def setUp(self):
        self.conf = mock.Mock()
        self.controller = devices.Controller(self.conf)
        self.req = mock.Mock(spec=['headers'])

    @mock.patch('balancer.core.api.device_get_index', autospec=True)
    def test_index(self, mock_device_get_index):
        mock_device_get_index.return_value = 'foo'
        resp = self.controller.index(self.req)
        self.assertTrue(mock_device_get_index.called)
        mock_device_get_index.assert_called_once_with(self.conf)
        self.assertEqual({'devices': 'foo'}, resp)

    @mock.patch('balancer.db.api.unpack_extra', autospec=True)
    @mock.patch('balancer.core.api.device_create', autospec=True)
    def test_create(self, mock_device_create, mock_unpack):
        mock_device_create.return_value = ['foo']
        mock_unpack.return_value = 'foo'
        res = self.controller.create(self.req, {'foo': 'foo'})
        self.assertTrue(mock_device_create.called)
        mock_device_create.assert_called_once_with(self.conf, foo='foo')
        mock_unpack.assert_called_once_with(['foo'])
        self.assertEqual({'device': 'foo'}, res)

    @mock.patch('balancer.core.api.device_delete', autospec=True)
    def test_delete(self, mock_device_delete):
        resp = self.controller.delete(self.req, 1)
        self.assertTrue(mock_device_delete.called)
        mock_device_delete.assert_called_once_with(self.conf, 1)
        self.assertTrue(hasattr(self.controller.delete, "wsgi_code"),
                                "has not redifined HTTP status code")
        self.assertTrue(self.controller.delete.wsgi_code == 204,
        "incorrect HTTP status code")
        self.assertEqual(None, resp)

    @unittest.skip('need to implement Controller.device_info')
    @mock.patch('balancer.core.api.device_info', autospec=True)
    def test_info(self, mock_device_info):
        mock_device_info.return_value = 'foo'
        resp = self.controller.device_info(self.req)
        self.assertTrue(mock_device_info.called)
        mock_device_info.assert_called_once_with()
        self.assertEqual({'devices': 'foo'}, resp)

    @mock.patch('balancer.core.api.device_show_algorithms')
    def test_show_algorithms_0(self, mock_core_api):
        resp = self.controller.show_algorithms(self.req)
        self.assertTrue(mock_core_api.called)

    @mock.patch('balancer.core.api.device_show_protocols')
    def test_show_protocols(self, mock_core_api):
        resp = self.controller.show_protocols(self.req)
        self.assertTrue(mock_core_api.called)


class TestRouter(unittest.TestCase):
    def setUp(self):
        config = mock.MagicMock(spec=dict)
        self.obj = router.API(config)

    def test_mapper(self):
        list_of_methods = (
            # loadbalancers
            ("/{tenant_id}/loadbalancers", "GET",
                loadbalancers.Controller, "index"),
            ("/{tenant_id}/loadbalancers", "POST",
                loadbalancers.Controller, "create"),
            ("/{tenant_id}/loadbalancers/{lb_id}", "GET",
                loadbalancers.Controller, "show"),
            ("/{tenant_id}/loadbalancers/{lb_id}", "PUT",
                loadbalancers.Controller, "update"),
            ("/{tenant_id}/loadbalancers/{lb_id}", "DELETE",
                loadbalancers.Controller, "delete"),
            ("/{tenant_id}/loadbalancers/find_for_VM/{vm_id}", "GET",
                loadbalancers.Controller, "findLBforVM"),
            ("/{tenant_id}/loadbalancers/{lb_id}/details", "GET",
                loadbalancers.Controller, "details"),
            # nodes
            ("/{tenant_id}/loadbalancers/{lb_id}/nodes", "GET",
                nodes.Controller, "index"),
            ("/{tenant_id}/loadbalancers/{lb_id}/nodes", "POST",
                nodes.Controller, "create"),
            ("/{tenant_id}/loadbalancers/{lb_id}/nodes/{node_id}", "GET",
                nodes.Controller, "show"),
            ("/{tenant_id}/loadbalancers/{lb_id}/nodes/{node_id}", "PUT",
                nodes.Controller, "update"),
            ("/{tenant_id}/loadbalancers/{lb_id}/nodes/{node_id}", "DELETE",
                nodes.Controller, "delete"),
            ("/{tenant_id}/loadbalancers/{lb_id}/nodes/{node_id}/{status}",
                                                                    "PUT",
                nodes.Controller, "changeNodeStatus"),
            # probes
            ("/{tenant_id}/loadbalancers/{lb_id}/healthMonitoring", "GET",
                probes.Controller, "index"),
            ("/{tenant_id}/loadbalancers/{lb_id}/healthMonitoring", "POST",
                probes.Controller, "create"),
            ("/{tenant_id}/loadbalancers/{lb_id}/healthMonitoring/{probe_id}",
                "GET", probes.Controller, "show"),
            ("/{tenant_id}/loadbalancers/{lb_id}/healthMonitoring/{probe_id}",
                                                                    "DELETE",
                probes.Controller, "delete"),
            # stickies
            ("/{tenant_id}/loadbalancers/{lb_id}/sessionPersistence", "GET",
                stickies.Controller, "index"),
            ("/{tenant_id}/loadbalancers/{lb_id}/sessionPersistence", "POST",
                stickies.Controller, "create"),
            ("/{tenant_id}/loadbalancers/{lb_id}/sessionPersistence"
                                                    "/{sticky_id}", "GET",
                stickies.Controller, "show"),
            ("/{tenant_id}/loadbalancers/{lb_id}/sessionPersistence"
                                                    "/{sticky_id}", "DELETE",
                stickies.Controller, "delete"),
            # vips
            ("/{tenant_id}/loadbalancers/{lb_id}/virtualIps", "GET",
                vips.Controller, "index"),
            ("/{tenant_id}/loadbalancers/{lb_id}/virtualIps", "POST",
                vips.Controller, "create"),
            ("/{tenant_id}/loadbalancers/{lb_id}/virtualIps/{vip_id}", "GET",
                vips.Controller, "show"),
            ("/{tenant_id}/loadbalancers/{lb_id}/virtualIps/{vip_id}",
                                                                    "DELETE",
                vips.Controller, "delete"),
            # devices
            ("/devices", "GET", devices.Controller, "index"),
            ("/devices", "POST", devices.Controller, "create"),
            ("/devices/{device_id}", "GET", devices.Controller, "show"),
            ("/devices/{device_id}", "DELETE", devices.Controller, "delete"),
            ("/devices/{device_id}/info", "GET", devices.Controller, "info"),
        )
        for url, method, controller, action in list_of_methods:
            LOG.info('Verifying %s to %s', method, url)
            m = self.obj.map.match(url, {"REQUEST_METHOD": method})
            self.assertTrue(m is not None, "Route not found for %s %s" % (
                    method, url))
            controller0 = m.pop('controller')
            action0 = m.pop('action')
            self.assertTrue(isinstance(controller0, wsgi.Resource),
                    "Controller for %s %s is not wshi.Resource instance." % (
                    method, url))
            self.assertTrue(isinstance(controller0.controller, controller),
                    "Inner controller for %s %s is not %s.%s instance." % (
                    method, url, controller.__module__, controller.__name__))
            self.assertEquals(action0, action)
            mok = mock.mocksignature(getattr(controller, action))
            if method == "POST" or method == "PUT":
                m['body'] = {}
            try:
                mok('SELF', 'REQUEST', **m)
            except TypeError:
                self.fail('Arguments in route "%s %s" does not match %s.%s.%s '
                          'signature: %s' % (method, url,
                    controller.__module__, controller.__name__, action, m))

########NEW FILE########
__FILENAME__ = test_base_driver
import unittest
import mock

from .test_db_api import device_fake1
from balancer.drivers.base_driver import BaseDriver


class TestBaseDriver(unittest.TestCase):
    def setUp(self):
        super(TestBaseDriver, self).setUp()
        self.conf = mock.Mock()

    def test_get_capabilities(self):
        """Test without capabilities"""
        base_driver = BaseDriver(self.conf, device_fake1)
        self.assertEqual(base_driver.get_capabilities(), None)

    def test_get_capabilities1(self):
        """Test with capabilities"""
        capabilities = {'capabilities': {
                        'algorithms': ['algo1', 'algo2'],
                        'protocols': ['udp', 'tcp']}}
        device_fake1['extra'] = capabilities
        base_driver = BaseDriver(self.conf, device_fake1)
        self.assertDictEqual(base_driver.get_capabilities(),
                             capabilities['capabilities'])

########NEW FILE########
__FILENAME__ = test_commands
import balancer.core.commands as cmd
import unittest
import mock
import types
import logging

LOG = logging.getLogger(__name__)


class TestDecorators(unittest.TestCase):
    """Need help with def fin coverage"""
    def setUp(self):
        self.obj0 = mock.MagicMock(__name__='GenTypeObj',
                return_value=mock.MagicMock(spec=types.GeneratorType))
        self.obj1 = mock.MagicMock(__name__='NonGenTypeObj',
                return_value=mock.MagicMock(spec=types.FunctionType))
        self.ctx_mock = mock.MagicMock()
        self.exc = Exception("Someone doing something wrong")

    def test_with_rollback_gen_type_0(self):
        """Don't get any exception"""
        wrapped = cmd.with_rollback(self.obj0)
        wrapped(self.ctx_mock, "arg1", "arg2")
        self.assertEquals([mock.call(self.ctx_mock, "arg1", "arg2")],
                self.obj0.call_args_list)
        rollback_fn = self.ctx_mock.add_rollback.call_args[0][0]
        rollback_fn(True)
        self.assertTrue(self.ctx_mock.add_rollback.called)
        self.assertTrue(self.obj0.return_value.close.called)

    def test_with_rollback_gen_type_1(self):
        """Get Rollback exception"""
        self.obj0.return_value.throw.side_effect = cmd.Rollback
        wrapped = cmd.with_rollback(self.obj0)
        wrapped(self.ctx_mock, "arg1", "arg2")
        self.assertEquals([mock.call(self.ctx_mock, "arg1", "arg2")],
                self.obj0.call_args_list)
        rollback_fn = self.ctx_mock.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(self.ctx_mock.add_rollback.called)
        self.assertEquals(self.obj0.return_value.throw.call_args_list,
                [mock.call(cmd.Rollback)])

    def test_with_rollback_gen_type_2(self):
        """Get exception during rollback"""
        self.obj0.return_value.throw.side_effect = Exception()
        wrapped = cmd.with_rollback(self.obj0)
        wrapped(self.ctx_mock, "arg1", "arg2")
        self.assertEquals([mock.call(self.ctx_mock, "arg1", "arg2")],
                self.obj0.call_args_list)
        rollback_fn = self.ctx_mock.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(self.ctx_mock.add_rollback.called)
        self.assertEquals(self.obj0.return_value.throw.call_args_list,
                [mock.call(cmd.Rollback)])

    def test_with_rollback_gen_type_3(self):
        """Get StopIteration exception"""
        self.obj0.return_value.next.side_effect = StopIteration
        with self.assertRaises(type(self.exc)):
            wrapped = cmd.with_rollback(self.obj0)
            wrapped(self.ctx_mock, "arg1", "arg2")
        self.assertEquals([mock.call(self.ctx_mock, "arg1", "arg2")],
                self.obj0.call_args_list)
        self.assertFalse(self.ctx_mock.add_rollback.called)

    def test_with_rollback_non_gen_type(self):
        with self.assertRaises(type(self.exc)):
            wrapped = cmd.with_rollback(self.obj1)
            wrapped(self.ctx_mock, "arg1", "arg2")

    def test_ignore_exceptions0(self):
        """Don't get exception"""
        wrapped = cmd.ignore_exceptions(self.obj1)
        wrapped("arg1", "arg2")
        self.assertEquals([mock.call("arg1", "arg2")],
                self.obj1.call_args_list)

    def test_ignore_exceptions1(self):
        """Get exception"""
        self.obj1.side_effect = Exception()
        wrapped = cmd.ignore_exceptions(self.obj1)
        wrapped()
        self.assertTrue(self.obj1.call_args_list, Exception)


class TestRollbackContext(unittest.TestCase):
    def setUp(self):
        self.rollback = mock.MagicMock()
        self.rollback.return_value = "foo"
        self.obj = cmd.RollbackContext()
        self.stack = []

    def test_init(self):
        self.obj.__init__()
        self.assertEquals(self.obj.rollback_stack, [], "Not equal")

    def test_add_rollback(self):
        self.obj.add_rollback(self.rollback)
        self.assertFalse(self.obj.rollback_stack == [], 'Empty')


class TestRollbackContextManager(unittest.TestCase):
    def setUp(self):
        self.rollback_mock = mock.MagicMock()
        self.obj = cmd.RollbackContextManager(
                context=mock.MagicMock(rollback_stack=[self.rollback_mock]))

    @mock.patch("balancer.core.commands.RollbackContext")
    def test_init(self, mock_context):
        self.obj.__init__()
        self.assertTrue(mock_context.called, "Context not called")

    @mock.patch("balancer.core.commands.RollbackContext")
    def test_enter(self, mock_context):
        res = self.obj.__enter__()
        self.assertEquals(res, self.obj.context, "Wrong context")

    def test_exit_none(self):
        self.obj.__exit__(None, None, None)
        self.assertEquals([mock.call(True,)],
                self.rollback_mock.call_args_list)

    def test_exit_not_none(self):
        exc = Exception("Someone set up us the bomb")
        with self.assertRaises(type(exc)):
            self.obj.__exit__(type(exc), exc, None)
        self.assertEquals([mock.call(False,)],
                self.rollback_mock.call_args_list)


class TestRserver(unittest.TestCase):
    def setUp(self):
        self.ctx = mock.MagicMock(device=mock.MagicMock(
            delete_real_server=mock.MagicMock(),
            create_real_server=mock.MagicMock()))
        self.rs = {'parent_id': "", 'id': mock.MagicMock(spec=int),
                'deployed': ""}
        self.exc = Exception()

    @mock.patch("balancer.db.api.server_update")
    def test_create_rserver_1(self, mock_func):
        """ parent_id is None """
        self.rs['parent_id'] = None
        cmd.create_rserver(self.ctx, self.rs)
        self.assertTrue(self.ctx.device.create_real_server.called)
        self.assertTrue(mock_func.called)
        mock_func.assert_called_once_with(self.ctx.conf,
                                          self.rs['id'], self.rs)

    @mock.patch("balancer.db.api.server_update")
    def test_create_rserver_2(self, mock_func):
        """ parent_id is not None or 0, no exception """
        self.rs['parent_id'] = 1
        cmd.create_rserver(self.ctx, self.rs)
        self.assertFalse(self.ctx.device.create_real_server.called)
        self.assertFalse(mock_func.called)

    @mock.patch("balancer.db.api.server_update")
    def test_create_rserver_3(self, mock_func):
        """Exception"""
        self.rs['parent_id'] = None
        cmd.create_rserver(self.ctx, self.rs)
        rollback_fn = self.ctx.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(self.ctx.device.delete_real_server.called)
        self.assertTrue(mock_func.called)
        self.assertTrue(mock_func.call_count == 2)
        mock_func.assert_called_with(self.ctx.conf,
                                     self.rs['id'], self.rs)

    @mock.patch("balancer.db.api.server_update")
    @mock.patch("balancer.db.api.server_get_all_by_parent_id")
    def test_delete_rserver_1(self, mock_f1, mock_f2):
        """rs parent_id empty, len rss > 0"""
        mock_f1.return_value = ({'id': 2}, {'id': 3})
        cmd.delete_rserver(self.ctx, self.rs)
        self.assertTrue(self.ctx.device.delete_real_server.called,
                "ctx_delete_rs not called")
        self.assertTrue(mock_f2.called, "server_upd not called")
        self.assertTrue(mock_f2.call_count == 3)
        mock_f2.assert_any_call(self.ctx.conf, 2, {'parent_id': 3})
        mock_f2.assert_any_call(self.ctx.conf, 3, {'parent_id': 3})
        mock_f2.assert_any_call(self.ctx.conf, 3, {'parent_id': '',
                                                   'deployed': 'True'})
        self.assertTrue(self.ctx.device.create_real_server.called,
                "ctx_create_rs not called")
        self.assertNotEquals(len(mock_f1.return_value), 0)

    @mock.patch("balancer.db.api.server_get_all_by_parent_id")
    @mock.patch("balancer.db.api.server_update")
    def test_delete_rserver_2(self, mock_f1, mock_f2):
        """rs parent_id not empty"""
        self.rs['parent_id'] = 1
        cmd.delete_rserver(self.ctx, self.rs)
        self.assertFalse(self.ctx.device.delete_real_server.called,
                         "delete_rserver called")
        self.assertFalse(mock_f1.called)
        self.assertFalse(mock_f2.called)

    @mock.patch("balancer.db.api.server_get_all_by_parent_id")
    @mock.patch("balancer.db.api.server_update")
    def test_delete_rserver_3(self, mock_f1, mock_f2):
        """rs parent_id empty, rss empty"""
        mock_f2.return_value = ()
        cmd.delete_rserver(self.ctx, self.rs)
        self.assertFalse(self.ctx.device.create_real_server.called,
                         "create_rserver called")
        self.assertTrue(self.ctx.device.delete_real_server.called)
        self.assertFalse(mock_f1.called, "server_update called")


class TestSticky(unittest.TestCase):
    def setUp(self):
        self.ctx = mock.MagicMock()
        self.sticky = mock.MagicMock()
        self.sticky[1] = 'id'
        self.sticky[2] = 'deployed'

    @mock.patch("balancer.db.api.sticky_update")
    def test_create_sticky(self, mock_upd):
        cmd.create_sticky(self.ctx, self.sticky)
        self.assertTrue(mock_upd.called, "upd not called")
        self.assertTrue(self.ctx.device.create_stickiness.called)
        mock_upd.assert_called_once_with(self.ctx.conf, self.sticky['id'],
                                         self.sticky)

    @mock.patch("balancer.db.api.sticky_update")
    def test_delete_sticky(self, mock_upd):
        cmd.delete_sticky(self.ctx, self.sticky)
        self.assertTrue(mock_upd.called, "upd not called")
        self.assertTrue(self.ctx.device.delete_stickiness.called)
        mock_upd.assert_called_once_with(self.ctx.conf, self.sticky['id'],
                                         self.sticky)


class TestProbe(unittest.TestCase):
    def setUp(self):
        self.ctx = mock.MagicMock()
        self.probe = mock.MagicMock()

    @mock.patch("balancer.core.commands")
    @mock.patch("balancer.db.api.probe_update")
    def test_create_probe_0(self, mock_f1, mock_f2):
        '''No exception should raise'''
        cmd.create_probe(self.ctx, self.probe)
        self.assertTrue(self.ctx.device.create_probe.called)
        self.assertTrue(mock_f1.called)
        self.assertFalse(mock_f2.called)
        mock_f1.assert_called_once_with(self.ctx.conf, self.probe['id'],
                {'deployed': True})

    @mock.patch("balancer.core.commands.delete_probe")
    @mock.patch("balancer.db.api.probe_update")
    def test_create_probe_1(self, mock_f1, mock_f2):
        '''Exception raises'''
        cmd.create_probe(self.ctx, self.probe)
        rollback_fn = self.ctx.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(mock_f2.called)
        mock_f2.assert_called_once_with(self.ctx, self.probe)

    @mock.patch("balancer.db.api.probe_update")
    def test_delete_probe(self, mock_upd):
        cmd.delete_probe(self.ctx, self.probe)
        self.assertTrue(self.ctx.device.delete_probe.called)
        self.assertTrue(self.ctx.device.delete_probe.call_count == 1)
        self.assertTrue(mock_upd.called, "upd not called")
        mock_upd.assert_called_once_with(self.ctx.conf, self.probe['id'],
                                         self.probe)


class TestVip(unittest.TestCase):
    def setUp(self):
        self.ctx = mock.MagicMock()
        self.vip = mock.MagicMock()
        self.server_farm = mock.MagicMock()

    @mock.patch("balancer.core.commands.delete_vip")
    @mock.patch("balancer.db.api.virtualserver_update")
    def test_create_vip_0(self, mock_f1, mock_f2):
        """No exception"""
        cmd.create_vip(self.ctx, self.vip, self.server_farm)
        self.assertTrue(self.ctx.device.create_virtual_ip.called)
        self.assertTrue(mock_f1.called)
        self.assertFalse(mock_f2.called)
        mock_f1.assert_called_once_with(self.ctx.conf, self.vip['id'],
                {'deployed': True})

    @mock.patch("balancer.core.commands.delete_vip")
    @mock.patch("balancer.db.api.virtualserver_update")
    def test_create_vip_1(self, mock_f1, mock_f2):
        """Exception"""
        cmd.create_vip(self.ctx, self.vip, self.server_farm)
        rollback_fn = self.ctx.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(mock_f2.called)
        mock_f2.assert_called_once_with(self.ctx, self.vip)

    @mock.patch("balancer.db.api.virtualserver_update")
    def test_delete_vip(self, mock_upd):
        cmd.delete_vip(self.ctx, self.vip)
        self.assertTrue(self.ctx.device.delete_virtual_ip.called)
        self.assertTrue(mock_upd.called, "upd not called")
        mock_upd.assert_called_once_with(self.ctx.conf, self.vip['id'],
                                         self.vip)


class TestServerFarm(unittest.TestCase):
    def setUp(self):
        self.ctx = mock.MagicMock(device=mock.MagicMock(
            delete_real_server_from_server_farm=mock.MagicMock(),
            delete_probe_from_server_farm=mock.MagicMock(),
            activate_real_server=mock.MagicMock(),
            uspend_real_server=mock.MagicMock(),
            add_real_server_to_server_farm=mock.MagicMock(),
            create_server_farm=mock.MagicMock(),
            add_probe_to_server_farm=mock.MagicMock()),
            conf=mock.MagicMock())
        self.server_farm = mock.MagicMock()
        self.rserver = mock.MagicMock()
        self.probe = mock.MagicMock()

    @mock.patch("balancer.db.api.predictor_get_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_update")
    @mock.patch("balancer.core.commands.delete_server_farm")
    def test_create_server_farm_0(self, mock_f1, mock_f2, mock_f3):
        """No exception"""
        cmd.create_server_farm(self.ctx, self.server_farm)
        self.assertTrue(self.ctx.device.create_server_farm.called)
        self.assertFalse(mock_f1.called)
        self.assertTrue(mock_f2.called)
        self.assertTrue(mock_f3.called)
        mock_f2.assert_called_once_with(self.ctx.conf, self.server_farm['id'],
                {'deployed': True})
        mock_f3.assert_called_once_with(self.ctx.conf, self.server_farm['id'])

    @mock.patch("balancer.db.api.predictor_get_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_update")
    @mock.patch("balancer.core.commands.delete_server_farm")
    def test_create_server_farm_1(self, mock_f1, mock_f2, mock_f3):
        """Exception"""
        cmd.create_server_farm(self.ctx, self.server_farm)
        rollback_fn = self.ctx.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(mock_f1.called)
        mock_f1.assert_called_once_with(self.ctx, self.server_farm)

    @mock.patch("balancer.db.api.serverfarm_update")
    def test_delete_server_farm(self, mock_upd):
        cmd.delete_server_farm(self.ctx, self.server_farm)
        self.assertTrue(self.ctx.device.delete_server_farm.called)
        self.assertTrue(mock_upd.called, "upd not called")
        mock_upd.assert_called_once_with(self.ctx.conf, self.server_farm['id'],
                                         self.server_farm)

    def test_add_rserver_to_server_farm_0(self):
        "No exception, if statement = True"
        cmd.add_rserver_to_server_farm(self.ctx, self.server_farm,
                                       self.rserver)
        self.assertTrue(self.ctx.device.add_real_server_to_server_farm.called)
        self.assertEquals(self.rserver['name'], self.rserver['parent_id'])

    def test_add_rserver_to_server_farm_1(self):
        "Exception"
        cmd.add_rserver_to_server_farm(self.ctx, self.server_farm,
                                       self.rserver)
        rollback_fn = self.ctx.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(
            self.ctx.device.delete_real_server_from_server_farm.called)

    def test_delete_rserver_from_server_farm(self):
        cmd.delete_rserver_from_server_farm(self.ctx, self.server_farm,
                                            self.rserver)
        self.assertTrue(
                self.ctx.device.delete_real_server_from_server_farm.called,
                "method not called")

    def test_add_probe_to_server_farm_0(self):
        "No exception"
        cmd.add_probe_to_server_farm(self.ctx, self.server_farm, self.probe)
        self.assertTrue(self.ctx.device.add_probe_to_server_farm.called)

    def test_add_probe_to_server_farm_1(self):
        "Exception"
        cmd.add_probe_to_server_farm(self.ctx, self.server_farm, self.probe)
        rollback_fn = self.ctx.add_rollback.call_args[0][0]
        rollback_fn(False)
        self.assertTrue(self.ctx.device.delete_probe_from_server_farm.called)

    def test_remove_probe_from_server_farm(self):
        cmd.remove_probe_from_server_farm(self.ctx, self.server_farm,
                                          self.probe)
        self.assertTrue(self.ctx.device.delete_probe_from_server_farm.called,
                        "method not called")

    def test_activate_rserver(self):
        cmd.activate_rserver(self.ctx, self.server_farm, self.rserver)
        self.assertTrue(self.ctx.device.activate_real_server.called,
                        "method not called")

    def test_suspend_rserver(self):
        cmd.suspend_rserver(self.ctx, self.server_farm, self.rserver)
        self.assertTrue(self.ctx.device.suspend_real_server.called,
                        "method not called")


class TestLoadbalancer(unittest.TestCase):
    def setUp(self):
        value = mock.MagicMock()
        self.ctx = mock.MagicMock()
        self.conf = mock.MagicMock()
        self.rserver = mock.MagicMock()
        self.probe = mock.MagicMock()
        self.sticky = mock.MagicMock()
        self.call_list = mock.MagicMock(spec=list)
        self.call_list.__iter__.return_value = [mock.MagicMock(
            get=mock.MagicMock())]
        self.balancer = mock.MagicMock(probes=self.call_list,
               rs=self.call_list, vips=self.call_list,
               sf=mock.MagicMock(_sticky=self.call_list))
        self.dict_list = [{'id': 1, 'name': 'name', 'extra': {
            'stragearg': value, 'anotherarg': value}, },
            {'id': 2, 'name': 'name0', 'extra': {
                'stragearg': value, 'anotherarg': value}, }]
        self.dictionary = {'id': 1, 'name': 'name', 'extra': {
            'stragearg': value, 'anotherarg': value}, }

    @mock.patch("balancer.core.commands.create_sticky")
    @mock.patch("balancer.core.commands.add_probe_to_loadbalancer")
    @mock.patch("balancer.core.commands.add_node_to_loadbalancer")
    @mock.patch("balancer.core.commands.create_vip")
    @mock.patch("balancer.core.commands.create_server_farm")
    def test_create_loadbalancer(self,
                                 mock_create_server_farm,
                                 mock_create_vip,
                                 mock_add_node_to_loadbalancer,
                                 mock_add_probe_to_loadbalancer,
                                 mock_create_sticky):
        cmd.create_loadbalancer(self.ctx, 'fakesf',
                                ['fakevip'],
                                ['fakeserver'],
                                ['fakeprobe'],
                                ['fakesticky'])
        mock_create_server_farm.assert_called_once_with(self.ctx, 'fakesf')
        mock_create_vip.assert_called_once_with(self.ctx, 'fakevip', 'fakesf')
        mock_add_node_to_loadbalancer.assert_called_once_with(self.ctx,
                                                              'fakesf',
                                                              'fakeserver')
        mock_add_probe_to_loadbalancer.assert_called_once_with(self.ctx,
                                                               'fakesf',
                                                               'fakeprobe')
        mock_create_sticky.assert_called_once_with(self.ctx, 'fakesticky')

    @mock.patch("balancer.core.commands.create_sticky")
    @mock.patch("balancer.core.commands.add_probe_to_loadbalancer")
    @mock.patch("balancer.core.commands.add_node_to_loadbalancer")
    @mock.patch("balancer.core.commands.create_vip")
    @mock.patch("balancer.core.commands.create_server_farm")
    def test_create_loadbalancer_only_lb(self,
                                         mock_create_server_farm,
                                         mock_create_vip,
                                         mock_add_node_to_loadbalancer,
                                         mock_add_probe_to_loadbalancer,
                                         mock_create_sticky):
        cmd.create_loadbalancer(self.ctx, 'fakesf', [], [], [], [])
        mock_create_server_farm.assert_called_once_with(self.ctx, 'fakesf')
        for mock_func in [mock_create_vip,
                          mock_add_node_to_loadbalancer,
                          mock_add_probe_to_loadbalancer,
                          mock_create_sticky]:
            self.assertFalse(mock_func.called)

    @mock.patch("balancer.core.commands.delete_sticky")
    @mock.patch("balancer.core.commands.remove_probe_from_server_farm")
    @mock.patch("balancer.core.commands.delete_probe")
    @mock.patch("balancer.core.commands.delete_server_farm")
    @mock.patch("balancer.core.commands.delete_rserver")
    @mock.patch("balancer.core.commands.delete_rserver_from_server_farm")
    @mock.patch("balancer.core.commands.delete_vip")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.virtualserver_get_all_by_sf_id")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.db.api.predictor_destroy_by_sf_id")
    @mock.patch("balancer.db.api.server_destroy_by_sf_id")
    @mock.patch("balancer.db.api.probe_destroy_by_sf_id")
    @mock.patch("balancer.db.api.virtualserver_destroy_by_sf_id")
    @mock.patch("balancer.db.api.sticky_destroy_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_destroy")
    @mock.patch("balancer.db.api.loadbalancer_destroy")
    def test_delete_loadbalancer(self, *mocks):
        for mok in mocks[7:11]:
            mok.return_value = [{"dummy": '1'}, {"dummy": '2'}]
        mocks[12].return_value = {'id': 1}
        cmd.delete_loadbalancer(self.ctx, self.balancer)
        for mok in mocks:
            self.assertTrue(mok.called, "This mock didn't call %s"
                    % mok._mock_name)

    @mock.patch("balancer.core.commands.delete_server_farm")
    @mock.patch("balancer.core.commands.delete_sticky")
    @mock.patch("balancer.core.commands.remove_probe_from_loadbalancer")
    @mock.patch("balancer.core.commands.remove_node_from_loadbalancer")
    @mock.patch("balancer.core.commands.delete_vip")
    def test_delete_loadbalancer(self,
                                 mock_delete_vip,
                                 mock_remove_node_from_loadbalancer,
                                 mock_remove_probe_from_loadbalancer,
                                 mock_delete_sticky,
                                 mock_delete_server_farm):
        cmd.delete_loadbalancer(self.ctx, 'fakesf',
                                ['fakevip'],
                                ['fakeserver'],
                                ['fakeprobe'],
                                ['fakesticky'])
        mock_delete_vip.assert_called_once_with(self.ctx, 'fakevip')
        mock_remove_node_from_loadbalancer.assert_called_once_with(self.ctx,
                'fakesf', 'fakeserver')
        mock_remove_probe_from_loadbalancer.assert_called_once_with(self.ctx,
                'fakesf', 'fakeprobe')
        mock_delete_sticky.assert_called_once_with(self.ctx, 'fakesticky')
        mock_delete_server_farm.assert_called_once_with(self.ctx, 'fakesf')

    @mock.patch("balancer.core.commands.create_rserver")
    @mock.patch("balancer.core.commands.add_rserver_to_server_farm")
    def test_add_node_to_loadbalancer(self, mock_f1, mock_f2):
        cmd.add_node_to_loadbalancer(self.ctx, self.balancer.sf, self.rserver)
        self.assertTrue(mock_f1.called, "add_rserver not called")
        self.assertTrue(mock_f2.called, "create_rserver not called")
        mock_f1.assert_called_once_with(self.ctx, self.balancer.sf,
                                        self.rserver)
        mock_f2.assert_called_once_with(self.ctx, self.rserver)

    @mock.patch("balancer.core.commands.delete_rserver")
    @mock.patch("balancer.core.commands.delete_rserver_from_server_farm")
    def test_remove_node_from_loadbalancer(self, mock_f1, mock_f2):
        cmd.remove_node_from_loadbalancer(
                self.ctx, self.balancer.sf, self.rserver)
        self.assertTrue(mock_f1.called, "delete_rserver_from_farm not called")
        self.assertTrue(mock_f2.called, "delete_rserver called")
        mock_f1.assert_called_once_with(self.ctx, self.balancer.sf,
                                        self.rserver)
        mock_f2.assert_called_once_with(self.ctx, self.rserver)

    @mock.patch("balancer.core.commands.create_probe")
    @mock.patch("balancer.core.commands.add_probe_to_server_farm")
    def test_add_probe_to_loadbalancer(self, mock_f1, mock_f2):
        cmd.add_probe_to_loadbalancer(self.ctx, self.balancer, self.probe)
        self.assertTrue(mock_f1.called, "add_probe not called")
        self.assertTrue(mock_f2.called, "create_probe not called")
        mock_f1.assert_called_once_with(self.ctx, self.balancer,
                                        self.probe)
        mock_f2.assert_called_once_with(self.ctx, self.probe)

    @mock.patch("balancer.core.commands.remove_probe_from_server_farm")
    @mock.patch("balancer.core.commands.delete_probe")
    def test_remove_probe_from_loadbalancer(self, mock_f1, mock_f2):
        cmd.remove_probe_from_loadbalancer(self.ctx, 'fakesf', self.probe)
        self.assertTrue(mock_f1.called, "delete_probe not called")
        self.assertTrue(mock_f2.called,
                        "remove_probe_from_server_farm not called")
        mock_f1.assert_called_once_with(self.ctx, self.probe)
        mock_f2.assert_called_once_with(self.ctx, 'fakesf', self.probe)

    @mock.patch("balancer.core.commands.create_sticky")
    def test_add_sticky_to_loadbalancer(self, mock_func):
        cmd.add_sticky_to_loadbalancer(self.ctx, self.balancer, self.sticky)
        self.assertTrue(mock_func.called, "create_sticky not called")
        mock_func.assert_called_once_with(self.ctx, self.sticky)

    @mock.patch("balancer.core.commands.delete_sticky")
    def test_remove_sticky_from_loadbalancer(self, mock_func):
        cmd.remove_sticky_from_loadbalancer(self.ctx, self.balancer,
                                            self.sticky)
        self.assertTrue(mock_func.called, "delete_sticky not called")
        mock_func.assert_called_once_with(self.ctx, self.sticky)

########NEW FILE########
__FILENAME__ = test_core_api
import mock
import unittest
import types
import balancer.core.api as api
from openstack.common import exception
from balancer import exception as exc
import balancer.db.models as models


class TestDecorators(unittest.TestCase):

    def setUp(self):
        self.func = mock.MagicMock(__name__='Test func',
                return_value=mock.MagicMock(spec=types.FunctionType))

    def test_asynchronous_1(self):
        wrapped = api.asynchronous(self.func)
        wrapped(async=False)
        self.assertEquals(self.func.call_args_list, [mock.call()])

    @mock.patch("eventlet.spawn")
    def test_asynchronous_2(self, mock_event):
        wrapped = api.asynchronous(self.func)
        wrapped(async=True)
        self.assertTrue(mock_event.called)


class TestBalancer(unittest.TestCase):
    patch_balancer = mock.patch("balancer.loadbalancers.vserver.Balancer")
    patch_schedule = mock.patch("balancer.core.scheduler.schedule")
    patch_reschedule = mock.patch("balancer.core.scheduler.reschedule")
    patch_logger = mock.patch("logging.getLogger")

    def setUp(self):
        self.conf = mock.MagicMock()
        value = mock.MagicMock
        self.dict_list = [{'id': 1, 'name': 'name', 'extra': {
            'stragearg': value, 'anotherarg': value}, },
            {'id': 2, 'name': 'name0', 'extra': {
                'stragearg': value, 'anotherarg': value}, }]
        self.dictionary = {'id': 1, 'name': 'name', 'extra': {
            'stragearg': value, 'anotherarg': value}, }
        self.tenant_id = 1
        self.lb_id = 1
        self.lb_node = self.dictionary
        self.lb_nodes = self.dict_list
        self.lb_node_id = 1
        self.lb_body_0 = {'bubble': "bubble"}
        self.lb_body = {'algorithm': "bubble"}
        self.dict_list_0 = {'nodes': [{'id': 1, 'name': 'name',
            'extra': {'stragearg': value, 'anotherarg': value}}],
            'healthMonitor': [{'id': 2, 'name': 'name0', 'extra': {
                'stragearg': value, 'anotherarg': value}}],
            'virtualIps': [{'id': 333, 'name': 'name0', 'extra': {
                'stragearg': value, 'anotherarg': value}}]}

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.loadbalancer_get_all_by_project")
    def test_lb_get_index(self, mock_api, mock_extra):
        mock_api.return_value = [{'id': 1, 'virtualIps': 'foo'}, {'id': 2}]
        mock_extra.return_value = 'foo'
        resp = api.lb_get_index(self.conf, self.tenant_id)
        self.assertTrue(mock_api.called)
        self.assertTrue(mock_extra.called)
        self.assertTrue(mock_extra.call_count == 2)
        self.assertEqual(resp, ['foo', 'foo'])
        mock_api.assert_called_once_with(self.conf, self.tenant_id)
        mock_extra.assert_any_call({'id': 1, 'virtualIps': 'foo'})
        mock_extra.assert_any_call({'id': 2})

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.loadbalancer_get_all_by_vm_id")
    def test_lb_find_for_vm(self, mock_api, mock_extra):
        vm_id = mock.Mock()
        mock_api.return_value = ['foo']
        mock_extra.return_value = 'foo'
        resp = api.lb_find_for_vm(self.conf, 'fake_tenant', vm_id)
        mock_api.assert_called_once_with(self.conf, 'fake_tenant', vm_id)
        mock_extra.assert_called_once_with('foo')
        self.assertTrue(mock_api.called)
        self.assertEqual(resp, ['foo'])

    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.virtualserver_get_all_by_sf_id")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    def test_lb_show_details(self, *mocks):
        mocks[5].return_value = {"virtualIps": 1, "nodes": 2,
                "healthMonitor": 3, "sessionPersistence": 4}
        mocks[6].return_value = mock.MagicMock(spec=models.ServerFarm)
        api.lb_show_details(self.conf, 'fake_tenant', self.lb_id)
        for mok in mocks:
            self.assertTrue(mok.called, "This mock %s didn't call"
                    % mok._mock_name)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_get_data_0(self, mock_api, mock_bal):
        api.lb_get_data(self.conf, 'fake_tenant', self.lb_id)
        self.assertTrue(mock_api.called)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_get_data_1(self, mock_api, mock_bal):
        mock_api.return_value = {"id": 1, "virtualIps": "cranch"}
        res = api.lb_get_data(self.conf, 'fake_tenant', self.lb_id)
        self.assertTrue(mock_api.called)
        self.assertEquals(res, {"id": 1})

    @mock.patch("balancer.db.api.probe_create")
    @mock.patch("balancer.db.api.probe_pack_extra")
    @mock.patch("balancer.db.api.server_create")
    @mock.patch("balancer.db.api.server_pack_extra")
    @mock.patch("balancer.db.api.virtualserver_create")
    @mock.patch("balancer.db.api.virtualserver_pack_extra")
    @mock.patch("balancer.db.api.serverfarm_create")
    @mock.patch("balancer.db.api.predictor_create")
    @mock.patch("balancer.db.api.loadbalancer_update")
    @mock.patch("balancer.db.api.loadbalancer_create")
    @mock.patch("balancer.db.api.loadbalancer_pack_extra")
    @patch_schedule
    @mock.patch("balancer.core.commands.create_loadbalancer")
    @mock.patch("balancer.drivers.get_device_driver")
    def test_create_lb_0(self, *mocks):
        """No exception"""
        mocks[2].return_value = {'id': 1}
        mocks[4].return_value = {'id': 2, 'algorithm': 'test',
                                 'protocol': 'test'}
        api.create_lb(self.conf, self.dict_list_0)
        for mok in mocks:
            self.assertTrue(mok.called, "Mock %s didn't call"
                    % mok._mock_name)
        mocks[5].assert_called_with(self.conf, 2,
                                    {'status': 'ACTIVE', 'deployed': True})

    @mock.patch("balancer.db.api.probe_create")
    @mock.patch("balancer.db.api.probe_pack_extra")
    @mock.patch("balancer.db.api.server_create")
    @mock.patch("balancer.db.api.server_pack_extra")
    @mock.patch("balancer.db.api.virtualserver_create")
    @mock.patch("balancer.db.api.virtualserver_pack_extra")
    @mock.patch("balancer.db.api.loadbalancer_update")
    @mock.patch("balancer.db.api.loadbalancer_create")
    @mock.patch("balancer.db.api.loadbalancer_pack_extra")
    @mock.patch("balancer.db.api.serverfarm_create")
    @mock.patch("balancer.db.api.predictor_create")
    @patch_schedule
    @mock.patch("balancer.core.commands.create_loadbalancer")
    @mock.patch("balancer.drivers.get_device_driver")
    def test_create_lb_1(self, *mocks):
        """Exception"""
        mocks[6].return_value = {'id': 2, 'algorithm': 'test',
                                 'protocol': 'test'}
        mocks[1].side_effect = exception.Invalid
        mocks[2].return_value = {'id': 1}
        mocks[4].return_value = mock.MagicMock()
        self.assertRaises(exception.Invalid, api.create_lb,
                          self.conf, self.dict_list_0)
        mocks[7].assert_called_with(self.conf, 2,
                                    {'status': 'ERROR', 'deployed': False})

    @patch_reschedule
    @mock.patch("balancer.core.commands.delete_loadbalancer")
    @mock.patch("balancer.core.commands.create_loadbalancer")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.loadbalancer_update")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.predictor_get_by_sf_id")
    @mock.patch("balancer.db.api.predictor_update")
    @mock.patch("balancer.db.api.virtualserver_get_all_by_sf_id")
    @mock.patch("balancer.db.api.virtualserver_update")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.drivers.get_device_driver")
    def test_update_lb(self,
                       mock_get_device_driver,
                       mock_sticky_get_all_by_sf_id,
                       mock_probe_get_all_by_sf_id,
                       mock_server_get_all_by_sf_id,
                       mock_virtualserver_update,
                       mock_virtualserver_get_all_by_sf_id,
                       mock_predictor_update,
                       mock_predictor_get_by_sf_id,
                       mock_serverfarm_get_all_by_lb_id,
                       mock_loadbalancer_update,
                       mock_loadbalancer_get,
                       mock_create_loadbalancer,
                       mock_delete_loadbalancer,
                       mock_reschedule):
        lb_body = {'algorithm': 'FAKE_ALGO1', 'protocol': 'FAKE_PROTO1'}
        mock_loadbalancer_get.return_value = {
            'id': self.lb_id,
            'device_id': 'fakedeviceid',
            'name': 'fakename',
            'algorithm': 'FAKE_ALGO0',
            'protocol': 'FAKE_PROTO0',
        }
        mock_loadbalancer_update.return_value = lb_ref = {
            'id': self.lb_id,
            'device_id': 'fakedeviceid',
            'name': 'fakename',
            'algorithm': 'FAKE_ALGO1',
            'protocol': 'FAKE_PROTO1',
        }
        mock_reschedule.return_value = {'id': 'fakedeviceid'}
        sf_ref = {'id': 'fakesfid'}
        mock_serverfarm_get_all_by_lb_id.return_value = [sf_ref]
        predictor_ref = {'id': 'fakepredid'}
        mock_predictor_get_by_sf_id.return_value = predictor_ref
        vip_ref = {'id': 'fakevipid', 'extra': {'protocol': 'FAKE_PROTO0'}}
        mock_virtualserver_get_all_by_sf_id.return_value = [vip_ref]
        mock_servers = mock_server_get_all_by_sf_id.return_value
        mock_probes = mock_probe_get_all_by_sf_id.return_value
        mock_stickies = mock_sticky_get_all_by_sf_id.return_value
        mock_device_driver = mock_get_device_driver.return_value
        api.update_lb(self.conf, 'faketenantid', self.lb_id, lb_body,
                      async=False)
        mock_loadbalancer_get.assert_called_once_with(self.conf, self.lb_id,
                                                      tenant_id='faketenantid')
        mock_serverfarm_get_all_by_lb_id.assert_called_once_with(self.conf,
                                                                 self.lb_id)
        mock_predictor_get_by_sf_id.assert_called_once_with(self.conf,
                                                            sf_ref['id'])
        mock_predictor_update.assert_called_once_with(self.conf,
            predictor_ref['id'], {'type': 'FAKE_ALGO1'})
        mock_virtualserver_get_all_by_sf_id.assert_called_once_with(self.conf,
                                                            sf_ref['id'])
        mock_virtualserver_update.assert_called_once_with(self.conf,
            vip_ref['id'], {'id': 'fakevipid',
                            'extra': {'protocol': 'FAKE_PROTO1'}})
        for mock_func in [mock_server_get_all_by_sf_id,
                          mock_probe_get_all_by_sf_id,
                          mock_sticky_get_all_by_sf_id]:
            mock_func.assert_called_once_with(self.conf, sf_ref['id'])
        mock_get_device_driver.assert_called_once_with(self.conf,
                                                       lb_ref['device_id'])
        mock_loadbalancer_update.assert_has_calls([
            mock.call(self.conf, self.lb_id, lb_ref),
            mock.call(self.conf, self.lb_id, {'status': 'ACTIVE'}),
        ])

        # reschedule returns another device
        mock_reschedule.return_value = {'id': 'anotherdeviceid'}
        mock_loadbalancer_update.reset_mock()
        mock_loadbalancer_get.return_value['algorithm'] = 'FAKE_ALGO0'
        api.update_lb(self.conf, 'faketenantid', self.lb_id, lb_body,
                      async=False)
        mock_loadbalancer_update.assert_has_calls([
            mock.call(self.conf, self.lb_id, lb_ref),
            mock.call(self.conf, self.lb_id, {'device_id': 'anotherdeviceid'}),
            mock.call(self.conf, self.lb_id, {'status': 'ACTIVE'}),
        ])

    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.virtualserver_get_all_by_sf_id")
    @mock.patch("balancer.db.api.predictor_update")
    @mock.patch("balancer.db.api.predictor_get_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_update")
    @mock.patch("balancer.db.api.loadbalancer_get")
    def test_update_lb_nothing(self,
                               mock_loadbalancer_get,
                               mock_loadbalancer_update,
                               *mock_funcs):
        lb_body = {'name': 'fakenewname'}
        mock_loadbalancer_get.return_value = {
            'id': self.lb_id,
            'device_id': 'fakedeviceid',
            'name': 'fakename',
            'algorithm': 'FAKE_ALGO0',
            'protocol': 'FAKE_PROTO0',
        }
        mock_loadbalancer_update.return_value = lb_ref = {
            'id': self.lb_id,
            'device_id': 'fakedeviceid',
            'name': 'fakenewname',
            'algorithm': 'FAKE_ALGO0',
            'protocol': 'FAKE_PROTO0',
        }
        sf_ref = {'id': 'fakesfid'}
        api.update_lb(self.conf, 'faketenantid', self.lb_id, lb_body,
                      async=False)
        mock_loadbalancer_get.assert_called_once_with(self.conf, self.lb_id,
                                                      tenant_id='faketenantid')
        for mock_func in mock_funcs:
            mock_func.assert_has_calls([])

    @patch_reschedule
    @mock.patch("balancer.core.commands.delete_loadbalancer")
    @mock.patch("balancer.core.commands.create_loadbalancer")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.loadbalancer_update")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.predictor_get_by_sf_id")
    @mock.patch("balancer.db.api.predictor_update")
    @mock.patch("balancer.db.api.virtualserver_get_all_by_sf_id")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.drivers.get_device_driver")
    def test_update_lb_error(self,
                             mock_get_device_driver,
                             mock_sticky_get_all_by_sf_id,
                             mock_probe_get_all_by_sf_id,
                             mock_server_get_all_by_sf_id,
                             mock_virtualserver_get_all_by_sf_id,
                             mock_predictor_update,
                             mock_predictor_get_by_sf_id,
                             mock_serverfarm_get_all_by_lb_id,
                             mock_loadbalancer_update,
                             mock_loadbalancer_get,
                             mock_create_loadbalancer,
                             mock_delete_loadbalancer,
                             mock_reschedule):
        lb_body = {'algorithm': 'FAKE_ALGO1'}
        mock_loadbalancer_get.return_value = {
            'id': self.lb_id,
            'device_id': 'fakedeviceid',
            'name': 'fakename',
            'algorithm': 'FAKE_ALGO0',
            'protocol': 'FAKE_PROTO0',
        }
        mock_loadbalancer_update.return_value = lb_ref = {
            'id': self.lb_id,
            'device_id': 'fakedeviceid',
            'name': 'fakename',
            'algorithm': 'FAKE_ALGO1',
            'protocol': 'FAKE_PROTO0',
        }
        mock_reschedule.return_value = {'id': 'fakedeviceid'}
        sf_ref = {'id': 'fakesfid'}
        mock_serverfarm_get_all_by_lb_id.return_value = [sf_ref]
        predictor_ref = {'id': 'fakepredid'}
        mock_predictor_get_by_sf_id.return_value = predictor_ref

        # assume core.commands.delete_loadbalancer raises error
        mock_delete_loadbalancer.side_effect = exception.Invalid
        self.assertRaises(exception.Invalid, api.update_lb, self.conf,
                          'faketenantid', self.lb_id, lb_body, async=False)
        mock_loadbalancer_update.assert_has_calls([
            mock.call(self.conf, self.lb_id, lb_ref),
            mock.call(self.conf, self.lb_id, {'status': 'ERROR'}), ])

        # assume core.commands.create_loadbalancer raises error
        mock_delete_loadbalancer.side_effect = None
        mock_loadbalancer_update.reset_mock()
        mock_loadbalancer_get.return_value['algorithm'] = 'FAKE_ALGO0'
        mock_create_loadbalancer.side_effect = exception.Invalid
        self.assertRaises(exception.Invalid, api.update_lb, self.conf,
                          'faketenantid', self.lb_id, lb_body, async=False)
        mock_loadbalancer_update.assert_has_calls([
            mock.call(self.conf, self.lb_id, lb_ref),
            mock.call(self.conf, self.lb_id, {'status': 'ERROR'}), ])

    @mock.patch("balancer.db.api.virtualserver_destroy_by_sf_id")
    @mock.patch("balancer.db.api.predictor_destroy_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_destroy")
    @mock.patch("balancer.db.api.loadbalancer_destroy")
    @mock.patch("balancer.db.api.server_destroy_by_sf_id")
    @mock.patch("balancer.db.api.sticky_destroy_by_sf_id")
    @mock.patch("balancer.db.api.probe_destroy_by_sf_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.virtualserver_get_all_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.delete_loadbalancer")
    def test_delete_lb(self, *mocks):
        mocks[2].return_value = mock.MagicMock()
        api.delete_lb(self.conf, 'fake_tenant', self.lb_id)
        for m in mocks:
            self.assertTrue(m.called, "Mock %s wasn't called"
                    % m._mock_name)

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.server_create")
    @mock.patch("balancer.db.api.server_pack_extra")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.add_node_to_loadbalancer")
    def test_lb_add_nodes(self, *mocks):
        mocks[2].return_value = {'device_id': 1}
        mocks[3].return_value = [{'id': 1}]
        api.lb_add_nodes(self.conf, 'fake_tenant', self.lb_id, self.lb_nodes)
        for mok in mocks:
            self.assertTrue(mok.called, "This mock didn't call %s"
                    % mok._mock_name)

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.server_get_all_by_sf_id")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    def test_lb_show_nodes(self, mock_serverfarm, mock_server, mock_unpack):
        mock_serverfarm.return_value = self.dict_list
        api.lb_show_nodes(self.conf, 'fake_tenant', 1)
        self.assertTrue(mock_serverfarm.called)
        self.assertTrue(mock_server.called)

    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.remove_node_from_loadbalancer")
    @mock.patch("balancer.db.api.server_get")
    @mock.patch("balancer.db.api.server_destroy")
    def test_lb_delete_node(self, *mocks):
        mocks[5].return_value = self.dict_list
        api.lb_delete_node(self.conf,
                'fake_tenant', self.lb_id, self.lb_node_id)
        for mock in mocks:
            self.assertTrue(mock.called)

    @mock.patch("balancer.db.api.serverfarm_get")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.server_update")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.activate_rserver")
    @mock.patch("balancer.db.api.server_get")
    def test_lb_change_node_status_0(self, *mocks):
        """Activate server called"""
        lb_node_status = "inservice"
        api.lb_change_node_status(self.conf,
                'fake_tenant', self.lb_id, self.lb_node_id, lb_node_status)
        for mock in mocks:
            self.assertTrue(mock.called)

    @mock.patch("balancer.db.api.serverfarm_get")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.server_update")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.suspend_rserver")
    @mock.patch("balancer.db.api.server_get")
    def test_lb_change_node_status_1(self, *mocks):
        """Suspend server called"""
        lb_node_status = ""
        api.lb_change_node_status(self.conf,
                'fake_tenant', self.lb_id, self.lb_node_id, lb_node_status)
        for mock in mocks:
            self.assertTrue(mock.called)

    @mock.patch("balancer.db.api.serverfarm_get")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.server_update")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.activate_rserver")
    @mock.patch("balancer.core.commands.suspend_rserver")
    @mock.patch("balancer.db.api.server_get")
    def test_lb_change_node_status_2(self, *mocks):
        """return ok"""
        mocks[0].return_value = {'sf_id': 1, 'state': 'status'}
        api.lb_change_node_status(self.conf,
                'fake_tenant', self.lb_id, self.lb_node_id, 'status')
        self.assertFalse(mocks[1].called)
        self.assertFalse(mocks[2].called)

    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.db.api.server_create")
    @mock.patch("balancer.db.api.server_update")
    @mock.patch("balancer.db.api.server_get")
    @mock.patch("balancer.db.api.server_destroy")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.serverfarm_get")
    @mock.patch("balancer.core.commands.delete_rserver_from_server_farm")
    @mock.patch("balancer.core.commands.add_rserver_to_server_farm")
    def test_lb_update_node_0(self, mock_com0, mock_com1, *mocks):
        """"""
        api.lb_update_node(self.conf,
                'fake_tenant', self.lb_id, self.lb_node_id, self.lb_node)
        self.assertTrue(mock_com0.called)
        self.assertTrue(mock_com1.called)

    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.db.api.server_update")
    @mock.patch("balancer.db.api.server_get")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.serverfarm_get")
    @mock.patch("balancer.core.commands.delete_rserver_from_server_farm")
    @mock.patch("balancer.core.commands.add_rserver_to_server_farm")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_update_node(self, mock_extra, mock_command1, mock_command2,
                            mock_sf, mock_lb, mock_get, mock_update,
                            mock_driver):
        """"""
        mock_extra.return_value = self.dictionary
        mock_lb.return_value.__getitem__.return_value = 2
        resp = api.lb_update_node(self.conf,
                'fake_tenant', self.lb_id, self.lb_node_id, self.lb_node)
        self.assertEqual(resp, self.dictionary)
        mock_update.assert_called_once_with(self.conf,
                                            mock_get.return_value['id'],
                                            mock_get.return_value)
        mock_extra.assert_called_once_with(mock_update.return_value)
        mock_get.assert_called_once_with(self.conf,
                self.lb_node_id, tenant_id='fake_tenant')
        mock_sf.assert_called_once_with(self.conf,
                                        mock_get.return_value['sf_id'])
        mock_lb.assert_called_once_with(self.conf, self.lb_id)
        mock_driver.assert_called_once_with(self.conf, 2)
        with mock_driver.return_value.request_context() as ctx:
            mock_command1.assert_called_once_with(ctx, mock_sf.return_value,
                                                  mock_update.return_value)
            mock_command2.assert_called_once_with(ctx, mock_sf.return_value,
                                                  mock_get.return_value)

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    def test_lb_show_probes_0(self, db_api0, db_api1, db_api2):
        db_api0.return_value = self.dict_list
        db_api1.return_value.__getitem__.return_value.\
                             __getitem__.return_value = 2
        db_api2.return_value = {'probe': 'foo'}
        resp = api.lb_show_probes(self.conf, 'fake_tenant', self.lb_id)
        self.assertTrue(db_api1.called)
        self.assertTrue(db_api2.called)
        self.assertTrue(db_api2.call_count == 2)
        self.assertEqual(resp, {'healthMonitoring': [{'probe': 'foo'},
                                                     {'probe': 'foo'}]})
        db_api0.assert_called_once_with(self.conf, 2)
        db_api1.assert_called_once_with(self.conf,
                self.lb_id, tenant_id='fake_tenant')
        db_api2.assert_any_call(self.dict_list[0])
        db_api2.assert_any_call(self.dict_list[1])

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.probe_get_all_by_sf_id")
    def test_lb_show_probes_1(self, db_api0, db_api1, db_api2):
        db_api1.return_value = []
        with self.assertRaises(exc.ServerFarmNotFound):
            api.lb_show_probes(self.conf, 'fake_tenant', self.lb_id)
            self.assertFalse(db_api0.called)
            self.assertFalse(db_api2.called)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.probe_pack_extra")
    @mock.patch("balancer.db.api.probe_create")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.add_probe_to_loadbalancer")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_add_probe_0(self, mock_unpack, mock_command, mock_driver,
                            mock_create, mock_pack, mock_sf, mock_lb):
        """lb_probe['type']!=None"""
        lb_probe = {'type': 'Gvido'}
        mock_sf.return_value.__getitem__.return_value = {'id': 'foo'}
        mock_unpack.return_value = self.dictionary
        resp = api.lb_add_probe(self.conf, 'fake_tenant', self.lb_id, lb_probe)
        self.assertEqual(resp, self.dictionary)
        mock_unpack.assert_called_once_with(mock_create.return_value)
        mock_pack.assert_called_once_with(lb_probe)
        mock_create.assert_called_once_with(self.conf, mock_pack.return_value)
        mock_sf.assert_called_once_with(self.conf, mock_lb.return_value['id'])
        mock_lb.assert_called_once_with(self.conf,
                self.lb_id, tenant_id='fake_tenant')
        with mock_driver.return_value.request_context() as ctx:
            mock_command.assert_called_once_with(ctx, {'id': 'foo'},
                                                 mock_create.return_value)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.probe_pack_extra")
    @mock.patch("balancer.db.api.probe_create")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.add_probe_to_loadbalancer")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_add_probe_1(self, *mocks):
        """lb_probe['type']=None"""
        lb_probe = {'type': None}
        resp = api.lb_add_probe(self.conf, 'fake_tenant', self.lb_id, lb_probe)
        self.assertEqual(resp, None)
        for mock in mocks:
            self.assertFalse(mock.called)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    def test_lb_add_probe_2(self, mock_sf, mock_lb):
        """Exception"""
        lb_probe = {'type': 'Gvido'}
        mock_sf.return_value = []
        with self.assertRaises(exc.ServerFarmNotFound):
            api.lb_add_probe(self.conf, 'fake_tenant', self.lb_id, lb_probe)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.probe_pack_extra")
    @mock.patch("balancer.db.api.probe_create")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.add_probe_to_loadbalancer")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_add_probe_2(self, *mocks):
        """lb_probe['type']!=None"""
        lb_probe = {'type': 'Gvido'}
        mocks[5].side_effect = IndexError
        with self.assertRaises(exc.ServerFarmNotFound):
            api.lb_add_probe(self.conf, 'fake_tenant', self.lb_id, lb_probe)
   #     for mok in mocks:
   #         self.assertTrue(mok.called)

    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.db.api.probe_get")
    @mock.patch("balancer.db.api.probe_destroy")
    @mock.patch("balancer.core.commands.remove_probe_from_server_farm")
    def test_lb_delete_probe(self, *mocks):
        mocks[5].return_value = self.dict_list
        api.lb_delete_probe(self.conf, 'fake_tenant', self.lb_id, self.lb_id)
        for mok in mocks:
            self.assertTrue(mok.called)

    @mock.patch("balancer.db.api.unpack_extra", autospec=True)
    @mock.patch("balancer.core.commands.create_vip", autospec=True)
    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    @mock.patch("balancer.db.api.virtualserver_create", autospec=True)
    @mock.patch("balancer.db.api.virtualserver_pack_extra", autospec=True)
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id", autospec=True)
    @mock.patch("balancer.db.api.loadbalancer_get", autospec=True)
    def test_lb_add_vip(self,
                        mock_loadbalancer_get,
                        mock_serverfarm_get_all_by_lb_id,
                        mock_virtualserver_pack_extra,
                        mock_virtualserver_create,
                        mock_get_device_driver,
                        mock_create_vip,
                        mock_unpack_extra):
        # Mock
        lb_ref = {
            'id': 'fakelbid',
            'device_id': 'fakedeviceid',
            'protocol': 'HTTP',
        }
        mock_loadbalancer_get.return_value = lb_ref
        sf_ref = mock.MagicMock()
        sf_ref.__getitem__.return_value = 'fakesfid'
        mock_serverfarm_get_all_by_lb_id.return_value = [sf_ref]
        mock_virtualserver_pack_extra.return_value = {}
        mock_virtualserver_create.return_value = vip_ref = mock.Mock()
        ctx = mock.MagicMock()
        ctx.__enter__.return_value = enter_ctx = mock.Mock()
        mock_get_device_driver.return_value = \
            mock.Mock(request_context=mock.Mock(return_value=ctx))
        # Call
        api.lb_add_vip(self.conf, 'fake_tenant', 'fakelbid', 'fakevipdict')
        # Assert
        mock_loadbalancer_get.assert_called_once_with(self.conf,
                'fakelbid', tenant_id='fake_tenant')
        mock_serverfarm_get_all_by_lb_id.assert_called_once_with(self.conf,
                                                                 'fakelbid')
        mock_virtualserver_pack_extra.assert_called_once_with('fakevipdict')
        mock_virtualserver_create.assert_called_once_with(self.conf, {
            'lb_id': 'fakelbid',
            'sf_id': 'fakesfid',
            'extra': {
                'protocol': 'HTTP',
            },
        })
        mock_get_device_driver.assert_called_once_with(self.conf,
                                                       'fakedeviceid')
        mock_create_vip.assert_called_once_with(enter_ctx, vip_ref, sf_ref)
        mock_unpack_extra.assert_called_once_with(vip_ref)

    @mock.patch("balancer.db.api.unpack_extra", autospec=True)
    @mock.patch("balancer.core.commands.create_vip", autospec=True)
    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    @mock.patch("balancer.db.api.virtualserver_create", autospec=True)
    @mock.patch("balancer.db.api.virtualserver_pack_extra", autospec=True)
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id", autospec=True)
    @mock.patch("balancer.db.api.loadbalancer_get", autospec=True)
    def test_lb_add_vip_failed(self,
                               mock_loadbalancer_get,
                               mock_serverfarm_get_all_by_lb_id,
                               mock_virtualserver_pack_extra,
                               mock_virtualserver_create,
                               mock_get_device_driver,
                               mock_create_vip,
                               mock_unpack_extra):
        mock_serverfarm_get_all_by_lb_id.return_value = []
        with self.assertRaises(exc.ServerFarmNotFound):
            api.lb_add_vip(self.conf, 'fake_tenant', 'fakelbid', 'fakevipdict')
        self.assertTrue(mock_loadbalancer_get.called)
        self.assertTrue(mock_serverfarm_get_all_by_lb_id.called)
        self.assertFalse(mock_virtualserver_pack_extra.called)
        self.assertFalse(mock_virtualserver_create.called)
        self.assertFalse(mock_get_device_driver.called)
        self.assertFalse(mock_create_vip.called)
        self.assertFalse(mock_unpack_extra.called)

    @mock.patch("balancer.core.commands.delete_vip", autospec=True)
    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    @mock.patch("balancer.db.api.virtualserver_destroy", autospec=True)
    @mock.patch("balancer.db.api.virtualserver_get", autospec=True)
    @mock.patch("balancer.db.api.loadbalancer_get", autospec=True)
    def test_lb_delete_vip(self,
                           mock_loadbalancer_get,
                           mock_virtualserver_get,
                           mock_virtualserver_destroy,
                           mock_get_device_driver,
                           mock_delete_vip):
        # Mock
        mock_loadbalancer_get.return_value = lb_ref = mock.MagicMock()
        lb_ref.__getitem__.return_value = 'fakedeviceid'
        mock_virtualserver_get.return_value = vip_ref = mock.Mock()
        ctx = mock.MagicMock()
        ctx.__enter__.return_value = enter_ctx = mock.Mock()
        mock_get_device_driver.return_value = \
            mock.Mock(request_context=mock.Mock(return_value=ctx))
        # Call
        api.lb_delete_vip(self.conf, 'fake_tenant', 'fakelbid', 'fakevipid')
        # Assert
        mock_loadbalancer_get.assert_called_once_with(self.conf,
                'fakelbid', tenant_id='fake_tenant')
        mock_virtualserver_get.assert_called_once_with(self.conf, 'fakevipid')
        mock_virtualserver_destroy.assert_called_once_with(self.conf,
                                                           'fakevipid')
        mock_get_device_driver.assert_called_once_with(self.conf,
                                                       'fakedeviceid')
        mock_delete_vip.assert_called_once_with(enter_ctx, vip_ref)

    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_show_sticky0(self, db_api0, db_api1, db_api2):
        db_api0.return_value = {'sticky': 'foo'}
        db_api1.return_value = self.dict_list
        db_api2.return_value.__getitem__.return_value.\
                             __getitem__.return_value = 2
        resp = api.lb_show_sticky(self.conf, 'fake_tenant', self.lb_id)
        self.assertEqual(resp, {"sessionPersistence": [{'sticky': 'foo'},
                                                       {'sticky': 'foo'}]})
        self.assertTrue(db_api0.called)
        self.assertTrue(db_api0.call_count == 2)
        self.assertTrue(db_api1.called)
        self.assertTrue(db_api2.called)
        db_api0.assert_any_call(self.dict_list[0])
        db_api0.assert_any_call(self.dict_list[1])
        db_api1.assert_called_once_with(self.conf, 2)
        db_api2.assert_called_once_with(self.conf,
                self.lb_id, tenant_id='fake_tenant')

    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.sticky_get_all_by_sf_id")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_lb_show_sticky1(self, db_api0, db_api1, db_api2):
        db_api2.return_value = []
        with self.assertRaises(exc.ServerFarmNotFound):
            api.lb_show_sticky(self.conf, 'fake_tenant', self.lb_id)
            self.assertFalse(db_api0.called)
            self.assertFalse(db_api1.called)

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.sticky_create")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.sticky_pack_extra")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.add_sticky_to_loadbalancer")
    def test_lb_add_sticky0(self, *mocks):
        mocks[4].return_value = self.dict_list
        sticky = mock.MagicMock()
        api.lb_add_sticky(self.conf, 'fake_tenant', self.lb_id, sticky)
        for mok in mocks:
            self.assertTrue(mok.called)

    @mock.patch("balancer.db.api.unpack_extra")
    @mock.patch("balancer.db.api.sticky_create")
    @mock.patch("balancer.db.api.serverfarm_get_all_by_lb_id")
    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.sticky_pack_extra")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.add_sticky_to_loadbalancer")
    def test_lb_add_sticky1(self, *mocks):
        sticky = {'type': None}
        resp = api.lb_add_sticky(self.conf, 'fake_tenant', self.lb_id, sticky)
        self.assertEqual(resp, None)
        for mock in mocks:
            self.assertFalse(mock.called)

    @mock.patch("balancer.db.api.loadbalancer_get")
    @mock.patch("balancer.db.api.sticky_get")
    @mock.patch("balancer.db.api.sticky_destroy")
    @mock.patch("balancer.drivers.get_device_driver")
    @mock.patch("balancer.core.commands.remove_sticky_from_loadbalancer")
    def test_lb_delete_sticky(self, mock_command, mock_driver, mock_destroy,
                              mock_get, mock_bal):
        mock_bal.return_value = {'id': 2, 'device_id': 2}
        resp = api.lb_delete_sticky(self.conf, 'fake_tenant', self.lb_id, 1)
        self.assertEqual(resp, 1)
        mock_bal.assert_called_once_with(self.conf,
                self.lb_id, tenant_id='fake_tenant')
        mock_get.assert_called_once_with(self.conf, 1)
        mock_destroy.assert_called_once_with(self.conf, 1)
        mock_driver.assert_called_once_with(self.conf, 2)
        with mock_driver.return_value.request_context() as ctx:
            mock_command.assert_called_once_with(ctx, mock_bal.return_value,
                                                 mock_get.return_value)


class TestDevice(unittest.TestCase):
    def setUp(self):
        self.conf = mock.MagicMock(register_group=mock.MagicMock)
        self.dict_list = ({'id': 1}, {'id': 2},)

    @mock.patch("balancer.db.api.device_get_all")
    @mock.patch("balancer.db.api.unpack_extra")
    def test_device_get_index(self, mock_f1, mock_f2):
        mock_f1.side_effect = [{'device': 1}, {'device': 2}]
        mock_f2.return_value = [[{'id': 1}], [{'id': 2}]]
        resp = api.device_get_index(self.conf)
        self.assertEqual(resp, [{'device': 1}, {'device': 2}])
        self.assertTrue(mock_f1.called)
        self.assertTrue(mock_f2.called)
        mock_f1.assert_any_call([{'id': 1}])
        mock_f1.assert_any_call([{'id': 2}])
        mock_f2.assert_called_once_with(self.conf)

    @mock.patch("balancer.db.api.device_pack_extra")
    @mock.patch("balancer.db.api.device_create")
    def test_device_create(self,  mock_f1, mock_f2):
        mock_f1.return_value = {'id': 1}
        resp = api.device_create(self.conf)
        self.assertEqual(resp['id'], 1)
        self.assertTrue(mock_f1.called, "device_create not called")
        self.assertTrue(mock_f2.called, "device_pack_extra not called")
        mock_f1.assert_caleld_once_with(self.conf, mock_f2.return_value)
        mock_f2.assert_called_once_with({})

    def test_device_info(self):
        params = {'query_params': 2}
        res = api.device_info(params)
        self.assertEquals(res, None, "Alyarma!")

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.drivers.get_device_driver')
    def test_device_show_algorithms_0(self, mock_driver, mock_db_api):
        """capabilities = None"""
        mock_driver.get_capabilities = None
        mock_db_api.return_value = self.dict_list
        resp = api.device_show_algorithms(self.conf)
        self.assertEqual(resp, [])

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.drivers.get_device_driver')
    def test_device_show_algorithms_1(self, mock_driver, mock_db_api):
        """capabilities is not empty, not None"""
        mock_db_api.return_value = self.dict_list
        mock_driver.return_value = drv = mock.MagicMock()
        drv.get_capabilities.return_value = {"algorithms": ["CRYSIS"]}
        resp = api.device_show_algorithms(self.conf)
        self.assertEqual(resp, ["CRYSIS"])

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.drivers.get_device_driver')
    def test_device_show_algorithms_2(self, mock_driver, mock_db_api):
        """capabilities is empty"""
        mock_db_api.return_value = self.dict_list
        mock_driver.return_value = drv = mock.MagicMock()
        drv.get_capabilities.return_value = {}
        resp = api.device_show_algorithms(self.conf)
        self.assertEqual(resp, [])

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.drivers.get_device_driver')
    def test_show_protocols_0(self, mock_driver, mock_db_api):
        """capabilities = None"""
        mock_driver.get_capabilities = None
        mock_db_api.return_value = self.dict_list
        resp = api.device_show_protocols(self.conf)
        self.assertEqual(resp, [])

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.drivers.get_device_driver')
    def test_show_protocols_1(self, mock_driver, mock_db_api):
        """capabilities"""
        mock_db_api.return_value = self.dict_list
        mock_driver.return_value = drv = mock.MagicMock()
        drv.get_capabilities.return_value = {"protocols": ["CRYSIS"]}
        resp = api.device_show_protocols(self.conf)
        self.assertEqual(resp, ["CRYSIS"])

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.drivers.get_device_driver')
    def test_show_protocols_2(self, mock_driver, mock_db_api):
        """capabilities"""
        mock_db_api.return_value = self.dict_list
        mock_driver.return_value = drv = mock.MagicMock()
        drv.get_capabilities.return_value = {}
        resp = api.device_show_protocols(self.conf)
        self.assertEqual(resp, [])

########NEW FILE########
__FILENAME__ = test_db_api
import unittest
import mock
import tempfile
import datetime
import os
import shutil

from balancer.db import api as db_api
from balancer.db import session
from balancer import exception
from balancer.core import lb_status


device_fake1 = {'name': 'fake1',
                'type': 'FAKE',
                'version': '1',
                'ip': '10.0.0.10',
                'port': 1010,
                'user': 'user1',
                'password': 'secrete1',
                'extra': {'supports_vlan': False}}

device_fake2 = {'name': 'fake2',
                'type': 'FAKE',
                'version': '2',
                'ip': '10.0.0.20',
                'port': 2020,
                'user': 'user2',
                'password': 'secrete2',
                'extra': {'supports_vlan': True,
                          'vip_vlan': 10,
                          'requires_vip_ip': True}}


def get_fake_probe(sf_id):
    probe = {'sf_id': sf_id,
             'name': 'probe1',
             'type': 'ICMP',
             'deployed': 'True',
             'extra': {'delay': 10,
                       'attemptsDeforeDeactivation': 5,
                       'timeout': 10}}
    return probe


def get_fake_lb(device_id, tenant_id):
    lb = {'device_id': device_id,
          'name': 'lb1',
          'algorithm': 'ROUNDROBIN',
          'protocol': 'HTTP',
          'status': 'INSERVICE',
          'tenant_id': tenant_id,
          'created_at': datetime.datetime(2000, 01, 01, 12, 00, 00),
          'updated_at': datetime.datetime(2000, 01, 02, 12, 00, 00),
          'deployed': 'True',
          'extra': {}}
    return lb


def get_fake_sf(lb_id):
    sf = {'lb_id': lb_id,
          'name': 'serverfarm1',
          'type': 'UNKNOWN',
          'status': 'UNKNOWN',
          'deployed': 'True',
          'extra': {}}
    return sf


def get_fake_virtualserver(sf_id, lb_id):
    vip = {'sf_id': sf_id,
           'lb_id': lb_id,
           'name': 'vip1',
           'address': '10.0.0.30',
           'mask': '255.255.255.255',
           'port': '80',
           'status': 'UNKNOWN',
           'deployed': 'True',
           'extra': {'ipVersion': 'IPv4',
                     'VLAN': 200,
                     'ICMPreply': True}}
    return vip


def get_fake_server(sf_id, vm_id, address='100.1.1.25', parent_id=None):
    server = {'sf_id': sf_id,
              'name': 'server1',
              'type': 'HOST',
              'address': address,

              'port': '8080',
              'weight': 2,
              'status': 'INSERVICE',
              'parent_id': parent_id,
              'deployed': 'True',
              'vm_id': vm_id,
              'extra': {'minCon': 300000,
                        'maxCon': 400000,
                        'rateBandwidth': 12,
                        'rateConnection': 1000}}
    return server


def get_fake_sticky(sf_id):
    sticky = {'sf_id': sf_id,
              'name': 'sticky1',
              'type': 'HTTP-COOKIE',
              'deployed': 'True',
              'extra': {'cookieName': 'testHTTPCookie',
                        'enableInsert': True,
                        'browserExpire': True,
                        'offset': True,
                        'length': 10,
                        'secondaryName': 'cookie'}}
    return sticky


def get_fake_predictor(sf_id):
    predictor = {'sf_id': sf_id,
                 'type': 'ROUNDROBIN',
                 'deployed': 'True',
                 'extra': {}}
    return predictor


class TestExtra(unittest.TestCase):
    @mock.patch("balancer.db.api.pack_update")
    def test_pack_extra(self, mock):
        model = mock.MagicMock()
        values = {'name': 'fakename', 'type': 'faketype', 'other': 'fakeother'}
        db_api.pack_extra(model, values)
        self.assertTrue(mock.called)

    def test_unpack_extra(self):
        obj_ref = {'name': 'fakename',
                   'type': 'faketype',
                   'extra': {'other': 'fakeother'}}
        values = db_api.unpack_extra(obj_ref)
        expected = {'name': 'fakename',
                    'type': 'faketype',
                    'other': 'fakeother'}
        self.assertEqual(values, expected)

    def test_pack_update_0(self):
        """1 way"""
        obj_ref = {'name': 'fakename', 'type': 'faketype',
                   'other': 'fakeother',
                   'extra': {'dejkstra': 'dejkstra'}}
        values = {'name': 'fakename', 'type': 'faketype', 'other': 'fakeother',
                'extra': {}}
        db_api.pack_update(obj_ref, values)
        self.assertEqual(values, obj_ref)

    def test_pack_update_1(self):
        """else way"""
        values = {'name': 'fakename', 'type': 'faketype',
                  'other': 'fakeother',
                  'dejkstra': 'dejkstra'}
        obj_ref = {'name': 'fakename', 'type': 'faketype',
                   'other': 'fakeother',
                   'extra': {}}
        final = {'name': 'fakename', 'type': 'faketype', 'other': 'fakeother',
                'extra': {'dejkstra': 'dejkstra'}}
        db_api.pack_update(obj_ref, values)
        self.assertEqual(obj_ref, final)

    def test_pack_update_2(self):
        """else way"""
        values = {'name': 'fakename', 'type': 'faketype', 'other': 'fakeother',
                'dejkstra': 'dejkstra'}
        obj_ref = {'name': 'fakename', 'type': 'faketype',
                   'other': 'fakeother',
                   'extra': {'dejkstra': 'fool'}}
        final = {'name': 'fakename', 'type': 'faketype', 'other': 'fakeother',
                'extra': {'dejkstra': 'dejkstra'}}
        db_api.pack_update(obj_ref, values)
        self.assertEqual(obj_ref, final)


class TestDBAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.golden_filename = tempfile.mkstemp()
        conf = mock.Mock()
        conf.sql.connection = "sqlite:///%s" % (cls.golden_filename,)
        session.sync(conf)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.golden_filename)

    def setUp(self):
        self.maxDiff = None
        _, self.filename = tempfile.mkstemp()
        self.conf = mock.Mock()
        self.conf.sql.connection = "sqlite:///%s" % self.filename
        shutil.copyfile(self.golden_filename, self.filename)

    def tearDown(self):
        os.remove(self.filename)

    def test_device_create(self):
        device_ref = db_api.device_create(self.conf, device_fake1)
        device = dict(device_ref.iteritems())
        expected = device_fake1.copy()
        self.assertIsNotNone(device['id'])
        expected['id'] = device['id']
        self.assertEqual(device, expected)

    def test_device_update(self):
        device_ref = db_api.device_create(self.conf, device_fake1)
        self.assertIsNotNone(device_ref['id'])
        update = {'password': 'test',
                  'extra': {'supports_vlan': True,
                            'vip_vlan': 100,
                            'requires_vip_ip': True}}
        device_ref = db_api.device_update(self.conf, device_ref['id'], update)
        device = dict(device_ref.iteritems())
        expected = device_fake1.copy()
        expected.update(update)
        self.assertIsNotNone(device['id'])
        expected['id'] = device['id']
        self.assertEqual(device, expected)

    def test_device_get_all(self):
        device_ref1 = db_api.device_create(self.conf, device_fake1)
        device_ref2 = db_api.device_create(self.conf, device_fake2)
        devices = db_api.device_get_all(self.conf)
        self.assertEqual([dict(dev.iteritems()) for dev in devices],
                         [dict(dev.iteritems()) for dev in [device_ref1,
                                                            device_ref2]])

    def test_device_get(self):
        device_ref1 = db_api.device_create(self.conf, device_fake1)
        device_ref2 = db_api.device_get(self.conf, device_ref1['id'])
        self.assertEqual(dict(device_ref1.iteritems()),
                         dict(device_ref2.iteritems()))

    def test_device_get_several(self):
        device_ref1 = db_api.device_create(self.conf, device_fake1)
        device_ref2 = db_api.device_create(self.conf, device_fake2)
        device_ref3 = db_api.device_get(self.conf, device_ref1['id'])
        device_ref4 = db_api.device_get(self.conf, device_ref2['id'])
        self.assertEqual(dict(device_ref3.iteritems()),
                         dict(device_ref1.iteritems()))
        self.assertEqual(dict(device_ref4.iteritems()),
                         dict(device_ref2.iteritems()))

    def test_device_destroy(self):
        device_ref = db_api.device_create(self.conf, device_fake1)
        db_api.device_destroy(self.conf, device_ref['id'])
        with self.assertRaises(exception.DeviceNotFound) as cm:
            db_api.device_get(self.conf, device_ref['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'device_id': device_ref['id']})

    def _create_lb_and_sf(self, device_id, tenant_id):
        lb_values = get_fake_lb(device_id, tenant_id)
        lb_ref = db_api.loadbalancer_create(self.conf, lb_values)
        sf_values = get_fake_sf(lb_ref['id'])
        sf_ref = db_api.serverfarm_create(self.conf, sf_values)
        return lb_ref['id'], sf_ref['id']

    def test_loadbalancer_create(self):
        values = get_fake_lb('1', 'tenant1')
        lb_ref = db_api.loadbalancer_create(self.conf, values)
        lb = dict(lb_ref.iteritems())
        self.assertIsNotNone(lb['id'])
        values['id'] = lb['id']
        self.assertEqual(lb, values)

    def test_loadbalancer_update(self):
        values = get_fake_lb('1', 'tenant1')
        lb_ref = db_api.loadbalancer_create(self.conf, values)
        update = {'protocol': 'FTP',
                  'extra': {'extrafield': 'extravalue'}}
        lb_ref = db_api.loadbalancer_update(self.conf, lb_ref['id'],
                                            update)
        lb = dict(lb_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(lb['id'])
        values['id'] = lb['id']
        values['updated_at'] = lb['updated_at']
        self.assertEqual(lb, values)

    def test_loadbalancer_get(self):
        values = get_fake_lb('1', 'tenant1')
        lb_ref1 = db_api.loadbalancer_create(self.conf, values)
        lb_ref2 = db_api.loadbalancer_get(self.conf, lb_ref1['id'])
        self.assertEqual(dict(lb_ref1.iteritems()),
                         dict(lb_ref2.iteritems()))

    def test_loadbalancer_get_with_tenant(self):
        db_api.loadbalancer_create(self.conf, get_fake_lb('1', 'tenant1'))
        values = get_fake_lb('2', 'tenant2')
        lb_ref1 = db_api.loadbalancer_create(self.conf, values)
        lb_ref2 = db_api.loadbalancer_get(self.conf,
                lb_ref1['id'], tenant_id='tenant2')
        self.assertEqual(dict(lb_ref1.iteritems()),
                         dict(lb_ref2.iteritems()))

    def test_loadbalancer_get_with_tenant_fails(self):
        values = get_fake_lb('1', 'tenant1')
        lb_ref1 = db_api.loadbalancer_create(self.conf, values)
        with self.assertRaises(exception.LoadBalancerNotFound):
            db_api.loadbalancer_get(self.conf,
                    lb_ref1['id'], tenant_id='tenant2')

    def test_loadbalancer_get_all_by_project(self):
        values = get_fake_lb('1', 'tenant1')
        lb_ref1 = db_api.loadbalancer_create(self.conf, values)
        values = get_fake_lb('2', 'tenant2')
        lb_ref2 = db_api.loadbalancer_create(self.conf, values)
        lbs1 = db_api.loadbalancer_get_all_by_project(self.conf, 'tenant1')
        lbs2 = db_api.loadbalancer_get_all_by_project(self.conf, 'tenant2')
        self.assertEqual([dict(lb_ref1.iteritems())],
                         [dict(lb.iteritems()) for lb in lbs1])
        self.assertEqual([dict(lb_ref2.iteritems())],
                         [dict(lb.iteritems()) for lb in lbs2])
        self.assertNotEqual(lbs1[0]['id'], lbs2[0]['id'])

    def test_loadbalancer_get_all_by_vm_id(self):
        lb_fake1 = get_fake_lb('1', 'tenant1')
        lb_fake2 = get_fake_lb('2', 'tenant2')
        lb_ref1 = db_api.loadbalancer_create(self.conf, lb_fake1)
        lb_ref2 = db_api.loadbalancer_create(self.conf, lb_fake2)
        sf_fake1 = get_fake_sf(lb_ref1['id'])
        sf_fake2 = get_fake_sf(lb_ref2['id'])
        sf_ref1 = db_api.serverfarm_create(self.conf, sf_fake1)
        sf_ref2 = db_api.serverfarm_create(self.conf, sf_fake2)
        node_fake1 = get_fake_server(sf_ref1['id'], 1, '10.0.0.1')
        node_fake2 = get_fake_server(sf_ref1['id'], 20, '10.0.0.2')
        node_fake3 = get_fake_server(sf_ref2['id'], 1, '10.0.0.3')
        node_fake4 = get_fake_server(sf_ref2['id'], 30, '10.0.0.4')
        node_ref1 = db_api.server_create(self.conf, node_fake1)
        node_ref2 = db_api.server_create(self.conf, node_fake2)
        node_ref3 = db_api.server_create(self.conf, node_fake3)
        node_ref4 = db_api.server_create(self.conf, node_fake4)
        lbs1 = db_api.loadbalancer_get_all_by_vm_id(self.conf, 'tenant1', 1)
        lbs2 = db_api.loadbalancer_get_all_by_vm_id(self.conf, 'tenant2', 30)
        lbs3 = db_api.loadbalancer_get_all_by_vm_id(self.conf, 'tenant2', 20)
        self.assertEqual([dict(lb_ref1.iteritems())],
                         [dict(lb.iteritems()) for lb in lbs1])
        self.assertEqual([dict(lb_ref2.iteritems())],
                         [dict(lb.iteritems()) for lb in lbs2])
        self.assertFalse(lbs3)

    def test_loadbalancer_get_all_by_device_id(self):
        lb_fake1 = get_fake_lb('1', 'tenant1')
        lb_ref1 = db_api.loadbalancer_create(self.conf, lb_fake1)
        lbs1 = db_api.loadbalancer_get_all_by_device_id(self.conf, '1')
        with self.assertRaises(exception.LoadBalancerNotFound):
            db_api.loadbalancer_get_all_by_device_id(self.conf, '2')
        self.assertEqual([dict(lb_ref1.iteritems())],
                         [dict(lb.iteritems()) for lb in lbs1])

    def test_lb_count_active_by_device(self):
        lb_fake1 = get_fake_lb('1', 'tenant1')
        lb_fake2 = get_fake_lb('1', 'tenant2')
        lb_fake2['status'] = lb_status.ACTIVE
        lb_ref1 = db_api.loadbalancer_create(self.conf, lb_fake1)
        lb_ref2 = db_api.loadbalancer_create(self.conf, lb_fake2)
        result = db_api.lb_count_active_by_device(self.conf, '1')
        self.assertEqual(result, 1)

    def test_loadbalancer_destroy(self):
        values = get_fake_lb('1', 'tenant1')
        lb = db_api.loadbalancer_create(self.conf, values)
        db_api.loadbalancer_destroy(self.conf, lb['id'])
        with self.assertRaises(exception.LoadBalancerNotFound) as cm:
            db_api.loadbalancer_get(self.conf, lb['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'loadbalancer_id': lb['id']})

    def test_probe_create(self):
        values = get_fake_probe('1')
        probe_ref = db_api.probe_create(self.conf, values)
        probe = dict(probe_ref.iteritems())
        self.assertIsNotNone(probe['id'])
        values['id'] = probe['id']
        self.assertEqual(probe, values)

    def test_probe_get_all(self):
        values = get_fake_probe('1')
        probe_ref1 = db_api.probe_create(self.conf, values)
        probe_ref2 = db_api.probe_create(self.conf, values)
        probes = db_api.probe_get_all(self.conf)
        self.assertEqual([dict(probe.iteritems()) for probe in probes],
                         [dict(probe.iteritems()) for probe in [probe_ref1,
                                                                probe_ref2]])

    def test_probe_get_all_by_sf_id(self):
        values = get_fake_probe('1')
        pr1 = db_api.probe_create(self.conf, values)
        values = get_fake_probe('2')
        pr2 = db_api.probe_create(self.conf, values)
        probes1 = db_api.probe_get_all_by_sf_id(self.conf, '1')
        probes2 = db_api.probe_get_all_by_sf_id(self.conf, '2')
        self.assertEqual([dict(pr1.iteritems())],
                         [dict(pr.iteritems()) for pr in probes1])
        self.assertEqual([dict(pr2.iteritems())],
                         [dict(pr.iteritems()) for pr in probes2])

    def test_probe_update(self):
        values = get_fake_probe('1')
        probe_ref = db_api.probe_create(self.conf, values)
        update = {'name': 'test',
                  'extra': {'delay': 20,
                            'attemptsDeforeDeactivation': 5,
                            'timeout': 15}}
        probe_ref = db_api.probe_update(self.conf, probe_ref['id'], update)
        probe = dict(probe_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(probe['id'])
        values['id'] = probe['id']
        self.assertEqual(probe, values)

    def test_probe_get(self):
        values = get_fake_probe('1')
        probe_ref1 = db_api.probe_create(self.conf, values)
        probe_ref2 = db_api.probe_get(self.conf, probe_ref1['id'])
        self.assertEqual(dict(probe_ref1.iteritems()),
                         dict(probe_ref2.iteritems()))

    def test_probe_get_with_tenant_fails(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        probe_ref = db_api.probe_create(self.conf, get_fake_probe(sf_id))
        with self.assertRaises(exception.ProbeNotFound):
            db_api.probe_get(self.conf, probe_ref['id'], tenant_id='tenant2')

    def test_probe_destroy_by_sf_id(self):
        values1 = get_fake_probe('1')
        values2 = get_fake_probe('2')
        probe_ref1 = db_api.probe_create(self.conf, values1)
        probe_ref2 = db_api.probe_create(self.conf, values2)
        db_api.probe_destroy_by_sf_id(self.conf, '1')
        probes = db_api.probe_get_all(self.conf)
        self.assertEqual(len(probes), 1)
        self.assertEqual(dict(probe_ref2.iteritems()),
                         dict(probes[0].iteritems()))

    def test_probe_destroy(self):
        values = get_fake_probe('1')
        probe = db_api.probe_create(self.conf, values)
        db_api.probe_destroy(self.conf, probe['id'])
        with self.assertRaises(exception.ProbeNotFound) as cm:
            db_api.probe_get(self.conf, probe['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'probe_id': probe['id']})

    def test_sticky_create(self):
        values = get_fake_sticky('1')
        sticky_ref = db_api.sticky_create(self.conf, values)
        sticky = dict(sticky_ref.iteritems())
        self.assertIsNotNone(sticky['id'])
        values['id'] = sticky['id']
        self.assertEqual(sticky, values)

    def test_sticky_get_all(self):
        values = get_fake_sticky('1')
        st1 = db_api.sticky_create(self.conf, values)
        st2 = db_api.sticky_create(self.conf, values)
        stickies = [dict(sticky.iteritems()) for sticky
                                           in db_api.sticky_get_all(self.conf)]
        self.assertEqual(stickies, [dict(st.iteritems()) for st in [st1, st2]])

    def test_sticky_get_all_by_sf_id(self):
        values = get_fake_sticky('1')
        st1 = db_api.sticky_create(self.conf, values)
        values = get_fake_sticky('2')
        st2 = db_api.sticky_create(self.conf, values)
        stickies1 = db_api.sticky_get_all_by_sf_id(self.conf, '1')
        stickies2 = db_api.sticky_get_all_by_sf_id(self.conf, '2')
        self.assertEqual(len(stickies1), 1)
        self.assertEqual(dict(st1.iteritems()), dict(stickies1[0].iteritems()))
        self.assertEqual(len(stickies2), 1)
        self.assertEqual(dict(st2.iteritems()), dict(stickies2[0].iteritems()))

    def test_sticky_update(self):
        values = get_fake_sticky('1')
        sticky_ref = db_api.sticky_create(self.conf, values)
        update = {'name': 'test',
                  'extra': {'cookieName': 'testHTTPCookie',
                            'enableInsert': True,
                            'browserExpire': False,
                            'offset': False,
                            'length': 1000,
                            'secondaryName': 'cookie'}}
        sticky_ref = db_api.sticky_update(self.conf, sticky_ref['id'], update)
        sticky = dict(sticky_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(sticky['id'])
        values['id'] = sticky['id']
        self.assertEqual(sticky, values)

    def test_sticky_get(self):
        values = get_fake_sticky('1')
        sticky_ref1 = db_api.sticky_create(self.conf, values)
        sticky_ref2 = db_api.sticky_get(self.conf, sticky_ref1['id'])
        self.assertEqual(dict(sticky_ref1.iteritems()),
                         dict(sticky_ref2.iteritems()))

    def test_sticky_get_with_tenant_fails(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        sticky_ref = db_api.sticky_create(self.conf, get_fake_sticky(sf_id))
        with self.assertRaises(exception.StickyNotFound):
            db_api.sticky_get(self.conf, sticky_ref['id'], tenant_id='tenant2')

    def test_sticky_destroy_by_sf_id(self):
        values = get_fake_sticky('1')
        sticky_ref1 = db_api.sticky_create(self.conf, values)
        values = get_fake_sticky('2')
        sticky_ref2 = db_api.sticky_create(self.conf, values)
        db_api.sticky_destroy_by_sf_id(self.conf, '1')
        stickies = db_api.sticky_get_all(self.conf)
        self.assertEqual([dict(sticky_ref2.iteritems())],
                         [dict(st.iteritems()) for st in stickies])

    def test_sticky_destroy(self):
        values = get_fake_sticky('1')
        sticky = db_api.sticky_create(self.conf, values)
        db_api.sticky_destroy(self.conf, sticky['id'])
        with self.assertRaises(exception.StickyNotFound) as cm:
            db_api.sticky_get(self.conf, sticky['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'sticky_id': sticky['id']})

    def test_server_create(self):
        values = get_fake_server('1', 1)
        server_ref = db_api.server_create(self.conf, values)
        server = dict(server_ref.iteritems())
        self.assertIsNotNone(server['id'])
        values['id'] = server['id']
        self.assertEqual(server, values)

    def test_server_get_all(self):
        values = get_fake_server('1', 1)
        server1 = db_api.server_create(self.conf, values)
        server2 = db_api.server_create(self.conf, values)
        servers = db_api.server_get_all(self.conf)
        self.assertEqual([dict(server.iteritems()) for server in servers],
                         [dict(server.iteritems()) for server in [server1,
                                                                  server2]])

    def test_server_get_all_by_sf_id(self):
        values = get_fake_server('1', 1)
        sr1 = db_api.server_create(self.conf, values)
        sr2 = db_api.server_create(self.conf, values)
        values = get_fake_server('2', 1)
        sr3 = db_api.server_create(self.conf, values)
        sr4 = db_api.server_create(self.conf, values)
        servers1 = db_api.server_get_all_by_sf_id(self.conf, '1')
        servers2 = db_api.server_get_all_by_sf_id(self.conf, '2')

        self.assertEqual([dict(server.iteritems()) for server in servers1],
                         [dict(server.iteritems()) for server in [sr1, sr2]])
        self.assertEqual([dict(server.iteritems()) for server in servers2],
                         [dict(server.iteritems()) for server in [sr3, sr4]])

    def test_server_update(self):
        values = get_fake_server('1', 1)
        server_ref = db_api.server_create(self.conf, values)
        update = {'name': 'test',
                  'extra': {'cookieName': 'testHTTPCookie',
                            'enableInsert': True,
                            'browserExpire': False,
                            'offset': False,
                            'length': 1000,
                            'secondaryName': 'cookie'}}
        server_ref = db_api.server_update(self.conf, server_ref['id'], update)
        server = dict(server_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(server['id'])
        values['id'] = server['id']
        self.assertEqual(server, values)

    def test_server_get0(self):
        values = get_fake_server('1', 1)
        server_ref1 = db_api.server_create(self.conf, values)
        server_ref2 = db_api.server_get(self.conf, server_ref1['id'])
        self.assertEqual(dict(server_ref1.iteritems()),
                         dict(server_ref2.iteritems()))

    def test_server_get1(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        server_values = get_fake_server(sf_id, 1)
        server_ref1 = db_api.server_create(self.conf, server_values)
        server_ref2 = db_api.server_get(self.conf, server_ref1['id'], lb_id)
        self.assertEqual(dict(server_ref1.iteritems()),
                         dict(server_ref2.iteritems()))

    def test_server_get2(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        server_values = get_fake_server(sf_id, 1)
        server_ref1 = db_api.server_create(self.conf, server_values)
        server_ref2 = db_api.server_get(self.conf,
                server_ref1['id'], lb_id, tenant_id='tenant1')
        self.assertEqual(dict(server_ref1.iteritems()),
                         dict(server_ref2.iteritems()))

    def test_server_get2_fails(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        server_values = get_fake_server(sf_id, 1)
        server_ref1 = db_api.server_create(self.conf, server_values)
        with self.assertRaises(exception.ServerNotFound):
            db_api.server_get(self.conf,
                server_ref1['id'], lb_id, tenant_id='tenant2')

    def test_server_get3(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        server_values = get_fake_server(sf_id, 1)
        server_ref1 = db_api.server_create(self.conf, server_values)
        server_ref2 = db_api.server_get(self.conf,
                server_ref1['id'], tenant_id='tenant1')
        self.assertEqual(dict(server_ref1.iteritems()),
                         dict(server_ref2.iteritems()))

    def test_server_get3_fails(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        server_values = get_fake_server(sf_id, 1)
        server_ref1 = db_api.server_create(self.conf, server_values)
        with self.assertRaises(exception.ServerNotFound):
            db_api.server_get(self.conf,
                server_ref1['id'], tenant_id='tenant2')

    def test_server_destroy_by_sf_id(self):
        values = get_fake_server('1', 1)
        server_ref1 = db_api.server_create(self.conf, values)
        values = get_fake_server('2', 1)
        server_ref2 = db_api.server_create(self.conf, values)
        db_api.server_destroy_by_sf_id(self.conf, '1')
        servers = db_api.server_get_all(self.conf)
        self.assertEqual([dict(server_ref2.iteritems())],
                         [dict(server.iteritems()) for server in servers])

    def test_server_destroy(self):
        values = get_fake_server('1', 1)
        server = db_api.server_create(self.conf, values)
        db_api.server_destroy(self.conf, server['id'])
        with self.assertRaises(exception.ServerNotFound) as cm:
            db_api.server_get(self.conf, server['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'server_id': server['id']})

    def test_server_get_by_address(self):
        values1 = get_fake_server('1', 1, '10.0.0.1')
        values2 = get_fake_server('1', 1, '10.0.0.2')
        server1 = db_api.server_create(self.conf, values1)
        server2 = db_api.server_create(self.conf, values2)
        server = db_api.server_get_by_address(self.conf, '10.0.0.1')
        self.assertEqual(dict(server.iteritems()), dict(server1.iteritems()))
        with self.assertRaises(exception.ServerNotFound) as cm:
            db_api.server_get_by_address(self.conf, '192.168.0.1')
        err = cm.exception
        self.assertEqual(err.kwargs, {'server_address': '192.168.0.1'})

    def test_server_get_by_address_on_device(self):
        lb_fake = get_fake_lb('1', 'tenant1')
        lb_ref = db_api.loadbalancer_create(self.conf, lb_fake)
        sf_fake = get_fake_sf(lb_ref['id'])
        sf_ref = db_api.serverfarm_create(self.conf, sf_fake)
        server_fake = get_fake_server(sf_ref['id'], 1, '10.0.0.1')
        server_ref = db_api.server_create(self.conf, server_fake)
        server = db_api.server_get_by_address_on_device(self.conf, '10.0.0.1',
                                                        '1')
        with self.assertRaises(exception.ServerNotFound) as cm:
            server = db_api.server_get_by_address_on_device(self.conf,
                                                            '10.0.0.2', '1')
        expected = {'server_address': '10.0.0.2',
                    'device_id': '1'}
        err = cm.exception
        self.assertEqual(err.kwargs, expected)
        with self.assertRaises(exception.ServerNotFound) as cm:
            server = db_api.server_get_by_address_on_device(self.conf,
                                                            '10.0.0.1', '2')
        err = cm.exception
        expected = {'server_address': '10.0.0.1',
                    'device_id': '2'}
        self.assertEqual(err.kwargs, expected)

    def test_server_get_all_by_parent_id(self):
        values1 = get_fake_server('1', 1, '10.0.0.1', 1)
        values2 = get_fake_server('1', 1, '10.0.0.2', 2)
        values3 = get_fake_server('1', 1, '10.0.0.3')
        server_ref1 = db_api.server_create(self.conf, values1)
        server_ref2 = db_api.server_create(self.conf, values2)
        server_ref3 = db_api.server_create(self.conf, values3)
        servers = db_api.server_get_all_by_parent_id(self.conf, 1)
        self.assertEqual([dict(server_ref1.iteritems())],
                         [dict(server.iteritems()) for server in servers])

    def test_serverfarm_create(self):
        values = get_fake_sf('1')
        serverfarm_ref = db_api.serverfarm_create(self.conf, values)
        serverfarm = dict(serverfarm_ref.iteritems())
        self.assertIsNotNone(serverfarm['id'])
        values['id'] = serverfarm['id']
        self.assertEqual(serverfarm, values)

    def test_serverfarm_get_all_by_lb_id(self):
        values1 = get_fake_sf('1')
        values2 = get_fake_sf('2')
        sf_ref1 = db_api.serverfarm_create(self.conf, values1)
        sf_ref2 = db_api.serverfarm_create(self.conf, values2)
        sfs1 = db_api.serverfarm_get_all_by_lb_id(self.conf, '1')
        sfs2 = db_api.serverfarm_get_all_by_lb_id(self.conf, '2')
        self.assertEqual([dict(sf_ref1.iteritems())],
                         [dict(sf.iteritems()) for sf in sfs1])
        self.assertEqual([dict(sf_ref2.iteritems())],
                         [dict(sf.iteritems()) for sf in sfs2])

    def test_serverfarm_get_all_by_lb_id1(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        res = db_api.serverfarm_get_all_by_lb_id(self.conf,
                lb_id, tenant_id='tenant2')
        self.assertEqual([], res)

    def test_serverfarm_update(self):
        values = get_fake_sf('1')
        serverfarm_ref = db_api.serverfarm_create(self.conf, values)
        update = {'name': 'test',
                  'extra': {'extrafield': 'extravalue'}}
        serverfarm_ref = db_api.serverfarm_update(self.conf,
                                                  serverfarm_ref['id'],
                                                  update)
        serverfarm = dict(serverfarm_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(serverfarm['id'])
        values['id'] = serverfarm['id']
        self.assertEqual(serverfarm, values)

    def test_serverfarm_get(self):
        values = get_fake_sf('1')
        serverfarm_ref1 = db_api.serverfarm_create(self.conf, values)
        serverfarm_ref2 = db_api.serverfarm_get(self.conf,
                                                serverfarm_ref1['id'])
        self.assertEqual(dict(serverfarm_ref1.iteritems()),
                         dict(serverfarm_ref2.iteritems()))

    def test_serverfarm_destroy(self):
        values = get_fake_sf('1')
        serverfarm = db_api.serverfarm_create(self.conf, values)
        db_api.serverfarm_destroy(self.conf, serverfarm['id'])
        with self.assertRaises(exception.ServerFarmNotFound) as cm:
            db_api.serverfarm_get(self.conf, serverfarm['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'serverfarm_id': serverfarm['id']})

    def test_predictor_create(self):
        values = get_fake_predictor('1')
        predictor_ref = db_api.predictor_create(self.conf, values)
        predictor = dict(predictor_ref.iteritems())
        self.assertIsNotNone(predictor['id'])
        values['id'] = predictor['id']
        self.assertEqual(predictor, values)

    def test_predictor_get_by_sf_id(self):
        values1 = get_fake_predictor('1')
        values2 = get_fake_predictor('2')
        predictor1 = db_api.predictor_create(self.conf, values1)
        predictor2 = db_api.predictor_create(self.conf, values2)
        predictor_ref1 = db_api.predictor_get_by_sf_id(self.conf, '1')
        predictor_ref2 = db_api.predictor_get_by_sf_id(self.conf, '2')
        self.assertEqual(dict(predictor_ref1.iteritems()),
                         dict(predictor1.iteritems()))
        self.assertEqual(dict(predictor_ref2.iteritems()),
                         dict(predictor2.iteritems()))

    def test_predictor_update(self):
        values = get_fake_predictor('1')
        predictor_ref = db_api.predictor_create(self.conf, values)
        update = {'type': 'LEASTCONNECTIONS',
                  'extra': {'extrafield': 'extravalue'}}
        predictor_ref = db_api.predictor_update(self.conf, predictor_ref['id'],
                                                update)
        predictor = dict(predictor_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(predictor['id'])
        values['id'] = predictor['id']
        self.assertEqual(predictor, values)

    def test_predictor_get(self):
        values = get_fake_predictor('1')
        predictor_ref1 = db_api.predictor_create(self.conf, values)
        predictor_ref2 = db_api.predictor_get(self.conf, predictor_ref1['id'])
        self.assertEqual(dict(predictor_ref1.iteritems()),
                         dict(predictor_ref2.iteritems()))

    def test_predictor_destroy_by_sf_id(self):
        values = get_fake_predictor('1')
        predictor_ref1 = db_api.predictor_create(self.conf, values)
        values = get_fake_predictor('2')
        predictor_ref2 = db_api.predictor_create(self.conf, values)
        db_api.predictor_destroy_by_sf_id(self.conf, '1')
        with self.assertRaises(exception.PredictorNotFound) as cm:
            db_api.predictor_get(self.conf, predictor_ref1['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'predictor_id': predictor_ref1['id']})
        predictor_ref3 = db_api.predictor_get(self.conf, predictor_ref2['id'])
        self.assertEqual(dict(predictor_ref2.iteritems()),
                         dict(predictor_ref3.iteritems()))

    def test_predictor_destroy(self):
        values = get_fake_predictor('1')
        predictor = db_api.predictor_create(self.conf, values)
        db_api.predictor_destroy(self.conf, predictor['id'])
        with self.assertRaises(exception.PredictorNotFound) as cm:
            db_api.predictor_get(self.conf, predictor['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'predictor_id': predictor['id']})

    def test_virtualserver_create(self):
        values = get_fake_virtualserver('1', '1')
        virtualserver_ref = db_api.virtualserver_create(self.conf, values)
        virtualserver = dict(virtualserver_ref.iteritems())
        self.assertIsNotNone(virtualserver['id'])
        values['id'] = virtualserver['id']
        self.assertEqual(virtualserver, values)

    def test_virtualserver_get_all_by_sf_id(self):
        values = get_fake_virtualserver('1', '1')
        virtualserver1 = db_api.virtualserver_create(self.conf, values)
        virtualserver2 = db_api.virtualserver_create(self.conf, values)
        values = get_fake_virtualserver('2', '1')
        virtualserver3 = db_api.virtualserver_create(self.conf, values)
        virtualserver4 = db_api.virtualserver_create(self.conf, values)
        virtualservers1 = db_api.virtualserver_get_all_by_sf_id(self.conf, '1')
        virtualservers2 = db_api.virtualserver_get_all_by_sf_id(self.conf, '2')
        self.assertEqual([dict(vs.iteritems()) for vs in virtualservers1],
                         [dict(vs.iteritems()) for vs in [virtualserver1,
                                                          virtualserver2]])
        self.assertEqual([dict(vs.iteritems()) for vs in virtualservers2],
                         [dict(vs.iteritems()) for vs in [virtualserver3,
                                                          virtualserver4]])

    def test_virtualserver_get_all_by_lb_id(self):
        lb_id1, sf_id1 = self._create_lb_and_sf('1', 'tenant1')
        values = get_fake_virtualserver(sf_id1, lb_id1)
        virtualserver1 = db_api.virtualserver_create(self.conf, values)
        virtualserver2 = db_api.virtualserver_create(self.conf, values)
        lb_id2, sf_id2 = self._create_lb_and_sf('1', 'tenant1')
        values = get_fake_virtualserver(sf_id2, lb_id2)
        virtualserver3 = db_api.virtualserver_create(self.conf, values)
        virtualserver4 = db_api.virtualserver_create(self.conf, values)
        virtualservers1 = db_api.virtualserver_get_all_by_lb_id(self.conf,
                lb_id1)
        virtualservers2 = db_api.virtualserver_get_all_by_lb_id(self.conf,
                lb_id2)
        self.assertEqual([dict(vs.iteritems()) for vs in virtualservers1],
                         [dict(vs.iteritems()) for vs in [virtualserver1,
                                                          virtualserver2]])
        self.assertEqual([dict(vs.iteritems()) for vs in virtualservers2],
                         [dict(vs.iteritems()) for vs in [virtualserver3,
                                                          virtualserver4]])

    def test_virtualserver_get_all_by_lb_id_with_tenant(self):
        lb_id1, sf_id1 = self._create_lb_and_sf('1', 'tenant1')
        values = get_fake_virtualserver(sf_id1, lb_id1)
        virtualserver1 = db_api.virtualserver_create(self.conf, values)
        virtualserver2 = db_api.virtualserver_create(self.conf, values)
        lb_id2, sf_id2 = self._create_lb_and_sf('1', 'tenant2')
        values = get_fake_virtualserver(sf_id2, lb_id2)
        virtualserver3 = db_api.virtualserver_create(self.conf, values)
        virtualserver4 = db_api.virtualserver_create(self.conf, values)
        virtualservers1 = db_api.virtualserver_get_all_by_lb_id(self.conf,
                lb_id1, tenant_id='tenant1')
        virtualservers2 = db_api.virtualserver_get_all_by_lb_id(self.conf,
                lb_id2, tenant_id='tenant1')
        self.assertEqual([dict(vs.iteritems()) for vs in virtualservers1],
                         [dict(vs.iteritems()) for vs in [virtualserver1,
                                                          virtualserver2]])
        self.assertEqual([], virtualservers2)

    def test_virtualserver_update(self):
        values = get_fake_virtualserver('1', '1')
        virtualserver_ref = db_api.virtualserver_create(self.conf, values)
        update = {'port': '80',
                  'deployed': 'True',
                  'extra': {'ipVersion': 'IPv4',
                            'VLAN': 400,
                            'ICMPreply': False}}
        virtualserver_ref = db_api.virtualserver_update(self.conf,
                                    virtualserver_ref['id'], update)
        virtualserver = dict(virtualserver_ref.iteritems())
        values.update(update)
        self.assertIsNotNone(virtualserver['id'])
        values['id'] = virtualserver['id']
        self.assertEqual(virtualserver, values)

    def test_virtualserver_get(self):
        values = get_fake_virtualserver('1', '1')
        virtualserver_ref1 = db_api.virtualserver_create(self.conf, values)
        virtualserver_ref2 = db_api.virtualserver_get(self.conf,
                                                      virtualserver_ref1['id'])
        self.assertEqual(dict(virtualserver_ref1.iteritems()),
                         dict(virtualserver_ref2.iteritems()))

    def test_virtualserver_get_with_tenant(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        values = get_fake_virtualserver(sf_id, lb_id)
        virtualserver_ref1 = db_api.virtualserver_create(self.conf, values)
        virtualserver_ref2 = db_api.virtualserver_get(self.conf,
                virtualserver_ref1['id'], tenant_id='tenant1')
        self.assertEqual(dict(virtualserver_ref1.iteritems()),
                         dict(virtualserver_ref2.iteritems()))

    def test_virtualserver_get_with_tenant_fails(self):
        lb_id, sf_id = self._create_lb_and_sf('1', 'tenant1')
        values = get_fake_virtualserver(sf_id, lb_id)
        virtualserver_ref1 = db_api.virtualserver_create(self.conf, values)
        with self.assertRaises(exception.VirtualServerNotFound):
            db_api.virtualserver_get(self.conf,
                virtualserver_ref1['id'], tenant_id='tenant2')

    def test_virtualserver_destroy_by_sf_id(self):
        values = get_fake_virtualserver('1', '1')
        virtualserver_ref1 = db_api.virtualserver_create(self.conf, values)
        values = get_fake_virtualserver('2', '1')
        virtualserver_ref2 = db_api.virtualserver_create(self.conf, values)
        db_api.virtualserver_destroy_by_sf_id(self.conf, '1')
        with self.assertRaises(exception.VirtualServerNotFound) as cm:
            db_api.virtualserver_get(self.conf, virtualserver_ref1['id'])
        err = cm.exception
        expected = {'virtualserver_id': virtualserver_ref1['id']}
        self.assertEqual(err.kwargs, expected)
        virtualserver_ref3 = db_api.virtualserver_get(self.conf,
                                                      virtualserver_ref2['id'])
        self.assertEqual(dict(virtualserver_ref2.iteritems()),
                         dict(virtualserver_ref3.iteritems()))

    def test_virtualserver_destroy(self):
        values = get_fake_virtualserver('1', '1')
        virtualserver = db_api.virtualserver_create(self.conf, values)
        db_api.virtualserver_destroy(self.conf, virtualserver['id'])
        with self.assertRaises(exception.VirtualServerNotFound) as cm:
            db_api.virtualserver_get(self.conf, virtualserver['id'])
        err = cm.exception
        self.assertEqual(err.kwargs, {'virtualserver_id': virtualserver['id']})

########NEW FILE########
__FILENAME__ = test_haproxy_driver
# -*- coding: utf-8 -*-

import unittest
import os
import paramiko
from mock import Mock, MagicMock, patch

import balancer.drivers.haproxy.haproxy_driver as Driver
import balancer.drivers.haproxy.remote_control as RemoteControl

device_fake = {'id': 'fake1',
               'type': 'FAKE',
               'version': '1',
               'ip': '10.0.0.10',
               'port': 1010,
               'user': 'user1',
               'password': 'secrete1',
               'extra': {'interface': 'eth0',
               'socket': '/tmp/haproxy.sock'}}

test_config_file = '''global
\tlog 127.0.0.1   local0
\tlog 127.0.0.1   local1 debug
\t#log loghost    local0 info
\tmaxconn 4096
\t#chroot /usr/share/haproxy
\tuser haproxy
\tgroup haproxy
\tdaemon
\t#debug
\t#quiet
\tstats socket /tmp/haproxy.sock user root level admin
defaults
\tlog     global
\tmode    http
\toption  httplog
\toption  dontlognull
\tretries 3
\toption redispatch
\tmaxconn 2000
\tcontimeout      5000
\tclitimeout      50000
\tsrvtimeout      50000
backend test_backend1
\tbalance roundrobin
\toption httpchk GET /
\tserver test_server1 1.1.1.1 check maxconn 10000 inter 2000 rise 2 fall 3
\tserver test_server2 1.1.1.2 check maxconn 10 inter 20 rise 2 fall 3 disabled
frontend test_frontend1
\tbind 192.168.19.245:80
\tmode http
\tdefault_backend 719beee908cf428fa542bc15d929ba18
'''

conf = []


def init_mock_channel():
    mock_channel = Mock()
    mock_channel.channel.recv_exit_status.return_value = 0
    mock_channel.read.return_value = "test"
    return mock_channel


def init_ssh_mock():
    mock_for_ssh = Mock()
    mock_channel = init_mock_channel()
    mock_for_ssh.exec_command.return_value = \
         [mock_channel, mock_channel, mock_channel]
    return mock_for_ssh


def init_driver_with_mock():
    mock_for_ssh = init_ssh_mock()
    driver = Driver.HaproxyDriver(conf, device_fake)
    driver._remote_ctrl._ssh = mock_for_ssh
    return driver


def get_fake_rserver(id_, parameters):
    rserver = {'id': id_, 'weight': 8, 'address': '1.1.1.3',\
               'port': 23, 'condition': 'enabled'}
    rserver['extra'] = {'minconn': 100, 'maxconn': 2000, 'inter': 100,
                        'rise': 3, 'fall': 4}
    rserver.update(parameters)
    return rserver


def get_fake_server_farm(id_, parameters):
    server_farm = {'id': id_, 'type': 'Host'}
    server_farm.update(parameters)
    return server_farm


def get_fake_virtual_ip(id_, parameters):
    vip = {'id': id_, 'address': '100.1.1.1', 'port': '8801',
           'extra': {'protocol': 'tcp'}}
    vip.update(parameters)
    return vip


def get_fake_probe(id_, parameters):
    probe = {'id': id_, 'type': 'HTTP', 'extra': {'requestMethodType': 'GET',\
             'path': '/test.html', 'minExpectStatus': '300'}}
    probe.update(parameters)
    return probe


def get_fake_predictor(id_, parameters):
    predictor = {'id': id_, 'type': 'roundrobin', 'extra': {}}
    predictor.update(parameters)
    return predictor


def get_fake_HaproxyFrontend(id_):
    frontend = Driver.HaproxyFronted({'id': id_, 'address': '1.1.1.1',
                                      'port': '8080'})
    frontend.default_backend = 'server_farm'
    return frontend


def get_fake_HaproxyBackend(id_):
    backend = Driver.HaproxyBackend(id_)
    backend.balance = 'source'
    return backend


def get_fake_Haproxy_rserver(id_):
    haproxy_rserver = Driver.HaproxyRserver()
    haproxy_rserver.name = id_
    haproxy_rserver.address = '150.153.152.151'
    haproxy_rserver.port = '12663'
    haproxy_rserver.fall = '10'
    return haproxy_rserver


class TestHaproxyDriverRemoteService(unittest.TestCase):
    def setUp(self):
        self.ssh = init_ssh_mock()
        remote_ctrl = RemoteControl.RemoteControl(device_fake)
        remote_ctrl._ssh = self.ssh
        self.remote_service = RemoteControl.RemoteService(remote_ctrl)

    def test_start_service(self):
        self.remote_service.start()
        self.ssh.exec_command.assert_called_once_with(
                          'sudo service haproxy start')

    def test_stop_service(self):
        self.remote_service.stop()
        self.ssh.exec_command.assert_called_once_with(
                           'sudo service haproxy stop')

    def test_restart_service(self):
        self.remote_service.restart()
        self.ssh.exec_command.assert_called_once_with('sudo haproxy'
                              ' -f /etc/haproxy/haproxy.cfg'
                              ' -p /var/run/haproxy.pid'
                              ' -sf $(cat /var/run/haproxy.pid)')


class TestHaproxyDriverRemoteInterface(unittest.TestCase):
    def setUp(self):
        self.ssh = init_ssh_mock()
        self.frontend = get_fake_HaproxyFrontend('test')
        remote_ctrl = RemoteControl.RemoteControl(device_fake)
        remote_ctrl._ssh = self.ssh
        self.remote_interface = RemoteControl.RemoteInterface(device_fake,
                                                              remote_ctrl)

    def test_add_ip(self):
        # ip wasn't configured on the interface
        self.assertTrue(self.remote_interface.add_ip(self.frontend))
        self.assertEqual(self.ssh.exec_command.call_count, 2)
        self.assertEqual(self.ssh.exec_command.call_args_list[0][0][0],
                         'ip addr show dev eth0')
        self.assertEqual(self.ssh.exec_command.call_args_list[1][0][0],
                         'sudo ip addr add 1.1.1.1/32 dev eth0')

        # ip was already configured on the interface
        self.ssh.reset_mock()
        mock_channel = init_mock_channel()
        mock_channel.read.return_value = "1.1.1.1"
        self.ssh.exec_command.return_value = [mock_channel, mock_channel,
                                              mock_channel]
        self.assertTrue(self.remote_interface.add_ip(self.frontend))
        self.assertEqual(self.ssh.exec_command.call_count, 1)
        self.assertEqual(self.ssh.exec_command.call_args[0][0],
                         'ip addr show dev eth0')

    def test_del_ip(self):
        # ip wasn't configured on the interface
        self.assertTrue(self.remote_interface.del_ip(self.frontend))
        self.assertEqual(self.ssh.exec_command.call_count, 1)
        self.assertEqual(self.ssh.exec_command.call_args[0][0],
                         'ip addr show dev eth0')

        # ip was already configured on the interface
        self.ssh.reset_mock()
        mock_channel = init_mock_channel()
        mock_channel.read.return_value = "1.1.1.1"
        self.ssh.exec_command.return_value = [mock_channel, mock_channel,
                                              mock_channel]
        self.assertTrue(self.remote_interface.del_ip(self.frontend))
        self.assertEqual(self.ssh.exec_command.call_count, 2)
        self.assertEqual(self.ssh.exec_command.call_args_list[0][0][0],
                         'ip addr show dev eth0')
        self.assertEqual(self.ssh.exec_command.call_args_list[1][0][0],
                         'sudo ip addr del 1.1.1.1/32 dev eth0')


class TestHaproxyDriverRemoteSocketOperation(unittest.TestCase):
    def setUp(self):
        self.ssh = init_ssh_mock()
        remote_ctrl = RemoteControl.RemoteControl(device_fake)
        remote_ctrl._ssh = self.ssh
        self.backend = get_fake_HaproxyBackend('test_backend')
        self.rserver = get_fake_rserver('test_rserver', {})
        self.remote_socket = RemoteControl.RemoteSocketOperation(device_fake,
                                                                 remote_ctrl)
        self.driver = init_driver_with_mock()

    def test_suspend_server(self):
        self.assertTrue(self.remote_socket.suspend_server(self.backend,
                                                          self.rserver))
        self.ssh.exec_command.assert_called_once_with(
                          'echo disable server test_backend/test_rserver | '
                          'sudo socat stdio unix-connect:/tmp/haproxy.sock')

    def test_activate_server(self):
        self.assertTrue(self.remote_socket.activate_server(self.backend,
                                                           self.rserver))
        self.ssh.exec_command.assert_called_once_with(
                          'echo enable server test_backend/test_rserver | '
                          'sudo socat stdio unix-connect:/tmp/haproxy.sock')

    def test_get_statistics(self):
        self.assertTrue(self.remote_socket.get_statistics(self.backend.name,
                                                          self.rserver['id']))
        self.ssh.exec_command.assert_called_once_with(
                          'echo show stat | sudo socat stdio unix-connect:'
                          '/tmp/haproxy.sock | grep test_backend,test_rserver')


class TestHaproxyDriverAllFunctions(unittest.TestCase):
    def setUp(self):
        self.driver = init_driver_with_mock()
        self.ssh = self.driver._remote_ctrl._ssh
        self.config_file_name = '/tmp/haproxy.cfg'
        f = open(self.config_file_name, 'w')
        f.write(test_config_file)
        f.close()

    def tearDown(self):
        if os.path.exists(self.config_file_name):
            os.remove(self.config_file_name)

    def check_line_on_pos(self, line, position):
        lines = open(self.config_file_name).read().splitlines()
        self.assertEqual(line, lines[position])

    def is_line_in_config(self, line):
        lines = open(self.config_file_name).read().splitlines()
        return line in lines

    def test_suspend_real_server(self):
        server_farm = get_fake_server_farm('test_backend1', {})
        rserver = get_fake_rserver('test_server1', {})
        self.check_line_on_pos('\tserver test_server1 1.1.1.1'
                               ' check maxconn 10000 inter 2000 rise 2'
                               ' fall 3',
                               26)
        self.driver.suspend_real_server(server_farm, rserver)
        self.check_line_on_pos('\tserver test_server1 1.1.1.1'
                               ' check maxconn 10000 inter 2000 rise 2'
                               ' fall 3 disabled',
                               26)
        self.ssh.exec_command.assert_called_once_with(
                          'echo disable server test_backend1/test_server1 | '
                          'sudo socat stdio unix-connect:/tmp/haproxy.sock')

    def test_activate_real_server(self):
        server_farm = get_fake_server_farm('test_backend1', {})
        rserver = get_fake_rserver('test_server2', {})
        self.check_line_on_pos('\tserver test_server2 1.1.1.2'
                               ' check maxconn 10 inter 20 rise 2'
                               ' fall 3 disabled',
                               27)
        self.driver.activate_real_server(server_farm, rserver)
        self.check_line_on_pos('\tserver test_server2 1.1.1.2'
                               ' check maxconn 10 inter 20 rise 2'
                               ' fall 3',
                               27)
        self.ssh.exec_command.assert_called_once_with(
                          'echo enable server test_backend1/test_server2 | '
                          'sudo socat stdio unix-connect:/tmp/haproxy.sock')

    def test_add_tcp_probe_to_server_farm(self):
        probe = get_fake_probe('test_probe1', {'type': 'tcp'})
        sf = get_fake_server_farm('test_backend1', {})
        self.driver.add_probe_to_server_farm(sf, probe)
        self.check_line_on_pos('\toption httpchk', 25)

    def test_add_http_probe_to_server_farm(self):
        probe = get_fake_probe('test_probe1', {'type': 'http'})
        sf = get_fake_server_farm('test_backend1', {})
        self.driver.add_probe_to_server_farm(sf, probe)
        self.check_line_on_pos('\toption httpchk GET /test.html', 26)

    def test_add_https_probe_to_server_farm(self):
        probe = get_fake_probe('test_probe1', {'type': 'https'})
        sf = get_fake_server_farm('test_backend1', {})
        self.driver.add_probe_to_server_farm(sf, probe)
        self.check_line_on_pos('\toption ssl-hello-chk', 26)

    def test_delete_http_probe_from_server_farm(self):
        probe = get_fake_probe('test_probe1', {'type': 'http'})
        sf = get_fake_server_farm('test_backend1', {})
        self.assertTrue(self.is_line_in_config('\toption httpchk GET /'))
        self.driver.delete_probe_from_server_farm(sf, probe)
        self.assertFalse(self.is_line_in_config('\toption httpchk GET /'))

    def test_delete_https_probe_from_server_farm(self):
        probe = get_fake_probe('test_probe1', {'type': 'https'})
        sf = get_fake_server_farm('test_backend1', {})
        self.driver.add_probe_to_server_farm(sf, probe)
        self.assertTrue(self.is_line_in_config('\toption ssl-hello-chk'))
        self.driver.delete_probe_from_server_farm(sf, probe)
        self.assertFalse(self.is_line_in_config('\toption ssl-hello-chk'))

    def test_create_server_farm_with_round_robin(self):
        sf = get_fake_server_farm('test_backend2', {})
        predictor = get_fake_predictor('test_predictor1',
                                       {'type': 'round_robin'})
        self.driver.create_server_farm(sf, predictor)
        self.check_line_on_pos('backend test_backend2', 28)
        self.check_line_on_pos('\tbalance roundrobin', 29)

    def test_create_server_farm_with_leastconnections(self):
        sf = get_fake_server_farm('test_backend2', {})
        predictor = get_fake_predictor('test_predictor1',
                                       {'type': 'least_connection'})
        self.driver.create_server_farm(sf, predictor)
        self.check_line_on_pos('backend test_backend2', 28)
        self.check_line_on_pos('\tbalance leastconn', 29)

    def test_create_server_farm_with_hashsource(self):
        sf = get_fake_server_farm('test_backend2', {})
        predictor = get_fake_predictor('test_predictor1',
                                       {'type': 'hash_source'})
        self.driver.create_server_farm(sf, predictor)
        self.check_line_on_pos('backend test_backend2', 28)
        self.check_line_on_pos('\tbalance source', 29)

    def test_create_server_farm_with_hashuri(self):
        sf = get_fake_server_farm('test_backend2', {})
        predictor = get_fake_predictor('test_predictor1',
                                       {'type': 'hash_uri'})
        self.driver.create_server_farm(sf, predictor)
        self.check_line_on_pos('backend test_backend2', 28)
        self.check_line_on_pos('\tbalance uri', 29)

    def test_delete_server_farm(self):
        sf = get_fake_server_farm('test_backend1', {})
        self.assertTrue(self.is_line_in_config('backend test_backend1'))
        self.assertTrue(self.is_line_in_config('\tbalance roundrobin'))
        self.assertTrue(self.is_line_in_config('\toption httpchk GET /'))
        self.assertTrue(self.is_line_in_config('\tserver test_server1 1.1.1.1 '
                                               'check maxconn 10000 inter 2000'
                                               ' rise 2 fall 3'))
        self.assertTrue(self.is_line_in_config('\tserver test_server2 1.1.1.2 '
                                               'check maxconn 10 inter 20 rise'
                                               ' 2 fall 3 disabled'))
        self.driver.delete_server_farm(sf)
        self.assertFalse(self.is_line_in_config('backend test_backend1'))
        self.assertFalse(self.is_line_in_config('\tbalance roundrobin'))
        self.assertFalse(self.is_line_in_config('\toption httpchk GET /'))
        self.assertFalse(self.is_line_in_config('\tserver test_server1 1.1.1.1'
                                                ' check maxconn 10000 inter '
                                                '2000 rise 2 fall 3'))
        self.assertFalse(self.is_line_in_config('\tserver test_server2 1.1.1.2'
                                                ' check maxconn 10 inter 20 '
                                                'rise 2 fall 3 disabled'))

    def test_add_real_server_to_server_farm(self):
        sf = get_fake_server_farm('test_backend1', {})
        rs = get_fake_rserver('test_server3', {'port': '23'})
        self.driver.add_real_server_to_server_farm(sf, rs)
        self.check_line_on_pos('\tserver test_server3 1.1.1.3:23 check maxconn'
                               ' 2000 inter 100 rise 3 fall 4', 28)
        rs['extra']['condition'] = 'disabled'
        self.driver.add_real_server_to_server_farm(sf, rs)
        self.check_line_on_pos('\tserver test_server3 1.1.1.3:23 check maxconn'
                               ' 2000 inter 100 rise 3 fall 4 disabled', 29)

    def test_delete_real_server_from_server_farm(self):
        sf = get_fake_server_farm('test_backend1', {})
        rs = get_fake_rserver('test_server2', {})
        self.assertTrue(self.is_line_in_config('\tserver test_server1 1.1.1.1 '
                                               'check maxconn 10000 inter 2000'
                                               ' rise 2 fall 3'))
        self.assertTrue(self.is_line_in_config('\tserver test_server2 1.1.1.2 '
                                               'check maxconn 10 inter 20 rise'
                                               ' 2 fall 3 disabled'))
        self.driver.delete_real_server_from_server_farm(sf, rs)
        self.assertFalse(self.is_line_in_config('\tserver test_server2 1.1.1.2'
                                               ' check maxconn 10 inter 20'
                                               ' rise 2 fall 3 disabled'))
        self.assertTrue(self.is_line_in_config('\tserver test_server1 1.1.1.1 '
                                               'check maxconn 10000 inter 2000'
                                               ' rise 2 fall 3'))

    def test_create_virtual_ip(self):
        virtualserver = get_fake_virtual_ip('test_frontend2', {})
        server_farm = get_fake_server_farm('test_backend1', {})
        self.driver.create_virtual_ip(virtualserver, server_farm)
        self.check_line_on_pos('frontend test_frontend2', 32)
        self.check_line_on_pos('\tbind 100.1.1.1:8801', 33)
        self.check_line_on_pos('\tdefault_backend test_backend1', 34)
        self.check_line_on_pos('\tmode tcp', 35)

        self.assertEqual(self.ssh.exec_command.call_count, 2)
        self.assertEqual(self.ssh.exec_command.call_args_list[0][0][0],
                         'ip addr show dev eth0')
        self.assertEqual(self.ssh.exec_command.call_args_list[1][0][0],
                         'sudo ip addr add 100.1.1.1/32 dev eth0')

    def test_delete_virtual_ip(self):
        mock_channel = init_mock_channel()
        mock_channel.read.return_value = "...100.1.1.1..."
        self.ssh.exec_command.return_value = [mock_channel, mock_channel,
                                              mock_channel]
        virtualserver = get_fake_virtual_ip('test_frontend1', {})
        self.assertTrue(self.is_line_in_config('frontend test_frontend1'))
        self.assertTrue(self.is_line_in_config('\tbind 192.168.19.245:80'))
        self.assertTrue(self.is_line_in_config(
                        '\tdefault_backend 719beee908cf428fa542bc15d929ba18'))
        self.assertTrue(self.is_line_in_config('\tmode http'))
        self.driver.delete_virtual_ip(virtualserver)
        self.assertFalse(self.is_line_in_config('frontend test_frontend1'))
        self.assertFalse(self.is_line_in_config('\tbind 192.168.19.245:80'))
        self.assertFalse(self.is_line_in_config(
                        '\tdefault_backend 719beee908cf428fa542bc15d929ba18'))
        self.assertFalse(self.is_line_in_config('\tmode http'))

        self.assertEqual(self.ssh.exec_command.call_count, 2)
        self.assertEqual(self.ssh.exec_command.call_args_list[0][0][0],
                         'ip addr show dev eth0')
        self.assertEqual(self.ssh.exec_command.call_args_list[1][0][0],
                         'sudo ip addr del 100.1.1.1/32 dev eth0')

    def test_get_statistics(self):
        stats = '041493dca01344adad9a04b5d9a50ac8,804e181ef8ec427d810ef46f0d'\
        'bd9cb2,0,0,0,1,1000,2,318,572,,0,,0,0,0,0,UP,1,1,0,0,0,1116,0,,1,1,'\
        '1,,2,,2,0,,1,L7OK,200,0,0,2,0,0,0,0,0,,,,0,0,'
        mock_channel = init_mock_channel()
        mock_channel.read.return_value = stats
        self.ssh.exec_command.return_value = [mock_channel, mock_channel,
                                              mock_channel]

        sf = get_fake_server_farm('test_backend1', {})
        rserver = get_fake_rserver('test_server1', {})
        statistics = self.driver.get_statistics(sf, rserver)
        self.assertEqual(statistics, {'connFail': '0', 'weight': '1',
                                      'connCurrent': '0', 'connMax': '1',
                                      'connTotal': '2', 'state': 'UP',
                                      'connRateLimit': '',
                                      'bandwRateLimit': '1'})
        self.ssh.exec_command.assert_called_once_with(
                          'echo show stat | sudo socat stdio unix-connect:/tmp'
                          '/haproxy.sock | grep test_backend1,test_server1')

    def test_finalize_config(self):
        mock_channel = init_mock_channel()
        self.ssh.exec_command.return_value = [mock_channel, mock_channel,
                                              mock_channel]

        self.driver._remote_ctrl.open()
        self.driver.finalize_config(False)
        self.assertFalse(self.ssh.exec_command.called)
        self.assertTrue(self.ssh.close.called)

        # config is valid
        mock_channel.read.return_value = 'Configuration file is valid'
        self.driver.config_manager.need_deploy = True
        self.driver.finalize_config(True)
        self.assertEqual(self.ssh.exec_command.call_count, 3)
        self.assertEqual(self.ssh.exec_command.call_args_list[0][0][0],
                         'haproxy -c -f /tmp/haproxy.cfg.remote')
        self.assertEqual(self.ssh.exec_command.call_args_list[1][0][0],
                         'sudo mv /tmp/haproxy.cfg.remote '
                         '/etc/haproxy/haproxy.cfg')
        self.assertEqual(self.ssh.exec_command.call_args_list[2][0][0],
                         'sudo haproxy -f /etc/haproxy/haproxy.cfg'
                         ' -p /var/run/haproxy.pid -sf '
                         '$(cat /var/run/haproxy.pid)')
        self.assertTrue(self.ssh.close.called)

        # config is invalid
        self.ssh.reset_mock()
        mock_channel.read.return_value = 'ERROR'
        self.driver.config_manager.need_deploy = True
        self.driver.finalize_config(True)
        self.ssh.exec_command.assert_called_once_with(
                        'haproxy -c -f /tmp/haproxy.cfg.remote')
        self.assertTrue(self.ssh.close.called)

    def test_get_capabilities(self):
        capabilities = self.driver.get_capabilities()
        self.assertEqual(capabilities, {'algorithms': ['STATIC_RR',
                                                       'ROUND_ROBIN',
                                                       'HASH_SOURCE',
                                                       'LEAST_CONNECTION',
                                                       'HASH_URI'],
                                        'protocols': ['HTTP', 'TCP']})

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scheduller
import mock
import unittest

from balancer.core import scheduler
from balancer import exception as exp
from balancer.common import cfg


def fake_filter(conf, lb_ref, dev_ref):
    return True if dev_ref['id'] > 2 else False


def fake_cost(conf, lb_ref, dev_ref):
    return 1. * dev_ref['id']


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.conf = mock.MagicMock()
        self.lb_ref = mock.MagicMock()
        self.devices = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]
        self.attrs = {'device_filters':
                 ['%s.fake_filter' % __name__],
                 'device_cost_functions':
                 ['%s.fake_cost' % __name__],
                 'device_cost_fake_cost_weight': 1.}
        self.conf.configure_mock(**self.attrs)

    @mock.patch('balancer.db.api.device_get_all')
    def test_scheduler_no_proper_devs(self, dev_get_all):
        dev_get_all.return_value = self.devices[:2]
        with self.assertRaises(exp.NoValidDevice):
            scheduler.schedule(self.conf, self.lb_ref)
            self.assertTrue(dev_get_all.called)

    @mock.patch('balancer.db.api.device_get_all')
    def test_scheduler_with_proper_devs(self, dev_get_all):
        dev_get_all.return_value = self.devices
        res = scheduler.schedule(self.conf, self.lb_ref)
        self.assertTrue(dev_get_all.called)
        self.assertEqual({'id': 3}, res)

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.db.api.device_get')
    def test_scheduler_reschedule_former(self, device_get, device_get_all):
        device_get.return_value = {'id': 3}
        device_get_all.return_value = self.devices
        device = scheduler.reschedule(self.conf, self.lb_ref)
        self.assertTrue(device_get.called)
        self.assertFalse(device_get_all.called)
        self.assertEqual({'id': 3}, device)

    @mock.patch('balancer.db.api.device_get_all')
    @mock.patch('balancer.db.api.device_get')
    def test_scheduler_reschedule_novel(self, device_get, device_get_all):
        device_get.return_value = {'id': 1}
        device_get_all.return_value = self.devices
        device = scheduler.reschedule(self.conf, self.lb_ref)
        self.assertTrue(device_get.called)
        self.assertTrue(device_get_all.called)
        self.assertEqual({'id': 3}, device)

    @mock.patch('balancer.db.api.device_get_all')
    def test_scheduler_without_devices(self, dev_get_all):
        dev_get_all.return_value = []
        with self.assertRaises(exp.DeviceNotFound):
            scheduler.schedule(self.conf, self.lb_ref)
            self.assertTrue(dev_get_all.called)

    @mock.patch('balancer.db.api.device_get_all')
    def test_scheduler_no_cfg(self, dev_get_all):
        conf = cfg.ConfigOpts(default_config_files=[])
        conf._oparser = mock.Mock()
        conf._oparser.parse_args.return_value = mock.Mock(), None
        conf._oparser.parse_args.return_value[0].__dict__ = self.attrs
        conf()
        dev_get_all.return_value = self.devices
        res = scheduler.schedule(conf, self.lb_ref)
        self.assertTrue(dev_get_all.called)
        self.assertEqual({'id': 3}, res)


class TestFilterCapabilities(unittest.TestCase):
    def setUp(self):
        self.conf = mock.MagicMock()
        self.conf.device_filter_capabilities = ['algorithm']
        self.lb_ref = {'id': 5}
        self.dev_ref = {'id': 1}

    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    def test_proper(self, mock_getdev):
        self.lb_ref['algorithm'] = 'test'
        mock_getdev.return_value.get_capabilities.return_value = {
                'algorithms': ['test'],
        }
        res = scheduler.filter_capabilities(self.conf, self.lb_ref,
                                           self.dev_ref)
        self.assertTrue(res)

    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    def test_no_req(self, mock_getdev):
        mock_getdev.return_value.get_capabilities.return_value = {
                'algorithms': ['test'],
        }
        res = scheduler.filter_capabilities(self.conf, self.lb_ref,
                                           self.dev_ref)
        self.assertTrue(res)

    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    def test_no_cap(self, mock_getdev):
        self.lb_ref['algorithm'] = 'test'
        mock_getdev.return_value.get_capabilities.return_value = {}
        res = scheduler.filter_capabilities(self.conf, self.lb_ref,
                                           self.dev_ref)
        self.assertFalse(res)

    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    def test_none_cap(self, mock_getdev):
        self.lb_ref['algorithm'] = 'test'
        mock_getdev.return_value.get_capabilities.return_value = None
        res = scheduler.filter_capabilities(self.conf, self.lb_ref,
                                           self.dev_ref)
        self.assertFalse(res)

    @mock.patch("balancer.drivers.get_device_driver", autospec=True)
    def test_no_cfg(self, mock_getdev):
        conf = cfg.ConfigOpts(default_config_files=[])
        conf._oparser = mock.Mock()
        conf._oparser.parse_args.return_value = mock.Mock(), None
        conf._oparser.parse_args.return_value[0].__dict__ = {}
        conf()
        self.lb_ref['algorithm'] = 'test'
        mock_getdev.return_value.get_capabilities.return_value = {
                'algorithms': ['test'],
        }
        res = scheduler.filter_capabilities(conf, self.lb_ref, self.dev_ref)
        self.assertTrue(res)


class TestWeigthsFunctions(unittest.TestCase):
    def setUp(self):
        self.conf = mock.MagicMock()
        self.lb_ref = {}
        self.dev_ref = {}

    @mock.patch('balancer.db.api.lb_count_active_by_device')
    def test_lbs_on(self, lb_count):
        lb_count.return_value = 3
        self.dev_ref['id'] = '1'
        res = scheduler.lbs_on(self.conf, self.lb_ref, self.dev_ref)
        self.assertEqual(res, 3)

########NEW FILE########
__FILENAME__ = test_utils
import unittest
from balancer import utils


class TestHttpCode(unittest.TestCase):

    def test_http_code_decorator(self):

        @utils.http_success_code(202)
        def test_function():
            return

        self.assertTrue(hasattr(test_function, "wsgi_code") and
                        test_function.wsgi_code == 202,
                        "http_code_decorator doesn't work")

########NEW FILE########
__FILENAME__ = utils
import contextlib
import functools
import logging
import sys

import webob.exc

LOG = logging.getLogger(__name__)


def http_success_code(code):
    """Attaches response code to a method.

    This decorator associates a response code with a method.  Note
    that the function attributes are directly manipulated; the method
    is not wrapped.
    """

    def decorator(func):
        func.wsgi_code = code
        return func
    return decorator


def verify_tenant(func):
    @functools.wraps(func)
    def __inner(self, req, tenant_id, *args, **kwargs):
        if hasattr(req, 'context') and tenant_id != req.context.tenant_id:
            LOG.info('User is not authorized to access this tenant.')
            raise webob.exc.HTTPUnauthorized
        return func(self, req, tenant_id, *args, **kwargs)
    return __inner


def require_admin(func):
    @functools.wraps(func)
    def __inner(self, req, *args, **kwargs):
        if hasattr(req, 'context') and not req.context.is_admin:
            LOG.info('User has no admin priviledges.')
            raise webob.exc.HTTPUnauthorized
        return func(self, req, *args, **kwargs)
    return __inner


@contextlib.contextmanager
def save_and_reraise_exception():
    """Save current exception, run some code and then re-raise.

    In some cases the exception context can be cleared, resulting in None
    being attempted to be reraised after an exception handler is run. This
    can happen when eventlet switches greenthreads or when running an
    exception handler, code raises and catches an exception. In both
    cases the exception context will be cleared.

    To work around this, we save the exception state, run handler code, and
    then re-raise the original exception. If another exception occurs, the
    saved exception is logged and the new exception is reraised.
    """
    type_, value, traceback = sys.exc_info()
    try:
        yield
    except Exception:
        LOG.error('Original exception being dropped',
                  exc_info=(type_, value, traceback))
        raise
    raise type_, value, traceback

########NEW FILE########
__FILENAME__ = version
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

"""Determine version of Skeleton library"""

try:
    from skeleton.vcsversion import version_info
except ImportError:
    version_info = {'branch_nick': u'LOCALBRANCH',
                    'revision_id': 'LOCALREVISION',
                    'revno': 0}

SKELETON_VERSION = ['2012', '1']
YEAR, COUNT = SKELETON_VERSION

FINAL = False   # This becomes true at Release Candidate time


def canonical_version_string():
    return '.'.join([YEAR, COUNT])


def version_string():
    if FINAL:
        return canonical_version_string()
    else:
        return '%s-dev' % (canonical_version_string(),)


def vcs_version_string():
    return "%s:%s" % (version_info['branch_nick'], version_info['revision_id'])


def version_string_with_vcs():
    return "%s-%s" % (canonical_version_string(), vcs_version_string())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
# Copyright (c) 2011 OpenStack, LLC.
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

#
# Skeleton documentation build configuration file, created by
# sphinx-quickstart on Tue May 18 13:50:15 2010.
#
# This file is execfile()'d with the current directory set to it's containing
# dir.
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
sys.path.append([os.path.abspath('../../balancer'),
    os.path.abspath('..'),
    os.path.abspath('../bin')
    ])

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              'sphinx.ext.ifconfig',
              'sphinx.ext.intersphinx',
              'sphinx.ext.pngmath',
              'sphinx.ext.graphviz',
              'sphinx.ext.todo']

todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = []
if os.getenv('HUDSON_PUBLISH_DOCS'):
    templates_path = ['_ga', '_templates']
else:
    templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'LBaaS'
copyright = u'2012-present, OpenStack, LLC.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from balancer import version as skeleton_version
# The full version, including alpha/beta/rc tags.
release = skeleton_version.version_string()
# The short X.Y version.
version = skeleton_version.canonical_version_string()

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

# The reST default role (for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['skeleton.']

# -- Options for man page output --------------------------------------------

# Grouping the document tree for man pages.
# List of tuples 'sourcefile', 'target', u'title', u'Authors name', 'manual'

man_pages = [
    ('man/lbaas', 'lbaas', u'LBaaS Service',
     [u'OpenStack'], 1)
 ]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme_path = ["."]
html_theme = '_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = ['_theme']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'skeletondoc'


# -- Options for LaTeX output ------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
# documentclass [howto/manual]).
latex_documents = [
  ('index', 'Skeleton.tex', u'Skeleton Documentation',
   u'Skeleton Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

# Example configuration for intersphinx: refer to the Python standard library.
#intersphinx_mapping = {'python': ('http://docs.python.org/', None),
#                       'dashboard': ('http://dashboard.openstack.org', None),
#                       'glance': ('http://glance.openstack.org', None),
#                       'keystone': ('http://keystone.openstack.org', None),
#                       'nova': ('http://nova.openstack.org', None),
#                       'swift': ('http://swift.openstack.org', None)}

########NEW FILE########
__FILENAME__ = config
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
Routines for configuring Openstack Projects
"""

import ConfigParser
import logging
import logging.config
import logging.handlers
import optparse
import os
import re
import sys

from paste import deploy

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)8s [%(name)s] %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_options(parser, cli_args=None):
    """
    Returns the parsed CLI options, command to run and its arguments, merged
    with any same-named options found in a configuration file.

    The function returns a tuple of (options, args), where options is a
    mapping of option key/str(value) pairs, and args is the set of arguments
    (not options) supplied on the command-line.

    The reason that the option values are returned as strings only is that
    ConfigParser and paste.deploy only accept string values...

    :param parser: The option parser
    :param cli_args: (Optional) Set of arguments to process. If not present,
                     sys.argv[1:] is used.
    :retval tuple of (options, args)
    """

    (options, args) = parser.parse_args(cli_args)

    return (vars(options), args)


def add_common_options(parser):
    """
    Given a supplied optparse.OptionParser, adds an OptionGroup that
    represents all common configuration options.

    :param parser: optparse.OptionParser
    """
    help_text = "The following configuration options are common to "\
                "this app's programs."

    group = optparse.OptionGroup(parser, "Common Options", help_text)
    group.add_option('-v', '--verbose', default=False, dest="verbose",
                     action="store_true",
                     help="Print more verbose output")
    group.add_option('-d', '--debug', default=False, dest="debug",
                     action="store_true",
                     help="Print debugging output")
    group.add_option('--config-file', default=None, metavar="PATH",
                     help="Path to the config file to use. When not specified "
                          "(the default), we generally look at the first "
                          "argument specified to be a config file, and if "
                          "that is also missing, we search standard "
                          "directories for a config file.")
    parser.add_option_group(group)


def add_log_options(parser):
    """
    Given a supplied optparse.OptionParser, adds an OptionGroup that
    represents all the configuration options around logging.

    :param parser: optparse.OptionParser
    """
    help_text = "The following configuration options are specific to logging "\
                "functionality for this program."

    group = optparse.OptionGroup(parser, "Logging Options", help_text)
    group.add_option('--log-config', default=None, metavar="PATH",
                     help="If this option is specified, the logging "
                          "configuration file specified is used and overrides "
                          "any other logging options specified. Please see "
                          "the Python logging module documentation for "
                          "details on logging configuration files.")
    group.add_option('--log-date-format', metavar="FORMAT",
                      default=DEFAULT_LOG_DATE_FORMAT,
                      help="Format string for %(asctime)s in log records. "
                           "Default: %default")
    group.add_option('--log-file', default=None, metavar="PATH",
                      help="(Optional) Name of log file to output to. "
                           "If not set, logging will go to stdout.")
    group.add_option("--log-dir", default=None,
                      help="(Optional) The directory to keep log files in "
                           "(will be prepended to --logfile)")
    group.add_option('--use-syslog', default=False, dest="use_syslog",
                     action="store_true",
                     help="Use syslog for logging.")
    parser.add_option_group(group)


def setup_logging(options, conf):
    """
    Sets up the logging options for a log with supplied name

    :param options: Mapping of typed option key/values
    :param conf: Mapping of untyped key/values from config file
    """

    if options.get('log_config', None):
        # Use a logging configuration file for all settings...
        if os.path.exists(options['log_config']):
            logging.config.fileConfig(options['log_config'])
            return
        else:
            raise RuntimeError("Unable to locate specified logging "
                               "config file: %s" % options['log_config'])

    # If either the CLI option or the conf value
    # is True, we set to True
    debug = options.get('debug') or \
            get_option(conf, 'debug', type='bool', default=False)
    verbose = options.get('verbose') or \
            get_option(conf, 'verbose', type='bool', default=False)
    root_logger = logging.root
    if debug:
        root_logger.setLevel(logging.DEBUG)
    elif verbose:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.WARNING)

    # Set log configuration from options...
    # Note that we use a hard-coded log format in the options
    # because of Paste.Deploy bug #379
    # http://trac.pythonpaste.org/pythonpaste/ticket/379
    log_format = options.get('log_format', DEFAULT_LOG_FORMAT)
    log_date_format = options.get('log_date_format', DEFAULT_LOG_DATE_FORMAT)
    formatter = logging.Formatter(log_format, log_date_format)

    logfile = options.get('log_file')
    if not logfile:
        logfile = conf.get('log_file')

    use_syslog = options.get('use_syslog') or \
                get_option(conf, 'use_syslog', type='bool', default=False)

    if use_syslog:
        handler = logging.handlers.SysLogHandler(address='/dev/log')
    elif logfile:
        logdir = options.get('log_dir')
        if not logdir:
            logdir = conf.get('log_dir')
        if logdir:
            logfile = os.path.join(logdir, logfile)
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def find_config_file(app_name, options, args, config_dir=None):
    """
    Return the first config file found for an application.

    We search for the paste config file in the following order:
    * If --config-file option is used, use that
    * If args[0] is a file, use that
    * Search for $app.conf in standard directories:
        * .
        * ~.config_dir/
        * ~
        * /etc/config_dir
        * /etc

    :retval Full path to config file, or None if no config file found
    """
    config_dir = config_dir or app_name

    fix_path = lambda p: os.path.abspath(os.path.expanduser(p))
    if options.get('config_file'):
        if os.path.exists(options['config_file']):
            return fix_path(options['config_file'])
    elif args:
        if os.path.exists(args[0]):
            return fix_path(args[0])

    # Handle standard directory search for $app_name.conf
    config_file_dirs = [fix_path(os.getcwd()),
                        fix_path(os.path.join('~', '.' + config_dir)),
                        fix_path('~'),
                        os.path.join('/etc', config_dir),
                        '/etc']

    for cfg_dir in config_file_dirs:
        cfg_file = os.path.join(cfg_dir, '%s.conf' % app_name)
        if os.path.exists(cfg_file):
            return cfg_file


def load_paste_config(app_name, options, args, config_dir=None):
    """
    Looks for a config file to use for an app and returns the
    config file path and a configuration mapping from a paste config file.

    We search for the paste config file in the following order:
    * If --config-file option is used, use that
    * If args[0] is a file, use that
    * Search for $app_name.conf in standard directories:
        * .
        * ~.config_dir/
        * ~
        * /etc/config_dir
        * /etc

    :param app_name: Name of the application to load config for, or None.
                     None signifies to only load the [DEFAULT] section of
                     the config file.
    :param options: Set of typed options returned from parse_options()
    :param args: Command line arguments from argv[1:]
    :retval Tuple of (conf_file, conf)

    :raises RuntimeError when config file cannot be located or there was a
            problem loading the configuration file.
    """
    conf_file = find_config_file(app_name, options, args, config_dir)
    if not conf_file:
        raise RuntimeError("Unable to locate any configuration file. "
                            "Cannot load application %s" % app_name)
    try:
	app = wsgi.paste_deploy_app(conf_file, app_name, conf)
        conf = deploy.appconfig("config:%s" % conf_file, name=app_name)
        return conf_file, conf
    except Exception, e:
        raise RuntimeError("Error trying to load config %s: %s"
                           % (conf_file, e))


def load_paste_app(app_name, options, args, config_dir=None):
    """
    Builds and returns a WSGI app from a paste config file.

    We search for the paste config file in the following order:
    * If --config-file option is used, use that
    * If args[0] is a file, use that
    * Search for $app_name.conf in standard directories:
        * .
        * ~.config_dir/
        * ~
        * /etc/config_dir
        * /etc

    :param app_name: Name of the application to load
    :param options: Set of typed options returned from parse_options()
    :param args: Command line arguments from argv[1:]

    :raises RuntimeError when config file cannot be located or application
            cannot be loaded from config file
    """
    conf_file, conf = load_paste_config(app_name, options,
                                        args, config_dir)

    try:
        # Setup logging early, supplying both the CLI options and the
        # configuration mapping from the config file
        setup_logging(options, conf)

        # We only update the conf dict for the verbose and debug
        # flags. Everything else must be set up in the conf file...
        debug = options.get('debug') or \
                get_option(conf, 'debug', type='bool', default=False)
        verbose = options.get('verbose') or \
                get_option(conf, 'verbose', type='bool', default=False)
        conf['debug'] = debug
        conf['verbose'] = verbose

        # Log the options used when starting if we're in debug mode...
        if debug:
            logger = logging.getLogger(app_name)
            logger.debug("*" * 80)
            logger.debug("Configuration options gathered from config file:")
            logger.debug(conf_file)
            logger.debug("================================================")
            items = dict([(k, v) for k, v in conf.items()
                          if k not in ('__file__', 'here')])
            for key, value in sorted(items.items()):
                logger.debug("%(key)-30s %(value)s" % locals())
            logger.debug("*" * 80)
        app = deploy.loadapp("config:%s" % conf_file, name=app_name)
    except (LookupError, ImportError), e:
        raise RuntimeError("Unable to load %(app_name)s from "
                           "configuration file %(conf_file)s."
                           "\nGot: %(e)r" % locals())
    return conf, app


def get_option(options, option, **kwargs):
    if option in options:
        value = options[option]
        type_ = kwargs.get('type', 'str')
        if type_ == 'bool':
            if hasattr(value, 'lower'):
                return value.lower() == 'true'
            else:
                return value
        elif type_ == 'int':
            return int(value)
        elif type_ == 'float':
            return float(value)
        else:
            return value
    elif 'default' in kwargs:
        return kwargs['default']
    else:
        raise KeyError("option '%s' not found" % option)

########NEW FILE########
__FILENAME__ = context
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
Simple class that stores security context information in the web request.

Projects should subclass this class if they wish to enhance the request
context or provide additional information in their specific WSGI pipeline.
"""


class RequestContext(object):

    """
    Stores information about the security context under which the user
    accesses the system, as well as additional request information.
    """

    def __init__(self, auth_tok=None, user=None, tenant=None, is_admin=False,
                 read_only=False, show_deleted=False):
        self.auth_tok = auth_tok
        self.user = user
        self.tenant = tenant
        self.is_admin = is_admin
        self.read_only = read_only
        self.show_deleted = show_deleted

########NEW FILE########
__FILENAME__ = exception
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
Exceptions common to OpenStack projects
"""

import logging


class ProcessExecutionError(IOError):
    def __init__(self, stdout=None, stderr=None, exit_code=None, cmd=None,
                 description=None):
        if description is None:
            description = "Unexpected error while running command."
        if exit_code is None:
            exit_code = '-'
        message = "%s\nCommand: %s\nExit code: %s\nStdout: %r\nStderr: %r" % (
                  description, cmd, exit_code, stdout, stderr)
        IOError.__init__(self, message)


class Error(Exception):
    def __init__(self, message=None):
        super(Error, self).__init__(message)


class ApiError(Error):
    def __init__(self, message='Unknown', code='Unknown'):
        self.message = message
        self.code = code
        super(ApiError, self).__init__('%s: %s' % (code, message))


class NotFound(Error):
    pass


class UnknownScheme(Error):

    msg = "Unknown scheme '%s' found in URI"

    def __init__(self, scheme):
        msg = self.__class__.msg % scheme
        super(UnknownScheme, self).__init__(msg)


class BadStoreUri(Error):

    msg = "The Store URI %s was malformed. Reason: %s"

    def __init__(self, uri, reason):
        msg = self.__class__.msg % (uri, reason)
        super(BadStoreUri, self).__init__(msg)


class Duplicate(Error):
    pass


class NotAuthorized(Error):
    pass


class NotEmpty(Error):
    pass


class Invalid(Error):
    pass


class BadInputError(Exception):
    """Error resulting from a client sending bad input to a server"""
    pass


class MissingArgumentError(Error):
    pass


class DatabaseMigrationError(Error):
    pass


class ClientConnectionError(Exception):
    """Error resulting from a client connecting to a server"""
    pass


def wrap_exception(f):
    def _wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception, e:
            if not isinstance(e, Error):
                #exc_type, exc_value, exc_traceback = sys.exc_info()
                logging.exception('Uncaught exception')
                #logging.error(traceback.extract_stack(exc_traceback))
                raise Error(str(e))
            raise
    _wrap.func_name = f.func_name
    return _wrap


class OpenstackException(Exception):
    """
    Base Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = "An unknown exception occurred"

    def __init__(self, **kwargs):
        try:
            self._error_string = self.message % kwargs

        except Exception:
            # at least get the core message out if something happened
            self._error_string = self.message

    def __str__(self):
        return self._error_string


class InvalidContentType(OpenstackException):
    message = "Invalid content type %(content_type)s"

########NEW FILE########
__FILENAME__ = context
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
Middleware that attaches a context to the WSGI request
"""

from openstack.common import utils
from openstack.common import wsgi
from openstack.common import context


class ContextMiddleware(wsgi.Middleware):
    def __init__(self, app, options):
        self.options = options
        super(ContextMiddleware, self).__init__(app)

    def make_context(self, *args, **kwargs):
        """
        Create a context with the given arguments.
        """

        # Determine the context class to use
        ctxcls = context.RequestContext
        if 'context_class' in self.options:
            ctxcls = utils.import_class(self.options['context_class'])

        return ctxcls(*args, **kwargs)

    def process_request(self, req):
        """
        Extract any authentication information in the request and
        construct an appropriate context from it.
        """
        # Use the default empty context, with admin turned on for
        # backwards compatibility
        req.context = self.make_context(is_admin=True)


def filter_factory(global_conf, **local_conf):
    """
    Factory method for paste.deploy
    """
    conf = global_conf.copy()
    conf.update(local_conf)

    def filter(app):
        return ContextMiddleware(app, conf)

    return filter

########NEW FILE########
__FILENAME__ = utils
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
System-level utilities and helper functions.
"""

import datetime
import sys

from openstack.common import exception


TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def int_from_bool_as_string(subject):
    """
    Interpret a string as a boolean and return either 1 or 0.

    Any string value in:
        ('True', 'true', 'On', 'on', '1')
    is interpreted as a boolean True.

    Useful for JSON-decoded stuff and config file parsing
    """
    return bool_from_string(subject) and 1 or 0


def bool_from_string(subject):
    """
    Interpret a string as a boolean.

    Any string value in:
        ('True', 'true', 'On', 'on', '1')
    is interpreted as a boolean True.

    Useful for JSON-decoded stuff and config file parsing
    """
    if type(subject) == type(bool):
        return subject
    if hasattr(subject, 'startswith'):  # str or unicode...
        if subject.strip().lower() in ('true', 'on', '1'):
            return True
    return False


def import_class(import_str):
    """Returns a class from a string including module and class"""
    mod_str, _sep, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ImportError, ValueError, AttributeError):
        raise exception.NotFound('Class %s cannot be found' % class_str)


def import_object(import_str):
    """Returns an object including a module or module and class"""
    try:
        __import__(import_str)
        return sys.modules[import_str]
    except ImportError:
        cls = import_class(import_str)
        return cls()


def isotime(at=None):
    if not at:
        at = datetime.datetime.utcnow()
    return at.strftime(TIME_FORMAT)


def parse_isotime(timestr):
    return datetime.datetime.strptime(timestr, TIME_FORMAT)

########NEW FILE########
__FILENAME__ = wsgi
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
Utility methods for working with WSGI servers
"""

import json
import logging
import sys
import datetime
import urllib2

import eventlet
import eventlet.wsgi
eventlet.patcher.monkey_patch(all=False, socket=True)
import routes
import routes.middleware
import webob.dec
import webob.exc

from openstack.common import exception

logger = logging.getLogger('openstack.common.wsgi')


class WritableLogger(object):
    """A thin wrapper that responds to `write` and logs."""

    def __init__(self, logger, level=logging.DEBUG):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg.strip("\n"))


def run_server(application, port):
    """Run a WSGI server with the given application."""
    sock = eventlet.listen(('0.0.0.0', port))
    eventlet.wsgi.server(sock, application)


class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, threads=1000):
        self.pool = eventlet.GreenPool(threads)

    def start(self, application, port, host='0.0.0.0', backlog=128):
        """Run a WSGI server with the given application."""
        socket = eventlet.listen((host, port), backlog=backlog)
        self.pool.spawn_n(self._run, application, socket)

    def wait(self):
        """Wait until all servers have completed running."""
        try:
            self.pool.waitall()
        except KeyboardInterrupt:
            pass

    def _run(self, application, socket):
        """Start a WSGI server in a new green thread."""
        logger = logging.getLogger('eventlet.wsgi.server')
        eventlet.wsgi.server(socket, application, custom_pool=self.pool,
                             log=WritableLogger(logger))


class Middleware(object):
    """
    Base WSGI middleware wrapper. These classes require an application to be
    initialized that will be called next.  By default the middleware will
    simply call its wrapped app, or you can override __call__ to customize its
    behavior.
    """

    def __init__(self, application):
        self.application = application

    def process_request(self, req):
        """
        Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.
        """
        return None

    def process_response(self, response):
        """Do whatever you'd like to the response."""
        return response

    @webob.dec.wsgify
    def __call__(self, req):
        response = self.process_request(req)
        if response:
            return response
        response = req.get_response(self.application)
        return self.process_response(response)


class Debug(Middleware):
    """
    Helper class that can be inserted into any WSGI application chain
    to get information about the request and response.
    """

    @webob.dec.wsgify
    def __call__(self, req):
        print ("*" * 40) + " REQUEST ENVIRON"
        for key, value in req.environ.items():
            print key, "=", value
        print
        resp = req.get_response(self.application)

        print ("*" * 40) + " RESPONSE HEADERS"
        for (key, value) in resp.headers.iteritems():
            print key, "=", value
        print

        resp.app_iter = self.print_generator(resp.app_iter)

        return resp

    @staticmethod
    def print_generator(app_iter):
        """
        Iterator that prints the contents of a wrapper string iterator
        when iterated.
        """
        print ("*" * 40) + " BODY"
        for part in app_iter:
            sys.stdout.write(part)
            sys.stdout.flush()
            yield part
        print


class Router(object):

    """
    WSGI middleware that maps incoming requests to WSGI apps.
    """

    def __init__(self, mapper):
        """
        Create a router for the given routes.Mapper.

        Each route in `mapper` must specify a 'controller', which is a
        WSGI app to call.  You'll probably want to specify an 'action' as
        well and have your controller be a wsgi.Controller, who will route
        the request to the action method.

        Examples:
          mapper = routes.Mapper()
          sc = ServerController()

          # Explicit mapping of one route to a controller+action
          mapper.connect(None, "/svrlist", controller=sc, action="list")

          # Actions are all implicitly defined
          mapper.resource("server", "servers", controller=sc)

          # Pointing to an arbitrary WSGI app.  You can specify the
          # {path_info:.*} parameter so the target app can be handed just that
          # section of the URL.
          mapper.connect(None, "/v1.0/{path_info:.*}", controller=BlogApp())
        """
        self.map = mapper
        self._router = routes.middleware.RoutesMiddleware(self._dispatch,
                                                          self.map)

    @webob.dec.wsgify
    def __call__(self, req):
        """
        Route the incoming request to a controller based on self.map.
        If no match, return a 404.
        """
        return self._router

    @staticmethod
    @webob.dec.wsgify
    def _dispatch(req):
        """
        Called by self._router after matching the incoming request to a route
        and putting the information into req.environ.  Either returns 404
        or the routed WSGI app's response.
        """
        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            return webob.exc.HTTPNotFound()
        app = match['controller']
        return app


class Request(webob.Request):

    """Add some Openstack API-specific logic to the base webob.Request."""

    def best_match_content_type(self):
        """Determine the requested response content-type."""
        supported = ('application/json',)
        bm = self.accept.best_match(supported)
        return bm or 'application/json'

    def get_content_type(self, allowed_content_types):
        """Determine content type of the request body."""
        if not "Content-Type" in self.headers:
            raise exception.InvalidContentType(content_type=None)

        content_type = self.content_type

        if content_type not in allowed_content_types:
            raise exception.InvalidContentType(content_type=content_type)
        else:
            return content_type


class JSONRequestDeserializer(object):
    def has_body(self, request):
        """
        Returns whether a Webob.Request object will possess an entity body.

        :param request:  Webob.Request object
        """
        if 'transfer-encoding' in request.headers:
            return True
        elif request.content_length > 0:
            return True

        return False

    def from_json(self, datastring):
        return json.loads(datastring)

    def default(self, request):
        msg = "Request deserialization: %s" % request
        logger.debug(msg)
        if self.has_body(request):
            logger.debug("Deserialization: request has body")
            if request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
                body  =  urllib2.unquote(request.body)
            else:
                body = request.body
            msg = "Request body: %s" % body
            logger.debug(msg)
            return {'body': self.from_json(body)}
        else:
            logger.debug("Deserialization: request has NOT body")
            return {}


class JSONResponseSerializer(object):

    def to_json(self, data):
        def sanitizer(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return obj

        return json.dumps(data, default=sanitizer)

    def default(self, response, result):
        logger.debug("JSONSerializer default method called.")
        response.headers['Content-Type'] = 'application/json'
        response.body = self.to_json(result)


class Resource(object):
    """
    WSGI app that handles (de)serialization and controller dispatch.

    Reads routing information supplied by RoutesMiddleware and calls
    the requested action method upon its deserializer, controller,
    and serializer. Those three objects may implement any of the basic
    controller action methods (create, update, show, index, delete)
    along with any that may be specified in the api router. A 'default'
    method may also be implemented to be used in place of any
    non-implemented actions. Deserializer methods must accept a request
    argument and return a dictionary. Controller methods must accept a
    request argument. Additionally, they must also accept keyword
    arguments that represent the keys returned by the Deserializer. They
    may raise a webob.exc exception or return a dict, which will be
    serialized by requested content type.
    """
    def __init__(self, controller, deserializer, serializer):
        """
        :param controller: object that implement methods created by routes lib
        :param deserializer: object that supports webob request deserialization
                             through controller-like actions
        :param serializer: object that supports webob response serialization
                           through controller-like actions
        """
        self.controller = controller
        self.serializer = serializer
        self.deserializer = deserializer

    # NOTE(yorik-sar): ugly fix for Routes misbehaviour
    def __add__(self, other):
        return other

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        """WSGI method that controls (de)serialization and method dispatch."""
        logger.debug("Resource __call__ is invoked")
        action_args = self.get_action_args(request.environ)
        action = action_args.pop('action', None)

        deserialized_params = self.deserialize_request(action, request)
        action_args.update(deserialized_params)
        action_result = self.execute_action(action, request, **action_args)

        try:
            return self.serialize_response(action, action_result, request)

        # return unserializable result (typically a webob exc)
        except Exception:
            return action_result

    def deserialize_request(self, action, request):
        return self.dispatch(self.deserializer, action, request)

    def serialize_response(self, action, action_result, request):
        msg = "Called serialize response Action:%s Result:%s  Request:%s" % (action,  action_result,  request)
        logger.debug(msg)

        try:
            if not self.controller:
                meth = getattr(self, action)
            else:
                meth = getattr(self.controller, action)
        except AttributeError:
            raise

        code = 200
        if hasattr(meth, 'wsgi_code'):
            code = meth.wsgi_code

        response = webob.Response()
        response.status = code
        logger.debug("serializer: dispatching call")
        #TODO check why it fails with original openstack code
        #self.dispatch(self.serializer, action, response,
         #             action_result, request)
        if action_result is not None:
            self.serializer.default(response,  action_result)
        msg = "Response: %s" % response
        logger.debug(msg)
        return response

    def execute_action(self, action, request, **action_args):
        return self.dispatch(self.controller, action, request, **action_args)

    def dispatch(self, obj, action, *args, **kwargs):
        """Find action-specific method on self and call it."""
        try:
            method = getattr(obj, action)
        except AttributeError:
            method = getattr(obj, 'default')

        return method(*args, **kwargs)

    def get_action_args(self, request_environment):
        """Parse dictionary created by routes library."""
        try:
            args = request_environment['wsgiorg.routing_args'][1].copy()
        except Exception:
            return {}

        try:
            del args['controller']
        except KeyError:
            pass

        try:
            del args['format']
        except KeyError:
            pass

        return args

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 OpenStack, LLC
# All Rights Reserved.
#
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

# Colorizer Code is borrowed from Twisted:
# Copyright (c) 2001-2010 Twisted Matrix Laboratories.
#
#    Permission is hereby granted, free of charge, to any person obtaining
#    a copy of this software and associated documentation files (the
#    "Software"), to deal in the Software without restriction, including
#    without limitation the rights to use, copy, modify, merge, publish,
#    distribute, sublicense, and/or sell copies of the Software, and to
#    permit persons to whom the Software is furnished to do so, subject to
#    the following conditions:
#
#    The above copyright notice and this permission notice shall be
#    included in all copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
#    LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
#    WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unittest runner for balancer

To run all test::
    python run_tests.py

To run a single test::
    python run_tests.py test_stores:TestSwiftBackend.test_get

To run a single test module::
    python run_tests.py test_stores
"""

import gettext
import logging
import os
import unittest
import sys

gettext.install('balancer', unicode=1)

from nose import config
from nose import result
from nose import core


class _AnsiColorizer(object):
    """
    A colorizer is an object that loosely wraps around a stream, allowing
    callers to write text to the stream in a particular color.

    Colorizer classes must implement C{supported()} and C{write(text, color)}.
    """
    _colors = dict(black=30, red=31, green=32, yellow=33,
                   blue=34, magenta=35, cyan=36, white=37)

    def __init__(self, stream):
        self.stream = stream

    def supported(cls, stream=sys.stdout):
        """
        A class method that returns True if the current platform supports
        coloring terminal output using this method. Returns False otherwise.
        """
        if not stream.isatty():
            return False  # auto color only on TTYs
        try:
            import curses
        except ImportError:
            return False
        else:
            try:
                try:
                    return curses.tigetnum("colors") > 2
                except curses.error:
                    curses.setupterm()
                    return curses.tigetnum("colors") > 2
            except:
                raise
                # guess false in case of error
                return False
    supported = classmethod(supported)

    def write(self, text, color):
        """
        Write the given text to the stream in the given color.

        @param text: Text to be written to the stream.

        @param color: A string label for a color. e.g. 'red', 'white'.
        """
        color = self._colors[color]
        self.stream.write('\x1b[%s;1m%s\x1b[0m' % (color, text))


class _Win32Colorizer(object):
    """
    See _AnsiColorizer docstring.
    """
    def __init__(self, stream):
        from win32console import GetStdHandle, STD_OUT_HANDLE, \
             FOREGROUND_RED, FOREGROUND_BLUE, FOREGROUND_GREEN, \
             FOREGROUND_INTENSITY
        red, green, blue, bold = (FOREGROUND_RED, FOREGROUND_GREEN,
                                  FOREGROUND_BLUE, FOREGROUND_INTENSITY)
        self.stream = stream
        self.screenBuffer = GetStdHandle(STD_OUT_HANDLE)
        self._colors = {
            'normal': red | green | blue,
            'red': red | bold,
            'green': green | bold,
            'blue': blue | bold,
            'yellow': red | green | bold,
            'magenta': red | blue | bold,
            'cyan': green | blue | bold,
            'white': red | green | blue | bold}

    def supported(cls, stream=sys.stdout):
        try:
            import win32console
            screenBuffer = win32console.GetStdHandle(
                win32console.STD_OUT_HANDLE)
        except ImportError:
            return False
        import pywintypes
        try:
            screenBuffer.SetConsoleTextAttribute(
                win32console.FOREGROUND_RED |
                win32console.FOREGROUND_GREEN |
                win32console.FOREGROUND_BLUE)
        except pywintypes.error:
            return False
        else:
            return True
    supported = classmethod(supported)

    def write(self, text, color):
        color = self._colors[color]
        self.screenBuffer.SetConsoleTextAttribute(color)
        self.stream.write(text)
        self.screenBuffer.SetConsoleTextAttribute(self._colors['normal'])


class _NullColorizer(object):
    """
    See _AnsiColorizer docstring.
    """
    def __init__(self, stream):
        self.stream = stream

    def supported(cls, stream=sys.stdout):
        return True
    supported = classmethod(supported)

    def write(self, text, color):
        self.stream.write(text)


class BalancerTestResult(result.TextTestResult):
    def __init__(self, *args, **kw):
        result.TextTestResult.__init__(self, *args, **kw)
        self._last_case = None
        self.colorizer = None
        # NOTE(vish, tfukushima): reset stdout for the terminal check
        stdout = sys.stdout
        sys.stdout = sys.__stdout__
        for colorizer in [_Win32Colorizer, _AnsiColorizer, _NullColorizer]:
            if colorizer.supported():
                self.colorizer = colorizer(self.stream)
                break
        sys.stdout = stdout

    def getDescription(self, test):
        return str(test)

    # NOTE(vish, tfukushima): copied from unittest with edit to add color
    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        if self.showAll:
            self.colorizer.write("OK", 'green')
            self.stream.writeln()
        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    # NOTE(vish, tfukushima): copied from unittest with edit to add color
    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if self.showAll:
            self.colorizer.write("FAIL", 'red')
            self.stream.writeln()
        elif self.dots:
            self.stream.write('F')
            self.stream.flush()

    # NOTE(vish, tfukushima): copied from unittest with edit to add color
    def addError(self, test, err):
        """
        Overrides normal addError to add support for errorClasses.
        If the exception is a registered class, the error will be added
        to the list for that class, not errors.
        """
        stream = getattr(self, 'stream', None)
        ec, ev, tb = err
        try:
            exc_info = self._exc_info_to_string(err, test)
        except TypeError:
            # This is for compatibility with Python 2.3.
            exc_info = self._exc_info_to_string(err)
        for cls, (storage, label, isfail) in self.errorClasses.items():
            if result.isclass(ec) and issubclass(ec, cls):
                if isfail:
                    test.passwd = False
                storage.append((test, exc_info))
                # Might get patched into a streamless result
                if stream is not None:
                    if self.showAll:
                        message = [label]
                        detail = result._exception_detail(err[1])
                        if detail:
                            message.append(detail)
                        stream.writeln(": ".join(message))
                    elif self.dots:
                        stream.write(label[:1])
                return
        self.errors.append((test, exc_info))
        test.passed = False
        if stream is not None:
            if self.showAll:
                self.colorizer.write("ERROR", 'red')
                self.stream.writeln()
            elif self.dots:
                stream.write('E')

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        current_case = test.test.__class__.__name__

        if self.showAll:
            if current_case != self._last_case:
                self.stream.writeln(current_case)
                self._last_case = current_case

            self.stream.write(
                '    %s' % str(test.test._testMethodName).ljust(60))
            self.stream.flush()


class BalancerTestRunner(core.TextTestRunner):
    def _makeResult(self):
        return BalancerTestResult(self.stream,
                              self.descriptions,
                              self.verbosity,
                              self.config)


if __name__ == '__main__':
    logger = logging.getLogger()
    hdlr = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

    c = config.Config(stream=sys.stdout,
                      env=os.environ,
                      verbosity=3,
                      plugins=core.DefaultPluginManager())

    runner = BalancerTestRunner(stream=c.stream,
                            verbosity=c.verbosity,
                            config=c)
    sys.exit(not core.run(config=c, testRunner=runner))

########NEW FILE########
__FILENAME__ = install_venv
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2010 OpenStack LLC.
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
Installation script for Glance's development virtualenv
"""

import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
VENV = os.path.join(ROOT, '.venv')
PIP_REQUIRES = os.path.join(ROOT, 'tools', 'pip-requires')
TEST_REQUIRES = os.path.join(ROOT, 'tools', 'test-requires')


def die(message, *args):
    print >> sys.stderr, message % args
    sys.exit(1)


def run_command(cmd, redirect_output=True, check_exit_code=True):
    """
    Runs a command in an out-of-process shell, returning the
    output of that command.  Working directory is ROOT.
    """
    if redirect_output:
        stdout = subprocess.PIPE
    else:
        stdout = None

    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=stdout)
    output = proc.communicate()[0]
    if check_exit_code and proc.returncode != 0:
        die('Command "%s" failed.\n%s', ' '.join(cmd), output)
    return output


HAS_EASY_INSTALL = bool(run_command(['which', 'easy_install'],
                                    check_exit_code=False).strip())
HAS_VIRTUALENV = bool(run_command(['which', 'virtualenv'],
                                    check_exit_code=False).strip())


def check_dependencies():
    """Make sure virtualenv is in the path."""

    if not HAS_VIRTUALENV:
        print 'not found.'
        # Try installing it via easy_install...
        if HAS_EASY_INSTALL:
            print 'Installing virtualenv via easy_install...',
            if not run_command(['which', 'easy_install']):
                die('ERROR: virtualenv not found.\n\n'
                    'Balancer development requires virtualenv, please install'
                    ' it using your favorite package management tool')
            print 'done.'
    print 'done.'


def create_virtualenv(venv=VENV):
    """
    Creates the virtual environment and installs PIP only into the
    virtual environment
    """
    print 'Creating venv...',
    run_command(['virtualenv', '-q', '--no-site-packages', VENV])
    print 'done.'
    print 'Installing pip in virtualenv...',
    if not run_command(['tools/with_venv.sh', 'easy_install',
                        'pip>1.0']).strip():
        die("Failed to install pip.")
    print 'done.'


def pip_install(*args):
    run_command(['tools/with_venv.sh',
                 'pip', 'install', '--upgrade'] + list(args),
                redirect_output=False)


def install_dependencies(venv=VENV):
    print 'Installing dependencies with pip (this can take a while)...'

    pip_install('pip')

    pip_install('-r', PIP_REQUIRES)
    pip_install('-r', TEST_REQUIRES)

    # Tell the virtual env how to "import glance"
    py_ver = _detect_python_version(venv)
    pthfile = os.path.join(venv, "lib", py_ver,
                           "site-packages", "balancer.pth")
    f = open(pthfile, 'w')
    f.write("%s\n" % ROOT)


def _detect_python_version(venv):
    lib_dir = os.path.join(venv, "lib")
    for pathname in os.listdir(lib_dir):
        if pathname.startswith('python'):
            return pathname
    raise Exception('Unable to detect Python version')


def print_help():
    help = """
 Glance development environment setup is complete.

 Glance development uses virtualenv to track and manage Python dependencies
 while in development and testing.

 To activate the Glance virtualenv for the extent of your current shell session
 you can run:

 $ source .venv/bin/activate

 Or, if you prefer, you can run commands in the virtualenv on a case by case
 basis by running:

 $ tools/with_venv.sh <your command>

 Also, make test will automatically use the virtualenv.
    """
    print help


def main(argv):
    check_dependencies()
    create_virtualenv()
    install_dependencies()
    print_help()

if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
