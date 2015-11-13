__FILENAME__ = redis_config
"""
Monkey patch configuration here...
"""
import redis

CLIENT = redis.Redis()

########NEW FILE########
__FILENAME__ = redis_dict
"""
This is module contains RedisDict, which allows users to interact with
Redis strings using the standard Python dictionary syntax.

Note that this uses an entire Redis database to back the dictionary,
not a Redis hashmap. If you prefer an interface to a hashmap, the
``redis_hash_dict`` file does just that.
"""
import UserDict
import redis_ds.redis_config as redis_config
from redis_ds.serialization import PassThroughSerializer, PickleSerializer, JSONSerializer


class RedisDict(UserDict.DictMixin, PassThroughSerializer):
    "Dictionary interface to Redis database."
    def __init__(self, redis_client=redis_config.CLIENT):
        """
        Parameters:
        - redis_client: configured redis_client to use for all requests.
                        should be fine to monkey patch this to set the
                        default settings for your environment...
        """
        self._client = redis_client

    def keys(self, pattern="*"):
        "Keys for Redis dictionary."
        return self._client.keys(pattern)

    def __len__(self):
        "Number of key-value pairs in dictionary/database."
        return self._client.dbsize()

    def __getitem__(self, key):
        "Retrieve a value by key."
        return self.deserialize(self._client.get(key))

    def __setitem__(self, key, val):
        "Set a value by key."
        val = self.serialize(val)
        return self._client.set(key, val)

    def __delitem__(self, key):
        "Ensure deletion of a key from dictionary."
        return self._client.delete(key)

    def __contains__(self, key):
        "Check if database contains a specific key."
        return self._client.exists(key)

    def get(self, key, default=None):
        "Retrieve a key's value from the database falling back to a default."
        return self.__getitem__(key) or default


class PickleRedisDict(RedisDict, PickleSerializer):
    "Serialize redis dictionary values via pickle."
    pass


class JSONRedisDict(RedisDict, JSONSerializer):
    "Serialize redis dictionary values via JSON."
    pass

########NEW FILE########
__FILENAME__ = redis_hash_dict
"""
Module contains RedisHashDict, which allows users to interact with Redis hashes
as if they were Python dictionaries.
"""
import redis_ds.redis_config as redis_config
from redis_ds.serialization import PassThroughSerializer, PickleSerializer, JSONSerializer
import UserDict


class RedisHashDict(UserDict.DictMixin, PassThroughSerializer):
    "A dictionary interface to Redis hashmaps."
    def __init__(self, hash_key, redis_client=redis_config.CLIENT):
        "Initialize the redis hashmap dictionary interface."
        self._client = redis_client
        self.hash_key = hash_key

    def keys(self):
        "Return all keys in the Redis hashmap."
        return self._client.hkeys(self.hash_key)

    def __len__(self):
        "Number of key-value pairs in the Redis hashmap."
        return self._client.hlen(self.hash_key)

    def __getitem__(self, key):
        "Retrieve a value from the hashmap."
        return self.deserialize(self._client.hget(self.hash_key, key))

    def __setitem__(self, key, val):
        "Set a key's value in the hashmap."
        val = self.serialize(val)
        return self._client.hset(self.hash_key, key, val)

    def __delitem__(self, key):
        "Ensure a key does not exist in the hashmap."
        return self._client.hdel(self.hash_key, key)

    def __contains__(self, key):
        "Check if a key exists within the hashmap."
        return self._client.hexists(self.hash_key, key)

    def get(self, key, default=None):
        "Retrieve a key's value or a default value if the key does not exist."
        return self.__getitem__(key) or default


class PickleRedisHashDict(RedisHashDict, PickleSerializer):
    "Serialize hashmap values using pickle."
    pass


class JSONRedisHashDict(RedisHashDict, JSONSerializer):
    "Serialize hashmap values using JSON."
    pass

########NEW FILE########
__FILENAME__ = redis_list
"A pythonic interface to a Redis dictionary."
import redis_ds.redis_config as redis_config
from redis_ds.serialization import PassThroughSerializer, PickleSerializer, JSONSerializer


