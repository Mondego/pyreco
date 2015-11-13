__FILENAME__ = cases
# encoding: utf-8
from __future__ import unicode_literals
import unittest

from uricore.wkz_datastructures import MultiDict


class IdentifierCase(unittest.TestCase):
    # Test properties and representations
    #
    # Class variables:
    # ri = URI or IRI object
    # expect = dict of expected results

    def test_scheme_baby(self):
        self.assertEquals(self.ri.scheme, self.expect['scheme'])

    def test_auth(self):
        self.assertEquals(self.ri.auth, self.expect['auth'])

    def test_hostname(self):
        self.assertEquals(self.ri.hostname, self.expect['hostname'])

    def test_port(self):
        self.assertEquals(self.ri.port, self.expect['port'])

    def test_path(self):
        self.assertEquals(self.ri.path, self.expect['path'])

    def test_query(self):
        self.assertEquals(self.ri.query, self.expect['query'])

    def test_querystr(self):
        self.assertEquals(self.ri.querystr, self.expect['querystr'])

    def test_fragment(self):
        self.assertEquals(self.ri.fragment, self.expect['fragment'])

    def test_netloc(self):
        self.assertEquals(self.ri.netloc, self.expect['netloc'])


class JoinAndUpdateCase(unittest.TestCase):
    # Test join and update
    #
    # Class variables:
    # RI = IRI/URI constructor given a unicode object

    def _literal_wrapper(self, lit):
        return lit

    def test_join_path_to_netloc(self):
        ri = self.RI('http://localhost:8000').join(self.RI('/path/to/file'))
        self.assertEquals(ri.scheme, 'http')
        self.assertEquals(ri.netloc, 'localhost:8000')
        self.assertEquals(ri.path, '/path/to/file')

    def test_join_path_to_path(self):
        ri = self.RI('http://localhost:8000/here/is/the').join(self.RI('/path/to/file'))
        self.assertEquals(ri.scheme, 'http')
        self.assertEquals(ri.netloc, 'localhost:8000')
        self.assertEquals(ri.path, '/here/is/the/path/to/file')

    def test_join_fragment_and_path(self):
        ri = self.RI('http://localhost:8000/here/is/the').join(self.RI('/thing#fragment'))
        self.assertEquals(ri.path, '/here/is/the/thing')
        self.assertEquals(ri.fragment, 'fragment')

    def test_join_query_to_path(self):
        ri = self.RI('http://localhost:8000/path/to/file').join(self.RI('?yes=no&left=right'))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query, MultiDict(dict(yes='no', left='right')))
        self.assertEquals(ri.querystr, 'yes=no&left=right')

    def test_join_query_to_query(self):
        ri = self.RI('http://localhost:8000/path/to/file?yes=no').join(self.RI('?left=right'))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query, MultiDict(dict(yes='no', left='right')))
        self.assertEquals(ri.querystr, 'yes=no&left=right')

    def test_join_query_to_query_to_make_multi_query(self):
        ri = self.RI('http://localhost:8000/path/to/file?yes=no').join(self.RI('?yes=maybe&left=right'))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query,
            MultiDict([('yes', 'no'), ('yes', 'maybe'), ('left', 'right')]))
        self.assertEquals(ri.querystr, 'yes=no&yes=maybe&left=right')

    def test_join_nonascii_query_to_query(self):
        ri = self.RI('http://localhost:8000/path/to/file?yes=no').join(self.RI('?h%C3%A4us=h%C3%B6f'))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query, MultiDict([('häus'.encode('utf-8'), 'höf'), ('yes', 'no')]))
        self.assertEquals(ri.querystr, 'h%C3%A4us=h%C3%B6f&yes=no')

    def test_join_fragment_to_query(self):
        ri = self.RI('http://rubberchick.en/path/to/file?yes=no').join(self.RI('#giblets'))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query, MultiDict(dict(yes='no',)))
        self.assertEquals(ri.querystr, 'yes=no')
        self.assertEquals(ri.fragment, 'giblets')

    def test_join_scheme_with_path(self):
        ri = self.RI('gopher://')
        result = ri.join(self.RI('nowhere'))
        self.assertEquals(result.scheme, 'gopher')
        self.assertEquals(result.path, '/nowhere')

    def test_join_no_hostname_with_hostname(self):
        ri = self.RI('gopher://')
        result = ri.join(self.RI('//whole.org/ville'))
        self.assertEquals(result.scheme, 'gopher')
        self.assertEquals(result.hostname, 'whole.org')
        self.assertEquals(result.path, '/ville')

    def test_join_string(self):
        ri = self.RI('http://localhost:8000').join(self._literal_wrapper('/path/to/file'))
        self.assertEquals(ri.scheme, 'http')
        self.assertEquals(ri.netloc, 'localhost:8000')
        self.assertEquals(ri.path, '/path/to/file')

    def test_update_query_with_query_object_to_make_multi_query(self):
        ri = self.RI('http://localhost:8000/path/to/file?yes=no')
        ri = ri.update_query(MultiDict(dict(yes='maybe', left='right')))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query,
            MultiDict([('yes', 'no'), ('yes', 'maybe'), ('left', 'right')]))
        self.assertEquals(ri.querystr, 'yes=no&yes=maybe&left=right')

    def test_update_query_with_nonascii_query_object(self):
        ri = self.RI('http://localhost:8000/path/to/file?yes=no')
        ri = ri.update_query(MultiDict({'häus':'höf'}))
        self.assertEquals(ri.path, '/path/to/file')
        self.assertEquals(ri.query, MultiDict([('häus'.encode('utf-8'), 'höf'), ('yes', 'no')]))
        self.assertEquals(ri.querystr, 'yes=no&h%C3%A4us=h%C3%B6f')


class NormalizeCase(unittest.TestCase):
    # Test normalization
    #
    # Class variables:
    # RI = IRI/URI constructor given a unicode object

    def _literal_wrapper(self, lit):
        return lit

    def test_normalizes_empty_fragment(self):
        ri = self.RI(self._literal_wrapper('http://example.com/#'))
        self.assertEquals(ri._identifier, 'http://example.com/')

    def test_normalizes_empty_query(self):
        ri = self.RI(self._literal_wrapper('http://example.com/?'))
        self.assertEquals(ri._identifier, 'http://example.com/')

    def test_normalizes_empty_query_and_fragment(self):
        ri = self.RI(self._literal_wrapper('http://example.com/?#'))
        self.assertEquals(ri._identifier, 'http://example.com/')

########NEW FILE########
__FILENAME__ = test_iri
# encoding: utf-8
from __future__ import unicode_literals
import unittest

from nose.plugins.skip import SkipTest

from uricore import IRI, URI
from uricore.wkz_datastructures import MultiDict

import cases


class TestIRI(unittest.TestCase):

    def test_str_input_fails(self):
        self.assertRaises(TypeError, IRI, 'http://example.com'.encode('ascii'))

    def test_uri_input(self):
        iri = TestIRISnowman.ri
        uri = URI(iri)
        self.assertEquals(str(iri), str(IRI(uri)))
        self.assertEquals(unicode(iri), unicode(IRI(uri)))

    def test_repr(self):
        iri = TestIRISnowman.ri
        eval_iri = eval(repr(iri))
        self.assertEquals(iri, eval_iri)

    def test_idn_ascii_encoding(self):
        iri = IRI("http://Bücher.ch/")
        self.assertEquals(str(iri), "http://xn--bcher-kva.ch/")

    def test_convert_pile_of_poo(self):
        raise SkipTest("Not Implemented")
        uri = URI("http://u:p@www.xn--ls8h.la:80/path?q=arg#frag".encode('utf-8'))
        try:
            IRI(uri)
        except Exception as e:
            assert False, "{0} {1}".format(type(e), e)

    def test_non_existent_scheme(self):
        try:
            IRI("watwatwat://wat.wat/wat")
        except Exception as e:
            assert False, "{0} {1}".format(type(e), e)

    def test_nonascii_query_keys(self):
        IRI(u'http://example.com/?gro\xdf=great')

    def test_iri_from_lenient(self):
        lenient_iri = IRI.from_lenient(u'http://de.wikipedia.org/wiki/Elf (Begriffskl\xe4rung)')
        self.assertEquals(repr(lenient_iri), "IRI(u'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29')")


class TestIRISnowman(cases.IdentifierCase):

    ri = IRI("http://u:p@www.\N{SNOWMAN}:80/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="www.\u2603",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@www.\u2603:80",
    )


class TestIRIConvertedSnowman(cases.IdentifierCase):

    uri = URI(("http://u:p@www.%s:80/path?q=arg#frag"
               % u"\N{SNOWMAN}".encode('idna')).encode('utf-8'))
    ri = IRI(uri)
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="www.\u2603",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@www.\u2603:80",
    )


class TestIRIPileOfPoo(cases.IdentifierCase):

    ri = IRI("http://u:p@www.💩.la:80/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="www.💩.la",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@www.💩.la:80",
    )


