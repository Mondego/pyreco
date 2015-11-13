__FILENAME__ = test_dicttoxml
from xmltodict import parse, unparse, OrderedDict

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import re
import collections
from textwrap import dedent

_HEADER_RE = re.compile(r'^[^\n]*\n')


def _strip(fullxml):
    return _HEADER_RE.sub('', fullxml)


class DictToXMLTestCase(unittest.TestCase):
    def test_root(self):
        obj = {'a': None}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_simple_cdata(self):
        obj = {'a': 'b'}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_cdata(self):
        obj = {'a': {'#text': 'y'}}
        self.assertEqual(obj, parse(unparse(obj), force_cdata=True))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_attrib(self):
        obj = {'a': {'@href': 'x'}}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_attrib_and_cdata(self):
        obj = {'a': {'@href': 'x', '#text': 'y'}}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_list(self):
        obj = {'a': {'b': ['1', '2', '3']}}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_multiple_roots(self):
        self.assertRaises(ValueError, unparse, {'a': '1', 'b': '2'})
        self.assertRaises(ValueError, unparse, {'a': ['1', '2', '3']})

    def test_nested(self):
        obj = {'a': {'b': '1', 'c': '2'}}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))
        obj = {'a': {'b': {'c': {'@a': 'x', '#text': 'y'}}}}
        self.assertEqual(obj, parse(unparse(obj)))
        self.assertEqual(unparse(obj), unparse(parse(unparse(obj))))

    def test_semistructured(self):
        xml = '<a>abc<d/>efg</a>'
        self.assertEqual(_strip(unparse(parse(xml))),
                         '<a><d></d>abcefg</a>')

    if hasattr(collections, 'OrderedDict'):
        def test_preprocessor(self):
            obj = {'a': OrderedDict((('b:int', [1, 2]), ('b', 'c')))}

            def p(key, value):
                try:
                    key, _ = key.split(':')
                except ValueError:
                    pass
                return key, value

            self.assertEqual(_strip(unparse(obj, preprocessor=p)),
                             '<a><b>1</b><b>2</b><b>c</b></a>')

    def test_preprocessor_skipkey(self):
        obj = {'a': {'b': 1, 'c': 2}}

        def p(key, value):
            if key == 'b':
                return None
            return key, value

        self.assertEqual(_strip(unparse(obj, preprocessor=p)),
                         '<a><c>2</c></a>')

    if hasattr(collections, 'OrderedDict'):
        def test_attr_order_roundtrip(self):
            xml = '<root a="1" b="2" c="3"></root>'
            self.assertEqual(xml, _strip(unparse(parse(xml))))

    if hasattr(collections, 'OrderedDict'):
        def test_pretty_print(self):
            obj = {'a': OrderedDict((
                ('b', [{'c': [1, 2]}, 3]),
                ('x', 'y'),
            ))}
            newl = '\n'
            indent = '....'
            xml = dedent('''\
            <?xml version="1.0" encoding="utf-8"?>
            <a>
            ....<b>
            ........<c>1</c>
            ........<c>2</c>
            ....</b>
            ....<b>3</b>
            ....<x>y</x>
            </a>''')
            self.assertEqual(xml, unparse(obj, pretty=True,
                                          newl=newl, indent=indent))

    def test_encoding(self):
        try:
            value = unichr(39321)
        except NameError:
            value = chr(39321)
        obj = {'a': value}
        utf8doc = unparse(obj, encoding='utf-8')
        latin1doc = unparse(obj, encoding='iso-8859-1')
        self.assertEqual(parse(utf8doc), parse(latin1doc))
        self.assertEqual(parse(utf8doc), obj)

    def test_fulldoc(self):
        xml_declaration_re = re.compile(
            '^' + re.escape('<?xml version="1.0" encoding="utf-8"?>'))
        self.assertTrue(xml_declaration_re.match(unparse({'a': 1})))
        self.assertFalse(
            xml_declaration_re.match(unparse({'a': 1}, full_document=False)))

########NEW FILE########
__FILENAME__ = test_xmltodict
from xmltodict import parse, ParsingInterrupted

try:
    import unittest2 as unittest
except ImportError:
    import unittest
try:
    from io import BytesIO as StringIO
except ImportError:
    from xmltodict import StringIO


