__FILENAME__ = memcache_ring
import memcache
import types

from hash_ring import HashRing

class MemcacheRing(memcache.Client):
    """Extends python-memcache so it uses consistent hashing to
    distribute the keys.
    """

    def __init__(self, servers, *k, **kw):
        self.hash_ring = HashRing(servers)

        memcache.Client.__init__(self, servers, *k, **kw)

        self.server_mapping = {}
        for server_uri, server_obj in zip(servers, self.servers):
            self.server_mapping[server_uri] = server_obj

    def _get_server(self, key):
        if type(key) == types.TupleType:
            return memcache.Client._get_server(key)

        for i in range(self._SERVER_RETRIES):
            iterator = self.hash_ring.iterate_nodes(key)
            for server_uri in iterator:
                server_obj = self.server_mapping[server_uri]
                if server_obj.connect():
                    return server_obj, key

        return None, None

########NEW FILE########
__FILENAME__ = ring
# -*- coding: utf-8 -*-
from hash_ring._compat import bytes
"""
    hash_ring
    ~~~~~~~~~~~~~~
    Implements consistent hashing that can be used when
    the number of server nodes can increase or decrease (like in memcached).

    Consistent hashing is a scheme that provides a hash table functionality
    in a way that the adding or removing of one slot
    does not significantly change the mapping of keys to slots.

    More information about consistent hashing can be read in these articles:

        "Web Caching with Consistent Hashing":
            http://www8.org/w8-papers/2a-webserver/caching/paper2.html

        "Consistent hashing and random trees:
        Distributed caching protocols for relieving hot spots on the World Wide Web (1997)":
            http://citeseerx.ist.psu.edu/legacymapper?did=38148


    Example of usage::

        memcache_servers = ['192.168.0.246:11212',
                            '192.168.0.247:11212',
                            '192.168.0.249:11212']

        ring = HashRing(memcache_servers)
        server = ring.get_node('my_key')

    :copyright: 2008 by Amir Salihefendic.
    :license: BSD
"""

import math
import sys
from bisect import bisect

if sys.version_info >= (2, 5):
    import hashlib
    md5_constructor = hashlib.md5
else:
    import md5
    md5_constructor = md5.new

