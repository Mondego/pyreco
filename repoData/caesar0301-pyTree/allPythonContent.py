__FILENAME__ = family_tree
#!/usr/bin/env python
# Example usage of treelib
#
# Author: chenxm
#
__author__ = 'chenxm'

from treelib import Tree, Node

## Create the family tree
tree = Tree()
tree.create_node("Harry", "harry")  # root node
tree.create_node("Jane", "jane", parent="harry")
tree.create_node("Bill", "bill", parent="harry")
tree.create_node("Diane", "diane", parent="jane")
tree.create_node("George", "george", parent="diane")
tree.create_node("Mary", "mary", parent="diane")
tree.create_node("Jill", "jill", parent="george")
tree.create_node("Mark", "mark", parent="jane")

sep = "-"*20 + '\n'

print(sep + "Tree of the whole family:")
tree.show(key=lambda x: x.tag, reverse=True)

print(sep + "All family members in DEPTH mode:")
for node in tree.expand_tree(mode=Tree.DEPTH):
    print(tree[node].tag)

print(sep + "All family members without Diane sub-family:")
tree.show(idhidden=False, filter=lambda x: x.identifier != 'diane')
# for node in tree.expand_tree(filter=lambda x: x.identifier != 'diane', mode=Tree.DEPTH):
#     print tree[node].tag

print(sep + "Let me introduce Diane family only:")
sub_t = tree.subtree('diane')
sub_t.show()

print(sep + "Children of Diane")
for child in tree.is_branch('diane'):
	print(tree[child].tag)

print(sep + "OOhh~ new members join Jill's family:")
new_tree = Tree()
new_tree.create_node("n1", 1)  # root node
new_tree.create_node("n2", 2, parent=1)
new_tree.create_node("n3", 3, parent=1)
tree.paste('jill', new_tree)
tree.show()

print(sep + "They leave after a while:")
tree.remove_node(1)
tree.show()

print(sep + "Now Jill moves to live with Grand-x-father Harry:")
tree.move_node('jill', 'harry')
tree.show()

print(sep + "A big family for George to send message to the oldest Harry:")
for node in tree.rsearch('george'):
    print(tree[node].tag)
########NEW FILE########
__FILENAME__ = folder_tree
#!/usr/bin/env python
# A file folder scanner contributed by @holger 
#
# You can spicify the scanned folder and file pattern by changing rootPath
# and pattern variables
#

__author__ = 'holger'

from treelib import tree

import fnmatch
import os
import zlib
import argparse

DEBUG = 0
FILECOUNT = 0
DIRCOUNT = 0
DIR_ERRORLIST = []
FILE_ERRORLIST = []


# Time Profiling
PROFILING = 0
# 0 - nothing
# 1 - time
# 2 - cProfile

if PROFILING == 1:
    import timeit
if PROFILING == 2:
    import cProfile


parser = argparse.ArgumentParser(description='Scan the given folder and print its structure in a tree.')
parser.add_argument('abspath', type=str, help= 'An absolute path to be scanned.')
parser.add_argument('pattern', type=str, help= 'File name pattern to filtered, e.g. *.pdf')

args = parser.parse_args()
rootPath = args.abspath
pattern = args.pattern

folder_blacklist = []

dir_tree = tree.Tree()
dir_tree.create_node('Root', rootPath)  # root node


def crc32(data):
    data = bytes(data, 'UTF-8')

    if DEBUG:
        print('++++++ CRC32 ++++++')
        print('input: ' + str(data))
        print('crc32: ' + hex(zlib.crc32(data) & 0xffffffff))
        print('+++++++++++++++++++')
    return hex(zlib.crc32(data) & 0xffffffff)  # crc32 returns a signed value, &-ing it will match py3k

parent = rootPath
i = 1

# calculating start depth
start_depth = rootPath.count('/')


def get_noteid(depth, root, dir):
    """ get_noteid returns
        - depth contains the current depth of the folder hierarchy
        - dir contains the current directory

        Function returns a string containing the current depth, the folder name and unique ID build by hashing the
        absolute path of the directory. All spaces are replaced by '_'

        <depth>_<dirname>+++<crc32>
        e.g. 2_Folder_XYZ_1+++<crc32>
    """
    return str(str(depth) + '_' + dir).replace(" ", "_") + '+++' + crc32(os.path.join(root, dir))

# TODO: Verzeichnistiefe pruefen: Was ist mit sowas /mp3/


def get_parentid(current_depth, root, dir):
    # special case for the 'root' of the tree
    # because we don't want a cryptic root-name
    if current_depth == 0:
        return root

    # looking for parent directory
    # e.g. /home/user1/mp3/folder1/parent_folder/current_folder
    # get 'parent_folder'

    search_string = os.path.join(root, dir)
    pos2 = search_string.rfind('/')
    pos1 = search_string.rfind('/', 0, pos2)
    parent_dir = search_string[pos1 + 1:pos2]
    parentid = str(current_depth - 1) + '_' + parent_dir.replace(" ", "_") + '+++' + crc32(root)
    return parentid
    # TODO: catch error



