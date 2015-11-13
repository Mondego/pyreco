__FILENAME__ = cardunion_test
import unittest
from math import sqrt
from cardunion import Cardunion


class TestCardunion(unittest.TestCase):
    def setUp(self):
        self.log2m = 12
        self.error = 1.04 / sqrt(2 ** self.log2m)

    def test_mid_range_with_strings(self):
        self.execute(10000, self.log2m, self.error)

    def test_long_range_with_strings(self):
        self.execute(100000, self.log2m, self.error)

    def test_low_range_with_strings(self):
        self.execute(100, self.log2m, self.error)

    def execute(self, set_size, m, p):
        hll = Cardunion(m)
        for i in range(set_size):
            hll.add(str(i))

        estimate = hll.count()
        error = abs(estimate / float(set_size) - 1)
        self.assertLess(error, p)

    def test_with_duplicates(self):
        hll = Cardunion(self.log2m)
        set_size = 100000
        for i in range(set_size):
            if i % 3:
                hll.add(str(i + 1))
            else:
                hll.add(str(i))

        estimate = hll.count()
        expected = set_size * 2.0 / 3.0
        error = abs(estimate / float(expected) - 1)
        self.assertLess(error, self.error)

    def test_with_heavy_duplicates(self):
        hll = Cardunion(self.log2m)
        set_size = 100000
        for i in range(set_size):
            if i % 2 or i < set_size / 2:
                hll.add(str(1))
            else:
                hll.add(str(i))

        estimate = hll.count()
        expected = set_size * 1.0 / 4.0
        error = abs(estimate / float(expected) - 1)
        self.assertLess(error, self.error)

    def test_dumps(self):
        hll = Cardunion(self.log2m)
        hll_copy = Cardunion(self.log2m)
        for i in range(10000):
            hll.add(str(i))

        hll_copy.loads(hll.dumps())
        self.assertEqual(hll.count(), hll_copy.count())

    def test_sparse_dumps(self):
        hll = Cardunion(self.log2m)
        hll_copy = Cardunion(self.log2m)
        for i in range(500):
            hll.add(str(i))

        hll_copy.loads(hll.dumps())
        self.assertEqual(hll.count(), hll_copy.count())

    def test_union(self):
        hll = Cardunion(self.log2m)
        hll_1 = Cardunion(self.log2m)
        for i in range(10000):
            hll.add(str(i))
        for i in range(10000, 20000):
            hll_1.add(str(i))

        hll.union([hll_1])
        estimate = hll.count()
        error = abs(estimate / float(20000) - 1)
        self.assertLess(error, self.error)

    def test_bunion(self):
        hll = Cardunion(self.log2m)
        hll_1 = Cardunion(self.log2m)
        hll_2 = Cardunion(self.log2m)
        for i in range(10000):
            hll.add(str(i))
        for i in range(10000, 20000):
            hll_1.add(str(i))
        for i in range(20000, 30000):
            hll_2.add(str(i))

        hll.bunion([hll_1.dumps(), hll_2.dumps()])
        estimate = hll.count()
        error = abs(estimate / float(30000) - 1)
        self.assertLess(error, self.error)

    def test_intersect(self):
        """Since there is no theoretical error bound for intersection,
        we'd use 3-sigma rule instead.
        """
        hll = Cardunion()
        hll_1 = Cardunion()
        for i in range(10000):
            hll.add(str(i))
        for i in range(5000, 15000):
            hll_1.add(str(i))

        estimate, error, _ = Cardunion.intersect([hll_1, hll])
        print estimate, error
        self.assertTrue(5000 - 3 * error <= estimate <= 5000 + 3 * error)

    def test_intersect_big_small(self):
        hll = Cardunion()
        hll_1 = Cardunion()
        for i in range(50):
            hll.add(str(i))
        for i in range(1, 100000):
            hll_1.add(str(i))

        estimate, error, _ = Cardunion.intersect([hll_1, hll])
        print estimate, error
        self.assertTrue(50 - 3 * error <= estimate <= 50 + 3 * error)

    def test_intersect_a_few(self):
        hll = Cardunion()
        hll_1 = Cardunion()
        hll_2 = Cardunion()
        for i in range(5000):
            hll.add(str(i))
        for i in range(1, 100000):
            hll_1.add(str(i))
        for i in range(25, 1000):
            hll_2.add(str(i))

        estimate, error, _ = Cardunion.intersect([hll_2, hll_1, hll])
        print estimate, error
        self.assertTrue(975 - 3 * error <= estimate <= 975 + 3 * error)

    def test_intersect_a_lot(self):
        hlls = []
        actual = 100000
        nset = 10
        for i in range(nset):
            hll = Cardunion()
            for j in range(actual):
                hll.add(str(i * 5000 + j))
            hlls.append(hll)

        estimate, error, _ = Cardunion.intersect(hlls)
        print estimate, error
        self.assertTrue(actual - (nset - 1) * 5000 - 3 * error
                        <= estimate <= actual - (nset - 1) * 5000 + 3 * error)

    def test_nonzero_counters(self):
        h = Cardunion()
        h.update_counter(1, 2)
        h.update_counter(3, 4)
        h.update_counter(5, 8)
        self.assertEquals(list(h.nonzero_counters), [(1, 2), (3, 4), (5, 8)])

########NEW FILE########
__FILENAME__ = pyebset_test
import unittest
from pyebset import BitSet


class BitSetTest(unittest.TestCase):
    """Docstring for BitSetTest """

    def test_set(self):
        b = BitSet()
        self.assertTrue(b.set(0))
        self.assertTrue(b.set(1))
        self.assertTrue(b.set(2))
        self.assertTrue(b.set(3))
        self.assertFalse(b.set(1))

    def test_dumps_loads(self):
        b = BitSet()
        self.assertTrue(b.set(0))
        self.assertTrue(b.set(1))
        self.assertTrue(b.set(4))
        self.assertTrue(b.set(8))
        self.assertTrue(b.set(16))
        s = BitSet()
        s.loads(b.dumps())
        self.assertEqual(b, s)

    def test_logical_ops(self):
        b = BitSet()
        b.set(0)
        b.set(1)
        b.set(4)
        b.set(8)
        b.set(16)
        bb = BitSet()
        bb.set(0)
        bb.set(1)
        bb.set(4)
        bb.set(9)
        cc = BitSet()
        cc.set(0)
        cc.set(1)
        cc.set(4)
        cc.set(8)
        cc.set(9)
        cc.set(16)
        dd = BitSet()
        dd.set(0)
        dd.set(1)
        dd.set(4)
        ee = BitSet()
        ee.set(2)
        ee.set(3)

        la = b & bb
        lo = b | bb
        ln = ~ dd
        ll = ~ ln
        self.assertEqual(lo, cc)
        self.assertNotEqual(la, dd)
        self.assertEqual(list(ln), list(ee))
        self.assertEqual(len(b), 5)
        self.assertEqual(len(bb), 4)
        self.assertEqual(len(cc), 6)
        self.assertEqual(len(dd), 3)
        self.assertEqual(len(ee), 2)
        self.assertEqual(len(la), 3)
        self.assertEqual(len(lo), 6)
        self.assertEqual(len(ln), 2)
        self.assertEqual(len(ll), 3)

    def test_logical_not(self):
        b = BitSet()
        b.set(0)
        b.set(1)
        b.set(8)
        b.set(9)
        c = ~b
        # test the logical not doesn't generate any numbers that are greater
        # than 9 in this case
        self.assertEqual(list(c), [2, 3, 4, 5, 6, 7])
        d = ~c
        self.assertListEqual(list(d), [0, 1, 8, 9])

    def test_logical_not_1(self):
        b = BitSet()
        b.set(0)
        b.set(1)
        b.set(7)
        b.set(8)
        c = ~b
        # test the logical not doesn't generate any numbers that are greater
        # than 9 in this case
        self.assertEqual(list(c), [2, 3, 4, 5, 6])
        d = ~c
        self.assertListEqual(list(d), [0, 1, 7, 8])

    def test_generator(self):
        b = BitSet()
        b.set(1)
        b.set(4)
        b.set(10)
        b.set(100000)
        b.set(12323131)
        self.assertEqual(list(b), [1, 4, 10, 100000, 12323131])

    def test_contains(self):
        b = BitSet()
        b.set(1)
        b.set(4)
        b.set(10)
        b.set(100000)
        b.set(12323131)
        for i in [1, 4, 10, 100000, 12323131]:
            self.assertTrue(i in b)
        for i in [2, 3, 5, 6, 1232312]:
            self.assertTrue(i not in b)

    def test_eq_ne(self):
        b = BitSet()
        b.set(1)
        b.set(2)
        bb = BitSet()
        bb.set(1)
        bb.set(2)
        cc = BitSet()
        cc.set(2)
        cc.set(3)
        self.assertTrue(b == bb)
        self.assertTrue(bb != cc)

########NEW FILE########
__FILENAME__ = test_cursor
# -*- coding: utf-8 -*-
import mdb
from unittest import TestCase


class TestCursor(TestCase):

    def setUp(self):
        import os
        import errno
        self.path = './testdbm'
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise
        self.env = mdb.Env(self.path, max_dbs=8)
        self.txn = self.env.begin_txn()
        self.db = self.env.open_db(self.txn, 'test_cursor')
        self.db.drop(self.txn, 0)
        self.txn.commit()
        self.txn = self.env.begin_txn()

    def tearDown(self):
        import shutil
        self.txn.commit()
        self.db.close()
        self.env.close()
        shutil.rmtree(self.path)

    def test_put(self):
        # all keys must be sorted
        cursor = mdb.Cursor(self.txn, self.db)
        cursor.put('foo', 'bar', mdb.MDB_APPENDDUP)
        self.assertEqual(cursor.get('foo'), ('foo', 'bar'))

    def test_put_unicode(self):
        # all keys must be sorted
        cursor = mdb.Cursor(self.txn, self.db)
        cursor.put('fΩo', 'b∑r', mdb.MDB_APPENDDUP)
        self.assertEqual(cursor.get('fΩo'), ('fΩo', 'b∑r'))

    def test_put_duplicate(self):
        # all values must be sorted as well
        cursor = mdb.Cursor(self.txn, self.db)
        cursor.put('foo', 'bar', mdb.MDB_APPENDDUP)
        cursor.put('foo', 'bar1', mdb.MDB_APPENDDUP)
        self.assertEqual(cursor.count_dups(), 2)
        self.assertEqual(cursor.get('foo'), ('foo', 'bar'))
        while 1:
            key, value = cursor.get(op=mdb.MDB_NEXT_DUP)
            if not key:
                break
            self.assertEqual((key, value), ('foo', 'bar1'))

    def test_delete_by_key(self):
        cursor = mdb.Cursor(self.txn, self.db)
        cursor.put('delete', 'done', mdb.MDB_APPENDDUP)
        cursor.put('delete', 'done1', mdb.MDB_APPENDDUP)
        key, value = cursor.get('delete')
        cursor.delete(mdb.MDB_NODUPDATA)
        self.assertEqual(cursor.get('delete'), (None, None))

    def test_delete_by_key_value(self):
        cursor = mdb.Cursor(self.txn, self.db)
        cursor.put('delete', 'done', mdb.MDB_APPENDDUP)
        cursor.put('delete', 'done1', mdb.MDB_APPENDDUP)
        key, value = cursor.get('delete')
        cursor.delete()
        self.assertEqual(cursor.get('delete'), ('delete', 'done1'))

    def test_delete_by_key_value_1(self):
        cursor = mdb.Cursor(self.txn, self.db)
        cursor.put('delete', 'done', mdb.MDB_APPENDDUP)
        cursor.put('delete', 'done1', mdb.MDB_APPENDDUP)
        cursor.put('delete', 'done2', mdb.MDB_APPENDDUP)
        key, value = cursor.get('delete', 'done2', op=mdb.MDB_NEXT_DUP)
        cursor.delete()
        self.assertEqual(cursor.get('delete'), ('delete', 'done'))

########NEW FILE########
__FILENAME__ = test_db
# -*- coding: utf-8 -*-
import mdb
from unittest import TestCase


class TestDB(TestCase):

    def setUp(self):
        import os
        import errno
        self.path = './testdbm'
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise
        self.env = mdb.Env(self.path, mapsize=1 * mdb.MB, max_dbs=8)

    def tearDown(self):
        import shutil
        self.env.close()
        shutil.rmtree(self.path)

    def drop_mdb(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.drop(txn, 0)
        txn.commit()
        db.close()

    def test_drop(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        items = db.items(txn)
        self.assertRaises(StopIteration, items.next)
        db.close()

    def test_put(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'foo', 'bar')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'foo'), 'bar')
        db.close()

    def test_contains(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'fΩo', 'bar')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertTrue(db.contains(txn, 'fΩo'))
        db.close()

    def test_put_unicode(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'fΩo', 'b∑r')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'fΩo'), 'b∑r')
        db.close()

    def test_put_zerostring(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'nopstring', '')
        db.put(txn, '', '')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'nopstring'), '')
        self.assertEqual(db.get(txn, ''), '')
        txn.abort()
        db.close()

    def test_get_exception(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        self.assertEqual(db.get(txn, "Not Existed", "Default"), "Default")
        txn.commit()
        db.close()

    def test_mget(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'foo', '1')
        db.put(txn, 'bar', '2')
        db.put(txn, 'egg', '3')
        db.put(txn, 'spam', '4')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.mget(txn, ['foo', 'spam', 'egg'])),
                         ['1', '4', '3'])
        txn.commit()
        db.close()

    def test_put_excetion(self):
        import random
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        with self.assertRaises(mdb.MapFullError):
            while True:
                db.put(txn,
                       "%d" % random.randint(0, 10000),
                       'HHHh' * 100)
        txn.abort()
        db.close()

    def test_put_nodup(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'dupkey', 'no', mdb.MDB_NODUPDATA)
        with self.assertRaises(mdb.KeyExistError):
            db.put(txn, 'dupkey', 'no', mdb.MDB_NODUPDATA)
        txn.abort()
        db.close()

    def test_put_duplicate(self):
        # all values must be sorted as well
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'foo', 'bar')
        db.put(txn, 'foo', 'bar1')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_dup(txn, 'foo')],
                         ['bar', 'bar1'])
        db.close()

    def test_get_all_items(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'all', 'items')
        db.put(txn, 'all1', 'items1')
        db.put(txn, 'all', 'items2')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.dup_items(txn)),
                         [('all', 'items'), ('all', 'items2'), ('all1', 'items1')])
        db.close()

    def test_get_less_than(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, '1', 'bar')
        db.put(txn, '1', 'bar1')
        db.put(txn, '2', 'bar2')
        db.put(txn, '3', 'bar3')
        db.put(txn, '4', 'bar4')
        db.put(txn, '5', 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, '1')],
                         [('1', 'bar'), ('1', 'bar1')])
        self.assertEqual([value for value in db.get_ne(txn, '1')],
                         [('2', 'bar2'), ('3', 'bar3'), ('4', 'bar4'), ('5', 'bar5')])
        self.assertEqual([value for value in db.get_lt(txn, '3')],
                         [('1', 'bar'), ('1', 'bar1'), ('2', 'bar2')])
        self.assertEqual([value for value in db.get_le(txn, '3')],
                         [('1', 'bar'), ('1', 'bar1'), ('2', 'bar2'), ('3', 'bar3')])
        self.assertEqual([value for value in db.get_gt(txn, '1')],
                         [('2', 'bar2'), ('3', 'bar3'), ('4', 'bar4'), ('5', 'bar5')])
        self.assertEqual([value for value in db.get_ge(txn, '3')],
                         [('3', 'bar3'), ('4', 'bar4'), ('5', 'bar5')])
        self.assertEqual([value for value in db.get_range(txn, '1', '3')],
                         [('1', 'bar'), ('1', 'bar1'), ('2', 'bar2'), ('3', 'bar3')])
        txn.commit()
        db.close()

    def test_delete_by_key(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'delete', 'done')
        db.put(txn, 'delete', 'done1')
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 'delete')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'delete', None), None)
        txn.abort()
        db.close()

    def test_delete_by_key_value(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.put(txn, 'delete', 'done')
        db.put(txn, 'delete', 'done1')
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 'delete', 'done')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'delete'), 'done1')
        db.close()

########NEW FILE########
__FILENAME__ = test_greater_failure
# -*- coding: utf-8 -*-
import mdb
from unittest import TestCase


class TestGreaterFailure(TestCase):

    def setUp(self):
        import os
        import errno
        self.path = './testdbmi'
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise
        self.env = mdb.Env(self.path, mapsize=1 * mdb.MB, max_dbs=8)

    def tearDown(self):
        import shutil
        self.env.close()
        shutil.rmtree(self.path)

    def drop_mdb(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY,
                              key_inttype=mdb.MDB_INT_32)
        db.drop(txn, 0)
        txn.commit()
        db.close()

    def test_intstr_greater_failure(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_INTEGERKEY|mdb.MDB_DUPSORT,
                              key_inttype=mdb.MDB_INT_32)
        db.put(txn,184504, 'bar1')
        db.put(txn,184031, 'bar2')
        db.put(txn,145248, 'bar3')
        db.put(txn,84131 , 'bar4')
        db.put(txn,3869  , 'bar5')
        db.put(txn,124034, 'bar6')
        db.put(txn,90752 , 'bar7')
        db.put(txn,48288 , 'bar8')
        db.put(txn,97573 , 'bar9')
        db.put(txn,18455 , 'bar0')

        txn.commit()
        txn = self.env.begin_txn()
        res = list(db.get_gt(txn, 50000))
        self.assertEqual(len(res), 7)
        res = list(db.get_gt(txn, 84131))
        self.assertEqual(len(res), 6)
        res = list(db.get_ge(txn, 84131))
        self.assertEqual(len(res), 7)
        txn.commit()
        db.close()

    def test_intint_greater_failure(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_INTEGERKEY|mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP,
                              key_inttype=mdb.MDB_INT_32)
        db.put(txn,184504, 1)
        db.put(txn,184031, 2)
        db.put(txn,145248, 3)
        db.put(txn,84131 , 4)
        db.put(txn,3869  , 5)
        db.put(txn,124034, 6)
        db.put(txn,90752 , 7)
        db.put(txn,48288 , 8)
        db.put(txn,97573 , 9)
        db.put(txn,18455 , 0)

        txn.commit()
        txn = self.env.begin_txn()
        res = list(db.get_gt(txn, 50000))
        self.assertEqual(len(res), 7)
        res = list(db.get_gt(txn, 84131))
        self.assertEqual(len(res), 6)
        res = list(db.get_ge(txn, 84131))
        self.assertEqual(len(res), 7)
        txn.commit()
        db.close()

    def test_strstr_greater_failure(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE)
        db.put(txn,'holy', 'bar1')
        db.put(txn,'smolly', 'bar2')
        db.put(txn,'abacus', 'bar3')
        db.put(txn,'dreadlock' , 'bar4')
        db.put(txn,'inno'  , 'bar5')
        db.put(txn,'db', 'bar6')
        db.put(txn,'idiotic' , 'bar7')
        db.put(txn,'idioms' , 'bar8')

        txn.commit()
        txn = self.env.begin_txn()
        res = list(db.get_gt(txn, 'grover'))
        self.assertEqual(len(res), 5)
        res = list(db.get_gt(txn, 'db'))
        self.assertEqual(len(res), 6)
        res = list(db.get_ge(txn, 'db'))
        self.assertEqual(len(res), 7)
        txn.commit()
        db.close()

    def test_strint_greater_failure(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_INTEGERDUP)
        db.put(txn,'holy', 1)
        db.put(txn,'smolly', 2)
        db.put(txn,'abacus', 3)
        db.put(txn,'dreadlock' , 4)
        db.put(txn,'inno'  , 5)
        db.put(txn,'db', 6)
        db.put(txn,'idiotic' , 7)
        db.put(txn,'idioms' , 8)

        txn.commit()
        txn = self.env.begin_txn()
        res = list(db.get_gt(txn, 'grover'))
        self.assertEqual(len(res), 5)
        res = list(db.get_gt(txn, 'db'))
        self.assertEqual(len(res), 6)
        res = list(db.get_ge(txn, 'db'))
        self.assertEqual(len(res), 7)
        txn.commit()
        db.close()


########NEW FILE########
__FILENAME__ = test_intdb
# -*- coding: utf-8 -*-
import mdb
from unittest import TestCase


