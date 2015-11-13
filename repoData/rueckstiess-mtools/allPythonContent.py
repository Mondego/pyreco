__FILENAME__ = mgenerate
#!/usr/bin/env python

import json
import bson
import sys
import inspect 
from multiprocessing import Process, cpu_count

try:
    try:
        from pymongo import MongoClient as Connection
    except ImportError:
        from pymongo import Connection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")


import mtools.mgenerate.operators as operators
from mtools.util.cmdlinetool import BaseCmdLineTool


class InsertProcess(Process):

    def __init__(self, number, template, collection, stdout):
        Process.__init__(self)
        self.number = number
        self.template = template
        self.collection = collection
        self.stdout = stdout

        # add all operators classes from the operators module, pass in _decode method
        self.operators = [c[1](self._decode) for c in inspect.getmembers(operators, inspect.isclass)]
        
        self.string_operators = {}
        self.dict_operators = {}

        # separate into key and value operators
        for o in self.operators:
            if o.string_format:
                for name in o.names:
                    self.string_operators[name] = o
            if o.dict_format:
                for name in o.names:
                    self.dict_operators[name] = o

    def run(self):
        batch = []
        batchsize = 0

        for n in xrange(self.number):
            # decode the template
            doc = self._decode(self.template)

            if self.stdout:
                print doc
            else:
                batch.append(doc)
                batchsize += self.bsonsize(doc)

                if n % 1000 == 0 or batchsize >= 1000000:
                    self.collection.insert(batch)
                    batch = []
                    batchsize = 0

        if not self.stdout:
            if batch:
                self.collection.insert(batch)

    
    def bsonsize(self, doc):
        return len(bson.BSON.encode(doc))


    def _decode_operator(self, data):
        if isinstance(data, str):
            # string-format operator
            return self._decode(self.string_operators[data]())

        # dict-format operators should only ever have one key
        assert len(data.keys()) == 1
        key = data.keys()[0]
        value = data[key]
        # call operator with parameters (which will recursively evaluate sub-documents) and return result
        return self._decode(self.dict_operators[key](value))


    def _decode_list(self, data):
        rv = []
        for item in data:
            item = self._decode(item)
            if item != "$missing":
                rv.append(item)
        return rv


    def _decode_dict(self, data):
        rv = {}
        for key, value in data.iteritems():
            key = self._decode(key)
            value = self._decode(value)
            if value != "$missing":
                rv[key] = value
        return rv


    def _decode(self, data):

        # if dict, check if it's a dict-format command
        if isinstance(data, dict): 
            if data.keys()[0] in self.dict_operators:
                return self._decode_operator(data)
            else:
                return self._decode_dict(data)

        # decode as list
        if isinstance(data, list):
            return self._decode_list(data)

        # if it's a unicode string, encode as utf-8
        if isinstance(data, unicode):
            data = data.encode('utf-8')

        # decode string-format commands
        if isinstance(data, str) and data != "$missing" and data in self.string_operators:
            return self._decode_operator(data)

        # everything else, just return the data as is
        return data



