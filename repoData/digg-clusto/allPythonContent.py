__FILENAME__ = clustohttp
#!/usr/bin/env python

try:
    import simplejson as json
except ImportError:
    import json

from urllib import urlencode, quote
from urlparse import urlsplit, urljoin
import httplib
import logging

from pprint import pprint

def request(method, url, body='', headers={}):
    logging.debug('%s %s' % (method, url))
    if type(body) != type(''):
        body = urlencode(body)
    url = urlsplit(url, 'http')

    conn = httplib.HTTPConnection(url.hostname, url.port)
    if url.query:
        query = '%s?%s' % (url.path, url.query)
    else:
        query = url.path
    conn.request(method, query, body, headers)
    response = conn.getresponse()
    length = response.getheader('Content-length', None)
    if length:
        data = response.read(int(length))
    else:
        data = response.read()
    conn.close()
    if response.status >= 400:
        logging.debug('Server error %s: %s' % (response.status, data))
    return (response.status, response.getheaders(), data)

class ClustoProxy(object):
    def __init__(self, url):
        self.url = url

    def get_entities(self, **kwargs):
        for k, v in kwargs.items():
            if k == 'attrs':
                kwargs[k] = json.dumps(v)
        status, headers, response = request('POST', self.url + '/query/get_entities?%s' % urlencode(kwargs))
        if status != 200:
            raise Exception(response)
        return [EntityProxy(self.url + x) for x in json.loads(response)]

    def get_by_name(self, name):
        status, headers, response = request('GET', self.url + '/query/get_by_name?name=%s' % quote(name))
        if status != 200:
            raise Exception(response)
        obj = json.loads(response)
        return EntityProxy(self.url + obj['object'])

    def get_from_pools(self, pools, clusto_types=None):
        url = self.url + '/query/get_from_pools?pools=%s' % ','.join(pools)
        if clusto_types:
            url += '&types=' + ','.join(clusto_types)
        status, headers, response = request('GET', url)
        if status != 200:
            raise Exception(response)
        return [EntityProxy(self.url + x) for x in json.loads(response)]

    def get_ip_manager(self, ip):
        status, headers, response = request('GET', self.url + '/query/get_ip_manager?ip=%s' % ip)
        if status != 200:
            raise Exception(response)
        return EntityProxy(self.url + json.loads(response))

class EntityProxy(object):
    def __init__(self, url):
        self.url = url
        self.name = self.url.rsplit('/', 1)[1]

    def __getattr__(self, action):
        def method(**kwargs):
            data = {}
            for k, v in kwargs.items():
                if isinstance(v, bool):
                    v = int(v)
                if not type(v) in (int, str, unicode):
                    v = json.dumps(v)
                data[k] = v
            if data:
                status, headers, response = request('GET', '%s/%s?%s' % (self.url, action, urlencode(data)))
            else:
                status, headers, response = request('GET', '%s/%s' % (self.url, action))
            if status != 200:
                raise Exception(response)
            if response:
                return json.loads(response)
            else:
                return None
        return method

    def contents(self):
        return [EntityProxy(urljoin(self.url, x)) for x in self.show()['contents']]

    def parents(self):
        return [EntityProxy(urljoin(self.url, x)) for x in self.show()['parents']]

    def attrs(self, **kwargs):
        return self.__getattr__('attrs')(**kwargs)['attrs']
    
    def set_port_attr(self, porttype, portnum, key, value):
        return self.__getattr__('set_port_attr')(porttype=porttype, portnum=portnum, key=key, value=value)

    def get_port_attr(self, porttype, portnum, key):
        return self.__getattr__('get_port_attr')(porttype=porttype, portnum=portnum, key=key)

    def __str__(self):
        return urlsplit(self.url).path

    def __repr__(self):
        return 'EntityProxy(%s)' % repr(self.url)

def test():
    clusto = ClustoProxy('http://127.0.0.1:9996')
    server = clusto.get_entities(attrs=[{'subkey': 'mac', 'value': '00:a0:d1:e9:3d:dc'}])
    server = server[0]
    print server
    assert server.name == 's0104'
    attr = server.get_port_attr('nic-eth', 1, 'mac')
    server.set_port_attr('nic-eth', 1, 'mac', attr)
    newattr = server.get_port_attr('nic-eth', 1, 'mac')
    print repr((attr, newattr))
    assert newattr == attr
    #print server.parents()
    #obj = clusto.get_by_name('s1100')
    #pprint(obj.ports())
    #pprint(obj.attrs(key='dhcp', merge_container_attrs=True))
    #webservers = clusto.get_from_pools(['webservers-lolcat', 'production'])
    #pprint(webservers)
    #pprint(webservers[0].contents())

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = rackfactory
#!/usr/bin/env python

from socket import gethostbyname

from clusto.scripthelpers import init_script
from clusto.drivers import *
import clusto

def get_factory(name, layout=None):
    if not layout:
        rack = clusto.get_by_name(name)
        layout = rack.attr_value(key='racklayout')

    factory = LAYOUTS.get(str(layout), None)
    if factory:
        factory = factory(name, rack.parents(clusto_types=['datacenter']))
    return factory

class RackFactory(object):
    def bind_dns_ip_to_osport(self, obj, osport, porttype=None, portnum=None, domain='digg.internal'):
        ip = gethostbyname('%s.%s' % (obj.name, domain))
        obj.bind_ip_to_osport(ip, osport, porttype=porttype, portnum=portnum)

class Digg201001RackFactory(RackFactory):
    LAYOUT_NAME = '201001'

    SWITCHPORT_TO_RU = {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11,
        12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20,
        21: 21, 22: 22, 23: 23,
        24: 25, 25: 26, 26: 27, 27: 28, 28: 29, 29: 30, 30: 31
    }
    SWITCHPORT_TO_PWR = {
        1: 'bb1', 2: 'bb2', 3: 'bb3', 4: 'bb4', 5: 'bb5', 6: 'bb6', 7: 'bb7',
        8: 'bb8', 9: 'ba1', 10: 'ba2', 11: 'ba3', 12: 'ba4', 13: 'ba5',
        14: 'ba6', 15: 'ba7', 16: 'ba8', 17: 'ab1', 18: 'ab2', 19: 'ab3',
        20: 'ab4', 21: 'ab5', 22: 'ab6', 23: 'ab7', 24: 'aa1', 25: 'aa2',
        26: 'aa3', 27: 'aa4', 28: 'aa5', 29: 'aa6', 30: 'aa7'
    }

    def __init__(self, name, datacenter):
        self.datacenter = datacenter
        self.rack = clusto.get_or_create(name, APCRack)
        self.switch = clusto.get_or_create(name + '-sw1', Cisco4948)
        self.console = clusto.get_or_create(name + '-ts1', OpenGearCM4148)
        self.power = clusto.get_or_create(name + '-pwr1', PowerTowerXM)

    def connect_ports(self):
        self.rack.set_attr(key='racklayout', value=self.LAYOUT_NAME)

        if not self.rack in self.datacenter:
            self.datacenter.insert(self.rack)

        if not self.power in self.rack:
            self.rack.insert(self.power, 41)
        if self.power.port_free('nic-eth', 1):
            self.power.connect_ports('nic-eth', 1, self.switch, 44)
        if self.power.port_free('console-serial', 1):
            self.power.connect_ports('console-serial', 1, self.console, 44)

        if not self.switch in self.rack:
            self.rack.insert(self.switch, 36)
        if self.switch.port_free('pwr-nema-5', 1):
            self.switch.connect_ports('pwr-nema-5', 1, self.power, 'aa8')
        if self.switch.port_free('console-serial', 1):
            self.switch.connect_ports('console-serial', 1, self.console, 48)

        if not self.console in self.rack:
            self.rack.insert(self.console, 34)
        if self.console.port_free('pwr-nema-5', 1):
            self.console.connect_ports('pwr-nema-5', 1, self.power, 'ab8')
        if self.console.port_free('nic-eth', 1):
            self.console.connect_ports('nic-eth', 1, self.switch, 43)

        self.bind_dns_ip_to_osport(self.switch, 'Vlan442')
        self.bind_dns_ip_to_osport(self.console, 'nic0', porttype='nic-eth', portnum=1)
        self.bind_dns_ip_to_osport(self.power, 'nic0', porttype='nic-eth', portnum=1)

    def add_server(self, server, switchport):
        if not server in self.rack:
            self.rack.insert(server, self.SWITCHPORT_TO_RU[switchport])
        if server.port_free('nic-eth', 1):
            server.connect_ports('nic-eth', 1, self.switch, switchport)
        if server.port_free('pwr-nema-5', 1):
            server.connect_ports('pwr-nema-5', 1, self.power, self.SWITCHPORT_TO_PWR[switchport])
        if server.port_free('console-serial', 1):
            server.connect_ports('console-serial', 1, self.console, switchport)

    def get_driver(self, switchport):
        return PenguinServer

class Digg5555RackFactory(RackFactory):
    LAYOUT_NAME = '5555'

    SWITCHPORT_TO_RU = {
        1:1, 2:2, 3:3, 4:4, 5:5,
        6:7, 7:8, 8:9, 9:10, 10:11,
        11:13, 12:14, 13:15, 14:16, 15:17,
        16:19, 17:20, 18:21, 19:22, 20:23,

        21:1, 22:2, 23:3, 24:4, 25:5,
        26:7, 27:8, 28:9, 29:10, 30:11,
        31:13, 32:14, 33:15, 34:16, 35:17,
        36:19, 37:20, 38:21, 39:22, 40:23,
    }

    SWITCHPORT_TO_PWR = {
        1: 'bb1', 2: 'bb2', 3: 'bb3', 4: 'bb4', 5: 'bb5',
        6: 'ba1', 7: 'ba2', 8: 'ba3', 9: 'ba4', 10: 'ba5',
        11: 'ab1', 12: 'ab2', 13: 'ab3', 14: 'ab4', 15: 'ab5',
        16: 'aa1', 17: 'aa2', 18: 'aa3', 19: 'aa4', 20: 'aa5',
    }

    def __init__(self, name, datacenter):
        self.datacenter = datacenter
        self.rack = clusto.get_or_create(name, APCRack)
        self.switch = clusto.get_or_create(name + '-sw1', Cisco4948)
        self.console = clusto.get_or_create(name + '-ts1', OpenGearCM4148)
        self.power = clusto.get_or_create(name + '-pwr1', PowerTowerXM)

    def connect_ports(self):
        self.rack.set_attr(key='racklayout', value=self.LAYOUT_NAME)

        if not self.rack in self.datacenter:
            self.datacenter.insert(self.rack)

        if not self.power in self.rack:
            self.rack.insert(self.power, 29)
        if self.power.port_free('nic-eth', 1):
            self.power.connect_ports('nic-eth', 1, self.switch, 44)
        if self.power.port_free('console-serial', 1):
            self.power.connect_ports('console-serial', 1, self.console, 44)

        if not self.switch in self.rack:
            self.rack.insert(self.switch, 31)
        if self.switch.port_free('pwr-nema-5', 1):
            self.switch.connect_ports('pwr-nema-5', 1, self.power, 'aa8')
        if self.switch.port_free('console-serial', 1):
            self.switch.connect_ports('console-serial', 1, self.console, 48)

        if not self.console in self.rack:
            self.rack.insert(self.console, 30)
        if self.console.port_free('pwr-nema-5', 1):
            self.console.connect_ports('pwr-nema-5', 1, self.power, 'ab8')
        if self.console.port_free('nic-eth', 1):
            self.console.connect_ports('nic-eth', 1, self.switch, 43)

        self.bind_dns_ip_to_osport(self.switch, 'Vlan442')
        self.bind_dns_ip_to_osport(self.console, 'nic0', porttype='nic-eth', portnum=1)
        self.bind_dns_ip_to_osport(self.power, 'nic0', porttype='nic-eth', portnum=1)

    def add_server(self, server, switchport):
        if switchport > 20:
            switchport -= 20

        if not server in self.rack:
            self.rack.insert(server, self.SWITCHPORT_TO_RU[switchport])
        if server.port_free('nic-eth', 1):
            server.connect_ports('nic-eth', 1, self.switch, switchport)
        if server.port_free('nic-eth', 2):
            server.connect_ports('nic-eth', 2, self.switch, switchport + 20)
        if server.port_free('pwr-nema-5', 1):
            server.connect_ports('pwr-nema-5', 1, self.power, self.SWITCHPORT_TO_PWR[switchport])
        if server.port_free('console-serial', 1):
            server.connect_ports('console-serial', 1, self.console, switchport)

    def get_driver(self, switchport):
        return PenguinServer

class Digg4444RackFactory(Digg5555RackFactory):
    LAYOUT_NAME = '4444'


class Digg53532URackFactory(RackFactory):
    LAYOUT_NAME = '53532U'

    SWITCHPORT_TO_RU = {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
        6: 7, 7: 8, 8: 9, 9: 10, 10: 11,
        11: 13, 12: 14, 13: 15, 14: 16, 15: 17,
        16: 19, 17: 20, 18: 21, 19: [35,36], 20: [33, 34]
    }
    SWITCHPORT_TO_PWR = {
        1: 'bb1', 2: 'bb2', 3: 'bb3', 4: 'bb4', 5: 'bb5',
        6: 'ba1', 7: 'ba2', 8: 'ba3', 9: 'ba4', 10: 'ba5',
        11: 'ab1', 12: 'ab2', 13: 'ab3', 14: 'ab4', 15: 'ab5',
        16: 'aa1', 17: 'aa2', 18: 'aa3', 19: ['aa7', 'ba7'],
        20: ['aa6', 'ba6']
    }

    def __init__(self, name, datacenter):
        self.datacenter = datacenter
        self.rack = clusto.get_or_create(name, APCRack)
        self.switch = clusto.get_or_create(name + '-sw1', Cisco4948)
        self.console = clusto.get_or_create(name + '-ts1', OpenGearCM4148)
        self.power = clusto.get_or_create(name + '-pwr1', PowerTowerXM)

    def connect_ports(self):
        self.rack.set_attr(key='racklayout', value=self.LAYOUT_NAME)

        if not self.rack in self.datacenter:
            self.datacenter.insert(self.rack)

        if not self.power in self.rack:
            self.rack.insert(self.power, 41)
        if self.power.port_free('nic-eth', 1):
            self.power.connect_ports('nic-eth', 1, self.switch, 44)
        if self.power.port_free('console-serial', 1):
            self.power.connect_ports('console-serial', 1, self.console, 44)

        if not self.switch in self.rack:
            self.rack.insert(self.switch, 36)
        if self.switch.port_free('pwr-nema-5', 1):
            self.switch.connect_ports('pwr-nema-5', 1, self.power, 'aa8')
        if self.switch.port_free('console-serial', 1):
            self.switch.connect_ports('console-serial', 1, self.console, 48)

        if not self.console in self.rack:
            self.rack.insert(self.console, 34)
        if self.console.port_free('pwr-nema-5', 1):
            self.console.connect_ports('pwr-nema-5', 1, self.power, 'ab8')
        if self.console.port_free('nic-eth', 1):
            self.console.connect_ports('nic-eth', 1, self.switch, 43)

        self.bind_dns_ip_to_osport(self.switch, 'Vlan442')
        self.bind_dns_ip_to_osport(self.console, 'nic0', porttype='nic-eth', portnum=1)
        self.bind_dns_ip_to_osport(self.power, 'nic0', porttype='nic-eth', portnum=1)

    def add_server(self, server, switchport):
        if not server in self.rack:
            self.rack.insert(server, self.SWITCHPORT_TO_RU[switchport])
        if server.port_free('nic-eth', 1):
            server.connect_ports('nic-eth', 1, self.switch, switchport)
        for i in range(len(SWITCHPORT_TO_PWR[switchport])):
            if server.port_free('pwr-nema-5', i):
                server.connect_ports('pwr-nema-5', i, self.power, self.SWITCHPORT_TO_PWR[switchport])
        if server.port_free('console-serial', 1):
            server.connect_ports('console-serial', 1, self.console, switchport)

    def get_driver(self, switchport):
        if isinstance(self.SWITCHPORT_TO_RU, list) and len(self.SWITCHPORT_TO_RU) == 2:
            return PenguinServer2U
        else:
            return PenguinServer


class Digg54542URackFactory(RackFactory):
    LAYOUT_NAME = '54542U'

    SWITCHPORT_TO_RU = {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
        6: 7, 7: 8, 8: 9, 9: 10, 10: 11,
        11: 13, 12: 14, 13: 15, 14: 16, 15: 17,
        16: 19, 17: 20, 18: 21, 19: 22, 20: [33, 34]
    }
    SWITCHPORT_TO_PWR = {
        1: 'bb1', 2: 'bb2', 3: 'bb3', 4: 'bb4', 5: 'bb5',
        6: 'ba1', 7: 'ba2', 8: 'ba3', 9: 'ba4', 10: 'ba5',
        11: 'ab1', 12: 'ab2', 13: 'ab3', 14: 'ab4', 15: 'ab5',
        16: 'aa1', 17: 'aa2', 18: 'aa3', 19: 'aa4',
        20: ['aa6', 'ba6']
    }

    def __init__(self, name, datacenter):
        self.datacenter = datacenter
        self.rack = clusto.get_or_create(name, APCRack)
        self.switch = clusto.get_or_create(name + '-sw1', Cisco4948)
        self.console = clusto.get_or_create(name + '-ts1', OpenGearCM4148)
        self.power = clusto.get_or_create(name + '-pwr1', PowerTowerXM)

    def connect_ports(self):
        self.rack.set_attr(key='racklayout', value=self.LAYOUT_NAME)

        if not self.rack in self.datacenter:
            self.datacenter.insert(self.rack)

        if not self.power in self.rack:
            self.rack.insert(self.power, 41)
        if self.power.port_free('nic-eth', 1):
            self.power.connect_ports('nic-eth', 1, self.switch, 44)
        if self.power.port_free('console-serial', 1):
            self.power.connect_ports('console-serial', 1, self.console, 44)

        if not self.switch in self.rack:
            self.rack.insert(self.switch, 36)
        if self.switch.port_free('pwr-nema-5', 1):
            self.switch.connect_ports('pwr-nema-5', 1, self.power, 'aa8')
        if self.switch.port_free('console-serial', 1):
            self.switch.connect_ports('console-serial', 1, self.console, 48)

        if not self.console in self.rack:
            self.rack.insert(self.console, 34)
        if self.console.port_free('pwr-nema-5', 1):
            self.console.connect_ports('pwr-nema-5', 1, self.power, 'ab8')
        if self.console.port_free('nic-eth', 1):
            self.console.connect_ports('nic-eth', 1, self.switch, 43)

        self.bind_dns_ip_to_osport(self.switch, 'Vlan442')
        self.bind_dns_ip_to_osport(self.console, 'nic0', porttype='nic-eth', portnum=1)
        self.bind_dns_ip_to_osport(self.power, 'nic0', porttype='nic-eth', portnum=1)

    def add_server(self, server, switchport):
        if not server in self.rack:
            self.rack.insert(server, self.SWITCHPORT_TO_RU[switchport])
        if server.port_free('nic-eth', 1):
            server.connect_ports('nic-eth', 1, self.switch, switchport)
        for i in range(len(SWITCHPORT_TO_PWR[switchport])):
            if server.port_free('pwr-nema-5', i):
                server.connect_ports('pwr-nema-5', i, self.power, self.SWITCHPORT_TO_PWR[switchport])
        if server.port_free('console-serial', 1):
            server.connect_ports('console-serial', 1, self.console, switchport)

    def get_driver(self, switchport):
        if isinstance(self.SWITCHPORT_TO_RU, list) and len(self.SWITCHPORT_TO_RU) == 2:
            return PenguinServer2U
        else:
            return PenguinServer

LAYOUTS = {}

for factory in [Digg4444RackFactory, Digg5555RackFactory, Digg201001RackFactory]:
    LAYOUTS[factory.LAYOUT_NAME] = factory

########NEW FILE########
__FILENAME__ = sysinfo
#!/usr/bin/env python

from paramiko import SSHClient, MissingHostKeyPolicy
from clusto.scripthelpers import init_script
from clusto.drivers import PenguinServer
import clusto

from optparse import OptionParser
from traceback import format_exc
import sys
import re

ifpattern = re.compile('^(?P<type>[a-z]+)(?P<num>[0-9]+)$')

class SilentPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key): pass

def discover_hardware(ip):
    client = SSHClient()

    client.load_system_host_keys()
    client.set_missing_host_key_policy(SilentPolicy())
    client.connect(ip, username='root', timeout=2.0)
    stdout = client.exec_command('cat /proc/partitions')[1].read()

    disks = []
    for line in stdout.split('\n'):
        if not line: continue
        line = [x for x in line.split(' ') if x]
        if not line[0].isdigit(): continue
        if not re.match('^[hs]d[a-z]$', line[3]): continue
        name = line[3]
        blocks = int(line[2])
        blocks *= 1024

        hdinfo = {
            'osname': name,
            'size': str(blocks),
        }

        # Query info from hdparm (IDE and SATA)
        stdout = client.exec_command('hdparm -I /dev/%s' % name)[1].read()
        useful = ('model', 'serial', 'firmware')
        for field in stdout.split('\n'):
            field = field.strip(' \t')
            for u in useful:
                if field.lower().startswith(u):
                    value = field.split(':', 1)[1]
                    hdinfo[u] = value.strip(' \t')

        # Attempt a SCSI query
        if not [x for x in useful if x in hdinfo]:
            stdout = client.exec_command('/usr/bin/sg_inq /dev/%s' % name)[1].read()
            scsi_useful = {
                'Product identification': 'model',
                'Product revision level': 'firmware',
                'Unit serial number': 'serial',
            }
            for field in [x.strip(' \t') for x in stdout.split('\n')]:
                for u in scsi_useful:
                    if field.startswith(u):
                        key = scsi_useful[u]
                        value = field.split(':', 1)[1]
                        hdinfo[key] = value.strip(' \t')
            if [x for x in useful if not x in hdinfo]:
                sys.stdout.write('%s:missing ' % name)

        disks.append(hdinfo)

    xen = False
    stdout = client.exec_command('uname -r')[1].read()
    if stdout.lower().find('-xen-') != -1:
        xen = True

    stdout = client.exec_command('dmidecode -t memory')[1].read()
    memory = []
    mem = {}
    for line in stdout.split('\n'):
        if not line and mem:
            memory.append(mem)
            mem = {}
            continue
        if not line.startswith('\t'): continue

        key, value = line.lstrip('\t').split(': ', 1)
        if key in ('Locator', 'Type', 'Speed', 'Size'):
            mem[key.lower()] = value

    processors = []
    cpu = {}

    if xen:
        sys.stdout.write('xen ')
        sys.stdout.flush()
        stdout = client.exec_command('/usr/sbin/xm info')[1].read()
        for line in stdout.split('\n'):
            line = line.split(':', 1)
            if len(line) != 2:
                continue
            key, value = line
            key = key.strip(' \t')
            value = value.strip(' \t')
            if key == 'nr_cpus':
                cpucount = int(value)
            if key == 'total_memory':
                kmem = int(value)
    else:
        stdout = client.exec_command('/usr/bin/free -m')[1].read()
        stdout = [x for x in stdout.split('\n')[1].split(' ') if x]
        kmem = int(stdout[1])

        stdout = client.exec_command('cat /proc/cpuinfo')[1].read()
        for line in stdout.split('\n'):
            if not line and cpu:
                processors.append(cpu)
                cpu = {}
                continue
            if not line: continue

            key, value = line.split(':', 1)
            key = key.strip(' \t')
            if key in ('model name', 'cpu MHz', 'cache size', 'vendor_id'):
                key = key.lower().replace(' ', '-').replace('_', '-')
                cpu[key] = value.strip(' ')
        cpucount = len(processors)

    serial = client.exec_command('/usr/sbin/dmidecode --string=system-serial-number')[1].read().rstrip('\r\n')
    hostname = client.exec_command('/bin/hostname -s')[1].read().rstrip('\r\n')

    stdout = client.exec_command('/sbin/ifconfig -a')[1].read()
    iface = {}
    for line in stdout.split('\n'):
        line = line.rstrip('\r\n')
        if not line: continue
        line = line.split('  ')
        if line[0]:
            name = line[0]
            iface[name] = []
            del line[0]
        line = [x for x in line if x]
        iface[name] += line

    for name in iface:
        attribs = {}
        value = None
        for attr in iface[name]:
            value = None
            if attr.startswith('Link encap') or \
                attr.startswith('inet addr') or \
                attr.startswith('Bcast') or \
                attr.startswith('Mask') or \
                attr.startswith('MTU') or \
                attr.startswith('Metric'):
                key, value = attr.split(':', 1)
            if attr.startswith('HWaddr'):
                key, value = attr.split(' ', 1)
            if attr.startswith('inet6 addr'):
                key, value = attr.split(': ', 1)
            if not value: continue
            attribs[key.lower()] = value
        iface[name] = attribs

    client.close()

    return {
        'disk': disks,
        'memory': memory,
        'processor': processors,
        'network': iface,
        'system': [{
            'serial': serial,
            'cpucount': cpucount,
            'hostname': hostname,
            'memory': kmem,
            'disk': sum([int(x['size'][:-9]) for x in disks])
        }],
    }

def update_server(server, info):
    server.del_attrs(key='memory')
    server.del_attrs(key='disk')
    server.del_attrs(key='processor')
    server.del_attrs(key='system')

    for itemtype in info:
        if itemtype == 'network': continue
        for i, item in enumerate(info[itemtype]):
            for subkey, value in item.items():
                server.set_attr(key=itemtype, subkey=subkey, value=value, number=i)

    for ifnum in range(0, 2):
        ifname = 'eth%i' % ifnum
        if not ifname in info['network']:
            continue

        #if server.attrs(subkey='mac', value=info['network'].get(ifname, {}).get('hwaddr', '')):
        #    continue
        #server.del_port_attr('nic-eth', ifnum + 1, 'mac')
        server.set_port_attr('nic-eth', ifnum + 1, 'mac', info['network'][ifname]['hwaddr'])

        if 'inet addr' in info['network'][ifname]:
            server.bind_ip_to_osport(info['network'][ifname]['inet addr'], ifname)

def main():
    parser = OptionParser(usage='usage: %prog [options] <object>')
    options, args = parser.parse_args()

    if not args:
        parser.print_help()
        return -1

    try:
        obj = clusto.get_by_name(args[0])
    except LookupError:
        sys.stderr.write('Object does not exist: %s\n' % args[0])
        return -1

    if obj.type != 'server':
        obj = obj.contents()
    else:
        obj = [obj]

    for server in obj:
        if server.type != 'server':
            sys.stdout.write('Not a server\n')
            continue

        #if server.attr_values(key='disk', subkey='serial'):
        #    continue

        sys.stdout.write(server.name + ' ')
        sys.stdout.flush()

        ip = server.get_ips()
        if not ip:
            sys.stdout.write('No IP assigned\n')
            continue
        ip = ip[0]

        try:
            sys.stdout.write('discover_hardware ')
            sys.stdout.flush()
            info = discover_hardware(ip)
        except:
            sys.stdout.write('Unable to discover. %s\n' % sys.exc_info()[1])
            continue

        try:
            sys.stdout.write('update_server ')
            clusto.begin_transaction()
            update_server(server, info)
            clusto.commit()
            sys.stdout.write('.\n')
        except:
            sys.stdout.write('Error updating clusto:\n%s\n' % format_exc())
            clusto.rollback_transaction()
        sys.stdout.flush()

if __name__ == '__main__':
    init_script()

    sys.exit(main())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# clusto documentation build configuration file, created by
# sphinx-quickstart on Wed Feb 24 23:53:25 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinxtogithub']
sphinx_to_github = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'clusto'
copyright = '2010, Digg, Inc.'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5.27'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

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

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'clustodoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
#latex_documents = [
#  ('index', 'clusto.tex', 'clusto Documentation',
#   'Digg, Inc.', 'manual'),
#]

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

########NEW FILE########
__FILENAME__ = clustoScript
import libDigg
import csParse
import time
import os

class Script:

    def __init__(self,cs):
        """ create the task object?"""

        self.csDict = cs.clusterScript

    def createChunks(self):

        mydict = self.csDict
        chunks = []

        for keys in mydict.keys():
            if keys == "globalHeader":
                globals = mydict[keys]

        for objects in mydict.values():
            chunk = Chunk(objects)
            chunk.setGlobals(globals)
            chunks.append(chunk)

        self.chunks = chunks

    def resolveChunks(self):

        # resolve the chunk and add the resolved Task to the Chunk
        # I'm faking it here until the resolver is done
        # should this be here, or in Chunks class?
            

        tasks = []
        for c in self.chunks:
            # skip the special header chunk
            if c.tasknum == 0:
                continue
            # make up some bullshit resolved tasks for now and attach them to a chunk
            # even though the real parsed in task might not look anything like this

            for i in 1,2,3:
                mydict = {'name':'testing chunk','body':['echo "blah blah"\n', 'ls /trlkaijs'], 'shell':'bash', 'services_include':'32G', 'runmode':'hostwithrole', 'task':2, 'cluster_root':'/foo', 'services':'foo1-3', 'mykey':'myvalue', 'ip':'127.0.0.1', 'transport':'ssh', 'onError':'continue' , 'maxParallel':'10' , 'debug':0,'verbose':1}
                t = Task(i,mydict)
                tasks.append(t)

            c.tasks = tasks
            tasks = []

class Chunk:

    def __init__(self,object):

        self.chunk = object
        self.tasknum = object['task']
        self._setDefaults()

    def _setDefaults(self):
    
        # add other defaults here. maybe get them from the database?
        # FIXME default user root? no good
        defaults = { 'user':'root' , 'shell':'bash' ,'transport':'ssh' , 'onError':'continue' , 'maxParallel':'10', 'verbose':'1' }
        
        mydict = self.chunk

        # if the key does not exist in the task, add a default key
        for k in defaults.keys():
            if not mydict.has_key(k):
                mydict[k]=defaults[k]    

    def setGlobals(self,globals):
        """take the globals dict and copy in any values that are missing or not overridden"""
        mydict = self.chunk

        for k in globals.keys():
            if not mydict.has_key(k):
                mydict[k]=globals[k]


class Task:

    def __init__(self,num,dict):
        # this is not real for now. the resolver will ultimatley have to do the lifting here to 
        # create the task objects when they are fully resolved.
        # that's why this looks so sad

        self.tasknum=num
        self.task=dict

class QueueRunner:

    def __init__(self,chunk):
        """takes a chunk that has resolved tasks in a list attached to it"""
        self.chunk = chunk 
        t = chunk.tasks[0]

        # set some defaults at the queue level
        # we'll just take them from the first task

        self.shell = t.task['shell']
        self.onError = t.task['onError']
        self.transport = t.task['transport']
        self.maxParallel = t.task['maxParallel']
        self.debug = t.task['debug']
        self.name = t.task['name']
        self.verbose = t.task['verbose']
        self.user = t.task['user']

    def writeTasks(self):

        """write out each task into a tempfile"""
        for t in self.chunk.tasks:
            fname = libDigg.tempFile()
            t.tempFile = fname
            # sleep a tiny bit to make sure the filename is unique
            time.sleep(.25)
            f = libDigg.fopen(fname,'w')
            body = t.task['body']
            for line in body:
                f.write(line)
            status = f.close()

            if status != None:
                print "writing temp file failed: %s" % status

    def execute(self):

        """copy each temp script to the proper host and execute each task"""

        for t in self.chunk.tasks:

            if not self.transport == "ssh":
                print "transport method %s not yet implimented" % self.transport    
                sys.exit()

            # note that this is not any kind of real fork (yet)
            # and is really only doing the tasks serially
            # also note that there is no kind of timeout alarm set 
            # to kill problem tasks

            chunknum = self.chunk.tasknum
            ip = t.task['ip']
            runningTasks = 0

            if runningTasks < self.maxParallel:

                runningTasks+=1
                if not self.verbose == 0:
                    print "starting chunk %s task %s on %s" % (chunknum,t.tasknum,ip)

                # pass the task to the queue
                self._queue(t)
            else:
                # is this the right way to do this?
                if not self.verbose == 0:
                    print "task %s waiting for queue to flush" % t.tasknum
                os.sleep(30)

            runningTasks-=1

    def _queue(self,t):    

        # first, push out each script            
        host = t.task['ip']
        user = "root"
        print "scp %s %s@%s:/tmp" % (t.tempFile,user,host)
        tmpCmd = "scp %s %s@%s:/tmp" % (t.tempFile,user,host)
        tmpPipe = os.popen(tmpCmd)
        t.tmpCopy = tmpPipe.readlines()
        tmpExit = tmpPipe.close()
        ip = t.task['ip']
                        
        if tmpExit == None:
            t.tmpExit = 0
        else:
            t.tmpExit = tmpExit

        if not t.tmpExit == 0:
            print "copying script to %s unsuccessful" % ip
            print t.tmpCopy
            print t.tmpExit
            os.exit()

        # then run each task
        cmd = "ssh %s@%s %s %s " % (self.user,host,self.shell,t.tempFile)
        cmdPipe = os.popen(cmd)
        t.cmdRun = cmdPipe.readlines()
        t.cmdExit = cmdPipe.close()

        if t.cmdExit == None:
            t.cmdExit = 0
        else:
            t.cmdExit = tmpExit

        if not t.cmdExit == 0:
            print "running script on %s unsuccessful: %s" % (ip,t.tempFile)
            print t.cmdRun
            print t.cmdExit
            if not self.onError == "continue":
                os.exit()

        if not self.verbose == 0:
            for line in t.cmdRun:
                print line

    def cleanUp(self):

        """if debug is off, delete the tempfiles on the local machine"""

        if self.debug == 0:
            for t in self.chunk.tasks:
                os.unlink(t.tempFile)