class TestIRIIPv6(cases.IdentifierCase):

    ri = IRI("http://u:p@[2a00:1450:4001:c01::67]/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="2a00:1450:4001:c01::67",
        port=None,
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@[2a00:1450:4001:c01::67]",
    )


class TestIRIIPv6WithPort(cases.IdentifierCase):

    ri = IRI("http://u:p@[2a00:1450:4001:c01::67]:80/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="2a00:1450:4001:c01::67",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@[2a00:1450:4001:c01::67]:80",
    )


class TestIRIJoin(cases.JoinAndUpdateCase):

    RI = IRI

    def test_cannot_join_uri(self):
        self.assertRaises(TypeError,
                          IRI('http://localhost:8000').join,
                          URI(str('/path/to/file'))
                         )


class TestIRINormalizes(cases.NormalizeCase):

    RI = IRI

########NEW FILE########
__FILENAME__ = test_resource
# encoding: utf-8
import unittest

from nose.plugins.skip import SkipTest

from uricore import IRI, URI
from uricore.wkz_datastructures import MultiDict


class TestURICore(unittest.TestCase):

    def setUp(self):
        self.uri = URI("http://example.com?foo=bar")

    def test_hashability(self):
        iri1 = IRI(u'http://\N{CLOUD}/')
        iri2 = IRI(u'http://\N{CLOUD}/')
        self.assertEquals(hash(iri1), hash(iri2))

        uri1 = URI(iri1)
        uri2 = URI('http://xn--l3h/')
        self.assertEquals(hash(uri1), hash(uri2))

        self.assertNotEquals(hash(iri1), hash(uri1))

    def test_eq(self):
        iri1 = IRI(u'http://\N{CLOUD}/')
        iri2 = IRI(u'http://\N{CLOUD}/')
        self.assertEquals(iri1, iri2)

        uri1 = URI(iri1)
        uri2 = URI('http://xn--l3h/')
        self.assertEquals(uri1, uri2)

        self.assertNotEquals(iri1, uri1)

    def test_ne(self):
        iri1 = IRI(u'http://\N{CLOUD}/')
        iri2 = IRI(u'http://\N{CLOUD}/')
        self.assertFalse(iri1 != iri2)

        uri1 = URI(iri1)
        uri2 = URI('http://xn--l3h/')
        self.assertFalse(uri1 != uri2)

        self.assertTrue(iri1 != uri1)

    def test_query_param_breaks_equality_(self):
        iri = IRI(u'http://\N{CLOUD}/')
        iri2 = IRI(u'http://\N{CLOUD}/?q=a')
        self.assertNotEquals(iri, iri2)

    def test_iri_add_port(self):
        iri = IRI(u'http://\N{SNOWMAN}/')
        new_iri = iri.update(port=8000)
        self.assertEquals(iri.netloc + ':8000', new_iri.netloc)
        self.assertEquals(new_iri.port, '8000')
        self.assertEquals(iri.port, None)

    def test_iri_update_query(self):
        iri = IRI(u'http://\N{SNOWMAN}/')
        q = iri.query
        q.update({'foo': u'42'})
        iri2 = iri.update_query(q)
        self.assertNotEquals(iri, iri2)
        self.assertTrue(isinstance(iri2, IRI))
        self.assertEquals(repr(iri.query), "MultiDict([])")
        self.assertEquals(repr(iri2), "IRI(u'http://\u2603/?foo=42')")
        self.assertEquals(repr(iri2.query), "MultiDict([('foo', u'42')])")

    def test_query_is_immutable(self):
        self.uri.query.add("foo", "baz")
        self.assertEquals(set(['bar']), set(self.uri.query.getlist('foo')))

    def test_configurable_multi_dict_class(self):
        class CustomMultiDict(MultiDict):
            pass
        iri = IRI(u'http://\N{SNOWMAN}/', query_cls=CustomMultiDict)
        self.assertTrue(isinstance(iri.query, CustomMultiDict))

########NEW FILE########
__FILENAME__ = test_template
# encoding: utf-8
from uricore import URI, IRI
from nose.tools import eq_ 
from uricore.template import uri_template

class OrderedDict(object):

    def __init__(self, items):
        self._items = items

    def iteritems(self):
        return iter(self._items)


# http://tools.ietf.org/html/rfc6570#section-3.2
params = {
    'count': ("one", "two", "three"),
    'dom': ("example", "com"),
    'dub': "me/too",
    'hello': "Hello World!",
    'half': "50%",
    'var': "value",
    'who': "fred",
    'base': "http://example.com/home/",
    'path': "/foo/bar",
    'list': ("red", "green", "blue"),
    'year': ("1965", "2000", "2012"),
    'semi': ';',
    'v': 6,
    'x': 1024,
    'y': 768,
    'empty': "",
    'empty_keys': [],
    'undef': None,
    'list': ["red", "green", "blue"],
    'unicode_keys': {u'gro\xdf':u'great',},
    'numeric_keys': {1: 'hello'},
    'keys': OrderedDict([('semi', ";"), ('dot', "."), ('comma', ",")]),
}

def check_template(template, expansion):
    eq_(uri_template(template, **params), expansion)


def test_composite_values():
    yield check_template, "find{?year*}", "find?year=1965&year=2000&year=2012"
    yield check_template, "www{.dom*}", "www.example.com"


def test_form_continuation_expansion():
    yield check_template, "{&who}", "&who=fred"
    yield check_template, "{&half}", "&half=50%25"
    yield check_template, "?fixed=yes{&x}", "?fixed=yes&x=1024"
    yield check_template, "{&x,y,empty}", "&x=1024&y=768&empty="
    yield check_template, "{&x,y,undef}", "&x=1024&y=768"
    yield check_template, "{&var:3}", "&var=val"
    yield check_template, "{&list}", "&list=red,green,blue"
    yield check_template, "{&list*}", "&list=red&list=green&list=blue"
    yield check_template, "{&keys}", "&keys=semi,%3B,dot,.,comma,%2C"
    yield check_template, "{&keys*}", "&semi=%3B&dot=.&comma=%2C"


def test_form_style_expansion():
    yield check_template, "{?who}", "?who=fred"
    yield check_template, "{?half}", "?half=50%25"
    yield check_template, "{?x,y}", "?x=1024&y=768"
    yield check_template, "{?x,y,empty}", "?x=1024&y=768&empty="
    yield check_template, "{?x,y,undef}", "?x=1024&y=768"
    yield check_template, "{?var:3}", "?var=val"
    yield check_template, "{?list}", "?list=red,green,blue"
    yield check_template, "{?list*}", "?list=red&list=green&list=blue"
    yield check_template, "{?keys}", "?keys=semi,%3B,dot,.,comma,%2C"
    yield check_template, "{?keys*}", "?semi=%3B&dot=.&comma=%2C"


def test_fragment_expansion():
    yield check_template, "{#var}", "#value"
    yield check_template, "{#hello}", "#Hello%20World!"
    yield check_template, "{#half}", "#50%25"
    yield check_template, "foo{#empty}", "foo#"
    yield check_template, "foo{#undef}", "foo"
    yield check_template, "{#x,hello,y}", "#1024,Hello%20World!,768"
    yield check_template, "{#path,x}/here", "#/foo/bar,1024/here"
    yield check_template, "{#path:6}/here", "#/foo/b/here"
    yield check_template, "{#list}", "#red,green,blue"
    yield check_template, "{#list*}", "#red,green,blue"
    yield check_template, "{#keys}", "#semi,;,dot,.,comma,,"
    yield check_template, "{#keys*}", "#semi=;,dot=.,comma=,"


def test_label_expansion():
    yield check_template, "{.who}", ".fred"
    yield check_template, "{.who,who}", ".fred.fred"
    yield check_template, "{.half,who}", ".50%25.fred"
    yield check_template, "www{.dom*}", "www.example.com"
    yield check_template, "X{.var}", "X.value"
    yield check_template, "X{.empty}", "X."
    yield check_template, "X{.undef}", "X"
    yield check_template, "X{.var:3}", "X.val"
    yield check_template, "X{.list}", "X.red,green,blue"
    yield check_template, "X{.list*}", "X.red.green.blue"
    yield check_template, "X{.keys}", "X.semi,%3B,dot,.,comma,%2C"
    yield check_template, "X{.keys*}", "X.semi=%3B.dot=..comma=%2C"
    yield check_template, "X{.empty_keys}", "X"
    yield check_template, "X{.empty_keys*}", "X"


