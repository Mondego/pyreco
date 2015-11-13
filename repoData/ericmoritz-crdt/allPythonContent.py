__FILENAME__ = base
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod, abstractproperty
from copy import deepcopy
import base64
import random


def random_client_id():
    """Returns a random client identifier"""
    return 'py_%s' % base64.b64encode(str(random.randint(1, 0x40000000)))


class StateCRDT(object):
    __metaclass__ = ABCMeta

    #
    # Abstract methods
    #

    @abstractmethod
    def __init__(self):
        pass

    @abstractproperty
    def value(self):
        """Returns the expected value generated from the payload"""
        pass

    @abstractproperty
    def payload(self):
        """This is a deepcopy-able version of the CRDT's payload.

        If the CRDT is going to be serialized to storage, this is the
        data that should be stored.
        """
        pass

    @classmethod
    @abstractmethod
    def merge(cls, X, Y):
        """Merge two replicas of this CRDT"""
        pass

    #
    # Built-in methods
    #

    def __repr__(self):
        return "<%s %s>" % (self.__class__, self.value)

    def clone(self):
        """Create a copy of this CRDT instance"""
        return self.__class__.from_payload(deepcopy(self.payload))

    @classmethod
    def from_payload(cls, payload, *args, **kwargs):
        """Create a new instance of this CRDT using a payload.  This
        is useful for creating an instance using a deserialized value
        from a datastore."""
        new = cls(*args, **kwargs)
        new.payload = payload
        return new

########NEW FILE########
__FILENAME__ = counters
# -*- coding: utf-8 -*-
from copy import deepcopy
from base import StateCRDT, random_client_id
from abc import ABCMeta


class GCounter(StateCRDT):
    def __init__(self, client_id=None):
        self._payload = {}
        self.client_id = client_id or random_client_id()

    #
    # State-based CRDT API
    #
    def get_payload(self):
        return self._payload

    def set_payload(self, newp):
        self._payload = newp
    payload = property(get_payload, set_payload)


    def clone(self):
        new = super(GCounter, self).clone()

        # Copy the client id
        new.client_id = self.client_id
        return new


    @property
    def value(self):
        return sum(self.payload.itervalues())

    def compare(self, other):
        """
        (∀i ∈ [0, n − 1] : X.P [i] ≤ Y.P [i])
        """
        return all(self.payload.get(key, 0) <= other.payload.get(key, 0)
                   for key in other.payload)

    @classmethod
    def merge(cls, X, Y):
        """
        let ∀i ∈ [0,n − 1] : Z.P[i] = max(X.P[i],Y.P[i])
        """
        keys = set(X.payload.iterkeys()) | set(Y.payload.iterkeys())

        gen = ((key, max(X.payload.get(key, 0), Y.payload.get(key, 0)))
               for key in keys)

        return GCounter.from_payload(dict(gen))

    #
    # Number API
    #
    def __str__(self):
        return self.value.__str__()

    #
    # GCounter API
    #
    def increment(self):
        try:
            c = self.payload[self.client_id]
        except KeyError:
            c = 0

        self.payload[self.client_id] = c + 1

    def __cmp__(self, other):
        return self.value.__cmp__(other.value)


