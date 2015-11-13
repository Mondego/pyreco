__FILENAME__ = cloudmanagers
from synapse.resources.resources import ResourcesController
from synapse.resources.resources import ResourceException
from synapse.config import config

from synapse.logger import logger
import traceback
import sys
import os
import uuid
import random
import cm_util
import cm_openstack

@logger
class CloudmanagersController(ResourcesController):

    __resource__ = "cloudmanagers"

    # The types of cloud managers handled by the plugin
    CM_TYPE_OPENSTACK = "openstack"

    # A dict to map the submodules to the cloud managers types
    CM_MAPPING = {cm_openstack: [CM_TYPE_OPENSTACK]}

    # The configuration file of the cloud managers plugin
    CLOUDMANAGERS_CONFIG_FILE = config.paths['config_path'] + "/plugins/cloudmanagers.conf"

#-----------------------------------------------------------------------------

    def __init__(self, mod):
		super(CloudmanagersController, self).__init__(mod)
		try:
			pass
		except ResourceException:
			self.logger.warn('{0} in not valid. The {1} plugin will probably not work'.format(self.CLOUDMANAGERS_CONFIG_FILE,self.__resource__))

#-----------------------------------------------------------------------------

    def _get_cloudmanager_type(self, res_id):
		return cm_util.get_config_option(res_id, "cm_type", self.CLOUDMANAGERS_CONFIG_FILE)

#-----------------------------------------------------------------------------

    def _load_driver_module(self, cm_type):
        for module in self.CM_MAPPING:
            if cm_type in self.CM_MAPPING[module]:
                try:
                    return module
                except ImportError:
                    pass
        return None

#-----------------------------------------------------------------------------

    def listimages(self, res_id=None, attributes=None):
        status={}
        error = None
        if(attributes is None):
            status['cloudmanagers'] = res_id
            status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            status['images'] = module._get_images(attributes)

        else:
            raise ResourceException("No arguments are yet allowed for this method")

        return status

#-----------------------------------------------------------------------------

    def read(self, res_id=None, attributes=None):
        status = {}
        error = None
        # If the cloud manager's id is not specified, the method will return a
        # list of the managed cloud managers ids
        if res_id == "":
            status['cloudmanagers'] = self._get_cloudmanagers()

        # If only the cloud manager's id is given, the method will return a
        # list of the existing virtual machines on the cloud manager
        elif (attributes is None or "name" not in attributes and "listimages" not in attributes):
            status['cloudmanagers'] = res_id
            status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            # Retrieve the list of VMs
            status['VMs'] = module._get_VMs(attributes)

        elif ("listimages" in attributes):
            status['cloudmanagers'] = res_id
            status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)

            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)

            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            status['images'] = module._get_images(attributes)
        else:
            # Retrieve the good module
            cm_type = self._get_cloudmanager_type(res_id)
            module = self._load_driver_module(cm_type)
            # Initialize mandatory attributes depending on cloud manager's type
            module._init_cloudmanager_attributes(res_id, attributes)

            # Check if the VM exists and retrieve the various important fields to return
            if module._exists(attributes):
                status['cloudmanager'] = res_id
                status['url'] = cm_util.get_config_option(res_id, "url", self.CLOUDMANAGERS_CONFIG_FILE)
                status['vm_name'] = attributes['name']

                try:
                    status['vm_vcpus'] = module._get_vcpus(attributes)
                except ResourceException, ex:
                    status['vm_vcpus'] = str(ex)

                try:
                    vm = module._get_VM(attributes)
                    vm_id = vm['id']
                    flavor = module._get_flavor(attributes, vm['id'])
                    status['vm_flavor'] = flavor['id']
                except ResourceException, ex:
                    status['vm_flavor'] = str(ex)

                status['vm_vnc_port'] = module._get_vnc_port(attributes)

                # Verifies if this is a vnx request
                # TODO: the vnc part should come here

            else:
                raise ResourceException("The specified VM doesn't exist")

            num_status = module._get_status(attributes)
            status['vm_status'] = module._get_readable_status(num_status)

        return status
#-----------------------------------------------------------------------------

    def create(self, res_id=None, attributes={}):
        status = {}
        error = ''

        passed = True

        cm_type = None
        module = None

        # Check mandatory attributes
        required_keys = ["name"]
        self._check_keys_in_dict(attributes, required_keys)

        # Check integer attributes
        int_attributes_keys = ["flavor", "vnc_port"]
        self._check_int_attributes(attributes, int_attributes_keys)

        # Check attributes values
        self._check_attributes_values(attributes)

        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Initialize mandatory attributes depending on cloud manager's type
        module._init_cloudmanager_attributes(res_id, attributes)


        # Check if the virtual machine exists
        if passed and not module._exists(attributes):

            try:
                # Initialize mandatory attributes depending on cloudmanager's type
                module._init_cloudmanager_attributes(res_id, attributes)
                cm_type = self._get_cloudmanager_type(res_id)
                # Initialize the virtual machine dictionary
                dict_vm = {'type': cm_type,
                    'name': attributes['name'],
                    'flavor': attributes.get('flavor', ""),
                    'image': attributes.get('image', ""),
                    'key': attributes.get('key', ""),
                    'user-data': attributes.get('user-data', "")
                }

                self.logger.debug("VM details: %s" % dict_vm)

                # Create and provision the VM
                state = module._create_VM(res_id, attributes, dict_vm)

                status['vm_status'] = module._get_readable_status(state)
                status['created'] = True
                status['vm_name'] = attributes['name']

            # If there was an error during the virtual machine's creation
            except ResourceException, ex:
                status['vm_name'] = attributes['name']
                status['vm_status'] = cm_util.VM_STATE_UNKNOWN
                status['created'] = False

            except Exception, ex:
                traceback.print_exc(file=sys.stdout)
        # If a virtual machine with the same name already exists
        elif passed:
            status['vm_name'] = attributes['name']
            state = module._get_status(attributes)
            status['vm_status'] = module._get_readable_status(state)
            status['created'] = False
            raise ResourceException("A VM already exists under this name")

        status['cloudmanager'] = res_id
        return status
#-----------------------------------------------------------------------------
    def update(self, res_id=None, attributes={}):
        status = {}
        error = None

        keys_upd_status = ["status"]
        keys_upd_flavor = ["flavor"]
        cmd_mandatory_keys = [keys_upd_status, keys_upd_flavor]

        # Check if there is at least one update command with all required
        # attributes
        cpt = 0
        for keys in cmd_mandatory_keys:
            try:
                self._check_keys_in_dict(attributes, keys)
                cpt += 1
            except ResourceException:
                pass

        # Retrieve the good module and the corresponding connection
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Initialize mandatory attributes depending on cloud manager's type
        module._init_cloudmanager_attributes(res_id, attributes)

        # If none of the tests has passed, an error message is appended
        if cpt == 0:
            raise ResourceException("There must be at least "
                                       "one command to do an update")

        # If the virtual machine exists
        elif module._exists(attributes):
            # Check the semantic values of some attributes
            self._check_attributes_values(attributes)

            status['vm_name'] = attributes['name']

            # Update the status
            if "status" in attributes:
                num_status = module._get_status(attributes)
                str_status = module._get_readable_status(num_status)

                # Check if the virtual machine is not in the required
                # state
                if (attributes['status'] != str_status):
                    num_status = self._set_status(res_id, attributes)
                    status['vm_status'] = module._get_readable_status(num_status)
                else:
                    status['vm_status'] = str_status

            # Update the flavor
            if ("flavor" in attributes):

                    vm = module._get_VM(attributes)
                    vm_id = vm['id']
                    current_flavor = module._get_flavor(attributes, vm_id)
                    new_flavor = attributes["flavor"]

                    flavor_dict = module._set_flavor(attributes, vm_id, current_flavor["id"], new_flavor)
                    status['vm_flavor'] = flavor_dict["id"]


        # If the virtual machine doesn't exist
        else:
            raise ResourceException("The specified VM doesn't "
                                       "exist")

        status['cloudmanager'] = res_id

        return status

#-----------------------------------------------------------------------------
    def delete(self, res_id=None, attributes=None):
        status = {}
        error = None

        required_keys = ["name"]

        # Check if the name of the virtual machine to delete exists in the
        # attributes
        self._check_keys_in_dict(attributes, required_keys)

        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Initialize mandatory attributes depending on cloud manager's type
        module._init_cloudmanager_attributes(res_id, attributes)

        # Check if the virtual machine exists
        if module._exists(attributes):
            status['vm_name'] = attributes['name']

            num_status = module._get_status(attributes)

            # If the machine is running and the attribute 'force' is not
            #specified, then the machine can't be removed
            if (("force" not in attributes or attributes['force'] == False)
                and module._get_readable_status(num_status) == cm_util.VM_STATE_RUNNING):
                    status['vm_status'] = module._get_readable_status(num_status)
                    status['deleted'] = False
                    raise ResourceException("The VM is "
                                "currently running. Use the option "
                                "force or shutdown the VM.")

            # Otherwise, we can remove the virtual machine
            else:
                state = module._delete_VM(attributes)
                status['vm_status'] = module._get_readable_status(state)
                status['deleted'] = True

        # If the machine doesn't exist
        else:
            status['vm_name'] = attributes['name']
            status['vm_status'] = cm_util.VM_STATE_UNKNOWN
            status['deleted'] = False
            raise ResourceException("The specified VM doesn't exist")

        status['cloudmanager'] = res_id
        return status


#-----------------------------------------------------------------------------

    def _get_cloudmanagers(self):
        '''
        Returns cloudmanagers from the config file
        '''
        config = cm_util.read_config_file(self.CLOUDMANAGERS_CONFIG_FILE)
        # Get a list of sections corresponding to cloud managers ids
        cloudmanagers = config.sections()
        try:
            # Remove general section
            cloudmanagers.remove("general")
        except ValueError:
            pass

        return cloudmanagers
#-----------------------------------------------------------------------------

    def _check_keys_in_dict(self, dictionary, keys):
        '''
        Checks if keys exist in a dict.

        @param dictionary: the dictionary on which the keys will be checked
        @type dictionary: dict

        @param keys: the keys to check in the given dictionary
        @type keys: list
        '''
        for key in keys:
            if key not in dictionary:
                raise ResourceException("Mandatory attribute '%s' is missing"
                                        % key)
            elif key is None:
                raise ResourceException("Mandatory attribute '%s' is None"
                                        % key)

#-----------------------------------------------------------------------------

    def _check_attributes_values(self, attributes):
        '''
        Checks values of the attributes dictionary in terms of semantic

        @param attributes: the dictionary of attributes
        @type attributes: dict
        '''
        if "name" in attributes:
            if attributes['name'] == "":
                raise ResourceException("The VM name must not be empty.")

        if "flavor" in attributes:
            if attributes['flavor'] == "" :
                raise ResourceException("The flavor must be specified.")

        if "image" in attributes:
            if attributes['image'] == "":
                raise ResourceException("The image must be specified")

#-----------------------------------------------------------------------------

    def _check_int_attributes(self, attributes, keys):
        '''
        Checks integer values in a dictionary

        @param attributes: the dictionary on which the integer keys will be
                            checked
        @type attributes: dict

        @param keys: the keys of the integer attributes
        @type keys: list
        '''
        for key in keys:
            if key in attributes:
                try:
                    int(attributes[key])
                except ValueError:
                    raise ResourceException("Attribute '%s' must be integer" %
                                            key)
                except TypeError:
                    raise ResourceException("Attribute '%s' is None" % key)

#-----------------------------------------------------------------------------


    def _set_status(self, res_id, attributes):
        '''
        Retrieves the status number and executes the corresponding action.

        @param res_id: cloud manager's id
        @type res_id: str

        @param attributes: the different attributes which will be used to
                            update the status of a virtual machine
        @type attributes: dict
        '''
        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # If the virtual machine is already in the given state, then this state
        # is returned
        if attributes['status'] == module._get_status(attributes):
            return module._get_status(attributes)

        try:
            # Retrieve a reference to the method of the module to call to
            # update the status of a virtual machine
            status_action = {
                cm_util.VM_STATE_RUNNING: self._run_vm(res_id, attributes),
                cm_util.VM_STATE_PAUSED: module._pause,
                cm_util.VM_STATE_SHUTDOWN: module._shutdown,
                cm_util.VM_STATE_REBOOTING: module._reboot,
                cm_util.VM_STATE_RESUME: module._resume
            }[attributes['status']]

        except KeyError:
            raise ResourceException("The given status is unknown")

        # Call the method and return the final status of the virtual machine
        return status_action(attributes)

#-----------------------------------------------------------------------------

    def _run_vm(self, res_id, attributes):
        '''
        Returns the most appropriate method to run the VM

        @param res_id: cloud manager's id
        @type res_id: str

        @param attributes: the different attributes which will be used to
                            run a virtual machine
        @type attributes: dict
        '''
        # Retrieve the good module
        cm_type = self._get_cloudmanager_type(res_id)
        module = self._load_driver_module(cm_type)

        # Retrieve the statusd of the virtual machine
        status = module._get_status(attributes)

        # Resume the virtual machine if it's paused and start it in other cases
        if module._get_readable_status(status) == cm_util.VM_STATE_PAUSED:
            return module._resume
        else:
            return module._start

########NEW FILE########
__FILENAME__ = cm_openstack
import cm_util
from synapse.config import config
from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourceException
import json
from restful_lib import Connection

import ConfigParser

from synapse.logger import logger
from synapse.syncmd import exec_cmd

# The configuration file of the cloud managers plugin
CLOUDMANAGERS_CONFIG_FILE = config.paths['config_path'] + "/plugins/cloudmanagers.conf"

log = logger("cm_openstack")

#-----------------------------------------------------------------------------

