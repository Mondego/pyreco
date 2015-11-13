__FILENAME__ = config
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging
import requests
import ConfigParser
import os.path
import anyjson as json

from daikon import exceptions

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Config(object):

    def __init__(self, arguments):
        self.arguments = arguments
        self._cluster = None
        self._host = None
        self._port = None
        self._replicas = None
        self._shards = None
        self._version = None

    def setup(self):
        ''' Setup configuration, and read config files '''

        self.config_parser = ConfigParser.ConfigParser()

        if not self.config_parser.read(
                ['/etc/daikon/daikon.conf',
                    os.path.expanduser('~/.daikon.conf'), 'daikon.conf']):
            msg = 'No config file found!'
            raise exceptions.ConfigError(msg)
        elif not self.config_parser.has_section(self.cluster()):
            msg = 'No cluster section defined for this cluster!'
            raise exceptions.ConfigError(msg)
        else:
            return self.config_parser

    def cluster(self):
        ''' Cluster configuration '''

        if self._cluster is not None:
            return self._cluster

        if hasattr(self.arguments, 'cluster') and \
                self.arguments.cluster is not None:
            self._cluster = self.arguments.cluster
        else:
            self._cluster = 'default'

        return self._cluster

    def host(self):
        ''' Host configuration '''

        if self._host is not None:
            return self._host

        if not self.config_parser.get(self.cluster(), 'host'):
            raise exceptions.ConfigError('No default host defined!')
        elif hasattr(self.arguments, 'host') and self.arguments.host:
            self._hsot = self.arguments.host
        else:
            self._host = self.config_parser.get(self.cluster(), 'host')

        return self._host

    def port(self):
        ''' Port configuration '''

        if self._port is not None:
            return self._port

        if not self.config_parser.get(self.cluster(), 'port'):
            raise exceptions.ConfigError('No default port defined!')
        elif hasattr(self.arguments, 'port') and self.arguments.port:
            self._port = self.arguments.port
        else:
            self._port = self.config_parser.get(self.cluster(), 'port')

        return self._port

    def replicas(self):
        ''' Replicas configuration '''

        if self._replicas is not None:
            return self._replicas

        if not self.config_parser.get(self.cluster(), 'replicas'):
            raise exceptions.ConfigError('No default replicas defined!')
        elif hasattr(self.arguments, 'replicas') and self.arguments.replicas:
            self._replicas = self.arguments.replicas
        else:
            self._replicas = self.config_parser.get(self.cluster(), 'replicas')

        return self._replicas

    def shards(self):
        ''' Shards configuration '''

        if self._shards is not None:
            return self._shards

        if not self.config_parser.get(self.cluster(), 'shards'):
            raise exceptions.ConfigError('No default shards defined!')
        elif hasattr(self.arguments, 'shards') and self.arguments.shards:
            self._shards = self.arguments.shards
        else:
            self._shards = self.config_parser.get(self.cluster(), 'shards')

        return self._shards

    def version(self):
        ''' Get ElasticSearch Version '''

        if self._version is not None:
            return self._version

        if self._host is None:
            self._host = self.host()

        if self._port is None:
            self._port = self.port()

        try:
            request_url = 'http://%s:%s' % (self._host, self._port)
            request = requests.get(request_url)
            request.raise_for_status()
            self._version = json.loads(request.content)[u'version'][u'number']
            return self._version
        except requests.RequestException, e:
            raise exceptions.ConfigError('Error fetching version - ' + str(e))

########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging
import requests
import anyjson as json
import urlparse

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Connection(object):
    _state = None
    _health = None

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.url = 'http://%s:%s' % (host, port)

    def get(self, path, raise_for_status=True):
        url = urlparse.urljoin(self.url, path)
        req = requests.get(url)
        if raise_for_status:
            req.raise_for_status()
        return req

    def post(self, path, data=None, raise_for_status=True):
        url = urlparse.urljoin(self.url, path)
        req = requests.post(url, data=data)
        if raise_for_status:
            req.raise_for_status()
        return req

    def delete(self, path, raise_for_status=True):
        url = urlparse.urljoin(self.url, path)
        req = requests.delete(url)
        if raise_for_status:
            req.raise_for_status()
        return req

    @property
    def health(self):
        if self._health is not None:
            return self._health

        path = '/_cluster/health?level=indices'
        health = json.loads(self.get(path).content)
        self._health = health[u'indices']
        return self._health

    @property
    def state(self):
        if self._state is not None:
            return self._state

        path = '/_cluster/state'
        state = json.loads(self.get(path).content)
        self._state = state[u'metadata'][u'indices']
        return self._state

