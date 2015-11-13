__FILENAME__ = extended_gcd
"""
    extended_gcd.py

    This module implements the extended greatest common divider algorithm.

    Pre: two integers a and b
    Post: a tuple (x, y) where a*x + b*y = gcd(a, b)

    Pseudo Code: http://en.wikipedia.org/wiki/Extended_Euclidean_algorithm
"""


def extended_gcd(p, q):

    (a, b) = (p, q)

    if a < 0:
        a = -1 * a

    if b < 0:
        b = -1 * b

    x0 = 0
    y1 = 0

    x1 = 1
    y0 = 1

    while(b != 0):
        quotient = a / b
        (a, b) = (b, a % b)
        (x1, x0) = (x0 - quotient * x1, x1)
        (y1, y0) = (y0 - quotient * y1, y1)

    if p < 0:
        y0 = -1 * y0

    if q < 0:
        x0 = -1 * x0

    return (y0, x0)

########NEW FILE########
__FILENAME__ = mersenne_twister
"""
    mersenne_twister.py

    Implementation of Mersenne Twister pseudo random number generator

    Mersenne Twister Overview:
    ---------------------------
    Generates high quality pseudo random integers with a long period.
    Used as the default random number generator for several
    languages (including Python).

    For a more technical overview, see the wikipedia entry.

    Pseudocode: http://en.wikipedia.org/wiki/Mersenne_twister
"""


class MersenneTwister:
    def __init__(self):
        self.state = []
        self.index = 0

    def seed(self, seed):
        """Initialize generator"""
        self.state = []
        self.index = 0
        self.state.append(seed)
        for i in range(1, 624):
            n = (0x6c078965 * (self.state[i-1] ^ (self.state[i-1] >> 30)) + i)
            n &= 0xffffffff
            self.state.append(n)


    def randint(self):
        """Extract random number"""
        if self.index == 0:
            self.generate()
            
        y = self.state[self.index]
        y ^= y >> 11
        y ^= (y << 7) & 0x9d2c5680
        y ^= (y << 15) & 0xefc60000
        y ^= y >> 18
        
        self.index = (self.index + 1) % 624
        return y


    def generate(self):
        """Generate 624 new random numbers"""
        for i in range(624):
            n = self.state[i] & 0x80000000
            n += self.state[(i+1)%624] & 0x7fffffff
            self.state[i] = self.state[(i+397)%624] ^ (n >> 1)
            if n%2 != 0:
                self.state[i] ^= 0x9908b0df

########NEW FILE########
__FILENAME__ = binary_search
"""
    binary_search.py

    Implementation of binary search on a sorted list.

    Binary Search Overview:
    ------------------------
    Recursively partitions the list until the key is found.

    Time Complexity:  O(lg n)

    Psuedo Code: http://en.wikipedia.org/wiki/Binary_search

"""


def search(seq, key):
    lo = 0
    hi = len(seq) - 1

    while hi >= lo:
        mid = lo + (hi - lo) // 2
        if seq[mid] < key:
            lo = mid + 1
        elif seq[mid] > key:
            hi = mid - 1
        else:
            return mid
    return False

########NEW FILE########
__FILENAME__ = bmh_search
"""
    bmh_search.py

    Implementation of bmh search to find a substring in a string

    BMH Search Overview:
    --------------------
    Uses a bad-character shift of the rightmost character of the window to
    compute shifts.

    Time: Complexity: O(m + n), where m is the substring to be found.

    Space: Complexity: O(m), where m is the substring to be found.

    Psuedo Code: https://github.com/FooBarWidget/boyer-moore-horspool

"""


def search(text, pattern):
    pattern_length = len(pattern)
    text_length = len(text)
    offsets = []
    if pattern_length > text_length:
        return offsets
    bmbc = [pattern_length] * 256
    for index, char in enumerate(pattern[:-1]):
        bmbc[ord(char)] = pattern_length - index - 1
    bmbc = tuple(bmbc)
    search_index = pattern_length - 1
    while search_index < text_length:
        pattern_index = pattern_length - 1
        text_index = search_index
        while text_index >= 0 and \
                text[text_index] == pattern[pattern_index]:
            pattern_index -= 1
            text_index -= 1
        if pattern_index == -1:
            offsets.append(text_index + 1)
        search_index += bmbc[ord(text[search_index])]

    return offsets

