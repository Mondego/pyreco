__FILENAME__ = client
# coding: utf-8

__all__ = ['connect', 'get_client']

import redis

client = None

def connect(*args, **kwargs):
    """ 
    连接 Redis 数据库，参数和 redis-py 的 Redis 类一样。
    """
    global client
    client = redis.Redis(*args, **kwargs)

def get_client():
    """ 
    返回 OORedis 客户端。
    """
    global client

    if client is None: connect()

    return client

########NEW FILE########
__FILENAME__ = const
# coding: utf-8

# redis 的数据类型
REDIS_TYPE = {
    'string': 'string',
    'list': 'list',
    'hash': 'hash',
    'set': 'set',
    'sorted_set': 'zset',
    'not_exists': 'none',
}

# redis 列表和有序集的 range 边界
LEFTMOST = 0
RIGHTMOST = -1

# 默认增量和减量
DEFAULT_INCREMENT = DEFAULT_DECREMENT = 1

########NEW FILE########
__FILENAME__ = base_key
# coding:utf-8

__all__ = ['BaseKey']

__metaclass__ = type

from ooredis.client import get_client
from ooredis.type_case import GenericTypeCase

class BaseKey:

    """ 
    所有其他 Key 对象的基类，保存了 key 名，客户端以及 TypeCase 。
    """

    def __init__(self, name, client=None, type_case=GenericTypeCase):
        """ 
        指定 key 名和客户端，以及 TypeCase 。

        Args:
            name: Redis key 的名字
            client: 客户端，默认为全局客户端
            type_case: 类型转换类

        Time:
            O(1)

        Returns:
            None

        Raises:
            None
        """
        self.name = name
        self._client = client or get_client()
        self._encode = type_case.encode
        self._decode = type_case.decode


    def __eq__(self, other):
        """ 
        判断两个 Key 对象是否相等。

        Args:
            other: 另一个 Key 对象。

        Time:
            O(1)

        Returns:
            bool: 相等返回 True ，否则返回 False 。

        Raises:
            None
        """
        return self.name == other.name

########NEW FILE########
__FILENAME__ = common_key_property_mixin
# coding: utf-8

__all__ = ['CommonKeyPropertyMixin']

__metaclass__ = type

class CommonKeyPropertyMixin:

    """
    包含所有 Redis key 通用的操作和属性。
    """

    @property
    def _represent(self):
        """ 
        返回 Key 对象在 Redis 中的表示(底层的实现类型)。

        Args:
            None

        Time:
            O(1)

        Returns: 
            redis的类型定义在REDIS_TYPE常量中，包含以下：
            'none' : 值不存在
            'string' : 字符串
            'list' : 列表
            'set' : 集合
            'zset' : 有序集
            'hash' : 哈希表

        Raises:
            None
        """
        return self._client.type(self.name)


    @property
    def ttl(self):
        """ 
        返回 key 的生存时间。

        Args:
            None

        Time:
            O(1)

        Returns: 
            None: key 不存在，或 key 没有设置生存时间。
            ttl_in_second: 以秒为单位的生存时间值。

        Raises:
            None
        """
        return self._client.ttl(self.name)


    @property
    def exists(self):
        """ 
        检查 key 是否存在。

        Args:
            None

        Time:
            O(1)

        Returns:
            bool: key 存在返回 True ，否则为 False 。

        Raises:
            None
        """
        return self._client.exists(self.name)


    def delete(self):
        """ 
        删除 key 。

        Args:
            None

        Time:
            O(1)

        Returns:
            None

        Raises:
            None
        """
        self._client.delete(self.name)


    def expire(self, second):
        """ 
        为 key 设置生存时间。

        Args:
            second: 以秒为单位的生存时间。

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 尝试对不存在的 key 进行设置时抛出。
        """
        # redis-py 对不存在的 key 进行 expire 时返回false，
        # 这里抛出一个异常。
        if not self.exists:
            raise TypeError

        self._client.expire(self.name, second)


    def expireat(self, unix_timestamp):
        """ 
        为 key 设置生存时间，以一个 unix 时间戳为终止时间。

        Args:
            unix_timestamp: 以 unix 时间戳为格式的生存时间。

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 对一个不存在的 key 进行操作时抛出。
        """
        # redis-py 对不存在的 key 进行 expireat 时返回False，
        # 这里抛出一个异常。
        if not self.exists:
            raise TypeError

        self._client.expireat(self.name, unix_timestamp)


    def persist(self):
        """ 
        移除 key 的生存时间

        Args:
            None

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 对一个不存在的 key 进行操作时抛出
        """
        # redis-py 对不存在的 key 进行 persist 返回-1
        # 这里抛出一个异常
        if not self.exists:
            raise TypeError

        self._client.persist(self.name)

########NEW FILE########
__FILENAME__ = counter
# coding: utf-8

__all__ = ['Counter']

__metaclass__ = type

from ooredis.type_case import IntTypeCase
from ooredis.const import DEFAULT_INCREMENT, DEFAULT_DECREMENT

from base_key import BaseKey
from common_key_property_mixin import CommonKeyPropertyMixin
from set_and_get_op_mixin import SetAndGetOpMixin
from helper import format_key, wrap_exception

class Counter(BaseKey, CommonKeyPropertyMixin, SetAndGetOpMixin):

    """
    计数器用途的 Key 对象。
   
    注意当 Key 对象为空时，get/getset 的返回值为 None 。
    """

    def __init__(self, name, client=None, type_case=IntTypeCase):
        """ 
        初始化一个 Counter 类实例，
        使用 IntTypeCase 作为默认 type case 。
        """
        super(Counter, self).__init__(name=name, client=client, type_case=type_case)


    def __repr__(self):
        return format_key(self, self.name, self.get())


    @wrap_exception
    def incr(self, increment=DEFAULT_INCREMENT):
        """
        将计数器的值加上增量 increment， 
        然后返回执行 incr 操作之后计数器的当前值。

        Args:
            increment: 增量，默认为 1 。

        Time:
            O(1)

        Returns:
            current_counter_value

        Raises:
            TypeError: 当 Key 对象储存的不是数值类型时抛出。
        """
        # redis-py 用 incr 代替 redis 的 incrby
        return self._client.incr(self.name, increment)


    @wrap_exception
    def decr(self, decrement=DEFAULT_DECREMENT):
        """
        将计数器的值减去减量 decrement ，
        然后返回执行 decr 操作之后计数器的当前值。

        Args:
            decrement: 减量，默认为1.

        Time:
            O(1)

        Returns:
            current_counter_value

        Raises:
            TypeError: 当 key 储存的不是数值类型时抛出。
        """
        # redis-py 用 decr 代替 redis 的 decrby
        return self._client.decr(self.name, decrement)


    def __iadd__(self, increment):
        """
        self.incr 方法的一个 Python 语法糖，
        区别是这个特殊方法不返回 Key 对象的当前值。

        Args:
            increment: 增量。

        Time:
            O(1)

        Returns:
            self: Python 要求这个特殊方法返回被修改后的对象。

        Raises:
            TypeError: 当 key 储存的不是数值类型时由 self.incr 抛出。
        """
        self.incr(increment)
        return self


    def __isub__(self, decrement):
        """
        self.decr 方法的一个 Python 语法糖，
        区别是这个特殊方法不返回 Key 对象的当前值。

        Args:
            decrement: 减量。

        Time:
            O(1)

        Returns:
            self: Python 要求这个特殊方法返回被修改后的对象。

        Raises:
            TypeError: 当 key 储存的不是数值类型时由 self.decr 抛出。
        """
        self.decr(decrement)
        return self

########NEW FILE########
__FILENAME__ = deque
# coding: utf-8

__all__ = ['Deque']

__metaclass__ = type

import redis

from base_key import BaseKey
from helper import format_key, wrap_exception
from common_key_property_mixin import CommonKeyPropertyMixin