class TestDB(TestCase):

    def setUp(self):
        import os
        import errno
        self.path = './testdbmi'
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise
        self.env = mdb.Env(self.path, mapsize=1 * mdb.MB, max_dbs=8)

    def tearDown(self):
        import shutil
        self.env.close()
        shutil.rmtree(self.path)

    def drop_mdb(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.drop(txn, 0)
        txn.commit()
        db.close()

    def test_drop(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        items = db.items(txn)
        self.assertRaises(StopIteration, items.next)
        txn.commit()
        db.close()

    def test_put(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, -11, 'bar')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, -11), 'bar')
        txn.commit()
        db.close()

    def test_contains(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 1024, "zzz")
        txn.commit()
        txn = self.env.begin_txn()
        self.assertTrue(db.contains(txn, 1024))
        db.close()

    def test_get_neighbours(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', flags=mdb.MDB_CREATE|mdb.MDB_INTEGERKEY)
        db.put(txn, 1, "1")
        db.put(txn, 5, "2")
        db.put(txn, 7, "3")
        db.put(txn, 8, "5")
        db.put(txn, 18, "6")
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get_neighbours(txn, 0),
                         ((1, "1"), (1, "1")))
        self.assertEqual(db.get_neighbours(txn, 1),
                         ((1, "1"), (1, "1")))
        self.assertEqual(db.get_neighbours(txn, 2),
                         ((1, "1"), (5, "2")))
        self.assertEqual(db.get_neighbours(txn, 3),
                         ((1, "1"), (5, "2")))
        self.assertEqual(db.get_neighbours(txn, 4),
                         ((1, "1"), (5, "2")))
        self.assertEqual(db.get_neighbours(txn, 5),
                         ((5, "2"), (5, "2")))
        self.assertEqual(db.get_neighbours(txn, 6),
                         ((5, "2"), (7, "3")))
        self.assertEqual(db.get_neighbours(txn, 7),
                         ((7, "3"), (7, "3")))
        self.assertEqual(db.get_neighbours(txn, 8),
                         ((8, "5"), (8, "5")))
        self.assertEqual(db.get_neighbours(txn, 9),
                         ((8, "5"), (18, "6")))
        self.assertEqual(db.get_neighbours(txn, 99),
                         ((18, "6"), (18, "6")))
        self.assertListEqual(list(db.mgetex(txn, range(10))),
                             ["1", "1", "1", "1", "1", "2", "2", "3", "5", "5"])

    def test_put_unicode(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 32768, 'b∑r')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 32768), 'b∑r')
        txn.commit()
        db.close()

    def test_get_exception(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        self.assertEqual(db.get(txn, 1321312312, 1), 1)
        txn.commit()
        db.close()

    def test_put_excetion(self):
        import random
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        with self.assertRaises(mdb.MapFullError):
            while True:
                db.put(txn,
                       random.randint(0, 10000),
                       'HHHh' * 100)
        txn.abort()
        db.close()

    def test_put_nodup(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 12345, 'no', mdb.MDB_NODUPDATA)
        with self.assertRaises(mdb.KeyExistError):
            db.put(txn, 12345, 'no', mdb.MDB_NODUPDATA)
        txn.abort()
        db.close()

    def test_put_duplicate(self):
        # all values must be sorted as well
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 13, 'bar')
        db.put(txn, 13, 'bar1')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_dup(txn, 13)],
                         ['bar', 'bar1'])
        txn.commit()
        db.close()

    def test_mget(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 1, 'bar')
        db.put(txn, 1, 'bar1')
        db.put(txn, 2, 'bar2')
        db.put(txn, 2, 'bar2-1')
        db.put(txn, 2, 'bar2-2')
        db.put(txn, 3, 'bar3')
        db.put(txn, 4, 'bar4')
        db.put(txn, 5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.mget(txn, [1, 2, 3, 5])),
                         ['bar', 'bar2', 'bar3', 'bar5'])

    def test_mget_1(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 1, 'bar')
        db.put(txn, 1, 'bar1')
        db.put(txn, 2, 'bar2')
        db.put(txn, 2, 'bar2-1')
        db.put(txn, 2, 'bar2-2')
        db.put(txn, 3, 'bar3')
        db.put(txn, 4, 'bar4')
        db.put(txn, 5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.mget(txn, [2, 5])),
                         ['bar2', 'bar5'])

    def test_get_less_than(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 1, 'bar')
        db.put(txn, 1, 'bar1')
        db.put(txn, 2, 'bar2')
        db.put(txn, 2, 'bar2-1')
        db.put(txn, 2, 'bar2-2')
        db.put(txn, 3, 'bar3')
        db.put(txn, 4, 'bar4')
        db.put(txn, 5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 2)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_eq(txn, 3)],
                         [(3, 'bar3')])
        self.assertEqual([value for value in db.get_lt(txn, 1)],
                         [])
        self.assertEqual([value for value in db.get_lt(txn, 3)],
                         [(1, 'bar'), (1, 'bar1'), (2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_lt(txn, 2)],
                         [(1, 'bar'), (1, 'bar1')])
        self.assertEqual([value for value in db.get_gt(txn, 2)],
                         [(3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 3)],
                         [(4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 4)],
                         [(5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 5)],
                         [])
        self.assertEqual([value for value in db.get_le(txn, 2)],
                         [(1, 'bar'), (1, 'bar1'), (2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_ge(txn, 2)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2'),
                          (3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_ne(txn, 2)],
                         [(1, 'bar'), (1, 'bar1'),
                          (3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_range(txn, 2, 4)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2'),
                          (3, 'bar3'), (4, 'bar4')])
        txn.commit()
        db.close()

    def test_get_all_items(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 14, 'items')
        db.put(txn, 15, 'items1')
        db.put(txn, 14, 'items2')
        txn.commit()
        txn = self.env.begin_txn()
        values = [value for key, value in db.items(txn)]
        self.assertEqual(values,
                         ['items', 'items1'])
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.dup_items(txn)),
                         [(14, 'items'), (14, 'items2'), (15, 'items1')])
        txn.commit()
        db.close()

    def test_delete_by_key(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 16, 'done')
        db.put(txn, 16, 'done1')
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 16)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 16), None)
        txn.abort()
        db.close()

    def test_delete_by_key_value(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY)
        db.put(txn, 17, 'done')
        db.put(txn, 17, 'done1')
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 17, 'done')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 17), 'done1')
        txn.commit()
        db.close()

    def test_range_for_int8(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY,
                              key_inttype=mdb.MDB_INT_8)
        db.put(txn, -1, 'bar')
        db.put(txn, -1, 'bar1')
        db.put(txn, -2, 'bar2')
        db.put(txn, -2, 'bar2-1')
        db.put(txn, -2, 'bar2-2')
        db.put(txn, -3, 'bar3')
        db.put(txn, -4, 'bar4')
        db.put(txn, -5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, -2)],
                         [(-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2')])
        self.assertEqual([value for value in db.get_eq(txn, -3)],
                         [(-3, 'bar3')])
        self.assertEqual([value for value in db.get_gt(txn, -1)],
                         [])
        self.assertEqual([value for value in db.get_gt(txn, -3)],
                         [(-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2'),
                          (-1, 'bar'), (-1, 'bar1')])
        self.assertEqual([value for value in db.get_gt(txn, -2)],
                         [(-1, 'bar'), (-1, 'bar1')])
        self.assertEqual([value for value in db.get_lt(txn, -2)],
                         [(-5, 'bar5'), (-4, 'bar4'), (-3, 'bar3')])
        self.assertEqual([value for value in db.get_lt(txn, -3)],
                         [(-5, 'bar5'), (-4, 'bar4')])
        self.assertEqual([value for value in db.get_lt(txn, -4)],
                         [(-5, 'bar5')])
        self.assertEqual([value for value in db.get_lt(txn, -5)],
                         [])
        self.assertEqual([value for value in db.get_ge(txn, -2)],
                         [(-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2'),
                          (-1, 'bar'), (-1, 'bar1')])
        self.assertEqual([value for value in db.get_le(txn, -2)],
                         [(-5, 'bar5'), (-4, 'bar4'), (-3, 'bar3'),
                          (-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2')])
        self.assertEqual([value for value in db.get_ne(txn, -2)],
                         [(-5, 'bar5'), (-4, 'bar4'), (-3, 'bar3'),
                          (-1, 'bar'), (-1, 'bar1'), ])
        self.assertEqual([value for value in db.get_range(txn, -4, -2)],
                         [(-4, 'bar4'), (-3, 'bar3'), (-2, 'bar2'),
                          (-2, 'bar2-1'), (-2, 'bar2-2'), ])
        txn.commit()
        db.close()

    def test_range_for_uint8(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY,
                              key_inttype=mdb.MDB_INT_8)
        db.put(txn, 1, 'bar')
        db.put(txn, 1, 'bar1')
        db.put(txn, 2, 'bar2')
        db.put(txn, 2, 'bar2-1')
        db.put(txn, 2, 'bar2-2')
        db.put(txn, 3, 'bar3')
        db.put(txn, 4, 'bar4')
        db.put(txn, 5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 2)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_eq(txn, 3)],
                         [(3, 'bar3')])
        self.assertEqual([value for value in db.get_lt(txn, 1)],
                         [])
        self.assertEqual([value for value in db.get_lt(txn, 3)],
                         [(1, 'bar'), (1, 'bar1'), (2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_lt(txn, 2)],
                         [(1, 'bar'), (1, 'bar1')])
        self.assertEqual([value for value in db.get_gt(txn, 2)],
                         [(3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 3)],
                         [(4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 4)],
                         [(5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 5)],
                         [])
        self.assertEqual([value for value in db.get_le(txn, 2)],
                         [(1, 'bar'), (1, 'bar1'), (2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_ge(txn, 2)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2'),
                          (3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_ne(txn, 2)],
                         [(1, 'bar'), (1, 'bar1'),
                          (3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_range(txn, 2, 4)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2'),
                          (3, 'bar3'), (4, 'bar4')])
        txn.commit()
        db.close()

    def test_range_for_int16(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY,
                              key_inttype=mdb.MDB_INT_16)
        db.put(txn, -1, 'bar')
        db.put(txn, -1, 'bar1')
        db.put(txn, -2, 'bar2')
        db.put(txn, -2, 'bar2-1')
        db.put(txn, -2, 'bar2-2')
        db.put(txn, -3, 'bar3')
        db.put(txn, -4, 'bar4')
        db.put(txn, -5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, -2)],
                         [(-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2')])
        self.assertEqual([value for value in db.get_eq(txn, -3)],
                         [(-3, 'bar3')])
        self.assertEqual([value for value in db.get_gt(txn, -1)],
                         [])
        self.assertEqual([value for value in db.get_gt(txn, -3)],
                         [(-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2'),
                          (-1, 'bar'), (-1, 'bar1')])
        self.assertEqual([value for value in db.get_gt(txn, -2)],
                         [(-1, 'bar'), (-1, 'bar1')])
        self.assertEqual([value for value in db.get_lt(txn, -2)],
                         [(-5, 'bar5'), (-4, 'bar4'), (-3, 'bar3')])
        self.assertEqual([value for value in db.get_lt(txn, -3)],
                         [(-5, 'bar5'), (-4, 'bar4')])
        self.assertEqual([value for value in db.get_lt(txn, -4)],
                         [(-5, 'bar5')])
        self.assertEqual([value for value in db.get_lt(txn, -5)],
                         [])
        self.assertEqual([value for value in db.get_ge(txn, -2)],
                         [(-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2'),
                          (-1, 'bar'), (-1, 'bar1')])
        self.assertEqual([value for value in db.get_le(txn, -2)],
                         [(-5, 'bar5'), (-4, 'bar4'), (-3, 'bar3'),
                          (-2, 'bar2'), (-2, 'bar2-1'), (-2, 'bar2-2')])
        self.assertEqual([value for value in db.get_ne(txn, -2)],
                         [(-5, 'bar5'), (-4, 'bar4'), (-3, 'bar3'),
                          (-1, 'bar'), (-1, 'bar1'), ])
        self.assertEqual([value for value in db.get_range(txn, -4, -2)],
                         [(-4, 'bar4'), (-3, 'bar3'), (-2, 'bar2'),
                          (-2, 'bar2-1'), (-2, 'bar2-2'), ])
        txn.commit()
        db.close()

    def test_range_for_uint16(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY,
                              key_inttype=mdb.MDB_UINT_16)
        db.put(txn, 1, 'bar')
        db.put(txn, 1, 'bar1')
        db.put(txn, 2, 'bar2')
        db.put(txn, 2, 'bar2-1')
        db.put(txn, 2, 'bar2-2')
        db.put(txn, 3, 'bar3')
        db.put(txn, 4, 'bar4')
        db.put(txn, 5, 'bar5')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 2)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_eq(txn, 3)],
                         [(3, 'bar3')])
        self.assertEqual([value for value in db.get_lt(txn, 1)],
                         [])
        self.assertEqual([value for value in db.get_lt(txn, 3)],
                         [(1, 'bar'), (1, 'bar1'), (2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_lt(txn, 2)],
                         [(1, 'bar'), (1, 'bar1')])
        self.assertEqual([value for value in db.get_gt(txn, 2)],
                         [(3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 3)],
                         [(4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 4)],
                         [(5, 'bar5')])
        self.assertEqual([value for value in db.get_gt(txn, 5)],
                         [])
        self.assertEqual([value for value in db.get_le(txn, 2)],
                         [(1, 'bar'), (1, 'bar1'), (2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2')])
        self.assertEqual([value for value in db.get_ge(txn, 2)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2'),
                          (3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_ne(txn, 2)],
                         [(1, 'bar'), (1, 'bar1'),
                          (3, 'bar3'), (4, 'bar4'), (5, 'bar5')])
        self.assertEqual([value for value in db.get_range(txn, 2, 4)],
                         [(2, 'bar2'), (2, 'bar2-1'), (2, 'bar2-2'),
                          (3, 'bar3'), (4, 'bar4')])
        txn.commit()
        db.close()

########NEW FILE########
__FILENAME__ = test_intintdb
# -*- coding: utf-8 -*-
import mdb
from unittest import TestCase


class TestDB(TestCase):

    def setUp(self):
        import os
        import errno
        self.path = './testdbmii'
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise
        self.env = mdb.Env(self.path, mapsize=1 * mdb.MB, max_dbs=8,
                           flags=mdb.MDB_WRITEMAP|mdb.MDB_NOSYNC)

    def tearDown(self):
        import shutil
        self.env.close()
        shutil.rmtree(self.path)

    def drop_mdb(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.drop(txn, 0)
        txn.commit()
        db.close()

    def test_drop(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        items = db.items(txn)
        self.assertRaises(StopIteration, items.next)
        txn.commit()
        db.close()

    def test_put(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, -11, -11)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, -11), -11)
        txn.commit()
        db.close()

    def test_mget(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 1, 1)
        db.put(txn, 1, 11)
        db.put(txn, 2, 2)
        db.put(txn, 2, 21)
        db.put(txn, 2, 22)
        db.put(txn, 3, 3)
        db.put(txn, 4, 4)
        db.put(txn, 5, 5)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.mget(txn, [1, 2, 3, 5])),
                         [1, 2, 3, 5])
        self.assertEqual(list(db.mget(txn, [3, 1, 2, 5])),
                         [3, 1, 2, 5])

    def test_get_neighbours(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 1, 1)
        db.put(txn, 5, 2)
        db.put(txn, 7, 3)
        db.put(txn, 8, 5)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get_neighbours(txn, 0),
                         ((1, 1), (1, 1)))
        self.assertEqual(db.get_neighbours(txn, 1),
                         ((1, 1), (1, 1)))
        self.assertEqual(db.get_neighbours(txn, 2),
                         ((1, 1), (5, 2)))
        self.assertEqual(db.get_neighbours(txn, 3),
                         ((1, 1), (5, 2)))
        self.assertEqual(db.get_neighbours(txn, 4),
                         ((1, 1), (5, 2)))
        self.assertEqual(db.get_neighbours(txn, 5),
                         ((5, 2), (5, 2)))
        self.assertEqual(db.get_neighbours(txn, 6),
                         ((5, 2), (7, 3)))
        self.assertEqual(db.get_neighbours(txn, 7),
                         ((7, 3), (7, 3)))
        self.assertEqual(db.get_neighbours(txn, 8),
                         ((8, 5), (8, 5)))
        self.assertEqual(db.get_neighbours(txn, 9),
                         ((8, 5), (8, 5)))
        self.assertListEqual(list(db.mgetex(txn, range(10))),
                             [1, 1, 1, 1, 1, 2, 2, 3, 5, 5])

    def test_contains(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 1024, 2)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertTrue(db.contains(txn, 1024))
        db.close()

    def test_get_exception(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        self.assertEqual(db.get(txn, 1321312312, 12), 12)
        txn.commit()
        db.close()

    def test_put_duplicate(self):
        # all values must be sorted as well
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP,
                              key_inttype=mdb.MDB_INT_16, value_inttype=mdb.MDB_INT_64)
        db.put(txn, 13, 1312321313123)
        db.put(txn, 13, 1431231231231)
        db.put(txn, 13123, 1431231231231)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_dup(txn, 13)],
                         [1312321313123, 1431231231231])
        self.assertEqual(db.get(txn, 13123), 1431231231231)
        txn.commit()
        db.close()

    def test_get_less_than(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 1, 1)
        db.put(txn, 1, 11)
        db.put(txn, 2, 2)
        db.put(txn, 2, 21)
        db.put(txn, 2, 22)
        db.put(txn, 3, 3)
        db.put(txn, 4, 4)
        db.put(txn, 5, 5)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 2)],
                         [(2, 2), (2, 21), (2, 22)])
        self.assertEqual([value for value in db.get_eq(txn, 3)],
                         [(3, 3)])
        self.assertEqual([value for value in db.get_lt(txn, 1)],
                         [])
        self.assertEqual([value for value in db.get_lt(txn, 3)],
                         [(1, 1), (1, 11), (2, 2), (2, 21), (2, 22)])
        self.assertEqual([value for value in db.get_lt(txn, 2)],
                         [(1, 1), (1, 11)])
        self.assertEqual([value for value in db.get_gt(txn, 2)],
                         [(3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 3)],
                         [(4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 4)],
                         [(5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 5)],
                         [])
        self.assertEqual([value for value in db.get_le(txn, 2)],
                         [(1, 1), (1, 11), (2, 2), (2, 21), (2, 22)])
        self.assertEqual([value for value in db.get_ge(txn, 2)],
                         [(2, 2), (2, 21), (2, 22),
                          (3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_ne(txn, 2)],
                         [(1, 1), (1, 11),
                          (3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_range(txn, 2, 4)],
                         [(2, 2), (2, 21), (2, 22),
                          (3, 3), (4, 4)])
        txn.commit()
        db.close()

    def test_range_uint8(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP,
                              key_inttype=mdb.MDB_UINT_8,
                              value_inttype=mdb.MDB_UINT_8)
        db.put(txn, 1, 1)
        db.put(txn, 1, 11)
        db.put(txn, 2, 2)
        db.put(txn, 2, 21)
        db.put(txn, 2, 22)
        db.put(txn, 3, 3)
        db.put(txn, 4, 4)
        db.put(txn, 5, 5)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 2)],
                         [(2, 2), (2, 21), (2, 22)])
        self.assertEqual([value for value in db.get_eq(txn, 3)],
                         [(3, 3)])
        self.assertEqual([value for value in db.get_lt(txn, 1)],
                         [])
        self.assertEqual([value for value in db.get_lt(txn, 3)],
                         [(1, 1), (1, 11), (2, 2), (2, 21), (2, 22)])
        self.assertEqual([value for value in db.get_lt(txn, 2)],
                         [(1, 1), (1, 11)])
        self.assertEqual([value for value in db.get_gt(txn, 2)],
                         [(3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 3)],
                         [(4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 4)],
                         [(5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 5)],
                         [])
        self.assertEqual([value for value in db.get_le(txn, 2)],
                         [(1, 1), (1, 11), (2, 2), (2, 21), (2, 22)])
        self.assertEqual([value for value in db.get_ge(txn, 2)],
                         [(2, 2), (2, 21), (2, 22),
                          (3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_ne(txn, 2)],
                         [(1, 1), (1, 11),
                          (3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_range(txn, 2, 4)],
                         [(2, 2), (2, 21), (2, 22),
                          (3, 3), (4, 4)])
        txn.commit()
        db.close()

    def test_range_int8(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP,
                              key_inttype=mdb.MDB_INT_8,
                              value_inttype=mdb.MDB_INT_8)
        db.put(txn, 1, 1)
        db.put(txn, 1, -11)
        db.put(txn, 2, 2)
        db.put(txn, 2, -21)
        db.put(txn, 2, 22)
        db.put(txn, 3, 3)
        db.put(txn, 4, 4)
        db.put(txn, 5, 5)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 2)],
                         [(2, -21), (2, 2), (2, 22)])
        self.assertEqual([value for value in db.get_eq(txn, 3)],
                         [(3, 3)])
        self.assertEqual([value for value in db.get_lt(txn, 1)],
                         [])
        self.assertEqual([value for value in db.get_lt(txn, 3)],
                         [(1, -11), (1, 1), (2, -21), (2, 2), (2, 22)])
        self.assertEqual([value for value in db.get_lt(txn, 2)],
                         [(1, -11), (1, 1)])
        self.assertEqual([value for value in db.get_gt(txn, 2)],
                         [(3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 3)],
                         [(4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 4)],
                         [(5, 5)])
        self.assertEqual([value for value in db.get_gt(txn, 5)],
                         [])
        self.assertEqual([value for value in db.get_le(txn, 2)],
                         [(1, -11), (1, 1), (2, -21), (2, 2), (2, 22)])
        self.assertEqual([value for value in db.get_ge(txn, 2)],
                         [(2, -21), (2, 2), (2, 22),
                          (3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_ne(txn, 2)],
                         [(1, -11), (1, 1),
                          (3, 3), (4, 4), (5, 5)])
        self.assertEqual([value for value in db.get_range(txn, 2, 4)],
                         [(2, -21), (2, 2), (2, 22),
                          (3, 3), (4, 4)])
        txn.commit()
        db.close()

    def test_get_all_items(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 14, 14)
        db.put(txn, 15, 15)
        db.put(txn, 14, 141)
        txn.commit()
        txn = self.env.begin_txn()
        values = [value for key, value in db.items(txn)]
        self.assertEqual(values,
                         [14, 15])
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.dup_items(txn)),
                         [(14, 14), (14, 141), (15, 15)])
        txn.commit()
        db.close()

    def test_delete_by_key(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 16, 16)
        db.put(txn, 16, 161)
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 16)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 16), None)
        txn.abort()
        db.close()

    def test_delete_by_key_value(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db',
                              flags=mdb.MDB_CREATE|mdb.MDB_DUPSORT|mdb.MDB_INTEGERKEY|mdb.MDB_INTEGERDUP)
        db.put(txn, 17, 17)
        db.put(txn, 17, 171)
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 17, 17)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 17), 171)
        txn.commit()
        db.close()

########NEW FILE########
__FILENAME__ = test_intreader
# -*- coding: utf-8 -*-
from unittest import TestCase
from mdb import Writer, Reader, DupReader


class TestReaderWriter(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree('./test_rw')
        except OSError:
            pass
        try:
            shutil.rmtree('./test_rw_dup')
        except OSError:
            pass

    def test_reader_and_writer(self):
        writer = Writer('./test_rw', int_key=True)
        writer.drop()
        writer.put(1234, 'bar')
        writer.put(5678, 'spam')
        reader = Reader('./test_rw', int_key=True)
        value = reader.get(1234)
        self.assertEqual(value, 'bar')
        value = reader.get(5678)
        self.assertEqual(value, 'spam')

    def test_dup_reader_and_writer(self):
        def key_value_gen():
            for i in range(3):
                yield 789, "value%d" % (i * i)
        writer = Writer('./test_rw_dup', int_key=True, dup=True)
        writer.drop()
        writer.put(123, 'bar')
        writer.put(456, 'spam')
        writer.mput({123: "bar1", 456: "spam1"})
        writer.mput(key_value_gen())
        reader = DupReader('./test_rw_dup', int_key=True)
        values = reader.get(123)
        self.assertEqual(list(values), ['bar', 'bar1'])
        values = reader.get(456)
        self.assertEqual(list(values), ['spam', 'spam1'])
        values = reader.get(789)
        self.assertEqual(list(values), ['value0', 'value1', 'value4'])

########NEW FILE########
__FILENAME__ = test_reader
# -*- coding: utf-8 -*-
from unittest import TestCase
from mdb import Writer, Reader, DupReader
from ujson import dumps, loads


class TestReaderWriter(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree('./test_rw')
        except OSError:
            pass
        try:
            shutil.rmtree('./test_rw_dup')
        except OSError:
            pass

    def test_reader_and_writer(self):
        writer = Writer('./test_rw', encode_fn=dumps)
        writer.drop()
        writer.put('foo', 'bar')
        writer.put('egg', 'spam')
        reader = Reader('./test_rw', decode_fn=loads)
        value = reader.get('foo')
        self.assertEqual(value, 'bar')
        value = reader.get('egg')
        self.assertEqual(value, 'spam')

    def test_dup_reader_and_writer(self):
        def key_value_gen():
            for i in range(3):
                yield 'fixed', "value%d" % (i * i)
        writer = Writer('./test_rw_dup', dup=True,
                        encode_fn=dumps)
        writer.drop()
        writer.put('foo', 'bar')
        writer.put('egg', 'spam')
        writer.mput({"foo": "bar1", "egg": "spam1"})
        writer.mput(key_value_gen())
        reader = DupReader('./test_rw_dup',
                           decode_fn=loads)
        values = reader.get('foo')
        self.assertEqual(list(values), ['bar', 'bar1'])
        values = reader.get('egg')
        self.assertEqual(list(values), ['spam', 'spam1'])
        values = reader.get('fixed')
        self.assertEqual(list(values), ['value0', 'value1', 'value4'])

########NEW FILE########
__FILENAME__ = test_strintdb
# -*- coding: utf-8 -*-
import mdb
from unittest import TestCase


class TestDB(TestCase):

    def setUp(self):
        import os
        import errno
        self.path = './testdbm'
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise
        self.env = mdb.Env(self.path, mapsize=1 * mdb.MB, max_dbs=8)

    def tearDown(self):
        import shutil
        self.env.close()
        shutil.rmtree(self.path)

    def drop_mdb(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        db.drop(txn, 0)
        txn.commit()
        db.close()

    def test_drop(self):
        self.drop_mdb()
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db')
        items = db.items(txn)
        self.assertRaises(StopIteration, items.next)
        db.close()

    def test_put(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_UINT_64)
        db.put(txn, 'foo', 9223371238321823122)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'foo'), 9223371238321823122)
        db.close()

    def test_put_unicode(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        db.put(txn, 'fΩo', 2)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'fΩo'), 2)
        db.close()

    def test_contains(self):
        # all keys must be sorted
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        db.put(txn, 'fΩo', 2)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertTrue(db.contains(txn, 'fΩo'))
        db.close()

    def test_get_exception(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        self.assertEqual(db.get(txn, "Not Existed", ""), "")
        txn.commit()
        db.close()

    def test_put_duplicate(self):
        # all values must be sorted as well
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        db.put(txn, 'foo', 1)
        db.put(txn, 'foo', 2)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_dup(txn, 'foo')],
                         [1, 2])
        db.close()

    def test_mget(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_UINT_8)
        db.drop(txn)
        db.put(txn, 'bar1', 1)
        db.put(txn, 'bar1', 2)
        db.put(txn, 'bar2', 3)
        db.put(txn, 'bar3', 4)
        db.put(txn, 'bar4', 5)
        db.put(txn, 'bar5', 6)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertListEqual(list(db.mget(txn, ['bar1', 'bar2', 'bar5'])),
                             [1, 3, 6])
        self.assertListEqual(list(db.mget(txn, ['bar5', 'bar1', 'bar3', 'bar4'])),
                             [6, 1, 4, 5])

    def test_get_all_items(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_INT_64)
        db.put(txn, 'all', 1323123132131231312)
        db.put(txn, 'all1', 2123123123131312313)
        db.put(txn, 'all', 1231231231231312313)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(list(db.dup_items(txn)),
                         [('all', 1231231231231312313), ('all', 1323123132131231312),
                          ('all1', 2123123123131312313)])
        db.close()

    def test_get_less_than(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        db.drop(txn)
        db.put(txn, 'bar1', 1)
        db.put(txn, 'bar1', 2)
        db.put(txn, 'bar2', 3)
        db.put(txn, 'bar3', 4)
        db.put(txn, 'bar4', 5)
        db.put(txn, 'bar5', 6)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 'bar1')],
                         [('bar1', 1), ('bar1', 2)])
        self.assertEqual([value for value in db.get_ne(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_lt(txn, 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3)])
        self.assertEqual([value for value in db.get_le(txn, 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4)])
        self.assertEqual([value for value in db.get_gt(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_ge(txn, 'bar1')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_range(txn, 'bar1', 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4)])
        txn.commit()
        db.close()

    def test_range_uint8(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_UINT_8)
        db.drop(txn)
        db.put(txn, 'bar1', 1)
        db.put(txn, 'bar1', 2)
        db.put(txn, 'bar2', 3)
        db.put(txn, 'bar3', 4)
        db.put(txn, 'bar4', 5)
        db.put(txn, 'bar5', 6)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 'bar1')],
                         [('bar1', 1), ('bar1', 2)])
        self.assertEqual([value for value in db.get_ne(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_lt(txn, 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3)])
        self.assertEqual([value for value in db.get_le(txn, 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4)])
        self.assertEqual([value for value in db.get_gt(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_ge(txn, 'bar1')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_range(txn, 'bar1', 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4)])
        txn.commit()
        db.close()

    def test_range_int8(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_INT_8)
        db.drop(txn)
        db.put(txn, 'bar1', -1)
        db.put(txn, 'bar1', -2)
        db.put(txn, 'bar2', 3)
        db.put(txn, 'bar3', 4)
        db.put(txn, 'bar4', 5)
        db.put(txn, 'bar5', 6)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 'bar1')],
                         [('bar1', -2), ('bar1', -1)])
        self.assertEqual([value for value in db.get_ne(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_lt(txn, 'bar3')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3)])
        self.assertEqual([value for value in db.get_le(txn, 'bar3')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3), ('bar3', 4)])
        self.assertEqual([value for value in db.get_gt(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_ge(txn, 'bar1')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_range(txn, 'bar1', 'bar3')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3), ('bar3', 4)])
        txn.commit()
        db.close()

    def test_range_uint16(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_UINT_16)
        db.drop(txn)
        db.put(txn, 'bar1', 1)
        db.put(txn, 'bar1', 2)
        db.put(txn, 'bar2', 3)
        db.put(txn, 'bar3', 4)
        db.put(txn, 'bar4', 5)
        db.put(txn, 'bar5', 6)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 'bar1')],
                         [('bar1', 1), ('bar1', 2)])
        self.assertEqual([value for value in db.get_ne(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_lt(txn, 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3)])
        self.assertEqual([value for value in db.get_le(txn, 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4)])
        self.assertEqual([value for value in db.get_gt(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_ge(txn, 'bar1')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_range(txn, 'bar1', 'bar3')],
                         [('bar1', 1), ('bar1', 2), ('bar2', 3), ('bar3', 4)])
        txn.commit()
        db.close()

    def test_range_int16(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE,
                              value_inttype=mdb.MDB_INT_16)
        db.drop(txn)
        db.put(txn, 'bar1', -1)
        db.put(txn, 'bar1', -2)
        db.put(txn, 'bar2', 3)
        db.put(txn, 'bar3', 4)
        db.put(txn, 'bar4', 5)
        db.put(txn, 'bar5', 6)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual([value for value in db.get_eq(txn, 'bar1')],
                         [('bar1', -2), ('bar1', -1)])
        self.assertEqual([value for value in db.get_ne(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_lt(txn, 'bar3')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3)])
        self.assertEqual([value for value in db.get_le(txn, 'bar3')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3), ('bar3', 4)])
        self.assertEqual([value for value in db.get_gt(txn, 'bar1')],
                         [('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_ge(txn, 'bar1')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3), ('bar3', 4), ('bar4', 5), ('bar5', 6)])
        self.assertEqual([value for value in db.get_range(txn, 'bar1', 'bar3')],
                         [('bar1', -2), ('bar1', -1), ('bar2', 3), ('bar3', 4)])
        txn.commit()
        db.close()

    def test_delete_by_key(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        db.put(txn, 'delete', 1)
        db.put(txn, 'delete', 11)
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 'delete')
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'delete'), None)
        txn.abort()
        db.close()

    def test_delete_by_key_value(self):
        txn = self.env.begin_txn()
        db = self.env.open_db(txn, 'test_db', mdb.MDB_DUPSORT|mdb.MDB_INTEGERDUP|mdb.MDB_CREATE)
        db.put(txn, 'delete', 1)
        db.put(txn, 'delete', 11)
        txn.commit()
        txn = self.env.begin_txn()
        db.delete(txn, 'delete', 1)
        txn.commit()
        txn = self.env.begin_txn()
        self.assertEqual(db.get(txn, 'delete'), 11)
        db.close()

########NEW FILE########
__FILENAME__ = test_wtrie
import struct
import unittest
from wtrie import Trie


class TestWTrie(unittest.TestCase):
    def test_wtrie(self):
        t = Trie()
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hell'), 2)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellothere'), 3)
        self.assertEqual(t.add('good'), 4)
        self.assertEqual(t.add('goodbye'), 5)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellsink'), 6)
        self.assertEqual(t.add(''), 0)

        # nodes = t.nodes
        # t.print_it()

        key, sz, pt = t.node_at_path()
        self.assertEqual(sz, 2)

        key, sz, pt = t.node_at_path(104)
        self.assertEqual(key, 'hell')
        self.assertEqual(pt, 0)
        self.assertEqual(sz, 2, 'actual %s' % sz)

        key2, sz, pt = t.node_at_path(104, 111)
        self.assertEqual(key2, 'o', 'actual %s' % key)
        self.assertEqual(pt, 2)
        self.assertEqual(sz, 1)

        key, sz, pt = t.node_at_path(104, 111, 116)
        self.assertEqual(key, 'there')
        self.assertEqual(pt, 1)
        self.assertEqual(sz, 0)

        n, k, _ = t.serialize()
        self.assertEqual(len(n), 7 * 4, "actual %d" % len(n))
        self.assertEqual(len(k), 100, "actual %d" % len(k))
        # print "sqork: %s" % t.kid_space

        print 'nodes', n
        print 'kids', k

        unpacked = struct.unpack_from("7I", n, 0)
        expected = (0x02000000, 0x01000010, 0x0200000b, 0x00000013, 0x01000004, 0x00000008, 0x00000016)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH2I", k, 0)
        expected = (0, 0, 0x67000004, 0x68000002)
        self.assertEqual(unpacked, expected, unpacked)

        unpacked = struct.unpack_from("IH4cI", k, 16)
        expected = (0x0000, 0x0004, 'g', 'o', 'o', 'd', 0x62000005)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH3c", k, 32)
        expected = (0x0004, 0x0003, 'b', 'y', 'e')
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH4c2I", k, 44)
        expected = (0x0000, 0x0004, 'h', 'e', 'l', 'l', 0x6f000001, 0x73000006)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IHcI", k, 64)
        expected = (0x0002, 1, 'o', 0x74000003)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH5c", k, 76)
        expected = (0x0001, 0x0005, 't', 'h', 'e', 'r', 'e')
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH4c", k, 88)
        expected = (0x0002, 0x0004, 's', 'i', 'n', 'k')
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

