__FILENAME__ = redis_bitset

from redis_systems import *

class BitsetFu (redis_obj):

    def add(self, item):
        self.conn.setbit(self.name, item, True)

    def remove(self, item):
        r = self.conn.setbit(self.name, item, False)
        if not r:
            raise KeyError

    def discard(self, item):
        self.conn.setbit(self.name, item, False)

    def update(self, other):
        if isinstance(other, BitsetFu):
            self.conn.bitop('OR', self.name, self.name, other.name)
        else:
            for itm in other:
                self.add(itm)

    def intersection_update(self, other):
        if isinstance(other, BitsetFu):
            self.conn.bitop('AND', self.name, self.name, other.name)
        else:
            for item in self:
                if item not in other:
                    self.discard(item)

    def symmetric_difference_update(self, other):
        if isinstance(other, BitsetFu):
            self.conn.bitop('XOR', self.name, self.name, other.name)
        else:
            for item in other:
                if item in self:
                    self.remove(item)
                else:
                    self.add(item)

    def __len__(self):
        return self.conn.bitcount(self.name)

    def __iter__(self):
        for i in range(self.conn.strlen(self.name)*8):
            if self.conn.getbit(self.name, i):
                yield i

    def __contains__(self, item):
        return self.conn.getbit(self.name, item)

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self

    def __ior__(self, other):
        self.update(other)
        return self
########NEW FILE########
__FILENAME__ = redis_hash
from redis_systems import *

class HashFu (redis_obj):

    def get(self, key, default=None):
        r = self.conn.hget(self.name, key)
        if r == None: r = default
        return r

    def keys(self):
        return self.conn.hkeys(self.name) or []

    def values(self):
        return self.conn.hvals(self.name) or []

    def items(self):
        return self.conn.hgetall(self.name).items()

    def pop(self, key, *args):
        n = self.name
        def f(pipe):
            pipe.multi()
            pipe.hget(n, key)
            pipe.hdel(n, key)
        r = self.conn.transaction(f, key)
        if r and r[1]:
            return r[0]
        elif args:
            return args[0]
        else:
            raise KeyError

    def update(self, *args, **kwargs):
        for o in args:
            self._update(o)
        self._update(kwargs)

    def _update(self, other):
        if hasattr(other, 'items'):
            for k,v in other.items():
                self[k] = v
        else:
            for k,v in other:
                self[k] = v

    def iter(self):
        for k in self.keys():
            yield k

    def __len__(self):
        return self.conn.hlen(self.name) or 0

    def __iter__(self):
        return self.iter()

    def __getitem__(self, key):
        val = self.get(key)
        if val == None:
            raise KeyError
        return val

    def __setitem__(self, key, value):
        self.conn.hset(self.name, key, value)

    def __delitem__(self, key):
        self.conn.hdel(self.name, key)

    def __contains__(self, key):
        return self.conn.hexists(self.name, key)


########NEW FILE########
__FILENAME__ = redis_list

from redis_systems import *

class ListFu (redis_obj):

    def append(self, item):
        self.conn.rpush(self.name, item)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def remove(self, value):
        self.conn.lrem(self.name, value)

    def pop(self, index=None):
        if index:
            raise ValueError('Not supported')
        return self.conn.rpop(self.name)

    def list_trim(self, start, stop):
        self.conn.ltrim(self.name, start, stop)

    def __len__(self):
        return self.conn.llen(self.name)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.conn.lrange(self.name, key.start, key.stop)

        val = self.conn.lindex(self.name, key)
        if not val:
            raise IndexError
        return val

    def __setitem__(self, key, value):
        try:
            self.conn.lset(self.name, key, value)
        except redis.exceptions.ResponseError:
            raise IndexError

    def __iter__(self):
        i = 0
        while True:
            items = self.conn.lrange(self.name, i, i+30)
            if len(items) == 0:
                raise StopIteration
            for item in items:
                yield item
            i += 30


########NEW FILE########
__FILENAME__ = redis_set

from redis_systems import *