def _encode(s):
    try:
        return bytes(s, 'ascii')
    except (NameError, TypeError):
        return s


class XMLToDictTestCase(unittest.TestCase):

    def test_string_vs_file(self):
        xml = '<a>data</a>'
        self.assertEqual(parse(xml),
                         parse(StringIO(_encode(xml))))

    def test_minimal(self):
        self.assertEqual(parse('<a/>'),
                         {'a': None})
        self.assertEqual(parse('<a/>', force_cdata=True),
                         {'a': None})

    def test_simple(self):
        self.assertEqual(parse('<a>data</a>'),
                         {'a': 'data'})

    def test_force_cdata(self):
        self.assertEqual(parse('<a>data</a>', force_cdata=True),
                         {'a': {'#text': 'data'}})

    def test_custom_cdata(self):
        self.assertEqual(parse('<a>data</a>',
                               force_cdata=True,
                               cdata_key='_CDATA_'),
                         {'a': {'_CDATA_': 'data'}})

    def test_list(self):
        self.assertEqual(parse('<a><b>1</b><b>2</b><b>3</b></a>'),
                         {'a': {'b': ['1', '2', '3']}})

    def test_attrib(self):
        self.assertEqual(parse('<a href="xyz"/>'),
                         {'a': {'@href': 'xyz'}})

    def test_skip_attrib(self):
        self.assertEqual(parse('<a href="xyz"/>', xml_attribs=False),
                         {'a': None})

    def test_custom_attrib(self):
        self.assertEqual(parse('<a href="xyz"/>',
                               attr_prefix='!'),
                         {'a': {'!href': 'xyz'}})

    def test_attrib_and_cdata(self):
        self.assertEqual(parse('<a href="xyz">123</a>'),
                         {'a': {'@href': 'xyz', '#text': '123'}})

    def test_semi_structured(self):
        self.assertEqual(parse('<a>abc<b/>def</a>'),
                         {'a': {'b': None, '#text': 'abcdef'}})
        self.assertEqual(parse('<a>abc<b/>def</a>',
                               cdata_separator='\n'),
                         {'a': {'b': None, '#text': 'abc\ndef'}})

    def test_nested_semi_structured(self):
        self.assertEqual(parse('<a>abc<b>123<c/>456</b>def</a>'),
                         {'a': {'#text': 'abcdef', 'b': {
                             '#text': '123456', 'c': None}}})

    def test_skip_whitespace(self):
        xml = """
        <root>


          <emptya>           </emptya>
          <emptyb attr="attrvalue">


          </emptyb>
          <value>hello</value>
        </root>
        """
        self.assertEqual(
            parse(xml),
            {'root': {'emptya': None,
                      'emptyb': {'@attr': 'attrvalue'},
                      'value': 'hello'}})

    def test_keep_whitespace(self):
        xml = "<root> </root>"
        self.assertEqual(parse(xml), dict(root=None))
        self.assertEqual(parse(xml, strip_whitespace=False),
                         dict(root=' '))

    def test_streaming(self):
        def cb(path, item):
            cb.count += 1
            self.assertEqual(path, [('a', {'x': 'y'}), ('b', None)])
            self.assertEqual(item, str(cb.count))
            return True
        cb.count = 0
        parse('<a x="y"><b>1</b><b>2</b><b>3</b></a>',
              item_depth=2, item_callback=cb)
        self.assertEqual(cb.count, 3)

    def test_streaming_interrupt(self):
        cb = lambda path, item: False
        self.assertRaises(ParsingInterrupted,
                          parse, '<a>x</a>',
                          item_depth=1, item_callback=cb)

    def test_postprocessor(self):
        def postprocessor(path, key, value):
            try:
                return key + ':int', int(value)
            except (ValueError, TypeError):
                return key, value
        self.assertEqual({'a': {'b:int': [1, 2], 'b': 'x'}},
                         parse('<a><b>1</b><b>2</b><b>x</b></a>',
                               postprocessor=postprocessor))

    def test_postprocessor_skip(self):
        def postprocessor(path, key, value):
            if key == 'b':
                value = int(value)
                if value == 3:
                    return None
            return key, value
        self.assertEqual({'a': {'b': [1, 2]}},
                         parse('<a><b>1</b><b>2</b><b>3</b></a>',
                               postprocessor=postprocessor))

    def test_unicode(self):
        try:
            value = unichr(39321)
        except NameError:
            value = chr(39321)
        self.assertEqual({'a': value},
                         parse('<a>%s</a>' % value))

    def test_encoded_string(self):
        try:
            value = unichr(39321)
        except NameError:
            value = chr(39321)
        xml = '<a>%s</a>' % value
        self.assertEqual(parse(xml),
                         parse(xml.encode('utf-8')))

    def test_namespace_support(self):
        xml = """
        <root xmlns="http://defaultns.com/"
              xmlns:a="http://a.com/"
              xmlns:b="http://b.com/">
          <x>1</x>
          <a:y>2</a:y>
          <b:z>3</b:z>
        </root>
        """
        d = {
            'http://defaultns.com/:root': {
                'http://defaultns.com/:x': '1',
                'http://a.com/:y': '2',
                'http://b.com/:z': '3',
            }
        }
        self.assertEqual(parse(xml, process_namespaces=True), d)

    def test_namespace_collapse(self):
        xml = """
        <root xmlns="http://defaultns.com/"
              xmlns:a="http://a.com/"
              xmlns:b="http://b.com/">
          <x>1</x>
          <a:y>2</a:y>
          <b:z>3</b:z>
        </root>
        """
        namespaces = {
            'http://defaultns.com/': None,
            'http://a.com/': 'ns_a',
        }
        d = {
            'root': {
                'x': '1',
                'ns_a:y': '2',
                'http://b.com/:z': '3',
            },
        }
        self.assertEqual(
            parse(xml, process_namespaces=True, namespaces=namespaces), d)

    def test_namespace_ignore(self):
        xml = """
        <root xmlns="http://defaultns.com/"
              xmlns:a="http://a.com/"
              xmlns:b="http://b.com/">
          <x>1</x>
          <a:y>2</a:y>
          <b:z>3</b:z>
        </root>
        """
        d = {
            'root': {
                '@xmlns': 'http://defaultns.com/',
                '@xmlns:a': 'http://a.com/',
                '@xmlns:b': 'http://b.com/',
                'x': '1',
                'a:y': '2',
                'b:z': '3',
            },
        }
        self.assertEqual(parse(xml), d)

