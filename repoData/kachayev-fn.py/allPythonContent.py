__FILENAME__ = func
from functools import partial

from .op import identity, flip

class F(object):
    """Provide simple syntax for functions composition
    (through << and >> operators) and partial function 
    application (through simple tuple syntax). 

    Usage example:

    >>> func = F() << (_ + 10) << (_ + 5)
    >>> print(func(10))
    25
    >>> func = F() >> (filter, _ < 6) >> sum
    >>> print(func(range(10))) 
    15
    """

    __slots__ = "f", 

    def __init__(self, f = identity, *args, **kwargs):
        self.f = partial(f, *args, **kwargs) if any([args, kwargs]) else f

    @classmethod
    def __compose(cls, f, g):
        """Produces new class intance that will 
        execute given functions one by one. Internal
        method that was added to avoid code duplication
        in other methods.
        """
        return cls(lambda *args, **kwargs: f(g(*args, **kwargs)))

    def __ensure_callable(self, f):
        """Simplify partial execution syntax. 
        Rerurn partial function built from tuple 
        (func, arg1, arg2, ...)
        """
        return self.__class__(*f) if isinstance(f, tuple) else f

    def __rshift__(self, g):
        """Overload << operator for F instances"""
        return self.__class__.__compose(self.__ensure_callable(g), self.f)

    def __lshift__(self, g):
        """Overload >> operator for F instances"""
        return self.__class__.__compose(self.f, self.__ensure_callable(g))

    def  __call__(self, *args, **kwargs):
        """Overload apply operator"""
        return self.f(*args, **kwargs)
########NEW FILE########
__FILENAME__ = finger
"""Finger tree implementation and application examples.

A finger tree is a purely functional data structure used in
efficiently implementing other functional data structures. A
finger tree gives amortized constant time access to the "fingers"
(leaves) of the tree, where data is stored, and the internal
nodes are labeled in some way as to provide the functionality of
the particular data structure being implemented.

More information on Wikipedia: http://goo.gl/ppH2nE

"Finger trees: a simple general-purpose data structure": http://goo.gl/jX4DeL
"""

from collections import namedtuple

# data Node a = Node2 a a | Node3 a a a
# data Digit a = One a | Two a a | Three a a a | Four a a a a 
# data FingerTree a = Empty
#                   | Single a
#                   | Deep (Digit a) (FingerTree (Node a)) (Digit a)

One = namedtuple("One", "a")
Two = namedtuple("Two", "a,b")
Three = namedtuple("Three", "a,b,c")
Four = namedtuple("Four", "a,b,c,d")

class Node2(namedtuple("Node2", "a,b")):
    def __iter__(self):
        yield self.a
        yield self.b

class Node3(namedtuple("Node3", "a,b,c")):
    def __iter__(self):
        yield self.a
        yield self.b
        yield self.c

Empty = namedtuple("Empty", "measure") 
Single = namedtuple("Single", "measure,elem")
Deep = namedtuple("Deep", "measure,left,middle,right")

class FingerTree(object):

    class Empty(Empty):
        def is_empty(self): return True
        def head(self): return None
        def last(self): return None
        def tail(self): return self
        def butlast(self): return self
        def push_front(self, v):
            return FingerTree.Single(self.measure, v)
        def push_back(self, v):
            return FingerTree.Single(self.measure, v)
        def __iter__(self): return iter([])

    class Single(Single):
        def is_empty(self): return False
        def head(self): return self.elem
        def last(self): return self.elem
        def tail(self): return FingerTree.Empty(self.measure)
        def butlast(self): return FingerTree.Empty(self.measure)
        def push_front(self, v):
            return FingerTree.Deep(self.measure, [v], FingerTree.Empty(self.measure), [self.elem])
        def push_back(self, v):
            return FingerTree.Deep(self.measure, [self.elem], FingerTree.Empty(self.measure), [v])
        def __iter__(self): return iter([self.elem])

    class Deep(Deep):
        def is_empty(self): return False
        def head(self): return self.left[0]
        def last(self): return self.right[-1]

        def tail(self):
            if len(self.left) == 1:
                if self.middle.is_empty():
                    return FingerTree.from_iterable(self.measure, list(self.right))
                return FingerTree.Deep(self.measure,
                                       [self.middle.head()],
                                       self.middle.tail(),
                                       self.right)
            return FingerTree.Deep(self.measure, self.left[1:], self.middle, self.right)

        def butlast(self):
            if len(self.rigth) == 1:
                if self.middle.is_empty():
                    return FingerTree.from_iterable(self.measure, list(self.left))
                return FingerTree.Deep(self.measure,
                                       self.left,
                                       self.middle.butlast(),
                                       [self.middle.last()])
            return FingerTree.Deep(self.measure, self.left, self.middle, self.right[:-1])

        def push_front(self, v):
            if len(self.left) == 4:
                return FingerTree.Deep(self.measure,
                                       [v, self.left[0]],
                                       self.middle.push_front(Node3(*self.left[1:])),
                                       self.right)
            return FingerTree.Deep(self.measure, [v] + self.left, self.middle, self.right)

        def push_back(self, v):
            if len(self.right) == 4:
                return FingerTree.Deep(self.measure,
                                       self.left,
                                       self.middle.push_back(Node3(*self.right[:3])),
                                       [self.right[-1], v])                
            return FingerTree.Deep(self.measure, self.left, self.middle, self.right + [v])

        def __iter__(self):
            for l in self.left: yield l
            for m in self.middle:
                for mi in m:
                    yield mi
            for r in self.right: yield r

    @staticmethod
    def from_iterable(measure, it):
        tree = FingerTree.Empty(measure)
        return reduce(lambda acc, curr: acc.push_front(curr), it, tree)

    def __new__(_cls, measure):
        return FingerTree.Empty(measure)


#####################################################
# Possible applications of finger tree in practice
#####################################################

class Deque(object):
    def __new__(_cls):
        return FingerTree.Empty(lambda x: x)

    @staticmethod
    def from_iterable(it):
        return FingerTree.from_iterable(lambda x: x, it)

########NEW FILE########
__FILENAME__ = heap
from functools import partial
from fn.op import identity

default_cmp = (lambda a,b: -1 if (a < b) else 1)

class _MergeBased(object):

    def __nonzero__(self):
        return self.root is not None

    def __bool__(self):
        return self.__nonzero__()

    def __iter__(self):
        """Extract elements one-by-one.
        Note, that list(*Heap()) gives you sorted list as result.
        """
        curr = self
        while curr:
            r, curr = curr.extract()
            yield r

    def __lt__(self, other):
        if (not self) and (not other): return False
        if not self: return True
        if not other: return False
        return self.cmpfn(self.keyfn(self.root), self.keyfn(other.root)) < 0

class SkewHeap(_MergeBased):
    """A skew heap (or self-adjusting heap) is a heap data structure
    implemented as a binary-tree. Amortized complexity analytics can
    be used to demonstrate that all operations one a skew heap can be
    done in O(log n).

    Skew heaps may be described with the following recursive definition:
    * a heap with only one element is a skew heap
    * the result of skew merging two skew heaps is also a skew heap

    In Haskell type definition it should looks like following:
    data Skew a = Empty | Node a (Skew a) (Skew a)

    More information on Wikipedia:
    [1] http://en.wikipedia.org/wiki/Skew_heap

    One can also check slides from my KyivPy#11 talk "Union-based heaps":
    [2] http://goo.gl/VMgdG2

    Basic usage sample:

    >>> from fn.immutable import SkewHeap
    >>> s = SkewHeap(10)
    >>> s = s.insert(20)
    >>> s
    <fn.immutable.heap.SkewHeap object at 0x10b14c050>
    >>> s = s.insert(30)
    >>> s
    <fn.immutable.heap.SkewHeap object at 0x10b14c158> # <-- other object
    >>> s.extract()
    (10, <fn.immutable.heap.SkewHeap object at 0x10b14c050>)
    >>> _, s = s.extract()
    >>> s.extract()
    (20, <fn.immutable.heap.SkewHeap object at 0x10b14c1b0>)
    """

    __slots__ = ("root", "left", "right", "keyfn", "cmpfn", "_make_heap")

    def __init__(self, el=None, left=None, right=None, key=None, cmp=None):
        """Creates skew heap with one element (or empty one)"""
        self.root = el
        self.left = left
        self.right = right
        self.keyfn = key or identity
        self.cmpfn = cmp or default_cmp
        self._make_heap = partial(self.__class__, key=self.keyfn, cmp=self.cmpfn)        

    def insert(self, el):
        """Returns new skew heap with additional element"""
        return self._make_heap(el).union(self)

    def extract(self):
        """Returns pair of values:
        * minimum (or maximum regarding to given compare function)
        * new skew heap without extracted element

        Or None and empty heap if self is an empty heap.
        """
        if not self: return None, self._make_heap()
        return self.root, self.left.union(self.right) if self.left else self._make_heap()

    def union(self, other):
        """Merge two heaps and returns new one (skew merging)"""
        if not self: return other
        if not other: return self

        if self < other:
            return self._make_heap(self.root, other.union(self.right), self.left)
        return self._make_heap(other.root, self.union(other.right), other.left)

class PairingHeap(_MergeBased):
    """A pairing heap is either an empty heap, or a pair consisting of a root
    element and a possibly empty list of pairing heap. The heap ordering property
    requires that all the root elements of the subheaps in the list are not
    smaller (bigger) than the root element of the heap.

    In Haskell type definition it should looks like following:
    data Pairing a = Empty | Node a [Pairing a]

    Pairing heap has and excellent practical amortized performance. The amortized
    time per extract is less than O(log n), find-min/find-max, merge and insert are O(1).

    More information about performance bounds you can find here:
    "The Pairing Heap: A New Form of Self-Adjusting Heap"
    [1] http://www.cs.cmu.edu/afs/cs.cmu.edu/user/sleator/www/papers/pairing-heaps.pdf

    More general information on Wikipedia:
    [2] http://en.wikipedia.org/wiki/Pairing_heap

    One can also check slides from my KyivPy#11 talk "Union-based heaps":
    [3] http://goo.gl/VMgdG2

    Basic usage sample:

    >>> from fn.immutable import PairingHeap
    >>> ph = PairingHeap("a")
    >>> ph = ph.insert("b")
    >>> ph
    <fn.immutable.heap.PairingHeap object at 0x10b13fa00>
    >>> ph = ph.insert("c")
    >>> ph
    <fn.immutable.heap.PairingHeap object at 0x10b13fa50>
    >>> ph.extract()
    ('a', <fn.immutable.heap.PairingHeap object at 0x10b13fa00>)
    >>> _, ph = ph.extract()
    >>> ph.extract()
    ('b', <fn.immutable.heap.PairingHeap object at 0x10b13f9b0>)
    """

    __slots__ = ("root", "subs", "keyfn", "cmpfn", "_make_heap")

    def __init__(self, el=None, subs=None, key=None, cmp=None):
        """Creates singlton from given element 
        (pairing heap with one element or empty one)
        """
        self.root = el
        self.subs = subs
        self.keyfn = key or identity
        self.cmpfn = cmp or default_cmp
        self._make_heap = partial(self.__class__, key=self.keyfn, cmp=self.cmpfn)

    def insert(self, el):
        """Returns new pairing heap with additional element"""
        return self.union(self._make_heap(el))

    def extract(self):
        """Returns pair of values:
        * minimum (or maximum regarding to given compare function)
        * new pairing heap without extracted element

        Or None and empty heap if self is an empty heap.
        """
        if not self: return None, self._make_heap()
        return self.root, PairingHeap._pairing(self._make_heap, self.subs)

    def union(self, other):
        """Returns new heap as a result of merging two given
        
        Note, that originally this operation for pairingi heap was
        named "meld", see [1] and [2]. We use here name "union" to
        follow consistent naming convention for all heap implementations.
        """ 
        if not self: return other
        if not other: return self

        if self < other:
            return self._make_heap(self.root, (other, self.subs))
        return self._make_heap(other.root, (self, other.subs))

    @staticmethod
    def _pairing(heap, hs):
        if hs is None: return heap()
        (h1, tail) = hs
        if tail is None: return h1
        (h2, tail) = tail
        return PairingHeap._pairing(heap, (h1.union(h2), tail))

