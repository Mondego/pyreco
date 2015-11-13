__FILENAME__ = gen_redis_proto
#!/usr/bin/env python -tt
# -*- coding: UTF-8 -*-
"""
Generating Redis Protocol

Generate the Redis protocol, in raw format, in order to use 'redis-cli --pipe' command to massively insert/delete.... keys in a redis server
It accepts as input a pipe with redis commands formatted as "SET key value" or "DEL key"...

Usage:

      echo "SET mykey1 value1\nSET mykey2 value2" > data.txt
      cat data.txt | python gen_redis_proto.py | redis-cli --pipe

"""

__author__ = "Salimane Adjao Moustapha (me@salimane.com)"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 2013/04/30 12:57:19 $"
__copyleft__ = "Copyleft (c) 2013 Salimane Adjao Moustapha"
__license__ = "MIT"

import sys
import fileinput
from itertools import imap


def encode(value):
    "Return a bytestring representation of the value"
    if isinstance(value, bytes):
        return value
    if not isinstance(value, unicode):
        value = str(value)
    if isinstance(value, unicode):
        value = value.encode('utf-8', 'strict')
    return value


def gen_redis_proto(*cmd):
    proto = ""
    proto += "*" + str(len(cmd)) + "\r\n"
    for arg in imap(encode, cmd):
        proto += "$" + str(len(arg)) + "\r\n"
        proto += arg + "\r\n"
    return proto


if __name__ == '__main__':
    for line in fileinput.input():
        sys.stdout.write(gen_redis_proto(*line.rstrip().split(' ')))

########NEW FILE########
__FILENAME__ = redis-copy
#!/usr/bin/env python -tt
# -*- coding: UTF-8 -*-
"""
Redis Copy

Redis Copy the keys in a source redis server into another target redis server.
The script probably needs to be added to a cron job if the keys are a lot because it only copies a fix number of keys at a time
and continue from there on the next run. It does this until there is no more keys to copy

Usage: python redis-copy.py [options]

Options:
  -l ..., --limit=...         optional numbers of keys to copy per run, if not defined 10000 is the default . e.g. 1000
  -s ..., --source=...        source redis server "ip:port" to copy keys from. e.g. 192.168.0.99:6379
  -t ..., --target=...        target redis server "ip:port" to copy keys to. e.g. 192.168.0.101:6379
  -d ..., --databases=...     comma separated list of redis databases to select when copying. e.g. 2,5
  -h, --help                  show this help
  --clean                     clean all variables, temp lists created previously by the script

Dependencies: redis (redis-py: sudo pip install redis)

Examples:
  python redis-copy.py --help                                show this doc

  python redis-copy.py \
  --source=192.168.0.99:6379 \
  --target=192.168.0.101:6379 \
  --databases=2,5 --clean                                 clean all variables, temp lists created previously by the script

  python redis-copy.py \
  --source=192.168.0.99:6379 \
  --target=192.168.0.101:6379 \
  --databases=2,5                                         copy all keys in db 2 and 5 from server 192.168.0.99:6379 to server 192.168.0.101:6379
                                                          with the default limit of 10000 per script run

  python redis-copy.py --limit=1000 \
  --source=192.168.0.99:6379 \
  --target=192.168.0.101:6379 \
  --databases=2,5                                         copy all keys in db 2 and 5 from server 192.168.0.99:6379 to server 192.168.0.101:6379
                                                          with a limit of 1000 per script run

"""

__author__ = "Salimane Adjao Moustapha (salimane@gmail.com)"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 2011/06/09 12:57:19 $"
__copyleft__ = "Copyleft (c) 2011 Salimane Adjao Moustapha"
__license__ = "MIT"


import redis
import time
import sys
import getopt


