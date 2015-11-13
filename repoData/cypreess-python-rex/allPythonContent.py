__FILENAME__ = rex
import re
import operator
from six.moves import reduce
import six

REX_CACHE = {}


class RexMatch(dict):
    """
    Dummy defaultdict implementation of matched strings. Returns `None`
    for unknown keys.
    """

    def __getitem__(self, y):
        try:
            return super(RexMatch, self).__getitem__(y)
        except KeyError:
            return None

    def get(self, k, d=None):
        ret = super(RexMatch, self).get(k, d)
        return d if ret is None else ret

    def __str__(self):
        return str(self[0]) if self[0] else ''

    def __unicode__(self):
        return six.u(self[0]) if self[0] else u''


class Rex(object):
    FLAGS = {
        'd': re.DEBUG,
        'i': re.IGNORECASE,
        'l': re.LOCALE,
        'm': re.MULTILINE,
        's': re.DOTALL,
        'u': re.UNICODE,
        'x': re.VERBOSE,
    }

    def __init__(self, action, pattern, replacement='', flags=0):
        self.action = action
        self.pattern = pattern
        self.flags = flags
        self.replacement = replacement
        self.re = re.compile(self.pattern, self.flags)

    def __process(self, text):
        if self.action == 'm':
            result = RexMatch()
            match = self.re.search(text)
            if match is not None:
                rex.group = result
                result[0] = match.group()
                result.update(enumerate(match.groups(), start=1))
                result.update(match.groupdict())
            return result
        elif self.action == 's':
            return self.re.sub(self.replacement, text, self.flags)

    def __eq__(self, other):
        return self.__process(other)

    def __call__(self, text):
        return self.__process(text)


def rex(expression, text=None, cache=True):
    rex_obj = REX_CACHE.get(expression, None)
    if cache and rex_obj:

        if text is not None:
            return text == rex_obj
        else:
            return rex_obj

    action = 'm'
    start = 0
    if expression[start] in 'ms':
        action = expression[start]
        start = 1

    delimiter = expression[start]
    end = expression.rfind(delimiter)
    if end in (-1, start):
        raise ValueError('Regular expression syntax error.')
    pattern = expression[start + 1:end]
    replacement = ''
    if action == 's':
        index = pattern.rfind(delimiter)
        if index in (-1, 0):
            raise ValueError('Regular expression syntax error.')
        replacement = pattern[index + 1:]
        pattern = pattern[:index]

    try:
        re_flags = [Rex.FLAGS[f] for f in expression[end + 1:]]
    except KeyError:
        raise ValueError('Bad flags')

    rex_obj = Rex(action, pattern, replacement, reduce(operator.or_, re_flags, 0))
    if cache:
        REX_CACHE[expression] = rex_obj

    if text is not None:
        return text == rex_obj
    else:
        return rex_obj
rex.group = RexMatch()


def rex_clear_cache():
    global REX_CACHE
    REX_CACHE = {}

########NEW FILE########
__FILENAME__ = test_rex
import re

import pytest
import rex as rex_module
from rex import rex_clear_cache, RexMatch, rex


def test_value_error():
    pytest.raises(ValueError, rex, '/test')
    pytest.raises(ValueError, rex, 'm/test')
    pytest.raises(ValueError, rex, 's/test/')
    pytest.raises(ValueError, rex, 's//test/')


def test_no_action():
    r = rex('/test/')
    assert r.action == 'm'
    assert r.pattern == 'test'
    assert r.flags == 0


def test_str():
    m = "This is dog!" == rex('/[a-z]+!/')
    assert str(m) == 'dog!'


def test_empty_str():
    m = "This is dog!" == rex('/[0-9]+!/')
    assert str(m) == ''


def test_unicode():
    m = "This is dog!" == rex('/[a-z]+!/')
    assert m.__unicode__() == u'dog!'


def test_empty_unicode():
    m = "This is dog!" == rex('/[0-9]+!/')
    assert m.__unicode__() == u''


def test_no_action_ex():
    r = rex('!test!')
    assert r.action == 'm'
    assert r.pattern == 'test'
    assert r.flags == 0


def test_m_action():
    r = rex('m/test/')
    assert r.action == 'm'
    assert r.pattern == 'test'
    assert r.flags == 0


def test_m_action_ex():
    r = rex('m!test!')
    assert r.action == 'm'
    assert r.pattern == 'test'
    assert r.flags == 0


