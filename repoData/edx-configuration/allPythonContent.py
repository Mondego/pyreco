__FILENAME__ = sqs
# Copyright 2013 John Jarvis <john@jarv.org>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


import os
import sys
import time
import json
try:
    import boto.sqs
    from boto.exception import NoAuthHandlerFound
except ImportError:
    print "Boto is required for the sqs_notify callback plugin"
    raise


class CallbackModule(object):
    """
    This Ansible callback plugin sends task events
    to SQS.

    The following vars must be set in the environment:
        ANSIBLE_ENABLE_SQS - enables the callback module
        SQS_REGION - AWS region to connect to
        SQS_MSG_PREFIX - Additional data that will be put
                         on the queue (optional)

    The following events are put on the queue
        - FAILURE events
        - OK events
        - TASK events
        - START events
    """
    def __init__(self):

        self.start_time = time.time()

        if 'ANSIBLE_ENABLE_SQS' in os.environ:
            self.enable_sqs = True
            if not 'SQS_REGION' in os.environ:
                print 'ANSIBLE_ENABLE_SQS enabled but SQS_REGION ' \
                      'not defined in environment'
                sys.exit(1)
            self.region = os.environ['SQS_REGION']
            try:
                self.sqs = boto.sqs.connect_to_region(self.region)
            except NoAuthHandlerFound:
                print 'ANSIBLE_ENABLE_SQS enabled but cannot connect ' \
                      'to AWS due invalid credentials'
                sys.exit(1)
            if not 'SQS_NAME' in os.environ:
                print 'ANSIBLE_ENABLE_SQS enabled but SQS_NAME not ' \
                      'defined in environment'
                sys.exit(1)
            self.name = os.environ['SQS_NAME']
            self.queue = self.sqs.create_queue(self.name)
            if 'SQS_MSG_PREFIX' in os.environ:
                self.prefix = os.environ['SQS_MSG_PREFIX']
            else:
                self.prefix = ''

            self.last_seen_ts = {}
        else:
            self.enable_sqs = False

    def runner_on_failed(self, host, res, ignore_errors=False):
        if self.enable_sqs:
            if not ignore_errors:
                self._send_queue_message(res, 'FAILURE')

    def runner_on_ok(self, host, res):
        if self.enable_sqs:
            # don't send the setup results
            if res['invocation']['module_name'] != "setup":
                self._send_queue_message(res, 'OK')

    def playbook_on_task_start(self, name, is_conditional):
        if self.enable_sqs:
            self._send_queue_message(name, 'TASK')

    def playbook_on_play_start(self, pattern):
        if self.enable_sqs:
            self._send_queue_message(pattern, 'START')

    def playbook_on_stats(self, stats):
        if self.enable_sqs:
            d = {}
            delta = time.time() - self.start_time
            d['delta'] = delta
            for s in ['changed', 'failures', 'ok', 'processed', 'skipped']:
                d[s] = getattr(stats, s)
            self._send_queue_message(d, 'STATS')

    def _send_queue_message(self, msg, msg_type):
        if self.enable_sqs:
            from_start = time.time() - self.start_time
            payload = {msg_type: msg}
            payload['TS'] = from_start
            payload['PREFIX'] = self.prefix
            # update the last seen timestamp for
            # the message type
            self.last_seen_ts[msg_type] = time.time()
            if msg_type in ['OK', 'FAILURE']:
                # report the delta between the OK/FAILURE and
                # last TASK
                if 'TASK' in self.last_seen_ts:
                    from_task = \
                        self.last_seen_ts[msg_type] - self.last_seen_ts['TASK']
                    payload['delta'] = from_task
                for output in ['stderr', 'stdout']:
                    if output in payload[msg_type]:
                        # only keep the last 1000 characters
                        # of stderr and stdout
                        if len(payload[msg_type][output]) > 1000:
                            payload[msg_type][output] = "(clipping) ... " \
                                    + payload[msg_type][output][-1000:]

            self.sqs.send_message(self.queue, json.dumps(payload))

########NEW FILE########
__FILENAME__ = ec2
#!/usr/bin/env python

'''
EC2 external inventory script
=================================

Generates inventory that Ansible can understand by making API request to
AWS EC2 using the Boto library.

NOTE: This script assumes Ansible is being executed where the environment
variables needed for Boto have already been set:
    export AWS_ACCESS_KEY_ID='AK123'
    export AWS_SECRET_ACCESS_KEY='abc123'

If you're using eucalyptus you need to set the above variables and
you need to define:

    export EC2_URL=http://hostname_of_your_cc:port/services/Eucalyptus

For more details, see: http://docs.pythonboto.org/en/latest/boto_config_tut.html

When run against a specific host, this script returns the following variables:
 - ec2_ami_launch_index
 - ec2_architecture
 - ec2_association
 - ec2_attachTime
 - ec2_attachment
 - ec2_attachmentId
 - ec2_client_token
 - ec2_deleteOnTermination
 - ec2_description
 - ec2_deviceIndex
 - ec2_dns_name
 - ec2_eventsSet
 - ec2_group_name
 - ec2_hypervisor
 - ec2_id
 - ec2_image_id
 - ec2_instanceState
 - ec2_instance_type
 - ec2_ipOwnerId
 - ec2_ip_address
 - ec2_item
 - ec2_kernel
 - ec2_key_name
 - ec2_launch_time
 - ec2_monitored
 - ec2_monitoring
 - ec2_networkInterfaceId
 - ec2_ownerId
 - ec2_persistent
 - ec2_placement
 - ec2_platform
 - ec2_previous_state
 - ec2_private_dns_name
 - ec2_private_ip_address
 - ec2_publicIp
 - ec2_public_dns_name
 - ec2_ramdisk
 - ec2_reason
 - ec2_region
 - ec2_requester_id
 - ec2_root_device_name
 - ec2_root_device_type
 - ec2_security_group_ids
 - ec2_security_group_names
 - ec2_shutdown_state
 - ec2_sourceDestCheck
 - ec2_spot_instance_request_id
 - ec2_state
 - ec2_state_code
 - ec2_state_reason
 - ec2_status
 - ec2_subnet_id
 - ec2_tenancy
 - ec2_virtualization_type
 - ec2_vpc_id

These variables are pulled out of a boto.ec2.instance object. There is a lack of
consistency with variable spellings (camelCase and underscores) since this
just loops through all variables the object exposes. It is preferred to use the
ones with underscores when multiple exist.

In addition, if an instance has AWS Tags associated with it, each tag is a new
variable named:
 - ec2_tag_[Key] = [Value]

Security groups are comma-separated in 'ec2_security_group_ids' and
'ec2_security_group_names'.
'''

# (c) 2012, Peter Sankauskas
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

import sys
import os
import argparse
import re
from time import time
import boto
from boto import ec2
from boto import rds
from boto import route53
import ConfigParser

try:
    import json
except ImportError:
    import simplejson as json