def test_path_expansion():
    yield check_template, "{/who}", "/fred"
    yield check_template, "{/who,who}", "/fred/fred"
    yield check_template, "{/half,who}", "/50%25/fred"
    yield check_template, "{/who,dub}", "/fred/me%2Ftoo"
    yield check_template, "{/var}", "/value"
    yield check_template, "{/var,empty}", "/value/"
    yield check_template, "{/var,undef}", "/value"
    yield check_template, "{/var,x}/here", "/value/1024/here"
    yield check_template, "{/var:1,var}", "/v/value"
    yield check_template, "{/list}", "/red,green,blue"
    yield check_template, "{/list*}", "/red/green/blue"
    yield check_template, "{/list*,path:4}", "/red/green/blue/%2Ffoo"
    yield check_template, "{/keys}", "/semi,%3B,dot,.,comma,%2C"
    yield check_template, "{/keys*}", "/semi=%3B/dot=./comma=%2C"


def test_path_style_expansion():
    yield check_template, "{;who}", ";who=fred"
    yield check_template, "{;half}", ";half=50%25"
    yield check_template, "{;empty}", ";empty"
    yield check_template, "{;v,empty,who}", ";v=6;empty;who=fred"
    yield check_template, "{;v,bar,who}", ";v=6;who=fred"
    yield check_template, "{;x,y}", ";x=1024;y=768"
    yield check_template, "{;x,y,empty}", ";x=1024;y=768;empty"
    yield check_template, "{;x,y,undef}", ";x=1024;y=768"
    yield check_template, "{;hello:5}", ";hello=Hello"
    yield check_template, "{;list}", ";list=red,green,blue"
    yield check_template, "{;list*}", ";list=red;list=green;list=blue"
    yield check_template, "{;keys}", ";keys=semi,%3B,dot,.,comma,%2C"
    yield check_template, "{;keys*}", ";semi=%3B;dot=.;comma=%2C"


def test_reserved_expansion():
    yield check_template, "{+var}", "value"
    yield check_template, "{+hello}", "Hello%20World!"
    yield check_template, "{+half}", "50%25"
    yield check_template, "{base}index", "http%3A%2F%2Fexample.com%2Fhome%2Findex"
    yield check_template, "{+base}index", "http://example.com/home/index"
    yield check_template, "O{+empty}X", "OX"
    yield check_template, "O{+undef}X", "OX"
    yield check_template, "{+path}/here", "/foo/bar/here"
    yield check_template, "here?ref={+path}", "here?ref=/foo/bar"
    yield check_template, "up{+path}{var}/here", "up/foo/barvalue/here"
    yield check_template, "{+x,hello,y}", "1024,Hello%20World!,768"
    yield check_template, "{+path,x}/here", "/foo/bar,1024/here"
    yield check_template, "{+path:6}/here", "/foo/b/here"
    yield check_template, "{+list}", "red,green,blue"
    yield check_template, "{+list*}", "red,green,blue"
    yield check_template, "{+keys}", "semi,;,dot,.,comma,,"
    yield check_template, "{+keys*}", "semi=;,dot=.,comma=,"


def test_simple_string_expansion():
    yield check_template, "{var}", "value"
    yield check_template, "{hello}", "Hello%20World%21"
    yield check_template, "{half}", "50%25"
    yield check_template, "O{empty}X", "OX"
    yield check_template, "O{undef}X", "OX"
    yield check_template, "{x,y}", "1024,768"
    yield check_template, "{x,hello,y}", "1024,Hello%20World%21,768"
    yield check_template, "?{x,empty}", "?1024,"
    yield check_template, "?{x,undef}", "?1024"
    yield check_template, "?{undef,y}", "?768"
    yield check_template, "{var:3}", "val"
    yield check_template, "{var:30}", "value"
    yield check_template, "{list}", "red,green,blue"
    yield check_template, "{list*}", "red,green,blue"
    yield check_template, "{keys}", "semi,%3B,dot,.,comma,%2C"
    yield check_template, "{keys*}", "semi=%3B,dot=.,comma=%2C"


def test_test_prefix_values():
    yield check_template, "{var}", "value"
    yield check_template, "{var:20}", "value"
    yield check_template, "{var:3}", "val"
    yield check_template, "{semi}", "%3B"
    yield check_template, "{semi:2}", "%3B"


def test_variable_expansion():
    yield check_template, "{count}", "one,two,three"
    yield check_template, "{count*}", "one,two,three"
    yield check_template, "{/count}", "/one,two,three"
    yield check_template, "{/count*}", "/one/two/three"
    yield check_template, "{;count}", ";count=one,two,three"
    yield check_template, "{;count*}", ";count=one;count=two;count=three"
    yield check_template, "{?count}", "?count=one,two,three"
    yield check_template, "{?count*}", "?count=one&count=two&count=three"
    yield check_template, "{&count*}", "&count=one&count=two&count=three"


def test_uri_template():
    eq_(URI("http://example.com/value"),
        URI.from_template("http://example.com/{var}", var="value"))


def test_iri_template():
    eq_(IRI(u'http://\u2603/value'),
        IRI.from_template(u'http://\N{SNOWMAN}/{var}', var='value'))
    eq_(IRI(u'http://\u2603/'),
        IRI.from_template(u'http://{domain}/', domain=u"\N{SNOWMAN}"))

def test_crazy_keys():
    yield check_template, "{?unicode_keys*}", "?gro%C3%9F=great"
    yield check_template, "{?numeric_keys*}", "?1=hello"

########NEW FILE########
__FILENAME__ = test_uri
# encoding: utf-8
import unittest

from nose.plugins.skip import SkipTest

from uricore import IRI, URI
from uricore.wkz_datastructures import MultiDict

import cases


class TestURI(unittest.TestCase):

    def test_unicode_input_fails(self):
        self.assertRaises(TypeError, URI, u"http://www.example.com/")

    def test_iri_input(self):
        uri = TestURISnowman.ri
        iri = IRI(uri)
        self.assertEquals(str(uri), str(URI(iri)))
        self.assertEquals(unicode(uri), unicode(URI(iri)))

    def test_repr(self):
        uri = TestURISnowman.ri
        eval_uri = eval(repr(uri))
        self.assertEquals(uri, eval_uri)

    def test_idn_ascii_encoding(self):
        uri = URI(u"http://Bücher.ch/".encode('utf-8'))
        self.assertEquals(str(uri), "http://xn--bcher-kva.ch/")

    def test_convert_pile_of_poo(self):
        raise SkipTest("Not Implemented")
        iri = IRI(u"http://u:p@www.💩.la:80/path?q=arg#frag")
        try:
            URI(iri)
        except Exception as e:
            assert False, "{0} {1}".format(type(e), e)

    def test_non_existent_scheme(self):
        try:
            URI("watwatwat://wat.wat/wat")
        except Exception as e:
            assert False, "{0} {1}".format(type(e), e)

    def test_uri_from_lenient(self):
        lenient_uri = URI.from_lenient(u'http://de.wikipedia.org/wiki/Elf (Begriffskl\xe4rung)'.encode('utf-8'))
        self.assertEquals(repr(lenient_uri), "URI('http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29')")


class TestURISnowman(cases.IdentifierCase):

    ri = URI("http://u:p@www.%s:80/path?q=arg#frag"
             % u"\N{SNOWMAN}".encode('idna'))
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="www.xn--n3h",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@www.xn--n3h:80",
    )


class TestURIConvertedSnowman(cases.IdentifierCase):

    iri = IRI(u"http://u:p@www.\N{SNOWMAN}:80/path?q=arg#frag")
    ri = URI(iri)
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="www.xn--n3h",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@www.xn--n3h:80",
    )


class TestURIPileOfPoo(cases.IdentifierCase):

    ri = URI("http://u:p@www.xn--ls8h.la:80/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="www.xn--ls8h.la",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@www.xn--ls8h.la:80",
    )


class TestURIIPv6(cases.IdentifierCase):

    ri = URI("http://u:p@[2a00:1450:4001:c01::67]/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="2a00:1450:4001:c01::67",
        port=None,
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@[2a00:1450:4001:c01::67]",
    )


class TestURIIPv6WithPort(cases.IdentifierCase):

    ri = URI("http://u:p@[2a00:1450:4001:c01::67]:80/path?q=arg#frag")
    expect = dict(
        scheme="http",
        auth="u:p",
        hostname="2a00:1450:4001:c01::67",
        port="80",
        path="/path",
        query=MultiDict([('q', 'arg')]),
        querystr='q=arg',
        fragment="frag",
        netloc="u:p@[2a00:1450:4001:c01::67]:80",
    )


class TestURIJoin(cases.JoinAndUpdateCase):

    RI = lambda self, s: URI(self._literal_wrapper(s), encoding='utf-8')

    def _literal_wrapper(self, lit):
        return lit.encode('utf-8')

    def test_cannot_join_uri(self):
        self.assertRaises(TypeError,
                          self.RI('http://localhost:8000').join,
                          IRI(u'/path/to/file')
                         )


class TestURINormalizes(cases.NormalizeCase):

    RI = URI

    def _literal_wrapper(self, lit):
        return lit.encode('utf-8')

########NEW FILE########
__FILENAME__ = core
# encoding: utf-8
__all__ = ['IRI', 'URI']

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from collections import defaultdict
from template import uri_template