if __name__ == '__main__':

    filename = "clusterscript.cs"
    cs = parseCs.parseCsFile(filename)
    cs.parseCsHeader()
    cs.parseTasks()

    script = Script(cs)
    script.createChunks()
    script.resolveChunks()

    for chunk in script.chunks:

        # skip the first chunk
        # which is just the global header data
        if chunk.tasknum == 0:
            continue
        q = QueueRunner(chunk)
        q.writeTasks()
        q.execute()
        #q.cleanUp()
        
    

########NEW FILE########
__FILENAME__ = clustodriver

TYPELIST = {}
DRIVERLIST = {}
RESERVEDATTRS = {}

class ClustoDriver(type):
    """
    Metaclass for all clusto drivers
    """
    def __init__(cls, name, bases, dct):

        if not hasattr(cls, '_driver_name'):
            raise DriverException("Driver %s missing _driver_name attribute"
                                  % cls.__name__)

        if cls._driver_name in DRIVERLIST:
            raise KeyError("class '%s' is trying to add the driver_name '%s' "
                           "to the driver list but that name is already "
                           "claimed by the '%s' class."
                           % (cls.__name__,
                              cls._driver_name,
                              DRIVERLIST[cls._driver_name].__name__))
        

        DRIVERLIST[cls._driver_name] = cls
        TYPELIST[cls._clusto_type] = cls

        # setup properties
        if not isinstance(cls._properties, dict):
            raise TypeError('_properties of %s is not a dict type.',
                            cls.__name__)
        

        super(ClustoDriver, cls).__init__(name, bases, dct)


########NEW FILE########
__FILENAME__ = clustometa


import clusto
from clusto.drivers.base import Driver
from clusto.schema import VERSION

# incrementing the first number means a major schema change
# incrementing the second number means a change in a driver's storage details


class ClustoMeta(Driver):
    """
    Holds meta information about the clusto database
    """

    _properties = {'schemaversion':None}

    _clusto_type = "clustometa"
    _driver_name = "clustometa"


    def __new__(cls):

        try:
            cls.__singleton = clusto.get_by_name(cls._driver_name)
        except LookupError:
            cls.__singleton = Driver.__new__(cls, cls._driver_name)


        return cls.__singleton


    def __init__(self): #, name=None, entity=None, *args, **kwargs):

        if not hasattr(self, 'entity'):
            super(ClustoMeta, self).__init__(self._driver_name)
            self.schemaversion = VERSION




        

########NEW FILE########
__FILENAME__ = controller
class Controller(object): pass

########NEW FILE########
__FILENAME__ = device
from clusto.drivers.base import Driver
import sys

class Device(Driver):

    _properties = {'model':None,
                   'serialnum':None,
                   'manufacturer':None}

    _clustotype = "device"
    _driver_name = "device"


    @classmethod
    def get_by_serial_number(self, serialnum):
        pass

    def _get_hostname(self):
        """return a hostname set for this device or its entity name"""

        hostname = self.attrs("hostname")

        if hostname:
            return hostname[0].value
        else:
            return self.entity.name

    def _set_hostname(self, name):

        self.set_attr("hostname", value=name)

    hostname = property(_get_hostname, _set_hostname)

    @property
    def fqdns(self):
        """return the fully qualified domain names for this device"""

        return self.attr_values("fqdn")


    def add_fqdn(self, fqdn):
        """add a fully qualified domain name"""

        if not self.has_attr("fqdn", number=True, value=fqdn):
            self.add_attr("fqdn", number=True, value=fqdn)

    def remove_fqdn(self, fqdn):
        """remove a fully qualified domain name"""

        self.del_attrs("fqdn", number=True, value=fqdn)

    def _power_captcha(self):
        while True:
            sys.stdout.write('Are you sure you want to reboot %s (yes/no)? ' % self.name)
            line = sys.stdin.readline().rstrip('\r\n')
            if line == 'yes':
                return True
            if line == 'no':
                return False
            sys.stdout.write('"yes" or "no", please\n')

    def power_on(self, captcha=True):
        if captcha and not self._power_captcha():
            return

        ports_set = 0
        for porttype, ports in self.port_info.items():
            if not porttype.startswith('pwr-'): continue
            for portnum, port in ports.items():
                if not port['connection']: continue
                port['connection'].set_power_on(porttype, port['otherportnum'])
                ports_set += 1
        return ports_set

    def power_off(self, captcha=True):
        if captcha and not self._power_captcha():
            return

        ports_set = 0
        for porttype, ports in self.port_info.items():
            if not porttype.startswith('pwr-'): continue
            for portnum, port in ports.items():
                if not port['connection']: continue
                port['connection'].set_power_off(porttype, port['otherportnum'])
                ports_set += 1
        return ports_set

    def power_reboot(self, captcha=True):
        if captcha and not self._power_captcha():
            return

        ports_rebooted = 0
        for porttype, ports in self.port_info.items():
            if not porttype.startswith('pwr-'): continue
            for portnum, port in ports.items():
                if not port['connection']: continue
                port['connection'].reboot(porttype, port['otherportnum'])
                ports_rebooted += 1
        return ports_rebooted

    def console(self, ssh_user='root'):
        console = self.port_info['console-serial'][1]
        if not console['connection']:
            sys.stderr.write('No console connected to %s console-serial:1\n' % self.name)
            sys.stderr.flush()
            return

        if not hasattr(console['connection'], 'console'):
            sys.stderr.write('No console method on %s\n' % console.name)
            sys.stderr.flush()
            return

        console['connection'].connect('console-serial', console['otherportnum'], ssh_user)

########NEW FILE########
__FILENAME__ = driver
"""Driver class

A Driver provides an interface to an Entity and its Attributes.
"""

import re
import itertools
import logging

import clusto
from clusto.schema import *
from clusto.exceptions import *

from clusto.drivers.base.clustodriver import *


class Driver(object):
    """Base Driver.

    The Driver class provides a proxy interface for managing and Entity and
    its Attributes. It provides many helper functions includeing attribute
    setters and accessors, attribute querying, and a handful of conventions.

    Every driver defines a _clusto_type and a _driver_name member variable.
    Upon creation these become the type and driver for the Entity and provides
    a mechanism for choosing the correct driver for a given Entity.

    A Driver can be created by passing either the name (a string) for a new
    Entity you'd like to create, an already instantiated Entity object, or a
    Driver object (which has already been instantiated and is managing an
    Entity).

    If a _properties member dictionary is defined they will be treated as
    default values for the given Entity attributes as well as exposed via a
    simpler mydriver.key access pattern.  So for:

    >>> class MyDriver(Driver):
    >>>    ...
    >>>    _properties = {'propA': 10, 'propB': "default1"}
    >>>    ...

    >>> d = MyDriver('foo')
    >>> d.propA == 10
    True

    >>> d.propB == "default1"
    True

    Only properties with non-None default values are set in the clusto db at
    initial instantiation time (when creating a brand new entity).

    >>> d.propA = 54
    >>> d.propA == 54
    True

    Several conventions are also exposed via the Driver interface.

    """

    __metaclass__ = ClustoDriver

    _clusto_type = "generic"
    _driver_name = "entity"

    _properties = dict()


    @property
    def type(self):
        return self.entity.type

    @property
    def driver(self):
        return self.entity.driver

    def __new__(cls, name_driver_entity, **kwargs):

        if isinstance(name_driver_entity, Driver):
            return name_driver_entity
        else:
            return object.__new__(cls)

    def __init__(self, name_driver_entity, **kwargs):

        if not isinstance(name_driver_entity, (str, unicode, Entity, Driver)):
            raise TypeError("First argument must be a string, "
                            "Driver, or Entity.")

        if isinstance(name_driver_entity, Driver):
            return

        if isinstance(name_driver_entity, Entity):

            self.entity = name_driver_entity
            self._choose_best_driver()
            return
        elif isinstance(name_driver_entity, (str, unicode)):

            try:
                existing = clusto.get_by_name(name_driver_entity)
            except LookupError, x:
                existing = None

            if existing:
                raise NameException("Driver with the name %s already exists."
                                    % (name_driver_entity))


            self.entity = Entity(name_driver_entity,
                                 driver=self._driver_name,
                                 clustotype=self._clusto_type)


        else:
            raise TypeError("Could not create driver from given arguments.")

        for key, val in self._properties.iteritems():
            if key in kwargs:
                val = kwargs[key]
            if val is None:
                continue
            setattr(self, key, val)


    def __eq__(self, other):

        if isinstance(other, Entity):
            return self.entity.name == other.name
        elif isinstance(other, Driver):
            return self.entity.name == other.entity.name
        else:
            return False

    def __repr__(self):

        s = "%s(name=%s, type=%s, driver=%s)"

        return s % (self.__class__.__name__, self.entity.name,
                    self.entity.type, self.entity.driver)

    def __cmp__(self, other):

        if hasattr(other, 'name'):
            return cmp(self.name, other.name)
        elif other is None:
            return 1
        else:
            raise TypeError("Cannot compare %s with %s", type(self), type(other))

    def __hash__(self):
        return hash(self.entity.name)

    def __contains__(self, other):
        return self.has_attr(key="_contains", value=other)

    def _choose_best_driver(self):
        """
        Examine the attributes of our entity and set the best driver class and
        mixins.
        """

        self.__class__ = DRIVERLIST[self.entity.driver]



    name = property(lambda x: x.entity.name)


    def _check_attr_name(self, key):
        """
        check to make sure the key does not contain invalid characters
        raise NameException if fail.
        """

        if not isinstance(key, basestring):
            raise TypeError("An attribute name must be a string.")

        if not re.match('^[A-Za-z_]+[0-9A-Za-z_-]*$', key):

            raise NameException("Attribute name %s is invalid. "
                                "Attribute names may not contain periods or "
                                "comas." % key)


    def __getattr__(self, name):
        if name in self._properties:
            attr = self.attr_query(name, subkey='property')
            if not attr:
                return self._properties[name]
            else:
                return attr[0].value
        else:
            raise AttributeError("Attribute %s does not exist." % name)


    def __setattr__(self, name, value):

        if name in self._properties:
            self.set_attr(name, value, subkey='property')
        else:
            object.__setattr__(self, name, value)

    @classmethod
    def ensure_driver(self, obj, msg=None):
        """Ensure that the given argument is a Driver.

        If the object is an Entity it will be turned into a Driver and then
        returned.  If it's a Driver it will be returned unaffected.  Otherwise
        a TypeError is raised with either a generic or given message.
        """

        if isinstance(obj, Entity):
            d = Driver(obj)
        elif isinstance(obj, Driver):
            d = obj
        else:
            if not msg:
                msg = "Not a Driver."
            raise TypeError(msg)

        return d

    @classmethod
    def do_attr_query(cls, key=(), value=(), number=(),
                    subkey=(), ignore_hidden=True, sort_by_keys=False,
                    glob=False, count=False, querybase=None, return_query=False,
                    entity=None):
        """Does queries against all Attributes using the DB."""

        clusto.flush()
        if querybase:
            query = querybase
        else:
            query = Attribute.query()

        ### This is bunk, gotta fix it
        if isinstance(cls, Driver):
            query = query.filter(and_(Attribute.entity_id==Entity.entity_id,
                                      Entity.driver == cls._driver_name,
                                      Entity.type == cls._clusto_type))

        if entity:
            query = query.filter_by(entity_id=entity.entity_id)

        if key is not ():
            if glob:
                query = query.filter(Attribute.key.like(key.replace('*', '%')))
            else:
                query = query.filter_by(key=key)

        if subkey is not ():
            if glob and subkey:
                query = query.filter(Attribute.subkey.like(subkey.replace('*', '%')))
            else:
                query = query.filter_by(subkey=subkey)

        if value is not ():
            typename = Attribute.get_type(value)

            if typename == 'relation':
                if isinstance(value, Driver):
                    value = value.entity.entity_id
                query = query.filter_by(relation_id=value)

            else:
                query = query.filter_by(**{typename+'_value':value})

        if number is not ():
            if isinstance(number, bool) or number is None:
                if number == True:
                    query = query.filter(Attribute.number != None)
                else:
                    query = query.filter(Attribute.number == None)
            elif isinstance(number, (int, long)):
                query = query.filter_by(number=number)

            else:
                raise TypeError("number must be either a boolean or an integer.")

        if ignore_hidden and ((key and not key.startswith('_')) or key is ()):
            query = query.filter(not_(Attribute.key.like('\\_%', escape='\\')))

        if sort_by_keys:
            query = query.order_by(Attribute.key)

        if count:
            return query.count()

        if return_query:
            return query

        return query.all()

    def attr_query(self, *args, **kwargs):
        """Queries all attributes of *this* entity using the DB."""

        kwargs['entity'] = self.entity

        return self.do_attr_query(*args, **kwargs)

    @classmethod
    def attr_filter(cls, attrlist, key=(), value=(), number=(),
                   subkey=(), ignore_hidden=True,
                   sort_by_keys=True,
                   regex=False,
                   clusto_types=None,
                   clusto_drivers=None,
                   ):
        """Filter attribute lists. (Uses generator comprehension)

        Given a list of Attributes filter them based on exact matches of key,
        number, subkey, value.

        There are some special cases:

        if number is True then the number variable must be non-null. if
        number is False then the number variable must be null.

        if ignore_hidden is True (the default) then filter out keys that begin
        with an underscore, if false don't filter out such keys.  If you
        specify a key that begins with an underscore as one of the arguments
        then ignore_hidden is assumed to be False.

        if sort_by_keys is True then attributes are returned sorted by keys,
        otherwise their order is undefined.

        if regex is True then treat the key, subkey, and value query
        parameters as regular expressions.

        clusto_types is a list of types that the entities referenced by
        relation attributes must match.

        clusto_drivers is a list of drivers that the entities referenced by
        relation attributes must match.
        """


        result = attrlist

        def subfilter(attrs, val, name):

            if regex:
                testregex = re.compile(val)
                result = (attr for attr in attrs
                          if testregex.match(getattr(attr, name)))

            else:
                result = (attr for attr in attrs
                          if getattr(attr, name) == val)


            return result

        parts = ((key, 'key'), (subkey, 'subkey'), (value, 'value'))
        argattr = ((val,name) for val,name in parts if val is not ())

        for v, n in argattr:
            result = subfilter(result, v, n)


        if number is not ():
            if isinstance(number, bool) or number is None:
                if number:
                    result = (attr for attr in result if attr.number is not None)
                else:
                    result = (attr for attr in result if attr.number is None)

            elif isinstance(number, (int, long)):
                result = (attr for attr in result if attr.number == number)

            else:
                raise TypeError("number must be either a boolean or an integer.")


        if value:
            result = (attr for attr in result if attr.value == value)


        if key and key.startswith('_'):
            ignore_hidden = False

        if ignore_hidden:
            result = (attr for attr in result if not attr.key.startswith('_'))

        if clusto_drivers:
            cdl = [clusto.get_driver_name(n) for n in clusto_drivers]
            result = (attr for attr in result if attr.is_relation and attr.value.entity.driver in cdl)

        if clusto_types:
            ctl = [clusto.get_type_name(n) for n in clusto_types]
            result = (attr for attr in result if attr.is_relation and attr.value.entity.type in ctl)

        if sort_by_keys:
            result = sorted(result)


        return list(result)

    def _itemize_attrs(self, attrlist):
        return [(x.keytuple, x.value) for x in attrlist]

    def attrs(self, *args, **kwargs):
        """Return attributes for this entity.

        (filters whole attribute list as opposed to querying the db directly)
        """

        if 'merge_container_attrs' in kwargs:
            merge_container_attrs = kwargs.pop('merge_container_attrs')
        else:
            merge_container_attrs = False

        ignore_memcache = False
        if 'ignore_memcache' in kwargs:
            ignore_memcache = kwargs.pop('ignore_memcache')

        if clusto.SESSION.memcache and not ignore_memcache:
            logging.debug('Pulling info from memcache when possible for %s' % self.name)
            k = None
            if 'key' in kwargs:
                k = kwargs['key']
            else:
                if len(args) > 1:
                    k = args[0]
            if k:
#               This is hackish, need to find another way to know if we should cache things or not
                if not k.startswith('_') and k != 'ip':
                    if 'subkey' in kwargs and kwargs['subkey'] is not None:
                        memcache_key = str('%s.%s.%s' % (self.name, k, kwargs['subkey']))
                    else:
                        memcache_key = str('%s.%s' % (self.name, k))
                    logging.debug('memcache key: %s' % memcache_key)
                    attrs = clusto.SESSION.memcache.get(memcache_key)
                    if not attrs:
                        attrs = self.attr_filter(self.entity.attrs, *args, **kwargs)
                        if attrs:
                            clusto.SESSION.memcache.set(memcache_key, attrs)
                else:
                    attrs = self.attr_filter(self.entity.attrs, *args, **kwargs)
            else:
                logging.debug('We cannot cache attrs without a key at least')
                attrs = self.attr_filter(self.entity.attrs, *args, **kwargs)
        else:
            attrs = self.attr_filter(self.entity.attrs, *args, **kwargs)

        if merge_container_attrs:
            kwargs['merge_container_attrs'] = merge_container_attrs
            kwargs['ignore_memcache'] = ignore_memcache
            for parent in self.parents():
                attrs.extend(parent.attrs(*args,  **kwargs))

        return attrs

    def attr_values(self, *args, **kwargs):
        """Return the values of the attributes that match the given arguments"""

        return [k.value for k in self.attrs(*args, **kwargs)]

    def attr_value(self, *args, **kwargs):
        """Return a single value for the given arguments or the default if none exist

        extra parameters:
          default - the default value to return if none exist
        """

        if 'default' in kwargs:
            default = kwargs.pop('default')
        else:
            default = None

        vals = self.attr_values(*args, **kwargs)

        if vals:
            if len(vals) != 1:
                raise DriverException("args match more than one value")
            return vals[0]
        else:
            return default

    def references(self, *args, **kwargs):
        """Return the references to this Thing. The references are attributes.

        Accepts the same arguments as attrs().

        The semantics of clusto_types and clusto_drivers changes to match the
        clusto_type or clusto_driver of the Entity that owns the attribute as
        opposed to the Entity the attribute refers to.
        """


        clusto_drivers = kwargs.pop('clusto_drivers', None)

        clusto_types = kwargs.pop('clusto_types', None)

        result = self.attr_filter(self.entity.references, *args, **kwargs)

        if clusto_drivers:
            cdl = [clusto.get_driver_name(n) for n in clusto_drivers]
            result = (attr for attr in result if attr.entity.driver in cdl)

        if clusto_types:
            ctl = [clusto.get_type_name(n) for n in clusto_types]
            result = (attr for attr in result if attr.entity.type in ctl)


        return list(result)

    def referencers(self, *args, **kwargs):
        """Return the Things that reference _this_ Thing.

        Accepts the same arguments as references() but adds an instanceOf filter
        argument.
        """

        refs = [Driver(a.entity) for a in sorted(self.references(*args, **kwargs),
                                                 lambda x,y: cmp(x.attr_id,
                                                                 y.attr_id))]

        return refs


    def attr_keys(self, *args, **kwargs):

        return [x.key for x in self.attrs(*args, **kwargs)]

    def attr_key_tuples(self, *args, **kwargs):

        return [x.keytuple for x in self.attrs(*args, **kwargs)]

    def attr_items(self, *args, **kwargs):
        return self._itemize_attrs(self.attrs(*args, **kwargs))

    def add_attr(self, key, value=(), number=(), subkey=()):
        """add a key/value to the list of attributes

        if number is True, create an attribute with the next available
        otherwise number just gets passed to the Attribute constructor so it
        can be an integer or an sqlalchemy expression

        An optional subkey can also be specified. Subkeys don't affect
        numbering by default.
        """

        if isinstance(key, Attribute):
            raise Exception("Unsupported Operation.  You can no longer add an attribute directly")

        self._check_attr_name(key)
        if subkey:
            self._check_attr_name(subkey)

        if isinstance(value, Driver):
            value = value.entity

        if (number is ()) or (number is False):
            number = None
        if subkey is ():
            subkey = None


        self.expire(key=key)
        return self.entity.add_attr(key, value, subkey=subkey, number=number)


    def del_attrs(self, *args, **kwargs):
        "delete attribute with the given key and value optionally value also"

        clusto.flush()
        try:
            clusto.begin_transaction()
            for i in self.attr_query(*args, **kwargs):
                i.delete()
            clusto.commit()
            self.expire(*args, **kwargs)
        except Exception, x:
            clusto.rollback_transaction()
            raise x


    def set_attr(self, key, value, number=False, subkey=None):
        """replaces all attributes with the given key"""
        self._check_attr_name(key)

        attrs = self.attrs(key=key, number=number, subkey=subkey)

        if len(attrs) > 1:
            raise DriverException("cannot set an attribute when args match more than one value")

        else:
            if len(attrs) == 1:
                if attrs[0].value == value:
                    return attrs[0]
                self.del_attrs(key=key, number=number, subkey=subkey)

            attr = self.add_attr(key, value, number=number, subkey=subkey)

        return attr


    def expire(self, *args, **kwargs):
        """Expires the memcache value (if using memcache) of this object"""

        key = None
        if 'key' in kwargs:
            key = kwargs['key']
        subkey = None
        if 'subkey' in kwargs:
            subkey = kwargs['subkey']
        if clusto.SESSION.memcache:
            attrs = self.attrs(key=key, subkey=subkey)
            memcache_keys = []
            for attr in attrs:
                mk = self.name
                mk += '.%s' % attr.key
                if subkey is None:
                    memcache_keys.append(str(mk))
                if attr.subkey:
                    mk += '.%s' % attr.subkey
                memcache_keys.append(str(mk)) 
            memcache_keys = set(memcache_keys)
            for mk in memcache_keys:
                logging.debug('Expiring %s' % mk)
                clusto.SESSION.memcache.delete(mk)
        else:
            logging.info('Not using memcache, not expiring anything.')

    def has_attr(self, *args, **kwargs):
        """return True if this list has an attribute with the given key"""

        if self.attr_query(*args, **kwargs):
            return True

        return False

    def insert(self, thing):
        """Insert the given Enity or Driver into this Entity.  Such that:

        >>> A.insert(B)
        >>> (B in A)
        True


        """

        d = self.ensure_driver(thing,
                              "Can only insert an Entity or a Driver. "
                              "Tried to insert %s." % str(type(thing)))


        parent = thing.parents()

        if parent:
            raise TypeError("%s is already in %s and cannot be inserted into %s."
                            % (d.name, parent[0].entity.name, self.name))

        self.add_attr("_contains", d, number=True)

    def remove(self, thing):
        """Remove the given Entity or Driver from this Entity. Such that:

        >>> A.insert(B)
        >>> B in A
        True
        >>> A.remove(B)
        >>> B in A
        False

        """
        if isinstance(thing, Entity):
            d = Driver(Entity)
        elif isinstance(thing, Driver):
            d = thing
        else:
            raise TypeError("Can only remove an Entity or a Driver. "
                            "Tried to remove %s." % str(type(thing)))


        self.del_attrs("_contains", d, ignore_hidden=False)

    def content_attrs(self, *args, **kwargs):
        """Return the attributes referring to this Thing's contents

        """

        attrs = self.attrs("_contains", *args, **kwargs)

        return attrs

    def contents(self, *args, **kwargs):
        """Return the contents of this Entity.  Such that:

        >>> A.insert(B)
        >>> A.insert(C)
        >>> A.contents()
        [B, C]

        """

        if 'search_children' in kwargs:
            search_children = kwargs.pop('search_children')
        else:
            search_children = False

        contents = [attr.value for attr in self.content_attrs(*args, **kwargs)]
        if search_children:
            for child in (attr.value for attr in self.content_attrs()):
                kwargs['search_children'] = search_children
                contents.extend(child.contents(*args, **kwargs))

        return contents

    def parents(self, **kwargs):
        """Return a list of Things that contain _this_ Thing. """

        search_parents = kwargs.pop('search_parents', False)

        if search_parents:
            parents=self.parents(**kwargs)
            allparents = self.parents()
            for thing in allparents:
                allparents.extend(thing.parents())

            for thing in allparents:
                parents.extend(thing.parents(**kwargs))
        else:
            parents = self.referencers('_contains', **kwargs)

        return parents

    def siblings(self, parent_filter=None, parent_kwargs=None,
                 additional_pools=None, **kwargs):
        """Return a list of Things that have the same parents as me.

        parameters:
           parent_filter - a function used to filter out unwanted parents
           parent_kwargs - arguments to be passed to self.parents()
           additional_pools - a list of additional pools to use as sibling parents
           **kwargs - arguments to clusto.get_from_pools()
        """

        if parent_kwargs is None:
            parent_kwargs = dict(clusto_types=[clusto.drivers.Pool])

        parents = self.parents(**parent_kwargs)

        if parent_filter:
            parents = filter(parent_filter, parents)

        if additional_pools:
            parents.extend(additional_pools)

        return [s for s in clusto.get_from_pools(parents, search_children=False, **kwargs) if s != self]

    @classmethod
    def get_by_attr(cls, *args, **kwargs):
        """Get list of Drivers that have by attributes search """

        attrlist = cls.do_attr_query(*args, **kwargs)

        objs = [Driver(x.entity) for x in attrlist]

        return objs



    @property
    def name(self):
        return self.entity.name

########NEW FILE########
__FILENAME__ = location

from clusto.drivers.base import Driver

class Location(Driver):

    _clusto_type = "location"
    _driver_name = "location"



########NEW FILE########
__FILENAME__ = resourcemanager

import clusto
from clusto.schema import select, and_, ATTR_TABLE, Attribute, func, Counter
from clusto.drivers.base import Driver, ClustoMeta
from clusto.exceptions import ResourceTypeException, ResourceNotAvailableException, ResourceException



class ResourceManager(Driver):
    """The ResourceManager driver should be subclassed by a driver that will
    manage a resource such as IP allocation, MAC Address lists, etc.

    This base class just allocates unique integers.

    Resources are attributes on Entities that are managed by a ResourceManger.
    The implementation has the following properties:

    1. The Entity being assigned the resource gets an attribute who's key is
    defined by the resource manager, a number assigned by the resource manager
    (sometimes related to the resource being allocated), and a value which is
    a representation of the resource.

    2. The Entity gets an additional attribute who's key, and number match the
    allocated resource, but with subkey='manager', and value that is a
    reference to the resource manager assigning the resource.

    Any additional attributes with same attribute key and number are
    considered part of the resource and can be managed by the resource
    manager.
    """
    

    _clusto_type = "resourcemanager"
    _driver_name = "resourcemanager"

    _attr_name = "resource"
    _record_allocations = True
    


        
    def allocator(self, thing=None):
        """return an unused resource from this resource manager"""

        raise NotImplemented("No allocator implemented for %s you must explicitly specify a resource."
                             % self.name)


    def ensure_type(self, resource, number=True, thing=None):
        """checks the type of a given resourece

        if the resource is valid return it and optionally convert it to
        another format.  The format it returns has to be compatible with 
        attribute naming 
        """
        return (resource, number)

    def get_resource_number(self, thing, resource):
        """Get the number for a resource on a given entity."""
        
        resource, number = self.ensure_type(resource, thing=thing)
        
        attrs = thing.attrs(self._attr_name, value=resource)

        if attrs:
            return attrs[0].number
        else:
            raise ResourceException("%s isn't assigned resource %s"
                                    % (thing.name, str(resource)))

    def get_resource_attr_values(self, thing, resource, key, number=True):
        """Get the value for the attrs on the resource assigned to a given entity matching the given key."""
        
        return [x.value for x in self.get_resource_attrs(thing, resource,
                                                         key, number)]
    
    def get_resource_attrs(self, thing, resource, key=(), number=True):
        """Get the Attributes for the attrs on the resource assigned to a given enttiy matching the given key."""
        
        resource, number = self.ensure_type(resource, number, thing=thing)
        
        return thing.attrs(self._attr_name, number=number, subkey=key)
    
    def add_resource_attr(self, thing, resource, key, value, number=True):
        """Add an Attribute for the resource assigned to a given entity setting the given key and value"""
        
        resource, number = self.ensure_type(resource, number, thing=thing)

        attr = thing.add_attr(self._attr_name, number=number, subkey=key, value=value)
        return attr

    def set_resource_attr(self, thing, resource, key, value, number=True):
        """Set an Attribute for the resource assigned to a given entity with the given key and value"""
        
        resource, number = self.ensure_type(resource, number, thing=thing)
        attr = thing.set_attr(self._attr_name, number=number, subkey=key, value=value)

        return attr

    def del_resource_attr(self, thing, resource, key, value=(), number=True):
        """Delete an Attribute for the resource assigned to a given entity matching the given key and value"""
        
        resource, number = self.ensure_type(resource, number, thing=thing)
        thing.del_attrs(self._attr_name, number=number, subkey=key, value=value)

    def additional_attrs(self, thing, resource, number):
        pass
    
    def allocate(self, thing, resource=(), number=True, force=False):
        """allocates a resource element to the given thing.

        resource - is passed as an argument it will be checked 
                   before assignment.  

        refattr - the attribute name on the entity that will refer back
                  this resource manager.

        returns the resource that was either passed in and processed 
        or generated.
        """

        try:
            clusto.begin_transaction()
            if not isinstance(thing, Driver):
                raise TypeError("thing is not of type Driver")

            if resource is ():
                # allocate a new resource
                resource, number = self.allocator(thing)

            else:
                resource, number = self.ensure_type(resource, number, thing)
                if not force and not self.available(resource, number, thing):
                    raise ResourceException("Requested resource is not available.")

            if self._record_allocations:
                if number == True:
                    c = Counter.get(ClustoMeta().entity, self._attr_name)
                    attr = thing.add_attr(self._attr_name,
                                          resource,
                                          number=c.value
                                          )
                    c.next()
                else:
                    attr = thing.add_attr(self._attr_name, resource, number=number)
                    
                clusto.flush()

                a=thing.add_attr(self._attr_name,
                            self.entity,
                            number=attr.number,
                            subkey='manager',
                            )

                clusto.flush()
                self.additional_attrs(thing, resource, attr.number)
                
            else:
                attr = None
            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x

        return attr #resource

    def deallocate(self, thing, resource=(), number=True):
        """deallocates a resource from the given thing."""


        clusto.begin_transaction()
        try:
            if resource is ():                      
                for res in self.resources(thing):
                    thing.del_attrs(self._attr_name, number=res.number)

            elif resource and not self.available(resource, number):
                resource, number = self.ensure_type(resource, number)

                res = thing.attrs(self._attr_name, self, subkey='manager', number=number)
                for a in res: 
                    thing.del_attrs(self._attr_name, number=a.number)
                    
            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x
    def available(self, resource, number=True, thing=None):
        """return True if resource is available, False otherwise.
        """

        resource, number = self.ensure_type(resource, number)

        if self.owners(resource, number):
            return False

        return True
            

    def owners(self, resource, number=True):
        """return a list of driver objects for the owners of a given resource.
        """

        resource, number = self.ensure_type(resource, number)

        return Driver.get_by_attr(self._attr_name, resource, number=number)

    @classmethod
    def resources(cls, thing):
        """return a list of resources from the resource manager that is
        associated with the given thing.

        A resource is a resource attribute in a resource manager.
        """
        
        attrs = [x for x in thing.attrs(cls._attr_name, subkey='manager') 
                 if isinstance(Driver(x.value), cls)]

        res = []

        for attr in attrs:
            t=thing.attrs(cls._attr_name, number=attr.number, subkey=None)
            res.extend(t)


        return res

    @property
    def count(self):
        """Return the number of resources used."""

        return len(self.references(self._attr_name, self, subkey='manager'))


