__FILENAME__ = client
from __future__ import division
from collections import defaultdict
from itertools import chain
from datetime import datetime, timedelta
from hashlib import sha1
from operator import add
from random import choice, sample
import time
import re
import sys

from mockredis.clock import SystemClock
from mockredis.lock import MockRedisLock
from mockredis.exceptions import RedisError, ResponseError
from mockredis.pipeline import MockRedisPipeline
from mockredis.script import Script
from mockredis.sortedset import SortedSet

if sys.version_info >= (3, 0):
    long = int
    xrange = range
    basestring = str
    from functools import reduce


class MockRedis(object):
    """
    A Mock for a redis-py Redis object

    Expire functionality must be explicitly
    invoked using do_expire(time). Automatic
    expiry is NOT supported.
    """

    def __init__(self,
                 strict=False,
                 clock=None,
                 load_lua_dependencies=True,
                 blocking_timeout=1000,
                 blocking_sleep_interval=0.01,
                 **kwargs):
        """
        Initialize as either StrictRedis or Redis.

        Defaults to non-strict.
        """
        self.strict = strict
        self.clock = SystemClock() if clock is None else clock
        self.load_lua_dependencies = load_lua_dependencies
        self.blocking_timeout = blocking_timeout
        self.blocking_sleep_interval = blocking_sleep_interval
        # The 'Redis' store
        self.redis = defaultdict(dict)
        self.timeouts = defaultdict(dict)
        # The 'PubSub' store
        self.pubsub = defaultdict(list)
        # Dictionary from script to sha ''Script''
        self.shas = dict()

    #### Connection Functions ####

    def echo(self, msg):
        return msg

    def ping(self):
        return "PONG"

    #### Transactions Functions ####

    def lock(self, key, timeout=0, sleep=0):
        """Emulate lock."""
        return MockRedisLock(self, key, timeout, sleep)

    def pipeline(self, transaction=True, shard_hint=None):
        """Emulate a redis-python pipeline."""
        return MockRedisPipeline(self, transaction, shard_hint)

    def watch(self, *argv, **kwargs):
        """
        Mock does not support command buffering so watch
        is a no-op
        """
        pass

    def unwatch(self):
        """
        Mock does not support command buffering so unwatch
        is a no-op
        """
        pass

    def multi(self, *argv, **kwargs):
        """
        Mock does not support command buffering so multi
        is a no-op
        """
        pass

    def execute(self):
        """Emulate the execute method. All piped commands are executed immediately
        in this mock, so this is a no-op."""
        pass

    #### Keys Functions ####

    def type(self, key):
        if key not in self.redis:
            return 'none'
        type_ = type(self.redis[key])
        if type_ is dict:
            return 'hash'
        elif type_ is str:
            return 'string'
        elif type_ is set:
            return 'set'
        elif type_ is list:
            return 'list'
        elif type_ is SortedSet:
            return 'zset'
        raise TypeError("unhandled type {}".format(type_))

    def keys(self, pattern='*'):
        """Emulate keys."""
        # Make a regex out of pattern. The only special matching character we look for is '*'
        regex = '^' + pattern.replace('*', '.*') + '$'

        # Find every key that matches the pattern
        result = [key for key in self.redis.keys() if re.match(regex, key)]

        return result

    def delete(self, *keys):
        """Emulate delete."""
        key_counter = 0
        for key in map(str, keys):
            if key in self.redis:
                del self.redis[key]
                key_counter += 1
            if key in self.timeouts:
                del self.timeouts[key]
        return key_counter

    def __delitem__(self, name):
        if self.delete(name) == 0:
            # redispy doesn't correctly raise KeyError here, so we don't either
            pass

    def exists(self, key):
        """Emulate exists."""
        return key in self.redis
    __contains__ = exists

    def _expire(self, key, delta):
        if key not in self.redis:
            return False

        self.timeouts[key] = self.clock.now() + delta
        return True

    def expire(self, key, delta):
        """Emulate expire"""
        delta = delta if isinstance(delta, timedelta) else timedelta(seconds=delta)
        return self._expire(key, delta)

    def pexpire(self, key, milliseconds):
        """Emulate pexpire"""
        return self._expire(key, timedelta(milliseconds=milliseconds))

    def expireat(self, key, when):
        """Emulate expireat"""
        expire_time = datetime.fromtimestamp(when)
        if key in self.redis:
            self.timeouts[key] = expire_time
            return True
        return False

    def _time_to_live(self, key, output_ms):
        """
        Returns time to live in milliseconds if output_ms is True, else returns seconds.
        """
        if key not in self.redis:
            # as of redis 2.8, -2 returned if key does not exist
            return long(-2)
        if key not in self.timeouts:
            # redis-py returns None; command docs say -1
            return None

        get_result = get_total_milliseconds if output_ms else get_total_seconds
        time_to_live = get_result(self.timeouts[key] - self.clock.now())
        return long(max(-1, time_to_live))

    def ttl(self, key):
        """
        Emulate ttl

        Even though the official redis commands documentation at http://redis.io/commands/ttl
        states "Return value: Integer reply: TTL in seconds, -2 when key does not exist or -1
        when key does not have a timeout." the redis-py lib returns None for both these cases.
        The lib behavior has been emulated here.

        :param key: key for which ttl is requested.
        :returns: the number of seconds till timeout, None if the key does not exist or if the
                  key has no timeout(as per the redis-py lib behavior).
        """
        return self._time_to_live(key, output_ms=False)

    def pttl(self, key):
        """
        Emulate pttl

        :param key: key for which pttl is requested.
        :returns: the number of milliseconds till timeout, None if the key does not exist or if the
                  key has no timeout(as per the redis-py lib behavior).
        """
        return self._time_to_live(key, output_ms=True)

    def do_expire(self):
        """
        Expire objects assuming now == time
        """
        for key, value in self.timeouts.items():
            if value - self.clock.now() < timedelta(0):
                del self.timeouts[key]
                # removing the expired key
                if key in self.redis:
                    self.redis.pop(key, None)

    def flushdb(self):
        self.redis.clear()
        self.pubsub.clear()
        self.timeouts.clear()

    #### String Functions ####

    def get(self, key):

        # Override the default dict
        result = None if key not in self.redis else self.redis[key]
        return result

    def __getitem__(self, name):
        """
        Return the value at key ``name``, raises a KeyError if the key
        doesn't exist.
        """
        value = self.get(name)
        if value is not None:
            return value
        raise KeyError(name)

    def mget(self, keys, *args):
        args = self._list_or_args(keys, args)
        return [self.get(arg) for arg in args]

    def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        """
        Set the ``value`` for the ``key`` in the context of the provided kwargs.

        As per the behavior of the redis-py lib:
        If nx and xx are both set, the function does nothing and None is returned.
        If px and ex are both set, the preference is given to px.
        If the key is not set for some reason, the lib function returns None.
        """
        if nx and xx:
            return None
        mode = "nx" if nx else "xx" if xx else None
        if self._should_set(key, mode):
            expire = None
            if ex is not None:
                expire = ex if isinstance(ex, timedelta) else timedelta(seconds=ex)
            if px is not None:
                expire = px if isinstance(px, timedelta) else timedelta(milliseconds=px)

            if expire is not None and expire.total_seconds() <= 0:
                raise ResponseError("invalid expire time in SETEX")

            result = self._set(key, value)
            if expire:
                self._expire(key, expire)

            return result
    __setitem__ = set

    def getset(self, key, value):
        old_value = self.get(key)
        self.set(key, value)
        return old_value

    def _set(self, key, value):
        self.redis[key] = str(value)

        # removing the timeout
        if key in self.timeouts:
            self.timeouts.pop(key, None)

        return True

    def _should_set(self, key, mode):
        """
        Determine if it is okay to set a key.

        If the mode is None, returns True, otherwise, returns True of false based on
        the value of ``key`` and the ``mode`` (nx | xx).
        """

        if mode is None or mode not in ["nx", "xx"]:
            return True

        if mode == "nx":
            if key in self.redis:
                # nx means set only if key is absent
                # false if the key already exists
                return False
        elif key not in self.redis:
            # at this point mode can only be xx
            # xx means set only if the key already exists
            # false if is absent
            return False
        # for all other cases, return true
        return True

    def setex(self, key, time, value):
        """
        Set the value of ``key`` to ``value`` that expires in ``time``
        seconds. ``time`` can be represented by an integer or a Python
        timedelta object.
        """
        if not self.strict:
            # when not strict mode swap value and time args order
            time, value = value, time
        return self.set(key, value, ex=time)

    def psetex(self, key, time, value):
        """
        Set the value of ``key`` to ``value`` that expires in ``time``
        milliseconds. ``time`` can be represented by an integer or a Python
        timedelta object.
        """
        return self.set(key, value, px=time)

    def setnx(self, key, value):
        """Set the value of ``key`` to ``value`` if key doesn't exist"""
        return self.set(key, value, nx=True)

    def mset(self, *args, **kwargs):
        """
        Sets key/values based on a mapping. Mapping can be supplied as a single
        dictionary argument or as kwargs.
        """
        if args:
            if len(args) != 1 or not isinstance(args[0], dict):
                raise RedisError('MSET requires **kwargs or a single dict arg')
            mapping = args[0]
        else:
            mapping = kwargs
        for key, value in mapping.items():
            self.set(key, value)
        return True

    def msetnx(self, *args, **kwargs):
        """
        Sets key/values based on a mapping if none of the keys are already set.
        Mapping can be supplied as a single dictionary argument or as kwargs.
        Returns a boolean indicating if the operation was successful.
        """
        if args:
            if len(args) != 1 or not isinstance(args[0], dict):
                raise RedisError('MSETNX requires **kwargs or a single dict arg')
            mapping = args[0]
        else:
            mapping = kwargs

        for key, value in mapping.items():
            if key in self.redis:
                return False
        for key, value in mapping.items():
            self.set(key, value)

        return True

    def decr(self, key, amount=1):
        """Emulate decr."""
        previous_value = long(self.redis.get(key, '0'))
        self.redis[key] = str(previous_value - amount)
        return long(self.redis[key])

    def decrby(self, key, amount=1):
        return self.decr(key, amount)

    def incr(self, key, amount=1):
        """Emulate incr."""
        previous_value = long(self.redis.get(key, '0'))
        self.redis[key] = str(previous_value + amount)
        return long(self.redis[key])

    def incrby(self, key, amount=1):
        return self.incr(key, amount)

    #### Hash Functions ####

    def hexists(self, hashkey, attribute):
        """Emulate hexists."""

        redis_hash = self._get_hash(hashkey, 'HEXISTS')
        return str(attribute) in redis_hash

    def hget(self, hashkey, attribute):
        """Emulate hget."""

        redis_hash = self._get_hash(hashkey, 'HGET')
        return redis_hash.get(str(attribute))

    def hgetall(self, hashkey):
        """Emulate hgetall."""

        redis_hash = self._get_hash(hashkey, 'HGETALL')
        return dict(redis_hash)

    def hdel(self, hashkey, *keys):
        """Emulate hdel"""

        redis_hash = self._get_hash(hashkey, 'HDEL')
        count = 0
        for key in keys:
            attribute = str(key)
            if attribute in redis_hash:
                count += 1
                del redis_hash[attribute]
                if not redis_hash:
                    del self.redis[hashkey]
        return count

    def hlen(self, hashkey):
        """Emulate hlen."""
        redis_hash = self._get_hash(hashkey, 'HLEN')
        return len(redis_hash)

    def hmset(self, hashkey, value):
        """Emulate hmset."""

        redis_hash = self._get_hash(hashkey, 'HMSET', create=True)
        for key, value in value.items():
            attribute = str(key)
            redis_hash[attribute] = str(value)

    def hmget(self, hashkey, keys, *args):
        """Emulate hmget."""

        redis_hash = self._get_hash(hashkey, 'HMGET')
        attributes = self._list_or_args(keys, args)
        return [redis_hash.get(str(attribute)) for attribute in attributes]

    def hset(self, hashkey, attribute, value):
        """Emulate hset."""

        redis_hash = self._get_hash(hashkey, 'HSET', create=True)
        attribute = str(attribute)
        redis_hash[attribute] = str(value)

    def hsetnx(self, hashkey, attribute, value):
        """Emulate hsetnx."""

        redis_hash = self._get_hash(hashkey, 'HSETNX', create=True)
        attribute = str(attribute)
        if attribute in redis_hash:
            return 0
        else:
            redis_hash[attribute] = str(value)
            return 1

    def hincrby(self, hashkey, attribute, increment=1):
        """Emulate hincrby."""

        return self._hincrby(hashkey, attribute, 'HINCRBY', long, increment)

    def hincrbyfloat(self, hashkey, attribute, increment=1.0):
        """Emulate hincrbyfloat."""

        return self._hincrby(hashkey, attribute, 'HINCRBYFLOAT', float, increment)

    def _hincrby(self, hashkey, attribute, command, type_, increment):
        """Shared hincrby and hincrbyfloat routine"""
        redis_hash = self._get_hash(hashkey, command, create=True)
        attribute = str(attribute)
        previous_value = type_(redis_hash.get(attribute, '0'))
        redis_hash[attribute] = str(previous_value + increment)
        return type_(redis_hash[attribute])

    def hkeys(self, hashkey):
        """Emulate hkeys."""

        redis_hash = self._get_hash(hashkey, 'HKEYS')
        return redis_hash.keys()

    def hvals(self, hashkey):
        """Emulate hvals."""

        redis_hash = self._get_hash(hashkey, 'HVALS')
        return redis_hash.values()

    #### List Functions ####

    def lrange(self, key, start, stop):
        """Emulate lrange."""
        redis_list = self._get_list(key, 'LRANGE')
        start, stop = self._translate_range(len(redis_list), start, stop)
        return redis_list[start:stop + 1]

    def lindex(self, key, index):
        """Emulate lindex."""

        redis_list = self._get_list(key, 'LINDEX')

        if key not in self.redis:
            return None

        try:
            return redis_list[index]
        except (IndexError):
            # Redis returns nil if the index doesn't exist
            return None

    def llen(self, key):
        """Emulate llen."""
        redis_list = self._get_list(key, 'LLEN')

        # Redis returns 0 if list doesn't exist
        return len(redis_list)

    def _blocking_pop(self, pop_func, keys, timeout):
        """Emulate blocking pop functionality"""
        if not isinstance(timeout, (int, long)):
            raise RuntimeError('timeout is not an integer or out of range')

        if timeout is None or timeout == 0:
            timeout = self.blocking_timeout

        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)

        elapsed_time = 0
        start = time.time()
        while elapsed_time < timeout:
            key, val = self._pop_first_available(pop_func, keys)
            if val:
                return key, val
            # small delay to avoid high cpu utilization
            time.sleep(self.blocking_sleep_interval)
            elapsed_time = time.time() - start
        return None

    def _pop_first_available(self, pop_func, keys):
        for key in keys:
            val = pop_func(key)
            if val:
                return key, val
        return None, None

    def blpop(self, keys, timeout=0):
        """Emulate blpop"""
        return self._blocking_pop(self.lpop, keys, timeout)

    def brpop(self, keys, timeout=0):
        """Emulate brpop"""
        return self._blocking_pop(self.rpop, keys, timeout)

    def lpop(self, key):
        """Emulate lpop."""
        redis_list = self._get_list(key, 'LPOP')

        if key not in self.redis:
            return None

        try:
            value = str(redis_list.pop(0))
            if len(redis_list) == 0:
                del self.redis[key]
            return value
        except (IndexError):
            # Redis returns nil if popping from an empty list
            return None

    def lpush(self, key, *args):
        """Emulate lpush."""
        redis_list = self._get_list(key, 'LPUSH', create=True)

        # Creates the list at this key if it doesn't exist, and appends args to its beginning
        args_reversed = [str(arg) for arg in args]
        args_reversed.reverse()
        self.redis[key] = args_reversed + redis_list

    def rpop(self, key):
        """Emulate lpop."""
        redis_list = self._get_list(key, 'RPOP')

        if key not in self.redis:
            return None

        try:
            value = str(redis_list.pop())
            if len(redis_list) == 0:
                del self.redis[key]
            return value
        except (IndexError):
            # Redis returns nil if popping from an empty list
            return None

    def rpush(self, key, *args):
        """Emulate rpush."""
        redis_list = self._get_list(key, 'RPUSH', create=True)

        # Creates the list at this key if it doesn't exist, and appends args to it
        redis_list.extend(map(str, args))

    def lrem(self, key, value, count=0):
        """Emulate lrem."""
        key, value = str(key), str(value)
        redis_list = self._get_list(key, 'LREM')
        removed_count = 0
        if key in self.redis:
            if count == 0:
                # Remove all ocurrences
                while redis_list.count(value):
                    redis_list.remove(value)
                    removed_count += 1
            elif count > 0:
                counter = 0
                # remove first 'count' ocurrences
                while redis_list.count(value):
                    redis_list.remove(value)
                    counter += 1
                    removed_count += 1
                    if counter >= count:
                        break
            elif count < 0:
                # remove last 'count' ocurrences
                counter = -count
                new_list = []
                for v in reversed(redis_list):
                    if v == value and counter > 0:
                        counter -= 1
                        removed_count += 1
                    else:
                        new_list.append(v)
                self.redis[key] = list(reversed(new_list))
        if removed_count > 0 and len(redis_list) == 0:
            del self.redis[key]
        return removed_count

    def ltrim(self, key, start, stop):
        """Emulate ltrim."""
        redis_list = self._get_list(key, 'LTRIM')
        if redis_list:
            start, stop = self._translate_range(len(redis_list), start, stop)
            self.redis[key] = redis_list[start:stop + 1]
        return True

    def rpoplpush(self, source, destination):
        """Emulate rpoplpush"""
        transfer_item = self.rpop(source)
        if transfer_item is not None:
            self.lpush(destination, transfer_item)
        return transfer_item

    def brpoplpush(self, source, destination, timeout=0):
        """Emulate brpoplpush"""
        transfer_item = self.brpop(source, timeout)
        if transfer_item is None:
            return None

        key, val = transfer_item
        self.lpush(destination, val)
        return val

    def lset(self, key, index, value):
        """Emulate lset."""
        redis_list = self._get_list(key, 'LSET')
        if redis_list is None:
            raise ResponseError("no such key")
        try:
            redis_list[index] = value
        except IndexError:
            raise ResponseError("index out of range")

    def sort(self, name,
             start=None,
             num=None,
             by=None,
             get=None,
             desc=False,
             alpha=False,
             store=None,
             groups=False):
        # check valid parameter combos
        if [start, num] != [None, None] and None in [start, num]:
            raise ValueError('start and num must both be specified together')

        # check up-front if there's anything to actually do
        items = num != 0 and self.get(name)
        if not items:
            if store:
                return 0
            else:
                return []

        # always organize the items as tuples of the value from the list itself and the value to sort by
        if by and '*' in by:
            items = [(i, self.get(by.replace('*', str(i)))) for i in items]
        elif by in [None, 'nosort']:
            items = [(i, i) for i in items]
        else:
            raise ValueError('invalid value for "by": %s' % by)

        if by != 'nosort':
            # if sorting, do alpha sort or float (default) and take desc flag into account
            sort_type = alpha and str or float
            items.sort(key=lambda x: sort_type(x[1]), reverse=bool(desc))

        # results is a list of lists to support different styles of get and also groups
        results = []
        if get:
            if isinstance(get, basestring):
                # always deal with get specifiers as a list
                get = [get]
            for g in get:
                if g == '#':
                    results.append([self.get(i) for i in items])
                else:
                    results.append([self.get(g.replace('*', str(i[0]))) for i in items])
        else:
            # if not using GET then returning just the item itself
            results.append([i[0] for i in items])

        # results to either list of tuples or list of values
        if len(results) > 1:
            results = list(zip(*results))
        elif results:
            results = results[0]

        # apply the 'start' and 'num' to the results
        if not start:
            start = 0
        if not num:
            if start:
                results = results[start:]
        else:
            end = start + num
            results = results[start:end]

        # if more than one GET then flatten if groups not wanted
        if get and len(get) > 1:
            if not groups:
                results = list(chain(*results))

        # either store value and return length of results or just return results
        if store:
            self.redis[store] = results
            return len(results)
        else:
            return results

    #### SCAN COMMANDS ####

    def _common_scan(self, values_function, cursor='0', match=None, count=10, key=None):
        """
        Common scanning skeleton.

        :param key: optional function used to identify what 'match' is applied to
        """
        if count is None:
            count = 10
        cursor = int(cursor)
        count = int(count)
        if not count:
            raise ValueError('if specified, count must be > 0: %s' % count)

        values = values_function()
        if cursor + count >= len(values):
            # we reached the end, back to zero
            result_cursor = '0'
        else:
            result_cursor = str(cursor + count)

        values = values[cursor:cursor+count]

        if match is not None:
            regex = '^' + match.replace('*', '.*') + '$'
            if not key:
                key = lambda v: v
            values = filter(lambda v: re.match(regex, key(v)), values)

        return [result_cursor, values]

    def scan(self, cursor='0', match=None, count=10):
        """Emulate scan."""
        def value_function():
            return sorted(self.redis.keys())  # sorted list for consistent order
        return self._common_scan(value_function, cursor=cursor, match=match, count=count)

    def sscan(self, name, cursor='0', match=None, count=10):
        """Emulate sscan."""
        def value_function():
            members = list(self.smembers(name))
            members.sort()  # sort for consistent order
            return members
        return self._common_scan(value_function, cursor=cursor, match=match, count=count)

    def zscan(self, name, cursor='0', match=None, count=10):
        """Emulate zscan."""
        def value_function():
            values = self.zrange(name, 0, -1, withscores=True)
            values.sort(key=lambda x: x[1])  # sort for consistent order
            return values
        return self._common_scan(value_function, cursor=cursor, match=match, count=count, key=lambda v: v[0])

    def hscan(self, name, cursor='0', match=None, count=10):
        """Emulate hscan."""
        def value_function():
            values = self.hgetall(name)
            values = list(values.items())  # list of tuples for sorting and matching
            values.sort(key=lambda x: x[0])  # sort for consistent order
            return values
        scanned = self._common_scan(value_function, cursor=cursor, match=match, count=count, key=lambda v: v[0])
        scanned[1] = dict(scanned[1])  # from list of tuples back to dict
        return scanned

    #### SET COMMANDS ####

    def sadd(self, key, *values):
        """Emulate sadd."""
        redis_set = self._get_set(key, 'SADD', create=True)
        before_count = len(redis_set)
        redis_set.update(map(str, values))
        after_count = len(redis_set)
        return after_count - before_count

    def scard(self, key):
        """Emulate scard."""
        redis_set = self._get_set(key, 'SADD')
        return len(redis_set)

    def sdiff(self, keys, *args):
        """Emulate sdiff."""
        func = lambda left, right: left.difference(right)
        return self._apply_to_sets(func, "SDIFF", keys, *args)

    def sdiffstore(self, dest, keys, *args):
        """Emulate sdiffstore."""
        result = self.sdiff(keys, *args)
        self.redis[dest] = result
        return len(result)

    def sinter(self, keys, *args):
        """Emulate sinter."""
        func = lambda left, right: left.intersection(right)
        return self._apply_to_sets(func, "SINTER", keys, *args)

    def sinterstore(self, dest, keys, *args):
        """Emulate sinterstore."""
        result = self.sinter(keys, *args)
        self.redis[dest] = result
        return len(result)

    def sismember(self, name, value):
        """Emulate sismember."""
        redis_set = self._get_set(name, 'SISMEMBER')
        if not redis_set:
            return False
        return str(value) in redis_set

    def smembers(self, name):
        """Emulate smembers."""
        return self._get_set(name, 'SMEMBERS').copy()

    def smove(self, src, dst, value):
        """Emulate smove."""
        src_set = self._get_set(src, 'SMOVE')
        dst_set = self._get_set(dst, 'SMOVE')

        if value not in src_set:
            return False

        src_set.discard(value)
        dst_set.add(value)
        self.redis[src], self.redis[dst] = src_set, dst_set
        return True

    def spop(self, name):
        """Emulate spop."""
        redis_set = self._get_set(name, 'SPOP')
        if not redis_set:
            return None
        member = choice(list(redis_set))
        redis_set.remove(member)
        if len(redis_set) == 0:
            del self.redis[name]
        return member

    def srandmember(self, name, number=None):
        """Emulate srandmember."""
        redis_set = self._get_set(name, 'SRANDMEMBER')
        if not redis_set:
            return None if number is None else []
        if number is None:
            return choice(list(redis_set))
        elif number > 0:
            return sample(list(redis_set), min(number, len(redis_set)))
        else:
            return [choice(list(redis_set)) for _ in xrange(abs(number))]

    def srem(self, key, *values):
        """Emulate srem."""
        redis_set = self._get_set(key, 'SREM')
        if not redis_set:
            return 0
        before_count = len(redis_set)
        for value in values:
            redis_set.discard(str(value))
        after_count = len(redis_set)
        if before_count > 0 and len(redis_set) == 0:
            del self.redis[key]
        return before_count - after_count

    def sunion(self, keys, *args):
        """Emulate sunion."""
        func = lambda left, right: left.union(right)
        return self._apply_to_sets(func, "SUNION", keys, *args)

    def sunionstore(self, dest, keys, *args):
        """Emulate sunionstore."""
        result = self.sunion(keys, *args)
        self.redis[dest] = result
        return len(result)

    #### SORTED SET COMMANDS ####

    def zadd(self, name, *args, **kwargs):
        zset = self._get_zset(name, "ZADD", create=True)

        pieces = []

        # args
        if len(args) % 2 != 0:
            raise RedisError("ZADD requires an equal number of "
                             "values and scores")
        for i in xrange(len(args) // 2):
            # interpretation of args order depends on whether Redis
            # or StrictRedis is used
            score = args[2 * i + (0 if self.strict else 1)]
            member = args[2 * i + (1 if self.strict else 0)]
            pieces.append((member, score))

        # kwargs
        pieces.extend(kwargs.items())

        insert_count = lambda member, score: 1 if zset.insert(str(member), float(score)) else 0
        return sum((insert_count(member, score) for member, score in pieces))

    def zcard(self, name):
        zset = self._get_zset(name, "ZCARD")

        return len(zset) if zset is not None else 0

    def zcount(self, name, min_, max_):
        zset = self._get_zset(name, "ZCOUNT")

        if not zset:
            return 0

        return len(zset.scorerange(float(min_), float(max_)))

    def zincrby(self, name, value, amount=1):
        zset = self._get_zset(name, "ZINCRBY", create=True)

        value = str(value)
        score = zset.score(value) or 0.0
        score += float(amount)
        zset[value] = score
        return score

    def zinterstore(self, dest, keys, aggregate=None):
        aggregate_func = self._aggregate_func(aggregate)

        members = {}

        for key in keys:
            zset = self._get_zset(key, "ZINTERSTORE")
            if not zset:
                return 0

            for score, member in zset:
                members.setdefault(member, []).append(score)

        intersection = SortedSet()
        for member, scores in members.items():
            if len(scores) != len(keys):
                continue
            intersection[member] = reduce(aggregate_func, scores)

        # always override existing keys
        self.redis[dest] = intersection
        return len(intersection)

    def zrange(self, name, start, end, desc=False, withscores=False,
               score_cast_func=float):
        zset = self._get_zset(name, "ZRANGE")

        if not zset:
            return []

        start, end = self._translate_range(len(zset), start, end)

        func = self._range_func(withscores, score_cast_func)
        return [func(item) for item in zset.range(start, end, desc)]

    def zrangebyscore(self, name, min_, max_, start=None, num=None,
                      withscores=False, score_cast_func=float):
        if (start is None) ^ (num is None):
            raise RedisError('`start` and `num` must both be specified')

        zset = self._get_zset(name, "ZRANGEBYSCORE")

        if not zset:
            return []

        func = self._range_func(withscores, score_cast_func)

        scorerange = zset.scorerange(float(min_), float(max_))
        if start is not None and num is not None:
            start, num = self._translate_limit(len(scorerange), int(start), int(num))
            scorerange = scorerange[start:start + num]
        return [func(item) for item in scorerange]

    def zrank(self, name, value):
        zset = self._get_zset(name, "ZRANK")

        return zset.rank(value) if zset else None

    def zrem(self, name, *values):
        zset = self._get_zset(name, "ZREM")

        if not zset:
            return 0

        count_removals = lambda value: 1 if zset.remove(value) else 0
        removal_count = sum((count_removals(value) for value in values))
        if removal_count > 0 and len(zset) == 0:
            del self.redis[name]
        return removal_count

    def zremrangebyrank(self, name, start, end):
        zset = self._get_zset(name, "ZREMRANGEBYRANK")

        if not zset:
            return 0

        start, end = self._translate_range(len(zset), start, end)
        count_removals = lambda score, member: 1 if zset.remove(member) else 0
        removal_count = sum((count_removals(score, member) for score, member in zset.range(start, end)))
        if removal_count > 0 and len(zset) == 0:
            del self.redis[name]
        return removal_count

    def zremrangebyscore(self, name, min_, max_):
        zset = self._get_zset(name, "ZREMRANGEBYSCORE")

        if not zset:
            return 0

        count_removals = lambda score, member: 1 if zset.remove(member) else 0
        removal_count = sum((count_removals(score, member)
                             for score, member in zset.scorerange(float(min_), float(max_))))
        if removal_count > 0 and len(zset) == 0:
            del self.redis[name]
        return removal_count

    def zrevrange(self, name, start, end, withscores=False,
                  score_cast_func=float):
        return self.zrange(name, start, end,
                           desc=True, withscores=withscores, score_cast_func=score_cast_func)

    def zrevrangebyscore(self, name, max_, min_, start=None, num=None,
                         withscores=False, score_cast_func=float):

        if (start is None) ^ (num is None):
            raise RedisError('`start` and `num` must both be specified')

        zset = self._get_zset(name, "ZREVRANGEBYSCORE")
        if not zset:
            return []

        func = self._range_func(withscores, score_cast_func)

        scorerange = [x for x in reversed(zset.scorerange(float(min_), float(max_)))]
        if start is not None and num is not None:
            start, num = self._translate_limit(len(scorerange), int(start), int(num))
            scorerange = scorerange[start:start + num]
        return [func(item) for item in scorerange]

    def zrevrank(self, name, value):
        zset = self._get_zset(name, "ZREVRANK")

        if zset is None:
            return None

        return len(zset) - zset.rank(value) - 1

    def zscore(self, name, value):
        zset = self._get_zset(name, "ZSCORE")

        return zset.score(value) if zset is not None else None

    def zunionstore(self, dest, keys, aggregate=None):
        union = SortedSet()
        aggregate_func = self._aggregate_func(aggregate)

        for key in keys:
            zset = self._get_zset(key, "ZUNIONSTORE")
            if not zset:
                continue

            for score, member in zset:
                if member in union:
                    union[member] = aggregate_func(union[member], score)
                else:
                    union[member] = score

        # always override existing keys
        self.redis[dest] = union
        return len(union)

    #### Script Commands ####

    def eval(self, script, numkeys, *keys_and_args):
        """Emulate eval"""
        sha = self.script_load(script)
        return self.evalsha(sha, numkeys, *keys_and_args)

    def evalsha(self, sha, numkeys, *keys_and_args):
        """Emulates evalsha"""
        if not self.script_exists(sha)[0]:
            raise RedisError("Sha not registered")
        script_callable = Script(self, self.shas[sha], self.load_lua_dependencies)
        numkeys = max(numkeys, 0)
        keys = keys_and_args[:numkeys]
        args = keys_and_args[numkeys:]
        return script_callable(keys, args)

    def script_exists(self, *args):
        """Emulates script_exists"""
        return [arg in self.shas for arg in args]

    def script_flush(self):
        """Emulate script_flush"""
        self.shas.clear()

    def script_kill(self):
        """Emulate script_kill"""
        """XXX: To be implemented, should not be called before that."""
        raise NotImplementedError("Not yet implemented.")

    def script_load(self, script):
        """Emulate script_load"""
        sha_digest = sha1(script.encode("utf-8")).hexdigest()
        self.shas[sha_digest] = script
        return sha_digest

    def register_script(self, script):
        """Emulate register_script"""
        return Script(self, script, self.load_lua_dependencies)

    def call(self, command, *args):
        """
        Sends call to the function, whose name is specified by command.

        Used by Script invocations and normalizes calls using standard
        Redis arguments to use the expected redis-py arguments.
        """
        command = self._normalize_command_name(command)
        args = self._normalize_command_args(command, *args)

        redis_function = getattr(self, command)
        value = redis_function(*args)
        return self._normalize_command_response(command, value)

    def _normalize_command_name(self, command):
        """
        Modifies the command string to match the redis client method name.
        """
        command = command.lower()

        if command == 'del':
            return 'delete'

        return command

    def _normalize_command_args(self, command, *args):
        """
        Modifies the command arguments to match the
        strictness of the redis client.
        """
        if command == 'zadd' and not self.strict and len(args) >= 3:
            # Reorder score and name
            zadd_args = [x for tup in zip(args[2::2], args[1::2]) for x in tup]
            return [args[0]] + zadd_args

        if command in ('zrangebyscore', 'zrevrangebyscore'):
            # expected format is: <command> name min max start num with_scores score_cast_func
            if len(args) <= 3:
                # just plain min/max
                return args

            start, num = None, None
            withscores = False

            for i, arg in enumerate(args[3:], 3):
                # keywords are case-insensitive
                lower_arg = str(arg).lower()

                # handle "limit"
                if lower_arg == "limit" and i + 2 < len(args):
                    start, num = args[i + 1], args[i + 2]

                # handle "withscores"
                if lower_arg == "withscores":
                    withscores = True

            # do not expect to set score_cast_func

            return args[:3] + (start, num, withscores)

        return args

    def _normalize_command_response(self, command, response):
        if command in ('zrange', 'zrevrange', 'zrangebyscore', 'zrevrangebyscore'):
            if response and isinstance(response[0], tuple):
                return [value for tpl in response for value in tpl]

        return response

    #### PubSub commands ####

    def publish(self, channel, message):
        self.pubsub[channel].append(message)

    #### Internal ####

    def _get_list(self, key, operation, create=False):
        """
        Get (and maybe create) a list by name.
        """
        return self._get_by_type(key, operation, create, 'list', [])

    def _get_set(self, key, operation, create=False):
        """
        Get (and maybe create) a set by name.
        """
        return self._get_by_type(key, operation, create, 'set', set())

    def _get_hash(self, name, operation, create=False):
        """
        Get (and maybe create) a hash by name.
        """
        return self._get_by_type(name, operation, create, 'hash', {})

    def _get_zset(self, name, operation, create=False):
        """
        Get (and maybe create) a sorted set by name.
        """
        return self._get_by_type(name, operation, create, 'zset', SortedSet(), return_default=False)

    def _get_by_type(self, key, operation, create, type_, default, return_default=True):
        """
        Get (and maybe create) a redis data structure by name and type.
        """
        key = str(key)
        if self.type(key) in [type_, 'none']:
            if create:
                return self.redis.setdefault(key, default)
            else:
                return self.redis.get(key, default if return_default else None)

        raise TypeError("{} requires a {}".format(operation, type_))

    def _translate_range(self, len_, start, end):
        """
        Translate range to valid bounds.
        """
        if start < 0:
            start += len_
        start = max(0, min(start, len_))
        if end < 0:
            end += len_
        end = max(-1, min(end, len_ - 1))
        return start, end

    def _translate_limit(self, len_, start, num):
        """
        Translate limit to valid bounds.
        """
        if start > len_ or num <= 0:
            return 0, 0
        return min(start, len_), num

    def _range_func(self, withscores, score_cast_func):
        """
        Return a suitable function from (score, member)
        """
        if withscores:
            return lambda score_member: (score_member[1], score_cast_func(str(score_member[0])))
        else:
            return lambda score_member: score_member[1]

    def _aggregate_func(self, aggregate):
        """
        Return a suitable aggregate score function.
        """
        funcs = {"sum": add, "min": min, "max": max}
        func_name = aggregate.lower() if aggregate else 'sum'
        try:
            return funcs[func_name]
        except KeyError:
            raise TypeError("Unsupported aggregate: {}".format(aggregate))

    def _apply_to_sets(self, func, operation, keys, *args):
        """Helper function for sdiff, sinter, and sunion"""
        keys = self._list_or_args(keys, args)
        if not keys:
            raise TypeError("{} takes at least two arguments".format(operation.lower()))
        left = self._get_set(keys[0], operation) or set()
        for key in keys[1:]:
            right = self._get_set(key, operation) or set()
            left = func(left, right)
        return left

    def _list_or_args(self, keys, args):
        """
        Shamelessly copied from redis-py.
        """
        # returns a single list combining keys and args
        try:
            iter(keys)
            # a string can be iterated, but indicates
            # keys wasn't passed as a list
            if isinstance(keys, basestring):
                keys = [keys]
        except TypeError:
            keys = [keys]
        if args:
            keys.extend(args)
        return keys


def get_total_seconds(td):
    """
    For python 2.6 support
    """
    return int((td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) // 1e6)


def get_total_milliseconds(td):
    return int((td.days * 24 * 60 * 60 + td.seconds) * 1000 + td.microseconds / 1000.0)


def mock_redis_client(**kwargs):
    """
    Mock common.util.redis_client so we
    can return a MockRedis object
    instead of a Redis object.
    """
    return MockRedis()


def mock_strict_redis_client(**kwargs):
    """
    Mock common.util.redis_client so we
    can return a MockRedis object
    instead of a StrictRedis object.
    """
    return MockRedis(strict=True)

########NEW FILE########
__FILENAME__ = clock
"""
Simple clock abstraction.
"""
from abc import ABCMeta, abstractmethod
from datetime import datetime


class Clock(object):
    """
    A clock knows the current time.

    Clock can be subclassed for testing scenarios that need to control for time.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def now(self):
        pass


class SystemClock(Clock):

    def now(self):
        return datetime.now()

########NEW FILE########
__FILENAME__ = exceptions
"""
Emulates exceptions raised by the Redis client.
"""


class RedisError(Exception):
    pass


class ResponseError(Exception):
    pass


class WatchError(Exception):
    pass

########NEW FILE########
__FILENAME__ = lock
class MockRedisLock(object):
    """
    Poorly imitate a Redis lock object from redis-py
    to allow testing without a real redis server.
    """

    def __init__(self, redis, name, timeout=None, sleep=0.1):
        """Initialize the object."""

        self.redis = redis
        self.name = name
        self.acquired_until = None
        self.timeout = timeout
        self.sleep = sleep

    def acquire(self, blocking=True):  # pylint: disable=R0201,W0613
        """Emulate acquire."""

        return True

    def release(self):   # pylint: disable=R0201
        """Emulate release."""

        return

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

########NEW FILE########
__FILENAME__ = noseplugin
"""
This module includes a nose plugin that allows unit tests to be run with a real
redis-server instance running locally (assuming redis-py) is installed. This provides
a simple way to verify that mockredis tests are accurate (at least for a particular
version of redis-server and redis-py).

For this plugin to work, several things need to be true:

 1. Nose and setuptools need to be used to invoke tests (so the plugin will work).

    Note that the setuptools "entry_point" for "nose.plugins.0.10" must be activated.

 2. A version of redis-py must be installed in the virtualenv under test.

 3. A redis-server instance must be running locally.

 4. The redis-server must have a database that can be flushed between tests.

    YOU WILL LOSE DATA OTHERWISE.

    By default, database 15 is used.

 5. Tests must be written without any references to internal mockredis state. Essentially,
    that means testing GET and SET together instead of separately and not looking at the contents
    of `self.redis.redis` (because this won't exist for redis-py).
"""
from functools import partial
import os

from nose.plugins import Plugin

from mockredis import MockRedis


class WithRedis(Plugin):
    """
    Nose plugin to allow selection of redis-server.
    """
    def options(self, parser, env=os.environ):
        parser.add_option("--use-redis",
                          dest="use_redis",
                          action="store_true",
                          default=False,
                          help="Use a local redis instance to validate tests.")
        parser.add_option("--redis-database",
                          dest="redis_database",
                          default=15,
                          help="Run tests against local redis database")

    def configure(self, options, conf):
        if options.use_redis:
            from redis import Redis, RedisError, ResponseError, StrictRedis, WatchError

            WithRedis.Redis = partial(Redis, db=options.redis_database)
            WithRedis.StrictRedis = partial(StrictRedis, db=options.redis_database)
            WithRedis.ResponseError = ResponseError
            WithRedis.RedisError = RedisError
            WithRedis.WatchError = WatchError
        else:
            from mockredis.exceptions import RedisError, ResponseError, WatchError

            WithRedis.Redis = MockRedis
            WithRedis.StrictRedis = partial(MockRedis, strict=True)
            WithRedis.ResponseError = ResponseError
            WithRedis.RedisError = RedisError
            WithRedis.WatchError = WatchError

########NEW FILE########
__FILENAME__ = pipeline
from copy import deepcopy

from mockredis.exceptions import RedisError, WatchError


class MockRedisPipeline(object):
    """
    Simulates a redis-python pipeline object.
    """

    def __init__(self, mock_redis, transaction=True, shard_hint=None):
        self.mock_redis = mock_redis
        self._reset()

    def __getattr__(self, name):
        """
        Handle all unfound attributes by adding a deferred function call that
        delegates to the underlying mock redis instance.
        """
        command = getattr(self.mock_redis, name)
        if not callable(command):
            raise AttributeError(name)

        def wrapper(*args, **kwargs):
            if self.watching and not self.explicit_transaction:
                # execute the command immediately
                return command(*args, **kwargs)
            else:
                self.commands.append(lambda: command(*args, **kwargs))
                return self
        return wrapper

    def watch(self, *keys):
        """
        Put the pipeline into immediate execution mode.
        Does not actually watch any keys.
        """
        if self.explicit_transaction:
            raise RedisError("Cannot issue a WATCH after a MULTI")
        self.watching = True
        for key in keys:
            self._watched_keys[key] = deepcopy(self.mock_redis.redis.get(key))

    def multi(self):
        """
        Start a transactional block of the pipeline after WATCH commands
        are issued. End the transactional block with `execute`.
        """
        if self.explicit_transaction:
            raise RedisError("Cannot issue nested calls to MULTI")
        if self.commands:
            raise RedisError("Commands without an initial WATCH have already been issued")
        self.explicit_transaction = True

    def execute(self):
        """
        Execute all of the saved commands and return results.
        """
        try:
            for key, value in self._watched_keys.items():
                if self.mock_redis.redis.get(key) != value:
                    raise WatchError("Watched variable changed.")
            return [command() for command in self.commands]
        finally:
            self._reset()

    def _reset(self):
        """
        Reset instance variables.
        """
        self.commands = []
        self.watching = False
        self._watched_keys = {}
        self.explicit_transaction = False

    def __exit__(self, *argv, **kwargs):
        pass

    def __enter__(self, *argv, **kwargs):
        return self

########NEW FILE########
__FILENAME__ = script
class Script(object):
    """
    An executable Lua script object returned by ``MockRedis.register_script``.
    """

    def __init__(self, registered_client, script, load_dependencies=True):
        self.registered_client = registered_client
        self.script = script
        self.load_dependencies = load_dependencies
        self.sha = registered_client.script_load(script)

    def __call__(self, keys=[], args=[], client=None):
        """Execute the script, passing any required ``args``"""
        client = client or self.registered_client

        if not client.script_exists(self.sha)[0]:
            self.sha = client.script_load(self.script)

        return self._execute_lua(keys, args, client)

    def _execute_lua(self, keys, args, client):
        """
        Sets KEYS and ARGV alongwith redis.call() function in lua globals
        and executes the lua redis script
        """
        lua, lua_globals = Script._import_lua(self.load_dependencies)
        lua_globals.KEYS = self._python_to_lua(keys)
        lua_globals.ARGV = self._python_to_lua(args)

        def _call(*call_args):
            response = client.call(*call_args)
            return self._python_to_lua(response)

        lua_globals.redis = {"call": _call}
        return self._lua_to_python(lua.execute(self.script))

    @staticmethod
    def _import_lua(load_dependencies=True):
        """
        Import lua and dependencies.

        :param load_dependencies: should Lua library dependencies be loaded?
        :raises: RuntimeError if Lua is not available
        """
        try:
            import lua
        except ImportError:
            raise RuntimeError("Lua not installed")

        lua_globals = lua.globals()
        if load_dependencies:
            Script._import_lua_dependencies(lua, lua_globals)
        return lua, lua_globals

    @staticmethod
    def _import_lua_dependencies(lua, lua_globals):
        """
        Imports lua dependencies that are supported by redis lua scripts.

        The current implementation is fragile to the target platform and lua version
        and may be disabled if these imports are not needed.

        Included:
            - cjson lib.
        Pending:
            - base lib.
            - table lib.
            - string lib.
            - math lib.
            - debug lib.
            - cmsgpack lib.
        """
        import ctypes
        ctypes.CDLL('liblua5.2.so', mode=ctypes.RTLD_GLOBAL)

        try:
            lua_globals.cjson = lua.eval('require "cjson"')
        except RuntimeError:
            raise RuntimeError("cjson not installed")

    @staticmethod
    def _lua_to_python(lval):
        """
        Convert Lua object(s) into Python object(s), as at times Lua object(s)
        are not compatible with Python functions
        """
        import lua
        lua_globals = lua.globals()
        if lval is None:
            # Lua None --> Python None
            return None
        if lua_globals.type(lval) == "table":
            # Lua table --> Python list
            pval = []
            for i in lval:
                pval.append(Script._lua_to_python(lval[i]))
            return pval
        elif isinstance(lval, long):
            # Lua number --> Python long
            return long(lval)
        elif isinstance(lval, float):
            # Lua number --> Python float
            return float(lval)
        elif lua_globals.type(lval) == "userdata":
            # Lua userdata --> Python string
            return str(lval)
        elif lua_globals.type(lval) == "string":
            # Lua string --> Python string
            return lval
        elif lua_globals.type(lval) == "boolean":
            # Lua boolean --> Python bool
            return bool(lval)
        raise RuntimeError("Invalid Lua type: " + str(lua_globals.type(lval)))

    @staticmethod
    def _python_to_lua(pval):
        """
        Convert Python object(s) into Lua object(s), as at times Python object(s)
        are not compatible with Lua functions
        """
        import lua
        if pval is None:
            # Python None --> Lua None
            return lua.eval("")
        if isinstance(pval, (list, tuple, set)):
            # Python list --> Lua table
            # e.g.: in lrange
            #     in Python returns: [v1, v2, v3]
            #     in Lua returns: {v1, v2, v3}
            lua_list = lua.eval("{}")
            lua_table = lua.eval("table")
            for item in pval:
                lua_table.insert(lua_list, Script._python_to_lua(item))
            return lua_list
        elif isinstance(pval, dict):
            # Python dict --> Lua dict
            # e.g.: in hgetall
            #     in Python returns: {k1:v1, k2:v2, k3:v3}
            #     in Lua returns: {k1, v1, k2, v2, k3, v3}
            lua_dict = lua.eval("{}")
            lua_table = lua.eval("table")
            for k, v in pval.iteritems():
                lua_table.insert(lua_dict, Script._python_to_lua(k))
                lua_table.insert(lua_dict, Script._python_to_lua(v))
            return lua_dict
        elif isinstance(pval, str):
            # Python string --> Lua userdata
            return pval
        elif isinstance(pval, bool):
            # Python bool--> Lua boolean
            return lua.eval(str(pval).lower())
        elif isinstance(pval, (int, long, float)):
            # Python int --> Lua number
            lua_globals = lua.globals()
            return lua_globals.tonumber(str(pval))

        raise RuntimeError("Invalid Python type: " + str(type(pval)))

########NEW FILE########
__FILENAME__ = sortedset
from bisect import bisect_left, bisect_right


class SortedSet(object):
    """
    Redis-style SortedSet implementation.

    Maintains two internal data structures:

    1. A multimap from score to member
    2. A dictionary from member to score.

    The multimap is implemented using a sorted list of (score, member) pairs. The bisect operations
    used to maintain the multimap are O(log N), but insertion into and removal from a list are O(N),
    so insertion and removal O(N). It should be possible to swap in an indexable skip list to get
    the expected O(log N) behavior.
    """
    def __init__(self):
        """
        Create an empty sorted set.
        """
        # sorted list of (score, member)
        self._scores = []
        # dictionary from member to score
        self._members = {}

    def clear(self):
        """
        Remove all members and scores from the sorted set.
        """
        self.__init__()

    def __len__(self):
        return len(self._members)

    def __contains__(self, member):
        return str(member) in self._members

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "SortedSet({})".format(self._scores)

    def __eq__(self, other):
        return self._scores == other._scores and self._members == other._members

    def __ne__(self, other):
        return not self == other

    def __setitem__(self, member, score):
        """
        Insert member with score. If member is already present in the
        set, update its score.
        """
        self.insert(member, score)

    def __delitem__(self, member):
        """
        Remove member from the set.
        """
        self.remove(member)

    def __getitem__(self, member):
        """
        Get the score for a member.
        """
        if isinstance(member, slice):
            raise TypeError("Slicing not supported")
        return self._members[member]

    def __iter__(self):
        return self._scores.__iter__()

    def __reversed__(self):
        return self._scores.__reversed__()

    def insert(self, member, score):
        """
        Identical to __setitem__, but returns whether a member was
        inserted (True) or updated (False)
        """
        found = self.remove(member)
        index = bisect_left(self._scores, (score, member))
        self._scores.insert(index, (score, member))
        self._members[member] = score
        return not found

    def remove(self, member):
        """
        Identical to __delitem__, but returns whether a member was removed.
        """
        member = str(member)
        if member not in self:
            return False
        score = self._members[member]
        score_index = bisect_left(self._scores, (score, member))
        del self._scores[score_index]
        del self._members[member]
        return True

    def score(self, member):
        """
        Identical to __getitem__, but returns None instead of raising
        KeyError if member is not found.
        """
        return self._members.get(str(member))

    def rank(self, member):
        """
        Get the rank (index of a member).
        """
        member = str(member)
        score = self._members.get(member)
        if score is None:
            return None
        return bisect_left(self._scores, (score, member))

    def range(self, start, end, desc=False):
        """
        Return (score, member) pairs between min and max ranks.
        """
        if not self:
            return []

        if desc:
            return reversed(self._scores[len(self) - end - 1:len(self) - start])
        else:
            return self._scores[start:end + 1]

    def scorerange(self, start, end):
        """
        Return (score, member) pairs between min and max scores.
        """
        if not self:
            return []

        left = bisect_left(self._scores, (start,))
        right = bisect_right(self._scores, (end,))

        # end is inclusive
        while right < len(self) and self._scores[right][0] == end:
            right += 1

        return self._scores[left:right]

    def min_score(self):
        return self._scores[0][0]

    def max_score(self):
        return self._scores[-1][0]

########NEW FILE########
__FILENAME__ = fixtures
"""
Test fixtures for mockredis using the WithRedis plugin.
"""
from contextlib import contextmanager

from nose.tools import assert_raises, raises

from mockredis.noseplugin import WithRedis


def setup(self):
    """
    Test setup fixtures. Creates and flushes redis/strict redis instances.
    """
    self.redis = WithRedis.Redis()
    self.redis_strict = WithRedis.StrictRedis()
    self.redis.flushdb()
    self.redis_strict.flushdb()


def raises_response_error(func):
    """
    Test decorator that handles ResponseError or its mock equivalent
    (currently ValueError).

    mockredis does not currently raise redis-py's exceptions because it
    does not current depend on redis-py strictly.
    """
    return raises(WithRedis.ResponseError)(func)


@contextmanager
def assert_raises_redis_error():
    """
    Test context manager that asserts that a RedisError or its mock equivalent
    (currently `redis.exceptions.RedisError`) were raised.

    mockredis does not currently raise redis-py's exceptions because it
    does not current depend on redis-py strictly.
    """
    with assert_raises(WithRedis.RedisError) as capture:
        yield capture


@contextmanager
def assert_raises_watch_error():
    """
    Test context manager that asserts that a WatchError or its mock equivalent
    (currently `watch.exceptions.WatchError`) were raised.

    mockwatch does not currently raise watch-py's exceptions because it
    does not current depend on watch-py strictly.
    """
    with assert_raises(WithRedis.WatchError) as capture:
        yield capture

########NEW FILE########
__FILENAME__ = test_constants
LIST1 = "test_list_1"
LIST2 = "test_list_2"

SET1 = "test_set_1"
SET2 = "test_set_2"

VAL1 = "val1"
VAL2 = "val2"
VAL3 = "val3"
VAL4 = "val4"

LPOP_SCRIPT = "return redis.call('LPOP', KEYS[1])"

########NEW FILE########
__FILENAME__ = test_factories
"""
Test redis client factory functions.
"""
from nose.tools import ok_

from mockredis import mock_redis_client, mock_strict_redis_client


def test_mock_redis_client():
    """
    Test that we can pass kwargs to the Redis mock/patch target.
    """
    ok_(not mock_redis_client(host="localhost", port=6379).strict)


def test_mock_strict_redis_client():
    """
    Test that we can pass kwargs to the StrictRedis mock/patch target.
    """
    ok_(mock_strict_redis_client(host="localhost", port=6379).strict)

########NEW FILE########
__FILENAME__ = test_hash
from nose.tools import eq_, ok_

from mockredis.tests.fixtures import setup


class TestRedisHash(object):
    """hash tests"""

    def setup(self):
        setup(self)

    def test_hexists(self):
        hashkey = "hash"
        ok_(not self.redis.hexists(hashkey, "key"))
        self.redis.hset(hashkey, "key", "value")
        ok_(self.redis.hexists(hashkey, "key"))
        ok_(not self.redis.hexists(hashkey, "key2"))

    def test_hgetall(self):
        hashkey = "hash"
        eq_({}, self.redis.hgetall(hashkey))
        self.redis.hset(hashkey, "key", "value")
        eq_({"key": "value"}, self.redis.hgetall(hashkey))

    def test_hdel(self):
        hashkey = "hash"
        self.redis.hmset(hashkey, {1: 1, 2: 2, 3: 3})
        eq_(0, self.redis.hdel(hashkey, "foo"))
        eq_({"1": "1", "2": "2", "3": "3"}, self.redis.hgetall(hashkey))
        eq_(2, self.redis.hdel(hashkey, "1", 2))
        eq_({"3": "3"}, self.redis.hgetall(hashkey))
        eq_(1, self.redis.hdel(hashkey, "3", 4))
        eq_({}, self.redis.hgetall(hashkey))
        ok_(not self.redis.exists(hashkey))
        eq_([], self.redis.keys("*"))

    def test_hlen(self):
        hashkey = "hash"
        eq_(0, self.redis.hlen(hashkey))
        self.redis.hset(hashkey, "key", "value")
        eq_(1, self.redis.hlen(hashkey))

    def test_hset(self):
        hashkey = "hash"
        self.redis.hset(hashkey, "key", "value")
        eq_("value", self.redis.hget(hashkey, "key"))

    def test_hget(self):
        hashkey = "hash"
        eq_(None, self.redis.hget(hashkey, "key"))

    def test_hset_integral(self):
        hashkey = "hash"
        self.redis.hset(hashkey, 1, 2)
        eq_("2", self.redis.hget(hashkey, 1))
        eq_("2", self.redis.hget(hashkey, "1"))

    def test_hsetnx(self):
        hashkey = "hash"
        eq_(1, self.redis.hsetnx(hashkey, "key", "value1"))
        eq_("value1", self.redis.hget(hashkey, "key"))
        eq_(0, self.redis.hsetnx(hashkey, "key", "value2"))
        eq_("value1", self.redis.hget(hashkey, "key"))

    def test_hmset(self):
        hashkey = "hash"
        self.redis.hmset(hashkey, {"key1": "value1", "key2": "value2"})
        eq_("value1", self.redis.hget(hashkey, "key1"))
        eq_("value2", self.redis.hget(hashkey, "key2"))

    def test_hmset_integral(self):
        hashkey = "hash"
        self.redis.hmset(hashkey, {1: 2, 3: 4})
        eq_("2", self.redis.hget(hashkey, "1"))
        eq_("2", self.redis.hget(hashkey, 1))
        eq_("4", self.redis.hget(hashkey, "3"))
        eq_("4", self.redis.hget(hashkey, 3))

    def test_hmget(self):
        hashkey = "hash"
        self.redis.hmset(hashkey, {1: 2, 3: 4})
        eq_(["2", None, "4"], self.redis.hmget(hashkey, "1", "2", "3"))
        eq_(["2", None, "4"], self.redis.hmget(hashkey, ["1", "2", "3"]))
        eq_(["2", None, "4"], self.redis.hmget(hashkey, [1, 2, 3]))

    def test_hincrby(self):
        hashkey = "hash"
        eq_(1, self.redis.hincrby(hashkey, "key", 1))
        eq_(3, self.redis.hincrby(hashkey, "key", 2))
        eq_("3", self.redis.hget(hashkey, "key"))

    def test_hincrbyfloat(self):
        hashkey = "hash"
        eq_(1.2, self.redis.hincrbyfloat(hashkey, "key", 1.2))
        eq_(3.5, self.redis.hincrbyfloat(hashkey, "key", 2.3))
        eq_("3.5", self.redis.hget(hashkey, "key"))

    def test_hkeys(self):
        hashkey = "hash"
        self.redis.hmset(hashkey, {1: 2, 3: 4})
        eq_(["1", "3"], sorted(self.redis.hkeys(hashkey)))

    def test_hvals(self):
        hashkey = "hash"
        self.redis.hmset(hashkey, {1: 2, 3: 4})
        eq_(["2", "4"], sorted(self.redis.hvals(hashkey)))

########NEW FILE########
__FILENAME__ = test_list
import time

from nose.tools import assert_raises, eq_

from mockredis.tests.fixtures import setup
from mockredis.tests.test_constants import (
    LIST1, LIST2, VAL1, VAL2, VAL3, VAL4
)


class TestRedisList(object):
    """list tests"""

    def setup(self):
        setup(self)

    def test_initially_empty(self):
        """
        List is created empty.
        """
        eq_(0, len(self.redis.lrange(LIST1, 0, -1)))

    def test_llen(self):
        eq_(0, self.redis.llen(LIST1))
        self.redis.lpush(LIST1, VAL1, VAL2)
        eq_(2, self.redis.llen(LIST1))
        self.redis.lpop(LIST1)
        eq_(1, self.redis.llen(LIST1))
        self.redis.lpop(LIST1)
        eq_(0, self.redis.llen(LIST1))

    def test_lindex(self):
        eq_(None, self.redis.lindex(LIST1, 0))
        eq_(False, self.redis.exists(LIST1))
        self.redis.rpush(LIST1, VAL1, VAL2)
        eq_(VAL1, self.redis.lindex(LIST1, 0))
        eq_(VAL2, self.redis.lindex(LIST1, 1))
        eq_(None, self.redis.lindex(LIST1, 2))
        eq_(VAL2, self.redis.lindex(LIST1, -1))
        eq_(VAL1, self.redis.lindex(LIST1, -2))
        eq_(None, self.redis.lindex(LIST1, -3))
        self.redis.lpop(LIST1)
        eq_(VAL2, self.redis.lindex(LIST1, 0))
        eq_(None, self.redis.lindex(LIST1, 1))

    def test_lpop(self):
        self.redis.rpush(LIST1, VAL1, VAL2)
        eq_(VAL1, self.redis.lpop(LIST1))
        eq_(1, len(self.redis.lrange(LIST1, 0, -1)))
        eq_(VAL2, self.redis.lpop(LIST1))
        eq_(0, len(self.redis.lrange(LIST1, 0, -1)))
        eq_(None, self.redis.lpop(LIST1))
        eq_([], self.redis.keys("*"))

    def test_blpop(self):
        self.redis.rpush(LIST1, VAL1, VAL2)
        eq_((LIST1, VAL1), self.redis.blpop((LIST1, LIST2)))
        eq_(1, len(self.redis.lrange(LIST1, 0, -1)))
        eq_((LIST1, VAL2), self.redis.blpop(LIST1))
        eq_(0, len(self.redis.lrange(LIST1, 0, -1)))
        timeout = 1
        start = time.time()
        eq_(None, self.redis.blpop(LIST1, timeout))
        eq_(timeout, int(time.time() - start))
        eq_([], self.redis.keys("*"))

    def test_lpush(self):
        """
        Insertion maintains order but not uniqueness.
        """
        # lpush two values
        self.redis.lpush(LIST1, VAL1)
        self.redis.lpush(LIST1, VAL2)

        # validate insertion
        eq_("list", self.redis.type(LIST1))
        eq_([VAL2, VAL1], self.redis.lrange(LIST1, 0, -1))

        # insert two more values with one repeated
        self.redis.lpush(LIST1, VAL1, VAL3)

        # validate the update
        eq_("list", self.redis.type(LIST1))
        eq_([VAL3, VAL1, VAL2, VAL1], self.redis.lrange(LIST1, 0, -1))

    def test_rpop(self):
        self.redis.rpush(LIST1, VAL1, VAL2)
        eq_(VAL2, self.redis.rpop(LIST1))
        eq_(1, len(self.redis.lrange(LIST1, 0, -1)))
        eq_(VAL1, self.redis.rpop(LIST1))
        eq_(0, len(self.redis.lrange(LIST1, 0, -1)))
        eq_(None, self.redis.rpop(LIST1))
        eq_([], self.redis.keys("*"))

    def test_brpop(self):
        self.redis.rpush(LIST1, VAL1, VAL2)
        eq_((LIST1, VAL2), self.redis.brpop((LIST2, LIST1)))
        eq_(1, len(self.redis.lrange(LIST1, 0, -1)))
        eq_((LIST1, VAL1), self.redis.brpop(LIST1))
        eq_(0, len(self.redis.lrange(LIST1, 0, -1)))
        timeout = 1
        start = time.time()
        eq_(None, self.redis.brpop(LIST1, timeout))
        eq_(timeout, int(time.time() - start))
        eq_([], self.redis.keys("*"))

    def test_rpush(self):
        """
        Insertion maintains order but not uniqueness.
        """
        # lpush two values
        self.redis.rpush(LIST1, VAL1)
        self.redis.rpush(LIST1, VAL2)

        # validate insertion
        eq_("list", self.redis.type(LIST1))
        eq_([VAL1, VAL2], self.redis.lrange(LIST1, 0, -1))

        # insert two more values with one repeated
        self.redis.rpush(LIST1, VAL1, VAL3)

        # validate the update
        eq_("list", self.redis.type(LIST1))
        eq_([VAL1, VAL2, VAL1, VAL3], self.redis.lrange(LIST1, 0, -1))

    def test_lrem(self):
        self.redis.rpush(LIST1, VAL1, VAL2, VAL1, VAL3, VAL4, VAL2)
        eq_(2, self.redis.lrem(LIST1, VAL1, 0))
        eq_([VAL2, VAL3, VAL4, VAL2], self.redis.lrange(LIST1, 0, -1))

        del self.redis[LIST1]
        self.redis.rpush(LIST1, VAL1, VAL2, VAL1, VAL3, VAL4, VAL2)
        eq_(1, self.redis.lrem(LIST1, VAL2, 1))
        eq_([VAL1, VAL1, VAL3, VAL4, VAL2], self.redis.lrange(LIST1, 0, -1))

        del self.redis[LIST1]
        self.redis.rpush(LIST1, VAL1, VAL2, VAL1, VAL3, VAL4, VAL2)
        eq_(2, self.redis.lrem(LIST1, VAL1, 100))
        eq_([VAL2, VAL3, VAL4, VAL2], self.redis.lrange(LIST1, 0, -1))

        del self.redis[LIST1]
        self.redis.rpush(LIST1, VAL1, VAL2, VAL1, VAL3, VAL4, VAL2)
        eq_(1, self.redis.lrem(LIST1, VAL3, -1))
        eq_([VAL1, VAL2, VAL1, VAL4, VAL2], self.redis.lrange(LIST1, 0, -1))

        del self.redis[LIST1]
        self.redis.rpush(LIST1, VAL1, VAL2, VAL1, VAL3, VAL4, VAL2)
        eq_(1, self.redis.lrem(LIST1, VAL2, -1))
        eq_([VAL1, VAL2, VAL1, VAL3, VAL4], self.redis.lrange(LIST1, 0, -1))

        del self.redis[LIST1]
        self.redis.rpush(LIST1, VAL1, VAL2, VAL1, VAL3, VAL4, VAL2)
        eq_(2, self.redis.lrem(LIST1, VAL2, -2))
        eq_([VAL1, VAL1, VAL3, VAL4], self.redis.lrange(LIST1, 0, -1))

        # string conversion
        self.redis.rpush(1, 1, "2", 3)
        eq_(1, self.redis.lrem(1, "1"))
        eq_(1, self.redis.lrem("1", 2))
        eq_(["3"], self.redis.lrange(1, 0, -1))
        del self.redis["1"]

        del self.redis[LIST1]
        self.redis.rpush(LIST1, VAL1)
        eq_(1, self.redis.lrem(LIST1, VAL1))
        eq_([], self.redis.lrange(LIST1, 0, -1))
        eq_([], self.redis.keys("*"))

        eq_(0, self.redis.lrem("NON_EXISTENT_LIST", VAL1, 0))

    def test_brpoplpush(self):
        self.redis.rpush(LIST1, VAL1, VAL2)
        self.redis.rpush(LIST2, VAL3, VAL4)
        transfer_item = self.redis.brpoplpush(LIST1, LIST2)
        eq_(VAL2, transfer_item)
        eq_([VAL1], self.redis.lrange(LIST1, 0, -1))
        eq_([VAL2, VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))
        transfer_item = self.redis.brpoplpush(LIST1, LIST2)
        eq_(VAL1, transfer_item)
        eq_([], self.redis.lrange(LIST1, 0, -1))
        eq_([VAL1, VAL2, VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))
        timeout = 1
        start = time.time()
        eq_(None, self.redis.brpoplpush(LIST1, LIST2, timeout))
        eq_(timeout, int(time.time() - start))

    def test_rpoplpush(self):
        self.redis.rpush(LIST1, VAL1, VAL2)
        self.redis.rpush(LIST2, VAL3, VAL4)
        transfer_item = self.redis.rpoplpush(LIST1, LIST2)
        eq_(VAL2, transfer_item)
        eq_([VAL1], self.redis.lrange(LIST1, 0, -1))
        eq_([VAL2, VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))

    def test_rpoplpush_with_empty_source(self):
        # source list is empty
        del self.redis[LIST1]
        self.redis.rpush(LIST2, VAL3, VAL4)
        transfer_item = self.redis.rpoplpush(LIST1, LIST2)
        eq_(None, transfer_item)
        eq_([], self.redis.lrange(LIST1, 0, -1))
        # nothing has been added to the destination queue
        eq_([VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))

    def test_rpoplpush_source_with_empty_string(self):
        # source list contains empty string
        self.redis.rpush(LIST1, '')
        self.redis.rpush(LIST2, VAL3, VAL4)
        eq_(1, self.redis.llen(LIST1))
        eq_(2, self.redis.llen(LIST2))

        transfer_item = self.redis.rpoplpush(LIST1, LIST2)
        eq_('', transfer_item)
        eq_(0, self.redis.llen(LIST1))
        eq_(3, self.redis.llen(LIST2))
        eq_([], self.redis.lrange(LIST1, 0, -1))
        # empty string is added to the destination queue
        eq_(['', VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))

    def test_lrange_get_all(self):
        """Cases for returning entire list"""
        values = [VAL4, VAL3, VAL2, VAL1]

        eq_([], self.redis.lrange(LIST1, 0, 6))
        eq_([], self.redis.lrange(LIST1, 0, -1))
        self.redis.lpush(LIST1, *reversed(values))

        # Check with exact range
        eq_(values, self.redis.lrange(LIST1, 0, 3))
        # Check with negative index
        eq_(values, self.redis.lrange(LIST1, 0, -1))
        # Check with range larger than length of list
        eq_(values, self.redis.lrange(LIST1, 0, 6))

    def test_lrange_get_sublist(self):
        """Cases for returning partial list"""
        values = [VAL4, VAL3, VAL2, VAL1]

        eq_([], self.redis.lrange(LIST1, 0, 6))
        eq_([], self.redis.lrange(LIST1, 0, -1))
        self.redis.lpush(LIST1, *reversed(values))

        # Check from left end of the list
        eq_(values[:2], self.redis.lrange(LIST1, 0, 1))
        # Check from right end of the list
        eq_(values[2:4], self.redis.lrange(LIST1, 2, 3))
        # Check from right end of the list with negative range
        eq_(values[-2:], self.redis.lrange(LIST1, -2, -1))
        # Check from middle of the list
        eq_(values[1:3], self.redis.lrange(LIST1, 1, 2))

    def test_ltrim_retain_all(self):
        values = [VAL4, VAL3, VAL2, VAL1]
        self._reinitialize_list(LIST1, *values)

        self.redis.ltrim(LIST1, 0, -1)
        eq_(values, self.redis.lrange(LIST1, 0, -1))

        self.redis.ltrim(LIST1, 0, len(values) - 1)
        eq_(values, self.redis.lrange(LIST1, 0, -1))

        self.redis.ltrim(LIST1, 0, len(values) + 1)
        eq_(values, self.redis.lrange(LIST1, 0, -1))

        self.redis.ltrim(LIST1, -1 * len(values), -1)
        eq_(values, self.redis.lrange(LIST1, 0, -1))

        self.redis.ltrim(LIST1, -1 * (len(values) + 1), -1)
        eq_(values, self.redis.lrange(LIST1, 0, -1))

    def test_ltrim_remove_all(self):
        values = [VAL4, VAL3, VAL2, VAL1]
        self._reinitialize_list(LIST1, *values)

        self.redis.ltrim(LIST1, 2, 1)
        eq_([], self.redis.lrange(LIST1, 0, -1))

        self._reinitialize_list(LIST1, *values)
        self.redis.ltrim(LIST1, -1, -2)
        eq_([], self.redis.lrange(LIST1, 0, -1))

        self._reinitialize_list(LIST1, *values)
        self.redis.ltrim(LIST1, 2, -3)
        eq_([], self.redis.lrange(LIST1, 0, -1))

        self._reinitialize_list(LIST1, *values)
        self.redis.ltrim(LIST1, -1, 2)
        eq_([], self.redis.lrange(LIST1, 0, -1))

    def test_ltrim(self):
        values = [VAL4, VAL3, VAL2, VAL1]
        self._reinitialize_list(LIST1, *values)

        self.redis.ltrim(LIST1, 1, 2)
        eq_(values[1:3], self.redis.lrange(LIST1, 0, -1))

        self._reinitialize_list(LIST1, *values)
        self.redis.ltrim(LIST1, -3, -1)
        eq_(values[-3:], self.redis.lrange(LIST1, 0, -1))

        self._reinitialize_list(LIST1, *values)
        self.redis.ltrim(LIST1, 1, 5)
        eq_(values[1:5], self.redis.lrange(LIST1, 0, -1))

        self._reinitialize_list(LIST1, *values)
        self.redis.ltrim(LIST1, -100, 2)
        eq_(values[-100:3], self.redis.lrange(LIST1, 0, -1))

    def test_sort(self):
        values = ['0.1', '2', '1.3']
        self._reinitialize_list(LIST1, *values)

        # test unsorted
        eq_(self.redis.sort(LIST1, by='nosort'), values)

        # test straightforward sort
        eq_(self.redis.sort(LIST1), ['0.1', '1.3', '2'])

        # test alpha vs numeric sort
        values = [-1, -2]
        self._reinitialize_list(LIST1, *values)
        eq_(self.redis.sort(LIST1, alpha=True), ['-1', '-2'])
        eq_(self.redis.sort(LIST1, alpha=False), ['-2', '-1'])

        values = ['0.1', '2', '1.3']
        self._reinitialize_list(LIST1, *values)

        # test returning values sorted by values of other keys
        self.redis.set('by_0.1', '3')
        self.redis.set('by_2', '2')
        self.redis.set('by_1.3', '1')
        eq_(self.redis.sort(LIST1, by='by_*'), ['1.3', '2', '0.1'])

        # test returning values from other keys sorted by list
        self.redis.set('get1_0.1', 'a')
        self.redis.set('get1_2', 'b')
        self.redis.set('get1_1.3', 'c')
        eq_(self.redis.sort(LIST1, get='get1_*'), ['a', 'c', 'b'])

        # test storing result
        eq_(self.redis.sort(LIST1, get='get1_*', store='result'), 3)
        eq_(self.redis.llen('result'), 3)
        eq_(self.redis.lrange('result', 0, -1), ['a', 'c', 'b'])

        # test desc (reverse order)
        eq_(self.redis.sort(LIST1, get='get1_*', desc=True), ['b', 'c', 'a'])

        # test multiple gets without grouping
        self.redis.set('get2_0.1', 'x')
        self.redis.set('get2_2', 'y')
        self.redis.set('get2_1.3', 'z')
        eq_(self.redis.sort(LIST1, get=['get1_*', 'get2_*']), ['a', 'x', 'c', 'z', 'b', 'y'])

        # test start and num apply to sorted items not final flat list of values
        eq_(self.redis.sort(LIST1, get=['get1_*', 'get2_*'], start=1, num=1), ['c', 'z'])

        # test multiple gets with grouping
        eq_(self.redis.sort(LIST1, get=['get1_*', 'get2_*'], groups=True), [('a', 'x'), ('c', 'z'), ('b', 'y')])

        # test start and num
        eq_(self.redis.sort(LIST1, get=['get1_*', 'get2_*'], groups=True, start=1, num=1), [('c', 'z')])
        eq_(self.redis.sort(LIST1, get=['get1_*', 'get2_*'], groups=True, start=1, num=2), [('c', 'z'), ('b', 'y')])

    def test_lset(self):
        with assert_raises(Exception):
            self.redis.lset(LIST1, 1, VAL1)

        self.redis.lpush(LIST1, VAL2)
        eq_([VAL2], self.redis.lrange(LIST1, 0, -1))

        with assert_raises(Exception):
            self.redis.lset(LIST1, 1, VAL1)

        self.redis.lset(LIST1, 0, VAL1)
        eq_([VAL1], self.redis.lrange(LIST1, 0, -1))

    def test_push_pop_returns_str(self):
        key = 'l'
        values = ['5', 5, [], {}]
        for v in values:
            self.redis.rpush(key, v)
            eq_(self.redis.lpop(key),
                str(v))

    def _reinitialize_list(self, key, *values):
        """
        Re-initialize the list
        """
        self.redis.delete(LIST1)
        self.redis.lpush(LIST1, *reversed(values))

########NEW FILE########
__FILENAME__ = test_normalize
"""
Test redis command normalization.
"""
from nose.tools import eq_

from mockredis.client import MockRedis


def test_normalize_command_name():
    cases = [
        ("DEL", "delete"),
        ("del", "delete"),
        ("ping", "ping"),
        ("PING", "ping"),
    ]

    def _test(command, expected):
        redis = MockRedis()
        eq_(redis._normalize_command_name(command), expected)

    for command, expected in cases:
        yield _test, command, expected


def test_normalize_command_args():

    cases = [
        (False, "zadd", ("key", "member", 1.0), ("key", 1.0, "member")),
        (True, "zadd", ("key", 1.0, "member"), ("key", 1.0, "member")),

        (True, "zrevrangebyscore",
         ("key", "inf", "-inf"),
         ("key", "inf", "-inf")),

        (True, "zrevrangebyscore",
         ("key", "inf", "-inf", "limit", 0, 10),
         ("key", "inf", "-inf", 0, 10, False)),

        (True, "zrevrangebyscore",
         ("key", "inf", "-inf", "withscores"),
         ("key", "inf", "-inf", None, None, True)),

        (True, "zrevrangebyscore",
         ("key", "inf", "-inf", "withscores", "limit", 0, 10),
         ("key", "inf", "-inf", 0, 10, True)),

        (True, "zrevrangebyscore",
         ("key", "inf", "-inf", "WITHSCORES", "LIMIT", 0, 10),
         ("key", "inf", "-inf", 0, 10, True)),
    ]

    def _test(strict, command, args, expected):
        redis = MockRedis(strict=strict)
        eq_(tuple(redis._normalize_command_args(command, *args)), expected)

    for strict, command, args, expected in cases:
        yield _test, strict, command, args, expected


def test_normalize_command_response():

    cases = [
        ("get", "foo", "foo"),
        ("zrevrangebyscore", [(1, 2), (3, 4)], [1, 2, 3, 4]),
    ]

    def _test(command, response, expected):
        redis = MockRedis()
        eq_(redis._normalize_command_response(command, response), expected)

    for command, response, expected in cases:
        yield _test, command, response, expected


########NEW FILE########
__FILENAME__ = test_pipeline
from hashlib import sha1

from nose.tools import eq_

from mockredis.tests.fixtures import (assert_raises_redis_error,
                                      assert_raises_watch_error,
                                      setup)


class TestPipeline(object):

    def setup(self):
        setup(self)

    def test_pipeline(self):
        """
        Pipeline execution returns all of the saved up values.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.echo("foo")
            pipeline.echo("bar")

            eq_(["foo", "bar"], pipeline.execute())

    def test_pipeline_args(self):
        """
        It should be possible to pass transaction and shard_hint.
        """
        with self.redis.pipeline(transaction=False, shard_hint=None):
            pass

    def test_set_and_get(self):
        """
        Pipeline execution returns the pipeline, not the intermediate value.
        """
        with self.redis.pipeline() as pipeline:
            eq_(pipeline, pipeline.set("foo", "bar"))
            eq_(pipeline, pipeline.get("foo"))

            eq_([True, "bar"], pipeline.execute())

    def test_scripts(self):
        """
        Verify that script calls work across pipelines.

        This test basically ensures that the pipeline shares
        state with the mock redis instance.
        """
        script_content = "redis.call('PING')"
        sha = sha1(script_content.encode("utf-8")).hexdigest()

        self.redis.register_script(script_content)

        # Script exists in mock redis
        eq_([True], self.redis.script_exists(sha))

        # Script exists in pipeline
        eq_([True], self.redis.pipeline().script_exists(sha).execute()[0])

    def test_watch(self):
        """
        Verify watch puts the pipeline in immediate execution mode.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.watch("key1", "key2")
            eq_(None, pipeline.get("key1"))
            eq_(None, pipeline.get("key2"))
            eq_(True, pipeline.set("foo", "bar"))
            eq_("bar", pipeline.get("foo"))

    def test_multi(self):
        """
        Test explicit transaction with multi command.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.multi()
            eq_(pipeline, pipeline.set("foo", "bar"))
            eq_(pipeline, pipeline.get("foo"))

            eq_([True, "bar"], pipeline.execute())

    def test_multi_with_watch(self):
        """
        Test explicit transaction with watched keys.
        """
        self.redis.set("foo", "bar")

        with self.redis.pipeline() as pipeline:
            pipeline.watch("foo")
            eq_("bar", pipeline.get("foo"))

            pipeline.multi()
            eq_(pipeline, pipeline.set("foo", "baz"))
            eq_(pipeline, pipeline.get("foo"))

            eq_([True, "baz"], pipeline.execute())

    def test_multi_with_watch_zset(self):
        """
        Test explicit transaction with watched keys, this time with zset
        """
        self.redis.zadd("foo", "bar", 1.0)

        with self.redis.pipeline() as pipeline:
            pipeline.watch("foo")
            eq_(1, pipeline.zcard("foo"))
            pipeline.multi()
            eq_(pipeline, pipeline.zadd("foo", "baz", 2.0))
            eq_([1], pipeline.execute())

    def test_multi_with_watch_error(self):
        """
        Test explicit transaction with watched keys.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.watch("foo")
            eq_(True, pipeline.set("foo", "bar"))
            eq_("bar", pipeline.get("foo"))

            pipeline.multi()
            eq_(pipeline, pipeline.set("foo", "baz"))
            eq_(pipeline, pipeline.get("foo"))

            with assert_raises_watch_error():
                eq_([True, "baz"], pipeline.execute())

    def test_watch_after_multi(self):
        """
        Cannot watch after multi.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.multi()
            with assert_raises_redis_error():
                pipeline.watch()

    def test_multiple_multi_calls(self):
        """
        Cannot call multi mutliple times.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.multi()
            with assert_raises_redis_error():
                pipeline.multi()

    def test_multi_on_implicit_transaction(self):
        """
        Cannot start an explicit transaction when commands have already been issued.
        """
        with self.redis.pipeline() as pipeline:
            pipeline.set("foo", "bar")
            with assert_raises_redis_error():
                pipeline.multi()

########NEW FILE########
__FILENAME__ = test_pubsub
"""
Tests for pubsub don't yet support verification against redis-server.
"""
from nose.tools import eq_

from mockredis import MockRedis


class TestRedisPubSub(object):

    def setup(self):
        self.redis = MockRedis()
        self.redis.flushdb()

    def test_publish(self):
        channel = 'ch#1'
        msg = 'test message'
        self.redis.publish(channel, msg)
        eq_(self.redis.pubsub[channel], [msg])

########NEW FILE########
__FILENAME__ = test_redis
from datetime import timedelta
from time import time
import sys

from nose.tools import assert_raises, eq_, ok_

from mockredis.tests.fixtures import setup

if sys.version_info >= (3, 0):
    long = int


class TestRedis(object):

    def setup(self):
        setup(self)

    def test_get_types(self):
        '''
        testing type conversions for set/get, hset/hget, sadd/smembers

        Python bools, lists, dicts are returned as strings by
        redis-py/redis.
        '''

        values = list([
            True,
            False,
            [1, '2'],
            {
                'a': 1,
                'b': 'c'
            },
        ])

        eq_(None, self.redis.get('key'))

        for value in values:
            self.redis.set('key', value)
            eq_(str(value),
                self.redis.get('key'),
                "redis.get")

            self.redis.hset('hkey', 'item', value)
            eq_(str(value),
                self.redis.hget('hkey', 'item'))

            self.redis.sadd('skey', value)
            eq_(set([str(value)]),
                self.redis.smembers('skey'))

            self.redis.flushdb()

    def test_incr(self):
        '''
        incr, hincr when keys exist
        '''

        values = list([
            (1, '2'),
            ('1', '2'),
        ])

        for value in values:
            self.redis.set('key', value[0])
            self.redis.incr('key')
            eq_(value[1],
                self.redis.get('key'),
                "redis.incr")

            self.redis.hset('hkey', 'attr', value[0])
            self.redis.hincrby('hkey', 'attr')
            eq_(value[1],
                self.redis.hget('hkey', 'attr'),
                "redis.hincrby")

            self.redis.flushdb()

    def test_incr_init(self):
        '''
        incr, hincr, decr when keys do NOT exist
        '''

        self.redis.incr('key')
        eq_('1', self.redis.get('key'))

        self.redis.hincrby('hkey', 'attr')
        eq_('1', self.redis.hget('hkey', 'attr'))

        self.redis.decr('dkey')
        eq_('-1', self.redis.get('dkey'))

    def test_ttl(self):
        self.redis.set('key', 'key')
        self.redis.expire('key', 30)

        result = self.redis.ttl('key')
        ok_(isinstance(result, long))
        # should be less than the timeout originally set
        ok_(result <= 30)

    def test_ttl_timedelta(self):
        self.redis.set('key', 'key')
        self.redis.expire('key', timedelta(seconds=30))

        result = self.redis.ttl('key')
        ok_(isinstance(result, long))
        # should be less than the timeout originally set
        ok_(result <= 30)

    def test_ttl_when_absent(self):
        """
        Test absent ttl handling.
        """
        # redis >= 2.8.0 return -2 if key does exist
        eq_(self.redis.ttl("invalid_key"), -2)

        # redis-py return None if there is no pttl
        self.redis.set("key", "value")
        eq_(self.redis.ttl("key"), None)

    def test_ttl_no_timeout(self):
        """
        Test whether, like the redis-py lib, ttl returns None if the key has no timeout set.
        """
        self.redis.set('key', 'key')
        eq_(self.redis.ttl('key'), None)

    def test_pttl(self):
        expiration_ms = 3000
        self.redis.set('key', 'key')
        self.redis.pexpire('key', expiration_ms)

        result = self.redis.pttl('key')
        ok_(isinstance(result, long))
        # should be less than the timeout originally set
        ok_(result <= expiration_ms)

    def test_pttl_when_absent(self):
        """
        Test absent pttl handling.
        """
        # redis >= 2.8.0 return -2 if key does exist
        eq_(self.redis.pttl("invalid_key"), -2)

        # redis-py return None if there is no pttl
        self.redis.set("key", "value")
        eq_(self.redis.pttl("key"), None)

    def test_pttl_no_timeout(self):
        """
        Test whether, like the redis-py lib, pttl returns None if the key has no timeout set.
        """
        self.redis.set('key', 'key')
        eq_(self.redis.pttl('key'), None)

    def test_expireat_calculates_time(self):
        """
        test whether expireat sets the correct ttl, setting a timestamp 30s in the future
        """
        self.redis.set('key', 'key')
        self.redis.expireat('key', int(time()) + 30)

        result = self.redis.ttl('key')
        ok_(isinstance(result, long))
        # should be less than the timeout originally set
        ok_(result <= 30, "Expected {} to be less than 30".format(result))

    def test_keys(self):
        eq_([], self.redis.keys("*"))

        self.redis.set("foo", "bar")
        eq_(["foo"], self.redis.keys("*"))
        eq_(["foo"], self.redis.keys("foo*"))
        eq_(["foo"], self.redis.keys("foo"))
        eq_([], self.redis.keys("bar"))

        self.redis.set("food", "bbq")
        eq_({"foo", "food"}, set(self.redis.keys("*")))
        eq_({"foo", "food"}, set(self.redis.keys("foo*")))
        eq_(["foo"], self.redis.keys("foo"))
        eq_(["food"], self.redis.keys("food"))
        eq_([], self.redis.keys("bar"))

    def test_contains(self):
        ok_("foo" not in self.redis)
        self.redis.set("foo", "bar")
        ok_("foo" in self.redis)

    def test_getitem(self):
        with assert_raises(KeyError):
            self.redis["foo"]
        self.redis.set("foo", "bar")
        eq_("bar", self.redis["foo"])
        self.redis.delete("foo")
        with assert_raises(KeyError):
            self.redis["foo"]

    def test_setitem(self):
        eq_(None, self.redis.get("foo"))
        self.redis["foo"] = "bar"
        eq_("bar", self.redis.get("foo"))

    def test_delitem(self):
        self.redis["foo"] = "bar"
        eq_("bar", self.redis["foo"])
        del self.redis["foo"]
        eq_(None, self.redis.get("foo"))
        # redispy does not correctly raise KeyError here, so we don't either
        del self.redis["foo"]

########NEW FILE########
__FILENAME__ = test_scan
from nose.tools import eq_

from mockredis.tests.fixtures import setup


class TestRedisEmptyScans(object):
    """zero scan results tests"""

    def setup(self):
        setup(self)

    def test_scans(self):
        def eq_scan(results, cursor, elements):
            """
            Explicitly compare cursor and element by index as there
            redis-py currently returns a tuple for HSCAN and a list
            for the others, mockredis-py only returns lists, and it's
            not clear that emulating redis-py in this regard is "correct".
            """
            eq_(results[0], cursor)
            eq_(results[1], elements)

        eq_scan(self.redis.scan(), '0', [])
        eq_scan(self.redis.sscan("foo"), '0', [])
        eq_scan(self.redis.zscan("foo"), '0', [])
        eq_scan(self.redis.hscan("foo"), '0', {})


class TestRedisScan(object):
    """SCAN tests"""

    def setup(self):
        setup(self)
        self.redis.set('key_abc_1', '1')
        self.redis.set('key_abc_2', '2')
        self.redis.set('key_abc_3', '3')
        self.redis.set('key_abc_4', '4')
        self.redis.set('key_abc_5', '5')
        self.redis.set('key_abc_6', '6')

        self.redis.set('key_xyz_1', '1')
        self.redis.set('key_xyz_2', '2')
        self.redis.set('key_xyz_3', '3')
        self.redis.set('key_xyz_4', '4')
        self.redis.set('key_xyz_5', '5')

    def test_scan(self):
        def do_full_scan(match, count):
            keys = set()  # technically redis SCAN can return duplicate keys
            cursor = '0'
            result_cursor = None
            while result_cursor != '0':
                results = self.redis.scan(cursor=cursor, match=match, count=count)
                keys.update(results[1])
                cursor = results[0]
                result_cursor = cursor
            return keys

        abc_keys = set(['key_abc_1', 'key_abc_2', 'key_abc_3', 'key_abc_4', 'key_abc_5', 'key_abc_6'])
        eq_(do_full_scan('*abc*', 1), abc_keys)
        eq_(do_full_scan('*abc*', 2), abc_keys)
        eq_(do_full_scan('*abc*', 10), abc_keys)

        xyz_keys = set(['key_xyz_1', 'key_xyz_2', 'key_xyz_3', 'key_xyz_4', 'key_xyz_5'])
        eq_(do_full_scan('*xyz*', 1), xyz_keys)
        eq_(do_full_scan('*xyz*', 2), xyz_keys)
        eq_(do_full_scan('*xyz*', 10), xyz_keys)

        one_keys = set(['key_abc_1', 'key_xyz_1'])
        eq_(do_full_scan('*_1', 1), one_keys)
        eq_(do_full_scan('*_1', 2), one_keys)
        eq_(do_full_scan('*_1', 10), one_keys)

        all_keys = abc_keys.union(xyz_keys)
        eq_(do_full_scan('*', 1), all_keys)
        eq_(do_full_scan('*', 2), all_keys)
        eq_(do_full_scan('*', 10), all_keys)


class TestRedisSScan(object):
    """SSCAN tests"""

    def setup(self):
        setup(self)
        self.redis.sadd('key', 'abc_1')
        self.redis.sadd('key', 'abc_2')
        self.redis.sadd('key', 'abc_3')
        self.redis.sadd('key', 'abc_4')
        self.redis.sadd('key', 'abc_5')
        self.redis.sadd('key', 'abc_6')

        self.redis.sadd('key', 'xyz_1')
        self.redis.sadd('key', 'xyz_2')
        self.redis.sadd('key', 'xyz_3')
        self.redis.sadd('key', 'xyz_4')
        self.redis.sadd('key', 'xyz_5')

    def test_scan(self):
        def do_full_scan(name, match, count):
            keys = set()  # technically redis SCAN can return duplicate keys
            cursor = '0'
            result_cursor = None
            while result_cursor != '0':
                results = self.redis.sscan(name, cursor=cursor, match=match, count=count)
                keys.update(results[1])
                cursor = results[0]
                result_cursor = cursor
            return keys

        abc_members = set(['abc_1', 'abc_2', 'abc_3', 'abc_4', 'abc_5', 'abc_6'])
        eq_(do_full_scan('key', '*abc*', 1), abc_members)
        eq_(do_full_scan('key', '*abc*', 2), abc_members)
        eq_(do_full_scan('key', '*abc*', 10), abc_members)

        xyz_members = set(['xyz_1', 'xyz_2', 'xyz_3', 'xyz_4', 'xyz_5'])
        eq_(do_full_scan('key', '*xyz*', 1), xyz_members)
        eq_(do_full_scan('key', '*xyz*', 2), xyz_members)
        eq_(do_full_scan('key', '*xyz*', 10), xyz_members)

        one_members = set(['abc_1', 'xyz_1'])
        eq_(do_full_scan('key', '*_1', 1), one_members)
        eq_(do_full_scan('key', '*_1', 2), one_members)
        eq_(do_full_scan('key', '*_1', 10), one_members)

        all_members = abc_members.union(xyz_members)
        eq_(do_full_scan('key', '*', 1), all_members)
        eq_(do_full_scan('key', '*', 2), all_members)
        eq_(do_full_scan('key', '*', 10), all_members)


class TestRedisZScan(object):
    """ZSCAN tests"""

    def setup(self):
        setup(self)
        self.redis.zadd('key', 'abc_1', 1)
        self.redis.zadd('key', 'abc_2', 2)
        self.redis.zadd('key', 'abc_3', 3)
        self.redis.zadd('key', 'abc_4', 4)
        self.redis.zadd('key', 'abc_5', 5)
        self.redis.zadd('key', 'abc_6', 6)

        self.redis.zadd('key', 'xyz_1', 1)
        self.redis.zadd('key', 'xyz_2', 2)
        self.redis.zadd('key', 'xyz_3', 3)
        self.redis.zadd('key', 'xyz_4', 4)
        self.redis.zadd('key', 'xyz_5', 5)

    def test_scan(self):
        def do_full_scan(name, match, count):
            keys = set()  # technically redis SCAN can return duplicate keys
            cursor = '0'
            result_cursor = None
            while result_cursor != '0':
                results = self.redis.zscan(name, cursor=cursor, match=match, count=count)
                keys.update(results[1])
                cursor = results[0]
                result_cursor = cursor
            return keys

        abc_members = set([('abc_1', 1), ('abc_2', 2), ('abc_3', 3), ('abc_4', 4), ('abc_5', 5), ('abc_6', 6)])
        eq_(do_full_scan('key', '*abc*', 1), abc_members)
        eq_(do_full_scan('key', '*abc*', 2), abc_members)
        eq_(do_full_scan('key', '*abc*', 10), abc_members)

        xyz_members = set([('xyz_1', 1), ('xyz_2', 2), ('xyz_3', 3), ('xyz_4', 4), ('xyz_5', 5)])
        eq_(do_full_scan('key', '*xyz*', 1), xyz_members)
        eq_(do_full_scan('key', '*xyz*', 2), xyz_members)
        eq_(do_full_scan('key', '*xyz*', 10), xyz_members)

        one_members = set([('abc_1', 1), ('xyz_1', 1)])
        eq_(do_full_scan('key', '*_1', 1), one_members)
        eq_(do_full_scan('key', '*_1', 2), one_members)
        eq_(do_full_scan('key', '*_1', 10), one_members)

        all_members = abc_members.union(xyz_members)
        eq_(do_full_scan('key', '*', 1), all_members)
        eq_(do_full_scan('key', '*', 2), all_members)
        eq_(do_full_scan('key', '*', 10), all_members)


class TestRedisHScan(object):
    """HSCAN tests"""

    def setup(self):
        setup(self)
        self.redis.hset('key', 'abc_1', 1)
        self.redis.hset('key', 'abc_2', 2)
        self.redis.hset('key', 'abc_3', 3)
        self.redis.hset('key', 'abc_4', 4)
        self.redis.hset('key', 'abc_5', 5)
        self.redis.hset('key', 'abc_6', 6)

        self.redis.hset('key', 'xyz_1', 1)
        self.redis.hset('key', 'xyz_2', 2)
        self.redis.hset('key', 'xyz_3', 3)
        self.redis.hset('key', 'xyz_4', 4)
        self.redis.hset('key', 'xyz_5', 5)

    def test_scan(self):
        def do_full_scan(name, match, count):
            keys = {}
            cursor = '0'
            result_cursor = None
            while result_cursor != '0':
                results = self.redis.hscan(name, cursor=cursor, match=match, count=count)
                keys.update(results[1])
                cursor = results[0]
                result_cursor = cursor
            return keys

        abc = {'abc_1': '1', 'abc_2': '2', 'abc_3': '3', 'abc_4': '4', 'abc_5': '5', 'abc_6': '6'}
        eq_(do_full_scan('key', '*abc*', 1), abc)
        eq_(do_full_scan('key', '*abc*', 2), abc)
        eq_(do_full_scan('key', '*abc*', 10), abc)

        xyz = {'xyz_1': '1', 'xyz_2': '2', 'xyz_3': '3', 'xyz_4': '4', 'xyz_5': '5'}
        eq_(do_full_scan('key', '*xyz*', 1), xyz)
        eq_(do_full_scan('key', '*xyz*', 2), xyz)
        eq_(do_full_scan('key', '*xyz*', 10), xyz)

        all_1 = {'abc_1': '1', 'xyz_1': '1'}
        eq_(do_full_scan('key', '*_1', 1), all_1)
        eq_(do_full_scan('key', '*_1', 2), all_1)
        eq_(do_full_scan('key', '*_1', 10), all_1)

        abcxyz = abc
        abcxyz.update(xyz)
        eq_(do_full_scan('key', '*', 1), abcxyz)
        eq_(do_full_scan('key', '*', 2), abcxyz)
        eq_(do_full_scan('key', '*', 10), abcxyz)

########NEW FILE########
__FILENAME__ = test_script
"""
Tests for scripts don't yet support verification against redis-server.
"""
from hashlib import sha1
from unittest.case import SkipTest
import sys

from nose.tools import assert_raises, eq_, ok_

from mockredis import MockRedis
from mockredis.exceptions import RedisError
from mockredis.script import Script as MockRedisScript
from mockredis.tests.test_constants import (
    LIST1, LIST2,
    SET1,
    VAL1, VAL2, VAL3, VAL4,
    LPOP_SCRIPT
)


if sys.version_info >= (3, 0):
    long = int


class TestScript(object):
    """
    Tests for MockRedis scripting operations
    """

    def setup(self):
        self.redis = MockRedis()
        self.LPOP_SCRIPT_SHA = sha1(LPOP_SCRIPT.encode("utf-8")).hexdigest()

        try:
            lua, lua_globals = MockRedisScript._import_lua()
        except RuntimeError:
            raise SkipTest("mockredispy was not installed with lua support")

        self.lua = lua
        self.lua_globals = lua_globals

        assert_equal_list = """
        function compare_list(list1, list2)
            if #list1 ~= #list2 then
                return false
            end
            for i, item1 in ipairs(list1) do
                if item1 ~= list2[i] then
                    return false
                end
            end
            return true
        end

        function assert_equal_list(list1, list2)
            assert(compare_list(list1, list2))
        end
        return assert_equal_list
        """
        self.lua_assert_equal_list = self.lua.execute(assert_equal_list)

        assert_equal_list_with_pairs = """
        function pair_exists(list1, key, value)
            i = 1
            for i, item1 in ipairs(list1) do
                if i%2 == 1 then
                    if (list1[i] == key) and (list1[i + 1] == value) then
                        return true
                    end
                end
            end
            return false
        end

        function compare_list_with_pairs(list1, list2)
            if #list1 ~= #list2 or #list1 % 2 == 1 then
                return false
            end
            for i = 1, #list1, 2 do
                if not pair_exists(list2, list1[i], list1[i + 1]) then
                    return false
                end
            end
            return true
        end

        function assert_equal_list_with_pairs(list1, list2)
            assert(compare_list_with_pairs(list1, list2))
        end
        return assert_equal_list_with_pairs
        """
        self.lua_assert_equal_list_with_pairs = self.lua.execute(assert_equal_list_with_pairs)

        compare_val = """
        function compare_val(var1, var2)
            return var1 == var2
        end
        return compare_val
        """
        self.lua_compare_val = self.lua.execute(compare_val)

    def test_register_script_lpush(self):
        # lpush two values
        script_content = "redis.call('LPUSH', KEYS[1], ARGV[1], ARGV[2])"
        script = self.redis.register_script(script_content)
        script(keys=[LIST1], args=[VAL1, VAL2])

        # validate insertion
        eq_([VAL2, VAL1], self.redis.lrange(LIST1, 0, -1))

    def test_register_script_lpop(self):
        self.redis.lpush(LIST1, VAL2, VAL1)

        # lpop one value
        script_content = "return redis.call('LPOP', KEYS[1])"
        script = self.redis.register_script(script_content)
        list_item = script(keys=[LIST1])

        # validate lpop
        eq_(VAL1, list_item)
        eq_([VAL2], self.redis.lrange(LIST1, 0, -1))

    def test_register_script_rpoplpush(self):
        self.redis.lpush(LIST1, VAL2, VAL1)
        self.redis.lpush(LIST2, VAL4, VAL3)

        # rpoplpush
        script_content = "redis.call('RPOPLPUSH', KEYS[1], KEYS[2])"
        script = self.redis.register_script(script_content)
        script(keys=[LIST1, LIST2])

        #validate rpoplpush
        eq_([VAL1], self.redis.lrange(LIST1, 0, -1))
        eq_([VAL2, VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))

    def test_register_script_rpop_lpush(self):
        self.redis.lpush(LIST1, VAL2, VAL1)
        self.redis.lpush(LIST2, VAL4, VAL3)

        # rpop from LIST1 and lpush the same value to LIST2
        script_content = """
        local tmp_item = redis.call('RPOP', KEYS[1])
        redis.call('LPUSH', KEYS[2], tmp_item)
        """
        script = self.redis.register_script(script_content)
        script(keys=[LIST1, LIST2])

        #validate rpop and then lpush
        eq_([VAL1], self.redis.lrange(LIST1, 0, -1))
        eq_([VAL2, VAL3, VAL4], self.redis.lrange(LIST2, 0, -1))

    def test_register_script_client(self):
        # lpush two values in LIST1 in first instance of redis
        self.redis.lpush(LIST1, VAL2, VAL1)

        # create script on first instance of redis
        script_content = LPOP_SCRIPT
        script = self.redis.register_script(script_content)

        # lpush two values in LIST1 in redis2 (second instance of redis)
        redis2 = MockRedis()
        redis2.lpush(LIST1, VAL4, VAL3)

        # execute LPOP script on redis2 instance
        list_item = script(keys=[LIST1], client=redis2)

        # validate lpop from LIST1 in redis2
        eq_(VAL3, list_item)
        eq_([VAL4], redis2.lrange(LIST1, 0, -1))
        eq_([VAL1, VAL2], self.redis.lrange(LIST1, 0, -1))

    def test_eval_lpush(self):
        # lpush two values
        script_content = "redis.call('LPUSH', KEYS[1], ARGV[1], ARGV[2])"
        self.redis.eval(script_content, 1, LIST1, VAL1, VAL2)

        # validate insertion
        eq_([VAL2, VAL1], self.redis.lrange(LIST1, 0, -1))

    def test_eval_lpop(self):
        self.redis.lpush(LIST1, VAL2, VAL1)

        # lpop one value
        script_content = "return redis.call('LPOP', KEYS[1])"
        list_item = self.redis.eval(script_content, 1, LIST1)

        # validate lpop
        eq_(VAL1, list_item)
        eq_([VAL2], self.redis.lrange(LIST1, 0, -1))

    def test_eval_zadd(self):
        # The score and member are reversed when the client is not strict.
        self.redis.strict = False
        script_content = "return redis.call('zadd', KEYS[1], ARGV[1], ARGV[2])"
        self.redis.eval(script_content, 1, SET1, 42, VAL1)

        eq_(42, self.redis.zscore(SET1, VAL1))

    def test_eval_zrangebyscore(self):
        # Make sure the limit is removed.
        script = "return redis.call('zrangebyscore',KEYS[1],ARGV[1],ARGV[2])"
        self.eval_zrangebyscore(script)

    def test_eval_zrangebyscore_with_limit(self):
        # Make sure the limit is removed.
        script = ("return redis.call('zrangebyscore', "
                  "KEYS[1], ARGV[1], ARGV[2], 'LIMIT', 0, 2)")

        self.eval_zrangebyscore(script)

    def eval_zrangebyscore(self, script):
        self.redis.strict = False
        self.redis.zadd(SET1, VAL1, 1)
        self.redis.zadd(SET1, VAL2, 2)

        eq_([],           self.redis.eval(script, 1, SET1, 0, 0))
        eq_([VAL1],       self.redis.eval(script, 1, SET1, 0, 1))
        eq_([VAL1, VAL2], self.redis.eval(script, 1, SET1, 0, 2))
        eq_([VAL2],       self.redis.eval(script, 1, SET1, 2, 2))

    def test_table_type(self):
        self.redis.lpush(LIST1, VAL2, VAL1)
        script_content = """
        local items = redis.call('LRANGE', KEYS[1], ARGV[1], ARGV[2])
        return type(items)
        """
        script = self.redis.register_script(script_content)
        itemType = script(keys=[LIST1], args=[0, -1])
        eq_('table', itemType)

    def test_script_hgetall(self):
        myhash = {"k1": "v1"}
        self.redis.hmset("myhash", myhash)
        script_content = """
        return redis.call('HGETALL', KEYS[1])
        """
        script = self.redis.register_script(script_content)
        item = script(keys=["myhash"])
        ok_(isinstance(item, list))
        eq_(["k1", "v1"], item)

    def test_evalsha(self):
        self.redis.lpush(LIST1, VAL1)
        script = LPOP_SCRIPT
        sha = self.LPOP_SCRIPT_SHA

        # validator error when script not registered
        with assert_raises(RedisError) as redis_error:
            self.redis.evalsha(self.LPOP_SCRIPT_SHA, 1, LIST1)

        eq_("Sha not registered", str(redis_error.exception))

        with assert_raises(RedisError):
            self.redis.evalsha(self.LPOP_SCRIPT_SHA, 1, LIST1)

        # load script and then evalsha
        eq_(sha, self.redis.script_load(script))
        eq_(VAL1, self.redis.evalsha(sha, 1, LIST1))
        eq_(0, self.redis.llen(LIST1))

    def test_script_exists(self):
        script = LPOP_SCRIPT
        sha = self.LPOP_SCRIPT_SHA
        eq_([False], self.redis.script_exists(sha))
        self.redis.register_script(script)
        eq_([True], self.redis.script_exists(sha))

    def test_script_flush(self):
        script = LPOP_SCRIPT
        sha = self.LPOP_SCRIPT_SHA
        self.redis.register_script(script)
        eq_([True], self.redis.script_exists(sha))
        self.redis.script_flush()
        eq_([False], self.redis.script_exists(sha))

    def test_script_load(self):
        script = LPOP_SCRIPT
        sha = self.LPOP_SCRIPT_SHA
        eq_([False], self.redis.script_exists(sha))
        eq_(sha, self.redis.script_load(script))
        eq_([True], self.redis.script_exists(sha))

    def test_lua_to_python_none(self):
        lval = self.lua.eval("")
        pval = MockRedisScript._lua_to_python(lval)
        ok_(pval is None)

    def test_lua_to_python_list(self):
        lval = self.lua.eval('{"val1", "val2"}')
        pval = MockRedisScript._lua_to_python(lval)
        ok_(isinstance(pval, list))
        eq_(["val1", "val2"], pval)

    def test_lua_to_python_long(self):
        lval = self.lua.eval('22')
        pval = MockRedisScript._lua_to_python(lval)
        ok_(isinstance(pval, long))
        eq_(22, pval)

    def test_lua_to_python_flota(self):
        lval = self.lua.eval('22.2')
        pval = MockRedisScript._lua_to_python(lval)
        ok_(isinstance(pval, float))
        eq_(22.2, pval)

    def test_lua_to_python_string(self):
        lval = self.lua.eval('"somestring"')
        pval = MockRedisScript._lua_to_python(lval)
        ok_(isinstance(pval, str))
        eq_("somestring", pval)

    def test_lua_to_python_bool(self):
        lval = self.lua.eval('true')
        pval = MockRedisScript._lua_to_python(lval)
        ok_(isinstance(pval, bool))
        eq_(True, pval)

    def test_python_to_lua_none(self):
        pval = None
        lval = MockRedisScript._python_to_lua(pval)
        is_null = """
        function is_null(var1)
            return var1 == nil
        end
        return is_null
        """
        lua_is_null = self.lua.execute(is_null)
        ok_(MockRedisScript._lua_to_python(lua_is_null(lval)))

    def test_python_to_lua_string(self):
        pval = "somestring"
        lval = MockRedisScript._python_to_lua(pval)
        lval_expected = self.lua.eval('"somestring"')
        eq_("string", self.lua_globals.type(lval))
        eq_(lval_expected, lval)

    def test_python_to_lua_list(self):
        pval = ["abc", "xyz"]
        lval = MockRedisScript._python_to_lua(pval)
        lval_expected = self.lua.eval('{"abc", "xyz"}')
        self.lua_assert_equal_list(lval_expected, lval)

    def test_python_to_lua_dict(self):
        pval = {"k1": "v1", "k2": "v2"}
        lval = MockRedisScript._python_to_lua(pval)
        lval_expected = self.lua.eval('{"k1", "v1", "k2", "v2"}')
        self.lua_assert_equal_list_with_pairs(lval_expected, lval)

    def test_python_to_lua_long(self):
        pval = long(10)
        lval = MockRedisScript._python_to_lua(pval)
        lval_expected = self.lua.eval('10')
        eq_("number", self.lua_globals.type(lval))
        ok_(MockRedisScript._lua_to_python(self.lua_compare_val(lval_expected, lval)))

    def test_python_to_lua_float(self):
        pval = 10.1
        lval = MockRedisScript._python_to_lua(pval)
        lval_expected = self.lua.eval('10.1')
        eq_("number", self.lua_globals.type(lval))
        ok_(MockRedisScript._lua_to_python(self.lua_compare_val(lval_expected, lval)))

    def test_python_to_lua_boolean(self):
        pval = True
        lval = MockRedisScript._python_to_lua(pval)
        eq_("boolean", self.lua_globals.type(lval))
        ok_(MockRedisScript._lua_to_python(lval))

########NEW FILE########
__FILENAME__ = test_set
from nose.tools import assert_raises, eq_, ok_

from mockredis.tests.fixtures import setup


class TestRedisSet(object):
    """set tests"""

    def setup(self):
        setup(self)

    def test_sadd(self):
        key = "set"
        values = ["one", "uno", "two", "three"]
        for value in values:
            eq_(1, self.redis.sadd(key, value))

    def test_sadd_multiple(self):
        key = "set"
        values = ["one", "uno", "two", "three"]
        eq_(4, self.redis.sadd(key, *values))

    def test_sadd_duplicate_key(self):
        key = "set"
        eq_(1, self.redis.sadd(key, "one"))
        eq_(0, self.redis.sadd(key, "one"))

    def test_scard(self):
        key = "set"
        eq_(0, self.redis.scard(key))
        ok_(not key in self.redis)
        values = ["one", "uno", "two", "three"]
        eq_(4, self.redis.sadd(key, *values))
        eq_(4, self.redis.scard(key))

    def test_sdiff(self):
        self.redis.sadd("x", "one", "two", "three")
        self.redis.sadd("y", "one")
        self.redis.sadd("z", "two")

        with assert_raises(Exception):
            self.redis.sdiff([])

        eq_(set(), self.redis.sdiff("w"))
        eq_(set(["one", "two", "three"]), self.redis.sdiff("x"))
        eq_(set(["two", "three"]), self.redis.sdiff("x", "y"))
        eq_(set(["two", "three"]), self.redis.sdiff(["x", "y"]))
        eq_(set(["three"]), self.redis.sdiff("x", "y", "z"))
        eq_(set(["three"]), self.redis.sdiff(["x", "y"], "z"))

    def test_sdiffstore(self):
        self.redis.sadd("x", "one", "two", "three")
        self.redis.sadd("y", "one")
        self.redis.sadd("z", "two")

        with assert_raises(Exception):
            self.redis.sdiffstore("w", [])

        eq_(3, self.redis.sdiffstore("w", "x"))
        eq_(set(["one", "two", "three"]), self.redis.smembers("w"))

        eq_(2, self.redis.sdiffstore("w", "x", "y"))
        eq_(set(["two", "three"]), self.redis.smembers("w"))
        eq_(2, self.redis.sdiffstore("w", ["x", "y"]))
        eq_(set(["two", "three"]), self.redis.smembers("w"))
        eq_(1, self.redis.sdiffstore("w", "x", "y", "z"))
        eq_(set(["three"]), self.redis.smembers("w"))
        eq_(1, self.redis.sdiffstore("w", ["x", "y"], "z"))
        eq_(set(["three"]), self.redis.smembers("w"))

    def test_sinter(self):
        self.redis.sadd("x", "one", "two", "three")
        self.redis.sadd("y", "one")
        self.redis.sadd("z", "two")

        with assert_raises(Exception):
            self.redis.sinter([])

        eq_(set(), self.redis.sinter("w"))
        eq_(set(["one", "two", "three"]), self.redis.sinter("x"))
        eq_(set(["one"]), self.redis.sinter("x", "y"))
        eq_(set(["two"]), self.redis.sinter(["x", "z"]))
        eq_(set(), self.redis.sinter("x", "y", "z"))
        eq_(set(), self.redis.sinter(["x", "y"], "z"))

    def test_sinterstore(self):
        self.redis.sadd("x", "one", "two", "three")
        self.redis.sadd("y", "one")
        self.redis.sadd("z", "two")

        with assert_raises(Exception):
            self.redis.sinterstore("w", [])

        eq_(3, self.redis.sinterstore("w", "x"))
        eq_(set(["one", "two", "three"]), self.redis.smembers("w"))

        eq_(1, self.redis.sinterstore("w", "x", "y"))
        eq_(set(["one"]), self.redis.smembers("w"))
        eq_(1, self.redis.sinterstore("w", ["x", "z"]))
        eq_(set(["two"]), self.redis.smembers("w"))
        eq_(0, self.redis.sinterstore("w", "x", "y", "z"))
        eq_(set(), self.redis.smembers("w"))
        eq_(0, self.redis.sinterstore("w", ["x", "y"], "z"))
        eq_(set(), self.redis.smembers("w"))

    def test_sismember(self):
        key = "set"
        ok_(not self.redis.sismember(key, "one"))
        ok_(key not in self.redis)
        eq_(1, self.redis.sadd(key, "one"))
        ok_(self.redis.sismember(key, "one"))
        ok_(not self.redis.sismember(key, "two"))

    def test_ismember_numeric(self):
        """
        Verify string conversion.
        """
        key = "set"
        eq_(1, self.redis.sadd(key,  1))
        eq_(set(["1"]), self.redis.smembers(key))
        ok_(self.redis.sismember(key, "1"))
        ok_(self.redis.sismember(key, 1))

    def test_smembers(self):
        key = "set"
        eq_(set(), self.redis.smembers(key))
        ok_(key not in self.redis)
        eq_(1, self.redis.sadd(key, "one"))
        eq_(set(["one"]), self.redis.smembers(key))
        eq_(1, self.redis.sadd(key, "two"))
        eq_(set(["one", "two"]), self.redis.smembers(key))

    def test_smembers_copy(self):
        key = "set"
        self.redis.sadd(key, "one", "two", "three")
        members = self.redis.smembers(key)
        eq_({"one", "two", "three"}, members)
        for member in members:
            # Checking that SMEMBERS returns the copy of internal data structure instead of
            # direct references. Otherwise SREM operation may give following error.
            # RuntimeError: Set changed size during iteration
            self.redis.srem(key, member)
        eq_(set(), self.redis.smembers(key))

    def test_smove(self):
        eq_(0, self.redis.smove("x", "y", "one"))

        eq_(2, self.redis.sadd("x", "one", "two"))
        eq_(set(["one", "two"]), self.redis.smembers("x"))
        eq_(set(), self.redis.smembers("y"))

        eq_(0, self.redis.smove("x", "y", "three"))
        eq_(set(["one", "two"]), self.redis.smembers("x"))
        eq_(set(), self.redis.smembers("y"))

        eq_(1, self.redis.smove("x", "y", "one"))
        eq_(set(["two"]), self.redis.smembers("x"))
        eq_(set(["one"]), self.redis.smembers("y"))

    def test_spop(self):
        key = "set"
        eq_(None, self.redis.spop(key))
        eq_(1, self.redis.sadd(key, "one"))
        eq_("one", self.redis.spop(key))
        eq_(0, self.redis.scard(key))
        eq_(1, self.redis.sadd(key, "one"))
        eq_(1, self.redis.sadd(key, "two"))
        first = self.redis.spop(key)
        ok_(first in ["one", "two"])
        eq_(1, self.redis.scard(key))
        second = self.redis.spop(key)
        eq_("one" if first == "two" else "two", second)
        eq_(0, self.redis.scard(key))
        eq_([], self.redis.keys("*"))

    def test_srandmember(self):
        key = "set"
        # count is None
        eq_(None, self.redis.srandmember(key))
        eq_(1, self.redis.sadd(key, "one"))
        eq_("one", self.redis.srandmember(key))
        eq_(1, self.redis.scard(key))
        eq_(1, self.redis.sadd(key, "two"))
        ok_(self.redis.srandmember(key) in ["one", "two"])
        eq_(2, self.redis.scard(key))
        # count > 0
        eq_([], self.redis.srandmember("empty", 1))
        ok_(self.redis.srandmember(key, 1)[0] in ["one", "two"])
        eq_(set(["one", "two"]), set(self.redis.srandmember(key, 2)))
        # count < 0
        eq_([], self.redis.srandmember("empty", -1))
        ok_(self.redis.srandmember(key, -1)[0] in ["one", "two"])
        members = self.redis.srandmember(key, -2)
        eq_(2, len(members))
        for member in members:
            ok_(member in ["one", "two"])

    def test_srem(self):
        key = "set"
        eq_(0, self.redis.srem(key, "one"))
        eq_(3, self.redis.sadd(key, "one", "two", "three"))
        eq_(0, self.redis.srem(key, "four"))
        eq_(2, self.redis.srem(key, "one", "three"))
        eq_(1, self.redis.srem(key, "two", "four"))
        eq_([], self.redis.keys("*"))

    def test_sunion(self):
        self.redis.sadd("x", "one", "two", "three")
        self.redis.sadd("y", "one")
        self.redis.sadd("z", "two")

        with assert_raises(Exception):
            self.redis.sunion([])

        eq_(set(), self.redis.sunion("v"))
        eq_(set(["one", "two", "three"]), self.redis.sunion("x"))
        eq_(set(["one"]), self.redis.sunion("v", "y"))
        eq_(set(["one", "two"]), self.redis.sunion(["y", "z"]))
        eq_(set(["one", "two", "three"]), self.redis.sunion("x", "y", "z"))
        eq_(set(["one", "two", "three"]), self.redis.sunion(["x", "y"], "z"))

    def test_sunionstore(self):
        self.redis.sadd("x", "one", "two", "three")
        self.redis.sadd("y", "one")
        self.redis.sadd("z", "two")

        with assert_raises(Exception):
            self.redis.sunionstore("w", [])

        eq_(0, self.redis.sunionstore("w", "v"))
        eq_(set(), self.redis.smembers("w"))

        eq_(3, self.redis.sunionstore("w", "x"))
        eq_(set(["one", "two", "three"]), self.redis.smembers("w"))

        eq_(1, self.redis.sunionstore("w", "v", "y"))
        eq_(set(["one"]), self.redis.smembers("w"))

        eq_(2, self.redis.sunionstore("w", ["y", "z"]))
        eq_(set(["one", "two"]), self.redis.smembers("w"))

        eq_(3, self.redis.sunionstore("w", "x", "y", "z"))
        eq_(set(["one", "two", "three"]), self.redis.smembers("w"))

        eq_(3, self.redis.sunionstore("w", ["x", "y"], "z"))
        eq_(set(["one", "two", "three"]), self.redis.smembers("w"))

########NEW FILE########
__FILENAME__ = test_sortedset
from nose.tools import assert_raises, eq_, ok_

from mockredis.sortedset import SortedSet


class TestSortedSet(object):
    """
    Tests the sorted set data structure, not the redis commands.
    """

    def setup(self):
        self.zset = SortedSet()

    def test_initially_empty(self):
        """
        Sorted set is created empty.
        """
        eq_(0, len(self.zset))

    def test_insert(self):
        """
        Insertion maintains order and uniqueness.
        """
        # insert two values
        ok_(self.zset.insert("one", 1.0))
        ok_(self.zset.insert("two", 2.0))

        # validate insertion
        eq_(2, len(self.zset))
        ok_("one" in self.zset)
        ok_("two" in self.zset)
        ok_(not 1.0 in self.zset)
        ok_(not 2.0 in self.zset)
        eq_(1.0, self.zset["one"])
        eq_(2.0, self.zset["two"])
        with assert_raises(KeyError):
            self.zset[1.0]
        with assert_raises(KeyError):
            self.zset[2.0]
        eq_(0, self.zset.rank("one"))
        eq_(1, self.zset.rank("two"))
        eq_(None, self.zset.rank(1.0))
        eq_(None, self.zset.rank(2.0))

        # re-insert a value
        ok_(not self.zset.insert("one", 3.0))

        # validate the update
        eq_(2, len(self.zset))
        eq_(3.0, self.zset.score("one"))
        eq_(0, self.zset.rank("two"))
        eq_(1, self.zset.rank("one"))

    def test_remove(self):
        """
        Removal maintains order.
        """
        # insert a few elements
        self.zset["one"] = 1.0
        self.zset["uno"] = 1.0
        self.zset["three"] = 3.0
        self.zset["two"] = 2.0

        # cannot remove a member that is not present
        eq_(False, self.zset.remove("four"))

        # removing an existing entry works
        eq_(True, self.zset.remove("two"))
        eq_(3, len(self.zset))
        eq_(0, self.zset.rank("one"))
        eq_(1, self.zset.rank("uno"))
        eq_(None, self.zset.rank("two"))
        eq_(2, self.zset.rank("three"))

        # delete also works
        del self.zset["uno"]
        eq_(2, len(self.zset))
        eq_(0, self.zset.rank("one"))
        eq_(None, self.zset.rank("uno"))
        eq_(None, self.zset.rank("two"))
        eq_(1, self.zset.rank("three"))

    def test_scoremap(self):
        self.zset["one"] = 1.0
        self.zset["uno"] = 1.0
        self.zset["two"] = 2.0
        self.zset["three"] = 3.0
        eq_([(1.0, "one"), (1.0, "uno")], self.zset.scorerange(1.0, 1.1))
        eq_([(1.0, "one"), (1.0, "uno"), (2.0, "two")],
            self.zset.scorerange(1.0, 2.0))

########NEW FILE########
__FILENAME__ = test_string
from datetime import timedelta

from nose.tools import eq_, ok_

from mockredis.client import get_total_milliseconds
from mockredis.tests.fixtures import raises_response_error, setup


class TestRedisString(object):
    """string tests"""

    def setup(self):
        setup(self)

    def test_get(self):
        eq_(None, self.redis.get('key'))
        self.redis.set('key', 'value')
        eq_('value', self.redis.get('key'))

    def test_mget(self):
        eq_(None, self.redis.get('mget1'))
        eq_(None, self.redis.get('mget2'))
        eq_([None, None], self.redis.mget('mget1', 'mget2'))
        eq_([None, None], self.redis.mget(['mget1', 'mget2']))

        self.redis.set('mget1', 'value1')
        self.redis.set('mget2', 'value2')
        eq_(['value1', 'value2'], self.redis.mget('mget1', 'mget2'))
        eq_(['value1', 'value2'], self.redis.mget(['mget1', 'mget2']))

    def test_set_no_options(self):
        self.redis.set('key', 'value')
        eq_('value', self.redis.get('key'))

    def _assert_set_with_options(self, test_cases):
        """
        Assert conditions for setting a key on the set function.

        The set function can take px, ex, nx and xx kwargs, this function asserts various conditions
        on set depending on the combinations of kwargs: creation mode(nx,xx) and expiration(ex,px).
        E.g. verifying that a non-existent key does not get set if xx=True or gets set with nx=True
        iff it is absent.
        """
        category, existing_key, cases = test_cases
        msg = "Failed in: {}".format(category)
        if existing_key:
            self.redis.set('key', 'value')
        for (key, value, expected_result), config in cases:
            # set with creation mode and expiry options
            result = self.redis.set(key, value, **config)
            eq_(expected_result, result, msg)
            if expected_result is not None:
                # if the set was expected to happen
                self._assert_was_set(key, value, config, msg)
            else:
                # if the set was not expected to happen
                self._assert_not_set(key, value, msg)

    def _assert_not_set(self, key, value, msg):
        """Check that the key and its timeout were not set"""

        # check that the value wasn't updated
        ok_(value != self.redis.get(key), msg)
        if self.redis.exists(key):
            # check that the expiration was not set
            eq_(self.redis.ttl(key), None)
        else:
            # check that the expiration was not set
            eq_(self.redis.ttl(key), -2)

    def _assert_was_set(self, key, value, config, msg, delta=1):
        """Assert that the key was set along with timeout if applicable"""

        eq_(value, self.redis.get(key))
        if "px" not in config and "ex" not in config:
            return
        # px should have been preferred over ex if it was specified
        ttl = self.redis.ttl(key)
        expected_ttl = int(config['px'] / 1000) if "px" in config else config["ex"]
        ok_(expected_ttl - ttl <= delta, msg)

    def test_set_with_options(self):
        """Test the set function with various combinations of arguments"""

        test_cases = [("1. px and ex are set, nx is always true & set on non-existing key",
                      False,
                      [(('key1', 'value1', None), dict(ex=20, px=70000, xx=True, nx=True)),
                      (('key2', 'value1', True), dict(ex=20, px=70000, xx=False, nx=True)),
                      (('key3', 'value2', True), dict(ex=20, px=70000, nx=True))]),

                      ("2. px and ex are set, nx is always true & set on existing key",
                      True,
                      [(('key', 'value1', None), dict(ex=20, px=70000, xx=True, nx=True)),
                      (('key', 'value1', None), dict(ex=20, px=7000, xx=False, nx=True)),
                      (('key', 'value1', None), dict(ex=20, px=70000, nx=True))]),

                      ("3. px and ex are set, xx is always true & set on existing key",
                      True,
                      [(('key', 'value1', None), dict(ex=20, px=70000, xx=True, nx=True)),
                      (('key', 'value1', True), dict(ex=20, px=70000, xx=True, nx=False)),
                      (('key', 'value4', True), dict(ex=20, px=70000, xx=True))]),

                      ("4. px and ex are set, xx is always true & set on non-existing key",
                      False,
                      [(('key1', 'value1', None), dict(ex=20, px=70000, xx=True, nx=True)),
                      (('key2', 'value2', None), dict(ex=20, px=70000, xx=True, nx=False)),
                      (('key3', 'value3', None), dict(ex=20, px=70000, xx=True))]),

                      ("5. either nx or xx defined and set to false or none defined" +
                       " & set on existing key",
                      True,
                      [(('key', 'value1', True), dict(ex=20, px=70000, xx=False)),
                      (('key', 'value2', True), dict(ex=20, px=70000, nx=False)),
                      (('key', 'value3', True), dict(ex=20, px=70000))]),

                      ("6. either nx or xx defined and set to false or none defined" +
                       " & set on non-existing key",
                      False,
                      [(('key1', 'value1', True), dict(ex=20, px=70000, xx=False)),
                      (('key2', 'value2', True), dict(ex=20, px=70000, nx=False)),
                      (('key3', 'value3', True), dict(ex=20, px=70000))]),

                      ("7: where neither px nor ex defined + set on existing key",
                      True,
                      [(('key', 'value2', None), dict(xx=True, nx=True)),
                      (('key', 'value2', None), dict(xx=False, nx=True)),
                      (('key', 'value2', True), dict(xx=True, nx=False)),
                      (('key', 'value3', True), dict(xx=True)),
                      (('key', 'value4', None), dict(nx=True)),
                      (('key', 'value4', True), dict(xx=False)),
                      (('key', 'value5', True), dict(nx=False))]),

                      ("8: where neither px nor ex defined + set on non-existing key",
                      False,
                      [(('key1', 'value1', None), dict(xx=True, nx=True)),
                      (('key2', 'value1', True), dict(xx=False, nx=True)),
                      (('key3', 'value2', None), dict(xx=True, nx=False)),
                      (('key4', 'value3', None), dict(xx=True)),
                      (('key5', 'value4', True), dict(nx=True)),
                      (('key6', 'value4', True), dict(xx=False)),
                      (('key7', 'value5', True), dict(nx=False))]),

                      ("9: where neither nx nor xx defined + set on existing key",
                      True,
                      [(('key', 'value1', True), dict(ex=20, px=70000)),
                      (('key1', 'value12', True), dict(ex=20)),
                      (('key1', 'value11', True), dict(px=20000))]),

                      ("10: where neither nx nor xx is defined + set on non-existing key",
                      False,
                      [(('key1', 'value1', True), dict(ex=20, px=70000)),
                      (('key2', 'value2', True), dict(ex=20)),
                      (('key3', 'value3', True), dict(px=20000))])]

        for cases in test_cases:
            yield self._assert_set_with_options, cases

    def _assert_set_with_timeout(self, seconds):
        """Assert both strict and non-strict that setex sets a key with a value along with a timeout"""

        eq_(None, self.redis_strict.get('key'))
        eq_(None, self.redis.get('key'))

        ok_(self.redis_strict.setex('key', seconds, 'value'))
        ok_(self.redis.setex('key', 'value', seconds))
        eq_('value', self.redis_strict.get('key'))
        eq_('value', self.redis.get('key'))

        ok_(self.redis_strict.ttl('key'), "expiration was not set correctly")
        ok_(self.redis.ttl('key'), "expiration was not set correctly")
        if isinstance(seconds, timedelta):
            seconds = seconds.seconds + seconds.days * 24 * 3600
        ok_(0 < self.redis_strict.ttl('key') <= seconds)
        ok_(0 < self.redis.ttl('key') <= seconds)

    def test_setex(self):
        test_cases = [20, timedelta(seconds=20)]
        for case in test_cases:
            yield self._assert_set_with_timeout, case

    @raises_response_error
    def test_setex_invalid_expiration(self):
        self.redis.setex('key', 'value', -2)

    @raises_response_error
    def test_strict_setex_invalid_expiration(self):
        self.redis_strict.setex('key', -2, 'value')

    @raises_response_error
    def test_setex_zero_expiration(self):
        self.redis.setex('key', 'value', 0)

    @raises_response_error
    def test_strict_setex_zero_expiration(self):
        self.redis_strict.setex('key', 0, 'value')

    def test_mset(self):
        ok_(self.redis.mset({"key1": "hello", "key2": ""}))
        ok_(self.redis.mset(**{"key3": "world", "key2": "there"}))
        eq_(["hello", "there", "world"], self.redis.mget("key1", "key2", "key3"))

    def test_msetnx(self):
        ok_(self.redis.msetnx({"key1": "hello", "key2": "there"}))
        ok_(not self.redis.msetnx(**{"key3": "world", "key2": "there"}))
        eq_(["hello", "there", None], self.redis.mget("key1", "key2", "key3"))

    def test_psetex(self):
        test_cases = [200, timedelta(milliseconds=250)]
        for case in test_cases:
            yield self._assert_set_with_timeout_milliseconds, case

    @raises_response_error
    def test_psetex_invalid_expiration(self):
        self.redis.psetex('key', -20, 'value')

    @raises_response_error
    def test_psetex_zero_expiration(self):
        self.redis.psetex('key', 0, 'value')

    def _assert_set_with_timeout_milliseconds(self, milliseconds):
        """Assert that psetex sets a key with a value along with a timeout"""

        eq_(None, self.redis.get('key'))

        ok_(self.redis.psetex('key', milliseconds, 'value'))
        eq_('value', self.redis.get('key'))

        ok_(self.redis.pttl('key'), "expiration was not set correctly")
        if isinstance(milliseconds, timedelta):
            milliseconds = get_total_milliseconds(milliseconds)

        ok_(0 < self.redis.pttl('key') <= milliseconds)

    def test_setnx(self):
        """Check whether setnx sets a key iff it does not already exist"""

        ok_(self.redis.setnx('key', 'value'))
        ok_(not self.redis.setnx('key', 'different_value'))
        eq_('value', self.redis.get('key'))

    def test_delete(self):
        """Test if delete works"""

        test_cases = [('1', '1'),
                      (('1', '2'), ('1', '2')),
                      (('1', '2', '3'), ('1', '3')),
                      (('1', '2'), '1'),
                      ('1', '2')]
        for case in test_cases:
            yield self._assert_delete, case

    def test_delete_int(self):
        self.redis.set("1", "value")
        eq_(self.redis.delete(1), 1)

    def _assert_delete(self, data):
        """
        Asserts that key(s) deletion along with removing timeouts if any, succeeds as expected
        """
        to_create, to_delete = data
        for key in to_create:
            self.redis.set(key, "value", ex=200)

        eq_(self.redis.delete(*to_delete), len(set(to_create) & set(to_delete)))

        # verify if the keys that were to be deleted, were deleted along with the timeouts.
        for key in set(to_create) & set(to_delete):
            ok_(key not in self.redis)
            eq_(self.redis.ttl(key), -2)

        # verify if the keys not to be deleted, were not deleted and their timeouts not removed.
        for key in set(to_create) - (set(to_create) & set(to_delete)):
            ok_(key in self.redis)
            ok_(self.redis.ttl(key) > 0)

    def test_getset(self):
        eq_(None, self.redis.get('getset_key'))
        eq_(None, self.redis.getset('getset_key', '1'))
        eq_('1', self.redis.getset('getset_key', '2'))
        eq_('2', self.redis.get('getset_key'))

########NEW FILE########
__FILENAME__ = test_zset
from nose.tools import assert_raises, eq_, ok_

from mockredis.tests.fixtures import setup


class TestRedisZset(object):
    """zset tests"""

    def setup(self):
        setup(self)

    def test_zadd(self):
        key = "zset"
        values = [("one", 1), ("uno", 1), ("two", 2), ("three", 3)]
        for member, score in values:
            eq_(1, self.redis.zadd(key, member, score))

    def test_zadd_strict(self):
        """Argument order for zadd depends on strictness"""
        key = "zset"
        values = [("one", 1), ("uno", 1), ("two", 2), ("three", 3)]
        for member, score in values:
            eq_(1, self.redis_strict.zadd(key, score, member))

    def test_zadd_duplicate_key(self):
        key = "zset"
        eq_(1, self.redis.zadd(key, "one", 1.0))
        eq_(0, self.redis.zadd(key, "one", 2.0))

    def test_zadd_wrong_type(self):
        key = "zset"
        self.redis.set(key, "value")
        with assert_raises(Exception):
            self.redis.zadd(key, "one", 2.0)

    def test_zadd_multiple_bad_args(self):
        key = "zset"
        args = ["one", 1, "two"]
        with assert_raises(Exception):
            self.redis.zadd(key, *args)

    def test_zadd_multiple_bad_score(self):
        key = "zset"
        with assert_raises(Exception):
            self.redis.zadd(key, "one", "two")

    def test_zadd_multiple_args(self):
        key = "zset"
        args = ["one", 1, "uno", 1, "two", 2, "three", 3]
        eq_(4, self.redis.zadd(key, *args))

    def test_zadd_multiple_kwargs(self):
        key = "zset"
        kwargs = {"one": 1, "uno": 1, "two": 2, "three": 3}
        eq_(4, self.redis.zadd(key, **kwargs))

    def test_zcard(self):
        key = "zset"
        eq_(0, self.redis.zcard(key))
        self.redis.zadd(key, "one", 1)
        eq_(1, self.redis.zcard(key))
        self.redis.zadd(key, "one", 2)
        eq_(1, self.redis.zcard(key))
        self.redis.zadd(key, "two", 2)
        eq_(2, self.redis.zcard(key))

    def test_zincrby(self):
        key = "zset"
        eq_(1.0, self.redis.zincrby(key, "member1"))
        eq_(2.0, self.redis.zincrby(key, "member2", 2))
        eq_(-1.0, self.redis.zincrby(key, "member1", -2))

    def test_zrange(self):
        key = "zset"
        eq_([], self.redis.zrange(key, 0, -1))
        self.redis.zadd(key, "one", 1.5)
        self.redis.zadd(key, "two", 2.5)
        self.redis.zadd(key, "three", 3.5)

        # full range
        eq_(["one", "two", "three"],
            self.redis.zrange(key, 0, -1))
        # withscores
        eq_([("one", 1.5), ("two", 2.5), ("three", 3.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

        with assert_raises(ValueError):
            # invalid literal for int() with base 10
            self.redis.zrange(key, 0, -1, withscores=True, score_cast_func=int)

        # score_cast_func
        def cast_to_int(score):
            return int(float(score))

        eq_([("one", 1), ("two", 2), ("three", 3)],
            self.redis.zrange(key, 0, -1, withscores=True, score_cast_func=cast_to_int))

        # positive ranges
        eq_(["one"], self.redis.zrange(key, 0, 0))
        eq_(["one", "two"], self.redis.zrange(key, 0, 1))
        eq_(["one", "two", "three"], self.redis.zrange(key, 0, 2))
        eq_(["one", "two", "three"], self.redis.zrange(key, 0, 3))
        eq_(["two", "three"], self.redis.zrange(key, 1, 2))
        eq_(["three"], self.redis.zrange(key, 2, 3))

        # negative ends
        eq_(["one", "two", "three"], self.redis.zrange(key, 0, -1))
        eq_(["one", "two"], self.redis.zrange(key, 0, -2))
        eq_(["one"], self.redis.zrange(key, 0, -3))
        eq_([], self.redis.zrange(key, 0, -4))

        # negative starts
        eq_([], self.redis.zrange(key, -1, 0))
        eq_(["three"], self.redis.zrange(key, -1, -1))
        eq_(["two", "three"], self.redis.zrange(key, -2, -1))
        eq_(["one", "two", "three"], self.redis.zrange(key, -3, -1))
        eq_(["one", "two", "three"], self.redis.zrange(key, -4, -1))

        # desc
        eq_(["three", "two", "one"], self.redis.zrange(key, 0, 2, desc=True))
        eq_(["two", "one"], self.redis.zrange(key, 1, 2, desc=True))
        eq_(["three", "two"], self.redis.zrange(key, 0, 1, desc=True))

    def test_zrem(self):
        key = "zset"
        ok_(not self.redis.zrem(key, "two"))

        self.redis.zadd(key, "one", 1.0)
        eq_(1, self.redis.zcard(key))
        eq_(["zset"], self.redis.keys("*"))

        ok_(self.redis.zrem(key, "one"))
        eq_(0, self.redis.zcard(key))
        eq_([], self.redis.keys("*"))

    def test_zscore(self):
        key = "zset"
        eq_(None, self.redis.zscore(key, "one"))

        self.redis.zadd(key, "one", 1.0)
        eq_(1.0, self.redis.zscore(key, "one"))

    def test_zscore_int_member(self):
        key = "zset"
        eq_(None, self.redis.zscore(key, 1))

        self.redis.zadd(key, 1, 1.0)
        eq_(1.0, self.redis.zscore(key, 1))

    def test_zrank(self):
        key = "zset"
        eq_(None, self.redis.zrank(key, "two"))

        self.redis.zadd(key, "one", 1.0)
        self.redis.zadd(key, "two", 2.0)
        eq_(0, self.redis.zrank(key, "one"))
        eq_(1, self.redis.zrank(key, "two"))

    def test_zrank_int_member(self):
        key = "zset"
        eq_(None, self.redis.zrank(key, 2))

        self.redis.zadd(key, "one", 1.0)
        self.redis.zadd(key, 2, 2.0)
        eq_(0, self.redis.zrank(key, "one"))
        eq_(1, self.redis.zrank(key, 2))

    def test_zcount(self):
        key = "zset"
        eq_(0, self.redis.zcount(key, "-inf", "inf"))

        self.redis.zadd(key, "one", 1.0)
        self.redis.zadd(key, "two", 2.0)

        eq_(2, self.redis.zcount(key, "-inf", "inf"))
        eq_(1, self.redis.zcount(key, "-inf", 1.0))
        eq_(1, self.redis.zcount(key, "-inf", 1.5))
        eq_(2, self.redis.zcount(key, "-inf", 2.0))
        eq_(2, self.redis.zcount(key, "-inf", 2.5))
        eq_(1, self.redis.zcount(key, 0.5, 1.0))
        eq_(1, self.redis.zcount(key, 0.5, 1.5))
        eq_(2, self.redis.zcount(key, 0.5, 2.0))
        eq_(2, self.redis.zcount(key, 0.5, 2.5))
        eq_(2, self.redis.zcount(key, 0.5, "inf"))

        eq_(0, self.redis.zcount(key, "inf", "-inf"))
        eq_(0, self.redis.zcount(key, 2.0, 0.5))

    def test_zrangebyscore(self):
        key = "zset"
        eq_([], self.redis.zrangebyscore(key, "-inf", "inf"))
        self.redis.zadd(key, "one", 1.5)
        self.redis.zadd(key, "two", 2.5)
        self.redis.zadd(key, "three", 3.5)

        eq_(["one", "two", "three"],
            self.redis.zrangebyscore(key, "-inf", "inf"))
        eq_([("one", 1.5), ("two", 2.5), ("three", 3.5)],
            self.redis.zrangebyscore(key, "-inf", "inf", withscores=True))

        with assert_raises(ValueError):
            # invalid literal for int() with base 10
            self.redis.zrangebyscore(key,
                                     "-inf",
                                     "inf",
                                     withscores=True,
                                     score_cast_func=int)

        def cast_score(score):
            return int(float(score))

        eq_([("one", 1), ("two", 2), ("three", 3)],
            self.redis.zrangebyscore(key,
                                     "-inf",
                                     "inf",
                                     withscores=True,
                                     score_cast_func=cast_score))

        eq_(["one"],
            self.redis.zrangebyscore(key, 1.0, 2.0))
        eq_(["one", "two"],
            self.redis.zrangebyscore(key, 1.0, 3.0))
        eq_(["one"],
            self.redis.zrangebyscore(key, 1.0, 3.0, start=0, num=1))
        eq_(["two"],
            self.redis.zrangebyscore(key, 1.0, 3.0, start=1, num=1))
        eq_(["two", "three"],
            self.redis.zrangebyscore(key, 1.0, 3.5, start=1, num=4))
        eq_([],
            self.redis.zrangebyscore(key, 1.0, 3.5, start=3, num=4))

    def test_zrevrank(self):
        key = "zset"
        eq_(None, self.redis.zrevrank(key, "two"))

        self.redis.zadd(key, "one", 1.0)
        self.redis.zadd(key, "two", 2.0)
        eq_(1, self.redis.zrevrank(key, "one"))
        eq_(0, self.redis.zrevrank(key, "two"))

    def test_zrevrangebyscore(self):
        key = "zset"
        eq_([], self.redis.zrevrangebyscore(key, "inf", "-inf"))
        self.redis.zadd(key, "one", 1.5)
        self.redis.zadd(key, "two", 2.5)
        self.redis.zadd(key, "three", 3.5)

        eq_(["three", "two", "one"],
            self.redis.zrevrangebyscore(key, "inf", "-inf"))
        eq_([("three", 3.5), ("two", 2.5), ("one", 1.5)],
            self.redis.zrevrangebyscore(key, "inf", "-inf", withscores=True))

        with assert_raises(ValueError):
            # invalid literal for int() with base 10
            self.redis.zrevrangebyscore(key,
                                        "inf",
                                        "-inf",
                                        withscores=True,
                                        score_cast_func=int)

        def cast_score(score):
            return int(float(score))

        eq_([("three", 3), ("two", 2), ("one", 1)],
            self.redis.zrevrangebyscore(key,
                                        "inf",
                                        "-inf",
                                        withscores=True,
                                        score_cast_func=cast_score))

        eq_(["one"],
            self.redis.zrevrangebyscore(key, 2.0, 1.0))
        eq_(["two", "one"],
            self.redis.zrevrangebyscore(key, 3.0, 1.0))
        eq_(["two"],
            self.redis.zrevrangebyscore(key, 3.0, 1.0, start=0, num=1))
        eq_(["one"],
            self.redis.zrevrangebyscore(key, 3.0, 1.0, start=1, num=1))
        eq_(["two", "one"],
            self.redis.zrevrangebyscore(key, 3.5, 1.0, start=1, num=4))
        eq_([],
            self.redis.zrevrangebyscore(key, 3.5, 1.0, start=3, num=4))

    def test_zremrangebyrank(self):
        key = "zset"
        eq_(0, self.redis.zremrangebyrank(key, 0, -1))

        self.redis.zadd(key, "one", 1.0)
        self.redis.zadd(key, "two", 2.0)
        self.redis.zadd(key, "three", 3.0)

        eq_(2, self.redis.zremrangebyrank(key, 0, 1))

        eq_(["three"], self.redis.zrange(key, 0, -1))
        eq_(1, self.redis.zremrangebyrank(key, 0, -1))

        eq_([], self.redis.zrange(key, 0, -1))
        eq_([], self.redis.keys("*"))

    def test_zremrangebyscore(self):
        key = "zset"
        eq_(0, self.redis.zremrangebyscore(key, "-inf", "inf"))

        self.redis.zadd(key, "one", 1.0)
        self.redis.zadd(key, "two", 2.0)
        self.redis.zadd(key, "three", 3.0)

        eq_(1, self.redis.zremrangebyscore(key, 0, 1))

        eq_(["two", "three"], self.redis.zrange(key, 0, -1))
        eq_(2, self.redis.zremrangebyscore(key, 2.0, "inf"))

        eq_([], self.redis.zrange(key, 0, -1))
        eq_([], self.redis.keys("*"))

    def test_zunionstore_no_keys(self):
        key = "zset"

        eq_(0, self.redis.zunionstore(key, ["zset1", "zset2"]))

    def test_zunionstore_default(self):
        # sum is default
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"]))
        eq_([("one", 1.0), ("three", 3.0), ("two", 4.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zunionstore_sum(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"], aggregate="sum"))
        eq_([("one", 1.0), ("three", 3.0), ("two", 4.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zunionstore_SUM(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"], aggregate="SUM"))
        eq_([("one", 1.0), ("three", 3.0), ("two", 4.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zunionstore_min(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"], aggregate="min"))
        eq_([("one", 1.0), ("two", 2.0), ("three", 3.0)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zunionstore_MIN(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"], aggregate="MIN"))
        eq_([("one", 1.0), ("two", 2.0), ("three", 3.0)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zunionstore_max(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        key = "zset"
        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"], aggregate="max"))
        eq_([("one", 1.0), ("two", 2.5), ("three", 3.0)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zunionstore_MAX(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        key = "zset"
        eq_(3, self.redis.zunionstore(key, ["zset1", "zset2"], aggregate="MAX"))
        eq_([("one", 1.0), ("two", 2.5), ("three", 3.0)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_no_keys(self):
        key = "zset"

        # no keys
        eq_(0, self.redis.zinterstore(key, ["zset1", "zset2"]))

    def test_zinterstore_default(self):
        # sum is default
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"]))
        eq_([("two", 4.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_sum(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"], aggregate="sum"))
        eq_([("two", 4.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_SUM(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"], aggregate="SUM"))
        eq_([("two", 4.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_min(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"], aggregate="min"))
        eq_([("two", 2.0)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_MIN(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"], aggregate="MIN"))
        eq_([("two", 2.0)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_max(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"], aggregate="max"))
        eq_([("two", 2.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

    def test_zinterstore_MAX(self):
        key = "zset"
        self.redis.zadd("zset1", "one", 1.0)
        self.redis.zadd("zset1", "two", 2.0)
        self.redis.zadd("zset2", "two", 2.5)
        self.redis.zadd("zset2", "three", 3.0)

        eq_(1, self.redis.zinterstore(key, ["zset1", "zset2"], aggregate="MAX"))
        eq_([("two", 2.5)],
            self.redis.zrange(key, 0, -1, withscores=True))

########NEW FILE########
