__FILENAME__ = rome
from itertools import count


__version__ = '0.0.3'


_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


class Roman(int):

    def __new__(class_, roman):
        try:
            roman = int(roman)
        except ValueError:
            roman = str(roman).upper().replace(' ', '')
            if not set(_map) >= set(roman):
                raise ValueError('Not a valid Roman numeral: %r' % roman)
            values = list(map(_map.get, roman))
            value = sum(-n if n < max(values[i:]) else n
                        for i, n in enumerate(values))
            return super(Roman, class_).__new__(class_, value)
        else:
            if roman < 1:
                raise ValueError('Only n > 0 allowed, given: %r' % roman)
            return super(Roman, class_).__new__(class_, roman)

    def _negatively(self):
        if self > 1000:
            return ''
        base, s = sorted((v, k) for k, v in _map.items() if v >= self)[0]
        decrement = base - self
        if decrement == 0:
            return s
        else:
            return Roman(decrement)._positively() + s

    def _positively(self):
        value = self
        result = ''
        while value > 0:
            for v, r in reversed(sorted((v, k) for k, v in _map.items())):
                if v <= value:
                    value -= v
                    result += r
                    break
        return result

    def _split(self):
        result = []
        for i in (10 ** i for i in count()):
            if i > self:
                break
            result.append(self % (i * 10) // i * i)
        return result[::-1]

    def __str__(self):
        s = ''
        for n in self._split():
            if n == 0:
                continue
            pos = Roman(n)._positively()
            neg = Roman(n)._negatively()
            s += neg if neg and len(neg) < len(pos) else pos
        return s

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__str__())

########NEW FILE########
__FILENAME__ = test_rome
from __future__ import with_statement

from pytest import raises

from rome import Roman


def test_one_letter_numerals():
    roman = 'IVXLCDM'
    arabic = [1, 5, 10, 50, 100, 500, 1000]
    for r, a in zip(roman, arabic):
        assert Roman(r) == a


def test_numerals_that_only_sum_up():
    assert Roman('XX') == 20
    assert Roman('MDCCCCX') == 1910
    assert Roman('MMXIII') == 2013


def test_numerals_that_need_to_substract():
    assert Roman('IIX') == 8
    assert Roman('XIX') == 19
    assert Roman('MCMLIV') == 1954
    assert Roman('M cM xC') == 1990


def test_arabic_to_roman():
    assert Roman(20) == 20
    assert Roman(20) == Roman('XX')
    assert str(Roman(20)) == 'XX'
    assert repr(Roman(20)) == "Roman('XX')"
    assert Roman(1999) == Roman('MDCCCCLXXXXVIIII')
    assert Roman(2112) == Roman('MMCXII')


def test_expressions():
    assert Roman('XX') + Roman('X') == Roman('XXX')
    assert Roman('XX') - Roman('X') == Roman('X')


def test_errors():
    with raises(ValueError):
        Roman('ZYX')
    with raises(ValueError):
        Roman(-1)
    with raises(ValueError):
        Roman(0)


def test_construct_number_negatively():
    assert Roman(10)._negatively() == 'X'
    assert Roman(9)._negatively() == 'IX'
    assert Roman(6)._negatively() == 'IIIIX'
    assert Roman(44)._negatively() == 'VIL'
    assert Roman(20)._negatively() == 'XXXL'
    assert Roman(2000)._negatively() == ''
    assert Roman(10000)._negatively() == ''


def test_split_number_into_groups():
    assert Roman(1234)._split() == [1000, 200, 30, 4]
    assert Roman(50280)._split() == [50000, 0, 200, 80, 0]
    assert Roman(20)._split() == [20, 0]


def test_normalize_roman_number():
    assert str(Roman('MDCCCCLXXXXVIIII')) == 'MCMXCIX'
    assert str(Roman(1903)) == 'MCMIII'
    assert str(Roman('IIII')) == 'IV'
    assert str(Roman(2000)) == 'MM'
    assert str(Roman(2013)) == 'MMXIII'

########NEW FILE########