class Ec2Inventory(object):
    def __init__(self):
        ''' Main execution path '''

        # Inventory grouped by instance IDs, tags, security groups, regions,
        # and availability zones
        self.inventory = {}

        # Index of hostname (address) to instance ID
        self.index = {}

        # Read settings and parse CLI arguments
        self.parse_cli_args()
        self.read_settings()

        # Cache
        if self.args.refresh_cache:
            self.do_api_calls_update_cache()
        elif not self.is_cache_valid():
            self.do_api_calls_update_cache()

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()

        elif self.args.list:
            # Display list of instances for inventory
            if len(self.inventory) == 0:
                data_to_print = self.get_inventory_from_cache()
            else:
                data_to_print = self.json_format_dict(self.inventory, True)
        print data_to_print


    def is_cache_valid(self):
        ''' Determines if the cache files have expired, or if it is still valid '''

        if self.args.tags_only:
            to_check = self.cache_path_tags
        else:
            to_check = self.cache_path_cache

        if os.path.isfile(to_check):
            mod_time = os.path.getmtime(to_check)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_index):
                    return True

        return False


    def read_settings(self):
        ''' Reads the settings from the ec2.ini file '''

        config = ConfigParser.SafeConfigParser()
        config.read(self.args.inifile)

        # is eucalyptus?
        self.eucalyptus_host = None
        self.eucalyptus = False
        if config.has_option('ec2', 'eucalyptus'):
            self.eucalyptus = config.getboolean('ec2', 'eucalyptus')
        if self.eucalyptus and config.has_option('ec2', 'eucalyptus_host'):
            self.eucalyptus_host = config.get('ec2', 'eucalyptus_host')

        # Regions
        self.regions = []
        configRegions = config.get('ec2', 'regions')
        configRegions_exclude = config.get('ec2', 'regions_exclude')
        if (configRegions == 'all'):
            if self.eucalyptus_host:
                self.regions.append(boto.connect_euca(host=self.eucalyptus_host).region.name)
            else:
                for regionInfo in ec2.regions():
                    if regionInfo.name not in configRegions_exclude:
                        self.regions.append(regionInfo.name)
        else:
            self.regions = configRegions.split(",")

        # Destination addresses
        self.destination_variable = config.get('ec2', 'destination_variable')
        self.vpc_destination_variable = config.get('ec2', 'vpc_destination_variable')

        # Route53
        self.route53_enabled = config.getboolean('ec2', 'route53')
        self.route53_excluded_zones = []
        if config.has_option('ec2', 'route53_excluded_zones'):
            self.route53_excluded_zones.extend(
                config.get('ec2', 'route53_excluded_zones', '').split(','))

        # Cache related
        if 'EC2_CACHE_PATH' in os.environ:
            cache_path = os.environ['EC2_CACHE_PATH']
        elif self.args.cache_path:
            cache_path = self.args.cache_path
        else:
            cache_path = config.get('ec2', 'cache_path')
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        self.cache_path_cache = cache_path + "/ansible-ec2.cache"
        self.cache_path_tags = cache_path + "/ansible-ec2.tags.cache"
        self.cache_path_index = cache_path + "/ansible-ec2.index"
        self.cache_max_age = config.getint('ec2', 'cache_max_age')



    def parse_cli_args(self):
        ''' Command line argument processing '''

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on EC2')
        parser.add_argument('--tags-only', action='store_true', default=False,
                           help='only return tags (default: False)')
        parser.add_argument('--list', action='store_true', default=True,
                           help='List instances (default: True)')
        parser.add_argument('--host', action='store',
                           help='Get all the variables about a specific instance')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                           help='Force refresh of cache by making API requests to EC2 (default: False - use cache files)')

        default_inifile = os.environ.get("ANSIBLE_EC2_INI", os.path.dirname(os.path.realpath(__file__))+'/ec2.ini')

        parser.add_argument('--inifile', dest='inifile', help='Path to init script to use', default=default_inifile)
        parser.add_argument(
            '--cache-path',
            help='Override the cache path set in ini file',
            required=False)
        self.args = parser.parse_args()


    def do_api_calls_update_cache(self):
        ''' Do API calls to each region, and save data in cache files '''

        if self.route53_enabled:
            self.get_route53_records()

        for region in self.regions:
            self.get_instances_by_region(region)
            self.get_rds_instances_by_region(region)

        if self.args.tags_only:
            self.write_to_cache(self.inventory, self.cache_path_tags)
        else:
            self.write_to_cache(self.inventory, self.cache_path_cache)

        self.write_to_cache(self.index, self.cache_path_index)

    def get_instances_by_region(self, region):
        ''' Makes an AWS EC2 API call to the list of instances in a particular
        region '''

        try:
            if self.eucalyptus:
                conn = boto.connect_euca(host=self.eucalyptus_host)
                conn.APIVersion = '2010-08-31'
            else:
                conn = ec2.connect_to_region(region)

            # connect_to_region will fail "silently" by returning None if the region name is wrong or not supported
            if conn is None:
                print("region name: %s likely not supported, or AWS is down.  connection to region failed." % region)
                sys.exit(1)

            reservations = conn.get_all_instances()
            for reservation in reservations:
                instances = sorted(reservation.instances)
                for instance in instances:
                    self.add_instance(instance, region)

        except boto.exception.BotoServerError as e:
            if  not self.eucalyptus:
                print "Looks like AWS is down again:"
            print e
            sys.exit(1)

    def get_rds_instances_by_region(self, region):
	''' Makes an AWS API call to the list of RDS instances in a particular
        region '''

        try:
            conn = rds.connect_to_region(region)
            if conn:
                instances = conn.get_all_dbinstances()
                for instance in instances:
                    self.add_rds_instance(instance, region)
        except boto.exception.BotoServerError as e:
            print "Looks like AWS RDS is down: "
            print e
            sys.exit(1)

    def get_instance(self, region, instance_id):
        ''' Gets details about a specific instance '''
        if self.eucalyptus:
            conn = boto.connect_euca(self.eucalyptus_host)
            conn.APIVersion = '2010-08-31'
        else:
            conn = ec2.connect_to_region(region)

        # connect_to_region will fail "silently" by returning None if the region name is wrong or not supported
        if conn is None:
            print("region name: %s likely not supported, or AWS is down.  connection to region failed." % region)
            sys.exit(1)

        reservations = conn.get_all_instances([instance_id])
        for reservation in reservations:
            for instance in reservation.instances:
                return instance


    def add_instance(self, instance, region):
        ''' Adds an instance to the inventory and index, as long as it is
        addressable '''

        # Only want running instances
        if instance.state != 'running':
            return

        # Select the best destination address
        if instance.subnet_id:
            dest = getattr(instance, self.vpc_destination_variable)
        else:
            dest =  getattr(instance, self.destination_variable)

        if not dest:
            # Skip instances we cannot address (e.g. private VPC subnet)
            return

        # Add to index
        self.index[dest] = [region, instance.id]

        # Inventory: Group by instance ID (always a group of 1)
        self.inventory[instance.id] = [dest]

        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, instance.placement, dest)

        # Inventory: Group by instance type
        self.push(self.inventory, self.to_safe('type_' + instance.instance_type), dest)

        # Inventory: Group by key pair
        if instance.key_name:
            self.push(self.inventory, self.to_safe('key_' + instance.key_name), dest)

        # Inventory: Group by security group
        try:
            for group in instance.groups:
                key = self.to_safe("security_group_" + group.name)
                self.push(self.inventory, key, dest)
        except AttributeError:
            print 'Package boto seems a bit older.'
            print 'Please upgrade boto >= 2.3.0.'
            sys.exit(1)

        # Inventory: Group by tag keys
        for k, v in instance.tags.iteritems():
            key = self.to_safe("tag_" + k + "=" + v)
            self.push(self.inventory, key, dest)
            self.keep_first(self.inventory, 'first_in_' + key, dest)

        # Inventory: Group by Route53 domain names if enabled
        if self.route53_enabled:
            route53_names = self.get_instance_route53_names(instance)
            for name in route53_names:
                self.push(self.inventory, name, dest)


    def add_rds_instance(self, instance, region):
        ''' Adds an RDS instance to the inventory and index, as long as it is
        addressable '''

        # Only want available instances
        if instance.status != 'available':
            return

        # Select the best destination address
        #if instance.subnet_id:
            #dest = getattr(instance, self.vpc_destination_variable)
        #else:
            #dest =  getattr(instance, self.destination_variable)
        dest = instance.endpoint[0]

        if not dest:
            # Skip instances we cannot address (e.g. private VPC subnet)
            return

        # Add to index
        self.index[dest] = [region, instance.id]

        # Inventory: Group by instance ID (always a group of 1)
        self.inventory[instance.id] = [dest]

        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, instance.availability_zone, dest)

        # Inventory: Group by instance type
        self.push(self.inventory, self.to_safe('type_' + instance.instance_class), dest)

        # Inventory: Group by security group
        try:
            if instance.security_group:
                key = self.to_safe("security_group_" + instance.security_group.name)
                self.push(self.inventory, key, dest)
        except AttributeError:
            print 'Package boto seems a bit older.'
            print 'Please upgrade boto >= 2.3.0.'
            sys.exit(1)

        # Inventory: Group by engine
        self.push(self.inventory, self.to_safe("rds_" + instance.engine), dest)

        # Inventory: Group by parameter group
        self.push(self.inventory, self.to_safe("rds_parameter_group_" + instance.parameter_group.name), dest)


    def get_route53_records(self):
        ''' Get and store the map of resource records to domain names that
        point to them. '''

        r53_conn = route53.Route53Connection()
        all_zones = r53_conn.get_zones()

        route53_zones = [ zone for zone in all_zones if zone.name[:-1]
                          not in self.route53_excluded_zones ]

        self.route53_records = {}

        for zone in route53_zones:
            rrsets = r53_conn.get_all_rrsets(zone.id)

            for record_set in rrsets:
                record_name = record_set.name

                if record_name.endswith('.'):
                    record_name = record_name[:-1]

                for resource in record_set.resource_records:
                    self.route53_records.setdefault(resource, set())
                    self.route53_records[resource].add(record_name)


    def get_instance_route53_names(self, instance):
        ''' Check if an instance is referenced in the records we have from
        Route53. If it is, return the list of domain names pointing to said
        instance. If nothing points to it, return an empty list. '''

        instance_attributes = [ 'public_dns_name', 'private_dns_name',
                                'ip_address', 'private_ip_address' ]

        name_list = set()

        for attrib in instance_attributes:
            try:
                value = getattr(instance, attrib)
            except AttributeError:
                continue

            if value in self.route53_records:
                name_list.update(self.route53_records[value])

        return list(name_list)


    def get_host_info(self):
        ''' Get variables about a specific host '''

        if len(self.index) == 0:
            # Need to load index from cache
            self.load_index_from_cache()

        if not self.args.host in self.index:
            # try updating the cache
            self.do_api_calls_update_cache()
            if not self.args.host in self.index:
                # host migh not exist anymore
                return self.json_format_dict({}, True)

        (region, instance_id) = self.index[self.args.host]

        instance = self.get_instance(region, instance_id)
        instance_vars = {}
        for key in vars(instance):
            value = getattr(instance, key)
            key = self.to_safe('ec2_' + key)

            # Handle complex types
            if type(value) in [int, bool]:
                instance_vars[key] = value
            elif type(value) in [str, unicode]:
                instance_vars[key] = value.strip()
            elif type(value) == type(None):
                instance_vars[key] = ''
            elif key == 'ec2_region':
                instance_vars[key] = value.name
            elif key == 'ec2_tags':
                for k, v in value.iteritems():
                    key = self.to_safe('ec2_tag_' + k)
                    instance_vars[key] = v
            elif key == 'ec2_groups':
                group_ids = []
                group_names = []
                for group in value:
                    group_ids.append(group.id)
                    group_names.append(group.name)
                instance_vars["ec2_security_group_ids"] = ','.join(group_ids)
                instance_vars["ec2_security_group_names"] = ','.join(group_names)
            else:
                pass
                # TODO Product codes if someone finds them useful
                #print key
                #print type(value)
                #print value

        return self.json_format_dict(instance_vars, True)


    def push(self, my_dict, key, element):
        ''' Pushed an element onto an array that may not have been defined in
        the dict '''

        if key in my_dict:
            my_dict[key].append(element);
        else:
            my_dict[key] = [element]

    def keep_first(self, my_dict, key, element):
        if key not in my_dict:
            my_dict[key] = [element]

    def get_inventory_from_cache(self):
        ''' Reads the inventory from the cache file and returns it as a JSON
        object '''
        if self.args.tags_only:
            cache = open(self.cache_path_tags, 'r')
        else:
            cache = open(self.cache_path_cache, 'r')
        json_inventory = cache.read()
        return json_inventory


    def load_index_from_cache(self):
        ''' Reads the index from the cache file sets self.index '''

        cache = open(self.cache_path_index, 'r')
        json_index = cache.read()
        self.index = json.loads(json_index)


    def write_to_cache(self, data, filename):
        '''
            Writes data in JSON format to a file
            '''

        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()


    def to_safe(self, word):
        ''' Converts 'bad' characters in a string to underscores so they can be
        used as Ansible groups '''

        return re.sub("[^A-Za-z0-9\-]", "_", word)


    def json_format_dict(self, data, pretty=False):
        ''' Converts a dict to a JSON object and dumps it as a formatted
        string '''
        if self.args.tags_only:
            data = [key for key in data.keys() if 'tag_' in key]
        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)


# Run the script
Ec2Inventory()


########NEW FILE########
__FILENAME__ = ec2
../ec2.py
########NEW FILE########
__FILENAME__ = ec2
../ec2.py
########NEW FILE########
__FILENAME__ = repos_from_orgs
#!/usr/bin/python
#   Given a list of repos in a yaml
#   file will create or update mirrors
#
#   Generates /var/tmp/repos.json from
#   a yaml file containing a list of
#   github organizations

import yaml
import sys
import requests
import json
import subprocess
import os
import logging
import fcntl
from os.path import dirname, abspath, join
from argparse import ArgumentParser

def check_running(run_type=''):

    pid_file = '{}-{}.pid'.format(
        os.path.basename(__file__),run_type)
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # another instance is running
        sys.exit(0)

def run_cmd(cmd):
    logging.debug('running: {}\n'.format(cmd))
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True)
    for line in iter(process.stdout.readline, ""):
        logging.debug(line)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-r', '--refresh', action='store_true',
                        help="Refresh the list of repos", default=False)
    parser.add_argument('-d', '--datadir', help="repo directory")
    return parser.parse_args()


