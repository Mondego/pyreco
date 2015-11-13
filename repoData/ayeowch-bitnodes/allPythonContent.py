__FILENAME__ = chart
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# chart.py - Stores chart data from Bitcoin network pinger.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Stores chart data from Bitcoin network pinger.
"""

import glob
import json
import logging
import os
import redis
import sys
import threading
from ConfigParser import ConfigParser

# Redis connection setup
REDIS_SOCKET = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_CONN = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                               password=REDIS_PASSWORD)

SETTINGS = {}


def get_chart_data(tick, nodes, prev_nodes):
    """
    Generates chart data for current tick using enumerated data for all
    reachable nodes.
    """
    data = {
        't': tick,
        'nodes': len(nodes),
        'ipv4': 0,
        'ipv6': 0,
        'user_agents': {},
        'countries': {},
        'coordinates': {},
        'orgs': {},
        'join': 0,
        'leave': 0,
    }
    curr_nodes = set()

    for node in nodes:
        #  0: address
        #  1: port
        #  2: version
        #  3: user_agent
        #  4: timestamp
        #  5: start_height
        #  6: hostname
        #  7: city
        #  8: country
        #  9: latitude
        # 10: longitude
        # 11: timezone
        # 12: asn
        # 13: org
        address = node[0]
        port = node[1]
        user_agent = node[3]
        country = node[8]
        latitude = node[9]
        longitude = node[10]
        org = node[13]

        curr_nodes.add((address, port))

        if ":" in address:
            data['ipv6'] += 1
        else:
            data['ipv4'] += 1

        data['user_agents'][user_agent] = data['user_agents'].get(
            user_agent, 0) + 1

        data['countries'][country] = data['countries'].get(country, 0) + 1

        coordinate = "%s,%s" % (latitude, longitude)
        data['coordinates'][coordinate] = data['coordinates'].get(
            coordinate, 0) + 1

        data['orgs'][org] = data['orgs'].get(org, 0) + 1

    data['join'] = len(curr_nodes - prev_nodes)
    data['leave'] = len(prev_nodes - curr_nodes)

    return data, curr_nodes


def save_chart_data(tick, timestamp, data):
    """
    Saves chart data for current tick in Redis.
    """
    redis_pipe = REDIS_CONN.pipeline()
    redis_pipe.set("t:m:last", json.dumps(data))
    redis_pipe.zadd("t:m:timestamp", tick, "{}:{}".format(tick, timestamp))
    redis_pipe.zadd("t:m:nodes", tick, "{}:{}".format(tick, data['nodes']))
    redis_pipe.zadd("t:m:ipv4", tick, "{}:{}".format(tick, data['ipv4']))
    redis_pipe.zadd("t:m:ipv6", tick, "{}:{}".format(tick, data['ipv6']))

    for user_agent in data['user_agents'].items():
        key = "t:m:user_agent:%s" % user_agent[0]
        redis_pipe.zadd(key, tick, "{}:{}".format(tick, user_agent[1]))

    for country in data['countries'].items():
        key = "t:m:country:%s" % country[0]
        redis_pipe.zadd(key, tick, "{}:{}".format(tick, country[1]))

    for coordinate in data['coordinates'].items():
        key = "t:m:coordinate:%s" % coordinate[0]
        redis_pipe.zadd(key, tick, "{}:{}".format(tick, coordinate[1]))

    for org in data['orgs'].items():
        key = "t:m:org:%s" % org[0]
        redis_pipe.zadd(key, tick, "{}:{}".format(tick, org[1]))

    redis_pipe.zadd("t:m:join", tick, "{}:{}".format(tick, data['join']))
    redis_pipe.zadd("t:m:leave", tick, "{}:{}".format(tick, data['leave']))

    redis_pipe.execute()


def replay_ticks():
    """
    Removes chart data and replays the published timestamps from export.py to
    recreate chart data.
    """
    keys = REDIS_CONN.keys('t:*')
    redis_pipe = REDIS_CONN.pipeline()
    for key in keys:
        redis_pipe.delete(key)
    redis_pipe.execute()

    files = sorted(glob.iglob("{}/*.json".format(SETTINGS['export_dir'])))
    if len(files) > SETTINGS['replay']:
        files = files[len(files) - SETTINGS['replay']:]
    for dump in files:
        timestamp = os.path.basename(dump).rstrip(".json")
        REDIS_CONN.publish('export', timestamp)


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('chart', 'logfile')
    SETTINGS['debug'] = conf.getboolean('chart', 'debug')
    SETTINGS['interval'] = conf.getint('chart', 'interval')
    SETTINGS['export_dir'] = conf.get('chart', 'export_dir')
    SETTINGS['replay'] = conf.getint('chart', 'replay')


def main(argv):
    if len(argv) < 2 or not os.path.exists(argv[1]):
        print("Usage: chart.py [config]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("%(asctime)s,%(msecs)05.1f %(levelname)s (%(funcName)s) "
                 "%(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='w')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    threading.Thread(target=replay_ticks).start()

    prev_nodes = set()

    pubsub = REDIS_CONN.pubsub()
    pubsub.subscribe('export')
    for msg in pubsub.listen():
        # 'export' message is published by export.py after exporting enumerated
        # data for all reachable nodes.
        if msg['channel'] == 'export' and msg['type'] == 'message':
            timestamp = int(msg['data'])  # From ping.py's 'snapshot' message

            # Normalize timestamp to fixed length tick
            floor = timestamp - (timestamp % SETTINGS['interval'])
            tick = floor + SETTINGS['interval']

            # Only the first snapshot before the next interval is used to
            # generate the chart data for each tick.
            if REDIS_CONN.zcount("t:m:nodes", tick, tick) == 0:
                logging.info("Timestamp: {}".format(timestamp))
                logging.info("Tick: {}".format(tick))

                dump = os.path.join(SETTINGS['export_dir'],
                                    "{}.json".format(timestamp))
                nodes = json.loads(open(dump, "r").read(), encoding="latin-1")
                data, prev_nodes = get_chart_data(tick, nodes, prev_nodes)
                save_chart_data(tick, timestamp, data)
                REDIS_CONN.publish('chart', tick)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = crawl
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# crawl.py - Greenlets-based Bitcoin network crawler.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Greenlets-based Bitcoin network crawler.
"""

from gevent import monkey
monkey.patch_all()

import gevent
import json
import logging
import os
import redis
import redis.connection
import socket
import sys
import time
from ConfigParser import ConfigParser

from protocol import ProtocolError, Connection, DEFAULT_PORT

redis.connection.socket = gevent.socket

# Redis connection setup
REDIS_SOCKET = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_CONN = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                               password=REDIS_PASSWORD)

SETTINGS = {}