########NEW FILE########
__FILENAME__ = list
from fn.uniform import reduce

class LinkedList(object):
    """Represents simplest singly linked list. Doesn't distinguish
    between empty and not-empty list (taking head of empty list will
    return None as a result).

    More about Linked List data structure on Wikipedia:
    [1] http://en.wikipedia.org/wiki/Linked_list

    Usage:

    >>> from fn.immutable import LinkedList
    >>> l = LinkedList()
    >>> l.cons(10)
    <fn.immutable.list.LinkedList object at 0x10acfbb00>
    >>> l.cons(10).cons(20).cons(30).head
    30
    >>> l.cons(10).cons(20).cons(30).tail
    <fn.immutable.list.LinkedList object at 0x10acfbc20>
    >>> l.cons(10).cons(20).cons(30).tail.head
    20
    >>> len(l.cons(10).cons(20).cons(30))
    3
    >>> list(l.cons(10).cons(20).cons(30))
    [30, 20, 10]
    >>> list(l + 100 + 110 + 120)
    [120, 110, 100]
    """

    __slots__ = ("head", "tail", "_count")
    
    def __init__(self, head=None, tail=None):
        self.head = head
        self.tail = tail
        self._count = 0 if tail is None else (len(tail) + 1)

    def cons(self, el):
        return self.__class__(el, self)

    def __add__(self, el):
        return self.cons(el)

    def __radd__(self, el):
        return self.cons(el)

    def __iter__(self):
        l = self
        while l:
            yield l.head
            l = l.tail

    def __len__(self):
        return self._count

    def __nonzero__(self):
        return self.tail is not None

    def __bool__(self):
        return len(self) > 0

class Stack(LinkedList):
    """Technically it's a LinkedList, but it provides more familiar
    API for Stack operations: push and pop. It also distinguishes between
    empty and non-empty structure, so trying to pop from empty stack will
    throw ValueError.
    """

    def push(self, el):
        return self.cons(el)

    def pop(self):
        if not self: raise ValueError("Stack is empty")
        return self.head, self.tail

    def is_empty(self):
        return not self

class Queue(object):
    """A queue is a particular kind of collection in which the entities in the collection
    are kept in order and the principal operations on the collection are the addition of
    entities to the rear terminal position, known as enqueue, and removal of entities from
    the front terminal position, known as dequeue.

    Queue data structure description on Wikipedia:
    [1] http://en.wikipedia.org/wiki/Queue_(abstract_data_type)

    Implementation based on two linked lists (left and right). Enqueue operation
    performs cons on right list (the end of the queue). Dequeue peeks first element
    from the left list (when possible), if left list is emptpy we populate left list
    with element from right one-by-one (in natural reverse order). Complexity of both
    operations are O(1).

    Such implementation is also known as "Banker's Queue" in different papers,
    i.e. in Chris Okasaki, "Purely Functional Data Structures"

    Usage:

    >>> from fn.immutable import Queue
    >>> q = Queue()
    >>> q1 = q.enqueue(10)
    >>> q2 = q1.enqueue(20)
    >>> el, tail = q2.dequeue()
    >>> el
    10
    >>> tail.dequeue()
    (20, <fn.immutable.list.Queue object at 0x1055554d0>)
    """

    __slots__ = ("left", "right")

    def __init__(self, left=None, right=None):
        self.left = left if left is not None else LinkedList()
        self.right = right if right is not None else LinkedList()

    def enqueue(self, el):
        """Returns new queue object with given element is added onto the end"""
        # check if we need to rebalance to prevent spikes
        if len(self.left) >= len(self.right):
            return Queue(self.left, self.right.cons(el))
        left = reduce(lambda acc, el: acc.cons(el), self.right, self.left)
        return Queue(left, LinkedList().cons(el))

    def dequeue(self):
        """Return pair of values: the item from the front of the queue and
        the new queue object without poped element.
        """
        if not self: raise ValueError("Queue is empty")
        # if there is at least one element on the left, we can return it
        if self.left:
            return self.left.head, Queue(self.left.tail, self.right)

        # in other case we need to copy right to left before
        d = reduce(lambda acc, el: acc.cons(el), self.right, LinkedList())
        return d.head, Queue(d.tail, LinkedList())

    def is_empty(self):
        return len(self) == 0

    def __iter__(self):
        curr = self
        while curr:
            el, curr = curr.dequeue()
            yield el

    def __nonzero__(self):
        return len(self)

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        lleft = len(self.left) if self.left is not None else 0
        lright = len(self.right) if self.right is not None else 0
        return lleft + lright

class Deque(object):
    """Double-ended queue is an  abstract data type that generalizes
    a queue, for which elements can be added to or removed from either
    the front (head) or back (tail).

    More information on Wikipedia:
    [1] http://en.wikipedia.org/wiki/Double-ended_queue

    Implementation details are described here:
    "Confluently Persistent Deques via Data Structural Bootstrapping"
    [2] https://cs.uwaterloo.ca/~imunro/cs840/p155-buchsbaum.pdf

    xxx: TBD
    """
    pass

########NEW FILE########
__FILENAME__ = trie
from fn import Stream
from fn.uniform import reduce
from fn.iters import takewhile

class Vector(object):
    """A vector is a collection of values indexed by contiguous integers.
    Based on Philip Bagwell's "Array Mapped Trie" and Rick Hickey's 
    "Bitmapped Vector Trie". As well as Clojure variant it supports access
    to items by index in log32N hops. 

    Code structure inspired much by PersistenVector.java (Clojure core):
    [1] http://goo.gl/sqtZ74

    Usage:
    >>> from fn.immutable import Vector
    >>> v = Vector()
    >>> v1 = v.assoc(0, 10)
    >>> v2 = v1.assoc(1, 20)
    >>> v3 = v2.assoc(2, 30)
    >>> v3.get(0)
    10
    >>> v3.get(1)
    20
    >>> v3.get(2)
    30
    >>> v4 = v2.assoc(2, 50)
    >>> v3.get(2) # <-- previous version didn't change
    30
    >>> v4.get(2)
    50
    """

    __slots__ = ("length", "shift", "root", "tail")

    class _Node(object):
        __slots__ = ("array")

        def __init__(self, values=None, init=None):
            self.array = values or [None]*32
            if init is not None: self.array[0] = init

        def __str__(self):
            return str(self.array)

        def __iter__(self):
            s = reduce(lambda acc, el: acc << (el if isinstance(el, self.__class__) else [el]),
                       takewhile(lambda el: el is not None, self.array),
                       Stream())
            return iter(s)

    def __init__(self, length=0, shift=None, root=None, tail=None):
        self.length = length
        self.shift = shift if shift is not None else 5
        self.root = root or self.__class__._Node()
        self.tail = tail if tail is not None else []

    def assoc(self, pos, el):
        """Returns a new vector that contains el at given position.
        Note, that position must be <= len(vector)
        """
        if pos < 0 or pos > self.length: raise IndexError()
        if pos == self.length: return self.cons(el)
        if pos < self._tailoff():
            up = self.__class__._do_assoc(self.shift, self.root, pos, el)
            return self.__class__(self.length, self.shift, up, self.tail)

        up = self.tail[:]
        up[pos & 0x01f] = el;
        return self.__class__(self.length, self.shift, self.root, up)

    def _tailoff(self):
        if self.length < 32: return 0
        return ((self.length - 1) >> 5) << 5

    @classmethod
    def _do_assoc(cls, level, node, pos, el):
        r = cls._Node(node.array[:])
        if level == 0:
            r.array[pos & 0x01f] = el
        else:
            sub = (pos >> level) & 0x01f
            r.array[sub] = cls._do_assoc(level-5, node.array[sub], pos, el)
        return r

    def cons(self, el):
        # if there is a room in tail, just append value to tail
        if (self.length - self._tailoff()) < 32:
            tailup = self.tail[:]
            tailup.append(el)
            return self.__class__(self.length+1, self.shift, self.root, tailup)

        # if tail is already full, we need to push element into tree
        # (from the top)
        tailnode = self.__class__._Node(self.tail)

        # if root is overflowed, we need to expand the whole tree
        if (self.length >> 5) > (1 << self.shift):
            uproot = self.__class__._Node(init=self.root)
            uproot.array[1] = self.__class__._make_path(self.shift, tailnode)
            shift = self.shift + 5
        else:
            uproot = self._push_tail(self.shift, self.root, tailnode)
            shift = self.shift

        return self.__class__(self.length+1, shift, uproot, [el])

    def _push_tail(self, level, root, tail):
        sub = ((self.length - 1) >> level) & 0x01f
        r = self.__class__._Node(root.array[:])
        if level == 5:
            r.array[sub] = tail
        else:
            child = root.array[sub]
            if child is not None:
                r.array[sub] = self._push_tail(level-5, child, tail)
            else:
                r.array[sub] = self.__class__._make_path(level-5, tail)
        return r

    @classmethod
    def _make_path(cls, level, node):
        if level == 0: return node
        return cls._Node(init=cls._make_path(level-5, node))

    def get(self, pos):
        """Returns a value accossiated with position"""
        if pos < 0 or pos >= self.length: raise IndexError()
        return self._find_container(pos)[pos & 0x01f]

    def peek(self):
        """Returns the last item in vector or None if vector is empty"""
        if self.length == 0: return None
        return self.get(self.length-1)

    def pop(self):
        """Returns a new vector without the last item"""
        if self.length == 0: raise ValueError("Vector is empty")
        if self.length == 1: return self.__class__()
        if self.length - self._tailoff() > 1:
            return self.__class__(self.length-1, self.shift, self.root, self.tail[:-1])

        tail = self._find_container(self.length - 2)
        root = self._pop_tail(self.shift, self.root) or self.__class__._Node()
        shift = self.shift

        if shift > 5 and root.array[1] is None:
            root = root.array[0]
            shift -= 5

        return self.__class__(self.length-1, shift, root, tail)

    def _find_container(self, pos):
        if pos < 0 or pos > self.length: raise IndexError()
        if pos >= self._tailoff(): return self.tail
        bottom = reduce(lambda node, level: node.array[(pos >> level) & 0x01f],
                        range(self.shift,0,-5), self.root)
        return bottom.array

    def _pop_tail(self, level, node):
        sub = ((self.length - 2) >> level) & 0x01f
        if level > 5:
            child = self._pop_tail(level-5, node.array[sub])
            if child is None and sub == 0: return None
            r = self.__class__._Node(node.array[:])
            r.array[sub] = child
            return r
        elif sub == 0: return None
        else:
            r = self.__class__._Node(node.array[:])
            r.array[sub] = None
            return r
    
    def subvec(self, start, end=None):
        """Returns a new vector of the items in vector from start to end"""
        pass

    def __len__(self):
        return self.length

    def __iter__(self):
        s = Stream() << self.root << self.tail
        return iter(s)

    def __getitem__(self, pos):
        return self.get(pos)

    def __setitem__(self, pos, val):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = iters
