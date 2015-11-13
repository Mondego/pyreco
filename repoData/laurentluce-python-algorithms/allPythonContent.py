__FILENAME__ = a_star_path_finding
import heapq

class Cell(object):
    def __init__(self, x, y, reachable):
        """
        Initialize new cell

        @param x cell x coordinate
        @param y cell y coordinate
        @param reachable is cell reachable? not a wall?
        """
        self.reachable = reachable
        self.x = x
        self.y = y
        self.parent = None
        self.g = 0
        self.h = 0
        self.f = 0

class AStar(object):
    def __init__(self):
        self.op = []
        heapq.heapify(self.op)
        self.cl = set()
        self.cells = []
        self.gridHeight = 6
        self.gridWidth = 6

    def init_grid(self):
        walls = ((0, 5), (1, 0), (1, 1), (1, 5), (2, 3), 
                 (3, 1), (3, 2), (3, 5), (4, 1), (4, 4), (5, 1))
        for x in range(self.gridWidth):
            for y in range(self.gridHeight):
                if (x, y) in walls:
                    reachable = False
                else:
                    reachable = True
                self.cells.append(Cell(x, y, reachable))
        self.start = self.get_cell(0, 0)
        self.end = self.get_cell(5, 5)

    def get_heuristic(self, cell):
        """
        Compute the heuristic value H for a cell: distance between
        this cell and the ending cell multiply by 10.

        @param cell
        @returns heuristic value H
        """
        return 10 * (abs(cell.x - self.end.x) + abs(cell.y - self.end.y))

    def get_cell(self, x, y):
        """
        Returns a cell from the cells list

        @param x cell x coordinate
        @param y cell y coordinate
        @returns cell
        """
        return self.cells[x * self.gridHeight + y]

    def get_adjacent_cells(self, cell):
        """
        Returns adjacent cells to a cell. Clockwise starting
        from the one on the right.

        @param cell get adjacent cells for this cell
        @returns adjacent cells list 
        """
        cells = []
        if cell.x < self.gridWidth-1:
            cells.append(self.get_cell(cell.x+1, cell.y))
        if cell.y > 0:
            cells.append(self.get_cell(cell.x, cell.y-1))
        if cell.x > 0:
            cells.append(self.get_cell(cell.x-1, cell.y))
        if cell.y < self.gridHeight-1:
            cells.append(self.get_cell(cell.x, cell.y+1))
        return cells

    def display_path(self):
        cell = self.end
        while cell.parent is not self.start:
            cell = cell.parent
            print 'path: cell: %d,%d' % (cell.x, cell.y)

    def compare(self, cell1, cell2):
        """
        Compare 2 cells F values

        @param cell1 1st cell
        @param cell2 2nd cell
        @returns -1, 0 or 1 if lower, equal or greater
        """
        if cell1.f < cell2.f:
            return -1
        elif cell1.f > cell2.f:
            return 1
        return 0
    
    def update_cell(self, adj, cell):
        """
        Update adjacent cell

        @param adj adjacent cell to current cell
        @param cell current cell being processed
        """
        adj.g = cell.g + 10
        adj.h = self.get_heuristic(adj)
        adj.parent = cell
        adj.f = adj.h + adj.g

    def process(self):
        # add starting cell to open heap queue
        heapq.heappush(self.op, (self.start.f, self.start))
        while len(self.op):
            # pop cell from heap queue 
            f, cell = heapq.heappop(self.op)
            # add cell to closed list so we don't process it twice
            self.cl.add(cell)
            # if ending cell, display found path
            if cell is self.end:
                self.display_path()
                break
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for c in adj_cells:
                if c.reachable and c not in self.cl:
                    if (c.f, c) in self.op:
                        # if adj cell in open list, check if current path is
                        # better than the one previously found
                        # for this adj cell.
                        if c.g > cell.g + 10:
                            self.update_cell(c, cell)
                    else:
                        self.update_cell(c, cell)
                        # add adj cell to open list
                        heapq.heappush(self.op, (c.f, c))

