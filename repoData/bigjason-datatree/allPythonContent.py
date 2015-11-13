__FILENAME__ = base
from copy import deepcopy

from datatree.tree import Vertex, InstructionNode

class Renderer(object):
    @property
    def friendly_names(self):
        raise NotImplementedError()

    def render_node(self, node, options={}):
        raise NotImplementedError()

    def render_final(self, rendered, options={}):
        raise NotImplementedError()

    def render_native(self, options={}):
        raise NotImplementedError('No render_native() method is provided for this renderer.')

    def render(self, base_node, options):
        """Renders the entire tree under base_node as a string."""
        return self.render_final(self.render_node(base_node, options=options), options=options)

class InternalRenderer(Renderer):
    """Base class for included renderers."""
    friendly_names = []

    ### Node Methods ###

    def data_only(self, node):
        """Return all DATA child nodes only."""
        return self.__filter(node, Vertex)

    def instruction_only(self, node):
        """Return all instruct child nodes only."""
        return self.__filter(node, InstructionNode)

    def __filter(self, node, node_type):
        return [x for x in node.__children__ if isinstance(x, node_type)]

    ### Option Methods ###

    @property
    def default_options(self):
        raise NotImplementedError()

    def get_options(self, user_options):
        if user_options is None: user_options = {}
        options = deepcopy(self.default_options)
        options.update(user_options)
        return options

########NEW FILE########
__FILENAME__ = dictrender
"""
Outputs the tree as python dict.  It is available under the alias ``'dict'`` 
and ``'dictionary'``.

Options
-------

================= ============================================================== ===========
Name              Description                                                    Default
================= ============================================================== ===========
pretty_string     When True, outputs the ``dict`` as a string with pretty        ``False``
                  formatting.
allow_node_loss   Determines if a duplicate node name will result in a node      ``False`` 
                  loss due to duplicate keys in the dict.
================= ============================================================== ===========

Example Output
--------------
.. code-block:: python

    tree('dict', pretty_string=True)

.. code-block:: python 

    {'author': {'genre': 'Fantasy/Comedy',
                'name': 'Terry Pratchett',
                'novels': ['Small Gods', 'The Fifth Elephant', 'Guards! Guards!']}}

Duplicate Node Names
--------------------
While xml handles duplicate nodes just fine, python dicts and json for that matter
do not allow duplicates.  To handle this the DictRenderer will attempt to
group nodes with the same name into a sub dictionary. This is why in the above 
example there is only one key for "novels".

"""

from pprint import pformat

from datatree.render.base import InternalRenderer
from datatree.tree import Tree

class DictRenderer(InternalRenderer):
    default_options = {
        'pretty_string': False,
        'allow_node_loss': False
    }

    def _children_distinct_names(self, children):
        return set([c.__node_name__ for c in children])

    # TODO: Figure out how to handle attributes here.
    def render_node(self, node, parent=None, options=None):
        if parent is None: parent = {}
        if options is None: options = {}
        user_options = self.get_options(options)
        children = self.data_only(node)

        if children:
            children_names = self._children_distinct_names(children)
            if len(children) > 1 and \
               len(children_names) == 1:
                value = []
            elif (len(children) > 1 and \
                  len(children_names) > 1 and \
                  len(children_names) != len(children)) and \
                  not user_options['allow_node_loss']:
                raise NodeLossError()
            else:
                value = {}
            for child in children:
                self.render_node(child, value, options=options)
        else:
            value = node.__value__

        if isinstance(node, Tree):
            parent = value
        elif isinstance(parent, dict):
            parent[node.__node_name__] = value
        else:
            parent.append(value)
        return parent

    def render_final(self, rendered, options=None):
        options = self.get_options(options)
        if options.get('pretty_string', False):
            return pformat(rendered)
        else:
            return rendered

# TODO: Move this class to a more general location.
class NodeLossError(Exception):
    def __init__(self, msg='One or more nodes were lost due to duplicate keys.'):
        super(NodeLossError, self).__init__(msg)

########NEW FILE########
__FILENAME__ = jsonrender
"""
Outputs the tree as json string using the python json module.  It is available
under the alias ``'json'``, ``'jsn'`` or ``'js'``.

Options
-------

=========  ================================================= ==========
Name       Description                                       Default
=========  ================================================= ==========
pretty     Outputs the json document with pretty formatting. ``False``
sort_keys  Sorts the keys in the json document.              ``False``
=========  ================================================= ==========

Example Output
--------------
.. code-block:: python

    tree('json', pretty=True)

.. code-block:: js 

    {
        "author": {
            "genre": "Fantasy/Comedy", 
            "name": "Terry Pratchett", 
            "novels": [
                "Small Gods", 
                "The Fifth Elephant", 
                "Guards! Guards!"
            ]
        }
    }
        
"""
from json import dumps

from .dictrender import DictRenderer

