__FILENAME__ = add_item
"""
Looks up a host based on its name, and then adds an item to it
"""

from pyzabbix import ZabbixAPI

# The hostname at which the Zabbix web interface is available
ZABBIX_SERVER = 'https://zabbix.example.com'

zapi = ZabbixAPI(ZABBIX_SERVER)

# Login to the Zabbix API
zapi.login('api_username', 'api_password')

host_name = 'example.com'

hosts = zapi.host.get(filter={"host": host_name})
if hosts:
    host_id = hosts[0]["hostid"]
    print("Found host id {0}".format(host_id))

    zapi.item.create(
        hostid=host_id,
        description='Used disk space on $1 in %',
        key_='vfs.fs.size[/,pused]',
    )
else:
    print("No hosts found")

########NEW FILE########
__FILENAME__ = current_issues
"""
Shows a list of all current issues (AKA tripped triggers)
"""

from getpass import getpass
from pyzabbix import ZabbixAPI

# The hostname at which the Zabbix web interface is available
ZABBIX_SERVER = 'https://zabbix.example.com'

zapi = ZabbixAPI(ZABBIX_SERVER)

# Login to the Zabbix API
zapi.login('api_username', 'api_password')

# Get a list of all issues (AKA tripped triggers)
triggers = zapi.trigger.get(only_true=1,
    skipDependent=1,
    monitored=1,
    active=1,
    output='extend',
    expandDescription=1,
    expandData='host',
)

# Do another query to find out which issues are Unacknowledged
unack_triggers = zapi.trigger.get(only_true=1,
    skipDependent=1,
    monitored=1,
    active=1,
    output='extend',
    expandDescription=1,
    expandData='host',
    withLastEventUnacknowledged=1,
)
unack_trigger_ids = [t['triggerid'] for t in unack_triggers]
for t in triggers:
    t['unacknowledged'] = True if t['triggerid'] in unack_trigger_ids\
    else False

# Print a list containing only "tripped" triggers
for t in triggers:
    if int(t['value']) == 1:
        print("{0} - {1} {2}".format(
            t['host'],
            t['description'],
            '(Unack)' if t['unacknowledged'] else '')
        )

########NEW FILE########
__FILENAME__ = fix_host_ips
"""
Zabbix stores the DNS name and the IP for each host that it monitors, and
uses one or the other to connect to the host.  It is good practice to make
sure the IP and DNS name are both correct.  This script checks the DNS and
IP for all hosts in Zabbix, compares the IP against an actual DNS lookup,
and fixes it if required.
"""

import socket
from getpass import getpass
from pyzabbix import ZabbixAPI, ZabbixAPIException

# The hostname at which the Zabbix web interface is available
ZABBIX_SERVER = 'https://zabbix.example.com'

zapi = ZabbixAPI(ZABBIX_SERVER)

# Login to the Zabbix API
zapi.login('api_username', 'api_password')

# Loop through all hosts
for h in zapi.host.get(extendoutput=True):
    # Make sure the hosts are named according to their FQDN
    if h['dns'] != h['host']:
        print('Warning: %s has dns "%s"' % (h['host'], h['dns']))

    # Make sure they are using hostnames to connect rather than IPs
    if h['useip'] == '1':
        print('%s is using IP instead of hostname. Skipping.' % h['host'])
        continue

    # Do a DNS lookup for the host's DNS name
    try:
        lookup = socket.gethostbyaddr(h['dns'])
    except socket.gaierror as e:
        print(h['dns'], e)
        continue
    actual_ip = lookup[2][0]

    # Check whether the looked-up IP matches the one stored in the host's IP
    # field
    if actual_ip != h['ip']:
        print("%s has the wrong IP: %s. Changing it to: %s" % (h['host'],
                                                               h['ip'],
                                                               actual_ip))

        # Set the host's IP field to match what the DNS lookup said it should
        # be
        try:
            zapi.host.update(hostid=h['hostid'], ip=actual_ip)
        except ZabbixAPIException as e:
            print(e)