########NEW FILE########
__FILENAME__ = pool
from clusto.drivers.base import Driver
from clusto.schema import *

from clusto.exceptions import PoolException

from itertools import imap, chain

class Pool(Driver):
    """
    A Pool is used to group Entities into a collection that shares attributes.

    Pools
    """

    _driver_name = "pool"
    _clusto_type = "pool"


    def insert(self, thing):
        """Insert the given Enity or Driver into this Entity.

        Such that:

        >>> A.insert(B)
        >>> (B in A)
        True

        A given entity can only be in a Pool one time.
        """

        d = self.ensure_driver(thing,
                               "Can only insert an Entity or a Driver. "
                               "Tried to insert %s." % str(type(thing)))

        if d in self:
            raise PoolException("%s is already in pool %s." % (d, self))

        self.add_attr("_contains", d, number=True)


    def is_parent(self, thing):
        """
        Is this pool the parent of the given entity
        """

        d = self.ensure_driver(thing,
                               "Can only be the parent of a Driver or Entity.")

        return self in d.contents()

    @classmethod
    def get_pools(cls, obj, allPools=True):

        d = cls.ensure_driver(obj, "obj must be either an Entity or a Driver.")


        pools = [Driver(a.entity) for a in d.parents()
                 if isinstance(Driver(a.entity), Pool)]

        if allPools:
            for i in pools:
                pools.extend(Pool.get_pools(i, allPools=True))

        return pools

class ExclusivePool(Pool):
    _driver_name = "exclusive_pool"

    def insert(self, thing):
        """Insert the given Enity or Driver into this Entity.

        Such that:

        >>> A.insert(B)
        >>> (B in A)
        True

        A given entity can only be inserted into an ExclusivePool if
        it is in NO other pools.
        """

        pools = Pool.get_pools(thing)
        if pools:
            raise PoolException("%s is already in pools %s, cannot insert "
                                "exclusively." % (thing, pools))

        Pool.insert(self, thing)

class UniquePool(Pool):
    _driver_name = "unique_pool"

    def insert(self, thing):
        """Insert the given Enity or Driver into this Entity.

        Such that:

        >>> A.insert(B)
        >>> (B in A)
        True

        A given entity can only be in ONE UniquePool.
        """

        pools = thing.parents(clusto_drivers=[self._driver_name])
        if pools:
            raise PoolException("%s is already in UniquePool(s) %s." %
                                (thing, pools))

        Pool.insert(self, thing)

########NEW FILE########
__FILENAME__ = VMController
from random import shuffle

from clusto.drivers import Controller
import libvirt

