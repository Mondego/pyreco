__FILENAME__ = http_server
# -*- coding: utf8 -*-

from redis_router.http_interface import start_server

start_server('0.0.0.0', 5000)

########NEW FILE########
__FILENAME__ = tcp_server
# -*- coding: utf8 -*-

from redis_router.tcp_interface import RouterServer

r = RouterServer('0.0.0.0', 5000)
r.run()

"""
$ telnet localhost 5000
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
set selam timu
True
get selam
timu
dbsize
13
"""
########NEW FILE########
__FILENAME__ = http_interface
# -*- coding: utf8 -*-

try:
    from flask import Flask, render_template, jsonify, request
except ImportError:
    raise ImportError('flask library is not installed.')

from router import Router

import os

# initialize flask application
app = Flask(__name__)

config_file = os.getenv('ROUTER_CONFIG_FILE', '/etc/redis_router/servers.config')

# main view
@app.route('/', methods=['POST', ])
def index():
    router = Router(config_file)
    command, arguments = request.form['command'], request.form['arguments']

    arguments = arguments.split(",")
    router_response = getattr(router, command)(*arguments)
    if isinstance(router_response, set):
        router_response = list(router_response)

    return jsonify({"response": router_response})

from gevent.wsgi import WSGIServer


def start_server(host, port):
    http_server = WSGIServer((host, port), app)
    http_server.serve_forever()

########NEW FILE########
__FILENAME__ = router

try:
    import ketama
except ImportError:
    raise ImportError('libketama is not installed.')    

import redis
import re
import logging


class Router(object):

    SERVERS = {}
    METHOD_BLACKLIST = [
        'smove',  # it's hard to shard with atomic approach.
        'move',
    ]

    def __init__(self, ketama_server_file):
        self.server_list = self.parse_server_file(ketama_server_file)
        self.continuum = ketama.Continuum(ketama_server_file)

        for hostname, port in self.server_list:
            server_string = "{0}:{1}".format(hostname, port)

            # creating a emtpy record for lazy connection responses.
            self.SERVERS.update({
                server_string: None,
            })

    def strict_connection(self, hostname, port, timeout=None):

        if not isinstance(port, int):
            try:
                port = int(port)
            except ValueError:
                raise ValueError('port must be int or int convertable.')

        return redis.StrictRedis(host=hostname, port=port, db=0, socket_timeout=timeout)

    def get_connection(self, key):
        key_hash, connection_uri = self.continuum.get_server(key)
        hostname, port = connection_uri.split(":")

        logging.debug("key '{0}' hashed as {1} and mapped to {2}".format(
            key,
            key_hash,
            connection_uri
        ))

        connection = self.SERVERS.get(connection_uri)
        if not connection:
            self.SERVERS.update({
                connection_uri: self.strict_connection(hostname, port),
            })

            connection = self.SERVERS.get(connection_uri)

        return connection

    def __getattr__(self, methodname):

        if methodname in self.METHOD_BLACKLIST:
            raise AttributeError('this method is not allowed with redis_router')

        def method(*args, **kwargs):
            if len(args) < 1:
                raise AttributeError("not enough arguments.")

            connection = self.get_connection(args[0])

            if hasattr(connection, methodname):
                return getattr(connection, methodname)(*args, **kwargs)
            else:
                raise AttributeError("invalid method name:{0}".format(methodname))

        return method

    def __set_generator(self, *args):
        """
        iterable for the custom set methods: ["sinter", "sdiff", "sunion"]
        returns related set's members as python's built-in set.
        """
        for index, key in enumerate(args):
            yield set(self.smembers(key))

    def sinter(self, *args):
        return set.intersection(*self.__set_generator(*args))

    def sinterstore(self, destination, *args):
        intersection = self.sinter(*args)
        if len(intersection) > 0:
            self.sadd(destination, *intersection)

        return len(intersection)

    def sdiff(self, *args):
        return set.difference(*self.__set_generator(*args))

    def sdiffstore(self, destination, *args):
        difference = self.sdiff(*args)
        if len(difference) > 0:
            self.sadd(destination, *difference)

        return len(difference)

    def sunion(self, *args):
        return set.union(*self.__set_generator(*args))

    def sunionstore(self, destination, *args):
        union = self.sunion(*args)
        if len(union) > 0:
            return self.sadd(destination, *union)

        return len(union)

    def ping_all(self, timeout=None):
        """
        pings all shards and returns the results.
        if a shard is down, returns 'DOWN' for the related shard.
        """
        results = list()
        for connection_uri, connection in self.SERVERS.items():
            if not connection:
                try:
                    connection = self.strict_connection(*connection_uri.split(":"), timeout=timeout)
                    results.append({
                        "result": connection.ping(),
                        "connection_uri": connection_uri,
                    })
                except redis.exceptions.ConnectionError:
                    results.append({
                        "result": 'DOWN',
                        "connection_uri": connection_uri,
                    })

        return results

    def dbsize(self):
        """
        returns the number of keys across all the shards.
        """
        result = 0
        for connection_uri, connection in self.SERVERS.items():
            if not connection:
                connection = self.strict_connection(*connection_uri.split(":"))

            result += int(connection.dbsize())

        return result

    def flush_all(self):
        """
        flushes all the keys from all the instances.
        """
        for connection_uri, connection in self.SERVERS.items():
            if not connection:
                connection = self.strict_connection(*connection_uri.split(":"))

            connection.flushall()

    def parse_server_file(self, ketama_server_file):
        file_content = open(ketama_server_file).read()
        result = re.findall('([^:]*):([^\s]*)\s[^\n]*\n', file_content)

        return result