from sys import version_info
from collections import deque, Iterable
from operator import add, itemgetter, attrgetter, not_
from functools import partial
from itertools import (islice, 
                       chain,                        
                       starmap, 
                       repeat, 
                       tee, 
                       cycle,
                       takewhile, 
                       dropwhile,
                       combinations)

from .op import flip
from .func import F
from .underscore import shortcut as _
from .uniform import *

def take(limit, base): 
    return islice(base, limit)

def drop(limit, base): 
    return islice(base, limit, None)

def takelast(n, iterable):
    "Return iterator to produce last n items from origin"
    return iter(deque(iterable, maxlen=n))

def droplast(n, iterable):
    "Return iterator to produce items from origin except last n"
    t1, t2 = tee(iterable)
    return map(itemgetter(0), zip(t1, islice(t2, n, None)))

def consume(iterator, n=None):
    """Advance the iterator n-steps ahead. If n is none, consume entirely.

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(islice(iterator, n, n), None)

def nth(iterable, n, default=None):
    """Returns the nth item or a default value

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    return next(islice(iterable, n, None), default)

# widely-spreaded shortcuts to get first item, all but first item,
# second item, and first item of first item from iterator respectively
head = first = partial(flip(nth), 0)
tail = rest = partial(drop, 1)
second = F(rest) >> first
ffirst = F(first) >> first

# shortcut to remove all falsey items from iterable
compact = partial(filter, None)

def reject(func, iterable):
    """Return an iterator yielding those items of iterable for which func(item)
    is false. If func is None, return the items that are false.
    """
    return filter(F(not_) << (func or _), iterable)

def iterate(f, x):
    """Return an iterator yielding x, f(x), f(f(x)) etc.
    """
    while True:
        yield x
        x = f(x)

def padnone(iterable):
    """Returns the sequence elements and then returns None indefinitely.
    Useful for emulating the behavior of the built-in map() function.

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    return chain(iterable, repeat(None))

def ncycles(iterable, n):
    """Returns the sequence elements n times

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    return chain.from_iterable(repeat(tuple(iterable), n))

def repeatfunc(func, times=None, *args):
    """Repeat calls to func with specified arguments.
    Example:  repeatfunc(random.random)

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    if times is None:
        return starmap(func, repeat(args))
    return starmap(func, repeat(args, times))

def grouper(n, iterable, fillvalue=None):
    """Collect data into fixed-length chunks or blocks, so
    grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

def group_by(keyfunc, iterable):
    """Returns a dict of the elements from given iterable keyed by result
    of keyfunc on each element. The value at each key will be a list of
    the corresponding elements, in the order they appeared in the iterable.
    """
    grouped = {}
    for item in iterable:
        grouped.setdefault(keyfunc(item), []).append(item)
    return grouped

def roundrobin(*iterables):
    """roundrobin('ABC', 'D', 'EF') --> A D E B F C
    Recipe originally credited to George Sakkis.
    Reimplemented to work both in Python 2+ and 3+. 

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    pending = len(iterables)
    next_attr = "next" if version_info[0] == 2 else "__next__"
    nexts = cycle(map(attrgetter(next_attr), map(iter, iterables)))
    while pending:
        try:
            for n in nexts:
                yield n()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))

def partition(pred, iterable):
    """Use a predicate to partition entries into false entries and true entries
    partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)

def splitat(t, iterable):
    """Split iterable into two iterators after given number of iterations
    splitat(2, range(5)) --> 0 1 and 2 3 4
    """
    t1, t2 = tee(iterable)
    return islice(t1, t), islice(t2, t, None)

def splitby(pred, iterable):
    """Split iterable into two iterators at first false predicate
    splitby(is_even, range(5)) --> 0 and 1 2 3 4
    """
    t1, t2 = tee(iterable)
    return takewhile(pred, t1), dropwhile(pred, t2)

def powerset(iterable):
    """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

def pairwise(iterable):
    """pairwise(s) -> (s0,s1), (s1,s2), (s2, s3), ...

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def iter_except(func, exception, first_=None):
    """ Call a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like __builtin__.iter(func, sentinel) but uses an exception instead
    of a sentinel to end the loop.

    Examples:
        iter_except(functools.partial(heappop, h), IndexError)   # priority queue iterator
        iter_except(d.popitem, KeyError)                         # non-blocking dict iterator
        iter_except(d.popleft, IndexError)                       # non-blocking deque iterator
        iter_except(q.get_nowait, Queue.Empty)                   # loop over a producer Queue
        iter_except(s.pop, KeyError)                             # non-blocking set iterator

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    try:
        if first_ is not None:
            yield first_()            # For database APIs needing an initial cast to db.first()
        while 1:
            yield func()
    except exception:
        pass


def flatten(items):
    """Flatten any level of nested iterables (not including strings, bytes or
    bytearrays).
    Reimplemented to work with all nested levels (not only one).

    http://docs.python.org/3.4/library/itertools.html#itertools-recipes
    """
    for item in items:
        is_iterable = isinstance(item, Iterable)
        is_string_or_bytes = isinstance(item, (str, bytes, bytearray))
        if is_iterable and not is_string_or_bytes:
            for i in flatten(item):
                yield i
        else:
            yield item

if version_info[0] == 3 and version_info[1] >= 3:
    from itertools import accumulate
else:
    def accumulate(iterable, func=add):
        """Make an iterator that returns accumulated sums. 
        Elements may be any addable type including Decimal or Fraction. 
        If the optional func argument is supplied, it should be a 
        function of two arguments and it will be used instead of addition.

        Origin implementation:
        http://docs.python.org/dev/library/itertools.html#itertools.accumulate

        Backported to work with all python versions (< 3.3)
        """
        it = iter(iterable)
        total = next(it)
        yield total
        for element in it:
            total = func(total, element)
            yield total


########NEW FILE########
__FILENAME__ = monad
"""
``fn.monad.Option`` represents optional values, each instance of 
``Option`` can be either instance of ``Full`` or ``Empty``. 
It provides you with simple way to write long computation sequences 
and get rid of many ``if/else`` blocks. See usage examples below. 

Assume that you have ``Request`` class that gives you parameter 
value by its name. To get uppercase notation for non-empty striped value:

    class Request(dict):
        def parameter(self, name):
            return self.get(name, None)

    r = Request(testing="Fixed", empty="   ")
    param = r.parameter("testing")
    if param is None:
        fixed = ""
    else:
        param = param.strip()
        if len(param) == 0:
            fixed = ""
        else:
            fixed = param.upper()


Hmm, looks ugly.. Update code with ``fn.monad.Option``:

    from operator import methodcaller
    from fn.monad import optionable

    class Request(dict):
        @optionable
        def parameter(self, name):
            return self.get(name, None)

    r = Request(testing="Fixed", empty="   ")
    fixed = r.parameter("testing")
             .map(methodcaller("strip"))
             .filter(len)
             .map(methodcaller("upper"))
             .get_or("")

``fn.monad.Option.or_call`` is good method for trying several 
variant to end computation. I.e. use have ``Request`` class 
with optional attributes ``type``, ``mimetype``, ``url``. 
You need to evaluate "request type" using at least on attribute:

    from fn.monad import Option

    request = dict(url="face.png", mimetype="PNG")
    tp = Option(request.get("type", None)) \ # check "type" key first
            .or_call(from_mimetype, request) \ # or.. check "mimetype" key
            .or_call(from_extension, request) \ # or... get "url" and check extension
            .get_or("application/undefined")