def _get_VMs(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id +"/servers", args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        servers = json.loads(resp['body'])
        i = 0
        vms = []
        for r in servers['servers']:
            vms.append(r['name'])
            i = i+1
        return vms
    else:
        log.error("_get_VMs: Bad HTTP return code: %s" % status)
#-----------------------------------------------------------------------------
def _get_VM(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id +"/servers/detail", args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    found = 0
    if status == '200' or status == '304':
        servers = json.loads(resp['body'])
        for vm in servers['servers']:
            if attributes['name'] == vm['name']:
                found = 1
                return vm
        if found == 0:
            #return False
            raise ResourceException("vm %s not found" % attributes['name'])
    else:
        log.error("_get_VM: Bad HTTP return code: %s" % status)

#-----------------------------------------------------------------------------

def _exists(attributes):
    try:
        _get_VM(attributes)
        return True
    except ResourceException:
        return False

#-----------------------------------------------------------------------------

def _get_vcpus(attributes):
    vm = _get_VM(attributes)
    if not vm['status'] == 'ACTIVE':
        raise ResourceException("The CPUs info can't be retrieved while the VM is not running")
    vm_id = vm['id']
    flavor = _get_flavor(attributes, vm_id)
    return flavor['vcpus']

#-----------------------------------------------------------------------------

def _get_flavor(attributes, vm_id):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id +"/servers/" + vm_id, args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        server = json.loads(resp['body'])
        flavor_id = server['server']['flavor']['id']
    else:
        log.error("Bad HTTP return code: %s" % status)
    resp = conn.request_get("/" + tenant_id +"/flavors/" + flavor_id, args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        flavor = json.loads(resp['body'])
    else:
        log.error("_get_flavor: Bad HTTP return code: %s" % status)
    return flavor['flavor']

#-----------------------------------------------------------------------------

def _set_flavor(attributes, vm_id, current_flavor, new_flavor):
    vm_status = _get_status(attributes)
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    if (vm_status == 'ACTIVE' and current_flavor != new_flavor):
        body = '{"resize": {"flavorRef":"'+ new_flavor + '"}}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm_id + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            return _get_flavor(attributes, vm_id)
        else:
            log.error("Bad HTTP return code: %s" % status)
    elif (vm_status == 'RESIZE'):
        log.error("Wait for VM resizing before confirming action")
    elif (vm_status == 'VERIFY_RESIZE'):
        body = '{"confirmResize": null}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm_id + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            return _get_flavor(attributes, vm_id)
        else:
            log.error("_set_flavor: Bad HTTP return code: %s" % status)
    else:
        log.error("Wrong VM state or wring destination flavor")

#-----------------------------------------------------------------------------

def _get_vnc_port(attributes):
    return '6969'

#-----------------------------------------------------------------------------

def _get_status(attributes):
    try:
        vm = _get_VM(attributes)
        return vm['status']
    except (ResourceException, 'No status'):
        return 0

#-----------------------------------------------------------------------------

def _init_cloudmanager_attributes(res_id, attributes):
    cloudmanager_type = cm_util.get_config_option(res_id, 'cm_type', CLOUDMANAGERS_CONFIG_FILE)
	# Initialize here specific attributes for OpenStack

    attributes["cm_base_url"] = cm_util.get_config_option(res_id, "url", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_keystone_url"] = cm_util.get_config_option(res_id, "keystone_base_url", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_nova_url"] = cm_util.get_config_option(res_id, "nova_base_url", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_tenant_name"] = cm_util.get_config_option(res_id, "tenant_name", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_username"] = cm_util.get_config_option(res_id, "username", CLOUDMANAGERS_CONFIG_FILE)
    attributes["cm_password"] = cm_util.get_config_option(res_id, "password", CLOUDMANAGERS_CONFIG_FILE)

#-----------------------------------------------------------------------------

def _create_VM(res_id, attributes, dict_vm):
    conn_nova = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    body = '{"server": {"name":"'+ dict_vm['name'].encode() + '", "imageRef":"' + dict_vm['image'].encode() + '", "key_name": "' + dict_vm['key'].encode() + '", "user_data":"' + dict_vm['user-data'] + '", "flavorRef":"' + dict_vm['flavor'] + '", "max_count": 1, "min_count": 1, "security_groups": [{"name": "default"}]}}'
    headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
    uri = tenant_id + "/servers"
    resp = conn_nova.request_post(uri, body=body, headers=headers)
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        data = json.loads(resp['body'])
        return _get_status(attributes)
    else:
        log.error("_create_VM: Bad HTTP return code: %s" % status)

#-----------------------------------------------------------------------------

def _delete_VM(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    vm = _get_VM(attributes)
    vm_id = vm['id']
    resp = conn.request_delete("/" + tenant_id +"/servers/" + vm_id, args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _get_keystone_tokens(attributes):
    conn = Connection(attributes["cm_keystone_url"])
    body = '{"auth": {"tenantName":"'+ attributes["cm_tenant_name"] + '", "passwordCredentials":{"username": "' + attributes["cm_username"] + '", "password": "' + attributes["cm_password"] + '"}}}'
    resp = conn.request_post("/tokens", body=body, headers={'Content-type':'application/json'})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        data = json.loads(resp['body'])
        tenant_id = data['access']['token']['tenant']['id']
        x_auth_token = data['access']['token']['id']
        return tenant_id, x_auth_token
    else:
        log.error("_get_keystone_tokens: Bad HTTP return code: %s" % status)

#-----------------------------------------------------------------------------

def _get_readable_status(num_status):
    return num_status

#-----------------------------------------------------------------------------
def _get_status(attributes):
    try:
        vm = _get_VM(attributes)
        return vm['status']
    except ResourceException as err:
        log.error(err)
        return 0
#-----------------------------------------------------------------------------
def _exists(attributes):
    try:
        _get_VM(attributes)
        return True
    except ResourceException:
        return False
#-----------------------------------------------------------------------------

def _get_images(attributes):
    conn = Connection(attributes["cm_nova_url"], username="", password="")
    tenant_id, x_auth_token = _get_keystone_tokens(attributes)
    resp = conn.request_get("/" + tenant_id + "/images", args={}, headers={'content-type':'application/json', 'accept':'application/json', 'x-auth-token':x_auth_token})
    status = resp[u'headers']['status']
    if status == '200' or status == '304':
        images = json.loads(resp['body'])
        return images['images']
    else:
        log.error("_get_images: Bad HTTP return code: %s" % status)

#-----------------------------------------------------------------------------

def _start(attributes):
    '''
    Starts a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        start a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if _get_status(attributes) == "SUSPENDED":
        conn = Connection(attributes["cm_nova_url"], username="", password="")
        tenant_id, x_auth_token = _get_keystone_tokens(attributes)
        body = '{"resume": null}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm['id'] + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            log.info("VM started up and its status is %s" % _get_status(attributes))
        else:
            log.error("_reboot: Bad HTTP return code: %s" % status)

    else:
        raise ResourceException("The VM must be suspended")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _shutdown(attributes):
    '''
    Shuts down a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        shutdown a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if _get_status(attributes) == "ACTIVE":
        conn = Connection(attributes["cm_nova_url"], username="", password="")
        tenant_id, x_auth_token = _get_keystone_tokens(attributes)
        body = '{"suspend": null}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm['id'] + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            log.info("VM shutted down and its status is %s" % _get_status(attributes))
        else:
            log.error("_reboot: Bad HTTP return code: %s" % status)

    else:
        raise ResourceException("The VM must be running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _reboot(attributes):
    '''
    Reboots a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        reboot a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if _get_status(attributes) == "ACTIVE":
        conn = Connection(attributes["cm_nova_url"], username="", password="")
        tenant_id, x_auth_token = _get_keystone_tokens(attributes)
        body = '{"reboot": {"type" : "SOFT"}}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm['id'] + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            log.info("VM is rebooting and its status is %s" % _get_status(attributes))
        else:
            log.error("_reboot: Bad HTTP return code: %s" % status)

    else:
        raise ResourceException("The VM must be running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

def _pause(attributes):
    '''
    Pauses a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        pause a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if _get_status(attributes) == "ACTIVE":
        conn = Connection(attributes["cm_nova_url"], username="", password="")
        tenant_id, x_auth_token = _get_keystone_tokens(attributes)
        body = '{"pause": null}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm['id'] + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            log.info("VM is paused and its status is %s" % _get_status(attributes))
        else:
            log.error("_pause: Bad HTTP return code: %s" % status)

    else:
        raise ResourceException("The VM must be running")

    return _get_status(attributes)

#-----------------------------------------------------------------------------
def _resume(attributes):
    '''
    Pauses a VM.

    @param attributes: the dictionary of the attributes that will be used to
                        pause a virtual machine
    @type attributes: dict
    '''
    vm = _get_VM(attributes)

    if _get_status(attributes) == "PAUSED":
        conn = Connection(attributes["cm_nova_url"], username="", password="")
        tenant_id, x_auth_token = _get_keystone_tokens(attributes)
        body = '{"unpause": null}'
        headers = {"Content-type": "application/json", "x-auth-token": x_auth_token.encode()}
        uri = tenant_id + "/servers/" + vm['id'] + "/action"
        resp = conn.request_post(uri, body=body, headers=headers)
        status = resp[u'headers']['status']
        if status == '200' or status == '304' or status == '202':
            log.info("VM is unpaused and status is %s" % _get_status(attributes))
        else:
            log.error("_resume: Bad HTTP return code: %s" % status)

    else:
        raise ResourceException("The VM must be paused")

    return _get_status(attributes)

#-----------------------------------------------------------------------------

########NEW FILE########
__FILENAME__ = cm_util
import ConfigParser
from synapse.logger import logger
from synapse.resources.resources import ResourceException

log = logger('cm_util')


# The different states of a virtual machine
VM_STATE_UNKNOWN = "unknown"
VM_STATE_RUNNING = "running"
VM_STATE_BLOCKED = "blocked"
VM_STATE_PAUSED = "paused"
VM_STATE_SHUTDOWN = "shutdown"
VM_STATE_SHUTOFF = "shutoff"
VM_STATE_CRASHED = "crashed"
VM_STATE_REBOOTING = "rebooting"
VM_STATE_RESUME = "resume"


def read_config_file(file_name):
    '''
    Returns a parsed configuration file.

    @param file_name: the path to the configuration file
    @type file_name: str
    '''
    config = ConfigParser.ConfigParser()

    try:
        ret = config.read(file_name)
        if not ret:
            raise ResourceException("The configuration file '%s' doesn't exist"
                                    % file_name)
    except ConfigParser.MissingSectionHeaderError:
        raise ResourceException("Couldn't parse configuration file '%s'" %
                                file_name)

    return config
    
#-----------------------------------------------------------------------------


def get_config_option(res_id, option, config_path):
    '''
    Retrieves an option in a configuration file.

    @param res_id: the hypervisor's id corresponding to a section in the
                    configuration file
    @type res_id: str

    @param option: the option to retrieve the value
    @type option: str

    @param config_path: the path to the configuration file
    @type config_path: str
    '''
    # Retrive the configuration file
    config = read_config_file(config_path)

    # If the section exists in the configuration file
    if config.has_section(res_id):
        try:
            # Return the value of the given option
            return config.get(res_id, option)
        except ConfigParser.NoOptionError:
            raise ResourceException("The option '%s' doesn't exist in "
                                    "libvirt configuration file." % option)
    else:
        raise ResourceException("The cloud manager '%s' doesn't exist in the "
                                "configuration file." % res_id)

#-----------------------------------------------------------------------------

########NEW FILE########
__FILENAME__ = develop
#!/usr/bin/env python

import os
import shutil


current_dir = os.path.dirname(os.path.relpath(__file__))


def create_folders(folders):

    for folder in folders:
        try:
            new_folder = os.path.join(current_dir, 'devel', folder)
            print "Creating %s" % new_folder
            os.makedirs(new_folder)
        except OSError:
            continue


def copy_conf_files(files):
    current_conf_folder = os.path.join(current_dir, 'conf')
    new_conf_folder = os.path.join(current_dir, 'devel', 'etc/synapse-agent')

    for fn in files:
        current_conf = os.path.join(current_conf_folder, fn)
        new_conf = os.path.join(new_conf_folder, fn)
        print "Copying %s to %s" % (current_conf, new_conf)
        if os.path.exists(new_conf):
            print "Saving existing %s to %s.save" % (fn, fn)
            shutil.copy(new_conf, new_conf + '.save')
        shutil.copy(current_conf, new_conf)


if __name__ == '__main__':
    folder = ['etc/synapse-agent',
              'etc/synapse-agent/ssl',
              'etc/synapse-agent/ssl/private',
              'etc/synapse-agent/ssl/certs',
              'etc/synapse-agent/ssl/csr',
              'var/lib/synapse-agent/persistence',
              'var/log/synapse-agent',
              'var/run']

    files = ['synapse-agent.conf',
             'logger.conf',
             'permissions.conf']

    create_folders(folder)
    copy_conf_files(files)

########NEW FILE########
__FILENAME__ = alerts
import os

from io import StringIO
from ConfigParser import RawConfigParser

from synapse.syncmd import exec_cmd
from synapse.config import config
from synapse.logger import logger
from synapse.scheduler import SynSched
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage, AmqpTask
from synapse import compare


@logger
class AlertsController(object):
    def __init__(self, locator, scheduler, publish_queue):
        self.path = self._configure()
        self.plugins = {}
        self._load_configs()
        self.publish_queue = publish_queue
        self.locator = locator
        self.scheduler = scheduler

        self.alerts = []

    def start(self):
        self._add_alerts()
        self.scheduler.add_job(self._reload, 30)

    def _configure(self):
        config_path = os.path.join(config.paths['config_path'], 'alerts.d')
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        return config_path

    def _reload(self):
        self._load_configs()
        self._add_alerts()

    def _load_configs(self):
        for conf_file in os.listdir(self.path):
            if not conf_file.endswith('.conf'):
                continue
            full_path = os.path.join(self.path, conf_file)
            conf = RawConfigParser()
            conf.read(full_path)
            for section in conf.sections():
                if not section in self.plugins:
                    self.plugins[section] = []
                items = dict(conf.items(section))
                for key, value in items.iteritems():
                    task = {'method': key,
                            'value': value,
                            'scheduled': False}
                    self.plugins[section].append(task)

    def _add_alerts(self):
        for resource, tasks in self.plugins.iteritems():
            instance = self.locator.get_instance(resource)
            for task in tasks:
                if task['scheduled']:
                    continue
                method_ref = getattr(instance, task['method'])
                parsed_params = self._parse_parameters(task['value'])
                interval = int(parsed_params[0])
                compare_method = parsed_params[1]
                threshold = parsed_params[2]
                actionargs = (method_ref, compare_method, threshold)
                self.scheduler.update_job(self.alert, int(interval),
                                          actionargs=actionargs)
                task['scheduled'] = True

    def _parse_parameters(self, parameters):
        return parameters.split(',') + [None] * (4 - len(parameters))

    def alert(self, sensor, compare_method, threshold):
        value = sensor()

        if compare_method is not None and threshold is not None:
            result = getattr(compare, compare_method)(value, threshold)
            alert = {
                'property': sensor.__name__,
                'output': value,
                'level': 'warning',
                'threshold': threshold,
                'compare_method': compare_method,
            }

            if result and not self._alert_sent(alert):
                self._add_alert(alert)
                self._publish(sensor, alert)

            elif not result and self._alert_sent(alert):
                self._remove_alert(alert)
                alert['level'] = 'normal'
                self._publish(sensor, alert)

    def _publish(self, sensor, alert):
        msg = {
            'collection': sensor.__self__.__class__.__resource__,
            'msg_type': 'alert',
            'status': alert
        }

        self.publish_queue.put(AmqpTask(OutgoingMessage(**msg)))

    def _alert_sent(self, alert):
        for al in self.alerts:
            if alert['property'] == al['property']:
                return True
        return False

    def _add_alert(self, alert):
        self.alerts.append(alert)

    def _remove_alert(self, alert):
        for al in self.alerts:
            if alert['property'] == al['property']:
                self.alerts.remove(al)

    def close(self):
        super(AlertsController, self).close()
        self.logger.debug("Shutting down alerts scheduler")
        self.scheduler.shutdown()


########NEW FILE########
__FILENAME__ = amqp
import time
import pika
import socket

from Queue import Empty
from ssl import CERT_REQUIRED
from datetime import datetime, timedelta

from pika.adapters import SelectConnection
from pika.adapters.select_connection import SelectPoller
from pika.credentials import PlainCredentials, ExternalCredentials

from synapse.logger import logger
from synapse.task import IncomingMessage, AmqpTask


@logger
class Amqp(object):
    def __init__(self, conf):
        # RabbitMQ general options
        self.cacertfile = conf['cacertfile']
        self.certfile = conf['certfile']
        self.exchange = conf['exchange']
        self.status_exchange = conf['status_exchange']
        self.fail_if_no_peer_cert = conf['fail_if_no_peer_cert']
        self.heartbeat = conf['heartbeat']
        self.host = conf['host']
        self.keyfile = conf['keyfile']
        self.password = conf['password']
        self.port = conf['port']
        self.ssl_port = conf['ssl_port']
        self.queue = conf['uuid']
        self.retry_delay = conf['retry_delay']
        self.ssl_auth = conf['ssl_auth']
        self.use_ssl = conf['use_ssl']
        self.username = conf['username']
        self.vhost = conf['vhost']
        self.redelivery_timeout = conf['redelivery_timeout']
        self.connection_attempts = conf['connection_attempts']
        self.poller_delay = conf['poller_delay']

        # Connection and channel initialization
        self._connection = None
        self._consume_channel = None
        self._consume_channel_number = None
        self._publish_channel = None
        self._publish_channel_number = None
        self._message_number = 0
        self._deliveries = {}
        self._responses = []

        self._closing = False

        self._processing = False

        # Plain credentials
        credentials = PlainCredentials(self.username, self.password)
        pika_options = {'host': self.host,
                        'port': self.port,
                        'virtual_host': self.vhost,
                        'credentials': credentials,
                        'connection_attempts': self.connection_attempts,
                        'retry_delay': self.retry_delay}

        # SSL options
        if self.use_ssl:
            pika_options['ssl'] = True
            pika_options['port'] = self.ssl_port
            if self.ssl_auth:
                pika_options['credentials'] = ExternalCredentials()
                pika_options['ssl_options'] = {
                    'ca_certs': self.cacertfile,
                    'certfile': self.certfile,
                    'keyfile': self.keyfile,
                    'cert_reqs': CERT_REQUIRED
                }

        if self.heartbeat:
            pika_options['heartbeat_interval'] = self.heartbeat

        self.parameters = pika.ConnectionParameters(**pika_options)

        self.print_config()

    def run(self):
        self.logger.info("[AMQP] Connecting...")
        self._connection = self.connect()
        self._message_number = 0
        self._connection.ioloop.start()

    def connect(self):
        SelectPoller.TIMEOUT = float(self.poller_delay)
        return SelectConnection(self.parameters, self.on_connection_open,
                                stop_ioloop_on_close=False)

    def print_config(self):
        to_print = [("Port", self.port),
                    ("Ssl port", self.ssl_port),
                    ("Queue", self.queue),
                    ("Exchange", self.exchange),
                    ("Heartbeat", self.heartbeat),
                    ("Host", self.host),
                    ("Use ssl", self.use_ssl),
                    ("Ssl auth", self.ssl_auth),
                    ("Vhost", self.vhost),
                    ("Redelivery timeout", self.redelivery_timeout)]
        to_print.sort()
        max_length = len(max([x[0] for x in to_print], key=len))

        self.logger.info("[AMQP-CONFIGURATION]")
        self.logger.info("##################################")
        for info in to_print:
            self.logger.info("{0:>{1}}: {2}".format(info[0], max_length,
                                                     info[1]))
        self.logger.info("##################################")

    def stop(self):
        self.logger.debug("[AMQP] Invoked stop.")
        self._closing = True
        self.close_publish_channel()
        self.close_consume_channel()
        if self._connection:
            self._connection.close()
        self.logger.info("[AMQP] Stopped.")

    def on_connection_open(self, connection):
        self.logger.info("[AMQP] Connected to %s." % self.host)
        self.add_on_connection_close_callback()
        self.open_consume_channel()
        self.open_publish_channel()

    def add_on_connection_close_callback(self):
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._consume_channel = None
        self._publish_channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            self.logger.warning('Connection closed, reopening in 5 seconds')
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):

        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        # Create a new connection
        self._connection = self.connect()

        # There is now a new connection, needs a new ioloop to run
        self._connection.ioloop.start()

    ##########################
    # Consume channel handling
    ##########################
    def open_consume_channel(self):
        self.logger.debug("Opening consume channel.")
        self._connection.channel(self.on_consume_channel_open)

    def on_consume_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        self._consume_channel_number = channel.channel_number
        self.logger.debug("Consume channel #%d successfully opened." %
                          channel.channel_number)
        self._consume_channel = channel
        self.add_on_consume_channel_close_callback()
        self.setup_consume_channel()

    def add_on_consume_channel_close_callback(self):
        self._consume_channel.add_on_close_callback(
            self.on_consume_channel_close)

    def on_consume_channel_close(self, channel, code, text):
        self.logger.debug("Consume channel closed [%d - %s]." % (code, text))
        if code == 320:
            raise socket.error
        else:
            if self._connection:
                self._connection.add_timeout(self.retry_delay,
                                             self.open_consume_channel)

    ############################
    # Publish channel handling #
    ############################
    def open_publish_channel(self):
        self.logger.debug("Opening publish channel.")
        self._connection.channel(self.on_publish_channel_open)

    def close_publish_channel(self):
        self.logger.debug('Closing the publish channel')
        if self._publish_channel and self._publish_channel._state == 2:
            self._publish_channel.close()

    def on_publish_channel_open(self, channel):
        channel.basic_qos(prefetch_count=1)
        self._publish_channel_number = channel.channel_number
        self.logger.debug("Publish channel #%d successfully opened." %
                          channel.channel_number)
        self._publish_channel = channel
        self.add_on_publish_channel_close_callback()
        self.setup_publish_channel()

    def add_on_publish_channel_close_callback(self):
        self._publish_channel.add_on_close_callback(
            self.on_publish_channel_close)

    def on_publish_channel_close(self, channel, code, text):
        self.logger.debug("Publish channel closed [%d - %s]." % (code, text))
        if code == 320:
            raise socket.error
        else:
            if self._connection:
                self._connection.add_timeout(self.retry_delay,
                                             self.open_publish_channel)

    def setup_publish_channel(self):
        raise NotImplementedError()

    def setup_consume_channel(self):
        raise NotImplementedError()

    def close_consume_channel(self):
        self.logger.debug('Closing the consume channel')
        if self._consume_channel and self._consume_channel._state == 2:
            self._consume_channel.close()

class AmqpSynapse(Amqp):
    def __init__(self, conf, pq, tq):
        super(AmqpSynapse, self).__init__(conf)
        self.pq = pq
        self.tq = tq

    ##########################
    # Consuming
    ##########################
    def setup_consume_channel(self):
        self.add_on_cancel_callback()
        self._consumer_tag = self._consume_channel.basic_consume(
            self._on_message, self.queue)

    def add_on_cancel_callback(self):
        self._consume_channel.add_on_cancel_callback(
            self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        self.logger.debug('Consumer was cancelled remotely, shutting down: %r',
                          method_frame)
        self._consume_channel.close()

    def on_cancelok(self, unused_frame):
        self.logger.debug('RabbitMQ acknowledged '
                         'the cancellation of the consumer')
        self.close_consume_channel()


    def stop_consuming(self):
        if self._consume_channel:
            self.logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._consume_channel.basic_cancel(
                self.on_cancelok, self._consumer_tag)

    def acknowledge_message(self, delivery_tag):
        self._consume_channel.basic_ack(delivery_tag=delivery_tag)
        self.logger.debug("[AMQP-ACK] Received message #%s acked" %
                          delivery_tag)

    def _on_message(self, channel, method_frame, header_frame, body):
        self._processing = True
        self.logger.debug("[AMQP-RECEIVE] #%s: %s" %
                          (method_frame.delivery_tag, body))
        try:
            message = IncomingMessage(body)
            headers = vars(header_frame)
            headers.update(vars(method_frame))
            task = AmqpTask(message, headers=headers)
            if not method_frame.redelivered:
                self._responses.append(method_frame.delivery_tag)
                self.tq.put(task)
            else:
                raise ValueError("Message redelivered. Won't process.")
        except ValueError as err:
            self.acknowledge_message(method_frame.delivery_tag)
            self._processing = False
            self.logger.warning(err)

    ##########################
    # Publishing
    ##########################
    def setup_publish_channel(self):
        self.start_publishing()

    def start_publishing(self):
        self._publish_channel.confirm_delivery(
            callback=self.on_confirm_delivery)
        if self._connection:
            self._connection.add_timeout(.1, self._publisher)
            self._connection.add_timeout(1, self._check_redeliveries)

    def on_confirm_delivery(self, tag):
        self.logger.debug("[AMQP-DELIVERED] #%s" % tag.method.delivery_tag)
        if tag.method.delivery_tag in self._deliveries:
            del self._deliveries[tag.method.delivery_tag]

    def _publisher(self):
        """This callback is used to check at regular interval if there's any
        message to be published to RabbitMQ.
        """
        try:
            for i in range(10):
                pt = self.pq.get(False)
                self._handle_publish(pt)
        except Empty:
            pass

        if self._connection:
            self._connection.add_timeout(.1, self._publisher)

    def _check_redeliveries(self):
        # In case we have a message to redeliver, let's wait a few seconds
        # before we actually redeliver them. This is to avoid unwanted
        # redeliveries.
        for key, value in self._deliveries.items():
            delta = datetime.now() - value['ts']
            task = value['task']
            if delta > timedelta(seconds=self.redelivery_timeout):
                self.logger.debug("[AMQP-REPLUBLISHED] #%s: %s" %
                                  (key, task.body))
                self.pq.put(task)
                del self._deliveries[key]
        if self._connection:
            self._connection.add_timeout(.1, self._check_redeliveries)

    def _handle_publish(self, message):
        """This method actually publishes the item to the broker after
        sanitizing it from unwanted informations.
        """
        publish_args = message.get()

        if (self._consume_channel and self._consume_channel._state == 2):
            delivery_tag = message.delivery_tag
            if delivery_tag in self._responses:
                self.acknowledge_message(delivery_tag)
                index = self._responses.index(delivery_tag)
                del self._responses[index]

        if (self._publish_channel and self._publish_channel._state == 2):
            self._publish_channel.basic_publish(**publish_args)

            self._message_number += 1
            self.logger.debug("[AMQP-PUBLISHED] #%s: <%s> %s" %
                             (self._message_number, message.correlation_id,
                              message.body))
        if message.redeliver:
            self._deliveries[self._message_number] = {}
            self._deliveries[self._message_number]["task"] = message
            self._deliveries[self._message_number]["ts"] = datetime.now()

        if publish_args['properties'].correlation_id is not None:
            self._processing = False

########NEW FILE########
__FILENAME__ = bootstrap

import os
import uuid
import time
import pika
import json
import socket
from Queue import Queue

from M2Crypto import RSA, X509, EVP, m2

from synapse.config import config
from synapse.amqp import Amqp
from synapse.logger import logger
from synapse_exceptions import SynapseException


TIMEOUT = 5

log = logger(__name__)


def bootstrap(options):

    bootstrap_opts = get_bootstrap_config()

    if options.force:
        bootstrap_opts['register'] = True
        pem_list = ('cert', 'cacert', 'key', 'csr')
        for pem in pem_list:
            try:
                os.remove(config.paths[pem])
            except (IOError, OSError):
                pass

    if not bootstrap_opts['register']:
        return

    opts = config.rabbitmq

    if not bootstrap_opts['uuid']:
        if not opts['uuid']:
            bootstrap_opts['uuid'] = str(uuid.uuid4())
        else:
            bootstrap_opts['uuid'] = opts['uuid']
    else:
        opts['uuid'] = bootstrap_opts['uuid']

    # Iterate over pem files paths. If at least one of them exists, don't
    # continue and raise an exception.
    exclude = ('csrfile', 'certfile', 'keyfile', 'cacertfile')
    if True in [os.path.exists(pem) for pem in exclude]:
        raise SynapseException("A pem file already exists. "
                               "Use --force with care to regenerate keys/csr.")

    csr = make_x509_request(opts['uuid'],
                            opts['csrfile'],
                            opts['keyfile'])

    response_queue = Queue()
    amqp = AmqpBootstrap(config.rabbitmq,
                         bootstrap_opts,
                         csr,
                         response_queue,
                         timeout=TIMEOUT).run()
    resp = {}

    resp = response_queue.get(True, TIMEOUT)

    response = json.loads(resp)

    if 'cert' in response:
        log.debug("Received certificate: %s" % response['cert'])
        save_cert(response, opts['certfile'], opts['cacertfile'])

        config.bootstrap['register'] = False
        config.bootstrap['uuid'] = bootstrap_opts['uuid']
        config.rabbitmq['username'] = bootstrap_opts['uuid']
        config.rabbitmq['uuid'] = bootstrap_opts['uuid']
        config.rabbitmq['host'] = bootstrap_opts['host']
        config.rabbitmq['vhost'] = bootstrap_opts['vhost']
        config.rabbitmq['use_ssl'] = True
        config.rabbitmq['ssl_auth'] = True

    else:
        raise Exception(response.get('error', 'Unknown error'))


def get_bootstrap_config():
    conf = {
        'register': False,
        'host': 'localhost',
        'vhost': '/',
        'port': '5672',
        'register_exchange': 'register',
        'register_routing_key': '',
        'username': 'guest',
        'password': 'guest',
        'uuid': '',
        }

    conf.update(config.conf.get('bootstrap', {}))

    conf['register'] = config.sanitize_true_false(conf['register'])
    conf['port'] = config.sanitize_int(conf['port'])

    return conf


def generateRSAKey():
    #RSA_F4 = 65637 -> PubExponent
    return RSA.gen_key(2048, m2.RSA_F4)


def makePKey(key):
    pkey = EVP.PKey()
    pkey.assign_rsa(key)
    return pkey


def make_x509_request(uuid, csrpath, keypath):
    rsa = generateRSAKey()
    pkey = makePKey(rsa)
    req = X509.Request()
    req.set_pubkey(pkey)
    name = X509.X509_Name()
    name.CN = uuid
    req.set_subject_name(name)
    req.sign(pkey, 'sha1')
    req.save(csrpath)
    rsa.save_key(keypath, cipher=None)
    os.chmod(keypath, 0640)
    message = {}
    message['uuid'] = name.CN
    with open(csrpath, 'r') as fd:
        message['csr'] = fd.read()
    return message


def save_cert(msg, certpath, cacertpath):
    if not isinstance(msg, dict):
        save_cert.log.error('Bad response format')
    with open(certpath, 'w') as fd:
        cert = msg.get('cert', '')
        fd.write(cert)
    with open(cacertpath, 'w') as fd:
        cacert = msg.get('cacert', '')
        fd.write(cacert)

@logger
class AmqpBootstrap(Amqp):
    def __init__(self, config, options, csr, response_queue, timeout=5):
        self.host = config['host'] = options['host']
        self.port = config['port'] = options['port']
        self.vhost = config['vhost'] = options['vhost']
        self.username = config['username'] = options['username']
        self.password = config['password'] = options['password']
        super(AmqpBootstrap, self).__init__(config)
        self.routing_key = options['register_routing_key']
        self.exchange = options['register_exchange']
        self.csr = csr
        self.timeout = timeout

        self.queue = ''

        self._consumer_tag = None
        self.response_queue = response_queue

    def setup_consume_channel(self):
        self._consume_channel.queue_declare(self.on_queue_declareok,
                                            durable=False,
                                            exclusive=True,
                                            auto_delete=True)

    def on_queue_declareok(self, method_frame):
        self.logger.info("Waiting a response for %d seconds", self.timeout)
        self._connection.add_timeout(self.timeout, self.stop)
        self.queue = method_frame.method.queue
        self.start_consuming()

    def start_consuming(self):
        self.add_on_cancel_callback()
        self._consumer_tag = self._consume_channel.basic_consume(
            self.on_message, self.queue)
        self.publish()

    def add_on_cancel_callback(self):
        self._consume_channel.add_on_cancel_callback(
            self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        self.logger.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        if self._consume_channel:
            self._consume_channel.close()

    def stop_consuming(self):
        self._connection.stop_ioloop_on_close = True
        if self._consume_channel:
            self.logger.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._consume_channel.basic_cancel(self.on_cancelok,
                                               self._consumer_tag)
    def on_cancelok(self, unused_frame):
        self.logger.debug('RabbitMQ acknowledged the cancellation '
                          'of the consumer')
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        self.logger.debug('Closing the channel')
        self._consume_channel.close()

    def on_message(self, channel, basic_deliver, properties, body):
        self.logger.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)
        self.acknowledge_message(basic_deliver.delivery_tag)
        self.response_queue.put(body)
        self.stop_consuming()
        self.stop()

    def acknowledge_message(self, delivery_tag):
        self._consume_channel.basic_ack(delivery_tag)

    def setup_publish_channel(self):
        """ Do nothing here. We want to be sure we're already consuming before
        publishing anything. See self.publish() in start_consuming method.
        """
        pass

    def publish(self):
        self._publish_channel.confirm_delivery(
            callback=self.on_confirm_delivery)

        properties = pika.BasicProperties(reply_to=self.queue,
                                          user_id=self.username)

        self._publish_channel.basic_publish(exchange=self.exchange,
                                            routing_key=self.routing_key,
                                            properties=properties,
                                            body=json.dumps(self.csr))

    def on_confirm_delivery(self, tag):
        self.logger.debug("[AMQP-DELIVERED] #%s" % tag.method.delivery_tag)

########NEW FILE########
__FILENAME__ = compare
def gt(value, threshold):
    return float(value) > float(threshold)

def lt(value, threshold):
    return float(value) < float(threshold)

def eq(value, threshold):
    assert abs(value - threshold) < 0.01

########NEW FILE########
__FILENAME__ = config
'''
Config file can be empty, default values will prevail.
Priority rules: command line > config file > default
Give possibility to change name (e.g. synapse to comodit-agent)
Give possibility to use custom config file
'''
import os
import sys
import uuid
import platform
import ConfigParser

from distutils import sysconfig


synapse_version = "Undefined"

try:
    import synapse.version as version_mod
    if version_mod.VERSION:
        synapse_version = version_mod.VERSION
except (ImportError, AttributeError):
    pass

class Config(object):

    TRUE_ANSWERS = (1, "y", "yes", "True", "true", True, "on")
    SYNAPSE_VERSION = synapse_version

    def __init__(self, name='synapse', windows=False):

        self.paths = {
            'pid': os.path.join('/var/run', name + '.pid'),
            'config_path': os.path.join('/etc', name),
            'conf': os.path.join('/etc', name, name + '.conf'),
            'permissions': os.path.join('/etc', name, 'permissions.conf'),
            'persistence': os.path.join('/var/lib', name, 'persistence'),
            'logger_conf': os.path.join('/etc', name, 'logger.conf'),
            'cacert': os.path.join('/etc', name, 'ssl/certs/cacert.pem'),
            'cert': os.path.join('/etc', name, 'ssl/certs/cert.pem'),
            'csr': os.path.join('/etc', name, 'ssl/csr/csr.pem'),
            'key': os.path.join('/etc', name, 'ssl/private/key.pem'),
            'log': os.path.join('/var/log', name, 'messages.log'),
            'pika_log': os.path.join('/var/log', name, 'pika.log'),
            'plugins': os.path.join('/var/lib', name, 'plugins'),
        }

        if windows:
            prefix = os.path.dirname(sysconfig.PREFIX)
            full_prefix = os.path.join(prefix, 'synapse-agent')
            for key, value in self.paths.iteritems():
                newval = value.replace('/', '\\')[1:]
                self.paths[key] = os.path.join(full_prefix, newval)

        self.conf = self.load_config('conf')

        self.rabbitmq = self.set_rabbitmq_config()
        self.monitor = self.set_monitor_config()
        self.compliance = self.set_compliance_config()
        self.resourcefile = self.set_resourcefile_config()
        self.controller = self.set_controller_config()
        self.log = self.set_logger_config()

        self.sections = [('rabbitmq', self.rabbitmq),
                         ('monitor', self.monitor),
                         ('resourcefile', self.resourcefile),
                         ('controller', self.controller),
                         ('log', self.log)]

    def add_section(self, name, section):
        setattr(self, name, section)
        self.sections.append((name, section))

    def set_rabbitmq_config(self):
        conf = {
            'use_ssl': False,
            'fail_if_no_peer_cert': True,
            'ssl_auth': False,
            'cacertfile': self.paths['cacert'],
            'csrfile': self.paths['csr'],
            'certfile': self.paths['cert'],
            'keyfile': self.paths['key'],
            'host': 'localhost',
            'vhost': '/',
            'port': '5672',
            'ssl_port': '5671',
            'username': 'guest',
            'password': 'guest',
            'uuid': '',
            'exchange': 'amq.fanout',
            'publish_exchange': 'inbox',
            'publish_routing_key': '',
            'status_exchange': 'inbox',
            'reply_exchange': 'inbox',
            'status_routing_key': '',
            'compliance_routing_key': '',
            'connection_attempts': 5000,
            'retry_delay': 5,
            'heartbeat': '30',
            'redelivery_timeout': 10,
            'poller_delay': 1
        }

        conf.update(self.conf.get('rabbitmq', {}))

        conf['use_ssl'] = self.sanitize_true_false(conf['use_ssl'])
        conf['fail_if_no_peer_cert'] = self.sanitize_true_false(
            conf['fail_if_no_peer_cert'])
        conf['ssl_auth'] = self.sanitize_true_false(conf['ssl_auth'])
        conf['port'] = self.sanitize_int(conf['port'])
        conf['ssl_port'] = self.sanitize_int(conf['ssl_port'])
        conf['connection_attempts'] = self.sanitize_int(
            conf['connection_attempts'])
        conf['retry_delay'] = self.sanitize_int(conf['retry_delay'])
        conf['heartbeat'] = self.sanitize_int(conf['heartbeat'])
        conf['redelivery_timeout'] = self.sanitize_int(
            conf['redelivery_timeout'])
        if not conf['uuid']:
            conf['uuid'] = str(uuid.uuid4())

        return conf

    def set_monitor_config(self):

        conf = {
            'enable_monitoring': True,
            'default_interval': '30',
            'publish_status': False,
        }

        conf.update(self.conf.get('monitor', {}))

        conf['default_interval'] = self.sanitize_int(conf['default_interval'])
        conf['publish_status'] = self.sanitize_true_false(
            conf['publish_status'])

        return conf

    def set_compliance_config(self):

        conf = {
            'enable_compliance': True,
            'default_interval': '30',
            'alert_interval': '3600',
        }

        conf.update(self.conf.get('compliance', {}))

        conf['default_interval'] = self.sanitize_int(conf['default_interval'])
        conf['alert_interval'] = self.sanitize_int(conf['alert_interval'])

        return conf

    def set_resourcefile_config(self):

        conf = {
            'url': 'http://localhost/setup.json',
            'path': '/tmp/setup.json',
            'timeout': 10
        }

        conf.update(self.conf.get('resourcefile', {}))

        conf['timeout'] = self.sanitize_int(conf['timeout'])

        return conf

    def set_controller_config(self):
        conf = {
            'ignored_resources': '',
            'persistence_path': self.paths['persistence'],
            'custom_plugins': self.paths['plugins'],
            'permissions_path': self.paths['permissions'],
            'distribution_name': self.get_platform()[0],
            'distribution_version': self.get_platform()[1],
            }

        #TODO check for mandatory config files like permissions

        conf.update(self.conf.get('controller', {}))

        return conf

    def set_logger_config(self):
        conf = {
            'level': 'INFO',
            'logger_conf': self.paths['logger_conf'],
            'path': self.paths['log'],
            'pika_log_path': self.paths['pika_log']
            }

        conf.update(self.conf.get('log', {}))

        return conf

    def load_config(self, name):
        fp = self.paths[name]

        conf = {}
        config = ConfigParser.SafeConfigParser()
        config.read(fp)
        for section in config.sections():
            conf[section] = dict(config.items(section))

        return conf

    def get_platform(self):
        dist = ('linux', '0')
        if platform.system().lower() == 'linux':
            dist = platform.linux_distribution()
        elif platform.system().lower() == 'windows':
            dist = ('windows', platform.win32_ver()[0])
        return (self._format_string(dist[0]), self._format_string(dist[1]))

    def _format_string(self, s):
        '''This method replaces dots and spaces with underscores.'''
        _s = '_'.join([x for x in s.lower().split(' ')])
        return ''.join([x for x in _s.replace('.', '_')])

    def update_conf(self, conf, kwargs):
        for key in kwargs:
            conf[key] = kwargs[key]

    def sanitize_true_false(self, option):
        if isinstance(option, basestring):
            return option.lower() in self.TRUE_ANSWERS
        return option

    def sanitize_int(self, option):
        try:
            return int(option)
        except ValueError:
            raise Exception("'%s' must be an integer" % option)

    def dump_config_file(self, to_file=True, *args):
        filecontent = ''

        if to_file:
            msg = "# This file is auto-generated. Edit at your own risks.\n"
            filecontent = '#' * len(msg) + '\n'
            filecontent += msg
            filecontent += '#' * len(msg) + '\n'

        filecontent += '\n'
        for section in self.sections:
            filecontent += "[%s]\n" % section[0]
            for option, value in section[1].iteritems():
                filecontent += "{0} = {1}\n".format(option, value)
            filecontent += '\n'

        if to_file:
            with open(self.paths['conf'], 'w') as fd:
                fd.write(filecontent)

        return filecontent


windows = platform.system().lower() == 'windows'
try:
    config = Config(name='synapse-agent', windows=windows)
except Exception as err:
    sys.exit('Error in config module: %s' % err)

########NEW FILE########
__FILENAME__ = controller
import json
import traceback

from threading import Thread
from synapse.synapse_exceptions import ResourceException

from synapse.resource_locator import ResourceLocator
from synapse.config import config
from synapse.logger import logger
from synapse.scheduler import SynSched
from synapse.alerts import AlertsController
from synapse.task import IncomingMessage, OutgoingMessage, AmqpTask
from synapse import compare

@logger
class Controller(Thread):
    '''The controller is the link between the transport layer and the
    resources layer. Basically, its job is to load resources modules and
    objects and to call their generic "process" method.
    '''

    def __init__(self, tq=None, pq=None):

        self.logger.debug("Initializing the controller...")
        Thread.__init__(self, name="CONTROLLER")

        self.tq = tq
        self.pq = pq

        self.scheduler = SynSched()
        self.locator = ResourceLocator(pq)
        self.alerter = AlertsController(self.locator, self.scheduler, pq)
        self.logger.debug("Controller successfully initialized.")

    def start_scheduler(self):
        # Start the scheduler thread
        self.scheduler.start()
        self.alerter.start()

        # Prepopulate tasks from config file
        if config.monitor['enable_monitoring']:
            self._enable_monitoring()
        if config.compliance['enable_compliance']:
            self._enable_compliance()

    def _get_monitor_interval(self, resource):
        try:
            default_interval = config.monitor['default_interval']
            return int(config.monitor.get(resource, default_interval))
        except ValueError:
            return default_interval

    def _get_compliance_interval(self, resource):
        try:
            default_interval = config.compliance['default_interval']
            return int(config.compliance.get(resource, default_interval))
        except ValueError:
            return default_interval

    def _enable_monitoring(self):
        resources = self.locator.get_instance()
        for resource in resources.values():
            if not len(resource.states):
                continue
            interval = self._get_monitor_interval(resource.__resource__)
            self.scheduler.add_job(resource.monitor_states, interval)

    def _enable_compliance(self):
        resources = self.locator.get_instance()
        for resource in resources.values():
            if not len(resource.states):
                continue
            interval = self._get_compliance_interval(resource.__resource__)
            self.scheduler.add_job(resource.check_compliance, interval)

    def stop_scheduler(self):
        # Shutdown the scheduler/monitor
        self.logger.debug("Shutting down global scheduler...")
        if self.scheduler.isAlive():
            self.scheduler.shutdown()
            self.scheduler.join()
        self.logger.debug("Scheduler stopped.")

    def close(self):

        # Stop this thread by putting a stop message in the blocking queue get
        self.tq.put("stop")

       # Close properly each resource
        try:
            for resource in self.locator.get_instance().itervalues():
                resource.close()
        except ResourceException, e:
            self.logger.debug(str(e))

        self.stop_scheduler()

    def run(self):
        """Implementation of the Threading run method. This methods waits on
        the tasks queue to get messages from the transport layer and then calls
        the call_method. It then waits for a response to put into the publish
        queue before waiting for a new task to come.
        """

        self.logger.debug("Controller started.")

        response = {}
        while True:
            task = self.tq.get()
            if task == "stop":
                break
            try:
                response = self.call_method(task.sender, task.body)

            except ResourceException as err:
                self.logger.error("%s" % err)

                if response.get('status'):
                    del response['status']
                response['error'] = '%s' % err

            except Exception:
                self.logger.debug('{0}'.format(traceback.format_exc()))

            finally:
                self.pq.put(AmqpTask(response, headers=task.headers))

    def call_method(self, user, body):
        """Reads the collection the message needs to reach and then calls the
        process method of that collection. It returns the response built by the
        collection.
        """
        response = {}

        # Check if the message body contains filters.
        filters = body.get('filters')

        if filters:
            if not self._check_filters(filters):
                raise ResourceException("Filters did not match")

        try:
            # Get a reference to the corresponding resource object.
            instance = self.locator.get_instance(body['collection'])

            # Call the resource's generic process method
            response = instance.process(body)

        except ResourceException, err:
            self.logger.debug("Resource exception: %s" % err)
            response['error'] = '%s' % err

        except Exception, e:
            raise ResourceException("There's a problem with your %s plugin: %s"
                                    % (body['collection'], e))

        # Return the response
        return response

    def _check_filters(self, filters):
        self.logger.debug("Checking filters")
        match = False

        for key, value in filters.iteritems():
            try:
                module = 'synapse.filters.%s' % key
                m = __import__(module)
                parts = module.split('.')
                for comp in parts[1:]:
                    m = getattr(m, comp)

                match = m.check(value)
                if match == False:
                    break
            except ImportError:
                pass

        self.logger.debug("Filters match: %s" % match)
        return match

########NEW FILE########
__FILENAME__ = daemon
# Public Domain
#
# Copyright 2007, 2009 Sander Marechal <s.marechal@jejik.com>
# Copyright 2010, 2011 Jack Kaliko <efrim@azylum.org>
#
# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

import atexit
import os
import sys
import time
from signal import signal, SIGTERM


class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    version = "0.4"

    def __init__(self, pidfile,
            stdin='/dev/null',
            stdout='/dev/null',
            stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.umask = 0

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" %
                             (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        self.umask = os.umask(0)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" %
                             (e.errno, e.strerror))
            sys.exit(1)

        self.write_pid()
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.shutdown)
        self.signal_management()

    def write_pid(self):
        # write pidfile
        if not self.pidfile:
            return
        pid = str(os.getpid())
        try:
            os.umask(self.umask)
            file(self.pidfile, 'w').write('%s\n' % pid)
        except Exception, wpid_err:
            sys.stderr.write(u'Error trying to write pid file: %s\n' %
                             wpid_err)
            sys.exit(1)
        os.umask(0)
        atexit.register(self.delpid)

    def signal_management(self):
        # Declare signal handlers
        signal(SIGTERM, self.exit_handler)

    def exit_handler(self, signum, frame):
        sys.exit(1)

    def delpid(self):
        try:
            os.unlink(self.pidfile)
        except OSError as err:
            message = 'Error trying to remove PID file: %s\n'
            sys.stderr.write(message % err)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def foreground(self):
        """
        Foreground/debug mode
        """
        self.write_pid()
        atexit.register(self.shutdown)
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Is the Daemon running?\n"
            sys.stderr.write(message % self.pidfile)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            os.kill(pid, SIGTERM)
            time.sleep(0.1)
        except OSError, err:
            if err.errno == 3:
                if os.path.exists(self.pidfile):
                    message = "Daemon's not running? removing pid file %s.\n"
                    sys.stderr.write(message % self.pidfile)
                    os.remove(self.pidfile)
            else:
                sys.stderr.write(err.strerror)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def shutdown(self):
        """
        You should override this method when you subclass Daemon. It will be
        called when the process is being stopped.
        Pay attention:
        Daemon() uses atexit to call Daemon().shutdown(), as a consequence
        shutdown and any other functions registered via this module are not
        called when the program is killed by an un-handled/unknown signal.
        This is the reason of Daemon().signal_management() existence.
        """

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be
        called after the process has been daemonized by start() or restart().
        """

########NEW FILE########
__FILENAME__ = dispatcher
import sys
import time
import signal
import socket
import traceback

from Queue import Queue
from pika.exceptions import AMQPConnectionError

from synapse.amqp import AmqpSynapse
from synapse.config import config
from synapse.controller import Controller
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class Dispatcher(object):
    """This module dispatches commands incoming from the command line to
    specific transports. It is also responsible for starting threads and
    catching signals like SIGINT and SIGTERM.
    """

    def __init__(self, transport):

        self.transport = transport

        # Handle signals
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        # Threads instances variables
        self.controller = None
        self.amqpsynapse = None

        self.resourcefile = None

        # These queues will be shared between the controller and the
        # transport and are used for incoming tasks and responses
        self.pq = Queue()
        self.tq = Queue()

    def stop(self, signum, frame):
        """This method handles SIGINT and SIGTERM signals. """

        self.logger.info("Stopping due to signal #%d" % signum)
        raise KeyboardInterrupt

    def stop_synapse(self):
        """Closes all threads and exits properly.
        """
        if self.resourcefile:
            self.resourcefile.done = True


        # Close the controller and wait for it to quit
        if self.controller:
            if self.controller.isAlive():
                self.controller.close()
                self.controller.join()
                self.logger.debug("Controller thread stopped")

        self.logger.info("Successfully stopped.")

    def dispatch(self):
        """This method actually dispatches to specific transport methods
        according to command line parameters.
        """

        self.logger.info('Starting on %s transport' %
                         self.transport.capitalize())
        transports = {
                'amqp': self.start_amqp,
                'http': self.start_resourcefile,
                'file': self.start_resourcefile,
        }
        try:
            transports[self.transport]()
        except KeyError as err:
            self.logger.error("Transport unknown. [%s]" % err)
            self.stop_synapse()
            sys.exit()

    def start_amqp(self):
        """ Starts all needed threads: controller and AMQP transport IOLOOP.
        """

        try:
            self.amqpsynapse = AmqpSynapse(config.rabbitmq,
                                           pq=self.pq, tq=self.tq)
            self.controller = Controller(self.tq, self.pq)
            self.controller.start()
            self.controller.start_scheduler()
            self.amqpsynapse.run()

        except (AMQPConnectionError, KeyboardInterrupt):
            pass
        except ResourceException as err:
            self.logger.error(str(err))
        except Exception as err:
            self.logger.error(err)
        finally:
            self.amqpsynapse.stop()
            self.stop_synapse()

    def start_resourcefile(self):
        """This method handles the --uri file and --uri http commands.
        """

        from synapse.resourcefile import ResourceFile
        try:
            self.resourcefile = ResourceFile(self.transport)
            self.resourcefile.fetch()
        except KeyboardInterrupt:
            self.stop_synapse()

########NEW FILE########
__FILENAME__ = hostnames
import socket
import re


def check(hostnames):

    match = False
    actual_hostname = socket.gethostbyaddr(socket.gethostname())[0]

    for hostname in hostnames:
        newhostname = hostname.replace(".", "\.")
        newhostname = newhostname.replace("*", ".*")
        regex = re.compile(newhostname)
        if re.match(regex, actual_hostname):
            match = True
            break

    return match

########NEW FILE########
__FILENAME__ = ipaddresses
import re
from netifaces import interfaces, ifaddresses, AF_INET


def check(ipaddresses):
    match = False
    ips = {}
    for ifaceName in interfaces():
        addresses = [i['addr']
                     for i in ifaddresses(ifaceName).setdefault(AF_INET,
                                                [{'addr':'No IP addr'}])]
        if len(addresses):
            ips[ifaceName] = addresses[0]
    for ip in ipaddresses:
        newip = ip.replace(".", "\.")
        newip = newip.replace("*", ".*")
        regex = re.compile(newip)
        for value in ips.values():
            if re.match(regex, value):
                return True

    return match

########NEW FILE########
__FILENAME__ = macaddresses
import os


def check(mac_addresses):
    ifconfig = os.popen('ifconfig').readlines()
    found = False
    for line in ifconfig:
        for ma in mac_addresses:
            if ma in line:
                found = True
                break
    return found

########NEW FILE########
__FILENAME__ = platforms
import platform


def check(platforms):
    return platform.system() in platforms

########NEW FILE########
__FILENAME__ = uuids
from synapse.config import config


def check(uuids):
    return config.rabbitmq['uuid'] in uuids

########NEW FILE########
__FILENAME__ = logger
import copy
import logging
import inspect
import logging.config

from synapse.config import config

LEVELS = ('FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'CRITICAL')


def logger(obj):
    if inspect.isclass(obj):
        setattr(obj,
                'logger',
                logging.getLogger('synapse.{0}'.format(obj.__name__)))
        return obj
    else:
        try:
            modulename = obj.split('.')[-1]
            return logging.getLogger('synapse.{0}'.format(modulename))
        except (AttributeError, IndexError):
            return logging.getLogger('synapse')


def setup_logging(logconf):
    # Get log level from config file
    logging.config.fileConfig(logconf['logger_conf'])


class SynapseFileHandler(logging.FileHandler):
    def __init__(self, mode):
        path = config.log['path']
        logging.FileHandler.__init__(self, path, mode)


class PikaFileHandler(logging.FileHandler):
    def __init__(self, mode):
        path = config.log['pika_log_path']
        logging.FileHandler.__init__(self, path, mode)


class ConsoleUnixColoredHandler(logging.StreamHandler):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    COLORS = {
        'FATAL': RED,
        'CRITICAL': RED,
        'ERROR': RED,
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': CYAN,
    }

    def emit(self, r):
        # Need to make a actual copy of the record to prevent altering
        # the message for other loggers.
        record = copy.copy(r)
        levelname = record.levelname

        # Configures the current colors to use.
        color = self.COLORS[record.levelname]

        # Colories the levelname of each log message
        record.levelname = self._get_fg_color(color) + str(levelname) + \
            self._reset()
        logging.StreamHandler.emit(self, record)

    def _get_fg_color(self, color):
        return '\x1B[1;3%sm' % color

    def _reset(self):
        return '\x1B[1;%sm' % self.BLACK

########NEW FILE########
__FILENAME__ = main
import sys
import logging
import optparse
import urlparse
import traceback
from synapse.config import config
from synapse import logger

from synapse.dispatcher import Dispatcher
from synapse.daemon import Daemon

synapse_version = "Undefined"

try:
    import synapse.version as version_mod
    if version_mod.VERSION:
        synapse_version = version_mod.VERSION
except (ImportError, AttributeError):
    pass


def init_parser():

    parser = optparse.OptionParser(version=synapse_version)

    parser.add_option("--daemonize", "-d", action="store_true",
                      dest="daemonize", default=False,
                      help="Starts in daemon")

    parser.add_option("--uri", type="string", dest="uri", default='amqp',
                      help="Specify where to get jobs from.")

    parser.add_option("--vhost", action="store",
                      dest="vhost", default=None,
                      help="Overrides config file's vhost option")

    parser.add_option("--uuid", action="store",
                      dest="uuid", default=None,
                      help="Overrides config file's queue option")

    parser.add_option("--disable", action="store",
                      dest="disable", default=None,
                      help="Comma separated list of resources to disable")

    parser.add_option("--force", action="store_true",
                      dest="force", default=None,
                      help="Force the ssl dance to take place by "
                            "deleting .pem files. Use with care !")

    parser.add_option("--timeout", action="store", type='int',
                      dest="timeout", default=None,
                      help='Will try to access http file for this number of '
                           'seconds')

    parser.add_option("-v", action="store_true",
                      dest="verbose", default=None,
                      help="Set loglevel to debug.")

    parser.add_option("--trace", action='store_true',
                      dest='trace', default=False,
                      help="Show traceback")

    parser.add_option("--print-config", action="store_true",
                      dest="print_config", default=False,
                      help="Prints the configuration on console")

    return parser


class Main(object):
    def __init__(self, parse_commandline=True):
        # Initialize the parser
        self.parser = init_parser()

        # Update config with command line options
        logger.setup_logging(config.log)
        self.logger = logging.getLogger('synapse')
        self.transport = None
        self.daemon = SynapseDaemon(config.paths['pid'])

        try:
            cli_args = sys.argv[1:] if parse_commandline else []
            options, args = self.parser.parse_args(cli_args)
            loglevel = config.log['level']
            if options.verbose:
                loglevel = 'DEBUG'
            self.setup_logger(loglevel.upper())
            self.parse_commandline(options, args)

            # Daemonize process ?
            if options.daemonize:
                self.daemon.set_transport(self.transport)
                self.daemon.start()
            else:
                Dispatcher(self.transport).dispatch()

        except Exception as err:
            self.logger.error(err)
            if options.trace:
                self.logger.error('{0}'.format(traceback.format_exc()))
            sys.exit(-1)

    def parse_commandline(self, options, args):

        try:
            from synapse import bootstrap
            config.add_section('bootstrap', bootstrap.get_bootstrap_config())
        except ImportError:
            pass

        if options.print_config:
            print config.dump_config_file(to_file=False)
            sys.exit()

        # Handle Daemon
        if len(args):
            if args[0].lower() == 'stop':
                self.daemon.stop()
                sys.exit()
            elif args[0].lower() == 'status':
                is_running = self.daemon.status()
                if is_running:
                    self.logger.info('Running !')
                else:
                    self.logger.info('Not Running !')
                sys.exit()

        if self.daemon.is_running_in_bg():
            self.logger.error("Daemon already running in background. "
                              "Exiting now.")
            sys.exit(-1)

        self.setup_transport(options)

        try:
            register = config.bootstrap.get('register', False)
            if self.transport == 'amqp' and register:
                bootstrap.bootstrap(options)
                config.dump_config_file()

        except Exception as err:
            self.logger.warning("Error while bootstraping: %s" % err)
            self.logger.warning("Trying to connect with default settings")

        self.setup_controller(options)

        return options, args

    def setup_transport(self, options):
        # Start parsing other options and arguments
        parsed_uri = urlparse.urlparse(options.uri)
        transport = parsed_uri.scheme or parsed_uri.path

        # Override RABBITMQ options
        if transport == 'amqp' or 'start':
            if options.uuid:
                config.rabbitmq['uuid'] = options.uuid
            if parsed_uri.hostname:
                config.rabbitmq['host'] = parsed_uri.hostname
            if parsed_uri.port:
                config.rabbitmq['port'] = parsed_uri.port
            if parsed_uri.username:
                config.rabbitmq['username'] = parsed_uri.username
            if parsed_uri.password:
                config.rabbitmq['password'] = parsed_uri.password
            if parsed_uri.scheme and parsed_uri.path:
                config.rabbitmq['vhost'] = parsed_uri.path[1:]

        # Override RESOURCEFILE options
        if transport == 'http':
            if options.timeout:
                config.resourcefile['timeout'] = options.timeout
            config.resourcefile['url'] = options.uri

        if transport == 'file':
            config.resourcefile['path'] = parsed_uri.path

        self.transport = transport

    def setup_controller(self, options):
        # Override CONTROLLER options
        if options.disable:
            config.controller['ignored_resources'] = options.disable

    def setup_logger(self, loglevel):
        # Override LOGGER options
        if loglevel in logger.LEVELS:
            handlers = logging.getLogger('synapse').handlers
            for handler in handlers:
                handler.setLevel(getattr(logging, loglevel))


class SynapseDaemon(Daemon):
    def run(self):
        Dispatcher(self.transport).dispatch()

    def set_transport(self, transport):
        self.transport = transport

    def status(self):
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
        except ValueError:
            return False

        try:
            with open("/proc/%d/status" % pid, 'r'):
                return True
        except (IOError, TypeError):
            return False

    def is_running_in_bg(self):
        return self.status()

########NEW FILE########
__FILENAME__ = permissions
import re

from synapse.logger import logger


perm_mapping = {"C": "create",
                "R": "read",
                "U": "update",
                "D": "delete",
                "-": ""}

log = logger(__name__)


def get(permission_file_path):
    """Reads the permissions file line by line and process them.
    Returns an array of permissions array.
    """

    permissions = []
    with open(permission_file_path, 'r') as fd:
        for index, line in enumerate(fd):
            # If line is blank, dont bother
            if not line.strip():
                continue
            try:
                permissions.append(process(line))
            except re.error:
                log.critical("There's a problem with your permissions config "
                             "file at line %d" % ((index + 1),))
                raise SystemExit

    if not len(permissions):
        log.critical("Your permissions config file is empty")
        raise SystemExit

    return permissions


def process(dirty_line):
    """This method will process lines in the permissions config file,
    build an array of permissions from it then returns it.
    """

    perm = []

    # Let's be sure we can split the line in 4 parts
    reg = re.compile('''
            \s*             # There can be whitespaces at beginning
            (\w*|\*)        # Match any alphanum or a * for username
            \s+             # Need a whitspace separator
            (\w*|\*)        # Match any alphanum or a * for collection
            \s+             # Need a whitspace separator
            \"?(.*?)\"?     # res_id can be surrounded by double quotes
            \s+             # Need a whitspace separator
            ([CRUD]{1,4}|-) # Accept any combination of CRUD or dash
            \s*             # There can be whitespaces at the end
            $               # No more than 4 groups
            ''', re.VERBOSE)

    # Try to match !
    result = reg.match(dirty_line)

    # If no match, raise REGEXP Error !
    if result is None:
        raise re.error

    # user
    perm.append(re.compile(_sanitize(result.group(1))))

    # collection
    perm.append(re.compile(_sanitize(result.group(2))))

    # res_id
    perm.append(re.compile(_sanitize(result.group(3))))

    # crud-
    perm.append([perm_mapping[p] for p in result.group(4)])

    # if user can read, user can ping
    # add it to the action list
    if 'R' in result.group(4):
        perm[3].append('ping')

    return perm


def _sanitize(item):
    newitem = item.replace('.', '\.')
    newitem = newitem.replace('*', '.*')
    return newitem


def check(permissions, user, collection, res_id):
    for perm in permissions:
        user_match = perm[0].match(user)
        collection_match = perm[1].match(collection)
        res_id_match = perm[2].match(res_id)

        # If we have a match, return authorized methods
        if (user_match and collection_match and res_id_match):
            return perm[3]

    return []

########NEW FILE########
__FILENAME__ = register_plugin
import sys
import imp
import os
import ConfigParser
import StringIO
import logging

from synapse.config import config


registry = {}
log = logging.getLogger('synapse.register_plugin')


def register(mapping, cls):
    name = cls.__resource__
    if not name in registry:
        path = os.path.dirname(
                os.path.abspath(sys.modules[cls.__module__].__file__))
        if not name in registry:
            mod = get_module(mapping, path)
            registry[name] = cls(mod)


def get_module(os_mapping, dirpath):
    mapping_config = ConfigParser.RawConfigParser()
    mapping_config.readfp(StringIO.StringIO(os_mapping))
    opts = config.controller
    dist = opts['distribution_name']
    ver = opts['distribution_version']
    combinations = ((dist, ver), (dist, 'default'), ('default', 'default'))

    mod_name = None
    for comb in combinations:
        mod_name = get_module_name(mapping_config, comb[0], comb[1])
        if mod_name:
            break

    if mod_name != 'default' and mod_name is not None:
        fp, path, desc = imp.find_module(mod_name, [dirpath])
        return imp.load_module(mod_name, fp, path, desc)
    elif mod_name == 'default':
        return None


def get_module_name(conf, section='default', option='default'):
    plugin_name = None
    try:
        plugin_name = conf.get(section, option)
        if plugin_name == 'None':
            plugin_name = 'default'
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        pass
    return plugin_name

########NEW FILE########
__FILENAME__ = resourcefile
import time
import json
import urllib2

from pprint import pformat

from synapse.config import config
from synapse.controller import Controller
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class ResourceFile:
    def __init__(self, transport):
        opts = config.resourcefile
        self.transport = transport
        self.url = opts['url']
        self.path = opts['path']
        self.timeout = opts['timeout']
        self.done = False

    def fetch(self):
        counter = 0
        while counter <= self.timeout and not self.done:
            try:
                self.dispatch(self.transport)
                self.done = True
                self.logger.info("Done processing.")
            except urllib2.HTTPError, err:
                #code = err.code
                self.logger.error("File not found: %s" % err)
            except IOError, err:
                # Connection error (socket)
                self.logger.error("IOError: %s" % err)
            except Exception, err:
                self.logger.error("SynapseException: %s" % err)
                self.done = True
            finally:
                if not self.done:
                    self.logger.info('Retrying in 2 seconds. '
                            '{0} seconds left'.format(self.timeout - counter))
                    time.sleep(2)
                    counter += 2

    def dispatch(self, transport):
        tasks = {'http': self._get_http, 'file': self._get_fs}[transport]()

        for task in tasks:
            response = ''
            try:
                self.logger.info("Sending task:\n{0}\n".format(pformat(task)))
                response = Controller().call_method('', task, check_perm=False)
            except ResourceException, error:
                response = error

            self.logger.info("Response:\n{0}\n".format(pformat(response)))

        return True

    def _get_http(self):
        self.logger.info('Trying to open url %s' % self.url)
        webfile = urllib2.urlopen(self.url)
        try:
            tasks = json.loads(webfile.read())
            self.logger.info('Found %d task(s), processing...' % len(tasks))
        except ValueError, err:
            raise Exception('Error while loading json: {0}'.format(err))
        finally:
            webfile.close()
        return tasks

    def _get_fs(self):
        self.logger.info('Trying to open file %s' % self.path)
        with open(self.path, 'r') as fd:
            try:
                tasks = json.load(fd)
                self.logger.info('Found %d task(s)' % len(tasks))
            except ValueError, err:
                raise Exception('Error while loading json: {0}'.format(err))
        return tasks or []

########NEW FILE########
__FILENAME__ = directories
import getpass
from datetime import datetime

from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class DirectoriesController(ResourcesController):

    __resource__ = "directories"

    def read(self, res_id=None, attributes={}):
        status = {}
        self.check_mandatory(res_id)

        present = self.module.is_dir(res_id)
        status['present'] = present
        if present:
            status['owner'] = self.module.owner(res_id)
            status['group'] = self.module.group(res_id)
            status['mode'] = self.module.mode(res_id)
            status['mod_time'] = self.module.mod_time(res_id)
            status['c_time'] = self.module.c_time(res_id)

        return status

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        owner = self._get_owner(res_id, attributes)
        group = self._get_group(res_id, attributes)
        mode = self._get_mode(res_id, attributes)

        state = {
            'owner': owner,
            'group': group,
            'mode': mode,
            'mod_time': str(datetime.now()),
            'c_time': str(datetime.now()),
            'present': True
        }
        self.save_state(res_id, state, monitor=monitor)

        self.module.create_folders(res_id)

        # Update meta of given file
        self.module.update_meta(res_id, owner, group, mode)

        return self.read(res_id=res_id)

    def update(self, res_id=None, attributes={}):
        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)

        previous_state = self.read(res_id=res_id)
        self.module.delete_folder(res_id)

        if not self.module.exists(res_id):
            previous_state['present'] = False
            self.response = previous_state

        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        # First, compare the present flag. If it differs, no need to go
        # further, there's a compliance issue.
        # Check the next path state
        if persisted_state.get("present") != current_state.get("present"):
            compliant = False
            return compliant

        # Secondly, compare path attributes
        for attr in ("name", "owner", "group", "mode"):
            if persisted_state.get(attr) != current_state.get(attr):
                compliant = False
                break

        return compliant

    def _get_owner(self, path, attributes):
        # Default, get the current user. getpass is portable Unix/Windows
        owner = getpass.getuser()

        # If path exists, get path owner
        if self.module.exists(path):
            owner = self.module.owner(path)
        # Overwrite if owner name is provided
        if attributes.get('owner'):
            owner = attributes['owner']

        return owner

    def _get_group(self, path, attributes):
        # Default, get the current user's group.
        # getpass is portable Unix/Windows
        group = getpass.getuser()

        # If path exists, get path group
        if self.module.exists(path):
            group = self.module.group(path)
        # Overwrite if group name is provided
        if attributes.get('group'):
            group = attributes['group']

        return group

    def _get_mode(self, path, attributes):
        # Default, get default mode according to current umask
        mode = self.module.get_default_mode(path)

        # If path exists, get current mode
        if self.module.exists(path):
            mode = self.module.mode(path)

        # If mode is provided, return its octal value as string
        if attributes.get('mode'):
            try:
                mode = oct(int(attributes['mode'], 8))
            except ValueError as err:
                raise ResourceException("Error with path mode (%s)" % err)

        return mode

########NEW FILE########
__FILENAME__ = unix-directories
import datetime
import grp
import os
import pwd
import shutil

from synapse.synapse_exceptions import ResourceException


def exists(path):
    try:
        return os.path.exists(path)
    except IOError:
        return False


def is_dir(path):
    try:
        return os.path.isdir(path)
    except IOError:
        return False


def list_dir(path):
    if not os.path.exists(path):
        raise ResourceException("Directory not found, sorry !")

    return os.listdir(path)


def create_folders(path):
    try:
        # Recursive mkdirs if dir path is not complete
        os.makedirs(path)
    except OSError:
        #Already exists, no prob !
        pass
    except Exception as err:
        # Another problem
        raise ResourceException('Failed when creating folders: %s' % err)


def update_meta(path, owner, group, filemode):
    if not os.path.exists(path):
        raise ResourceException('This path does not exist.')

    ownerid = get_owner_id(owner)
    groupid = get_group_id(group)
    octfilemode = int(filemode, 8)

    try:
        os.chmod(path, octfilemode)
        os.chown(path, ownerid, groupid)
    except ValueError as err:
        raise ResourceException(err)


def delete_folder(path):
    if not os.path.exists(path):
        raise ResourceException("Directory doesn't exist")
    try:
        shutil.rmtree(path)
    except OSError as err:
        raise ResourceException("Exception when removing the folder: %s" % err)


def mod_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getmtime(path)))


def c_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getctime(path)))


def owner(path):
    if not os.path.exists(path):
        raise ResourceException('Directory does not exist.')

    si = os.stat(path)
    uid = si.st_uid
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError as err:
        raise ResourceException(err)


def get_owner_id(name):
    try:
        return pwd.getpwnam(name).pw_uid
    except KeyError as err:
        raise ResourceException(err)


def group(path):
    if not os.path.exists(path):
        raise ResourceException('Directory does not exist.')

    si = os.stat(path)
    gid = si.st_gid
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError as err:
        raise ResourceException(err)


def get_group_id(name):
    try:
        return grp.getgrnam(name).gr_gid
    except KeyError as err:
        raise ResourceException(err)


def mode(path):
    if not os.path.exists(path):
        raise ResourceException('Directory does not exist.')

    si = os.stat(path)
    _mode = "%o" % si.st_mode
    return _mode[-4:]


def get_default_mode(path):
    current_umask = os.umask(0)
    os.umask(current_umask)
    _mode = 0644
    if os.path.isdir(path):
        _mode = 0777 ^ current_umask
    return oct(_mode)

########NEW FILE########
__FILENAME__ = executables
from synapse.syncmd import exec_cmd
from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class ExecutablesController(ResourcesController):

    __resource__ = "executables"

    def read(self, res_id=None, attributes=None):
        pass

    def create(self, res_id=None, attributes=None):
        pass

    def update(self, res_id=None, attributes=None):
        if not res_id:
            raise ResourceException('Please provide a command')

        #status = self.module.exec_threaded_cmd(res_id)
        self.logger.info("Executing: %s" % res_id)
        status = exec_cmd(res_id)
        if status['returncode'] != 0:
            error = "Status code %s: [%s]" %(status["returncode"],
                                             status["stderr"])
            raise ResourceException(error)
        self.logger.info("Done executing '%s'" % res_id)

        return status

    def delete(self, res_id=None, attributes=None):
        pass

########NEW FILE########
__FILENAME__ = files
import base64
import getpass
import urllib2
from datetime import datetime
from urllib2 import URLError

from synapse.resources.resources import ResourcesController
from synapse.logger import logger
from synapse.synapse_exceptions import ResourceException


@logger
class FilesController(ResourcesController):

    __resource__ = "files"

    def read(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        status = {}

        present = self.module.is_file(res_id)
        status['name'] = res_id
        status['present'] = present
        if present:
            if attributes.get('get_content'):
                content = self.module.get_content(res_id)
                status['content'] = content
            if attributes.get('md5'):
                md5 = self.module.md5(res_id)
                status['md5'] = md5
            status['owner'] = self.module.owner(res_id)
            status['group'] = self.module.group(res_id)
            status['mode'] = self.module.mode(res_id)
            status['mod_time'] = self.module.mod_time(res_id)
            status['c_time'] = self.module.c_time(res_id)

        return status

    def create(self, res_id=None, attributes={}):
        '''
        This method is used to create or update a file on disk.
        ID is mandatory.
        Owner, group and mode are optional.
        If not specified and file exists, get mode of file on system
        If not specified and file doesn't exist, owner is the current user,
        group is the current group and mode depends on system's umask.
        '''
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        owner = self._get_owner(res_id, attributes)
        group = self._get_group(res_id, attributes)
        mode = self._get_mode(res_id, attributes)
        content = self._get_content(attributes)

        state = {
            'name': res_id,
            'owner': owner,
            'group': group,
            'mode': mode,
            'mod_time': str(datetime.now()),
            'c_time': str(datetime.now()),
            'present': True,
            'md5': self.module.md5_str(content)
        }

        self.save_state(res_id, state, monitor=monitor)

        if not self.module.exists(res_id):
            self.module.create_file(res_id)

        # Update meta of given file
        self.module.update_meta(res_id, owner, group, mode)

        # Set the content in file only if it's a file
        self.module.set_content(res_id, content)

        return self.read(res_id=res_id, attributes=attributes)

    def update(self, res_id=None, attributes={}):
        '''See create method'''

        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)

        previous_state = self.read(res_id=res_id)
        self.module.delete(res_id)

        if not self.module.exists(res_id):
            previous_state['present'] = False
            self.response = previous_state

        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        # First, compare the present flag. If it differs, no need to go
        # further, there's a compliance issue.
        # Check the next file state
        if persisted_state.get('present') != current_state.get('present'):
            compliant = False
            return compliant

        # Secondly, compare files attributes
        for attr in ('name', 'owner', 'group'):
            if persisted_state.get(attr) != current_state.get(attr):
                compliant = False
                break

        # Fix the retrocompatibility for mode when it used to be only 3 octal
        # digits
        current_mode = current_state.get('mode', '')
        persisted_mode = persisted_state.get('mode', '')
        if len(persisted_mode) == 3:
            if current_mode[-3:] != persisted_mode[-3:]:
                compliant = False
        elif current_mode != persisted_mode:
                compliant = False

        # Then compare modification times. If different, check md5sum
        if persisted_state.get('mod_time') != current_state.get('mod_time'):
            current_state_md5 = self.module.md5(persisted_state['name'])
            if current_state_md5 != persisted_state.get('md5'):
                compliant = False

        return compliant

    def _get_owner(self, path, attributes):
        # Default, get the current user. getpass is portable Unix/Windows
        owner = getpass.getuser()

        # If path exists, get path owner
        if self.module.exists(path):
            owner = self.module.owner(path)
        # Overwrite if owner name is provided
        if attributes.get('owner'):
            owner = attributes['owner']

        return owner

    def _get_group(self, path, attributes):
        # Default, get the current user's group.
        # getpass is portable Unix/Windows
        group = getpass.getuser()

        # If path exists, get path group
        if self.module.exists(path):
            group = self.module.group(path)
        # Overwrite if group name is provided
        if attributes.get('group'):
            group = attributes['group']

        return group

    def _get_mode(self, path, attributes):
        # Default, get default mode according to current umask
        mode = self.module.get_default_mode(path)

        # If path exists, get current mode
        if self.module.exists(path):
            mode = self.module.mode(path)

        # If mode is provided, return its octal value as string
        if attributes.get('mode'):
            try:
                mode = oct(int(attributes['mode'], 8))
            except ValueError as err:
                raise ResourceException("Error with path mode (%s)" % err)

        return mode

    def _get_content(self, attributes):
        content = attributes.get('content')
        content_by_url = attributes.get('content_by_url')
        encoding = attributes.get('encoding')

        # If content is url provided, overwrite content
        if content_by_url:
            try:
                fd = urllib2.urlopen(content_by_url)
                content = fd.read()
            except URLError, err:
                raise ResourceException("Error: %s (%s)" %
                        (err, content_by_url))

        # Decode if content is base64 encoded.
        if encoding == 'base64':
            try:
                content = base64.b64decode(content)
            except TypeError, err:
                raise ResourceException("Can't b64decode: %s" % err)

        return content

########NEW FILE########
__FILENAME__ = unix-files
import datetime
import grp
import hashlib
import os
import pwd
import logging

from synapse.synapse_exceptions import ResourceException
log = logging.getLogger('synapse.unix-files')


def exists(path):
    try:
        return os.path.exists(path)
    except IOError:
        return False


def is_file(path):
    try:
        return os.path.isfile(path)
    except IOError:
        return False


def list_dir(path):
    if not os.path.exists(path):
        raise ResourceException("Folder not found, sorry !")

    return os.listdir(path)


def get_content(path):
    if not os.path.exists(path):
        raise ResourceException('File not found, sorry !')

    with open(path, 'rb') as fd:
        content = fd.read()

    return content


def set_content(path, content):
    if not is_file(path):
        raise ResourceException('File not found')

    if content is not None:
        with open(path, 'w') as fd:
            fd.write(str(content))


def md5(path, block_size=2 ** 20):
    if not os.path.isfile(path):
        return None

    with open(path, 'r') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()


def md5_str(content):
    if content is None:
        content = ''

    m = hashlib.md5()
    m.update(content)
    return m.hexdigest()


def create_file(path):
    # Create folders if they don't exist
    if not os.path.exists(os.path.dirname(path)):
        create_folders(os.path.dirname(path))

    # Create the file if it does not exist
    if not os.path.exists(path):
        open(path, 'a').close()


def create_folders(path):
    try:
        # Recursive mkdirs if dir path is not complete
        os.makedirs(path)
    except OSError:
        #Already exists, no prob !
        pass
    except Exception as err:
        # Another problem
        raise ResourceException('Failed when creating folders: %s' % err)


def update_meta(path, owner, group, filemode):
    if not os.path.exists(path):
        raise ResourceException('This path does not exist.')

    ownerid = get_owner_id(owner)
    groupid = get_group_id(group)
    octfilemode = int(filemode, 8)

    try:
        os.chmod(path, octfilemode)
        os.chown(path, ownerid, groupid)
    except ValueError as err:
        raise ResourceException(err)


def delete(path):
    try:
        os.remove(path)
    except OSError:
        log.debug('File %s does not exist', path)


def mod_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getmtime(path)))


def c_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getctime(path)))


def owner(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')

    si = os.stat(path)
    uid = si.st_uid
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError as err:
        raise ResourceException(err)

def get_owner_id(name):
    try:
        return pwd.getpwnam(name).pw_uid
    except KeyError as err:
        raise ResourceException(err)


def group(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')

    si = os.stat(path)
    gid = si.st_gid
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError as err:
        raise ResourceException(err)


def get_group_id(name):
    try:
        return grp.getgrnam(name).gr_gid
    except KeyError as err:
        raise ResourceException(err)


def mode(path):
    if not os.path.exists(path):
        raise ResourceException('File does not exist.')

    si = os.stat(path)
    _mode = "%o" % si.st_mode
    return _mode[-4:]


def get_default_mode(path):
    current_umask = os.umask(0)
    os.umask(current_umask)
    _mode = 0644
    if os.path.isfile(path):
        _mode = 0666 ^ current_umask
    return oct(_mode)

########NEW FILE########
__FILENAME__ = win-files
import os
import hashlib
import datetime

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def exists(path):
    try:
        open(path)
        return True
    except IOError:
        return False


def list_dir(path):
    if not os.path.exists(path):
        raise ResourceException("Folder not found, sorry !")

    return os.listdir(path)


def get_content(path):
    path = os.path.join("/", path)
    if not os.path.exists(path):
        raise ResourceException('File not found, sorry !')

    with open(path, 'r') as file:
        content = file.read()

    return content


def set_content(path, content):
    _path = os.path.join("/", path)

    if not os.path.exists(_path):
        raise ResourceException('File not found')

    with open(_path, 'w') as fd:
        fd.write(str(content))


def md5(path, block_size=2 ** 20):
    if not os.path.exists(path):
        raise ResourceException('File not found')
    with open(path, 'r') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()


def md5_str(content):
    m = hashlib.md5()
    m.update(content)
    return m.hexdigest()


def create_file(id):
    try:
        # Recursive mkdirs if dir path is not complete
        os.makedirs(os.path.dirname(os.path.join("/", id)))
        update_meta(id, -1, -1, 0755)
    except:
        pass

    # Create the file with default values if not existing
    path = os.path.join("/", id)
    if not os.path.exists(path):
        open(path, 'a').close()
        try:
            os.chmod(path, 0644)
        except ValueError:
            raise
    else:
        raise ResourceException('File already exists')


def update_meta(id, owner, group, mode):
    pass


def delete(path):
    _path = os.path.join("/", path)
    if not os.path.exists(_path):
        raise ResourceException('File not found, sorry !')
    os.remove(_path)


def mod_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getmtime(path)))


def c_time(path):
    return str(datetime.datetime.fromtimestamp(os.path.getctime(path)))


def owner(path):
    pass


def group(path):
    pass


def mode(path):
    pass


def execute(cmd):
    return exec_cmd(cmd)

########NEW FILE########
__FILENAME__ = groups
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class GroupsController(ResourcesController):

    __resource__ = "groups"

    def read(self, res_id=None, attributes=None):
        return self.module.get_group_infos(res_id)

    def create(self, res_id=None, attributes=None):
        monitor = attributes.get('monitor')
        gid = "%s" % attributes.get("gid")
        state = {
            'present': True,
            'gid': gid
        }
        self.save_state(res_id, state, monitor=monitor)
        self.module.group_add(res_id, gid)

        return self.read(res_id)

    def update(self, res_id=None, attributes={}):
        status = {}
        new_name = attributes.get('new_name')
        gid = "%s" % attributes.get('gid')
        monitor = attributes.get('monitor')
        state = {
            'present': True,
            'gid': gid
        }

        self.save_state(res_id, state, monitor=monitor)

        if self.module.exists(res_id):
            if new_name or gid:
                self.module.group_mod(res_id, new_name, gid)
                status = self.module.get_group_infos(new_name)
            else:
                status = self.module.get_group_infos(res_id)
        else:
            self.create(res_id=res_id, attributes=attributes)

        return self.read(res_id)

    def delete(self, res_id=None, attributes=None):
        monitor = attributes.get('monitor')
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)
        self.module.group_del(res_id)
        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state.get(key):
                compliant = False
                break

        return compliant

########NEW FILE########
__FILENAME__ = unix-groups
import grp

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def exists(name):
    res = False
    try:
        res = format_group_info(name).get('present', False)
    except Exception:
        pass

    return res


def get_group_infos(name=None):
    if not name:
        return [format_group_info(x.gr_name) for x in grp.getgrall()]
    else:
        return format_group_info(name)


def format_group_info(name):
    d = {}
    try:
        gr = grp.getgrnam(name)
        d["present"] = True
        d["name"] = gr.gr_name
        d["members"] = gr.gr_mem
        d["gid"] = str(gr.gr_gid)
    except KeyError:
        d["present"] = False

    return d


def group_add(name, gid):
    cmd = ["/usr/sbin/groupadd"]

    if gid:
        cmd += ['--gid', "%s" % gid]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    # retcode 9 is group already exists. That's what we want.
    if ret['returncode'] != 9 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def group_mod(name, new_name, gid):
    cmd = ["/usr/sbin/groupmod"]

    if new_name:
        cmd += ['--new-name', "%s" % new_name]

    if gid:
        cmd += ['--gid', "%s" % gid]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def group_del(name):
    ret = exec_cmd("/usr/sbin/groupdel %s" % name)

    # retcode 6 is group doesn't exist. That's what we want.
    if ret['returncode'] != 6 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

########NEW FILE########
__FILENAME__ = win-groups

########NEW FILE########
__FILENAME__ = host
import logging
import socket

from netifaces import interfaces, ifaddresses, AF_INET, AF_LINK

from synapse.config import config

controller_options = config.controller
distribution_name = controller_options['distribution_name']
distribution_version = controller_options['distribution_version']
log = logging.getLogger('synapse.hosts')


def get_uuid():
    return config.rabbitmq['uuid']


def ping():
    return get_uuid()


def get_platform():
    return distribution_name, distribution_version


def get_cpu():
    try:
        import psutil
        return str(psutil.cpu_percent(interval=1))
    except ImportError:
        return 0


def get_hostname():
    try:
        response = socket.gethostbyaddr(socket.gethostname())[0]
    except IOError:
        response = socket.gethostname()
    except Exception, error:
        response = 'Error: ' + str(error)
    return str(response)


def get_mac_addresses():
    macs = {}
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in
                ifaddresses(ifaceName).setdefault(AF_LINK,
                    [{'addr':'No MAC addr'}])]
        if len(addresses):
            macs[ifaceName] = addresses[0]
    return macs


def get_memtotal():
    controller_config = config.controller
    if controller_config['distribution_name'] != 'windows':
        memtotal = ''
        try:
            with open('/proc/meminfo', 'rb') as fd:
                lines = fd.readlines()
                memtotal = lines[0].split()[1]
        except OSError, err:
            return "{0}".format(err)
        return memtotal


def get_ip_addresses():
    ips = {}
    for ifaceName in interfaces():
        addresses = [i['addr']
                     for i in ifaddresses(ifaceName).setdefault(AF_INET,
                                                [{'addr':'No IP addr'}])]
        if len(addresses):
            ips[ifaceName] = addresses[0]
    return ips


def get_uptime():
    controller_config = config.controller
    if controller_config['distribution_name'] != 'windows':
        try:
            with open("/proc/uptime", "rb") as fd:
                out = fd.readline().split()

        except:
            return "Cannot open /proc/uptime"

        total_seconds = float(out[0])

        # Helper vars:
        MINUTE = 60
        HOUR = MINUTE * 60
        DAY = HOUR * 24

        # Get the days, hours, etc:
        days = int(total_seconds / DAY)
        hours = int((total_seconds % DAY) / HOUR)
        minutes = int((total_seconds % HOUR) / MINUTE)
        seconds = int(total_seconds % MINUTE)

        # Build up the pretty string (like this: "N days, N hours, N minutes,
        # N seconds")
        string = ""
        if days > 0:
            string += str(days) + " " + (days == 1 and "day" or "days") + ", "
        if len(string) > 0 or hours > 0:
            string += str(hours) + " " + (hours == 1 and "hour" or "hours") + \
                      ", "
        if len(string) > 0 or minutes > 0:
            string += str(minutes) + " " + \
                      (minutes == 1 and "minute" or "minutes") + ", "
        string += str(seconds) + " " + (seconds == 1 and "second" or "seconds")

        return string

########NEW FILE########
__FILENAME__ = hosts
from synapse.logger import logger
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage, AmqpTask


@logger
class HostsController(ResourcesController):
    """ Resource exposing hosts informations.
    """

    __resource__ = "hosts"

    def read(self, res_id=None, attributes={}):
        sensors = attributes.keys()

        if not len(sensors):
            return {
                'hostname': self.module.get_hostname(),
                'ip': self.module.get_ip_addresses()
            }

        status = {}
        if 'hostname' in sensors:
            status['hostname'] = self.module.get_hostname()
        if 'ip' in sensors:
            status['ip'] = self.module.get_ip_addresses()
        if 'memtotal' in sensors:
            status['memtotal'] = self.module.get_memtotal()
        if 'macaddress' in sensors:
            status['macaddress'] = self.module.get_mac_addresses()
        if 'platform' in sensors:
            status['platform'] = self.module.get_platform()
        if 'uptime' in sensors:
            status['uptime'] = self.module.get_uptime()
        if 'cpu' in sensors:
            status['cpu'] = self.cpu()

        return status

    def ping(self):
        result = self.read()
        msg = OutgoingMessage(collection=self.__resource__,
                              status=result,
                              msg_type='status',
                              status_message=True)
        task = AmqpTask(msg)
        self.publish(task)

    def cpu(self):
        return self.module.get_cpu()


########NEW FILE########
__FILENAME__ = nagios
import os
from io import StringIO


from ConfigParser import RawConfigParser
from synapse.syncmd import exec_cmd
from synapse.config import config
from synapse.logger import logger
from synapse.scheduler import SynSched
from synapse.resources.resources import ResourcesController
from synapse.task import OutgoingMessage


@logger
class NagiosPluginsController(ResourcesController):

    __resource__ = "nagios"

    def __init__(self, module):
        super(NagiosPluginsController, self).__init__(module)
        self.path = self._configure()
        self.plugins = {}
        self._load_configs()
        self.scheduler = SynSched()
        self.scheduler.start()
        self._load_jobs()
        self.scheduler.add_job(self._reload, 30)

    def read(self, res_id=None, attributes=None):
        sensors = attributes.keys()
        status = {}
        for sensor in sensors:
            if sensor in self.plugins.keys():
                status[sensor] = exec_cmd(self.plugins[sensor]['command'])

        return status

    def _configure(self):
        config_path = os.path.join(config.paths['config_path'], 'nagios.d')
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        return config_path

    def _reload(self):
        self._load_configs()
        self._load_jobs()

    def _load_configs(self):
        for conf_file in os.listdir(self.path):
            if not conf_file.endswith('.conf'):
                continue
            full_path = os.path.join(self.path, conf_file)
            conf = RawConfigParser()
            conf.read(full_path)
            for section in conf.sections():
                if section not in self.plugins:
                    self.plugins[section] = dict(conf.items(section))
                    self.plugins[section]['scheduled'] = False

    def _load_jobs(self):
        for key, value in self.plugins.iteritems():
            if value['scheduled']:
                continue

            try:
                interval = int(value['interval'])
                command = value['command']
                if os.path.exists(command.split()[0]):
                    self.scheduler.add_job(self._execute,
                                           interval,
                                           actionargs=(key, command))
                    self.plugins[key]['scheduled'] = True
                else:
                    self.logger.warning("%s doesn't exist" % command)

            except ValueError:
                self.logger.warning("Interval value for %s must be an int" %
                                    key)
            except KeyError as err:
                self.logger.warning("Error when parsing %s (%s)" %
                                    (self.path, key))

    def _execute(self, name, cmd):
        result = exec_cmd(cmd)
        if result['returncode'] != 0:
            result['name'] = name
            msg = OutgoingMessage(collection=self.__resource__, status=result,
                                  msg_type='alert')
            self.publish(msg)

    def close(self):
        super(NagiosPluginsController, self).close()
        self.logger.debug("Shutting down nagios scheduler")
        self.scheduler.shutdown()

########NEW FILE########
__FILENAME__ = apt
import os
import logging

from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


env_vars = {'DEBIAN_FRONTEND': 'noninteractive'}
os.environ.update(env_vars)

log = logging.getLogger('synapse')

def install(name):
    ret = exec_cmd("/usr/bin/apt-get -qy update")
    ret = exec_cmd("/usr/bin/apt-get -qy install {0} --force-yes".format(name))
    if not is_installed(name):
        raise ResourceException(ret['stderr'])


def get_installed_packages():
    ret = exec_cmd("/usr/bin/dpkg-query -l")
    return ret['stdout'].split('\n')


def remove(name):
    ret = exec_cmd("/usr/bin/apt-get -qy remove {0} --force-yes".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def update(name):
    if name:
        ret = exec_cmd(
            "/usr/bin/apt-get -quy install {0} --force-yes".format(name))
        if ret['returncode'] != 0:
            raise ResourceException(ret['stderr'])
    else:
        ret = exec_cmd("/usr/bin/apt-get -qy update")
        ret = exec_cmd("/usr/bin/apt-get -qy upgrade --force-yes")
        if ret['returncode'] != 0:
            raise ResourceException(ret['stderr'])


def is_installed(name):
    ret = exec_cmd("/usr/bin/dpkg-query -l '{0}'".format(name))
    if ret['returncode'] != 0:
        return False

    # There's no way to use return code of any of the dpkg-query options.
    # Instead we use the "state" column of dpkg-query -l
    # So programmaticaly here:
    # 1. Get stdout
    # 2. Split on new line
    # 3. Get the last but one line (last is blank, in any case?)
    # 4. Get first character (i=installed)
    try:
        return ret['stdout'].split('\n')[-2][0] == 'i'
    except IndexError as err:
        log.error(err)
        return False

########NEW FILE########
__FILENAME__ = packages
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class PackagesController(ResourcesController):

    __resource__ = "packages"

    def read(self, res_id=None, attributes=None):
        status = {}

        if res_id:
            status['installed'] = self.module.is_installed(res_id)
        else:
            status['installed'] = self.module.get_installed_packages()

        return status

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'installed': True}
        self.save_state(res_id, state, monitor=monitor)

        if not self.module.is_installed(res_id):
            self.module.install(res_id)

        return self.read(res_id)

    def update(self, res_id='', attributes=None):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'installed': True}
        self.save_state(res_id, state, monitor=monitor)

        self.module.update(res_id)

        return self.read(res_id)

    def delete(self, res_id=None, attributes=None):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')

        state = {'installed': False}
        self.save_state(res_id, state, monitor=monitor)

        if self.module.is_installed(res_id):
            self.module.remove(res_id)

        return self.read(res_id)

    def is_compliant(self, expected, current):
        for key in expected.keys():
            if expected[key] != current.get(key):
                return False

        return True

########NEW FILE########
__FILENAME__ = yum-pkg
from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException
from synapse.logger import logger

log = logger('yum-pkg')


def install(name):
    ret = exec_cmd("/usr/bin/yum -q -y install %s" % name)
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def get_installed_packages():
    ret = exec_cmd("/bin/rpm -qa")
    return ret['stdout'].split('\n')


def remove(name):
    ret = exec_cmd("/usr/bin/yum -q -y remove %s" % name)
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def update(name):
    # We need to check first if the package is installed. yum update of a
    # non-existing package has a returncode of 0. We need to raise an exception
    # if the package is not installed !
    inst = is_installed(name)
    ret = exec_cmd("/usr/bin/yum -q -y update %s" % name)

    if ret['returncode'] != 0 or not inst:
        raise ResourceException(ret['stderr'])


def is_installed(name):
    if name:
        ret = exec_cmd("/bin/rpm -q %s" % name)
        return ret['returncode'] == 0
    else:
        return get_installed_packages()

########NEW FILE########
__FILENAME__ = rabbitmq
import json
import urllib2, base64
from synapse.logger import logger
from synapse.resources.resources import ResourcesController


@logger
class RabbitmqController(ResourcesController):

    __resource__ = "rabbitmq"

    def read(self, res_id=None, attributes={}):
        sensors = attributes.keys()

        status = {}
        if 'file_descriptors' in sensors:
            params = attributes['file_descriptors']
            status['file_descriptors'] = self.file_descriptors(params)

        return status

    def file_descriptors(self, parameters={}):
        username = parameters.get('username', 'guest')
        password = parameters.get('password', 'guest')
        url = parameters.get('url', 'http://localhost:55672/api/nodes')
        request = urllib2.Request(url)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        try:
            result = urllib2.urlopen(request)
            return json.loads(result.read())[0]['fd_used']
        except urllib2.URLError as err:
            return 0

########NEW FILE########
__FILENAME__ = apt-repos
import os

from synapse.synapse_exceptions import ResourceException

src_dir = "/etc/apt/sources.list.d"


def get_repos(name, details=False):
    repos = []
    for src_file in os.listdir(src_dir):
        full_path = os.path.join(src_dir, src_file)
        if name and name == src_file.split('.')[0]:
            repos.append(_load_repo(full_path))
            break
        elif name is None:
            repos.append(_load_repo(full_path))

    return repos


def create_repo(name, attributes={}):
    # Initialize the repo dictionnary
    repo = {}
    repo_file = os.path.join(src_dir, name + '.list')

    # If the file already exists, load repo into a dict
    if os.path.isfile(repo_file):
        repo = _load_repo(repo_file)

    newrepo = {}

    try:
        # baseurl attr is mandatory
        baseurl = attributes['baseurl']

        # if the full entry is not provided (i.e "deb url dist [components]")
        # distribution and components attr are mandatory
        if not _full_entry(baseurl):
            url = baseurl
            distribution = attributes['distribution']
            components = attributes['components']
            if not isinstance(components, list):
                components = set(''.join(components.split()).split(','))

        # If the full entry is provided, just split it into required elements
        else:
            url = baseurl.split()[0]
            distribution = baseurl.split()[1]
            components = set(baseurl.split()[2:])

        # Build the new repo dict
        newrepo = {'baseurl': url,
                   'distribution': distribution,
                   'components': components}

    except KeyError as err:
        raise ResourceException("Missing mandatory attribute [%s]" % err)

    # If that repo already exist, del entry and add the new one
    if name in repo:
        for index, rep in enumerate(repo[name]):
            if (rep['baseurl'] == newrepo['baseurl'] and
                rep['distribution'] == newrepo['distribution']):

                del repo[name][index]

        repo[name].append(newrepo)
    else:
        repo[name] = [newrepo]

    _dump_repo(repo)


def _full_entry(entry):
    items = entry.split()
    if len(items) == 1:
        return False
    elif len(items) >= 2:
        return True
    else:
        raise ResourceException("Invalid baseurl attribute.")


def delete_repo(name, attributes):
    repo = {}
    repo_file = os.path.join(src_dir, name + '.list')

    # If the file already exists, load repo into a dict
    if os.path.isfile(repo_file):
        repo = _load_repo(repo_file)

    try:
        # baseurl attr is mandatory
        baseurl = attributes['baseurl']

        if len(baseurl.split()) == 1:
            url = baseurl
            distribution = attributes['distribution']

        elif len(baseurl.split()) > 1:
            url = baseurl.split()[0]
            distribution = baseurl.split()[1]

        # Build the new repo dict
        deleterepo = {'baseurl': url,
                      'distribution': distribution}

    except KeyError as err:
        raise ResourceException("Missing mandatory attribute [%s]" % err)

    if name in repo:
        for index, rep in enumerate(repo[name]):
            if (rep['baseurl'] == deleterepo['baseurl'] and
                rep['distribution'] == deleterepo['distribution']):

                del repo[name][index]

        if not len(repo[name]):
            os.remove(repo_file)


def _load_repo(full_path):
    name = full_path.split(os.path.sep)[-1].split('.')[0]
    repo = {name: []}

    with open(full_path, 'r') as fd:
        for line in fd:
            tmp_repo = {}
            if not line:
                break
            elements = line.split()
            if len(elements) > 1 and elements[0] == 'deb':
                tmp_repo['baseurl'] = elements[1]
                tmp_repo['distribution'] = elements[2]
                components = elements[3:]
                if len(components):
                    tmp_repo['components'] = components

                repo[name].append(tmp_repo)

    return repo


def _dump_repo(repodict):
    for reponame, repos in repodict.iteritems():
        repo_file = os.path.join(src_dir, reponame + '.list')
        with open(repo_file, 'w') as fd:
            for item in repos:
                debstr = []
                debstr.append('deb')
                debstr.append(item['baseurl'])
                debstr.append(item['distribution'])
                for comp in item['components']:
                    debstr.append(comp)
                fd.write(' '.join(debstr) + '\n')

########NEW FILE########
__FILENAME__ = repos
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class ReposController(ResourcesController):

    __resource__ = "repos"

    def read(self, res_id=None, attributes={}):
        res_id = self._normalize(res_id)
        details = attributes.get('details')
        return self.module.get_repos(res_id, details=details)

    def create(self, res_id=None, attributes={}):
        self.check_mandatory(res_id)
        res_id = self._normalize(res_id)
        baseurl = attributes.get('baseurl')
        monitor = attributes.get('monitor')
        state = {
            'baseurl': baseurl,
             'present': True
        }
        self.save_state(res_id, state, monitor=monitor)
        if baseurl:
            self.module.create_repo(res_id, attributes)
        return self.read(res_id)

    def update(self, res_id=None, attributes=None):
        return self.create(res_id=res_id, attributes=attributes)

    def delete(self, res_id=None, attributes=None):
        self.check_mandatory(res_id)
        monitor = attributes.get('monitor')
        res_id = self._normalize(res_id)
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)
        self.module.delete_repo(res_id, attributes)

        return self.read(res_id)

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state[key]:
                compliant = False
                break

        return compliant

    def _normalize(self, name):
        return name.lower().replace(" ", "_")

########NEW FILE########
__FILENAME__ = yum-repos
import ConfigParser
import os

from synapse.synapse_exceptions import ResourceException


repo_path = "/etc/yum.repos.d"


def get_repos(name, details=False):

    repos = {}
    repo_file_list = os.listdir(repo_path)

    for repo_file in repo_file_list:
        repo_file_path = os.path.join(repo_path, repo_file)
        config = ConfigParser.RawConfigParser()
        try:
            config.read(repo_file_path)
            for section in config.sections():
                repo = dict(config.items(section))
                repo["filename"] = repo_file_path
                repo["present"] = True
                repos[section] = repo
        except Exception:
            repo = {'present': False}

    response = repos

    if name:
        response = repos.get(name, {"present": False,
                                    "name": name})
    else:
        if not details:
            response = repos.keys()

    return response


def create_repo(name, attributes):

    config_parser = ConfigParser.RawConfigParser()

    values = ("name",
              "baseurl",
              "metalink",
              "mirrorlist",
              "gpgcheck",
              "gpgkey",
              "exclude",
              "includepkgs",
              "enablegroups",
              "enabled",
              "failovermethod",
              "keepalive",
              "timeout",
              "enabled",
              "http_caching",
              "retries",
              "throttle",
              "bandwidth",
              "sslcacert",
              "sslverify",
              "sslclientcert",
              "metadata_expire",
              "mirrorlist_expire",
              "proxy",
              "proxy_username",
              "proxy_password",
              "cost",
              "skip_if_unavailable")

    baseurl = None
    try:
        baseurl = attributes['baseurl'].split()[0]
    except (KeyError, AttributeError) as err:
        raise ResourceException("Wrong baseurl attribute [%s]" % err)

    # Check if repo already exists
    repo = get_repos(name)

    # If it exists, get the filename in which the repo is defined
    # If not, check if a filename is user provided
    # If no filename is provided, create one based on the repo name
    if repo.get('present'):
        filename = repo.get("filename")
    elif attributes.get("filename"):
        filename = attributes["filename"]
    else:
        filename = "%s.repo" % name

    # Read the config file (empty or not) and load it in a ConfigParser
    # object
    repo_file_path = os.path.join(repo_path, filename)
    config_parser.read(repo_file_path)

    # Check if the repo is define in the ConfigParser context.
    # If not, add a section based on the repo name.
    if not config_parser.has_section(name):
        config_parser.add_section(name)
        config_parser.set(name, "name", name)

    # Set gpgcheck to 0 by default to bypass some issues
    config_parser.set(name, 'gpgcheck', 0)

    # Update the section with not None fields provided by the user
    for key, value in attributes.items():
        if value is not None and key in values:
            config_parser.set(name, key, value)

    config_parser.set(name, 'baseurl', baseurl)

    # Write changes to the repo file.
    with open(repo_file_path, 'wb') as repofile:
        config_parser.write(repofile)


def delete_repo(name, attributes):
    config_parser = ConfigParser.RawConfigParser()
    repo = get_repos(name)

    if repo.get('present'):
        filename = repo.get("filename")
        repo_file_path = os.path.join(repo_path, filename)
        config_parser.read(repo_file_path)

        if config_parser.remove_section(name):
            # Write changes to the repo file.
            with open(repo_file_path, 'wb') as repofile:
                config_parser.write(repofile)

        # Delete the repo file if there are no section in them
        config_parser.read(repo_file_path)
        if not len(config_parser.sections()):
            os.remove(repo_file_path)

########NEW FILE########
__FILENAME__ = resources
import sys
import traceback
import time
from datetime import datetime, timedelta


from synapse.synapse_exceptions import ResourceException
from synapse.states_manager import StatesManager
from synapse.config import config
from synapse.logger import logger
from synapse.task import AmqpTask, OutgoingMessage


@logger
class ResourcesController(object):
    """ This class is the mother of all resources classes.
    """
    __resource__ = ""

    action_map = {'create': 'Creating',
                  'read'  : 'Reading',
                  'update': 'Updating',
                  'delete': 'Deleting',
    }

    def __init__(self, module):
        self.default_interval = config.monitor['default_interval']
        alert_interval = config.compliance['alert_interval']
        self.alert_interval = timedelta(seconds=alert_interval)

        self.module = module
        self.res_id = None
        self.states_manager = StatesManager(self.__resource__)
        self.states = self.states_manager.states

        # This queue is injected by the resource locator at plugin
        # instantiation
        self.publish_queue = None

        self.response = {}

        # Use this lock to avoid unconsistent reads among threads, especially
        # the compliance/monitor one.
        self._lock = False

    def _fmt_attrs(self, attrs):
        res = ''

        if isinstance(attrs, dict):
            for key, value in attrs.iteritems():
                if isinstance(value, basestring) and len(value) > 20:
                    value = ''.join(value[:20] + '...')
                res += '%s: %s, ' % (key, value)

        elif isinstance(attrs, list):
            for item in attrs:
                res += '%s, ' % item

        return res.rstrip(', ')

    def process(self, arg):
        '''This is the only resource method called by the controller.'''

        action = arg.get('action')
        params = arg.get('attributes', {}) or {}
        monitor = arg.get('monitor')

        if monitor is not None:
            params['monitor'] = monitor

        self.res_id = arg.get('id')

        msg = "[%s] %s" % (self.__resource__.upper(), self.action_map[action])
        if self.res_id:
            msg += " '%s'" % self.res_id
        if params:
            msg += " (%s)" % self._fmt_attrs(params)

        self.logger.info(msg)

        self._lock = True
        self.response = self.set_response()
        try:
            result = getattr(self, action)(res_id=self.res_id,
                                           attributes=params)

            self.response = self.set_response(result)

            msg = "[%s] %s" % (self.__resource__.upper(), action.capitalize())
            if self.res_id:
                msg += " '%s'" % self.res_id
            msg += ": OK"
            self.logger.info(msg)

        except ResourceException as err:
            self.response = self.set_response(error='%s' % err)
            self.logger.info("[%s] %s '%s': RESOURCE ERROR [%s]" %
                             (self.__resource__.upper(),
                              action.capitalize(),
                              self.res_id,
                              self.response['error'].rstrip('\n')))

        except Exception as err:
            self.response = self.set_response(error='%s' % err)
            traceback.print_exc(file=sys.stdout)
            self.logger.info("[%s] %s '%s': UNKNOWN ERROR [%s]" %
                             (self.__resource__.upper(),
                              action.capitalize(),
                              self.res_id,
                              self.response['error'].rstrip('\n')))
        finally:
            self._lock = False

        # Copy the value to return
        response = self.response

        # Reset status and response
        self.response = {}

        return response

    def close(self):
        self.logger.debug("Shutting down %s controller...", self.__resource__)
        self.states_manager.shutdown()

    def set_response(self, resp={}, **kwargs):
        """Use this method to send a response to the controller.
        """

        msg = OutgoingMessage(resource_id=self.res_id,
                              collection=self.__resource__,
                              status=resp,
                              msg_type='response',
                              **kwargs)

        return msg

    def check_mandatory(self, *args):
        for arg in args:
            if not arg:
                raise ResourceException("Please provide ID")

    def is_compliant(self, expected, current):
        raise NotImplementedError('%s monitoring not implemented'
                                  % self.__resource__)

    def save_state(self, res_id, state={}, monitor=True):
        self.states_manager.save_state(res_id, state, monitor)

    def check_compliance(self):
        if self._lock:
            return

        for state in self.states:
            if not state['compliant'] or state['back_to_compliance']:
                self.publish_compliance(state)

    def monitor_states(self):
        if self._lock:
            return

        for state in self.states:
            # Get expected and current states
            expected = state['status']
            res_id = state['resource_id']
            current = self.read(res_id)

            # Update current status
            state['current_status'] = current

            # Update compliance infos
            was_compliant = state['compliant']
            is_compliant = self.is_compliant(expected, current)

            state['compliant'] = is_compliant
            state['back_to_compliance'] = not was_compliant and is_compliant

            now = datetime.now()

            # Persist states on disk.
            self.states_manager.persist()

    def publish(self, message):
        if self.publish_queue:
            self.publish_queue.put(AmqpTask(message))

    def publish_compliance(self, state, publish=True):
        """ When a state change is detected, this method publish a message to
        the transport layer.
        """

        msg = ''
        now = datetime.now()
        time_format = '%d/%m/%y %H:%M:%S'
        state['timestamp'] = now.strftime(time_format)

        if state['back_to_compliance'] and state['compliant']:
            state['msg_type'] = 'compliance_ok'
            state['back_to_compliance'] = False
            state['last_alert'] = None
            msg = "is BACK to compliance"

        elif not state['compliant']:
            state['msg_type'] = 'compliance_error'
            msg = "is NOT compliant"
            last_alert = state.get('last_alert')
            if last_alert:
                delta = now - datetime.strptime(last_alert, time_format)
                if delta < self.alert_interval:
                    publish = False
                else:
                    state['last_alert'] = now.strftime(time_format)
            else:
                state['last_alert'] = now.strftime(time_format)


        if publish:
            self.logger.debug("%s (%s) %s." % (state['resource_id'],
                                               state['collection'],
                                               msg))
            msg = OutgoingMessage(**state)
            self.publish(msg)

        self.states_manager.persist()

########NEW FILE########
__FILENAME__ = services-debian
import os

from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def start(name):
    ret = exec_cmd("/etc/init.d/{0} start".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd("/etc/init.d/{0} stop".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd("/usr/sbin/update-rc.d -f {0} defaults".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd("/usr/sbin/update-rc.d -f {0} remove".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    ret = exec_cmd("/etc/init.d/{0} restart".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def reload(name):
    ret = exec_cmd("/etc/init.d/{0} reload".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def is_enabled(name):
    ret = exec_cmd("/sbin/runlevel")
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    match = False
    try:
        runlevel = ret['stdout'].split()[1]
        for filename in os.listdir('/etc/rc%s.d' % runlevel):
            if name in filename and filename.startswith('S'):
                match = True

    except ValueError, err:
        raise ResourceException(err)
    except IndexError, err:
        raise ResourceException(err)

    return match


def is_running(name):
    ret = exec_cmd("/etc/init.d/{0} status".format(name))
    return ret['returncode'] == 0

########NEW FILE########
__FILENAME__ = services-systemd
from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def _cmd(action, name):
    return "systemctl {0} {1}.service".format(action, name)


def start(name):
    ret = exec_cmd(_cmd("start", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd(_cmd("stop", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd(_cmd("enable", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd(_cmd("disable", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    ret = exec_cmd(_cmd("restart", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def reload(name):
    ret = exec_cmd(_cmd("reload", name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def is_enabled(name):
    ret = exec_cmd(_cmd("is-enabled", name))
    return ret['returncode'] == 0


def is_running(name):
    ret = exec_cmd(_cmd("status", name))
    return ret['returncode'] == 0

########NEW FILE########
__FILENAME__ = services-systemv
import os

from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def start(name):
    ret = exec_cmd("/etc/init.d/{0} start".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd("/etc/init.d/{0} stop".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd("/sbin/chkconfig {0} on".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd("/sbin/chkconfig {0} off".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    ret = exec_cmd("/etc/init.d/{0} restart".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def reload(name):
    ret = exec_cmd("/etc/init.d/{0} reload".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def is_enabled(name):
    ret = exec_cmd("/sbin/runlevel")
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    match = False
    try:
        runlevel = ret['stdout'].split()[1]
        for filename in os.listdir('/etc/rc%s.d' % runlevel):
            if name in filename and filename.startswith('S'):
                match = True

    except (ValueError, IndexError), err:
        raise ResourceException(err)

    return match


def is_running(name):
    ret = exec_cmd("/etc/init.d/{0} status".format(name))
    return ret['returncode'] == 0

########NEW FILE########
__FILENAME__ = services-windows
from synapse.syncmd import exec_cmd
from synapse.synapse_exceptions import ResourceException


def start(name):
    ret = exec_cmd("net start {0}".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def stop(name):
    ret = exec_cmd("net stop {0}".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def enable(name):
    ret = exec_cmd("sc config {0} start= auto".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def disable(name):
    ret = exec_cmd("sc config {0} start= demand".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def restart(name):
    stop(name)
    start(name)


def reload(name):
    pass


def is_enabled(name):
    pass


def is_running(name):
    ret = exec_cmd("sc query {0}".format(name))
    for line in ret['stdout'].split('\n'):
        if 'RUNNING' in line:
            return True
    return False

########NEW FILE########
__FILENAME__ = services
from synapse.synapse_exceptions import ResourceException
from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class ServicesController(ResourcesController):

    __resource__ = "services"

    def read(self, res_id=None, attributes=None):
        status = {}
        self.check_mandatory(res_id)
        status['running'] = self.module.is_running(res_id)
        status['enabled'] = self.module.is_enabled(res_id)

        return status

    def create(self, res_id=None, attributes=None):
        return self.update(res_id=res_id, attributes=attributes)

    def update(self, res_id=None, attributes=None):
        # Id must be provided. Update cannot be done on multiple resources.
        # Attributes key must be provided
        status = {}
        self.check_mandatory(res_id, attributes)
        monitor = attributes.get('monitor')

        enabled = attributes.get('enabled')
        running = attributes.get('running')
        restart_service = attributes.get('restart')
        reload_service = attributes.get('reload')
        monitor = attributes.get('monitor')

        state = {
            'running': running,
            'enabled': enabled
        }

        self.save_state(res_id, state, monitor=monitor)

        # Retrieve the current state...
        status['running'] = self.module.is_running(res_id)
        status['enabled'] = self.module.is_enabled(res_id)

        # ...and compare it with wanted status. Take action if different.

        # Enable/Disable resource
        if enabled is not None and enabled != status["enabled"]:
            if enabled:
                self.module.enable(res_id)
            else:
                self.module.disable(res_id)

        # Start/Stop resource
        if running is not None and running != status["running"]:
            if running:
                self.module.start(res_id)
            else:
                self.module.stop(res_id)

        # Restart resource
        if restart_service:
            self.module.restart(res_id)

        # Reload resource
        if reload_service:
            self.module.reload(res_id)

        # Return status after actions has been taken
        status['running'] = self.module.is_running(res_id)
        status['enabled'] = self.module.is_enabled(res_id)

        return status

    def delete(self, res_id=None, attributes=None):
        return {}

    def is_compliant(self, persisted_state, current_state):
        compliant = True

        for key in persisted_state.keys():
            if current_state.get(key) != persisted_state.get(key):
                compliant = False
                break

        return compliant

########NEW FILE########
__FILENAME__ = unix-users
import grp
import pwd

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def user_exists(name):
    res = False
    try:
        res = get_user_infos(name).get('present')
    except Exception:
        pass

    return res


def get_user_infos(name):
    d = {}
    try:
        pw = pwd.getpwnam(name)
        d["present"] = True
        d["gid"] = str(pw.pw_gid)
        d["uid"] = str(pw.pw_uid)
        d["name"] = pw.pw_name
        d["homedir"] = pw.pw_dir
        d["shell"] = pw.pw_shell
        d["gecos"] = pw.pw_gecos
        d["groups"] = get_groups(name)

    except KeyError:
        d["present"] = False

    return d


def user_add(name, password, login_group, groups,
             homedir, comment, uid, gid, shell):

    cmd = ['/usr/sbin/useradd']

    if login_group:
        cmd += ['-g', '%s' % login_group]
    if len(groups):
        cmd += ['-G', ','.join(groups)]
    if homedir:
        cmd += ['--home', '%s' % homedir]
    if comment:
        cmd += ['--comment', '%s' % comment]
    if uid:
        cmd += ['--uid', '%s' % uid]
    if gid:
        cmd += ['--gid', '%s' % gid]
    if shell:
        cmd += ['--shell', '%s' % shell]

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    # retcode 9 is group already exists. That's what we want.
    if ret['returncode'] != 9 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    if password:
        set_password(name, password)


def filter_existing_groups(groups):
    if isinstance(groups, basestring):
        groups = groups.split(',')
        groups = [group.strip() for group in groups]

    return groups


def get_groups(name):
    cmd = ["/usr/bin/groups"]
    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    # Return a list of groups
    return ret['stdout'].split(':')[1].lstrip().split()


def user_mod(name, password, login_group, groups, homedir, move_home,
             comment, uid, gid, shell):

    try:
        if password:
            set_password(name, password)

        cmd = ["/usr/sbin/usermod"]
        if login_group:
            cmd += ['-g', '%s' % login_group]
        if len(groups):
            cmd += ['-G', ','.join(groups)]
        if homedir:
            cmd += ['--home', '%s' % homedir]
        if homedir and move_home:
            cmd += ['--move-home']
        if comment:
            cmd += ['--comment', '%s' % comment]
        if uid:
            cmd += ['--uid', '%s' % uid]
        if gid:
            cmd += ['--gid', '%s' % gid]
        if shell:
            cmd += ['--shell', '%s' % shell]

        cmd.append(name)

        if len(cmd) > 2:
            ret = exec_cmd(' '.join(cmd))
            if ret['returncode'] != 0:
                raise ResourceException(ret['stderr'])

    except ResourceException:
        raise


def set_password(name, password):
    ret = exec_cmd("echo {0}:{1} | chpasswd".format(name, password))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def user_del(name):
    ret = exec_cmd("/usr/sbin/userdel {0} -f".format(name))

    # retcode 6 is group doesn't exist. That's what we want.
    if ret['returncode'] != 6 and ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def get_group_infos(name):
    try:
        gr = grp.getgrnam(name)
        d = {}
        d["name"] = gr.gr_name
        d["members"] = gr.gr_mem
        d["gid"] = str(gr.gr_gid)
        return d

    except KeyError:
        raise ResourceException("Group not found")

def get_pw(name):
    pw = None
    try:
        with open('/etc/shadow', 'r') as fd:
            for line in fd:
                if line.split(':')[0] == name:
                    pw = line.split(':')[1]
    except Exception as err:
        raise ResourceException(err)

    return pw

########NEW FILE########
__FILENAME__ = users
import re

from synapse.resources.resources import ResourcesController
from synapse.logger import logger


@logger
class UsersController(ResourcesController):

    __resource__ = "users"

    def read(self, res_id=None, attributes=None):
        return self.module.get_user_infos(res_id)

    def create(self, res_id=None, attributes=None):
        password = attributes.get('password')
        login_group = attributes.get('login_group')
        groups = self._sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir') or '/home/%s' % res_id
        comment = attributes.get('full_name')
        uid = "%s" % attributes.get('uid', '') or ''
        gid = "%s" % attributes.get('gid', '') or ''
        shell = attributes.get('shell')

        self.module.user_add(res_id, password, login_group, groups,
                             homedir, comment, uid, gid, shell)

        if not uid:
            uid = self.module.get_user_infos(res_id)['uid']
        if not gid:
            gid = self.module.get_user_infos(res_id)['gid']
        if not shell:
            shell = self.module.get_user_infos(res_id)['shell']

        state = {
            'present': True,
            'password': self.module.get_pw(res_id),
            'groups': groups.append(login_group),
            'homedir': homedir,
            'gecos': comment,
            'uid': uid,
            'gid': gid,
            'shell': shell
        }
        self.save_state(res_id, state, monitor=monitor)

        return self.read(res_id)

    def update(self, res_id=None, attributes=None):

        monitor = attributes.get('monitor')
        if monitor is False:
            self.comply(monitor=False)
            return "%s unmonitored" % res_id

        password = attributes.get("password")
        login_group = attributes.get("login_group")
        groups = self._sanitize_groups(attributes.get('groups', []))
        homedir = attributes.get('homedir')
        move_home = attributes.get('move_home')
        comment = attributes.get('full_name')
        uid = "%s" % attributes.get('uid')
        gid = "%s" % attributes.get('gid')
        shell = attributes.get('shell')

        if self.module.user_exists(res_id):
            self.module.user_mod(res_id, password, login_group, groups,
                                 homedir, move_home, comment, uid, gid, shell)
            state = {
                'present': True,
                'password': self.module.get_pw(res_id),
                'groups': groups.append(login_group),
                'homedir': homedir,
                'gecos': comment,
                'uid': uid,
                'gid': gid,
                'shell': shell
            }

            self.save_state(res_id, state, monitor=monitor)

            self.response = self.module.get_user_infos(res_id)
        else:
            self.response = self.create(res_id=res_id, attributes=attributes)

        return self.read(res_id)

    def delete(self, res_id=None, attributes=None):
        monitor = attributes.get('monitor')
        state = {'present': False}
        self.save_state(res_id, state, monitor=monitor)
        self.module.user_del(res_id)
        return self.read(res_id)

    def _sanitize_groups(self, groups):
        group_list = []
        if groups:
            group_list = re.sub('\s', '', groups).split(',')
        return group_list

    def is_compliant(self, persisted_state, current_state):
        compliant = True
        name = persisted_state.get('name')

        for key in persisted_state.keys():
            if key == 'password':
                if persisted_state['password'] != self.module.get_pw(name):
                    compliant = False
            else:
                if current_state.get(key) != persisted_state[key]:
                    compliant = False

        return compliant

########NEW FILE########
__FILENAME__ = win-users
import re

from synapse.synapse_exceptions import ResourceException
from synapse.syncmd import exec_cmd


def user_exists(name):
    try:
        get_user_infos(name)

    except ResourceException:
        return False

    return True


def get_user_infos(name):
    pass
    #try:
    #    pw = pwd.getpwnam(name)
    #    d = {}
    #    d["gid"] = pw.pw_gid
    #    d["uid"] = pw.pw_uid
    #    d["name"] = pw.pw_name
    #    d["dir"] = pw.pw_dir
    #    d["shell"] = pw.pw_shell
    #    d["gecos"] = pw.pw_gecos
    #    d["groups"] = get_groups(name)
    #    return d

    #except KeyError:
    #    raise ResourceException("User not found")


def user_add(name, password, login_group, groups):
    cmd = []
    cmd.append("/usr/sbin/useradd")
    if login_group:
        cmd.append("-g")
        cmd.append(login_group)
    if groups:
        groups_no_ws = re.sub(r'\s', '', groups)
        try:
            group_list = groups_no_ws.split(',')
            for group in group_list:
                groups.read(group)
            cmd.append("-G")
            cmd.append(groups_no_ws)
        except ResourceException:
            raise ResourceException("Group does not exist")

    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))

    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    if password:
        set_password(name, password)


def filter_existing_groups(groups):
    groups_no_ws = re.sub(r'\s', '', groups)
    group_list = groups_no_ws.split(',')
    existing_groups = []
    for group in group_list:
        try:
            groups.get_group_infos(group)
            existing_groups.append(group)
        except ResourceException:
            pass

    return existing_groups


def get_groups(name):
    cmd = []
    cmd.append("/usr/bin/groups")
    cmd.append(name)

    ret = exec_cmd(' '.join(cmd))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])

    # Return a list of groups
    return ret['stdout'].split(':')[1].lstrip().split()


def user_mod(name,
             password=None,
             login_group=None,
             add_to_groups=None,
             remove_from_groups=None,
             set_groups=None
             ):

    try:
        if password:
            set_password(name, password)

        cmd = []
        cmd.append("/usr/sbin/usermod")

        if login_group:
            cmd.append("-g")
            cmd.append(login_group)

        elif add_to_groups:
            groups = filter_existing_groups(add_to_groups)
            if len(groups):
                cmd.append("-G")
                cmd.append(','.join(groups))
                cmd.append("-a")

        elif remove_from_groups:
            groups = filter_existing_groups(remove_from_groups)
            current_groups = get_groups(name)

            if len(groups):
                groups_to_set = filter(lambda x: x not in groups,
                                       current_groups)
                cmd.append("-G")
                cmd.append(','.join(groups_to_set))

        elif set_groups:
            groups = filter_existing_groups(set_groups)
            if len(groups):
                cmd.append("-G")
                cmd.append(','.join(groups))

        cmd.append(name)
        if len(cmd) > 2:
            ret = exec_cmd(' '.join(cmd))
            if ret['returncode'] != 0:
                raise ResourceException(ret['stderr'])

    except ResourceException:
        raise


def set_password(name, password):
    ret = exec_cmd("echo -n {0} | passwd --stdin {1}".format(password, name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def user_del(name):
    ret = exec_cmd("/usr/sbin/userdel {0} -f".format(name))
    if ret['returncode'] != 0:
        raise ResourceException(ret['stderr'])


def get_group_infos(name):
    pass
    #try:
    #    gr = grp.getgrnam(name)
    #    d = {}
    #    d["name"] = gr.gr_name
    #    d["members"] = gr.gr_mem
    #    d["gid"] = gr.gr_gid
    #    return d

    #except KeyError:
    #    raise ResourceException("Group not found")

########NEW FILE########
__FILENAME__ = resource_locator
import os
import sys
import imp
import pkgutil

from synapse.config import config
from synapse.synapse_exceptions import ResourceException
from synapse.logger import logger
from synapse.register_plugin import registry


@logger
class ResourceLocator(object):
    def __init__(self, publish_queue):
        builtin_plugins = os.sep.join([os.path.dirname(__file__), "resources"])
        custom_plugins = config.controller['custom_plugins']
        sys.path.append(custom_plugins)
        resources_path_list = [builtin_plugins, custom_plugins]

        self.load_packages(resources_path_list)

        for controller in registry.itervalues():
            controller.publish_queue = publish_queue

    def get_instance(self, name=None):
        try:
            return registry[name] if name else registry
        except KeyError:
            raise ResourceException("The resource [%s] does not exist" % name)

    def load_packages(self, paths):
        ignored = self.get_ignored()
        for path in paths:
            for mod in pkgutil.iter_modules([path]):
                if mod[1] not in ignored:
                    fp, pathname, desc = imp.find_module(mod[1], [mod[0].path])
                    imp.load_module(mod[1], fp, pathname, desc)

    def get_ignored(self):
        # We only ignore resources specified in ignore option
        return [x.strip().lower() for x in
                config.controller['ignored_resources'].split(',')]

########NEW FILE########
__FILENAME__ = scheduler
import time
import sched

import threading

from synapse.config import config
from synapse.logger import logger


@logger
class SynSched(threading.Thread):
    def __init__(self):
        self.logger.debug("Initializing the scheduler...")
        threading.Thread.__init__(self, name="SCHEDULER")

        # Start the scheduler
        self.scheduler = sched.scheduler(time.time, lambda x: time.sleep(.1))

    def run(self):
        self.scheduler.run()
        self.logger.debug("Scheduler started...")

    def add_job(self, job, interval, actionargs=()):
        self.logger.debug("Adding job '%s' to scheduler every %d seconds" %
                          (job, interval))
        self._periodic(self.scheduler, interval, job, actionargs=actionargs)

    def update_job(self, job, interval, actionargs=()):
        job_name = actionargs[0].__name__
        existing_job = self.get_job(job_name)
        if existing_job is None:
            self.add_job(job, interval, actionargs)
        elif (interval != existing_job.argument[1] or
              actionargs != existing_job.argument[3]):
                self.scheduler.cancel(existing_job)
                self.add_job(job, interval, actionargs)

    def get_job(self, job_name):
        job = None
        for event in self.scheduler.queue:
            if len(event.argument[3]):
                if job_name == event.argument[3][0].__name__:
                    job = event
            else:
                if job_name == event.argument[2].__name__:
                    job = event

        return job

    def _periodic(self, scheduler, interval, action, actionargs=()):
        args = (scheduler, interval, action, actionargs)
        scheduler.enter(interval, 1, self._periodic, args)
        try:
            action(*actionargs)
        except NotImplementedError:
            pass
        except Exception as err:
            self.logger.error("Could not run job \'%s\' (%s)", action, err)

    def shutdown(self):
        """Shuts down the scheduler."""
        self.logger.debug("Canceling scheduled events")
        for event in self.scheduler.queue:
            self.scheduler.cancel(event)

########NEW FILE########
__FILENAME__ = startup_windows
import sys
import urllib2
import tempfile
import subprocess

from netifaces import interfaces, ifaddresses, AF_LINK


def _get_mac_addresses():
    macs = {}
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in
                ifaddresses(ifaceName).setdefault(AF_LINK,
                    [{'addr':'No MAC addr'}])]
        if len(addresses):
            macs[ifaceName] = addresses[0]
    return macs


if __name__ == "__main__":
    mac_addresses = _get_mac_addresses().values()

    if not len(mac_addresses):
        sys.exit()

    fd, tmppath = tempfile.mkstemp()

    for mac in mac_addresses:
        try:
            url = "http://alder.angleur.guardis.be/w2k8boot.py"
            #url = "http://birch.angleur.guardis.be:8000/api/data/%s/w2k8boot"
            #% (_get_mac_addresses().values()[0], tmppath)
            u = urllib2.urlopen(url)
        except urllib2.HTTPError, err:
            continue

    with open(tmppath, "wb") as tmpscript:
        tmpscript.write(u.read())

    cmd = "python %s" % tmppath

    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    print stdout

########NEW FILE########
__FILENAME__ = states_manager
import os, stat
import pickle
from pickle import PicklingError, PickleError
from operator import itemgetter

from synapse.synapse_exceptions import SynapseException
from synapse.config import config
from synapse.logger import logger


@logger
class StatesManager(object):
    def __init__(self, resource_name):
        self.resource_name = resource_name

        # Get folder where states are persisted
        folder = config.controller['persistence_path']

        # If folder does not exist, raise exception
        if not os.path.exists(folder):
            raise Exception('Persistence folder does not exist.')

        # Filename for this resource state manager
        self.path = os.path.join(folder, resource_name + '.pkl')

        # Load states in memory
        self.states = self._load_from_file(self.path)

    def _load_from_file(self, path):
        states = []
        try:
            if os.path.exists(path):
                with open(path, 'rb') as fd:
                    states = pickle.load(fd)
        except (PickleError, PicklingError), err:
            raise SynapseException(err)
        except (IOError, EOFError):
            pass

        self.logger.debug("Loading %d persisted resources states from %s" %
                          (len(states), path))

        return states

    def persist(self):
        try:
            with open(self.path, 'wb') as fd:
                os.chmod(self.path, stat.S_IREAD | stat.S_IWRITE)
                pickle.dump(self.states, fd)
        except IOError as err:
            self.logger.error(err)

    def shutdown(self):
        for state in self.states:
            if 'last_alert' in state:
                state['last_alert'] = None
        self.persist()

    def save_state(self, res_id, state, monitor):
        if monitor is False:
            self._remove_state(res_id)

        else:
            item = {
                'uuid': config.rabbitmq['uuid'],
                'resource_id': res_id,
                'collection': self.resource_name,
                'status': state,
                'compliant': True,
                'back_to_compliance': False
            }

            self._update_state(item)
        self.persist()

    def _update_state(self, state):
        index = self._get_index(state['resource_id'])
        if index != -1:
            state['back_to_compliance'] = not self.states[index]['compliant']
            self.states[index].update(state)
        else:
            self.states.append(state)

    def _remove_state(self, res_id):
        index = self._get_index(res_id)
        if index != -1:
            del self.states[index]

    def _get_index(self, res_id):
        try:
            return map(itemgetter('resource_id'), self.states).index(res_id)
        except ValueError:
            return -1

    def _get_state(self, res_id):
        index = self._get_index(res_id)
        return self.states[index] if index != -1 else {}


########NEW FILE########
__FILENAME__ = synapse_exceptions
from synapse.config import config


class ResourceException(Exception):
    pass


class MethodNotAllowedException(Exception):
    def __init__(self, value):
        opts = config.rabbitmq
        self.error = {}
        self.error['uuid'] = opts['uuid']
        self.error['error'] = value
        self.error['status'] = {}

    def __str__(self):
        return repr(self.error)


class SynapseException(Exception):
    def __init__(self, value=''):
        opts = config.rabbitmq
        self.value = value
        self.error = {}
        self.error['uuid'] = opts['uuid']
        self.error['error'] = value
        self.error['status'] = {}

    def __str__(self):
        return repr(self.error)

########NEW FILE########
__FILENAME__ = syncmd
import sys
import tempfile

from subprocess import Popen, PIPE
from threading import Thread

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty


ON_POSIX = 'posix' in sys.builtin_module_names
__STDOUTBUF__ = ''


def exec_cmd(cmd):
    ret = {}
    stdout = tempfile.TemporaryFile(mode='w+t')
    stderr = tempfile.TemporaryFile(mode='w+t')
    try:
        proc = Popen(cmd, shell=True, universal_newlines=True,
                     stdout=stdout, stderr=stderr)
        ret_code = proc.wait()

        stdout.flush()
        stderr.flush()

        out = ''
        stdout.seek(0)
        for line in stdout:
            out += line.rstrip()

        err = ''
        stderr.seek(0)
        for line in stderr:
            err += line.rstrip()

        ret['cmd'] = cmd
        ret['stdout'] = out
        ret['stderr'] = err
        ret['returncode'] = ret_code
        ret['pid'] = proc.pid

    finally:
        stdout.close()
        stderr.close()

    return ret


def exec_threaded_cmd(cmd):
    proc = Popen(cmd,
                 shell=True,
                 bufsize=64,
                 close_fds=ON_POSIX,
                 stdout=PIPE,
                 stderr=PIPE)
    bufqueue = Queue()
    t = Thread(target=_enqueue_output, args=(proc.stdout, bufqueue))
    t.daemon = True
    t.start()

    try:
        global __STDOUTBUF__
        line = bufqueue.get(timeout=.1)
    except Empty:
        pass
    else:
        __STDOUTBUF__ += line


def _enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

########NEW FILE########
__FILENAME__ = task
import json

from pika import BasicProperties
from synapse.config import config
from synapse.logger import logger
from synapse import permissions


@logger
class Message(object):
    _model = {}

    def __init__(self, message):
        self.body = self.validate(message)

    def validate(self, message):
        raise NotImplementedError


class OutgoingMessage(Message):

    def __init__(self,
                 resource_id='',
                 collection='',
                 status={},
                 msg_type='',
                 **kwargs):
        msg = {
            'resource_id': resource_id,
            'collection': collection,
            'status': status,
            'msg_type': msg_type
        }

        for kwarg in kwargs:
            msg[kwarg] = kwargs[kwarg]

        self.body = self.validate(msg)

    def validate(self, msg):
        _model = {
            'uuid': config.rabbitmq['uuid'],
            'resource_id': '',
            'collection': '',
            'status': {},
            'version':config.SYNAPSE_VERSION
        }

        if not isinstance(msg, dict):
            raise ValueError("Outgoing message is not a dict.")

        try:
            _model.update(msg)
            msg = json.dumps(_model)
        except AttributeError as err:
            raise ValueError("Message not well formatted: %s", err)

        return msg


class IncomingMessage(Message):

    def validate(self, msg):
        _model = {
            'id': '',
            'collection': '',
            'action': '',
            'attributes': {},
            'monitor': False
        }

        try:
            msg = json.loads(msg)
            _model.update(msg)
        except AttributeError as err:
            raise ValueError("Message not well formatted: %s", err)

        if 'collection' not in msg or not msg['collection']:
            raise ValueError("Collection missing.")

        if 'action' not in msg or not msg['action']:
            raise ValueError("Action missing.")

        if 'attributes' in msg and not isinstance(msg['attributes'], dict):
            raise ValueError("Attributes must be a dict.")

        if 'monitor' in msg and not isinstance(msg['monitor'], bool):
            raise ValueError("Monitor must be a boolean")

        return _model


@logger
class Task(object):
    def __init__(self, message, sender='', check_permissions=True):
        self.body = message.body
        self.sender = sender
        #TODO: re-enable permission
        #if check_permissions and isinstance(message, IncomingMessage):
        #    self._check_permissions(message.body)

    def _check_permissions(self, msg):
        allowed = permissions.get(config.controller['permissions_path'])
        perms = permissions.check(allowed,
                                  self.sender,
                                  msg['collection'],
                                  msg['id'])

        if self.body['action'] not in perms:
            raise ValueError("You don't have permission to do that.")


@logger
class AmqpTask(Task):
    def __init__(self, body, headers={}):
        self.headers = headers
        self.sender = self._get_sender(self.headers)
        super(AmqpTask, self).__init__(body, sender=self.sender)
        self.user_id = self._get_user_id()
        self.correlation_id = self._get_correlation_id(self.headers)
        self.delivery_tag = self._get_delivery_tag(self.headers)
        self.publish_exchange = self._get_publish_exchange(self.headers)
        self.routing_key = self._get_routing_key(self.headers)
        self.redeliver = False

    def _get_publish_exchange(self, headers):
        publish_exchange = None

        if 'headers' in headers:
            hds = headers['headers']
            if isinstance(hds, dict):
                publish_exchange = hds.get('reply_exchange')

        if publish_exchange is None:
            publish_exchange = config.rabbitmq['publish_exchange']

        return publish_exchange

    def _get_delivery_tag(self, headers):
        return headers.get('delivery_tag')

    def _get_routing_key(self, headers):
        routing_key = headers.get('reply_to', headers.get('routing_key'))

        if routing_key is None:
            routing_key = config.rabbitmq['publish_routing_key']

        return routing_key

    def _get_correlation_id(self, headers):
        return headers.get('correlation_id')

    def _get_sender(self, headers):
        return headers.get('user_id') or ''

    def _get_user_id(self):
        return config.rabbitmq['username']

    def get(self):
        basic_properties = BasicProperties(correlation_id=self.correlation_id,
                                           user_id=self.user_id)
        body = self.body
        if isinstance(body, dict):
            body = json.dumps(self.body)
        try:
            return {"exchange": self.publish_exchange,
                    "routing_key": self.routing_key,
                    "properties": basic_properties,
                    "body": body}
        except ValueError as err:
            self.logger.error("Invalid message (%s)" % err)

########NEW FILE########
__FILENAME__ = webtransport
import web
import sys
import json
from synapse.synapse_exceptions import SynapseException

from synapse.log import log


class WebTransport(object):
    def __init__(self, controller=None):
        globals()['ctrl'] = controller
        log.debug("Initialized controller")
        try:
            self.urls = ("/(.*)", "Restapi")
            sys.argv[1:] = ['8888']
        except ValueError, err:
            raise SynapseException('Wrong port (%s)' % err)

    def start(self):
        log.debug("Starting REST API")
        app = web.application(self.urls, globals())
        app.run()


class Restapi:
    def GET(self, path):
        return self.process_request(path, 'read')

    def POST(self, path):
        return self.process_request(path, 'create')

    def PUT(self, path):
        return self.process_request(path, 'udpate')

    def DELETE(self, path):
        return self.process_request(path, 'delete')

    def process_request(self, path, action):
        msg = {}
        try:
            path.lstrip('/')
            path_parts = path.split('/')
            msg['action'] = action
            msg['collection'] = path_parts[0]
            if len(path_parts) > 1:
                id = path_parts[1]
                msg['id'] = id

            if len(web.data()):
                msg['attributes'] = json.loads(web.data())
            log.debug('REST Msg: %s' % msg)

        except IndexError, err:
            return err
        except ValueError, err:
            return err
        response = globals()['ctrl'].call_method(msg)

        return response

########NEW FILE########
__FILENAME__ = test_permissions
import re
import os
import unittest

from synapse import permissions


perm_mapping = ['create', 'read', 'update', 'delete', 'ping']


class TestPermissionsProcess(unittest.TestCase):
    def test_fail_if_too_few_sections(self):
        line = "cortex hypervisors *CRUD"
        self.assertRaises(re.error, permissions.process, line)

    def test_fail_if_too_many_sections(self):
        line = "cortex hypervisors * CRUD roger"
        self.assertRaises(re.error, permissions.process, line)

    def test_sanitization(self):
        line = " cortex   hypervisors\t* CRUD\n  \t"
        result = [re.compile('cortex'),
                  re.compile('hypervisors'),
                  re.compile('.*'),
                  set(perm_mapping)]

        test = permissions.process(line)
        test[3] = set(test[3])
        self.assertListEqual(test, result)

    def test_fail_bad_regexp(self):
        line = "cortex hypervisors (((((()) CRUD"
        self.assertRaises(re.error, permissions.process, line)

    def test_bad_permissions_fail(self):
        line = "cortex hypervisors * ARUD"
        self.assertRaises(re.error, permissions.process, line)

    def test_unordered_permissions_success(self):
        line = "cortex hypervisors * DURC"
        # Check no exception is thrown
        permissions.process(line)

    def test_accept_dash_permission(self):
        line = "cortex hypervisors * -"
        # Check no exception is thrown
        permissions.process(line)


class TestPermissionsCheck(unittest.TestCase):

    def setUp(self):
        self.line = "cortex files /etc/httpd/* CRD"

    def test_everything_allowed(self):
        self.line = "* * * CRUD"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_nothing_allowed(self):
        self.line = "* * * -"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_deny_wrong_res_id(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_allow_wildcard_res_id(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/httpd/httpd.conf'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_allow_space_in_res_id(self):
        self.line = """cortex files "/home/user/My Images/*" CRD"""
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/home/user/My Images/test.png'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_allow_wildcard_collection(self):
        self.line = "cortex * * CRD"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'packages'
        res_id = 'httpd'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_wrong_permission(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/httpd/httpd.conf'
        action = 'update'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_wrong_collection(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'packages'
        res_id = '/etc/httpd/httpd.conf'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_wrong_user(self):
        perm = permissions.process(self.line)

        user = 'coretekusu'
        collection = 'packages'
        res_id = '/etc/httpd/httpd.conf'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_if_can_read_then_can_ping(self):
        self.line = "* files * R"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = ''
        action = 'ping'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_if_cannot_read_then_cannot_ping(self):
        self.line = "* files * -"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = ''
        action = 'ping'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)


class TestPermissionsFile(unittest.TestCase):

    def _get_fp(self, fn):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), fn))

    def test_empty_file_raises_error(self):
        fp = self._get_fp('empty_permissions.conf')
        self.assertRaises(SystemExit, permissions.get, fp)

    def test_absent_file_raises_error(self):
        fp = self._get_fp('nofile.conf')
        self.assertRaises(IOError, permissions.get, fp)

    def test_blank_lines_dont_matter(self):
        fp = self._get_fp('permissions.conf')
        permissions.get(fp)

    def test_lines_order_matter_fail(self):
        fp = self._get_fp('permissions.conf')
        perm_list = permissions.get(fp)

        user = '*'
        collection = 'executables'
        res_id = 'rm -rf /'
        action = 'update'
        perms = permissions.check(perm_list, user, collection, res_id)

        self.assertFalse(action in perms)

    def test_lines_order_matter_success(self):
        fp = self._get_fp('permissions.conf')
        perm_list = permissions.get(fp)

        user = '*'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'update'
        perms = permissions.check(perm_list, user, collection, res_id)

        self.assertTrue(action in perms)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
