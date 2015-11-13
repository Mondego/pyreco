__FILENAME__ = pool
from Queue import Queue
from itertools import chain
import os
from redis import ConnectionError
from redis.connection import Connection
from redis.client import parse_info
from collections import namedtuple
import logging
import socket

logger = logging.getLogger(__name__)

Server = namedtuple('Server', ['host', 'port'])


class Pool(object):

    def __init__(self, connection_class=Connection,
                 max_connections=None, hosts=[],
                 **connection_kwargs):

        self.pid = os.getpid()
        self.connection_class = connection_class
        self.connection_kwargs = connection_kwargs
        self.max_connections = max_connections or 2 ** 31
        self._in_use_connections = set()

        self._hosts = set() # current active known hosts
        self._current_master = None # (host,port)

        self._master_pool = set()
        self._slave_pool = set()
        self._created_connections = 0

        for x in hosts:
            if ":" in x:
                (host, port) = x.split(":")

            else:
                host = x
                port = 6379
            host = socket.gethostbyname(host)
            self._hosts.add(Server(host, int(port)))

        self._configure()

    def _configure(self):
        """
        given the servers we know about, find the current master
        once we have the master, find all the slaves
        """
        logger.debug("Running configure")
        to_check = Queue()
        for x in self._hosts:
            to_check.put(x)

        while not to_check.empty():
            x = to_check.get()

            try:
                conn = self.connection_class(host=x.host, port=x.port, **self.connection_kwargs)
                conn.send_command("INFO")
                info = parse_info(conn.read_response())

                if info['role'] == 'slave':
                    self._slave_pool.add(conn)
                elif info['role'] == 'master':
                    self._current_master = x
                    logger.debug("Current master {}:{}".format(x.host, x.port))
                    self._master_pool.add(conn)
                    slaves = filter(lambda x: x[0:5] == 'slave', info.keys())
                    slaves = [info[y] for y in slaves]
                    slaves = [y.split(',') for y in slaves]
                    slaves = filter(lambda x: x[2] == 'online', slaves)
                    slaves = [Server(x[0], int(x[1])) for x in slaves]

                    for y in slaves:
                        if y not in self._hosts:
                            self._hosts.add(y)
                            to_check.put(y)

                    # add the slaves
            except:
                # remove from list
                to_remove = []
        logger.debug("Configure complete, host list: {}".format(self._hosts))


    def _checkpid(self):
        if self.pid != os.getpid():
            self.disconnect()
            self.__init__(self.connection_class, self.max_connections,
                          **self.connection_kwargs)

    def get_connection(self, command_name, *keys, **options):
        "Get a connection from the pool"
        self._checkpid()
        try:
            connection = self._master_pool.pop()
            logger.debug("Using connection from pool")
        except KeyError:
            logger.debug("Creating new connection")
            connection = self.make_connection()

        self._in_use_connections.add(connection)
        return connection

    def make_connection(self):
        "Create a new connection"
        if self._created_connections >= self.max_connections:
            raise ConnectionError("Too many connections")

        self._created_connections += 1

        if self._current_master == None:
            logger.debug("No master set - reconfiguratin")
            self._configure()

        host = self._current_master[0]
        port = self._current_master[1]

        logger.debug("Creating new connection to {}:{}".format(host, port))
        return self.connection_class(host=host, port=port, **self.connection_kwargs)

    def release(self, connection):

        """
        Releases the connection back to the pool
        if the connection is dead, we disconnect all
        """

        if connection._sock is None:
            logger.debug("Dead socket, reconfigure")
            self.disconnect()
            self._configure()
            self._current_master = None
            server = Server(connection.host, int(connection.port))
            self._hosts.remove(server)
            logger.debug("New configuration: {}".format(self._hosts))

            return

        self._checkpid()
        if connection.pid == self.pid:
            self._in_use_connections.remove(connection)
            self._master_pool.add(connection)

    def disconnect(self):
        "Disconnects all connections in the pool"
        self._master_pool = set()
        self._slave_pool = set()
        self._in_use_connections = set()



########NEW FILE########
__FILENAME__ = base

import unittest
from jondis.tests.manager import Manager


class BaseJondisTest(unittest.TestCase):
    def setUp(self):
        self.manager = Manager()
        self.start()

    def start(self):
        """
        We always need to run the base setup, so we might as well just call start() instead
        of using super() on every single test.  Slightly less obnoxious
        """
        raise NotImplementedError("You must use the start() method to start redis servers.")

    def tearDown(self):
        self.manager.shutdown()

########NEW FILE########
__FILENAME__ = manager

import subprocess
import os

# im picking an arbitarily high port
# starting point, going up from here
from time import sleep
import redis
import logging