class Deque(BaseKey, CommonKeyPropertyMixin):

    """ 
    将 Redis 的 list 结构映射到双端队列对象。
    """

    def append(self, python_item):
        """
        将元素 item 追加到队列的最右边。

        Args:
            item

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        redis_item = self._encode(python_item)
        self._client.rpush(self.name, redis_item)


    @wrap_exception
    def appendleft(self, python_item):
        """
        将元素 item 追加到队列的最左边。

        Args:
            item

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        redis_item = self._encode(python_item)
        self._client.lpush(self.name, redis_item)


    def extend(self, python_iterable):
        """
        将 iterable 内的所有元素追加到队列的最右边。

        Args:
            iterable

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        redis_iterable = map(self._encode, python_iterable)
        self._client.rpush(self.name, *redis_iterable)


    @wrap_exception
    def extendleft(self, python_iterable):
        """
        将 iterable 内的所有元素追加到队列的最左边。

        注意被追加元素是以逆序排列的。

        比如对一个空队列 d 执行 d.extendleft(range(3)) ，
        那么队列 d 将变成 [3, 2, 1] 。

        Args:
            iterable

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        redis_iterable = map(self._encode, python_iterable)
        self._client.lpush(self.name, *redis_iterable)


    def clear(self):
        """
        删除队列中的所有元素。

        Time:
            O(1)
        
        Returns:
            None

        Raises:
            None
        """
        self.delete()
    

    def count(self, python_item):
        """
        计算队列中和 item 相等的元素的个数。

        Args:
            item

        Time:
            O(N)

        Returns:
            count

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        return list(self).count(python_item)


    @wrap_exception
    def pop(self):
        """
        移除并返回队列最右边的元素。

        如果队列为空， 抛出 IndexError 。

        Args:
            None

        Time:
            O(1)

        Returns:
            pop_item

        Raises:
            IndexError: 尝试对空队列执行 pop 操作时抛出。
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        redis_item = self._client.rpop(self.name)
        if redis_item is None:
            raise IndexError

        python_item = self._decode(redis_item)
        return python_item


    @wrap_exception
    def block_pop(self, timeout=0):
        """
        移除并返回队列最右边的元素，
        如果队列中没有元素，那么阻塞 timeout 秒，直到获取元素或超时为止。

        Args:
            timeout: 等待元素时的最大阻塞秒数

        Time:
            O(1)

        Returns:
            None: 超时时返回
            pop_item: 被弹出的元素

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        # 每个非空 brpop 的结果都是一个列表 ['list of the pop item', 'pop item']
        redis_queue_name_and_item_list = self._client.brpop(self.name, timeout)
        if redis_queue_name_and_item_list is not None:
            redis_item = redis_queue_name_and_item_list[1]
            python_item = self._decode(redis_item)
            return python_item


    @wrap_exception
    def popleft(self):
        """
        移除并返回队列最左边的元素。

        如果队列为空，抛出 IndexError 。

        Args:
            None

        Time:
            O(1)

        Returns:
            pop_item

        Raises:
            IndexError: 尝试对空队列执行 pop 操作时抛出。
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        redis_item = self._client.lpop(self.name)
        if redis_item is None:
            raise IndexError
        python_item = self._decode(redis_item)
        return python_item


    @wrap_exception
    def block_popleft(self, timeout=0):
        """
        移除并返回队列最左边的元素，
        如果队列中没有元素，那么阻塞 timeout 秒，直到获取元素或超时为止。

        Args:
            timeout: 等待元素时的最大阻塞秒数

        Time:
            O(1)

        Returns:
            None: 超时时返回
            pop_item: 被弹出的元素

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        # 每个非空 blpop 的结果都是一个列表 ['list of the pop item', 'pop item']
        redis_queue_name_and_item_list = self._client.blpop(self.name, timeout)
        if redis_queue_name_and_item_list is not None:
            redis_item = redis_queue_name_and_item_list[1]
            python_item = self._decode(redis_item) 
            return python_item


    def __repr__(self):
        return format_key(self, self.name, list(self))


    @wrap_exception
    def __len__(self):
        """
        返回队列中的元素个数。
        空列表返回 0 。

        Time:
            O(1)

        Returns:
            len

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        return self._client.llen(self.name)


    def __iter__(self):
        """
        返回一个包含整个队列所有元素的迭代器。

        Time:
            O(N)

        Returns:
            iterator

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        try:
            all_redis_item = self._client.lrange(self.name, 0, -1)
            for redis_item in all_redis_item:
                python_item = self._decode(redis_item)
                yield python_item
        except redis.exceptions.ResponseError:
            raise TypeError

    
    def __delitem__(self, index):
        """
        删除列表中给定 index 上的值。

        Args:
            index ：可以是单个 key ，也可以是一个表示范围的 slice 。
            item

        Time:
            O(N)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        # TODO: 这个实现带有竞争条件
        all_python_item = list(self)

        self.delete()

        del all_python_item[index]
        if all_python_item != []:
            self.extend(all_python_item)
        """
        # del self[index]
        # ...

        # del self[:]
        if key.start is None and key.stop is None:
            self.delete()

        # del self[i:]
        if key.start is not None and key.stop is None:
            self._client.ltrim(self.name, 0, key.start-1)

        # del self[:j]
        if key.start is None and key.stop is not None:
            self._client.ltrim(self.name, key.stop, -1)

        # del self[i:j]
        # ...
        """


    def __getitem__(self, index):
        """
        返回列表中给定 index 上的值。

        Args:
            index ：可以是单个 key ，也可以是一个表示范围的 slice 。
            item

        Time:
            O(N)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        return list(self)[index]


    def __setitem__(self, index, item):
        """
        将列表中给定 index 上的值设置为 item 。

        Args:
            index ：可以是单个 key ，也可以是一个表示范围的 slice 。
            item

        Time:
            O(N)

        Returns:
            None

        Raises:
            TypeError: 尝试对非 list 类型的 key 进行操作时抛出。
        """
        # TODO: 这个实现带有竞争条件
        all_python_item = list(self)

        all_python_item[index] = item

        self.delete()
        self.extend(all_python_item)

########NEW FILE########
__FILENAME__ = dict
# coding:utf-8

__all__ = ['Dict']

__metaclass__ = type

import redis
import collections

from base_key import BaseKey
from helper import format_key, wrap_exception
from common_key_property_mixin import CommonKeyPropertyMixin

DELETE_FAIL_CAUSE_KEY_NOT_EXISTS = False

class Dict(BaseKey, CommonKeyPropertyMixin, collections.MutableMapping):

    """
    将 Redis 的 Hash 结构映射为字典对象。
    """

    def __repr__(self):
        return format_key(self, self.name, dict(self))


    @wrap_exception
    def __contains__(self, key):
        """
        检查字典是否包含给定 key 。

        Args:
            key

        Time:
            O(1)

        Returns:
            bool

        Raises:
            TypeError: Key 对象不是 Dict 类型时抛出。
        """
        return self._client.hexists(self.name, key)
    

    @wrap_exception
    def __setitem__(self, key, python_value):
        """ 
        将字典中键 key 的值设为 python_value 。
        如果键 key 已经关联了另一个值 ，那么将它覆盖。

        Args:
            key
            python_value

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: Key 对象不是 Dict 类型时抛出。
        """
        redis_value = self._encode(python_value)
        self._client.hset(self.name, key, redis_value)


    @wrap_exception
    def __getitem__(self, key):
        """ 
        返回字典中键 key 的值。
        如果键 key 在字典中不存在，那么抛出 KeyError 。

        Args:
            key

        Time:
            O(1)

        Returns:
            python_value

        Raises:
            KeyError: key 不存在时抛出。
            TypeError: Key 对象不是 Dict 类型时抛出。
        """
        redis_value = self._client.hget(self.name, key)
        if redis_value is None:
            raise KeyError

        python_value = self._decode(redis_value)
        return python_value

    
    @wrap_exception
    def __delitem__(self, key):
        """ 
        删除字典键 key 的值。
        如果键 key 的值不存在，那么抛出 KeyError 。

        Args:
            key

        Time:
            O(1)

        Returns:
            None

        Raises:
            KeyError: key 不存在时抛出。
            TypeError: Key 对象不是 Dict 类型时抛出。
        """
        status = self._client.hdel(self.name, key)
        if status == DELETE_FAIL_CAUSE_KEY_NOT_EXISTS:
            raise KeyError


    # @wrap_exception
    # 似乎因为 yield 的缘故，装饰器没办法在这里使用
    def __iter__(self):
        """ 
        返回一个包含字典里所有键的迭代器。

        Args:
            None

        Time:
            O(N)

        Returns:
            iterator
        
        Raises:
            TypeError: Key 对象不是 Dict 类型时抛出。
        """
        try:
            for key in self._client.hkeys(self.name):
                yield key
        except redis.exceptions.ResponseError:
            raise TypeError

   
    @wrap_exception
    def __len__(self):
        """
        返回字典中键-值对的个数。
        空字典返回 0 。

        Args:
            None

        Time:
            O(1)

        Returns:
            len

        Raises:
            TypeError: Key 对象不是 Dict 类型时抛出。
        """
        return self._client.hlen(self.name)

########NEW FILE########
__FILENAME__ = helper
# coding:utf-8

__all__ = [
    'format_key',
    'wrap_exception',
]

import redis
from functools import wraps

def format_key(key, name, value):
    """ 
    提供对 Key 对象的格式化支持。
    """
    type = key.__class__.__name__.title()
    return "{0} Key '{1}': {2}".format(type, name, value)

def wrap_exception(func):
    """
    redis-py 在对数据结构执行不属于它的操作时抛出 ResponseError
    这里将 ResponseError 转换为 TypeError
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.exceptions.ResponseError:
            raise TypeError
    return wrapper

########NEW FILE########
__FILENAME__ = set
# coding:utf-8

__all__ = ['Set']

__metaclass__ = type

import redis
import collections

from ooredis.const import REDIS_TYPE

from base_key import BaseKey
from helper import format_key, wrap_exception
from common_key_property_mixin import CommonKeyPropertyMixin

REMOVE_SUCCESS = True
MOVE_FAIL_CAUSE_MEMBER_NOT_IN_SET = 0

class Set(BaseKey, CommonKeyPropertyMixin):

    """
    将 Redis 的 Set 结构映射为集合对象。
    """

    def __repr__(self):
        return format_key(self, self.name, set(self))


    @wrap_exception
    def add(self, element):
        """ 
        将 element 加入到集合当中。

        如果 element 已经是集合的成员，不做动作。
        如果 key 不存在，一个空集合被创建并执行 add 动作。

        Args:
            element

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 当 key 非空且它不是 Redis 的 set 类型时抛出。
        """
        redis_element = self._encode(element)
        self._client.sadd(self.name, redis_element)


    @wrap_exception
    def remove(self, element):
        """ 
        如果 element 是集合的成员，移除它。

        如果要移除的元素不存在，抛出 KeyError 。

        Args：
            element

        Time：
            O(1)

        Returns:
            None

        Raises:
            TypeError: 当 key 非空且它不是 Redis 的 set 类型时抛出。
            KeyError： 要移除的元素 element 不存在于集合时抛出。
        """
        redis_element = self._encode(element)
        remove_state = self._client.srem(self.name, redis_element)
        if remove_state != REMOVE_SUCCESS:
            raise KeyError


    @wrap_exception
    def pop(self):
        """ 
        移除并返回集合中任意一个成员。
        如果集合为空，抛出 KeyError 。

        Args:
            None

        Time：
            O(1)

        Returns:
            member: 被移除的集合成员。

        Raises:
            TypeError: 当 key 非空且它不是 Redis 的 set 类型时抛出。
            KeyError: 集合为空集时抛出。
        """
        redis_member = self._client.spop(self.name)
        if redis_member is None:
            raise KeyError

        python_member = self._decode(redis_member)
        return python_member


    @wrap_exception
    def random(self):
        """ 
        随机返回集合中的某个元素。

        该操作和 pop 方法相似，但 pop 将随机元素从集合中移除并返回，
        而 random 则仅仅返回随机元素，而不对集合进行任何改动。

        Args:
            None

        Time:
            O(1)

        Returns:
            member: 当集合非空时，返回一个成员。
            None: 当集合为空集时，返回 None 。

        Raises:
            TypeError: 当 key 非空且它不是 Redis 的 set 类型时抛出。
        """
        redis_element = self._client.srandmember(self.name)
        python_member = self._decode(redis_element)
        return python_member


    @wrap_exception
    def move(self, destination, member):
        """ 
        将集合成员 member 移动到另一个集合 destination 中去。

        具体参考 Redis 命令：SMOVE。

        Args:
            destination: 指定被移动元素的目的地集合， 必须是一个集合 key 对象。
            member: 被移动的源集合的成员。

        Time:
            O(1)

        Returns:
            None

        Raises:
            KeyError: 要被移动的元素 member 不存在于集合时抛出。
            TypeError: 当 key 非空且它不是 Redis 的 set 类型时抛出。
        """
        redis_member = self._encode(member)
        state = self._client.smove(self.name, destination.name, redis_member)
        if state == MOVE_FAIL_CAUSE_MEMBER_NOT_IN_SET:
            raise KeyError


    # disjoint, 不相交

    def isdisjoint(self, other):
        """ 
        检查集合是否和另一个集合不相交。

        Args:
            other: 一个 Python 集合或集合 Key 对象。
        
        Returns:
            bool

        Time:
            O(N)

        Raises:
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        other_member = set(other)
        self_member = set(self)

        return self_member.isdisjoint(other_member)


    # subset, <= , 子集

    def __le__(self, other):
        """ 
        测试集合是否是另一个集合的子集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Returns:
            bool

        Time:
            O(N)

        Raises:
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) <= set(other)

    issubset = __le__


    # proper subset, < , 真子集

    def __lt__(self, other):
        """ 
        测试集合是否是另一个集合的真子集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Returns:
            bool

        Time:
            O(N)

        Raises:
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) < set(other)


    # superset, >= , 超集

    def __ge__(self, other):
        """ 
        测试集合是否是另一个集合的超集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Returns:
            bool

        Time:
            O(N)

        Raises:
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) >= set(other)

    issuperset = __ge__


    # proper superset, > , 真超集

    def __gt__(self, other):
        """ 
        测试集合是否是另一个集合的真超集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Returns:
            bool

        Time:
            O(N)

        Raises:
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) > set(other)


    # union, | , 并集

    def __or__(self, other):
        """ 
        返回集合和另一个集合的并集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Time:
            O(N)

        Returns:
            set

        Raises：
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) | set(other)

    __ror__ = __or__
    __ror__.__doc__ = """ __or__的反向方法，用于支持多集合对象进行并集操作。"""


    @wrap_exception
    def __ior__(self, other):
        """
        计算 self 和 other 之间的并集，并将结果设置为 self 的值。
        other 可以是另一个集合 key 对象，或者 Python set 的实例。

        Args:
            other

        Time:
            O(N)

        Returns:
            self: Python 指定该方法必须返回 self 。

        Raises:
            TypeError: 当 key 或 other 的类型不符合要求时抛出。
        """
        if isinstance(other, set):
            python_elements = set(self) | other
            redis_elements = map(self._encode, python_elements)
            self._client.sadd(self.name, *redis_elements)
        else:
            self._client.sunionstore(self.name, [self.name, other.name])

        return self
 

    # intersection, & , 交集

    def __and__(self, other):
        """ 
        返回集合和另一个集合的交集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Time:
            O(N)

        Returns:
            set

        Raises：
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) & set(other)

    __rand__ = __and__
    __rand__.__doc__ = """ __and__的反向方法，用于支持多集合进行交集操作。 """


    @wrap_exception
    def __iand__(self, other):
        """
        计算 self 和 other 之间的交集，并将结果设置为 self 的值。
        other 可以是另一个集合 key 对象，或者 Python set 的实例。

        Args:
            other

        Time:
            O(N)

        Returns:
            self: Python 指定该方法必须返回 self 。

        Raises:
            TypeError: 当 key 或 other 的类型不符合要求时抛出。
        """
        if isinstance(other, set):
            python_elements = set(self) - (set(self) & other)
            redis_elements = map(self._encode, python_elements)
            self._client.srem(self.name, *redis_elements)
        elif other.exists and other._represent != REDIS_TYPE['set']:
            raise TypeError
        else:
            self._client.sinterstore(self.name, [self.name, other.name])

        return self


    # difference, - , 差集

    def __sub__(self, other):
        """ 
        返回集合对另一个集合的差集。

        Args:
            other: 一个 Python 集合或集合 key 对象。

        Time:
            O(N)

        Returns:
            set

        Raises：
            TypeError: 当 key 或 other 不是 Set 类型时抛出。
        """
        return set(self) - set(other)


    def __rsub__(self, other):
        """ 
        __sub__的反向方法，
        用于支持多集合进行差集运算。
        """
        # WARNING: 注意这里的位置不要弄反。
        return set(other) - set(self)


    @wrap_exception
    def __isub__(self, other):
        """
        计算 self 和 other 之间的差集，并将结果设置为 self 的值。
        other 可以是另一个集合 key 对象，或者 Python set 的实例。

        Args:
            other

        Time:
            O(N)

        Returns:
            self: Python指定该方法必须返回self。

        Raises:
            TypeError: 当 key 或 other 的类型不符合要求时抛出。
        """
        if isinstance(other, set):
            python_elements = set(self) & other
            redis_elements = map(self._encode, python_elements)
            self._client.srem(self.name, *redis_elements)
        else:
            self._client.sdiffstore(self.name, [self.name, other.name])

        return self


    # symmetric difference, ^ ， 对等差

    def __xor__(self, other):
        """ 
        返回集合对另一个集合的对等差集。

        Args:
            other: 一个Python集合或集合key对象。

        Returns:
            set

        Time:
            O(N)

        Raises:
            TypeError: 当key或other不是Set类型时抛出。
        """
        return set(self) ^ set(other)

    __rxor__ = __xor__
    __rxor__.__doc__ = \
    """ __xor__的反向方法，用于支持多集合的对等差集运算。 """


    @wrap_exception
    def __len__(self):
        """ 
        返回集合中元素的个数。
        当集合为空集时，返回 0 。

        Args:
            None

        Time:
            O(1)

        Returns:
            len 

        Raises:
            TypeError: 当 key 不是 Redis 的 set 类型时抛出。
        """
        return self._client.scard(self.name)


    def __iter__(self):
        """ 
        返回一个包含集合中所有元素的迭代器。

        Time:
            O(N)

        Returns:
            iterator

        Raises:
            TypeError: 当 key 不是 Redis 的 set 类型时抛出。
        """
        try:
            for redis_member in self._client.smembers(self.name):
                python_member = self._decode(redis_member)
                yield python_member
        except redis.exceptions.ResponseError:
            raise TypeError


    @wrap_exception
    def __contains__(self, element):
        """ 
        检查给定元素 element 是否集合的成员。

        Args:
            element

        Time:
            O(1)

        Returns:
            bool: element 是集合成员的话返回 True ，否则返回 False 。

        Raises:
            TypeError: 当 key 不是 Redis 的 set 类型时抛出。
        """
        redis_element = self._encode(element)
        return self._client.sismember(self.name, redis_element)

########NEW FILE########
__FILENAME__ = set_and_get_op_mixin
# coding: utf-8

__all__ = ['SetAndGetOpMixin']

__metaclass__ = type

from functools import wraps
from ooredis.const import REDIS_TYPE

from helper import wrap_exception

def raise_when_set_wrong_type(func):
    """
    set/setex/setnx 命令可以无视类型进行设置的命令，为了保证类型的限制，
    ooredis 对一个非 string 类型进行 set/setex/setnx 将引发 TypeError 异常。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.exists and \
           self._represent != REDIS_TYPE['string']:
            raise TypeError
        return func(*args, **kwargs)
    return wrapper