########NEW FILE########
__FILENAME__ = maxhash_test
import unittest
from maxhash import MinHeap, MaxHash


class TestMinHeap(unittest.TestCase):
    def test_pop(self):
        m = MinHeap(1024, (3, 5, 2, 1))
        self.assertEqual(m.pop(), 1)
        self.assertEqual(m.pop(), 2)
        self.assertEqual(m.pop(), 3)
        self.assertEqual(m.pop(), 5)

    def test_push(self):
        m = MinHeap(1024, ())
        m.push(1)
        m.push(3)
        m.push(2)
        self.assertEqual(m.pop(), 1)
        self.assertEqual(m.pop(), 2)
        self.assertEqual(m.pop(), 3)
        m.push(1)
        m.push(3)
        m.push(2)
        m.push(4)
        m.push(6)
        m.push(5)
        self.assertEqual(m.pop(), 1)
        self.assertEqual(m.pop(), 2)
        self.assertEqual(m.pop(), 3)
        self.assertEqual(m.pop(), 4)
        self.assertEqual(m.pop(), 5)
        self.assertEqual(m.pop(), 6)

    def test_nlargest(self):
        m = MinHeap(1024, [1, 2, 3, 4, 2, 1, 5, 6])
        l = list(m.nlargest(3))
        l.sort()
        self.assertEqual(l, [4, 5, 6])


class TestMaxHash(unittest.TestCase):
    def test_add(self):
        m = MaxHash(8192)
        m.add(str(1))
        m.add(str(2))
        m.add(str(3))
        m.add(str(4))
        self.assertEqual(len(m.uniq()), 4)

    def test_merge(self):
        r1 = range(10000)
        m1 = MaxHash(8192)
        r2 = range(2000, 12000)
        m2 = MaxHash(8192)
        r3 = range(15000)
        m3 = MaxHash(8192)
        for i in r1:
            m1.add(str(i))
        for i in r2:
            m2.add(str(i))
        for i in r3:
            m3.add(str(i))
        m2.merge(m1)
        ix = MaxHash.get_jaccard_index([m2, m3])
        self.assertAlmostEqual(ix, 0.80, 2)

    def test_union(self):
        r1 = range(10000)
        m1 = MaxHash(8192)
        r2 = range(2000, 12000)
        m2 = MaxHash(8192)
        r3 = range(15000)
        m3 = MaxHash(8192)
        for i in r1:
            m1.add(str(i))
        for i in r2:
            m2.add(str(i))
        for i in r3:
            m3.add(str(i))
        m4 = m1.union(m2)
        ix = MaxHash.get_jaccard_index([m3, m4])
        self.assertAlmostEqual(ix, 0.80, 2)

    def test_jarcard_index(self):
        r1 = range(10000)
        m1 = MaxHash(8192)
        r2 = range(2000, 10000)
        m2 = MaxHash(8192)
        for i in r1:
            m1.add(str(i))
        for i in r2:
            m2.add(str(i))
        ix = MaxHash.get_jaccard_index([m1, m2])
        self.assertAlmostEqual(ix, 0.80, 2)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Hustle documentation build configuration file, created by
# sphinx-quickstart on Mon Feb 24 15:42:18 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))ht
sys.path.insert(0, os.path.abspath('../hustle'))


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Hustle'
copyright = u'2014, Tim Spurway'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinxdoc'

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
html_logo = './_static/hustle.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Hustledoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'Hustle.tex', u'Hustle Documentation',
   u'Tim Spurway', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'hustle', u'Hustle Documentation',
     [u'Tim Spurway'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Hustle', u'Hustle Documentation',
   u'Tim Spurway', 'Hustle', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}
autodoc_member_order = 'bysource'
########NEW FILE########
__FILENAME__ = cardinality
from hustle.core.marble import Aggregation


def h_cardinality(col):
    """
    """
    def _inner_deault():
        from cardunion import Cardunion
        return Cardunion(12)

    def _inner_hll_accumulate(a, v):
        a.bunion([v])
        return a

    return Aggregation("cardinality",
                       col,
                       f=_inner_hll_accumulate,
                       g=lambda a: a.count(),
                       h=lambda a: a.dumps(),
                       default=_inner_deault,
                       is_numeric=True)


def h_union(col):
    def _inner_deault():
        from cardunion import Cardunion
        return Cardunion(12)

    def _inner_hll_accumulate(a, v):
        a.bunion([v])
        return a

    return Aggregation("union",
                       col,
                       f=_inner_hll_accumulate,
                       g=lambda a, c: a.dumps(),
                       h=lambda a: a.dumps(),
                       default=_inner_deault)


def h_minhash_merge(col):
    def _inner_deault():
        from maxhash import MaxHash
        return MaxHash()

    def _inner_hll_accumulate(a, v):
        from maxhash import MaxHash
        a.merge(MaxHash.loads(v))
        return a

    return Aggregation("minhash_merge",
                       col,
                       f=_inner_hll_accumulate,
                       g=lambda a, c: a.dumps(),
                       h=lambda a: a.dumps(),
                       default=_inner_deault)

########NEW FILE########
__FILENAME__ = marble
"""
:mod:`hustle.core.marble` -- The Hustle Database Core
=====================================================


"""
from collections import defaultdict
from functools import partial
from pyebset import BitSet

import clz4
import mdb
import os
import rtrie
import tempfile
import time
import ujson
import sys


class Marble(object):
    """
    The Marble is the smallest unit of distribution and replication in Hustle.  The Marble is a wrapper around a
    standalone `LMDB <http://symas.com/mdb/>`_ key/value store.  An *LMDB* key/value store may have many sub key/value
    stores, which are called DBs in LMDB terminology.  Each Hustle column is represented by one LMDB DB (called the column
    DB), plus another LMDB DB if that column is indexed (called the index DB) (see :ref:`schemadesign`).

    The Marble file is also the unit of insertion and replication of data into the Hustle system.  Marbles can be built
    on remote systems, in a completely distributed manner.  They are then *pushed* into the cluster's DDFS file system,
    which is a relatively inexpensive operation.  This is Hustle's :ref:`distributed insert functionality <insertguide>`.

    In addition each Marble contains several LMDB meta DBs for meta-data for prefix Tries, schema, and table statistics
    used by the query optimizer.

    The column DB is a key/value store that stores data for a particular column.  It has a locally unique row identifier (RID) as
    the key, and the actual value for that column's data as its value, encoded depending on the schema data type of
    the column.  All integer types are directly encoded in LMDB as integers, whereas the Trie compression types are encoded
    as integers (called VIDs), which actually are keys in the two dedicated Trie meta DBs (one for 32 and one for 16
    bit Tries).  Uncompressed strings, as well as lz4 and binary style data is simply encoded as byte string values.

    The index DB for a column is a key/value store that inverts the key and the value of the column DB.  It is used to
    perform the identity and range queries required form Hustle's *where clause*.  The key in the index DB is the
    actual value for that column, but the value is a *bitmap index* of the RIDs where that value is present.  This is
    a very efficient and compact way to store the index in an append-only database like Hustle.

    :type name: basestring
    :param name: the name of the *Marble* to create

    :type fields: sequence of string
    :param name: the schema specification of the columns (see :ref:`Hustle Schema Guide <schemadesign>`

    :type partition: basestring
    :param partition: the column that will serve as the partition for this *Marble*
    """
    def __init__(self, name=None, fields=(), partition=None):
        self._name = name
        self._fields = fields
        self._partition = partition
        self._columns = {}

        for field in fields:
            field, type_indicator, compression_indicator, rtrie_indicator, \
                index_indicator, boolean = self._parse_index_type(field)
            part = field == partition
            col = Column(field,
                         self,
                         index_indicator=index_indicator,
                         partition=part,
                         type_indicator=type_indicator,
                         compression_indicator=compression_indicator,
                         rtrie_indicator=rtrie_indicator,
                         boolean=boolean)
            self._columns[field] = col
            self.__dict__[field] = col

    @property
    def _field_names(self):
        return [self._parse_index_type(field)[0] for field in self._fields]

    @classmethod
    def _parse_index_type(cls, ix):
        """
        We have 9 possible types represented by the type_indicator:
        MDB_STR = 0
        MDB_INT_32 = 1
        MDB_UINT_32 = 2
        MDB_INT_16 = 3
        MDB_UINT_16 = 4
        MDB_INT_8 = 5
        MDB_UINT_8 = 6
        MDB_INT_64 = 7
        MDB_UINT_64 = 8

        The compression_indicator - used only for MDB_STR type_indicators:
        0 - rtrie compression
        1 - no compression
        2 - LZ4 compression
        3 - BINARY

        The rtrie_indicator - used only for 0 (rtrie) compression_indicators:
        MDB_UINT_32 - 32 bit VID
        MDB_UINT_16 - 16 bit VID

        The boolean - used to indicate that this field is a boolean type
        """
        type_indicator = mdb.MDB_STR
        compression_indicator = 0
        rtrie_indicator = mdb.MDB_UINT_32
        index_indicator = 0
        boolean = False

        nx = ix
        while True:
            if len(ix) > 1 and ix[0] < 'a':
                ind = ix[0]
                nx = ix[1:]
                if ind == '#':
                    type_indicator = mdb.MDB_INT_32
                    if ix[1] == '2':
                        type_indicator = mdb.MDB_INT_16
                        nx = ix[2:]
                    elif ix[1] == '4':
                        nx = ix[2:]
                    elif ix[1] == '1':
                        type_indicator = mdb.MDB_INT_8
                        nx = ix[2:]
                    elif ix[1] == '8':
                        type_indicator = mdb.MDB_INT_64
                        nx = ix[2:]
                elif ind == '@':
                    type_indicator = mdb.MDB_UINT_32
                    if ix[1] == '2':
                        type_indicator = mdb.MDB_UINT_16
                        nx = ix[2:]
                    elif ix[1] == '4':
                        nx = ix[2:]
                    elif ix[1] == '1':
                        type_indicator = mdb.MDB_UINT_8
                        nx = ix[2:]
                    elif ix[1] == '8':
                        type_indicator = mdb.MDB_UINT_64
                        nx = ix[2:]
                elif ind == '%':
                    if ix[1] == '2':
                        rtrie_indicator = mdb.MDB_UINT_16
                        nx = ix[2:]
                    if ix[1] == '4':
                        nx = ix[2:]
                elif ind == '!':
                    boolean = True
                elif ind == '$':
                    compression_indicator = 1
                elif ind == '*':
                    compression_indicator = 2
                elif ind == '&':
                    compression_indicator = 3
                elif ind == '+':
                    index_indicator = 1
                    ix = nx
                    continue
                elif ind == '=':
                    index_indicator = 2
                    ix = nx
                    continue
            break
        return nx, type_indicator, compression_indicator, rtrie_indicator, index_indicator, boolean

    @classmethod
    def from_file(cls, filename):
        """
        Instantiate a :class:`Marble <hustle.core.marble.Marble>` from an *LMDB*
        """
        env, txn, db = mdb.mdb_read_handle(filename, '_meta_', False,
                                           False, False,
                                           mdb.MDB_NOSUBDIR | mdb.MDB_NOLOCK)
        try:
            vals = {k: ujson.loads(v) for k, v in db.items(txn) if not k.startswith('_')}
            return cls(**vals)
        finally:
            txn.commit()
            env.close()

    @classmethod
    def _open_env(cls, filename, maxsize, write):
        # Always open env without locking, since readers and writers never show up
        # togerther.
        if write:
            oflags = mdb.MDB_WRITEMAP | mdb.MDB_NOLOCK
        else:
            oflags = mdb.MDB_RDONLY | mdb.MDB_NOLOCK

        retry = 0
        while retry <= 11:
            try:
                env = mdb.Env(filename,
                              max_dbs=1024,
                              mapsize=maxsize,
                              flags=oflags | mdb.MDB_NORDAHEAD | mdb.MDB_NOSYNC | mdb.MDB_NOSUBDIR)
            except Exception as e:
                print "Error: %s" % e
                retry += 1
                time.sleep(5)
            else:
                return env
        raise SystemError("Failed to open MDB env.")

    def _open(self, filename, maxsize=100 * 1024 * 1024, write=False, lru_size=10000):
        env = self._open_env(filename, maxsize, write)
        env, txn, dbs, meta = self._open_dbs(env, write, lru_size)
        if not write:
            partition = ujson.loads(meta.get(txn, 'partition', 'null'))
            if partition:
                pdata = ujson.loads(meta.get(txn, '_pdata', 'null'))
                if pdata is None:
                    raise ValueError("Can't load partition information from meta table.")
                db, _, _, _, _ = dbs[partition]
                db.echome = pdata
        return env, txn, dbs, meta

    def _open_dbs(self, env, write, lru_size):
        from pylru import LRUDict
        from itertools import repeat

        class PartitionDB(object):
            '''
            A fake mdb-like class just for partition columns.
            '''
            def __init__(self, partition, total):
                self.echome = partition
                self.total = total

            def put(self, txn, row_id, val):
                return

            def mgetex(self, txn, keys, default=None):
                '''keys should be a bitmap
                '''
                for i in range(len(keys)):
                    yield self.echome

            def get_neighbours(self, txn, key):
                return (key, self.echome), (self.total + 1, self.echome)

            def get(self, txn, key, default=None):
                return self.echome

            def close(self):
                return

        class CountDB(object):
            def __init__(self, total):
                self.total = total

            def close(self):
                pass

            def put(self, txn, key, val):
                pass

            def get(self, _, rid, default=None):
                return 1

            def mgetex(self, _, rids, default=None):
                return repeat(1, len(rids))

            def get_neighbours(self, _, rid, default=None):
                return (rid, 1), (self.total + 1, 1)

        class BooleanDB(object):
            def __init__(self, subindexdb, txn):
                bitset = BitSet()
                try:
                    data = subindexdb.get(txn, 1)
                    bitset.loads(data)
                except:
                    pass
                self.true_bm = bitset

            def close(self):
                pass

            def put(self, txn, key, val):
                pass

            def get(self, _, rid, default=None):
                if rid in self.true_bm:
                    return 1
                else:
                    return 0

            def get_neighbours(self, _, rid, default=None):
                if rid in self.true_bm:
                    return (rid, 1), (rid, 1)
                else:
                    return (rid, 0), (rid, 0)

            def mgetex(self, _, rids, default=None):
                for rid in rids:
                    if rid in self.true_bm:
                        yield 1
                    else:
                        yield 0

        class BooleanIX(object):
            def __init__(self, subindexdb, txn, number_rows):
                self.subindexdb = subindexdb
                self.txn = txn
                self.number_rows = number_rows

            def close(self):
                self.subindexdb.close()

            def put(self, txn, key, val):
                if key == 1:
                    self.subindexdb.put(self.txn, key, val)

            def stat(self, txn):
                return {'ms_entries': 2}

            def get(self, txn, key, default=None):
                bm = self.subindexdb.get(self.txn, 1)
                if key == 1:
                    return bm

                bitmap = BitSet()
                bitmap.loads(bm)
                bitmap |= ZERO_BS
                bitmap.set(self.number_rows)
                bitmap.lnot_inplace()
                return bitmap.dumps()

        if write:
            txn = env.begin_txn()
        else:
            txn = env.begin_txn(flags=mdb.MDB_RDONLY)

        meta = env.open_db(txn, name='_meta_', flags=mdb.MDB_CREATE)
        number_rows = ujson.loads(meta.get(txn, '_total_rows', "0"))

        if not write:
            dbs = {'_count': (CountDB(number_rows), None, None,
                              Column('_count', None, type_indicator=1), None)}
        else:
            dbs = {}
        for index, column in self._columns.iteritems():
            subindexdb = None
            bitmap_dict = _dummy
            last = None  # to record the last inserted value
            if column.index_indicator:
                # create an index for this column
                flags = mdb.MDB_CREATE
                if column.is_int:
                    flags |= mdb.MDB_INTEGERKEY
                subindexdb = env.open_db(txn,
                                         name="ix:%s" % index,
                                         flags=flags,
                                         key_inttype=column.get_effective_inttype())

                if column.is_boolean:
                    subindexdb = BooleanIX(subindexdb, txn, number_rows)

                if write:
                    if column.index_indicator == 2:
                        evict = Victor(mdb_evict, txn, subindexdb)
                        fetch = Victor(mdb_fetch, txn, subindexdb)
                        bitmap_dict = LRUDict.getDict(lru_size,
                                                      fetch,
                                                      evict,
                                                      column.is_int,
                                                      BitSet)
                    else:
                        bitmap_dict = defaultdict(BitSet)

            if column.is_boolean:
                subdb = BooleanDB(subindexdb, txn)
            elif column.partition:
                subdb = PartitionDB(column.name, number_rows)
            else:
                flags = mdb.MDB_CREATE | mdb.MDB_INTEGERKEY
                if column.is_int:
                    flags |= mdb.MDB_INTEGERDUP
                subdb = env.open_db(txn,
                                    name=index,
                                    flags=flags,
                                    key_inttype=mdb.MDB_UINT_32,
                                    value_inttype=column.get_effective_inttype())

            dbs[index] = (subdb, subindexdb, bitmap_dict, column, last)
        return env, txn, dbs, meta

    def _insert(self, streams, preprocess=None, maxsize=1024 * 1024 * 1024,
                tmpdir='/tmp', decoder=None, lru_size=10000, header=False,
                verbose=True, partition_filter=None):
        """insert a file into the hustle table."""
        from wtrie import Trie
        from collections import Iterable

        COMMIT_THRESHOLD = 50000

        if not decoder:
            decoder = json_decoder

        partitions = {}
        counters = {}
        autoincs = {}
        vid_tries = {}
        vid16_tries = {}
        page_size = 4096
        pdata, pfilter = None, None
        err = 0
        if partition_filter is not None:
            if isinstance(partition_filter, Iterable) \
                    and not isinstance(partition_filter, (basestring, unicode)):
                pfilter = set(partition_filter)
            else:
                pfilter = set()
                pfilter.add(partition_filter)

        try:
            for stream in streams:
                if header:
                    # skip the first line
                    stream.next()

                for line in stream:
                    # print "Line: %s" % line
                    try:
                        data = decoder(line)
                        if preprocess:
                            preprocess(data)
                    except Exception as e:
                        if verbose:
                            print "Exception decoding/preprocessing record (skipping): %s %s" % (e, line)
                        else:
                            print ". ",
                            err += 1
                            if err % 100 == 0:
                                print err,
                                sys.stdout.flush()
                        continue

                    newpdata = str(data.get(self._partition, ''))
                    if partition_filter is not None and newpdata not in pfilter:
                        continue

                    if pdata != newpdata:
                        pdata = newpdata
                        if pdata in partitions:
                            bigfile, env, txn, dbs, meta, pmaxsize = partitions[pdata]
                        else:
                            bigfile = tempfile.mktemp(prefix="hustle", dir=tmpdir) + '.big'
                            env, txn, dbs, meta = self._open(bigfile, maxsize=maxsize,
                                                             write=True, lru_size=lru_size)
                            page_size = env.stat()['ms_psize']
                            partitions[pdata] = bigfile, env, txn, dbs, meta, maxsize
                            counters[pdata] = 0
                            autoincs[pdata] = 1
                            vid_tries[pdata] = Trie()
                            vid16_tries[pdata] = Trie()
                            pmaxsize = maxsize

                    if counters[pdata] >= COMMIT_THRESHOLD:
                        txn.commit()
                        total_pages = pmaxsize / page_size
                        last_page = env.info()['me_last_pgno']
                        pages_left = total_pages - last_page
                        highwatermark = int(0.75 * total_pages)
                        if pages_left < highwatermark:
                            pmaxsize = int(pmaxsize * 1.5)
                            try:
                                print "======= attempting to resize mmap ======"
                                env.set_mapsize(pmaxsize)
                                env, txn, dbs, meta = self._open_dbs(env,
                                                                     write=True,
                                                                     lru_size=lru_size)
                            except Exception as e:
                                import traceback
                                print "Error resizing MDB: %s" % e
                                print traceback.format_exc(15)
                                return 0, None
                        else:
                            txn = env.begin_txn()
                        #TODO: a bit a hack - need to reset txns and dbs for all of our indexes
                        #  (iff they are LRUDicts)
                        for index, (_, subindexdb, bitmap_dict, _, _) in dbs.iteritems():
                            if bitmap_dict is not _dummy and type(bitmap_dict) is not defaultdict:
                                lru_evict = bitmap_dict._Evict
                                lru_fetch = bitmap_dict._Fetch
                                lru_evict.txn = lru_fetch.txn = txn
                                lru_evict.db = lru_fetch.db = subindexdb
                        partitions[pdata] = bigfile, env, txn, dbs, meta, pmaxsize
                        counters[pdata] = 0

                    updated_dbs = _insert_row(data, txn, dbs, autoincs[pdata],
                                              vid_tries[pdata], vid16_tries[pdata])
                    autoincs[pdata] += 1
                    counters[pdata] += 1
                    if updated_dbs:
                        partitions[pdata] = bigfile, env, txn, updated_dbs, meta, pmaxsize

            files = {}
            total_records = 0
            for pdata, (bigfile, env, txn, dbs, meta, pmaxsize) in partitions.iteritems():
                try:
                    meta.put(txn, '_total_rows', str(autoincs[pdata]))
                    total_records += autoincs[pdata] - 1
                    vid_nodes, vid_kids, _ = vid_tries[pdata].serialize()
                    vid16_nodes, vid16_kids, _ = vid16_tries[pdata].serialize()
                    vn_ptr, vn_len = vid_nodes.buffer_info()
                    vk_ptr, vk_len = vid_kids.buffer_info()
                    vn16_ptr, vn16_len = vid16_nodes.buffer_info()
                    vk16_ptr, vk16_len = vid16_kids.buffer_info()
                    meta.put_raw(txn, '_vid_nodes', vn_ptr, vn_len)
                    meta.put_raw(txn, '_vid_kids', vk_ptr, vk_len)
                    meta.put_raw(txn, '_vid16_nodes', vn16_ptr, vn16_len)
                    meta.put_raw(txn, '_vid16_kids', vk16_ptr, vk16_len)
                    meta.put(txn, 'name', ujson.dumps(self._name))
                    meta.put(txn, 'fields', ujson.dumps(self._fields))
                    meta.put(txn, 'partition', ujson.dumps(self._partition))
                    meta.put(txn, '_pdata', ujson.dumps(pdata))
                    for index, (subdb, subindexdb, bitmap_dict, column, last) in dbs.iteritems():
                        if subindexdb:
                            # process all values for this bitmap index
                            if column.index_indicator == 2:
                                bitmap_dict.evictAll()
                            else:
                                for val, bitmap in bitmap_dict.iteritems():
                                    subindexdb.put(txn, val, bitmap.dumps())
                        # insert a sentinel row to value table
                        subdb.put(txn, autoincs[pdata], last)
                    txn.commit()
                except Exception as e:
                    print "Error writing to MDB: %s" % e
                    txn.abort()
                    import traceback
                    trace = traceback.format_exc(15)
                    print trace
                    return 0, None
                else:
                    # close dbs
                    meta.close()
                    for index, (subdb, subindexdb, _, _, _) in dbs.iteritems():
                        subdb.close()
                        if subindexdb:
                            subindexdb.close()
                    try:
                        outfile = bigfile[:-4]  # drop the '.big'
                        env.copy(outfile)
                        files[pdata] = outfile
                    except Exception as e:
                        print "Copy error: %s" % e
                        raise e
                env.close()
            return total_records, files
        finally:
            for _, (bigfile, _, _, _, _, _) in partitions.iteritems():
                os.unlink(bigfile)


class MarbleStream(object):
    def __init__(self, local_file):
        import socket
        self.marble = Marble.from_file(local_file)
        self.env, self.txn, self.dbs, self.meta = self.marble._open(local_file, write=False)
        self.number_rows = ujson.loads(self.meta.get(self.txn, '_total_rows'))
        self.vid_nodes, _ = self.meta.get_raw(self.txn, '_vid_nodes')
        self.vid_kids, _ = self.meta.get_raw(self.txn, '_vid_kids')
        self.vid16_nodes, _ = self.meta.get_raw(self.txn, '_vid16_nodes', (None, 0))
        self.vid16_kids, _ = self.meta.get_raw(self.txn, '_vid16_kids', (None, 0))
        self.partition = ujson.loads(self.meta.get(self.txn, 'partition', 'null'))
        self.pdata = ujson.loads(self.meta.get(self.txn, '_pdata', 'null'))
        self.host = socket.gethostname()

    def iter_all(self):
        return xrange(1, self.number_rows)

    def mget(self, column_name, keys):
        db, _, _, column, _ = self.dbs[column_name]
        for data in db.mgetex(self.txn, keys):
            yield column.fetcher(data, self.vid16_nodes, self.vid16_kids,
                                 self.vid_nodes, self.vid_kids)

    def get(self, column_name, key):
        """
        In hustle, value table stores data in an Ajacent-Duplicates-Compressing
        fashion. Also, each table has a sentinel as the last value so that
        we don't check the case that key doesn't exist in this function.
        """
        db, _, _, column, _ = self.dbs[column_name]
        lower, _ = db.get_neighbours(self.txn, key)
        return column.fetcher(lower[1], self.vid16_nodes, self.vid16_kids,
                              self.vid_nodes, self.vid_kids)

    def _vid_for_value(self, column, key):
        if column.is_trie:
            if column.rtrie_indicator == mdb.MDB_UINT_16:
                key = rtrie.vid_for_value(self.vid16_nodes, self.vid16_kids, key)
            else:
                key = rtrie.vid_for_value(self.vid_nodes, self.vid_kids, key)
        elif column.is_lz4:
            key = clz4.compress(key)
        return key

    def bit_eq(self, ix, key):
        _, idb, _, column, _ = self.dbs[ix]
        rval = BitSet()
        zkey = self._vid_for_value(column, key)
        if zkey is not None:
            val = idb.get(self.txn, zkey)
            if val is not None:
                rval.loads(val)
        return rval

    def bit_ne(self, ix, key):
        _, idb, _, column, _ = self.dbs[ix]
        rval = BitSet()
        key = self._vid_for_value(column, key)
        if key is not None:
            val = idb.get(self.txn, key)
            if val is not None:
                rval.loads(val)
                rval |= ZERO_BS
                rval.set(self.number_rows)
                rval.lnot_inplace()
        return rval

    def bit_eq_ex(self, ix, keys):
        from collections import Iterable
        _, idb, _, column, _ = self.dbs[ix]
        rval = BitSet()
        for key in keys:
            if isinstance(key, Iterable) and not isinstance(key, (basestring, unicode)):
                # in case the key is a composite object, just grab the first one
                key = key[0]
            zkey = self._vid_for_value(column, key)
            if zkey is not None:
                val = idb.get(self.txn, zkey)
                if val is not None:
                    bitset = BitSet()
                    bitset.loads(val)
                    rval |= bitset
        return rval

    def bit_ne_ex(self, ix, keys):
        from collections import Iterable
        _, idb, _, column, _ = self.dbs[ix]
        rval = BitSet()
        for key in keys:
            if isinstance(key, Iterable) and not isinstance(key, (basestring, unicode)):
                # in case the key is a composite object, just grab the first one
                key = key[0]
            zkey = self._vid_for_value(column, key)
            if zkey is not None:
                val = idb.get(self.txn, zkey)
                if val is not None:
                    bitset = BitSet()
                    bitset.loads(val)
                    rval |= bitset
        rval |= ZERO_BS
        rval.set(self.number_rows)
        rval.lnot_inplace()
        return rval

    def _bit_op(self, val, op):
        rval = BitSet()
        it = op(self.txn, val)
        for _, v in it:
            if v is None:
                continue
            bitset = BitSet()
            bitset.loads(v)
            rval |= bitset
        return rval

    def bit_lt(self, ix, val):
        _, idb, _, _, _ = self.dbs[ix]
        return self._bit_op(val, idb.get_lt)

    def bit_gt(self, ix, val):
        _, idb, _, _, _ = self.dbs[ix]
        return self._bit_op(val, idb.get_gt)

    def bit_le(self, ix, val):
        _, idb, _, _, _ = self.dbs[ix]
        return self._bit_op(val, idb.get_le)

    def bit_ge(self, ix, val):
        _, idb, _, _, _ = self.dbs[ix]
        return self._bit_op(val, idb.get_ge)

    def close(self):
        try:
            self.txn.commit()
            self.env.close()
        except:
            pass