# TODO: import these from httpcore someday
from . import wkz_urls as urls
from . import wkz_datastructures as datastructures


def build_netloc(hostname, auth=None, port=None):
    auth = "{0}@".format(auth) if auth else ""
    port = ":{0}".format(port) if port else ""
    if ':' in hostname:
        hostname = '['+hostname+']'
    if isinstance(hostname, unicode):
        return u"{0}{1}{2}".format(auth, hostname, port)
    return "{0}{1}{2}".format(auth, hostname, port)


def unsplit(**kwargs):
    parts = defaultdict(str)
    for k in kwargs:
        if kwargs[k]:
            parts[k] = kwargs[k]

    if 'netloc' in parts:
        netloc = parts['netloc']
    else:
        netloc = build_netloc(parts['hostname'], parts.get('auth'),
                              parts.get('port'))

    return urlparse.urlunsplit((
        parts['scheme'], netloc,
        parts['path'], parts['querystr'],
        parts['fragment']
    ))


def identifier_to_dict(identifier):
    fields = ('scheme', 'auth', 'hostname', 'port',
              'path', 'querystr', 'fragment')
    values = urls._uri_split(identifier)
    d = dict(zip(fields, values))

    # querystr is a str
    if isinstance(d['querystr'], unicode):
        d['querystr'] = d['querystr'].encode('utf-8')

    return d


class ResourceIdentifier(object):

    def __init__(self, identifier, query_cls=None):
        if not isinstance(identifier, basestring):
            raise TypeError("Expected str or unicode: %s", type(identifier))

        self._parts = identifier_to_dict(identifier)
        self._identifier = unsplit(**self._parts)

        # NOTE: might be better to subclass instead of pass a query_cls around
        self.query_cls = query_cls or datastructures.MultiDict

    def __repr__(self):
        return "{0}({1!r})".format(type(self).__name__, self._identifier)

    def __eq__(self, other):
        if set(self._parts.keys()) != set(other._parts.keys()):
            return False
        return all(self._parts[k] == other._parts[k] for k in self._parts.iterkeys())

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._identifier)

    @property
    def scheme(self):
        return self._parts['scheme']

    @property
    def auth(self):
        return self._parts['auth']

    @property
    def hostname(self):
        return self._parts['hostname']

    @property
    def port(self):
        return self._parts['port']

    @property
    def path(self):
        return self._parts['path']

    @property
    def querystr(self):
        return self._parts['querystr']

    @property
    def query(self):
        """Return a new instance of query_cls."""

        if not hasattr(self, '_decoded_query'):
            self._decoded_query = list(urls._url_decode_impl(
                self.querystr.split('&'), 'utf-8', False, True, 'strict'))
        return self.query_cls(self._decoded_query)

    @property
    def fragment(self):
        return self._parts['fragment']

    @property
    def netloc(self):
        return build_netloc(self.hostname, self.auth, self.port)

    def update(self, **kwargs):
        vals = dict(self._parts)
        if len(kwargs):
            vals.update(kwargs)

        return type(self)(unsplit(**vals), query_cls=self.query_cls)

    def update_query(self, qry):
        assert isinstance(qry, self.query_cls)

        vals = dict(self._parts)
        q = self.query
        q.update(qry)
        vals['querystr'] = urls.url_encode(q, encode_keys=True, charset=getattr(self, 'encoding', 'utf-8'))

        return type(self)(unsplit(**vals), query_cls=self.query_cls)

    def join(self, other):
        if isinstance(other, unicode):
            other = IRI(other)
        elif isinstance(other, str):
            other = URI(other)

        if not isinstance(other, type(self)):
            raise TypeError("Expected unicode or {0}: {1}".format(
                type(self).__name__, type(other).__name__))

        vals = dict(self._parts)

        if other.scheme:
            if self.scheme:
                raise ValueError("cannot join scheme onto %ss with scheme" %
                                 self.__class__.name)
            vals['scheme'] = other.scheme

        if other.auth:
            if self.auth:
                raise ValueError("cannot join auth onto %ss with auth" %
                                 self.__class__.name)
            vals['auth'] = other.auth

        if other.hostname:
            if self.hostname:
                raise ValueError(
                    "cannot join hostname onto %ss with hostname" %
                    self.__class__.name)
            vals['hostname'] = other.hostname
            vals['port'] = other.port

        if other.path:
            if self.querystr or self.fragment:
                raise ValueError(
                    "cannot join path onto %ss with querystr or fragment" %
                    self.__class__.name)
            vals['path'] = '/'.join([self.path, other.path]).replace('//', '/')

        if other.querystr:
            if self.fragment:
                raise ValueError(
                    "cannot join querystr onto %ss with fragment" %
                    self.__class__.name)
            query = self.query
            query.update(other.query)
            vals['querystr'] = urls.url_encode(query, encode_keys=True, charset=getattr(self, 'encoding', 'utf-8'))

        if other.fragment:
            if self.fragment:
                raise ValueError(
                    "cannot join fragment onto %ss with fragment" %
                    self.__class__.name)
            vals['fragment'] = other.fragment

        return type(self)(unsplit(**vals), query_cls=self.query_cls)

    @classmethod
    def from_template(cls, template, **kwargs):
        return cls(urls.url_unquote(uri_template(template, **kwargs)))



class IRI(ResourceIdentifier):

    def __init__(self, iri, query_cls=None):

        if isinstance(iri, unicode):
            identifier = iri
        elif isinstance(iri, ResourceIdentifier):
            identifier = unicode(iri)
        else:
            raise TypeError("iri must be unicode or IRI/URI: %s"
                            % type(iri).__name__)

        super(IRI, self).__init__(identifier, query_cls)

    def __str__(self):
        return urls.iri_to_uri(self._identifier)

    def __unicode__(self):
        return self._identifier

    @classmethod
    def from_lenient(cls, maybe_gibberish):
        return cls(urls.url_fix(maybe_gibberish.encode('utf-8')).decode('utf-8'))


class URI(ResourceIdentifier):

    def __init__(self, uri, encoding='utf-8', query_cls=None):

        if isinstance(uri, str):
            identifier = urls.iri_to_uri(uri.decode(encoding))
        elif isinstance(uri, ResourceIdentifier):
            identifier = str(uri)
        else:
            raise TypeError("uri must be str or IRI/URI: %s"
                            % type(uri).__name__)

        super(URI, self).__init__(identifier, query_cls)
        self.encoding = encoding

    def __str__(self):
        return self._identifier

    def __unicode__(self):
        return urls.uri_to_iri(self._identifier)

    @classmethod
    def from_lenient(cls, maybe_gibberish):
        return cls(urls.url_fix(maybe_gibberish))

    @classmethod
    def from_template(cls, template, **kwargs):
        return URI(IRI(urls.url_unquote(uri_template(template, **kwargs))))

########NEW FILE########
__FILENAME__ = template
import re
from uricore.wkz_urls  import url_quote


def _format_mapping(operator, item):
    try:
        k, v, mapped = item
    except ValueError:
        k, v = item
        mapped = False

    if operator in ['#', '+']:
        # From http://tools.ietf.org/html/rfc6570#section-1.5
        safe = ':/?#[]@!$&\'\"()*/+,;='
    else:
        safe = ''

    if isinstance(v, (list, tuple)):
        v = ','.join(url_quote(x, safe=safe) for x in v)
    else:
        v = url_quote(v, safe=safe)

    if operator in [';', '?', '&'] or mapped:
        if not v:
            mid = '' if operator == ';' else '='
        else:
            mid = '='

        return u"{0}{1}{2}".format(url_quote(k, safe=safe), mid, v)
    else:
        return u"{0}".format(v)


def _template_joiner(operator):
    if operator in ['#', '+', '']:
        return ','
    elif operator == '?':
        return '&'
    elif operator == '.':
        return'.'
    return operator


def _varspec_expansion(operator, varspec, data):
    portion = None
    explode = False

    if ':' in varspec:
        varspec, portion = varspec.split(':', 1)
        portion = int(portion)

    if varspec.endswith('*'):
        varspec = varspec[:-1]
        explode = True

    value = data.get(varspec)

    if value == None:
        return []

    try:
        if len(value) == 0 and value != "":
            return []
    except TypeError:
        pass

    try:
        if explode:
            return [(k, v, True) for k,v in value.iteritems()]
        else:
            parts = []
            for k, v in value.iteritems():
                parts += [k, v]
            return [(varspec, parts)]
    except AttributeError:
        pass

    if isinstance(value, (list, tuple)):
        if explode:
            return [(varspec, v) for v in value]
        else:
            return [(varspec, value)]

    value = unicode(value)

    if portion is not None:
        value = value[:portion]

    return [(varspec, value)]