class SetAndGetOpMixin:
    
    """
    包装起 Redis 的 set 、 get 和 setget 等操作。
    """

    @raise_when_set_wrong_type
    def set(self, python_value):
        """
        为 Key 对象指定值。

        Args:
            python_value: 为 Key 对象指定的值。

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 当 key 非空但 Key 对象不是指定类型时抛出。
        """
        redis_value = self._encode(python_value)

        self._client.set(self.name, redis_value)


    @raise_when_set_wrong_type
    def setnx(self, python_value):
        """
        将 Key 对象的值设为 python_value ，当且仅当 Key 不存在。

        Args:
            python_value

        Time:
            O(1)

        Returns:
            bool: 如果设置成功，那么返回 True ，否则返回 False 。

        Raises:
            TypeError: 当 Key 对象非空且不是 Redis 的字符串类型时抛出。
        """
        redis_value = self._encode(python_value)

        return self._client.setnx(self.name, redis_value)


    @raise_when_set_wrong_type
    def setex(self, python_value, ttl_in_second):
        """
        将 Key 对象的值设为 python_value ，
        并将 Key 对象的生存时间设为 ttl_in_second 。

        Args:
            python_value
            ttl_in_second: 生存时间，以秒为单位。

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 当 Key 对象非空且不是 Redis 的字符串类型时抛出。
        """
        redis_value = self._encode(python_value)

        return self._client.setex(self.name, redis_value, ttl_in_second)


    @wrap_exception
    def get(self):
        """
        返回 Key 对象的值。

        Time:
            O(1)

        Returns:
            python_value： Key 对象的值。
            None: key 不存在时返回。

        Raises:
            TypeError: 当 key 非空但 Key 对象不是指定类型时抛出。
        """
        redis_value = self._client.get(self.name)

        python_value = self._decode(redis_value)

        return python_value

   
    @wrap_exception
    def getset(self, python_value):
        """ 
        修改 Key 对象的值，并返回 Key 对象之前储存的值。

        Args:
            python_value: Key 对象的新值。

        Time:
            O(1)

        Returns:
            None: 当 key 不存时(没有前值)返回。
            python_value:  Key 对象之前的值。

        Raises:
            TypeError: 当 key 非空但 Key 对象不是指定类型时抛出。
        """
        new_redis_value = self._encode(python_value)

        old_redis_value = self._client.getset(self.name, new_redis_value)

        python_value = self._decode(old_redis_value)

        return python_value

########NEW FILE########
__FILENAME__ = sorted_set
# coding: utf-8

__all__ = ['SortedSet']

__metaclass__ = type

from functools import partial
from ooredis.const import (
    LEFTMOST,
    RIGHTMOST,
    DEFAULT_INCREMENT,
    DEFAULT_DECREMENT,
)

from base_key import BaseKey
from helper import format_key, wrap_exception
from common_key_property_mixin import CommonKeyPropertyMixin

# redis command execute status code
MEMBER_NOT_IN_SET_AND_REMOVE_FALSE = 0
MEMBER_NOT_IN_SET_AND_DELETE_FALSE = 0
MEMBER_NOT_IN_SET_AND_GET_SCORE_FALSE = None

class SortedSet(BaseKey, CommonKeyPropertyMixin):

    """ 
    将 Redis 的 sorted set 结构映射为有序集对象。
    """

    def __repr__(self):
        return format_key(self, self.name, list(self))
  

    @wrap_exception
    def __len__(self):
        """ 
        返回有序集的基数。

        Args:
            None

        Time:
            O(1)

        Returns:
            int: 有序集的基数，集合不存在或为空时返回0。

        Raises：
            TypeError: 当key不是有序集类型时抛出。
        """
        return self._client.zcard(self.name)


    @wrap_exception
    def __contains__(self, element):
        """ 
        检查给定元素 element 是否是有序集的成员。 

        Args:
            element

        Time:
            O(log(N))

        Returns:
            bool: 如果 element 是集合的成员，返回 True ，否则 False 。

        Raises:
            TypeError: 当 key 不是有序集类型时抛出。
        """
        # 因为在 redis 里 zset 没有 set 那样的 SISMEMBER 命令，
        # 所以这里用 ZSCORE 命令 hack 一个：
        # 如果 ZSCORE key member 不为 None ，证明 element 是有序集成员。
        # 注意，这里不能用 self.score 来实现，因为这两个方法互相引用。
        redis_element = self._encode(element)
        element_score = self._client.zscore(self.name, redis_element)
        return element_score is not None


    @wrap_exception
    def __setitem__(self, member, new_score):
        """ 
        将元素 member 的 score 值更新为 new_score 。

        如果 member 不存在于有序集，
        那么将 member 加入到有序集， score 值等于 new_score 。

        Args:
            member
            new_score

        Time:
            O(1)

        Returns:
            None

        Raises:
            TypeError: 当key不是有序集类型时抛出。
        """
        redis_memeber = self._encode(member)
        self._client.zadd(self.name, redis_memeber, new_score)


    @wrap_exception
    def __getitem__(self, index):
        """ 
        返回有序集指定下标内的元素。

        Args:
            index: 一个下标或一个 slice 对象。

        Returns:
            dict： 使用下标时，返回一个字典，包含 member 和 score 。
            list：使用 slice 对象时，返回一个列表， 列表中每个项都是一个字典。

        Time:
            O(log(N)+M) ， N 为有序集的基数，而 M 为结果集的基数。

        Raises:
            KeyError: index 下标超出范围时抛出。
            TypeError: 当 key 不是有序集类型时抛出。
        """
        item_to_dict_list = \
            partial(map,
                    lambda item: dict(
                        member=self._decode(item[0]), 
                        score=item[1]
                    ))

        if isinstance(index, slice):
            items = self._client.zrange(self.name, LEFTMOST, RIGHTMOST, withscores=True)
            return item_to_dict_list(items[index])
        else:
            items = self._client.zrange(self.name, index, index, withscores=True)
            return item_to_dict_list(items)[0]


    @wrap_exception
    def __delitem__(self, index):
        """ 
        删除有序集指定下标内的元素。

        Args:
            index: 下标或一个 slice 对象。

        Time:
            O(log(N)+M) ， N 为有序集的基数，而 M 为被移除成员的数量。

        Returns:
            None

        Raises:
            KeyError: index 下标超出范围时抛出。
            TypeError: 当 key 不是有序集类型时抛出。
        """
        if isinstance(index, slice):
            start = LEFTMOST if index.start is None else index.start
            stop = RIGHTMOST if index.stop is None else index.stop-1

            self._client.zremrangebyrank(self.name, start, stop)
        else:
            status = self._client.zremrangebyrank(self.name, index, index)
            if status == MEMBER_NOT_IN_SET_AND_DELETE_FALSE:
                raise IndexError


    @wrap_exception
    def remove(self, member):
        """ 
        移除有序集成员 member ，如果 member 不存在，不做动作。

        Args:
            member: 要移除的成员。

        Time:
            O(log(N))

        Returns:
            None

        Raises:
            TypeError: 当 key 不是有序集类型时抛出。
        """
        redis_member = self._encode(member)
        self._client.zrem(self.name, redis_member)


    @wrap_exception
    def rank(self, member):
        """ 
        按从小到大的顺序(正序)返回有序集成员 member 的 score 值的排名。

        Args:
            member: 被检查的成员。

        Time:
            O(log(N))

        Returns:
            None: 当 member 不是有序集的成员时返回
            int: member 的 score 排名。

        Raises:
            TypeError: 当 key 不是有序集类型时由 in 语句抛出。
        """
        redis_member = self._encode(member)
        return self._client.zrank(self.name, redis_member)


    @wrap_exception
    def reverse_rank(self, member):
        """
        按从大到小的顺序(逆序)返回有序集成员 member 的 score 值排名。

        Args:
            member

        Time:
            O(log(N))

        Returns:
            None: 当 member 不是有序集的成员时返回
            int: member 的 score 值排名

        Raises:
            TypeError: 当 key 不是有序集类型时由 in 语句抛出。
        """
        redis_member = self._encode(member)
        return self._client.zrevrank(self.name, redis_member)


    @wrap_exception
    def score(self, member):
        """ 
        返回有序集中成员 member 的 score 值。

        Args:
            member

        Time:
            O(1)

        Returns:
            None: 当 member 不是有序集的成员时返回
            float: 以浮点值表示的 score 值。

        Raises:
            TypeError: 当 key 不是有序集类型时抛出，由 in 语句抛出。
        """
        redis_member = self._encode(member)
        return self._client.zscore(self.name, redis_member)


    @wrap_exception
    def incr(self, member, increment=DEFAULT_INCREMENT):  
        """ 
        将 member 的 score 值加上 increment 。 

        当 key 不存在，或 member 不是 key 的成员时，
        self.incr(member, increment) 等同于 self[member] = increment

        Args:
            member: 集合成员
            increment: 增量，默认为1。

        Time:
            O(log(N))

        Returns:
            float: member 成员的新 score 值。

        Raises:
            TypeError: 当 key 不是有序集类型时抛出。
        """
        redis_member = self._encode(member)
        return self._client.zincrby(self.name, redis_member, increment)


    def decr(self, member, decrement=DEFAULT_DECREMENT):
        """ 
        将 member 的 score 值减去 decrement 。 

        当 key 不存在，或 member 不是 key 的成员时，
        self.decr(member, decrement) 等同于 self[member] = 0-decrement

        Args:
            member: 集合成员
            decrement: 减量，默认为 1 。

        Time:
            O(log(N))

        Returns:
            float: member 成员的新 score 值。

        Raises:
            TypeError: 当 key 不是有序集类型时抛出。
        """
        return self.incr(member, 0-decrement)