def enumerate_node(redis_pipe, addr_msgs):
    """
    Adds all peering nodes with max. age of 24 hours into the crawl set.
    """
    peers = 0
    now = time.time()

    for addr_msg in addr_msgs:
        if 'addr_list' in addr_msg:
            for peer in addr_msg['addr_list']:
                age = now - peer['timestamp']  # seconds

                # Add peering node with age <= 24 hours into crawl set
                if age >= 0 and age <= SETTINGS['max_age']:
                    address = peer['ipv4'] if peer['ipv4'] else peer['ipv6']
                    port = peer['port'] if peer['port'] > 0 else DEFAULT_PORT
                    redis_pipe.sadd('pending', (address, port))
                    peers += 1

    return peers


def connect(redis_conn, key):
    """
    Establishes connection with a node to:
    1) Send version message
    2) Receive version and verack message
    3) Send getaddr message
    4) Receive addr message containing list of peering nodes
    Stores node in Redis.
    """
    handshake_msgs = []
    addr_msgs = []

    redis_conn.hset(key, 'state', "")  # Set Redis hash for a new node

    (address, port) = key[5:].split("-", 1)
    start_height = redis_conn.get('start_height')
    if start_height is None:
        start_height = 0
    else:
        start_height = int(start_height)

    connection = Connection((address, int(port)),
                            socket_timeout=SETTINGS['socket_timeout'],
                            user_agent=SETTINGS['user_agent'],
                            start_height=start_height)
    try:
        logging.debug("Connecting to {}".format(connection.to_addr))
        connection.open()
        handshake_msgs = connection.handshake()
        addr_msgs = connection.getaddr()
    except (ProtocolError, socket.error) as err:
        logging.debug("{}: {}".format(connection.to_addr, err))
    finally:
        connection.close()

    gevent.sleep(0.3)
    redis_pipe = redis_conn.pipeline()
    if len(handshake_msgs) > 0:
        start_height_key = "start_height:{}-{}".format(address, port)
        redis_pipe.setex(start_height_key, SETTINGS['max_age'],
                         handshake_msgs[0].get('start_height', 0))
        peers = enumerate_node(redis_pipe, addr_msgs)
        logging.debug("{} Peers: {}".format(connection.to_addr, peers))
        redis_pipe.hset(key, 'state', "up")
    redis_pipe.execute()


def dump(nodes):
    """
    Dumps data for reachable nodes into timestamp-prefixed JSON file and
    returns max. start height from the nodes.
    """
    json_data = []
    max_start_height = REDIS_CONN.get('start_height')
    if max_start_height is None:
        max_start_height = 0
    else:
        max_start_height = int(max_start_height)

    logging.info("Reachable nodes: {}".format(len(nodes)))
    for node in nodes:
        (address, port) = node[5:].split("-", 1)
        try:
            start_height = int(REDIS_CONN.get(
                "start_height:{}-{}".format(address, port)))
        except TypeError as err:
            logging.warning("start_height:{}-{} missing".format(address, port))
            start_height = 0
        json_data.append([address, int(port), start_height])
        max_start_height = max(start_height, max_start_height)

    json_output = os.path.join(SETTINGS['crawl_dir'],
                               "{}.json".format(int(time.time())))
    open(json_output, 'w').write(json.dumps(json_data))
    logging.info("Wrote {}".format(json_output))

    return max_start_height


def restart():
    """
    Dumps data for the reachable nodes into a JSON file.
    Loads all reachable nodes from Redis into the crawl set.
    Removes keys for all nodes from current crawl.
    Updates start height in Redis.
    """
    nodes = []  # Reachable nodes

    keys = REDIS_CONN.keys('node:*')
    logging.debug("Keys: {}".format(len(keys)))

    redis_pipe = REDIS_CONN.pipeline()
    for key in keys:
        state = REDIS_CONN.hget(key, 'state')
        if state == "up":
            nodes.append(key)
            (address, port) = key[5:].split("-", 1)
            redis_pipe.sadd('pending', (address, int(port)))
        redis_pipe.delete(key)

    start_height = dump(nodes)
    redis_pipe.set('start_height', start_height)
    logging.info("Start height: {}".format(start_height))

    redis_pipe.execute()


def cron():
    """
    Assigned to a worker to perform the following tasks periodically to
    maintain a continuous crawl:
    1) Reports the current number of nodes in crawl set
    2) Initiates a new crawl once the crawl set is empty
    """
    start = int(time.time())

    while True:
        pending_nodes = REDIS_CONN.scard('pending')
        logging.info("Pending: {}".format(pending_nodes))

        if pending_nodes == 0:
            REDIS_CONN.set('crawl:master:state', "starting")
            elapsed = int(time.time()) - start
            REDIS_CONN.set('elapsed', elapsed)
            logging.info("Elapsed: {}".format(elapsed))
            logging.info("Restarting")
            restart()
            start = int(time.time())
            REDIS_CONN.set('crawl:master:state', "running")

        gevent.sleep(SETTINGS['cron_delay'])


def task():
    """
    Assigned to a worker to retrieve (pop) a node from the crawl set and
    attempt to establish connection with a new node.
    """
    redis_conn = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                                   password=REDIS_PASSWORD)

    while True:
        if not SETTINGS['master']:
            while REDIS_CONN.get('crawl:master:state') != "running":
                gevent.sleep(SETTINGS['socket_timeout'])

        node = redis_conn.spop('pending')  # Pop random node from set
        if node is None:
            gevent.sleep(1)
            continue

        node = eval(node)  # Convert string from Redis to tuple
        key = "node:{}-{}".format(node[0], node[1])

        # Skip IPv6 node
        if ":" in key and not SETTINGS['ipv6']:
            continue

        if redis_conn.exists(key):
            continue

        connect(redis_conn, key)


def set_pending():
    """
    Initializes pending set in Redis with a list of reachable nodes from DNS
    seeders to bootstrap the crawler.
    """
    for seeder in SETTINGS['seeders']:
        nodes = []
        try:
            nodes = socket.getaddrinfo(seeder, None)
        except socket.gaierror as err:
            logging.warning("{}".format(err))
            continue
        for node in nodes:
            address = node[-1][0]
            REDIS_CONN.sadd('pending', (address, DEFAULT_PORT))


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('crawl', 'logfile')
    SETTINGS['seeders'] = conf.get('crawl', 'seeders').strip().split("\n")
    SETTINGS['workers'] = conf.getint('crawl', 'workers')
    SETTINGS['debug'] = conf.getboolean('crawl', 'debug')
    SETTINGS['user_agent'] = conf.get('crawl', 'user_agent')
    SETTINGS['socket_timeout'] = conf.getint('crawl', 'socket_timeout')
    SETTINGS['cron_delay'] = conf.getint('crawl', 'cron_delay')
    SETTINGS['max_age'] = conf.getint('crawl', 'max_age')
    SETTINGS['ipv6'] = conf.getboolean('crawl', 'ipv6')
    SETTINGS['crawl_dir'] = conf.get('crawl', 'crawl_dir')
    if not os.path.exists(SETTINGS['crawl_dir']):
        os.makedirs(SETTINGS['crawl_dir'])
    SETTINGS['master'] = argv[2] == "master"


