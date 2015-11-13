__FILENAME__ = fakeredis
import random
import warnings
import copy
from ctypes import CDLL, POINTER, c_double, c_char_p, pointer
from ctypes.util import find_library
import fnmatch
from urlparse import urlparse
from collections import MutableMapping
from datetime import datetime, timedelta
import redis
from redis.exceptions import ResponseError
import redis.client


__version__ = '0.4.2'
DATABASES = {}

_libc = CDLL(find_library('c'))
_libc.strtod.restype = c_double
_libc.strtod.argtypes = [c_char_p, POINTER(c_char_p)]
_strtod = _libc.strtod


def timedelta_total_seconds(delta):
    return delta.days * 86400 + delta.seconds + delta.microseconds / 1E6


class _StrKeyDict(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._dict = dict(*args, **kwargs)
        self._ex_keys = {}

    def __getitem__(self, key):
        self._update_expired_keys()
        return self._dict[str(key)]

    def __setitem__(self, key, value):
        self._dict[str(key)] = value

    def __delitem__(self, key):
        del self._dict[str(key)]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def expire(self, key, timestamp):
        self._ex_keys[key] = timestamp

    def expiring(self, key):
        if not key in self._ex_keys.keys():
            return None
        return self._ex_keys[key]

    def _update_expired_keys(self):
        now = datetime.now()
        deleted = []
        for key in self._ex_keys.keys():
            if now > self._ex_keys[key]:
                deleted.append(key)

        for key in deleted:
            del self._ex_keys[key]
            del self[key]

    def copy(self):
        new_copy = _StrKeyDict()
        for key, value in self._dict.items():
            new_copy[key] = value
        return new_copy

    def clear(self):
        super(_StrKeyDict, self).clear()
        self._ex_keys.clear()

    def to_bare_dict(self):
        return copy.deepcopy(self._dict)


class FakeStrictRedis(object):
    @classmethod
    def from_url(cls, url, db=None, **kwargs):
        url = urlparse(url)
        if db is None:
            try:
                db = int(url.path.replace('/', ''))
            except (AttributeError, ValueError):
                db = 0
        return cls(db=db)

    def __init__(self, db=0, **kwargs):
        if db not in DATABASES:
            DATABASES[db] = _StrKeyDict()
        self._db = DATABASES[db]
        self._db_num = db


    def flushdb(self):
        DATABASES[self._db_num].clear()
        return True

    def flushall(self):
        for db in DATABASES:
            DATABASES[db].clear()

    # Basic key commands
    def append(self, key, value):
        self._db[key] += value
        return len(self._db[key])

    def bitcount(self, name, start=0, end=-1):
        if end == -1:
            end = None
        else:
            end += 1
        try:
            s = self._db[name][start:end]
            return sum([bin(ord(l)).count('1') for l in s])
        except KeyError:
            return 0

    def decr(self, name, amount=1):
        try:
            self._db[name] = int(self._db.get(name, '0')) - amount
        except (TypeError, ValueError):
            raise redis.ResponseError("value is not an integer or out of "
                                      "range.")
        return self._db[name]

    def exists(self, name):
        return name in self._db
    __contains__ = exists

    def expire(self, name, time):
        if isinstance(time, timedelta):
            time = int(timedelta_total_seconds(time))
        if self.exists(name):
            self._db.expire(name, datetime.now() + timedelta(seconds=time))
        else:
            return False

    def expireat(self, name, when):
        if not self.exists(name):
            return False
        if isinstance(when, datetime):
            self._db.expire(name, when)
        else:
            self._db.expire(name, datetime.fromtimestamp(when))

    def get(self, name):
        value = self._db.get(name)
        if value is not None:
            return str(value)

    def __getitem__(self, name):
        return self._db[name]

    def getbit(self, name, offset):
        """Returns a boolean indicating the value of ``offset`` in ``name``"""
        val = self._db.get(name, '\x00')
        byte = offset / 8
        remaining = offset % 8
        actual_bitoffset = 7 - remaining
        try:
            actual_val = ord(val[byte])
        except IndexError:
            return 0
        return 1 if (1 << actual_bitoffset) & actual_val else 0

    def getset(self, name, value):
        """
        Set the value at key ``name`` to ``value`` if key doesn't exist
        Return the value at key ``name`` atomically
        """
        val = self._db.get(name)
        if val is None:
            self._db[name] = value
        return val

    def incr(self, name, amount=1):
        """
        Increments the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as ``amount``
        """
        try:
            self._db[name] = int(self._db.get(name, '0')) + amount
        except (TypeError, ValueError):
            raise redis.ResponseError("value is not an integer or out of "
                                      "range.")
        return self._db[name]

    def keys(self, pattern=None):
        return [key for key in self._db.keys()
                if not key or not pattern or fnmatch.fnmatch(key, pattern)]

    def mget(self, keys, *args):
        all_keys = self._list_or_args(keys, args)
        found = []
        for key in all_keys:
            found.append(self._db.get(key))
        return found

    def mset(self, mapping):
        for key, val in mapping.iteritems():
            self.set(key, val)
        return True

    def msetnx(self, mapping):
        """
        Sets each key in the ``mapping`` dict to its corresponding value if
        none of the keys are already set
        """
        if not any(k in self._db for k in mapping):
            for key, val in mapping.iteritems():
                self.set(key, val)
            return True
        return False

    def move(self, name, db):
        pass

    def persist(self, name):
        pass

    def ping(self):
        return True

    def randomkey(self):
        pass

    def rename(self, src, dst):
        try:
            value = self._db[src]
        except KeyError:
            raise redis.ResponseError("No such key: %s" % src)
        self._db[dst] = value
        del self._db[src]
        return True

    def renamenx(self, src, dst):
        if dst in self._db:
            return False
        else:
            return self.rename(src, dst)

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        if (not nx and not xx) \
        or (nx and self._db.get(name, None) is None) \
        or (xx and not self._db.get(name, None) is None):
            if ex > 0:
                self._db.expire(name, datetime.now() + timedelta(seconds=ex))
            elif px > 0:
                self._db.expire(name, datetime.now() + timedelta(milliseconds=px))
            self._db[name] = str(value)
            return True
        else:
            return None

    __setitem__ = set

    def setbit(self, name, offset, value):
        val = self._db.get(name, '\x00')
        byte = offset / 8
        remaining = offset % 8
        actual_bitoffset = 7 - remaining
        if len(val) - 1 < byte:
            # We need to expand val so that we can set the appropriate
            # bit.
            needed = byte - (len(val) - 1)
            val += '\x00' * needed
        if value == 1:
            new_byte = chr(ord(val[byte]) | (1 << actual_bitoffset))
        else:
            new_byte = chr(ord(val[byte]) ^ (1 << actual_bitoffset))
        reconstructed = list(val)
        reconstructed[byte] = new_byte
        self._db[name] = ''.join(reconstructed)

    def setex(self, name, time, value):
        if isinstance(time, timedelta):
            time = int(timedelta_total_seconds(time))
        return self.set(name, value, ex=time)

    def psetex(self, name, time_ms, value):
        if isinstance(time_ms, timedelta):
            time_ms = int(timedelta_total_seconds(time_ms) * 1000)
        if time_ms == 0:
            raise ResponseError("invalid expire time in SETEX")
        return self.set(name, value, px=time_ms)

    def setnx(self, name, value):
        result = self.set(name, value, nx=True)
        # Real Redis returns False from setnx, but None from set(nx=...)
        if not result:
            return False
        return result

    def setrange(self, name, offset, value):
        pass

    def strlen(self, name):
        try:
            return len(self._db[name])
        except KeyError:
            return 0

    def substr(self, name, start, end=-1):
        if end == -1:
            end = None
        else:
            end += 1
        try:
            return self._db[name][start:end]
        except KeyError:
            return ''
    # Redis >= 2.0.0 this command is called getrange
    # according to the docs.
    getrange = substr

    def ttl(self, name):
        if name not in self._db:
            return None

        exp_time = self._db.expiring(name)
        if not exp_time:
            return None

        now = datetime.now()
        if now > exp_time:
            return None
        else:
            return round((exp_time - now).days * 3600 * 24
                         + (exp_time - now).seconds
                         + (exp_time - now).microseconds / 1E6)

    def type(self, name):
        pass

    def watch(self, *names):
        pass

    def unwatch(self):
        pass

    def delete(self, *names):
        deleted = 0
        for name in names:
            try:
                del self._db[name]
                deleted += 1
            except KeyError:
                continue
        return deleted

    def sort(self, name, start=None, num=None, by=None, get=None, desc=False,
             alpha=False, store=None):
        """Sort and return the list, set or sorted set at ``name``.

        ``start`` and ``num`` allow for paging through the sorted data

        ``by`` allows using an external key to weight and sort the items.
            Use an "*" to indicate where in the key the item value is located

        ``get`` allows for returning items from external keys rather than the
            sorted data itself.  Use an "*" to indicate where int he key
            the item value is located

        ``desc`` allows for reversing the sort

        ``alpha`` allows for sorting lexicographically rather than numerically

        ``store`` allows for storing the result of the sort into
            the key ``store``

        """
        if (start is None and num is not None) or \
                (start is not None and num is None):
            raise redis.RedisError(
                "RedisError: ``start`` and ``num`` must both be specified")
        try:
            data = list(self._db[name])[:]
            if by is not None:
                # _sort_using_by_arg mutates data so we don't
                # need need a return value.
                self._sort_using_by_arg(data, by=by)
            elif not alpha:
                data.sort(key=self._strtod_key_func)
            else:
                data.sort()
            if not (start is None and num is None):
                data = data[start:start + num]
            if desc:
                data = list(reversed(data))
            if store is not None:
                self._db[store] = data
                return len(data)
            else:
                return self._retrive_data_from_sort(data, get)
        except KeyError:
            return []

    def _retrive_data_from_sort(self, data, get):
        if get is not None:
            if isinstance(get, basestring):
                get = [get]
            new_data = []
            for k in data:
                for g in get:
                    single_item = self._get_single_item(k, g)
                    new_data.append(single_item)
            data = new_data
        return data

    def _get_single_item(self, k, g):
        if '*' in g:
            g = g.replace('*', k)
            if '->' in g:
                key, hash_key = g.split('->')
                single_item = self._db.get(key, {}).get(hash_key)
            else:
                single_item = self._db.get(g)
        elif '#' in g:
            single_item = k
        else:
            single_item = None
        return single_item

    def _strtod_key_func(self, arg):
        # str()'ing the arg is important! Don't ever remove this.
        arg = str(arg)
        end = c_char_p()
        val = _strtod(arg, pointer(end))
        # real Redis also does an isnan check, not sure if
        # that's needed here or not.
        if end.value:
            raise redis.ResponseError(
                "One or more scores can't be converted into double")
        else:
            return val

    def _sort_using_by_arg(self, data, by):
        def _by_key(arg):
            key = by.replace('*', arg)
            if '->' in by:
                key, hash_key = key.split('->')
                return self._db.get(key, {}).get(hash_key)
            else:
                return self._db.get(key)
        data.sort(key=_by_key)

    def lpush(self, name, *values):
        self._db.setdefault(name, [])[0:0] = list(reversed((values)))
        return len(self._db[name])

    def lrange(self, name, start, end):
        if end == -1:
            end = None
        else:
            end += 1
        return self._db.get(name, [])[start:end]

    def llen(self, name):
        return len(self._db.get(name, []))

    def lrem(self, name, count, value):
        a_list = self._db.get(name, [])
        found = []
        for i, el in enumerate(a_list):
            if el == value:
                found.append(i)
        if count > 0:
            indices_to_remove = found[:count]
        elif count < 0:
            indices_to_remove = found[count:]
        else:
            indices_to_remove = found
        # Iterating in reverse order to ensure the indices
        # remain valid during deletion.
        for index in reversed(indices_to_remove):
            del a_list[index]
        return len(indices_to_remove)

    def rpush(self, name, *values):
        self._db.setdefault(name, []).extend([str(x) for x in values])
        return len(self._db[name])

    def lpop(self, name):
        try:
            return self._db.get(name, []).pop(0)
        except IndexError:
            return None

    def lset(self, name, index, value):
        try:
            self._db.get(name, [])[index] = value
        except IndexError:
            raise redis.ResponseError("index out of range")

    def rpushx(self, name, value):
        try:
            self._db[name].append(value)
        except KeyError:
            return

    def ltrim(self, name, start, end):
        try:
            val = self._db[name]
        except KeyError:
            return True
        if end == -1:
            end = None
        else:
            end += 1
        self._db[name] = val[start:end]
        return True

    def lindex(self, name, index):
        try:
            return self._db.get(name, [])[index]
        except IndexError:
            return None

    def lpushx(self, name, value):
        try:
            self._db[name].insert(0, value)
        except KeyError:
            return

    def rpop(self, name):
        try:
            return self._db.get(name, []).pop()
        except IndexError:
            return None

    def linsert(self, name, where, refvalue, value):
        index = self._db.get(name, []).index(refvalue)
        self._db.get(name, []).insert(index, value)

    def rpoplpush(self, src, dst):
        el = self.rpop(src)
        if el is not None:
            try:
                self._db[dst].insert(0, el)
            except KeyError:
                self._db[dst] = [el]
        return el

    def blpop(self, keys, timeout=0):
        # This has to be a best effort approximation which follows
        # these rules:
        # 1) For each of those keys see if there's something we can
        #    pop from.
        # 2) If this is not the case then simulate a timeout.
        # This means that there's not really any blocking behavior here.
        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)
        for key in keys:
            if self._db.get(key, []):
                return (key, self._db[key].pop(0))

    def brpop(self, keys, timeout=0):
        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)
        for key in keys:
            if self._db.get(key, []):
                return (key, self._db[key].pop())

    def brpoplpush(self, src, dst, timeout=0):
        el = self.rpop(src)
        if el is not None:
            try:
                self._db[dst].insert(0, el)
            except KeyError:
                self._db[dst] = [el]
        return el

    def hdel(self, name, *keys):
        h = self._db.get(name, {})
        rem = 0
        for k in keys:
            if k in h:
                del h[k]
                rem += 1
        return rem

    def hexists(self, name, key):
        "Returns a boolean indicating if ``key`` exists within hash ``name``"
        if self._db.get(name, {}).get(key) is None:
            return 0
        else:
            return 1

    def hget(self, name, key):
        "Return the value of ``key`` within the hash ``name``"
        return self._db.get(name, {}).get(key)

    def hgetall(self, name):
        "Return a Python dict of the hash's name/value pairs"
        all_items = self._db.get(name, {})
        if hasattr(all_items, 'to_bare_dict'):
            all_items = all_items.to_bare_dict()
        return all_items

    def hincrby(self, name, key, amount=1):
        "Increment the value of ``key`` in hash ``name`` by ``amount``"
        new = int(self._db.setdefault(name, _StrKeyDict()).get(key, '0')) + amount
        self._db[name][key] = new
        return new

    def hkeys(self, name):
        "Return the list of keys within hash ``name``"
        return self._db.get(name, {}).keys()

    def hlen(self, name):
        "Return the number of elements in hash ``name``"
        return len(self._db.get(name, {}))

    def hset(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name``
        Returns 1 if HSET created a new field, otherwise 0
        """
        key_is_new = key not in self._db.get(name, {})
        self._db.setdefault(name, _StrKeyDict())[key] = str(value)
        return 1 if key_is_new else 0

    def hsetnx(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name`` if ``key`` does not
        exist.  Returns 1 if HSETNX created a field, otherwise 0.
        """
        if key in self._db.get(name, {}):
            return False
        self._db.setdefault(name, _StrKeyDict())[key] = str(value)
        return True

    def hmset(self, name, mapping):
        """
        Sets each key in the ``mapping`` dict to its corresponding value
        in the hash ``name``
        """
        if not mapping:
            raise redis.DataError("'hmset' with 'mapping' of length 0")
        self._db.setdefault(name, _StrKeyDict()).update(mapping)
        return True

    def hmget(self, name, keys, *args):
        "Returns a list of values ordered identically to ``keys``"
        h = self._db.get(name, {})
        all_keys = self._list_or_args(keys, args)
        return [h.get(k) for k in all_keys]

    def hvals(self, name):
        "Return the list of values within hash ``name``"
        return self._db.get(name, {}).values()

    def sadd(self, name, *values):
        "Add ``value`` to set ``name``"
        a_set = self._db.setdefault(name, set())
        card = len(a_set)
        a_set |= set(values)
        return len(a_set) - card

    def scard(self, name):
        "Return the number of elements in set ``name``"
        return len(self._db.get(name, set()))

    def sdiff(self, keys, *args):
        "Return the difference of sets specified by ``keys``"
        all_keys = self._list_or_args(keys, args)
        diff = self._db.get(all_keys[0], set()).copy()
        for key in all_keys[1:]:
            diff -= self._db.get(key, set())
        return diff

    def sdiffstore(self, dest, keys, *args):
        """
        Store the difference of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        diff = self.sdiff(keys, *args)
        self._db[dest] = diff
        return len(diff)

    def sinter(self, keys, *args):
        "Return the intersection of sets specified by ``keys``"
        all_keys = self._list_or_args(keys, args)
        intersect = self._db.get(all_keys[0], set()).copy()
        for key in all_keys[1:]:
            intersect.intersection_update(self._db.get(key, set()))
        return intersect

    def sinterstore(self, dest, keys, *args):
        """
        Store the intersection of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        intersect = self.sinter(keys, *args)
        self._db[dest] = intersect
        return len(intersect)

    def sismember(self, name, value):
        "Return a boolean indicating if ``value`` is a member of set ``name``"
        return value in self._db.get(name, set())

    def smembers(self, name):
        "Return all members of the set ``name``"
        return self._db.get(name, set())

    def smove(self, src, dst, value):
        try:
            self._db.get(src, set()).remove(value)
            self._db.setdefault(dst, set()).add(value)
            return True
        except KeyError:
            return False

    def spop(self, name):
        "Remove and return a random member of set ``name``"
        try:
            return self._db.get(name, set()).pop()
        except KeyError:
            return None

    def srandmember(self, name):
        "Return a random member of set ``name``"
        members = self._db.get(name, set())
        if members:
            index = random.randint(0, len(members) - 1)
            return list(members)[index]

    def srem(self, name, *values):
        "Remove ``value`` from set ``name``"
        a_set = self._db.setdefault(name, set())
        card = len(a_set)
        a_set -= set(values)
        return card - len(a_set)

    def sunion(self, keys, *args):
        "Return the union of sets specifiued by ``keys``"
        all_keys = self._list_or_args(keys, args)
        union = self._db.get(all_keys[0], set()).copy()
        for key in all_keys[1:]:
            union.update(self._db.get(key, set()))
        return union

    def sunionstore(self, dest, keys, *args):
        """
        Store the union of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        union = self.sunion(keys, *args)
        self._db[dest] = union
        return len(union)

    def zadd(self, name, *args, **kwargs):
        """
        Set any number of score, element-name pairs to the key ``name``. Pairs
        can be specified in two ways:

        As *args, in the form of: score1, name1, score2, name2, ...
        or as **kwargs, in the form of: name1=score1, name2=score2, ...

        The following example would add four values to the 'my-key' key:
        redis.zadd('my-key', 1.1, 'name1', 2.2, 'name2', name3=3.3, name4=4.4)
        """
        if len(args) % 2 != 0:
            raise redis.RedisError("ZADD requires an equal number of "
                                   "values and scores")
        zset = self._db.setdefault(name, _StrKeyDict())
        added = 0
        for score, value in zip(*[args[i::2] for i in range(2)]):
            if value not in zset:
                added += 1
            try:
                zset[value] = float(score)
            except ValueError:
                raise redis.ResponseError("value is not a valid float")
        for value, score in kwargs.items():
            if value not in zset:
                added += 1
            try:
                zset[value] = float(score)
            except ValueError:
                raise redis.ResponseError("value is not a valid float")
        return added

    def zcard(self, name):
        "Return the number of elements in the sorted set ``name``"
        return len(self._db.get(name, {}))

    def zcount(self, name, min, max):
        found = 0
        for score in self._db.get(name, {}).values():
            if min <= score <= max:
                found += 1
        return found

    def zincrby(self, name, value, amount=1):
        "Increment the score of ``value`` in sorted set ``name`` by ``amount``"
        d = self._db.setdefault(name, _StrKeyDict())
        score = d.get(value, 0) + amount
        d[value] = score
        return score

    def zinterstore(self, dest, keys, aggregate=None):
        """
        Intersect multiple sorted sets specified by ``keys`` into
        a new sorted set, ``dest``. Scores in the destination will be
        aggregated based on the ``aggregate``, or SUM if none is provided.
        """
        if not keys:
            raise redis.ResponseError("At least one key must be specified "
                                      "for ZINTERSTORE/ZUNIONSTORE")
        # keys can be a list or a dict so it needs to be converted to
        # a list first.
        list_keys = list(keys)
        valid_keys = set(self._db.get(list_keys[0], {}))
        for key in list_keys[1:]:
            valid_keys.intersection_update(self._db.get(key, {}))
        return self._zaggregate(dest, keys, aggregate,
                                lambda x: x in
                                valid_keys)

    def zrange(self, name, start, end, desc=False, withscores=False):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``end`` sorted in ascending order.

        ``start`` and ``end`` can be negative, indicating the end of the range.

        ``desc`` indicates to sort in descending order.

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs
        """
        if end == -1:
            end = None
        else:
            end += 1
        all_items = self._db.get(name, {})
        if desc:
            reverse = True
        else:
            reverse = False
        in_order = self._get_zelements_in_order(all_items, reverse)
        items = in_order[start:end]
        if not withscores:
            return items
        else:
            return [(k, all_items[k]) for k in items]

    def _get_zelements_in_order(self, all_items, reverse=False):
        by_keyname = sorted(all_items.items(), key=lambda x: x[0], reverse=reverse)
        in_order = sorted(by_keyname, key=lambda x: x[1], reverse=reverse)
        return [el[0] for el in in_order]

    def zrangebyscore(self, name, min, max,
                      start=None, num=None, withscores=False):
        """
        Return a range of values from the sorted set ``name`` with scores
        between ``min`` and ``max``.

        If ``start`` and ``num`` are specified, then return a slice
        of the range.

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs
        """
        return self._zrangebyscore(name, min, max, start, num, withscores,
                                   reverse=False)

    def _zrangebyscore(self, name, min, max, start, num, withscores, reverse):
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise redis.RedisError("``start`` and ``num`` must both "
                                   "be specified")
        all_items = self._db.get(name, {})
        in_order = self._get_zelements_in_order(all_items, reverse=reverse)
        matches = []
        for item in in_order:
            if min <= all_items[item] <= max:
                matches.append(item)
        if start is not None:
            matches = matches[start:start + num]
        if withscores:
            return [(k, all_items[k]) for k in matches]
        return matches

    def zrank(self, name, value):
        """
        Returns a 0-based value indicating the rank of ``value`` in sorted set
        ``name``
        """
        all_items = self._db.get(name, {})
        in_order = sorted(all_items, key=lambda x: all_items[x])
        try:
            return in_order.index(value)
        except ValueError:
            return None

    def zrem(self, name, *values):
        "Remove member ``value`` from sorted set ``name``"
        z = self._db.get(name, {})
        rem = 0
        for v in values:
            if v in z:
                del z[v]
                rem += 1
        return rem

    def zremrangebyrank(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with ranks between
        ``min`` and ``max``. Values are 0-based, ordered from smallest score
        to largest. Values can be negative indicating the highest scores.
        Returns the number of elements removed
        """
        all_items = self._db.get(name, {})
        in_order = self._get_zelements_in_order(all_items)
        num_deleted = 0
        if max == -1:
            max = None
        else:
            max += 1
        for key in in_order[min:max]:
            del all_items[key]
            num_deleted += 1
        return num_deleted

    def zremrangebyscore(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with scores
        between ``min`` and ``max``. Returns the number of elements removed.
        """
        all_items = self._db.get(name, {})
        removed = 0
        for key in all_items.copy():
            if min <= all_items[key] <= max:
                del all_items[key]
                removed += 1
        return removed

    def zrevrange(self, name, start, num, withscores=False):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``num`` sorted in descending order.

        ``start`` and ``num`` can be negative, indicating the end of the range.

        ``withscores`` indicates to return the scores along with the values
        The return type is a list of (value, score) pairs
        """
        return self.zrange(name, start, num, True, withscores)

    def zrevrangebyscore(self, name, max, min,
                         start=None, num=None, withscores=False):
        """
        Return a range of values from the sorted set ``name`` with scores
        between ``min`` and ``max`` in descending order.

        If ``start`` and ``num`` are specified, then return a slice
        of the range.

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs
        """
        return self._zrangebyscore(name, min, max, start, num, withscores,
                                   reverse=True)

    def zrevrank(self, name, value):
        """
        Returns a 0-based value indicating the descending rank of
        ``value`` in sorted set ``name``
        """
        num_items = len(self._db.get(name, {}))
        zrank = self.zrank(name, value)
        if zrank is not None:
            return num_items - self.zrank(name, value) - 1

    def zscore(self, name, value):
        "Return the score of element ``value`` in sorted set ``name``"
        try:
            return self._db[name][value]
        except KeyError:
            return None

    def zunionstore(self, dest, keys, aggregate=None):
        """
        Union multiple sorted sets specified by ``keys`` into
        a new sorted set, ``dest``. Scores in the destination will be
        aggregated based on the ``aggregate``, or SUM if none is provided.
        """
        if not keys:
            raise redis.ResponseError("At least one key must be specified "
                                      "for ZINTERSTORE/ZUNIONSTORE")
        self._zaggregate(dest, keys, aggregate, lambda x: True)

    def _zaggregate(self, dest, keys, aggregate, should_include):
        new_zset = _StrKeyDict()
        if aggregate is None:
            aggregate = 'SUM'
        # This is what the actual redis client uses, so we'll use
        # the same type check.
        if isinstance(keys, dict):
            keys_weights = [(k, keys[k]) for k in keys]
        else:
            keys_weights = [(k, 1) for k in keys]
        for key, weight in keys_weights:
            current_zset = self._db.get(key, {})
            if isinstance(current_zset, set):
                # When casting set to zset redis uses a default score of 1.0
                current_zset = dict((k, 1.0) for k in current_zset)
            for el in current_zset:
                if not should_include(el):
                    continue
                if el not in new_zset:
                    new_zset[el] = current_zset[el] * weight
                elif aggregate == 'SUM':
                    new_zset[el] += current_zset[el] * weight
                elif aggregate == 'MAX':
                    new_zset[el] = max([new_zset[el],
                                        current_zset[el] * weight])
                elif aggregate == 'MIN':
                    new_zset[el] = min([new_zset[el],
                                        current_zset[el] * weight])
        self._db[dest] = new_zset

    def _list_or_args(self, keys, args):
        # Based off of list_or_args from redis-py.
        # Returns a single list combining keys and args.
        # A string can be iterated, but indicates
        # keys wasn't passed as a list.
        if isinstance(keys, basestring):
            keys = [keys]
        if args:
            keys.extend(args)
        return keys

    def pipeline(self, transaction=True):
        """Return an object that can be used to issue Redis commands in a batch.

        Arguments --
            transaction (bool) -- whether the buffered commands
                are issued atomically. True by default.
        """
        return FakePipeline(self, transaction)

    def transaction(self, func, *keys):
        # We use a for loop instead of while
        # because if the test this is being used in
        # goes wrong we don't want an infinite loop!
        with self.pipeline() as p:
            for _ in range(5):
                try:
                    p.watch(*keys)
                    func(p)
                    return p.execute()
                except redis.WatchError:
                    continue
        raise redis.WatchError('Could not run transaction after 5 tries')


class FakeRedis(FakeStrictRedis):
    def setex(self, name, value, time):
        return super(FakeRedis, self).setex(name, time, value)

    def lrem(self, name, value, num=0):
        return super(FakeRedis, self).lrem(name, num, value)

    def zadd(self, name, value=None, score=None, **pairs):
        """
        For each kwarg in ``pairs``, add that item and it's score to the
        sorted set ``name``.

        The ``value`` and ``score`` arguments are deprecated.
        """
        if value is not None or score is not None:
            if value is None or score is None:
                raise redis.RedisError(
                    "Both 'value' and 'score' must be specified to ZADD")
            warnings.warn(DeprecationWarning(
                "Passing 'value' and 'score' has been deprecated. "
                "Please pass via kwargs instead."))
        else:
            value = pairs.keys()[0]
            score = pairs.values()[0]
        self._db.setdefault(name, _StrKeyDict())[value] = score


class FakePipeline(object):
    """Helper class for FakeStrictRedis to implement pipelines.

    A pipeline is a collection of commands that
    are buffered until you call ``execute``, at which
    point they are called sequentially and a list
    of their return values is returned.

    """
    def __init__(self, owner, transaction=True):
        """Create a pipeline for the specified FakeStrictRedis instance.

        Arguments --
            owner -- a FakeStrictRedis instance.

        """
        self.owner = owner
        self.transaction = transaction
        self.commands = []
        self.need_reset = False
        self.is_immediate = False
        self.watching = {}

    def __getattr__(self, name):
        """Magic method to allow FakeStrictRedis commands to be called.

        Returns a method that records the command for later.

        """
        if not hasattr(self.owner, name):
            raise AttributeError('%r: does not have attribute %r' %
                                 (self.owner, name))

        def meth(*args, **kwargs):
            if self.is_immediate:
                # Special mode during watch_multi sequence.
                return getattr(self.owner, name)(*args, **kwargs)
            self.commands.append((name, args, kwargs))
            return self

        setattr(self, name, meth)
        return meth

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.reset()

    def execute(self):
        """Run all the commands in the pipeline and return the results."""
        if self.watching:
            mismatches = [
                (k, v, u) for (k, v, u) in
                [(k, v, self.owner._db.get(k))
                    for (k, v) in self.watching.items()]
                if v != u]
            if mismatches:
                self.commands = []
                self.watching = {}
                raise redis.WatchError(
                    'Watched key%s %s changed' % (
                        '' if len(mismatches) == 1 else
                        's', ', '.join(k for (k, _, _) in mismatches)))
        ret = [getattr(self.owner, name)(*args, **kwargs)
               for name, args, kwargs in self.commands]
        self.commands = []
        self.watching = {}
        return ret

    def watch(self, *keys):
        self.watching.update((key, copy.deepcopy(self.owner._db.get(key)))
                             for key in keys)
        self.need_reset = True
        self.is_immediate = True

    def multi(self):
        self.is_immediate = False

    def reset(self):
        self.need_reset = False

########NEW FILE########
__FILENAME__ = test_fakeredis
#!/usr/bin/env python
from time import sleep, time
from redis.exceptions import ResponseError
import unittest2 as unittest
import inspect
from functools import wraps

from nose.plugins.skip import SkipTest
from nose.plugins.attrib import attr
import redis
import redis.client

import fakeredis
from datetime import datetime, timedelta


def redis_must_be_running(cls):
    # This can probably be improved.  This will determines
    # at import time if the tests should be run, but we probably
    # want it to be when the tests are actually run.
    try:
        r = redis.StrictRedis('localhost', port=6379)
        r.ping()
    except redis.ConnectionError:
        redis_running = False
    else:
        redis_running = True
    if not redis_running:
        for name, attr in inspect.getmembers(cls):
            if name.startswith('test_'):
                @wraps(attr)
                def skip_test(*args, **kwargs):
                    raise SkipTest("Redis is not running.")
                setattr(cls, name, skip_test)
        cls.setUp = lambda x: None
        cls.tearDown = lambda x: None
    return cls


class TestFakeStrictRedis(unittest.TestCase):
    def setUp(self):
        self.redis = self.create_redis()

    def tearDown(self):
        self.redis.flushall()
        del self.redis

    def create_redis(self, db=0):
        return fakeredis.FakeStrictRedis(db=db)

    def test_flushdb(self):
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.keys(), ['foo'])
        self.assertEqual(self.redis.flushdb(), True)
        self.assertEqual(self.redis.keys(), [])

    def test_set_then_get(self):
        self.assertEqual(self.redis.set('foo', 'bar'), True)
        self.assertEqual(self.redis.get('foo'), 'bar')

    def test_get_does_not_exist(self):
        self.assertEqual(self.redis.get('foo'), None)

    def test_get_with_non_str_keys(self):
        self.assertEqual(self.redis.set('2', 'bar'), True)
        self.assertEqual(self.redis.get(2), 'bar')

    def test_set_non_str_keys(self):
        self.assertEqual(self.redis.set(2, 'bar'), True)
        self.assertEqual(self.redis.get(2), 'bar')
        self.assertEqual(self.redis.get('2'), 'bar')

    def test_getbit(self):
        self.redis.setbit('foo', 3, 1)
        self.assertEqual(self.redis.getbit('foo', 0), 0)
        self.assertEqual(self.redis.getbit('foo', 1), 0)
        self.assertEqual(self.redis.getbit('foo', 2), 0)
        self.assertEqual(self.redis.getbit('foo', 3), 1)
        self.assertEqual(self.redis.getbit('foo', 4), 0)
        self.assertEqual(self.redis.getbit('foo', 100), 0)

    def test_multiple_bits_set(self):
        self.redis.setbit('foo', 1, 1)
        self.redis.setbit('foo', 3, 1)
        self.redis.setbit('foo', 5, 1)

        self.assertEqual(self.redis.getbit('foo', 0), 0)
        self.assertEqual(self.redis.getbit('foo', 1), 1)
        self.assertEqual(self.redis.getbit('foo', 2), 0)
        self.assertEqual(self.redis.getbit('foo', 3), 1)
        self.assertEqual(self.redis.getbit('foo', 4), 0)
        self.assertEqual(self.redis.getbit('foo', 5), 1)
        self.assertEqual(self.redis.getbit('foo', 6), 0)

    def test_unset_bits(self):
        self.redis.setbit('foo', 1, 1)
        self.redis.setbit('foo', 2, 0)
        self.redis.setbit('foo', 3, 1)
        self.assertEqual(self.redis.getbit('foo', 1), 1)
        self.redis.setbit('foo', 1, 0)
        self.assertEqual(self.redis.getbit('foo', 1), 0)
        self.redis.setbit('foo', 3, 0)
        self.assertEqual(self.redis.getbit('foo', 3), 0)

    def test_setbits_and_getkeys(self):
        # The bit operations and the get commands
        # should play nicely with each other.
        self.redis.setbit('foo', 1, 1)
        self.assertEqual(self.redis.get('foo'), '@')
        self.redis.setbit('foo', 2, 1)
        self.assertEqual(self.redis.get('foo'), '`')
        self.redis.setbit('foo', 3, 1)
        self.assertEqual(self.redis.get('foo'), 'p')
        self.redis.setbit('foo', 9, 1)
        self.assertEqual(self.redis.get('foo'), 'p@')
        self.redis.setbit('foo', 54, 1)
        self.assertEqual(self.redis.get('foo'), 'p@\x00\x00\x00\x00\x02')

    def test_bitcount(self):
        self.redis.delete('foo')
        self.assertEqual(self.redis.bitcount('foo'), 0)
        self.redis.setbit('foo', 1, 1)
        self.assertEqual(self.redis.bitcount('foo'), 1)
        self.redis.setbit('foo', 8, 1)
        self.assertEqual(self.redis.bitcount('foo'), 2)
        self.assertEqual(self.redis.bitcount('foo', 1, 1), 1)
        self.redis.setbit('foo', 57, 1)
        self.assertEqual(self.redis.bitcount('foo'), 3)
        self.redis.set('foo', ' ')
        self.assertEqual(self.redis.bitcount('foo'), 1)

    def test_getset_not_exist(self):
        val = self.redis.getset('foo', 'bar')
        self.assertEqual(val, None)
        self.assertEqual(self.redis.get('foo'), 'bar')

    def test_getset_exists(self):
        self.redis.set('foo', 'bar')
        val = self.redis.getset('foo', 'baz')
        self.assertEqual(val, 'bar')

    def test_setitem_getitem(self):
        self.assertEqual(self.redis.keys(), [])
        self.redis['foo'] = 'bar'
        self.assertEqual(self.redis['foo'], 'bar')

    def test_strlen(self):
        self.redis['foo'] = 'bar'

        self.assertEqual(self.redis.strlen('foo'), 3)
        self.assertEqual(self.redis.strlen('noexists'), 0)

    def test_substr(self):
        self.redis['foo'] = 'one_two_three'
        self.assertEqual(self.redis.substr('foo', 0), 'one_two_three')
        self.assertEqual(self.redis.substr('foo', 0, 2), 'one')
        self.assertEqual(self.redis.substr('foo', 4, 6), 'two')
        self.assertEqual(self.redis.substr('foo', -5), 'three')

    def test_substr_noexist_key(self):
        self.assertEqual(self.redis.substr('foo', 0), '')
        self.assertEqual(self.redis.substr('foo', 10), '')
        self.assertEqual(self.redis.substr('foo', -5, -1), '')

    def test_append(self):
        self.assertTrue(self.redis.set('foo', 'bar'))
        self.assertEqual(self.redis.append('foo', 'baz'), 6)
        self.assertEqual(self.redis.get('foo'), 'barbaz')

    def test_incr_with_no_preexisting_key(self):
        self.assertEqual(self.redis.incr('foo'), 1)
        self.assertEqual(self.redis.incr('bar', 2), 2)

    def test_incr_preexisting_key(self):
        self.redis.set('foo', 15)
        self.assertEqual(self.redis.incr('foo', 5), 20)
        self.assertEqual(self.redis.get('foo'), '20')

    def test_incr_bad_type(self):
        self.redis.set('foo', 'bar')
        with self.assertRaises(redis.ResponseError):
            self.redis.incr('foo', 15)

    def test_decr(self):
        self.redis.set('foo', 10)
        self.assertEqual(self.redis.decr('foo'), 9)
        self.assertEqual(self.redis.get('foo'), '9')

    def test_decr_newkey(self):
        self.redis.decr('foo')
        self.assertEqual(self.redis.get('foo'), '-1')

    def test_decr_badtype(self):
        self.redis.set('foo', 'bar')
        with self.assertRaises(redis.ResponseError):
            self.redis.decr('foo', 15)

    def test_exists(self):
        self.assertFalse('foo' in self.redis)
        self.redis.set('foo', 'bar')
        self.assertTrue('foo' in self.redis)

    def test_contains(self):
        self.assertFalse(self.redis.exists('foo'))
        self.redis.set('foo', 'bar')
        self.assertTrue(self.redis.exists('foo'))

    def test_rename(self):
        self.redis.set('foo', 'unique value')
        self.assertTrue(self.redis.rename('foo', 'bar'))
        self.assertEqual(self.redis.get('foo'), None)
        self.assertEqual(self.redis.get('bar'), 'unique value')

    def test_rename_nonexistent_key(self):
        with self.assertRaises(redis.ResponseError):
            self.redis.rename('foo', 'bar')

    def test_renamenx_doesnt_exist(self):
        self.redis.set('foo', 'unique value')
        self.assertTrue(self.redis.renamenx('foo', 'bar'))
        self.assertEqual(self.redis.get('foo'), None)
        self.assertEqual(self.redis.get('bar'), 'unique value')

    def test_rename_does_exist(self):
        self.redis.set('foo', 'unique value')
        self.redis.set('bar', 'unique value2')
        self.assertFalse(self.redis.renamenx('foo', 'bar'))
        self.assertEqual(self.redis.get('foo'), 'unique value')
        self.assertEqual(self.redis.get('bar'), 'unique value2')

    def test_mget(self):
        self.redis.set('foo', 'one')
        self.redis.set('bar', 'two')
        self.assertEqual(self.redis.mget(['foo', 'bar']), ['one', 'two'])
        self.assertEqual(self.redis.mget(['foo', 'bar', 'baz']),
                         ['one', 'two', None])
        self.assertEqual(self.redis.mget('foo', 'bar'), ['one', 'two'])
        self.assertEqual(self.redis.mget('foo', 'bar', None),
                         ['one', 'two', None])

    def test_mset(self):
        self.assertEqual(self.redis.mset({'foo': 'one', 'bar': 'two'}), True)
        self.assertEqual(self.redis.mset({'foo': 'one', 'bar': 'two'}), True)
        self.assertEqual(self.redis.mget('foo', 'bar'), ['one', 'two'])

    def test_msetnx(self):
        self.assertEqual(self.redis.msetnx({'foo': 'one', 'bar': 'two'}),
                         True)
        self.assertEqual(self.redis.msetnx({'bar': 'two', 'baz': 'three'}),
                         False)
        self.assertEqual(self.redis.mget('foo', 'bar', 'baz'),
                         ['one', 'two', None])

    def test_setex(self):
        self.assertEqual(self.redis.setex('foo', 100, 'bar'), True)
        self.assertEqual(self.redis.get('foo'), 'bar')

    def test_setex_using_timedelta(self):
        self.assertEqual(self.redis.setex('foo', timedelta(seconds=100), 'bar'), True)
        self.assertEqual(self.redis.get('foo'), 'bar')

    def test_setnx(self):
        self.assertEqual(self.redis.setnx('foo', 'bar'), True)
        self.assertEqual(self.redis.get('foo'),  'bar')
        self.assertEqual(self.redis.setnx('foo', 'baz'), False)
        self.assertEqual(self.redis.get('foo'),  'bar')

    def test_delete(self):
        self.redis['foo'] = 'bar'
        self.assertEqual(self.redis.delete('foo'), True)
        self.assertEqual(self.redis.get('foo'), None)

    def test_delete_multiple(self):
        self.redis['one'] = 'one'
        self.redis['two'] = 'two'
        self.redis['three'] = 'three'
        # Since redis>=2.7.6 returns number of deleted items.
        self.assertEqual(self.redis.delete('one', 'two'), 2)
        self.assertEqual(self.redis.get('one'), None)
        self.assertEqual(self.redis.get('two'), None)
        self.assertEqual(self.redis.get('three'), 'three')
        self.assertEqual(self.redis.delete('one', 'two'), False)
        # If any keys are deleted, True is returned.
        self.assertEqual(self.redis.delete('two', 'three'), True)
        self.assertEqual(self.redis.get('three'), None)

    def test_delete_nonexistent_key(self):
        self.assertEqual(self.redis.delete('foo'), False)

    ## Tests for the list type.

    def test_rpush_then_lrange_with_nested_list1(self):
        self.assertEqual(self.redis.rpush('foo', [12345L, 6789L]), 1)
        self.assertEqual(self.redis.rpush('foo', [54321L, 9876L]), 2)
        self.assertEqual(self.redis.lrange(
            'foo', 0, -1), ['[12345L, 6789L]', '[54321L, 9876L]'])
        self.redis.flushall()

    def test_rpush_then_lrange_with_nested_list2(self):
        self.assertEqual(self.redis.rpush('foo', [12345L, 'banana']), 1)
        self.assertEqual(self.redis.rpush('foo', [54321L, 'elephant']), 2)
        self.assertEqual(self.redis.lrange(
            'foo', 0, -1), ['[12345L, \'banana\']', '[54321L, \'elephant\']'])
        self.redis.flushall()

    def test_rpush_then_lrange_with_nested_list3(self):
        self.assertEqual(self.redis.rpush('foo', [12345L, []]), 1)
        self.assertEqual(self.redis.rpush('foo', [54321L, []]), 2)
        self.assertEqual(self.redis.lrange(
            'foo', 0, -1), ['[12345L, []]', '[54321L, []]'])
        self.redis.flushall()

    def test_lpush_then_lrange_all(self):
        self.assertEqual(self.redis.lpush('foo', 'bar'), 1)
        self.assertEqual(self.redis.lpush('foo', 'baz'), 2)
        self.assertEqual(self.redis.lpush('foo', 'bam', 'buzz'), 4)
        self.assertEqual(self.redis.lrange('foo', 0, -1),
                         ['buzz', 'bam', 'baz', 'bar'])

    def test_lpush_then_lrange_portion(self):
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'two')
        self.redis.lpush('foo', 'three')
        self.redis.lpush('foo', 'four')
        self.assertEqual(self.redis.lrange('foo', 0, 2),
                         ['four', 'three', 'two'])
        self.assertEqual(self.redis.lrange('foo', 0, 3),
                         ['four', 'three', 'two', 'one'])

    def test_lpush_key_does_not_exist(self):
        self.assertEqual(self.redis.lrange('foo', 0, -1), [])

    def test_lpush_with_nonstr_key(self):
        self.redis.lpush(1, 'one')
        self.redis.lpush(1, 'two')
        self.redis.lpush(1, 'three')
        self.assertEqual(self.redis.lrange(1, 0, 2),
                         ['three', 'two', 'one'])
        self.assertEqual(self.redis.lrange('1', 0, 2),
                         ['three', 'two', 'one'])

    def test_llen(self):
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'two')
        self.redis.lpush('foo', 'three')
        self.assertEqual(self.redis.llen('foo'), 3)

    def test_llen_no_exist(self):
        self.assertEqual(self.redis.llen('foo'), 0)

    def test_lrem_postitive_count(self):
        self.redis.lpush('foo', 'same')
        self.redis.lpush('foo', 'same')
        self.redis.lpush('foo', 'different')
        self.redis.lrem('foo', 2, 'same')
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['different'])

    def test_lrem_negative_count(self):
        self.redis.lpush('foo', 'removeme')
        self.redis.lpush('foo', 'three')
        self.redis.lpush('foo', 'two')
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'removeme')
        self.redis.lrem('foo', -1, 'removeme')
        # Should remove it from the end of the list,
        # leaving the 'removeme' from the front of the list alone.
        self.assertEqual(self.redis.lrange('foo', 0, -1),
                         ['removeme', 'one', 'two', 'three'])

    def test_lrem_zero_count(self):
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lrem('foo', 0, 'one')
        self.assertEqual(self.redis.lrange('foo', 0, -1), [])

    def test_lrem_default_value(self):
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lrem('foo', 0, 'one')
        self.assertEqual(self.redis.lrange('foo', 0, -1), [])

    def test_lrem_does_not_exist(self):
        self.redis.lpush('foo', 'one')
        self.redis.lrem('foo', 0, 'one')
        # These should be noops.
        self.redis.lrem('foo', -2, 'one')
        self.redis.lrem('foo', 2, 'one')

    def test_lrem_return_value(self):
        self.redis.lpush('foo', 'one')
        count = self.redis.lrem('foo', 0, 'one')
        self.assertEqual(count, 1)
        self.assertEqual(self.redis.lrem('foo', 0, 'one'), 0)

    def test_rpush(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.redis.rpush('foo', 'three')
        self.redis.rpush('foo', 'four', 'five')
        self.assertEqual(self.redis.lrange('foo', 0, -1),
                         ['one', 'two', 'three', 'four', 'five'])

    def test_lpop(self):
        self.assertEqual(self.redis.rpush('foo', 'one'), 1)
        self.assertEqual(self.redis.rpush('foo', 'two'), 2)
        self.assertEqual(self.redis.rpush('foo', 'three'), 3)
        self.assertEqual(self.redis.lpop('foo'), 'one')
        self.assertEqual(self.redis.lpop('foo'), 'two')
        self.assertEqual(self.redis.lpop('foo'), 'three')

    def test_lpop_empty_list(self):
        self.redis.rpush('foo', 'one')
        self.redis.lpop('foo')
        self.assertEqual(self.redis.lpop('foo'), None)
        # Verify what happens if we try to pop from a key
        # we've never seen before.
        self.assertEqual(self.redis.lpop('noexists'), None)

    def test_lset(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.redis.rpush('foo', 'three')
        self.redis.lset('foo', 0, 'four')
        self.redis.lset('foo', -2, 'five')
        self.assertEqual(self.redis.lrange('foo', 0, -1),
                         ['four', 'five', 'three'])

    def test_lset_index_out_of_range(self):
        self.redis.rpush('foo', 'one')
        with self.assertRaises(redis.ResponseError):
            self.redis.lset('foo', 3, 'three')

    def test_rpushx(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpushx('foo', 'two')
        self.redis.rpushx('bar', 'three')
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['one', 'two'])
        self.assertEqual(self.redis.lrange('bar', 0, -1), [])

    def test_ltrim(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.redis.rpush('foo', 'three')
        self.redis.rpush('foo', 'four')

        self.assertTrue(self.redis.ltrim('foo', 1, 3))
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['two', 'three',
                                                           'four'])
        self.assertTrue(self.redis.ltrim('foo', 1, -1))
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['three', 'four'])

    def test_ltrim_with_non_existent_key(self):
        self.assertTrue(self.redis.ltrim('foo', 0, -1))

    def test_lindex(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.assertEqual(self.redis.lindex('foo', 0), 'one')
        self.assertEqual(self.redis.lindex('foo', 4), None)
        self.assertEqual(self.redis.lindex('bar', 4), None)

    def test_lpushx(self):
        self.redis.lpush('foo', 'two')
        self.redis.lpushx('foo', 'one')
        self.redis.lpushx('bar', 'one')
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['one', 'two'])
        self.assertEqual(self.redis.lrange('bar', 0, -1), [])

    def test_rpop(self):
        self.assertEqual(self.redis.rpop('foo'), None)
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.assertEqual(self.redis.rpop('foo'), 'two')
        self.assertEqual(self.redis.rpop('foo'), 'one')
        self.assertEqual(self.redis.rpop('foo'), None)

    def test_linsert(self):
        self.redis.rpush('foo', 'hello')
        self.redis.rpush('foo', 'world')
        self.redis.linsert('foo', 'before', 'world', 'there')
        self.assertEqual(self.redis.lrange('foo', 0, -1),
                         ['hello', 'there', 'world'])

    def test_rpoplpush(self):
        self.assertEqual(self.redis.rpoplpush('foo', 'bar'), None)
        self.assertEqual(self.redis.lpop('bar'), None)
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.redis.rpush('bar', 'one')

        self.assertEqual(self.redis.rpoplpush('foo', 'bar'), 'two')
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['one'])
        self.assertEqual(self.redis.lrange('bar', 0, -1), ['two', 'one'])

    def test_rpoplpush_to_nonexistent_destination(self):
        self.redis.rpush('foo', 'one')
        self.assertEqual(self.redis.rpoplpush('foo', 'bar'), 'one')
        self.assertEqual(self.redis.rpop('bar'), 'one')

    def test_blpop_single_list(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.redis.rpush('foo', 'three')
        self.assertEqual(self.redis.blpop(['foo'], timeout=1),
                         ('foo', 'one'))

    def test_blpop_test_multiple_lists(self):
        self.redis.rpush('baz', 'zero')
        self.assertEqual(self.redis.blpop(['foo', 'baz'], timeout=1),
                         ('baz', 'zero'))

        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        # bar has nothing, so the returned value should come
        # from foo.
        self.assertEqual(self.redis.blpop(['bar', 'foo'], timeout=1),
                         ('foo', 'one'))
        self.redis.rpush('bar', 'three')
        # bar now has something, so the returned value should come
        # from bar.
        self.assertEqual(self.redis.blpop(['bar', 'foo'], timeout=1),
                         ('bar', 'three'))
        self.assertEqual(self.redis.blpop(['bar', 'foo'], timeout=1),
                         ('foo', 'two'))

    def test_blpop_allow_single_key(self):
        # blpop converts single key arguments to a one element list.
        self.redis.rpush('foo', 'one')
        self.assertEqual(self.redis.blpop('foo', timeout=1), ('foo', 'one'))

    def test_brpop_test_multiple_lists(self):
        self.redis.rpush('baz', 'zero')
        self.assertEqual(self.redis.brpop(['foo', 'baz'], timeout=1),
                         ('baz', 'zero'))

        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.assertEqual(self.redis.brpop(['bar', 'foo'], timeout=1),
                         ('foo', 'two'))

    def test_brpop_single_key(self):
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.assertEqual(self.redis.brpop('foo', timeout=1),
                         ('foo', 'two'))

    def test_brpoplpush_multi_keys(self):
        self.assertEqual(self.redis.lpop('bar'), None)
        self.redis.rpush('foo', 'one')
        self.redis.rpush('foo', 'two')
        self.assertEqual(self.redis.brpoplpush('foo', 'bar', timeout=1),
                         'two')
        self.assertEqual(self.redis.lrange('bar', 0, -1), ['two'])

    @attr('slow')
    def test_blocking_operations_when_empty(self):
        self.assertEqual(self.redis.blpop(['foo'], timeout=1),
                         None)
        self.assertEqual(self.redis.blpop(['bar', 'foo'], timeout=1),
                         None)
        self.assertEqual(self.redis.brpop('foo', timeout=1),
                         None)
        self.assertEqual(self.redis.brpoplpush('foo', 'bar', timeout=1),
                         None)

    ## Tests for the hash type.

    def test_hset_then_hget(self):
        self.assertEqual(self.redis.hset('foo', 'key', 'value'), 1)
        self.assertEqual(self.redis.hget('foo', 'key'), 'value')

    def test_hset_update(self):
        self.assertEqual(self.redis.hset('foo', 'key', 'value'), 1)
        self.assertEqual(self.redis.hset('foo', 'key', 'value'), 0)

    def test_hgetall(self):
        self.assertEqual(self.redis.hset('foo', 'k1', 'v1'), 1)
        self.assertEqual(self.redis.hset('foo', 'k2', 'v2'), 1)
        self.assertEqual(self.redis.hset('foo', 'k3', 'v3'), 1)
        self.assertEqual(self.redis.hgetall('foo'), {'k1': 'v1', 'k2': 'v2',
                                                     'k3': 'v3'})

    def test_hgetall_with_tuples(self):
        self.assertEqual(self.redis.hset('foo', (1, 2), (1, 2, 3)), 1)
        self.assertEqual(self.redis.hgetall('foo'), {'(1, 2)': '(1, 2, 3)'})

    def test_hgetall_empty_key(self):
        self.assertEqual(self.redis.hgetall('foo'), {})

    def test_hexists(self):
        self.redis.hset('foo', 'bar', 'v1')
        self.assertEqual(self.redis.hexists('foo', 'bar'), 1)
        self.assertEqual(self.redis.hexists('foo', 'baz'), 0)
        self.assertEqual(self.redis.hexists('bar', 'bar'), 0)

    def test_hkeys(self):
        self.redis.hset('foo', 'k1', 'v1')
        self.redis.hset('foo', 'k2', 'v2')
        self.assertEqual(set(self.redis.hkeys('foo')), set(['k1', 'k2']))
        self.assertEqual(set(self.redis.hkeys('bar')), set([]))

    def test_hlen(self):
        self.redis.hset('foo', 'k1', 'v1')
        self.redis.hset('foo', 'k2', 'v2')
        self.assertEqual(self.redis.hlen('foo'), 2)

    def test_hvals(self):
        self.redis.hset('foo', 'k1', 'v1')
        self.redis.hset('foo', 'k2', 'v2')
        self.assertEqual(set(self.redis.hvals('foo')), set(['v1', 'v2']))
        self.assertEqual(set(self.redis.hvals('bar')), set([]))

    def test_hmget(self):
        self.redis.hset('foo', 'k1', 'v1')
        self.redis.hset('foo', 'k2', 'v2')
        self.redis.hset('foo', 'k3', 'v3')
        # Normal case.
        self.assertEqual(self.redis.hmget('foo', ['k1', 'k3']), ['v1', 'v3'])
        self.assertEqual(self.redis.hmget('foo', 'k1', 'k3'), ['v1', 'v3'])
        # Key does not exist.
        self.assertEqual(self.redis.hmget('bar', ['k1', 'k3']), [None, None])
        self.assertEqual(self.redis.hmget('bar', 'k1', 'k3'), [None, None])
        # Some keys in the hash do not exist.
        self.assertEqual(self.redis.hmget('foo', ['k1', 'k500']),
                         ['v1', None])
        self.assertEqual(self.redis.hmget('foo', 'k1', 'k500'),
                         ['v1', None])

    def test_hdel(self):
        self.redis.hset('foo', 'k1', 'v1')
        self.redis.hset('foo', 'k2', 'v2')
        self.redis.hset('foo', 'k3', 'v3')
        self.assertEqual(self.redis.hget('foo', 'k1'), 'v1')
        self.assertEqual(self.redis.hdel('foo', 'k1'), True)
        self.assertEqual(self.redis.hget('foo', 'k1'), None)
        self.assertEqual(self.redis.hdel('foo', 'k1'), False)
        # Since redis>=2.7.6 returns number of deleted items.
        self.assertEqual(self.redis.hdel('foo', 'k2', 'k3'), 2)
        self.assertEqual(self.redis.hget('foo', 'k2'), None)
        self.assertEqual(self.redis.hget('foo', 'k3'), None)
        self.assertEqual(self.redis.hdel('foo', 'k2', 'k3'), False)

    def test_hincrby(self):
        self.redis.hset('foo', 'counter', 0)
        self.assertEqual(self.redis.hincrby('foo', 'counter'), 1)
        self.assertEqual(self.redis.hincrby('foo', 'counter'), 2)
        self.assertEqual(self.redis.hincrby('foo', 'counter'), 3)

    def test_hincrby_with_no_starting_value(self):
        self.assertEqual(self.redis.hincrby('foo', 'counter'), 1)
        self.assertEqual(self.redis.hincrby('foo', 'counter'), 2)
        self.assertEqual(self.redis.hincrby('foo', 'counter'), 3)

    def test_hincrby_with_range_param(self):
        self.assertEqual(self.redis.hincrby('foo', 'counter', 2), 2)
        self.assertEqual(self.redis.hincrby('foo', 'counter', 2), 4)
        self.assertEqual(self.redis.hincrby('foo', 'counter', 2), 6)

    def test_hsetnx(self):
        self.assertEqual(self.redis.hsetnx('foo', 'newkey', 'v1'), True)
        self.assertEqual(self.redis.hsetnx('foo', 'newkey', 'v1'), False)
        self.assertEqual(self.redis.hget('foo', 'newkey'), 'v1')

    def test_hmsetset_empty_raises_error(self):
        with self.assertRaises(redis.DataError):
            self.redis.hmset('foo', {})

    def test_hmsetset(self):
        self.redis.hset('foo', 'k1', 'v1')
        self.assertEqual(self.redis.hmset('foo', {'k2': 'v2', 'k3': 'v3'}),
                         True)

    def test_sadd(self):
        self.assertEqual(self.redis.sadd('foo', 'member1'), 1)
        self.assertEqual(self.redis.sadd('foo', 'member1'), 0)
        self.assertEqual(self.redis.smembers('foo'), set(['member1']))
        self.assertEqual(self.redis.sadd('foo', 'member2', 'member3'), 2)
        self.assertEqual(self.redis.smembers('foo'),
                         set(['member1', 'member2', 'member3']))
        self.assertEqual(self.redis.sadd('foo', 'member3', 'member4'), 1)
        self.assertEqual(self.redis.smembers('foo'),
                         set(['member1', 'member2', 'member3', 'member4']))

    def test_scard(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('foo', 'member2')
        self.assertEqual(self.redis.scard('foo'), 2)

    def test_sdiff(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('bar', 'member2')
        self.redis.sadd('bar', 'member3')
        self.assertEqual(self.redis.sdiff('foo', 'bar'), set(['member1']))
        # Original sets shouldn't be modified.
        self.assertEqual(self.redis.smembers('foo'),
                         set(['member1', 'member2']))
        self.assertEqual(self.redis.smembers('bar'),
                         set(['member2', 'member3']))

    def test_sdiff_one_key(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.assertEqual(self.redis.sdiff('foo'), set(['member1', 'member2']))

    def test_sdiff_empty(self):
        self.assertEqual(self.redis.sdiff('foo'), set())

    def test_sdiffstore(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('bar', 'member2')
        self.redis.sadd('bar', 'member3')
        self.assertEqual(self.redis.sdiffstore('baz', 'foo', 'bar'), 1)

    def test_sinter(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('bar', 'member2')
        self.redis.sadd('bar', 'member3')
        self.assertEqual(self.redis.sinter('foo', 'bar'), set(['member2']))
        self.assertEqual(self.redis.sinter('foo'), set(['member1', 'member2']))

    def test_sinterstore(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('bar', 'member2')
        self.redis.sadd('bar', 'member3')
        self.assertEqual(self.redis.sinterstore('baz', 'foo', 'bar'), 1)

    def test_sismember(self):
        self.assertEqual(self.redis.sismember('foo', 'member1'), False)
        self.redis.sadd('foo', 'member1')
        self.assertEqual(self.redis.sismember('foo', 'member1'), True)

    def test_smembers(self):
        self.assertEqual(self.redis.smembers('foo'), set())

    def test_smove(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.assertEqual(self.redis.smove('foo', 'bar', 'member1'), True)
        self.assertEqual(self.redis.smembers('bar'), set(['member1']))

    def test_smove_non_existent_key(self):
        self.assertEqual(self.redis.smove('foo', 'bar', 'member1'), False)

    def test_spop(self):
        # This is tricky because it pops a random element.
        self.redis.sadd('foo', 'member1')
        self.assertEqual(self.redis.spop('foo'), 'member1')
        self.assertEqual(self.redis.spop('foo'), None)

    def test_srandmember(self):
        self.redis.sadd('foo', 'member1')
        self.assertEqual(self.redis.srandmember('foo'), 'member1')
        # Shouldn't be removed from the set.
        self.assertEqual(self.redis.srandmember('foo'), 'member1')

    def test_srem(self):
        self.redis.sadd('foo', 'member1', 'member2', 'member3', 'member4')
        self.assertEqual(self.redis.smembers('foo'),
                         set(['member1', 'member2', 'member3', 'member4']))
        self.assertEqual(self.redis.srem('foo', 'member1'), True)
        self.assertEqual(self.redis.smembers('foo'),
                         set(['member2', 'member3', 'member4']))
        self.assertEqual(self.redis.srem('foo', 'member1'), False)
        # Since redis>=2.7.6 returns number of deleted items.
        self.assertEqual(self.redis.srem('foo', 'member2', 'member3'), 2)
        self.assertEqual(self.redis.smembers('foo'), set(['member4']))
        self.assertEqual(self.redis.srem('foo', 'member3', 'member4'), True)
        self.assertEqual(self.redis.smembers('foo'), set([]))
        self.assertEqual(self.redis.srem('foo', 'member3', 'member4'), False)

    def test_sunion(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('bar', 'member2')
        self.redis.sadd('bar', 'member3')
        self.assertEqual(self.redis.sunion('foo', 'bar'),
                         set(['member1', 'member2', 'member3']))

    def test_sunionstore(self):
        self.redis.sadd('foo', 'member1')
        self.redis.sadd('foo', 'member2')
        self.redis.sadd('bar', 'member2')
        self.redis.sadd('bar', 'member3')
        self.assertEqual(self.redis.sunionstore('baz', 'foo', 'bar'), 3)
        self.assertEqual(self.redis.smembers('baz'),
                         set(['member1', 'member2', 'member3']))

    def test_zadd(self):
        self.redis.zadd('foo', four=4)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zadd('foo', 2, 'two', 1, 'one', zero=0), 3)
        self.assertEqual(self.redis.zrange('foo', 0, -1),
                         ['zero', 'one', 'two', 'three', 'four'])
        self.assertEqual(self.redis.zadd('foo', 7, 'zero', one=1, five=5), 1)
        self.assertEqual(self.redis.zrange('foo', 0, -1),
                         ['one', 'two', 'three', 'four', 'five', 'zero'])

    def test_zadd_uses_str(self):
        self.redis.zadd('foo', 12345, (1, 2, 3))
        self.assertEqual(self.redis.zrange('foo', 0, 0), ['(1, 2, 3)'])

    def test_zadd_errors(self):
        # The args are backwards, it should be 2, "two", so we
        # expect an exception to be raised.
        with self.assertRaises(redis.ResponseError):
            self.redis.zadd('foo', 'two', 2)
        with self.assertRaises(redis.ResponseError):
            self.redis.zadd('foo', two='two')

    def test_zadd_multiple(self):
        self.redis.zadd('foo', 1, 'one', 2, 'two')
        self.assertEqual(self.redis.zrange('foo', 0, 0),
                         ['one'])
        self.assertEqual(self.redis.zrange('foo', 1, 1),
                         ['two'])

    def test_zrange_same_score(self):
        self.redis.zadd('foo', two_a=2)
        self.redis.zadd('foo', two_b=2)
        self.redis.zadd('foo', two_c=2)
        self.redis.zadd('foo', two_d=2)
        self.redis.zadd('foo', two_e=2)
        self.assertEqual(self.redis.zrange('foo', 2, 3),
                         ['two_c', 'two_d'])

    def test_zcard(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.assertEqual(self.redis.zcard('foo'), 2)

    def test_zcard_non_existent_key(self):
        self.assertEqual(self.redis.zcard('foo'), 0)

    def test_zcount(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', three=2)
        self.redis.zadd('foo', five=5)
        self.assertEqual(self.redis.zcount('foo', 2, 4), 1)
        self.assertEqual(self.redis.zcount('foo', 1, 4), 2)
        self.assertEqual(self.redis.zcount('foo', 0, 5), 3)

    def test_zincrby(self):
        self.redis.zadd('foo', one=1)
        self.assertEqual(self.redis.zincrby('foo', 'one', 10), 11)
        self.assertEqual(self.redis.zrange('foo', 0, -1, withscores=True),
                         [('one', 11)])

    def test_zrange_descending(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrange('foo', 0, -1, desc=True),
                         ['three', 'two', 'one'])

    def test_zrange_descending_with_scores(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrange('foo', 0, -1, desc=True,
                                           withscores=True),
                         [('three', 3), ('two', 2), ('one', 1)])

    def test_zrange_with_positive_indices(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrange('foo', 0, 1), ['one', 'two'])

    def test_zrank(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrank('foo', 'one'), 0)
        self.assertEqual(self.redis.zrank('foo', 'two'), 1)
        self.assertEqual(self.redis.zrank('foo', 'three'), 2)

    def test_zrank_non_existent_member(self):
        self.assertEqual(self.redis.zrank('foo', 'one'), None)

    def test_zrem(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.redis.zadd('foo', four=4)
        self.assertEqual(self.redis.zrem('foo', 'one'), True)
        self.assertEqual(self.redis.zrange('foo', 0, -1),
                         ['two', 'three', 'four'])
        # Since redis>=2.7.6 returns number of deleted items.
        self.assertEqual(self.redis.zrem('foo', 'two', 'three'), 2)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['four'])
        self.assertEqual(self.redis.zrem('foo', 'three', 'four'), True)
        self.assertEqual(self.redis.zrange('foo', 0, -1), [])
        self.assertEqual(self.redis.zrem('foo', 'three', 'four'), False)

    def test_zrem_non_existent_member(self):
        self.assertFalse(self.redis.zrem('foo', 'one'))

    def test_zrem_numeric_member(self):
        self.redis.zadd('foo', **{'128': 13.0, '129': 12.0})
        self.assertEqual(self.redis.zrem('foo',  128), True)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['129'])

    def test_zscore(self):
        self.redis.zadd('foo', one=54)
        self.assertEqual(self.redis.zscore('foo', 'one'), 54)

    def test_zscore_non_existent_member(self):
        self.assertIsNone(self.redis.zscore('foo', 'one'))

    def test_zrevrank(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrevrank('foo', 'one'), 2)
        self.assertEqual(self.redis.zrevrank('foo', 'two'), 1)
        self.assertEqual(self.redis.zrevrank('foo', 'three'), 0)

    def test_zrevrank_non_existent_member(self):
        self.assertEqual(self.redis.zrevrank('foo', 'one'), None)

    def test_zrevrange(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrevrange('foo', 0, 1), ['three', 'two'])
        self.assertEqual(self.redis.zrevrange('foo', 0, -1),
                         ['three', 'two', 'one'])

    def test_zrevrange_sorted_keys(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', 2, 'two_b')
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrevrange('foo', 0, 2), ['three', 'two_b', 'two'])
        self.assertEqual(self.redis.zrevrange('foo', 0, -1),
                         ['three', 'two_b', 'two', 'one'])


    def test_zrangebyscore(self):
        self.redis.zadd('foo', zero=0)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', two_a_also=2)
        self.redis.zadd('foo', two_b_also=2)
        self.redis.zadd('foo', four=4)
        self.assertEqual(self.redis.zrangebyscore('foo', 1, 3),
                         ['two', 'two_a_also', 'two_b_also'])
        self.assertEqual(self.redis.zrangebyscore('foo', 2, 3),
                         ['two', 'two_a_also', 'two_b_also'])
        self.assertEqual(self.redis.zrangebyscore('foo', 0, 4),
                         ['zero', 'two', 'two_a_also', 'two_b_also', 'four'])

    def test_zrangebyscore_slice(self):
        self.redis.zadd('foo', two_a=2)
        self.redis.zadd('foo', two_b=2)
        self.redis.zadd('foo', two_c=2)
        self.redis.zadd('foo', two_d=2)
        self.assertEqual(self.redis.zrangebyscore('foo', 0, 4, 0, 2),
                         ['two_a', 'two_b'])
        self.assertEqual(self.redis.zrangebyscore('foo', 0, 4, 1, 3),
                         ['two_b', 'two_c', 'two_d'])

    def test_zrangebyscore_withscores(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrangebyscore('foo', 1, 3, 0, 2, True),
                         [('one', 1), ('two', 2)])

    def test_zrevrangebyscore(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zrevrangebyscore('foo', 3, 1),
                         ['three', 'two', 'one'])
        self.assertEqual(self.redis.zrevrangebyscore('foo', 3, 2),
                         ['three', 'two'])
        self.assertEqual(self.redis.zrevrangebyscore('foo', 3, 1, 0, 1),
                         ['three'])
        self.assertEqual(self.redis.zrevrangebyscore('foo', 3, 1, 1, 2),
                         ['two', 'one'])

    def test_zremrangebyrank(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zremrangebyrank('foo', 0, 1), 2)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['three'])

    def test_zremrangebyrank_negative_indices(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', three=3)
        self.assertEqual(self.redis.zremrangebyrank('foo', -2, -1), 2)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['one'])

    def test_zremrangebyrank_out_of_bounds(self):
        self.redis.zadd('foo', one=1)
        self.assertEqual(self.redis.zremrangebyrank('foo', 1, 3), 0)

    def test_zremrangebyscore(self):
        self.redis.zadd('foo', zero=0)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('foo', four=4)
        # Outside of range.
        self.assertEqual(self.redis.zremrangebyscore('foo', 5, 10), 0)
        self.assertEqual(self.redis.zrange('foo', 0, -1),
                         ['zero', 'two', 'four'])
        # Middle of range.
        self.assertEqual(self.redis.zremrangebyscore('foo', 1, 3), 1)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['zero', 'four'])
        self.assertEqual(self.redis.zremrangebyscore('foo', 1, 3), 0)
        # Entire range.
        self.assertEqual(self.redis.zremrangebyscore('foo', 0, 4), 2)
        self.assertEqual(self.redis.zrange('foo', 0, -1), [])

    def test_zremrangebyscore_badkey(self):
        self.assertEqual(self.redis.zremrangebyscore('foo', 0, 2), 0)

    def test_zunionstore(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zunionstore('baz', ['foo', 'bar'])
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 2), ('three', 3), ('two', 4)])

    def test_zunionstore_sum(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zunionstore('baz', ['foo', 'bar'], aggregate='SUM')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 2), ('three', 3), ('two', 4)])

    def test_zunionstore_max(self):
        self.redis.zadd('foo', one=0)
        self.redis.zadd('foo', two=0)
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zunionstore('baz', ['foo', 'bar'], aggregate='MAX')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 1), ('two', 2), ('three', 3)])

    def test_zunionstore_min(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('bar', one=0)
        self.redis.zadd('bar', two=0)
        self.redis.zadd('bar', three=3)
        self.redis.zunionstore('baz', ['foo', 'bar'], aggregate='MIN')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 0), ('two', 0), ('three', 3)])

    def test_zunionstore_weights(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', four=4)
        self.redis.zunionstore('baz', {'foo': 1, 'bar': 2}, aggregate='SUM')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 3), ('two', 6), ('four', 8)])

    def test_zunionstore_mixed_set_types(self):
        # No score, redis will use 1.0.
        self.redis.sadd('foo', 'one')
        self.redis.sadd('foo', 'two')
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zunionstore('baz', ['foo', 'bar'], aggregate='SUM')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 2), ('three', 3), ('two', 3)])

    def test_zunionstore_badkey(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zunionstore('baz', ['foo', 'bar'], aggregate='SUM')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 1), ('two', 2)])
        self.redis.zunionstore('baz', {'foo': 1, 'bar': 2}, aggregate='SUM')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 1), ('two', 2)])

    def test_zinterstore(self):
        self.redis.zadd('foo', one=1)
        self.redis.zadd('foo', two=2)
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zinterstore('baz', ['foo', 'bar'])
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 2), ('two', 4)])

    def test_zinterstore_mixed_set_types(self):
        self.redis.sadd('foo', 'one')
        self.redis.sadd('foo', 'two')
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zinterstore('baz', ['foo', 'bar'], aggregate='SUM')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 2), ('two', 3)])

    def test_zinterstore_max(self):
        self.redis.zadd('foo', one=0)
        self.redis.zadd('foo', two=0)
        self.redis.zadd('bar', one=1)
        self.redis.zadd('bar', two=2)
        self.redis.zadd('bar', three=3)
        self.redis.zinterstore('baz', ['foo', 'bar'], aggregate='MAX')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 1), ('two', 2)])

    def test_zinterstore_onekey(self):
        self.redis.zadd('foo', one=1)
        self.redis.zinterstore('baz', ['foo'], aggregate='MAX')
        self.assertEqual(self.redis.zrange('baz', 0, -1, withscores=True),
                         [('one', 1)])

    def test_zinterstore_nokey(self):
        with self.assertRaises(redis.ResponseError):
            self.redis.zinterstore('baz', [], aggregate='MAX')

    def test_zunionstore_nokey(self):
        with self.assertRaises(redis.ResponseError):
            self.redis.zunionstore('baz', [], aggregate='MAX')

    def test_multidb(self):
        r1 = self.create_redis(db=0)
        r2 = self.create_redis(db=1)

        r1['r1'] = 'r1'
        r2['r2'] = 'r2'

        self.assertTrue('r2' not in r1)
        self.assertTrue('r1' not in r2)

        self.assertEqual(r1['r1'], 'r1')
        self.assertEqual(r2['r2'], 'r2')

        r1.flushall()

        self.assertTrue('r1' not in r1)
        self.assertTrue('r2' not in r2)

    def test_basic_sort(self):
        self.redis.rpush('foo', '2')
        self.redis.rpush('foo', '1')
        self.redis.rpush('foo', '3')

        self.assertEqual(self.redis.sort('foo'), ['1', '2', '3'])

    def test_empty_sort(self):
        self.assertEqual(self.redis.sort('foo'), [])

    def test_sort_range_offset_range(self):
        self.redis.rpush('foo', '2')
        self.redis.rpush('foo', '1')
        self.redis.rpush('foo', '4')
        self.redis.rpush('foo', '3')

        self.assertEqual(self.redis.sort('foo', start=0, num=2), ['1', '2'])

    def test_sort_range_offset_norange(self):
        with self.assertRaises(redis.RedisError):
            self.redis.sort('foo', start=1)

    def test_sort_range_with_large_range(self):
        self.redis.rpush('foo', '2')
        self.redis.rpush('foo', '1')
        self.redis.rpush('foo', '4')
        self.redis.rpush('foo', '3')
        # num=20 even though len(foo) is 4.
        self.assertEqual(self.redis.sort('foo', start=1, num=20),
                         ['2', '3', '4'])

    def test_sort_descending(self):
        self.redis.rpush('foo', '1')
        self.redis.rpush('foo', '2')
        self.redis.rpush('foo', '3')
        self.assertEqual(self.redis.sort('foo', desc=True), ['3', '2', '1'])

    def test_sort_alpha(self):
        self.redis.rpush('foo', '2a')
        self.redis.rpush('foo', '1b')
        self.redis.rpush('foo', '2b')
        self.redis.rpush('foo', '1a')

        self.assertEqual(self.redis.sort('foo', alpha=True),
                         ['1a', '1b', '2a', '2b'])

    def test_foo(self):
        self.redis.rpush('foo', '2a')
        self.redis.rpush('foo', '1b')
        self.redis.rpush('foo', '2b')
        self.redis.rpush('foo', '1a')
        with self.assertRaises(redis.ResponseError):
            self.redis.sort('foo', alpha=False)

    def test_sort_with_store_option(self):
        self.redis.rpush('foo', '2')
        self.redis.rpush('foo', '1')
        self.redis.rpush('foo', '4')
        self.redis.rpush('foo', '3')

        self.assertEqual(self.redis.sort('foo', store='bar'), 4)
        self.assertEqual(self.redis.lrange('bar', 0, -1),
                         ['1', '2', '3', '4'])

    def test_sort_with_by_and_get_option(self):
        self.redis.rpush('foo', '2')
        self.redis.rpush('foo', '1')
        self.redis.rpush('foo', '4')
        self.redis.rpush('foo', '3')

        self.redis['weight_1'] = '4'
        self.redis['weight_2'] = '3'
        self.redis['weight_3'] = '2'
        self.redis['weight_4'] = '1'

        self.redis['data_1'] = 'one'
        self.redis['data_2'] = 'two'
        self.redis['data_3'] = 'three'
        self.redis['data_4'] = 'four'

        self.assertEqual(self.redis.sort('foo', by='weight_*', get='data_*'),
                         ['four', 'three', 'two', 'one'])
        self.assertEqual(self.redis.sort('foo', by='weight_*', get='#'),
                         ['4', '3', '2', '1'])
        self.assertEqual(
            self.redis.sort('foo', by='weight_*', get=('data_*', '#')),
            ['four', '4', 'three', '3', 'two', '2', 'one', '1'])
        self.assertEqual(self.redis.sort('foo', by='weight_*', get='data_1'),
                         [None, None, None, None])

    def test_sort_with_hash(self):
        self.redis.rpush('foo', 'middle')
        self.redis.rpush('foo', 'eldest')
        self.redis.rpush('foo', 'youngest')
        self.redis.hset('record_youngest', 'age', 1)
        self.redis.hset('record_youngest', 'name', 'baby')

        self.redis.hset('record_middle', 'age', 10)
        self.redis.hset('record_middle', 'name', 'teen')

        self.redis.hset('record_eldest', 'age', 20)
        self.redis.hset('record_eldest', 'name', 'adult')

        self.assertEqual(self.redis.sort('foo', by='record_*->age'),
                         ['youngest', 'middle', 'eldest'])
        self.assertEqual(
            self.redis.sort('foo', by='record_*->age', get='record_*->name'),
            ['baby', 'teen', 'adult'])

    def test_sort_with_set(self):
        self.redis.sadd('foo', '3')
        self.redis.sadd('foo', '1')
        self.redis.sadd('foo', '2')
        self.assertEqual(self.redis.sort('foo'), ['1', '2', '3'])

    def test_pipeline(self):
        # The pipeline method returns an object for
        # issuing multiple commands in a batch.
        p = self.redis.pipeline()
        p.watch('bam')
        p.multi()
        p.set('foo', 'bar').get('foo')
        p.lpush('baz', 'quux')
        p.lpush('baz', 'quux2').lrange('baz', 0, -1)
        res = p.execute()

        # Check return values returned as list.
        self.assertEqual([True, 'bar', 1, 2, ['quux2', 'quux']], res)

        # Check side effects happened as expected.
        self.assertEqual(['quux2', 'quux'], self.redis.lrange('baz', 0, -1))

        # Check that the command buffer has been emptied.
        self.assertEqual([], p.execute())

    def test_multiple_successful_watch_calls(self):
        p = self.redis.pipeline()
        p.watch('bam')
        p.multi()
        p.set('foo', 'bar')
        # Check that the watched keys buffer has been emptied.
        p.execute()

        # bam is no longer being watched, so it's ok to modify
        # it now.
        p.watch('foo')
        self.redis.set('bam', 'boo')
        p.multi()
        p.set('foo', 'bats')
        self.assertEqual(p.execute(), [True])

    def test_pipeline_non_transactional(self):
        # For our simple-minded model I don't think
        # there is any observable difference.
        p = self.redis.pipeline(transaction=False)
        res = p.set('baz', 'quux').get('baz').execute()

        self.assertEqual([True, 'quux'], res)

    def test_pipeline_raises_when_watched_key_changed(self):
        self.redis.set('foo', 'bar')
        self.redis.rpush('greet', 'hello')
        p = self.redis.pipeline()
        self.addCleanup(p.reset)

        p.watch('greet', 'foo')
        nextf = p.get('foo') + 'baz'
        # Simulate change happening on another thread.
        self.redis.rpush('greet', 'world')
        # Begin pipelining.
        p.multi()
        p.set('foo', nextf)

        self.assertRaises(redis.WatchError, p.execute)

    def test_pipeline_succeeds_despite_unwatched_key_changed(self):
        # Same setup as before except for the params to the WATCH command.
        self.redis.set('foo', 'bar')
        self.redis.rpush('greet', 'hello')
        p = self.redis.pipeline()
        try:
            # Only watch one of the 2 keys.
            p.watch('foo')
            nextf = p.get('foo') + 'baz'
            # Simulate change happening on another thread.
            self.redis.rpush('greet', 'world')
            p.multi()
            p.set('foo', nextf)
            p.execute()

            # Check the commands were executed.
            self.assertEqual('barbaz', self.redis.get('foo'))
        finally:
            p.reset()

    def test_pipeline_succeeds_when_watching_nonexistent_key(self):
        self.redis.set('foo', 'bar')
        self.redis.rpush('greet', 'hello')
        p = self.redis.pipeline()
        try:
            # Also watch a nonexistent key.
            p.watch('foo', 'bam')
            nextf = p.get('foo') + 'baz'
            # Simulate change happening on another thread.
            self.redis.rpush('greet', 'world')
            p.multi()
            p.set('foo', nextf)
            p.execute()

            # Check the commands were executed.
            self.assertEqual('barbaz', self.redis.get('foo'))
        finally:
            p.reset()

    def test_watch_state_is_cleared_across_multiple_watches(self):
        self.redis.set('foo', 'one')
        self.redis.set('bar', 'baz')
        p = self.redis.pipeline()
        self.addCleanup(p.reset)

        p.watch('foo')
        # Simulate change happening on another thread.
        self.redis.set('foo', 'three')
        p.multi()
        p.set('foo', 'three')
        with self.assertRaises(redis.WatchError):
            p.execute()

        # Now watch another key.  It should be ok to change
        # foo as we're no longer watching it.
        p.watch('bar')
        self.redis.set('foo', 'four')
        p.multi()
        p.set('bar', 'five')
        self.assertEqual(p.execute(), [True])

    def test_pipeline_proxies_to_redis_object(self):
        p = self.redis.pipeline()
        self.assertTrue(hasattr(p, 'zadd'))
        with self.assertRaises(AttributeError):
            p.non_existent_attribute

    def test_pipeline_as_context_manager(self):
        self.redis.set('foo', 'bar')
        with self.redis.pipeline() as p:
            p.watch('foo')
            self.assertTrue(isinstance(p, redis.client.BasePipeline)
                            or p.need_reset)
            p.multi()
            p.set('foo', 'baz')
            p.execute()

        # Usually you would consider the pipeline to
        # have been destroyed
        # after the with statement, but we need to check
        # it was reset properly:
        self.assertTrue(isinstance(p, redis.client.BasePipeline)
                        or not p.need_reset)

    def test_pipeline_transaction_shortcut(self):
        # This example taken pretty much from the redis-py documentation.
        self.redis.set('OUR-SEQUENCE-KEY', 13)
        calls = []

        def client_side_incr(pipe):
            calls.append((pipe,))
            current_value = pipe.get('OUR-SEQUENCE-KEY')
            next_value = int(current_value) + 1

            if len(calls) < 3:
                # Simulate a change from another thread.
                self.redis.set('OUR-SEQUENCE-KEY', next_value)

            pipe.multi()
            pipe.set('OUR-SEQUENCE-KEY', next_value)

        res = self.redis.transaction(client_side_incr, 'OUR-SEQUENCE-KEY')

        self.assertEqual([True], res)
        self.assertEqual(16, int(self.redis.get('OUR-SEQUENCE-KEY')))
        self.assertEqual(3, len(calls))

    def test_key_patterns(self):
        self.redis.mset({'one': 1, 'two': 2, 'three': 3, 'four': 4})
        self.assertItemsEqual(self.redis.keys('*o*'), ['four', 'one', 'two'])
        self.assertItemsEqual(self.redis.keys('t??'), ['two'])
        self.assertItemsEqual(self.redis.keys('*'),
                              ['four', 'one', 'two', 'three'])
        self.assertItemsEqual(self.redis.keys(),
                              ['four', 'one', 'two', 'three'])

    def test_ping(self):
        self.assertTrue(self.redis.ping())


class TestFakeRedis(unittest.TestCase):
    def setUp(self):
        self.redis = self.create_redis()

    def tearDown(self):
        self.redis.flushall()
        del self.redis

    def create_redis(self, db=0):
        return fakeredis.FakeRedis(db=db)

    def test_setex(self):
        self.assertEqual(self.redis.setex('foo', 'bar', 100), True)
        self.assertEqual(self.redis.get('foo'), 'bar')

    def test_setex_using_timedelta(self):
        self.assertEqual(self.redis.setex('foo', 'bar', timedelta(seconds=100)), True)
        self.assertEqual(self.redis.get('foo'), 'bar')

    def test_lrem_postitive_count(self):
        self.redis.lpush('foo', 'same')
        self.redis.lpush('foo', 'same')
        self.redis.lpush('foo', 'different')
        self.redis.lrem('foo', 'same', 2)
        self.assertEqual(self.redis.lrange('foo', 0, -1), ['different'])

    def test_lrem_negative_count(self):
        self.redis.lpush('foo', 'removeme')
        self.redis.lpush('foo', 'three')
        self.redis.lpush('foo', 'two')
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'removeme')
        self.redis.lrem('foo', 'removeme', -1)
        # Should remove it from the end of the list,
        # leaving the 'removeme' from the front of the list alone.
        self.assertEqual(self.redis.lrange('foo', 0, -1),
                         ['removeme', 'one', 'two', 'three'])

    def test_lrem_zero_count(self):
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lrem('foo', 'one')
        self.assertEqual(self.redis.lrange('foo', 0, -1), [])

    def test_lrem_default_value(self):
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lpush('foo', 'one')
        self.redis.lrem('foo', 'one')
        self.assertEqual(self.redis.lrange('foo', 0, -1), [])

    def test_lrem_does_not_exist(self):
        self.redis.lpush('foo', 'one')
        self.redis.lrem('foo', 'one')
        # These should be noops.
        self.redis.lrem('foo', 'one', -2)
        self.redis.lrem('foo', 'one', 2)

    def test_lrem_return_value(self):
        self.redis.lpush('foo', 'one')
        count = self.redis.lrem('foo', 'one', 0)
        self.assertEqual(count, 1)
        self.assertEqual(self.redis.lrem('foo', 'one'), 0)

    def test_zadd_deprecated(self):
        self.redis.zadd('foo', 'one', 1)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['one'])

    def test_zadd_missing_required_params(self):
        with self.assertRaises(redis.RedisError):
            # Missing the 'score' param.
            self.redis.zadd('foo', 'one')
        with self.assertRaises(redis.RedisError):
            # Missing the 'value' param.
            self.redis.zadd('foo', None, score=1)

    def test_zadd_with_single_keypair(self):
        self.redis.zadd('foo', bar=1)
        self.assertEqual(self.redis.zrange('foo', 0, -1), ['bar'])

    def test_set_nx_doesnt_set_value_twice(self):
        self.assertEqual(self.redis.set('foo', 'bar', nx=True), True)
        self.assertEqual(self.redis.set('foo', 'bar', nx=True), None)

    def test_set_xx_set_value_when_exists(self):
        self.assertEqual(self.redis.set('foo', 'bar', xx=True), None)
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.set('foo', 'bar', xx=True), True)

    @attr('slow')
    def test_set_ex_should_expire_value(self):
        self.redis.set('foo', 'bar', ex=0)
        self.assertEqual(self.redis.get('foo'), 'bar')
        self.redis.set('foo', 'bar', ex=1)
        sleep(2)
        self.assertEqual(self.redis.get('foo'), None)

    @attr('slow')
    def test_set_px_should_expire_value(self):
        self.redis.set('foo', 'bar', px=500)
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)

    @attr('slow')
    def test_psetex_expire_value(self):
        self.assertRaises(ResponseError, self.redis.psetex, 'foo', 0, 'bar')
        self.redis.psetex('foo', 500, 'bar')
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)

    @attr('slow')
    def test_psetex_expire_value_using_timedelta(self):
        self.assertRaises(ResponseError, self.redis.psetex, 'foo', timedelta(seconds=0), 'bar')
        self.redis.psetex('foo', timedelta(seconds=0.5), 'bar')
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)

    @attr('slow')
    def test_expire_should_expire_key(self):
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.get('foo'), 'bar')
        self.redis.expire('foo', 1)
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)
        self.assertEqual(self.redis.expire('bar', 1), False)

    @attr('slow')
    def test_expire_should_expire_key_using_timedelta(self):
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.get('foo'), 'bar')
        self.redis.expire('foo', timedelta(seconds=1))
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)
        self.assertEqual(self.redis.expire('bar', 1), False)

    @attr('slow')
    def test_expireat_should_expire_key_by_datetime(self):
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.get('foo'), 'bar')
        self.redis.expireat('foo', datetime.now() + timedelta(seconds=1))
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)

    @attr('slow')
    def test_expireat_should_expire_key_by_timestamp(self):
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.get('foo'), 'bar')
        self.redis.expireat('foo', int(time() + 1))
        sleep(1.5)
        self.assertEqual(self.redis.get('foo'), None)
        self.assertEqual(self.redis.expire('bar', 1), False)

    def test_ttl_should_return_none_for_non_expiring_key(self):
        self.redis.set('foo', 'bar')
        self.assertEqual(self.redis.get('foo'), 'bar')
        self.assertEqual(self.redis.ttl('foo'), None)

    def test_ttl_should_return_value_for_expiring_key(self):
        self.redis.set('foo', 'bar')
        self.redis.expire('foo', 1)
        self.assertEqual(self.redis.ttl('foo'), 1)
        self.redis.expire('foo', 2)
        self.assertEqual(self.redis.ttl('foo'), 2)
        long_long_c_max = 100000000000
        # See https://github.com/antirez/redis/blob/unstable/src/db.c#L632
        self.redis.expire('foo', long_long_c_max)
        self.assertEqual(self.redis.ttl('foo'), long_long_c_max)


@redis_must_be_running
class TestRealRedis(TestFakeRedis):
    def create_redis(self, db=0):
        return redis.Redis('localhost', port=6379, db=db)


@redis_must_be_running
class TestRealStrictRedis(TestFakeStrictRedis):
    def create_redis(self, db=0):
        return redis.StrictRedis('localhost', port=6379, db=db)


class TestInitArgs(unittest.TestCase):
    def test_can_accept_any_kwargs(self):
        fakeredis.FakeRedis(foo='bar', bar='baz')
        fakeredis.FakeStrictRedis(foo='bar', bar='baz')

    def test_from_url(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://username:password@localhost:6379/0')
        db.set('foo', 'bar')
        self.assertEqual(db.get('foo'), 'bar')

    def test_from_url_with_db_arg(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://username:password@localhost:6379/0')
        db1 = fakeredis.FakeStrictRedis.from_url(
            'redis://username:password@localhost:6379/1')
        db2 = fakeredis.FakeStrictRedis.from_url(
            'redis://username:password@localhost:6379/',
            db=2)
        db.set('foo', 'foo0')
        db1.set('foo', 'foo1')
        db2.set('foo', 'foo2')
        self.assertEqual(db.get('foo'), 'foo0')
        self.assertEqual(db1.get('foo'), 'foo1')
        self.assertEqual(db2.get('foo'), 'foo2')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
