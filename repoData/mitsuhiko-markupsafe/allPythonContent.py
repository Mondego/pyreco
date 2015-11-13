__FILENAME__ = bench_basic
from markupsafe import escape


def run():
    escape('<strong>Hello World!</strong>')

########NEW FILE########
__FILENAME__ = bench_largestring
from markupsafe import escape


def run():
    string = '<strong>Hello World!</strong>' * 1000
    escape(string)

########NEW FILE########
__FILENAME__ = bench_long_empty_string
from markupsafe import escape


def run():
    string = 'Hello World!' * 1000
    escape(string)

########NEW FILE########
__FILENAME__ = bench_long_suffix
from markupsafe import escape


def run():
    string = '<strong>Hello World!</strong>' + 'x' * 100000
    escape(string)

########NEW FILE########
__FILENAME__ = bench_short_empty_string
from markupsafe import escape


def run():
    escape('Hello World!')

########NEW FILE########
__FILENAME__ = runbench
#!/usr/bin/env python
"""
    Runs the benchmarks
"""
import sys
import os
import re
from subprocess import Popen

_filename_re = re.compile(r'^bench_(.*?)\.py$')
bench_directory = os.path.abspath(os.path.dirname(__file__))


def list_benchmarks():
    result = []
    for name in os.listdir(bench_directory):
        match = _filename_re.match(name)
        if match is not None:
            result.append(match.group(1))
    result.sort(key=lambda x: (x.startswith('logging_'), x.lower()))
    return result


def run_bench(name):
    sys.stdout.write('%-32s' % name)
    sys.stdout.flush()
    Popen([sys.executable, '-mtimeit', '-s',
           'from bench_%s import run' % name,
           'run()']).wait()


def main():
    print '=' * 80
    print 'Running benchmark for MarkupSafe'
    print '-' * 80
    os.chdir(bench_directory)
    for bench in list_benchmarks():
        run_bench(bench)
    print '-' * 80


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import gc
import sys
import unittest
from markupsafe import Markup, escape, escape_silent
from markupsafe._compat import text_type