def main(argv):
    if len(argv) < 3 or not os.path.exists(argv[1]):
        print("Usage: crawl.py [config] [master|slave]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("[%(process)d] %(asctime)s,%(msecs)05.1f %(levelname)s "
                 "(%(funcName)s) %(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='a')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    if SETTINGS['master']:
        REDIS_CONN.set('crawl:master:state', "starting")
        logging.info("Removing all keys")
        keys = REDIS_CONN.keys('node:*')
        redis_pipe = REDIS_CONN.pipeline()
        for key in keys:
            redis_pipe.delete(key)
        redis_pipe.delete('pending')
        redis_pipe.execute()
        set_pending()

    # Spawn workers (greenlets) including one worker reserved for cron tasks
    workers = []
    if SETTINGS['master']:
        workers.append(gevent.spawn(cron))
    for _ in xrange(SETTINGS['workers'] - len(workers)):
        workers.append(gevent.spawn(task))
    logging.info("Workers: {}".format(len(workers)))
    gevent.joinall(workers)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = export
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# export.py - Exports enumerated data for reachable nodes into a JSON file.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Exports enumerated data for reachable nodes into a JSON file.
"""

import json
import logging
import os
import redis
import sys
import time
from ConfigParser import ConfigParser

# Redis connection setup
REDIS_SOCKET = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_CONN = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                               password=REDIS_PASSWORD)

SETTINGS = {}


def get_row(node):
    """
    Returns enumerated row data from Redis for the specified node.
    """
    # address, port, version, user_agent, timestamp
    node = eval(node)
    address = node[0]
    port = node[1]

    start_height = REDIS_CONN.get('start_height:{}-{}'.format(address, port))
    if start_height is None:
        start_height = (0,)
    else:
        start_height = (int(start_height),)

    hostname = REDIS_CONN.hget('resolve:{}'.format(address), 'hostname')
    hostname = (hostname,)

    geoip = REDIS_CONN.hget('resolve:{}'.format(address), 'geoip')
    if geoip is None:
        # city, country, latitude, longitude, timezone, asn, org
        geoip = (None, None, None, None, None, None, None)
    else:
        geoip = eval(geoip)

    return node + start_height + hostname + geoip


def export_nodes(nodes, timestamp):
    """
    Merges enumerated data for the specified nodes and exports them into
    timestamp-prefixed JSON file.
    """
    rows = []
    start = time.time()
    for node in nodes:
        row = get_row(node)
        rows.append(row)
    end = time.time()
    elapsed = end - start
    logging.info("Elapsed: {}".format(elapsed))

    dump = os.path.join(SETTINGS['export_dir'], "{}.json".format(timestamp))
    open(dump, 'w').write(json.dumps(rows, encoding="latin-1"))
    logging.info("Wrote {}".format(dump))


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('export', 'logfile')
    SETTINGS['debug'] = conf.getboolean('export', 'debug')
    SETTINGS['export_dir'] = conf.get('export', 'export_dir')
    if not os.path.exists(SETTINGS['export_dir']):
        os.makedirs(SETTINGS['export_dir'])


def main(argv):
    if len(argv) < 2 or not os.path.exists(argv[1]):
        print("Usage: export.py [config]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("%(asctime)s,%(msecs)05.1f %(levelname)s (%(funcName)s) "
                 "%(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='w')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    pubsub = REDIS_CONN.pubsub()
    pubsub.subscribe('resolve')
    for msg in pubsub.listen():
        # 'resolve' message is published by resolve.py after resolving hostname
        # and GeoIP data for all reachable nodes.
        if msg['channel'] == 'resolve' and msg['type'] == 'message':
            timestamp = int(msg['data'])  # From ping.py's 'snapshot' message
            logging.info("Timestamp: {}".format(timestamp))
            nodes = REDIS_CONN.smembers('opendata')
            logging.info("Nodes: {}".format(len(nodes)))
            export_nodes(nodes, timestamp)
            REDIS_CONN.publish('export', timestamp)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = pcap
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pcap.py - Saves inv messages from pcap files in Redis.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Saves inv messages from pcap files in Redis.
"""

import dpkt
import glob
import logging
import os
import redis
import socket
import sys
import threading
import time
from ConfigParser import ConfigParser

from protocol import ProtocolError, Serializer

# Redis connection setup
REDIS_SOCKET = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_CONN = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                               password=REDIS_PASSWORD)

SETTINGS = {}


def save_invs(timestamp, node, invs):
    """
    Adds inv messages into the inv set in Redis.
    """
    timestamp = int(timestamp * 1000)  # in ms
    redis_pipe = REDIS_CONN.pipeline()
    for inv in invs:
        logging.debug("[{}] {}:{}".format(timestamp, inv['type'], inv['hash']))
        key = "inv:{}:{}".format(inv['type'], inv['hash'])
        redis_pipe.zadd(key, timestamp, node)
        redis_pipe.expire(key, 18000)  # Expires in 5 hours
    redis_pipe.execute()


def get_invs(filepath):
    """
    Extracts inv messages from the specified pcap file.
    """
    serializer = Serializer()
    pcap_file = open(filepath)
    pcap_reader = dpkt.pcap.Reader(pcap_file)
    for timestamp, buf in pcap_reader:
        frame = dpkt.ethernet.Ethernet(buf)
        ip_packet = frame.data
        if isinstance(ip_packet.data, dpkt.tcp.TCP):
            tcp_packet = ip_packet.data
            payload = tcp_packet.data
            if len(payload) > 0:
                try:
                    (msg, _) = serializer.deserialize_msg(payload)
                except ProtocolError as err:
                    pass
                else:
                    if msg['command'] == "inv":
                        if ip_packet.v == 6:
                            address = socket.inet_ntop(socket.AF_INET6,
                                                       ip_packet.src)
                        else:
                            address = socket.inet_ntop(socket.AF_INET,
                                                       ip_packet.src)
                        node = (address, tcp_packet.sport)
                        save_invs(timestamp, node, msg['inventory'])
    pcap_file.close()