a = AStar()
a.init_grid()
a.process()


########NEW FILE########
__FILENAME__ = binary_tree
class Node:
    """
    Tree node: left and right child + data which can be any object
    """
    def __init__(self, data):
        """
        Node constructor

        @param data node data object
        """
        self.left = None
        self.right = None
        self.data = data

    def insert(self, data):
        """
        Insert new node with data

        @param data node data object to insert
        """
        if data < self.data:
            if self.left is None:
                self.left = Node(data)
            else:
                self.left.insert(data)
        else:
            if self.right is None:
                self.right = Node(data)
            else:
                self.right.insert(data)

    def lookup(self, data, parent=None):
        """
        Lookup node containing data

        @param data node data object to look up
        @param parent node's parent
        @returns node and node's parent if found or None, None
        """
        if data < self.data:
            if self.left is None:
                return None, None
            return self.left.lookup(data, self)
        elif data > self.data:
            if self.right is None:
                return None, None
            return self.right.lookup(data, self)
        else:
            return self, parent

    def delete(self, data):
        """
        Delete node containing data

        @param data node's content to delete
        """
        # get node containing data
        node, parent = self.lookup(data)
        if node is not None:
            children_count = node.children_count()
            if children_count == 0:
                # if node has no children, just remove it
                # check if it is not the root node
                if parent.left is node:
                    parent.left = None
                else:
                    parent.right = None
                del node
            elif children_count == 1:
                # if node has 1 child
                # replace node by its child
                if node.left:
                    n = node.left
                else:
                    n = node.right
                if parent.left is node:
                    parent.left = n
                else:
                    parent.right = n
                del node
            else:
                # if node has 2 children
                # find its successor
                parent = node
                successor = node.right
                while successor.left:
                    parent = successor
                    successor = successor.left
                # replace node data by its successor data
                node.data = successor.data
                # fix successor's parent node child
                if parent.left == successor:
                    parent.left = successor.right
                else:
                    parent.right = successor.right

    def compare_trees(self, node):
        """
        Compare 2 trees

        @param node tree to compare
        @returns True if the tree passed is identical to this tree
        """
        if node is None:
            return False
        if self.data != node.data:
            return False
        res = True
        if self.left is None:
            if node.left:
                return False
        else:
            res = self.left.compare_trees(node.left)
        if self.right is None:
            if node.right:
                return False
        else:
            res = self.right.compare_trees(node.right)
        return res
                
    def print_tree(self):
        """
        Print tree content inorder
        """
        if self.left:
            self.left.print_tree()
        print self.data,
        if self.right:
            self.right.print_tree()

    def tree_data(self):
        """
        Generator to get the tree nodes data
        """
        # we use a stack to traverse the tree in a non-recursive way
        stack = []
        node = self
        while stack or node: 
            if node:
                stack.append(node)
                node = node.left
            else: # we are returning so we pop the node and we yield it
                node = stack.pop()
                yield node.data
                node = node.right

    def children_count(self):
        """
        Return the number of children

        @returns number of children: 0, 1, 2
        """
        cnt = 0
        if self.left:
            cnt += 1
        if self.right:
            cnt += 1
        return cnt

########NEW FILE########
__FILENAME__ = generators
def fib(n):
    """
    Generator for Fibonacci serie

    Example: for i in fib(5): print i
    @param n fib range upper bound
    """
    a, b = 0, 1
    i = 0
    while i < n:
        yield b
        a, b = b, a+b
        i += 1


########NEW FILE########
__FILENAME__ = list
def find_max_sub(l):
    """
    Find subset with higest sum

    Example: [-2, 3, -4, 5, 1, -5] -> (3,4), 6
    @param l list
    @returns subset bounds and highest sum
    """
    # max sum
    max = l[0]
    # current sum
    m = 0
    # max sum subset bounds
    bounds = (0, 0)
    # current subset start
    s = 0
    for i in range(len(l)):
        m += l[i]
        if m > max:
            max = m
            bounds = (s, i)
        elif m < 0:
            m = 0
            s = i+1
    return bounds, max

