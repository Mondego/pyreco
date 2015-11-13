__FILENAME__ = Domain
import requests
from .Record import Record

class Domain(object):
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.client_id = ""
        self.api_key = ""
        self.name = None
        self.ttl = None
        self.live_zone_file = None
        self.error = None
        self.zone_file_with_error = None
        self.records = []

        #Setting the attribute values
        for attr in kwargs.keys():
            setattr(self,attr,kwargs[attr])

    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/domains/%s%s" % ( self.id, path ), params=payload)
        data = r.json()
        self.call_response = data
        if data['status'] != "OK":
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)
   
        return data

    def load(self):
        domain = self.__call_api("")['domain']
        self.zone_file_with_error = domain['zone_file_with_error']
        self.error = domain['error']
        self.live_zone_file = domain['live_zone_file']
        self.ttl = domain['ttl']
        self.name = domain['name']
        self.id = domain['id']

    def destroy(self):
        """
            Destroy the droplet
        """
        self.__call_api("/destroy/")

    def create(self):
        """
            Create the droplet with object properties.
        """
        data = {
                "name": self.name,
                "ip_address": self.ip_address,
            }
        data = self.__call_api("new", data)
        if data:
            self.id = data['domain']['id']

    def get_records(self):
        """
            Returns a list of Record objects
        """
        records = []
        data = self.__call_api("/records/")
        for record_data in data['records']:
            record = Record(domain_id=record_data.pop('domain_id'),
                            id=record_data.pop('id'))
            for key, value in record_data.iteritems():
                setattr(record, key, value)
            record.client_id = self.client_id
            record.api_key = self.api_key
            records.append(record)
        return records

########NEW FILE########
__FILENAME__ = Droplet
import requests
from .Event import Event