class MGeneratorTool(BaseCmdLineTool):

    def __init__(self):
        BaseCmdLineTool.__init__(self)
        
        self.argparser.description = 'Script to generate pseudo-random data based on template documents.'
        
        self.argparser.add_argument('template', action='store', help='template for data generation, JSON or file')
        self.argparser.add_argument('--number', '-n', action='store', type=int, metavar='NUM', default=1, help='number of documents to insert.')
        self.argparser.add_argument('--host', action='store', default='localhost', help='mongod/s host to import data, default=localhost')
        self.argparser.add_argument('--port', action='store', default=27017, type=int, help='mongod/s port to import data, default=27017')
        self.argparser.add_argument('--database', '-d', action='store', metavar='D', default='test', help='database D to insert data, default=test')
        self.argparser.add_argument('--collection', '-c', action='store', metavar='C', default='mgendata', help='collection C to import data, default=mgendata')
        self.argparser.add_argument('--drop', action='store_true', default=False, help='drop collection before inserting data')
        self.argparser.add_argument('--stdout', action='store_true', default=False, help='prints data to stdout instead of inserting to mongod/s instance.')
        self.argparser.add_argument('--write-concern', '-w', action='store', metavar="W", default=1, help='write concern for inserts, default=1')


    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments)

        if self.args['template'].startswith('{'):
            # not a file
            try:
                template = json.loads(self.args['template'])
            except ValueError as e:
                raise SystemExit("can't parse template: %s" % e)
        else:
            try:
                f = open(self.args['template'])
            except IOError as e:
                raise SystemExit("can't open file %s: %s" % (self.args['template'], e))

            try:
                template = json.load(f)
            except ValueError as e:
                raise SystemExit("can't parse template in %s: %s" % (self.args['template'], e))


        if not self.args['stdout']:        
            mc = Connection(host=self.args['host'], port=self.args['port'], w=self.args['write_concern'])        
            col = mc[self.args['database']][self.args['collection']]
            if self.args['drop']:
                col.drop()

        # divide work over number of cores
        num_cores = 1 if self.args['stdout'] else cpu_count()
        num_list = [self.args['number'] // num_cores] * num_cores
        num_list[0] += self.args['number'] % num_cores

        processes = []

        for n in num_list:
            p = InsertProcess(n, template, col, self.args['stdout'])
            p.start()
            processes.append(p)

        for p in processes:
            p.join()



if __name__ == '__main__':
    tool = MGeneratorTool()
    tool.run()

########NEW FILE########
__FILENAME__ = operators
from bson import ObjectId
from mtools.util import OrderedDict

from random import choice, random, randint

from datetime import datetime
from dateutil import parser

import time
import string


class BaseOperator(object):
    names = []
    dict_format = False
    string_format = False
    defaults = OrderedDict()

    def __init__(self, decode_method):
        self._decode = decode_method


    def _parse_options(self, options={}):
        parsed = self.defaults.copy()

        if isinstance(options, list):
            parsed.update( zip(self.defaults.keys(), options) )

        elif isinstance(options, dict):
            parsed.update( options )

        for k,v in parsed.iteritems():
            if isinstance(v, unicode):
                parsed[k] = v.encode('utf-8')
        return parsed



class ObjectIdOperator(BaseOperator):

    names = ['$objectid', '$oid']
    string_format = True

    def __call__(self, options=None):
        self._parse_options(options)
        return ObjectId()


class NumberOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$number', '$num']
    defaults = OrderedDict([ ('min', 0), ('max', 100) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max first
        minval = self._decode(options['min'])
        maxval = self._decode(options['max'])
        assert minval <= maxval

        return randint(minval, maxval)



class FloatOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$float']
    defaults = OrderedDict([ ('min', 0.0), ('max', 1.0) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max first
        minval = self._decode(options['min'])
        maxval = self._decode(options['max'])
        assert minval <= maxval

        val = random() * (maxval - minval) + minval
        return val



class IncOperator(BaseOperator):

    dict_format = False
    string_format = True
    names = ['$inc']
    value = -1

    def __call__(self, options=None):
        options = self._parse_options(options)

        self.value += 1
        return self.value


class StringOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$string', '$str']
    defaults = OrderedDict([ ('length', 10), ('mask', None) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max first
        length = self._decode(options['length'])
        mask = self._decode(options['mask'])

        if mask == None:
            mask = '.' * length

        assert length > 0
        result = ''.join( choice(string.ascii_letters + string.digits) for i in xrange(length) )

        return result


class MissingOperator(BaseOperator):

    dict_format = True
    string_format = True

    names = ['$missing']
    defaults = OrderedDict([ ('percent', 100), ('ifnot', None) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate percent
        percent = self._decode(options['percent'])

        if randint(1,100) <= percent:
            return '$missing'
        else:
            # ifnot is not yet evaluated, leave that up to another operator
            return options['ifnot']


class ChooseOperator(BaseOperator):

    dict_format = True
    names = ['$choose']
    defaults = OrderedDict([ ('from', []), ('weights', None) ])

    def __call__(self, options=None):
        # options can be arbitrary long list, store as "from" in options dictionary
        if isinstance(options, list):
            options = {'from': options}

        options = self._parse_options(options)

        # decode ratio
        weights = self._decode(options['weights'])
        if not weights:
            # pick one choice, uniformly distributed, but don't evaluate yet
            return choice(options['from'])
        else:
            assert len(weights) == len(options['from'])
            
            total_weight = 0
            acc_weight_items = []
            for item, weight in zip(options['from'], weights):
                total_weight += weight
                acc_weight_items.append( (total_weight, item) )
            
            pick = random() * total_weight
            for weight, item in acc_weight_items:
                if weight >= pick:
                    return item



class ArrayOperator(BaseOperator):

    dict_format = True
    names = ['$array']
    defaults = OrderedDict([ ('of', None), ('number', 10) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate number
        number = self._decode(options['number'])

        # build array of 'of' elements, but don't evaluate them yet
        return [ options['of'] ] * number


class DateTimeOperator(BaseOperator):

    dict_format = True
    string_format = True

    names = ['$datetime', '$date']
    defaults = OrderedDict([ ('min', 0), ('max', int(time.time())) ])


    def _parse_dt(self, input):
        """ parse input, either int (epoch) or date string (use dateutil parser). """
        if isinstance(input, str):
            # string needs conversion, try parsing with dateutil's parser
            try:
                dt = parser.parse(input)
            except Exception as e:
                raise SystemExit("can't parse date/time format for %s." % input)

            td = dt - datetime.utcfromtimestamp(0)
            return int((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6)
        else:
            return int(input)


    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max and convert time formats to epochs
        mintime = self._parse_dt(self._decode(options['min']))
        maxtime = self._parse_dt(self._decode(options['max']))

        # generate random epoch number
        epoch = randint(mintime, maxtime)
        return datetime.fromtimestamp(epoch)



########NEW FILE########
__FILENAME__ = mlaunch
#!/usr/bin/env python

import Queue
import argparse
import subprocess
import threading
import os, time, sys, re
import socket
import json
import re
import warnings
import psutil
import signal

from collections import defaultdict
from operator import itemgetter

from mtools.util.cmdlinetool import BaseCmdLineTool
from mtools.util.print_table import print_table
from mtools.version import __version__

try:
    try:
        from pymongo import MongoClient as Connection
        from pymongo import MongoReplicaSetClient as ReplicaSetConnection
    except ImportError:
        from pymongo import Connection
        from pymongo import ReplicaSetConnection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")


def wait_for_host(port, interval=1, timeout=30, to_start=True, queue=None):
    """ Ping a mongos or mongod every `interval` seconds until it responds, or `timeout` seconds have passed. If `to_start`
        is set to False, will wait for the node to shut down instead. This function can be called as a separate thread.

        If queue is provided, it will place the results in the message queue and return, otherwise it will just return the result
        directly.
    """
    host = 'localhost:%i'%port
    startTime = time.time()
    while True:
        if (time.time() - startTime) > timeout:
            if queue:
                queue.put_nowait((port, False))
            return False
        try:
            # make connection and ping host
            con = Connection(host)
            if not con.alive():
                raise Exception
            if to_start:
                if queue:
                    queue.put_nowait((port, True))
                return True
            else:
                time.sleep(interval)
        except Exception as e:
            if to_start:
                time.sleep(interval)
            else:
                if queue:
                    queue.put_nowait((port, True))
                return True



def shutdown_host(port, username=None, password=None, authdb=None):
    """ send the shutdown command to a mongod or mongos on given port. This function can be called as a separate thread. """
    host = 'localhost:%i'%port
    try:
        mc = Connection(host)
        try:
            if username and password and authdb:
                if authdb != "admin":
                    raise RuntimeError("given username/password is not for admin database")
                else:
                    try:
                        mc.admin.authenticate(name=username, password=password)
                    except OperationFailure:
                        # perhaps auth is not required
                        pass

            mc.admin.command('shutdown', force=True)
        except AutoReconnect:
            pass
    except ConnectionFailure:
        pass
    else:
        mc.close()


class MLaunchTool(BaseCmdLineTool):

    def __init__(self):
        BaseCmdLineTool.__init__(self)

        self.hostname = socket.gethostname()

        # arguments
        self.args = None

        # startup parameters for each port
        self.startup_info = {}

        # data structures for the discovery feature
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}

        # config docs for replica sets (key is replica set name)
        self.config_docs = {}

        # shard connection strings
        self.shard_connection_str = []


    def run(self, arguments=None):
        """ This is the main run method, called for all sub-commands and parameters.
            It sets up argument parsing, then calls the sub-command method with the same name.
        """

        # set up argument parsing in run, so that subsequent calls to run can call different sub-commands
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('--version', action='version', version="mtools version %s" % __version__)
        self.argparser.add_argument('--no-progressbar', action='store_true', default=False, help='disables progress bar')


        self.argparser.description = 'script to launch MongoDB stand-alone servers, replica sets and shards.'

        # make sure init is default command even when specifying arguments directly
        if arguments and arguments.startswith('-'):
            arguments = 'init ' + arguments
        
        # default sub-command is `init` if none provided
        elif len(sys.argv) > 1 and sys.argv[1].startswith('-') and sys.argv[1] not in ['-h', '--help', '--version']:
            sys.argv = sys.argv[0:1] + ['init'] + sys.argv[1:]

        # create command sub-parsers
        subparsers = self.argparser.add_subparsers(dest='command')
        self.argparser._action_groups[0].title = 'commands'
        self.argparser._action_groups[0].description = 'init is the default command and can be omitted. To get help on individual commands, run mlaunch <command> --help'
        
        # init command 
        init_parser = subparsers.add_parser('init', help='initialize a new MongoDB environment and start stand-alone instances, replica sets, or sharded clusters.',
            description='initialize a new MongoDB environment and start stand-alone instances, replica sets, or sharded clusters')

        # either single or replica set
        me_group = init_parser.add_mutually_exclusive_group(required=True)
        me_group.add_argument('--single', action='store_true', help='creates a single stand-alone mongod instance')
        me_group.add_argument('--replicaset', action='store_true', help='creates replica set with several mongod instances')

        # replica set arguments
        init_parser.add_argument('--nodes', action='store', metavar='NUM', type=int, default=3, help='adds NUM data nodes to replica set (requires --replicaset, default=3)')
        init_parser.add_argument('--arbiter', action='store_true', default=False, help='adds arbiter to replica set (requires --replicaset)')
        init_parser.add_argument('--name', action='store', metavar='NAME', default='replset', help='name for replica set (default=replset)')
        
        # sharded clusters
        init_parser.add_argument('--sharded', action='store', nargs='+', metavar='N', help='creates a sharded setup consisting of several singles or replica sets. Provide either list of shard names or number of shards.')
        init_parser.add_argument('--config', action='store', default=1, type=int, metavar='NUM', choices=[1, 3], help='adds NUM config servers to sharded setup (requires --sharded, NUM must be 1 or 3, default=1)')
        init_parser.add_argument('--mongos', action='store', default=1, type=int, metavar='NUM', help='starts NUM mongos processes (requires --sharded, default=1)')

        # verbose, port, binary path
        init_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')
        init_parser.add_argument('--port', action='store', type=int, default=27017, help='port for mongod, start of port range in case of replica set or shards (default=27017)')
        init_parser.add_argument('--binarypath', action='store', default=None, metavar='PATH', help='search for mongod/s binaries in the specified PATH.')
        init_parser.add_argument('--dir', action='store', default='./data', help='base directory to create db and log paths (default=./data/)')

        # authentication, users, roles
        self._default_auth_roles = ['dbAdminAnyDatabase', 'readWriteAnyDatabase', 'userAdminAnyDatabase', 'clusterAdmin']
        init_parser.add_argument('--auth', action='store_true', default=False, help='enable authentication and create a key file and admin user (default=user/password)')
        init_parser.add_argument('--username', action='store', type=str, default='user', help='username to add (requires --auth, default=user)')
        init_parser.add_argument('--password', action='store', type=str, default='password', help='password for given username (requires --auth, default=password)')
        init_parser.add_argument('--auth-db', action='store', type=str, default='admin', metavar='DB', help='database where user will be added (requires --auth, default=admin)')
        init_parser.add_argument('--auth-roles', action='store', default=self._default_auth_roles, metavar='ROLE', nargs='*', help='admin user''s privilege roles; note that the clusterAdmin role is required to run the stop command (requires --auth, default="%s")' % ' '.join(self._default_auth_roles))

        # start command
        start_parser = subparsers.add_parser('start', help='starts existing MongoDB instances. Example: "mlaunch start config" will start all config servers.', 
            description='starts existing MongoDB instances. Example: "mlaunch start config" will start all config servers.')
        start_parser.add_argument('tags', metavar='TAG', action='store', nargs='*', default=[], help='without tags, all non-running nodes will be restarted. Provide additional tags to narrow down the set of nodes to start.')
        start_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')
        start_parser.add_argument('--dir', action='store', default='./data', help='base directory to start nodes (default=./data/)')
        start_parser.add_argument('--binarypath', action='store', default=None, metavar='PATH', help='search for mongod/s binaries in the specified PATH.')

        # stop command
        stop_parser = subparsers.add_parser('stop', help='stops running MongoDB instances. Example: "mlaunch stop shard 2 secondary" will stop all secondary nodes of shard 2.',
            description='stops running MongoDB instances with the shutdown command. Example: "mlaunch stop shard 2 secondary" will stop all secondary nodes of shard 2.')
        stop_parser.add_argument('tags', metavar='TAG', action='store', nargs='*', default=[], help='without tags, all running nodes will be stopped. Provide additional tags to narrow down the set of nodes to stop.')
        stop_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')
        stop_parser.add_argument('--dir', action='store', default='./data', help='base directory to stop nodes (default=./data/)')
        
        # list command
        list_parser = subparsers.add_parser('list', help='list MongoDB instances of this environment.',
            description='list MongoDB instances of this environment.')
        list_parser.add_argument('--dir', action='store', default='./data', help='base directory to list nodes (default=./data/)')
        list_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')

        # list command
        kill_parser = subparsers.add_parser('kill', help='kills (or sends another signal to) MongoDB instances of this environment.',
            description='kills (or sends another signal to) MongoDB instances of this environment.')
        kill_parser.add_argument('tags', metavar='TAG', action='store', nargs='*', default=[], help='without tags, all running nodes will be killed. Provide additional tags to narrow down the set of nodes to kill.')
        kill_parser.add_argument('--dir', action='store', default='./data', help='base directory to kill nodes (default=./data/)')
        kill_parser.add_argument('--signal', action='store', default=15, help='signal to send to processes, default=15 (SIGTERM)')
        kill_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')

        # argparser is set up, now call base class run()
        BaseCmdLineTool.run(self, arguments, get_unknowns=True)

        # conditions on argument combinations
        if self.args['command'] == 'init' and 'single' in self.args and self.args['single']:
            if self.args['arbiter']:
                self.argparser.error("can't specify --arbiter for single nodes.")


        # replace path with absolute path, but store relative path as well
        self.relative_dir = self.args['dir']
        self.dir = os.path.abspath(self.args['dir'])
        self.args['dir'] = self.dir

        # branch out in sub-commands
        getattr(self, self.args['command'])()


    # -- below are the main commands: init, start, stop, list

    def init(self):
        """ sub-command init. Branches out to sharded, replicaset or single node methods. """
        
        # check for existing environment. Only allow subsequent 'mlaunch init' if they are identical.
        if self._load_parameters():
            if self.loaded_args != self.args:
                raise SystemExit('A different environment already exists at %s.' % self.dir)
            first_init = False
        else:
            first_init = True

        # check if authentication is enabled, make key file       
        if self.args['auth'] and first_init:
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
            os.system('openssl rand -base64 753 > %s/keyfile'%self.dir)
            os.system('chmod 600 %s/keyfile'%self.dir)

        # construct startup strings
        self._construct_cmdlines()

        # if not all ports are free, complain and suggest alternatives.
        all_ports = self.get_tagged(['all'])
        ports_avail = self.wait_for(all_ports, 1, 1, to_start=False)

        if not all(map(itemgetter(1), ports_avail)):
            dir_addon = ' --dir %s'%self.relative_dir if self.relative_dir != './data' else ''
            errmsg = '\nThe following ports are not available: %s\n\n' % ', '.join( [ str(p[0]) for p in ports_avail if not p[1] ] )
            errmsg += " * If you want to restart nodes from this environment, use 'mlaunch start%s' instead.\n" % dir_addon
            errmsg += " * If the ports are used by a different mlaunch environment, stop those first with 'mlaunch stop --dir <env>'.\n"
            errmsg += " * You can also specify a different port range with an additional '--port <startport>'\n"
            raise SystemExit(errmsg)

        if self.args['sharded']:
            shard_names = self._get_shard_names(self.args)

            # start mongod (shard and config) nodes and wait
            nodes = self.get_tagged(['mongod', 'down'])
            self._start_on_ports(nodes, wait=True)

            # initiate replica sets if init is called for the first time
            if first_init:
                for shard in shard_names:
                    # initiate replica set on first member
                    members = sorted(self.get_tagged([shard]))
                    self._initiate_replset(members[0], shard)

            # add mongos
            mongos = sorted(self.get_tagged(['mongos', 'down']))
            self._start_on_ports(mongos, wait=True)

            if first_init:
                # add shards
                mongos = sorted(self.get_tagged(['mongos']))
                con = Connection('localhost:%i'%mongos[0])

                shards_to_add = len(self.shard_connection_str)
                nshards = con['config']['shards'].count()
                if nshards < shards_to_add:
                    if self.args['replicaset']:
                        print "adding shards. can take up to 30 seconds..."
                    else:
                        print "adding shards."

                while True:
                    try:
                        nshards = con['config']['shards'].count()
                    except:
                        nshards = 0
                    if nshards >= shards_to_add:
                        break

                    for conn_str in self.shard_connection_str:
                        try:
                            res = con['admin'].command({'addShard': conn_str})
                        except Exception as e:
                            if self.args['verbose']:
                                print e, ', will retry in a moment.'
                            continue

                        if res['ok']:
                            if self.args['verbose']:
                                print "shard %s added successfully"%conn_str
                                self.shard_connection_str.remove(conn_str)
                                break
                        else:
                            if self.args['verbose']:
                                print res, '- will retry'

                    time.sleep(1)

        
        elif self.args['single']:
            # just start node
            nodes = self.get_tagged(['single', 'down'])
            self._start_on_ports(nodes, wait=False)

        
        elif self.args['replicaset']:
            # start nodes and wait
            nodes = sorted(self.get_tagged(['mongod', 'down']))
            self._start_on_ports(nodes, wait=True)

            # initiate replica set
            if first_init:
                self._initiate_replset(nodes[0], self.args['name'])


        # wait for all nodes to be running
        nodes = self.get_tagged(['all'])
        self.wait_for(nodes)

        # now that nodes are running, add admin user if authentication enabled
        if self.args['auth'] and first_init:
            self.discover()
            nodes = []

            if self.args['sharded']:
                nodes = self.get_tagged(['mongos', 'running'])
            elif self.args['single']:
                nodes = self.get_tagged(['single', 'running'])
            elif self.args['replicaset']:
                print "waiting for primary to add a user."
                if self._wait_for_primary():
                    nodes = self.get_tagged(['primary', 'running'])
                else:
                    raise RuntimeError("failed to find a primary, so adding admin user isn't possible")

            if not nodes:
                raise RuntimeError("can't connect to server, so adding admin user isn't possible")

            if "clusterAdmin" not in self.args['auth_roles']:
                warnings.warn("the stop command will not work with auth if the user does not have the clusterAdmin role")

            self._add_user(sorted(nodes)[0], name=self.args['username'], password=self.args['password'], 
                database=self.args['auth_db'], roles=self.args['auth_roles'])

            if self.args['verbose']:
                print "added user %s on %s database" % (self.args['username'], self.args['auth_db'])

        
        # in sharded env, if --mongos 0, kill the dummy mongos
        if self.args['sharded'] and self.args['mongos'] == 0:
            port = self.args['port']
            print "shutting down temporary mongos on localhost:%s" % port
            username = self.args['username'] if self.args['auth'] else None
            password = self.args['password'] if self.args['auth'] else None
            authdb = self.args['auth_db'] if self.args['auth'] else None
            shutdown_host(port, username, password, authdb)


        # write out parameters
        if self.args['verbose']:
            print "writing .mlaunch_startup file."
        self._store_parameters()

        # discover again, to get up-to-date info
        self.discover()

        if self.args['verbose']:
            print "done."


    def stop(self):
        """ sub-command stop. This method will parse the list of tags and stop the matching nodes.
            Each tag has a set of nodes associated with it, and only the nodes matching all tags (intersection)
            will be shut down.
        """
        self.discover()

        matches = self._get_ports_from_args(self.args, 'running')
        if len(matches) == 0:
            raise SystemExit('no nodes stopped.')

        for port in matches:
            if self.args['verbose']:
                print "shutting down localhost:%s" % port

            username = self.loaded_args['username'] if self.loaded_args['auth'] else None
            password = self.loaded_args['password'] if self.loaded_args['auth'] else None
            authdb = self.loaded_args['auth_db'] if self.loaded_args['auth'] else None
            shutdown_host(port, username, password, authdb)

        # wait until nodes are all shut down
        self.wait_for(matches, to_start=False)
        print "%i node%s stopped." % (len(matches), '' if len(matches) == 1 else 's')

        # there is a very brief period in which nodes are not reachable anymore, but the
        # port is not torn down fully yet and an immediate start command would fail. This 
        # very short sleep prevents that case, and it is practically not noticable by users
        time.sleep(0.1)

        # refresh discover
        self.discover()


    def start(self):
        """ sub-command start. """
        self.discover()

        # startup_info only gets loaded from protocol version 2 on, check if it's loaded
        if not self.startup_info:
            # hack to make environment startable with older protocol versions < 2: try to start nodes via init if all nodes are down
            if len(self.get_tagged(['down'])) == len(self.get_tagged(['all'])):
                self.args = self.loaded_args
                print "upgrading mlaunch environment meta-data."
                return self.init() 
            else:
                raise SystemExit("These nodes were created with an older version of mlaunch (v1.1.1 or below). To upgrade this environment and make use of the start/stop/list commands, stop all nodes manually, then run 'mlaunch start' again. You only have to do this once.")

        
        # if new unknown_args are present, compare them with loaded ones (here we can be certain of protocol v2+)
        if self.args['binarypath'] != None or (self.unknown_args and set(self.unknown_args) != set(self.loaded_unknown_args)):

            # store current args, use self.args from the file (self.loaded_args)
            start_args = self.args
            self.args = self.loaded_args

            self.args['binarypath'] = start_args['binarypath']
            # construct new startup strings with updated unknown args. They are for this start only and 
            # will not be persisted in the .mlaunch_startup file
            self._construct_cmdlines()

            # reset to original args for this start command
            self.args = start_args

        matches = self._get_ports_from_args(self.args, 'down')
        if len(matches) == 0:
            raise SystemExit('no nodes started.')

        # start mongod and config servers first
        mongod_matches = self.get_tagged(['mongod'])
        mongod_matches = mongod_matches.union(self.get_tagged(['config']))
        mongod_matches = mongod_matches.intersection(matches)
        self._start_on_ports(mongod_matches, wait=True)

        # now start mongos
        mongos_matches = self.get_tagged(['mongos']).intersection(matches)
        self._start_on_ports(mongos_matches)

        # wait for all matched nodes to be running
        self.wait_for(matches)

        # refresh discover
        self.discover()


    def list(self):
        """ sub-command list. Takes no further parameters. Will discover the current configuration and
            print a table of all the nodes with status and port.
        """
        self.discover()
        print_docs = []

        # mongos
        for node in sorted(self.get_tagged(['mongos'])):
            doc = {'process':'mongos', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'}
            print_docs.append( doc )
        
        if len(self.get_tagged(['mongos'])) > 0:
            print_docs.append( None )

        # configs
        for node in sorted(self.get_tagged(['config'])):
            doc = {'process':'config server', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'}
            print_docs.append( doc )
        
        if len(self.get_tagged(['config'])) > 0:
            print_docs.append( None )

        # mongod
        for shard in self._get_shard_names(self.loaded_args):
            tags = []
            replicaset = 'replicaset' in self.loaded_args and self.loaded_args['replicaset']
            padding = ''

            if shard:
                print_docs.append(shard)
                tags.append(shard)
                padding = '    '

            if replicaset:
                # primary
                primary = self.get_tagged(tags + ['primary', 'running'])
                if len(primary) > 0:
                    node = list(primary)[0]
                    print_docs.append( {'process':padding+'primary', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )
                
                # secondaries
                secondaries = self.get_tagged(tags + ['secondary', 'running'])
                for node in sorted(secondaries):
                    print_docs.append( {'process':padding+'secondary', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )
                
                # data-bearing nodes that are down or not in the replica set yet
                mongods = self.get_tagged(tags + ['mongod'])
                arbiters = self.get_tagged(tags + ['arbiter'])

                nodes = sorted(mongods - primary - secondaries - arbiters)
                for node in nodes:
                    print_docs.append( {'process':padding+'mongod', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'})

                # arbiters
                for node in arbiters:
                    print_docs.append( {'process':padding+'arbiter', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )

            else:
                nodes = self.get_tagged(tags + ['mongod'])
                if len(nodes) > 0:
                    node = nodes.pop()
                    print_docs.append( {'process':padding+'single', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )
            if shard:
                print_docs.append(None)


        if self.args['verbose']:
            # print tags as well
            for doc in filter(lambda x: type(x) == dict, print_docs):               
                tags = self.get_tags_of_port(doc['port'])
                doc['tags'] = ', '.join(tags)

        print_docs.append( None )   
        print         
        print_table(print_docs)


    def kill(self):
        self.discover()

        # get matching tags, can only send signals to running nodes
        matches = self._get_ports_from_args(self.args, 'running')
        processes = self._get_processes()

        # convert signal to int
        sig = self.args['signal']
        if type(sig) == int:
            pass
        elif isinstance(sig, str):
            try:
                sig = int(sig)
            except ValueError as e:
                try:
                    sig = getattr(signal, sig)
                except AttributeError as e:
                    raise SystemExit("can't parse signal '%s', use integer or signal name (SIGxxx)." % sig)

        for port in processes:
            # only send signal to matching processes
            if port in matches:
                p = processes[port]
                p.send_signal(sig)
                if self.args['verbose']:
                    print " %s on port %i, pid=%i" % (p.name, port, p.pid)

        print "sent signal %s to %i process%s." % (sig, len(matches), '' if len(matches) == 1 else 'es')

        # there is a very brief period in which nodes are not reachable anymore, but the
        # port is not torn down fully yet and an immediate start command would fail. This 
        # very short sleep prevents that case, and it is practically not noticable by users
        time.sleep(0.1)

        # refresh discover
        self.discover()

    
    # --- below are api helper methods, can be called after creating an MLaunchTool() object


    def discover(self):
        """ This method will go out to each of the processes and get their state. It builds the
            self.cluster_tree, self.cluster_tags, self.cluster_running data structures, needed
            for sub-commands start, stop, list.
        """
        # need self.args['command'] so fail if it's not available
        if not self.args or not 'command' in self.args or not self.args['command']:
            return

        # load .mlaunch_startup file for start, stop, list, use current parameters for init
        if self.args['command'] == 'init':
            self.loaded_args, self.loaded_unknown_args = self.args, self.unknown_args
        else:
            if not self._load_parameters():
                raise SystemExit("can't read %s/.mlaunch_startup, use 'mlaunch init ...' first." % self.dir)

        # reset cluster_* variables
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}
        
        # get shard names
        shard_names = self._get_shard_names(self.loaded_args)

        # some shortcut variables
        is_sharded = 'sharded' in self.loaded_args and self.loaded_args['sharded'] != None
        is_replicaset = 'replicaset' in self.loaded_args and self.loaded_args['replicaset']
        is_single = 'single' in self.loaded_args and self.loaded_args['single']
        has_arbiter = 'arbiter' in self.loaded_args and self.loaded_args['arbiter']

        # determine number of nodes to inspect
        if is_sharded:
            num_config = self.loaded_args['config']
            # at least one temp. mongos for adding shards, will be killed later on
            num_mongos = max(1, self.loaded_args['mongos'])
            num_shards = len(shard_names)
        else:
            num_shards = 1
            num_config = 0
            num_mongos = 0

        num_nodes_per_shard = self.loaded_args['nodes'] if is_replicaset else 1
        if has_arbiter:
            num_nodes_per_shard += 1

        num_nodes = num_shards * num_nodes_per_shard + num_config + num_mongos

        current_port = self.loaded_args['port']

        # tag all nodes with 'all'
        self.cluster_tags['all'].extend ( range(current_port, current_port + num_nodes) )

        # tag all nodes with their port number (as string) and whether they are running
        for port in range(current_port, current_port + num_nodes):
            self.cluster_tags[str(port)].append(port)

            running = self.is_running(port)
            self.cluster_running[port] = running
            self.cluster_tags['running' if running else 'down'].append(port)

        
        # find all mongos
        for i in range(num_mongos):
            port = i+current_port

            # add mongos to cluster tree
            self.cluster_tree.setdefault( 'mongos', [] ).append( port )
            # add mongos to tags
            self.cluster_tags['mongos'].append( port )

        current_port += num_mongos

        # find all mongods (sharded, replicaset or single)
        if shard_names == None:
            shard_names = [ None ]

        for shard in shard_names:
            port_range = range(current_port, current_port + num_nodes_per_shard)

            # all of these are mongod nodes
            self.cluster_tags['mongod'].extend( port_range )

            if shard:
                # if this is a shard, store in cluster_tree and tag shard name
                self.cluster_tree.setdefault( 'shard', [] ).append( port_range )
                self.cluster_tags[shard].extend( port_range )

            if is_replicaset:
                # get replica set states
                rs_name = shard if shard else self.loaded_args['name']
                
                try:
                    mrsc = ReplicaSetConnection( ','.join( 'localhost:%i'%i for i in port_range ), replicaSet=rs_name )
                    # primary, secondaries, arbiters
                    if mrsc.primary:
                        self.cluster_tags['primary'].append( mrsc.primary[1] )
                    self.cluster_tags['secondary'].extend( map(itemgetter(1), mrsc.secondaries) )
                    self.cluster_tags['arbiter'].extend( map(itemgetter(1), mrsc.arbiters) )

                    # secondaries in cluster_tree (order is now important)
                    self.cluster_tree.setdefault( 'secondary', [] )
                    for i, secondary in enumerate(sorted(map(itemgetter(1), mrsc.secondaries))):
                        if len(self.cluster_tree['secondary']) <= i:
                            self.cluster_tree['secondary'].append([])
                        self.cluster_tree['secondary'][i].append(secondary)

                except (ConnectionFailure, ConfigurationError):
                    pass

            elif is_single:
                self.cluster_tags['single'].append( current_port )

            # increase current_port
            current_port += num_nodes_per_shard


        # find all config servers
        for i in range(num_config):
            port = i+current_port

            try:
                mc = Connection( 'localhost:%i'%port )
                running = True

            except ConnectionFailure:
                # node not reachable
                running = False

            # add config server to cluster tree
            self.cluster_tree.setdefault( 'config', [] ).append( port )
            # add config server to tags
            self.cluster_tags['config'].append( port )
            self.cluster_tags['mongod'].append( port )

        current_port += num_mongos


    def is_running(self, port):
        """ returns if a host on a specific port is running. """
        try:
            con = Connection('localhost:%s' % port)
            con.admin.command('ping')
            return True
        except (AutoReconnect, ConnectionFailure):
            return False


    def get_tagged(self, tags):
        """ The format for the tags list is tuples for tags: mongos, config, shard, secondary tags
            of the form (tag, number), e.g. ('mongos', 2) which references the second mongos 
            in the list. For all other tags, it is simply the string, e.g. 'primary'.
        """

        # if tags is a simple string, make it a list (note: tuples like ('mongos', 2) must be in a surrounding list)
        if not hasattr(tags, '__iter__') and type(tags) == str:
            tags = [ tags ]

        nodes = set(self.cluster_tags['all'])

        for tag in tags:
            if re.match(r'\w+ \d{1,2}', tag):
                # special case for tuple tags: mongos, config, shard, secondary. These can contain a number
                tag, number = tag.split()

                try:
                    branch = self.cluster_tree[tag][int(number)-1]
                except (IndexError, KeyError):
                    continue

                if hasattr(branch, '__iter__'):
                    subset = set(branch)
                else:
                    subset = set([branch])
            else:
                # otherwise use tags dict to get the subset
                subset = set(self.cluster_tags[tag])

            nodes = nodes.intersection(subset)

        return nodes

    

    def get_tags_of_port(self, port):
        """ get all tags related to a given port (inverse of what is stored in self.cluster_tags) """
        return sorted([tag for tag in self.cluster_tags if port in self.cluster_tags[tag] ])


    def wait_for(self, ports, interval=1.0, timeout=30, to_start=True):
        """ Given a list of ports, spawns up threads that will ping the host on each port concurrently. 
            Returns when all hosts are running (if to_start=True) / shut down (if to_start=False)
        """
        threads = []
        queue = Queue.Queue()

        for port in ports:
            threads.append(threading.Thread(target=wait_for_host, args=(port, interval, timeout, to_start, queue)))

        if self.args and 'verbose' in self.args and self.args['verbose']:
            print "waiting for nodes %s..." % ('to start' if to_start else 'to shutdown')
        
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # get all results back and return tuple
        return tuple(queue.get_nowait() for _ in ports)


    # --- below here are internal helper methods, should not be called externally ---


    def _convert_u2b(self, obj):
        """ helper method to convert unicode back to plain text. """
        if isinstance(obj, dict):
            return dict([(self._convert_u2b(key), self._convert_u2b(value)) for key, value in obj.iteritems()])
        elif isinstance(obj, list):
            return [self._convert_u2b(element) for element in obj]
        elif isinstance(obj, unicode):
            return obj.encode('utf-8')
        else:
            return obj


    def _load_parameters(self):
        """ tries to load the .mlaunch_startup file that exists in each datadir. 
            Handles different protocol versions. 
        """
        datapath = self.dir

        startup_file = os.path.join(datapath, '.mlaunch_startup')
        if not os.path.exists(startup_file):
            return False

        in_dict = self._convert_u2b(json.load(open(startup_file, 'r')))

        # handle legacy version without versioned protocol
        if 'protocol_version' not in in_dict:
            in_dict['protocol_version'] = 1
            self.loaded_args = in_dict
            self.startup_info = {}

        elif in_dict['protocol_version'] == 2:
            self.startup_info = in_dict['startup_info']
            self.loaded_unknown_args = in_dict['unknown_args']
            self.loaded_args = in_dict['parsed_args']

        # changed 'authentication' to 'auth', if present (from old env) rename
        if 'authentication' in self.loaded_args:
            self.loaded_args['auth'] = self.loaded_args['authentication']
            del self.loaded_args['authentication']

        return True


    def _store_parameters(self):
        """ stores the startup parameters and config in the .mlaunch_startup file in the datadir. """
        datapath = self.dir

        out_dict = {
            'protocol_version': 2, 
            'mtools_version':  __version__,
            'parsed_args': self.args,
            'unknown_args': self.unknown_args,
            'startup_info': self.startup_info
        }

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        try:
            json.dump(out_dict, open(os.path.join(datapath, '.mlaunch_startup'), 'w'), -1)
        except Exception:
            pass


    def _create_paths(self, basedir, name=None):
        """ create datadir and subdir paths. """
        if name:
            datapath = os.path.join(basedir, name)
        else:
            datapath = basedir

        dbpath = os.path.join(datapath, 'db')
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)
        if self.args['verbose']:
            print 'creating directory: %s'%dbpath
        
        return datapath


    def _get_ports_from_args(self, args, extra_tag):
        tags = []

        for tag1, tag2 in zip(args['tags'][:-1], args['tags'][1:]):
            if re.match('^\d{1,2}$', tag1):
                print "warning: ignoring numeric value '%s'" % tag1
                continue

            if re.match('^\d{1,2}$', tag2):
                if tag1 in ['mongos', 'shard', 'secondary', 'config']:
                    # combine tag with number, separate by string
                    tags.append( '%s %s' % (tag1, tag2) )
                    continue
                else: 
                    print "warning: ignoring numeric value '%s' after '%s'"  % (tag2, tag1)
            
            tags.append( tag1 )

        if len(args['tags']) > 0:
            tag = args['tags'][-1]
            if not re.match('^\d{1,2}$', tag):
                tags.append(tag)

        tags.append(extra_tag)

        matches = self.get_tagged(tags)
        return matches


    def _filter_valid_arguments(self, arguments, binary="mongod", config=False):
        """ check which of the list of arguments is accepted by the specified binary (mongod, mongos). 
            returns a list of accepted arguments. If an argument does not start with '-' but its preceding
            argument was accepted, then it is accepted as well. Example ['--slowms', '1000'] both arguments
            would be accepted for a mongod.
        """

        if self.args and self.args['binarypath']:
            binary = os.path.join( self.args['binarypath'], binary)

        # get the help list of the binary
        ret = subprocess.Popen(['%s --help'%binary], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        out, err = ret.communicate()

        accepted_arguments = []

        # extract all arguments starting with a '-'
        for line in [option for option in out.split('\n')]:
            line = line.lstrip()
            if line.startswith('-'):
                argument = line.split()[0]
                # exception: don't allow --oplogSize for config servers
                if config and argument == '--oplogSize':
                    continue
                accepted_arguments.append(argument)

        # filter valid arguments
        result = []
        for i, arg in enumerate(arguments):
            if arg.startswith('-'):
                # check if the binary accepts this argument or special case -vvv for any number of v
                if arg in accepted_arguments or re.match(r'-v+', arg):
                    result.append(arg)
            elif i > 0 and arguments[i-1] in result:
                # if it doesn't start with a '-', it could be the value of the last argument, e.g. `--slowms 1000`
                result.append(arg)

        # return valid arguments as joined string
        return ' '.join(result)


    def _get_shard_names(self, args):
        """ get the shard names based on the self.args['sharded'] parameter. If it's a number, create
            shard names of type shard##, where ## is a 2-digit number. Returns a list [ None ] if 
            no shards are present.
        """

        if 'sharded' in args and args['sharded']:
            if len(args['sharded']) == 1:
                try:
                    # --sharded was a number, name shards shard01, shard02, ... (only works with replica sets)
                    n_shards = int(args['sharded'][0])
                    shard_names = ['shard%.2i'%(i+1) for i in range(n_shards)]
                except ValueError, e:
                    # --sharded was a string, use it as name for the one shard 
                    shard_names = args['sharded']
            else:
                shard_names = args['sharded']
        else:
            shard_names = [ None ]
        return shard_names


    
    def _start_on_ports(self, ports, wait=False):
        threads = []

        for port in ports:
            command_str = self.startup_info[str(port)]
            ret = subprocess.call([command_str], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
            
            binary = command_str.split()[0]
            if '--configsvr' in command_str:
                binary = 'config server'

            if self.args['verbose']:
                print "launching: %s" % command_str
            else:
                print "launching: %s on port %s" % (binary, port)

            if ret > 0:
                raise SystemExit("can't start process, return code %i. tried to launch: %s"% (ret, command_str))

        if wait:
            self.wait_for(ports)


    def _initiate_replset(self, port, name, maxwait=30):
        # initiate replica set
        if not self.args['replicaset']:
            return 

        con = Connection('localhost:%i'%port)
        try:
            rs_status = con['admin'].command({'replSetGetStatus': 1})
        except OperationFailure, e:
            # not initiated yet
            for i in range(maxwait):
                try:
                    con['admin'].command({'replSetInitiate':self.config_docs[name]})
                    break
                except OperationFailure, e:
                    print e.message, " - will retry"
                    time.sleep(1)

            if self.args['verbose']:
                print "initializing replica set '%s' with configuration: %s" % (name, self.config_docs[name])
            print "replica set '%s' initialized." % name


    def _add_user(self, port, name, password, database, roles):
        con = Connection('localhost:%i'%port)
        try:
            con[database].add_user(name, password=password, roles=roles)
        except OperationFailure as e:
            pass


    def _get_processes(self):
        all_ports = self.get_tagged('all')
        
        process_dict = {}

        for p in psutil.process_iter():
            # skip all but mongod / mongos
            if p.name not in ['mongos', 'mongod']:
                continue

            # find first TCP listening port
            ports = [con.laddr[1] for con in p.get_connections(kind='tcp') if con.status=='LISTEN']
            if len(ports) > 0:
                port = min(ports)
            else:
                continue
                
            # only consider processes belonging to this environment
            if port in all_ports:
                process_dict[port] = p

        return process_dict


    def _wait_for_primary(self, max_wait=120):

        for i in range(max_wait):
            self.discover()

            if "primary" in self.cluster_tags and self.cluster_tags['primary']:
                return True

            time.sleep(1)

        return False


    # --- below are command line constructor methods, that build the command line strings to be called

    def _construct_cmdlines(self):
        """ This is the top-level _construct_* method. From here, it will branch out to
            the different cases: _construct_sharded, _construct_replicaset, _construct_single. These
            can themselves call each other (for example sharded needs to create the shards with
            either replicaset or single node). At the lowest level, the construct_mongod, _mongos, _config
            will create the actual command line strings and store them in self.startup_info.
        """

        if self.args['sharded']:
            # construct startup string for sharded environments
            self._construct_sharded()
        
        elif self.args['single']:
            # construct startup string for single node environment
            self._construct_single(self.dir, self.args['port'])
            
        elif self.args['replicaset']:
            # construct startup strings for a non-sharded replica set
            self._construct_replset(self.dir, self.args['port'], self.args['name'])

        # discover current setup
        self.discover()



    def _construct_sharded(self):
        """ construct command line strings for a sharded cluster. """

        num_mongos = self.args['mongos'] if self.args['mongos'] > 0 else 1
        shard_names = self._get_shard_names(self.args)

        # create shards as stand-alones or replica sets
        nextport = self.args['port'] + num_mongos
        for shard in shard_names:
            if self.args['single']:
                self.shard_connection_str.append( self._construct_single(self.dir, nextport, name=shard) )
                nextport += 1
            elif self.args['replicaset']:
                self.shard_connection_str.append( self._construct_replset(self.dir, nextport, shard) )
                nextport += self.args['nodes']
                if self.args['arbiter']:
                    nextport += 1

        # start up config server(s)
        config_string = []
        config_names = ['config1', 'config2', 'config3'] if self.args['config'] == 3 else ['config']
            
        for name in config_names:
            self._construct_config(self.dir, nextport, name)
            config_string.append('%s:%i'%(self.hostname, nextport))
            nextport += 1
        
        # multiple mongos use <datadir>/mongos/ as subdir for log files
        if num_mongos > 1:
            mongosdir = os.path.join(self.dir, 'mongos')
            if not os.path.exists(mongosdir):
                if self.args['verbose']:
                    print "creating directory: %s" % mongosdir
                os.makedirs(mongosdir) 

        # start up mongos, but put them to the front of the port range
        nextport = self.args['port']
        for i in range(num_mongos):
            if num_mongos > 1:
                mongos_logfile = 'mongos/mongos_%i.log' % nextport
            else:
                mongos_logfile = 'mongos.log'
            self._construct_mongos(os.path.join(self.dir, mongos_logfile), nextport, ','.join(config_string))

            nextport += 1


    def _construct_replset(self, basedir, portstart, name):
        """ construct command line strings for a replicaset, either for sharded cluster or by itself. """

        self.config_docs[name] = {'_id':name, 'members':[]}

        for i in range(self.args['nodes']):
            datapath = self._create_paths(basedir, '%s/rs%i'%(name, i+1))
            self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+i, replset=name)
        
            host = '%s:%i'%(self.hostname, portstart+i)
            self.config_docs[name]['members'].append({'_id':len(self.config_docs[name]['members']), 'host':host, 'votes':int(len(self.config_docs[name]['members']) < 7 - int(self.args['arbiter']))})

        # launch arbiter if True
        if self.args['arbiter']:
            datapath = self._create_paths(basedir, '%s/arb'%(name))
            self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+self.args['nodes'], replset=name)
            
            host = '%s:%i'%(self.hostname, portstart+self.args['nodes'])
            self.config_docs[name]['members'].append({'_id':len(self.config_docs[name]['members']), 'host':host, 'arbiterOnly': True})

        return name + '/' + ','.join([c['host'] for c in self.config_docs[name]['members']])



    def _construct_config(self, basedir, port, name=None):
        """ construct command line strings for a config server """
        datapath = self._create_paths(basedir, name)
        self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None, extra='--configsvr')



    def _construct_single(self, basedir, port, name=None):
        """ construct command line strings for a single node, either for shards or as a stand-alone. """
        datapath = self._create_paths(basedir, name)
        self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None)

        host = '%s:%i'%(self.hostname, port)

        return host


    def _construct_mongod(self, dbpath, logpath, port, replset=None, extra=''):
        """ construct command line strings for mongod process. """
        rs_param = ''
        if replset:
            rs_param = '--replSet %s'%replset

        auth_param = ''
        if self.args['auth']:
            key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
            auth_param = '--keyFile %s'%key_path

        if self.unknown_args:
            config = '--configsvr' in extra
            extra = self._filter_valid_arguments(self.unknown_args, "mongod", config=config) + ' ' + extra

        path = self.args['binarypath'] or ''
        command_str = "%s %s --dbpath %s --logpath %s --port %i --logappend %s %s --fork"%(os.path.join(path, 'mongod'), rs_param, dbpath, logpath, port, auth_param, extra)

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str


    def _construct_mongos(self, logpath, port, configdb):
        """ construct command line strings for a mongos process. """
        extra = ''
        out = subprocess.PIPE
        if self.args['verbose']:
            out = None

        auth_param = ''
        if self.args['auth']:
            key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
            auth_param = '--keyFile %s'%key_path

        if self.unknown_args:
            extra = self._filter_valid_arguments(self.unknown_args, "mongos") + extra

        path = self.args['binarypath'] or ''
        command_str = "%s --logpath %s --port %i --configdb %s --logappend %s %s --fork"%(os.path.join(path, 'mongos'), logpath, port, configdb, auth_param, extra)

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str




if __name__ == '__main__':
    tool = MLaunchTool()
    tool.run()

########NEW FILE########
__FILENAME__ = mlog2json
#!/usr/bin/env python

print "deprecated since version 1.1.0 of mtools. Use 'mlogfilter <logfile> --json' instead."

########NEW FILE########
__FILENAME__ = mlogdistinct
#!/usr/bin/env python

print "deprecated since version 1.1.0 of mtools. Use 'mloginfo <logfile> --distinct' instead."

########NEW FILE########
__FILENAME__ = base_filter
class BaseFilter(object):
    """ Base Filter class. All filters need to derive from it and implement
        their version of filterArgs, accept, and optionally skipRemaining.

        filterArgs needs to be a list of tuples with 2 elements each. The 
        first tuple element is the filter argument, e.g. --xyz. The second
        element of the tuple is a dictionary that gets passed to the 
        ArgumentParser object's add_argument method.
    """

    filterArgs = []

    def __init__(self, mlogfilter):
        """ constructor. save command line arguments and set active to False
            by default. 
        """
        self.mlogfilter = mlogfilter

        # filters need to actively set this flag to true
        self.active = False

    def setup(self):
        """ hook to setup anything necessary for the filter before actually
            going through logevents. overwrite in subclass if setup is required.
        """
        pass

    def accept(self, logevent):
        """ overwrite this method in subclass and return True if the provided 
            logevent should be accepted (causing output), or False if not.
        """
        return True

    def skipRemaining(self):
        """ overwrite this method in sublcass and return True if all lines
            from here to the end of the file should be rejected (no output).
        """
        return False
########NEW FILE########
__FILENAME__ = datetime_filter
from mtools.util import OrderedDict
from mtools.util.hci import DateTimeBoundaries
from datetime import datetime, timedelta, MINYEAR, MAXYEAR
from dateutil.tz import tzutc
from mtools.util.logevent import LogEvent

from base_filter import BaseFilter


def custom_parse_dt(value):
    return value


class DateTimeFilter(BaseFilter):
    """ This filter has two parser arguments: --from and --to, both are
        optional. All possible values for --from and --to can be described as:

        [DATE] [TIME] [OFFSET] in that order, separated by a space.

        [DATE] can be any of
            - a 3-letter weekday (Mon, Tue, Wed, ...)
            - a date as 3-letter month, 1-2 digits day (Sep 5, Jan 31, Aug 08)
            - the words: today, now, start, end

        [TIME] can be any of
            - hours and minutes (20:15, 04:00, 3:00)
            - hours, minutes and seconds (13:30:01, 4:55:55)

        [OFFSET] consists of [OPERATOR][VALUE][UNIT]   (no spaces in between)

        [OPERATOR] can be + or - (note that - can only be used if the whole
            "[DATE] [TIME] [OFFSET]" is in quotation marks, otherwise it would
            be confused with a separate parameter)

        [VALUE] can be any number

        [UNIT] can be any of s, sec, m, min, h, hours, d, days, w, weeks, mo,
            months, y, years

        The [OFFSET] is added/subtracted to/from the specified [DATE] [TIME].

        For the --from parameter, the default is the same as 'start'
            (0001-01-01 00:00:00). If _only_ an [OFFSET] is given, it is
            added to 'start' (which is not very useful).

        For the --to parameter, the default is the same as 'end'
            (9999-31-12 23:59:59). If _only_ an [OFFSET] is given, however,
            it is added to [FROM].

        Examples:
            --from Sun 10:00
                goes from last Sunday 10:00:00am to the end of the file

            --from Sep 29
                goes from Sep 29 00:00:00 to the end of the file

            --to today 15:00
                goes from the beginning of the file to today at 15:00:00

            --from today --to +1h
                goes from today's date 00:00:00 to today's date 01:00:00

            --from 20:15 --to +3m
                goes from today's date at 20:15:00 to today's date at 20:18:00
    """

    filterArgs = [
       ('--from', {'action':'store',  'type':custom_parse_dt, 'nargs':'*', 'default':'start', 'help':'output starting at FROM', 'dest':'from'}),
       ('--to',   {'action':'store',  'type':custom_parse_dt, 'nargs':'*', 'default':'end',   'help':'output up to TO',         'dest':'to'})
    ]

    timeunits = ['s', 'sec', 'm', 'min', 'h', 'hours', 'd', 'days', 'w', 'weeks', 'mo', 'months', 'y', 'years']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    dtRegexes = OrderedDict([
        ('weekday', r'|'.join(weekdays)),                         # weekdays: see above
        ('date',    '('+ '|'.join(months) +')' + r'\s+\d{1,2}'),  # month + day:  Jan 5, Oct 13, Sep 03, ...
        ('word',    r'now|start|end|today'),
        ('time2',   r'\d{1,2}:\d{2,2}'),                          # 11:59, 1:13, 00:00, ...
        ('time3',   r'\d{1,2}:\d{2,2}:\d{2,2}'),                  # 11:59:00, 1:13:12, 00:00:59, ...
        ('offset',  r'[\+-]\d+(' + '|'.join(timeunits) + ')'),    # offsets: +3min, -20s, +7days, ...
    ])

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        self.fromReached = False
        self.toReached = False

        self.active = ('from' in self.mlogfilter.args and self.mlogfilter.args['from'] != 'start') or \
                      ('to' in self.mlogfilter.args and self.mlogfilter.args['to'] != 'end')


    def setup(self):
        """ get start end end date of logfile before starting to parse. """

        if self.mlogfilter.is_stdin:
            # assume this year (we have no other info)
            now = datetime.now()
            self.startDateTime = datetime(now.year, 1, 1, tzinfo=tzutc())
            self.endDateTime = datetime(MAXYEAR, 12, 31, tzinfo=tzutc())

        else:
            logfiles = self.mlogfilter.args['logfile']
            self.startDateTime = min([lf.start+timedelta(hours=self.mlogfilter.args['timezone'][i]) for i, lf in enumerate(logfiles)])
            self.endDateTime = max([lf.end+timedelta(hours=self.mlogfilter.args['timezone'][i]) for i, lf in enumerate(logfiles)])

        # now parse for further changes to from and to datetimes
        dtbound = DateTimeBoundaries(self.startDateTime, self.endDateTime)
        self.fromDateTime, self.toDateTime = dtbound(self.mlogfilter.args['from'] or None,
                                                     self.mlogfilter.args['to'] or None)

        # define start_limit for mlogfilter's fast_forward method
        self.start_limit = self.fromDateTime

        # for single logfile, get file seek position of `to` datetime
        if len(self.mlogfilter.args['logfile']) == 1 and not self.mlogfilter.is_stdin:

            if self.mlogfilter.args['to'] != "end":
                # fast forward, get seek value, then reset file
                logfile = self.mlogfilter.args['logfile'][0]
                logfile.fast_forward(self.toDateTime)
                self.seek_to = logfile.filehandle.tell()
                logfile.filehandle.seek(0)
            else:
                self.seek_to = -1
        else:
            self.seek_to = False


    def accept(self, logevent):
        if self.fromReached and self.seek_to:
            if self.seek_to != -1:
                self.toReached = self.mlogfilter.args['logfile'][0].filehandle.tell() >= self.seek_to
            return True
        else:
            # slow version has to check each datetime
            dt = logevent.datetime

            # if logevent has no datetime, accept if between --from and --to
            if dt == None:
                return self.fromReached

            if self.fromDateTime <= dt <= self.toDateTime:
                self.toReached = False
                self.fromReached = True
                return True

            elif dt > self.toDateTime:
                self.toReached = True
                return False

            else:
                return False


    def skipRemaining(self):
        return self.toReached

########NEW FILE########
__FILENAME__ = fast_filter
from base_filter import BaseFilter

class FastFilter(BaseFilter):
    """ accepts only lines that have a duration that is shorter than the specified
        parameter in ms.
    """
    filterArgs = [
        ('--fast', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times shorter than FAST ms (default 1000)'})
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter
            )
        if 'fast' in self.mlogfilter.args and self.mlogfilter.args['fast'] != False:
            self.active = True
            if self.mlogfilter.args['fast'] == None:
                self.fastms = 1000
            else:
                self.fastms = self.mlogfilter.args['fast']

    def accept(self, logevent):
        if self.active and logevent.duration != None:
            return logevent.duration <= self.fastms
        return False

########NEW FILE########
__FILENAME__ = logline_filter
from mtools.util.logevent import LogEvent
from mtools.util.pattern import json2pattern

from base_filter import BaseFilter

class LogLineFilter(BaseFilter):
    """ 
    """
    filterArgs = [
        ('--namespace', {'action':'store', 'metavar':'NS', 'help':'only output log lines matching operations on NS.'}),
        ('--operation', {'action':'store', 'metavar':'OP', 'help':'only output log lines matching operations of type OP.'}),
        ('--thread',    {'action':'store', 'help':'only output log lines of thread THREAD.'}),
        ('--pattern',   {'action':'store', 'help':'only output log lines that query with the pattern PATTERN (queries, getmores, updates, removes)'})
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        self.namespace = None
        self.operation = None
        self.thread = None
        self.pattern = None

        if 'namespace' in self.mlogfilter.args and self.mlogfilter.args['namespace']:
            self.namespace = self.mlogfilter.args['namespace']
            self.active = True
        if 'operation' in self.mlogfilter.args and self.mlogfilter.args['operation']:
            self.operation = self.mlogfilter.args['operation']
            self.active = True
        if 'thread' in self.mlogfilter.args and self.mlogfilter.args['thread']:
            self.thread = self.mlogfilter.args['thread']
            self.active = True
        if 'pattern' in self.mlogfilter.args and self.mlogfilter.args['pattern']:
            self.pattern = json2pattern(self.mlogfilter.args['pattern'])
            self.active = True

    def accept(self, logevent):
        # if several filters are active, all have to agree
        res = False
        if self.namespace and logevent.namespace != self.namespace:
            return False
        if self.operation and logevent.operation != self.operation:
            return False
        if self.thread and logevent.thread != self.thread:
            return False
        if self.pattern and logevent.pattern != self.pattern:
            return False
        return True

########NEW FILE########
__FILENAME__ = mask_filter
from datetime_filter import DateTimeFilter
from datetime import MINYEAR, timedelta
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile
from mtools.util.cmdlinetool import InputSourceAction



class MaskFilter(DateTimeFilter):
    """ This filter takes an argument `--mask <LOGFILE>` and another optional argument
        `--mask-size <SECS>`. It will read <LOGFILE> and for each of the lines extract
        the datetimes (let's call these "events"). It will add some padding for each
        of these events, <SECS>/2 seconds on either side. MaskFilter will then accept
        every line from the original log file (different to <LOGFILE>), that lies within
        one of these masked intervals.

        This feature is very useful to find all correlating lines to certain events.

        For example, find all assertions in a log file, then find all log lines 
        surrounding these assertions:

            grep "assert" mongod.log > assertions.log
            mlogfilter mongod.log --mask assertions.log --mask-size 60

        """


    filterArgs = [
       ('--mask', {'action':'store', 'type':InputSourceAction(), 'help':'source (log file or system.profile db) to create the filter mask.'}), 
       ('--mask-size', {'action':'store',  'type':int, 'default':60, 'help':'mask size in seconds around each filter point (default: 60 secs, 30 on each side of the event)'}),
       ('--mask-center', {'action':'store',  'choices':['start', 'end', 'both'], 'default':'end', 'help':'mask center point for events with duration (default: end). If both is chosen, all events from start to end are returned.'})
    ]


    def __init__(self, mlogfilter):
        """ constructor, init superclass and mark this filter active if `mask` argument is present. """
        DateTimeFilter.__init__(self, mlogfilter)
        self.active = ('mask' in self.mlogfilter.args and self.mlogfilter.args['mask'] != None)
        if self.active:
            self.mask_end_reached = False
            self.mask_source = self.mlogfilter.args['mask']
            self.mask_list = []

    def setup(self):
        """ create mask list consisting of all tuples between which this filter accepts lines. """
        
        # get start and end of the mask and set a start_limit
        if not self.mask_source.start:
            raise SystemExit("Can't parse format of %s. Is this a log file or system.profile collection?" % self.mlogfilter.args['mask'])

        self.mask_half_td = timedelta( seconds=self.mlogfilter.args['mask_size'] / 2 )

        # load filter mask file
        logevent_list = list(self.mask_source)

        # define start and end of total mask
        self.mask_start = self.mask_source.start - self.mask_half_td
        self.mask_end = self.mask_source.end + self.mask_half_td
        
        # consider --mask-center
        if self.mlogfilter.args['mask_center'] in ['start', 'both']:
            if logevent_list[0].duration:
                self.mask_start -= timedelta(milliseconds=logevent_list[0].duration)

        if self.mlogfilter.args['mask_center'] == 'start':
            if logevent_list[-1].duration:
                self.mask_end -= timedelta(milliseconds=logevent_list[-1].duration)

        self.start_limit = self.mask_start

        # different center points
        if 'mask_center' in self.mlogfilter.args:
            if self.mlogfilter.args['mask_center'] in ['start', 'both']:
                starts = [(le.datetime - timedelta(milliseconds=le.duration)) if le.duration != None else le.datetime for le in logevent_list if le.datetime]

            if self.mlogfilter.args['mask_center'] in ['end', 'both']:
                ends = [le.datetime for le in logevent_list if le.datetime]

            if self.mlogfilter.args['mask_center'] == 'start':
                event_list = sorted(starts)
            elif self.mlogfilter.args['mask_center'] == 'end':
                event_list = sorted(ends)
            elif self.mlogfilter.args['mask_center'] == 'both':
                event_list = sorted(zip(starts, ends))

        mask_list = []

        if len(event_list) == 0:
            return

        start_point = end_point = None
        
        for e in event_list:
            if start_point == None:
                start_point, end_point = self._pad_event(e)
                continue

            next_start = (e[0] if type(e) == tuple else e) - self.mask_half_td
            if next_start <= end_point:
                end_point = (e[1] if type(e) == tuple else e) + self.mask_half_td
            else:
                mask_list.append((start_point, end_point))
                start_point, end_point = self._pad_event(e)

        if start_point:
            mask_list.append((start_point, end_point))

        self.mask_list = mask_list


    def _pad_event(self, event):
        if type(event) == tuple:
            start_point = event[0] - self.mask_half_td
            end_point = event[1] + self.mask_half_td
        else:
            start_point = event - self.mask_half_td
            end_point = event + self.mask_half_td

        return start_point, end_point


    def accept(self, logevent):
        """ overwrite this method in subclass and return True if the provided 
            logevent should be accepted (causing output), or False if not.
        """
        dt = logevent.datetime
        if not dt:
            return False

        mask = next( (mask for mask in self.mask_list if mask[0] < dt and mask[1] > dt), None )

        return True if mask else False


    def skipRemaining(self):
        """ overwrite this method in sublcass and return True if all lines
            from here to the end of the file should be rejected (no output).
        """
        return self.mask_end_reached


########NEW FILE########
__FILENAME__ = slow_filter
from base_filter import BaseFilter

class SlowFilter(BaseFilter):
    """ accepts only lines that have a duration that is longer than the specified 
        parameter in ms (default 1000).
    """
    filterArgs = [
        ('--slow', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times longer than SLOW ms (default 1000)'})
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        
        if 'slow' in self.mlogfilter.args and self.mlogfilter.args['slow'] != False:
            self.active = True
            if self.mlogfilter.args['slow'] == None:
                self.slowms = 1000
            else:
                self.slowms = self.mlogfilter.args['slow']

    def accept(self, logevent):
        if logevent.duration != None:
            return logevent.duration >= self.slowms
        return False
########NEW FILE########
__FILENAME__ = tablescan_filter
from base_filter import BaseFilter

class TableScanFilter(BaseFilter):
    """ accepts only if the line contains a nscanned:[0-9] nreturned:[0-9] where the ratio of nscanned:nreturned is > 100 and nscanned > 10000
    """
    filterArgs = [
        ('--scan', {'action':'store_true', 'help':'only output lines which appear to be table scans (if nscanned>10000 and ratio of nscanned to nreturned>100)'})
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        
        if 'scan' in self.mlogfilter.args:
            self.active = self.mlogfilter.args['scan']

    def accept(self, logevent):

        ns = logevent.nscanned
        nr = logevent.nreturned

        if ns != None and nr != None:
            if nr == 0:
                # avoid division by 0 errors
                nr = 1
            return (ns > 10000 and ns/nr > 100)

        return False

########NEW FILE########
__FILENAME__ = word_filter
import re
from base_filter import BaseFilter


class WordFilter(BaseFilter):
    """ accepts only if line contains any of the words specified by --word 
    """

    filterArgs = [
        ('--word', {'action':'store', 'nargs':'*', 'help':'only output lines matching any of WORD'}),
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        # extract all arguments passed into 'word'
        if 'word' in self.mlogfilter.args and self.mlogfilter.args['word']:
            self.words = self.mlogfilter.args['word'].split()
            self.active = True
        else:
            self.active = False

    def accept(self, logevent):
        for word in self.words:
            if re.search(word, logevent.line_str):
                return True
        return False

########NEW FILE########
__FILENAME__ = mlogfilter
#!/usr/bin/env python

import argparse, re
import sys
import inspect
import types

from datetime import datetime, timedelta, MINYEAR, MAXYEAR
from dateutil.tz import tzutc

from mtools.util.logevent import LogEvent
from mtools.util.cmdlinetool import LogFileTool
from mtools.mlogfilter.filters import *

import mtools.mlogfilter.filters as filters

class MLogFilterTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)

        # add all filter classes from the filters module
        self.filters = [c[1] for c in inspect.getmembers(filters, inspect.isclass)]

        self.argparser.description = 'mongod/mongos log file parser. Use parameters to enable filters. A line only gets printed if it passes all enabled filters. If several log files are provided, their lines are merged by timestamp.'
        self.argparser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
        self.argparser.add_argument('--shorten', action='store', type=int, default=False, nargs='?', metavar='LENGTH', help='shortens long lines by cutting characters out of the middle until the length is <= LENGTH (default 200)')
        self.argparser.add_argument('--exclude', action='store_true', default=False, help='if set, excludes the matching lines rather than includes them.')
        self.argparser.add_argument('--human', action='store_true', help='outputs large numbers formatted with commas and print milliseconds as hr,min,sec,ms for easier readability.')
        self.argparser.add_argument('--json', action='store_true', help='outputs all matching lines in json format rather than the native log line.')
        self.argparser.add_argument('--markers', action='store', nargs='*', default=['filename'], help='use markers when merging several files to distinguish them. Choose from none, enum, alpha, filename (default), or provide list.')
        self.argparser.add_argument('--timezone', action='store', nargs='*', default=[], type=int, metavar="N", help="timezone adjustments: add N hours to corresponding log file, single value for global adjustment.")
        self.argparser.add_argument('--timestamp-format', action='store', default='none', choices=['none', 'ctime-pre2.4', 'ctime', 'iso8601-utc', 'iso8601-local'], help="choose datetime format for log output")

    def addFilter(self, filterClass):
        """ adds a filter class to the parser. """
        if not filterClass in self.filters:
            self.filters.append(filterClass)


    def _arrayToString(self, arr):
        """ if arr is of type list, join elements with space delimiter. """
        if isinstance(arr, list):
            return " ".join(arr)
        else:
            return arr


    def _outputLine(self, logevent, length=None, human=False):
        """ prints the final line, with various options (length, human, datetime changes, ...) """
        # adapt timezone output if necessary
        if self.args['timestamp_format'] != 'none':
            logevent._reformat_timestamp(self.args['timestamp_format'], force=True)
        if any(self.args['timezone']):
            if self.args['timestamp_format'] == 'none':
                self.args['timestamp_format'] = logevent.datetime_format
            logevent._reformat_timestamp(self.args['timestamp_format'], force=True)

        if self.args['json']:
            print logevent.to_json()
            return

        line = logevent.line_str

        if length:
            if len(line) > length:
                line = line[:length/2-2] + '...' + line[-length/2+1:]
        if human:
            line = self._changeMs(line)
            line = self._formatNumbers(line)

        print line


    def _msToString(self, ms):
        """ changes milliseconds to hours min sec ms format """
        hr, ms = divmod(ms, 3600000)
        mins, ms = divmod(ms, 60000)
        secs, mill = divmod(ms, 1000)
        return "%ihr %imin %isecs %ims"%(hr, mins, secs, mill)


    def _changeMs(self, line):
        """ changes the ms part in the string if needed """
        # use the the position of the last space instead
        try:
            last_space_pos = line.rindex(' ')
        except ValueError, s:
            return line
        else:
            end_str = line[last_space_pos:]
            new_string = line
            if end_str[-2:] == 'ms' and int(end_str[:-2]) >= 1000:
                # isolate the number of milliseconds
                ms = int(end_str[:-2])
                # create the new string with the beginning part of the log with the new ms part added in
                new_string = line[:last_space_pos] + ' (' +  self._msToString(ms) + ')' + line[last_space_pos:]
            return new_string

    def _formatNumbers(self, line):
        """ formats the numbers so that there are commas inserted, ie. 1200300 becomes 1,200,300 """
        # below thousands separator syntax only works for python 2.7, skip for 2.6
        if sys.version_info < (2, 7):
            return line

        last_index = 0
        try:
            # find the index of the last } character
            last_index = (line.rindex('}') + 1)
            end = line[last_index:]
        except ValueError, e:
            return line
        else:
            # split the string on numbers to isolate them
            splitted = re.split("(\d+)", end)
            for index, val in enumerate(splitted):
                converted = 0
                try:
                    converted = int(val)
                #if it's not an int pass and don't change the string
                except ValueError, e:
                    pass
                else:
                    if converted > 1000:
                        splitted[index] = format(converted, ",d")
            return line[:last_index] + ("").join(splitted)


    def _datetime_key_for_merge(self, logevent):
        """ helper method for ordering log lines correctly during merge. """
        if not logevent:
            # if logfile end is reached, return max datetime to never pick this line
            return datetime(MAXYEAR, 12, 31, 23, 59, 59, 999999, tzutc())

        # if no datetime present (line doesn't have one) return mindate to pick this line immediately
        return logevent.datetime or datetime(MINYEAR, 1, 1, 0, 0, 0, 0, tzutc())


    def _merge_logfiles(self):
        """ helper method to merge several files together by datetime. """
        # open files, read first lines, extract first dates
        lines = [next(logfile, None) for logfile in self.args['logfile']]

        # adjust lines by timezone
        for i in range(len(lines)):
            if lines[i] and lines[i].datetime:
                lines[i]._datetime = lines[i].datetime + timedelta(hours=self.args['timezone'][i])

        while any(lines):
            min_line = min(lines, key=self._datetime_key_for_merge)
            min_index = lines.index(min_line)

            if self.args['markers'][min_index]:
                min_line.merge_marker_str = self.args['markers'][min_index]

            yield min_line

            # update lines array with a new line from the min_index'th logfile
            lines[min_index] = next(self.args['logfile'][min_index], None)
            if lines[min_index] and lines[min_index].datetime:
                lines[min_index]._datetime = lines[min_index].datetime + timedelta(hours=self.args['timezone'][min_index])


    def logfile_generator(self):
        """ generator method that yields each line of the logfile, or the next line in case of several log files. """

        if not self.args['exclude']:
            # ask all filters for a start_limit and fast-forward to the maximum
            start_limits = [ f.start_limit for f in self.filters if hasattr(f, 'start_limit') ]

            if start_limits:
                for logfile in self.args['logfile']:
                    logfile.fast_forward( max(start_limits) )

        if len(self.args['logfile']) > 1:
            # merge log files by time
            for logevent in self._merge_logfiles():
                yield logevent
        else:
            # only one file
            for logevent in self.args['logfile'][0]:
                if self.args['timezone'][0] != 0 and logevent.datetime:
                    logevent._datetime = logevent.datetime + timedelta(hours=self.args['timezone'][0])
                yield logevent


    def run(self, arguments=None):
        """ parses the logfile and asks each filter if it accepts the line.
            it will only be printed if all filters accept the line.
        """

        # add arguments from filter classes before calling superclass run
        for f in self.filters:
            for fa in f.filterArgs:
                self.argparser.add_argument(fa[0], **fa[1])

        # now parse arguments and post-process
        LogFileTool.run(self, arguments)
        self.args = dict((k, self.args[k] if k in ['logfile', 'markers', 'timezone'] else self._arrayToString(self.args[k])) for k in self.args)

        # make sure logfile is always a list, even if 1 is provided through sys.stdin
        if type(self.args['logfile']) != types.ListType:
            self.args['logfile'] = [self.args['logfile']]

        # require at least 1 log file (either through stdin or as parameter)
        if len(self.args['logfile']) == 0:
            raise SystemExit('Error: Need at least 1 log file, either as command line parameter or through stdin.')

        # handle timezone parameter
        if len(self.args['timezone']) == 1:
            self.args['timezone'] = self.args['timezone'] * len(self.args['logfile'])
        elif len(self.args['timezone']) == len(self.args['logfile']):
            pass
        elif len(self.args['timezone']) == 0:
            self.args['timezone'] = [0] * len(self.args['logfile'])
        else:
            raise SystemExit('Error: Invalid number of timezone parameters. Use either one parameter (for global adjustment) or the number of log files (for individual adjustments).')

        # create filter objects from classes and pass args
        self.filters = [f(self) for f in self.filters]

        # remove non-active filter objects
        self.filters = [f for f in self.filters if f.active]

        # call setup for each active filter
        for f in self.filters:
            f.setup()

        if self.args['shorten'] != False:
            if self.args['shorten'] == None:
                self.args['shorten'] = 200

        if self.args['verbose']:
            print "command line arguments"
            for a in self.args:
                print "    %s: %s" % (a, self.args[a])
            print
            print "active filters:",
            print ', '.join([f.__class__.__name__ for f in self.filters])
            print
            print '===================='

        # handle markers parameter
        if len(self.args['markers']) == 1:
            marker = self.args['markers'][0]
            if marker == 'enum':
                self.args['markers'] = ['{%i}'%(i+1) for i in range(len(self.args['logfile']))]
            elif marker == 'alpha':
                self.args['markers'] = ['{%s}'%chr(97+i) for i in range(len(self.args['logfile']))]
            elif marker == 'none':
                self.args['markers'] = [None for _ in self.args['logfile']]
            elif marker == 'filename':
                self.args['markers'] = ['{%s}'%logfile.name for logfile in self.args['logfile']]
        elif len(self.args['markers']) == len(self.args['logfile']):
            pass
        else:
            raise SystemExit('Error: Number of markers not the same as number of files.')

        # with --human, change to ctime format if not specified otherwise
        if self.args['timestamp_format'] == 'none' and self.args['human']:
            self.args['timestamp_format'] = 'ctime'

        # go through each line and ask each filter if it accepts
        if not 'logfile' in self.args or not self.args['logfile']:
            raise SystemExit('no logfile found.')

        for logevent in self.logfile_generator():
            if self.args['exclude']:
                # print line if any filter disagrees
                if any([not f.accept(logevent) for f in self.filters]):
                    self._outputLine(logevent, self.args['shorten'], self.args['human'])

            else:
                # only print line if all filters agree
                if all([f.accept(logevent) for f in self.filters]):
                    self._outputLine(logevent, self.args['shorten'], self.args['human'])

                # if at least one filter refuses to accept any remaining lines, stop
                if any([f.skipRemaining() for f in self.filters]):
                    # if input is not stdin
                    if sys.stdin.isatty():
                        break


if __name__ == '__main__':

    tool = MLogFilterTool()
    tool.run()

########NEW FILE########
__FILENAME__ = mloginfo
#!/usr/bin/env python

from mtools.util.logfile import LogFile
from mtools.util.logevent import LogEvent
from mtools.util.cmdlinetool import LogFileTool

import inspect
import mtools.mloginfo.sections as sections



class MLogInfoTool(LogFileTool):

    def __init__(self):
        """ Constructor: add description to argparser. """
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=False)

        self.argparser.description = 'Extracts general information from logfile and prints it to stdout.'
        self.argparser.add_argument('--verbose', action='store_true', help='show more verbose output (depends on info section)')
        self.argparser_sectiongroup = self.argparser.add_argument_group('info sections', 'Below commands activate additional info sections for the log file.')

        # add all filter classes from the filters module
        self.sections = [c[1](self) for c in inspect.getmembers(sections, inspect.isclass)]

    def run(self, arguments=None):
        """ Print out useful information about the log file. """
        LogFileTool.run(self, arguments)

        for i, self.logfile in enumerate(self.args['logfile']):
            if i > 0:
                print
                print ' ------------------------------------------'
                print

            print "     source: %s" % self.logfile.name
            print "      start: %s" % (self.logfile.start.strftime("%Y %b %d %H:%M:%S") if self.logfile.start else "unknown")
            print "        end: %s" % (self.logfile.end.strftime("%Y %b %d %H:%M:%S") if self.logfile.start else "unknown")

            # TODO: add timezone if iso8601 format
            print "date format: %s" % self.logfile.datetime_format
            print "     length: %s" % len(self.logfile)
            print "     binary: %s" % (self.logfile.binary or "unknown")
            

            version = (' -> '.join(self.logfile.versions) or "unknown")

            # if version is unknown, go by date
            if version == 'unknown':
                if self.logfile.datetime_format == 'ctime-pre2.4':
                    version = '< 2.4 (no milliseconds)'
                elif self.logfile.datetime_format == 'ctime':
                    version = '>= 2.4 (milliseconds present)'
                elif self.logfile.datetime_format.startswith('iso8601-'):
                    version = '>= 2.6 (iso8601 format)'

            print "    version: %s" % version,
            print

            # now run all sections
            for section in self.sections:
                if section.active:
                    print
                    print section.name.upper()
                    section.run()


if __name__ == '__main__':
    tool = MLogInfoTool()
    tool.run()

########NEW FILE########
__FILENAME__ = base_section
class BaseSection(object):
    """ BaseSection class. All sections need to derive from it and add
        their arguments to the mloginfo.argparser object and determine if they are
        active.
    """

    filterArgs = []
    name = 'base'
    active = False

    def __init__(self, mloginfo):
        """ constructor. save command line arguments and set active to False
            by default. 
        """
        # mloginfo object, use it to get access to argparser and other class variables
        self.mloginfo = mloginfo


    def run(self):
        pass


########NEW FILE########
__FILENAME__ = connection_section
from base_section import BaseSection
from collections import defaultdict
import re

from mtools.util.profile_collection import ProfileCollection

class ConnectionSection(BaseSection):
    """ This section goes through the logfile and extracts information 
        about opened and closed connections.
    """
    
    name = "connections"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--connections', action='store_true', help='outputs information about opened and closed connections')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['connections']


    def run(self):
        """ run this section and print out information. """
        if isinstance(self.mloginfo.logfile, ProfileCollection):
            print
            print "    not available for system.profile collections"
            print
            return

        ip_opened = defaultdict(lambda: 0)
        ip_closed = defaultdict(lambda: 0)
        socket_exceptions = 0

        for logevent in self.mloginfo.logfile:
            line = logevent.line_str
            pos = line.find('connection accepted')
            if pos != -1:
                # connection was opened, increase counter
                tokens = line[pos:pos+100].split(' ')
                if tokens[3] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[3].split(':')
                ip_opened[ip] += 1

            pos = line.find('end connection')
            if pos != -1:
                # connection was closed, increase counter
                tokens = line[pos:pos+100].split(' ')
                if tokens[2] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[2].split(':')
                ip_closed[ip] += 1

            if "SocketException" in line:
                socket_exceptions += 1


        # calculate totals
        total_opened = sum(ip_opened.values())
        total_closed = sum(ip_closed.values())

        unique_ips = set(ip_opened.keys())
        unique_ips.update(ip_closed.keys())


        # output statistics
        print "     total opened:", total_opened
        print "     total closed:", total_closed
        print "    no unique IPs:", len(unique_ips)
        print "socket exceptions:", socket_exceptions
        print

        for ip in sorted(unique_ips, key=lambda x: ip_opened[x], reverse=True):
            opened = ip_opened[ip] if ip in ip_opened else 0
            closed = ip_closed[ip] if ip in ip_closed else 0

            print "%-15s  opened: %-8i  closed: %-8i" % (ip, opened, closed)
        print

########NEW FILE########
__FILENAME__ = distinct_section
from base_section import BaseSection

from mtools.util.log2code import Log2CodeConverter
from mtools.util.profile_collection import ProfileCollection

from collections import defaultdict


class DistinctSection(BaseSection):
    """ This section shows a distinct view of all log lines matched with the Log2Code matcher.
    	It will output sorted statistics of which logevent patterns where matched how often
    	(most frequent first).
    """
    
    name = "distinct"
    log2code = Log2CodeConverter()


    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--distinct', action='store_true', help='outputs distinct list of all log line by message type (slow)')

    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['distinct']


    def run(self):
        """ go over each line in the logfile, run through log2code matcher 
            and group by matched pattern.
        """

        if isinstance(self.mloginfo.logfile, ProfileCollection):
            print
            print "    not available for system.profile collections"
            print
            return


        codelines = defaultdict(lambda: 0)
        non_matches = 0

        # get log file information
        logfile = self.mloginfo.logfile
        if logfile.start and logfile.end and not self.mloginfo.args['verbose']:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = self.mloginfo._datetime_to_epoch(logfile.end) - progress_start
        else:
            self.mloginfo.progress_bar_enabled = False

        for i, logevent in enumerate(self.mloginfo.logfile):
            cl, _ = self.log2code(logevent.line_str)

            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if logevent.datetime:
                    progress_curr = self.mloginfo._datetime_to_epoch(logevent.datetime)
                    self.mloginfo.update_progress(float(progress_curr-progress_start) / progress_total)

            if cl:
                codelines[cl.pattern] += 1
            else:
                if logevent.operation:
                    # skip operations (command, insert, update, delete, query, getmore)
                    continue
                if not logevent.thread:
                    # skip the lines that don't have a thread name (usually map/reduce or assertions)
                    continue
                if len(logevent.split_tokens) - logevent.datetime_nextpos <= 1:
                    # skip empty log messages (after thread name)
                    continue
                if "warning: log line attempted" in logevent.line_str and "over max size" in logevent.line_str:
                    # skip lines that are too long
                    continue

                # everything else is a real non-match
                non_matches += 1
                if self.mloginfo.args['verbose']:
                    print "couldn't match:", logevent

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        if self.mloginfo.args['verbose']: 
            print

        for cl in sorted(codelines, key=lambda x: codelines[x], reverse=True):
            print "%8i"%codelines[cl], "  ", " ... ".join(cl)

        print
        if non_matches > 0:
            print "distinct couldn't match %i lines"%non_matches
            if not self.mloginfo.args['verbose']:
                print "to show non-matched lines, run with --verbose."

########NEW FILE########
__FILENAME__ = query_section
from base_section import BaseSection

from mtools.util.profile_collection import ProfileCollection
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table
from mtools.util import OrderedDict

from operator import itemgetter

import numpy as np

class QuerySection(BaseSection):
    """ 
    """
    
    name = "queries"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --queries flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--queries', action='store_true', help='outputs statistics about query patterns')
        self.mloginfo.argparser_sectiongroup.add_argument('--sort', action='store', default='sum', choices=['namespace', 'pattern', 'count', 'min', 'max', 'mean', '95%', 'sum'])

    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['queries']


    def run(self):
        """ run this section and print out information. """
        grouping = Grouping(group_by=lambda x: (x.namespace, x.pattern))
        logfile = self.mloginfo.logfile

        if logfile.start and logfile.end:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = self.mloginfo._datetime_to_epoch(logfile.end) - progress_start
        else:
            self.mloginfo.progress_bar_enabled = False


        for i, le in enumerate(logfile):
            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if le.datetime:
                    progress_curr = self.mloginfo._datetime_to_epoch(le.datetime)
                    self.mloginfo.update_progress(float(progress_curr-progress_start) / progress_total)

            if le.operation in ['query', 'update', 'remove']:
                grouping.add(le)

        grouping.sort_by_size()

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        titles = ['namespace', 'pattern', 'count', 'min (ms)', 'max (ms)', 'mean (ms)', '95%-ile (ms)', 'sum (ms)']
        table_rows = []
        for g in grouping:
            # calculate statistics for this group
            namespace, pattern = g

            group_events = [le.duration for le in grouping[g] if le.duration != None]

            stats = OrderedDict()
            stats['namespace'] = namespace
            stats['pattern'] = pattern
            stats['count'] = len( group_events )
            stats['min'] = min( group_events ) if group_events else '-'
            stats['max'] = max( group_events ) if group_events else '-'
            stats['mean'] = 0
            stats['95%'] = np.percentile(group_events, 95)
            stats['sum'] = sum( group_events ) if group_events else '-'
            stats['mean'] = stats['sum'] / stats['count'] if group_events else '-'

            if self.mloginfo.args['verbose']:
                stats['example'] = grouping[g][0]
                titles.append('example')

            table_rows.append(stats)

        # sort order depending on field names
        reverse = True
        if self.mloginfo.args['sort'] in ['namespace', 'pattern']:
            reverse = False

        table_rows = sorted(table_rows, key=itemgetter(self.mloginfo.args['sort']), reverse=reverse)
        print_table(table_rows, titles, uppercase_headers=False)
        print 


########NEW FILE########
__FILENAME__ = restart_section
from base_section import BaseSection

from mtools.util.profile_collection import ProfileCollection

class RestartSection(BaseSection):
    """ This section determines if there were any restarts in the log file and prints out
        the times and version of the restarts found. It uses the information collected in
        LogFile so it doesn't have to walk the file manually.
    """
    
    name = "restarts"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--restarts', action='store_true', help='outputs information about every detected restart')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['restarts']


    def run(self):

        if isinstance(self.mloginfo.logfile, ProfileCollection):
            print
            print "    not available for system.profile collections"
            print
            return

        """ run this section and print out information. """
        for version, logevent in self.mloginfo.logfile.restarts:
            print "   %s version %s" % (logevent.datetime.strftime("%b %d %H:%M:%S"), version)

        if len(self.mloginfo.logfile.restarts) == 0:
            print "  no restarts found"

########NEW FILE########
__FILENAME__ = mlogmerge
#!/usr/bin/env python

print "deprecated since version 1.1.0 of mtools. Use 'mlogfilter <logfile> <logfile> ...' instead."
########NEW FILE########
__FILENAME__ = mlogversion
#!/usr/bin/env python

print "deprecated since version 1.1.0 of mtools. Use 'mloginfo <logfile>' instead."

########NEW FILE########
__FILENAME__ = mlogvis
#!/usr/bin/env python

from mtools.util.logevent import LogEvent
from mtools.util.cmdlinetool import LogFileTool
import mtools

import os
import webbrowser


class MLogVisTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)

        self.argparser.description = 'mongod/mongos log file visualizer (browser edition). Extracts \
            information from each line of the log file and outputs a html file that can be viewed in \
            a browser. Automatically opens a browser tab and shows the file.'

    def _export(self, with_line_str=True):
        fields = ['_id', 'datetime', 'operation', 'thread', 'namespace', 'nscanned', 'nreturned', 'duration', 'numYields', 'w', 'r']
        if with_line_str:
            fields.append('line_str')

        first_row = True
        result_str = ''
        out_count = 0
        for line_no, logevent in enumerate(self.args['logfile']):
            # only export lines that have a datetime and duration
            if logevent.duration != None and logevent.datetime:
                out_count += 1
                # if too many lines include a line_str, the page won't load
                if with_line_str and out_count > 10000:
                    print "Warning: more than 10,000 data points detected. Skipping actual log line strings for faster plotting."
                    return False
                # write log line out as json
                if not first_row:
                    # prepend comma and newline
                    result_str += ',\n'
                else:
                    first_row = False
                # hack to include _id for log lines from file
                logevent._id = line_no
                result_str += logevent.to_json(fields)
        return result_str
        

    def run(self, arguments=None):
        LogFileTool.run(self, arguments)

        # store in current local folder
        mlogvis_dir = '.'

        # change stdin logfile name and remove the < >
        logname = self.args['logfile'].name
        if logname == '<stdin>':
            logname = 'stdin'

        os.chdir(mlogvis_dir)

        data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
        srcfilelocation = os.path.join(data_path, 'index.html')
        
        json_docs = self._export(True)
        if not json_docs:
            json_docs = self._export(False)

        outf = '{"type": "duration", "logfilename": "' + logname + '", "data":[' + json_docs + ']}'

        dstfilelocation = os.path.join(os.getcwd(), '%s.html'%logname)

        print "copying %s to %s" % (srcfilelocation, dstfilelocation)

        srcfile = open(srcfilelocation)
        contents = srcfile.read()
        srcfile.close()

        dstfile = open(dstfilelocation, 'wt')
        replaced_contents = contents.replace('##REPLACE##', outf)
        dstfile.write(replaced_contents)
        dstfile.close()

        print "serving visualization on file://"+dstfilelocation

        webbrowser.open("file://"+dstfilelocation)


if __name__ == '__main__':
    tool = MLogVisTool()
    tool.run()

########NEW FILE########
__FILENAME__ = mplotqueries
#!/usr/bin/env python

import argparse
import re
import os
import sys
import uuid
import glob
import cPickle
import types
import inspect

from copy import copy
from mtools import __version__
from datetime import timedelta

try:
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter, date2num
    from matplotlib.lines import Line2D
    from matplotlib.text import Text
    from matplotlib import __version__ as mpl_version
    import mtools.mplotqueries.plottypes as plottypes
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries that visualizes the logfile in a web browser.")


from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile

from mtools.util.cmdlinetool import LogFileTool

class MPlotQueriesTool(LogFileTool):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)

        self.argparser.description='A script to plot various information from logfiles. ' \
            'Clicking on any of the plot points will print the corresponding log line to stdout.'

        # disable some default shortcuts
        plt.rcParams['keymap.xscale'] = ''
        plt.rcParams['keymap.yscale'] = ''

        # import all plot type classes in plottypes module
        self.plot_types = [c[1] for c in inspect.getmembers(plottypes, inspect.isclass)]
        self.plot_types = dict((pt.plot_type_str, pt) for pt in self.plot_types)
        self.plot_instances = []

        # main parser arguments
        self.argparser.add_argument('--logscale', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        self.argparser.add_argument('--overlay', action='store', nargs='?', default=None, const='add', choices=['add', 'list', 'reset'], help="create combinations of several plots. Use '--overlay' to create an overlay (this will not plot anything). The first call without '--overlay' will additionally plot all existing overlays. Use '--overlay reset' to clear all overlays.")
        self.argparser.add_argument('--type', action='store', default='scatter', choices=self.plot_types.keys(), help='type of plot (default=scatter with --yaxis duration).')        
        self.argparser.add_argument('--title', action='store', default=None, help='change the title of the plot (default=filename(s))')        
        self.argparser.add_argument('--group', help="specify value to group on. Possible values depend on type of plot. All basic plot types can group on 'namespace', 'operation', 'thread', 'pattern', range and histogram plots can additionally group on 'log2code'. The group can also be a regular expression.")
        self.argparser.add_argument('--group-limit', metavar='N', type=int, default=None, help="specify an upper limit of the number of groups. Groups are sorted by number of data points. If limit is specified, only the top N will be listed separately, the rest are grouped together in an 'others' group")
        self.argparser.add_argument('--no-others', action='store_true', default=False, help="if this flag is used, the 'others' group (see --group-limit) will be discarded.")
        self.argparser.add_argument('--optime-start', action='store_true', default=False, help="plot operations with a duration when they started instead (by subtracting the duration). The default is to plot them when they finish (at the time they are logged).")

        self.legend = None

        # progress bar
        self.progress_bar_enabled = not self.is_stdin


    def run(self, arguments=None):
        LogFileTool.run(self, arguments, get_unknowns=True)

        self.parse_logevents()
        self.group()

        if self.args['overlay'] == 'reset':
            self.remove_overlays()

        # if --overlay is set, save groups in a file, else load groups and plot
        if self.args['overlay'] == "list":
            self.list_overlays()
            raise SystemExit

        plot_specified = not sys.stdin.isatty() or len(self.args['logfile']) > 0

        # if no plot is specified (either pipe or filename(s)) and reset, quit now
        if not plot_specified and self.args['overlay'] == 'reset':
            raise SystemExit
        
        if self.args['overlay'] == "" or self.args['overlay'] == "add":
            if plot_specified:
                self.save_overlay()
            else:
                print "Nothing to plot."
            raise SystemExit

        # else plot (with potential overlays) if there is something to plot
        overlay_loaded = self.load_overlays()
        
        if plot_specified or overlay_loaded:
            self.plot()
        else:
            print "Nothing to plot."
            raise SystemExit


    def parse_logevents(self):
        multiple_files = False

        # create generator for logfile(s) handles
        if type(self.args['logfile']) != types.ListType:
            self.logfiles = [self.args['logfile']]
        else:
            self.logfiles = self.args['logfile']
            
        if len(self.logfiles) > 1:
            # force "logfile" to be the group key for multiple files
            multiple_files = True
            self.args['group'] = 'filename'
        
        plot_instance = self.plot_types[self.args['type']](args=self.args, unknown_args=self.unknown_args)

        for logfile in self.logfiles:
            
            # get log file information
            if self.progress_bar_enabled:
                if logfile.start and logfile.end:
                    progress_start = self._datetime_to_epoch(logfile.start)
                    progress_total = self._datetime_to_epoch(logfile.end) - progress_start
                else:
                    self.progress_bar_enabled = False
                
                if progress_total == 0:
                    # protect from division by zero errors
                    self.progress_bar_enabled = False

            for i, logevent in enumerate(logfile):

                # adjust times if --optime-start is enabled
                if self.args['optime_start'] and logevent.duration != None and logevent.datetime:
                    # create new variable end_datetime in logevent object and store starttime there
                    logevent.end_datetime = logevent.datetime 
                    logevent._datetime = logevent._datetime - timedelta(milliseconds=logevent.duration)
                    logevent._datetime_calculated = True

                # update progress bar every 1000 lines
                if self.progress_bar_enabled and (i % 1000 == 0) and logevent.datetime:
                    progress_curr = self._datetime_to_epoch(logevent.datetime)
                    self.update_progress(float(progress_curr-progress_start) / progress_total, 'parsing %s'%logfile.name)

                # offer plot_instance and see if it can plot it
                if plot_instance.accept_line(logevent):
                    
                    # if logevent doesn't have datetime, skip
                    if logevent.datetime == None:
                        continue
                    
                    if logevent.namespace == None:
                        logevent._namespace = "None"

                    plot_instance.add_line(logevent)

                if multiple_files:
                    # amend logevent object with filename for group by filename
                    logevent.filename = logfile.name


            # store start and end for each logfile (also works for system.profile and stdin stream)
            plot_instance.date_range = (logfile.start, logfile.end)

        # clear progress bar
        if self.logfiles and self.progress_bar_enabled:
            self.update_progress(1.0)

        self.plot_instances.append(plot_instance)


    def group(self):
        self.plot_instances = [pi for pi in self.plot_instances if not pi.empty]
        for plot_inst in self.plot_instances:
            plot_inst.group()

    
    def list_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        print "Existing overlays:"
        for f in target_files:
            print "  ", os.path.basename(f)


    def save_overlay(self):
        # make directory if not present
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path)
            except OSError:
                SystemExit("Couldn't create directory %s, quitting. Check permissions, or run without --overlay to display directly." % overlay_path)

        # create unique filename
        while True:
            uid = str(uuid.uuid4())[:8]
            target_file = os.path.join(target_path, uid)
            if not os.path.exists(target_file):
                break

        # dump plots and handle exceptions
        try:
            cPickle.dump(self.plot_instances, open(target_file, 'wb'), -1)
            print "Created overlay: %s" % uid
        except Exception as e:
            print "Error: %s" % e
            SystemExit("Couldn't write to %s, quitting. Check permissions, or run without --overlay to display directly." % target_file)


    def load_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return False

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        for f in target_files:
            try:
                overlay = cPickle.load(open(f, 'rb'))
            except Exception as e:
                print "Couldn't read overlay %s, skipping." % f
                continue

            # extend each list according to its key
            self.plot_instances.extend(overlay)
            # for key in group_dict:
            #     self.groups.setdefault(key, list()).extend(group_dict[key])
            
            print "Loaded overlay: %s" % os.path.basename(f)
        
        if len(target_files) > 0:
            print

        return len(target_files) > 0


    def remove_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return 0

        target_files = glob.glob(os.path.join(target_path, '*'))
        # remove all group files
        for f in target_files:
            try:
                os.remove(f)
            except OSError as e:
                print "Error occured when deleting %s, skipping."
                continue

        if len(target_files) > 0:
            print "Deleted overlays."          


    def print_shortcuts(self):
        print "\nkeyboard shortcuts (focus must be on figure window):\n"

        print "    %8s  %s" % ("p", "switch to pan mode")
        print "    %8s  %s" % ("o", "switch to zoom mode")
        print "    %8s  %s" % ("left/right", "back / forward")
        print "    %8s  %s" % ("h", "home (original view)")
        print "    %8s  %s" % ("l", "toggle log/linear y-axis")
        print "    %8s  %s" % ("f", "toggle fullscreen")
        print "    %8s  %s" % ("1-9", "toggle visibility of top 10 individual plots 1-9")
        print "    %8s  %s" % ("0", "toggle visibility of all plots")
        print "    %8s  %s" % ("-", "toggle visibility of legend")
        print "    %8s  %s" % ("g", "toggle grid")
        print "    %8s  %s" % ("c", "toggle 'created with' footnote")
        print "    %8s  %s" % ("s", "save figure")
        print "    %8s  %s" % ("q", "quit mplotqueries")

        print


    def onpick(self, event):
        """ this method is called per artist (group), with possibly
            a list of indices.
        """   
        if hasattr(event.artist, '_mt_legend_item'):
            # legend item, instead of data point
            idx = event.artist._mt_legend_item
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass
            return

        # only print logevents of visible points
        if not event.artist.get_visible():
            return

        # get PlotType and let it print that event
        plot_type = event.artist._mt_plot_type
        plot_type.clicked(event)


    def toggle_artist(self, artist):
        try:
            visible = artist.get_visible()
            artist.set_visible(not visible)
            plt.gcf().canvas.draw()
        except Exception:
            pass


    def onpress(self, event):
        # number keys
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key)-1
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass

        # 0, toggle all plots
        if event.key == '0':
            try:
                visible = any([a.get_visible() for a in self.artists])
            except AttributeError:
                return

            for artist in self.artists:
                artist.set_visible(not visible)
            plt.gcf().canvas.draw()

        # quit
        if event.key == 'q':
            raise SystemExit('quitting.')

        # toggle legend
        if event.key == '-':
            if self.legend:
                self.toggle_artist(self.legend)
                plt.gcf().canvas.draw()

        # toggle created footnote
        if event.key == 'c':
            self.toggle_artist(self.footnote)
            plt.gcf().canvas.draw()

        # toggle yaxis logscale
        if event.key == 'l':
            scale = plt.gca().get_yscale()
            if scale == 'linear':
                plt.gca().set_yscale('log')
            else:
                plt.gca().set_yscale('linear')

            plt.autoscale(True, axis='y', tight=True)
            plt.gcf().canvas.draw()


    def plot(self):
        # check if there is anything to plot
        if len(self.plot_instances) == 0:
            raise SystemExit('no data to plot.')

        self.artists = []
        plt.figure(figsize=(12,8), dpi=100, facecolor='w', edgecolor='w')
        axis = plt.subplot(111)

        # set xlim from min to max of logfile ranges
        xlim_min = min([pi.date_range[0] for pi in self.plot_instances])
        xlim_max = max([pi.date_range[1] for pi in self.plot_instances])

        if xlim_max < xlim_min:
            raise SystemExit('no data to plot.')

        xlabel = 'time'
        ylabel = ''
        for i, plot_inst in enumerate(sorted(self.plot_instances, key=lambda pi: pi.sort_order)):
            self.artists.extend(plot_inst.plot(axis, i, len(self.plot_instances), (xlim_min, xlim_max) ))
            if hasattr(plot_inst, 'xlabel'):
                xlabel = plot_inst.xlabel
            if hasattr(plot_inst, 'ylabel'):
                ylabel = plot_inst.ylabel
        self.print_shortcuts()

        axis.set_xlabel(xlabel)
        axis.set_xticklabels(axis.get_xticks(), rotation=90, fontsize=10)
        axis.xaxis.set_major_formatter(DateFormatter('%b %d\n%H:%M:%S'))

        for label in axis.get_xticklabels():  # make the xtick labels pickable
            label.set_picker(True)
            
        axis.set_xlim(date2num([xlim_min, xlim_max]))

        # ylabel for y axis
        if self.args['logscale']:
            ylabel += ' (log scale)'
        axis.set_ylabel(ylabel)

        # title and mtools link
        axis.set_title(self.args['title'] or ', '.join([l.name for l in self.logfiles if l.name != '<stdin>']))
        plt.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.95)
        self.footnote = plt.annotate('created with mtools v%s: https://github.com/rueckstiess/mtools' % __version__, (10, 10), xycoords='figure pixels', va='bottom', fontsize=8)

        handles, labels = axis.get_legend_handles_labels()
        if len(labels) > 0:
            # only change fontsize if supported 
            major, minor, _ = mpl_version.split('.')
            if (int(major), int(minor)) >= (1, 3):
                self.legend = axis.legend(loc='upper left', frameon=False, numpoints=1, fontsize=9)
            else:
                self.legend = axis.legend(loc='upper left', frameon=False, numpoints=1)
        
        if self.args['type'] == 'scatter':
            # enable legend picking for scatter plots
            for i, legend_line in enumerate(self.legend.get_lines()):
                legend_line.set_picker(10)
                legend_line._mt_legend_item = i

        plt.gcf().canvas.mpl_connect('pick_event', self.onpick)
        plt.gcf().canvas.mpl_connect('key_press_event', self.onpress)
        plt.show()


if __name__ == '__main__':
    tool = MPlotQueriesTool()
    tool.run()



########NEW FILE########
__FILENAME__ = base_type
from mtools.util import OrderedDict
from mtools.util.log2code import Log2CodeConverter
from mtools.util.grouping import Grouping

import re
from datetime import MINYEAR, MAXYEAR, datetime, timedelta
import types

try:
    from matplotlib import cm
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries that visualizes the logfile in a web browser.")

class BasePlotType(object):

    # 14 most distinguishable colors, according to 
    # http://stackoverflow.com/questions/309149/generate-distinctly-different-rgb-colors-in-graphs
    colors = ['#000000','#00FF00','#0000FF','#FF0000','#01FFFE','#FFA6FE','#FFDB66','#006401', \
              '#010067','#95003A','#007DB5','#FF00F6','#FFEEE8','#774D00']
    color_index = 0
    markers = ['o', 's', '<', 'D']
    marker_index = 0

    sort_order = 0
    plot_type_str = 'base'
    default_group_by = None
    date_range = (datetime(MAXYEAR, 12, 31), datetime(MINYEAR, 1, 1))


    def __init__(self, args=None, unknown_args=None):
        self.args = args
        self.unknown_args = unknown_args
        self.groups = OrderedDict()
        self.empty = True
        self.limits = None

        if self.args['optime_start']:
            self.xlabel = 'time (start of ops)'
        else:
            self.xlabel = 'time (end of ops)'


    def accept_line(self, logevent):
        """ return True if this PlotType can plot this line. """
        return True

    def add_line(self, logevent):
        """ append log line to this plot type. """
        key = None
        self.empty = False
        self.groups.setdefault(key, list()).append(logevent)

    @property 
    def logevents(self):
        """ iterator yielding all logevents from groups dictionary. """
        for key in self.groups:
            for logevent in self.groups[key]:
                yield logevent

    @classmethod
    def color_map(cls, group):
        color = cls.colors[cls.color_index]
        cls.color_index += 1

        marker = cls.markers[cls.marker_index]
        if cls.color_index >= len(cls.colors):
            cls.marker_index += 1
            cls.marker_index %= len(cls.markers)
            cls.color_index %= cls.color_index

        return color, marker


    def group(self):
        """ (re-)group all logevents by the given group. """
        if hasattr(self, 'group_by'):
            group_by = self.group_by
        else:
            group_by = self.default_group_by
            if self.args['group'] != None:
                group_by = self.args['group']

        self.groups = Grouping(self.logevents, group_by)
        self.groups.move_items(None, 'others')
        self.groups.sort_by_size(group_limit=self.args['group_limit'], discard_others=self.args['no_others'])

    def plot_group(self, group, idx, axis):
        raise NotImplementedError("BasePlotType can't plot. Use a derived class instead")


    def clicked(self, event):
        """ this is called if an element of this plottype was clicked. Implement in sub class. """
        pass


    def plot(self, axis, ith_plot, total_plots, limits):
        self.limits = limits

        artists = []
        print self.plot_type_str.upper(), "plot"
        print "%5s %9s  %s"%("id", " #points", "group")

        for idx, group in enumerate(self.groups):
            print "%5s %9s  %s"%(idx+1, len(self.groups[group]), group)
            group_artists = self.plot_group(group, idx+ith_plot, axis)
            if isinstance(group_artists, list):
                artists.extend(group_artists)
            else:
                artists.append(group_artists)

        print

        return artists


########NEW FILE########
__FILENAME__ = connchurn_type
from mtools.mplotqueries.plottypes.base_type import BasePlotType
import argparse
import types
import re
import numpy as np

try:
    from matplotlib.dates import date2num, num2date
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


from mtools.util.log2code import Log2CodeConverter


def opened_closed(logevent):
    """ inspects a log line and groups it by connection being openend or closed. If neither, return False. """
    if "connection accepted" in logevent.line_str:
        return "opened"
    elif "end connection" in logevent.line_str:
        return "closed"
    else:
        return False

class ConnectionChurnPlotType(BasePlotType):
    """ plots a histogram plot over all logevents. The bucket size can be specified with the --bucketsize or -b parameter. Unit is in seconds. """

    plot_type_str = 'connchurn'
    timeunits = {'sec':1, 's':1, 'min':60, 'm':1, 'hour':3600, 'h':3600, 'day':86400, 'd':86400}
    sort_order = 1


    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        argparser = argparse.ArgumentParser("mplotqueries --type histogram")
        argparser.add_argument('--bucketsize', '-b', action='store', metavar='SIZE', help="histogram bucket size in seconds", default=60)
        sub_args = vars(argparser.parse_args(unknown_args))

        self.logscale = args['logscale']
        # get bucket size, either as int (seconds) or as string (see timeunits above)
        bs = sub_args['bucketsize']
        try:
            self.bucketsize = int(bs)
        except ValueError:
            self.bucketsize = self.timeunits[bs]

        self.ylabel = "# connections opened/closed"

        self.group_by = opened_closed

    def accept_line(self, logevent):
        """ only return lines with 'connection accepted' or 'end connection'. """
        return opened_closed(logevent)


    def plot_group(self, group, idx, axis):

        x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )
        color, _ = self.color_map(group)

        xmin, xmax = date2num(self.limits)
        n_bins = max(1, int((xmax - xmin)*24.*60.*60./self.bucketsize))
        if n_bins > 1000:
            # warning for too many buckets
            print "warning: %i buckets, will take a while to render. consider increasing --bucketsize." % n_bins

        bins = np.linspace(xmin, xmax, n_bins)

        n, bins, artists = axis.hist(x, bins=bins, align='mid', log=self.logscale, histtype="bar", color=color, 
            edgecolor="white", alpha=0.7, picker=True, label="# connections %s per bin" % group)

        if group == 'closed':
            ymin = 0
            for a in artists:
                    height = a.get_height()
                    height = -height
                    a.set_height(height)
                    if height < ymin: 
                        ymin = height
        
            axis.set_ylim(bottom = ymin*1.1) 
        
        elif group == 'opened':
            self.ymax = max([a.get_height() for a in artists])

        for num_conn, bin, artist in zip(n, bins, artists):
            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_n = num_conn
            artist._mt_bin = bin

        return artists


    def plot_total_conns(self, axis):
        opened = self.groups['opened']
        closed = self.groups['closed']

        total = sorted(opened+closed, key=lambda le: le.datetime)
        x = date2num( [ logevent.datetime for logevent in total ] )
        
        try:
            conns = [int(re.search(r'(\d+) connections? now open', le.line_str).group(1)) for le in total]
        except AttributeError:
            # hack, v2.0.x doesn't have this information
            axis.set_ylim(top = self.ymax*1.1) 
            return 

        axis.plot(x, conns, '-', color='black', linewidth=2, alpha=0.7, label='# open connections total')

        self.ymax = max(self.ymax, max(conns))
        axis.set_ylim(top = self.ymax*1.1) 


    def plot(self, axis, ith_plot, total_plots, limits):
        artists = BasePlotType.plot(self, axis, ith_plot, total_plots, limits)

        # parse all groups and plot currently open number of connections
        artist = self.plot_total_conns(axis)
        artists.append(artist)

        return artists


    @classmethod
    def color_map(cls, group):
        """ change default color behavior to map certain states always to the same colors (similar to MMS). """
        colors = {'opened': 'green', 'closed':'red', 'total':'black'}
        return colors[group], cls.markers[0]


    def clicked(self, event):
        """ print group name and number of items in bin. """
        group = event.artist._mt_group
        n = event.artist._mt_n
        dt = num2date(event.artist._mt_bin)
        print "%4i connections %s in %s sec beginning at %s" % (n, group, self.bucketsize, dt.strftime("%b %d %H:%M:%S"))


########NEW FILE########
__FILENAME__ = event_type
from mtools.mplotqueries.plottypes.base_type import BasePlotType

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")
    
class EventPlotType(BasePlotType):

    plot_type_str = 'event'

    def plot_group(self, group, idx, axis):
        x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )

        # event plots use axvline
        artists = []
        color, marker = self.color_map(group)

        for i, xcoord in enumerate(x):
            if i == 0:
                artist = axis.axvline(xcoord, linewidth=2, picker=5, color=color, alpha=0.7, label=group)
            else:
                artist = axis.axvline(xcoord, linewidth=2, picker=5, color=color, alpha=0.7)
            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_line_id = i
            artists.append(artist)

        axis.autoscale_view(scaley=False)
        return artists

    def clicked(self, event):
        group = event.artist._mt_group
        line_id = event.artist._mt_line_id
        print self.groups[group][line_id].line_str


class RSStatePlotType(EventPlotType):
    """ This plot type derives from the event plot type (vertical lines), but instead of
        plotting arbitrary events, it will only accept lines that indicate a replica set change.

        Those lines either contain the string "is now in state" (for other members) or are
        of the form "[rsMgr] replSet PRIMARY" for own state changes. 

        A custom group_by method 'lastword()' groups those lines by their last word (which is
        representative of the new state) and an overloaded color_map() method assigns colors
        to each of those states, similar to the ones used in MMS.
    """

    plot_type_str = 'rsstate'

    # force group() to always use lastword method to group by
    # group_by = 'lastword'

    colors = ['m', 'y', 'r', 'g', 'g', 'k', 'b', 'c']
    states = ['PRIMARY', 'SECONDARY', 'DOWN', 'STARTUP', 'STARTUP2', 'RECOVERING', 'ROLLBACK', 'ARBITER']

    
    def accept_line(self, logevent):
        """ only match log lines containing 'is now in state' (reflects other node's state changes) 
            or of type "[rsMgr] replSet PRIMARY" (reflects own state changes). 
        """
        if "is now in state" in logevent.line_str and logevent.split_tokens[-1] in self.states:
            return True

        if "replSet" in logevent.line_str and logevent.thread == "rsMgr" and logevent.split_tokens[-1] in self.states:
            return True

        return False


    def group_by(self, logevent):
        """ group by the last token of the log line (PRIMARY, SECONDARY, ...) """
        return logevent.split_tokens[-1]


    @classmethod
    def color_map(cls, group):
        print "Group", group
        """ change default color behavior to map certain states always to the same colors (similar to MMS). """
        try:
            state_idx = cls.states.index(group)
        except ValueError:
            # on any unexpected state, return black
            state_idx = 5
        return cls.colors[state_idx], cls.markers[0]

########NEW FILE########
__FILENAME__ = histogram_type
from mtools.mplotqueries.plottypes.base_type import BasePlotType
import argparse
import types
import numpy as np

try:
    from matplotlib.dates import date2num, num2date
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


from mtools.util.log2code import Log2CodeConverter


class HistogramPlotType(BasePlotType):
    """ plots a histogram plot over all logevents. The bucket size can be specified with the --bucketsize or -b parameter. Unit is in seconds. """

    plot_type_str = 'histogram'
    timeunits = {'sec':1, 's':1, 'min':60, 'm':1, 'hour':3600, 'h':3600, 'day':86400, 'd':86400}
    sort_order = 1
    default_group_by = 'namespace'
    l2cc = Log2CodeConverter()

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        argparser = argparse.ArgumentParser("mplotqueries --type histogram")
        argparser.add_argument('--bucketsize', '-b', action='store', metavar='SIZE', help="histogram bucket size in seconds", default=60)
        argparser.add_argument('--no-stacked', action='store_true', help="switch graph mode from stacked histogram (default) to side-by-side histograms.", default=False)
        sub_args = vars(argparser.parse_args(unknown_args))

        self.logscale = args['logscale']
        # get bucket size, either as int (seconds) or as string (see timeunits above)
        bs = sub_args['bucketsize']
        try:
            self.bucketsize = int(bs)
        except ValueError:
            self.bucketsize = self.timeunits[bs]
        self.barstacked = not sub_args['no_stacked']

        self.ylabel = "# lines per %i second bin" % self.bucketsize

    def accept_line(self, logevent):
        """ return True for each line. We bucket everything. Filtering has to be done before passing to this type of plot. """
        return True

    def log2code(self, logevent):
        codeline = self.l2cc(logevent.line_str)
        if codeline:
            return ' ... '.join(codeline.pattern)
        else:
            return None

    def plot_group(self, group, idx, axis):
        raise NotImplementedError("Not implemented for histogram plots.")


    def plot(self, axis, ith_plot, total_plots, limits):
        """ Plots the histogram as a whole over all groups, rather than individual groups like other plot types. """
        
        print self.plot_type_str.upper(), "plot"
        print "%5s %9s  %s"%("id", " #points", "group")

        for idx, group in enumerate(self.groups):
            print "%5s %9s  %s"%(idx+1, len(self.groups[group]), group)
        
        print 

        datasets = []
        colors = []
        minx = np.inf
        maxx = -np.inf

        for idx, group in enumerate(self.groups):
            x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )
            minx = min(minx, min(x))
            maxx = max(maxx, max(x))
            datasets.append(x)
            color, marker = self.color_map(group)
            colors.append(color)
        
        if total_plots > 1:
            # if more than one plot, move histogram to twin axis on the right
            twin_axis = axis.twinx()
            twin_axis.set_ylabel(self.ylabel)
            axis.set_zorder(twin_axis.get_zorder()+1) # put ax in front of ax2 
            axis.patch.set_visible(False) # hide the 'canvas' 
            axis = twin_axis

        n_bins = max(1, int((maxx - minx)*24.*60.*60./self.bucketsize))
        if n_bins > 1000:
            # warning for too many buckets
            print "warning: %i buckets, will take a while to render. consider increasing --bucketsize." % n_bins

        n, bins, artists = axis.hist(datasets, bins=n_bins, align='mid', log=self.logscale, histtype="barstacked" if self.barstacked else "bar", color=colors, edgecolor="none", linewidth=0, alpha=0.8, picker=True, label=map(str, self.groups.keys()))
        
        # scale current y-axis to match min and max values
        axis.set_ylim(np.min(n), np.max(n))

        # add meta-data for picking
        if len(self.groups) > 1:
            for g, group in enumerate(self.groups.keys()):
                for i in range(len(artists[g])):
                    artists[g][i]._mt_plot_type = self
                    artists[g][i]._mt_group = group
                    artists[g][i]._mt_n = n[g][i]
                    if self.barstacked:
                        artists[g][i]._mt_n -= (n[g-1][i] if g > 0 else 0)

                    artists[g][i]._mt_bin = bins[i]
        else:
            for i in range(len(artists)):
                artists[i]._mt_plot_type = self
                artists[i]._mt_group = group
                artists[i]._mt_n = n[i]
                artists[i]._mt_bin = bins[i]

        return artists

    def clicked(self, event):
        """ print group name and number of items in bin. """
        group = event.artist._mt_group
        n = event.artist._mt_n
        dt = num2date(event.artist._mt_bin)
        print "%4i %s events in %s sec beginning at %s" % (n, group, self.bucketsize, dt.strftime("%b %d %H:%M:%S"))


########NEW FILE########
__FILENAME__ = range_type
from mtools.mplotqueries.plottypes.base_type import BasePlotType
from datetime import timedelta
import argparse

try:
    from matplotlib.dates import date2num, num2date
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")
    
from mtools.util.log2code import Log2CodeConverter

class RangePlotType(BasePlotType):

    plot_type_str = 'range'
    sort_order = 2
    l2cc = Log2CodeConverter()

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        argparser = argparse.ArgumentParser("mplotqueries --type range")
        argparser.add_argument('--gap', action='store', metavar='SEC', type=int, help="gap threshold in seconds after which a new line is started (default: 60)", default=None)
        sub_args = vars(argparser.parse_args(unknown_args))

        self.gap = sub_args['gap']


    def accept_line(self, logevent):
        """ return True if the log line does not have a duration. """
        return True

    def log2code(self, logevent):
        codeline = self.l2cc(logevent.line_str)
        if codeline:
            return ' ... '.join(codeline.pattern)
        else:
            return None

    def plot_group(self, group, idx, axis):
        y_min, y_max = axis.get_ylim()

        if y_min == 0. and y_max == 1.:
            axis.set_ylim(0.0, 1.0)

        height = (y_max - y_min) / len(self.groups)
        y_bottom = y_min + (y_max-y_min) - idx * height

        x_lefts = [ date2num( self.groups[group][0].datetime ) ]
        x_rights = []

        if self.gap:
            td = timedelta(seconds=self.gap)
            for le, le_next in zip(self.groups[group][:-1], self.groups[group][1:]):
                if le_next.datetime - le.datetime >= td:
                    x_lefts.append( date2num(le_next.datetime) )
                    x_rights.append( date2num(le.datetime) )

        x_rights.append( date2num( self.groups[group][-1].datetime ) )

        color=self.colors[idx%len(self.colors)]
        
        artists = []

        for x_left, x_right in zip(x_lefts, x_rights):
            width = max(0.001, x_right-x_left)
            artist = axis.barh(y_bottom-0.5*height, width=width, height=0.7*height, left=x_left, color=color, alpha=0.7, edgecolor='white', picker=5, linewidth=1, align='center')[0]
            
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_left = x_left
            artist._mt_right = x_right

            artists.append(artist)

        if len(self.groups) < 50:
            axis.annotate(group, xy=(0, y_bottom-height/2.), xycoords='axes fraction', xytext=(-10, 0), textcoords='offset pixels', va='bottom', ha='right', fontsize=9)

        axis.axes.get_yaxis().set_visible(False)

        return artists

    def clicked(self, event):
        group = event.artist._mt_group
        print num2date(event.artist._mt_left).strftime("%a %b %d %H:%M:%S"), '-', num2date(event.artist._mt_right).strftime("%a %b %d %H:%M:%S")



########NEW FILE########
__FILENAME__ = scatter_type
from mtools.mplotqueries.plottypes.base_type import BasePlotType
from operator import itemgetter
from datetime import timedelta

import argparse

try:
    import matplotlib.pyplot as plt

    from matplotlib.dates import date2num
    from matplotlib.lines import Line2D
    from matplotlib.patches import Polygon

except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


class ScatterPlotType(BasePlotType):

    plot_type_str = 'scatter'
    sort_order = 3
    default_group_by = 'namespace'

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        self.logscale = args['logscale']

        # parse arguments further to get --yaxis argument
        argparser = argparse.ArgumentParser("mplotqueries --type scatter")
        argparser.add_argument('--yaxis', '-y', action='store', metavar='FIELD', default='duration')
        args = vars(argparser.parse_args(unknown_args))

        self.field = args['yaxis']
        if args['yaxis'] == 'duration':
            self.ylabel = 'duration in ms'
        else:
            self.ylabel = args['yaxis']

        self.durlines = []


    def accept_line(self, logevent):
        """ return True if the log line has the nominated yaxis field. """
        return (getattr(logevent, self.field) != None)

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ getattr(logevent, self.field) for logevent in self.groups[group] ]
        
        if self.logscale:
            axis.semilogy()

        artist = axis.plot_date(x, y, color=color, markeredgecolor='k', marker=marker, alpha=0.7, \
            markersize=7, picker=5, label=group)[0]
        # add meta-data for picking
        artist._mt_plot_type = self
        artist._mt_group = group 

        return artist

    def clicked(self, event):
        """ this is called if an element of this plottype was clicked. Implement in sub class. """        
        group = event.artist._mt_group
        indices = event.ind

        if not event.mouseevent.dblclick:
            for i in indices:
                print self.groups[group][i].line_str

        else:
            # toggle durline
            first = indices[0]
            logevent = self.groups[group][first]

            try:
                # remove triangle for this event
                idx = map(itemgetter(0), self.durlines).index(logevent)
                _, poly = self.durlines[idx]
                poly.remove()
                plt.gcf().canvas.draw()
                del self.durlines[idx]

            except ValueError:
                # construct triangle and add to list of durlines

                if self.args['optime_start']:
                    pts = [ [date2num(logevent.datetime), 0], 
                            [date2num(logevent.datetime), logevent.duration], 
                            [date2num(logevent.datetime + timedelta(milliseconds=logevent.duration)), 0] ]
                else:
                    pts = [ [date2num(logevent.datetime), 0], 
                            [date2num(logevent.datetime), logevent.duration], 
                            [date2num(logevent.datetime - timedelta(milliseconds=logevent.duration)), 0] ]

                poly = Polygon(pts, closed=True, alpha=0.2, linewidth=0, facecolor=event.artist.get_markerfacecolor(), edgecolor=None, zorder=-10000)

                ax = plt.gca()
                ax.add_patch(poly)
                plt.gcf().canvas.draw()

                self.durlines.append( (logevent, poly) )



class DurationLineType(ScatterPlotType):

    plot_type_str = 'durline'
    sort_order = 3
    default_group_by = 'namespace'

    def __init__(self, args=None, unknown_args=None):
        ScatterPlotType.__init__(self, args, unknown_args)
        self.args['optime_start'] = True

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x_start = date2num( [ logevent.datetime for logevent in self.groups[group] ] )
        x_end = date2num( [ logevent.end_datetime for logevent in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ getattr(logevent, 'duration') for logevent in self.groups[group] ]
        
        if self.logscale:
            axis.semilogy()

        # artist = axis.plot_date(x, y, color=color, markeredgecolor='k', marker=marker, alpha=0.7, \
        #     markersize=7, picker=5, label=group)[0]
        
        artists = []
        labels = set()

        for i, (xs, xe, ye) in enumerate(zip(x_start, x_end, y)):
            artist = axis.plot_date([xs, xe], [0, ye], '-', color=color, alpha=0.7, linewidth=2,
            markersize=7, picker=5, label=None if group in labels else group)[0]
            
            labels.add(group)

            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group 
            artist._mt_line_id = i
            artists.append(artist)

        return artists


    def clicked(self, event):
        group = event.artist._mt_group
        line_id = event.artist._mt_line_id
        print self.groups[group][line_id].line_str



class NScannedNPlotType(ScatterPlotType):

    plot_type_str = 'nscanned/n'
    default_group_by = 'namespace'


    def __init__(self, args=None, unknown_args=None):
        # Only call baseplot type constructor, we don't need argparser
        BasePlotType.__init__(self, args, unknown_args)

        self.ylabel = 'nscanned / n ratio'

    def accept_line(self, logevent):
        """ return True if the log line has a duration. """
        return getattr(logevent, 'nscanned') and getattr(logevent, 'nreturned')

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        nreturned = float(logevent.nreturned)
        if nreturned == 0.0:
            nreturned = 1.0

        y = [ getattr(logevent, 'nscanned') / nreturned for logevent in self.groups[group] ]
        artist = axis.plot_date(x, y, color=color, marker=marker, alpha=0.5, \
            markersize=7, picker=5, label=group)[0]
        # add meta-data for picking
        artist._mt_plot_type = self
        artist._mt_group = group 

        return artist





########NEW FILE########
__FILENAME__ = test_all_help
import sys
from nose.tools import *
from mtools.test import all_tools
from mtools.version import __version__
import time

@all_tools
def test_help(tool_cls):
    """ Check that all command line tools have a --help option that explains the usage.
        As per argparse default, this help text always starts with `usage:`.
    """
    tool = tool_cls()
   
    try:
        tool.run("--help")

    except SystemExit as e:
        if not hasattr(sys.stdout, "getvalue"):
            raise Exception('stdout not captured in test.')
        output = sys.stdout.getvalue().strip()
        assert output.startswith('usage:')


@all_tools
def test_version(tool_cls):
    """ Check that all command line tools have a --version option that returns the current version. """

    tool = tool_cls()
   
    try:
        tool.run("--version")

    except SystemExit as e:
        if not hasattr(sys.stdout, "getvalue"):
            raise Exception('stdout not captured in test.')

        # argparse's --version outputs to stderr, which can't be captured with nosetests.
        # therefore just checking that the scripts run and not output anything to stdout 
        output = sys.stdout.getvalue().strip()
        assert len(output) == 0

########NEW FILE########
__FILENAME__ = test_all_import
from nose.tools import nottest, make_decorator
from functools import wraps

# tools without any external dependencies
from mtools.mlogfilter.mlogfilter import MLogFilterTool
from mtools.mlogvis.mlogvis import MLogVisTool
from mtools.mloginfo.mloginfo import MLogInfoTool

tools = [MLogFilterTool, MLogVisTool, MLogInfoTool]


# mlaunch depends on pymongo
try:
    from mtools.mlaunch.mlaunch import MLaunchTool
    tools.append(MLaunchTool)
except ImportError:
    pass


# mplotqueries depends on matplotlib
try:
    from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
    tools.append(MPlotQueriesTool)
except ImportError:
    pass


def all_tools(fn):
    """ This is a decorator for test functions, that runs a loop over all command line tool
        classes imported above and passes each class to the test function. 

        To use this decorator, the test function must accept a single parameter. Example:

        @all_tools
        def test_something(tool_cls):
            tool = tool_cls()
            # test tool here ...
    """
    @wraps(fn)     # copies __name__ of the original function, nose requires the name to start with "test_"
    def new_func():
        for tool in tools:
            fn(tool)
    return new_func


def test_import_all():
    """ Import all tools from mtools module.
        The tools that have external dependencies will only be imported if the dependencies are fulfilled. 
        This test just passes by defaultbecause the imports are tested implicitly by loading this file.
    """
    pass

########NEW FILE########
__FILENAME__ = test_mlaunch
import inspect
import shutil
import socket
import time
import os
import json
import sys
import json

from mtools.mlaunch.mlaunch import MLaunchTool, shutdown_host
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConnectionFailure
from bson import SON
from nose.tools import *
from nose.plugins.attrib import attr
from nose.plugins.skip import Skip, SkipTest


class TestMLaunch(object):
    """ This class tests functionality around the mlaunch tool. It has some
        additional methods that are helpful for the tests, as well as a setup
        and teardown method for all tests.

        Don't call tests from other tests. This won't work as each test gets
        its own data directory (for debugging).
    """

    port = 33333
    base_dir = 'data_test_mlaunch'


    def __init__(self):
        """ Constructor. """
        self.use_auth = False
        self.data_dir = ''
        

    def setup(self):
        """ start up method to create mlaunch tool and find free port """
        self.tool = MLaunchTool()

        # if the test data path exists, remove it
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)


    def teardown(self):
        """ tear down method after each test, removes data directory """        

        # kill all running processes
        self.tool.discover()

        ports = self.tool.get_tagged(['all', 'running'])
        processes = self.tool._get_processes().values()
        for p in processes:
            p.terminate()
            p.wait(10)

        self.tool.wait_for(ports, to_start=False)

        # quick sleep to avoid spurious test failures
        time.sleep(0.1)

        # if the test data path exists, remove it
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)


    def run_tool(self, arg_str):
        """ wrapper to call self.tool.run() with or without auth """
        # name data directory according to test method name
        caller = inspect.stack()[1][3]
        self.data_dir = os.path.join(self.base_dir, caller)

        # add data directory to arguments for all commands
        arg_str += ' --dir %s' % self.data_dir
        
        if arg_str.startswith('init') or arg_str.startswith('--'):
            # add --port and --nojournal to init calls
            arg_str += ' --port %i --nojournal --smallfiles' % self.port 
            
            if self.use_auth:
                # add --auth to init calls if flag is set
                arg_str += ' --auth'

        self.tool.run(arg_str)


    # -- tests below ---

    @raises(ConnectionFailure)
    def test_test(self):
        """ TestMLaunch setup and teardown test """

        # test that data dir does not exist
        assert not os.path.exists(self.data_dir)

        # start mongo process on free test port
        self.run_tool("init --single")

        # call teardown method within this test
        self.teardown()

        # test that data dir does not exist anymore
        assert not os.path.exists(self.data_dir)

        # test that mongod is not running on this port anymore (raises ConnectionFailure)
        mc = MongoClient('localhost:%i' % self.port)


    def test_argv_run(self):
        """ mlaunch: test true command line arguments, instead of passing into tool.run() """
        
        # make command line arguments through sys.argv
        sys.argv = ['mlaunch', 'init', '--single', '--dir', self.base_dir, '--port', str(self.port), '--nojournal']

        self.tool.run()
        assert self.tool.is_running(self.port)


    def test_init_default(self):
        """ mlaunch: test that 'init' command can be omitted, is default """

        # make command line arguments through sys.argv
        sys.argv = ['mlaunch', '--single', '--dir', self.base_dir, '--port', str(self.port), '--nojournal']

        self.tool.run()
        assert self.tool.is_running(self.port)


    def test_init_default_arguments(self):
        """ mlaunch: test that 'init' command is default, even when specifying arguments to run() """
        
        self.run_tool("--single")
        assert self.tool.is_running(self.port)


    def test_single(self):
        """ mlaunch: start stand-alone server and tear down again """

        # start mongo process on free test port
        self.run_tool("init --single")

        # make sure node is running
        assert self.tool.is_running(self.port)

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongod.log'))

        # check that the tags are set correctly: 'single', 'mongod', 'running', <port>
        assert set(self.tool.get_tags_of_port(self.port)) == set(['running', 'mongod', 'all', 'single', str(self.port)])



    def test_replicaset_conf(self):
        """ mlaunch: start replica set of 2 nodes + arbiter and compare rs.conf() """

        # start mongo process on free test port
        self.run_tool("init --replicaset --nodes 2 --arbiter")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/arb'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 3 members, exactly one is arbiter
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 3
        assert sum(1 for memb in conf['members'] if 'arbiterOnly' in memb and memb['arbiterOnly']) == 1


    @timed(60)
    @attr('slow')
    def test_replicaset_ismaster(self):
        """ mlaunch: start replica set and verify that first node becomes primary """

        # start mongo process on free test port
        self.run_tool("init --replicaset")

        # wait for primary
        assert self.tool._wait_for_primary()

        # insert a document and wait to replicate to 2 secondaries (10 sec timeout)
        mc = MongoClient('localhost:%i' % self.port)
        mc.test.smokeWait.insert({}, w=2, wtimeout=10*60*1000)


    def test_sharded_status(self):
        """ mlaunch: start cluster with 2 shards of single nodes, 1 config server """

        # start mongo process on free test port 
        self.run_tool("init --sharded 2 --single")
    
        # check if data directories and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'shard01/db'))
        assert os.path.exists(os.path.join(self.data_dir, 'shard02/db'))
        assert os.path.exists(os.path.join(self.data_dir, 'config/db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongos.log'))

        # create mongo client
        mc = MongoClient('localhost:%i' % (self.port))

        # check for 2 shards and 1 mongos
        assert mc['config']['shards'].count() == 2
        assert mc['config']['mongos'].count() == 1


    def helper_output_has_line_with(self, keywords, output):
        """ checks if output contains a line where all keywords are present. """
        return len( filter( None, [ all( [kw in line for kw in keywords] ) for line in output] ) )


    def test_verbose_sharded(self):
        """ mlaunch: test verbose output when creating sharded cluster """

        self.run_tool("init --sharded 2 --replicaset --config 3 --mongos 2 --verbose")

        # capture stdout
        output = sys.stdout.getvalue().splitlines()

        keywords = ('rs1', 'rs2', 'rs3', 'shard01', 'shard02', 'config1', 'config2', 'config3')

        # creating directory
        for keyword in keywords:
            # make sure every directory creation was announced to stdout
            assert self.helper_output_has_line_with(['creating directory', keyword, 'db'], output)

        assert self.helper_output_has_line_with(['creating directory', 'mongos'], output)

        # launching nodes
        for keyword in keywords:
            assert self.helper_output_has_line_with(['launching', keyword, '--port', '--logpath', '--dbpath'], output)

        # mongos
        assert self.helper_output_has_line_with(['launching', 'mongos', '--port', '--logpath', str(self.port)], output)
        assert self.helper_output_has_line_with(['launching', 'mongos', '--port', '--logpath', str(self.port + 1)], output)

        # some fixed outputs
        assert self.helper_output_has_line_with(['waiting for nodes to start'], output)
        assert self.helper_output_has_line_with(['adding shards. can take up to 30 seconds'], output)
        assert self.helper_output_has_line_with(['writing .mlaunch_startup file'], output)
        assert self.helper_output_has_line_with(['done'], output)

        # replica sets initialized, shard added
        for keyword in ('shard01', 'shard02'):
            assert self.helper_output_has_line_with(['replica set', keyword, 'initialized'], output)
            assert self.helper_output_has_line_with(['shard', keyword, 'added successfully'], output)



    def test_shard_names(self):
        """ mlaunch: test if sharded cluster with explicit shard names works """

        # start mongo process on free test port 
        self.run_tool("init --sharded tic tac toe --replicaset")

        # create mongo client
        mc = MongoClient('localhost:%i' % (self.port))

        # check that shard names match
        shard_names = set( doc['_id'] for doc in mc['config']['shards'].find() )
        assert shard_names == set(['tic', 'tac', 'toe'])


    def test_startup_file(self):
        """ mlaunch: create .mlaunch_startup file in data path """
        
        # Also tests utf-8 to byte conversion and json import

        self.run_tool("init --single -v")

        # check if the startup file exists
        startup_file = os.path.join(self.data_dir, '.mlaunch_startup')
        assert os.path.isfile(startup_file)

        # compare content of startup file with tool.args
        file_contents = self.tool._convert_u2b(json.load(open(startup_file, 'r')))
        assert file_contents['parsed_args'] == self.tool.args
        assert file_contents['unknown_args'] == self.tool.unknown_args


    def test_single_mongos_explicit(self):
        """ mlaunch: test if single mongos is running on start port and creates <datadir>/mongos.log """
        
        # start 2 shards, 1 config server, 1 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 1")

        # check if mongos log files exist on correct ports
        assert os.path.exists(os.path.join(self.data_dir, 'mongos.log'))

        # check for correct port
        assert self.tool.get_tagged('mongos') == set([self.port])


    def test_single_mongos(self):
        """ mlaunch: test if multiple mongos use separate log files in 'mongos' subdir """

        # start 2 shards, 1 config server, 2 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 1")

        # check that 2 mongos are running
        assert len( self.tool.get_tagged(['mongos', 'running']) ) == 1


    def test_multiple_mongos(self):
        """ mlaunch: test if multiple mongos use separate log files in 'mongos' subdir """

        # start 2 shards, 1 config server, 2 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 2")

        # this also tests that mongos are started at the beginning of the port range
        assert os.path.exists(os.path.join(self.data_dir, 'mongos', 'mongos_%i.log' % (self.port)))
        assert os.path.exists(os.path.join(self.data_dir, 'mongos', 'mongos_%i.log' % (self.port + 1)))

        # check that 2 mongos are running
        assert len( self.tool.get_tagged(['mongos', 'running']) ) == 2


    def test_filter_valid_arguments(self):
        """ mlaunch: check arguments unknown to mlaunch against mongos and mongod """

        # filter against mongod
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv --configdb localhost:27017 --foobar".split(), "mongod")
        assert result == "--slowms 500 -vvv"

        # filter against mongos
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv --configdb localhost:27017 --foobar".split(), "mongos")
        assert result == "-vvv --configdb localhost:27017"


    def test_large_replicaset_arbiter(self):
        """ mlaunch: start large replica set of 12 nodes with arbiter """

        # start mongo process on free test port (don't need journal for this test)
        self.run_tool("init --replicaset --nodes 11 --arbiter")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs3'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs4'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs5'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs6'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs7'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs8'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs9'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs10'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs11'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/arb'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 12 members, exactly one arbiter
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 12
        assert sum(1 for memb in conf['members'] if 'arbiterOnly' in memb and memb['arbiterOnly']) == 1

        # check that 12 nodes are discovered
        assert len(self.tool.get_tagged('all')) == 12


    def test_large_replicaset_noarbiter(self):
        """ mlaunch: start large replica set of 12 nodes without arbiter """

        # start mongo process on free test port (don't need journal for this test)
        self.run_tool("init --replicaset --nodes 12")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs3'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs4'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs5'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs6'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs7'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs8'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs9'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs10'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs11'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs12'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 12 members, no arbiters
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 12
        assert sum(1 for memb in conf['members'] if 'arbiterOnly' in memb and memb['arbiterOnly']) == 0


    def test_stop(self):
        """ mlaunch: test stopping all nodes """

        self.run_tool("init --replicaset")
        self.run_tool("stop")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )


    def test_kill(self):
        """ mlaunch: test killing all nodes """

        # start sharded cluster and kill with default signal (15)
        self.run_tool("init --sharded 2 --single")
        self.run_tool("kill")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )


        # start nodes again, this time, kill with string "SIGTERM"
        self.run_tool("start")
        self.run_tool("kill --signal SIGTERM")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )


        # start nodes again, this time, kill with signal 9 (SIGKILL)
        self.run_tool("start")
        self.run_tool("kill --signal 9")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )



    def test_stop_start(self):
        """ mlaunch: test stop and then re-starting nodes """

        # start mongo process on free test port
        self.run_tool("init --replicaset")
        self.run_tool("stop")
        time.sleep(1)
        self.run_tool("start")

        # make sure all nodes are running
        nodes = self.tool.get_tagged('all')
        assert all( self.tool.is_running(node) for node in nodes )

    
    @timed(180)
    @attr('slow')
    def test_kill_partial(self):
        """ mlaunch: test killing and restarting tagged groups on different tags """

        # key is tag for command line, value is tag for get_tagged
        tags = ['shard01', 'shard 1', 'mongos', 'config 1', str(self.port)] 

        # start large cluster
        self.run_tool("init --sharded 2 --replicaset --config 3 --mongos 3")

        # make sure all nodes are running
        nodes = self.tool.get_tagged('all')
        assert all( self.tool.is_running(node) for node in nodes )

        # go through all tags, stop nodes for each tag, confirm only the tagged ones are down, start again
        for tag in tags:
            print "---------", tag
            self.run_tool("kill %s" % tag)
            assert self.tool.get_tagged('down') == self.tool.get_tagged(tag)
            time.sleep(1)

            # short sleep, because travis seems to be sensitive and sometimes fails otherwise
            self.run_tool("start")
            assert len(self.tool.get_tagged('down')) == 0
            time.sleep(1)

        # make sure primaries are running again (we just failed them over above). 
        # while True is ok, because test times out after some time
        while True:
            primaries = self.tool.get_tagged('primary')
            if len(primaries) == 2:
                break
            time.sleep(1)
            self.tool.discover()

        # test for primary, but as the nodes lose their tags, needs to be manual
        self.run_tool("kill primary")
        assert len(self.tool.get_tagged('down')) == 2


    def test_restart_with_unkown_args(self):
        """ mlaunch: test start command with extra unknown arguments """

        # init environment (sharded, single shards ok)
        self.run_tool("init --single")
        
        # get verbosity of mongod, assert it is 0
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel', 1)]))
        assert loglevel[u'logLevel'] == 0

        # stop and start nodes but pass in unknown_args
        self.run_tool("stop")

        # short sleep, because travis seems to be sensitive and sometimes fails otherwise
        time.sleep(1)

        self.run_tool("start -vv")

        # compare that the nodes are restarted with the new unknown_args, assert loglevel is now 2
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel', 1)]))
        assert loglevel[u'logLevel'] == 2

        # stop and start nodes without unknown args again
        self.run_tool("stop")
        
        # short sleep, because travis seems to be sensitive and sometimes fails otherwise
        time.sleep(1)

        self.run_tool("start")

        # compare that the nodes are restarted with the previous loglevel
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel', 1)]))
        assert loglevel[u'logLevel'] == 0


    def test_start_stop_single_repeatedly(self):
        """ mlaunch: test starting and stopping single node in short succession """ 
        # repeatedly start single node
        self.run_tool("init --single")

        for i in range(10):
            self.run_tool("stop")

            # short sleep, because travis seems to be sensitive and sometimes fails otherwise
            time.sleep(1)

            self.run_tool("start")

    
    @raises(SystemExit)
    def test_init_init_replicaset(self):
        """ mlaunch: test calling init a second time on the replica set """

        # init a replica set
        self.run_tool("init --replicaset")

        # now stop and init again, this should work if everything is stopped and identical environment
        self.run_tool("stop")
        self.run_tool("init --replicaset")

        # but another init should fail with a SystemExit
        self.run_tool("init --replicaset")


    def test_start_stop_replicaset_repeatedly(self):
        """ mlaunch: test starting and stopping replica set in short succession """ 
        # repeatedly start replicaset nodes
        self.run_tool("init --replicaset")

        for i in range(10):
            self.run_tool("stop")

            # short sleep, because travis seems to be sensitive and sometimes fails otherwise
            time.sleep(1)

            self.run_tool("start")


    @attr('slow')
    @attr('auth')
    def test_repeat_all_with_auth(self):
        """ this test will repeat all the tests in this class (excluding itself) but with auth. """
        tests = [t for t in inspect.getmembers(self, predicate=inspect.ismethod) if t[0].startswith('test_') ]

        self.use_auth = True

        for name, method in tests:
            # don't call any tests that use auth already (tagged with 'auth' attribute), including this method
            if hasattr(method, 'auth'):
                continue

            setattr(method.__func__, 'description', method.__doc__.strip() + ', with auth.')
            yield ( method, )

        self.use_auth = False

    # TODO 
    # - test functionality of --binarypath, --verbose, --name

    # All tests that use auth need to be decorated with @attr('auth')


    def helper_adding_default_user(self, environment):
        """ This is a helper function for the next test: test_adding_default_user() """

        self.run_tool("init %s --auth" % environment)

        # connect and authenticate with default credentials: user / password on admin database
        mc = MongoClient('localhost:%i' % self.port)
        mc.admin.authenticate('user', password='password')

        # check if the user roles are correctly set to the default roles
        user = mc.admin.system.users.find_one()
        assert set(user['roles']) == set(self.tool._default_auth_roles)


    @attr('auth')
    def test_adding_default_user(self):
        envs = (
            "--single", 
            "--replicaset", 
            "--sharded 2 --single", 
            "--sharded 2 --replicaset",
            "--sharded 2 --single --config 3"
        )

        for env in envs:
            method = self.helper_adding_default_user
            setattr(method.__func__, 'description', method.__doc__.strip() + ', with ' + env)
            yield (method, env)


    @attr('auth')
    def test_adding_default_user_no_mongos(self):
        """ mlaunch: test that even with --mongos 0 there is a user created """

        self.run_tool("init --sharded 2 --single --mongos 0 --auth")

        # connect to config server instead to check for credentials (no mongos)
        ports = list(self.tool.get_tagged('config'))
        mc = MongoClient('localhost:%i' % ports[0])
        mc.admin.authenticate('user', password='password')

        # check if the user roles are correctly set to the default roles
        user = mc.admin.system.users.find_one()
        assert set(user['roles']) == set(self.tool._default_auth_roles)
      

    @attr('auth')
    def test_adding_custom_user(self):
        """ mlaunch: test custom username and password and custom roles. """

        self.run_tool("init --single --auth --username corben --password fitzroy --auth-roles dbAdminAnyDatabase readWriteAnyDatabase userAdminAnyDatabase")

        # connect and authenticate with default credentials: user / password on admin database
        mc = MongoClient('localhost:%i' % self.port)
        mc.admin.authenticate('corben', password='fitzroy')

        # check if the user roles are correctly set to the specified roles
        user = mc.admin.system.users.find_one()
        print user
        assert set(user['roles']) == set(["dbAdminAnyDatabase", "readWriteAnyDatabase", "userAdminAnyDatabase"])
        assert user['user'] == 'corben'


    def test_existing_environment(self):
        """ mlaunch: test warning for overwriting an existing environment """

        self.run_tool("init --single")
        self.run_tool("stop")
        try:
            self.run_tool("init --replicaset")
        except SystemExit as e:
            assert 'different environment already exists' in e.message


    def test_upgrade_v1_to_v2(self):
        """ mlaunch: test upgrade from protocol version 1 to 2. """
        startup_options = {"name": "replset", "replicaset": True, "dir": "./data", "authentication": False, "single": False, "arbiter": False, "mongos": 1, "binarypath": None, "sharded": None, "nodes": 3, "config": 1, "port": 33333, "restart": False, "verbose": False}

        # create directory
        self.run_tool("init --replicaset")
        self.run_tool("stop")

        # replace startup options
        with open(os.path.join(self.base_dir, 'test_upgrade_v1_to_v2', '.mlaunch_startup'), 'w') as f:
            json.dump(startup_options, f, -1)

        # now start with old config and check if upgrade worked
        self.run_tool("start")
        with open(os.path.join(self.base_dir, 'test_upgrade_v1_to_v2', '.mlaunch_startup'), 'r') as f:
            startup_options = json.load(f)
            assert startup_options['protocol_version'] == 2

    def test_sharded_named_1(self):
        """ mlaunch: test --sharded <name> for a single shard """

        self.run_tool("init --sharded foo --single")
        assert len(self.tool.get_tagged('foo'))  == 1


    def test_mlaunch_list(self):
        """ mlaunch: test list command """

        self.run_tool("init --sharded 2 --replicaset --mongos 2")
        self.run_tool("list")

        # capture stdout and only keep from actual LIST output
        output = sys.stdout.getvalue().splitlines()
        output = output[output.index( next(o for o in output if o.startswith('PROCESS')) ):]

        assert self.helper_output_has_line_with(['PROCESS', 'STATUS', 'PORT'], output) == 1
        assert self.helper_output_has_line_with(['mongos', 'running'], output) == 2
        assert self.helper_output_has_line_with(['config server', 'running'], output) == 1
        assert self.helper_output_has_line_with(['shard01'], output) == 1
        assert self.helper_output_has_line_with(['shard02'], output) == 1
        assert self.helper_output_has_line_with(['primary', 'running'], output) == 2
        assert self.helper_output_has_line_with(['running', 'running'], output) == 9


    def helper_which(self, pgm):
        """ equivalent of which command """
        
        path=os.getenv('PATH')
        for p in path.split(os.path.pathsep):
            p=os.path.join(p,pgm)
            if os.path.exists(p) and os.access(p,os.X_OK):
                return p

    
    def test_mlaunch_binary_path_start(self):
        """ mlaunch: test if --binarypath is persistent between init and start """

        # get true binary path (to test difference to not specifying one)
        path = self.helper_which('mongod')
        path = path[:path.rfind('/')]

        self.run_tool("init --single --binarypath %s" % path)
        self.run_tool("stop")
        
        self.run_tool("start")
        assert self.tool.loaded_args['binarypath'] == path
        assert self.tool.startup_info[str(self.port)].startswith('%s/mongod' % path)

        self.run_tool("stop")
        try:
            self.run_tool("start --binarypath /some/other/path")
            raise Exception
        except:
            assert self.tool.args['binarypath'] == '/some/other/path'
            assert self.tool.startup_info[str(self.port)].startswith('/some/other/path/mongod')


    @raises(SystemExit)
    def test_single_and_arbiter(self):
        """ mlaunch: test --single with --arbiter error """
        
        self.run_tool("init --single --arbiter")


    def test_oplogsize_config(self):
        """ mlaunch: test config server never receives --oplogSize parameter """

        self.run_tool("init --sharded 1 --single --oplogSize 19 --verbose")
        output = sys.stdout.getvalue().splitlines()

        output_launch_config = next(o for o in output if '--configsvr' in o)
        assert '--oplogSize' not in output_launch_config


if __name__ == '__main__':

    # run individual tests with normal print output 
    tml = TestMLaunch()
    tml.setup()
    tml.test_kill_partial()
    tml.teardown()




########NEW FILE########
__FILENAME__ = test_mlogfilter
from mtools.mlogfilter.mlogfilter import MLogFilterTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile
import mtools

from nose.tools import *
from nose.plugins.skip import Skip, SkipTest

from random import randrange
from datetime import timedelta, datetime
from dateutil import parser
import os
import sys
import re
import json


def random_date(start, end):
    """ This function will return a random datetime between two datetime objects. """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


class TestMLogFilter(object):
    """ This class tests functionality around the mlogfilter tool. """

    def setup(self):
        """ start up method to create mlaunch tool and find free port. """
        self.tool = MLogFilterTool()

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_225.log')
        self.logfile = LogFile(open(self.logfile_path, 'r'))


    def test_msToString(self):
        assert(self.tool._msToString(100) == '0hr 0min 0secs 100ms')
        assert(self.tool._msToString(1000) == '0hr 0min 1secs 0ms')
        assert(self.tool._msToString(100000) == '0hr 1min 40secs 0ms')
        assert(self.tool._msToString(10000000) == '2hr 46min 40secs 0ms')

    def test_from(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        self.tool.run('%s --from %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_iso8601_timestamp(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        self.tool.run('%s --from %s'%(self.logfile_path, random_start.isoformat()))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_to(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        random_end = random_date(random_start, self.logfile.end)

        self.tool.run('%s --from %s --to %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start and le.datetime <= random_end)


    def test_from_to_26_log(self):
        logfile_26_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        logfile_26 = LogFile(open(logfile_26_path, 'r'))

        random_start = random_date(logfile_26.start, logfile_26.end)
        random_end = random_date(random_start, logfile_26.end)

        print random_start, random_end
        print logfile_26.start, logfile_26.end

        self.tool.run('%s --from %s --to %s'%(logfile_26_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0

        at_least_one = False
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            at_least_one = True
            assert(le.datetime >= random_start and le.datetime <= random_end)
        assert at_least_one

    def test_from_to_stdin(self):

        year = datetime.now().year
        start = datetime(year, 8, 5, 20, 45)
        end = datetime(year, 8, 5, 21, 01)
        self.tool.is_stdin = True
        self.tool.run('%s --from %s --to %s'%(self.logfile_path, start.strftime("%b %d %H:%M:%S"), end.strftime("%b %d %H:%M:%S")))
        self.tool.is_stdin = False

        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.datetime >= start and le.datetime <= end)


    def test_json(self):
        """ output with --json is in JSON format. """
        self.tool.run('%s --json'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            line_dict = json.loads(line)
            assert(line_dict)
            assert(type(line_dict) == dict)

    def test_shorten_50(self):
        self.tool.run('%s --shorten 50'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 50)

    def test_shorten_default(self):
        self.tool.run('%s --shorten'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 200)

    def test_merge_same(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s'%(self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 2*file_length
        for prev, next in zip(lines[:-1], lines[1:]):
            prev_le = LogEvent(prev)
            next_le = LogEvent(next)
            if not prev_le.datetime or not next_le.datetime:
                continue
            assert prev_le.datetime <= next_le.datetime

    def test_merge_markers(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s --markers foo bar'%(self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len([l for l in lines if l.startswith('foo')]) == file_length
        assert len([l for l in lines if l.startswith('bar')]) == file_length

    def test_merge_invalid_markers(self):
        try:
            self.tool.run('%s %s --markers foo bar baz'%(self.logfile_path, self.logfile_path))
        except SystemExit as e:
            assert 'Number of markers not the same' in e.message

    def test_exclude(self):
        file_length = len(self.logfile)
        tool = MLogFilterTool()
        tool.run('%s --slow 300' % self.logfile_path)

        tool = MLogFilterTool()
        tool.run('%s --slow 300 --exclude' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines_total = len(output.splitlines())

        assert lines_total == file_length


    def test_end_reached(self):
        self.tool.run('%s --from Jan 3015 --to +10min'%self.logfile_path)
        output = sys.stdout.getvalue()
        assert output.strip() == ''


    def test_human(self):
        # need to skip this test for python 2.6.x because thousands separator format is not compatible
        if sys.version_info < (2, 7):
            raise SkipTest

        self.tool.run('%s --slow --thread conn8 --human'%self.logfile_path)
        output = sys.stdout.getvalue().rstrip()
        assert(output.endswith('(0hr 0min 1secs 324ms) 1,324ms'))
        assert('cursorid:7,776,022,515,301,717,602' in output)

    def test_slow_fast(self):
        self.tool.run('%s --slow 145 --fast 500'%self.logfile_path)
        output = sys.stdout.getvalue()
        assert(len(output.splitlines()) > 0)
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.duration >= 145 and le.duration <= 500)

    def test_scan(self):
        # load tablescan logfile
        scn_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'collscans.log')

        self.tool.run('%s --scan' % scn_logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 3

    def test_accept_nodate(self):
        self.tool.is_stdin = True
        self.tool.run('%s --from Aug 5 2014 20:53:50 --to +5min'%self.logfile_path)
        self.tool.is_stdin = False

        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any('=== a line without a datetime ===' in l for l in lines)

    def test_thread(self):
        self.tool.run('%s --thread initandlisten'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.thread == 'initandlisten')

    def test_no_timestamp_format(self):
        self.tool.run('%s --timestamp-format none --timezone 5'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if le.datetime:
                assert le.datetime_format == 'ctime-pre2.4'

    def test_operation(self):
        self.tool.run('%s --operation insert'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.operation == 'insert')

    def test_invalid_timezone_args(self):
        try:
            self.tool.run('%s --timezone 1 2 3'%self.logfile_path)
        except SystemExit as e:
            assert "Invalid number of timezone parameters" in e.message

    def test_verbose(self):
        self.tool.run('%s --slow --verbose'%self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert lines[0].startswith('command line arguments')
        assert any( line.startswith('active filters: SlowFilter') for line in lines )

    def test_namespace(self):
        self.tool.run('%s --namespace local.oplog.rs'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.namespace == 'local.oplog.rs')

    def test_pattern(self):
        # test that pattern is correctly parsed, reordered and compared to logevent pattern
        self.tool.run('%s --pattern {ns:1,_id:1,host:1}'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.pattern == '{"_id": 1, "host": 1, "ns": 1}')

    def test_word(self):
        self.tool.run('%s --word lock'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert('lock' in line)


    def test_mask_end(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size/2)

        self.tool.run('%s --mask %s --mask-size %i'%(self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(
                    (le.datetime >= event1 - padding and le.datetime <= event1 + padding) or
                    (le.datetime >= event2 - padding and le.datetime <= event2 + padding)
                  )


    def test_mask_start(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size/2)

        self.tool.run('%s --mask %s --mask-size %i --mask-center start'%(self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(
                    (le.datetime >= event1 - duration1 - padding and le.datetime <= event1 - duration1 + padding) or
                    (le.datetime >= event2 - padding and le.datetime <= event2 + padding)
                  )


    def test_mask_both(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size/2)

        self.tool.run('%s --mask %s --mask-size %i --mask-center both'%(self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(
                    (le.datetime >= event1 - duration1 - padding and le.datetime <= event1 + padding) or
                    (le.datetime >= event2 - padding and le.datetime <= event2 + padding)
                  )

    @raises(SystemExit)
    def test_no_logfile(self):
        """ mlogfilter: test that not providing at least 1 log file throws clean error. """

        self.tool.run('--from Jan 1')


    def test_year_rollover_1(self):
        """ mlogfilter: test that mlogfilter works correctly with year-rollovers in logfiles with ctime (1) """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')

        self.tool.run('%s --from Jan 1 2014 --timestamp-format iso8601-utc' % yro_logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert line.startswith("2014-")


    def test_year_rollover_2(self):
        """ mlogfilter: test that mlogfilter works correctly with year-rollovers in logfiles with ctime (2) """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')

        self.tool.run('%s --from Dec 31 --to +1day --timestamp-format iso8601-utc' % yro_logfile_path)
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0
        for line in output.splitlines():
            assert line.startswith("2013-")


# output = sys.stdout.getvalue().strip()

########NEW FILE########
__FILENAME__ = test_mloginfo
from mtools.mloginfo.mloginfo import MLogInfoTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile
import mtools

from nose.tools import *
from nose.plugins.skip import Skip, SkipTest

# from random import randrange
# from datetime import timedelta, datetime
# from dateutil import parser
import os
import sys
import re


def random_date(start, end):
    """ This function will return a random datetime between two datetime objects. """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


class TestMLogInfo(object):
    """ This class tests functionality around the mloginfo tool. """

    def setup(self):
        """ startup method to create mloginfo tool. """
        self.tool = MLogInfoTool()

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_225.log')
        self.logfile = LogFile(open(self.logfile_path, 'r'))


    def test_basic(self):
        self.tool.run('%s' % self.logfile_path)
        output = sys.stdout.getvalue()
        results = {}
        for line in output.splitlines():
            if line.strip() == '':
                continue
            key, val = line.split(':', 1)
            results[key.strip()] = val.strip()

        assert results['source'].endswith('mongod_225.log')
        assert results['start'].endswith('Aug 05 20:21:42')
        assert results['end'].endswith('Aug 05 21:04:52')
        assert results['date format'] == 'ctime-pre2.4'
        assert results['length'] == '497'
        assert results['binary'] == 'mongod'
        assert results['version'] == '2.2.5'


    def test_multiple_files(self):
        self.tool.run('%s %s' % (self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        results = {}
        lines = output.splitlines()
        assert len( [l for l in lines if l.strip().startswith('source') ] ) == 2
        assert len( [l for l in lines if l.strip().startswith('start') ] ) == 2
        assert len( [l for l in lines if l.strip().startswith('end') ] ) == 2
        assert len( [l for l in lines if l.strip().startswith('-----') ] ) == 1


    def test_version_norestart(self):
        # different log file
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')
        self.tool.run('%s' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'version: >= 2.4' in line, lines))


    def test_distinct_output(self):
        # different log file
        self.tool.run('%s --distinct' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'DISTINCT' in line, lines))
        assert len(filter(lambda line: re.match(r'\s+\d+\s+\w+', line), lines)) > 10


    def test_connections_output(self):
        # different log file
        self.tool.run('%s --connections' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'CONNECTIONS' in line, lines))

        assert any(map(lambda line: 'total opened' in line, lines))
        assert any(map(lambda line: 'total closed' in line, lines))
        assert any(map(lambda line: 'unique IPs' in line, lines))
        assert any(map(lambda line: 'socket exceptions' in line, lines))

        assert len(filter(lambda line: re.match(r'\d+\.\d+\.\d+\.\d+', line), lines)) > 1


    def test_queries_output(self):
        # different log file
        self.tool.run('%s --queries' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'QUERIES' in line, lines))
        assert any(map(lambda line: line.startswith('namespace'), lines))

        assert len(filter(lambda line: re.match(r'\w+\.\w+\s+{', line), lines)) >= 1


    def test_restarts_output(self):
        # different log file
        self.tool.run('%s --restarts' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'RESTARTS' in line, lines))
        assert any(map(lambda line: 'version 2.2.5' in line, lines))

########NEW FILE########
__FILENAME__ = test_util_hci
from mtools.util.hci import DateTimeBoundaries
from datetime import datetime, timedelta
from dateutil.tz import tzutc

def test_dtb_within_boundaries_absolute():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('Feb 18 2013', 'Feb 19 2013')
    assert from_dt == datetime(2013, 2, 18, tzinfo=tzutc())
    assert to_dt == datetime(2013, 2, 19, tzinfo=tzutc())


def test_dtb_from_before_start():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('Sep 15 2012', 'Dec 1 2012')
    assert from_dt == start
    assert to_dt == datetime(2012, 12, 01, tzinfo=tzutc())


def test_dtb_to_after_end():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('2013-01-15', '2016-03-02')
    assert from_dt == datetime(2013, 1, 15, tzinfo=tzutc())
    assert to_dt == end


def test_dtb_both_outside_bounds():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('2000-01-01', '2050-12-31')
    assert from_dt == start
    assert to_dt == end


def test_dtb_keywords():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2050, 1, 1, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    
    # start and end
    from_dt, to_dt = dtb('start', 'end')
    assert from_dt == start
    assert to_dt == end

    # today
    from_dt, to_dt = dtb('start', 'today')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzutc())
    assert to_dt == today

    # now, must be witin one second from now
    from_dt, to_dt = dtb('start', 'now')
    now = datetime.now().replace(tzinfo=tzutc())
    assert now - to_dt < timedelta(seconds=1)


def test_dtb_string2dt():

    start = datetime(2000, 1, 1, tzinfo=tzutc())
    end = datetime(2015, 6, 13, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)

    # without lower bound
    assert dtb.string2dt('') == start
    assert dtb.string2dt('2013') == datetime(2013, 1, 1, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Aug 2011') == datetime(2011, 8, 1, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 1978') == datetime(1978, 9, 29, 0, 0, tzinfo=tzutc())
    
    # no year given, choose end year if still in log file, otherwise year before
    assert dtb.string2dt('20 Mar') == datetime(2015, 3, 20, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('20 Aug') == datetime(2014, 8, 20, 0, 0, tzinfo=tzutc())

    # weekdays, always use last week of log file end
    assert dtb.string2dt('Sat') == datetime(2015, 6, 13, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Wed') == datetime(2015, 6, 10, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Sun') == datetime(2015, 6, 7, 0, 0, tzinfo=tzutc())

    # constants
    assert dtb.string2dt('start') == start
    assert dtb.string2dt('end') == end
    assert dtb.string2dt('today') == datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzutc())
    assert dtb.string2dt('yesterday') == datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzutc()) - timedelta(days=1)


    # times
    assert dtb.string2dt('29 Sep 1978 13:06') == datetime(1978, 9, 29, 13, 6, tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 13:06') == datetime(2014, 9, 29, 13, 6, tzinfo=tzutc())
    assert dtb.string2dt('13:06') == datetime(2000, 1, 1, 13, 6, tzinfo=tzutc())
    assert dtb.string2dt('13:06:15') == datetime(2000, 1, 1, 13, 6, 15, tzinfo=tzutc())
    assert dtb.string2dt('13:06:15.214') == datetime(2000, 1, 1, 13, 6, 15, 214000, tzinfo=tzutc())
    assert dtb.string2dt('Wed 13:06:15') == datetime(2015, 6, 10, 13, 6, 15, tzinfo=tzutc())

    # offsets
    assert dtb.string2dt('2013 +1d') == datetime(2013, 1, 2, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Sep 2011 +1mo') == datetime(2011, 10, 1, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 1978 +3hours') == datetime(1978, 9, 29, 3, 0, tzinfo=tzutc())
    assert dtb.string2dt('20 Mar +5min') == datetime(2015, 3, 20, 0, 5, tzinfo=tzutc())
    assert dtb.string2dt('20 Aug -2day') == datetime(2014, 8, 18, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Sat -1d') == datetime(2015, 6, 12, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Wed +4sec') == datetime(2015, 6, 10, 0, 0, 4, tzinfo=tzutc())
    assert dtb.string2dt('Sun -26h') == datetime(2015, 6, 5, 22, 0, tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 1978 13:06 +59s') == datetime(1978, 9, 29, 13, 6, 59, tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 13:06 +120secs') == datetime(2014, 9, 29, 13, 8, tzinfo=tzutc())
    # assert dtb.string2dt('13:06 -1week') == datetime(2014, 12, 25, 13, 6, tzinfo=tzutc())
    # print dtb.string2dt('13:06:15 -16sec')
    # assert dtb.string2dt('13:06:15 -16sec') == datetime(2014, 1, 1, 13, 5, 59, tzinfo=tzutc())
    # assert dtb.string2dt('13:06:15.214 +1h') == datetime(2014, 1, 1, 14, 6, 15, 214000, tzinfo=tzutc())
    assert dtb.string2dt('Wed 13:06:15 -1day') == datetime(2015, 6, 9, 13, 6, 15, tzinfo=tzutc())
    
    print dtb.string2dt('start +3h')
    assert dtb.string2dt('start +3h') == start + timedelta(hours=3)

    # offset only
    assert dtb.string2dt('-2d') == datetime(2015, 6, 11, tzinfo=tzutc())

    # test presence / absence of year and behavior for adjustment
    assert dtb.string2dt('July 30 2015') == datetime(2015, 7, 30, tzinfo=tzutc())
    assert dtb.string2dt('July 30') == datetime(2014, 7, 30, tzinfo=tzutc())
    assert dtb.string2dt('1899 Nov 1') == datetime(1899, 11, 1, tzinfo=tzutc())

    # isoformat
    from_dt = datetime(2014, 8, 5, 20, 57, 7, tzinfo=tzutc())
    assert dtb.string2dt(from_dt.isoformat()) == datetime(2014, 8, 5, 20, 57, 7, tzinfo=tzutc())
    assert dtb.string2dt('2014-04-28T16:17:18.192Z') == datetime(2014, 4, 28, 16, 17, 18, 192000, tzinfo=tzutc())

    # with lower_bounds
    lower = datetime(2013, 5, 2, 16, 21, 58, 123, tzinfo=tzutc())
    assert dtb.string2dt('', lower) == end
    assert dtb.string2dt('2013', lower) == datetime(2013, 1, 1, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Aug', lower) == datetime(2014, 8, 1, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('+3sec', lower) == lower + timedelta(seconds=3)
    assert dtb.string2dt('+4min', lower) == lower + timedelta(minutes=4)
    assert dtb.string2dt('-5hours', lower) == lower - timedelta(hours=5)


if __name__ == '__main__':
    
   test_dtb_string2dt()









########NEW FILE########
__FILENAME__ = test_util_log2code
from mtools.util.log2code import Log2CodeConverter

logline1 = """Thu Nov 14 17:58:43.898 [rsStart] replSet info Couldn't load config yet. Sleeping 20sec and will try again."""
logline2 = """Thu Nov 14 17:58:43.917 [initandlisten] connection accepted from 10.10.0.38:37233 #10 (4 connections now open)"""

l2cc = Log2CodeConverter()

def test_log2code():
    fixed, variable = l2cc(logline1)
    assert fixed
    assert fixed.matches["r2.4.9"] == [('src/mongo/db/repl/rs.cpp', 790, 0, 'log(')]


########NEW FILE########
__FILENAME__ = test_util_logevent
import sys
from nose.tools import *
from mtools.util.logevent import LogEvent
import time
import datetime
from dateutil import parser

line_ctime_pre24 = "Sun Aug  3 21:52:05 [initandlisten] db version v2.2.4, pdfile version 4.5"
line_ctime = "Sun Aug  3 21:52:05.995 [initandlisten] db version v2.4.5"
line_iso8601_local = "2013-08-03T21:52:05.995+1000 [initandlisten] db version v2.5.2-pre-"
line_iso8601_utc = "2013-08-03T11:52:05.995Z [initandlisten] db version v2.5.2-pre-"
line_getmore = "Mon Aug  5 20:26:32 [conn9] getmore local.oplog.rs query: { ts: { $gte: new Date(5908578361554239489) } } cursorid:1870634279361287923 ntoreturn:0 keyUpdates:0 numYields: 107 locks(micros) r:85093 nreturned:13551 reslen:230387 144ms"
line_253_numYields = "2013-10-21T12:07:27.057+1100 [conn2] query test.docs query: { foo: 234333.0 } ntoreturn:0 ntoskip:0 keyUpdates:0 numYields:1 locks(micros) r:239078 nreturned:0 reslen:20 145ms"
line_246_numYields = "Mon Oct 21 12:14:21.888 [conn4] query test.docs query: { foo: 23432.0 } ntoreturn:0 ntoskip:0 nscanned:316776 keyUpdates:0 numYields: 2405 locks(micros) r:743292 nreturned:2 reslen:2116 451ms"
line_pattern_26_a = """2014-03-18T18:34:30.435+1100 [conn10] query test.new query: { a: 1.0 } planSummary: EOF ntoreturn:0 ntoskip:0 keyUpdates:0 numYields:0 locks(micros) r:103 nreturned:0 reslen:20 0ms"""
line_pattern_26_b = """2014-03-18T18:34:34.360+1100 [conn10] query test.new query: { query: { a: 1.0 }, orderby: { b: 1.0 } } planSummary: EOF ntoreturn:0 ntoskip:0 keyUpdates:0 numYields:0 locks(micros) r:55 nreturned:0 reslen:20 0ms"""
line_pattern_26_c = """2014-03-18T18:34:50.777+1100 [conn10] query test.new query: { $query: { a: 1.0 }, $orderby: { b: 1.0 } } planSummary: EOF ntoreturn:0 ntoskip:0 keyUpdates:0 numYields:0 locks(micros) r:60 nreturned:0 reslen:20 0ms"""

# fake system.profile documents
profile_doc1 = { "op" : "query", "ns" : "test.foo", "thread": "test.system.profile", "query" : { "test" : 1 }, "ntoreturn" : 0, "ntoskip" : 0, "nscanned" : 0, "keyUpdates" : 0, "numYield" : 0, "lockStats" : { "timeLockedMicros" : { "r" : 461, "w" :0 }, "timeAcquiringMicros" : { "r" : 4, "w" : 3 } }, "nreturned" : 0, "responseLength" : 20, "millis" : 0, "ts" : parser.parse("2014-03-20T04:04:21.231Z"), "client" : "127.0.0.1", "allUsers" : [ ], "user" : "" }
profile_doc2 = { "op" : "query", "ns" : "test.foo", "thread": "test.system.profile", "query" : { "query" : { "test" : 1 }, "orderby" : { "field" : 1 } }, "ntoreturn" : 0, "ntoskip" : 0, "nscanned" : 0, "keyUpdates" : 0, "numYield" : 0, "lockStats" : { "timeLockedMicros" : { "r" : 534, "w" : 0 }, "timeAcquiringMicros" : { "r" : 5, "w" : 4 } }, "nreturned" : 0, "responseLength" : 20, "millis" : 0, "ts" : parser.parse("2014-03-20T04:04:33.775Z"), "client" : "127.0.0.1", "allUsers" : [ ], "user" : "" }
profile_doc3 = { "op" : "query", "ns" : "test.foo", "thread": "test.system.profile", "query" : { "$query" : { "test" : 1 }, "$orderby" : { "field" : 1 } }, "ntoreturn" : 0, "ntoskip" : 0, "nscanned" : 0, "keyUpdates" : 0, "numYield" : 0, "lockStats" : { "timeLockedMicros" : { "r" : 436, "w" : 0 }, "timeAcquiringMicros" : { "r" : 5, "w" : 8 } }, "nreturned" : 0, "responseLength" : 20, "millis" : 0, "ts" : parser.parse("2014-03-20T04:04:52.791Z"), "client" : "127.0.0.1", "allUsers" : [ ], "user" : "" }

def test_logevent_datetime_parsing():
    """ Check that all four timestamp formats are correctly parsed. """

    le = LogEvent(line_ctime_pre24)
    this_year = datetime.datetime.now().year

    le_str = le.line_str
    assert(str(le.datetime) == '%s-08-03 21:52:05+00:00'%this_year)
    assert(le._datetime_format == 'ctime-pre2.4')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo != None)

    le =  LogEvent(line_ctime)
    le_str = le.line_str
    assert(str(le.datetime) == '%s-08-03 21:52:05.995000+00:00'%this_year)
    assert(le._datetime_format == 'ctime')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo != None)

    le =  LogEvent(line_iso8601_utc)
    le_str = le.line_str
    assert(str(le.datetime) == '2013-08-03 11:52:05.995000+00:00')
    assert(le._datetime_format == 'iso8601-utc')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo != None)

    le =  LogEvent(line_iso8601_local)
    le_str = le.line_str
    assert(str(le.datetime) == '2013-08-03 21:52:05.995000+10:00')
    assert(le._datetime_format == 'iso8601-local')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo != None)


def test_logevent_pattern_parsing():

    le = LogEvent(line_pattern_26_a)
    assert(le.pattern) == '{"a": 1}'

    le = LogEvent(line_pattern_26_b)
    assert(le.pattern) == '{"a": 1}'

    le = LogEvent(line_pattern_26_c)
    assert(le.pattern) == '{"a": 1}'


def test_logevent_sort_pattern_parsing():

    le = LogEvent(line_pattern_26_a)
    assert(le.sort_pattern) == None

    le = LogEvent(line_pattern_26_b)
    assert(le.sort_pattern) == '{"b": 1}'

    le = LogEvent(line_pattern_26_c)
    assert(le.sort_pattern) == '{"b": 1}'


def test_logevent_profile_pattern_parsing():
    le = LogEvent(profile_doc1)
    assert(le.pattern == '{"test": 1}')

    le = LogEvent(profile_doc2)
    assert(le.pattern == '{"test": 1}')
        
    le = LogEvent(profile_doc3)
    assert(le.pattern == '{"test": 1}')


def test_logevent_profile_sort_pattern_parsing():
    le = LogEvent(profile_doc1)
    assert(le.sort_pattern == None)

    le = LogEvent(profile_doc2)
    assert(le.sort_pattern == '{"field": 1}')
        
    le = LogEvent(profile_doc3)
    assert(le.sort_pattern == '{"field": 1}')



def test_logevent_extract_new_and_old_numYields():
    le =  LogEvent(line_246_numYields)
    assert(le.numYields == 2405)

    le =  LogEvent(line_253_numYields)
    assert(le.numYields == 1)


def test_logevent_value_extraction():
    """ Check for correct value extraction of all fields. """
    
    le =  LogEvent(line_getmore)
    assert(le.thread == 'conn9')
    assert(le.operation == 'getmore')
    assert(le.namespace == 'local.oplog.rs')
    assert(le.duration == 144)
    assert(le.numYields == 107)
    assert(le.r == 85093)
    assert(le.ntoreturn == 0)
    assert(le.nreturned == 13551)
    assert(le.pattern == '{"ts": 1}')


def test_logevent_lazy_evaluation():
    """ Check that all LogEvent variables are evaluated lazily. """
    
    fields = ['_thread', '_operation', '_namespace', '_duration', '_numYields', '_r', '_ntoreturn', '_nreturned', '_pattern']

    # before parsing all member variables need to be None
    le =  LogEvent(line_getmore)
    for attr in fields:
        assert(getattr(le, attr) == None)

    # after parsing, they all need to be filled out
    le.parse_all()
    for attr in fields:
        assert(getattr(le, attr) != None)

########NEW FILE########
__FILENAME__ = test_util_logfile
import sys, os
import mtools

from nose.tools import *
from datetime import datetime
from mtools.util.logfile import LogFile
from mtools.util.logevent import LogEvent
from dateutil.tz import tzutc, tzoffset


class TestUtilLogFile(object):

    def setup(self):
        """ start up method for LogFile fixture. """

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')
        self.file_year_rollover = open(self.logfile_path, 'r')


    def test_len(self):
        """ LogFile: test len() and iteration over LogFile method """

        logfile = LogFile(self.file_year_rollover)
        length = len(logfile)

        i = 0
        for i, le in enumerate(logfile):
            assert isinstance(le, LogEvent)

        assert length == i+1 
        assert length == 1836


    def test_start_end(self):
        """ LogFile: test .start and .end property work correctly """

        logfile = LogFile(self.file_year_rollover)
        
        assert logfile.start == datetime(2013, 12, 30, 00, 13, 01, 661000, tzutc())
        assert logfile.end == datetime(2014, 01, 02, 23, 27, 11, 720000, tzutc())


    def test_timezone(self):

        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        mongod_26 = open(logfile_path, 'r')

        logfile = LogFile(mongod_26)
        assert logfile.timezone == tzoffset(None, -14400)


    def test_rollover_detection(self):
        """ LogFile: test datetime_format and year_rollover properties """

        logfile = LogFile(self.file_year_rollover)
        assert logfile.datetime_format == "ctime"
        assert logfile.year_rollover == logfile.end

########NEW FILE########
__FILENAME__ = cmdlinetool
import argparse
import sys
import re
import signal
import datetime
import os

from dateutil.tz import tzutc

from mtools.version import __version__
from mtools.util.profile_collection import ProfileCollection
from mtools.util.logfile import LogFile

try:
    try:
        from pymongo import MongoClient as Connection
    except ImportError:
        from pymongo import Connection
        from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError

    class InputSourceAction(argparse.FileType):
        """ This class extends the FileType class from the argparse module. It will try to open
            the file and pass the handle to a new LogFile object, but if that's not possible it 
            will catch the exception and interpret the string as a MongoDB URI and try to connect 
            to the database. In that case, it will return a ProfileCollection object.

            Both derive from the same base class InputSource and support iteration over LogEvents.
        """
        def __call__(self, string):
            try:
                # catch filetype and return LogFile object
                filehandle = argparse.FileType.__call__(self, string)
                return LogFile(filehandle)

            except argparse.ArgumentTypeError as e:
                # not a file, try open as MongoDB database 
                m = re.match('^(\w+)(?::(\d+))?(?:/([a-zA-Z0-9._-]+))?$', string)
                if m:
                    host, port, namespace = m.groups()
                    port = int(port) if port else 27017
                    namespace = namespace or 'test.system.profile'
                    if '.' in namespace:
                        database, collection = namespace.split('.', 1)
                    else:
                        database = namespace
                        collection = 'system.profile'

                    if host == 'localhost' or re.match('\d+\.\d+\.\d+\.\d+', host):
                        return ProfileCollection(host, port, database, collection)

                raise argparse.ArgumentTypeError("can't parse %s as file or MongoDB connection string." % string)


except ImportError:

    class InputSourceAction(argparse.FileType):
        pass


class BaseCmdLineTool(object):
    """ Base class for any mtools command line tool. Adds --version flag and basic control flow. """

    def __init__(self):
        """ Constructor. Any inheriting class should add a description to the argparser and extend 
            it with additional arguments as needed.
        """
        # define argument parser and add version argument
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('--version', action='version', version="mtools version %s" % __version__)
        self.argparser.add_argument('--no-progressbar', action='store_true', default=False, help='disables progress bar')
        self.is_stdin = not sys.stdin.isatty()
        

    def run(self, arguments=None, get_unknowns=False):
        """ Init point to execute the script. If `arguments` string is given, will evaluate the 
            arguments, else evaluates sys.argv. Any inheriting class should extend the run method 
            (but first calling BaseCmdLineTool.run(self)).
        """
        # redirect PIPE signal to quiet kill script, if not on Windows
        if os.name != 'nt':
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        if get_unknowns:
            if arguments:
                self.args, self.unknown_args = self.argparser.parse_known_args(args=arguments.split())
            else:
                self.args, self.unknown_args = self.argparser.parse_known_args()
            self.args = vars(self.args)
        else:
            if arguments:
                self.args = vars(self.argparser.parse_args(args=arguments.split()))
            else:
                self.args = vars(self.argparser.parse_args())

        self.progress_bar_enabled = not (self.args['no_progressbar'] or self.is_stdin)

    
    def _datetime_to_epoch(self, dt):
        """ converts the datetime to unix epoch (properly). """
        if dt:
            td = (dt - datetime.datetime.fromtimestamp(0, tzutc()))
            # don't use total_seconds(), that's only available in 2.7
            total_secs = int((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6)
            return total_secs
        else: 
            return 0
    
    def update_progress(self, progress, prefix=''):
        """ use this helper function to print a progress bar for longer-running scripts. 
            The progress value is a value between 0.0 and 1.0. If a prefix is present, it 
            will be printed before the progress bar. 
        """
        total_length = 40

        if progress == 1.:
            sys.stdout.write('\r' + ' '*(total_length + len(prefix) + 50))
            sys.stdout.write('\n')
            sys.stdout.flush()
        else:
            bar_length = int(round(total_length*progress))
            sys.stdout.write('\r%s [%s%s] %.1f %% ' % (prefix, '='*bar_length, ' '*(total_length-bar_length), progress*100))
            sys.stdout.flush()



class LogFileTool(BaseCmdLineTool):
    """ Base class for any mtools tool that acts on logfile(s). """

    def __init__(self, multiple_logfiles=False, stdin_allowed=True):
        """ Constructor. Adds logfile(s) and stdin option to the argument parser. """
        BaseCmdLineTool.__init__(self)

        self.multiple_logfiles = multiple_logfiles
        self.stdin_allowed = stdin_allowed

        arg_opts = {'action':'store', 'type':InputSourceAction()}

        if self.multiple_logfiles:
            arg_opts['nargs'] = '*'
            arg_opts['help'] = 'logfile(s) to parse'
        else:
            arg_opts['help'] = 'logfile to parse'

        if self.is_stdin:
            if not self.stdin_allowed:
                raise SystemExit("this tool can't parse input from stdin.")
                
            arg_opts['const'] = LogFile(sys.stdin)
            arg_opts['action'] = 'store_const'
            if 'type' in arg_opts: 
                del arg_opts['type']
            if 'nargs' in arg_opts:
                del arg_opts['nargs']

        self.argparser.add_argument('logfile', **arg_opts)


if __name__ == '__main__':
    tool = LogFileTool(multiple_logfiles=True, stdin_allowed=True)
    tool.run()
    print tool.args
    # for line in tool.args['logfile']:
    #     print line


########NEW FILE########
__FILENAME__ = grouping
from mtools.util import OrderedDict
import re

class Grouping(object):

    def __init__(self, iterable=None, group_by=None):
        self.groups = {}
        self.group_by = group_by

        if iterable:
            for item in iterable:
                self.add(item, group_by)


    def add(self, item, group_by=None):
        """ General purpose class to group items by certain criteria. """

        key = None
        
        if not group_by:
            group_by = self.group_by

        if group_by:
            # if group_by is a function, use it with item as argument
            if hasattr(group_by, '__call__'):
                key = group_by(item)

            # if the item has attribute of group_by as string, use that as key
            elif isinstance(group_by, str) and hasattr(item, group_by):
                key = getattr(item, group_by)

            else:
                key = None
                # try to match str(item) with regular expression
                if isinstance(group_by, str):
                    match = re.search(group_by, str(item))
                    if match:
                        if len(match.groups()) > 0:
                            key = match.group(1)
                        else:
                            key = match.group()
            
        self.groups.setdefault(key, list()).append(item)
        

    def __getitem__(self, key):
        return self.groups[key]

    def __iter__(self):
        for key in self.groups:
            yield key

    def __len__(self):
        return len(self.groups)

    def keys(self):
        return self.groups.keys()

    def values(self):
        return self.groups.values()

    def items(self):
        return self.groups.items()


    def regroup(self, group_by=None):
        if not group_by:
            group_by = self.group_by

        groups = self.groups
        self.groups = {}

        for g in groups:
            for item in groups[g]:
                self.add(item, group_by)


    def move_items(self, from_group, to_group):
        """ will take all elements from the from_group and add it to the to_group. """
        if from_group not in self.keys() or len(self.groups[from_group]) == 0:
            return 

        self.groups.setdefault(to_group, list()).extend(self.groups.get(from_group, list()))
        if from_group in self.groups:
            del self.groups[from_group]


    def sort_by_size(self, group_limit=None, discard_others=False, others_label='others'):
        """ sorts the groups by the number of elements they contain, descending. Also has option to 
            limit the number of groups. If this option is chosen, the remaining elements are placed
            into another group with the name specified with others_label. if discard_others is True,
            the others group is removed instead.
        """

        # sort groups by number of elements
        self.groups = OrderedDict( sorted(self.groups.iteritems(), key=lambda x: len(x[1]), reverse=True) )

        # if group-limit is provided, combine remaining groups
        if group_limit != None:

            # now group together all groups that did not make the limit
            if not discard_others:
                group_keys = self.groups.keys()[ group_limit-1: ]
                self.groups.setdefault(others_label, list())
            else:
                group_keys = self.groups.keys()[ group_limit: ]

            # only go to second last (-1), since the 'others' group is now last
            for g in group_keys:
                if not discard_others:
                    self.groups[others_label].extend(self.groups[g])
                del self.groups[g]

            # remove if empty
            if others_label in self.groups and len(self.groups[others_label]) == 0:
                del self.groups[others_label]

        # remove others group regardless of limit if requested
        if discard_others and others_label in self.groups:
            del self.groups[others_label]



if __name__ == '__main__':
    # Example
    items = [1, 4, 3, 5, 7, 8, 6, 7, 9, 8, 6, 4, 2, 3, 3, 0]

    grouping = Grouping(items, r'[3, 4, 5, 6, 7]')
    grouping.sort_by_size(group_limit=1, discard_others=True)
    # grouping.move_items('no match', 'foo')

    grouping.regroup(lambda x: 'even' if x % 2 == 0 else 'odd')

    for g in grouping:
        print g, grouping[g]


########NEW FILE########
__FILENAME__ = hci
from mtools.util import OrderedDict
from datetime import date, time, datetime, timedelta
import re
import copy
from dateutil import parser
from dateutil.tz import tzutc

class DateTimeBoundaries(object):

    timeunits = ['secs', 'sec', 's', 'mins', 'min', 'm', 'months', 'month', 'mo', 'hours', 'hour', 'h', 'days', 'day', 'd', 'weeks','week', 'w', 'years', 'year', 'y']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    dtRegexes = OrderedDict([ 
        # special constants
        ('constant', re.compile('(now|start|end|today|yesterday)' + '($|\s+)')),                        
        # weekday: Mon, Wed, Sat
        ('weekday',  re.compile('(' + '|'.join(weekdays) + ')' + '($|\s+)')),                 
        # 11:59:00.123, 1:13:12.004  (also match timezone postfix like Z or +0700 or -05:30)
        # ('time',     re.compile('(?P<hour>\d{1,2}):(?P<minute>\d{2,2})' + '(?::(?P<second>\d{2,2})(?:.(?P<microsecond>\d{3,3}))?)?(?P<timezone>[0-9Z:\+\-]+)?' + '($|\s+)')),                                      
        # offsets: +3min, -20s, +7days  (see timeunits above)
        ('offset',   re.compile('(?P<operator>[\+-])(?P<value>\d+)(?P<unit>' + '|'.join(timeunits) +')'+'($|\s+)'))                          
    ])

    def __init__(self, start, end):
        """ initialize the DateTimeBoundaries object with true start and end datetime objects. """

        if start > end:
            raise ValueError('Error in DateTimeBoundaries: end cannot be before start datetime.')

        # make sure all datetimes are timezone-aware
        self.start = start
        if not self.start.tzinfo:
            self.start = self.start.replace(tzinfo=tzutc())
        
        self.end = end
        if not self.end.tzinfo:
            self.end = self.end.replace(tzinfo=tzutc())


    def string2dt(self, s, lower_bound=None):
        original_s = s
        
        result = {}
        dt = None

        # if s is completely empty, return start or end, depending on what parameter is evaluated
        if s == '':
            return self.end if lower_bound else self.start

        # first try to match the defined regexes
        for idx in self.dtRegexes:
            regex = self.dtRegexes[idx]
            mo = regex.search(s)
            # if match was found, cut it out of original string and store in result
            if mo:
                result[idx] = mo
                s = s[:mo.start(0)] + s[mo.end(0):]

        # handle constants
        if 'constant' in result:
            constant = result['constant'].group(0).strip()
            if constant == 'end':
                dt = self.end
            elif constant == 'start':
                dt = self.start
            elif constant == 'today':
                dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif constant == 'yesterday':
                dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            elif constant == 'now':
                dt = datetime.now()

        elif 'weekday' in result:
                weekday = result['weekday'].group(0).strip()
                # assume most-recently occured weekday in logfile
                most_recent_date = self.end.replace(hour=0, minute=0, second=0, microsecond=0)
                offset = (most_recent_date.weekday() - self.weekdays.index(weekday)) % 7
                dt = most_recent_date - timedelta(days=offset)
            
        # if anything remains unmatched, try parsing it with dateutil's parser
        if s.strip() != '':
            try:
                if dt:
                    dt = parser.parse(s, default=dt, tzinfos=tzutc)
                else:
                    # check if it's only time, then use the start dt as default, else just use the current year
                    if re.match('(?P<hour>\d{1,2}):(?P<minute>\d{2,2})' + '(?::(?P<second>\d{2,2})(?:.(?P<microsecond>\d{3,3}))?)?(?P<timezone>[0-9Z:\+\-]+)?$', s):
                        default = self.end if lower_bound else self.start
                    else:
                        default = datetime(self.end.year, 1, 1, 0, 0, 0)
                    default = default.replace(second=0, microsecond=0)

                    dt = parser.parse(s, default=default)

            except ValueError as e:
                raise ValueError("Error in DateTimeBoundaries: can't parse datetime from %s" % s)

        if not dt:
            dt = lower_bound or self.end

        # if no timezone specified, use the one from the logfile
        if dt.tzinfo == None:
            dt = dt.replace(tzinfo=self.start.tzinfo)

        
        # time is applied separately (not through the parser) so that string containing only time don't use today as default date (parser behavior)
        # if 'time' in result:
        #     dct = dict( (k, int(v)) for k,v in result['time'].groupdict(0).iteritems() )
        #     dct['microsecond'] *= 1000
        #     dt = dt.replace(**dct)

        # apply offset
        if 'offset' in result:

            # separate in operator, value, unit
            dct = result['offset'].groupdict()

            mult = 1
            if dct['unit'] in ['s', 'sec', 'secs']:
                dct['unit'] = 'seconds'
            elif dct['unit'] in ['m', 'min', 'mins']:
                dct['unit'] = 'minutes'
            elif dct['unit'] in ['h', 'hour', 'hours']:
                dct['unit'] = 'hours'
            elif dct['unit'] in ['d', 'day', 'days']:
                dct['unit'] = 'days'
            elif dct['unit'] in ['w', 'week', 'weeks']:
                dct['unit'] = 'days'
                mult = 7
            elif dct['unit'] in ['mo', 'month', 'months']:
                dct['unit'] = 'days'
                mult = 30.43
            elif dct['unit'] in ['y', 'year', 'years']:
                dct['unit'] = 'days'
                mult = 365.24
            
            if dct['operator'] == '-':
                mult *= -1

            dt = dt + eval('timedelta(%s=%i)'%(dct['unit'], mult*int(dct['value'])))

        # if parsed datetime is out of bounds and no year specified, try to adjust year
        year_present = re.search('\d{4,4}', original_s)

        if not year_present:
            if dt < self.start and dt.replace(year=dt.year+1) >= self.start and dt.replace(year=dt.year+1) <= self.end:
                dt = dt.replace(year=dt.year+1)
            elif dt > self.end and dt.replace(year=dt.year-1) >= self.start and dt.replace(year=dt.year-1) <= self.end:
                dt = dt.replace(year=dt.year-1)

        return dt


    def __call__(self, from_str=None, to_str=None):
        """ sets the boundaries based on `from` and `to` strings. """

        from_dt = self.string2dt(from_str, lower_bound=None)
        to_dt = self.string2dt(to_str, lower_bound=from_dt)

        if to_dt < from_dt:
            raise ValueError('Error in DateTimeBoundaries: lower bound is greater than upper bound.')

        # limit from and to at the real boundaries
        if to_dt > self.end:
            to_dt = self.end
        
        if from_dt < self.start:
            from_dt = self.start

        return from_dt, to_dt


if __name__ == '__main__':
    
    dtb = DateTimeBoundaries(parser.parse('Apr 8 2014 13:00-0400'), parser.parse('Apr 10 2014 16:21-0400'))
    lower, upper = dtb('2014-04-08T13:21-0400', '')
    print "lower", lower
    print "upper", upper

    print dtb.string2dt("start +3h")


########NEW FILE########
__FILENAME__ = input_source
class InputSource(object):

    def __iter__(self):
        """ Iterate over log events. """
        pass

    def fast_forward(self, dt):
        pass
########NEW FILE########
__FILENAME__ = log2code
import cPickle
import os
import re
import sys
import argparse
from collections import defaultdict
from itertools import chain, izip_longest


from mtools.util.logcodeline import LogCodeLine
import mtools

def import_l2c_db():
    """ static import helper function, checks if the log2code.pickle exists first, otherwise
        raises ImportError. 
    """
    data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
    if os.path.exists(os.path.join(data_path, 'log2code.pickle')):
        av, lv, lbw, lcl = cPickle.load(open(os.path.join(data_path, 'log2code.pickle'), 'rb'))
        return av, lv, lbw, lcl
    else:

        raise ImportError('log2code.pickle not found in %s.'%data_path)




class Log2CodeConverter(object):

    # static import of logdb data structures
    all_versions, log_version, logs_by_word, log_code_lines = import_l2c_db()
        
    def _log2code(self, line):
        tokens = re.split(r'[\s"]', line)

        # find first word in first 20 tokens that has a corresponding log message stored
        for word_no, word in enumerate(w for w in tokens if w in self.logs_by_word):

            # go through all error messages starting with this word
            coverage = []
            for log in self.logs_by_word[word]:

                if all([line.find(token) >= 0 for token in log]):
                    # all tokens match, calculate coverage
                    cov = sum([len(token) for token in log])
                    coverage.append(cov)
                else:
                    coverage.append(0)
            
            best_cov = max(coverage)
            if not best_cov:
                continue

            if word_no > 20:
                # avoid parsing really long lines. If the log message didn't start within the
                # first 20 words, it's probably not a known message
                return None

                # # no match found, may have been a named log level. try next word
                # if word in ["warning:", "ERROR:", "SEVERE:", "UNKNOWN:"]:
                #     continue
                # else:
                #     # duration = time.time() - start_time
                #     # print duration
                #     continue
        
            best_match = self.logs_by_word[word][coverage.index(best_cov)]
            return self.log_code_lines[best_match]

    def _strip_counters(self, sub_line):
        """ finds the ending part of the codeline by 
            taking out the counters and durations
        """
        try:
            end = sub_line.rindex('}')
        except ValueError, e:
            return sub_line
        else:
            return sub_line[:(end + 1)]

    def _strip_datetime(self,sub_line):
        """ strip out datetime and other parts so that
            there is no redundancy
        """
        try:
            begin = sub_line.index(']')
        except ValueError, e:
            return sub_line
        else:
            # create a "" in place character for the beginnings..
            # needed when interleaving the lists
            sub = sub_line[begin + 1:]
            return sub


    def _find_variable(self, pattern, logline):
        """ return the variable parts of the code 
            given a tuple of strings pattern
            ie. (this, is, a, pattern) -> 'this is a good pattern' -> [good]
        """
        var_subs = []
        # find the beginning of the pattern
        first_index = logline.index(pattern[0])
        beg_str = logline[:first_index]
        #strip the beginning substring
        var_subs.append(self._strip_datetime(beg_str))

        for patt, patt_next in zip(pattern[:-1], pattern[1:]):
            # regular expression pattern that finds what's in the middle of two substrings
            pat = re.escape(patt) + '(.*)' + re.escape(patt_next)
            # extract whats in the middle of the two substrings
            between = re.search(pat, logline)
            try:
                # add what's in between if the search isn't none 
                var_subs.append(between.group(1))
            except Exception, e:
                pass
        rest_of_string = logline.rindex(pattern[-1]) + len(pattern[-1])

        # add the rest of the string to the end minus the counters and durations
        end_str = logline[rest_of_string:]
        var_subs.append(self._strip_counters(end_str))

        # strip whitespace from each string, but keep the strings themselves
        # var_subs = [v.strip() for v in var_subs]

        return var_subs

    def _variable_parts(self, line, codeline):
        """returns the variable parts of the codeline, 
            given the static parts
        """
        var_subs = []
        # codeline has the pattern and then has the outputs in different versions
        if codeline:
            var_subs = self._find_variable(codeline.pattern, line)
        else:
            # make the variable part of the line string without all the other stuff
            line_str= self._strip_datetime(self._strip_counters(line))
            var_subs= [line_str.strip()]
        return var_subs

    def __call__(self, line, variable=False):
        """ returns a tuple of the log2code and variable parts
            when the class is called
        """

        if variable:
            log2code = self._log2code(line)
            return log2code, self._variable_parts(line,log2code)
        else:
            return self._log2code(line), None


    def combine(self, pattern, variable):
        """ combines a pattern and variable parts to be a line string again. """
        
        inter_zip= izip_longest(variable, pattern, fillvalue='')
        interleaved = [elt for pair in inter_zip for elt in pair ]
        return ''.join(interleaved)






# class MLog2Code(object):

#     def __init__(self):
#         self._import_l2c_db()
#         self._parse_args()
#         self.analyse()

#     def _import_l2c_db(self):
#         self.all_versions, self.logs_versions, self.logs_by_word, self.log_code_lines = \
#             cPickle.load(open('./logdb.pickle', 'rb'))

#     def _parse_args(self):
#         # create parser object
#         parser = argparse.ArgumentParser(description='mongod/mongos log file to code line converter (BETA)')

#         # only create default argument if not using stdin
#         if sys.stdin.isatty():
#             parser.add_argument('logfile', action='store', help='looks up and prints out information about where a log line originates from the code.')

#         self.args = vars(parser.parse_args())

#     def analyse(self):
#         # open logfile
#         if sys.stdin.isatty():
#             logfile = open(self.args['logfile'], 'r')
#         else:
#             logfile = sys.stdin

#         for i, line in enumerate(logfile): 
#             match = self.log2code(line)

#             if  match:
#                 print line,
#                 print self.logs_versions[match]
#                 print self.log_code_lines[match]


#     def log2code(self, line):
#         tokens = line.split()

#         # find first word in line that has a corresponding log message stored
#         word = next((w for w in tokens if w in self.logs_by_word), None)
#         if not word:
#             return None

#         # go through all error messages starting with this word
#         coverage = []
#         for log in self.logs_by_word[word]:

#             if all([line.find(token) >= 0 for token in log]):
#                 # all tokens match, calculate coverage
#                 cov = sum([len(token) for token in log])
#                 coverage.append(cov)
#             else:
#                 coverage.append(0)
        
#         best_cov = max(coverage)
#         if not best_cov:
#             return None
        
#         best_match = self.logs_by_word[word][coverage.index(best_cov)]
#         return best_match



# if __name__ == '__main__':
#         l2cc = Log2CodeConverter()
#         lcl = l2cc("""Sun Mar 24 00:44:16.295 [conn7815] moveChunk migrate commit accepted by TO-shard: { active: true, ns: "db.coll", from: "shard001:27017", min: { i: ObjectId('4b7730748156791f310b03a3'), m: "stats", t: new Date(1348272000000) }, max: { i: ObjectId('4b8f826192f9e2154d05dda7'), m: "mongo", t: new Date(1345680000000) }, shardKeyPattern: { i: 1.0, m: 1.0, t: 1.0 }, state: "done", counts: { cloned: 3115, clonedBytes: 35915282, catchup: 0, steady: 0 }, ok: 1.0 }""")
#         print lcl.versions

        #possible_versions = possible_versions & set(logs_versions[best_match])


        # if len(possible_versions) != old_num_v:
        #     print i, line.rstrip()
        #     print "    best_match:", best_match
        #     print "    log message only present in versions:", logs_versions[best_match]
        #     print "    this limits the possible versions to:", possible_versions
        #     print

        # if not possible_versions:
        #     raise SystemExit


    # print "possible versions:", ", ".join([pv[1:] for pv in possible_versions])
    # for pv in possible_versions:
    #     print pv, possible_versions[pv]

    # plt.bar(range(len(possible_versions.values())), possible_versions.values(), align='center')
    # plt.xticks(range(len(possible_versions.keys())), possible_versions.keys(), size='small', rotation=90)
    # plt.show()


########NEW FILE########
__FILENAME__ = logcodeline
from collections import defaultdict

class LogCodeLine(object):
    """ LogCodeLine represents a logevent pattern extracted from the source code.
        The pattern is a tuple of constant strings, variables are cut out.
        LogCodeLine stores "matches" of the same log pattern from different
        source files and different versions of the code. 

        A match is a tuple of (filename, line number, loglevel, trigger). Matches
        are stored in a dictionary with the git tag version as they key, e.g. 
        "r2.2.3".

        The import_l2c_db.py tool extracts all such patterns and creates LogCodeLines 
        for each pattern.
    """

    def __init__(self, pattern, pattern_id):
        """ constructor takes a pattern, which is a tuple of strings. """
        self.pattern = pattern
        self.pattern_id = pattern_id
        self.versions = set()
        self.matches = defaultdict(list)

    def addMatch(self, version, filename, lineno, loglevel, trigger):
        """ adding a match to the LogCodeLine, including the version, filename
            of the source file, the line number, and the loglevel. 
        """
        self.versions.add(version)
        self.matches[version].append((filename, lineno, loglevel, trigger))

    def __str__(self):
        """ String representation of a LogCodeLine, outputs all matches of 
            the pattern.
        """
        s = "%s\n"%(" <var> ".join(self.pattern))
        for version in sorted(self.versions):
            for filename, lineno, loglevel, trigger in self.matches[version]:
                s += "{:>10}: in {}:{}, loglevel {}, trigger {}\n".format(version, filename, lineno, loglevel, trigger)
        return s


########NEW FILE########
__FILENAME__ = logevent
from datetime import datetime
from dateutil.tz import tzutc
import dateutil.parser
import re
import json

from mtools.util.pattern import json2pattern


class DateTimeEncoder(json.JSONEncoder):
    """ custom datetime encoder for json output. """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class LogEvent(object):
    """ LogEvent extracts information from a mongod/mongos log file line and
        stores the following properties/variables:

        line_str: the original line string
        split_tokens: a list of string tokens after splitting line_str using
                      whitespace as split points
        datetime: a datetime object for the logevent. For logfiles created with
                  version 2.4+, it also contains micro-seconds
        duration: the duration of a timed operation in ms
        thread: the thread name (e.g. "conn1234") as string
        operation: insert, update, remove, query, command, getmore, None
        namespace: the namespace of the operation, or None

        Certain operations also add the number of affected/scanned documents.
        If applicable, the following variables are also set, otherwise the
        default is None: nscanned, ntoreturn, nreturned, ninserted, nupdated

        For performance reason, all fields are evaluated lazily upon first
        request.
    """

    # datetime handler for json encoding
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, \
        datetime) else None

    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', \
        'Oct', 'Nov', 'Dec']


    def __init__(self, doc_or_str):
        self._year_rollover = False

        if isinstance(doc_or_str, str):
            # create from string, remove line breaks at end of _line_str
            self.from_string = True
            self._line_str = doc_or_str.rstrip()
            self._profile_doc = None
            self._reset()
        else:
            self.from_string = False
            self._profile_doc = doc_or_str
            # docs don't need to be parsed lazily, they are fast
            self._parse_document()



    def _reset(self):
        self._split_tokens_calculated = False
        self._split_tokens = None

        self._duration_calculated = False
        self._duration = None

        self._datetime_calculated = False
        self._datetime = None
        self._datetime_nextpos = None
        self._datetime_format = None
        self._datetime_str = ''

        self._thread_calculated = False
        self._thread = None

        self._operation_calculated = False
        self._operation = None
        self._namespace = None

        self._pattern = None
        self._sort_pattern = None

        self._counters_calculated = False
        self._nscanned = None
        self._ntoreturn = None
        self._nupdated = None
        self._nreturned = None
        self._ninserted = None
        self._ndeleted = None
        self._numYields = None
        self._r = None
        self._w = None

        self.merge_marker_str = ''

    def set_line_str(self, line_str):
        """ line_str is only writeable if LogEvent was created from a string, not from a system.profile documents. """

        if not self.from_string:
            raise ValueError("can't set line_str for LogEvent created from system.profile documents.")

        if line_str != self._line_str:
            self._line_str = line_str.rstrip()
            self._reset()


    def get_line_str(self):
        """ return line_str depending on source, logfile or system.profile. """

        if self.from_string:
            return ' '.join([s for s in [self.merge_marker_str, self._datetime_str, self._line_str] if s])
        else:
            return ' '.join([s for s in [self._datetime_str, self._line_str] if s])

    line_str = property(get_line_str, set_line_str)


    @property
    def split_tokens(self):
        """ splits string into tokens (lazy) """

        if not self._split_tokens_calculated:
            # split into items (whitespace split)
            self._split_tokens = self._line_str.split()
            self._split_tokens_calculated = True

        return self._split_tokens


    @property
    def duration(self):
        """ calculate duration if available (lazy) """

        if not self._duration_calculated:
            self._duration_calculated = True

            # split_tokens = self.split_tokens
            line_str = self.line_str

            if line_str and line_str.endswith('ms'):
                try:
                    # find duration from end
                    space_pos = line_str.rfind(" ")
                    if space_pos == -1:
                        return
                    self._duration = int(line_str[line_str.rfind(" ")+1:-2].replace(',',''))
                except ValueError:
                    self._duration = None
            elif "flushing" in self.line_str:
                matchobj = re.search(r'flushing mmaps took (\d+)ms', self.line_str)
                if matchobj:
                    self._duration = int(matchobj.group(1))

        return self._duration


    @property
    def datetime(self):
        """ extract datetime if available (lazy) """

        if not self._datetime_calculated:
            self._datetime_calculated = True

            # if no datetime after 10 tokens, break to avoid parsing very long lines
            split_tokens = self.split_tokens[:10]

            match_found = False
            for offs in xrange(len(split_tokens)):
                dt = self._match_datetime_pattern(split_tokens[offs:offs+4])
                if dt:
                    self._datetime = dt
                    self._datetime_nextpos = offs
                    if self._datetime_format.startswith("iso8601"):
                        self._datetime_nextpos += 1
                    else:
                        self._datetime_nextpos += 4

                    # separate datetime str and linestr
                    self._line_str = ' '.join(self.split_tokens[self._datetime_nextpos:])
                    self._reformat_timestamp(self._datetime_format)
                    break

        return self._datetime


    @property
    def datetime_format(self):
        if not self._datetime_calculated:
            _ = self.datetime

        return self._datetime_format


    @property
    def datetime_nextpos(self):
        if self._datetime_nextpos == None and not self._datetime_calculated:
            _ = self.datetime
        return self._datetime_nextpos


    def set_datetime_hint(self, format, nextpos, rollover):
        self._datetime_format = format
        self._datetime_nextpos = nextpos
        self._year_rollover = rollover

        # fast check if timezone changed. if it has, trigger datetime evaluation
        if format.startswith('ctime'):
            if len(self.split_tokens) < 4 or self.split_tokens[self._datetime_nextpos-4] not in self.weekdays:
                _ = self.datetime
                return False
            return True
        else:
            if not self.split_tokens[self._datetime_nextpos-1][0].isdigit():
                _ = self.datetime
                return False
            return True


    def _match_datetime_pattern(self, tokens):
        """ Helper method that takes a list of tokens and tries to match
            the datetime pattern at the beginning of the token list.

            There are several formats that this method needs to understand
            and distinguish between (see MongoDB's SERVER-7965):

            ctime-pre2.4    Wed Dec 31 19:00:00
            ctime           Wed Dec 31 19:00:00.000
            iso8601-utc     1970-01-01T00:00:00.000Z
            iso8601-local   1969-12-31T19:00:00.000+0500
        """
        # first check: less than 4 tokens can't be ctime
        assume_iso8601_format = len(tokens) < 4

        # check for ctime-pre-2.4 or ctime format
        if not assume_iso8601_format:
            weekday, month, day, time = tokens[:4]
            if len(tokens) < 4 or (weekday not in self.weekdays) or \
               (month not in self.months) or not day.isdigit():
                assume_iso8601_format = True

        if assume_iso8601_format:
            # sanity check, because the dateutil parser could interpret
            # any numbers as a valid date
            if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}', \
                            tokens[0]):
                return None

            # convinced that this is a ISO-8601 format, the dateutil parser
            # will do the rest
            dt = dateutil.parser.parse(tokens[0])
            self._datetime_format = "iso8601-utc" \
                if tokens[0].endswith('Z') else "iso8601-local"

        else:
            # assume current year unless self.year_rollover is set (from LogFile)
            year = datetime.now().year
            dt = dateutil.parser.parse(' '.join(tokens[:4]), default=datetime(year, 1, 1))

            if dt.tzinfo == None:
                dt = dt.replace(tzinfo=tzutc())

            if self._year_rollover and dt > self._year_rollover:
                dt = dt.replace(year=year-1)

            self._datetime_format = "ctime" \
                if '.' in tokens[3] else "ctime-pre2.4"

        return dt


    @property
    def thread(self):
        """ extract thread name if available (lazy) """

        if not self._thread_calculated:
            self._thread_calculated = True

            split_tokens = self.split_tokens

            if not self.datetime_nextpos or len(split_tokens) <= self.datetime_nextpos:
                return None

            connection_token = split_tokens[self.datetime_nextpos]
            match = re.match(r'^\[([^\]]*)\]$', connection_token)
            if match:
                self._thread = match.group(1)

        return self._thread


    @property
    def operation(self):
        """ extract operation (query, insert, update, remove, getmore, command)
            if available (lazy) """

        if not self._operation_calculated:
            self._operation_calculated = True
            self._extract_operation_and_namespace()

        return self._operation


    @property
    def namespace(self):
        """ extract namespace if available (lazy) """

        if not self._operation_calculated:
            self._operation_calculated = True
            self._extract_operation_and_namespace()

        return self._namespace


    def _extract_operation_and_namespace(self):
        """ Helper method to extract both operation and namespace from a
            logevent. It doesn't make sense to only extract one as they
            appear back to back in the token list.
        """

        split_tokens = self.split_tokens

        if not self._datetime_nextpos:
            # force evaluation of datetime to get access to datetime_offset
            _ = self.datetime

        if not self._datetime_nextpos or len(split_tokens) <= self._datetime_nextpos + 2:
            return

        op = split_tokens[self._datetime_nextpos + 1]

        if op in ['query', 'insert', 'update', 'remove', 'getmore', 'command']:
            self._operation = op
            self._namespace = split_tokens[self._datetime_nextpos + 2]



    @property
    def pattern(self):
        """ extract query pattern from operations """

        if not self._pattern:

            # trigger evaluation of operation
            if self.operation in ['query', 'getmore', 'update', 'remove']:
                self._pattern = self._find_pattern('query: ')

        return self._pattern

    
    @property
    def sort_pattern(self):
        """ extract query pattern from operations """

        if not self._sort_pattern:

            # trigger evaluation of operation
            if self.operation in ['query', 'getmore']:
                self._sort_pattern = self._find_pattern('orderby: ')

        return self._sort_pattern


    @property
    def nscanned(self):
        """ extract nscanned counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nscanned

    @property
    def ntoreturn(self):
        """ extract ntoreturn counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ntoreturn


    @property
    def nreturned(self):
        """ extract nreturned counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nreturned


    @property
    def ninserted(self):
        """ extract ninserted counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ninserted

    @property
    def ndeleted(self):
        """ extract ndeleted counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ndeleted

    @property
    def nupdated(self):
        """ extract nupdated counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nupdated

    @property
    def numYields(self):
        """ extract numYields counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._numYields

    @property
    def r(self):
        """ extract read lock (r) counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._r

    @property
    def w(self):
        """ extract write lock (w) counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._w


    def _extract_counters(self):
        """ Helper method to extract counters like nscanned, nreturned, etc.
            from the logevent.
        """

        # extract counters (if present)
        counters = ['nscanned', 'ntoreturn', 'nreturned', 'ninserted', \
            'nupdated', 'ndeleted', 'r', 'w', 'numYields']

        split_tokens = self.split_tokens

        # trigger thread evaluation to get access to offset
        if self.thread:
            for t, token in enumerate(split_tokens[self.datetime_nextpos+2:]):
                for counter in counters:
                    if token.startswith('%s:'%counter):
                        try:
                            vars(self)['_'+counter] = int((token.split(':')[-1]).replace(',', ''))
                        except ValueError:
                            # see if this is a pre-2.5.2 numYields with space in between (e.g. "numYields: 2")
                            # https://jira.mongodb.org/browse/SERVER-10101
                            if counter == 'numYields' and token.startswith('numYields'):
                                try:
                                    self._numYields = int((split_tokens[t+1+self.datetime_nextpos+2]).replace(',', ''))
                                except ValueError:
                                    pass
                        # token not parsable, skip
                        break



    def parse_all(self):
        """ triggers the extraction of all information, which would usually
            just be evaluated lazily.
        """
        tokens = self.split_tokens
        duration = self.duration
        datetime = self.datetime
        thread = self.thread
        operation = self.operation
        namespace = self.namespace
        pattern = self.pattern
        nscanned = self.nscanned
        ntoreturn = self.ntoreturn
        nreturned = self.nreturned
        ninserted = self.ninserted
        ndeleted = self.ndeleted
        nupdated = self.nupdated
        numYields = self.numYields
        w = self.w
        r = self.r


    def _find_pattern(self, trigger):

        # get start of json query pattern
        start_idx = self.line_str.rfind(trigger)
        if start_idx == -1:
            # no query pattern found
            return None

        stop_idx = 0
        brace_counter = 0
        search_str = self.line_str[start_idx+len(trigger):]

        for match in re.finditer(r'{|}', search_str):
            stop_idx = match.start()
            if search_str[stop_idx] == '{':
                brace_counter += 1
            else:
                brace_counter -= 1
            if brace_counter == 0:
                break
        search_str = search_str[:stop_idx+1].strip()
        if search_str:
            return json2pattern(search_str)
        else:
            return None



    def _reformat_timestamp(self, format, force=False):
        if format not in ['ctime', 'ctime-pre2.4', 'iso8601-utc', 'iso8601-local']:
            raise ValueError('invalid datetime format %s, choose from ctime, ctime-pre2.4, iso8601-utc, iso8601-local.')

        if (self.datetime_format == None or (self.datetime_format == format and self._datetime_str != '')) and not force:
            return
        elif self.datetime == None:
            return
        elif format.startswith('ctime'):
            dt_string = self.weekdays[self.datetime.weekday()] + ' ' + self.datetime.strftime("%b %d %H:%M:%S")
            # remove zero-padding from day number
            tokens = dt_string.split(' ')
            if tokens[2].startswith('0'):
                tokens[2] = tokens[2].replace('0', ' ', 1)
            dt_string = ' '.join(tokens)
            if format == 'ctime':
                dt_string += '.' + str(int(self.datetime.microsecond / 1000)).zfill(3)
        elif format == 'iso8601-local':
            dt_string = self.datetime.isoformat()
            if not self.datetime.utcoffset():
                dt_string += '+00:00'
            ms_str = str(int(self.datetime.microsecond * 1000)).zfill(3)[:3]
            # change isoformat string to have 3 digit milliseconds and no : in offset
            dt_string = re.sub(r'(\.\d+)?([+-])(\d\d):(\d\d)', '.%s\\2\\3\\4'%ms_str, dt_string)
        elif format == 'iso8601-utc':
            if self.datetime.utcoffset():
                dt_string = self.datetime.astimezone(tzutc()).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                dt_string = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")
            dt_string += '.' + str(int(self.datetime.microsecond * 1000)).zfill(3)[:3] + 'Z'

        # set new string and format
        self._datetime_str = dt_string
        self._datetime_format = format


    def __str__(self):
        """ default string conversion for a LogEvent object is just its line_str. """
        return str(self.line_str)


    def to_dict(self, labels=None):
        """ converts LogEvent object to a dictionary. """
        output = {}
        if labels == None:
            labels = ['line_str', 'split_tokens', 'datetime', 'operation', \
                'thread', 'namespace', 'nscanned', 'ntoreturn',  \
                'nreturned', 'ninserted', 'nupdated', 'ndeleted', 'duration', 'r', 'w', 'numYields']

        for label in labels:
            value = getattr(self, label, None)
            if value != None:
                output[label] = value

        return output


    def to_json(self, labels=None):
        """ converts LogEvent object to valid JSON. """
        output = self.to_dict(labels)
        return json.dumps(output, cls=DateTimeEncoder, ensure_ascii=False)


    def _parse_document(self):
        """ Parses a system.profile document and copies all the values to the member variables. """
        doc = self._profile_doc

        self._split_tokens_calculated = True
        self._split_tokens = None

        self._duration_calculated = True
        self._duration = doc[u'millis']

        self._datetime_calculated = True
        self._datetime = doc[u'ts']
        if self._datetime.tzinfo == None:
            self._datetime = self._datetime.replace(tzinfo=tzutc())
        self._datetime_format = None
        self._reformat_timestamp('ctime', force=True)

        self._thread_calculated = True
        self._thread = doc['thread']

        self._operation_calculated = True
        self._operation = doc[u'op']
        self._namespace = doc[u'ns']

        # query pattern for system.profile events, all three cases (see SERVER-13245)
        if 'query' in doc:
            if 'query' in doc['query'] and isinstance(doc['query']['query'], dict):
                self._pattern = str(doc['query']['query']).replace("'", '"')
            elif '$query' in doc['query']:
                self._pattern = str(doc['query']['$query']).replace("'", '"')
            else:
                self._pattern = str(doc['query']).replace("'", '"')

            # sort pattern
            if 'orderby' in doc['query'] and isinstance(doc['query']['orderby'], dict):
                self._sort_pattern = str(doc['query']['orderby']).replace("'", '"')    
            elif '$orderby' in doc['query']:
                self._sort_pattern = str(doc['query']['$orderby']).replace("'", '"')
            else: 
                self._sort_pattern = None

        self._counters_calculated = True
        self._nscanned = doc[u'nscanned'] if 'nscanned' in doc else None
        self._ntoreturn = doc[u'ntoreturn'] if 'ntoreturn' in doc else None
        self._nupdated = doc[u'nupdated'] if 'nupdated' in doc else None
        self._nreturned = doc[u'nreturned'] if 'nreturned' in doc else None
        self._ninserted = doc[u'ninserted'] if 'ninserted' in doc else None
        self._ndeleted = doc[u'ndeleted'] if 'ndeleted' in doc else None
        self._numYields = doc[u'numYield'] if 'numYield' in doc else None
        self._r = doc[u'lockStats'][u'timeLockedMicros'][u'r']
        self._w = doc[u'lockStats'][u'timeLockedMicros'][u'w']

        self._r_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'r']
        self._w_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'w']

        # build a fake line_str
        payload = ''
        if 'query' in doc:
            payload += 'query: %s' % str(doc[u'query']).replace("u'", "'").replace("'", '"')
        if 'command' in doc:
            payload += 'command: %s' % str(doc[u'command']).replace("u'", "'").replace("'", '"')
        if 'updateobj' in doc:
            payload += ' update: %s' % str(doc[u'updateobj']).replace("u'", "'").replace("'", '"')

        scanned = 'nscanned:%i'%self._nscanned if 'nscanned' in doc else ''
        yields = 'numYields:%i'%self._numYields if 'numYield' in doc else ''
        locks = 'w:%i' % self.w if self.w != None else 'r:%i' % self.r
        duration = '%ims' % self.duration if self.duration != None else ''

        self._line_str = "[{thread}] {operation} {namespace} {payload} {scanned} {yields} locks(micros) {locks} {duration}".format(
            datetime=self.datetime, thread=self.thread, operation=self.operation, namespace=self.namespace, payload=payload, scanned=scanned, yields=yields, locks=locks, duration=duration)

########NEW FILE########
__FILENAME__ = logfile
from mtools.util.logevent import LogEvent
from mtools.util.input_source import InputSource

from math import ceil 
from datetime import datetime
import time
import re

class LogFile(InputSource):
    """ wrapper class for log files, either as open file streams of from stdin. """

    def __init__(self, filehandle):
        """ provide logfile as open file stream or stdin. """
        self.filehandle = filehandle
        self.name = filehandle.name
        
        self.from_stdin = filehandle.name == "<stdin>"
        self._start = None
        self._end = None
        self._filesize = None
        self._num_lines = None
        self._restarts = None
        self._binary = None
        self._timezone = None

        self._datetime_format = None
        self._year_rollover = None

        # make sure bounds are calculated before starting to iterate, including potential year rollovers
        self._calculate_bounds()

    @property
    def start(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if not self._start:
            self._calculate_bounds()
        return self._start

    @property
    def end(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if not self._end:
            self._calculate_bounds()
        return self._end

    @property
    def timezone(self):
        """ lazy evaluation of timezone of logfile. """
        if not self._timezone:
            self._calculate_bounds()
        return self._timezone

    @property
    def filesize(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if self.from_stdin:
            return None
        if not self._filesize:
            self._calculate_bounds()
        return self._filesize

    @property
    def datetime_format(self):
        """ lazy evaluation of the datetime format. """
        if not self._datetime_format:
            self._calculate_bounds()
        return self._datetime_format

    @property
    def year_rollover(self):
        """ lazy evaluation of the datetime format. """
        if self._year_rollover == None:
            self._calculate_bounds()
        return self._year_rollover

    @property
    def num_lines(self):
        """ lazy evaluation of the number of lines. Returns None for stdin input currently. """
        if self.from_stdin:
            return None
        if not self._num_lines:
            self._iterate_lines()
        return self._num_lines

    @property
    def restarts(self):
        """ lazy evaluation of all restarts. """
        if not self._num_lines:
            self._iterate_lines()
        return self._restarts

    @property
    def binary(self):
        """ lazy evaluation of the binary name. """
        if not self._num_lines:
            self._iterate_lines()
        return self._binary

    @property
    def versions(self):
        """ return all version changes. """
        versions = []
        for v, _ in self.restarts:
            if len(versions) == 0 or v != versions[-1]:
                versions.append(v)
        return versions

    def next(self):
        """ get next line, adjust for year rollover and hint datetime format. """

        # use readline here because next() iterator uses internal readahead buffer so seek position is wrong
        line = self.filehandle.readline()
        if line == '':
            raise StopIteration
        line = line.rstrip('\n')

        le = LogEvent(line)
        
        # hint format and nextpos from previous line
        if self._datetime_format and self._datetime_nextpos != None:
            ret = le.set_datetime_hint(self._datetime_format, self._datetime_nextpos, self.year_rollover)
            if not ret:
                # logevent indicates timestamp format has changed, invalidate hint info
                self._datetime_format = None
                self._datetime_nextpos = None
        elif le.datetime:
            # print "not hinting"
            # gather new hint info from another logevent
            self._datetime_format = le.datetime_format
            self._datetime_nextpos = le._datetime_nextpos  

        return le

    def __iter__(self):
        """ iteration over LogFile object will return a LogEvent object for each line (generator) """
        le = None
        
        while True:
            try:
                le = self.next()
            except StopIteration as e:
                # end of log file, get end date
                if not self.end and self.from_stdin:
                    if le and le.datetime:
                        self._end = le.datetime

                # future iterations start from the beginning
                if not self.from_stdin:
                    self.filehandle.seek(0)
                
                # now raise StopIteration exception
                raise e

            # get start date for stdin input
            if not self.start and self.from_stdin:
                if le and le.datetime:
                    self._start = le.datetime

            yield le


    def __len__(self):
        """ return the number of lines in a log file. """
        return self.num_lines


    def _iterate_lines(self):
        """ count number of lines (can be expensive). """
        self._num_lines = 0
        self._restarts = []

        l = 0
        for l, line in enumerate(self.filehandle):

            # find version string
            if "version" in line:

                restart = None
                # differentiate between different variations
                if "mongos" in line or "MongoS" in line:
                    self._binary = 'mongos'
                elif "db version v" in line:
                    self._binary = 'mongod'

                else: 
                    continue

                version = re.search(r'(\d\.\d\.\d+)', line)
                if version:
                    version = version.group(1)
                    restart = (version, LogEvent(line))
                    self._restarts.append(restart)

        self._num_lines = l+1

        # reset logfile
        self.filehandle.seek(0)


    def _calculate_bounds(self):
        """ calculate beginning and end of logfile. """

        if self.from_stdin: 
            return False

        # get start datetime 
        for line in self.filehandle:
            logevent = LogEvent(line)
            if logevent.datetime:
                self._start = logevent.datetime
                self._timezone = logevent.datetime.tzinfo
                self._datetime_format = logevent.datetime_format
                self._datetime_nextpos = logevent._datetime_nextpos
                break

        # get end datetime (lines are at most 10k, go back 30k at most to make sure we catch one)
        self.filehandle.seek(0, 2)
        self._filesize = self.filehandle.tell()
        self.filehandle.seek(-min(self._filesize, 30000), 2)

        for line in reversed(self.filehandle.readlines()):
            logevent = LogEvent(line)
            if logevent.datetime:
                self._end = logevent.datetime
                break

        # if there was a roll-over, subtract 1 year from start time
        if self._end < self._start:
            self._start = self._start.replace(year=self._start.year-1)
            self._year_rollover = self._end
        else:
            self._year_rollover = False

        # reset logfile
        self.filehandle.seek(0)

        return True


    def _find_curr_line(self, prev=False):
        """ internal helper function that finds the current (or previous if prev=True) line in a log file
            based on the current seek position.
        """
        curr_pos = self.filehandle.tell()
        line = None

        # jump back 15k characters (at most) and find last newline char
        jump_back = min(self.filehandle.tell(), 15000)
        self.filehandle.seek(-jump_back, 1)
        buff = self.filehandle.read(jump_back)
        self.filehandle.seek(curr_pos, 0)

        newline_pos = buff.rfind('\n')
        if prev:
            newline_pos = buff[:newline_pos].rfind('\n')

        # move back to last newline char
        if newline_pos == -1:
            self.filehandle.seek(0)
            return self.next()

        self.filehandle.seek(newline_pos - jump_back + 1, 1)

        # roll forward until we found a line with a datetime
        try:
            logevent = self.next()
            while not logevent.datetime:
                logevent = self.next()

            return logevent
        except StopIteration:
            # reached end of file
            return None


    def fast_forward(self, start_dt):
        """ Fast-forward a log file to the given start_dt datetime object using binary search.
            Only fast for files. Streams need to be forwarded manually, and it will miss the 
            first line that would otherwise match (as it consumes the log line). 
        """
        if self.from_stdin:
            # skip lines until start_dt is reached
            return

        else:
            # fast bisection path
            min_mark = 0
            max_mark = self.filesize
            step_size = max_mark

            # check if start_dt is already smaller than first datetime
            self.filehandle.seek(0)
            le = self.next()
            if le.datetime and le.datetime >= start_dt:
                self.filehandle.seek(0)
                return

            le = None
            self.filehandle.seek(0)

            # search for lower bound
            while abs(step_size) > 100:
                step_size = ceil(step_size / 2.)
                
                self.filehandle.seek(step_size, 1)
                le = self._find_curr_line()
                if not le:
                    break
                                
                if le.datetime >= start_dt:
                    step_size = -abs(step_size)
                else:
                    step_size = abs(step_size)

            if not le:
                return

            # now walk backwards until we found a truely smaller line
            while le and self.filehandle.tell() >= 2 and le.datetime >= start_dt:
                self.filehandle.seek(-2, 1)
                le = self._find_curr_line(prev=True)




########NEW FILE########
__FILENAME__ = parse_sourcecode
import os
import re
import sys
import commands
import subprocess
import cPickle
from collections import defaultdict

from mtools.util.logcodeline import LogCodeLine

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


mongodb_path = "/Users/tr/Documents/code/mongo/"
git_path = "/usr/bin/git"
pattern_id = 0

def source_files(mongodb_path):
    for root, dirs, files in os.walk(mongodb_path):
        for filename in files:
            # skip files in dbtests folder
            if 'dbtests' in root:
                continue
            if filename.endswith(('.cpp', '.c', '.h')):
                yield os.path.join(root, filename)

def get_all_versions():
    pr = subprocess.Popen(git_path + " checkout master", 
                          cwd = mongodb_path, 
                          shell = True, 
                          stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE)
    pr.communicate()

    pr = subprocess.Popen(git_path + " tag", 
                          cwd = mongodb_path, 
                          shell = True, 
                          stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE)

    (out, error) = pr.communicate()
    versions = out.split()

    # only newer than 1.8.0
    versions = versions[versions.index("r1.8.0"):]

    # remove release candidates
    versions = [v for v in versions if "rc" not in v]

    # remove developer versions
    versions = [v for v in versions if re.search(r'\.[02468]\.', v)]

    # add master logs
    versions.append('master')

    return versions


def switch_version(version):
    pr = subprocess.Popen(git_path + " checkout %s"%version, 
                          cwd = os.path.dirname( mongodb_path ), 
                          shell = True, 
                          stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE)

    (out, error) = pr.communicate()
    print error


def output_verbose(version, filename, lineno, line, statement, matches, accepted, why):
    print "%10s %s %s:%s" % ("location:", version, filename, lineno)
    print "%10s %s"       % ("line:", line)
    print "%10s %s"       % ("statement:", statement)
    print "%10s %s"       % ("matches:", matches)
    print "%10s %s"       % ("accepted:", accepted)
    print "%10s %s"       % ("reason:", why)
    print "----------------------------"
    print 


def extract_logs(log_code_lines, current_version):
    global pattern_id
    log_templates = set()
    log_triggers = [" log(", " LOG(", " LOGSOME", " warning()", " error()", " out()", " problem()"]

    for filename in source_files(mongodb_path):
        f = open(filename, 'r')

        # remove parent path
        filename = filename[len(mongodb_path):]

        lines = f.readlines()
        for lineno, line in enumerate(lines):
            trigger = next((t for t in log_triggers if t in line), None)
            
            if trigger:
                # extend line to wrap over line breaks until ; at end of line is encountered
                statement = line
                current_lineno = lineno

                semicolon_match = None
                while not semicolon_match:
                    current_lineno += 1
                    if current_lineno >= len(lines):
                        break
                    statement += lines[current_lineno]
                    # match semicolon at end of line (potentially with whitespace between)
                    semicolon_match = re.search(';\s*$', statement, flags=re.MULTILINE)
                    if semicolon_match:
                        statement = statement[:semicolon_match.start()]
                        break

                # exclude triggers in comments (both // and /* */)
                trigger_pos = statement.find(trigger)
                newline_pos = statement.rfind("\n", 0, trigger_pos)
                if statement.find("//", newline_pos+1, trigger_pos) != -1:
                    # output_verbose(current_version, filename, lineno, line, statement, "comment //")
                    continue
                comment_pos = statement.find("/*", 0, trigger_pos)
                if comment_pos != -1:
                    if statement.find("*/", comment_pos+2, trigger_pos) == -1:
                        # output_verbose(current_version, filename, lineno, line, statement, "comment /* */")
                        continue

                statement = statement[statement.find(trigger)+len(trigger):].strip()

                # unescape strings
                # statement = statement.decode("string-escape")
                # print statement

                # remove compiler #ifdef .. #endif directives
                statement = re.sub(r'#ifdef.*?#endif', '', statement, flags=re.DOTALL)

                # filtering out conditional strings with tertiary operator: ( ... ? ... : ... )
                statement = re.sub(r'\(.*?\?.*?\:.*?\)', '', statement)

                # split into stream tokens
                stream_tokens = statement.split("<<")

                # remove newlines from stream tokens
                stream_tokens = [re.sub('\n', '', s).strip() for s in stream_tokens]

                matches = []
                for s in stream_tokens:
                    # match only non-empty strings with single / double quotes
                    match = re.match(r'"(.+?)"', s)
                    if match:
                        match = re.sub(r'(\\t)|(\\n)|"', '', match.group(1)).strip()
                        matches.append(match)


                # # get all double-quoted strings surrounded by << or ending in ;
                # print "s:::", statement
                # matches = re.findall(r"<\s*\"(.*?)\"\s*(?:<|;)", statement, flags=re.DOTALL)
                # print matches

                # # remove tabs, double quotes and newlines and strip whitespace from matches
                # matches = [re.sub(r'(\\t)|(\\n)|"', '', m).strip() for m in matches]    
                # print matches

                # remove empty tokens
                matches = [m for m in matches if m]

                # skip empty matches
                if len(matches) == 0:
                    # output_verbose(current_version, filename, lineno, line, statement, matches, False, "zero matches")
                    continue

                # skip matches with total character length < 3
                if len(''.join(matches)) < 3:
                    continue

                # skip matches consisting of single word, this will discard some valid log lines but overall improves performance
                if len(matches) == 1 and " " not in matches[0]:
                    continue

                # special case that causes trouble because of query operation lines
                if matches[0] == "query:":
                    # output_verbose(current_version, filename, lineno, line, statement, matches, False, "contains 'query:'")
                    continue

                loglevel = re.search(r'LOG\(\s*([0-9])\s*\)', line)
                if loglevel:
                    loglevel = int(loglevel.group(1))

                if trigger == ' log(':
                    loglevel = 0

                pattern = tuple(matches)

                # add to log_code_lines dict
                if not pattern in log_code_lines:
                    log_code_lines[pattern] = LogCodeLine(pattern, pattern_id)
                    pattern_id += 1

                # clean up values
                lineno = lineno+1
                trigger = trigger.strip()

                log_code_lines[pattern].addMatch(current_version, filename, lineno, loglevel, trigger)
                log_templates.add(pattern)

                # output_verbose(current_version, filename, lineno, line, statement, matches, True, "OK")

        f.close()


    return log_templates





if __name__ == '__main__':

    versions = get_all_versions()

    if len(sys.argv) > 1:
        versions = [sys.argv[1]]

    log_code_lines = {}
    logs_versions = defaultdict(list)
    print "parsing..."
    for v in versions:
        switch_version(v)
        logs = extract_logs(log_code_lines, v)
        print "version %s, %i lines extracted" %(v[1:], len(logs))
        for l in logs:
            logs_versions[l].append(v)

    switch_version('master')

    # also store hashed by first word for quickly finding the related log lines
    logs_by_word = defaultdict(list)
    for lv in logs_versions:
        first_token = lv[0]
        split_words = first_token.split()
        logs_by_word[split_words[0]].append(lv)

    # now sort by number of tokens
    for lbw in logs_by_word:
        logs_by_word[lbw] = sorted(logs_by_word[lbw], key=lambda x: len(x), reverse=True)

    # for l in sorted(logs_versions):
    #     print " <var> ".join(l), "found in:", ", ".join(logs_versions[l])

    # write out to mongodb
    write_to_db = True
    try:
        mc = MongoClient()
        mc['log2code']['instances'].drop()
    except ConnectionFailure:
        write_to_db = False

    for pattern in log_code_lines:
        lcl = log_code_lines[pattern]

        first_token = pattern[0]
        split_words = first_token.split()

        instance = {
            '_id': lcl.pattern_id,
            'pattern': list(lcl.pattern),
            'first_word': split_words[0],
            'matches': []
        }

        for version in lcl.matches:
            matches = lcl.matches[version]
            for occ in matches:
                instance['matches'].append({
                    'version': version,
                    'file': occ[0],
                    'lineno': occ[1],
                    'loglevel': occ[2],
                    'trigger': occ[3]
                })
        
        if write_to_db:
            mc['log2code']['instances'].update({'pattern': instance['pattern']}, instance, upsert=True)

    cPickle.dump((versions, logs_versions, logs_by_word, log_code_lines), open('log2code.pickle', 'wb'), -1)

    print "%i unique log messages imported and written to log2code.pickle"%len(log_code_lines)



########NEW FILE########
__FILENAME__ = pattern
import re
import json

def _decode_pattern_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_pattern_list(item)
        elif isinstance(item, dict):
            item = _decode_pattern_dict(item)
        rv.append(item)

        rv = sorted(rv)
    return rv

def _decode_pattern_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
            if key in ['$in', '$gt', '$gte', '$lt', '$lte', '$exists']:
                return 1
            if key == '$nin':
                value = 1
            if key in ['query', '$query']:
                return _decode_pattern_dict(value)

        if isinstance(value, list):
            value = _decode_pattern_list(value)
        elif isinstance(value, dict):
            value = _decode_pattern_dict(value)
        else:
            value = 1

        rv[key] = value
    return rv


def json2pattern(s):
    """ converts JSON format (even mongo shell notation without quoted key names) to a query pattern """
    # make valid JSON by wrapping field names in quotes
    s, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:', ' \\1 "\\2" : ' , s)
    # convert values to 1 where possible, to get rid of things like new Date(...)
    s, n = re.subn(r'([:,\[])\s*([^{}\[\]"]+?)\s*([,}\]])', '\\1 1 \\3', s)

    # now convert to dictionary, converting unicode to ascii 
    try:
        doc = json.loads(s, object_hook=_decode_pattern_dict)
        return json.dumps(doc, sort_keys=True, separators=(', ', ': ') )
    except ValueError:
        return None


if __name__ == '__main__':
    
    s = '{d: {$gt: 2, $lt: 4}, b: {$gte: 3}, c: {$nin: [1, "foo", "bar"]}, "$or": [{a:1}, {b:1}] }'
    print json2pattern(s)

    s = '{a: {$gt: 2, $lt: 4}, "b": {$nin: [1, 2, 3]}, "$or": [{a:1}, {b:1}] }'
    print json2pattern(s)

    s = '{ a: 1, b: { c: 2, d: "text" }, e: "more test" }'
    print json2pattern(s)

    s = '{ _id: ObjectId(\'528556616dde23324f233168\'), config: { _id: 2, host: "localhost:27017" }, ns: "local.oplog.rs" }'
    print json2pattern(s)

########NEW FILE########
__FILENAME__ = presplit
from pymongo import Connection
from pymongo.errors import OperationFailure
from bson.son import SON
from bson.min_key import MinKey

import argparse

def presplit(host, database, collection, shardkey, shardnumber=None, chunkspershard=1, verbose=False):
    """ get information about the number of shards, then split chunks and 
        distribute over shards. Currently assumes shardkey to be hex string,
        for example ObjectId or UUID. 

        host: host and port to connect to, e.g. "192.168.0.1:27017", "localhost:30000"
        database: database name to enable sharding
        collection: collection name to shard 
        shardkey: shardkey to pre-split on (must be hex string, e.g. ObjectId or UUID)
        shardnumber: if None, automatically presplit over all available shards. 
            if integer, only presplit over the given number of shards (maximum is 
            the number of actual shards)
    """
    
    con = Connection(host)
    namespace = '%s.%s'%(database, collection)

    # disable balancer
    con['config']['settings'].update({'_id':"balancer"}, {'$set':{'stopped': True}}, upsert=True)

    # enable sharding on database if not yet enabled
    db_info = con['config']['databases'].find_one({'_id':database})
    if not db_info or db_info['partitioned'] == False:
        con['admin'].command(SON({'enableSharding': database}))

    # shard collection if not yet sharded
    coll_info = con['config']['collections'].find_one({'_id':namespace})
    if coll_info and not coll_info['dropped']:
        # if it is sharded already, quit. something is not right.
        if verbose:
            print "collection already sharded."
        return
    else:
        con[database][collection].ensure_index(shardkey)
        con['admin'].command(SON({'shardCollection': namespace, 'key': {shardkey:1}}))

    # get shard number and names and calculate split points
    shards = list(con['config']['shards'].find())

    if len(shards) == 1:
        if verbose:
            print "only one shard found. no pre-splitting required."
        return

    # limit number of shards if shardnumber given
    if shardnumber and shardnumber <= len(shards):
        shards = shards[:shardnumber]

    shard_names = [s['_id'] for s in shards]
    splits_total = len(shards) * chunkspershard
    split_interval = 16**4 / splits_total
    split_points = ["%0.4x"%s for s in range(split_interval, splits_total*split_interval, split_interval)]
    
    # pre-splitting commands
    for s in split_points:
        con['admin'].command(SON([('split',namespace), ('middle', {shardkey: s})]))
    
    split_points = [MinKey()] + split_points

    # move chunks to shards (catch the one error where the chunk resides on that shard already)
    for i,s in enumerate(split_points):
        try:
            if verbose:
                print 'moving chunk %s in collection %s to shard %s.'%(s, namespace, shard_names[i % len(shards)])
            res = con['admin'].command(SON([('moveChunk',namespace), ('find', {shardkey: s}), ('to', shard_names[i % len(shards)])]))
        except OperationFailure, e:
            if verbose:
                print e

    if verbose:
        print 'chunk distribution:',
        chunk_group = con['config']['chunks'].group(key={'shard': 1}, condition={'ns': namespace}, initial={'nChunks':0}, reduce=""" function (doc, out) { out.nChunks++; } """)
        print ', '.join(["%s: %i"%(ch['shard'], ch['nChunks']) for ch in chunk_group])

if __name__ == '__main__':

    # presplitting function
    parser = argparse.ArgumentParser(description='MongoDB pre-splitting tool')

    parser.add_argument('host', action='store', nargs='?', default='localhost:27017', metavar='host:port', help='host:port of mongos or mongod process (default localhost:27017)')
    parser.add_argument('namespace', action='store', help='namespace to shard, in form "database.collection"')
    parser.add_argument('shardkey', action='store', help='shard key to split on, e.g. "_id"')
    parser.add_argument('-n', '--number', action='store', metavar='N', type=int, default=None, help='max. number of shards to use (default is all)')
    parser.add_argument('-c', '--chunks', action='store', metavar='N', type=int, default=1, help='number of chunks per shard (default is 1)')

    parser.add_argument('--verbose', action='store_true', default=False, help='print verbose information')
    args = vars(parser.parse_args())

    args['database'], args['collection'] = args['namespace'].split('.')
    presplit(args['host'], args['database'], args['collection'], args['shardkey'], args['number'], args['chunks'], args['verbose'])


########NEW FILE########
__FILENAME__ = print_table
def print_table( rows, override_headers=None, uppercase_headers=True ):
    """ rows needs to be a list of dictionaries, all with the same keys. """
    
    keys = rows[0].keys()
    headers = override_headers or keys
    if uppercase_headers:
        rows = [ dict(zip(keys, map(lambda x: x.upper(), headers))), None ] + rows
    else:
        rows = [ dict(zip(keys, headers)), None ] + rows

    lengths = [ max( len(str(row[k])) for row in rows if hasattr(row, '__iter__') ) for k in keys ]
    template = (' '*4).join( ['{%s:%i}'%(h,l) for h,l in zip(keys, lengths)] )

    for row in rows:
        if type(row) == str:
            print row
        elif row == None:
            print
        else:
            print template.format(**row)


if __name__ == '__main__':

    d = [ {'a': '123', 'b': '654', 'c':'foo'},
          {'a': '12ooo3', 'b': '654', 'c':'foo'},
          {'a': '123', 'b': '65123124', 'c':'foo'},
          {'a': '123', 'b': '654', 'c':'fsadadsoo'},
          None,
          {'a': '123', 'b': '654', 'c':'foo'} ]

    print_table(d, ['long title here', 'foo', 'bar']) 
    

########NEW FILE########
__FILENAME__ = profile_collection
from mtools.util.logevent import LogEvent
from mtools.util.input_source import InputSource
from dateutil.tz import tzutc

try:
    try:
        from pymongo import MongoClient as Connection
    except ImportError:
        from pymongo import Connection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")

from pymongo import ASCENDING, DESCENDING

class ProfileCollection(InputSource):
    """ wrapper class for input source system.profile collection """

    datetime_format = "ISODate()"

    def __init__(self, host='localhost', port=27017, database='test', collection='system.profile'):
        """ constructor for ProfileCollection. Takes host, port, database and collection as parameters. 
            All are optional and have default values.
        """

        # store parameters
        self.host = host
        self.port = port
        self.database = database
        self.collection = collection
        self.name = "%s.%s" % (database, collection)

        # property variables
        self._start = None
        self._end = None
        self._num_events = None

        self.cursor = None

        # test if database can be reached and collection exists
        try:
            mc = Connection(host=host, port=port)
            self.versions = [ mc.server_info()[u'version'] ]
            binary = 'mongos' if mc.is_mongos else 'mongod'
            self.binary = "%s (running on %s:%i)" % (binary, host, port)

        except (ConnectionFailure, AutoReconnect) as e:
            raise SystemExit("can't connect to database, please check if a mongod instance is running on %s:%s." % (host, port))
        
        self.coll_handle = mc[database][collection]

        if self.coll_handle.count() == 0:
            raise SystemExit("can't find any data in %s.%s collection. Please check database and collection name." % (database, collection))


    @property
    def start(self):
        """ lazy evaluation of start and end of events. """
        if not self._start:
            self._calculate_bounds()
        return self._start


    @property
    def end(self):
        """ lazy evaluation of start and end of events. """
        if not self._end:
            self._calculate_bounds()
        return self._end

    @property
    def num_events(self):
        """ lazy evaluation of the number of events. """
        if not self._num_events:
            self._num_events = self.coll_handle.count()
        return self._num_events


    def next(self):
        """ makes iterators. """
        if not self.cursor:
            self.cursor = self.coll_handle.find().sort([ ("ts", ASCENDING) ])

        doc = self.cursor.next()
        doc['thread'] = self.name
        le = LogEvent(doc)
        return le


    def __iter__(self):
        """ iteration over ProfileCollection object will return a LogEvent object for each document. """

        self.cursor = self.coll_handle.find().sort([ ("ts", ASCENDING) ])

        for doc in self.cursor:
            doc['thread'] = self.name
            le = LogEvent(doc)
            yield le


    def __len__(self):
        """ returns the number of events in the collection. """
        return self.num_events


    def _calculate_bounds(self):
        """ calculate beginning and end of log events. """

        # get start datetime 
        first = self.coll_handle.find_one(None, sort=[ ("ts", ASCENDING) ])
        last = self.coll_handle.find_one(None, sort=[ ("ts", DESCENDING) ])

        self._start = first['ts']
        if self._start.tzinfo == None:
            self._start = self._start.replace(tzinfo=tzutc())

        self._end = last['ts']
        if self._end.tzinfo == None:
            self._end = self._end.replace(tzinfo=tzutc())

        return True


if __name__ == '__main__':
    pc = ProfileCollection()

    for event in pc:
        print event

########NEW FILE########
__FILENAME__ = version
__version__ = '1.1.5'

########NEW FILE########
