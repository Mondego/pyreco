__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.abspath('../..'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']  # 'sphinx.ext.intersphinx']

templates_path = ['_templates']

source_suffix = '.rst'

#source_encoding = 'utf-8-sig'

master_doc = 'index'

project = u'Reconfigure'
copyright = u'2013, Eugeny Pankov'

version = '1.0'
release = '1.0a1'

exclude_patterns = []
add_function_parentheses = True

#pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------
#html_theme = 'air'
#html_theme_options = {}
#html_theme_path = ['../../../sphinx-themes']

html_title = 'Reconfigure documentation'
html_short_title = 'Reconfigure docs'

#html_logo = None

#html_favicon = None

html_static_path = ['_static']

htmlhelp_basename = 'Reconfiguredoc'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}


########NEW FILE########
__FILENAME__ = base
class BaseBuilder (object):
    """
    A base class for builders
    """

    def build(self, tree):
        """
        :param tree: :class:`reconfigure.nodes.Node` tree
        :returns: Data tree
        """

    def unbuild(self, tree):
        """
        :param tree: Data tree
        :returns: :class:`reconfigure.nodes.Node` tree
        """

########NEW FILE########
__FILENAME__ = bound
from reconfigure.builders.base import BaseBuilder


class BoundBuilder (BaseBuilder):
    """
    A builder that uses :class:`reconfigure.items.bound.BoundData` to build stuff

    :param root_class: a ``BoundData`` class that used as processing root
    """

    def __init__(self, root_class):
        self.root_class = root_class

    def build(self, nodetree):
        return self.root_class(nodetree)

    def unbuild(self, tree):
        pass

########NEW FILE########
__FILENAME__ = bound_tests
from reconfigure.items.bound import BoundData
from reconfigure.nodes import Node, PropertyNode
import unittest


class BoundDataTest (unittest.TestCase):

    def test_bind_property(self):
        class TestBoundData (BoundData):
            pass
        TestBoundData.bind_property('prop', 'dataprop', getter=lambda x: 'd' + x, setter=lambda x: x[1:])

        n = Node('name', children=[
                PropertyNode('prop', 'value')
            ])

        d = TestBoundData(n)

        self.assertEqual(d.dataprop, 'dvalue')
        d.dataprop = 'dnew'
        self.assertEqual(d.dataprop, 'dnew')
        self.assertEqual(n.get('prop').value, 'new')

    def test_bind_collection(self):
        class TestBoundData (BoundData):
            pass

        class TestChildData (BoundData):
            def template(self):
                return Node('', children=[PropertyNode('value', None)])

        TestBoundData.bind_collection('items', item_class=TestChildData, selector=lambda x: x.name != 'test')
        TestChildData.bind_property('value', 'value')
        n = Node('name', children=[
                Node('1', children=[PropertyNode('value', 1)]),
                Node('2', children=[PropertyNode('value', 2)]),
                Node('test', children=[PropertyNode('value', 3)]),
                Node('3', children=[PropertyNode('value', 3)]),
            ])

        d = TestBoundData(n)
        self.assertEqual(d.items[0].value, 1)
        self.assertEqual(len(d.items), 3)
        c = TestChildData()
        c.value = 4
        d.items.append(c)
        self.assertEqual(len(d.items), 4)
        self.assertEqual(d.items[-1].value, 4)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ajenti
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import JsonParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.ajenti import AjentiData