########NEW FILE########
__FILENAME__ = tcp_interface
import logging
import sys
import os


try:
    from gevent.server import StreamServer
except ImportError:
    raise Exception('gevent library is not installed.')

from router import Router


class RouterServer(object):

    CONFIG_FILE = '/etc/redis_router/servers.config'

    def __init__(self, host, port):
        self.server = StreamServer((host, port), self.main)
        self.init_router()

    def main(self, socket, address):
        logging.debug('New connection from %s:%s' % address)
        fileobj = socket.makefile()
        while True:
            client_call = fileobj.readline().replace("\n", "")

            if not client_call:
                logging.debug("client disconnected")
                break

            if client_call.strip() == '\quit':
                logging.debug("client quit")
                sys.exit(0)
            elif len(client_call) > 2:
                splitted_query = client_call.strip().split(" ")
                method, args = splitted_query[0], splitted_query[1:]

                response = getattr(self.r, method)(*args)
                fileobj.write(response)

            fileobj.flush()

    def init_router(self):
        if not os.path.exists(self.CONFIG_FILE):
            raise IOError('config file could not found. {0}'.format(self.CONFIG_FILE))

        self.r = Router(self.CONFIG_FILE)
        return self.r

    def run(self):
        self.server.serve_forever()



########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf8 -*-

import unittest
import os
import ketama

from redis_router.router import Router


class RouterTests(unittest.TestCase):

    def setUp(self):
        # localhost:6379 and localhost:6390 must be accessible redis instances for testing.
        self.valid_list_file = os.tmpnam()
        self.valid_list = file(self.valid_list_file, "w")
        self.valid_list.write("127.0.0.1:6379\t600\n")
        self.valid_list.write("127.0.0.1:6380\t400\n")
        self.valid_list.flush()

        self.invalid_list_file = os.tmpnam()
        self.invalid_list = file(self.invalid_list_file, "w")
        self.invalid_list.write("127.0.0.1:11211 600\n")
        self.invalid_list.write("127.0.0.1:11212 foo\n")
        self.invalid_list.flush()

        self.router = Router(self.valid_list_file)

    def tearDown(self):
        self.valid_list.close()
        os.unlink(self.valid_list_file)

        self.invalid_list.close()
        os.unlink(self.invalid_list_file)

    def test_valid_configuration(self):
        r = Router(self.valid_list_file)
        self.assertEqual(isinstance(r, Router), True)

    def test_invalid_configuration(self):
        self.assertRaises(ketama.KetamaError, Router, self.invalid_list_file)

    def test_continuum(self):
        cont = Router(self.valid_list_file).continuum
        self.assertEqual(type(cont), ketama.Continuum)

    def test_invalid_null(self):
        self.assertRaises(ketama.KetamaError, Router, "/dev/null")

    def test_hashing(self):
        router = Router(self.valid_list_file)
        router.set('forge', 13)
        router.set("spawning_pool", 18)

        key_hash, connection_uri = router.continuum.get_server('forge')
        self.assertEqual(key_hash, 4113771093)
        self.assertEqual(connection_uri, '127.0.0.1:6379')

        key_hash, connection_uri = router.continuum.get_server('spawning_pool')
        self.assertEqual(key_hash, 1434709819)
        self.assertEqual(connection_uri, '127.0.0.1:6380')

    def test_sinter(self):
        self.router.sadd('X', 'a', 'b', 'c')
        self.router.sadd('Y', 'a', 'd', 'e')

        self.assertEqual(self.router.sinter('X', 'Y'), set(['a', ]))

    def test_sinterstore(self):
        self.router.sadd('X1', 'a', 'b', 'c')
        self.router.sadd('Y1', 'a', 'd', 'e')
        self.router.sinterstore('Z1', 'X1', 'Y1')

        self.assertEqual(self.router.smembers('Z1'), set(['a', ]))

    def test_sunion(self):
        self.router.sadd('T1', 'a', 'b', 'c')
        self.router.sadd('M1', 'a', 'd', 'e')

        self.assertEqual(self.router.sunion('T1', 'M1'), set(['a', 'b', 'c', 'd', 'e']))

    def test_sunionstore(self):
        self.router.sadd('T2', 'a', 'b', 'c')
        self.router.sadd('M2', 'a', 'd', 'e')

        self.router.sunionstore('Z2', 'T2', 'M2')

        self.assertEqual(self.router.smembers('Z2'), set(['a', 'b', 'c', 'd', 'e']))

    def test_dbsize(self):
        self.router.flush_all()

        for index in xrange(1, 10):
            self.router.set('data{0}'.format(index), '1')

        self.assertEqual(self.router.dbsize(), 9)

    def test_flush_all(self):
        for index in xrange(1, 10):
            self.router.set('random_data{0}'.format(index), '1')

        self.router.flush_all()

        self.assertEqual(self.router.dbsize(), 0)









########NEW FILE########
