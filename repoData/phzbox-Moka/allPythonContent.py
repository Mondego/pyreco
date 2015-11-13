__FILENAME__ = tests
import unittest
import string
import operator as op
from __init__ import List, Dict, Blank as _


class ListTest(unittest.TestCase):

    def setUp(self):
        self.seq = List(range(1, 6))

    def test_is_list(self):
        self.assertEqual(range(1, 6), self.seq)

    def test_map(self):
        self.assertEqual(self.seq.map(lambda x: x * 2), [2, 4, 6, 8, 10])

    def test_keep(self):
        self.assertEqual(self.seq.clone().keep(lambda x: x < 3), [1, 2])
        self.assertEqual(self.seq.clone().keep(op.eq, 3), [3])
        self.assertEqual(self.seq.keep(op.eq, 3), [3])

    def test_rem(self):
        self.assertEqual(self.seq.clone().rem(lambda x: x < 3), [3, 4, 5])
        self.assertEqual(self.seq.rem(op.eq, 3), [1, 2, 4, 5])

    def test_mix(self):
        r = (self.seq
                 .map(lambda x: x * 2)
                 .rem(lambda x: x < 5)
                 .keep(lambda x: x % 2 == 0)
                 .rem(op.eq, 6))

        self.assertEqual(r, [8, 10])

    def test_self(self):
        self.assertEqual(
            (self.seq
             .clone()
             .map(lambda x: x * 2)
             .rem(lambda x: x < 5)
             .keep(lambda x: x % 2 == 0)
             .rem(op.eq, 6)
             .tee(self.assertEqual, [8, 10])),
             [8, 10])

        (self.seq
              .keep(lambda x: x > 4)
              .tee(self.assertEqual, [5])
              .last_value) = [5]

    def test_some(self):
        self.assert_(self.seq.some(lambda x: x < 3))

        self.assert_(self.seq.some(op.eq, 4))

        self.assertFalse(List([1, 1, 1]).some(op.eq, 2))

        self.assertFalse(self.seq.some(lambda x: x < 1))

    def test_has(self):
        self.assert_(List(range(10)).has(op.eq, 5))
        self.assert_(List(range(10)).has(lambda x: x in [1, 2]))

    def test_find(self):
        self.assertEqual(self.seq.find(op.eq, 3), 3)

        self.assertEqual(self.seq.find(lambda x: x == 3), 3)

        self.assertEqual(self.seq.find(lambda x: x != 3), 1)

    def test_all(self):
        self.assertFalse(self.seq.all(lambda x: x < 3))

        self.assertFalse(self.seq.all(op.eq, 4))

        self.assert_(List([1, 1, 1]).all(op.eq, 1))

        self.assert_(self.seq.all(lambda x: x < 10))

    def test_append(self):
        self.assertEqual(self.seq.append(6), [1, 2, 3, 4, 5, 6])
        self.assertEqual(self.seq, [1, 2, 3, 4, 5])

    def test_extend(self):
        self.assertEqual(self.seq.extend([1, 2]), [1, 2, 3, 4, 5, 1, 2])
        self.assertEqual(self.seq, [1, 2, 3, 4, 5])

    def test_insert(self):
        self.assertEqual(self.seq.insert(0, 4), [4, 1, 2, 3, 4, 5])
        self.assertEqual(self.seq, [1, 2, 3, 4, 5])

    def test_getslice(self):
        self.assertEqual(self.seq[:2], [1, 2])
        self.assertEqual(type(self.seq[:1]), List)
        self.assertEqual(self.seq[:2].map(lambda x: x * 2), [2, 4])

    def test_setslice(self):
        self.seq[2:] = [9, 9]
        self.assertEqual(self.seq, [1, 2, 9, 9])
        self.assertEqual(type(self.seq), List)

    def test_reverse(self):
        self.assertEqual(self.seq.reverse(), [5, 4, 3, 2, 1])
        self.assertEqual(type(self.seq), List)

    def test_sort(self):
        self.seq = List([1, 4, 2, 5, 3])
        self.assertEqual(self.seq.sort(), [1, 2, 3, 4, 5])
        self.assertEqual(type(self.seq), List)

    def test_count(self):
        self.assertEqual(self.seq.count(), 5)
        self.assertEqual(self.seq.count(op.eq, 3), 1)
        self.assertEqual(self.seq.count(lambda x: x in [1, 3]), 2)

    def test_empty(self):
        self.assertFalse(self.seq.empty())
        self.assertTrue(List().empty())
        self.assertTrue(List([None, 0, 0]).empty(lambda x: x in [None, 0]))
        self.assertFalse(List([None, [], 0]).empty(lambda x: x in [None, 0]))

    def test_attr(self):
        self.assertEqual(self.seq.attr('real'), [1, 2, 3, 4, 5])
        self.assertEqual(self.seq.clone().attr('imag'), [0, 0, 0, 0, 0])
        self.assertEqual(self.seq.clone().map(op.attrgetter('real')),
                         [1, 2, 3, 4, 5])

    def test_item(self):
        self.assertEqual(List([dict(a=1), dict(a=2)]).item('a'), [1, 2])
        (List([dict(a=1), dict(a=2)])
           .map(op.itemgetter('a'))
           .do(self.assertEqual, [1, 2]))

    def test_invoke(self):
        self.assertEqual(self.seq.invoke('__str__'),
                         ['1', '2', '3', '4', '5'])
        (self.seq
             .map(op.methodcaller('__str__'))
             .do(self.assertEqual, ['1', '2', '3', '4', '5']))

    def test_partial(self):
        (List('7')
          .map(string.zfill, 3)
          .do(self.assertEqual, ['007']))

    def test_partial_blank(self):
        (List([3])
          .map(string.zfill, '7', _)
          .do(self.assertEqual, ['007']))

    def test_kw_in(self):
        (List([1, 2])
          .keep(op.contains, [2, 3, 4], _)
          .do(self.assertEqual, [2]))

    def test_kw_gt(self):
        (List([1, 2])
          .keep(op.gt, 1)
          .do(self.assertEqual, [2]))

    def test_kw_ge(self):
        (List([1, 2])
          .keep(op.ge, 1)
          .do(self.assertEqual, [1, 2]))

    def test_kw_lt(self):
        (List([1, 2])
          .keep(op.lt, 2)
          .do(self.assertEqual, [1]))

    def test_kw_le(self):
        (List([1, 2])
          .keep(op.le, 2)
          .do(self.assertEqual, [1, 2]))

    def test_savelist(self):
        x = List(range(1, 5))
        x.keep(op.gt, 2)
        x.keep(op.lt, 4)
        self.assertEqual(x, [3])


