__FILENAME__ = alphabetical_substring
#!/usr/bin/env python
''' 
Alphabetical substring

Input: string
Output: the sub string that has the most characters in a row that are in alphabetical order. If there is a tie then print the first occurance.

Pulled from edx CompSci 101

'''

def alphabetical_substring(s):
    substring = {}
    max_value = 0

    for i in range(len(s)):
        count = 0
        sub_value  = s[i]

        while i+1 < len(s) and s[i] <= s[i+1]:
            count += 1
            i += 1
            sub_value += s[i]

        substring[count] = substring.get(count, sub_value)
        max_value = max(substring.keys())
    
    return substring[max_value]
    # print('Longest substring in alphabetical order is: %s' % substring[max_value])

if __name__ == '__main__':
    #Test section
    input_case = ['azcbobobegghakl', 'abcdefghijklmnopqrstuvwxyz', 'nqlkcvjkwytg', 'bovgfeiromsncq']
    ans = ['beggh', 'abcdefghijklmnopqrstuvwxyz', 'jkwy', 'bov']

    for i in range(len(input_case)):
        print('Expected input = %s and output = %s which is %s' % (input_case[i], ans[i], ans[i] == alphabetical_substring(input_case[i])))

########NEW FILE########
__FILENAME__ = anagram
#!/usr/bin/env python
"""
Anagram 
(A word, phrase, or name formed by rearranging the letters of anothe)

Give a list of strings, return a list of anagram sets just from the original input.

Example:
    Input: ['cat', 'tablet', 'wolf', 'act', 'battle', 'flow', 'batlet', 'food']
    Output: [['cat', 'act'], ['tablet', 'battle', 'batlet'], ['wolf', 'flow']]

Note: It does not generate any new words that are not in the input.

Original problem/solution submission from claudiay
"""

def anagram(words):
    results = []
    matches = {}

    # Create a dict with sorted values as key, and list of original strings as
    # the value.
    for word in words:
        key = ''.join(sorted(list(word)))
        if matches.get(key, False):
            matches[key].append(word)
        else:
            matches[key] = [word]

    #Creates result list of lists 
    for k, v in matches.items():
        if len(v) >= 2:
            results.append(v)

    return results


def anagram2(words):
    matches = {}

    # Create a dict with sorted values as key, and list of original strings as
    # the value.
    for word in words:
        key = ''.join(sorted(list(word)))
        if matches.get(key, False):
            matches[key].append(word)
        else:
            matches[key] = [word]

    #Pops value from dict if not more than 1 and returns dictionary values
    for k, v in matches.items():
        if len(v) <= 1:
            matches.pop(k, None)

    return matches.values()

if __name__ == '__main__':

    #Test section
    implementations = [anagram,anagram2]

    words_input = ['cat', 'tablet', 'wolf', 'act', 'battle', 'flow', 'batlet', 'food']
    result = [['tablet', 'battle', 'batlet'], ['wolf', 'flow'], ['cat', 'act']]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s) returns %s: %s" % (words_input,result,(impl(words_input) == result))




########NEW FILE########
__FILENAME__ = bfs
#!/usr/bin/env python
'''
Breadth First Search

Input: tree and value to search for

Output: Breadth first search for a specified value in tree
'''


class Node():

    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

    def bfs(n, person):
        tree = []
        tree.append(n)
        ans = False
        while tree:
            n = tree.pop(0)
            if person == n.val:
                ans = True
            else:
                if n.left:
                    tree.append(n.left)
                if n.right:
                    tree.append(n.right)
        return ans


# Run, build & test the tree
if __name__ == '__main__':
    # Build out the tree.
    n = Node('Lola')
    n2 = Node('Ann')
    n3 = Node('Rose')
    n4 = Node('Janice')
    n5 = Node('Harriet')
    n6 = Node('Louis')
    n7 = Node('Gertrude')

    n.left = n2
    n.right = n3
    n.right.left = n4
    n.right.right = n5
    n.left.left = n6
    n.left.right = n7

  # Test section
    implementations = [n.bfs]

    person_search = 'Louis'
    person_search2 = 'George'

    result = True
    result2 = False

    for impl in implementations:
        print "trying %s" % impl
        print " f(%s) exists: %s" % (person_search, impl(person_search) == result)
        print " f(%s) does not exist: %s" % (person_search2, impl(person_search2) == result2)

########NEW FILE########
__FILENAME__ = bft
#!/usr/bin/env python
'''
Breadth First Traversal

Input: binary tree
Output: printing out results of the tree by traversing the tree.
'''


class Node():

    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

    # Prints each value moving across each layer. O(n)
    def bft(self):
        q = []
        ans = []
        q.append(self)
        while q:
            n = q.pop(0)
            ans.append(n.val)
            if n.left:
                q.append(n.left)
            if n.right:
                q.append(n.right)
        return ' '.join(ans)

    # Prints each level on a separate line. O(n)
    def bft2(self):
        q = []
        q2 = []
        ans = []
        q.append(self)
        while q:
            n = q.pop(0)
            ans.append(n.val)
            if n.left:
                q2.append(n.left)
            if n.right:
                q2.append(n.right)
            if len(q) == 0:
                q = q2
                q2 = []
                ans.append('\n')
        return ' '.join(ans)

    # Variation that prints one line breadth. O(n)
    def bft3(self):
        parent = [self]
        ans = []
        while parent:
            children = []
            for i, node in enumerate(parent):
                ans.append(node.val)
                if node.left:
                    children.append(node.left)
                if node.right:
                    children.append(node.right)
            parent = children
        return ' '.join(ans)


# Run, build & test the tree.
if __name__ == '__main__':
    # Build out the tree.
    n = Node('Lola')
    n2 = Node('Ann')
    n3 = Node('Rose')
    n4 = Node('Janice')
    n5 = Node('Harriet')
    n6 = Node('Louis')
    n7 = Node('Gertrude')

    n.left = n2
    n.right = n3
    n.right.left = n4
    n.right.right = n5
    n.left.left = n6
    n.left.right = n7

    # Test section. Split implementations since results are different.
    implementations = [n.bft, n.bft3]
    implementations2 = [n.bft2]

    result1 = 'Lola Ann Rose Louis Gertrude Janice Harriet'
    result2 = 'Lola \n Ann Rose \n Louis Gertrude Janice Harriet \n'

    for impl in implementations:
        print "trying %s" % impl
        print " f(tree) == %s: %s" % (result1, impl() == result1)

    for impl in implementations2:
        print "trying %s" % impl
        print " f(tree) == %s: %s" % (result2, impl() == result2)

########NEW FILE########
__FILENAME__ = bisection_guess
print("Please think of a number between 0 and 100!")
ans = 'n'
start = 0
end = 100

while True:
    guess = (start+end)/2

    print("Is your secret number %s?" % guess) 
    
    ans = raw_input("Enter 'h' to indicate the guess is too high. Enter 'l' to indicate the guess is too low. Enter 'c' to indicate I guessed correctly.")

    if ans == 'c':
        print("Game over. Your secret number was: %d" % guess)
        break
    elif ans == 'h':
        end = guess
        lastguess = -guess
    elif ans == 'l':
        start = guess
        lastguess = guess
    else: 
        print("Sorry, I did not understand your input")

########NEW FILE########
__FILENAME__ = chess_board
#!/usr/bin/env python
'''
Chess Board

Input: draw_white and draw_black functions exist to draw the squares

Output:
Draw a chess board that is 8 x 8 but the better solution will be flexible in size.

Trick: When drawn out, the numbers on a grid are both even or both odd then they are the same color.

'''

# Basic nested loop implementation


def draw_board(n):
    for i in range(8):
        for j in range(8):
            if (i % 2 == 0 and j % 2 == 0) or (i % 2 != 0 and j % 2 != 0):
                draw_white()
            else:
                draw_black()

# Split funciotn and nested conditionals


def is_even(c):
    return c % 2 == 0


def draw_board2(n):
    for row in range(n):
        for column in range(n):
            if is_even(row):
                if is_even(column):
                    draw_white()
                else:
                    draw_black()
            else:
                if is_even(column):
                    draw_black()
                else:
                    draw_white()


# micro-optimizing to show off nested list comprehensions. - jdunck
#  in the 1st row, make the odd checks black.
#  in the 2nd row, make the even checks black.
def draw_board3(n):
    boxes = [(i, j) for i in range(n) for j in range(n)]
    for box in boxes:
        if is_even(box[0] + box[1]):
            draw_white()
        else:
            draw_black()

########NEW FILE########
__FILENAME__ = count_occurances
#!/usr/bin/env python
''' 
String Count

Input: string or array
Output: Highest count of occurances of letters in a string OR count of numbers in a list given a target OR count of occurances of a substring in a full string.

'''

# Count string letters in unsorted string - O(n)
def high_occ(string):
    letter_dict = {}
    high_value = 0
    for i in string:
        letter_dict[i] = letter_dict.get(i, 0) + 1
    for key, value in letter_dict.iteritems():
        if value > high_value:
            high_value = value
    return high_value


# Count numbers in a list
def list_count(num_list, n):
    count = 0
    if len(num_list) <= 1 and num_list[0] == n:
        count += 1      
    if n in num_list and len(num_list) > 1:
        pivot = int(len(num_list)/2)
        if num_list[pivot] == n:
            count += 1
            if num_list[pivot+1] == n:
                count += 1
            if num_list[pivot-1] == n:
                count += 1
        if num_list[pivot] > n:
            count += list_count(num_list[:pivot], n)
        if num_list[pivot] < n:
            count += list_count(num_list[pivot+1:], n)
    return count

#Simple solution for count numbers - O(n)
def list_count2(num_list, n):
    return num_list.count(n)

#O(n)
def list_count3(num_list, n):
    num_counts = dict((num, num_list.count(n)) for num in num_list)
    return num_counts[n]


# O(n^2) - Counting how often a sub-string appears in a full_string
def count_substr(full_string, str_match):
    num = 0
    for i, letter in enumerate(full_string):
        if letter == str_match[0]:
            j = 0
            match_case = True
            while match_case:
                if j == 3:
                    num += 1
                    match_case = False
                elif str_match[j] == full_string[i]:
                    i += 1
                    j += 1
                    if i < len(full_string):
                        continue
                    else:
                        i -= 1
                else:
                    match_case = False
    print("Number of times bob occurs is: %d" % num)
    return num

# O(n)
def count_substr2(full_string, str_match):
    occurance = 0
    for i in range(1, len(full_string)-1):
        if full_string[i-1:i+(len(str_match)-1)] == str_match:
            occurance += 1
    print 'Number of times bob occurs is:', occurance
    return occurance


# Trying something with boyers here - in progress
# def count_substr(full_string, str_match):
#     occurance = 0
#     for i in range(len(full_string),1,-len(str_match)):
#         if str_match[i]==match[-1]:
#             if full_string[i-(len(str_match)-1):i] == str_match:
#                 occurance += 1
#         elif str_match[i] in match:
#     print 'Number of times bob occurs is:', occurance
#     return ocurrance

if __name__ == '__main__':
    #Test section
    implementations = [list_count,list_count2,list_count3]
    implementations2 = [count_substr, count_substr2]
    num_list = [2,4,5,5,5,6,7]


    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s, 7) == 1: %s" % (num_list, (impl(num_list,7) == 1))
        print "  f(%s, 5) == 3: %s" % (num_list, (impl(num_list,5) == 3))

    print "f(%s) == %s : %s" % ('hello world', 3, (high_occ('hello world') == 3))

    for impl in implementations2:
        print "trying %s" % impl
        print("count_substr('pupbhb', 'bob') == 0: %s") % ( impl('pupbhb', 'bob') == 0)
        print("count_substr('bobbobooflubobbbobobbobbbobbwwboobcbobbbobobcboob', 'bob') == 10: %s") % (impl('bobbobooflubobbbobobbobbbobbwwboobcbobbbobobcboob', 'bob') == 10)
        print("count_substr('mtbobbboboba', 'bob') == 3: %s") % ( impl('mtbobbboboba', 'bob') == 3)

########NEW FILE########
__FILENAME__ = deviation
#!/usr/bin/env python
'''
Deviation Problem

Input: list of integer elements and an integer (length of sequences)

Consider all the sequences of consecutive elements in the list.For each sequence, compute the difference between the maximum and the minimum value of the elements in that sequence and name it the deviation.

Output: Write a function that computes and returns the maximum value among the deviations of all the sequences

Constraints:
* List contains up to 100,000 elements.
* All the elements are integer numbers in the range: [1, 231 -1]
* Return in less than 2 seconds

Example: The sequences of length 3 are...

    6 9 4 having the median 5 (the minimum value in the sequence is 4 and the maximum is 9)
    9 4 7 having the median 5 (the minimum value in the sequence is 4 and the maximum is 9)
    7 4 1 having the median 6 (the minimum value in the sequence is 1 and the maximum is 7)
    The maximum value among all medians is 6

Expand: For negative numbers and/or odd sements
'''

# O(nm)


def max_deviation(int_list, seq_len):
    marker = 0
    dev_list = []

    while marker < len(int_list):
        segment = int_list[marker:marker + seq_len]
        dev_list.append(max(segment) - min(segment))
        marker += seq_len
    return max(dev_list)

# Looping based on size of segment. - O(n)


def max_deviation2(int_list, seq_len):
    dev_list = []

    num_seg = int(len(int_list) / (seq_len))

    marker = 0

    for i in range(0, num_seg):
        segment = int_list[marker:marker + seq_len]
        dev_list.append(max(segment) - min(segment))
        marker += seq_len

    return max(dev_list)


# Let's define N as the length of the overall sequence and M is the length of the subsequence.
#
# In a simple approach, where we build a subsequence for each part, we will build O(N/M) subsequences.
# We will then run max() and min() (which are O(M)) N/M times, so the runtime of this implementation is O(N).
#
# Just knocking this out, pythonically and not worrying about the performance too much:
# Memory (e.g. space complexity) is O(n).
def max_deviation3(int_list, seq_len):
    last_start_bound = 1 + len(int_list) - seq_len
    subseqs = [int_list[i:i + seq_len]
               for i in range(0, last_start_bound, seq_len)]
    deviations = [(max(subseq) - min(subseq)) for subseq in subseqs]
    return max(deviations)


# We can improve slightly by switching to generators so we don't materialize all the
# intermediate structures until needed: (This has the same runtime
# complexity, but uses less memory.) Space complexity is O(n) and memory
# is O(N/M).
def max_deviation4(int_list, seq_len):
    last_start_bound = 1 + len(int_list) - seq_len
    subseqs = (int_list[i:i + seq_len]
               for i in xrange(0, last_start_bound, seq_len))
    deviations = ((max(subseq) - min(subseq)) for subseq in subseqs)
    return max(deviations)

if __name__ == '__main__':
    # Test section
    implementations = [
        max_deviation, max_deviation2, max_deviation3, max_deviation4]
    int_list = [1, 2, 3, 4, 5, 6]
    seq_len = 2
    result = 1

    int_list2 = [6, 9, 4, 9, 4, 7, 7, 4, 1]
    seq_len2 = 3
    result2 = 6

    int_list3 = [1, 2, 3, 4, 5, 6]
    seq_len3 = 5
    result3 = 4


    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s, %s) == %s: %s" % (int_list, seq_len, result, (impl(int_list, seq_len) == result))
        print "  f(%s, %s) == %s: %s" % (int_list2, seq_len2, result2, (impl(int_list2, seq_len2) == result2))
        print "  f(%s, %s) == %s: %s" % (int_list3, seq_len3, result3, (impl(int_list3, seq_len3) == result3))