class JsonRenderer(DictRenderer):
    default_options = {
        'pretty': False,
        'sort_keys': False
    }

    def _get_opts_kw(self, opts):
        result = {}
        if opts.get('pretty'):
            result["indent"] = 4
        result['sort_keys'] = opts.get('sort_keys')
        return result

    def render(self, base_node, options=None):
        """Renders the entire tree under base_node as a json string."""
        if options is None: options = {}
        used_options = self.get_options(options)
        kwargs = self._get_opts_kw(used_options)
        return dumps(self.render_final(self.render_node(base_node, options=used_options), options=used_options), **kwargs)

########NEW FILE########
__FILENAME__ = xmlrenderer
"""
Outputs the tree as an xml string.  It is available under the alias ``'xml'``.

Options
-------

======= ============================================================== ===========
Name    Description                                                    Default
======= ============================================================== ===========
pretty  When True, Outputs the xml document with pretty formatting.    ``False``
indent  Used with pretty formatting.  It is the string that will       ``'    '``
        be used to indent each level.
======= ============================================================== ===========

Example Output
--------------
.. code-block:: python

    tree('xml', pretty=True)

Or even shorter:

.. code-block:: python

    tree(pretty=True)

.. code-block:: xml 

    <author>
        <name>Terry Pratchett</name>
        <genre>Fantasy/Comedy</genre>
        <!-- Only 2 books listed -->
        <novels count="2">
            <novel year="1992">Small Gods</novel>
            <novel year="1999">The Fifth Elephant</novel>
            <novel year="1989">Guards! Guards!</novel>
        </novels>
    </author>
"""
from xml.sax.saxutils import escape, quoteattr
from StringIO import StringIO # TODO: cStringIO has no unicode support. Do we care?

from datatree.render.base import InternalRenderer
from datatree.symbols import Symbol
from datatree.tree import (Tree,
                           CDataNode,
                           CommentNode,
                           DeclarationNode,
                           InstructionNode)

class XmlRenderer(InternalRenderer):
    """
    Custom xml provider to support full xml options.
    """
    default_options = {
        'pretty': False,
        'indent': '    '
    }

    def render_node(self, node, doc=None, options=None, level=0):
        options = self.get_options(options)
        if isinstance(node, Tree): level = -1
        indent = options['indent'] * level if options['pretty'] else ''
        newline = '\n' if options.get('pretty') else ''

        def safe_str(val):
            return str(val) if val is not None else ''

        def safe_quote(val):
            return val.replace('"', '&quot;')

        def start_line_str():
            return "{0}{1}".format(newline, indent)

        def start_line():
            if options['pretty'] and doc.len > 0:
                doc.write(start_line_str())

        def render_children():
            for child in node.__children__:
                self.render_node(child, doc=doc, level=level + 1,
                                 options=options)

        def data_node():
            attributes = self.get_attrs_str(node.__attributes__)
            if not node.__children__ and node.__value__ is None:
                doc.write('<{0} {1}{2}/>'.format(node.__node_name__,
                                                 attributes,
                                                 ' ' if attributes else ''))
            else:
                doc.write('<{0}{1}{2}>'.format(node.__node_name__,
                                               ' ' if attributes else '',
                                               attributes))
                if node.__value__ is not None:
                    if len(node.__children__) > 0:
                        doc.write(newline)
                        doc.write(indent)
                    doc.write(escape(str(node.__value__)))

                render_children()

                if len(node.__children__) > 0:
                    doc.write(newline)
                    doc.write(indent)
                doc.write('</{0}>'.format(node.__node_name__))

        def comment_node():
            doc.write('<!-- {0} -->'.format(safe_str(node.__value__).strip()))

        def instruct_node():
            attrs = {}
            if node.__node_name__ == 'xml':
                attrs['version'] = '1.0'
                attrs['encoding'] = 'UTF-8'
            attrs.update(node.__attributes__)
            attrs_str = self.get_attrs_str(attrs)

            doc.write('<?{0}{1}{2}?>'.format(node.__node_name__,
                                             ' ' if attrs_str else '',
                                             attrs_str))

        def declare_node():
            # Don't use standard attrib render.
            attrs = []
            for a in node.__declaration_params__:
                if isinstance(a, Symbol):
                    attrs.append(str(a))
                else:
                    attrs.append('"{0}"'.format(safe_quote(safe_str(a))))
            if attrs:
                attrs_str = ' ' + ' '.join(attrs)
            else:
                attrs_str = ''

            doc.write('<!{0}{1}>'.format(node.__node_name__, attrs_str))

        def cdata_node():
            # Attrs are ignored for cdata
            doc.write('<![cdata[{0}]]>'.format(safe_str(node.__value__)))

        ## Actual flow of render starts here ##

        if doc is None:
            doc = StringIO()

        if isinstance(node, Tree):
            render_children()
        elif isinstance(node, CommentNode):
            start_line()
            comment_node()
        elif isinstance(node, InstructionNode):
            start_line()
            instruct_node()
        elif isinstance(node, DeclarationNode):
            start_line()
            declare_node()
        elif isinstance(node, CDataNode):
            start_line()
            cdata_node()
        else:
            start_line()
            data_node()

        return doc.getvalue()

    def render_final(self, rendered, options=None):
        return rendered

    @staticmethod
    def get_attrs_str(attrs):
        attrs = ('{0}={1}'.format(key, quoteattr(str(value)))
        for key, value in attrs.iteritems())
        return ' '.join(attrs).strip()