class SetFu (redis_obj):

    def add(self, item):
        self.conn.sadd(self.name, item)

    def discard(self, item):
        self.conn.srem(self.name, item)

    def remove(self, item):
        r = self.conn.srem(self.name, item)
        if r < 1:
            raise KeyError

    def pop(self):
        r = self.conn.spop(self.name)
        if r == None:
            raise KeyError
        return r

    def update(self, other):
        if isinstance(other, SetFu):
            self.conn.sunionstore(self.name, self.name, other.name)
        else:
            for item in other:
                self.add(item)

    def intersection_update(self, other):
        if isinstance(other, SetFu):
            self.conn.sinterstore(self.name, self.name, other.name)
        else:
            for item in self:
                if item not in other:
                    self.discard(item)

    def difference_update(self, other):
        if isinstance(other, SetFu):
            self.conn.sdiffstore(self.name, self.name, other.name)
        else:
            for item in other:
                self.discard(item)

    def symmetric_difference_update(self, other):
        if isinstance(other, SetFu):
            with self.conn.pipeline(transaction=True) as trans:
                trans.sunionstore('__transientkey-1__', self.name, other.name)
                trans.sinterstore('__transientkey-2__', self.name, other.name)
                trans.sdiffstore(self.name, '__transientkey-1__', '__transientkey-2__')
                trans.delete('__transientkey-1__', '__transientkey-2__')
                trans.execute()
        else:
            for item in other:
                if item in self:
                    self.remove(item)
                else:
                    self.add(item)

    def __iter__(self):
        for item in self.conn.smembers(self.name):
            yield item

    def __len__(self):
        return self.conn.scard(self.name)

    def __contains__(self, item):
        return self.conn.sismember(self.name, item)

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self

    def __ior__(self, other):
        self.update(other)
        return self


########NEW FILE########
__FILENAME__ = redis_systems
import redis


#--- System related ----------------------------------------------
SYSTEMS = {
    'default': redis.Redis(host='localhost', port=6379)
}

def setup_system(name, host, port, **kw):
    SYSTEMS[name] = redis.Redis(host=host, port=port, **kw)

def get_redis(system='default'):
    return SYSTEMS[system]


class redis_obj:

    def __init__(self, name, system):
        self.name = name
        self.conn = get_redis(system)

    def clear(self):
        self.conn.delete(self.name)


########NEW FILE########
__FILENAME__ = test
import sys
from redis_wrap import get_redis, get_list, get_hash, get_set, get_bitset

def raises(f, excpt):
    try:
        f()
        return False
    except excpt:
        return True


def setup_module(module=None):
    get_redis().delete('bears')
    get_redis().delete('deers')
    get_redis().delete('villains')
    get_redis().delete('fishes')

    print sys._getframe(0).f_code.co_name, 'ok.'

def test_list():
    bears = get_list('bears')
    assert len(bears) == 0

    bears.append('grizzly')
    assert len(bears) == 1

    for bear in bears:
        assert bear == 'grizzly'

    assert 'grizzly' in bears

    bears.extend(['white bear', 'pedo bear'])
    assert len(bears) == 3

    bears[2] = 'nice bear'
    assert bears[2] == 'nice bear'

    assert 5 > len(bears)
    try:
        bears[5] = 'dizzy bear'
    except IndexError:
        pass

    bears.extend(['polar bear', 'gummy bear'])
    assert bears[1:2] == ['white bear', 'nice bear']
    assert bears[2:4] == ['nice bear', 'polar bear', 'gummy bear']

    bears.remove('grizzly')
    assert 'grizzly' not in bears

    print sys._getframe(0).f_code.co_name, 'ok.'

def test_list_trim():
    deers = get_list('deers')

    for i in range(0, 100):
        deers.append('rudolf_%s' % i)

    assert len(deers) == 100

    deers.list_trim(0, 5)

    assert len(deers) == 6

    assert deers[0] == 'rudolf_0'
    assert deers[1] == 'rudolf_1'

    print sys._getframe(0).f_code.co_name, 'ok.'

def test_hash():
    villains = get_hash('villains')
    assert 'riddler' not in villains

    villains['riddler'] = 'Edward Nigma'
    assert 'riddler' in villains
    assert villains.get('riddler') == 'Edward Nigma'

    assert len(villains.keys()) == 1
    assert villains.values() == ['Edward Nigma']

    assert list(villains) == ['riddler']

    assert villains.items() == [('riddler', 'Edward Nigma')]

    del villains['riddler']
    assert len(villains.keys()) == 0
    assert 'riddler' not in villains

    villains['drZero'] = ''
    assert villains['drZero'] == ''

    assert villains.pop('drZero') == ''
    assert 'drZero' not in villains

    assert raises(lambda: villains.pop('Mysterio'), KeyError)
    assert villains.pop('Mysterio', 'Quentin Beck') == 'Quentin Beck'

    villains.update({'drEvil':'Douglas Powers'})
    villains.update([('joker','Jack'),('penguin','Oswald Chesterfield Cobblepot')])
    assert set(villains.items()) == set([
        ('drEvil','Douglas Powers'),
        ('joker','Jack'),
        ('penguin','Oswald Chesterfield Cobblepot')])

    other_villains = get_hash('minions')
    other_villains.update(lizard='Curt Connors', rhino='Aleksei Sytsevich')
    villains.update(other_villains)
    assert set(villains.items()) == set([
        ('drEvil','Douglas Powers'),
        ('joker','Jack'),
        ('penguin','Oswald Chesterfield Cobblepot'),
        ('lizard','Curt Connors'),
        ('rhino', 'Aleksei Sytsevich')])

    print sys._getframe(0).f_code.co_name, 'ok.'