class Column(object):
    """
    A *Column* is the named, typed field of a :class:`Marble <hustle.core.marble.Marble>`.   *Columns* are typically
    created automatically by parsing the *fields* of a the *Marble* instantiation.

    The *Column* overrides Python's relational operators :code:`> < <= >= ==` which forms the basis for
    the :ref:`Query DSL <queryguide>`.  All of these operators expect a *Python literal* as their second
    (right hand side) argument which should be the same type as the *Column*.  These *Column Expressions* are
    represented by the :class:`Expr <hustle.core.marble.Expr>` class.

    Note that the *Marble* and *Table* classes expose their *Columns* as Python *attributes*::

        # instantiate a table
        imps = Table.from_tag('impressions')

        # access a the date column
        date_column = imps.date

        # create a Column Expression
        site_column_expression = imps.site_id == 'google.com'

        # create another Column Expression
        date_column_expression = date_column > '2014-03-07'

        # query
        select(date_column, where=date_column_expression & )

    """
    def __init__(self, name, table=None, index_indicator=0, partition=False, type_indicator=0,
                 compression_indicator=0, rtrie_indicator=mdb.MDB_UINT_32, alias=None, boolean=False):
        self.name = name
        self.fullname = "%s.%s" % (table._name, name) if hasattr(table, '_name') else name
        self.table = table
        self.type_indicator = type_indicator if not boolean else mdb.MDB_UINT_8
        self.partition = partition
        self.index_indicator = index_indicator if not boolean else 1
        self.compression_indicator = compression_indicator
        self.rtrie_indicator = rtrie_indicator
        self.alias = alias
        self.is_boolean = boolean
        self.is_trie = self.type_indicator == mdb.MDB_STR and compression_indicator == 0
        self.is_lz4 = self.type_indicator == mdb.MDB_STR and compression_indicator == 2
        self.is_binary = self.type_indicator == mdb.MDB_STR and compression_indicator == 3
        self.is_int = self.type_indicator != mdb.MDB_STR or self.compression_indicator == 0
        self.is_numeric = self.type_indicator > 0
        self.is_index = self.index_indicator > 0
        self.is_wide = self.index_indicator == 2

        # use dictionary (trie) compression if required
        if self.is_trie:
            if self.rtrie_indicator == mdb.MDB_UINT_16:
                self.converter = _convert_vid16
                self.fetcher = _fetch_vid16
            else:
                self.converter = _convert_vid
                self.fetcher = _fetch_vid
            self.default_value = ''
        elif self.is_lz4:
            self.converter = _convert_lz4
            self.fetcher = _fetch_lz4
            self.default_value = ''
        elif self.is_int:
            self.converter = _convert_int
            self.fetcher = _fetch_me
            self.default_value = 0
        else:
            self.converter = _convert_str
            self.fetcher = _fetch_me
            self.default_value = ''

    def named(self, alias):
        """
        return a new column that has an alias that will be used in the resulting schema
        :type alias: str
        :param alias: the name of the alias
        """
        newcol = Column(self.name, self.table, self.index_indicator, self.partition,
                        self.type_indicator, self.compression_indicator,
                        self.rtrie_indicator, alias)
        return newcol

    @property
    def column(self):
        return self

    def schema_string(self):
        """
        return the schema for this column.  This is used to build the schema of a query
        result, so we need to use the alias.
        """
        rval = self.alias or self.name or ''
        indexes = ['', '+', '=']
        prefix = indexes[self.index_indicator]
        lookup = ['', '#4', '@4', '#2', '@2', '#1', '@1', '#8', '@8']

        if self.type_indicator == mdb.MDB_STR:
            if self.compression_indicator == 0:
                prefix += '%'
                if self.rtrie_indicator == mdb.MDB_UINT_32:
                    prefix += '4'
                elif self.rtrie_indicator == mdb.MDB_UINT_16:
                    prefix += '2'
            elif self.compression_indicator == 1:
                prefix += '$'
            elif self.compression_indicator == 2:
                prefix += '*'
            elif self.compression_indicator == 3:
                prefix += '&'
        elif self.is_binary:
            prefix = '!'
        else:
            prefix += lookup[self.type_indicator]
        return prefix + rval

    def description(self):
        """
        Return a human-readable type description for this column.
        """
        type_lookup = ['', 'int32', 'uint32', 'int16', 'uint16', 'int8',
                       'uint8', 'int64', 'uint64']
        dict_lookup = ['', '', '32', '', '16', '', '']
        string_lookup = ['trie', 'string', 'lz4', 'binary']
        index_lookup = ['', 'index', 'wide index']

        rval = type_lookup[self.type_indicator]
        if not self.type_indicator:
            rval += string_lookup[self.compression_indicator]
            if self.compression_indicator == 0:
                rval += dict_lookup[self.rtrie_indicator]
        name = self.alias or self.name if not self.partition \
            else "*" + (self.alias or self.name)
        inds = [rval, name]
        if self.is_boolean:
            inds = ['bit', name]
        elif self.index_indicator:
            inds.insert(0, index_lookup[self.index_indicator])
        return ' '.join(inds)

    def get_effective_inttype(self):
        if self.type_indicator == mdb.MDB_STR and self.compression_indicator == 0:
            return self.rtrie_indicator
        return self.type_indicator

    def _get_expr(self, op, part_op, other):
        if not self.partition \
                and op in [in_lt, in_gt, in_ge, in_le] \
                and (self.is_trie or self.is_lz4 or self.is_binary):
            raise TypeError("Column %s doesn't support range query."
                            % self.fullname)
        if not self.is_index:
            raise TypeError("Column %s is not an index, cannot appear in 'where' clause."
                            % self.fullname)
        part_expr = partial(part_op, other=other) if self.partition else part_all
        return Expr(self.table,
                    partial(op, col=self.name, other=other),
                    part_expr,
                    self.partition)

    def __lshift__(self, other):
        return self._get_expr(in_in, part_in, other=other)

    def __rshift__(self, other):
        return self._get_expr(in_not_in, part_not_in, other=other)

    def __eq__(self, other):
        return self._get_expr(in_eq, part_eq, other=other)

    def __ne__(self, other):
        return self._get_expr(in_ne, part_ne, other=other)

    def __lt__(self, other):
        return self._get_expr(in_lt, part_lt, other=other)

    def __gt__(self, other):
        return self._get_expr(in_gt, part_gt, other=other)

    def __ge__(self, other):
        return self._get_expr(in_ge, part_ge, other=other)

    def __le__(self, other):
        return self._get_expr(in_le, part_le, other=other)

    def __str__(self):
        return self.description()


def dflt_default():
    """
    Default 'default' function for aggregation, simply returns none
    """
    return None


def dflt_gh(a):
    """
    Default 'g/h' function for aggregation, simply returns accum
    """
    return a


def dflt_f(a, v):
    """
    Default 'f' function for aggregation, simply returns value and ignores accum
    """
    return v


class Aggregation(object):
    """
    An *Aggregation* is a Column Function that represents some aggregating computation over the values of that
    column.  It is exclusively used in the *project* section of the :func:`select() <hustle.select>` function.

    An *Aggregation* object holds onto four distinct function references which are called at specific times
    during the *group_by stage* of the query pipeline.

    :type f: func(accumulator, value)
    :param f: the function called for every value of the *column*, returns a new accumulator (the MAP aggregator)

    :type g: func(accumulator)
    :param g: the function called to produce the final value (the REDUCE aggregator)

    :type h: func(accumulator)
    :param h: the function called to produce intermediate values (the COMBINE aggregator)

    :type default: func()
    :param default:  the function called to produce the initial aggregation accumulator

    :type column: :class:`Column <hustle.core.marble.Column>`
    :param column: the column to aggregate

    :type name: basestring
    :param name: the unique name of the aggregator.  Used to assign a column name to the result

    .. note::

        Here is the actual implementation of the h_avg() *Aggregation* which will give us the average value
        for a numeric column in a :func:`select() <hustle.select>` statement::

            def h_avg(col):
                return Aggregation("avg",
                                   col,
                                   f=lambda (accum, count), val: (accum + val, count + 1),
                                   g=lambda (accum, count): float(accum) / count,
                                   h=lambda (accum, count): (accum, count),
                                   default=lambda: (0, 0))

        First look at the *default()* function which returns the tuple (0, 0).  This sets the *accum* and *count* values
        that we will be tracking both to zero.  Next, let's see what's happening in the *f()* function.  Note that it
        performs two computations, one :code:`accum + val` builds a sum of the values, and the :code:`count + 1` will
        count the total number of values.  The difference between the *g()* and *h()* functions is when they take place.
        The *h()* function is used to summarize results.  It should always return an *accum* that can be further
        inputted into the *f()* function.  The *g()* function is used at the very end of the computation to compute the
        final value to return the client.

        Note that most aggreations are much simpler than :func:`h_avg() <hustle.h_avg>`.  Consider the implementation
        for :func:`h_sum() <hustle.h_sum>`::

            def h_sum(col):
                return Aggregation("sum",
                                   col,
                                   f=lambda accum, val: accum + val
                                   default=0)

        We don't have to implement the :code:`h() or g()` functions, as they simply default to funcitons that
        return the :code:`accum`, which is normally sufficient.

    .. seealso::
        :func:`h_sum() <hustle.h_sum>`, :func:`h_count() <hustle.h_count>`, :func:`h_avg() <hustle.h_avg>`
            Some of Hustle's aggregation functions

    """
    def __init__(self, name, column, f=None, g=dflt_gh, h=dflt_gh,
                 default=dflt_default, result_spec=None):

        self.column = column
        self.f = f
        self.g = g
        self.h = h
        self.default = default
        self.name = "%s(%s)" % (name, column.name if column else '')
        self.fullname = "%s(%s)" % (name, column.fullname if column else '')
        self.result_spec = result_spec

        self.is_numeric = column.is_numeric if column else False
        self.is_binary = column.is_binary if column else False

    @property
    def table(self):
        return self.column.table

    def named(self, alias):
        newag = Aggregation(self.name, self.column.named(alias), self.f,
                            self.g, self.h, self.default)
        return newag

    def schema_string(self):
        """
        return the schema for this aggregation.  override this by setting the :code:`result_spec`
        """
        if self.result_spec:
            return self.result_spec.schema_string()
        else:
            return self.column.schema_string()


class Expr(object):
    """
    The *Expr* is returned by the overloaded relational operators of the :class:`Column <hustle.core.marble.Column>`
    class.

    The *Expr* is a recursive class, that can be composed of other *Exprs* all connected with the logical
    :code:`& | ~` operators (*and, or, not*).

    Each *Expr* instance must be aware if its sub-expressions *have* partitions or *are* partitions.  This is to
    because the *&* and *|* operators will optimize expressions over patitioned columns differently.  Consider the
    following query::

        select(impressions.site_id, where=(impressions.date == '2014-02-20') & (impressions.amount > 10))

    Let's assume that the *impressions.date* column is a partition column.  It should be clear that we can optimize
    this query by only executing the query on the '2014-02-20' partition, which if we had many dates would vastly
    improve our query execution.

    On the other hand consider the following, almost identical query::

        select(impressions.site_id, where=(impressions.date == '2014-02-20') | (impressions.amount > 10))

    In this case, we cannot optimize according to our partition.  We need to visit *all* partitions in *impressions*
    and execute the *OR* operation across those rows for the *amount* expression.

    .. note::

        It is important to realize that all Column Expressions in an Expr must refer to the same *Table*

    :type table: :class:`Table <hustle.Table>`
    :param table: the *Table* this *Expr* queries

    :type f: func(MarbleStream)
    :param f: the function to execute to actually perform the expression on data in the *Marble*

    :type part_f: func(list of strings)
    :param part_f: the function to execute to perform the expresson on data in the *partition*

    :type is_partition: bool
    :param is_partition: indicates if this Expr only has partition columns

    """
    def __init__(self, table, f=None, part_f=None, is_partition=False):
        if not part_f:
            part_f = part_all
        self.table = table
        self.f = f
        self.part_f = part_f
        self.is_partition = is_partition

    @property
    def _name(self):
        return self.table._name

    @property
    def has_partition(self):
        return self.part_f != part_all

    @property
    def has_no_partition(self):
        return not self.has_partition

    def _assert_unity(self, other_expr):
        if self.table is not None and other_expr.table is not None \
                and self.table._name != other_expr.table._name:
            raise Exception("Error Expression must have a single table: %s != %s" %
                            (self.table._name, other_expr.table._name))

    def __and__(self, other_expr):
        self._assert_unity(other_expr)

        # p & p
        if self.is_partition and other_expr.is_partition:
            return Expr(self.table,
                        None,
                        partial(part_conditional, op='and', l_expr=self.part_f,
                                r_expr=other_expr.part_f),
                        True)
        # n & n
        elif self.has_no_partition and other_expr.has_no_partition:
            return Expr(self.table,
                        partial(in_conditional, op='and', l_expr=self.f,
                                r_expr=other_expr.f),
                        part_all)
        # n & p
        elif (self.is_partition and other_expr.has_no_partition) \
                or (self.has_no_partition and other_expr.is_partition):
            if self.is_partition:
                f_expr = other_expr.f
                pf_expr = self.part_f
            else:
                f_expr = self.f
                pf_expr = other_expr.part_f
            return Expr(self.table, f_expr, pf_expr)
        # n & np
        elif (self.has_no_partition and other_expr.has_partition) \
                or (self.has_partition and other_expr.has_no_partition):
            if self.has_partition:
                pf_expr = self.part_f
            else:
                pf_expr = other_expr.part_f
            return Expr(self.table,
                        partial(in_conditional, op='and', l_expr=self.f,
                                r_expr=other_expr.f),
                        pf_expr)
        # p & np
        elif (self.is_partition and other_expr.has_partition) \
                or (self.has_partition and other_expr.is_partition):
            if self.is_partition:
                f_expr = other_expr.f
            else:
                f_expr = self.f
            return Expr(self.table,
                        f_expr,
                        partial(part_conditional, op='and', l_expr=self.part_f,
                                r_expr=other_expr.part_f))
        # np & np
        elif self.has_partition and other_expr.has_partition:
            return Expr(self.table,
                        partial(in_conditional, op='and', l_expr=self.f,
                                r_expr=other_expr.f),
                        partial(part_conditional, op='and', l_expr=self.part_f,
                                r_expr=other_expr.part_f))
        else:
            raise Exception("Error in partitions (and)")

    def __or__(self, other_expr):
        self._assert_unity(other_expr)

        # p | p
        if self.is_partition and other_expr.is_partition:
            return Expr(self.table,
                        partial(in_conditional, op='or', l_expr=self.f,
                                r_expr=other_expr.f),
                        partial(part_conditional, op='or', l_expr=self.part_f,
                                r_expr=other_expr.part_f),
                        True)
        # p | np
        elif (self.is_partition and other_expr.has_partition) \
                or (self.has_partition and other_expr.is_partition):
            if self.is_partition:
                f_expr = other_expr.f
            else:
                f_expr = self.f
            return Expr(self.table,
                        f_expr,
                        partial(part_conditional, op='or', l_expr=self.part_f,
                                r_expr=other_expr.part_f))
        # np | np
        elif self.has_partition and other_expr.has_partition:
            return Expr(self.table,
                        partial(in_conditional, op='or', l_expr=self.f,
                                r_expr=other_expr.f),
                        partial(part_conditional, op='or', l_expr=self.part_f,
                                r_expr=other_expr.part_f))
        # n | n, n | p, n | np
        elif self.has_no_partition or other_expr.has_no_partition:
            return Expr(self.table,
                        partial(in_conditional, op='or', l_expr=self.f,
                                r_expr=other_expr.f),
                        part_all)
        else:
            raise Exception("Error in partitions (or)")

    def __invert__(self):
        # invert partition function only if it's not part_all
        if self.has_partition:
            return Expr(self.table,
                        partial(in_not, expr=self.f),
                        partial(in_not, expr=self.part_f),
                        self.is_partition)
        else:
            return Expr(self.table,
                        partial(in_not, expr=self.f),
                        self.part_f,
                        self.is_partition)

    def __call__(self, tablet, invert=False):
        return self.f(tablet, invert)

    def partition(self, tags, invert=False):
        return self.part_f(tags, invert)


def _convert_vid16(val, vid_trie=None, vid_trie16=None):
    try:
        val = str(val)
    except:
        val = val.encode('utf-8')

    return vid_trie16.add(val)


def _convert_vid(val, vid_trie=None, vid_trie16=None):
    try:
        val = str(val)
    except:
        val = val.encode('utf-8')
    return vid_trie.add(val)


def _convert_int(val, vid_trie=None, vid_trie16=None):
    if type(val) is int or type(val) is long:
        return val
    return int(val)


def _convert_str(val, vid_trie=None, vid_trie16=None):
    try:
        val = str(val)
    except:
        val = val.encode('utf-8')
    return val


def _convert_lz4(val, vid_trie=None, vid_trie16=None):
    try:
        val = str(val)
    except:
        val = val.encode('utf-8')
    return clz4.compress(val)


def _fetch_vid16(vid, vid16_nodes, vid16_kids, vid_nodes, vid_kids):
    return rtrie.value_for_vid(vid16_nodes, vid16_kids, vid)


def _fetch_vid(vid, vid16_nodes, vid16_kids, vid_nodes, vid_kids):
    return rtrie.value_for_vid(vid_nodes, vid_kids, vid)


def _fetch_lz4(data, vid16_nodes, vid16_kids, vid_nodes, vid_kids):
    return clz4.decompress(data)


def _fetch_me(data, vid16_nodes, vid16_kids, vid_nodes, vid_kids):
    return data


def in_not(obj, invert, expr):
    if expr is None:
        return BitSet()
    return expr(obj, not invert)


def part_all(tags, invert=False):
    if invert:
        return []
    return tags


def part_conditional(obj, invert, op, l_expr, r_expr):
    if (op == 'and' and not invert) or (op == 'or' and invert):
        # and
        l_set = set(l_expr(obj, invert))
        for uid in r_expr(obj, invert):
            if uid in l_set:
                yield uid
    else:
        # or
        l_set = set(l_expr(obj, invert))
        for uid in l_set:
            yield uid
        for uid in r_expr(obj, invert):
            if uid not in l_set:
                yield uid


def in_conditional(tablet, invert, op, l_expr, r_expr):
    if (op == 'and' and not invert) or (op == 'or' and invert):
        # and
        if l_expr is None:
            return r_expr(tablet, invert)
        elif r_expr is None:
            return l_expr(tablet, invert)
        return l_expr(tablet, invert) & r_expr(tablet, invert)
    else:
        # or
        if l_expr is None or r_expr is None:
            return None
        return l_expr(tablet, invert) | r_expr(tablet, invert)


def in_in(tablet, invert, col, other):
    from collections import Iterable
    if isinstance(other, Iterable) \
            and not isinstance(other, (basestring, unicode)):
        other = set(other)
        if invert:
            return tablet.bit_ne_ex(col, other)
        return tablet.bit_eq_ex(col, other)
    else:
        raise ValueError("Item in contains must be an iterable.")


def part_in(tags, invert, other):
    from collections import Iterable
    if isinstance(other, Iterable) \
            and not isinstance(other, (basestring, unicode)):
        other = set(other)
        if invert:
            return part_not_in(tags, False, other)
        return (t for t in tags if t in other)
    else:
        raise ValueError("Item in contains must be an iterable.")


def in_not_in(tablet, invert, col, other):
    from collections import Iterable
    if isinstance(other, Iterable) \
            and not isinstance(other, (basestring, unicode)):
        other = set(other)
        if invert:
            return tablet.bit_eq_ex(col, other)
        return tablet.bit_ne_ex(col, other)
    else:
        raise ValueError("Item in contains must be an iterable.")


def part_not_in(tags, invert, other):
    from collections import Iterable
    if isinstance(other, Iterable) \
            and not isinstance(other, (basestring, unicode)):
        other = set(other)
        if invert:
            return part_in(tags, False, other)
        return (t for t in tags if t not in other)
    else:
        raise ValueError("Item in contains must be an iterable.")


def in_eq(tablet, invert, col, other):
    if invert:
        return tablet.bit_ne(col, other)
    return tablet.bit_eq(col, other)


def part_eq(tags, invert, other):
    if invert:
        return part_ne(tags, False, other)
    return (t for t in tags if t == other)


def in_ne(tablet, invert, col, other):
    if invert:
        return tablet.bit_eq(col, other)
    return tablet.bit_ne(col, other)


def part_ne(tags, invert, other):
    if invert:
        return part_eq(tags, False, other)
    return (t for t in tags if t != other)


def in_lt(tablet, invert, col, other):
    if invert:
        return tablet.bit_ge(col, other)
    return tablet.bit_lt(col, other)


def part_lt(tags, invert, other):
    if invert:
        return part_ge(tags, False, other)
    return (t for t in tags if t < other)


def in_gt(tablet, invert, col, other):
    if invert:
        return tablet.bit_le(col, other)
    return tablet.bit_gt(col, other)


def part_gt(tags, invert, other):
    if invert:
        return part_le(tags, False, other)
    return (t for t in tags if t > other)


def in_ge(tablet, invert, col, other):
    if invert:
        return tablet.bit_lt(col, other)
    return tablet.bit_ge(col, other)


def part_ge(tags, invert, other):
    if invert:
        return part_lt(tags, False, other)
    return (t for t in tags if t >= other)


def in_le(tablet, invert, col, other):
    if invert:
        return tablet.bit_gt(col, other)
    return tablet.bit_le(col, other)


def part_le(tags, invert, other):
    if invert:
        return part_gt(tags, False, other)
    return (t for t in tags if t <= other)


def check_query(select, join, order_by, limit, wheres):
    """Query checker for hustle."""

    if not len(wheres):
        raise ValueError("Where clause must have at least one table. where=%s"
                         % repr(wheres))

    tables = {}
    for where in wheres:
        if isinstance(where, Marble):
            table = where
        else:
            table = where.table
        if table._name in tables:
            raise ValueError("Table %s occurs twice in the where clause."
                             % where._name)
        tables[table._name] = table

    if len(select) == 0:
        raise ValueError("No items in the select clause.")

    selects = set()
    for i, c in enumerate(select):
        name = c.fullname
        if c.table and c.table._name not in tables:
            raise ValueError("Selected column %s is not from the given tables"
                             " in the where clauses." % name)
        if name in selects:
            raise ValueError("Duplicate column %s in the select list." % name)
        selects.add(name)
        selects.add(c.name)
        selects.add(i)

    if join:
        if len(tables) != 2:
            raise ValueError("Query with join takes exact two tables, %d given."
                             % len(tables))
        if len(join) != 2:
            raise ValueError("Join takes exact two columns, %d given."
                             % len(join))
        if join[0].table._name == join[1].table._name:
            raise ValueError("Join columns belong to a same table.")
        if join[0].type_indicator != join[1].type_indicator:
            raise ValueError("Join columns have different types.")
        for c in join:
            if c.table._name not in tables:
                name = '%s.%s' % (c.table._name, c.name)
                raise ValueError("Join column %s is not from the given tables"
                                 " in the where clauses." % name)

    if order_by:
        for c in order_by:
            name = c.fullname if isinstance(c, (Column, Aggregation)) else c
            if name not in selects:
                raise ValueError("Order_by column %s is not in the select list."
                                 % name)

    if limit is not None:
        if limit < 0:
            raise ValueError("Negtive number is not allowed in the limit.")

    return True


def mdb_fetch(key, txn=None, ixdb=None):
    from pyebset import BitSet
    try:
        bitmaps = ixdb.get(txn, key)
    except:
        bitmaps = None

    if bitmaps is not None:
        bitset = BitSet()
        bitset.loads(bitmaps)
        return bitset
    return None


def mdb_evict(key, bitset, txn=None, ixdb=None):
    ixdb.put(txn, key, bitset.dumps())


class DUMMY(object):
    tobj = None

    def __getitem__(self, item):
        return self.tobj

_dummy = DUMMY()
_dummy_bitmap = DUMMY()
_dummy.tobj = _dummy_bitmap

ZERO_BS = BitSet()
ZERO_BS.set(0)

setattr(_dummy_bitmap, 'set', (lambda k: k))
setattr(_dummy, 'get', lambda k: _dummy_bitmap)


def kv_decoder(line, kvs=()):
    key, value = line
    return dict(zip(kvs, key + value))


def json_decoder(line):
    return ujson.loads(line)


def csv_decoder(line, fieldnames, delimiter=','):
    return dict(zip(fieldnames, line.rstrip().split(delimiter)))


def fixed_width_decoder(line, indexes=((0, '_'),)):
    rval = {}
    s, field = indexes[0]
    for e, nextfield in indexes[1:]:
        if field != '_':
            val = line[s:e].strip()
            rval[field] = val
        s = e
        field = nextfield
    if field != '_':
        val = line[s:].strip()
        rval[field] = val
    return rval


class Victor(object):
    def __init__(self, fn, txn, db):
        self.fn = fn
        self.txn = txn
        self.db = db

    def __call__(self, *args):
        if len(args) > 1:
            return self.fn(args[0], args[1], txn=self.txn, ixdb=self.db)
        else:
            return self.fn(args[0], txn=self.txn, ixdb=self.db)


def _insert_row(data, txn, dbs, row_id, vid_trie, vid16_trie):
    column = None
    updated = False
    try:
        for col, (subdb, subinxdb, bitmap_dict, column, last) in dbs.iteritems():
            val = column.converter(data.get(column.name, column.default_value)
                                   or column.default_value, vid_trie, vid16_trie)
            if val != last:
                subdb.put(txn, row_id, val)
                updated = True
                dbs[col] = subdb, subinxdb, bitmap_dict, column, val
            bitmap_dict[val].set(row_id)
    except Exception as e:
        print "Can't INSERT: %s %s: %s" % (repr(data), column, e)

    if updated:
        return dbs
    else:
        return None