########NEW FILE########
__FILENAME__ = yamlrender
"""
Outputs the tree as yaml string using the `PyYAML <http://pypi.python.org/pypi/PyYAML/>`_
package (which must be installed).  It is available under the alias ``'yaml'``
or ``'yml'``.

Options
-------

=========  ================================================= ===========
Name       Description                                       Default
=========  ================================================= ===========
*None*
=========  ================================================= ===========

Example Output
--------------
.. code-block:: python

    tree('yaml')

.. code-block:: yaml 

    author:
      genre: Fantasy/Comedy
      name: Terry Pratchett
      novels: [Small Gods, The Fifth Elephant, Guards! Guards!]
        
"""

from yaml import dump
try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from .dictrender import DictRenderer

class YamlRenderer(DictRenderer):
    default_options = {
    }

    def render(self, base_node, options=None):
        """Renders the entire tree under base_node as a json string."""
        if options is None: options = {}
        return dump(self.render_final(self.render_node(base_node, options=options), options=options), Dumper=Dumper)

########NEW FILE########
__FILENAME__ = symbols

class Symbol(object):
    """A symbol is used to represent a string, usually one that is intended to
    be rendered as unquoted.
    """
    def __init__(self, name):
        self.name = name

    def __getattr__(self, name):
        self.__dict__[name] = result = self.__dict__.get(name, self.__class__(name))
        return result
    
    def __str__(self):
        return self.name
    
    def __getitem__(self, name):
        return self.__getattr__(name)

########NEW FILE########
__FILENAME__ = base
import logging

from datatree import Tree

logger = logging.getLogger(__name__)

class NodeTestBase(object):
    """
    Base class used to aid in testing.
    """

    def get_unified_tree(self):
        tree = Tree()
        with tree.node("author") as author:
            author.node('name', 'Terry Pratchett')
            author.node('genre', 'Fantasy/Comedy')
            with author.node('novels', count=2) as novels:
                novels.node('novel', 'Small Gods', year=1992)
                novels.node('novel', 'The Fifth Elephant', year=1999)
                novels.node('novel', 'Feet of Clay', year=1996)
        return tree

    def get_unified_dict(self):
        return {
            "author": {
                "name": 'Terry Pratchett',
                'genre': 'Fantasy/Comedy',
                'novels': [
                    'Small Gods',
                    'The Fifth Elephant',
                    'Feet of Clay'
                ]
            }
        }

    def get_dirty_tree(self):
        tree = Tree()
        with tree.node("author") as author:
            author.node('name', 'Terry Pratchett')
            with author.node('genre') as genre:
                genre.node('fantasy', 'true')
                genre.node('comedy', 'true')
                genre.node('horror', 'false')
        return tree

    def get_dirty_dict(self):
        return {
            "author": {
                "name": 'Terry Pratchett',
                'genre': {
                    'fantasy': 'true',
                    'comedy': 'true',
                    'horror': 'false'
                }
            }
        }

    def get_flat_tree(self):
        tree = Tree()
        with tree.node("author") as author:
            author.node('name', 'Terry Pratchett')
            author.node('genre', 'Fantasy/Comedy')
        return tree

    def get_flat_dict(self):
        return {
            "author": {
                "name": 'Terry Pratchett',
                'genre': 'Fantasy/Comedy',
                }
        }

    def test_tree_exists(self):
        assert self.get_dirty_tree() is not None
        assert self.get_unified_tree() is not None


########NEW FILE########
__FILENAME__ = test_dictrenderer
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datatree import Tree
from datatree.tests.base import NodeTestBase
from datatree.render.dictrender import DictRenderer, NodeLossError