########NEW FILE########
__FILENAME__ = dfs
#!/usr/bin/env python
'''
Depth First Search (DFS)

Input: tree of names and search for existance of one name
Output: true or false if the name is found

'''


class Node():

    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

    def add(value):
        pass  # handle adding nodes
    # Recursive solution - O(n)

    def dfs(self, person):
        if not self.val:
            return False
        else:
            if self.val == person:
                return True
            else:
                if self.left:
                    return self.left.dfs(person)
                if self.right:
                    return self.right.dfs(person)

if __name__ == '__main__':

    # Build out the tree.
    n = Node('Lola')
    n2 = Node('Ann')
    n3 = Node('Rose')
    n4 = Node('Janice')
    n5 = Node('Harriet')
    n6 = Node('Louis')
    n7 = Node('Gertrude')

    n.left = n2
    n.right = n3
    n.right.left = n4
    n.right.right = n5
    n.left.left = n6
    n.left.right = n7

    # Test section
    implementations = [n.dfs]

    person_search = 'Louis'
    person_search2 = 'George'

    result = True
    result2 = False

    for impl in implementations:
        print "trying %s" % impl
        print " f(%s) == %s: %s" % (person_search, person_search, impl(person_search) == result)
        print " f(%s) == %s: %s" % (person_search2, person_search2, impl(person_search2) == result2)

########NEW FILE########
__FILENAME__ = dft
#!/usr/bin/env python
'''
Depth First Traversal

Input: Create tree
Output: Print each value on each node traversing the tree by depth and from the left first

'''

class Node():

    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

    # Recursive solution and method leverages string results holder for
    # results - list is an alternative - O(n)
    def dft(n):
        hold = ''
        if not n:
            return
        else:
            hold = '%s ' % n.val
            if n.left:
                hold += '%s' % n.left.dft()
            if n.right:
                hold += '%s' % n.right.dft()

        return hold

if __name__ == '__main__':

    # Build out the tree.
    n = Node('Lola')
    n2 = Node('Ann')
    n3 = Node('Rose')
    n4 = Node('Janice')
    n5 = Node('Harriet')
    n6 = Node('Louis')
    n7 = Node('Gertrude')

    n.left = n2
    n.right = n3
    n.right.left = n4
    n.right.right = n5
    n.left.left = n6
    n.left.right = n7

    # Test section
    implementations = [n.dft]

    result = 'Lola Ann Louis Gertrude Rose Janice Harriet '

    for impl in implementations:
        print "trying %s" % impl
        print " f(tree) == %s: %s" % (result, impl() == result)

########NEW FILE########
__FILENAME__ = diagonals
'''
Matrix diagonals

Input: Matrix / List of Lists 
Output: Print diagonals

Input Example:

[[1, 2, 8],
 [-4, 5, 2],
 [0, -4, -6],
 [-3, 3, 9]]

Output Example:
8
2 2
1 5 -6
-4 -4 9
0 3
-3


NumPy solution initially from: http://stackoverflow.com/questions/6313308/get-all-the-diagonals-in-a-matrix-list-of-lists-in-python
'''


# List of lists solution

def diag(size):
    return [(i, i) for i in range(size)]

def is_in_matrix(matrix, pair):
    return 0 <= pair[0] < matrix[0] and 0 <= pair[1] < matrix[1]

def transpose(ray, amount):
    return [(x-amount, y) for (x,y) in ray]

def diagonals(h, w):
    for offset in reversed(range(-w, h-1)):
        diagonal = [p for p in transpose(diag(6), offset) if is_in_matrix([h, w], p)]
        if diagonal:
            print diagonal


# NumPy Solution
import numpy as np

matrix = np.array(
         [[-2,  5,  3,  2],
          [ 9, -6,  5,  1],
          [ 3,  2,  7,  3],
          [-1,  8, -4,  8]])

diags = [matrix[::-1,:].diagonal(i) for i in range(-3,4)]
diags.extend(matrix.diagonal(i) for i in range(3,-4,-1))
print [n.tolist() for n in diags]

import numpy as np

# Alter dimensions as needed
x,y = 3,4

# create a default array of specified dimensions
a = np.arange(x*y).reshape(x,y)
print a
print

# a.diagonal returns the top-left-to-lower-right diagonal "i"
# according to this diagram:
#
#  0  1  2  3  4 ...
# -1  0  1  2  3
# -2 -1  0  1  2
# -3 -2 -1  0  1
#  :
#
# You wanted lower-left-to-upper-right and upper-left-to-lower-right diagonals.
#
# The syntax a[slice,slice] returns a new array with elements from the sliced ranges,
# where "slice" is Python's [start[:stop[:step]] format.

# "::-1" returns the rows in reverse. ":" returns the columns as is,
# effectively vertically mirroring the original array so the wanted diagonals are
# lower-right-to-uppper-left.
#
# Then a list comprehension is used to collect all the diagonals.  The range
# is -x+1 to y (exclusive of y), so for a matrix like the example above
# (x,y) = (4,5) = -3 to 4.
diags = [a[::-1,:].diagonal(i) for i in range(-a.shape[0]+1,a.shape[1])]

# Now back to the original array to get the upper-left-to-lower-right diagonals,
# starting from the right, so the range needed for shape (x,y) was y-1 to -x+1 descending.
diags.extend(a.diagonal(i) for i in range(a.shape[1]-1,-a.shape[0],-1))

# Another list comp to convert back to Python lists from numpy arrays,
# so it prints what you requested.
print [n.tolist() for n in diags]
########NEW FILE########
__FILENAME__ = double_linked_list
'''
Double Linked List

In a doubly linked list, each element has the property that if element A has a "before" link to element B, then element B has an "after" link to element A

Provide a definition for an insert function that will create an ordered doubly linked list. This function is defined outside of the class Frob, and takes two arguments: a Frob that is currently part of a doubly linked list, and a new Frob. The new Frob will not initially have any "before" or "after" links to other Frobs. The function should mutate the list to place the new Frob in the correct location, with the resulting doubly linked list having appropriate "before" and "after" links.

Note that if a Frob is inserted with the same name as a pre-existing Frob, both names should be inserted in the final data structure (the exact ordering of the two identical Frobs does not matter)

From MIT CS 101 online class. 

'''

class Frob(object):
    def __init__(self, name):
        self.name = name
        self.before = None
        self.after = None
    def setBefore(self, before):
        self.before = before
    def setAfter(self, after):
        self.after = after
    def getBefore(self):
        return self.before
    def getAfter(self):
        return self.after
    def myName(self):
        return self.name
    def __repr__(self):
        return self.myName()

def insert(atMe, newFrob):
    """
    atMe: a Frob that is part of a doubly linked list
    newFrob:  a Frob with no links
    This procedure appropriately inserts newFrob into the linked list that atMe is a part of.
    """

    def set_frob(middle_frob, before_frob=None, after_frob=None):
        if before_frob:
            middle_frob.setBefore(before_frob)
            before_frob.setAfter(middle_frob)        
        if after_frob:
            after_frob.setBefore(middle_frob)
            middle_frob.setAfter(after_frob)

    def find_first():
        temp_frob = atMe
        while temp_frob.getAfter():
            temp_frob = temp_frob.getAfter()
            if temp_frob.myName() >= newFrob.myName():
                return temp_frob.getBefore()
        return temp_frob

    def find_last():
        temp_frob = atMe
        while temp_frob.getBefore():
            temp_frob = temp_frob.getBefore()
            if temp_frob.myName() <= newFrob.myName():
                return temp_frob.getAfter()
        return temp_frob

    if atMe.myName() == newFrob.myName():
        set_frob(newFrob, atMe.getBefore(), atMe)

    elif atMe.myName() < newFrob.myName():
        before_val = find_first()
        set_frob(newFrob, before_val, before_val.getAfter())

    elif atMe.myName() > newFrob.myName():
        after_val = find_last()
        set_frob(newFrob, after_val.getBefore(), after_val)

if __name__ == '__main__':
    #Test section

    eric = Frob('eric')
    andrew = Frob('andrew')
    ruth = Frob('ruth')
    fred = Frob('fred')
    martha = Frob('martha')

    insert(eric, andrew)
    insert(eric, ruth)
    insert(eric, fred)
    insert(ruth, martha)
    insert(eric, Frob('martha'))

    def find_front(start):
        if start.getBefore():
            return find_front(start.getBefore())
        else:
            return start

    def show_tree(node):
        temp = node
        while temp:
            print temp
            temp = temp.getAfter()

    # Show the linked list 
    front = find_front(eric)
    show_tree(front) # andrew eric fred martha martha ruth



########NEW FILE########
__FILENAME__ = equal_prob
#!/usr/bin/env python
'''
Equal Probability

Input: string
Output: Shuffle the string to make sure that it returns an equal-probability

Example: For string of length n, you have n! permutations-- so the string you return should reflect 1/n! 

What I did was pick a random number between (i, n-1) and increment i until it reaches len(string)-1, then take that random index and swap it with the first character of the string. 

As you iterate, you only look at the slice of string (i: len(string)-1) because the swapped characters (ones in the front) have been used already, and shouldn't be touched again.
'''
########NEW FILE########
__FILENAME__ = extract_num
#!/usr/bin/env python
'''
Extract Number

Input: A list of dictionaries with text that includes time
Output: Strip the time out of the text, convert to time, calculate the average time and return the mean.

Challenge: Account for military time. Account for
'''
import re  # import regex

# Strip out time with Regex


def strip_time(string):
    str_time = re.search('\d+:\d+', string)
    if str_time:  # if it exists then return
        time_list = str_time.group().split(':')
        return time_list

# Convert time to int and calc mean


def get_mean(time_list):
    hours = minutes = 0
    for time in time_list:
        if time:
            hours += int(time[0])
            minutes += int(time[1])

    list_len = len(time_list)
    mean_hour = hours / list_len
    mean_min = minutes / list_len

    print 5, '%d:%d' % (mean_hour, mean_min)

    return '%d:%d' % (mean_hour, mean_min)

# Extract strings from list of dicts and conver to mean time


def dict_mean_time(list_dicts):
    time_list = []
    for dictionary in list_dicts:  # loop list
        for num, string in dictionary.items():  # loop dict
            if strip_time(string):  # confirm time exists
                time_list.append(strip_time(string))  # capture time list

    return get_mean(time_list)

if __name__ == '__main__':
    # Test section
    list_dicts = [{1: "hello at 9:30"}, {
        2: "night at 10:30", 3: "moon at 8:00"}, {0: "no"}]
    implementations = [dict_mean_time]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(list_dicts) == '9:20': %s" % (impl(list_dicts) == '9:20')

########NEW FILE########
__FILENAME__ = factorial
#!/usr/bin/env python
'''
Factorial

Input: Take in a number
Output: The factorial of a number (n!). The product of all positive integers less than or equal to a number.

'''

import math

 # Recursive solution

def rec_fact(n):
    if n == 0:
        return 1
    else:
        return (n * rec_fact(n - 1))

# While loop iteration solution - O(n)

def loop_sol_1(n):
    if n == 0:
        n = 1
    num = n
    while num > 1:
        num -= 1
        n *= num
    return n

# For loop iteration solution - O(n)

def loop_sol_2(n):
    if n == 0:
        n = 1
    for num in range(1, n):
        n *= num
    return n

# For loop containing full conditional - O(n)
def loop_sol_3(x):
    for num in range(0,x+1):
        if num < 2:
            result = num
        else:
            result *= num
    return result

 
# List comprehension solution - O(n)
def functional(n):
    return reduce(lambda x, y: x * y, [1] + range(1, n + 1))

# Math library solution
std_lib = math.factorial

if __name__ == '__main__':
    # Test section
    implementations = [std_lib, rec_fact, loop_sol_1, loop_sol_2, loop_sol_3, functional]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(0) == 1: %s" % (impl(0) == 1)
        print "  f(1) == 1: %s" % (impl(1) == 1)
        print "  f(2) == 2: %s" % (impl(2) == 2)
        print "  f(3) == 6: %s" % (impl(3) == 6)

########NEW FILE########
__FILENAME__ = family_tree
'''
Family Tree

This is an example of traversing the tree to get specific information. All information originally provided except cousin method.

Input: 
Class Member is a class that represents a single person in the family, and Class Family represents the whole family tree.


Output:
Write code for the method cousin of the class Family according to the docstring in FamilyTree.py and the definitions for degree removed and cousin type 

         A 
     |       |
     B       C
   |   |   |   |
   D   E   F   G
  | | | | | | | | | |
  H I J K L M N O Q R

Degree removed = How many levels different the nodes were on (e.g. node A is zeroth level and D is 2nd level they are two removed)

Cousin type = The node level that is the closest to a common parent/ancestor node. In general, i'th cousins have a grandparent or ancestor that is i levels up from their parents.  (e.g. B & C are zeroth cousins, D & G are 1st cousins, H & M are 2nd cousins)

Combined = D & M are 1st cousins 1 removed, B & L are zeroth cousins 2 removed.

From MIT CS 101 online class. 

'''

class Member(object):
    def __init__(self, founder):
        """ 
        founder: string
        Initializes a member. 
        Name is the string of name of this node,
        parent is None, and no children
        """        
        self.name = founder
        self.parent = None         
        self.children = []    

    def __str__(self):
        return self.name    

    def add_parent(self, mother):
        """
        mother: Member
        Sets the parent of this node to the `mother` Member node
        """
        self.parent = mother   

    def get_parent(self):
        """
        Returns the parent Member node of this Member
        """
        return self.parent 

    def is_parent(self, mother):
        """
        mother: Member
        Returns: Boolean, whether or not `mother` is the 
        parent of this Member
        """
        return self.parent == mother  

    def add_child(self, child):
        """
        child: Member
        Adds another child Member node to this Member
        """
        self.children.append(child)   

    def is_child(self, child):
        """
        child: Member
        Returns: Boolean, whether or not `child` is a
        child of this Member
        """
        return child in self.children 