########NEW FILE########
__FILENAME__ = pipeline
from disco.core import Job
from disco.worker.task_io import task_input_stream
from functools import partial
from hustle.core.marble import Marble, Column, Aggregation,\
    dflt_f, dflt_gh, dflt_default
from hustle.core.pipeworker import HustleStage

import sys
import hustle
import hustle.core
import hustle.core.marble


SPLIT = "split"
GROUP_ALL = "group_all"
GROUP_LABEL = "group_label"
GROUP_LABEL_NODE = "group_node_label"
GROUP_NODE = "group_node"

_POOL = 'abcdefghijklmnopqrstuvwxyz0123456789'
# default number of partitions, users can set this in the settings.yaml
_NPART = 16


def hustle_output_stream(stream, partition, url, params, result_table):
    """
    A disco output stream for creating a Hustle :class:`hustle.Table` output from a stage.
    """
    class HustleOutputStream(object):
        def __init__(self, stream, url, params, **kwargs):
            import tempfile
            from wtrie import Trie

            self.result_table = result_table
            self.result_columns = result_table._field_names
            tmpdir = getattr(params, 'tmpdir', '/tmp')
            self.filename = tempfile.mktemp(prefix="hustle", dir=tmpdir)
            maxsize = getattr(params, 'maxsize', 100 * 1024 * 1024)
            self.env, self.txn, self.dbs, self.meta = \
                self.result_table._open(self.filename, maxsize, write=True,
                                        lru_size=10000)
            self.autoinc = 1
            self.url = url
            self.vid_trie = Trie()
            self.vid16_trie = Trie()

        def add(self, k, v):
            from hustle.core.marble import _insert_row
            data = dict(zip(self.result_columns, list(k) + list(v)))
            #print "BOZAK! adding %s %s %s" % (self.result_columns, k, v)
            updated_dbs = _insert_row(data, self.txn, self.dbs, self.autoinc,
                                      self.vid_trie, self.vid16_trie)
            if updated_dbs:
                self.dbs = updated_dbs
            self.autoinc += 1

        def close(self):
            import os
            import ujson

            self.meta.put(self.txn, '_total_rows', str(self.autoinc))
            vid_nodes, vid_kids, _ = self.vid_trie.serialize()
            vid16_nodes, vid16_kids, _ = self.vid16_trie.serialize()
            vn_ptr, vn_len = vid_nodes.buffer_info()
            vk_ptr, vk_len = vid_kids.buffer_info()
            vn16_ptr, vn16_len = vid16_nodes.buffer_info()
            vk16_ptr, vk16_len = vid16_kids.buffer_info()
            self.meta.put_raw(self.txn, '_vid_nodes', vn_ptr, vn_len)
            self.meta.put_raw(self.txn, '_vid_kids', vk_ptr, vk_len)
            self.meta.put_raw(self.txn, '_vid16_nodes', vn16_ptr, vn16_len)
            self.meta.put_raw(self.txn, '_vid16_kids', vk16_ptr, vk16_len)
            self.meta.put(self.txn, 'name', ujson.dumps(self.result_table._name))
            self.meta.put(self.txn, 'fields', ujson.dumps(self.result_table._fields))
            for index, (subdb, subindexdb, bitmap_dict, column, last) in self.dbs.iteritems():
                if subindexdb:
                    # process all values for this bitmap index
                    if column.index_indicator == 2:
                        bitmap_dict.evictAll()
                    else:
                        for val, bitmap in bitmap_dict.iteritems():
                            subindexdb.put(self.txn, val, bitmap.dumps())
                # insert a sentinel row to value table
                subdb.put(self.txn, self.autoinc + 1, last)
            self.txn.commit()

            try:
                self.env.copy(self.url)
                # print "Dumped result to %s" % self.url
            except Exception as e:
                print "Copy error: %s" % e
                self.txn.abort()
                raise e
            self.env.close()
            os.unlink(self.filename)

    return HustleOutputStream(stream, url, params)


def hustle_input_stream(fd, size, url, params, wheres, gen_where_index, key_names):
    from disco import util
    from hustle.core.marble import Expr, MarbleStream
    from itertools import izip, repeat
    empty = ()

    try:
        scheme, netloc, rest = util.urlsplit(url)
    except Exception as e:
        print "Error handling hustle_input_stream for %s. %s" % (url, e)
        raise e

    fle = util.localize(rest, disco_data=params._task.disco_data,
                        ddfs_data=params._task.ddfs_data)
    # print "FLOGLE: %s %s" % (url, fle)

    otab = None
    try:
        # import sys
        # sys.path.append('/Library/Python/2.7/site-packages/pycharm-debug.egg')
        # import pydevd
        # pydevd.settrace('localhost', port=12999, stdoutToServer=True, stderrToServer=True)
        otab = MarbleStream(fle)
        bitmaps = {}

        for index, where in enumerate(wheres):
            # do not process where clauses that have nothing to do with this marble
            if where._name == otab.marble._name:
                if type(where) is Expr and not where.is_partition:
                    bm = where(otab)
                    bitmaps[index] = (bm, len(bm))
                else:
                    # it is either the table itself, or a partition expression.
                    # Either way, returns the entire table
                    bitmaps[index] = (otab.iter_all(), otab.number_rows)

        for index, (bitmap, blen) in bitmaps.iteritems():
            prefix_gen = [repeat(index, blen)] if gen_where_index else []

            row_iter = prefix_gen + \
                [otab.mget(col, bitmap) if col is not None else repeat(None, blen)
                 for col in key_names[index]]

            for row in izip(*row_iter):
                yield row, empty
    finally:
        if otab:
            otab.close()


class SelectPipe(Job):
    # profile = True
    required_modules = [
        ('hustle', hustle.__file__),
        ('hustle.core', hustle.core.__file__),
        ('hustle.core.pipeline', __file__),
        ('hustle.core.marble', hustle.core.marble.__file__)]

    def get_result_schema(self, project):
        import random
        from hustle import Table

        if self.output_table:
            return self.output_table
        fields = []
        for col_or_agg in project:
            col_spec = col_or_agg.schema_string()
            if col_spec not in fields:
                fields.append(col_spec)
        name = '-'.join([w._name for w in self.wheres])[:64]
        # append a 3-charactor random suffix to avoid name collision
        self.output_table = Table(name="sub-%s-%s" %
                                  (name, "".join(random.sample(_POOL, 3))),
                                  fields=fields)
        return self.output_table

    def _get_table(self, obj):
        """If obj is a table return its name otherwise figure out
        what it is and return the tablename"""
        if isinstance(obj, Marble):
            return obj
        else:
            return obj.table

    def _resolve(self, cols, check, types=(Column, Aggregation)):
        rval = []
        for i, col in enumerate(cols):
            if isinstance(col, types):
                rval.append(col)
            elif isinstance(col, basestring):
                selectcol = next((c for c in check
                                  if c.name == col or c.fullname == col), None)
                if selectcol:
                    rval.append(selectcol)
            elif isinstance(col, int):
                if col < len(check):
                    rval.append(check[col])
        return rval

    def _get_key_names(self, project, join):
        key_names = []
        for where in self.wheres:
            table_name = self._get_table(where)._name
            keys = []
            if join:
                join_column = next(c.name for c in join
                                   if c.table._name == table_name)
                keys.append(join_column)
            keys += tuple(c.column.name
                          if c.table is None or c.table._name == table_name
                          else None for c in project)
            key_names.append(keys)
        return key_names

    def __init__(self,
                 master,
                 wheres,
                 project=(),
                 order_by=(),
                 join=(),
                 full_join=False,
                 distinct=False,
                 desc=False,
                 limit=0,
                 partition=0,
                 nest=False,
                 wide=False,
                 pre_order_stage=()):
        from hustle.core.pipeworker import Worker

        super(SelectPipe, self).__init__(master=master, worker=Worker())
        self.wheres = wheres
        self.order_by = self._resolve(order_by, project)
        partition = partition or _NPART
        binaries = [i for i, c in enumerate(project)
                    if isinstance(c, (Column, Aggregation)) and c.is_binary]
        # if nest is true, use output_schema to store the output table
        self.output_table = None

        # aggregation functions and their defaults
        efs, gees, ehches, dflts = zip(*[(c.f, c.g, c.h, c.default)
                                         if isinstance(c, Aggregation)
                                         else (dflt_f, dflt_gh, dflt_gh, dflt_default)
                                         for c in project])
        need_agg = False  # need to commit aggregatation
        all_agg = True    # whether all columns in select are aggregates
        for c in project:
            if isinstance(c, Aggregation):
                need_agg = True
            else:
                all_agg = False
        if all_agg:
            _agg_fn = _aggregate_fast
        else:
            _agg_fn = _aggregate

        # build the pipeline
        select_hash_cols = ()
        sort_range = _get_sort_range(0, project, self.order_by)

        join_stage = []
        if join or full_join:
            joinbins = [i + 2 for i in binaries]
            join_stage = [
                (GROUP_LABEL,
                 HustleStage('join',
                             sort=(1, 0),
                             binaries=joinbins,
                             process=partial(process_join,
                                             full_join=full_join,
                                             ffuncs=efs,
                                             ghfuncs=ehches,
                                             deffuncs=dflts,
                                             wide=wide,
                                             need_agg=need_agg,
                                             agg_fn=_agg_fn,
                                             label_fn=partial(_tuple_hash,
                                                              cols=sort_range,
                                                              p=partition))))]
            select_hash_cols = (1,)

        group_by_stage = []
        if need_agg:
            # If all columns in project are aggregations, use process_skip_group
            # to skip the internal groupby
            if all_agg:
                process_group_fn = process_skip_group
                group_by_range = []
            else:
                process_group_fn = process_group
                group_by_range = [i for i, c in enumerate(project)
                                  if isinstance(c, Column)]

            # build the pipeline
            group_by_stage = []
            if wide:
                group_by_stage = [
                    (GROUP_LABEL_NODE,
                     HustleStage('group-combine',
                                 sort=group_by_range,
                                 binaries=binaries,
                                 process=partial(process_group_fn,
                                                 ffuncs=efs,
                                                 ghfuncs=ehches,
                                                 deffuncs=dflts,
                                                 label_fn=partial(_tuple_hash,
                                                                  cols=group_by_range,
                                                                  p=partition))))]
            # A Hack here that overrides disco stage's default option 'combine'.
            # Hustle needs all inputs with the same label to be combined.
            group_by_stage.append((GROUP_LABEL,
                                   HustleStage('group-reduce',
                                               combine=True,
                                               input_sorted=wide,
                                               sort=group_by_range,
                                               binaries=binaries,
                                               process=partial(process_group_fn,
                                                               ffuncs=efs,
                                                               ghfuncs=gees,
                                                               deffuncs=dflts))))

        # process the order_by/distinct stage
        order_stage = []
        if self.order_by or distinct or limit:
            order_stage = [
                (GROUP_LABEL_NODE,
                 HustleStage('order-combine',
                             sort=sort_range,
                             binaries=binaries,
                             desc=desc,
                             process=partial(process_order,
                                             distinct=distinct,
                                             limit=limit or sys.maxint))),
                (GROUP_ALL,
                 HustleStage('order-reduce',
                             sort=sort_range,
                             desc=desc,
                             input_sorted=True,
                             combine_labels=True,
                             process=partial(process_order,
                                             distinct=distinct,
                                             limit=limit or sys.maxint))),
            ]

        if not select_hash_cols:
            select_hash_cols = sort_range

        key_names = self._get_key_names(project, join)

        pipeline = [(SPLIT,
                     HustleStage('restrict-select',
                                 # combine=True,  # cannot set combine -- see #hack in restrict-select phase
                                 process=partial(process_restrict,
                                                 ffuncs=efs,
                                                 ghfuncs=ehches,
                                                 deffuncs=dflts,
                                                 wide=wide or join or full_join,
                                                 need_agg=need_agg,
                                                 agg_fn=_agg_fn,
                                                 label_fn=partial(_tuple_hash,
                                                                  cols=select_hash_cols,
                                                                  p=partition)),
                                 input_chain=[task_input_stream,
                                              partial(hustle_input_stream,
                                                      wheres=wheres,
                                                      gen_where_index=join or full_join,
                                                      key_names=key_names)]))
                    ] + join_stage + group_by_stage + list(pre_order_stage) + order_stage

        # determine the style of output (ie. if it is a Hustle Table),
        # and modify the last stage accordingly
        if nest:
            pipeline[-1][1].output_chain = \
                [partial(hustle_output_stream, result_table=self.get_result_schema(project))]
        self.pipeline = pipeline


def _tuple_hash(key, cols, p):
    r = 0
    for c in cols:
        r ^= hash(key[c])
    return r % p


def _aggregate(inp, label_fn, ffuncs, ghfuncs, deffuncs):
    """
    General channel for executing aggregate function, would be used if
    columns in project are either aggregation or group by columns
    """
    vals = {}
    group_template = [(lambda a: a) if f.__name__ == 'dflt_f' else (lambda a: None)
                      for f in ffuncs]
    for record, _ in inp:
        group = tuple(f(e) for e, f in zip(record, group_template))
        if group in vals:
            accums = vals[group]
        else:
            accums = [default() for default in deffuncs]

        try:
            accums = [f(a, v) for f, a, v in zip(ffuncs, accums, record)]
        except Exception as e:
            print e
            print "YEEHEQW: f=%s a=%s r=%s g=%s" % (ffuncs, accums, record, group)
            import traceback
            print traceback.format_exc(15)
            raise e

        vals[group] = accums

    for group, accums in vals.iteritems():
        key = tuple(h(a) for h, a in zip(ghfuncs, accums))
        out_label = label_fn(group)
        yield out_label, key


def _aggregate_fast(inp, label_fn, ffuncs, ghfuncs, deffuncs):
    """
    Fast channel for executing aggregate function, would be used if
    all columns in project are aggregations
    """
    accums = [default() for default in deffuncs]
    for record, _ in inp:
        try:
            accums = [f(a, v) for f, a, v in zip(ffuncs, accums, record)]
        except Exception as e:
            print e
            print "YEEHEQW: f=%s a=%s r=%s" % (ffuncs, accums, record)
            import traceback
            print traceback.format_exc(15)
            raise e

    key = tuple(h(a) for h, a in zip(ghfuncs, accums))
    yield 0, key


def process_restrict(interface, state, label, inp, task, label_fn, ffuncs,
                     ghfuncs, deffuncs, agg_fn, wide=False, need_agg=False):
    from disco import util
    empty = ()

    # inp contains a set of replicas, let's force local #HACK
    input_processed = False
    for i, inp_url in inp.input.replicas:
        scheme, (netloc, port), rest = util.urlsplit(inp_url)
        if netloc == task.host:
            input_processed = True
            inp.input = inp_url
            break

    if not input_processed:
        raise Exception("Input %s not processed, no LOCAL resource found."
                        % str(inp.input))

    # opportunistically aggregate in this stage
    if need_agg and not wide:
        for out_label, key in agg_fn(inp, label_fn, ffuncs, ghfuncs, deffuncs):
            interface.output(out_label).add(key, empty)
    else:
        for key, value in inp:
            out_label = label_fn(key)
            # print "RESTRICT: %s %s" % (key, value)
            interface.output(out_label).add(key, value)


def process_join(interface, state, label, inp, task, full_join, label_fn,
                 ffuncs, ghfuncs, deffuncs, agg_fn, wide=False, need_agg=False):
    """
    Processor function for the join stage.

    Note that each key in the 'inp' is orgnized as:
        key = (where_index, join_column, other_columns)

    Firstly, all keys are divided into different groups based on the join_column.
    Then the where_index is used to separate keys from different where clauses.
    Finally, merging columns together.
    """
    from itertools import groupby
    empty = ()

    def _merge_record(offset, r1, r2):
        return [i if i is not None else j for i, j in zip(r1[offset:], r2[offset:])]

    def _join_input():
        # inp is a list of (key, value) tuples, the join_cloumn is the 2nd item of the key.
        for joinkey, rest in groupby(inp, lambda k: k[0][1]):
            # To process this join key, we must have values from both tables
            first_table = []
            for record, value in rest:
                # Grab all records from first table by using where index
                if record[0] == 0:
                    first_table.append(record)
                else:
                    if not len(first_table):
                        break
                    # merge each record from table 2 with all records from table 1
                    for first_record in first_table:
                        # dispose of the where_index and join column
                        newrecord = _merge_record(2, first_record, record)
                        yield newrecord, value

    if need_agg and not wide:
        for out_label, key in agg_fn(_join_input(), label_fn, ffuncs, ghfuncs, deffuncs):
            interface.output(out_label).add(key, empty)
    else:
        for key, value in _join_input():
            out_label = label_fn(key)
            # print "JOIN: %s %s" % (key, value)
            interface.output(out_label).add(key, value)


def process_order(interface, state, label, inp, task, distinct, limit):
    from itertools import groupby, islice
    empty = ()
    if distinct:
        for uniqkey, _ in islice(groupby(inp, lambda (k, v): tuple(k)), 0, limit):
            # print "ORDERED %s" % repr(uniqkey)
            interface.output(label).add(uniqkey, empty)
    else:
        for key, value in islice(inp, 0, limit):
            # print "ORDERED %s" % repr(key)
            interface.output(label).add(key, value)


def process_group(interface, state, label, inp, task, ffuncs, ghfuncs,
                  deffuncs, label_fn=None):
    """Process function of aggregation combine stage."""
    from itertools import groupby

    empty = ()

    group_template = [(lambda a: a) if f.__name__ == 'dflt_f' else (lambda a: None)
                      for f in ffuncs]
    # pull the key apart
    for group, tups in groupby(inp,
                               lambda (k, _):
                               tuple(ef(e) for e, ef in zip(k, group_template))):
        accums = [default() for default in deffuncs]
        for record, _ in tups:
            # print "Group: %s, REC: %s" % (group, repr(record))
            try:
                accums = [f(a, v) for f, a, v in zip(ffuncs, accums, record)]
            except Exception as e:
                print e
                print "YOLO: f=%s a=%s r=%s g=%s" % (ffuncs, accums, record, group)
                import traceback
                print traceback.format_exc(15)
                raise e

        key = tuple(h(a) for h, a in zip(ghfuncs, accums))
        if label_fn:
            label = label_fn(group)
        interface.output(label).add(key, empty)


def process_skip_group(interface, state, label, inp, task, ffuncs,
                       ghfuncs, deffuncs, label_fn=None):
    """Process function of aggregation combine stage without groupby.
    """
    empty = ()
    accums = [default() for default in deffuncs]
    for record, _ in inp:
        try:
            accums = [f(a, v) for f, a, v in zip(ffuncs, accums, record)]
        except Exception as e:
            raise e

    key = tuple(h(a) for h, a in zip(ghfuncs, accums))
    interface.output(0).add(key, empty)


def _get_sort_range(select_offset, select_columns, order_by_columns):
    # sort by all
    sort_range = [i + select_offset for i, c in enumerate(select_columns)
                  if isinstance(c, Column) and not c.is_binary]
    if order_by_columns:
        scols = ["%s%s" % (c.table._name if c.table else '', c.name)
                 for c in select_columns]
        ocols = ["%s%s" % (c.table._name if c.table else '', c.name)
                 for c in order_by_columns]
        rcols = set(scols) - set(ocols)
        # make sure to include the columns *not* in the order_by expression as well
        # this is to ensure that 'distinct' will work
        sort_range = tuple(select_offset + scols.index(c) for c in ocols) +\
            tuple(select_offset + scols.index(c) for c in rcols)
    return sort_range

########NEW FILE########
__FILENAME__ = pipeworker
#!/usr/bin/env python

from collections import defaultdict
from disco import util
from disco.util import shuffled, chainify
from disco.worker.pipeline import worker
from disco.worker.pipeline.worker import Stage
from heapq import merge
from itertools import islice


# import sys
# sys.path.append('/Library/Python/2.7/site-packages/pycharm-debug.egg')
# import pydevd
# pydevd.settrace('localhost', port=12999, stdoutToServer=True, stderrToServer=True)

def sort_reader(fd, fname, read_buffer_size=8192):
    buf = ""
    while True:
        r = fd.read(read_buffer_size)
        buf += r

        kayvees = buf.split('\n')
        buf = kayvees[-1]

        # the last key/value pair will be truncated except for EOF, in which case it will be empty
        for kayvee in islice(kayvees, len(kayvees) - 1):
            raws = kayvee.split(b"\xff")
            yield islice(raws, len(raws) - 1)

        if not len(r):
            if len(buf):
                print("Couldn't match the last {0} bytes in {1}. "
                      "Some bytes may be missing from input.".format(len(buf), fname))
            break


def disk_sort(input, filename, sort_keys, binaries=(), sort_buffer_size='10%',
              desc=False):
    import ujson
    from disco.comm import open_local
    from disco.fileutils import AtomicFile
    import base64
    # import sys
    # sys.path.append('/Library/Python/2.7/site-packages/pycharm-debug.egg')
    # import pydevd
    # pydevd.settrace('localhost', port=12999, stdoutToServer=True, stderrToServer=True)
    out_fd = AtomicFile(filename)
    key_types = None
    MPT = ()
    # print "SORTKEY: %s" % repr(sort_keys)
    for key, _ in input:
        if isinstance(key, (str, unicode)):
            raise ValueError("Keys must be sequences", key)

        # determine if the key is numeric
        if key_types is None:
            key_types = []
            for kt in key:
                try:
                    float(kt)
                    key_types.append('n')
                except:
                    key_types.append('')

        #serialize the key - encoded either as NULL, json, or b64 - note that
        for i, each_key in enumerate(key):
            if each_key is None:
                ukey = b'\x00'
            elif i in binaries and key_types[i] != 'n':
                ukey = base64.b64encode(each_key)
            else:
                ukey = ujson.dumps(each_key)
            out_fd.write(ukey)
            out_fd.write(b'\xff')
        out_fd.write('\n')
    out_fd.flush()
    out_fd.close()
    unix_sort(filename,
              [(sk, key_types[sk]) for sk in sort_keys],
              sort_buffer_size=sort_buffer_size,
              desc=desc)
    fd = open_local(filename)
    for k in sort_reader(fd, fd.url):
        # yield [ujson.loads(key) if key != b'\x00' else None for key in k], MPT

        rval = []
        for i, key in enumerate(k):
            if key == b'\x00':
                rkey = None
            elif i in binaries:
                rkey = base64.b64decode(key)
            else:
                rkey = ujson.loads(key)
            rval.append(rkey)
        yield rval, MPT


def sort_cmd(filename, sort_keys, sort_buffer_size, desc=False):
    keys = []
    # print "File %s" % filename
    for index, typ in sort_keys:
        keys.append("-k")
        index += 1
        if desc:
            keys.append("%d,%dr%s" % (index, index, typ))
        else:
            keys.append("%d,%d%s" % (index, index, typ))

    cmd = ["sort", "-t", '\xff']
    return (cmd + keys + ["-T", ".", "-S", sort_buffer_size, "-o", filename, filename],
            False)


def unix_sort(filename, sort_keys, sort_buffer_size='10%', desc=False):
    import subprocess, os.path
    if not os.path.isfile(filename):
        raise Exception("Invalid sort input file {0}".format(filename), filename)
    try:
        env = os.environ.copy()
        env['LC_ALL'] = 'C'
        cmd, shell = sort_cmd(filename, sort_keys, sort_buffer_size, desc=desc)
        subprocess.check_call(cmd, env=env, shell=shell)
    except subprocess.CalledProcessError as e:
        raise Exception("Sorting {0} failed: {1}".format(filename, e), filename)


class _lt_wrapper(tuple):
    def __new__(cls, seq, sort_range):
        return super(_lt_wrapper, cls).__new__(cls, seq)

    def __init__(self, seq, sort_range):
        super(_lt_wrapper, self).__init__(seq)
        self.sort_range = sort_range

    def __lt__(self, other):
        for sr in self.sort_range:
            if self[sr] < other[sr]:
                return True
            elif self[sr] > other[sr]:
                return False
        return False  # they are equal


class _gt_wrapper(tuple):
    def __new__(cls, seq, sort_range):
        return super(_gt_wrapper, cls).__new__(cls, seq)

    def __init__(self, seq, sort_range):
        super(_gt_wrapper, self).__init__(seq)
        self.sort_range = sort_range

    def __lt__(self, other):
        for sr in self.sort_range:
            if self[sr] > other[sr]:
                return True
            elif self[sr] < other[sr]:
                return False
        return False  # they are equal


def merge_wrapper(it, sort_range=(0,), desc=False):
    if desc:
        wrapper = _gt_wrapper
    else:
        wrapper = _lt_wrapper

    for key, value in it:
        yield wrapper(key, sort_range), value


class HustleStage(Stage):
    def __init__(self, name, sort=(), input_sorted=False, desc=False,
                 combine_labels=False, binaries=(), **kwargs):
        super(HustleStage, self).__init__(name, **kwargs)
        self.sort = sort
        self.input_sorted = input_sorted
        self.desc = desc
        self.combine_labels = combine_labels
        self.binaries = binaries


class Worker(worker.Worker):
    def jobenvs(self, job, **jobargs):
        import sys
        envs = {'PYTHONPATH': ':'.join([path.strip('/') for path in sys.path])}
        envs['LD_LIBRARY_PATH'] = 'lib'
        envs['PYTHONPATH'] = ':'.join(('lib', envs.get('PYTHONPATH', '')))
        envs['PATH'] = '/srv/disco/helper/bin:/usr/local/bin:/bin:/usr/bin'
        envs['TZ'] = 'UTC'
        envs['DISCO_WORKER_MAX_MEM'] = "-1"
        return envs

    def start(self, task, job, **jobargs):
        task.makedirs()
        if self.getitem('profile', job, jobargs):
            from cProfile import runctx
            name = 'profile-{0}'.format(task.uid)
            path = task.path(name)
            runctx('self.run(task, job, **jobargs)', globals(), locals(), path)
            task.put(name, open(path, 'rb').read())
        else:
            self.run(task, job, **jobargs)
        self.end(task, job, **jobargs)

    def prepare_input_map(self, task, stage, params):
        # The input map maps a label to a sequence of inputs with that
        # label.
        map = defaultdict(list)

        for l, i in util.chainify(self.labelexpand(task, stage, i, params)
                                  for i in self.get_inputs()):
            if stage.combine_labels:
                map[0].append(i)
            else:
                map[l].append(i)

        if stage.sort:
            newmap = {}
            if stage.input_sorted:
                for label, inputs in map.iteritems():
                    input = merge(*(merge_wrapper(inp,
                                                  sort_range=stage.sort,
                                                  desc=stage.desc)
                                    for inp in inputs))
                    newmap[label] = [input]
            else:
                for label, inputs in map.iteritems():

                    input = chainify(shuffled(inputs))
                    newmap[label] = [disk_sort(input,
                                               task.path('sort.dl'),
                                               sort_keys=stage.sort,
                                               sort_buffer_size='15%',
                                               binaries=stage.binaries,
                                               desc=stage.desc)]
            map = newmap
        #print "OUTSIE: %s" % str(map)
        return map

    def run_stage(self, task, stage, params):
        # Call the various entry points of the stage task in order.
        params._task = task
        interface = self.make_interface(task, stage, params)
        state = stage.init(interface, params) if callable(stage.init) else None
        if callable(stage.process):
            input_map = self.prepare_input_map(task, stage, params)
            for label in stage.input_hook(state, input_map.keys()):
                if stage.combine:
                    stage.process(interface, state, label,
                                  worker.SerialInput(input_map[label]), task)
                else:
                    for inp in input_map[label]:
                        stage.process(interface, state, label, inp, task)
        if callable(stage.done):
            stage.done(interface, state)