########NEW FILE########
__FILENAME__ = depth_first_search
"""
    depth_first_search.py

    Recursive implementation of DFS algorithm on a graph.

    Depth First Search Overview:
    ------------------------
    Used to traverse trees, tree structures or graphs.
    Starts at a selected node (root) and explores the branch
    as far as possible before backtracking.

    Time Complexity: O(E + V)
        E = Number of edges
        V = Number of vertices (nodes)

    Pseudocode: https://en.wikipedia.org/wiki/Depth-first_search    
"""
def dfs(graph,start,path = []):
    if start not in graph or graph[start] == None or graph[start] == []:
        return None
    path = path + [start]
    for edge in graph[start]:
        if edge not in path:
            path = dfs(graph, edge,path)
    return path

########NEW FILE########
__FILENAME__ = kmp_search
"""
    kmp_search.py

    Implementation of kmp search on a sorted list.

    KMP Search Overview:
    ------------------------
    Uses a prefix function to reduce the searching time.

    Time Complexity:  O(n + k), where k is the substring to be found

    Psuedo Code: CLRS. Introduction to Algorithms. 3rd ed.

"""


def search(string, word):
    word_length = len(word)
    string_length = len(string)
    offsets = []

    if word_length > string_length:
        return offsets

    prefix = compute_prefix(word)
    q = 0
    for index, letter in enumerate(string):
        while q > 0 and word[q] != letter:
            q = prefix[q - 1]
        if word[q] == letter:
            q += 1
        if q == word_length:
            offsets.append(index - word_length + 1)
            q = prefix[q - 1]
    return offsets


def compute_prefix(word):
    word_length = len(word)
    prefix = [0] * word_length
    k = 0

    for q in xrange(1, word_length):
        while k > 0 and word[k] != word[q]:
            k = prefix[k - 1]

        if word[k + 1] == word[q]:
            k = k + 1
        prefix[q] = k
    return prefix

########NEW FILE########
__FILENAME__ = rabinkarp_search
"""
    rabinkarp_search.py

    Implementation of Rabin-Karp search on a given string.

    Rabin-Karp Search Overview:
    ------------------------
    Search for a substring in a given string, by comparing hash values
    of the strings.

    Time Complexity: O(nm)

    Psuedo Code: http://en.wikipedia.org/wiki/Rabin-Karp_algorithm

"""

from hashlib import md5


def search(s, sub):
    n, m = len(s), len(sub)
    hsub_digest = md5(sub).digest()
    offsets = []
    if m > n:
        return offsets

    for i in xrange(n - m + 1):
        if md5(s[i:i + m]).digest() == hsub_digest:
            if s[i:i + m] == sub:
                offsets.append(i)

    return offsets

########NEW FILE########
__FILENAME__ = knuth
"""
    knuth.py
    Implementation of the Fisher-Yates/Knuth shuffle

    Fisher-Yates/Knuth Overview:
    ----------------------------
    Randomly picks integers to swap elements in an ubiased manner.

    Time Complexity: O(n)
    Space Complexity: O(n)n

    Pseudocode: http://en.wikipedia.org/wiki/Fisher%E1%80%93Yates_shuffle

"""
from random import seed, randint


def shuffle(seq):
    seed()
    for i in reversed(range(len(seq))):
        j = randint(0, i)
        seq[i], seq[j] = seq[j], seq[i]
    return seq

########NEW FILE########
__FILENAME__ = bogo_sort
"""
    bogo_sort.py

    Implementation of bogo sort on a list and returns a sorted list.

    Bogo Sort Overview:
    -------------------
    A naive sorting that picks two elements at random and swaps them.

    Time Complexity: O(n * n!)

    Space Complexity: O(1) Auxiliary

    Stable: No

    WARNING: This algorithm may never sort the list correctly.
"""

import random


def sort(seq):
    if len(seq) == 1:
        return seq
    random.seed()
    while not is_sorted(seq):
        if len(seq) == 2:
            i = 0
            j = 1
        else:
            i = random.randint(0, len(seq) - 2)
            j = random.randint(i, len(seq) - 1)
        seq[i], seq[j] = seq[j], seq[i]
    return seq


def is_sorted(seq):
    return all(seq[i - 1] <= seq[i] for i in xrange(1, len(seq)))