class RedisCopy:
    """A class for copying keys from one server to another.
    """

    #some key prefix for this script
    mprefix = 'mig:'
    keylistprefix = 'keylist:'
    hkeylistprefix = 'havekeylist:'

    # numbers of keys to copy on each iteration
    limit = 10000

    def __init__(self, source, target, dbs):
        self.source = source
        self.target = target
        self.dbs = dbs

    def save_keylists(self):
        """Function to save the keys' names of the source redis server into a list for later usage.
        """

        for db in self.dbs:
            servername = self.source['host'] + ":" + str(
                self.source['port']) + ":" + str(db)
            #get redis handle for server-db
            r = redis.StrictRedis(
                host=self.source['host'], port=self.source['port'], db=db)
            dbsize = r.dbsize()
            #check whether we already have the list, if not get it
            hkl = r.get(self.mprefix + self.hkeylistprefix + servername)
            if hkl is None or int(hkl) != 1:
                print "Saving the keys in %s to temp keylist...\n" % servername
                moved = 0
                r.delete(self.mprefix + self.keylistprefix + servername)
                for key in r.keys('*'):
                    moved += 1
                    r.rpush(
                        self.mprefix + self.keylistprefix + servername, key)
                    if moved % self.limit == 0:
                        print  "%d keys of %s inserted in temp keylist at %s...\n" % (moved, servername, time.strftime("%Y-%m-%d %I:%M:%S"))

                r.set(self.mprefix + self.hkeylistprefix + servername, 1)
            print "ALL %d keys of %s already inserted to temp keylist ...\n\n" % (dbsize - 1, servername)

    def copy_db(self, limit=None):
        """Function to copy all the keys from the source into the new target.
        - limit : optional numbers of keys to copy per run
        """

        #set the limit per run
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = None

        if limit is not None:
            self.limit = limit

        for db in self.dbs:
            servername = self.source['host'] + ":" + str(
                self.source['port']) + ":" + str(db)
            print "Processing keys copying of server %s at %s...\n" % (
                servername, time.strftime("%Y-%m-%d %I:%M:%S"))
            #get redis handle for current source server-db
            r = redis.StrictRedis(
                host=self.source['host'], port=self.source['port'], db=db)
            moved = 0
            dbsize = r.dbsize() - 1
            #get keys already moved
            keymoved = r.get(self.mprefix + "keymoved:" + servername)
            keymoved = 0 if keymoved is None else int(keymoved)
            #check if we already have all keys copied for current source server-db
            if dbsize < keymoved:
                print "ALL %d keys from %s have already been copied.\n" % (
                    dbsize, servername)
                continue

            print "Started copy of %s keys from %d to %d at %s...\n" % (servername, keymoved, dbsize, time.strftime("%Y-%m-%d %I:%M:%S"))

            #get redis handle for corresponding target server-db
            rr = redis.StrictRedis(
                host=self.target['host'], port=self.target['port'], db=db)

            #max index for lrange
            newkeymoved = keymoved + \
                self.limit if dbsize > keymoved + self.limit else dbsize

            for key in r.lrange(self.mprefix + self.keylistprefix + servername, keymoved, newkeymoved):
                #get key type
                ktype = r.type(key)
                #if undefined type go to next key
                if ktype == 'none':
                    continue

                #save key to target server-db
                if ktype == 'string':
                    rr.set(key, r.get(key))
                elif ktype == 'hash':
                    rr.hmset(key, r.hgetall(key))
                elif ktype == 'list':
                    if key == self.mprefix + "keylist:" + servername:
                        continue
                    #value = r.lrange(key, 0, -1)
                    #rr.rpush(key, *value)
                    for k in r.lrange(key, 0, -1):
                        rr.rpush(key, k)
                elif ktype == 'set':
                    #value = r.smembers(key)
                    #rr.sadd(key, *value)
                    for k in r.smembers(key):
                        rr.sadd(key, k)
                elif ktype == 'zset':
                    #value = r.zrange(key, 0, -1, withscores=True)
                    #rr.zadd(key, **dict(value))
                    for k, v in r.zrange(key, 0, -1, withscores=True):
                        rr.zadd(key, v, k)

                # Handle keys with an expire time set
                kttl = r.ttl(key)
                kttl = -1 if kttl is None else int(kttl)
                if kttl != -1:
                    rr.expire(key, kttl)

                moved += 1

                if moved % 10000 == 0:
                    print "%d keys have been copied on %s at %s...\n" % (
                        moved, servername, time.strftime("%Y-%m-%d %I:%M:%S"))

            r.set(self.mprefix + "keymoved:" + servername, newkeymoved)
            print "%d keys have been copied on %s at %s\n" % (
                newkeymoved, servername, time.strftime("%Y-%m-%d %I:%M:%S"))

    def flush_target(self):
        """Function to flush the target server.
        """
        for db in self.dbs:
            servername = self.target['host'] + ":" + str(
                self.target['port']) + ":" + str(db)
            print "Flushing server %s at %s...\n" % (
                servername, time.strftime("%Y-%m-%d %I:%M:%S"))
            r = redis.StrictRedis(
                host=self.target['host'], port=self.target['port'], db=db)
            r.flushdb()
            print "Flushed server %s at %s...\n" % (
                servername, time.strftime("%Y-%m-%d %I:%M:%S"))

    def clean(self):
        """Function to clean all variables, temp lists created previously by the script.
        """

        print "Cleaning all temp variables...\n"
        for db in self.dbs:
            servername = self.source['host'] + ":" + str(
                self.source['port']) + ":" + str(db)
            r = redis.StrictRedis(
                host=self.source['host'], port=self.source['port'], db=db)
            r.delete(self.mprefix + "keymoved:" + servername)
            r.delete(self.mprefix + self.keylistprefix + servername)
            r.delete(self.mprefix + self.hkeylistprefix + servername)
            r.delete(self.mprefix + "firstrun")
            r.delete(self.mprefix + 'run')
        print "Done.\n"