def print_node(dir, node_id, parent_id):
    print('#############################')
    print('node created')
    print('      dir:     ' + dir)
    print('      note_id: ' + node_id)
    print('      parent:  ' + parent_id)


def crawler():
    global DIRCOUNT
    global FILECOUNT

    for root, dirs, files in os.walk(rootPath):

        # +++ DIRECTORIES +++
        for dir in dirs:

            # calculating current depth
            current_depth = os.path.join(root, dir).count('/') - start_depth

            if DEBUG:
                print('current: ' + os.path.join(root, dir))

            node_id = get_noteid(current_depth, root, dir)
            parent_id = str(get_parentid(current_depth, root, dir))

            if parent_id == str(None):
                DIR_ERRORLIST.append(os.path.join(root, dir))

            if DEBUG:
                print_node(dir, node_id, parent_id)

            # create node
            dir_tree.create_node(dir, node_id, parent_id)
            DIRCOUNT += 1

        # +++ FILES +++
        for filename in fnmatch.filter(files, pattern):

            if dir in folder_blacklist:
                continue

            # calculating current depth
            current_depth = os.path.join(root, filename).count('/') - start_depth

            if DEBUG:
                print('current: ' + os.path.join(root, filename))

            node_id   = get_noteid(current_depth, root, filename)
            parent_id = str(get_parentid(current_depth, root, filename))

            if parent_id == str(None):
                FILE_ERRORLIST.append(os.path.join(root, dir))

            if DEBUG:
                print_node(filename, node_id, parent_id)

            # create node
            dir_tree.create_node(filename, node_id, parent_id)
            FILECOUNT += 1


if PROFILING == 0:
    crawler()
if PROFILING == 1:
    t1 = timeit.Timer("crawler()", "from __main__ import crawler")
    print('time:      ' + str(t1.timeit(number=1)))
if PROFILING == 2:
    cProfile.run("crawler()")


print('filecount: ' + str(FILECOUNT))
print('dircount:  ' + str(DIRCOUNT))

if DIR_ERRORLIST:
    for item in DIR_ERRORLIST:
        print(item)
else:
    print('no directory errors')

print('\n\n\n')

if FILE_ERRORLIST:
    for item in FILE_ERRORLIST:
        print(item)
else:
    print('no file errors')

print('nodes: ' + str(len(dir_tree.nodes)))

dir_tree.show()





########NEW FILE########
__FILENAME__ = test_treelib
#!/usr/bin/env python
import unittest
from treelib import Tree, Node
from treelib.tree import NodeIDAbsentError

class NodeCase(unittest.TestCase):
    def setUp(self):
        self.node1 = Node("Test One", "identifier 1")
        self.node2 = Node("Test Two", "identifier 2")

    def test_initialization(self):
        self.assertEqual(self.node1.tag, "Test One")
        self.assertEqual(self.node1.identifier, "identifier 1")
        self.assertEqual(self.node1.expanded, True)
        self.assertEqual(self.node1.bpointer, None)
        self.assertEqual(self.node1.fpointer, [])
        self.assertEqual(self.node1.data, None)

    def test_set_tag(self):
        self.node1.tag = "Test 1"
        self.assertEqual(self.node1.tag, "Test 1")
        self.node1.tag = "Test One"

    def test_set_identifier(self):
        self.node1.identifier = "ID1"
        self.assertEqual(self.node1.identifier, "ID1")
        self.node1.identifier = "identifier 1"

    def test_set_fpointer(self):
        self.node1.update_fpointer("identifier 2")
        self.assertEqual(self.node1.fpointer, ['identifier 2'])
        self.node1.fpointer = []

    def test_set_bpointer(self):
        self.node2.update_bpointer("identifier 1")
        self.assertEqual(self.node2.bpointer, 'identifier 1')
        self.node2.bpointer = None

    def test_set_is_leaf(self):
        self.node1.update_fpointer("identifier 2")
        self.node2.update_bpointer("identifier 1")
        self.assertEqual(self.node1.is_leaf(), False)
        self.assertEqual(self.node2.is_leaf(), True)

    def test_data(self):
        class Flower(object):
            def __init__(self, color):
                self.color = color
            def __str__(self):
                return "%s" % self.color
        self.node1.data = Flower("red")
        self.assertEqual(self.node1.data.color, "red")

    def tearDown(self):
        pass


