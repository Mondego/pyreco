__FILENAME__ = tf-01
#!/usr/bin/env python

import sys, os, string

# Utility for handling the intermediate 'secondary memory'
def touchopen(filename, *args, **kwargs):
    try:
        os.remove(filename)
    except OSError:
        pass
    open(filename, "a").close() # "touch" file
    return open(filename, *args, **kwargs)

# The constrained memory should have no more than 1024 cells
data = []
# We're lucky:
# The stop words are only 556 characters and the lines are all 
# less than 80 characters, so we can use that knowledge to 
# simplify the problem: we can have the stop words loaded in 
# memory while processing one line of the input at a time.
# If these two assumptions didn't hold, the algorithm would 
# need to be changed considerably.

# Overall strategy: (PART 1) read the input file, count the 
# words, increment/store counts in secondary memory (a file) 
# (PART 2) find the 25 most frequent words in secondary memory

# PART 1: 
# - read the input file one line at a time
# - filter the characters, normalize to lower case
# - identify words, increment corresponding counts in file

# Load the list of stop words
f = open('../stop_words.txt')
data = [f.read(1024).split(',')] # data[0] holds the stop words
f.close()

data.append([])    # data[1] is line (max 80 characters)
data.append(None)  # data[2] is index of the start_char of word
data.append(0)     # data[3] is index on characters, i = 0
data.append(False) # data[4] is flag indicating if word was found
data.append('')    # data[5] is the word
data.append('')    # data[6] is word,NNNN
data.append(0)     # data[7] is frequency

# Open the secondary memory
word_freqs = touchopen('word_freqs', 'rb+')
# Open the input file
f = open(sys.argv[1])
# Loop over input file's lines
while True:
    data[1] = [f.readline()] 
    if data[1] == ['']: # end of input file
        break
    if data[1][0][len(data[1][0])-1] != '\n': # If it does not end with \n
        data[1][0] = data[1][0] + '\n' # Add \n
    data[2] = None
    data[3] = 0 
    # Loop over characters in the line
    for c in data[1][0]: # elimination of symbol c is exercise
        if data[2] == None:
            if c.isalnum():
                # We found the start of a word
                data[2] = data[3]
        else:
            if not c.isalnum():
                # We found the end of a word. Process it
                data[4] = False 
                data[5] = data[1][0][data[2]:data[3]].lower()
                # Ignore words with len < 2, and stop words
                if len(data[5]) >= 2 and data[5] not in data[0]:
                    # Let's see if it already exists
                    while True:
                        data[6] = word_freqs.readline().strip()
                        if data[6] == '':
                            break;
                        data[7] = int(data[6].split(',')[1])
                        # word, no white space
                        data[6] = data[6].split(',')[0].strip() 
                        if data[5] == data[6]:
                            data[7] += 1
                            data[4] = True
                            break
                    if not data[4]:
                        word_freqs.seek(0, 1) # Needed in Windows
                        word_freqs.writelines("%20s,%04d\n" % (data[5], 1))
                    else:
                        word_freqs.seek(-26, 1)
                        word_freqs.writelines("%20s,%04d\n" % (data[5], data[7]))
                    word_freqs.seek(0,0)
                # Let's reset
                data[2] = None
        data[3] += 1
# We're done with the input file
f.close()
word_freqs.flush()

# PART 2
# Now we need to find the 25 most frequently occuring words.
# We don't need anything from the previous values in memory
del data[:]

# Let's use the first 25 entries for the top 25 words
data = data + [[]]*(25 - len(data))
data.append('') # data[25] is word,freq from file
data.append(0)  # data[26] is freq

# Loop over secondary memory file
while True:
    data[25] = word_freqs.readline().strip()
    if data[25] == '': # EOF
        break
    data[26] = int(data[25].split(',')[1]) # Read it as integer
    data[25] = data[25].split(',')[0].strip() # word
    # Check if this word has more counts than the ones in memory
    for i in range(25): # elimination of symbol i is exercise
        if data[i] == [] or data[i][1] < data[26]:
            data.insert(i, [data[25], data[26]]) 
            del data[26] #  delete the last element
            break
            
for tf in data[0:25]: # elimination of symbol tf is exercise
    if len(tf) == 2:
        print tf[0], ' - ', tf[1]
# We're done
word_freqs.close()

########NEW FILE########
__FILENAME__ = forth
#!/usr/local/bin/python
#
#   f o r t h . p y
#   Author: Chris Meyers @ 
#           http://openbookproject.net/py4fun/forth/forth.html
#
import sys, re

ds       = []          # The data stack
cStack   = []          # The control struct stack
heap     = [0]*2000    # The data heap
heapNext =  0          # Next avail slot in heap
words    = []          # The input stream of tokens

def main() :
    while 1 :
        pcode = compile()          # compile/run from user
        if pcode == None : print; return
        execute(pcode)

#============================== Lexical Parsing
        
def getWord (prompt="... ") :
    global words
    while not words : 
        try    : lin = raw_input(prompt)+"\n"
        except : return None
        if lin[0:1] == "@" : lin = open(lin[1:-1]).read()
        tokenizeWords(lin)
    word = words[0]
    words = words[1:]
    return word

def tokenizeWords(s) :
    global words                                          # clip comments, split to list of words
    words += re.sub("#.*\n","\n",s+"\n").lower().split()  # Use "#" for comment to end of line

#================================= Runtime operation

def execute (code) :
    p = 0
    while p < len(code) :
        func = code[p]
        p += 1
        newP = func(code,p)
        if newP != None : p = newP