class Family(object):
    def __init__(self, founder):
        """ 
        Initialize with string of name of oldest ancestor

        Keyword arguments:
        founder -- string of name of oldest ancestor
        """

        self.names_to_nodes = {}
        self.root = Member(founder)    
        self.names_to_nodes[founder] = self.root   

    def set_children(self, mother, list_of_children):
        """
        Set all children of the mother. 

        Keyword arguments: 
        mother -- mother's name as a string
        list_of_children -- children names as strings
        """
        # convert name to Member node (should check for validity)
        mom_node = self.names_to_nodes[mother]   
        # add each child
        for c in list_of_children:           
            # create Member node for a child   
            c_member = Member(c)               
            # remember its name to node mapping
            self.names_to_nodes[c] = c_member    
            # set child's parent
            c_member.add_parent(mom_node)        
            # set the parent's child
            mom_node.add_child(c_member)         
    
    def is_parent(self, mother, kid):
        """
        Returns True or False whether mother is parent of kid. 

        Keyword arguments: 
        mother -- string of mother's name
        kid -- string of kid's name
        """
        mom_node = self.names_to_nodes[mother]
        child_node = self.names_to_nodes[kid]
        return child_node.is_parent(mom_node)   

    def is_child(self, kid, mother):
        """
        Returns True or False whether kid is child of mother. 

        Keyword arguments: 
        kid -- string of kid's name
        mother -- string of mother's name
        """        
        mom_node = self.names_to_nodes[mother]   
        child_node = self.names_to_nodes[kid]
        return mom_node.is_child(child_node)

    def cousin(self, a, b):
        """
        Returns a tuple of (the cousin type, degree removed) 

        cousin type is an integer that is -1 if a and b
        are the same node or if one is the direct descendent 
        of the other.  Otherwise, cousin type is 0 or greater,
        representing the shorter distance to their common 
        ancestor as described in the exercises above.

        degree removed is the distance to the common ancestor

        Keyword arguments: 
        a -- string that is the name of a
        b -- string that is the name of b
        """
        
        ## YOUR CODE HERE ####
        a_node = self.names_to_nodes[a]
        b_node = self.names_to_nodes[b]

        def create_branch(node):
            branch = [node]
            parent = node.get_parent()

            while parent:
                branch.append(parent)
                parent = parent.get_parent()
            return branch

        if a_node.name == b_node.name:
            return (-1, 0)
        elif a_node.is_child(b_node) or b_node.is_child(a_node):
            return (-1, 0)

        a_branch = create_branch(a_node)
        b_branch = create_branch(b_node)

        b_parent_index = 0
        for a_parent_index, node in enumerate(a_branch):
            try:
                b_parent_index = b_branch.index(node)
                break
            except ValueError:
                pass

        cousin_type = max(a_parent_index, b_parent_index)
        degree_removed = abs(a_parent_index - b_parent_index)
        return (cousin_type, degree_removed)

if __name__ == '__main__':
    #Test section
    f = Family("a")
    f.set_children("a", ["b", "c"])
    f.set_children("b", ["d", "e"])
    f.set_children("c", ["f", "g"])

    f.set_children("d", ["h", "i"])
    f.set_children("e", ["j", "k"])
    f.set_children("f", ["l", "m"])
    f.set_children("g", ["n", "o", "p", "q"])

    words = ["zeroth", "first", "second", "third", "fourth", "fifth", "non"]

    ## These are your test cases. 

    ## The first test case should print out:
    ## 'b' is a zeroth cousin 0 removed from 'c'
    t, r = f.cousin("b", "c")
    print "'b' is a", words[t],"cousin", r, "removed from 'c'"

    ## For the remaining test cases, use the graph to figure out what should 
    ## be printed, and make sure that your code prints out the appropriate values.

    t, r = f.cousin("d", "f")
    print "'d' is a", words[t],"cousin", r, "removed from 'f'"

    t, r = f.cousin("i", "n")
    print "'i' is a", words[t],"cousin", r, "removed from 'n'"

    t, r = f.cousin("q", "e")
    print "'q' is a", words[t], "cousin", r, "removed from 'e'"

    t, r = f.cousin("h", "c")
    print "'h' is a", words[t], "cousin", r, "removed from 'c'"

    t, r = f.cousin("h", "a")
    print "'h' is a", words[t], "cousin", r, "removed from 'a'"

    t, r = f.cousin("h", "h")
    print "'h' is a", words[t], "cousin", r, "removed from 'h'"

    t, r = f.cousin("a", "a")
    print "'a' is a", words[t], "cousin", r, "removed from 'a'"
########NEW FILE########
__FILENAME__ = fibonacci
#!/usr/bin/env python
'''
Fibonacci - each number equals the sum of the two preceding numbers.

Fn = Fn-1 + Fn-2

Input: the point in the sequence to take a fibonnaci number
Output: the fibonnaci number at the point in a sequence starting a 0

Ex: 
At position 0 the Fib number is 0. 
At position 4 the Fib number is 3 (adding 1, 2 which are the numbers before)

Challenge:
* Account for negative or fraction numbers
* Do it more efficiently (memoization)?
* Do it with only O(1) space (iteratively using a for loop)

'''

# O(n)
def fib_iteration(num):
    alist = []
    first = 0
    second = 1
    while num >= 0:
        alist.append(first)
        num -= 1
        first, second = second, (first + second)
    return alist[num]

# O(2^n)
def fib_recursive(num):
    if num < 2:
        return num
    else:
        return fib_recursive(num - 1) + fib_recursive(num - 2)

def fib_generator(num):
    fib_1 = fib_2 = 0
    for n in range(num):
        if n == 0:
            fib_2 = 1
            yield fib_1
        elif n == 1:
            yield fib_2
        else:
            next = fib_1 + fib_2
            yield next
            fib_1 = fib_2
            fib_2 = next

# O(n)
def fib_iteration2(index):
    results = [0, 1]
    if index < 2:
        return index
    for i in range(1, index):
        new_val = results[0] + results[1]
        results[0], results[1] = results[1], new_val
    return results[-1]

# O(n) - how to get adjustment if 3 returns 1?
def fib_variation(n):
    a, b, c, d = 0, 1, 1, 1
    for i in range(n):
        a, b, c, d = b, c, d, c+d
    return sum(a, b, c, d)

if __name__ == '__main__':

    # Test section
    implementations = [fib_iteration, fib_iteration2, fib_recursive, fib_variation]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(0) == 0: %s" % (impl(0) == 0)
        print "  f(1) == 1: %s" % (impl(1) == 1)
        print "  f(2) == 1: %s" % (impl(2) == 1)
        print "  f(3) == 2: %s" % (impl(3) == 2)
        print "  f(6) == 8: %s" % (impl(6) == 8)
        print "  f(13) == 233: %s" % (impl(13) == 233)

    # Special case trying out generator
    gen_example = fib_generator(13)
    print "trying generator"
    print "  f(0) == 0: %s" % (gen_example.next() == 0)
    print "  f(1) == 1: %s" % (gen_example.next() == 1)
    print "  f(2) == 1: %s" % (gen_example.next() == 1)
    print "  f(3) == 2: %s" % (gen_example.next() == 2)
########NEW FILE########
__FILENAME__ = find_duplicates
#!/usr/bin/env python
'''
Find Duplicates

Input: list of Size N, integers from 1 to n
Output: print out if there are duplicates
'''

#O(n)
def find_dup(list1):
    count = {}
    ans = []
    for l in list1:
        count.setdefault(l,0)
        count[l]+=1
    for item, num in count.iteritems():
        if num > 1:
            ans.append(item) 
    return ans

#O(n)
def find_dup2(list1):
    ans = []
    for i,l in enumerate(list1):
        if i < len(list1):
            if l in list1[i+1:]:
                ans.append(l) 
    ans.sort()
    return ans


if __name__ == '__main__':
    #Test section
    implementations = [find_dup,find_dup2]
    input1 = [5,4,7,2,1,8,3,1,4]
    result1 = [1, 4]

    for impl in implementations:
        print "  f(%s) == %s: %s" % (input1, result1, impl(input1) == result1)

########NEW FILE########
__FILENAME__ = find_num
#!/usr/bin/env python
'''
Find Num 

Input: List of integers and target number.
Output: If the number exists and the index of the number  OR
What number is missing

'''

#Return true if num exists in list -O(n)
def find_num(list1, num):
    if num in list1:
        return True
    return False


#Return index of the second occurance of a num in list - O(n)
def find_num2(list1, num):
    count = result = 0
    for x, n in enumerate(list1):
        if n == num:
            count += 1
            if count == 2:    
                result = x
            else:
                result = "Doesn't exist"
    return result


#Find a missing number when comparing two lists - O(n^2)
def miss_num(list1, list2):
    
    for i in list1:
        if i not in list2:
            return i
    return 0


#Second variation to find a missing number by adding the values and subtracting - O(n)
def miss_num2(list1, list2):
    return abs(sum(list1)-sum(list2))

if __name__ == '__main__':
    #Test section
    implementations = [find_num, find_num2]
    list1 = [5,4,1,2,8,3,-1,3,1]

    result1 = True
    result2 = False
    result3 = "Doesn't exist"

    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s, 0) == False or Doesn't exist: %s" % (list1, (impl(list1, 0) == result2 or impl(list1, 0) == result3))
        print "  f(%s, 1) == True or 8: %s" % (impl(list1, 1) == (list1, result1 or impl(list1, 1) == 8))
        print "  f(%s, 2) == True or Doesn't exist: %s" % (list1, (impl(list1, 2) == True or impl(list1, 2) == result3))
        print "  f(%s, 3) == True or 7: %s" % (list1, (impl(list1, 3) == result1 or impl(list1, 3) == 7))

    #Test for find miss number variations 
    implementations2 = [miss_num, miss_num2]
    list2 = [5,4,7,2,1,8,3]
    list3 = [5,4,7,2,8,3]
    list4 = [5,4,7,2,1,8,3]

    for impl in implementations2:
        print "trying %s" % impl
        print "  f(%s, %s) == 1: %s" % (list2, list3, (impl(list2, list3) == 1))
        print "  f(%s, %s) == 0: %s" % (list3, list4, (impl(list3, list4) == 0))

########NEW FILE########
__FILENAME__ = find_small_nums
#!/usr/bin/env python
'''
Find Subset 

Input: list of intergers and number of values to return
Output: list contains the number small values in the list
'''

# Using embeded for loops - O(n^2)
def small_sub(l,k):
    for j in range(len(l)):
        for i in range(len(l)):
            if l[j] < l[i]:
                l[i], l[j] = l[j], l[i]
    return l[0:k]

# Apply sort - O(n)
def small_sub2(l,k):
    l.sort()
    return l[0:k]

if __name__ == '__main__':
    #Test section
    num_list = [1,10,3,9,5,-1]
    num_vals = 3

    implementations = [small_sub, small_sub2]
    result = [-1,1,3]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s) == %s: %s" % (impl, result, impl(num_list,num_vals) == result)

########NEW FILE########
__FILENAME__ = fixed_point
"""
Fixed Point 

f: a function of one argument that returns a float
epsilon: a small float

returns the best guess when that guess is less than epsilon 
away from f(guess) or after 100 trials, whichever comes first.
"""

def fixedPoint(f, epsilon):
    guess = 1.0
    for i in range(100):
        if abs(f(guess) - guess) < epsilon:
            return guess
        else:
            guess = f(guess)
    return guess

def sqrt1(a):
    def tryit(x):
        return 0.5 * (a/x + x)
    return fixedPoint(tryit, 0.0001)

#################

def babylon(a):
    def test(x):
        return 0.5 * ((a / x) + x)
    return test

def sqrt2(a):
    return fixedPoint(babylon(a), 0.0001)


if __name__ == '__main__':

    # Test section
    implementations = [sqrt1, sqrt2]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(25) == 5: %s" % (round(impl(25)) == 5)
        print "  f(5) == 2: %s" % (round(impl(5)) == 2)
        print "  f(4) == 2: %s" % (round(impl(4)) == 2)

########NEW FILE########
__FILENAME__ = fizzbuzz
#!/usr/bin/env python
'''
Fizz Buzz 

Input: list of numbers

Output: print numbers submitted except:
  if divisable by 3 - write fizz
  if divisable by 5 - write buzz
  if divisable by 15 - write fizz buzz


'''

#O(n)
def fizz_buzz(num):
    for n in range(1,(num+1)):
        if n % 15 == 0:
            print "fizz buzz"
        elif n % 5 == 0:
            print "buzz"
        elif n % 3 == 0:
            print "fizz"
        else:
            print n


'''
Alternative version
- if divisible by 5 or contains 5 as a digit in the number => "fizz"
 - if divisible by 7 or contains 7 as a digit in the number => "buzz" 
 - if divisible by 5 and 7, or contains 5 and 7, or divisible by 5 and contains 7, 
 or divisible by 7 and contains 5 => "fizz buzz" 

'''

#O(n)
def fizz_buzz2(num):
    low_val = []

    for n in range(1, (num+1)):
        div_5 = has_5 = div_7 = has_7 = False

        #Find where number meets conditions
        if n%5 == 0: 
            div_5 = True 
        if str(n).find('5') != -1:
            has_5 = True
        if n%7 == 0:
            div_7 = True
        if str(n).find('7') != -1:
            has_7 = True

        #Run comparison to find fizz buzz conditions and print
        if (div_5 and div_7) or (has_5 and has_7) or (div_5 and has_7) or (has_5 and div_7):
            print 'fizz buzz'
        elif (div_5 or has_5):
            print 'fizz'
        elif (div_7 or has_7):
            print 'buzz'
        else:
            print n



'''
print lowest value of numbers that meets all 16 combinations of T/F 
to conditions

/5 or *5 25 and 53 
/7 or *7
*5 & *7 75
/5 & *7 75
/7 & *5 
/5 & /7 35


divis_5 = True # or False
divis_7 = True
has_5 = True
has_7 = True
'''

#O(n)
def fizz_buzz_combos(start, end):
    ans = {}
    while len(ans) < 16 and start <= end:
        div_5 = start%5 == 0
        div_7 = start%7 == 0
        inc_5 = str(start).find('5') != -1
        inc_7 = str(start).find('7') != -1

        combo = '%s%s%s%s' % (div_5, div_7, inc_5, inc_7)

        if combo not in ans:
            ans[combo] = start

        start += 1

    return sorted(ans.values())

if __name__ == '__main__':
    #Test section
    print "fizz buzz 1st version:\n", fizz_buzz(18)
    print "fizz buzz 2nd version:\n", fizz_buzz2(40)
    print "fizz buzz 3rd version:\n", fizz_buzz_combos(0,1000)



########NEW FILE########
__FILENAME__ = flatten_list
#!/usr/bin/env python
'''
Flatten Lists

Input: multiple Lists
Output: contcatenation of lists into one
'''

#List comprehension - O(n)
def flatten_list(list_of_lists):
    return [item for sublist in list_of_lists for item in sublist]

if __name__ == '__main__':
    #Test section
    list_of_lists = [[1,2],[3,4],[5,6]]
    result = [1,2,3,4,5,6]

    implementations = [flatten_list]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s) == %s: %s" % (list_of_lists, result, (impl(list_of_lists) == result))


########NEW FILE########
__FILENAME__ = gcd
#!/usr/bin/env python
''' 
Greatest Common Divisor

Input: Two positive integers
Output: Largest integer that divides into both

Sample problem from edx CompSci 101

'''
def gcd(a, b):
    test_value = min(a, b)
    if a % test_value == 0 and b % test_value == 0:
        return test_value
    while test_value > 0:
        test_value -= 1
        if a % test_value == 0 and b % test_value == 0:
            return test_value

def gcd2(a, b):
    testValue = min(a, b)

    # Keep looping until testValue divides both a & b evenly
    while a % testValue != 0 or b % testValue != 0:
        testValue -= 1

def gcd_recursion(a, b):
    '''
    Applying Euclid's algorithm
    '''
    if b == 0:
        return a
    else:
        return gcd_recursion(b, a%b)

if __name__ == '__main__':
    # Test section
    implementations = [gcd, gcd2, gcd_recursion]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(2,12) == 2: %s" % (gcd(2,12) == 2)
        print "  f(6,12) == 6: %s" % (gcd(6,12) == 6)
        print "  f(17,12) == 1: %s" % (gcd(17,12) == 1)
        print "  f(160,96) == 32: %s" % (gcd(160,96) == 32)