########NEW FILE########
__FILENAME__ = bubble_sort
"""
    bubble_sort.py

    Implementation of bubble sort on a list and returns a sorted list.

    Bubble Sort Overview:
    ---------------------
    A naive sorting that compares and swaps adjacent elements

    Time Complexity: O(n**2)

    Space Complexity: O(1) Auxiliary

    Stable: Yes

    Psuedo code: http://en.wikipedia.org/wiki/Bubble_sort

"""


def sort(seq):
    L = len(seq)
    for _ in range(L):
        for n in range(1, L):
            if seq[n] < seq[n - 1]:
                seq[n - 1], seq[n] = seq[n], seq[n - 1]
    return seq

########NEW FILE########
__FILENAME__ = cocktail_sort
"""
    cocktail_sort.py

    Implementation of cocktail sort (aka bidirectional bubble sort,
    or the happy hour sort) on a list.

    Cocktail Sort Overview:
    ------------------------
    Walk the list bidirectionally, swapping neighbors if one should come
    before/after the other.

    Time Complexity: O(n**2)

    Space Complexity: O(1) Auxiliary

    Stable: Yes

    Psuedo Code: http://en.wikipedia.org/wiki/Cocktail_sort
"""


def sort(seq):
    lower_bound = -1
    upper_bound = len(seq) - 1
    swapped = True
    while swapped:
        swapped = False
        lower_bound += 1
        for i in range(lower_bound, upper_bound):
            if seq[i] > seq[i + 1]:
                seq[i], seq[i + 1] = seq[i + 1], seq[i]
                swapped = True
        if not swapped:
            break
        swapped = False
        upper_bound -= 1
        for i in range(upper_bound, lower_bound, -1):
            if seq[i] < seq[i - 1]:
                seq[i], seq[i - 1] = seq[i - 1], seq[i]
                swapped = True
    return seq

########NEW FILE########
__FILENAME__ = comb_sort
"""
    comb_sort.py

    Implementation of comb sort on a list and returns a sorted list.

    Comb Sort Overview:
    -------------------
    Improves on bubble sort by using a gap sequence to remove turtles.

    Time Complexity: O(n**2)

    Space Complexity: O(1) Auxiliary

    Stable: Yes

    Psuedo code: http://en.wikipedia.org/wiki/Comb_sort

"""


def sort(seq):
    gap = len(seq)
    swap = True

    while gap > 1 or swap:
        gap = max(1, int(gap / 1.25))
        swap = False
        for i in range(len(seq) - gap):
            if seq[i] > seq[i + gap]:
                seq[i], seq[i + gap] = seq[i + gap], seq[i]
                swap = True
    return seq

########NEW FILE########
__FILENAME__ = heap_sort
"""
    heap_sort.py

    Implementation of heap sort on a list and returns a sorted list.

    Heap Sort Overview:
    -------------------
    Uses the max heap data structure implemented in a list.

    Time Complexity: O(n log n)

    Space Complexity: O(1) Auxiliary

    Stable: Yes

    Psuedo Code: CLRS. Introduction to Algorithms. 3rd ed.

"""


def max_heapify(seq, i, n):
    l = 2 * i + 1
    r = 2 * i + 2

    if l <= n and seq[l] > seq[i]:
        largest = l
    else:
        largest = i
    if r <= n and seq[r] > seq[largest]:
        largest = r

    if largest != i:
        seq[i], seq[largest] = seq[largest], seq[i]
        max_heapify(seq, largest, n)


def build_heap(seq):
    n = len(seq) - 1
    for i in range(n/2, -1, -1):
        max_heapify(seq, i, n)


def sort(seq):
    build_heap(seq)
    heap_size = len(seq) - 1
    for x in range(heap_size, 0, -1):
        seq[0], seq[x] = seq[x], seq[0]
        heap_size = heap_size - 1
        max_heapify(seq, 0, heap_size)

    return seq

########NEW FILE########
__FILENAME__ = insertion_sort
"""
    insertion_sort.py

    Implemenation of insertion sort on a list and returns a sorted list.

    Insertion Sort Overview:
    ------------------------
    Uses insertion of elements in to the list to sort the list.

    Time Complexity: O(n**2)

    Space Complexity: O(n) total

    Stable: Yes

    Psuedo Code: CLRS. Introduction to Algorithms. 3rd ed.

"""