########NEW FILE########
__FILENAME__ = xmltodict
#!/usr/bin/env python
"Makes working with XML feel like you are working with JSON"

from xml.parsers import expat
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
try:  # pragma no cover
    from cStringIO import StringIO
except ImportError:  # pragma no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
try:  # pragma no cover
    from collections import OrderedDict
except ImportError:  # pragma no cover
    try:
        from ordereddict import OrderedDict
    except ImportError:
        OrderedDict = dict

try:  # pragma no cover
    _basestring = basestring
except NameError:  # pragma no cover
    _basestring = str
try:  # pragma no cover
    _unicode = unicode
except NameError:  # pragma no cover
    _unicode = str

__author__ = 'Martin Blech'
__version__ = '0.9.0'
__license__ = 'MIT'


class ParsingInterrupted(Exception):
    pass


class _DictSAXHandler(object):
    def __init__(self,
                 item_depth=0,
                 item_callback=lambda *args: True,
                 xml_attribs=True,
                 attr_prefix='@',
                 cdata_key='#text',
                 force_cdata=False,
                 cdata_separator='',
                 postprocessor=None,
                 dict_constructor=OrderedDict,
                 strip_whitespace=True,
                 namespace_separator=':',
                 namespaces=None):
        self.path = []
        self.stack = []
        self.data = None
        self.item = None
        self.item_depth = item_depth
        self.xml_attribs = xml_attribs
        self.item_callback = item_callback
        self.attr_prefix = attr_prefix
        self.cdata_key = cdata_key
        self.force_cdata = force_cdata
        self.cdata_separator = cdata_separator
        self.postprocessor = postprocessor
        self.dict_constructor = dict_constructor
        self.strip_whitespace = strip_whitespace
        self.namespace_separator = namespace_separator
        self.namespaces = namespaces

    def _build_name(self, full_name):
        if not self.namespaces:
            return full_name
        i = full_name.rfind(self.namespace_separator)
        if i == -1:
            return full_name
        namespace, name = full_name[:i], full_name[i+1:]
        short_namespace = self.namespaces.get(namespace, namespace)
        if not short_namespace:
            return name
        else:
            return self.namespace_separator.join((short_namespace, name))

    def _attrs_to_dict(self, attrs):
        if isinstance(attrs, dict):
            return attrs
        return self.dict_constructor(zip(attrs[0::2], attrs[1::2]))

    def startElement(self, full_name, attrs):
        name = self._build_name(full_name)
        attrs = self._attrs_to_dict(attrs)
        self.path.append((name, attrs or None))
        if len(self.path) > self.item_depth:
            self.stack.append((self.item, self.data))
            if self.xml_attribs:
                attrs = self.dict_constructor(
                    (self.attr_prefix+key, value)
                    for (key, value) in attrs.items())
            else:
                attrs = None
            self.item = attrs or None
            self.data = None

    def endElement(self, full_name):
        name = self._build_name(full_name)
        if len(self.path) == self.item_depth:
            item = self.item
            if item is None:
                item = self.data
            should_continue = self.item_callback(self.path, item)
            if not should_continue:
                raise ParsingInterrupted()
        if len(self.stack):
            item, data = self.item, self.data
            self.item, self.data = self.stack.pop()
            if self.strip_whitespace and data is not None:
                data = data.strip() or None
            if data and self.force_cdata and item is None:
                item = self.dict_constructor()
            if item is not None:
                if data:
                    self.push_data(item, self.cdata_key, data)
                self.item = self.push_data(self.item, name, item)
            else:
                self.item = self.push_data(self.item, name, data)
        else:
            self.item = self.data = None
        self.path.pop()

    def characters(self, data):
        if not self.data:
            self.data = data
        else:
            self.data += self.cdata_separator + data

    def push_data(self, item, key, data):
        if self.postprocessor is not None:
            result = self.postprocessor(self.path, key, data)
            if result is None:
                return item
            key, data = result
        if item is None:
            item = self.dict_constructor()
        try:
            value = item[key]
            if isinstance(value, list):
                value.append(data)
            else:
                item[key] = [value, data]
        except KeyError:
            item[key] = data
        return item