def uri_template(template, **kwargs):

    def template_expansion(matchobj):
        varlist = matchobj.group(1)
        operator = ''

        if re.match(r"\+|#|\.|/|;|\?|&", varlist):
            operator = varlist[0]
            varlist = varlist[1:]

        prefix = '' if operator == '+' else operator
        joiner = _template_joiner(operator)

        params = []
        for varspec in varlist.split(','):
            params += _varspec_expansion(operator, varspec, kwargs)

        uri = [_format_mapping(operator, item) for item in params]

        if not uri:
            return ""

        return prefix + joiner.join(uri)

    return re.sub(r"{(.*?)}", template_expansion, template)

########NEW FILE########
__FILENAME__ = wkz_datastructures
from wkz_internal import _missing

class BadRequestKeyError(Exception): pass

def is_immutable(self):
    raise TypeError('%r objects are immutable' % self.__class__.__name__)


class TypeConversionDict(dict):
    """Works like a regular dict but the :meth:`get` method can perform
    type conversions.  :class:`MultiDict` and :class:`CombinedMultiDict`
    are subclasses of this class and provide the same feature.

    .. versionadded:: 0.5
    """

    def get(self, key, default=None, type=None):
        """Return the default value if the requested data doesn't exist.
        If `type` is provided and is a callable it should convert the value,
        return it or raise a :exc:`ValueError` if that is not possible.  In
        this case the function will return the default as if the value was not
        found:

        >>> d = TypeConversionDict(foo='42', bar='blub')
        >>> d.get('foo', type=int)
        42
        >>> d.get('bar', -1, type=int)
        -1

        :param key: The key to be looked up.
        :param default: The default value to be returned if the key can't
                        be looked up.  If not further specified `None` is
                        returned.
        :param type: A callable that is used to cast the value in the
                     :class:`MultiDict`.  If a :exc:`ValueError` is raised
                     by this callable the default value is returned.
        """
        try:
            rv = self[key]
            if type is not None:
                rv = type(rv)
        except (KeyError, ValueError):
            rv = default
        return rv


class MultiDict(TypeConversionDict):
    """A :class:`MultiDict` is a dictionary subclass customized to deal with
    multiple values for the same key which is for example used by the parsing
    functions in the wrappers.  This is necessary because some HTML form
    elements pass multiple values for the same key.

    :class:`MultiDict` implements all standard dictionary methods.
    Internally, it saves all values for a key as a list, but the standard dict
    access methods will only return the first value for a key. If you want to
    gain access to the other values, too, you have to use the `list` methods as
    explained below.

    Basic Usage:

    >>> d = MultiDict([('a', 'b'), ('a', 'c')])
    >>> d
    MultiDict([('a', 'b'), ('a', 'c')])
    >>> d['a']
    'b'
    >>> d.getlist('a')
    ['b', 'c']
    >>> 'a' in d
    True

    It behaves like a normal dict thus all dict functions will only return the
    first value when multiple values for one key are found.

    From Werkzeug 0.3 onwards, the `KeyError` raised by this class is also a
    subclass of the :exc:`~exceptions.BadRequest` HTTP exception and will
    render a page for a ``400 BAD REQUEST`` if caught in a catch-all for HTTP
    exceptions.

    A :class:`MultiDict` can be constructed from an iterable of
    ``(key, value)`` tuples, a dict, a :class:`MultiDict` or from Werkzeug 0.2
    onwards some keyword parameters.

    :param mapping: the initial value for the :class:`MultiDict`.  Either a
                    regular dict, an iterable of ``(key, value)`` tuples
                    or `None`.
    """

    def __init__(self, mapping=None):
        if isinstance(mapping, MultiDict):
            dict.__init__(self, ((k, l[:]) for k, l in mapping.iterlists()))
        elif isinstance(mapping, dict):
            tmp = {}
            for key, value in mapping.iteritems():
                if isinstance(value, (tuple, list)):
                    value = list(value)
                else:
                    value = [value]
                tmp[key] = value
            dict.__init__(self, tmp)
        else:
            tmp = {}
            for key, value in mapping or ():
                tmp.setdefault(key, []).append(value)
            dict.__init__(self, tmp)

    def __getstate__(self):
        return dict(self.lists())

    def __setstate__(self, value):
        dict.clear(self)
        dict.update(self, value)

    def __iter__(self):
        return self.iterkeys()

    def __getitem__(self, key):
        """Return the first data value for this key;
        raises KeyError if not found.

        :param key: The key to be looked up.
        :raise KeyError: if the key does not exist.
        """
        if key in self:
            return dict.__getitem__(self, key)[0]
        raise BadRequestKeyError(key)

    def __setitem__(self, key, value):
        """Like :meth:`add` but removes an existing key first.

        :param key: the key for the value.
        :param value: the value to set.
        """
        dict.__setitem__(self, key, [value])

    def add(self, key, value):
        """Adds a new value for the key.

        .. versionadded:: 0.6

        :param key: the key for the value.
        :param value: the value to add.
        """
        dict.setdefault(self, key, []).append(value)

    def getlist(self, key, type=None):
        """Return the list of items for a given key. If that key is not in the
        `MultiDict`, the return value will be an empty list.  Just as `get`
        `getlist` accepts a `type` parameter.  All items will be converted
        with the callable defined there.

        :param key: The key to be looked up.
        :param type: A callable that is used to cast the value in the
                     :class:`MultiDict`.  If a :exc:`ValueError` is raised
                     by this callable the value will be removed from the list.
        :return: a :class:`list` of all the values for the key.
        """
        try:
            rv = dict.__getitem__(self, key)
        except KeyError:
            return []
        if type is None:
            return list(rv)
        result = []
        for item in rv:
            try:
                result.append(type(item))
            except ValueError:
                pass
        return result

    def setlist(self, key, new_list):
        """Remove the old values for a key and add new ones.  Note that the list
        you pass the values in will be shallow-copied before it is inserted in
        the dictionary.

        >>> d = MultiDict()
        >>> d.setlist('foo', ['1', '2'])
        >>> d['foo']
        '1'
        >>> d.getlist('foo')
        ['1', '2']

        :param key: The key for which the values are set.
        :param new_list: An iterable with the new values for the key.  Old values
                         are removed first.
        """
        dict.__setitem__(self, key, list(new_list))

    def setdefault(self, key, default=None):
        """Returns the value for the key if it is in the dict, otherwise it
        returns `default` and sets that value for `key`.

        :param key: The key to be looked up.
        :param default: The default value to be returned if the key is not
                        in the dict.  If not further specified it's `None`.
        """
        if key not in self:
            self[key] = default
        else:
            default = self[key]
        return default

    def setlistdefault(self, key, default_list=None):
        """Like `setdefault` but sets multiple values.  The list returned
        is not a copy, but the list that is actually used internally.  This
        means that you can put new values into the dict by appending items
        to the list:

        >>> d = MultiDict({"foo": 1})
        >>> d.setlistdefault("foo").extend([2, 3])
        >>> d.getlist("foo")
        [1, 2, 3]

        :param key: The key to be looked up.
        :param default: An iterable of default values.  It is either copied
                        (in case it was a list) or converted into a list
                        before returned.
        :return: a :class:`list`
        """
        if key not in self:
            default_list = list(default_list or ())
            dict.__setitem__(self, key, default_list)
        else:
            default_list = dict.__getitem__(self, key)
        return default_list

    def items(self, multi=False):
        """Return a list of ``(key, value)`` pairs.

        :param multi: If set to `True` the list returned will have a
                      pair for each value of each key.  Otherwise it
                      will only contain pairs for the first value of
                      each key.

        :return: a :class:`list`
        """
        return list(self.iteritems(multi))

    def lists(self):
        """Return a list of ``(key, values)`` pairs, where values is the list of
        all values associated with the key.

        :return: a :class:`list`
        """
        return list(self.iterlists())

    def values(self):
        """Returns a list of the first value on every key's value list.

        :return: a :class:`list`.
        """
        return [self[key] for key in self.iterkeys()]

    def listvalues(self):
        """Return a list of all values associated with a key.  Zipping
        :meth:`keys` and this is the same as calling :meth:`lists`:

        >>> d = MultiDict({"foo": [1, 2, 3]})
        >>> zip(d.keys(), d.listvalues()) == d.lists()
        True

        :return: a :class:`list`
        """
        return list(self.iterlistvalues())

    def iteritems(self, multi=False):
        """Like :meth:`items` but returns an iterator."""
        for key, values in dict.iteritems(self):
            if multi:
                for value in values:
                    yield key, value
            else:
                yield key, values[0]

    def iterlists(self):
        """Like :meth:`items` but returns an iterator."""
        for key, values in dict.iteritems(self):
            yield key, list(values)

    def itervalues(self):
        """Like :meth:`values` but returns an iterator."""
        for values in dict.itervalues(self):
            yield values[0]

    def iterlistvalues(self):
        """Like :meth:`listvalues` but returns an iterator."""
        return dict.itervalues(self)

    def copy(self):
        """Return a shallow copy of this object."""
        return self.__class__(self)

    def to_dict(self, flat=True):
        """Return the contents as regular dict.  If `flat` is `True` the
        returned dict will only have the first item present, if `flat` is
        `False` all values will be returned as lists.

        :param flat: If set to `False` the dict returned will have lists
                     with all the values in it.  Otherwise it will only
                     contain the first value for each key.
        :return: a :class:`dict`
        """
        if flat:
            return dict(self.iteritems())
        return dict(self.lists())

    def update(self, other_dict):
        """update() extends rather than replaces existing key lists."""
        for key, value in iter_multi_items(other_dict):
            MultiDict.add(self, key, value)

    def pop(self, key, default=_missing):
        """Pop the first item for a list on the dict.  Afterwards the
        key is removed from the dict, so additional values are discarded:

        >>> d = MultiDict({"foo": [1, 2, 3]})
        >>> d.pop("foo")
        1
        >>> "foo" in d
        False

        :param key: the key to pop.
        :param default: if provided the value to return if the key was
                        not in the dictionary.
        """
        try:
            return dict.pop(self, key)[0]
        except KeyError, e:
            if default is not _missing:
                return default
            raise BadRequestKeyError(str(e))

    def popitem(self):
        """Pop an item from the dict."""
        try:
            item = dict.popitem(self)
            return (item[0], item[1][0])
        except KeyError, e:
            raise BadRequestKeyError(str(e))

    def poplist(self, key):
        """Pop the list for a key from the dict.  If the key is not in the dict
        an empty list is returned.

        .. versionchanged:: 0.5
           If the key does no longer exist a list is returned instead of
           raising an error.
        """
        return dict.pop(self, key, [])

    def popitemlist(self):
        """Pop a ``(key, list)`` tuple from the dict."""
        try:
            return dict.popitem(self)
        except KeyError, e:
            raise BadRequestKeyError(str(e))

    def __copy__(self):
        return self.copy()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.items(multi=True))