class VMController(Controller):
    @classmethod
    def allocate(cls, pool, namemanager, ipmanager, memory, disk, swap, storage_pool='vol0'):
        '''
        Allocate a new VM running on a server in the given pool with enough
        free memory.  The new VM will be assigned a name from the given
        namemanager.

        Memory is specified in megabytes (MB)
        Swap is specified in megabytes (MB)
        Disk is specified in gigabytes (GB)
        '''

        # Find a suitable server in the pool
        host = VMController._find_hypervisor(pool, memory, disk, swap, storage_pool)

        # Call libvirt to create the server
        vmxml = VMController._xen_create_vm(host, memory, disk, swap, storage_pool)

        vm = namemanager.allocate(XenVirtualServer)
        vm.from_xml(vmxml)

        # Assign an IP to the server object
        ipmanager.allocate(vm)

        # Return VM object
        return vm
    
    @classmethod
    def destroy(cls, obj):
        # Call libvirt to destroy the server
        # clusto.deleteEntity(obj.entity)

    @classmethod
    def _find_hypervisor(cls, pool, memory, disk, swap, storage_pool):
        candidates = pool.contents()
        shuffle(candidates)

        while True:
            if not candidates:
                raise Exception('No hypervisor candidates have enough available resources')
            server = candidates.pop()
            ip = server.get_ips()
            if not ip:
                continue
            conn = libvirt.openReadOnly('xen+tcp://%s' % ip[0])
            if not conn:
                continue

            freedisk = conn.storagePoolLookupByName(storage_pool).info()[3]
            if (disk * 1073741824) > freedisk:
                continue

            freemem = conn.getFreeMemory() / 1048576
            if mem > freemem:
                continue
            return server

    @classmethod
    def _xen_create_vm(cls, 

########NEW FILE########
__FILENAME__ = basicappliance

from clusto.drivers import Device
from clusto.drivers.devices import PortMixin, IPMixin

class BasicAppliance(IPMixin, PortMixin, Device):
    """
    Basic appliance Driver
    """

    _clusto_type = 'appliance'
    _driver_name = 'basicappliance'

    
    _portmeta = { 'pwr-nema-5' : { 'numports':2, },
                  'nic-eth' : { 'numports':1, },
                  'console-serial' : { 'numports':1, },
                  }

########NEW FILE########
__FILENAME__ = netscaler
from basicappliance import BasicAppliance

class Netscaler(BasicAppliance):
    _driver_name = 'netscaler'
    pass

class Netscaler17000(Netscaler):
    _driver_name = 'netscaler17000'

    _portmeta = { 'pwr-nema-5': { 'numports':2, },
                  'nic-eth': { 'numports': 9, },
                  'nic-xfp': { 'numports': 2, },
                  'console-serial': { 'numports': 1, },
                }

class Netscaler10010(Netscaler):
    _driver_name = 'netscaler10010'

    _portmeta = {   'pwr-nema-5': { 'numports': 2 },
                    'nic-eth': { 'numports': 9 },
                    'console-serial': { 'numports': 1 },
                }

########NEW FILE########
__FILENAME__ = ipmixin
"""
IPMixin is a basic mixin to be used by devices that can be assigned IPs
"""

import re

import clusto

from clusto.drivers.resourcemanagers import IPManager

from clusto.exceptions import ConnectionException,  ResourceException


class IPMixin:

    def add_ip(self, ip=None, ipman=None):

        if not ip and not ipman:
            raise ResourceException('If no ip is specified then an ipmanager must be specified')

        elif ip:
            
            if not ipman:
                ipman = IPManager.get_ip_manager(ip)

            return ipman.allocate(self, ip)
        else:
            return ipman.allocate(self)
            
            
        
    def has_ip(self, ip):

        ipman = IPManager.get_ip_manager(ip)

        return self in ipman.owners(ip)

    def get_ips(self):
        """Get a list of IPs for this Entity in ipstring format"""

        return self.attr_values(IPManager._attr_name, subkey='ipstring')
        

    def bind_ip_to_osport(self, ip, osportname, ipman=None, porttype=None, portnum=None):
        """bind an IP to an os port and optionally also asign the os port name
        to a physical port

        If the given ip is already allocated to this device then use it.  If
        it isn't, try to allocate it from a matching IPManager.

        
        """

        if (porttype != None) ^ (portnum != None):
                raise Exception("both portype and portnum need to be specified or set to None")
            
        try:
            clusto.begin_transaction()

            if not self.has_ip(ip):
                if not ipman:
                    ipman = IPManager.get_ip_manager(ip)

                ipman.allocate(self, ip)

                clusto.flush()
            else:
                ipman = IPManager.get_ip_manager(ip)

            ipattrs = ipman.get_resource_attrs(self, ip)

            if porttype is not None and portnum is not None:
                self.set_port_attr(porttype, portnum, 'osportname', osportname)

            self.set_attr(ipattrs[0].key,
                         number=ipattrs[0].number,
                         subkey='osportname',
                         value=osportname)

            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x
        


        



            
        

########NEW FILE########
__FILENAME__ = portmixin
"""
PortMixin is a basic mixin to be used with devices that have ports
"""

import re

import clusto


from clusto.exceptions import ConnectionException

class PortMixin:
    """Provide port capabilities to devices
    
    The ports are defined in the Driver's _portmeta dictionary:

    _portmeta = { '<porttype>' : {'numports': <num> }}

    Several ports types can be defined in this dictionary.  Currently
    'numports' is the only porttype attribute used.  This data does not get
    stored as Entity attributes in the clusto db.  They live only in the class
    definition.

    Port data gets stored in the DB as the connect to other ports.  The
    keynames are of the form '_port-<porttype>'.  Each port has a specific
    number associated with it (usually the same number as on the physical
    device itself) and can have several port attributes.  There are no
    restrictions on attributes but some common ones might be: osname,
    cabletype, status, etc.
    
    """
    
    # _portmeta = { 'porttype' : {'numports': 10 }}

    _portmeta = { 'pwr-nema-5' : { 'numports':1, },
                  'nic-eth' : { 'numports':2, },
                  }


    def _port_key(self, porttype):
        
        return 'port-' + porttype
    
    def _ensure_portnum(self, porttype, num):


        if not self._portmeta.has_key(porttype) \
                or not isinstance(num, int) \
                or num < 1 \
                or num > self._portmeta[porttype]['numports']:

            msg = "No port %s:%s exists on %s." % (porttype, str(num), self.name)
                    
            raise ConnectionException(msg)
                

        return num

    def connect_ports(self, porttype, srcportnum, dstdev, dstportnum):
        """connect a local port to a port on another device
        """


        for dev, num in [(self, srcportnum), (dstdev, dstportnum)]:

            if not hasattr(dev, 'port_exists'):
                msg = "%s has no ports."
                raise ConnectionException(msg % (dev.name))

            num = dev._ensure_portnum(porttype, num)

            if not dev.port_exists(porttype, num):
                msg = "port %s:%d doesn't exist on %s"
                raise ConnectionException(msg % (porttype, num, dev.name))

        
            if not dev.port_free(porttype, num):
                msg = "port %s%d on %s is already in use"
                raise ConnectionException(msg % (porttype, num, dev.name))

        try:
            clusto.begin_transaction()
            self.set_port_attr(porttype, srcportnum, 'connection', dstdev)
            self.set_port_attr(porttype, srcportnum, 'otherportnum', dstportnum)
            
            dstdev.set_port_attr(porttype, dstportnum, 'connection', self)
            dstdev.set_port_attr(porttype, dstportnum, 'otherportnum', srcportnum)
            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x

    def disconnect_port(self, porttype, portnum):
        """disconnect both sides of a port"""

        portnum = self._ensure_portnum(porttype, portnum)

        if not self.port_free(porttype, portnum):

            dev = self.get_connected(porttype, portnum)
            
            otherportnum = self.get_port_attr(porttype, portnum, 'otherportnum')
            
            clusto.begin_transaction()
            try:
                dev.del_port_attr(porttype, otherportnum, 'connection')
                dev.del_port_attr(porttype, otherportnum, 'otherportnum')
                
                self.del_port_attr(porttype, portnum, 'connection')
                self.del_port_attr(porttype, portnum, 'otherportnum')
                clusto.commit()
            except Exception, x:
                clusto.rollback_transaction()
                raise x
            

    def get_connected(self, porttype, portnum):
        """return the device that the given porttype/portnum is connected to"""

        portnum = self._ensure_portnum(porttype, portnum)

        if not self.port_exists(porttype, portnum):
            msg = "port %s:%d doesn't exist on %s"
            raise ConnectionException(msg % (porttype, portnum, self.name))
            

        return self.get_port_attr(porttype, portnum, 'connection')
            

    def ports_connectable(self, porttype, srcportnum, dstdev, dstportnum):
        """test if the ports you're trying to connect are compatible.
        """

        return (self.port_exists(porttype, srcportnum) 
                and dstdev.port_exists(porttype, dstportnum))
 
    def port_exists(self, porttype, portnum):
        """return true if the given port exists on this device"""
        
        if ((porttype in self._portmeta)):
            try:
                portnum = self._ensure_portnum(porttype, portnum)
                return True
            except ConnectionException:
                return False
        else:
            return False

    def port_free(self, porttype, portnum):
        """return true if the given porttype and portnum are not in use"""
        
        portnum = self._ensure_portnum(porttype, portnum)

        if (not self.port_exists(porttype, portnum) or
            self.has_attr(key=self._port_key(porttype), number=portnum, 
                         subkey='connection')):
            return False
        else:
            return True
        

    def add_port_attr(self, porttype, portnum, key, value):
        """add an attribute on the given port"""

        portnum = self._ensure_portnum(porttype, portnum)

        self.add_attr(key=self._port_key(porttype),
                     number=portnum,
                     subkey=key,
                     value=value)

    def set_port_attr(self, porttype, portnum, key, value):
        """set an attribute on the given port"""

        portnum = self._ensure_portnum(porttype, portnum)

        self.set_attr(key=self._port_key(porttype),
                     number=portnum,
                     subkey=key,
                     value=value)


    def del_port_attr(self, porttype, portnum, key, value=()):
        """delete an attribute on the given port"""

        portnum = self._ensure_portnum(porttype, portnum)

        if value is ():
            self.del_attrs(key=self._port_key(porttype),
                          number=portnum,
                          subkey=key)
        else:

            self.del_attrs(key=self._port_key(porttype),
                          number=portnum,
                          subkey=key,
                          value=value)
            
                     
    def get_port_attr(self, porttype, portnum, key):
        """get an attribute on the given port"""

        portnum = self._ensure_portnum(porttype, portnum)

        attr = self.attrs(key=self._port_key(porttype),
                          number=portnum,
                          subkey=key)

        if len(attr) > 1:
            raise ConnectionException("Somehow more than one attribute named "
                                      "%s is associated with port %s:%d on %s"
                                      % (key, porttype, portnum, self.name))

        elif len(attr) == 1:
            return attr[0].value

        else:
            return None
            
    @property
    def port_info(self):
        """return a list of tuples containing port information for this device
        
        format:
            port_info[<porttype>][<portnum>][<portattr>]
        """

        portinfo = {}
        for ptype in self.port_types:
            portinfo[ptype]={}
            for n in range(1, self._portmeta[ptype]['numports'] + 1):
                portinfo[ptype][n] = {'connection': self.get_port_attr(ptype, n, 'connection'),
                                      'otherportnum': self.get_port_attr(ptype, n, 'otherportnum')}

        return portinfo

    @property
    def port_info_tuples(self):
        """return port information as a list of tuples that are suitble for use
        as *args to connect_ports

        format:
          [ ('porttype', portnum, <connected device>, <port connected to>), ... ]
        """
        
        t = []
        d = self.port_info
        for porttype, numdict in d.iteritems():
            for num, stats in numdict.iteritems():
                t.append((porttype, num, 
                          stats['connection'], stats['otherportnum']))
        
        return t

                         

    
    @property
    def free_ports(self):
        
        return [(pinfo[0], pinfo[1]) for pinfo in self.port_info_tuples if pinfo[3] == None]

    @property
    def connected_ports(self):
        """Return a list of connected ports"""

        pdict = {}
        for ptype in self.port_types:

            portlist = [a.number for a in self.attrs(self._port_key(ptype), 
                                                     subkey='connection')]
            portlist.sort()
            pdict[ptype] = portlist

        return pdict

    @property
    def port_types(self):
        return self._portmeta.keys()



########NEW FILE########
__FILENAME__ = snmpmixin
"""
SNMPMixin for objects that can be accessed with SNMP
"""

import clusto
from clusto.drivers.resourcemanagers import IPManager

# Get rid of pesky errors about missing routes and tcpdump
import logging
runtime = logging.getLogger('scapy.runtime')
runtime.setLevel(logging.ERROR)
loading = logging.getLogger('scapy.loading')
loading.setLevel(logging.ERROR)

from scapy.all import SNMP, SNMPget, SNMPset, SNMPnext, SNMPvarbind
from socket import socket, AF_INET, SOCK_DGRAM

class SNMPMixin:
    """Provide SNMP capabilities to devices
    """

    def _snmp_connect(self, port=161):
        ip = IPManager.get_ips(self)
        if not ip:
            raise ValueError('Device %s does not have an IP' % self.name)
        ip = ip[0]

        community = self.attr_values(key='snmp', subkey='community', merge_container_attrs=True)
        if not community:
            raise ValueError('Device %s does not have an SNMP community attribute' % self.name)
        
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.connect((ip, port))
        return (str(community[0]), sock)

    def _snmp_get(self, oid):
        community, sock = self._snmp_connect()

        pdu = SNMPget(varbindlist=[SNMPvarbind(oid=str(oid))])
        p = SNMP(community=community, PDU=pdu)
        sock.sendall(p.build())

        r = SNMP(sock.recv(4096))
        return r.PDU.varbindlist[0].value.val

    def _snmp_set(self, oid, value):
        community, sock = self._snmp_connect()

        pdu = SNMPset(varbindlist=[SNMPvarbind(oid=str(oid), value=value)])
        p = SNMP(community=community, PDU=pdu)
        sock.sendall(p.build())

        r = SNMP(sock.recv(4096))
        return r

    def _snmp_walk(self, oid_prefix):
        community, sock = self._snmp_connect()

        nextoid = oid_prefix
        while True:
            p = SNMP(community=community, PDU=SNMPnext(varbindlist=[SNMPvarbind(oid=nextoid)]))
            sock.sendall(p.build())

            r = SNMP(sock.recv(4096))
            oid = r.PDU.varbindlist[0].oid.val
            if oid.startswith(oid_prefix):
                yield (oid, r.PDU.varbindlist[0].value.val)
            else:
                break
            nextoid = oid

        sock.close()

########NEW FILE########
__FILENAME__ = basicconsoleserver

from clusto.drivers import Device
from clusto.drivers.devices import PortMixin, IPMixin

class BasicConsoleServer(IPMixin, PortMixin, Device):
    """
    Basic console server Driver
    """

    _clusto_type = 'consoleserver'
    _driver_name = 'basicconsoleserver'

    
    _portmeta = { 'pwr-nema-5' : { 'numports':1, },
                  'nic-eth' : { 'numports':1, },
                  'console-serial' : { 'numports':24, },
                  }

    def connect(self, port, num):
        raise NotImplemented

########NEW FILE########
__FILENAME__ = opengear
from basicconsoleserver import BasicConsoleServer
from clusto.exceptions import ConnectionException
from clusto.drivers.resourcemanagers import IPManager

from subprocess import Popen

class OpenGearCM4148(BasicConsoleServer):

    _driver_name = 'opengearcm4148'

    _portmeta = { 'pwr-nema-5' : { 'numports':1, },
                  'nic-eth' : { 'numports':1, },
                  'console-serial' : { 'numports':48, },
                  }

    def connect(self, porttype, num, ssh_user='root'):
        if porttype != 'console-serial':
            raise DriverException("Cannot connect to a non-serial port")

        host = IPManager.get_ips(self)
        if len(host) == 0:
            host = self.name
        else:
            host = host[0]

        proc = Popen(['ssh', '-p', str(num + 3000), '-l', ssh_user, host])
        proc.communicate()

########NEW FILE########
__FILENAME__ = basicnetworkswitch

from clusto.drivers.base import Device
from clusto.drivers.devices.common import PortMixin, IPMixin

class BasicNetworkSwitch(IPMixin, PortMixin, Device):
    """
    Basic network switch driver
    """

    _clusto_type = 'networkswitch'
    _driver_name = 'basicnetworkswitch'


    _portmeta = {'pwr-nema-5' : {'numports':1},
                 'nic-eth' : {'numports':24}}



########NEW FILE########
__FILENAME__ = cisconetworkswitch

from basicnetworkswitch import BasicNetworkSwitch

class Cisco2960(BasicNetworkSwitch):
    _driver_name = 'cisco2960'

    _portmeta = {
        'pwr-nema-5': {'numports': 1},
        'console-serial': {'numports': 1},
        'nic-eth': {'numports': 48},
    }

class Cisco3560(BasicNetworkSwitch):
    _driver_name = 'cisco3560'

    _portmeta = {
        'pwr-nema-5': {'numports': 1},
        'console-serial': {'numports': 1},
        'nic-eth': {'numports': 48},
        'nic-fiber10g': {'numports': 4},
    }

class Cisco4948(BasicNetworkSwitch):
    _driver_name = 'cisco4948'

    _portmeta = {
        'pwr-nema-5': {'numports': 1},
        'console-serial': {'numports': 1},
        'nic-eth': {'numports': 48},
        'nic-fiber10g': {'numports': 2},
    }

########NEW FILE########
__FILENAME__ = basicpowerstrip

from clusto.drivers.base import Device
from clusto.drivers.devices.common import PortMixin, IPMixin

class BasicPowerStrip(IPMixin, PortMixin, Device):
    """
    Basic power strip Driver.
    """

    _clusto_type = "powerstrip"
    _driver_name = "basicpowerstrip"
    

    
    _portmeta = { 'pwr-nema-5' : { 'numports':8, }, 
                  }

########NEW FILE########
__FILENAME__ = servertech
"""
Server Technology Power Strips

"""


from basicpowerstrip import BasicPowerStrip
from clusto.drivers.devices.common import IPMixin, SNMPMixin
from clusto.drivers.resourcemanagers import IPManager
from clusto.exceptions import DriverException

import re


class PowerTowerXM(BasicPowerStrip, IPMixin, SNMPMixin):
    """
    Provides support for Power Tower XL/XM

    Power Port designations start with 1 at the upper left (.aa1) down to 32
    at the bottom right (.bb8).
    """

    _driver_name = "powertowerxm"

    _properties = {'withslave':0}


    _portmeta = { 'pwr-nema-L5': { 'numports':2 },
                  'pwr-nema-5' : { 'numports':16, },
                  'nic-eth' : { 'numports':1, },
                  'console-serial' : { 'numports':1, },
                  }



    _portmap = {'aa1':1,'aa2':2,'aa3':3,'aa4':4,'aa5':5,'aa6':6,'aa7':7,'aa8':8,
                'ab1':9,'ab2':10,'ab3':11,'ab4':12,'ab5':13,'ab6':14,'ab7':15,
                'ab8':16,'ba1':17,'ba2':18,'ba3':19,'ba4':20,'ba5':21,'ba6':22,
                'ba7':23,'ba8':24,'bb1':25,'bb2':26,'bb3':27,'bb4':28,'bb5':29,
                'bb6':30,'bb7':31,'bb8':32}

    _outlet_states = ['idleOff', 'idleOn', 'wakeOff', 'wakeOn', 'off', 'on', 'lockedOff', 'reboot', 'shutdown', 'pendOn', 'pendOff', 'minimumOff', 'minimumOn', 'eventOff', 'eventOn', 'eventReboot', 'eventShutdown']

    def _ensure_portnum(self, porttype, portnum):
        """map powertower port names to clusto port numbers"""

        if not self._portmeta.has_key(porttype):
            msg = "No port %s:%s exists on %s." % (porttype, str(num), self.name)
                    
            raise ConnectionException(msg)

        if isinstance(portnum, int):
            num = portnum
        else:
            if portnum.startswith('.'):
                portnum = portnum[1:] 
            
            if self._portmap.has_key(portnum):
                num = self._portmap[portnum]
            else:
                msg = "No port %s:%s exists on %s." % (porttype, str(num), 
                                                       self.name)
                    
                raise ConnectionException(msg)
 
        numports = self._portmeta[porttype]
        if self.withslave:
            if porttype in ['mains', 'pwr']:
                numports *= 2

        if num < 0 or num >= numports:
            msg = "No port %s:%s exists on %s." % (porttype, str(num), 
                                                   self.name)
                    
            raise ConnectionException(msg)



        return num

    def _get_port_oid(self, outlet):
        for oid, value in self._snmp_walk('1.3.6.1.4.1.1718.3.2.3.1.2'):
            if value.lower() == outlet:
                return oid

    def get_outlet_state(self, outlet):
        oid = self._get_port_oid(outlet)
        oid = oid.replace('1.3.6.1.4.1.1718.3.2.3.1.2', '1.3.6.1.4.1.1718.3.2.3.1.10')
        state = self._snmp_get(oid)
        return self._outlet_states[int(state)]

    def set_outlet_state(self, outlet, state, session=None):
        oid = self._get_port_oid(outlet)
        oid = oid.replace('1.3.6.1.4.1.1718.3.2.3.1.2', '1.3.6.1.4.1.1718.3.2.3.1.11')
        r = self._snmp_set(oid, state)
        if r.PDU.varbindlist[0].value.val != state:
            raise DriverException('Unable to set SNMP state')

    def set_power_off(self, porttype, portnum):
        if porttype != 'pwr-nema-5':
            raise DriverException('Cannot turn off ports of type: %s' % str(porttype))
        portnum = portnum.lstrip('.').lower()
        state = self.set_outlet_state(portnum, 2)

    def set_power_on(self, porttype, portnum):
        if porttype != 'pwr-nema-5':
            raise DriverException('Cannot turn off ports of type: %s' % str(porttype))
        portnum = portnum.lstrip('.').lower()
        state = self.set_outlet_state(portnum, 1)

    def reboot(self, porttype, portnum):
        if porttype != 'pwr-nema-5':
            raise DriverException('Cannot reboot ports of type: %s' % str(porttype))

        portnum = portnum.lstrip('.').lower()

        state = self.get_outlet_state(portnum)

        nextstate = None
        if state == 'off':
            nextstate = 1
        if state in ('idleOn', 'on', 'wakeOn'):
            nextstate = 3

        if not nextstate:
            raise DriverException('Outlet in unexpected state: %s' % state)

        self.set_outlet_state(portnum, nextstate)

########NEW FILE########
__FILENAME__ = basicserver
from clusto.drivers.base import Device
from clusto.drivers.devices.common import PortMixin, IPMixin

class BasicServer(IPMixin, PortMixin, Device):
    """
    server
    """

    _clusto_type = "server"
    _driver_name = "basicserver"

    _properties = {'model':None,
                   'manufacturer':None}

    _portmeta = {'pwr-nema-5': {'numports':1},
                 'nic-eth': {'numports':2},
                 'console-serial' : { 'numports':1, }
                 }



class BasicVirtualServer(BasicServer):

    _clusto_type = "virtualserver"
    _driver_name = "basicvirtualserver"

    def create(self, pool, **kwargs):
        raise NotImplemented

    def start(self):
        raise NotImplemented

    def reboot(self):
        raise NotImplemented

    def shutdown(self):
        raise NotImplemented

    def destroy(self):
        raise NotImplemented

########NEW FILE########
__FILENAME__ = ec2server

from clusto.drivers.devices import BasicVirtualServer

class EC2VirtualServer(BasicVirtualServer):
    _driver_name = "ec2virtualserver"

    _port_meta = {}

    

########NEW FILE########
__FILENAME__ = kvmvirtualserver
from traceback import format_exc
from urlparse import urlparse
from telnetlib import Telnet
import httplib
import sys

try:
    import simplejson as json
except ImportError:
    import json

from basicserver import BasicVirtualServer
from clusto.exceptions import DriverException
import clusto

class KVMVirtualServer(BasicVirtualServer):
    _driver_name = "kvmvirtualserver"

    def __init__(self, name, **kwargs):
        BasicVirtualServer.__init__(self, name, **kwargs)

    def get_hypervisor(self):
        from clusto.drivers import VMManager
        host = VMManager.resources(self)
        if not host:
            raise DriverException('Cannot start a VM without first allocating a hypervisor')
        return host[0].value
        
    def _request(self, method, endpoint, body=None):
        host = self.get_hypervisor().get_ips()[0]
        conn = httplib.HTTPConnection(host, 3000)

        if body:
            body = json.dumps(body, indent=2, sort_keys=True)

        conn.request(method, endpoint, body)
        response = conn.getresponse()
        return (response.status, response.read())

    def kvm_create(self, options):
        status, response = self._request('POST', '/api/1/%s' % self.name, {
            'memory': options.memory,
            'disk': options.disk,
        })
        if status != 200:
            raise DriverException(response)

        response = json.loads(response)

        config = response['config']

        try:
            clusto.begin_transaction()
            self.set_attr(key='system', subkey='memory', value=config['memory'])
            self.set_attr(key='system', subkey='disk', value=config['disk'])
            self.set_attr(key='system', subkey='cpucount', value=1)
            self.set_attr(key='kvm', subkey='console-port', value=config['console'])
            self.set_attr(key='kvm', subkey='vnc-port', value=5900 + config['vnc'])
            self.set_port_attr('nic-eth', 1, 'mac', config['mac'])
            self.set_port_attr('nic-eth', 1, 'model', config['nic'])
            clusto.SESSION.clusto_description = 'Populate KVM information for %s' % self.name
            clusto.commit()
        except:
            sys.stderr.write(format_exc() + '\n')
            clusto.rollback_transaction()

    def kvm_update(self, options):
        attr = dict([(x.subkey, x.value) for x in self.attrs(key='system')])

        status, response = self._request('PUT', '/api/1/%s' % self.name, {
            'memory': attr['memory'],
            'disk': attr['disk'],
            'mac': self.get_port_attr('nic-eth', 1, 'mac'),
            'nic': self.get_port_attr('nic-eth', 1, 'model'),
        })
        if status != 201:
            raise DriverException(response)
        #response = json.loads(response)

    def kvm_delete(self, options):
        status, response = self._request('DELETE', '/api/1/%s' % self.name)
        if status != 200:
            raise DriverException(response)

    def kvm_status(self, options):
        status, response = self._request('GET', '/api/1/%s' % self.name)
        if status != 200:
            raise DriverException(response)
        response = json.loads(response)
        return response['state']

    def kvm_start(self, options):
        status, response = self._request('POST', '/api/1/%s/start' % self.name)
        if status != 200:
            raise DriverException(response)
        response = json.loads(response)
        if response['state'] != 'RUNNING':
            raise DriverException('VM is not in the RUNNING state after starting')

    def kvm_stop(self, options):
        status, response = self._request('POST', '/api/1/%s/stop' % self.name)
        if status != 200:
            raise DriverException(response)
        response = json.loads(response)
        if response['state'] != 'STOPPED':
            raise DriverException('VM is not in the STOPPED state after stopping')

    def kvm_console(self, options):
        client = Telnet(self.get_hypervisor().get_ips()[0], self.attr_value(key='kvm', subkey='console'))
        client.interact()

########NEW FILE########
__FILENAME__ = penguincomputing
"""
Drivers for Penguin Computing Servers
"""

from basicserver import BasicServer

class PenguinServer(BasicServer):
    _driver_name = "penguinserver"

class PenguinServer2U(PenguinServer):
    _driver_name = "penguinserver2u"
    _portmeta = {'pwr-nema-5': {'numports': 2},
                 'nic-eth': {'numports': 2},
                 'console-serial': {'numports': 1}}
    rack_units = 2

########NEW FILE########
__FILENAME__ = xenvirtualserver
from xml.etree import ElementTree
from subprocess import Popen
from random import shuffle

from basicserver import BasicVirtualServer
from clusto.exceptions import DriverException

from IPy import IP
import libvirt

class XenVirtualServer(BasicVirtualServer):
    _driver_name = "xenvirtualserver"

    def __init__(self, name, **kwargs):
        BasicVirtualServer.__init__(self, name, **kwargs)

    def _libvirt_create_disk(self, conn, name, capacity, vgname):
        volume = ElementTree.XML('''
        <volume>
            <name></name>
            <capacity></capacity>
            <target>
                <path></path>
            </target>
        </volume>''')
        volume.find('name').text = '%s-%s' % (self.name, name)
        volume.find('capacity').text = str(capacity)
        volume.find('target/path').text = '/dev/%s/%s-%s' % (vgname, self.name, name)

        vg = conn.storagePoolLookupByName(vgname)
        return vg.createXML(ElementTree.tostring(volume), 0)

    def _libvirt_delete_disk(self, conn, name, vgname):
        vol = conn.storageVolLookupByPath('/dev/%s/%s-%s' % (vgname, self.name, name))
        if vol.delete(0) != 0:
            raise DriverException('Unable to delete disk %s-%s' % (self.name, name))

    def _libvirt_create_domain(self, conn, memory, cpucount, vgname):
        domain = ElementTree.XML('''
        <domain type="xen">
            <name></name>
            <memory></memory>
            <vcpu></vcpu>
            <os>
                <type>hvm</type>
                <loader>/usr/lib/xen-default/boot/hvmloader</loader>
                <boot dev="hd" />
                <boot dev="network" />
            </os>
            <features>
                <pae />
            </features>
            <devices>
                <disk type="block">
                    <source />
                    <target />
                </disk>
                <disk type="block">
                    <source />
                    <target />
                </disk>
                <interface type="bridge">
                    <mac />
                    <source bridge="eth0" />
                </interface>
                <console type="pty">
                    <target port="0" />
                </console>
            </devices>
        </domain>''')

        domain.find('name').text = self.name
        domain.find('memory').text = str(memory)
        domain.find('vcpu').text = str(cpucount)

        disks = list(domain.findall('devices/disk'))
        disks[0].find('source').set('dev', '/dev/%s/%s-root' % (vgname, self.name))
        disks[0].find('target').set('dev', 'hda')
        disks[1].find('source').set('dev', '/dev/%s/%s-swap' % (vgname, self.name))
        disks[1].find('target').set('dev', 'hdb')

        domain.find('devices/interface/mac').set('address', self.get_port_attr('nic-eth', 1, 'mac'))

        xml = ElementTree.tostring(domain)
        return conn.defineXML(xml)

    def _libvirt_delete_domain(self, conn):
        domain = conn.lookupByName(self.name)
        if domain.undefine() != 0:
            raise DriverException('Unable to delete (undefine) domain %s' % name)

    def _libvirt_connect(self):
        host = self.get_hypervisor()

        ip = host.get_ips()
        if not ip:
            raise DriverException('Hypervisor does not have an IP!')
        ip = ip[0]

        conn = libvirt.open('xen+tcp://%s' % ip)
        if not conn:
            raise DriverException('Unable to connect to hypervisor! xen+tcp://%s' % ip)
        return conn

    def get_hypervisor(self):
        from clusto.drivers import VMManager
        host = VMManager.resources(self)
        if not host:
            raise DriverException('Cannot start a VM without first allocating a hypervisor with VMManager.allocate')
        return host[0].value

    def vm_create(self, conn=None):
        if not conn:
            conn = self._libvirt_connect()

        # Get and validate attributes
        disk_size = self.attr_values(key='system', subkey='disk')
        memory_size = self.attr_values(key='system', subkey='memory')
        swap_size = self.attr_values(key='system', subkey='swap')
        cpu_count = self.attr_values(key='system', subkey='cpucount')

        if not disk_size:
            raise DriverException('Cannot create a VM without a key=system,subkey=disk parameter (disk size in GB)')
        if not memory_size:
            raise DriverException('Cannot create a VM without a key=system,subkey=memory parameter (memory size in MB)')
        if not swap_size:
            swap_size = [512]
        if not cpu_count:
            cpu_count = [1]

        disk_size = disk_size[0]
        swap_size = swap_size[0]
        memory_size = memory_size[0]
        cpu_count = cpu_count[0]

        disk_size *= 1073741824
        swap_size *= 1048576
        memory_size *= 1024

        host = self.get_hypervisor()
        volume_group = host.attr_values(key='xen', subkey='volume-group', merge_container_attrs=True)
        if not volume_group:
            raise DriverException('No key=xen,subkey=volume-group defined for %s' % host.name)
        else:
            volume_group = volume_group[0]

        # Create disks and domain
        if not self._libvirt_create_disk(conn, 'root', disk_size, volume_group):
            raise DriverException('Unable to create logical volume %s-root' % self.name)
        if not self._libvirt_create_disk(conn, 'swap', swap_size, volume_group):
            raise DriverException('Unable to create logical volume %s-swap' % self.name)
        if not self._libvirt_create_domain(conn, memory_size, cpu_count, volume_group):
            raise DriverException('Unable to define domain %s' % self.name)

    def vm_start(self, conn=None):
        if not conn:
            conn = self._libvirt_connect()
        domain = conn.lookupByName(self.name)
        if domain.create() != 0:
            raise DriverException('Unable to start domain %s' % self.name)
        #domain.setSchedulerParameters({'weight': self.attr_value(key='system', subkey='memory')})

    def vm_stop(self, force=False, conn=None):
        if not conn:
            conn = self._libvirt_connect()
        domain = conn.lookupByName(self.name)

        if force:
            ret = domain.destroy()
        else:
            ret = domain.shutdown()

        if ret != 0:
            raise DriverException('Unable to stop (destroy) domain %s' % self.name)

    def vm_reboot(self, conn=None):
        if not conn:
            conn = self._libvirt_connect()
        domain = conn.lookupByName(self.name)
        if domain.reboot(0) != 0:
            raise DriverException('Unable to reboot domain %s' % self.name)

    def vm_delete(self, conn=None):
        if not conn:
            conn = self._libvirt_connect()

        host = self.get_hypervisor()
        volume_group = host.attr_values(key='xen', subkey='volume-group', merge_container_attrs=True)
        if not volume_group:
            raise DriverException('No key=xen,subkey=volume-group defined for %s' % host.name)
        else:
            volume_group = volume_group[0]

        self._libvirt_delete_domain(conn)
        self._libvirt_delete_disk(conn, 'root', volume_group)
        self._libvirt_delete_disk(conn, 'swap', volume_group)

    def vm_console(self, ssh_user='root'):
        host = self.get_hypervisor()

        ip = host.get_ips()
        if not ip:
            raise DriverException('Hypervisor has no IP: %s' % host.name)
        ip = ip[0]

        proc = Popen('ssh -t -l %s %s "xm console %s"' % (ssh_user, ip, self.name), shell=True)
        proc.communicate()

########NEW FILE########
__FILENAME__ = basicdatacenter

from clusto.drivers.base import Location

class BasicDatacenter(Location):
    """
    Basic datacenter driver
    """

    _clusto_type = "datacenter"
    _driver_name = "basicdatacenter"

    

########NEW FILE########
__FILENAME__ = equinixdatacenter

from basicdatacenter import BasicDatacenter

class EquinixDatacenter(BasicDatacenter):
    """
    Equinix datacenter driver
    """

    _driver_name = "equinixdatacenter"

########NEW FILE########
__FILENAME__ = apcrack

from basicrack import BasicRack

class APCRack(BasicRack):

    _driver_name = "apcrack"

    

########NEW FILE########
__FILENAME__ = basicrack

import re
from clusto.drivers.base import Location, Device, Driver

class BasicRack(Location):
    """
    Basic rack driver.
    """

    _clusto_type = "rack"
    _driver_name = "basicrack"

    _properties = {'minu':1,
                   'maxu':45}


    def _ensure_rack_u(self, rackU):
        if not isinstance(rackU, int) and not isinstance(rackU, (list, tuple)):
            raise TypeError("a rackU must be an Integer or list/tuple of Integers.")


        if isinstance(rackU, list):
            for U in rackU:
                if not isinstance(U, int):
                    raise TypeError("a rackU must be an Integer or List of Integers.")

        if isinstance(rackU, int):
            rackU = [rackU]
        else:
            rackU = list(rackU)

        # do U checks
        for U in rackU:
            if U > self.maxu:
                raise TypeError("the rackU must be less than %d." % self.maxu)
            if U < self.minu:
                raise TypeError("RackUs may not be negative.")

        rackU.sort()
        last = rackU[0]
        for i in rackU[1:]:
            if i == last:
                raise TypeError("you can't list the same U twice.")
            if (i-1) != (last):
                raise TypeError("a device can only occupy multiple Us if they're adjacent.")
            last = i

        return rackU

    def insert(self, device, rackU):
        """Insert a given device into the given rackU."""


        if not isinstance(device, Device):
            raise TypeError("You can only add Devices to a rack.  %s is a"
                            " %s" % (device.name, str(device.__class__)))

        rackU = self._ensure_rack_u(rackU)

        rau = self.get_rack_and_u(device)

        if rau != None:
            raise Exception("%s is already in rack %s"
                            % (device.name, rau['rack'].name))

        if hasattr(device, 'rack_units') and (len(rackU) != device.rack_units):
            raise TypeError("%s is a %dU device, cannot insert it in %dU"
                            % (device.name, units, len(rackU)))

        for U in rackU:
            dev = self.get_device_in(U)
            if dev:
                raise TypeError("%s is already in RU %d" % (dev.name, U))

        for U in rackU:
            self.add_attr("_contains", device, number=U, subkey='ru')

    def get_device_in(self, rackU):

        if not isinstance(rackU, int):
            raise TypeError("RackU must be a single integer. Got: %s" % str(rackU))

        rackU = self._ensure_rack_u(rackU)[0]

        owners = self.contents(number=rackU, subkey='ru')

        if len(owners) > 1:
            raise Exception('Somehow there is more than one thing in ru%d.'
                            'Only one of these should be in this space in the '
                            'rack: %s' % (rackU,
                                          ','.join([x.name for x in owners])))
        if owners:
            return owners[0]

        return None

    @classmethod
    def get_rack_and_u(cls, device):
        """
        Get the rack and rackU for a given device.

        returns a tuple of (rack, u-number)
        """

        rack = set(device.parents(clusto_types=[cls]))


        if len(rack) > 1:
            raise Exception("%s is somehow in more than one rack, this will "
                            "likely need to be rectified manually.  It currently "
                            "appears to be in racks %s"
                            % (device.name, str(rack)))

        if rack:
            rack = rack.pop()
            return {'rack':Driver(rack.entity),
                    'RU':[x.number for x in rack.content_attrs(value=device,
                                                              subkey='ru')]}
        else:

            return None

########NEW FILE########
__FILENAME__ = ipmanager
import clusto
from clusto.schema import Attribute

from clusto.drivers.base import ResourceManager, ResourceTypeException, Driver
from clusto.exceptions import ResourceNotAvailableException, ResourceException

import IPy

class IPManager(ResourceManager):
    """Resource Manager for IP spaces
    
    roughly follows the functionality available in IPy
    """


    _driver_name="ipmanager"

    _properties = {'gateway': None,
                   'netmask': '255.255.255.255',
                   'baseip': None }

    _attr_name = "ip"

    __int_ip_const = 2147483648
    
    @property
    def ipy(self):
        if not hasattr(self, '__ipy'):

            self.__ipy = IPy.IP(''.join([u'%s' % str(self.baseip), '/', 
                                u'%s' % self.netmask]), make_net=True)


        return self.__ipy

    def ensure_type(self, resource, number=True, thing=None):
        """check that the given ip falls within the range managed by this manager"""

        try:
            if isinstance(resource, int):
                ip = IPy.IP(resource+self.__int_ip_const)
            else:
                ip = IPy.IP(resource)
        except ValueError:
            raise ResourceTypeException("%s is not a valid ip."
                                        % resource)

        if self.baseip and (ip not in self.ipy):
            raise ResourceTypeException(u"The ip %s is out of range for this IP manager.  Should be in %s/%s"
                                        % (str(ip), self.baseip, self.netmask))


        return (int(ip.int()-self.__int_ip_const), number)


    def additional_attrs(self, thing, resource, number):

        resource, number = self.ensure_type(resource, number)

        thing.add_attr(self._attr_name, number=number, subkey='ipstring', value=u'%s' % str(IPy.IP(resource+self.__int_ip_const)))
        
                     
    def allocator(self, thing=None):
        """allocate IPs from this manager"""

        if self.baseip is None:
            raise ResourceTypeException("Cannot generate an IP for an ipManager with no baseip")

        lastip = self.attr_query('_lastip')
                
        if not lastip:
            # I subtract self.__int_ip_const to keep in int range
            startip=int(self.ipy.net().int() + 1) - self.__int_ip_const 
        else:
            startip = lastip[0].value


        
        ## generate new ips the slow naive way
        nextip = int(startip)
        if self.gateway:
            gateway = IPy.IP(self.gateway).int() - self.__int_ip_const
        else:
            gateway = None
        endip = self.ipy.broadcast().int() - self.__int_ip_const

        for i in range(2):
            while nextip < endip:

                if nextip == gateway:
                    nextip += 1
                    continue

                if self.available(nextip):
                    self.set_attr('_lastip', nextip)
                    return self.ensure_type(nextip, True)
                else:
                    nextip += 1
            
            # check from the beginning again in case an earlier ip
            # got freed
                    
            nextip = int(self.ipy.net().int() + 1)
            
        raise ResourceNotAvailableException("out of available ips.")

    @classmethod
    def get_ip_manager(cls, ip):
        """return a valid ip manager for the given ip.

        @param ip: the ip
        @type ip: integer, string, or IPy object

        @return: the appropriate IP manager from the clusto database
        """

        ipman = None
        if isinstance(ip, Attribute):
            ipman = ip.entity
            return Driver(ipman)

        for ipmantest in clusto.get_entities(clusto_drivers=[cls]):
            try:
                ipmantest.ensure_type(ip)
            except ResourceTypeException:
                continue

            ipman = Driver(ipmantest)
            break
        

        if not ipman:
            raise ResourceException(u"No resource manager for %s exists."
                                    % str(ip))
        
        return ipman
        
    @classmethod
    def get_ips(cls, device):

        ret = [u'%s' % str(IPy.IP(x.value+cls.__int_ip_const))
               for x in cls.resources(device)]

        return ret

    @classmethod
    def get_devices(self, ip):
        subnet = IPManager.get_ip_manager(ip)
        return subnet.owners(ip)

########NEW FILE########
__FILENAME__ = simplenamemanager
import clusto
from clusto.drivers.base import ResourceManager

from clusto.exceptions import ResourceException
from clusto.schema import ATTR_TABLE

class SimpleNameManagerException(ResourceException):
    pass

class SimpleNameManager(ResourceManager):
    """
    SimpleNameManager - manage the generation of a names with a common
    prefix and an incrementing integer component.

    e.g foo001, foo002, foo003, etc.
    
    """

    _driver_name = "simplenamemanager"
    _properties = {'basename':'',
                   'digits':2,
                   'next':1,
                   'leadingZeros':int(True)}

    _record_allocations = True
    _attr_name = 'simplename'
    
    def allocator(self, thing=None):
        clusto.flush()

        counter = clusto.Counter.get(self.entity, 'next', default=self.next)

        num = str(counter.value)

        if self.leadingZeros:
            num = num.rjust(self.digits, '0')

        if len(num) > self.digits:
            raise SimpleNameManagerException("Out of digits for the integer. "
                                             "Max of %d digits and we're at "
                                             "number %s." % (self.digits, num))
        
        nextname = self.basename + num

        counter.next()

        return (nextname, True)
        

class SimpleEntityNameManager(SimpleNameManager):    

    _driver_name = "simpleentitynamemanager"

    _record_allocations = False


    def allocate(self, clustotype, resource=None, number=True):
        """allocates a resource element to the given thing.

        resource - is passed as an argument it will be checked 
                   before assignment.  

        refattr - the attribute name on the entity that will refer back
                  this resource manager.

        returns the resource that was either passed in and processed 
        or generated.
        """

        if not isinstance(clustotype, type):
            raise TypeError("thing is not a Driver class")

        try:
            clusto.begin_transaction()

            if not resource:
                name, num = self.allocator()

                newobj = clustotype(name)

            else:
                name = resource
                newobj = clustotype(resource)


            super(SimpleEntityNameManager, self).allocate(newobj, name)

            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x
        
        return newobj


    def deallocate(self, thing, resource=None, number=True):
        raise Exception("can't deallocate an entity name, delete the entity instead.")


########NEW FILE########
__FILENAME__ = simplenummanager
import clusto
from clusto.drivers.base import ResourceManager

from clusto.exceptions import ResourceException
from clusto.schema import ATTR_TABLE

class SimpleNumManagerException(ResourceException):
    pass

class SimpleNumManager(ResourceManager):
    """Manage the generation of numbers that can be associated with Entities
    
    """

    _driver_name = "simplenummanager"
    _properties = {'maxnum':None,
                   'next':0,
                   }

    _record_allocations = True
    _attr_name = "simplenum"
    
    def allocator(self, thing=None):

        clusto.flush()

        counter = clusto.Counter.get(self.entity, 'next', default=self.next)

        num = counter.value
        
        if self.maxnum and num > self.maxnum:
            raise SimpleNumManagerException("Out of numbers. "
                                            "Max of %d reached." 
                                            % (self.maxnum))
        
        counter.next()
        return (num, True)


########NEW FILE########
__FILENAME__ = vmmanager
"""
The VMManager is a special case of resource manager.

It overrides many of the standard ResourceManager functions but still makes
use of the ResourceManager plumbing where appropriate.

"""

import clusto
from clusto.drivers.devices.servers import BasicServer, BasicVirtualServer
from clusto.drivers.base import ResourceManager
from clusto.exceptions import ResourceException

import random

class VMManager(ResourceManager):
    """Manage resources for Virtual Machines.

    The resource being managed are the host machines.  A VM gets assigned to a
    host machine.  The VMManager keeps track of how much cpu/ram/disk is
    available on each host and allocates them accordingly.
    """
    
    _driver_name = "vmmanager"

    _attr_name = "vmmanager"

    def ensure_type(self, resource, number=True, thing=None):

        if isinstance(resource, basestring):
            resource = clusto.get_by_name(resource)

        if resource not in self:
            raise ResourceException("%s is not managed by this VM manager"
                                    % resource.name)

        return (resource, number)
    
        
    def insert(self, thing):
        # insert into self and also add attributes that will help with  allocation
        if thing.type != BasicServer._clusto_type:
            raise ResourceException("Only servers can be inserted into "
                                    "this manager but %s is of type %s."
                                    % (thing.name, thing.type))

        
        memory = thing.attr_value('system', subkey='memory')
        disk = thing.attr_value('system', subkey='disk')
        cpucount = thing.attr_value('system', subkey='cpucount')

        if not memory and not disk and not cpucount:
            raise ResourceException("Server must have attributes for "
                                    "key='system' and subkey='disk',"
                                    "'memory', and 'cpucount' set to be "
                                    "inserted into this manager.")

        d = self.ensure_driver(thing,
                               "Can only insert an Entity or a Driver. "
                               "Tried to insert %s." % str(type(thing)))

        if d in self:
            raise PoolException("%s is already in %s." % (d, self))

        self.add_attr("_contains", d, number=True)
    
    def remove(self, thing):
        # check if thing is in use by a VM
        # error if yes
        # remove if no and clear attributes related to helping allocation

        vms = self.owners(thing)
        if vms:
            raise ResourceException("%s is still allocated to VMs: %s"
                                    % (thing.name, str(vms)))

        super(VMManager, self).remove(thing)
        
        
    def additional_attrs(self, thing, resource, number):

        resource, number = self.ensure_type(resource, number)

        thing.set_attr(self._attr_name, number=number,
                       subkey='allocated_memory',
                       value=thing.attr_value('system', subkey='memory'))

    def available(self, resource, number=True, thing=None):
        resource, number = self.ensure_type(resource, number)

        return self._has_capacity(resource, thing)

        
    def _has_capacity(self, host, vm):


        # if the host was allocated to the vmmanager it is "reserved" and
        # shouldn't get any more VMs assigned to it.
        if self in self.owners(host):
            return False
        
        ## this is a very slow way to do this
        
        mem = host.attr_value('system', subkey='memory')
        disk = host.attr_value('system', subkey='disk')
        cpu = host.attr_value('system', subkey='cpucount')
        vms = host.referencers(clusto_types=[BasicVirtualServer])

        for v in vms:
            mem -= v.attr_value('system', subkey='memory')
            disk -= v.attr_value('system', subkey='disk')
            cpu -= v.attr_value('system', subkey='cpucount')

        vmmem = vm.attr_value('system', subkey='memory')
        vmdisk = vm.attr_value('system', subkey='disk')
        vmcpu = vm.attr_value('system', subkey='cpucount')
        
        return (vmcpu <= cpu) & (vmmem <= mem) & (vmdisk <= disk)
        
    
    def allocator(self, thing):
        """Allocate a host server for a given virtual server. """

        for res in self.resources(thing):
            raise ResourceException("%s is already assigned to %s"
                                    % (thing.name, res.value))

        hosts = self.contents(clusto_types=[BasicServer])

        hosts = sorted(hosts,
                       key=lambda x: x.attr_value('system', subkey='disk'))
        hosts = sorted(hosts,
                       key=lambda x: x.attr_value('system', subkey='cpucount'))
        hosts = sorted(hosts,
                       key=lambda x: x.attr_value('system', subkey='memory'))
                       
        
        for i in hosts:
            if self._has_capacity(i, thing):
                return (i, True)

                
        raise ResourceException("No hosts available.")

    def allocate(self, thing, resource=(), number=True, **kwargs):
        """Allocate resources for VMs

        pass off normal allocation to the parent but also keep track of
        available host-resources
        """
        
        for res in self.resources(thing):
            raise ResourceException("%s is already assigned to %s"
                                    % (thing.name, res.value))

        attr = super(VMManager, self).allocate(thing, resource, number, **kwargs)

        return attr
    

class EC2VMManager(VMManager):

    _driver_name = "ec2vmmanager"

    _properties = {'budget':None,
                   'current_cost':None,
                   'accountstuff':None} # i'd have to lookup again what ec2 actually needs

    def allocator(self):
        """allocate VMs on ec2 while keeping track of current costs and staying within the budget"""
        pass

class XenVMManager(VMManager):
    """Manage Xen Instances


    insert() servers that can act as hypervisors into this VM manager
    """
    
    _driver_name = "xenvmmanager"

    #_properties = { # som configuration properties that help control how many VMs per CPU or something like that}

########NEW FILE########
__FILENAME__ = exceptions
class ClustoException(Exception):
    """base clusto exception"""
    pass

class DriverException(ClustoException):
    """exception for driver errors"""
    pass

class ConnectionException(ClustoException):
    """exception for operations related to connecting two Things together"""
    pass


class NameException(ClustoException):
    """exception for invalid entity or attribute names"""
    pass


class ResourceException(ClustoException):
    """exception related to resources"""
    pass

class ResourceNotAvailableException(ResourceException):
    pass

class ResourceTypeException(ResourceException):
    pass


class PoolException(ClustoException):
    pass

class TransactionException(ClustoException):
    pass

########NEW FILE########
__FILENAME__ = schema
"""
Clusto schema

"""

VERSION = 3
from sqlalchemy import *
from sqlalchemy.exc import OperationalError
from sqlalchemy.exceptions import InvalidRequestError

#from sqlalchemy.ext.sessioncontext import SessionContext
#from sqlalchemy.ext.assignmapper import assign_mapper

from sqlalchemy.orm import * #Mapper, MapperExtension
from sqlalchemy.orm.mapper import Mapper

from sqlalchemy.orm import mapperlib
import sqlalchemy.sql

import re
import sys
import datetime
import clusto
from functools import wraps


__all__ = ['ATTR_TABLE', 'Attribute', 'and_', 'ENTITY_TABLE', 'Entity', 'func',
           'METADATA', 'not_', 'or_', 'SESSION', 'select', 'VERSION',
           'latest_version', 'CLUSTO_VERSIONING', 'Counter', 'ClustoVersioning',
           'working_version', 'OperationalError', 'ClustoEmptyCommit']


METADATA = MetaData()


CLUSTO_VERSIONING = Table('clustoversioning', METADATA,
                          Column('version', Integer, primary_key=True),
                          Column('timestamp', TIMESTAMP, default=func.current_timestamp(), index=True),
                          Column('user', String(64), default=None),
                          Column('description', Text, default=None),
                          mysql_engine='InnoDB'

                          )

class ClustoEmptyCommit(Exception):
    pass

class ClustoSession(sqlalchemy.orm.interfaces.SessionExtension):

    def after_begin(self, session, transaction, connection):

        sql = CLUSTO_VERSIONING.insert().values(user=SESSION.clusto_user,
                                                description=SESSION.clusto_description)

        session.execute(sql)

        SESSION.clusto_description = None
        SESSION.flushed = set()

    def before_commit(self, session):

        if not any([session.is_modified(x) for x in session]) \
               and hasattr(SESSION, 'flushed') \
               and not SESSION.flushed:
            raise ClustoEmptyCommit()

    def after_commit(self, session):
        SESSION.flushed = set()

    def after_flush(self, session, flush_context):
        SESSION.flushed.update(x for x in session)


SESSION = scoped_session(sessionmaker(autoflush=True, autocommit=True,
                                      extension=ClustoSession()))


def latest_version():
    return select([func.coalesce(func.max(CLUSTO_VERSIONING.c.version), 0)])

def working_version():
    return select([func.coalesce(func.max(CLUSTO_VERSIONING.c.version),1)])

SESSION.clusto_version = working_version()
SESSION.clusto_user = None
SESSION.clusto_description = None

ENTITY_TABLE = Table('entities', METADATA,
                     Column('entity_id', Integer, primary_key=True),
                     Column('name', String(128, convert_unicode=True,
                                           assert_unicode=None),
                            nullable=False, ),
                     Column('type', String(32), nullable=False),
                     Column('driver', String(32), nullable=False),
                     Column('version', Integer, nullable=False),
                     Column('deleted_at_version', Integer, default=None),
                     mysql_engine='InnoDB'
                     )

Index('idx_entity_name_version',
      ENTITY_TABLE.c.name,
      ENTITY_TABLE.c.version,
      ENTITY_TABLE.c.deleted_at_version)

ATTR_TABLE = Table('entity_attrs', METADATA,
                   Column('attr_id', Integer, primary_key=True),
                   Column('entity_id', Integer,
                          ForeignKey('entities.entity_id'), nullable=False),
                   Column('key', String(256, convert_unicode=True,
                           assert_unicode=None),),
                   Column('subkey', String(256, convert_unicode=True,
                           assert_unicode=None), nullable=True,
                          default=None, ),
                   Column('number', Integer, nullable=True, default=None),
                   Column('datatype', String(32), default='string', nullable=False),

                   Column('int_value', Integer, default=None),
                   Column('string_value', Text(convert_unicode=True,
                           assert_unicode=None), default=None,),
                   Column('datetime_value', DateTime, default=None),
                   Column('relation_id', Integer,
                          ForeignKey('entities.entity_id'), default=None),

                   Column('version', Integer, nullable=False),
                   Column('deleted_at_version', Integer, default=None),
                   mysql_engine='InnoDB'

                   )
Index('idx_attrs_entity_version',
      ATTR_TABLE.c.entity_id,
      ATTR_TABLE.c.version,
      ATTR_TABLE.c.deleted_at_version)

Index('idx_attrs_key', ATTR_TABLE.c.key)
Index('idx_attrs_subkey', ATTR_TABLE.c.subkey)

DDL('CREATE INDEX idx_attrs_str_value on %(table)s (string_value(20))', on='mysql').execute_at("after-create", ATTR_TABLE)

DDL('CREATE INDEX idx_attrs_str_value on %(table)s ((substring(string_value,0,20)))', on='postgresql').execute_at("after-create", ATTR_TABLE)

DDL('CREATE INDEX idx_attrs_str_value on %(table)s (string_value)', on='sqlite').execute_at("after-create", ATTR_TABLE)

COUNTER_TABLE = Table('counters', METADATA,
                      Column('counter_id', Integer, primary_key=True),
                      Column('entity_id', Integer, ForeignKey('entities.entity_id'), nullable=False),
                      Column('attr_key', String(256, convert_unicode=True, assert_unicode=None)),
                      Column('value', Integer, default=0),
                      mysql_engine='InnoDB'
                      )

Index('idx_counter_entity_attr',
      COUNTER_TABLE.c.entity_id,
      COUNTER_TABLE.c.attr_key)

class ClustoVersioning(object):
    pass

class Counter(object):

    def __init__(self, entity, keyname, start=0):
        self.entity = entity
        self.attr_key = keyname

        self.value = start

        SESSION.add(self)
        SESSION.flush()

    def next(self):

        self.value = Counter.value + 1
        SESSION.flush()
        return self.value

    @classmethod
    def get(cls, entity, keyname, default=0):

        try:
            ctr = SESSION.query(cls).filter(and_(cls.entity==entity,
                                                 cls.attr_key==keyname)).one()

        except sqlalchemy.orm.exc.NoResultFound:
            ctr = cls(entity, keyname, default)

        return ctr

class ProtectedObj(object):

    ## this is a hack to make these objects immutable-ish
    writable = False

    @staticmethod
    def writer(func):
        @wraps(func)
        def newfunc(self, *args, **kwargs):
            self.writable = True
            res = func(self, *args, **kwargs)
            self.writable = False
            return res
        return newfunc

    def __setattr__(self, name, val):
        if (name.startswith('_sa_')
            or self.writable
            or name == 'writable'):
            super(ProtectedObj, self).__setattr__(name, val)
        else:
            raise Exception("Not Writable")




class Attribute(ProtectedObj):
    """Attribute class holds key/value pair

    An Attribute is a DB backed object that holds a key, number, subkey,
    and a value.

    Each Attribute is associated with an Entity.

    There can be multiple attributes with the same key, number, subkey, and/or
    value.

    Optionally you can explicitely set int_value, string_value,
    datetime_value, relation_id, and datatype.  These settings would override
    the values set by passing in 'value'.
    """

    @ProtectedObj.writer
    def __init__(self, entity, key, value=None,
                 subkey=None, number=None):

        self.entity = entity
        self.key = key

        self.value = value

        self.subkey = subkey
        self.version = working_version()
        if isinstance(number, bool) and number == True:
            counter = Counter.get(entity, key, default=-1)
            self.number = counter.next()
        elif isinstance(number, Counter):
            self.number = number.next()
        else:
            self.number = number


        SESSION.add(self)
        SESSION.flush()



    def __cmp__(self, other):

        if not isinstance(other, Attribute):
            raise TypeError("Can only compare equality with an Attribute. "
                            "Got a %s instead." % (type(other).__name__))

        return cmp(self.key, other.key)

    def __eq__(self, other):

        if not isinstance(other, Attribute):
            return False

        return ((self.key == other.key) and (self.value == other.value))

    def __repr__(self):

        params = ('key','value','subkey','number','datatype','version', 'deleted_at_version')
                  #'int_value','string_value','datetime_value','relation_id')


        vals = ((x,getattr(self,x)) for x in params)
        strs = ("%s=%s" % (key, ("'%s'" % val if isinstance(val,basestring) else '%s'%str(val))) for key, val in vals)

        s = "%s(%s)" % (self.__class__.__name__, ','.join(strs))

        return s

    def __str__(self):

        params = ('key','number','subkey','datatype',)

        val = "%s.%s %s" % (self.entity.name, '|'.join([str(getattr(self, param)) for param in params]), str(self.value))
        return val

    @property
    def is_relation(self):
        return self.datatype == 'relation'

    def get_value_type(self, value=None):
        if value == None:
            if self.datatype == None:
                valtype = "string"
            else:
                valtype = self.datatype
        else:
            valtype = self.get_type(value)

        return valtype + "_value"

    @property
    def keytuple(self):
        return (self.key, self.number, self.subkey)

    @property
    def to_tuple(self):
        return (self.key, self.number, self.subkey, self.value)

    @classmethod
    def get_type(self, value):

        if isinstance(value, (int,long)):
            if value > sys.maxint:
                raise ValueError("Can only store number between %s and %s"
                                 % (-sys.maxint-1, sys.maxint))
            datatype = 'int'
        elif isinstance(value, basestring):
            datatype = 'string'
        elif isinstance(value, datetime.datetime):
            datatype = 'datetime'
        elif isinstance(value, Entity):
            datatype = 'relation'
        elif hasattr(value, 'entity') and isinstance(value.entity, Entity):
            datatype = 'relation'
        else:
            datatype = 'string'

        return datatype


    def _get_value(self):

        if self.get_value_type() == 'relation_value':
            return clusto.drivers.base.Driver(getattr(self, self.get_value_type()))
        else:
            val = getattr(self, self.get_value_type())
            if self.datatype == 'int':
                return int(val)
            else:
                return val

    def _set_value(self, value):

        if not isinstance(value, sqlalchemy.sql.ColumnElement):
            self.datatype = self.get_type(value)
            if self.datatype == 'int':
                value = int(value)
        setattr(self, self.get_value_type(value), value)



    value = property(_get_value, _set_value)

    @ProtectedObj.writer
    def delete(self):
        ### TODO this seems like a hack

        self.deleted_at_version = working_version()

    @classmethod
    def queryarg(cls, key=None, value=(), subkey=(), number=()):

        args = [or_(cls.deleted_at_version==None,
                    cls.deleted_at_version>SESSION.clusto_version),
                cls.version<=SESSION.clusto_version]

        if key:
            args.append(Attribute.key==key)

        if number is not ():
            args.append(Attribute.number==number)

        if subkey is not ():
            args.append(Attribute.subkey==subkey)

        if value is not ():
            valtype = Attribute.get_type(value) + '_value'
            if valtype == 'relation_value':

                # get entity_id from Drivers too
                if hasattr(value, 'entity'):
                    e = value.entity
                else:
                    e = value

                args.append(getattr(Attribute, 'relation_id') == e.entity_id)

            else:
                args.append(getattr(Attribute, valtype) == value)

        return and_(*args)

    @classmethod
    def query(cls):
        return SESSION.query(cls).filter(or_(cls.deleted_at_version==None,
                                             cls.deleted_at_version>SESSION.clusto_version)).filter(cls.version<=SESSION.clusto_version)

class Entity(ProtectedObj):
    """
    The base object that can be stored and managed in clusto.

    An entity can have a name, type, and attributes.

    An Entity's functionality is augmented by Drivers which act as proxies for
    interacting with an Entity and its Attributes.
    """

    @ProtectedObj.writer
    def __init__(self, name, driver='entity', clustotype='entity'):
        """Initialize an Entity.

        @param name: the name of the new Entity
        @type name: C{str}
        @param attrslist: the list of key/value pairs to be set as attributes
        @type attrslist: C{list} of C{tuple}s of length 2
        """

        self.name = name

        self.driver = driver
        self.type = clustotype

        self.version = working_version()
        SESSION.add(self)
        SESSION.flush()

    def __eq__(self, otherentity):
        """Am I the same as the Other Entity.

        @param otherentity: the entity you're comparing with
        @type otherentity: L{Entity}
        """

        ## each Thing must have a unique name so I'll just compare those
        if not isinstance(otherentity, Entity):
            retval = False
        else:
            retval = self.name == otherentity.name

        return retval

    def __cmp__(self, other):

        if not hasattr(other, 'name'):
            raise TypeError("Can only compare equality with an Entity-like "
                            "object.  Got a %s instead."
                            % (type(other).__name__))

        return cmp(self.name, other.name)


    def __repr__(self):
        s = "%s(name=%s, driver=%s, clustotype=%s, version=%s, deleted_at_version=%s)"

        return s % (self.__class__.__name__,
                    self.name, self.driver, self.type, str(self.version), str(self.deleted_at_version))

    def __str__(self):
        "Return string representing this entity"

        return str(self.name)

    @property
    def attrs(self):
        return Attribute.query().filter(and_(Attribute.entity==self,
                                             and_(or_(ATTR_TABLE.c.deleted_at_version>SESSION.clusto_version,
                                                      ATTR_TABLE.c.deleted_at_version==None),
                                                  ATTR_TABLE.c.version<=SESSION.clusto_version))).all()

    @property
    def references(self):
        return Attribute.query().filter(and_(Attribute.relation_id==self.entity_id,
                                             and_(or_(ATTR_TABLE.c.deleted_at_version>SESSION.clusto_version,
                                                      ATTR_TABLE.c.deleted_at_version==None),
                                                  ATTR_TABLE.c.version<=SESSION.clusto_version))).all()


    def add_attr(self, *args, **kwargs):

        return Attribute(self, *args, **kwargs)

    @ProtectedObj.writer
    def delete(self):
        "Delete self and all references to self."

        clusto.begin_transaction()
        try:
            self.deleted_at_version = working_version()

            for i in self.references:
                i.delete()

            for i in self.attrs:
                i.delete()

            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x

    @classmethod
    def query(cls):
        return SESSION.query(cls).filter(or_(cls.deleted_at_version==None,
                                             cls.deleted_at_version>SESSION.clusto_version)).filter(cls.version<=SESSION.clusto_version)


    @ProtectedObj.writer
    def _set_driver_and_type(self, driver, clusto_type):
        """sets the driver and type for the entity

        this shouldn't be too dangerous, but be careful

        params:
          driver: the driver name
          clusto_type: the type name
        """

        try:
            clusto.begin_transaction()

            self.type = clusto_type
            self.driver = driver

            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x


mapper(ClustoVersioning, CLUSTO_VERSIONING)

mapper(Counter, COUNTER_TABLE,
       properties = {'entity': relation(Entity, lazy=True, uselist=False)},

       )

mapper(Attribute, ATTR_TABLE,
       properties = {'relation_value': relation(Entity, lazy=True,
                                                primaryjoin=ATTR_TABLE.c.relation_id==ENTITY_TABLE.c.entity_id,
                                                uselist=False,
                                                passive_updates=False),
                     'entity': relation(Entity, lazy=True, uselist=False,
                                        primaryjoin=ATTR_TABLE.c.entity_id==ENTITY_TABLE.c.entity_id)})


## might be better to make the relationships here dynamic_loaders in the long
## term.
mapper(Entity, ENTITY_TABLE,

       )

########NEW FILE########
__FILENAME__ = scripthelpers

import os
import sys
import clusto
import logging
import commands

from ConfigParser import SafeConfigParser
from optparse import OptionParser, make_option


scriptpaths = [os.path.realpath(os.path.join(os.curdir, 'scripts')),
               '/etc/clusto/scripts',
               '/usr/local/bin',
               '/usr/bin',
               ] #+ filter(lambda x: not x.endswith('.egg'), sys.path)

def list_clusto_scripts(path):
    """
    Return a list of clusto scripts in the given path.
    """

    if not os.path.exists(path):
        return []

    if os.path.isdir(path):
        dirlist = os.listdir(path)
    else:
        dirlist = [path]

    available = filter(lambda x: x.startswith("clusto-")
                       and not x.endswith('~')
                       and os.access(os.path.join(path,x), os.X_OK),
                       dirlist)

    
    return map(lambda x: os.path.join(path, x), available)

def runcmd(args):
    
    args[0] = 'clusto-' + args[0]
    cmdname = args[0]
    paths = os.environ['PATH'].split(':')

    cmd = None
    for path in paths:
        cmdtest = os.path.join(path, cmdname)
        if os.path.exists(cmdtest):
            cmd = cmdtest
            break

    if not cmd:
        raise CommandError(cmdname + " is not a clusto-command.")

    
    os.execvpe(cmdname, args, env=os.environ)


def get_command(cmdname):

    for path in scriptpaths:

        scripts = list_clusto_scripts(path)

        for s in scripts:
            if s.split('-')[1].split('.')[0] == cmdname:
                return s


    return None

def get_command_help(cmdname):

    fullpath = get_command(cmdname)

    return commands.getoutput(fullpath + " --help-description")
    
def get_clusto_config(filename=None):
    """Find, parse, and return the configuration data needed by clusto.

    Gets the config path from the CLUSTOCONFIG environment variable otherwise
    it is /etc/clusto/clusto.conf
    """

    filesearchpath = ['/etc/clusto/clusto.conf']

    
    filename = filename or os.environ.get('CLUSTOCONFIG')

    if not filename:
        filename = filesearchpath[0]

    if filename:
        if not os.path.exists(os.path.realpath(filename)):
            raise CmdLineError("Config file %s doesn't exist." % filename)
        
    config = SafeConfigParser()
    config.read([filename])

    if not config.has_section('clusto'):
        config.add_section('clusto')

    if 'CLUSTODSN' in os.environ:
        config.set('clusto', 'dsn', os.environ['CLUSTODSN'])

    if not config.has_option('clusto', 'dsn'):
        raise CmdLineError("No database given for clusto data.")

    return config


def init_script(name=os.path.basename(sys.argv[0]), configfile=None,
                initializedb=False):
    """Initialize the clusto environment for clusto scripts.

    Connects to the clusto database, returns a python SafeConfigParser and a
    logger.

    Uses get_clusto_config and setup_logging
    """
    config = get_clusto_config(filename=configfile)
    clusto.connect(config=config)

    if initializedb:
        clusto.init_clusto()
    
    logger = setup_logging(config=config, name=name)

    return (config, logger)


def setup_logging(config=None, name="clusto.script"):
    """Setup the default log level and return the logger

    The logger will try to log to /var/log and console.
    
    #FIXME shouldn't ignore the config
    """

    loglocation="/var/log"

    logfilename = os.path.join(loglocation,'clusto.log')
    
    if not (os.access(loglocation, os.W_OK) 
            or (os.path.exists(logfilename) and os.access(logfilename, os.W_OK))):
        logfilename = os.path.devnull
        
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=logfilename,
                        )
    

    log = logging.getLogger(name)

    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    log.addHandler(console)

    return log