"""

from collections import namedtuple
from functools import wraps, partial
from operator import eq, is_not

class Option(object):

    def __new__(tp, value, checker=partial(is_not, None)):
        if isinstance(value, Option):
            # Option(Full) -> Full
            # Option(Empty) -> Empty
            return value

        return Full(value) if checker(value) else Empty()

    @staticmethod
    def from_value(value):
        return Option(value)

    @staticmethod
    def from_call(callback, *args, **kwargs):
        """Execute callback and catch possible (all by default)
        exceptions. If exception is raised Empty will be returned.
        """
        exc = kwargs.pop("exc", Exception)
        try:
            return Option(callback(*args, **kwargs)) 
        except exc:
            return Empty()

    def map(self, callback):
        raise NotImplementedError()

    def filter(self, callback):
        raise NotImplementedError()

    def get_or(self, default):
        raise NotImplementedError()

    def get_or_call(self, callback, *args, **kwargs):
        raise NotImplementedError()

    def or_else(self, default):
        raise NotImplementedError()

    def or_call(self, callback, *args, **kwargs):
        raise NotImplementedError()

class Full(Option):
    """Represents value that is ready for further computations"""

    __slots__ = "x", 
    empty = False 

    def __new__(tp, value, *args, **kwargs):
        # Full(Empty) -> Full
        if isinstance(value, Empty):
            return Empty()
        return object.__new__(tp) 

    def __init__(self, value, *args):
        # Option(Full) -> Full
        self.x = value.get_or("") if isinstance(value, Full) else value

    def map(self, callback):
        return Full(callback(self.x))

    def filter(self, callback):
        return self if callback(self.x) else Empty()

    def get_or(self, default):
        return self.x

    def get_or_call(self, callback, *args, **kwargs):
        return self.x

    def or_else(self, default):
        return self

    def or_call(self, callback, *args, **kwargs):
        return self

    def __str__(self):
        return "Full(%s)" % self.x

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, Full):
            return False
        return eq(self.x, other.x)


class Empty(Option):
    """Represents empty option (without value)"""

    __object = None
    empty = True

    def __new__(tp, *args, **kwargs):
        if Empty.__object is None:
            Empty.__object = object.__new__(tp)
        return Empty.__object

    def map(self, callback):
        return Empty()

    def filter(self, callback):
        return Empty()

    def get_or(self, default):
        return default

    def get_or_call(self, callback, *args, **kwargs):
        return callback(*args, **kwargs)

    def or_else(self, default):
        return Option(default)

    def or_call(self, callback, *args, **kwargs):
        return Option(callback(*args, **kwargs))

    def __str__(self):
        return "Empty()"

    __repr__ = __str__

    def __eq__(self, other):
        return isinstance(other, Empty)

def optionable(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return Option(f(*args, **kwargs))
    
    return wrapper
########NEW FILE########
__FILENAME__ = op
from sys import version_info

identity = lambda arg: arg

def _apply(f, args=None, kwargs=None):
    return f(*(args or []), **(kwargs or {}))

apply = apply if version_info[0] == 2 else _apply

def call(f, *args, **kwargs):
    return f(*args, **kwargs)

def flip(f):
    """Return function that will apply arguments in reverse order"""

    # Original function is saved in special attribute
    # in order to optimize operation of "duble flipping",
    # so flip(flip(A)) is A
    # Do not use this approach for underscore callable, 
    # see https://github.com/kachayev/fn.py/issues/23
    flipper = getattr(f, "__flipback__", None)
    if flipper is not None:
        return flipper

    def _flipper(a, b): 
        return f(b, a)
    
    setattr(_flipper, "__flipback__", f)
    return _flipper

def curry(f, arg, *rest):
    return curry(f(arg), *rest) if rest else f(arg)

from .func import F
from .uniform import * 
from itertools import starmap

def zipwith(f): 
    'zipwith(f)(seq1, seq2, ..) -> [f(seq1[0], seq2[0], ..), f(seq1[1], seq2[1], ..), ...]'
    return F(starmap, f) << zip

def foldl(f, init=None):
    """Return function to fold iterator to scala value 
    using passed function as reducer.

    Usage:
    >>> print foldl(_ + _)([0,1,2,3,4])
    10
    >>> print foldl(_ * _, 1)([1,2,3])
    6
    """
    def fold(it): 
        args = [f, it]
        if init is not None: args.append(init)
        return reduce(*args)

    return fold

def foldr(f, init=None):
    """Return function to fold iterator to scala value using 
    passed function as reducer in reverse order (consume values 
    from iterator from right-to-left).

    Usage:
    >>> print foldr(call, 10)([lambda s: s**2, lambda k: k+10])
    400
    """
    def fold(it): 
        args = [flip(f), reversed(it)]
        if init is not None: args.append(init)
        return reduce(*args)

    return fold

def unfold(f):
    """Return function to unfold value into stream using 
    passed function as values producer. Passed function should 
    accept current cursor and should return: 
      * tuple of two elements (value, cursor), value will be added 
        to output, cursor will be used for next function call 
      * None in order to stop producing sequence 

    Usage:
    >>> doubler = unfold(lambda x: (x*2, x*2))
    >>> list(islice(doubler(10), 0, 10))
    [20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240]
    """
    def _unfolder(start):
        value, curr = None, start
        while 1:
            step = f(curr)
            if step is None: break
            value, curr = step
            yield value
    return _unfolder

########NEW FILE########
__FILENAME__ = recur
"""Provides decorator to deal with tail calls in recursive function."""

class tco(object):
    """Provides a trampoline for functions that need one.

    Such function should return one of:
     * (False, result) - will exit from loop and return result to caller
     * (True, args) or (True, args, kwargs) - will repeat loop with the same
                                              function and other arguments
     * (func, args) or (func, kwargs) - will repeat loop with new callable
                                        and new arguments 

    Usage example:

    @recur.tco
    def accumulate(origin, f=operator.add, acc=0):
        n = next(origin, None)
        if n is None: return False, acc
        return True, (origin, f, f(acc, n))

    Idea was described on python mailing list:
    http://mail.python.org/pipermail/python-ideas/2009-May/004486.html    
    """

    __slots__ = "func", 

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        action = self
        while True:
            result = action.func(*args, **kwargs)
            # return final result
            if not result[0]: return result[1]

            # next loop with other arguments
            act, args = result[:2]
            # it's possible to given other function to run
            # XXX: do I need to raise exception if it's 
            # impossible to use such function in tail calls loop?
            if callable(act): action = act
            kwargs = result[2] if len(result) > 2 else {}

########NEW FILE########
__FILENAME__ = stream
from sys import version_info

if version_info[0] == 2:
    from sys import maxint
else:
    from sys import maxsize as maxint

from itertools import chain
from .iters import map, range

class Stream(object):

    __slots__ = ("_last", "_collection", "_origin")

    class _StreamIterator(object):
        
        __slots__ = ("_stream", "_position")

        def __init__(self, stream):
            self._stream = stream
            self._position = -1 # not started yet

        def __next__(self):
            # check if elements are available for next position
            # return next element or raise StopIteration
            self._position += 1
            if (len(self._stream._collection) > self._position or 
                self._stream._fill_to(self._position)):
                return self._stream._collection[self._position]

            raise StopIteration()

        if version_info[0] == 2:
            next = __next__

    def __init__(self, *origin):
        self._collection = []
        self._last = -1 # not started yet
        self._origin = iter(origin) if origin else []

    def __lshift__(self, rvalue):
        iterator = rvalue() if callable(rvalue) else rvalue
        self._origin = chain(self._origin, iterator)
        return self

    def cursor(self):
        """Return position of next evaluated element"""
        return self._last + 1

    def _fill_to(self, index):
        if self._last >= index:
            return True

        while self._last < index:
            try:
                n = next(self._origin)
            except StopIteration:
                return False

            self._last += 1
            self._collection.append(n)

        return True

    def __iter__(self):
        return self._StreamIterator(self)

    def __getitem__(self, index):
        if isinstance(index, int):
            # todo: i'm not sure what to do with negative indices
            if index < 0: raise TypeError("Invalid argument type")
            self._fill_to(index)
        elif isinstance(index, slice):
            low, high, step = index.indices(maxint)
            if step == 0: raise ValueError("Step must not be 0")
            return self.__class__() << map(self.__getitem__, range(low, high, step or 1))
        else:
            raise TypeError("Invalid argument type")

        return self._collection.__getitem__(index)

########NEW FILE########
__FILENAME__ = underscore
import re
import operator

from sys import version_info
from itertools import repeat, count

from .op import identity, apply, flip
from .uniform import map, zip
from .func import F

div = operator.div if version_info[0] == 2 else operator.truediv

def fmap(f, format):
    def applyier(self, other):
        fmt = "(%s)" % format.replace("self", self._format)

        if isinstance(other, self.__class__):
            return self.__class__((f, self, other),
                                  fmt.replace("other", other._format),
                                  self._format_args + other._format_args,
                                  self._arity + other._arity)
        else:
            call = F(flip(f), other) << F(self)
            return self.__class__(call, fmt.replace("other", "%r"), (other,), self._arity)
    return applyier

class ArityError(TypeError):
    def __str__(self):
        return "{0!r} expected {1} arguments, got {2}".format(*self.args)

def unary_fmap(f, format):
    def applyier(self):
        fmt = "(%s)" % format.replace("self", self._format)
        return self.__class__(F(self) << f, fmt, self._format_args, self._arity)
    return applyier

class _Callable(object):

    __slots__ = "_callback", "_format", "_format_args", "_arity"
    # Do not use "flipback" approach for underscore callable,
    # see https://github.com/kachayev/fn.py/issues/23
    __flipback__ = None

    def __init__(self, callback=identity, format="_", format_args=tuple(), arity=1):
        self._callback = callback
        self._format = format
        self._format_args = format_args
        self._arity = arity

    def call(self, name, *args, **kwargs):
        """Call method from _ object by given name and arguments"""
        return self.__class__(F(lambda f: apply(f, args, kwargs)) << operator.attrgetter(name) << F(self))

    def __getattr__(self, name):
        return self.__class__(F(operator.attrgetter(name)) << F(self),
                              "getattr(%s, %%r)" % (self._format,),
                              self._format_args + (name,),
                              self._arity)

    def __getitem__(self, k):
        if isinstance(k, self.__class__):
            return self.__class__((operator.getitem, self, k),
                                  "%s[%s]" % (self._format, k._format),
                                  self._format_args + k._format_args,
                                  self._arity + k._arity)
        return self.__class__(F(operator.itemgetter(k)) << F(self),
                              "%s[%%r]" % (self._format,),
                              self._format_args + (k,),
                              self._arity)

    def __str__(self):
        """Build readable representation for function

        (_ < 7): (x1) => (x1 < 7)
        (_ + _*10): (x1, x2) => (x1 + (x2*10))
        """
        # args iterator with produce infinite sequence
        # args -> (x1, x2, x3, ...)
        args = map("".join, zip(repeat("x"), map(str, count(1))))
        l, r = [], self._format
        # replace all "_" signs from left to right side
        while r.count("_"):
            n = next(args)
            r = r.replace("_", n, 1)
            l.append(n)

        r = r % self._format_args
        return "({left}) => {right}".format(left=", ".join(l), right=r)

    def __repr__(self):
        """Return original function notation to ensure that eval(repr(f)) == f"""
        return re.sub(r"x\d", "_", str(self).split("=>")[1].strip())

    def __call__(self, *args):
        if len(args) != self._arity:
            raise ArityError(self, self._arity, len(args))

        if not isinstance(self._callback, tuple):
            return self._callback(*args)

        f, left, right = self._callback
        return f(left(*args[:left._arity]), right(*args[left._arity:]))

    __add__ = fmap(operator.add, "self + other")
    __mul__ = fmap(operator.mul, "self * other")
    __sub__ = fmap(operator.sub, "self - other")
    __mod__ = fmap(operator.mod, "self %% other")
    __pow__ = fmap(operator.pow, "self ** other")

    __and__ = fmap(operator.and_, "self & other")
    __or__ = fmap(operator.or_, "self | other")
    __xor__ = fmap(operator.xor, "self ^ other")

    __div__ = fmap(div, "self / other")
    __divmod__ = fmap(divmod, "self / other")
    __floordiv__ = fmap(operator.floordiv, "self / other")
    __truediv__ = fmap(operator.truediv, "self / other")

    __lshift__ = fmap(operator.lshift, "self << other")
    __rshift__ = fmap(operator.rshift, "self >> other")

    __lt__ = fmap(operator.lt, "self < other")
    __le__ = fmap(operator.le, "self <= other")
    __gt__ = fmap(operator.gt, "self > other")
    __ge__ = fmap(operator.ge, "self >= other")
    __eq__ = fmap(operator.eq, "self == other")
    __ne__ = fmap(operator.ne, "self != other")

    __neg__ = unary_fmap(operator.neg, "-self")
    __pos__ = unary_fmap(operator.pos, "+self")
    __invert__ = unary_fmap(operator.invert, "~self")

    __radd__ = fmap(flip(operator.add), "other + self")
    __rmul__ = fmap(flip(operator.mul), "other * self")
    __rsub__ = fmap(flip(operator.sub), "other - self")
    __rmod__ = fmap(flip(operator.mod), "other %% self")
    __rpow__ = fmap(flip(operator.pow), "other ** self")
    __rdiv__ = fmap(flip(div), "other / self")
    __rdivmod__ = fmap(flip(divmod), "other / self")
    __rtruediv__ = fmap(flip(operator.truediv), "other / self")
    __rfloordiv__ = fmap(flip(operator.floordiv), "other / self")

    __rlshift__ = fmap(flip(operator.lshift), "other << self")
    __rrshift__ = fmap(flip(operator.rshift), "other >> self")

    __rand__ = fmap(flip(operator.and_), "other & self")
    __ror__ = fmap(flip(operator.or_), "other | self")
    __rxor__ = fmap(flip(operator.xor), "other ^ self")

shortcut = _Callable()

########NEW FILE########
__FILENAME__ = uniform
from sys import version_info

# Syntax sugar to deal with Python 2/Python 3 
# differences: this one will return generator
# even in Python 2.*
if version_info[0] == 2:
    from itertools import izip as zip, imap as map, ifilter as filter

filter = filter
map = map
zip = zip

if version_info[0] == 3:
    from functools import reduce

reduce = reduce 
range = xrange if version_info[0] == 2 else  range

if version_info[0] == 2:
    from itertools import ifilterfalse as filterfalse
    from itertools import izip_longest as zip_longest
else:
    from itertools import filterfalse
    from itertools import zip_longest

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python

"""Tests for Fn.py library"""

import sys
import unittest
import operator
import itertools

from fn import op, _, F, Stream, iters, underscore, monad, recur
from fn.uniform import reduce
from fn.immutable import SkewHeap, PairingHeap, LinkedList, Stack, Queue, Vector, Deque

class InstanceChecker(object):
    if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
        def assertIsInstance(self, inst, cls):
            self.assertTrue(isinstance(inst, cls))

class OperatorTestCase(unittest.TestCase):

    def test_currying(self):
        def add(first):
            def add(second):
                return first + second
            return add

        self.assertEqual(1, op.curry(add, 0, 1))

    def test_apply(self):
        self.assertEqual(10, op.apply(operator.add, [2,8]))

    def test_flip(self):
        self.assertEqual(10, op.flip(operator.sub)(2, 12))
        self.assertEqual(-10, op.flip(op.flip(operator.sub))(2, 12))
        # flipping of flipped function should use optimization
        self.assertTrue(operator.sub is op.flip(op.flip(operator.sub)))

    def test_flip_with_shortcut(self):
        self.assertEqual(10, op.flip(_ - _)(2, 12))

    def test_zipwith(self):
        zipper = op.zipwith(operator.add)
        self.assertEqual([10,11,12], list(zipper([0,1,2], itertools.repeat(10))))

        zipper = op.zipwith(_ + _)
        self.assertEqual([10,11,12], list(zipper([0,1,2], itertools.repeat(10))))

        zipper = F() << list << op.zipwith(_ + _)
        self.assertEqual([10,11,12], zipper([0,1,2], itertools.repeat(10)))

    def test_foldl(self):
        self.assertEqual(10, op.foldl(operator.add)([0,1,2,3,4]))
        self.assertEqual(20, op.foldl(operator.add, 10)([0,1,2,3,4]))
        self.assertEqual(20, op.foldl(operator.add, 10)(iters.range(5)))
        self.assertEqual(10, op.foldl(_ + _)(range(5)))

    def test_foldr(self):
        summer = op.foldr(operator.add)
        self.assertEqual(10, op.foldr(operator.add)([0,1,2,3,4]))
        self.assertEqual(20, op.foldr(operator.add, 10)([0,1,2,3,4]))
        self.assertEqual(20, op.foldr(operator.add, 10)(iters.range(5)))
        # specific case for right-side folding
        self.assertEqual(100, 
                         op.foldr(op.call, 0)([lambda s: s**2, lambda k: k+10]))

    def test_unfold_infinite(self):
        doubler = op.unfold(lambda x: (x*2, x*2))
        self.assertEqual(20, next(doubler(10)))
        self.assertEqual([20, 40, 80, 160, 320], list(iters.take(5, doubler(10))))

    def test_unfold_finite(self):
        countdown = op.unfold(lambda x: (x-1, x-2) if x > 1 else None)
        self.assertEqual([9,7,5,3,1], list(countdown(10)))

class UnderscoreTestCase(unittest.TestCase):

    def test_identity_default(self):
        self.assertEqual(10, _(10))

    def test_arithmetic(self):
        # operator +
        self.assertEqual(7, (_ + 2)(5))
        self.assertEqual([10,11,12], list(map(_ + 10, [0,1,2])))
        # operator -
        self.assertEqual(3, (_ - 2)(5))
        self.assertEqual(13, (_ - 2 + 10)(5))
        self.assertEqual([0,1,2], list(map(_ - 10, [10,11,12])))
        # operator * 
        self.assertEqual(10, (_ * 2)(5))
        self.assertEqual(50, (_ * 2 + 40)(5))
        self.assertEqual([0,10,20], list(map(_ * 10, [0,1,2])))
        # operator /
        self.assertEqual(5, (_ / 2)(10))
        self.assertEqual(6, (_ / 2 + 1)(10))
        self.assertEqual([1,2,3], list(map(_ / 10, [10,20,30])))
        # operator **
        self.assertEqual(100, (_ ** 2)(10))
        # operator %
        self.assertEqual(1, (_ % 2)(11))
        # operator << 
        self.assertEqual(32, (_ << 2)(8))
        # operator >> 
        self.assertEqual(2, (_ >> 2)(8))
        # operator (-a)
        self.assertEqual(10,  (-_)(-10))
        self.assertEqual(-10, (-_)(10))
        # operator (+a)
        self.assertEqual(10,  (+_)(10))
        self.assertEqual(-10, (+_)(-10))
        # operator (~a)
        self.assertEqual(-11, (~_)(10))

    def test_arithmetic_multiple(self):
        self.assertEqual(10, (_ + _)(5, 5))
        self.assertEqual(0, (_ - _)(5, 5))
        self.assertEqual(25, (_ * _)(5, 5))
        self.assertEqual(1, (_ / _)(5, 5))

    def test_arithmetic_swap(self):
        # operator +
        self.assertEqual(7, (2 + _)(5))
        self.assertEqual([10,11,12], list(map(10 + _, [0,1,2])))
        # operator -
        self.assertEqual(3, (8 - _)(5))
        self.assertEqual(13, (8 - _ + 10)(5))
        self.assertEqual([10,9,8], list(map(10 - _, [0,1,2])))
        # operator * 
        self.assertEqual(10, (2 * _)(5))
        self.assertEqual(50, (2 * _ + 40)(5))
        self.assertEqual([0,10,20], list(map(10 * _, [0,1,2])))
        # operator /
        self.assertEqual(5, (10 / _)(2))
        self.assertEqual(6, (10 / _ + 1)(2))
        self.assertEqual([10,5,2], list(map(100 / _, [10,20,50])))
        # operator **
        self.assertEqual(100, (10**_)(2))
        # operator %
        self.assertEqual(1, (11 % _)(2))
        # operator << 
        self.assertEqual(32, (8 << _)(2))
        # operator >> 
        self.assertEqual(2, (8 >> _)(2))

    def test_bitwise(self):
        # and
        self.assertTrue( (_ & 1)(1))
        self.assertFalse((_ & 1)(0))
        self.assertFalse((_ & 0)(1))
        self.assertFalse((_ & 0)(0))
        # or 
        self.assertTrue( (_ | 1)(1))
        self.assertTrue( (_ | 1)(0))
        self.assertTrue( (_ | 0)(1))
        self.assertFalse((_ | 0)(0))
        # xor
        self.assertTrue( (_ ^ 1)(0))
        self.assertTrue( (_ ^ 0)(1))
        self.assertFalse((_ ^ 1)(1))
        self.assertFalse((_ ^ 0)(0))

    def test_bitwise_swap(self):
        # and
        self.assertTrue( (1 & _)(1))
        self.assertFalse((1 & _)(0))
        self.assertFalse((0 & _)(1))
        self.assertFalse((0 & _)(0))
        # or 
        self.assertTrue( (1 | _)(1))
        self.assertTrue( (1 | _)(0))
        self.assertTrue( (0 | _)(1))
        self.assertFalse((0 | _)(0))
        # xor
        self.assertTrue( (1 ^ _)(0))
        self.assertTrue( (0 ^ _)(1))
        self.assertFalse((1 ^ _)(1))
        self.assertFalse((0 ^ _)(0))

    def test_getattr(self):
        class GetattrTest(object):
            def __init__(self):
                self.doc = "TestCase"

        self.assertEqual("TestCase", (_.doc)(GetattrTest()))
        self.assertEqual("TestCaseTestCase", (_.doc * 2)(GetattrTest()))
        self.assertEqual("TestCaseTestCase", (_.doc + _.doc)(GetattrTest(), GetattrTest()))

    def test_call_method(self):
        self.assertEqual(["test", "case"], (_.call("split"))("test case"))
        self.assertEqual("str", _.__name__(str))

    def test_call_method_args(self):
        self.assertEqual(["test", "case"], (_.call("split", "-"))("test-case"))
        self.assertEqual(["test-case"], (_.call("split", "-", 0))("test-case"))

    def test_call_method_kwargs(self):
        test_dict = {'num': 23}
        _.call("update", num = 42)(test_dict)
        self.assertEqual({'num': 42}, (test_dict))

    def test_comparator(self):
        self.assertTrue((_ < 7)(1))
        self.assertFalse((_ < 7)(10))
        self.assertTrue((_ > 20)(25))
        self.assertFalse((_ > 20)(0))
        self.assertTrue((_ <= 7)(6))
        self.assertTrue((_ <= 7)(7))
        self.assertFalse((_ <= 7)(8))
        self.assertTrue((_ >= 7)(8))
        self.assertTrue((_ >= 7)(7))
        self.assertFalse((_ >= 7)(6))
        self.assertTrue((_ == 10)(10))
        self.assertFalse((_ == 10)(9))

    def test_none(self):
        self.assertTrue((_ == None)(None))

        class pushlist(list):
            def __lshift__(self, item):
                self.append(item)
                return self

        self.assertEqual([None], (_ << None)(pushlist()))

    def test_comparator_multiple(self):
        self.assertTrue((_ < _)(1, 2))
        self.assertFalse((_ < _)(2, 1))
        self.assertTrue((_ > _)(25, 20))
        self.assertFalse((_ > _)(20, 25))
        self.assertTrue((_ <= _)(6, 7))
        self.assertTrue((_ <= _)(7, 7))
        self.assertFalse((_ <= _)(8, 7))
        self.assertTrue((_ >= _)(8, 7))
        self.assertTrue((_ >= _)(7, 7))
        self.assertFalse((_ >= _)(6, 7))
        self.assertTrue((_ == _)(10, 10))
        self.assertFalse((_ == _)(9, 10))

    def test_comparator_filter(self):
        self.assertEqual([0,1,2], list(filter(_ < 5, [0,1,2,10,11,12])))

    def test_slicing(self):
        self.assertEqual(0,       (_[0])(list(range(10))))
        self.assertEqual(9,       (_[-1])(list(range(10))))
        self.assertEqual([3,4,5], (_[3:])(list(range(6))))
        self.assertEqual([0,1,2], (_[:3])(list(range(10))))
        self.assertEqual([1,2,3], (_[1:4])(list(range(10))))
        self.assertEqual([0,2,4], (_[0:6:2])(list(range(10))))

    def test_slicing_multiple(self):
        self.assertEqual(0, (_[_])(range(10), 0))
        self.assertEqual(8, (_[_ * (-1)])(range(10), 2))

    def test_arity_error(self):
        self.assertRaises(underscore.ArityError, _, 1, 2)
        self.assertRaises(underscore.ArityError, _ + _, 1)
        # can be catched as TypeError
        self.assertRaises(TypeError, _, 1, 2)
        self.assertRaises(TypeError, _ + _, 1)

    def test_more_than_2_operations(self):
        self.assertEqual(12, (_ * 2 + 10)(1))
        self.assertEqual(6,  (_ + _ + _)(1,2,3))
        self.assertEqual(10, (_ + _ + _ + _)(1,2,3,4))
        self.assertEqual(7,  (_ + _ * _)(1,2,3))

    def test_string_converting(self):
        self.assertEqual("(x1) => x1", str(_))

        self.assertEqual("(x1) => (x1 + 2)",  str(_ + 2))
        self.assertEqual("(x1) => (x1 - 2)",  str(_ - 2))
        self.assertEqual("(x1) => (x1 * 2)",  str(_ * 2))
        self.assertEqual("(x1) => (x1 / 2)",  str(_ / 2))
        self.assertEqual("(x1) => (x1 % 2)",  str(_ % 2))
        self.assertEqual("(x1) => (x1 ** 2)", str(_ ** 2))

        self.assertEqual("(x1) => (x1 & 2)", str(_ & 2))
        self.assertEqual("(x1) => (x1 | 2)", str(_ | 2))
        self.assertEqual("(x1) => (x1 ^ 2)", str(_ ^ 2))

        self.assertEqual("(x1) => (x1 >> 2)", str(_ >> 2))
        self.assertEqual("(x1) => (x1 << 2)", str(_ << 2))

        self.assertEqual("(x1) => (x1 < 2)",  str(_ < 2))
        self.assertEqual("(x1) => (x1 > 2)",  str(_ > 2))
        self.assertEqual("(x1) => (x1 <= 2)", str(_ <= 2))
        self.assertEqual("(x1) => (x1 >= 2)", str(_ >= 2))
        self.assertEqual("(x1) => (x1 == 2)", str(_ == 2))
        self.assertEqual("(x1) => (x1 != 2)", str(_ != 2))

    def test_rigthside_string_converting(self):
        self.assertEqual("(x1) => (2 + x1)",  str(2 + _))
        self.assertEqual("(x1) => (2 - x1)",  str(2 - _))
        self.assertEqual("(x1) => (2 * x1)",  str(2 * _))
        self.assertEqual("(x1) => (2 / x1)",  str(2 / _))
        self.assertEqual("(x1) => (2 % x1)",  str(2 % _))
        self.assertEqual("(x1) => (2 ** x1)", str(2 ** _))

        self.assertEqual("(x1) => (2 & x1)", str(2 & _))
        self.assertEqual("(x1) => (2 | x1)", str(2 | _))
        self.assertEqual("(x1) => (2 ^ x1)", str(2 ^ _))

        self.assertEqual("(x1) => (2 >> x1)", str(2 >> _))
        self.assertEqual("(x1) => (2 << x1)", str(2 << _))

    def test_unary_string_converting(self):
        self.assertEqual("(x1) => (+x1)", str(+_))
        self.assertEqual("(x1) => (-x1)", str(-_))
        self.assertEqual("(x1) => (~x1)", str(~_))

    def test_multiple_string_converting(self):
        self.assertEqual("(x1, x2) => (x1 + x2)", str(_ + _))
        self.assertEqual("(x1, x2) => (x1 * x2)", str(_ * _))
        self.assertEqual("(x1, x2) => (x1 - x2)", str(_ - _))
        self.assertEqual("(x1, x2) => (x1 / x2)", str(_ / _))
        self.assertEqual("(x1, x2) => (x1 % x2)", str(_ % _))
        self.assertEqual("(x1, x2) => (x1 ** x2)", str(_ ** _))

        self.assertEqual("(x1, x2) => (x1 & x2)", str(_ & _))
        self.assertEqual("(x1, x2) => (x1 | x2)", str(_ | _))
        self.assertEqual("(x1, x2) => (x1 ^ x2)", str(_ ^ _))

        self.assertEqual("(x1, x2) => (x1 >> x2)", str(_ >> _))
        self.assertEqual("(x1, x2) => (x1 << x2)", str(_ << _))

        self.assertEqual("(x1, x2) => (x1 > x2)",  str(_ > _))
        self.assertEqual("(x1, x2) => (x1 < x2)",  str(_ < _))
        self.assertEqual("(x1, x2) => (x1 >= x2)", str(_ >= _))
        self.assertEqual("(x1, x2) => (x1 <= x2)", str(_ <= _))
        self.assertEqual("(x1, x2) => (x1 == x2)", str(_ == _))
        self.assertEqual("(x1, x2) => (x1 != x2)", str(_ != _))

    def test_reverse_string_converting(self):
        self.assertEqual("(x1, x2, x3) => ((x1 + x2) + x3)", str(_ + _ + _))
        self.assertEqual("(x1, x2, x3) => (x1 + (x2 * x3))", str(_ + _ * _))

    def test_multi_underscore_string_converting(self):
        self.assertEqual("(x1) => (x1 + '_')", str(_ + "_"))
        self.assertEqual("(x1, x2) => getattr((x1 + x2), '__and_now__')", str((_ + _).__and_now__))
        self.assertEqual("(x1, x2) => x1['__name__'][x2]", str(_['__name__'][_]))

    def test_repr(self):
        self.assertEqual(_ / 2, eval(repr(_ / 2)))
        self.assertEqual(_ + _, eval(repr(_ + _)))
        self.assertEqual(_ + _ * _, eval(repr(_ + _ * _)))

class CompositionTestCase(unittest.TestCase):

    def test_composition(self):
        def f(x): return x * 2
        def g(x): return x + 10

        self.assertEqual(30, (F(f) << g)(5))

        def z(x): return x * 20
        self.assertEqual(220, (F(f) << F(g) << F(z))(5))

    def test_partial(self):
        # Partial should work if we pass additional arguments to F constructor
        f = F(operator.add, 10) << F(operator.add, 5)
        self.assertEqual(25, f(10))

    def test_underscore(self):
        self.assertEqual([1, 4, 9], list(map(F() << (_ ** 2) << _ + 1, range(3))))    

    def test_pipe_composition(self):
        def f(x): return x * 2
        def g(x): return x + 10

        self.assertEqual(20, (F() >> f >> g)(5))

    def test_pipe_partial(self):
        func = F() >> (iters.filter, _ < 6) >> sum
        self.assertEqual(15, func(iters.range(10)))

class IteratorsTestCase(unittest.TestCase):

    def test_take(self):
        self.assertEqual([0,1], list(iters.take(2, range(10))))
        self.assertEqual([0,1], list(iters.take(10, range(2))))

    def test_drop(self):
        self.assertEqual([3,4], list(iters.drop(3, range(5))))
        self.assertEqual([], list(iters.drop(10, range(2))))

    def test_takelast(self):
        self.assertEqual([8,9], list(iters.takelast(2, range(10))))
        self.assertEqual([0,1], list(iters.takelast(10, range(2))))

    def test_droplast(self):
        self.assertEqual([0,1], list(iters.droplast(3, range(5))))
        self.assertEqual([], list(iters.droplast(10, range(2))))

    def test_consume(self):
        # full consuming, without limitation
        r = iters.range(10)
        self.assertEqual(10, len(list(r)))
        itr = iter(r)
        iters.consume(itr)
        self.assertEqual(0, len(list(itr)))

    def test_consume_limited(self):
        r = iters.range(10)
        self.assertEqual(10, len(list(r)))
        itr = iter(r)
        iters.consume(itr, 5)
        self.assertEqual(5, len(list(itr)))

    def test_nth(self):
        self.assertEqual(1, iters.nth(range(5), 1))
        self.assertEqual(None, iters.nth(range(5), 10))
        self.assertEqual("X", iters.nth(range(5), 10, "X"))

    def test_head(self):
        self.assertEqual(0, iters.head([0,1,2]))
        self.assertEqual(None, iters.head([]))

        def gen():
            yield 1 
            yield 2
            yield 3 

        self.assertEqual(1, iters.head(gen()))

    def test_first(self):
        self.assertEqual(iters.first, iters.head)  # Check if same object

    def test_tail(self):
        self.assertEqual([1,2], list(iters.tail([0,1,2])))
        self.assertEqual([], list(iters.tail([])))

        def gen():
            yield 1 
            yield 2
            yield 3 

        self.assertEqual([2,3], list(iters.tail(gen())))

    def test_rest(self):
        self.assertEqual(iters.rest, iters.tail)  # Check if same object

    def test_second(self):
        self.assertEqual(2, iters.second([1, 2, 3]))
        self.assertEqual(None, iters.second([]))

        def gen():
            yield 10
            yield 20
            yield 30

        self.assertEqual(20, iters.second(gen()))

    def test_ffirst(self):
        self.assertEqual(1, iters.ffirst([[1, 2], [3, 4]]))
        self.assertEqual(None, iters.ffirst([[], [10, 20]]))

        def gen():
            yield (x * 10 for x in (10, 20, 30,))

        self.assertEqual(100, iters.ffirst(gen()))

    def test_compact(self):
        self.assertEqual([True, 1, 0.1, "non-empty", [""], (0,), {"a": 1}],
                         list(iters.compact([None, False, True, 0, 1, 0.0, 0.1,
                                             "", "non-empty", [], [""],
                                             (), (0,), {}, {"a": 1}])))

    def test_reject(self):
        self.assertEqual([1, 3, 5, 7, 9],
                         list(iters.reject(_ % 2 == 0, range(1, 11))))
        self.assertEqual([None, False, 0, 0.0, "", [], (), {}],
                         list(iters.reject(None, [None, False, True, 0, 1,
                                                  0.0, 0.1, "", "non-empty",
                                                  [], [""], (), (0,),
                                                  {}, {"a": 1}])))

    def test_iterate(self):
        it = iters.iterate(lambda x: x * x, 2)
        self.assertEqual(2, next(it))  # 2
        self.assertEqual(4, next(it))  # 2 * 2
        self.assertEqual(16, next(it))  # 4 * 4
        self.assertEqual(256, next(it))  # 16 * 16

    def test_padnone(self):
        it = iters.padnone([10,11])
        self.assertEqual(10, next(it))
        self.assertEqual(11, next(it))
        self.assertEqual(None, next(it))
        self.assertEqual(None, next(it))

    def test_ncycles(self):
        it = iters.ncycles([10,11], 2)
        self.assertEqual(10, next(it))
        self.assertEqual(11, next(it))
        self.assertEqual(10, next(it))
        self.assertEqual(11, next(it))
        self.assertRaises(StopIteration, next, it)

    def test_repeatfunc(self):
        def f():
            return "test"

        # unlimited count
        it = iters.repeatfunc(f)
        self.assertEqual("test", next(it))
        self.assertEqual("test", next(it))
        self.assertEqual("test", next(it))

        # limited
        it = iters.repeatfunc(f, 2)
        self.assertEqual("test", next(it))
        self.assertEqual("test", next(it))
        self.assertRaises(StopIteration, next, it)

    def test_grouper(self):
        # without fill value (default should be None)
        a, b, c = iters.grouper(3, "ABCDEFG")
        self.assertEqual(["A","B","C"], list(a))
        self.assertEqual(["D","E","F"], list(b))
        self.assertEqual(["G",None,None], list(c))

        # with fill value
        a, b, c = iters.grouper(3, "ABCDEFG", "x")
        self.assertEqual(["A","B","C"], list(a))
        self.assertEqual(["D","E","F"], list(b))
        self.assertEqual(["G","x","x"], list(c))

    def test_group_by(self):
        # verify grouping logic
        grouped = iters.group_by(len, ['1', '12', 'a', '123', 'ab'])
        self.assertEqual({1: ['1', 'a'], 2: ['12', 'ab'], 3: ['123']}, grouped)

        # verify it works with any iterable - not only lists
        def gen():
            yield '1'
            yield '12'

        grouped = iters.group_by(len, gen())
        self.assertEqual({1: ['1'], 2: ['12']}, grouped)

    def test_roundrobin(self):
        r = iters.roundrobin('ABC', 'D', 'EF')
        self.assertEqual(["A","D","E","B","F","C"], list(r))

    def test_partition(self):
        def is_odd(x):
            return x % 2 == 1

        before, after = iters.partition(is_odd, iters.range(5))
        self.assertEqual([0,2,4], list(before))
        self.assertEqual([1,3], list(after))

    def test_splitat(self):
        before, after = iters.splitat(2, iters.range(5))
        self.assertEqual([0,1], list(before))
        self.assertEqual([2,3,4], list(after))

    def test_splitby(self):
        def is_even(x):
            return x % 2 == 0

        before, after = iters.splitby(is_even, iters.range(5))
        self.assertEqual([0], list(before))
        self.assertEqual([1, 2,3,4], list(after))

    def test_powerset(self):
        ps = iters.powerset([1,2])
        self.assertEqual([tuple(),(1,),(2,),(1,2)], list(ps))

    def test_pairwise(self):
        ps = iters.pairwise([1,2,3,4])
        self.assertEqual([(1,2),(2,3),(3,4)], list(ps))

    def test_iter_except(self):
        d = ["a", "b", "c"]
        it = iters.iter_except(d.pop, IndexError)
        self.assertEqual(["c", "b", "a"], list(it))

    def test_flatten(self):
        # flatten nested lists
        self.assertEqual([1,2,3,4], list(iters.flatten([[1,2], [3,4]])))
        self.assertEqual([1,2,3,4,5,6], list(iters.flatten([[1,2], [3, [4,5,6]]])))
        # flatten nested tuples, sets, and frozen sets
        self.assertEqual([1,2,3,4,5,6], list(iters.flatten(((1,2), (3, (4,5,6))))))
        self.assertEqual([1,2,3], list(iters.flatten(set([1, frozenset([2,3])]))))
        # flatten nested generators
        generators = ((num + 1 for num in range(0, n)) for n in range(1, 4))
        self.assertEqual([1,1,2,1,2,3], list(iters.flatten(generators)))
        # flat list should return itself
        self.assertEqual([1,2,3], list(iters.flatten([1,2,3])))
        # Don't flatten strings, bytes, or bytearrays
        self.assertEqual([2,"abc",1], list(iters.flatten([2,"abc",1])))
        self.assertEqual([2, b'abc', 1], list(iters.flatten([2, b'abc', 1])))
        self.assertEqual([2, bytearray(b'abc'), 1], 
                         list(iters.flatten([2, bytearray(b'abc'), 1])))

    def test_accumulate(self):
        self.assertEqual([1,3,6,10,15], list(iters.accumulate([1,2,3,4,5])))
        self.assertEqual([1,2,6,24,120], list(iters.accumulate([1,2,3,4,5], operator.mul)))

    def test_filterfalse(self):
        l = iters.filterfalse(lambda x: x > 10, [1,2,3,11,12])
        self.assertEqual([1,2,3], list(l))

class StreamTestCase(unittest.TestCase):

    def test_from_list(self):
        s = Stream() << [1,2,3,4,5]
        self.assertEqual([1,2,3,4,5], list(s))
        self.assertEqual(2, s[1])
        self.assertEqual([1,2], list(s[0:2]))

    def test_from_iterator(self):
        s = Stream() << range(6) << [6,7]
        self.assertEqual([0,1,2,3,4,5,6,7], list(s))

    def test_from_generator(self):
        def gen():
            yield 1
            yield 2
            yield 3
        
        s = Stream() << gen << (4,5)
        assert list(s) == [1,2,3,4,5]

    def test_lazy_slicing(self):
        s = Stream() << iters.range(10)
        self.assertEqual(s.cursor(), 0)

        s_slice = s[:5]
        self.assertEqual(s.cursor(), 0)
        self.assertEqual(len(list(s_slice)), 5)

    def test_lazy_slicing_recursive(self):
        s = Stream() << iters.range(10)
        sf = s[1:3][0:2]

        self.assertEqual(s.cursor(), 0)
        self.assertEqual(len(list(sf)), 2)

    def test_fib_infinite_stream(self):
        from operator import add 

        f = Stream()
        fib = f << [0, 1] << iters.map(add, f, iters.drop(1, f))

        self.assertEqual([0,1,1,2,3,5,8,13,21,34], list(iters.take(10, fib)))
        self.assertEqual(6765, fib[20])
        self.assertEqual([832040,1346269,2178309,3524578,5702887], list(fib[30:35]))
        # 35 elements should be already evaluated
        self.assertEqual(fib.cursor(), 35)

    def test_origin_param(self):
        self.assertEqual([100], list(Stream(100)))
        self.assertEqual([1,2,3], list(Stream(1, 2, 3)))
        self.assertEqual([1,2,3,10,20,30], list(Stream(1, 2, 3) << [10,20,30]))

    def test_origin_param_string(self):
        self.assertEqual(["stream"], list(Stream("stream")))

class OptionTestCase(unittest.TestCase, InstanceChecker):

    def test_create_option(self):
        self.assertIsInstance(monad.Option("A"), monad.Full)
        self.assertIsInstance(monad.Option(10), monad.Full)
        self.assertIsInstance(monad.Option(10, lambda x: x > 7), monad.Full)
        self.assertIsInstance(monad.Option(None), monad.Empty)
        self.assertIsInstance(monad.Option(False), monad.Full)
        self.assertIsInstance(monad.Option(0), monad.Full)
        self.assertIsInstance(monad.Option(False, checker=bool), monad.Empty)
        self.assertIsInstance(monad.Option(0, checker=bool), monad.Empty)
        self.assertIsInstance(monad.Option(10, lambda x: x > 70), monad.Empty)

    def test_map_filter(self):
        class Request(dict):
            def parameter(self, name):
                return monad.Option(self.get(name, None))

        r = Request(testing="Fixed", empty="   ")

        # full chain
        self.assertEqual("FIXED", r.parameter("testing")
                                   .map(operator.methodcaller("strip"))
                                   .filter(len)
                                   .map(operator.methodcaller("upper"))
                                   .get_or(""))

        # breaks on filter
        self.assertEqual("", r.parameter("empty")
                              .map(operator.methodcaller("strip"))
                              .filter(len)
                              .map(operator.methodcaller("upper"))
                              .get_or(""))

        # breaks on parameter
        self.assertEqual("", r.parameter("missed")
                              .map(operator.methodcaller("strip"))
                              .filter(len)
                              .map(operator.methodcaller("upper"))
                              .get_or(""))

    def test_empty_check(self):
        self.assertTrue(monad.Empty().empty)
        self.assertTrue(monad.Option(None).empty)
        self.assertTrue(monad.Option.from_call(lambda: None).empty)
        self.assertFalse(monad.Option(10).empty)
        self.assertFalse(monad.Full(10).empty)

    def test_lazy_orcall(self):
        def from_mimetype(request):
            # you can return both value or Option
            return request.get("mimetype", None)

        def from_extension(request):
            # you can return both value or Option
            return monad.Option(request.get("url", None))\
                        .map(lambda s: s.split(".")[-1])

        # extract value from extension
        r = dict(url="myfile.png")
        self.assertEqual("PNG", monad.Option(r.get("type", None)) \
                                     .or_call(from_mimetype, r) \
                                     .or_call(from_extension, r) \
                                     .map(operator.methodcaller("upper")) \
                                     .get_or(""))

        # extract value from mimetype
        r = dict(url="myfile.svg", mimetype="png")
        self.assertEqual("PNG", monad.Option(r.get("type", None)) \
                                     .or_call(from_mimetype, r) \
                                     .or_call(from_extension, r) \
                                     .map(operator.methodcaller("upper")) \
                                     .get_or(""))

        # type is set directly
        r = dict(url="myfile.jpeg", mimetype="svg", type="png")
        self.assertEqual("PNG", monad.Option(r.get("type", None)) \
                                     .or_call(from_mimetype, r) \
                                     .or_call(from_extension, r) \
                                     .map(operator.methodcaller("upper")) \
                                     .get_or(""))

    def test_optionable_decorator(self):
        class Request(dict):
            @monad.optionable
            def parameter(self, name):
                return self.get(name, None)

        r = Request(testing="Fixed", empty="   ")

        # full chain
        self.assertEqual("FIXED", r.parameter("testing")
                                   .map(operator.methodcaller("strip"))
                                   .filter(len)
                                   .map(operator.methodcaller("upper"))
                                   .get_or(""))

    def test_stringify(self):
        self.assertEqual("Full(10)", str(monad.Full(10)))
        self.assertEqual("Full(in box!)", str(monad.Full("in box!")))
        self.assertEqual("Empty()", str(monad.Empty()))
        self.assertEqual("Empty()", str(monad.Option(None)))

    def test_option_repr(self):
        self.assertEqual("Full(10)", repr(monad.Full(10)))
        self.assertEqual("Full(in box!)", repr(monad.Full("in box!")))
        self.assertEqual("Empty()", repr(monad.Empty()))
        self.assertEqual("Empty()", repr(monad.Option(None)))

    def test_static_constructor(self):
        self.assertEqual(monad.Empty(),  monad.Option.from_value(None))
        self.assertEqual(monad.Full(10), monad.Option.from_value(10))
        self.assertEqual(monad.Empty(),  monad.Option.from_call(lambda: None))
        self.assertEqual(monad.Full(10), monad.Option.from_call(operator.add, 8, 2))
        self.assertEqual(monad.Empty(), 
                         monad.Option.from_call(lambda d, k: d[k], 
                                                {"a":1}, "b", exc=KeyError))

    def test_flatten_operation(self):
        self.assertEqual(monad.Empty(), monad.Empty(monad.Empty()))
        self.assertEqual(monad.Empty(), monad.Empty(monad.Full(10)))
        self.assertEqual(monad.Empty(), monad.Full(monad.Empty()))
        self.assertEqual("Full(20)", str(monad.Full(monad.Full(20))))

class TrampolineTestCase(unittest.TestCase):

    def test_tco_decorator(self):

        def recur_accumulate(origin, f=operator.add, acc=0):
            n = next(origin, None)
            if n is None: return acc
            return recur_accumulate(origin, f, f(acc, n))

        # this works normally
        self.assertEqual(10, recur_accumulate(iter(range(5))))

        limit = sys.getrecursionlimit() * 10
        # such count of recursive calls should fail on CPython,
        # for PyPy we skip this test cause on PyPy the limit is
        # approximative and checked at a lower level
        if not hasattr(sys, 'pypy_version_info'):
            self.assertRaises(RuntimeError, recur_accumulate, iter(range(limit)))

        # with recur decorator it should run without problems
        @recur.tco
        def tco_accumulate(origin, f=operator.add, acc=0):
            n = next(origin, None)
            if n is None: return False, acc
            return True, (origin, f, f(acc, n))

        self.assertEqual(sum(range(limit)), tco_accumulate(iter(range(limit))))

    def test_tco_different_functions(self):

        @recur.tco
        def recur_inc2(curr, acc=0):
            if curr == 0: return False, acc
            return recur_dec, (curr-1, acc+2)

        @recur.tco
        def recur_dec(curr, acc=0):
            if curr == 0: return False, acc
            return recur_inc2, (curr-1, acc-1)

        self.assertEqual(5000, recur_inc2(10000))

class UnionBasedHeapsTestCase(unittest.TestCase):

    def _heap_basic_operations(self, cls):
        # Create new heap with 3 elements
        s1 = cls(10)
        s2 = s1.insert(30)
        s3 = s2.insert(20)

        # Extract elements one-by-one
        el1, sx1 = s3.extract()
        el2, sx2 = sx1.extract()
        el3, sx3 = sx2.extract()

        # Check elements ordering
        self.assertEqual(10, el1)
        self.assertEqual(20, el2)
        self.assertEqual(30, el3)

        # Check that previous heap are persistent
        el22, _ = sx1.extract()
        self.assertEqual(20, el22)

    def _heap_iterator(self, cls):
        # Create new heap with 5 elements
        h = cls(10)
        h = h.insert(30)
        h = h.insert(20)
        h = h.insert(5)
        h = h.insert(100)

        # Convert to list using iterator
        self.assertEqual([5, 10, 20, 30, 100], list(h))

    def _heap_custom_compare(self, cls):
        h = cls(cmp=lambda a,b: len(a) - len(b))
        h = h.insert("give")
        h = h.insert("few words")
        h = h.insert("about")
        h = h.insert("union heaps")
        h = h.insert("implementation")

        # Convert to list using iterator
        self.assertEqual(["give",
                          "about",
                          "few words",
                          "union heaps",
                          "implementation"], list(h))

    def _heap_compare_with_keyfunc(self, cls):
        from operator import itemgetter

        # Create new heap with 5 elements
        h = cls(key=itemgetter(1))
        h = h.insert((10, 10))
        h = h.insert((30, 15))
        h = h.insert((20, 110))
        h = h.insert((40, -10))
        h = h.insert((50, 100))

        # Convert to list using iterator
        self.assertEqual([(40,-10), (10,10), (30,15), (50,100), (20,110)], list(h))

    def test_skew_heap_basic(self):
        self._heap_basic_operations(SkewHeap)

    def test_pairing_heap_basic(self):
        self._heap_basic_operations(PairingHeap)

    def test_skew_heap_iterator(self):
        self._heap_iterator(SkewHeap)

    def test_pairing_heap_iterator(self):
        self._heap_iterator(PairingHeap)

    def test_skew_heap_key_func(self):
        self._heap_compare_with_keyfunc(SkewHeap)

    def test_pairing_heap_key_func(self):
        self._heap_compare_with_keyfunc(PairingHeap)

    def test_skew_heap_cmp_func(self):
        self._heap_custom_compare(SkewHeap)

    def test_pairing_heap_cmp_func(self):
        self._heap_custom_compare(PairingHeap)

class LinkedListsTestCase(unittest.TestCase):

    def test_linked_list_basic_operations(self):
        l1 = LinkedList()
        l2 = l1.cons(1)
        l3 = l2.cons(2)
        self.assertEqual(None, l1.head)
        self.assertEqual(1, l2.head)
        self.assertEqual(2, l3.head)
        self.assertEqual(1, l3.tail.head)
        self.assertEqual(None, l3.tail.tail.head)

    def test_linked_list_num_of_elements(self):
        self.assertEqual(0, len(LinkedList()))
        self.assertEqual(3, len(LinkedList().cons(10).cons(20).cons(30)))

    def tests_linked_list_iterator(self):
        self.assertEqual([30, 20, 10], list(LinkedList().cons(10).cons(20).cons(30)))
    
    def test_stack_push_pop_ordering(self):
        s1 = Stack()
        s2 = s1.push(1)
        s3 = s2.push(10)
        s4 = s3.push(100)
        (sv4, s5) = s4.pop()
        (sv3, s6) = s5.pop()
        self.assertEqual(100, sv4)
        self.assertEqual(10, sv3)
        self.assertEqual(100, s4.pop()[0])

    def test_stack_length(self):
        self.assertEqual(0, len(Stack()))
        self.assertEqual(3, len(Stack().push(1).push(2).push(3)))

    def test_stack_is_empty_check(self):
        self.assertTrue(Stack().push(100))
        self.assertFalse(Stack().push(100).is_empty())
        self.assertTrue(Stack().is_empty())

    def test_pop_empty_stack_exception(self):
        self.assertRaises(ValueError, Stack().pop)

    def test_stack_iterator(self):
        self.assertEqual([10, 5, 1], list(Stack().push(1).push(5).push(10)))
        self.assertEqual(6, sum(Stack().push(1).push(2).push(3)))

class BankerQueueTestCase(unittest.TestCase):
    
    def test_queue_basic_operations(self):
        q1 = Queue()
        q2 = q1.enqueue(1)
        q3 = q2.enqueue(10)
        q4 = q3.enqueue(100)
        self.assertEqual(1, q4.dequeue()[0])
        self.assertEqual(1, q3.dequeue()[0])
        self.assertEqual(1, q2.dequeue()[0])
        v1, q5 = q4.dequeue()
        v2, q6 = q5.dequeue()
        v3, q7 = q6.dequeue()
        self.assertEqual(1, v1)
        self.assertEqual(10, v2)
        self.assertEqual(100, v3)
        self.assertEqual(0, len(q7))

    def test_queue_num_of_elements(self):
        self.assertEqual(0, len(Queue()))
        self.assertEqual(3, len(Queue().enqueue(1).enqueue(2).enqueue(3)))

    def test_queue_is_empty(self):
        self.assertTrue(Queue().is_empty())
        self.assertFalse(Queue().enqueue(1).is_empty())
        self.assertTrue(Queue().enqueue(1).dequeue()[1].is_empty())

    def test_dequeue_from_empty(self):
        self.assertRaises(ValueError, Queue().dequeue)

    def test_iterator(self):
        self.assertEqual([], list(Queue()))
        self.assertEqual([1,2,3], list(Queue().enqueue(1).enqueue(2).enqueue(3)))
        self.assertEqual(60, sum(Queue().enqueue(10).enqueue(20).enqueue(30)))

class VectorTestCase(unittest.TestCase):

    def test_cons_operation(self):
        v = Vector()
        self.assertEqual(0, len(v))
        v1 = v.cons(10)
        self.assertEqual(1, len(v1))
        self.assertEqual(0, len(v)) # previous value didn't change
        up = reduce(lambda acc, el: acc.cons(el), range(513), Vector())
        self.assertEqual(513, len(up))

    def test_assoc_get_operations(self):
        v = Vector()
        v1 = v.assoc(0, 10)
        v2 = v1.assoc(1, 20)
        v3 = v2.assoc(2, 30)
        self.assertEqual(10, v3.get(0))
        self.assertEqual(20, v3.get(1))
        self.assertEqual(30, v3.get(2))
        # check persistence
        v4 = v2.assoc(2, 50)
        self.assertEqual(30, v3.get(2))
        self.assertEqual(50, v4.get(2))
        # long vector
        up = reduce(lambda acc, el: acc.assoc(el, el*2), range(1500), Vector())
        self.assertEqual(2800, up.get(1400))
        self.assertEqual(2998, up.get(1499))

    def test_pop_operations(self):
        v = reduce(lambda acc, el: acc.cons(el), range(2000), Vector())
        self.assertEqual(1999, len(v.pop()))
        self.assertEqual(list(range(1999)), list(v.pop()))

    def test_vector_iterator(self):
        v = reduce(lambda acc, el: acc.assoc(el, el+1), range(1500), Vector())
        self.assertEqual(list(range(1, 1501)), list(v))
        self.assertEqual(1125750, sum(v))

    def test_index_error(self):
        v = reduce(lambda acc, el: acc.assoc(el, el+2), range(50), Vector())
        self.assertRaises(IndexError, v.get, -1)
        self.assertRaises(IndexError, v.get, 50)
        self.assertRaises(IndexError, v.get, 52)

    def test_setitem_should_not_be_implemented(self):
        def f():
            v = Vector().cons(20)
            v[0] = 10
        self.assertRaises(NotImplementedError, f)

    def test_subvector_operation(self):
        pass

class FingerTreeDequeTestCase(unittest.TestCase):
    
    def test_deque_basic_operations(self):
        d1 = Deque()
        d2 = d1.push_back(1)
        d3 = d2.push_back(2)
        d4 = d3.push_back(3)
        d5 = d4.push_front(10)
        d6 = d5.push_front(20)
        self.assertEqual(1, d4.head())
        self.assertEqual(3, d4.last())
        self.assertEqual(20, d6.head())
        self.assertEqual(3, d6.last())

    def test_deque_num_of_elements(self):
        pass

    def test_deque_is_empty(self):
        self.assertTrue(Deque().is_empty())
        self.assertFalse(Deque().push_back(1).is_empty())
        self.assertTrue(Deque().push_back(1).tail().is_empty())

    def test_iterator(self):
        self.assertEqual([], list(Deque()))
        self.assertEqual([1,2,3], list(Deque().push_back(1).push_back(2).push_back(3)))
        self.assertEqual(60, sum(Deque().push_back(10).push_front(20).push_back(30)))
        self.assertEqual(sum(range(1,20)), sum(Deque.from_iterable(range(1,20))))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