########NEW FILE########
__FILENAME__ = string
# coding: utf-8

__all__ = ['String']

__metaclass__ = type

from helper import format_key
from base_key import BaseKey
from common_key_property_mixin import CommonKeyPropertyMixin
from set_and_get_op_mixin import SetAndGetOpMixin

class String(BaseKey, CommonKeyPropertyMixin, SetAndGetOpMixin):

    """
    为储存单个值的 Key 对象提供 set，get 和 getset 等操作。
    """

    def __repr__(self):
        return format_key(self, self.name, self.get())

########NEW FILE########
__FILENAME__ = float_type_case
# coding: utf-8

class FloatTypeCase:

    """ 
    处理 float 类型值的转换。 
    """

    @staticmethod
    def encode(value):
        """
        尝试将输入值转换成 float 类型，
        如果转换失败，抛出 TypeError 。
        """
        return float(value)

    @staticmethod
    def decode(value):
        """ 
        尝试将输入值转换成 float 类型，
        如果转换失败，抛出 TypeError 。
        """
        if value is not None:
            return float(value)

########NEW FILE########
__FILENAME__ = generic_type_case
# coding: utf-8

from numbers import Integral

class GenericTypeCase:

    """ 
    通用类型转换类，可以处理 str/unicode/int/float 类型值。
    """

    @staticmethod
    def encode(value):
        """ 
        接受 int/long/str/unicode/float 类型值，
        否则抛出 TypeError 。
        """
        if isinstance(value, basestring) or \
           isinstance(value, Integral) or \
           isinstance(value, float):
            return value

        raise TypeError

    @staticmethod
    def decode(value):
        """ 
        将传入值转换成 int/long/str/unicode/float 等格式。
        因为 redis 只返回字符串值，这个函数也只接受字符串值，
        否则抛出 AssertionError 。
        """
        if value is None:
            return
        
        # 以下类型转换规则是基于 Redis 只返回
        # 字符串值这个假设之上来构造的
        # 这里用一个断言来保证这种假设
        assert isinstance(value, basestring)

        # 从最限定的类型开始转换
        try: return int(value)
        except:
            try: return float(value)
            except:
                try: return str(value)
                except:
                    return unicode(value)

########NEW FILE########
__FILENAME__ = int_type_case
# coding: utf-8

class IntTypeCase:

    """ 
    处理 int(long) 类型值的转换。
    """

    @staticmethod
    def encode(value):
        """ 
        接受 int 类型值，否则抛出 TypeError 。 
        """
        try:
            return int(value)
        except ValueError:
            raise TypeError

    @staticmethod
    def decode(value):
        """ 
        尝试将值转回 int 类型，
        如果转换失败，抛出 TypeError。
        """
        if value is None:
            return

        try:
            return int(value)
        except ValueError:
            raise TypeError

########NEW FILE########
__FILENAME__ = json_type_case
# coding: utf-8

import json

class JsonTypeCase:

    """ 
    用于将 python 对象转化为 JSON 对象。 
    """

    @staticmethod
    def encode(value):
        """ 
        将值转成 JSON 对象，
        如果值不能转成 JSON 对象，抛出 TypeError 异常。
        """
        return json.dumps(value)
    
    @staticmethod
    def decode(value):
        """ 
        将 Json 对象转回原来的类型。
        如果转换失败，抛出 TypeError 。
        """
        if value is None:
            return

        return json.loads(value)

########NEW FILE########
__FILENAME__ = serialize_type_case
# coding: utf-8

import pickle

class SerializeTypeCase:

    """ 
    处理 python 对象序列化(使用 pickle 模块)。
    """

    @staticmethod
    def encode(value):
        """ 
        将值序列化(包括自定义类和 Python 内置类)。
        如果传入的值无法被序列化，抛出 TypeError 。
        """
        try:
            return pickle.dumps(value)
        except pickle.PicklingError:
            raise TypeError

    @staticmethod
    def decode(value):
        """ 
        将序列化的字符串转换回原来的对象，
        如果传入值无法进行反序列化，抛出 TypeError 。
        """
        if value is None:
            return

        try:
            return pickle.loads(value)
        except pickle.UnpicklingError:
            raise TypeError

########NEW FILE########
__FILENAME__ = string_type_case
# coding: utf-8

class StringTypeCase:

    """ 
    处理字符串类型( str 或 unicode )值的转换。 
    """

    @staticmethod
    def encode(value):
        """ 
        接受 basestring 子类的值( str 或 unicode )，
        否则抛出 TypeError 。
        """
        if isinstance(value, basestring):
            return value

        raise TypeError

    @staticmethod
    def decode(value):
        """ 
        将值转回 str 或 unicode 类型。 
        """
        if value is None:
            return 

        try:
            return str(value)
        except:
            return unicode(value)

########NEW FILE########
__FILENAME__ = test_base_key
#! /usr/bin/env python2.7
# coding:utf-8

import redis
import unittest

from ooredis.key.base_key import BaseKey
from ooredis.const import REDIS_TYPE
from ooredis.type_case import GenericTypeCase
from ooredis.client import connect, get_client

class TestBaseKey(unittest.TestCase):
    
    def setUp(self):
        connect()
    
        self.name = "name"
        self.value = "value"

        self.key = BaseKey(self.name)

        self.redispy = redis.Redis()
        self.redispy.flushdb()

    def tearDown(self):
        self.redispy.flushdb()


    # __init__

    def test_init_key(self):
        self.assertTrue(
            isinstance(self.key._client, redis.Redis)
        )

        self.assertEqual(
            get_client(),
            self.key._client
        )

        self.assertEqual(
            self.key._encode,
            GenericTypeCase.encode
        )
        self.assertEqual(
            self.key._decode,
            GenericTypeCase.decode
        )


    # __eq__

    def test__eq__TRUE(self):
        self.assertEqual(
            self.key, 
            BaseKey(self.name)
        )

    def test__eq__FALSE(self):
        self.assertNotEqual(
            self.key,
            BaseKey('another-key')
        )

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_common_key_property_mixin
# coding:utf-8

import redis
import unittest

from ooredis.key.base_key import BaseKey
from ooredis.key.common_key_property_mixin import CommonKeyPropertyMixin
from ooredis.const import REDIS_TYPE
from ooredis.type_case import GenericTypeCase
from ooredis.client import connect, get_client

class KeyWithProperty(BaseKey, CommonKeyPropertyMixin):
    pass

class TestCommonKeyPropertyMixin(unittest.TestCase):
    
    def setUp(self):
        connect()
    
        self.name = "name"
        self.value = "value"

        self.key = KeyWithProperty(self.name)

        self.redispy = redis.Redis()
        self.redispy.flushdb()

    def tearDown(self):
        self.redispy.flushdb()


    # _represent

    def test_represent(self):
        # string
        self.redispy.set('string', 'string')
        self.assertEqual(
            KeyWithProperty('string')._represent,
            REDIS_TYPE['string']
        )

        # list
        self.redispy.lpush('list', 'itme')
        self.assertEqual(
            KeyWithProperty('list')._represent,
            REDIS_TYPE['list']
        )

        # set
        self.redispy.sadd('set', 'element')
        self.assertEqual(
            KeyWithProperty('set')._represent,
            REDIS_TYPE['set']
        )

        # sorted set
        self.redispy.zadd('sorted_set', 'value', 30)
        self.assertEqual(
            KeyWithProperty('sorted_set')._represent,
            REDIS_TYPE['sorted_set']
        )

        # hash
        self.redispy.hset('hash', 'field', 'value')
        self.assertEqual(
            KeyWithProperty('hash')._represent,
            REDIS_TYPE['hash']
        )

        # not exists key
        self.assertFalse(
            self.redispy.exists('not_exists_key')
        )
        self.assertEqual(
            KeyWithProperty('not_exists_key')._represent,
            REDIS_TYPE['not_exists']
        )


    # ttl

    def test_ttl_with_PERSIST_KEY(self):
        self.redispy.set(self.key.name, self.value)

        self.assertIsNone(
            self.key.ttl
        )

    def test_ttl_with_VOLATILE_KEY(self):
        self.redispy.expire(self.key.name, 300)

        self.assertTrue(
            self.key.ttl <= 300
        )

    def test_ttl_with_NOT_EXISTS_KEY(self):
        self.redispy.delete(self.key.name)

        self.assertIsNone(
            self.key.ttl
        )


    # exists

    def test_exists_FALSE(self):
        self.assertFalse(
            self.key.exists
        )

    def test_exists_TRUE(self):
        self.redispy.set(self.key.name, self.value)

        self.assertTrue(
            self.key.exists
        )


    # delete

    def test_delete_EXISTS_KEY(self):
        self.redispy.set(self.key.name, self.value)

        self.key.delete()

        self.assertFalse(
            self.key.exists
        )

    def test_delete_NOT_EXISTS_KEY(self):
        self.key.delete()

        self.assertFalse(
            self.key.exists
        )


    # expire

    def test_expire_with_EXISTS_KEY(self):
        self.redispy.set(self.key.name, self.value)

        self.key.expire(30000)

        self.assertTrue(
            self.key.ttl <= 30000
        )

    def test_expire_RAISE_when_KEY_NOT_EXISTS(self):
        with self.assertRaises(TypeError):
            self.key.expire(30000)


    # expireat

    def test_expireat_with_EXISTS_KEY(self):
        self.redispy.set(self.key.name, self.value)

        self.key.expireat(1355292000)

        self.assertIsNotNone(
            self.key.ttl
        )

    def test_expireat_RAISE_when_KEY_NOT_EXISTS(self):
        with self.assertRaises(TypeError):
            self.key.expireat(1355292000)   # 2012.12.12


    # persist

    def test_persist_RAISE_when_KEY_NOT_EXISTS(self):
        with self.assertRaises(Exception):
            self.key.persist()

    def test_persist_with_PERSIST_KEY(self):
        self.redispy.set(self.key.name, self.value)

        self.assertIsNone(
            self.key.persist()
        )

    def test_persist_with_VOLATILE_KEY(self):
        self.redispy.setex(self.key.name, self.value, 3000)

        self.key.persist()

        self.assertIsNone(
            self.key.ttl
        )


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_counter
# coding: utf-8

import redis
import unittest

from ooredis.client import connect
from ooredis.key.helper import format_key
from ooredis.key.counter import Counter