def iter_multi_items(mapping):
    """Iterates over the items of a mapping yielding keys and values
    without dropping any from more complex structures.
    """
    if isinstance(mapping, MultiDict):
        for item in mapping.iteritems(multi=True):
            yield item
    elif isinstance(mapping, dict):
        for key, value in mapping.iteritems():
            if isinstance(value, (tuple, list)):
                for value in value:
                    yield key, value
            else:
                yield key, value
    else:
        for item in mapping:
            yield item


class ImmutableDictMixin(object):
    """Makes a :class:`dict` immutable.

    .. versionadded:: 0.5

    :private:
    """
    _hash_cache = None

    @classmethod
    def fromkeys(cls, keys, value=None):
        instance = super(cls, cls).__new__(cls)
        instance.__init__(zip(keys, repeat(value)))
        return instance

    def __reduce_ex__(self, protocol):
        return type(self), (dict(self),)

    def _iter_hashitems(self):
        return self.iteritems()

    def __hash__(self):
        if self._hash_cache is not None:
            return self._hash_cache
        rv = self._hash_cache = hash(frozenset(self._iter_hashitems()))
        return rv

    def setdefault(self, key, default=None):
        is_immutable(self)

    def update(self, *args, **kwargs):
        is_immutable(self)

    def pop(self, key, default=None):
        is_immutable(self)

    def popitem(self):
        is_immutable(self)

    def __setitem__(self, key, value):
        is_immutable(self)

    def __delitem__(self, key):
        is_immutable(self)

    def clear(self):
        is_immutable(self)


class ImmutableMultiDictMixin(ImmutableDictMixin):
    """Makes a :class:`MultiDict` immutable.

    .. versionadded:: 0.5

    :private:
    """

    def __reduce_ex__(self, protocol):
        return type(self), (self.items(multi=True),)

    def _iter_hashitems(self):
        return self.iteritems(multi=True)

    def add(self, key, value):
        is_immutable(self)

    def popitemlist(self):
        is_immutable(self)

    def poplist(self, key):
        is_immutable(self)

    def setlist(self, key, new_list):
        is_immutable(self)

    def setlistdefault(self, key, default_list=None):
        is_immutable(self)


class ImmutableMultiDict(ImmutableMultiDictMixin, MultiDict):
    """An immutable :class:`MultiDict`.

    .. versionadded:: 0.5
    """

    def copy(self):
        """Return a shallow mutable copy of this object.  Keep in mind that
        the standard library's :func:`copy` function is a no-op for this class
        like for any other python immutable type (eg: :class:`tuple`).
        """
        return MultiDict(self)

    def __copy__(self):
        return self

########NEW FILE########
__FILENAME__ = wkz_internal
class _Missing(object):

    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_missing = _Missing()


def _decode_unicode(value, charset, errors):
    """Like the regular decode function but this one raises an
    `HTTPUnicodeError` if errors is `strict`."""
    fallback = None
    if errors.startswith('fallback:'):
        fallback = errors[9:]
        errors = 'strict'
    try:
        return value.decode(charset, errors)
    except UnicodeError, e:
        if fallback is not None:
            return value.decode(fallback, 'replace')
        from werkzeug.exceptions import HTTPUnicodeError
        raise HTTPUnicodeError(str(e))