def parse(xml_input, encoding=None, expat=expat, process_namespaces=False,
          namespace_separator=':', **kwargs):
    """Parse the given XML input and convert it into a dictionary.

    `xml_input` can either be a `string` or a file-like object.

    If `xml_attribs` is `True`, element attributes are put in the dictionary
    among regular child elements, using `@` as a prefix to avoid collisions. If
    set to `False`, they are just ignored.

    Simple example::

        >>> import xmltodict
        >>> doc = xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>
        ... \"\"\")
        >>> doc['a']['@prop']
        u'x'
        >>> doc['a']['b']
        [u'1', u'2']

    If `item_depth` is `0`, the function returns a dictionary for the root
    element (default behavior). Otherwise, it calls `item_callback` every time
    an item at the specified depth is found and returns `None` in the end
    (streaming mode).

    The callback function receives two parameters: the `path` from the document
    root to the item (name-attribs pairs), and the `item` (dict). If the
    callback's return value is false-ish, parsing will be stopped with the
    :class:`ParsingInterrupted` exception.

    Streaming example::

        >>> def handle(path, item):
        ...     print 'path:%s item:%s' % (path, item)
        ...     return True
        ...
        >>> xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>\"\"\", item_depth=2, item_callback=handle)
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:1
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:2

    The optional argument `postprocessor` is a function that takes `path`,
    `key` and `value` as positional arguments and returns a new `(key, value)`
    pair where both `key` and `value` may have changed. Usage example::

        >>> def postprocessor(path, key, value):
        ...     try:
        ...         return key + ':int', int(value)
        ...     except (ValueError, TypeError):
        ...         return key, value
        >>> xmltodict.parse('<a><b>1</b><b>2</b><b>x</b></a>',
        ...                 postprocessor=postprocessor)
        OrderedDict([(u'a', OrderedDict([(u'b:int', [1, 2]), (u'b', u'x')]))])

    You can pass an alternate version of `expat` (such as `defusedexpat`) by
    using the `expat` parameter. E.g:

        >>> import defusedexpat
        >>> xmltodict.parse('<a>hello</a>', expat=defusedexpat.pyexpat)
        OrderedDict([(u'a', u'hello')])

    """
    handler = _DictSAXHandler(namespace_separator=namespace_separator,
                              **kwargs)
    if isinstance(xml_input, _unicode):
        if not encoding:
            encoding = 'utf-8'
        xml_input = xml_input.encode(encoding)
    if not process_namespaces:
        namespace_separator = None
    parser = expat.ParserCreate(
        encoding,
        namespace_separator
    )
    try:
        parser.ordered_attributes = True
    except AttributeError:
        # Jython's expat does not support ordered_attributes
        pass
    parser.StartElementHandler = handler.startElement
    parser.EndElementHandler = handler.endElement
    parser.CharacterDataHandler = handler.characters
    parser.buffer_text = True
    try:
        parser.ParseFile(xml_input)
    except (TypeError, AttributeError):
        parser.Parse(xml_input, True)
    return handler.item