if __name__ == '__main__':
    Worker.main()

########NEW FILE########
__FILENAME__ = settings
import os
from disco.ddfs import DDFS
from disco.core import Disco


def guess_settings():
    for settings_file in (os.path.expanduser('~/.hustle'),
                          '/etc/hustle/settings.yaml'):
        if os.path.exists(settings_file):
            return settings_file
    return ''


defaults = {
    'settings_file': guess_settings(),
    'server': 'disco://localhost',
    'nest': False,
    'dump': False,
    'worker_class': 'disco.worker.classic.worker.Worker',
    'partition': 16,
    'history_size': 1000
}

overrides = {}


class Settings(dict):
    def __init__(self, *args, **kwargs):
        # load the defaults
        super(Settings, self).update(defaults)

        # override with the settings file
        path = kwargs.get('settings_file') or self['settings_file']
        if path and os.path.exists(path):
            try:
                import yaml
                self.update(yaml.load(open(path)))
            except:
                pass  # if ya can't ya can't

        # final overrides
        super(Settings, self).update(overrides)
        super(Settings, self).__init__(*args, **kwargs)

        # set up ddfs and disco
        if not self['server'].startswith('disco://'):
            self['server'] = 'disco://' + self['server']

        if 'ddfs' not in self:
            self['ddfs'] = DDFS(self['server'])
        self['server'] = Disco(self['server'])

        # set up worker
        if 'worker' not in self:
            worker_mod, _, worker_class = self['worker_class'].rpartition('.')
            mod = __import__(worker_mod, {}, {}, worker_mod)
            self['worker'] = getattr(mod, worker_class)()

########NEW FILE########
__FILENAME__ = stat
from disco.core import Job
from disco.worker.task_io import task_input_stream
from hustle.core.pipeworker import Worker, HustleStage

import hustle
import hustle.core
import hustle.core.marble


def stat_input_stream(fd, size, url, params):
    from disco import util
    from hustle.core.marble import MarbleStream

    try:
        scheme, netloc, rest = util.urlsplit(url)
    except Exception as e:
        print "Error handling hustle_input_stream for %s. %s" % (url, e)
        raise e

    otab = None
    try:
        # print "FLurlG: %s" % url
        fle = util.localize(rest, disco_data=params._task.disco_data,
                            ddfs_data=params._task.ddfs_data)
        # print "FLOGLE: %s" % fle
        otab = MarbleStream(fle)
        rows = otab.number_rows
        frows = float(rows)
        rval = {'_': rows, }
        for field, (subdb, subindexdb, _, column, _) in otab.dbs.iteritems():
            if subindexdb:
                rval[field] = subindexdb.stat(otab.txn)['ms_entries'] / frows
        yield '', rval
    except Exception as e:
        print "Gibbers: %s" % e
        raise e
    finally:
        if otab:
            otab.close()


class StatPipe(Job):
    required_modules = [
        ('hustle', hustle.__file__),
        ('hustle.core', hustle.core.__file__),
        ('hustle.core.marble', hustle.core.marble.__file__)]

    def __init__(self, master):

        super(StatPipe, self).__init__(master=master, worker=Worker())
        self.pipeline = [('split',
                          HustleStage('stat',
                                      process=process_stat,
                                      input_chain=[task_input_stream,
                                                   stat_input_stream]))]


def process_stat(interface, state, label, inp, task):
    from disco import util

    # inp contains a set of replicas, let's force local #HACK
    input_processed = False
    for i, inp_url in inp.input.replicas:
        scheme, (netloc, port), rest = util.urlsplit(inp_url)
        if netloc == task.host:
            input_processed = True
            inp.input = inp_url
            break

    if not input_processed:
        raise Exception("Input %s not processed, no LOCAL resource found."
                        % str(inp.input))

    for key, value in inp:
        interface.output(0).add(key, value)

########NEW FILE########
__FILENAME__ = util
from disco import func
from disco import util
from disco.settings import DiscoSettings

import collections


class Peekable(object):
    def __init__(self, iterable):
        self._iterable = iter(iterable)
        self._cache = collections.deque()

    def __iter__(self):
        return self

    def _fillcache(self, n):
        if n is None:
            n = 1
        while len(self._cache) < n:
            self._cache.append(self._iterable.next())

    def next(self, n=None):
        self._fillcache(n)
        if n is None:
            result = self._cache.popleft()
        else:
            result = [self._cache.popleft() for i in range(n)]
        return result

    def peek(self, n=None):
        self._fillcache(n)
        if n is None:
            result = self._cache[0]
        else:
            result = [self._cache[i] for i in range(n)]
        return result


class SortedIterator(object):

    def __init__(self, inputs):
        ins = [Peekable(input) for input in inputs]
        self.collection = sorted(ins, key=self._key)

    def __iter__(self):
        return self

    def next(self):
        removes = []
        reinsert = None
        rval = None
        for stream in self.collection:
            try:
                rval = stream.next()
                reinsert = stream
                break
            except StopIteration:
                removes.append(stream)

        if rval:
            for remove in removes:
                self.collection.remove(remove)
            if reinsert:
                self.collection.remove(reinsert)
                try:
                    reinsert.peek()
                except:
                    pass
                else:
                    removes = []
                    reinsert_index = 0
                    for stream in self.collection:
                        try:
                            stream.peek()
                            if self._key(reinsert) < self._key(stream):
                                break
                        except:
                            removes.append(stream)
                        reinsert_index += 1
                    self.collection.insert(reinsert_index, reinsert)
                    for remove in removes:
                        self.collection.remove(remove)
            return rval
        raise StopIteration

    def _key(self, stream):
        try:
            key, value = stream.peek()
            return tuple(key)
        except StopIteration:
            return tuple()


def sorted_iterator(urls,
                    reader=func.chain_reader,
                    input_stream=(func.map_input_stream,),
                    notifier=func.notifier,
                    params=None,
                    ddfs=None):

    from disco.worker import Input
    from disco.worker.classic.worker import Worker

    worker = Worker(map_reader=reader, map_input_stream=input_stream)
    settings = DiscoSettings(DISCO_MASTER=ddfs) if ddfs else DiscoSettings()

    inputs = []
    for input in util.inputlist(urls, settings=settings):
        notifier(input)
        instream = Input(input, open=worker.opener('map', 'in', params))
        if instream:
            inputs.append(instream)

    return SortedIterator(inputs)


def ensure_list(val):
    if not isinstance(val, list):
        if isinstance(val, (tuple, set)):
            return list(val)
        return [val]
    return val

########NEW FILE########
__FILENAME__ = test_aggregation
import unittest
from hustle import select, Table, h_sum, h_count, star
from setup import IMPS
from hustle.core.settings import Settings, overrides


class TestAggregation(unittest.TestCase):
    def setUp(self):
        overrides['server'] = 'disco://localhost'
        overrides['dump'] = False
        overrides['nest'] = False
        self.settings = Settings()

    def tearDown(self):
        pass

    def test_count(self):
        imps = Table.from_tag(IMPS)
        res = select(h_count(), where=imps)
        count = list(res)[0][0]
        self.assertEqual(count, 200)

    def test_simple_aggregation(self):
        imps = Table.from_tag(IMPS)
        results = select(imps.ad_id, imps.cpm_millis, where=imps.date == '2014-01-27')

        sum_millis = {}
        for ad_id, millis in results:
            if ad_id not in sum_millis:
                sum_millis[ad_id] = [0, 0]
            sum_millis[ad_id][0] += millis
            sum_millis[ad_id][1] += 1

        results = select(imps.ad_id, h_sum(imps.cpm_millis), h_count(), where=imps.date == '2014-01-27')
        self.assertGreater(len(list(results)), 0)
        for ad_id, millis, count in results:
            ad_tup = sum_millis[ad_id]
            self.assertEqual(millis, ad_tup[0])
            self.assertEqual(count, ad_tup[1])

    def test_ordered_aggregation(self):
        imps = Table.from_tag(IMPS)
        resx = select(imps.ad_id, imps.cpm_millis, where=imps.date == '2014-01-27')

        sum_millis = {}
        for ad_id, millis in resx:
            if ad_id not in sum_millis:
                sum_millis[ad_id] = [0, 0]
            sum_millis[ad_id][0] += millis
            sum_millis[ad_id][1] += 1

        results = select(imps.ad_id, h_sum(imps.cpm_millis), h_count(),
                         where=imps.date == '2014-01-27',
                         order_by=2,
                         limit=3,
                         nest=True)
        self.assertGreater(len(list(results)), 0)
        lowest = 0
        for ad_id, millis, count in results:
            self.assertLessEqual(lowest, count)
            lowest = count
            ad_tup = sum_millis[ad_id]
            self.assertEqual(millis, ad_tup[0])
            self.assertEqual(count, ad_tup[1])
        self.assertEqual(len(list(results)), min(len(sum_millis), 3))

    def test_multiple_group_bys(self):
        imps = Table.from_tag(IMPS)
        results = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date > '2014-01-22')

        sum_millis = {}
        for ad_id, dt, millis in results:
            key = str(ad_id) + dt
            if key not in sum_millis:
                sum_millis[key] = [0, 0]
            sum_millis[key][0] += millis
            sum_millis[key][1] += 1

        results = select(imps.ad_id, imps.date, h_sum(imps.cpm_millis), h_count(), where=imps.date > '2014-01-22')
        self.assertGreater(len(list(results)), 0)
        for ad_id, dt, millis, count in results:
            ad_tup = sum_millis[str(ad_id) + dt]
            self.assertEqual(millis, ad_tup[0])
            self.assertEqual(count, ad_tup[1])

    def test_nested_agg(self):
        imps = Table.from_tag(IMPS)
        results = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date > '2014-01-22')

        sum_millis = {}
        for ad_id, dt, millis in results:
            key = str(ad_id) + dt
            if key not in sum_millis:
                sum_millis[key] = [0, 0]
            sum_millis[key][0] += millis
            sum_millis[key][1] += 1

        newtab = select(imps.ad_id, imps.date, h_sum(imps.cpm_millis), h_count(),
                        where=imps.date > '2014-01-22',
                        nest=True)
        results = select(*star(newtab), where=newtab)
        self.assertGreater(len(list(results)), 0)
        for ad_id, dt, millis, count in results:
            ad_tup = sum_millis[str(ad_id) + dt]
            self.assertEqual(millis, ad_tup[0])
            self.assertEqual(count, ad_tup[1])

    def test_overflow(self):
        from itertools import izip

        imps = Table.from_tag(IMPS)
        fly_results = select(imps.date, h_sum(imps.impression), where=imps, order_by=imps.date)

        nest_tab = select(imps.date, h_sum(imps.impression), where=imps, nest=True)
        nest_results = select(*star(nest_tab), where=nest_tab, order_by=0)

        for ((fdate, fimps), (ndate, nimps)) in izip(fly_results, nest_results):
            self.assertEqual(fdate, ndate)
            self.assertEqual(fimps, nimps)


########NEW FILE########
__FILENAME__ = test_bool
import unittest
from hustle import select, Table, h_sum, h_count
from setup import IMPS, PIXELS
from hustle.core.settings import Settings, overrides


class TestBool(unittest.TestCase):
    def setUp(self):
        overrides['server'] = 'disco://localhost'
        overrides['dump'] = False
        overrides['nest'] = False
        self.settings = Settings()

    def tearDown(self):
        pass

    def test_project(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.click, imps.conversion, imps.impression, where=imps)
        clicks = conversions = impressions = 0
        for (click, conv, imp) in res:
            clicks += click
            conversions += conv
            impressions += imp

        self.assertEqual(clicks, 21)
        self.assertEqual(conversions, 5)
        self.assertEqual(impressions, 174)

    def test_aggregate(self):
        imps = Table.from_tag(IMPS)
        res = select(h_sum(imps.click), h_sum(imps.conversion), h_sum(imps.impression), where=imps)

        (clicks, conversions, impressions) = list(res)[0]

        self.assertEqual(clicks, 21)
        self.assertEqual(conversions, 5)
        self.assertEqual(impressions, 174)

    def test_bool_values(self):
        pix = Table.from_tag(PIXELS)
        res = select(pix.isActive, where=pix.isActive == True)
        actives = 0
        for (act, ) in res:
            actives += act

        self.assertEqual(actives, 234)

        res = select(pix.isActive, where=pix.isActive == 0)
        actives = 0
        for (act, ) in res:
            actives += 1

        self.assertEqual(actives, 266)

    def test_bit_values(self):
        pix = Table.from_tag(PIXELS)
        res = select(pix.isActive, where=pix.isActive == 1)
        actives = 0
        for (act, ) in res:
            actives += act

        self.assertEqual(actives, 234)




########NEW FILE########
__FILENAME__ = test_drop
import unittest
from hustle import Table, insert, drop, delete, get_partitions
from hustle.core.settings import Settings, overrides

IMPS = '__test_drop_imps'


def imp_process(data):
    from disco.util import urlsplit

    _, (host, _), _ = urlsplit(data['url'])
    if host.startswith('www.'):
        host = host[4:]
    data['site_id'] = host


def ensure_tables():
    overrides['server'] = 'disco://localhost'
    overrides['dump'] = False
    overrides['nest'] = False
    settings = Settings()
    ddfs = settings['ddfs']

    imps = Table.create(IMPS,
                        fields=['=$token', '%url', '+%site_id', '@cpm_millis', '+#ad_id', '+$date', '+@time'],
                        partition='date',
                        force=True)

    tags = ddfs.list("hustle:%s:" % IMPS)
    if len(tags) == 0:
        # insert the files
        insert(imps, phile='fixtures/imps.json', preprocess=imp_process)
    return imps


class TestDropTable(unittest.TestCase):
    def setUp(self):
        overrides['server'] = 'disco://localhost'
        overrides['dump'] = False
        overrides['nest'] = False
        self.settings = Settings()
        self.ddfs = self.settings['ddfs']
        self.table = ensure_tables()

    def test_delete_all(self):
        delete(self.table)
        self.assertEqual([], get_partitions(self.table))
        tags = self.ddfs.list(Table.base_tag(self.table._name))
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0], "hustle:__test_drop_imps")

    def test_delete_partial(self):
        delete(self.table.date >= '2014-01-13')
        self.assertEqual(['hustle:__test_drop_imps:2014-01-10',
                          'hustle:__test_drop_imps:2014-01-11',
                          'hustle:__test_drop_imps:2014-01-12'],
                         get_partitions(self.table))
        tags = self.ddfs.list(Table.base_tag(self.table._name))
        self.assertEqual(len(tags), 4)
        self.assertIn("hustle:__test_drop_imps", tags)
        drop(self.table)
        with self.assertRaises(ValueError):
            delete(self.table.site_id == 'foobar')
            delete(self.tale.url)

    def test_drop(self):
        drop(self.table)
        self.assertEqual([], get_partitions(self.table))
        tags = self.ddfs.list(Table.base_tag(self.table._name))
        self.assertEqual(len(tags), 0)

########NEW FILE########
__FILENAME__ = test_join
import unittest
from hustle import select, Table, h_sum, h_count
from setup import IMPS, PIXELS
from hustle.core.settings import Settings, overrides


class TestJoin(unittest.TestCase):
    def setUp(self):
        overrides['server'] = 'disco://localhost'
        overrides['dump'] = False
        overrides['nest'] = False
        self.settings = Settings()

    def tearDown(self):
        pass

    def test_simple_join(self):
        imps = Table.from_tag(IMPS)
        pix = Table.from_tag(PIXELS)

        imp_sites = [(s, a) for (s, a) in select(imps.site_id, imps.ad_id,
                                                 where=imps.date < '2014-01-13')]
        pix_sites = [(s, a) for (s, a) in select(pix.site_id, pix.amount,
                                                 where=pix.date < '2014-01-13')]

        join = []
        for imp_site, imp_ad_id in imp_sites:
            for pix_site, pix_amount in pix_sites:
                if imp_site == pix_site:
                    join.append((imp_ad_id, pix_amount))

        res = select(imps.ad_id, pix.amount,
                     where=(imps.date < '2014-01-13', pix.date < '2014-01-13'),
                     join=(imps.site_id, pix.site_id),
                     order_by='amount')
        results = list(res)
        self.assertEqual(len(results), len(join))

        for jtup in join:
            self.assertIn(jtup, results)

        lowest = 0
        for ad_id, amount in results:
            self.assertLessEqual(lowest, amount)
            lowest = amount

    def test_nested_join(self):
        imps = Table.from_tag(IMPS)
        pix = Table.from_tag(PIXELS)

        imp_sites = list(select(imps.site_id, imps.ad_id,
                                where=imps.date < '2014-01-13'))
        pix_sites = list(select(pix.site_id, pix.amount,
                                where=((pix.date < '2014-01-13') &
                                       (pix.isActive == True))))

        join = []
        for imp_site, imp_ad_id in imp_sites:
            for pix_site, pix_amount in pix_sites:
                if imp_site == pix_site:
                    join.append((imp_ad_id, pix_amount))

        sub_pix = select(pix.site_id, pix.amount, pix.date,
                         where=((pix.date < '2014-01-15') & (pix.isActive == True)),
                         nest=True)

        res = select(imps.ad_id, sub_pix.amount,
                     where=(imps.date < '2014-01-13', sub_pix.date < '2014-01-13'),
                     join=(imps.site_id, sub_pix.site_id))
        results = [tuple(c) for c in res]
        self.assertEqual(len(results), len(join))

        for jtup in join:
            self.assertIn(jtup, results)

    def test_nested_self_join(self):
        """
        A self join is joining the table against itself.  This requires the use of aliases.
        """
        imps = Table.from_tag(IMPS)

        early = list(select(imps.ad_id, imps.cpm_millis,
                            where=imps.date < '2014-01-20'))
        late = list(select(imps.ad_id, imps.cpm_millis,
                           where=imps.date >= '2014-01-20'))

        join = {}
        for eid, ecpm in early:
            for lid, lcpm in late:
                if eid == lid:
                    if eid not in join:
                        join[eid] = [0, 0, 0]
                    join[eid][0] += ecpm
                    join[eid][1] += lcpm
                    join[eid][2] += 1

        early = select(imps.ad_id, imps.cpm_millis, where=imps.date < '2014-01-20', nest=True)
        late = select(imps.ad_id, imps.cpm_millis, where=imps.date >= '2014-01-20', nest=True)
        jimmy = select(early.ad_id.named('adididid'),
                       h_sum(early.cpm_millis).named('emillis'),
                       h_sum(late.cpm_millis).named('lmillis'),
                       h_count(),
                       where=(early, late),
                       join='ad_id')

        james = list(jimmy)
        self.assertEqual(len(join), len(james))

        for (ad_id, emillis, lmillis, cnt) in james:
            ecpm, lcpm, ocnt = join[ad_id]
            self.assertEqual(emillis, ecpm)
            self.assertEqual(lmillis, lcpm)
            self.assertEqual(cnt, ocnt)


    def test_aggregate_join(self):
        imps = Table.from_tag(IMPS)
        pix = Table.from_tag(PIXELS)

        imp_sites = list(select(imps.site_id, imps.ad_id,
                                where=imps.date < '2014-01-13'))
        pix_sites = list(select(pix.site_id, pix.amount,
                                where=pix.date < '2014-01-13'))

        join = {}
        for imp_site, imp_ad_id in imp_sites:
            for pix_site, pix_amount in pix_sites:
                if imp_site == pix_site:
                    if imp_ad_id not in join:
                        join[imp_ad_id] = [0, 0]
                    join[imp_ad_id][0] += pix_amount
                    join[imp_ad_id][1] += 1

        res = select(imps.ad_id, h_sum(pix.amount), h_count(),
                     where=(imps.date < '2014-01-13', pix.date < '2014-01-13'),
                     join=(imps.site_id, pix.site_id))
        results = list(res)
        self.assertEqual(len(results), len(join))

        for (ad_id, amount, count) in results:
            ramount, rcount = join[ad_id]
            self.assertEqual(ramount, amount)
            self.assertEqual(rcount, count)


########NEW FILE########
__FILENAME__ = test_project_order
import unittest
from hustle import select, Table
from setup import IMPS
from hustle.core.settings import Settings, overrides


class TestProjectOrder(unittest.TestCase):
    def setUp(self):
        overrides['server'] = 'disco://localhost'
        overrides['dump'] = False
        overrides['nest'] = False
        self.settings = Settings()

    def tearDown(self):
        pass

    def test_single_int_order(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date == '2014-01-27', order_by=imps.cpm_millis)
        lowest = 0
        for a, d, c in res:
            self.assertLessEqual(lowest, c)
            lowest = c

    def test_combo_order(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=imps.date > '2014-01-21',
                     order_by=(imps.date, imps.cpm_millis))
        lowest_cpm = 0
        lowest_date = '2000-01-01'
        for a, d, c in res:
            if lowest_date == d:
                self.assertLessEqual(lowest_cpm, c)
                lowest_cpm = c
            else:
                self.assertLessEqual(lowest_date, d)
                lowest_date = d
                lowest_cpm = c

    def test_combo_descending(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=imps.date > '2014-01-21',
                     order_by=(imps.date, imps.cpm_millis),
                     desc=True)
        highest_cpm = 1000000000
        highest_date = '2222-01-01'
        for a, d, c in res:
            if highest_date == d:
                self.assertGreaterEqual(highest_cpm, c)
                highest_cpm = c
            else:
                self.assertGreaterEqual(highest_date, d)
                highest_date = d
                highest_cpm = c

    def test_high_limit(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date == '2014-01-27', limit=100)
        results = list(res)
        self.assertEqual(len(results), 10)

    def test_low_limit(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date == '2014-01-27', limit=4)
        results = list(res)
        self.assertEqual(len(results), 4)

    def test_distinct(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, where=imps.date == '2014-01-27', distinct=True)
        results = list(res)
        self.assertEqual(len(results), 8)

    def test_overall(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, where=imps.date == '2014-01-27', distinct=True, limit=4,
                     order_by='ad_id', desc=True)
        results = [a for a, d in res]
        self.assertEqual(len(results), 4)
        self.assertListEqual(results, [30019, 30018, 30017, 30015])

########NEW FILE########
__FILENAME__ = test_simple_query
import unittest
from hustle import select, Table
from setup import IMPS
from hustle.core.settings import Settings, overrides


class TestSimpleQuery(unittest.TestCase):
    def setUp(self):
        overrides['server'] = 'disco://localhost'
        overrides['dump'] = False
        overrides['nest'] = False
        self.settings = Settings()

    def tearDown(self):
        pass

    def test_equality_on_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date == '2014-01-27')
        results = list(res)
        self.assertEqual(len(results), 10)
        found = next((a, d, c) for a, d, c in results if a == 30018 and d == '2014-01-27' and c == 4506)
        self.assertIsNotNone(found)
        self.assertTrue(all(d == '2014-01-27' for _, d, _ in results))

    def test_range_on_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis, where=imps.date > '2014-01-27')
        results = list(res)
        self.assertEqual(len(results), 20)
        self.assertTrue(all(d in ('2014-01-28', '2014-01-29') for _, d, _ in results))

    def test_combo_where_on_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=((imps.date >= '2014-01-20') & (imps.ad_id == 30010)))
        results = list(res)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(d >= '2014-01-20' and a == 30010 for a, d, _ in results))

    def test_combo_where_on_or_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=((imps.date == '2014-01-21') | (imps.date == '2014-01-25') | (imps.ad_id == 30010)))
        results = list(res)
        self.assertEqual(len(results), 27)
        self.assertTrue(all(d == '2014-01-21' or d == '2014-01-25' or a == 30010 for a, d, _ in results))

    def test_combo_where_on_or_partition_ex(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=((imps.date << ['2014-01-21', '2014-01-25']) | (imps.ad_id == 30010)))
        results = list(res)
        self.assertEqual(len(results), 27)
        self.assertTrue(all(d == '2014-01-21' or d == '2014-01-25' or a == 30010 for a, d, _ in results))

    def test_combo_where_on_or_partition_ex1(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=((imps.date << ['2014-01-21', '2014-01-25']) | (imps.ad_id << [30003, 30010])))
        results = list(res)
        self.assertEqual(len(results), 40)
        self.assertTrue(all(d == '2014-01-21' or d == '2014-01-25' or a == 30010 or a == 30003 for a, d, _ in results))

    def test_combo_where_on_or_partition_ex2(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=((imps.date << ['2014-01-21', '2014-01-25']) & (imps.ad_id << [30003, 30010])))
        results = list(res)
        self.assertEqual(len(results), 1)
        self.assertTrue(all(d == '2014-01-21' and a == 30010 for a, d, _ in results))

    def test_combo_where_on_and_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=((imps.date >= '2014-01-21') & (imps.date <= '2014-01-23') & (imps.ad_id == 30010)))
        results = list(res)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(d in ('2014-01-21', '2014-01-22', '2014-01-23') and a == 30010 for a, d, _ in results))

    def test_combo_where_no_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis, where=(imps.time >= 180000))
        results = list(res)
        print results
        self.assertEqual(len(results), 5)

    def test_combo_where_on_mixed_partition(self):
        imps = Table.from_tag(IMPS)
        res = select(imps.ad_id, imps.date, imps.cpm_millis,
                     where=(((imps.date >= '2014-01-21') & (imps.date <= '2014-01-23') & (imps.time > 170000))))
        results = list(res)
        self.assertEqual(len(results), 2)
        self.assertTrue(all((d in ('2014-01-21', '2014-01-22', '2014-01-23') and a == 30003) for a, d, c in results))

########NEW FILE########
__FILENAME__ = query


select(i.token, min(i.time), where=((i.campaign_io_id == 17146) |(i.campaign_io_id == 17147) |(i.campaign_io_id == 17160)) & (i.impressions > 0) & (i.is_psa == 0) & (i.date == '2014-02-20'), nest=True)


########NEW FILE########
__FILENAME__ = test_column
import unittest
from hustle.core.marble import Column
import mdb


_NAME = "test"