########NEW FILE########
__FILENAME__ = display
# -*- coding: utf-8 -*-
#
#   Copyright [2012] [Patrick Ancillotti]
#   Copyright [2012] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import os
import types
import logging

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Display(object):

    def print_dict(self, output, level=0):
        for key, value in output.iteritems():
            if isinstance(value, types.DictType):
                self.print_output(key, level=level)
                self.print_dict(value, level=level + 1)
            else:
                self.print_output('%s: %s' % (key, value), level=level)

    def print_output(self, output, vars=None, level=0):
        if isinstance(output, types.ListType):
            output = os.linesep.join(output)
        elif isinstance(output, types.DictType):
            return self.print_dict(output, level=level)
        if vars is not None:
            output = output % vars
        prefix = ''
        if level > 0:
            prefix = '\t' * level
        print prefix + output

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class DaikonError(Exception):
    ''' Base Exception Class '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'ERROR: Error - %s' % (self.value)


class ConfigError(DaikonError):
    ''' Config Exception Class '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'ERROR: Configuration Error - %s' % (self.value)


class ActionIndexError(DaikonError):
    ''' Index Exception Class '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'ERROR: Index Error - %s' % (self.value)


class ActionNodeError(DaikonError):
    ''' Node Exception Class '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'ERROR: Node Error - %s' % (self.value)


class ActionClusterError(DaikonError):
    ''' Cluster Exception Class '''

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'ERROR: Cluster Error - %s' % (self.value)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import sys
import logging
from time import time

from daikon import display
from daikon import managers
from daikon import config
from daikon import connection
from daikon import exceptions
from daikon import parser

# ---------------------
# Variables
# ---------------------

VERSION = '1.50'

# ---------------------
# Logging
# ---------------------

log_format = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
log_stream = logging.StreamHandler()
log_stream.setLevel(logging.INFO)
log_stream.setFormatter(log_format)
log_stream.addFilter('daikon')

log = logging.getLogger('daikon')
log.addHandler(log_stream)

stime = time()


# ---------------------
# Main
# ---------------------

def main():
    try:
        d = display.Display()

        p = parser.Parser(VERSION)
        p.setup()
        args = p.get_results()

        conf = config.Config(args)
        conf.setup()

        conn = connection.Connection(conf.host(), conf.port())

        if hasattr(args, 'index_name'):
            action = args.index_name
            index = managers.Index(conn)

            if action == 'list':
                output = index.list(args.extended)
                d.print_output('SUCCESS: Listing Indexes')
                d.print_output(output, level=1)

            if action == 'status':
                index_name = args.index_status_indexname
                output = index.status(index_name, args.extended)
                d.print_output(output)

            if action == 'create':
                index_name = args.index_create_indexname
                shards = conf.shards()
                replicas = conf.replicas()
                output = index.create(index_name, shards, replicas)
                d.print_output('SUCCESS: Creating Index : "%s"',  output)

            if action == 'delete':
                index_name = args.index_delete_indexname
                output = index.delete(index_name)
                d.print_output('SUCCESS: Deleting Index : "%s"', output)

            if action == 'open':
                index_name = args.index_open_indexname
                output = index.open(index_name)
                d.print_output('SUCCESS: Opening Index : "%s"', output)

            if action == 'close':
                index_name = args.index_close_indexname
                output = index.close(index_name)
                d.print_output('SUCCESS: Closing Index : "%s"', output)

        elif hasattr(args, 'node_name'):
            node = managers.Node(args, d)
            if args.node_name == 'shutdown':
                node.node_shutdown(args.node_shutdown_hostname,
                        conf.port(), args.delay)
            if args.node_name == 'status':
                node.node_status(args.node_status_hostname,
                        conf.port(), args.extended)
            if args.node_name == 'list':
                node.node_list(conf.host(), conf.port(), args.extended)

        elif hasattr(args, 'cluster_name'):
            cluster = managers.Cluster(args, d)
            if args.cluster_name == 'status':
                cluster.cluster_status(conf.cluster(), conf.host(),
                        conf.port(), args.extended)
            if args.cluster_name == 'shutdown':
                cluster.cluster_shutdown(conf.cluster(), conf.host(),
                        conf.port())

        total_time = round(float(time() - stime), 3)
        d.print_output('Execution Time: "%s" seconds', total_time)
    except exceptions.ConfigError as error:
        print error
        return 1
    except (exceptions.ActionIndexError,
            exceptions.ActionNodeError,
            exceptions.ActionClusterError) as error:
        print error
        return 1
    finally:
        sys.exit()


if __name__ == '__main__':
        main()

########NEW FILE########
__FILENAME__ = cluster
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging
import requests
import urllib2
import anyjson as json