########NEW FILE########
__FILENAME__ = wkz_urls
# -*- coding: utf-8 -*-
"""
    werkzeug.urls
    ~~~~~~~~~~~~~

    This module implements various URL related functions.

    :copyright: (c) 2011 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from wkz_internal import _decode_unicode
from wkz_datastructures import MultiDict, iter_multi_items
from wkz_wsgi import make_chunk_iter


#: list of characters that are always safe in URLs.
_always_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                'abcdefghijklmnopqrstuvwxyz'
                '0123456789_.-')
_safe_map = dict((c, c) for c in _always_safe)
for i in xrange(0x80):
    c = chr(i)
    if c not in _safe_map:
        _safe_map[c] = '%%%02X' % i
_safe_map.update((chr(i), '%%%02X' % i) for i in xrange(0x80, 0x100))
_safemaps = {}

#: lookup table for encoded characters.
_hexdig = '0123456789ABCDEFabcdef'
_hextochr = dict((a + b, chr(int(a + b, 16)))
                 for a in _hexdig for b in _hexdig)


def _quote(s, safe='/', _join=''.join):
    assert isinstance(s, str), 'quote only works on bytes'
    if not s or not s.rstrip(_always_safe + safe):
        return s
    try:
        quoter = _safemaps[safe]
    except KeyError:
        safe_map = _safe_map.copy()
        safe_map.update([(c, c) for c in safe])
        _safemaps[safe] = quoter = safe_map.__getitem__
    return _join(map(quoter, s))


def _quote_plus(s, safe=''):
    if ' ' in s:
        return _quote(s, safe + ' ').replace(' ', '+')
    return _quote(s, safe)


def _safe_urlsplit(s):
    """the urlparse.urlsplit cache breaks if it contains unicode and
    we cannot control that.  So we force type cast that thing back
    to what we think it is.
    """
    rv = urlparse.urlsplit(s)
    # we have to check rv[2] here and not rv[1] as rv[1] will be
    # an empty bytestring in case no domain was given.
    if type(rv[2]) is not type(s):
        assert hasattr(urlparse, 'clear_cache')
        urlparse.clear_cache()
        rv = urlparse.urlsplit(s)
        assert type(rv[2]) is type(s)
    return rv


def _unquote(s, unsafe=''):
    assert isinstance(s, str), 'unquote only works on bytes'
    rv = s.split('%')
    if len(rv) == 1:
        return s
    s = rv[0]
    for item in rv[1:]:
        try:
            char = _hextochr[item[:2]]
            if char in unsafe:
                raise KeyError()
            s += char + item[2:]
        except KeyError:
            s += '%' + item
    return s


def _unquote_plus(s):
    return _unquote(s.replace('+', ' '))


def _uri_split(uri):
    """Splits up an URI or IRI."""
    scheme, netloc, path, query, fragment = _safe_urlsplit(uri)

    auth = None
    port = None

    if '@' in netloc:
        auth, netloc = netloc.split('@', 1)

    if netloc.startswith('['):
        host, port_part = netloc[1:].split(']', 1)
        if port_part.startswith(':'):
            port = port_part[1:]
    elif ':' in netloc:
        host, port = netloc.split(':', 1)
    else:
        host = netloc
    return scheme, auth, host, port, path, query, fragment


def iri_to_uri(iri, charset='utf-8'):
    r"""Converts any unicode based IRI to an acceptable ASCII URI.  Werkzeug
    always uses utf-8 URLs internally because this is what browsers and HTTP
    do as well.  In some places where it accepts an URL it also accepts a
    unicode IRI and converts it into a URI.

    Examples for IRI versus URI:

    >>> iri_to_uri(u'http://☃.net/')
    'http://xn--n3h.net/'
    >>> iri_to_uri(u'http://üser:pässword@☃.net/påth')
    'http://%C3%BCser:p%C3%A4ssword@xn--n3h.net/p%C3%A5th'

    .. versionadded:: 0.6

    :param iri: the iri to convert
    :param charset: the charset for the URI
    """
    iri = unicode(iri)
    scheme, auth, hostname, port, path, query, fragment = _uri_split(iri)

    scheme = scheme.encode('ascii')
    hostname = hostname.encode('idna')

    if ':' in hostname:
        hostname = '[' + hostname + ']'

    if auth:
        if ':' in auth:
            auth, password = auth.split(':', 1)
        else:
            password = None
        auth = _quote(auth.encode(charset))
        if password:
            auth += ':' + _quote(password.encode(charset))
        hostname = auth + '@' + hostname
    if port:
        hostname += ':' + port

    path = _quote(path.encode(charset), safe="/:~+%")
    query = _quote(query.encode(charset), safe="=%&[]:;$()+,!?*/")

    # this absolutely always must return a string.  Otherwise some parts of
    # the system might perform double quoting (#61)
    return str(urlparse.urlunsplit([scheme, hostname, path, query, fragment]))


def uri_to_iri(uri, charset='utf-8', errors='replace'):
    r"""Converts a URI in a given charset to a IRI.

    Examples for URI versus IRI

    >>> uri_to_iri('http://xn--n3h.net/')
    u'http://\u2603.net/'
    >>> uri_to_iri('http://%C3%BCser:p%C3%A4ssword@xn--n3h.net/p%C3%A5th')
    u'http://\xfcser:p\xe4ssword@\u2603.net/p\xe5th'

    Query strings are left unchanged:

    >>> uri_to_iri('/?foo=24&x=%26%2f')
    u'/?foo=24&x=%26%2f'

    .. versionadded:: 0.6

    :param uri: the URI to convert
    :param charset: the charset of the URI
    :param errors: the error handling on decode
    """
    uri = url_fix(str(uri), charset)
    scheme, auth, hostname, port, path, query, fragment = _uri_split(uri)

    scheme = _decode_unicode(scheme, 'ascii', errors)

    try:
        hostname = hostname.decode('idna')
    except UnicodeError:
        # dammit, that codec raised an error.  Because it does not support
        # any error handling we have to fake it.... badly
        if errors not in ('ignore', 'replace'):
            raise
        hostname = hostname.decode('ascii', errors)

    if ':' in hostname:
        hostname = '[' + hostname + ']'

    if auth:
        if ':' in auth:
            auth, password = auth.split(':', 1)
        else:
            password = None
        auth = _decode_unicode(_unquote(auth), charset, errors)
        if password:
            auth += u':' + _decode_unicode(_unquote(password),
                                           charset, errors)
        hostname = auth + u'@' + hostname
    if port:
        # port should be numeric, but you never know...
        hostname += u':' + port.decode(charset, errors)

    path = _decode_unicode(_unquote(path, '/;?'), charset, errors)
    query = _decode_unicode(_unquote(query, ';/?:@&=+,$'),
                            charset, errors)

    return urlparse.urlunsplit([scheme, hostname, path, query, fragment])


def url_decode(s, charset='utf-8', decode_keys=False, include_empty=True,
               errors='replace', separator='&', cls=None):
    """Parse a querystring and return it as :class:`MultiDict`.  Per default
    only values are decoded into unicode strings.  If `decode_keys` is set to
    `True` the same will happen for keys.

    Per default a missing value for a key will default to an empty key.  If
    you don't want that behavior you can set `include_empty` to `False`.

    Per default encoding errors are ignored.  If you want a different behavior
    you can set `errors` to ``'replace'`` or ``'strict'``.  In strict mode a
    `HTTPUnicodeError` is raised.

    .. versionchanged:: 0.5
       In previous versions ";" and "&" could be used for url decoding.
       This changed in 0.5 where only "&" is supported.  If you want to
       use ";" instead a different `separator` can be provided.

       The `cls` parameter was added.

    :param s: a string with the query string to decode.
    :param charset: the charset of the query string.
    :param decode_keys: set to `True` if you want the keys to be decoded
                        as well.
    :param include_empty: Set to `False` if you don't want empty values to
                          appear in the dict.
    :param errors: the decoding error behavior.
    :param separator: the pair separator to be used, defaults to ``&``
    :param cls: an optional dict class to use.  If this is not specified
                       or `None` the default :class:`MultiDict` is used.
    """
    if cls is None:
        cls = MultiDict
    return cls(_url_decode_impl(str(s).split(separator), charset, decode_keys,
                                include_empty, errors))


def url_decode_stream(stream, charset='utf-8', decode_keys=False,
                      include_empty=True, errors='replace', separator='&',
                      cls=None, limit=None, return_iterator=False):
    """Works like :func:`url_decode` but decodes a stream.  The behavior
    of stream and limit follows functions like
    :func:`~werkzeug.wsgi.make_line_iter`.  The generator of pairs is
    directly fed to the `cls` so you can consume the data while it's
    parsed.

    .. versionadded:: 0.8

    :param stream: a stream with the encoded querystring
    :param charset: the charset of the query string.
    :param decode_keys: set to `True` if you want the keys to be decoded
                        as well.
    :param include_empty: Set to `False` if you don't want empty values to
                          appear in the dict.
    :param errors: the decoding error behavior.
    :param separator: the pair separator to be used, defaults to ``&``
    :param cls: an optional dict class to use.  If this is not specified
                       or `None` the default :class:`MultiDict` is used.
    :param limit: the content length of the URL data.  Not necessary if
                  a limited stream is provided.
    :param return_iterator: if set to `True` the `cls` argument is ignored
                            and an iterator over all decoded pairs is
                            returned
    """
    if return_iterator:
        cls = lambda x: x
    elif cls is None:
        cls = MultiDict
    pair_iter = make_chunk_iter(stream, separator, limit)
    return cls(_url_decode_impl(pair_iter, charset, decode_keys,
                                include_empty, errors))


def _url_decode_impl(pair_iter, charset, decode_keys, include_empty,
                     errors):
    for pair in pair_iter:
        if not pair:
            continue
        if '=' in pair:
            key, value = pair.split('=', 1)
        else:
            if not include_empty:
                continue
            key = pair
            value = ''
        key = _unquote_plus(key)
        if decode_keys:
            key = _decode_unicode(key, charset, errors)
        yield key, url_unquote_plus(value, charset, errors)


def url_encode(obj, charset='utf-8', encode_keys=False, sort=False, key=None,
               separator='&'):
    """URL encode a dict/`MultiDict`.  If a value is `None` it will not appear
    in the result string.  Per default only values are encoded into the target
    charset strings.  If `encode_keys` is set to ``True`` unicode keys are
    supported too.

    If `sort` is set to `True` the items are sorted by `key` or the default
    sorting algorithm.

    .. versionadded:: 0.5
        `sort`, `key`, and `separator` were added.

    :param obj: the object to encode into a query string.
    :param charset: the charset of the query string.
    :param encode_keys: set to `True` if you have unicode keys.
    :param sort: set to `True` if you want parameters to be sorted by `key`.
    :param separator: the separator to be used for the pairs.
    :param key: an optional function to be used for sorting.  For more details
                check out the :func:`sorted` documentation.
    """
    return separator.join(_url_encode_impl(obj, charset, encode_keys, sort, key))


def url_encode_stream(obj, stream=None, charset='utf-8', encode_keys=False,
                      sort=False, key=None, separator='&'):
    """Like :meth:`url_encode` but writes the results to a stream
    object.  If the stream is `None` a generator over all encoded
    pairs is returned.

    .. versionadded:: 0.8

    :param obj: the object to encode into a query string.
    :param stream: a stream to write the encoded object into or `None` if
                   an iterator over the encoded pairs should be returned.  In
                   that case the separator argument is ignored.
    :param charset: the charset of the query string.
    :param encode_keys: set to `True` if you have unicode keys.
    :param sort: set to `True` if you want parameters to be sorted by `key`.
    :param separator: the separator to be used for the pairs.
    :param key: an optional function to be used for sorting.  For more details
                check out the :func:`sorted` documentation.
    """
    gen = _url_encode_impl(obj, charset, encode_keys, sort, key)
    if stream is None:
        return gen
    for idx, chunk in enumerate(gen):
        if idx:
            stream.write(separator)
        stream.write(chunk)


def _url_encode_impl(obj, charset, encode_keys, sort, key):
    iterable = iter_multi_items(obj)
    if sort:
        iterable = sorted(iterable, key=key)
    for key, value in iterable:
        if value is None:
            continue
        if encode_keys and isinstance(key, unicode):
            key = key.encode(charset)
        else:
            key = str(key)
        if isinstance(value, unicode):
            value = value.encode(charset)
        else:
            value = str(value)
        yield '%s=%s' % (_quote(key), _quote_plus(value))


def url_quote(s, charset='utf-8', safe='/:'):
    """URL encode a single string with a given encoding.

    :param s: the string to quote.
    :param charset: the charset to be used.
    :param safe: an optional sequence of safe characters.
    """
    if isinstance(s, unicode):
        s = s.encode(charset)
    elif not isinstance(s, str):
        s = str(s)
    return _quote(s, safe=safe)


def url_quote_plus(s, charset='utf-8', safe=''):
    """URL encode a single string with the given encoding and convert
    whitespace to "+".

    :param s: the string to quote.
    :param charset: the charset to be used.
    :param safe: an optional sequence of safe characters.
    """
    if isinstance(s, unicode):
        s = s.encode(charset)
    elif not isinstance(s, str):
        s = str(s)
    return _quote_plus(s, safe=safe)


def url_unquote(s, charset='utf-8', errors='replace'):
    """URL decode a single string with a given decoding.

    Per default encoding errors are ignored.  If you want a different behavior
    you can set `errors` to ``'replace'`` or ``'strict'``.  In strict mode a
    `HTTPUnicodeError` is raised.

    :param s: the string to unquote.
    :param charset: the charset to be used.
    :param errors: the error handling for the charset decoding.
    """
    if isinstance(s, unicode):
        s = s.encode(charset)
    return _decode_unicode(_unquote(s), charset, errors)


def url_unquote_plus(s, charset='utf-8', errors='replace'):
    """URL decode a single string with the given decoding and decode
    a "+" to whitespace.

    Per default encoding errors are ignored.  If you want a different behavior
    you can set `errors` to ``'replace'`` or ``'strict'``.  In strict mode a
    `HTTPUnicodeError` is raised.

    :param s: the string to unquote.
    :param charset: the charset to be used.
    :param errors: the error handling for the charset decoding.
    """
    if isinstance(s, unicode):
        s = s.encode(charset)
    return _decode_unicode(_unquote_plus(s), charset, errors)


def url_fix(s, charset='utf-8'):
    r"""Sometimes you get an URL by a user that just isn't a real URL because
    it contains unsafe characters like ' ' and so on.  This function can fix
    some of the problems in a similar way browsers handle data entered by the
    user:

    >>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffskl\xe4rung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    :param s: the string with the URL to fix.
    :param charset: The target charset for the URL if the url was given as
                    unicode string.
    """
    if isinstance(s, unicode):
        s = s.encode(charset, 'replace')
    scheme, netloc, path, qs, anchor = _safe_urlsplit(s)
    path = _quote(path, '/%')
    qs = _quote_plus(qs, ':&%=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

########NEW FILE########
__FILENAME__ = wkz_wsgi
class LimitedStream(object):
    """Wraps a stream so that it doesn't read more than n bytes.  If the
    stream is exhausted and the caller tries to get more bytes from it
    :func:`on_exhausted` is called which by default returns an empty
    string.  The return value of that function is forwarded
    to the reader function.  So if it returns an empty string
    :meth:`read` will return an empty string as well.

    The limit however must never be higher than what the stream can
    output.  Otherwise :meth:`readlines` will try to read past the
    limit.

    The `silent` parameter has no effect if :meth:`is_exhausted` is
    overriden by a subclass.

    .. versionchanged:: 0.6
       Non-silent usage was deprecated because it causes confusion.
       If you want that, override :meth:`is_exhausted` and raise a
       :exc:`~exceptions.BadRequest` yourself.

    .. admonition:: Note on WSGI compliance

       calls to :meth:`readline` and :meth:`readlines` are not
       WSGI compliant because it passes a size argument to the
       readline methods.  Unfortunately the WSGI PEP is not safely
       implementable without a size argument to :meth:`readline`
       because there is no EOF marker in the stream.  As a result
       of that the use of :meth:`readline` is discouraged.

       For the same reason iterating over the :class:`LimitedStream`
       is not portable.  It internally calls :meth:`readline`.

       We strongly suggest using :meth:`read` only or using the
       :func:`make_line_iter` which safely iterates line-based
       over a WSGI input stream.

    :param stream: the stream to wrap.
    :param limit: the limit for the stream, must not be longer than
                  what the string can provide if the stream does not
                  end with `EOF` (like `wsgi.input`)
    :param silent: If set to `True` the stream will allow reading
                   past the limit and will return an empty string.
    """

    def __init__(self, stream, limit, silent=True):
        self._read = stream.read
        self._readline = stream.readline
        self._pos = 0
        self.limit = limit
        self.silent = silent
        if not silent:
            from warnings import warn
            warn(DeprecationWarning('non-silent usage of the '
            'LimitedStream is deprecated.  If you want to '
            'continue to use the stream in non-silent usage '
            'override on_exhausted.'), stacklevel=2)

    def __iter__(self):
        return self

    @property
    def is_exhausted(self):
        """If the stream is exhausted this attribute is `True`."""
        return self._pos >= self.limit

    def on_exhausted(self):
        """This is called when the stream tries to read past the limit.
        The return value of this function is returned from the reading
        function.
        """
        if self.silent:
            return ''
        from werkzeug.exceptions import BadRequest
        raise BadRequest('input stream exhausted')

    def on_disconnect(self):
        """What should happen if a disconnect is detected?  The return
        value of this function is returned from read functions in case
        the client went away.  By default a
        :exc:`~werkzeug.exceptions.ClientDisconnected` exception is raised.
        """
        from werkzeug.exceptions import ClientDisconnected
        raise ClientDisconnected()

    def exhaust(self, chunk_size=1024 * 16):
        """Exhaust the stream.  This consumes all the data left until the
        limit is reached.

        :param chunk_size: the size for a chunk.  It will read the chunk
                           until the stream is exhausted and throw away
                           the results.
        """
        to_read = self.limit - self._pos
        chunk = chunk_size
        while to_read > 0:
            chunk = min(to_read, chunk)
            self.read(chunk)
            to_read -= chunk

    def read(self, size=None):
        """Read `size` bytes or if size is not provided everything is read.

        :param size: the number of bytes read.
        """
        if self._pos >= self.limit:
            return self.on_exhausted()
        if size is None or size == -1:  # -1 is for consistence with file
            size = self.limit
        to_read = min(self.limit - self._pos, size)
        try:
            read = self._read(to_read)
        except (IOError, ValueError):
            return self.on_disconnect()
        if to_read and len(read) != to_read:
            return self.on_disconnect()
        self._pos += len(read)
        return read

    def readline(self, size=None):
        """Reads one line from the stream."""
        if self._pos >= self.limit:
            return self.on_exhausted()
        if size is None:
            size = self.limit - self._pos
        else:
            size = min(size, self.limit - self._pos)
        try:
            line = self._readline(size)
        except (ValueError, IOError):
            return self.on_disconnect()
        if size and not line:
            return self.on_disconnect()
        self._pos += len(line)
        return line

    def readlines(self, size=None):
        """Reads a file into a list of strings.  It calls :meth:`readline`
        until the file is read to the end.  It does support the optional
        `size` argument if the underlaying stream supports it for
        `readline`.
        """
        last_pos = self._pos
        result = []
        if size is not None:
            end = min(self.limit, last_pos + size)
        else:
            end = self.limit
        while 1:
            if size is not None:
                size -= last_pos - self._pos
            if self._pos >= end:
                break
            result.append(self.readline(size))
            if size is not None:
                last_pos = self._pos
        return result

    def tell(self):
        """Returns the position of the stream.

        .. versionadded:: 0.9
        """
        return self._pos

    def next(self):
        line = self.readline()
        if line is None:
            raise StopIteration()
        return line


def make_limited_stream(stream, limit):
    """Makes a stream limited."""
    if not isinstance(stream, LimitedStream):
        if limit is None:
            raise TypeError('stream not limited and no limit provided.')
        stream = LimitedStream(stream, limit)
    return stream


def make_chunk_iter(stream, separator, limit=None, buffer_size=10 * 1024):
    """Works like :func:`make_line_iter` but accepts a separator
    which divides chunks.  If you want newline based processing
    you should use :func:`make_limited_stream` instead as it
    supports arbitrary newline markers.

    .. versionadded:: 0.8

    .. versionadded:: 0.9
       added support for iterators as input stream.

    :param stream: the stream or iterate to iterate over.
    :param separator: the separator that divides chunks.
    :param limit: the limit in bytes for the stream.  (Usually
                  content length.  Not necessary if the `stream`
                  is a :class:`LimitedStream`.
    :param buffer_size: The optional buffer size.
    """
    _read = make_chunk_iter_func(stream, limit, buffer_size)
    _split = re.compile(r'(%s)' % re.escape(separator)).split
    buffer = []
    while 1:
        new_data = _read()
        if not new_data:
            break
        chunks = _split(new_data)
        new_buf = []
        for item in chain(buffer, chunks):
            if item == separator:
                yield ''.join(new_buf)
                new_buf = []
            else:
                new_buf.append(item)
        buffer = new_buf
    if buffer:
        yield ''.join(buffer)


########NEW FILE########