logger = logging.getLogger(__name__)

port = 25530
DEVNULL=open(os.devnull, 'wb')

class Manager(object):
    def __init__(self):
        # procs is a dict of tuples (proc, port)
        self.procs = {}

    def start(self, name, master=None):
        """
        :type master int
        """
        global port
        slave_of = "--slaveof 127.0.0.1 {}".format(master) if master else ""

        start_command = "redis-server --port {} {}".format(port, slave_of)

        proc = subprocess.Popen(start_command, shell=True, stdout=DEVNULL, stderr=DEVNULL)

        self.procs[name] = (proc, port)
        port += 1
        # ghetto hack but necessary to find the right slaves
        sleep(.1)
        return self.procs[name][1]

    def stop(self, name):
        (proc, port) = self.procs[name]
        proc.terminate()
        # same hack as above to make sure failure actually happens
        sleep(.1)

    def promote(self, port):
        admin_conn = redis.StrictRedis('localhost', port)
        logger.debug("Promoting {}".format(port))
        admin_conn.slaveof() # makes it the master
        sleep(.1)

    def shutdown(self):
        for (proc,port) in self.procs.itervalues():
            proc.terminate()

    def __getitem__(self, item):
        return self.procs[item]




########NEW FILE########
__FILENAME__ = test_find_slaves

from jondis.tests.base import BaseJondisTest
from jondis.pool import Pool


class BasicFindSlavesTest(BaseJondisTest):
    def start(self):
        self.master = self.manager.start('master')
        self.slave = self.manager.start('slave', self.master)

    def test_update_hosts(self):
        """
        ensures the self.pool is aware of the slaves after updating
        """
        hosts = ['127.0.0.1:{}'.format(self.master),
                 '127.0.0.1:{}'.format(self.slave)]

        pool = Pool(hosts=hosts)

        assert len(pool._slave_pool) == 1
        assert len(pool._master_pool) == 1

class DiscoverSlavesTest(BaseJondisTest):

    def start(self):
        self.master = self.manager.start('master')
        self.slave = self.manager.start('slave', self.master)
        self.slave2 = self.manager.start('slave2', self.master)

    def test_find_slave(self):
        # tests that we auto discover the 2nd slave
        hosts = ['127.0.0.1:{}'.format(self.master),
                 '127.0.0.1:{}'.format(self.slave)]

        pool = Pool(hosts=hosts)

        assert len(pool._hosts) == 3, pool._hosts
        assert len(pool._slave_pool) == 2
        assert len(pool._master_pool) == 1

class SlaveDiscovery2Test(BaseJondisTest):
    def start(self):
        self.master = self.manager.start('master')
        self.slave = self.manager.start('slave', self.master)
        self.slave2 = self.manager.start('slave2', self.master)

        hosts = ['127.0.0.1:{}'.format(self.master)]

        self.pool = Pool(hosts=hosts)

    def test_update_hosts(self):
        """
        ensures the self.pool is aware of the slaves after updating
        """

        assert len(self.pool._hosts) == 3, self.pool._hosts
        assert len(self.pool._slave_pool) == 2
        assert len(self.pool._master_pool) == 1

########NEW FILE########
__FILENAME__ = test_slave_promotion
from time import sleep
import unittest
from jondis.pool import Pool
from jondis.tests.base import BaseJondisTest
import redis
import logging

logger = logging.getLogger(__name__)

class SlavePromotionTest(BaseJondisTest):
    def start(self):
        self.master = self.manager.start('master')
        self.slave = self.manager.start('slave', self.master)

        assert self.master > 0
        assert self.slave > 0


    def test_promotion_on_failure(self):
        pool = Pool(hosts=['127.0.0.1:{}'.format(self.master)])
        r = redis.StrictRedis(connection_pool=pool)

        tmp = r.set('test', 1)
        tmp2 = r.get('test2')

        self.manager.stop('master')

        admin_conn = redis.StrictRedis('localhost', self.slave)

        # promote slave to master
        self.manager.promote(self.slave)
        self.master = self.slave

        with self.assertRaises(redis.ConnectionError):
            r.get('test2')

        tmp2 = r.get('test2')
        self.pool = pool
        self.r = r

    def test_multiple_cascading_failures(self):
        self.test_promotion_on_failure()

        pool = self.pool

        self.slave = self.manager.start('slave2', self.master)
        self.pool._configure()
        
        self.manager.stop('slave')
        self.manager.promote(self.slave)

        logger.debug("Force reconfigure")

        r = self.r
        with self.assertRaises(redis.ConnectionError):
            r.get('test2')

        tmp2 = r.get('test2')

########NEW FILE########