def sort(seq):
    for n in range(1, len(seq)):
        item = seq[n]
        hole = n
        while hole > 0 and seq[hole - 1] > item:
            seq[hole] = seq[hole - 1]
            hole = hole - 1
        seq[hole] = item
    return seq

########NEW FILE########
__FILENAME__ = merge_sort
"""
    merge_sort.py

    Implementation of merge sort on a list and returns a sorted list.

    Merge Sort Overview:
    ------------------------
    Uses divide and conquer to recursively divide and sort the list

    Time Complexity: O(n log n)

    Space Complexity: O(n) Auxiliary

    Stable: Yes

    Psuedo Code: CLRS. Introduction to Algorithms. 3rd ed.

"""


def merge(left, right):
    result = []
    n, m = 0, 0
    while n < len(left) and m < len(right):
        if left[n] <= right[m]:
            result.append(left[n])
            n += 1
        else:
            result.append(right[m])
            m += 1

    result += left[n:]
    result += right[m:]
    return result


def sort(seq):
    if len(seq) <= 1:
        return seq

    middle = len(seq) / 2
    left = sort(seq[:middle])
    right = sort(seq[middle:])
    return merge(left, right)

########NEW FILE########
__FILENAME__ = quick_sort
"""
    quick_sort.py

    Implementation of quick sort on a list and returns a sorted list.

    Quick Sort Overview:
    ------------------------
    Uses partitioning to recursively divide and sort the list

    Time Complexity: O(n**2) worst case

    Space Complexity: O(n**2) this version

    Stable: No

    Psuedo Code: CLRS. Introduction to Algorithms. 3rd ed.

"""


def sort(seq):

    if len(seq) < 1:
        return seq
    else:
        pivot = seq[0]
        left = sort([x for x in seq[1:] if x < pivot])
        right = sort([x for x in seq[1:] if x >= pivot])
        return left + [pivot] + right

########NEW FILE########
__FILENAME__ = quick_sort_in_place
"""
    quick_sort_in_place.py

    Implementation of quick sort on a list and returns a sorted list.
    In-place version.

    Quick Sort Overview:
    ------------------------
    Uses partitioning to recursively divide and sort the list

    Time Complexity: O(n**2) worst case

    Space Complexity: O(log n) this version

    Stable: No

    Psuedo Code: http://en.wikipedia.org/wiki/Quicksort#In-place_version

"""

def partition(seq, left, right, pivot_index):
    pivot_value = seq[pivot_index]
    seq[pivot_index], seq[right] = seq[right], seq[pivot_index]
    store_index = left
    for i in range( left, right ):
        if seq[i] < pivot_value:
            seq[i], seq[store_index] = seq[store_index], seq[i]
            store_index += 1
    seq[store_index], seq[right] = seq[right], seq[store_index]
    return store_index

def sort(seq, left, right):
    """in-place version of quicksort"""
    from random import randrange
    if len(seq) <= 1:
        return seq
    elif left < right:
        #pivot = (left+right)/2
        pivot = randrange(left, right)
        pivot_new_index = partition(seq, left, right, pivot)
        sort(seq, left, pivot_new_index - 1)
        sort(seq, pivot_new_index + 1, right)
        return seq

########NEW FILE########
__FILENAME__ = selection_sort
"""
    selection_sort.py

    Implementation of selection sort on a list and returns a sorted list.

    Selection Sort Overview:
    ------------------------
    Uses in-place comparision to sort the list

    Time Complexity:  O(n**2)

    Space Complexity: O(1) Auxiliary

    Stable: Yes

    Psuedo Code: http://en.wikipedia.org/wiki/Selection_sort

"""


def sort(seq):

    for i in range(0, len(seq)):
        minat = i
        minum = seq[i]
        for j in range(i + 1, len(seq)):
            if minum > seq[j]:
                minat = j
                minum = seq[j]
        temp = seq[i]
        seq[i] = seq[minat]
        seq[minat] = temp

    return seq

########NEW FILE########
__FILENAME__ = shell_sort
"""
    shell_sort.py

    Implementation of shell sort on an list and returns a sorted list.

    Shell Sort Overview:
    ------------------------
    Comparision sort that sorts far away elements first to sort the list

    Time Complexity:  O(n**2)

    Space Complexity: O(1) Auxiliary

    Stable: Yes

    Psuedo Code: http://en.wikipedia.org/wiki/Shell_sort

"""