def refresh_cache():
    path = dirname(abspath(__file__))
    try:
        with open(join(path, 'orgs.yml')) as f:
            orgs = yaml.load(f)
    except IOError:
        print "Unable to read {}/orgs.yml, does it exist?".format(path)
        sys.exit(1)

    repos = []

    for org in orgs:
        page = 1
        while True:
            r = requests.get('https://api.github.com/users/{}/repos?page={}'.format(org, page))
            org_data = r.json()
            # request pages until we get zero results
            if not isinstance(org_data, list) or len(org_data) == 0:
                break
            for repo_data in org_data:
                if 'html_url' in repo_data:
                    repos.append({'html_url': repo_data['html_url'],
                                  'name': repo_data['name'],
                                  'org': repo_data['owner']['login']})
            page += 1
    with open('/var/tmp/repos.json', 'wb') as f:
        f.write(json.dumps(repos))


def update_repos():
    with open('/var/tmp/repos.json') as f:
        repos = json.load(f)
    for repo in repos:
        repo_path = os.path.join(args.datadir, repo['org'], repo['name'] + '.git')
        if not os.path.exists(repo_path):
            run_cmd('mkdir -p {}'.format(repo_path))
            run_cmd('git clone --mirror {} {}'.format(repo['html_url'], repo_path))
            run_cmd('cd {} && git update-server-info'.format(repo_path))
        else:
            run_cmd('cd {} && git fetch --all --tags'.format(repo_path))
            run_cmd('cd {} && git update-server-info'.format(repo_path))

if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(filename='/var/log/repos-from-orgs.log',
                        level=logging.DEBUG)
    if args.refresh:
        check_running('refresh')
        refresh_cache()
    else:
        check_running()
        if not args.datadir:
            print "Please specificy a repository directory"
            sys.exit(1)
        if not os.path.exists('/var/tmp/repos.json'):
            refresh_cache()
        update_repos()

########NEW FILE########
__FILENAME__ = pre_supervisor_checks
import argparse
import boto
from boto.utils import get_instance_metadata
from boto.exception import AWSConnectionError
import hipchat
import os
import subprocess
import traceback

# Services that should be checked for migrations.
MIGRATION_COMMANDS = {
        'lms': "{python} {code_dir}/manage.py lms migrate --noinput --settings=aws --db-dry-run --merge",
        'cms': "{python} {code_dir}/manage.py cms migrate --noinput --settings=aws --db-dry-run --merge",
        'xqueue': "{python} {code_dir}/manage.py xqueue migrate --noinput --settings=aws --db-dry-run --merge",
    }
HIPCHAT_USER = "PreSupervisor"

def services_for_instance(instance_id):
    """
    Get the list of all services named by the services tag in this
    instance's tags.
    """
    ec2 = boto.connect_ec2()
    reservations = ec2.get_all_instances(instance_ids=[instance_id])
    for reservation in reservations:
        for instance in reservation.instances:
            if instance.id == instance_id:
                try:
                    services = instance.tags['services'].split(',')
                except KeyError as ke:
                    msg = "Tag named 'services' not found on this instance({})".format(instance_id)
                    raise Exception(msg)

                for service in services:
                    yield service

def edp_for_instance(instance_id):
    ec2 = boto.connect_ec2()
    reservations = ec2.get_all_instances(instance_ids=[instance_id])
    for reservation in reservations:
        for instance in reservation.instances:
            if instance.id == instance_id:
                try:
                    environment = instance.tags['environment']
                    deployment = instance.tags['deployment']
                    play = instance.tags['play']
                except KeyError as ke:
                    msg = "{} tag not found on this instance({})".format(ke.message, instance_id)
                    raise Exception(msg)
                return (environment, deployment, play)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Enable all services that are in the services tag of this ec2 instance.")
    parser.add_argument("-a","--available",
        help="The location of the available services.")
    parser.add_argument("-e","--enabled",
        help="The location of the enabled services.")

    migration_args = parser.add_argument_group("edxapp_migrations",
            "Args for running edxapp migration checks.")
    migration_args.add_argument("--edxapp-code-dir",
            help="Location of the edx-platform code.")
    migration_args.add_argument("--edxapp-python",
            help="Path to python to use for executing migration check.")

    xq_migration_args = parser.add_argument_group("xqueue_migrations",
            "Args for running xqueue migration checks.")
    xq_migration_args.add_argument("--xqueue-code-dir",
            help="Location of the edx-platform code.")
    xq_migration_args.add_argument("--xqueue-python",
            help="Path to python to use for executing migration check.")

    hipchat_args = parser.add_argument_group("hipchat",
            "Args for hipchat notification.")
    hipchat_args.add_argument("-c","--hipchat-api-key",
        help="Hipchat token if you want to receive notifications via hipchat.")
    hipchat_args.add_argument("-r","--hipchat-room",
        help="Room to send messages to.")

    args = parser.parse_args()

    report = []
    prefix = None
    notify = None

    try:
        if args.hipchat_api_key:
            hc = hipchat.HipChat(token=args.hipchat_api_key)
            notify = lambda message: hc.message_room(room_id=args.hipchat_room,
                message_from=HIPCHAT_USER, message=message)
    except Exception as e:
        print("Failed to initialize hipchat, {}".format(e))
        traceback.print_exc()

    instance_id = get_instance_metadata()['instance-id']
    prefix = instance_id

    try:
        environment, deployment, play = edp_for_instance(instance_id)
        prefix = "{environment}-{deployment}-{play}-{instance_id}".format(
            environment=environment,
            deployment=deployment,
            play=play,
            instance_id=instance_id)
        for service in services_for_instance(instance_id):
            if service in MIGRATION_COMMANDS:
                # Do extra migration related stuff.
                if (service == 'lms' or service == 'cms') and args.edxapp_code_dir:
                    cmd = MIGRATION_COMMANDS[service].format(python=args.edxapp_python,
                        code_dir=args.edxapp_code_dir)
                    if os.path.exists(args.edxapp_code_dir):
                        os.chdir(args.edxapp_code_dir)
                        # Run migration check command.
                        output = subprocess.check_output(cmd, shell=True)
                        if 'Migrating' in output:
                            raise Exception("Migrations have not been run for {}".format(service))
                elif service == 'xqueue' and args.xqueue_code_dir:
                    cmd = MIGRATION_COMMANDS[service].format(python=args.xqueue_python,
                        code_dir=xqueue_code_dir)
                    if os.path.exists(args.xqueue_code_dir):
                        os.chdir(args.xqueue_code_dir)
                        # Run migration check command.
                        output = subprocess.check_output(cmd, shell=True)
                        if 'Migrating' in output:
                            raise Exception("Migrations have not been run for {}".format(service))
    
            # Link to available service.
            available_file = os.path.join(args.available, "{}.conf".format(service))
            link_location = os.path.join(args.enabled, "{}.conf".format(service))
            if os.path.exists(available_file):
                subprocess.call("ln -sf {} {}".format(available_file, link_location), shell=True)
                report.append("Linking service: {}".format(service))
            else:
                raise Exception("No conf available for service: {}".format(link_location))
    except AWSConnectionError as ae:
        msg = "{}: ERROR : {}".format(prefix, ae)
        if notify:
            notify(msg)
            notify(traceback.format_exc())
        raise ae
    except Exception as e:
        msg = "{}: ERROR : {}".format(prefix, e)
        print(msg)
        if notify:
            notify(msg)
    else:
        msg = "{}: {}".format(prefix, " | ".join(report))
        print(msg)
        if notify:
            notify(msg)

########NEW FILE########
__FILENAME__ = elb_reg
#!/usr/bin/env python

from argparse import ArgumentParser
import time
import boto


def await_elb_instance_state(lb, instance_id, awaited_state):
    """blocks until the ELB reports awaited_state
    for instance_id.
    lb = loadbalancer object
    instance_id : instance_id (string)
    awaited_state : state to poll for (string)"""

    start_time = time.time()
    while True:
        state = lb.get_instance_health([instance_id])[0].state
        if state == awaited_state:
            print "Load Balancer {lb} is in awaited state " \
                  "{awaited_state}, proceeding.".format(
                  lb=lb.dns_name,
                  awaited_state=awaited_state)
            break
        else:
            print "Checking again in 2 seconds. Elapsed time: {0}".format(
                time.time() - start_time)
            time.sleep(2)


def deregister():
    """Deregister the instance from all ELBs and wait for the ELB
    to report them out-of-service"""

    for lb in active_lbs:
        lb.deregister_instances([args.instance])
        await_elb_instance_state(lb, args.instance, 'OutOfService')


def register():
    """Register the instance for all ELBs and wait for the ELB
    to report them in-service"""
    for lb in active_lbs:
        lb.register_instances([args.instance])
        await_elb_instance_state(lb, args.instance, 'InService')


def parse_args():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="sp_action")
    subparsers.add_parser('register', help='register an instance')
    subparsers.add_parser('deregister', help='deregister an instance')

    parser.add_argument('-e', '--elbs', required=True,
                        help="Comma separated list of ELB names")
    parser.add_argument('-i', '--instance', required=True,
                        help="Single instance to operate on")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    elb = boto.connect_elb()
    elbs = elb.get_all_load_balancers()
    active_lbs = sorted(
        lb
        for lb in elbs
        if lb.name in args.elbs.split(','))

    print "ELB : " + str(args.elbs.split(','))
    print "Instance: " + str(args.instance)
    if args.sp_action == 'deregister':
        print "Deregistering an instance"
        deregister()
    elif args.sp_action == 'register':
        print "Registering an instance"
        register()

########NEW FILE########
__FILENAME__ = github_oauth_token
#!/usr/bin/env python

"""
Generate a GitHub OAuth token with a particular
set of permissions.

Usage:

    github_oauth_token.py USERNAME PASSWORD [SCOPE ...]

Example:

    github_oauth_token.py jenkins_user repo:status public_repo

This will prompt the user for the password.
"""

import sys
import requests
import json
import getpass
from textwrap import dedent

USAGE = "Usage: {0} USERNAME NOTE [SCOPE ...]"


def parse_args(arg_list):
    """
    Return a dict of the command line arguments.
    Prints an error message and exits if the arguments are invalid.
    """
    if len(arg_list) < 4:
        print USAGE.format(arg_list[0])
        exit(1)

    # Prompt for the password
    password = getpass.getpass()

    return {
        'username': arg_list[1],
        'password': password,
        'note': arg_list[2],
        'scopes': arg_list[3:],
    }