def cron():
    """
    Periodically fetches oldest pcap file to extract inv messages from.
    """
    while True:
        time.sleep(5)

        try:
            oldest = min(glob.iglob("{}/*.pcap".format(SETTINGS['pcap_dir'])))
        except ValueError as err:
            logging.warning(err)
            continue
        latest = max(glob.iglob("{}/*.pcap".format(SETTINGS['pcap_dir'])))
        if oldest == latest:
            continue
        dump = oldest
        logging.info("Dump: {}".format(dump))

        start = time.time()
        get_invs(dump)
        end = time.time()
        elapsed = end - start
        logging.info("Elapsed: {}".format(elapsed))

        os.remove(dump)


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('pcap', 'logfile')
    SETTINGS['debug'] = conf.getboolean('pcap', 'debug')
    SETTINGS['pcap_dir'] = conf.get('pcap', 'pcap_dir')
    if not os.path.exists(SETTINGS['pcap_dir']):
        os.makedirs(SETTINGS['pcap_dir'])


def main(argv):
    if len(argv) < 2 or not os.path.exists(argv[1]):
        print("Usage: pcap.py [config]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("%(asctime)s,%(msecs)05.1f %(levelname)s (%(funcName)s) "
                 "%(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='w')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    threading.Thread(target=cron).start()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = ping
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ping.py - Greenlets-based Bitcoin network pinger.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Greenlets-based Bitcoin network pinger.
"""

from gevent import monkey
monkey.patch_all()

import gevent
import gevent.pool
import glob
import json
import logging
import os
import redis
import redis.connection
import socket
import sys
import time
from ConfigParser import ConfigParser

from protocol import ProtocolError, Connection

redis.connection.socket = gevent.socket

# Redis connection setup
REDIS_SOCKET = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_CONN = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                               password=REDIS_PASSWORD)

SETTINGS = {}


def keepalive(connection, version_msg):
    """
    Periodically sends a ping message to the specified node to maintain open
    connection. Open connections are tracked in open set with the associated
    data stored in opendata set in Redis.
    """
    node = connection.to_addr
    version = version_msg.get('version', "")
    user_agent = version_msg.get('user_agent', "")
    now = int(time.time())
    data = node + (version, user_agent, now)

    REDIS_CONN.sadd('open', node)
    REDIS_CONN.sadd('opendata', data)

    last_ping = now

    while True:
        try:
            ttl = int(REDIS_CONN.get('elapsed'))
        except TypeError as err:
            ttl = 60

        if time.time() > last_ping + ttl:
            try:
                connection.ping()
            except socket.error as err:
                logging.debug("Closing {} ({})".format(node, err))
                break
            last_ping = time.time()

        # Sink received messages to flush them off socket buffer
        try:
            connection.get_messages()
        except socket.timeout as err:
            pass
        except (ProtocolError, socket.error) as err:
            logging.debug("Closing {} ({})".format(node, err))
            break

        gevent.sleep(0.3)

    connection.close()

    REDIS_CONN.srem('open', node)
    REDIS_CONN.srem('opendata', data)


def task():
    """
    Assigned to a worker to retrieve (pop) a node from the reachable set and
    attempt to establish and maintain connection with the node.
    """
    node = REDIS_CONN.spop('reachable')
    if node is None:
        return
    (address, port, start_height) = eval(node)

    handshake_msgs = []
    connection = Connection((address, port),
                            socket_timeout=SETTINGS['socket_timeout'],
                            user_agent=SETTINGS['user_agent'],
                            start_height=start_height)

    try:
        connection.open()
        handshake_msgs = connection.handshake()
    except (ProtocolError, socket.error) as err:
        logging.debug("Closing {} ({})".format(connection.to_addr, err))
        connection.close()

    if len(handshake_msgs) == 0:
        return

    keepalive(connection, handshake_msgs[0])


def cron(pool):
    """
    Assigned to a worker to perform the following tasks periodically to
    maintain a continuous network-wide connections:

    [Master]
    1) Checks for a new snapshot
    2) Loads new reachable nodes into the reachable set in Redis
    3) Signals listener to get reachable nodes from opendata set

    [Master/Slave]
    1) Spawns workers to establish and maintain connection with reachable nodes
    """
    snapshot = None

    while True:
        if SETTINGS['master']:
            new_snapshot = get_snapshot()

            if new_snapshot != snapshot:
                nodes = get_nodes(new_snapshot)
                if len(nodes) == 0:
                    continue

                logging.info("New snapshot: {}".format(new_snapshot))
                snapshot = new_snapshot

                logging.info("Nodes: {}".format(len(nodes)))

                reachable_nodes = set_reachable(nodes)
                logging.info("New reachable nodes: {}".format(reachable_nodes))

                # Allow connections to stabilize before publishing snapshot
                gevent.sleep(SETTINGS['cron_delay'])
                REDIS_CONN.publish('snapshot', int(time.time()))

            connections = REDIS_CONN.scard('open')
            logging.info("Connections: {}".format(connections))

        for _ in xrange(min(REDIS_CONN.scard('reachable'), pool.free_count())):
            pool.spawn(task)

        workers = SETTINGS['workers'] - pool.free_count()
        logging.info("Workers: {}".format(workers))

        gevent.sleep(SETTINGS['cron_delay'])


def get_snapshot():
    """
    Returns latest JSON file (based on creation date) containing a snapshot of
    all reachable nodes from a completed crawl.
    """
    snapshot = None
    try:
        snapshot = max(glob.iglob("{}/*.json".format(SETTINGS['crawl_dir'])))
    except ValueError as err:
        logging.warning(err)
    return snapshot


def get_nodes(path):
    """
    Returns all reachable nodes from a JSON file.
    """
    nodes = []
    text = open(path, 'r').read()
    try:
        nodes = json.loads(text)
    except ValueError as err:
        logging.warning(err)
    return nodes


def set_reachable(nodes):
    """
    Adds reachable nodes that are not already in the open set into the
    reachable set in Redis. New workers can be spawned separately to establish
    and maintain connection with these nodes.
    """
    for node in nodes:
        address = node[0]
        port = node[1]
        start_height = node[2]
        if not REDIS_CONN.sismember('open', (address, port)):
            REDIS_CONN.sadd('reachable', (address, port, start_height))
    return REDIS_CONN.scard('reachable')


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('ping', 'logfile')
    SETTINGS['workers'] = conf.getint('ping', 'workers')
    SETTINGS['debug'] = conf.getboolean('ping', 'debug')
    SETTINGS['user_agent'] = conf.get('ping', 'user_agent')
    SETTINGS['socket_timeout'] = conf.getint('ping', 'socket_timeout')
    SETTINGS['cron_delay'] = conf.getint('ping', 'cron_delay')
    SETTINGS['crawl_dir'] = conf.get('ping', 'crawl_dir')
    if not os.path.exists(SETTINGS['crawl_dir']):
        os.makedirs(SETTINGS['crawl_dir'])
    SETTINGS['master'] = argv[2] == "master"


def main(argv):
    if len(argv) < 3 or not os.path.exists(argv[1]):
        print("Usage: ping.py [config] [master|slave]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("[%(process)d] %(asctime)s,%(msecs)05.1f %(levelname)s "
                 "(%(funcName)s) %(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='a')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    if SETTINGS['master']:
        logging.info("Removing all keys")
        REDIS_CONN.delete('reachable')
        REDIS_CONN.delete('open')
        REDIS_CONN.delete('opendata')

    # Initialize a pool of workers (greenlets)
    pool = gevent.pool.Pool(SETTINGS['workers'])
    pool.spawn(cron, pool)
    pool.join()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# protocol.py - Bitcoin protocol access for bitnodes.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Bitcoin protocol access for bitnodes.
Reference: https://en.bitcoin.it/wiki/Protocol_specification

---------------------------------------------------------------------
               PACKET STRUCTURE FOR BITCOIN PROTOCOL
                     protocol version >= 70001
---------------------------------------------------------------------
[---MESSAGE---]
[ 4] MAGIC_NUMBER   (\xF9\xBE\xB4\xD9)                      uint32_t
[12] COMMAND                                                char[12]
[ 4] LENGTH         <I ( len(payload) )                     uint32_t
[ 4] CHECKSUM       ( sha256(sha256(payload))[:4] )         uint32_t
[..] PAYLOAD        see below

    [---VERSION_PAYLOAD---]
    [ 4] VERSION        <i                                  int32_t
    [ 8] SERVICES       <Q                                  uint64_t
    [ 8] TIMESTAMP      <q                                  int64_t
    [26] ADDR_RECV
        [ 8] SERVICES   <Q                                  uint64_t
        [16] IP_ADDR
            [12] IPV6   (\x00 * 10 + \xFF * 2)              char[12]
            [ 4] IPV4                                       char[4]
        [ 2] PORT       >H                                  uint16_t
    [26] ADDR_FROM
        [ 8] SERVICES   <Q                                  uint64_t
        [16] IP_ADDR
            [12] IPV6   (\x00 * 10 + \xFF * 2)              char[12]
            [ 4] IPV4                                       char[4]
        [ 2] PORT       >H                                  uint16_t
    [ 8] NONCE          <Q ( random.getrandbits(64) )       uint64_t
    [..] USER_AGENT     variable string
    [ 4] START_HEIGHT   <i                                  int32_t
    [ 1] RELAY          <? (since version >= 70001)         bool

    [---ADDR_PAYLOAD---]
    [..] COUNT          variable integer
    [..] ADDR_LIST      multiple of COUNT (max 1000)
        [ 4] TIMESTAMP  <I                                  uint32_t
        [ 8] SERVICES   <Q                                  uint64_t
        [16] IP_ADDR
            [12] IPV6   (\x00 * 10 + \xFF * 2)              char[12]
            [ 4] IPV4                                       char[4]
        [ 2] PORT       >H                                  uint16_t

    [---PING_PAYLOAD---]
    [ 8] NONCE          <Q ( random.getrandbits(64) )       uint64_t

    [---PONG_PAYLOAD---]
    [ 8] NONCE          <Q ( nonce from ping )              uint64_t

    [---INV_PAYLOAD---]
    [..] COUNT          variable integer
    [..] INVENTORY      multiple of COUNT (max 50000)
        [ 4] TYPE       <I (0=error, 1=tx, 2=block)         uint32_t
        [32] HASH                                           char[32]
---------------------------------------------------------------------
"""