def sort(seq):

    gaps = [x for x in range(len(seq) / 2, 0, -1)]

    for gap in gaps:
        for i in range(gap, len(seq)):
            temp = seq[i]
            j = i
            while j >= gap and seq[j - gap] > temp:
                seq[j] = seq[j - gap]
                j -= gap
            seq[j] = temp

    return seq

########NEW FILE########
__FILENAME__ = test_math
import unittest
from ..math.extended_gcd import extended_gcd


class TestExtendedGCD(unittest.TestCase):

    def test_extended_gcd(self):
        # Find extended_gcd of 35 and 77
        (a, b) = extended_gcd(35, 77)
        self.assertIs(35 * a + 77 * b, 7)

        # Find extended_gcd of 15 and 19
        (a, b) = extended_gcd(15, 19)
        self.assertIs(15 * a + 19 * b, 1)

        # Find extended_gcd of 18 and 9
        (a, b) = extended_gcd(18, 9)
        self.assertIs(18 * a + 9 * b, 9)

        # Find extended_gcd of 99 and 81
        (a, b) = extended_gcd(99, 81)
        self.assertIs(99 * a + 81 * b, 9)

        # Find extended_gcd of 50 and 15
        (a, b) = extended_gcd(50, 15)
        self.assertIs(50 * a + 15 * b, 5)

########NEW FILE########
__FILENAME__ = test_random
import unittest
from ..random import mersenne_twister


class TestMersenneTwister(unittest.TestCase):
    """
    Tests Mersenne Twister values for several seeds comparing against
    expected values from C++ STL's Mersenne Twister implementation
    """
    
    def test_mersenne_twister(self):
        mt = mersenne_twister.MersenneTwister()

        #Test seed 1
        mt.seed(1)
        self.expected = [1791095845, 4282876139, 3093770124,
                         4005303368, 491263, 550290313, 1298508491,
                         4290846341, 630311759, 1013994432]
        self.results = []
        for i in range(10):
            self.results.append(mt.randint())
        self.assertEqual(self.expected, self.results)

        #Test seed 42
        mt.seed(42)
        self.expected = [1608637542, 3421126067, 4083286876,
                         787846414, 3143890026, 3348747335,
                         2571218620, 2563451924, 670094950, 1914837113]
        self.results = []
        for i in range(10):
            self.results.append(mt.randint())
        self.assertEqual(self.expected, self.results)

        #Test seed 2147483647
        mt.seed(2147483647)
        self.expected = [1689602031, 3831148394, 2820341149,
                         2744746572, 370616153, 3004629480,
                         4141996784, 3942456616, 2667712047, 1179284407]
        self.results = []
        for i in range(10):
            self.results.append(mt.randint())
        self.assertEqual(self.expected, self.results)

        #Test seed -1
        #Hex is used to force 32-bit -1
        mt.seed(0xffffffff)
        self.expected = [419326371, 479346978, 3918654476,
                         2416749639, 3388880820, 2260532800,
                         3350089942, 3309765114, 77050329, 1217888032]
        self.results = []
        for i in range(10):
            self.results.append(mt.randint())
        self.assertEqual(self.expected, self.results)

########NEW FILE########
__FILENAME__ = test_searching
""" Unit Tests for searching """
import unittest
from ..searching import binary_search, kmp_search, rabinkarp_search, bmh_search, depth_first_search


class TestBinarySearch(unittest.TestCase):
    """
    Tests Binary Search on a small range from 0-9
    """

    def test_binarysearch(self):
        self.seq = range(10)
        rv1 = binary_search.search(self.seq, 0)
        rv2 = binary_search.search(self.seq, 9)
        rv3 = binary_search.search(self.seq, -1)
        rv4 = binary_search.search(self.seq, 10)
        rv5 = binary_search.search(self.seq, 4)
        self.assertIs(rv1, 0)
        self.assertIs(rv2, 9)
        self.assertFalse(rv3)
        self.assertFalse(rv4)
        self.assertIs(rv5, 4)
        self.seq = range(9)
        rv1 = binary_search.search(self.seq, 0)
        rv2 = binary_search.search(self.seq, 8)
        rv3 = binary_search.search(self.seq, -1)
        rv4 = binary_search.search(self.seq, 10)
        rv5 = binary_search.search(self.seq, 4)
        self.assertIs(rv1, 0)
        self.assertIs(rv2, 8)
        self.assertFalse(rv3)
        self.assertFalse(rv4)
        self.assertIs(rv5, 4)