from daikon import exceptions

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Cluster(object):

    def __init__(self, arguments, d):
        self.arguments = arguments
        self.d = d

    def cluster_status(self, cluster, host, port, extended):
        try:
            request_health_url = 'http://%s:%s/_cluster/health?level=indices' \
                    % (host, port)
            request_health = requests.get(request_health_url)
            request_health.raise_for_status()

            request_state_url = 'http://%s:%s/_cluster/state' % (host, port)
            request_state = requests.get(request_state_url)
            request_state.raise_for_status()

            self.d.print_output('SUCCESS: Fetching Cluster Status : "%s"',
                                cluster)

            r_state = json.loads(request_state.content)
            r_health = json.loads(request_health.content)[u'indices']
            master_node = r_state[u'master_node']
            master_node_state = r_state[u'nodes'][master_node]

            self.d.print_output('Information:', level=1)
            self.d.print_output('Cluster Name: %s', r_state[u'cluster_name'],
                                level=2)
            self.d.print_output('Master Node: %s', r_state[u'master_node'],
                                level=2)

            if extended:
                self.d.print_output('Name: %s', master_node_state[u'name'],
                                    level=3)
                self.d.print_output('Transport Address: %s',
                                    master_node_state[u'transport_address'],
                                    level=3)

            self.d.print_output('Indices:', level=1)
            for index in r_state[u'metadata'][u'indices']:
                self.d.print_output('Name: %s', index, level=2)

                if extended:
                    index_result = r_state[u'metadata'][u'indices'][index]
                    self.d.print_output('State: %s',
                                        index_result[u'state'],
                                        level=3)
                    self.d.print_output('Replicas: %s',
                                        index_result[u'settings']
                                            [u'index.number_of_replicas'],
                                        level=3)
                    self.d.print_output('Shards: %s',
                                        index_result[u'settings']
                                            [u'index.number_of_shards'],
                                        level=3)

                    if index_result[u'state'] == 'close':
                        self.d.print_output('Status: CLOSED', level=3)
                    else:
                        self.d.print_output('Status: %s',
                                            r_health[index][u'status'],
                                            level=3)

            self.d.print_output('Nodes:', level=1)
            for node in r_state[u'nodes']:
                self.d.print_output('Node: %s', node, level=2)
                if extended:
                    self.d.print_output('Name: %s',
                                        r_state[u'nodes'][node][u'name'],
                                        level=3)
                    self.d.print_output('Transport Address: %s',
                                        r_state[u'nodes'][node]
                                            [u'transport_address'],
                                        level=3)

        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Fetching Cluster Status - %s' % (e)
            raise exceptions.ActionClusterError(msg)

    def cluster_shutdown(self, cluster, host, port):
        try:
            request_url = 'http://%s:%s/_shutdown' % (host, port)
            request = requests.post(request_url)
            request.raise_for_status()
            self.d.print_output('SUCCESS: Shutting Down Cluster : "%s"',
                                cluster)
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Shutting Down Cluster - %s' % (e)
            raise exceptions.ActionClusterError(msg)

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging
import requests
import anyjson as json
import urllib2