import binascii
import gevent
import hashlib
import random
import socket
import struct
import sys
import time
from cStringIO import StringIO
from operator import itemgetter

MAGIC_NUMBER = "\xF9\xBE\xB4\xD9"
PROTOCOL_VERSION = 70001
SERVICES = 1
USER_AGENT = "/getaddr.bitnodes.io:0.1/"
START_HEIGHT = 290000
RELAY = 1  # set to 1 to receive all txs
DEFAULT_PORT = 8333

SOCKET_BUFSIZE = 8192
SOCKET_TIMEOUT = 15
HEADER_LEN = 24


def sha256(data):
    return hashlib.sha256(data).digest()


class ProtocolError(Exception):
    pass


class HeaderTooShortError(ProtocolError):
    pass


class InvalidMagicNumberError(ProtocolError):
    pass


class PayloadTooShortError(ProtocolError):
    pass


class InvalidPayloadChecksum(ProtocolError):
    pass


class IncompatibleClientError(ProtocolError):
    pass


class ReadError(ProtocolError):
    pass


class Serializer(object):
    def __init__(self, **config):
        self.user_agent = config.get('user_agent', USER_AGENT)
        self.start_height = config.get('start_height', START_HEIGHT)
        # This is set prior to throwing PayloadTooShortError exception to
        # allow caller to fetch more data over the network.
        self.required_len = 0

    def serialize_msg(self, **kwargs):
        command = kwargs['command']
        msg = [
            MAGIC_NUMBER,
            command + "\x00" * (12 - len(command)),
        ]

        payload = ""
        if command == "version":
            to_addr = kwargs['to_addr']
            from_addr = kwargs['from_addr']
            payload = self.serialize_version_payload(to_addr, from_addr)
        elif command == "ping" or command == "pong":
            nonce = kwargs['nonce']
            payload = self.serialize_ping_payload(nonce)

        msg.extend([
            struct.pack("<I", len(payload)),
            sha256(sha256(payload))[:4],
            payload,
        ])

        msg = ''.join(msg)
        return msg

    def deserialize_msg(self, data):
        msg = {}

        data_len = len(data)
        if data_len < HEADER_LEN:
            raise HeaderTooShortError("got {} of {} bytes".format(
                data_len, HEADER_LEN))

        data = StringIO(data)
        header = data.read(HEADER_LEN)
        msg.update(self.deserialize_header(header))

        if (data_len - HEADER_LEN) < msg['length']:
            self.required_len = HEADER_LEN + msg['length']
            raise PayloadTooShortError("got {} of {} bytes".format(
                data_len, HEADER_LEN + msg['length']))

        payload = data.read(msg['length'])
        computed_checksum = sha256(sha256(payload))[:4]
        if computed_checksum != msg['checksum']:
            raise InvalidPayloadChecksum("{} != {}".format(
                binascii.hexlify(computed_checksum),
                binascii.hexlify(msg['checksum'])))

        if msg['command'] == "version":
            msg.update(self.deserialize_version_payload(payload))
        elif msg['command'] == "ping":
            msg.update(self.deserialize_ping_payload(payload))
        elif msg['command'] == "addr":
            msg.update(self.deserialize_addr_payload(payload))
        elif msg['command'] == "inv":
            msg.update(self.deserialize_inv_payload(payload))

        return (msg, data.read())

    def deserialize_header(self, data):
        msg = {}
        data = StringIO(data)

        msg['magic_number'] = data.read(4)
        if msg['magic_number'] != MAGIC_NUMBER:
            raise InvalidMagicNumberError("{} != {}".format(
                binascii.hexlify(msg['magic_number']),
                binascii.hexlify(MAGIC_NUMBER)))

        msg['command'] = data.read(12).strip("\x00")
        msg['length'] = struct.unpack("<I", data.read(4))[0]
        msg['checksum'] = data.read(4)

        return msg

    def serialize_version_payload(self, to_addr, from_addr):
        payload = [
            struct.pack("<i", PROTOCOL_VERSION),
            struct.pack("<Q", SERVICES),
            struct.pack("<q", int(time.time())),
            self.serialize_network_address(to_addr),
            self.serialize_network_address(from_addr),
            struct.pack("<Q", random.getrandbits(64)),
            self.serialize_string(self.user_agent),
            struct.pack("<i", self.start_height),
            struct.pack("<?", RELAY),
        ]
        payload = ''.join(payload)
        return payload

    def deserialize_version_payload(self, data):
        msg = {}
        data = StringIO(data)

        msg['version'] = struct.unpack("<i", data.read(4))[0]
        if msg['version'] < PROTOCOL_VERSION:
            raise IncompatibleClientError("{} < {}".format(
                msg['version'], PROTOCOL_VERSION))

        msg['services'] = struct.unpack("<Q", data.read(8))[0]
        msg['timestamp'] = struct.unpack("<q", data.read(8))[0]
        msg['to_addr'] = self.deserialize_network_address(data)
        msg['from_addr'] = self.deserialize_network_address(data)
        msg['nonce'] = struct.unpack("<Q", data.read(8))[0]
        msg['user_agent'] = self.deserialize_string(data)
        msg['start_height'] = struct.unpack("<i", data.read(4))[0]

        try:
            msg['relay'] = struct.unpack("<?", data.read(1))[0]
        except struct.error:
            msg['relay'] = False

        return msg

    def serialize_ping_payload(self, nonce):
        payload = [
            struct.pack("<Q", nonce),
        ]
        payload = ''.join(payload)
        return payload

    def deserialize_ping_payload(self, data):
        data = StringIO(data)
        try:
            nonce = struct.unpack("<Q", data.read(8))[0]
        except struct.error as err:
            raise ReadError(err)
        msg = {
            'nonce': nonce,
        }
        return msg

    def deserialize_addr_payload(self, data):
        msg = {}
        data = StringIO(data)

        msg['count'] = self.deserialize_int(data)
        msg['addr_list'] = []
        for _ in xrange(msg['count']):
            network_address = self.deserialize_network_address(
                data, has_timestamp=True)
            msg['addr_list'].append(network_address)

        return msg

    def deserialize_inv_payload(self, data):
        msg = {
            'timestamp': int(time.time() * 1000),  # milliseconds
        }
        data = StringIO(data)

        msg['count'] = self.deserialize_int(data)
        msg['inventory'] = []
        for _ in xrange(msg['count']):
            inventory = self.deserialize_inventory(data)
            msg['inventory'].append(inventory)

        return msg

    def serialize_network_address(self, addr):
        (ip_address, port) = addr
        network_address = [struct.pack("<Q", SERVICES)]
        if "." in ip_address:
            # unused (12 bytes) + ipv4 (4 bytes) = ipv4-mapped ipv6 address
            unused = "\x00" * 10 + "\xFF" * 2
            network_address.append(
                unused + socket.inet_pton(socket.AF_INET, ip_address))
        else:
            # ipv6 (16 bytes)
            network_address.append(
                socket.inet_pton(socket.AF_INET6, ip_address))
        network_address.append(struct.pack(">H", port))
        network_address = ''.join(network_address)
        return network_address

    def deserialize_network_address(self, data, has_timestamp=False):
        timestamp = None
        if has_timestamp:
            timestamp = struct.unpack("<I", data.read(4))[0]

        try:
            services = struct.unpack("<Q", data.read(8))[0]
        except struct.error as err:
            raise ReadError(err)

        _ipv6 = data.read(12)
        _ipv4 = data.read(4)
        port = struct.unpack(">H", data.read(2))[0]

        ipv6 = socket.inet_ntop(socket.AF_INET6, _ipv6 + _ipv4)
        ipv4 = socket.inet_ntop(socket.AF_INET, _ipv4)

        if ipv4 in ipv6:
            ipv6 = ""  # use ipv4
        else:
            ipv4 = ""  # use ipv6

        return {
            'timestamp': timestamp,
            'services': services,
            'ipv6': ipv6,
            'ipv4': ipv4,
            'port': port,
        }

    def deserialize_inventory(self, data):
        inv_type = struct.unpack("<I", data.read(4))[0]
        inv_hash = data.read(32)[::-1]  # big-endian to little-endian
        return {
            'type': inv_type,
            'hash': binascii.hexlify(inv_hash),
        }

    def serialize_string(self, data):
        length = len(data)
        if length < 0xFD:
            return chr(length) + data
        elif length <= 0xFFFF:
            return chr(0xFD) + struct.pack("<H", length) + data
        elif length <= 0xFFFFFFFF:
            return chr(0xFE) + struct.pack("<I", length) + data
        return chr(0xFF) + struct.pack("<Q", length) + data

    def deserialize_string(self, data):
        length = self.deserialize_int(data)
        return data.read(length)

    def deserialize_int(self, data):
        length = struct.unpack("<B", data.read(1))[0]
        if length == 0xFD:
            length = struct.unpack("<H", data.read(2))[0]
        elif length == 0xFE:
            length = struct.unpack("<I", data.read(4))[0]
        elif length == 0xFF:
            length = struct.unpack("<Q", data.read(8))[0]
        return length