def get_oauth_token(username, password, scopes, note):
    """
    Create a GitHub OAuth token with the given scopes.
    If unsuccessful, print an error message and exit.

    Returns a tuple `(token, scopes)`
    """
    params = {'scopes': scopes, 'note': note}

    response = response = requests.post(
        'https://api.github.com/authorizations',
        data=json.dumps(params),
        auth=(username, password)
    )

    if response.status_code != 201:
        print dedent("""
            Could not create OAuth token.
            HTTP status code: {0}
            Content: {1}
        """.format(response.status_code, response.text)).strip()
        exit(1)

    try:
        token_data = response.json()
        return token_data['token'], token_data['scopes']

    except TypeError:
        print "Could not parse response data."
        exit(1)

    except KeyError:
        print "Could not retrieve data from response."
        exit(1)


def main():
    arg_dict = parse_args(sys.argv)
    token, scopes = get_oauth_token(
        arg_dict['username'], arg_dict['password'],
        arg_dict['scopes'], arg_dict['note']
    )

    print "Token: {0}".format(token)
    print "Scopes: {0}".format(", ".join(scopes))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = import_xml_courses
# Import XML Courses from git repos into the CMS.
# Run with sudo and make sure the user can clone
# the course repos.

# Output Has per course
#{
#    repo_url:
#    repo_name:
#    org:
#    course:
#    run:
#    disposition:
#    version:
#}

import argparse
from os.path import basename
import yaml

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Import XML courses from git repos.")
    parser.add_argument("-c", "--courses-csv", required=True,
        help="A CSV of xml courses to import.")
    args = parser.parse_args()

    courses = open(args.courses_csv, 'r')

    all_course_data = []
    all_xml_mappings = {}
    for line in courses:
        cols = line.strip().split(',')
        slug = cols[0]
        author_format = cols[1]
        disposition = cols[2]
        repo_url = cols[4]
        version = cols[5]

        if author_format.lower() != 'xml' \
          or disposition.lower() == "don't import":
            continue

        # Checkout w/tilde
        org, course, run = slug.split("/")
        repo_name = "{}~{}".format(basename(repo_url).rstrip('.git'), run)

        course_info = {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "org": org,
            "course": course,
            "run": run,
            "disposition": disposition.lower(),
            "version": version,
        }
        all_course_data.append(course_info)

        if disposition.lower() == "on disk":
            all_xml_mappings[slug] = 'xml'

    edxapp_xml_courses = { "EDXAPP_XML_COURSES": all_course_data, "EDXAPP_XML_MAPPINGS": all_xml_mappings }
    print yaml.safe_dump(edxapp_xml_courses, default_flow_style=False)

########NEW FILE########
__FILENAME__ = abbey
#!/usr/bin/env python -u
import sys
from argparse import ArgumentParser
import time
import json
import yaml
import os
try:
    import boto.ec2
    import boto.sqs
    from boto.vpc import VPCConnection
    from boto.exception import NoAuthHandlerFound, EC2ResponseError
    from boto.sqs.message import RawMessage
    from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping
except ImportError:
    print "boto required for script"
    sys.exit(1)

from pprint import pprint

AMI_TIMEOUT = 600  # time to wait for AMIs to complete
EC2_RUN_TIMEOUT = 180  # time to wait for ec2 state transition
EC2_STATUS_TIMEOUT = 300  # time to wait for ec2 system status checks
NUM_TASKS = 5  # number of tasks for time summary report
NUM_PLAYBOOKS = 2


class Unbuffered:
    """
    For unbuffered output, not
    needed if PYTHONUNBUFFERED is set
    """
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--noop', action='store_true',
                        help="don't actually run the cmds",
                        default=False)
    parser.add_argument('--secure-vars-file', required=False,
                        metavar="SECURE_VAR_FILE", default=None,
                        help="path to secure-vars from the root of "
                        "the secure repo. By default <deployment>.yml and "
                        "<environment>-<deployment>.yml will be used if they "
                        "exist in <secure-repo>/ansible/vars/. This secure file "
                        "will be used in addition to these if they exist.")
    parser.add_argument('--stack-name',
                        help="defaults to ENVIRONMENT-DEPLOYMENT",
                        metavar="STACK_NAME",
                        required=False)
    parser.add_argument('-p', '--play',
                        help='play name without the yml extension',
                        metavar="PLAY", required=True)
    parser.add_argument('--playbook-dir',
                        help='directory to find playbooks in',
                        default='configuration/playbooks/edx-east',
                        metavar="PLAYBOOKDIR", required=False)
    parser.add_argument('-d', '--deployment', metavar="DEPLOYMENT",
                        required=True)
    parser.add_argument('-e', '--environment', metavar="ENVIRONMENT",
                        required=True)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="turn on verbosity")
    parser.add_argument('--no-cleanup', action='store_true',
                        help="don't cleanup on failures")
    parser.add_argument('--vars', metavar="EXTRA_VAR_FILE",
                        help="path to extra var file", required=False)
    parser.add_argument('--refs', metavar="GIT_REFS_FILE",
                        help="path to a var file with app git refs", required=False)
    parser.add_argument('--configuration-version', required=False,
                        help="configuration repo branch(no hashes)",
                        default="master")
    parser.add_argument('--configuration-secure-version', required=False,
                        help="configuration-secure repo branch(no hashes)",
                        default="master")
    parser.add_argument('--configuration-secure-repo', required=False,
                        default="git@github.com:edx-ops/prod-secure",
                        help="repo to use for the secure files")
    parser.add_argument('--configuration-private-version', required=False,
                        help="configuration-private repo branch(no hashes)",
                        default="master")
    parser.add_argument('--configuration-private-repo', required=False,
                        default="git@github.com:edx-ops/ansible-private",
                        help="repo to use for private playbooks")
    parser.add_argument('-c', '--cache-id', required=True,
                        help="unique id to use as part of cache prefix")
    parser.add_argument('-i', '--identity', required=False,
                        help="path to identity file for pulling "
                             "down configuration-secure",
                        default=None)
    parser.add_argument('-r', '--region', required=False,
                        default="us-east-1",
                        help="aws region")
    parser.add_argument('-k', '--keypair', required=False,
                        default="deployment",
                        help="AWS keypair to use for instance")
    parser.add_argument('-t', '--instance-type', required=False,
                        default="m1.large",
                        help="instance type to launch")
    parser.add_argument("--role-name", required=False,
                        default="abbey",
                        help="IAM role name to use (must exist)")
    parser.add_argument("--msg-delay", required=False,
                        default=5,
                        help="How long to delay message display from sqs "
                             "to ensure ordering")
    parser.add_argument("--hipchat-room-id", required=False,
                        default=None,
                        help="The API ID of the Hipchat room to post"
                             "status messages to")
    parser.add_argument("--hipchat-api-token", required=False,
                        default=None,
                        help="The API token for Hipchat integration")
    parser.add_argument("--root-vol-size", required=False,
                        default=50,
                        help="The size of the root volume to use for the "
                             "abbey instance.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-b', '--base-ami', required=False,
                       help="ami to use as a base ami",
                       default="ami-0568456c")
    group.add_argument('--blessed', action='store_true',
                       help="Look up blessed ami for env-dep-play.",
                       default=False)

    return parser.parse_args()


def get_instance_sec_group(vpc_id):

    grp_details = ec2.get_all_security_groups(
        filters={
            'vpc_id': vpc_id,
            'tag:play': args.play
        }
    )

    if len(grp_details) < 1:
        sys.stderr.write("ERROR: Expected atleast one security group, got {}\n".format(
            len(grp_details)))

    return grp_details[0].id


def get_blessed_ami():
    images = ec2.get_all_images(
        filters={
            'tag:environment': args.environment,
            'tag:deployment': args.deployment,
            'tag:play': args.play,
            'tag:blessed': True
        }
    )

    if len(images) != 1:
        raise Exception("ERROR: Expected only one blessed ami, got {}\n".format(
            len(images)))

    return images[0].id


