__FILENAME__ = btuple_tests
# Based on Python's tuple_tests.py, licensed under the Python License
# Agreement

import sys
import random
import gc
from blist import btuple
from blist.test import unittest
from blist.test import seq_tests

class bTupleTest(seq_tests.CommonTest):
    type2test = btuple

    def test_constructors(self):
        super(bTupleTest, self).test_len()
        # calling built-in types without argument must return empty
        self.assertEqual(tuple(), ())
        t0_3 = (0, 1, 2, 3)
        t0_3_bis = tuple(t0_3)
        self.assert_(t0_3 is t0_3_bis)
        self.assertEqual(tuple([]), ())
        self.assertEqual(tuple([0, 1, 2, 3]), (0, 1, 2, 3))
        self.assertEqual(tuple(''), ())
        self.assertEqual(tuple('spam'), ('s', 'p', 'a', 'm'))

    def test_truth(self):
        super(bTupleTest, self).test_truth()
        self.assert_(not ())
        self.assert_((42, ))

    def test_len(self):
        super(bTupleTest, self).test_len()
        self.assertEqual(len(()), 0)
        self.assertEqual(len((0,)), 1)
        self.assertEqual(len((0, 1, 2)), 3)

    def test_iadd(self):
        super(bTupleTest, self).test_iadd()
        u = (0, 1)
        u2 = u
        u += (2, 3)
        self.assert_(u is not u2)

    def test_imul(self):
        super(bTupleTest, self).test_imul()
        u = (0, 1)
        u2 = u
        u *= 3
        self.assert_(u is not u2)

    def test_tupleresizebug(self):
        # Check that a specific bug in _PyTuple_Resize() is squashed.
        def f():
            for i in range(1000):
                yield i
        self.assertEqual(list(tuple(f())), list(range(1000)))

    def test_hash(self):
        # See SF bug 942952:  Weakness in tuple hash
        # The hash should:
        #      be non-commutative
        #      should spread-out closely spaced values
        #      should not exhibit cancellation in tuples like (x,(x,y))
        #      should be distinct from element hashes:  hash(x)!=hash((x,))
        # This test exercises those cases.
        # For a pure random hash and N=50, the expected number of occupied
        #      buckets when tossing 252,600 balls into 2**32 buckets
        #      is 252,592.6, or about 7.4 expected collisions.  The
        #      standard deviation is 2.73.  On a box with 64-bit hash
        #      codes, no collisions are expected.  Here we accept no
        #      more than 15 collisions.  Any worse and the hash function
        #      is sorely suspect.

        N=50
        base = list(range(N))
        xp = [(i, j) for i in base for j in base]
        inps = base + [(i, j) for i in base for j in xp] + \
                     [(i, j) for i in xp for j in base] + xp + list(zip(base))
        collisions = len(inps) - len(set(map(hash, inps)))
        self.assert_(collisions <= 15)

    def test_repr(self):
        l0 = btuple()
        l2 = btuple((0, 1, 2))
        a0 = self.type2test(l0)
        a2 = self.type2test(l2)

        self.assertEqual(str(a0), repr(l0))
        self.assertEqual(str(a2), repr(l2))
        self.assertEqual(repr(a0), "btuple(())")
        self.assertEqual(repr(a2), "btuple((0, 1, 2))")

    def _not_tracked(self, t):
        if sys.version_info[0] < 3:
            return
        else: # pragma: no cover
            # Nested tuples can take several collections to untrack
            gc.collect()
            gc.collect()
            self.assertFalse(gc.is_tracked(t), t)

    def _tracked(self, t):
        if sys.version_info[0] < 3:
            return
        else: # pragma: no cover
            self.assertTrue(gc.is_tracked(t), t)
            gc.collect()
            gc.collect()
            self.assertTrue(gc.is_tracked(t), t)

    def test_track_literals(self):
        # Test GC-optimization of tuple literals
        x, y, z = 1.5, "a", []

        self._not_tracked(())
        self._not_tracked((1,))
        self._not_tracked((1, 2))
        self._not_tracked((1, 2, "a"))
        self._not_tracked((1, 2, (None, True, False, ()), int))
        self._not_tracked((object(),))
        self._not_tracked(((1, x), y, (2, 3)))

        # Tuples with mutable elements are always tracked, even if those
        # elements are not tracked right now.
        self._tracked(([],))
        self._tracked(([1],))
        self._tracked(({},))
        self._tracked((set(),))
        self._tracked((x, y, z))

    def check_track_dynamic(self, tp, always_track):
        x, y, z = 1.5, "a", []

        check = self._tracked if always_track else self._not_tracked
        check(tp())
        check(tp([]))
        check(tp(set()))
        check(tp([1, x, y]))
        check(tp(obj for obj in [1, x, y]))
        check(tp(set([1, x, y])))
        check(tp(tuple([obj]) for obj in [1, x, y]))
        check(tuple(tp([obj]) for obj in [1, x, y]))

        self._tracked(tp([z]))
        self._tracked(tp([[x, y]]))
        self._tracked(tp([{x: y}]))
        self._tracked(tp(obj for obj in [x, y, z]))
        self._tracked(tp(tuple([obj]) for obj in [x, y, z]))
        self._tracked(tuple(tp([obj]) for obj in [x, y, z]))

    def test_track_dynamic(self):
        # Test GC-optimization of dynamically constructed tuples.
        self.check_track_dynamic(tuple, False)

    def test_track_subtypes(self):
        # Tuple subtypes must always be tracked
        class MyTuple(tuple):
            pass
        self.check_track_dynamic(MyTuple, True)

########NEW FILE########
__FILENAME__ = list_tests
# This file taken from Python, licensed under the Python License Agreement

from __future__ import print_function
"""
Tests common to list and UserList.UserList
"""

import sys
import os

from blist.test import unittest
from blist.test import test_support
from blist.test import seq_tests

from decimal import Decimal

def CmpToKey(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) == -1
    return K