class TestColumn(unittest.TestCase):
    def setUp(self):
        pass

    def test_column_errors(self):
        str_column = Column(_NAME, None, index_indicator=0, partition=False,
                            type_indicator=mdb.MDB_STR,
                            compression_indicator=0,
                            rtrie_indicator=mdb.MDB_UINT_16)
        with self.assertRaises(TypeError):
            str_column > 'hello'

        with self.assertRaises(TypeError):
            str_column == 'hello'

    def test_is_int(self):
        str_column = Column(_NAME, None, index_indicator=False, partition=False,
                            type_indicator=mdb.MDB_STR,
                            compression_indicator=0,
                            rtrie_indicator=mdb.MDB_UINT_16)
        self.assertTrue(str_column.is_int)

        str_column = Column(_NAME, None, index_indicator=False, partition=False,
                            type_indicator=mdb.MDB_STR,
                            compression_indicator=1,
                            rtrie_indicator=mdb.MDB_UINT_16)
        self.assertFalse(str_column.is_int)

    def test_is_boolean(self):
        b_column = Column(_NAME, None, boolean=True)
        self.assertTrue(b_column.is_int)
        self.assertTrue(b_column.is_index)
        self.assertTrue(b_column.is_boolean)
        self.assertFalse(b_column.is_wide)
        self.assertFalse(b_column.is_trie)


    def test_is_trie(self):
        str_column = Column(_NAME, None, index_indicator=False, partition=False,
                            type_indicator=mdb.MDB_STR,
                            compression_indicator=0,
                            rtrie_indicator=mdb.MDB_UINT_16)
        self.assertTrue(str_column.is_trie)

        str_column = Column(_NAME, None, index_indicator=False, partition=False,
                            type_indicator=mdb.MDB_INT_16,
                            compression_indicator=0,
                            rtrie_indicator=mdb.MDB_UINT_16)
        self.assertFalse(str_column.is_trie)

        str_column = Column(_NAME, None, index_indicator=False, partition=False,
                            type_indicator=mdb.MDB_STR,
                            compression_indicator=1,
                            rtrie_indicator=mdb.MDB_UINT_16)
        self.assertFalse(str_column.is_trie)

    def test_schema_string(self):
        c = Column(_NAME, None, index_indicator=False, partition=False,
                   type_indicator=mdb.MDB_UINT_16, compression_indicator=0,
                   rtrie_indicator=mdb.MDB_UINT_16)
        self.assertEqual(c.schema_string(), "%s%s" % ('@2', _NAME))

        c.type_indicator = mdb.MDB_INT_16
        self.assertEqual(c.schema_string(), "%s%s" % ('#2', _NAME))
        c.type_indicator = mdb.MDB_INT_32
        self.assertEqual(c.schema_string(), "%s%s" % ('#4', _NAME))
        c.type_indicator = mdb.MDB_UINT_32
        self.assertEqual(c.schema_string(), "%s%s" % ('@4', _NAME))
        c.type_indicator = mdb.MDB_INT_64
        self.assertEqual(c.schema_string(), "%s%s" % ('#8', _NAME))
        c.type_indicator = mdb.MDB_UINT_64
        self.assertEqual(c.schema_string(), "%s%s" % ('@8', _NAME))

        c.type_indicator = mdb.MDB_STR
        c.compression_indicator = 0
        self.assertEqual(c.schema_string(), "%s%s" % ('%2', _NAME))
        c.rtrie_indicator = mdb.MDB_UINT_32
        self.assertEqual(c.schema_string(), "%s%s" % ('%4', _NAME))
        c.compression_indicator = 1
        self.assertEqual(c.schema_string(), "%s%s" % ('$', _NAME))
        c.compression_indicator = 2
        self.assertEqual(c.schema_string(), "%s%s" % ('*', _NAME))

    def test_get_effective_inttype(self):
        c = Column(_NAME, None, index_indicator=False, partition=False,
                   type_indicator=mdb.MDB_UINT_16, compression_indicator=0,
                   rtrie_indicator=mdb.MDB_INT_16)
        self.assertEqual(c.get_effective_inttype(), mdb.MDB_UINT_16)

        c.type_indicator = mdb.MDB_STR
        self.assertEqual(c.get_effective_inttype(), mdb.MDB_INT_16)

    def test_check_range_query_for_trie(self):
        c = Column(_NAME, None, index_indicator=1, partition=False,
                   type_indicator=mdb.MDB_STR, compression_indicator=0,
                   rtrie_indicator=mdb.MDB_INT_16)
        with self.assertRaises(TypeError):
            c < "foo"
        with self.assertRaises(TypeError):
            c <= "foo"
        with self.assertRaises(TypeError):
            c > "foo"
        with self.assertRaises(TypeError):
            c >= "foo"
        c == "foo"
        c != "foo"

    def test_check_range_query_for_lz4(self):
        c = Column(_NAME, None, index_indicator=1, partition=False,
                   type_indicator=mdb.MDB_STR, compression_indicator=2,
                   rtrie_indicator=None)
        with self.assertRaises(TypeError):
            c < "foo"
        with self.assertRaises(TypeError):
            c <= "foo"
        with self.assertRaises(TypeError):
            c > "foo"
        with self.assertRaises(TypeError):
            c >= "foo"
        c == "foo"
        c != "foo"

    def test_check_range_query_for_partition(self):
        c = Column(_NAME, None, index_indicator=1, partition=True,
                   type_indicator=mdb.MDB_STR, compression_indicator=1,
                   rtrie_indicator=None)
        c < "foo"
        c <= "foo"
        c > "foo"
        c >= "foo"
        c == "foo"
        c != "foo"

    def test_check_range_query(self):
        c = Column(_NAME, None, index_indicator=True, partition=False,
                   type_indicator=mdb.MDB_INT_16, compression_indicator=1,
                   rtrie_indicator=None)
        c < 1
        c <= 1
        c > 1
        c >= 1
        c == 1
        c != 1

########NEW FILE########
__FILENAME__ = test_expression
import unittest
from hustle.core.marble import Column
from pyebset import BitSet


ZERO_BS = BitSet()
ZERO_BS.set(0)


class Tablet(object):
    def __init__(self, l=()):
        self.l = BitSet()
        for i in l:
            self.l.set(i)

    def iter_all(self):
        return iter(self.l)

    def bit_eq(self, col, other):
        b = BitSet()
        for i in self.l:
            if i == other:
                b.set(i)
        return b

    def bit_ne(self, col, other):
        b = BitSet()
        for i in self.l:
            if i != other:
                b.set(i)
        return b

    def bit_lt(self, col, other):
        b = BitSet()
        for i in self.l:
            if i < other:
                b.set(i)
        return b

    def bit_gt(self, col, other):
        b = BitSet()
        for i in self.l:
            if i > other:
                b.set(i)
        return b

    def bit_ge(self, col, other):
        b = BitSet()
        for i in self.l:
            if i >= other:
                b.set(i)
        return b

    def bit_le(self, col, other):
        b = BitSet()
        for i in self.l:
            if i <= other:
                b.set(i)
        return b

    def bit_eq_ex(self, col, keys):
        rval = BitSet()
        for i in self.l:
            if i in keys:
                rval.set(i)
        return rval

    def bit_ne_ex(self, col, keys):
        rval = BitSet()
        for i in self.l:
            if i not in keys:
                rval.set(i)
        return rval


class TestExpr(unittest.TestCase):
    def test_expr_without_partitions(self):
        cee_vals = Tablet([1, 5, 7, 9, 12, 13, 14, 19, 27, 38])
        cee = Column('cee', None, type_indicator=1, index_indicator=1, partition=False)

        ex = (cee < 8)
        self.assertEqual(list(ex(cee_vals)), [1, 5, 7])

        ex = (cee > 7)
        self.assertEqual(list(ex(cee_vals)), [9, 12, 13, 14, 19, 27, 38])

        ex = (cee <= 7)
        self.assertEqual(list(ex(cee_vals)), [1, 5, 7])

        ex = (cee >= 7)
        self.assertEqual(list(ex(cee_vals)), [7, 9, 12, 13, 14, 19, 27, 38])

        ex = (cee == 7)
        self.assertEqual(list(ex(cee_vals)), [7])

        ex = (cee != 7)
        self.assertEqual(list(ex(cee_vals)), [1, 5, 9, 12, 13, 14, 19, 27, 38])

        # test AND
        ex = (cee > 7) & (cee < 20)
        self.assertEqual(list(ex(cee_vals)), [9, 12, 13, 14, 19])

        ex = (cee > 7) & (cee < 20) & (cee > 13)
        self.assertEqual(list(ex(cee_vals)), [14, 19])

        # test OR
        ex = (cee < 7) | (cee > 20)
        x = sorted(ex(cee_vals))
        self.assertEqual(x, [1, 5, 27, 38])

        ex = (cee == 7) | (cee == 20) | (cee == 13)
        self.assertEqual(list(ex(cee_vals)), [7, 13])

        # test NOT
        ex = ~((cee >= 7) & (cee <= 20))
        x = sorted(ex(cee_vals))
        self.assertEqual(x, [1, 5, 27, 38])

        # test NOT
        ex = ~((cee < 7) | (cee == 19))
        x = sorted(ex(cee_vals))
        self.assertEqual(x, [7, 9, 12, 13, 14, 27, 38])

        # test in
        ex = (cee << [1, 5])
        self.assertEqual(list(ex(cee_vals)), [1, 5])
        ex = (cee << [1, 3, 5, 7])
        self.assertEqual(list(ex(cee_vals)), [1, 5, 7])
        ex = (cee << [1, 5, 7]) & (cee > 4)
        self.assertEqual(list(ex(cee_vals)), [5, 7])

        # test not in
        ex = (cee >> [1, 5, 7, 9])
        self.assertEqual(list(ex(cee_vals)), [12, 13, 14, 19, 27, 38])
        ex = (cee >> [1, 3, 5, 7, 9, 12, 15, 19])
        self.assertEqual(list(ex(cee_vals)), [13, 14, 27, 38])

        # test in & not in
        ex = (cee << [1, 5, 7]) & (cee >> [3, 7])
        self.assertEqual(list(ex(cee_vals)), [1, 5])
        ex = (cee << [1, 5, 7]) & (cee >> [3, 7]) & (cee >> [1, 5])
        self.assertEqual(list(ex(cee_vals)), [])
        ex = (cee << [1, 5, 7]) & (cee >> [3, 7]) | (cee >> [1, 5])
        self.assertEqual(list(ex(cee_vals)), [1, 5, 7, 9, 12, 13, 14, 19, 27, 38])
        ex = (cee << [1, 5, 7]) & (cee >> [3, 7]) | (cee == 9)
        self.assertEqual(list(ex(cee_vals)), [1, 5, 9])

    def test_expr_with_partitions(self):
        pee = Column('pee', None, type_indicator=1, index_indicator=1, partition=True)
        pee_tags = [1, 5, 7, 9, 12, 13, 14, 19, 27, 38]
        cee = Column('cee', None, type_indicator=1, index_indicator=1, partition=False)

        p_and_p = (pee < 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [1, 5])

        p_and_p = (pee > 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [9, 12, 13, 14, 19, 27, 38])

        p_and_p = (pee == 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7])

        p_and_p = (pee != 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [1, 5, 9, 12, 13, 14, 19, 27, 38])

        p_and_p = (pee >= 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])

        p_and_p = (pee <= 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [1, 5, 7])

        p_and_p = ~(pee > 7)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [1, 5, 7])

        # test pure partition combination
        p_and_p = (pee > 5) | (pee == 1)
        self.assertEqual(sorted(p_and_p.partition(pee_tags)), [1, 7, 9, 12, 13, 14, 19, 27, 38])

        p_and_p = ~((pee <= 5) | (pee > 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14])

        p_and_p = (pee == 5) | (pee == 99)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [5])

        p_and_p = (pee > 5) & (pee <= 14) & (pee > 12)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [13, 14])

        p_and_p = ((pee > 5) & (pee <= 14)) | (pee == 5)
        x = sorted(p_and_p.partition(pee_tags))
        self.assertEqual(x, [5, 7, 9, 12, 13, 14])

        p_and_p = ~(~(((pee > 5) & (pee <= 14))) & (pee != 5))
        x = sorted(p_and_p.partition(pee_tags))
        self.assertEqual(x, [5, 7, 9, 12, 13, 14])

        p_and_p = ~(((pee <= 5) | (pee > 14)) & (pee != 5))
        x = sorted(p_and_p.partition(pee_tags))
        self.assertEqual(x, [5, 7, 9, 12, 13, 14])

        # test combined partition/index combinations
        # p & c == p
        p_and_p = (pee > 5) & (cee <= 14)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])

        # test combined partition/index combinations
        # p & ~c == p
        p_and_p = (pee > 5) & ~(cee <= 14)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])
        p_and_p = (pee > 5) & ~~(cee <= 14)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])

        # p & ~c & ~c == p
        p_and_p = (pee > 5) & ~(cee <= 14) & ~(cee >= 5)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])
        p_and_p = (cee > 5) & ~((pee > 5) & ~(cee <= 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), [1, 5])
        p_and_p = (cee > 5) & (~(pee > 5) & ~(cee <= 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), [1, 5])
        p_and_p = (cee > 5) & ~(~(pee > 5) & ~(cee <= 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])
        p_and_p = (cee > 5) & ~~((pee > 5) & ~(cee <= 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])
        p_and_p = (cee > 5) & ~((pee > 5) | ~(cee <= 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), pee_tags)
        p_and_p = (cee > 5) & ~~((pee > 5) | ~(cee <= 14))
        self.assertEqual(list(p_and_p.partition(pee_tags)), pee_tags)

        # p & ~c | ~c == all
        p_and_p = (pee > 5) & ~(cee <= 14) | ~(cee >= 5)
        self.assertEqual(list(p_and_p.partition(pee_tags)), pee_tags)

        # ~c & ~c & p == p
        p_and_p = ~(cee <= 14) & ~(cee >= 5) & (pee > 5)
        self.assertEqual(list(p_and_p.partition(pee_tags)), [7, 9, 12, 13, 14, 19, 27, 38])

        # p | c == universe
        p_and_p = (pee == 5) | (pee == 8) | (cee == 99)
        x = list(p_and_p.partition(pee_tags))
        self.assertEqual(x, pee_tags)

        p_and_p = (pee == 5) | (pee == 8) | (cee == 99)
        x = list(p_and_p.partition(pee_tags))
        self.assertEqual(x, pee_tags)

        # p | c == universe
        p_and_p = ((pee == 5) | (pee > 14)) | (cee > 12)
        self.assertEqual(list(p_and_p.partition(pee_tags)), pee_tags)

        # c & p == p ==> p | p
        p_and_p = ((pee == 5) | (pee > 14)) | ((cee > 12) & (pee == 1))
        self.assertEqual(sorted(p_and_p.partition(pee_tags)), [1, 5, 19, 27, 38])

########NEW FILE########
__FILENAME__ = test_lru_dict
import mdb
import os
import unittest
from functools import partial
from hustle.core.marble import mdb_evict, mdb_fetch
from pylru import LRUDict
from pylru import CharLRUDict, IntLRUDict
from pyebset import BitSet