class TreeCase(unittest.TestCase):
    def setUp(self):
        tree = Tree()
        tree.create_node("Harry", "harry")
        tree.create_node("Jane", "jane", parent="harry")
        tree.create_node("Bill", "bill", parent="harry")
        tree.create_node("Diane", "diane", parent="jane")
        tree.create_node("George", "george", parent="bill")
        self.tree = tree
        self.copytree = Tree(self.tree, True)

    def test_tree(self):
        self.assertEqual(isinstance(self.tree, Tree), True)
        self.assertEqual(isinstance(self.copytree, Tree), True)

    def test_is_root(self):
        self.assertTrue(self.tree._nodes['harry'].is_root())
        self.assertFalse(self.tree._nodes['jane'].is_root())

    def test_paths_to_leaves(self):
        paths = self.tree.paths_to_leaves()
        self.assertEqual( len(paths), 2 )
        self.assertTrue( ['harry', 'jane', 'diane'] in paths )
        self.assertTrue( ['harry', 'bill', 'george'] in paths )

    def test_nodes(self):
        self.assertEqual(len(self.tree.nodes), 5)
        self.assertEqual(len(self.tree.all_nodes()), 5)
        self.assertEqual(self.tree.size(), 5)
        self.assertEqual(self.tree.get_node("jane").tag, "Jane")
        self.assertEqual(self.tree.contains("jane"), True)
        self.assertEqual(self.tree.contains("alien"), False)
        self.tree.create_node("Alien","alien", parent="jane");
        self.assertEqual(self.tree.contains("alien"), True)
        self.tree.remove_node("alien")

    def test_getitem(self):
        """Nodes can be accessed via getitem."""
        for node_id in self.tree.nodes:
            try:
                self.tree[node_id]
            except NodeIDAbsentError:
                self.fail('Node access should be possible via getitem.')
        try:
            self.tree['root']
        except NodeIDAbsentError:
            pass
        else:
            self.fail('There should be no default fallback value for getitem.')

    def test_parent(self):
        for nid in self.tree.nodes:
            if nid == self.tree.root:
                self.assertEqual(self.tree.parent(nid), None)
            else:
                self.assertEqual(self.tree.parent(nid) in self.tree.all_nodes(), True)

    def test_children(self):
        for nid in self.tree.nodes:
            children = self.tree.is_branch(nid)
            for child in children:
                self.assertEqual(self.tree[child] in self.tree.all_nodes(), True)
            children = self.tree.children(nid)
            for child in children:
                self.assertEqual(child in self.tree.all_nodes(), True)
        try:
            self.tree.is_branch("alien")
        except NodeIDAbsentError:
            pass
        else:
            self.fail("The absent node should be declaimed.")

    def test_remove_node(self):
        self.tree.create_node("Jill", "jill", parent = "george")
        self.tree.create_node("Mark", "mark", parent = "jill")
        self.assertEqual(self.tree.remove_node("jill"), 2)
        self.assertEqual(self.tree.get_node("jill") is None, True)
        self.assertEqual(self.tree.get_node("mark") is None, True)

    def test_depth(self):
        # Try getting the level of this tree
        self.assertEqual(self.tree.depth(), 2)
        self.tree.create_node("Jill", "jill", parent = "george")
        self.assertEqual(self.tree.depth(), 3)
        self.tree.create_node("Mark", "mark", parent = "jill")
        self.assertEqual(self.tree.depth(), 4)

        # Try getting the level of the node
        """
        self.tree.show()
        Harry
        |___ Bill
        |    |___ George
        |         |___ Jill
        |              |___ Mark
        |___ Jane
        |    |___ Diane
        """
        self.assertEqual(self.tree.depth(self.tree.get_node("mark")), 4) # get depth via node instance
        self.assertEqual(self.tree.depth(self.tree.get_node("jill")), 3)
        self.assertEqual(self.tree.depth(self.tree.get_node("george")), 2)
        self.assertEqual(self.tree.depth("jane"), 1) # get depth via node identifier
        self.assertEqual(self.tree.depth("bill"), 1)
        self.assertEqual(self.tree.depth("harry"), 0)

        # Try getting Exception
        node = Node("Test One", "identifier 1")
        self.assertRaises(NodeIDAbsentError, self.tree.depth, node)

        # Reset the test case
        self.tree.remove_node("jill")

    def test_leaves(self):
        leaves = self.tree.leaves()
        for nid in self.tree.expand_tree():
            self.assertEqual((self.tree[nid].is_leaf()) == (self.tree[nid] in leaves), True)

    def test_link_past_node(self):
        self.tree.create_node("Jill", "jill", parent="harry")
        self.tree.create_node("Mark", "mark", parent="jill")
        self.assertEqual("mark" not in self.tree.is_branch("harry"), True)
        self.tree.link_past_node("jill")
        self.assertEqual("mark" in self.tree.is_branch("harry"), True)

    def test_expand_tree(self):
        nodes = [self.tree[nid] for nid in self.tree.expand_tree()]
        self.assertEqual(len(nodes), 5)

    def test_move_node(self):
        diane_parent = self.tree.parent("diane")
        self.tree.move_node("diane", "bill")
        self.assertEqual("diane" in self.tree.is_branch("bill"), True)
        self.tree.move_node("diane", diane_parent.identifier)

    def test_paste_tree(self):
        new_tree = Tree()
        new_tree.create_node("Jill", "jill")
        new_tree.create_node("Mark", "mark", parent="jill")
        self.tree.paste("jane", new_tree)
        self.assertEqual("jill" in self.tree.is_branch("jane"), True)
        self.tree.remove_node("jill")

    def test_rsearch(self):
        for nid in ["harry", "jane", "diane"]:
            self.assertEqual(nid in self.tree.rsearch("diane"), True)

    def test_subtree(self):
        subtree_copy = Tree(self.tree.subtree("jane"), deep=True)
        self.assertEqual(subtree_copy.parent("jane") is None, True)
        subtree_copy["jane"].tag = "Sweeti"
        self.assertEqual(self.tree["jane"].tag == "Jane", True)
        self.assertEqual(subtree_copy.level("diane"), 1)
        self.assertEqual(subtree_copy.level("jane"), 0)
        self.assertEqual(self.tree.level("jane"), 1)

    def test_remove_subtree(self):
        subtree_shallow = self.tree.remove_subtree("jane")
        self.assertEqual("jane" not in self.tree.is_branch("harry"), True)
        self.tree.paste("harry", subtree_shallow)

    def test_to_json(self):
        self.tree.to_json()

    def test_siblings(self):
        self.assertEqual(len(self.tree.siblings("harry")) == 0, True)
        self.assertEqual(self.tree.siblings("jane")[0].identifier == "bill", True)

    def test_tree_data(self):
        class Flower(object):
            def __init__(self, color):
                self.color = color
        self.tree.create_node("Jill", "jill", parent="jane", data=Flower("white"))
        self.assertEqual(self.tree["jill"].data.color, "white")
        self.tree.remove_node("jill")

    def test_level(self):
        self.assertEqual(self.tree.level('harry'),  0)
        depth = self.tree.depth()
        self.assertEqual(self.tree.level('diane'),  depth)
        self.assertEqual(self.tree.level('diane', lambda x:x.identifier!='jane'),depth-1)

    def tearDown(self):
        self.tree = None
        self.copytree = None