class Connection(object):
    def __init__(self, to_addr, from_addr=("0.0.0.0", 0), **config):
        if to_addr[1] == 0:
            to_addr = (to_addr[0], DEFAULT_PORT)
        self.to_addr = to_addr
        self.from_addr = from_addr
        self.serializer = Serializer(**config)
        self.socket_timeout = config.get('socket_timeout', SOCKET_TIMEOUT)
        self.socket = None

    def open(self):
        self.socket = socket.create_connection(self.to_addr,
                                               self.socket_timeout)

    def close(self):
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            finally:
                self.socket.close()

    def send(self, data):
        self.socket.sendall(data)

    def recv(self, length=0):
        if length > 0:
            chunks = []
            while length > 0:
                chunk = self.socket.recv(SOCKET_BUFSIZE)
                if not chunk:
                    break  # remote host closed connection
                chunks.append(chunk)
                length -= len(chunk)
            data = ''.join(chunks)
        else:
            data = self.socket.recv(SOCKET_BUFSIZE)
        return data

    def get_messages(self, length=0, commands=None):
        msgs = []
        data = self.recv(length=length)
        while len(data) > 0:
            gevent.sleep(0)
            try:
                (msg, data) = self.serializer.deserialize_msg(data)
            except PayloadTooShortError:
                data += self.recv(
                    length=self.serializer.required_len - len(data))
                (msg, data) = self.serializer.deserialize_msg(data)
            if msg.get('command') == "ping":
                self.pong(msg['nonce'])  # respond to ping immediately
            msgs.append(msg)
        if len(msgs) > 0 and commands:
            msgs[:] = [msg for msg in msgs if msg.get('command') in commands]
        return msgs

    def handshake(self):
        # [version] >>>
        msg = self.serializer.serialize_msg(
            command="version", to_addr=self.to_addr, from_addr=self.from_addr)
        self.send(msg)

        # <<< [version 124 bytes] [verack 24 bytes]
        msgs = self.get_messages(length=148, commands=["version", "verack"])
        if len(msgs) > 0:
            msgs[:] = sorted(msgs, key=itemgetter('command'), reverse=True)

        return msgs

    def getaddr(self):
        # [getaddr] >>>
        msg = self.serializer.serialize_msg(command="getaddr")
        self.send(msg)

        # <<< [addr]..
        msgs = self.get_messages(commands=["addr"])

        return msgs

    def ping(self, nonce=None):
        if nonce is None:
            nonce = random.getrandbits(64)

        # [ping] >>>
        msg = self.serializer.serialize_msg(command="ping", nonce=nonce)
        self.send(msg)

    def pong(self, nonce):
        # [pong] >>>
        msg = self.serializer.serialize_msg(command="pong", nonce=nonce)
        self.send(msg)