########NEW FILE########
__FILENAME__ = maze
grid = [[0, 0, 0, 0, 0, 1],
        [1, 1, 0, 0, 0, 1],
        [0, 0, 0, 1, 0, 0],
        [0, 1, 1, 0, 0, 1],
        [0, 1, 0, 0, 1, 0],
        [0, 1, 0, 0, 0, 2]
        ]

def search(x, y):
    if grid[x][y] == 2:
        print 'found at %d,%d' % (x, y)
        return True
    elif grid[x][y] == 1:
        print 'wall at %d,%d' % (x, y)
        return False
    elif grid[x][y] == 3:
        print 'visited at %d,%d' % (x, y)
        return False
    
    print 'visiting %d,%d' % (x, y)

    # mark as visited
    grid[x][y] = 3
    if ((x < len(grid)-1 and search(x+1, y)) 
        or (y > 0 and search(x, y-1))
        or (x > 0 and search(x-1, y))
        or (y < len(grid)-1 and search(x, y+1))):
        return True

    return False

search(0, 0)


########NEW FILE########
__FILENAME__ = performance_string_matching
import time
import string_matching

class StringMatchingPerformance:
   
  def __init__(self):
    pass

  def calculate_performance(self):
    t = 'ababbababa'
    s = 'aba'
    times = 1000
    
    ts = time.time()
    for i in range(times):
      string_matching.string_matching_naive(t, s)
    t1 = time.time() - ts
    print 'string_matching_naive: %.2f seconds' % t1

    ts = time.time()
    for i in range(times):
      string_matching.string_matching_rabin_karp(t, s)
    t2 = time.time() - ts
    print 'string_matching_rabin_karp: %.2f seconds' % t2

    ts = time.time()
    for i in range(times):
      string_matching.string_matching_knuth_morris_pratt(t, s)
    t2 = time.time() - ts
    print 'string_matching_knuth_morris_pratt: %.2f seconds' % t2

    ts = time.time()
    for i in range(times):
      string_matching.string_matching_boyer_moore_horspool(t, s)
    t2 = time.time() - ts
    print 'string_matching_boyer_moore_horspool: %.2f seconds' % t2

if __name__ == '__main__':
  p = StringMatchingPerformance()
  p.calculate_performance()


########NEW FILE########
__FILENAME__ = permutations
def permutations(l):
    """
    Generator for list permutations
    
    @param l list to generate permutations for
    @result yield each permutation

    Example:
    l = [1,2,3]
    a = [1]
    permutations([2,3]) = [[2,3], [3,2]]
    [2,3]
    yield [1,2,3]
    yield [2,1,3]
    yield [2,3,1]
    [3,2]
    yield [1,3,2]
    yield [3,1,2]
    yield [3,2,1]
    """
    if len(l) <= 1:
        yield l
    else:
        a = [l.pop(0)]
        for p in permutations(l):
            for i in range(len(p)+1):
                yield p[:i] + a + p[i:]

for p in permutations([1,2,3]):
    print p


########NEW FILE########
__FILENAME__ = string_matching
"""
Filename: string_matching.py
"""

def string_matching_naive(text='', pattern=''):
    """
    Returns positions where pattern is found in text

    We slide the string to match 'pattern' over the text

    O((n-m)m)
    Example: text = 'ababbababa', pattern = 'aba'
                     string_matching_naive(t, s) returns [0, 5, 7]
    @param text text to search inside
    @param pattern string to search for
    @return list containing offsets (shifts) where pattern is found inside text
    """

    n = len(text)
    m = len(pattern)
    offsets = []
    for i in range(n-m+1):
        if pattern == text[i:i+m]:
            offsets.append(i)

    return offsets