########NEW FILE########
__FILENAME__ = graph_search
#!/usr/bin/env python
'''
Graph Search Problem 

Input:
* N cities with a unique integer ID in the [1..N] range 
* Cities connected by X bidirectional roads which have the same length
    * List of ids of first city connected by each road 
    * List of ids of second city connected by each road
* ID home city
* ID destination city

Output: Print minimum number of roads to travel between home and destination

Assumption: destination city is always accessible from home city


The ith road connects the ith city in the firstCityRoad array and the ith city in the secondCityRoad array.

Constraints:
* Number of cities will not exceed 5000
* Number of roads will not exceed 100000
* Print the result in less than 2 seconds

Example:

    7 cities identified by IDs=1,2,3,4,5,6,7
    5 roads connecting the following pairs of cities: (1,3), (2,3), (3,4), (2,4), (5,6)
    from your home city ID=1 you can reach the destination city ID=4 taking either the 1, 3, 4 route or 1, 3, 2, 4 route
    the 1, 3, 4 route requires you to travel two roads (1,3) and (3,4)
    the 1, 3, 2, 4 route requires you to travel three roads (1,3), (3,2) and (2,4)
    the first route is the shortest one requiring you to travel only 2 roads

1 - 3 -- 4
    |   /
    2  

5 -- 6

'''

class Graph(Object):
    def __init__(self, nodes, edges):
        self.node = nodes
        self.edges = edges

    # def is_connected(self, a, b):
    #     return (a,b) in self.edges

    def edges_from(self, a):
        return [e for e in self.edges if n in e]

# g = Graph(...)

# (1,2) - > (2,1)
# (from, to)

# [(1,2),(2,1)]

# Open shortest path (ospf)
# visited { [1,2]: True, [1,4]: True }
# paths = (1,2), (1,4)

def ospf(home, dest, graph):
    visited = {}

    for e in graph.edges:
        visited[e] = False

    paths = graph.edges_from(home)

    for p in paths:
        if visited[path]:

            # new path
            other_city = p[1] 
            visited[path] = True
            paths.extend(graph.edges_from(other_city))
        else:
            # seen this already
            pass

# Track the number of results mapped
if __name__ == '__main__':
# Test search
home = 1
dest = 5
cities = [1,2,3,4,5,6,7]
road_graph = [(1,3),(3,4),(2,3),(2,4),(5,6)]

print ospf(home, dest, graph)
########NEW FILE########
__FILENAME__ = hangman_helper
import string

def isWordGuessed(secretWord, lettersGuessed):
    '''
    secretWord: string, the word the user is guessing
    lettersGuessed: list, what letters have been guessed so far
    returns: boolean, True if all the letters of secretWord are in lettersGuessed;
      False otherwise
    '''
    for letter in secretWord:
        if letter in lettersGuessed:
            continue
        else: 
            return False
    return True

def getGuessedWord(secretWord, lettersGuessed):
    '''
    secretWord: string, the word the user is guessing
    lettersGuessed: list, what letters have been guessed so far
    returns: string, comprised of letters and underscores that represents
      what letters in secretWord have been guessed so far.
    '''
    guessed_so_far = list(len(secretWord) * '_')

    for i, letter in enumerate(secretWord):
        if letter in lettersGuessed:
            guessed_so_far[i] = letter
    return ''.join(guessed_so_far)

def getGuessedWord_alt(secretWord, lettersGuessed):
    answer = []
    for i in secretWord:
        if i in lettersGuessed:
            answer.append(i + ' ')
        else:
            answer.append('_ ')
    return ''.join(answer)


def getAvailableLetters(lettersGuessed):
    '''
    lettersGuessed: list, what letters have been guessed so far
    returns: string, comprised of letters that represents what letters have not
      yet been guessed.
    '''
    result = list(string.ascii_lowercase)
    for letter in lettersGuessed:
        result.remove(letter)
    return ''.join(result)


if __name__ == '__main__':
    # Test Cases
    print("trying isWordGuessed")
    print("isWordGuessed('apple', ['a', 'e', 'i', 'k', 'p', 'r', 's']) == False: %s") % (isWordGuessed('apple', ['a', 'e', 'i', 'k', 'p', 'r', 's']) == False)
    print("isWordGuessed('durian', ['h', 'a', 'c', 'd', 'i', 'm', 'n', 'r', 't', 'u']) == True: %s") % (isWordGuessed('durian', ['h', 'a', 'c', 'd', 'i', 'm', 'n', 'r', 't', 'u']) == True)
    print("isWordGuessed('pineapple', ['q', 'v', 's', 'k', 'e', 'o', 'r', 't', 'h', 'n']) == False: %s") % (isWordGuessed('pineapple', ['q', 'v', 's', 'k', 'e', 'o', 'r', 't', 'h', 'n']) == False)
    isWordGuessed('coconut', []) == False
    isWordGuessed('carrot', ['z', 'x', 'q', 'c', 'a', 'r', 'r', 'o', 't']) == True

    print("trying getGuessedWord")
    print("getGuessedWord('apple', ['e', 'i', 'k', 'p', 'r', 's']) == '_pp_e': %s ") % (getGuessedWord('apple', ['e', 'i', 'k', 'p', 'r', 's']) == '_pp_e')
    getGuessedWord('durian', ['a', 'c', 'd', 'h', 'i', 'm', 'n', 'r', 't', 'u']) == 'durian'
    getGuessedWord('broccoli', ['f', 'c', 'q', 'b', 'z', 'p', 't', 'u', 'g', 'a']) == 'b__cc___'
    getGuessedWord('grapefruit', []) == '__________'

    print("trying getAvailableLetters")
    print("getAvailableLetters(['e', 'i', 'k', 'p', 'r', 's']) == 'abcdfghjlmnoqtuvwxyz': %s") % (getAvailableLetters(['e', 'i', 'k', 'p', 'r', 's']) == 'abcdfghjlmnoqtuvwxyz')
    getAvailableLetters([]) == 'abcdefghijklmnopqrstuvwxyz'
    getAvailableLetters(['e', 'p', 'v', 'f', 's', 'q', 'n', 'h', 'b', 'z', 'l', 'r']) == 'acdgijkmotuwxy'
    getAvailableLetters(['y', 'g', 'w', 'c', 'u', 'z', 'l', 'q', 't']) == 'abdefhijkmnoprsvx'
########NEW FILE########
__FILENAME__ = ps3_hangman
# 6.00 Problem Set 3
# 
# Hangman game
#

# -----------------------------------
# Helper code
# You don't need to understand this helper code,
# but you will have to know how to use the functions
# (so be sure to read the docstrings!)

import random
import string
from hangman_helper import getAvailableLetters, isWordGuessed, getGuessedWord

WORDLIST_FILENAME = "words.txt"

def loadWords():
    """
    Returns a list of valid words. Words are strings of lowercase letters.
    
    Depending on the size of the word list, this function may
    take a while to finish.
    """
    print "Loading word list from file..."
    # inFile: file
    inFile = open(WORDLIST_FILENAME, 'r', 0)
    # line: string
    line = inFile.readline()
    # wordlist: list of strings
    wordlist = string.split(line)
    print "  ", len(wordlist), "words loaded."
    return wordlist

def chooseWord(wordlist):
    """
    wordlist (list): list of words (strings)

    Returns a word from wordlist at random
    """
    return random.choice(wordlist)

# end of helper code
# -----------------------------------

# Load the list of words into the variable wordlist
# so that it can be accessed from anywhere in the program
wordlist = loadWords()


def hangman(secretWord):
    '''
    secretWord: string, the secret word to guess.

    Starts up an interactive game of Hangman.

    * At the start of the game, let the user know how many 
      letters the secretWord contains.

    * Ask the user to supply one guess (i.e. letter) per round.

    * The user should receive feedback immediately after each guess 
      about whether their guess appears in the computers word.

    * After each round, you should also display to the user the 
      partially guessed word so far, as well as letters that the 
      user has not yet guessed.

    Follows the other limitations detailed in the problem write-up.
    '''
    num_guesses = 8
    lettersGuessed = []
    won = False

    print("Welcome to the game, Hangman! \nI am thinking of a word that is %d letters long.") % len(secretWord)

    while num_guesses > 0:
        print("-----------")
        print("You have %d guesses left") % num_guesses
        print("Available Letters: %s") % getAvailableLetters(lettersGuessed)
        guess = raw_input("Please guess a letter:")
        guess = guess.lower()
        if guess in lettersGuessed:
            print("Oops! You've already guessed that letter: %s") % remaining
            continue
        lettersGuessed.append(guess)
        remaining = getGuessedWord(secretWord, lettersGuessed)
        if guess in secretWord:
            print("Good guess: %s") % remaining
        else:
            num_guesses -= 1
            print("Oops! That letter is not in my word: %s") % remaining


        if isWordGuessed(secretWord, lettersGuessed):
            print("-----------")
            print("Congratulations, you won!")
            won = True
            break
        
    if not won:
        print("-----------")
        print("Sorry, you ran out of guesses. The word was %s.") % secretWord





# When you've completed your hangman function, uncomment these two lines
# and run this file to test! (hint: you might want to pick your own
# secretWord while you're testing)

secretWord = chooseWord(wordlist).lower()
hangman(secretWord)
########NEW FILE########
__FILENAME__ = itinerary
#!/usr/bin/env python
'''
Travel Itinerary

Input: city_pairs of of paired travel cityations (from to)
Output: Print out the cities in order based on travel plan


'SFO' - 'LAX'
'LAX' - 'BOS'
'JFK' - 'SFO'
'BOS' - 'DEN'
'''

def sort_cities(city_pairs):
    visit_count = {}
    for index, city in enumerate(city_pairs):
        if visit_count[city[0]]:
            visit_count[city[0]] += 1
        else:
            visit_count[city[0]] = 1
        if visit_count[city[1]]:
            visit_count[city[1]] += 1
        else:
            visit_count[city[1]] = 1
    return print_cities(visit_count, city_pairs)

def print_cities(visit_count, city_pairs):
    for city, visit in visit_count:
        if visit == [0]:
            print city
            orig = city
            for index, city in enumerate(city_pairs):
                if orig == city[0]:
                    print city[1]
                    orig = city[1]
                    city_pairs.pop(index)


if __name__ == '__main__':
        
    # Test section

    # City pairs format is (from, to)
    city_pairs = [('SFO','LAX'),('BOS','DEN'),('LAX','BOS'),('JFK','SFO')]
    result = [('JFK','SFO'),('SFO','LAX'),('LAX','BOS'),('BOS','DEN')]

    implementations = [sort_cities]

    for impl in implementations:
        print 'for %s in implementations' % impl
        print 'f(%s) == %s: %s' % (city_pairs, result, impl(city_pairs) == result)
########NEW FILE########
__FILENAME__ = linked_list
'''
Linked List
(Singuly vs. Doubly)

Input: Empty
Output: Define a linked list and be able to navigate, add and delete

Node
  data   next       data  next        data   next 
[      |      ] -> [     |     ] -> [      |      ]

head.next 
n = head
n = n.next 


'''


########NEW FILE########
__FILENAME__ = list_intersection
#!/usr/bin/env python
'''
List Intersection

Input: 2 lists
Output: numbers where the two lists intersect 
'''

#Return list of intersections between 2 lists - O(n^2) or O(nm)
def list_int(list1, list2):
    result = []
    for a in list1:
        for b in list2:
            if a == b:
                result.append(a)
    return set(result)

#Return list of intersections between 2 lists - O(n^2) or O(nm)
def list_int2(list1, list2):
    result = []
    for a in list1: 
        if a in list2: #'in' is a loop
            result.append(a)
    return set(result)

#Return list of intersections using list and set functions - O(n)
def list_int3(list1, list2):
    return set(list(set(list1) & set(list2)))

#Create a dictionary and then run through to build list with list comprehension - O(n)
def list_int4(list1, list2):
    s1 = set(list1)
    lc = [list2[i] for i in xrange(len(list2)) if list2[i] in s1]
    return set(list(lc))

if __name__ == '__main__':
    #Test section 
    implementations = [list_int, list_int2, list_int3, list_int4]
    list1 = [9,-1,10,2,300,3,0,-10]
    list2 = [5,4,7,-1,8,9]
    list3 = [-2,0,2000,30,16,85,903,-10,567,4,300]
    list4 = [-2,2000,30,16,85,903,567,4]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(list1, list2) == [9,-1]: %s" % (impl(list1, list2) == set([9,-1]))
        print "  f(list1, list3) == [0,-10,300]: %s" % (impl(list1, list3) == set([0,-10,300]))
        print "  f(list2, list3) == [4]: %s" % (impl(list2, list3) == set([4]))
        print "  f(list1, list4) == []: %s" % (impl(list1, list4) == set([]))
        print impl(list1, list3)

 
########NEW FILE########
__FILENAME__ = logarithm
'''
Compute Logarithm

x: a positive integer
b: a positive integer; b >= 2

returns: log_b(x), or, the logarithm of x relative to a base b. 

Assumes: It should only return integer value and solution is recursive.
'''


def myLog(x, b):
    if x < b:
        return 0
    else:
        return myLog(x/b, b) + 1

if __name__ == '__main__':

    # Test section
    implementations = [myLog]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(1, 2) == 0: %s" % (impl(1,2) == 0)
        print "  f(2, 2) == 1: %s" % (impl(2,2) == 1)
        print "  f(16, 2) == 4: %s" % (impl(16,2) == 4)
        print "  f(15, 3) == 2: %s" % (impl(15,3) == 2)
        print "  f(15, 4) == 1: %s" % (impl(15,4) == 1)

########NEW FILE########
__FILENAME__ = make_change
#!/usr/bin/env python
'''
Make Change 
(variation on sum target question but more than pair)

Input: Target coin and list of coins
Output: Count of unique ways to make change OR
        List of unique ways to make change - originally coded by Jasmine

'''
coins = [1, 5, 10, 25]

#Count solution
def make_change(coins, num_coins, target):
    count = 0

    if target == 0:
        return 1
    
    if target < 0:
        return 0

    if num_coins <= 0 and target >= 1:
        return 0

    return make_change(coins, num_coins-1, target) + make_change(coins, num_coins, target - coins[num_coins-1])
    

#Recursive solution to return all unique combinations of change to make taret
#Solution applies dynamic programming




#global variable - bad but whatever
amts_calculated = {} #default combination for zero cents is zero coins across

def make_change2(coins, target):
    if not 0 in amts_calculated:
        amts_calculated[0] = (len(coins) * [0],)

    if target < 0 :
        return []

    if target == 0 :
        return amts_calculated[0]

    if target not in amts_calculated:
        combined_list = ()

        for index, coin in enumerate(coins):
            base_solutions_list = make_change2(coins, target-coin)
            solutions_list = ()

            for solution in base_solutions_list:
                new_solution = solution[:]
                new_solution[index] += 1

                solutions_list = solutions_list + (new_solution,)

            for new_solution in solutions_list:
                if new_solution not in combined_list:
                    combined_list = combined_list + (new_solution,)

        amts_calculated[target] = combined_list

    return amts_calculated[target]


# Test section