def create_instance_args():
    """
    Looks up security group, subnet
    and returns arguments to pass into
    ec2.run_instances() including
    user data
    """

    vpc = VPCConnection()
    subnet = vpc.get_all_subnets(
        filters={
            'tag:aws:cloudformation:stack-name': stack_name,
            'tag:play': args.play}
    )
    if len(subnet) < 1:
        sys.stderr.write("ERROR: Expected at least one subnet, got {}\n".format(
            len(subnet)))
        sys.exit(1)
    subnet_id = subnet[0].id
    vpc_id = subnet[0].vpc_id

    security_group_id = get_instance_sec_group(vpc_id)

    if args.identity:
        config_secure = 'true'
        with open(args.identity) as f:
            identity_contents = f.read()
    else:
        config_secure = 'false'
        identity_contents = "dummy"

    user_data = """#!/bin/bash
set -x
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
base_dir="/var/tmp/edx-cfg"
extra_vars="$base_dir/extra-vars-$$.yml"
secure_identity="$base_dir/secure-identity"
git_ssh="$base_dir/git_ssh.sh"
configuration_version="{configuration_version}"
configuration_secure_version="{configuration_secure_version}"
configuration_private_version="{configuration_private_version}"
environment="{environment}"
deployment="{deployment}"
play="{play}"
config_secure={config_secure}
git_repo_name="configuration"
git_repo="https://github.com/edx/$git_repo_name"
git_repo_secure="{configuration_secure_repo}"
git_repo_secure_name="{configuration_secure_repo_basename}"
git_repo_private="{configuration_private_repo}"
git_repo_private_name=$(basename $git_repo_private .git)
secure_vars_file={secure_vars_file}
environment_deployment_secure_vars="$base_dir/$git_repo_secure_name/ansible/vars/{environment}-{deployment}.yml"
deployment_secure_vars="$base_dir/$git_repo_secure_name/ansible/vars/{deployment}.yml"
instance_id=\\
$(curl http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)
instance_ip=\\
$(curl http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null)
instance_type=\\
$(curl http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null)
playbook_dir="$base_dir/{playbook_dir}"

if $config_secure; then
    git_cmd="env GIT_SSH=$git_ssh git"
else
    git_cmd="git"
fi

ANSIBLE_ENABLE_SQS=true
SQS_NAME={queue_name}
SQS_REGION=us-east-1
SQS_MSG_PREFIX="[ $instance_id $instance_ip $environment-$deployment $play ]"
PYTHONUNBUFFERED=1

# environment for ansible
export ANSIBLE_ENABLE_SQS SQS_NAME SQS_REGION SQS_MSG_PREFIX PYTHONUNBUFFERED

if [[ ! -x /usr/bin/git || ! -x /usr/bin/pip ]]; then
    echo "Installing pkg dependencies"
    /usr/bin/apt-get update
    /usr/bin/apt-get install -y git python-pip python-apt \\
        git-core build-essential python-dev libxml2-dev \\
        libxslt-dev curl --force-yes
fi


rm -rf $base_dir
mkdir -p $base_dir
cd $base_dir

cat << EOF > $git_ssh
#!/bin/sh
exec /usr/bin/ssh -o StrictHostKeyChecking=no -i "$secure_identity" "\$@"
EOF

chmod 755 $git_ssh

if $config_secure; then
    cat << EOF > $secure_identity
{identity_contents}
EOF
fi

cat << EOF >> $extra_vars
---
# extra vars passed into
# abbey.py including versions
# of all the repositories
{extra_vars_yml}

{git_refs_yml}

# abbey will always run fake migrations
# this is so that the application can come
# up healthy
fake_migrations: true

# Use the build number an the dynamic cache key.
EDXAPP_UPDATE_STATIC_FILES_KEY: true
edxapp_dynamic_cache_key: {deployment}-{environment}-{play}-{cache_id}

disable_edx_services: true
EOF

chmod 400 $secure_identity

$git_cmd clone $git_repo $git_repo_name
cd $git_repo_name
$git_cmd checkout $configuration_version
cd $base_dir

if $config_secure; then
    $git_cmd clone $git_repo_secure $git_repo_secure_name
    cd $git_repo_secure_name
    $git_cmd checkout $configuration_secure_version
    cd $base_dir
fi

if [[ ! -z $git_repo_private ]]; then
    $git_cmd clone $git_repo_private $git_repo_private_name
    cd $git_repo_private_name
    $git_cmd checkout $configuration_private_version
    cd $base_dir
fi


cd $base_dir/$git_repo_name
sudo pip install -r requirements.txt

cd $playbook_dir

if [[ -r "$deployment_secure_vars" ]]; then
    extra_args_opts+=" -e@$deployment_secure_vars"
fi

if [[ -r "$environment_deployment_secure_vars" ]]; then
    extra_args_opts+=" -e@$environment_deployment_secure_vars"
fi

if $secure_vars_file; then
    extra_args_opts+=" -e@$secure_vars_file"
fi

extra_args_opts+=" -e@$extra_vars"

ansible-playbook -vvvv -c local -i "localhost," $play.yml $extra_args_opts
ansible-playbook -vvvv -c local -i "localhost," stop_all_edx_services.yml $extra_args_opts

rm -rf $base_dir

    """.format(
                configuration_version=args.configuration_version,
                configuration_secure_version=args.configuration_secure_version,
                configuration_secure_repo=args.configuration_secure_repo,
                configuration_secure_repo_basename=os.path.basename(
                    args.configuration_secure_repo),
                configuration_private_version=args.configuration_private_version,
                configuration_private_repo=args.configuration_private_repo,
                environment=args.environment,
                deployment=args.deployment,
                play=args.play,
                playbook_dir=args.playbook_dir,
                config_secure=config_secure,
                identity_contents=identity_contents,
                queue_name=run_id,
                extra_vars_yml=extra_vars_yml,
                git_refs_yml=git_refs_yml,
                secure_vars_file=secure_vars_file,
                cache_id=args.cache_id)

    mapping = BlockDeviceMapping()
    root_vol = BlockDeviceType(size=args.root_vol_size)
    mapping['/dev/sda1'] = root_vol

    ec2_args = {
        'security_group_ids': [security_group_id],
        'subnet_id': subnet_id,
        'key_name': args.keypair,
        'image_id': base_ami,
        'instance_type': args.instance_type,
        'instance_profile_name': args.role_name,
        'user_data': user_data,
        'block_device_map': mapping,
    }

    return ec2_args


def poll_sqs_ansible():
    """
    Prints events to the console and
    blocks until a final STATS ansible
    event is read off of SQS.

    SQS does not guarantee FIFO, for that
    reason there is a buffer that will delay
    messages before they are printed to the
    console.

    Returns length of the ansible run.
    """
    oldest_msg_ts = 0
    buf = []
    task_report = []  # list of tasks for reporting
    last_task = None
    completed = 0
    while True:
        messages = []
        while True:
            # get all available messages on the queue
            msgs = sqs_queue.get_messages(attributes='All')
            if not msgs:
                break
            messages.extend(msgs)

        for message in messages:
            recv_ts = float(
                message.attributes['ApproximateFirstReceiveTimestamp']) * .001
            sent_ts = float(message.attributes['SentTimestamp']) * .001
            try:
                msg_info = {
                    'msg': json.loads(message.get_body()),
                    'sent_ts': sent_ts,
                    'recv_ts': recv_ts,
                }
                buf.append(msg_info)
            except ValueError as e:
                print "!!! ERROR !!! unable to parse queue message, " \
                      "expecting valid json: {} : {}".format(
                          message.get_body(), e)
            if not oldest_msg_ts or recv_ts < oldest_msg_ts:
                oldest_msg_ts = recv_ts
            sqs_queue.delete_message(message)

        now = int(time.time())
        if buf:
            try:
                if (now - min([msg['recv_ts'] for msg in buf])) > args.msg_delay:
                    # sort by TS instead of recv_ts
                    # because the sqs timestamp is not as
                    # accurate
                    buf.sort(key=lambda k: k['msg']['TS'])
                    to_disp = buf.pop(0)
                    if 'START' in to_disp['msg']:
                        print '\n{:0>2.0f}:{:0>5.2f} {} : Starting "{}"'.format(
                            to_disp['msg']['TS'] / 60,
                            to_disp['msg']['TS'] % 60,
                            to_disp['msg']['PREFIX'],
                            to_disp['msg']['START']),

                    elif 'TASK' in to_disp['msg']:
                        print "\n{:0>2.0f}:{:0>5.2f} {} : {}".format(
                            to_disp['msg']['TS'] / 60,
                            to_disp['msg']['TS'] % 60,
                            to_disp['msg']['PREFIX'],
                            to_disp['msg']['TASK']),
                        last_task = to_disp['msg']['TASK']
                    elif 'OK' in to_disp['msg']:
                        if args.verbose:
                            print "\n"
                            for key, value in to_disp['msg']['OK'].iteritems():
                                print "    {:<15}{}".format(key, value)
                        else:
                            invocation = to_disp['msg']['OK']['invocation']
                            module = invocation['module_name']
                            # 'set_fact' does not provide a changed value.
                            if module == 'set_fact':
                                changed = "OK"
                            elif to_disp['msg']['OK']['changed']:
                                changed = "*OK*"
                            else:
                                changed = "OK"
                            print " {}".format(changed),
                        task_report.append({
                            'TASK': last_task,
                            'INVOCATION': to_disp['msg']['OK']['invocation'],
                            'DELTA': to_disp['msg']['delta'],
                        })
                    elif 'FAILURE' in to_disp['msg']:
                        print " !!!! FAILURE !!!!",
                        for key, value in to_disp['msg']['FAILURE'].iteritems():
                            print "    {:<15}{}".format(key, value)
                        raise Exception("Failed Ansible run")
                    elif 'STATS' in to_disp['msg']:
                        print "\n{:0>2.0f}:{:0>5.2f} {} : COMPLETE".format(
                            to_disp['msg']['TS'] / 60,
                            to_disp['msg']['TS'] % 60,
                            to_disp['msg']['PREFIX'])

                        # Since 3 ansible plays get run.
                        # We see the COMPLETE message 3 times
                        # wait till the last one to end listening
                        # for new messages.
                        completed += 1
                        if completed >= NUM_PLAYBOOKS:
                            return (to_disp['msg']['TS'], task_report)
            except KeyError:
                print "Failed to print status from message: {}".format(to_disp)

        if not messages:
            # wait 1 second between sqs polls
            time.sleep(1)


def create_ami(instance_id, name, description):

    params = {'instance_id': instance_id,
              'name': name,
              'description': description,
              'no_reboot': True}

    AWS_API_WAIT_TIME = 1
    image_id = ec2.create_image(**params)
    print("Checking if image is ready.")
    for _ in xrange(AMI_TIMEOUT):
        try:
            img = ec2.get_image(image_id)
            if img.state == 'available':
                print("Tagging image.")
                img.add_tag("environment", args.environment)
                time.sleep(AWS_API_WAIT_TIME)
                img.add_tag("deployment", args.deployment)
                time.sleep(AWS_API_WAIT_TIME)
                img.add_tag("play", args.play)
                time.sleep(AWS_API_WAIT_TIME)
                img.add_tag("configuration_ref", args.configuration_version)
                time.sleep(AWS_API_WAIT_TIME)
                img.add_tag("configuration_secure_ref", args.configuration_secure_version)
                time.sleep(AWS_API_WAIT_TIME)
                img.add_tag("configuration_secure_repo", args.configuration_secure_repo)
                time.sleep(AWS_API_WAIT_TIME)
                img.add_tag("cache_id", args.cache_id)
                time.sleep(AWS_API_WAIT_TIME)
                for repo, ref in git_refs.items():
                    key = "refs:{}".format(repo)
                    img.add_tag(key, ref)
                    time.sleep(AWS_API_WAIT_TIME)
                break
            else:
                time.sleep(1)
        except EC2ResponseError as e:
            if e.error_code == 'InvalidAMIID.NotFound':
                time.sleep(1)
            else:
                raise Exception("Unexpected error code: {}".format(
                    e.error_code))
            time.sleep(1)
    else:
        raise Exception("Timeout waiting for AMI to finish")

    return image_id