def rAdd (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(a+b)
def rMul (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(a*b)
def rSub (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(a-b)
def rDiv (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(a/b)
def rEq  (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(int(a==b))
def rGt  (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(int(a>b))
def rLt  (cod,p) : b=ds.pop(); a=ds.pop(); ds.append(int(a<b))
def rSwap(cod,p) : a=ds.pop(); b=ds.pop(); ds.append(a); ds.append(b)
def rDup (cod,p) : ds.append(ds[-1])
def rDrop(cod,p) : ds.pop()
def rOver(cod,p) : ds.append(ds[-2])
def rDump(cod,p) : print "ds = ", ds
def rDot (cod,p) : print ds.pop()
def rJmp (cod,p) : return cod[p]
def rJnz (cod,p) : return (cod[p],p+1)[ds.pop()]
def rJz  (cod,p) : return (p+1,cod[p])[ds.pop()==0]
def rRun (cod,p) : execute(rDict[cod[p]]); return p+1
def rPush(cod,p) : ds.append(cod[p])     ; return p+1

def rCreate (pcode,p) :
    global heapNext, lastCreate
    lastCreate = label = getWord()      # match next word (input) to next heap address
    rDict[label] = [rPush, heapNext]    # when created word is run, pushes its address

def rDoes (cod,p) :
    rDict[lastCreate] += cod[p:]        # rest of words belong to created words runtime
    return len(cod)                     # jump p over these

def rAllot (cod,p) :
    global heapNext
    heapNext += ds.pop()                # reserve n words for last create

def rAt  (cod,p) : ds.append(heap[ds.pop()])       # get heap @ address
def rBang(cod,p) : a=ds.pop(); heap[a] = ds.pop()  # set heap @ address
def rComa(cod,p) :                                 # push tos into heap
    global heapNext
    heap[heapNext]=ds.pop()
    heapNext += 1

rDict = {
  '+'  : rAdd, '-'   : rSub, '/' : rDiv, '*'    : rMul,   'over': rOver,
  'dup': rDup, 'swap': rSwap, '.': rDot, 'dump' : rDump,  'drop': rDrop,
  '='  : rEq,  '>'   : rGt,   '<': rLt,
  ','  : rComa,'@'   : rAt, '!'  : rBang,'allot': rAllot,

  'create': rCreate, 'does>': rDoes,
}
#================================= Compile time 

def compile() :
    pcode = []; prompt = "Forth> "
    while 1 :
        word = getWord(prompt)  # get next word
        if word == None : return None
        cAct = cDict.get(word)  # Is there a compile time action ?
        rAct = rDict.get(word)  # Is there a runtime action ?

        if cAct : cAct(pcode)   # run at compile time
        elif rAct :
            if type(rAct) == type([]) :
                pcode.append(rRun)     # Compiled word.
                pcode.append(word)     # for now do dynamic lookup
            else : pcode.append(rAct)  # push builtin for runtime
        else :
            # Number to be pushed onto ds at runtime
            pcode.append(rPush)
            try : pcode.append(int(word))
            except :
                try: pcode.append(float(word))
                except : 
                    pcode[-1] = rRun     # Change rPush to rRun
                    pcode.append(word)   # Assume word will be defined
        if not cStack : return pcode
        prompt = "...    "
    
def fatal (mesg) : raise mesg

def cColon (pcode) :
    if cStack : fatal(": inside Control stack: %s" % cStack)
    label = getWord()
    cStack.append(("COLON",label))  # flag for following ";"

def cSemi (pcode) :
    if not cStack : fatal("No : for ; to match")
    code,label = cStack.pop()
    if code != "COLON" : fatal(": not balanced with ;")
    rDict[label] = pcode[:]       # Save word definition in rDict
    while pcode : pcode.pop()

def cBegin (pcode) :
    cStack.append(("BEGIN",len(pcode)))  # flag for following UNTIL

def cUntil (pcode) :
    if not cStack : fatal("No BEGIN for UNTIL to match")
    code,slot = cStack.pop()
    if code != "BEGIN" : fatal("UNTIL preceded by %s (not BEGIN)" % code)
    pcode.append(rJz)
    pcode.append(slot)

def cIf (pcode) :
    pcode.append(rJz)
    cStack.append(("IF",len(pcode)))  # flag for following Then or Else
    pcode.append(0)                   # slot to be filled in

def cElse (pcode) :
    if not cStack : fatal("No IF for ELSE to match")
    code,slot = cStack.pop()
    if code != "IF" : fatal("ELSE preceded by %s (not IF)" % code)
    pcode.append(rJmp)
    cStack.append(("ELSE",len(pcode)))  # flag for following THEN
    pcode.append(0)                     # slot to be filled in
    pcode[slot] = len(pcode)            # close JZ for IF

def cThen (pcode) :
    if not cStack : fatal("No IF or ELSE for THEN to match")
    code,slot = cStack.pop()
    if code not in ("IF","ELSE") : fatal("THEN preceded by %s (not IF or ELSE)" % code)
    pcode[slot] = len(pcode)             # close JZ for IF or JMP for ELSE

cDict = {
  ':'    : cColon, ';'    : cSemi, 'if': cIf, 'else': cElse, 'then': cThen,
  'begin': cBegin, 'until': cUntil,
}
  
if __name__ == "__main__" : main()

########NEW FILE########
__FILENAME__ = tf-02
#!/usr/bin/env python
import sys, re, operator, string

#
# The all-important data stack
#
stack = []

#
# The heap. Maps names to data (i.e. variables)
#
heap = {}

#
# The new "words" (procedures) of our program
#
def read_file():
    """
    Takes a path to a file on the stack and places the entire
    contents of the file back on the stack.
    """
    f = open(stack.pop())
    # Push the result onto the stack
    stack.append([f.read()])
    f.close()

def filter_chars():
    """
    Takes data on the stack and places back a copy with all 
    nonalphanumeric chars replaced by white space. 
    """
    # This is not in style. RE is too high-level, but using it
    # for doing this fast and short. Push the pattern onto stack
    stack.append(re.compile('[\W_]+'))
    # Push the result onto the stack
    stack.append([stack.pop().sub(' ', stack.pop()[0]).lower()])

def scan():
    """
    Takes a string on the stack and scans for words, placing
    the list of words back on the stack
    """
    # Again, split() is too high-level for this style, but using
    # it for doing this fast and short. Left as exercise.
    stack.extend(stack.pop()[0].split())

def remove_stop_words():
    """ 
    Takes a list of words on the stack and removes stop words.
    """
    f = open('../stop_words.txt')
    stack.append(f.read().split(','))
    f.close()
    # add single-letter words
    stack[-1].extend(list(string.ascii_lowercase))
    heap['stop_words'] = stack.pop()
    # Again, this is too high-level for this style, but using it
    # for doing this fast and short. Left as exercise.
    heap['words'] = []
    while len(stack) > 0:
        if stack[-1] in heap['stop_words']:
            stack.pop() # pop it and drop it
        else:
            heap['words'].append(stack.pop()) # pop it, store it
    stack.extend(heap['words']) # Load the words onto the stack
    del heap['stop_words']; del heap['words'] # Not needed 
    
def frequencies():
    """
    Takes a list of words and returns a dictionary associating
    words with frequencies of occurrence.
    """
    heap['word_freqs'] = {}
    # A little flavour of the real Forth style here...
    while len(stack) > 0:
        # ... but the following line is not in style, because the 
        # naive implementation would be too slow
        if stack[-1] in heap['word_freqs']:
            # Increment the frequency, postfix style: f 1 +
            stack.append(heap['word_freqs'][stack[-1]]) # push f
            stack.append(1) # push 1
            stack.append(stack.pop() + stack.pop()) # add
        else:
            stack.append(1) # Push 1 in stack[2]
        # Load the updated freq back onto the heap
        heap['word_freqs'][stack.pop()] = stack.pop()  

    # Push the result onto the stack
    stack.append(heap['word_freqs'])
    del heap['word_freqs'] # We don't need this variable anymore

def sort():
    # Not in style, left as exercise
    stack.extend(sorted(stack.pop().iteritems(), key=operator.itemgetter(1)))

# The main function
#
stack.append(sys.argv[1])
read_file(); filter_chars(); scan(); remove_stop_words()
frequencies(); sort()

stack.append(0)
# Check stack length against 1, because after we process
# the last word there will be one item left
while stack[-1] < 25 and len(stack) > 1:
    heap['i'] = stack.pop()
    (w, f) = stack.pop(); print w, ' - ', f
    stack.append(heap['i']); stack.append(1)
    stack.append(stack.pop() + stack.pop())


########NEW FILE########
__FILENAME__ = tf-03
#!/usr/bin/env python

import sys, string
# the global list of [word, frequency] pairs
word_freqs = []
# the list of stop words
with open('../stop_words.txt') as f:
    stop_words = f.read().split(',')
stop_words.extend(list(string.ascii_lowercase))

# iterate through the file one line at a time 
for line in open(sys.argv[1]):
    start_char = None
    i = 0
    for c in line:
        if start_char == None:
            if c.isalnum():
                # We found the start of a word
                start_char = i
        else:
            if not c.isalnum():
                # We found the end of a word. Process it
                found = False
                word = line[start_char:i].lower()
                # Ignore stop words
                if word not in stop_words:
                    pair_index = 0
                    # Let's see if it already exists
                    for pair in word_freqs:
                        if word == pair[0]:
                            pair[1] += 1
                            found = True
                            found_at = pair_index
                            break
                        pair_index += 1
                    if not found:
                        word_freqs.append([word, 1])
                    elif len(word_freqs) > 1:
                        # We may need to reorder
                        for n in reversed(range(pair_index)):
                            if word_freqs[pair_index][1] > word_freqs[n][1]:
                                # swap
                                word_freqs[n], word_freqs[pair_index] = word_freqs[pair_index], word_freqs[n]
                                pair_index = n
                # Let's reset
                start_char = None
        i += 1

for tf in word_freqs[0:25]:
    print tf[0], ' - ', tf[1]


########NEW FILE########
__FILENAME__ = tf-04
#!/usr/bin/env python
import sys, string

# The shared mutable data
data = []
words = []
word_freqs = []

#
# The procedures
#
def read_file(path_to_file):
    """
    Takes a path to a file and assigns the entire
    contents of the file to the global variable data
    """
    global data
    with open(path_to_file) as f:
        data = data + list(f.read())

def filter_chars_and_normalize():
    """
    Replaces all nonalphanumeric chars in data with white space
    """
    global data
    for i in range(len(data)):
        if not data[i].isalnum():
            data[i] = ' '
        else:
            data[i] = data[i].lower()

def scan():
    """
    Scans data for words, filling the global variable words
    """
    global data
    global words
    data_str = ''.join(data)
    words = words + data_str.split()

def remove_stop_words():
    global words
    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    # add single-letter words
    stop_words.extend(list(string.ascii_lowercase))
    indexes = []
    for i in range(len(words)):
        if words[i] in stop_words:
            indexes.append(i)
    for i in reversed(indexes):
        words.pop(i)

def frequencies():
    """
    Creates a list of pairs associating
    words with frequencies 
    """
    global words
    global word_freqs
    for w in words:
        keys = [wd[0] for wd in word_freqs]
        if w in keys:
            word_freqs[keys.index(w)][1] += 1
        else:
            word_freqs.append([w, 1])

def sort():
    """
    Sorts word_freqs by frequency
    """
    global word_freqs
    word_freqs.sort(lambda x, y: cmp(y[1], x[1]))


#
# The main function
#
read_file(sys.argv[1])
filter_chars_and_normalize()
scan()
remove_stop_words()
frequencies()
sort()

for tf in word_freqs[0:25]:
    print tf[0], ' - ', tf[1]


########NEW FILE########
__FILENAME__ = tf-05
#!/usr/bin/env python
import sys, re, operator, string

#
# The functions
#
def read_file(path_to_file):
    """
    Takes a path to a file and returns the entire
    contents of the file as a string
    """
    with open(path_to_file) as f:
        data = f.read()
    return data

def filter_chars_and_normalize(str_data):
    """
    Takes a string and returns a copy with all nonalphanumeric 
    chars replaced by white space
    """
    pattern = re.compile('[\W_]+')
    return pattern.sub(' ', str_data).lower()

def scan(str_data):
    """
    Takes a string and scans for words, returning
    a list of words.
    """
    return str_data.split()

def remove_stop_words(word_list):
    """ 
    Takes a list of words and returns a copy with all stop 
    words removed 
    """
    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    # add single-letter words
    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    """
    Takes a list of words and returns a dictionary associating
    words with frequencies of occurrence
    """
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    """
    Takes a dictionary of words and their frequencies
    and returns a list of pairs where the entries are
    sorted by frequency 
    """
    return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)

def print_all(word_freqs):
    """
    Takes a list of pairs where the entries are sorted by frequency and print them recursively.
    """
    if(len(word_freqs) > 0):
        print word_freqs[0][0], ' - ', word_freqs[0][1]
        print_all(word_freqs[1:]);

#
# The main function
#
print_all(sort(frequencies(remove_stop_words(scan(filter_chars_and_normalize(read_file(sys.argv[1]))))))[0:25])


########NEW FILE########
__FILENAME__ = tf-06-1
#!/usr/bin/env python
import re, string, sys

stops = set(open("../stop_words.txt").read().split(",") + list(string.ascii_lowercase))
words = [x.lower() for x in re.split("[^a-zA-Z]+", open(sys.argv[1]).read()) if len(x) > 0 and x.lower() not in stops]
unique_words = list(set(words))
unique_words.sort(lambda x, y: cmp(words.count(y), words.count(x)))
print "\n".join(["%s - %s" % (x, words.count(x)) for x in unique_words[:25]])

########NEW FILE########
__FILENAME__ = tf-06-pn
#!/usr/bin/env python
# My golf score is slightly lower!  
# Best wishes, Peter Norvig

import re, sys, collections

stopwords = set(open('../stop_words.txt').read().split(','))
words = re.findall('[a-z]{2,}', open(sys.argv[1]).read().lower())
counts = collections.Counter(w for w in words if w not in stopwords)
for (w, c) in counts.most_common(25):
    print w, '-', c

########NEW FILE########
__FILENAME__ = tf-06
#!/usr/bin/env python
import heapq, re, sys

words = re.findall("[a-z]{2,}", open(sys.argv[1]).read().lower())
for w in heapq.nlargest(25, set(words) - set(open("../stop_words.txt").read().split(",")), words.count):
    print w, "-", words.count(w)

########NEW FILE########
__FILENAME__ = tf-07
#!/usr/bin/env python
import re, sys, operator

# Mileage may vary. If this crashes, make it lower
RECURSION_LIMIT = 9500
# We add a few more, because, contrary to the name,
# this doesn't just rule recursion: it rules the 
# depth of the call stack
sys.setrecursionlimit(RECURSION_LIMIT+10)

def count(word_list, stopwords, wordfreqs):
    # What to do with an empty list
    if word_list == []:
        return
    # The inductive case, what to do with a list of words
    else:
        # Process the head word
        word = word_list[0]
        if word not in stopwords:
            if word in word_freqs:
                wordfreqs[word] += 1
            else:
                wordfreqs[word] = 1
        # Process the tail 
        count(word_list[1:], stopwords, wordfreqs)

def wf_print(wordfreq):
    if wordfreq == []:
        return
    else:
        (w, c) = wordfreq[0]
        print w, '-', c
        wf_print(wordfreq[1:])

stop_words = set(open('../stop_words.txt').read().split(','))
words = re.findall('[a-z]{2,}', open(sys.argv[1]).read().lower())
word_freqs = {}
# Theoretically, we would just call count(words, word_freqs)
# Try doing that and see what happens.
for i in range(0, len(words), RECURSION_LIMIT):
    count(words[i:i+RECURSION_LIMIT], stop_words, word_freqs)

wf_print(sorted(word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)[:25])


########NEW FILE########
__FILENAME__ = tf-08
#!/usr/bin/env python
import sys, re, operator, string

#
# The functions
#
def read_file(path_to_file, func):
    with  open(path_to_file) as f:
        data = f.read()
    func(data, normalize)

def filter_chars(str_data, func):
    pattern = re.compile('[\W_]+')
    func(pattern.sub(' ', str_data), scan)

def normalize(str_data, func):
    func(str_data.lower(), remove_stop_words)

def scan(str_data, func):
    func(str_data.split(), frequencies)

def remove_stop_words(word_list, func):
    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    # add single-letter words
    stop_words.extend(list(string.ascii_lowercase))
    func([w for w in word_list if not w in stop_words], sort)

def frequencies(word_list, func):
    wf = {}
    for w in word_list:
        if w in wf:
            wf[w] += 1
        else:
            wf[w] = 1
    func(wf, print_text)

def sort(wf, func):
    func(sorted(wf.iteritems(), key=operator.itemgetter(1), reverse=True), no_op)

def print_text(word_freqs, func):
    for (w, c) in word_freqs[0:25]:
        print w, "-", c
    func(None)

def no_op(func):
    return

#
# The main function
#
read_file(sys.argv[1], filter_chars)

########NEW FILE########
__FILENAME__ = tf-09
#!/usr/bin/env python
import sys, re, operator, string

#
# The One class for this example
#
class TFTheOne:
    def __init__(self, v):
        self._value = v

    def bind(self, func):
        self._value = func(self._value)
        return self

    def printme(self):
        print self._value

#
# The functions
#
def read_file(path_to_file):
    with open(path_to_file) as f:
        data = f.read()
    return data

def filter_chars(str_data):
    pattern = re.compile('[\W_]+')
    return pattern.sub(' ', str_data)

def normalize(str_data):
    return str_data.lower()

def scan(str_data):
    return str_data.split()

def remove_stop_words(word_list):
    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    # add single-letter words
    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)

def top25_freqs(word_freqs):
    top25 = ""
    for tf in word_freqs[0:25]:
        top25 += str(tf[0]) + ' - ' + str(tf[1]) + '\n'
    return top25

#
# The main function
#
TFTheOne(sys.argv[1])\
.bind(read_file)\
.bind(filter_chars)\
.bind(normalize)\
.bind(scan)\
.bind(remove_stop_words)\
.bind(frequencies)\
.bind(sort)\
.bind(top25_freqs)\
.printme()


########NEW FILE########
__FILENAME__ = tf-10
#!/usr/bin/env python
import sys, re, operator, string
from abc import ABCMeta

#
# The classes
#
class TFExercise():
    __metaclass__ = ABCMeta

    def info(self):
        return self.__class__.__name__

class DataStorageManager(TFExercise):
    """ Models the contents of the file """
    
    def __init__(self, path_to_file):
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def words(self):
        """ Returns the list words in storage """
        return self._data.split()

    def info(self):
        return super(DataStorageManager, self).info() + ": My major data structure is a " + self._data.__class__.__name__

class StopWordManager(TFExercise):
    """ Models the stop word filter """
    
    def __init__(self):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        # add single-letter words
        self._stop_words.extend(list(string.ascii_lowercase))

    def is_stop_word(self, word):
        return word in self._stop_words

    def info(self):
        return super(StopWordManager, self).info() + ": My major data structure is a " + self._stop_words.__class__.__name__

class WordFrequencyManager(TFExercise):
    """ Keeps the word frequency data """
    
    def __init__(self):
        self._word_freqs = {}

    def increment_count(self, word):
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def sorted(self):
        return sorted(self._word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)

    def info(self):
        return super(WordFrequencyManager, self).info() + ": My major data structure is a " + self._word_freqs.__class__.__name__

class WordFrequencyController(TFExercise):
    def __init__(self, path_to_file):
        self._storage_manager = DataStorageManager(path_to_file)
        self._stop_word_manager = StopWordManager()
        self._word_freq_manager = WordFrequencyManager()

    def run(self):
        for w in self._storage_manager.words():
            if not self._stop_word_manager.is_stop_word(w):
                self._word_freq_manager.increment_count(w)

        word_freqs = self._word_freq_manager.sorted()
        for (w, c) in word_freqs[0:25]:
            print w, ' - ', c

#
# The main function
#
WordFrequencyController(sys.argv[1]).run()

########NEW FILE########
__FILENAME__ = tf-11
#!/usr/bin/env python
import sys, re, operator, string

class DataStorageManager():
    """ Models the contents of the file """
    _data = ''

    def dispatch(self, message):
        if message[0] == 'init':
            return self._init(message[1])
        elif message[0] == 'words':
            return self._words()
        else:
            raise Exception("Message not understood " + message[0])
 
    def _init(self, path_to_file):
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def _words(self):
        """ Returns the list words in storage"""
        data_str = ''.join(self._data)
        return data_str.split()

class StopWordManager():
    """ Models the stop word filter """
    _stop_words = []

    def dispatch(self, message):
        if message[0] == 'init':
            return self._init()
        elif message[0] == 'is_stop_word':
            return self._is_stop_word(message[1])
        else:
            raise Exception("Message not understood " + message[0])
 
    def _init(self):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))

    def _is_stop_word(self, word):
        return word in self._stop_words

class WordFrequencyManager():
    """ Keeps the word frequency data """
    _word_freqs = {}

    def dispatch(self, message):
        if message[0] == 'increment_count':
            return self._increment_count(message[1])
        elif message[0] == 'sorted':
            return self._sorted()
        else:
            raise Exception("Message not understood " + message[0])
 
    def _increment_count(self, word):
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def _sorted(self):
        return sorted(self._word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)

class WordFrequencyController():

    def dispatch(self, message):
        if message[0] == 'init':
            return self._init(message[1])
        elif message[0] == 'run':
            return self._run()
        else:
            raise Exception("Message not understood " + message[0])
 
    def _init(self, path_to_file):
        self._storage_manager = DataStorageManager()
        self._stop_word_manager = StopWordManager()
        self._word_freq_manager = WordFrequencyManager()
        self._storage_manager.dispatch(['init', path_to_file])
        self._stop_word_manager.dispatch(['init'])

    def _run(self):
        for w in self._storage_manager.dispatch(['words']):
            if not self._stop_word_manager.dispatch(['is_stop_word', w]):
                self._word_freq_manager.dispatch(['increment_count', w])

        word_freqs = self._word_freq_manager.dispatch(['sorted'])
        for (w, c) in word_freqs[0:25]:
            print w, ' - ', c

#
# The main function
#
wfcontroller = WordFrequencyController()
wfcontroller.dispatch(['init', sys.argv[1]])
wfcontroller.dispatch(['run'])


########NEW FILE########
__FILENAME__ = tf-12
#!/usr/bin/env python
import sys, re, operator, string

# Auxiliary functions that can't be lambdas
#
def extract_words(obj, path_to_file):
    with open(path_to_file) as f:
        obj['data'] = f.read()
    pattern = re.compile('[\W_]+')
    data_str = ''.join(pattern.sub(' ', obj['data']).lower())
    obj['data'] = data_str.split()

def load_stop_words(obj):
    with open('../stop_words.txt') as f:
        obj['stop_words'] = f.read().split(',')
    # add single-letter words
    obj['stop_words'].extend(list(string.ascii_lowercase))

def increment_count(obj, w):
    obj['freqs'][w] = 1 if w not in obj['freqs'] else obj['freqs'][w]+1

data_storage_obj = {
    'data' : [],
    'init' : lambda path_to_file : extract_words(data_storage_obj, path_to_file),
    'words' : lambda : data_storage_obj['data']
}

stop_words_obj = {
    'stop_words' : [],
    'init' : lambda : load_stop_words(stop_words_obj),
    'is_stop_word' : lambda word : word in stop_words_obj['stop_words']
}

word_freqs_obj = {
    'freqs' : {},
    'increment_count' : lambda w : increment_count(word_freqs_obj, w),
    'sorted' : lambda : sorted(word_freqs_obj['freqs'].iteritems(), key=operator.itemgetter(1), reverse=True)
}

data_storage_obj['init'](sys.argv[1])
stop_words_obj['init']()

for w in data_storage_obj['words']():
    if not stop_words_obj['is_stop_word'](w):
        word_freqs_obj['increment_count'](w)

word_freqs = word_freqs_obj['sorted']()
for (w, c) in word_freqs[0:25]:
    print w, ' - ', c

########NEW FILE########
__FILENAME__ = tf-13
#!/usr/bin/env python
import abc, sys, re, operator, string

#
# The abstract things
#
class IDataStorage (object):
    """ Models the contents of the file """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def words(self):
        """ Returns the words in storage """
        pass

class IStopWordFilter (object):
    """ Models the stop word filter """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def is_stop_word(self, word):
        """ Checks whether the given word is a stop word """
        pass

class IWordFrequencyCounter(object):
    """ Keeps the word frequency data """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def increment_count(self, word):
        """ Increments the count for the given word """
        pass

    @abc.abstractmethod
    def sorted(self):
        """ Returns the words and their frequencies, sorted by frequency""" 
        pass

#
# The concrete things
#
class DataStorageManager:
    _data = ''
    def __init__(self, path_to_file):
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()
        self._data = ''.join(self._data).split()

    def words(self):
        return self._data

class StopWordManager:
    _stop_words = []
    def __init__(self):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))

    def is_stop_word(self, word):
        return word in self._stop_words