def setup_clusto_env(options):
    """
    Take clusto parameters and put it into the shell environment.
    """


    if options.dsn:
        os.environ['CLUSTODSN'] = options.dsn
    if options.configfile:
        os.environ['CLUSTOCONFIG'] = options.configfile

    if os.environ.has_key('CLUSTOCONFIG'):
        config = get_clusto_config(os.environ['CLUSTOCONFIG'])
    else:
        config = get_clusto_config()

    if not os.environ.has_key('CLUSTODSN'):
        os.environ['CLUSTODSN'] = config.get('clusto','dsn')

    return config

class CmdLineError(Exception):
    pass

class CommandError(Exception):
    pass


class ClustoScript(object):

    usage = "%prog [options]"
    option_list = []
    num_args = None
    num_args_min = 0
    short_description = "sample short descripton"
    
    def __init__(self):
        self.parser = OptionParser(usage=self.usage,
                                   option_list=self.option_list)

        self.parser.add_option("--help-description",
                                action="callback",
                               callback=self._help_description,
                               dest="helpdesc",
                               help="print out the short command description")

        
    

    def _help_description(self, option, opt_str, value, parser, *args, **kwargs):

        print self.short_description
        sys.exit(0)
    


def runscript(scriptclass):

    script = scriptclass()

    (options, argv) = script.parser.parse_args(sys.argv)

    config, logger = init_script()

    try:
        if (script.num_args != None and script.num_args != (len(argv)-1)) or script.num_args_min > (len(argv)-1):
            raise CmdLineError("Wrong number of arguments.")
        
        retval = script.main(argv,
                             options,
                             config=config,
                             log=logger)

    except (CmdLineError, LookupError), msg:
        print msg
        script.parser.print_help()
        return 1

    
    return sys.exit(retval)

########NEW FILE########
__FILENAME__ = config
import os.path
import logging.handlers
import logging
import sys
import os

try:
    import simplejson as json
except ImportError:
    import json

LEVELS = {
    'DEBUG':    logging.DEBUG,
    'INFO':     logging.INFO,
    'WARNING':  logging.WARNING,
    'ERROR':    logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

files = [
    '/etc/clusto/services.conf',
    '%s/.clusto/services.conf' % os.environ.get('HOME', '/tmp'),
    'services.conf',
]

config = None
for filename in files:
    if os.path.exists(filename):
        try:
            config = json.load(file(filename, 'r'))
            break
        except:
            sys.stderr.write('Unable to parse config file %s: %s\n' % (filename, sys.exc_info()[1]))

if not config:
    sys.stderr.write('Unable to find services.conf!\n')

def conf(key, **kwargs):
    obj = config
    for k in key.split('.'):
        try:
            obj = obj[k]
        except KeyError, ke:
            if 'default' in kwargs.keys():
                return kwargs['default']
            else:
                raise KeyError(ke)
    return obj

def get_logger(name, level='INFO'):
    log = logging.getLogger(name)

    fmt = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S')
    stdout = logging.StreamHandler()
    stdout.setFormatter(fmt)

    fmt = logging.Formatter('%(name)s %(message)s')
    syslog = logging.handlers.SysLogHandler()
    syslog.setFormatter(fmt)

    log.addHandler(stdout)
    log.addHandler(syslog)
    log.setLevel(LEVELS[level])
    return log

########NEW FILE########
__FILENAME__ = dhcp
from traceback import format_exc
from struct import unpack
from errno import EINTR
from time import time
import socket
import signal

from clusto.services.config import conf, get_logger
log = get_logger('clusto.dhcp', 'INFO')

import logging
runtime = logging.getLogger('scapy.runtime')
runtime.setLevel(logging.ERROR)
loading = logging.getLogger('scapy.loading')
loading.setLevel(logging.ERROR)

from scapy.all import BOOTP, DHCP, DHCPTypes, DHCPOptions, DHCPRevOptions
from IPy import IP

import clusto

extra = conf('dhcp.extra_options')
extra = dict([(int(k), str(v)) for k, v in extra.items()])
DHCPOptions.update(extra)

for k,v in DHCPOptions.iteritems():
    if type(v) is str:
        n = v
        v = None
    else:
        n = v.name
    DHCPRevOptions[n] = (k,v)

class DHCPRequest(object):
    def __init__(self, packet):
        self.packet = packet
        self.parse()

    def parse(self):
        options = self.packet[DHCP].options
        hwaddr = ':'.join(['%02x' % ord(x) for x in self.packet.chaddr[:6]])

        mac = None
        vendor = None
        options = dict([x for x in options if isinstance(x, tuple)])
        if 'client_id' in options:
            mac = unpack('>6s', options['client_id'][1:])[0]
            options['client_id'] = ':'.join(['%02x' % ord(x) for x in mac]).lower()

        self.type = DHCPTypes[options['message-type']]
        self.hwaddr = hwaddr
        self.options = options

class DHCPResponse(object):
    def __init__(self, type, offerip=None, options={}, request=None):
        self.type = type
        self.offerip = offerip
        self.serverip = socket.gethostbyname(socket.gethostname())
        self.options = options
        self.request = request

    def set_type(self, type):
        self.type = type

    def build(self):
        options = [
            ('message-type', self.type)
        ]
        pxelinux = False
        for k, v in self.options.items():
            if k == 'enabled': continue
            if not k in DHCPRevOptions:
                log.warning('Unknown DHCP option: %s' % k)
                continue
            if k.startswith('pxelinux'):
                pxelinux = True
            if isinstance(v, unicode):
                v = v.encode('ascii', 'ignore')
            options.append((k, v))

        if pxelinux:
            options.append(('pxelinux-magic', '\xf1\x00\x75\x7e'))

        bootp_options = {
            'op': 2,
            'xid': self.request.packet.xid,
            'ciaddr': '0.0.0.0',
            'yiaddr': self.offerip,
            'chaddr': self.request.packet.chaddr,
        }
        if 'tftp_server' in self.options:
            bootp_options['siaddr'] = self.options['tftp_server']
        if 'tftp_filename' in self.options:
            bootp_options['file'] = self.options['tftp_filename']
        for k, v in bootp_options.items():
            if isinstance(v, unicode):
                bootp_options[k] = v.encode('ascii', 'ignore')

        pkt = BOOTP(**bootp_options)/DHCP(options=options)
        #pkt.show()
        return pkt.build()

class DHCPServer(object):
    def __init__(self, bind_address=('0.0.0.0', 67)):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(bind_address)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_id = socket.gethostbyname(socket.gethostname())

    def run(self):
        while True:
            try:
                data, address = self.sock.recvfrom(4096)
            except KeyboardInterrupt:
                break
            except socket.error, e:
                if e.args[0] == EINTR:
                    continue
                log.error(format_exc())
                break
            packet = BOOTP(data)
            request = DHCPRequest(packet)

            log.debug('%s %s' % (request.type, request.hwaddr))

            methodname = 'handle_%s' % request.type
            if hasattr(self, methodname):
                method = getattr(self, methodname)
                try:
                    method(request)
                except:
                    log.error(format_exc())
                    continue

    def send(self, address, data):
        while data:
            bytes = self.sock.sendto(str(data), 0, (address, 68))
            data = data[bytes:]

class ClustoDHCPServer(DHCPServer):
    def __init__(self):
        DHCPServer.__init__(self)
        self.offers = {}
        log.info('Clusto DHCP server starting')

    def handle_request(self, request):
        chaddr = request.packet.chaddr
        if not chaddr in self.offers:
            log.warning('Got a request before sending an offer from %s' % request.hwaddr)
            return
        response = self.offers[chaddr]
        response.type = 'ack'

        self.send('255.255.255.255', response.build())

    def handle_discover(self, request):
        if conf('dhcp.update_ipmi'):
            self.update_ipmi(request)

        attrs = [{
            'key': 'port-nic-eth',
            'subkey': 'mac',
            'number': 1,
            'value': request.hwaddr,
        }]
        server = clusto.get_entities(attrs=attrs)

        if not server:
            return

        if len(server) > 1:
            log.warning('More than one server with address %s: %s' % (request.hwaddr, ', '.join([x.name for x in server])))
            return
        
        server = server[0]

        enabled = server.attrs(key='dhcp', subkey='enabled', merge_container_attrs=True)
        if not enabled or not enabled[0].value:
            log.info('DHCP not enabled for %s' % server.name)
            return

        ip = server.attrs(key='ip', subkey='ipstring')
        if not ip:
            log.info('No IP assigned for %s' % server.name)
            return
        else:
            ip = ip[0].value

        ipman = server.attrs(key='ip', subkey='manager')
        if not ipman:
            log.info('Could not find the ip manager for %s' % server.name)
            return
        else:
            ipman = ipman[0].value
        ipman = dict([(x.key, x.value) for x in ipman.attrs(subkey='property')])
        #ipman = dict([(x['key'], x['value']) for x in clusto.get_ip_manager(ip).attrs() if x['subkey'] == 'property'])
        ipy = IP('%s/%s' % (ip, ipman['netmask']), make_net=True)

        options = {
            'server_id': self.server_id,
            'lease_time': 3600,
            'renewal_time': 1600,
            'subnet_mask': ipman['netmask'],
            'broadcast_address': ipy.broadcast().strNormal(),
            'router': ipman['gateway'],
            'hostname': server.hostname,
        }

        log.info('Sending offer to %s, options: %s' % (server.name, options))

        for attr in server.attrs(key='dhcp', merge_container_attrs=True):
            options[attr.subkey] = attr.value

        response = DHCPResponse(type='offer', offerip=ip, options=options, request=request)
        self.offers[request.packet.chaddr] = response
        self.send('255.255.255.255', response.build())

    def update_ipmi(self, request):
        attrs = [{
            'key': 'bootstrap',
            'subkey': 'mac',
            'value': request.hwaddr,
        }, {
            'key': 'port-nic-eth',
            'subkey': 'mac',
            'number': 1,
            'value': request.hwaddr,
        }]
        server = clusto.get_entities(attrs=attrs)

        if not server:
            return

        try:
            server = server[0]
            if request.options.get('vendor_class_id', None) == 'udhcp 0.9.9-pre':
                # This is an IPMI request
                #logging.debug('Associating IPMI %s %s' % (request.hwaddr, server.name))
                server.set_port_attr('nic-eth', 1, 'ipmi-mac', request.hwaddr)
            else:
                #logging.debug('Associating physical %s %s' % (requst.hwaddr, server.name))
                server.set_port_attr('nic-eth', 1, 'mac', request.hwaddr)
        except:
            log.error('Error updating server MAC: %s' % format_exc())


########NEW FILE########
__FILENAME__ = http
#!/usr/bin/env python
try:
    import simplejson as json
except ImportError:
    import json

from webob import Request, Response
from traceback import format_exc
from urllib import unquote_plus
import xmlrpclib
import cPickle
import new
import re

from clusto.drivers import Driver, IPManager
import clusto

from clusto.services.config import conf, get_logger
log = get_logger('clusto.http', 'INFO')

def xmldumps(obj, **kwargs):
    return xmlrpclib.dumps((obj,), **kwargs)

formats = {
    'json': (json.dumps, json.loads, {'indent': 4}),
    'pickle': (cPickle.dumps, cPickle.loads, {}),
    'xml': (xmldumps, xmlrpclib.loads, {'methodresponse': True, 'allow_none': True}),
}

try:
    import yaml
    formats['yaml'] = (yaml.dump, yaml.load, {'indent': 4})
except ImportError:
    pass

def unclusto(obj):
    '''
    Convert an object to a representation that can be safely serialized into
    JSON.
    '''
    if type(obj) in (str, unicode, int) or obj == None:
        return obj
    if isinstance(obj, clusto.Attribute):
        return {
            'key': obj.key,
            'value': unclusto(obj.value),
            'subkey': obj.subkey,
            'number': obj.number,
            'datatype': obj.datatype
        }
    if issubclass(obj.__class__, Driver):
        return '/%s/%s' % (obj.type, obj.name)
    return str(obj)

def dumps(request, obj):
    format = request.params.get('format', 'json')
    dumpfunc, loadfunc, kwargs = formats[format]
    result = dumpfunc(obj, **kwargs)
    if format == 'json' and 'callback' in request.params:
        callback = request.params['callback']
        result = '%s(%s)' % (callback, result)
    return result

def loads(request, obj):
    format = request.params.get('format', 'json')
    dumpfunc, loadfunc, kwargs = formats[format]
    return loadfunc(obj)

class EntityAPI(object):
    def __init__(self, obj):
        self.obj = obj
        self.url = '/%s/%s' % (self.obj.type, self.obj.name)

    def addattr(self, request):
        '''
        Add an attribute to this object.

        Requires HTTP parameters "key" and "value"
        Optional parameters are "subkey" and "number"
        '''
        kwargs = dict(request.params.items())
        self.obj.add_attr(**kwargs)
        clusto.commit()
        return self.show(request)

    def delattr(self, request):
        '''
        Delete an attribute from this object.

        Requires HTTP parameter "key"
        '''
        self.obj.del_attrs(request.params['key'])
        clusto.commit()
        return self.show(request)

    def attrs(self, request):
        '''
        Query attributes from this object.
        '''
        result = {
            'attrs': []
        }
        kwargs = dict(request.params.items())
        for attr in self.obj.attrs(**kwargs):
            result['attrs'].append(unclusto(attr))
        return Response(status=200, body=dumps(request, result))

    def insert(self, request):
        '''
        Insert an object into this object

        Requires a "device" attribute, which is the absolute URL path to the
        object to be inserted.

        For example: /pool/examplepool/insert?object=/server/exampleserver
        '''
        device = request.params['object'].strip('/').split('/')[1]
        device = clusto.get_by_name(device)
        self.obj.insert(device)
        clusto.commit()
        return self.show(request)

    def remove(self, request):
        '''
        Remove a device from this object.

        Requires a "device" attribute, which is the absolute URL path to the
        object to be removed.

        For example: /pool/examplepool/remove?object=/server/exampleserver
        '''
        device = request.params['object'].strip('/').split('/')[1]
        device = clusto.get_by_name(device)
        self.obj.remove(device)
        clusto.commit()
        return self.show(request)

    def show(self, request):
        '''
        Returns attributes and actions available for this object.
        '''
        result = {}
        result['object'] = self.url

        attrs = []
        for x in self.obj.attrs():
            attrs.append(unclusto(x))
        result['attrs'] = attrs
        result['contents'] = [unclusto(x) for x in self.obj.contents()]
        result['parents'] = [unclusto(x) for x in self.obj.parents()]
        result['actions'] = [x for x in dir(self) if not x.startswith('_') and callable(getattr(self, x))]

        return Response(status=200, body=dumps(request, result))

class PortInfoAPI(EntityAPI):
    def ports(self, request):
        '''
        Returns a list of ports within this object and any information about
        connections between those ports and other devices.
        '''
        result = {}
        result['object'] = self.url
        result['ports'] = []
        for port in self.obj.port_info_tuples:
            porttype, portnum, otherobj, othernum = [unclusto(x) for x in port]
            result['ports'].append({
                'type': porttype,
                'num': portnum,
                'other': otherobj,
                'othernum': othernum,
            })

        return Response(status=200, body=dumps(request, result))

    def set_port_attr(self, request):
        kwargs = {}
        params = request.params
        for arg in ('porttype', 'portnum', 'key', 'value'):
            if not arg in params:
                return Response(status=400, body='Required argument "%s" is missing\n' % arg)
            kwargs[arg] = params[arg]

        try:
            kwargs['portnum'] = int(kwargs['portnum'])
        except ValueError:
            return Response(status=400, body='portnum must be an integer\n')

        self.obj.set_port_attr(**kwargs)
        return Response(status=200)

    def get_port_attr(self, request):
        kwargs = {}
        params = request.params
        for arg in ('porttype', 'portnum', 'key'):
            if not arg in params:
                return Response(status=400, body='Required argument "%s" is missing\n' % arg)
            kwargs[str(arg)] = params[arg]

        try:
            kwargs['portnum'] = int(kwargs['portnum'])
        except ValueError:
            return Response(status=400, body='portnum must be an integer\n')

        return Response(status=200, body=dumps(request, self.obj.get_port_attr(**kwargs)))

class RackAPI(EntityAPI):
    def insert(self, request):
        '''
        Insert a device into a rack.

        This method is overridden to require a "ru" parameter in addition to
        "device"

        Example: /rack/examplerack/insert?object=/server/exampleserver&ru=6
        '''
        device = request.params['object'].strip('/').split('/')[1]
        device = clusto.get_by_name(device)
        self.obj.insert(device, int(request.params['ru']))
        clusto.commit()
        return self.contents(request)

class ResourceAPI(EntityAPI):
    def allocate(self, request):
        '''
        Allocate a new object of the given type
        '''
        driver = clusto.DRIVERLIST[request.params['driver']]
        device = self.obj.allocate(driver)
        clusto.commit()
        return Response(status=201, body=dumps(request, unclusto(device)))

class QueryAPI(object):
    @classmethod
    def get_entities(self, request):
        kwargs = {'attrs': []}
        for k, v in request.params.items():
            if k in ('format', 'callback'): continue
            v = loads(request, unquote_plus(v))
            kwargs[str(k)] = v

        attrs = []
        for attr in kwargs['attrs']:
            attrs.append(dict([(str(k), v) for k, v in attr.items()]))
        kwargs['attrs'] = attrs

        result = [unclusto(x) for x in clusto.get_entities(**kwargs)]
        return Response(status=200, body=dumps(request, result))

    @classmethod
    def get_by_name(self, request):
        if not 'name' in request.params:
            return Response(status=400, body='400 Bad Request\nYou must specify a "name" parameter\n')
        name = request.params['name']
        obj = clusto.get_by_name(name)
        api = EntityAPI(obj)
        return api.show(request)

    @classmethod
    def get_from_pools(self, request):
        if not 'pools' in request.params:
            return Response(status=400, body='400 Bad Request\nYou must specify at least one pool\n')
        pools = request.params['pools'].split(',')

        if 'types' in request.params:
            clusto_types = request.params['types'].split(',')
        else:
            clusto_types = None

        result = [unclusto(x) for x in clusto.get_from_pools(pools, clusto_types)]
        return Response(status=200, body=dumps(request, result))

    @classmethod
    def get_ip_manager(self, request):
        if not 'ip' in request.params:
            return Response(status=400, body='400 Bad Request\nYou must specify an IP\n')

        try:
            ipman = IPManager.get_ip_manager(request.params['ip'])
        except:
            return Response(status=404, body='404 Not Found\n')
        return Response(status=200, body=dumps(request, unclusto(ipman)))

class ClustoApp(object):
    def __init__(self):
        self.urls = [
            ('^/favicon.ico$',
                self.notfound),
            ('^/search$',
                self.search),
            ('^/query/(?P<querytype>[a-z_]+)',
                self.query_delegate),
            ('^/(?P<objtype>\w+)/(?P<name>[-\w0-9]+)/(?P<action>\w+)',
                self.action_delegate),
            ('^/(?P<objtype>\w+)/(?P<name>[-\w0-9]+)',
                self.action_delegate),
            ('^/(?P<objtype>\w+)',
                self.types_delegate),
            ('^/',
                self.default_delegate),
        ]
        self.urls = [(re.compile(pattern), obj) for pattern, obj in self.urls]

        self.types = {
            'server': PortInfoAPI,
            'consoleserver': PortInfoAPI,
            'networkswitch': PortInfoAPI,
            'powerstrip': PortInfoAPI,
            'rack': RackAPI,
            'resource': ResourceAPI,
        }

    def default_delegate(self, request, match):
        return Response(status=200, body=dumps(request, ['/' + x for x in clusto.typelist.keys()]))

    def types_delegate(self, request, match):
        objtype = match.groupdict()['objtype']
        result = []
        for obj in clusto.get_entities(clusto_types=(objtype,)):
            result.append(unclusto(obj))
        return Response(status=200, body=dumps(request, result))

    def action_delegate(self, request, match):
        if request.method == 'GET':
            return self.get_action(request, match)

        if request.method == 'POST':
            return self.post_action(request, match)

        if request.method == 'DELETE':
            return self.delete_action(request, match)

        return Response(status=501, body='501 Not Implemented\n')

    def query_delegate(self, request, match):
        querytype = match.groupdict()['querytype']

        if hasattr(QueryAPI, querytype):
            method = getattr(QueryAPI, querytype)
            return method(request)
        else:
            return Response(status=400, body='400 Bad Request\nThere is no such query\n')

    def post_action(self, request, match):
        name = request.path_info.strip('/')
        if name.count('/') != 1:
            return Response(status=400, body='400 Bad Request\nYou may only create objects, not types or actions\n')
        objtype, objname = name.split('/', 1)

        try:
            obj = clusto.get_by_name(objname)
            if obj:
                return Response(status=409, body='409 Conflict\nObject already exists\n')
        except LookupError: pass

        obj = clusto.typelist[objtype](objname)

        obj = EntityAPI(obj)
        response = obj.show(request)
        response.status = 201
        return response

    def delete_action(self, request, match):
        name = request.path_info.strip('/')
        if name.count('/') != 1:
            return Response(status=400, body='400 Bad Request\nYou may only delete objects, not types or actions\n')
        objtype, objname = name.split('/', 1)

        try:
            obj = clusto.get_by_name(objname)
        except LookupError:
            return Response(status=404, body='404 Not Found\n')

        clusto.delete_entity(obj.entity)
        clusto.commit()
        return Response(status=200, body='200 OK\nObject deleted\n')

    def get_action(self, request, match):
        group = match.groupdict()
        try:
            obj = clusto.get_by_name(group['name'])
        except LookupError:
            return Response(status=404, body='404 Not Found\n')

        if obj.type != group['objtype']:
            response = Response(status=302)
            response.headers.add('Location', str('/%s/%s/%s' % (obj.type, obj.name, group.get('action', ''))))
            return response

        action = group.get('action', 'show')
        handler = self.types.get(group['objtype'], EntityAPI)
        if not obj:
            obj = clusto.get_by_name(group['name'])
        h = handler(obj)
        if hasattr(h, action):
            f = getattr(h, action)
            response = f(request)
        else:
            response = Response(status=404, body='404 Not Found\nInvalid action\n')
        return response

    def search(self, request, match):
        query = request.params.get('q', None)
        if not query:
            return Response(status=400, body='400 Bad Request\nNo query specified\n')

        result = []
        for obj in clusto.get_entities():
            if obj.name.find(query) != -1:
                result.append(unclusto(obj))
        return Response(status=200, body=dumps(request, result))

    def notfound(self, request, match):
        return Response(status=404)

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = Response(status=404, body='404 Not Found\nUnmatched URL\n')

        for pattern, handler in self.urls:
            match = pattern.match(request.path_info)
            if match:
                try:
                    response = handler(request, match)
                except:
                    response = Response(status=500, body=format_exc())
                break

        return response(environ, start_response)

########NEW FILE########
__FILENAME__ = snmp
#!/usr/bin/env python
from socket import socket, AF_INET, SOCK_DGRAM
from traceback import format_exc
from time import strftime, time, localtime, sleep
from struct import unpack
import sys

import logging

from clusto.services.config import conf, get_logger
log = get_logger('clusto.snmp', 'INFO')

import logging
runtime = logging.getLogger('scapy.runtime')
runtime.setLevel(logging.ERROR)
loading = logging.getLogger('scapy.loading')
loading.setLevel(logging.ERROR)

from scapy.all import SNMP

from clusto.drivers import IPManager, PenguinServer
import clusto

sys.path.insert(0, '/var/lib/clusto')
import rackfactory

def update_clusto(trap):
    ts = strftime('[%Y-%m-%d %H:%M:%S]')
    if trap['operation'] != 1:
        return

    if not trap['mac'].startswith('00'):
        return

    switch = IPManager.get_devices(trap['switch'])
    if not switch:
        log.warning('Unknown trap source: %s' % trap['switch'])
        return
    else:
        switch = switch[0]

    if not switch.attrs(key='snmp', subkey='discovery', value=1, merge_container_attrs=True):
        log.debug('key=snmp, subkey=discovery for %s not set to 1, ignoring trap' % switch.name)
        return

    rack = switch.parents(clusto_types=['rack'])[0]

    try:
        factory = rackfactory.get_factory(rack.name)
        if not factory:
            log.warning('Unable to locate rack factory for %s' % rack.name)
            return
    except:
        log.error(format_exc())
        return

    server = switch.get_connected('nic-eth', trap['port'])
    if not server:
        servernames = clusto.get_by_name('servernames')
        clusto.SESSION.clusto_description = 'SNMP allocate new server'
        driver = factory.get_driver(trap['port'])
        server = servernames.allocate(driver)
        log.info('Created new %s on %s port %s: %s' % (driver.__name__, trap['switch'], trap['port'], server.name))

    try:
        clusto.begin_transaction()
        if not trap['mac'] in server.attr_values(key='bootstrap', subkey='mac', value=trap['mac']):
            log.debug('Adding bootstrap mac to', server.name)
            server.add_attr(key='bootstrap', subkey='mac', value=trap['mac'])

        factory.add_server(server, trap['port'])
        switch.set_port_attr('nic-eth', trap['port'], 'vlan', trap['vlan'])

        clusto.SESSION.clusto_description = 'SNMP update MAC and connections on %s' % server.name
        clusto.commit()
    except:
        log.error(format_exc())
        clusto.rollback_transaction()

    log.debug(repr(trap))

def trap_listen():
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('0.0.0.0', 162))
    while True:
        data, address = sock.recvfrom(4096)
        trap = SNMP(data)

        for var in trap.PDU.varbindlist:
            if var.oid.val == '1.3.6.1.4.1.9.9.215.1.1.8.1.2.1':
                var.value.val = var.value.val[:11]
                operation, vlan, mac, port = unpack('>cH6sH', var.value.val)
                result = {
                    'operation': ord(operation),
                    'vlan': vlan,
                    'mac': ':'.join([('%x' % ord(x)).rjust(2, '0') for x in mac]).lower(),
                    'port': port,
                    'switch': address[0],
                }
                yield result