########NEW FILE########
__FILENAME__ = trend_data
"""
Retrieves trend data for a given item_id
"""

from getpass import getpass
from pyzabbix import ZabbixAPI
from datetime import datetime
import time

# The hostname at which the Zabbix web interface is available
ZABBIX_SERVER = 'https://zabbix.example.com'

zapi = ZabbixAPI(ZABBIX_SERVER)

# Login to the Zabbix API
zapi.login('api_username', 'api_password')

item_id = 'item_id'

# Create a time range
time_till = time.mktime(datetime.now().timetuple())
time_from = time_till - 60 * 60 * 4  # 4 hours

# Query item's trend data
history = zapi.history.get(itemids=[item_id],
    time_from=time_from,
    time_till=time_till,
    output='extend',
    limit='5000',
)

# If nothing was found, try getting it from history
if not len(history):
    history = zapi.history.get(itemids=[item_id],
        time_from=time_from,
        time_till=time_till,
        output='extend',
        limit='5000',
        history=0,
    )

# Print out each datapoint
for point in history:
    print("{0}: {1}".format(datetime.fromtimestamp(int(point['clock']))
    .strftime("%x %X"), point['value']))

########NEW FILE########
__FILENAME__ = test_api
import unittest
import httpretty
import json
from pyzabbix import ZabbixAPI


class TestPyZabbix(unittest.TestCase):

    @httpretty.activate
    def test_login(self):
        httpretty.register_uri(
            httpretty.POST,
            "http://example.com/api_jsonrpc.php",
            body=json.dumps({
                "jsonrpc": "2.0",
                "result": "0424bd59b807674191e7d77572075f33",
                "id": 0
            }),
        )

        zapi = ZabbixAPI('http://example.com')
        zapi.login('mylogin', 'mypass')

        # Check request
        self.assertEqual(
            httpretty.last_request().body,
            json.dumps({
                'jsonrpc': '2.0',
                'method': 'user.login',
                'params': {'user': 'mylogin', 'password': 'mypass'},
                'auth': '',
                'id': 0,
            })
        )
        self.assertEqual(
            httpretty.last_request().headers['content-type'],
            'application/json-rpc'
        )
        self.assertEqual(
            httpretty.last_request().headers['user-agent'],
            'python/pyzabbix'
        )

        # Check response
        self.assertEqual(zapi.auth, "0424bd59b807674191e7d77572075f33")

    @httpretty.activate
    def test_host_get(self):
        httpretty.register_uri(
            httpretty.POST,
            "http://example.com/api_jsonrpc.php",
            body=json.dumps({
                "jsonrpc": "2.0",
                "result": [{"hostid": 1234}],
                "id": 0
            }),
        )

        zapi = ZabbixAPI('http://example.com')
        zapi.auth = "123"
        result = zapi.host.get()

        # Check request
        self.assertEqual(
            httpretty.last_request().body,
            json.dumps({
                'jsonrpc': '2.0',
                'method': 'host.get',
                'params': {},
                'auth': '123',
                'id': 0,
            })
        )

        # Check response
        self.assertEqual(result, [{"hostid": 1234}])

    @httpretty.activate
    def test_host_delete(self):
        httpretty.register_uri(
            httpretty.POST,
            "http://example.com/api_jsonrpc.php",
            body=json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "itemids": [
                        "22982",
                        "22986"
                    ]
                },
                "id": 0
            }),
        )

        zapi = ZabbixAPI('http://example.com')
        zapi.auth = "123"
        result = zapi.host.delete("22982", "22986")

        # Check request
        self.assertEqual(
            httpretty.last_request().body,
            json.dumps({
                'jsonrpc': '2.0',
                'method': 'host.delete',
                'params': ["22982", "22986"],
                'auth': '123',
                'id': 0,
            })
        )

        # Check response
        self.assertEqual(set(result["itemids"]), set(["22982", "22986"]))

########NEW FILE########