class test_DictRenderer(unittest.TestCase, NodeTestBase):
    def test_nested_render(self):
        self.assertDictEqual(
            self.get_dirty_tree().render('dict'),
            self.get_dirty_dict()
        )

    def test_flat_render(self):
        self.assertDictEqual(
            self.get_flat_tree()('dict'),
            self.get_flat_dict()
        )

    def test_children_distinct_names(self):
        tree = Tree()
        with tree.node('tree') as root:
            root.node('person', 'One')
            root.node('person', 'Two')
            root.node('person', 'Three')

        render = DictRenderer()
        self.assertSetEqual(
            render._children_distinct_names(root.__children__),
            set(["person"])
        )

    def test_children_distinct_names_are_different(self):
        tree = Tree()
        with tree.node('root') as root:
            root.node('person', 'One')
            root.node('different', 'Two')
            root.node('strokes', 'Three')
        render = DictRenderer()
        self.assertSetEqual(
            render._children_distinct_names(root.__children__),
            set(["person", "different", "strokes"])
        )

    def test_duplicate_nodes_conversion(self):
        self.assertDictEqual(
            self.get_unified_tree()('dict'),
            self.get_unified_dict()
        )

    def get_lossy_tree(self):
        tree = Tree()
        with tree.node('root', 'tale') as root:
            root.node('level', 'absurd')
            root.node('level', 'stupid')
            root.node('handle', 'lame')
        return tree

    def test_duplicate_nodes_nodelosserror(self):
        with self.assertRaises(NodeLossError):
            self.get_lossy_tree()('dict')

    def test_render_option_allow_node_loss(self):
        self.assertDictEqual(
            self.get_lossy_tree()('dict', allow_node_loss=True),
                {
                'root': {
                    'level': 'stupid',
                    'handle': 'lame'
                }
            }
        )

    def test_add_node_return(self):
        tree = Tree()
        root = tree.node('root')
        self.assertEqual(root, tree.__children__[0])

    def test_run_as_callable(self):
        tree = Tree()

        with tree.node('root') as root:
            root.node('item', 1)

        actual = tree('dict')
        expected = {'root': {'item': 1}}
        self.assertDictEqual(actual, expected)

    def test_render_pretty_string(self):
        self.assertIn(
            'Terry Pratchett',
            self.get_unified_tree()('dict', pretty_string=True)
        )

########NEW FILE########
__FILENAME__ = test_jsonrenderer
from json import loads
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datatree import Tree
from datatree.tests.base import NodeTestBase

class test_JsonRenderer(unittest.TestCase, NodeTestBase):
    def json_to_dict(self, json):
        return loads(json)

    def test_nested_render(self):
        self.assertDictEqual(
            self.json_to_dict(self.get_dirty_tree().render('json')),
            self.get_dirty_dict()
        )

    def test_flat_render(self):
        self.assertDictEqual(
            self.json_to_dict(self.get_flat_tree()('json')),
            self.get_flat_dict()
        )

    def test_nested_render_pretty(self):
        self.assertDictEqual(
            self.json_to_dict(self.get_dirty_tree().render('json', pretty=True)),
            self.get_dirty_dict()
        )
########NEW FILE########
__FILENAME__ = test_node
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datatree import Node, Tree
from datatree.tests.base import NodeTestBase