def test_set():
    fishes = get_set('fishes')
    assert len(fishes) == 0
    assert 'nemo' not in fishes

    assert raises(lambda: fishes.remove('nemo'), KeyError)

    fishes.discard('nemo')      # it's ok to .discard() nonexistant items

    fishes.add('nemo')
    assert len(fishes) == 1
    assert 'nemo' in fishes

    for item in fishes:
        assert item == 'nemo'

    fishes.remove('nemo')
    assert len(fishes) == 0

    fishes.add('dory')
    assert fishes.pop() == 'dory'
    assert raises(lambda: fishes.pop(), KeyError)

    fishes.add('marlin')
    assert len(fishes) == 1
    fishes.clear()
    assert len(fishes) == 0

    fishes.update(('nemo','marlin'))
    assert set(fishes) == set (['nemo','marlin'])
    fishes |= ('dory','crush')
    assert set(fishes) == set (['nemo','marlin', 'dory', 'crush'])

    other_fishes = get_set('other_fishes')
    other_fishes.update(('gill', 'bloat', 'flo'))
    fishes |= other_fishes
    assert set(fishes) == set(['nemo','marlin', 'dory', 'crush', 'gill', 'bloat', 'flo'])

    fishes.intersection_update(('nemo','marlin', 'dory', 'crush', 'gill', 'deb', 'bloat'))
    assert set(fishes) == set(['nemo','marlin', 'dory', 'crush', 'gill', 'bloat'])
    fishes &= ('nemo','marlin', 'dory', 'gill', 'bloat', 'gurgle')
    assert set(fishes) == set(['nemo','marlin', 'dory', 'gill', 'bloat'])
    fishes &= other_fishes
    assert set(fishes) == set(['gill', 'bloat'])

    fishes.clear()
    fishes.update(('nemo','marlin', 'dory', 'gill', 'bloat'))
    fishes.difference_update(('gill', 'bloat', 'flo'))
    assert set(fishes) == set(['nemo','marlin', 'dory'])

    fishes.clear()
    fishes.update(('nemo','marlin', 'dory', 'gill', 'bloat'))
    fishes -= ('gill', 'bloat', 'flo')
    assert set(fishes) == set(['nemo','marlin', 'dory'])

    fishes.clear()
    fishes.update(('nemo','marlin', 'dory', 'gill', 'bloat'))
    fishes -= other_fishes
    assert set(fishes) == set(['nemo','marlin', 'dory'])

    fishes.clear()
    fishes.update(('nemo','marlin', 'dory', 'gill', 'bloat'))
    fishes.symmetric_difference_update(('gill', 'bloat', 'flo'))
    assert set(fishes) == set(['nemo','marlin', 'dory', 'flo'])

    fishes.clear()
    fishes.update(('nemo','marlin', 'dory', 'gill', 'bloat'))
    fishes ^= ('gill', 'bloat', 'flo')
    assert set(fishes) == set(['nemo','marlin', 'dory', 'flo'])

    fishes.clear()
    fishes.update(('nemo','marlin', 'dory', 'gill', 'bloat'))
    fishes ^= other_fishes
    assert set(fishes) == set(['nemo','marlin', 'dory', 'flo'])
    print sys._getframe(0).f_code.co_name, 'ok.'

def test_bitset():
    users = get_bitset('users')
    users.clear()
    assert len(users) == 0

    assert 3 not in users
    users.add(3)
    assert len(users) == 1
    assert 3 in users

    assert raises(lambda: users.remove(9), KeyError)
    users.discard(9)
    users.add(7)
    users.remove(7)

    users |= (5,4)
    assert set(users) == set([3,4,5])

    others = get_bitset('others')
    others |= (4,6,8)
    assert set(others) == set([4,6,8])
    users |= others
    assert set(users) == set([3,4,5,6,8])

    users &= (4,5,6,7,8)
    assert set(users) == set([4,5,6,8])

    users.clear()
    assert len(users) == 0

    print sys._getframe(0).f_code.co_name, 'ok.'

if __name__ == '__main__':
    setup_module()
    test_list()
    test_list_trim()
    test_hash()
    test_set()
    test_bitset()

########NEW FILE########