if __name__ == '__main__':
    num_coins = len(coins)    
    print num_coins

    target = 1
    target2 = 2
    target3 = 3
    target4 = 5
    target5 = 7
    target6 = 10
    target7 = 25
    target8 = 27

    result = 1
    result2 = 1
    result3 = 1
    result4 = 2
    result5 = 2
    result6 = 4
    result7 = 13
    result8 = 13

    implementations = [make_change]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(%s) == %s: %s" % (target, result, impl(coins,num_coins,target) == result)
        print "  f(%s) == %s: %s" % (target2, result2, impl(coins,num_coins,target2) == result2)
        print "  f(%s) == %s: %s" % (target3, result3, impl(coins,num_coins,target3) == result3)
        print "  f(%s) == %s: %s" % (target4, result4, impl(coins,num_coins,target4) == result4)
        print "  f(%s) == %s: %s" % (target5, result5, impl(coins,num_coins,target5) == result5)
        print "  f(%s) == %s: %s" % (target6, result6, impl(coins,num_coins,target6) == result6)
        print "  f(%s) == %s: %s" % (target7, result7, impl(coins,num_coins,target7) == result7)
        print "  f(%s) == %s: %s" % (target8, result8, impl(coins,num_coins,target8) == result8)

    result1_2 = ([1,0,0,0],)
    result2_2 = ([2,0,0,0],)
    result3_2 = ([3,0,0,0],)
    result4_2 = ([5,0,0,0],[0,1,0,0])
    result5_2 = ([7,0,0,0],[2,1,0,0])
    result6_2 = ([10, 0, 0, 0], [5, 1, 0, 0], [0, 2, 0, 0], [0, 0, 1, 0])
    result7_2 = ([25, 0, 0, 0], [20, 1, 0, 0], [15, 2, 0, 0], [15, 0, 1, 0], [10, 3, 0, 0], [10, 1, 1, 0], [5, 4, 0, 0], [5, 2, 1, 0], [5, 0, 2, 0], [0, 5, 0, 0], [0, 3, 1, 0], [0, 1, 2, 0], [0, 0, 0, 1])
    result8_2 = ([27, 0, 0, 0], [22, 1, 0, 0], [17, 2, 0, 0], [17, 0, 1, 0], [12, 3, 0, 0], [12, 1, 1, 0], [7, 4, 0, 0], [7, 2, 1, 0], [7, 0, 2, 0], [2, 5, 0, 0], [2, 3, 1, 0], [2, 1, 2, 0], [2, 0, 0, 1])

    implementations2 = [make_change2]
    for impl in implementations2:
        print "trying %s" % impl
        print "  f(%s) == %s: %s" % (target, result1_2, impl(coins, target) == result1_2)
        print "  f(%s) == %s: %s" % (target2, result2_2, impl(coins, target2) == result2_2)
        print "  f(%s) == %s: %s" % (target3, result3_2, impl(coins, target3) == result3_2)
        print "  f(%s) == %s: %s" % (target4, result4_2, impl(coins, target4) == result4_2)
        print "  f(%s) == %s: %s" % (target5, result5_2, impl(coins, target5) == result5_2)
        print "  f(%s) == %s: %s" % (target6, result6_2, impl(coins, target6) == result6_2)
        print "  f(%s) == %s: %s" % (target7, result7_2, impl(coins, target7) == result7_2)
        print "  f(%s) == %s: %s" % (target8, result8_2, impl(coins, target8) == result8_2)

########NEW FILE########
__FILENAME__ = mcmc
'''
MCMC from Scratch

Algorithm for sampling probability distributions.
Approximates target distribution

Code from : http://darrenjw.wordpress.com/2010/04/28/mcmc-programming-in-r-python-java-and-c/

f(x,y) = k x2 exp{-xy2-y2+2y-4x}

'''

import random, math
 
def gibbs(N=20000,thin=500):
    x=0
    y=0
    print "Iter  x  y"
    for i in range(N):
        for j in range(thin):
            x=random.gammavariate(3,1.0/(y*y+4))
            y=random.gauss(1.0/(x+1),1.0/math.sqrt(x+1))
        print i,x,y
     
gibbs()
########NEW FILE########
__FILENAME__ = merge
#!/usr/bin/env python
'''
Merge Sort 

Input: words
Output: sorted array of items in O(n log n)

Challenge:
    How to complete mergesort in constant space?
'''
from random import shuffle


# Check input type and convert to list
def mergesort(words):
    if type(words) is str:
        result = slice_array(list(words))
        return ''.join(result)
    else:
        return slice_array(words)


# Determine input len & splits and call merge function
def slice_array(mlist):
    size = len(mlist)
    if size <= 1: 
        return mlist
    mid = size / 2
    return sort_values(slice_array(mlist[:mid]), slice_array(mlist[mid:]))


def sort_values(left, right):
    result = []
    i, j = 0, 0
    
    # Compare left and right lists and append to temp list
    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # Add remaining input to results to pass back.
    return result + left[i:] + right[j:]


if __name__ == '__main__':
    # Test string
    print mergesort('hellow world')     # ' dehllloorww'

    # Test list of integers
    nums = [i for i in range(42)]
    shuffle(nums)
    print mergesort(nums)


########NEW FILE########
__FILENAME__ = oop
'''
Object Oriented Programming Practice

Use (or create) a course info class and edx objects. Create the support methods in the edx class to set grades, get grades, set Pset and get Pset. These methods inherit and utilize the courseInfo object methods.


Question on MIT Comp Sci 101 final.

'''

class courseInfo(object):

    def __init__(self, courseName):
        self.courseName = courseName
        self.psetsDone = []
        self.grade = "No Grade"
        
    def setPset(self, pset, score):
        self.psetsDone.append((pset, score))
        
    def getPset(self, pset):
        for (p, score) in self.psetsDone:
            if p == pset:
                return score

    def setGrade(self, grade):
        if self.grade == "No Grade":
            self.grade = grade

    def getGrade(self):
        return self.grade



class edx(object):
    def __init__(self, courses):
        self.myCourses = []
        for course in courses:
            self.myCourses.append(courseInfo(course))


    def _findCourse(self, course):
        matching_courses = [c for c in self.myCourses if course == c.courseName]
        try:
            return matching_courses[0] 
        except IndexError:
            return None


    def setGrade(self, grade, course="6.01x"):
        """
        grade: integer greater than or equal to 0 and less than or equal to 100
        course: string 

        This method sets the grade in the courseInfo object named by `course`.   

        If `course` was not part of the initialization, then no grade is set, and no
        error is thrown.

        The method does not return a value.
        """
        #   fill in code to set the grade
        course = self._findCourse(course)

        if course:
            course.setGrade(grade)


    def getGrade(self, course="6.02x"):
        """
        course: string 

        This method gets the grade in the the courseInfo object named by `course`.

        returns: the integer grade for `course`.  
        If `course` was not part of the initialization, returns -1.
        """
        #   fill in code to get the grade
        course = self._findCourse(course)

        if course:
            return course.getGrade()
        else:
            return -1

    def setPset(self, pset, score, course="6.00x"):
        """
        pset: a string or a number
        score: an integer between 0 and 100
        course: string

        The `score` of the specified `pset` is set for the
        given `course` using the courseInfo object.

        If `course` is not part of the initialization, then no pset score is set,
        and no error is thrown.
        """
        #   fill in code to set the pset
        course = self._findCourse(course)

        if course:
            return course.setPset(pset, score)


    def getPset(self, pset, course="6.00x"):
        """
        pset: a string or a number
        score: an integer between 0 and 100
        course: string        

        returns: The score of the specified `pset` of the given
        `course` using the courseInfo object.
        If `course` was not part of the initialization, returns -1.
        """
        #   fill in code to get the pset

        course = self._findCourse(course)

        if course:
            return course.getPset(pset)
        else:
            return -1


if __name__ == '__main__':
    #Test section

    edX = edx( ["6.00x","6.01x","6.02x"] )
    edX.setPset(1,100)
    edX.setPset(2,200,"6.00x")
    edX.setPset(2,90,"6.00x")

    edX.setGrade(100)

    for c in ["6.00x","6.01x","6.02x"]:
        edX.setGrade(90,c)
        print edX.getPset(1, c)


########NEW FILE########
__FILENAME__ = palindrome
#!/usr/bin/env python
'''
Palindrome

Input: word
Output: true if a palindrome

Note: jofusa contributed additional example and test
'''

#Recursive solution.
def pal(word):
    if len(word) < 2:
        return True
    if word[0] == word [-1]:
        return pal(word[1:-1])
    if word[0] != word [-1]:
        return False

#Simple reverse list solution. O(n)
def pal2(word):
    return word == word[::-1]


#Strip out space and uppercases. O(n)
def pal3(word):
    stripped_word = word.replace(' ','').lower()
    return stripped_word == stripped_word[::-1]

def palWrapper(str1, str2):
    # A single-length string cannot be semordnilap
    if len(str1) == 1 or len(str2) == 1:
        return False

    # Equal strings cannot be semordnilap
    if str1 == str2:
        return False

    return pal4(str1, str2)

#Solve by skipping over spaces and punctuation
def pal4(str1, str2):

    # If strings aren't the same length, they cannot be palindrome
    if len(str1) != len(str2):
        return False

    # Base case: if the strings are each of length 1, check if they're equal
    if len(str1) == 1:
        return str1 == str2

    # Recursive case: check if the first letter of str1 equals the last letter of str2    
    if str1[:1] == str2[-1:]:
        return pal4(str1[1:], str2[:-1])
    else:
        return False


if __name__ == '__main__':
    #Test
    s = 'rowme'
    s2 = 'Lion oil'
    s3 = 'a man a plan a canal Panama'
    s4 = ('live', 'evil')
    s5 = ('dog', 'god')
    s6 = ('a', 'at')
    s7 = ('qanukywtmjcevo', 'hldxsgrtvkeywj')

    answers = ['emwor','lio noiL', 'amanaP lanac a nalp a nam a', True, True, False]

    result = False
    result2 = True

    implementations = [pal,pal2,pal3]
    implementations2 = [pal3]
    implementations3 = [palWrapper]

    for impl in implementations:
        print "trying %s" % impl
        print "f(s) == %s: %s" % (result,(impl(s) == result))

    for impl in implementations2:
        print "f(s2) == %s: %s" % (result2,(impl(s2) == result2))
        print "f(s3) == %s: %s" % (result2,(impl(s3) == result2))

    for impl in implementations3:
        print "f(s4) == %s: %s" % (result2,(impl(s4[0],s4[1]) == result2))
        print "f(s5) == %s: %s" % (result2,(impl(s5[0],s5[1]) == result2))
        print "f(s6) == %s: %s" % (result,(impl(s6[0],s6[1]) == result))
        print "f(s7) == %s: %s" % (result,(impl(s7[0],s7[1]) == result))

########NEW FILE########
__FILENAME__ = palindrome_rearrange_words
#!/usr/bin/env python
'''
Palindrome Part 2 

Input: List of words
Output: Rearrange each word if can be a palindrome, otherwise replace with -1 and return the list

'''

from collections import deque, defaultdict
from palindrome import pal2 # path relative import - pull from Github python folder

#Use deque structure to solve.
def palindrome(words):
    pal_list = []
    if len(words) <= 1 and len(words[0]) <= 1 :
        pal_list.append(''.join(words))
        
    #Loop through words.
    for i, word in enumerate(words):
        
        #Create count of letters.
        counter = {}
        for j,letters in enumerate(word): 
            counter[letters] = counter.get(letters, 0) + 1
        
        #Loop through counter and assign letters to deque
        sides = []
        center = deque()
        for letter, occurrences in counter.items():
            quotiant, remainder = divmod(occurrences, 2)

            if not remainder:
                sides.append(letter * quotiant)
                continue

            if center:
                pal_list.append(-1)
                sides = []        
                center = deque()
                break

            center.append(letter * occurrences)

        center.extendleft(sides)
        center.extend(sides)

        if center != deque([]):
            pal_list.append(''.join(center))

    return pal_list


#Build dictionary of letter counts, then build word if only 1 occurance of an odd count
def palindrome2(words_list):
    pal_list = []
    for i, word in enumerate(words_list):

        #Build dictionary of letter counts:
        count_dict = {}
        for j, letter in enumerate(word):

            if letter in count_dict:
                count_dict[letter] += 1
            else:
                count_dict[letter] = 1

        #Find number of odd letter occurances in dictionary
        remainder = 0
        for key, value in count_dict.iteritems():
            if value % 2 != 0:
                remainder +=1

        if remainder > 1:
            pal_list.append(-1)
        else:
            sides = []
            middle = []   
        
            for key, value in count_dict.iteritems():
                if value % 2 == 0:
                    sides.append(key * (value/2))
                else:
                    middle.append(key * value)
            
            if sides:
                middle.extend(sides)
                middle.reverse()
                middle.extend(sides)
            
            if middle != -1:
                pal_list.append(''.join(middle))

    return pal_list


def palindrome3(words_list):
    results = []
    def fail():
        results.append(-1)

    def count_occurrences(word, evens, odds):
        for c in word:
            # count letters but also swap them back and forth for easy checking
            # of the # of odds later.
            if c in odds:
                left = evens
                right = odds
            else:
                left = odds
                right = evens

            left[c] = right[c] + 1
            del right[c]

    for word in words_list:
        evens = defaultdict(int)
        odds = defaultdict(int)
        count_occurrences(word, evens, odds)

        # if the word is len-even, then there must
        # be no odd-occurring letters - otherwise it can't be
        # a palindrome.
        if len(word) % 2 == 0:
            if len(odds) != 0:
                fail()
                continue
            center = ""
        else:
            # ok, odd-length, but still we must have only one odd.
            if len(odds) > 1:
                fail()
                continue
            # fancy: center = odds.keys()[0] * odds.values()[0]
            center_letter, center_count = odds.items()[0]
            center = center_letter * center_count
        # build the left half, then join it to the center and the left's reverse:
        left = []
        for char, count in evens.items():
            left.append(char * (count/2))
        left = "".join(left)
        # and that's a final palindrome:
        results.append(left + center + left[::-1])
    return results

if __name__ == '__main__':
    #Test section.
    implementations = [palindrome, palindrome2, palindrome3]
    words = ['cecarar', 'nono', 'abbbbb']
    words2 = ['talliat', 'eded', 'memo']
    words3 = ['hello']
    words4 = ['']

    result = ['rcaeacr', 'noon', -1]
    result2 = ['ltaiatl', 'deed', -1]
    result3 = [-1]
    result4 = ['']

    #Function to check if its a palindrome despite the order of the letters.
    def verify(actual, expected):
        for i, val in enumerate(actual):
            if val == -1:
                if expected[i] != -1:
                    return False
                continue
            if pal2(val) != pal2(expected[i]):
                return False
        return True

    for impl in implementations:
        print "trying %s" % impl
        print "  f(words1) == result: %s" % (verify(impl(words), result))
        print "  f(words2) == result2: %s" % (verify(impl(words2), result2))
        print "  f(words3) == result3: %s" % (verify(impl(words3), result3))
        print "  f(words4) == result4: %s" % (verify(impl(words4), result4))

########NEW FILE########
__FILENAME__ = pay_credit_debt
#!/usr/bin/env python
''' 
Pay Credit Debt

Several problems included here to show how to calculate and print payment information as it relates to credit card payment

Pulled from edx CompSci 101

'''

def monthly_payment(balance, monthlyInterestRate, monthlyPaymentRate, numbermonths):
    '''
    Print monthly minimum payment and remaining balance as well as return annual total paid and balance.
    '''
    month = totalPaid = 0
    while month < numbermonths:
        month += 1
        minimumMonthlyPayment = monthlyPaymentRate * balance
        monthlyUnpaidBalance = balance - minimumMonthlyPayment
        balance = monthlyUnpaidBalance + monthlyInterestRate * monthlyUnpaidBalance 
        totalPaid += minimumMonthlyPayment

        print("Month: %.2f" % month)
        print("Minimum monthly payment: %.2f" % minimumMonthlyPayment)
        print("Remaining balance: %.2f" % balance)

    return (totalPaid, balance)