class TestCounter(unittest.TestCase):
    
    def setUp(self):
        connect()

        self.redispy = redis.Redis()
        self.redispy.flushdb()

        self.tearDown()

        self.str = 'str'

        self.name = 'counter'
        self.value = 10086

        self.counter = Counter(self.name)

    def tearDown(self):
        self.redispy.flushdb()

    def set_wrong_type(self, key_object):
        self.redispy.set(key_object.name, 'string')

    # __repr__

    def test_repr_when_NOT_EXISTS(self):
        self.assertEqual(
            repr(self.counter),
            format_key(self.counter, self.name, str(None))
        )

    def test_repr_when_EXISTS(self):
        self.counter.set(self.value)
        
        self.assertEqual(
            repr(self.counter),
            format_key(self.counter, self.name, self.value)
        )
        
    # incr

    def test_incr(self):
        self.assertEqual(
            self.counter.incr(),
            1
        )

    def test_incr_with_INCREMENT(self):
        self.assertEqual(
            self.counter.incr(2),
            2
        )

    def test_incr_RAISE_when_INPUT_TYPE(self):
        with self.assertRaises(TypeError):
            self.counter.incr(self.str)

    def test_incr_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.counter)
            self.counter.incr()

    # decr

    def test_decr(self):
        self.assertEqual(
            self.counter.decr(),
            -1
        )

    def test_decr_with_DECREMENT(self):
        self.assertEqual(
            self.counter.decr(2),
            -2
        )

    def test_decr_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.counter.decr(self.str)

    def test_decr_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.counter)
            self.counter.decr()

    # iadd

    def test_iadd(self):
        self.counter += 1

        self.assertEqual(
            self.counter.get(),
            1
        )

    def test_iadd_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.counter += self.str

    def test_iadd_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.counter)
            self.counter += 1

    # isub

    def test_isub(self):
        self.counter -= 1

        self.assertEqual(
            self.counter.get(),
            -1
        )

    def test_isub_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.counter -= self.str

    def test_isub_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.counter)
            self.counter -= 1

    # get
    def test_get(self):
        self.counter.set(self.value)

        self.assertEqual(
            self.counter.get(),
            self.value
        )

    def test_get_RETURN_NONE_when_NOT_EXISTS(self):
        self.assertIsNone(
            self.counter.get()
        )

    def test_get_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.counter)
            self.counter.get()

    # set

    def test_set(self):
        self.counter.set(self.value)
        self.assertEqual(
            self.counter.get(),
            self.value
        )

    def test_set_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.counter.set(self.str) 

    # getset

    def test_getset_when_NOT_EXISTS(self):
        previous_value = self.counter.getset(self.value)

        self.assertIsNone(
            previous_value
        )

        self.assertEqual(
            self.counter.get(),
            self.value
        )

    def test_getset_when_EXISTS(self):
        self.counter.getset(self.value)

        self.new_value = 123
        previous_value = self.counter.getset(self.new_value)

        self.assertEqual(
            previous_value,
            self.value
        )

        self.assertEqual(
            self.counter.get(),
            self.new_value
        )

    def test_getset_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.counter.getset(self.str)

########NEW FILE########
__FILENAME__ = test_deque
# coding: utf-8

from redis import Redis
from ooredis import Deque
from unittest import TestCase

from ooredis.key.helper import format_key
from ooredis.type_case import JsonTypeCase

class TestDeque(TestCase):

    def setUp(self):
        self.redispy = Redis()

        self.item = 10086 
        self.another_item = 10000

        self.multi_item = [123, 321, 231]

        self.d = Deque('deque', type_case=JsonTypeCase)
   
    def tearDown(self):
        self.redispy.flushdb()

    # helper

    def set_wrong_type(self, key_object):
        self.redispy.set(key_object.name, 'string')

    # __repr__

    def test__repr__(self):
        assert repr(self.d) == format_key(self.d, self.d.name, list(self.d))

    # __len__

    def test_len_when_EMPTY(self):
        assert len(self.d) == 0

    def test_len_when_NOT_EMPTY(self):
        self.d.append(self.item)
        assert len(self.d) == 1
    
    def test_len_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            len(self.d)

    # append

    def test_append_when_EMPTY(self):
        self.d.append(self.item)

        assert list(self.d) == [self.item]
        assert len(self.d) == 1

    def test_append_when_NOT_EMPTY(self):
        self.d.append(self.item)
        self.d.append(self.another_item)

        assert list(self.d) == [self.item, self.another_item]
        assert len(self.d) == 2

    def test_append_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.append(self.item)

    # extend

    def test_extend_when_EMPTY(self):
        self.d.extend(self.multi_item)

        assert list(self.d) == self.multi_item
        assert len(self.d) == len(self.multi_item)

    def test_extend_when_NOT_EMPTY(self):
        self.d.extend(self.multi_item)

        self.d.extend(self.multi_item)

        assert list(self.d) == self.multi_item * 2
        assert len(self.d) == len(self.multi_item) * 2

    def test_extend_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.extend(self.multi_item)

    # extendleft

    def test_extendleft_when_EMPTY(self):
        self.d.extendleft(self.multi_item)

        assert list(self.d) == list(reversed(self.multi_item))
        assert len(self.d) == len(self.multi_item)

    def test_extendleft_when_NOT_EMPTY(self):
        self.d.extendleft(self.multi_item)
        
        self.d.extendleft(self.multi_item)

        assert list(self.d) == list(reversed(self.multi_item)) * 2
        assert len(self.d) == len(self.multi_item) * 2

    def test_extend_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.extendleft(self.multi_item)

    # appendleft

    def test_appendleft_when_EMPTY(self):
        self.d.appendleft(self.item)

        assert list(self.d) == [self.item]
        assert len(self.d) == 1

    def test_appendleft_when_NOT_EMPTY(self):
        self.d.appendleft(self.item)
        self.d.appendleft(self.another_item)

        assert list(self.d) == [self.another_item, self.item]
        assert len(self.d) == 2

    def test_append_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.appendleft(self.item)

    # __iter__

    def test__iter__when_EMPTY(self):
        assert list(self.d) == []

    def test__iter__when_NOT_EMPTY(self):
        self.d.append(self.item)
        assert list(self.d) == [self.item]

    def test__iter__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            list(self.d)

    # clear

    def test_clear_when_EMPTY(self):
        self.d.clear()
        assert list(self.d) == []
        assert len(self.d) == 0

    def test_clear_when_NOT_EMPTY(self):
        self.d.append(self.item)

        self.d.clear()

        assert list(self.d) == []
        assert len(self.d) == 0

    # count

    def test_count_when_EMPTY(self):
        assert self.d.count(self.item) == 0

    def test_count_when_NOT_EMPTY_and_ITEM_FOUNDED(self):
        self.d.append(self.item)
        assert self.d.count(self.item) == 1

        self.d.append(self.item)
        assert self.d.count(self.item) == 2

        self.d.append(self.another_item)
        assert self.d.count(self.item) == 2

    def test_count_when_NOT_EMPTY_and_ITEM_NOT_FOUND(self):
        self.d.append(self.item)
        assert self.d.count(self.another_item) == 0

    def test_count_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.count(self.item)

    # pop

    def test_pop_RAISE_when_EMPTY(self):
        with self.assertRaises(IndexError):
            self.d.pop()

    def test_pop_with_SINGLE_ITEM(self):
        self.d.append(self.item)

        assert self.d.pop() == self.item
        assert len(self.d) == 0

    def test_pop_with_MULTI_ITEM(self):
        self.d.append(self.item)
        self.d.append(self.another_item)

        assert self.d.pop() == self.another_item
        assert len(self.d) == 1

    def test_pop_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.pop()


    # block_pop

    def test_block_pop_RETURN_NONE_when_EMPTY(self):
        self.assertIsNone(
            self.d.block_pop(1)
        )

    def test_block_pop_with_SINGLE_ITEM(self):
        self.d.append(self.item)

        self.assertEqual(
            self.d.block_pop(1),
            self.item
        )

        self.assertEqual(
            len(self.d),
            0
        )

    def test_block_pop_with_MULTI_ITEM(self):
        self.d.append(self.item)
        self.d.append(self.another_item)

        self.assertEqual(
            self.d.block_pop(),
            self.another_item
        )

        self.assertEqual(
            len(self.d),
            1
        )

    def test_pop_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.block_pop()


    # popleft

    def test_popleft_RAISE_when_EMPTY(self):
        with self.assertRaises(IndexError):
            self.d.popleft()

    def test_popleft_with_SINGLE_ITEM(self):
        self.d.appendleft(self.item)

        assert self.d.popleft() == self.item
        assert len(self.d) == 0

    def test_popleft_with_MULTI_ITEM(self):
        self.d.appendleft(self.item)
        self.d.appendleft(self.another_item)

        assert self.d.popleft() == self.another_item
        assert len(self.d) == 1

    def test_popleft_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.popleft()


    # block_popleft

    def test_block_popleft_RETURN_NONE_when_DEQUE_EMPTY(self):
        self.assertIsNone(
            self.d.block_popleft(1)
        )

    def test_block_popleft_with_SINGLE_ITEM(self):
        self.d.appendleft(self.item)

        self.assertEqual(
            self.d.block_popleft(1),
            self.item
        )

        self.assertEqual(
            len(self.d),
            0
        )

    def test_block_popleft_with_MULTI_ITEM(self):
        self.d.appendleft(self.item)
        self.d.appendleft(self.another_item)

        self.assertEqual(
            self.d.block_popleft(1),
            self.another_item
        )

        self.assertEqual(
            len(self.d),
            1
        )

    def test_block_popleft_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d.block_popleft()


    # __getitem__

    def test__getitem__use_INDEX(self):
        self.d.append(self.item)
        assert self.d[0] == self.item

    def test__getitem__RAISE_when_OUT_OF_INDEX(self):
        with self.assertRaises(IndexError):
            self.d[10086]

    def test__getitem__use_SLICE(self):
        for i in range(5):
            self.d.append(self.item)
        assert self.d[:5] == [self.item] * 5

    def test__getitem__RETURN_EMPTY_LIST_when_OUT_OF_RANGE(self):
        assert self.d[123:10086] == [] 
    
    def test__getitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d[0]


    # __delitem__
    
    # wrong type

    def test__delitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            del self.d[1]

    # del d[i]
    
    def test__delitem__by_INDEX_RAISE_when_OUT_OF_INDEX(self):
        with self.assertRaises(IndexError):
            del self.d[10086]

    def test__delitem__by_INDEX_with_SINGLE_ITEM(self):
        self.d.append(self.item)

        del self.d[0]
        self.assertEqual(
            list(self.d),
            []
        )

    def test__delitem__by_INDEX_with_MULTI_ITEM(self):
        self.d.extend(self.multi_item)

        del self.d[0]
        self.assertEqual(
            list(self.d),
            self.multi_item[1:]
        )

    # del d[:]

    def test__delitem__DELETE_ALL_ITEM_when_EMPTY(self):
        del self.d[:]
        assert list(self.d) == []

    def test__delitem__DELETE_ALL_ITEM_with_SINGLE_ITEM(self):
        self.d.append(self.item)

        del self.d[:]
        assert list(self.d) == []

    def test__delitem__DELETE_ALL_ITEM_with_MULTI_ITEM(self):
        self.d.append(self.multi_item)

        del self.d[:]
        assert list(self.d) == []

    # del d[i:]

    def test__delitem__given_LEFT_RANGE(self):
        self.d.extend(self.multi_item)

        del self.d[1:]

        self.assertEqual(
            list(self.d), 
            self.multi_item[:1]
        )

    # del d[:j]

    def test__delitem__given_RIGHT_RANGE(self):
        self.d.extend(self.multi_item)

        del self.d[:1]

        self.assertEqual(
            list(self.d),
            self.multi_item[1:]
        )

    # del d[i:j]

    def test__delitem__by_SLICE_INDEX_with_MULTI_ITEM(self):
        self.d.extend(self.multi_item)

        del self.d[0:3]
        self.assertEqual(
            list(self.d),
            []
        )


    # __setitem__

    # d[i]

    def test__setitem__by_SINGLE_INDEX(self):
        self.d.append(self.item)

        self.d[0] = self.another_item
        self.assertEqual(
            list(self.d),
            [self.another_item]
        )

    # d[i:j]

    def test__setitem__by_SLICE(self):
        self.d.extend(self.multi_item)

        self.d[1:3] = []
        self.assertEqual(
            list(self.d),
            self.multi_item[:1]
        )

    # wrong type

    def test__setitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d[0] = self.item

########NEW FILE########
__FILENAME__ = test_dict
#! /usr/bin/env python2.7
# coding: utf-8

import redis
import unittest

from ooredis.key.dict import Dict
from ooredis.client import connect
from ooredis.key.helper import format_key
from ooredis.type_case import JsonTypeCase