class HashRing(object):

    def __init__(self, nodes=None, weights=None):
        """`nodes` is a list of objects that have a proper __str__ representation.
        `weights` is dictionary that sets weights to the nodes.  The default
        weight is that all nodes are equal.
        """
        self.ring = dict()
        self._sorted_keys = []

        self.nodes = nodes

        if not weights:
            weights = {}
        self.weights = weights

        self._generate_circle()

    def _generate_circle(self):
        """Generates the circle.
        """
        total_weight = 0
        for node in self.nodes:
            total_weight += self.weights.get(node, 1)

        for node in self.nodes:
            weight = 1

            if node in self.weights:
                weight = self.weights.get(node)

            factor = math.floor((40*len(self.nodes)*weight) / total_weight);

            for j in range(0, int(factor)):
                b_key = self._hash_digest( '%s-%s' % (node, j) )

                for i in range(0, 3):
                    key = self._hash_val(b_key, lambda x: x+i*4)
                    self.ring[key] = node
                    self._sorted_keys.append(key)

        self._sorted_keys.sort()

    def get_node(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned.

        If the hash ring is empty, `None` is returned.
        """
        pos = self.get_node_pos(string_key)
        if pos is None:
            return None
        return self.ring[ self._sorted_keys[pos] ]

    def get_node_pos(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned
        along with it's position in the ring.

        If the hash ring is empty, (`None`, `None`) is returned.
        """
        if not self.ring:
            return None

        key = self.gen_key(string_key)

        nodes = self._sorted_keys
        pos = bisect(nodes, key)

        if pos == len(nodes):
            return 0
        else:
            return pos

    def iterate_nodes(self, string_key, distinct=True):
        """Given a string key it returns the nodes as a generator that can hold the key.

        The generator iterates one time through the ring
        starting at the correct position.

        if `distinct` is set, then the nodes returned will be unique,
        i.e. no virtual copies will be returned.
        """
        if not self.ring:
            yield None, None

        returned_values = set()
        def distinct_filter(value):
            if str(value) not in returned_values:
                returned_values.add(str(value))
                return value

        pos = self.get_node_pos(string_key)
        for key in self._sorted_keys[pos:]:
            val = distinct_filter(self.ring[key])
            if val:
                yield val

        for i, key in enumerate(self._sorted_keys):
            if i < pos:
                val = distinct_filter(self.ring[key])
                if val:
                    yield val

    def gen_key(self, key):
        """Given a string key it returns a long value,
        this long value represents a place on the hash ring.

        md5 is currently used because it mixes well.
        """
        b_key = self._hash_digest(key)
        return self._hash_val(b_key, lambda x: x)

    def _hash_val(self, b_key, entry_fn):
        return (( b_key[entry_fn(3)] << 24)
                |(b_key[entry_fn(2)] << 16)
                |(b_key[entry_fn(1)] << 8)
                | b_key[entry_fn(0)] )

    def _hash_digest(self, key):
        m = md5_constructor()
        m.update(bytes(key, 'utf-8'))
        return list(map(ord, str(m.digest())))

########NEW FILE########
__FILENAME__ = _compat
import sys

if sys.version_info[0] < 3:
    xrange = xrange
    # sounds weird but I need to set the encoding for python3.3
    bytes = lambda x, y: str(x)
else:
    xrange = range
    bytes = bytes

########NEW FILE########
__FILENAME__ = change_distribution
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hash_ring import HashRing

text = open('tests/palindromes.txt', encoding='utf-8').read()
text = text.replace('\n', '').replace('a ', '').replace('an ', '')
palindromes = [t.strip() for t in text.split(',')]

#--- Helper functions ----------------------------------------------
def create_sets(servers):
    server_sets = {}
    for s in servers:
        server_sets[s] = set()

    ring = HashRing(servers)
    for word in palindromes:
        node = ring.get_node(word)
        server_sets[node].add(word)

    return server_sets

def print_distributions(name, server_sets):
    print('\nDistribution of %s::' % name)
    for s in server_sets:
        print('%s: %s' % (s, len(server_sets[s])))

def print_set_info(servers_init, servers_new):
    for init_server in servers_init:
        init_set = servers_init[init_server]
        new_set = servers_new[init_server]

        print('')
        print('%s: %s in init_set' %\
                (init_server, len(init_set)))
        print('%s: %s in new_set' %\
                (init_server, len(new_set)))
        print('%s: %s in both init_set and new_set' %\
                (init_server, len(init_set.intersection(new_set))))

#--- Testing ----------------------------------------------
init_servers = ['192.168.0.246:11212',
                '192.168.0.247:11212',
                '192.168.0.248:11212']
server_sets_3 = create_sets(init_servers)

print_distributions('server_sets_3', server_sets_3)

extra_servers = ['192.168.0.246:11212',
                 '192.168.0.247:11212',
                 '192.168.0.248:11212',
                 '192.168.0.249:11212',
                 '192.168.0.250:11212']
server_sets_5 = create_sets(extra_servers)

print_distributions('server_sets_5', server_sets_5)

print_set_info(server_sets_3, server_sets_5)

########NEW FILE########
__FILENAME__ = iteration_benchmark
import os, sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hash_ring import HashRing

init_servers = ['192.168.0.246:11212',
                '192.168.0.247:11212',
                '192.168.0.249:11212',
                '192.168.0.250:11212',
                '192.168.0.251:11212',
                '192.168.0.252:11212',
                '192.168.0.253:11212',
                '192.168.0.255:11212',
                '192.168.0.256:11212',
                '192.168.0.257:11212',
                '192.168.0.258:11212',
                '192.168.0.259:11212']

ring = HashRing(init_servers)
t_start = time.time()
for n in ring.iterate_nodes('test'):
    print(n)
print('Time elapsed %s' % (time.time() - t_start))

########NEW FILE########
__FILENAME__ = random_distribution
import os
import sys
import random
import string
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hash_ring import HashRing

memcache_servers = ['192.168.0.246:11212',
                    '192.168.0.247:11212',
                    '192.168.0.249:11212']
weights = {
    '192.168.0.246:11212': 1,
    '192.168.0.247:11212': 2,
    '192.168.0.249:11212': 1
}

ring = HashRing(memcache_servers, weights)
iterations = 100000

def genCode(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join([random.choice(chars) for i in range(length)])

def random_distribution():
    counts = {}
    for s in memcache_servers:
        counts[s] = 0

    for i in range(0, iterations):
        word = genCode(10)
        counts[ring.get_node(word)] += 1

    for k in counts:
        print('%s: %s' % (k, counts[k]))

    print(sum(counts.values()))

random_distribution()

########NEW FILE########
__FILENAME__ = test_ring
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hash_ring import HashRing

#--- Global ----------------------------------------------
memcache_servers = ['192.168.0.246:11212',
                    '192.168.0.247:11212',
                    '192.168.0.249:11212',
                    '192.168.0.250:11212',
                    '192.168.0.251:11212',
                    '192.168.0.252:11212',]

ring = HashRing(memcache_servers)

text = open('tests/palindromes.txt').read()
text = text.replace('\n', '').replace('a ', '').replace('an ', '')
palindromes = text.split(',')


#--- Tests ----------------------------------------------
def test_palindromes():
    assert len(palindromes) > 0

def test_get_node():
    server = ring.get_node('amir')
    assert server in memcache_servers
    assert ring.get_node('amir') == ring.get_node('amir')


def test_distribution():
    counts = {}
    for s in memcache_servers:
        counts[s] = 0

    def count_word(w):
        counts[ring.get_node(w)] += 1

    for palindrome in palindromes:
        count_word(palindrome)

    for s in memcache_servers:
        assert counts[s] > 0

def test_iterate_nodes():
    simple_list = ['1', '2', '3', '4', '5']
    new_ring = HashRing(simple_list)

    nodes = []
    for node in new_ring.iterate_nodes('a'):
        nodes.append(node)

    assert len(nodes) == len(simple_list)
    for elm in simple_list:
        assert elm in nodes


class Server(object):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return str(self.name)

def test_with_objects():
    simple_list = [Server(1), Server(2), Server(3)]

    new_ring = HashRing(simple_list)

    node = new_ring.get_node('BABU')
    assert node in simple_list

    nodes = []
    for node in new_ring.iterate_nodes('aloha'):
        nodes.append(node)

    assert len(nodes) == len(simple_list)
    for elm in simple_list:
        assert elm in nodes

########NEW FILE########