def monthly_interest(annualInterestRate, months):
    return annualInterestRate / float(months)

def min_payment(balance, annualInterestRate, monthlyPaymentRate):
    '''
    Print credit card balance and total paid after one year if paying minimum monthly payment rate
    '''
    numbermonths = 12

    monthlyInterestRate = monthly_interest(annualInterestRate, numbermonths)
    totalPaid, balance = monthly_payment(balance, monthlyInterestRate, monthlyPaymentRate, numbermonths)

    print("Total paid: %.2f" % totalPaid)
    print("Remaining balance: %.2f" % balance)

def calc_balance(monthlyPayment, monthlyInterestRate, balance, period):
    '''
    Return the balance based on monthly payment, interest rate, balance and timing
    '''
    while period != 0:
        monthlyUnpaidBalance = balance - monthlyPayment
        balance = monthlyUnpaidBalance + monthlyInterestRate * monthlyUnpaidBalance
        period -= 1
    return balance

def year_payoff(balance, annualInterestRate):
    '''
    Print the lowest payment to pay debt off in a year within a multiple of 10
    '''
    orgbalance = balance
    months = 12
    monthlyInterestRate = monthly_interest(annualInterestRate, months)
    paid = False    
    monthlyPayment = 0

    while not paid:
        monthlyPayment += 10
        balance = calc_balance(monthlyPayment, monthlyInterestRate, orgbalance, months)

        if balance <= 0:
            paid = True

    print("Lowest Payment %.2f" % monthlyPayment)

def bisection_year_payoff(balance, annualInterestRate):
    '''
    Bisection search to make the program fast
    '''
    months = 12
    epsilon = 0.01

    orgbalance = balance
    monthlyInterestRate = monthly_interest(annualInterestRate, months)
    monthlyPaymentLowerBound = balance / months
    monthlyPaymentUpperBound = (balance * ((1+monthlyInterestRate)**months))/ months

    while abs(balance) >= epsilon:
        monthlyPayment = (monthlyPaymentLowerBound + monthlyPaymentUpperBound) / 2
        
        balance = calc_balance(monthlyPayment, monthlyInterestRate,orgbalance, months)

        if round(balance, 2) == epsilon:
            break
        elif balance > epsilon:
            monthlyPaymentLowerBound = monthlyPayment
        elif  balance < epsilon:
            monthlyPaymentUpperBound = monthlyPayment

    print("Lowest Payment %.2f" % monthlyPayment)

#Tests

min_payment(4213, 0.2, 0.04)
# 'Total paid: 1775.55 \n Remaining balance: 3147.67'
min_payment(3473, 0.15, 0.05)
# 'Total paid: 1697.9 \n Remaining balance: 2178.35' 

year_payoff(3329, 0.2) 
# 'Lowest Payment: 310'
year_payoff(3380, 0.18)
# 'Lowest Payment: 310'

bisection_year_payoff(320000, .2)
# 'Lowest Payment: 29157.09'
bisection_year_payoff(71751, .15) 
# 'Lowest Payment: 6396.17'
########NEW FILE########
__FILENAME__ = prime
#!/usr/bin/env python
'''
Prime Number

Input: positive integer
Output: set of prime divsors of a number

'''

def find_primes(n):
    possible_divisor = 2
    primes = set()
    while n != 1:
        while n % possible_divisor == 0:
            primes.add(possible_divisor)
            n /= possible_divisor
        possible_divisor += 1
    return list(primes)

'''
Write a generator, genPrimes, that returns the sequence of prime numbers on successive calls to its next() method: 2, 3, 5, 7, 11, ...
'''

def genPrimes():
    primes = []   # primes generated so far
    last = 1      # last number tried
    while True:
        last += 1
        for p in primes:
            if last % p == 0:
                break
        else:
            primes.append(last)
            yield last

if __name__ == '__main__':
    #Test section
    impl = find_primes
    sample_n = [1,6,7,100]
    results = [[],[2,3],[7],[2,5]]
    print "trying find_primes"
    for index, n in enumerate(sample_n):
        # print "trying %s" % impl
        print "f(%s) == %s: %s" % (n,results[index],(impl(n) == results[index]))

    print "trying genPrimes"
    prime_print = genPrimes()
    print "first round == 2: %s" % (prime_print.next() == 2)
    print "first round == 3: %s" % (prime_print.next() == 3)
    print "first round == 5: %s" % (prime_print.next() == 5)

########NEW FILE########
__FILENAME__ = prime_clean_chain
'''
Prime - 4th Clean Chain

Input: Take a sequence of N numbers. We'll call the sequence a "Clean Chain of length N" if the sum of the first N - 1 numbers is evenly divisibly by the Nth number.

For example, the sequence [2, 4, 6, 8, 10] forms a clean chain of length 5, since 2 + 4 + 6 + 8 = 20, which is divisible by 10, and the sequence has 5 numbers.
The first clean chain formed out of the sequence of primes is simply [2], with length 1.
The second is [2, 3, 5] with length 3.
The third is [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71], with length 20

Output: What is the length of the fourth clean chain formed out of only primes?

Bonus: major bonus points, find the length of the fifth chain, too, and include it in the comments.

Contribution: Jess

'''

'''
Answer: Nathan Lucas (https://github.com/bnlucas)

The code below was taken from my reversible obfuscated hashing library, BaseHash
(https://github.com/bnlucas/python-basehash) found under basehash/primes.py

More information on the work behind the verification of primes can be found at
http://coderwall.com/p/utwriw and http://coderwall.com/p/t0u70w discussing the
process of developing these methods.

[     2,      3,      5,      7,     11,     13,     17,     19,     23,     29,
     31,     37,     41,     43,     47,     53,     59,     61,     67,     71,
    ...,
 368911, 368939, 368947, 368957, 369007, 369013, 369023, 369029, 369067, 369071,
 369077, 369079, 369097, 369119]

For the full fourth chain, all 3147 lines, see https://gist.github.com/bnlucas/7803398
There is a verifier at the bottom of the gist to ensure it is not skipping anything.

 prime       prev. sum       remainder
     2               0               0    1st clean chain
     5               5               0    2nd clean chain
    71             568               0    3rd clean chain
369119      5536785000               0    4th clean chain
'''

from fractions import gcd


PRIMES_LE_31 = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
PRIMONIAL_31 = 200560490130