class MarkupTestCase(unittest.TestCase):

    def test_adding(self):
        # adding two strings should escape the unsafe one
        unsafe = '<script type="application/x-some-script">alert("foo");</script>'
        safe = Markup('<em>username</em>')
        assert unsafe + safe == text_type(escape(unsafe)) + text_type(safe)

    def test_string_interpolation(self):
        # string interpolations are safe to use too
        assert Markup('<em>%s</em>') % '<bad user>' == \
               '<em>&lt;bad user&gt;</em>'
        assert Markup('<em>%(username)s</em>') % {
            'username': '<bad user>'
        } == '<em>&lt;bad user&gt;</em>'

        assert Markup('%i') % 3.14 == '3'
        assert Markup('%.2f') % 3.14 == '3.14'

    def test_type_behavior(self):
        # an escaped object is markup too
        assert type(Markup('foo') + 'bar') is Markup

        # and it implements __html__ by returning itself
        x = Markup("foo")
        assert x.__html__() is x

    def test_html_interop(self):
        # it also knows how to treat __html__ objects
        class Foo(object):
            def __html__(self):
                return '<em>awesome</em>'
            def __unicode__(self):
                return 'awesome'
            __str__ = __unicode__
        assert Markup(Foo()) == '<em>awesome</em>'
        assert Markup('<strong>%s</strong>') % Foo() == \
            '<strong><em>awesome</em></strong>'

    def test_tuple_interpol(self):
        self.assertEqual(Markup('<em>%s:%s</em>') % (
            '<foo>',
            '<bar>',
        ), Markup(u'<em>&lt;foo&gt;:&lt;bar&gt;</em>'))

    def test_dict_interpol(self):
        self.assertEqual(Markup('<em>%(foo)s</em>') % {
            'foo': '<foo>',
        }, Markup(u'<em>&lt;foo&gt;</em>'))
        self.assertEqual(Markup('<em>%(foo)s:%(bar)s</em>') % {
            'foo': '<foo>',
            'bar': '<bar>',
        }, Markup(u'<em>&lt;foo&gt;:&lt;bar&gt;</em>'))

    def test_escaping(self):
        # escaping and unescaping
        assert escape('"<>&\'') == '&#34;&lt;&gt;&amp;&#39;'
        assert Markup("<em>Foo &amp; Bar</em>").striptags() == "Foo & Bar"
        assert Markup("&lt;test&gt;").unescape() == "<test>"

    def test_formatting(self):
        for actual, expected in (
            (Markup('%i') % 3.14, '3'),
            (Markup('%.2f') % 3.14159, '3.14'),
            (Markup('%s %s %s') % ('<', 123, '>'), '&lt; 123 &gt;'),
            (Markup('<em>{awesome}</em>').format(awesome='<awesome>'),
             '<em>&lt;awesome&gt;</em>'),
            (Markup('{0[1][bar]}').format([0, {'bar': '<bar/>'}]),
             '&lt;bar/&gt;'),
            (Markup('{0[1][bar]}').format([0, {'bar': Markup('<bar/>')}]),
             '<bar/>')):
            assert actual == expected, "%r should be %r!" % (actual, expected)

    # This is new in 2.7
    if sys.version_info > (2, 6):
        def test_formatting_empty(self):
            formatted = Markup('{}').format(0)
            assert formatted == Markup('0')

    def test_custom_formatting(self):
        class HasHTMLOnly(object):
            def __html__(self):
                return Markup('<foo>')

        class HasHTMLAndFormat(object):
            def __html__(self):
                return Markup('<foo>')
            def __html_format__(self, spec):
                return Markup('<FORMAT>')

        assert Markup('{0}').format(HasHTMLOnly()) == Markup('<foo>')
        assert Markup('{0}').format(HasHTMLAndFormat()) == Markup('<FORMAT>')

    def test_complex_custom_formatting(self):
        class User(object):
            def __init__(self, id, username):
                self.id = id
                self.username = username
            def __html_format__(self, format_spec):
                if format_spec == 'link':
                    return Markup('<a href="/user/{0}">{1}</a>').format(
                        self.id,
                        self.__html__(),
                    )
                elif format_spec:
                    raise ValueError('Invalid format spec')
                return self.__html__()
            def __html__(self):
                return Markup('<span class=user>{0}</span>').format(self.username)

        user = User(1, 'foo')
        assert Markup('<p>User: {0:link}').format(user) == \
            Markup('<p>User: <a href="/user/1"><span class=user>foo</span></a>')

    def test_all_set(self):
        import markupsafe as markup
        for item in markup.__all__:
            getattr(markup, item)

    def test_escape_silent(self):
        assert escape_silent(None) == Markup()
        assert escape(None) == Markup(None)
        assert escape_silent('<foo>') == Markup(u'&lt;foo&gt;')

    def test_splitting(self):
        self.assertEqual(Markup('a b').split(), [
            Markup('a'),
            Markup('b')
        ])
        self.assertEqual(Markup('a b').rsplit(), [
            Markup('a'),
            Markup('b')
        ])
        self.assertEqual(Markup('a\nb').splitlines(), [
            Markup('a'),
            Markup('b')
        ])

    def test_mul(self):
        self.assertEqual(Markup('a') * 3, Markup('aaa'))


class MarkupLeakTestCase(unittest.TestCase):

    def test_markup_leaks(self):
        counts = set()
        for count in range(20):
            for item in range(1000):
                escape("foo")
                escape("<foo>")
                escape(u"foo")
                escape(u"<foo>")
            counts.add(len(gc.get_objects()))
        assert len(counts) == 1, 'ouch, c extension seems to leak objects'


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MarkupTestCase))

    # this test only tests the c extension
    if not hasattr(escape, 'func_code'):
        suite.addTest(unittest.makeSuite(MarkupLeakTestCase))

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

# vim:sts=4:sw=4:et:

########NEW FILE########
__FILENAME__ = _compat
# -*- coding: utf-8 -*-
"""
    markupsafe._compat
    ~~~~~~~~~~~~~~~~~~

    Compatibility module for different Python versions.

    :copyright: (c) 2013 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys

PY2 = sys.version_info[0] == 2

if not PY2:
    text_type = str
    string_types = (str,)
    unichr = chr
    int_types = (int,)
    iteritems = lambda x: iter(x.items())
else:
    text_type = unicode
    string_types = (str, unicode)
    unichr = unichr
    int_types = (int, long)
    iteritems = lambda x: x.iteritems()

########NEW FILE########
__FILENAME__ = _constants
# -*- coding: utf-8 -*-
"""
    markupsafe._constants
    ~~~~~~~~~~~~~~~~~~~~~

    Highlevel implementation of the Markup string.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""


HTML_ENTITIES = {
    'AElig': 198,
    'Aacute': 193,
    'Acirc': 194,
    'Agrave': 192,
    'Alpha': 913,
    'Aring': 197,
    'Atilde': 195,
    'Auml': 196,
    'Beta': 914,
    'Ccedil': 199,
    'Chi': 935,
    'Dagger': 8225,
    'Delta': 916,
    'ETH': 208,
    'Eacute': 201,
    'Ecirc': 202,
    'Egrave': 200,
    'Epsilon': 917,
    'Eta': 919,
    'Euml': 203,
    'Gamma': 915,
    'Iacute': 205,
    'Icirc': 206,
    'Igrave': 204,
    'Iota': 921,
    'Iuml': 207,
    'Kappa': 922,
    'Lambda': 923,
    'Mu': 924,
    'Ntilde': 209,
    'Nu': 925,
    'OElig': 338,
    'Oacute': 211,
    'Ocirc': 212,
    'Ograve': 210,
    'Omega': 937,
    'Omicron': 927,
    'Oslash': 216,
    'Otilde': 213,
    'Ouml': 214,
    'Phi': 934,
    'Pi': 928,
    'Prime': 8243,
    'Psi': 936,
    'Rho': 929,
    'Scaron': 352,
    'Sigma': 931,
    'THORN': 222,
    'Tau': 932,
    'Theta': 920,
    'Uacute': 218,
    'Ucirc': 219,
    'Ugrave': 217,
    'Upsilon': 933,
    'Uuml': 220,
    'Xi': 926,
    'Yacute': 221,
    'Yuml': 376,
    'Zeta': 918,
    'aacute': 225,
    'acirc': 226,
    'acute': 180,
    'aelig': 230,
    'agrave': 224,
    'alefsym': 8501,
    'alpha': 945,
    'amp': 38,
    'and': 8743,
    'ang': 8736,
    'apos': 39,
    'aring': 229,
    'asymp': 8776,
    'atilde': 227,
    'auml': 228,
    'bdquo': 8222,
    'beta': 946,
    'brvbar': 166,
    'bull': 8226,
    'cap': 8745,
    'ccedil': 231,
    'cedil': 184,
    'cent': 162,
    'chi': 967,
    'circ': 710,
    'clubs': 9827,
    'cong': 8773,
    'copy': 169,
    'crarr': 8629,
    'cup': 8746,
    'curren': 164,
    'dArr': 8659,
    'dagger': 8224,
    'darr': 8595,
    'deg': 176,
    'delta': 948,
    'diams': 9830,
    'divide': 247,
    'eacute': 233,
    'ecirc': 234,
    'egrave': 232,
    'empty': 8709,
    'emsp': 8195,
    'ensp': 8194,
    'epsilon': 949,
    'equiv': 8801,
    'eta': 951,
    'eth': 240,
    'euml': 235,
    'euro': 8364,
    'exist': 8707,
    'fnof': 402,
    'forall': 8704,
    'frac12': 189,
    'frac14': 188,
    'frac34': 190,
    'frasl': 8260,
    'gamma': 947,
    'ge': 8805,
    'gt': 62,
    'hArr': 8660,
    'harr': 8596,
    'hearts': 9829,
    'hellip': 8230,
    'iacute': 237,
    'icirc': 238,
    'iexcl': 161,
    'igrave': 236,
    'image': 8465,
    'infin': 8734,
    'int': 8747,
    'iota': 953,
    'iquest': 191,
    'isin': 8712,
    'iuml': 239,
    'kappa': 954,
    'lArr': 8656,
    'lambda': 955,
    'lang': 9001,
    'laquo': 171,
    'larr': 8592,
    'lceil': 8968,
    'ldquo': 8220,
    'le': 8804,
    'lfloor': 8970,
    'lowast': 8727,
    'loz': 9674,
    'lrm': 8206,
    'lsaquo': 8249,
    'lsquo': 8216,
    'lt': 60,
    'macr': 175,
    'mdash': 8212,
    'micro': 181,
    'middot': 183,
    'minus': 8722,
    'mu': 956,
    'nabla': 8711,
    'nbsp': 160,
    'ndash': 8211,
    'ne': 8800,
    'ni': 8715,
    'not': 172,
    'notin': 8713,
    'nsub': 8836,
    'ntilde': 241,
    'nu': 957,
    'oacute': 243,
    'ocirc': 244,
    'oelig': 339,
    'ograve': 242,
    'oline': 8254,
    'omega': 969,
    'omicron': 959,
    'oplus': 8853,
    'or': 8744,
    'ordf': 170,
    'ordm': 186,
    'oslash': 248,
    'otilde': 245,
    'otimes': 8855,
    'ouml': 246,
    'para': 182,
    'part': 8706,
    'permil': 8240,
    'perp': 8869,
    'phi': 966,
    'pi': 960,
    'piv': 982,
    'plusmn': 177,
    'pound': 163,
    'prime': 8242,
    'prod': 8719,
    'prop': 8733,
    'psi': 968,
    'quot': 34,
    'rArr': 8658,
    'radic': 8730,
    'rang': 9002,
    'raquo': 187,
    'rarr': 8594,
    'rceil': 8969,
    'rdquo': 8221,
    'real': 8476,
    'reg': 174,
    'rfloor': 8971,
    'rho': 961,
    'rlm': 8207,
    'rsaquo': 8250,
    'rsquo': 8217,
    'sbquo': 8218,
    'scaron': 353,
    'sdot': 8901,
    'sect': 167,
    'shy': 173,
    'sigma': 963,
    'sigmaf': 962,
    'sim': 8764,
    'spades': 9824,
    'sub': 8834,
    'sube': 8838,
    'sum': 8721,
    'sup': 8835,
    'sup1': 185,
    'sup2': 178,
    'sup3': 179,
    'supe': 8839,
    'szlig': 223,
    'tau': 964,
    'there4': 8756,
    'theta': 952,
    'thetasym': 977,
    'thinsp': 8201,
    'thorn': 254,
    'tilde': 732,
    'times': 215,
    'trade': 8482,
    'uArr': 8657,
    'uacute': 250,
    'uarr': 8593,
    'ucirc': 251,
    'ugrave': 249,
    'uml': 168,
    'upsih': 978,
    'upsilon': 965,
    'uuml': 252,
    'weierp': 8472,
    'xi': 958,
    'yacute': 253,
    'yen': 165,
    'yuml': 255,
    'zeta': 950,
    'zwj': 8205,
    'zwnj': 8204
}

########NEW FILE########
__FILENAME__ = _native
# -*- coding: utf-8 -*-
"""
    markupsafe._native
    ~~~~~~~~~~~~~~~~~~

    Native Python implementation the C module is not compiled.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from markupsafe import Markup
from markupsafe._compat import text_type


def escape(s):
    """Convert the characters &, <, >, ' and " in string s to HTML-safe
    sequences.  Use this if you need to display text that might contain
    such characters in HTML.  Marks return value as markup string.
    """
    if hasattr(s, '__html__'):
        return s.__html__()
    return Markup(text_type(s)
        .replace('&', '&amp;')
        .replace('>', '&gt;')
        .replace('<', '&lt;')
        .replace("'", '&#39;')
        .replace('"', '&#34;')
    )


def escape_silent(s):
    """Like :func:`escape` but converts `None` into an empty
    markup string.
    """
    if s is None:
        return Markup()
    return escape(s)


def soft_unicode(s):
    """Make a string unicode if it isn't already.  That way a markup
    string is not converted back to unicode.
    """
    if not isinstance(s, text_type):
        s = text_type(s)
    return s

########NEW FILE########