class Droplet(object):
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.client_id = ""
        self.api_key = ""
        self.name = None
        self.backup_active = None
        self.region_id = None
        self.image_id = None
        self.size_id = None
        self.status = None
        self.ip_address = None
        self.private_ip_address = None
        self.call_reponse = None
        self.ssh_key_ids = None
        self.created_at = None
        self.events = []

        #Setting the attribute values
        for attr in kwargs.keys():
            setattr(self,attr,kwargs[attr])

    def call_api(self, path, params=dict()):
        """
            exposes any api entry
            useful when working with new API calls that are not yet implemented by Droplet class
        """
        return self.__call_api(path, params)

    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/droplets/%s%s" % ( self.id, path ), params=payload)
        data = r.json()
        self.call_response = data
        if data['status'] != "OK":
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)
        #add the event to the object's event list.
        event_id = data.get(u'event_id',None)
        if not event_id and u'event_id' in data.get(u'droplet',{}):
            event_id = data[u'droplet'][u'event_id']

        if event_id: self.events.append(event_id)
        return data

    def load(self):
        droplet = self.__call_api("")['droplet']
        self.backup_active = droplet['backups_active']
        self.region_id = droplet['region_id']
        self.size_id = droplet['size_id']
        self.image_id = droplet['image_id']
        self.status = droplet['status']
        self.name = droplet['name']
        self.ip_address = droplet['ip_address']
        self.private_ip_address = droplet['private_ip_address']
        self.created_at = droplet['created_at']
        self.id = droplet['id']

    def power_on(self):
        """
            Boot up the droplet
        """
        self.__call_api("/power_on/")

    def shutdown(self):
        """
            shutdown the droplet
        """
        self.__call_api("/shutdown/")

    def reboot(self):
        """
            restart the droplet
        """
        self.__call_api("/reboot/")

    def power_cycle(self):
        """
            restart the droplet
        """
        self.__call_api("/power_cycle/")

    def power_off(self):
        """
            restart the droplet
        """
        self.__call_api("/power_off/")

    def reset_root_password(self):
        """
            reset the root password
        """
        self.__call_api("/reset_root_password/")

    def resize(self, new_size):
        """
            resize the droplet to a new size
        """
        self.__call_api("/resize/", {"size_id": new_size})

    def take_snapshot(self, snapshot_name):
        """
            Take a snapshot!
        """
        self.__call_api("/snapshot/", {"name": snapshot_name})

    def restore(self, image_id):
        """
            Restore the droplet to an image ( snapshot or backup )
        """
        self.__call_api("/restore/", {"image_id": image_id})

    def rebuild(self, image_id=None):
        """
            Restore the droplet to an image ( snapshot or backup )
        """
        if self.image_id and not image_id:
            image_id = self.image_id
        self.__call_api("/rebuild/", {"image_id": image_id})

    def enable_backups(self):
        """
            Enable automatic backups
        """
        self.__call_api("/enable_backups/")

    def disable_backups(self):
        """
            Disable automatic backups
        """
        self.__call_api("/disable_backups/")

    def destroy(self, scrub_data=True):
        """
            Destroy the droplet
        """
        self.__call_api("/destroy/", {'scrub_data': '1' if scrub_data else '0'})

    def rename(self, name):
        """
            Rename the droplet
        """
        self.__call_api("/rename/", {'name': name})

    def create(self, ssh_key_ids=None, virtio=False, private_networking=False, backups_enabled=False):
        """
            Create the droplet with object properties.
        """
        data = {
                "name": self.name,
                "size_id": self.size_id,
                "image_id": self.image_id,
                "region_id": self.region_id,
                "ssh_key_ids": self.ssh_key_ids
            }

        if ssh_key_ids:
            if type(ssh_key_ids) in [int, long, str]:
                data['ssh_key_ids']= str(ssh_key_ids)
            elif type(ssh_key_ids) in [set, list, tuple, dict]:
                data['ssh_key_ids'] = ','.join(str(x) for x in ssh_key_ids)
            else:
                raise Exception("ssh_key_ids should be an integer or long number, a string, a set, a list/tuple or a ditionary ")

        if backups_enabled:
            data['backups_enabled'] = 1

        if virtio:
            data['virtio'] = 1

        if private_networking:
            data['private_networking'] = 1

        data = self.__call_api("new", data)
        if data:
            self.id = data['droplet']['id']

    def get_events(self):
        """
            Returns a list of Event objects
            This events can be used to check the droplet's status
        """
        events = []
        for event_id in self.events:
            event = Event(event_id)
            event.client_id = self.client_id
            event.api_key = self.api_key
            event.load()
            events.append(event)
        return events

########NEW FILE########
__FILENAME__ = Event
import requests

class Event(object):
    def __init__(self, event_id=""):
        self.id = event_id
        self.client_id = None
        self.api_key = None
        self.event_type_id = None
        self.percentage = None
        self.droplet_id = None
        self.action_status = None
        self.call_response = None
        
    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/events/%s%s" % ( self.id, path ), params=payload)
        data = r.json()
        self.call_response = data
        if data['status'] != "OK":            
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)
        return data

    def load(self):
        event = self.__call_api("")
        if event:
            event = event[u'event']
            self.id = event['id']
            self.event_type_id = event[u'event_type_id']
            self.percentage = event[u'percentage']
            self.droplet_id = event[u'droplet_id']
            self.action_status = event[u'action_status']
        
########NEW FILE########
__FILENAME__ = Image
import requests

class Image(object):
    def __init__(self, client_id="", api_key=""):
        self.client_id = client_id
        self.api_key = api_key

        self.name = None
        self.id = None
        self.distribution = None

    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/images/%s%s" % ( self.id, path ), params=payload)
        data = r.json()
        self.call_response = data
        if data['status'] != "OK":
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)

        return data

    def Destroy(self):
        """
            Destroy the image
        """
        self.__call_api("/destroy/")

    def transfer(self, new_region_id):
        """
            Transfer the image
        """
        self.__call_api("/transfer/", {"region_id": new_region_id})

########NEW FILE########
__FILENAME__ = Manager
import requests
from .Droplet import Droplet
from .Region import Region
from .Size import Size
from .Image import Image
from .Domain import Domain
from .SSHKey import SSHKey