def isqrt(n):
    if n < 0:
        raise ValueError('Square root is not defined for negative numbers.')
    x = int(n)
    if x == 0:
        return 0
    a, b = divmod(x.bit_length(), 2)
    n = 2 ** (a + b)
    while True:
        y = (n + x // n) >> 1
        if y >= n:
            return n
        n = y


def is_square(n):
    s = isqrt(n)
    return s * s == n


def factor(n, p=2):
    s = 0
    d = n - 1
    q = p

    while not d & q - 1:
        s += 1
        q *= p

    return s, d // (q // p)


def jacobi(a, p):
    if (not p & 1) or (p < 0):
        raise ValueError('p must be a positive odd number.')

    if (a == 0) or (a == 1):
        return a

    a = a % p
    t = 1

    while a != 0:
        while not a & 1:
            a >>= 1
            if p & 7 in (3, 5):
                t = -t

        a, p = p, a
        if (a & 3 == 3) and (p & 3) == 3:
            t = -t

        a = a % p

    if p == 1:
        return t

    return 0


def selfridge(n):
    d = 5
    s = 1
    ds = d * s

    while True:
        if gcd(ds, n) > 1:
            return ds, 0, 0

        if jacobi(ds, n) == -1:
            return ds, 1, (1 - ds) / 4

        d += 2
        s *= -1
        ds = d * s


def chain(n, u1, v1, u2, v2, d, q, m):
    k = q
    while m > 0:
        u2 = (u2 * v2) % n
        v2 = (v2 * v2 - 2 * q) % n
        q = (q * q) % n

        if m & 1 == 1:
            t1, t2 = u2 * v1, u1 * v2
            t3, t4 = v2 * v1, u2 * u1 * d
            u1, v1 = t1 + t2, t3 + t4

            if u1 & 1 == 1:
                u1 = u1 + n

            if v1 & 1 == 1:
                v1 = v1 + n

            u1, v1 = (u1 / 2) % n, (v1 / 2) % n
            k = (q * k) % n

        m = m >> 1

    return u1, v1, k


def strong_pseudoprime(n, a, s=None, d=None):
    if not n & 1:
        return False

    if (s is None) or (d is None):
        s, d = factor(n, 2)

    x = pow(a, d, n)

    if x == 1:
        return True

    for i in xrange(s):
        if x == n - 1:
            return True

        x = pow(x, 2, n)

    return False


def lucas_pseudoprime(n):
    if not n & 1:
        return False

    d, p, q = selfridge(n)
    if p == 0:
        return n == d

    u, v, k = chain(n, 0, 2, 1, p, d, q, (n + 1) >> 1)
    return u == 0


def strong_lucas_pseudoprime(n):
    if not n & 1:
        return False

    d, p, q = selfridge(n)
    if p == 0:
        return n == d

    s, t = factor(n + 2)

    u, v, k = chain(n, 1, p, 1, p, d, q, t >> 1)

    if (u == 0) or (v == 0):
        return True

    for i in xrange(1, s):
        v = (v * v - 2 * k) % n
        k = (k * k) % n
        if v == 0:
            return True

    return False


def baillie_psw(n, limit=100):
    if n == 2:
        return True

    if not n & 1:
        return False

    if n < 2 or is_square(n):
        return False

    if gcd(n, PRIMONIAL_31) > 1:
        return n in PRIMES_LE_31

    bound = min(limit, isqrt(n))
    for i in xrange(3, bound, 2):
        if not n % i:
            return False

    return strong_pseudoprime(n, 2) \
        and strong_pseudoprime(n, 3) \
        and strong_lucas_pseudoprime(n)


def next_prime(n):
    if n < 2:
        return 2

    if n < 5:
        return [3, 5, 5][n - 2]

    gap = [1, 6, 5, 4, 3, 2, 1, 4, 3, 2, 1, 2, 1, 4, 3, 2, 1, 2, 1, 4, 3, 2, 1,
           6, 5, 4, 3, 2, 1, 2]

    n += 1 if not n & 1 else 2

    while not baillie_psw(n):
        n += gap[n % 30]

    return n


def is_clean_prime_chain(prime):
    return sum(prime[:-1]) % prime[-1] == 0


def clean_prime_chain(prime):
    while True:
        prime.append(next_prime(prime[-1]))

        if is_clean_prime_chain(prime):
            return prime

########NEW FILE########
__FILENAME__ = product_integers
""" 
Product integers

This function takes in a list of integers and returns a list of integers containing the product of the 
# rest of the integers, excluding the corresponding element from the original list of integers. 

Examples:
Input = [1,2,3,4]
Output = [24,12,8,6]

Input = [-1,3,4,2]
Output = [24,-8,-6,-12]

SOLUTION:
Runtime: O(n)
Step1: I multiply every element in the input list1 and store in variable "product."
Step 2: Then, I divide out each element in input list1, append quotient to new_list, and finally, 
return new_list. """

def multiplication(list1):
    product = 1
    for j in list1:
        product = product * j
    return product

def product_intgers(list1):
    # Remove any and all zeros from list1. Any # divided by zero is undefined.
    zero_indices = []
    for i in range(len(list1)):
        if list1[i] == 0:
            zero_indices.append(i)
    for i in zero_indices:
        list1.remove(0)

    product = multiplication(list1)
    new_list = []

    if len(list1) <= 1: # if list1 only contains 1 element or fewer, return the original list1 
        print list1
        return list1

    for i in list1:
        new_list.append(product/i)
    print new_list
    return new_list

if __name__ == '__main__':
    # Sample Test Cases below.
    product_intgers([9]) #Expect [9]
    product_intgers([2,1,0]) # Expect [1,2]
    product_intgers([2,1,0]) #Expect [1,2]
    product_intgers([1,2,3]) #Expect [6,3,2]
    product_intgers([1,2,3,4]) #Expect [24,12,8,6]
    product_intgers([1,2,3,4,5]) #Expect [120,60,40,30,24]
    product_intgers([1,2,3,4,-5]) #Expect [-120,-60,-40,-30,24]
    product_intgers([0,0,0,0,0,0,0,0,0,0,0,0,0]) #Expect [0]
########NEW FILE########
__FILENAME__ = pythonbee
#!/usr/bin/env python
'''
Python-bee Sample from DBX 2013

'''

'''
Input: Non-empty, unique list of integers
Output: True if list is sorted else False
'''

def f(l):
    return sorted(l) == l

'''
Input: List of integers
Output: List of their squares in same order
'''
def f2(l):
   return [i*i for i in l]

'''
Input: Non-empyt list of floats 
Output: Mean
'''
def f3(a):
    return sum(a)/len(a)

'''
Input: Non-negative integer, X 
Output: Sum of the digits of 2^x
'''

def f4(x):
    ans = 0
    for i in str(2*x):
        ans += int(i)
    return ans

'''
Input: String of letters 
Output: Length of the longest substring of that string consisting of the same letter repeated
'''
def f5(x):
    pass #To be answered

if __name__ == '__main__':
    #Test section

    #Input
    int_list = [1,2,6,5]
    float_list = [1.5,2.5,3.5]
    num = 32

    #Output
    int_list_result = False
    int_list_result2 = [1,4,36,25]
    float_list_result = 2.5
    sum_num_result = 10

    print "f(%s) == %s: %s" % (int_list, int_list_result, f(int_list) == int_list_result)
    print "f2(%s) == %s: %s" % (int_list, int_list_result2, f2(int_list) == int_list_result2) 
    print "f3(%s) == %s: %s" % (float_list, float_list_result,f3(float_list) == float_list_result)
    print "f4(%s) == %s: %s" % (num, sum_num_result, f4(num) == sum_num_result)

########NEW FILE########
__FILENAME__ = quicksort
#!/usr/bin/env python
'''
Quicksort

Input: list of numbers
Output: sorted list using quicksort 
'''

import random

# O(n^2) with list comprehension
def quick_sort(l):
    if len(l) <= 1:
        return []
    lesser = [x for x in l[1:] if x < l[0]]
    greater = [x for x in l[1:] if x > l[0]]
    return quick_sort(lesser) + [l[0]] + quick_sort(greater)

def find_pivot(l):
    pivot_index = random.randint(0,len(l)-1)
    return pivot_index

# O(n^2)
def quick_sort2(l, length=None):
    if len(l) <= 1:
        return l
    pivot_index = find_pivot(l)
    pivot = l[pivot_index]
    
    #Swap pivot to first item in list
    i = j = 1
    for num in l:
        if num < pivot:
            l[i],l[j]=l[j],l[i]
            i += 1
        j += 1
    l[0],l[i]=l[i],l[0]
    quick_sort2(l, i) 
    quicksort2(l, len(l)-1)
    return l # l will be changed as it goes through thus no = needed

# O(n^2)
def quick_sort3(l):
    left = right = []
    if len(l) <= 1:
        return l 
    else:
        pivot = random.randint(len(l))
        for num in l:
            if num > l[pivot]:
                left.append(l)
            else:
                right.append(l)
    return quick_sort3(left) + quick_sort3(right)


if __name__ == '__main__':
    #Test section
    l = [5,8,3,1,2,7,9,6]
    result = [1,2,3,5,6,7,8,9]

    implementations = [quick_sort, quick_sort2, quick_sort3, quick_sort4]

    for impl in implementations:
        print "trying %s" % impl
        print "%s == %s" % (impl,result)


########NEW FILE########
__FILENAME__ = random_weight_value
#!/usr/bin/env python
'''
Random Weighted Value

Input: 1 list of values and 1 list of corresponding weights of the values existing

Output: Return value based on its weight

'''
import random

#O(n)
def weighted_choice(value_list, weight_list):
    counter = 0
    sum_weight = sum(weight_list)
    random_weight = random.randomint(0, sum_weight)
    for i, weight in enumerate(weight_list):
        if random_weight >= counter:
            counter += weight
        else:
            return val_list[i]
#O(n)
def print_weight(items, weights):
    d = {}
    for i in range(100):
        value = weighted_choice(items, weights)
        d[value] += 1

    for k, count in d.items():
        print k, "*" * count

#O(n) - Jesse's answers
def weighted_choice2(choices):
    total = sum(weight for choice, weight in choices)
    r = random.uniform(0, total)
    count = 0
    for choice, weight in choices:
        if count + weight > r:
            return choice
        count += weight
 
#O(n)
def print_weight2(choices): 
    counts = {v: 0 for v, weight in values}
    for i in range(100):
        v = weighted_choice(choice)
        counts[v] += 1
     
    for v in sorted(counts.keys()):
        count = counts[v]
        print v, "*" * count

if __name__ == '__main__':
    # Test service
    value_list = [a,b,c,d]
    weight_list = [2,10,1,50]

    print print_weight(value_list, weight_list)

    values = [('a', 50),('b', 10),('c', 10),('d', 30),('e', 5),('f', 5)]

    print print_weight2(values)

########NEW FILE########
__FILENAME__ = reservoir_sampling
'''
Reservoir Sampling

'''

import random 

def random_subset( iterator, K ): 
    result = [] 
    counter = 0 
    for item in iterator: 
        counter += 1 
        if len( result ) < K: 
            result.append( item ) 
        else: 
            s = int(random.random() * counter) 
            if s < K: 
                result[ s ] = item 
    return result
########NEW FILE########
__FILENAME__ = reverse
#!/usr/bin/env python
'''
Reverse 

Input: string, sentenece or link

Out: reverse of what is submitted

Note: claudiay contributed additional example and test
'''

# Simple example of reversing a string
# However, pop is an expensive call and should be avoided in code that
# will be called many times
def reverse_str(string):
    rev_list=[]
    new_list=list(string)
    while new_list:
        rev_list += new_list[-1]
        new_list.pop()
    return ''.join(rev_list)

# Neat reverse string trick in python - O(n)
def reverse_str2(string):
    return string[::-1]


# Reversed function - constant space - O(n)
def reverse_str3(string):
    return ''.join(reversed(string))


# Constant space - O(logn)
def reverse_str4(string):
    string_list = list(string)
    for i in range(int((len(string))/2)):
        # Swap values in array.
        string_list[i], string_list[-1-i] = string_list[-1-i], string_list[i]
    return ''.join(string_list)

# Constant space - O(logn)
def reverse_str5(string):
    list_str = list(string)
    length = len(list_str)
    if length <= 1:
        return string
    else:
        for i in range(int(length/2)):
            list_str[i],list_str[-1-i] = list_str[-1-i], list_str[i]
        return ''.join(list_str)

# O(n)
def reverse_sentence6(sentence):
    sent_list = sentence.split(' ')
    new_list = []
    for word in sent_list:
        new_list.append(reverse_str(word))
    return ' '.join(new_list)


# Reverse a string and replace capitalize vowels
def cap(char):
    if char in 'aeiou':
        return char.upper()
    return char

# Constant space - O(logn)
def reverse_sentence7(sent):
    # Anti-Marxist style of reversing strings. 
    alist = list(sent)
    for i in range(int(len(alist)/2)):
        alist[i], alist[-1-i] = cap(alist[-1-i]), cap(alist[i])
    return ''.join(alist)

# Constant space - O(logn)
def reverse_list(alist):
    for num in range(int(len(alist)/2)):
        alist[num], alist[-1-num] = alist[-1-num], alist[num]
    return alist

#O(n)
def reverse_list2(alist):
    return alist[::-1]    


if __name__ == '__main__':

    # Test section
    print "reverse_str:\t", reverse_str("string")
    print "reverse_str2:\t", reverse_str2("string")
    print "reverse_str3:\t", reverse_str3("string")
    print "reverse_str4:\t", reverse_str4("string")
    print "reverse_str5:\t", reverse_str5("string")

    
    print "reverse_sentence6:\t", reverse_sentence6("The lazy brown fox.")
    print "reverse_sentence7:\t", reverse_sentence7("The lazy brown fox.")
    print "reverse_list:\t", reverse_list([i for i in range(10)])
    print "reverse_list2:\t", reverse_list2([i for i in range(10)])


########NEW FILE########
__FILENAME__ = rock_paper_scissors
'''
Rock / Paper / Scissors

Opponent Plays:
60% Rock
30% Scissors
10% Paper

Play 10 rounds and get $10 if you win 
What is the most optimal hand to play with what you know of your opponent?
Score / Points gain
win = +1 Point
lose = -1 Point
Tie = 0 Points

Input: score, round
Output: expected value
'''

def rock_game(round, score):
    if round == 0:
        if score > 0:
            return $10
        elif score == 0:
            return $0
        else:
            return -$10
    else:
        r -= 1 
        # Take max expected value if you play rock vs play paper strategy 
        return max((.6rock_game(r, score+0)+.3rock_game(r, score+1)+.1rock_game(r, score-1)), (.6rock_game(r, score+1)+.3rock(_gamer, score-1)+.1rock_game(r, score+0)))

########NEW FILE########
__FILENAME__ = scramble
#!/usr/bin/env python
"""
Scramble

Input: .txt file of acceptable English words and a string of letters
Output: find all acceptable words

Example:
    Input: 'dog'
    Output: 'dog', 'god', 'go', 'do'

Two cases:
    1) Using a dict that maps a sorted tuple of letters to possible words.
        ex. d[('d', 'o', 'g')] = ['dog', 'god']
    2) Using a dict that only maps string word to True:
        ex. d['dog'] = True

What are the pros and cons of the different methods? In which situation(s)
would one be preferable over the other? Which is ~generally~ better?

Original problem/solution submission from claudiay
"""

# Create dict of acceptable words from file_name.
# Map a tuple of the sorted lettters to acceptable words
def create_dict(file_name):
    words = {}
    with open(file_name) as f:
        content = f.readlines()
    for word in content:
        word = word.strip()
        key = tuple(sorted(list(word)))
        if words.get(key, False):
            # Key already exists
            words[key].append(word)
        else:
            words[key] = [word]
    return words

# Create dict that maps word to True
# We don't have time to sort through all these words
def create_simple_dict(file_name):
    words = {}
    with open(file_name) as f:
        content = f.readlines()
    for word in content:
        word = word.strip()
        words[word] = True
    return words

# Similar to itertools.combinations()
# Iterates through all combinations of letters for length of r
def search(letters, r):
    n = len(letters)
    if r > n:
        return
    indices = range(r)
    yield tuple(letters[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i + 1, r):
            indices[j] = indices[j-1] + 1
        yield tuple(letters[i] for i in indices)

# O(n^2)
def unscramble(word, english):
    words = []
    word = sorted(word)

    for i in range(1, len(word) + 1):
        for subset in search(word, i):
            if english.get(subset, False):
                words += english.get(subset)
    return words

# Similar to itertools.permutations()
# Shuffle through all combinations found through search() - O(n^2)
def permutations(letters, r):
    n = len(letters)
    if r > n:
        return
    indices = range(n)
    cycles = range(n, n-r, -1)
    # Generator and list comprehension
    yield ''.join(letters[i] for i in indices[:r])
    while n:
        for i in reversed(range(r)):
            cycles[i] -= 1
            if cycles[i] == 0:
                indices[i:] = indices[i+1:] + indices[i:i+1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                yield ''.join(letters[i] for i in indices[:r])
                break
        else:
            return

# O(n^2)
def unscramble_simple_dict(word, english):
    words = []
    
    for i in range(1, len(word) + 1):
        for subset in permutations(word, i):
            if english.get(subset, False):
                words.append(subset)
    return words


#Test section
if __name__ == '__main__':
    english = create_dict('words.txt')
    print "Dictionary created."
    print unscramble('dog', english)
    print unscramble('yawn', english)

    english = create_simple_dict('words.txt')
    print "Dictionary created."
    print unscramble_simple_dict('dog', english)
    print unscramble_simple_dict('yawn', english)


########NEW FILE########
__FILENAME__ = seat_circle
'''
Seat Circle

Input: 100 chairs in a circle and they are labeled from 1 to 100

Condition: 
Pattern of change is that seat 1 is asked to leave, seat 2 is asked to stay, seat 3 is asked to leave...
Pattern continues of skipping one and asking one to leave till only one is left

Output: Return who the last person left
'''

# Pseudo coded answer in class
def last_person(seats):
    pop_odd = True
    while len(seats) > 1:
        for i, seat in enumerate(seats):
            if pop_odd and i % 2 == 1:
                del seats[i]
            elif not pop_odd and i % 2 == 0:
                del seats[i]

# Melanie - correct answer
def last_person2(seats):
    # Skip marker for first num in list if last num in is deleted from previous loop
    skip = False 
    while len(seats) > 1:
        for index, seat in enumerate(seats):
            if skip:
                skip = False
            else:
                x = seats.pop(index)
            if index == len(seats):
                skip = True
    return seats

# Erica - incorrect copy - need to fix
def last_person3(seats):
    odd_toggle = 0
    while len(seats) > 1:
        if len(seats) % 2 == 0 and odd_toggle == 0:
            del seats[odd_toggle::2]
        elif len(seats) % 2 == 0 and odd_toggle == 1:
            del seats[odd_toggle::2]
        elif len(seats) % 2 == 1 and odd_toggle == 0:
            del seats[odd_toggle::2]
            odd_toggle = 1
        else:
            del seats[odd_toggle::2]
            odd_toggle == 0
    return seats

# Jesse - List comprehension - needs adjustment
def last_person4(seats):
    while len(seats) > 1:
        pop_odd = (len(seats) % 2 == 0)

        if pop_odd:
            seats = [seat for i, seat in enumerate(seats) if i % 2 == 0]
        else:
            seats = [seat for i, seat in enumerate(seats) if i % 2 == 1]

    return seats

#Test section
if __name__ == '__main__':

    implementations = [last_person2, last_person3, last_person4]



    for impl in implementations:
        seats = [i for i in range(1,101)] # Use pop = the var has to be reset each loop
        print '%s returns %s' % (impl.__name__, impl(seats))


########NEW FILE########
__FILENAME__ = sentence_sort
#!/usr/bin/env python
"""
Sentence Sort

Input: sentence

Output: sort a sentence by length of words

Example:

 Input:  "This is a fun interview"
 Output: "a is fun this interview"

Original problem/solution submission from jofusa
"""


def pythonic_approach(sentence):
    """
    This utilize's python's first class functions and the optional paramater to sort arrays
    """
    return ' '.join(sorted(sentence.split(), key = len))

########NEW FILE########
__FILENAME__ = test_sentence_sort
#!/usr/bin/env python
'''
Sentence Sort Test

Test file for sentence_sort problem

Original problem/solution submission from jofusa
'''

from sentence_sort import *

def test_sentence_sort():
    test = "This is the First"
    assert "is the This First" ==  pythonic_approach(test)


########NEW FILE########
__FILENAME__ = split
#!/usr/bin/env python
'''
Split

Input: string and and character to split on
Output: create list with the string split based on character submitted

Challenge: How to run it with no split value?

'''

def split(string, char=None):
    create_list = []
    start,stop = 0,0
    if char==None:
        char = ''
    for i, letter in enumerate(string):
        if letter == char: 
            stop = i
            create_list.append(string[start:stop])
            start = i+1
        if i == (len(string)-1):
            create_list.append(string[start:len(string)])
    return create_list

if __name__ == '__main__':
    # Test section
    print split('s p l i t', ' ')


########NEW FILE########
__FILENAME__ = sqroot
'''
Find the square root of n.

    Input: A number
    Output: The square root or the integers closest to the square root
    Assume: positive n

 Newton's method is a popular solution for square root, but not implemented here.
'''

def sqrt(n):
    for number in range(0, n):
        if isSqrt(number,n):
            return number
        else:
            if n < number * number:
                return number, number - 1


def isSqrt(a,b):
    '''
    Helper function to use in sqrt function to calculate number squared
    '''
    if a * a == b:
        return True
    else:
        return False


# Test Section
if __name__ == '__main__':
    print "sqrt(25) = 5: %s" % (sqrt(25) == 5)
    print "sqrt(30) = (6, 5): %s" % (sqrt(30) == (6,5))


########NEW FILE########
__FILENAME__ = square
#!/usr/bin/env python
''' 
Square

Input: number
Ouput: number squared
'''

#Simple solution - O(1)
def square(num):
    return num * num

#Loop / list comprehension solution - O(n)
def square2(num):
    return sum([num for n in range(num)])

if __name__ == '__main__':
    #Test section
    implementations = [square, square2]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(0) == 0: %s" % (impl(0) == 0)
        print "  f(1) == 1: %s" % (impl(1) == 1)
        print "  f(2) == 4: %s" % (impl(2) == 4)
        print "  f(3) == 9: %s" % (impl(3) == 9)
        print "  f(10) == 100: %s" % (impl(10) == 100)

########NEW FILE########
__FILENAME__ = string_lacing
'''
String Lacing

s1 and s2 are strings.

Returns a new str with elements of s1 and s2 interlaced,
beginning with s1. If strings are not of same length, 
then the extra elements should appear at the end.
'''


def laceStrings(s1, s2):
    size = min(len(s1), len(s2))
    longest_str = max(s1,s2)
    result = ''

    for i in range(size):
        result += s1[i] + s2[i]
    
    return result + longest_str[size:]

def laceStringsRecur(s1, s2):

    def helpLaceStrings(s1, s2, out):
        if s1 == '':
            return s2
        if s2 == '':
            return s1
        else:
            return s1[0] + s2[0] + helpLaceStrings(s1[1:], s2[1:], '')
            # return  out + helpLaceStrings(s1[1:], s2[1:], s1[0] + s2[0])

    return helpLaceStrings(s1, s2, '')

if __name__ == '__main__':

    # Test section    
    test_func = laceStrings
    string1 = ['abcd', '  ', 'ttt', '', 'and', 'treehousego']
    string2 = ['efghi', 'abc', 'ccc', '', 'treehousego', 'a']
    results = ['aebfcgdhi', ' a bc', 'tctctc', '', 'atnrdeehousego', 'tareehousego']

    for i in range(len(results)):
        print "trying %s" % test_func
        print "f(%s, %s) == %s: %s" % (string1[i], string2[i], results[i], test_func(string1[i],string2[i]) == results[i])
        print test_func(string1[i],string2[i])

########NEW FILE########
__FILENAME__ = string_match
#!/usr/bin/env python
'''
String Match
Find if a smaller string exists and/or can be created out of a larger string.

Input: Two strings
Output: True if the smaller string exists in the larger string

Known as ransome note or needle in a haystack.

'''

#Ransome note example find out if the letters are in the mag
#Split in two functions which equal nested loops - O(n^2)
def mag_dict(magazine):
    mag_hash = {}
    for i in magazine:
        mag_hash[i] = mag_hash.get(i, 0) + 1
    return mag_hash


def match(mag, note):
    mdict = mag_dict(mag)
    for i in note:
        if i in mdict:
            mdict[i] -= 1
        else:
            return False
    return True


#Check which string would be a subset assuming the order submitted changes
def find_main_str(str1, str2):
    if len(str1) > len(str2):
        return (str1, str2)
    else:
        return (str2, str1)

#O(n)
def match2(str1,str2):
    large, small = find_main_str(str1,str2)

    if small in large:
        return True


#Embedded loop solution. - O(n+m)
def match3(s1,s2):
    state = False
    for i, char in enumerate(s1):
        if s2[0] == char:
            j=0
            while j < len(s2):
                if i+j < len(s1):
                    if s2[j] != s1[i+j]:
                        break
                    else: 
                        state = True
                        j += 1
                else:
                    break
    return state

#Boyer Moore Algorithm approach - compare starting end of string 
#check each subset of the main string whether the last character is
#included. If not then shift out another subset. - O(n-m)

#Note: still not functioning properly - need to account for end of string

def match4(s1,s2):
    j_d = {}
    for c in s1:
        j_d[c] = True

    i = len(s2)-1
    while i < len(s1):
        if not j_d.get(s1[i]):
            if i >= len(s1):
                i = len(s1)-1
            else:
                i += len(s2)
        else:    
            j = len(s2)-1            
            while j >= 0: 
                found = False
                a = 0
                print 1, s2[j]
                print 2, s1[i]
                print 3, j

                if s2[j] != s1[i]:
                    break
                
                j -= 1
                i -= 1
            
            i += len(s2)-1

        if j == -1:
            found = True
            break


    return found

if __name__ == '__main__':
    #Test section
    str1 = 'Cat goes crazy'
    str1a = 'crazy'
    str1b = 'Cat'

    str2 = 'this is a hash'
    str2a = 'hash'
    str2b = 'not'

    result = True
    result2 = False

    implementations = [match, match2, match3]

    for impl in implementations:
        print "trying %s" % impl
        print "f(%s) == %s: %s" % (str1a, result, (impl(str1, str1a) == result))
        print "f(%s) == %s: %s" % (str1b, result, (impl(str1, str1b) == result))
        print "f(%s) == %s: %s" % (str2a, result, (impl(str2, str2a) == result))
        print "f(%s) == %s: %s" % (str2b, result2, (impl(str2, str2b) == result2))



########NEW FILE########
__FILENAME__ = sum_target
#!/usr/bin/env python
'''
Sum Target

Input: List of numbers & target number 
Output: Each pair of numbers that adds up to target

Challenge: 
*For a list of numbers and a target number, return true if any two numbers add to the target number
*Given a list of numbers, return a set of 3 numbers that add to 0.
'''
import itertools

#Functions provide true/false results

# Embedded loops. - O(n^2)
def sum_target(target, num_list):
    ans = False
    for i in num_list:
        for j in num_list:
            if (i+j) == target:
                ans = True
    return ans

#Recursive solution. - O(n)
def sum_target2(target, num_list):
    if len(num_list) <= 1 and num_list[0] != target:
        return False
    elif num_list[-2]:
        if (num_list[-2]+num_list[-1]) == target:
            return True
        else:
            return sum_target2(target, num_list[:-1])
    else:
        return False


#Functions provide lists answers

#O(n^2)
def sum_target3(target, num_list):
    pairs = []
    for index, elem in enumerate(num_list):
        for i in num_list[index+1:]:
            if (elem + i) == target:
                if [elem, i] not in pairs and [i, elem] not in pairs:
                    pairs.append([elem,i])
    return pairs

#Broken down into multiple functions. - O(n^2)
#Finds if the numbers sum to 0.
def sum_num(target, num_1, num_2):
    return (num_1 + num_2 == target)

#
def compare_val(target, val, num_list):
    for i in num_list:
        if sum_num(target,val,i):
                return [val, i]

def sum_target4(target, num_list):
    pairs = []
    for index, val in enumerate(num_list):
        if compare_val(target, val, num_list[index+1:]):
            a, b = compare_val(target, val, num_list[index+1:])
            if [a, b] not in pairs and [b, a] not in pairs:
                pairs.append(compare_val(target, val, num_list[index+1:]))
    return pairs

#Solution with dictionary but still embedded loops. - O(n^2)
def sum_target5(target, num_list):
    pairs = {}

    for val in num_list:
        remain = target - val
        if remain in num_list and remain not in pairs: # in is O(n) because used against list
            pairs[val] = remain
    return pairs


#O(n^2) - very similar to 5
def sum_target6(target, num_list):
    pairs = {}

    for num in num_list:
        remain = target - num
        if (target - (num + remain)) == 0 and remain not in pairs:
            pairs[num] = remain
    
    return pairs


if __name__ == '__main__':
    #Test section
    num_list = [5,3,5,7,1,2,5,6]
    num_list2 = [0,-1,5,0,3,1]
    target = 20
    target2 = 8
    target3 = 0

    #True/false results
    result = True
    result2 = False

    implementations = [sum_target, sum_target2]

    for impl in implementations:
        print "trying %s" % impl
        print "f(%s) == []: %s" % (target, impl(target, num_list) == result2)
        print "f(%s) == [5,3] or [7,1]: %s" % (target2, impl(target2, num_list) == result)
        print "f(%s) == []: %s" % (target3, impl(target3, num_list) == result2)


    #List of values results
    result3 = []
    result4 = [[5,3],[7,1],[2,6]]
    result5 = []

    implementations2 = [sum_target3, sum_target4]
    for impl in implementations2:
        print "trying %s" % impl
        print "f(%s) == %s: %s" % (num_list, target, impl(target, num_list) == result3)
        print "f(%s) == %s: %s" % (num_list, target2, impl(target2, num_list) == result4)
        print "f(%s) == %s: %s" % (num_list, target3, impl(target3, num_list) == result5)
        print impl(target2, num_list)

    result6 = {2: 6, 5: 3, 7: 1}

    implementations2 = [sum_target5, sum_target6]

    for impl in implementations2:
        print "trying %s" % impl
        print "f(%s) == %s: %s" % (num_list, target2, impl(target2, num_list) == result6)

########NEW FILE########
__FILENAME__ = sum_target_bool
'''
Sum Target / Combination Validation

n is an int

Returns True if some integer combination of 6, 9 and 20 equals n
Otherwise returns False.

'''
from __future__ import division # brings in math from python 3.0
import time

# O(n^3)
def target_combo(n):
    a = b = c = 0
    while (6 * a) <= n:
        while (9 * b) <= n:
            while (20 * c) <= n:
                ans = (6 * a) + (9 * b) + (20 * c)
                if ans == n:
                    return True
                c += 1
            c = 0
            b += 1
        c = b = 0
        a += 1

    return False

# O(1) - because combo sizes are fixed
def target_combo2(n):
    combo_sizes = [20, 9, 6]
    remaining = n
    for combo_size in combo_sizes:
        remaining -= (remaining // combo_size) * combo_size
    return remaining == 0

def do_thing(thing, *args):
    start = time.time()
    thing(*args)
    return time.time() - start

if __name__ == '__main__':

    # Test section
    implementations = [target_combo, target_combo2]

    for impl in implementations:
        print "trying %s" % impl
        print "  f(6) is %s" % (impl(6)==True)
        print "  f(7) is %s" % (impl(7)==False)
        print "  f(100000000) is %s seconds" % (do_thing(impl, 100000000))

########NEW FILE########
__FILENAME__ = test
list = [5,3,7,5,1,2,5,6]
target = 10

def add(list, target):
	#make a dictionary of nums in the list
	#to make the lookup faster
	num_dict = {}
	for i, num in enumerate(list):
		if num not in num_dict:
			num_dict[num] = [i]
		else:
			num_dict[num].append(i)

	# now go through each number in the list
	for i, num in enumerate(list):
		diff = target - num

		#this is for, for example, 
		#if you're looking for 10
		#and you get a 5 in the list
		#you need another 5
		if diff == num:
			if len(num_dict[num]) > 1:
				return True
		#look for the difference in the dict. 
		#if it's there then you've got
		#your sum
		if diff in num_dict:
			return True
	return False

# putting the list in a dictionary first
# passes through the list once, giving it 
# a time of n, then going through the 
# the list again is another n which makes
# 2n. Since integers don't matter much 
# it's n time. 







l1 = [5,4,7,2,1,8,3]
l2 = [8,1,2,7,5,3]
# missing number = 4

def missing(l1, l2):
	l1.sort()
	l2.sort()

	if len(l1) > len(l2):
		longest = l1
		second = l2
	else:
		longest = l2
		second = l1


	for i, num in enumerate(longest):
		if i == len(longest)-1:
			return longest[i]
		elif num != second[i]:
			return num

# This is bad n time because the sort algorithm takes 
# some amount of time (i don't know because it's set
# by the programming language, then n again to go through
# the list again.)

# The best way to do it is add both lists up
# and subtract them 
# sum(l1) = 30
# sum(l2) = 26
# difference is 4 :)


########NEW FILE########
__FILENAME__ = tic_tac_toe
'''
Tic-tac-toe

Input: Define the class to build a Tic-tac-toe board and game
Output: Run a game and return the winner

'''

class Board():
    def __init__(self):
        self._b=[
        [Tile(None), Tile(None), Tile(None)]
        [Tile(None), Tile(None), Tile(None)]
        [Tile(None), Tile(None), Tile(None)]
        ]
    def play(self, piece, row, col):
        r = self._b[row]
        r[col] = piece

        OR 

        self._b[row][col] = piece

    def score(self, row, col):
        return self._b[row][col]

class Tile():
    def __init__(self, val):
        self.val = val

if __name__ == '__main__':
    #Test section

    b = Board()
    player = "X"
    while b.score()==None:
        row = raw_input("row?")
        col = raw_input("column?")
        b.play(player, row, col)
        if player =="X":
            player = "O"
        else:
            player = "X"

    print "Player", b.score(), "wins!"

########NEW FILE########
__FILENAME__ = tmp_seat
# List comprehension
def last_person4(seats):
    while len(seats) > 1:
        print "seats> (0!r)".format(seats)
        pop_odd = (len(seats) % 2 == 0)

        if pop_odd:
            seats = [seat for i, seat in enumerate(seats) if i % 2 == 0]
        else:
            seats = [seat for i, seat in enumerate(seats) if i % 2 == 1]
        raw_input('press_enter')

    return seats

print last_person4(seats = [i for i in range(1, 101)])
########NEW FILE########
__FILENAME__ = turn_matrix
#!/usr/bin/env python
'''
Turn Matrix

Input: 3x3 matrix of integers

Output: Rotate the matrix by 90 degrees and return rotated matrix

Example:

1 2 3
4 5 6 
7 8 9

Switch to:

7 4 1
8 5 2
9 6 3

'''


#Set data structure as a list of coordinates
def flip_matrix(mat):
    mid = int(len(matrix/6))
    for i, coord in enumerate(matrix):
        if i == 0:
            pass
        # if x is 1 then it just flips x & y
        elif mid == coord[0]:
            coord[0], coord[1] = coord[1], coord[0]
        # if x is less than 1 then x becomes y and y becomes 2
        elif mid > coord[1]:
            coord[0] = coord[1]
            coord[1] = mid + 1
        # if x is greater than 1 then x becomes y and y becomes 1
        elif mid < coord[0]:
            coord[0] = coord[1]
            coord[1] = mid - 1


#Improved approach is new[x,y] = old [y,2-x]

"""
Input: Given an NxN matrix

Output: Rotate the matrix by 90 degrees and return rotated matrix.

Example:
    input: 
           [[1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16]]
    output:
           [[13, 9, 5, 1],
            [14, 10, 6, 2],
            [15, 11, 7, 3],
            [16, 12, 8, 4]]

Note: claudiay contributed additional example and test
"""

# Short without zip
def rotate(matrix):
    return [[j[i] for j in matrix][::-1] for i in range(len(matrix))]

# Python trick answer, returns an array with tuples
def rotate_with_zip(matrix):
    return zip(*matrix[::-1])

# A expanded version to explain each step
def rotate_explain(matrix):
    n = len(matrix)
    new_matrix = []

    for i in range(n):
        new_row = []
        for row in matrix:
            new_row.append(row[i])
        new_matrix.append(new_row[::-1]) # Reverse new_row before appending.
    
    return new_matrix

# Rotate the matrix in place, without creating another matrix
# Ideal for situations processing a large matrix with limited space
def rotate_in_place(matrix):
    n = len(matrix)
    for i in range(n/2):
        for j in range(n/2 + n%2):
            swap = matrix[i][j]
            for k in range(4):
                swap, matrix[j][n-i-1] = matrix[j][n-i-1], swap
                i, j = j, n - i - 1
    
    return matrix


if __name__ == '__main__':
    # Test section
    matrix = [[1, 2, 3, 4],
              [5, 6, 7, 8],
              [9, 10, 11, 12],
              [13, 14, 15, 16]]
    
    odd_matrix = [[0, 1, 2, 3, 4],
                  [5, 6, 7, 8, 9],
                  [10, 11, 12, 13, 14],
                  [15, 16, 17, 18, 19],
                  [20, 21, 22, 23, 24]]

    #Test section
    print rotate(matrix)
    print rotate_with_zip(matrix)
    print rotate_explain(matrix)
    print rotate_in_place(matrix)


    print rotate(odd_matrix)
    print rotate_with_zip(odd_matrix)
    print rotate_explain(odd_matrix)
    print rotate_in_place(odd_matrix)


########NEW FILE########
__FILENAME__ = winetasting
'''
Wine Tasting

A large group of friends from the town of Nocillis visit the vineyards of Apan to taste wines.
The vineyards produce many fine wines and the friends decide to buy as many as 3 bottles of wine each if they are available to purchase.
Unfortunately, the vineyards of Apan have a peculiar restriction that they can not sell more than one bottle of the same wine.
So the vineyards come up with the following scheme:
They ask each person to write down a list of up to 10 wines that they enjoyed and would be happy buying.
With this information, please help the vineyards maximize the number of wines that they can sell to the group of friends.

Input
A two-column TSV file with the first column containing the ID (just a string) of a person and the second column the ID of the wine that they like.
Here are three input data sets of increasing sizes. Please send us solutions even if it runs only on the first file.

https://s3.amazonaws.com/br-user/puzzles/person_wine_3.txt
https://s3.amazonaws.com/br-user/puzzles/person_wine_4.txt.zip
https://s3.amazonaws.com/br-user/puzzles/person_wine_5.txt.zip

Output
First line contains the number of wine bottles sold in aggregate with your solution.
Each subsequent line should be two columns, tab separated.
The first column is an ID of a person and the second column should be the ID of the wine that they will buy.

Please check your work.
Note that the IDs of the output second column should be unique since a single bottle of wine can not be sold to two people
and an ID on the first column can appear at most three times since each person can only buy up to 3 bottles of wine.
'''

########NEW FILE########