class WordFrequencyManager:
    _word_freqs = {}

    def increment_count(self, word):
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def sorted(self):
        return sorted(self._word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)


#
# The wiring between abstract things and concrete things
#
IDataStorage.register(DataStorageManager)
IStopWordFilter.register(StopWordManager)
IWordFrequencyCounter.register(WordFrequencyManager)

#
# The application object
#
class WordFrequencyController:
    def __init__(self, path_to_file):
        self._storage = DataStorageManager(path_to_file)
        self._stop_word_manager = StopWordManager()
        self._word_freq_counter = WordFrequencyManager()

    def run(self):
        for w in self._storage.words():
            if not self._stop_word_manager.is_stop_word(w):
                self._word_freq_counter.increment_count(w)

        word_freqs = self._word_freq_counter.sorted()
        for (w, c) in word_freqs[0:25]:
            print w, ' - ', c

#
# The main function
#
WordFrequencyController(sys.argv[1]).run()

########NEW FILE########
__FILENAME__ = tf-14
#!/usr/bin/env python
import sys, re, operator, string

#
# The "I'll call you back" Word Frequency Framework
#
class WordFrequencyFramework:
    _load_event_handlers = []
    _dowork_event_handlers = []
    _end_event_handlers = []

    def register_for_load_event(self, handler):
        self._load_event_handlers.append(handler)

    def register_for_dowork_event(self, handler):
        self._dowork_event_handlers.append(handler)

    def register_for_end_event(self, handler):
        self._end_event_handlers.append(handler)
    
    def run(self, path_to_file):
        for h in self._load_event_handlers:
            h(path_to_file)
        for h in self._dowork_event_handlers:
            h()
        for h in self._end_event_handlers:
            h()