def test_s_action():
    r = rex('s/test/ohh/')
    assert r.action == 's'
    assert r.pattern == 'test'
    assert r.replacement == 'ohh'
    assert r.flags == 0


def test_s_action_flags():
    r = rex('/test/im')
    assert r.action == 'm'
    assert r.pattern == 'test'
    assert r.flags == re.I | re.M


def test_s_action_bad():
    pytest.raises(ValueError, rex, '/test/imH')


def test_m_true():
    assert ("Aa 9-9 88 xx" == rex('/([0-9-]+) (?P<t>[0-9-]+)/'))


def test_m_true_orthodox():
    assert rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa 9-9 88 xx")


def test_m_false_noncache():
    assert rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa 9-9 88 xx", cache=False)
    assert not rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa bb cc xx", cache=False)


def test_m_false():
    assert not ("Aa 9-9  xx" == rex('/([0-9-]+) (?P<t>[0-9-]+)/'))


def test_m_false_orthodox():
    assert not rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa 9-9  xx")


def test_m_value():
    assert ("Aa 9-9 88 xx" == rex('/([0-9-]+) (?P<t>[0-9-]+)/'))['t'] == '88'
    assert ("Aa 9-9 88 xx" == rex('/([0-9-]+) (?P<t>[0-9-]+)/'))[2] == '88'
    assert ("Aa 9-9 88 xx" == rex('/([0-9-]+) (?P<t>[0-9-]+)/'))['tttt'] is None


def test_m_value_orthodox():
    assert rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa 9-9 88 xx")['t'] == '88'
    assert rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa 9-9 88 xx")[2] == '88'
    assert rex('/([0-9-]+) (?P<t>[0-9-]+)/', "Aa 9-9 88 xx")['tttt'] is None


def test_m_true_call():
    r = rex('/([0-9-]+) (?P<t>[0-9-]+)/')
    assert r("Aa 9-9 88 xx")


def test_m_false_call():
    r = rex('/([0-9-]+) (?P<t>[0-9-]+)/')
    assert not r("Aa 9-9  xx")


def test_s():
    s = ("This is a cat" == rex('s/cat/dog/'))
    assert s == 'This is a dog'


def test_s_i():
    s = "This is a cat" == rex('s/CAT/dog/i')
    assert s == 'This is a dog'


def test_s_multi():
    s = "This is a cat cat cat cat" == rex('s/cat/dog/')
    assert s == 'This is a dog dog dog dog'


def test_s_orthodox():
    assert rex('s/cat/dog/', "This is a cat") == 'This is a dog'


def test_s_i_orthodox():
    assert rex('s/CAT/dog/i', "This is a cat") == 'This is a dog'


def test_s_multi_orthodox():
    assert rex('s/cat/dog/', "This is a cat cat cat cat") == 'This is a dog dog dog dog'


def test_cache():
    rex('s/cache/test/')
    assert 's/cache/test/' in rex_module.REX_CACHE


def test_cache_2():
    a = rex('s/cache/test/')
    b = rex('s/cache/test/')
    assert a is b


def test_no_cache_2():
    a = rex('s/cache/test/', cache=False)
    b = rex('s/cache/test/', cache=False)
    assert not (a is b)


def test_not_cache():
    rex('s/cache/test1/', cache=False)
    assert not 's/cache/test1/' in rex_module.REX_CACHE


def test_clear_cache():
    rex('s/cache/test/')
    rex_clear_cache()
    assert not 's/cache/test/' in rex_module.REX_CACHE


def test_rex_match():
    rm = RexMatch(((0, 'some match'), ('a', 1), ('b', 2)))
    assert rm['a'] == 1
    assert rm['b'] == 2
    assert str(rm) == 'some match'
    assert rm.__unicode__() == u'some match'


def test_rex_match_empty():
    rm = RexMatch()
    assert rm['a'] is None
    assert rm['b'] is None
    assert str(rm) == ''
    assert rm.__unicode__() == u''


def test_rex_match_get_empty():
    rm = RexMatch((('c', None),))
    assert rm.get('a') is None
    assert rm.get('a', 'b') == 'b'
    assert rm.get('c', 'b') == 'b'


def test_rex_group():
    m = "This is cat! A kitten is a cat but not a dog." == rex('/[a-z]+!.*(kitten\s\S{2}).*but.*(dog)\./')
    assert m == rex.group


if __name__ == "__main__":
    pytest.main()
########NEW FILE########