def main(source, target, databases, limit=None, clean=False):
    #getting source and target
    if (source == target):
        exit('The 2 servers adresses are the same. e.g. python redis-copy.py 127.0.0.1:6379 127.0.0.1:63791  0,1')
    so = source.split(':')
    if len(so) == 2:
        source_server = {'host': so[0], 'port': int(so[1])}
    else:
        exit('Supplied source address is wrong. e.g. python redis-copy.py 127.0.0.1:6379 127.0.0.1:63791  0,1')

    sn = target.split(':')
    if len(sn) == 2:
        target_server = {'host': sn[0], 'port': int(sn[1])}
    else:
        exit('Supplied target address is wrong. e.g. python redis-copy.py 127.0.0.1:6379 127.0.0.1:63791  0,1')

    #getting the dbs
    dbs = [int(k) for k in databases.split(',')]
    if len(dbs) < 1:
        exit('Supplied list of db is wrong. e.g. python redis-copy.py 127.0.0.1:6379 127.0.0.1:63791  0,1')

    try:
        r = redis.StrictRedis(
            host=source_server['host'], port=source_server['port'], db=dbs[0])
    except AttributeError as e:
        exit('Please this script requires redis-py >= 2.4.10, your current version is :' + redis.__version__)

    mig = RedisCopy(source_server, target_server, dbs)

    if clean == False:
        #check if script already running
        run = r.get(mig.mprefix + "run")
        if run is not None and int(run) == 1:
            exit('another process already running the script')
        r.set(mig.mprefix + 'run', 1)

        mig.save_keylists()

        firstrun = r.get(mig.mprefix + "firstrun")
        firstrun = 0 if firstrun is None else int(firstrun)
        if firstrun == 0:
            mig.flush_target()
            r.set(mig.mprefix + "firstrun", 1)

        mig.copy_db(limit)
    else:
        mig.clean()

    r.set(mig.mprefix + 'run', 0)


def usage():
    print __doc__