class TestKMPSearch(unittest.TestCase):
    """
    Tests KMP search on string "ABCDE FG ABCDEABCDEF"
    """

    def test_kmpsearch(self):
        self.string = "ABCDE FG ABCDEABCDEF"
        rv1 = kmp_search.search(self.string, "ABCDEA")
        rv2 = kmp_search.search(self.string, "ABCDER")
        self.assertIs(rv1[0], 9)
        self.assertFalse(rv2)


class TestRabinKarpSearch(unittest.TestCase):
    """
    Tests Rabin-Karp search on string "ABCDEFGHIJKLMNOP"
    """

    def test_rabinkarpsearch(self):
        self.string = "ABCDEFGHIJKLMNOP"
        rv1 = rabinkarp_search.search(self.string, "MNOP")
        rv2 = rabinkarp_search.search(self.string, "BCA")
        self.assertIs(rv1[0], 12)
        self.assertFalse(rv2)


class TestBMHSearch(unittest.TestCase):
    """
    Tests BMH search on string "ABCDE FG ABCDEABCDEF"
    """

    def test_bmhsearch(self):
        self.string = "ABCDE FG ABCDEABCDEF"
        rv1 = bmh_search.search(self.string, "ABCDEA")
        rv2 = bmh_search.search(self.string, "ABCDER")
        self.assertIs(rv1[0], 9)
        self.assertFalse(rv2)

class TestDepthFirstSearch(unittest.TestCase):
    """
    Tests DFS on a graph represented by a adjacency list
    """

    def test_dfs(self):
        self.graph = {'A': ['B','C','E'],
                      'B': ['A','D','F'],
                      'C': ['A','G'],
                      'D': ['B'],
                      'F': ['B'],
                      'E': ['A'],
                      'G': ['C']}
        rv1 = depth_first_search.dfs(self.graph, "A")
        rv2 = depth_first_search.dfs(self.graph, "G")
        rv1e = depth_first_search.dfs(self.graph, "Z")
        self.assertEqual(rv1, ['A', 'B', 'D', 'F', 'C', 'G', 'E'])
        self.assertEqual(rv2, ['G', 'C', 'A', 'B', 'D', 'F', 'E'])
        self.assertEqual(rv1e, None)
        self.graph = {1:[2,3,4],
                      2:[1,6,10],
                      3:[1,5,10],
                      4:[1,10,11],
                      5:[3,10],
                      6:[2,7,8,9],
                      7:[6,8],
                      8:[6,7],
                      9:[6,10],
                      10:[3,5,9,12],
                      11:[4],
                      12:[10]}
        rv3 = depth_first_search.dfs(self.graph,1)
        rv4 = depth_first_search.dfs(self.graph,5)
        rv5 = depth_first_search.dfs(self.graph,6)
        rv2e = depth_first_search.dfs(self.graph,99)
        self.assertEqual(rv3, [1, 2, 6, 7, 8, 9, 10, 3, 5, 12, 4, 11])
        self.assertEqual(rv4, [5, 3, 1, 2, 6, 7, 8, 9, 10, 12, 4, 11])
        self.assertEqual(rv5, [6, 2, 1, 3, 5, 10, 9, 12, 4, 11, 7, 8])
        self.assertEqual(rv2e, None)
        self.graph = {1:[2,3,4,5,6],
                     2:[1,4,7,8,9],
                     3:[1,10],
                     4:[1,2,11,12],
                     5:[1,13,14,15],
                     6:[1,15],
                     7:[2],
                     8:[2],
                     9:[2,10],
                     10:[3,9],
                     11:[4],
                     12:[4],
                     13:[5],
                     14:[5],
                     15:[5,6]}
        rv6 = depth_first_search.dfs(self.graph,1)
        rv7 = depth_first_search.dfs(self.graph,10)
        rv8 = depth_first_search.dfs(self.graph,5)
        rv3e = depth_first_search.dfs(self.graph,-1)
        self.assertEqual(rv6, [1, 2, 4, 11, 12, 7, 8, 9, 10, 3, 5, 13, 14, 15, 6])
        self.assertEqual(rv7, [10, 3, 1, 2, 4, 11, 12, 7, 8, 9, 5, 13, 14, 15, 6])
        self.assertEqual(rv8, [5, 1, 2, 4, 11, 12, 7, 8, 9, 10, 3, 6, 15, 13, 14])
        self.assertEqual(rv3e, None)