class Manager(object):
    def __init__(self, client_id="", api_key=""):
        self.client_id = client_id
        self.api_key = api_key
        self.call_response = None

    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/%s" % path, params=payload)
        data = r.json()
        self.call_response = data
        if data['status'] != "OK":
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)
        return data

    def get_all_regions(self):
        """
            This function returns a list of Region object.
        """
        data = self.__call_api("/regions/")
        regions = list()
        for jsoned in data['regions']:
            region = Region()
            region.id = jsoned['id']
            region.name = jsoned['name']
            region.client_id = self.client_id
            region.api_key = self.api_key
            regions.append(region)
        return regions

    def get_all_droplets(self):
        """
            This function returns a list of Droplet object.
        """
        data = self.__call_api("/droplets/")
        droplets = list()
        for jsoned in data['droplets']:
            droplet = Droplet()
            droplet.backup_active = jsoned['backups_active']
            droplet.region_id = jsoned['region_id']
            droplet.size_id = jsoned['size_id']
            droplet.image_id = jsoned['image_id']
            droplet.status = jsoned['status']
            droplet.name = jsoned['name']
            droplet.id = jsoned['id']
            droplet.ip_address = jsoned['ip_address']
            droplet.private_ip_address = jsoned['private_ip_address']
            droplet.created_at = jsoned['created_at']
            droplet.client_id = self.client_id
            droplet.api_key = self.api_key
            droplets.append(droplet)
        return droplets

    def get_all_sizes(self):
        """
            This function returns a list of Size object.
        """
        data = self.__call_api("/sizes/")
        sizes = list()
        for jsoned in data['sizes']:
            size = Size()
            size.id = jsoned['id']
            size.name = jsoned['name']
            size.memory = jsoned['memory']
            size.cpu = jsoned['cpu']
            size.disk = jsoned['disk']
            size.cost_per_hour = jsoned['cost_per_hour']
            size.cost_per_month = jsoned['cost_per_month']
            size.client_id = self.client_id
            size.api_key = self.api_key
            sizes.append(size)
        return sizes

    def get_all_images(self):
        """
            This function returns a list of Image object.
        """
        data = self.__call_api("/images/")
        images = list()
        for jsoned in data['images']:
            image = Image()
            image.id = jsoned['id']
            image.name = jsoned['name']
            image.distribution = jsoned['distribution']
            image.client_id = self.client_id
            image.api_key = self.api_key
            images.append(image)
        return images

    def get_my_images(self):
        """
            This function returns a list of Image object.
        """
        data = self.__call_api("/images/",{"filter":"my_images"})
        images = list()
        for jsoned in data['images']:
            image = Image()
            image.id = jsoned['id']
            image.name = jsoned['name']
            image.distribution = jsoned['distribution']
            image.client_id = self.client_id
            image.api_key = self.api_key
            images.append(image)
        return images

    def get_global_images(self):
        """
            This function returns a list of Image object.
        """
        data = self.__call_api("/images/",{"filter":"global"})
        images = list()
        for jsoned in data['images']:
            image = Image()
            image.id = jsoned['id']
            image.name = jsoned['name']
            image.distribution = jsoned['distribution']
            image.client_id = self.client_id
            image.api_key = self.api_key
            images.append(image)
        return images

    def get_all_domains(self):
        """
            This function returns a list of Domain object.
        """
        data = self.__call_api("/domains/")
        domains = list()
        for jsoned in data['domains']:
            domain = Domain()
            domain.zone_file_with_error = jsoned['zone_file_with_error']
            domain.error = jsoned['error']
            domain.live_zone_file = jsoned['live_zone_file']
            domain.ttl = jsoned['ttl']
            domain.name = jsoned['name']
            domain.id = jsoned['id']
            domain.client_id = self.client_id
            domain.api_key = self.api_key
            domains.append(domain)
        return domains

    def get_all_sshkeys(self):
        """
            This function returns a list of SSHKey object.
        """
        data = self.__call_api("/ssh_keys/")
        ssh_keys = list()
        for jsoned in data['ssh_keys']:
            ssh_key = SSHKey()
            ssh_key.id = jsoned['id']
            ssh_key.name = jsoned['name']
            ssh_key.client_id = self.client_id
            ssh_key.api_key = self.api_key
            ssh_keys.append(ssh_key)
        return ssh_keys