#
# The entities of the application
#
class DataStorage:
    """ Models the contents of the file """
    _data = ''
    _stop_word_filter = None
    _word_event_handlers = []

    def __init__(self, wfapp, stop_word_filter):
        self._stop_word_filter = stop_word_filter
        wfapp.register_for_load_event(self.__load)
        wfapp.register_for_dowork_event(self.__produce_words)

    def __load(self, path_to_file):
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def __produce_words(self):
        """ Iterates through the list words in storage 
            calling back handlers for words """
        data_str = ''.join(self._data)
        for w in data_str.split():
            if not self._stop_word_filter.is_stop_word(w):
                for h in self._word_event_handlers:
                    h(w)

    def register_for_word_event(self, handler):
        self._word_event_handlers.append(handler)

class StopWordFilter:
    """ Models the stop word filter """
    _stop_words = []
    def __init__(self, wfapp):
        wfapp.register_for_load_event(self.__load)

    def __load(self, ignore):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        # add single-letter words
        self._stop_words.extend(list(string.ascii_lowercase))

    def is_stop_word(self, word):
        return word in self._stop_words

class WordFrequencyCounter:
    """ Keeps the word frequency data """
    _word_freqs = {}
    def __init__(self, wfapp, data_storage):
        data_storage.register_for_word_event(self.__increment_count)
        wfapp.register_for_end_event(self.__print_freqs)

    def __increment_count(self, word):
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def __print_freqs(self):
        word_freqs = sorted(self._word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
        for (w, c) in word_freqs[0:25]:
            print w, ' - ', c

#
# The main function
#
wfapp = WordFrequencyFramework()
stop_word_filter = StopWordFilter(wfapp)
data_storage = DataStorage(wfapp, stop_word_filter)
word_freq_counter = WordFrequencyCounter(wfapp, data_storage)
wfapp.run(sys.argv[1])


########NEW FILE########
__FILENAME__ = tf-15
#!/usr/bin/env python
import sys, re, operator, string

#
# The event management substrate
#
class EventManager:
    def __init__(self):
        self._subscriptions = {}

    def subscribe(self, event_type, handler):
        if event_type in self._subscriptions:
            self._subscriptions[event_type].append(handler)
        else:
            self._subscriptions[event_type] = [handler]

    def publish(self, event):
        event_type = event[0]
        if event_type in self._subscriptions:
            for h in self._subscriptions[event_type]:
                h(event)

#
# The application entities
#
class DataStorage:
    """ Models the contents of the file """
    def __init__(self, event_manager):
        self._event_manager = event_manager
        self._event_manager.subscribe('load', self.load)
        self._event_manager.subscribe('start', self.produce_words)

    def load(self, event):
        path_to_file = event[1]
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def produce_words(self, event):
        data_str = ''.join(self._data)
        for w in data_str.split():
            self._event_manager.publish(('word', w))
        self._event_manager.publish(('eof', None))

class StopWordFilter:
    """ Models the stop word filter """
    def __init__(self, event_manager):
        self._stop_words = []
        self._event_manager = event_manager
        self._event_manager.subscribe('load', self.load)
        self._event_manager.subscribe('word', self.is_stop_word)

    def load(self, event):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))

    def is_stop_word(self, event):
        word = event[1]
        if word not in self._stop_words:
            self._event_manager.publish(('valid_word', word))

class WordFrequencyCounter:
    """ Keeps the word frequency data """
    def __init__(self, event_manager):
        self._word_freqs = {}
        self._event_manager = event_manager
        self._event_manager.subscribe('valid_word', self.increment_count)
        self._event_manager.subscribe('print', self.print_freqs)

    def increment_count(self, event):
        word = event[1]
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def print_freqs(self, event):
        word_freqs = sorted(self._word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
        for (w, c) in word_freqs[0:25]:
            print w, ' - ', c

class WordFrequencyApplication:
    def __init__(self, event_manager):
        self._event_manager = event_manager
        self._event_manager.subscribe('run', self.run)
        self._event_manager.subscribe('eof', self.stop)

    def run(self, event):
        path_to_file = event[1]
        self._event_manager.publish(('load', path_to_file))
        self._event_manager.publish(('start', None))

    def stop(self, event):
        self._event_manager.publish(('print', None))

#
# The main function
#
em = EventManager()
DataStorage(em), StopWordFilter(em), WordFrequencyCounter(em)
WordFrequencyApplication(em)
em.publish(('run', sys.argv[1]))

########NEW FILE########
__FILENAME__ = tf-16
#!/usr/bin/env python
import sys, re, operator, string, inspect

def read_stop_words():
    """ This function can only be called from a function 
        named extract_words."""
    # Meta-level data: inspect.stack()
    if inspect.stack()[1][3] != 'extract_words':
        return None

    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    stop_words.extend(list(string.ascii_lowercase))
    return stop_words

def extract_words(path_to_file):
    # Meta-level data: locals()
    with open(locals()['path_to_file']) as f:
        str_data = f.read()
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', str_data).lower().split()
    stop_words = read_stop_words()
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    # Meta-level data: locals()
    word_freqs = {}
    for w in locals()['word_list']:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    # Meta-level data: locals()
    return sorted(locals()['word_freq'].iteritems(), key=operator.itemgetter(1), reverse=True)

def main():
    word_freqs = sort(frequencies(extract_words(sys.argv[1])))
    for (w, c) in word_freqs[0:25]:
        print w, ' - ', c

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = tf-17
#!/usr/bin/env python
import sys, re, operator, string, os

#
# Two down-to-earth things
#
stops = set(open("../stop_words.txt").read().split(",") + list(string.ascii_lowercase))

def frequencies_imp(word_list):
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

#
# Let's write our functions as strings.
#
if len(sys.argv) > 1:
    extract_words_func = "lambda name : [x.lower() for x in re.split('[^a-zA-Z]+', open(name).read()) if len(x) > 0 and x.lower() not in stops]"
    frequencies_func = "lambda wl : frequencies_imp(wl)"
    sort_func = "lambda word_freq: sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)"
    filename = sys.argv[1]
else:
    extract_words_func = "lambda x: []"
    frequencies_func = "lambda x: []"
    sort_func = "lambda x: []"
    filename = os.path.basename(__file__)
#
# So far, this program isn't much about term-frequency. It's about
# a bunch of strings that look like functions.
# Let's add our functions to the "base" program, dynamically.
#
exec('extract_words = ' + extract_words_func)
exec('frequencies = ' + frequencies_func)
exec('sort = ' + sort_func)

#
# The main function. This would work just fine:
#  word_freqs = sort(frequencies(extract_words(filename)))
#
word_freqs = locals()['sort'](locals()['frequencies'](locals()['extract_words'](filename)))

for (w, c) in word_freqs[0:25]:
    print w, ' - ', c


########NEW FILE########
__FILENAME__ = tf-18
#!/usr/bin/env python
import sys, re, operator, string, time

#
# The functions
#
def extract_words(path_to_file):
    with open(path_to_file) as f:
        str_data = f.read()
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', str_data).lower().split()
    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)