def string_matching_rabin_karp(text='', pattern='', hash_base=256):
    """
    Returns positions where pattern is found in text

    We calculate the hash value of the pattern and we compare it to the hash
    value of text[i:i+m] for i = 0..n-m
    The nice thing is that we don't need to calculate the hash value of
    text[i:i+m] each time from scratch, we know that:
    h(text[i+1:i+m+1]) = (base * (h(text[i:i+m]) - (text[i] * (base ^ (m-1))))) + text[i+m]
    We can get h('bcd') from h('abc').
    h('bcd') = (base * (h('abc') - ('a' * (base ^ 2)))) + 'd'
    
    worst case: O(nm)
    we can expect O(n+m) if the number of valid matches is small and the pattern
    large
    
    Performance: ord() is slow so we shouldn't use it here

    Example: text = 'ababbababa', pattern = 'aba'
                     string_matching_rabin_karp(text, pattern) returns [0, 5, 7]
    @param text text to search inside
    @param pattern string to search for
    @param hash_base base to calculate the hash value 
    @return list containing offsets (shifts) where pattern is found inside text
    """

    n = len(text)
    m = len(pattern)
    offsets = []
    htext = hash_value(text[:m], hash_base)
    hpattern = hash_value(pattern, hash_base)
    for i in range(n-m+1):
        if htext == hpattern:
            if text[i:i+m] == pattern: 
                offsets.append(i)
        if i < n-m:
            htext = (hash_base * (htext - (ord(text[i]) * (hash_base ** (m-1))))) + ord(text[i+m])

    return offsets

def hash_value(s, base):
    """
    Calculate the hash value of a string using base

    Example: 'abc' = 97 x base^2 + 98 x base^1 + 99 x base^0
    @param s string to compute hash value for
    @param base base to use to compute hash value
    @return hash value
    """
    v = 0
    p = len(s)-1
    for i in range(p+1):
        v += ord(s[i]) * (base ** p)
        p -= 1

    return v

def string_matching_knuth_morris_pratt(text='', pattern=''):
    """
    Returns positions where pattern is found in text

    See http://jboxer.com/2009/12/the-knuth-morris-pratt-algorithm-in-my-own-words/ for a great explanation on how this algorithm works.
    
    O(m+n)
    Example: text = 'ababbababa', pattern = 'aba'
                     string_matching_knuth_morris_pratt(text, pattern) returns [0, 5, 7]
    @param text text to search inside
    @param pattern string to search for
    @return list containing offsets (shifts) where pattern is found inside text
    """

    n = len(text)
    m = len(pattern)
    offsets = []
    pi = compute_prefix_function(pattern)
    q = 0
    for i in range(n):
        while q > 0 and pattern[q] != text[i]:
            q = pi[q - 1]
        if pattern[q] == text[i]:
            q = q + 1
        if q == m:
            offsets.append(i - m + 1)
            q = pi[q-1]

    return offsets

def compute_prefix_function(p):
    m = len(p)
    pi = [0] * m
    k = 0
    for q in range(1, m):
        while k > 0 and p[k] != p[q]:
            k = pi[k - 1]
        if p[k] == p[q]:
            k = k + 1
        pi[q] = k
    return pi

def string_matching_boyer_moore_horspool(text='', pattern=''):
    """
    Returns positions where pattern is found in text

    See http://en.wikipedia.org/wiki/Boyer%E2%80%93Moore%E2%80%93Horspool_algorithm for an explanation on how 
    this algorithm works.
    
    O(n)
    Performance: ord() is slow so we shouldn't use it here

    Example: text = 'ababbababa', pattern = 'aba'
                     string_matching_boyer_moore_horspool(text, pattern) returns [0, 5, 7]
    @param text text to search inside
    @param pattern string to search for
    @return list containing offsets (shifts) where pattern is found inside text
    """
    
    m = len(pattern)
    n = len(text)
    offsets = []
    if m > n:
        return offsets
    skip = []
    for k in range(256):
        skip.append(m)
    for k in range(m-1):
        skip[ord(pattern[k])] = m - k - 1
    skip = tuple(skip)
    k = m - 1
    while k < n:
        j = m - 1; i = k
        while j >= 0 and text[i] == pattern[j]:
            j -= 1
            i -= 1
        if j == -1:
            offsets.append(i + 1)
        k += skip[ord(text[k])]

    return offsets