def suite():
    suites = [NodeCase, TreeCase]
    suite = unittest.TestSuite()
    for s in suites:
        suite.addTest(unittest.makeSuite(s))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = node
#!/usr/bin/env python
"""treelib - Simple to use for you.

   Python 2/3 Tree Implementation
"""

import uuid


class Node(object):
    """
    A Node object is stored inside the _nodes dictionary of a Tree object.
    Use Node objects to store data inside the data attribute.
    """

    #: ADD, DELETE, INSERT constants :
    (ADD, DELETE, INSERT) = list(range(3))

    def __init__(self, tag=None, identifier=None, expanded=True, data=None):
        """Create a new Node object to be placed inside a Tree object"""

        #: if given as a parameter, must be unique
        self._identifier = None
        self._set_identifier(identifier)

        #: None or something else
        #: if None, self._identifier will be set to the identifier's value.
        if tag is None:
            self._tag = self._identifier
        else:
            self._tag = tag

        #: boolean
        self.expanded = expanded

        #: identifier of the parent's node :
        self._bpointer = None
        #: identifier(s) of the soons' node(s) :
        self._fpointer = list()

        #: None or whatever given as a parameter
        self.data = data

    def __lt__(self, other):
        return self.tag < other.tag

    def _set_identifier(self, nid):
        """Initialize self._set_identifier"""
        if nid is None:
            self._identifier = str(uuid.uuid1())
        else:
            self._identifier = nid

    @property
    def bpointer(self):
        """return the value of _bpointer; see below for the setter"""
        return self._bpointer

    @bpointer.setter
    def bpointer(self, nid):
        """set the value of _bpointer; see above for the getter"""
        if nid is not None:
            self._bpointer = nid
        else:
            # print("WARNNING: the bpointer of node %s " \
            #      "is set to None" % self._identifier)
            self._bpointer = None

    @property
    def fpointer(self):
        """return the value of _fpointer; see below for the setter"""
        return self._fpointer

    @fpointer.setter
    def fpointer(self, value):
        """set the value of _fpointer; see above for the getter"""
        if value is None:
            self._fpointer = list()
        elif isinstance(value, list):
            self._fpointer = value
        elif isinstance(value, dict):
            self._fpointer = list(value.keys())
        elif isinstance(value, set):
            self._fpointer = list(value)
        else:  # TODO: add deprecated routine
            pass

    @property
    def identifier(self):
        """return the value of _identifier; see below for the setter"""
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        """set the value of _identifier; see above for the getter"""
        if value is None:
            print("WARNNING: node ID can not be None")
        else:
            self._set_identifier(value)

    def is_leaf(self):
        """return True if the the current node has no soon"""
        if len(self.fpointer) == 0:
            return True
        else:
            return False

    def is_root(self):
        """return True if self has no parent, i.e. if self is root"""
        return self._bpointer is None

    @property
    def tag(self):
        """return the value if _tag; see below for the setter"""
        return self._tag

    @tag.setter
    def tag(self, value):
        """set the value if _tag; see above for the getter"""
        self._tag = value if value is not None else None

    def update_bpointer(self, nid):
        """set bpointer"""
        self.bpointer = nid

    def update_fpointer(self, nid, mode=ADD):
        """set _fpointer recursively"""
        if nid is None:
            return

        if mode is self.ADD:
            self._fpointer.append(nid)
        elif mode is self.DELETE:
            if nid in self._fpointer:
                self._fpointer.remove(nid)
        elif mode is self.INSERT:  # deprecate to ADD mode
            print("WARNNING: INSERT is deprecated to ADD mode")
            self.update_fpointer(nid)

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = tree
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""treelib - Simple to use for you.

   Python 2/3 Tree Implementation