class test_Node(unittest.TestCase, NodeTestBase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_single_level(self):
        root = Node('a', 'Here', href='url', title='A Title')

        self.assertEqual(root.__node_name__, 'a')
        self.assertEqual(root.__attributes__['href'], 'url')
        self.assertEqual(root.__attributes__['title'], 'A Title')
        self.assertEqual(root.__value__, 'Here')

    def test_nested(self):
        root = Node('one')
        root.node('item1', 1)
        with root.node('nested1') as nested:
            nested.node('nested2', 'two')

        self.assertEqual(root.__node_name__, 'one')
        self.assertEqual(root.__children__[0].__value__, 1)
        self.assertEqual(root.__children__[1].__children__[0].__value__, 'two')

    def test_context_manager(self):
        root = Node()
        with root as actual:
            self.assertEqual(root, actual)

    def test_add_node(self):
        root = Node('level1', 'two', some='attr')
        root.add_node(root)

        child = root.__children__[0]
        self.assertEqual(child.__node_name__, 'level1')
        self.assertEqual(child.__value__, 'two')
        self.assertDictEqual(child.__attributes__, {'some': 'attr'})

    def test_add_child_node(self):
        tree = Tree()
        node = tree.node('A Value')
        self.assertEqual(tree.__children__[0], node)

    def test_add_duplicate_nodes(self):
        root = Node()
        root.node('greeting', 'Hello')
        root.node('greeting', 'Hi')

        hello = root.__children__[0]
        hi = root.__children__[1]

        self.assertEqual(hello.__value__, 'Hello')
        self.assertEqual(hi.__value__, 'Hi')
        for child in root.__children__:
            self.assertEqual(child.__node_name__, 'greeting')

    def test_callable_render(self):
        root = Node()
        root.node('item', 1)

        actual = str(root())
        self.assertIn("root", actual)
        self.assertIn("item", actual)

    def test_to_string(self):
        self.assertIsInstance(
            self.get_unified_tree().to_string(),
            basestring
        )

    def test_render_child_node_as_root(self):
        tree = Tree()
        with tree.node('root') as root:
            child = root.node('name')
            child.node('first', 'Bob')
            child.node('last', 'Wiley')

        self.assertIsInstance(
            child.render(),
            basestring
        )
########NEW FILE########
__FILENAME__ = test_rendererbase
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datatree.render.base import Renderer, InternalRenderer
from datatree import Tree

class test_Renderer(unittest.TestCase):

    def test_friendly_names_error(self):
        with self.assertRaises(NotImplementedError):
            self.assertListEqual(Renderer().friendly_names, [])

    def test_friendly_names_ok(self):
        class Tester(Renderer):
            friendly_names = ['A']
            
        self.assertListEqual(Tester().friendly_names, ['A'])
        
    def test_required_methods(self):
        r = Renderer()
        with self.assertRaises(NotImplementedError):
            r.friendly_names()
        with self.assertRaises(NotImplementedError):
            r.render_node(None)
        with self.assertRaises(NotImplementedError):
            r.render_final(None)
        with self.assertRaises(NotImplementedError):
            r.render_native(None)

class test_InternalRenderer(unittest.TestCase):
    
    def test_default_options_not_implemented(self):
        r = InternalRenderer()
        with self.assertRaises(NotImplementedError):
            r.default_options

    def _get_test_tree(self):
        tree = Tree()
        tree.instruct()
        tree.node('name', 'Bob')
        tree.node('age', 12)
        return tree
            
    def test_data_only(self):
        actual = len(InternalRenderer().data_only(self._get_test_tree()))
        self.assertEqual(actual, 2)
        
    def test_instruction_only(self):
        actual = len(InternalRenderer().instruction_only(self._get_test_tree()))
        self.assertEqual(actual, 1)

########NEW FILE########
__FILENAME__ = test_symbol
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datatree.symbols import Symbol

tester = Symbol('tester')

class test_Symbol(unittest.TestCase):

    def test_one_level(self):
        self.assertEqual(tester.test, tester.test)
        self.assertIs(tester.test, tester.test)

    def test_nested(self):
        self.assertEqual(tester.test.real, tester.test.real)
        self.assertIs(tester.test.real, tester.test.real)
        self.assertFalse(tester.real is tester.test.real, 'Nested should not equal not nested.')

    def test_to_str(self):
        self.assertEqual(str(tester.testme), 'testme')

    def test_to_str_nested(self):
        self.assertEqual(str(tester.testme.testme), 'testme')
        
    def test_accessor_special_char_str(self):
        self.assertEqual(str(tester['A Name']), 'A Name')
        self.assertEqual(str(tester['A Name!']), 'A Name!')
        
    def test_accessor_special_char(self):
        self.assertIs(tester['Another Name'], tester['Another Name'])

    def test_accessor_special_char_nested(self):
        self.assertIs(tester["Root Node"]["Nested One"], tester["Root Node"]["Nested One"])
        
    def test_accessor(self):
        self.assertIsNotNone(tester["Who Has?"])
########NEW FILE########
__FILENAME__ = test_tree
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datatree import Tree

class test_Tree(unittest.TestCase):
    pass # TODO: Revisit. Does this need its own tests?

########NEW FILE########
__FILENAME__ = test_xmlrenderer
try:
    import unittest2 as unittest
except ImportError:
    import unittest
try:
    import xml.etree.cElementTree as e
except ImportError:
    import xml.etree.ElementTree as e

from datatree import Tree, __
from datatree.render.xmlrenderer import XmlRenderer

class test_XmlRenderer(unittest.TestCase):
    def test_get_attrs_str(self):
        input = {'age': '<b>300</b>', 'weight': 225}
        actual = XmlRenderer.get_attrs_str(input)

        self.assertIn('age=', actual)
        self.assertIn('&lt;b&gt;300&lt;/b&gt;"', actual,
                      "Age was not escaped properly")
        self.assertIn("weight=", actual)
        self.assertIn('"225"', actual,
                      "weight was not quoted properly")

    def get_author(self):
        tree = Tree()        
        with tree.node('author', rating="<b>5/6 Stars</b>") as author:
            author.node('name', 'Terry Pratchett')
            author.node('genere', 'Fantasy/Comedy')
            author.node('country', abbreviation="UK")
            author.node('living')
            with author.node('novels', count=2) as novels:
                novels.node('novel', 'Small Gods', year=1992)
                novels.node('novel', 'The Fifth Elephant', year=1999)
                with novels.node('shorts', count=2) as shorts:
                    shorts.node('short', "Short Story 1")
                    shorts.node('short', "Short Story 2")
        return tree
            
    def test_render_multi_levels(self):
        author = self.get_author()
        actual = e.fromstring(author.render('xml'))
        
        self.assertEqual(actual.find('name').text, 'Terry Pratchett')
        self.assertEqual(actual.find('.//shorts').attrib['count'], '2')

    def test_render_comment(self):
        tree = Tree()
        tree.node('root').comment("Something Here")
        self.assertIn('<!-- Something Here -->', tree('xml'))

    def test_render_cdata_string(self):
        tree = Tree()
        tree.node('root').cdata("Some Value")
        self.assertIn('<![cdata[Some Value]]>', tree('xml'))
        
    def test_render_cdata_not_string(self):
        int_val = 1234567891011121314151617181920
        tree = Tree()
        tree.node('root').cdata(int_val)
        self.assertIn('<![cdata[{0}]]>'.format(str(int_val)), tree('xml'))
        
    def test_render_declaration(self):
        tree = Tree()
        tree.declare('ELEMENT', __.Value, 'A value here.')
        self.assertIn(tree(), r'<!ELEMENT Value "A value here.">')

    def test_render_declaration_no_values(self):
        tree = Tree()
        tree.declare('ELEMENT')
        self.assertIn(tree(), r'<!ELEMENT>')

    def test_render_instruction_xml(self):
        tree = Tree()
        tree.instruct('xml')
        self.assertIn(tree(), '<?xml version="1.0" encoding="UTF-8"?>')
        
    def test_render_instruction(self):
        tree = Tree()
        tree.instruct('process', do="Good")
        self.assertIn(tree(), '<?process do="Good"?>')

    def _get_complex_structure(self):        
        tree = Tree()
        tree.instruct('xml')
        #tree.cdata(r"<b>I am some text.</b>")
        tree.declare('DOCTYPE', __.author, __.SYSTEM,  'SomeDTD.dtd')
        with tree.node('author') as author:
            author.node('name', 'Terry Pratchett')
            author.node('genre', 'Fantasy/Comedy')
            author.comment("Only 2 books listed")
            with author.node('novels', count=2) as novels:
                novels.node('novel', 'Small Gods', year=1992)
                novels.node('novel', 'The Fifth Elephant', year=1999)
        return tree

    def test_parse_complex_doc(self):
        tree = self._get_complex_structure()
        etree = e.fromstring(tree())
        self.assertEqual(etree.find('.//genre').text, 'Fantasy/Comedy')
        self.assertEqual(len(etree.findall('.//novel')), 2)
        
    def test_parse_complex_doc_pretty(self):
        tree = self._get_complex_structure()
        etree = e.fromstring(tree(pretty=True))
        self.assertEqual(etree.find('.//genre').text, 'Fantasy/Comedy')
        self.assertEqual(len(etree.findall('.//novel')), 2)

    def test_data_node_with_children_and_text(self):
        tree = Tree()
        with tree.node('a', 'A', href="http://bigjason.com") as a:
            a.node('b', "Link")
        self.assertEqual(
            tree(),
            '<a href="http://bigjason.com">A<b>Link</b></a>'
        )

########NEW FILE########
__FILENAME__ = test_yamlrenderer
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
    
from datatree import Tree
from datatree.tests.base import NodeTestBase

class test_YamlRenderer(unittest.TestCase, NodeTestBase):
    def yaml_to_dict(self, yaml_text):
        return load(yaml_text, Loader=Loader)

    def test_nested_render(self):
        self.assertDictEqual(
            self.yaml_to_dict(self.get_dirty_tree().render('yaml')),
            self.get_dirty_dict()
        )

    def test_flat_render(self):
        self.assertDictEqual(
            self.yaml_to_dict(self.get_flat_tree()('yaml')),
            self.get_flat_dict()
        )


########NEW FILE########
__FILENAME__ = tree
from StringIO import StringIO

from .symbols import Symbol
from .utils import get_class

__all__ = ['Tree', 'Node', 'n', 'Name', '__']

Name = Symbol('Name')
__ = Name

_plugins = [
    [("xml",), 'datatree.render.xmlrenderer.XmlRenderer'],
    [('dict', 'dictionary'), 'datatree.render.dictrender.DictRenderer'],
    [('json', 'jsn', 'js'), 'datatree.render.jsonrender.JsonRenderer'],
    [('yaml', 'yml'), 'datatree.render.yamlrender.YamlRenderer']
]

class BaseNode(object):
    def __init__(self, node_name='root', node_value=None, node_parent=None,
                 node_namespace=None, **attributes):
        """

        :param node_name: The name identifier for the node.  Default value is
            ``'root'``.
        :param node_value: The value of this node.  Note that this will be
            converted to a string usually during rendering.  Default is ``None``
            which generally means it is ignored during rendering.
        :param node_parent: The parent node if any.
        :param node_namespace: The declared namespace for the ``Node``.  A dict
        :param attributes:
        """
        self.__children__ = []
        self.__node_name__ = node_name
        self.__value__ = node_value
        self.__parent__ = node_parent
        self.__name_space__ = node_namespace
        self.__attributes__ = attributes

    @staticmethod
    def register_renderer(klass):
        """Register a renderer class with the datatree rendering system.
        
        :keyword klass: Either a string with the fully qualified name of the 
          renderer class to register, or the actual class itself.  The name
          will be read from the class. 
        """
        if isinstance(klass, str):
            klass = get_class(klass)
        global _plugins
        _plugins.append([tuple(klass.friendly_names), klass])

    def __get_methods__(self):
        return set(['to_string', 'render', 'register_renderer'])

    def __str__(self):
        return '{0}/{1}'.format(self.__node_name__, self.__value__)

    def to_string(self, level=0):
        """Create an ugly representation of the datatree from this node
        down.

        .. Warning::
            This is included as a debug aid and is not good for much else. The
            output is messy and inconsistent.
        """
        result = StringIO()
        prefix = ' ' * level
        new_level = level + 2
        result.write(prefix)
        result.write(str(self))
        result.write('\n')
        for child in self.__children__:
            result.write(child.to_string(new_level))

        return result.getvalue()

    def render(self, renderer='xml', as_root=False, **options):
        """Render the datatree using the provided renderer.
        
        :keyword renderer: The name of the renderer to use.  You may add more
            renderers by using the register_renderer method.
            
        :keyword as_root: If True, the tree will be rendered from this node down,
            otherwise rendering will happen from the tree root.
        
        :keyword options: Key value pairs of options that will be passed to
            the renderer.         
        """
        if not as_root and self.__parent__:
            return self.__parent__.render(renderer, **options)

        global _plugins
        render_kls = None
        for plugin in _plugins:
            names, kls = plugin
            if renderer in names:
                if not isinstance(kls, str):
                    render_kls = kls
                else:
                    # Fetch the class and cache it for later.
                    render_kls = get_class(kls)
                    plugin[1] = render_kls
                break
                # TODO: Should the renderers be instantiated?
        return render_kls().render(self, options=options)

    def __call__(self, renderer='xml', as_root=False, **options):
        """Same as calling :function:`render <NodeBase.render>`.

        :keyword renderer: The name of the renderer to use.  You may add more
            renderers by using the register_renderer method.

        :keyword as_root: If True, the tree will be rendered from this node down,
            otherwise rendering will happen from the tree root.

        :keyword options: Key value pairs of options that will be passed to
            the renderer.
        """
        return self.render(renderer, as_root=as_root, **options)


class Vertex(BaseNode):
    """Node that can have children.
    """

    def __init__(self, *args, **kwargs):
        super(Vertex, self).__init__(*args, **kwargs)
        self.__methods__ = self.__get_methods__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def comment(self, text):
        """Adds a comment to the node.
        
        .. note::
            Comments are ignored by some of the renderers such as json and
            dict. Consult the documentation to find out the behaviour.
        
        :keyword text: Text content of the comment.
        """
        return self.add_node(
            CommentNode(
                node_name="!COMMENT!",
                node_value=text,
                node_parent=self
            )
        )

    def cdata(self, text, **attributes):
        """Add a :class:`CDataNode <datatree.tree.CDataNode>` to the current
        tree.

        .. note::
            CData tags are ignored by some of the renderers such as json and
            dict. Consult the documentation to find out the behaviour.

        :param text: Text value of the CDATA tag.
        :param attributes: Additional attributes to be added to the tag.
        :return: The created :class:`CDataNode <datatree.tree.CDataNode>`.
        """
        return self.add_node(
            CDataNode(
                node_name='!CDATA!',
                node_value=text,
                **attributes
            )
        )

    def ns(self, name=None, url=None):
        ns = NameSpace(name_space=url)
        setattr(self, name, ns)
        return ns


    ### Child Manipulation Methods ###

    def node(self, name, value=None, **attributes):
        """Creates and adds :class:`Node <datatree.tree.Node>` object to the
        current tree.

        :param name: The name identifier for the node..
        :param value: The value of this node.  Note that this will be
            converted to a string usually during rendering.  Default is ``None``
            which generally means it is ignored during rendering.
        :param attributes: The key value pairs that will be used as the
            attributes for the node.
        :return: The created :class:`Node <datatree.tree.Node>`.
        """
        new_node = Node(
            node_name=name,
            node_parent=self,
            node_value=value,
            **attributes
        )
        self.add_node(new_node)
        return new_node

    def add_node(self, node):
        self.__children__.append(node)
        return node


class Leaf(BaseNode):
    """Node that can have no children.
    """
    pass


class Tree(Vertex):
    """Very top node in a datatree.
    
    The Tree is the top node used to build a datatree.
    """

    def __init__(self, *args, **kwargs):
        kwargs['node_name'] = None
        super(Tree, self).__init__(*args, **kwargs)

    def instruct(self, name='xml', **attributes):
        """Add an xml processing instruction.
        
        .. note::
            Instructions are ignored by some of the renderers such as json and
            dict. Consult the documentation to find out the behaviour.

        :keyword name: Name of the instruction node. A value of xml will create
            the instruction ``<?xml ?>``.
        
        :keyword attributes: Any extra attributes for the instruction.
        """
        return self.add_node(InstructionNode(node_name=name, **attributes))

    def declare(self, name, *attributes):
        """Add an xml declaration to the datatree.  
        
        .. note::
            Declarations are ignored by some of the renderers such as json and
            dict. Consult the documentation to find out the behaviour.

        .. Warning::
            This functionality is pretty limited for the time being,
            hopefully the API for this will become more clear with time.
        
        :keyword name: Name of the declaration node.
        
        :keyword attributes: Extra attributes to be added. Strings will be
            added as quoted strings.  Symbols will be added as unquoted
            strings. Import the ``__`` object and use it like this:
            ``__.SomeValue`` to add a symbol.
        """
        child = self.add_node(DeclarationNode(node_name=name))
        child.__declaration_params__ = attributes
        return child


class Node(Vertex):
    """A node is able to be instantiated directly and added to any Vertex.
    """

    def __init__(self, node_name='root', node_value=None, **attributes):
        super(Node, self).__init__(node_name=node_name, node_value=node_value,
                                   **attributes)


class InstructionNode(Leaf):
    pass


class DeclarationNode(Leaf):
    pass


class CommentNode(Leaf):
    def __str__(self):
        """Return a string representation.

        :return: A generic comment string.

        >>> cmt = CommentNode(node_value='A comment of some type.')
        >>> str(cmt)
        '# A comment of some type.'
        """
        return "# {0}".format(self.__value__)


class CDataNode(Leaf):
    pass


class NameSpace(Vertex):
    """A namespace is declared on the tree and accepts child nodes.  It is
    mostly ignored by the renderers with the exception of the XMLRenderer.
    """

    def __init__(self, *args, **kwargs):
        super(NameSpace, self).__init__(*args, **kwargs)
########NEW FILE########
__FILENAME__ = utils

try:
    from importlib import import_module

    def get_class(kls):
        """Return a class by its full name."""
        parts = kls.split('.')
        module = '.'.join(parts[:-1])
        m = import_module(module)
        return getattr(m, parts[-1])

except ImportError:
    def get_class(kls):
        """Return a class by its full name."""
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__(module)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# datatree documentation build configuration file, created by
# sphinx-quickstart on Tue May 24 11:30:19 2011.
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
sys.path.insert(0, os.path.abspath('../'))
import datatree

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'datatree'
copyright = u'2011, Jason Webb'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(map(str, datatree.VERSION[:2]))
# The full version, including alpha/beta/rc tags.
release = '.'.join(map(str, datatree.VERSION))

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
exclude_patterns = ['.build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

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
html_static_path = ['.static']

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
htmlhelp_basename = 'datatreedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'datatree.tex', u'datatree Documentation',
   u'Jason Webb', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'datatree', u'datatree Documentation',
     [u'Jason Webb'], 1)
]