class PNCounter(StateCRDT):
    def __init__(self, client_id=None):
        self.P = GCounter()
        self.N = GCounter()
        self.client_id = client_id or random_client_id()

    #
    # State-based CRDT API
    #
    def get_payload(self):
        return {
            "P": self.P.payload,
            "N": self.N.payload
            }

    def set_payload(self, payload):
        self.P.payload = payload['P']
        self.N.payload = payload['N']

    payload = property(get_payload, set_payload)

    def get_client_id(self):
        return self._cid

    def set_client_id(self, client_id):
        self._cid = client_id
        self.P.client_id = client_id
        self.N.client_id = client_id

    client_id = property(get_client_id, set_client_id)

    def clone(self):
        new = super(PNCounter, self).clone()

        # Copy the client id
        new.client_id = self.client_id
        return new

    @property
    def value(self):
        return self.P.value - self.N.value

    @classmethod
    def merge(cls, X, Y):
        merged_P = GCounter.merge(X.P, Y.P)
        merged_N = GCounter.merge(X.N, Y.N)

        merged_payload = {
            "P": merged_P.payload,
            "N": merged_N.payload,
            }
        return PNCounter.from_payload(merged_payload)

    def compare(self, other):
        """
        (∀i ∈ [0, n − 1] : X.P [i] ≤ Y.P [i] ∧
        ∀i ∈ [0, n − 1] : X.N[i] ≤ Y.N[i]
        """
        P_compare = self.P.compare(other.P)
        N_compare = self.N.compare(other.N)

        return P_compare and N_compare

    #
    # Counter API
    #
    def increment(self):
        self.P.increment()

    def decrement(self):
        self.N.increment()

    def __cmp__(self, other):
        return self.value.__cmp__(other.value)

########NEW FILE########
__FILENAME__ = sets
# -*- coding: utf-8 -*-
from base import StateCRDT, random_client_id
from copy import deepcopy
from collections import MutableSet
from counters import GCounter
from time import time
import uuid


class SetStateCRDT(StateCRDT, MutableSet):

    def __contains__(self, element):
        return self.value.__contains__(element)

    def __iter__(self):
        return self.value.__iter__()

    def __len__(self):
        return self.value.__len__()


class GSet(SetStateCRDT):
    def __init__(self):
        self._payload = set()

    @classmethod
    def merge(cls, X, Y):
        merged = GSet()
        merged._payload = X._payload.union(Y._payload)

        return merged

    def compare(self, other):
        return self.issubset(other)

    @property
    def value(self):
        return self._payload

    def get_payload(self):
        return list(self._payload)

    def set_payload(self, payload):
        self._payload = set(payload)

    payload = property(get_payload, set_payload)

    #
    # Set API
    #
    def add(self, element):
        self._payload.add(element)

    def discard(self, element):
        raise NotImplementedError("This is a grow-only set")


class LWWSet(SetStateCRDT):
    def __init__(self):
        self.A = {}
        self.R = {}

    def compare(self, other):
        pass

    @property
    def value(self):
        return set(e for (e, ts) in self.A.iteritems()
                   if ts >= self.R.get(e, 0))

    @classmethod
    def _merged_dicts(cls, x, y):
        new = {}
        keys = set(x) | set(y)
        for key in keys:
            new[key] = max(x.get(key,0), y.get(key, 0))

        return new

    @classmethod
    def merge(cls, X, Y):
        payload = {
            "A": cls._merged_dicts(X.A, Y.A),
            "R": cls._merged_dicts(X.R, Y.R),
            }

        return cls.from_payload(payload)

    def get_payload(self):
        return {
            "A": self.A,
            "R": self.R,
            }

    def set_payload(self, payload):
        self.A = payload['A']
        self.R = payload['R']

    payload = property(get_payload, set_payload)

    def add(self, element):
        self.A[element] = (time(), )
        
    def discard(self, element):
        if element in self.A:
            self.R[element] = (time(), )


class TwoPSet(SetStateCRDT):
    def __init__(self):
        self.A = GSet()
        self.R = GSet()

    @classmethod
    def merge(cls, X, Y):
        merged_A = GSet.merge(X.A, Y.A)
        merged_R = GSet.merge(X.R, Y.R)

        merged_payload = {
            "A": merged_A,
            "R": merged_R,
            }

        return TwoPSet.from_payload(merged_payload)

    def compare(self, other):
        """
        (S.A ⊆ T.A ∨ S.R ⊆ T.R)
        """
        A_compare = self.A.compare(other.A)
        R_compare = self.R.compare(other.R)

        return A_compare or R_compare

    @property
    def value(self):
        return self.A.value - self.R.value

    def get_payload(self):
        return {
            "A": self.A.payload,
            "R": self.R.payload,
            }

    def set_payload(self, payload):
        self.A = GSet.from_payload(payload['A'])
        self.R = GSet.from_payload(payload['R'])

    payload = property(get_payload, set_payload)

    def __contains__(self, element):
        return element in self.A and element not in self.R

    def __iter__(self):
        return self.value.__iter__(element)

    def __len__(self):
        return self.value.__len__(element)

    def add(self, element):
        self.A.add(element)

    def discard(self, element):
        if element in self:
            self.R.add(element)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import bisect