from daikon import exceptions

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Index(object):
    def __init__(self, connection):
        self._connection = connection

    def create(self, index_name, shards, replicas):
        try:
            data = {"settings": {"number_of_shards": shards,
                                 "number_of_replicas": replicas}}
            self._connection.post(index_name, data)
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Creating Index - %s' % (e)
            raise exceptions.ActionIndexError(msg)
        return index_name

    def delete(self, index_name):
        try:
            self._connection.delete(index_name)
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Deleting Index - %s' % (e)
            raise exceptions.ActionIndexError(msg)
        return index_name

    def open(self, index_name):
        try:
            url = '%s/_open' % index_name
            self._connection.post(url)
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Opening Index - %s' % (e)
            raise exceptions.ActionIndexError(msg)
        return index_name

    def close(self, index_name):
        try:
            url = '%s/_close' % index_name
            self._connection.post(url)
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Closing Index - %s' % (e)
            raise exceptions.ActionIndexError(msg)
        return index_name

    def status(self, index_name, extended=False):
        try:
            url = '%s/_status' % index_name
            res = json.loads(self._connection.get(url).content)
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Fetching Index Status - %s' % (e)
            raise exceptions.ActionIndexError(msg)

        output = {}
        size = {}
        doc = {}
        merge = {}

        if index_name not in res['indices']:
            output['Status'] = 'Closed'
            return {index_name: output}
        else:
            output['Status'] = 'Open'

        output['Size'] = size
        output['Documents'] = doc
        output['Merge'] = merge

        status = res['indices'][index_name]

        size['Primary'] = status['index']['primary_size']
        doc['Current'] = status['docs']['num_docs']
        merge['Total'] = status['merges']['total']

        if extended:
            size['Total'] = status['index']['size']

            doc['Max'] = status['docs']['max_doc']
            doc['Deleted'] = status['docs']['deleted_docs']

            merge['Current'] = status['merges']['current']

            shards = {}
            for shard, value in status['shards'].iteritems():
                s_data = {}
                value = value[0]
                s_data['State'] = value['routing']['state']
                s_data['Size'] = value['index']['size']

                s_docs = {}
                s_docs['Current'] = value['docs']['num_docs']
                s_docs['Max'] = value['docs']['max_doc']
                s_docs['Deleted'] = value[u'docs']['deleted_docs']

                s_data['Documents'] = s_docs
                shards['Shard %s' % shard] = s_data

            output['Shards'] = shards
        return {index_name: output}

    def list(self, extended=False):
        try:
            health = self._connection.health
            state = self._connection.state
        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Listing Indexes - %s' % (e)
            raise exceptions.ActionIndexError(msg)

        output = {}
        for index in state:
            out = {}
            if extended:
                out['state'] = state[index][u'state']

                if out['state'] == 'close':
                    out['status'] = 'closed'
                else:
                    out['status'] = health[index][u'status']

                settings = state[index]['settings']
                out['shards'] = settings['index.number_of_shards']
                out['replicas'] = settings['index.number_of_replicas']

            output[index] = out
        return output

########NEW FILE########
__FILENAME__ = node
# -*- coding: utf-8 -*-
#
#   Copyright [2011] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging
import requests
import urllib2
import anyjson as json

from daikon import exceptions

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Node(object):

    def __init__(self, arguments, d):
        self.d = d
        self.arguments = arguments

    def node_status(self, host, port, extended):
        try:
            req_url = 'http://%s:%s/_cluster/nodes/_local/stats' \
                      % (host, port)
            req = requests.get(req_url)
            req.raise_for_status()
            res = json.loads(req.content)
            self.d.print_output('SUCCESS: Fetching Index Status : "%s"', host)

            for node in res[u'nodes']:
                self.d.print_output('Status:', level=1)
                self.d.print_output('Node Status:', level=2)
                self.d.print_output('Cluster: %s',
                                    res[u'cluster_name'],
                                    level=3)
                self.d.print_output('ID: %s', node, level=3)

                res_n = res[u'nodes'][node]

                if not extended:
                    self.d.print_output('Index Status:', level=2)
                    self.d.print_output('Size: %s',
                                        res_n[u'indices'][u'store'][u'size'],
                                        level=3)

                else:
                    self.d.print_output('Name: %s', res_n[u'name'], level=3)
                    self.d.print_output('Index Status:', level=2)
                    self.d.print_output('Size: %s',
                                        res_n[u'indices'][u'store'][u'size'],
                                        level=3)
                    self.d.print_output('Get (Total): %s',
                                        res_n[u'indices'][u'get'][u'total'],
                                        level=3)
                    self.d.print_output('Get (Time): %s',
                                        res_n[u'indices'][u'get'][u'time'],
                                        level=3)
                    self.d.print_output('Searches (Total): %s',
                                        res_n[u'indices'][u'search']
                                            [u'query_total'],
                                        level=3)
                    self.d.print_output('Searches (Time): %s',
                                        res_n[u'indices'][u'search']
                                            [u'query_time'],
                                        level=3)

        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Fetching Node Status - %s' % (e)
            raise exceptions.ActionNodeError(msg)

    def node_list(self, host, port, extended):

        try:
            req_url = 'http://%s:%s/_cluster/state' % (host, port)
            req = requests.get(req_url)
            req.raise_for_status()
            res = json.loads(req.content)[u'nodes']
            self.d.print_output('SUCCESS: Fetching Node List :')

            for node in res:
                self.d.print_output('Node: %s', node, level=2)

                if extended:
                    self.d.print_output('Name: %s',
                                        res[node][u'name'],
                                        level=3)
                    self.d.print_output('Transport Address: %s',
                                        res[node][u'transport_address'],
                                        level=3)

        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Fetching Node List - %s' % (e)
            raise exceptions.ActionNodeError(msg)

    def node_shutdown(self, host, port, delay):

        try:
            req_url = ('http://%s:%s/_cluster/nodes/_local/'
                       '_shutdown?delay=%ss') % (host, port, delay)
            req = requests.post(req_url)
            req.raise_for_status()
            self.d.print_output('SUCCESS: Shutting Down Node : "%s"', host)

        except (requests.RequestException, urllib2.HTTPError), e:
            msg = 'Error Shutting Down Node - %s' % (e)
            raise exceptions.ActionNodeError(msg)

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
#
#   Copyright [2012] [Patrick Ancillotti]
#   Copyright [2011] [Jason Kölker]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# ---------------------
# Imports
# ---------------------