def _emit(key, value, content_handler,
          attr_prefix='@',
          cdata_key='#text',
          depth=0,
          preprocessor=None,
          pretty=False,
          newl='\n',
          indent='\t'):
    if preprocessor is not None:
        result = preprocessor(key, value)
        if result is None:
            return
        key, value = result
    if not isinstance(value, (list, tuple)):
        value = [value]
    if depth == 0 and len(value) > 1:
        raise ValueError('document with multiple roots')
    for v in value:
        if v is None:
            v = OrderedDict()
        elif not isinstance(v, dict):
            v = _unicode(v)
        if isinstance(v, _basestring):
            v = OrderedDict(((cdata_key, v),))
        cdata = None
        attrs = OrderedDict()
        children = []
        for ik, iv in v.items():
            if ik == cdata_key:
                cdata = iv
                continue
            if ik.startswith(attr_prefix):
                attrs[ik[len(attr_prefix):]] = iv
                continue
            children.append((ik, iv))
        if pretty:
            content_handler.ignorableWhitespace(depth * indent)
        content_handler.startElement(key, AttributesImpl(attrs))
        if pretty and children:
            content_handler.ignorableWhitespace(newl)
        for child_key, child_value in children:
            _emit(child_key, child_value, content_handler,
                  attr_prefix, cdata_key, depth+1, preprocessor,
                  pretty, newl, indent)
        if cdata is not None:
            content_handler.characters(cdata)
        if pretty and children:
            content_handler.ignorableWhitespace(depth * indent)
        content_handler.endElement(key)
        if pretty and depth:
            content_handler.ignorableWhitespace(newl)


def unparse(input_dict, output=None, encoding='utf-8', full_document=True,
            **kwargs):
    """Emit an XML document for the given `input_dict` (reverse of `parse`).

    The resulting XML document is returned as a string, but if `output` (a
    file-like object) is specified, it is written there instead.

    Dictionary keys prefixed with `attr_prefix` (default=`'@'`) are interpreted
    as XML node attributes, whereas keys equal to `cdata_key`
    (default=`'#text'`) are treated as character data.

    The `pretty` parameter (default=`False`) enables pretty-printing. In this
    mode, lines are terminated with `'\n'` and indented with `'\t'`, but this
    can be customized with the `newl` and `indent` parameters.

    """
    ((key, value),) = input_dict.items()
    must_return = False
    if output is None:
        output = StringIO()
        must_return = True
    content_handler = XMLGenerator(output, encoding)
    if full_document:
        content_handler.startDocument()
    _emit(key, value, content_handler, **kwargs)
    if full_document:
        content_handler.endDocument()
    if must_return:
        value = output.getvalue()
        try:  # pragma no cover
            value = value.decode(encoding)
        except AttributeError:  # pragma no cover
            pass
        return value

if __name__ == '__main__':  # pragma: no cover
    import sys
    import marshal

    (item_depth,) = sys.argv[1:]
    item_depth = int(item_depth)

    def handle_item(path, item):
        marshal.dump((path, item), sys.stdout)
        return True

    try:
        root = parse(sys.stdin,
                     item_depth=item_depth,
                     item_callback=handle_item,
                     dict_constructor=dict)
        if item_depth == 0:
            handle_item([], root)
    except KeyboardInterrupt:
        pass

########NEW FILE########