class SortedSet(MutableSet):
    def __init__(self, items):
        if items:
            self.items = sorted(items)
        else:
            self.items = []

    def __repr__(self):
        return "SortedSet(%s)" % (self.items, )

    def add(self, element):
        i = bisect.bisect_left(self.items, element)

        if i == len(self.items):
            self.items.append(element)
        elif self.items[i] != element:
            self.items.insert(i, element)

    def remove(self, element):
        try:
            i = self.items.index(element)
            del self.items[i]
        except ValueError:
            raise KeyError(element)

    def discard(self, element):
        try:
            i = self.items.index(element)
            del self.items[i]
        except ValueError:
            pass

    def __len__(self):
        return self.items.__len__()

    def __contains__(self, e):
        return self.items.__contains__(e)

    def __iter__(self):
        return iter(self.items)

########NEW FILE########
__FILENAME__ = demo
import os
import json
from friendship import Friendship


def load(user_key):
    filename = "./%s.friendship.json" % user_key
    if os.path.exists(filename):
        with open(filename) as fh:
            return Friendship.from_payload(json.load(fh))
    else:
        new = Friendship()
        new.user_key = user_key
        return new


def store(friendship):
    filename = "./%s.friendship.json" % friendship.user_key

    with open(filename, "w") as fh:
        json.dump(friendship.payload, fh)
    

def friend_glenn():
    eric = load("eric")
    glenn = load("glenn")

    eric.follow(glenn)

    store(eric)
    store(glenn)


friend_glenn()

eric = load("eric")

print "Is eric following glenn?", "glenn" in eric.following 


########NEW FILE########
__FILENAME__ = friendship
from crdt.sets import LWWSet
from crdt.base import StateCRDT


class Friendship(StateCRDT):
    def __init__(self):
        # The user key is considered constant among replicas
        # so no CRDT is needed
        self.user_key  = None
        self.following = LWWSet()
        self.followers = LWWSet()

    def get_payload(self):
        assert self.user_key, "Can not generate a payload without a user_key"
        return {
            "user_key": self.user_key,
            "following": self.following.payload,
            "followers": self.followers.payload,
        }

    def set_payload(self, payload):
       self.following = LWWSet.from_payload(payload['following'])
       self.followers = LWWSet.from_payload(payload['followers'])

       self.user_key  = payload['user_key']

    payload = property(get_payload, set_payload)

    @property
    def value(self):
        return {
            "user_key": self.user_key,
            "following": self.following.value,
            "followers": self.followers.value,
            }
    
    @classmethod
    def merge(cls, X, Y):
        assert X.user_key == Y.user_key, "User keys do not match"
        assert X.user_key is not None, "user_key must be set"

        following = LWWSet.merge(X.following, Y.following)
        followers = LWWSet.merge(X.following, Y.following)

        new = cls()
        new.user_key = X.user_key
        new.following = following
        new.followers = followers
        
        return new

    #
    # Friendship API
    # 
    def follow(self, friend):
        self.following.add(friend.user_key)
        friend.followers.add(self.user_key)

    def unfollow(self, friend):
        self.following.discard(friend.user_key)
        friend.followers.discard(self.user_key)

########NEW FILE########
__FILENAME__ = test_counters
# -*- coding: utf-8 -*-
from crdt.counters import GCounter, PNCounter