########NEW FILE########
__FILENAME__ = example
from datatree import Tree

if __name__ == '__main__':
    tree = Tree()
    #tree.instruct('xml', version='1.0')
    with tree.node("author") as author:
        author.node('name', 'Terry Pratchett')
        author.node('genre', 'Fantasy/Comedy')
        author.comment("Only 2 books listed")
        with author.node('novels', count=2) as novels:
            novels.node('novel', 'Small Gods', year=1992)
            novels.node('novel', 'The Fifth Elephant', year=1999)
            novels.node("novel", "Guards! Guards!", year=1989)

    print 'XML:'
    print author(pretty=True)
    print
    print
    print 'JSON:'
    print author('json', pretty=True)
    print
    print
    print 'YAML:'
    print author('yaml')
    print
    print
    print 'Dict:'
    print author('dict', pretty_string=True)

########NEW FILE########
__FILENAME__ = runtests
#! /usr/bin/env python

import sys
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from os import path
from random import Random, randint

import coverage

class RandomOrderTestSuite(unittest.TestSuite):
    """
    Test Suite that will randomize the order of tests.  This avoids the tests
    becoming dependent on some overlooked state.  USE WITH CAUTION.
    """

    def __init__(self, seed, *args, **kwargs):
        if seed:
            self.__seed = seed
        else:
            self.__seed = randint(0, 9999)
        super(RandomOrderTestSuite, self).__init__(*args, **kwargs)

    def __get_all_tests(self, test_case):
        result = []
        for item in test_case:
            if hasattr(item, "_tests") and len(item._tests) > 0:
                result += self.__get_all_tests(item)
            else:
                result.append(item)
        return result

    def run(self, result):
        cases = self.__get_all_tests(self)
        r = Random(self.__seed)
        r.shuffle(cases)
        for test in cases:
            if result.shouldStop:
                break
            test(result)
        print
        print
        print '>>> python runtests.py --seed={0}'.format(self.__seed)
        return result

if __name__ == "__main__":
    cov = coverage.coverage(source=[path.join(path.dirname(__file__), 'datatree')])
    cov.start()

    seed = None
    for arg in sys.argv:
        if arg.startswith('--seed='):
            seed = int(arg.split('=')[1])

    current_folder = path.dirname(__file__)
    base_folder = path.join(current_folder, "datatree")

    sys.path.insert(0, current_folder)

    suite = RandomOrderTestSuite(seed)
    loader = unittest.loader.defaultTestLoader
    suite.addTest(loader.discover(base_folder, pattern="test*.py"))
    runner = unittest.TextTestRunner()
    runner.verbosity = 2

    runner.run(suite.run)
    cov.stop()
    # Output the coverage
    cov.html_report(directory='htmlcov')
    print 'Coverage report written to: {0}'.format(path.join(path.dirname(__file__), 'htmlcov', 'index.html'))

########NEW FILE########