########NEW FILE########
__FILENAME__ = alltests

if __name__ == '__main__':

    import os
    import sys


    sys.path.append(os.path.realpath('.'))


import unittest
import clusto.test


def gettests(tests=None):
    if not tests:
        tests = ('clusto.test.base', 'clusto.test.drivers',
                 'clusto.test.usage',)

    suite = unittest.defaultTestLoader.loadTestsFromNames(tests)

    return suite


def runtests(tests=None, db='sqlite:///:memory:', echo=False):

    clusto.test.testbase.DB=db
    clusto.test.testbase.ECHO=echo
    suite = gettests(tests)
    runner = unittest.TextTestRunner()    
    runner.run(suite)




if __name__ == '__main__':

    import optparse

    parser = optparse.OptionParser()
    parser.add_option('--db', dest='dsn', 
                      help='specifies which db to test against',
                      default='sqlite:///:memory:')
    parser.add_option('--echo', dest='echo', action='store_true', default=False,
                      help="Echo sqlalchemy sql")
    
    (options, args) = parser.parse_args()
    runtests(args, options.dsn, options.echo)

########NEW FILE########
__FILENAME__ = clustotests
import unittest
from clusto.test import testbase

import clusto
from clusto.schema import *
from clusto.drivers.base import *
from clusto.drivers import BasicDatacenter, Pool, BasicServer, IPManager
from sqlalchemy.exceptions import InvalidRequestError

class TestClustoPlain(testbase.ClustoTestBase):

    def testInitClustoIdempotent(self):

        clusto.init_clusto()
        clusto.init_clusto()
        clusto.init_clusto()
        clusto.init_clusto()

        self.assertEqual(SESSION.query(ClustoVersioning).count(), 2)



class TestClusto(testbase.ClustoTestBase):
    def data(self):

        Entity('e1')
        Entity('e2')
        Entity('e3')

        clusto.flush()


    def testClustoMeta(self):

        cm = clusto.get_by_name('clustometa')

        self.assertEqual(cm.schemaversion, VERSION)

    def testGetByName(self):

        e1 = Entity.query().filter_by(name='e1').one()

        q = clusto.get_by_name('e1')

        self.assertEqual(q, e1)

        self.assertEqual(q.name, 'e1')

    def testSimpleRename(self):

        clusto.rename('e1', 'f1')

        q = Entity.query()

        self.assertEqual(q.filter_by(name='e1').count(), 0)

        self.assertEqual(q.filter_by(name='f1').count(), 1)


    def testChangeDriver(self):

        d = Driver('d1')
        d.add_attr('foo', 1)

        self.assertEqual(d.driver, Driver._driver_name)

        self.assertRaises(Exception, setattr, d.entity, driver, 'foo')

        clusto.change_driver(d.name, BasicServer)

        self.assertRaises(DriverException, clusto.change_driver, d.name, str)

        d = clusto.get_by_name('d1')

        self.assertEqual(d.driver, BasicServer._driver_name)
        self.assertTrue(isinstance(d, BasicServer))

        self.assertEqual(d.attr_value('foo'), 1)


    def testTransactionRollback(self):

        clusto.begin_transaction()

        d1 = Entity('d1')

        clusto.get_by_name('d1')

        d2 = Entity('d2')
        clusto.rollback_transaction()


        self.assertRaises(LookupError, clusto.get_by_name, 'd1')

    def testTransactionRollback2(self):

        try:
            clusto.begin_transaction()

            c1 = Entity('c1')

            raise Exception()
        except Exception:

            clusto.rollback_transaction()

        c2 = Entity('c2')

        self.assertRaises(LookupError, clusto.get_by_name, 'c1')
        clusto.get_by_name('c2')

    def testTransactionRollback3(self):

        d1 = Entity('d1')

        clusto.begin_transaction()
        d2 = Entity('d2')
        clusto.rollback_transaction()

        clusto.get_by_name('d1')
        self.assertRaises(LookupError, clusto.get_by_name, 'd2')

    def testTransactionRollback4(self):

        d1 = Driver('d1')

        try:
            clusto.begin_transaction()

            d2 = Driver('d2')

            try:
                clusto.begin_transaction()
                d2.add_attr('foo', 'bar')

                clusto.commit()

            except:
                clusto.rollback_transaction()

            d1.add_attr('foo2', 'bar2')

            raise Exception()
            clusto.commit()
        except:
            clusto.rollback_transaction()

        self.assertEqual(d1.attrs(), [])
        self.assertRaises(LookupError, clusto.get_by_name, 'd2')


    def testTransactionCommit(self):

        try:
            clusto.begin_transaction()

            c1 = Entity('c1')
            clusto.commit()
        except Exception:
            clusto.rollback_transaction()

        clusto.get_by_name('c1')


    def testGetEntities(self):

        d1 = Driver('d1')
        dv1 = Device('dv1')
        Location('l1')
        BasicDatacenter('dc1')


        namelist = ['e1', 'e2', 'dv1']

        self.assertEqual(sorted([n.name
                                 for n in clusto.get_entities(names=namelist)]),
                         sorted(namelist))

        dl = [Driver]
        self.assertEqual(sorted([n.name
                                 for n in clusto.get_entities(clusto_drivers=dl)]),
                         sorted(['d1','e1','e2','e3']))


        tl = [Location, BasicDatacenter]
        self.assertEqual(sorted([n.name
                                 for n in clusto.get_entities(clusto_types=tl)]),
                         sorted(['l1','dc1']))

        p1 = Pool('p1')
        p2 = Pool('p2')
        p3 = Pool('p3')
        p4 = Pool('p4')

        s1 = BasicServer('s1')
        s2 = BasicServer('s2')
        s3 = BasicServer('s3')

        p1.insert(s1)
        p1.insert(s2)

        p2.insert(s2)
        p2.insert(s3)
        p2.insert(d1)

        p3.insert(s3)
        p3.insert(d1)
        p3.insert(s1)

        p4.insert(p3)


        self.assertEqual(sorted([s2,s3]),
                         sorted(clusto.get_from_pools(pools=[p2],
                                                      clusto_types=[BasicServer])))

        self.assertEqual(sorted([s2]),
                         sorted(clusto.get_from_pools(pools=[p2, 'p1'],
                                                      clusto_types=[BasicServer])))
        self.assertEqual(sorted([s3]),
                         sorted(clusto.get_from_pools(pools=['p2', 'p3'],
                                                      clusto_types=[BasicServer])))

        self.assertEqual(sorted([s1]),
                         sorted(clusto.get_from_pools(pools=['p4', 'p1'],
                                                      clusto_types=[BasicServer])))

    def testGetEntitesWithAttrs(self):

        d1 = Driver('d1')
        d2 = Driver('d2')
        d3 = Driver('d3')
        d4 = Driver('d4')

        d1.add_attr('k1', 'test')
        d2.add_attr('k1', 'testA')

        d1.add_attr('k2', number=1, subkey='A', value=67)
        d3.add_attr('k3', number=True, value=d4)



        self.assertEqual(clusto.get_entities(attrs=[{'key':'k2'}]),
                         [d1])


        self.assertEqual(sorted(clusto.get_entities(attrs=[{'key':'k1'}])),
                         sorted([d1,d2]))


        self.assertEqual(sorted(clusto.get_entities(attrs=[{'value':d4}])),
                         [d3])


        self.assertEqual(clusto.get_entities(attrs=[{'value':67}]),
                         [d1])

        self.assertEqual(sorted(clusto.get_entities(attrs=[{'number':0}])),
                         sorted([d3]))

        self.assertEqual(clusto.get_entities(attrs=[{'subkey':'A'},
                                                   {'value':'test'}]),
                         [d1])

    def testGet(self):
        s1 = BasicServer('s1')
        s2 = BasicServer('s2')
        s3 = BasicServer('s3')
        ipm = IPManager('testnet', baseip='10.0.0.0', netmask='255.255.255.0')

        s1.set_attr(key='system', subkey='serial', value='P0000000000')
        s2.set_port_attr('nic-eth', 1, 'mac', '00:11:22:33:44:55')
        s3.bind_ip_to_osport('10.0.0.1', 'eth0')

        self.assertEqual(clusto.get('s1')[0], s1)
        self.assertEqual(clusto.get('00:11:22:33:44:55')[0], s2)
        self.assertEqual(clusto.get('10.0.0.1')[0], s3)
        self.assertEqual(clusto.get('P0000000000')[0], s1)
        self.assertEqual(clusto.get('foo'), None)
        self.assertRaises(ValueError, clusto.get, None)

    def testDeleteEntity(self):

        e1 = Entity.query().filter_by(name='e1').one()

        d = Driver(e1)

        d.add_attr('deltest1', 'test')
        d.add_attr('deltest1', 'testA')



        clusto.delete_entity(e1)


        self.assertEqual([], clusto.get_entities(names=['e1']))

        self.assertEqual([], Driver.do_attr_query(key='deltest*', glob=True))



    def testDriverSearches(self):

        d = Driver('d1')

        self.assertRaises(NameError, clusto.get_driver_name, 'FAKEDRIVER')

        self.assertEqual(clusto.get_driver_name(Driver),
                         'entity')

        self.assertRaises(LookupError, clusto.get_driver_name, 123)

        self.assertEqual(clusto.get_driver_name('entity'),
                         'entity')

        self.assertEqual(clusto.get_driver_name(d.entity),
                         'entity')

    def testTypeSearches(self):

        d = Driver('d1')

        self.assertEqual(clusto.get_type_name('generic'),
                         'generic')

        self.assertEqual(clusto.get_type_name(d.entity),
                         'generic')

        self.assertRaises(LookupError, clusto.get_type_name, 123)


    def testAttributeOldVersionsInGetEntities(self):

        sl = [BasicServer('s' + str(x)) for x in range(10)]
        for n, s in enumerate(sl):
            s.add_attr(key='old', value="val")
            s.del_attrs(key='old')
            s.add_attr(key='new', value='foo')

        l=clusto.get_entities(attrs=[{'key':'old', 'value':'val'}])

        self.assertEqual(l, [])


    def testSiblings(self):

        d1 = Driver('d1')
        d2 = Driver('d2')
        d3 = Driver('d3')
        d4 = Driver('d4')
        d5 = Driver('d5')
        d6 = Driver('d6')
        d7 = Driver('d7')
        d8 = Driver('d8')

        db = Pool('db')
        web = Pool('web')
        dev = Pool('dev')
        prod = Pool('prod')
        alpha = Pool('alpha')
        beta = Pool('beta')

        db.set_attr('pooltype', 'role')
        web.set_attr('pooltype', 'role')

        db.insert(d1)
        db.insert(d2)
        db.insert(d3)
        db.insert(d7)
        db.insert(d8)

        web.insert(d4)
        web.insert(d5)
        web.insert(d6)
        web.insert(d7)

        map(prod.insert, [d1,d2,d4,d5])

        map(dev.insert, [d3,d6,d7,d8])

        map(alpha.insert, [d7, d8])
        map(beta.insert, [d3,d6])


        self.assertEquals(sorted([d2]),
                          sorted(d1.siblings()))

        self.assertEquals(sorted(d3.siblings()),
                          sorted([]))

        self.assertEquals(sorted(d3.siblings(parent_filter=lambda x: not x.attr_values('pooltype', 'role'),
                                             additional_pools=[web])),
                          sorted([d6]))

        self.assertEquals(sorted(d7.siblings(parent_filter=lambda x: not x.attr_values('pooltype', 'role'),
                                             additional_pools=[db])),
                          sorted([d8]))

########NEW FILE########
__FILENAME__ = countertests
import unittest
from clusto.test import testbase

import clusto
from clusto.schema import *
from clusto.drivers.base import *
from clusto.drivers import BasicDatacenter
from sqlalchemy.exceptions import InvalidRequestError

class TestClustoCounter(testbase.ClustoTestBase):

    def testCounterDefault(self):


        e = Entity('e1')
        c = Counter(e, 'key1')

        self.assertEqual(c.value, 0)

        d = Counter(e, 'key2', start=10)

        self.assertEqual(d.value, 10)

    def testCounterIncrement(self):
    
        e = Entity('e1')
        c = Counter(e, 'key1')

                         
        c.next()
        c.next()
        self.assertEqual(c.value,2)

    def testGetCounter(self):

        e = Entity('e1')

        c = Counter.get(e, 'key1')

        c.next()
        self.assertEqual(c.value, 1)


        d = Counter.get(e, 'key1', default=100)
        d.next()
        self.assertEqual(d.value, 2)

        f = Counter.get(e, 'key2', default=20)
        self.assertEqual(f.value, 20)


########NEW FILE########
__FILENAME__ = drivertests
"""
Test the basic Driver object
"""

import unittest
from clusto.test import testbase
import datetime

import clusto
from clusto import Attribute
from clusto.drivers.base import *
from clusto.drivers import Pool
from clusto.exceptions import *