def main():
    to_addr = ("148.251.238.178", 8333)

    handshake_msgs = []
    addr_msgs = []

    connection = Connection(to_addr)
    try:
        print("open")
        connection.open()

        print("handshake")
        handshake_msgs = connection.handshake()

        print("getaddr")
        addr_msgs = connection.getaddr()

    except (ProtocolError, socket.error) as err:
        print("{}: {}".format(err, to_addr))

    print("close")
    connection.close()

    print(handshake_msgs)

    return 0


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = resolve
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# resolve.py - Resolves hostname and GeoIP data for each reachable node.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Resolves hostname and GeoIP data for each reachable node.
"""

from decimal import Decimal
from gevent import socket
import gevent
import logging
import os
import pygeoip
import random
import redis
import redis.connection
import sys
from ConfigParser import ConfigParser

redis.connection.socket = socket

# Redis connection setup
REDIS_SOCKET = os.environ.get('REDIS_SOCKET', "/tmp/redis.sock")
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_CONN = redis.StrictRedis(unix_socket_path=REDIS_SOCKET,
                               password=REDIS_PASSWORD)

# MaxMind databases
GEOIP4 = pygeoip.GeoIP("geoip/GeoLiteCity.dat", pygeoip.MMAP_CACHE)
GEOIP6 = pygeoip.GeoIP("geoip/GeoLiteCityv6.dat", pygeoip.MMAP_CACHE)
ASN4 = pygeoip.GeoIP("geoip/GeoIPASNum.dat", pygeoip.MMAP_CACHE)
ASN6 = pygeoip.GeoIP("geoip/GeoIPASNumv6.dat", pygeoip.MMAP_CACHE)

# Worker (resolver) status
RESOLVED = 2
FAILED = 1  # Failed socket.gethostbyaddr()

SETTINGS = {}


def resolve_nodes(nodes):
    """
    Spawns workers to resolve hostname and GeoIP data for all nodes.
    """
    addresses_1 = []  # Resolve hostname
    addresses_2 = []  # Resolve GeoIP data

    idx = 0
    for node in nodes:
        node = eval(node)
        address = node[0]
        if not REDIS_CONN.hexists('resolve:{}'.format(address), 'hostname'):
            if idx < 1000:
                addresses_1.append(address)
            idx += 1
        if not REDIS_CONN.hexists('resolve:{}'.format(address), 'geoip'):
            addresses_2.append(address)

    logging.info("Hostname: {} addresses".format(len(addresses_1)))
    workers = [gevent.spawn(set_hostname, address) for address in addresses_1]
    gevent.joinall(workers, timeout=15)

    (resolved, failed, aborted) = status(workers)
    logging.info("Hostname: {} resolved, {} failed, {} aborted".format(
        resolved, failed, aborted))

    logging.info("GeoIP: {} addresses".format(len(addresses_2)))
    workers = [gevent.spawn(set_geoip, address) for address in addresses_2]
    gevent.joinall(workers, timeout=15)

    (resolved, failed, aborted) = status(workers)
    logging.info("GeoIP: {} resolved, {} failed, {} aborted".format(
        resolved, failed, aborted))


def status(workers):
    """
    Summarizes resolve status for the spawned workers after a set timeout.
    """
    resolved = 0
    failed = 0
    aborted = 0  # Timed out

    for worker in workers:
        if worker.value == RESOLVED:
            resolved += 1
        elif worker.value == FAILED:
            failed += 1
        else:
            aborted += 1

    return (resolved, failed, aborted)


def set_data(address, field, value):
    """
    Stores data for an address in Redis with a randomize TTL randomize to
    distribute expiring keys across multiple times.
    """
    ttl = random.randint(SETTINGS['min_ttl'], SETTINGS['max_ttl'])
    redis_pipe = REDIS_CONN.pipeline()
    redis_pipe.hset('resolve:{}'.format(address), field, value)
    redis_pipe.expire('resolve:{}'.format(address), ttl)
    redis_pipe.execute()


def set_hostname(address):
    """
    Caches hostname for the specified address in Redis.
    """
    hostname = raw_hostname(address)
    set_data(address, 'hostname', hostname)
    if hostname != address:
        return RESOLVED
    return FAILED


def raw_hostname(address):
    """
    Resolves hostname for the specified address using reverse DNS resolution.
    """
    hostname = address
    try:
        hostname = socket.gethostbyaddr(address)[0]
    except (socket.gaierror, socket.herror) as err:
        logging.debug("{}: {}".format(address, err))
    return hostname


def set_geoip(address):
    """
    Caches GeoIP data for the specified address in Redis.
    """
    geoip = raw_geoip(address)
    set_data(address, 'geoip', geoip)
    return RESOLVED


def raw_geoip(address):
    """
    Resolves GeoIP data for the specified address using MaxMind databases.
    """
    city = None
    country = None
    latitude = None
    longitude = None
    timezone = None
    asn = None
    org = None

    geoip_record = None
    prec = Decimal('.000001')
    if ":" in address:
        geoip_record = GEOIP6.record_by_addr(address)
    else:
        geoip_record = GEOIP4.record_by_addr(address)
    if geoip_record:
        city = geoip_record['city']
        country = geoip_record['country_code']
        latitude = float(Decimal(geoip_record['latitude']).quantize(prec))
        longitude = float(Decimal(geoip_record['longitude']).quantize(prec))
        timezone = geoip_record['time_zone']

    asn_record = None
    if ":" in address:
        asn_record = ASN6.org_by_addr(address)
    else:
        asn_record = ASN4.org_by_addr(address)
    if asn_record:
        data = asn_record.split(" ", 1)
        asn = data[0]
        if len(data) > 1:
            org = data[1]

    return (city, country, latitude, longitude, timezone, asn, org)


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('resolve', 'logfile')
    SETTINGS['debug'] = conf.getboolean('resolve', 'debug')
    SETTINGS['min_ttl'] = conf.getint('resolve', 'min_ttl')
    SETTINGS['max_ttl'] = conf.getint('resolve', 'max_ttl')


def main(argv):
    if len(argv) < 2 or not os.path.exists(argv[1]):
        print("Usage: resolve.py [config]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("%(asctime)s,%(msecs)05.1f %(levelname)s (%(funcName)s) "
                 "%(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='w')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    pubsub = REDIS_CONN.pubsub()
    pubsub.subscribe('snapshot')
    for msg in pubsub.listen():
        # 'snapshot' message is published by ping.py after establishing
        # connection with nodes from a new snapshot.
        if msg['channel'] == 'snapshot' and msg['type'] == 'message':
            timestamp = int(msg['data'])
            logging.info("Timestamp: {}".format(timestamp))
            nodes = REDIS_CONN.smembers('opendata')
            logging.info("Nodes: {}".format(len(nodes)))
            resolve_nodes(nodes)
            REDIS_CONN.publish('resolve', timestamp)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = seeder
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# seeder.py - Exports reachable nodes into a DNS zone file for DNS seeder.
#
# Copyright (c) 2014 Addy Yeow Chin Heng <ayeowch@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Exports reachable nodes into a DNS zone file for DNS seeder.
"""