########NEW FILE########
__FILENAME__ = test_binary_tree
import unittest
import algorithms.binary_tree as binary_tree

class BinaryTreeTest(unittest.TestCase):
    
  def test_binary_tree(self):

    data = [10, 5, 15, 4, 7, 13, 17, 11, 14]
    # create 2 trees with the same content
    root = binary_tree.Node(data[0])
    for i in data[1:]:
      root.insert(i)

    root2 = binary_tree.Node(data[0])
    for i in data[1:]:
      root2.insert(i)

    # check if both trees are identical
    self.assertTrue(root.compare_trees(root2))

    # check the content of the tree inorder
    t = []
    for d in root.tree_data():
      t.append(d)
    self.assertEquals(t, [4, 5, 7, 10, 11, 13, 14, 15, 17])

    # test lookup
    node, parent = root.lookup(9)
    self.assertTrue(node is None)
    # check if returned node and parent are correct
    node, parent = root.lookup(11)
    self.assertTrue(node.data == 11)
    self.assertTrue(parent.data == 13)

    # delete a leaf node
    root.delete(4)
    # check the content of the tree inorder
    t = []
    for d in root.tree_data():
      t.append(d)
    self.assertEquals(t, [5, 7, 10, 11, 13, 14, 15, 17])

    # delete a node with 1 child
    root.delete(5)
    # check the content of the tree inorder
    t = []
    for d in root.tree_data():
      t.append(d)
    self.assertEquals(t, [7, 10, 11, 13, 14, 15, 17])

    # delete a node with 2 children
    root.delete(13)
    # check the content of the tree inorder
    t = []
    for d in root.tree_data():
      t.append(d)
    self.assertEquals(t, [7, 10, 11, 14, 15, 17])

    # delete a node with 2 children
    root.delete(15)
    # check the content of the tree inorder
    t = []
    for d in root.tree_data():
      t.append(d)
    self.assertEquals(t, [7, 10, 11, 14, 17])

if __name__ == '__main__':
  unittest.main()


########NEW FILE########
__FILENAME__ = test_string_matching
import unittest
import string_matching

class StringMatchingTest(unittest.TestCase):
    
  def test_string_matching_naive(self):
        t = 'ababbababa'
        s = 'aba'
        self.assertEquals(string_matching.string_matching_naive(t, s), [0, 5, 7])
        t = 'ababbababa'
        s = 'abbb'
        self.assertEquals(string_matching.string_matching_naive(t, s), [])

  def test_string_matching_rabin_karp(self):
        t = 'ababbababa'
        s = 'aba'
        self.assertEquals(string_matching.string_matching_rabin_karp(t, s), [0, 5, 7])
        t = 'ababbababa'
        s = 'abbb'
        self.assertEquals(string_matching.string_matching_rabin_karp(t, s), [])

  def test_string_matching_knuth_morris_pratt(self):
        t = 'ababbababa'
        s = 'aba'
        self.assertEquals(string_matching.string_matching_knuth_morris_pratt(t, s), [0, 5, 7])
        t = 'ababbababa'
        s = 'abbb'
        self.assertEquals(string_matching.string_matching_knuth_morris_pratt(t, s), [])

  def test_string_matching_boyer_moore_horspool(self):
        t = 'ababbababa'
        s = 'aba'
        self.assertEquals(string_matching.string_matching_boyer_moore_horspool(t, s), [0, 5, 7])
        t = 'ababbababa'
        s = 'abbb'
        self.assertEquals(string_matching.string_matching_boyer_moore_horspool(t, s), [])

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