"""
from __future__ import print_function
from __future__ import unicode_literals
import json
from copy import deepcopy
try:
    from .node import Node
except:
    from node import Node

__author__ = 'chenxm'


class NodeIDAbsentError(Exception):
    """Exception throwed if a node's identifier is unknown"""
    pass


class MultipleRootError(Exception):
    """Exception throwed if more than one root exists in a tree."""
    pass


class DuplicatedNodeIdError(Exception):
    """Exception throwed if an identifier already exists in a tree."""
    pass


class LinkPastRootNodeError(Exception):
    """
    Exception throwed in Tree.link_past_node() if one attempts
    to "link past" the root node of a tree.
    """
    pass


class InvalidLevelNumber(Exception):
    pass


class Tree(object):
    """Tree objects are made of Node(s) stored in _nodes dictionary."""

    #: ROOT, DEPTH, WIDTH, ZIGZAG constants :
    (ROOT, DEPTH, WIDTH, ZIGZAG) = list(range(4))

    def __contains__(self, identifier):
        """Return a list of the nodes'identifiers matching the identifier argument"""
        return [node.identifier for node in self._nodes
                if node.identifier is identifier]

    def __init__(self, tree=None, deep=False):
        """Initiate a new tree or copy another tree with a shallow or deep copy."""

        #: dictionary, identifier: Node object
        self._nodes = {}

        #: identifier of the root node
        self.root = None

        if tree is not None:
            self.root = tree.root

            if deep:
                for nid in tree._nodes:
                    self._nodes[nid] = deepcopy(tree._nodes[nid])
            else:
                self._nodes = tree._nodes

    def __getitem__(self, key):
        """Return _nodes[key]"""
        try:
            return self._nodes[key]
        except KeyError:
            raise NodeIDAbsentError("Node '%s' is not in the tree" % key)

    def __len__(self):
        """Return len(_nodes)"""
        return len(self._nodes)

    def __setitem__(self, key, item):
        """Set _nodes[key]"""
        self._nodes.update({key: item})

    def __update_bpointer(self, nid, parent_id):
        """set self[nid].bpointer"""
        self[nid].update_bpointer(parent_id)

    def __update_fpointer(self, nid, child_id, mode):
        if nid is None:
            return
        else:
            self[nid].update_fpointer(child_id, mode)

    def _real_true(self, p):
        return True

    def _to_dict(self, nid=None, key=None, reverse=False):
        """transform self into a dict"""

        nid = self.root if (nid is None) else nid
        tree_dict = {self[nid].tag: {"children": []}}

        if self[nid].expanded:
            queue = [self[i] for i in self[nid].fpointer]
            key = (lambda x: x) if (key is None) else key
            queue.sort(key=key, reverse=reverse)

            for elem in queue:
                tree_dict[self[nid].tag]["children"].append(
                    self._to_dict(elem.identifier))
            if tree_dict[self[nid].tag]["children"] == []:
                tree_dict = self[nid].tag
            return tree_dict

    def add_node(self, node, parent=None):
        """
        Add a new node to tree.
        The 'node' parameter refers to an instance of Class::Node
        """
        if not isinstance(node, Node):
            raise OSError("First parameter must be object of Class::Node.")

        if node.identifier in self._nodes:
            raise DuplicatedNodeIdError("Can't create node "
                                        "with ID '%s'" % node.identifier)

        if parent is None:
            if self.root is not None:
                raise MultipleRootError("A tree takes one root merely.")
            else:
                self.root = node.identifier
        elif not self.contains(parent):
            raise NodeIDAbsentError("Parent node '%s' "
                                    "is not in the tree" % parent)

        self._nodes.update({node.identifier: node})
        self.__update_fpointer(parent, node.identifier, Node.ADD)
        self.__update_bpointer(node.identifier, parent)

    def all_nodes(self):
        """Return all nodes in a list"""
        return list(self._nodes.values())

    def children(self, nid):
        """
        Return the children (Node) list of nid.
        Empty list is returned if nid does not exist
        """
        return [self[i] for i in self.is_branch(nid)]

    def contains(self, nid):
        """Check if the tree contains node of given id"""
        return True if nid in self._nodes else False

    def create_node(self, tag=None, identifier=None, parent=None, data=None):
        """Create a child node for given @parent node."""
        node = Node(tag=tag, identifier=identifier, data=data)
        self.add_node(node, parent)
        return node

    def depth(self, node=None):
        """
        Get the maximum level of this tree or the level of the given node

        @param node Node instance or identifier
        @return int
        @throw NodeIDAbsentError
        """
        ret = 0
        if node is None:
            # Get maximum level of this tree
            leaves = self.leaves()
            for leave in leaves:
                level = self.level(leave.identifier)
                ret = level if level >= ret else ret
        else:
            # Get level of the given node
            if not isinstance(node, Node):
                nid = node
            else:
                nid = node.identifier
            if not self.contains(nid):
                raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)
            ret = self.level(nid)
        return ret

    def expand_tree(self, nid=None, mode=DEPTH, filter=None, key=None,
                    reverse=False):
        """
        Python generator. Loosly based on an algorithm from
        'Essential LISP' by John R. Anderson, Albert T. Corbett, and
        Brian J. Reiser, page 239-241

        UPDATE: the @filter function is performed on Node object during
        traversing.

        UPDATE: the @key and @reverse are present to sort nodes at each
        level.
        """
        nid = self.root if (nid is None) else nid
        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        filter = self._real_true if (filter is None) else filter
        if filter(self[nid]):
            yield nid
            queue = [self[i] for i in self[nid].fpointer if filter(self[i])]
            if mode in [self.DEPTH, self.WIDTH]:
                queue.sort(key=key, reverse=reverse)
                while queue:
                    yield queue[0].identifier
                    expansion = [self[i] for i in queue[0].fpointer
                                 if filter(self[i])]
                    expansion.sort(key=key, reverse=reverse)
                    if mode is self.DEPTH:
                        queue = expansion + queue[1:]  # depth-first
                    elif mode is self.WIDTH:
                        queue = queue[1:] + expansion  # width-first

            elif mode is self.ZIGZAG:
                # Suggested by Ilya Kuprik (ilya-spy@ynadex.ru).
                stack_fw = []
                queue.reverse()
                stack = stack_bw = queue
                direction = False
                while stack:
                    expansion = [self[i] for i in stack[0].fpointer
                                 if filter(self[i])]
                    yield stack.pop(0).identifier
                    if direction:
                        expansion.reverse()
                        stack_bw = expansion + stack_bw
                    else:
                        stack_fw = expansion + stack_fw
                    if not stack:
                        direction = not direction
                        stack = stack_fw if direction else stack_bw

    def get_node(self, nid):
        """Return the node with nid. None returned if nid not exists."""
        if nid is None or not self.contains(nid):
            return None
        return self._nodes[nid]

    def is_branch(self, nid):
        """
        Return the children (ID) list of nid.
        Empty list is returned if nid does not exist
        """
        if nid is None:
            raise OSError("First parameter can't be None")
        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        try:
            fpointer = self[nid].fpointer
        except KeyError:
            fpointer = []
        return fpointer

    def leaves(self, root=None):
        """Get leaves of the whole tree of a subtree."""
        leaves = []
        if root is None:
            for node in self._nodes.values():
                if node.is_leaf():
                    leaves.append(node)
        else:
            for node in self.expand_tree(root):
                if self[node].is_leaf():
                    leaves.append(node)
        return leaves

    def level(self, nid, filter=None):
        """
        Get the node level in this tree.
        The level is an integer starting with '0' at the root.
        In other words, the root lives at level '0';

        Update: @filter params is added to calculate level passing
        exclusive nodes.
        """
        return len([n for n in self.rsearch(nid, filter)])-1

    def link_past_node(self, nid):
        """
        Delete a node by linking past it.

        For example, if we have a -> b -> c and delete node b, we are left
        with a -> c
        """
        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)
        if self.root == nid:
            raise LinkPastRootNodeError("Cannot link past the root node, "
                                        "delete it with remove_node()")
        # Get the parent of the node we are linking past
        parent = self[self[nid].bpointer]
        # Set the children of the node to the parent
        for child in self[nid].fpointer:
            self[child].update_bpointer(parent.identifier)
        # Link the children to the parent
        parent.fpointer += self[nid].fpointer
        # Delete the node
        parent.update_fpointer(nid, mode=parent.DELETE)
        del self._nodes[nid]

    def move_node(self, source, destination):
        """
        Move a node indicated by @source parameter to be a child of
        @destination.
        """
        if not self.contains(source) or not self.contains(destination):
            raise NodeIDAbsentError

        parent = self[source].bpointer
        self.__update_fpointer(parent, source, Node.DELETE)
        self.__update_fpointer(destination, source, Node.ADD)
        self.__update_bpointer(source, destination)

    @property
    def nodes(self):
        """Return a dict form of nodes in a tree: {id: node_instance}"""
        return self._nodes

    def parent(self, nid):
        """Get parent node object of given id"""
        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        pid = self[nid].bpointer
        if pid is None or not self.contains(pid):
            return None

        return self[pid]

    def paste(self, nid, new_tree, deepcopy=False):
        """
        Paste a @new_tree to the original one by linking the root
        of new tree to given node (nid).

        Update: add @deepcopy of pasted tree.
        """
        assert isinstance(new_tree, Tree)
        if nid is None:
            raise OSError("First parameter can't be None")

        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        set_joint = set(new_tree._nodes) & set(self._nodes)  # joint keys
        if set_joint:
            # TODO: a deprecated routine is needed to avoid exception
            raise ValueError('Duplicated nodes %s exists.' % list(set_joint))

        if deepcopy:
            for node in new_tree._nodes:
                self._nodes.update({node.identifier: deepcopy(node)})
        else:
            self._nodes.update(new_tree._nodes)
        self.__update_fpointer(nid, new_tree.root, Node.ADD)
        self.__update_bpointer(new_tree.root, nid)

    def paths_to_leaves(self):
        """
        Use this function to get the identifiers allowing to go from the root
        nodes to each leaf.
        Return a list of list of identifiers, root being not omitted.

        For example :
            Harry
            |___ Bill
            |___ Jane
            |    |___ Diane
            |         |___ George
            |              |___ Jill
            |         |___ Mary
            |    |___ Mark

        expected result :
        [['harry', 'jane', 'diane', 'mary'],
         ['harry', 'jane', 'mark'],
         ['harry', 'jane', 'diane', 'george', 'jill'],
         ['harry', 'bill']]
        """
        res = []

        for leaf in self.leaves():
            res.append([nid for nid in self.rsearch(leaf.identifier)][::-1])

        return res

    def remove_node(self, identifier):
        """
        Remove a node indicated by 'identifier'; all the successors are
        removed as well.

        Return the number of removed nodes.
        """
        removed = []
        if identifier is None:
            return 0

        if not self.contains(identifier):
            raise NodeIDAbsentError("Node '%s' "
                                    "is not in the tree" % identifier)

        parent = self[identifier].bpointer
        for id in self.expand_tree(identifier):
            # TODO: implementing this function as a recursive function:
            #       check if node has children
            #       true -> run remove_node with child_id
            #       no -> delete node
            removed.append(id)
        cnt = len(removed)
        for id in removed:
            del self._nodes[id]
        # Update its parent info
        self.__update_fpointer(parent, identifier, Node.DELETE)
        return cnt

    def remove_subtree(self, nid):
        """
        Return a subtree deleted from this tree. If nid is None, an
        empty tree is returned.
        For the original tree, this method is similar to
        `remove_node(self,nid)`, because given node and its children
        are removed from the original tree in both methods.
        For the returned value and performance, these two methods are
        different:

            `remove_node` returns the number of deleted nodes;
            `remove_subtree` returns a subtree of deleted nodes;

        You are always suggested to use `remove_node` if your only to
        delete nodes from a tree, as the other one need memory
        allocation to store the new tree.
        """
        st = Tree()
        if nid is None:
            return st

        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)
        st.root = nid

        parent = self[nid].bpointer
        self[nid].bpointer = None  # reset root parent for the new tree
        removed = []
        for id in self.expand_tree(nid):
            removed.append(id)
        for id in removed:
            st._nodes.update({id: self._nodes.pop(id)})
        # Update its parent info
        self.__update_fpointer(parent, nid, Node.DELETE)
        return st

    def rsearch(self, nid, filter=None):
        """
        Traverse the tree branch along the branch from nid to its
        ancestors (until root).
        """
        if nid is None:
            return

        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        filter = (self._real_true) if (filter is None) else filter

        current = nid
        while current is not None:
            if filter(self[current]):
                yield current
            # subtree() hasn't update the bpointer
            current = self[current].bpointer if self.root != current else None

    def save2file(self, filename, nid=None, level=ROOT, idhidden=True,
                  filter=None, key=None, reverse=False, line_type='ascii-ex'):
        """Update 20/05/13: Save tree into file for offline analysis"""
        handler = lambda x: open(filename, 'ab').write(''.join([x,'\n']).encode('utf-8'))
        self._print_backend(nid,
                            level,
                            idhidden,
                            filter,
                            key,
                            reverse,
                            line_type,
                            handler)
        
    def show(self, nid=None, level=ROOT, idhidden=True, filter=None,
             key=None, reverse=False, line_type='ascii-ex'):
        self._print_backend(nid,
                            level,
                            idhidden,
                            filter,
                            key,
                            reverse,
                            line_type,
                            func=print)

    def _print_backend(self, nid=None, level=ROOT, idhidden=True, filter=None,
             key=None, reverse=False, line_type='ascii-ex', func=print, iflast=[]):
        """
        Another implementation of printing tree using Stack
        Print tree structure in hierarchy style.

        For example:
            Root
            |___ C01
            |    |___ C11
            |         |___ C111
            |         |___ C112
            |___ C02
            |___ C03
            |    |___ C31

        A more elegant way to achieve this function using Stack
        structure, for constructing the Nodes Stack push and pop nodes
        with additional level info.

        UPDATE: the @key @reverse is present to sort node at each
        level.
        """
        line_types = \
        {'ascii': ('|', '|-- ', '+-- '),
         'ascii-ex': ('\u2502', '\u251c\u2500\u2500 ', '\u2514\u2500\u2500 '),
         'ascii-exr': ('\u2502', '\u251c\u2500\u2500 ', '\u2570\u2500\u2500 '),
         'ascii-em': ('\u2551', '\u2560\u2550\u2550 ', '\u255a\u2550\u2550 '),
         'ascii-emv': ('\u2551', '\u255f\u2500\u2500 ', '\u2559\u2500\u2500 '),
         'ascii-emh': ('\u2502', '\u255e\u2550\u2550 ', '\u2558\u2550\u2550 ')}
        DT_VLINE, DT_LINE_BOX, DT_LINE_COR = line_types[line_type]

        leading = ''
        lasting = DT_LINE_BOX

        nid = self.root if (nid is None) else nid
        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        label = ("{0}".format(self[nid].tag)) \
                 if idhidden else ("{0}[{1}]".format(self[nid].tag,
                                                     self[nid].identifier))

        filter = (self._real_true) if (filter is None) else filter

        if level == self.ROOT:
            func(label)
        else:
            leading = ''.join(map(lambda x: DT_VLINE + ' ' * 3 if not x else ' ' * 4, iflast[0:-1]))
            lasting = DT_LINE_COR if iflast[-1] else DT_LINE_BOX
            func("{0}{1}{2}".format(leading, lasting, label))

        if filter(self[nid]) and self[nid].expanded:
            queue = [self[i] for i in self[nid].fpointer if filter(self[i])]
            key = (lambda x: x) if (key is None) else key
            queue.sort(key=key, reverse=reverse)
            level += 1
            for element in queue:
                iflast.append(queue.index(element) == len(queue)-1)
                self._print_backend(element.identifier,
                          level,
                          idhidden,
                          filter,
                          key,
                          reverse,
                          line_type,
                          func,
                          iflast)
                iflast.pop()

    def siblings(self, nid):
        """
        Return the siblings of given @nid.

        If @nid is root or there are no siblings, an empty list is returned.
        """
        siblings = []

        if nid != self.root:
            pid = self[nid].bpointer
            siblings = [self[i] for i in self[pid].fpointer if i != nid]

        return siblings

    def size(self, level=None):
        """
        Get the number of nodes of the whole tree if @level is not
        given. Otherwise, the total number of nodes at specific level
        is returned.

        @param level The level number in the tree. It must be between
        [0, tree.depth].

        Otherwise, InvalidLevelNumber exception will be raised.
        """
        return len(self._nodes)

    def subtree(self, nid):
        """
        Return a shallow COPY of subtree with nid being the new root.
        If nid is None, return an empty tree.
        If you are looking for a deepcopy, please create a new tree
        with this shallow copy,

        e.g.
            new_tree = Tree(t.subtree(t.root), deep=True)

        This line creates a deep copy of the entire tree.
        """
        st = Tree()
        if nid is None:
            return st

        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        st.root = nid
        for node_n in self.expand_tree(nid):
            st._nodes.update({self[node_n].identifier: self[node_n]})
        return st

    def to_json(self):
        """Return the json string corresponding to self"""
        return json.dumps(self._to_dict())

if __name__ == '__main__':
    pass

########NEW FILE########