class RedisList(PassThroughSerializer):
    "Interface to a Redis list."
    def __init__(self, list_key, redis_client=redis_config.CLIENT):
        "Initialize interface."
        self._client = redis_client
        self.list_key = list_key

    def __len__(self):
        "Number of values in list."
        return self._client.llen(self.list_key)

    def __getitem__(self, key):
        "Retrieve a value by index or values by slice syntax."
        if type(key) == int:
            return self.deserialize(self._client.lindex(self.list_key, key))
        elif hasattr(key, 'start') and hasattr(key, 'stop'):
            start = key.start or 0
            stop = key.stop or -1
            values = self._client.lrange(self.list_key, start, stop)
            return [self.deserialize(value) for value in values]
        else:
            raise IndexError

    def __setitem__(self, pos, val):
        "Set the value at a position."
        val = self.serialize(val)
        return self._client.lset(self.list_key, pos, val)

    def append(self, val, head=False):
        "Append a value to list to rear or front."
        val = self.serialize(val)
        if head:
            return self._client.lpush(self.list_key, val)
        else:
            return self._client.rpush(self.list_key, val)

    def pop(self, head=False, blocking=False):
        "Remove an value from head or tail of list."
        if head and blocking:
            return self.deserialize(self._client.blpop(self.list_key)[1])
        elif head:
            return self.deserialize(self._client.lpop(self.list_key))
        elif blocking:
            return self.deserialize(self._client.brpop(self.list_key)[1])
        else:
            return self.deserialize(self._client.rpop(self.list_key))

    def __unicode__(self):
        "Represent entire list."
        return u"RedisList(%s)" % (self[0:-1],)

    def __repr__(self):
        "Represent entire list."
        return self.__unicode__()


class PickleRedisList(RedisList, PickleSerializer):
    "Serialize Redis List values via Pickle."
    pass


class JSONRedisList(RedisList, JSONSerializer):
    "Serialize Redis List values via JSON."
    pass

########NEW FILE########
__FILENAME__ = redis_set
"A Pythonic interface to a Redis set."
import redis_ds.redis_config as redis_config
from redis_ds.serialization import PassThroughSerializer, PickleSerializer, JSONSerializer


class RedisSet(PassThroughSerializer):
    "An object which behaves like a Python set, but which is based by Redis."
    def __init__(self, set_key, redis_client=redis_config.CLIENT):
        "Initialize the set."
        self._client = redis_client
        self.set_key = set_key
        
    def __len__(self):
        "Number of values in the set."
        return self._client.scard(self.set_key)

    def add(self, val):
        "Add a value to the set."
        val = self.serialize(val)
        self._client.sadd(self.set_key, val)
        
    def update(self, vals):
        "Idempotently add multiple values to the set."
        vals = [self.serialize(x) for x in vals]
        self._client.sadd(self.set_key, *vals)

    def __contains__(self, val):
        "Check if a value is a member of a set."
        return self._client.sismember(self.set_key, val)
        
    def pop(self):
        "Remove and return a value from the set."
        return self.deserialize(self._client.spop(self.set_key))
    
    def remove(self, val):
        "Remove a specific value from the set."
        self._client.srem(self.set_key, self.serialize(val))
    
    def __unicode__(self):
        "Represent all members in a set."
        objs = self._client.smembers(self.set_key)
        objs = [self.deserialize(x) for x in objs]
        return u"RedisSet(%s)" % (objs,)

    def __repr__(self):
        "Represent all members in a set."
        return self.__unicode__()


class PickleRedisSet(RedisSet, PickleSerializer):
    "Pickle values stored in set."
    pass


class JSONRedisSet(RedisSet, JSONSerializer):
    "JSON values stored in set."
    pass
    

########NEW FILE########
__FILENAME__ = serialization
"Mixins for serializing objects."
import json
import cPickle as pickle


class PassThroughSerializer(object):
    "Don't serialize."
    def serialize(self, obj):
        "Support for serializing objects stored in Redis."
        return obj

    def deserialize(self, obj):
        "Support for deserializing objects stored in Redis."
        return obj