if __name__ == "__main__":
    clean = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hl:s:t:d:", ["help", "limit=", "source=", "target=", "databases=", "clean"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt == "--clean":
            clean = True
        elif opt in ("-l", "--limit"):
            limit = arg
        elif opt in ("-s", "--source"):
            source = arg
        elif opt in ("-t", "--target"):
            target = arg
        elif opt in ("-d", "--databases"):
            databases = arg

    try:
        limit = int(limit)
    except (NameError, TypeError, ValueError):
        limit = None

    try:
        main(source, target, databases, limit, clean)
    except NameError as e:
        usage()

########NEW FILE########
__FILENAME__ = redis-mem-stats
#! /usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Redis Memory Stats

A memory size analyzer that parses the output of the memory report of rdb <https://github.com/sripathikrishnan/redis-rdb-tools>
 for memory size stats about key patterns

At its core, RedisMemStats uses the output of the memory report of rdb, which echoes a csv row line for every key
stored to a Redis instance.
It parses these lines, and aggregates stats on the most memory consuming keys, prefixes, dbs and redis data structures.

Usage: rdb -c memory <REDIS dump.rdb TO ANALYZE> | ./redis-mem-stats.py [options]

      OR

      rdb -c memory <REDIS dump.rdb TO ANALYZE> > <OUTPUT CSV FILE>
      ./redis-mem-stats.py [options] <OUTPUT CSV FILE>

      options:
      --prefix-delimiter=...           String to split on for delimiting prefix and rest of key, if not provided `:` is the default . --prefix-delimiter=#

Examples:
  rdb -c memory /var/lib/redis/dump.rdb > /tmp/outfile.csv
  ./redis-mem-stats.py /tmp/outfile.csv

  or

  rdb -c memory /var/lib/redis/dump.rdb | ./redis-mem-stats.py