########NEW FILE########
__FILENAME__ = Record
import requests
      
class Record(object):
    def __init__(self, domain_id, id="", client_id="", api_key=""):
        self.domain_id = domain_id
        self.id = id
        self.client_id = client_id
        self.api_key = api_key
        self.record_type = None
        self.name = None
        self.data = None
        self.priority = None
        self.port = None
        self.weight = None
        
    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/domains/%s/records/%s%s" % (
                         self.domain_id, self.id, path), params=payload)
        data = r.json()
        self.call_response = data
        if data['status'] != "OK":            
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)
        return data

    def create(self):
        """
            Create a record for a domain
        """
        data = {
                "record_type": self.record_type,
                "data": self.data,
                "name": self.name,
                "priority": self.priority,
                "port": self.port,
                "weight": self.weight
            }
        data = self.__call_api("new", data)
        if data:
            self.id = data['record']['id']

    def destroy(self):
        """
            Destroy the record
        """
        self.__call_api("/destroy/")

    def save(self):
        """
            Save existing record
        """
        data = {
            "record_type": self.record_type,
            "data": self.data,
            "name": self.name,
            "priority": self.priority,
            "port": self.port,
            "weight": self.weight,
        }
        data = self.__call_api("/edit/", data)

    def load(self):
        record = self.__call_api("")
        if record:
            record = record[u'record']
            self.id = record['id']
            self.record_type = record[u'record_type']
            self.name = record[u'name']
            self.data = record[u'data']
            self.priority = record[u'priority']
            self.port = record[u'port']
            self.weight = record[u'weight']

########NEW FILE########
__FILENAME__ = Region
class Region(object):
    def __init__(self, client_id="", api_key=""):
        self.client_id = client_id
        self.api_key = api_key

        self.name = None
        self.id = None

########NEW FILE########
__FILENAME__ = Size
class Size(object):
    def __init__(self, client_id="", api_key=""):
        self.client_id = client_id
        self.api_key = api_key

        self.name = None
        self.id = None
        self.memory = None
        self.cpu = None
        self.disk = None
        self.cost_per_hour = None
        self.cost_per_month = None

########NEW FILE########
__FILENAME__ = SSHKey
import requests

class SSHKey(object):
    def __init__(self, client_id="", api_key="", *args, **kwargs):

        self.client_id = client_id
        self.api_key = api_key

        self.id = ""
        self.name = None
        self.ssh_pub_key = None

        #Setting the attribute values
        for attr in kwargs.keys():
            setattr(self,attr,kwargs[attr])

    def __call_api(self, path, params=dict()):
        payload = {'client_id': self.client_id, 'api_key': self.api_key}
        payload.update(params)
        r = requests.get("https://api.digitalocean.com/ssh_keys/%s%s" % ( self.id, path ), params=payload)

        data = r.json()
        self.call_response = data
        if data['status'] != "OK":
            msg = [data[m] for m in ("message", "error_message", "status") if m in data][0]
            raise Exception(msg)

        return data

    def load(self):
        ssh_key = self.__call_api("")['ssh_key']
        self.ssh_pub_key = ssh_key['ssh_pub_key']
        self.name = ssh_key['name']
        self.id = ssh_key['id']

    def create(self):
        """
            Create the SSH Key
        """
        data = {
                "name": self.name,
                "ssh_pub_key": self.ssh_pub_key,
            }
        data = self.__call_api("/new/", data)
        if data:
            self.id = data['ssh_key']['id']

    def edit(self):
        """
            Edit the SSH Key
        """
        data = {
                "name": self.name,
                "ssh_pub_key": self.ssh_pub_key,
            }
        data = self.__call_api("/edit/", data)
        if data:
            self.id = data['ssh_key']['id']

    def destroy(self):
        """
            Destroy the SSH Key
        """
        self.__call_api("/destroy/")

########NEW FILE########