# The side functionality
def profile(f):
    def profilewrapper(*arg, **kw):
        start_time = time.time()
        ret_value = f(*arg, **kw)
        elapsed = time.time() - start_time
        print "%s(...) took %s secs" % (f.__name__, elapsed)
        return ret_value
    return profilewrapper

# join points
tracked_functions = [extract_words, frequencies, sort]
# weaver
for func in tracked_functions:
    globals()[func.func_name]=profile(func)

word_freqs = sort(frequencies(extract_words(sys.argv[1])))

for (w, c) in word_freqs[0:25]:
    print w, ' - ', c


########NEW FILE########
__FILENAME__ = frequencies1
import operator

def top25(word_list):
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return sorted(word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)[:25]


########NEW FILE########
__FILENAME__ = frequencies2
import operator, collections

def top25(word_list):
    counts = collections.Counter(w for w in word_list)
    return counts.most_common(25)


########NEW FILE########
__FILENAME__ = words1
import sys, re, string

def extract_words(path_to_file):
    with open(path_to_file) as f:
        str_data = f.read()
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', str_data).lower().split()

    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    stop_words.extend(list(string.ascii_lowercase))

    return [w for w in word_list if not w in stop_words]


########NEW FILE########
__FILENAME__ = words2
import sys, re, string

def extract_words(path_to_file):
    words = re.findall('[a-z]{2,}', open(path_to_file).read().lower())
    stopwords = set(open('../stop_words.txt').read().split(','))
    return [w for w in words if w not in stopwords]


########NEW FILE########
__FILENAME__ = tf-19
#!/usr/bin/env python
import sys, ConfigParser, imp

def load_plugins():
    config = ConfigParser.ConfigParser()
    config.read("config.ini")
    words_plugin = config.get("Plugins", "words")
    frequencies_plugin = config.get("Plugins", "frequencies")
    global tfwords, tffreqs
    tfwords = imp.load_compiled('tfwords', words_plugin)
    tffreqs = imp.load_compiled('tffreqs', frequencies_plugin)

load_plugins()
word_freqs = tffreqs.top25(tfwords.extract_words(sys.argv[1]))

for (w, c) in word_freqs:
    print w, ' - ', c


########NEW FILE########
__FILENAME__ = tf-20
#!/usr/bin/env python
import sys, re, operator, string, inspect

#
# The functions
#
def extract_words(path_to_file):
    if type(path_to_file) is not str or not path_to_file:
        return []

    try:
        with open(path_to_file) as f:
            str_data = f.read()
    except IOError as e:
        print "I/O error({0}) when opening {1}: {2}".format(e.errno, path_to_file, e.strerror)
        return []
    
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', str_data).lower().split()
    return word_list

def remove_stop_words(word_list):
    if type(word_list) is not list:
        return [] 

    try:
        with open('../stop_words.txt') as f:
            stop_words = f.read().split(',')
    except IOError as e:
        print "I/O error({0}) when opening ../stops_words.txt: {1}".format(e.errno, e.strerror)
        return word_list

    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    if type(word_list) is not list or word_list == []:
        return {}

    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    if type(word_freq) is not dict or word_freq == {}:
        return []

    return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)

#
# The main function
#
filename = sys.argv[1] if len(sys.argv) > 1 else "../input.txt"
word_freqs = sort(frequencies(remove_stop_words(extract_words(filename))))

for tf in word_freqs[0:25]:
    print tf[0], ' - ', tf[1]


########NEW FILE########
__FILENAME__ = tf-21
#!/usr/bin/env python

import sys, re, operator, string, traceback

#
# The functions
#
def extract_words(path_to_file):
    assert(type(path_to_file) is str), "I need a string!" 
    assert(path_to_file), "I need a non-empty string!" 

    try:
        with open(path_to_file) as f:
            str_data = f.read()
    except IOError as e:
        print "I/O error({0}) when opening {1}: {2}! I quit!".format(e.errno, path_to_file, e.strerror)
        raise e
    
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', str_data).lower().split()
    return word_list

def remove_stop_words(word_list):
    assert(type(word_list) is list), "I need a list!"

    try:
        with open('../stop_words.txt') as f:
            stop_words = f.read().split(',')
    except IOError as e:
        print "I/O error({0}) when opening ../stops_words.txt: {1}! I quit!".format(e.errno, e.strerror)
        raise e

    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    assert(type(word_list) is list), "I need a list!"
    assert(word_list <> []), "I need a non-empty list!"

    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    assert(type(word_freq) is dict), "I need a dictionary!"
    assert(word_freq <> {}), "I need a non-empty dictionary!"

    try:
        return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)
    except Exception as e:
        print "Sorted threw {0}: {1}".format(e)
        raise e

#
# The main function
#
try:
    assert(len(sys.argv) > 1), "You idiot! I need an input file!"
    word_freqs = sort(frequencies(remove_stop_words(extract_words(sys.argv[1]))))

    assert(type(word_freqs) is list), "OMG! This is not a list!"
    assert(len(word_freqs) > 25), "SRSLY? Less than 25 words!"
    for (w, c) in word_freqs[0:25]:
        print w, ' - ', c
except Exception as e:
    print "Something wrong: {0}".format(e)
    traceback.print_exc()
    

########NEW FILE########
__FILENAME__ = tf-22
#!/usr/bin/env python
import sys, re, operator, string

#
# The functions
#
def extract_words(path_to_file):
    assert(type(path_to_file) is str), "I need a string! I quit!" 
    assert(path_to_file), "I need a non-empty string! I quit!" 

    with open(path_to_file) as f:
        data = f.read()
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', data).lower().split()
    return word_list

def remove_stop_words(word_list):
    assert(type(word_list) is list), "I need a list! I quit!"

    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    # add single-letter words
    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    assert(type(word_list) is list), "I need a list! I quit!"
    assert(word_list <> []), "I need a non-empty list! I quit!"

    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freqs):
    assert(type(word_freqs) is dict), "I need a dictionary! I quit!"
    assert(word_freqs <> {}), "I need a non-empty dictionary! I quit!"

    return sorted(word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)

#
# The main function
#
try:
    assert(len(sys.argv) > 1), "You idiot! I need an input file! I quit!"
    word_freqs = sort(frequencies(remove_stop_words(extract_words(sys.argv[1]))))

    assert(len(word_freqs) > 25), "OMG! Less than 25 words! I QUIT!"
    for tf in word_freqs[0:25]:
        print tf[0], ' - ', tf[1]
except Exception as e:
        print "Something wrong: {0}".format(e)



########NEW FILE########
__FILENAME__ = tf-23-monadic
#!/usr/bin/env python
import sys, re, operator, string

#
# The PassiveAggressive class for this example
#
class TFPassiveAggressive:
    def __init__(self):
        self._e = None
        self._offending_func = None
        self._value = None

    def bind(self, func):
        if self._e == None:
            try:
                self._value = func(self._value)
            except Exception as e:
                self._e = e
                self._offending_func = func
        return self

    def printme(self):
        if self._e == None:
            print self._value
        else:
            print self._e, " in ", self._offending_func.__name__

#
# The functions
#
def get_input(ignore):
    assert(len(sys.argv) > 1), "You idiot! I need an input file! I quit!"
    return sys.argv[1]

def extract_words(path_to_file):
    assert(type(path_to_file) is str), "I need a string! I quit!" 
    assert(path_to_file), "I need a non-empty string! I quit!" 

    with open(path_to_file) as f:
        data = f.read()
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', data).lower().split()
    return word_list

def remove_stop_words(word_list):
    assert(type(word_list) is list), "I need a list! I quit!"

    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    # add single-letter words
    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

def frequencies(word_list):
    assert(type(word_list) is list), "I need a list! I quit!"
    assert(word_list <> []), "I need a non-empty list! I quit!"

    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freqs):
    assert(type(word_freqs) is dict), "I need a dictionary! I quit!"
    assert(word_freqs <> {}), "I need a non-empty dictionary! I quit!"

    return sorted(word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)

def top25_freqs(word_freqs):
    assert(type(word_freqs) is list), "I need a list! I quit!"
    assert(word_freqs <> {}), "I need a non-empty dictionary! I quit!"

    top25 = ""
    for tf in word_freqs[0:25]:
        top25 += str(tf[0]) + ' - ' + str(tf[1]) + '\n'
    return top25

#
# The main function
#
TFPassiveAggressive().bind(get_input).bind(extract_words).bind(remove_stop_words).bind(frequencies).bind(sort).bind(top25_freqs).printme()
########NEW FILE########
__FILENAME__ = tf-23
#!/usr/bin/env python
import sys, re, operator, string, inspect