def launch_and_configure(ec2_args):
    """
    Creates an sqs queue, launches an ec2 instance,
    configures it and creates an AMI. Polls
    SQS for updates
    """

    print "{:<40}".format(
        "Creating SQS queue and launching instance for {}:".format(run_id))
    print
    for k, v in ec2_args.iteritems():
        if k != 'user_data':
            print "    {:<25}{}".format(k, v)
    print

    global sqs_queue
    global instance_id
    sqs_queue = sqs.create_queue(run_id)
    sqs_queue.set_message_class(RawMessage)
    res = ec2.run_instances(**ec2_args)
    inst = res.instances[0]
    instance_id = inst.id

    print "{:<40}".format(
        "Waiting for instance {} to reach running status:".format(instance_id)),
    status_start = time.time()
    for _ in xrange(EC2_RUN_TIMEOUT):
        res = ec2.get_all_instances(instance_ids=[instance_id])
        if res[0].instances[0].state == 'running':
            status_delta = time.time() - status_start
            run_summary.append(('EC2 Launch', status_delta))
            print "[ OK ] {:0>2.0f}:{:0>2.0f}".format(
                status_delta / 60,
                status_delta % 60)
            break
        else:
            time.sleep(1)
    else:
        raise Exception("Timeout waiting for running status: {} ".format(
            instance_id))

    print "{:<40}".format("Waiting for system status:"),
    system_start = time.time()
    for _ in xrange(EC2_STATUS_TIMEOUT):
        status = ec2.get_all_instance_status(inst.id)
        if status[0].system_status.status == u'ok':
            system_delta = time.time() - system_start
            run_summary.append(('EC2 Status Checks', system_delta))
            print "[ OK ] {:0>2.0f}:{:0>2.0f}".format(
                system_delta / 60,
                system_delta % 60)
            break
        else:
            time.sleep(1)
    else:
        raise Exception("Timeout waiting for status checks: {} ".format(
            instance_id))

    print
    print "{:<40}".format(
        "Waiting for user-data, polling sqs for Ansible events:")

    (ansible_delta, task_report) = poll_sqs_ansible()
    run_summary.append(('Ansible run', ansible_delta))
    print
    print "{} longest Ansible tasks (seconds):".format(NUM_TASKS)
    for task in sorted(
            task_report, reverse=True,
            key=lambda k: k['DELTA'])[:NUM_TASKS]:
        print "{:0>3.0f} {}".format(task['DELTA'], task['TASK'])
        print "  - {}".format(task['INVOCATION'])
    print

    print "{:<40}".format("Creating AMI:"),
    ami_start = time.time()
    ami = create_ami(instance_id, run_id, run_id)
    ami_delta = time.time() - ami_start
    print "[ OK ] {:0>2.0f}:{:0>2.0f}".format(
        ami_delta / 60,
        ami_delta % 60)
    run_summary.append(('AMI Build', ami_delta))
    total_time = time.time() - start_time
    all_stages = sum(run[1] for run in run_summary)
    if total_time - all_stages > 0:
        run_summary.append(('Other', total_time - all_stages))
    run_summary.append(('Total', total_time))

    return run_summary, ami


def send_hipchat_message(message):
    #If hipchat is configured send the details to the specified room
    if args.hipchat_api_token and args.hipchat_room_id:
        import hipchat
        try:
            hipchat = hipchat.HipChat(token=args.hipchat_api_token)
            hipchat.message_room(args.hipchat_room_id, 'AbbeyNormal',
                                 message)
        except Exception as e:
            print("Hipchat messaging resulted in an error: %s." % e)

if __name__ == '__main__':

    args = parse_args()

    run_summary = []

    start_time = time.time()

    if args.vars:
        with open(args.vars) as f:
            extra_vars_yml = f.read()
            extra_vars = yaml.load(extra_vars_yml)
    else:
        extra_vars_yml = ""
        extra_vars = {}

    if args.refs:
        with open(args.refs) as f:
            git_refs_yml = f.read()
            git_refs = yaml.load(git_refs_yml)
    else:
        git_refs_yml = ""
        git_refs = {}

    if args.secure_vars_file:
        # explicit path to a single
        # secure var file
        secure_vars_file = args.secure_vars_file
    else:
        secure_vars_file = 'false'

    if args.stack_name:
        stack_name = args.stack_name
    else:
        stack_name = "{}-{}".format(args.environment, args.deployment)

    try:
        sqs = boto.sqs.connect_to_region(args.region)
        ec2 = boto.ec2.connect_to_region(args.region)
    except NoAuthHandlerFound:
        print 'You must be able to connect to sqs and ec2 to use this script'
        sys.exit(1)

    if args.blessed:
        base_ami = get_blessed_ami()
    else:
        base_ami = args.base_ami

    try:
        sqs_queue = None
        instance_id = None

        run_id = "{}-abbey-{}-{}-{}".format(
            int(time.time() * 100), args.environment, args.deployment, args.play)

        ec2_args = create_instance_args()

        if args.noop:
            print "Would have created sqs_queue with id: {}\nec2_args:".format(
                run_id)
            pprint(ec2_args)
            ami = "ami-00000"
        else:
            run_summary, ami = launch_and_configure(ec2_args)
            print
            print "Summary:\n"

            for run in run_summary:
                print "{:<30} {:0>2.0f}:{:0>5.2f}".format(
                    run[0], run[1] / 60, run[1] % 60)
            print "AMI: {}".format(ami)

            message = 'Finished baking AMI {image_id} for {environment} {deployment} {play}.'.format(
                image_id=ami,
                environment=args.environment,
                deployment=args.deployment,
                play=args.play)

            send_hipchat_message(message)
    except Exception as e:
        message = 'An error occurred building AMI for {environment} ' \
            '{deployment} {play}.  The Exception was {exception}'.format(
                environment=args.environment,
                deployment=args.deployment,
                play=args.play,
                exception=repr(e))
        send_hipchat_message(message)
    finally:
        print
        if not args.no_cleanup and not args.noop:
            if sqs_queue:
                print "Cleaning up - Removing SQS queue - {}".format(run_id)
                sqs.delete_queue(sqs_queue)
            if instance_id:
                print "Cleaning up - Terminating instance ID - {}".format(
                    instance_id)
            # Check to make sure we have an instance id.
            if instance_id:
                ec2.terminate_instances(instance_ids=[instance_id])

########NEW FILE########
__FILENAME__ = create_stack
import argparse
import boto
import yaml
from os.path import basename
from time import sleep
from pprint import pprint


FAILURE_STATES = [
    'CREATE_FAILED',
    'ROLLBACK_IN_PROGRESS',
    'ROLLBACK_FAILED',
    'ROLLBACK_COMPLETE',
    'DELETE_IN_PROGRESS',
    'DELETE_FAILED',
    'DELETE_COMPLETE',
    ]

def upload_file(file_path, bucket_name, key_name):
    """
    Upload a file to the given s3 bucket and return a template url.
    """
    conn = boto.connect_s3()
    try:
        bucket = conn.get_bucket(bucket_name)
    except boto.exception.S3ResponseError as e:
        conn.create_bucket(bucket_name)
        bucket = conn.get_bucket(bucket_name, validate=False)

    key = boto.s3.key.Key(bucket)
    key.key = key_name
    key.set_contents_from_filename(file_path)

    key.set_acl('public-read')
    url = "https://s3.amazonaws.com/{}/{}".format(bucket.name, key.name)
    print( "URL: {}".format(url))
    return url

def create_stack(stack_name, template, region='us-east-1', blocking=True,
                 temp_bucket='edx-sandbox-devops', parameters=[],
                 update=False):

    cfn = boto.connect_cloudformation()

    # Upload the template to s3
    key_pattern = 'devops/cloudformation/auto/{}_{}'
    key_name = key_pattern.format(stack_name, basename(template))
    template_url = upload_file(template, temp_bucket, key_name)

    # Reference the stack.
    try:
        if update:
            stack_id = cfn.update_stack(stack_name,
                template_url=template_url,
                capabilities=['CAPABILITY_IAM'],
                tags={'autostack':'true'},
                parameters=parameters)
        else:
            stack_id = cfn.create_stack(stack_name,
                template_url=template_url,
                capabilities=['CAPABILITY_IAM'],
                tags={'autostack':'true'},
                parameters=parameters)
    except Exception as e:
        print(e.message)
        raise e

    status = None
    while blocking:
        sleep(5)
        stack_instance = cfn.describe_stacks(stack_id)[0]
        status = stack_instance.stack_status
        print(status)
        if 'COMPLETE' in status:
            break

    if status in FAILURE_STATES:
        raise Exception('Creation Failed. Stack Status: {}, ID:{}'.format(
            status, stack_id))

    return stack_id

def cfn_params_from(filename):
    params_dict = yaml.safe_load(open(filename))
    return [ (key,value) for key,value in params_dict.items() ]

if __name__ == '__main__':
        description = 'Create a cloudformation stack from a template.'
        parser = argparse.ArgumentParser(description=description)

        msg = 'Name for the cloudformation stack.'
        parser.add_argument('-n', '--stackname', required=True, help=msg)

        msg = 'Pass this argument if we are updating an existing stack.'
        parser.add_argument('-u', '--update', action='store_true')

        msg = 'Name of the bucket to use for temporarily uploading the \
            template.'
        parser.add_argument('-b', '--bucketname', default="edx-sandbox-devops",
            help=msg)

        msg = 'The path to the cloudformation template.'
        parser.add_argument('-t', '--template', required=True, help=msg)

        msg = 'The AWS region to build this stack in.'
        parser.add_argument('-r', '--region', default='us-east-1', help=msg)

        msg = 'YAML file containing stack build parameters'
        parser.add_argument('-p', '--parameters', help=msg)

        args = parser.parse_args()
        stack_name = args.stackname
        template = args.template
        region = args.region
        bucket_name = args.bucketname
        parameters = cfn_params_from(args.parameters)
        update = args.update

        create_stack(stack_name, template, region, temp_bucket=bucket_name, parameters=parameters, update=update)
        print('Stack({}) created.'.format(stack_name))

########NEW FILE########
__FILENAME__ = db-clone
#!/usr/bin/env python
import boto
import boto.route53
import boto.route53.record
import boto.ec2.elb
import boto.rds2
import time
from argparse import ArgumentParser, RawTextHelpFormatter
import datetime
import sys
from vpcutil import rds_subnet_group_name_for_stack_name, all_stack_names
import os

description = """

   Creates a new RDS instance using restore
   from point in time using the latest available backup.
   The new db will be the same size as the original.
   The name of the db will remain the same, the master db password
   will be changed and is set on the command line.

   If stack-name is provided the RDS instance will be launched
   in the VPC that corresponds to that name.

   New db name defaults to "from-<source db name>-<human date>-<ts>"
   A new DNS entry will be created for the RDS when provided
   on the command line

"""

RDS_SIZES = [
    'db.m1.small',
    'db.m1.large',
    'db.m1.xlarge',
    'db.m2.xlarge',
    'db.m2.2xlarge',
    'db.m2.4xlarg',
]

# These are the groups for the different
# stack names that will be assigned once
# the corresponding db is cloned

SG_GROUPS = {
    'stage-edx': 'sg-d2f623b7',
}

# This group must already be created
# and allows for full access to port
# 3306 from within the vpc.
# This group is assigned temporarily
# for cleaning the db

SG_GROUPS_FULL = {
    'stage-edx': 'sg-0abf396f',
}