class TestDriverAttributes(testbase.ClustoTestBase):

    def testSetAttrs(self):

        d1 = Driver('d1')
        d1.set_attr('foo', 'bar')

        self.assertEqual(d1.attr_items(),
                         [(('foo', None, None), 'bar')])

        d1.set_attr('foo', 'bar2')
        self.assertEqual(d1.attr_items(),
                         [(('foo', None, None), 'bar2')])

        d1.add_attr('foo', 'bar3')

        self.assertEqual(sorted(d1.attr_items()),
                         sorted(
                         [(('foo', None, None), 'bar2'),
                          (('foo', None, None), 'bar3')]))

        self.assertRaises(DriverException, d1.set_attr, 'foo', 'bar4')


        d2 = Driver('d2')
        d2.add_attr('a', number=0, subkey='foo', value='bar1')
        d2.add_attr('a', number=1, subkey='foo', value='bar1')
        d2.add_attr('a', number=2, subkey='foo', value='bar1')

        d2.set_attr('a', 't1')

        self.assertEqual(sorted(d2.attr_items()),
                         sorted([(('a', 0, 'foo'), 'bar1'),
                                 (('a', 1, 'foo'), 'bar1'),
                                 (('a', 2, 'foo'), 'bar1'),
                                 (('a', None, None), 't1'),]))

    def testGettingAttrs(self):

        d1 = Driver('d1')

        d1.add_attr('foo', 'bar')
        d1.add_attr('foo', 'bar1', number=0)

        self.assertEqual(sorted(d1.attr_items()),
                         [(('foo', None, None), 'bar'), 
                          (('foo', 0, None), 'bar1')])



        self.assertEqual(d1.attr_items(number=True),
                         [(('foo', 0, None), 'bar1')])

    def testGettingAttrValues(self):
        d1 = Driver('d1')
        d2 = Driver('d2')
        
        d1.add_attr('foo', 'bar')
        d1.add_attr('foo0', 'bar1')
        d2.add_attr('d1', d1)

        clusto.flush()

        self.assertEqual(sorted(['bar', 'bar1']),
                         sorted(d1.attr_values('foo.*', regex=True)))

        self.assertEqual([d1], d2.attr_values())
        

    def testGettingAttrsMultipleTimes(self):
        d1 = Driver('d1')
        d2 = Driver('d2')
        
        d1.add_attr('foo', 'bar')
        d1.add_attr('foo0', 'bar1')
        d2.add_attr('d1', d1)

        clusto.flush()

        d = clusto.get_by_name('d1')
        
        self.assertEqual(len(d.references()), 1)
        self.assertEqual(len(d.attrs()), 2)


        
        
    def testNumberedAttrs(self):

        d1 = Driver('d1')

        d1.add_attr('foo', 'bar')

        d1.add_attr('foo', 'bar1', number=5)
        d1.add_attr('foo', 'bar2', number=6)

        clusto.flush()

        self.assertEqual(sorted(d1.attr_items()),
                         sorted([(('foo', None, None), 'bar'), 
                          (('foo', 5, None), 'bar1'), 
                          (('foo', 6, None), 'bar2')]))

        self.assertEqual(sorted(d1.attr_items(number=True)),
                         sorted([(('foo', 5, None), 'bar1'), 
                          (('foo', 6, None), 'bar2')]))


    def testAutoNumberedAttrs(self):
        d1 = Driver('d1')

        d1.add_attr('foo', 'bar')

        d1.add_attr('foo', 'bar1', number=True)
        d1.add_attr('foo', 'bar2', number=True)

        clusto.flush()

        self.assertEqual(sorted(d1.attr_items()),
                         sorted([(('foo', None, None), 'bar'),
                                 (('foo', 0, None), 'bar1'),
                                 (('foo', 1, None), 'bar2')]))

        self.assertEqual(sorted(d1.attr_items(number=True)),
                         sorted([(('foo', 0, None), 'bar1'),
                                 (('foo', 1, None), 'bar2')]))

        
    def testSubKeyAttrs(self):

        d1 = Driver('d1')

        d1.add_attr('foo', 'bar', subkey='subfoo')
        d1.add_attr('foo', 'caz', subkey='subbar')

        self.assertEqual(sorted(d1.attr_key_tuples()),
                         sorted([('foo',None,'subfoo'), ('foo',None,'subbar')]))

    def testNumberedAttrsWithSubKeys(self):

        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        
        self.assertEqual(d1.attr_items(),
                         [(('foo', 0, 'one'), 'bar1'),
                          (('foo', 1, 'two'), 'bar2')])

    def testGettingSpecificNumberedAttrs(self):
        
        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        d1.add_attr(key='foo', value='bar3', number=True, subkey='three')
        d1.add_attr(key='foo', value='bar4', number=True, subkey='four')

        self.assertEqual(list(d1.attr_items(key='foo', number=2)),
                         [(('foo',2,'three'), 'bar3')])
        
        self.assertEqual(list(d1.attr_items(key='foo', number=0)),
                         [(('foo',0,'one'), 'bar1')])
        
    def testGettingAttrsWithSpecificValues(self):

        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        d1.add_attr(key='foo', value='bar3', number=True, subkey='three')
        d1.add_attr(key='foo', value='bar4', number=True, subkey='four')

        self.assertEqual(list(d1.attr_items(value='bar3')),
                         [(('foo',2,'three'), 'bar3')])
        
        self.assertEqual(list(d1.attr_items(value='bar1')),
                         [(('foo',0,'one'), 'bar1')])
        

                          
    def testDelAttrs(self):
        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        d1.add_attr(key='foo', value='bar3', number=True, subkey='three')
        d1.add_attr(key='foo', value='bar4', number=True, subkey='four')

        d1.del_attrs(key='foo', value='bar4')

        
        self.assertEqual(list(d1.attr_items(value='bar4')),
                         [])

        self.assertEqual(list(d1.attr_items(value='bar3')),
                         [(('foo',2,'three'), 'bar3')])

        d1.del_attrs(key='foo', subkey='three', number=2)
        self.assertEqual(list(d1.attr_items(value='bar3')),
                         [])


    def testHasAttr(self):
        
        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        d1.add_attr(key='foo', value='bar3', number=True, subkey='three')
        d1.add_attr(key='foo', value='bar4', number=True, subkey='four')

        self.assertFalse(d1.has_attr(key='foo', number=False))
        self.assertTrue(d1.has_attr(key='foo', number=True))
        self.assertTrue(d1.has_attr(key='foo', number=1, subkey='two'))

    def testHiddenAttrs(self):

        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        d1.add_attr(key='_foo', value='bar3', number=True, subkey='three')
        d1.add_attr(key='_foo', value='bar4', number=True, subkey='four')

        self.assertEqual(d1.attr_items(ignore_hidden=True),
                         [(('foo',0,'one'), 'bar1'), (('foo',1,'two'), 'bar2')])


    def testAttributeGetValueAfterAdd(self):

        d1 = Driver('d1')

        d1.add_attr('foo', 2)
        self.assertEqual(d1.attr_items('foo'), [(('foo',None,None), 2)])
        d1.add_attr('bar', 3)
        self.assertEqual(d1.attr_items('foo'), [(('foo',None,None), 2)])
        self.assertEqual(d1.attr_items('bar'), [(('bar',None,None), 3)])


    def testGetByAttr(self):

        d1 = Driver('d1')
        d1.add_attr('foo', 1)

        d2 = Driver('d2')
        d2.add_attr('foo', 2)

        d3 = Driver('d3')
        d3.add_attr('bar', 3)

        clusto.flush()

        result = Driver.get_by_attr('foo', 2)

        self.assertEqual(result, [d2])
        
    def testAttrCount(self):
        
        d1 = Driver('d1')

        d1.add_attr(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar2', number=True, subkey='two')
        d1.add_attr(key='foo', value='bar3', number=True, subkey='three')
        d1.add_attr(key='foo', value='bar4', number=True, subkey='four')
        
        self.assertEqual(d1.attr_query(key='foo', number=2, count=True), 1)
        
        self.assertEqual(d1.attr_query(key='foo', number=0, count=True), 1)

        self.assertEqual(d1.attr_query(key='foo', number=False, count=True), 0)
        self.assertEqual(d1.attr_query(key='foo', count=True), 4)

        self.assertEqual(d1.attr_query(subkey='four', count=True), 1)


        d1.del_attrs(key='foo', value='bar1', number=True, subkey='one')
        d1.add_attr(key='foo', value='bar5', number=True, subkey='five')
        self.assertEqual(d1.attr_query(key='foo', number=0, count=True), 0)
        self.assertEqual(d1.attr_query(key='foo', number=4, count=True), 1)
        
    def testSetAttrAlreadySet(self):

        d1 = Driver('d1')

        version = clusto.get_latest_version_number()
        
        d1.set_attr(key='foo', value='bar1')

        self.assertEqual(version+1, clusto.get_latest_version_number())

        d1.set_attr(key='foo', value='bar1')

        self.assertEqual(version+1, clusto.get_latest_version_number())

class TestDriverContainerFunctions(testbase.ClustoTestBase):
    
    def testInsert(self):

        d1 = Driver('d1')
        d2 = Driver('d2')

        d1.insert(d2)
        
        clusto.flush()

        d = clusto.get_by_name('d1')

        self.assertEqual(d.attr_items(ignore_hidden=False),
                         [(('_contains', 0, None), d2)])

    def testRemove(self):
        
        d1 = Driver('d1')
        d2 = Driver('d2')

        d1.insert(d2)
        
        clusto.flush()

        d = clusto.get_by_name('d1')
        d.remove(d2)

        clusto.flush()

        self.assertEqual(d.attr_items(ignore_hidden=False),
                         [])

    def testContents(self):
        
        d1 = Driver('d1')
        d2 = Driver('d2')

        d1.insert(d2)
        
        self.assertEqual(d1.contents(), [d2])
                         

    def testChildrenContents(self):

        p1 = Pool('p1')
        p2 = Pool('p2')

        d1 = Driver('d1')
        d2 = Driver('d2')

        p1.insert(d1)
        p2.insert(d2)
        p2.insert(p1)

        self.assertEqual(sorted([p1,d1,d2]),
                         sorted(p2.contents(search_children=True)))
        
    def testMultipleInserts(self):

        d1 = Driver('d1')
        d2 = Driver('d2')
        d3 = Driver('d3')

        d1.insert(d2)
        
        self.assertRaises(TypeError, d3.insert, d2)

    def testNumberedInserts(self):

        d1 = Driver('d1')

        d1.insert(Driver('d2'))
        d1.insert(Driver('d3'))
        d1.insert(Driver('d4'))
        d1.insert(Driver('d5'))
        d1.insert(Driver('d6'))

        
        self.assertEqual(range(5),
                         [x.number for x in d1.attrs(ignore_hidden=False)])
        

    def testParents(self):

        class OtherDriver(Driver):
            _clusto_type = 'otherdriver'
            _driver_name = 'otherdriver'


        p1 = Pool('toppool')
        d1 = Pool('grandparent')
        d1a = Pool('othergrandparent')
        d1b = OtherDriver('anothergrandparent')
        d2 = Driver('parent')
        d3 = Driver('child')

        d1b.add_attr('foo', 'someval')
        p1.insert(d1a)
        d1b.insert(d2)
        d1a.insert(d2)
        d1.insert(d2)
        d2.insert(d3)

        self.assertEqual(sorted([d1,d1a, p1]),
                         sorted(d3.parents(clusto_types=[Pool], search_parents=True)))

        self.assertEqual([d2],
                         d3.parents())

        self.assertEqual(['someval'],
                         d3.attr_values('foo', merge_container_attrs=True))

class TestDriver(testbase.ClustoTestBase):
    
    def testCreatingDriverWithUsedName(self):
        
        d1 = Driver('d1')

        self.assertRaises(NameException, Driver, 'd1')

        d1.attrs()

    def testDriverSets(self):
        
        d1 = Driver('d1')
        d2 = Driver('d2')

        s = set([d1,d1,d2])

        self.assertEquals(len(s), 2)

class ATestDriver(Driver):

    _clusto_type = "tester"
    _driver_name = "testdriver"

    _properties = {'propA': None,
                   'propB': 'foo',
                   'propC': 5 }

class TestDriverProperties(testbase.ClustoTestBase):
    
    def testPropDefaultGetter(self):

        d = ATestDriver('d')

        self.assertEqual(None, d.propA)
        self.assertEqual('foo', d.propB)
        self.assertEqual(5, d.propC)

    def testPropSetter(self):

        d = ATestDriver('d')

        self.assertEqual(None, d.propA)

        d.propA = 'foo'
        self.assertEqual('foo', d.propA)

        d.propA = 'bar'
        self.assertEqual('bar', d.propA)

        d.propA = 10
        self.assertEqual(10, d.propA)

    def testPropSetterMultipleObjects(self):
        d = ATestDriver('d')
        d2 = ATestDriver('d2')

        d.propB = 'bar'
        d2.propB = 'cat'

        self.assertEqual(d2.propB, 'cat')
        self.assertEqual(d.propB, 'bar')

class TestDriverQueries(testbase.ClustoTestBase):
    
    def data(self):

        d1 = Driver('d1')
        d2 = Driver('d2')
        d3 = Driver('d3')

        d1.add_attr('_foo', 'bar1')
        d1.add_attr('car', 'baz')
        d1.add_attr('car', 'baz')
        d1.add_attr('d', 'dee', number=True)
        d1.add_attr('d', 'dee', number=True)
        d1.add_attr('a', 1)
        d1.add_attr('a', 1, subkey='t')
        d1.add_attr('a', 1, subkey='g')
        d1.add_attr('a', 1, subkey='z', number=4)
        d1.add_attr('a', 1, subkey='z', number=5)
        d1.add_attr('a', 1, subkey='z', number=6)
        
        d1.set_attr('d2', d2)
        d1.set_attr('d3', d3)

        d2.set_attr('aaa', 1)
        d2.set_attr('aab', 2)
        d2.set_attr('aac', 3)



    def testAttrAndQueryEqual(self):

        d1 = clusto.get_by_name('d1')
        d2 = clusto.get_by_name('d2')
        d3 = clusto.get_by_name('d3')

        self.assertEqual(d1.attrs('a'), d1.attr_query('a'))

        self.assertEqual(d1.attrs('a', 1), d1.attr_query('a', 1))

        self.assertEqual(d1.attrs('a', 1, number=True), 
                         d1.attr_query('a', 1, number=True))

        self.assertEqual(d1.attrs('a', 1, number=5), 
                         d1.attr_query('a', 1, number=5))

        self.assertEqual(d1.attrs(value='dee'), 
                         d1.attr_query(value='dee'))


        self.assertEqual(d1.attrs(value='_foo'), 
                         d1.attr_query(value='_foo'))

        self.assertEqual(d1.attrs(key='_foo'), 
                         d1.attr_query(key='_foo'))

        self.assertEqual(d1.attrs(key='a', subkey=None), 
                         d1.attr_query(key='a', subkey=None))

        self.assertEqual(d1.attrs(value=d2), 
                         d1.attr_query(value=d2))


        self.assertEqual(d1.attrs(subkey='z'),
                         d1.attr_query(subkey='z'))


    def testDoAttrQuery(self):

        d1 = clusto.get_by_name('d1')
        d2 = clusto.get_by_name('d2')
        self.assertEqual(set(Driver.get_by_attr(key='a*', glob=True)),
                         set([d1,d2]))

########NEW FILE########
__FILENAME__ = entitytests
"""
Test the basic Entity object
"""

import unittest
from clusto.test import testbase
import datetime

import clusto
from clusto.schema import *

class TestEntitySchema(testbase.ClustoTestBase):

    def testCreateEntityObject(self):

        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')
        e2 = Entity('e2')

        res = Entity.query().filter_by(name='e1')

        self.assertEqual(res.count(),1)

        e = res.all()[0]

        self.assertEqual(e.name, 'e1')


    def testOutputEntityObject(self):

        expectedout = "e1"
        
        e1 = Entity('e1')

        self.assertEqual(str(e1), expectedout)

        clusto.flush()

        self.assertEqual(str(Entity.query().filter_by(name='e1')[0]), expectedout)
        

    def testDeleteEntity(self):

        e1 = Entity('e1')

        clusto.flush()

        self.assertEqual(Entity.query().filter_by(type='entity').count(), 1)

        e1.delete()

        clusto.flush()

        self.assertEqual(Entity.query().filter_by(type='entity').count(), 0)
    
class TestEntityAttributes(testbase.ClustoTestBase):

    def data(self):

        Entity('e1')
        Entity('e2')
        Entity('e3')

        clusto.flush()

    def testAddingAttribute(self):

        e = Entity.query().filter_by(name='e2').one()

        e1 = Entity.query().filter_by(name='e1').one()

                
        self.assertEqual(e.name, 'e2')

        e.add_attr(key='one', value=1)
        e.add_attr(key='two', value=2)

        clusto.flush()

        q = Attribute.query().filter_by(entity_id=e.entity_id,
                                               key='two').one() 
        self.assertEqual(q.value, 2)

        q = Attribute.query().filter_by(entity_id=e.entity_id,
                                               key='one').one()

        self.assertEqual(q.value, 1)
        

    def testAddingDateAttribute(self):

        e1 = Entity.query().filter_by(name='e1').one()

        d = datetime.datetime(2007,12,16,7,46)
        
        e1.add_attr('somedate', d)

        clusto.flush()

        q = Attribute.query().filter_by(entity_id=e1.entity_id,
                                               key='somedate').one()

        self.assertEqual(q.value, d)
        
    def testData(self):

        q = Entity.query().\
               filter(not_(Entity.type=='clustometa')).count()

        self.assertEqual(q, 3)
        
    def testEmptyAttributes(self):
        """
        If I set no attributes there shouldn't be any in the DB except the
        clusto meta attributes
        """
        
        q = Attribute.query().join('entity').\
               filter(not_(Entity.type=='clustometa')).count()

        self.assertEqual(q, 0)
        
    def testRelationAttribute(self):

        e1 = Entity.query().filter_by(name='e1').one()
        
        e4 = Entity('e4')
        e4.add_attr(key='e1', value=e1)
        
        clusto.flush()


        e4 = Entity.query().filter_by(name='e4').one()

        attr = e4.attrs[0]

        self.assertEqual(attr.relation_value, e1)

    def testStringAttribute(self):

        e2 = Entity.query().filter_by(name='e2').one()

        e2.add_attr(key='somestring', value='thestring')

        clusto.flush()

        q = Attribute.query().filter_by(entity=e2,
                                               key='somestring').one()

        self.assertEqual(q.value, 'thestring')

    def testIntAttribute(self):

        e4 = Entity('e4')
        e4.add_attr(key='someint', value=10)

        clusto.flush()

        q = Attribute.query().filter_by(entity=e4,
                                               key='someint').one()

        self.assertEqual(q.value, 10)

    def testMultipleAttributes(self):

        e2 = Entity.query().filter_by(name='e2').one()

        e2.add_attr(key='somestring', number=1, subkey='foo',
                                   value='thestring')

        e2.add_attr(key='somestring', number=1, subkey='foo',
                                   value='thestring')


        clusto.flush()

        q = Attribute.query().filter_by(entity=e2,
                                               key='somestring').all()

        self.assertEqual([a.value for a in q], 
                         ['thestring', 'thestring'])

    def testEntityDeleteRelations(self):

        e1 = Entity.query().filter_by(name='e1').one()
        e2 = Entity.query().filter_by(name='e2').one()

        e1.add_attr('pointer1', e2)

        clusto.flush()

        self.assertEqual(Entity.query().\
                            filter_by(type='entity').count(),
                         3)

        self.assertEqual(Attribute.query().\
                            filter(and_(Entity.entity_id==Attribute.entity_id,
                                        Entity.type=='entity',
                                        
                                        )).count()
                         , 1)

        e2new = Entity.query().filter_by(name='e2').one()

        e2new.delete()

        self.assertEqual(Entity.query().\
                            filter_by(type='entity').count(),
                         2)
        
        self.assertEqual(Attribute.query().\
                            filter(and_(Entity.entity_id==Attribute.entity_id,
                                        Entity.type=='entity')).count(),
                         0)

        clusto.flush()

        self.assertEqual(Entity.query().\
                            filter_by(type='entity').count(),
                         2)
        self.assertEqual(Attribute.query().\
                            filter(and_(Entity.entity_id==Attribute.entity_id,
                                        Entity.type=='entity')).count(),
                         0)


    def testAccessRelationAttributesMultipleTimes(self):
        e1 = Entity.query().filter_by(name='e1').one()
        e2 = Entity.query().filter_by(name='e2').one()

        e1.add_attr('foo', 2)
        e1.add_attr('foo', e2)

        clusto.flush()
        e1 = Entity.query().filter_by(name='e1').one()
        self.assertEqual(len(list(e1.attrs)), 2)
        self.assertEqual(len(list(e1.attrs)), 2)
        self.assertEqual(len(list(e1.attrs)), 2)

        
    
class TestEntityReferences(testbase.ClustoTestBase):

    def data(self):
        
        e1 = Entity('e1')
        e2 = Entity('e2')
        e3 = Entity('e3')

        e3.add_attr(key='e1', value=e1)
        e3.add_attr(key='e2', value=e2)

        clusto.flush()
    
    def testReference(self):

        e1 = Entity.query().filter_by(name='e1').one()
        e2 = Entity.query().filter_by(name='e2').one()
        e3 = Entity.query().filter_by(name='e3').one()

        self.assertEqual(e1.references[0].entity,
                         e2.references[0].entity)

        self.assertEqual(e3,
                         e2.references[0].entity)

    def testReferenceDelete(self):

        e1 = Entity.query().filter_by(name='e1').one()


        e3 = Entity.query().filter_by(name='e3').one()

        
        e3.delete()

        self.assertEqual(len(list(e1.references)), 0)

        clusto.flush()

        e1a = Entity.query().filter_by(name='e1').one()

        self.assertEqual(len(list(e1a.references)), 0)
        self.assertEqual(id(e1a), id(e1))

        e2 = Entity.query().filter_by(name='e2').one()

        self.assertEqual(len(list(e2.references)), 0)


########NEW FILE########
__FILENAME__ = versioningtests
import unittest
from clusto.test import testbase

import clusto
from clusto.schema import *
from clusto.drivers.base import *
from clusto.drivers import BasicDatacenter
from sqlalchemy.exceptions import InvalidRequestError

class TestClustoVersioning(testbase.ClustoTestBase):

    def testGetFirstVersionNumber(self):

        curver = clusto.get_latest_version_number()
        self.assertEqual(curver, 2)

    def testVersionIncrementing(self):

        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')
        e2 = Entity('e2')

        self.assertEqual(clusto.get_latest_version_number(), curver + 2)

    def testVersionIncrementWithAttrs(self):

        curver = clusto.get_latest_version_number()
        
        e1 = Entity('e1')
        e2 = Entity('e2')

        e1.add_attr('foo', 2)

        
        self.assertEqual(clusto.get_latest_version_number(), curver + 3)
        
        
    def testDeleteVersion(self):

        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')
        etest = clusto.get_by_name('e1')
        e1.delete()


        self.assertRaises(LookupError, clusto.get_by_name, 'e1')

        e1a = Entity('e1')

        etest = clusto.get_by_name('e1')

        self.assertEqual(etest.entity.version, curver+3)


    def testViewOldVersion(self):

        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')
        e2 = Entity('e2')
        e3 = Entity('e3')

        self.assertEqual(Entity.query().filter(Entity.name.like('e%')).count(),
                         3)

        SESSION.clusto_version = curver

        self.assertEqual(Entity.query().filter(Entity.name.like('e%')).count(),
                         0)

        SESSION.clusto_version = clusto.working_version()

        self.assertEqual(Entity.query().filter(Entity.name.like('e%')).count(),
                         3)

        SESSION.clusto_version = curver + 1

        self.assertEqual(Entity.query().filter(Entity.name.like('e%')).count(),
                         1)


        SESSION.clusto_version = curver + 2

        self.assertEqual(sorted([e1,e2]),
                         Entity.query().filter(Entity.name.like('e%')).all())

    def testOldVersionsOfAttributes(self):

        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')
        e2 = Entity('e2')

        e1.add_attr('foo', 1)
        e1.add_attr('foo2', 2)
        e1.add_attr('foo3', 3)

        SESSION.clusto_version = curver + 3

        self.assertEqual(len(list(e1.attrs)), 1)
        
        e = Entity.query().filter_by(name='e1').one()

        SESSION.clusto_version = curver + 4

        self.assertEqual(sorted([a.key for a in e.attrs]),
                         sorted(['foo', 'foo2']))


    def testAttributesImmutable(self):

        e1 = Entity('e1')
        e1.add_attr('foo', 1)

        a = e1.attrs[0]

        self.assertRaises(Exception, setattr, a.value, 2)

        
    def testEntityImmutable(self):

        e1 = Entity('e1')

        self.assertRaises(Exception, setattr, e1.driver, 'foo')

    def testEntityRename(self):

        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')

        e1.add_attr('foo',1)
        e1.add_attr('foo',2)

        e1attrs = [a.to_tuple for a in e1.attrs]
        
        midver = clusto.get_latest_version_number()

        clusto.rename('e1', 't1')

        postrenamever = clusto.get_latest_version_number()
        
        t1 = clusto.get_by_name('t1')

        self.assertEqual(sorted(e1attrs),
                         sorted([a.to_tuple for a in t1.entity.attrs]))

        
        t1.del_attrs('foo', 2)

        self.assertRaises(LookupError, clusto.get_by_name, 'e1')

        self.assertEqual(sorted(t1.attrs('foo',1)),
                         sorted(t1.attrs()))

        SESSION.clusto_version = midver

        self.assertRaises(LookupError, clusto.get_by_name, 't1')

        e = clusto.get_by_name('e1')

        self.assertEqual(sorted(e1attrs),
                         sorted([a.to_tuple for a in e.attrs()]))

        
        for a in e.attrs():
            self.assertEqual(e.entity.deleted_at_version,
                             a.deleted_at_version)

        SESSION.clusto_version = postrenamever

        self.assertEqual(e.entity.deleted_at_version,
                         t1.entity.version)

        for a in t1.attrs():
            self.assertEqual(e.entity.deleted_at_version,
                             a.version)

    def testPoolRename(self):

        
        curver = clusto.get_latest_version_number()

        e1 = Entity('e1')
        e2 = Entity('e2')

        p1 = clusto.drivers.Pool('p1')

        p1.insert(e1)
        p1.insert(e2)

        self.assertEqual(sorted([e1,e2]),
                         sorted((d.entity for d in p1.contents())))

        clusto.rename('p1', 'p1renamed')

        p1renamed = clusto.get_by_name('p1renamed')

        self.assertEqual(sorted([e1,e2]),
                         sorted((d.entity for d in p1renamed.contents())))



    def testSetAttrIncrementsVersion(self):

        curver = clusto.get_latest_version_number()
        
        d = clusto.drivers.Driver('d1')

        self.assertEqual(curver + 1, clusto.get_latest_version_number())

        Attribute(d.entity, 'cat', 'baz')

        clusto.begin_transaction()
        SESSION.clusto_description = "TEST"

        #Attribute(d.entity, 'foo', 'cat')
        #SESSION.add(Attribute(d.entity, 'coo', 'daa'))

        Attribute.query().all()

        a = Attribute(d.entity, 'foo', 'bar')

        clusto.commit()
        #clusto.rollback_transaction()
            
        #self.assertEqual(['bar', 'bar'], d.attr_values('foo'))

        self.assert_('bar' in d.attr_values('foo'))
        self.assertEqual(curver + 3, clusto.get_latest_version_number())
        
    def testEmptyCommits(self):


        server = clusto.drivers.BasicServer('s1')

        curver = clusto.get_latest_version_number()
        server.attrs()

        self.assertEqual(curver, clusto.get_latest_version_number())
        

        try:
            clusto.begin_transaction()

            SESSION.clusto_description = "TEST"

            Entity.query().all()

            clusto.commit()

        except:
            
            clusto.rollback_transaction()

        self.assertEqual(curver, clusto.get_latest_version_number())

        self.assertEqual([], server.attr_values('foo'))

########NEW FILE########
__FILENAME__ = pooltests

import clusto
from clusto.test import testbase 
import itertools

from clusto.drivers import *
from clusto.exceptions import PoolException

class PoolTests(testbase.ClustoTestBase):

    def data(self):

        d1 = Driver('d1')
        d2 = Driver('d2')

        p1 = Pool('p1')

        clusto.flush()


    def testPoolCreate(self):

        p3 = Pool('p3')
        d3 = Driver('d3')
        
        clusto.flush()

        q = clusto.get_by_name('p3')

        self.assertTrue(isinstance(q, Pool))

        self.assertFalse(isinstance(clusto.get_by_name('d3'), Pool))

    def testPoolMembers(self):

        d1, d2, p1 = map(clusto.get_by_name, ('d1', 'd2', 'p1'))
        
        p1.insert(d1)
        p1.insert(d2)
        
        clusto.flush()


        q = clusto.get_by_name('p1')

        membernames = sorted([x.name for x in p1.contents()])

        self.assertEqual(membernames, sorted(['d1','d2']))

    def testGetPools(self):

        d1, d2, p1 = [clusto.get_by_name(i) for i in ['d1', 'd2', 'p1']]

        p2 = Pool('p2')
        
        p1.insert(d1)
        p2.insert(d1)
        p1.insert(d2)


        self.assertEqual(sorted(Pool.get_pools(d1)),
                         sorted([p1,p2]))

    def testGetPoolsMultiLevel(self):

        d1, d2, p1 = [clusto.get_by_name(i) for i in ['d1', 'd2', 'p1']]

        p2 = Pool('p2')
        p3 = Pool('p3')
        p4 = Pool('p4')
        d3 = Driver('d3')
        
        p1.insert(d1)
        p2.insert(d1)
        p1.insert(d2)

        p1.insert(p3)
        p3.insert(p4)
        p4.insert(d3)

        self.assertEqual(sorted(Pool.get_pools(d1, allPools=True)),
                         sorted([p1,p2]))

                
        self.assertEqual(sorted(set(Pool.get_pools(d3, allPools=True))),
                         sorted([p1, p3, p4]))

    def testPoolsIterator(self):

        
        A = Pool('A')

        d1, d2 = [clusto.get_by_name(i) for i in ['d1', 'd2']]

        B = Pool('B')
        C = Pool('C')
        A1 = Pool('A1')
        B2 = Pool('B2')
        B1 = Pool('B1')
        C1 = Pool('C1')

        C1.insert(C)
        B1.insert(B)
        A1.insert(B)

        A1.insert(A)
        B2.insert(A)

        A.insert(d1)
        B.insert(d1)
        C.insert(d1)

        clusto.flush()

        self.assertEqual([x.name for x in Pool.get_pools(d1)],
                         [u'A', u'B', u'C', u'A1', u'B2', u'B1', u'A1', u'C1'])

        self.assertEqual([x.name for x in Pool.get_pools(d1, allPools=False)],
                         [u'A', u'B', u'C'])


    def testPoolAttrs(self):

        d1, d2, p1 = map(clusto.get_by_name, ('d1', 'd2', 'p1'))

        p1.add_attr('t1', 1)
        p1.add_attr('t2', 2)

        d1.add_attr('t3', 3)

        p1.insert(d1)
        p1.insert(d2)
        

        clusto.flush()

        d2 = clusto.get_by_name('d2')

        self.assertEqual(sorted(d2.attrs(merge_container_attrs=True)), sorted(p1.attrs()))


        self.assertEqual(sorted(['t1', 't2', 't3']),
                         sorted([x.key for x in d1.attrs(merge_container_attrs=True)]))


    def testPoolAttrsOverride(self):

        d1, d2, p1 = map(clusto.get_by_name, ('d1', 'd2', 'p1'))

        p1.add_attr('t1', 1)
        p1.add_attr('t2', 2)

        p1.insert(d1)
        d1.add_attr('t1', 'foo')
        clusto.flush()

        
    def testFilterPoolContents(self):
        
        d1, d2, p1 = map(clusto.get_by_name, ('d1', 'd2', 'p1'))

        p1.insert(d1)
        p1.insert(d2)
        p1.insert(BasicServer('s1'))
        p1.insert(BasicServer('s2'))
        p1.insert(BasicNetworkSwitch('sw1'))

        self.assertEqual(p1.contents(clusto_types=[BasicNetworkSwitch]),
                         [clusto.get_by_name('sw1')])

    def testAddToPoolMultipleTimes(self):
        
        d1, d2, p1 = map(clusto.get_by_name, ('d1', 'd2', 'p1'))

        p1.insert(d1)

        self.assertRaises(PoolException, p1.insert, d1)
        

    def testDelAttrs(self):

        d1, d2, p1 = map(clusto.get_by_name, ('d1', 'd2', 'p1'))

        p1.insert(d1)
        p1.insert(d2)

        p1.add_attr('testkey', 'foo')
        
        self.assertEqual(sorted(p1.contents()),
                         sorted([d1,d2]))

        self.assertEqual([(a.key, a.value) for a in p1.attrs()],
                         [('testkey','foo')])
        
        p1.del_attrs()

        self.assertEqual(sorted(p1.contents()),
                         sorted([d1,d2]))

        self.assertEqual(p1.attrs(), [])

        

########NEW FILE########
__FILENAME__ = porttests

import clusto
from clusto.test import testbase

from clusto.drivers import Driver, PortMixin
from clusto.exceptions import ConnectionException

class TestDev1(Driver, PortMixin):
    _clusto_type = "test1"
    _driver_name = "test1driver"

    _portmeta = {'a' : {'numports':5},
                 'b' : {'numports':1}}

class TestDev2(Driver, PortMixin):

    _clusto_type = "test2"
    _driver_name = "test2driver"

    _portmeta = {'a' : {'numports':4},
                 'z' : {'numports':1}}

class PortLess(Driver):
    _clusto_type = "portless"
    _driver_name = "portless"

class PortTests(testbase.ClustoTestBase):
    """Test the port framework"""

    
    def data(self):
        
        a = TestDev1('t1')
        b = TestDev2('t2')
        c = PortLess('p')

    def testPortTypes(self):
        
        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        
        self.assertEqual(sorted(t1.port_types), 
                         sorted(['a', 'b']))

        self.assertEqual(sorted(t2.port_types), 
                         sorted(['a', 'z']))

    def testPortExists(self):
        
        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        self.assertTrue(t1.port_exists('a', 3))
        self.assertTrue(t1.port_exists('a', 1))
        self.assertFalse(t1.port_exists('a', 6))
        self.assertFalse(t1.port_exists('z', 4))

        self.assertTrue(t2.port_exists('z', 1))
        self.assertFalse(t2.port_exists('z', 2))

    def testPortsConnectable(self):
        
        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        self.assertTrue(t1.ports_connectable('a', 1, t2, 3))
        self.assertFalse(t1.ports_connectable('a', 1, t2, 5))
        self.assertFalse(t1.ports_connectable('b', 1, t2, 1))

    def testPortFree(self):
        
        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        self.assertTrue(t1.port_free('a', 2))

        t1.connect_ports('a', 1, t2, 1)

        self.assertFalse(t1.port_free('a', 1))

    def testConnectPorts(self):
        
        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        t1.connect_ports('a', 1, t2, 3)

        
        self.assertEqual(t2, t1.get_connected('a', 1))
        self.assertEqual(t1, t2.get_connected('a', 3))

        self.assertEqual(None, t1.get_connected('b', 1))


        # try to work with ports that don't exist
        self.assertRaises(ConnectionException, t2.get_connected, 'b', 3)
        self.assertRaises(ConnectionException, t2.connect_ports, 'b', 2, t1, 7)
        self.assertRaises(ConnectionException, t2.connect_ports, 'z', 1, t1, 1)


        # try to connect ports that are already connected but in the reverse order
        self.assertRaises(ConnectionException, t2.connect_ports, 'a', 4, t1, 1)

        # try to connect to a device that doesn't have ports
        self.assertRaises(ConnectionException, t1.connect_ports, 'a', 2, p, 1)

    def testDisconnectPort(self):

        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        t1.connect_ports('a', 1, t2, 3)

        self.assertEqual(t2, t1.get_connected('a', 1))
        
        t2.disconnect_port('a', 3)

        self.assertEqual(None, t1.get_connected('a', 1))
        self.assertEqual(None, t2.get_connected('a', 3))

        self.assertTrue(t1.port_free('a', 1))
        self.assertTrue(t2.port_free('a', 3))

        
    def testPortAttrs(self):

        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        t1.set_port_attr('a', 1, 'macaddr', 'foo')
        self.assertEqual('foo', t1.get_port_attr('a', 1, 'macaddr'))

        self.assertRaises(ConnectionException, 
                          t2.set_port_attr, 'j', 3, 'foo', 'bar')

        self.assertEqual(None, t2.get_port_attr('z', 1, 'mac'))
        t2.set_port_attr('z', 1, 'mac', 'bar')
        self.assertEqual('bar', t2.get_port_attr('z', 1, 'mac'))
        t2.del_port_attr('z', 1, 'mac')
        self.assertEqual(None, t2.get_port_attr('z', 1, 'mac'))
        


    def testPortInfo(self):
        
        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        self.assertEqual(sorted([('a', 1, None, None,),
                                 ('a', 2, None, None,),
                                 ('a', 3, None, None,),
                                 ('a', 4, None, None,),
                                 ('a', 5, None, None,),
                                 ('b', 1, None, None,),]),
                         sorted(t1.port_info_tuples))

        
        t1.connect_ports('a', 2, t2, 1)

        self.assertEqual(sorted([('a', 2, None, None,),
                                 ('a', 1, t1, 2,),
                                 ('a', 3, None, None,),
                                 ('a', 4, None, None,),
                                 ('z', 1, None, None,),]),
                         sorted(t2.port_info_tuples))

        self.assertEqual(t1, t2.port_info['a'][1]['connection'])
        self.assertEqual(2, t2.port_info['a'][1]['otherportnum'])

        self.assertEqual(None, t2.port_info['a'][3]['connection'])
        self.assertEqual(None, t2.port_info['z'][1]['otherportnum'])

        self.assertEqual(sorted([('a', 2),
                                 ('a', 3),
                                 ('a', 4),
                                 ('z', 1),]),
                         sorted(t2.free_ports))

        self.assertEqual(sorted(['a', 'b']),
                         sorted(t1.port_types))

        self.assertEqual(sorted(['a', 'z']),
                         sorted(t2.port_types))


    def testConnectedPorts(self):

        t1, t2, p = map(clusto.get_by_name, ['t1', 't2', 'p'])

        for i in [t1, t2]:
            for t in i.port_types:
                self.assertEqual([], i.connected_ports[t])

        t1.connect_ports('a', 1, t2, 3)
        t2.connect_ports('a', 2, t1, 2)
        
        self.assertEqual([1, 2], t1.connected_ports['a'])
        

########NEW FILE########
__FILENAME__ = DatacenterTests

import clusto
from clusto.test import testbase

from clusto.drivers.Base import Thing
from clusto.drivers.Servers import Server
from clusto.drivers.Datacenter import Rack, RackU, Datacenter, Colo, Cage
from clusto.exceptions import *

class RackTests(testbase.ClustoTestBase):

    def testAddToRack(self):

        rackname = 'ashrack101'
        rack = Rack(rackname)

        t1 = Thing('foo1')

        rack.addToRack(t1, [23,24])

        clusto.flush()

        tp = clusto.get_by_name('foo1')

        theRack = tp.get_connectedByType(Rack)

        self.assert_(theRack[0].name == rackname)

    def testRackContents(self):

        rackname = 'ashrack101'

        rack = Rack(rackname)

        t1 = Thing('t1')
        t2 = Thing('t2')
        t3 = Thing('t3')

        rack.addToRack(t3, [1,2])
        rack.addToRack(t2, [32])
        rack.addToRack(t1, [23,24,25])

        clusto.flush()

        contents = rack.getRackContents()

        self.assert_(contents[1].name == contents[2].name =='t3')
        self.assert_(contents[32].name == 't2')
        self.assert_(contents[23].name == contents[24].name
                     == contents[25].name == 't1')

        t1.delete()

        clusto.flush()

        rack = clusto.get_by_name(rackname)
        contents = rack.getRackContents()
        clusto.flush()
        
        self.assertEqual(len(contents), 3)
        

    def testRackUMissingArg(self):

        # correct 
        RackU('foo2', 3)

        # missing RU number
        self.assertRaises(TypeError, RackU, 'foo') 



class Datacentertest(testbase.ClustoTestBase):
    """
    Test Datacenter Driver
    """

    def testLocationRequirement(self):

        d = Datacenter('d1', 'san francisco')
        clusto.flush()

        z = clusto.get_by_name('d1')

        self.assert_(z.getAttr('location') == 'san francisco')

    def testDatacenterThingStack(self):

        d = Datacenter('d1', 'footown')

        co = Colo('colo1')
        ca = Cage('cage1')

        ra = Rack('rack1')

        s = Server('s1')

        d.connect(co)
        co.connect(ca)
        ca.connect(ra)

        clusto.flush()

        # can't connect a server to a datacenter
        self.assertRaises(ConnectionException, d.connect, s)
        

########NEW FILE########
__FILENAME__ = basicservertest

import clusto
from clusto.drivers import BasicServer, IPManager
from clusto.test import testbase

from clusto.exceptions import ResourceException

class BasicServerTest(testbase.ClustoTestBase):

    def data(self):
        s1 = BasicServer('bs1', model='7000', manufacturer='ibm')
        s2 = BasicServer('bs2', model='ab1200', manufacturer='sun')

        
    def testBasicServerCreation(self):

        s1 = clusto.get_by_name('bs1')
        s2 = clusto.get_by_name('bs2')

        self.assertEqual(s1.model, '7000')
        self.assertEqual(s1.manufacturer, 'ibm')
        self.assertEqual(s2.model, 'ab1200')
        self.assertEqual(s2.manufacturer, 'sun')

        
    def testHostname(self):

        s1 = clusto.get_by_name('bs1')
        s2 = clusto.get_by_name('bs2')

        s2.hostname = "testname"

        clusto.flush()

        self.assertEqual(s1.hostname, "bs1")

        self.assertEqual(s2.hostname, "testname")

        self.assertEqual(s2.entity.name, "bs2")

        s2.hostname = "newname"

        self.assertEqual(s2.hostname, "newname")
        

    def testfqdn(self):

        s1 = clusto.get_by_name('bs1')
        s2 = clusto.get_by_name('bs2')

        self.assertEqual(s1.fqdns, [])

        s2.add_fqdn("test.example.com")

        self.assertEqual(["test.example.com"],
                         s2.fqdns)

        s2.add_fqdn("test2.example.com")
        
        clusto.flush()

        self.assertEqual(sorted(["test.example.com",
                                 "test2.example.com"]),
                         sorted(s2.fqdns))

        s2.remove_fqdn("test.example.com")

        
        self.assertEqual(["test2.example.com"],
                         s2.fqdns)


    def testBindingIPtoOSPort(self):

        s1 = clusto.get_by_name('bs1')
        s2 = clusto.get_by_name('bs2')
                
        ipm = IPManager('ipman', netmask='255.255.255.0', baseip='192.168.1.0')

        s1.bind_ip_to_osport('192.168.1.20', 'eth0', porttype='nic-eth', portnum=1)

        
    def testAddingIP(self):

        s1 = clusto.get_by_name('bs1')

        self.assertRaises(ResourceException, s1.add_ip, '10.0.0.100')

        ipm = IPManager('ipman', netmask='255.255.0.0', baseip='10.0.0.1')

        s1.add_ip('10.0.0.100')
        
        self.assertTrue(s1.has_ip('10.0.0.100'))

        s1.add_ip(ipman=ipm)

        self.assertTrue(s1.has_ip('10.0.0.1'))

    def testAddingIPfromIPManagerWithGateway(self):
                        
        s1 = clusto.get_by_name('bs1')
        ipm = IPManager('ipman', netmask='255.255.0.0', baseip='10.0.0.1', gateway='10.0.0.1')

        s1.add_ip(ipman=ipm)

        self.assertTrue(s1.has_ip('10.0.0.2'))
        

    def testBindingIPtoOSPort(self):

        s1 = clusto.get_by_name('bs1')

        ipm = IPManager('ipman', netmask='255.255.0.0', baseip='10.0.0.1', gateway='10.0.0.1')

        self.assertRaises(Exception, s1.bind_ip_to_osport, '10.0.0.100', 'eth0', porttype='nic-eth')
        self.assertRaises(Exception, s1.bind_ip_to_osport, '10.0.0.100', 'eth0', portnum=0)
        
        s1.bind_ip_to_osport('10.0.0.100', 'eth0')#, porttype='nic-eth', portnum=1)

        self.assertEqual(IPManager.get_devices('10.0.0.100'), [s1])
        

########NEW FILE########
__FILENAME__ = basicracktests

import clusto
from clusto.drivers import BasicRack, BasicServer
from clusto.test import testbase

class BasicRackTest(testbase.ClustoTestBase):

    def data(self):

        r1 = BasicRack('r1')
        r2 = BasicRack('r2')

        clusto.flush()

    def testAddingToRack(self):

        r1 = clusto.get_by_name('r1')

        s1 = BasicServer('s1')

        r1.insert(s1, 1)


        rt = clusto.get_by_name('r1')
        st = clusto.get_by_name('s1')

        self.assertEqual(len(r1.contents(subkey='ru')), 1)

        self.assertEqual(r1.contents(subkey='ru')[0].name, 's1')
        
        self.assertEqual(s1.parents(clusto_drivers=[BasicRack])[0].name, 'r1')

    def testMaxRackPosition(self):

        r1 = clusto.get_by_name('r1')

        self.assertRaises(TypeError, r1.insert, BasicServer('s1'), 400)

        self.assertRaises(TypeError, r1.insert, BasicServer('s2'), -13)

        clusto.flush()

    def testGettingThingInRack(self):

        r1 = clusto.get_by_name('r1')

        r1.insert(BasicServer('s1'), 40)

        clusto.flush()

        s1 = r1.get_device_in(40)

        self.assertEqual(s1.name, 's1')
        

    def testGettingRackAndU(self):

        r1, r2 = [clusto.get_by_name(r) for r in ['r1','r2']]

        s=BasicServer('s1')
        clusto.flush()
        r1.insert(s, 13)

        clusto.flush()

        s = clusto.get_by_name('s1')

        res = BasicRack.get_rack_and_u(s)

        
        self.assertEqual(res['rack'].name, 'r1')
        self.assertEqual(res['RU'], [13])

        res2 = BasicRack.get_rack_and_u(BasicServer('s2'))
        self.assertEqual(res2, None)

    def testCanOnlyAddToOneRack(self):
        """
        A device should only be able to get added to a single rack
        """

        
        r1, r2 = [clusto.get_by_name(r) for r in ['r1','r2']]

        s1 = BasicServer('s1')
        s2 = BasicServer('s2')
        
        r1.insert(s1, 13)
        self.assertRaises(Exception, r2.insert,s1, 1)
        
    def testCanAddADeviceToMultipleAdjacentUs(self):
        """
        you should be able to add a device to multiple adjacent RUs
        """

        r1, r2 = [clusto.get_by_name(r) for r in ['r1','r2']]

        s1 = BasicServer('s1')
        s2 = BasicServer('s2')
        
        r1.insert(s1, [1,2,3])

        clusto.flush()

        s = clusto.get_by_name('s1')

        self.assertEqual(sorted(BasicRack.get_rack_and_u(s)['RU']),
                         [1,2,3])

        self.assertRaises(TypeError, r1.insert, s2, [1,2,4])

    def testAddingToDoubleDigitLocationThenSingleDigitLocation(self):

        r1, r2 = [clusto.get_by_name(r) for r in ['r1','r2']]

        s1 = BasicServer('s1')
        s2 = BasicServer('s2')
        
        r1.insert(s1, 11)

        r1.insert(s2, 1)

        clusto.flush()

        s = clusto.get_by_name('s1')

        self.assertEqual(sorted(BasicRack.get_rack_and_u(s)['RU']),
                         [11])

        self.assertEqual(sorted(BasicRack.get_rack_and_u(s2)['RU']),
                         [1])


########NEW FILE########
__FILENAME__ = NetworkTests
import unittest
#from clusto.schema import *
import clusto
from clusto.drivers.Network import *
from clusto.test import testbase

class TestIP(testbase.ClustoTestBase):

    def testIP(self):

        ip1 = IP('ipone')

        ip1.ip = '192.168.243.22'

        
        self.assertEqual(ip1.ip, '192.168.243.22')
        

        clusto.flush()

        ip2 = clusto.get_by_name('ipone')

        self.assertEqual(ip2.ip, '192.168.243.22')
        

    def testEmptyIP(self):

        ip1 = IP('ipone')

        self.assertEqual(ip1.ip, None)
        

class TestNetBlock(testbase.ClustoTestBase):
    pass


########NEW FILE########
__FILENAME__ = ipmanagertest

import clusto
from clusto.test import testbase

from clusto.drivers import IPManager, BasicServer, ResourceTypeException, ResourceException

import IPy

class IPManagerTest(testbase.ClustoTestBase):

    def data(self):

        ip1 = IPManager('a1', gateway='192.168.1.1', netmask='255.255.255.0',
                        baseip='192.168.1.0')

        ip2 = IPManager('b1', gateway='10.0.128.1', netmask='255.255.252.0',
                        baseip='10.0.128.0')

        s = BasicServer('s1')

    def testBadIPAllocation(self):
        
        ip1, ip2, s1 = map(clusto.get_by_name, ['a1', 'b1', 's1'])

        self.assertRaises(ResourceTypeException, ip1.allocate, s1, '10.2.3.4')

    def testNewIP(self):
        
        ip1, ip2, s1 = map(clusto.get_by_name, ['a1', 'b1', 's1'])

        num = 50
        for i in range(num):
            ip1.allocate(s1)


        self.assertEqual(ip1.count, num)
        self.assertEqual(len(ip1.resources(s1)), num)
        
        self.assertEqual(ip1.owners('192.168.1.' + str(num+1)), [s1])

    def testGetIPManager(self):

        ip1, ip2 = map(clusto.get_by_name, ['a1', 'b1'])

        self.assertEqual(ip1, IPManager.get_ip_manager('192.168.1.23'))
        self.assertEqual(ip2, IPManager.get_ip_manager('10.0.129.22'))

    def testGetIP(self):

        ip1, ip2, s1 = map(clusto.get_by_name, ['a1', 'b1', 's1'])

        ip1.allocate(s1)
        ip2.allocate(s1)

        self.assertEqual(sorted(IPManager.get_ips(s1)),
                         sorted(['192.168.1.2', '10.0.128.2']))

    def testReserveIP(self):
        
        ip1, ip2, s1 = map(clusto.get_by_name, ['a1', 'b1', 's1'])

        ip2.allocate(ip2, '10.0.128.4')

        self.assertRaises(ResourceException, ip2.allocate, s1, '10.0.128.4')

        

########NEW FILE########
__FILENAME__ = simplenamemanagertest
import clusto
from clusto.test import testbase 
import itertools

from clusto.drivers import *

from clusto.drivers.resourcemanagers.simplenamemanager import SimpleNameManagerException



class SimpleEntityNameManagerTests(testbase.ClustoTestBase):

    def data(self):

        n1 = SimpleEntityNameManager('foonamegen',
                                     basename='foo',
                                     digits=4,
                                     next=1,
                                     )


        n2 = SimpleEntityNameManager('barnamegen',
                                     basename='bar',
                                     digits=2,
                                     next=95,
                                     )
        
        clusto.flush()

    def testNamedDriverCreation(self):
        ngen = clusto.get_by_name('foonamegen')
        
        s1 = ngen.allocate(Driver)

        clusto.flush()

        d1 = clusto.get_by_name('foo0001')

        self.assertEquals(s1.name, d1.name)
        
    def testAllocateName(self):

        ngen = clusto.get_by_name('foonamegen')
        
        s1 = ngen.allocate(Driver)
        s2 = ngen.allocate(Driver)
        s3 = ngen.allocate(Driver)
        s4 = ngen.allocate(Driver)

        clusto.flush()

        self.assertEqual(s1.name, 'foo0001')
        self.assertEqual(s2.name, 'foo0002')
        self.assertEqual(s3.name, 'foo0003')
        self.assertEqual(s4.name, 'foo0004')

    def testNoLeadingZeros(self):

        ngen = clusto.get_by_name('barnamegen')

        s1 = ngen.allocate(Driver)
        s2 = ngen.allocate(Driver)
        s3 = ngen.allocate(Driver)
        s4 = ngen.allocate(Driver)

        clusto.flush()

        self.assertEqual(s1.name, 'bar95')
        self.assertEqual(s2.name, 'bar96')
        self.assertEqual(s3.name, 'bar97')
        self.assertEqual(s4.name, 'bar98')

    def testTooManyDigits(self):
        
        ngen = clusto.get_by_name('barnamegen')

        s1 = ngen.allocate(Driver)
        s2 = ngen.allocate(Driver)
        s3 = ngen.allocate(Driver)
        s4 = ngen.allocate(Driver)

        s5 = ngen.allocate(Driver)
        self.assertRaises(SimpleNameManagerException,
                          ngen.allocate, Driver)


    def testAllocateManyNames(self):
        
        ngen = clusto.get_by_name('foonamegen')

        for i in xrange(50):
            ngen.allocate(Driver)

        self.assertRaises(LookupError, clusto.get_by_name, 'foo0051')
        self.assertEqual(clusto.get_by_name('foo0050').name, 'foo0050')


    def testAllocateGivenName(self):

        ngen = clusto.get_by_name('foonamegen')

        d = ngen.allocate(Driver, 'testname')

        self.assertEqual(d.name, 'testname')

class SimpleNameManagerTests(testbase.ClustoTestBase):

    def data(self):
        n1 = SimpleNameManager('foonamegen',
                               basename='foo',
                               digits=4,
                               startingnum=1,
                               )

        clusto.flush()

    def testAllocateManyNames(self):
        
        ngen = clusto.get_by_name('foonamegen')

        d = Driver('foo')

        for i in xrange(50):
            ngen.allocate(d)
            
        
        self.assertEqual(len(SimpleNameManager.resources(d)), 50)

########NEW FILE########
__FILENAME__ = simplenummanagertest
import clusto
from clusto.test import testbase 
import itertools

from clusto.drivers import *

from clusto.drivers.resourcemanagers.simplenummanager import *



class SimpleNumManagerTests(testbase.ClustoTestBase):

    def data(self):

        n1 = SimpleNumManager('numgen1', next=1)

        n2 = SimpleNumManager('numgen2', maxnum=4, next=0)
        
        clusto.flush()

    def testAllocateNum(self):

        ngen = clusto.get_by_name('numgen1')
        
        d = Driver('foo')
        s1 = ngen.allocate(d)
        s2 = ngen.allocate(d)
        s3 = ngen.allocate(d)
        s4 = ngen.allocate(d)

        self.assertEqual(ngen.owners(1), [d])
        self.assertEqual(ngen.owners(2), [d])
        self.assertEqual(ngen.owners(3), [d])
        self.assertEqual(ngen.owners(4), [d])


    def testAllocateMaxNum(self):
        
        d = Driver('foo')

        ngen = clusto.get_by_name('numgen2')

        s1 = ngen.allocate(d)
        s1 = ngen.allocate(d)
        s1 = ngen.allocate(d)
        s1 = ngen.allocate(d)
        s1 = ngen.allocate(d)

        self.assertRaises(SimpleNumManagerException, ngen.allocate, d)
        
        

########NEW FILE########
__FILENAME__ = vmmanagertest

import clusto
from clusto.test import testbase

from clusto.drivers import (VMManager, BasicServer, BasicVirtualServer,
                            ResourceTypeException, ResourceException)


class VMManagerTest(testbase.ClustoTestBase):

    def data(self):

        vmm = VMManager('vmm')

        s1 = BasicServer('s1')
        s1.set_attr('system', subkey='memory', value=1000)
        s1.set_attr('system', subkey='disk', value=5000)
        s1.set_attr('system', subkey='cpucount', value=2)
        
        s2 = BasicServer('s2')
        s2.set_attr('system', subkey='memory', value=16000)
        s2.set_attr('system', subkey='disk', value=2500)
        s2.set_attr('system', subkey='cpucount', value=2)
        

        vmm.insert(s1)
        vmm.insert(s2)
        

    def testVMManagerAllocate(self):

        s1 = clusto.get_by_name('s1')
        s2 = clusto.get_by_name('s2')
        
        vs1 = BasicVirtualServer('vs1')
        vs1.set_attr('system', subkey='memory', value=1000)
        vs1.set_attr('system', subkey='disk', value=50)
        vs1.set_attr('system', subkey='cpucount', value=1)

        vs2 = BasicVirtualServer('vs2')
        vs2.set_attr('system', subkey='memory', value=8000)
        vs2.set_attr('system', subkey='disk', value=1000)
        vs2.set_attr('system', subkey='cpucount', value=1)

        vs3 = BasicVirtualServer('vs3')
        vs3.set_attr('system', subkey='memory', value=800)
        vs3.set_attr('system', subkey='disk', value=100)
        vs3.set_attr('system', subkey='cpucount', value=3)

        vmm = clusto.get_by_name('vmm')

        vmm.allocate(vs1)

        self.assertEqual(len(vmm.resources(vs1)), 1)

        self.assert_(vmm.resources(vs1)[0].value in [s1, s2])

        vmm.allocate(vs2)

        self.assertEqual([r.value for r in vmm.resources(vs2)], [s2])

        self.assertRaises(ResourceException, vmm.allocate, vs3)

    def testVMDestroy(self):

        vmm = clusto.get_by_name('vmm')


        vs1 = BasicVirtualServer('vs1')
        vs1.set_attr('system', subkey='memory', value=1000)
        vs1.set_attr('system', subkey='disk', value=50)
        vs1.set_attr('system', subkey='cpucount', value=2)

        vs2 = BasicVirtualServer('vs2')
        vs2.set_attr('system', subkey='memory', value=5000)
        vs2.set_attr('system', subkey='disk', value=50)
        vs2.set_attr('system', subkey='cpucount', value=2)

        vs3 = BasicVirtualServer('vs3')
        vs3.set_attr('system', subkey='memory', value=1000)
        vs3.set_attr('system', subkey='disk', value=50)
        vs3.set_attr('system', subkey='cpucount', value=1)

        s1 = clusto.get_by_name('s1')
        s2 = clusto.get_by_name('s2')
        
        vmm.allocate(vs1)
        vmm.allocate(vs2)

        self.assertRaises(ResourceException, vmm.allocate, vs3)

        vmm.deallocate(vs2)

        vmm.allocate(vs3)

        self.assertEqual([r.value for r in vmm.resources(vs3)],
                         [clusto.get_by_name('s2')])
                          
    def testVMAllocateToSpecificHost(self):

        vs1 = BasicVirtualServer('vs1')
        vs1.set_attr('system', subkey='memory', value=1000)
        vs1.set_attr('system', subkey='disk', value=50)
        vs1.set_attr('system', subkey='cpucount', value=2)

        vs2 = BasicVirtualServer('vs2')
        vs2.set_attr('system', subkey='memory', value=5000)
        vs2.set_attr('system', subkey='disk', value=50)
        vs2.set_attr('system', subkey='cpucount', value=2)

        vs3 = BasicVirtualServer('vs3')
        vs3.set_attr('system', subkey='memory', value=1000)
        vs3.set_attr('system', subkey='disk', value=50)
        vs3.set_attr('system', subkey='cpucount', value=1)

        s1 = clusto.get_by_name('s1')
        s2 = clusto.get_by_name('s2')
        s3 = BasicServer('s3')
        
        vmm = clusto.get_by_name('vmm')
        vmm.allocate(vs1, s1)

        self.assertRaises(ResourceException, vmm.allocate, vs2, s3)

        self.assertRaises(ResourceException, vmm.allocate, vs1, s1)
        self.assertRaises(ResourceException, vmm.allocate, vs1, s2)

        self.assertEqual([r.value for r in vmm.resources(vs1)],
                         [clusto.get_by_name('s1')])

        self.assertRaises(ResourceException, vmm.allocate, vs2, s1)

        self.assertEqual([r.value for r in vmm.resources(vs2)],
                         [])

        vmm.allocate(vs2, s1, force=True)

        self.assertEqual([r.value for r in vmm.resources(vs2)],
                         [clusto.get_by_name('s1')])


    def testAddingAndRemovingHosts(self):

        s1 = clusto.get_by_name('s1')
        s2 = clusto.get_by_name('s2')
        s3 = BasicServer('s3')
        s3.set_attr('system', subkey='memory', value=16000)
        s3.set_attr('system', subkey='disk', value=2500)
        s3.set_attr('system', subkey='cpucount', value=2)
        
        vmm = clusto.get_by_name('vmm')

        vs1 = BasicVirtualServer('vs1')
        vs1.set_attr('system', subkey='memory', value=1000)
        vs1.set_attr('system', subkey='disk', value=50)
        vs1.set_attr('system', subkey='cpucount', value=2)

        self.assertRaises(ResourceException, vmm.allocate, vs1, s3)

        vmm.allocate(vs1, s1)

        self.assertRaises(ResourceException, vmm.remove, s1)
        vmm.deallocate(vs1)
        vmm.remove(s1)

        vmm.insert(s3)

        vmm.allocate(vs1, s3)

    def testReservingResource(self):

        s1 = clusto.get_by_name('s1')
        s2 = clusto.get_by_name('s2')

        vmm = clusto.get_by_name('vmm')

        vs1 = BasicVirtualServer('vs1')
        vs1.set_attr('system', subkey='memory', value=1000)
        vs1.set_attr('system', subkey='disk', value=50)
        vs1.set_attr('system', subkey='cpucount', value=2)

        vmm.allocate(vmm, s1)

        self.assertRaises(ResourceException, vmm.allocate, vs1, s1)
        

class EC2VMManagerTest(testbase.ClustoTestBase):

    def data(self):

        vmm = clusto.drivers.EC2VMManager('ec2man')

        

########NEW FILE########
__FILENAME__ = resourcetests
import clusto
from clusto.test import testbase 
import itertools

from clusto.drivers import *

from clusto.drivers.resourcemanagers.simplenamemanager import SimpleNameManagerException


class ResourceManagerTests(testbase.ClustoTestBase):

    def testAllocate(self):

        rm = ResourceManager('test')
        d = Driver('d')

        rm.allocate(d, 'foo')

        self.assertEqual(rm.owners('foo'), [d])

    def testResourceCount(self):

        rm = ResourceManager('test')
        d = Driver('d')
        
        rm.allocate(d, 'foo')
        rm.allocate(d, 'bar')
        
        self.assertEqual(rm.count, 2)

    def testDeallocate(self):

        rm = ResourceManager('test')
        d = Driver('d')

        rm.allocate(d, 'foo')
        self.assertEqual(rm.count, 1)

        rm.deallocate(d, 'foo')
        self.assertEqual(rm.count, 0)
        self.assertEqual(rm.owners('foo'), [])

    def testGeneralDeallocate(self):

        rm = ResourceManager('test')
        d = Driver('d')

        rm.allocate(d, 'foo')
        rm.allocate(d, 'bar')
        
        self.assertEqual(rm.count, 2)
        self.assertEqual(sorted([x.value for x in rm.resources(d)]),
                         sorted(['foo', 'bar']))

        rm.deallocate(d)

        self.assertEqual(rm.count, 0)
        self.assertEqual(sorted(rm.resources(d)),
                         sorted([]))


    def testResourceAttrs(self):

        
        rm = ResourceManager('test')
        d = Driver('d')

        rm.allocate(d, 'foo')
        rm.allocate(d, 'bar')

        rm.add_resource_attr(d, 'foo', 'attr1', 10)

        self.assertEqual(rm.get_resource_attr_values(d, 'foo', 'attr1'), [10])

        rm.add_resource_attr(d, 'foo', 'attr1', 20)

        self.assertEqual(sorted(rm.get_resource_attr_values(d, 'foo', 'attr1')),
                         sorted([10, 20]))

        rm.del_resource_attr(d, 'foo', 'attr1')
        self.assertEqual(rm.get_resource_attr_values(d, 'foo', 'attr1'), [])

        rm.set_resource_attr(d,'bar', 'attr2', 1)        
        self.assertEqual(rm.get_resource_attr_values(d, 'bar', 'attr2'), [1])

        rm.set_resource_attr(d,'bar', 'attr2', 2)
        self.assertEqual(rm.get_resource_attr_values(d, 'bar', 'attr2'), [2])

    def testReserveResource(self):

        rm = ResourceManager('test')
        d = Driver('d')

        rm.allocate(d, 'foo')

        rm.allocate(rm, 'bar')
        

        self.assertRaises(ResourceException, rm.allocate, d, 'bar')
        

########NEW FILE########
__FILENAME__ = clustoscripttest


########NEW FILE########
__FILENAME__ = test

from clusto.test import testbase
import unittest

from schema import *
from drivers import *

class TestThingSchema(unittest.TestCase):

    def setUp(self):
        
        metadata.connect('sqlite:///:memory:')
        metadata.create_all()



    def tearDown(self):

        ctx.current.clear()
        metadata.dispose()


    def testThingConnections(self):
        
        t=Thing('foo1')
        t2=Thing('subfoo')
        t3=Thing('foo2')
        s=Server('serv1')

        t.connect(s)
        ctx.current.flush()

        ta1=ThingAssociation(t,t2)
        ta2=ThingAssociation(t3,t)

        ctx.current.flush()
        ctx.current.clear()
        
        f=Thing.selectone(Thing.c.name=='foo1')

        for i in f.connections:
            pass #sys.stderr.write('\n' + i.name +": " + str(i.meta_attrs) + '\n')
        self.assertEqual(len(f.connections), 3)

    def testDrivers(self):

        
        s1=Server('s1')
        s2=Server('s2')

        t1=Thing('t1')
        t2=Thing('t2')

        self.assertEqual(s1.getAttr('clustotype'), 'server')
                                 
        ctx.current.flush()

        l=Server.select()
        
        self.assertEqual(len(l), 2)

        o=Thing.select()
        self.assertEqual(len(o), 4)
        ctx.current.flush()
        
    def testAttributes(self):

        s1=Server('s4')
        
        ctx.current.flush()
        
        s=Server.selectone(Server.c.name=='s4')

        #s.attrs.append(Attribute('g',1))
        s.add_attr('g', 1)
        s.add_attr('a', 2)
        s.add_attr('b', 3)
        
        ctx.current.flush()        

        a = Attribute.select()
        self.assertEqual(len(a), 4)

        n1 = Netscaler('one1')

        self.assertEqual(n1.getAttr('vendor'), 'citrix')
        
        ctx.current.flush()

    def testOutput(self):

        s1 = Server('s5')
        s1.add_attr('version', 1)
        s1.add_attr('model', 'amd')
        
                
        s2 = Server('s6')
        s2.add_attrs([('version', 2), ('vender', 'penguin computing')])
        
        s1.connect(s2)
        
        ctx.current.flush()

        s=Server.select()

if __name__ == '__main__':
    suite = unittest.makeSuite(TestThingSchema)
    unittest.TextTestRunner(verbosity=2).run(suite)
    

########NEW FILE########
__FILENAME__ = testbase
import sys
import os

sys.path.insert(0, os.curdir)


import unittest

import clusto

import ConfigParser

DB='sqlite:///:memory:'
ECHO=False

class ClustoTestResult(unittest.TestResult):
    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        print >>sys.stderr, "ERROR HERE!"
        clusto.rollback_transaction()
        self.errors.append((test, self._exc_info_to_string(err, test)))
        


class ClustoTestBase(unittest.TestCase):



    def data(self):
        pass
    
    def setUp(self):

        conf = ConfigParser.ConfigParser()
        conf.add_section('clusto')
        conf.set('clusto', 'dsn', DB)
        clusto.SESSION.clusto_version = clusto.working_version()
        clusto.connect(conf,echo=ECHO)
        clusto.clear()
        clusto.SESSION.close()
        clusto.init_clusto()
        self.data()


    def tearDown(self):
        if clusto.SESSION.is_active:
            raise Exception("SESSION IS STILL ACTIVE in %s" % str(self.__class__))

        clusto.clear()
        clusto.disconnect()
        clusto.METADATA.drop_all(clusto.SESSION.bind)



    def defaultTestResult(self):
        if not hasattr(self._testresult):
            self._testresult = ClustoTestResult()

        return self._testresult


########NEW FILE########
__FILENAME__ = clusterusage
from clusto.test import testbase

from clusto.drivers import BasicServer, APCRack, IPManager, Pool
from clusto.drivers import Cisco4948, PowerTowerXM, BasicDatacenter
from clusto.exceptions import ConnectionException
import clusto

class ClusterUsageTest(testbase.ClustoTestBase):
    """Test managing a cluster

    create pools, find services, query machine properties, etc.
    """

    def data(self):

        def createRack(datacenter, rackprefix):

            try:
                clusto.begin_transaction()
                r = APCRack(rackprefix)
                pwr = PowerTowerXM(rackprefix+'-pwr1', withslave=True)

                sw = Cisco4948(rackprefix+'-sw1')
                sw.connect_ports('nic-eth', 48, pwr, 1)
                pwr.connect_ports('pwr-nema-5', 'aa8', sw, 1)

                r.insert(pwr, [1,2,3,4])
                r.insert(sw, [5])

                for i in range(20):
                    s=BasicServer(rackprefix+'-s'+'%02d'%i)
                    r.insert(s, [6+i])
                    s.connect_ports('nic-eth', 1, sw, i+1)
                    s.connect_ports('pwr-nema-5', 1,
                                    pwr, 'ab'[i/10%2] + 'ab'[i/5%2] + str(i%5 + 1))
                clusto.commit()
            except Exception, x:
                clusto.rollback_transaction()
                raise x
                
            return r

        ds = map(BasicDatacenter, ['dc1', 'dc2', 'dc3'])

        for num, d in enumerate(ds):
            for i in range(1):
                rackname = 'rack-'+ str(num) + '%03d' % i
                r = createRack(d, rackname)

                d.insert(r)

        ipmans = [IPManager('block-' + x, netmask='255.255.0.0', baseip=x)
                  for x in ('10.1.0.0', '10.2.0.0', '10.3.0.0')]

        state_pools = map(Pool, ('production', 'development'))
        type_pools = map(Pool, ('webserver', 'database'))
        db_group_pools = map(Pool, ('users', 'objects', 'logs'))
        web_group_pools = map(Pool, ('frontend', 'api', 'admin'))
        
        for num, d in enumerate(ds):
            ipman = ipmans[num]
            for s in d.contents(clusto_types=[BasicServer],
                                search_children=True):
                ipman.allocate(s)
                ipman.allocate(s)
                
        
    def testGetServers(self):
        pass

########NEW FILE########
__FILENAME__ = concurrentusage
from clusto.test import testbase

from clusto.drivers import BasicServer, BasicRack, IPManager
from clusto.drivers import BasicNetworkSwitch, BasicPowerStrip, PowerTowerXM
from clusto.exceptions import ConnectionException
import clusto

import os
import threading
import ConfigParser

thread_count = 0

def barrier_creator(count):

    semaphore = threading.Semaphore()
    event = threading.Event()

    def synchronise():
        """ All calls to this method will block until the last (count) call is made """
        global thread_count

        semaphore.acquire()
        thread_count += 1
        if thread_count == count:
            event.set()
        semaphore.release()

        event.wait(3)

    return synchronise

    
class ClustoWorkThread(threading.Thread):

    def __init__(self, db, echo, barrier):
        super(ClustoWorkThread, self).__init__()  
        conf = ConfigParser.ConfigParser()
        conf.add_section('clusto')
        conf.set('clusto', 'dsn', db)
        self.conf = conf
        self.echo = echo
        self.barrier = barrier
        
    def run(self):

        clusto.connect(self.conf,echo=self.echo)
        clusto.init_clusto()

        try:

            clusto.begin_transaction()

            e = clusto.Entity('foo'+self.getName())

            self.barrier()

            clusto.commit()
        except Exception, x:
            clusto.rollback_transaction()
            raise x
            
class ConcurrentTest(testbase.unittest.TestCase):

    def setUp(self):
        conf = ConfigParser.ConfigParser()
        conf.add_section('clusto')
        conf.set('clusto', 'dsn', testbase.DB)

        clusto.SESSION.clusto_version = clusto.working_version()
        clusto.connect(conf,echo=testbase.ECHO)
        clusto.METADATA.drop_all(clusto.SESSION.bind)
        clusto.clear()
        clusto.SESSION.close()


    def tearDown(self):
        if clusto.SESSION.is_active:
            raise Exception("SESSION IS STILL ACTIVE in %s" % str(self.__class__))

        clusto.clear()
        clusto.disconnect()
        clusto.METADATA.drop_all(clusto.SESSION.bind)

        
    def testConcurrentThreads(self):

        DB = testbase.DB
        if DB.startswith('sqlite'):
            return
            
        conf = ConfigParser.ConfigParser()
        conf.add_section('clusto')
        conf.set('clusto', 'dsn', testbase.DB)
        clusto.connect(conf, echo=testbase.ECHO)
        clusto.init_clusto()
        firstver = clusto.get_latest_version_number()
        
        threadcount = 5
        threads = []
        barrier = barrier_creator(threadcount)
        for i in range(threadcount):
            threads.append(ClustoWorkThread(DB, testbase.ECHO,
                                            barrier))

        for i in threads:
            i.start()

        for i in threads:
            i.join()

        self.assertEqual(clusto.get_latest_version_number(),
                         threadcount+firstver)        


        

########NEW FILE########
__FILENAME__ = serverinstallation

from clusto.test import testbase

from clusto.drivers import BasicServer, BasicRack, IPManager
from clusto.drivers import BasicNetworkSwitch, BasicPowerStrip, PowerTowerXM
from clusto.exceptions import ConnectionException
import clusto

class ServerInstallationTest(testbase.ClustoTestBase):
    """Test installing a server 

    Put the server into a rack 
    connect the server to a powerstrip and a networkswitch
    """

    def data(self):
        
        r1 = BasicRack('r1')
        
        sw1 = BasicNetworkSwitch('sw1')

        s1 = BasicServer('s1')
        
        p1 = PowerTowerXM('p1')

        r1.insert(p1, (10,11))
        r1.insert(sw1, 12)
        r1.insert(s1, 1)

    def testServerRackLocation(self):

        r = clusto.get_by_name('r1')
        s = clusto.get_by_name('s1')
        
        self.assertEqual(BasicRack.get_rack_and_u(s)['RU'], [1])

        self.assertEqual(r.get_device_in(12),
                         clusto.get_by_name('sw1'))

        self.assertEqual(r.get_device_in(10),
                         clusto.get_by_name('p1'))

        self.assertEqual(r.get_device_in(11),
                         clusto.get_by_name('p1'))
        
        

    def testPortConnections(self):

        s = clusto.get_by_name('s1')
        sw = clusto.get_by_name('sw1')
        p1 = clusto.get_by_name('p1')

        sw.connect_ports('nic-eth', 1, s, 1)
        
        
        self.assertRaises(ConnectionException,
                          s.connect_ports, 'nic-eth', 1, sw, 2)

        p1.connect_ports(porttype='pwr-nema-5',
                        srcportnum=1,
                        dstdev=s,
                        dstportnum=1)
                        
        self.assertEqual(s.get_connected('pwr-nema-5', 1),
                         p1)


    def testSettingUpServer(self):
        
        from clusto.drivers import SimpleEntityNameManager

        servernames = SimpleEntityNameManager('servernames',
                                              basename='server',
                                              digits=4
                                              )

        newserver = servernames.allocate(BasicServer)
        

        sw = clusto.get_by_name('sw1')
        p1 = clusto.get_by_name('p1')
        r = clusto.get_by_name('r1')

        self.assertEqual('server0001', newserver.name)


        self.assertRaises(TypeError, r.insert, newserver, 1)

        r.insert(newserver,2)
        p1.connect_ports('pwr-nema-5', 1, newserver, 1)
        sw.connect_ports('nic-eth', 1, newserver, 1)
        sw.connect_ports('nic-eth', 3, p1, 1)

        self.assertEqual(BasicRack.get_rack_and_u(newserver)['rack'], r)

        ipman = IPManager('subnet-10.0.0.1', netmask='255.255.255.0', baseip='10.0.0.1')

        newserver.bind_ip_to_osport('10.0.0.2', 'eth0', porttype='nic-eth', portnum=1)

        ipvals = newserver.attrs(value='10.0.0.2')
        self.assertEqual(len(ipvals), 1)

        self.assertEqual(ipvals[0].value, '10.0.0.2')

        self.assertEqual(clusto.get_by_attr('ip', '10.0.0.2'), [newserver])


        aserver = servernames.allocate(BasicServer)

        ipattr = ipman.allocate(aserver)
        
        aserver.bind_ip_to_osport(ipattr.value, 'eth0', porttype='nic-eth', portnum=1)

        ip = aserver.attr_values(ipattr.key, number=ipattr.number, subkey=ipattr.subkey)

        self.assertEqual(aserver.get_port_attr('nic-eth', 1, 'osportname'),
                         'eth0')

        self.assertEqual(len(aserver.attrs(subkey='osportname', value='eth0')),
                         2)

        self.assertEqual(aserver.attrs(IPManager._attr_name,
                                       subkey='ipstring',
                                       number=aserver.attrs(IPManager._attr_name,
                                                            subkey='osportname',
                                                            value='eth0')[0].number,
                                       )[0].value,
                         '10.0.0.1')

        ipattr2 = ipman.allocate(aserver)

        self.assertEqual(sorted(aserver.get_ips()),
                         sorted(['10.0.0.1', '10.0.0.3']))
        
        
        
        
        

        

########NEW FILE########
__FILENAME__ = clean
from rest import request

BASE_URL = 'http://localhost:9999'

status, headers, data = request('DELETE', BASE_URL + '/pool/api_test_pool')
print 'DELETE /pool/api_test_pool (%i)' % status
status, headers, data = request('DELETE', BASE_URL + '/pool/api_test_child')
print 'DELETE /pool/api_test_child (%i)' % status

########NEW FILE########
__FILENAME__ = rest
import httplib
import logging
from urllib import urlencode
from urlparse import urlsplit

def request(method, url, body='', headers={}):
    logging.debug('%s %s' % (method, url))
    if type(body) != type(''):
        body = urlencode(body)
    url = urlsplit(url, 'http')

    conn = httplib.HTTPConnection(url.hostname, url.port)
    if url.query:
        query = '%s?%s' % (url.path, url.query)
    else:
        query = url.path
    conn.request(method, query, body, headers)
    response = conn.getresponse()
    length = response.getheader('Content-length', None)
    if length:
        data = response.read(int(length))
    else:
        data = response.read()
    conn.close()
    if response.status >= 400:
        logging.debug('Server error %s: %s' % (response.status, data))
    return (response.status, response.getheaders(), data)

def tinyurl(url):
    status, response = request('GET', 'http://tinyurl.com/api-create.php?url=%s' % url)
    return response

########NEW FILE########
__FILENAME__ = test
from rest import request
from pprint import pprint
from traceback import format_exc

try: import json
except ImportError: import simplejson as json

BASE_URL = 'http://localhost:9999'

def test_default_delegate():
    status, headers, data = request('GET', BASE_URL + '/')
    assert status == 200
    assert type(json.loads(data)) == list
    return True

def test_types_delegate():
    status, headers, data = request('GET', BASE_URL + '/server')
    assert status == 200
    data = json.loads(data)
    assert type(data) == list
    if len(data) > 0:
        assert type(data[0]) == str
    return True

def test_action_delegate():
    testname = '/pool/api_test_pool'

    test_create(testname)
    test_create('/pool/api_test_child')

    test_action_addattr(testname)
    test_action_delattr(testname)
    test_action_insert(testname)
    test_action_remove(testname)
    test_action_show(testname)

    test_delete('/pool/api_test_child')
    test_delete(testname)

def test_create(testname):
    status, headers, data = request('POST', BASE_URL + testname)
    assert status == 201
    data = json.loads(data)
    assert 'object' in data
    assert data['object'] == testname
    return True

def test_action_addattr(testname):
    status, headers, data = request('GET', BASE_URL + testname + '/addattr?key=testkey&value=testvalue')
    assert status == 200
    data = json.loads(data)
    assert type(data) == dict
    assert data['attrs'] == [{'key': 'testkey', 'value': 'testvalue', 'subkey': None, 'number': None, 'datatype': 'string'}]
    return True

def test_action_delattr(testname):
    status, headers, data = request('GET', BASE_URL + testname + '/delattr?key=testkey')
    assert status == 200
    data = json.loads(data)
    assert len(data['attrs']) == 0
    return True

def test_action_insert(testname):
    status, headers, data = request('GET', BASE_URL + testname + '/insert?object=/pool/api_test_child')
    assert status == 200
    data = json.loads(data)
    assert data['contents'] == ['/pool/api_test_child']
    return True

def test_action_remove(testname):
    status, headers, data = request('GET', BASE_URL + testname + '/remove?object=/pool/api_test_child')
    assert status == 200
    data = json.loads(data)
    assert data['contents'] == []
    return True

def test_action_show(testname):
    status, headers, data = request('GET', BASE_URL + testname + '/show')
    assert status == 200
    data = json.loads(data)
    for field in ('object', 'attrs', 'contents', 'parents', 'actions'):
        assert field in data.keys()
    return True

def test_delete(testname):
    status, headers, data = request('DELETE', BASE_URL + testname)
    assert status in (200, 202, 204)
    return True

if __name__ == '__main__':
    test_default_delegate()
    test_types_delegate()
    test_action_delegate()

########NEW FILE########