class TestDict(unittest.TestCase):
    
    def setUp(self):
        connect()

        self.redispy = redis.Redis()
        self.redispy.flushdb()

        self.name = 'dict'
        self.key = 'key'
        self.value = [1, 2, 3]

        self.d = Dict(self.name, type_case=JsonTypeCase)

    def tearDown(self): 
        self.redispy.flushdb()

    def set_wrong_type(self, key):
        self.redispy.set(key.name, 'string')


    # __repr__

    def test__repr__(self):
        self.assertEqual(
            repr(self.d),
            format_key(self.d, self.name, dict(self.d))
        )

    
    # __contains__

    def test__contains__return_True(self):
        self.d[self.key] = self.value

        self.assertTrue(
            self.key in self.d
        )

    def test__contains__return_False(self):
        self.assertFalse(
            self.key in self.d
        )


    # __setitem__

    def test__setitem__when_KEY_NOT_TAKEN(self):
        self.d[self.key] = self.value
        
        self.assertEqual(
            self.d[self.key],
            self.value
        )

        self.assertEqual(
            dict(self.d),
            {self.key: self.value}
        )

    def test__setitem__OVERWRITE_EXISTS_KEY(self):
        self.old_value = 'foo'

        self.d[self.key] = self.value

        self.assertEqual(
            self.d[self.key],
            self.value
        )

        self.assertEqual(
            dict(self.d),
            {self.key : self.value}
        )

    def test__setitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d[self.key] = self.value


    # __getitem__

    def test__getitem__with_EXISTS_KEY(self):
        self.d[self.key]= self.value

        self.assertEqual(
            self.d[self.key],
            self.value
        )

    def test__getitem__RAISE_when_KEY_NOT_EXISTS(self):
        with self.assertRaises(KeyError):
            self.d[self.key]

    def test__getitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            self.d[self.key]


    # __delitem__

    def test__delitem__when_KEY_EXISTS(self):
        self.d[self.key] = self.value
        
        del self.d[self.key]

        self.assertTrue(
            self.key not in self.d
        )

        self.assertEqual(
            dict(self.d),
            {}
        )

    def test__delitem__RAISE_when_KEY_NOT_EXISTS(self):
        with self.assertRaises(KeyError):
            del self.d['not_exists_key']

    def test__delitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            del self.d['wrong_type_cant_be_delete']


    # __iter__

    def test__ite__with_EMPTY_DICT(self):
        self.assertEqual(
            list(self.d),
            []
        )

    def test__ite__with_NOT_EMPTY_DICT(self):
        self.d[self.key] = self.value

        self.assertEqual(
            list(self.d),
            [self.key]
        )

    def test__iter__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            list(self.d)


    # __len__

    def test__len__with_EMPTY_DICT(self):
        self.assertEqual(
            len(self.d),
            0
        )

    def test__len__with_NOT_EMPTY_DICT(self):
        self.d[self.key] = self.value

        self.assertEqual(
            len(self.d),
            1
        )

    def test__len__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.d)
            len(self.d)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_helper
# coding:utf-8

import redis
import unittest

from ooredis.key.base_key import BaseKey
from ooredis.key.helper import format_key, wrap_exception

class TestHelper(unittest.TestCase):

    def setUp(self):
        self.name = "name"
        self.value = "value"
        self.key = BaseKey(self.name)


    # format_key

    def test_format_key(self):
        output = format_key(self.key, self.name, self.value)
        self.assertEqual( output,"Basekey Key 'name': value")

    
    # wrap_exception

    def test_wrap_exception_RAISE_TYPE_ERROR_when_ERROR_OCCUR(self):

        @wrap_exception
        def r():
            raise redis.exceptions.ResponseError

        with self.assertRaises(TypeError):
            r() 

    def test_wrap_exception_NOT_RAISE_when_NO_ERROR_OCCUR(self):

        @wrap_exception
        def f():
            return 10

        self.assertEqual(
            f(),
            10
        )


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_set
#! /usr/bin/env python2.7
# coding: utf-8

import redis
import unittest

from ooredis.client import connect

from ooredis.key.set import Set
from ooredis.key.helper import format_key
from ooredis.type_case import FloatTypeCase
    
class TestSet(unittest.TestCase):

    def setUp(self):
        connect()

        self.redispy = redis.Redis()
        self.redispy.flushdb()

        self.s = Set('set', type_case=FloatTypeCase)
        self.another = Set('another', type_case=FloatTypeCase)
        self.third = Set('third', type_case=FloatTypeCase)

        self.element = 3.14

    def tearDown(self):
        self.redispy.flushdb()

    def set_wrong_type(self, key_object):
        self.redispy.set(key_object.name, 'string')


    # __repr__

    def test__repr__(self):
        self.assertEqual(
            repr(self.s),
            format_key(self.s, self.s.name, set(self.s))
        )


    # __len__

    def test__len__with_EMPTY_SET(self):
        self.assertEqual(
            len(self.s),
            0
        )

    def test__len__with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            len(self.s),
            1
        )

    def test__len__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            len(self.s)


    # __iter__

    def test__iter__with_EMPTY_SET(self):
        self.assertEqual(
            list(iter(self.s)),
            []
        )

    def test__iter__with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            list(iter(self.s)),
            [self.element]
        )

    def test__iter__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            list(iter(self.s))


    # __contains__

    def test__contains__FALSE(self):
        self.assertTrue(
            self.element not in self.s
        )

    def test__contains__TRUE(self):
        self.s.add(self.element)

        self.assertTrue(
            self.element in self.s
        )

    def test__contains__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.element in self.s


    # add

    def test_add_with_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            set(self.s),
            {self.element}
        )

    def test_add_when_ELEMENT_ALREADY_SET_MEMBER(self):
        self.s.add(self.element)

        self.s.add(self.element)
        self.assertEqual(
            set(self.s),
            {self.element}
        )

    def test_add_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s.add(self.element)


    # remove

    def test_remove_when_ELEMENT_EXISTS(self):
        self.s.add(self.element)

        self.s.remove(self.element)

        self.assertEqual(
            set(self.s),
            set()
        )

    def test_remove_RAISE_when_ELEMENT_NOT_EXISTS(self):
        with self.assertRaises(KeyError):
            self.s.remove(self.element)

    def test_remove_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s.remove(self.element)


    # pop

    def test_pop_RAISE_when_SET_EMPTY(self):
        with self.assertRaises(KeyError):
            self.s.pop()

    def test_pop_with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s.pop(),
            self.element
        )

        self.assertEqual(
            len(self.s),
            0
        )

    def test_pop_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s.pop()


    # random

    def test_random_with_EMPTY_SET(self):
        self.assertIsNone(
            self.s.random()
        )

    def test_random_with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s.random(),
            self.element
        )

        # make sure Set.random not delete element in set
        self.assertEqual(
            len(self.s),
            1
        )

        self.assertEqual(
            set(self.s),
            set([self.element])
        )

    def test_random_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s.random()


    # move

    def test_move_ELEMENT_NOT_EXISTS_IN_DESTINATION_SET(self):
        self.s.add(self.element)

        self.s.move(self.another, self.element)

        # remove self.element from self.s
        self.assertEqual(
            len(self.s),
            0
        )

        # move ok
        self.assertEqual(
            len(self.another),
            1
        )

        self.assertEqual(
            set(self.another),
            set([self.element])
        )

    def test_move_ELEMENT_EXISTS_IN_DESTINATION_SET(self):
        self.s.add(self.element)
        self.another.add(self.element)

        self.s.move(self.another, self.element)

        # remove self.element from self.s
        self.assertEqual(
            len(self.s),
            0
        )

        # self.another not change(cause self.element alread exists)
        self.assertEqual(
            len(self.another),
            1
        )

        self.assertEqual(
            set(self.another),
            set([self.element])
        )

    def test_move_RAISE_KEY_ERROR_when_ELEMENT_NOT_SET_MEMBER(self):
        with self.assertRaises(KeyError):
            self.s.move(self.another, 10086)

    def test_move_RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s.move(self.another, self.element)

    def test_move_RAISE_when_DESTINATION_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.s.add(self.element)

            self.set_wrong_type(self.another)
            self.s.move(self.another, self.element)


    # isdisjoint

    def test_isdisjoint_True(self):
        self.s.add(self.element)

        self.assertTrue(
            self.s.isdisjoint(self.another)
        )

    def test_isdisjoint_False(self):
        self.s.add(self.element)
        self.another.add(self.element)

        self.assertFalse(
            self.s.isdisjoint(self.another)
        )

    def test_idisjoint_with_PYTHON_SET(self):
        self.s.add(self.element)

        self.assertTrue(
            self.s.isdisjoint(set())
        )

    def test_isdisjoint_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s.isdisjoint(set())

    def test_isdisjoint_RAISE_when_OTHER_SET_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s.isdisjoint(self.another)


    # __le__

    def test__le__True(self):
        self.assertTrue(
            self.s <= self.another
        )

    def test__le__False(self):
        self.s.add(self.element)

        self.assertFalse(
            self.s <= self.another
        )

    def test__le__with_PYTHON_SET(self):
        self.assertTrue(
            self.s <= set()
        )

    def test__le__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s <= self.another

    def test__le__RAISE_when_OTHER_SET_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s <= self.another


    # issubset

    def test_issubset(self):
        self.assertTrue(
            self.s.issubset(self.another)
        )


    # __lt__

    def test__lt__True(self):
        self.another.add(self.element)

        self.assertTrue(
            self.s < self.another
        )

    def test__lt__False(self):
        self.s.add(self.element)

        self.assertFalse(
            self.s < self.another
        )

    def test__lt__with_PYTHON_SET(self):
        self.assertFalse(
            self.s < set()
        )

    def test__lt__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s < self.another

    def test__lt__RAISE_when_OTHER_SET_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s < self.another


    # __ge__

    def test__ge__TRUE(self):
        self.assertTrue(
            self.s >= self.another
        )

    def test__ge__FALSE(self):
        self.another.add(self.element)

        self.assertFalse(
            self.s >= self.another
        )

    def test__ge__with_PYTHON_SET(self):
        self.assertTrue(
            self.s >= set()
        )

    def test__ge__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s >= self.another

    def test__ge__RAISE_when_OTHER_SET_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s >= self.another


    # issuperset

    def test_issuperset(self):   
        self.assertTrue(
            self.s.issuperset(self.another)
        )


    # __gt__

    def test__gt__True(self):
        self.s.add(self.element)

        self.assertTrue(
            self.s > self.another
        )

    def test__gt__FALSE(self):
        self.another.add(self.element)

        self.assertFalse(
            self.s > self.another
        )

    def test__gt__with_PYTHON_SET(self):
        self.s.add(self.element)

        self.assertTrue(
            self.s > set()
        )
    
    def test__gt__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s > self.another

    def test__gt__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s > self.another


    # __or__

    def test__or__(self):
        self.s.add(self.element)
        
        self.assertEqual(
            self.s | self.another,
            {self.element}
        )

    def test__or__with_MULTI_OPERAND(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s | self.another | self.third,
            {self.element}
        )

    def test__or__with_PYTHON_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s | set(),
            {self.element}
        )

    def test__or__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s | self.another

    def test__or__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s | self.another


    # __ror__

    def test__ror__(self):
        self.s.add(self.element)

        self.assertEqual(
            self.another | self.s,
            {self.element}
        )


    # __ior__

    def test__ior__with_EMPTY_SET(self):
        self.s |= self.another

        self.assertEqual(
            set(self.s),
            set()
        )

    def test__ior__with_NOT_EMPTY_SET(self):
        self.another.add(self.element)

        self.s |= self.another

        self.assertEqual(
            set(self.s),
            set(self.another)
        )

    def test_ior_with_PYTHON_SET(self):
        self.s |= {1, 2, 3}

        self.assertEqual(
            set(self.s) ,
            {1, 2, 3}
        )

    def test__ior__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s |= self.another

    def test__ior__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s |= self.another


    # __and__

    def test__and__(self):
        self.s.add(self.element)
        self.another.add(self.element)

        self.assertEqual(
            self.s & self.another,
            {self.element}
        )

    def test__and__with_MULTI_OPERAND(self):
        self.s.add(self.element)
        self.another.add(self.element)
        self.third.add(self.element)

        self.assertEqual(
            self.s & self.another & self.third,
            {self.element}
        )
            
    def test__and__with_PYTHON_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s & {self.element},
            {self.element}
        )

    def test__and__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s & self.another

    def test__and__RAISE_when_OTHER_SET_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s & self.another


    # __rand__

    def test__rand__(self):
        self.s.add(self.element)

        self.assertEqual(
            {self.element} & self.s,
            {self.element}
        )


    # __iand__

    def test__iand__with_EMPTY_SET(self):
        self.s &= self.another

        self.assertEqual(
            set(self.s),
            set()
        )

    def test__iand__with_NOT_EMPTY_SET(self):   
        self.s.add(self.element)

        self.another.add(self.element)
        
        self.s &= self.another

        self.assertEqual(
            set(self.s),
            {self.element}
        )

    def test__iand__with_PYTHON_SET(self):
        self.s.add(1)
        self.s.add(2)
        self.s.add(3)

        self.s &= {1, 2}

        self.assertEqual(
            set(self.s) ,
            {1, 2}
        )

    def test__iand__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s &= self.another
   
    def test__iand__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s &= self.another


    # __sub__

    def test__sub__with_EMPTY_SET(self):
        self.assertEqual(
            self.s - self.another,
            set()
        )

    def test__sub__with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s - self.another,
            {self.element}
        )

    def test__sub__with_MULTI_OPERAND(self):
        self.s.add(self.element)
        self.another.add(self.element)
        self.third.add(self.element)

        self.assertEqual(
            self.s - self.another - self.third,
            set()
        )

    def test__sub__with_PYTHON_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s - set(),
            {self.element}
        )

    def test__sub__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s - self.another

    def test__sub__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s - self.another


    # __rsub__

    def test__rsub__(self):
        self.s.add(self.element)

        self.assertEqual(
            set() - self.s,
            set()
        )


    #__isub__

    def test__isub__with_EMPTY_SET(self):
        self.s -= self.another

        self.assertEqual(
            set(self.s),
            set()
        )

    def test__isub__with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.s -= self.another

        self.assertEqual(
            set(self.s),
            {self.element}
        )

    def test__isub__with_PYTHON_SET(self):
        self.s.add(1)
        self.s.add(2)
        self.s.add(3)

        self.s -= {1, 2}

        self.assertEqual(
            set(self.s) ,
            {3}
        )

    def test__isub__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s -= self.another

    def test__isub__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s -= self.another


    # __xor__

    def test__xor__with_EMPTY_SET(self):
        self.assertEqual(
            self.s ^ self.another,
            set()
        )

    def test__xor__with_NOT_EMPTY_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s ^ self.another,
            {self.element}
        )

    def test__xor__with_MULTI_OPERAND(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s ^ self.another ^ self.third,
            {self.element}
        )

    def test__xor__with_PYTHON_SET(self):
        self.s.add(self.element)

        self.assertEqual(
            self.s ^ set(),
            {self.element}
        )

    def test__xor__RAISE_when_SELF_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s ^ self.another

    def test__xor__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s ^ self.another


    # __rxor__

    def test__rxor__(self):
        self.assertEqual(
            {self.element} ^ self.s,
            {self.element}
        )


    # __ixor__

    def test__ixor__with_EMPTY_SET(self):
        self.s ^= self.another

        self.assertEqual(
            set(self.s),
            set()
        )

    def test__ixor__with_NOT_EMPTY_SET(self):
        self.s.add(1)
        self.s.add(2)
        self.s.add(3)

        self.another.add(1)
        self.another.add(4)
        self.another.add(5)

        self.s ^= self.another

        self.assertEqual(
            set(self.s),
            {2, 3, 4, 5}
        )

    def test__ixor__with_PYTHON_SET(self):
        self.s.add(1)
        self.s.add(2)
        self.s.add(3)

        self.s ^= {1, 4, 5}

        self.assertEqual(
            set(self.s),
            {2, 3, 4, 5}
        )

    def test__ixor__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.s)
            self.s ^= {1, 2, 3}

    def test__ixor__RAISE_when_OTHER_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type(self.another)
            self.s ^= self.another


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_set_and_get_op_mixin
# coding: utf-8