import logging
import argparse as arg

# ---------------------
# Logging
# ---------------------

log = logging.getLogger('daikon')


# ---------------------
# Classes
# ---------------------

class Parser(object):

    def __init__(self, version):
        self._version = version
        self._main = None

    def setup(self):
        self._main = arg.ArgumentParser(description='ElasticSearch CLI v%s' %
                                        (self._version))
        self._main.add_argument('--version', action='version',
                                version=self._version)
        self._main.add_argument('--cluster')
        self._main.add_argument('--host')
        self._main.add_argument('--port')

        main_sub = self._main.add_subparsers(title='subcommands',
                                             description='valid subcommands',
                                             help='additional help',
                                             dest='main_sub')

        # index

        index = main_sub.add_parser('index')
        index = index.add_subparsers(title='subcommands',
                                     description='valid subcommands',
                                     help='additional help',
                                     dest='index_name')

        # index create

        index_create = index.add_parser('create')
        index_create.add_argument('index_create_indexname',
                                  metavar='indexname')
        index_create.add_argument('--cluster')
        index_create.add_argument('--shards')
        index_create.add_argument('--replicas')
        index_create.add_argument('--host')
        index_create.add_argument('--port')

        # index delete

        index_delete = index.add_parser('delete')
        index_delete.add_argument('index_delete_indexname',
                                  metavar='indexname')
        index_delete.add_argument('--cluster')
        index_delete.add_argument('--host')
        index_delete.add_argument('--port')

        # index open

        index_open = index.add_parser('open')
        index_open.add_argument('index_open_indexname',
                                metavar='indexname')
        index_open.add_argument('--cluster')
        index_open.add_argument('--host')
        index_open.add_argument('--port')

        # index close

        index_close = index.add_parser('close')
        index_close.add_argument('index_close_indexname',
                                 metavar='indexname')
        index_close.add_argument('--cluster')
        index_close.add_argument('--host')
        index_close.add_argument('--port')

        # index status

        index_status = index.add_parser('status')
        index_status.add_argument('index_status_indexname',
                                  metavar='indexname')
        index_status.add_argument('--cluster')
        index_status.add_argument('--host')
        index_status.add_argument('--port')
        index_status.add_argument('--extended', action='store_true')
        index_status.add_argument('--display', choices=['extended', 'regular'])

        # index list

        index_list = index.add_parser('list')
        index_list.add_argument('--cluster')
        index_list.add_argument('--host')
        index_list.add_argument('--port')
        index_list.add_argument('--extended', action='store_true')

        # cluster

        cluster = main_sub.add_parser('cluster')
        cluster = cluster.add_subparsers(title='subcommands',
                                         description='valid subcommands',
                                         help='additional help',
                                         dest='cluster_name')

        # cluster status

        cluster_status = cluster.add_parser('status')
        cluster_status.add_argument('--cluster')
        cluster_status.add_argument('--host')
        cluster_status.add_argument('--port')
        cluster_status.add_argument('--extended', action='store_true')

        # cluster shutdown

        cluster_shutdown = cluster.add_parser('shutdown')
        cluster_shutdown.add_argument('--cluster')
        cluster_shutdown.add_argument('--host')
        cluster_shutdown.add_argument('--port')

        # node

        node = main_sub.add_parser('node')
        node = node.add_subparsers(title='subcommands',
                                   description='valid subcommands',
                                   help='additional help',
                                   dest='node_name')

        # node list

        node_list = node.add_parser('list')
        node_list.add_argument('--cluster')
        node_list.add_argument('--host')
        node_list.add_argument('--port')
        node_list.add_argument('--extended', action='store_true')

        # node status

        node_status = node.add_parser('status')
        node_status.add_argument('node_status_hostname',
                                 metavar='hostname')
        node_status.add_argument('--cluster')
        node_status.add_argument('--port')
        node_status.add_argument('--extended', action='store_true')

        # node shutdown

        node_shutdown = node.add_parser('shutdown')
        node_shutdown.add_argument('node_shutdown_hostname',
                                   metavar='hostname')
        node_shutdown.add_argument('--delay', default=0)
        node_shutdown.add_argument('--port')
        node_shutdown.add_argument('--cluster')

    def get_results(self):
        return self._main.parse_args()

########NEW FILE########