class AjentiConfig (Reconfig):
    def __init__(self, **kwargs):
        k = {
            'parser': JsonParser(),
            'builder': BoundBuilder(AjentiData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = base
import chardet


class Reconfig (object):
    """
    Basic config class. Derivatives normally only need to override the constructor.

    Config data is loaded either from ``path`` or from ``content``

    :param parser: overrides the Parser instance
    :param includer: overrides the Includer instance
    :param builder: overrides the Builder instance
    :param path: config file path. Not compatible with ``content``
    :param content: config file content. Not compatible with ``path``
    """

    def __init__(self, parser=None, includer=None, builder=None, path=None, content=None):
        self.parser = parser
        self.builder = builder
        self.includer = includer
        if self.includer is not None:
            if not self.includer.parser:
                self.includer.parser = self.parser
        if path:
            self.origin = path
            self.content = None
        else:
            self.origin = None
            self.content = content

    def load(self):
        """
        Loads the config data, parses and builds it. Sets ``tree`` attribute to point to Data tree.
        """
        if self.origin:
            self.content = open(self.origin, 'r').read()

        self.encoding = 'utf8'
        if hasattr(self.content, 'decode'):  # str (2) or bytes (3)
            try:
                self.content = self.content.decode('utf8')
            except (UnicodeDecodeError, AttributeError):
                self.encoding = chardet.detect(self.content)['encoding']
                self.content = self.content.decode(self.encoding)

        self.nodetree = self.parser.parse(self.content)
        if self.includer is not None:
            self.nodetree = self.includer.compose(self.origin, self.nodetree)
        if self.builder is not None:
            self.tree = self.builder.build(self.nodetree)
        return self

    def save(self):
        """
        Unbuilds, stringifies and saves the config. If the config was loaded from string, returns ``{ origin: data }`` dict
        """
        tree = self.tree
        if self.builder is not None:
            nodetree = self.builder.unbuild(tree) or self.nodetree
        if self.includer is not None:
            nodetree = self.includer.decompose(nodetree)
        else:
            nodetree = {self.origin: nodetree}

        result = {}
        for k in nodetree:
            v = self.parser.stringify(nodetree[k])
            if self.encoding != 'utf8':
                v = v.encode(self.encoding)
            result[k or self.origin] = v

        if self.origin is not None:
            for k in result:
                open(k, 'w').write(result[k])
        return result

########NEW FILE########
__FILENAME__ = bind9
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import BIND9Parser
from reconfigure.includers import BIND9Includer
from reconfigure.builders import BoundBuilder
from reconfigure.items.bind9 import BIND9Data


class BIND9Config (Reconfig):
    """
    ``named.conf``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': BIND9Parser(),
            'includer': BIND9Includer(),
            'builder': BoundBuilder(BIND9Data),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = crontab
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import CrontabParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.crontab import CrontabData


class CrontabConfig (Reconfig):
    def __init__(self, **kwargs):
        k = {
            'parser': CrontabParser(),
            'builder': BoundBuilder(CrontabData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = csf
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import ShellParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.csf import CSFData


class CSFConfig (Reconfig):
    """
    ``CSF main config``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': ShellParser(),
            'builder': BoundBuilder(CSFData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = ctdb
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import IniFileParser
from reconfigure.parsers import SSVParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.ctdb import CTDBData, NodesData, PublicAddressesData


class CTDBConfig (Reconfig):
    """
    ``CTDB main config``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': IniFileParser(sectionless=True),
            'builder': BoundBuilder(CTDBData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)


class CTDBNodesConfig (Reconfig):
    """
    ``CTDB node list file``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(),
            'builder': BoundBuilder(NodesData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)


class CTDBPublicAddressesConfig (Reconfig):
    """
    ``CTDB public address list file``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(separator=' '),
            'builder': BoundBuilder(PublicAddressesData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = dhcpd
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import NginxParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.dhcpd import DHCPDData


class DHCPDConfig (Reconfig):
    """
    ``DHCPD``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': NginxParser(),
            'builder': BoundBuilder(DHCPDData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = exports
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import ExportsParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.exports import ExportsData


class ExportsConfig (Reconfig):
    """
    ``/etc/fstab``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': ExportsParser(),
            'builder': BoundBuilder(ExportsData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = fstab
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import SSVParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.fstab import FSTabData


class FSTabConfig (Reconfig):
    """
    ``/etc/fstab``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(),
            'builder': BoundBuilder(FSTabData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = group
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import SSVParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.group import GroupsData


class GroupConfig (Reconfig):
    """
    ``/etc/group``
    """

    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(separator=':'),
            'builder': BoundBuilder(GroupsData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = hosts
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import SSVParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.hosts import HostsData


class HostsConfig (Reconfig):
    """
    ``/etc/hosts``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(),
            'builder': BoundBuilder(HostsData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = iptables
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import IPTablesParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.iptables import IPTablesData


class IPTablesConfig (Reconfig):
    """
    ``iptables-save`` and ``iptables-restore``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': IPTablesParser(),
            'builder': BoundBuilder(IPTablesData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = netatalk
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import IniFileParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.netatalk import NetatalkData


class NetatalkConfig (Reconfig):
    """
    Netatalk afp.conf
    """

    def __init__(self, **kwargs):
        k = {
            'parser': IniFileParser(),
            'builder': BoundBuilder(NetatalkData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = nsd
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import NSDParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.nsd import NSDData


class NSDConfig (Reconfig):
    """
    ``NSD DNS server nsd.conf``
    """
    def __init__(self, **kwargs):
        k = {
            'parser': NSDParser(),
            'builder': BoundBuilder(NSDData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = passwd
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import SSVParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.passwd import PasswdData


class PasswdConfig (Reconfig):
    """
    ``/etc/passwd``
    """

    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(separator=':'),
            'builder': BoundBuilder(PasswdData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = resolv
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import SSVParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.resolv import ResolvData


class ResolvConfig (Reconfig):
    """
    ``/etc/resolv.conf``
    """

    def __init__(self, **kwargs):
        k = {
            'parser': SSVParser(maxsplit=1),
            'builder': BoundBuilder(ResolvData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = samba
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import IniFileParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.samba import SambaData


class SambaConfig (Reconfig):
    def __init__(self, **kwargs):
        k = {
            'parser': IniFileParser(),
            'builder': BoundBuilder(SambaData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = squid
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import SquidParser
from reconfigure.builders import BoundBuilder
from reconfigure.items.squid import SquidData


class SquidConfig (Reconfig):
    def __init__(self, **kwargs):
        k = {
            'parser': SquidParser(),
            'builder': BoundBuilder(SquidData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = supervisor
from reconfigure.configs.base import Reconfig
from reconfigure.parsers import IniFileParser
from reconfigure.includers import SupervisorIncluder
from reconfigure.builders import BoundBuilder
from reconfigure.items.supervisor import SupervisorData


class SupervisorConfig (Reconfig):
    """
    ``/etc/supervisor/supervisord.conf``
    """

    def __init__(self, **kwargs):
        k = {
            'parser': IniFileParser(),
            'includer': SupervisorIncluder(),
            'builder': BoundBuilder(SupervisorData),
        }
        k.update(kwargs)
        Reconfig.__init__(self, **k)

########NEW FILE########
__FILENAME__ = auto
from reconfigure.includers.base import BaseIncluder
from reconfigure.nodes import *
import glob
import os


class AutoIncluder (BaseIncluder):
    """
    This base includer automatically walks the node tree and loads the include files from ``IncludeNode.files`` properties. ``files`` is supposed to contain absolute path, relative path or a shell wildcard.
    """

    def compose(self, origin, tree):
        self.compose_rec(origin, origin, tree)
        return tree

    def compose_rec(self, root, origin, node):
        if not node.origin:
            node.origin = origin
        for child in node.children:
            self.compose_rec(root, origin, child)
        for child in node.children:
            spec = self.is_include(child)
            if spec:
                files = spec
                if node.origin and not files.startswith('/'):
                    files = os.path.join(os.path.split(root)[0], files)
                if '*' in files or '.' in files:
                    files = glob.glob(files)
                else:
                    files = [files]
                for file in files:
                    if file in self.content_map:
                        content = self.content_map[file]
                    else:
                        content = open(file, 'r').read()
                    subtree = self.parser.parse(content)
                    node.children.extend(subtree.children)
                    self.compose_rec(root, file, subtree)
                node.children[node.children.index(child)] = IncludeNode(spec)

    def decompose(self, tree):
        result = {}
        result[tree.origin] = self.decompose_rec(tree, result)
        return result

    def decompose_rec(self, node, result):
        for child in node.children:
            if child.__class__ == IncludeNode:
                replacement = self.remove_include(child)
                if replacement:
                    node.children[node.children.index(child)] = replacement
            else:
                if child.origin is None:
                    child.origin = node.origin
                if child.origin != node.origin:
                    node.children.remove(child)
                    result.setdefault(child.origin, RootNode()).children.append(self.decompose_rec(child, result))
                else:
                    self.decompose_rec(child, result)
        return node

    def is_include(self, node):
        """
        Should return whether the node is an include node and return file pattern glob if it is
        """

    def remove_include(self, node):
        """
        Shoud transform :class:`reconfigure.nodes.IncludeNode` into a normal Node to be stringified into the file
        """

########NEW FILE########
__FILENAME__ = base
class BaseIncluder (object):  # pragma: no cover
    """
    A base includer class

    :param parser: Parser instance that was used to parse the root config file
    :param content_map: a dict that overrides config content for specific paths
    """

    def __init__(self, parser=None, content_map={}):
        self.parser = parser
        self.content_map = content_map

    def compose(self, origin, tree):
        """
        Should locate the include nodes in the Node tree, replace them with :class:`reconfigure.nodes.IncludeNode`, parse the specified include files and append them to tree, with correct node ``origin`` attributes
        """

    def decompose(self, origin, tree):
        """
        Should detach the included subtrees from the Node tree and return a ``{ origin: content-node-tree }`` dict.
        """

########NEW FILE########
__FILENAME__ = bind9
from reconfigure.includers.auto import AutoIncluder
from reconfigure.nodes import PropertyNode


class BIND9Includer (AutoIncluder):
    def is_include(self, node):
        if isinstance(node, PropertyNode) and node.name == 'include':
            return node.value.strip('"')

    def remove_include(self, node):
        return PropertyNode('include', '"%s"' % node.files)

########NEW FILE########
__FILENAME__ = nginx
from reconfigure.includers.auto import AutoIncluder
from reconfigure.nodes import PropertyNode


class NginxIncluder (AutoIncluder):
    def is_include(self, node):
        if isinstance(node, PropertyNode) and node.name == 'include':
            return node.value

    def remove_include(self, node):
        return PropertyNode('include', node.files)

########NEW FILE########
__FILENAME__ = supervisor
from reconfigure.includers.auto import AutoIncluder
from reconfigure.nodes import Node, PropertyNode


class SupervisorIncluder (AutoIncluder):
    def is_include(self, node):
        if node.name == 'include':
            return node.get('files').value

    def remove_include(self, node):
        return Node('include', children=[PropertyNode('files', node.files)])

########NEW FILE########
__FILENAME__ = ajenti
import json

from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData, BoundDictionary


class AjentiData (BoundData):
    pass


class HttpData (BoundData):
    pass


class SSLData (BoundData):
    pass


class UserData (BoundData):
    def template(self):
        return Node(
            'unnamed',
            PropertyNode('configs', {}),
            PropertyNode('password', ''),
            PropertyNode('permissions', []),
        )


class ConfigData (BoundData):
    def template(self):
        return PropertyNode('', '{}')


AjentiData.bind_property('authentication', 'authentication')
AjentiData.bind_property('language', 'language')
AjentiData.bind_property('installation_id', 'installation_id')
AjentiData.bind_property('enable_feedback', 'enable_feedback')
AjentiData.bind_child('http_binding', lambda x: x.get('bind'), item_class=HttpData)
AjentiData.bind_child('ssl', lambda x: x.get('ssl'), item_class=SSLData)
AjentiData.bind_collection('users', path=lambda x: x.get('users'), item_class=UserData, collection_class=BoundDictionary, key=lambda x: x.name)


HttpData.bind_property('host', 'host')
HttpData.bind_property('port', 'port')

SSLData.bind_property('certificate_path', 'certificate_path')
SSLData.bind_property('enable', 'enable')

ConfigData.bind_name('name')

UserData.bind_name('name')
UserData.bind_property('email', 'email')
UserData.bind_property('password', 'password')
UserData.bind_property('permissions', 'permissions')
UserData.bind_collection('configs', lambda x: x.get('configs'), item_class=ConfigData, collection_class=BoundDictionary, key=lambda x: x.name)

ConfigData.bind_attribute('value', 'data', getter=json.loads, setter=json.dumps)

########NEW FILE########
__FILENAME__ = bind9
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class BIND9Data (BoundData):
    pass


class ZoneData (BoundData):
    def template(self):
        return Node(
            'zone',
            PropertyNode('type', 'master'),
            PropertyNode('file', 'db.example.com'),
            parameter='"example.com"',
        )


quote = lambda x: '"%s"' % x
unquote = lambda x: x.strip('"')

BIND9Data.bind_collection('zones', selector=lambda x: x.name == 'zone', item_class=ZoneData)
ZoneData.bind_attribute('parameter', 'name', getter=unquote, setter=quote)
ZoneData.bind_property('type', 'type')
ZoneData.bind_property('file', 'file', getter=unquote, setter=quote)

########NEW FILE########
__FILENAME__ = bound
import json


class BoundCollection (object):
    """
    Binds a list-like object to a set of nodes

    :param node: target node (its children will be bound)
    :param item_class: :class:`BoundData` class for items
    :param selector: ``lambda x: bool``, used to filter out a subset of nodes
    """

    def __init__(self, node, item_class, selector=lambda x: True):
        self.node = node
        self.selector = selector
        self.item_class = item_class
        self.data = []
        self.rebuild()

    def rebuild(self):
        """
        Discards cached collection and rebuilds it from the nodes
        """
        del self.data[:]
        for node in self.node.children:
            if self.selector(node):
                self.data.append(self.item_class(node))

    def to_dict(self):
        return [x.to_dict() if hasattr(x, 'to_dict') else x for x in self]

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

    def __str__(self):
        return self.to_json()

    def __iter__(self):
        return self.data.__iter__()

    def __getitem__(self, index):
        return self.data.__getitem__(index)

    def __len__(self):
        return len(self.data)

    def __contains__(self, item):
        return item in self.data

    def append(self, item):
        self.node.append(item._node)
        self.data.append(item)

    def remove(self, item):
        self.node.remove(item._node)
        self.data.remove(item)

    def insert(self, index, item):
        self.node.children.insert(index, item._node)
        self.data.insert(index, item)

    def pop(self, index):
        d = self[index]
        self.remove(d)
        return d


class BoundDictionary (BoundCollection):
    """
    Binds a dict-like object to a set of nodes. Accepts same params as :class:`BoundCollection` plus ``key``

    :param key: ``lambda value: object``, is used to get key for value in the collection
    """

    def __init__(self, key=None, **kwargs):
        self.key = key
        BoundCollection.__init__(self, **kwargs)

    def rebuild(self):
        BoundCollection.rebuild(self)
        self.rebuild_dict()

    def rebuild_dict(self):
        self.datadict = dict((self.key(x), x) for x in self.data)

    def to_dict(self):
        return dict((k, x.to_dict() if hasattr(x, 'to_dict') else x) for k, x in self.items())

    def __getitem__(self, key):
        self.rebuild_dict()
        return self.datadict[key]

    def __setitem__(self, key, value):
        self.rebuild_dict()
        if not key in self:
            self.append(value)
        self.datadict[key] = value
        self.rebuild_dict()

    def __contains__(self, key):
        self.rebuild_dict()
        return key in self.datadict

    def __iter__(self):
        self.rebuild_dict()
        return self.datadict.__iter__()

    def iteritems(self):
        self.rebuild_dict()
        return self.datadict.items()

    items = iteritems

    def setdefault(self, k, v):
        if not k in self:
            self[k] = v
            self.append(v)
        return self[k]

    def values(self):
        self.rebuild_dict()
        return self.data

    def update(self, other):
        for k, v in other.items():
            self[k] = v

    def pop(self, key):
        if key in self:
            self.remove(self[key])


class BoundData (object):
    """
    Binds itself to a node.

    ``bind_*`` classmethods should be called on module-level, after subclass declaration.

    :param node: all bindings will be relative to this node
    :param kwargs: if ``node`` is ``None``, ``template(**kwargs)`` will be used to create node tree fragment
    """

    def __init__(self, node=None, **kwargs):
        if node is None:
            node = self.template(**kwargs)
        self._node = node

    def template(self, **kwargs):
        """
        Override to create empty objects.

        :returns: a :class:`reconfigure.nodes.Node` tree that will be used as a template for new BoundData instance
        """
        return None

    def to_dict(self):
        res_dict = {}
        for attr_key in self.__class__.__dict__:
            if attr_key in self.__class__._bound:
                attr_value = getattr(self, attr_key)
                if isinstance(attr_value, BoundData):
                    res_dict[attr_key] = attr_value.to_dict()
                elif isinstance(attr_value, BoundCollection):
                    res_dict[attr_key] = attr_value.to_dict()
                else:
                    res_dict[attr_key] = attr_value
        return res_dict

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

    def __str__(self):
        return self.to_json()

    @classmethod
    def bind(cls, data_property, getter, setter):
        """
        Creates an arbitrary named property in the class with given getter and setter. Not usually used directly.

        :param data_property: property name
        :param getter: ``lambda: object``, property getter
        :param setter: ``lambda value: None``, property setter
        """
        if not hasattr(cls, '_bound'):
            cls._bound = []
        cls._bound.append(data_property)
        setattr(cls, data_property, property(getter, setter))

    @classmethod
    def bind_property(cls, node_property, data_property, default=None, \
            default_remove=[], \
            path=lambda x: x, getter=lambda x: x, setter=lambda x: x):
        """
        Binds the value of a child :class:`reconfigure.node.PropertyNode` to a property

        :param node_property: ``PropertyNode``'s ``name``
        :param data_property: property name to be created
        :param default: default value of the property (is ``PropertyNode`` doesn't exist)
        :param default_remove: if setting a value contained in default_remove, the target property is removed
        :param path: ``lambda self.node: PropertyNode``, can be used to point binding to another Node instead of ``self.node``.
        :param getter: ``lambda object: object``, used to transform value when getting
        :param setter: ``lambda object: object``, used to transform value when setting
        """
        def pget(self):
            prop = path(self._node).get(node_property)
            if prop is not None:
                return getter(prop.value)
            else:
                return default

        def pset(self, value):
            if setter(value) in default_remove:
                node = path(self._node).get(node_property)
                if node is not None:
                    path(self._node).remove(node)
            else:
                path(self._node).set_property(node_property, setter(value))

        cls.bind(data_property, pget, pset)

    @classmethod
    def bind_attribute(cls, node_attribute, data_property, default=None, \
            path=lambda x: x, getter=lambda x: x, setter=lambda x: x):
        """
        Binds the value of node object's attribute to a property

        :param node_attribute: ``Node``'s attribute name
        :param data_property: property name to be created
        :param default: default value of the property (is ``PropertyNode`` doesn't exist)
        :param path: ``lambda self.node: PropertyNode``, can be used to point binding to another Node instead of ``self.node``.
        :param getter: ``lambda object: object``, used to transform value when getting
        :param setter: ``lambda object: object``, used to transform value when setting
        """
        def pget(self):
            prop = getattr(path(self._node), node_attribute)
            if prop is not None:
                return getter(prop)
            else:
                return getter(default)

        def pset(self, value):
            setattr(path(self._node), node_attribute, setter(value))

        cls.bind(data_property, pget, pset)

    @classmethod
    def bind_collection(cls, data_property, path=lambda x: x, selector=lambda x: True, item_class=None, \
        collection_class=BoundCollection, **kwargs):
        """
        Binds the subset of node's children to a collection property

        :param data_property: property name to be created
        :param path: ``lambda self.node: PropertyNode``, can be used to point binding to another Node instead of ``self.node``.
        :param selector: ``lambda Node: bool``, can be used to filter out a subset of child nodes
        :param item_class: a :class:`BoundData` subclass to be used for collection items
        :param collection_class: a :class:`BoundCollection` subclass to be used for collection property itself
        """
        def pget(self):
            if not hasattr(self, '__' + data_property):
                setattr(self, '__' + data_property,
                    collection_class(
                        node=path(self._node),
                        item_class=item_class,
                        selector=selector,
                        **kwargs
                    )
                )
            return getattr(self, '__' + data_property)

        cls.bind(data_property, pget, None)

    @classmethod
    def bind_name(cls, data_property, getter=lambda x: x, setter=lambda x: x):
        """
        Binds the value of node's ``name`` attribute to a property

        :param data_property: property name to be created
        :param getter: ``lambda object: object``, used to transform value when getting
        :param setter: ``lambda object: object``, used to transform value when setting
        """
        def pget(self):
            return getter(self._node.name)

        def pset(self, value):
            self._node.name = setter(value)

        cls.bind(data_property, pget, pset)

    @classmethod
    def bind_child(cls, data_property, path=lambda x: x, item_class=None):
        """
        Directly binds a child Node to a BoundData property

        :param data_property: property name to be created
        :param path: ``lambda self.node: PropertyNode``, can be used to point binding to another Node instead of ``self.node``.
        :param item_class: a :class:`BoundData` subclass to be used for the property value
        """
        def pget(self):
            if not hasattr(self, '__' + data_property):
                setattr(self, '__' + data_property,
                    item_class(
                        path(self._node),
                    )
                )
            return getattr(self, '__' + data_property)

        cls.bind(data_property, pget, None)

########NEW FILE########
__FILENAME__ = crontab
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class CrontabData(BoundData):
    """Data class for crontab configs"""
    pass


class CrontabNormalTaskData(BoundData):
    fields = ['minute', 'hour', 'day_of_month', 'month', 'day_of_week', 'command']

    def describe(self):
        return ' '.join(getattr(self, x) for x in self.fields)

    def template(self, **kwargs):
        return Node('normal_task', children=[
            PropertyNode('minute', '0'),
            PropertyNode('hour', '0'),
            PropertyNode('day_of_month', '1'),
            PropertyNode('month', '1'),
            PropertyNode('day_of_week', '1'),
            PropertyNode('command', 'false')
        ])


class CrontabSpecialTaskData(BoundData):
    fields = ['special', 'command']

    def template(self, **kwargs):
        return Node('special_task', children=[
            PropertyNode('special', '@reboot'),
            PropertyNode('command', 'false')
        ])


class CrontabEnvSettingData(BoundData):
    fields = ['name', 'value']

    def template(self, **kwargs):
        return Node('env_setting', children=[
            PropertyNode('name', 'ENV_NAME'),
            PropertyNode('value', 'ENV_VALUE')
        ])


def bind_for_fields(bound_data_class):
    for field in bound_data_class.fields:
        bound_data_class.bind_property(field, field)

CrontabData.bind_collection('normal_tasks', selector=lambda x: x.name == 'normal_task', item_class=CrontabNormalTaskData)
bind_for_fields(CrontabNormalTaskData)

CrontabNormalTaskData.bind_attribute('comment', 'comment')

CrontabData.bind_collection('env_settings', selector=lambda x: x.name == 'env_setting', item_class=CrontabEnvSettingData)
bind_for_fields(CrontabEnvSettingData)

CrontabEnvSettingData.bind_attribute('comment', 'comment')

CrontabData.bind_collection('special_tasks', selector=lambda x: x.name == 'special_task', item_class=CrontabSpecialTaskData)
bind_for_fields(CrontabSpecialTaskData)

CrontabSpecialTaskData.bind_attribute('comment', 'comment')

########NEW FILE########
__FILENAME__ = csf
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData
from reconfigure.items.util import onezero_getter, onezero_setter


class CSFData (BoundData):
    pass


CSFData.bind_property('TESTING', 'testing', getter=onezero_getter, setter=onezero_setter)
CSFData.bind_property('IPV6', 'ipv6', getter=onezero_getter, setter=onezero_setter)

CSFData.bind_property('TCP_IN', 'tcp_in')
CSFData.bind_property('TCP_OUT', 'tcp_out')
CSFData.bind_property('UDP_IN', 'udp_in')
CSFData.bind_property('UDP_OUT', 'udp_out')
CSFData.bind_property('TCP6_IN', 'tcp6_in')
CSFData.bind_property('TCP6_OUT', 'tcp6_out')
CSFData.bind_property('UDP6_IN', 'udp6_in')
CSFData.bind_property('UDP6_OUT', 'udp6_out')
CSFData.bind_property('ETH_DEVICE', 'eth_device')
CSFData.bind_property('ETH6_DEVICE', 'eth6_device')

########NEW FILE########
__FILENAME__ = ctdb
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData
from reconfigure.items.util import yn_getter, yn_setter


class CTDBData (BoundData):
    pass

CTDBData.bind_property('CTDB_RECOVERY_LOCK', 'recovery_lock_file', path=lambda x: x.get(None))
CTDBData.bind_property('CTDB_PUBLIC_INTERFACE', 'public_interface', path=lambda x: x.get(None))
CTDBData.bind_property('CTDB_PUBLIC_ADDRESSES', 'public_addresses_file', default='/etc/ctdb/public_addresses', path=lambda x: x.get(None))
CTDBData.bind_property(
    'CTDB_MANAGES_SAMBA', 'manages_samba', path=lambda x: x.get(None),
    getter=yn_getter, setter=yn_setter)
CTDBData.bind_property('CTDB_NODES', 'nodes_file', default='/etc/ctdb/nodes', path=lambda x: x.get(None))
CTDBData.bind_property('CTDB_LOGFILE', 'log_file', path=lambda x: x.get(None))
CTDBData.bind_property('CTDB_DEBUGLEVEL', 'debug_level', default='2', path=lambda x: x.get(None))
CTDBData.bind_property('CTDB_PUBLIC_NETWORK', 'public_network', default='', path=lambda x: x.get(None))
CTDBData.bind_property('CTDB_PUBLIC_GATEWAY', 'public_gateway', default='', path=lambda x: x.get(None))


class NodesData (BoundData):
    pass


class NodeData (BoundData):
    def template(self):
        return Node('line', children=[
            Node('token', children=[PropertyNode('value', '127.0.0.1')]),
        ])


NodesData.bind_collection('nodes', item_class=NodeData)
NodeData.bind_property('value', 'address', path=lambda x: x.children[0])


class PublicAddressesData (BoundData):
    pass


class PublicAddressData (BoundData):
    def template(self):
        return Node('line', children=[
            Node('token', children=[PropertyNode('value', '127.0.0.1')]),
            Node('token', children=[PropertyNode('value', 'eth0')]),
        ])

PublicAddressesData.bind_collection('addresses', item_class=PublicAddressData)
PublicAddressData.bind_property('value', 'address', path=lambda x: x.children[0])
PublicAddressData.bind_property('value', 'interface', path=lambda x: x.children[1])

########NEW FILE########
__FILENAME__ = dhcpd
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class DHCPDData (BoundData):
    pass


class SubnetData (BoundData):
    def template(self):
        return Node(
            'subnet',
            parameter='192.168.0.0 netmask 255.255.255.0',
        )


class RangeData (BoundData):
    def template(self):
        return PropertyNode('range', '192.168.0.1 192.168.0.100')


class OptionData (BoundData):
    def template(self):
        return PropertyNode('option', '')


DHCPDData.bind_collection('subnets', selector=lambda x: x.name == 'subnet', item_class=SubnetData)
SubnetData.bind_attribute('parameter', 'name')
SubnetData.bind_collection('subnets', selector=lambda x: x.name == 'subnet', item_class=SubnetData)
SubnetData.bind_collection('ranges', selector=lambda x: x.name == 'range', item_class=RangeData)
RangeData.bind_attribute('value', 'range')
OptionData.bind_attribute('value', 'value')

for x in [DHCPDData, SubnetData]:
    x.bind_collection('options', selector=lambda x: x.name == 'option', item_class=OptionData)

########NEW FILE########
__FILENAME__ = exports
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class ExportsData (BoundData):
    pass


class ExportData (BoundData):
    def template(self):
        return Node(
            '/',
            Node('clients')
        )


class ClientData (BoundData):
    def template(self):
        return Node(
            'localhost',
            PropertyNode('options', '')
        )


ExportsData.bind_collection('exports', item_class=ExportData)
ExportData.bind_name('name')
ExportData.bind_attribute('comment', 'comment', default='')
ExportData.bind_collection('clients', path=lambda x: x['clients'], item_class=ClientData)
ClientData.bind_name('name')
ClientData.bind_property('options', 'options')

########NEW FILE########
__FILENAME__ = fstab
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class FSTabData (BoundData):
    pass


class FilesystemData (BoundData):
    fields = ['device', 'mountpoint', 'type', 'options', 'freq', 'passno']

    def template(self):
        return Node('line', children=[
            Node('token', children=[PropertyNode('value', 'none')]),
            Node('token', children=[PropertyNode('value', 'none')]),
            Node('token', children=[PropertyNode('value', 'auto')]),
            Node('token', children=[PropertyNode('value', 'defaults,rw')]),
            Node('token', children=[PropertyNode('value', '0')]),
            Node('token', children=[PropertyNode('value', '0')]),
        ])


FSTabData.bind_collection('filesystems', item_class=FilesystemData)
for i in range(0, len(FilesystemData.fields)):
    path = lambda i: lambda x: x.children[i]
    FilesystemData.bind_property('value', FilesystemData.fields[i], path=path(i))

########NEW FILE########
__FILENAME__ = group
from reconfigure.items.bound import BoundData


class GroupsData (BoundData):
    pass


class GroupData (BoundData):
    fields = ['name', 'password', 'gid', 'users']


GroupsData.bind_collection('groups', item_class=GroupData)
for i in range(0, len(GroupData.fields)):
    path = lambda i: lambda x: x.children[i]
    GroupData.bind_property('value', GroupData.fields[i], path=path(i))

########NEW FILE########
__FILENAME__ = hosts
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class HostsData (BoundData):
    pass


class HostData (BoundData):
    def template(self):
        return Node('line', children=[
            Node('token', children=[PropertyNode('value', '127.0.0.1')]),
            Node('token', children=[PropertyNode('value', 'localhost')]),
        ])


class AliasData (BoundData):
    def template(self):
        return Node()


HostsData.bind_collection('hosts', item_class=HostData)
HostData.bind_property('value', 'address', path=lambda x: x.children[0])
HostData.bind_property('value', 'name', path=lambda x: x.children[1])
HostData.bind_collection('aliases', item_class=AliasData, selector=lambda x: x.parent.indexof(x) > 1)
AliasData.bind_property('value', 'name')

########NEW FILE########
__FILENAME__ = iptables
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class IPTablesData (BoundData):
    pass


class TableData (BoundData):
    def template(self):
        return Node('custom')


class ChainData (BoundData):
    def template(self):
        return Node(
            'CUSTOM',
            PropertyNode('default', '-'),
        )


class RuleData (BoundData):
    def template(self):
        return Node(
            'append',
            Node(
                'option',
                Node('argument', PropertyNode('value', 'ACCEPT')),
                PropertyNode('negative', False),
                PropertyNode('name', 'j'),
            )
        )

    @property
    def summary(self):
        return ' '.join((
            ('! ' if x.negative else '') +
            ('-' if len(x.name) == 1 else '--') + x.name + ' ' +
            ' '.join(a.value for a in x.arguments))
            for x in self.options
        )

    def verify(self):
        protocol_option = None
        for option in self.options:
            if option.name in ['p', 'protocol']:
                self.options.remove(option)
                self.options.insert(0, option)
                protocol_option = option
        for option in self.options:
            if 'port' in option.name:
                if not protocol_option:
                    protocol_option = OptionData.create('protocol')
                    self.options.insert(0, protocol_option)

    def get_option(self, *names):
        for name in names:
            for option in self.options:
                if option.name == name:
                    return option


class OptionData (BoundData):
    templates = {
        'protocol': ['protocol', ['tcp']],
        'match': ['match', ['multiport']],
        'source': ['source', ['127.0.0.1']],
        'mac-source': ['mac-source', ['00:00:00:00:00:00']],
        'destination': ['destination', ['127.0.0.1']],
        'in-interface': ['in-interface', ['lo']],
        'out-interface': ['out-interface', ['lo']],
        'source-port': ['source-port', ['80']],
        'source-ports': ['source-ports', ['80,443']],
        'destination-port': ['destination-port', ['80']],
        'destination-ports': ['destination-ports', ['80,443']],
        'state': ['state', ['NEW']],
        'reject-with': ['reject-with', ['icmp-net-unreachable']],
        'custom': ['name', ['value']],
    }

    @staticmethod
    def create(template_id):
        t = OptionData.templates[template_id]
        return OptionData(Node(
            'option',
            *(
                [Node('argument', PropertyNode('value', x)) for x in t[1]]
                + [PropertyNode('negative', False)]
                + [PropertyNode('name', t[0])]
            )
        ))

    @staticmethod
    def create_destination():
        return OptionData(Node(
            'option',
            Node('argument', PropertyNode('value', 'ACCEPT')),
            PropertyNode('negative', False),
            PropertyNode('name', 'j'),
        ))


class ArgumentData (BoundData):
    pass


IPTablesData.bind_collection('tables', item_class=TableData)
TableData.bind_collection('chains', item_class=ChainData)
TableData.bind_name('name')
ChainData.bind_property('default', 'default')
ChainData.bind_collection('rules', selector=lambda x: x.name == 'append', item_class=RuleData)
ChainData.bind_name('name')
RuleData.bind_collection('options', item_class=OptionData)
RuleData.bind_attribute('comment', 'comment')
OptionData.bind_property('name', 'name')
OptionData.bind_property('negative', 'negative')
OptionData.bind_collection('arguments', selector=lambda x: x.name == 'argument', item_class=ArgumentData)
ArgumentData.bind_property('value', 'value')

########NEW FILE########
__FILENAME__ = netatalk
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData
from reconfigure.items.util import yn_getter, yn_setter


class NetatalkData (BoundData):
    pass


class GlobalData (BoundData):
    pass


class ShareData (BoundData):
    fields = ['path', 'appledouble', 'valid users', 'cnid scheme', 'ea', 'password']
    defaults = ['', 'ea', '', 'dbd', 'none', '']

    def template(self):
        return Node(
            'share',
            *[PropertyNode(x, y) for x, y in zip(ShareData.fields, ShareData.defaults)]
        )


NetatalkData.bind_child('global', lambda x: x.get('Global'), item_class=GlobalData)
NetatalkData.bind_collection('shares', selector=lambda x: x.name != 'Global', item_class=ShareData)


GlobalData.bind_property('afp port', 'afp_port', default='548')
GlobalData.bind_property('cnid listen', 'cnid_listen', default='localhost:4700')
GlobalData.bind_property('uam list', 'uam_list', default='uams_dhx.so,uams_dhx2.so')
GlobalData.bind_property(
    'zeroconf', 'zeroconf', default=True,
    getter=yn_getter, setter=yn_setter)

ShareData.bind_name('name')
ShareData.bind_attribute('comment', 'comment', path=lambda x: x.get('path'), default='')
for f, d in zip(ShareData.fields, ShareData.defaults):
    ShareData.bind_property(f, f.replace(' ', '_'), default=d)

########NEW FILE########
__FILENAME__ = nsd
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class NSDData (BoundData):
    pass


class ZoneData (BoundData):
    def template(self):
        return Node(
            'zone',
            PropertyNode('name', '"example.com"'),
            PropertyNode('file', '"example.com.zone"'),
        )


quote = lambda x: '"%s"' % x
unquote = lambda x: x.strip('"')

NSDData.bind_collection('zones', selector=lambda x: x.name == 'zone', item_class=ZoneData)
ZoneData.bind_property('name', 'name', getter=unquote, setter=quote)
ZoneData.bind_property('zonefile', 'file', getter=unquote, setter=quote)

########NEW FILE########
__FILENAME__ = passwd
from reconfigure.items.bound import BoundData


class PasswdData (BoundData):
    pass


class UserData (BoundData):
    fields = ['name', 'password', 'uid', 'gid', 'comment', 'home', 'shell']


PasswdData.bind_collection('users', item_class=UserData)
for i in range(0, len(UserData.fields)):
    path = lambda i: lambda x: x.children[i]
    UserData.bind_property('value', UserData.fields[i], path=path(i))

########NEW FILE########
__FILENAME__ = resolv
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class ResolvData (BoundData):
    pass


class ItemData (BoundData):
    def template(self):
        return Node('line', children=[
            Node('token', children=[PropertyNode('value', 'nameserver')]),
            Node('token', children=[PropertyNode('value', '8.8.8.8')]),
        ])


ResolvData.bind_collection('items', item_class=ItemData)
ItemData.bind_property('value', 'name', path=lambda x: x.children[0])
ItemData.bind_property('value', 'value', path=lambda x: x.children[1])

########NEW FILE########
__FILENAME__ = samba
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData
from reconfigure.items.util import yn_getter, yn_setter


class SambaData (BoundData):
    pass


class GlobalData (BoundData):
    pass


class ShareData (BoundData):
    fields = [
        'comment', 'path', 'guest ok', 'browseable', 'create mask', 'directory mask', 'read only',
        'follow symlinks', 'wide links', 'fstype', 'write list', 'veto files',
        'force create mode', 'force directory mode', 'dfree command', 'force user', 'force group',
        'valid users', 'read list', 'dfree cache time',
    ]
    defaults = [
        '', '', 'no', 'yes', '0744', '0755', 'yes',
        'yes', 'no', 'NTFS', '', '', '000', '000', '',
        '', '', '', '', '',
    ]
    default_values = [
        '', '', False, True, '0744', '0755', True,
        True, False, '', '', '', '000', '000', '',
        '', '', '', '', '',
    ]

    def template(self):
        return Node(
            'share',
            *[PropertyNode(x, y) for x, y in zip(ShareData.fields, ShareData.defaults)]
        )


SambaData.bind_child('global', lambda x: x.get('global'), item_class=GlobalData)
SambaData.bind_collection('shares', selector=lambda x: x.name != 'global', item_class=ShareData)


GlobalData.bind_property('workgroup', 'workgroup', default='')
GlobalData.bind_property('server string', 'server_string', default='')
GlobalData.bind_property('interfaces', 'interfaces', default='')
GlobalData.bind_property(
    'bind interfaces only', 'bind_interfaces_only', default=True,
    getter=yn_getter, setter=yn_setter)
GlobalData.bind_property('log file', 'log_file', default='')
GlobalData.bind_property('security', 'security', default='user')

ShareData.bind_name('name')
for f, d in zip(ShareData.fields, ShareData.default_values):
    if d not in [True, False]:
        ShareData.bind_property(f, f.replace(' ', '_'), default=d)
    else:
        ShareData.bind_property(
            f, f.replace(' ', '_'), default=d,
            getter=yn_getter, setter=yn_setter)

########NEW FILE########
__FILENAME__ = squid
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class SquidData (BoundData):
    pass


class ACLData (BoundData):
    def template(self, name=None, *args):
        children = [PropertyNode('1', name)]
        index = 2
        for arg in args:
            children += [PropertyNode(str(index), arg)]
            index += 1
        return Node(
            'line',
            PropertyNode('name', 'acl'),
            Node(
                'arguments',
                *children
            )
        )

    def describe(self):
        return ' '.join(x.value for x in self.options)


class HTTPAccessData (BoundData):
    def template(self):
        return Node(
            'line',
            PropertyNode('name', 'http_access'),
            Node('arguments', PropertyNode('1', ''))
        )


class HTTPPortData (BoundData):
    def template(self):
        return Node(
            'line',
            PropertyNode('name', 'http_port'),
            Node('arguments', PropertyNode('1', '3128'))
        )


class HTTPSPortData (BoundData):
    def template(self):
        return Node(
            'line',
            PropertyNode('name', 'https_port'),
            Node('arguments', PropertyNode('1', '3128'))
        )


class ArgumentData (BoundData):
    def template(self):
        return PropertyNode('value', 'none')


def __bind_by_name(cls, prop, name, itemcls):
    cls.bind_collection(
        prop,
        selector=lambda x: x.get('name').value == name,
        item_class=itemcls
    )

__bind_by_name(SquidData, 'acl', 'acl', ACLData)
__bind_by_name(SquidData, 'http_access', 'http_access', HTTPAccessData)
__bind_by_name(SquidData, 'http_port', 'http_port', HTTPPortData)
__bind_by_name(SquidData, 'https_port', 'https_port', HTTPSPortData)


def __bind_first_arg(cls, prop):
    cls.bind_attribute('value', prop, path=lambda x: x.get('arguments').children[0])


def __bind_other_args(cls, prop, itemcls):
    cls.bind_collection(
        prop, path=lambda x: x.get('arguments'),
        selector=lambda x: x.parent.children.index(x) > 0, item_class=itemcls
    )

__bind_first_arg(ACLData, 'name')
__bind_other_args(ACLData, 'options', ArgumentData)

__bind_first_arg(HTTPAccessData, 'mode')
__bind_other_args(HTTPAccessData, 'options', ArgumentData)

__bind_first_arg(HTTPPortData, 'port')
__bind_other_args(HTTPPortData, 'options', ArgumentData)
__bind_first_arg(HTTPSPortData, 'port')
__bind_other_args(HTTPSPortData, 'options', ArgumentData)

ArgumentData.bind_attribute('value', 'value')

########NEW FILE########
__FILENAME__ = supervisor
from reconfigure.nodes import Node, PropertyNode
from reconfigure.items.bound import BoundData


class SupervisorData (BoundData):
    pass


class ProgramData (BoundData):
    fields = ['command', 'autostart', 'autorestart', 'startsecs', 'startretries', \
        'user', 'directory', 'umask', 'environment']

    def template(self):
        return Node('program:new',
            PropertyNode('command', 'false'),
        )


SupervisorData.bind_collection('programs', item_class=ProgramData, selector=lambda x: x.name.startswith('program:'))
ProgramData.bind_name('name', getter=lambda x: x[8:], setter=lambda x: 'program:%s' % x)
ProgramData.bind_attribute('comment', 'comment')
for i in range(0, len(ProgramData.fields)):
    ProgramData.bind_property(ProgramData.fields[i], ProgramData.fields[i], default_remove=[None, ''])

########NEW FILE########
__FILENAME__ = util
yn_getter = lambda x: x == 'yes'
yn_setter = lambda x: 'yes' if x else 'no'
onezero_getter = lambda x: x == '1'
onezero_setter = lambda x: '1' if x else '0'

########NEW FILE########
__FILENAME__ = nodes
class Node (object):
    """
    A base node class for the Node Tree.
    This class represents a named container node.
    """

    def __init__(self, name=None, *args, **kwargs):
        """
        :param name: Node name
        :param *args: Children
        :param comment: Node comment string
        :param origin: Node's source location (usually path to the file)
        """
        self.name = name
        self.origin = None
        self.children = []
        for node in list(args) + kwargs.pop('children', []):
            self.append(node)
        self.comment = kwargs.pop('comment', None)
        self.__dict__.update(kwargs)

    def __str__(self):
        s = '(%s)' % self.name
        if self.comment:
            s += ' (%s)' % self.comment
        s += '\n'
        for child in self.children:
            if child.origin != self.origin:
                s += '\t@%s\n' % child.origin
            s += '\n'.join('\t' + x for x in str(child).splitlines()) + '\n'
        return s

    def __hash__(self):
        return sum(hash(x) for x in [self.name, self.origin, self.comment] + self.children)

    def __eq__(self, other):
        if other is None:
            return False

        return \
            self.name == other.name and \
            self.comment == other.comment and \
            self.origin == other.origin and \
            set(self.children) == set(other.children)

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def __nonzero__(self):
        return True

    def __getitem__(self, key):
        if type(key) in (int, slice):
            return self.children[key]
        return self.get(key)

    def __setitem__(self, key, value):
        if type(key) is int:
            self.children[key] = value
        self.set_property(key, value)

    def __contains__(self, item):
        return item in self.children

    def indexof(self, node):
        """
        :returns: index of the node in the children array or ``None`` if it's not a child
        """
        if node in self.children:
            return self.children.index(node)
        else:
            return None

    def get(self, name, default=None):
        """
        :returns: a child node by its name or ``default``
        """
        for child in self.children:
            if child.name == name:
                return child
        if default:
            self.append(default)
        return default

    def get_all(self, name):
        """
        :returns: list of child nodes with supplied ``name``
        """
        return [n for n in self.children if n.name == name]

    def append(self, node):
        if not node.origin:
            node.origin = self.origin
        self.children.append(node)
        node.parent = self

    def remove(self, node):
        self.children.remove(node)

    def replace(self, name, node=None):
        """
        Replaces the child nodes by ``name``

        :param node: replacement node or list of nodes 

        ::

            n.append(Node('a'))
            n.append(Node('a'))
            n.replace('a', None)
            assert(len(n.get_all('a')) == 0)

        """
        if name:
            self.children = [c for c in self.children if c.name != name]
        if node is not None:
            if type(node) == list:
                for n in node:
                    self.children.append(n)
            else:
                self.children.append(node)

    def set_property(self, name, value):
        """
        Creates or replaces a child :class:`PropertyNode` by name.
        """
        node = self.get(name)
        if node is None:
            node = PropertyNode(name, value)
            self.append(node)
        node.value = value
        return self


class RootNode (Node):
    """
    A special node class that indicates tree root
    """


class PropertyNode (Node):
    """
    A node that serves as a property of its parent node.
    """

    def __init__(self, name, value, comment=None):
        """
        :param name: Property name
        :param value: Property value
        """
        Node.__init__(self, name, comment=comment)
        self.value = value

    def __eq__(self, other):
        if other is None:
            return False

        return \
            Node.__eq__(self, other) and \
            self.value == other.value

    def __hash__(self):
        return Node.__hash__(self) + hash(self.value)

    def __str__(self):
        s = '%s = %s' % (self.name, self.value)
        if self.comment:
            s += ' (%s)' % self.comment
        return s


class IncludeNode (Node):
    """
    A node that indicates a junction point between two config files
    """

    def __init__(self, files):
        """
        :param files: an includer-dependent config location specifier
        """
        Node.__init__(self)
        self.name = '<include>'
        self.files = files

    def __str__(self):
        return '<include> %s' % self.files

########NEW FILE########
__FILENAME__ = base
class BaseParser (object):  # pragma: no cover
    """
    A base parser class
    """

    def parse(self, content):
        """
        :param content: string config content
        :returns: a :class:`reconfigure.nodes.Node` tree
        """
        return None

    def stringify(self, tree):
        """
        :param tree: a :class:`reconfigure.nodes.Node` tree
        :returns: string config content
        """
        return None

########NEW FILE########
__FILENAME__ = bind9
from reconfigure.nodes import *
from reconfigure.parsers.nginx import NginxParser


class BIND9Parser (NginxParser):
    """
    A parser for named.conf
    """

    tokens = [
        (r"[\w_]+\s*?.*?{", lambda s, t: ('section_start', t)),
        (r"[\w\d_:.]+?.*?;", lambda s, t: ('option', t)),
        (r"\".*?\"\s*;", lambda s, t: ('option', t)),
        (r"\s", lambda s, t: 'whitespace'),
        (r"$^", lambda s, t: 'newline'),
        (r"\#.*?\n", lambda s, t: ('comment', t)),
        (r"//.*?\n", lambda s, t: ('comment', t)),
        (r"/\*.*?\*/", lambda s, t: ('comment', t)),
        (r"\};", lambda s, t: 'section_end'),
    ]
    token_section_end = '};'

########NEW FILE########
__FILENAME__ = crontab
from reconfigure.nodes import RootNode, Node, PropertyNode
from reconfigure.parsers import BaseParser


class CrontabParser(BaseParser):

    def __init__(self, remove_comments=False):
        self.remove_comments = remove_comments

    def parse(self, content):
        root = RootNode()
        lines = [l.strip() for l in content.splitlines() if l]
        comment = None
        for line in lines:
            if line.startswith('#'):
                comment = '\n'.join([comment, line]) if comment else line[1:]
                continue
            elif line.startswith('@'):
                special, command = line.split(' ', 1)
                node = Node('special_task', comment=comment)
                node.append(PropertyNode('special', special))
                node.append(PropertyNode('command', command))

            else:
                split_line = line.split(' ', 5)
                if len(split_line) <= 3 and '=' in line:
                    name, value = [n.strip() for n in line.split('=')]
                    if not name:
                        continue
                    node = Node('env_setting', comment=comment)
                    node.append(PropertyNode('name', name))
                    node.append(PropertyNode('value', value))
                elif len(split_line) == 6:
                    node = Node('normal_task', comment=comment)
                    node.append(PropertyNode('minute', split_line[0]))
                    node.append(PropertyNode('hour', split_line[1]))
                    node.append(PropertyNode('day_of_month', split_line[2]))
                    node.append(PropertyNode('month', split_line[3]))
                    node.append(PropertyNode('day_of_week', split_line[4]))
                    node.append(PropertyNode('command', split_line[5]))
                else:
                    continue
            root.append(node)
            comment = None
        root.comment = comment
        return root

    def stringify(self, tree):
        result_lines = []
        stringify_func = {
            'special_task': self.stringify_special_task,
            'env_setting': self.stringify_env_setting,
            'normal_task': self.stringify_normal_task,
        }
        for node in tree:
            if isinstance(node, Node):
                string_line = stringify_func.get(node.name, lambda x: '')(node)
                if node.comment:
                    result_lines.append('#' + node.comment)
                result_lines.append(string_line)
        return '\n'.join([line for line in result_lines if line])

    def stringify_special_task(self, node):
        special_node = node.get('special')
        command_node = node.get('command')
        if isinstance(special_node, PropertyNode) and isinstance(command_node, PropertyNode):
            return ' '.join([special_node.value, command_node.value])
        return ''

    def stringify_env_setting(self, node):
        name = node.get('name')
        value = node.get('value')
        if isinstance(name, PropertyNode) and isinstance(value, PropertyNode):
                return ' = '.join([name.value, value.value])
        return ''

    def stringify_normal_task(self, node):
        if all([isinstance(child, PropertyNode) for child in node.children]):
            values_list = [str(pr_node.value).strip() for pr_node in node.children if pr_node.value]
            if len(values_list) == 6:
                return ' '.join(values_list)
        return ''

########NEW FILE########
__FILENAME__ = exports
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser
from reconfigure.parsers.ssv import SSVParser


class ExportsParser (BaseParser):
    """
    A parser for NFS' /etc/exports
    """

    def __init__(self, *args, **kwargs):
        BaseParser.__init__(self, *args, **kwargs)
        self.inner = SSVParser(continuation='\\')

    def parse(self, content):
        tree = self.inner.parse(content)
        root = RootNode()
        for export in tree:
            export_node = Node(export[0].get('value').value)
            export_node.comment = export.comment
            clients_node = Node('clients')
            export_node.append(clients_node)
            root.append(export_node)

            for client in export[1:]:
                s = client.get('value').value
                name = s.split('(')[0]
                options = ''
                if '(' in s:
                    options = s.split('(', 1)[1].rstrip(')')
                client_node = Node(name)
                client_node.set_property('options', options)
                clients_node.append(client_node)
        return root

    def stringify(self, tree):
        root = RootNode()
        for export in tree:
            export_node = Node('line', comment=export.comment)
            export_node.append(Node('token', PropertyNode('value', export.name)))
            for client in export['clients']:
                s = client.name
                if client['options'].value:
                    s += '(%s)' % client['options'].value
                export_node.append(Node('token', PropertyNode('value', s)))
            root.append(export_node)
        return self.inner.stringify(root)

########NEW FILE########
__FILENAME__ = ini
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser
from reconfigure.parsers.iniparse import INIConfig

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class IniFileParser (BaseParser):
    """
    A parser for standard ``.ini`` config files.

    :param sectionless: if ``True``, allows a section-less attributes appear in the beginning of file
    """

    def __init__(self, sectionless=False, nullsection='__default__'):
        self.sectionless = sectionless
        self.nullsection = nullsection

    def _get_comment(self, container):
        c = container.contents[0].comment
        return c.strip() if c else None

    def _set_comment(self, container, comment):
        if comment:
            container.contents[0].comment = comment
            container.contents[0].comment_separator = ';'

    def parse(self, content):
        content = '\n'.join(filter(None, [x.strip() for x in content.splitlines()]))
        if self.sectionless:
            content = '[' + self.nullsection + ']\n' + content
        data = StringIO(content)
        cp = INIConfig(data, optionxformvalue=lambda x: x)

        root = RootNode()
        for section in cp:
            name = section
            if self.sectionless and section == self.nullsection:
                name = None
            section_node = Node(name)
            section_node.comment = self._get_comment(cp[section]._lines[0])
            for option in cp[section]:
                if option in cp[section]._options:
                    node = PropertyNode(option, cp[section][option])
                    node.comment = self._get_comment(cp[section]._options[option])
                    section_node.children.append(node)
            root.children.append(section_node)
        return root

    def stringify(self, tree):
        cp = INIConfig()
        for section in tree.children:
            if self.sectionless and section.name is None:
                sectionname = self.nullsection
            else:
                sectionname = section.name
            cp._new_namespace(sectionname)
            for option in section.children:
                if not isinstance(option, PropertyNode):
                    raise TypeError('Third level nodes should be PropertyNodes')
                cp[sectionname][option.name] = option.value
                if option.comment:
                    self._set_comment(cp[sectionname]._options[option.name], option.comment)
            if hasattr(cp[sectionname], '_lines'):
                self._set_comment(cp[sectionname]._lines[0], section.comment)

        data = str(cp) + '\n'
        if self.sectionless:
            data = data.replace('[' + self.nullsection + ']\n', '')
        return data

########NEW FILE########
__FILENAME__ = compat
# Copyright (c) 2001, 2002, 2003 Python Software Foundation
# Copyright (c) 2004-2008 Paramjit Oberoi <param.cs.wisc.edu>
# All Rights Reserved.  See LICENSE-PSF & LICENSE for details.

"""Compatibility interfaces for ConfigParser

Interfaces of ConfigParser, RawConfigParser and SafeConfigParser
should be completely identical to the Python standard library
versions.  Tested with the unit tests included with Python-2.3.4

The underlying INIConfig object can be accessed as cfg.data
"""

import re
try:
    from ConfigParser import DuplicateSectionError,    \
                      NoSectionError, NoOptionError,   \
                      InterpolationMissingOptionError, \
                      InterpolationDepthError,         \
                      InterpolationSyntaxError,        \
                      DEFAULTSECT, MAX_INTERPOLATION_DEPTH

    # These are imported only for compatiability.
    # The code below does not reference them directly.
    from ConfigParser import Error, InterpolationError, \
                      MissingSectionHeaderError, ParsingError
except ImportError:
    from configparser import DuplicateSectionError,    \
                      NoSectionError, NoOptionError,   \
                      InterpolationMissingOptionError, \
                      InterpolationDepthError,         \
                      InterpolationSyntaxError,        \
                      DEFAULTSECT, MAX_INTERPOLATION_DEPTH

    # These are imported only for compatiability.
    # The code below does not reference them directly.
    from configparser import Error, InterpolationError, \
                      MissingSectionHeaderError, ParsingError

import reconfigure.parsers.iniparse.ini


class RawConfigParser(object):
    def __init__(self, defaults=None, dict_type=dict):
        if dict_type != dict:
            raise ValueError('Custom dict types not supported')
        self.data = ini.INIConfig(defaults=defaults, optionxformsource=self)

    def optionxform(self, optionstr):
        return optionstr.lower()

    def defaults(self):
        d = {}
        secobj = self.data._defaults
        for name in secobj._options:
            d[name] = secobj._compat_get(name)
        return d

    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        return list(self.data)

    def add_section(self, section):
        """Create a new section in the configuration.

        Raise DuplicateSectionError if a section by the specified name
        already exists.  Raise ValueError if name is DEFAULT or any of
        its case-insensitive variants.
        """
        # The default section is the only one that gets the case-insensitive
        # treatment - so it is special-cased here.
        if section.lower() == "default":
            raise ValueError('Invalid section name: %s' % section)

        if self.has_section(section):
            raise DuplicateSectionError(section)
        else:
            self.data._new_namespace(section)

    def has_section(self, section):
        """Indicate whether the named section is present in the configuration.

        The DEFAULT section is not acknowledged.
        """
        return (section in self.data)

    def options(self, section):
        """Return a list of option names for the given section name."""
        if section in self.data:
            return list(self.data[section])
        else:
            raise NoSectionError(section)

    def read(self, filenames):
        """Read and parse a filename or a list of filenames.

        Files that cannot be opened are silently ignored; this is
        designed so that you can specify a list of potential
        configuration file locations (e.g. current directory, user's
        home directory, systemwide directory), and all existing
        configuration files in the list will be read.  A single
        filename may also be given.
        """
        files_read = []
        if isinstance(filenames, basestring):
            filenames = [filenames]
        for filename in filenames:
            try:
                fp = open(filename)
            except IOError:
                continue
            files_read.append(filename)
            self.data._readfp(fp)
            fp.close()
        return files_read

    def readfp(self, fp, filename=None):
        """Like read() but the argument must be a file-like object.

        The `fp' argument must have a `readline' method.  Optional
        second argument is the `filename', which if not given, is
        taken from fp.name.  If fp has no `name' attribute, `<???>' is
        used.
        """
        self.data._readfp(fp)

    def get(self, section, option, vars=None):
        if not self.has_section(section):
            raise NoSectionError(section)
        if vars is not None and option in vars:
            value = vars[option]

        sec = self.data[section]
        if option in sec:
            return sec._compat_get(option)
        else:
            raise NoOptionError(option, section)

    def items(self, section):
        if section in self.data:
            ans = []
            for opt in self.data[section]:
                ans.append((opt, self.get(section, opt)))
            return ans
        else:
            raise NoSectionError(section)

    def getint(self, section, option):
        return int(self.get(section, option))

    def getfloat(self, section, option):
        return float(self.get(section, option))

    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def getboolean(self, section, option):
        v = self.get(section, option)
        if v.lower() not in self._boolean_states:
            raise ValueError('Not a boolean: %s' % v)
        return self._boolean_states[v.lower()]

    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        if section in self.data:
            sec = self.data[section]
        else:
            raise NoSectionError(section)
        return (option in sec)

    def set(self, section, option, value):
        """Set an option."""
        if section in self.data:
            self.data[section][option] = value
        else:
            raise NoSectionError(section)

    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""
        fp.write(str(self.data))

    def remove_option(self, section, option):
        """Remove an option."""
        if section in self.data:
            sec = self.data[section]
        else:
            raise NoSectionError(section)
        if option in sec:
            del sec[option]
            return 1
        else:
            return 0

    def remove_section(self, section):
        """Remove a file section."""
        if not self.has_section(section):
            return False
        del self.data[section]
        return True


class ConfigDict(object):
    """Present a dict interface to a ini section."""

    def __init__(self, cfg, section, vars):
        self.cfg = cfg
        self.section = section
        self.vars = vars

    def __getitem__(self, key):
        try:
            return RawConfigParser.get(self.cfg, self.section, key, self.vars)
        except (NoOptionError, NoSectionError):
            raise KeyError(key)


class ConfigParser(RawConfigParser):

    def get(self, section, option, raw=False, vars=None):
        """Get an option value for a given section.

        All % interpolations are expanded in the return values, based on the
        defaults passed into the constructor, unless the optional argument
        `raw' is true.  Additional substitutions may be provided using the
        `vars' argument, which must be a dictionary whose contents overrides
        any pre-existing defaults.

        The section DEFAULT is special.
        """
        if section != DEFAULTSECT and not self.has_section(section):
            raise NoSectionError(section)

        option = self.optionxform(option)
        value = RawConfigParser.get(self, section, option, vars)

        if raw:
            return value
        else:
            d = ConfigDict(self, section, vars)
            return self._interpolate(section, option, value, d)

    def _interpolate(self, section, option, rawval, vars):
        # do the string interpolation
        value = rawval
        depth = MAX_INTERPOLATION_DEPTH
        while depth:                    # Loop through this until it's done
            depth -= 1
            if "%(" in value:
                try:
                    value = value % vars
                except KeyError as e:
                    raise InterpolationMissingOptionError(
                        option, section, rawval, e.args[0])
            else:
                break
        if value.find("%(") != -1:
            raise InterpolationDepthError(option, section, rawval)
        return value

    def items(self, section, raw=False, vars=None):
        """Return a list of tuples with (name, value) for each option
        in the section.

        All % interpolations are expanded in the return values, based on the
        defaults passed into the constructor, unless the optional argument
        `raw' is true.  Additional substitutions may be provided using the
        `vars' argument, which must be a dictionary whose contents overrides
        any pre-existing defaults.

        The section DEFAULT is special.
        """
        if section != DEFAULTSECT and not self.has_section(section):
            raise NoSectionError(section)
        if vars is None:
            options = list(self.data[section])
        else:
            options = []
            for x in self.data[section]:
                if x not in vars:
                    options.append(x)
            options.extend(vars.keys())

        if "__name__" in options:
            options.remove("__name__")

        d = ConfigDict(self, section, vars)
        if raw:
            return [(option, d[option])
                    for option in options]
        else:
            return [(option, self._interpolate(section, option, d[option], d))
                    for option in options]


class SafeConfigParser(ConfigParser):
    _interpvar_re = re.compile(r"%\(([^)]+)\)s")
    _badpercent_re = re.compile(r"%[^%]|%$")

    def set(self, section, option, value):
        if not isinstance(value, basestring):
            raise TypeError("option values must be strings")
        # check for bad percent signs:
        # first, replace all "good" interpolations
        tmp_value = self._interpvar_re.sub('', value)
        # then, check if there's a lone percent sign left
        m = self._badpercent_re.search(tmp_value)
        if m:
            raise ValueError("invalid interpolation syntax in %r at "
                             "position %d" % (value, m.start()))

        ConfigParser.set(self, section, option, value)

    def _interpolate(self, section, option, rawval, vars):
        # do the string interpolation
        L = []
        self._interpolate_some(option, L, rawval, section, vars, 1)
        return ''.join(L)

    _interpvar_match = re.compile(r"%\(([^)]+)\)s").match

    def _interpolate_some(self, option, accum, rest, section, map, depth):
        if depth > MAX_INTERPOLATION_DEPTH:
            raise InterpolationDepthError(option, section, rest)
        while rest:
            p = rest.find("%")
            if p < 0:
                accum.append(rest)
                return
            if p > 0:
                accum.append(rest[:p])
                rest = rest[p:]
            # p is no longer used
            c = rest[1:2]
            if c == "%":
                accum.append("%")
                rest = rest[2:]
            elif c == "(":
                m = self._interpvar_match(rest)
                if m is None:
                    raise InterpolationSyntaxError(option, section,
                        "bad interpolation variable reference %r" % rest)
                var = m.group(1)
                rest = rest[m.end():]
                try:
                    v = map[var]
                except KeyError:
                    raise InterpolationMissingOptionError(
                        option, section, rest, var)
                if "%" in v:
                    self._interpolate_some(option, accum, v,
                                           section, map, depth + 1)
                else:
                    accum.append(v)
            else:
                raise InterpolationSyntaxError(
                    option, section,
                    "'%' must be followed by '%' or '(', found: " + repr(rest))
########NEW FILE########
__FILENAME__ = config
class ConfigNamespace(object):
    """Abstract class representing the interface of Config objects.

    A ConfigNamespace is a collection of names mapped to values, where
    the values may be nested namespaces.  Values can be accessed via
    container notation - obj[key] - or via dotted notation - obj.key.
    Both these access methods are equivalent.

    To minimize name conflicts between namespace keys and class members,
    the number of class members should be minimized, and the names of
    all class members should start with an underscore.

    Subclasses must implement the methods for container-like access,
    and this class will automatically provide dotted access.

    """

    # Methods that must be implemented by subclasses

    def _getitem(self, key):
        return NotImplementedError(key)

    def __setitem__(self, key, value):
        raise NotImplementedError(key, value)

    def __delitem__(self, key):
        raise NotImplementedError(key)

    def __iter__(self):
        return NotImplementedError()

    def _new_namespace(self, name):
        raise NotImplementedError(name)

    def __contains__(self, key):
        try:
            self._getitem(key)
        except KeyError:
            return False
        return True

    # Machinery for converting dotted access into container access,
    # and automatically creating new sections/namespaces.
    #
    # To distinguish between accesses of class members and namespace
    # keys, we first call object.__getattribute__().  If that succeeds,
    # the name is assumed to be a class member.  Otherwise it is
    # treated as a namespace key.
    #
    # Therefore, member variables should be defined in the class,
    # not just in the __init__() function.  See BasicNamespace for
    # an example.

    def __getitem__(self, key):
        try:
            return self._getitem(key)
        except KeyError:
            return Undefined(key, self)

    def __getattr__(self, name):
        try:
            return self._getitem(name)
        except KeyError:
            if name.startswith('__') and name.endswith('__'):
                raise AttributeError
            return Undefined(name, self)

    def __setattr__(self, name, value):
        try:
            object.__getattribute__(self, name)
            object.__setattr__(self, name, value)
        except AttributeError:
            self.__setitem__(name, value)

    def __delattr__(self, name):
        try:
            object.__getattribute__(self, name)
            object.__delattr__(self, name)
        except AttributeError:
            self.__delitem__(name)

    # During unpickling, Python checks if the class has a __setstate__
    # method.  But, the data dicts have not been initialised yet, which
    # leads to  _getitem and hence __getattr__ raising an exception.  So
    # we explicitly impement default __setstate__ behavior.
    def __setstate__(self, state):
        self.__dict__.update(state)

class Undefined(object):
    """Helper class used to hold undefined names until assignment.

    This class helps create any undefined subsections when an
    assignment is made to a nested value.  For example, if the
    statement is "cfg.a.b.c = 42", but "cfg.a.b" does not exist yet.
    """

    def __init__(self, name, namespace):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'namespace', namespace)

    def __setattr__(self, name, value):
        obj = self.namespace._new_namespace(self.name)
        obj[name] = value

    def __setitem__(self, name, value):
        obj = self.namespace._new_namespace(self.name)
        obj[name] = value


# ---- Basic implementation of a ConfigNamespace

class BasicConfig(ConfigNamespace):
    """Represents a hierarchical collection of named values.

    Values are added using dotted notation:

    >>> n = BasicConfig()
    >>> n.x = 7
    >>> n.name.first = 'paramjit'
    >>> n.name.last = 'oberoi'

    ...and accessed the same way, or with [...]:

    >>> n.x
    7
    >>> n.name.first
    'paramjit'
    >>> n.name.last
    'oberoi'
    >>> n['x']
    7
    >>> n['name']['first']
    'paramjit'

    Iterating over the namespace object returns the keys:

    >>> l = list(n)
    >>> l.sort()
    >>> l
    ['name', 'x']

    Values can be deleted using 'del' and printed using 'print'.

    >>> n.aaa = 42
    >>> del n.x
    >>> print n
    aaa = 42
    name.first = paramjit
    name.last = oberoi

    Nested namepsaces are also namespaces:

    >>> isinstance(n.name, ConfigNamespace)
    True
    >>> print n.name
    first = paramjit
    last = oberoi
    >>> sorted(list(n.name))
    ['first', 'last']

    Finally, values can be read from a file as follows:

    >>> from StringIO import StringIO
    >>> sio = StringIO('''
    ... # comment
    ... ui.height = 100
    ... ui.width = 150
    ... complexity = medium
    ... have_python
    ... data.secret.password = goodness=gracious me
    ... ''')
    >>> n = BasicConfig()
    >>> n._readfp(sio)
    >>> print n
    complexity = medium
    data.secret.password = goodness=gracious me
    have_python
    ui.height = 100
    ui.width = 150
    """

    # this makes sure that __setattr__ knows this is not a namespace key
    _data = None

    def __init__(self):
        self._data = {}

    def _getitem(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __str__(self, prefix=''):
        lines = []
        keys = self._data.keys()
        keys.sort()
        for name in keys:
            value = self._data[name]
            if isinstance(value, ConfigNamespace):
                lines.append(value.__str__(prefix='%s%s.' % (prefix,name)))
            else:
                if value is None:
                    lines.append('%s%s' % (prefix, name))
                else:
                    lines.append('%s%s = %s' % (prefix, name, value))
        return '\n'.join(lines)

    def _new_namespace(self, name):
        obj = BasicConfig()
        self._data[name] = obj
        return obj

    def _readfp(self, fp):
        while True:
            line = fp.readline()
            if not line:
                break

            line = line.strip()
            if not line: continue
            if line[0] == '#': continue
            data = line.split('=', 1)
            if len(data) == 1:
                name = line
                value = None
            else:
                name = data[0].strip()
                value = data[1].strip()
            name_components = name.split('.')
            ns = self
            for n in name_components[:-1]:
                if n in ns:
                    ns = ns[n]
                    if not isinstance(ns, ConfigNamespace):
                        raise TypeError('value-namespace conflict', n)
                else:
                    ns = ns._new_namespace(n)
            ns[name_components[-1]] = value


# ---- Utility functions

def update_config(target, source):
    """Imports values from source into target.

    Recursively walks the <source> ConfigNamespace and inserts values
    into the <target> ConfigNamespace.  For example:

    >>> n = BasicConfig()
    >>> n.playlist.expand_playlist = True
    >>> n.ui.display_clock = True
    >>> n.ui.display_qlength = True
    >>> n.ui.width = 150
    >>> print n
    playlist.expand_playlist = True
    ui.display_clock = True
    ui.display_qlength = True
    ui.width = 150

    >>> from iniparse import ini
    >>> i = ini.INIConfig()
    >>> update_config(i, n)
    >>> print i
    [playlist]
    expand_playlist = True
    <BLANKLINE>
    [ui]
    display_clock = True
    display_qlength = True
    width = 150

    """
    for name in source:
        value = source[name]
        if isinstance(value, ConfigNamespace):
            if name in target:
                myns = target[name]
                if not isinstance(myns, ConfigNamespace):
                    raise TypeError('value-namespace conflict')
            else:
                myns = target._new_namespace(name)
            update_config(myns, value)
        else:
            target[name] = value



########NEW FILE########
__FILENAME__ = ini
from __future__ import unicode_literals
"""Access and/or modify INI files

* Compatiable with ConfigParser
* Preserves order of sections & options
* Preserves comments/blank lines/etc
* More conveninet access to data

Example:

    >>> from StringIO import StringIO
    >>> sio = StringIO('''# configure foo-application
    ... [foo]
    ... bar1 = qualia
    ... bar2 = 1977
    ... [foo-ext]
    ... special = 1''')

    >>> cfg = INIConfig(sio)
    >>> print cfg.foo.bar1
    qualia
    >>> print cfg['foo-ext'].special
    1
    >>> cfg.foo.newopt = 'hi!'
    >>> cfg.baz.enabled = 0

    >>> print cfg
    # configure foo-application
    [foo]
    bar1 = qualia
    bar2 = 1977
    newopt = hi!
    [foo-ext]
    special = 1
    <BLANKLINE>
    [baz]
    enabled = 0

"""

# An ini parser that supports ordered sections/options
# Also supports updates, while preserving structure
# Backward-compatiable with ConfigParser

import re
try:
    from ConfigParser import DEFAULTSECT, ParsingError, MissingSectionHeaderError
except ImportError:
    from configparser import DEFAULTSECT, ParsingError, MissingSectionHeaderError

from reconfigure.parsers.iniparse import config

class LineType(object):
    line = None

    def __init__(self, line=None):
        if line is not None:
            self.line = line.strip('\n')

    # Return the original line for unmodified objects
    # Otherwise construct using the current attribute values
    def __str__(self):
        if self.line is not None:
            return self.line
        else:
            return self.to_string()

    # If an attribute is modified after initialization
    # set line to None since it is no longer accurate.
    def __setattr__(self, name, value):
        if hasattr(self,name):
            self.__dict__['line'] = None
        self.__dict__[name] = value

    def to_string(self):
        raise Exception('This method must be overridden in derived classes')


class SectionLine(LineType):
    regex =  re.compile(r'^\['
                        r'(?P<name>[^]]+)'
                        r'\]\s*'
                        r'((?P<csep>;|#)(?P<comment>.*))?$')

    def __init__(self, name, comment=None, comment_separator=None,
                             comment_offset=-1, line=None):
        super(SectionLine, self).__init__(line)
        self.name = name
        self.comment = comment
        self.comment_separator = comment_separator
        self.comment_offset = comment_offset

    def to_string(self):
        out = '[' + self.name + ']'
        if self.comment is not None:
            # try to preserve indentation of comments
            out = (out+' ').ljust(self.comment_offset)
            out = out + self.comment_separator + self.comment
        return out

    def parse(cls, line):
        m = cls.regex.match(line.rstrip())
        if m is None:
            return None
        return cls(m.group('name'), m.group('comment'),
                   m.group('csep'), m.start('csep'),
                   line)
    parse = classmethod(parse)


class OptionLine(LineType):
    def __init__(self, name, value, separator='=', comment=None,
                 comment_separator=None, comment_offset=-1, line=None):
        super(OptionLine, self).__init__(line)
        self.name = name
        self.value = value
        self.separator = separator
        self.comment = comment
        self.comment_separator = comment_separator
        self.comment_offset = comment_offset

    def to_string(self):
        out = '%s%s%s' % (self.name, self.separator, self.value)
        if self.comment is not None:
            # try to preserve indentation of comments
            out = (out+' ').ljust(self.comment_offset)
            out = out + self.comment_separator + self.comment
        return out

    regex = re.compile(r'^(?P<name>[^:=\s[][^:=]*)'
                       r'(?P<sep>[:=]\s*)'
                       r'(?P<value>.*)$')

    def parse(cls, line):
        m = cls.regex.match(line.rstrip())
        if m is None:
            return None

        name = m.group('name').rstrip()
        value = m.group('value')
        sep = m.group('name')[len(name):] + m.group('sep')

        # comments are not detected in the regex because
        # ensuring total compatibility with ConfigParser
        # requires that:
        #     option = value    ;comment   // value=='value'
        #     option = value;1  ;comment   // value=='value;1  ;comment'
        #
        # Doing this in a regex would be complicated.  I
        # think this is a bug.  The whole issue of how to
        # include ';' in the value needs to be addressed.
        # Also, '#' doesn't mark comments in options...

        coff = value.find(';')
        if coff != -1 and value[coff-1].isspace():
            comment = value[coff+1:]
            csep = value[coff]
            value = value[:coff].rstrip()
            coff = m.start('value') + coff
        else:
            comment = None
            csep = None
            coff = -1

        return cls(name, value, sep, comment, csep, coff, line)
    parse = classmethod(parse)


def change_comment_syntax(comment_chars='%;#', allow_rem=False):
    comment_chars = re.sub(r'([\]\-\^])', r'\\\1', comment_chars)
    regex = r'^(?P<csep>[%s]' % comment_chars
    if allow_rem:
        regex += '|[rR][eE][mM]'
    regex += r')(?P<comment>.*)$'
    CommentLine.regex = re.compile(regex)

class CommentLine(LineType):
    regex = re.compile(r'^(?P<csep>[;#]|[rR][eE][mM])'
                       r'(?P<comment>.*)$')

    def __init__(self, comment='', separator='#', line=None):
        super(CommentLine, self).__init__(line)
        self.comment = comment
        self.separator = separator

    def to_string(self):
        return self.separator + self.comment

    def parse(cls, line):
        m = cls.regex.match(line.rstrip())
        if m is None:
            return None
        return cls(m.group('comment'), m.group('csep'), line)
    parse = classmethod(parse)


class EmptyLine(LineType):
    # could make this a singleton
    def to_string(self):
        return ''

    value = property(lambda _: '')

    def parse(cls, line):
        if line.strip(): return None
        return cls(line)
    parse = classmethod(parse)


class ContinuationLine(LineType):
    regex = re.compile(r'^\s+(?P<value>.*)$')

    def __init__(self, value, value_offset=None, line=None):
        super(ContinuationLine, self).__init__(line)
        self.value = value
        if value_offset is None:
            value_offset = 8
        self.value_offset = value_offset

    def to_string(self):
        return ' '*self.value_offset + self.value

    def parse(cls, line):
        m = cls.regex.match(line.rstrip())
        if m is None:
            return None
        return cls(m.group('value'), m.start('value'), line)
    parse = classmethod(parse)


class LineContainer(object):
    def __init__(self, d=None):
        self.contents = []
        self.orgvalue = None
        if d:
            if isinstance(d, list): self.extend(d)
            else: self.add(d)

    def add(self, x):
        self.contents.append(x)

    def extend(self, x):
        for i in x: self.add(i)

    def get_name(self):
        return self.contents[0].name

    def set_name(self, data):
        self.contents[0].name = data

    def get_value(self):
        if self.orgvalue is not None:
            return self.orgvalue
        elif len(self.contents) == 1:
            return self.contents[0].value
        else:
            return '\n'.join([('%s' % x.value) for x in self.contents
                              if not isinstance(x, CommentLine)])

    def set_value(self, data):
        self.orgvalue = data
        lines = ('%s' % data).split('\n')

        # If there is an existing ContinuationLine, use its offset
        value_offset = None
        for v in self.contents:
            if isinstance(v, ContinuationLine):
                value_offset = v.value_offset
                break

        # Rebuild contents list, preserving initial OptionLine
        self.contents = self.contents[0:1]
        self.contents[0].value = lines[0]
        del lines[0]
        for line in lines:
            if line.strip():
                self.add(ContinuationLine(line, value_offset))
            else:
                self.add(EmptyLine())

    name = property(get_name, set_name)
    value = property(get_value, set_value)

    def __str__(self):
        s = [x.__str__() for x in self.contents]
        return '\n'.join(s)

    def finditer(self, key):
        for x in self.contents[::-1]:
            if hasattr(x, 'name') and x.name==key:
                yield x

    def find(self, key):
        for x in self.finditer(key):
            return x
        raise KeyError(key)


def _make_xform_property(myattrname, srcattrname=None):
    private_attrname = myattrname + 'value'
    private_srcname = myattrname + 'source'
    if srcattrname is None:
        srcattrname = myattrname

    def getfn(self):
        srcobj = getattr(self, private_srcname)
        if srcobj is not None:
            return getattr(srcobj, srcattrname)
        else:
            return getattr(self, private_attrname)

    def setfn(self, value):
        srcobj = getattr(self, private_srcname)
        if srcobj is not None:
            setattr(srcobj, srcattrname, value)
        else:
            setattr(self, private_attrname, value)

    return property(getfn, setfn)


class INISection(config.ConfigNamespace):
    _lines = None
    _options = None
    _defaults = None
    _optionxformvalue = None
    _optionxformsource = None
    _compat_skip_empty_lines = set()
    def __init__(self, lineobj, defaults = None,
                       optionxformvalue=None, optionxformsource=None):
        self._lines = [lineobj]
        self._defaults = defaults
        self._optionxformvalue = optionxformvalue
        self._optionxformsource = optionxformsource
        self._options = {}

    _optionxform = _make_xform_property('_optionxform')

    def _compat_get(self, key):
        # identical to __getitem__ except that _compat_XXX
        # is checked for backward-compatible handling
        if key == '__name__':
            return self._lines[-1].name
        if self._optionxform: key = self._optionxform(key)
        try:
            value = self._options[key].value
            del_empty = key in self._compat_skip_empty_lines
        except KeyError:
            if self._defaults and key in self._defaults._options:
                value = self._defaults._options[key].value
                del_empty = key in self._defaults._compat_skip_empty_lines
            else:
                raise
        if del_empty:
            value = re.sub('\n+', '\n', value)
        return value

    def _getitem(self, key):
        if key == '__name__':
            return self._lines[-1].name
        if self._optionxform: key = self._optionxform(key)
        try:
            return self._options[key].value
        except KeyError:
            if self._defaults and key in self._defaults._options:
                return self._defaults._options[key].value
            else:
                raise

    def __setitem__(self, key, value):
        if self._optionxform: xkey = self._optionxform(key)
        else: xkey = key
        if xkey in self._compat_skip_empty_lines:
            self._compat_skip_empty_lines.remove(xkey)
        if xkey not in self._options:
            # create a dummy object - value may have multiple lines
            obj = LineContainer(OptionLine(key, ''))
            self._lines[-1].add(obj)
            self._options[xkey] = obj
        # the set_value() function in LineContainer
        # automatically handles multi-line values
        self._options[xkey].value = value

    def __delitem__(self, key):
        if self._optionxform: key = self._optionxform(key)
        if key in self._compat_skip_empty_lines:
            self._compat_skip_empty_lines.remove(key)
        for l in self._lines:
            remaining = []
            for o in l.contents:
                if isinstance(o, LineContainer):
                    n = o.name
                    if self._optionxform: n = self._optionxform(n)
                    if key != n: remaining.append(o)
                else:
                    remaining.append(o)
            l.contents = remaining
        del self._options[key]

    def __iter__(self):
        d = set()
        for l in self._lines:
            for x in l.contents:
                if isinstance(x, LineContainer):
                    if self._optionxform:
                        ans = self._optionxform(x.name)
                    else:
                        ans = x.name
                    if ans not in d:
                        yield ans
                        d.add(ans)
        if self._defaults:
            for x in self._defaults:
                if x not in d:
                    yield x
                    d.add(x)

    def _new_namespace(self, name):
        raise Exception('No sub-sections allowed', name)


def make_comment(line):
    return CommentLine(line.rstrip('\n'))


def readline_iterator(f):
    """iterate over a file by only using the file object's readline method"""

    have_newline = False
    while True:
        line = f.readline()

        if not line:
            if have_newline:
                yield ""
            return

        if line.endswith('\n'):
            have_newline = True
        else:
            have_newline = False

        yield line


def lower(x):
    return x.lower()


class INIConfig(config.ConfigNamespace):
    _data = None
    _sections = None
    _defaults = None
    _optionxformvalue = None
    _optionxformsource = None
    _sectionxformvalue = None
    _sectionxformsource = None
    _parse_exc = None
    _bom = False
    def __init__(self, fp=None, defaults=None, parse_exc=True,
                 optionxformvalue=lower, optionxformsource=None,
                 sectionxformvalue=None, sectionxformsource=None):
        self._data = LineContainer()
        self._parse_exc = parse_exc
        self._optionxformvalue = optionxformvalue
        self._optionxformsource = optionxformsource
        self._sectionxformvalue = sectionxformvalue
        self._sectionxformsource = sectionxformsource
        self._sections = {}
        if defaults is None: defaults = {}
        self._defaults = INISection(LineContainer(), optionxformsource=self)
        for name, value in defaults.items():
            self._defaults[name] = value
        if fp is not None:
            self._readfp(fp)

    _optionxform = _make_xform_property('_optionxform', 'optionxform')
    _sectionxform = _make_xform_property('_sectionxform', 'optionxform')

    def _getitem(self, key):
        if key == DEFAULTSECT:
            return self._defaults
        if self._sectionxform: key = self._sectionxform(key)
        return self._sections[key]

    def __setitem__(self, key, value):
        raise Exception('Values must be inside sections', key, value)

    def __delitem__(self, key):
        if self._sectionxform: key = self._sectionxform(key)
        for line in self._sections[key]._lines:
            self._data.contents.remove(line)
        del self._sections[key]

    def __iter__(self):
        d = set()
        d.add(DEFAULTSECT)
        for x in self._data.contents:
            if isinstance(x, LineContainer):
                if x.name not in d:
                    yield x.name
                    d.add(x.name)

    def _new_namespace(self, name):
        if self._data.contents:
            self._data.add(EmptyLine())
        obj = LineContainer(SectionLine(name))
        self._data.add(obj)
        if self._sectionxform: name = self._sectionxform(name)
        if name in self._sections:
            ns = self._sections[name]
            ns._lines.append(obj)
        else:
            ns = INISection(obj, defaults=self._defaults,
                            optionxformsource=self)
            self._sections[name] = ns
        return ns

    def __str__(self):
        if self._bom:
            fmt = '\ufeff%s'
        else:
            fmt = '%s'
        return fmt % self._data.__str__()

    __unicode__ = __str__

    _line_types = [EmptyLine, CommentLine,
                   SectionLine, OptionLine,
                   ContinuationLine]

    def _parse(self, line):
        for linetype in self._line_types:
            lineobj = linetype.parse(line)
            if lineobj:
                return lineobj
        else:
            # can't parse line
            return None

    def _readfp(self, fp):
        cur_section = None
        cur_option = None
        cur_section_name = None
        cur_option_name = None
        pending_lines = []
        pending_empty_lines = False
        try:
            fname = fp.name
        except AttributeError:
            fname = '<???>'
        linecount = 0
        exc = None
        line = None

        for line in readline_iterator(fp):
            # Check for BOM on first line
            if linecount == 0:
                if line[0] == '\ufeff':
                    line = line[1:]
                    self._bom = True

            lineobj = self._parse(line)
            linecount += 1

            if not cur_section and not isinstance(lineobj,
                                (CommentLine, EmptyLine, SectionLine)):
                if self._parse_exc:
                    raise MissingSectionHeaderError(fname, linecount, line)
                else:
                    lineobj = make_comment(line)

            if lineobj is None:
                if self._parse_exc:
                    if exc is None: exc = ParsingError(fname)
                    exc.append(linecount, line)
                lineobj = make_comment(line)

            if isinstance(lineobj, ContinuationLine):
                if cur_option:
                    if pending_lines:
                        cur_option.extend(pending_lines)
                        pending_lines = []
                        if pending_empty_lines:
                            optobj._compat_skip_empty_lines.add(cur_option_name)
                            pending_empty_lines = False
                    cur_option.add(lineobj)
                else:
                    # illegal continuation line - convert to comment
                    if self._parse_exc:
                        if exc is None: exc = ParsingError(fname)
                        exc.append(linecount, line)
                    lineobj = make_comment(line)

            if isinstance(lineobj, OptionLine):
                if pending_lines:
                    cur_section.extend(pending_lines)
                    pending_lines = []
                    pending_empty_lines = False
                cur_option = LineContainer(lineobj)
                cur_section.add(cur_option)
                if self._optionxform:
                    cur_option_name = self._optionxform(cur_option.name)
                else:
                    cur_option_name = cur_option.name
                if cur_section_name == DEFAULTSECT:
                    optobj = self._defaults
                else:
                    optobj = self._sections[cur_section_name]
                optobj._options[cur_option_name] = cur_option

            if isinstance(lineobj, SectionLine):
                self._data.extend(pending_lines)
                pending_lines = []
                pending_empty_lines = False
                cur_section = LineContainer(lineobj)
                self._data.add(cur_section)
                cur_option = None
                cur_option_name = None
                if cur_section.name == DEFAULTSECT:
                    self._defaults._lines.append(cur_section)
                    cur_section_name = DEFAULTSECT
                else:
                    if self._sectionxform:
                        cur_section_name = self._sectionxform(cur_section.name)
                    else:
                        cur_section_name = cur_section.name
                    if cur_section_name not in self._sections:
                        self._sections[cur_section_name] = \
                                INISection(cur_section, defaults=self._defaults,
                                           optionxformsource=self)
                    else:
                        self._sections[cur_section_name]._lines.append(cur_section)

            if isinstance(lineobj, (CommentLine, EmptyLine)):
                pending_lines.append(lineobj)
                if isinstance(lineobj, EmptyLine):
                    pending_empty_lines = True

        self._data.extend(pending_lines)
        if line and line[-1]=='\n':
            self._data.add(EmptyLine())

        if exc:
            raise exc


########NEW FILE########
__FILENAME__ = utils
from reconfigure.parsers.iniparse import compat
from reconfigure.parsers.iniparse.ini import LineContainer, EmptyLine

def tidy(cfg):
    """Clean up blank lines.

    This functions makes the configuration look clean and
    handwritten - consecutive empty lines and empty lines at
    the start of the file are removed, and one is guaranteed
    to be at the end of the file.
    """

    if isinstance(cfg, compat.RawConfigParser):
        cfg = cfg.data
    cont = cfg._data.contents
    i = 1
    while i < len(cont):
        if isinstance(cont[i], LineContainer):
            tidy_section(cont[i])
            i += 1
        elif (isinstance(cont[i-1], EmptyLine) and
              isinstance(cont[i], EmptyLine)):
            del cont[i]
        else:
            i += 1

    # Remove empty first line
    if cont and isinstance(cont[0], EmptyLine):
        del cont[0]

    # Ensure a last line
    if cont and not isinstance(cont[-1], EmptyLine):
        cont.append(EmptyLine())

def tidy_section(lc):
    cont = lc.contents
    i = 1
    while i < len(cont):
        if (isinstance(cont[i-1], EmptyLine) and
            isinstance(cont[i], EmptyLine)):
            del cont[i]
        else:
            i += 1

    # Remove empty first line
    if len(cont) > 1 and isinstance(cont[1], EmptyLine):
        del cont[1]
########NEW FILE########
__FILENAME__ = iptables
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser


class IPTablesParser (BaseParser):
    """
    A parser for ``iptables`` configuration as produced by ``iptables-save``
    """

    def parse(self, content):
        content = filter(None, [x.strip() for x in content.splitlines() if not x.startswith('#')])
        root = RootNode()
        cur_table = None
        chains = {}
        for l in content:
            if l.startswith('*'):
                cur_table = Node(l[1:])
                chains = {}
                root.append(cur_table)
            elif l.startswith(':'):
                name = l[1:].split()[0]
                node = Node(name)
                node.set_property('default', l.split()[1])
                chains[name] = node
                cur_table.append(node)
            else:
                comment = None
                if '#' in l:
                    l, comment = l.split('#')
                    comment = comment.strip()
                tokens = l.split()
                if tokens[0] == '-A':
                    tokens.pop(0)
                    node = Node('append')
                    node.comment = comment
                    chain = tokens.pop(0)
                    chains[chain].append(node)
                    while tokens:
                        token = tokens.pop(0)
                        option = Node('option')
                        option.set_property('negative', token == '!')
                        if token == '!':
                            token = tokens.pop(0)
                        option.set_property('name', token.strip('-'))
                        while tokens and not tokens[0].startswith('-') and tokens[0] != '!':
                            option.append(Node('argument', PropertyNode('value', tokens.pop(0))))
                        node.append(option)

        return root

    def stringify(self, tree):
        data = ''
        for table in tree.children:
            data += '*%s\n' % table.name
            for chain in table.children:
                data += ':%s %s [0:0]\n' % (chain.name, chain.get('default').value)
            for chain in table.children:
                for item in chain.children:
                    if item.name == 'append':
                        data += '-A %s %s%s\n' % (
                            chain.name,
                            ' '.join(
                                ('! ' if o.get('negative').value else '') +
                                ('--' if len(o.get('name').value) > 1 else '-') + o.get('name').value + ' ' +
                                ' '.join(a.get('value').value for a in o.children if a.name == 'argument')
                                for o in item.children
                                if o.name == 'option'
                            ),
                            ' # %s' % item.comment if item.comment else ''
                        )
            data += 'COMMIT\n'
        return data

########NEW FILE########
__FILENAME__ = jsonparser
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser
import json


class JsonParser (BaseParser):
    """
    A parser for JSON files (using ``json`` module)
    """

    def parse(self, content):
        node = RootNode()
        self.load_node_rec(node, json.loads(content))
        return node

    def load_node_rec(self, node, json):
        for k in sorted(json.keys()):
            v = json[k]
            if isinstance(v, dict):
                child = Node(k)
                node.children.append(child)
                self.load_node_rec(child, v)
            else:
                node.children.append(PropertyNode(k, v))

    def stringify(self, tree):
        return json.dumps(self.save_node_rec(tree), indent=4)

    def save_node_rec(self, node):
        r = {}
        for child in node.children:
            if isinstance(child, PropertyNode):
                r[child.name] = child.value
            else:
                r[child.name] = self.save_node_rec(child)
        return r

########NEW FILE########
__FILENAME__ = nginx
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser
import re


class NginxParser (BaseParser):
    """
    A parser for nginx configs
    """

    tokens = [
        (r"[\w_]+\s*?.*?{", lambda s, t: ('section_start', t)),
        (r"[\w_]+?.+?;", lambda s, t: ('option', t)),
        (r"\s", lambda s, t: 'whitespace'),
        (r"$^", lambda s, t: 'newline'),
        (r"\#.*?\n", lambda s, t: ('comment', t)),
        (r"\}", lambda s, t: 'section_end'),
    ]
    token_comment = '#'
    token_section_end = '}'

    def parse(self, content):
        scanner = re.Scanner(self.tokens)
        tokens, remainder = scanner.scan(' '.join(filter(None, content.split(' '))))
        if remainder:
            raise Exception('Invalid tokens: %s' % remainder)

        node = RootNode()
        node.parameter = None
        node_stack = []
        next_comment = None

        while len(tokens) > 0:
            token = tokens[0]
            tokens = tokens[1:]
            if token in ['whitespace', 'newline']:
                continue
            if token == 'section_end':
                node = node_stack.pop()
            if token[0] == 'comment':
                if not next_comment:
                    next_comment = ''
                else:
                    next_comment += '\n'
                next_comment += token[1].strip('#/*').strip()
            if token[0] == 'option':
                if ' ' in token[1] and not token[1][0] in ['"', "'"]:
                    k, v = token[1].split(None, 1)
                else:
                    v = token[1]
                    k = ''
                prop = PropertyNode(k.strip(), v[:-1].strip())
                prop.comment = next_comment
                next_comment = None
                node.children.append(prop)
            if token[0] == 'section_start':
                line = token[1][:-1].strip().split(None, 1) + [None]
                section = Node(line[0])
                section.parameter = line[1]
                section.comment = next_comment
                next_comment = None
                node_stack += [node]
                node.children.append(section)
                node = section

        return node

    def stringify(self, tree):
        return ''.join(self.stringify_rec(node) for node in tree.children)

    def stringify_rec(self, node):
        if isinstance(node, PropertyNode):
            if node.name:
                s = '%s %s;\n' % (node.name, node.value)
            else:
                s = '%s;\n' % (node.value)
        elif isinstance(node, IncludeNode):
            s = 'include %s;\n' % (node.files)
        else:
            result = '\n%s %s {\n' % (node.name, node.parameter or '')
            for child in node.children:
                result += '\n'.join('\t' + x for x in self.stringify_rec(child).splitlines()) + '\n'
            result += self.token_section_end + '\n'
            s = result
        if node.comment:
            s = ''.join(self.token_comment + ' %s\n' % l for l in node.comment.splitlines()) + s
        return s

########NEW FILE########
__FILENAME__ = nsd
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser


class NSDParser (BaseParser):
    """
    A parser for NSD DNS server nsd.conf file
    """

    def parse(self, content):
        lines = content.splitlines()
        root = RootNode()
        last_comment = None
        node = root
        for line in lines:
            line = line.strip()
            if line:
                if line.startswith('#'):
                    c = line.strip('#').strip()
                    if last_comment:
                        last_comment += '\n' + c
                    else:
                        last_comment = c
                    continue

                key, value = line.split(':')
                value = value.strip()
                key = key.strip()
                if key in ['server', 'zone', 'key']:
                    node = Node(key, comment=last_comment)
                    root.append(node)
                else:
                    node.append(PropertyNode(key, value, comment=last_comment))
                last_comment = None
        return root

    def stringify_comment(self, line, comment):
        if comment:
            return ''.join('# %s\n' % x for x in comment.splitlines()) + line
        return line

    def stringify(self, tree):
        r = ''
        for node in tree.children:
            r += self.stringify_comment(node.name + ':', node.comment) + '\n'
            for subnode in node.children:
                l = '%s: %s' % (subnode.name, subnode.value)
                r += self.stringify_comment(l, subnode.comment) + '\n'
            r += '\n'
        return r

########NEW FILE########
__FILENAME__ = shell
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser


class ShellParser (BaseParser):
    """
    A parser for shell scripts with variables
    """

    def __init__(self, *args, **kwargs):
        self.comment = '#'
        self.continuation = '\\'
        BaseParser.__init__(self, *args, **kwargs)

    def parse(self, content):
        rawlines = content.splitlines()
        lines = []
        while rawlines:
            l = rawlines.pop(0).strip()
            while self.continuation and rawlines and l.endswith(self.continuation):
                l = l[:-len(self.continuation)]
                l += rawlines.pop(0)
            lines.append(l)

        root = RootNode()
        last_comment = None
        for line in lines:
            line = line.strip()
            if line:
                if line.startswith(self.comment):
                    c = line.strip(self.comment).strip()
                    if last_comment:
                        last_comment += '\n' + c
                    else:
                        last_comment = c
                    continue
                if len(line) == 0:
                    continue

                name, value = line.split('=', 1)
                comment = None
                if '#' in value:
                    value, comment = value.split('#', 1)
                    last_comment = (last_comment or '') + comment.strip()
                node = PropertyNode(name.strip(), value.strip().strip('"'))
                if last_comment:
                    node.comment = last_comment
                    last_comment = None
                root.append(node)
        return root

    def stringify(self, tree):
        r = ''
        for node in tree.children:
            if node.comment and '\n' in node.comment:
                r += '\n' + ''.join('# %s\n' % x for x in node.comment.splitlines())
            r += '%s = "%s"' % (node.name, node.value)
            if node.comment and not '\n' in node.comment:
                r += ' # %s' % node.comment
            r += '\n'
        return r

########NEW FILE########
__FILENAME__ = squid
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser


class SquidParser (BaseParser):
    """
    A parser for Squid configs
    """

    def parse(self, content):
        lines = filter(None, [x.strip() for x in content.splitlines()])
        root = RootNode()
        last_comment = None
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                c = line.strip('#').strip()
                if last_comment:
                    last_comment += '\n' + c
                else:
                    last_comment = c
                continue
            if len(line) == 0:
                continue
            tokens = line.split()
            node = Node('line', Node('arguments'))
            if last_comment:
                node.comment = last_comment
                last_comment = None

            index = 0
            for token in tokens:
                if token.startswith('#'):
                    node.comment = ' '.join(tokens[tokens.index(token):])[1:].strip()
                    break
                if index == 0:
                    node.set_property('name', token)
                else:
                    node.get('arguments').set_property(str(index), token)
                index += 1
            root.append(node)
        return root

    def stringify(self, tree):
        r = ''
        for node in tree.children:
            if node.comment and '\n' in node.comment:
                r += ''.join('%s %s\n' % ('#', x) for x in node.comment.splitlines())
            r += node.get('name').value + ' ' + ' '.join(x.value for x in node.get('arguments').children)
            if node.comment and not '\n' in node.comment:
                r += ' # %s' % node.comment
            r += '\n'
        return r

########NEW FILE########
__FILENAME__ = ssv
from reconfigure.nodes import *
from reconfigure.parsers import BaseParser


class SSVParser (BaseParser):
    """
    A parser for files containing space-separated value (notably, ``/etc/fstab`` and friends)

    :param separator: separator character, defaults to whitespace
    :param maxsplit: max number of tokens per line, defaults to infinity
    :param comment: character denoting comments
    :param continuation: line continuation character, None to disable
    """

    def __init__(self, separator=None, maxsplit=-1, comment='#', continuation=None, *args, **kwargs):
        self.separator = separator
        self.maxsplit = maxsplit
        self.comment = comment
        self.continuation = continuation
        BaseParser.__init__(self, *args, **kwargs)

    def parse(self, content):
        rawlines = content.splitlines()
        lines = []
        while rawlines:
            l = rawlines.pop(0).strip()
            while self.continuation and rawlines and l.endswith(self.continuation):
                l = l[:-len(self.continuation)]
                l += rawlines.pop(0)
            lines.append(l)
        root = RootNode()
        last_comment = None
        for line in lines:
            line = line.strip()
            if line:
                if line.startswith(self.comment):
                    c = line.strip(self.comment).strip()
                    if last_comment:
                        last_comment += '\n' + c
                    else:
                        last_comment = c
                    continue
                if len(line) == 0:
                    continue
                tokens = line.split(self.separator, self.maxsplit)
                node = Node('line')
                if last_comment:
                    node.comment = last_comment
                    last_comment = None
                for token in tokens:
                    if token.startswith(self.comment):
                        node.comment = ' '.join(tokens[tokens.index(token):])[1:].strip()
                        break
                    node.append(Node(
                        name='token',
                        children=[
                            PropertyNode(name='value', value=token)
                        ]
                    ))
                root.append(node)
        return root

    def stringify(self, tree):
        r = ''
        for node in tree.children:
            if node.comment and '\n' in node.comment:
                r += ''.join('%s %s\n' % (self.comment, x) for x in node.comment.splitlines())
            r += (self.separator or '\t').join(x.get('value').value for x in node.children)
            if node.comment and not '\n' in node.comment:
                r += ' # %s' % node.comment
            r += '\n'
        return r

########NEW FILE########
__FILENAME__ = ajenti_tests
import json

from reconfigure.configs import AjentiConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class AjentiConfigTest (BaseConfigTest):
    sources = {
        None: """{
    "authentication": false,
    "bind": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "language": null,
    "enable_feedback": true,
    "installation_id": null,
    "users": {
        "test": {
            "configs": { "a": "{}" },
            "password": "sha512",
            "permissions": [
                "section:Dash"
            ]
        }
    },
    "ssl": {
        "enable": false,
        "certificate_path": ""
    }
}
"""
    }
    result = {
        'authentication': False,
        'enable_feedback': True,
        'installation_id': None,
        'language': None,
        'http_binding': {'host': '0.0.0.0', 'port': 8000},
        'ssl': {'certificate_path': '', 'enable': False},
        'users': {'test': {
            'configs': {'a': {'data': {}, 'name': 'a'}},
            'email': None,
            'name': 'test',
            'password': 'sha512',
            'permissions': ['section:Dash']
        }}
    }

    config = AjentiConfig

    stringify_filter = staticmethod(lambda x: json.loads(str(x)))


del BaseConfigTest

########NEW FILE########
__FILENAME__ = base_test
import unittest
import json


class BaseConfigTest (unittest.TestCase):
    sources = ""
    result = None
    config = None
    config_kwargs = {}
    stringify_filter = staticmethod(lambda x: x.split())

    def test_config(self):
        if not self.config:
            return

        self.maxDiff = None

        config = self.config(content=self.sources[None], **self.config_kwargs)
        if config.includer:
            config.includer.content_map = self.sources
        config.load()
        #print 'RESULT', config.tree.to_dict()
        #print 'SOURCE', self.__class__.result
        #self.assertTrue(self.__class__.result== config.tree.to_dict())
        a, b = self.__class__.result, config.tree.to_dict()
        if a != b:
            print('SOURCE: %s\nGENERATED: %s\n' % (json.dumps(a, indent=4), json.dumps(b, indent=4)))
        self.assertEquals(a, b)

        result = config.save()
        s_filter = self.__class__.stringify_filter
        #print s_filter(result[None])
        for k, v in result.items():
            self.assertEquals(
                s_filter(self.__class__.sources[k]),
                s_filter(v)
            )

########NEW FILE########
__FILENAME__ = bind9_tests
from reconfigure.configs import BIND9Config
from reconfigure.tests.configs.base_test import BaseConfigTest


class BIND9ConfigTest (BaseConfigTest):
    sources = {
        None: """
zone "asd" {
    type master;
    file "/file";
};

"""
    }
    result = {
        "zones": [
            {
                "type": "master",
                "name": "asd",
                "file": "/file"
            }
        ]
    }

    config = BIND9Config


del BaseConfigTest

########NEW FILE########
__FILENAME__ = crontab_tests
from reconfigure.configs import CrontabConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class CrontabConfigTest (BaseConfigTest):
    sources = {
        None: """#comment line
* * * * * date
@reboot ls -al
1 * 0 1 2 date -s
NAME = TEST"""
    }
    result = {
        'normal_tasks': [
            {
                'minute': '*',
                'hour': '*',
                'day_of_month': '*',
                'month': '*',
                'day_of_week': '*',
                'command': 'date',
                'comment': 'comment line'
            },
            {
                'minute': '1',
                'hour': '*',
                'day_of_month': '0',
                'month': '1',
                'day_of_week': '2',
                'command': 'date -s',
                'comment': None,
            },

        ],
        'special_tasks': [
            {
                'special': '@reboot',
                'command': 'ls -al',
                'comment': None,
            }
        ],
        'env_settings': [
            {
                'name': 'NAME',
                'value': 'TEST',
                'comment': None
            }
        ]
    }
    config = CrontabConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = csf_tests
from reconfigure.configs import CSFConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class CSFConfigTest (BaseConfigTest):
    sources = {
        None: """
TESTING = "1"
TCP_IN = "20,21,22,25,53,80,110,143,443,465,587,993,995"
TCP_OUT = "20,21,22,25,53,80,110,113,443"
UDP_IN = "20,21,53"
UDP_OUT = "20,21,53,113,123"
IPV6 = "0"
TCP6_IN = "20,21,22,25,53,80,110,143,443,465,587,993,995"
TCP6_OUT = "20,21,22,25,53,80,110,113,443"
UDP6_IN = "20,21,53"
UDP6_OUT = "20,21,53,113,123"
ETH_DEVICE = ""
ETH6_DEVICE = ""
"""
    }
    result = {
        "tcp6_out": "20,21,22,25,53,80,110,113,443",
        "testing": True,
        "eth_device": "",
        "tcp_in": "20,21,22,25,53,80,110,143,443,465,587,993,995",
        "tcp6_in": "20,21,22,25,53,80,110,143,443,465,587,993,995",
        "udp6_in": "20,21,53",
        "tcp_out": "20,21,22,25,53,80,110,113,443",
        "udp6_out": "20,21,53,113,123",
        "ipv6": False,
        "udp_in": "20,21,53",
        "eth6_device": "",
        "udp_out": "20,21,53,113,123"
    }

    config = CSFConfig

########NEW FILE########
__FILENAME__ = ctdb_tests
from reconfigure.configs import CTDBConfig, CTDBNodesConfig, CTDBPublicAddressesConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class CTDBNodesConfigTest (BaseConfigTest):
    sources = {
        None: """10.10.1.1
10.10.1.2
"""
    }
    result = {
        'nodes': [
            {
                'address': '10.10.1.1',
            },
            {
                'address': '10.10.1.2',
            },
        ]
    }
    config = CTDBNodesConfig


class CTDBPublicAddressesConfigTest (BaseConfigTest):
    sources = {
        None: """10.10.1.1 eth0
10.10.1.2 eth1
"""
    }
    result = {
        'addresses': [
            {
                'address': '10.10.1.1',
                'interface': 'eth0',
            },
            {
                'address': '10.10.1.2',
                'interface': 'eth1',
            },
        ]
    }
    config = CTDBPublicAddressesConfig


class CTDBConfigTest (BaseConfigTest):
    sources = {
        None: """CTDB_RECOVERY_LOCK="/dadoscluster/ctdb/storage"
CTDB_PUBLIC_INTERFACE=eth0
CTDB_PUBLIC_ADDRESSES=/etc/ctdb/public_addresses
CTDB_MANAGES_SAMBA=yes
CTDB_NODES=/etc/ctdb/nodes
CTDB_LOGFILE=/var/log/log.ctdb
CTDB_DEBUGLEVEL=2
CTDB_PUBLIC_NETWORK="10.0.0.0/24"
CTDB_PUBLIC_GATEWAY="10.0.0.9"
"""
    }
    result = {
        "recovery_lock_file": "\"/dadoscluster/ctdb/storage\"",
        "public_interface": "eth0",
        "public_addresses_file": "/etc/ctdb/public_addresses",
        "nodes_file": "/etc/ctdb/nodes",
        "debug_level": "2",
        "public_gateway": "\"10.0.0.9\"",
        "public_network": "\"10.0.0.0/24\"",
        "log_file": "/var/log/log.ctdb",
        "manages_samba": True
    }

    config = CTDBConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = dhcpd_tests
from reconfigure.configs import DHCPDConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class DHCPDConfigTest (BaseConfigTest):
    sources = {
        None: """
default-lease-time 600;
max-lease-time 7200;

 subnet 10.17.224.0 netmask 255.255.255.0 {
    option routers rtr-224.example.org;
    range 10.0.29.10 10.0.29.230;
  }
shared-network 224-29 {
  subnet 10.17.224.0 netmask 255.255.255.0 {
    option routers rtr-224.example.org;
  }
  pool {
    deny members of "foo";
    range 10.0.29.10 10.0.29.230;
  }
}

"""
    }
    result = {
        "subnets": [
            {
                "ranges": [
                    {
                        "range": "10.0.29.10 10.0.29.230"
                    }
                ],
                "subnets": [],
                "name": "10.17.224.0 netmask 255.255.255.0",
                "options": [
                    {
                        "value": "routers rtr-224.example.org"
                    }
                ]
            }
        ],
        "options": []
    }

    config = DHCPDConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = exports_tests
from reconfigure.configs import ExportsConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class ExportsConfigTest (BaseConfigTest):
    sources = {
        None: """
/another/exported/directory 192.168.0.3(rw,sync) \
192.168.0.4(ro) # test
/one 192.168.0.1 # comment
"""
    }
    result = {
        "exports": [
            {
                "comment": "test",
                "name": '/another/exported/directory',
                "clients": [
                    {
                        "name": "192.168.0.3",
                        "options": "rw,sync"
                    },
                    {
                        "name": "192.168.0.4",
                        "options": "ro"
                    }
                ]
            },
            {
                "comment": "comment",
                "name": '/one',
                "clients": [
                    {
                        "name": "192.168.0.1",
                        "options": ""
                    }
                ]
            }
        ]
    }

    config = ExportsConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = fstab_tests
from reconfigure.configs import FSTabConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class FSTabConfigTest (BaseConfigTest):
    sources = {
        None: """fs1\tmp1\text\trw\t1\t2
fs2\tmp2\tauto\tnone\t0\t0
"""
    }
    result = {
        'filesystems': [
            {
                'device': 'fs1',
                'mountpoint': 'mp1',
                'type': 'ext',
                'options': 'rw',
                'freq': '1',
                'passno': '2'
            },
            {
                'device': 'fs2',
                'mountpoint': 'mp2',
                'type': 'auto',
                'options': 'none',
                'freq': '0',
                'passno': '0'
            },
        ]
    }
    config = FSTabConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = group_tests
from reconfigure.configs import GroupConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class GroupConfigTest (BaseConfigTest):
    sources = {
        None: """sys:x:3:
adm:x:4:eugeny
"""
    }
    result = {
        'groups': [
            {
                'name': 'sys',
                'password': 'x',
                'gid': '3',
                'users': '',
            },
            {
                'name': 'adm',
                'password': 'x',
                'gid': '4',
                'users': 'eugeny',
            },
        ]
    }
    config = GroupConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = hosts_tests
from reconfigure.configs import HostsConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class FSTabConfigTest (BaseConfigTest):
    sources = {
        None: """a1 h1 a2 a3 a4
a5 h2
a6 h3 a7
"""
    }
    result = {
        'hosts': [
            {
                'address': 'a1',
                'name': 'h1',
                'aliases': [
                    {'name': 'a2'},
                    {'name': 'a3'},
                    {'name': 'a4'},
                ]
            },
            {
                'address': 'a5',
                'aliases': [],
                'name': 'h2',
            },
            {
                'address': 'a6',
                'name': 'h3',
                'aliases': [
                    {'name': 'a7'},
                ]
            },
        ]
    }
    config = HostsConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = iptables_tests
from reconfigure.configs import IPTablesConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class IPTablesConfigTest (BaseConfigTest):
    sources = {
        None: '''*filter
:INPUT ACCEPT [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT ! -s 202.54.1.2/32 -j DROP
-A INPUT -m state --state NEW,ESTABLISHED -j ACCEPT # test
COMMIT
'''
    }
    result = {
        'tables': [
            {
                'chains': [
                    {
                        'default': 'ACCEPT',
                        'rules': [
                            {
                                'options': [
                                    {
                                        'arguments': [
                                            {
                                                'value': '202.54.1.2/32'
                                            }
                                        ],
                                        'negative': True,
                                        'name': 's'
                                    },
                                    {
                                        'arguments': [
                                            {
                                                'value': 'DROP'
                                            }
                                        ],
                                        'negative': False,
                                        'name': 'j'
                                    }
                                ],
                                'comment': None,
                            },
                            {
                                'options': [
                                    {
                                        'arguments': [
                                            {
                                                'value': 'state'
                                            }
                                        ],
                                        'negative': False,
                                        'name': 'm'
                                    },
                                    {
                                        'arguments': [
                                            {
                                                'value': 'NEW,ESTABLISHED'
                                            }
                                        ],
                                        'negative': False,
                                        'name': 'state'
                                    },
                                    {
                                        'arguments': [
                                            {
                                                'value': 'ACCEPT'
                                            }
                                        ],
                                        'negative': False,
                                        'name': 'j'
                                    }
                                ],
                                'comment': 'test',
                            }
                        ],
                        'name': 'INPUT'
                    },
                    {
                        'default': 'DROP',
                        'rules': [],
                        'name': 'FORWARD'
                    },
                    {
                        'default': 'ACCEPT',
                        'rules': [],
                        'name': 'OUTPUT'
                    }
                ],
                'name': 'filter'
            }
        ]
    }

    config = IPTablesConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = netatalk_tests
from reconfigure.configs import NetatalkConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class NetatalkConfigTest (BaseConfigTest):
    sources = {
        None: """
[Global]
afp port=123

[test]
path=/home ;comment
valid users=root
ea=sys
"""
    }

    result = {
        "global": {
            "zeroconf": True,
            "cnid_listen": "localhost:4700",
            "uam_list": 'uams_dhx.so,uams_dhx2.so',
            "afp_port": "123",
        },
        "shares": [
            {
                "comment": "comment",
                "appledouble": "ea",
                "name": "test",
                "ea": "sys",
                "valid_users": "root",
                "cnid_scheme": "dbd",
                "path": "/home",
                "password": '',
            }
        ]
    }

    config = NetatalkConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = nsd_tests
from reconfigure.configs import NSDConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class NSDConfigTest (BaseConfigTest):
    sources = {
        None: """
zone:
        name: "example.net"
        zonefile: "example.net.signed.zone"
        notify-retry: 5
"""
    }
    result = {
        "zones": [
            {
                "name": "example.net",
                "file": "example.net.signed.zone"
            }
        ]
    }

    config = NSDConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = passwd_tests
from reconfigure.configs import PasswdConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class PasswdConfigTest (BaseConfigTest):
    sources = {
        None: """backup:x:34:34:backup:/var/backups:/bin/sh
list:x:38:38:Mailing List Manager:/var/list:/bin/sh
"""
    }
    result = {
        'users': [
            {
                'name': 'backup',
                'password': 'x',
                'uid': '34',
                'gid': '34',
                'comment': 'backup',
                'home': '/var/backups',
                'shell': '/bin/sh'
            },
            {
                'name': 'list',
                'password': 'x',
                'uid': '38',
                'gid': '38',
                'comment': 'Mailing List Manager',
                'home': '/var/list',
                'shell': '/bin/sh'
            },
        ]
    }
    config = PasswdConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = resolv_tests
from reconfigure.configs import ResolvConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class ResolvConfigTest (BaseConfigTest):
    sources = {
        None: """nameserver 1
domain 2
search 3 5
"""
    }
    result = {
        'items': [
            {
                'name': 'nameserver',
                'value': '1',
            },
            {
                'name': 'domain',
                'value': '2',
            },
            {
                'name': 'search',
                'value': '3 5',
            },
        ]
    }
    config = ResolvConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = samba_tests
from reconfigure.configs import SambaConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class SambaConfigTest (BaseConfigTest):
    sources = {
        None: """
[global]
workgroup=WORKGROUP
server string=%h server (Samba, Ubuntu)
interfaces=127.0.0.0/8 eth0
bind interfaces only=yes
log file=/var/log/samba/log.%m
security=user

[homes]
comment=Home Directories
browseable=no

[profiles]
comment=Users profiles
path=/home/samba/profiles
guest ok=no
browseable=no
create mask=0600
directory mask=0700
"""
    }

    result = {
        "global": {
            "server_string": "%h server (Samba, Ubuntu)",
            "workgroup": "WORKGROUP",
            "interfaces": "127.0.0.0/8 eth0",
            "bind_interfaces_only": True,
            "security": "user",
            "log_file": "/var/log/samba/log.%m"
        },
        "shares": [
            {
                "name": "homes",
                "comment": "Home Directories",
                "browseable": False,
                "create_mask": "0744",
                "directory_mask": "0755",
                'follow_symlinks': True,
                "read_only": True,
                "guest_ok": False,
                "path": "",
                'wide_links': False,
                "fstype": "",
                "force_create_mode": "000",
                "force_directory_mode": "000",
                "veto_files": "",
                "write_list": "",
                "dfree_command": "",
                "force_group": "",
                "force_user": "",
                "valid_users": "",
                "read_list": "",
                "dfree_cache_time": "",
            },
            {
                "name": "profiles",
                "comment": "Users profiles",
                "browseable": False,
                "create_mask": "0600",
                "directory_mask": "0700",
                'follow_symlinks': True,
                "read_only": True,
                "guest_ok": False,
                "path": "/home/samba/profiles",
                'wide_links': False,
                "fstype": "",
                "force_create_mode": "000",
                "force_directory_mode": "000",
                "veto_files": "",
                "write_list": "",
                "dfree_command": "",
                "force_group": "",
                "force_user": "",
                "valid_users": "",
                "read_list": "",
                "dfree_cache_time": "",
            }
        ]
    }

    config = SambaConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = squid_tests
from reconfigure.configs import SquidConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class SquidConfigTest (BaseConfigTest):
    sources = {
        None: """acl manager proto cache_object
acl SSL_ports port 443
http_access deny CONNECT !SSL_ports
http_port 3128
"""
    }
    result = {
       "http_access": [
            {
                "mode": "deny",
                "options": [
                    {
                        "value": "CONNECT"
                    },
                    {
                        "value": "!SSL_ports"
                    }
                ]
            }
        ],
        "http_port": [
            {
                "options": [],
                "port": "3128"
            }
        ],
        "https_port": [],
        "acl": [
            {
                "name": "manager",
                "options": [
                    {
                        "value": "proto"
                    },
                    {
                        "value": "cache_object"
                    }
                ]
            },
            {
                "name": "SSL_ports",
                "options": [
                    {
                        "value": "port"
                    },
                    {
                        "value": "443"
                    }
                ]
            }
        ]
    }

    config = SquidConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = supervisor_tests
from reconfigure.configs import SupervisorConfig
from reconfigure.tests.configs.base_test import BaseConfigTest


class SupervisorConfigTest (BaseConfigTest):
    sources = {
        None: """[unix_http_server]
file=/var/run//supervisor.sock ;comment
chmod=0700
[include]
files=test""",
        'test': """[program:test1]
command=cat
        """
    }
    result = {
        "programs": [
            {
                "comment": None,
                "autorestart": None,
                "name": "test1",
                "startsecs": None,
                "umask": None,
                "environment": None,
                "command": "cat",
                "user": None,
                "startretries": None,
                "directory": None,
                "autostart": None
            }
        ]
    }

    config = SupervisorConfig


del BaseConfigTest

########NEW FILE########
__FILENAME__ = nginx_tests
#coding: utf8
import unittest
from reconfigure.parsers import NginxParser
from reconfigure.includers import NginxIncluder


class IncludersTest (unittest.TestCase):
    def test_compose_decompose(self):
        content = """
            sec1 {
                p1 1;
                include test;
            }
        """
        content2 = """
            sec2 {
                p2 2;
            }
        """

        parser = NginxParser()
        includer = NginxIncluder(parser=parser, content_map={'test': content2})
        tree = parser.parse(content)
        tree = includer.compose(None, tree)
        self.assertTrue(len(tree.children[0].children) == 3)

        treemap = includer.decompose(tree)
        self.assertTrue(len(treemap.keys()) == 2)
        self.assertTrue(treemap['test'].children[0].name == 'sec2')

########NEW FILE########
__FILENAME__ = base_test
import unittest


class BaseParserTest (unittest.TestCase):
    source = ""
    parsed = None
    parser = None

    @property
    def stringified(self):
        return self.source

    def test_parse(self):
        if not self.__class__.parser:
            return

        nodetree = self.parser.parse(self.__class__.source)
        if self.__class__.parsed != nodetree:
            print('TARGET: %s\n\nPARSED: %s' % (self.__class__.parsed, nodetree))
        self.assertEquals(self.__class__.parsed, nodetree)

    def test_stringify(self):
        if not self.__class__.parser:
            return

        unparsed = self.parser.stringify(self.__class__.parsed)
        a, b = self.stringified, unparsed
        if a.split() != b.split():
            print('SOURCE: %s\n\nGENERATED: %s' % (a, b))
            self.assertEquals(a.split(), b.split())

########NEW FILE########
__FILENAME__ = bind9_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import BIND9Parser
from reconfigure.nodes import *


class BIND9ParserTest (BaseParserTest):
    parser = BIND9Parser()
    source = """p1 asd;

sec {
    s1p1 asd;
    /*s1p2 wqe;*/

    sec2 test {
        ::1;
        s2p1 qwe;
    };
};
"""

    @property
    def stringified(self):
        return """
  p1 asd;

sec {
    s1p1 asd;

    # s1p2 wqe;
    sec2 test {
        ::1;
        s2p1 qwe;
    };
};
"""

    parsed = RootNode(
        None,
        PropertyNode('p1', 'asd'),
        Node(
            'sec',
            PropertyNode('s1p1', 'asd'),
            Node(
                'sec2',
                PropertyNode('', '::1'),
                PropertyNode('s2p1', 'qwe'),
                parameter='test',
                comment='s1p2 wqe;',
            ),
            parameter=None,
        )
    )


del BaseParserTest

########NEW FILE########
__FILENAME__ = crontab_tests
from reconfigure.parsers import CrontabParser
from reconfigure.nodes import RootNode, Node, PropertyNode
from reconfigure.tests.parsers.base_test import BaseParserTest


class CrontabParserTest (BaseParserTest):
    parser = CrontabParser()

    source = '\n'.join(['#comment line',
                    '* * * * * date',
                    '@reboot ls -al',
                    '1 * 0 1 2 date -s',
                    'NAME = TEST',
                    ])
    parsed = RootNode(None,
            children=[
                Node('normal_task',
                    comment='comment line',
                    children=[
                        PropertyNode('minute', '*'),
                        PropertyNode('hour', '*'),
                        PropertyNode('day_of_month', '*'),
                        PropertyNode('month', '*'),
                        PropertyNode('day_of_week', '*'),
                        PropertyNode('command', 'date'),
                    ]
                ),
                Node('special_task',
                    children=[
                        PropertyNode('special', '@reboot'),
                        PropertyNode('command', 'ls -al'),
                    ]
                ),
                Node('normal_task',
                    children=[
                        PropertyNode('minute', '1'),
                        PropertyNode('hour', '*'),
                        PropertyNode('day_of_month', '0'),
                        PropertyNode('month', '1'),
                        PropertyNode('day_of_week', '2'),
                        PropertyNode('command', 'date -s'),
                    ]
                ),
                Node('env_setting',
                    children=[
                        PropertyNode('name', 'NAME'),
                        PropertyNode('value', 'TEST'),
                    ]
                ),
            ]
        )
#    bad_source = '\n'.join(['* * * * dd',   #Wrong line
#                        ' = FAIL',      #wrong line
#    ])


del BaseParserTest

########NEW FILE########
__FILENAME__ = exports_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import ExportsParser
from reconfigure.nodes import *


class ExportsParserTest (BaseParserTest):
    parser = ExportsParser()
    source = """
/another/exported/directory 192.168.0.3(rw,sync) \
192.168.0.4(ro)
# comment
/one 192.168.0.1
"""
    parsed = RootNode(
        None,
        Node(
            '/another/exported/directory',
            Node(
                'clients',
                Node(
                    '192.168.0.3',
                    PropertyNode('options', 'rw,sync')
                ),
                Node(
                    '192.168.0.4',
                    PropertyNode('options', 'ro')
                ),
            ),
        ),
        Node(
            '/one',
            Node(
                'clients',
                Node(
                    '192.168.0.1',
                    PropertyNode('options', '')
                ),
            ),
            comment='comment'
        )
    )

    @property
    def stringified(self):
        return """/another/exported/directory\t192.168.0.3(rw,sync)\t192.168.0.4(ro)
/one\t192.168.0.1\t# comment
"""


del BaseParserTest

########NEW FILE########
__FILENAME__ = ini_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import IniFileParser
from reconfigure.nodes import *


class IniParserTest (BaseParserTest):
    parser = IniFileParser(sectionless=True)
    source = """a=b

[section1] ;section comment
s1p1=asd ;comment 2
s1p2=123
"""
    parsed = RootNode(None,
        Node(None,
            PropertyNode('a',  'b'),
        ),
        Node('section1',
            PropertyNode('s1p1', 'asd', comment='comment 2'),
            PropertyNode('s1p2', '123'),
            comment='section comment'
        ),
    )


del BaseParserTest

########NEW FILE########
__FILENAME__ = iptables_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import IPTablesParser
from reconfigure.nodes import *


class IPTablesParserTest (BaseParserTest):
    parser = IPTablesParser()
    source = """*filter
:INPUT ACCEPT [0:0] 
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT ! -s 202.54.1.2/32 -j DROP # test
-A INPUT -m state --state NEW,ESTABLISHED -j ACCEPT
COMMIT
"""
    parsed = RootNode(None,
        Node('filter',
            Node('INPUT',
                PropertyNode('default', 'ACCEPT'),
                Node('append',
                    Node('option',
                        Node('argument', PropertyNode('value', '202.54.1.2/32')),
                        PropertyNode('negative', True),
                        PropertyNode('name', 's')
                    ),
                    Node('option',
                        Node('argument', PropertyNode('value', 'DROP')),
                        PropertyNode('negative', False),
                        PropertyNode('name', 'j')
                    ),
                    comment='test'
                ),
                Node('append',
                    Node('option',
                        Node('argument', PropertyNode('value', 'state')),
                        PropertyNode('negative', False),
                        PropertyNode('name', 'm')
                    ),
                    Node('option',
                        Node('argument', PropertyNode('value', 'NEW,ESTABLISHED')),
                        PropertyNode('negative', False),
                        PropertyNode('name', 'state')
                    ),
                    Node('option',
                        Node('argument', PropertyNode('value', 'ACCEPT')),
                        PropertyNode('negative', False),
                        PropertyNode('name', 'j')
                    ),
                ),
            ),
            Node('FORWARD',
                PropertyNode('default', 'DROP'),
            ),
            Node('OUTPUT',
                PropertyNode('default', 'ACCEPT'),
            ),
        )
    )


del BaseParserTest

########NEW FILE########
__FILENAME__ = jsonparser_tests
import json
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import JsonParser
from reconfigure.nodes import *


class JsonParserTest (BaseParserTest):
    parser = JsonParser()
    source = """{
    "p2": 123,
    "s1": {
        "s1p1": "qwerty"
    }
}
"""

    parsed = RootNode(None,
        PropertyNode('p2',  123),
        Node('s1',
            PropertyNode('s1p1',  'qwerty'),
        ),
    )

    def test_stringify(self):
        unparsed = self.parser.stringify(self.__class__.parsed)
        a, b = self.stringified, unparsed
        if json.loads(a) != json.loads(b):
            print('SOURCE: %s\n\nGENERATED: %s' % (a, b))
            self.assertEquals(a, b)

del BaseParserTest

########NEW FILE########
__FILENAME__ = nginx_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import NginxParser
from reconfigure.nodes import *


class NginxParserTest (BaseParserTest):
    parser = NginxParser()
    source = """p1 asd;

sec {
    s1p1 asd;
    s1p2 wqe;

    # test
    sec2 test { s2p1 qwe; }
}
"""
    parsed = RootNode(
        None,
        PropertyNode('p1', 'asd'),
        Node(
            'sec',
            PropertyNode('s1p1', 'asd'),
            PropertyNode('s1p2', 'wqe'),
            Node(
                'sec2',
                PropertyNode('s2p1', 'qwe'),
                parameter='test',
                comment='test',
            ),
            parameter=None,
        )
    )


del BaseParserTest

########NEW FILE########
__FILENAME__ = nsd_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import NSDParser
from reconfigure.nodes import *


class BIND9ParserTest (BaseParserTest):
    parser = NSDParser()
    source = """# asd
    server:
        ip4-only: no
key:
        name: "mskey"
"""

    parsed = RootNode(
        None,
        Node(
            'server',
            PropertyNode('ip4-only', 'no'),
            comment='asd'
        ),
        Node(
            'key',
            PropertyNode('name', '"mskey"'),
        )
    )


del BaseParserTest

########NEW FILE########
__FILENAME__ = shell_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import ShellParser
from reconfigure.nodes import *


class ShellParserTest (BaseParserTest):
    parser = ShellParser()
    source = """
# The following
# otherwise they
PORTS_pop3d = "110,995"
PORTS_htpasswd = "80,443" # b
"""
    parsed = RootNode(
        None,
        PropertyNode('PORTS_pop3d', '110,995', comment='The following\notherwise they'),
        PropertyNode('PORTS_htpasswd', '80,443', comment='b'),
    )

del BaseParserTest

########NEW FILE########
__FILENAME__ = squid_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import SquidParser
from reconfigure.nodes import *


class SquidParserTest (BaseParserTest):
    parser = SquidParser()
    source = """# line1
# long comment
a\tbc
efgh # line2
"""
    parsed = RootNode(None,
        Node('line',
            PropertyNode('name',  'a'),
            Node('arguments',
                PropertyNode('1',  'bc'),
            ),
            comment='line1\nlong comment',
        ),
        Node('line',
            PropertyNode('name',  'efgh'),
            Node('arguments'),
            comment='line2',
        ),
    )


del BaseParserTest

########NEW FILE########
__FILENAME__ = ssv_tests
from reconfigure.tests.parsers.base_test import BaseParserTest
from reconfigure.parsers import SSVParser
from reconfigure.nodes import *


class SSVParserTest (BaseParserTest):
    parser = SSVParser(continuation='\\')
    source = """# line1
# long comment
a\tbc\\
\tdef
efgh # line2
"""
    parsed = RootNode(
        None,
        Node(
            'line',
            Node('token', PropertyNode('value',  'a')),
            Node('token', PropertyNode('value',  'bc')),
            Node('token', PropertyNode('value',  'def')),
            comment='line1\nlong comment',
        ),
        Node(
            'line',
            Node('token', PropertyNode('value',  'efgh')),
            comment='line2',
        ),
    )

    @property
    def stringified(self):
        return """# line1
# long comment
a\tbc\tdef
efgh # line2
"""


del BaseParserTest

########NEW FILE########