import redis
import unittest

from ooredis.client import connect
from ooredis.type_case import FloatTypeCase

from ooredis.key.base_key import BaseKey
from ooredis.key.common_key_property_mixin import CommonKeyPropertyMixin
from ooredis.key.set_and_get_op_mixin import SetAndGetOpMixin

class C(BaseKey, CommonKeyPropertyMixin, SetAndGetOpMixin):
    pass

class TestSetAndGetOpMixin(unittest.TestCase):

    def setUp(self):
        connect()

        self.redispy = redis.Redis()
        self.redispy.flushdb()
  
        self.name = 'pi'
        self.value = 3.14

        # 使用 FloatTypeCase 是为了测试 TypeCase
        self.key = C(self.name, type_case=FloatTypeCase)

    def tearDown(self):
        self.redispy.flushdb()

    def set_wrong_type(self):
        self.redispy.lpush(self.name, "create a list value")


    # set

    def test_set(self): 
        self.key.set(self.value)

        self.assertEqual(
            self.key.get(),
            self.value
        )

    def test_set_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.key.set(self.value)

    
    # setnx

    def test_setnx_with_NO_EXISTS_KEY(self):
        self.key.setnx(self.value)

        self.assertEqual(
            self.key.get(),
            self.value
        )

    def test_setnx_WILL_NOT_OVERWRITE_EXISTS_VALUE(self):
        self.key.setnx(self.value)

        self.key.setnx(10086)   # this value will not set

        self.assertEqual(
            self.key.get(),
            self.value
        )

    def test_setnx_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.key.setnx(self.value)

    
    # setex

    def test_setex_with_NO_EXISTS_KEY(self):
        self.key.setex(self.value, 10086)

        self.assertIsNotNone(
            self.key.ttl
        )

        self.assertEqual(
            self.key.get(),
            self.value
        )

    def test_setex_WILL_UPDATE_EXPIRE_TIME_when_KEY_EXISTS(self):
        self.key.setex(self.value, 10086)

        self.key.setex(self.value, 100)     # overwrite 10086 (origin ttl)

        self.assertTrue(
            self.key.ttl <= 100
        )

        self.assertEqual(
            self.key.get(),
            self.value
        )

    def test_setex_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.key.setex(self.value, 10086)


    # get

    def test_get_RETURN_NONE_when_KEY_NOT_EXISTS(self):
        self.assertIsNone(
            self.key.get()
        )

    def test_get_with_EXISTS_KEY(self):
        self.key.set(self.value)

        self.assertEqual(
            self.key.get(), 
            self.value
        )

    def test_get_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.key.get()


    # getset

    def test_getset_RETURN_NONE_when_KEY_NOT_EXISTS(self):
        self.assertIsNone(
            self.key.getset(self.value)
        )

        self.assertEqual(
            self.key.get(),
            self.value
        )

    def test_getset_RETURN_OLD_VALUE_when_KEY_EXISTS(self):
        self.new_value = 10086
        self.old_value = self.value

        self.key.set(self.old_value)

        self.assertEqual(
            self.key.getset(self.new_value),
            self.old_value
        )

        self.assertEqual(
            self.key.get(), 
            self.new_value
        )

    def test_getset_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.key.getset(self.value)

########NEW FILE########
__FILENAME__ = test_sorted_set
#! /usr/bin/env python2.7
# coding: utf-8

import redis
import unittest

from ooredis.client import connect
from ooredis.key.helper import format_key
from ooredis.type_case import JsonTypeCase
from ooredis.key.sorted_set import SortedSet
    