def parse_args(args=sys.argv[1:]):

    stack_names = all_stack_names()
    rds = boto.rds2.connect_to_region('us-east-1')
    dbs = [db['DBInstanceIdentifier']
           for db in rds.describe_db_instances()['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']]

    parser = ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
    parser.add_argument('-s', '--stack-name', choices=stack_names,
                        default=None,
                        help='Stack name for where you want this RDS instance launched')
    parser.add_argument('-t', '--type', choices=RDS_SIZES,
                        default='db.m1.small', help='RDS size to create instances of')
    parser.add_argument('-d', '--db-source', choices=dbs,
                        default=u'stage-edx', help="source db to clone")
    parser.add_argument('-p', '--password',
                        help="password for the new database", metavar="NEW PASSWORD")
    parser.add_argument('-r', '--region', default='us-east-1',
                        help="region to connect to")
    parser.add_argument('--dns',
                        help="dns entry for the new rds instance")
    parser.add_argument('--clean-wwc', action="store_true",
                        default=False,
                        help="clean the wwc db after launching it into the vpc, removing sensitive data")
    parser.add_argument('--clean-prod-grader', action="store_true",
                        default=False,
                        help="clean the prod_grader db after launching it into the vpc, removing sensitive data")
    parser.add_argument('--dump', action="store_true",
                        default=False,
                        help="create a sql dump after launching it into the vpc")
    parser.add_argument('--secret-var-file',
                        help="using a secret var file run ansible against the host to update db users")

    return parser.parse_args(args)


def wait_on_db_status(db_name, region='us-east-1', wait_on='available', aws_id=None, aws_secret=None):
    rds = boto.rds2.connect_to_region(region)
    while True:
        statuses = rds.describe_db_instances(db_name)['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']
        if len(statuses) > 1:
            raise Exception("More than one instance returned for {0}".format(db_name))
        if statuses[0]['DBInstanceStatus'] == wait_on:
            break
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(2)
    return