import glob
import json
import logging
import operator
import os
import random
import sys
import threading
import time
from ConfigParser import ConfigParser

from protocol import DEFAULT_PORT

SETTINGS = {}


def export_nodes(nodes):
    """
    Exports nodes as A and AAAA records into DNS zone file. Nodes are selected
    from oldest (longest uptime) to newest each with unique AS number.
    """
    nodes = sorted(nodes, key=operator.itemgetter(4))[:SETTINGS['nodes']]
    heights = sorted(set([node[5] for node in nodes]))  # Unique heights
    height = heights[int(0.999 * len(heights))]  # 99.9th percentile height
    min_height = max(SETTINGS['min_height'], height)
    min_age = SETTINGS['min_age']
    now = int(time.time())
    logging.info("Min. height: {}".format(min_height))
    oldest = now - min(nodes, key=operator.itemgetter(4))[4]
    if oldest < min_age:
        min_age = oldest - (0.01 * oldest)  # Max. 1% newer than oldest
    logging.info("Min. age: {}".format(min_age))
    asns = []
    a_records = []
    aaaa_records = []
    for node in nodes:
        address = node[0]
        port = node[1]
        age = now - node[4]
        height = node[5]
        asn = node[12]
        if (port == DEFAULT_PORT and asn not in asns and
                age >= min_age and height >= min_height):
            if ":" in address:
                aaaa_records.append("@\tIN\tAAAA\t{}".format(address))
            else:
                a_records.append("@\tIN\tA\t{}".format(address))
            asns.append(asn)
    random.shuffle(a_records)
    random.shuffle(aaaa_records)
    logging.info("A records: {}".format(len(a_records)))
    logging.info("AAAA records: {}".format(len(aaaa_records)))
    a_records = "\n".join(a_records[:SETTINGS['a_records']]) + "\n"
    aaaa_records = "\n".join(aaaa_records[:SETTINGS['aaaa_records']]) + "\n"
    template = open(SETTINGS['template'], "r").read()
    open(SETTINGS['zone_file'], "w").write(
        template + a_records + aaaa_records)


def cron():
    """
    Periodically fetches latest snapshot to sample nodes for DNS zone file.
    """
    while True:
        time.sleep(5)
        dump = max(glob.iglob("{}/*.json".format(SETTINGS['export_dir'])))
        logging.info("Dump: {}".format(dump))
        nodes = []
        try:
            nodes = json.loads(open(dump, "r").read(), encoding="latin-1")
        except ValueError:
            logging.warning("Write pending")
        if len(nodes) > 0:
            export_nodes(nodes)


def init_settings(argv):
    """
    Populates SETTINGS with key-value pairs from configuration file.
    """
    conf = ConfigParser()
    conf.read(argv[1])
    SETTINGS['logfile'] = conf.get('seeder', 'logfile')
    SETTINGS['debug'] = conf.getboolean('seeder', 'debug')
    SETTINGS['export_dir'] = conf.get('seeder', 'export_dir')
    SETTINGS['nodes'] = conf.getint('seeder', 'nodes')
    SETTINGS['min_height'] = conf.getint('seeder', 'min_height')
    SETTINGS['min_age'] = conf.getint('seeder', 'min_age')
    SETTINGS['zone_file'] = conf.get('seeder', 'zone_file')
    SETTINGS['template'] = conf.get('seeder', 'template')
    SETTINGS['a_records'] = conf.getint('seeder', 'a_records')
    SETTINGS['aaaa_records'] = conf.getint('seeder', 'aaaa_records')


def main(argv):
    if len(argv) < 2 or not os.path.exists(argv[1]):
        print("Usage: seeder.py [config]")
        return 1

    # Initialize global settings
    init_settings(argv)

    # Initialize logger
    loglevel = logging.INFO
    if SETTINGS['debug']:
        loglevel = logging.DEBUG

    logformat = ("%(asctime)s,%(msecs)05.1f %(levelname)s (%(funcName)s) "
                 "%(message)s")
    logging.basicConfig(level=loglevel,
                        format=logformat,
                        filename=SETTINGS['logfile'],
                        filemode='w')
    print("Writing output to {}, press CTRL+C to terminate..".format(
          SETTINGS['logfile']))

    threading.Thread(target=cron).start()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