class CommonTest(seq_tests.CommonTest):

    def test_init(self):
        # Iterable arg is optional
        self.assertEqual(self.type2test([]), self.type2test())

        # Init clears previous values
        a = self.type2test([1, 2, 3])
        a.__init__()
        self.assertEqual(a, self.type2test([]))

        # Init overwrites previous values
        a = self.type2test([1, 2, 3])
        a.__init__([4, 5, 6])
        self.assertEqual(a, self.type2test([4, 5, 6]))

        # Mutables always return a new object
        b = self.type2test(a)
        self.assertNotEqual(id(a), id(b))
        self.assertEqual(a, b)

    def test_repr(self):
        l0 = []
        l2 = [0, 1, 2]
        a0 = self.type2test(l0)
        a2 = self.type2test(l2)

        self.assertEqual(str(a0), 'blist(%s)' % str(l0))
        self.assertEqual(repr(a0), 'blist(%s)' % repr(l0))
        self.assertEqual(repr(a2), 'blist(%s)' % repr(l2))
        self.assertEqual(str(a2),  "blist([0, 1, 2])")
        self.assertEqual(repr(a2), "blist([0, 1, 2])")

        a2.append(a2)
        a2.append(3)
        self.assertEqual(str(a2),  "blist([0, 1, 2, [...], 3])")
        self.assertEqual(repr(a2), "blist([0, 1, 2, [...], 3])")

    def test_print(self):
        d = self.type2test(range(200))
        d.append(d)
        d.extend(range(200,400))
        d.append(d)
        d.append(400)
        try:
            fo = open(test_support.TESTFN, "w")
            fo.write(str(d))
            fo.close()
            fo = open(test_support.TESTFN, "r")
            self.assertEqual(fo.read(), repr(d))
        finally:
            fo.close()
            os.remove(test_support.TESTFN)

    def test_set_subscript(self):
        a = self.type2test(list(range(20)))
        self.assertRaises(ValueError, a.__setitem__, slice(0, 10, 0), [1,2,3])
        self.assertRaises(TypeError, a.__setitem__, slice(0, 10), 1)
        self.assertRaises(ValueError, a.__setitem__, slice(0, 10, 2), [1,2])
        self.assertRaises(TypeError, a.__getitem__, 'x', 1)
        a[slice(2,10,3)] = [1,2,3]
        self.assertEqual(a, self.type2test([0, 1, 1, 3, 4, 2, 6, 7, 3,
                                            9, 10, 11, 12, 13, 14, 15,
                                            16, 17, 18, 19]))

    def test_reversed(self):
        a = self.type2test(list(range(20)))
        r = reversed(a)
        self.assertEqual(list(r), self.type2test(list(range(19, -1, -1))))
        if hasattr(r, '__next__'): # pragma: no cover
            self.assertRaises(StopIteration, r.__next__)
        else: # pragma: no cover
            self.assertRaises(StopIteration, r.next)
        self.assertEqual(list(reversed(self.type2test())),
                         self.type2test())

    def test_setitem(self):
        a = self.type2test([0, 1])
        a[0] = 0
        a[1] = 100
        self.assertEqual(a, self.type2test([0, 100]))
        a[-1] = 200
        self.assertEqual(a, self.type2test([0, 200]))
        a[-2] = 100
        self.assertEqual(a, self.type2test([100, 200]))
        self.assertRaises(IndexError, a.__setitem__, -3, 200)
        self.assertRaises(IndexError, a.__setitem__, 2, 200)

        a = self.type2test([])
        self.assertRaises(IndexError, a.__setitem__, 0, 200)
        self.assertRaises(IndexError, a.__setitem__, -1, 200)
        self.assertRaises(TypeError, a.__setitem__)

        a = self.type2test([0,1,2,3,4])
        a[0] = 1
        a[1] = 2
        a[2] = 3
        self.assertEqual(a, self.type2test([1,2,3,3,4]))
        a[0] = 5
        a[1] = 6
        a[2] = 7
        self.assertEqual(a, self.type2test([5,6,7,3,4]))
        a[-2] = 88
        a[-1] = 99
        self.assertEqual(a, self.type2test([5,6,7,88,99]))
        a[-2] = 8
        a[-1] = 9
        self.assertEqual(a, self.type2test([5,6,7,8,9]))

    def test_delitem(self):
        a = self.type2test([0, 1])
        del a[1]
        self.assertEqual(a, [0])
        del a[0]
        self.assertEqual(a, [])

        a = self.type2test([0, 1])
        del a[-2]
        self.assertEqual(a, [1])
        del a[-1]
        self.assertEqual(a, [])

        a = self.type2test([0, 1])
        self.assertRaises(IndexError, a.__delitem__, -3)
        self.assertRaises(IndexError, a.__delitem__, 2)

        a = self.type2test([])
        self.assertRaises(IndexError, a.__delitem__, 0)

        self.assertRaises(TypeError, a.__delitem__)

    def test_setslice(self):
        l = [0, 1]
        a = self.type2test(l)

        for i in range(-3, 4):
            a[:i] = l[:i]
            self.assertEqual(a, l)
            a2 = a[:]
            a2[:i] = a[:i]
            self.assertEqual(a2, a)
            a[i:] = l[i:]
            self.assertEqual(a, l)
            a2 = a[:]
            a2[i:] = a[i:]
            self.assertEqual(a2, a)
            for j in range(-3, 4):
                a[i:j] = l[i:j]
                self.assertEqual(a, l)
                a2 = a[:]
                a2[i:j] = a[i:j]
                self.assertEqual(a2, a)

        aa2 = a2[:]
        aa2[:0] = [-2, -1]
        self.assertEqual(aa2, [-2, -1, 0, 1])
        aa2[0:] = []
        self.assertEqual(aa2, [])

        a = self.type2test([1, 2, 3, 4, 5])
        a[:-1] = a
        self.assertEqual(a, self.type2test([1, 2, 3, 4, 5, 5]))
        a = self.type2test([1, 2, 3, 4, 5])
        a[1:] = a
        self.assertEqual(a, self.type2test([1, 1, 2, 3, 4, 5]))
        a = self.type2test([1, 2, 3, 4, 5])
        a[1:-1] = a
        self.assertEqual(a, self.type2test([1, 1, 2, 3, 4, 5, 5]))

        a = self.type2test([])
        a[:] = tuple(range(10))
        self.assertEqual(a, self.type2test(list(range(10))))

        if sys.version_info[0] < 3:
            self.assertRaises(TypeError, a.__setslice__, 0, 1, 5)
            self.assertRaises(TypeError, a.__setslice__)

    def test_delslice(self):
        a = self.type2test([0, 1])
        del a[1:2]
        del a[0:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[1:2]
        del a[0:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[-2:-1]
        self.assertEqual(a, self.type2test([1]))

        a = self.type2test([0, 1])
        del a[-2:-1]
        self.assertEqual(a, self.type2test([1]))

        a = self.type2test([0, 1])
        del a[1:]
        del a[:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[1:]
        del a[:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test([0, 1])
        del a[-1:]
        self.assertEqual(a, self.type2test([0]))

        a = self.type2test([0, 1])
        del a[-1:]
        self.assertEqual(a, self.type2test([0]))

        a = self.type2test([0, 1])
        del a[:]
        self.assertEqual(a, self.type2test([]))

    def test_append(self):
        a = self.type2test([])
        a.append(0)
        a.append(1)
        a.append(2)
        self.assertEqual(a, self.type2test([0, 1, 2]))

        self.assertRaises(TypeError, a.append)

    def test_extend(self):
        a1 = self.type2test([0])
        a2 = self.type2test((0, 1))
        a = a1[:]
        a.extend(a2)
        self.assertEqual(a, a1 + a2)

        a.extend(self.type2test([]))
        self.assertEqual(a, a1 + a2)

        a.extend(a)
        self.assertEqual(a, self.type2test([0, 0, 1, 0, 0, 1]))

        a = self.type2test("spam")
        a.extend("eggs")
        self.assertEqual(a, list("spameggs"))

        self.assertRaises(TypeError, a.extend, None)

        self.assertRaises(TypeError, a.extend)

    def test_insert(self):
        a = self.type2test([0, 1, 2])
        a.insert(0, -2)
        a.insert(1, -1)
        a.insert(2, 0)
        self.assertEqual(a, [-2, -1, 0, 0, 1, 2])

        b = a[:]
        b.insert(-2, "foo")
        b.insert(-200, "left")
        b.insert(200, "right")
        self.assertEqual(b, self.type2test(["left",-2,-1,0,0,"foo",1,2,"right"]))

        self.assertRaises(TypeError, a.insert)

    def test_pop(self):
        a = self.type2test([-1, 0, 1])
        a.pop()
        self.assertEqual(a, [-1, 0])
        a.pop(0)
        self.assertEqual(a, [0])
        self.assertRaises(IndexError, a.pop, 5)
        a.pop(0)
        self.assertEqual(a, [])
        self.assertRaises(IndexError, a.pop)
        self.assertRaises(TypeError, a.pop, 42, 42)
        a = self.type2test([0, 10, 20, 30, 40])

    def test_remove(self):
        a = self.type2test([0, 0, 1])
        a.remove(1)
        self.assertEqual(a, [0, 0])
        a.remove(0)
        self.assertEqual(a, [0])
        a.remove(0)
        self.assertEqual(a, [])

        self.assertRaises(ValueError, a.remove, 0)

        self.assertRaises(TypeError, a.remove)

        class BadExc(Exception):
            pass

        class BadCmp:
            def __eq__(self, other):
                if other == 2:
                    raise BadExc()
                return False

        a = self.type2test([0, 1, 2, 3])
        self.assertRaises(BadExc, a.remove, BadCmp())

        class BadCmp2:
            def __eq__(self, other):
                raise BadExc()

        d = self.type2test('abcdefghcij')
        d.remove('c')
        self.assertEqual(d, self.type2test('abdefghcij'))
        d.remove('c')
        self.assertEqual(d, self.type2test('abdefghij'))
        self.assertRaises(ValueError, d.remove, 'c')
        self.assertEqual(d, self.type2test('abdefghij'))

        # Handle comparison errors
        d = self.type2test(['a', 'b', BadCmp2(), 'c'])
        e = self.type2test(d)
        self.assertRaises(BadExc, d.remove, 'c')
        for x, y in zip(d, e):
            # verify that original order and values are retained.
            self.assert_(x is y)

    def test_count(self):
        a = self.type2test([0, 1, 2])*3
        self.assertEqual(a.count(0), 3)
        self.assertEqual(a.count(1), 3)
        self.assertEqual(a.count(3), 0)

        self.assertRaises(TypeError, a.count)

        class BadExc(Exception):
            pass

        class BadCmp:
            def __eq__(self, other):
                if other == 2:
                    raise BadExc()
                return False

        self.assertRaises(BadExc, a.count, BadCmp())

    def test_index(self):
        u = self.type2test([0, 1])
        self.assertEqual(u.index(0), 0)
        self.assertEqual(u.index(1), 1)
        self.assertRaises(ValueError, u.index, 2)

        u = self.type2test([-2, -1, 0, 0, 1, 2])
        self.assertEqual(u.count(0), 2)
        self.assertEqual(u.index(0), 2)
        self.assertEqual(u.index(0, 2), 2)
        self.assertEqual(u.index(-2, -10), 0)
        self.assertEqual(u.index(0, 3), 3)
        self.assertEqual(u.index(0, 3, 4), 3)
        self.assertRaises(ValueError, u.index, 2, 0, -10)

        self.assertRaises(TypeError, u.index)

        class BadExc(Exception):
            pass

        class BadCmp:
            def __eq__(self, other):
                if other == 2:
                    raise BadExc()
                return False

        a = self.type2test([0, 1, 2, 3])
        self.assertRaises(BadExc, a.index, BadCmp())

        a = self.type2test([-2, -1, 0, 0, 1, 2])
        self.assertEqual(a.index(0), 2)
        self.assertEqual(a.index(0, 2), 2)
        self.assertEqual(a.index(0, -4), 2)
        self.assertEqual(a.index(-2, -10), 0)
        self.assertEqual(a.index(0, 3), 3)
        self.assertEqual(a.index(0, -3), 3)
        self.assertEqual(a.index(0, 3, 4), 3)
        self.assertEqual(a.index(0, -3, -2), 3)
        self.assertEqual(a.index(0, -4*sys.maxsize, 4*sys.maxsize), 2)
        self.assertRaises(ValueError, a.index, 0, 4*sys.maxsize,-4*sys.maxsize)
        self.assertRaises(ValueError, a.index, 2, 0, -10)
        a.remove(0)
        self.assertRaises(ValueError, a.index, 2, 0, 4)
        self.assertEqual(a, self.type2test([-2, -1, 0, 1, 2]))

        # Test modifying the list during index's iteration
        class EvilCmp:
            def __init__(self, victim):
                self.victim = victim
            def __eq__(self, other):
                del self.victim[:]
                return False
        a = self.type2test()
        a[:] = [EvilCmp(a) for _ in range(100)]
        # This used to seg fault before patch #1005778
        self.assertRaises(ValueError, a.index, None)

    def test_reverse(self):
        u = self.type2test([-2, -1, 0, 1, 2])
        u2 = u[:]
        u.reverse()
        self.assertEqual(u, [2, 1, 0, -1, -2])
        u.reverse()
        self.assertEqual(u, u2)

        self.assertRaises(TypeError, u.reverse, 42)

    def test_clear(self):
        u = self.type2test([2, 3, 4])
        u.clear()
        self.assertEqual(u, [])

        u = self.type2test([])
        u.clear()
        self.assertEqual(u, [])

        u = self.type2test([])
        u.append(1)
        u.clear()
        u.append(2)
        self.assertEqual(u, [2])

        self.assertRaises(TypeError, u.clear, None)

    def test_copy(self):
        u = self.type2test([1, 2, 3])
        v = u.copy()
        self.assertEqual(v, [1, 2, 3])

        u = self.type2test([])
        v = u.copy()
        self.assertEqual(v, [])

        # test that it's indeed a copy and not a reference
        u = self.type2test(['a', 'b'])
        v = u.copy()
        v.append('i')
        self.assertEqual(u, ['a', 'b'])
        self.assertEqual(v, u + self.type2test(['i']))

        # test that it's a shallow, not a deep copy
        u = self.type2test([1, 2, [3, 4], 5])
        v = u.copy()
        self.assertEqual(u, v)
        self.assertIs(v[3], u[3])

        self.assertRaises(TypeError, u.copy, None)

    def test_sort(self):
        u = self.type2test([1, 0])
        u.sort()
        self.assertEqual(u, [0, 1])

        u = self.type2test([2,1,0,-1,-2])
        u.sort()
        self.assertEqual(u, self.type2test([-2,-1,0,1,2]))
        
        self.assertRaises(TypeError, u.sort, 42, 42)
        
        a = self.type2test(reversed(list(range(512))))
        a.sort()
        self.assertEqual(a, self.type2test(list(range(512))))
        
        def revcmp(a, b): # pragma: no cover
            if a == b:
                return 0
            elif a < b:
                return 1
            else: # a > b
                return -1
        u.sort(key=CmpToKey(revcmp))
        self.assertEqual(u, self.type2test([2,1,0,-1,-2]))
        
        # The following dumps core in unpatched Python 1.5:
        def myComparison(x,y):
           xmod, ymod = x%3, y%7
           if xmod == ymod:
               return 0
           elif xmod < ymod:
               return -1
           else: # xmod > ymod
               return 1
        z = self.type2test(list(range(12)))
        z.sort(key=CmpToKey(myComparison))
        
        self.assertRaises(TypeError, z.sort, 2)
        
        def selfmodifyingComparison(x,y):
            z.append(1)
            return cmp(x, y)
        self.assertRaises(ValueError, z.sort, key=CmpToKey(selfmodifyingComparison))
        
        if sys.version_info[0] < 3:
            self.assertRaises(TypeError, z.sort, lambda x, y: 's')
        
        self.assertRaises(TypeError, z.sort, 42, 42, 42, 42)

    def test_slice(self):
        u = self.type2test("spam")
        u[:2] = "h"
        self.assertEqual(u, list("ham"))

    def test_iadd(self):
        super(CommonTest, self).test_iadd()
        u = self.type2test([0, 1])
        u2 = u
        u += [2, 3]
        self.assert_(u is u2)

        u = self.type2test("spam")
        u += "eggs"
        self.assertEqual(u, self.type2test("spameggs"))

        self.assertRaises(TypeError, u.__iadd__, None)

    def test_imul(self):
        u = self.type2test([0, 1])
        u *= 3
        self.assertEqual(u, self.type2test([0, 1, 0, 1, 0, 1]))
        u *= 0
        self.assertEqual(u, self.type2test([]))
        s = self.type2test([])
        oldid = id(s)
        s *= 10
        self.assertEqual(id(s), oldid)

    def test_extendedslicing(self):
        #  subscript
        a = self.type2test([0,1,2,3,4])

        #  deletion
        del a[::2]
        self.assertEqual(a, self.type2test([1,3]))
        a = self.type2test(list(range(5)))
        del a[1::2]
        self.assertEqual(a, self.type2test([0,2,4]))
        a = self.type2test(list(range(5)))
        del a[1::-2]
        self.assertEqual(a, self.type2test([0,2,3,4]))
        a = self.type2test(list(range(10)))
        del a[::1000]
        self.assertEqual(a, self.type2test([1, 2, 3, 4, 5, 6, 7, 8, 9]))
        #  assignment
        a = self.type2test(list(range(10)))
        a[::2] = [-1]*5
        self.assertEqual(a, self.type2test([-1, 1, -1, 3, -1, 5, -1, 7, -1, 9]))
        a = self.type2test(list(range(10)))
        a[::-4] = [10]*3
        self.assertEqual(a, self.type2test([0, 10, 2, 3, 4, 10, 6, 7, 8 ,10]))
        a = self.type2test(list(range(4)))
        a[::-1] = a
        self.assertEqual(a, self.type2test([3, 2, 1, 0]))
        a = self.type2test(list(range(10)))
        b = a[:]
        c = a[:]
        a[2:3] = self.type2test(["two", "elements"])
        b[slice(2,3)] = self.type2test(["two", "elements"])
        c[2:3:] = self.type2test(["two", "elements"])
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        a = self.type2test(list(range(10)))
        a[::2] = tuple(range(5))
        self.assertEqual(a, self.type2test([0, 1, 1, 3, 2, 5, 3, 7, 4, 9]))

    def test_constructor_exception_handling(self):
        # Bug #1242657
        class Iter(object):
            def next(self):
                raise KeyboardInterrupt
            __next__ = next
        
        class F(object):
            def __iter__(self):
                return Iter()
        self.assertRaises(KeyboardInterrupt, self.type2test, F())

    def test_sort_cmp(self):
        u = self.type2test([1, 0])
        u.sort()
        self.assertEqual(u, [0, 1])

        u = self.type2test([2,1,0,-1,-2])
        u.sort()
        self.assertEqual(u, self.type2test([-2,-1,0,1,2]))

        self.assertRaises(TypeError, u.sort, 42, 42)

        if sys.version_info[0] >= 3:
          return  # Python 3 removed the cmp option for sort.

        def revcmp(a, b):
            return cmp(b, a)
        u.sort(revcmp)
        self.assertEqual(u, self.type2test([2,1,0,-1,-2]))

        # The following dumps core in unpatched Python 1.5:
        def myComparison(x,y):
            return cmp(x%3, y%7)
        z = self.type2test(range(12))
        z.sort(myComparison)

        self.assertRaises(TypeError, z.sort, 2)

        def selfmodifyingComparison(x,y):
            z.append(1)
            return cmp(x, y)
        self.assertRaises(ValueError, z.sort, selfmodifyingComparison)

        self.assertRaises(TypeError, z.sort, lambda x, y: 's')

        self.assertRaises(TypeError, z.sort, 42, 42, 42, 42)

########NEW FILE########
__FILENAME__ = mapping_tests
# This file taken from Python, licensed under the Python License Agreement

# tests common to dict and UserDict
import sys
import collections
from blist.test import unittest
try:
    from collections import UserDict # Python 3
except ImportError:
    from UserDict import UserDict # Python 2

class BasicTestMappingProtocol(unittest.TestCase):
    # This base class can be used to check that an object conforms to the
    # mapping protocol

    # Functions that can be useful to override to adapt to dictionary
    # semantics
    type2test = None # which class is being tested (overwrite in subclasses)

    def _reference(self): # pragma: no cover
        """Return a dictionary of values which are invariant by storage
        in the object under test."""
        return {1:2, "key1":"value1", "key2":(1,2,3)}
    def _empty_mapping(self):
        """Return an empty mapping object"""
        return self.type2test()
    def _full_mapping(self, data):
        """Return a mapping object with the value contained in data
        dictionary"""
        x = self._empty_mapping()
        for key, value in data.items():
            x[key] = value
        return x

    def __init__(self, *args, **kw):
        unittest.TestCase.__init__(self, *args, **kw)
        self.reference = self._reference().copy()

        # A (key, value) pair not in the mapping
        key, value = self.reference.popitem()
        self.other = {key:value}

        # A (key, value) pair in the mapping
        key, value = self.reference.popitem()
        self.inmapping = {key:value}
        self.reference[key] = value

    def test_read(self):
        # Test for read only operations on mapping
        p = self._empty_mapping()
        p1 = dict(p) #workaround for singleton objects
        d = self._full_mapping(self.reference)
        if d is p: # pragma: no cover
            p = p1
        #Indexing
        for key, value in self.reference.items():
            self.assertEqual(d[key], value)
        knownkey = list(self.other.keys())[0]
        self.failUnlessRaises(KeyError, lambda:d[knownkey])
        #len
        self.assertEqual(len(p), 0)
        self.assertEqual(len(d), len(self.reference))
        #__contains__
        for k in self.reference:
            self.assert_(k in d)
        for k in self.other:
            self.failIf(k in d)
        #cmp
        self.assertEqual(p, p)
        self.assertEqual(d, d)
        self.assertNotEqual(p, d)
        self.assertNotEqual(d, p)
        #__non__zero__
        if p: self.fail("Empty mapping must compare to False")
        if not d: self.fail("Full mapping must compare to True")
        # keys(), items(), iterkeys() ...
        def check_iterandlist(iter, lst, ref):
            if sys.version_info[0] < 3: # pragma: no cover
                self.assert_(hasattr(iter, 'next'))
            else: # pragma: no cover
                self.assert_(hasattr(iter, '__next__'))
            self.assert_(hasattr(iter, '__iter__'))
            x = list(iter)
            self.assert_(set(x)==set(lst)==set(ref))
        check_iterandlist(iter(d.keys()), list(d.keys()),
                          self.reference.keys())
        check_iterandlist(iter(d), list(d.keys()), self.reference.keys())
        check_iterandlist(iter(d.values()), list(d.values()),
                          self.reference.values())
        check_iterandlist(iter(d.items()), list(d.items()),
                          self.reference.items())
        #get
        key, value = next(iter(d.items()))
        knownkey, knownvalue = next(iter(self.other.items()))
        self.assertEqual(d.get(key, knownvalue), value)
        self.assertEqual(d.get(knownkey, knownvalue), knownvalue)
        self.failIf(knownkey in d)

    def test_write(self):
        # Test for write operations on mapping
        p = self._empty_mapping()
        #Indexing
        for key, value in self.reference.items():
            p[key] = value
            self.assertEqual(p[key], value)
        for key in self.reference.keys():
            del p[key]
            self.failUnlessRaises(KeyError, lambda:p[key])
        p = self._empty_mapping()
        #update
        p.update(self.reference)
        self.assertEqual(dict(p), self.reference)
        items = list(p.items())
        p = self._empty_mapping()
        p.update(items)
        self.assertEqual(dict(p), self.reference)
        d = self._full_mapping(self.reference)
        #setdefault
        key, value = next(iter(d.items()))
        knownkey, knownvalue = next(iter(self.other.items()))
        self.assertEqual(d.setdefault(key, knownvalue), value)
        self.assertEqual(d[key], value)
        self.assertEqual(d.setdefault(knownkey, knownvalue), knownvalue)
        self.assertEqual(d[knownkey], knownvalue)
        #pop
        self.assertEqual(d.pop(knownkey), knownvalue)
        self.failIf(knownkey in d)
        self.assertRaises(KeyError, d.pop, knownkey)
        default = 909
        d[knownkey] = knownvalue
        self.assertEqual(d.pop(knownkey, default), knownvalue)
        self.failIf(knownkey in d)
        self.assertEqual(d.pop(knownkey, default), default)
        #popitem
        key, value = d.popitem()
        self.failIf(key in d)
        self.assertEqual(value, self.reference[key])
        p=self._empty_mapping()
        self.assertRaises(KeyError, p.popitem)

    def test_constructor(self):
        self.assertEqual(self._empty_mapping(), self._empty_mapping())

    def test_bool(self):
        self.assert_(not self._empty_mapping())
        self.assert_(self.reference)
        self.assert_(bool(self._empty_mapping()) is False)
        self.assert_(bool(self.reference) is True)

    def test_keys(self):
        d = self._empty_mapping()
        self.assertEqual(list(d.keys()), [])
        d = self.reference
        self.assert_(list(self.inmapping.keys())[0] in d.keys())
        self.assert_(list(self.other.keys())[0] not in d.keys())
        self.assertRaises(TypeError, d.keys, None)

    def test_values(self):
        d = self._empty_mapping()
        self.assertEqual(list(d.values()), [])

        self.assertRaises(TypeError, d.values, None)

    def test_items(self):
        d = self._empty_mapping()
        self.assertEqual(list(d.items()), [])

        self.assertRaises(TypeError, d.items, None)

    def test_len(self):
        d = self._empty_mapping()
        self.assertEqual(len(d), 0)

    def test_getitem(self):
        d = self.reference
        self.assertEqual(d[list(self.inmapping.keys())[0]],
                         list(self.inmapping.values())[0])

        self.assertRaises(TypeError, d.__getitem__)

    def test_update(self):
        # mapping argument
        d = self._empty_mapping()
        d.update(self.other)
        self.assertEqual(list(d.items()), list(self.other.items()))

        # No argument
        d = self._empty_mapping()
        d.update()
        self.assertEqual(d, self._empty_mapping())

        # item sequence
        d = self._empty_mapping()
        d.update(self.other.items())
        self.assertEqual(list(d.items()), list(self.other.items()))

        # Iterator
        d = self._empty_mapping()
        d.update(self.other.items())
        self.assertEqual(list(d.items()), list(self.other.items()))

        # FIXME: Doesn't work with UserDict
        # self.assertRaises((TypeError, AttributeError), d.update, None)
        self.assertRaises((TypeError, AttributeError), d.update, 42)

        outerself = self
        class SimpleUserDict:
            def __init__(self):
                self.d = outerself.reference
            def keys(self):
                return self.d.keys()
            def __getitem__(self, i):
                return self.d[i]
        d.clear()
        d.update(SimpleUserDict())
        i1 = sorted(d.items())
        i2 = sorted(self.reference.items())
        self.assertEqual(i1, i2)

        class Exc(Exception): pass

        d = self._empty_mapping()
        class FailingUserDict:
            def keys(self):
                raise Exc
        self.assertRaises(Exc, d.update, FailingUserDict())

        d.clear()

        class FailingUserDict:
            def keys(self):
                class BogonIter:
                    def __init__(self):
                        self.i = 1
                    def __iter__(self):
                        return self
                    def __next__(self):
                        if self.i:
                            self.i = 0
                            return 'a'
                        raise Exc
                    next = __next__
                return BogonIter()
            def __getitem__(self, key):
                return key
        self.assertRaises(Exc, d.update, FailingUserDict())

        class FailingUserDict:
            def keys(self):
                class BogonIter:
                    def __init__(self):
                        self.i = ord('a')
                    def __iter__(self):
                        return self
                    def __next__(self):
                        if self.i <= ord('z'):
                            rtn = chr(self.i)
                            self.i += 1
                            return rtn
                        else: # pragma: no cover
                            raise StopIteration
                    next = __next__
                return BogonIter()
            def __getitem__(self, key):
                raise Exc
        self.assertRaises(Exc, d.update, FailingUserDict())

        d = self._empty_mapping()
        class badseq(object):
            def __iter__(self):
                return self
            def __next__(self):
                raise Exc()
            next = __next__

        self.assertRaises(Exc, d.update, badseq())

        self.assertRaises(ValueError, d.update, [(1, 2, 3)])

    # no test_fromkeys or test_copy as both os.environ and selves don't support it

    def test_get(self):
        d = self._empty_mapping()
        self.assert_(d.get(list(self.other.keys())[0]) is None)
        self.assertEqual(d.get(list(self.other.keys())[0], 3), 3)
        d = self.reference
        self.assert_(d.get(list(self.other.keys())[0]) is None)
        self.assertEqual(d.get(list(self.other.keys())[0], 3), 3)
        self.assertEqual(d.get(list(self.inmapping.keys())[0]),
                         list(self.inmapping.values())[0])
        self.assertEqual(d.get(list(self.inmapping.keys())[0], 3),
                         list(self.inmapping.values())[0])
        self.assertRaises(TypeError, d.get)
        self.assertRaises(TypeError, d.get, None, None, None)

    def test_setdefault(self):
        d = self._empty_mapping()
        self.assertRaises(TypeError, d.setdefault)

    def test_popitem(self):
        d = self._empty_mapping()
        self.assertRaises(KeyError, d.popitem)
        self.assertRaises(TypeError, d.popitem, 42)

    def test_pop(self):
        d = self._empty_mapping()
        k, v = list(self.inmapping.items())[0]
        d[k] = v
        self.assertRaises(KeyError, d.pop, list(self.other.keys())[0])

        self.assertEqual(d.pop(k), v)
        self.assertEqual(len(d), 0)

        self.assertRaises(KeyError, d.pop, k)


class TestMappingProtocol(BasicTestMappingProtocol):
    def test_constructor(self):
        BasicTestMappingProtocol.test_constructor(self)
        self.assert_(self._empty_mapping() is not self._empty_mapping())
        self.assertEqual(self.type2test(x=1, y=2), self._full_mapping({"x": 1, "y": 2}))

    def test_bool(self):
        BasicTestMappingProtocol.test_bool(self)
        self.assert_(not self._empty_mapping())
        self.assert_(self._full_mapping({"x": "y"}))
        self.assert_(bool(self._empty_mapping()) is False)
        self.assert_(bool(self._full_mapping({"x": "y"})) is True)

    def test_keys(self):
        BasicTestMappingProtocol.test_keys(self)
        d = self._empty_mapping()
        self.assertEqual(list(d.keys()), [])
        d = self._full_mapping({'a': 1, 'b': 2})
        k = d.keys()
        self.assert_('a' in k)
        self.assert_('b' in k)
        self.assert_('c' not in k)

    def test_values(self):
        BasicTestMappingProtocol.test_values(self)
        d = self._full_mapping({1:2})
        self.assertEqual(list(d.values()), [2])

    def test_items(self):
        BasicTestMappingProtocol.test_items(self)

        d = self._full_mapping({1:2})
        self.assertEqual(list(d.items()), [(1, 2)])

    def test_contains(self):
        d = self._empty_mapping()
        self.assert_(not ('a' in d))
        self.assert_('a' not in d)
        d = self._full_mapping({'a': 1, 'b': 2})
        self.assert_('a' in d)
        self.assert_('b' in d)
        self.assert_('c' not in d)

        self.assertRaises(TypeError, d.__contains__)

    def test_len(self):
        BasicTestMappingProtocol.test_len(self)
        d = self._full_mapping({'a': 1, 'b': 2})
        self.assertEqual(len(d), 2)

    def test_getitem(self):
        BasicTestMappingProtocol.test_getitem(self)
        d = self._full_mapping({'a': 1, 'b': 2})
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2)
        d['c'] = 3
        d['a'] = 4
        self.assertEqual(d['c'], 3)
        self.assertEqual(d['a'], 4)
        del d['b']
        self.assertEqual(d, self._full_mapping({'a': 4, 'c': 3}))

        self.assertRaises(TypeError, d.__getitem__)

    def test_clear(self):
        d = self._full_mapping({1:1, 2:2, 3:3})
        d.clear()
        self.assertEqual(d, self._full_mapping({}))

        self.assertRaises(TypeError, d.clear, None)

    def test_update(self):
        BasicTestMappingProtocol.test_update(self)
        # mapping argument
        d = self._empty_mapping()
        d.update({1:100})
        d.update({2:20})
        d.update({1:1, 2:2, 3:3})
        self.assertEqual(d, self._full_mapping({1:1, 2:2, 3:3}))

        # no argument
        d.update()
        self.assertEqual(d, self._full_mapping({1:1, 2:2, 3:3}))

        # keyword arguments
        d = self._empty_mapping()
        d.update(x=100)
        d.update(y=20)
        d.update(x=1, y=2, z=3)
        self.assertEqual(d, self._full_mapping({"x":1, "y":2, "z":3}))

        # item sequence
        d = self._empty_mapping()
        d.update([("x", 100), ("y", 20)])
        self.assertEqual(d, self._full_mapping({"x":100, "y":20}))

        # Both item sequence and keyword arguments
        d = self._empty_mapping()
        d.update([("x", 100), ("y", 20)], x=1, y=2)
        self.assertEqual(d, self._full_mapping({"x":1, "y":2}))

        # iterator
        d = self._full_mapping({1:3, 2:4})
        d.update(self._full_mapping({1:2, 3:4, 5:6}).items())
        self.assertEqual(d, self._full_mapping({1:2, 2:4, 3:4, 5:6}))

        class SimpleUserDict:
            def __init__(self):
                self.d = {1:1, 2:2, 3:3}
            def keys(self):
                return self.d.keys()
            def __getitem__(self, i):
                return self.d[i]
        d.clear()
        d.update(SimpleUserDict())
        self.assertEqual(d, self._full_mapping({1:1, 2:2, 3:3}))

    def test_fromkeys(self):
        self.assertEqual(self.type2test.fromkeys('abc'), self._full_mapping({'a':None, 'b':None, 'c':None}))
        d = self._empty_mapping()
        self.assert_(not(d.fromkeys('abc') is d))
        self.assertEqual(d.fromkeys('abc'), self._full_mapping({'a':None, 'b':None, 'c':None}))
        self.assertEqual(d.fromkeys((4,5),0), self._full_mapping({4:0, 5:0}))
        self.assertEqual(d.fromkeys([]), self._full_mapping({}))
        def g():
            yield 1
        self.assertEqual(d.fromkeys(g()), self._full_mapping({1:None}))
        self.assertRaises(TypeError, {}.fromkeys, 3)
        class dictlike(self.type2test): pass
        self.assertEqual(dictlike.fromkeys('a'), self._full_mapping({'a':None}))
        self.assertEqual(dictlike().fromkeys('a'), self._full_mapping({'a':None}))
        self.assert_(dictlike.fromkeys('a').__class__ is dictlike)
        self.assert_(dictlike().fromkeys('a').__class__ is dictlike)
        # FIXME: the following won't work with UserDict, because it's an old style class
        # self.assert_(type(dictlike.fromkeys('a')) is dictlike)
        class mydict(self.type2test):
            def __new__(cls):
                return UserDict()
        ud = mydict.fromkeys('ab')
        self.assertEqual(ud, {'a':None, 'b':None})
        # FIXME: the following won't work with UserDict, because it's an old style class
        # self.assert_(isinstance(ud, collections.UserDict))
        self.assertRaises(TypeError, dict.fromkeys)

        class Exc(Exception): pass

        class baddict1(self.type2test):
            def __init__(self):
                raise Exc()

        self.assertRaises(Exc, baddict1.fromkeys, [1])

        class BadSeq(object):
            def __iter__(self):
                return self
            def __next__(self):
                raise Exc()
            next = __next__

        self.assertRaises(Exc, self.type2test.fromkeys, BadSeq())

        class baddict2(self.type2test):
            def __setitem__(self, key, value):
                raise Exc()

        self.assertRaises(Exc, baddict2.fromkeys, [1])

    def test_copy(self):
        d = self._full_mapping({1:1, 2:2, 3:3})
        self.assertEqual(d.copy(), self._full_mapping({1:1, 2:2, 3:3}))
        d = self._empty_mapping()
        self.assertEqual(d.copy(), d)
        self.assert_(isinstance(d.copy(), d.__class__))
        self.assertRaises(TypeError, d.copy, None)

    def test_get(self):
        BasicTestMappingProtocol.test_get(self)
        d = self._empty_mapping()
        self.assert_(d.get('c') is None)
        self.assertEqual(d.get('c', 3), 3)
        d = self._full_mapping({'a' : 1, 'b' : 2})
        self.assert_(d.get('c') is None)
        self.assertEqual(d.get('c', 3), 3)
        self.assertEqual(d.get('a'), 1)
        self.assertEqual(d.get('a', 3), 1)

    def test_setdefault(self):
        BasicTestMappingProtocol.test_setdefault(self)
        d = self._empty_mapping()
        self.assert_(d.setdefault('key0') is None)
        d.setdefault('key0', [])
        self.assert_(d.setdefault('key0') is None)
        d.setdefault('key', []).append(3)
        self.assertEqual(d['key'][0], 3)
        d.setdefault('key', []).append(4)
        self.assertEqual(len(d['key']), 2)

    def test_popitem(self):
        BasicTestMappingProtocol.test_popitem(self)
        for copymode in -1, +1:
            # -1: b has same structure as a
            # +1: b is a.copy()
            for log2size in range(12):
                size = 2**log2size
                a = self._empty_mapping()
                b = self._empty_mapping()
                for i in range(size):
                    a[repr(i)] = i
                    if copymode < 0:
                        b[repr(i)] = i
                if copymode > 0:
                    b = a.copy()
                for i in range(size):
                    ka, va = ta = a.popitem()
                    self.assertEqual(va, int(ka))
                    kb, vb = tb = b.popitem()
                    self.assertEqual(vb, int(kb))
                    self.assert_(not(copymode < 0 and ta != tb))
                self.assert_(not a)
                self.assert_(not b)

    def test_pop(self):
        BasicTestMappingProtocol.test_pop(self)

        # Tests for pop with specified key
        d = self._empty_mapping()
        k, v = 'abc', 'def'

        # verify longs/ints get same value when key > 32 bits (for 64-bit archs)
        # see SF bug #689659
        x = 4503599627370496
        y = 4503599627370496
        h = self._full_mapping({x: 'anything', y: 'something else'})
        self.assertEqual(h[x], h[y])

        self.assertEqual(d.pop(k, v), v)
        d[k] = v
        self.assertEqual(d.pop(k, 1), v)


class TestHashMappingProtocol(TestMappingProtocol):

    def test_getitem(self):
        TestMappingProtocol.test_getitem(self)
        class Exc(Exception): pass

        class BadEq(object):
            def __eq__(self, other): # pragma: no cover
                raise Exc()
            def __hash__(self):
                return 24

        d = self._empty_mapping()
        d[BadEq()] = 42
        self.assertRaises(KeyError, d.__getitem__, 23)

        class BadHash(object):
            fail = False
            def __hash__(self):
                if self.fail:
                    raise Exc()
                else:
                    return 42

        d = self._empty_mapping()
        x = BadHash()
        d[x] = 42
        x.fail = True
        self.assertRaises(Exc, d.__getitem__, x)

    def test_fromkeys(self):
        TestMappingProtocol.test_fromkeys(self)
        class mydict(self.type2test):
            def __new__(cls):
                return UserDict()
        ud = mydict.fromkeys('ab')
        self.assertEqual(ud, {'a':None, 'b':None})
        self.assert_(isinstance(ud, UserDict))

    def test_pop(self):
        TestMappingProtocol.test_pop(self)

        class Exc(Exception): pass

        class BadHash(object):
            fail = False
            def __hash__(self):
                if self.fail:
                    raise Exc()
                else:
                    return 42

        d = self._empty_mapping()
        x = BadHash()
        d[x] = 42
        x.fail = True
        self.assertRaises(Exc, d.pop, x)

    def test_mutatingiteration(self): # pragma: no cover
        d = self._empty_mapping()
        d[1] = 1
        try:
            for i in d:
                d[i+1] = 1
        except RuntimeError:
            pass
        else:
            self.fail("changing dict size during iteration doesn't raise Error")

    def test_repr(self): # pragma: no cover
        d = self._empty_mapping()
        self.assertEqual(repr(d), '{}')
        d[1] = 2
        self.assertEqual(repr(d), '{1: 2}')
        d = self._empty_mapping()
        d[1] = d
        self.assertEqual(repr(d), '{1: {...}}')

        class Exc(Exception): pass

        class BadRepr(object):
            def __repr__(self):
                raise Exc()

        d = self._full_mapping({1: BadRepr()})
        self.assertRaises(Exc, repr, d)

    def test_eq(self):
        self.assertEqual(self._empty_mapping(), self._empty_mapping())
        self.assertEqual(self._full_mapping({1: 2}),
                         self._full_mapping({1: 2}))

        class Exc(Exception): pass

        class BadCmp(object):
            def __eq__(self, other):
                raise Exc()
            def __hash__(self):
                return 1

        d1 = self._full_mapping({BadCmp(): 1})
        d2 = self._full_mapping({1: 1})
        self.assertRaises(Exc, lambda: BadCmp()==1)
        #self.assertRaises(Exc, lambda: d1==d2)

    def test_setdefault(self):
        TestMappingProtocol.test_setdefault(self)

        class Exc(Exception): pass

        class BadHash(object):
            fail = False
            def __hash__(self):
                if self.fail:
                    raise Exc()
                else:
                    return 42

        d = self._empty_mapping()
        x = BadHash()
        d[x] = 42
        x.fail = True
        self.assertRaises(Exc, d.setdefault, x, [])

########NEW FILE########
__FILENAME__ = seq_tests
# This file taken from Python, licensed under the Python License Agreement

from __future__ import print_function
"""
Tests common to tuple, list and UserList.UserList
"""

from blist.test import test_support
from blist.test import unittest
import sys

# Various iterables
# This is used for checking the constructor (here and in test_deque.py)
def iterfunc(seqn):
    'Regular generator'
    for i in seqn:
        yield i

class Sequence:
    'Sequence using __getitem__'
    def __init__(self, seqn):
        self.seqn = seqn
    def __getitem__(self, i):
        return self.seqn[i]

class IterFunc:
    'Sequence using iterator protocol'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.i >= len(self.seqn): raise StopIteration
        v = self.seqn[self.i]
        self.i += 1
        return v
    next = __next__

class IterGen:
    'Sequence using iterator protocol defined with a generator'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        for val in self.seqn:
            yield val

class IterNextOnly:
    'Missing __getitem__ and __iter__'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __next__(self): # pragma: no cover
        if self.i >= len(self.seqn): raise StopIteration
        v = self.seqn[self.i]
        self.i += 1
        return v
    next = __next__

class IterNoNext:
    'Iterator missing next()'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        return self

class IterGenExc:
    'Test propagation of exceptions'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        return self
    def __next__(self):
        3 // 0
    next = __next__

class IterFuncStop:
    'Test immediate stop'
    def __init__(self, seqn):
        pass
    def __iter__(self):
        return self
    def __next__(self):
        raise StopIteration
    next = __next__

from itertools import chain
def itermulti(seqn):
    'Test multiple tiers of iterators'
    return chain(map(lambda x:x, iterfunc(IterGen(Sequence(seqn)))))

class CommonTest(unittest.TestCase):
    # The type to be tested
    type2test = None

    def test_constructors(self):
        l0 = []
        l1 = [0]
        l2 = [0, 1]

        u = self.type2test()
        u0 = self.type2test(l0)
        u1 = self.type2test(l1)
        u2 = self.type2test(l2)

        uu = self.type2test(u)
        uu0 = self.type2test(u0)
        uu1 = self.type2test(u1)
        uu2 = self.type2test(u2)

        v = self.type2test(tuple(u))
        class OtherSeq:
            def __init__(self, initseq):
                self.__data = initseq
            def __len__(self):
                return len(self.__data)
            def __getitem__(self, i):
                return self.__data[i]
        s = OtherSeq(u0)
        v0 = self.type2test(s)
        self.assertEqual(len(v0), len(s))

        s = "this is also a sequence"
        vv = self.type2test(s)
        self.assertEqual(len(vv), len(s))

        # Create from various iteratables
        for s in ("123", "", list(range(1000)), ('do', 1.2), range(2000,2200,5)):
            for g in (Sequence, IterFunc, IterGen,
                      itermulti, iterfunc):
                self.assertEqual(self.type2test(g(s)), self.type2test(s))
            self.assertEqual(self.type2test(IterFuncStop(s)), self.type2test())
            self.assertEqual(self.type2test(c for c in "123"), self.type2test("123"))
            self.assertRaises(TypeError, self.type2test, IterNextOnly(s))
            self.assertRaises(TypeError, self.type2test, IterNoNext(s))
            self.assertRaises(ZeroDivisionError, self.type2test, IterGenExc(s))

    def test_truth(self):
        self.assert_(not self.type2test())
        self.assert_(self.type2test([42]))

    def test_getitem(self):
        u = self.type2test([0, 1, 2, 3, 4])
        for i in range(len(u)):
            self.assertEqual(u[i], i)
            self.assertEqual(u[int(i)], i)
        for i in range(-len(u), -1):
            self.assertEqual(u[i], len(u)+i)
            self.assertEqual(u[int(i)], len(u)+i)
        self.assertRaises(IndexError, u.__getitem__, -len(u)-1)
        self.assertRaises(IndexError, u.__getitem__, len(u))
        self.assertRaises(ValueError, u.__getitem__, slice(0,10,0))

        u = self.type2test()
        self.assertRaises(IndexError, u.__getitem__, 0)
        self.assertRaises(IndexError, u.__getitem__, -1)

        self.assertRaises(TypeError, u.__getitem__)

        a = self.type2test([10, 11])
        self.assertEqual(a[0], 10)
        self.assertEqual(a[1], 11)
        self.assertEqual(a[-2], 10)
        self.assertEqual(a[-1], 11)
        self.assertRaises(IndexError, a.__getitem__, -3)
        self.assertRaises(IndexError, a.__getitem__, 3)

    def test_getslice(self):
        l = [0, 1, 2, 3, 4]
        u = self.type2test(l)

        self.assertEqual(u[0:0], self.type2test())
        self.assertEqual(u[1:2], self.type2test([1]))
        self.assertEqual(u[-2:-1], self.type2test([3]))
        self.assertEqual(u[-1000:1000], u)
        self.assertEqual(u[1000:-1000], self.type2test([]))
        self.assertEqual(u[:], u)
        self.assertEqual(u[1:None], self.type2test([1, 2, 3, 4]))
        self.assertEqual(u[None:3], self.type2test([0, 1, 2]))

        # Extended slices
        self.assertEqual(u[::], u)
        self.assertEqual(u[::2], self.type2test([0, 2, 4]))
        self.assertEqual(u[1::2], self.type2test([1, 3]))
        self.assertEqual(u[::-1], self.type2test([4, 3, 2, 1, 0]))
        self.assertEqual(u[::-2], self.type2test([4, 2, 0]))
        self.assertEqual(u[3::-2], self.type2test([3, 1]))
        self.assertEqual(u[3:3:-2], self.type2test([]))
        self.assertEqual(u[3:2:-2], self.type2test([3]))
        self.assertEqual(u[3:1:-2], self.type2test([3]))
        self.assertEqual(u[3:0:-2], self.type2test([3, 1]))
        self.assertEqual(u[::-100], self.type2test([4]))
        self.assertEqual(u[100:-100:], self.type2test([]))
        self.assertEqual(u[-100:100:], u)
        self.assertEqual(u[100:-100:-1], u[::-1])
        self.assertEqual(u[-100:100:-1], self.type2test([]))
        self.assertEqual(u[-100:100:2], self.type2test([0, 2, 4]))

        # Test extreme cases with long ints
        a = self.type2test([0,1,2,3,4])
        self.assertEqual(a[ -pow(2,128): 3 ], self.type2test([0,1,2]))
        self.assertEqual(a[ 3: pow(2,145) ], self.type2test([3,4]))

        if sys.version_info[0] < 3:
            self.assertRaises(TypeError, u.__getslice__)

    def test_contains(self):
        u = self.type2test([0, 1, 2])
        for i in u:
            self.assert_(i in u)
        for i in min(u)-1, max(u)+1:
            self.assert_(i not in u)

        self.assertRaises(TypeError, u.__contains__)

    def test_contains_fake(self):
        class AllEq:
            # Sequences must use rich comparison against each item
            # (unless "is" is true, or an earlier item answered)
            # So instances of AllEq must be found in all non-empty sequences.
            def __eq__(self, other):
                return True
            def __hash__(self): # pragma: no cover
                raise NotImplemented
        self.assert_(AllEq() not in self.type2test([]))
        self.assert_(AllEq() in self.type2test([1]))

    def test_contains_order(self):
        # Sequences must test in-order.  If a rich comparison has side
        # effects, these will be visible to tests against later members.
        # In this test, the "side effect" is a short-circuiting raise.
        class DoNotTestEq(Exception):
            pass
        class StopCompares:
            def __eq__(self, other):
                raise DoNotTestEq

        checkfirst = self.type2test([1, StopCompares()])
        self.assert_(1 in checkfirst)
        checklast = self.type2test([StopCompares(), 1])
        self.assertRaises(DoNotTestEq, checklast.__contains__, 1)

    def test_len(self):
        self.assertEqual(len(self.type2test()), 0)
        self.assertEqual(len(self.type2test([])), 0)
        self.assertEqual(len(self.type2test([0])), 1)
        self.assertEqual(len(self.type2test([0, 1, 2])), 3)

    def test_minmax(self):
        u = self.type2test([0, 1, 2])
        self.assertEqual(min(u), 0)
        self.assertEqual(max(u), 2)

    def test_addmul(self):
        u1 = self.type2test([0])
        u2 = self.type2test([0, 1])
        self.assertEqual(u1, u1 + self.type2test())
        self.assertEqual(u1, self.type2test() + u1)
        self.assertEqual(u1 + self.type2test([1]), u2)
        self.assertEqual(self.type2test([-1]) + u1, self.type2test([-1, 0]))
        self.assertEqual(self.type2test(), u2*0)
        self.assertEqual(self.type2test(), 0*u2)
        self.assertEqual(self.type2test(), u2*0)
        self.assertEqual(self.type2test(), 0*u2)
        self.assertEqual(u2, u2*1)
        self.assertEqual(u2, 1*u2)
        self.assertEqual(u2, u2*1)
        self.assertEqual(u2, 1*u2)
        self.assertEqual(u2+u2, u2*2)
        self.assertEqual(u2+u2, 2*u2)
        self.assertEqual(u2+u2, u2*2)
        self.assertEqual(u2+u2, 2*u2)
        self.assertEqual(u2+u2+u2, u2*3)
        self.assertEqual(u2+u2+u2, 3*u2)

        class subclass(self.type2test):
            pass
        u3 = subclass([0, 1])
        self.assertEqual(u3, u3*1)
        self.assert_(u3 is not u3*1)

    def test_iadd(self):
        u = self.type2test([0, 1])
        u += self.type2test()
        self.assertEqual(u, self.type2test([0, 1]))
        u += self.type2test([2, 3])
        self.assertEqual(u, self.type2test([0, 1, 2, 3]))
        u += self.type2test([4, 5])
        self.assertEqual(u, self.type2test([0, 1, 2, 3, 4, 5]))

        u = self.type2test("spam")
        u += self.type2test("eggs")
        self.assertEqual(u, self.type2test("spameggs"))

    def test_imul(self):
        u = self.type2test([0, 1])
        u *= 3
        self.assertEqual(u, self.type2test([0, 1, 0, 1, 0, 1]))

    def test_getitemoverwriteiter(self):
        # Verify that __getitem__ overrides are not recognized by __iter__
        class T(self.type2test):
            def __getitem__(self, key): # pragma: no cover
                return str(key) + '!!!'
        self.assertEqual(next(iter(T((1,2)))), 1)

    def test_repeat(self):
        for m in range(4):
            s = tuple(range(m))
            for n in range(-3, 5):
                self.assertEqual(self.type2test(s*n), self.type2test(s)*n)
            self.assertEqual(self.type2test(s)*(-4), self.type2test([]))
            self.assertEqual(id(s), id(s*1))

    def test_subscript(self):
        a = self.type2test([10, 11])
        self.assertEqual(a.__getitem__(0), 10)
        self.assertEqual(a.__getitem__(1), 11)
        self.assertEqual(a.__getitem__(-2), 10)
        self.assertEqual(a.__getitem__(-1), 11)
        self.assertRaises(IndexError, a.__getitem__, -3)
        self.assertRaises(IndexError, a.__getitem__, 3)
        self.assertEqual(a.__getitem__(slice(0,1)), self.type2test([10]))
        self.assertEqual(a.__getitem__(slice(1,2)), self.type2test([11]))
        self.assertEqual(a.__getitem__(slice(0,2)), self.type2test([10, 11]))
        self.assertEqual(a.__getitem__(slice(0,3)), self.type2test([10, 11]))
        self.assertEqual(a.__getitem__(slice(3,5)), self.type2test([]))
        self.assertRaises(ValueError, a.__getitem__, slice(0, 10, 0))
        self.assertRaises(TypeError, a.__getitem__, 'x')

########NEW FILE########
__FILENAME__ = sorteddict_tests
import bisect
import sys
import blist
from blist.test import mapping_tests

def CmpToKey(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) == -1
    return K

class sorteddict_test(mapping_tests.TestHashMappingProtocol):
    type2test = blist.sorteddict

    def _reference(self):
        """Return a dictionary of values which are invariant by storage
        in the object under test."""
        return {1:2, 3:4, 5:6}

    class Collider(object):
        def __init__(self, x):
            self.x = x
        def __repr__(self):
            return 'Collider(%r)' % self.x
        def __eq__(self, other):
            return self.__class__ == other.__class__ and self.x == other.x
        def __lt__(self, other):
            if type(self) != type(other):
                return NotImplemented
            return self.x < other.x
        def __hash__(self):
            return 42

    def test_repr(self):
        d = self._empty_mapping()
        self.assertEqual(repr(d), 'sorteddict({})')
        d[1] = 2
        self.assertEqual(repr(d), 'sorteddict({1: 2})')
        d = self._empty_mapping()
        d[1] = d
        self.assertEqual(repr(d), 'sorteddict({1: sorteddict({...})})')
        d = self._empty_mapping()
        d[self.Collider(1)] = 1
        d[self.Collider(2)] = 2
        self.assertEqual(repr(d),
                         'sorteddict({Collider(1): 1, Collider(2): 2})')
        d = self._empty_mapping()
        d[self.Collider(2)] = 2
        d[self.Collider(1)] = 1
        self.assertEqual(repr(d),
                         'sorteddict({Collider(1): 1, Collider(2): 2})')

        class Exc(Exception): pass

        class BadRepr(object):
            def __repr__(self):
                raise Exc()

        d = self._full_mapping({1: BadRepr()})
        self.assertRaises(Exc, repr, d)

    def test_mutatingiteration(self):
        pass

    def test_sort(self):
        u = self.type2test.fromkeys([1, 0])
        self.assertEqual(list(u.keys()), [0, 1])

        u = self.type2test.fromkeys([2,1,0,-1,-2])
        self.assertEqual(u, self.type2test.fromkeys([-2,-1,0,1,2]))
        self.assertEqual(list(u.keys()), [-2,-1,0,1,2])
        
        a = self.type2test.fromkeys(reversed(list(range(512))))
        self.assertEqual(list(a.keys()), list(range(512)))
        
        def revcmp(a, b): # pragma: no cover
            if a == b:
                return 0
            elif a < b:
                return 1
            else: # a > b
                return -1
        u = self.type2test.fromkeys([2,1,0,-1,-2], key=CmpToKey(revcmp))
        self.assertEqual(list(u.keys()), [2,1,0,-1,-2])
        
        # The following dumps core in unpatched Python 1.5:
        def myComparison(x,y):
           xmod, ymod = x%3, y%7
           if xmod == ymod:
               return 0
           elif xmod < ymod:
               return -1
           else: # xmod > ymod
               return 1

        self.type2test.fromkeys(list(range(12)), key=CmpToKey(myComparison))

        #def selfmodifyingComparison(x,y):
        #    z[x+y] = None
        #    return cmp(x, y)
        #z = self.type2test(CmpToKey(selfmodifyingComparison))
        #self.assertRaises(ValueError, z.update, [(i,i) for i in range(12)])
        
        self.assertRaises(TypeError, self.type2test.fromkeys, 42, 42, 42, 42)

    def test_view_indexing_without_key(self):
      self._test_view_indexing(key=None)

    def test_view_indexing_with_key(self):
      self._test_view_indexing(key=lambda x: -x)

    def _test_view_indexing(self, key):
      expected_items = [(3, "first"), (7, "second")]
      if key is not None:
        u = self.type2test(key, expected_items)
        expected_items.sort(key=lambda item: key(item[0]))
      else:
        u = self.type2test(expected_items)
        expected_items.sort()
      expected_keys, expected_values = list(zip(*expected_items))

      if sys.version_info[0] < 3:
        keys = u.viewkeys()
        values = u.viewvalues()
        items = u.viewitems()
      else:
        keys = u.keys()
        values = u.values()
        items = u.items()

      for i in range(len(expected_items)):
        self.assertEqual(keys[i], expected_keys[i])
        self.assertEqual(values[i], expected_values[i])
        self.assertEqual(items[i], expected_items[i])

      for i in range(-1, len(expected_items)+1):
        for j in range(-1, len(expected_items)+1):
          self.assertEqual(keys[i:j], blist.sortedset(expected_keys[i:j]))
          self.assertEqual(values[i:j], list(expected_values[i:j]))
          self.assertEqual(items[i:j], blist.sortedset(expected_items[i:j]))

      self.assertEqual(list(reversed(keys)), list(reversed(expected_keys)))
      for i, key in enumerate(expected_keys):
        self.assertEqual(keys.index(key), expected_keys.index(key))
        self.assertEqual(keys.count(key), 1)
        self.assertEqual(keys.bisect_left(key), i)
        self.assertEqual(keys.bisect_right(key), i+1)
      self.assertEqual(keys.count(object()), 0)
      self.assertRaises(ValueError, keys.index, object())

      for item in expected_items:
        self.assertEqual(items.index(item), expected_items.index(item))
        self.assertEqual(items.count(item), 1)
      self.assertEqual(items.count((7, "foo")), 0)
      self.assertEqual(items.count((object(), object())), 0)
      self.assertRaises(ValueError, items.index, (7, "foo"))
      self.assertRaises(ValueError, items.index, (object(), object()))

########NEW FILE########
__FILENAME__ = sortedlist_tests
# This file based loosely on Python's list_tests.py.

import sys
import collections, operator
import gc
import random
import blist
from blist.test import unittest
from blist.test import list_tests, seq_tests

def CmpToKey(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) == -1
    return K

class SortedBase(object):
    def build_items(self, n):
        return list(range(n))

    def build_item(self, x):
        return x

    def test_empty_repr(self):
        self.assertEqual('%s()' % self.type2test.__name__,
                         repr(self.type2test()))

    def validate_comparison(self, instance):
        if sys.version_info[0] < 3 and isinstance(instance, collections.Set):
            ops = ['ne', 'or', 'and', 'xor', 'sub']
        else:
            ops = ['lt', 'gt', 'le', 'ge', 'ne', 'or', 'and', 'xor', 'sub']
        operators = {}
        for op in ops:
            name = '__'+op+'__'
            operators['__'+op+'__'] = getattr(operator, name)

        class Other(object):
            def __init__(self):
                self.right_side = False
            def __eq__(self, other):
                self.right_side = True
                return True
            __lt__ = __eq__
            __gt__ = __eq__
            __le__ = __eq__
            __ge__ = __eq__
            __ne__ = __eq__
            __ror__ = __eq__
            __rand__ = __eq__
            __rxor__ = __eq__
            __rsub__ = __eq__

        for name, op in operators.items():
            if not hasattr(instance, name): continue
            other = Other()
            op(instance, other)
            self.assertTrue(other.right_side,'Right side not called for %s.%s'
                            % (type(instance), name))

    def test_right_side(self):
        self.validate_comparison(self.type2test())

    def test_delitem(self):
        items = self.build_items(2)
        a = self.type2test(items)
        del a[1]
        self.assertEqual(a, self.type2test(items[:1]))
        del a[0]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test(items)
        del a[-2]
        self.assertEqual(a, self.type2test(items[1:]))
        del a[-1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test(items)
        self.assertRaises(IndexError, a.__delitem__, -3)
        self.assertRaises(IndexError, a.__delitem__, 2)

        a = self.type2test([])
        self.assertRaises(IndexError, a.__delitem__, 0)

        self.assertRaises(TypeError, a.__delitem__)

    def test_delslice(self):
        items = self.build_items(2)
        a = self.type2test(items)
        del a[1:2]
        del a[0:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test(items)
        del a[1:2]
        del a[0:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test(items)
        del a[-2:-1]
        self.assertEqual(a, self.type2test(items[1:]))

        a = self.type2test(items)
        del a[-2:-1]
        self.assertEqual(a, self.type2test(items[1:]))

        a = self.type2test(items)
        del a[1:]
        del a[:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test(items)
        del a[1:]
        del a[:1]
        self.assertEqual(a, self.type2test([]))

        a = self.type2test(items)
        del a[-1:]
        self.assertEqual(a, self.type2test(items[:1]))

        a = self.type2test(items)
        del a[-1:]
        self.assertEqual(a, self.type2test(items[:1]))

        a = self.type2test(items)
        del a[:]
        self.assertEqual(a, self.type2test([]))

    def test_out_of_range(self):
        u = self.type2test()
        def del_test():
            del u[0]
        self.assertRaises(IndexError, lambda: u[0])
        self.assertRaises(IndexError, del_test)

    def test_bad_mul(self):
        u = self.type2test()
        self.assertRaises(TypeError, lambda: u * 'q')
        def imul_test():
            u = self.type2test()
            u *= 'q'
        self.assertRaises(TypeError, imul_test)

    def test_pop(self):
        lst = self.build_items(20)
        random.shuffle(lst)
        u = self.type2test(lst)
        for i in range(20-1,-1,-1):
            x = u.pop(i)
            self.assertEqual(x, i)
        self.assertEqual(0, len(u))

    def test_reversed(self):
        lst = list(range(20))
        a = self.type2test(lst)
        r = reversed(a)
        self.assertEqual(list(r), list(range(19, -1, -1)))
        if hasattr(r, '__next__'): # pragma: no cover
            self.assertRaises(StopIteration, r.__next__)
        else: # pragma: no cover
            self.assertRaises(StopIteration, r.next)
        self.assertEqual(self.type2test(reversed(self.type2test())),
                         self.type2test())

    def test_mismatched_types(self):
        class NotComparable:
            def __lt__(self, other): # pragma: no cover
                raise TypeError
            def __cmp__(self, other): # pragma: no cover
                raise TypeError
        NotComparable = NotComparable()

        item = self.build_item(5)
        sl = self.type2test()
        sl.add(item)
        self.assertRaises(TypeError, sl.add, NotComparable)
        self.assertFalse(NotComparable in sl)
        self.assertEqual(sl.count(NotComparable), 0)
        sl.discard(NotComparable)
        self.assertRaises(ValueError, sl.index, NotComparable)

    def test_order(self):
        stuff = [self.build_item(random.randrange(1000000))
                 for i in range(1000)]
        if issubclass(self.type2test, collections.Set):
            stuff = set(stuff)
        sorted_stuff = list(sorted(stuff))
        u = self.type2test

        self.assertEqual(sorted_stuff, list(u(stuff)))
        sl = u()
        for x in stuff:
            sl.add(x)
        self.assertEqual(sorted_stuff, list(sl))
        x = sorted_stuff.pop(len(stuff)//2)
        sl.discard(x)
        self.assertEqual(sorted_stuff, list(sl))

    def test_constructors(self):
        # Based on the seq_test, but without adding incomparable types
        # to the list.

        l0 = self.build_items(0)
        l1 = self.build_items(1)
        l2 = self.build_items(2)

        u = self.type2test()
        u0 = self.type2test(l0)
        u1 = self.type2test(l1)
        u2 = self.type2test(l2)

        uu = self.type2test(u)
        uu0 = self.type2test(u0)
        uu1 = self.type2test(u1)
        uu2 = self.type2test(u2)

        v = self.type2test(tuple(u))
        class OtherSeq:
            def __init__(self, initseq):
                self.__data = initseq
            def __len__(self):
                return len(self.__data)
            def __getitem__(self, i):
                return self.__data[i]
        s = OtherSeq(u0)
        v0 = self.type2test(s)
        self.assertEqual(len(v0), len(s))

    def test_sort(self):
        # based on list_tests.py
        lst = [1, 0]
        lst = [self.build_item(x) for x in lst]
        u = self.type2test(lst)
        self.assertEqual(list(u), [0, 1])

        lst = [2,1,0,-1,-2]
        lst = [self.build_item(x) for x in lst]
        u = self.type2test(lst)
        self.assertEqual(list(u), [-2,-1,0,1,2])

        lst = list(range(512))
        lst = [self.build_item(x) for x in lst]
        a = self.type2test(reversed(lst))
        self.assertEqual(list(a), lst)

        def revcmp(a, b): # pragma: no cover
            if a == b:
                return 0
            elif a < b:
                return 1
            else: # a > b
                return -1
        u = self.type2test(u, key=CmpToKey(revcmp))
        self.assertEqual(list(u), [2,1,0,-1,-2])

        # The following dumps core in unpatched Python 1.5:
        def myComparison(x,y):
           xmod, ymod = x%3, y%7
           if xmod == ymod:
               return 0
           elif xmod < ymod:
               return -1
           else: # xmod > ymod
               return 1
        z = self.type2test(list(range(12)), key=CmpToKey(myComparison))

        self.assertRaises(TypeError, self.type2test, 42, 42, 42, 42)

class StrongSortedBase(SortedBase, seq_tests.CommonTest):
    def not_applicable(self):
        pass
    test_repeat = not_applicable
    test_imul = not_applicable
    test_addmul = not_applicable
    test_iadd = not_applicable
    test_getslice = not_applicable
    test_contains_order = not_applicable
    test_contains_fake = not_applicable

    def test_constructors2(self):
        s = "a seq"
        vv = self.type2test(s)
        self.assertEqual(len(vv), len(s))

        # Create from various iteratables
        for s in ("123", "", list(range(1000)), (1.5, 1.2), range(2000,2200,5)):
            for g in (seq_tests.Sequence, seq_tests.IterFunc,
                      seq_tests.IterGen, seq_tests.itermulti,
                      seq_tests.iterfunc):
                self.assertEqual(self.type2test(g(s)), self.type2test(s))
            self.assertEqual(self.type2test(seq_tests.IterFuncStop(s)),
                             self.type2test())
            self.assertEqual(self.type2test(c for c in "123"),
                             self.type2test("123"))
            self.assertRaises(TypeError, self.type2test,
                              seq_tests.IterNextOnly(s))
            self.assertRaises(TypeError, self.type2test,
                              seq_tests.IterNoNext(s))
            self.assertRaises(ZeroDivisionError, self.type2test,
                              seq_tests.IterGenExc(s))

class weak_int:
    def __init__(self, v):
        self.value = v
    def unwrap(self, other):
        if isinstance(other, weak_int):
            return other.value
        return other
    def __hash__(self):
        return hash(self.value)
    def __repr__(self): # pragma: no cover
        return repr(self.value)
    def __lt__(self, other):
        return self.value < self.unwrap(other)
    def __le__(self, other):
        return self.value <= self.unwrap(other)
    def __gt__(self, other):
        return self.value > self.unwrap(other)
    def __ge__(self, other):
        return self.value >= self.unwrap(other)
    def __eq__(self, other):
        return self.value == self.unwrap(other)
    def __ne__(self, other):
        return self.value != self.unwrap(other)
    def __mod__(self, other):
        return self.value % self.unwrap(other)
    def __neg__(self):
        return weak_int(-self.value)

class weak_manager():
    def __init__(self):
        self.all = [weak_int(i) for i in range(10)]
        self.live = [v for v in self.all if random.randrange(2)]
        random.shuffle(self.all)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.all
        gc.collect()

class WeakSortedBase(SortedBase, unittest.TestCase):
    def build_items(self, n):
        return [weak_int(i) for i in range(n)]

    def build_item(self, x):
        return weak_int(x)

    def test_collapse(self):
        items = self.build_items(10)
        u = self.type2test(items)
        del items
        gc.collect()
        self.assertEqual(list(u), [])

    def test_sort(self):
        # based on list_tests.py
        x = [weak_int(i) for i in [1, 0]]
        u = self.type2test(x)
        self.assertEqual(list(u), list(reversed(x)))

        x = [weak_int(i) for i in [2,1,0,-1,-2]]
        u = self.type2test(x)
        self.assertEqual(list(u), list(reversed(x)))

        #y = [weak_int(i) for i in reversed(list(range(512)))]
        #a = self.type2test(y)
        #self.assertEqual(list(a), list(reversed(y)))

        def revcmp(a, b): # pragma: no cover
            if a == b:
                return 0
            elif a < b:
                return 1
            else: # a > b
                return -1
        u = self.type2test(u, key=CmpToKey(revcmp))
        self.assertEqual(list(u), x)

        # The following dumps core in unpatched Python 1.5:
        def myComparison(x,y):
           xmod, ymod = x%3, y%7
           if xmod == ymod:
               return 0
           elif xmod < ymod:
               return -1
           else: # xmod > ymod
               return 1
        x = [weak_int(i) for i in range(12)]
        z = self.type2test(x, key=CmpToKey(myComparison))

        self.assertRaises(TypeError, self.type2test, 42, 42, 42, 42)

    def test_constructor(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        self.assertEqual(list(wsl), m.live)

    def test_add(self):
        with weak_manager() as m:
            wsl = self.type2test()
            for x in m.all:
                wsl.add(x)
            del x
        self.assertEqual(list(wsl), m.live)

    def test_discard(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        x = m.live.pop(len(m.live)//2)
        wsl.discard(x)
        self.assertEqual(list(wsl), m.live)

    def test_contains(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        for x in m.live:
            self.assertTrue(x in wsl)
        self.assertFalse(weak_int(-1) in wsl)

    def test_iter(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        for i, x in enumerate(wsl):
            self.assertEqual(x, m.live[i])

    def test_getitem(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        for i in range(len(m.live)):
            self.assertEqual(wsl[i], m.live[i])

    def test_reversed(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        r1 = list(reversed(wsl))
        r2 = list(reversed(m.live))
        self.assertEqual(r1, r2)

        all = [weak_int(i) for i in range(6)]
        wsl = self.type2test(all)
        del all[-1]
        self.assertEqual(list(reversed(wsl)), list(reversed(all)))

    def test_index(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        for x in m.live:
            self.assertEqual(wsl[wsl.index(x)], x)
        self.assertRaises(ValueError, wsl.index, weak_int(-1))

    def test_count(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        for x in m.live:
            self.assertEqual(wsl.count(x), 1)
        self.assertEqual(wsl.count(weak_int(-1)), 0)

    def test_getslice(self):
        with weak_manager() as m:
            wsl = self.type2test(m.all)
        self.assertEqual(m.live, list(wsl[:]))

class SortedListMixin:
    def test_eq(self):
        items = self.build_items(20)
        u = self.type2test(items)
        v = self.type2test(items, key=lambda x: -x)
        self.assertNotEqual(u, v)

    def test_cmp(self):
        items = self.build_items(20)
        u = self.type2test(items)
        low = u[:10]
        high = u[10:]
        self.assert_(low != high)
        self.assert_(low == u[:10])
        self.assert_(low < high)
        self.assert_(low <= high, str((low, high)))
        self.assert_(high > low)
        self.assert_(high >= low)
        self.assertFalse(low == high)
        self.assertFalse(high < low)
        self.assertFalse(high <= low)
        self.assertFalse(low > high)
        self.assertFalse(low >= high)

        low = u[:5]
        self.assert_(low != high)
        self.assertFalse(low == high)

    def test_update(self):
        items = self.build_items(20)
        u = self.type2test()
        u.update(items)
        self.assertEqual(u, self.type2test(items))

    def test_remove(self):
        items = self.build_items(20)
        u = self.type2test(items)
        u.remove(items[-1])
        self.assertEqual(u, self.type2test(items[:19]))
        self.assertRaises(ValueError, u.remove, items[-1])

    def test_mul(self):
        items = self.build_items(2)
        u1 = self.type2test(items[:1])
        u2 = self.type2test(items)
        self.assertEqual(self.type2test(), u2*0)
        self.assertEqual(self.type2test(), 0*u2)
        self.assertEqual(self.type2test(), u2*0)
        self.assertEqual(self.type2test(), 0*u2)
        self.assertEqual(u2, u2*1)
        self.assertEqual(u2, 1*u2)
        self.assertEqual(u2, u2*1)
        self.assertEqual(u2, 1*u2)
        self.assertEqual(self.type2test(items + items), u2*2)
        self.assertEqual(self.type2test(items + items), 2*u2)
        self.assertEqual(self.type2test(items + items + items), 3*u2)
        self.assertEqual(self.type2test(items + items + items), u2*3)

        class subclass(self.type2test):
            pass
        u3 = subclass(items)
        self.assertEqual(u3, u3*1)
        self.assert_(u3 is not u3*1)

    def test_imul(self):
        items = self.build_items(2)
        items6 = items[:1]*3 + items[1:]*3
        u = self.type2test(items)
        u *= 3
        self.assertEqual(u, self.type2test(items6))
        u *= 0
        self.assertEqual(u, self.type2test([]))
        s = self.type2test([])
        oldid = id(s)
        s *= 10
        self.assertEqual(id(s), oldid)

    def test_repr(self):
        name = self.type2test.__name__
        u = self.type2test()
        self.assertEqual(repr(u), '%s()' % name)
        items = self.build_items(3)
        u.update(items)
        self.assertEqual(repr(u), '%s([0, 1, 2])' % name)
        u = self.type2test()
        u.update([u])
        self.assertEqual(repr(u), '%s([%s(...)])' % (name, name))

    def test_bisect(self):
        items = self.build_items(5)
        del items[0]
        del items[2] # We end up with [1, 2, 4]
        u = self.type2test(items, key=lambda x: -x) # We end up with [4, 2, 1]
        self.assertEqual(u.bisect_left(3), 1)
        self.assertEqual(u.bisect(2), 2) # bisect == bisect_right
        self.assertEqual(u.bisect_right(2), 2)

class SortedSetMixin:
    def test_duplicates(self):
        u = self.type2test
        ss = u()
        stuff = [weak_int(random.randrange(100000)) for i in range(10)]
        sorted_stuff = list(sorted(stuff))
        for x in stuff:
            ss.add(x)
        for x in stuff:
            ss.add(x)
        self.assertEqual(sorted_stuff, list(ss))
        x = sorted_stuff.pop(len(stuff)//2)
        ss.discard(x)
        self.assertEqual(sorted_stuff, list(ss))

    def test_eq(self):
        items = self.build_items(20)
        u = self.type2test(items)
        v = self.type2test(items, key=lambda x: -x)
        self.assertEqual(u, v)

    def test_remove(self):
        items = self.build_items(20)
        u = self.type2test(items)
        u.remove(items[-1])
        self.assertEqual(u, self.type2test(items[:19]))
        self.assertRaises(KeyError, u.remove, items[-1])

class SortedListTest(StrongSortedBase, SortedListMixin):
    type2test = blist.sortedlist

class WeakSortedListTest(WeakSortedBase, SortedListMixin):
    type2test = blist.weaksortedlist

    def test_advance(self):
        items = [weak_int(0), weak_int(0)]
        u = self.type2test(items)
        del items[0]
        gc.collect()
        self.assertEqual(u.count(items[0]), 1)

class SortedSetTest(StrongSortedBase, SortedSetMixin):
    type2test = blist.sortedset

class WeakSortedSetTest(WeakSortedBase, SortedSetMixin):
    type2test = blist.weaksortedset

    def test_repr(self):
        items = self.build_items(20)
        u = self.type2test(items)
        self.assertEqual(repr(u), 'weaksortedset(%s)' % repr(items))

########NEW FILE########
__FILENAME__ = test_list
from __future__ import print_function
from blist.test import unittest
from blist.test import test_support, list_tests

class ListTest(list_tests.CommonTest):
    type2test = list

    def test_truth(self):
        super(ListTest, self).test_truth()
        self.assert_(not [])
        self.assert_([42])

    def test_identity(self):
        self.assert_([] is not [])

    def test_len(self):
        super(ListTest, self).test_len()
        self.assertEqual(len([]), 0)
        self.assertEqual(len([0]), 1)
        self.assertEqual(len([0, 1, 2]), 3)

def test_main(verbose=None):
    test_support.run_unittest(ListTest)

    # verify reference counting
    import sys
    if verbose:
        import gc
        counts = [None] * 5
        for i in range(len(counts)):
            test_support.run_unittest(ListTest)
            gc.set_debug(gc.DEBUG_STATS)
            gc.collect()
            #counts[i] = sys.gettotalrefcount()
        print(counts)


if __name__ == "__main__":
    test_main(verbose=False)

########NEW FILE########
__FILENAME__ = test_set
# This file taken from Python, licensed under the Python License Agreement

from __future__ import print_function

import gc
import weakref
import operator
import copy
import pickle
from random import randrange, shuffle
import sys
import warnings
import collections

from blist.test import unittest
from blist.test import test_support as support

from blist import sortedset as set

class PassThru(Exception):
    pass

def check_pass_thru():
    raise PassThru
    yield 1 # pragma: no cover

class BadCmp: # pragma: no cover
    def __hash__(self):
        return 1
    def __lt__(self, other):
        raise RuntimeError
    def __eq__(self, other):
        raise RuntimeError

class ReprWrapper:
    'Used to test self-referential repr() calls'
    def __repr__(self):
        return repr(self.value)

class TestJointOps(unittest.TestCase):
    # Tests common to both set and frozenset

    def setUp(self):
        self.word = word = 'simsalabim'
        self.otherword = 'madagascar'
        self.letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.s = self.thetype(word)
        self.d = dict.fromkeys(word)

    def test_new_or_init(self):
        self.assertRaises(TypeError, self.thetype, [], 2)
        self.assertRaises(TypeError, set().__init__, a=1)

    def test_uniquification(self):
        actual = sorted(self.s)
        expected = sorted(self.d)
        self.assertEqual(actual, expected)
        self.assertRaises(PassThru, self.thetype, check_pass_thru())

    def test_len(self):
        self.assertEqual(len(self.s), len(self.d))

    def test_contains(self):
        for c in self.letters:
            self.assertEqual(c in self.s, c in self.d)
        s = self.thetype([frozenset(self.letters)])
        # Issue 8752
        #self.assertIn(self.thetype(self.letters), s)

    def test_union(self):
        u = self.s.union(self.otherword)
        for c in self.letters:
            self.assertEqual(c in u, c in self.d or c in self.otherword)
        self.assertEqual(self.s, self.thetype(self.word))
        self.assertRaises(PassThru, self.s.union, check_pass_thru())
        for C in set, frozenset, dict.fromkeys, str, list, tuple:
            self.assertEqual(self.thetype('abcba').union(C('cdc')), set('abcd'))
            self.assertEqual(self.thetype('abcba').union(C('efgfe')), set('abcefg'))
            self.assertEqual(self.thetype('abcba').union(C('ccb')), set('abc'))
            self.assertEqual(self.thetype('abcba').union(C('ef')), set('abcef'))
            self.assertEqual(self.thetype('abcba').union(C('ef'), C('fg')), set('abcefg'))

        # Issue #6573
        x = self.thetype()
        self.assertEqual(x.union(set([1]), x, set([2])), self.thetype([1, 2]))

    def test_or(self):
        i = self.s.union(self.otherword)
        self.assertEqual(self.s | set(self.otherword), i)
        self.assertEqual(self.s | frozenset(self.otherword), i)
        self.assertEqual(self.s | self.otherword, i)

    def test_intersection(self):
        i = self.s.intersection(self.otherword)
        for c in self.letters:
            self.assertEqual(c in i, c in self.d and c in self.otherword)
        self.assertEqual(self.s, self.thetype(self.word))
        self.assertRaises(PassThru, self.s.intersection, check_pass_thru())
        for C in set, frozenset, dict.fromkeys, str, list, tuple:
            self.assertEqual(self.thetype('abcba').intersection(C('cdc')), set('cc'))
            self.assertEqual(self.thetype('abcba').intersection(C('efgfe')), set(''))
            self.assertEqual(self.thetype('abcba').intersection(C('ccb')), set('bc'))
            self.assertEqual(self.thetype('abcba').intersection(C('ef')), set(''))
            self.assertEqual(self.thetype('abcba').intersection(C('cbcf'), C('bag')), set('b'))
        s = self.thetype('abcba')
        z = s.intersection()
        if self.thetype == frozenset(): # pragma: no cover
            self.assertEqual(id(s), id(z))
        else:
            self.assertNotEqual(id(s), id(z))

    def test_isdisjoint(self):
        def f(s1, s2):
            'Pure python equivalent of isdisjoint()'
            return not set(s1).intersection(s2)
        for larg in '', 'a', 'ab', 'abc', 'ababac', 'cdc', 'cc', 'efgfe', 'ccb', 'ef':
            s1 = self.thetype(larg)
            for rarg in '', 'a', 'ab', 'abc', 'ababac', 'cdc', 'cc', 'efgfe', 'ccb', 'ef':
                for C in set, frozenset, dict.fromkeys, str, list, tuple:
                    s2 = C(rarg)
                    actual = s1.isdisjoint(s2)
                    expected = f(s1, s2)
                    self.assertEqual(actual, expected)
                    self.assertTrue(actual is True or actual is False)

    def test_and(self):
        i = self.s.intersection(self.otherword)
        self.assertEqual(self.s & set(self.otherword), i)
        self.assertEqual(self.s & frozenset(self.otherword), i)
        self.assertEqual(self.s & self.otherword, i)

    def test_difference(self):
        i = self.s.difference(self.otherword)
        for c in self.letters:
            self.assertEqual(c in i, c in self.d and c not in self.otherword)
        self.assertEqual(self.s, self.thetype(self.word))
        self.assertRaises(PassThru, self.s.difference, check_pass_thru())
        for C in set, frozenset, dict.fromkeys, str, list, tuple:
            self.assertEqual(self.thetype('abcba').difference(C('cdc')), set('ab'))
            self.assertEqual(self.thetype('abcba').difference(C('efgfe')), set('abc'))
            self.assertEqual(self.thetype('abcba').difference(C('ccb')), set('a'))
            self.assertEqual(self.thetype('abcba').difference(C('ef')), set('abc'))
            self.assertEqual(self.thetype('abcba').difference(), set('abc'))
            self.assertEqual(self.thetype('abcba').difference(C('a'), C('b')), set('c'))

    def test_sub(self):
        i = self.s.difference(self.otherword)
        self.assertEqual(self.s - set(self.otherword), i)
        self.assertEqual(self.s - frozenset(self.otherword), i)
        self.assertEqual(self.s - self.otherword, i)

    def test_symmetric_difference(self):
        i = self.s.symmetric_difference(self.otherword)
        for c in self.letters:
            self.assertEqual(c in i, (c in self.d) ^ (c in self.otherword))
        self.assertEqual(self.s, self.thetype(self.word))
        self.assertRaises(PassThru, self.s.symmetric_difference, check_pass_thru())
        for C in set, frozenset, dict.fromkeys, str, list, tuple:
            self.assertEqual(self.thetype('abcba').symmetric_difference(C('cdc')), set('abd'))
            self.assertEqual(self.thetype('abcba').symmetric_difference(C('efgfe')), set('abcefg'))
            self.assertEqual(self.thetype('abcba').symmetric_difference(C('ccb')), set('a'))
            self.assertEqual(self.thetype('abcba').symmetric_difference(C('ef')), set('abcef'))

    def test_xor(self):
        i = self.s.symmetric_difference(self.otherword)
        self.assertEqual(self.s ^ set(self.otherword), i)
        self.assertEqual(self.s ^ frozenset(self.otherword), i)
        self.assertEqual(self.s ^ self.otherword, i)

    def test_equality(self):
        self.assertEqual(self.s, set(self.word))
        self.assertEqual(self.s, frozenset(self.word))
        self.assertEqual(self.s == self.word, False)
        self.assertNotEqual(self.s, set(self.otherword))
        self.assertNotEqual(self.s, frozenset(self.otherword))
        self.assertEqual(self.s != self.word, True)

    def test_setOfFrozensets(self):
        t = map(frozenset, ['abcdef', 'bcd', 'bdcb', 'fed', 'fedccba'])
        s = self.thetype(t)
        self.assertEqual(len(s), 3)

    def test_sub_and_super(self):
        p, q, r = map(self.thetype, ['ab', 'abcde', 'def'])
        self.assertTrue(p < q)
        self.assertTrue(p <= q)
        self.assertTrue(q <= q)
        self.assertTrue(q > p)
        self.assertTrue(q >= p)
        self.assertFalse(q < r)
        self.assertFalse(q <= r)
        self.assertFalse(q > r)
        self.assertFalse(q >= r)
        self.assertTrue(set('a').issubset('abc'))
        self.assertTrue(set('abc').issuperset('a'))
        self.assertFalse(set('a').issubset('cbs'))
        self.assertFalse(set('cbs').issuperset('a'))

    def test_pickling(self):
        for i in range(pickle.HIGHEST_PROTOCOL + 1):
            p = pickle.dumps(self.s, i)
            dup = pickle.loads(p)
            self.assertEqual(self.s, dup, "%s != %s" % (self.s, dup))
            if type(self.s) not in (set, frozenset):
                self.s.x = 10
                p = pickle.dumps(self.s)
                dup = pickle.loads(p)
                self.assertEqual(self.s.x, dup.x)

    def test_deepcopy(self):
        class Tracer:
            def __init__(self, value):
                self.value = value
            def __hash__(self): # pragma: no cover
                return self.value
            def __deepcopy__(self, memo=None):
                return Tracer(self.value + 1)
        t = Tracer(10)
        s = self.thetype([t])
        dup = copy.deepcopy(s)
        self.assertNotEqual(id(s), id(dup))
        for elem in dup:
            newt = elem
        self.assertNotEqual(id(t), id(newt))
        self.assertEqual(t.value + 1, newt.value)

    def test_gc(self):
        # Create a nest of cycles to exercise overall ref count check
        class A:
            def __lt__(self, other):
                return id(self) < id(other)
            def __gt__(self, other):
                return id(self) > id(other)
        s = set(A() for i in range(1000))
        for elem in s:
            elem.cycle = s
            elem.sub = elem
            elem.set = set([elem])

    def test_badcmp(self):
        s = self.thetype([BadCmp()])
        # Detect comparison errors during insertion and lookup
        self.assertRaises(RuntimeError, self.thetype, [BadCmp(), BadCmp()])
        self.assertRaises(RuntimeError, s.__contains__, BadCmp())
        # Detect errors during mutating operations
        if hasattr(s, 'add'):
            self.assertRaises(RuntimeError, s.add, BadCmp())
            self.assertRaises(RuntimeError, s.discard, BadCmp())
            self.assertRaises(RuntimeError, s.remove, BadCmp())

    def test_cyclical_repr(self):
        w = ReprWrapper()
        s = self.thetype([w])
        w.value = s
        if self.thetype == set:
            self.assertEqual(repr(s), 'sortedset([sortedset(...)])')
        else:
            name = repr(s).partition('(')[0]    # strip class name
            self.assertEqual(repr(s), '%s([%s(...)])' % (name, name))

    def test_cyclical_print(self):
        w = ReprWrapper()
        s = self.thetype([w])
        w.value = s
        fo = open(support.TESTFN, "w")
        try:
            fo.write(str(s))
            fo.close()
            fo = open(support.TESTFN, "r")
            self.assertEqual(fo.read(), repr(s))
        finally:
            fo.close()
            support.unlink(support.TESTFN)

    def test_container_iterator(self):
        # Bug #3680: tp_traverse was not implemented for set iterator object
        class C(object):
            def __lt__(self, other):
                return id(self) < id(other)
            def __gt__(self, other):
                return id(self) > id(other)
        obj = C()
        ref = weakref.ref(obj)
        container = set([obj, 1])
        obj.x = iter(container)
        del obj, container
        gc.collect()
        self.assertTrue(ref() is None, "Cycle was not collected")

class TestSet(TestJointOps):
    thetype = set
    basetype = set

    def test_init(self):
        s = self.thetype()
        s.__init__(self.word)
        self.assertEqual(s, set(self.word))
        s.__init__(self.otherword)
        self.assertEqual(s, set(self.otherword))
        self.assertRaises(TypeError, s.__init__, s, 2);
        self.assertRaises(TypeError, s.__init__, 1);

    def test_constructor_identity(self):
        s = self.thetype(range(3))
        t = self.thetype(s)
        self.assertNotEqual(id(s), id(t))

    def test_hash(self):
        self.assertRaises(TypeError, hash, self.s)

    def test_clear(self):
        self.s.clear()
        self.assertEqual(self.s, set())
        self.assertEqual(len(self.s), 0)

    def test_copy(self):
        dup = self.s.copy()
        self.assertEqual(self.s, dup)
        self.assertNotEqual(id(self.s), id(dup))
        #self.assertEqual(type(dup), self.basetype)

    def test_add(self):
        self.s.add('Q')
        self.assertIn('Q', self.s)
        dup = self.s.copy()
        self.s.add('Q')
        self.assertEqual(self.s, dup)
        #self.assertRaises(TypeError, self.s.add, [])

    def test_remove(self):
        self.s.remove('a')
        self.assertNotIn('a', self.s)
        self.assertRaises(KeyError, self.s.remove, 'Q')
        s = self.thetype([frozenset(self.word)])
        #self.assertIn(self.thetype(self.word), s)
        #s.remove(self.thetype(self.word))
        #self.assertNotIn(self.thetype(self.word), s)
        #self.assertRaises(KeyError, self.s.remove, self.thetype(self.word))

    def test_remove_keyerror_unpacking(self):
        # bug:  www.python.org/sf/1576657
        for v1 in ['Q', (1,)]:
            try:
                self.s.remove(v1)
            except KeyError as e:
                v2 = e.args[0]
                self.assertEqual(v1, v2)
            else: # pragma: no cover
                self.fail()

    def test_remove_keyerror_set(self):
        key = self.thetype([3, 4])
        try:
            self.s.remove(key)
        except KeyError as e:
            self.assertTrue(e.args[0] is key,
                         "KeyError should be {0}, not {1}".format(key,
                                                                  e.args[0]))
        else: # pragma: no cover
            self.fail()

    def test_discard(self):
        self.s.discard('a')
        self.assertNotIn('a', self.s)
        self.s.discard('Q')
        #self.assertRaises(TypeError, self.s.discard, [])
        s = self.thetype([frozenset(self.word)])
        #self.assertIn(self.thetype(self.word), s)
        #s.discard(self.thetype(self.word))
        #self.assertNotIn(self.thetype(self.word), s)
        #s.discard(self.thetype(self.word))

    def test_pop(self):
        for i in range(len(self.s)):
            elem = self.s.pop()
            self.assertNotIn(elem, self.s)
        self.assertRaises(IndexError, self.s.pop)

    def test_update(self):
        retval = self.s.update(self.otherword)
        self.assertEqual(retval, None)
        for c in (self.word + self.otherword):
            self.assertIn(c, self.s)
        self.assertRaises(PassThru, self.s.update, check_pass_thru())
        self.assertRaises(TypeError, self.s.update, 6)
        for p, q in (('cdc', 'abcd'), ('efgfe', 'abcefg'), ('ccb', 'abc'), ('ef', 'abcef')):
            for C in set, frozenset, dict.fromkeys, str, list, tuple:
                s = self.thetype('abcba')
                self.assertEqual(s.update(C(p)), None)
                self.assertEqual(s, set(q))
        for p in ('cdc', 'efgfe', 'ccb', 'ef', 'abcda'):
            q = 'ahi'
            for C in set, frozenset, dict.fromkeys, str, list, tuple:
                s = self.thetype('abcba')
                self.assertEqual(s.update(C(p), C(q)), None)
                self.assertEqual(s, set(s) | set(p) | set(q))

    def test_ior(self):
        self.s |= set(self.otherword)
        for c in (self.word + self.otherword):
            self.assertIn(c, self.s)

    def test_intersection_update(self):
        retval = self.s.intersection_update(self.otherword)
        self.assertEqual(retval, None)
        for c in (self.word + self.otherword):
            if c in self.otherword and c in self.word:
                self.assertIn(c, self.s)
            else:
                self.assertNotIn(c, self.s)
        self.assertRaises(PassThru, self.s.intersection_update, check_pass_thru())
        self.assertRaises(TypeError, self.s.intersection_update, 6)
        for p, q in (('cdc', 'c'), ('efgfe', ''), ('ccb', 'bc'), ('ef', '')):
            for C in set, frozenset, dict.fromkeys, str, list, tuple:
                s = self.thetype('abcba')
                self.assertEqual(s.intersection_update(C(p)), None)
                self.assertEqual(s, set(q))
                ss = 'abcba'
                s = self.thetype(ss)
                t = 'cbc'
                self.assertEqual(s.intersection_update(C(p), C(t)), None)
                self.assertEqual(s, set('abcba')&set(p)&set(t))

    def test_iand(self):
        self.s &= set(self.otherword)
        for c in (self.word + self.otherword):
            if c in self.otherword and c in self.word:
                self.assertIn(c, self.s)
            else:
                self.assertNotIn(c, self.s)

    def test_difference_update(self):
        retval = self.s.difference_update(self.otherword)
        self.assertEqual(retval, None)
        for c in (self.word + self.otherword):
            if c in self.word and c not in self.otherword:
                self.assertIn(c, self.s)
            else:
                self.assertNotIn(c, self.s)
        self.assertRaises(PassThru, self.s.difference_update, check_pass_thru())
        self.assertRaises(TypeError, self.s.difference_update, 6)
        self.assertRaises(TypeError, self.s.symmetric_difference_update, 6)
        for p, q in (('cdc', 'ab'), ('efgfe', 'abc'), ('ccb', 'a'), ('ef', 'abc')):
            for C in set, frozenset, dict.fromkeys, str, list, tuple:
                s = self.thetype('abcba')
                self.assertEqual(s.difference_update(C(p)), None)
                self.assertEqual(s, set(q))

                s = self.thetype('abcdefghih')
                s.difference_update()
                self.assertEqual(s, self.thetype('abcdefghih'))

                s = self.thetype('abcdefghih')
                s.difference_update(C('aba'))
                self.assertEqual(s, self.thetype('cdefghih'))

                s = self.thetype('abcdefghih')
                s.difference_update(C('cdc'), C('aba'))
                self.assertEqual(s, self.thetype('efghih'))

    def test_isub(self):
        self.s -= set(self.otherword)
        for c in (self.word + self.otherword):
            if c in self.word and c not in self.otherword:
                self.assertIn(c, self.s)
            else:
                self.assertNotIn(c, self.s)

    def test_symmetric_difference_update(self):
        retval = self.s.symmetric_difference_update(self.otherword)
        self.assertEqual(retval, None)
        for c in (self.word + self.otherword):
            if (c in self.word) ^ (c in self.otherword):
                self.assertIn(c, self.s)
            else:
                self.assertNotIn(c, self.s)
        self.assertRaises(PassThru, self.s.symmetric_difference_update, check_pass_thru())
        self.assertRaises(TypeError, self.s.symmetric_difference_update, 6)
        for p, q in (('cdc', 'abd'), ('efgfe', 'abcefg'), ('ccb', 'a'), ('ef', 'abcef')):
            for C in set, frozenset, dict.fromkeys, str, list, tuple:
                s = self.thetype('abcba')
                self.assertEqual(s.symmetric_difference_update(C(p)), None)
                self.assertEqual(s, set(q))

    def test_ixor(self):
        self.s ^= set(self.otherword)
        for c in (self.word + self.otherword):
            if (c in self.word) ^ (c in self.otherword):
                self.assertIn(c, self.s)
            else:
                self.assertNotIn(c, self.s)

    def test_inplace_on_self(self):
        t = self.s.copy()
        t |= t
        self.assertEqual(t, self.s)
        t &= t
        self.assertEqual(t, self.s)
        t -= t
        self.assertEqual(t, self.thetype())
        t = self.s.copy()
        t ^= t
        self.assertEqual(t, self.thetype())

    def test_weakref(self):
        s = self.thetype('gallahad')
        p = weakref.proxy(s)
        self.assertEqual(str(p), str(s))
        s = None
        self.assertRaises(ReferenceError, str, p)

    def test_rich_compare(self): # pragma: no cover
        if sys.version_info[0] < 3:
            return

        class TestRichSetCompare:
            def __gt__(self, some_set):
                self.gt_called = True
                return False
            def __lt__(self, some_set):
                self.lt_called = True
                return False
            def __ge__(self, some_set):
                self.ge_called = True
                return False
            def __le__(self, some_set):
                self.le_called = True
                return False

        # This first tries the bulitin rich set comparison, which doesn't know
        # how to handle the custom object. Upon returning NotImplemented, the
        # corresponding comparison on the right object is invoked.
        myset = set((1, 2, 3))

        myobj = TestRichSetCompare()
        myset < myobj
        self.assertTrue(myobj.gt_called)

        myobj = TestRichSetCompare()
        myset > myobj
        self.assertTrue(myobj.lt_called)

        myobj = TestRichSetCompare()
        myset <= myobj
        self.assertTrue(myobj.ge_called)

        myobj = TestRichSetCompare()
        myset >= myobj
        self.assertTrue(myobj.le_called)

class SetSubclass(set):
    pass

class TestSetSubclass(TestSet):
    thetype = SetSubclass
    basetype = set

class SetSubclassWithKeywordArgs(set):
    def __init__(self, iterable=[], newarg=None):
        set.__init__(self, iterable)

class TestSetSubclassWithKeywordArgs(TestSet):

    def test_keywords_in_subclass(self):
        'SF bug #1486663 -- this used to erroneously raise a TypeError'
        SetSubclassWithKeywordArgs(newarg=1)

# Tests taken from test_sets.py =============================================

empty_set = set()

#==============================================================================

class TestBasicOps(unittest.TestCase):

    def test_repr(self):
        if self.repr is not None:
            self.assertEqual(repr(self.set), self.repr)

    def test_print(self):
        try:
            fo = open(support.TESTFN, "w")
            fo.write(str(self.set))
            fo.close()
            fo = open(support.TESTFN, "r")
            self.assertEqual(fo.read(), repr(self.set))
        finally:
            fo.close()
            support.unlink(support.TESTFN)

    def test_length(self):
        self.assertEqual(len(self.set), self.length)

    def test_self_equality(self):
        self.assertEqual(self.set, self.set)

    def test_equivalent_equality(self):
        self.assertEqual(self.set, self.dup)

    def test_copy(self):
        self.assertEqual(self.set.copy(), self.dup)

    def test_self_union(self):
        result = self.set | self.set
        self.assertEqual(result, self.dup)

    def test_empty_union(self):
        result = self.set | empty_set
        self.assertEqual(result, self.dup)

    def test_union_empty(self):
        result = empty_set | self.set
        self.assertEqual(result, self.dup)

    def test_self_intersection(self):
        result = self.set & self.set
        self.assertEqual(result, self.dup)

    def test_empty_intersection(self):
        result = self.set & empty_set
        self.assertEqual(result, empty_set)

    def test_intersection_empty(self):
        result = empty_set & self.set
        self.assertEqual(result, empty_set)

    def test_self_isdisjoint(self):
        result = self.set.isdisjoint(self.set)
        self.assertEqual(result, not self.set)

    def test_empty_isdisjoint(self):
        result = self.set.isdisjoint(empty_set)
        self.assertEqual(result, True)

    def test_isdisjoint_empty(self):
        result = empty_set.isdisjoint(self.set)
        self.assertEqual(result, True)

    def test_self_symmetric_difference(self):
        result = self.set ^ self.set
        self.assertEqual(result, empty_set)

    def test_checkempty_symmetric_difference(self):
        result = self.set ^ empty_set
        self.assertEqual(result, self.set)

    def test_self_difference(self):
        result = self.set - self.set
        self.assertEqual(result, empty_set)

    def test_empty_difference(self):
        result = self.set - empty_set
        self.assertEqual(result, self.dup)

    def test_empty_difference_rev(self):
        result = empty_set - self.set
        self.assertEqual(result, empty_set)

    def test_iteration(self):
        for v in self.set:
            self.assertIn(v, self.values)
        setiter = iter(self.set)
        # note: __length_hint__ is an internal undocumented API,
        # don't rely on it in your own programs
        #self.assertEqual(setiter.__length_hint__(), len(self.set))

    def test_pickling(self):
        p = pickle.dumps(self.set)
        copy = pickle.loads(p)
        self.assertEqual(self.set, copy,
                         "%s != %s" % (self.set, copy))

#------------------------------------------------------------------------------

class TestBasicOpsEmpty(TestBasicOps):
    def setUp(self):
        self.case   = "empty set"
        self.values = []
        self.set    = set(self.values)
        self.dup    = set(self.values)
        self.length = 0
        self.repr   = "sortedset()"

#------------------------------------------------------------------------------

class TestBasicOpsSingleton(TestBasicOps):
    def setUp(self):
        self.case   = "unit set (number)"
        self.values = [3]
        self.set    = set(self.values)
        self.dup    = set(self.values)
        self.length = 1
        self.repr   = "sortedset([3])"

    def test_in(self):
        self.assertIn(3, self.set)

    def test_not_in(self):
        self.assertNotIn(2, self.set)

#------------------------------------------------------------------------------

class TestBasicOpsTuple(TestBasicOps):
    def setUp(self):
        self.case   = "unit set (tuple)"
        self.values = [(0, 1)]
        self.set    = set(self.values)
        self.dup    = set(self.values)
        self.length = 1
        self.repr   = "sortedset([(0, 1)])"

    def test_in(self):
        self.assertIn((0, 1), self.set)

    def test_not_in(self):
        self.assertNotIn(9, self.set)

#------------------------------------------------------------------------------

class TestBasicOpsTriple(TestBasicOps):
    def setUp(self):
        self.case   = "triple set"
        self.values = [0, 1, 2]
        self.set    = set(self.values)
        self.dup    = set(self.values)
        self.length = 3
        self.repr   = None

#------------------------------------------------------------------------------

class TestBasicOpsString(TestBasicOps):
    def setUp(self):
        self.case   = "string set"
        self.values = ["a", "b", "c"]
        self.set    = set(self.values)
        self.dup    = set(self.values)
        self.length = 3
        self.repr   = "sortedset(['a', 'b', 'c'])"

#------------------------------------------------------------------------------

def baditer():
    raise TypeError
    yield True # pragma: no cover

def gooditer():
    yield True

class TestExceptionPropagation(unittest.TestCase):
    """SF 628246:  Set constructor should not trap iterator TypeErrors"""

    def test_instanceWithException(self):
        self.assertRaises(TypeError, set, baditer())

    def test_instancesWithoutException(self):
        # All of these iterables should load without exception.
        set([1,2,3])
        set((1,2,3))
        set({'one':1, 'two':2, 'three':3})
        set(range(3))
        set('abc')
        set(gooditer())

    def test_changingSizeWhileIterating(self):
        s = set([1,2,3])
        try:
            for i in s:
                s.update([4])
        except RuntimeError:
            pass
        else: # pragma: no cover
            self.fail("no exception when changing size during iteration")

#==============================================================================

class TestSetOfSets(unittest.TestCase):
    def test_constructor(self):
        inner = frozenset([1])
        outer = set([inner])
        element = outer.pop()
        self.assertEqual(type(element), frozenset)
        outer.add(inner)        # Rebuild set of sets with .add method
        outer.remove(inner)
        self.assertEqual(outer, set())   # Verify that remove worked
        outer.discard(inner)    # Absence of KeyError indicates working fine

#==============================================================================

class TestBinaryOps(unittest.TestCase):
    def setUp(self):
        self.set = set((2, 4, 6))

    def test_eq(self):              # SF bug 643115
        self.assertEqual(self.set, set({2:1,4:3,6:5}))

    def test_union_subset(self):
        result = self.set | set([2])
        self.assertEqual(result, set((2, 4, 6)))

    def test_union_superset(self):
        result = self.set | set([2, 4, 6, 8])
        self.assertEqual(result, set([2, 4, 6, 8]))

    def test_union_overlap(self):
        result = self.set | set([3, 4, 5])
        self.assertEqual(result, set([2, 3, 4, 5, 6]))

    def test_union_non_overlap(self):
        result = self.set | set([8])
        self.assertEqual(result, set([2, 4, 6, 8]))

    def test_intersection_subset(self):
        result = self.set & set((2, 4))
        self.assertEqual(result, set((2, 4)))

    def test_intersection_superset(self):
        result = self.set & set([2, 4, 6, 8])
        self.assertEqual(result, set([2, 4, 6]))

    def test_intersection_overlap(self):
        result = self.set & set([3, 4, 5])
        self.assertEqual(result, set([4]))

    def test_intersection_non_overlap(self):
        result = self.set & set([8])
        self.assertEqual(result, empty_set)

    def test_isdisjoint_subset(self):
        result = self.set.isdisjoint(set((2, 4)))
        self.assertEqual(result, False)

    def test_isdisjoint_superset(self):
        result = self.set.isdisjoint(set([2, 4, 6, 8]))
        self.assertEqual(result, False)

    def test_isdisjoint_overlap(self):
        result = self.set.isdisjoint(set([3, 4, 5]))
        self.assertEqual(result, False)

    def test_isdisjoint_non_overlap(self):
        result = self.set.isdisjoint(set([8]))
        self.assertEqual(result, True)

    def test_sym_difference_subset(self):
        result = self.set ^ set((2, 4))
        self.assertEqual(result, set([6]))

    def test_sym_difference_superset(self):
        result = self.set ^ set((2, 4, 6, 8))
        self.assertEqual(result, set([8]))

    def test_sym_difference_overlap(self):
        result = self.set ^ set((3, 4, 5))
        self.assertEqual(result, set([2, 3, 5, 6]))

    def test_sym_difference_non_overlap(self):
        result = self.set ^ set([8])
        self.assertEqual(result, set([2, 4, 6, 8]))

#==============================================================================

class TestUpdateOps(unittest.TestCase):
    def setUp(self):
        self.set = set((2, 4, 6))

    def test_union_subset(self):
        self.set |= set([2])
        self.assertEqual(self.set, set((2, 4, 6)))

    def test_union_superset(self):
        self.set |= set([2, 4, 6, 8])
        self.assertEqual(self.set, set([2, 4, 6, 8]))

    def test_union_overlap(self):
        self.set |= set([3, 4, 5])
        self.assertEqual(self.set, set([2, 3, 4, 5, 6]))

    def test_union_non_overlap(self):
        self.set |= set([8])
        self.assertEqual(self.set, set([2, 4, 6, 8]))

    def test_union_method_call(self):
        self.set.update(set([3, 4, 5]))
        self.assertEqual(self.set, set([2, 3, 4, 5, 6]))

    def test_intersection_subset(self):
        self.set &= set((2, 4))
        self.assertEqual(self.set, set((2, 4)))

    def test_intersection_superset(self):
        self.set &= set([2, 4, 6, 8])
        self.assertEqual(self.set, set([2, 4, 6]))

    def test_intersection_overlap(self):
        self.set &= set([3, 4, 5])
        self.assertEqual(self.set, set([4]))

    def test_intersection_non_overlap(self):
        self.set &= set([8])
        self.assertEqual(self.set, empty_set)

    def test_intersection_method_call(self):
        self.set.intersection_update(set([3, 4, 5]))
        self.assertEqual(self.set, set([4]))

    def test_sym_difference_subset(self):
        self.set ^= set((2, 4))
        self.assertEqual(self.set, set([6]))

    def test_sym_difference_superset(self):
        self.set ^= set((2, 4, 6, 8))
        self.assertEqual(self.set, set([8]))

    def test_sym_difference_overlap(self):
        self.set ^= set((3, 4, 5))
        self.assertEqual(self.set, set([2, 3, 5, 6]))

    def test_sym_difference_non_overlap(self):
        self.set ^= set([8])
        self.assertEqual(self.set, set([2, 4, 6, 8]))

    def test_sym_difference_method_call(self):
        self.set.symmetric_difference_update(set([3, 4, 5]))
        self.assertEqual(self.set, set([2, 3, 5, 6]))

    def test_difference_subset(self):
        self.set -= set((2, 4))
        self.assertEqual(self.set, set([6]))

    def test_difference_superset(self):
        self.set -= set((2, 4, 6, 8))
        self.assertEqual(self.set, set([]))

    def test_difference_overlap(self):
        self.set -= set((3, 4, 5))
        self.assertEqual(self.set, set([2, 6]))

    def test_difference_non_overlap(self):
        self.set -= set([8])
        self.assertEqual(self.set, set([2, 4, 6]))

    def test_difference_method_call(self):
        self.set.difference_update(set([3, 4, 5]))
        self.assertEqual(self.set, set([2, 6]))

#==============================================================================

class TestMutate(unittest.TestCase):
    def setUp(self):
        self.values = ["a", "b", "c"]
        self.set = set(self.values)

    def test_add_present(self):
        self.set.add("c")
        self.assertEqual(self.set, set("abc"))

    def test_add_absent(self):
        self.set.add("d")
        self.assertEqual(self.set, set("abcd"))

    def test_add_until_full(self):
        tmp = set()
        expected_len = 0
        for v in self.values:
            tmp.add(v)
            expected_len += 1
            self.assertEqual(len(tmp), expected_len)
        self.assertEqual(tmp, self.set)

    def test_remove_present(self):
        self.set.remove("b")
        self.assertEqual(self.set, set("ac"))

    def test_remove_absent(self):
        try:
            self.set.remove("d")
            self.fail("Removing missing element should have raised LookupError") # pragma: no cover
        except LookupError:
            pass

    def test_remove_until_empty(self):
        expected_len = len(self.set)
        for v in self.values:
            self.set.remove(v)
            expected_len -= 1
            self.assertEqual(len(self.set), expected_len)

    def test_discard_present(self):
        self.set.discard("c")
        self.assertEqual(self.set, set("ab"))

    def test_discard_absent(self):
        self.set.discard("d")
        self.assertEqual(self.set, set("abc"))

    def test_clear(self):
        self.set.clear()
        self.assertEqual(len(self.set), 0)

    def test_pop(self):
        popped = {}
        while self.set:
            popped[self.set.pop()] = None
        self.assertEqual(len(popped), len(self.values))
        for v in self.values:
            self.assertIn(v, popped)

    def test_update_empty_tuple(self):
        self.set.update(())
        self.assertEqual(self.set, set(self.values))

    def test_update_unit_tuple_overlap(self):
        self.set.update(("a",))
        self.assertEqual(self.set, set(self.values))

    def test_update_unit_tuple_non_overlap(self):
        self.set.update(("a", "z"))
        self.assertEqual(self.set, set(self.values + ["z"]))

#==============================================================================

class TestSubsets(unittest.TestCase):

    case2method = {"<=": "issubset",
                   ">=": "issuperset",
                  }

    reverse = {"==": "==",
               "!=": "!=",
               "<":  ">",
               ">":  "<",
               "<=": ">=",
               ">=": "<=",
              }

    def test_issubset(self):
        x = self.left
        y = self.right
        for case in "!=", "==", "<", "<=", ">", ">=":
            expected = case in self.cases
            # Test the binary infix spelling.
            result = eval("x" + case + "y", locals())
            self.assertEqual(result, expected)
            # Test the "friendly" method-name spelling, if one exists.
            if case in TestSubsets.case2method:
                method = getattr(x, TestSubsets.case2method[case])
                result = method(y)
                self.assertEqual(result, expected)

            # Now do the same for the operands reversed.
            rcase = TestSubsets.reverse[case]
            result = eval("y" + rcase + "x", locals())
            self.assertEqual(result, expected)
            if rcase in TestSubsets.case2method:
                method = getattr(y, TestSubsets.case2method[rcase])
                result = method(x)
                self.assertEqual(result, expected)
#------------------------------------------------------------------------------

class TestSubsetEqualEmpty(TestSubsets):
    left  = set()
    right = set()
    name  = "both empty"
    cases = "==", "<=", ">="

#------------------------------------------------------------------------------

class TestSubsetEqualNonEmpty(TestSubsets):
    left  = set([1, 2])
    right = set([1, 2])
    name  = "equal pair"
    cases = "==", "<=", ">="

#------------------------------------------------------------------------------

class TestSubsetEmptyNonEmpty(TestSubsets):
    left  = set()
    right = set([1, 2])
    name  = "one empty, one non-empty"
    cases = "!=", "<", "<="

#------------------------------------------------------------------------------

class TestSubsetPartial(TestSubsets):
    left  = set([1])
    right = set([1, 2])
    name  = "one a non-empty proper subset of other"
    cases = "!=", "<", "<="

#------------------------------------------------------------------------------

class TestSubsetNonOverlap(TestSubsets):
    left  = set([1])
    right = set([2])
    name  = "neither empty, neither contains"
    cases = "!="

#==============================================================================

class TestOnlySetsInBinaryOps(unittest.TestCase):

    def test_eq_ne(self):
        # Unlike the others, this is testing that == and != *are* allowed.
        self.assertEqual(self.other == self.set, False)
        self.assertEqual(self.set == self.other, False)
        self.assertEqual(self.other != self.set, True)
        self.assertEqual(self.set != self.other, True)

    def test_ge_gt_le_lt(self):
        self.assertRaises(TypeError, lambda: self.set < self.other)
        self.assertRaises(TypeError, lambda: self.set <= self.other)
        self.assertRaises(TypeError, lambda: self.set > self.other)
        self.assertRaises(TypeError, lambda: self.set >= self.other)

        self.assertRaises(TypeError, lambda: self.other < self.set)
        self.assertRaises(TypeError, lambda: self.other <= self.set)
        self.assertRaises(TypeError, lambda: self.other > self.set)
        self.assertRaises(TypeError, lambda: self.other >= self.set)

    def test_update_operator(self):
        if self.otherIsIterable:
            self.set |= self.other
        else:
            try:
                self.set |= self.other
            except TypeError:
                pass
            else: # pragma: no cover
                self.fail("expected TypeError")

    def test_update(self):
        if self.otherIsIterable:
            self.set.update(self.other)
        else:
            self.assertRaises(TypeError, self.set.update, self.other)

    def test_union(self):
        if self.otherIsIterable:
            self.set | self.other
            self.other | self.set
            self.set.union(self.other)
        else:
            self.assertRaises(TypeError, lambda: self.set | self.other)
            self.assertRaises(TypeError, lambda: self.other | self.set)
            self.assertRaises(TypeError, self.set.union, self.other)

    def test_intersection_update_operator(self):
        if self.otherIsIterable:
            self.set &= self.other
        else:
            try:
                self.set &= self.other
            except TypeError:
                pass
            else: # pragma: no cover
                self.fail("expected TypeError")

    def test_intersection_update(self):
        if self.otherIsIterable:
            self.set.intersection_update(self.other)
        else:
            self.assertRaises(TypeError,
                              self.set.intersection_update,
                              self.other)

    def test_intersection(self):
        if self.otherIsIterable:
            self.set & self.other
            self.other & self.set
            self.set.intersection(self.other)
        else:
            self.assertRaises(TypeError, lambda: self.set & self.other)
            self.assertRaises(TypeError, lambda: self.other & self.set)
            self.assertRaises(TypeError, self.set.intersection, self.other)

    def test_sym_difference_update_operator(self):
        if self.otherIsIterable:
            self.set ^= self.other
        else:
            try:
                self.set ^= self.other
            except TypeError:
                pass
            else: # pragma: no cover
                self.fail("expected TypeError")

    def test_sym_difference_update(self):
        if self.otherIsIterable:
            self.set.symmetric_difference_update(self.other)
        else:
            self.assertRaises(TypeError,
                              self.set.symmetric_difference_update,
                              self.other)

    def test_sym_difference(self):
        if self.otherIsIterable:
            self.set ^ self.other
            self.other ^ self.set
            self.set.symmetric_difference(self.other)
        else:
            self.assertRaises(TypeError, lambda: self.set ^ self.other)
            self.assertRaises(TypeError, lambda: self.other ^ self.set)
            self.assertRaises(TypeError, self.set.symmetric_difference, self.other)

    def test_difference_update_operator(self):
        if self.otherIsIterable:
            self.set -= self.other
        else:
            try:
                self.set -= self.other
            except TypeError:
                pass
            else: # pragma: no cover
                self.fail("expected TypeError")

    def test_difference_update(self):
        if self.otherIsIterable:
            self.set.difference_update(self.other)
        else:
            self.assertRaises(TypeError,
                              self.set.difference_update,
                              self.other)

    def test_difference(self):
        if self.otherIsIterable:
            self.set - self.other
            self.other - self.set
            self.set.difference(self.other)
        else:
            self.assertRaises(TypeError, lambda: self.set - self.other)
            self.assertRaises(TypeError, lambda: self.other - self.set)
            self.assertRaises(TypeError, self.set.difference, self.other)

#------------------------------------------------------------------------------

class TestOnlySetsNumeric(TestOnlySetsInBinaryOps):
    def setUp(self):
        self.set   = set((1, 2, 3))
        self.other = 19
        self.otherIsIterable = False

#------------------------------------------------------------------------------

class TestOnlySetsDict(TestOnlySetsInBinaryOps):
    def setUp(self):
        self.set   = set((1, 2, 3))
        self.other = {1:2, 3:4}
        self.otherIsIterable = True

#------------------------------------------------------------------------------

class TestOnlySetsOperator(TestOnlySetsInBinaryOps):
    def setUp(self):
        self.set   = set((1, 2, 3))
        self.other = operator.add
        self.otherIsIterable = False

#------------------------------------------------------------------------------

class TestOnlySetsTuple(TestOnlySetsInBinaryOps):
    def setUp(self):
        self.set   = set((1, 2, 3))
        self.other = (2, 4, 6)
        self.otherIsIterable = True

#------------------------------------------------------------------------------

class TestOnlySetsString(TestOnlySetsInBinaryOps):
    def setUp(self):
        self.set   = set('xyz')
        self.other = 'abc'
        self.otherIsIterable = True

#------------------------------------------------------------------------------

class TestOnlySetsGenerator(TestOnlySetsInBinaryOps):
    def setUp(self):
        def gen():
            for i in range(0, 10, 2):
                yield i
        self.set   = set((1, 2, 3))
        self.other = gen()
        self.otherIsIterable = True

#==============================================================================

class TestCopying(unittest.TestCase):

    def test_copy(self):
        dup = self.set.copy()
        dup_list = sorted(dup, key=repr)
        set_list = sorted(self.set, key=repr)
        self.assertEqual(len(dup_list), len(set_list))
        for i in range(len(dup_list)):
            self.assertTrue(dup_list[i] is set_list[i])

    def test_deep_copy(self):
        dup = copy.deepcopy(self.set)
        ##print type(dup), repr(dup)
        dup_list = sorted(dup, key=repr)
        set_list = sorted(self.set, key=repr)
        self.assertEqual(len(dup_list), len(set_list))
        for i in range(len(dup_list)):
            self.assertEqual(dup_list[i], set_list[i])

#------------------------------------------------------------------------------

class TestCopyingEmpty(TestCopying):
    def setUp(self):
        self.set = set()

#------------------------------------------------------------------------------

class TestCopyingSingleton(TestCopying):
    def setUp(self):
        self.set = set(["hello"])

#------------------------------------------------------------------------------

class TestCopyingTriple(TestCopying):
    def setUp(self):
        self.set = set([-1, 0, 1])

#------------------------------------------------------------------------------

class TestCopyingTuple(TestCopying):
    def setUp(self):
        self.set = set([(1, 2)])

#------------------------------------------------------------------------------

class TestCopyingNested(TestCopying):
    def setUp(self):
        self.set = set([((1, 2), (3, 4))])

#==============================================================================

class TestIdentities(unittest.TestCase):
    def setUp(self):
        self.a = set('abracadabra')
        self.b = set('alacazam')

    def test_binopsVsSubsets(self):
        a, b = self.a, self.b
        self.assertTrue(a - b < a)
        self.assertTrue(b - a < b)
        self.assertTrue(a & b < a)
        self.assertTrue(a & b < b)
        self.assertTrue(a | b > a)
        self.assertTrue(a | b > b)
        self.assertTrue(a ^ b < a | b)

    def test_commutativity(self):
        a, b = self.a, self.b
        self.assertEqual(a&b, b&a)
        self.assertEqual(a|b, b|a)
        self.assertEqual(a^b, b^a)
        if a != b:
            self.assertNotEqual(a-b, b-a)

    def test_summations(self):
        # check that sums of parts equal the whole
        a, b = self.a, self.b
        self.assertEqual((a-b)|(a&b)|(b-a), a|b)
        self.assertEqual((a&b)|(a^b), a|b)
        self.assertEqual(a|(b-a), a|b)
        self.assertEqual((a-b)|b, a|b)
        self.assertEqual((a-b)|(a&b), a)
        self.assertEqual((b-a)|(a&b), b)
        self.assertEqual((a-b)|(b-a), a^b)

    def test_exclusion(self):
        # check that inverse operations show non-overlap
        a, b, zero = self.a, self.b, set()
        self.assertEqual((a-b)&b, zero)
        self.assertEqual((b-a)&a, zero)
        self.assertEqual((a&b)&(a^b), zero)

# Tests derived from test_itertools.py =======================================

def R(seqn):
    'Regular generator'
    for i in seqn:
        yield i

class G:
    'Sequence using __getitem__'
    def __init__(self, seqn):
        self.seqn = seqn
    def __getitem__(self, i):
        return self.seqn[i]

class I:
    'Sequence using iterator protocol'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.i >= len(self.seqn): raise StopIteration
        v = self.seqn[self.i]
        self.i += 1
        return v
    next = __next__

class Ig:
    'Sequence using iterator protocol defined with a generator'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        for val in self.seqn:
            yield val

class X:
    'Missing __getitem__ and __iter__'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __next__(self): # pragma: no cover
        if self.i >= len(self.seqn): raise StopIteration
        v = self.seqn[self.i]
        self.i += 1
        return v
    next = __next__

class N:
    'Iterator missing __next__()'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        return self

class E:
    'Test propagation of exceptions'
    def __init__(self, seqn):
        self.seqn = seqn
        self.i = 0
    def __iter__(self):
        return self
    def __next__(self):
        3 // 0
    next = __next__

class S:
    'Test immediate stop'
    def __init__(self, seqn):
        pass
    def __iter__(self):
        return self
    def __next__(self):
        raise StopIteration
    next = __next__

from itertools import chain
def L(seqn):
    'Test multiple tiers of iterators'
    return chain(map(lambda x:x, R(Ig(G(seqn)))))

class TestVariousIteratorArgs(unittest.TestCase):

    def test_constructor(self):
        for cons in (set,):
            for s in (range(3), (), range(1000), (1.1, 1.2), range(2000,2200,5), range(10)):
                for g in (G, I, Ig, S, L, R):
                    self.assertEqual(sorted(cons(g(s)), key=repr), sorted(g(s), key=repr))
                self.assertRaises(TypeError, cons , X(s))
                self.assertRaises(TypeError, cons , N(s))
                self.assertRaises(ZeroDivisionError, cons , E(s))

    def test_inline_methods(self):
        s = set([-1,-2,-3])
        for data in (range(3), (), range(1000), (1.1, 1.2), range(2000,2200,5), range(10)):
            for meth in (s.union, s.intersection, s.difference, s.symmetric_difference, s.isdisjoint):
                for g in (G, I, Ig, L, R):
                    expected = meth(data)
                    actual = meth(G(data))
                    if isinstance(expected, bool):
                        self.assertEqual(actual, expected)
                    else:
                        self.assertEqual(sorted(actual, key=repr), sorted(expected, key=repr))
                self.assertRaises(TypeError, meth, X(s))
                self.assertRaises(TypeError, meth, N(s))
                self.assertRaises(ZeroDivisionError, meth, E(s))

    def test_inplace_methods(self):
        for data in (range(3), (), range(1000), (1.1, 1.2), range(2000,2200,5), range(10)):
            for methname in ('update', 'intersection_update',
                             'difference_update', 'symmetric_difference_update'):
                for g in (G, I, Ig, S, L, R):
                    s = set([1,2,3])
                    t = s.copy()
                    getattr(s, methname)(list(g(data)))
                    getattr(t, methname)(g(data))
                    self.assertEqual(sorted(s, key=repr), sorted(t, key=repr))

                self.assertRaises(TypeError, getattr(set([1,2,3]), methname), X(data))
                self.assertRaises(TypeError, getattr(set([1,2,3]), methname), N(data))
                self.assertRaises(ZeroDivisionError, getattr(set([1,2,3]), methname), E(data))

#==============================================================================

test_classes = (
        TestSet,
        TestSetSubclass,
        TestSetSubclassWithKeywordArgs,
        TestSetOfSets,
        TestExceptionPropagation,
        TestBasicOpsEmpty,
        TestBasicOpsSingleton,
        TestBasicOpsTuple,
        TestBasicOpsTriple,
        TestBasicOpsString,
        TestBinaryOps,
        TestUpdateOps,
        TestMutate,
        TestSubsetEqualEmpty,
        TestSubsetEqualNonEmpty,
        TestSubsetEmptyNonEmpty,
        TestSubsetPartial,
        TestSubsetNonOverlap,
        TestOnlySetsNumeric,
        TestOnlySetsDict,
        TestOnlySetsOperator,
        TestOnlySetsTuple,
        TestOnlySetsString,
        TestOnlySetsGenerator,
        TestCopyingEmpty,
        TestCopyingSingleton,
        TestCopyingTriple,
        TestCopyingTuple,
        TestCopyingNested,
        TestIdentities,
        TestVariousIteratorArgs,
        )

########NEW FILE########
__FILENAME__ = test_support
# This file taken from Python, licensed under the Python License Agreement

from __future__ import print_function
"""Supporting definitions for the Python regression tests."""

if __name__ != 'blist.test.test_support':
    raise ImportError('test_support must be imported from the test package')

import sys

class Error(Exception):
    """Base class for regression test exceptions."""

class TestFailed(Error):
    """Test failed."""

class TestSkipped(Error):
    """Test skipped.

    This can be raised to indicate that a test was deliberatly
    skipped, but not because a feature wasn't available.  For
    example, if some resource can't be used, such as the network
    appears to be unavailable, this should be raised instead of
    TestFailed.
    """

class ResourceDenied(TestSkipped):
    """Test skipped because it requested a disallowed resource.

    This is raised when a test calls requires() for a resource that
    has not be enabled.  It is used to distinguish between expected
    and unexpected skips.
    """

verbose = 1              # Flag set to 0 by regrtest.py
use_resources = None     # Flag set to [] by regrtest.py
max_memuse = 0           # Disable bigmem tests (they will still be run with
                         # small sizes, to make sure they work.)

# _original_stdout is meant to hold stdout at the time regrtest began.
# This may be "the real" stdout, or IDLE's emulation of stdout, or whatever.
# The point is to have some flavor of stdout the user can actually see.
_original_stdout = None
def record_original_stdout(stdout):
    global _original_stdout
    _original_stdout = stdout

def get_original_stdout():
    return _original_stdout or sys.stdout

def unload(name):
    try:
        del sys.modules[name]
    except KeyError:
        pass

def unlink(filename):
    import os
    try:
        os.unlink(filename)
    except OSError:
        pass

def forget(modname):
    '''"Forget" a module was ever imported by removing it from sys.modules and
    deleting any .pyc and .pyo files.'''
    unload(modname)
    import os
    for dirname in sys.path:
        unlink(os.path.join(dirname, modname + os.extsep + 'pyc'))
        # Deleting the .pyo file cannot be within the 'try' for the .pyc since
        # the chance exists that there is no .pyc (and thus the 'try' statement
        # is exited) but there is a .pyo file.
        unlink(os.path.join(dirname, modname + os.extsep + 'pyo'))

def is_resource_enabled(resource):
    """Test whether a resource is enabled.  Known resources are set by
    regrtest.py."""
    return use_resources is not None and resource in use_resources

def requires(resource, msg=None):
    """Raise ResourceDenied if the specified resource is not available.

    If the caller's module is __main__ then automatically return True.  The
    possibility of False being returned occurs when regrtest.py is executing."""
    # see if the caller's module is __main__ - if so, treat as if
    # the resource was set
    if sys._getframe().f_back.f_globals.get("__name__") == "__main__":
        return
    if not is_resource_enabled(resource):
        if msg is None:
            msg = "Use of the `%s' resource not enabled" % resource
        raise ResourceDenied(msg)

FUZZ = 1e-6

def fcmp(x, y): # fuzzy comparison function
    if type(x) == type(0.0) or type(y) == type(0.0):
        try:
            x, y = coerce(x, y)
            fuzz = (abs(x) + abs(y)) * FUZZ
            if abs(x-y) <= fuzz:
                return 0
        except:
            pass
    elif type(x) == type(y) and type(x) in (type(()), type([])):
        for i in range(min(len(x), len(y))):
            outcome = fcmp(x[i], y[i])
            if outcome != 0:
                return outcome
        return cmp(len(x), len(y))
    return cmp(x, y)

try:
    str
    have_unicode = 1
except NameError:
    have_unicode = 0

is_jython = sys.platform.startswith('java')

import os
# Filename used for testing
if os.name == 'java':
    # Jython disallows @ in module names
    TESTFN = '$test'
elif os.name == 'riscos':
    TESTFN = 'testfile'
else:
    TESTFN = '@test'
    # Unicode name only used if TEST_FN_ENCODING exists for the platform.
    if have_unicode:
        # Assuming sys.getfilesystemencoding()!=sys.getdefaultencoding()
        # TESTFN_UNICODE is a filename that can be encoded using the
        # file system encoding, but *not* with the default (ascii) encoding
        if isinstance('', str):
            # python -U
            # XXX perhaps unicode() should accept Unicode strings?
            TESTFN_UNICODE = "@test-\xe0\xf2"
        else:
            # 2 latin characters.
            TESTFN_UNICODE = str("@test-\xe0\xf2", "latin-1")
        TESTFN_ENCODING = sys.getfilesystemencoding()

# Make sure we can write to TESTFN, try in /tmp if we can't
fp = None
try:
    fp = open(TESTFN, 'w+')
except IOError:
    TMP_TESTFN = os.path.join('/tmp', TESTFN)
    try:
        fp = open(TMP_TESTFN, 'w+')
        TESTFN = TMP_TESTFN
        del TMP_TESTFN
    except IOError:
        print(('WARNING: tests will fail, unable to write to: %s or %s' %
                (TESTFN, TMP_TESTFN)))
if fp is not None:
    fp.close()
    unlink(TESTFN)
del os, fp

def findfile(file, here=__file__):
    """Try to find a file on sys.path and the working directory.  If it is not
    found the argument passed to the function is returned (this does not
    necessarily signal failure; could still be the legitimate path)."""
    import os
    if os.path.isabs(file):
        return file
    path = sys.path
    path = [os.path.dirname(here)] + path
    for dn in path:
        fn = os.path.join(dn, file)
        if os.path.exists(fn): return fn
    return file

def verify(condition, reason='test failed'):
    """Verify that condition is true. If not, raise TestFailed.

       The optional argument reason can be given to provide
       a better error text.
    """

    if not condition:
        raise TestFailed(reason)

def vereq(a, b):
    """Raise TestFailed if a == b is false.

    This is better than verify(a == b) because, in case of failure, the
    error message incorporates repr(a) and repr(b) so you can see the
    inputs.

    Note that "not (a == b)" isn't necessarily the same as "a != b"; the
    former is tested.
    """

    if not (a == b):
        raise TestFailed("%r == %r" % (a, b))

def sortdict(dict):
    "Like repr(dict), but in sorted order."
    items = list(dict.items())
    items.sort()
    reprpairs = ["%r: %r" % pair for pair in items]
    withcommas = ", ".join(reprpairs)
    return "{%s}" % withcommas

def check_syntax(statement):
    try:
        compile(statement, '<string>', 'exec')
    except SyntaxError:
        pass
    else:
        print('Missing SyntaxError: "%s"' % statement)

def open_urlresource(url):
    import urllib.request, urllib.parse, urllib.error, urllib.parse
    import os.path

    filename = urllib.parse.urlparse(url)[2].split('/')[-1] # '/': it's URL!

    for path in [os.path.curdir, os.path.pardir]:
        fn = os.path.join(path, filename)
        if os.path.exists(fn):
            return open(fn)

    requires('urlfetch')
    print('\tfetching %s ...' % url, file=get_original_stdout())
    fn, _ = urllib.request.urlretrieve(url, filename)
    return open(fn)

#=======================================================================
# Decorator for running a function in a different locale, correctly resetting
# it afterwards.

def run_with_locale(catstr, *locales):
    def decorator(func):
        def inner(*args, **kwds):
            try:
                import locale
                category = getattr(locale, catstr)
                orig_locale = locale.setlocale(category)
            except AttributeError:
                # if the test author gives us an invalid category string
                raise
            except:
                # cannot retrieve original locale, so do nothing
                locale = orig_locale = None
            else:
                for loc in locales:
                    try:
                        locale.setlocale(category, loc)
                        break
                    except:
                        pass

            # now run the function, resetting the locale on exceptions
            try:
                return func(*args, **kwds)
            finally:
                if locale and orig_locale:
                    locale.setlocale(category, orig_locale)
        inner.__name__ = func.__name__
        inner.__doc__ = func.__doc__
        return inner
    return decorator

#=======================================================================
# Big-memory-test support. Separate from 'resources' because memory use should be configurable.

# Some handy shorthands. Note that these are used for byte-limits as well
# as size-limits, in the various bigmem tests
_1M = 1024*1024
_1G = 1024 * _1M
_2G = 2 * _1G

def set_memlimit(limit):
    import re
    global max_memuse
    sizes = {
        'k': 1024,
        'm': _1M,
        'g': _1G,
        't': 1024*_1G,
    }
    m = re.match(r'(\d+(\.\d+)?) (K|M|G|T)b?$', limit,
                 re.IGNORECASE | re.VERBOSE)
    if m is None:
        raise ValueError('Invalid memory limit %r' % (limit,))
    memlimit = int(float(m.group(1)) * sizes[m.group(3).lower()])
    if memlimit < 2.5*_1G:
        raise ValueError('Memory limit %r too low to be useful' % (limit,))
    max_memuse = memlimit

def bigmemtest(minsize, memuse, overhead=5*_1M):
    """Decorator for bigmem tests.

    'minsize' is the minimum useful size for the test (in arbitrary,
    test-interpreted units.) 'memuse' is the number of 'bytes per size' for
    the test, or a good estimate of it. 'overhead' specifies fixed overhead,
    independant of the testsize, and defaults to 5Mb.

    The decorator tries to guess a good value for 'size' and passes it to
    the decorated test function. If minsize * memuse is more than the
    allowed memory use (as defined by max_memuse), the test is skipped.
    Otherwise, minsize is adjusted upward to use up to max_memuse.
    """
    def decorator(f):
        def wrapper(self):
            if not max_memuse:
                # If max_memuse is 0 (the default),
                # we still want to run the tests with size set to a few kb,
                # to make sure they work. We still want to avoid using
                # too much memory, though, but we do that noisily.
                maxsize = 5147
                self.failIf(maxsize * memuse + overhead > 20 * _1M)
            else:
                maxsize = int((max_memuse - overhead) / memuse)
                if maxsize < minsize:
                    # Really ought to print 'test skipped' or something
                    if verbose:
                        sys.stderr.write("Skipping %s because of memory "
                                         "constraint\n" % (f.__name__,))
                    return
                # Try to keep some breathing room in memory use
                maxsize = max(maxsize - 50 * _1M, minsize)
            return f(self, maxsize)
        wrapper.minsize = minsize
        wrapper.memuse = memuse
        wrapper.overhead = overhead
        return wrapper
    return decorator

#=======================================================================
# Preliminary PyUNIT integration.

from . import unittest


class BasicTestRunner:
    def run(self, test):
        result = unittest.TestResult()
        test(result)
        return result

def run_suite(suite, testclass=None):
    """Run tests from a unittest.TestSuite-derived class."""
    if verbose:
        runner = unittest.TextTestRunner(sys.stdout, verbosity=2)
    else:
        runner = BasicTestRunner()

    result = runner.run(suite)
    if not result.wasSuccessful():
        if len(result.errors) == 1 and not result.failures:
            err = result.errors[0][1]
        elif len(result.failures) == 1 and not result.errors:
            err = result.failures[0][1]
        else:
            if testclass is None:
                msg = "errors occurred; run in verbose mode for details"
            else:
                msg = "errors occurred in %s.%s" \
                      % (testclass.__module__, testclass.__name__)
            raise TestFailed(msg)
        raise TestFailed(err)


def run_unittest(*classes):
    """Run tests from unittest.TestCase-derived classes."""
    suite = unittest.TestSuite()
    for cls in classes:
        if isinstance(cls, (unittest.TestSuite, unittest.TestCase)):
            suite.addTest(cls)
        else:
            suite.addTest(unittest.makeSuite(cls))
    if len(classes)==1:
        testclass = classes[0]
    else:
        testclass = None
    run_suite(suite, testclass)


#=======================================================================
# doctest driver.

def run_doctest(module, verbosity=None):
    """Run doctest on the given module.  Return (#failures, #tests).

    If optional argument verbosity is not specified (or is None), pass
    test_support's belief about verbosity on to doctest.  Else doctest's
    usual behavior is used (it searches sys.argv for -v).
    """

    import doctest

    if verbosity is None:
        verbosity = verbose
    else:
        verbosity = None

    # Direct doctest output (normally just errors) to real stdout; doctest
    # output shouldn't be compared by regrtest.
    save_stdout = sys.stdout
    sys.stdout = get_original_stdout()
    try:
        f, t = doctest.testmod(module, verbose=verbosity)
        if f:
            raise TestFailed("%d of %d doctests failed" % (f, t))
    finally:
        sys.stdout = save_stdout
    if verbose:
        print('doctest (%s) ... %d tests with zero failures' % (module.__name__, t))
    return f, t

########NEW FILE########
__FILENAME__ = unittest
#! /usr/bin/python2.5
from __future__ import print_function
'''
Python unit testing framework, based on Erich Gamma's JUnit and Kent Beck's
Smalltalk testing framework.

This module contains the core framework classes that form the basis of
specific test cases and suites (TestCase, TestSuite etc.), and also a
text-based utility class for running the tests and reporting the results
 (TextTestRunner).

Simple usage:

    import unittest

    class IntegerArithmenticTestCase(unittest.TestCase):
        def testAdd(self):  ## test method names begin 'test*'
            self.assertEquals((1 + 2), 3)
            self.assertEquals(0 + 1, 1)
        def testMultiply(self):
            self.assertEquals((0 * 10), 0)
            self.assertEquals((5 * 8), 40)

    if __name__ == '__main__':
        unittest.main()

Further information is available in the bundled documentation, and from

  http://pyunit.sourceforge.net/

Copyright (c) 1999-2003 Steve Purcell
This module is free software, and you may redistribute it and/or modify
it under the same terms as Python itself, so long as this copyright message
and disclaimer are retained in their original form.

IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF
THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.

THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS,
AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
'''

__author__ = "Steve Purcell"
__email__ = "stephen_purcell at yahoo dot com"
__version__ = "#Revision: 1.63 $"[11:-2]

import time
import sys
import traceback
import os
import types

class ReferenceLeak(Exception):
    def __init__(self, s, n):
        self.n = n
        self.s = s

    def __str__(self):
        return '%s: %d' % (self.s, self.n)

##############################################################################
# Exported classes and functions
##############################################################################
__all__ = ['TestResult', 'TestCase', 'TestSuite', 'TextTestRunner',
           'TestLoader', 'FunctionTestCase', 'main', 'defaultTestLoader']

# Expose obsolete functions for backwards compatibility
__all__.extend(['getTestCaseNames', 'makeSuite', 'findTestCases'])


##############################################################################
# Test framework core
##############################################################################

# All classes defined herein are 'new-style' classes, allowing use of 'super()'
__metaclass__ = type

def _strclass(cls):
    return "%s.%s" % (cls.__module__, cls.__name__)

__unittest = 1

class TestResult:
    """Holder for test result information.

    Test results are automatically managed by the TestCase and TestSuite
    classes, and do not need to be explicitly manipulated by writers of tests.

    Each instance holds the total number of tests run, and collections of
    failures and errors that occurred among those test runs. The collections
    contain tuples of (testcase, exceptioninfo), where exceptioninfo is the
    formatted traceback of the error that occurred.
    """
    def __init__(self):
        self.failures = []
        self.errors = []
        self.testsRun = 0
        self.shouldStop = 0

    def startTest(self, test):
        "Called when the given test is about to be run"
        self.testsRun = self.testsRun + 1

    def stopTest(self, test):
        "Called when the given test has been run"
        pass

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        self.errors.append((test, self._exc_info_to_string(err, test)))

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        self.failures.append((test, self._exc_info_to_string(err, test)))

    def addSuccess(self, test):
        "Called when a test has completed successfully"
        pass

    def wasSuccessful(self):
        "Tells whether or not this result was a success"
        return len(self.failures) == len(self.errors) == 0

    def stop(self):
        "Indicates that the tests should be aborted"
        self.shouldStop = True

    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple of values into a string."""
        exctype, value, tb = err
        # Skip test runner traceback levels
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next
        if exctype is test.failureException:
            # Skip assert*() traceback levels
            length = self._count_relevant_tb_levels(tb)
            return ''.join(traceback.format_exception(exctype, value, tb, length))
        return ''.join(traceback.format_exception(exctype, value, tb))

    def _is_relevant_tb_level(self, tb):
        return '__unittest' in tb.tb_frame.f_globals

    def _count_relevant_tb_levels(self, tb):
        length = 0
        while tb and not self._is_relevant_tb_level(tb):
            length += 1
            tb = tb.tb_next
        return length

    def __repr__(self):
        return "<%s run=%i errors=%i failures=%i>" % \
               (_strclass(self.__class__), self.testsRun, len(self.errors),
                len(self.failures))

class TestCase:
    """A class whose instances are single test cases.

    By default, the test code itself should be placed in a method named
    'runTest'.

    If the fixture may be used for many test cases, create as
    many test methods as are needed. When instantiating such a TestCase
    subclass, specify in the constructor arguments the name of the test method
    that the instance is to execute.

    Test authors should subclass TestCase for their own tests. Construction
    and deconstruction of the test's environment ('fixture') can be
    implemented by overriding the 'setUp' and 'tearDown' methods respectively.

    If it is necessary to override the __init__ method, the base class
    __init__ method must always be called. It is important that subclasses
    should not change the signature of their __init__ method, since instances
    of the classes are instantiated automatically by parts of the framework
    in order to be run.
    """

    # This attribute determines which exception will be raised when
    # the instance's assertion methods fail; test methods raising this
    # exception will be deemed to have 'failed' rather than 'errored'

    failureException = AssertionError

    def __init__(self, methodName='runTest'):
        """Create an instance of the class that will use the named test
           method when executed. Raises a ValueError if the instance does
           not have a method with the specified name.
        """
        try:
            self._testMethodName = methodName
            testMethod = getattr(self, methodName)
            self._testMethodDoc = testMethod.__doc__
        except AttributeError:
            raise ValueError("no such test method in %s: %s" % \
                  (self.__class__, methodName))

    def assertIs(self, expr1, expr2, msg=None):
        """Just like self.assertTrue(a is b), but with a nicer default message."""
        if expr1 is not expr2:
            standardMsg = '%s is not %s' % (safe_repr(expr1),
                                             safe_repr(expr2))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIn(self, member, container, msg=None):
        """Just like self.assertTrue(a in b), but with a nicer default message."""
        if member not in container:
            standardMsg = '%s not found in %s' % (repr(member),
                                                  repr(container))
            self.fail(str((msg, standardMsg)))

    def assertNotIn(self, member, container, msg=None):
        """Just like self.assertTrue(a not in b), but with a nicer default message."""
        if member in container:
            standardMsg = '%s unexpectedly found in %s' % (repr(member),
                                                        repr(container))
            self.fail(str((msg, standardMsg)))


    def setUp(self):
        "Hook method for setting up the test fixture before exercising it."
        pass

    def tearDown(self):
        "Hook method for deconstructing the test fixture after testing it."
        pass

    def countTestCases(self):
        return 1

    def defaultTestResult(self):
        return TestResult()

    def shortDescription(self):
        """Returns a one-line description of the test, or None if no
        description has been provided.

        The default implementation of this method returns the first line of
        the specified test method's docstring.
        """
        doc = self._testMethodDoc
        return doc and doc.split("\n")[0].strip() or None

    def id(self):
        return "%s.%s" % (_strclass(self.__class__), self._testMethodName)

    def __str__(self):
        return "%s (%s)" % (self._testMethodName, _strclass(self.__class__))

    def __repr__(self):
        return "<%s testMethod=%s>" % \
               (_strclass(self.__class__), self._testMethodName)

    def run(self, result=None):
        self.run_(result, False)
        self.run_(result, False)
        try:
            self.run_(result, True)
        except AttributeError:
            pass
        
    def run_(self, result, memcheck):
        if result is None: result = self.defaultTestResult()
        if memcheck and not hasattr(sys, 'gettotalrefcount'):
            return
        result.startTest(self)
        testMethod = getattr(self, self._testMethodName)
        try:
            import gc

            total_start = 0
            total_finish = 0
            ok = True
            gc.collect()
            ob_start = set(id(x) for x in gc.get_objects())
            try:
                total_start = sys.gettotalrefcount()
            except AttributeError:
                pass

            try:
                self.setUp()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, self._exc_info())
                return

            ok = False
            try:
                testMethod()
                ok = True
            except self.failureException:
                result.addFailure(self, self._exc_info())
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, self._exc_info())

            try:
                self.tearDown()
                if ok and memcheck:
                    gc.collect()
                    gc.collect()
                    total_finish = sys.gettotalrefcount()
                    ob_finish = gc.get_objects()
                    if len(ob_start) != len(ob_finish):
                        #for ob in ob_finish:
                        #    if id(ob) not in ob_start and ob is not ob_start:
                        #        print ob
                        raise ReferenceLeak('more objects', len(ob_finish)-len(ob_start))
                    if total_finish != total_start:
                        print(total_start, total_finish)
                        raise ReferenceLeak('more references', total_finish - total_start)
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, self._exc_info())
                ok = False
            if ok: result.addSuccess(self)
        finally:
            result.stopTest(self)

    def __call__(self, *args, **kwds):
        return self.run(*args, **kwds)

    def debug(self):
        """Run the test without collecting errors in a TestResult"""
        self.setUp()
        getattr(self, self._testMethodName)()
        self.tearDown()

    def _exc_info(self):
        """Return a version of sys.exc_info() with the traceback frame
           minimised; usually the top level of the traceback frame is not
           needed.
        """
        exctype, excvalue, tb = sys.exc_info()
        if sys.platform[:4] == 'java': ## tracebacks look different in Jython
            return (exctype, excvalue, tb)
        return (exctype, excvalue, tb)

    def fail(self, msg=None):
        """Fail immediately, with the given message."""
        raise self.failureException(msg)

    def failIf(self, expr, msg=None):
        "Fail the test if the expression is true."
        if expr: raise self.failureException(msg)

    def failUnless(self, expr, msg=None):
        """Fail the test unless the expression is true."""
        if not expr: raise self.failureException(msg)

    def failUnlessRaises(self, excClass, callableObj, *args, **kwargs):
        """Fail unless an exception of class excClass is thrown
           by callableObj when invoked with arguments args and keyword
           arguments kwargs. If a different type of exception is
           thrown, it will not be caught, and the test case will be
           deemed to have suffered an error, exactly as for an
           unexpected exception.
        """
        try:
            callableObj(*args, **kwargs)
        except excClass:
            return
        else:
            if hasattr(excClass,'__name__'): excName = excClass.__name__
            else: excName = str(excClass)
            raise self.failureException("%s not raised" % excName)

    def failUnlessEqual(self, first, second, msg=None):
        """Fail if the two objects are unequal as determined by the '=='
           operator.
        """
        if not first == second:
            raise self.failureException(msg or '%r != %r' % (first, second))

    def failIfEqual(self, first, second, msg=None):
        """Fail if the two objects are equal as determined by the '=='
           operator.
        """
        if first == second:
            raise self.failureException(msg or '%r == %r' % (first, second))

    def failUnlessAlmostEqual(self, first, second, places=7, msg=None):
        """Fail if the two objects are unequal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most signficant digit).
        """
        if round(second-first, places) != 0:
            raise self.failureException(msg or '%r != %r within %r places' % (first, second, places))

    def failIfAlmostEqual(self, first, second, places=7, msg=None):
        """Fail if the two objects are equal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most signficant digit).
        """
        if round(second-first, places) == 0:
            raise self.failureException(msg or '%r == %r within %r places' % (first, second, places))

    # Synonyms for assertion methods

    assertEqual = assertEquals = failUnlessEqual

    assertNotEqual = assertNotEquals = failIfEqual

    assertAlmostEqual = assertAlmostEquals = failUnlessAlmostEqual

    assertNotAlmostEqual = assertNotAlmostEquals = failIfAlmostEqual

    assertRaises = failUnlessRaises

    assert_ = assertTrue = failUnless

    assertFalse = failIf



class TestSuite:
    """A test suite is a composite test consisting of a number of TestCases.

    For use, create an instance of TestSuite, then add test case instances.
    When all tests have been added, the suite can be passed to a test
    runner, such as TextTestRunner. It will run the individual test cases
    in the order in which they were added, aggregating the results. When
    subclassing, do not forget to call the base class constructor.
    """
    def __init__(self, tests=()):
        self._tests = []
        self.addTests(tests)

    def __repr__(self):
        return "<%s tests=%s>" % (_strclass(self.__class__), self._tests)

    __str__ = __repr__

    def __iter__(self):
        return iter(self._tests)

    def countTestCases(self):
        cases = 0
        for test in self._tests:
            cases += test.countTestCases()
        return cases

    def addTest(self, test):
        self._tests.append(test)

    def addTests(self, tests):
        for test in tests:
            self.addTest(test)

    def run(self, result):
        for test in self._tests:
            if result.shouldStop:
                break
            test(result)
        return result

    def __call__(self, *args, **kwds):
        return self.run(*args, **kwds)

    def debug(self):
        """Run the tests without collecting errors in a TestResult"""
        for test in self._tests: test.debug()


class FunctionTestCase(TestCase):
    """A test case that wraps a test function.

    This is useful for slipping pre-existing test functions into the
    PyUnit framework. Optionally, set-up and tidy-up functions can be
    supplied. As with TestCase, the tidy-up ('tearDown') function will
    always be called if the set-up ('setUp') function ran successfully.
    """

    def __init__(self, testFunc, setUp=None, tearDown=None,
                 description=None):
        TestCase.__init__(self)
        self.__setUpFunc = setUp
        self.__tearDownFunc = tearDown
        self.__testFunc = testFunc
        self.__description = description

    def setUp(self):
        if self.__setUpFunc is not None:
            self.__setUpFunc()

    def tearDown(self):
        if self.__tearDownFunc is not None:
            self.__tearDownFunc()

    def runTest(self):
        self.__testFunc()

    def id(self):
        return self.__testFunc.__name__

    def __str__(self):
        return "%s (%s)" % (_strclass(self.__class__), self.__testFunc.__name__)

    def __repr__(self):
        return "<%s testFunc=%s>" % (_strclass(self.__class__), self.__testFunc)

    def shortDescription(self):
        if self.__description is not None: return self.__description
        doc = self.__testFunc.__doc__
        return doc and doc.split("\n")[0].strip() or None



##############################################################################
# Locating and loading tests
##############################################################################

class TestLoader:
    """This class is responsible for loading tests according to various
    criteria and returning them wrapped in a Test
    """
    testMethodPrefix = 'test'
    suiteClass = TestSuite

    def loadTestsFromTestCase(self, testCaseClass):
        """Return a suite of all tests cases contained in testCaseClass"""
        if issubclass(testCaseClass, TestSuite):
            raise TypeError("Test cases should not be derived from TestSuite. Maybe you meant to derive from TestCase?")
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        return self.suiteClass(list(map(testCaseClass, testCaseNames)))

    def loadTestsFromModule(self, module):
        """Return a suite of all tests cases contained in the given module"""
        tests = []
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and
                issubclass(obj, TestCase)):
                tests.append(self.loadTestsFromTestCase(obj))
        return self.suiteClass(tests)

    def loadTestsFromName(self, name, module=None):
        """Return a suite of all tests cases given a string specifier.

        The name may resolve either to a module, a test case class, a
        test method within a test case class, or a callable object which
        returns a TestCase or TestSuite instance.

        The method optionally resolves the names relative to a given module.
        """
        parts = name.split('.')
        if module is None:
            parts_copy = parts[:]
            while parts_copy:
                try:
                    module = __import__('.'.join(parts_copy))
                    break
                except ImportError:
                    del parts_copy[-1]
                    if not parts_copy: raise
            parts = parts[1:]
        obj = module
        for part in parts:
            parent, obj = obj, getattr(obj, part)

        if type(obj) == types.ModuleType:
            return self.loadTestsFromModule(obj)
        elif (isinstance(obj, type) and
              issubclass(obj, TestCase)):
            return self.loadTestsFromTestCase(obj)
        elif type(obj) == types.UnboundMethodType:
            return parent(obj.__name__)
        elif isinstance(obj, TestSuite):
            return obj
        elif hasattr(obj, '__call__'):
            test = obj()
            if not isinstance(test, (TestCase, TestSuite)):
                raise ValueError("calling %s returned %s, not a test" % (obj,test))
            return test
        else:
            raise ValueError("don't know how to make test from: %s" % obj)

    def loadTestsFromNames(self, names, module=None):
        """Return a suite of all tests cases found using the given sequence
        of string specifiers. See 'loadTestsFromName()'.
        """
        suites = [self.loadTestsFromName(name, module) for name in names]
        return self.suiteClass(suites)

    def getTestCaseNames(self, testCaseClass):
        """Return a sorted sequence of method names found within testCaseClass
        """
        def isTestMethod(attrname, testCaseClass=testCaseClass, prefix=self.testMethodPrefix):
            return attrname.startswith(prefix) and hasattr(getattr(testCaseClass, attrname), '__call__')
        testFnNames = list(filter(isTestMethod, dir(testCaseClass)))
        for baseclass in testCaseClass.__bases__:
            for testFnName in self.getTestCaseNames(baseclass):
                if testFnName not in testFnNames:  # handle overridden methods
                    testFnNames.append(testFnName)
        return testFnNames



defaultTestLoader = TestLoader()


##############################################################################
# Patches for old functions: these functions should be considered obsolete
##############################################################################

def _makeLoader(prefix, suiteClass=None):
    loader = TestLoader()
    loader.testMethodPrefix = prefix
    if suiteClass: loader.suiteClass = suiteClass
    return loader

def getTestCaseNames(testCaseClass, prefix):
    return _makeLoader(prefix).getTestCaseNames(testCaseClass)

def makeSuite(testCaseClass, prefix='test', suiteClass=TestSuite):
    return _makeLoader(prefix, suiteClass).loadTestsFromTestCase(testCaseClass)

def findTestCases(module, prefix='test', suiteClass=TestSuite):
    return _makeLoader(prefix, suiteClass).loadTestsFromModule(module)


##############################################################################
# Text UI
##############################################################################

class _WritelnDecorator:
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        return getattr(self.stream,attr)

    def writeln(self, arg=None):
        if arg: self.write(arg)
        self.write('\n') # text-mode streams translate to \r\n if needed


class _TextTestResult(TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by TextTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, descriptions, verbosity):
        TestResult.__init__(self)
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions

    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        TestResult.startTest(self, test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write('.')

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write('E')

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
        elif self.dots:
            self.stream.write('F')

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % err)


class TextTestRunner:
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1):
        self.stream = _WritelnDecorator(stream)
        self.descriptions = descriptions
        self.verbosity = verbosity

    def _makeResult(self):
        return _TextTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        result.printErrors()
        self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run != 1 and "s" or "", timeTaken))
        self.stream.writeln()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = list(map(len, (result.failures, result.errors)))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        else:
            self.stream.writeln("OK")
        return result



##############################################################################
# Facilities for running tests from the command line
##############################################################################

class TestProgram:
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """
    USAGE = """\
Usage: %(progName)s [options] [test] [...]

Options:
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output

Examples:
  %(progName)s                               - run default set of tests
  %(progName)s MyTestSuite                   - run suite 'MyTestSuite'
  %(progName)s MyTestCase.testSomething      - run MyTestCase.testSomething
  %(progName)s MyTestCase                    - run all 'test*' test methods
                                               in MyTestCase
"""
    def __init__(self, module='__main__', defaultTest=None,
                 argv=None, testRunner=None, testLoader=defaultTestLoader):
        if type(module) == type(''):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        if argv is None:
            argv = sys.argv
        self.verbosity = 1
        self.defaultTest = defaultTest
        self.testRunner = testRunner
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        self.parseArgs(argv)
        self.runTests()

    def usageExit(self, msg=None):
        if msg: print(msg)
        print(self.USAGE % self.__dict__)
        sys.exit(2)

    def parseArgs(self, argv):
        import getopt
        try:
            options, args = getopt.getopt(argv[1:], 'hHvq',
                                          ['help','verbose','quiet'])
            for opt, value in options:
                if opt in ('-h','-H','--help'):
                    self.usageExit()
                if opt in ('-q','--quiet'):
                    self.verbosity = 0
                if opt in ('-v','--verbose'):
                    self.verbosity = 2
            if len(args) == 0 and self.defaultTest is None:
                self.test = self.testLoader.loadTestsFromModule(self.module)
                return
            if len(args) > 0:
                self.testNames = args
            else:
                self.testNames = (self.defaultTest,)
            self.createTests()
        except getopt.error as msg:
            self.usageExit(msg)

    def createTests(self):
        self.test = self.testLoader.loadTestsFromNames(self.testNames,
                                                       self.module)

    def runTests(self):
        if self.testRunner is None:
            self.testRunner = TextTestRunner(verbosity=self.verbosity)
        result = self.testRunner.run(self.test)
        sys.exit(not result.wasSuccessful())

main = TestProgram


##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)

########NEW FILE########
__FILENAME__ = _btuple
from blist._blist import blist
from ctypes import c_int
import collections
class btuple(collections.Sequence):
    def __init__(self, seq=None):
        if isinstance(seq, btuple):
            self._blist = seq._blist
        elif seq is not None:
            self._blist = blist(seq)
        else:
            self._blist = blist()
        self._hash = -1

    def _btuple_or_tuple(self, other, f):
        if isinstance(other, btuple):
            rv = f(self._blist, other._blist)
        elif isinstance(other, tuple):
            rv = f(self._blist, blist(other))
        else:
            return NotImplemented
        if isinstance(rv, blist):
            rv = btuple(rv)
        return rv        
        
    def __hash__(self):
        # Based on tuplehash from tupleobject.c
        if self._hash != -1:
            return self._hash
        
        n = len(self)
        mult = c_int(1000003)
        x = c_int(0x345678)
        for ob in self:
            n -= 1
            y = c_int(hash(ob))
            x = (x ^ y) * mult
            mult += c_int(82520) + n + n
        x += c_int(97531)
        if x == -1:
            x = -2;
        self._hash = x.value
        return self._hash

    def __add__(self, other):
        return self._btuple_or_tuple(other, blist.__add__)
    def __radd__(self, other):
        return self._btuple_or_tuple(other, blist.__radd__)
    def __contains__(self, item):
        return item in self._blist
    def __eq__(self, other):
        return self._btuple_or_tuple(other, blist.__eq__)
    def __ge__(self, other):
        return self._btuple_or_tuple(other, blist.__ge__)
    def __gt__(self, other):
        return self._btuple_or_tuple(other, blist.__gt__)
    def __le__(self, other):
        return self._btuple_or_tuple(other, blist.__le__)
    def __lt__(self, other):
        return self._btuple_or_tuple(other, blist.__lt__)
    def __ne__(self, other):
        return self._btuple_or_tuple(other, blist.__ne__)
    def __iter__(self):
        return iter(self._blist)
    def __len__(self):
        return len(self._blist)
    def __getitem__(self, key):
        if isinstance(key, slice):
            return btuple(self._blist[key])
        return self._blist[key]
    def __getslice__(self, i, j):
        return btuple(self._blist[i:j])
    def __repr__(self):
        return 'btuple((' + repr(self._blist)[7:-2] + '))'
    def __str__(self):
        return repr(self)
    def __mul__(self, i):
        return btuple(self._blist * i)
    def __rmul__(self, i):
        return btuple(i * self._blist)
    def count(self, item):
        return self._blist.count(item)
    def index(self, item):
        return self._blist.index(item)

del c_int
del collections

########NEW FILE########
__FILENAME__ = _sorteddict
from blist._sortedlist import sortedset, ReprRecursion
import collections, sys
from blist._blist import blist

class missingdict(dict):
    def __missing__(self, key):
        return self._missing(key)

class KeysView(collections.KeysView, collections.Sequence):
    def __getitem__(self, index):
        return self._mapping._sortedkeys[index]
    def __reversed__(self):
        return reversed(self._mapping._sortedkeys)
    def index(self, key):
        return self._mapping._sortedkeys.index(key)
    def count(self, key):
        return 1 if key in self else 0
    def _from_iterable(self, it):
        return sortedset(it, key=self._mapping._sortedkeys._key)
    def bisect_left(self, key):
        return self._mapping._sortedkeys.bisect_left(key)
    def bisect_right(self, key):
        return self._mapping._sortedkeys.bisect_right(key)
    bisect = bisect_right

class ItemsView(collections.ItemsView, collections.Sequence):
    def __getitem__(self, index):
        if isinstance(index, slice):
            keys = self._mapping._sortedkeys[index]
            return self._from_iterable((key, self._mapping[key])
                                       for key in keys)
        key = self._mapping._sortedkeys[index]
        return (key, self._mapping[key])
    def index(self, item):
        key, value = item
        i = self._mapping._sortedkeys.index(key)
        if self._mapping[key] == value:
            return i
        raise ValueError
    def count(self, item):
        return 1 if item in self else 0
    def _from_iterable(self, it):
      keyfunc = self._mapping._sortedkeys._key
      if keyfunc is None:
        return sortedset(it)
      else:
        return sortedset(it, key=lambda item: keyfunc(item[0]))

class ValuesView(collections.ValuesView, collections.Sequence):
    def __getitem__(self, index):
        if isinstance(index, slice):
            keys = self._mapping._sortedkeys[index]
            return [self._mapping[key] for key in keys]
        key = self._mapping._sortedkeys[index]
        return self._mapping[key]

class sorteddict(collections.MutableMapping):
    def __init__(self, *args, **kw):
        if hasattr(self, '__missing__'):
            self._map = missingdict()
            self._map._missing = self.__missing__
        else:
            self._map = dict()
        key = None
        if len(args) > 0:
            if hasattr(args[0], '__call__'):
                key = args[0]
                args = args[1:]
            elif len(args) > 1:
                raise TypeError("'%s' object is not callable" %
                                args[0].__class__.__name__)
        if len(args) > 1:
            raise TypeError('sorteddict expected at most 2 arguments, got %d'
                            % len(args))
        if len(args) == 1 and isinstance(args[0], sorteddict) and key is None:
            key = args[0]._sortedkeys._key
        self._sortedkeys = sortedset(key=key)
        self.update(*args, **kw)

    if sys.version_info[0] < 3:
        def keys(self):
            return self._sortedkeys.copy()
        def items(self):
            return blist((key, self[key]) for key in self)
        def values(self):
            return blist(self[key] for key in self)
        def viewkeys(self):
            return KeysView(self)
        def viewitems(self):
            return ItemsView(self)
        def viewvalues(self):
            return ValuesView(self)
    else:
        def keys(self):
            return KeysView(self)
        def items(self):
            return ItemsView(self)
        def values(self):
            return ValuesView(self)

    def __setitem__(self, key, value):
        try:
            if key not in self._map:
                self._sortedkeys.add(key)
            self._map[key] = value
        except:
            if key not in self._map:
                self._sortedkeys.discard(key)
            raise

    def __delitem__(self, key):
        self._sortedkeys.discard(key)
        del self._map[key]

    def __getitem__(self, key):
        return self._map[key]

    def __iter__(self):
        return iter(self._sortedkeys)

    def __len__(self):
        return len(self._sortedkeys)

    def copy(self):
        return sorteddict(self)

    @classmethod
    def fromkeys(cls, keys, value=None, key=None):
        if key is not None:
            rv = cls(key)
        else:
            rv = cls()
        for key in keys:
            rv[key] = value
        return rv

    def __repr__(self):
        with ReprRecursion(self) as r:
            if r:
              return 'sorteddict({...})'
            return ('sorteddict({%s})' %
                    ', '.join('%r: %r' % (k, self._map[k]) for k in self))

    def __eq__(self, other):
        if not isinstance(other, sorteddict):
            return False
        return self._map == other._map

########NEW FILE########
__FILENAME__ = _sortedlist
from blist._blist import blist
import collections, bisect, weakref, operator, itertools, sys, threading
try: # pragma: no cover
    izip = itertools.izip
except AttributeError: # pragma: no cover
    izip = zip

__all__ = ['sortedlist', 'weaksortedlist', 'sortedset', 'weaksortedset']

class ReprRecursion(object):
    local = threading.local()
    def __init__(self, ob):
        if not hasattr(self.local, 'repr_count'):
            self.local.repr_count = collections.defaultdict(int)
        self.ob_id = id(ob)
        self.value = self.ob_id in self.local.repr_count

    def __enter__(self):
        self.local.repr_count[self.ob_id] += 1
        return self.value

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.local.repr_count[self.ob_id] -= 1
        if self.local.repr_count[self.ob_id] == 0:
            del self.local.repr_count[self.ob_id]
        return False

class _sortedbase(collections.Sequence):
    def __init__(self, iterable=(), key=None):
        self._key = key
        if key is not None and not hasattr(key, '__call__'):
            raise TypeError("'%s' object is not callable" % str(type(key)))
        if ((isinstance(iterable,type(self))
             or isinstance(self,type(iterable)))
            and iterable._key is key):
            self._blist = blist(iterable._blist)
        else:
            self._blist = blist()
            for v in iterable:
                self.add(v)

    def _from_iterable(self, iterable):
        return self.__class__(iterable, self._key)

    def _u2key(self, value):
        "Convert a user-object to the key"
        if self._key is None:
            return value
        else:
            return self._key(value)

    def _u2i(self, value):
        "Convert a user-object to the internal representation"
        if self._key is None:
            return value
        else:
            return (self._key(value), value)

    def _i2u(self, value):
        "Convert an internal object to a user-object"
        if self._key is None:
            return value
        else:
            return value[1]

    def _i2key(self, value):
        "Convert an internal object to the key"
        if self._key is None:
            return value
        else:
            return value[0]

    def _bisect_left(self, v):
        """Locate the point in the list where v would be inserted.

        Returns an (i, value) tuple:
          - i is the position where v would be inserted
          - value is the current user-object at position i

        This is the key function to override in subclasses.  They must
        accept a user-object v and return a user-object value.
        """

        key = self._u2key(v)
        lo = 0
        hi = len(self._blist)
        while lo < hi:
            mid = (lo+hi)//2
            v = self._i2key(self._blist[mid])
            if v < key: lo = mid + 1
            else: hi = mid
        if lo < len(self._blist):
            return lo, self._i2u(self._blist[lo])
        return lo, None

    def _bisect_right(self, v):
        """Same as _bisect_left, but go to the right of equal values"""

        key = self._u2key(v)
        lo = 0
        hi = len(self._blist)
        while lo < hi:
            mid = (lo+hi)//2
            v = self._i2key(self._blist[mid])
            if key < v: hi = mid
            else: lo = mid + 1
        if lo < len(self._blist):
            return lo, self._i2u(self._blist[lo])
        return lo, None

    def bisect_left(self, v):
        """L.bisect_left(v) -> index

        The return value i is such that all e in L[:i] have e < v, and
        all e in a[i:] have e >= v.  So if v already appears in the
        list, i points just before the leftmost v already there.
        """
        return self._bisect_left(v)[0]

    def bisect_right(self, v):
        """L.bisect_right(v) -> index

        Return the index where to insert item v in the list.

        The return value i is such that all e in a[:i] have e <= v,
        and all e in a[i:] have e > v.  So if v already appears in the
        list, i points just beyond the rightmost v already there.
        """
        return self._bisect_right(v)[0]

    bisect = bisect_right

    def add(self, value):
        """Add an element."""
        # Will throw a TypeError when trying to add an object that
        # cannot be compared to objects already in the list.
        i, _ = self._bisect_right(value)
        self._blist.insert(i, self._u2i(value))

    def discard(self, value):
        """Remove an element if it is a member.

        If the element is not a member, do nothing.

        """

        try:
            i, v = self._bisect_left(value)
        except TypeError:
            # Value cannot be compared with values already in the list.
            # Ergo, value isn't in the list.
            return
        i = self._advance(i, value)
        if i >= 0:
            del self._blist[i]

    def __contains__(self, value):
        """x.__contains__(y) <==> y in x"""
        try:
            i, v = self._bisect_left(value)
        except TypeError:
            # Value cannot be compared with values already in the list.
            # Ergo, value isn't in the list.
            return False
        i = self._advance(i, value)
        return i >= 0

    def __len__(self):
        """x.__len__() <==> len(x)"""
        return len(self._blist)

    def __iter__(self):
        """ x.__iter__() <==> iter(x)"""
        return (self._i2u(v) for v in self._blist)

    def __getitem__(self, index):
        """x.__getitem__(y) <==> x[y]"""
        if isinstance(index, slice):
            rv = self.__class__()
            rv._blist = self._blist[index]
            rv._key = self._key
            return rv
        return self._i2u(self._blist[index])

    def _advance(self, i, value):
        "Do a linear search through all items with the same key"
        key = self._u2key(value)
        while i < len(self._blist):
            if self._i2u(self._blist[i]) == value:
                return i
            elif key < self._i2key(self._blist[i]):
                break
            i += 1
        return -1

    def __reversed__(self):
        """L.__reversed__() -- return a reverse iterator over the list"""
        return (self._i2u(v) for v in reversed(self._blist))

    def index(self, value):
        """L.index(value) -> integer -- return first index of value.

        Raises ValueError if the value is not present.

        """

        try:
            i, v = self._bisect_left(value)
        except TypeError:
            raise ValueError
        i = self._advance(i, value)
        if i >= 0:
            return i
        raise ValueError

    def count(self, value):
        """L.count(value) -> integer -- return number of occurrences of value"""
        try:
            i, _ = self._bisect_left(value)
        except TypeError:
            return 0
        key = self._u2key(value)
        count = 0
        while True:
            i = self._advance(i, value)
            if i == -1:
                return count
            count += 1
            i += 1

    def pop(self, index=-1):
        """L.pop([index]) -> item -- remove and return item at index (default last).

        Raises IndexError if list is empty or index is out of range.

        """

        rv = self[index]
        del self[index]
        return rv

    def __delslice__(self, i, j):
        """x.__delslice__(i, j) <==> del x[i:j]

        Use of negative indices is not supported.

        """
        del self._blist[i:j]

    def __delitem__(self, i):
        """x.__delitem__(y) <==> del x[y]"""
        del self._blist[i]

class _weaksortedbase(_sortedbase):
    def _bisect_left(self, value):
        key = self._u2key(value)
        lo = 0
        hi = len(self._blist)
        while lo < hi:
            mid = (lo+hi)//2
            n, v = self._squeeze(mid)
            hi -= n
            if n and hi == len(self._blist):
                continue
            if self._i2key(self._blist[mid]) < key: lo = mid+1
            else: hi = mid
        n, v = self._squeeze(lo)
        return lo, v

    def _bisect_right(self, value):
        key = self._u2key(value)
        lo = 0
        hi = len(self._blist)
        while lo < hi:
            mid = (lo+hi)//2
            n, v = self._squeeze(mid)
            hi -= n
            if n and hi == len(self._blist):
                continue
            if key < self._i2key(self._blist[mid]): hi = mid
            else: lo = mid+1
        n, v = self._squeeze(lo)
        return lo, v

    _bisect = _bisect_right

    def _u2i(self, value):
        if self._key is None:
            return weakref.ref(value)
        else:
            return (self._key(value), weakref.ref(value))

    def _i2u(self, value):
        if self._key is None:
            return value()
        else:
            return value[1]()

    def _i2key(self, value):
        if self._key is None:
            return value()
        else:
            return value[0]

    def __iter__(self):
        """ x.__iter__() <==> iter(x)"""
        i = 0
        while i < len(self._blist):
            n, v = self._squeeze(i)
            if v is None: break
            yield v
            i += 1

    def _squeeze(self, i):
        n = 0
        while i < len(self._blist):
            v = self._i2u(self._blist[i])
            if v is None:
                del self._blist[i]
                n += 1
            else:
                return n, v
        return n, None

    def __getitem__(self, index):
        """x.__getitem__(y) <==> x[y]"""
        if isinstance(index, slice):
            return _sortedbase.__getitem__(self, index)
        n, v = self._squeeze(index)
        if v is None:
            raise IndexError('list index out of range')
        return v

    def __reversed__(self):
        """L.__reversed__() -- return a reverse iterator over the list"""
        i = len(self._blist)-1
        while i >= 0:
            n, v = self._squeeze(i)
            if not n:
                yield v
            i -= 1

    def _advance(self, i, value):
        "Do a linear search through all items with the same key"
        key = self._u2key(value)
        while i < len(self._blist):
            n, v = self._squeeze(i)
            if v is None:
                break
            if v == value:
                return i
            elif key < self._i2key(self._blist[i]):
                break
            i += 1
        return -1

class _listmixin(object):
    def remove(self, value):
        """L.remove(value) -- remove first occurrence of value.

        Raises ValueError if the value is not present.
        """

        del self[self.index(value)]

    def update(self, iterable):
        """L.update(iterable) -- add all elements from iterable into the list"""

        for item in iterable:
            self.add(item)

    def __mul__(self, k):
        if not isinstance(k, int):
            raise TypeError("can't multiply sequence by non-int of type '%s'"
                            % str(type(int)))
        rv = self.__class__()
        rv._key = self._key
        rv._blist = sum((blist([x])*k for x in self._blist), blist())
        return rv
    __rmul__ = __mul__

    def __imul__(self, k):
        if not isinstance(k, int):
            raise TypeError("can't multiply sequence by non-int of type '%s'"
                            % str(type(int)))
        self._blist = sum((blist([x])*k for x in self._blist), blist())
        return self

    def __eq__(self, other):
        """x.__eq__(y) <==> x==y"""
        return self._cmp_op(other, operator.eq)
    def __ne__(self, other):
        """x.__ne__(y) <==> x!=y"""
        return self._cmp_op(other, operator.ne)
    def __lt__(self, other):
        """x.__lt__(y) <==> x<y"""
        return self._cmp_op(other, operator.lt)
    def __gt__(self, other):
        """x.__gt__(y) <==> x>y"""
        return self._cmp_op(other, operator.gt)
    def __le__(self, other):
        """x.__le__(y) <==> x<=y"""
        return self._cmp_op(other, operator.le)
    def __ge__(self, other):
        """x.__ge__(y) <==> x>=y"""
        return self._cmp_op(other, operator.ge)

class _setmixin(object):
    "Methods that override our base class"

    def add(self, value):
        """Add an element to the set.

        This has no effect if the element is already present.

        """
        if value in self: return
        super(_setmixin, self).add(value)

    def __iter__(self):
        it = super(_setmixin, self).__iter__()
        while True:
            item = next(it)
            n = len(self)
            yield item
            if n != len(self):
                raise RuntimeError('Set changed size during iteration')

def safe_cmp(f):
    def g(self, other):
        if not isinstance(other, collections.Set):
            raise TypeError("can only compare to a set")
        return f(self, other)
    return g

class _setmixin2(collections.MutableSet):
    "methods that override or supplement the collections.MutableSet methods"

    __ror__ = collections.MutableSet.__or__
    __rand__ = collections.MutableSet.__and__
    __rxor__ = collections.MutableSet.__xor__

    if sys.version_info[0] < 3: # pragma: no cover
        __lt__ = safe_cmp(collections.MutableSet.__lt__)
        __gt__ = safe_cmp(collections.MutableSet.__gt__)
        __le__ = safe_cmp(collections.MutableSet.__le__)
        __ge__ = safe_cmp(collections.MutableSet.__ge__)

    def __ior__(self, it):
        if self is it:
            return self
        for value in it:
            self.add(value)
        return self

    def __isub__(self, it):
        if self is it:
            self.clear()
            return self
        for value in it:
            self.discard(value)
        return self

    def __ixor__(self, it):
        if self is it:
            self.clear()
            return self
        for value in it:
            if value in self:
                self.discard(value)
            else:
                self.add(value)
        return self

    def __rsub__(self, other):
        return self._from_iterable(other) - self

    def _make_set(self, iterable):
        if isinstance(iterable, collections.Set):
            return iterable
        return self._from_iterable(iterable)

    def difference(self, *args):
        """Return a new set with elements in the set that are not in the others."""
        rv = self.copy()
        rv.difference_update(*args)
        return rv

    def intersection(self, *args):
        """Return a new set with elements common to the set and all others."""
        rv = self.copy()
        rv.intersection_update(*args)
        return rv

    def issubset(self, other):
        """Test whether every element in the set is in *other*."""
        return self <= self._make_set(other)

    def issuperset(self, other):
        """Test whether every element in *other* is in the set."""
        return self >= self._make_set(other)

    def symmetric_difference(self, other):
        """Return a new set with elements in either the set or *other*
        but not both."""

        return self ^ self._make_set(other)

    def union(self, *args):
        """Return the union of sets as a new set.

        (i.e. all elements that are in either set.)

        """
        rv = self.copy()
        for arg in args:
            rv |= self._make_set(arg)
        return rv

    def update(self, *args):
        """Update the set, adding elements from all others."""
        for arg in args:
            self |= self._make_set(arg)

    def difference_update(self, *args):
        """Update the set, removing elements found in others."""
        for arg in args:
            self -= self._make_set(arg)

    def intersection_update(self, *args):
        """Update the set, keeping only elements found in it and all others."""
        for arg in args:
            self &= self._make_set(arg)

    def symmetric_difference_update(self, other):
        """Update the set, keeping only elements found in either set,
        but not in both."""

        self ^= self._make_set(other)

    def clear(self):
        """Remove all elements"""
        del self._blist[:]

    def copy(self):
        return self[:]

class sortedlist(_sortedbase, _listmixin):
    """sortedlist(iterable=(), key=None) -> new sorted list

    Keyword arguments:
    iterable -- items used to initially populate the sorted list
    key -- a function to return the sort key of an item

    A sortedlist is indexable like a list, but always keeps its
    members in sorted order.

    """

    def __repr__(self):
        """x.__repr__() <==> repr(x)"""
        if not self: return 'sortedlist()'
        with ReprRecursion(self) as r:
            if r: return 'sortedlist(...)'
            return ('sortedlist(%s)' % repr(list(self)))

    def _cmp_op(self, other, op):
        if not (isinstance(other,type(self)) or isinstance(self,type(other))):
            return NotImplemented
        if len(self) != len(other):
            if op is operator.eq:
                return False
            if op is operator.ne:
                return True
        for x, y in izip(self, other):
            if x != y:
                return op(x, y)
        return op in (operator.eq, operator.le, operator.ge)

class weaksortedlist(_listmixin, _weaksortedbase):
    """weaksortedlist(iterable=(), key=None) -> new sorted weak list

    Keyword arguments:
    iterable -- items used to initially populate the sorted list
    key -- a function to return the sort key of an item

    A weaksortedlist is indexable like a list, but always keeps its
    items in sorted order.  The weaksortedlist weakly references its
    members, so items will be discarded after there is no longer a
    strong reference to the item.

    """

    def __repr__(self):
        """x.__repr__() <==> repr(x)"""
        if not self: return 'weaksortedlist()'
        with ReprRecursion(self) as r:
            if r: return 'weaksortedlist(...)'
            return 'weaksortedlist(%s)' % repr(list(self))

    def _cmp_op(self, other, op):
        if not (isinstance(other,type(self)) or isinstance(self,type(other))):
            return NotImplemented
        for x, y in izip(self, other):
            if x != y:
                return op(x, y)
        return op in (operator.eq, operator.le, operator.ge)

class sortedset(_setmixin, _sortedbase, _setmixin2):
    """sortedset(iterable=(), key=None) -> new sorted set

    Keyword arguments:
    iterable -- items used to initially populate the sorted set
    key -- a function to return the sort key of an item

    A sortedset is similar to a set but is also indexable like a list.
    Items are maintained in sorted order.

    """

    def __repr__(self):
        """x.__repr__() <==> repr(x)"""
        if not self: return 'sortedset()'
        with ReprRecursion(self) as r:
            if r: return 'sortedset(...)'
            return ('sortedset(%s)' % repr(list(self)))

class weaksortedset(_setmixin, _weaksortedbase, _setmixin2):
    """weaksortedset(iterable=(), key=None) -> new sorted weak set

    Keyword arguments:
    iterable -- items used to initially populate the sorted set
    key -- a function to return the sort key of an item

    A weaksortedset is similar to a set but is also indexable like a
    list.  Items are maintained in sorted order.  The weaksortedset
    weakly references its members, so items will be discarded after
    there is no longer a strong reference to the item.

    """

    def __repr__(self):
        """x.__repr__() <==> repr(x)"""
        if not self: return 'weaksortedset()'
        with ReprRecursion(self) as r:
            if r: return 'weaksortedset(...)'
            return 'weaksortedset(%s)' % repr(list(self))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# blist documentation build configuration file, created by
# sphinx-quickstart on Sat May 15 18:18:54 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage', 'sphinx.ext.pngmath']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'blist'
copyright = u'2010, Stutzbach Enterprises, LLC'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.2'
# The full version, including alpha/beta/rc tags.
release = '1.2.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'blistdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'blist.tex', u'blist Documentation',
   u'Stutzbach Enterprises, LLC', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

pngmath_use_preview = True
pngmath_dvipng_args = ['-gamma 1.5', '-D 110', '-bg Transparent']

########NEW FILE########
__FILENAME__ = fuzz
#!/usr/bin/python2.5
from __future__ import print_function

from blist import blist
import pprint, random, sys

if len(sys.argv) > 0:
    random.seed(int(sys.argv[1]))
else:
    random.seed(3)

type1 = list
type2 = blist
iterations = 100000

lobs = [type1(), type1()]
blobs = [type2(), type2()]

def get_method(self, name):
    if name == '__add__':
        return lambda x: operator.add(self, x)
    return getattr(self, name)

methods = {
    '__add__': 1,
    '__contains__': 1,
    '__delitem__': 1,
    '__delslice__': 2,
    '__eq__': 1,
    '__ge__': 1,
    '__getitem__': 1,
    '__getslice__': 2,
    '__gt__': 1,
    '__hash__': 0,
    '__iadd__': 1,
    '__imul__': 1,
    '__iter__': 1,
    '__le__': 1,
    '__len__': 0,
    '__lt__': 1,
    '__mul__': 1,
    '__ne__': 1,
    '__repr__': 0,
    '__reversed__': 1,
    '__rmul__': 1,
    '__setitem__': 2,
    '__setslice__': 3,
    '__str__': 0,
    'append': 1,
    'count': 1,
    'extend': 1,
    'index': 1,
    'insert': 2,
    'pop': 1,
    'remove': 1,
    'reverse': 0,
    'sort': 3,
    }

for name in list(name for name in methods if not hasattr([], name)):
    del methods[name]

# In Python 2, list types and blist types may compare differently
# against other types.
if sys.version_info[0] < 3:
    for name in ('__ge__', '__le__', '__lt__', '__gt__'):
        del methods[name]

left = None
right = None

gen_int = lambda: random.randint(-2**10, 2**10)
gen_float = lambda: random.random()
gen_string = lambda: "foo"
gen_ob_a = lambda: left
gen_ob_b = lambda: right
gen_index_a = lambda: length_left and random.randrange(length_left)
gen_index_b = lambda: length_right and random.randrange(length_right)
gen_hash = lambda: hash
gen_key = lambda: (lambda x: x)

gens = [
    gen_int,
    gen_ob_a,
    gen_ob_b,
    gen_index_a,
    gen_index_b,
    gen_hash,
    gen_key
    ]

def save_obs(ob1, ob2):
    f = open('ob1', 'w')
    f.write(pprint.pformat(ob1))
    f.write('\n')
    f.close()
    f = open('ob2', 'w')
    f.write(pprint.pformat(ob2))
    f.write('\n')
    f.close()

def safe_print(s):
    s = str(s)
    print(s[:300])

def gen_arg():
    gener = random.sample(gens, 1)[0]
    return gener()

def call(f, args):
    try:
        return f(*args)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise
    except BaseException as e:
        return str(type(e))

def smart_eq(a, b, d=None):
    try:
        return a == b
    except RuntimeError:
        pass
    if d is None:
        d = set()
    if id(a) in d and id(b) in d:
        return True
    d.add(id(a))
    d.add(id(b))
    if len(a) != len(b):
        return False
    print(len(a), end=' ')
    sys.stdout.flush()
    if len(a) > 100000:
        print('skipping', end=' ')
        sys.stdout.flush()
        return True
    for i in range(len(a)):
        if not smart_eq(a[i], b[i], d):
            return False
    return True

last = None

for _ in range(iterations):
    if not smart_eq(lobs, blobs):
        print()
        safe_print(last)
        safe_print('Mismatched objects')
        safe_print(lobs)
        print()
        safe_print(blobs)
        break
    print()
    if random.random() < 0.5:
        lobs.reverse()
        blobs.reverse()

    left, right = lobs[0], lobs[1]
    length_left = len(left)
    length_right = len(right)

    if random.random() < 0.01 or length_left + length_right > 1000000:
        print('(%d,%d)' % (len(lobs[0]), len(lobs[1])))
        sys.stdout.flush()
        lobs = [type1(), type1()]
        blobs = [type2(), type2()]
        left, right = lobs[0], lobs[1]
        length_left = len(left)
        length_right = len(right)
    else:
        #print '.',
        #sys.stdout.flush()
        pass
    
    method = random.sample(list(methods), 1)[0]

    args = [gen_arg() for i in range(methods[method])]

    last = ' list: %s%s' % (method, str(tuple(args)))
    print(method, '(%d, %d)' % (length_left, length_right), end=' ') 
    sys.stdout.flush()
    f = get_method(left, method)
    rv1 = call(f, args)
    print('.', end=' ')
    sys.stdout.flush()

    left, right = blobs[0], blobs[1]
    args2 = []
    for arg in args:
        if arg is lobs[0]:
            args2.append(blobs[0])
        elif arg is lobs[1]:
            args2.append(blobs[1])
        else:
            args2.append(arg)
    #print ('type2: %s%s' % (method, str(tuple(args2))))
    f = get_method(left, method)
    rv2 = call(f, args2)
    print('.', end=' ')
    sys.stdout.flush()
    if method in ('__repr__', '__str__'):
        continue
    if type(rv1) == type('') and 'MemoryError' in rv1:
        if method.startswith('__i'):
            lobs = [type1(), type1()]
            blobs = [type2(), type2()]
        continue
    if type(rv2) == type(''):
        rv2 = rv2.replace('blist', 'list')
    elif type(rv2) == type2 and random.random() < 0.25:
        blobs[0] = rv2
        lobs[0] = rv1

    if not smart_eq(rv1, rv2):
        if method == 'sort' and length_left == 1:
            continue

        save_obs(lobs, blobs)
        print()
        safe_print(lobs)
        print()
            
        #print last
        safe_print('Mismatched return values')
        safe_print(rv1)
        print()
        safe_print(rv2)
        sys.exit(0)


########NEW FILE########
__FILENAME__ = blist
#!/usr/bin/python

"""

Copyright 2007 Stutzbach Enterprises, LLC (daniel@stutzbachenterprises.com)

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer. 
   2. Redistributions in binary form must reproduce the above
      copyright notice, this list of conditions and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution. 
   3. The name of the author may not be used to endorse or promote
      products derived from this software without specific prior written
      permission. 

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

Motivation and Design Goals
---------------------------

The goal of this module is to provide a list-like type that has
better asymptotic performance than Python lists, while maintaining
similar performance for lists with few items.

I was driven to write this type by the work that I do.  I frequently
need to work with large lists, and run into efficiency problems when I
need to insert or delete elements in the middle of the list.  I'd like
a type that looks, acts, and quacks like a Python list while offering
good asymptotic performance for all common operations.

A could make a type that has good asymptotic performance, but poor
relative performance on small lists.  That'd be pretty easy to achieve
with, say, red-black trees.  While sometimes I do need good asymptotic
performance, other times I need the speed of Python's array-based
lists for operating on a small list in a tight loop.  I don't want to
have to think about which one to use.  I want one type with good
performance in both cases.

In other words, it should "just work".

I don't propose replacing the existing Python list implementation.  I
am neither that ambitious, and I appreciate how tightly optimized and
refined the existing list implementation is.  I would like to see this
type someday included in Python's collections module, so users with
similar needs can make use of it.  

The data structure I've created to solve the problem is a variation of
a B+Tree, hence I call it the "BList".  It has good asymptotic
performance for all operations, even for some operations you'd expect
to still be O(N).  For example:

    >>> from blist import BList
    >>> n = 10000000               # n = 10 million
    >>> b = BList([0])             # O(1)
    >>> bigb = b * n               # O(log n)
    >>> bigb2 = bigb[1:-1]         # O(log n)
    >>> del bigb2[5000000]         # O(log n)
    
With BLists, even taking a slice (line 4) takes O(log n) time.  This
wonderful feature is because BLists can implement copy-on-write.  More
on that later.

Thus far, I have only implemented a Python version of BList, as a
working prototype.  Obviously, the Python implementation isn't very
efficient at all, but it serves to illustrate the important algorithms.
Later, I plan to implement a C version, which should have comparable
performance to ordinary Python lists when operating on small lists.
The Python version of BLists only outperforms Python lists when the
lists are VERY large.

Basic Idea
----------

BLists are based on B+Trees are a dictionary data structure where each
element is a (key, value) pair and the keys are kept in sorted order.
B+Trees internally use a tree representation.  All data is stored in
the leaf nodes of the tree, and all leaf nodes are at the same level.
Unlike binary trees, each node has a large number of children, stored
as an array of references within the node.  The B+Tree operations ensure
that each node always has between "limit/2" and "limit" children
(except the root which may have between 0 and "limit" children).  When
a B+Tree has fewer than "limit/2" elements, they will all be contained
in a single node (the root).

Wikipedia has a diagram that may be helpful for understanding the
basic structure of a B+Tree:
    http://en.wikipedia.org/wiki/B+_tree

Of course, we don't want a dictionary.  We want a list.  

In BLists, the "key" is implicit: it's the in-order location of the value.
Instead of keys, each BList node maintains a count of the total number
of data elements beneath it in the tree.  This allows walking the tree
efficiently by keeping track of how far we've moved when passing by a
child node.  The tree structure gives us O(log n) for most operations,
asymptotically.

When the BList has fewer than "limit/2" data elements, they are all
stored in the root node.  In other words, for small lists a BList
essentially reduces to an array.  It should have almost identical
performance to a regular Python list, as only one or two extra if()
statements will be needed per method call.

Adding elements
---------------

Elements are inserted recursively.  Each node determines which child
node contains the insertion point, and calls the insertion routine of
that child.

When we add elements to a BList node, the node may overflow (i.e.,
have more than "limit" elements).  Instead of overflowing, the node
creates a new BList node and gives half of its elements to the new
node.  When the inserting function returns, the function informs its
parent about the new sibling.  This causes the parent to add the new
node as a child.  If this causes the parent to overflow, it creates a
sibling of its own, notifies its parent, and so on.

When the root of the tree overflows, it must increase the depth of the
tree.  The root creates two new children and splits all of its former
references between these two children (i.e., all former children are now
grandchildren).

Removing an element
-------------------

Removing an element is also done recursively.  Each node determines
which child node contains the element to be removed, and calls the
removal routine of that child.

Removing an element may cause an underflow (i.e., fewer than "limit/2"
elements).  It's the parent's job to check if a child has underflowed
after any operation that might cause an underflow.  The parent must
then repair the child, either by borrowing elements from one of the
child's sibling or merging the child with one of its sibling.  It the
parent performs a merge, this may also cause its parent to underflow.

If a node has only one element, the tree collapses.  The node replaces
its one child with its grandchildren.  When removing a single element,
this can only happen at the root.

Removing a range
----------------

The __delslice__ method to remove a range of elements is the most
complex operation for a BList to perform.  The first step is to locate
the common parent of all the elements to be removed.  The parent
deletes any children who will be completely deleted (i.e., they are
entirely within the range to be deleted).  The parent also has to deal
with two children who may be partially deleted: they contain the left
and right boundaries of the deletion range.

The parent calls the deletion operation recursively on these two
children.  When the call returns, the children must return a valid
BList, but they may be in an underflow state, and, worse, they may
have needed to collapse the tree.  To make life a little easier, the
children return an integer indicating how many levels of the tree
collapsed (if any).  The parent now has two adjacent subtrees of
different heights that need to be put back into the main tree (to keep
it balanced).

To accomplish this goal, we use a merge-tree operation, defined below.
The parent merges the two adjacent subtrees into a single subtree,
then merges the subtree with one of its other children.  If it has no
other children, then the parent collapses to become the subtree and
indicates to its parent the total level of collapse.

Merging subtrees
----------------

The __delslice__ method needs a way to merge two adjacent subtrees of
potentially different heights.  Because we only need to merge *adjacent*
subtrees, we don't have to handle inserting a subtree into the middle of
another.  There are only two cases: the far-left and the far-right.  If
the two subtrees are the same height, this is a pretty simple operation where
we join their roots together.  If the trees are different heights, we
merge the smaller into the larger as follows.  Let H be the difference
in their heights.  Then, recurse through the larger tree by H levels
and insert the smaller subtree there.

Retrieving a range and copy-on-write
------------------------------------

One of the most powerful features of BLists is the ability to support
copy-on-write.  Thus far we have described a BLists as a tree
structure where parents contain references to their children.  None of
the basic tree operations require the children to maintain references
to their parents or siblings.  Therefore, it is possible for a child
to have *multiple parents*.  The parents can happily share the child
as long as they perform read-only operations on it.  If a parent wants
to modify a child in any way, it first checks the child's reference
count.  If it is 1, the parent has the only reference and can proceed.
Otherwise, the parent must create a copy of the child, and relinquish
its reference to the child.

Creating a copy of a child doesn't implicitly copy the child's
subtree.  It just creates a new node with a new reference to the
child.  In other words, the child and the copy are now joint parents
of their children.

This assumes that no other code will gain references to internal BList
nodes.  The internal nodes are never exposed to the user, so this is a
safe assumption.  In the worst case, if the user manages to gain a
reference to an internal BList node (such as through the gc module),
it will just prevent the BList code from modifying that node.  It will
create a copy instead.  User-visible nodes (i.e., the root of a tree)
have no parents and are never shared children.

Why is this copy-on-write operation so useful?

Consider the common idiom of performing an operation on a slice of a
list.  Normally, this requires making a copy of that region of the
list, which is expensive if the region is large.  With copy-on-write,
__getslice__ takes logarithmic time and logarithmic memory.

As a fun but slightly less practical example, ever wanted to make
REALLY big lists?  Copy-on-write also allows for a logarithmic time
and logarithmic memory implementation of __mul__.

>>> little_list = BList([0])
>>> big_list = little_list * 2**512           <-- 220 milliseconds
>>> print big_list.__len__()
13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096

(iterating over big_list is not recommended)

Comparison of cost of operations with list()
---------------------------------------------

n is the size of "self", k is the size of the argument.  For slice
operations, k is the length of the slice.  For __mul__, k is the value
of the argument.

   Operation            list               BList
---------------     ------------  -----------------------
init from seq       O(k)          O(k)
copy                O(k)          O(1)
append              O(1)          O(log n)
insert              O(n)          O(log n)
__mul__             O(n*k)        O(log k)
__delitem__         O(n)          O(log n)
__len__             O(1)          O(1)
iteration           O(n)          O(n)
__getslice__        O(k)          O(log n)
__delslice__        O(n)          O(log n + k)
__setslice__        O(n+k)        O(log n + log k)        [1]
extend              O(k)          O(log n + log k)        [1]
__sort__            O(n*log n)    O(n*log n)              [2]
index               O(k)          O(log n + k)
remove              O(n)          O(n)
count               O(n)          O(n)
extended slicing    O(k)          O(k*log n)
__cmp__             O(min(n,k))   O(min(n,k))

[1]: Plus O(k) if the sequence being added is not also a BList
[2]: list.__sort__ requires O(n) worst-case extra memory, while BList.__sort
     requires only (log n) extra memory

For BLists smaller than "limit" elements, each operation essentially
reduces to the equivalent list operation, so there is little-to-no
overhead for the common case of small lists.


Implementation Details
======================

Structure
---------

Each node has four member variables:

leaf:     true if this node is a leaf node (has user data as children),
          false if this node is an interior node (has other nodes as children)

children: an array of references to the node's children

n:        the total number of user data elements below the node.
          equal to len(children) for leaf nodes

refcount: None for a root node,
          otherwise, the number of other nodes with references to this node
                     (i.e., parents)
          
Global Constants
----------------

limit:    the maximum size of .children, must be even and >= 8
half:     limit//2, the minimum size of .children for a valid node,
          other than the root

Definitions
-----------

- The only user-visible node is the root node.
- All leaf nodes are at the same height in the tree.
- If the root node has exactly one child, the root node must be a leaf node.
- Nodes never maintain references to their parents or siblings, only to
  their children.
- Users call methods of the user-node, which may call methods of its
  children, who may call their children recursively.
- A node's user-visible elements are numbered from 0 to self.n-1.  These are
  called "positions".  
- A node's children are numbered 0 to len(self.children)-1.  These are
  called "indexes" and should not be confused with positions.

- Completely private functions (called via self.) may temporarily
  violate these invariants.
- Functions exposed to the user must ensure these invariants are true
  when they return.
- Some functions are visible to the parent of a child node.  When
  these functions return, the invariants must be true as if the child
  were a root node.

Conventions
-----------

- Function that may be called by either users or the object's parent
  either do not begin with underscores, or they begin and end with __.
- A function that may only be called by the object itself begins with
  __ and do not end with underscores.
- Functions that may be called by an object's parent, but not by the user,
  begin with a single underscore.

Other rules
-----------

- If a function may cause a BList to overflow, the function has the
  following return types:
  - None, if the BList did not overflow
  - Otherwise, a valid BList subtree containing a new right-hand sibling
    for the BList that was called.
- BList objects may modify their children if the child's .refcount is
  1.  If the .refcount is greater than 1, the child is shared by another
  parent. The object must copy the child, decrement the child's reference
  counter, and modify the copy instead.
- If an interior node has only one child, before returning it must
  collapse the tree so it takes on the properties of its child.  This
  may mean the interior node becomes a leaf.
- An interior node may return with no children.  The parent must then
  remove the interior node from the parent's children.
- If a function may cause an interior node to collapse, it must have
  the following return types:
  - 0, if the BList did not collapse, or if it is now empty (self.n == 0)
  - A positive integer indicating how many layers have collapsed (i.e., how
    much shorter the subtree is compared to before the function call).
- If a user-visible function does not modify the BList, the BList's
  internal structure must not change.  This is important for
  supporting iterators.

Observations
------------

- User-nodes always have a refcount of at least 1
- User-callable methods may not cause the reference counter to decrement.
- If a parent calls a child's method that may cause the child to
  underflow, the parent must detect the underflow and merge the child
  before returning.

Pieces not implemented here that will be needed in a C version
--------------------------------------------------------------

- __deepcopy__
- support for pickling
- container-type support for the garbage collector

Suspected Bugs:
 - None currently, but needs more testing
 - Passes test_list.py :-)

User-visible Differences from list():
 - If you modify the list in the middle of an iteration and continue
   to iterate, the behavior is different.  BList iteration could be
   implemented the same way as in list, but then iteration would have
   O(n * log n) cost instead of O(n).  I'm okay with the way it is.

Miscellaneous:
 - All of the reference counter stuff is redundant with the reference
   counting done internally on Python objects.  In C we can just peak
   at the reference counter stored in all Python objects.

"""

import copy, types
from itertools import *

########################################################################
# Global constants

limit = 8               # Maximum size, currently low (for testing purposes)
half = limit//2         # Minimum size
assert limit % 2 == 0   # Must be divisible by 2
assert limit >= 8       # The code assumes each block is at least this big

PARANOIA = 2            # Checks reference counters
DEBUG    = 1            # Checks correctness
NO_DEBUG = 0            # No checking

debugging_level = NO_DEBUG

leaked_reference = False

########################################################################
# Simulate utility functions from the Python C API.  These functions
# help us detect the case where we have a self-referential list and a
# user has asked us to print it...
Py_Repr = []
def Py_ReprEnter(obj):
    if obj in Py_Repr: return 1
    Py_Repr.append(obj)
    return 0

def Py_ReprLeave(obj):
    for i in range(len(Py_Repr)-1,-1,-1):
        if Py_Repr[i] == obj:
            del Py_Repr[i]
            break

# Needed for sort
builtin_cmp = cmp

########################################################################
# Decorators are for error-checking and code clarity.  They verify
# (most of) the invariances given above.  They're replaced with no_op()
# if debugging_level == NO_DEBUG.

def modifies_self(f):
    "Decorator for member functions which require write access to self"
    def g(self, *args, **kw):
        assert self.refcount == 1 or self.refcount is None
        rv = f(self, *args, **kw)
        assert self.refcount == 1 or not self.refcount, self.refcount
        return rv
    return g

def parent_callable(f):
    "Indicates the member function may be called by the BList's parent"
    def g(self, *args, **kw):
        #self._check_invariants()
        rv = f(self, *args, **kw)
        self._check_invariants()
        return rv
    return g

def user_callable(f):
    "Indicates a user callable function"
    def g(self, *args, **kw):
        assert self.refcount >= 1 or self.refcount is None
        refs = self.refcount
        self._check_invariants()
        rv = f(self, *args, **kw)
        assert self.refcount == refs
        self._check_invariants()
        return rv
    return g

def may_overflow(f):
    "Indicates the member function may cause an overflow"
    def g(self, *args, **kw):
        rv = f(self, *args, **kw)
        if rv is not None:
            assert isinstance(rv, BList)
            rv._check_invariants()
        self._check_invariants()
        return rv
    return g

def may_collapse(f):
    "Indicates the member function may collapse the subtree"
    def g(self, *args, **kw):
        #height1 = self._get_height()   ## Not reliable just before collapse
        rv = f(self, *args, **kw)
        #height2 = self._get_height()
        assert isinstance(rv, int) and rv >= 0
        self._check_invariants()
        return rv
    return g

def no_op(f):
    return f

if debugging_level == 0:
    modifies_self = no_op
    parent_callable = no_op
    user_callable = no_op
    may_overflow = no_op
    may_collapse = no_op

########################################################################
# Utility functions and decorators for fixing up index parameters.

def sanify_index(n, i):
    if isinstance(i, slice): return i
    if i < 0:
        i += n
    return i

def strong_sanify_index(n, i):
    if isinstance(i, slice): return i
    if i < 0:
        i += n
        if i < 0:
            i = 0
    elif i > n:
        i = n
    return i

def allow_negative1(f):
    "Decarator for allowing a negative position as the first argument"
    def g(self, i, *args, **kw):
        i = sanify_index(self.n, i)
        return f(self, i, *args, **kw)
    return g

def allow_negative2(f):
    "Decarator for allowing a negative position as the 1st and 2nd args"
    def g(self, i, j, *args, **kw):
        i = sanify_index(self.n, i)
        j = sanify_index(self.n, j)
        return f(self, i, j, *args, **kw)
    return g

########################################################################
# An extra constructor and the main class

def _BList(other=[]):
    "Create a new BList for internal use"

    self = BList(other)
    self.refcount = 1
    return self

class BList(object):
    __slots__ = ('leaf', 'children', 'n', 'refcount')

    def _check_invariants(self):
        if debugging_level == NO_DEBUG: return
        try:
            if debugging_level == PARANOIA:
                self.__check_reference_count()
            if self.leaf:
                assert self.n == len(self.children)
            else:
                assert self.n == sum(child.n for child in self.children)
                assert len(self.children) > 1 or len(self.children) == 0, len(self.children)
                for child in self.children:
                    assert isinstance(child, BList)
                    assert half <= len(child.children) <= limit
            assert self.refcount >= 1 or self.refcount is None \
                   or (self.refcount == 0 and not self.children)
        except:
            print self.debug()
            raise

    def _check_invariants_r(self):
        if debugging_level == NO_DEBUG: return
        self._check_invariants()
        if self.leaf: return
        for c in self.children:
            c._check_invariants_r()

    def __init__(self, seq=[]):
        self.leaf = True

        # Points to children
        self.children = []

        # Number of leaf elements that are descendents of this node
        self.n = 0

        # User visible objects have a refcount of None
        self.refcount = None

        # We can copy other BLists in O(1) time :-)
        if isinstance(seq, BList):
            self.__become(seq)
            self._check_invariants()
            return

        self.__init_from_seq(seq)

    ####################################################################
    # Useful internal utility functions

    @modifies_self
    def __become(self, other):
        "Turns self into a clone of other"

        if id(self) == id(other):
            self._adjust_n()
            return
        if not other.leaf:
            for child in other.children:
                child._incref()
        if other.refcount is not None:
            other._incref()  # Other may be one of our children
        self.__forget_children()
        self.n = other.n
        self.children[:] = other.children
        self.leaf = other.leaf
        if other.refcount is not None:
            other._decref()

    @parent_callable
    @modifies_self
    def _adjust_n(self):
        "Recompute self.n"
        if self.leaf:
            self.n = len(self.children)
        else:
            self.n = sum(x.n for x in self.children)

    @parent_callable
    def _locate(self, i):
        """We are searching for the child that contains leaf element i.

        Returns a 3-tuple: (the child object, our index of the child,
                            the number of leaf elements before the child)
        """
        if self.leaf:
            return self.children[i], i, i

        so_far = 0
        for k in range(len(self.children)):
            p = self.children[k]
            if i < so_far + p.n:
                return p, k, so_far
            so_far += p.n
        else:
            return self.children[-1], len(self.children)-1, so_far - p.n

    def __get_reference_count(self):
        "Figure out how many parents we have"
        import gc

        # Count the number of times we are pointed to by a .children
        # list of a BList

        gc.collect()
        objs = gc.get_referrers(self)
        total = 0
        for obj in objs:
            if isinstance(obj, list):
                # Could be a .children
                objs2 = gc.get_referrers(obj)
                for obj2 in objs2:
                    # Could be a BList
                    if isinstance(obj2, BList):
                        total += len([x for x in obj2.children if x is self])
        return total

    def __check_reference_count(self):
        "Validate that we're counting references properly"
        total = self.__get_reference_count()

        if self.refcount is not None:
            # The caller may be about to increment the reference counter, so
            # total == self.refcount or total+1 == self.refcount are OK
            assert total == self.refcount or total+1 == self.refcount,\
                   (total, self.refcount)

        # Reset the flag to avoid repeatedly raising the assertion
        global leaked_reference
        x = leaked_reference
        leaked_reference = False
        assert not x, x

    def _decref(self):
        assert self.refcount is not None
        assert self.refcount > 0
        if self.refcount == 1:
            # We're going to be garbage collected.  Remove all references
            # to other objects.
            self.__forget_children()
        self.refcount -= 1

    def _incref(self):
        assert self.refcount is not None
        self.refcount += 1

    @parent_callable
    def _get_height(self):
        """Find the current height of the tree.

        We could keep an extra few bytes in each node rather than
        figuring this out dynamically, which would reduce the
        asymptotic complexitiy of a few operations.  However, I
        suspect it's not worth the extra overhead of updating it all
        over the place.
        """

        if self.leaf:
            return 1
        return 1 + self.children[-1]._get_height()

    @modifies_self
    def __forget_children(self, i=0, j=None):
        "Remove links to some of our children, decrementing their refcounts"
        if j is None: j = len(self.children)
        if not self.leaf:
            for k in range(i, j):
                self.children[k]._decref()
        del self.children[i:j]

    def __del__(self):
        """In C, this would be a tp_clear function instead of a __del__.

        Because of the way Python's garbage collector handles __del__
        methods, we can end up with uncollectable BList objects if the
        user creates circular references.  In C with a tp_clear
        function, this wouldn't be a problem.
        """
        if self.refcount:
            global leaked_reference
            leaked_reference = True
        try:
            self.refcount = 1          # Make invariance-checker happy
            self.__forget_children()
            self.refcount = 0
        except:
            import traceback
            traceback.print_exc()
            raise

    @modifies_self
    def __forget_child(self, i):
        "Removes links to one child"
        self.__forget_children(i, i+1)

    @modifies_self
    def __prepare_write(self, pt):
        """We are about to modify the child at index pt.  Prepare it.

        This function returns the child object.  If the caller has
        other references to the child, they must be discarded as they
        may no longer be valid.

        If the child's .refcount is 1, we simply return the
        child object.

        If the child's .refcount is greater than 1, we:

        - copy the child object
        - decrement the child's .refcount
        - replace self.children[pt] with the copy
        - return the copy
        """

        if pt < 0:
            pt = len(self.children) + pt
        if not self.leaf and self.children[pt].refcount > 1:
            new_copy = _BList()
            new_copy.__become(self.children[pt])
            self.children[pt]._decref()
            self.children[pt] = new_copy
        return self.children[pt]

    @staticmethod
    def __new_sibling(children, leaf):
        """Non-default constructor.  Create a node with specific children.

        We steal the reference counters from the caller.
        """

        self = _BList()
        self.children = children
        self.leaf = leaf
        self._adjust_n()
        return self

    ####################################################################
    # Functions for manipulating the tree

    @modifies_self
    def __borrow_right(self, k):
        "Child k has underflowed.  Borrow from k+1"
        p = self.children[k]
        right = self.__prepare_write(k+1)
        total = len(p.children) + len(right.children)
        split = total//2

        assert split >= half
        assert total-split >= half

        migrate = split - len(p.children)

        p.children.extend(right.children[:migrate])
        del right.children[:migrate]
        right._adjust_n()
        p._adjust_n()

    @modifies_self
    def __borrow_left(self, k):
        "Child k has underflowed.  Borrow from k-1"
        p = self.children[k]
        left = self.__prepare_write(k-1)
        total = len(p.children) + len(left.children)
        split = total//2

        assert split >= half
        assert total-split >= half

        migrate = split - len(p.children)

        p.children[:0] = left.children[-migrate:]
        del left.children[-migrate:]
        left._adjust_n()
        p._adjust_n()

    @modifies_self
    def __merge_right(self, k):
        "Child k has underflowed.  Merge with k+1"
        p = self.children[k]
        for p2 in self.children[k+1].children:
            if not self.children[k+1].leaf:
                p2._incref()
            p.children.append(p2)
        self.__forget_child(k+1)
        p._adjust_n()

    @modifies_self
    def __merge_left(self, k):
        "Child k has underflowed.  Merge with k-1"
        p = self.children[k]
        if not self.children[k-1].leaf:
            for p2 in self.children[k-1].children:
                p2._incref()
        p.children[:0] = self.children[k-1].children
        self.__forget_child(k-1)
        p._adjust_n()

    @staticmethod
    def __concat(left_subtree, right_subtree, height_diff):
        """Concatenate two trees of potentially different heights.

        The parameters are the two trees, and the difference in their
        heights expressed as left_height - right_height.

        Returns a tuple of the new, combined tree, and an integer.
        The integer expresses the height difference between the new
        tree and the taller of the left and right subtrees.  It will
        be 0 if there was no change, and 1 if the new tree is taller
        by 1.
        """

        assert left_subtree.refcount == 1
        assert right_subtree.refcount == 1

        adj = 0

        if height_diff == 0:
            root = _BList()
            root.children = [left_subtree, right_subtree]
            root.leaf = False
            collapse = root.__underflow(0)
            if not collapse:
                collapse = root.__underflow(1)
            if not collapse:
                adj = 1
            overflow = None
        elif height_diff > 0: # Left is larger
            root = left_subtree
            overflow = root._insert_subtree(-1, right_subtree,
                                            height_diff - 1)
        else: # Right is larger
            root = right_subtree
            overflow = root._insert_subtree(0, left_subtree,
                                            -height_diff - 1)
        adj += -root.__overflow_root(overflow)

        return root, adj

    @staticmethod
    def __concat_subtrees(left_subtree, left_depth, right_subtree,right_depth):
        """Concatenate two subtrees of potentially different heights.

        Returns a tuple of the new, combined subtree and its depth.

        Depths are the depth in the parent, not their height.
        """

        root, adj = BList.__concat(left_subtree, right_subtree,
                                   -(left_depth - right_depth))
        return root, max(left_depth, right_depth) - adj

    @staticmethod
    def __concat_roots(left_root, left_height, right_root, right_height):
        """Concatenate two roots of potentially different heights.

        Returns a tuple of the new, combined root and its height.

        Heights are the height from the root to its leaf nodes.
        """

        root, adj = BList.__concat(left_root, right_root,
                                   left_height - right_height)
        return root, max(left_height, right_height) + adj

    @may_collapse
    @modifies_self
    def __collapse(self):
        "Collapse the tree, if possible"
        if len(self.children) != 1 or self.leaf:
            self._adjust_n()
            return 0

        p = self.children[0]
        self.__become(p)
        return 1

    @may_collapse
    @modifies_self
    def __underflow(self, k):
        """Check if children k-1, k, or k+1 have underflowed.

        If so, move things around until self is the root of a valid
        subtree again, possibly requiring collapsing the tree.

        Always calls self._adjust_n() (often via self.__collapse()).
        """

        if self.leaf:
            self._adjust_n()
            return 0

        if k < len(self.children):
            p = self.__prepare_write(k)
            short = half - len(p.children)

            while short > 0:
                if k+1 < len(self.children) \
                   and len(self.children[k+1].children) - short >= half:
                    self.__borrow_right(k)
                elif k > 0 and len(self.children[k-1].children) - short >=half:
                    self.__borrow_left(k)
                elif k+1 < len(self.children):
                    self.__merge_right(k)
                elif k > 0:
                    self.__merge_left(k)
                    k = k - 1
                else:
                    # No siblings for p
                    return self.__collapse()

                p = self.__prepare_write(k)
                short = half - len(p.children)

        if k > 0 and len(self.children[k-1].children) < half:
            collapse = self.__underflow(k-1)
            if collapse: return collapse
        if k+1 < len(self.children) \
               and len(self.children[k+1].children) <half:
            collapse = self.__underflow(k+1)
            if collapse: return collapse

        return self.__collapse()

    @modifies_self
    def __overflow_root(self, overflow):
        "Handle the case where a user-visible node overflowed"
        self._check_invariants()
        if not overflow: return 0
        child = _BList(self)
        self.__forget_children()
        self.children[:] = [child, overflow]
        self.leaf = False
        self._adjust_n()
        self._check_invariants()
        return -1

    @may_overflow
    @modifies_self
    def __insert_here(self, k, item):
        """Insert 'item', which may be a subtree, at index k.

        Since the subtree may have fewer than half elements, we may
        need to merge it after insertion.

        This function may cause self to overflow.  If it does, it will
        take the upper half of its children and put them in a new
        subtree and return the subtree.  The caller is responsible for
        inserting this new subtree just to the right of self.

        Otherwise, it returns None.

        """

        if k < 0:
            k += len(self.children)

        if len(self.children) < limit:
            self.children.insert(k, item)
            collapse = self.__underflow(k)
            assert not collapse
            self._adjust_n()
            return None

        sibling = BList.__new_sibling(self.children[half:], self.leaf)
        del self.children[half:]

        if k < half:
            self.children.insert(k, item)
            collapse = self.__underflow(k)
            assert not collapse
        else:
            sibling.children.insert(k - half, item)
            collapse = sibling.__underflow(k-half)
            assert not collapse
            sibling._adjust_n()
        self._adjust_n()
        return sibling

    @may_overflow
    @modifies_self
    def _insert_subtree(self, side, subtree, depth):
        """Recurse depth layers, then insert subtree on the left or right

        This function may cause an overflow.

        depth == 0 means insert the subtree as a child of self.
        depth == 1 means insert the subtree as a grandchild, etc.

        """
        assert side == 0 or side == -1

        self._check_invariants()
        subtree._check_invariants()

        self.n += subtree.n

        if depth:
            p = self.__prepare_write(side)
            overflow = p._insert_subtree(side, subtree, depth-1)
            if not overflow: return None
            subtree = overflow

        if side < 0:
            side = len(self.children)

        sibling = self.__insert_here(side, subtree)

        return sibling

    @modifies_self
    def __reinsert_subtree(self, k, depth):
        'Child at position k is too short by "depth".  Fix it'

        assert self.children[k].refcount == 1, self.children[k].refcount
        subtree = self.children.pop(k)
        if len(self.children) > k:
            # Merge right
            p = self.__prepare_write(k)
            overflow = p._insert_subtree(0, subtree, depth-1)
            if overflow:
                self.children.insert(k+1, overflow)
        else:
            # Merge left
            p = self.__prepare_write(k-1)
            overflow = p._insert_subtree(-1, subtree, depth-1)
            if overflow:
                self.children.insert(k, overflow)
        return self.__underflow(k)

    ####################################################################
    # The main insert and deletion operations

    @may_overflow
    @modifies_self
    def _insert(self, i, item):
        """Recursive to find position i, and insert item just there.

        This function may cause an overflow.

        """
        if self.leaf:
            return self.__insert_here(i, item)

        p, k, so_far = self._locate(i)
        del p
        self.n += 1
        p = self.__prepare_write(k)
        overflow = p._insert(i - so_far, item)
        del p
        if not overflow: return
        return self.__insert_here(k+1, overflow)

    @user_callable
    @modifies_self
    def __iadd__(self, other):
        # Make not-user-visible roots for the subtrees
        right = _BList(other)
        left = _BList(self)

        left_height = left._get_height()
        right_height = right._get_height()

        root = BList.__concat_subtrees(left, -left_height,
                                       right, -right_height)[0]
        self.__become(root)
        root._decref()
        return self

    @parent_callable
    @may_collapse
    @modifies_self
    def _delslice(self, i, j):
        """Recursive version of __delslice__

        This may cause self to collapse.  It returns None if it did
        not.  If a collapse occured, it returns a positive integer
        indicating how much shorter this subtree is compared to when
        _delslice() was entered.

        Additionally, this function may cause an underflow.

        """

        if i == 0 and j >= self.n:
            # Delete everything.
            self.__forget_children()
            self.n = 0
            return 0

        if self.leaf:
            del self.children[i:j]
            self.n = len(self.children)
            return 0

        p, k, so_far = self._locate(i)
        p2, k2, so_far2 = self._locate(j-1)
        del p
        del p2

        if k == k2:
            # All of the deleted elements are contained under a single
            # child of this node.  Recurse and check for a short
            # subtree and/or underflow

            assert so_far == so_far2
            p = self.__prepare_write(k)
            depth = p._delslice(i - so_far, j - so_far)
            if not depth:
                return self.__underflow(k)
            return self.__reinsert_subtree(k, depth)

        # Deleted elements are in a range of child elements.  There
        # will be:
        # - a left child (k) where we delete some (or all) of its children
        # - a right child (k2) where we delete some (or all) of it children
        # - children in between who are deleted entirely

        # Call _delslice recursively on the left and right
        p = self.__prepare_write(k)
        collapse_left = p._delslice(i - so_far, j - so_far)
        del p
        p2 = self.__prepare_write(k2)
        collapse_right = p2._delslice(max(0, i - so_far2), j - so_far2)
        del p2

        deleted_k = False
        deleted_k2 = False

        # Delete [k+1:k2]
        self.__forget_children(k+1, k2)
        k2 = k+1

        # Delete k1 and k2 if they are empty
        if not self.children[k2].n:
            self.children[k2]._decref()
            del self.children[k2]
            deleted_k2 = True
        if not self.children[k].n:
            self.children[k]._decref()
            del self.children[k]
            deleted_k = True

        if deleted_k and deleted_k2: # No messy subtrees.  Good.
            return self.__collapse()

        # The left and right may have collapsed and/or be in an
        # underflow state.  Clean them up.  Work on fixing collapsed
        # trees first, then worry about underflows.

        if not deleted_k and not deleted_k2 \
               and collapse_left and collapse_right:
            # Both exist and collapsed.  Merge them into one subtree.
            left = self.children.pop(k)
            right = self.children.pop(k)
            subtree, depth = BList.__concat_subtrees(left, collapse_left,
                                                     right, collapse_right)
            del left
            del right
            self.children.insert(k, subtree)
            
        elif deleted_k:
            # Only the right potentially collapsed, point there.
            depth = collapse_right
            # k already points to the old k2, since k was deleted
        elif not deleted_k2 and not collapse_left:
            # Only the right potentially collapsed, point there.
            k = k + 1
            depth = collapse_right
        else:
            depth = collapse_left

        # At this point, we have a potentially short subtree at k,
        # with depth "depth".

        if not depth or len(self.children) == 1:
            # Doesn't need merging, or no siblings to merge with
            return depth + self.__underflow(k)

        # We definitely have a short subtree at k, and we have other children
        return self.__reinsert_subtree(k, depth)

    @modifies_self
    def __init_from_seq(self, seq):
        # Try the common case of a sequence <= limit in length
        iterator = iter(seq)
        for i in range(limit):
            try:
                x = iterator.next()
            except StopIteration:
                self.n = len(self.children)
                self._check_invariants()
                return
            except AttributeError:
                raise TypeError('instance has no next() method')
            self.children.append(x)
        self.n = limit
        assert limit == len(self.children)
        self._check_invariants()

        # No such luck, build bottom-up instead.
        # The sequence data so far goes in a leaf node.
        cur = _BList()
        self._check_invariants()
        cur._check_invariants()
        cur.__become(self)
        cur._check_invariants()
        self.__forget_children()
        cur._check_invariants()

        forest = Forest()
        forest.append_leaf(cur)
        cur = _BList()

        while 1:
            try:
                x = iterator.next()
            except StopIteration:
                break
            if len(cur.children) == limit:
                cur.n = limit
                cur._check_invariants()
                forest.append_leaf(cur)
                cur = _BList()
            cur.children.append(x)

        if cur.children:
            forest.append_leaf(cur)
            cur.n = len(cur.children)
        else:
            cur._decref()

        final = forest.finish()
        self.__become(final)
        final._decref()

    ########################################################################
    # Below here are other user-callable functions built using the above
    # primitives and user functions.

    @parent_callable
    def _str(self, f):
        """Recursive version of __str__

        Not technically user-callable, but nice to keep near the other
        string functions.
        """

        if self.leaf:
            return ', '.join(f(x) for x in self.children)
        else:
            return ', '.join(x._str(f) for x in self.children)

    @user_callable
    def __str__(self):
        "User-visible function"
        if Py_ReprEnter(self):
            return '[...]'
        #rv = 'BList(%s)' % self._str()
        rv = '[%s]' % self._str(str)
        Py_ReprLeave(self)
        return rv

    @user_callable
    def __repr__(self):
        "User-visible function"
        if Py_ReprEnter(self):
            return '[...]'
        #rv = 'BList(%s)' % self._str()
        rv = '[%s]' % self._str(repr)
        Py_ReprLeave(self)
        return rv

    def debug(self, indent=''):
        import gc
        gc.collect()
        "Return a string that shows the internal structure of the BList"
        indent = indent + ' '
        if not self.leaf:
            rv = 'blist(leaf=%s, n=%s, r=%s, %s)' % (
                str(self.leaf), str(self.n), str(self.refcount),
                '\n%s' % indent +
                ('\n%s' % indent).join([x.debug(indent+'  ')
                                        for x in self.children]))
        else:
            rv = 'blist(leaf=%s, n=%s, r=%s, %s)' % (
                str(self.leaf), str(self.n), str(self.refcount),
                str(self.children))
        return rv

    @user_callable
    @allow_negative1
    def __getitem__(self, i):
        "User-visible function"
        if isinstance(i, slice):
            start, stop, step = i.indices(self.n)
            return BList(self[j] for j in xrange(start, stop, step))

        if type(i) != types.IntType and type(i) != types.LongType:
            raise TypeError('list indices must be integers')

        if i >= self.n or i < 0:
            raise IndexError

        if self.leaf:
            return self.children[i]

        p, k, so_far = self._locate(i)
        assert i >= so_far
        return p.__getitem__(i - so_far)

    @user_callable
    @modifies_self
    @allow_negative1
    def __setitem__(self, i, y):
        "User-visible function"

        if isinstance(i, slice):
            start, stop, step = i.indices(self.n)
            if step == 1:
                # More efficient
                self[start:stop] = y
                return
            y = _BList(y)
            raw_length = (stop - start)
            length = raw_length//step
            if raw_length % step:
                length += 1
            if length != len(y):
                leny = len(y)
                y._decref()
                raise ValueError('attempt to assign sequence of size %d '
                                 'to extended slice of size %d'
                                 % (leny, length))
            k = 0
            for j in xrange(start, stop, step):
                self[j] = y[k]
                k += 1
            y._decref()
            return

        if i >= self.n or i < 0:
            raise IndexError

        if self.leaf:
            self.children[i] = y
            return

        p, k, so_far = self._locate(i)
        p = self.__prepare_write(k)
        p.__setitem__(i-so_far, y)

    @user_callable
    def __len__(self):
        "User-visible function"
        return self.n

    @user_callable
    def __iter__(self):
        "User-visible function"
        return self._iter(0, None)

    def _iter(self, i, j):
        "Make an efficient iterator between elements i and j"
        if self.leaf:
            return ShortBListIterator(self, i, j)
        return BListIterator(self, i, j)

    @user_callable
    def __cmp__(self, other):
        if not isinstance(other, BList) and not isinstance(other, list):
            return cmp(id(type(self)), id(type(other)))

        iter1 = iter(self)
        iter2 = iter(other)
        x_failed = False
        y_failed = False
        while 1:
            try:
                x = iter1.next()
            except StopIteration:
                x_failed = True
            try:
                y = iter2.next()
            except StopIteration:
                y_failed = True
            if x_failed or y_failed: break

            c = cmp(x, y)
            if c: return c

        if x_failed and y_failed: return 0
        if x_failed: return -1
        return 1

    @user_callable
    def __contains__(self, item):
        for x in self:
            if x == item: return True
        return False

    @user_callable
    @modifies_self
    def __setslice__(self, i, j, other):
        # Python automatically adds len(self) to these values if they
        # are negative.  They'll get incremented a second time below
        # when we use them as slice arguments.  Subtract len(self)
        # from them to keep them at the same net value.
        #
        # If they went positive the first time, that's OK.  Python
        # won't change them any further.

        if i < 0:
            i -= self.n
        if j < 0:
            j -= self.n

        # Make a not-user-visible root for the other subtree
        other = _BList(other)

        # Efficiently handle the common case of small lists
        if self.leaf and other.leaf and self.n + other.n <= limit:
            self.children[i:j] = other.children
            other._decref()
            self._adjust_n()
            return

        left = self
        right = _BList(self)
        del left[i:]
        del right[:j]
        left += other
        left += right

        other._decref()
        right._decref()

    @user_callable
    @modifies_self
    def extend(self, other):
        return self.__iadd__(other)

    @user_callable
    @modifies_self
    def pop(self, i=-1):
        try:
            i = int(i)
        except ValueError:
            raise TypeError('an integer is required')
        rv = self[i]
        del self[i]
        return rv

    @user_callable
    def index(self, item, i=0, j=None):
        i, j, _ = slice(i, j).indices(self.n)
        for k, x in enumerate(self._iter(i, j)):
            if x == item:
                return k + i
        raise ValueError('list.index(x): x not in list')

    @user_callable
    @modifies_self
    def remove(self, item):
        for i, x in enumerate(self):
            if x == item:
                del self[i]
                return
        raise ValueError('list.index(x): x not in list')

    @user_callable
    def count(self, item):
        rv = 0
        for x in self:
            if x == item:
                rv += 1
        return rv

    @user_callable
    @modifies_self
    def reverse(self):
        self.children.reverse()
        if self.leaf: return
        for i in range(len(self.children)):
            p = self.__prepare_write(i)
            p.reverse()

    @user_callable
    def __mul__(self, n):
        if n <= 0:
            return BList()

        power = BList(self)
        rv = BList()

        if n & 1:
            rv += self
        mask = 2

        while mask <= n:
            power += power
            if mask & n:
                rv += power
            mask <<= 1
        return rv

    __rmul__ = __mul__

    @user_callable
    @modifies_self
    def __imul__(self, n):
        self.__become(self * n)
        return self

    @parent_callable
    @modifies_self
    def _merge(self, other, cmp=None, key=None, reverse=False):
        """Merge two sorted BLists into one sorted BList, part of MergeSort

        This function consumes the two input BLists along the way,
        making the MergeSort nearly in-place.  This function gains ownership
        of the self and other objects and must .decref() them if appropriate.

        It returns one sorted BList.

        It operates by maintaining two forests (lists of BList
        objects), one for each of the two inputs lists.  When it needs
        a new leaf node, it looks at the first element of the forest
        and checks to see if it's a leaf.  If so, it grabs that.  If
        not a leaf, it takes that node, removes the root, and prepends
        the children to the forest.  Then, it checks again for a leaf.
        It repeats this process until it is able to acquire a leaf.
        This process avoids the cost of doing O(log n) work O(n) times
        (for a total O(n log n) cost per merge).  It takes O(log n)
        extra memory and O(n) steps.

        We also maintain a forest for the output.  Whenever we fill an
        output leaf node, we append it to the output forest.  We keep
        track of the total number of leaf nodes added to the forest,
        and use that to analytically determine if we have "limit" nodes at the
        end of the forest all of the same height.  When we do, we remove them
        from the forest, place them under a new node, and put the new node on
        the end of the forest.  This guarantees that the output forest
        takes only O(log n) extra memory.  When we're done with the input, we
        merge the forest into one final BList.

        Whenever we finish with an input leaf node, we add it to a
        recyclable list, which we use as a source for nodes for the
        output.  Since the output will use only O(1) more nodes than the
        combined input, this part is effectively in-place.

        Overall, this function uses O(log n) extra memory and takes O(n) time.
        """
        
        other._check_invariants();
        if not cmp:
            cmp = builtin_cmp
    
        recyclable = []
    
        def do_cmp(a, b):
            "Utility function for performing a comparison"
            
            if key:
                a = a[key]
                b = b[key]
            x = cmp(a, b)
            if reverse:
                x = -x
            return x
    
        def recycle(node):
            "We've consumed a node, set it aside for re-use"
            del node.children[:]
            node.n = 0
            node.leaf = True
            recyclable.append(node)
            assert node.refcount == 1
            assert node.__get_reference_count() == 0
    
        def get_node(leaf):
            "Get a node, either from the recycled list or through allocation"
            if recyclable:
                node = recyclable.pop(-1)
            else:
                node = _BList()
            node.leaf = leaf
            return node
    
        def get_leaf(forest):
            "Get a new leaf node to process from one of the input forests"
            node = forest.pop(-1)
            assert not node.__get_reference_count()
            while not node.leaf:
                forest.extend(reversed(node.children))
                recycle(node)
                node = forest.pop(-1)
            assert node.__get_reference_count() == 0
            return node

        try:
            if do_cmp(self[-1], other[0]) <= 0: # Speed up a common case
                self += other
                other._decref()
                return self

            # Input forests
            forest1 = [self]
            forest2 = [other]

            # Output forests
            forest_out = Forest()

            # Input leaf nodes we are currently processing
            leaf1 = get_leaf(forest1)
            leaf2 = get_leaf(forest2)

            # Index into leaf1 and leaf2, respectively
            i = 0 
            j = 0

            # Current output leaf node we are building
            output = get_node(leaf=True)
                
            while ((forest1 or i < len(leaf1.children))
                    and (forest2 or j < len(leaf2.children))):

                # Check if we need to get a new input leaf node
                if i == len(leaf1.children):
                    recycle(leaf1)
                    leaf1 = get_leaf(forest1)
                    i = 0
                if j == len(leaf2.children):
                    recycle(leaf2)
                    leaf2 = get_leaf(forest2)
                    j = 0

                # Check if we have filled up an output leaf node
                if output.n == limit:
                    forest_out.append_leaf(output)
                    output = get_node(leaf=True)

                # Figure out which input leaf has the lower element
                if do_cmp(leaf1.children[i], leaf2.children[j]) <= 0:
                    output.children.append(leaf1.children[i])
                    i += 1
                else:
                    output.children.append(leaf2.children[j])
                    j += 1

                output.n += 1

            # At this point, we have completely consumed at least one
            # of the lists

            # Append our partially-complete output leaf node to the forest
            forest_out.append_leaf(output)

            # Append a partially-consumed input leaf node, if one exists
            if i < len(leaf1.children):
                del leaf1.children[:i]
                forest_out.append_leaf(leaf1)
            else:
                recycle(leaf1)
            if j < len(leaf2.children):
                del leaf2.children[:j]
                forest_out.append_leaf(leaf2)
            else:
                recycle(leaf2)
    
            # Append the rest of whichever input forest still has
            # nodes.  This could be sped up by merging trees instead
            # of doing it leaf-by-leaf.
            while forest1:
                forest_out.append_leaf(get_leaf(forest1))
            while forest2:
                forest_out.append_leaf(get_leaf(forest2))

            out_tree = forest_out.finish()
    
        finally:
            # Fix reference counters, in case the user-compare function
            # threw an exception.
            for c in recyclable:
                c._decref()

        return out_tree

    @parent_callable
    @modifies_self
    def _sort(self, *args, **kw):
        if self.leaf:
            self.children.sort(*args, **kw)
            return
        for i in range(len(self.children)):
            self.__prepare_write(i)
            self.children[i]._sort(*args, **kw)
        while len(self.children) != 1:
            children = []
            for i in range(0, len(self.children)-1, 2):
                #print 'Merge:', self.children[i], self.children[i+1]
                a = self.children[i]
                b = self.children[i+1]
                self.children[i] = None     # Keep reference-checker happy
                self.children[i+1] = None
                self.children[i] = a._merge(b, *args, **kw)
                #print '->', self.children[i].debug()
                #assert list(self.children[i]) == sorted(self.children[i], *args, **kw)
                #self.children[i+1]._decref()
                children.append(self.children[i])
            self.children[:] = children
        self.__become(self.children[0])
        self._check_invariants_r()

    @user_callable
    @modifies_self
    def sort(self, *args, **kw):
        if self.leaf: # Special case to speed up common case
            self.children.sort(*args, **kw)
            return
        no_list = BList()
        real_self = BList(self)
        self.__become(no_list)
        try:
            real_self._sort(*args, **kw)
            self._check_invariants_r()
            if self.n:
                raise ValueError('list modified during sort')
        finally:
            self._check_invariants_r()
            real_self._check_invariants_r()
            self.__become(real_self)
            self._check_invariants_r()
                    
    @user_callable
    def __add__(self, other):
        if not isinstance(other, BList) and not isinstance(other, list):
            raise TypeError('can only concatenate list (not "%s") to list'
                            % str(type(other)))
        rv = BList(self)
        rv += other
        return rv

    @user_callable
    def __radd__(self, other):
        if not isinstance(other, BList) and not isinstance(other, list):
            raise TypeError('can only concatenate list (not "%s") to list'
                            % str(type(other)))
        rv = BList(other)
        rv += self
        return rv

    @user_callable
    @modifies_self
    def append(self, item):
        "User-visible function"
        self.insert(len(self), item)

    @user_callable
    @modifies_self
    @allow_negative1
    def insert(self, i, item):
        "User-visible function"
        if i > self.n:
            i = self.n
        overflow = self._insert(i, item)
        self.__overflow_root(overflow)

    @user_callable
    @modifies_self
    def __delslice__(self, i, j):
        "User-visible function"
        if i >= j:
            return
        self._delslice(i, j)

    @user_callable
    @modifies_self
    @allow_negative1
    def __delitem__(self, i):
        "User-visible function"

        if isinstance(i, slice):
            start, stop, step = i.indices(self.n)
            if step == 1:
                # More efficient
                self.__delslice__(start, stop)
                return
            j = start
            if step > 0:
                step -= 1 # We delete an item at each step
                while j < len(self) and j < stop:
                    del self[j]
                    j += step
            else:
                for j in range(start, stop, step):
                    del self[j]
            return

        if i >= self.n or i < 0:
            raise IndexError

        self.__delslice__(i, i+1)

    @user_callable
    def __getslice__(self, i, j):
        "User-visible function"

        # If the indices were negative, Python has already added len(self) to
        # them.  If they're still negative, treat them as 0.
        if i < 0: i = 0
        if j < 0: j = 0

        if j <= i:
            return BList()

        if i >= self.n:
            return BList()

        if self.leaf:
            return BList(self.children[i:j])

        rv = BList(self)
        del rv[j:]
        del rv[:i]

        return rv

    def __copy__(self):
        return BList(self)

########################################################################
# Forest class; an internal utility class for building BLists bottom-up

class Forest:
    def __init__(self):
        self.num_leafs = 0
        self.forest = []

    def append_leaf(self, leaf):
        "Append a leaf to the output forest, possible combining nodes"
        
        if not leaf.children:     # Don't add empty leaf nodes
            leaf._decref()
            return
        self.forest.append(leaf)
        leaf._adjust_n()
    
        # Every "limit" leaf nodes, combine the last "limit" nodes
        # This takes "limit" leaf nodes and replaces them with one node
        # that has the leaf nodes as children.
        
        # Every "limit**2" leaf nodes, take the last "limit" nodes
        # (which have height 2) and replace them with one node
        # (with height 3).
    
        # Every "limit**i" leaf nodes, take the last "limit" nodes
        # (which have height i) and replace them with one node
        # (with height i+1).
    
        i = 1
        self.num_leafs += 1
        while self.num_leafs % limit**i == 0:
            parent = _BList()
            parent.leaf = False
            assert len(self.forest) >= limit, \
                   (len(self.forest), limit, i, self.num_leafs)
            parent.children[:] = self.forest[-limit:]
            del self.forest[-limit:]
    
            # If the right-hand node has too few children,
            # borrow from a neighbor
            x = parent._BList__underflow(len(parent.children)-1)
            assert not x
    
            self.forest.append(parent)
            i += 1
            parent._check_invariants_r()

    def finish(self):
        "Combine the forest into a final BList"
    
        out_tree = None    # The final BList we are building
        out_height = 0     # It's height
        group_height = 1   # The height of the next group from the forest
        while self.forest:
            n = self.num_leafs % limit  # Numbers of same-height nodes
            self.num_leafs /= limit  
            group_height += 1
    
            if not n:
                # No nodes at this height
                continue

            # Merge nodes of the same height into 1 node, and
            # merge it into our output BList.
            group = _BList()
            group.leaf = False
            group.children[:] = self.forest[-n:]
            del self.forest[-n:]
            adj = group._BList__underflow(len(group.children)-1)
            if not out_tree:
                out_tree = group
                out_height = group_height - adj
            else:
                out_tree, out_height = BList._BList__concat_roots(group,
                                                            group_height - adj,
                                                            out_tree,
                                                            out_height)
        out_tree._check_invariants_r()
        return out_tree


########################################################################
# Iterator classes.  BList._iter() choses which one to use.

class ShortBListIterator:
    "A low-overhead iterator for short lists"

    def __init__(self, lst, start=0, stop=None):
        if stop is None:
            stop = len(lst)
        self.cur = start
        self.stop = stop
        self.lst = lst

    def next(self):
        if self.cur >= self.stop or self.cur >= self.lst.n:
            self.stop = 0  # Ensure the iterator cannot be restarted
            raise StopIteration

        rv = BList.__getitem__(self.lst, self.cur)
        self.cur += 1
        return rv

    def __iter__(self):
        return self

class BListIterator:
    """A high-overhead iterator that is more asymptotically efficient.

    Maintain a stack to traverse the tree.  The first step is to copy
    the list so we don't have to worry about user's modifying the list
    and wreaking havoc with our references.  Copying the list is O(1),
    but not worthwhile for lists that only contain a single leaf node.
    """

    def __init__(self, lst, start=0, stop=None):
        self.stack = []
        lst = BList(lst)  # Protect against users modifying the list
        if stop is None:
            stop = len(lst)
        if stop < 0: stop = 0
        if start < 0: start = 0
        self.remaining = stop - start
        while not lst.leaf:
            p, k, so_far = lst._locate(start)
            self.stack.append([lst, k+1])
            lst = lst.children[0]
            start -= so_far
        self.stack.append([lst, start])

    def next(self):
        if not self.remaining:
            raise StopIteration
        self.remaining -= 1

        p, i = self.stack[-1]
        if i < len(p.children):
            self.stack[-1][1] += 1
            return p.children[i]

        while 1:
            if not self.stack: raise StopIteration
            p, i = self.stack.pop()
            if i < len(p.children):
                break

        self.stack.append([p, i+1])

        while not p.leaf:
            p = p.children[i]
            i = 0
            self.stack.append([p, i+1])

        return p.children[i]

    def __iter__(self):
        return self

    def __copy__(self):
        rv = BListIterator.__new__()
        rv.stack = copy.copy(self.stack)
        rv.remaining = self.remaining
        return rv

########################################################################
# Test code

def main():
    n = 512

    data = range(n)
    import random
    random.shuffle(data)
    x = BList(data)
    x.sort()

    assert list(x) == sorted(data), x

    lst = BList()
    t = tuple(range(n))
    for i in range(n):
        lst.append(i)
        if tuple(lst) != t[:i+1]:
            print i, tuple(lst), t[:i+1]
            print lst.debug()
            break
    
    x = lst[4:258]
    assert tuple(x) == tuple(t[4:258])
    x.append(-1)
    assert tuple(x) == tuple(t[4:258] + (-1,))
    assert tuple(lst) == t
    
    lst[200] = 6
    assert tuple(x) == tuple(t[4:258] + (-1,))
    assert tuple(lst) == tuple(t[0:200] + (6,) + t[201:])
    
    del lst[200]
    #print lst.debug()
    assert tuple(lst) == tuple(t[0:200] + t[201:])
    
    lst2 = BList(range(limit+1))
    assert tuple(lst2) == tuple(range(limit+1))
    del lst2[1]
    del lst2[-1]
    assert tuple(lst2) == (0,) + tuple(range(2,limit))
    assert lst2.leaf
    assert len(lst2.children) == limit-1

    lst = BList(range(n))
    lst.insert(200, 0)
    assert tuple(lst) == (t[0:200] + (0,) + t[200:])
    del lst[200:]
    assert tuple(lst) == tuple(range(200))

    lst = BList(range(3))
    lst*3
    assert lst*3 == range(3)*3

    a = BList('spam')
    a.extend('eggs')
    assert a == list('spameggs')

    x = BList([0])
    for i in range(290) + [1000, 10000, 100000, 1000000, 10000000]:
        if len(x*i) != i:
            print 'mul failure', i
            print (x*i).debug()
            break

    little_list = BList([0])
    big_list = little_list * 2**512

blist = BList
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = replot
#!/usr/bin/python

from speed_test import *

if len(sys.argv) == 1:
    for k in timing_d:
        plot(k, True)
        plot(k, False)
        html(k)
else:
    name = sys.argv[1]
    plot(name, True)
    plot(name, False)
    html(name)

########NEW FILE########
__FILENAME__ = speed_test
#!/usr/bin/python
from __future__ import print_function

import os, sys, subprocess
from math import *

# The tests to run are near the bottom

MIN_REPS = 3
NUM_POINTS = 9
MIN_TIME = 0.1
MAX_TIME = 1.0
MAX_X = 100000

def makedir(x):
    try:
        os.mkdir(x)
    except OSError:
        pass

def rm(x):
    try:
        os.unlink(x)
    except OSError:
        pass

makedir('fig')
makedir('fig/relative')
makedir('fig/absolute')
makedir('.cache')
makedir('dat')
makedir('gnuplot')

limits = (128,)
current_limit = None
def make(limit):
    global current_limit
    current_limit = limit

setup = 'from blist import blist'

ns = []
for i in range(50+1):
    ns.append(int(floor(10**(i*0.1))))
ns = list(i for i in sorted(set(ns)) if i <= MAX_X)

def smart_timeit(stmt, setup, hint):
    n = hint
    while 1:
        v = timeit(stmt, setup, n)
        if v[0]*n > MIN_TIME:
            return v, n
        n <<= 1

import timeit
timeit_path = timeit.__file__

timeit_cache = {}
def timeit(stmt, setup, rep):
    assert rep >= MIN_REPS
    key = (stmt, setup, rep, current_limit)
    if key in timeit_cache:
        return timeit_cache[key]
    try:
        n = NUM_POINTS
        args =[sys.executable, timeit_path,
               '-r', str(n), '-v', '-n', str(rep), '-s', setup, '--', stmt]
        p = subprocess.Popen(args,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        so, se = p.communicate()
        try:
            lines = so.split(b'\n')
            raw = lines[0]
            number = int(lines[1].split()[0])
            times = [float(x) / number for x in raw.split()[2:]]
            times.sort()
            # median, lower quartile, upper quartile
            v = (times[n//2], times[n//4], times[3*n//4])
            timeit_cache[key] = v
            return v
        except:
            print(so)
            print(se)
            raise
    except:
        print(stmt)
        print(setup)
        raise

values = {}
def get_timing1(limit, label, setup_n, template, typename, use_rep_map):
    f = open('dat/%s-%s.dat' % (str(limit), label), 'w')
    print('#', label, file=f)
    print('#', template.replace('\n', '\\n'), file=f)
    if setup_n is None:
        setup_n = "x = TypeToTest(range(n))"
    else:
        setup_n = setup_n
    ftimeit = open('fig/%s.txt' % label, 'w')
    print('<div class="blist_inner">Setup: <code>%s</code><br/>' % setup_n.replace('\n', '<br/>'), 
          file=ftimeit)
    print('Timed: <code>%s</code></div>' % template.replace('\n', '<br/>'), 
          file=ftimeit)
    ftimeit.close()
 
    for i in reversed(list(range(len(ns)))):
        n = ns[i]
        key = (limit, label, setup_n, n, template, typename)
        print(n, end=' ')
        sys.stdout.flush()
        setup2 = '\nTypeToTest = %s\nn = %d\n' % (typename, n)
        setup3 = setup + '\n' + setup2 + setup_n
        stmt = template
        if not use_rep_map:
            if i < len(ns)-1:
                rep_map[n] = max(rep_map[n], rep_map[ns[i+1]])
            v, rep = smart_timeit(stmt, setup3, rep_map[n])
            if rep_map[n] < rep:
                rep_map[n] = rep
        else:
            k = rep_map[n]
            if k * values[key] > MAX_TIME:
                k = max(MIN_REPS, int(ceil(MAX_TIME / values[key])))
            v = timeit(stmt, setup3, k)
        values[key] = v[0]
        v = [x*1000 for x in v]
        if typename == 'list':
            list_values[n] = v[0]
        print(n, file=f, end=' ')
        for x in v:
            print(x, file=f, end=' ')
        for x in v:
            print(x/list_values[n], file=f, end=' ')
        print(file=f)
    print()
    f.close()

def get_timing(label, setup_n, template):
    global rep_map, list_values
    rep_map = {}
    list_values = {}
    for n in ns:
        rep_map[n] = MIN_REPS
    make('list')
    get_timing1('list', label, setup_n, template, 'list', False)
    for limit in limits:
        print('Timing', label, limit, ':', end=' ')
        sys.stdout.flush()
        make(limit)
        get_timing1(limit, label, setup_n, template, 'blist', False)

    make('list')
    get_timing1('list', label, setup_n, template, 'list', True)
    for limit in limits:
        print('Timing', label, limit, ':', end=' ')
        sys.stdout.flush()
        make(limit)
        get_timing1(limit, label, setup_n, template, 'blist', True)

    plot(label, True)
    plot(label, False)
    html(label)

def html(label):
    fname = 'fig/%s.html' % label
    f = open(fname, 'w')
    if timing_d[label][0] is None:
        setup = 'x = TypeToTest(range(n))'
    else:
        setup = timing_d[label][0]
    print('''
<html>
<head>
<title>BList vs Python list timing results: %s</title>
<script src="svg.js"></script>
</head>
<body>
<div style="width: 100%%; background-color: #ccc;">
<a href="/">Home</a>
| <a href="/blist/">BList</a>
| <a href="http://pokersleuth.com/">Poker Sleuth</a>
| <a href="http://pokersleuth.com/poker-crunch.shtml">Poker Calculator</a>
| <a href="http://pokersleuth.com/hand-converter.shtml">Hand Converter</a>

</div>
    
<object data="absolute/%s.svg" width="480" height="360"
	type="image/svg+xml"></object>
<object data="relative/%s.svg" width="480" height="360"
	type="image/svg+xml"></object>
<p>
Setup:
<pre>
%s
</pre>
Timed:
<pre>
%s
</pre>
</body>
</html>
    ''' % (label, label, label, setup, timing_d[label][1]), file=f)
    f.close()

def plot(label, relative):
    safe_label = label.replace('_', '\\\\_')
    fname = 'gnuplot/%s.gnuplot' % label
    f = open(fname, 'w')
    if relative:
        d = 'fig/relative/'
    else:
        d = 'fig/absolute/'
    print("""
set output "%s/%s.svg"
set xlabel "List Size (n)"
set title "%s"
set terminal svg size 480,360 dynamic enhanced
set size noratio 1,1
set key top left
set bars 0.2
set pointsize 0.5
set xtics ("1" 1, "10" 10, "100" 100, "1k" 1000, "10k" 10000, "100k" 100000, "1M" 1000000)
""" % (d, label, safe_label), file=f)

    if relative:
        print('set title "Normalized Execution Times, log-linear scale"', file=f)
        print('set logscale x', file=f)
        print('set yrange [0:*]', file=f)
        print('set yrange [0:200]', file=f)
        print('set ylabel "Execution Time (%)"', file=f)
        k = 3
        m = 100.0
    else:
        print('set title "Raw Execution Times, log-log scale"', file=f)
        print('set logscale xy', file=f)
        print('set yrange [0.00001:10]', file=f)
        print('set ylabel "Execution Time"', file=f)
        print('set ytics ("1 ns" 0.000001, "10 ns" 0.00001, "100 ns" 0.0001, "1 us" 0.001, "10 us" 0.01, "100 us" 0.1, "1 ms" 1.0, "10 ms" 10.0, "100 ms" 100.0)', file=f)
        k = 0
        m = 1.0

    print (('plot "dat/list-%s.dat" using 1:(%f*$%d):(%f*$%d):(%f*$%d) title "list()" with yerr pt 1, \\' % (label, m, k+2, m, k+3, m, k+4)), file=f)
    for limit in limits:
        print (('    "dat/%d-%s.dat" using 1:(%f*$%d):(%f*$%d):(%f*$%d) title "blist()" with yerr pt 1 '% (limit, label, m, k+2, m, k+3, m, k+4)), file=f)
    print(file=f)
    f.flush()
    f.close()
    if os.system('gnuplot "%s"' % fname):
        raise RuntimeError('Gnuplot failure')

timing_d = {}
def add_timing(name, auto, stmt):
    timing_d[name] = (auto, stmt)

def run_timing(name):
    auto, stmt = timing_d[name]
    get_timing(name, auto, stmt)

def run_all():
    for k in sorted(timing_d):
        run_timing(k)

########################################################################
# Tests to run are below here.
# The arguments to add_timing are as follows:
#   1) name of the test
#   2) setup code to run once.  "None" means x = TypeToTest(range(n))
#   3) code to execute repeatedly in a loop
#
# The following symbols will autoamtically be defined:
#   - blist
#   - TypeToTest
#   - n

add_timing('eq list', 'x = TypeToTest(range(n))\ny=range(n)', 'x==y')
#add_timing('eq recursive', 'x = TypeToTest()\nx.append(x)\ny = TypeToTest()\ny.append(y)', 'try:\n  x==y\nexcept RuntimeError:\n  pass')

add_timing('FIFO', None, """\
x.insert(0, 0)
x.pop(0)
""")

add_timing('LIFO', None, """\
x.append(0)
x.pop(-1)
""")

add_timing('add', None, "x + x")
add_timing('contains', None, "-1 in x")
#add_timing('getitem1', None, "x[0]")
#add_timing('getitem2', None, "x.__getitem__(0)")
add_timing('getitem3', 'x = TypeToTest(range(n))\nm = n//2', "x[m]")
add_timing('getslice', None, "x[1:-1]")
add_timing('forloop', None, "for i in x:\n    pass")
add_timing('len', None, "len(x)")
add_timing('eq', None, "x == x")
add_timing('mul10', None, "x * 10")
#add_timing('setitem1', None, 'x[0] = 1')
add_timing('setitem3', 'x = TypeToTest(range(n))\nm = n//2', 'x[m] = 1')
add_timing('count', None, 'x.count(5)')
add_timing('reverse', None, 'x.reverse()')
add_timing('delslice', None, 'del x[len(x)//4:3*len(x)//4]\nx *= 2')
add_timing('setslice', None, 'x[:] = x')

add_timing('sort random', 'import random\nx = [random.randrange(n*4) for i in range(n)]', 'y = TypeToTest(x)\ny.sort()')
add_timing('sort random key', 'import random\nx = [random.randrange(n*4) for i in range(n)]', 'y = TypeToTest(x)\ny.sort(key=float)')
add_timing('sort sorted', None, 'x.sort()')
add_timing('sort sorted key', None, 'x.sort(key=int)')
add_timing('sort reversed', 'x = list(range(n))\nx.reverse()', 'y = TypeToTest(x)\ny.sort()')
add_timing('sort reversed key', 'x = list(range(n))\nx.reverse()', 'y = TypeToTest(x)\ny.sort(key=int)')

add_timing('sort random tuples', 'import random\nx = [(random.random(), random.random()) for i in range(n)]', 'y = TypeToTest(x)\ny.sort()')

ob_def = '''
import random
class ob:
    def __init__(self, v):
        self.v = v
    def __lt__(self, other):
        return self.v < other.v
x = [ob(random.randrange(n*4)) for i in range(n)]
'''

add_timing('sort random objects', ob_def, 'y = TypeToTest(x)\ny.sort()')
add_timing('sort sorted objects', ob_def + 'x.sort()', 'x.sort()')

add_timing('init from list', 'x = list(range(n))', 'y = TypeToTest(x)')
add_timing('init from tuple', 'x = tuple(range(n))', 'y = TypeToTest(x)')
add_timing('init from iterable', 'x = range(n)', 'y = TypeToTest(x)')
add_timing('init from same type', None, 'y = TypeToTest(x)')

add_timing('shuffle', 'from random import shuffle\nx = TypeToTest(range(n))', 'shuffle(x)')

if __name__ == '__main__':
    make(128)
    if len(sys.argv) == 1:
        run_all()
    else:
        for name in sys.argv[1:]:
            run_timing(name)

########NEW FILE########
__FILENAME__ = speed_test_native
#!/usr/bin/python2.5

import os, sys, subprocess
from math import *

# The tests to run are near the bottom

MIN_REPS = 3
MIN_TIME = 0.01
MAX_TIME = 1.0

if 'cygwin' in os.uname()[0].lower():
    extension = 'dll'
else:
    extension = 'so'

def makedir(x):
    try:
        os.mkdir(x)
    except OSError:
        pass

def rm(x):
    try:
        os.unlink(x)
    except OSError:
        pass

makedir('fig')
makedir('fig/relative')
makedir('fig/absolute')
makedir('.cache')
makedir('dat')
makedir('gnuplot')

setup = ''

types = ('blist', 'list')

typemap = {
    'blist': '/home/agthorr/mypython-2.5/python',
    'list': '/home/agthorr/Python-2.5/python',
}

ns = (range(1,10) + range(10, 100, 10) + range(100, 1000, 100)
      + range(1000, 10001, 1000))

def smart_timeit(python, stmt, setup, hint):
    n = hint
    while 1:
        v = timeit(python, stmt, setup, n)
        if v[0]*n > MIN_TIME:
            return v, n
        n <<= 1

timeit_cache = {}
def timeit(python, stmt, setup, rep):
    assert rep >= MIN_REPS
    key = (python, stmt, setup, rep)
    if key in timeit_cache:
        return timeit_cache[key]
    try:
        n = 9
        p = subprocess.Popen([python, '/usr/lib/python2.5/timeit.py',
                              '-r', str(n), '-v', '-n', str(rep), '-s', setup, '--', stmt],
                             stdout=subprocess.PIPE)
        so, se = p.communicate()
        try:
            lines = so.split('\n')

            raw = lines[0]
            number = int(lines[1].split()[0])
            times = [float(x) / number for x in raw.split()[2:]]
            times.sort()

            v = (times[n//2+1], times[n//4+1], times[(3*n)//4+1])

            #so = lines[1]
            #parts = so.split()
            #v = float(parts[-4])
            #units = parts[-3]
            #if units == 'usec':
            #    v *= 10.0**-6
            #elif units == 'msec':
            #    v *= 10.0**-3
            #elif units == 'sec':
            #    pass
            #else:
            #    raise 'Unknown units'
            timeit_cache[key] = v
            return v
        except:
            print so
            print se
            raise
    except:
        print stmt
        print setup
        raise

values = {}
def get_timing1(label, setup_n, template, typename, use_rep_map):
    f = open('dat/%s-%s.dat' % (str(typename), label), 'w')
    print >>f, '#', label
    print >>f, '#', template.replace('\n', '\\n')
    for i in reversed(range(len(ns))):
        n = ns[i]
        key = (label, setup_n, n, template, typename)
        print n,
        sys.stdout.flush()
        setup2 = '\nn = %d\n' % (n,)
        if setup_n is None:
            setup3 = "x = list(range(n))"
        else:
            setup3 = setup_n
        setup3 = setup + '\n' + setup2 + setup3
        stmt = template
        if not use_rep_map:
            if i < len(ns)-1:
                rep_map[n] = max(rep_map[n], rep_map[ns[i+1]])
            v, rep = smart_timeit(typemap[typename], stmt, setup3, rep_map[n])
            if rep_map[n] < rep:
                rep_map[n] = rep
        else:
            k = rep_map[n]
            if k * values[key] > MAX_TIME:
                k = max(MIN_REPS, int(ceil(MAX_TIME / values[key])))
            v = timeit(typemap[typename], stmt, setup3, k)
        values[key] = v[0]
        v = [x*1000 for x in v]
        if typename == 'list':
            list_values[n] = v[0]
        print >>f, n,
        for x in v:
            print >>f, x,
        for x in v:
            print >>f, x/list_values[n],
        print >>f
    print
    f.close()

def get_timing(label, setup_n, template):
    global rep_map, list_values
    rep_map = {}
    list_values = {}
    for n in ns:
        rep_map[n] = MIN_REPS
    get_timing1(label, setup_n, template, 'list', False)
    print 'Timing', label, ':',
    sys.stdout.flush()
    get_timing1(label, setup_n, template, 'blist', False)

    get_timing1(label, setup_n, template, 'list', True)
    print 'Timing', label, ':',
    sys.stdout.flush()
    get_timing1(label, setup_n, template, 'blist', True)

    plot(label, True)
    plot(label, False)
    html(label)

def html(label):
    fname = 'fig/%s.html' % label
    f = open(fname, 'w')
    if timing_d[label][0] is None:
        setup = 'x = list(range(n))'
    else:
        setup = timing_d[label][0]
    print >>f, '''
<html>
<head>
<title>BList vs Python list timing results: %s</title>
</head>
<body>
<div style="width: 100%%; background-color: #ccc;">
<a href="/">Home</a>
| <a href="/blist/">BList</a>
| <a href="http://pokersleuth.com/">Poker Sleuth</a>
| <a href="http://pokersleuth.com/poker-crunch.shtml">Poker Calculator</a>
| <a href="http://pokersleuth.com/hand-converter.shtml">Hand Converter</a>

</div>
    
<img src="absolute/%s.png"/>
<img src="relative/%s.png"/>
<p>
Setup:
<pre>
%s
</pre>
Timed:
<pre>
%s
</pre>
</body>
</html>
    ''' % (label, label, label, setup, timing_d[label][1])
    f.close()

def plot(label, relative):
    safe_label = label.replace('_', '\\\\_')
    fname = 'gnuplot/%s.gnuplot' % label
    f = open(fname, 'w')
    if relative:
        d = 'fig/relative/'
    else:
        d = 'fig/absolute/'
    os.putenv('GDFONTPATH', '/usr/share/fonts/truetype/msttcorefonts/')
    print >>f, """
set output "%s/%s.png"
set xlabel "List Size (n)"
set title "%s"
#set bmargin 3

#set pointsize 2
#set view 60, 30, 1.0, 1.0
#set lmargin 12
#set rmargin 10
#set tmargin 1
#set bmargin 5
#set ylabel 0
#set mxtics default
#set mytics default
#set tics out
#set nox2tics
#set noy2tics
#set border 3
#set xtics nomirror autofreq
#set ytics nomirror autofreq
#set key height 1
#set nokey
#unset xdata
#unset y2label
#unset x2label

#set format "%%g"
set terminal png transparent interlace medium font "./times.ttf" size 640,480 nocrop enhanced xffffff x000000 xff0000 x0000ff xc030c0 xff0000 x000000
set size noratio 1,1

#set key below height 1
""" % (d, label, safe_label)

    if relative:
        print >>f, 'set title "Normalized Execution Times, log-linear scale"'
        print >>f, 'set logscale x'
        print >>f, 'set yrange [0:*]'
        print >>f, 'set yrange [0:200]'
        print >>f, 'set ylabel "Execution Time (%)"'
        print >>f, 'set key bottom left'
        print >>f, 'set mytics 5'
    else:
        print >>f, 'set title "Raw Execution Times, log-log scale"'
        print >>f, 'set key top left'
        #print >>f, 'set mytics 10'
        print >>f, 'set logscale xy'
        print >>f, 'set yrange [0.0001:10]'
        print >>f, 'set ylabel "Execution Time"'
        print >>f, 'set ytics ("1 ns" 0.000001, "10 ns" 0.00001, "100 ns" 0.0001, "1 us" 0.001, "10 us" 0.01, "100 us" 0.1, "1 ms" 1.0, "10 ms" 10.0, "100 ms" 100.0)'

    if relative:
        k = 3
        m = 100.0
    else:
        k = 0
        m = 1.0

    print >>f, ('plot "dat/list-%s.dat" using 1:(%f*$%d):(%f*$%d):(%f*$%d) title "list()" with yerrorlines, \\'
                % (label, m, k+2, m, k+3, m, k+4))
    print >>f, ('    "dat/blist-%s.dat" using 1:(%f*$%d):(%f*$%d):(%f*$%d) title "blist()" with yerrorlines '
                % (label, m, k+2, m, k+3, m, k+4))
        
    print >>f
    f.flush()
    f.close()
    if os.system('gnuplot "%s"' % fname):
        raise 'Gnuplot failure'

timing_d = {}
def add_timing(name, auto, stmt):
    timing_d[name] = (auto, stmt)

def run_timing(name):
    auto, stmt = timing_d[name]
    get_timing(name, auto, stmt)

def run_all():
    for k in sorted(timing_d):
        run_timing(k)

########################################################################
# Tests to run are below here.
# The arguments to add_timing are as follows:
#   1) name of the test
#   2) setup code to run once.  "None" means x = list(range(n))
#   3) code to execute repeatedly in a loop
#
# The following symbols will automatically be defined:
#   - n

add_timing('FIFO', None, """\
x.insert(0, 0)
del x[0]
""")

add_timing('LIFO', None, """\
x.append(0)
del x[-1]
""")

add_timing('add', None, "x + x")
add_timing('contains', None, "-1 in x")
add_timing('getitem1', None, "x[0]")
add_timing('getitem2', None, "x.__getitem__(0)")
add_timing('getitem3', 'x = range(n)\nm = n//2', "x[m]")
add_timing('getslice', None, "x[1:-1]")
add_timing('forloop', None, "for i in x:\n    pass")
add_timing('len', None, "len(x)")
add_timing('eq', None, "x == x")
add_timing('mul10', None, "x * 10")
add_timing('setitem1', None, 'x[0] = 1')
add_timing('setitem3', 'x = range(n)\nm = n//2', 'x[m] = 1')
add_timing('count', None, 'x.count(5)')
add_timing('reverse', None, 'x.reverse()')
add_timing('delslice', None, 'del x[len(x)//4:3*len(x)//4]\nx *= 2')
add_timing('setslice', None, 'x[:] = x')

add_timing('sort random', 'import random\nx = [random.random() for i in range(n)]', 'y = list(x)\ny.sort()')
add_timing('sort sorted', None, 'y = list(x)\ny.sort()')
add_timing('sort reversed', 'x = range(n)\nx.reverse()', 'y = list(x)\ny.sort()')

add_timing('init from list', 'x = range(n)', 'y = list(x)')
add_timing('init from tuple', 'x = tuple(range(n))', 'y = list(x)')
add_timing('init from iterable', 'x = xrange(n)', 'y = list(x)')
add_timing('init from same type', None, 'y = list(x)')

add_timing('shuffle', 'from random import shuffle\nx = list(range(n))', 'shuffle(x)')

if __name__ == '__main__':
    if len(sys.argv) == 1:
        run_all()
    else:
        for name in sys.argv[1:]:
            run_timing(name)

########NEW FILE########
__FILENAME__ = summarize
#!/usr/bin/env python

import os, sys

names = set()
for fname in os.listdir('dat/'):
    if fname.endswith('.dat'):
        names.add(fname.split('.')[0].split('-')[1])

if len(sys.argv) > 1:
    names = set(sys.argv[1:])

final = {}
for name in names:
    data = {}
    with open('dat/128-%s.dat' % name) as f:
        lines = f.readlines()
    for line in lines:
        if line[0] == '#':
            continue
        line = line.split()
        if len(line) < 5:
            continue
        data[int(line[0])] = float(line[4])
    if not data:
        continue
    final[name] = sum(data.values())/len(data)

items = [(t[1], t[0]) for t in final.items()]
items.sort()
hit1 = len(sys.argv) > 1
for v, name in items:
    if v >= 1.0 and not hit1:
        hit1 = True
        print '-'*72
    print '%.0f%% %s' % (v*100, name)

     

########NEW FILE########
__FILENAME__ = test_blist
#!/usr/bin/python
from __future__ import print_function

"""
Copyright 2007-2010 Stutzbach Enterprises, LLC (daniel@stutzbachenterprises.com)

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   1. Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above
      copyright notice, this list of conditions and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution.
   3. The name of the author may not be used to endorse or promote
      products derived from this software without specific prior written
      permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

"""


import sys
import os

import unittest, operator
import blist, pickle
from blist import _blist
#BList = list
from blist.test import test_support, list_tests, sortedlist_tests, btuple_tests
from blist.test import sorteddict_tests, test_set

limit = _blist._limit
n = 512//8 * limit

class BListTest(list_tests.CommonTest):
    type2test = blist.blist

    def test_delmul(self):
        x = self.type2test(list(range(10000)))
        for i in range(100):
            del x[len(x)//4:3*len(x)//4]
            x *= 2

    def test_truth(self):
        super(BListTest, self).test_truth()
        self.assert_(not self.type2test())
        self.assert_(self.type2test([42]))

    def test_identity(self):
        self.assert_(self.type2test([]) is not self.type2test([]))

    def test_len(self):
        super(BListTest, self).test_len()
        self.assertEqual(len(self.type2test()), 0)
        self.assertEqual(len(self.type2test([0])), 1)
        self.assertEqual(len(self.type2test([0, 1, 2])), 3)

    def test_append2(self):
        lst = self.type2test()
        t = tuple(range(n))
        for i in range(n):
            lst.append(i)
            self.assertEqual(tuple(lst), t[:i+1])

    def test_delstuff(self):
        lst = self.type2test(list(range(n)))
        t = tuple(range(n))
        x = lst[4:258]
        self.assertEqual(tuple(x), tuple(t[4:258]))
        x.append(-1)
        self.assertEqual(tuple(x), tuple(t[4:258] + (-1,)))
        self.assertEqual(tuple(lst), t)
        lst[200] = 6
        self.assertEqual(tuple(x), tuple(t[4:258] + (-1,)))
        self.assertEqual(tuple(lst), tuple(t[0:200] + (6,) + t[201:]))
        del lst[200]
        self.assertEqual(tuple(lst), tuple(t[0:200] + t[201:]))

    def test_del1(self):
        lst2 = self.type2test(list(range(limit+1)))
        self.assertEqual(tuple(lst2), tuple(range(limit+1)))
        del lst2[1]
        del lst2[-1]
        self.assertEqual(tuple(lst2), (0,) + tuple(range(2,limit)))

    def test_insert_and_del(self):
        lst = self.type2test(list(range(n)))
        t = tuple(range(n))
        lst.insert(200, 0)
        self.assertEqual(tuple(lst), (t[0:200] + (0,) + t[200:]))
        del lst[200:]
        self.assertEqual(tuple(lst), tuple(range(200)))

    def test_mul3(self):
        lst = self.type2test(list(range(3)))
        self.assertEqual(tuple(lst*3), tuple(list(range(3))*3))

    def test_mul(self):
        x = self.type2test(list(range(limit**2)))
        for i in range(10):
            self.assertEqual(len(x*i), i*limit**2)

    def test_extendspam(self):
        a = self.type2test('spam')
        a.extend('eggs')
        self.assertEqual(list(a), list('spameggs'))

    def test_bigmul1(self):
        x = self.type2test([0])
        for i in list(range(290)) + [1000, 10000, 100000, 1000000, 10000000, 2**29]:
            self.assertEqual(len(x*i), i)

    def test_badinit(self):
        self.assertRaises(TypeError, self.type2test, 0, 0, 0)

    def test_copyself(self):
        x = self.type2test(list(range(n)))
        x[:] = x

    def test_nohash(self):
        x = self.type2test()
        d = {}
        self.assertRaises(TypeError, d.__setitem__, x, 5)

    def test_collapseboth(self):
        x = self.type2test(list(range(512)))
        del x[193:318]

    def test_collapseright(self):
        x = self.type2test(list(range(512)))
        del x[248:318]

    def test_badrepr(self):
        class BadExc(Exception):
            pass

        class BadRepr:
            def __repr__(self):
                raise BadExc

        x = self.type2test([BadRepr()])
        self.assertRaises(BadExc, repr, x)
        x = self.type2test(list(range(n)))
        x.append(BadRepr())
        self.assertRaises(BadExc, repr, x)

    def test_slice0(self):
        x = self.type2test(list(range(n)))
        x[slice(5,3,1)] = []
        self.assertEqual(x, list(range(n)))
        x = self.type2test(list(range(n)))
        self.assertRaises(ValueError, x.__setitem__, slice(5,3,1), [5,3,2])
        del x[slice(5,3,1)]
        self.assertEqual(x, list(range(n)))

    def test_badindex(self):
        x = self.type2test()
        self.assertRaises(TypeError, x.__setitem__, 's', 5)

    def test_comparelist(self):
        x = self.type2test(list(range(n)))
        y = list(range(n-1))
        self.assert_(not (x == y))
        self.assert_(x != y)
        self.assert_(not (x < y))
        self.assert_(not (x <= y))
        self.assert_(x > y)
        self.assert_(x >= y)

        y = list(range(n))
        self.assert_(x == y)
        self.assert_(y == x)

        y[100] = 6
        self.assert_(not (x == y))
        self.assert_(x != y)

    def test_compareblist(self):
        x = self.type2test(list(range(n)))
        y = self.type2test(list(range(n-1)))
        self.assert_(not (x == y))
        self.assert_(x != y)
        self.assert_(not (x < y))
        self.assert_(not (x <= y))
        self.assert_(x > y)
        self.assert_(x >= y)

        y[100] = 6
        self.assert_(not (x == y))
        self.assert_(x != y)

    def test_comparetuple(self):
        x = self.type2test(list(range(n)))
        y = tuple(range(n))
        self.assert_(x != y)

    def test_indexempty(self):
        x = self.type2test(list(range(10)))
        self.assertRaises(ValueError, x.index, 'spam')

    def test_indexargs(self):
        x = self.type2test(list(range(10)))
        self.assertEqual(x.index(5,1,-1), 5)
        self.assertRaises(ValueError, x.index, 5, -1, -9)
        self.assertRaises(ValueError, x.index, 8, 1, 4)
        self.assertRaises(ValueError, x.index, 0, 1, 4)

    def test_reversebig(self):
        x = self.type2test(list(range(n)))
        x.reverse()
        self.assertEqual(x, list(range(n-1,-1,-1)))

    def test_badconcat(self):
        x = self.type2test()
        y = 'foo'
        self.assertRaises(TypeError, operator.add, x, y)

    def test_bad_assign(self):
        x = self.type2test(list(range(n)))
        self.assertRaises(TypeError, x.__setitem__, slice(1,10,2), 5)

    def sort_evil(self, after):
        class EvilCompare:
            count = 0
            num_raises = 0
            def __init__(self, x):
                self.x = x
            def __lt__(self, other):
                EvilCompare.count += 1
                if EvilCompare.count > after:
                    EvilCompare.num_raises += 1
                    raise ValueError
                return self.x < other.x

        x = self.type2test(EvilCompare(x) for x in range(n))
        from random import shuffle
        shuffle(x)
        self.assertRaises(ValueError, x.sort)
        self.assertEqual(EvilCompare.num_raises, 1)
        x = [a.x for a in x]
        x.sort()
        self.assertEquals(x, list(range(n)))

    def test_sort_evil_small(self):
        self.sort_evil(limit * 5)

    def test_sort_evil_big(self):
        self.sort_evil(n + limit)

    def test_big_extend(self):
        x = self.type2test([1])
        x.extend(range(n))
        self.assertEqual(tuple(x), (1,) + tuple(range(n)))

    def test_big_getslice(self):
        x = self.type2test([0]) * 65536
        self.assertEqual(len(x[256:512]), 256)

    def test_modify_original(self):
        x = self.type2test(list(range(1024)))
        y = x[:]
        x[5] = 'z'
        self.assertEqual(tuple(y), tuple(range(1024)))
        self.assertEqual(x[5], 'z')
        self.assertEqual(tuple(x[:5]), tuple(range(5)))
        self.assertEqual(tuple(x[6:]), tuple(range(6, 1024)))

    def test_modify_copy(self):
        x = self.type2test(list(range(1024)))
        y = x[:]
        y[5] = 'z'
        self.assertEqual(tuple(x), tuple(range(1024)))
        self.assertEqual(y[5], 'z')
        self.assertEqual(tuple(y[:5]), tuple(range(5)))
        self.assertEqual(tuple(y[6:]), tuple(range(6, 1024)))

    def test_bigsort(self):
        x = self.type2test(list(range(100000)))
        x.sort()

    def test_sort_twice(self):
        y = blist.blist(list(range(limit+1)))
        for i in range(2):
            x = blist.blist(y)
            x.sort()
            self.assertEqual(tuple(x), tuple(range(limit+1)))

    def test_LIFO(self):
        x = blist.blist()
        for i in range(1000):
            x.append(i)
        for j in range(1000-1,-1,-1):
            self.assertEqual(x.pop(), j)

    def pickle_test(self, pickler, x):
        y = pickler.dumps(x)
        z = pickler.loads(y)
        self.assertEqual(x, z)
        self.assertEqual(repr(x), repr(z))

    def pickle_tests(self, pickler):
        self.pickle_test(pickler, blist.blist())
        self.pickle_test(pickler, blist.blist(list(range(limit))))
        self.pickle_test(pickler, blist.blist(list(range(limit+1))))
        self.pickle_test(pickler, blist.blist(list(range(n))))

        x = blist.blist([0])
        x *= n
        self.pickle_test(pickler, x)
        y = blist.blist(x)
        y[5] = 'x'
        self.pickle_test(pickler, x)
        self.pickle_test(pickler, y)

    def test_pickle(self):
        self.pickle_tests(pickle)

    def test_types(self):
        type(blist.blist())
        type(iter(blist.blist()))
        type(iter(reversed(blist.blist())))

    def test_iterlen_empty(self):
        it = iter(blist.blist())
        if hasattr(it, '__next__'): # pragma: no cover
            self.assertRaises(StopIteration, it.__next__)
        else: # pragma: no cover
            self.assertRaises(StopIteration, it.next)
        self.assertEqual(it.__length_hint__(), 0)

    def test_sort_floats(self):
        x = blist.blist([0.1, 0.2, 0.3])
        x.sort()

tests = [BListTest,
         sortedlist_tests.SortedListTest,
         sortedlist_tests.WeakSortedListTest,
         sortedlist_tests.SortedSetTest,
         sortedlist_tests.WeakSortedSetTest,
         btuple_tests.bTupleTest,
         sorteddict_tests.sorteddict_test
         ]
tests += test_set.test_classes

def test_suite():
    suite = unittest.TestSuite()
    for test in tests:
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(test))
    return suite

def test_main(verbose=None):
    test_support.run_unittest(*tests)

if __name__ == "__main__":
    test_main(verbose=True)

########NEW FILE########