#
# Decorator for enforcing types of arguments in method calls
#
class AcceptTypes():
    def __init__(self, *args):
        self._args = args

    def __call__(self, f):
        def wrapped_f(*args):
            for i in range(len(self._args)):
                if type(args[i]) <> self._args[i]:
                    raise TypeError("Expecting %s got %s" % (str(self._args[i]), str(type(args[i]))))
            return f(*args)
        return wrapped_f
#
# The functions
#
@AcceptTypes(str)
def extract_words(path_to_file):
    with open(path_to_file) as f:
        str_data = f.read()    
    pattern = re.compile('[\W_]+')
    word_list = pattern.sub(' ', str_data).lower().split()
    with open('../stop_words.txt') as f:
        stop_words = f.read().split(',')
    stop_words.extend(list(string.ascii_lowercase))
    return [w for w in word_list if not w in stop_words]

@AcceptTypes(list)
def frequencies(word_list):
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

@AcceptTypes(dict)
def sort(word_freq):
    return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)

word_freqs = sort(frequencies(extract_words(sys.argv[1])))
for (w, c) in word_freqs[0:25]:
    print w, ' - ', c


########NEW FILE########
__FILENAME__ = tf-24
#!/usr/bin/env python
import sys, re, operator, string

#
# The Quarantine class for this example
#
class TFQuarantine:
    def __init__(self, func):
        self._funcs = [func]

    def bind(self, func):
        self._funcs.append(func)
        return self

    def execute(self):
        def guard_callable(v):
            return v() if hasattr(v, '__call__') else v

        value = lambda : None
        for func in self._funcs:
            value = func(guard_callable(value))
        print guard_callable(value)

#
# The functions
#
def get_input(arg):
    def _f():
        return sys.argv[1]
    return _f

def extract_words(path_to_file):
    def _f():
        with open(path_to_file) as f:
            data = f.read()
        pattern = re.compile('[\W_]+')
        word_list = pattern.sub(' ', data).lower().split()
        return word_list
    return _f

def remove_stop_words(word_list):
    def _f():
        with open('../stop_words.txt') as f:
            stop_words = f.read().split(',')
        # add single-letter words
        stop_words.extend(list(string.ascii_lowercase))
        return [w for w in word_list if not w in stop_words]
    return _f

def frequencies(word_list):
    word_freqs = {}
    for w in word_list:
        if w in word_freqs:
            word_freqs[w] += 1
        else:
            word_freqs[w] = 1
    return word_freqs

def sort(word_freq):
    return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)

def top25_freqs(word_freqs):
    top25 = ""
    for tf in word_freqs[0:25]:
        top25 += str(tf[0]) + ' - ' + str(tf[1]) + '\n'
    return top25

#
# The main function
#
TFQuarantine(get_input)\
.bind(extract_words)\
.bind(remove_stop_words)\
.bind(frequencies)\
.bind(sort)\
.bind(top25_freqs)\
.execute()


########NEW FILE########
__FILENAME__ = tf-25
#!/usr/bin/env python
import sys, re, string, sqlite3, os.path

#
# The relational database of this problem consists of 3 tables:
# documents, words, characters
#
def create_db_schema(connection):
    c = connection.cursor()
    c.execute('''CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT, name)''')
    c.execute('''CREATE TABLE words (id, doc_id, value)''')
    c.execute('''CREATE TABLE characters (id, word_id, value)''')
    connection.commit()
    c.close()

def load_file_into_database(path_to_file, connection):
    """ Takes the path to a file and loads the contents into the database """
    def _extract_words(path_to_file):
        with open(path_to_file) as f:
            str_data = f.read()    
        pattern = re.compile('[\W_]+')
        word_list = pattern.sub(' ', str_data).lower().split()
        with open('../stop_words.txt') as f:
            stop_words = f.read().split(',')
        stop_words.extend(list(string.ascii_lowercase))
        return [w for w in word_list if not w in stop_words]

    words = _extract_words(path_to_file)

    # Now let's add data to the database
    # Add the document itself to the database
    c = connection.cursor()
    c.execute("INSERT INTO documents (name) VALUES (?)", (path_to_file,))
    c.execute("SELECT id from documents WHERE name=?", (path_to_file,))
    doc_id = c.fetchone()[0]

    # Add the words to the database
    c.execute("SELECT MAX(id) FROM words")
    row = c.fetchone()
    word_id = row[0]
    if word_id == None:
        word_id = 0
    for w in words:
        c.execute("INSERT INTO words VALUES (?, ?, ?)", (word_id, doc_id, w))
        # Add the characters to the database
        char_id = 0
        for char in w:
            c.execute("INSERT INTO characters VALUES (?, ?, ?)", (char_id, word_id, char))
            char_id += 1
        word_id += 1
    connection.commit()
    c.close()

#
# Create if it doesn't exist
#
if not os.path.isfile('tf.db'):
    with sqlite3.connect('tf.db') as connection:
        create_db_schema(connection)
        load_file_into_database(sys.argv[1], connection)

# Now, let's query
with sqlite3.connect('tf.db') as connection:
    c = connection.cursor()
    c.execute("SELECT value, COUNT(*) as C FROM words GROUP BY value ORDER BY C DESC")
    for i in range(25):
        row = c.fetchone()
        if row != None:
            print row[0] + ' - '  + str(row[1])

########NEW FILE########
__FILENAME__ = tf-26
#!/usr/bin/env python
import sys, re, itertools, operator

#
# The columns. Each column is a data element and a formula.
# The first 2 columns are the input data, so no formulas.
#
all_words = [(), None]
stop_words = [(), None]
non_stop_words = [(), lambda : \
                          map(lambda w : \
                            w if w not in stop_words[0] else '',\
                              all_words[0])]
unique_words = [(),lambda : 
                    set([w for w in non_stop_words[0] if w!=''])]
counts = [(), lambda : 
                map(lambda w, word_list : word_list.count(w), \
                    unique_words[0], \
                    itertools.repeat(non_stop_words[0], \
                                   len(unique_words[0])))]
sorted_data = [(), lambda : sorted(zip(list(unique_words[0]), \
                                       counts[0]), \
                                   key=operator.itemgetter(1), 
                                   reverse=True)]

# The entire spreadsheet
all_columns = [all_words, stop_words, non_stop_words,\
               unique_words, counts, sorted_data]

#
# The active procedure over the columns of data.
# Call this everytime the input data changes, or periodically.
#
def update():
    global all_columns
    # Apply the formula in each column
    for c in all_columns:
        if c[1] != None:
            c[0] = c[1]() 


# Load the fixed data into the first 2 columns
all_words[0] = re.findall('[a-z]{2,}', open(sys.argv[1]).read().lower())
stop_words[0] = set(open('../stop_words.txt').read().split(','))
# Update the columns with formulas
update()

for (w, c) in sorted_data[0][:25]:
    print w, '-', c

########NEW FILE########
__FILENAME__ = tf-27
#!/usr/bin/env python
import sys, operator, string

def characters(filename):
    for line in open(filename):
        for c in line:
            yield c

def all_words(filename):
    start_char = True
    for c in characters(filename):
        if start_char == True:
            word = ""
            if c.isalnum():
                # We found the start of a word
                word = c.lower()
                start_char = False
            else: pass
        else:
            if c.isalnum():
                word += c.lower()
            else:
                # We found end of word, emit it
                start_char = True
                yield word

def non_stop_words(filename):
    stopwords = set(open('../stop_words.txt').read().split(',')  + list(string.ascii_lowercase))
    for w in all_words(filename):
        if not w in stopwords:
            yield w