class TestSortedSet(unittest.TestCase):

    def setUp(self):
        connect()

        self.redispy = redis.Redis()
        self.redispy.flushdb()

        self.s = SortedSet('sorted_set', type_case=JsonTypeCase)
        self.another = SortedSet('another', type_case=JsonTypeCase)

        self.element = {'k':'v'}
        self.score = 10086
        
    def tearDown(self):
        self.redispy.flushdb()

    def set_wrong_type(self):
        self.redispy.set(self.s.name, 'string')


    # __repr__

    def test_repr(self):
        self.assertEqual(
            repr(self.s),
            format_key(self.s, self.s.name, list(self.s))
        )


    # __len__

    def test_len_RETURN_0_when_SET_EMPTY(self):
        self.assertEqual(len(self.s), 0)

    def test_len_with_NOT_EMPTY_SET(self):
        self.s[self.element] = self.score

        self.assertEqual(
            len(self.s),
            1
        )

    def test_len_RAISE_when_WONRG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            len(self.s)


    # __contains__

    def test_in_RETURN_FALSE(self):
        self.assertFalse(
            self.element in self.s
        )

    def test_in_RETURN_TRUE(self):
        self.s[self.element] = self.score

        self.assertTrue(
            self.element in self.s
        )

    def test_in_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.element in self.s


    # __setitem__

    def test_setitem_when_MEMBER_NOT_EXISTS(self):
        self.s[self.element] = self.score

        self.assertEqual(
            len(self.s),
            1
        )

        self.assertEqual(
            self.s[0]['member'],
            self.element
        )
        self.assertEqual(
            self.s[0]['score'], 
            self.score
        )

    def test_setitem_UPDATE_SCORE_when_MEMBER_EXISTS(self):
        self.s[self.element] = 10086

        self.s[self.element] = self.score

        self.assertEqual(
            self.s[0]['member'],
            self.element
        )
        self.assertEqual(
            self.s[0]['score'],
            self.score
        )

    def test_setitem_raise_when_wrong_type(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s[self.element] = self.score


    # __getitem__

    def test_getitem_with_INDEX(self):
        self.s[self.element] = self.score

        self.assertTrue(
            isinstance(self.s[0], dict)
        )

        self.assertEqual(
            self.s[0]['member'],
            self.element
        )
        self.assertEqual(
            self.s[0]['score'],
            self.score
        )

    def test_getitem_RAISE_when_INDEX_OUT_OF_RANGE(self):
        with self.assertRaises(IndexError):
            self.s[10086]

    def test_getitem_with_RANGE(self):
        self.s['one'] = 1
        self.s['two'] = 2
        self.s['three']= 3

        self.assertEqual(self.s[1:],    
                         [{'member': 'two', 'score': 2},
                          {'member': 'three', 'score': 3},])

        self.assertEqual(self.s[:2],
                        [{'member': 'one', 'score': 1},
                         {'member': 'two', 'score': 2}])

        self.assertEqual(self.s[:],
                        [{'member': 'one', 'score': 1},
                         {'member': 'two', 'score': 2},
                         {'member': 'three', 'score': 3},])

        self.assertEqual(self.s[1:2],
                         [{'member': 'two', 'score': 2},])

        self.assertEqual(self.s[10086:],
                         [])

    def test_getitem_with_wrong_type(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s[:]


    # __delitem__

    def test__delitem__(self):
        self.s[self.element] = self.score

        del self.s[0]

        self.assertEqual(
            len(self.s),
            0
        )

    def test__delitem__with_EMPTY_SET(self):
        del self.s[:]
        self.assertEqual(
            len(self.s),
            0
        )

    def test__delitem__with_DEFAULT_START_OR_DEFAULT_END_RANGE(self):
        self.s['one'] = 1
        self.s['two'] = 2
        self.s['three'] = 3

        # del 'one'
        del self.s[:1]

        self.assertEqual(
            len(self.s),
            2
        )
        self.assertEqual(
            self.s[:],
            [
                {'member': 'two', 'score': 2},
                {'member': 'three', 'score': 3},
            ]
        )

        # del 'three'
        del self.s[1:]

        self.assertEqual(
            len(self.s),
            1
        )
        self.assertEqual(
            self.s[:],
            [
                {'member': 'two', 'score': 2},
            ]
        )

        # del all
        del self.s[:]
        self.assertEqual(
            len(self.s), 
            0
        )

    def test__delitem__with_REVERSE_RANGE(self):
        self.s['one'] = 1
        self.s['two'] = 2
        self.s['three'] = 3

        # del 'three'
        del self.s[-1]

        self.assertEqual(
            len(self.s), 
            2
        )
        self.assertEqual(
            self.s[:],
            [
                {'member': 'one', 'score': 1},
                {'member': 'two', 'score': 2}
            ]
        )

        # del 'two'
        del self.s[-1:]

        self.assertEqual(
            len(self.s), 
            1
        )
        self.assertEqual(
            self.s[:],
            [
                {'member': 'one', 'score': 1}
            ]
        )

        # del 'one'
        del self.s[-1]
        self.assertEqual(
            len(self.s), 
            0
        )

    def test__delitem__in_RANGE_with_GIVEN_START_AND_END(self):
        self.s['one'] = 1

        del self.s[0:1]

        self.assertEqual(
            len(self.s), 
            0
        )

    def test__delitem__RAISE_when_INDEX_OUT_OF_RANGE(self):
        with self.assertRaises(IndexError):
            del self.s[10086]
    
    def test__delitem__RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            del self.s[:]


    # remove

    def test_remove_EXISTS_MEMBER(self):
        self.s[self.element] = self.score

        self.s.remove(
            self.element
        )
        self.assertEqual(
            len(self.s),
            0
        )

    def test_remove_RETURN_NONE_when_MEMBER_NOT_EXISTS(self):
        self.assertIsNone(
            self.s.remove(self.element)
        )

    def test_remove_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s.remove(self.element)


    # rank

    def test_rank(self):
        self.s[self.element] = self.score

        self.assertEqual(
            self.s.rank(self.element), 
            0
        )

        # 插入一个 score 值比 self.element 更小的元素
        self.s['new'] = self.score-1
        # self.element被重排了
        self.assertEqual(
            self.s.rank(self.element), 
            1
        )
   
    def test_rank_RETURN_NONE_when_MEMBER_NOT_EXISTS(self):
        self.assertIsNone(
            self.s.rank(self.element)
        )

    def test_rank_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s.rank(self.element)


    # reverse_rank

    def test_reverse_rank(self):
        self.s[self.element] = self.score

        self.assertEqual(
            self.s.reverse_rank(self.element),
            0
        )

        # 插入一个score值比self.element更大的元素
        self.s['new'] = self.score+1
        # self.element被重排了
        self.assertEqual(
            self.s.reverse_rank(self.element),
            1
        )

    def test_reverse_rank_RETURN_NONE_when_MEMBER_NOT_EXISTS(self):
        self.assertIsNone(
            self.s.reverse_rank(self.element)
        )

    def test_rank_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s.reverse_rank(self.element)


    # score

    def test_score(self):
        self.s[self.element] = self.score

        self.assertEqual(
            self.s.score(self.element), 
            self.score
        )

    def test_score_RETURN_NONE_when_MEMBER_NOT_EXISTS(self):
        self.assertIsNone(
            self.s.score(self.element)
        )

    def test_score_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s.score(self.element)


    # incr

    def test_incr_RETURN_FALOT_TYPE(self):
        self.assertTrue(
            isinstance(self.s.incr(self.element), float)
        )

    def test_incr_with_EXISTS_MEMBER(self):
        self.s[self.element] = self.score

        self.increment = 100

        self.assertEqual(
            self.s.incr(self.element, self.increment),
            self.score + self.increment
        )

    def test_incr_with_EXISTS_MEMBER_using_DEFAULT_INCREMENT(self):
        self.s[self.element] = self.score

        self.default_increment = 1

        self.assertEqual(
            self.s.incr(self.element),
            self.score + self.default_increment
        )

    def test_incr_with_NOT_EXISTS_MEMBER(self):
        self.assertEqual(
            self.s.incr(self.element), 
            1
        )

        self.assertEqual(
            len(self.s), 
            1
        )
        self.assertEqual(
            self.s.score(self.element),
            1
        )

    def test_incr_RAISE_when_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s.incr(self.element)


    # decr

    def test_decr_RETURN_FALOT_TYPE(self):
        self.assertTrue(
            isinstance(self.s.decr(self.element), float)
        )

    def test_decr_with_EXISTS_MEMBER(self):
        self.s[self.element] = self.score

        self.decrement = 100

        self.assertEqual(
            self.s.decr(self.element, self.decrement),
            self.score - self.decrement
        )

    def test_decr_with_EXISTS_MEMBER_using_DEFAULT_DECREMENT(self):
        self.s[self.element] = self.score

        self.default_decrement = 1

        self.assertEqual(
            self.s.decr(self.element),
            self.score-self.default_decrement
        )

    def test_decr_with_NOT_EXISTS_MEMBER(self):
        self.assertEqual(
            self.s.decr(self.element),
            -1
        )

        self.assertEqual(
            len(self.s),
            1
        )
        self.assertEqual(
            self.s.score(self.element),
            -1
        )
    
    def test_decr_raise_when_wrong_type(self):
        with self.assertRaises(TypeError):
            self.set_wrong_type()
            self.s.decr(self.element)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_string
#! /usr/bin/env python2.7
# coding: utf-8

import redis
import unittest

from ooredis import String
from ooredis.client import connect
from ooredis.key.helper import format_key

class TestString(unittest.TestCase):

    def setUp(self):
        connect()

        self.redispy = redis.Redis()
        self.redispy.flushdb()
  
        self.name = 'pi'
        self.value = 3.14

        self.key = String(self.name)

    def tearDown(self):
        self.redispy.flushdb()


    # __repr__

    def test_repr(self):
        self.key.set(self.value)

        self.assertEqual(
            repr(self.key),
            format_key(self.key, self.name, self.value)
        )

########NEW FILE########
__FILENAME__ = test_client
#! /usr/bin/env python2.7
# coding:utf-8

import unittest

from ooredis.client import connect, get_client
import redis

class TestClient(unittest.TestCase):
    
    def setUp(self):
        self.client = connect()

    def test_get(self):
        self.assertTrue(isinstance(get_client(), redis.Redis))

    def test_get_get(self):
        self.assertEqual(get_client(), get_client())

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_remote_server
#! /usr/bin/env python2.7
# coding:utf-8

import unittest

from ooredis import connect, get_client, String
import redis

class TestRemoteServer(unittest.TestCase):
    
    def setUp(self):
        self.host = '127.0.0.1'

        # ooredis
        connect(host=self.host)
       
        # redis-py
        self.r = redis.Redis(host=self.host)
        self.r.flushdb()

    def test_set_and_get(self):
        self.s = String('key')
        self.s.set('value')

        self.assertEqual(self.s.get(), 'value')

        self.assertTrue(self.r.exists('key'))
        self.assertEqual(self.r.get('key'), self.s.get())

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_float_type_case
# coding: utf-8

from unittest import TestCase
from ooredis.type_case import FloatTypeCase

class TestFloat(TestCase):

    def setUp(self):
        self.f = 3.14
        self.i = 10086

        self.wrong_type_input = set()

    # encode

    def test_encode_ACCEPT_FLOAT(self):
        assert FloatTypeCase.encode(self.f) == self.f

    def test_encode_ACCEPT_INT(self):
        assert FloatTypeCase.encode(self.i) == float(self.i)

    def test_encode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            FloatTypeCase.encode(self.wrong_type_input)

    # decode

    def test_decode_RETURN_NONE(self):
        assert FloatTypeCase.decode(None) == None

    def test_decode_RETURN_FLOAT(self):
        assert FloatTypeCase.decode(str(self.f)) == self.f

    def test_decode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            FloatTypeCase.decode(self.wrong_type_input)

########NEW FILE########
__FILENAME__ = test_generic_type_case
# coding: utf-8

from unittest import TestCase
from ooredis.type_case import GenericTypeCase

class TestGeneric(TestCase):

    def setUp(self):
        self.s = 'str'
        self.u = u'unicode'
        self.i = 10086
        self.l = 100861008610086
        self.f = 3.14

        self.wrong_type_input = set()

    # encode

    def test_encode_ACCEPT_STRING(self):
        assert GenericTypeCase.encode(self.s) == self.s
    
    def test_encode_ACCEPT_UNICODE(self):
        assert GenericTypeCase.encode(self.u) == self.u

    def test_encode_ACCEPT_INT(self):
        assert GenericTypeCase.encode(self.i) == self.i

    def test_encode_ACCEPT_LONG(self):
        assert GenericTypeCase.encode(self.l) == self.l

    def test_encode_ACCEPT_FLOAT(self):
        assert GenericTypeCase.encode(self.f) == self.f

    def test_encode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            GenericTypeCase.encode(self.wrong_type_input)

    # decode

    def test_decode_RETURN_NONE(self):
        assert GenericTypeCase.decode(None) is None

    def test_decode_RETURN_STRING(self):
        assert GenericTypeCase.decode(str(self.s)) == self.s

    def test_decode_RETURN_UNICODE(self):
        assert GenericTypeCase.decode(unicode(self.u)) == self.u

    def test_decode_RETURN_INT(self):
        assert GenericTypeCase.decode(str(self.i)) == self.i

    def test_decode_RETURN_LONG(self):
        assert GenericTypeCase.decode(str(self.l)) == self.l

    def test_decode_RETURN_FLOAT(self):
        assert GenericTypeCase.decode(str(self.f)) == self.f

    def test_decode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(AssertionError):
            GenericTypeCase.decode(self.l)

########NEW FILE########
__FILENAME__ = test_int_type_case
# coding: utf-8

from unittest import TestCase
from ooredis.type_case import IntTypeCase

class TestInt(TestCase):

    def setUp(self):
        self.i = 10086
        self.l = 100861008610086

        self.wrong_type_input = set()

    # encode

    def test_encode_ACCEPT_INT(self):
        assert IntTypeCase.encode(self.i) == self.i

    def test_encode_ACCEPT_LONG(self):
        assert IntTypeCase.encode(self.l) == self.l

    def test_encode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            IntTypeCase.encode(self.wrong_type_input)

    # decode

    def test_decode_RETURN_NONE(self):
        assert IntTypeCase.decode(None) == None

    def test_decode_RETURN_INT(self):    
        assert IntTypeCase.decode(str(self.i)) == self.i

    def test_decode_RETURN_LONG(self):
        assert IntTypeCase.decode(str(self.l)) == self.l

    def test_decode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            IntTypeCase.decode(self.wrong_type_input)

########NEW FILE########
__FILENAME__ = test_json_type_case
# coding: utf-8

import json

from unittest import TestCase
from ooredis.type_case import JsonTypeCase

class UnJsonableObj:
    pass

class TestJson(TestCase):

    def setUp(self):
        self.s = 'str'

        self.wrong_type_input = UnJsonableObj()

    # encode

    def test_encode_with_JSONABLE(self):
        assert JsonTypeCase.encode(self.s) == json.dumps(self.s)

    def test_encode_RAISE_when_INPUT_UN_JSONABLE(self):
        with self.assertRaises(TypeError):
            JsonTypeCase.encode(self.wrong_type_input)

    # decode

    def test_decode_RETURN_NONE(self):
        assert JsonTypeCase.decode(None) == None

    def test_decode_RETURN_JSONABLE(self):
        assert JsonTypeCase.decode(json.dumps(self.s)) == self.s

    def test_decode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            JsonTypeCase.decode(self.wrong_type_input)

########NEW FILE########
__FILENAME__ = test_serialize_type_case
# coding: utf-8

import pickle

from unittest import TestCase
from ooredis.type_case import SerializeTypeCase

class SerializeAbleClass:
    greet = 'hello moto'

class TestSerializeTypeCase(TestCase):

    def setUp(self):
        self.s = 'str'
        self.c = SerializeAbleClass()

    # encode

    def test_encode_with_STR(self):
        assert SerializeTypeCase.encode(self.s) == pickle.dumps(self.s)

    def test_encode_with_CLASS(self):
        assert SerializeTypeCase.encode(self.c) == pickle.dumps(self.c)

    # decode

    def test_decode_RETURN_NONE(self):
        assert SerializeTypeCase.decode(None) == None

    def test_decode_RETURN_STR(self):
        assert SerializeTypeCase.decode(SerializeTypeCase.encode(self.s)) == self.s

    def test_decode_RETURN_CLASS(self):
        assert isinstance(SerializeTypeCase.decode(SerializeTypeCase.encode(self.c)), SerializeAbleClass)

########NEW FILE########
__FILENAME__ = test_string_type_case
# coding: utf-8

from unittest import TestCase
from ooredis.type_case import StringTypeCase

class TestString(TestCase):

    def setUp(self):
        self.s = 'str'
        self.u = u'unicode'

        self.wrong_type_input = set()

    # encode

    def test_encode_ACCEPT_STR(self):
        assert StringTypeCase.encode(self.s) == self.s

    def test_encode_ACCEPT_UNICODE(self):
        assert StringTypeCase.encode(self.u) == self.u

    def test_encode_RAISE_when_INPUT_WRONG_TYPE(self):
        with self.assertRaises(TypeError):
            StringTypeCase.encode(self.wrong_type_input)

    # decode

    def test_decode_RETURN_NONE(self):
        assert StringTypeCase.decode(None) == None

    def test_decode_RETURN_STR(self):
        assert StringTypeCase.decode(self.s) == self.s

    def test_decode_RETURN_UNICODE(self):
        assert StringTypeCase.decode(self.u) == self.u

########NEW FILE########