if __name__ == '__main__':
    args = parse_args()
    sanitize_wwc_sql_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sanitize-db-wwc.sql")
    sanitize_prod_grader_sql_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sanitize-db-prod_grader.sql")
    play_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../playbooks/edx-east")

    rds = boto.rds2.connect_to_region(args.region)
    restore_dbid = 'from-{0}-{1}-{2}'.format(args.db_source, datetime.date.today(), int(time.time()))
    restore_args = dict(
        source_db_instance_identifier=args.db_source,
        target_db_instance_identifier=restore_dbid,
        use_latest_restorable_time=True,
        db_instance_class=args.type,
    )
    if args.stack_name:
        subnet_name = rds_subnet_group_name_for_stack_name(args.stack_name)
        restore_args['db_subnet_group_name'] = subnet_name
    rds.restore_db_instance_to_point_in_time(**restore_args)
    wait_on_db_status(restore_dbid)

    db_host = rds.describe_db_instances(restore_dbid)['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['Endpoint']['Address']

    if args.password or args.stack_name:
        modify_args = dict(
            apply_immediately=True
        )
        if args.password:
            modify_args['master_user_password'] = args.password
        if args.stack_name:
            modify_args['vpc_security_group_ids'] = [SG_GROUPS[args.stack_name], SG_GROUPS_FULL[args.stack_name]]
        else:
            # dev-edx is the default security group for dbs that
            # are not in the vpc, it allows connections from the various
            # NAT boxes and from sandboxes
            modify_args['db_security_groups'] = ['dev-edx']

        # Update the db immediately
        rds.modify_db_instance(restore_dbid, **modify_args)

    if args.clean_wwc:
        # Run the mysql clean sql file
        sanitize_cmd = """mysql -u root -p{root_pass} -h{db_host} wwc < {sanitize_wwc_sql_file} """.format(
            root_pass=args.password,
            db_host=db_host,
            sanitize_wwc_sql_file=sanitize_wwc_sql_file)
        print("Running {}".format(sanitize_cmd))
        os.system(sanitize_cmd)

    if args.clean_prod_grader:
        # Run the mysql clean sql file
        sanitize_cmd = """mysql -u root -p{root_pass} -h{db_host} prod_grader < {sanitize_prod_grader_sql_file} """.format(
            root_pass=args.password,
            db_host=db_host,
            sanitize_prod_grader_sql_file=sanitize_prod_grader_sql_file)
        print("Running {}".format(sanitize_cmd))
        os.system(sanitize_cmd)

    if args.secret_var_file:
        db_cmd = """cd {play_path} && ansible-playbook -c local -i 127.0.0.1, update_edxapp_db_users.yml """ \
            """-e @{secret_var_file} -e "edxapp_db_root_user=root edxapp_db_root_pass={root_pass} """ \
            """EDXAPP_MYSQL_HOST={db_host}" """.format(
            root_pass=args.password,
            secret_var_file=args.secret_var_file,
            db_host=db_host,
            play_path=play_path)
        print("Running {}".format(db_cmd))
        os.system(db_cmd)

    if args.dns:
        dns_cmd = """cd {play_path} && ansible-playbook -c local -i 127.0.0.1, create_cname.yml """ \
            """-e "dns_zone=edx.org dns_name={dns} sandbox={db_host}" """.format(
            play_path=play_path,
            dns=args.dns,
            db_host=db_host)
        print("Running {}".format(dns_cmd))
        os.system(dns_cmd)

    if args.stack_name:
        rds.modify_db_instance(restore_dbid, vpc_security_group_ids=[SG_GROUPS[args.stack_name]])

########NEW FILE########
__FILENAME__ = vpc-tools
"""VPC Tools.

Usage:
    vpc-tools.py ssh-config (vpc <vpc_id> | stack-name <stack_name>) [(identity-file <identity_file>)] user <user> [(config-file <config_file>)] [(strict-host-check <strict_host_check>)]
    vpc-tools.py (-h --help)
    vpc-tools.py (-v --version)

Options:
    -h --help       Show this screen.
    -v --version    Show version.

"""
import boto
from docopt import docopt
from vpcutil import vpc_for_stack_name
from vpcutil import stack_name_for_vpc
from collections import defaultdict


VERSION="vpc tools 0.1"
DEFAULT_USER="ubuntu"
DEFAULT_HOST_CHECK="ask"

BASTION_CONFIG = """Host {jump_box}
    HostName {ip}
    ForwardAgent yes
    User {user}
    StrictHostKeyChecking {strict_host_check}
    {identity_line}
    """

HOST_CONFIG = """# Instance ID: {instance_id}
Host {name}
    ProxyCommand ssh {config_file} -W %h:%p {jump_box}
    HostName {ip}
    ForwardAgent yes
    User {user}
    StrictHostKeyChecking {strict_host_check}
    {identity_line}
    """

BASTION_HOST_CONFIG = """# Instance ID: {instance_id}
Host {name}
    HostName {ip}
    ForwardAgent yes
    User {user}
    StrictHostKeyChecking {strict_host_check}
    {identity_line}
    """



def dispatch(args):

    if args.get("ssh-config"):
        _ssh_config(args)

def _ssh_config(args):
    if args.get("vpc"):
      vpc_id = args.get("<vpc_id>")
      stack_name = stack_name_for_vpc(vpc_id)
    elif args.get("stack-name"):
      stack_name = args.get("<stack_name>")
      vpc_id = vpc_for_stack_name(stack_name)
    else:
      raise Exception("No vpc_id or stack_name provided.")

    vpc = boto.connect_vpc()

    identity_file = args.get("<identity_file>", None)
    if identity_file:
        identity_line = "IdentityFile {}".format(identity_file)
    else:
        identity_line = ""

    user = args.get("<user>")
    config_file = args.get("<config_file>")
    strict_host_check = args.get("<strict_host_check>")

    if not user:
      user = DEFAULT_USER

    if not strict_host_check:
      strict_host_check = DEFAULT_HOST_CHECK

    if config_file:
      config_file = "-F {}".format(config_file)
    else:
      config_file = ""

    jump_box = "{stack_name}-bastion".format(stack_name=stack_name)
    friendly = "{stack_name}-{logical_id}-{instance_number}"
    id_type_counter = defaultdict(int)

    reservations = vpc.get_all_instances(filters={'vpc-id' : vpc_id})

    for reservation in reservations:
        for instance in reservation.instances:

            if 'play' in instance.tags:
                logical_id = instance.tags['play']
            elif 'role' in instance.tags:
                # deprecated, use "play" instead
                logical_id = instance.tags['role']
            elif 'group' in instance.tags:
                logical_id = instance.tags['group']
            elif 'aws:cloudformation:logical-id' in instance.tags:
                logical_id = instance.tags['aws:cloudformation:logical-id']
            else:
                continue
            instance_number = id_type_counter[logical_id]
            id_type_counter[logical_id] += 1

            if logical_id == "BastionHost" or logical_id == 'bastion':

                print BASTION_CONFIG.format(
                    jump_box=jump_box,
                    ip=instance.ip_address,
                    user=user,
                    strict_host_check=strict_host_check,
                    identity_line=identity_line)

                print BASTION_HOST_CONFIG.format(
                    name=instance.private_ip_address,
                    ip=instance.ip_address,
                    user=user,
                    instance_id=instance.id,
                    strict_host_check=strict_host_check,
                    identity_line=identity_line)

                #duplicating for convenience with ansible
                name = friendly.format(stack_name=stack_name,
                                       logical_id=logical_id,
                                       instance_number=instance_number)

                print BASTION_HOST_CONFIG.format(
                    name=name,
                    ip=instance.ip_address,
                    user=user,
                    strict_host_check=strict_host_check,
                    instance_id=instance.id,
                    identity_line=identity_line)

            else:
                # Print host config even for the bastion box because that is how
                # ansible accesses it.
                print HOST_CONFIG.format(
                    name=instance.private_ip_address,
                    jump_box=jump_box,
                    ip=instance.private_ip_address,
                    user=user,
                    config_file=config_file,
                    strict_host_check=strict_host_check,
                    instance_id=instance.id,
                    identity_line=identity_line)

                #duplicating for convenience with ansible
                name = friendly.format(stack_name=stack_name,
                                       logical_id=logical_id,
                                       instance_number=instance_number)

                print HOST_CONFIG.format(
                    name=name,
                    jump_box=jump_box,
                    ip=instance.private_ip_address,
                    user=user,
                    config_file=config_file,
                    strict_host_check=strict_host_check,
                    instance_id=instance.id,
                    identity_line=identity_line)

if __name__ == '__main__':
    args = docopt(__doc__, version=VERSION)
    dispatch(args)

########NEW FILE########
__FILENAME__ = vpcutil
import boto
import boto.rds2
import boto.rds

CFN_TAG_KEY = 'aws:cloudformation:stack-name'

def vpc_for_stack_name(stack_name, aws_id=None, aws_secret=None):
    cfn = boto.connect_cloudformation(aws_id, aws_secret)
    resources = cfn.list_stack_resources(stack_name)
    for resource in resources:
        if resource.resource_type == 'AWS::EC2::VPC':
            return resource.physical_resource_id


def stack_name_for_vpc(vpc_name, aws_id, aws_secret):
    vpc = boto.connect_vpc(aws_id, aws_secret)
    resource = vpc.get_all_vpcs(vpc_ids=[vpc_name])[0]
    if CFN_TAG_KEY in resource.tags:
        return resource.tags[CFN_TAG_KEY]
    else:
        msg = "VPC({}) is not part of a cloudformation stack.".format(vpc_name)
        raise Exception(msg)


def rds_subnet_group_name_for_stack_name(stack_name, region='us-east-1', aws_id=None, aws_secret=None):
    # Helper function to look up a subnet group name by stack name
    rds = boto.rds2.connect_to_region(region)
    vpc = vpc_for_stack_name(stack_name)
    for group in rds.describe_db_subnet_groups()['DescribeDBSubnetGroupsResponse']['DescribeDBSubnetGroupsResult']['DBSubnetGroups']:
        if group['VpcId'] == vpc:
            return group['DBSubnetGroupName']
    return None


def all_stack_names(region='us-east-1', aws_id=None, aws_secret=None):
    vpc_conn = boto.connect_vpc(aws_id, aws_secret)
    return [vpc.tags[CFN_TAG_KEY] for vpc in vpc_conn.get_all_vpcs()
            if CFN_TAG_KEY in vpc.tags.keys()]

########NEW FILE########
__FILENAME__ = vpc_dns
#!/usr/bin/env python -u
#
# Updates DNS records for a stack
#
# Example usage:
#
#   # update route53 entries for ec2 and rds instances
#   # in the vpc with stack-name "stage-stack" and
#   # create DNS entries in the example.com hosted
#   # zone
#
#   python vpc_dns.py -s stage-stack -z example.com
#
#   # same thing but just print what will be done without
#   # making any changes
#
#   python vpc_dns.py -n -s stage-stack -z example.com
#
#   # Create a new zone "vpc.example.com", update the parent
#   # zone "example.com"
#
#   python vpc_dns.py -s stage-stack -z vpc.example.com
#

import argparse
import boto
import datetime
from vpcutil import vpc_for_stack_name
import xml.dom.minidom
import sys

# These are ELBs that we do not want to create dns entries
# for because the instances attached to them are also in
# other ELBs and we want the env-deploy-play tuple which makes
# up the dns name to be unique

ELB_BAN_LIST = [
    'Apros',
]

# If the ELB name has the key in its name these plays
# will be used for the DNS CNAME tuple.  This is used for
# commoncluster.

ELB_PLAY_MAPPINGS = {
    'RabbitMQ': 'rabbitmq',
    'Xqueue': 'xqueue',
    'Elastic': 'elasticsearch',
}


class DNSRecord():

    def __init__(self, zone, record_name, record_type,
                 record_ttl, record_values):
        self.zone = zone
        self.record_name = record_name
        self.record_type = record_type
        self.record_ttl = record_ttl
        self.record_values = record_values


def add_or_update_record(dns_records):
    """
    Creates or updates a DNS record in a hosted route53
    zone
    """
    change_set = boto.route53.record.ResourceRecordSets()
    record_names = set()

    for record in dns_records:

        status_msg = """
        record_name:   {}
        record_type:   {}
        record_ttl:    {}
        record_values: {}
                 """.format(record.record_name, record.record_type,
                            record.record_ttl, record.record_values)
        if args.noop:
            print("Would have updated DNS record:\n{}".format(status_msg))
        else:
            print("Updating DNS record:\n{}".format(status_msg))

        if record.record_name in record_names:
            print("Unable to create record for {} with value {} because one already exists!".format(
                record.record_values, record.record_name))
            sys.exit(1)
        record_names.add(record.record_name)

        zone_id = record.zone.Id.replace("/hostedzone/", "")

        records = r53.get_all_rrsets(zone_id)

        old_records = {r.name[:-1]: r for r in records}

        # If the record name already points to something.
        # Delete the existing connection. If the record has
        # the same type and name skip it.
        if record.record_name in old_records.keys():
            if record.record_name + "." == old_records[record.record_name].name and \
                    record.record_type == old_records[record.record_name].type:
                print("Record for {} already exists and is identical, skipping.\n".format(
                    record.record_name))
                continue

            if args.force:
                print("Deleting record:\n{}".format(status_msg))
                change = change_set.add_change(
                    'DELETE',
                    record.record_name,
                    record.record_type,
                    record.record_ttl)
            else:
                raise RuntimeError(
                    "DNS record exists for {} and force was not specified.".
                    format(record.record_name))

            for value in old_records[record.record_name].resource_records:
                change.add_value(value)

        change = change_set.add_change(
            'CREATE',
            record.record_name,
            record.record_type,
            record.record_ttl)

        for value in record.record_values:
            change.add_value(value)

    if args.noop:
        print("Would have submitted the following change set:\n")
    else:
        print("Submitting the following change set:\n")
    xml_doc = xml.dom.minidom.parseString(change_set.to_xml())
    print(xml_doc.toprettyxml(newl=''))  # newl='' to remove extra newlines
    if not args.noop:
        r53.change_rrsets(zone_id, change_set.to_xml())


def get_or_create_hosted_zone(zone_name):
    """
    Creates the zone and updates the parent
    with the NS information in the zone

    returns: created zone
    """

    zone = r53.get_hosted_zone_by_name(zone_name)
    parent_zone_name = ".".join(zone_name.split('.')[1:])
    parent_zone = r53.get_hosted_zone_by_name(parent_zone_name)

    if args.noop:
        if parent_zone:
            print("Would have created/updated zone: {} parent: {}".format(
                zone_name, parent_zone_name))
        else:
            print("Would have created/updated zone: {}".format(
                zone_name, parent_zone_name))
        return zone

    if not zone:
        print("zone {} does not exist, creating".format(zone_name))
        ts = datetime.datetime.utcnow().strftime('%Y-%m-%d-%H:%M:%SUTC')
        zone = r53.create_hosted_zone(
            zone_name, comment="Created by vpc_dns script - {}".format(ts))

    if parent_zone:
        print("Updating parent zone {}".format(parent_zone_name))

        dns_records = set()
        dns_records.add(DNSRecord(parent_zone, zone_name, 'NS', 900, zone.NameServers))
        add_or_update_record(dns_records)

    return zone


def get_security_group_dns(group_name):
    # stage-edx-RabbitMQELBSecurityGroup-YB8ZKIZYN1EN
    environment, deployment, sec_group, salt = group_name.split('-')
    play = sec_group.replace("ELBSecurityGroup", "").lower()
    return environment, deployment, play


def get_dns_from_instances(elb):
    for inst in elb.instances:
        try:
            instance = ec2_con.get_all_instances(
                instance_ids=[inst.id])[0].instances[0]
        except IndexError:
            print("instance {} attached to elb {}".format(inst, elb))
            sys.exit(1)
        try:
            env_tag = instance.tags['environment']
            deployment_tag = instance.tags['deployment']
            if 'play' in instance.tags:
                play_tag = instance.tags['play']
            else:
                # deprecated, for backwards compatibility
                play_tag = instance.tags['role']
            break  # only need the first instance for tag info
        except KeyError:
            print("Instance {}, attached to elb {} does not "
                  "have a tag for environment, play or deployment".format(inst, elb))
            sys.exit(1)

    return env_tag, deployment_tag, play_tag


def update_elb_rds_dns(zone):
    """
    Creates elb and rds CNAME records
    in a zone for args.stack_name.
    Uses the tags of the instances attached
    to the ELBs to create the dns name
    """

    dns_records = set()

    vpc_id = vpc_for_stack_name(args.stack_name, args.aws_id, args.aws_secret)

    if not zone and args.noop:
        # use a placeholder for zone name
        # if it doesn't exist
        zone_name = "<zone name>"
    else:
        zone_name = zone.Name[:-1]

    stack_elbs = [elb for elb in elb_con.get_all_load_balancers()
                  if elb.vpc_id == vpc_id]
    for elb in stack_elbs:
        env_tag, deployment_tag, play_tag = get_dns_from_instances(elb)

        # Override the play tag if a substring of the elb name
        # is in ELB_PLAY_MAPPINGS

        for key in ELB_PLAY_MAPPINGS.keys():
            if key in elb.name:
                play_tag = ELB_PLAY_MAPPINGS[key]
                break
        fqdn = "{}-{}-{}.{}".format(env_tag, deployment_tag, play_tag, zone_name)

        # Skip over ELBs if a substring of the ELB name is in
        # the ELB_BAN_LIST

        if any(name in elb.name for name in ELB_BAN_LIST):
            print("Skipping {} because it is on the ELB ban list".format(elb.name))
            continue

        dns_records.add(DNSRecord(zone, fqdn, 'CNAME', 600, [elb.dns_name]))

    stack_rdss = [rds for rds in rds_con.get_all_dbinstances()
                  if hasattr(rds.subnet_group, 'vpc_id') and
                  rds.subnet_group.vpc_id == vpc_id]

    # TODO the current version of the RDS API doesn't support
    # looking up RDS instance tags.  Hence, we are using the
    # env_tag and deployment_tag that was set via the loop over instances above.

    rds_endpoints = set()
    for rds in stack_rdss:
        endpoint = stack_rdss[0].endpoint[0]
        fqdn = "{}-{}-{}.{}".format(env_tag, deployment_tag, 'rds', zone_name)
        # filter out rds instances with the same endpoints (multi-AZ)
        if endpoint not in rds_endpoints:
            dns_records.add(DNSRecord(zone, fqdn, 'CNAME', 600, [endpoint]))
        rds_endpoints.add(endpoint)

    add_or_update_record(dns_records)

if __name__ == "__main__":
    description = """

    Give a cloudformation stack name, for an edx stack, setup
    DNS names for the ELBs in the stack

    DNS entries will be created with the following format

       <environment>-<deployment>-<play>.edx.org

    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--stack-name', required=True,
                        help="The name of the cloudformation stack.")
    parser.add_argument('-n', '--noop',
                        help="Don't make any changes.", action="store_true",
                        default=False)
    parser.add_argument('-z', '--zone-name', default="edx.org",
                        help="The name of the zone under which to "
                             "create the dns entries.")
    parser.add_argument('-f', '--force',
                        help="Force reuse of an existing name in a zone",
                        action="store_true", default=False)
    parser.add_argument('--aws-id', default=None,
                        help="read only aws key for fetching instance information"
                             "the account you wish add entries for")
    parser.add_argument('--aws-secret', default=None,
                        help="read only aws id for fetching instance information for"
                             "the account you wish add entries for")

    args = parser.parse_args()
    # Connect to ec2 using the provided credentials on the commandline
    ec2_con = boto.connect_ec2(args.aws_id, args.aws_secret)
    elb_con = boto.connect_elb(args.aws_id, args.aws_secret)
    rds_con = boto.connect_rds(args.aws_id, args.aws_secret)

    # Connect to route53 using the user's .boto file
    r53 = boto.connect_route53()

    zone = get_or_create_hosted_zone(args.zone_name)
    update_elb_rds_dns(zone)

########NEW FILE########