class DictTest(unittest.TestCase):

    def setUp(self):
        self.seq = Dict(a=1, b=2, c=3)

    def test_is_dict(self):
        self.assertEqual(self.seq, dict(a=1, b=2, c=3))

    def test_map(self):
        self.assertEqual(self.seq.map(lambda x, y: (x, x)),
                         dict(a='a', b='b', c='c'))

        self.assertEqual(self.seq.map(lambda x, y: (x, y * 2)),
                         dict(a=2, b=4, c=6))

    def test_keep(self):
        self.assertEqual(self.seq.keep(lambda x, y: y == 3), dict(c=3))
        self.assertEqual(self.seq.keep(lambda x, y: y > 2), dict(c=3))

    def test_rem(self):
        self.assertEqual(self.seq.rem(lambda x, y: y == 3), dict(a=1, b=2))
        self.assertEqual(self.seq.rem(lambda x, y: y > 2), dict(a=1, b=2))

    def test_update(self):
        self.assertEqual(self.seq.update(dict(a=5, d=1)),
                         dict(a=5, b=2, c=3, d=1))
        self.assertTrue(isinstance(self.seq.update(dict(a=5, d=1)), Dict))

    def test_clear(self):
        self.assertEqual(self.seq.clear(), {})
        self.assertTrue(isinstance(self.seq.clear(), Dict))

    def test_copy(self):
        a = []

        self.assertEqual(id(Dict(a=a).copy()['a']), id(a))
        self.assertEqual(self.seq.copy(), self.seq)
        self.assertTrue(isinstance(self.seq.copy(), Dict))

    def test_fromkeys(self):
        self.assertTrue(isinstance(Dict.fromkeys([1, 2, 3]), Dict))
        self.assertEqual(Dict.fromkeys([1, 2, 3]),
                         {1: None, 2: None, 3: None})

    def test_all(self):
        self.assertTrue(self.seq.all(lambda x, y: y in [1, 2, 3]))
        self.assertTrue(self.seq.update(a=2, c=2).all(lambda x, y: y == 2))
        self.assertFalse(self.seq.all(lambda x, y: y == 4))

    def test_some(self):
        self.assertTrue(self.seq.some(lambda x, y: op.eq(y, 2)))
        self.assertFalse(self.seq.some(lambda x, y: op.eq(x, 2)))
        self.assertTrue(self.seq.some(lambda x, y: y == 3))

    def test_count(self):
        self.assertEqual(self.seq.count(), 3)
        self.assertEqual(self.seq.count(lambda x, y: y == 3), 1)
        self.assertEqual(self.seq.count(lambda x, y: y in [1, 3]), 2)

    def test_empty(self):
        self.assertFalse(self.seq.empty())
        self.assertTrue(Dict().empty())
        self.assertTrue(Dict(zip([1, 2, 3], [None, 0, 0]))
                          .empty(lambda x, y: y in [None, 0]))

        self.assertFalse(Dict(zip([1, 2, 3], [None, [], 0]))
                          .empty(lambda x, y: y in [None, 0]))

    def test_do(self):
        self.assertEqual(
            (self.seq
             .map(lambda x, y: (x, y * 2))
             .rem(lambda x, y: y == 4)
             .do(self.assertEqual, dict(a=2, c=6))),
             dict(a=2, c=6))

        self.assertEqual(self.seq.do(lambda self: 1 + 1).last_value, 2)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