def test_gcounter():
    """
     []
   /    \
 A[a:1] B[b:1]       +1, +1
   |     |  \
   |     |    \
   |    /      |
 AB[a:1, b:1]  |     merge
   |           |
 AB[a:2, b:1]  |      +1
   |           |
    \      B2[b:2]    +1
     \         |
      \       /
    ABB2[a:2, b:2]    merge
    """

    A = GCounter(client_id="a")
    B = GCounter(client_id="b")

    A.increment()
    assert A.payload == {"a": 1}

    B.increment()
    assert B.payload == {"b": 1}

    B2 = B.clone()
    assert B2.payload == {"b": 1}

    B2.increment()
    assert B2.payload == {"b": 2}

    AB = GCounter.merge(A, B)
    AB.client_id = "a"
    assert AB.payload == {"a": 1, "b": 1}

    AB.increment()
    assert AB.payload == {"a": 2, "b": 1}

    ABB2 = GCounter.merge(AB, B2)
    assert ABB2.payload == {"a": 2, "b": 2}


def test_pncounter():
    """
        [ ] - [ ]
         /       \
  [a:1] - [ ]     [ ] - [b:1]   +1 -1
        |           |
  [a:1] - [a:1]   [ ] - [b:2]   -1 -1
        |          / \
         \       /     \
          \     /       |
  [a:1] - [a:1 b:2]     |      merge
        |               |
        |         [ ] - [b:3]   -1
         \             /
        [a:1] - [a:1 b:3]         merge
        """

    A = PNCounter(client_id="a")
    B = PNCounter(client_id="b")

    A.increment()
    B.decrement()

    A.decrement()
    B.decrement()

    AB = PNCounter.merge(A, B)

    B2 = B.clone()
    B2.decrement()

    ABB2 = PNCounter.merge(AB, B2)

    assert ABB2.value == -3

if __name__ == '__main__':
    test_gcounter()
    test_pncounter()

########NEW FILE########
__FILENAME__ = test_sets
# -*- coding: utf-8 -*-
from crdt.sets import GSet, TwoPSet, LWWSet
from crdt import sets
import time

def test_gset():
    """
        {},{}
      /       \
  A{eric},{}   B{glenn},{}            +eric +glenn
    |               |
 A{eric mark},{}    |                 +mark
    |             /   \
    |           /      \
     \         /        \
      \       /     B2{glenn tom}     +tom
        \   /              \
   AB{eric mark glenn}      \         <<merge>>
            \               /
             \             /
      ABB2{eric mark tom glenn}   <<merge>>
    """
    A = GSet()
    B = GSet()

    A.add("eric")
    A.add("mark")
    B.add("glenn")
    B2 = B.clone()

    AB = GSet.merge(A, B)

    B2.add("tom")

    ABB2 = GSet.merge(AB, B2)
    assert ABB2.value == {"eric", "mark", "tom", "glenn"}, ABB2.value


def test_towpset():
    """
        {},{}
      /       \
  A{eric},{}   B{glenn},{}          +eric +glenn
    |             \
 A{eric mark},{} B{glenn tom},{}   +mark +tom
    |             /   \
    |           /      \
     \         /        \
      \       /     B2{glenn tom},{tom}   -tom
        \   /              \
   AB{eric mark tom glenn}  \   <<merge>>
            \               /
             \             /
    ABB2{eric mark tom glenn},{tom}   <<merge>>

    """
    A = TwoPSet()
    B = TwoPSet()

    A.add("eric")
    B.add("glenn")

    A.add("mark")
    B.add("tom")

    AB = TwoPSet.merge(A, B)

    B2 = B.clone()
    B2.remove("tom")

    ABB2 = TwoPSet.merge(AB, B2)
    assert ABB2.value == {"eric", "mark", "glenn"}, ABB2.value


def test_lwwset():
    A = LWWSet()
    
    fake_time = 1

    def mock_time():
        return fake_time
    old_time = sets.time
    sets.time = mock_time

    A.add("eric")

    B = A.clone()
    C = A.clone()

    # Test that concurrent updates favor add
    fake_time = 2
    B.add("eric")
    C.remove("eric")

    D = LWWSet.merge(B, C)

    assert D.value == set(["eric"])

    sets.time = old_time

########NEW FILE########