########NEW FILE########
__FILENAME__ = test_shuffling
import unittest
from ..shuffling import knuth


class ShufflingAlgorithmTestCase(unittest.TestCase):
    """
    Shared code for shuffling unit tests.
    """

    def setUp(self):
        self.sorted = range(10)


class TestKnuthShuffle(ShufflingAlgorithmTestCase):
    """
    Tests Knuth shuffle on a small range from 0-9
    """
    def test_knuthshuffle(self):
        self.shuffle = knuth.shuffle(range(10))
        self.not_shuffled = 0

        for i in self.sorted:
            if i == self.shuffle[i]:
                self.not_shuffled = self.not_shuffled + 1

        self.assertGreater(5, self.not_shuffled)

########NEW FILE########
__FILENAME__ = test_sorting
import random
import unittest
from ..sorting import bubble_sort, selection_sort, insertion_sort, \
    merge_sort, quick_sort, heap_sort, shell_sort, comb_sort, cocktail_sort, \
    quick_sort_in_place


class SortingAlgorithmTestCase(unittest.TestCase):
    """
    Shared code for a sorting unit test.
    """

    def setUp(self):
        self.input = range(10)
        random.shuffle(self.input)
        self.correct = range(10)


class TestBubbleSort(SortingAlgorithmTestCase):
    """
    Tests Bubble sort on a small range from 0-9
    """

    def test_bubblesort(self):
        self.output = bubble_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestSelectionSort(SortingAlgorithmTestCase):
    """
    Tests Selection sort on a small range from 0-9
    """

    def test_selectionsort(self):
        self.output = selection_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestInsertionSort(SortingAlgorithmTestCase):
    """
    Tests Insertion sort on a small range from 0-9
    """

    def test_selectionsort(self):
        self.output = insertion_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestMergeSort(SortingAlgorithmTestCase):
    """
    Tests Merge sort on a small range from 0-9
    also tests merge function included in merge sort
    """

    def test_mergesort(self):
        self.output = merge_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)

    def test_merge(self):
        self.seq1 = range(0, 5)
        self.seq2 = range(5, 10)
        self.seq = merge_sort.merge(self.seq1, self.seq2)
        self.assertIs(self.seq[0], 0)
        self.assertIs(self.seq[-1], 9)


class TestQuickSort(SortingAlgorithmTestCase):
    """
    Test Quick sort on a small range from 0-9
    """

    def test_quicksort(self):
        self.output = quick_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestQuickSortInPlace(SortingAlgorithmTestCase):
    """
    Tests Quick sort in place version on a small range from 0-9
    also tests partition function included in quick sort
    """
    def test_quicksort_in_place(self):
        self.output = quick_sort_in_place.sort(self.input, 0,
                len(self.input)-1)
        self.assertEqual(self.correct, self.output)

    def test_partition(self):
        self.seq = range(10)
        self.assertIs(quick_sort_in_place.partition(self.seq, 0,
            len(self.seq)-1, 5), 5)


class TestHeapSort(SortingAlgorithmTestCase):
    """
    Test Heap sort on a small range from 0-9
    """

    def test_heapsort(self):
        self.output = heap_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestShellSort(SortingAlgorithmTestCase):
    """
    Test Shell sort on a small range from 0-9
    """

    def test_shellsort(self):
        self.output = shell_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestCombSort(SortingAlgorithmTestCase):
    """
    Test Comb sort on a small range from 0-9
    """

    def test_combsort(self):
        self.output = comb_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)


class TestCocktailSort(SortingAlgorithmTestCase):
    """
    Tests Cocktail sort on a small range from 0-9
    """

    def test_cocktailsort(self):
        self.output = cocktail_sort.sort(self.input)
        self.assertEqual(self.correct, self.output)

########NEW FILE########
__FILENAME__ = run_tests
import nose

if __name__ == '__main__':
    nose.main()

########NEW FILE########