def count_and_sort(filename):
    freqs, i = {}, 1
    for w in non_stop_words(filename):
        freqs[w] = 1 if w not in freqs else freqs[w]+1
        if i % 5000 == 0:
            yield sorted(freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
        i = i+1
    yield sorted(freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
#
# The main function
#
for word_freqs in count_and_sort(sys.argv[1]):
    print "-----------------------------"
    for (w, c) in word_freqs[0:25]:
        print w, ' - ', c


########NEW FILE########
__FILENAME__ = tf-28
#!/usr/bin/env python

import sys, re, operator, string
from threading import Thread
from Queue import Queue

class ActiveWFObject(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.name = str(type(self))
        self.queue = Queue()
        self._stop = False
        self.start()

    def run(self):
        while not self._stop:
            message = self.queue.get()
            self._dispatch(message)
            if message[0] == 'die':
                self._stop = True

def send(receiver, message):
    receiver.queue.put(message)

class DataStorageManager(ActiveWFObject):
    """ Models the contents of the file """
    _data = ''

    def _dispatch(self, message):
        if message[0] == 'init':
            self._init(message[1:])
        elif message[0] == 'send_word_freqs':
            self._process_words(message[1:])
        else:
            # forward
            send(self._stop_word_manager, message)
 
    def _init(self, message):
        path_to_file = message[0]
        self._stop_word_manager = message[1]
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def _process_words(self, message):
        recipient = message[0]
        data_str = ''.join(self._data)
        words = data_str.split()
        for w in words:
            send(self._stop_word_manager, ['filter', w])
        send(self._stop_word_manager, ['top25', recipient])

class StopWordManager(ActiveWFObject):
    """ Models the stop word filter """
    _stop_words = []

    def _dispatch(self, message):
        if message[0] == 'init':
            self._init(message[1:])
        elif message[0] == 'filter':
            return self._filter(message[1:])
        else:
            # forward
            send(self._word_freqs_manager, message)
 
    def _init(self, message):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))
        self._word_freqs_manager = message[0]

    def _filter(self, message):
        word = message[0]
        if word not in self._stop_words:
            send(self._word_freqs_manager, ['word', word])

class WordFrequencyManager(ActiveWFObject):
    """ Keeps the word frequency data """
    _word_freqs = {}

    def _dispatch(self, message):
        if message[0] == 'word':
            self._increment_count(message[1:])
        elif message[0] == 'top25':
            self._top25(message[1:])
 
    def _increment_count(self, message):
        word = message[0]
        if word in self._word_freqs:
            self._word_freqs[word] += 1 
        else: 
            self._word_freqs[word] = 1

    def _top25(self, message):
        recipient = message[0]
        freqs_sorted = sorted(self._word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
        send(recipient, ['top25', freqs_sorted])

class WordFrequencyController(ActiveWFObject):

    def _dispatch(self, message):
        if message[0] == 'run':
            self._run(message[1:])
        elif message[0] == 'top25':
            self._display(message[1:])
        else:
            raise Exception("Message not understood " + message[0])
 
    def _run(self, message):
        self._storage_manager = message[0]
        send(self._storage_manager, ['send_word_freqs', self])

    def _display(self, message):
        word_freqs = message[0]
        for (w, f) in word_freqs[0:25]:
            print w, ' - ', f
        send(self._storage_manager, ['die'])
        self._stop = True

#
# The main function
#
word_freq_manager = WordFrequencyManager()

stop_word_manager = StopWordManager()
send(stop_word_manager, ['init', word_freq_manager])

storage_manager = DataStorageManager()
send(storage_manager, ['init', sys.argv[1], stop_word_manager])

wfcontroller = WordFrequencyController()
send(wfcontroller, ['run', storage_manager])

# Wait for the active objects to finish
[t.join() for t in [word_freq_manager, stop_word_manager, storage_manager, wfcontroller]]

########NEW FILE########
__FILENAME__ = tf-29
#!/usr/bin/env python
import re, sys, operator, Queue, threading

# Two data spaces
word_space = Queue.Queue()
freq_space = Queue.Queue()

stopwords = set(open('../stop_words.txt').read().split(','))

# Worker function that consumes words from the word space
# and sends partial results to the frequency space
def process_words():
    word_freqs = {}
    while True:
        try:
            word = word_space.get(timeout=1)
        except Queue.Empty:
            break
        if not word in stopwords:
            if word in word_freqs:
                word_freqs[word] += 1
            else:
                word_freqs[word] = 1
    freq_space.put(word_freqs)

# Let's have this thread populate the word space
for word in re.findall('[a-z]{2,}', open(sys.argv[1]).read().lower()):
    word_space.put(word)

# Let's create the workers and launch them at their jobs
workers = []
for i in range(5):
    workers.append(threading.Thread(target = process_words))
[t.start() for t in workers]

# Let's wait for the workers to finish
[t.join() for t in workers]

# Let's merge the partial frequency results by consuming
# frequency data from the frequency space
word_freqs = {}
while not freq_space.empty():
    freqs = freq_space.get()
    for (k, v) in freqs.iteritems():
        if k in word_freqs:
            count = sum(item[k] for item in [freqs, word_freqs])
        else:
            count = freqs[k]
        word_freqs[k] = count
        
for (w, c) in sorted(word_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)[:25]:
    print w, '-', c

########NEW FILE########
__FILENAME__ = tf-30
#!/usr/bin/env python
import sys, re, operator, string

#
# Functions for map reduce
#
def partition(data_str, nlines):
    """ 
    Partitions the input data_str (a big string)
    into chunks of nlines.
    """
    lines = data_str.split('\n')
    for i in xrange(0, len(lines), nlines):
        yield '\n'.join(lines[i:i+nlines])

def split_words(data_str):
    """ 
    Takes a string,  returns a list of pairs (word, 1), 
    one for each word in the input, so
    [(w1, 1), (w2, 1), ..., (wn, 1)]
    """
    def _scan(str_data):
        pattern = re.compile('[\W_]+')
        return pattern.sub(' ', str_data).lower().split()

    def _remove_stop_words(word_list):
        with open('../stop_words.txt') as f:
            stop_words = f.read().split(',')
        stop_words.extend(list(string.ascii_lowercase))
        return [w for w in word_list if not w in stop_words]

    # The actual work of splitting the input into words
    result = []
    words = _remove_stop_words(_scan(data_str))
    for w in words:
        result.append((w, 1))
    return result

def count_words(pairs_list_1, pairs_list_2):
    """ 
    Takes two lists of pairs of the form
    [(w1, 1), ...]
    and returns a list of pairs [(w1, frequency), ...], 
    where frequency is the sum of all the reported occurrences
    """
    mapping = dict((k, v) for k, v in pairs_list_1)
    for p in pairs_list_2:
        if p[0] in mapping:
            mapping[p[0]] += p[1]
        else:
            mapping[p[0]] = 1
    return mapping.items()

#
# Auxiliary functions
#
def read_file(path_to_file):
    with open(path_to_file) as f:
        data = f.read()
    return data

def sort(word_freq):
    return sorted(word_freq, key=operator.itemgetter(1), reverse=True)

#
# The main function
#
splits = map(split_words, partition(read_file(sys.argv[1]), 200))
splits.insert(0, []) # Normalize input to reduce
word_freqs = sort(reduce(count_words, splits))

for (w, c) in word_freqs[0:25]:
    print w, ' - ', c


########NEW FILE########
__FILENAME__ = tf-31
#!/usr/bin/env python
import sys, re, operator, string

#
# Functions for map reduce
#
def partition(data_str, nlines):
    """ 
    Partitions the input data_str (a big string)
    into chunks of nlines.
    """
    lines = data_str.split('\n')
    for i in xrange(0, len(lines), nlines):
        yield '\n'.join(lines[i:i+nlines])

def split_words(data_str):
    """ 
    Takes a string, returns a list of pairs (word, 1), 
    one for each word in the input, so
    [(w1, 1), (w2, 1), ..., (wn, 1)]
    """
    def _scan(str_data):
        pattern = re.compile('[\W_]+')
        return pattern.sub(' ', str_data).lower().split()

    def _remove_stop_words(word_list):
        with open('../stop_words.txt') as f:
            stop_words = f.read().split(',')
        stop_words.extend(list(string.ascii_lowercase))
        return [w for w in word_list if not w in stop_words]

    # The actual work of the mapper
    result = []
    words = _remove_stop_words(_scan(data_str))
    for w in words:
        result.append((w, 1))
    return result

def regroup(pairs_list):
    """
    Takes a list of lists of pairs of the form 
    [[(w1, 1), (w2, 1), ..., (wn, 1)],
     [(w1, 1), (w2, 1), ..., (wn, 1)],
     ...]
    and returns a dictionary mapping each unique word to the 
    corresponding list of pairs, so
    { w1 : [(w1, 1), (w1, 1)...], 
      w2 : [(w2, 1), (w2, 1)...], 
      ...}
    """
    mapping = {}
    for pairs in pairs_list:
        for p in pairs:
            if p[0] in mapping:
                mapping[p[0]].append(p)
            else:
                mapping[p[0]] = [p]
    return mapping
    
def count_words(mapping):
    """ 
    Takes a mapping of the form (word, [(word, 1), (word, 1)...)])
    and returns a pair (word, frequency), where frequency is the 
    sum of all the reported occurrences
    """
    def add(x, y):
        return x+y

    return (mapping[0], reduce(add, (pair[1] for pair in mapping[1])))

#
# Auxiliary functions
#
def read_file(path_to_file):
    with open(path_to_file) as f:
        data = f.read()
    return data

def sort(word_freq):
    return sorted(word_freq, key=operator.itemgetter(1), reverse=True)

#
# The main function
#
splits = map(split_words, partition(read_file(sys.argv[1]), 200))
splits_per_word = regroup(splits)
word_freqs = sort(map(count_words, splits_per_word.items()))

for (w, c) in word_freqs[0:25]:
    print w, ' - ', c


########NEW FILE########
__FILENAME__ = tf-32-active
#!/usr/bin/env python
import sys, operator, string, os, threading, re
from util import getch, cls, get_input
from time import sleep

lock = threading.Lock()

#
# The active view
#
class FreqObserver(threading.Thread):
    def __init__(self, freqs):
        threading.Thread.__init__(self)
        self.daemon,self._end = True, False
        # freqs is the part of the model to be observed
        self._freqs = freqs
        self._freqs_0 = sorted(self._freqs.iteritems(), key=operator.itemgetter(1), reverse=True)[:25]
        self.start()

    def run(self):
        while not self._end:
            self._update_view()
            sleep(0.1)
        self._update_view()

    def stop(self):
        self._end = True

    def _update_view(self):
        lock.acquire()
        freqs_1 = sorted(self._freqs.iteritems(), key=operator.itemgetter(1), reverse=True)[:25]
        lock.release()
        if (freqs_1 != self._freqs_0):
            self._update_display(freqs_1)
            self._freqs_0 = freqs_1

    def _update_display(self, tuples):
        def refresh_screen(data):
            # clear screen
            cls()
            print data
            sys.stdout.flush()

        data_str = ""
        for (w, c) in tuples:
            data_str += str(w) + ' - ' + str(c) + '\n'
        refresh_screen(data_str)

#
# The model
#
class WordsCounter:
    freqs = {}
    def count(self):
        def non_stop_words():
            stopwords = set(open('../stop_words.txt').read().split(',')  + list(string.ascii_lowercase))
            for line in f:
                yield [w for w in re.findall('[a-z]{2,}', line.lower()) if w not in stopwords]

        words = non_stop_words().next()
        lock.acquire()
        for w in words:
            self.freqs[w] = 1 if w not in self.freqs else self.freqs[w]+1
        lock.release()

#
# The controller
#
print "Press space bar to fetch words from the file one by one"
print "Press ESC to switch to automatic mode"
model = WordsCounter()
view = FreqObserver(model.freqs)
with open(sys.argv[1]) as f:
    while get_input():
        try:
            model.count()
        except StopIteration:
            # Let's wait for the view thread to die gracefully
            view.stop()
            sleep(1)
            break



########NEW FILE########
__FILENAME__ = tf-32-reactive
#!/usr/bin/env python
import sys, re, operator, collections

class WordFrequenciesModel:
    """ Models the data. In this case, we're only interested 
    in words and their frequencies as an end result """
    freqs = {}
    def __init__(self):
        self._observers = []

    def register(self, obs):
        self._observers.append(obs)

    def update(self, path_to_file):
        try:
            stopwords = set(open('../stop_words.txt').read().split(','))
            words = re.findall('[a-z]{2,}', open(path_to_file).read().lower())
            self.freqs = collections.Counter(w for w in words if w not in stopwords)
            for obs in self._observers:
                obs.render()
        except IOError:
            print "File not found"
            self.freqs = {}

class WordFrequenciesView:
    def __init__(self, model):
        self._model = model
        model.register(self)

    def render(self):
        sorted_freqs = sorted(self._model.freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
        for (w, c) in sorted_freqs[:25]:
            print w, '-', c

class WordFrequencyController:
    def __init__(self, model, view):
        self._model, self._view = model, view

    def run(self):
        self._model.update(sys.argv[1])
        while True:
            print "Next file: " 
            sys.stdout.flush() 
            filename = sys.stdin.readline().strip()
            self._model.update(filename)

m = WordFrequenciesModel()
v = WordFrequenciesView(m)
c = WordFrequencyController(m, v)
c.run()

########NEW FILE########
__FILENAME__ = tf-32
#!/usr/bin/env python
import sys, re, operator, collections

class WordFrequenciesModel:
    """ Models the data. In this case, we're only interested 
    in words and their frequencies as an end result """
    freqs = {}
    stopwords = set(open('../stop_words.txt').read().split(','))
    def __init__(self, path_to_file):
        self.update(path_to_file)

    def update(self, path_to_file):
        try:
            words = re.findall('[a-z]{2,}', open(path_to_file).read().lower())
            self.freqs = collections.Counter(w for w in words if w not in self.stopwords)
        except IOError:
            print "File not found"
            self.freqs = {}

class WordFrequenciesView:
    def __init__(self, model):
        self._model = model

    def render(self):
        sorted_freqs = sorted(self._model.freqs.iteritems(), key=operator.itemgetter(1), reverse=True)
        for (w, c) in sorted_freqs[0:25]:
            print w, '-', c

class WordFrequencyController:
    def __init__(self, model, view):
        self._model, self._view = model, view
        view.render()

    def run(self):
        while True:
            print "Next file: " 
            sys.stdout.flush() 
            filename = sys.stdin.readline().strip()
            self._model.update(filename)
            self._view.render()


m = WordFrequenciesModel(sys.argv[1])
v = WordFrequenciesView(m)
c = WordFrequencyController(m, v)
c.run()

########NEW FILE########
__FILENAME__ = util
import sys, os

#
# getch in a platform-independent way
# Credit: http://code.activestate.com/recipes/134892/
#
class _Getch:
    """Gets a single character from standard input.  Does not echo to the
    screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            try:
                self.impl = _GetchMacCarbon()
            except(AttributeError, ImportError):
                self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt
    def __call__(self):
        import msvcrt
        return msvcrt.getch()

class _GetchMacCarbon:
    def __init__(self):
        import Carbon

    def __call__(self):
        import Carbon
        if Carbon.Evt.EventAvail(0x0008)[0]==0: # 0x0008 is the keyDownMask
            return ''
        else:
            (what,msg,when,where,mod)=Carbon.Evt.GetNextEvent(0x0008)[1]
            return chr(msg & 0x000000FF)

getch = _Getch()

def cls():
    os.system(['clear','cls'][os.name == 'nt'])


interactive = True
def get_input():
    global interactive
    if not interactive:
        return True

    while True: 
        key = ord(getch())
        if key == 32: # space bar
            return True
        elif key == 27: # ESC
            interactive = False
            return True


########NEW FILE########
__FILENAME__ = tf-33
#!/usr/bin/env python
import re, string, sys

with open("../stop_words.txt") as f:
    stops = set(f.read().split(",")+list(string.ascii_lowercase))
# The "database"
data = {}

# Internal functions of the "server"-side application
def error_state():
    return "Something wrong", ["get", "default", None]

# The "server"-side application handlers
def default_get_handler(args):
        rep = "What would you like to do?"
        rep += "\n1 - Quit" + "\n2 - Upload file"
        links = {"1" : ["post", "execution", None], "2" : ["get", "file_form", None]}
        return rep, links

def quit_handler(args):
    sys.exit("Goodbye cruel world...")

def upload_get_handler(args):
    return "Name of file to upload?", ["post", "file"]
        
def upload_post_handler(args):
    def create_data(filename):
        if filename in data:
            return
        word_freqs = {}
        with open(filename) as f:
            for w in [x.lower() for x in re.split("[^a-zA-Z]+", f.read()) if len(x) > 0 and x.lower() not in stops]:
                word_freqs[w] = word_freqs.get(w, 0) + 1
        word_freqsl = word_freqs.items()
        word_freqsl.sort(lambda x, y: cmp(y[1], x[1]))
        data[filename] = word_freqsl

    if args == None:
        return error_state()
    filename = args[0]
    try:
        create_data(filename)
    except:
        return error_state()
    return word_get_handler([filename, 0])

def word_get_handler(args):
    def get_word(filename, word_index):
        if word_index < len(data[filename]):
            return data[filename][word_index]
        else:
            return ("no more words", 0) 

    filename = args[0]; word_index = args[1]
    word_info = get_word(filename, word_index)
    rep = '\n#{0}: {1} - {2}'.format(word_index+1, word_info[0], word_info[1])
    rep += "\n\nWhat would you like to do next?"
    rep += "\n1 - Quit" + "\n2 - Upload file"
    rep += "\n3 - See next most-frequently occurring word"
    links = {"1" : ["post", "execution", None], 
             "2" : ["get", "file_form", None], 
             "3" : ["get", "word", [filename, word_index+1]]}
    return rep, links

# Handler registration
handlers = {"post_execution" : quit_handler,
            "get_default" : default_get_handler, 
            "get_file_form" : upload_get_handler, 
            "post_file" : upload_post_handler, 
            "get_word" : word_get_handler }

# The "server" core
def handle_request(verb, uri, args):
    def handler_key(verb, uri):
        return verb + "_" + uri

    if handler_key(verb, uri) in handlers:
        return handlers[handler_key(verb, uri)](args)
    else:
        return handlers[handler_key("get", "default")](args)

# A very simple client "browser"
def render_and_get_input(state_representation, links):
    print state_representation
    sys.stdout.flush()
    if type(links) is dict: # many possible next states
        input = sys.stdin.readline().strip()
        if input in links:
            return links[input]
        else:
            return ["get", "default", None]
    elif type(links) is list: # only one possible next state
        if links[0] == "post": # get "form" data
            input = sys.stdin.readline().strip()
            links.append([input]) # add the data at the end
            return links
        else: # get action, don't get user input
            return links
    else:
        return ["get", "default", None]

request = ["get", "default", None]
while True:
    # "server"-side computation
    state_representation, links = handle_request(*request)
    # "client"-side computation
    request = render_and_get_input(state_representation, links)

########NEW FILE########
__FILENAME__ = tf-34
#!/usr/bin/env python

import sys, re, operator, string, inspect

# Reusing the defensive style program to illustrate this

#
# The functions
#
def extract_words(path_to_file):
    """
    Takes a path to a file and returns the non-stop
    words, after properly removing nonalphanumeric chars
    and normalizing for lower case
    """
    fail = False
    word_list = []
    if type(path_to_file) is str and path_to_file:
        try:
            with open(path_to_file) as f:
                str_data = f.read()
        except IOError as e:
            print "I/O error({0}) when opening {1}: {2}".format(e.errno, path_to_file, e.strerror)
            fail = True
    
        if not fail:
            pattern = re.compile('[\W_]+')
            word_list = pattern.sub(' ', str_data).lower().split()

            try:
                with open('../stop_words.txt') as f:
                    stop_words = f.read().split(',')
            except IOError as e:
                print "I/O error({0}) when opening ../stops_words.txt: {1}".format(e.errno, e.strerror)
                fail = True

            if not fail:
                stop_words.extend(list(string.ascii_lowercase))

    return [w for w in word_list if not w in stop_words] if not fail else []

def frequencies(word_list):
    """
    Takes a list of words and returns a dictionary associating
    words with frequencies of occurrence
    """
    if type(word_list) is list and word_list <> []:
        word_freqs = {}
        for w in word_list:
            if w in word_freqs:
                word_freqs[w] += 1
            else:
                word_freqs[w] = 1
        return word_freqs
    else:
        return {}

def sort(word_freq):
    """
    Takes a dictionary of words and their frequencies
    and returns a list of pairs where the entries are
    sorted by frequency 
    """
    if type(word_freq) is dict and word_freq <> {}:
        return sorted(word_freq.iteritems(), key=operator.itemgetter(1), reverse=True)
    else:
        return []

#
# The main function
#
filename = sys.argv[1] if len(sys.argv) > 1 else "../input.txt"
word_freqs = sort(frequencies(extract_words(filename)))

for tf in word_freqs[0:25]:
    print tf[0], ' - ', tf[1]


########NEW FILE########
