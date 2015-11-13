__FILENAME__ = proclaim


class Proclaim(object):

    def __init__(self, redis):
        self.redis = redis
        self.groups = { "all": [] }

    def activate_group(self, feature, group):
        if group in self.groups:
            self.redis.sadd(_group_key(feature), group)

    def deactivate_group(self, feature, group):
        self.redis.srem(_group_key(feature), group)

    def deactivate_all(self, feature):
        self.redis.delete(_group_key(feature))
        self.redis.delete(_user_key(feature))
        self.redis.delete(_percentage_key(feature))

    def activate_user(self, feature, user):
        self.redis.sadd(_user_key(feature), user.id)

    def deactivate_user(self, feature, user):
        self.redis.srem(_user_key(feature), user.id)

    def define_group(self, group, *users):
        self.groups[group] = []
        for user in users:
            self.groups[group].append(user.id)

    def is_active(self, feature, user):
        if self._user_in_active_group(feature, user):
            return True
        if self._user_active(feature, user):
            return True
        if self._user_within_active_percentage(feature, user):
            return True
        return False

    def activate_percentage(self, feature, percentage):
        self.redis.set(_percentage_key(feature), percentage)

    def deactivate_percentage(self, feature, percentage):
        self.redis.delete(_percentage_key(feature), percentage)

    def _user_in_active_group(self, feature, user):
        if self.redis.exists(_group_key(feature)):
            active_groups = self.redis.smembers(_group_key(feature))
            if active_groups:
                for grp in active_groups:
                    if user.id in self.groups[grp]:
                        return True
        return False

    def _user_active(self, feature, user):
        if self.redis.sismember(_user_key(feature), user.id):
            return True
        return False

    def _user_within_active_percentage(self, feature, user):
        if self.redis.exists(_percentage_key(feature)):
            percentage = self.redis.get(_percentage_key(feature))
            if int(user.id) % 10 < int(percentage) / 10:
                return True
        return False

def _key(name):
    return "feature:%s" % name

def _group_key(name):
    return "%s:groups" % (_key(name))

def _user_key(name):
    return "%s:users" % (_key(name))

def _percentage_key(name):
    return "%s:percentage" % (_key(name))


########NEW FILE########
__FILENAME__ = test_proclaim
import redis
import unittest

from proclaim import Proclaim

class User(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

jim = User(id=1, username='jim@test.com')
bob = User(id=23, username='bob@test.com')
joan = User(id=40, username='joan@test.com')

class TestProclaim(unittest.TestCase):

    def setUp(self):
        self.redis = redis.Redis(host='localhost', port=6379)
        self.proclaim = Proclaim(self.redis)
        self.proclaim.define_group("a", jim, joan)
        self.proclaim.define_group("b", jim, joan, bob)

    def test_groups(self):
        assert len(self.proclaim.groups["b"]) == 3
        assert jim.id in self.proclaim.groups["a"]

    def test_activate_group(self):
        self.proclaim.activate_group("f1", "b")
        assert self.proclaim.is_active("f1", jim)

    def test_deactivate_group(self):
        self.proclaim.deactivate_group("f1", "b")
        assert not self.proclaim.is_active("f1", jim)

    def test_activate_user(self):
        self.proclaim.activate_user("f2", joan)
        assert self.proclaim.is_active("f2", joan)

    def test_deactivate_user(self):
        self.proclaim.deactivate_user("f2", joan)
        assert not self.proclaim.is_active("f2", joan)

    def test_activate_percentage(self):
        self.proclaim.activate_percentage("f3", 25)
        assert self.proclaim.is_active("f3", jim)
        assert self.proclaim.is_active("f3", joan)
        assert not self.proclaim.is_active("f3", bob)

    def test_deactivate_percentage(self):
        self.proclaim.deactivate_percentage("f3", 25)
        assert not self.proclaim.is_active("f3", jim)

########NEW FILE########