class TestLRUDict(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        try:
            os.unlink('/tmp/lru_test')
            os.unlink('/tmp/lru_test-lock')
        except:
            pass

    def test_lru(self):
        def get(db, txn, key):
            try:
                return db.get(txn, key)
            except:
                return None

        env = mdb.Env('/tmp/lru_test', flags=mdb.MDB_WRITEMAP | mdb.MDB_NOSYNC | mdb.MDB_NOSUBDIR)
        txn = env.begin_txn()
        ixdb = env.open_db(txn, 'ix', flags=mdb.MDB_CREATE)

        lru = LRUDict.getDict(5,
                      partial(mdb_fetch, txn=txn, ixdb=ixdb),
                      partial(mdb_evict, txn=txn, ixdb=ixdb))

        lru.set('hello', BitSet())
        lru.set('goodbye', BitSet())
        lru.set('amine', BitSet())
        lru.set('solution', BitSet())
        lru.set('lsd', BitSet())
        self.assertEqual(len(lru._getContents()), 5)

        lru.set('proxy', BitSet())
        store = lru._getContents()
        self.assertNotIn('hello', store)
        self.assertIsNotNone(get(ixdb, txn, 'hello'))
        self.assertEqual(len(store), 5)

        bitmap = lru['hello']
        store = lru._getContents()
        self.assertIn('hello', store)
        self.assertEqual(len(store), 5)
        self.assertIsInstance(bitmap, BitSet)
        self.assertIsNone(lru.get('skibiddles'))

        # test eviction order
        self.assertIsNotNone(lru.get('goodbye')) # this now should 'reset' goodbye so that it won't be evicted
        lru.set('whammy bar', BitSet()) # amine should be evicted
        store = lru._getContents()
        self.assertNotIn('amine', store)
        self.assertIn('goodbye', store)

        txn.commit()
        env.close()

class LruTest(unittest.TestCase):
    def test_basic_char(self):
        mdict = {}

        def fetch(key):
            try:
                res = mdict[key]
            except:
                return None
            return res

        def evict(key, value):
            mdict[key] = value

        l = CharLRUDict(10, fetch, evict)

        a = 100000
        b = 200000

        for i in range(a, b):
            l.set(str(i * i), i * i)

        for i in range(b - 1, a, -1):
            v = l.get(str(i * i))
            self.assertEqual(i * i, v)

    def test_basic_int(self):
        mdict = {}

        def fetch(key):
            try:
                res = mdict[key]
            except:
                return None
            return res

        def evict(key, value):
            mdict[key] = value

        l = IntLRUDict(10, fetch, evict)

        a = 100000
        b = 200000

        for i in range(a , b):
            l.set(i * i, i * i)

        for i in range(b - 1, a, -1):
            v = l.get(i * i)
            self.assertEqual(i * i, v)

    def test_no_eviction(self):
        def fetch(key):
            return None

        def evict(key, value):
            self.fail("Nothing should be evicted: " + str(key) + " " + str(value))

        l = CharLRUDict(1, fetch, evict, list)
        s = l["10"]
        self.assertListEqual(s, [])

########NEW FILE########
__FILENAME__ = test_marble
import unittest
import ujson
import os
import rtrie
import mdb
from pyebset import BitSet
from hustle.core.marble import Marble, MarbleStream
import clz4

_FIELDS_RAW = ("id", "name", "artist", "date", "quantity", "genre", "rating")
_FIELDS = ("+@4id", "+*name", "+$date", "+%2genre", "+@2rating", "artist", "@4quantity")
_PARTITIONS = "date"
_ALBUMS = [
    (1000, "Metallica", "Metallica", "1992-10-03", 5000000, "R&R", 5),
    (1001, "Reload", "Metallica", "1992-10-03", 2000000, "R&R", 4),
    (1002, "Use Your Imagination", "Guns&Roses", "1992-10-03", 4000000, "R&R", 5),
    (1003, "Come As You Are", "Nirvana", "1992-10-03", 6000000, "R&R", 5),
    (1004, "Pianist", "Ennio Morricone", "1986-01-03", 200000, "SoundTrack", 5),
    (1005, "The Good, The Bad, and The Ugly", "Ennio Morricone", "1986-01-03", 400000, "SoundTrack", 5),
    (1006, "Once Upon A Time In America", "Ennio Morricone", "1986-01-03", 1200000, "SoundTrack", 5),
    (1007, "Cinema Paradise", "Ennio Morricone", "1986-01-03", 50000, "SoundTrack", 4),
    (1008, "Taxi Driver", "Ennio Morricone", "1986-01-03", 300000, "SoundTrack", 5),
    (1009, "Once Upon A Time In The West", "Ennio Morricone", "1986-01-03", 1200000, "SoundTrack", 3),
]
_NPARTITIONS = 2  # Only two unique values for date


class TestMarble(unittest.TestCase):
    def setUp(self):
        self.albums = [dict(zip(_FIELDS_RAW, album)) for album in _ALBUMS]
        self.marble = Marble(name="Collections",
                             fields=_FIELDS,
                             partition=_PARTITIONS)
        self.n_inserted, self.files = self.marble._insert([(ujson.dumps(l) for l in self.albums)])

    def tearDown(self):
        for date, file in self.files.iteritems():
            os.unlink(file)

    def test_field_names(self):
        self.assertListEqual(sorted(list(_FIELDS_RAW)), sorted(self.marble._field_names))

    def test_marble_insert(self):
        #  test general infomation
        self.assertEqual(self.n_inserted, len(_ALBUMS))
        self.assertEqual(_NPARTITIONS, len(self.files))
        part_id = {}
        #  test that each sub db is fine
        for date, file in self.files.iteritems():
            env, txn, dbs, meta = self.marble._open(file)
            #  check meta db
            self.assertTrue(meta.contains(txn, "_vid_nodes"))
            self.assertTrue(meta.contains(txn, "_vid_kids"))
            self.assertTrue(meta.contains(txn, "_vid16_nodes"))
            self.assertTrue(meta.contains(txn, "_vid16_kids"))
            self.assertEqual(meta.get(txn, "name"), ujson.dumps("Collections"))
            self.assertEqual(meta.get(txn, "partition"), ujson.dumps("date"))
            self.assertEqual(meta.get(txn, "fields"), ujson.dumps(_FIELDS))
            self.assertEqual(meta.get(txn, "_pdata"), ujson.dumps(date))
            vid_nodes, _ = meta.get_raw(txn, '_vid_nodes')
            vid_kids, _ = meta.get_raw(txn, '_vid_kids')
            vid16_nodes, _ = meta.get_raw(txn, '_vid16_nodes', (None, 0))
            vid16_kids, _ = meta.get_raw(txn, '_vid16_kids', (None, 0))
            #  check subdb, subinddb
            part_id[date] = 1
            for name, (db, ind_db, _, column, _) in dbs.iteritems():
                if name == "_count":
                    continue
                bitmaps = {}
                part_id[date] = 1
                for album in self.albums:
                    if date == album[_PARTITIONS]:  # match the partition
                        value = album[name]
                        i = part_id[album[_PARTITIONS]]
                        part_id[album[_PARTITIONS]] += 1
                        if column.is_trie:
                            if column.rtrie_indicator == mdb.MDB_UINT_16:
                                val = rtrie.vid_for_value(vid16_nodes, vid16_kids, value)
                            else:
                                val = rtrie.vid_for_value(vid_nodes, vid_kids, value)
                        elif column.is_lz4:
                            val = clz4.compress(value)
                        else:
                            val = value
                        # self.assertEqual(db.get(txn, i), val)
                        if ind_db is not None:
                            #  row_id should be in bitmap too
                            if val in bitmaps:
                                bitmap = bitmaps[val]
                            else:
                                bitmap = BitSet()
                                bitmap.loads(ind_db.get(txn, val))
                                bitmaps[val] = bitmap
                            self.assertTrue(i in bitmap)
            txn.commit()
            env.close()

    def test_marble_stream_get(self):
        for date, file in self.files.iteritems():
            stream = MarbleStream(file)
            rowid = 1
            for album in self.albums:
                if album[_PARTITIONS] != date:
                    continue
                # test 'get' first
                for k, v in album.iteritems():
                    self.assertEqual(v, stream.get(k, rowid))
                rowid += 1
            stream.close()

    def test_marble_stream_bit_ops(self):
        stream = MarbleStream(self.files["1992-10-03"])
        rowid = 1
        # test "name" index
        for album in self.albums:
            if album[_PARTITIONS] != "1992-10-03":
                continue
            bitset = stream.bit_eq("name", album["name"])
            bs = BitSet()
            bs.set(rowid)
            rowid += 1
            for i in bitset:
                self.assertTrue(i in bs)
        # test "genre" index
        bitset = stream.bit_eq("genre", "R&R")
        bs = BitSet()
        for i in range(1, 5):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        stream.close()

        stream = MarbleStream(self.files["1986-01-03"])
        rowid = 1
        # test "name" index
        for album in self.albums:
            if album[_PARTITIONS] != "1986-01-03":
                continue
            bitset = stream.bit_eq("name", album["name"])
            bs = BitSet()
            bs.set(rowid)
            rowid += 1
            for i in bitset:
                self.assertTrue(i in bs)
        # test "genre" index
        bitset = stream.bit_eq("genre", "SoundTrack")
        bs = BitSet()
        for i in range(1, 7):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        # test "rating" index
        # test for eq and not-eq
        bitset = stream.bit_eq("rating", 4)
        bs = BitSet()
        bs.set(4)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_eq("rating", 3)
        bs = BitSet()
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_eq("rating", 5)
        bs = BitSet()
        for i in range(1, 4):
            bs.set(i)
        bs.set(5)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ne("rating", 5)
        bs = BitSet()
        bs.set(4)
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ne("rating", 3)
        bs = BitSet()
        for i in range(1, 6):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ne("rating", 4)
        bs = BitSet()
        for i in range(1, 4):
            bs.set(i)
        bs.set(5)
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        # test "rating" index
        # test for eq_ex and not_eq_ex
        bitset = stream.bit_eq_ex("rating", [3, 4])
        bs = BitSet()
        bs.set(4)
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_eq_ex("rating", [5])
        bs = BitSet()
        for i in range(1, 4):
            bs.set(i)
        bs.set(5)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ne_ex("rating", [5])
        bs = BitSet()
        bs.set(4)
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ne_ex("rating", [3, 4])
        bs = BitSet()
        for i in range(1, 4):
            bs.set(i)
        bs.set(5)
        for i in bitset:
            self.assertTrue(i in bs)

        # test for less_than and less_eq
        bitset = stream.bit_ge("rating", 3)
        bs = BitSet()
        for i in range(1, 7):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_gt("rating", 3)
        bs = BitSet()
        for i in range(1, 6):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_le("rating", 3)
        bs = BitSet()
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_lt("rating", 3)
        bs = BitSet()
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_lt("rating", 5)
        bs = BitSet()
        bs.set(4)
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_le("rating", 5)
        bs = BitSet()
        for i in range(1, 7):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_gt("rating", 5)
        bs = BitSet()
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ge("rating", 5)
        bs = BitSet()
        for i in range(1, 4):
            bs.set(i)
        bs.set(5)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_le("rating", 4)
        bs = BitSet()
        bs.set(4)
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_lt("rating", 4)
        bs = BitSet()
        bs.set(6)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_ge("rating", 4)
        bs = BitSet()
        for i in range(1, 6):
            bs.set(i)
        for i in bitset:
            self.assertTrue(i in bs)

        bitset = stream.bit_gt("rating", 4)
        bs = BitSet()
        for i in range(1, 4):
            bs.set(i)
        bs.set(5)
        for i in bitset:
            self.assertTrue(i in bs)

        stream.close()


class TestInsertPartitionFilter(unittest.TestCase):
    def test_partition_numbers(self):
        self.albums = [dict(zip(_FIELDS_RAW, album)) for album in _ALBUMS]
        self.marble = Marble(name="Collections",
                             fields=_FIELDS,
                             partition=_PARTITIONS)
        self.n_inserted, self.files = self.marble._insert([(ujson.dumps(l) for l in self.albums)],
                                                          partition_filter='1992-10-03')
        self.assertEquals(len(self.files), 1)
        inserted = len([1 for album in self.albums if album['date'] == '1992-10-03'])
        self.assertEquals(inserted, self.n_inserted)

        for date, file in self.files.iteritems():
            os.unlink(file)

    def test_partition_numbers_set(self):
        self.albums = [dict(zip(_FIELDS_RAW, album)) for album in _ALBUMS]
        self.marble = Marble(name="Collections",
                             fields=_FIELDS,
                             partition=_PARTITIONS)
        self.n_inserted, self.files = self.marble._insert([(ujson.dumps(l) for l in self.albums)],
                                                          partition_filter=['1992-10-03', '1986-01-03'])
        self.assertEquals(len(self.files), 2)
        inserted = len([1 for album in self.albums if album['date'] == '1992-10-03' or
                        album['date'] == '1986-01-03'])
        self.assertEquals(inserted, self.n_inserted)

        for date, file in self.files.iteritems():
            os.unlink(file)

########NEW FILE########
__FILENAME__ = test_merge_wrapper
import unittest
from hustle.core.pipeworker import merge_wrapper


class TestMarble(unittest.TestCase):
    def test_up(self):
        a = [(('keya', 5), 22), (('lima', 9), 23), (('oebra', 21), 24), (('qeya', 5), 22), (('tima', 9), 23), (('zebra', 21), 24)]
        b = [(('aeya', 5), 22), (('fima', 12), 23), (('hebra', 8), 24), (('xya', 5), 22), (('yima', 12), 23), (('zzebra', 8), 24)]
        c = [(('beya', 5), 22), (('fliea', 9), 23), (('gray', 21), 24), (('morie', 5), 22), (('steel', 9), 23), (('yale', 21), 24)]
        d = [(('vera', 5), 22), (('wera', 12), 23), (('xera', 8), 24), (('yolanda', 5), 22), (('yolo', 12), 23), (('zanadu', 8), 24)]
        from heapq import merge
        res = merge(merge_wrapper(a), merge_wrapper(b), merge_wrapper(c), merge_wrapper(d))
        lowest = 'aaaaaa'
        for k, v in res:
            self.assertTrue(lowest < k[0])
            lowest = k[0]

    def test_down(self):
        a = [(('zebra', 21), 24), (('lima', 9), 23), (('keya', 5), 22), ]
        b = [(('zzebra', 8), 24), (('sima', 12), 23), (('aeya', 5), 22)]
        from heapq import merge
        res = merge(merge_wrapper(a, desc=True), merge_wrapper(b, desc=True))
        highest = 'zzzzzzzzz'
        for k, v in res:
            self.assertTrue(highest > k[0])
            highest = k[0]

    def test_nulls(self):
        a = [(('zebra', 21), 24), (('keya', 5), 22), ((None, 9), 23)]
        b = [(('zzebra', 8), 24), (('sima', 12), 23), (('aeya', 5), 22), ((None, 12), 18)]
        from heapq import merge
        res = merge(merge_wrapper(a, desc=True), merge_wrapper(b, desc=True))
        highest = 'zzzzzzzzz'
        for k, v in res:
            print k, v
            self.assertTrue(highest >= k[0])
            highest = k[0]

    def test_multi(self):
        a = [(('zebra', 12), 24), (('webra', 12), 24), (('bebra', 12), 24), (('aebra', 12), 24), (('zebra', 11), 24), (('keya', 5), 22), (('aeya', 5), 22), ]
        b = [(('sima', 12), 23), (('zzebra', 8), 28), (('yzebra', 8), 28), (('azebra', 8), 28), (('aeya', 5), 22)]
        from heapq import merge
        res = merge(merge_wrapper(a, sort_range=(1, 0), desc=True), merge_wrapper(b, sort_range=(1, 0), desc=True))
        highest = 999999999
        highest_2nd = 'zzzzzzzz'
        same_count = 0
        for k, v in res:
            print "kev", k, v
            if highest == k[1]:
                self.assertTrue(highest_2nd >= k[0])
                same_count += 1
            self.assertGreaterEqual(highest, k[1])
            highest = k[1]
            highest_2nd = k[0]
        self.assertEqual(same_count, 8)

    def test_lopsided(self):
        a = [(('zebra', 21), 24)]
        b = [(('zzebra', 8), 24), (('sima', 12), 23), (('aeya', 5), 22)]
        from heapq import merge
        res = merge(merge_wrapper(a, desc=True), merge_wrapper(b, desc=True))
        highest = 'zzzzzzzzz'
        for k, v in res:
            self.assertTrue(highest > k[0])
            highest = k[0]





########NEW FILE########
__FILENAME__ = test_pipeline
import unittest
from hustle.core.pipeline import SelectPipe, _get_sort_range
from hustle.core.marble import Marble

EMP_FIELDS = ("+@2id", "+$name", "+%2hire_date", "+@4salary", "+@2department_id")
DEPT_FIELDS = ("+@2id", "+%2name", "+%2building", "+@2manager_id")


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.emp = Marble(name="employee",
                          fields=EMP_FIELDS)
        self.dept = Marble(name="department",
                           fields=DEPT_FIELDS)

    def test_get_key_names(self):
        wheres = [(self.emp.salary > 25000), self.dept]
        project = [self.emp.name, self.emp.salary, self.dept.building]

        pipe = SelectPipe('server', wheres=wheres, project=project)
        self.assertTupleEqual(('name', 'salary', None), tuple(pipe._get_key_names(project, ())[0]))
        self.assertTupleEqual((None, None, 'building'), tuple(pipe._get_key_names(project, ())[1]))

        join = [self.dept.id, self.emp.department_id]
        pipe = SelectPipe('server', wheres=wheres, project=project, join=join)
        self.assertTupleEqual(('department_id', 'name', 'salary', None), tuple(pipe._get_key_names(project, join)[0]))
        self.assertTupleEqual(('id', None, None, 'building'), tuple(pipe._get_key_names(project, join)[1]))

        project = [self.dept.building, self.emp.name, self.emp.salary]
        pipe = SelectPipe('server', wheres=wheres, project=project, join=join)
        self.assertTupleEqual(('department_id', None, 'name', 'salary'), tuple(pipe._get_key_names(project, join)[0]))
        self.assertTupleEqual(('id', 'building', None, None), tuple(pipe._get_key_names(project, join)[1]))

    def test_get_sort_range(self):
        project = [self.emp.name, self.emp.salary, self.dept.building]
        order_by = []

        # first case is with an empty order_by, it should sort by all columns
        sort_range = _get_sort_range(2, project, order_by)
        self.assertTupleEqual(tuple(sort_range), (2, 3, 4))
        sort_range = _get_sort_range(0, project, order_by)
        self.assertTupleEqual(tuple(sort_range), (0, 1, 2))

        # test with a specified order_by, note that we should always be sorting all columns - the order_by
        # just specifies the order.  The unspecified columns are not in a defined order.
        order_by = [self.emp.salary]
        sort_range = _get_sort_range(2, project, order_by)
        self.assertEqual(len(sort_range), 3)
        self.assertEqual(sort_range[0], 3)

        order_by = [self.dept.building, self.emp.name]
        sort_range = _get_sort_range(1, project, order_by)
        self.assertEqual(len(sort_range), 3)
        self.assertTupleEqual(sort_range[:2], (3, 1))

    def test_get_pipeline(self):
        wheres = [(self.emp.salary > 25000), self.dept]
        project = [self.emp.name, self.emp.salary, self.dept.building]

        pipe = SelectPipe('server',
                          wheres=wheres,
                          project=project)
        #(SPLIT, HustleStage('restrict-project',
        #                            process=partial(process_restrict, jobobj=job),
        #                            input_chain=[partial(hustle_stream, jobobj=job)]))
        pipeline = pipe.pipeline
        self.assertEqual(len(pipeline), 1)
        self.assertEqual('split', pipeline[0][0])
        self.assertEqual('restrict-select', pipeline[0][1].name)

        order_by = [self.dept.building, self.emp.name]
        pipe = SelectPipe('server',
                          wheres=wheres,
                          project=project,
                          order_by=order_by)
        #(SPLIT, HustleStage('restrict-project',
        #                            process=partial(process_restrict, jobobj=job),
        #                            input_chain=[partial(hustle_stream, jobobj=job)])),
        #(GROUP_LABEL, HustleStage('order',
        #                          process=partial(process_order, jobobj=job, distinct=job.distinct),
        #                          sort=sort_range))]

        pipeline = pipe.pipeline
        self.assertEqual(len(pipeline), 3)
        self.assertEqual('split', pipeline[0][0])
        self.assertEqual('group_node_label', pipeline[1][0])
        self.assertEqual('order-combine', pipeline[1][1].name)

        order_by = [self.dept.building, self.emp.name]
        join = [self.dept.id, self.emp.department_id]
        pipe = SelectPipe('server',
                          wheres=wheres,
                          project=project,
                          order_by=order_by,
                          join=join)
        pipeline = pipe.pipeline
        self.assertEqual(len(pipeline), 4)
        self.assertEqual('split', pipeline[0][0])
        self.assertEqual('group_label', pipeline[1][0])
        self.assertEqual('join', pipeline[1][1].name)
        self.assertEqual('group_all', pipeline[3][0])
        self.assertEqual('order-reduce', pipeline[3][1].name)

    def test_column_aliases_project(self):
        wheres = [(self.emp.salary > 25000), self.dept]
        project = [self.emp.name, self.emp.salary, self.dept.building, self.dept.name]
        order_by = ['name', 'employee.salary', self.dept.building, 3]
        join = [self.emp.name, self.dept.name]

        pipe = SelectPipe('server',
                          wheres=wheres,
                          project=project,
                          order_by=order_by,
                          join=join)

        self.assertEqual(len(pipe.order_by), 4)
        self.assertEqual(pipe.order_by[0], self.emp.name)
        self.assertEqual(pipe.order_by[1], self.emp.salary)
        self.assertEqual(pipe.order_by[2], self.dept.building)
        self.assertEqual(pipe.order_by[0], self.dept.name)

########NEW FILE########
__FILENAME__ = test_pipeworker
import unittest
from hustle.core.pipeworker import sort_reader, disk_sort
from StringIO import StringIO
import os

OUT_FILE = '/tmp/test_disk_sort'

TEST_FILE = \
    b"stuff\xff19\xffvalue1\x00" \
    b"morestuff\xff29\xffvalue2\x00" \
    b"reallylongkeyprobablylongerthanthebufferljkfdskjlkjjkjkjjjjjjjjjjjjjsfddfsfdsdfsdfsfdsfdsdfsfdsfdsdsffdsdfsdfsfdsdfsdfsdfsdfsfdsdsfdfsfdsfdsdsfdsffdsdfsdsfdsfdfsdfsfdssdfdfsdfsdfsdfsdfsfdsfdssdfdfs\xff15\xfffinalvalue\x00"\

EXPECTED = [
    (["stuff", "19"], "value1"),
    (["morestuff", "29"], "value2"),
    (["reallylongkeyprobablylongerthanthebufferljkfdskjlkjjkjkjjjjjjjjjjjjjsfddfsfdsdfsdfsfdsfdsdfsfdsfdsdsffdsdfsdfsfdsdfsdfsdfsdfsfdsdsfdfsfdsfdsdsfdsffdsdfsdsfdsfdfsdfsfdssdfdfsdfsdfsdfsdfsfdsfdssdfdfs", "15"], "finalvalue"),
]

RESPECTED = [
    (["stuff", 1900], 'value1'),
    (["morestuff", 9], 'value2'),
    (["anymore", 290], 'value3'),
    (["stuff", 29], 'value4'),
    (["toeat", 1500], 'value5'),
    (["reallystuff", 15], 'finalvalue'),
]


SOMENULLS = [
    (["olay", 1900], 'value1'),
    (["morestuff", 9], 'value2'),
    (["anymore", 290], 'value3'),
    ([None, 29], 'value4'),
    (["toeat", 1500], 'value5'),
    (["reallystuff", 15], 'finalvalue'),
]


class TestPipeworker(unittest.TestCase):
    def setUp(self):
        pass

    def _clean_ds_tmp(self):
        try:
            os.unlink(OUT_FILE)
        except:
            pass

    def test_sort_reader(self):
        for buf_size in [8, 16, 32, 64, 256, 8192]:
            infile = StringIO(TEST_FILE)
            for actual, expected in zip(sort_reader(infile, 'test', buf_size), EXPECTED):
                self.assertListEqual(actual[0], expected[0])
                self.assertEqual(actual[1], expected[1])

    def test_simple_disk_sort(self):
        self._clean_ds_tmp()
        actual = [(key, value) for key, value in disk_sort(RESPECTED, OUT_FILE, (0, 1))]
        print "ACTUAL: ", actual
        self.assertEqual(actual[0][0][0], "anymore")
        self.assertEqual(actual[1][0][1], 9)
        self.assertEqual(actual[2][0][0], "reallystuff")
        self.assertEqual(actual[3][1], ()) # tests secondary sorting

    def test_positional_disk_sort(self):
        self._clean_ds_tmp()
        actual = [(key, value) for key, value in disk_sort(RESPECTED, OUT_FILE, [1])]
        print "ACTUAL: ", actual
        self.assertEqual(actual[0][0][0], "morestuff")
        self.assertEqual(actual[1][0][1], 15)
        self.assertEqual(actual[2][0][0], "stuff")
        self.assertEqual(actual[3][1], ())
        self.assertEqual(actual[5][1], ())

    def test_nulls(self):
        self._clean_ds_tmp()
        actual = [(key, value) for key, value in disk_sort(SOMENULLS, OUT_FILE, [0])]
        print "ACTUAL: ", actual
        self.assertEqual(actual[0][0][0], None)


########NEW FILE########
__FILENAME__ = test_query_checker
import unittest
from hustle.core.marble import Marble, check_query


_FIELDS = ("+@4id", "+*name", "+$date", "+%2genre", "+@2rating", "artist", "@4quantity")
_PARTITIONS = "date"
_FIELDS_SELL = ("+@4id", "+@4item_id", "+$date", "@4store_id", "@4quantity", "$price")


class TestChecker(unittest.TestCase):
    def setUp(self):
        self.albums = Marble(name="Albums",
                             fields=_FIELDS,
                             partition=_PARTITIONS)
        self.transaction = Marble(name="Transcation",
                                  fields=_FIELDS_SELL,
                                  partition=_PARTITIONS)
        self.single_where = [(self.albums.rating > 3)]
        self.multi_wheres = [(self.albums.rating > 3) & (self.albums.id == 1000)]
        self.cross_wheres = [self.albums.rating > 3, self.transaction.id == 1000]
        self.single_select = [self.albums.name]
        self.multi_select = [self.albums.name, self.albums.date, self.albums.rating]
        self.cross_select = [self.albums.name, self.albums.artist,
                             self.transaction.store_id, self.transaction.price]
        self.order_by = [self.albums.quantity, self.albums.rating]
        self.join = [self.albums.id, self.transaction.item_id]
        self.join_invalid = [self.albums.id, self.transaction.price]
        self.join_invalid_1 = [self.albums.id, self.albums.id]
        self.join_invalid_2 = [self.albums.id, self.transaction.price]
        self.limit_single = 100
        self.limit_single_invalid = -100

    def test_select_clauses(self):
        # test empty select
        with self.assertRaises(ValueError):
            check_query([],
                        [],
                        self.order_by,
                        None,
                        self.single_where)
        # test duplicate select
        with self.assertRaises(ValueError):
            check_query(self.single_select + self.single_select,
                        [],
                        self.order_by,
                        None,
                        self.single_where)
        self.assertTrue(check_query(self.single_select, [], [],
                                    None, self.single_where))

    def test_where_clauses(self):
        # should raise if a single table shows up in multi-wheres
        # should raise if where and select are from different tables
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        [],
                        [],
                        self.order_by,
                        [self.transaction.id == 1000])
        self.assertTrue(check_query(self.single_select, [], [],
                                    None, self.single_where))

    def test_join(self):
        # test join with single table
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        self.join,
                        [],
                        None,
                        self.single_where)

        # test invalid join
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        self.join_invalid,
                        [],
                        None,
                        self.cross_wheres)

        # test invalid join
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        self.join_invalid_1,
                        [],
                        None,
                        self.cross_wheres)

        # test invalid join
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        self.join_invalid_2,
                        [],
                        None,
                        self.cross_wheres)
        self.assertTrue(check_query(self.single_select,
                                    self.join, [], None, self.cross_wheres))

    def test_order_by(self):
        # should raise if select columns don't contain the order column
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        [],
                        self.order_by,
                        None,
                        self.single_where)
        self.assertTrue(check_query(self.single_select, [], [self.albums.name],
                                    None, self.single_where))

    def test_limit(self):
        with self.assertRaises(ValueError):
            check_query(self.single_select,
                        [],
                        [],
                        self.limit_single_invalid,
                        self.single_where)

        self.assertTrue(
            check_query(self.single_select,
                        [],
                        [],
                        self.limit_single,
                        self.single_where))

    def test_full_query(self):
        self.assertTrue(
            check_query(
                self.cross_select,
                self.join,
                self.single_select,
                self.limit_single,
                self.cross_wheres))

########NEW FILE########
__FILENAME__ = test_rtrie
# -*- coding: utf-8 -*-
import unittest
import rtrie
import mdb
from wtrie import Trie

class TestRTrie(unittest.TestCase):
    def test_rtrie_in_memory(self):

        s = unicode(u'séllsink').encode('utf-8')
        #print "HELLSINK: %s" % s

        t = Trie()
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hell'), 2)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellothere'), 3)
        self.assertEqual(t.add('good'), 4)
        self.assertEqual(t.add('goodbye'), 5)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellsink'), 6)
        self.assertEqual(t.add(s), 7)
        t.print_it()

        nodes, kids, _ = t.serialize()
        nodeaddr, nodelen = nodes.buffer_info()
        kidaddr, kidlen = kids.buffer_info()
        print "LENS %s %s" % (nodelen, kidlen)

        for i in range(8):
            val = rtrie.value_for_vid(nodeaddr, kidaddr, i)
            print "Value", i, val

        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, 'hello'), 1)
        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, 'hell'), 2)
        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, 'goodbye'), 5)
        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, 'hellsink'), 6)
        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, 'hellothere'), 3)
        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, 'good'), 4)
        self.assertEqual(rtrie.vid_for_value(nodeaddr, kidaddr, s), 7)
        self.assertIsNone(rtrie.vid_for_value(nodeaddr, kidaddr, 'notthere'))
        self.assertIsNone(rtrie.vid_for_value(nodeaddr, kidaddr, 'h'))
        self.assertIsNone(rtrie.vid_for_value(nodeaddr, kidaddr, 'he'))
        self.assertIsNone(rtrie.vid_for_value(nodeaddr, kidaddr, 'hel'))
        self.assertIsNone(rtrie.vid_for_value(nodeaddr, kidaddr, 'hells'))

    def test_rtrie_in_mdb(self):
        t = Trie()
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hell'), 2)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellothere'), 3)
        self.assertEqual(t.add('good'), 4)
        self.assertEqual(t.add('goodbye'), 5)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellsink'), 6)

        nodes, kids, _ = t.serialize()
        nodeaddr, nodelen = nodes.buffer_info()
        kidaddr, kidlen = kids.buffer_info()
        try:
            env = mdb.Env('/tmp/test_rtrie', flags=mdb.MDB_WRITEMAP | mdb.MDB_NOSYNC | mdb.MDB_NOSUBDIR)
            txn = env.begin_txn()
            db = env.open_db(txn, name='_meta_', flags=mdb.MDB_CREATE)
            db.put_raw(txn, 'nodes', nodeaddr, nodelen)
            db.put_raw(txn, 'kids', kidaddr, kidlen)

            n, ns = db.get_raw(txn, 'nodes')
            k, ks = db.get_raw(txn, 'kids')
            txn.commit()
            env.close()

            env = mdb.Env('/tmp/test_rtrie', flags=mdb.MDB_NOSYNC | mdb.MDB_NOSUBDIR)
            txn = env.begin_txn()
            db = env.open_db(txn, name='_meta_')

            n, ns = db.get_raw(txn, 'nodes')
            k, ks = db.get_raw(txn, 'kids')
            self.assertEqual(rtrie.vid_for_value(n, k, 'hello'), 1)
            self.assertEqual(rtrie.vid_for_value(n, k, 'hell'), 2)
            self.assertEqual(rtrie.vid_for_value(n, k, 'goodbye'), 5)
            self.assertEqual(rtrie.vid_for_value(n, k, 'hellsink'), 6)
            self.assertEqual(rtrie.vid_for_value(n, k, 'hellothere'), 3)
            self.assertEqual(rtrie.vid_for_value(n, k, 'good'), 4)
            self.assertIsNone(rtrie.vid_for_value(n, k, 'notthere'))

            txn.commit()
            env.close()
        finally:
            import os
            os.unlink('/tmp/test_rtrie')
            os.unlink('/tmp/test_rtrie-lock')


########NEW FILE########
__FILENAME__ = test_stress_wtrie
import unittest
import os
from wtrie import Trie
from rtrie import value_for_vid, vid_for_value


pwd = os.getcwd()
if os.path.basename(pwd) != 'test':
    fixture = os.path.join(pwd, 'test/fixtures/keys')
else:
    fixture = os.path.join(pwd, 'fixtures/keys')


class TestStressWTrie(unittest.TestCase):
    def test_stress_wtrie(self):
        ktrie = Trie()
        strie = Trie()
        etrie = Trie()

        keywords = {}
        search_terms = {}
        exchange_ids = {}

        with open(fixture) as f:
            for data in f:
                for word in data.split(' '):
                    vid = ktrie.add(word)
                    actual_vid = keywords.get(word)
                    if actual_vid is not None:
                        self.assertEqual(vid, actual_vid)
                    else:
                        keywords[word] = vid

                vid = strie.add(data)
                actual_vid = search_terms.get(data)
                if actual_vid is not None:
                    self.assertEqual(vid, actual_vid)
                else:
                    search_terms[data] = vid

        nodes, kids, nodelen = etrie.serialize()
        naddr, nlen = nodes.buffer_info()
        kaddr, klen = kids.buffer_info()
        #summarize(naddr, kaddr, nodelen)
        #print_it(naddr, kaddr)

        for dc, vid in exchange_ids.iteritems():
            rvid = etrie.add(dc)
            self.assertEqual(vid, rvid)

            print dc, vid
            value = value_for_vid(naddr, kaddr, vid)
            self.assertEqual(dc, value)
            if dc != value:
                print "      dc=%s adc=%s" % (dc, value)

            avid = vid_for_value(naddr, kaddr, dc)
            #print "vid=%s avid=%s" % (vid, avid)
            self.assertEqual(vid, avid)

########NEW FILE########
__FILENAME__ = test_table
import unittest
from hustle import Table

class TestTable(unittest.TestCase):
    def test_create_syntax(self):
        full_columns = ['wide index uint32 x', 'index string y', 'int16 z', 'lz4 a', 'trie32 b', 'binary c']
        full_fields = ['=@4x', '+$y', '#2z', '*a', '%4b', '&c']
        fields = Table.parse_column_specs(full_columns)
        self.assertListEqual(fields, full_fields)

        default_columns = ['wide index x', 'index int y', 'uint z', 'trie b', 'c']
        default_fields = ['=x', '+#y', '@z', '%b', 'c']
        fields = Table.parse_column_specs(default_columns)
        self.assertListEqual(fields, default_fields)

    def test_create_errors(self):
        self.assertRaises(ValueError, Table.parse_column_specs, ['wide wide index x'])
        self.assertRaises(ValueError, Table.parse_column_specs, ['index wide x'])
        self.assertRaises(ValueError, Table.parse_column_specs, ['index blah16 x'])
        self.assertRaises(ValueError, Table.parse_column_specs, ['uint24 x'])

########NEW FILE########
__FILENAME__ = test_util
import unittest
from hustle.core.util import SortedIterator

class TestSortedIterator(unittest.TestCase):

    def test_merges_sorted_inputs(self):
        data = [
            [
                ((1, 1), 'some_value'),
                ((1, 2), 'some_value'),
                ((1, 3), 'some_value')
            ],
            [
                ((1, 100), 'some_value'),
                ((1, 200), 'some_value'),
                ((1, 300), 'some_value')
            ],
            [
                ((1, 10), 'some_value'),
                ((1, 20), 'some_value'),
                ((1, 30), 'some_value')
            ],
            [
                ((1, 4), 'some_value'),
                ((1, 40), 'some_value'),
                ((1, 400), 'some_value')
            ]
        ]
        sorted_iterator = SortedIterator(data)
        expected = [
            ((1, 1), 'some_value'),
            ((1, 2), 'some_value'),
            ((1, 3), 'some_value'),
            ((1, 4), 'some_value'),
            ((1, 10), 'some_value'),
            ((1, 20), 'some_value'),
            ((1, 30), 'some_value'),
            ((1, 40), 'some_value'),
            ((1, 100), 'some_value'),
            ((1, 200), 'some_value'),
            ((1, 300), 'some_value'),
            ((1, 400), 'some_value')]
        self.assertListEqual(list(sorted_iterator), expected)

    def test_assumes_individual_inputs_are_already_sorted(self):
        data = [
            [
                ((2, 1), 'some_value'),
                ((1, 1), 'some_value'),
            ],
            [
                ((4, 1), 'some_value'),
                ((3, 1), 'some_value'),
            ]
        ]
        sorted_iterator = SortedIterator(data)
        expected = [
            ((2, 1), 'some_value'),
            ((1, 1), 'some_value'),
            ((4, 1), 'some_value'),
            ((3, 1), 'some_value')]
        self.assertListEqual(list(sorted_iterator), expected)

    def test_handles_duplicates(self):
        data = [
            [
                ((1, 1), 'some_value'),
                ((1, 2), 'some_value'),
            ],
            [
                ((1, 1), 'some_value'),
                ((1, 2), 'some_value'),
                ((1, 3), 'some_value'),
            ],
            [
                ((1, 3), 'some_value'),
            ]
        ]
        sorted_iterator = SortedIterator(data)
        expected = [
            ((1, 1), 'some_value'),
            ((1, 1), 'some_value'),
            ((1, 2), 'some_value'),
            ((1, 2), 'some_value'),
            ((1, 3), 'some_value'),
            ((1, 3), 'some_value')]
        self.assertListEqual(list(sorted_iterator), expected)

    def test_handles_empty_input(self):
        data = [
            [((1, 1), 'some_value')],
            [],  # <----- empty input
            [((2, 1), 'some_value')],
        ]
        sorted_iterator = SortedIterator(data)
        expected = [
            ((1, 1), 'some_value'),
            ((2, 1), 'some_value')]
        self.assertListEqual(list(sorted_iterator), expected)

########NEW FILE########
__FILENAME__ = test_wtrie
import struct
import unittest
from wtrie import Trie


class TestWTrie(unittest.TestCase):
    def test_wtrie(self):
        t = Trie()
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hell'), 2)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellothere'), 3)
        self.assertEqual(t.add('good'), 4)
        self.assertEqual(t.add('goodbye'), 5)
        self.assertEqual(t.add('hello'), 1)
        self.assertEqual(t.add('hellsink'), 6)
        self.assertEqual(t.add(''), 0)

        # nodes = t.nodes
        # t.print_it()

        key, sz, pt = t.node_at_path()
        self.assertEqual(sz, 2)

        key, sz, pt = t.node_at_path(104)
        self.assertEqual(key, 'hell')
        self.assertEqual(pt, 0)
        self.assertEqual(sz, 2, 'actual %s' % sz)

        key2, sz, pt = t.node_at_path(104, 111)
        self.assertEqual(key2, 'o', 'actual %s' % key)
        self.assertEqual(pt, 2)
        self.assertEqual(sz, 1)

        key, sz, pt = t.node_at_path(104, 111, 116)
        self.assertEqual(key, 'there')
        self.assertEqual(pt, 1)
        self.assertEqual(sz, 0)

        n, k, _ = t.serialize()
        self.assertEqual(len(n), 7 * 4, "actual %d" % len(n))
        self.assertEqual(len(k), 100, "actual %d" % len(k))
        # print "sqork: %s" % t.kid_space

        print 'nodes', n
        print 'kids', k

        unpacked = struct.unpack_from("7I", n, 0)
        expected = (0x02000000, 0x01000010, 0x0200000b, 0x00000013, 0x01000004, 0x00000008, 0x00000016)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH2I", k, 0)
        expected = (0, 0, 0x67000004, 0x68000002)
        self.assertEqual(unpacked, expected, unpacked)

        unpacked = struct.unpack_from("IH4cI", k, 16)
        expected = (0x0000, 0x0004, 'g', 'o', 'o', 'd', 0x62000005)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH3c", k, 32)
        expected = (0x0004, 0x0003, 'b', 'y', 'e')
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH4c2I", k, 44)
        expected = (0x0000, 0x0004, 'h', 'e', 'l', 'l', 0x6f000001, 0x73000006)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IHcI", k, 64)
        expected = (0x0002, 1, 'o', 0x74000003)
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH5c", k, 76)
        expected = (0x0001, 0x0005, 't', 'h', 'e', 'r', 'e')
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

        unpacked = struct.unpack_from("IH4c", k, 88)
        expected = (0x0002, 0x0004, 's', 'i', 'n', 'k')
        self.assertEqual(unpacked, expected, 'actual %s' % str(unpacked))

########NEW FILE########