class PickleSerializer(PassThroughSerializer):
    "Serialize values using pickle."
    def serialize(self, obj):
        return pickle.dumps(obj)

    def deserialize(self, obj):
        "Deserialize values using pickle."
        return pickle.loads(obj)


class JSONSerializer(PassThroughSerializer):
    "Serialize values using JSON."
    def serialize(self, obj):
        return json.dumps(obj)

    def deserialize(self, obj):
        "Deserialize values using JSON."
        return json.loads(obj)


########NEW FILE########
__FILENAME__ = tests
"Tests for redis datastructures."
import unittest
from redis_ds.redis_dict import RedisDict, PickleRedisDict, JSONRedisDict
from redis_ds.redis_hash_dict import RedisHashDict, PickleRedisHashDict, JSONRedisHashDict
from redis_ds.redis_list import RedisList, PickleRedisList, JSONRedisList
from redis_ds.redis_set import RedisSet, PickleRedisSet, JSONRedisSet


class TestRedisDatastructures(unittest.TestCase):
    "Test the various data structures."
    prefix = "test_rds"

    def test_redis_dict(self):
        "Test the redis dict implementation."
        key = "%s.dict" % self.prefix
        for class_impl in (RedisDict, PickleRedisDict, JSONRedisDict):
            rd = class_impl()
            del rd[key]
            init_size = len(rd)
            self.assertFalse(key in rd)
            rd[key] = 10
            self.assertTrue(key in rd)
            self.assertEqual(len(rd), init_size + 1)

            # pass through serialize loses type information, whereas
            # the other serializers retain type correctly, hence the
            # ambiguity in this test
            self.assertTrue(rd[key] in  ('10', 10))
            del rd[key]
            self.assertFalse(key in rd)
            self.assertEqual(len(rd), init_size)

    def test_redis_hash_dict(self):
        "Test the redis hash dict implementation."
        hash_key = "%s.hash_dict" % self.prefix
        key = "hello"

        # ensure dictionary isn't here
        rd = RedisDict()
        del rd[hash_key]

        for class_impl in (RedisHashDict, PickleRedisHashDict, JSONRedisHashDict):
            rhd = class_impl(hash_key)
            self.assertEqual(len(rhd), 0)
            self.assertFalse(key in rhd)
            rhd[key] = 10
            self.assertTrue(key in rhd)
            self.assertEqual(len(rhd), 1)

            # pass through serialize loses type information, whereas
            # the other serializers retain type correctly, hence the
            # ambiguity in this test
            self.assertTrue(rhd[key] in  ('10', 10))
            del rhd[key]
            self.assertFalse(key in rhd)
            self.assertEqual(len(rhd), 0)

    def test_redis_list(self):
        "Test the redis hash dict implementation."
        list_key = "%s.list" % self.prefix

        # ensure list isn't here
        rd = RedisDict()
        del rd[list_key]

        for class_impl in (RedisList, PickleRedisList, JSONRedisList):
            rl = class_impl(list_key)
            self.assertEqual(len(rl), 0)
            rl.append("a")            
            rl.append("b")
            self.assertEqual(len(rl), 2)
            self.assertEquals(rl[0], "a")
            self.assertEquals(rl[-1], "b")
            self.assertEquals(rl[:1], ["a", "b"])
            self.assertEquals(rl[:], ["a", "b"])
            self.assertEquals(rl.pop(), "b")
            self.assertEquals(rl.pop(), "a")

    def test_redis_set(self):
        "Test redis set."
        set_key = "%s.list" % self.prefix

        # ensure set isn't here
        rd = RedisDict()
        del rd[set_key]

        for class_impl in (RedisSet, PickleRedisSet, JSONRedisSet):
            rs = class_impl(set_key)
            self.assertEquals(len(rs), 0)
            rs.add("a")
            rs.add("a")
            rs.update(("a", "b"))
            self.assertEquals(len(rs), 2)
            self.assertTrue(rs.pop() in ("a", "b"))
            self.assertEquals(len(rs), 1)
            self.assertTrue(rs.pop() in ("a", "b"))
            self.assertEquals(len(rs), 0)




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