Dependencies: rdb (redis-rdb-tools: https://github.com/sripathikrishnan/redis-rdb-tools)

"""

__author__ = "Salimane Adjao Moustapha (me@salimane.com)"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 2012/09/24 12:57:19 $"
__copyleft__ = "Copyleft (c) 2012-2013 Salimane Adjao Moustapha"
__license__ = "MIT"

import argparse
import sys
from collections import defaultdict
from itertools import imap


class RedisMemStats(object):
    """
    Analyze the output of the memory report of rdb
    """

    def __init__(self, prefix_delim=':'):
        self.line_count = 0
        self.skipped_lines = 0
        self.total_size = 0
        self.dbs = defaultdict(int)
        self.types = defaultdict(int)
        self.keys = defaultdict(int)
        self.prefixes = defaultdict(int)
        self.sizes = []
        self._cached_sorts = {}
        self.prefix_delim = prefix_delim

    def _record_size(self, entry):
        size = int(entry['size'])
        self.total_size += size
        self.dbs[entry['db']] += size
        self.types[entry['type']] += size
        self.keys[entry['key']] += size
        pos = entry['key'].rfind(self.prefix_delim)
        if pos is not -1:
            self.prefixes[entry['key'][0:pos]] += size
        # self.sizes.append((entry['size'], entry))

    def _record_columns(self, sizes):
        for size, entry in sizes:
            mem = int(size)
            self.dbs[entry['db']] += mem
            self.types[entry['type']] += mem
            self.keys[entry['key']] += mem
            pos = entry['key'].rfind(self.prefix_delim)
            if pos is not -1:
                self.prefixes[entry['key'][0:pos]] += mem

    def _get_or_sort_list(self, ls):
        key = id(ls)
        if not key in self._cached_sorts:
            sorted_items = sorted(ls)
            self._cached_sorts[key] = sorted_items
        return self._cached_sorts[key]

    def _general_stats(self):
        return (
            ("Lines Processed", self.line_count),
        )

    def process_entry(self, entry):
        self._record_size(entry)

    def _top_n(self, stat, n=30):
        sorted_items = sorted(
            stat.iteritems(), key=lambda x: x[1], reverse=True)
        return sorted_items[:n]

    def humanize_bytes(self, size):
        for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return "%3.1f%s" % (size, x)
            size /= 1024.0

    def _pretty_print(self, result, title, percentages=False):
        print title
        print '=' * 40
        if not result:
            print 'n/a\n'
            return

        max_key_len = max((len(x[0]) for x in result))
        max_val_len = max((len(str(x[1])) for x in result))
        for key, val in result:
            val_h = self.humanize_bytes(val)
            key_padding = max(max_key_len - len(key), 0) * ' '
            if percentages:
                val_padding = max(max_val_len - len(val_h), 0) * ' '
                val = '%s%s\t(%.2f%%)' % (
                    val_h, val_padding, (float(val) / self.total_size) * 100)
            print key, key_padding, '\t', val
        print

    def print_stats(self):
        self._pretty_print(self._general_stats(), 'Overall Stats')
        # self._record_columns(self.sizes)
        self._pretty_print(
            self._top_n(self.prefixes), 'Heaviest Prefixes', percentages=True)
        self._pretty_print(
            self._top_n(self.keys), 'Heaviest Keys', percentages=True)
        self._pretty_print(
            self._top_n(self.dbs), 'Heaviest Dbs', percentages=True)
        self._pretty_print(
            self._top_n(self.types), 'Heaviest Types', percentages=True)

    def process_input(self, input):
        for line in input:
            self.line_count += 1
            line = line.strip()
            parts = line.split(",")
            if len(parts) > 1:
                try:
                    size = int(parts[3])
                except ValueError as e:
                    self.skipped_lines += 1
                    continue
                self.process_entry({'db': parts[0], 'type': parts[1], 'key': parts[2].replace('"', ''), 'size': parts[3]})
            else:
                self.skipped_lines += 1
                continue

    def gen_redis_proto(self, *cmd):
        proto = ""
        proto += "*" + str(len(cmd)) + "\r\n"
        for arg in imap(self.encode, cmd):
            proto += "$" + str(len(arg)) + "\r\n"
            proto += arg + "\r\n"
        return proto

    def encode(self, value):
        "Return a bytestring representation of the value"
        if isinstance(value, bytes):
            return value
        if not isinstance(value, unicode):
            value = str(value)
        if isinstance(value, unicode):
            value = value.encode('utf-8', 'strict')
        return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'input',
        type=argparse.FileType('r'),
        default=sys.stdin,
        nargs='?',
        help="File to parse; will read from stdin otherwise")
    parser.add_argument(
        '--prefix-delimiter',
        type=str,
        default=':',
        help="String to split on for delimiting prefix and rest of key",
        required=False)
    args = parser.parse_args()
    counter = RedisMemStats(prefix_delim=args.prefix_delimiter)
    counter.process_input(args.input)
    counter.print_stats()

########NEW FILE########
__FILENAME__ = redis-sharding
#!/usr/bin/env python -tt
# -*- coding: UTF-8 -*-
"""
Redis sharding

Reshard the keys in a number of source redis servers into another number of target cluster of redis servers
in order to scale an application.
The script probably needs to be added to a cron job if the keys are a lot because it only reshards a fix number of keys at a time
and continue from there on the next run. It does this until there is no more keys to reshard

Usage: python redis-sharding.py [options]

Options:
  -l ..., --limit=...         optional numbers of keys to reshard per run, if not defined 10000 is the default . e.g. 1000
  -s ..., --sources=...       comma separated list of source redis servers "ip:port" to fetch keys from. e.g. 192.168.0.99:6379,192.168.0.100:6379
  -t ..., --targets=...       comma separated list target redis servers "node_i#ip:port" to reshard the keys to. e.g. node_1#192.168.0.101:6379,node_2#192.168.0.102:6379,node_3#192.168.0.103:6379
  -d ..., --databases=...     comma separated list of redis databases to select when resharding. e.g. 2,5
  -h, --help                  show this help
  --clean                     clean all variables, temp lists created previously by the script

Dependencies: redis (redis-py: sudo pip install redis)

IMPORTANT: This script assume your target redis cluster of servers is based on a  node system,
which is simply a host:port pair that points to a single redis-server instance.
Each node is given a symbolic node name "node_i" where i is the number gotten from this hashing system
"str((abs(binascii.crc32(key) & 0xffffffff) % len(targets)) + 1)"
to uniquely identify it in a way that doesn’t tie it to a specific host (or port).
e.g.
config = {
  'node_1':{'host':'192.168.0.101', 'port':6379},
  'node_2':{'host':'192.168.0.102', 'port':6379},
  'node_3':{'host':'192.168.0.103', 'port':6379},
}



Examples:
  python redis-sharding.py --help                                show this doc

  python redis-sharding.py \
  --sources=192.168.0.99:6379,192.168.0.100:6379 \
  --targets="node_1#192.168.0.101:6379,node_2#192.168.0.102:6379,node_3#192.168.0.103:6379" \
  --databases=2,5 --clean


  python redis-sharding.py \
  --sources=192.168.0.99:6379,192.168.0.100:6379 \
  --targets="node_1#192.168.0.101:6379,node_2#192.168.0.102:6379,node_3#192.168.0.103:6379" \
  --databases=2,5

  python redis-sharding.py --limit=1000 \
  --sources=192.168.0.99:6379,192.168.0.100:6379 \
  --targets="node_1#192.168.0.101:6379,node_2#192.168.0.102:6379,node_3#192.168.0.103:6379" \
  --databases=2,5

"""

__author__ = "Salimane Adjao Moustapha (salimane@gmail.com)"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 2011/06/09 12:57:19 $"
__copyleft__ = "Copyleft (c) 2011 Salimane Adjao Moustapha"
__license__ = "MIT"


import redis
import time
import binascii
import sys
import getopt


class RedisSharding:
    """A class for resharding the keys in a number of source redis servers into another number of target cluster of redis servers
    """

    #some key prefix for this script
    shardprefix = 'rsk:'
    keylistprefix = 'keylist:'
    hkeylistprefix = 'havekeylist:'

    # hold the redis handle of the targets cluster
    targets_redis = {}

    # numbers of keys to resharding on each iteration
    limit = 10000

    def __init__(self, sources, targets, dbs):
        self.sources = sources
        self.targets = targets
        self.len_targets = len(targets)
        self.dbs = dbs
        for node in self.targets:
            for db in self.dbs:
                self.targets_redis[node + '_' + str(db)] = redis.StrictRedis(host=self.targets[node]['host'], port=self.targets[node]['port'], db=db)

    def save_keylists(self):
        """Function for each server in the sources, save all its keys' names into a list for later usage.
        """

        for server in self.sources:
            for db in self.dbs:
                servername = server['host'] + ":" + str(
                    server['port']) + ":" + str(db)
                #get redis handle for server-db
                r = redis.StrictRedis(
                    host=server['host'], port=server['port'], db=db)
                dbsize = r.dbsize()
                #check whether we already have the list, if not get it
                hkl = r.get(
                    self.shardprefix + self.hkeylistprefix + servername)
                if hkl is None or int(hkl) != 1:
                    print "Saving the keys in %s to temp keylist...\n" % servername
                    moved = 0
                    r.delete(
                        self.shardprefix + self.keylistprefix + servername)
                    for key in r.keys('*'):
                        moved += 1
                        r.rpush(self.shardprefix +
                                self.keylistprefix + servername, key)
                        if moved % self.limit == 0:
                            print  "%d keys of %s inserted in temp keylist at %s...\n" % (moved, servername, time.strftime("%Y-%m-%d %I:%M:%S"))

                    r.set(self.shardprefix +
                          self.hkeylistprefix + servername, 1)
                print "ALL %d keys of %s already inserted to temp keylist ...\n\n" % (dbsize - 1, servername)

    def reshard_db(self, limit=None):
        """Function for each server in the sources, reshard all its keys into the new target cluster.
        - limit : optional numbers of keys to reshard per run
        """

        #set the limit per run
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = None

        if limit is not None:
            self.limit = limit

        for server in self.sources:
            for db in self.dbs:
                servername = server['host'] + ":" + str(
                    server['port']) + ":" + str(db)
                print "Processing keys resharding of server %s at %s...\n" % (
                    servername, time.strftime("%Y-%m-%d %I:%M:%S"))
                #get redis handle for current source server-db
                r = redis.StrictRedis(
                    host=server['host'], port=server['port'], db=db)
                moved = 0
                dbsize = r.dbsize() - 1
                #get keys already moved
                keymoved = r.get(self.shardprefix + "keymoved:" + servername)
                keymoved = 0 if keymoved is None else int(keymoved)
                #check if we already have all keys resharded for current source server-db
                if dbsize <= keymoved:
                    print "ALL %d keys from %s have already been resharded.\n" % (dbsize, servername)
                    #move to next source server-db in iteration
                    continue

                print "Started resharding of %s keys from %d to %d at %s...\n" % (servername, keymoved, dbsize, time.strftime("%Y-%m-%d %I:%M:%S"))
                #max index for lrange
                newkeymoved = keymoved + \
                    self.limit if dbsize > keymoved + self.limit else dbsize

                for key in r.lrange(self.shardprefix + self.keylistprefix + servername, keymoved, newkeymoved):
                    #calculate reshard node of key
                    node = str((abs(binascii.crc32(
                        key) & 0xffffffff) % self.len_targets) + 1)
                    #get key type
                    ktype = r.type(key)
                    #if undefined type go to next key
                    if ktype == 'none':
                        continue

                    #get redis handle for corresponding target server-db
                    rr = self.targets_redis['node_' + node + '_' + str(db)]
                    #save key to new cluster server-db
                    if ktype == 'string':
                        rr.set(key, r.get(key))
                    elif ktype == 'hash':
                        rr.hmset(key, r.hgetall(key))
                    elif ktype == 'list':
                        if key == self.shardprefix + "keylist:" + servername:
                            continue
                        #value = r.lrange(key, 0, -1)
                        #rr.rpush(key, *value)
                        for k in r.lrange(key, 0, -1):
                            rr.rpush(key, k)
                    elif ktype == 'set':
                        #value = r.smembers(key)
                        #rr.sadd(key, *value)
                        for k in r.smembers(key):
                            rr.sadd(key, k)
                    elif ktype == 'zset':
                        #value = r.zrange(key, 0, -1, withscores=True)
                        #rr.zadd(key, **dict(value))
                        for k, v in r.zrange(key, 0, -1, withscores=True):
                            rr.zadd(key, v, k)

                    # Handle keys with an expire time set
                    kttl = r.ttl(key)
                    kttl = -1 if kttl is None else int(kttl)
                    if kttl != -1:
                        rr.expire(key, kttl)

                    moved += 1

                    if moved % 10000 == 0:
                        print "%d keys have been resharded on %s at %s...\n" % (moved, servername, time.strftime("%Y-%m-%d %I:%M:%S"))

                r.set(self.shardprefix + "keymoved:" + servername, newkeymoved)
                print "%d keys have been resharded on %s at %s\n" % (newkeymoved, servername, time.strftime("%Y-%m-%d %I:%M:%S"))

    def flush_targets(self):
        """Function to flush all targets server in the new cluster.
        """

        for handle in self.targets_redis:
            server = handle[:handle.rfind('_')]
            db = handle[handle.rfind('_') + 1:]
            servername = self.targets[server]['host'] + ":" + \
                str(self.targets[server]['port']) + ":" + db
            print "Flushing server %s at %s...\n" % (
                servername, time.strftime("%Y-%m-%d %I:%M:%S"))
            r = self.targets_redis[handle]
            r.flushdb()
            print "Flushed server %s at %s...\n" % (
                servername, time.strftime("%Y-%m-%d %I:%M:%S"))

    def clean(self):
        """Function to clean all variables, temp lists created previously by the script.
        """

        print "Cleaning all temp variables...\n"
        for server in self.sources:
            for db in self.dbs:
                servername = server['host'] + ":" + str(
                    server['port']) + ":" + str(db)
                r = redis.StrictRedis(
                    host=server['host'], port=server['port'], db=db)
                r.delete(self.shardprefix + "keymoved:" + servername)
                r.delete(self.shardprefix + self.keylistprefix + servername)
                r.delete(self.shardprefix + self.hkeylistprefix + servername)
                r.delete(self.shardprefix + "firstrun")
                r.delete(self.shardprefix + 'run')
        print "Done.\n"


def main(sources, targets, databases, limit=None, clean=False):
    sources_cluster = []
    for k in sources.split(','):
        so = k.split(':')
        if len(so) == 2:
            sources_cluster.append({'host': so[0], 'port': int(so[1])})
        else:
            exit("""Supplied sources addresses is wrong. e.g. python redis-sharding.py 127.0.0.1:6379,127.0.0.2:6379 node_1#127.0.0.1:63791,node_2#127.0.0.1:63792  0,1
            try : python redis-sharding.py --help""")

    targets_cluster = {}
    for k in targets.split(','):
        t = k.split('#')
        if len(t) == 2:
            so = t[1].split(':')
            if len(so) == 2:
                targets_cluster[t[0]] = {'host': so[0], 'port': int(so[1])}
            else:
                exit("""Supplied target addresses is wrong. e.g. python redis-sharding.py 127.0.0.1:6379,127.0.0.2:6379 node_1#127.0.0.1:63791,node_2#127.0.0.1:63792  0,1
                try : python redis-sharding.py --help""")
        else:
            exit("""Supplied target cluster format is wrong. e.g. python redis-sharding.py 127.0.0.1:6379,127.0.0.2:6379 node_1#127.0.0.1:63791,node_2#127.0.0.1:63792  0,1
            try : python redis-sharding.py --help""")

    dbs = [int(k) for k in databases.split(',')]
    if len(dbs) < 1:
        exit("""Supplied list of db is wrong. e.g. python redis-sharding.py 127.0.0.1:6379,127.0.0.2:6379 node_1#127.0.0.1:63791,node_2#127.0.0.1:63792  0,1
        try : python redis-sharding.py --help""")

    try:
        r = redis.StrictRedis(host=sources_cluster[0]['host'],
                              port=sources_cluster[0]['port'], db=dbs[0])
    except AttributeError as e:
        exit('Please this script requires redis-py >= 2.4.10, your current version is :' + redis.__version__)

    rsd = RedisSharding(sources_cluster, targets_cluster, dbs)

    if clean == False:
        #check if script already running
        run = r.get(rsd.shardprefix + "run")
        if run is not None and int(run) == 1:
            exit('another process already running the script')
        r.set(rsd.shardprefix + 'run', 1)

        rsd.save_keylists()

        firstrun = r.get(rsd.shardprefix + "firstrun")
        firstrun = 0 if firstrun is None else int(firstrun)
        if firstrun == 0:
            rsd.flush_targets()
            r.set(rsd.shardprefix + "firstrun", 1)

        rsd.reshard_db(limit)
    else:
        rsd.clean()

    r.set(rsd.shardprefix + 'run', 0)


def usage():
    print __doc__


if __name__ == "__main__":
    clean = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hl:s:t:d:", ["help", "limit=", "sources=", "targets=", "databases=", "clean"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt == "--clean":
            clean = True
        elif opt in ("-l", "--limit"):
            limit = arg
        elif opt in ("-s", "--sources"):
            sources = arg
        elif opt in ("-t", "--targets"):
            targets = arg
        elif opt in ("-d", "--databases"):
            databases = arg

    try:
        limit = int(limit)
    except (NameError, TypeError, ValueError):
        limit = None

    try:
        main(sources, targets, databases, limit, clean)
    except NameError as e:
        usage()

########NEW FILE########
