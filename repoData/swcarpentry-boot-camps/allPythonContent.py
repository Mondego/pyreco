__FILENAME__ = exercise-allsixframes-ans
#!/usr/bin/env python
'''exercise_allsixframes.py   
Write the code to translate sequences in all six frames.  ''' 

from Bio import SeqIO
import sys

def allsixframes(record):
    ''' This function takes a SeqRecord object and returns a list of 
    six strings, with the translation of the sequence in the seqrecord 
    in all six frames.'''
#   your code goes here
    frame = []
    frame.append(record.seq.translate())  # translation
    frame.append(record.seq[1:].translate())  # translation + 1
    frame.append(record.seq[2:].translate())  # translation + 2
    frame.append(record.seq.reverse_complement().translate())  # reverse complement translation 
    frame.append(record.seq.reverse_complement()[1:].translate())  # reverse complement translation + 1 
    frame.append(record.seq.reverse_complement()[2:].translate())  # you should see the pattern by now
    return frame

#   Open a fastq file, goes through it record-by-record, and output
#   the sequence id, the sequence, and the translations 
print len(sys.argv)
if len(sys.argv) <= 1:
    filename = "data/test-sequences.fasta"
else:
    filename = sys.argv[1]
sys.stderr.write("Trying to open %s\n" % filename)

generator = SeqIO.parse(filename, "fasta")
for seqrecord in generator:
    sixframes = allsixframes(seqrecord)
    print ">%s\n%s" % (seqrecord.id, seqrecord.seq)
    for i in range(6):
        print i, sixframes[i]

########NEW FILE########
__FILENAME__ = exercise-allsixframes
#!/usr/bin/env python
'''exercise_allsixframes.py   
Write the code to translate sequences in all six frames.  ''' 

from Bio import SeqIO
import sys

def allsixframes(record):
    ''' This function takes a SeqRecord object and returns a list of 
    six strings, with the translation of the sequence in the seqrecord 
    in all six frames.'''
    frame = []
    frame.append(record.seq.translate())  # translation
    frame.append("NNN")  # translation + 1
    frame.append("NNN")  # translation + 2
    frame.append("NNN")  # reverse complement translation 
    frame.append("NNN")  # reverse complement translation + 1 
    frame.append("NNN")  # you should see the pattern by now
    return frame

#   Open a fastq file, goes through it record-by-record, and output
#   the sequence id, the sequence, and the translations 
print len(sys.argv)
if len(sys.argv) <= 1:
    filename = "data/test-sequences.fasta"
else:
    filename = sys.argv[1]
sys.stderr.write("Trying to open %s\n" % filename)

generator = SeqIO.parse(filename, "fasta")
for seqrecord in generator:
    sixframes = allsixframes(seqrecord)
    print ">%s\n%s" % (seqrecord.id, seqrecord.seq)
    for i in range(6):
        print i, sixframes[i]

########NEW FILE########
__FILENAME__ = exercise-b-trim-ans
#!/usr/bin/env python
'''exercise-b-trim.py   Write the code to trim sequences of low-quality bases. 
You can expect to turn the data in data/tiny.fastq into the filtered data 
exactly like data/tiny.trimmed.fastq  '''

from Bio import SeqIO
import sys

def btrimmer(seqrecord):
    ''' This function takes a Seq object containing fastq data and returns a Seq 
    object with low-quality bases  (bases with quality scores of 2 and below) 
    removed from the end of the read'''
    i = len(seqrecord)-1
    while seqrecord.letter_annotations["phred_quality"][i] <= 2:
         i = i - 1
    choppedsequence = seq[0:i+1]    #  This does NOT do what you want
    return choppedsequence

#   This part opens a fastq file, goes through it record-by-record, calls btrimmer 
#   and writes fastq-formatted reuslts to standard out.
generator = SeqIO.parse("data/tiny.fastq", "fastq")
for fastqsequence in generator:
     choppedfastqsequence = btrimmer(fastqsequence)
     sys.stdout.write(choppedfastqsequence.format("fastq"))

########NEW FILE########
__FILENAME__ = exercise-b-trim
#!/usr/bin/env python
'''exercise-b-trim.py   Write the code to trim sequences of low-quality bases. 
You can expect to turn the data in data/tiny.fastq into the filtered data 
exactly like data/tiny.trimmed.fastq  '''

from Bio import SeqIO
import sys

def btrimmer(seqrecord):
    ''' This function takes a SeqRecord object containing fastq data and returns a Seq 
    object with low-quality bases  (bases with quality scores of 2 and below) 
    removed from the end of the read'''
#   your code goes here
    choppedsequence = seqrecord    #  This is a placeholder, it does not trim!
    return choppedsequence

#   This part opens a fastq file, goes through it record-by-record, calls btrimmer 
#   and writes fastq-formatted reuslts to standard out.
generator = SeqIO.parse("data/tiny.fastq", "fastq")
for fastqsequence in generator:
    choppedfastqsequence = btrimmer(fastqsequence)
    sys.stdout.write(choppedfastqsequence.format("fastq"))

########NEW FILE########
__FILENAME__ = exercise-reversecomplement-ans
#!/usr/bin/env python
'''exercis-se_allsixframes.py   Write the code to translate sequences 
in all six frames.  ''' 

from Bio import SeqIO

def reversecomplement(record):
    ''' This function takes a SeqRecord object and returns its reverse complement'''
    reversecomplementsequence = record.seq.reverse_complement()
#   your code goes here
    return reversecomplementsequence 

#   Open a fastq file, goes through it record-by-record, and output
#   the sequence id, the sequence, and the translations 

generator = SeqIO.parse("data/test-sequences.fasta", "fasta")
for seqrecord in generator:
    reversesequence = reversecomplement(seqrecord)
    print ">%s\nORIG: %s" % (seqrecord.id, seqrecord.seq)
    print "REVC: %s" % reversesequence

########NEW FILE########
__FILENAME__ = exercise-reversecomplement
#!/usr/bin/env python
'''exercis-se_allsixframes.py   Write the code to translate sequences 
in all six frames.  ''' 

from Bio import SeqIO

def reversecomplement(record):
    ''' This function takes a SeqRecord object and returns its 
    reverse complement'''
#   your code goes here
    reversecomplementsequence = "N" * len(record.seq)
    return reversecomplementsequence 


#   Open a fastq file, goes through it record-by-record, and output
#   the sequence id, the sequence, and the translations 
generator = SeqIO.parse("data/test-sequences.fasta", "fasta")
for seqrecord in generator:
    reversesequence = reversecomplement(seqrecord)
    print ">%s\nORIG: %s" % (seqrecord.id, seqrecord.seq)
    print "REVC: %s" % reversesequence

########NEW FILE########
__FILENAME__ = gb2fa
#!/usr/bin/env python
'''Converts genbank files to sequence-only nucleic acid fasta'''

from Bio import SeqIO
import sys

outputformat = "fasta"
if len(sys.argv) != 3 :
    print "wrong number of args"
    print "Usage: gb2fa.py <input.gbk> <output.fasta>"
    sys.exit()
print "Converting %s to %s " % (sys.argv[1], sys.argv[2])
generator = SeqIO.parse(sys.argv[1], "genbank")
outfile = open(sys.argv[2], "w")
for record in generator:
    outfile.write(record.format(outputformat))

########NEW FILE########
__FILENAME__ = metagenome_statistics-example
#!/usr/bin/env python
'''This script retrieves a metagenome_statistics data structure from the MG-RAST API and
plots a graph using data from the web interface'''

import urllib, json, sys
import numpy as np

# retrieve the data by sending at HTTP GET request to the MG-RAST API
ACCESSIONNUMBER = "mgm4440613.3"   # this is a public job
some_url = "http://api.metagenomics.anl.gov/api2.cgi/metagenome_statistics/%s?verbosity=full" % ACCESSIONNUMBER
sys.stderr.write("Retrieving %s\n" % some_url) 
jsonobject = urllib.urlopen(some_url).read()

# convert the data from a JSON structure to a python data type, a dict of dicts.
jsonstructure = json.loads(jsonobject)

# get the elements of the data that we want out of the dict of dicts..
spectrum = np.array( jsonstructure["qc"]["kmer"]["15_mer"]["data"], dtype="float")
lengthdistribution = np.array( jsonstructure["length_histogram"]["upload"], dtype="int")
lengthdistribution2 = np.array( jsonstructure["length_histogram"]["post_qc"], dtype="int")

# display the first ten lines of the data table
np.savetxt(sys.stderr, spectrum[0:10], fmt="%d", delimiter="\t")

# plot the length distribution graph
import matplotlib.pyplot as plt
plt.plot(lengthdistribution[:, 0], lengthdistribution[:, 1], label="uploaded")
plt.plot(lengthdistribution2[:, 0], lengthdistribution2[:, 1], label="post qc")
plt.xlabel("length (bp)")
plt.ylabel("number of reads")
plt.title("Length distribution for %s" % ACCESSIONNUMBER ) 
plt.legend()
plt.show()

########NEW FILE########
__FILENAME__ = retrievegbk-ans
#!/usr/bin/env python
'''This script sends a efetch request to NCBI, requesting a genbank-formatted data file
and creates a .gbk file if successful
retrieve.py NC_000913  
should create NC_000913.gbk containing the annotated E. coli K12 reference genome '''

import os, sys
from Bio import Entrez

def downloadgbk(accessionno):
    filename = "%s.gbk" % accessionno       
    print "Trying efectch on %s, writing to %s" % ( accessionno, filename )
    if not os.path.isfile(filename):  
        net_handle = Entrez.efetch(db="nucleotide", id=accessionno, rettype="gb", retmode="text") 
        out_handle = open(filename, "w")
        out_handle.write(net_handle.read() ) 
        out_handle.close()
        net_handle.close()
    else:
        print "skipping, %s already exists!" % filename

Entrez.email = "trimble@anl.gov"
Entrez.tool = "SoftwareCarpentryBootcamp"

if len(sys.argv) != 2:
    sys.exit("Usage: retrieve.py <accession number>")
accession = sys.argv[1]     # take the first program argument

downloadgbk(accession)

########NEW FILE########
__FILENAME__ = retrievegbk
#!/usr/bin/env python
'''This script sends a efetch request to NCBI, requesting a genbank-formatted data file
and creates a .gbk file if successful
retrieve.py NC_000913  
should create NC_000913.gbk containing the annotated E. coli K12 reference genome '''

import os, sys

def downloadgbk(accessionno):
    '''downloadgbk(accessionno)
    Takes a str as an argument
    Creates a file called argument.gbk if it doesn't exist
    populates the file with genbank-formatted data from NCBI's efectch API'''

    from Bio import Entrez
    Entrez.email = "swc@example.com    # Tell NCBI who you are!
    Entrez.tool = "SoftwareCarpentryBootcamp"

    filename = "%s.gbk" % accessionno       
    print "Trying efectch on %s, writing to %s" % ( accessionno, filename )
    if not os.path.isfile(filename):  
        net_handle = Entrez.efetch(db="nucleotide", id=accessionno, rettype="gb", retmode="text") 
        out_handle = open(filename, "w")
        out_handle.write(net_handle.read()) 
        net_handle.close()
        out_handle.close()
    else:
        print "skipping, %s already exists!" % filename

def main():
    if len(sys.argv) != 2:    # check that exactly one argument was suppplied 
        sys.exit("Usage: retrieve.py <accession number>")
    accession = sys.argv[1]     # assign the first argument to accession
    downloadgbk(accession)      # call the subroutine downloadgbk

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = skeleton
#!/usr/bin/env python
'''This is a skeleton python program.  It doesn't do anything, but it parses arguments and 
calls a subroutine.'''

def do_something(arg):
    sys.stderr.write("I'm doing something with argument %s!\n" % arg)
    return(42)

import sys, os
from optparse import OptionParser

if __name__ == '__main__':
    usage  = "usage: skeleton.py [<options>] [<arguments>]"
    parser = OptionParser(usage)
    parser.add_option("-i", "--input",  dest="infile", default=None, help="Input filename")
    parser.add_option("-o", "--output", dest="outfile", default=None, help="Output filename")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=True, help="Verbose")
    (opts, args) = parser.parse_args()
#    if len(args) == 0 :
#        sys.exit("No arguments supplied!")
#    argument = args[0]
    inputfile = opts.infile

#    if opts.verbose: 
#        sys.stdout.write("Argument: %s\n" % argument ) 

    do_something(inputfile)

    if opts.verbose: 
        sys.stdout.write("Done. \n")

########NEW FILE########
__FILENAME__ = tiny-fastq-parser
#!/usr/bin/env python
'''tiny-fastq-parser.py
opens an example FASTQ file and dumps the data fields'''

from Bio import SeqIO
generator = SeqIO.parse("data/tiny.fastq", "fastq")
for sequence in generator:
    print sequence.id
    print sequence.seq
    print sequence.letter_annotations["phred_quality"]


########NEW FILE########
__FILENAME__ = data_structures

# <markdowncell>
# # Compound Data Types: Lists, Dictionaries, Sets, Tuples, and Reading Files
# 
# * * * * *
# <markdowncell>
# **Based on lecture materials by Milad Fatenejad, Joshua R. Smith, and Will Trimble**
# 
# Python would be a fairly useless language if it weren't for the compound data types. The main two are **lists** and **dictionaries**, but I'll mention **sets** and **tuples** as well. I'll also go over reading text data from files. 
# 
# <markdowncell>
# ## Lists
# 
# A list is an ordered, indexable collection of data. Lets say you have collected some current and voltage data that looks like this:
# 
# ```
# voltage:
# -2.0
# -1.0
# 0.0
# 1.0
# 2.0
# 
# current:
# -1.0
# -0.5
# 0.0
# 0.5
# 1.0
# ```
# 
# So you could put that data into lists like
# 
# <codecell>
voltageList = [-2.0, -1.0, 0.0, 1.0, 2.0]
currentList = [-1.0, -0.5, 0.0, 0.5, 1.0]

# <markdowncell>
# obviously voltageList is of type list:
# 
# <codecell>
type(voltageList)
# <markdowncell>
# 
# Python lists have the charming (annoying?) feature that they are indexed from zero. Therefore, to find the value of the first item in voltageList:
# 
# <codecell>
voltageList[0]
# <markdowncell>
# 
# And to find the value of the third item

# <codecell>
voltageList[2]
# <markdowncell>

# Lists can be indexed from the back using a negative index. The last item of currentList
# 
# <codecell>
currentList[-1]
# <markdowncell>
# 
# and the next-to-last
# <codecell>
currentList[-2]
# <markdowncell>
# 
# You can "slice" items from within a list. Lets say we wanted the second through fourth items from voltageList
# <codecell>
voltageList[1:4]
# <markdowncell>
# 
# Or from the third item to the end
# <codecell>
voltageList[2:]
# <markdowncell>
# 
# and so on.
# 
# <markdowncell>
# ### Append and Extend
# 
# Just like strings have methods, lists do too.
# 
# <codecell>
dir(list)
# <markdowncell>
# 
# One useful method is append. Lets say we want to stick the following data on the end of both our lists.
# 
# ```
# voltage:
# 3.0
# 4.0
# 
# current:
# 1.5
# 2.0
# ```
# 
# If you want to append items to the end of a list, use the append method.
# 
# <codecell>
voltageList.append(3.)
# <codecell>
voltageList.append(4.)
# <codecell>
voltageList
# <markdowncell>
# 
# You can see how that approach might be tedious in certain cases. If you want to concatenate a list onto the end of another one, use extend.
# 
# <codecell>
currentList.extend([1.5, 2.0])
# <codecell>
currentList
# <markdowncell>
# ### Length of Lists
# 
# Sometimes you want to know how many items are in a list. Use the len command.
# 
# <codecell>
len(voltageList)
# <markdowncell>
# 
# ### Heterogeneous Data
# 
# Lists can contain hetergeneous data.
# 
# <codecell>
dataList = ["experiment: current vs. voltage", \
    "run", 47, \
    "temperature", 372.756, \
    "current", [-1.0, -0.5, 0.0, 0.5, 1.0], \
    "voltage", [-2.0, -1.0, 0.0, 1.0, 2.0]]
# <codecell>
print dataList
# <markdowncell>
 
# We've got strings, ints, floats, and even other lists in there. The slashes are there so we can continue on the next line. They aren't necessary but they can sometimes make things look better.
# 
# ## Assigning Variables to Other Variables
# 
# Something that might cause you headaches in the future is how python deals with assignment of one variable to another. When you set a variable equal to another, both variables point to the same thing. Changing the first one ends up changing the second. Be careful about this fact.
# 
# <codecell>
a = [1,2]
# <codecell>
b = a
# <codecell>
a.append(10)
# <codecell>
b
# <markdowncell>
# 
# There's a ton more to know about lists, but lets press on. Check out Dive Into Python or the help documentation for more info.
# 
# ## Reading From Files
# 
# At this point it is useful to take a detour regarding files. Lets say you have a file with some current and voltage data and some metadata.
# 
# ```
# data.dat:
# 
# experiment: current vs. voltage
# run: 47
# temperature: 372.756
# current: [-1.0, -0.5, 0.0, 0.5, 1.0]
# voltage: [-2.0, -1.0, 0.0, 1.0, 2.0]
# ```
# 
# We can read this data into a list type variable pretty easily.
# 
# <codecell>
f = open("data.dat")
# <codecell>
ivdata = f.readlines()
# <codecell>
f.close()
# <codecell>
ivdata
# <markdowncell>
# 
# Right now the data in ivdata isn't in a particularly useful format, but you can imagine that with some additional programming we could straighten it out. We will eventually do that.
# 
# ## Tuples
# 
# Tuples are another of python's basic compound data types that are almost like lists. The difference is that a tuple is immutable; once you set the data in it, the tuple cannot be changed. You define a tuple as follows.
# 
# <codecell>
tup = ("red", "white", "blue")
 
# <codecell>
type(tup)
# <markdowncell>
# 
# You can slice and index the tuple exactly like you would a list. Tuples are used in the inner workings of python, and a tuple can be used as a key in a dictionary, whereas a list cannot as we will see in a moment.
# 
# See if you can retrieve the third element of **tup**:
# <codecell>
 
# <markdowncell>
# ## Sets
# 
# Most introductary python courses do not go over sets this early (or at all), but I've found this data type to be useful. The python set type is similar to the idea of a mathematical set: it is an unordered collection of unique things. Consider:
# 
# <codecell>
fruit = set(["apple", "banana", "pear", "banana"]) 
# <markdowncell>
#You have to use a list to create a set.

# 
# Since sets contain only unique items, there's only one banana in the set fruit.
# 
# You can do things like intersections, unions, etc. on sets just like in math. Here's an example of an intersection of two sets (the common items in both sets).
# 
# <codecell>
firstBowl = set(["apple", "banana", "pear", "peach"])
 
# <codecell>
secondBowl = set(["peach", "watermelon", "orange", "apple"])
 
# <codecell>
set.intersection(firstBowl, secondBowl)
# <codecell>
set(['apple', 'peach'])

# <markdowncell>
# 
# You can check out more info using the help docs. We won't be returning to sets, but its good for you to know they exist.
# 
# ## Dictionaries
# 
# Recall our file data.dat which contained our current-voltage data and also some metadata. We were able to import the data as a list, but clearly the list type is not the optial choice for a data model. The dictionary is a much better choice. A python dictionary is a collection of key, value pairs. The key is a way to name the data, and the value is the data itself. Here's a way to create a dictionary that contains all the data in our data.dat file in a more sensible way than a list.
# 
# <codecell>
dataDict = {"experiment": "current vs. voltage", \
                    "run": 47, \
                    "temperature": 372.756, \
                    "current": [-1.0, -0.5, 0.0, 0.5, 1.0], \
                    "voltage": [-2.0, -1.0, 0.0, 1.0, 2.0]}
# <codecell>
print dataDict

# <markdowncell>
# 
# This model is clearly better because you no longer have to remember that the run number is in the second position of the list, you just refer directly to "run":
# 
# <codecell>
dataDict["run"]
# <markdowncell>
# 
# If you wanted the voltage data list:
# 
# <codecell>
dataDict["voltage"]
# <markdowncell>
# 
# Or perhaps you wanted the last element of the current data list
# 
# <codecell>
dataDict["current"][-1]
# <markdowncell>
# 
# Once a dictionary has been created, you can change the values of the data if you like.
# 
# <codecell>
dataDict["temperature"] = 3275.39
# <markdowncell>
# 
# You can also add new keys to the dictionary.  Note that dictionaries are indexed with square braces, just like lists--they look the same, even though they're very different.
# 
# <codecell>
dataDict["user"] = "Johann G. von Ulm"
# <markdowncell>
# 
# Dictionaries, like strings, lists, and all the rest, have built-in methods. Lets say you wanted all the keys from a particular dictionary.
# 
# <codecell>
dataDict.keys()
# <markdowncell>
# 
# also, values
# 
# <codecell>
dataDict.values()
# <markdowncell>
# 
# The help documentation has more information about what dictionaries can do.
# 
# Its worth mentioning that the value part of a dictionary can be any kind of data, even another dictionary, or some complex nested structure. The same is true about a list: they can contain complex data types.
# 
# Since tuples are immutable, they can be used as keys for dictionaries. Lists are mutable, and therefore cannot.
# 
# When you design software in python, most data will end up looking either like a list or a dictionary. These two data types are very important in python and you'll end up using them all the time.

########NEW FILE########
__FILENAME__ = exercises
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# # Exercise 1
# 1. Calculate the mean of the numbers 2, 3, and 10.

# <codecell>
  
# <markdowncell>

# # Exercise 2
# 1. Make a list with 5 things in it.
# <codecell>
  
# 1. Add two more things.
# <codecell>
   
# <markdowncell>
# # Exercise 2
# 1. Make a dictionary whose keys are the strings "zero" through "nine" and whose values are ints 0 through 9.
# <codecell>
digitsdict = {}
#  Your code goes here

# <markdowncell>
# # Exercise 3
# 1. Make a dictionary and experiment using different types as keys. Can containers be keys?

# <codecell>
  

# <markdowncell>

# # Exercises 4
# 1. Write an if statement that prints whether x is even or odd
# <codecell>
x=4
print x
if x < 5:
  print "x is less than five!"
else: 
  print "x is not less than five!"

# <codecell>

# <markdowncell>

# # Exercises 5
# 1. Using a loop, calculate the factorial of 42 (the product of all integers up to and including 42).

# <codecell>
   
# <markdowncell>

# # Exercises 6
# 1. Create a function that returns the factorial of a given number.

# <codecell>
 
# <markdowncell>

# # Exercise 7
# 7A. Read the file 'big_animals.txt' and print each line and the length of each line.
# <codecell>

# 7B. Read the file 'big_animals.txt' again and print each line where the number of animals sighted is greater than 10.  We'll won't output the lines with fewer than 10 animals.
# <codecell>

# 7C. Read the file 'big_animals.txt' again and return a list of tuples.
# <codecell>

# 7D. Turn the code for #7C into a function and use it on the files 'merida_animals.txt' and 'fergus_animals.txt'.

# <codecell>
 
# <markdowncell>
# # Exercise 8
# 1.  Check your answer to Exercise 5 (the value of 42!) using the **math.gamma()** function.
# <codecell>
import math


########NEW FILE########
__FILENAME__ = index_error
#!/usr/bin/env python
"""
IndexError - accessing a list by an index that doesn't exist. This usually
comes up due to some messed up logic around the source of the error.
"""

# Try accessing an element of this list
a_list = ["you", "should", "avoid", "accessing", 
          "lists", "by", "index", "anyway!"]
non_existent_element = a_list[100]

# Pythonic bonus points: only use a list if you're going to be iterating over
# every element. The following won't cause an IndexError.
for item in a_list:
    print item

# If you need to access random elements of a list, consider rewriting your code
# to use a dictionary.
########NEW FILE########
__FILENAME__ = io_error
#!/usr/bin/env python
"""
IOError - trying to open a file that doesn't exist (usually).
"""

# This will error unless the code is in the same directory as a file named
# "a_file.txt"
with open("a_file.txt") as in_file:
    print in_file.read()

########NEW FILE########
__FILENAME__ = key_error
#!/usr/bin/env python
"""
KeyError - accessing a dictionary by a key that doesn't exist. Like a name
error, this is usually due to a typo.
"""

# Define a dictionary and then access a nonexistent element
a_dict = {
          "a really long key name": 1, 
          "some other": "stuff not relevant",
          "to the": "error"
         }
value = a_dict["a raelly long key name"]

########NEW FILE########
__FILENAME__ = name_error
#!/usr/bin/env python
"""
NameError - usually happens because of typos. Can also happen by forgetting
to initialize certain variable types.
"""

# A typo-induced NameError
a_really_complicated_variable_name = 1
something_else = a_really_complciated_name + 1

# A NameError from forgetting to initialize a list (or dictionary) data type
for i in range(100):
    my_dict[4 * i] = i - 1
########NEW FILE########
__FILENAME__ = syntax_error
#!/usr/bin/env python
"""
SyntaxError - There's something wrong with how you wrote the surrounding code.
Check your parentheses, and make sure there are colons where needed.
"""

while True
    print "Where's the colon at?"
########NEW FILE########
__FILENAME__ = type_error
#!/usr/bin/env python
"""
TypeError - trying to do an operation with incompatible data types.
"""

# You can add strings or ints together, no problem
added_strings = "1" + "1"
added_ints = 1 + 1

# But what is the sum of an int and a string? (spoiler: it's a TypeError)
added_mixed_types = added_strings + added_ints

# Here's something to mess with you. Does this work?
multiplied_mixed_types = added_strings * added_ints
########NEW FILE########
__FILENAME__ = value_error
#!/usr/bin/env python
"""
ValueError - Running a function with an improper data type. Usually comes up
when you're trying to convert between strings, floats, and ints
"""

# You can't convert all strings to ints!
print int("Go home, int(). You're drunk.")
########NEW FILE########
__FILENAME__ = 1_conway_pre_linted
#!/usr/bin/env python
"""
Conway's game of life example, part one.

This has typos and unused imports. Use a linter like pyflakes to catch them.
"""


from math import sqrt

def conway(population, 
    generations = 100):
    for i in range(genrations): population = evolve(population)
    return popluation

def evolve(population):
    activeCells = population[:]
    for cell in population:
        for neighbor in neighbors(cell):
            if neighbor not in activeCells: activeCells.append(neighbor)
    newPopulation = []
    for cell in activeCells:
        count = sum(neighbor in population for neighbor in neighbors(cell))
        if count == 3 or (count == 2 and cell in population): 
            if cell not in newPopulation: newPopluation.add(cell)
    return newPopulation

def neighbors(cell):
    x, y = cell
    return [(x, y), (x+1, y), (x-1, y), (x, y+1), (x, y-1), (x+1, y+1), (x+1, y-1), (x-1, y+1), (x-1, y-1)]

glider = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 2)]
print conway(glider)

########NEW FILE########
__FILENAME__ = 2_conway_pre_formatted
#!/usr/bin/env python
"""
Conway's game of life example, part two.

This does not conform to PEP8 standards. Use pep8 to check most standards, and
then fix the others by eye.
"""


def conway(population, 
    generations = 100):
    for i in range(generations): population = evolve(population)
    return population

def evolve(population):
    activeCells = population[:]
    for cell in population:
        for neighbor in neighbors(cell):
            if neighbor not in activeCells: activeCells.append(neighbor)
    newPopulation = []
    for cell in activeCells:
        count = sum(neighbor in population for neighbor in neighbors(cell))
        if count == 3 or (count == 2 and cell in population):
            if cell not in newPopulation: newPopulation.append(cell)
    return newPopulation

def neighbors(cell):
    x, y = cell
    return [(x, y), (x+1, y), (x-1, y), (x, y+1), (x, y-1), (x+1, y+1), (x+1, y-1), (x-1, y+1), (x-1, y-1)]

glider = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 2)]
print conway(glider)

########NEW FILE########
__FILENAME__ = 3_conway_pre_debugged
#!/usr/bin/env python
"""
Conway's game of life example, part three.

This code has a bug that makes the game return improper results.
"""


def conway(population, generations=100):
    """Runs Conway's game of life on an initial population."""
    for i in range(generations):
        population = evolve(population)
    return population


def evolve(population):
    """Evolves the population by one generation."""
    # Get a unique set of discrete cells that need to be checked
    active_cells = population[:]
    for cell in population:
        for neighbor in neighbors(cell):
            if neighbor not in active_cells:
                active_cells.append(neighbor)
    # For each cell in the set, test if it lives or dies
    new_population = []
    for cell in active_cells:
        count = sum(neighbor in population for neighbor in neighbors(cell))
        if count == 3 or (count == 2 and cell in population):
            if cell not in new_population:
                new_population.append(cell)
    # Return the new surviving population
    return new_population


def neighbors(cell):
    x, y = cell
    return [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
            (x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)]

glider = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 2)]
print conway(glider)

########NEW FILE########
__FILENAME__ = 4_conway_pre_profiled
#!/usr/bin/env python
"""
Conway's game of life example, part four.

This code is functional, but it doesn't make use of sets in a scenario where 
they're the perfect data type.
"""


def conway(population, generations=100):
    """Runs Conway's game of life on an initial population."""
    for i in range(generations):
        population = evolve(population)
    return population


def evolve(population):
    """Evolves the population by one generation."""
    # Get a unique set of discrete cells that need to be checked
    active_cells = population[:]
    for cell in population:
        for neighbor in neighbors(cell):
            if neighbor not in active_cells:
                active_cells.append(neighbor)
    # For each cell in the set, test if it lives or dies
    new_population = []
    for cell in active_cells:
        count = sum(neighbor in population for neighbor in neighbors(cell))
        if count == 3 or (count == 2 and cell in population):
            if cell not in new_population:
                new_population.append(cell)
    # Return the new surviving population
    return new_population


def neighbors(cell):
    """Returns the neighbors of a given cell."""
    x, y = cell
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1),
            (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)]

glider = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 2)]
print conway(glider)


########NEW FILE########
__FILENAME__ = 5_conway_final
#!/usr/bin/env python
"""
Conway's game of life, final version.

Rules:
 * Any cell with fewer than two neighbors dies (underpopulation)
 * Any cell with more than three neighbors dies (overpopulation)
 * Any empty spot with three neighbors becomes a live cell (reproduction)

Check out the wikipedia article for more information, including interesting
starting populations.
"""


def conway(population, generations=100):
    """Runs Conway's game of life on an initial population."""
    population = set(population)
    for i in range(generations):
        population = evolve(population)
    return list(population) 


def evolve(population):
    """Evolves the population by one generation."""
    # Get a unique set of discrete cells that need to be checked
    active_cells = population | set([neighbor for p in population
                                    for neighbor in neighbors(p)])
    # For each cell in the set, test if it lives or dies
    new_population = set()
    for cell in active_cells:
        count = sum([neighbor in population for neighbor in neighbors(cell)])
        if count == 3 or (count == 2 and cell in population):
            new_population.add(cell)
    # Return the new surviving population
    return new_population


def neighbors(cell):
    """Returns the neighbors of a given cell."""
    x, y = cell
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1),
            (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)]

glider = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 2)]
print conway(glider)

########NEW FILE########
__FILENAME__ = linting_example
#!/usr/bin/env python
"""
Examples of things pyflakes will pick up
"""

# Unused imports
from math import sin

# Using undefined variables
# (usually checking undefined variables solves typo issues)
x = no_one_defined_me + 1

# Using an uninitialized variable
non_existent_dict["a_field"] = 100

########NEW FILE########
__FILENAME__ = pdb_example
#!/usr/bin/env python
"""
Setting a trace in some sample code with pdb.
"""

import pdb

a = 2
while True:
    print "This number's gonna get HUGEE"
    pdb.set_trace()
    a *= a

########NEW FILE########
__FILENAME__ = profiler_example
#!/usr/bin/env python
"""
A script that shows off profiling via list iteration schemes
"""

from random import random


def dynamic_array(size=1000000):
    """Fills an array that is sized dynamically."""
    dynamic = []
    for i in range(size):
        dynamic.append(random() * i)
    return dynamic


def static_array(size=1000000):
    """Fills an array that is pre-allocated."""
    static = [None] * size
    for i in range(size):
        static[i] = random() * i
    return static


def comprehension_array(size=1000000):
    """Fills an array that is handled by Python via list comprehension."""
    return [random() * i for i in range(size)]

if __name__ == "__main__":
    import sys

    # Allow the user to input filled array sizes
    size = 1000000
    for i, val in enumerate(sys.argv):
        if val == "--size":
            size = int(sys.argv[i + 1])

    # Allow the user to specify the method of array filling
    if "--dynamic" in sys.argv:
        dynamic_array(size)
    if "--static" in sys.argv:
        static_array(size)
    if "--comprehension" in sys.argv:
        comprehension_array(size)

########NEW FILE########
__FILENAME__ = segfault
#!/usr/bin/env python
"""
A C function that segfaults, and a wrapper that can handle it
"""

import ctypes

def cause_segmentation_fault():
    """Crashes the Python interpreter by segfaulting."""
    i = ctypes.c_char('a')
    j = ctypes.pointer(i)
    c = 0
    while True:
        j[c] = 'a'
        c += 1
    return j

if __name__ == "__main__":
    import sys
    
    # This handles the segfault and gives us a traceback
    if "--handle" in sys.argv:
        import faulthandler
        faulthandler.enable()
    
    # This runs the function that will segfault
    cause_segmentation_fault()
########NEW FILE########
__FILENAME__ = style_example
#!/usr/bin/env python
"""
A myriad of poor formatting, copied from Anthony Scopatz
"""

import os

aNumber = 0.5

def HappyGo_lucky():  
   tten = aNumber * 10 # times ten
   if tten< 60:
         return 60
   else:
     return tten

409

print HappyGo_lucky()

########NEW FILE########
__FILENAME__ = trace_back_example
def add_two(x):
    return x+2.0

def multiply_by_5(x):
    return x*5

def divide_by_4(x):
    return x/4.0

def run_equation(x):
    return add_two(multiply_by_5(divide_by_4(x)))


########NEW FILE########
__FILENAME__ = close_line
import numpy as np
from scipy.optimize import fmin

#
# Attempt 1
#

def point_on_line1(x, p1, p2):
    y = p1[1] + (x - p1[0])*(p2[1] - p1[1]) / (p2[0] - p1[0])
    return np.array([x, y])


def dist_from_line1(x, pdata, p1, p2):
    pline = point_on_line1(x, p1, p2)
    return np.sqrt(np.sum((pline - pdata)**2))


def closest_data_to_line1(data, p1, p2):
    dists = np.empty(len(data), dtype=float)
    for i, pdata in enumerate(data):
        x = fmin(dist_from_line1, p1[0], (pdata, p1, p2), disp=False)[0]
        dists[i] = dist_from_line1(x, pdata, p1, p2)
    imin = np.argmin(dists)
    return imin, data[imin]


#
# Attempt 2
#

def dist_from_line2(pdata, p1, p2):
    a = np.sqrt(np.sum((p1 - pdata)**2))
    b = np.sqrt(np.sum((p2 - pdata)**2))
    c = np.sqrt(np.sum((p2 - p1)**2))
    h = a * np.sqrt(1.0 - ((a**2 + c**2 - b**2) / (2.0 * a * c))**2)
    return h

def closest_data_to_line2(data, p1, p2):
    dists = np.empty(len(data), dtype=float)
    for i, pdata in enumerate(data):
        dists[i] = dist_from_line2(pdata, p1, p2)
    imin = np.argmin(dists)
    return imin, data[imin]

#
# Attempt 3
#

def perimeter3(pdata, p1, p2):
    a = np.sqrt(np.sum((p1 - pdata)**2))
    b = np.sqrt(np.sum((p2 - pdata)**2))
    c = np.sqrt(np.sum((p2 - p1)**2))
    return (a + b + c)

def closest_data_to_line3(data, p1, p2):
    peris = np.empty(len(data), dtype=float)
    for i, pdata in enumerate(data):
        peris[i] = perimeter3(pdata, p1, p2)
    imin = np.argmin(peris)
    return imin, data[imin]

#
# Attempt 4
#

def closest_data_to_line4(data, p1, p2):
    return data[np.argmin(np.sqrt(np.sum((p1 - data)**2, axis=1)) + \
                np.sqrt(np.sum((p2 - data)**2, axis=1)))]


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# FLASH documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 19 15:40:40 2012.
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
sys.path.insert(0, os.path.abspath('sphinxext'))
sys.path.insert(1, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 
              #'sphinx.ext.mathjax', 
              #'sphinx.ext.jsmath', 
              'sphinx.ext.pngmath', 
              'sphinx.ext.viewcode',
              'numpydoc', 
              'ipython_console_highlighting',]

# Extension configuration
autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'THW'
copyright = u'2012, The Hacker Within'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2012'
# The full version, including alpha/beta/rc tags.
release = '2012'

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
exclude_patterns = ['_build']

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
#pygments_style = 'sphinx'
#pygments_style = 'tango'
pygments_style = 'pastie'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'cloud_flash'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {'sidebarbgcolor': '#f6fcfc',
                      'relbarbgcolor': '#323039',
                      'footerbgcolor': '#222127',
                      'bodytrimcolor': '#80858a',
                      'linkcolor': '#A92727',
                      'textcolor': '#323039', 
                      'sectionbgcolor': '#77181E',
                      #'sectiontextcolor': '#777777',
                      'sectiontrimcolor': '#f6fcfc', 
                      'codebgcolor': '#f6fcfc',
                      #'codetextcolor': '#323039', 
                      #'codetextcolor': '#222127', 
                      'codetextcolor': '#000000', 
                      'quotebgcolor': '#f6fcfc',
                      }

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "{project} {release}".format(project=project, release=release)

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = '_static/flash-logo-sm.gif'
html_logo = '_static/thwlogo-small.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'flash.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

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
htmlhelp_basename = 'THWdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'THW.tex', u'THW Documentation',
   u'The Hacker Within', 'manual'),
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

# Added jsMath
jsmath_path = "jsMath/easy/load.js"


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'thw', u'THW Documentation',
     [u'The HAcker Within'], 1)
]

########NEW FILE########
__FILENAME__ = apigen
"""Attempt to generate templates for module reference with Sphinx

XXX - we exclude extension modules

To include extension modules, first identify them as valid in the
``_uri2path`` method, then handle them in the ``_parse_module`` script.

We get functions and classes by parsing the text of .py files.
Alternatively we could import the modules for discovery, and we'd have
to do that for extension modules.  This would involve changing the
``_parse_module`` method to work via import and introspection, and
might involve changing ``discover_modules`` (which determines which
files are modules, and therefore which module URIs will be passed to
``_parse_module``).

NOTE: this is a modified version of a script originally shipped with the
PyMVPA project, which we've adapted for NIPY use.  PyMVPA is an MIT-licensed
project."""

# Stdlib imports
import os
import re

# Functions and classes
class ApiDocWriter(object):
    ''' Class for automatic detection and parsing of API docs
    to Sphinx-parsable reST format'''

    # only separating first two levels
    rst_section_levels = ['*', '=', '-', '~', '^']

    def __init__(self,
                 package_name,
                 rst_extension='.rst',
                 package_skip_patterns=None,
                 module_skip_patterns=None,
                 ):
        ''' Initialize package for parsing

        Parameters
        ----------
        package_name : string
            Name of the top-level package.  *package_name* must be the
            name of an importable package
        rst_extension : string, optional
            Extension for reST files, default '.rst'
        package_skip_patterns : None or sequence of {strings, regexps}
            Sequence of strings giving URIs of packages to be excluded
            Operates on the package path, starting at (including) the
            first dot in the package path, after *package_name* - so,
            if *package_name* is ``sphinx``, then ``sphinx.util`` will
            result in ``.util`` being passed for earching by these
            regexps.  If is None, gives default. Default is:
            ['\.tests$']
        module_skip_patterns : None or sequence
            Sequence of strings giving URIs of modules to be excluded
            Operates on the module name including preceding URI path,
            back to the first dot after *package_name*.  For example
            ``sphinx.util.console`` results in the string to search of
            ``.util.console``
            If is None, gives default. Default is:
            ['\.setup$', '\._']
        '''
        if package_skip_patterns is None:
            package_skip_patterns = ['\\.tests$']
        if module_skip_patterns is None:
            module_skip_patterns = ['\\.setup$', '\\._']
        self.package_name = package_name
        self.rst_extension = rst_extension
        self.package_skip_patterns = package_skip_patterns
        self.module_skip_patterns = module_skip_patterns

    def get_package_name(self):
        return self._package_name

    def set_package_name(self, package_name):
        ''' Set package_name

        >>> docwriter = ApiDocWriter('sphinx')
        >>> import sphinx
        >>> docwriter.root_path == sphinx.__path__[0]
        True
        >>> docwriter.package_name = 'docutils'
        >>> import docutils
        >>> docwriter.root_path == docutils.__path__[0]
        True
        '''
        # It's also possible to imagine caching the module parsing here
        self._package_name = package_name
        self.root_module = __import__(package_name)
        self.root_path = self.root_module.__path__[0]
        self.written_modules = None

    package_name = property(get_package_name, set_package_name, None,
                            'get/set package_name')

    def _get_object_name(self, line):
        ''' Get second token in line
        >>> docwriter = ApiDocWriter('sphinx')
        >>> docwriter._get_object_name("  def func():  ")
        'func'
        >>> docwriter._get_object_name("  class Klass(object):  ")
        'Klass'
        >>> docwriter._get_object_name("  class Klass:  ")
        'Klass'
        '''
        name = line.split()[1].split('(')[0].strip()
        # in case we have classes which are not derived from object
        # ie. old style classes
        return name.rstrip(':')

    def _uri2path(self, uri):
        ''' Convert uri to absolute filepath

        Parameters
        ----------
        uri : string
            URI of python module to return path for

        Returns
        -------
        path : None or string
            Returns None if there is no valid path for this URI
            Otherwise returns absolute file system path for URI

        Examples
        --------
        >>> docwriter = ApiDocWriter('sphinx')
        >>> import sphinx
        >>> modpath = sphinx.__path__[0]
        >>> res = docwriter._uri2path('sphinx.builder')
        >>> res == os.path.join(modpath, 'builder.py')
        True
        >>> res = docwriter._uri2path('sphinx')
        >>> res == os.path.join(modpath, '__init__.py')
        True
        >>> docwriter._uri2path('sphinx.does_not_exist')

        '''
        if uri == self.package_name:
            return os.path.join(self.root_path, '__init__.py')
        path = uri.replace('.', os.path.sep)
        path = path.replace(self.package_name + os.path.sep, '')
        path = os.path.join(self.root_path, path)
        # XXX maybe check for extensions as well?
        if os.path.exists(path + '.py'): # file
            path += '.py'
        elif os.path.exists(os.path.join(path, '__init__.py')):
            path = os.path.join(path, '__init__.py')
        else:
            return None
        return path

    def _path2uri(self, dirpath):
        ''' Convert directory path to uri '''
        relpath = dirpath.replace(self.root_path, self.package_name)
        if relpath.startswith(os.path.sep):
            relpath = relpath[1:]
        return relpath.replace(os.path.sep, '.')

    def _parse_module(self, uri):
        ''' Parse module defined in *uri* '''
        filename = self._uri2path(uri)
        if filename is None:
            # nothing that we could handle here.
            return ([],[])
        f = open(filename, 'rt')
        functions, classes = self._parse_lines(f)
        f.close()
        return functions, classes
    
    def _parse_lines(self, linesource):
        ''' Parse lines of text for functions and classes '''
        functions = []
        classes = []
        for line in linesource:
            if line.startswith('def ') and line.count('('):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    functions.append(name)
            elif line.startswith('class '):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    classes.append(name)
            else:
                pass
        functions.sort()
        classes.sort()
        return functions, classes

    def generate_api_doc(self, uri):
        '''Make autodoc documentation template string for a module

        Parameters
        ----------
        uri : string
            python location of module - e.g 'sphinx.builder'

        Returns
        -------
        S : string
            Contents of API doc
        '''
        # get the names of all classes and functions
        functions, classes = self._parse_module(uri)
        if not len(functions) and not len(classes):
            print 'WARNING: Empty -',uri  # dbg
            return ''

        # Make a shorter version of the uri that omits the package name for
        # titles 
        uri_short = re.sub(r'^%s\.' % self.package_name,'',uri)
        
        ad = '.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n'

        chap_title = uri_short
        ad += (chap_title+'\n'+ self.rst_section_levels[1] * len(chap_title)
               + '\n\n')

        # Set the chapter title to read 'module' for all modules except for the
        # main packages
        if '.' in uri:
            title = 'Module: :mod:`' + uri_short + '`'
        else:
            title = ':mod:`' + uri_short + '`'
        ad += title + '\n' + self.rst_section_levels[2] * len(title)

        if len(classes):
            ad += '\nInheritance diagram for ``%s``:\n\n' % uri
            ad += '.. inheritance-diagram:: %s \n' % uri
            ad += '   :parts: 3\n'

        ad += '\n.. automodule:: ' + uri + '\n'
        ad += '\n.. currentmodule:: ' + uri + '\n'
        multi_class = len(classes) > 1
        multi_fx = len(functions) > 1
        if multi_class:
            ad += '\n' + 'Classes' + '\n' + \
                  self.rst_section_levels[2] * 7 + '\n'
        elif len(classes) and multi_fx:
            ad += '\n' + 'Class' + '\n' + \
                  self.rst_section_levels[2] * 5 + '\n'
        for c in classes:
            ad += '\n:class:`' + c + '`\n' \
                  + self.rst_section_levels[multi_class + 2 ] * \
                  (len(c)+9) + '\n\n'
            ad += '\n.. autoclass:: ' + c + '\n'
            # must NOT exclude from index to keep cross-refs working
            ad += '  :members:\n' \
                  '  :undoc-members:\n' \
                  '  :show-inheritance:\n' \
                  '  :inherited-members:\n' \
                  '\n' \
                  '  .. automethod:: __init__\n'
        if multi_fx:
            ad += '\n' + 'Functions' + '\n' + \
                  self.rst_section_levels[2] * 9 + '\n\n'
        elif len(functions) and multi_class:
            ad += '\n' + 'Function' + '\n' + \
                  self.rst_section_levels[2] * 8 + '\n\n'
        for f in functions:
            # must NOT exclude from index to keep cross-refs working
            ad += '\n.. autofunction:: ' + uri + '.' + f + '\n\n'
        return ad

    def _survives_exclude(self, matchstr, match_type):
        ''' Returns True if *matchstr* does not match patterns

        ``self.package_name`` removed from front of string if present

        Examples
        --------
        >>> dw = ApiDocWriter('sphinx')
        >>> dw._survives_exclude('sphinx.okpkg', 'package')
        True
        >>> dw.package_skip_patterns.append('^\\.badpkg$')
        >>> dw._survives_exclude('sphinx.badpkg', 'package')
        False
        >>> dw._survives_exclude('sphinx.badpkg', 'module')
        True
        >>> dw._survives_exclude('sphinx.badmod', 'module')
        True
        >>> dw.module_skip_patterns.append('^\\.badmod$')
        >>> dw._survives_exclude('sphinx.badmod', 'module')
        False
        '''
        if match_type == 'module':
            patterns = self.module_skip_patterns
        elif match_type == 'package':
            patterns = self.package_skip_patterns
        else:
            raise ValueError('Cannot interpret match type "%s"' 
                             % match_type)
        # Match to URI without package name
        L = len(self.package_name)
        if matchstr[:L] == self.package_name:
            matchstr = matchstr[L:]
        for pat in patterns:
            try:
                pat.search
            except AttributeError:
                pat = re.compile(pat)
            if pat.search(matchstr):
                return False
        return True

    def discover_modules(self):
        ''' Return module sequence discovered from ``self.package_name`` 


        Parameters
        ----------
        None

        Returns
        -------
        mods : sequence
            Sequence of module names within ``self.package_name``

        Examples
        --------
        >>> dw = ApiDocWriter('sphinx')
        >>> mods = dw.discover_modules()
        >>> 'sphinx.util' in mods
        True
        >>> dw.package_skip_patterns.append('\.util$')
        >>> 'sphinx.util' in dw.discover_modules()
        False
        >>> 
        '''
        modules = [self.package_name]
        # raw directory parsing
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Check directory names for packages
            root_uri = self._path2uri(os.path.join(self.root_path,
                                                   dirpath))
            for dirname in dirnames[:]: # copy list - we modify inplace
                package_uri = '.'.join((root_uri, dirname))
                if (self._uri2path(package_uri) and
                    self._survives_exclude(package_uri, 'package')):
                    modules.append(package_uri)
                else:
                    dirnames.remove(dirname)
            # Check filenames for modules
            for filename in filenames:
                module_name = filename[:-3]
                module_uri = '.'.join((root_uri, module_name))
                if (self._uri2path(module_uri) and
                    self._survives_exclude(module_uri, 'module')):
                    modules.append(module_uri)
        return sorted(modules)
    
    def write_modules_api(self, modules,outdir):
        # write the list
        written_modules = []
        for m in modules:
            api_str = self.generate_api_doc(m)
            if not api_str:
                continue
            # write out to file
            outfile = os.path.join(outdir,
                                   m + self.rst_extension)
            fileobj = open(outfile, 'wt')
            fileobj.write(api_str)
            fileobj.close()
            written_modules.append(m)
        self.written_modules = written_modules

    def write_api_docs(self, outdir):
        """Generate API reST files.

        Parameters
        ----------
        outdir : string
            Directory name in which to store files
            We create automatic filenames for each module
            
        Returns
        -------
        None

        Notes
        -----
        Sets self.written_modules to list of written modules
        """
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        # compose list of modules
        modules = self.discover_modules()
        self.write_modules_api(modules,outdir)
        
    def write_index(self, outdir, froot='gen', relative_to=None):
        """Make a reST API index file from written files

        Parameters
        ----------
        path : string
            Filename to write index to
        outdir : string
            Directory to which to write generated index file
        froot : string, optional
            root (filename without extension) of filename to write to
            Defaults to 'gen'.  We add ``self.rst_extension``.
        relative_to : string
            path to which written filenames are relative.  This
            component of the written file path will be removed from
            outdir, in the generated index.  Default is None, meaning,
            leave path as it is.
        """
        if self.written_modules is None:
            raise ValueError('No modules written')
        # Get full filename path
        path = os.path.join(outdir, froot+self.rst_extension)
        # Path written into index is relative to rootpath
        if relative_to is not None:
            relpath = outdir.replace(relative_to + os.path.sep, '')
        else:
            relpath = outdir
        idx = open(path,'wt')
        w = idx.write
        w('.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n')
        w('.. toctree::\n\n')
        for f in self.written_modules:
            w('   %s\n' % os.path.join(relpath,f))
        idx.close()

########NEW FILE########
__FILENAME__ = comment_eater
from cStringIO import StringIO
import compiler
import inspect
import textwrap
import tokenize

from compiler_unparse import unparse


class Comment(object):
    """ A comment block.
    """
    is_comment = True
    def __init__(self, start_lineno, end_lineno, text):
        # int : The first line number in the block. 1-indexed.
        self.start_lineno = start_lineno
        # int : The last line number. Inclusive!
        self.end_lineno = end_lineno
        # str : The text block including '#' character but not any leading spaces.
        self.text = text

    def add(self, string, start, end, line):
        """ Add a new comment line.
        """
        self.start_lineno = min(self.start_lineno, start[0])
        self.end_lineno = max(self.end_lineno, end[0])
        self.text += string

    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.start_lineno,
            self.end_lineno, self.text)


class NonComment(object):
    """ A non-comment block of code.
    """
    is_comment = False
    def __init__(self, start_lineno, end_lineno):
        self.start_lineno = start_lineno
        self.end_lineno = end_lineno

    def add(self, string, start, end, line):
        """ Add lines to the block.
        """
        if string.strip():
            # Only add if not entirely whitespace.
            self.start_lineno = min(self.start_lineno, start[0])
            self.end_lineno = max(self.end_lineno, end[0])

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.start_lineno,
            self.end_lineno)


class CommentBlocker(object):
    """ Pull out contiguous comment blocks.
    """
    def __init__(self):
        # Start with a dummy.
        self.current_block = NonComment(0, 0)

        # All of the blocks seen so far.
        self.blocks = []

        # The index mapping lines of code to their associated comment blocks.
        self.index = {}

    def process_file(self, file):
        """ Process a file object.
        """
        for token in tokenize.generate_tokens(file.next):
            self.process_token(*token)
        self.make_index()

    def process_token(self, kind, string, start, end, line):
        """ Process a single token.
        """
        if self.current_block.is_comment:
            if kind == tokenize.COMMENT:
                self.current_block.add(string, start, end, line)
            else:
                self.new_noncomment(start[0], end[0])
        else:
            if kind == tokenize.COMMENT:
                self.new_comment(string, start, end, line)
            else:
                self.current_block.add(string, start, end, line)

    def new_noncomment(self, start_lineno, end_lineno):
        """ We are transitioning from a noncomment to a comment.
        """
        block = NonComment(start_lineno, end_lineno)
        self.blocks.append(block)
        self.current_block = block

    def new_comment(self, string, start, end, line):
        """ Possibly add a new comment.
        
        Only adds a new comment if this comment is the only thing on the line.
        Otherwise, it extends the noncomment block.
        """
        prefix = line[:start[1]]
        if prefix.strip():
            # Oops! Trailing comment, not a comment block.
            self.current_block.add(string, start, end, line)
        else:
            # A comment block.
            block = Comment(start[0], end[0], string)
            self.blocks.append(block)
            self.current_block = block

    def make_index(self):
        """ Make the index mapping lines of actual code to their associated
        prefix comments.
        """
        for prev, block in zip(self.blocks[:-1], self.blocks[1:]):
            if not block.is_comment:
                self.index[block.start_lineno] = prev

    def search_for_comment(self, lineno, default=None):
        """ Find the comment block just before the given line number.

        Returns None (or the specified default) if there is no such block.
        """
        if not self.index:
            self.make_index()
        block = self.index.get(lineno, None)
        text = getattr(block, 'text', default)
        return text


def strip_comment_marker(text):
    """ Strip # markers at the front of a block of comment text.
    """
    lines = []
    for line in text.splitlines():
        lines.append(line.lstrip('#'))
    text = textwrap.dedent('\n'.join(lines))
    return text


def get_class_traits(klass):
    """ Yield all of the documentation for trait definitions on a class object.
    """
    # FIXME: gracefully handle errors here or in the caller?
    source = inspect.getsource(klass)
    cb = CommentBlocker()
    cb.process_file(StringIO(source))
    mod_ast = compiler.parse(source)
    class_ast = mod_ast.node.nodes[0]
    for node in class_ast.code.nodes:
        # FIXME: handle other kinds of assignments?
        if isinstance(node, compiler.ast.Assign):
            name = node.nodes[0].name
            rhs = unparse(node.expr).strip()
            doc = strip_comment_marker(cb.search_for_comment(node.lineno, default=''))
            yield name, rhs, doc


########NEW FILE########
__FILENAME__ = compiler_unparse
""" Turn compiler.ast structures back into executable python code.

    The unparse method takes a compiler.ast tree and transforms it back into
    valid python code.  It is incomplete and currently only works for
    import statements, function calls, function definitions, assignments, and
    basic expressions.

    Inspired by python-2.5-svn/Demo/parser/unparse.py

    fixme: We may want to move to using _ast trees because the compiler for
           them is about 6 times faster than compiler.compile.
"""

import sys
import cStringIO
from compiler.ast import Const, Name, Tuple, Div, Mul, Sub, Add

def unparse(ast, single_line_functions=False):
    s = cStringIO.StringIO()
    UnparseCompilerAst(ast, s, single_line_functions)
    return s.getvalue().lstrip()

op_precedence = { 'compiler.ast.Power':3, 'compiler.ast.Mul':2, 'compiler.ast.Div':2,
                  'compiler.ast.Add':1, 'compiler.ast.Sub':1 }

class UnparseCompilerAst:
    """ Methods in this class recursively traverse an AST and
        output source code for the abstract syntax; original formatting
        is disregarged.
    """

    #########################################################################
    # object interface.
    #########################################################################

    def __init__(self, tree, file = sys.stdout, single_line_functions=False):
        """ Unparser(tree, file=sys.stdout) -> None.

            Print the source for tree to file.
        """
        self.f = file
        self._single_func = single_line_functions
        self._do_indent = True
        self._indent = 0
        self._dispatch(tree)
        self._write("\n")
        self.f.flush()

    #########################################################################
    # Unparser private interface.
    #########################################################################

    ### format, output, and dispatch methods ################################

    def _fill(self, text = ""):
        "Indent a piece of text, according to the current indentation level"
        if self._do_indent:
            self._write("\n"+"    "*self._indent + text)
        else:
            self._write(text)

    def _write(self, text):
        "Append a piece of text to the current line."
        self.f.write(text)

    def _enter(self):
        "Print ':', and increase the indentation."
        self._write(": ")
        self._indent += 1

    def _leave(self):
        "Decrease the indentation level."
        self._indent -= 1

    def _dispatch(self, tree):
        "_dispatcher function, _dispatching tree type T to method _T."
        if isinstance(tree, list):
            for t in tree:
                self._dispatch(t)
            return
        meth = getattr(self, "_"+tree.__class__.__name__)
        if tree.__class__.__name__ == 'NoneType' and not self._do_indent:
            return
        meth(tree)


    #########################################################################
    # compiler.ast unparsing methods.
    #
    # There should be one method per concrete grammar type. They are
    # organized in alphabetical order.
    #########################################################################

    def _Add(self, t):
        self.__binary_op(t, '+')

    def _And(self, t):
        self._write(" (")
        for i, node in enumerate(t.nodes):
            self._dispatch(node)
            if i != len(t.nodes)-1:
                self._write(") and (")
        self._write(")")
               
    def _AssAttr(self, t):
        """ Handle assigning an attribute of an object
        """
        self._dispatch(t.expr)
        self._write('.'+t.attrname)
 
    def _Assign(self, t):
        """ Expression Assignment such as "a = 1".

            This only handles assignment in expressions.  Keyword assignment
            is handled separately.
        """
        self._fill()
        for target in t.nodes:
            self._dispatch(target)
            self._write(" = ")
        self._dispatch(t.expr)
        if not self._do_indent:
            self._write('; ')

    def _AssName(self, t):
        """ Name on left hand side of expression.

            Treat just like a name on the right side of an expression.
        """
        self._Name(t)

    def _AssTuple(self, t):
        """ Tuple on left hand side of an expression.
        """

        # _write each elements, separated by a comma.
        for element in t.nodes[:-1]:
            self._dispatch(element)
            self._write(", ")

        # Handle the last one without writing comma
        last_element = t.nodes[-1]
        self._dispatch(last_element)

    def _AugAssign(self, t):
        """ +=,-=,*=,/=,**=, etc. operations
        """
        
        self._fill()
        self._dispatch(t.node)
        self._write(' '+t.op+' ')
        self._dispatch(t.expr)
        if not self._do_indent:
            self._write(';')
            
    def _Bitand(self, t):
        """ Bit and operation.
        """
        
        for i, node in enumerate(t.nodes):
            self._write("(")
            self._dispatch(node)
            self._write(")")
            if i != len(t.nodes)-1:
                self._write(" & ")
                
    def _Bitor(self, t):
        """ Bit or operation
        """
        
        for i, node in enumerate(t.nodes):
            self._write("(")
            self._dispatch(node)
            self._write(")")
            if i != len(t.nodes)-1:
                self._write(" | ")
                
    def _CallFunc(self, t):
        """ Function call.
        """
        self._dispatch(t.node)
        self._write("(")
        comma = False
        for e in t.args:
            if comma: self._write(", ")
            else: comma = True
            self._dispatch(e)
        if t.star_args:
            if comma: self._write(", ")
            else: comma = True
            self._write("*")
            self._dispatch(t.star_args)
        if t.dstar_args:
            if comma: self._write(", ")
            else: comma = True
            self._write("**")
            self._dispatch(t.dstar_args)
        self._write(")")

    def _Compare(self, t):
        self._dispatch(t.expr)
        for op, expr in t.ops:
            self._write(" " + op + " ")
            self._dispatch(expr)

    def _Const(self, t):
        """ A constant value such as an integer value, 3, or a string, "hello".
        """
        self._dispatch(t.value)

    def _Decorators(self, t):
        """ Handle function decorators (eg. @has_units)
        """
        for node in t.nodes:
            self._dispatch(node)

    def _Dict(self, t):
        self._write("{")
        for  i, (k, v) in enumerate(t.items):
            self._dispatch(k)
            self._write(": ")
            self._dispatch(v)
            if i < len(t.items)-1:
                self._write(", ")
        self._write("}")

    def _Discard(self, t):
        """ Node for when return value is ignored such as in "foo(a)".
        """
        self._fill()
        self._dispatch(t.expr)

    def _Div(self, t):
        self.__binary_op(t, '/')

    def _Ellipsis(self, t):
        self._write("...")

    def _From(self, t):
        """ Handle "from xyz import foo, bar as baz".
        """
        # fixme: Are From and ImportFrom handled differently?
        self._fill("from ")
        self._write(t.modname)
        self._write(" import ")
        for i, (name,asname) in enumerate(t.names):
            if i != 0:
                self._write(", ")
            self._write(name)
            if asname is not None:
                self._write(" as "+asname)
                
    def _Function(self, t):
        """ Handle function definitions
        """
        if t.decorators is not None:
            self._fill("@")
            self._dispatch(t.decorators)
        self._fill("def "+t.name + "(")
        defaults = [None] * (len(t.argnames) - len(t.defaults)) + list(t.defaults)
        for i, arg in enumerate(zip(t.argnames, defaults)):
            self._write(arg[0])
            if arg[1] is not None:
                self._write('=')
                self._dispatch(arg[1])
            if i < len(t.argnames)-1:
                self._write(', ')
        self._write(")")
        if self._single_func:
            self._do_indent = False
        self._enter()
        self._dispatch(t.code)
        self._leave()
        self._do_indent = True

    def _Getattr(self, t):
        """ Handle getting an attribute of an object
        """
        if isinstance(t.expr, (Div, Mul, Sub, Add)):
            self._write('(')
            self._dispatch(t.expr)
            self._write(')')
        else:
            self._dispatch(t.expr)
            
        self._write('.'+t.attrname)
        
    def _If(self, t):
        self._fill()
        
        for i, (compare,code) in enumerate(t.tests):
            if i == 0:
                self._write("if ")
            else:
                self._write("elif ")
            self._dispatch(compare)
            self._enter()
            self._fill()
            self._dispatch(code)
            self._leave()
            self._write("\n")

        if t.else_ is not None:
            self._write("else")
            self._enter()
            self._fill()
            self._dispatch(t.else_)
            self._leave()
            self._write("\n")
            
    def _IfExp(self, t):
        self._dispatch(t.then)
        self._write(" if ")
        self._dispatch(t.test)

        if t.else_ is not None:
            self._write(" else (")
            self._dispatch(t.else_)
            self._write(")")

    def _Import(self, t):
        """ Handle "import xyz.foo".
        """
        self._fill("import ")
        
        for i, (name,asname) in enumerate(t.names):
            if i != 0:
                self._write(", ")
            self._write(name)
            if asname is not None:
                self._write(" as "+asname)

    def _Keyword(self, t):
        """ Keyword value assignment within function calls and definitions.
        """
        self._write(t.name)
        self._write("=")
        self._dispatch(t.expr)
        
    def _List(self, t):
        self._write("[")
        for  i,node in enumerate(t.nodes):
            self._dispatch(node)
            if i < len(t.nodes)-1:
                self._write(", ")
        self._write("]")

    def _Module(self, t):
        if t.doc is not None:
            self._dispatch(t.doc)
        self._dispatch(t.node)

    def _Mul(self, t):
        self.__binary_op(t, '*')

    def _Name(self, t):
        self._write(t.name)

    def _NoneType(self, t):
        self._write("None")
        
    def _Not(self, t):
        self._write('not (')
        self._dispatch(t.expr)
        self._write(')')
        
    def _Or(self, t):
        self._write(" (")
        for i, node in enumerate(t.nodes):
            self._dispatch(node)
            if i != len(t.nodes)-1:
                self._write(") or (")
        self._write(")")
                
    def _Pass(self, t):
        self._write("pass\n")

    def _Printnl(self, t):
        self._fill("print ")
        if t.dest:
            self._write(">> ")
            self._dispatch(t.dest)
            self._write(", ")
        comma = False
        for node in t.nodes:
            if comma: self._write(', ')
            else: comma = True
            self._dispatch(node)

    def _Power(self, t):
        self.__binary_op(t, '**')

    def _Return(self, t):
        self._fill("return ")
        if t.value:
            if isinstance(t.value, Tuple):
                text = ', '.join([ name.name for name in t.value.asList() ])
                self._write(text)
            else:
                self._dispatch(t.value)
            if not self._do_indent:
                self._write('; ')

    def _Slice(self, t):
        self._dispatch(t.expr)
        self._write("[")
        if t.lower:
            self._dispatch(t.lower)
        self._write(":")
        if t.upper:
            self._dispatch(t.upper)
        #if t.step:
        #    self._write(":")
        #    self._dispatch(t.step)
        self._write("]")

    def _Sliceobj(self, t):
        for i, node in enumerate(t.nodes):
            if i != 0:
                self._write(":")
            if not (isinstance(node, Const) and node.value is None):
                self._dispatch(node)

    def _Stmt(self, tree):
        for node in tree.nodes:
            self._dispatch(node)

    def _Sub(self, t):
        self.__binary_op(t, '-')

    def _Subscript(self, t):
        self._dispatch(t.expr)
        self._write("[")
        for i, value in enumerate(t.subs):
            if i != 0:
                self._write(",")
            self._dispatch(value)
        self._write("]")

    def _TryExcept(self, t):
        self._fill("try")
        self._enter()
        self._dispatch(t.body)
        self._leave()

        for handler in t.handlers:
            self._fill('except ')
            self._dispatch(handler[0])
            if handler[1] is not None:
                self._write(', ')
                self._dispatch(handler[1])
            self._enter()
            self._dispatch(handler[2])
            self._leave()
            
        if t.else_:
            self._fill("else")
            self._enter()
            self._dispatch(t.else_)
            self._leave()

    def _Tuple(self, t):

        if not t.nodes:
            # Empty tuple.
            self._write("()")
        else:
            self._write("(")

            # _write each elements, separated by a comma.
            for element in t.nodes[:-1]:
                self._dispatch(element)
                self._write(", ")

            # Handle the last one without writing comma
            last_element = t.nodes[-1]
            self._dispatch(last_element)

            self._write(")")
            
    def _UnaryAdd(self, t):
        self._write("+")
        self._dispatch(t.expr)
        
    def _UnarySub(self, t):
        self._write("-")
        self._dispatch(t.expr)        

    def _With(self, t):
        self._fill('with ')
        self._dispatch(t.expr)
        if t.vars:
            self._write(' as ')
            self._dispatch(t.vars.name)
        self._enter()
        self._dispatch(t.body)
        self._leave()
        self._write('\n')
        
    def _int(self, t):
        self._write(repr(t))

    def __binary_op(self, t, symbol):
        # Check if parenthesis are needed on left side and then dispatch
        has_paren = False
        left_class = str(t.left.__class__)
        if (left_class in op_precedence.keys() and
            op_precedence[left_class] < op_precedence[str(t.__class__)]):
            has_paren = True
        if has_paren:
            self._write('(')
        self._dispatch(t.left)
        if has_paren:
            self._write(')')
        # Write the appropriate symbol for operator
        self._write(symbol)
        # Check if parenthesis are needed on the right side and then dispatch
        has_paren = False
        right_class = str(t.right.__class__)
        if (right_class in op_precedence.keys() and
            op_precedence[right_class] < op_precedence[str(t.__class__)]):
            has_paren = True
        if has_paren:
            self._write('(')
        self._dispatch(t.right)
        if has_paren:
            self._write(')')

    def _float(self, t):
        # if t is 0.1, str(t)->'0.1' while repr(t)->'0.1000000000001'
        # We prefer str here.
        self._write(str(t))

    def _str(self, t):
        self._write(repr(t))
        
    def _tuple(self, t):
        self._write(str(t))

    #########################################################################
    # These are the methods from the _ast modules unparse.
    #
    # As our needs to handle more advanced code increase, we may want to
    # modify some of the methods below so that they work for compiler.ast.
    #########################################################################

#    # stmt
#    def _Expr(self, tree):
#        self._fill()
#        self._dispatch(tree.value)
#
#    def _Import(self, t):
#        self._fill("import ")
#        first = True
#        for a in t.names:
#            if first:
#                first = False
#            else:
#                self._write(", ")
#            self._write(a.name)
#            if a.asname:
#                self._write(" as "+a.asname)
#
##    def _ImportFrom(self, t):
##        self._fill("from ")
##        self._write(t.module)
##        self._write(" import ")
##        for i, a in enumerate(t.names):
##            if i == 0:
##                self._write(", ")
##            self._write(a.name)
##            if a.asname:
##                self._write(" as "+a.asname)
##        # XXX(jpe) what is level for?
##
#
#    def _Break(self, t):
#        self._fill("break")
#
#    def _Continue(self, t):
#        self._fill("continue")
#
#    def _Delete(self, t):
#        self._fill("del ")
#        self._dispatch(t.targets)
#
#    def _Assert(self, t):
#        self._fill("assert ")
#        self._dispatch(t.test)
#        if t.msg:
#            self._write(", ")
#            self._dispatch(t.msg)
#
#    def _Exec(self, t):
#        self._fill("exec ")
#        self._dispatch(t.body)
#        if t.globals:
#            self._write(" in ")
#            self._dispatch(t.globals)
#        if t.locals:
#            self._write(", ")
#            self._dispatch(t.locals)
#
#    def _Print(self, t):
#        self._fill("print ")
#        do_comma = False
#        if t.dest:
#            self._write(">>")
#            self._dispatch(t.dest)
#            do_comma = True
#        for e in t.values:
#            if do_comma:self._write(", ")
#            else:do_comma=True
#            self._dispatch(e)
#        if not t.nl:
#            self._write(",")
#
#    def _Global(self, t):
#        self._fill("global")
#        for i, n in enumerate(t.names):
#            if i != 0:
#                self._write(",")
#            self._write(" " + n)
#
#    def _Yield(self, t):
#        self._fill("yield")
#        if t.value:
#            self._write(" (")
#            self._dispatch(t.value)
#            self._write(")")
#
#    def _Raise(self, t):
#        self._fill('raise ')
#        if t.type:
#            self._dispatch(t.type)
#        if t.inst:
#            self._write(", ")
#            self._dispatch(t.inst)
#        if t.tback:
#            self._write(", ")
#            self._dispatch(t.tback)
#
#
#    def _TryFinally(self, t):
#        self._fill("try")
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#        self._fill("finally")
#        self._enter()
#        self._dispatch(t.finalbody)
#        self._leave()
#
#    def _excepthandler(self, t):
#        self._fill("except ")
#        if t.type:
#            self._dispatch(t.type)
#        if t.name:
#            self._write(", ")
#            self._dispatch(t.name)
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#    def _ClassDef(self, t):
#        self._write("\n")
#        self._fill("class "+t.name)
#        if t.bases:
#            self._write("(")
#            for a in t.bases:
#                self._dispatch(a)
#                self._write(", ")
#            self._write(")")
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#    def _FunctionDef(self, t):
#        self._write("\n")
#        for deco in t.decorators:
#            self._fill("@")
#            self._dispatch(deco)
#        self._fill("def "+t.name + "(")
#        self._dispatch(t.args)
#        self._write(")")
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#    def _For(self, t):
#        self._fill("for ")
#        self._dispatch(t.target)
#        self._write(" in ")
#        self._dispatch(t.iter)
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#        if t.orelse:
#            self._fill("else")
#            self._enter()
#            self._dispatch(t.orelse)
#            self._leave
#
#    def _While(self, t):
#        self._fill("while ")
#        self._dispatch(t.test)
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#        if t.orelse:
#            self._fill("else")
#            self._enter()
#            self._dispatch(t.orelse)
#            self._leave
#
#    # expr
#    def _Str(self, tree):
#        self._write(repr(tree.s))
##
#    def _Repr(self, t):
#        self._write("`")
#        self._dispatch(t.value)
#        self._write("`")
#
#    def _Num(self, t):
#        self._write(repr(t.n))
#
#    def _ListComp(self, t):
#        self._write("[")
#        self._dispatch(t.elt)
#        for gen in t.generators:
#            self._dispatch(gen)
#        self._write("]")
#
#    def _GeneratorExp(self, t):
#        self._write("(")
#        self._dispatch(t.elt)
#        for gen in t.generators:
#            self._dispatch(gen)
#        self._write(")")
#
#    def _comprehension(self, t):
#        self._write(" for ")
#        self._dispatch(t.target)
#        self._write(" in ")
#        self._dispatch(t.iter)
#        for if_clause in t.ifs:
#            self._write(" if ")
#            self._dispatch(if_clause)
#
#    def _IfExp(self, t):
#        self._dispatch(t.body)
#        self._write(" if ")
#        self._dispatch(t.test)
#        if t.orelse:
#            self._write(" else ")
#            self._dispatch(t.orelse)
#
#    unop = {"Invert":"~", "Not": "not", "UAdd":"+", "USub":"-"}
#    def _UnaryOp(self, t):
#        self._write(self.unop[t.op.__class__.__name__])
#        self._write("(")
#        self._dispatch(t.operand)
#        self._write(")")
#
#    binop = { "Add":"+", "Sub":"-", "Mult":"*", "Div":"/", "Mod":"%",
#                    "LShift":">>", "RShift":"<<", "BitOr":"|", "BitXor":"^", "BitAnd":"&",
#                    "FloorDiv":"//", "Pow": "**"}
#    def _BinOp(self, t):
#        self._write("(")
#        self._dispatch(t.left)
#        self._write(")" + self.binop[t.op.__class__.__name__] + "(")
#        self._dispatch(t.right)
#        self._write(")")
#
#    boolops = {_ast.And: 'and', _ast.Or: 'or'}
#    def _BoolOp(self, t):
#        self._write("(")
#        self._dispatch(t.values[0])
#        for v in t.values[1:]:
#            self._write(" %s " % self.boolops[t.op.__class__])
#            self._dispatch(v)
#        self._write(")")
#
#    def _Attribute(self,t):
#        self._dispatch(t.value)
#        self._write(".")
#        self._write(t.attr)
#
##    def _Call(self, t):
##        self._dispatch(t.func)
##        self._write("(")
##        comma = False
##        for e in t.args:
##            if comma: self._write(", ")
##            else: comma = True
##            self._dispatch(e)
##        for e in t.keywords:
##            if comma: self._write(", ")
##            else: comma = True
##            self._dispatch(e)
##        if t.starargs:
##            if comma: self._write(", ")
##            else: comma = True
##            self._write("*")
##            self._dispatch(t.starargs)
##        if t.kwargs:
##            if comma: self._write(", ")
##            else: comma = True
##            self._write("**")
##            self._dispatch(t.kwargs)
##        self._write(")")
#
#    # slice
#    def _Index(self, t):
#        self._dispatch(t.value)
#
#    def _ExtSlice(self, t):
#        for i, d in enumerate(t.dims):
#            if i != 0:
#                self._write(': ')
#            self._dispatch(d)
#
#    # others
#    def _arguments(self, t):
#        first = True
#        nonDef = len(t.args)-len(t.defaults)
#        for a in t.args[0:nonDef]:
#            if first:first = False
#            else: self._write(", ")
#            self._dispatch(a)
#        for a,d in zip(t.args[nonDef:], t.defaults):
#            if first:first = False
#            else: self._write(", ")
#            self._dispatch(a),
#            self._write("=")
#            self._dispatch(d)
#        if t.vararg:
#            if first:first = False
#            else: self._write(", ")
#            self._write("*"+t.vararg)
#        if t.kwarg:
#            if first:first = False
#            else: self._write(", ")
#            self._write("**"+t.kwarg)
#
##    def _keyword(self, t):
##        self._write(t.arg)
##        self._write("=")
##        self._dispatch(t.value)
#
#    def _Lambda(self, t):
#        self._write("lambda ")
#        self._dispatch(t.args)
#        self._write(": ")
#        self._dispatch(t.body)




########NEW FILE########
__FILENAME__ = docscrape
"""Extract reference documentation from the NumPy source tree.

"""

import inspect
import textwrap
import re
import pydoc
from StringIO import StringIO
from warnings import warn

class Reader(object):
    """A line-based string reader.

    """
    def __init__(self, data):
        """
        Parameters
        ----------
        data : str
           String with lines separated by '\n'.

        """
        if isinstance(data,list):
            self._str = data
        else:
            self._str = data.split('\n') # store string as list of lines

        self.reset()

    def __getitem__(self, n):
        return self._str[n]

    def reset(self):
        self._l = 0 # current line nr

    def read(self):
        if not self.eof():
            out = self[self._l]
            self._l += 1
            return out
        else:
            return ''

    def seek_next_non_empty_line(self):
        for l in self[self._l:]:
            if l.strip():
                break
            else:
                self._l += 1

    def eof(self):
        return self._l >= len(self._str)

    def read_to_condition(self, condition_func):
        start = self._l
        for line in self[start:]:
            if condition_func(line):
                return self[start:self._l]
            self._l += 1
            if self.eof():
                return self[start:self._l+1]
        return []

    def read_to_next_empty_line(self):
        self.seek_next_non_empty_line()
        def is_empty(line):
            return not line.strip()
        return self.read_to_condition(is_empty)

    def read_to_next_unindented_line(self):
        def is_unindented(line):
            return (line.strip() and (len(line.lstrip()) == len(line)))
        return self.read_to_condition(is_unindented)

    def peek(self,n=0):
        if self._l + n < len(self._str):
            return self[self._l + n]
        else:
            return ''

    def is_empty(self):
        return not ''.join(self._str).strip()


class NumpyDocString(object):
    def __init__(self, docstring, config={}):
        docstring = textwrap.dedent(docstring).split('\n')

        self._doc = Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': [''],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Attributes': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'Warnings': [],
            'References': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def __getitem__(self,key):
        return self._parsed_data[key]

    def __setitem__(self,key,val):
        if not self._parsed_data.has_key(key):
            warn("Unknown section %s" % key)
        else:
            self._parsed_data[key] = val

    def _is_at_section(self):
        self._doc.seek_next_non_empty_line()

        if self._doc.eof():
            return False

        l1 = self._doc.peek().strip()  # e.g. Parameters

        if l1.startswith('.. index::'):
            return True

        l2 = self._doc.peek(1).strip() #    ---------- or ==========
        return l2.startswith('-'*len(l1)) or l2.startswith('='*len(l1))

    def _strip(self,doc):
        i = 0
        j = 0
        for i,line in enumerate(doc):
            if line.strip(): break

        for j,line in enumerate(doc[::-1]):
            if line.strip(): break

        return doc[i:len(doc)-j]

    def _read_to_next_section(self):
        section = self._doc.read_to_next_empty_line()

        while not self._is_at_section() and not self._doc.eof():
            if not self._doc.peek(-1).strip(): # previous line was empty
                section += ['']

            section += self._doc.read_to_next_empty_line()

        return section

    def _read_sections(self):
        while not self._doc.eof():
            data = self._read_to_next_section()
            name = data[0].strip()

            if name.startswith('..'): # index section
                yield name, data[1:]
            elif len(data) < 2:
                yield StopIteration
            else:
                yield name, self._strip(data[2:])

    def _parse_param_list(self,content):
        r = Reader(content)
        params = []
        while not r.eof():
            header = r.read().strip()
            if ' : ' in header:
                arg_name, arg_type = header.split(' : ')[:2]
            else:
                arg_name, arg_type = header, ''

            desc = r.read_to_next_unindented_line()
            desc = dedent_lines(desc)

            params.append((arg_name,arg_type,desc))

        return params


    _name_rgx = re.compile(r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>[a-zA-Z0-9_.-]+))\s*", re.X)
    def _parse_see_also(self, content):
        """
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3

        """
        items = []

        def parse_item_name(text):
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name, rest):
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []

        for line in content:
            if not line.strip(): continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        if func.strip():
                            push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)
        return items

    def _parse_index(self, section, content):
        """
        .. index: default
           :refguide: something, else, and more

        """
        def strip_each_in(lst):
            return [s.strip() for s in lst]

        out = {}
        section = section.split('::')
        if len(section) > 1:
            out['default'] = strip_each_in(section[1].split(','))[0]
        for line in content:
            line = line.split(':')
            if len(line) > 2:
                out[line[1]] = strip_each_in(line[2].split(','))
        return out

    def _parse_summary(self):
        """Grab signature (if given) and summary"""
        if self._is_at_section():
            return

        summary = self._doc.read_to_next_empty_line()
        summary_str = " ".join([s.strip() for s in summary]).strip()
        if re.compile('^([\w., ]+=)?\s*[\w\.]+\(.*\)$').match(summary_str):
            self['Signature'] = summary_str
            if not self._is_at_section():
                self['Summary'] = self._doc.read_to_next_empty_line()
        else:
            self['Summary'] = summary

        if not self._is_at_section():
            self['Extended Summary'] = self._read_to_next_section()

    def _parse(self):
        self._doc.reset()
        self._parse_summary()

        for (section,content) in self._read_sections():
            if not section.startswith('..'):
                section = ' '.join([s.capitalize() for s in section.split(' ')])
            if section in ('Parameters', 'Returns', 'Raises', 'Warns',
                           'Other Parameters', 'Attributes', 'Methods'):
                self[section] = self._parse_param_list(content)
            elif section.startswith('.. index::'):
                self['index'] = self._parse_index(section, content)
            elif section == 'See Also':
                self['See Also'] = self._parse_see_also(content)
            else:
                self[section] = content

    # string conversion routines

    def _str_header(self, name, symbol='-'):
        return [name, len(name)*symbol]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        if self['Signature']:
            return [self['Signature'].replace('*','\*')] + ['']
        else:
            return ['']

    def _str_summary(self):
        if self['Summary']:
            return self['Summary'] + ['']
        else:
            return []

    def _str_extended_summary(self):
        if self['Extended Summary']:
            return self['Extended Summary'] + ['']
        else:
            return []

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            for param,param_type,desc in self[name]:
                out += ['%s : %s' % (param, param_type)]
                out += self._str_indent(desc)
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += self[name]
            out += ['']
        return out

    def _str_see_also(self, func_role):
        if not self['See Also']: return []
        out = []
        out += self._str_header("See Also")
        last_had_desc = True
        for func, desc, role in self['See Also']:
            if role:
                link = ':%s:`%s`' % (role, func)
            elif func_role:
                link = ':%s:`%s`' % (func_role, func)
            else:
                link = "`%s`_" % func
            if desc or last_had_desc:
                out += ['']
                out += [link]
            else:
                out[-1] += ", %s" % link
            if desc:
                out += self._str_indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self, func_role=''):
        out = []
        out += self._str_signature()
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Other Parameters',
                           'Raises', 'Warns'):
            out += self._str_param_list(param_list)
        out += self._str_section('Warnings')
        out += self._str_see_also(func_role)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
        for param_list in ('Attributes', 'Methods'):
            out += self._str_param_list(param_list)
        out += self._str_index()
        return '\n'.join(out)


def indent(str,indent=4):
    indent_str = ' '*indent
    if str is None:
        return indent_str
    lines = str.split('\n')
    return '\n'.join(indent_str + l for l in lines)

def dedent_lines(lines):
    """Deindent a list of lines maximally"""
    return textwrap.dedent("\n".join(lines)).split("\n")

def header(text, style='-'):
    return text + '\n' + style*len(text) + '\n'


class FunctionDoc(NumpyDocString):
    def __init__(self, func, role='func', doc=None, config={}):
        self._f = func
        self._role = role # e.g. "func" or "meth"

        if doc is None:
            if func is None:
                raise ValueError("No function or docstring given")
            doc = inspect.getdoc(func) or ''
        NumpyDocString.__init__(self, doc)

        if not self['Signature'] and func is not None:
            func, func_name = self.get_func()
            try:
                # try to read signature
                argspec = inspect.getargspec(func)
                argspec = inspect.formatargspec(*argspec)
                argspec = argspec.replace('*','\*')
                signature = '%s%s' % (func_name, argspec)
            except TypeError, e:
                signature = '%s()' % func_name
            self['Signature'] = signature

    def get_func(self):
        func_name = getattr(self._f, '__name__', self.__class__.__name__)
        if inspect.isclass(self._f):
            func = getattr(self._f, '__call__', self._f.__init__)
        else:
            func = self._f
        return func, func_name

    def __str__(self):
        out = ''

        func, func_name = self.get_func()
        signature = self['Signature'].replace('*', '\*')

        roles = {'func': 'function',
                 'meth': 'method'}

        if self._role:
            if not roles.has_key(self._role):
                print "Warning: invalid role %s" % self._role
            out += '.. %s:: %s\n    \n\n' % (roles.get(self._role,''),
                                             func_name)

        out += super(FunctionDoc, self).__str__(func_role=self._role)
        return out


class ClassDoc(NumpyDocString):
    def __init__(self, cls, doc=None, modulename='', func_doc=FunctionDoc,
                 config={}):
        if not inspect.isclass(cls) and cls is not None:
            raise ValueError("Expected a class or None, but got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename

        if doc is None:
            if cls is None:
                raise ValueError("No class or documentation string given")
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

        if config.get('show_class_members', True):
            if not self['Methods']:
                self['Methods'] = [(name, '', '')
                                   for name in sorted(self.methods)]
            if not self['Attributes']:
                self['Attributes'] = [(name, '', '')
                                      for name in sorted(self.properties)]

    @property
    def methods(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and callable(func)]

    @property
    def properties(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and func is None]

########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
import sphinx
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
    def __init__(self, docstring, config={}):
        self.use_plots = config.get('use_plots', False)
        NumpyDocString.__init__(self, docstring, config=config)

    # string conversion routines
    def _str_header(self, name, symbol='`'):
        return ['.. rubric:: ' + name, '']

    def _str_field_list(self, name):
        return [':' + name + ':']

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return ['']
        if self['Signature']:
            return ['``%s``' % self['Signature']] + ['']
        else:
            return ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_field_list(name)
            out += ['']
            for param,param_type,desc in self[name]:
                out += self._str_indent(['**%s** : %s' % (param.strip(),
                                                          param_type)])
                out += ['']
                out += self._str_indent(desc,8)
                out += ['']
        return out

    @property
    def _obj(self):
        if hasattr(self, '_cls'):
            return self._cls
        elif hasattr(self, '_f'):
            return self._f
        return None

    def _str_member_list(self, name):
        """
        Generate a member listing, autosummary:: table where possible,
        and a table where not.

        """
        out = []
        if self[name]:
            out += ['.. rubric:: %s' % name, '']
            prefix = getattr(self, '_name', '')

            if prefix:
                prefix = '~%s.' % prefix

            autosum = []
            others = []
            for param, param_type, desc in self[name]:
                param = param.strip()
                if not self._obj or hasattr(self._obj, param):
                    autosum += ["   %s%s" % (prefix, param)]
                else:
                    others.append((param, param_type, desc))

            if autosum:
                out += ['.. autosummary::', '   :toctree:', '']
                out += autosum

            if others:
                maxlen_0 = max([len(x[0]) for x in others])
                maxlen_1 = max([len(x[1]) for x in others])
                hdr = "="*maxlen_0 + "  " + "="*maxlen_1 + "  " + "="*10
                fmt = '%%%ds  %%%ds  ' % (maxlen_0, maxlen_1)
                n_indent = maxlen_0 + maxlen_1 + 4
                out += [hdr]
                for param, param_type, desc in others:
                    out += [fmt % (param.strip(), param_type)]
                    out += self._str_indent(desc, n_indent)
                out += [hdr]
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            content = textwrap.dedent("\n".join(self[name])).split("\n")
            out += content
            out += ['']
        return out

    def _str_see_also(self, func_role):
        out = []
        if self['See Also']:
            see_also = super(SphinxDocString, self)._str_see_also(func_role)
            out = ['.. seealso::', '']
            out += self._str_indent(see_also[2:])
        return out

    def _str_warnings(self):
        out = []
        if self['Warnings']:
            out = ['.. warning::', '']
            out += self._str_indent(self['Warnings'])
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        if len(idx) == 0:
            return out

        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            elif section == 'refguide':
                out += ['   single: %s' % (', '.join(references))]
            else:
                out += ['   %s: %s' % (section, ','.join(references))]
        return out

    def _str_references(self):
        out = []
        if self['References']:
            out += self._str_header('References')
            if isinstance(self['References'], str):
                self['References'] = [self['References']]
            out.extend(self['References'])
            out += ['']
            # Latex collects all references to a separate bibliography,
            # so we need to insert links to it
            if sphinx.__version__ >= "0.6":
                out += ['.. only:: latex','']
            else:
                out += ['.. latexonly::','']
            items = []
            for line in self['References']:
                m = re.match(r'.. \[([a-z0-9._-]+)\]', line, re.I)
                if m:
                    items.append(m.group(1))
            out += ['   ' + ", ".join(["[%s]_" % item for item in items]), '']
        return out

    def _str_examples(self):
        examples_str = "\n".join(self['Examples'])

        if (self.use_plots and 'import matplotlib' in examples_str
                and 'plot::' not in examples_str):
            out = []
            out += self._str_header('Examples')
            out += ['.. plot::', '']
            out += self._str_indent(self['Examples'])
            out += ['']
            return out
        else:
            return self._str_section('Examples')

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Other Parameters',
                           'Raises', 'Warns'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_examples()
        #for param_list in ('Attributes', 'Methods'):
        #    out += self._str_member_list(param_list)
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    def __init__(self, obj, doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        FunctionDoc.__init__(self, obj, doc=doc, config=config)

class SphinxClassDoc(SphinxDocString, ClassDoc):
    def __init__(self, obj, doc=None, func_doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        ClassDoc.__init__(self, obj, doc=doc, func_doc=None, config=config)

class SphinxObjDoc(SphinxDocString):
    def __init__(self, obj, doc=None, config={}):
        self._f = obj
        SphinxDocString.__init__(self, doc, config=config)

def get_doc_object(obj, what=None, doc=None, config={}):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        return SphinxClassDoc(obj, func_doc=SphinxFunctionDoc, doc=doc,
                              config=config)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, doc=doc, config=config)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxObjDoc(obj, doc, config=config)

########NEW FILE########
__FILENAME__ = inheritance_diagram
"""
Defines a docutils directive for inserting inheritance diagrams.

Provide the directive with one or more classes or modules (separated
by whitespace).  For modules, all of the classes in that module will
be used.

Example::

   Given the following classes:

   class A: pass
   class B(A): pass
   class C(A): pass
   class D(B, C): pass
   class E(B): pass

   .. inheritance-diagram: D E

   Produces a graph like the following:

               A
              / \
             B   C
            / \ /
           E   D

The graph is inserted as a PNG+image map into HTML and a PDF in
LaTeX.
"""

import inspect
import os
import re
import subprocess
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from docutils.nodes import Body, Element
from docutils.parsers.rst import directives
from sphinx.roles import xfileref_role

def my_import(name):
    """Module importer - taken from the python documentation.

    This function allows importing names with dots in them."""
    
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

class DotException(Exception):
    pass

class InheritanceGraph(object):
    """
    Given a list of classes, determines the set of classes that
    they inherit from all the way to the root "object", and then
    is able to generate a graphviz dot graph from them.
    """
    def __init__(self, class_names, show_builtins=False):
        """
        *class_names* is a list of child classes to show bases from.

        If *show_builtins* is True, then Python builtins will be shown
        in the graph.
        """
        self.class_names = class_names
        self.classes = self._import_classes(class_names)
        self.all_classes = self._all_classes(self.classes)
        if len(self.all_classes) == 0:
            raise ValueError("No classes found for inheritance diagram")
        self.show_builtins = show_builtins

    py_sig_re = re.compile(r'''^([\w.]*\.)?    # class names
                           (\w+)  \s* $        # optionally arguments
                           ''', re.VERBOSE)

    def _import_class_or_module(self, name):
        """
        Import a class using its fully-qualified *name*.
        """
        try:
            path, base = self.py_sig_re.match(name).groups()
        except:
            raise ValueError(
                "Invalid class or module '%s' specified for inheritance diagram" % name)
        fullname = (path or '') + base
        path = (path and path.rstrip('.'))
        if not path:
            path = base
        try:
            module = __import__(path, None, None, [])
            # We must do an import of the fully qualified name.  Otherwise if a
            # subpackage 'a.b' is requested where 'import a' does NOT provide
            # 'a.b' automatically, then 'a.b' will not be found below.  This
            # second call will force the equivalent of 'import a.b' to happen
            # after the top-level import above.
            my_import(fullname)
            
        except ImportError:
            raise ValueError(
                "Could not import class or module '%s' specified for inheritance diagram" % name)

        try:
            todoc = module
            for comp in fullname.split('.')[1:]:
                todoc = getattr(todoc, comp)
        except AttributeError:
            raise ValueError(
                "Could not find class or module '%s' specified for inheritance diagram" % name)

        # If a class, just return it
        if inspect.isclass(todoc):
            return [todoc]
        elif inspect.ismodule(todoc):
            classes = []
            for cls in todoc.__dict__.values():
                if inspect.isclass(cls) and cls.__module__ == todoc.__name__:
                    classes.append(cls)
            return classes
        raise ValueError(
            "'%s' does not resolve to a class or module" % name)

    def _import_classes(self, class_names):
        """
        Import a list of classes.
        """
        classes = []
        for name in class_names:
            classes.extend(self._import_class_or_module(name))
        return classes

    def _all_classes(self, classes):
        """
        Return a list of all classes that are ancestors of *classes*.
        """
        all_classes = {}

        def recurse(cls):
            all_classes[cls] = None
            for c in cls.__bases__:
                if c not in all_classes:
                    recurse(c)

        for cls in classes:
            recurse(cls)

        return all_classes.keys()

    def class_name(self, cls, parts=0):
        """
        Given a class object, return a fully-qualified name.  This
        works for things I've tested in matplotlib so far, but may not
        be completely general.
        """
        module = cls.__module__
        if module == '__builtin__':
            fullname = cls.__name__
        else:
            fullname = "%s.%s" % (module, cls.__name__)
        if parts == 0:
            return fullname
        name_parts = fullname.split('.')
        return '.'.join(name_parts[-parts:])

    def get_all_class_names(self):
        """
        Get all of the class names involved in the graph.
        """
        return [self.class_name(x) for x in self.all_classes]

    # These are the default options for graphviz
    default_graph_options = {
        "rankdir": "LR",
        "size": '"8.0, 12.0"'
        }
    default_node_options = {
        "shape": "box",
        "fontsize": 10,
        "height": 0.25,
        "fontname": "Vera Sans, DejaVu Sans, Liberation Sans, Arial, Helvetica, sans",
        "style": '"setlinewidth(0.5)"'
        }
    default_edge_options = {
        "arrowsize": 0.5,
        "style": '"setlinewidth(0.5)"'
        }

    def _format_node_options(self, options):
        return ','.join(["%s=%s" % x for x in options.items()])
    def _format_graph_options(self, options):
        return ''.join(["%s=%s;\n" % x for x in options.items()])

    def generate_dot(self, fd, name, parts=0, urls={},
                     graph_options={}, node_options={},
                     edge_options={}):
        """
        Generate a graphviz dot graph from the classes that
        were passed in to __init__.

        *fd* is a Python file-like object to write to.

        *name* is the name of the graph

        *urls* is a dictionary mapping class names to http urls

        *graph_options*, *node_options*, *edge_options* are
        dictionaries containing key/value pairs to pass on as graphviz
        properties.
        """
        g_options = self.default_graph_options.copy()
        g_options.update(graph_options)
        n_options = self.default_node_options.copy()
        n_options.update(node_options)
        e_options = self.default_edge_options.copy()
        e_options.update(edge_options)

        fd.write('digraph %s {\n' % name)
        fd.write(self._format_graph_options(g_options))

        for cls in self.all_classes:
            if not self.show_builtins and cls in __builtins__.values():
                continue

            name = self.class_name(cls, parts)

            # Write the node
            this_node_options = n_options.copy()
            url = urls.get(self.class_name(cls))
            if url is not None:
                this_node_options['URL'] = '"%s"' % url
            fd.write('  "%s" [%s];\n' %
                     (name, self._format_node_options(this_node_options)))

            # Write the edges
            for base in cls.__bases__:
                if not self.show_builtins and base in __builtins__.values():
                    continue

                base_name = self.class_name(base, parts)
                fd.write('  "%s" -> "%s" [%s];\n' %
                         (base_name, name,
                          self._format_node_options(e_options)))
        fd.write('}\n')

    def run_dot(self, args, name, parts=0, urls={},
                graph_options={}, node_options={}, edge_options={}):
        """
        Run graphviz 'dot' over this graph, returning whatever 'dot'
        writes to stdout.

        *args* will be passed along as commandline arguments.

        *name* is the name of the graph

        *urls* is a dictionary mapping class names to http urls

        Raises DotException for any of the many os and
        installation-related errors that may occur.
        """
        try:
            dot = subprocess.Popen(['dot'] + list(args),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   close_fds=True)
        except OSError:
            raise DotException("Could not execute 'dot'.  Are you sure you have 'graphviz' installed?")
        except ValueError:
            raise DotException("'dot' called with invalid arguments")
        except:
            raise DotException("Unexpected error calling 'dot'")

        self.generate_dot(dot.stdin, name, parts, urls, graph_options,
                          node_options, edge_options)
        dot.stdin.close()
        result = dot.stdout.read()
        returncode = dot.wait()
        if returncode != 0:
            raise DotException("'dot' returned the errorcode %d" % returncode)
        return result

class inheritance_diagram(Body, Element):
    """
    A docutils node to use as a placeholder for the inheritance
    diagram.
    """
    pass

def inheritance_diagram_directive(name, arguments, options, content, lineno,
                                  content_offset, block_text, state,
                                  state_machine):
    """
    Run when the inheritance_diagram directive is first encountered.
    """
    node = inheritance_diagram()

    class_names = arguments

    # Create a graph starting with the list of classes
    graph = InheritanceGraph(class_names)

    # Create xref nodes for each target of the graph's image map and
    # add them to the doc tree so that Sphinx can resolve the
    # references to real URLs later.  These nodes will eventually be
    # removed from the doctree after we're done with them.
    for name in graph.get_all_class_names():
        refnodes, x = xfileref_role(
            'class', ':class:`%s`' % name, name, 0, state)
        node.extend(refnodes)
    # Store the graph object so we can use it to generate the
    # dot file later
    node['graph'] = graph
    # Store the original content for use as a hash
    node['parts'] = options.get('parts', 0)
    node['content'] = " ".join(class_names)
    return [node]

def get_graph_hash(node):
    return md5(node['content'] + str(node['parts'])).hexdigest()[-10:]

def html_output_graph(self, node):
    """
    Output the graph for HTML.  This will insert a PNG with clickable
    image map.
    """
    graph = node['graph']
    parts = node['parts']

    graph_hash = get_graph_hash(node)
    name = "inheritance%s" % graph_hash
    path = '_images'
    dest_path = os.path.join(setup.app.builder.outdir, path)
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    png_path = os.path.join(dest_path, name + ".png")
    path = setup.app.builder.imgpath

    # Create a mapping from fully-qualified class names to URLs.
    urls = {}
    for child in node:
        if child.get('refuri') is not None:
            urls[child['reftitle']] = child.get('refuri')
        elif child.get('refid') is not None:
            urls[child['reftitle']] = '#' + child.get('refid')

    # These arguments to dot will save a PNG file to disk and write
    # an HTML image map to stdout.
    image_map = graph.run_dot(['-Tpng', '-o%s' % png_path, '-Tcmapx'],
                              name, parts, urls)
    return ('<img src="%s/%s.png" usemap="#%s" class="inheritance"/>%s' %
            (path, name, name, image_map))

def latex_output_graph(self, node):
    """
    Output the graph for LaTeX.  This will insert a PDF.
    """
    graph = node['graph']
    parts = node['parts']

    graph_hash = get_graph_hash(node)
    name = "inheritance%s" % graph_hash
    dest_path = os.path.abspath(os.path.join(setup.app.builder.outdir, '_images'))
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    pdf_path = os.path.abspath(os.path.join(dest_path, name + ".pdf"))

    graph.run_dot(['-Tpdf', '-o%s' % pdf_path],
                  name, parts, graph_options={'size': '"6.0,6.0"'})
    return '\n\\includegraphics{%s}\n\n' % pdf_path

def visit_inheritance_diagram(inner_func):
    """
    This is just a wrapper around html/latex_output_graph to make it
    easier to handle errors and insert warnings.
    """
    def visitor(self, node):
        try:
            content = inner_func(self, node)
        except DotException, e:
            # Insert the exception as a warning in the document
            warning = self.document.reporter.warning(str(e), line=node.line)
            warning.parent = node
            node.children = [warning]
        else:
            source = self.document.attributes['source']
            self.body.append(content)
            node.children = []
    return visitor

def do_nothing(self, node):
    pass

def setup(app):
    setup.app = app
    setup.confdir = app.confdir

    app.add_node(
        inheritance_diagram,
        latex=(visit_inheritance_diagram(latex_output_graph), do_nothing),
        html=(visit_inheritance_diagram(html_output_graph), do_nothing))
    app.add_directive(
        'inheritance-diagram', inheritance_diagram_directive,
        False, (1, 100, 0), parts = directives.nonnegative_int)

########NEW FILE########
__FILENAME__ = ipython_console_highlighting
"""reST directive for syntax-highlighting ipython interactive sessions.

XXX - See what improvements can be made based on the new (as of Sept 2009)
'pycon' lexer for the python console.  At the very least it will give better
highlighted tracebacks.
"""

#-----------------------------------------------------------------------------
# Needed modules

# Standard library
import re

# Third party
from pygments.lexer import Lexer, do_insertions
from pygments.lexers.agile import (PythonConsoleLexer, PythonLexer, 
                                   PythonTracebackLexer)
from pygments.token import Comment, Generic

from sphinx import highlighting

#-----------------------------------------------------------------------------
# Global constants
line_re = re.compile('.*?\n')

#-----------------------------------------------------------------------------
# Code begins - classes and functions

class IPythonConsoleLexer(Lexer):
    """
    For IPython console output or doctests, such as:

    .. sourcecode:: ipython

      In [1]: a = 'foo'

      In [2]: a
      Out[2]: 'foo'

      In [3]: print a
      foo

      In [4]: 1 / 0

    Notes:

      - Tracebacks are not currently supported.

      - It assumes the default IPython prompts, not customized ones.
    """
    
    name = 'IPython console session'
    aliases = ['ipython']
    mimetypes = ['text/x-ipython-console']
    input_prompt = re.compile("(In \[[0-9]+\]: )|(   \.\.\.+:)")
    output_prompt = re.compile("(Out\[[0-9]+\]: )|(   \.\.\.+:)")
    continue_prompt = re.compile("   \.\.\.+:")
    tb_start = re.compile("\-+")

    def get_tokens_unprocessed(self, text):
        pylexer = PythonLexer(**self.options)
        tblexer = PythonTracebackLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            input_prompt = self.input_prompt.match(line)
            continue_prompt = self.continue_prompt.match(line.rstrip())
            output_prompt = self.output_prompt.match(line)
            if line.startswith("#"):
                insertions.append((len(curcode),
                                   [(0, Comment, line)]))
            elif input_prompt is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, input_prompt.group())]))
                curcode += line[input_prompt.end():]
            elif continue_prompt is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, continue_prompt.group())]))
                curcode += line[continue_prompt.end():]
            elif output_prompt is not None:
                # Use the 'error' token for output.  We should probably make
                # our own token, but error is typicaly in a bright color like
                # red, so it works fine for our output prompts.
                insertions.append((len(curcode),
                                   [(0, Generic.Error, output_prompt.group())]))
                curcode += line[output_prompt.end():]
            else:
                if curcode:
                    for item in do_insertions(insertions,
                                              pylexer.get_tokens_unprocessed(curcode)):
                        yield item
                        curcode = ''
                        insertions = []
                yield match.start(), Generic.Output, line
        if curcode:
            for item in do_insertions(insertions,
                                      pylexer.get_tokens_unprocessed(curcode)):
                yield item


def setup(app):
    """Setup as a sphinx extension."""

    # This is only a lexer, so adding it below to pygments appears sufficient.
    # But if somebody knows that the right API usage should be to do that via
    # sphinx, by all means fix it here.  At least having this setup.py
    # suppresses the sphinx warning we'd get without it.
    pass

#-----------------------------------------------------------------------------
# Register the extension as a valid pygments lexer
highlighting.lexers['ipython'] = IPythonConsoleLexer()

########NEW FILE########
__FILENAME__ = ipython_directive
# -*- coding: utf-8 -*-
"""Sphinx directive to support embedded IPython code.

This directive allows pasting of entire interactive IPython sessions, prompts
and all, and their code will actually get re-executed at doc build time, with
all prompts renumbered sequentially.

To enable this directive, simply list it in your Sphinx ``conf.py`` file
(making sure the directory where you placed it is visible to sphinx, as is
needed for all Sphinx directives).

By default this directive assumes that your prompts are unchanged IPython ones,
but this can be customized.  For example, the following code in your Sphinx
config file will configure this directive for the following input/output
prompts ``Yade [1]:`` and ``-> [1]:``::

 import ipython_directive as id
 id.rgxin =re.compile(r'(?:In |Yade )\[(\d+)\]:\s?(.*)\s*')
 id.rgxout=re.compile(r'(?:Out| ->  )\[(\d+)\]:\s?(.*)\s*')
 id.fmtin ='Yade [%d]:'
 id.fmtout=' ->  [%d]:'

 from IPython import Config
 id.CONFIG = Config(
   prompt_in1="Yade [\#]:",
   prompt_in2="     .\D..",
   prompt_out=" ->  [\#]:"
 )
 id.reconfig_shell()

 import ipython_console_highlighting as ich
 ich.IPythonConsoleLexer.input_prompt=
    re.compile("(Yade \[[0-9]+\]: )|(   \.\.\.+:)")
 ich.IPythonConsoleLexer.output_prompt=
    re.compile("(( ->  )|(Out)\[[0-9]+\]: )|(   \.\.\.+:)")
 ich.IPythonConsoleLexer.continue_prompt=re.compile("   \.\.\.+:")


ToDo
----

- Turn the ad-hoc test() function into a real test suite.
- Break up ipython-specific functionality from matplotlib stuff into better
  separated code.
- Make sure %bookmarks used internally are removed on exit.


Authors
-------

- John D Hunter: original author.
- Fernando Perez: refactoring, documentation, cleanups, port to 0.11.
- VáclavŠmilauer <eudoxos-AT-arcig.cz>: Prompt generalizations.
"""

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import cStringIO
import os
import re
import sys

# To keep compatibility with various python versions
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

# Third-party
import matplotlib
import sphinx
from docutils.parsers.rst import directives

matplotlib.use('Agg')

# Our own
from IPython import Config, InteractiveShell
from IPython.utils.io import Term

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

sphinx_version = sphinx.__version__.split(".")
# The split is necessary for sphinx beta versions where the string is
# '6b1'
sphinx_version = tuple([int(re.split('[a-z]', x)[0])
                        for x in sphinx_version[:2]])

COMMENT, INPUT, OUTPUT =  range(3)
CONFIG = Config()
rgxin = re.compile('In \[(\d+)\]:\s?(.*)\s*')
rgxout = re.compile('Out\[(\d+)\]:\s?(.*)\s*')
fmtin = 'In [%d]:'
fmtout = 'Out[%d]:'

#-----------------------------------------------------------------------------
# Functions and class declarations
#-----------------------------------------------------------------------------
def block_parser(part):
    """
    part is a string of ipython text, comprised of at most one
    input, one output, comments, and blank lines.  The block parser
    parses the text into a list of::

      blocks = [ (TOKEN0, data0), (TOKEN1, data1), ...]

    where TOKEN is one of [COMMENT | INPUT | OUTPUT ] and
    data is, depending on the type of token::

      COMMENT : the comment string

      INPUT: the (DECORATOR, INPUT_LINE, REST) where
         DECORATOR: the input decorator (or None)
         INPUT_LINE: the input as string (possibly multi-line)
         REST : any stdout generated by the input line (not OUTPUT)


      OUTPUT: the output string, possibly multi-line
    """

    block = []
    lines = part.split('\n')
    N = len(lines)
    i = 0
    decorator = None
    while 1:

        if i==N:
            # nothing left to parse -- the last line
            break

        line = lines[i]
        i += 1
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            block.append((COMMENT, line))
            continue

        if line_stripped.startswith('@'):
            # we're assuming at most one decorator -- may need to
            # rethink
            decorator = line_stripped
            continue

        # does this look like an input line?
        matchin = rgxin.match(line)
        if matchin:
            lineno, inputline = int(matchin.group(1)), matchin.group(2)

            # the ....: continuation string
            continuation = '   %s:'%''.join(['.']*(len(str(lineno))+2))
            Nc = len(continuation)
            # input lines can continue on for more than one line, if
            # we have a '\' line continuation char or a function call
            # echo line 'print'.  The input line can only be
            # terminated by the end of the block or an output line, so
            # we parse out the rest of the input line if it is
            # multiline as well as any echo text

            rest = []
            while i<N:

                # look ahead; if the next line is blank, or a comment, or
                # an output line, we're done

                nextline = lines[i]
                matchout = rgxout.match(nextline)
                #print "nextline=%s, continuation=%s, starts=%s"%(nextline, continuation, nextline.startswith(continuation))
                if matchout or nextline.startswith('#'):
                    break
                elif nextline.startswith(continuation):
                    inputline += '\n' + nextline[Nc:]
                else:
                    rest.append(nextline)
                i+= 1

            block.append((INPUT, (decorator, inputline, '\n'.join(rest))))
            continue

        # if it looks like an output line grab all the text to the end
        # of the block
        matchout = rgxout.match(line)
        if matchout:
            lineno, output = int(matchout.group(1)), matchout.group(2)
            if i<N-1:
                output = '\n'.join([output] + lines[i:])

            block.append((OUTPUT, output))
            break

    return block


class EmbeddedSphinxShell(object):
    """An embedded IPython instance to run inside Sphinx"""

    def __init__(self):

        self.cout = cStringIO.StringIO()
        Term.cout = self.cout
        Term.cerr = self.cout

        # For debugging, so we can see normal output, use this:
        # from IPython.utils.io import Tee
        #Term.cout = Tee(self.cout, channel='stdout') # dbg
        #Term.cerr = Tee(self.cout, channel='stderr') # dbg

        # Create config object for IPython
        config = Config()
        config.Global.display_banner = False
        config.Global.exec_lines = ['import numpy as np',
                                    'from pylab import *'
                                    ]
        config.InteractiveShell.autocall = False
        config.InteractiveShell.autoindent = False
        config.InteractiveShell.colors = 'NoColor'

        # Create and initialize ipython, but don't start its mainloop
        IP = InteractiveShell.instance(config=config)

        # Store a few parts of IPython we'll need.
        self.IP = IP
        self.user_ns = self.IP.user_ns
        self.user_global_ns = self.IP.user_global_ns
                                    
        self.input = ''
        self.output = ''

        self.is_verbatim = False
        self.is_doctest = False
        self.is_suppress = False

        # on the first call to the savefig decorator, we'll import
        # pyplot as plt so we can make a call to the plt.gcf().savefig
        self._pyplot_imported = False

        # we need bookmark the current dir first so we can save
        # relative to it
        self.process_input_line('bookmark ipy_basedir')
        self.cout.seek(0)
        self.cout.truncate(0)

    def process_input_line(self, line):
        """process the input, capturing stdout"""
        #print "input='%s'"%self.input
        stdout = sys.stdout
        try:
            sys.stdout = self.cout
            self.IP.push_line(line)
        finally:
            sys.stdout = stdout

    # Callbacks for each type of token
    def process_input(self, data, input_prompt, lineno):
        """Process data block for INPUT token."""
        decorator, input, rest = data
        image_file = None
        #print 'INPUT:', data  # dbg
        is_verbatim = decorator=='@verbatim' or self.is_verbatim
        is_doctest = decorator=='@doctest' or self.is_doctest
        is_suppress = decorator=='@suppress' or self.is_suppress
        is_savefig = decorator is not None and \
                     decorator.startswith('@savefig')

        input_lines = input.split('\n')

        continuation = '   %s:'%''.join(['.']*(len(str(lineno))+2))
        Nc = len(continuation)

        if is_savefig:
            saveargs = decorator.split(' ')
            filename = saveargs[1]
            outfile = os.path.join('_static/%s'%filename)
            # build out an image directive like
            # .. image:: somefile.png
            #    :width 4in
            #
            # from an input like
            # savefig somefile.png width=4in
            imagerows = ['.. image:: %s'%outfile]

            for kwarg in saveargs[2:]:
                arg, val = kwarg.split('=')
                arg = arg.strip()
                val = val.strip()
                imagerows.append('   :%s: %s'%(arg, val))

            image_file = outfile
            image_directive = '\n'.join(imagerows)

        # TODO: can we get "rest" from ipython
        #self.process_input_line('\n'.join(input_lines))

        ret = []
        is_semicolon = False

        for i, line in enumerate(input_lines):
            if line.endswith(';'):
                is_semicolon = True

            if i==0:
                # process the first input line
                if is_verbatim:
                    self.process_input_line('')
                else:
                    # only submit the line in non-verbatim mode
                    self.process_input_line(line)
                formatted_line = '%s %s'%(input_prompt, line)
            else:
                # process a continuation line
                if not is_verbatim:
                    self.process_input_line(line)

                formatted_line = '%s %s'%(continuation, line)

            if not is_suppress:
                ret.append(formatted_line)

        if not is_suppress:
            if len(rest.strip()):
                if is_verbatim:
                    # the "rest" is the standard output of the
                    # input, which needs to be added in
                    # verbatim mode
                    ret.append(rest)

        self.cout.seek(0)
        output = self.cout.read()
        if not is_suppress and not is_semicolon:
            ret.append(output)

        self.cout.truncate(0)
        return ret, input_lines, output, is_doctest, image_file
        #print 'OUTPUT', output  # dbg

    def process_output(self, data, output_prompt,
                       input_lines, output, is_doctest, image_file):
        """Process data block for OUTPUT token."""
        if is_doctest:
            submitted = data.strip()
            found = output
            if found is not None:
                found = found.strip()
                
                # XXX - fperez: in 0.11, 'output' never comes with the prompt
                # in it, just the actual output text.  So I think all this code
                # can be nuked...
                ## ind = found.find(output_prompt)
                ## if ind<0:
                ##     e='output prompt="%s" does not match out line=%s' % \
                ##        (output_prompt, found)
                ##     raise RuntimeError(e)
                ## found = found[len(output_prompt):].strip()

                if found!=submitted:
                    e = ('doctest failure for input_lines="%s" with '
                         'found_output="%s" and submitted output="%s"' %
                         (input_lines, found, submitted) )
                    raise RuntimeError(e)
                #print 'doctest PASSED for input_lines="%s" with found_output="%s" and submitted output="%s"'%(input_lines, found, submitted)

    def process_comment(self, data):
        """Process data block for COMMENT token."""
        if not self.is_suppress:
            return [data]

    def process_block(self, block):
        """
        process block from the block_parser and return a list of processed lines
        """

        ret = []
        output = None
        input_lines = None

        m = rgxin.match(str(self.IP.outputcache.prompt1).strip())
        lineno = int(m.group(1))

        input_prompt = fmtin%lineno
        output_prompt = fmtout%lineno
        image_file = None
        image_directive = None
        # XXX - This needs a second refactor.  There's too much state being
        # held globally, which makes for a very awkward interface and large,
        # hard to test functions.  I've already broken this up at least into
        # three separate processors to isolate the logic better, but this only
        # serves to highlight the coupling.  Next we need to clean it up...
        for token, data in block:
            if token==COMMENT:
                out_data = self.process_comment(data)
            elif token==INPUT:
                out_data, input_lines, output, is_doctest, image_file= \
                          self.process_input(data, input_prompt, lineno)
            elif token==OUTPUT:
                out_data = \
                    self.process_output(data, output_prompt,
                                        input_lines, output, is_doctest,
                                        image_file)
            if out_data:
                ret.extend(out_data)

        if image_file is not None:
            self.ensure_pyplot()
            command = 'plt.gcf().savefig("%s")'%image_file
            print 'SAVEFIG', command  # dbg
            self.process_input_line('bookmark ipy_thisdir')
            self.process_input_line('cd -b ipy_basedir')
            self.process_input_line(command)
            self.process_input_line('cd -b ipy_thisdir')
            self.cout.seek(0)
            self.cout.truncate(0)
        return ret, image_directive

    def ensure_pyplot(self):
        if self._pyplot_imported:
            return
        self.process_input_line('import matplotlib.pyplot as plt')

# A global instance used below. XXX: not sure why this can't be created inside
# ipython_directive itself.
shell = EmbeddedSphinxShell()

def reconfig_shell():
    """Called after setting module-level variables to re-instantiate
    with the set values (since shell is instantiated first at import-time
    when module variables have default values)"""
    global shell
    shell = EmbeddedSphinxShell()


def ipython_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine,
                      ):

    debug = ipython_directive.DEBUG
    shell.is_suppress = options.has_key('suppress')
    shell.is_doctest = options.has_key('doctest')
    shell.is_verbatim = options.has_key('verbatim')

    #print 'ipy', shell.is_suppress, options
    parts = '\n'.join(content).split('\n\n')
    lines = ['.. sourcecode:: ipython', '']

    figures = []
    for part in parts:
        block = block_parser(part)

        if len(block):
            rows, figure = shell.process_block(block)
            for row in rows:
                lines.extend(['    %s'%line for line in row.split('\n')])

            if figure is not None:
                figures.append(figure)

    for figure in figures:
        lines.append('')
        lines.extend(figure.split('\n'))
        lines.append('')

    #print lines
    if len(lines)>2:
        if debug:
            print '\n'.join(lines)
        else:
            #print 'INSERTING %d lines'%len(lines)
            state_machine.insert_input(
                lines, state_machine.input_lines.source(0))

    return []

ipython_directive.DEBUG = False
ipython_directive.DEBUG = True  # dbg

# Enable as a proper Sphinx directive
def setup(app):
    setup.app = app
    options = {'suppress': directives.flag,
               'doctest': directives.flag,
               'verbatim': directives.flag,
               }

    app.add_directive('ipython', ipython_directive, True, (0, 2, 0), **options)


# Simple smoke test, needs to be converted to a proper automatic test.
def test():

    examples = [
        r"""
In [9]: pwd
Out[9]: '/home/jdhunter/py4science/book'

In [10]: cd bookdata/
/home/jdhunter/py4science/book/bookdata

In [2]: from pylab import *

In [2]: ion()

In [3]: im = imread('stinkbug.png')

@savefig mystinkbug.png width=4in
In [4]: imshow(im)
Out[4]: <matplotlib.image.AxesImage object at 0x39ea850>
        
""",
        r"""

In [1]: x = 'hello world'

# string methods can be
# used to alter the string
@doctest
In [2]: x.upper()
Out[2]: 'HELLO WORLD'

@verbatim
In [3]: x.st<TAB>
x.startswith  x.strip
""",
    r"""

In [130]: url = 'http://ichart.finance.yahoo.com/table.csv?s=CROX\
   .....: &d=9&e=22&f=2009&g=d&a=1&br=8&c=2006&ignore=.csv'

In [131]: print url.split('&')
['http://ichart.finance.yahoo.com/table.csv?s=CROX', 'd=9', 'e=22', 'f=2009', 'g=d', 'a=1', 'b=8', 'c=2006', 'ignore=.csv']

In [60]: import urllib

""",
    r"""\

In [133]: import numpy.random

@suppress
In [134]: numpy.random.seed(2358)

@doctest
In [135]: np.random.rand(10,2)
Out[135]:
array([[ 0.64524308,  0.59943846],
       [ 0.47102322,  0.8715456 ],
       [ 0.29370834,  0.74776844],
       [ 0.99539577,  0.1313423 ],
       [ 0.16250302,  0.21103583],
       [ 0.81626524,  0.1312433 ],
       [ 0.67338089,  0.72302393],
       [ 0.7566368 ,  0.07033696],
       [ 0.22591016,  0.77731835],
       [ 0.0072729 ,  0.34273127]])

""",

    r"""
In [106]: print x
jdh

In [109]: for i in range(10):
   .....:     print i
   .....:
   .....:
0
1
2
3
4
5
6
7
8
9
""",

        r"""

In [144]: from pylab import *

In [145]: ion()

# use a semicolon to suppress the output
@savefig test_hist.png width=4in
In [151]: hist(np.random.randn(10000), 100);


@savefig test_plot.png width=4in
In [151]: plot(np.random.randn(10000), 'o');
   """,

        r"""
# use a semicolon to suppress the output
In [151]: plt.clf()

@savefig plot_simple.png width=4in
In [151]: plot([1,2,3])

@savefig hist_simple.png width=4in
In [151]: hist(np.random.randn(10000), 100);

""",
     r"""
# update the current fig
In [151]: ylabel('number')

In [152]: title('normal distribution')


@savefig hist_with_text.png
In [153]: grid(True)

        """,
        ]

    #ipython_directive.DEBUG = True  # dbg
    #options = dict(suppress=True)  # dbg
    options = dict()
    for example in examples:
        content = example.split('\n')
        ipython_directive('debug', arguments=None, options=options,
                          content=content, lineno=0,
                          content_offset=None, block_text=None,
                          state=None, state_machine=None,
                          )

# Run test suite as a script
if __name__=='__main__':
    if not os.path.isdir('_static'):
        os.mkdir('_static')
    test()
    print 'All OK? Check figures in _static/'

########NEW FILE########
__FILENAME__ = numpydoc
"""
========
numpydoc
========

Sphinx extension that handles docstrings in the Numpy standard format. [1]

It will:

- Convert Parameters etc. sections to field lists.
- Convert See Also section to a See also entry.
- Renumber references.
- Extract the signature from the docstring, if it can't be determined otherwise.

.. [1] http://projects.scipy.org/numpy/wiki/CodingStyleGuidelines#docstring-standard

"""

import sphinx

if sphinx.__version__ < '1.0.1':
    raise RuntimeError("Sphinx 1.0.1 or newer is required")

import os, re, pydoc
from docscrape_sphinx import get_doc_object, SphinxDocString
from sphinx.util.compat import Directive
import inspect

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):

    cfg = dict(use_plots=app.config.numpydoc_use_plots,
               show_class_members=app.config.numpydoc_show_class_members)

    if what == 'module':
        # Strip top title
        title_re = re.compile(ur'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub(u'', u"\n".join(lines)).split(u"\n")
    else:
        doc = get_doc_object(obj, what, u"\n".join(lines), config=cfg)
        lines[:] = unicode(doc).split(u"\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name=u"%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += [u'', u'.. htmlonly::', '']
        lines += [u'    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for line in lines:
        line = line.strip()
        m = re.match(ur'^.. \[([a-z0-9_.-])\]', line, re.I)
        if m:
            references.append(m.group(1))

    # start renaming from the longest string, to avoid overwriting parts
    references.sort(key=lambda x: -len(x))
    if references:
        for i, line in enumerate(lines):
            for r in references:
                if re.match(ur'^\d+$', r):
                    new_r = u"R%d" % (reference_offset[0] + int(r))
                else:
                    new_r = u"%s%d" % (r, reference_offset[0])
                lines[i] = lines[i].replace(u'[%s]_' % r,
                                            u'[%s]_' % new_r)
                lines[i] = lines[i].replace(u'.. [%s]' % r,
                                            u'.. [%s]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        (not hasattr(obj, '__init__') or
        'initializes x; see ' in pydoc.getdoc(obj.__init__))):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub(u"^[^(]*", u"", doc['Signature'])
        return sig, u''

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_

    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('autodoc-process-signature', mangle_signature)
    app.add_config_value('numpydoc_edit_link', None, False)
    app.add_config_value('numpydoc_use_plots', None, False)
    app.add_config_value('numpydoc_show_class_members', True, True)

    # Extra mangling domains
    app.add_domain(NumpyPythonDomain)
    app.add_domain(NumpyCDomain)

#------------------------------------------------------------------------------
# Docstring-mangling domains
#------------------------------------------------------------------------------

from docutils.statemachine import ViewList
from sphinx.domains.c import CDomain
from sphinx.domains.python import PythonDomain

class ManglingDomainBase(object):
    directive_mangling_map = {}

    def __init__(self, *a, **kw):
        super(ManglingDomainBase, self).__init__(*a, **kw)
        self.wrap_mangling_directives()

    def wrap_mangling_directives(self):
        for name, objtype in self.directive_mangling_map.items():
            self.directives[name] = wrap_mangling_directive(
                self.directives[name], objtype)

class NumpyPythonDomain(ManglingDomainBase, PythonDomain):
    name = 'np'
    directive_mangling_map = {
        'function': 'function',
        'class': 'class',
        'exception': 'class',
        'method': 'function',
        'classmethod': 'function',
        'staticmethod': 'function',
        'attribute': 'attribute',
    }

class NumpyCDomain(ManglingDomainBase, CDomain):
    name = 'np-c'
    directive_mangling_map = {
        'function': 'function',
        'member': 'attribute',
        'macro': 'function',
        'type': 'class',
        'var': 'object',
    }

def wrap_mangling_directive(base_directive, objtype):
    class directive(base_directive):
        def run(self):
            env = self.state.document.settings.env

            name = None
            if self.arguments:
                m = re.match(r'^(.*\s+)?(.*?)(\(.*)?', self.arguments[0])
                name = m.group(2).strip()

            if not name:
                name = self.arguments[0]

            lines = list(self.content)
            mangle_docstrings(env.app, objtype, name, None, None, lines)
            self.content = ViewList(lines, self.content.parent)

            return base_directive.run(self)

    return directive


########NEW FILE########
__FILENAME__ = phantom_import
"""
==============
phantom_import
==============

Sphinx extension to make directives from ``sphinx.ext.autodoc`` and similar
extensions to use docstrings loaded from an XML file.

This extension loads an XML file in the Pydocweb format [1] and
creates a dummy module that contains the specified docstrings. This
can be used to get the current docstrings from a Pydocweb instance
without needing to rebuild the documented module.

.. [1] http://code.google.com/p/pydocweb

"""
import imp, sys, compiler, types, os, inspect, re

def setup(app):
    app.connect('builder-inited', initialize)
    app.add_config_value('phantom_import_file', None, True)

def initialize(app):
    fn = app.config.phantom_import_file
    if (fn and os.path.isfile(fn)):
        print "[numpydoc] Phantom importing modules from", fn, "..."
        import_phantom_module(fn)

#------------------------------------------------------------------------------
# Creating 'phantom' modules from an XML description
#------------------------------------------------------------------------------
def import_phantom_module(xml_file):
    """
    Insert a fake Python module to sys.modules, based on a XML file.

    The XML file is expected to conform to Pydocweb DTD. The fake
    module will contain dummy objects, which guarantee the following:

    - Docstrings are correct.
    - Class inheritance relationships are correct (if present in XML).
    - Function argspec is *NOT* correct (even if present in XML).
      Instead, the function signature is prepended to the function docstring.
    - Class attributes are *NOT* correct; instead, they are dummy objects.

    Parameters
    ----------
    xml_file : str
        Name of an XML file to read
    
    """
    import lxml.etree as etree

    object_cache = {}

    tree = etree.parse(xml_file)
    root = tree.getroot()

    # Sort items so that
    # - Base classes come before classes inherited from them
    # - Modules come before their contents
    all_nodes = dict([(n.attrib['id'], n) for n in root])
    
    def _get_bases(node, recurse=False):
        bases = [x.attrib['ref'] for x in node.findall('base')]
        if recurse:
            j = 0
            while True:
                try:
                    b = bases[j]
                except IndexError: break
                if b in all_nodes:
                    bases.extend(_get_bases(all_nodes[b]))
                j += 1
        return bases

    type_index = ['module', 'class', 'callable', 'object']
    
    def base_cmp(a, b):
        x = cmp(type_index.index(a.tag), type_index.index(b.tag))
        if x != 0: return x

        if a.tag == 'class' and b.tag == 'class':
            a_bases = _get_bases(a, recurse=True)
            b_bases = _get_bases(b, recurse=True)
            x = cmp(len(a_bases), len(b_bases))
            if x != 0: return x
            if a.attrib['id'] in b_bases: return -1
            if b.attrib['id'] in a_bases: return 1
        
        return cmp(a.attrib['id'].count('.'), b.attrib['id'].count('.'))

    nodes = root.getchildren()
    nodes.sort(base_cmp)

    # Create phantom items
    for node in nodes:
        name = node.attrib['id']
        doc = (node.text or '').decode('string-escape') + "\n"
        if doc == "\n": doc = ""

        # create parent, if missing
        parent = name
        while True:
            parent = '.'.join(parent.split('.')[:-1])
            if not parent: break
            if parent in object_cache: break
            obj = imp.new_module(parent)
            object_cache[parent] = obj
            sys.modules[parent] = obj

        # create object
        if node.tag == 'module':
            obj = imp.new_module(name)
            obj.__doc__ = doc
            sys.modules[name] = obj
        elif node.tag == 'class':
            bases = [object_cache[b] for b in _get_bases(node)
                     if b in object_cache]
            bases.append(object)
            init = lambda self: None
            init.__doc__ = doc
            obj = type(name, tuple(bases), {'__doc__': doc, '__init__': init})
            obj.__name__ = name.split('.')[-1]
        elif node.tag == 'callable':
            funcname = node.attrib['id'].split('.')[-1]
            argspec = node.attrib.get('argspec')
            if argspec:
                argspec = re.sub('^[^(]*', '', argspec)
                doc = "%s%s\n\n%s" % (funcname, argspec, doc)
            obj = lambda: 0
            obj.__argspec_is_invalid_ = True
            obj.func_name = funcname
            obj.__name__ = name
            obj.__doc__ = doc
            if inspect.isclass(object_cache[parent]):
                obj.__objclass__ = object_cache[parent]
        else:
            class Dummy(object): pass
            obj = Dummy()
            obj.__name__ = name
            obj.__doc__ = doc
            if inspect.isclass(object_cache[parent]):
                obj.__get__ = lambda: None
        object_cache[name] = obj

        if parent:
            if inspect.ismodule(object_cache[parent]):
                obj.__module__ = parent
                setattr(object_cache[parent], name.split('.')[-1], obj)

    # Populate items
    for node in root:
        obj = object_cache.get(node.attrib['id'])
        if obj is None: continue
        for ref in node.findall('ref'):
            if node.tag == 'class':
                if ref.attrib['ref'].startswith(node.attrib['id'] + '.'):
                    setattr(obj, ref.attrib['name'],
                            object_cache.get(ref.attrib['ref']))
            else:
                setattr(obj, ref.attrib['name'],
                        object_cache.get(ref.attrib['ref']))

########NEW FILE########
__FILENAME__ = plot_directive
"""
A special directive for generating a matplotlib plot.

.. warning::

   This is a hacked version of plot_directive.py from Matplotlib.
   It's very much subject to change!


Usage
-----

Can be used like this::

    .. plot:: examples/example.py

    .. plot::

       import matplotlib.pyplot as plt
       plt.plot([1,2,3], [4,5,6])

    .. plot::

       A plotting example:

       >>> import matplotlib.pyplot as plt
       >>> plt.plot([1,2,3], [4,5,6])

The content is interpreted as doctest formatted if it has a line starting
with ``>>>``.

The ``plot`` directive supports the options

    format : {'python', 'doctest'}
        Specify the format of the input

    include-source : bool
        Whether to display the source code. Default can be changed in conf.py
    
and the ``image`` directive options ``alt``, ``height``, ``width``,
``scale``, ``align``, ``class``.

Configuration options
---------------------

The plot directive has the following configuration options:

    plot_include_source
        Default value for the include-source option

    plot_pre_code
        Code that should be executed before each plot.

    plot_basedir
        Base directory, to which plot:: file names are relative to.
        (If None or empty, file names are relative to the directoly where
        the file containing the directive is.)

    plot_formats
        File formats to generate. List of tuples or strings::

            [(suffix, dpi), suffix, ...]

        that determine the file format and the DPI. For entries whose
        DPI was omitted, sensible defaults are chosen.

    plot_html_show_formats
        Whether to show links to the files in HTML.

TODO
----

* Refactor Latex output; now it's plain images, but it would be nice
  to make them appear side-by-side, or in floats.

"""

import sys, os, glob, shutil, imp, warnings, cStringIO, re, textwrap, traceback
import sphinx

import warnings
warnings.warn("A plot_directive module is also available under "
              "matplotlib.sphinxext; expect this numpydoc.plot_directive "
              "module to be deprecated after relevant features have been "
              "integrated there.",
              FutureWarning, stacklevel=2)


#------------------------------------------------------------------------------
# Registration hook
#------------------------------------------------------------------------------

def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir
    
    app.add_config_value('plot_pre_code', '', True)
    app.add_config_value('plot_include_source', False, True)
    app.add_config_value('plot_formats', ['png', 'hires.png', 'pdf'], True)
    app.add_config_value('plot_basedir', None, True)
    app.add_config_value('plot_html_show_formats', True, True)

    app.add_directive('plot', plot_directive, True, (0, 1, False),
                      **plot_directive_options)

#------------------------------------------------------------------------------
# plot:: directive
#------------------------------------------------------------------------------
from docutils.parsers.rst import directives
from docutils import nodes

def plot_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    return run(arguments, content, options, state_machine, state, lineno)
plot_directive.__doc__ = __doc__

def _option_boolean(arg):
    if not arg or not arg.strip():
        # no argument given, assume used as a flag
        return True
    elif arg.strip().lower() in ('no', '0', 'false'):
        return False
    elif arg.strip().lower() in ('yes', '1', 'true'):
        return True
    else:
        raise ValueError('"%s" unknown boolean' % arg)

def _option_format(arg):
    return directives.choice(arg, ('python', 'lisp'))

def _option_align(arg):
    return directives.choice(arg, ("top", "middle", "bottom", "left", "center",
                                   "right"))

plot_directive_options = {'alt': directives.unchanged,
                          'height': directives.length_or_unitless,
                          'width': directives.length_or_percentage_or_unitless,
                          'scale': directives.nonnegative_int,
                          'align': _option_align,
                          'class': directives.class_option,
                          'include-source': _option_boolean,
                          'format': _option_format,
                          }

#------------------------------------------------------------------------------
# Generating output
#------------------------------------------------------------------------------

from docutils import nodes, utils

try:
    # Sphinx depends on either Jinja or Jinja2
    import jinja2
    def format_template(template, **kw):
        return jinja2.Template(template).render(**kw)
except ImportError:
    import jinja
    def format_template(template, **kw):
        return jinja.from_string(template, **kw)

TEMPLATE = """
{{ source_code }}

{{ only_html }}

   {% if source_link or (html_show_formats and not multi_image) %}
   (
   {%- if source_link -%}
   `Source code <{{ source_link }}>`__
   {%- endif -%}
   {%- if html_show_formats and not multi_image -%}
     {%- for img in images -%}
       {%- for fmt in img.formats -%}
         {%- if source_link or not loop.first -%}, {% endif -%}
         `{{ fmt }} <{{ dest_dir }}/{{ img.basename }}.{{ fmt }}>`__
       {%- endfor -%}
     {%- endfor -%}
   {%- endif -%}
   )
   {% endif %}

   {% for img in images %}
   .. figure:: {{ build_dir }}/{{ img.basename }}.png
      {%- for option in options %}
      {{ option }}
      {% endfor %}

      {% if html_show_formats and multi_image -%}
        (
        {%- for fmt in img.formats -%}
        {%- if not loop.first -%}, {% endif -%}
        `{{ fmt }} <{{ dest_dir }}/{{ img.basename }}.{{ fmt }}>`__
        {%- endfor -%}
        )
      {%- endif -%}
   {% endfor %}

{{ only_latex }}

   {% for img in images %}
   .. image:: {{ build_dir }}/{{ img.basename }}.pdf
   {% endfor %}

"""

class ImageFile(object):
    def __init__(self, basename, dirname):
        self.basename = basename
        self.dirname = dirname
        self.formats = []

    def filename(self, format):
        return os.path.join(self.dirname, "%s.%s" % (self.basename, format))

    def filenames(self):
        return [self.filename(fmt) for fmt in self.formats]

def run(arguments, content, options, state_machine, state, lineno):
    if arguments and content:
        raise RuntimeError("plot:: directive can't have both args and content")

    document = state_machine.document
    config = document.settings.env.config

    options.setdefault('include-source', config.plot_include_source)

    # determine input
    rst_file = document.attributes['source']
    rst_dir = os.path.dirname(rst_file)

    if arguments:
        if not config.plot_basedir:
            source_file_name = os.path.join(rst_dir,
                                            directives.uri(arguments[0]))
        else:
            source_file_name = os.path.join(setup.confdir, config.plot_basedir,
                                            directives.uri(arguments[0]))
        code = open(source_file_name, 'r').read()
        output_base = os.path.basename(source_file_name)
    else:
        source_file_name = rst_file
        code = textwrap.dedent("\n".join(map(str, content)))
        counter = document.attributes.get('_plot_counter', 0) + 1
        document.attributes['_plot_counter'] = counter
        base, ext = os.path.splitext(os.path.basename(source_file_name))
        output_base = '%s-%d.py' % (base, counter)

    base, source_ext = os.path.splitext(output_base)
    if source_ext in ('.py', '.rst', '.txt'):
        output_base = base
    else:
        source_ext = ''

    # ensure that LaTeX includegraphics doesn't choke in foo.bar.pdf filenames
    output_base = output_base.replace('.', '-')

    # is it in doctest format?
    is_doctest = contains_doctest(code)
    if options.has_key('format'):
        if options['format'] == 'python':
            is_doctest = False
        else:
            is_doctest = True

    # determine output directory name fragment
    source_rel_name = relpath(source_file_name, setup.confdir)
    source_rel_dir = os.path.dirname(source_rel_name)
    while source_rel_dir.startswith(os.path.sep):
        source_rel_dir = source_rel_dir[1:]

    # build_dir: where to place output files (temporarily)
    build_dir = os.path.join(os.path.dirname(setup.app.doctreedir),
                             'plot_directive',
                             source_rel_dir)
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    # output_dir: final location in the builder's directory
    dest_dir = os.path.abspath(os.path.join(setup.app.builder.outdir,
                                            source_rel_dir))

    # how to link to files from the RST file
    dest_dir_link = os.path.join(relpath(setup.confdir, rst_dir),
                                 source_rel_dir).replace(os.path.sep, '/')
    build_dir_link = relpath(build_dir, rst_dir).replace(os.path.sep, '/')
    source_link = dest_dir_link + '/' + output_base + source_ext

    # make figures
    try:
        results = makefig(code, source_file_name, build_dir, output_base,
                          config)
        errors = []
    except PlotError, err:
        reporter = state.memo.reporter
        sm = reporter.system_message(
            2, "Exception occurred in plotting %s: %s" % (output_base, err),
            line=lineno)
        results = [(code, [])]
        errors = [sm]

    # generate output restructuredtext
    total_lines = []
    for j, (code_piece, images) in enumerate(results):
        if options['include-source']:
            if is_doctest:
                lines = ['']
                lines += [row.rstrip() for row in code_piece.split('\n')]
            else:
                lines = ['.. code-block:: python', '']
                lines += ['    %s' % row.rstrip()
                          for row in code_piece.split('\n')]
            source_code = "\n".join(lines)
        else:
            source_code = ""

        opts = [':%s: %s' % (key, val) for key, val in options.items()
                if key in ('alt', 'height', 'width', 'scale', 'align', 'class')]

        only_html = ".. only:: html"
        only_latex = ".. only:: latex"

        if j == 0:
            src_link = source_link
        else:
            src_link = None

        result = format_template(
            TEMPLATE,
            dest_dir=dest_dir_link,
            build_dir=build_dir_link,
            source_link=src_link,
            multi_image=len(images) > 1,
            only_html=only_html,
            only_latex=only_latex,
            options=opts,
            images=images,
            source_code=source_code,
            html_show_formats=config.plot_html_show_formats)

        total_lines.extend(result.split("\n"))
        total_lines.extend("\n")

    if total_lines:
        state_machine.insert_input(total_lines, source=source_file_name)

    # copy image files to builder's output directory
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for code_piece, images in results:
        for img in images:
            for fn in img.filenames():
                shutil.copyfile(fn, os.path.join(dest_dir,
                                                 os.path.basename(fn)))

    # copy script (if necessary)
    if source_file_name == rst_file:
        target_name = os.path.join(dest_dir, output_base + source_ext)
        f = open(target_name, 'w')
        f.write(unescape_doctest(code))
        f.close()

    return errors


#------------------------------------------------------------------------------
# Run code and capture figures
#------------------------------------------------------------------------------

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as image
from matplotlib import _pylab_helpers

import exceptions

def contains_doctest(text):
    try:
        # check if it's valid Python as-is
        compile(text, '<string>', 'exec')
        return False
    except SyntaxError:
        pass
    r = re.compile(r'^\s*>>>', re.M)
    m = r.search(text)
    return bool(m)

def unescape_doctest(text):
    """
    Extract code from a piece of text, which contains either Python code
    or doctests.

    """
    if not contains_doctest(text):
        return text

    code = ""
    for line in text.split("\n"):
        m = re.match(r'^\s*(>>>|\.\.\.) (.*)$', line)
        if m:
            code += m.group(2) + "\n"
        elif line.strip():
            code += "# " + line.strip() + "\n"
        else:
            code += "\n"
    return code

def split_code_at_show(text):
    """
    Split code at plt.show()

    """

    parts = []
    is_doctest = contains_doctest(text)

    part = []
    for line in text.split("\n"):
        if (not is_doctest and line.strip() == 'plt.show()') or \
               (is_doctest and line.strip() == '>>> plt.show()'):
            part.append(line)
            parts.append("\n".join(part))
            part = []
        else:
            part.append(line)
    if "\n".join(part).strip():
        parts.append("\n".join(part))
    return parts

class PlotError(RuntimeError):
    pass

def run_code(code, code_path, ns=None):
    # Change the working directory to the directory of the example, so
    # it can get at its data files, if any.
    pwd = os.getcwd()
    old_sys_path = list(sys.path)
    if code_path is not None:
        dirname = os.path.abspath(os.path.dirname(code_path))
        os.chdir(dirname)
        sys.path.insert(0, dirname)

    # Redirect stdout
    stdout = sys.stdout
    sys.stdout = cStringIO.StringIO()

    # Reset sys.argv
    old_sys_argv = sys.argv
    sys.argv = [code_path]
    
    try:
        try:
            code = unescape_doctest(code)
            if ns is None:
                ns = {}
            if not ns:
                exec setup.config.plot_pre_code in ns
            exec code in ns
        except (Exception, SystemExit), err:
            raise PlotError(traceback.format_exc())
    finally:
        os.chdir(pwd)
        sys.argv = old_sys_argv
        sys.path[:] = old_sys_path
        sys.stdout = stdout
    return ns


#------------------------------------------------------------------------------
# Generating figures
#------------------------------------------------------------------------------

def out_of_date(original, derived):
    """
    Returns True if derivative is out-of-date wrt original,
    both of which are full file paths.
    """
    return (not os.path.exists(derived)
            or os.stat(derived).st_mtime < os.stat(original).st_mtime)


def makefig(code, code_path, output_dir, output_base, config):
    """
    Run a pyplot script *code* and save the images under *output_dir*
    with file names derived from *output_base*

    """

    # -- Parse format list
    default_dpi = {'png': 80, 'hires.png': 200, 'pdf': 50}
    formats = []
    for fmt in config.plot_formats:
        if isinstance(fmt, str):
            formats.append((fmt, default_dpi.get(fmt, 80)))
        elif type(fmt) in (tuple, list) and len(fmt)==2:
            formats.append((str(fmt[0]), int(fmt[1])))
        else:
            raise PlotError('invalid image format "%r" in plot_formats' % fmt)

    # -- Try to determine if all images already exist

    code_pieces = split_code_at_show(code)

    # Look for single-figure output files first
    all_exists = True
    img = ImageFile(output_base, output_dir)
    for format, dpi in formats:
        if out_of_date(code_path, img.filename(format)):
            all_exists = False
            break
        img.formats.append(format)

    if all_exists:
        return [(code, [img])]

    # Then look for multi-figure output files
    results = []
    all_exists = True
    for i, code_piece in enumerate(code_pieces):
        images = []
        for j in xrange(1000):
            img = ImageFile('%s_%02d_%02d' % (output_base, i, j), output_dir)
            for format, dpi in formats:
                if out_of_date(code_path, img.filename(format)):
                    all_exists = False
                    break
                img.formats.append(format)

            # assume that if we have one, we have them all
            if not all_exists:
                all_exists = (j > 0)
                break
            images.append(img)
        if not all_exists:
            break
        results.append((code_piece, images))

    if all_exists:
        return results

    # -- We didn't find the files, so build them

    results = []
    ns = {}

    for i, code_piece in enumerate(code_pieces):
        # Clear between runs
        plt.close('all')

        # Run code
        run_code(code_piece, code_path, ns)

        # Collect images
        images = []
        fig_managers = _pylab_helpers.Gcf.get_all_fig_managers()
        for j, figman in enumerate(fig_managers):
            if len(fig_managers) == 1 and len(code_pieces) == 1:
                img = ImageFile(output_base, output_dir)
            else:
                img = ImageFile("%s_%02d_%02d" % (output_base, i, j),
                                output_dir)
            images.append(img)
            for format, dpi in formats:
                try:
                    figman.canvas.figure.savefig(img.filename(format), dpi=dpi)
                except exceptions.BaseException, err:
                    raise PlotError(traceback.format_exc())
                img.formats.append(format)

        # Results
        results.append((code_piece, images))

    return results


#------------------------------------------------------------------------------
# Relative pathnames
#------------------------------------------------------------------------------

try:
    from os.path import relpath
except ImportError:
    # Copied from Python 2.7
    if 'posix' in sys.builtin_module_names:
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""
            from os.path import sep, curdir, join, abspath, commonprefix, \
                 pardir

            if not path:
                raise ValueError("no path specified")

            start_list = abspath(start).split(sep)
            path_list = abspath(path).split(sep)

            # Work out how much of the filepath is shared by start and path.
            i = len(commonprefix([start_list, path_list]))

            rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return curdir
            return join(*rel_list)
    elif 'nt' in sys.builtin_module_names:
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""
            from os.path import sep, curdir, join, abspath, commonprefix, \
                 pardir, splitunc

            if not path:
                raise ValueError("no path specified")
            start_list = abspath(start).split(sep)
            path_list = abspath(path).split(sep)
            if start_list[0].lower() != path_list[0].lower():
                unc_path, rest = splitunc(path)
                unc_start, rest = splitunc(start)
                if bool(unc_path) ^ bool(unc_start):
                    raise ValueError("Cannot mix UNC and non-UNC paths (%s and %s)"
                                                                        % (path, start))
                else:
                    raise ValueError("path is on drive %s, start on drive %s"
                                                        % (path_list[0], start_list[0]))
            # Work out how much of the filepath is shared by start and path.
            for i in range(min(len(start_list), len(path_list))):
                if start_list[i].lower() != path_list[i].lower():
                    break
            else:
                i += 1

            rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return curdir
            return join(*rel_list)
    else:
        raise RuntimeError("Unsupported platform (no relpath available!)")

########NEW FILE########
__FILENAME__ = traitsdoc
"""
=========
traitsdoc
=========

Sphinx extension that handles docstrings in the Numpy standard format, [1]
and support Traits [2].

This extension can be used as a replacement for ``numpydoc`` when support
for Traits is required.

.. [1] http://projects.scipy.org/numpy/wiki/CodingStyleGuidelines#docstring-standard
.. [2] http://code.enthought.com/projects/traits/

"""

import inspect
import os
import pydoc

import docscrape
import docscrape_sphinx
from docscrape_sphinx import SphinxClassDoc, SphinxFunctionDoc, SphinxDocString

import numpydoc

import comment_eater

class SphinxTraitsDoc(SphinxClassDoc):
    def __init__(self, cls, modulename='', func_doc=SphinxFunctionDoc):
        if not inspect.isclass(cls):
            raise ValueError("Initialise using a class. Got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename
        self._name = cls.__name__
        self._func_doc = func_doc

        docstring = pydoc.getdoc(cls)
        docstring = docstring.split('\n')

        # De-indent paragraph
        try:
            indent = min(len(s) - len(s.lstrip()) for s in docstring
                         if s.strip())
        except ValueError:
            indent = 0

        for n,line in enumerate(docstring):
            docstring[n] = docstring[n][indent:]

        self._doc = docscrape.Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': '',
            'Description': [],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Traits': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'References': '',
            'Example': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Description'] + self['Extended Summary'] + ['']

    def __str__(self, indent=0, func_role="func"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Traits', 'Methods',
                           'Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_see_also("obj")
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_section('Example')
        out += self._str_section('Examples')
        out = self._str_indent(out,indent)
        return '\n'.join(out)

def looks_like_issubclass(obj, classname):
    """ Return True if the object has a class or superclass with the given class
    name.

    Ignores old-style classes.
    """
    t = obj
    if t.__name__ == classname:
        return True
    for klass in t.__mro__:
        if klass.__name__ == classname:
            return True
    return False

def get_doc_object(obj, what=None, config=None):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        doc = SphinxTraitsDoc(obj, '', func_doc=SphinxFunctionDoc, config=config)
        if looks_like_issubclass(obj, 'HasTraits'):
            for name, trait, comment in comment_eater.get_class_traits(obj):
                # Exclude private traits.
                if not name.startswith('_'):
                    doc['Traits'].append((name, trait, comment.splitlines()))
        return doc
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, '', config=config)
    else:
        return SphinxDocString(pydoc.getdoc(obj), config=config)

def setup(app):
    # init numpydoc
    numpydoc.setup(app, get_doc_object)


########NEW FILE########
__FILENAME__ = chaos
#!python
# chaos.py
import pylab as pl
import numpy as np

# we import the fortran extension module here
import _chaos

# here is the logistic function
# this uses some advanced Python features.
# Logistic is a function that returns another function.
# This is known as a 'closure' and is a very powerful feature.
def logistic(r):
    def _inner(x):
        return r * x * (1.0 - x)
    return _inner

def sine(r):
    from math import sin, pi
    def _inner(x):
        return r * sin(pi * x)
    return _inner

def driver(func, lower, upper, N=400):
    # X will scan over the parameter value.
    X = np.linspace(lower, upper, N)
    nresults, niter = 1000, 1000
    for x in X:
        # We call the fortran function, passing the appropriate Python function.
        results = _chaos.iterate_limit(func(x), 0.5, niter, nresults)
        pl.plot([x]*len(results), results, 'k,')

if __name__ == '__main__':
    pl.figure()
    driver(logistic, 0.0, 4.0)
    pl.xlabel('r')
    pl.ylabel('X limit')
    pl.title('Logistic Map')
    pl.figure()
    driver(sine, 0.0, 1.0)
    pl.xlabel('r')
    pl.ylabel('X limit')
    pl.title('Sine Map')
    pl.show()

########NEW FILE########
__FILENAME__ = pass_args
# pass_args.py
import numpy as np
import _scalar_args

print _scalar_args.scalar_args.__doc__

# these are simple python scalars.
int_in = 1.0
real_in = 10.0

# since these are intent(inout) variables, these must be arrays
int_inout = np.zeros((1,), dtype = np.int32)
real_inout = np.zeros((1,), dtype = np.float32)

# all intent(out) variables are returned in a tuple, so they aren't passed as
# arguments.

int_out, real_out = _scalar_args.scalar_args(int_in, real_in, int_inout, real_inout)

for name in ('int_inout', 'real_inout', 'int_out', 'real_out'):
    print '%s == %s' % (name, locals()[name])

########NEW FILE########
__FILENAME__ = pass_array_args
# pass_array_args.py
import numpy as np
import _array_args

print _array_args.array_args.__doc__

# int_arr is a 10 X 10 array filled with consecutive integers.
# It is in 'fortran' order.
int_arr = np.asfortranarray(np.arange(100, dtype = 'i').reshape(10,10))

# cplx_arr is a 10 X 10 complex array filled with zeros.
# It is in 'fortran' order.
cplx_arr = np.asfortranarray(np.zeros((10,10), dtype = 'F'))

# We invoke the wrapped fortran subroutine.
real_arr = _array_args.array_args(int_arr, cplx_arr)

# Here are the results.
print "int_arr  = %s" %  int_arr
print "real_arr = %s" % real_arr
print "cplx_arr = %s" % cplx_arr

########NEW FILE########
__FILENAME__ = pytest
#File: pytest.py
import Numeric
def foo(a):
    a = Numeric.array(a)
    m,n = a.shape
    for i in range(m):
        for j in range(n):
            a[i,j] = a[i,j] + 10*(i+1) + (j+1)
    return a
#eof



########NEW FILE########
__FILENAME__ = flow_control
# Solutions to exercises for Python Flow Control 
# John Blischak
# jdblischak@gmail.com

"""
Short Exercise
Write an if statement that prints whether x is even or odd.
"""
x = 4
if x % 2 == 0:
    print 'x is even'
else:
    print 'x is odd'

"""
Short Exercise
Using a loop, calculate the factorial of 42 (the product of all integers up to and including 42).
"""
i = 1
factorial = 1
while i <= 42:
    factorial = factorial * i
    i = i + 1
print factorial

"""
Longer Exercise: Converting genotypes

Part 1:
Create a new list which has the converted genotype for each subject ('AA' -> 0, 'AG' -> 1, 'GG' -> 2).
"""
genos = ['AA', 'GG', 'AG', 'AG', 'GG']
genos_new = []
# Use your knowledge of if/else statements and loop structures below.
for i in genos:
    if i == 'AA':
        genos_new.append(0)
    elif i == 'AG':
        genos_new.append(1)
    else:
        genos_new.append(2)

"""
Part 2:
Sometimes there are errors and the genotype cannot be determined. 
Adapt your code from above to deal with this problem (in this example missing data is assigned NA for "Not Available").
"""

genos_w_missing = ['AA', 'NA', 'GG', 'AG', 'AG', 'GG', 'NA']
genos_w_missing_new = []
# The missing data should not be converted to a number, but remain 'NA' in the new list
for i in genos_w_missing:
    if i == 'NA':
        genos_w_missing_new.append(i)
    elif i == 'AA':
        genos_w_missing_new.append(0)
    elif i == 'AG':
        genos_w_missing_new.append(1)
    else:
        genos_w_missing_new.append(2)

"""
Part 3:
The file genos.txt has a column of genotypes. Read in the data and convert the genotypes as above.
Hint: You'll need to use the built-in string method strip to remove the new-line characters 
(See the example of reading in a file above. We will cover string methods in the next section).
"""
# Store the genotypes from genos.txt in this list
genos_from_file = []
handle = open("genos.txt")
for line in handle:
    i = line.strip()
    if i == 'NA':
        genos_from_file.append(i)
    elif i == 'AA':
        genos_from_file.append(0)
    elif i == 'AG':
        genos_from_file.append(1)
    else:
        genos_from_file.append(2)
handle.close()

########NEW FILE########
__FILENAME__ = functions_and_modules
# Solutions to exercises for Python Functions and Modules
# John Blischak
# jdblischak@gmail.com

#Short Exercise: Calculate GC content of DNA
# Calculate the fraction of G's and C's in this DNA sequence
seq1 = 'ACGTACGTAGCTAGTAGCTACGTAGCTACGTA'
gc = float(seq1.count('G') + seq1.count('C')) / len(seq1)

"""
Short exercise: Write a function to calculate GC content of DNA
Make a function that calculate the GC content of a given DNA sequence. For the more advanced participants, make your function able to handle sequences of mixed case (see the third test case).
"""

def calculate_gc(x):
    """Calculates the GC content of DNA sequence x.
    x: a string composed only of A's, T's, G's, and C's."""
    x = x.upper()
    return float(x.count('G') + x.count('C')) / (x.count('G') + x.count('C') + x.count('A') + x.count('T'))

"""
Longer exercise: Reading Cochlear implant into Python

Part 1:
Write a function `view_cochlear` that will open the file and print out each line. The only input to the function should be the name of the file as a string. 
"""
def view_cochlear(filename):
    """Reads in data file and prints to console.
    Input: Filename as string.
    """
    x = open(filename)
    for line in x:
        print line.strip()
    x.close()

"""
Part 2:
Adapt your function above to exclude the first line using the flow control techniques we learned in the last lesson. The first line is just `#` (but don't forget to remove the `'\n'`).
"""
def view_cochlear(filename):
    """Reads in data file and prints to console, skipping the first line.
    Input: Filename as string.
    """
    x = open(filename)
    for line in x:
        if line.strip() == '#':
            continue
        else:
            print line.strip()
    x.close()

"""
Part 3:
Adapt your function above to return a dictionary containing the contents of the file. Split each line of the file by a colon followed by a space (': '). The first half of the string should be the key of the dictionary, and the second half should be the value of the dictionary.
"""
def save_cochlear(filename):
    """Reads in data file and saves data.
    Input: Filename as string.
    Output: A dictionary of the data.
    """
    d = {}
    x = open(filename)
    for line in x:
        if line.strip() == '#':
            continue
        else:
            parsed = line.strip().split(': ')
            d[parsed[0]] = parsed[1]
    x.close()
    return d
    
"""
Bonus exercise: Convert DNA to RNA
Write a function that mimics transcription. The input argument is a string that contains the letters A, T, G, and C.
Create a new string following these rules: 
* Convert A to U
* Convert T to A
* Convert G to C
* Convert C to G
Hint: You can iterate through a string using a for loop similary to how you loop through a list.
"""
def transcribe(seq):
    """Transcribes a DNA sequence to RNA.
    Input: string of A's, T's, G's, and C's
    Output: string of RNA basd on input DNA.
    Converts using the following rules:
    A->U, T->A, G->C, C->G
    """
    rna = ''
    for letter in seq:
        if letter == 'A':
            rna = rna + 'U'
        elif letter == 'T':
            rna = rna + 'A'
        elif letter == 'G':
            rna = rna + 'C'
        else:
            rna = rna + 'G'
    return rna

########NEW FILE########
__FILENAME__ = ipythonblocks
"""
ipythonblocks provides a BlockGrid class that displays a colored grid in the
IPython Notebook. The colors can be manipulated, making it useful for
practicing control flow stuctures and quickly seeing the results.

"""

# This file is copyright 2013 by Matt Davis and covered by the license at
# https://github.com/jiffyclub/ipythonblocks/blob/master/LICENSE.txt

import copy
import itertools
import numbers
import os
import sys
import time
import uuid

from operator import iadd

from IPython.display import HTML, display, clear_output

if sys.version_info[0] >= 3:
    xrange = range
    from functools import reduce

__all__ = ('Block', 'BlockGrid', 'Pixel', 'ImageGrid',
           'InvalidColorSpec', 'show_color', 'embed_colorpicker',
           'colors', '__version__')
__version__ = '1.5'

_TABLE = ('<style type="text/css">'
          'table.blockgrid {{border: none;}}'
          ' .blockgrid tr {{border: none;}}'
          ' .blockgrid td {{padding: 0px;}}'
          ' #blocks{0} td {{border: {1}px solid white;}}'
          '</style>'
          '<table id="blocks{0}" class="blockgrid"><tbody>{2}</tbody></table>')
_TR = '<tr>{0}</tr>'
_TD = ('<td title="{0}" style="width: {1}px; height: {1}px;'
       'background-color: {2};"></td>')
_RGB = 'rgb({0}, {1}, {2})'
_TITLE = 'Index: [{0}, {1}]&#10;Color: ({2}, {3}, {4})'

_SINGLE_ITEM = 'single item'
_SINGLE_ROW = 'single row'
_ROW_SLICE = 'row slice'
_DOUBLE_SLICE = 'double slice'

_SMALLEST_BLOCK = 1

_SLEEP_TIME = 0.2


class InvalidColorSpec(Exception):
    """
    Error for a color value that is not a number.

    """
    pass


def show_color(red, green, blue):
    """
    Show a given color in the IPython Notebook.

    Parameters
    ----------
    red, green, blue : int
        Integers on the range [0 - 255].

    """
    div = ('<div style="height: 60px; min-width: 200px; '
           'background-color: {0}"></div>')
    display(HTML(div.format(_RGB.format(red, green, blue))))


def embed_colorpicker():
    """
    Embed the web page www.colorpicker.com inside the IPython Notebook.

    """
    iframe = ('<iframe src="http://www.colorpicker.com/" '
              'width="100%" height="550px"></iframe>')
    display(HTML(iframe))


class Block(object):
    """
    A colored square.

    Parameters
    ----------
    red, green, blue : int
        Integers on the range [0 - 255].
    size : int, optional
        Length of the sides of this block in pixels. One is the lower limit.

    Attributes
    ----------
    red, green, blue : int
        The color values for this `Block`. The color of the `Block` can be
        updated by assigning new values to these attributes.
    rgb : tuple of int
        Tuple of (red, green, blue) values. Can be used to set all the colors
        at once.
    row, col : int
        The zero-based grid position of this `Block`.
    size : int
        Length of the sides of this block in pixels. The block size can be
        changed by modifying this attribute. Note that one is the lower limit.

    """

    def __init__(self, red, green, blue, size=20):
        self.red = red
        self.green = green
        self.blue = blue
        self.size = size

        self._row = None
        self._col = None

    @staticmethod
    def _check_value(value):
        """
        Check that a value is a number and constrain it to [0 - 255].

        """
        if not isinstance(value, numbers.Number):
            s = 'value must be a number. got {0}.'.format(value)
            raise InvalidColorSpec(s)

        return int(round(min(255, max(0, value))))

    @property
    def red(self):
        return self._red

    @red.setter
    def red(self, value):
        value = self._check_value(value)
        self._red = value

    @property
    def green(self):
        return self._green

    @green.setter
    def green(self, value):
        value = self._check_value(value)
        self._green = value

    @property
    def blue(self):
        return self._blue

    @blue.setter
    def blue(self, value):
        value = self._check_value(value)
        self._blue = value

    @property
    def rgb(self):
        return (self._red, self._green, self._blue)

    @rgb.setter
    def rgb(self, colors):
        if len(colors) != 3:
            s = 'Setting colors requires three values: (red, green, blue).'
            raise ValueError(s)

        self.red, self.green, self.blue = colors

    @property
    def row(self):
        return self._row

    @property
    def col(self):
        return self._col

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = max(_SMALLEST_BLOCK, size)

    def set_colors(self, red, green, blue):
        """
        Updated block colors.

        Parameters
        ----------
        red, green, blue : int
            Integers on the range [0 - 255].

        """
        self.red = red
        self.green = green
        self.blue = blue

    @property
    def _td(self):
        """
        The HTML for a table cell with the background color of this Block.

        """
        title = _TITLE.format(self._row, self._col,
                              self._red, self._green, self._blue)
        rgb = _RGB.format(self._red, self._green, self._blue)
        return _TD.format(title, self._size, rgb)

    def _repr_html_(self):
        return _TABLE.format(uuid.uuid4(), 0, _TR.format(self._td))

    def show(self):
        display(HTML(self._repr_html_()))

    def __str__(self):
        s = ['{0}'.format(self.__class__.__name__),
             'Color: ({0}, {1}, {2})'.format(self._red,
                                             self._green,
                                             self._blue)]

        # add position information if we have it
        if self._row is not None:
            s[0] += ' [{0}, {1}]'.format(self._row, self._col)

        return os.linesep.join(s)


class BlockGrid(object):
    """
    A grid of blocks whose colors can be individually controlled.

    Parameters
    ----------
    width : int
        Number of blocks wide to make the grid.
    height : int
        Number of blocks high to make the grid.
    fill : tuple of int, optional
        An optional initial color for the grid, defaults to black.
        Specified as a tuple of (red, green, blue). E.g.: (10, 234, 198)
    block_size : int, optional
        Length of the sides of grid blocks in pixels. One is the lower limit.
    lines_on : bool, optional
        Whether or not to display lines between blocks.

    Attributes
    ----------
    width : int
        Number of blocks along the width of the grid.
    height : int
        Number of blocks along the height of the grid.
    shape : tuple of int
        A tuple of (width, height).
    block_size : int
        Length of the sides of grid blocks in pixels. The block size can be
        changed by modifying this attribute. Note that one is the lower limit.
    lines_on : bool
        Whether lines are shown between blocks when the grid is displayed.
        This attribute can used to toggle the whether the lines appear.

    """

    def __init__(self, width, height, fill=(0, 0, 0),
                 block_size=20, lines_on=True):
        self._width = width
        self._height = height
        self._block_size = block_size
        self.lines_on = lines_on
        self._initialize_grid(fill)

    def _initialize_grid(self, fill):
        grid = [[Block(*fill, size=self._block_size)
                for col in xrange(self.width)]
                for row in xrange(self.height)]

        self._grid = grid

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def shape(self):
        return (self._width, self._height)

    @property
    def block_size(self):
        return self._block_size

    @block_size.setter
    def block_size(self, size):
        self._block_size = size

        for block in self:
            block.size = size

    @property
    def lines_on(self):
        return self._lines_on

    @lines_on.setter
    def lines_on(self, value):
        if value not in (0, 1):
            s = 'lines_on may only be True or False.'
            raise ValueError(s)

        self._lines_on = value

    @classmethod
    def _view_from_grid(cls, grid):
        """
        Make a new grid from a list of lists of Block objects.

        """
        new_width = len(grid[0])
        new_height = len(grid)

        new_BG = cls(new_width, new_height)
        new_BG._grid = grid

        return new_BG

    @staticmethod
    def _categorize_index(index):
        """
        Used by __getitem__ and __setitem__ to determine whether the user
        is asking for a single item, single row, or some kind of slice.

        """
        if isinstance(index, int):
            return _SINGLE_ROW

        elif isinstance(index, slice):
            return _ROW_SLICE

        elif isinstance(index, tuple):
            if len(index) > 2:
                s = 'Invalid index, too many dimensions.'
                raise IndexError(s)

            elif len(index) == 1:
                s = 'Single indices must be integers, not tuple.'
                raise TypeError(s)

            if isinstance(index[0], slice):
                if isinstance(index[1], (int, slice)):
                    return _DOUBLE_SLICE

            if isinstance(index[1], slice):
                if isinstance(index[0], (int, slice)):
                    return _DOUBLE_SLICE

            elif isinstance(index[0], int) and isinstance(index[0], int):
                return _SINGLE_ITEM

        raise IndexError('Invalid index.')

    def __getitem__(self, index):
        ind_cat = self._categorize_index(index)

        if ind_cat == _SINGLE_ROW:
            return self._view_from_grid([self._grid[index]])

        elif ind_cat == _SINGLE_ITEM:
            block = self._grid[index[0]][index[1]]
            block._row, block._col = index
            return block

        elif ind_cat == _ROW_SLICE:
            return self._view_from_grid(self._grid[index])

        elif ind_cat == _DOUBLE_SLICE:
            new_grid = self._get_double_slice(index)
            return self._view_from_grid(new_grid)

    def __setitem__(self, index, value):
        if len(value) != 3:
            s = 'Assigned value must have three integers. got {0}.'
            raise ValueError(s.format(value))

        ind_cat = self._categorize_index(index)

        if ind_cat == _SINGLE_ROW:
            map(lambda b: b.set_colors(*value), self._grid[index])

        elif ind_cat == _SINGLE_ITEM:
            self._grid[index[0]][index[1]].set_colors(*value)

        else:
            if ind_cat == _ROW_SLICE:
                sub_grid = self._grid[index]

            elif ind_cat == _DOUBLE_SLICE:
                sub_grid = self._get_double_slice(index)

            map(lambda b: b.set_colors(*value), itertools.chain(*sub_grid))

    def _get_double_slice(self, index):
        sl_height, sl_width = index

        if isinstance(sl_width, int):
            if sl_width == -1:
                sl_width = slice(sl_width, None)
            else:
                sl_width = slice(sl_width, sl_width + 1)

        if isinstance(sl_height, int):
            if sl_height == -1:
                sl_height = slice(sl_height, None)
            else:
                sl_height = slice(sl_height, sl_height + 1)

        rows = self._grid[sl_height]
        grid = [r[sl_width] for r in rows]

        return grid

    def __iter__(self):
        for r in xrange(self.height):
            for c in xrange(self.width):
                yield self[r, c]

    @property
    def animate(self):
        """
        Iterate over this property to have your changes to the grid
        animated in the IPython Notebook.

        """
        for block in self:
            self.show()
            time.sleep(_SLEEP_TIME)
            yield block
            clear_output()
        self.show()

    def _repr_html_(self):
        rows = range(self._height)
        cols = range(self._width)

        html = reduce(iadd,
                      (_TR.format(reduce(iadd,
                                         (self[r, c]._td
                                          for c in cols)))
                       for r in rows))

        return _TABLE.format(uuid.uuid4(), int(self._lines_on), html)

    def __str__(self):
        s = ['{0}'.format(self.__class__.__name__),
             'Shape: {0}'.format(self.shape)]

        return os.linesep.join(s)

    def copy(self):
        """
        Returns an independent copy of this BlockGrid.

        """
        return copy.deepcopy(self)

    def show(self):
        """
        Display colored grid as an HTML table.

        """
        display(HTML(self._repr_html_()))

    def flash(self):
        """
        Display the grid for a short time. Useful for making an animation.

        """
        self.show()
        time.sleep(_SLEEP_TIME)
        clear_output()

    def to_text(self, filename=None):
        """
        Write a text file containing the size and block color information
        for this grid.

        If no file name is given the text is sent to stdout.

        Parameters
        ----------
        filename : str, optional
            File into which data will be written. Will be overwritten if
            it already exists.

        """
        if filename:
            f = open(filename, 'w')
        else:
            f = sys.stdout

        s = ['# width height', '{0} {1}'.format(self.width, self.height),
             '# block size', '{0}'.format(self.block_size),
             '# initial color', '0 0 0',
             '# row column red green blue']
        f.write(os.linesep.join(s) + os.linesep)

        for block in self:
            things = [str(x) for x in (block.row, block.col) + block.rgb]
            f.write(' '.join(things) + os.linesep)

        if filename:
            f.close()


class Pixel(Block):
    @property
    def x(self):
        """
        Horizontal coordinate of Pixel.

        """
        return self._col

    @property
    def y(self):
        """
        Vertical coordinate of Pixel.

        """
        return self._row

    @property
    def _td(self):
        """
        The HTML for a table cell with the background color of this Pixel.

        """
        title = _TITLE.format(self._col, self._row,
                              self._red, self._green, self._blue)
        rgb = _RGB.format(self._red, self._green, self._blue)
        return _TD.format(title, self._size, rgb)

    def __str__(self):
        s = ['{0}'.format(self.__class__.__name__),
             'Color: ({0}, {1}, {2})'.format(self._red,
                                             self._green,
                                             self._blue)]

        # add position information if we have it
        if self._row is not None:
            s[0] += ' [{0}, {1}]'.format(self._col, self._row)

        return os.linesep.join(s)


class ImageGrid(BlockGrid):
    """
    A grid of blocks whose colors can be individually controlled.

    Parameters
    ----------
    width : int
        Number of blocks wide to make the grid.
    height : int
        Number of blocks high to make the grid.
    fill : tuple of int, optional
        An optional initial color for the grid, defaults to black.
        Specified as a tuple of (red, green, blue). E.g.: (10, 234, 198)
    block_size : int, optional
        Length of the sides of grid blocks in pixels. One is the lower limit.
    lines_on : bool, optional
        Whether or not to display lines between blocks.
    origin : {'lower-left', 'upper-left'}
        Set the location of the grid origin.

    Attributes
    ----------
    width : int
        Number of blocks along the width of the grid.
    height : int
        Number of blocks along the height of the grid.
    shape : tuple of int
        A tuple of (width, height).
    block_size : int
        Length of the sides of grid blocks in pixels.
    lines_on : bool
        Whether lines are shown between blocks when the grid is displayed.
        This attribute can used to toggle the whether the lines appear.
    origin : str
        The location of the grid origin.

    """

    def __init__(self, width, height, fill=(0, 0, 0),
                 block_size=20, lines_on=True, origin='lower-left'):
        super(ImageGrid, self).__init__(width, height, fill,
                                        block_size, lines_on)

        if origin not in ('lower-left', 'upper-left'):
            s = "origin keyword must be one of {'lower-left', 'upper-left'}."
            raise ValueError(s)

        self._origin = origin

    def _initialize_grid(self, fill):
        grid = [[Pixel(*fill, size=self._block_size)
                for col in xrange(self.width)]
                for row in xrange(self.height)]

        self._grid = grid

    @property
    def block_size(self):
        return self._block_size

    @property
    def origin(self):
        return self._origin

    def _transform_index(self, index):
        """
        Transform a single-item index from Python style coordinates to
        image style coordinates in which the first item refers to column and
        the second item refers to row. Also takes into account the
        location of the origin.

        """
        # in ImageGrid index is guaranteed to be a tuple.

        # first thing, switch the coordinates since ImageGrid is column
        # major and ._grid is row major.
        new_ind = [index[1], index[0]]

        # now take into account that the ImageGrid origin may be lower-left,
        # while the ._grid origin is upper-left.
        if self._origin == 'lower-left':
            new_ind[0] = self._height - new_ind[0] - 1

        return tuple(new_ind)

    def __getitem__(self, index):
        ind_cat = self._categorize_index(index)

        # ImageGrid will only support single item indexing and 2D slices
        if ind_cat not in (_DOUBLE_SLICE, _SINGLE_ITEM):
            s = 'ImageGrid only supports 2D indexing.'
            raise IndexError(s)

        if ind_cat == _SINGLE_ITEM:
            real_index = self._transform_index(index)
            pixel = self._grid[real_index[0]][real_index[1]]
            pixel._col, pixel._row = index
            return pixel

        elif ind_cat == _DOUBLE_SLICE:
            new_grid = self._get_double_slice(index)
            return self._view_from_grid(new_grid)

    def __setitem__(self, index, value):
        if len(value) != 3:
            s = 'Assigned value must have three integers. got {0}.'
            raise ValueError(s.format(value))

        pixels = self[index]

        if isinstance(pixels, Pixel):
            pixels.set_colors(*value)

        else:
            map(lambda p: p.set_colors(*value), itertools.chain(*pixels._grid))

    def _get_double_slice(self, index):
        cslice, rslice = index

        if isinstance(rslice, int):
            if rslice == -1:
                rslice = slice(rslice, None)
            else:
                rslice = slice(rslice, rslice + 1)

        if isinstance(cslice, int):
            if cslice == -1:
                cslice = slice(cslice, None)
            else:
                cslice = slice(cslice, cslice + 1)

        rows = range(self._height)[rslice]
        if self._origin == 'lower-left':
            rows = rows[::-1]

        cols = range(self._width)[cslice]

        new_grid = [[self[c, r] for c in cols] for r in rows]

        return new_grid

    def __iter__(self):
        for col in xrange(self.width):
            for row in xrange(self.height):
                yield self[col, row]

    def _repr_html_(self):
        rows = range(self._height)
        cols = range(self._width)

        if self._origin == 'lower-left':
            rows = rows[::-1]

        html = reduce(iadd,
                      (_TR.format(reduce(iadd,
                                         (self[c, r]._td
                                          for c in cols)))
                       for r in rows))

        return _TABLE.format(uuid.uuid4(), int(self._lines_on), html)


# As a convenience, provide the named HTML colors as a dictionary.
colors = \
    {'AliceBlue': (240, 248, 255),
     'AntiqueWhite': (250, 235, 215),
     'Aqua': (0, 255, 255),
     'Aquamarine': (127, 255, 212),
     'Azure': (240, 255, 255),
     'Beige': (245, 245, 220),
     'Bisque': (255, 228, 196),
     'Black': (0, 0, 0),
     'BlanchedAlmond': (255, 235, 205),
     'Blue': (0, 0, 255),
     'BlueViolet': (138, 43, 226),
     'Brown': (165, 42, 42),
     'BurlyWood': (222, 184, 135),
     'CadetBlue': (95, 158, 160),
     'Chartreuse': (127, 255, 0),
     'Chocolate': (210, 105, 30),
     'Coral': (255, 127, 80),
     'CornflowerBlue': (100, 149, 237),
     'Cornsilk': (255, 248, 220),
     'Crimson': (220, 20, 60),
     'Cyan': (0, 255, 255),
     'DarkBlue': (0, 0, 139),
     'DarkCyan': (0, 139, 139),
     'DarkGoldenrod': (184, 134, 11),
     'DarkGray': (169, 169, 169),
     'DarkGreen': (0, 100, 0),
     'DarkKhaki': (189, 183, 107),
     'DarkMagenta': (139, 0, 139),
     'DarkOliveGreen': (85, 107, 47),
     'DarkOrange': (255, 140, 0),
     'DarkOrchid': (153, 50, 204),
     'DarkRed': (139, 0, 0),
     'DarkSalmon': (233, 150, 122),
     'DarkSeaGreen': (143, 188, 143),
     'DarkSlateBlue': (72, 61, 139),
     'DarkSlateGray': (47, 79, 79),
     'DarkTurquoise': (0, 206, 209),
     'DarkViolet': (148, 0, 211),
     'DeepPink': (255, 20, 147),
     'DeepSkyBlue': (0, 191, 255),
     'DimGray': (105, 105, 105),
     'DodgerBlue': (30, 144, 255),
     'FireBrick': (178, 34, 34),
     'FloralWhite': (255, 250, 240),
     'ForestGreen': (34, 139, 34),
     'Fuchsia': (255, 0, 255),
     'Gainsboro': (220, 220, 220),
     'GhostWhite': (248, 248, 255),
     'Gold': (255, 215, 0),
     'Goldenrod': (218, 165, 32),
     'Gray': (128, 128, 128),
     'Green': (0, 128, 0),
     'GreenYellow': (173, 255, 47),
     'Honeydew': (240, 255, 240),
     'HotPink': (255, 105, 180),
     'IndianRed': (205, 92, 92),
     'Indigo': (75, 0, 130),
     'Ivory': (255, 255, 240),
     'Khaki': (240, 230, 140),
     'Lavender': (230, 230, 250),
     'LavenderBlush': (255, 240, 245),
     'LawnGreen': (124, 252, 0),
     'LemonChiffon': (255, 250, 205),
     'LightBlue': (173, 216, 230),
     'LightCoral': (240, 128, 128),
     'LightCyan': (224, 255, 255),
     'LightGoldenrodYellow': (250, 250, 210),
     'LightGray': (211, 211, 211),
     'LightGreen': (144, 238, 144),
     'LightPink': (255, 182, 193),
     'LightSalmon': (255, 160, 122),
     'LightSeaGreen': (32, 178, 170),
     'LightSkyBlue': (135, 206, 250),
     'LightSlateGray': (119, 136, 153),
     'LightSteelBlue': (176, 196, 222),
     'LightYellow': (255, 255, 224),
     'Lime': (0, 255, 0),
     'LimeGreen': (50, 205, 50),
     'Linen': (250, 240, 230),
     'Magenta': (255, 0, 255),
     'Maroon': (128, 0, 0),
     'MediumAquamarine': (102, 205, 170),
     'MediumBlue': (0, 0, 205),
     'MediumOrchid': (186, 85, 211),
     'MediumPurple': (147, 112, 219),
     'MediumSeaGreen': (60, 179, 113),
     'MediumSlateBlue': (123, 104, 238),
     'MediumSpringGreen': (0, 250, 154),
     'MediumTurquoise': (72, 209, 204),
     'MediumVioletRed': (199, 21, 133),
     'MidnightBlue': (25, 25, 112),
     'MintCream': (245, 255, 250),
     'MistyRose': (255, 228, 225),
     'Moccasin': (255, 228, 181),
     'NavajoWhite': (255, 222, 173),
     'Navy': (0, 0, 128),
     'OldLace': (253, 245, 230),
     'Olive': (128, 128, 0),
     'OliveDrab': (107, 142, 35),
     'Orange': (255, 165, 0),
     'OrangeRed': (255, 69, 0),
     'Orchid': (218, 112, 214),
     'PaleGoldenrod': (238, 232, 170),
     'PaleGreen': (152, 251, 152),
     'PaleTurquoise': (175, 238, 238),
     'PaleVioletRed': (219, 112, 147),
     'PapayaWhip': (255, 239, 213),
     'PeachPuff': (255, 218, 185),
     'Peru': (205, 133, 63),
     'Pink': (255, 192, 203),
     'Plum': (221, 160, 221),
     'PowderBlue': (176, 224, 230),
     'Purple': (128, 0, 128),
     'Red': (255, 0, 0),
     'RosyBrown': (188, 143, 143),
     'RoyalBlue': (65, 105, 225),
     'SaddleBrown': (139, 69, 19),
     'Salmon': (250, 128, 114),
     'SandyBrown': (244, 164, 96),
     'SeaGreen': (46, 139, 87),
     'Seashell': (255, 245, 238),
     'Sienna': (160, 82, 45),
     'Silver': (192, 192, 192),
     'SkyBlue': (135, 206, 235),
     'SlateBlue': (106, 90, 205),
     'SlateGray': (112, 128, 144),
     'Snow': (255, 250, 250),
     'SpringGreen': (0, 255, 127),
     'SteelBlue': (70, 130, 180),
     'Tan': (210, 180, 140),
     'Teal': (0, 128, 128),
     'Thistle': (216, 191, 216),
     'Tomato': (255, 99, 71),
     'Turquoise': (64, 224, 208),
     'Violet': (238, 130, 238),
     'Wheat': (245, 222, 179),
     'White': (255, 255, 255),
     'WhiteSmoke': (245, 245, 245),
     'Yellow': (255, 255, 0),
     'YellowGreen': (154, 205, 50)}

########NEW FILE########
__FILENAME__ = make_img
import numpy as np
import pylab
import pdb


#read in the image
img = np.genfromtxt('spec_example.dat')
ax_img = pylab.axes([0.1, 0.1, 0.65, 0.8]) #[left, bottom, width, height]
ax_plot = pylab.axes([0.77, 0.1, 0.13, 0.8])




#Display the image
ax_img.imshow(img, origin = 'lower', interpolation = 'nearest')

#Collapse the spectrum along x axis
img_collapse = np.sum(img, axis = 1)
#create and array to plot against
y = np.arange(img_collapse.shape[0])

#Plot to new axis
ax_plot.plot(img_collapse, y, 'k', lw = 2)
ax_plot.set_ylim(ax_img.get_ylim())

########NEW FILE########
__FILENAME__ = recommend
'''
Original example from Toby Segaran: "Programming Collective Intelligence"
Altered by Richard T. Guy (2010)
'''

from math import sqrt
import numpy

EPS = 1.0e-9 # Never use == for floats.

raw_scores = {

  'Bhargan Basepair' : {
    'Jackson 1999' : 2.5,
    'Chen 2002' : 3.5,
    'Rollins and Khersau 2002' : 3.0,
    'El Awy 2005' : 3.5,
    'Chen 2008' : 2.5,
    'Falkirk et al 2006' : 3.0
  },

  'Fan Fullerene' : {
    'Jackson 1999' : 3.0,
    'Chen 2002' : 3.5,
    'Rollins and Khersau 2002' : 1.5,
    'El Awy 2005' : 5.0,
    'Falkirk et al 2006' : 3.0,
    'Chen 2008' : 3.5
  },

  'Helen Helmet' : {
    'Jackson 1999' : 2.5,
    'Chen 2002' : 3.0,
    'El Awy 2005' : 3.5,
    'Falkirk et al 2006' : 4.0
  },

  'Mehrdad Mapping' : {
    'Chen 2002' : 3.5,
    'Rollins and Khersau 2002' : 3.0,
    'Falkirk et al 2006' : 4.5,
    'El Awy 2005' : 4.0,
    'Chen 2008' : 2.5
  },

  'Miguel Monopole' : {
    'Jackson 1999' : 3.0,
    'Chen 2002' : 4.0,
    'Rollins and Khersau 2002' : 2.0,
    'El Awy 2005' : 3.0,
    'Falkirk et al 2006' : 3.0,
    'Chen 2008' : 2.0
  },

  'Gail Graphics' : {
    'Jackson 1999' : 3.0,
    'Chen 2002' : 4.0,
    'Falkirk et al 2006' : 3.0,
    'El Awy 2005' : 5.0,
    'Chen 2008' : 3.5
  },

  'Stephen Scanner' : {
    'Chen 2002' :4.5,
    'Chen 2008' :1.0,
    'El Awy 2005' :4.0
  }
}

def prep_data(all_scores):
  '''
  Turn {person : {title : score, ...} ...} into NumPy array.
  Each row is a person, each column is a paper title.
  Note that input data is sparse (does not contain all person X paper pairs).
  '''

  # Names of all people in alphabetical order.
  people = all_scores.keys()
  people.sort()

  # Names of all papers in alphabetical order.
  papers = set()
  for person in people:
    for title in all_scores[person].keys():
      papers.add(title)
  papers = list(papers)
  papers.sort()

  # Create and fill array.
  ratings = numpy.zeros((len(people), len(papers)))
  for (person_id, person) in enumerate(people):
    for (title_id, title) in enumerate(papers):
      rating = all_scores[person].get(title, 0)
      ratings[person_id, title_id] = float(rating)

  return people, papers, ratings

def sim_distance(prefs, left_index, right_index):
  '''
  Calculate distance-based similarity score for two people.
  Prefs is array[person X paper].

  Calculated a similarity difference btween two people (rows),
  which is 0 if they have no preferences in common.
  '''

  # Where do both people have preferences?
  left_has_prefs = prefs[left_index, :] > 0
  right_has_prefs = prefs[right_index, :] > 0
  mask = numpy.logical_and(left_has_prefs, right_has_prefs)

  # Not enough signal.
  if numpy.sum(mask) < EPS:
    return 0

  # Return sum-of-squares distance.
  diff = prefs[left_index, mask] - prefs[right_index, mask]
  sum_of_squares = numpy.linalg.norm(diff) ** 2
  result = 1. / (1. + sum_of_squares)
  return result

def sim_pearson(prefs, left_index, right_index):
  '''
  Calculate Pearson correlation between two individuals.
  '''

  # Where do both have ratings?
  rating_left = prefs[left_index, :]
  rating_right = prefs[right_index, :]
  mask = numpy.logical_and(rating_left > 0, rating_right > 0)

  # Note that summing over Booleans gives number of Trues
  num_common = sum(mask)

  # Return zero if there are no common ratings.
  if num_common == 0:
    return 0

  # Calculate Pearson score "r"
  varcovar = numpy.cov(rating_left[mask], rating_right[mask])
  numerator = varcovar[0,1]

  denominator = sqrt(varcovar[0,0]) * sqrt(varcovar[1,1])

  if denominator < EPS:
    return 0

  r = numerator / denominator
  return r

def top_matches(ratings, person, num, sim_func):
  '''
  Return the most similar individuals to a person.
  '''

  scores = []
  for other in range(ratings.shape[0]):
    if other != person:
      scores.append((sim_func(ratings, person, other), other))

  scores.sort()
  scores.reverse()
  return scores[0:num]

def calculate_similar(paper_ids, ratings, num=10):
  '''
  Find the papers that are most similar to each other.
  '''

  result = {}
  ratings_by_paper = ratings.T
  for item in range(ratings_by_paper.shape[0]):
    unnamed_scores = top_matches(ratings_by_paper, item, num, sim_distance)
    scores = [(x[0], paper_ids[x[1]]) for x in unnamed_scores]
    result[paper_ids[item]] = scores

  return result

def recommend(prefs, subject, sim_func):
  '''
  Get recommendations for an individual from a weighted average of other people.
  '''

  totals = {}
  sim_sums = {}
  num_people = prefs.shape[0]
  num_papers = prefs.shape[1]

  for other in range(num_people):

    # Don't compare people to themselves.
    if other == subject:
      continue
    sim = sim_func(prefs, subject, other)

    # ignore scores of zero or lower
    if sim < EPS:
      continue

    for title in range(num_papers):
      
      # Only score papers this person hasn't seen yet.
      if prefs[subject, title] < EPS and prefs[other, title] > EPS:
        
        # Similarity * Score
        if title in totals:
          totals[title] += prefs[other, title] * sim
        else:
          totals[title] = 0

        # Sum of similarities
        if title in sim_sums():
          sim_sums[title] += sim
        else:
          sim_sums[title] = 0

  # Create the normalized list
  
  rankings = []
  for title, total in totals.items():
    rankings.append((total/sim_sums[title], title))

  # Return the sorted list
  rankings.sort()
  rankings.reverse()
  return rankings

def test():
  person_ids, paper_ids, all_ratings = prep_data(raw_scores)
  print 'person_ids', person_ids
  print 'paper_ids', paper_ids
  print 'all_ratings', all_ratings
  print 'similarity distance', sim_distance(all_ratings, 0, 1)
  print 'similarity Pearson', sim_pearson(all_ratings, 0, 1)
  print top_matches(all_ratings, 0, 5, sim_pearson)
  print calculate_similar(paper_ids, all_ratings)
  print recommend(all_ratings, 0, sim_distance)
  print recommend(all_ratings, 1, sim_distance)
	
if __name__ == '__main__':
  test()

########NEW FILE########
__FILENAME__ = segaran-recommend
# A dictionary of movie critics and their ratings of a small
# set of movies
critics={'Lisa Rose': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
 'The Night Listener': 3.0},
'Gene Seymour': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
 'You, Me and Dupree': 3.5}, 
'Michael Phillips': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
 'Superman Returns': 3.5, 'The Night Listener': 4.0},
'Claudia Puig': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
 'You, Me and Dupree': 2.5},
'Mick LaSalle': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
 'You, Me and Dupree': 2.0}, 
'Jack Matthews': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
'Toby': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0}}


from math import sqrt

# Returns a distance-based similarity score for person1 and person2
def sim_distance(prefs,person1,person2):
  # Get the list of shared_items
  si={}
  for item in prefs[person1]: 
    if item in prefs[person2]: si[item]=1

  # if they have no ratings in common, return 0
  if len(si)==0: return 0

  # Add up the squares of all the differences
  sum_of_squares=sum([pow(prefs[person1][item]-prefs[person2][item],2) 
                      for item in prefs[person1] if item in prefs[person2]])

  return 1/(1+sum_of_squares)

# Returns the Pearson correlation coefficient for p1 and p2
def sim_pearson(prefs,p1,p2):
  # Get the list of mutually rated items
  si={}
  for item in prefs[p1]: 
    if item in prefs[p2]: si[item]=1

  # if they are no ratings in common, return 0
  if len(si)==0: return 0

  # Sum calculations
  n=len(si)
  
  # Sums of all the preferences
  sum1=sum([prefs[p1][it] for it in si])
  sum2=sum([prefs[p2][it] for it in si])
  
  # Sums of the squares
  sum1Sq=sum([pow(prefs[p1][it],2) for it in si])
  sum2Sq=sum([pow(prefs[p2][it],2) for it in si])	
  
  # Sum of the products
  pSum=sum([prefs[p1][it]*prefs[p2][it] for it in si])
  
  # Calculate r (Pearson score)
  num=pSum-(sum1*sum2/n)
  den=sqrt((sum1Sq-pow(sum1,2)/n)*(sum2Sq-pow(sum2,2)/n))
  if den==0: return 0

  r=num/den

  return r

# Returns the best matches for person from the prefs dictionary. 
# Number of results and similarity function are optional params.
def topMatches(prefs,person,n=5,similarity=sim_pearson):
  scores=[(similarity(prefs,person,other),other) 
                  for other in prefs if other!=person]
  scores.sort()
  scores.reverse()
  return scores[0:n]

# Gets recommendations for a person by using a weighted average
# of every other user's rankings
def getRecommendations(prefs,person,similarity=sim_pearson):
  totals={}
  simSums={}
  for other in prefs:
    # don't compare me to myself
    if other==person: continue
    sim=similarity(prefs,person,other)

    # ignore scores of zero or lower
    if sim<=0: continue
    for item in prefs[other]:
	    
      # only score movies I haven't seen yet
      if item not in prefs[person] or prefs[person][item]==0:
        # Similarity * Score
        totals.setdefault(item,0)
        totals[item]+=prefs[other][item]*sim
        # Sum of similarities
        simSums.setdefault(item,0)
        simSums[item]+=sim

  # Create the normalized list
  rankings=[(total/simSums[item],item) for item,total in totals.items()]

  # Return the sorted list
  rankings.sort()
  rankings.reverse()
  return rankings

def transformPrefs(prefs):
  result={}
  for person in prefs:
    for item in prefs[person]:
      result.setdefault(item,{})
      
      # Flip item and person
      result[item][person]=prefs[person][item]
  return result


def calculateSimilarItems(prefs,n=10):
  # Create a dictionary of items showing which other items they
  # are most similar to.
  result={}
  # Invert the preference matrix to be item-centric
  itemPrefs=transformPrefs(prefs)
  c=0
  for item in itemPrefs:
    # Status updates for large datasets
    c+=1
    if c%100==0: print "%d / %d" % (c,len(itemPrefs))
    # Find the most similar items to this one
    scores=topMatches(itemPrefs,item,n=n,similarity=sim_distance)
    result[item]=scores
  return result

def getRecommendedItems(prefs,itemMatch,user):
  userRatings=prefs[user]
  scores={}
  totalSim={}
  # Loop over items rated by this user
  for (item,rating) in userRatings.items( ):

    # Loop over items similar to this one
    for (similarity,item2) in itemMatch[item]:

      # Ignore if this user has already rated this item
      if item2 in userRatings: continue
      # Weighted sum of rating times similarity
      scores.setdefault(item2,0)
      scores[item2]+=similarity*rating
      # Sum of all the similarities
      totalSim.setdefault(item2,0)
      totalSim[item2]+=similarity

  # Divide each total score by total weighting to get an average
  rankings=[(score/totalSim[item],item) for item,score in scores.items( )]

  # Return the rankings from highest to lowest
  rankings.sort( )
  rankings.reverse( )
  return rankings

def loadMovieLens(path='/data/movielens'):
  # Get movie titles
  movies={}
  for line in open(path+'/u.item'):
    (id,title)=line.split('|')[0:2]
    movies[id]=title
  
  # Load data
  prefs={}
  for line in open(path+'/u.data'):
    (user,movieid,rating,ts)=line.split('\t')
    prefs.setdefault(user,{})
    prefs[user][movies[movieid]]=float(rating)
  return prefs

########NEW FILE########
__FILENAME__ = constants
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy constants, Crawl before you walk!

#A plethora of important fundamental constants can be found in
import scipy.constants
#NOTE: this module is not automatically included when you "import scipy"

#Some very basic pieces of information are given as module attributes
print("SciPy thinks that pi = %.16f"%scipy.constants.pi)
import math
print("While math thinks that pi = %.16f"%math.pi)
print("SciPy also thinks that the speed of light is c = %.1F"%scipy.constants.c)
print("")

#But the real value of SciPy constants is its enormous physical constant database
print("SciPy physical constants are of the form:")
print("      scipy.constants.physical_constants[name] = (value, units, uncertainty)")
print("")

print("For example the mass of an alpha particle is %s"%str(scipy.constants.physical_constants["alpha particle mass"]))
print("But buyer beware! Let's look at the speed of light again.")
print("c = %s"%str(scipy.constants.physical_constants["speed of light in vacuum"]))
print("The uncertainty in c should not be zero!")
print("")

print("Check http://docs.scipy.org/doc/scipy/reference/constants.html for a complete listing.")


########NEW FILE########
__FILENAME__ = image_tricks
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Image Tricks, fly before you....You can do that?!

#For some reason that has yet to be explained to me, SciPy has the ability to treat 2D & 3D arrays
#as images.  You can even convert PIL images or read in external files as numpy arrays!
#From here, you can fool around with the raw image data at will.  Naturally, this functionality 
#is buried within the 'miscellaneous' module.
import scipy.misc

#First let's read in an image file.  For now, make it a JPEG.
img = scipy.misc.imread("image.jpg")
#Note that this really is an array!
print(str(img))

#We can now apply some basic filters...
img = scipy.misc.imfilter(img, 'blur')

#We can even rotate the image, counter-clockwise by degrees.
img = scipy.misc.imrotate(img, 45)

#And then, we can rewrite the array to an image file.
scipy.misc.imsave("image1.jpg", img)

#Because the array takes integer values from 0 - 255, we can easily define our own filters as well!
def InverseImage(imgarr):
	return 255 - imgarr

#Starting fresh we get... 
img = scipy.misc.imread("image.jpg")
img = scipy.misc.imrotate(img, 330)
img = InverseImage(img)
scipy.misc.imsave("image2.jpg", img)

#Check out http://docs.scipy.org/doc/scipy/reference/misc.html for a complete listing.


########NEW FILE########
__FILENAME__ = integrate
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Integration, run before you glide. 

#Tools used to calculate numerical, definite integrals may be found in the 'integrate' module.
import scipy.integrate
#For kicks, let's also grab
import scipy.special
import numpy

#There are two basic ways you can integrate in SciPy:
#     1. Integrate a function, or
#     2. Integrate piecewise data.

#First Let's deal with integration of functions.
#Recall that in Python, functions are also objects.  
#Therefore you can pass functions as arguments to other functions!
#Just make sure that the function that you want to integrate returns a float, 
#or, at the very least, an object that has a __float__() method.

#The simplest way to compute a functions definite integral is via the quad(...) function.
def CrazyFunc(x):
	return (scipy.special.i1(x) - 1)**3

print("Try integrating CrazyFunc on the range [-5, 10]...")

val, err = scipy.integrate.quad(CrazyFunc, -5, 10)

print("A Crazy Function integrates to %.8E"%val)  
print("And with insanely low error of %.8E"%err)  
print("")

#You can also use scipy.integrate.Inf for infinity in the limits of integration
print("Now try integrating e^x on [-inf, 0]")
print("(val, err) = " + str( scipy.integrate.quad(scipy.exp, -scipy.integrate.Inf, 0.0) ))
print("")

#2D integrations follows similarly, 
def dA_Sphere(phi, theta):
	return  scipy.sin(phi)

print("Integrate the surface area of the unit sphere...")
val, err = scipy.integrate.dblquad(dA_Sphere, 0.0, 2.0*scipy.pi, lambda theta: 0.0,  lambda theta: scipy.pi )
print("val = %.8F"%val)
print("err = %.8E"%err)
print("")

def dV_Sphere(phi, theta, r):
	return r * r * dA_Sphere(phi, theta)

print("Integrate the volume of a sphere with r=3.5...")
val, err = scipy.integrate.tplquad(dV_Sphere, 0.0, 3.5, lambda r: 0.0, lambda r: 2.0*scipy.pi, lambda x, y: 0.0, lambda x, y: scipy.pi)
print("val = %.8F"%val)
print("err = %.8E"%err)
print("")

#Now, only very rarely will scientists (and even more rarely engineers) will truely 'know' 
#the function that they wish to integrate.  Much more often we'll have piecewise data 
#that we wish numerically integrate (ie sum an array y(x), biased by array x).  
#This can be done in SciPy through the trapz function.

y = range(0, 11)
print("Trapazoidally integrate y = x on [0,10]...")
val = scipy.integrate.trapz(y)
print("val = %F"%val)
print("")

#You can also define a domain to integrate over.
x = numpy.arange(0.0, 20.5, 0.5)
y = x * x
print("Trapazoidally integrate y = x^2 on [0,20] with half steps...")
val = scipy.integrate.trapz(y, x)
print("val = %F"%val)
print("")

print("Trapazoidally integrate y = x^2 with dx=0.5...")
val = scipy.integrate.trapz(y, dx=0.5)
print("val = %F"%val)
print("")

def dDecay(y, t, lam):
	return -lam*y

#Of course, sometimes we have simple ODEs that we want to integrate over time for...
#These are generally of the form:
#     dy / dt = f(y, t)
#For example take the decay equation...
#     f(y, t) = - lambda * y
#We can integrate this using SciPy's 'odeint'  This is of the form:
#     odeint( f, y0, [t0, t1, ...])
#Let's try it... 
vals = scipy.integrate.odeint( lambda y, t: dDecay(y, t, 0.2), 1.0, [0.0, 10.0] ) 
print("If you start with a mass of y(0) = %F"%vals[0][0])
print("you'll only have y(t=10) = %F left."%vals[1][0])

#Check out http://docs.scipy.org/doc/scipy/reference/integrate.html for a complete listing.

########NEW FILE########
__FILENAME__ = pade1
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Pade, glide before you fly!

#As you have seen, SciPy has some really neat functionality that comes stock.
#Oddly, some of the best stuff is in the 'miscelaneous' module.
import scipy.misc 

#Most people are familar with the polynomial expansions of a function:
#     f(x) = a + bx + cx^2 + ...
#Or a Taylor expansion:
#     f(x) = sum( d^n f(a) / dx^n (x-a)^n /n! )
#However, there exists the lesser known, more exact Pade approximation.
#This basically splits up a function into a numerator and a denominator.
#     f(x) = p(x) / q(x)
#Then, you can approximate p(x) and q(x) using a power series.  
#A more complete treatment is available in Section 5.12 in 'Numerical Recipes' by W. H. Press, et al.


#The stregnth of this method is demonstated though figures...
from pylab import *

#Let's expand e^x to fith order and record the coefficents 
e_exp = [1.0, 1.0, 1.0/2.0, 1.0/6.0, 1.0/24.0, 1.0/120.0]

#The Pade coefficients are given simply by, 
p, q = scipy.misc.pade(e_exp, 2)
#p and q are of numpy's polynomial class
#So the Pade approximation is given by 
def PadeAppx(x):
	return p(x) / q(x)

#Let's test it...
x = arange(0.0, 3.1, 0.1)

e_exp.reverse()
e_poly = poly1d(e_exp)

plot(x, PadeAppx(x), 'k--', label="Pade Approximation")
plot(x, scipy.e**x, 'k-', label=r'$e^x$')
plot(x, e_poly(x), 'r-', label="Power Series")

#axis([0, 10, -2, 1.25])
xlabel(r'$x$')
ylabel("Exponential Functions")

legend(loc=0)

show()

#Check out http://docs.scipy.org/doc/scipy/reference/misc.html for a complete listing.


########NEW FILE########
__FILENAME__ = pade2
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Pade, glide before you fly!

#As you have seen, SciPy has some really neat functionality that comes stock.
#Oddly, some of the best stuff is in the 'miscelaneous' module.
import scipy.misc 
from pylab import *

#So our exponential pade approimation didn't give us great gains, 
#But let's try approximating a rougher function.
def f(x):
	return (7.0 + (1+x)**(4.0/3.0))**(1.0/3.0)

#Through someone else's labors we know the expansion to be... 
f_exp = [2.0, 1.0/9.0, 1.0/81.0, -49.0/8748.0, 175.0/78732.0]

#The Pade coefficients are given simply by, 
p, q = scipy.misc.pade(f_exp, (5-1)/2)
#p and q are of numpy's polynomial class
#So the Pade approximation is given by 
def PadeAppx(x):
	return p(x) / q(x)

#Let's test it...
x = arange(0.0, 10.01, 0.01)

f_exp.reverse()
f_poly = poly1d(f_exp)

plot(x, PadeAppx(x), 'k--', label="Pade Approximation")
plot(x, f(x), 'k-', label=r'$f(x)$')
plot(x, f_poly(x), 'r-', label="Power Series")

xlabel(r'$x$')
ylabel("Polynomial Function")

legend(loc=0)

show()

#Check out http://docs.scipy.org/doc/scipy/reference/misc.html for a complete listing.


########NEW FILE########
__FILENAME__ = special_functions
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy special functions, walk before you run!

#Code that numerically approximates common (and some not-so-common) special functions can be found in 'scipy.special'
from scipy.special import *

#Here you can find things like error functions, gamma functions, Legendre polynomials, etc.
#But as a example let's focus on my favorites: Bessel functions.
#Time for some graphs...
from pylab import *

x = arange(0.0, 10.1, 0.1)

for n in range(4):
	j = jn(n, x)
	plot(x, j, 'k-')
	text(x[10*(n+1)+1], j[10*(n+1)], r'$J_%r$'%n)

for n in range(3):
	y = yn(n, x)
	plot(x, y, 'k--')
	text(x[10*(n)+6], y[10*(n)+5], r'$Y_%r$'%n)

axis([0, 10, -2, 1.25])
xlabel(r'$x$')
ylabel("Bessel Functions")

show()

#Check out http://docs.scipy.org/doc/scipy/reference/special.html for a complete listing.

#Note that the figure that was created here is a reproduction of 
#Figure 6.5.1 in 'Numerical Recipes' by W. H. Press, et al.

########NEW FILE########
__FILENAME__ = close_line
import numpy as np
from scipy.optimize import fmin

#
# Attempt 1
#

def point_on_line1(x, p1, p2):
    y = p1[1] + (x - p1[0])*(p2[1] - p1[1]) / (p2[0] - p1[0])
    return np.array([x, y])


def dist_from_line1(x, pdata, p1, p2):
    pline = point_on_line1(x, p1, p2)
    return np.sqrt(np.sum((pline - pdata)**2))


def closest_data_to_line1(data, p1, p2):
    dists = np.empty(len(data), dtype=float)
    for i, pdata in enumerate(data):
        x = fmin(dist_from_line1, p1[0], (pdata, p1, p2), disp=False)[0]
        dists[i] = dist_from_line1(x, pdata, p1, p2)
    imin = np.argmin(dists)
    return imin, data[imin]


#
# Attempt 2
#

def dist_from_line2(pdata, p1, p2):
    a = np.sqrt(np.sum((p1 - pdata)**2))
    b = np.sqrt(np.sum((p2 - pdata)**2))
    c = np.sqrt(np.sum((p2 - p1)**2))
    h = a * np.sqrt(1.0 - ((a**2 + c**2 - b**2) / (2.0 * a * c))**2)
    return h

def closest_data_to_line2(data, p1, p2):
    dists = np.empty(len(data), dtype=float)
    for i, pdata in enumerate(data):
        dists[i] = dist_from_line2(pdata, p1, p2)
    imin = np.argmin(dists)
    return imin, data[imin]

#
# Attempt 3
#

def perimeter3(pdata, p1, p2):
    a = np.sqrt(np.sum((p1 - pdata)**2))
    b = np.sqrt(np.sum((p2 - pdata)**2))
    c = np.sqrt(np.sum((p2 - p1)**2))
    return (a + b + c)

def closest_data_to_line3(data, p1, p2):
    peris = np.empty(len(data), dtype=float)
    for i, pdata in enumerate(data):
        peris[i] = perimeter3(pdata, p1, p2)
    imin = np.argmin(peris)
    return imin, data[imin]

#
# Attempt 4
#

def closest_data_to_line4(data, p1, p2):
    return data[np.argmin(np.sqrt(np.sum((p1 - data)**2, axis=1)) + \
                np.sqrt(np.sum((p2 - data)**2, axis=1)))]


########NEW FILE########
__FILENAME__ = calculate_gc
def calculate_gc(x):
    '''
    Calculates the GC content of DNA sequence x.
    '''
    pass

########NEW FILE########
__FILENAME__ = mean
def mean(numlist):
    try :
        total = sum(numlist)
        length = len(numlist)
    except TypeError :
        raise TypeError("The list was not numbers.")
    except :
        print "Something unknown happened with the list."
    return total/length

########NEW FILE########
__FILENAME__ = test_calculate_gc
from nose.tools import assert_equal, assert_almost_equal, assert_true, \
    assert_false, assert_raises, assert_is_instance

from calculate_gc import calculate_gc

def test_only_G_and_C():
    '''
    Sequence of only G's and C's has fraction 1.0
    '''
    fixture = 'GGCGCCGGC'
    result = calculate_gc(fixture)
    assert_equal(result, 1.0)

def test_half():
    '''
    Sequence with half G and C has fraction 0.5
    '''
    fixture = 'ATGC'
    result = calculate_gc(fixture)
    assert_equal(result, 0.5)

def test_lower_case():
    '''
    Sequence with lower case letters
    '''
    fixture = 'atgc'
    result = calculate_gc(fixture)
    assert_equal(result, 0.5)

def test_not_DNA():
    '''
    Raise TypeError if not DNA
    '''
    fixture = 'qwerty'
    assert_raises(TypeError, calculate_gc, fixture)

########NEW FILE########
__FILENAME__ = test_mean
from nose.tools import assert_equal, assert_almost_equal, assert_true, \
    assert_false, assert_raises, assert_is_instance

from mean import mean

def test_mean1():
    obs = mean([0, 0, 0, 0])
    exp = 0
    assert_equal(obs, exp)

    obs = mean([0, 200])
    exp = 100
    assert_equal(obs, exp)

    obs = mean([0, -200])
    exp = -100
    assert_equal(obs, exp)

    obs = mean([0]) 
    exp = 0
    assert_equal(obs, exp)

def test_floating_mean1():
    obs = mean([1, 2])
    exp = 1.5
    assert_equal(obs, exp)

########NEW FILE########
__FILENAME__ = test_transcribe
from nose.tools import assert_equal, assert_almost_equal, assert_true, \
    assert_false, assert_raises, assert_is_instance

from transcribe import transcribe

########NEW FILE########
__FILENAME__ = transcribe
def transcribe(seq):
    """Transcribes a DNA sequence to RNA.
    Input: string of A's, T's, G's, and C's
    Output: string of RNA basd on input DNA.
    Converts using the following rules:
    A->U, T->A, G->C, C->G
    """
    rna = ''
    for letter in seq:
        if letter == 'A':
            rna = rna + 'U'
        elif letter == 'T':
            rna = rna + 'A'
        elif letter == 'G':
            rna = rna + 'C'
        else:
            rna = rna + 'G'
    return rna
########NEW FILE########
__FILENAME__ = mean
def mean(numlist):
    try :
        total = sum(numlist)
        length = len(numlist)
    except TypeError :
        raise TypeError("The list was not numbers.")
    except :
        print "Something unknown happened with the list."
    return total/length

########NEW FILE########
__FILENAME__ = test_mean
from nose.tools import assert_equal, assert_almost_equal, assert_true, \
    assert_false, assert_raises, assert_is_instance

from mean import mean

def test_mean1():
    obs = mean([0, 0, 0, 0])
    exp = 0
    assert_equal(obs, exp)

    obs = mean([0, 200])
    exp = 100
    assert_equal(obs, exp)

    obs = mean([0, -200])
    exp = -100
    assert_equal(obs, exp)

    obs = mean([0]) 
    exp = 0
    assert_equal(obs, exp)

def test_floating_mean1():
    obs = mean([1, 2])
    exp = 1.5
    assert_equal(obs, exp)

########NEW FILE########
__FILENAME__ = exercises
# -*- coding: utf-8 -*-
# <nbformat>3</nbformat>

# <markdowncell>

# # Exercise 1
# 1. Assign variables with the values 1, 5, and "ten" with the types int, float, and string respectively.
# <codecell>
  
# <markdowncell>
# 2. Confirm that the types are int, float, and string
# <codecell>
  
# <markdowncell>
# 3. Determine which for which pairs of the set of int, float, and string the + operation gives an error.  
# > int-int :
# > int-float : 
# > int-string :
# > float-float  :
# > float-string :
# > string-string : 
# Any surprises?
# <codecell>
 
# <markdowncell>
# 4. Determine which for which pairs of the set of int, float, and string) the * operation gives an error.  Any surprises?
# <codecell>
  
# <markdowncell>
# 5. Assign a string the value of "1, 5, and ten" from these three variables.  
# <codecell>
 
# <markdowncell>
# # Exercise 2
# Here you will use **math.log10()** and **math.floor()**, which require the line **import math** for you to access these funcitons.  
# 1. Determine the return type of log10()
# <codecell>
import math
  
# <markdowncell>
# 2. What is the value and type of log10(42) ?
# <codecell>
  
# <markdowncell>
# 3. What is the value and type of log10(-0.32) ?
# <codecell>
 
# <markdowncell>
# 4. What about 1.0 / 0 ?   
# <codecell>
   
# <markdowncell>
# 4. What is the return type of floor acting on an int?  Acting on a float?  **floor** is in the math namespace.  It will only work after **import math** and it is invoked as **math.floor()**
# <codecell>
   
# <markdowncell>
# # Exercise 3
#  len() is a builtin function to count the length of things.  For which of the basic datatypes so far does len() return a value?  Does it return the length or the length+1 ?
# <codecell>
  
# <markdowncell>
# # Example 1
# Python lists are agnostic to the type of the data contained within them.  You can generate arrays with different elements of different types:
# <codecell>
pythonlist =[2.43, 1, 0.92, 0, "0.38"]
print pythonlist
# <codecell>
print type(pythonlist[0]), type(pythonlist[1]), type(pythonlist[2]), type(pythonlist[3])
# <markdowncell>
# # Exercise 4
# numpy is an extremely useful library that has its own data types; you will frequently need to specify the types as float or possibly higher-precision float at the time you create them.  The numpy data types are only sometimes compatible with the native data types.  
# <codecell>
import numpy as np
numpyarray = np.array(pythonlist)
# <markdowncell>
# What is the default data type of a after the conversion?
# <codecell>
 
# <markdowncell>
# Ack! The results of type() do not betray the representation.  For that we need 
# <codecell>
print numpyarray.dtype
# <markdowncell>
# Which is not a numeric data type.  We can cause it to be stored as numpy floats if we specify float when we convert it to numpy:
# <codecell>
numpyfloatarray = np.array(python_array, dtype="float")

# <markdowncell>
# # Exercise 5
# 5A. Write an expression to determine the number of digits in a non-negative integer.  Hint:  maybe **len()** or **math.log()** might be useful here.
# <codecell>

# <markdowncell>
# 5B. Test your expression on 45, 2, and 2.0.  Does it work for all three?
# <codecell>

########NEW FILE########
__FILENAME__ = hello
import time

print "hello world"

time.sleep(1)

print "is it me you're looking for?"

time.sleep(2)

f = open("richie.txt")
for line in f:
  print line.rstrip()
  time.sleep(0.2)

f.close()


########NEW FILE########
__FILENAME__ = variables
# -*- coding: utf-8 -*-
# <nbformat>2.0</nbformat>

# <markdowncell>

# ## Python, iPython, and the basics
# 
# * * * * *
# 
# **Based on Lecture Materials By: Milad Fatenejad, Katy Huff, Tommy Guy, Joshua R. Smith, Will Trimble, and Many More**
# 
# <markdowncell>
# ## Introduction
# This lecture is on basic programming in python. In order to do the examples, we are going to use an environment called iPython notebook.  I expect this lecture to be interactive, so stop me at any point if you have questions. The correct power dynamic is that people are the masters and the machines are servants. The computer is a hammer; it exists to help us get things done.  We can hammer nails with the handle, with the claw of the hammer; some of us even hammer nails with bricks.  But when you learn what part of the hammer works best with nails, and have some experience swinging it, you spend less time worrying about the hammering and more time worrying about your furniture.
# 
# <markdowncell>
# So now would be a good time to roll out [PEP 20, The Zen of Python](http://www.python.org/dev/peps/pep-0020/)
# > Beautiful is better than ugly.  
# > Explicit is better than implicit.  
# > Simple is better than complex.  
# > Complex is better than complicated.  
# > Flat is better than nested.  
# > Sparse is better than dense.  
# > Readability counts.  
# > Special cases aren't special enough to break the rules.  
# > Although practicality beats purity.  
# > Errors should never pass silently.  
# > Unless explicitly silenced.  
# > In the face of ambiguity, refuse the temptation to guess.  
# > There should be one-- and preferably only one --obvious way to do it.  
# > Although that way may not be obvious at first unless you're Dutch.  
# > Now is better than never.   
# > Although never is often better than *right* now.  
# > If the implementation is hard to explain, it's a bad idea.  
# > If the implementation is easy to explain, it may be a good idea.  
# > Namespaces are one honking great idea -- let's do more of those!  
# 
# <markdowncell>
# Here is the reference material.
# 
# * [Dive into Python](http://www.diveintopython.net/toc/index.html)
# * [Software Carpentry's Python Lectures](http://software-carpentry.org/4_0/python/)
# * [IPython: A System for Interactive Scientific Computing](http://dx.doi.org/10.1109/MCSE.2007.53)
# * [How to Think Like a Computer Scientist](http://www.greenteapress.com/thinkpython/thinkpython.html)
# 
# <markdowncell>
# ## Lesson 1
# * print statements
# * variables
# * integers
# * floats
# * strings
# * types
# * type coersion
# * basic operations: add numbers, concatenate strings, basic data type functionality
# <markdowncell>
# ## Lesson 2
# * list
# * dictionary
# * set
# * tuple
# * file reading
# <markdowncell>
# ## Lesson 3
# * for loop
# * conditional (if) statements
# * while loops
# * iteration
# * writing to files
# <markdowncell>
# ## Lesson 4
# * methods
# * modules
# 
# 
# ## Python environments
# You can run python commands in a handful of ways; you can create executable scripts, you can run the python interpreter, you can run iPython, or you can run iPython notebook.  iPython is an alternative to the built-in Python interpreter with some nice features.  iPython notebook gives you interactive access to the python interpreter from within a browser window, and it allows you to save your commands as a "notebook".
# Let's give the built-in interpreter a spin just this once.  Open a **Terminal** window, which starts your default shell.  Type 

# <markdowncell>
# ``
# python 
# ``
# <markdowncell>
# And you should see python start up.  Type 
# <markdowncell>
# ``
# print "Fresh out of parrots"
# ``
# <markdowncell>
# Note the black-and-white wallpaper.
# Escape from python with 
# `` 
# quit()
# ``
# <markdowncell>
# ***
# 
# iPython has more useful features for interactive use than the standard python interpreter, but it works in the same way--it is interacitve, and you get there from the command line.  iPython notebook uses javascript to allow you to enter python commands in your browser and show you the result in the browser.  We'll use it from here on out.

# <codecell>

print "hello world"

# <markdowncell>

# ## Navigating in ipython notebook
# The box above is called the input cell; commands you put here will be fed to the python interpreter one at a time when you press **Shift-ENTER**.  
# The output of the command, or the error message, appears below the line you entered it on.
# The panel which may appear on the left has some notebook options; you can minimize the panel by double-clicking on the bar separating the windows. 
# <codecell>
print "Try and tell that to the young people"
print "of today--they won't believe you."
# <markdowncell>

# If you hit **ENTER** only, ipython notebook gives you another line in the current cell.  
# This allows you to compose multi-line commands and submit them to python all at once.  

# <markdowncell>

# Up and down arrows will allow you to move the cursor to different cells in the notebook, including these cells containing text (which you can edit in your browser).  
# Only the cells for which you press Shift-ENTER or Control-ENTER will be executed by the python interpreter.   

# <markdowncell>

# You can enter the same line over and over again into the interpreter.  It's wierd, but it's life. 

# <codecell>

i = 0

# <markdowncell>

# **Shift-ENTER** executes and moves to the next cell.  
# **Control-ENTER** executes and does *not* move to the next cell.  
# Try entering this cell a few times:  
# <codecell>

i = i + 1
print i

# <markdowncell>

# If you want to create new empty cells, it's three keys: **Shift-Enter**, **Control-M**, and then  **a**  This will insert more cells in the middle of the notebook. 

# <markdowncell>

# ## Getting Help
# 
# iPython has some nice help features. Let's say we want to know more about the integer data type. There are at least two ways to do this task:

# <codecell>

help(int)

# <markdowncell>

# which displays a scrolling text help, or

# <codecell>

int?

# <markdowncell>

# Which displays a shorter help summary in the magic pane at the bottom of the screen.  You can minimize the magic pane when it gets in your way.

# <markdowncell>

# If you wanted to see all the built-in commands available for something, use the *dir* command. Check out all of the methods of the object "Hello world", which are shared by all objects of the str type.

# <codecell>

dir("Hello world")

# <markdowncell>

# There's a method that looks important -- swapcase.  Let's see what it does:  

# <codecell>

"Hello world".swapcase()

# <markdowncell>

# Hrm.  Ahem.
# ## Executing code in files
# 
# If your code is in a file, you can execute it from the iPython shell with the **%run** command. Execute hello.py like so

# <codecell>

%run hellp.py

# <markdowncell>

# *Ooops.*  We misspelled **hello.py**, and python is giving us an error message.  Change the line above to hello.py, hit **Shift-ENTER**, and see what it does.

# <markdowncell>

# ## Clearing iPython
# 
# To clear everything from iPython, use the %reset command.

# <codecell>

mystring = "And three shall be the count." 
print mystring

# <codecell>

%reset

# <codecell>

print mystring

# <markdowncell>

# Note that the error message contains a recap of the input that caused the error (with an arrow, no less!)   It is objecting that **mystring** is not defined, since we just reset it.
# 
# ## Variables
# 
# All programming languages have variables, and python is no different. To create a variable, just name it and set it with the equals sign. One important caveat: variable names can only contain letters, numbers, and the underscore character. Let's set a variable.

# <codecell>

experiment = "current vs. voltage"

# <codecell>

print experiment

# <codecell>

voltage = 2

# <codecell>

current = 0.5

# <codecell>

print voltage, current

# <markdowncell>

# ## Types and Dynamic Typing
# 
# Like most programming languages, things in python are typed. The type refers to the type of data. We've already defined three different types of data in experiment, voltage, and current. The types are string, integer, and float. You can inspect the type of a variable by using the type command.

# <codecell>

type(experiment)

# <codecell>

type(voltage)

# <codecell>

type(current)

# <markdowncell>

# Python is a dynamically typed language (unlike, say, C++). If you know what that means, you may be feeling some fear and loathing right now. If you don't know what dynamic typing means, the next stuff may seem esoteric and pedantic. Its actually important, but its importance may not be clear to you until long after this class is over.
# 
# Dynamic typing means that you don't have to declare the type of a variable when you define it; python just figures it out based on how you are setting the variable. Lets say you set a variable. Sometime later you can just change the type of data assigned to a variable and python is perfectly happy about that. Since it won't be obvious until (possibly much) later why that's important, I'll let you marinate on that idea for a second. 
# 
# Here's an example of dynamic typing. What's the type of data assigned to voltage?

# <codecell>

type(voltage)

# <markdowncell>

# Lets assign a value of 2.7 (which is clearly a float) to voltage. What happens to the type?

# <codecell>

voltage = 2.7

# <codecell>

type(voltage)

# <markdowncell>

# You can even now assign a string to the variable voltage and python would be happy to comply.

# <codecell>

voltage = "2.7 volts"

# <codecell>

type(voltage)

# <markdowncell>

# I'll let you ruminate on the pros and cons of this construction while I change the value of voltage back to an int:

# <codecell>

voltage = 2

# <markdowncell>

# ## Coersion
# It is possible to coerce (a fancy and slightly menacing way to say "convert") certain types of data to other types. For example, its pretty straightforward to coerce numerical data to strings.

# <codecell>

voltageString = str(voltage)

# <codecell>

currentString = str(current)

# <codecell>

voltageString

# <codecell>

type(voltageString)

# <markdowncell>

# As you might imagine, you can go the other way in certain cases. Lets say you had numerical data in a string.

# <codecell>

resistanceString = "4.0"

# <codecell>

resistance = float(resistanceString)

# <codecell>

resistance

# <codecell>

type(resistance)

# <markdowncell>

# What would happen if you tried to coerce resistanceString to an int? What about coercing resistance to an int? Consider the following:

# <codecell>

resistanceString = "4.0 ohms"

# <markdowncell>

# Do you think you can coerce that string to a numerical type?
# ## On Being Precise with floats and ints
# Again, the following may seem esoteric and pedantic, but it is very important. So bear with me.
# Let's say you had some voltage data that looks like the following
# ``
# 0
# 0.5
# 1
# 1.5
# 2
# ``
# 
# Obviously, if you just assigned this data individually to a variable, you'd end up with the following types
# ``
# 0   -> int
# 0.5 -> float
# 1   -> int
# 1.5 -> float
# 2   -> int
# ``
# 
# But what if you wanted all of that data to be floats on its way in? You could assign the variable and then coerce it to type float:

# <codecell>

voltage = float(1)

# <markdowncell>

# But that's ugly. If you want what is otherwise an integer to be a float, just add a period at the end

# <codecell>

voltage = 1.

# <codecell>

type(voltage)

# <markdowncell>

# This point becomes important when we start operating on data in the next section.
# 
# ## Data Operations
# 
# What's the point of data if we aren't going to do something with it?  Let's get computing.

# <codecell>

a = 1

# <codecell>

b = 2

# <codecell>

c = a+b

# <codecell>

c

# <codecell>

type(a), type(b), type(c)

# <markdowncell>

# So we got a value of three for the sum, which also happens to be an integer. Any operation between two integers is another integer. Makes sense.
# 
# So what about the case where a is an integer and b is a float?

# <codecell>

a = 1

# <codecell>

b = 2.

# <codecell>

c = a + b

# <codecell>

c

# <codecell>

type(a), type(b), type(c)

# <markdowncell>

# You can do multiplication on numbers as well.

# <codecell>

a = 2

# <codecell>

b = 3

# <codecell>

c = a * b

# <codecell>

c

# <codecell>

type(a), type(b), type(c)

# <markdowncell>

# Also division.

# <codecell>

a = 1

# <codecell>

b = 2

# <codecell>

c = a / b

# <codecell>

c

# <markdowncell>

# **ZING!**
# 
# This is why type is important. Divding two integers returnes an integer: this operation calculates the quotient and floors the result to get the answer.
# 
# If everything was a float, the division is what you would expect.

# <codecell>

a = 1.

# <codecell>

b = 2.

# <codecell>

c = a / b

# <codecell>

c

# <codecell>

type(a), type(b), type(c)

# <markdowncell>

# There are operations that can be done with strings.

# <codecell>

firstName = "Johann"

# <codecell>

lastName = "Gambolputty"

# <markdowncell>

# When concatenating strings, we must explicitly use the concatenation operator +.  Computers don't understand context.

# <codecell>

fullName = firstName + lastName

# <codecell>

print fullName

# <codecell>

fullName = firstName + " " + lastName

# <codecell>

print fullName

# <markdowncell>

# There are other operations deined on string data. Use the *dir* comnand to find them. One example I'll show is the upper method. Lets take a look at the documentation.

# <codecell>

str.upper?

# <markdowncell>

# So we can use it to upper-caseify a string. 

# <codecell>

fullName.upper()

# <markdowncell>

# You have to use the parenthesis at the end because upper is a method of the string class.
# 
# For what its worth, you don't need to have a variable to use the upper() method, you could use it on the string itself.

# <codecell>

"Johann Gambolputty".upper()

# <markdowncell>

# What do you think should happen when you take upper of an int?  What about a string representation of an int?
# 
# That wraps up this lesson. We tried out the iPython shell and got some experience with ints, floats, and strings. Along the way we talked about some philosophy and how programming is like hammering.  
# 
# ## Miscellaneous scraps
# ## Pasting
# 
# You can paste things into the ipython console by copying text from your machine with **ctrl+c** and typing **%paste** at the iPython prompt.  The **%paste** is necessary syntax for multi-line clipboard deposits.
# 
# <codecell>
%paste
   
# <markdowncell>


########NEW FILE########
__FILENAME__ = get-my-ip
#!/usr/bin/env python

"""Get your public IP address from a UDP socket connection
"""

import socket as _socket


def get_my_ip(host, port=80):
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    try:
        s.connect((host, port))
        return s.getsockname()[0]
    finally:
        s.close()


if __name__ == '__main__':
    import argparse as _argparse

    parser = _argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'host', default='software-carpentry.org', nargs='?')
    parser.add_argument(
        'port', default=80, type=int, nargs='?')

    args = parser.parse_args()

    print(get_my_ip(host=args.host, port=args.port))

########NEW FILE########
__FILENAME__ = swc-installation-test-1
#!/usr/bin/env python

"""Test script to check required Python version.

Execute this code at the command line by typing:

  python swc-installation-test-1.py

How to get a command line:

- On OSX run this with the Terminal application.

- On Windows, go to the Start menu, select 'Run' and type 'cmd'
(without the quotes) to run the 'cmd.exe' Windows Command Prompt.

- On Linux, either use your login shell directly, or run one of a
  number of graphical terminals (e.g. 'xterm', 'gnome-terminal', ...).

For some screen shots, see:

  http://software-carpentry.org/setup/terminal.html

Run the script and follow the instructions it prints at the end.  If
you see an error saying that the 'python' command was not found, than
you may not have any version of Python installed.  See:

  http://www.python.org/download/releases/2.7.3/#download

for installation instructions.

This test is separate to avoid Python syntax errors parsing the more
elaborate `swc-installation-test-2.py`.
"""

import sys as _sys


__version__ = '0.1'


def check():
    if _sys.version_info < (2, 6):
        print('check for Python version (python):')
        print('outdated version of Python: ' + _sys.version)
        return False
    return True


if __name__ == '__main__':
    if check():
        print('Passed')
    else:
        print('Failed')
        print('Install a current version of Python!')
        print('http://www.python.org/download/releases/2.7.3/#download')
        _sys.exit(1)

########NEW FILE########
__FILENAME__ = swc-installation-test-2
#!/usr/bin/env python

"""Test script to check for required functionality.

Execute this code at the command line by typing:

  python swc-installation-test-2.py

Run the script and follow the instructions it prints at the end.

This script requires at least Python 2.6.  You can check the version
of Python that you have installed with 'swc-installation-test-1.py'.

By default, this script will test for all the dependencies your
instructor thinks you need.  If you want to test for a different set
of packages, you can list them on the command line.  For example:

  python swc-installation-test-2.py git virtual-editor

This is useful if the original test told you to install a more recent
version of a particular dependency, and you just want to re-test that
dependency.
"""

from __future__ import print_function  # for Python 2.6 compatibility

import distutils.ccompiler as _distutils_ccompiler
import fnmatch as _fnmatch
try:  # Python 2.7 and 3.x
    import importlib as _importlib
except ImportError:  # Python 2.6 and earlier
    class _Importlib (object):
        """Minimal workarounds for functions we need
        """
        @staticmethod
        def import_module(name):
            module = __import__(name)
            for n in name.split('.')[1:]:
                module = getattr(module, n)
            return module
    _importlib = _Importlib()
import logging as _logging
import os as _os
import platform as _platform
import re as _re
import shlex as _shlex
import subprocess as _subprocess
import sys as _sys
try:  # Python 3.x
    import urllib.parse as _urllib_parse
except ImportError:  # Python 2.x
    import urllib as _urllib_parse  # for quote()


if not hasattr(_shlex, 'quote'):  # Python versions older than 3.3
    # Use the undocumented pipes.quote()
    import pipes as _pipes
    _shlex.quote = _pipes.quote


__version__ = '0.1'

# Comment out any entries you don't need
CHECKS = [
# Shell
    'virtual-shell',
# Editors
    'virtual-editor',
# Browsers
    'virtual-browser',
# Version control
    'git',
    'hg',              # Command line tool
    #'mercurial',       # Python package
    'EasyMercurial',
# Build tools and packaging
    'make',
    'virtual-pypi-installer',
    'setuptools',
    #'xcode',
# Testing
    'nosetests',       # Command line tool
    'nose',            # Python package
    'py.test',         # Command line tool
    'pytest',          # Python package
# SQL
    'sqlite3',         # Command line tool
    'sqlite3-python',  # Python package
# Python
    'python',
    'ipython',         # Command line tool
    'IPython',         # Python package
    'argparse',        # Useful for utility scripts
    'numpy',
    'scipy',
    'matplotlib',
    'pandas',
    'sympy',
    'Cython',
    'networkx',
    'mayavi.mlab',
    ]

CHECKER = {}

_ROOT_PATH = _os.sep
if _platform.system() == 'win32':
    _ROOT_PATH = 'c:\\'


class InvalidCheck (KeyError):
    def __init__(self, check):
        super(InvalidCheck, self).__init__(check)
        self.check = check

    def __str__(self):
        return self.check


class DependencyError (Exception):
    _default_url = 'http://software-carpentry.org/setup/'
    _setup_urls = {  # (system, version, package) glob pairs
        ('*', '*', 'Cython'): 'http://docs.cython.org/src/quickstart/install.html',
        ('Linux', '*', 'EasyMercurial'): 'http://easyhg.org/download.html#download-linux',
        ('Darwin', '*', 'EasyMercurial'): 'http://easyhg.org/download.html#download-mac',
        ('Windows', '*', 'EasyMercurial'): 'http://easyhg.org/download.html#download-windows',
        ('*', '*', 'EasyMercurial'): 'http://easyhg.org/download.html',
        ('*', '*', 'argparse'): 'https://pypi.python.org/pypi/argparse#installation',
        ('*', '*', 'ash'): 'http://www.in-ulm.de/~mascheck/various/ash/',
        ('*', '*', 'bash'): 'http://www.gnu.org/software/bash/manual/html_node/Basic-Installation.html#Basic-Installation',
        ('Linux', '*', 'chromium'): 'http://code.google.com/p/chromium/wiki/LinuxBuildInstructions',
        ('Darwin', '*', 'chromium'): 'http://code.google.com/p/chromium/wiki/MacBuildInstructions',
        ('Windows', '*', 'chromium'): 'http://www.chromium.org/developers/how-tos/build-instructions-windows',
        ('*', '*', 'chromium'): 'http://www.chromium.org/developers/how-tos',
        ('Windows', '*', 'emacs'): 'http://www.gnu.org/software/emacs/windows/Installing-Emacs.html',
        ('*', '*', 'emacs'): 'http://www.gnu.org/software/emacs/#Obtaining',
        ('*', '*', 'firefox'): 'http://www.mozilla.org/en-US/firefox/new/',
        ('Linux', '*', 'gedit'): 'http://www.linuxfromscratch.org/blfs/view/svn/gnome/gedit.html',
        ('*', '*', 'git'): 'http://git-scm.com/downloads',
        ('*', '*', 'google-chrome'): 'https://www.google.com/intl/en/chrome/browser/',
        ('*', '*', 'hg'): 'http://mercurial.selenic.com/',
        ('*', '*', 'mercurial'): 'http://mercurial.selenic.com/',
        ('*', '*', 'IPython'): 'http://ipython.org/install.html',
        ('*', '*', 'ipython'): 'http://ipython.org/install.html',
        ('*', '*', 'jinja'): 'http://jinja.pocoo.org/docs/intro/#installation',
        ('*', '*', 'kate'): 'http://kate-editor.org/get-it/',
        ('*', '*', 'make'): 'http://www.gnu.org/software/make/',
        ('Darwin', '*', 'matplotlib'): 'http://matplotlib.org/users/installing.html#building-on-osx',
        ('Windows', '*', 'matplotlib'): 'http://matplotlib.org/users/installing.html#installing-on-windows',
        ('*', '*', 'matplotlib'): 'http://matplotlib.org/users/installing.html#installing',
        ('*', '*', 'mayavi.mlab'): 'http://docs.enthought.com/mayavi/mayavi/installation.html',
        ('*', '*', 'nano'): 'http://www.nano-editor.org/dist/latest/faq.html#3',
        ('*', '*', 'networkx'): 'http://networkx.github.com/documentation/latest/install.html#installing',
        ('*', '*', 'nose'): 'https://nose.readthedocs.org/en/latest/#installation-and-quick-start',
        ('*', '*', 'nosetests'): 'https://nose.readthedocs.org/en/latest/#installation-and-quick-start',
        ('*', '*', 'notepad++'): 'http://notepad-plus-plus.org/download/v6.3.html',
        ('*', '*', 'numpy'): 'http://docs.scipy.org/doc/numpy/user/install.html',
        ('*', '*', 'pandas'): 'http://pandas.pydata.org/pandas-docs/stable/install.html',
        ('*', '*', 'pip'): 'http://www.pip-installer.org/en/latest/installing.html',
        ('*', '*', 'pytest'): 'http://pytest.org/latest/getting-started.html',
        ('*', '*', 'python'): 'http://www.python.org/download/releases/2.7.3/#download',
        ('*', '*', 'pyzmq'): 'https://github.com/zeromq/pyzmq/wiki/Building-and-Installing-PyZMQ',
        ('*', '*', 'py.test'): 'http://pytest.org/latest/getting-started.html',
        ('Linux', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy/Linux',
        ('Darwin', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy/Mac_OS_X',
        ('Windows', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy/Windows',
        ('*', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy',
        ('*', '*', 'setuptools'): 'https://pypi.python.org/pypi/setuptools#installation-instructions',
        ('*', '*', 'sqlite3'): 'http://www.sqlite.org/download.html',
        ('*', '*', 'sublime-text'): 'http://www.sublimetext.com/2',
        ('*', '*', 'sympy'): 'http://docs.sympy.org/dev/install.html',
        ('Darwin', '*', 'textmate'): 'http://macromates.com/',
        ('Darwin', '*', 'textwrangler'): 'http://www.barebones.com/products/textwrangler/download.html',
        ('*', '*', 'tornado'): 'http://www.tornadoweb.org/',
        ('*', '*', 'vim'): 'http://www.vim.org/download.php',
        ('Darwin', '*', 'xcode'): 'https://developer.apple.com/xcode/',
        ('*', '*', 'xemacs'): 'http://www.us.xemacs.org/Install/',
        ('*', '*', 'zsh'): 'http://www.zsh.org/',
        }

    def _get_message(self):
        return self._message
    def _set_message(self, message):
        self._message = message
    message = property(_get_message, _set_message)

    def __init__(self, checker, message, causes=None):
        super(DependencyError, self).__init__(message)
        self.checker = checker
        self.message = message
        if causes is None:
            causes = []
        self.causes = causes

    def get_url(self):
        system = _platform.system()
        version = None
        for pversion in (
            'linux_distribution',
            'mac_ver',
            'win32_ver',
            ):
            value = getattr(_platform, pversion)()
            if value[0]:
                version = value[0]
                break
        package = self.checker.name
        for (s,v,p),url in self._setup_urls.items():
            if (_fnmatch.fnmatch(system, s) and
                    _fnmatch.fnmatch(version, v) and
                    _fnmatch.fnmatch(package, p)):
                return url
        return self._default_url

    def __str__(self):
        url = self.get_url()
        lines = [
            'check for {0} failed:'.format(self.checker.full_name()),
            '  ' + self.message,
            '  For instructions on installing an up-to-date version, see',
            '  ' + url,
            ]
        if self.causes:
            lines.append('  causes:')
            for cause in self.causes:
                lines.extend('  ' + line for line in str(cause).splitlines())
        return '\n'.join(lines)


def check(checks=None):
    successes = []
    failures = []
    if not checks:
        checks = CHECKS
    for check in checks:
        try:
            checker = CHECKER[check]
        except KeyError as e:
            raise InvalidCheck(check)# from e
        _sys.stdout.write('check {0}...\t'.format(checker.full_name()))
        try:
            version = checker.check()
        except DependencyError as e:
            failures.append(e)
            _sys.stdout.write('fail\n')
        else:
            _sys.stdout.write('pass\n')
            successes.append((checker, version))
    if successes:
        print('\nSuccesses:\n')
        for checker,version in successes:
            print('{0} {1}'.format(
                    checker.full_name(),
                    version or 'unknown'))
    if failures:
        print('\nFailures:')
        printed = []
        for failure in failures:
            if failure not in printed:
                print()
                print(failure)
                printed.append(failure)
        return False
    return True


class Dependency (object):
    def __init__(self, name, long_name=None, minimum_version=None,
                 version_delimiter='.', and_dependencies=None,
                 or_dependencies=None):
        self.name = name
        self.long_name = long_name or name
        self.minimum_version = minimum_version
        self.version_delimiter = version_delimiter
        if not and_dependencies:
            and_dependencies = []
        self.and_dependencies = and_dependencies
        if not or_dependencies:
            or_dependencies = []
        self.or_dependencies = or_dependencies
        self._check_error = None

    def __str__(self):
        return '<{0} {1}>'.format(type(self).__name__, self.name)

    def full_name(self):
        if self.name == self.long_name:
            return self.name
        else:
            return '{0} ({1})'.format(self.long_name, self.name)

    def check(self):
        if self._check_error:
            raise self._check_error
        try:
            self._check_dependencies()
            return self._check()
        except DependencyError as e:
            self._check_error = e  # cache for future calls
            raise

    def _check_dependencies(self):
        for dependency in self.and_dependencies:
            if not hasattr(dependency, 'check'):
                dependency = CHECKER[dependency]
            try:
                dependency.check()
            except DependencyError as e:
                raise DependencyError(
                    checker=self,
                    message=(
                        'some dependencies for {0} were not satisfied'
                        ).format(self.full_name()),
                    causes=[e])
        self.or_pass = None
        or_errors = []
        for dependency in self.or_dependencies:
            if not hasattr(dependency, 'check'):
                dependency = CHECKER[dependency]
            try:
                version = dependency.check()
            except DependencyError as e:
                or_errors.append(e)
            else:
                self.or_pass = {
                    'dependency': dependency,
                    'version': version,
                    }
                break  # no need to test other dependencies
        if self.or_dependencies and not self.or_pass:
            raise DependencyError(
                checker=self,
                message=(
                    '{0} requires at least one of the following dependencies'
                    ).format(self.full_name()),
                    causes=or_errors)

    def _check(self):
        version = self._get_version()
        parsed_version = None
        if hasattr(self, '_get_parsed_version'):
            parsed_version = self._get_parsed_version()
        if self.minimum_version:
            self._check_version(version=version, parsed_version=parsed_version)
        return version

    def _get_version(self):
        raise NotImplementedError(self)

    def _minimum_version_string(self):
        return self.version_delimiter.join(
            str(part) for part in self.minimum_version)

    def _check_version(self, version, parsed_version=None):
        if not parsed_version:
            parsed_version = self._parse_version(version=version)
        if not parsed_version or parsed_version < self.minimum_version:
            raise DependencyError(
                checker=self,
                message='outdated version of {0}: {1} (need >= {2})'.format(
                    self.full_name(), version, self._minimum_version_string()))

    def _parse_version(self, version):
        if not version:
            return None
        parsed_version = []
        for part in version.split(self.version_delimiter):
            try:
                parsed_version.append(int(part))
            except ValueError as e:
                raise DependencyError(
                    checker=self,
                    message=(
                        'unparsable {0!r} in version {1} of {2}, (need >= {3})'
                        ).format(
                        part, version, self.full_name(),
                        self._minimum_version_string()))# from e
        return tuple(parsed_version)


class PythonDependency (Dependency):
    def __init__(self, name='python', long_name='Python version',
                 minimum_version=(2, 6), **kwargs):
        super(PythonDependency, self).__init__(
            name=name, long_name=long_name, minimum_version=minimum_version,
            **kwargs)

    def _get_version(self):
        return _sys.version

    def _get_parsed_version(self):
        return _sys.version_info


CHECKER['python'] = PythonDependency()


class CommandDependency (Dependency):
    exe_extension = _distutils_ccompiler.new_compiler().exe_extension

    def __init__(self, command, paths=None, version_options=('--version',),
                 stdin=None, version_regexp=None, version_stream='stdout',
                 **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = command
        super(CommandDependency, self).__init__(**kwargs)
        self.command = command
        self.paths = paths
        self.version_options = version_options
        self.stdin = None
        if not version_regexp:
            regexp = r'([\d][\d{0}]*[\d])'.format(self.version_delimiter)
            version_regexp = _re.compile(regexp)
        self.version_regexp = version_regexp
        self.version_stream = version_stream

    def _get_command_version_stream(self, command=None, stdin=None,
                                    expect=(0,)):
        if command is None:
            command = self.command + (self.exe_extension or '')
        if not stdin:
            stdin = self.stdin
        if stdin:
            popen_stdin = _subprocess.PIPE
        else:
            popen_stdin = None
        try:
            p = _subprocess.Popen(
                [command] + list(self.version_options), stdin=popen_stdin,
                stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
                universal_newlines=True)
        except OSError as e:
            raise DependencyError(
                checker=self,
                message="could not find '{0}' executable".format(command),
                )# from e
        stdout,stderr = p.communicate(stdin)
        status = p.wait()
        if status not in expect:
            lines = [
                "failed to execute: {0} {1}".format(
                    command,
                    ' '.join(_shlex.quote(arg)
                             for arg in self.version_options)),
                'status: {0}'.format(status),
                ]
            for name,string in [('stdout', stdout), ('stderr', stderr)]:
                if string:
                    lines.extend([name + ':', string])
            raise DependencyError(checker=self, message='\n'.join(lines))
        for name,string in [('stdout', stdout), ('stderr', stderr)]:
            if name == self.version_stream:
                if not string:
                    raise DependencyError(
                        checker=self,
                        message='empty version stream on {0} for {1}'.format(
                            self.version_stream, command))
                return string
        raise NotImplementedError(self.version_stream)

    def _get_version_stream(self, **kwargs):
        paths = [self.command + (self.exe_extension or '')]
        if self.exe_extension:
            paths.append(self.command)  # also look at the extension-less path
        if self.paths:
            paths.extend(self.paths)
        or_errors = []
        for path in paths:
            try:
                return self._get_command_version_stream(command=path, **kwargs)
            except DependencyError as e:
                or_errors.append(e)
        raise DependencyError(
            checker=self,
            message='errors finding {0} version'.format(
                self.full_name()),
            causes=or_errors)

    def _get_version(self):
        version_stream = self._get_version_stream()
        match = self.version_regexp.search(version_stream)
        if not match:
            raise DependencyError(
                checker=self,
                message='no version string in output:\n{0}'.format(
                    version_stream))
        return match.group(1)


def _program_files_paths(*args):
    "Utility for generating MS Windows search paths"
    pf = _os.environ.get('ProgramFiles', '/usr/bin')
    pfx86 = _os.environ.get('ProgramFiles(x86)', pf)
    paths = [_os.path.join(pf, *args)]
    if pfx86 != pf:
        paths.append(_os.path.join(pfx86, *args))
    return paths


for command,long_name,minimum_version,paths in [
        ('sh', 'Bourne Shell', None, None),
        ('ash', 'Almquist Shell', None, None),
        ('bash', 'Bourne Again Shell', None, None),
        ('csh', 'C Shell', None, None),
        ('ksh', 'KornShell', None, None),
        ('dash', 'Debian Almquist Shell', None, None),
        ('tcsh', 'TENEX C Shell', None, None),
        ('zsh', 'Z Shell', None, None),
        ('git', 'Git', (1, 7, 0), None),
        ('hg', 'Mercurial', (2, 0, 0), None),
        ('EasyMercurial', None, (1, 3), None),
        ('pip', None, None, None),
        ('sqlite3', 'SQLite 3', None, None),
        ('nosetests', 'Nose', (1, 0, 0), None),
        ('ipython', 'IPython script', (0, 13), None),
        ('emacs', 'Emacs', None, None),
        ('xemacs', 'XEmacs', None, None),
        ('vim', 'Vim', None, None),
        ('vi', None, None, None),
        ('nano', 'Nano', None, None),
        ('gedit', None, None, None),
        ('kate', 'Kate', None, None),
        ('notepad++', 'Notepad++', None,
         _program_files_paths('Notepad++', 'notepad++.exe')),
        ('firefox', 'Firefox', None,
         _program_files_paths('Mozilla Firefox', 'firefox.exe')),
        ('google-chrome', 'Google Chrome', None,
         _program_files_paths('Google', 'Chrome', 'Application', 'chrome.exe')
         ),
        ('chromium', 'Chromium', None, None),
        ]:
    if not long_name:
        long_name = command
    CHECKER[command] = CommandDependency(
        command=command, paths=paths, long_name=long_name,
        minimum_version=minimum_version)
del command, long_name, minimum_version, paths  # cleanup namespace


class MakeDependency (CommandDependency):
    makefile = '\n'.join([
            'all:',
            '\t@echo "MAKE_VERSION=$(MAKE_VERSION)"',
            '\t@echo "MAKE=$(MAKE)"',
            '',
            ])

    def _get_version(self):
        try:
            return super(MakeDependency, self)._get_version()
        except DependencyError as e:
            version_options = self.version_options
            self.version_options = ['-f', '-']
            try:
                stream = self._get_version_stream(stdin=self.makefile)
                info = {}
                for line in stream.splitlines():
                    try:
                        key,value = line.split('=', 1)
                    except ValueError as ve:
                        raise e# from NotImplementedError(stream)
                    info[key] = value
                if info.get('MAKE_VERSION', None):
                    return info['MAKE_VERSION']
                elif info.get('MAKE', None):
                    return None
                raise e
            finally:
                self.version_options = version_options


CHECKER['make'] = MakeDependency(command='make', minimum_version=None)


class EasyInstallDependency (CommandDependency):
    def _get_version(self):
        try:
            return super(EasyInstallDependency, self)._get_version()
        except DependencyError as e:
            version_stream = self.version_stream
            try:
                self.version_stream = 'stderr'
                stream = self._get_version_stream(expect=(1,))
                if 'option --version not recognized' in stream:
                    return 'unknown (possibly Setuptools?)'
            finally:
                self.version_stream = version_stream


CHECKER['easy_install'] = EasyInstallDependency(
    command='easy_install', long_name='Setuptools easy_install',
    minimum_version=None)


CHECKER['py.test'] = CommandDependency(
    command='py.test', version_stream='stderr',
    minimum_version=None)


class PathCommandDependency (CommandDependency):
    """A command that doesn't support --version or equivalent options

    On some operating systems (e.g. OS X), a command's executable may
    be hard to find, or not exist in the PATH.  Work around that by
    just checking for the existence of a characteristic file or
    directory.  Since the characteristic path may depend on OS,
    installed version, etc., take a list of paths, and succeed if any
    of them exists.
    """
    def _get_command_version_stream(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_version_stream(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_version(self):
        for path in self.paths:
            if _os.path.exists(path):
                return None
        raise DependencyError(
            checker=self,
            message=(
                'nothing exists at any of the expected paths for {0}:\n    {1}'
                ).format(
                self.full_name(),
                '\n    '.join(p for p in self.paths)))


for paths,name,long_name in [
        ([_os.path.join(_ROOT_PATH, 'Applications', 'Sublime Text 2.app')],
         'sublime-text', 'Sublime Text'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'TextMate.app')],
         'textmate', 'TextMate'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'TextWrangler.app')],
         'textwrangler', 'TextWrangler'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'Safari.app')],
         'safari', 'Safari'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'Xcode.app'),  # OS X >=1.7
          _os.path.join(_ROOT_PATH, 'Developer', 'Applications', 'Xcode.app'
                        )  # OS X 1.6,
          ],
         'xcode', 'Xcode'),
        ]:
    if not long_name:
        long_name = name
    CHECKER[name] = PathCommandDependency(
        command=None, paths=paths, name=name, long_name=long_name)
del paths, name, long_name  # cleanup namespace


class PythonPackageDependency (Dependency):
    def __init__(self, package, **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = package
        if 'and_dependencies' not in kwargs:
            kwargs['and_dependencies'] = []
        if 'python' not in kwargs['and_dependencies']:
            kwargs['and_dependencies'].append('python')
        super(PythonPackageDependency, self).__init__(**kwargs)
        self.package = package

    def _get_version(self):
        package = self._get_package(self.package)
        return self._get_version_from_package(package)

    def _get_package(self, package):
        try:
            return _importlib.import_module(package)
        except ImportError as e:
            raise DependencyError(
                checker=self,
                message="could not import the '{0}' package for {1}".format(
                    package, self.full_name()),
                )# from e

    def _get_version_from_package(self, package):
        try:
            version = package.__version__
        except AttributeError:
            version = None
        return version


for package,name,long_name,minimum_version,and_dependencies in [
        ('nose', None, 'Nose Python package',
         CHECKER['nosetests'].minimum_version, None),
        ('pytest', None, 'pytest Python package',
         CHECKER['py.test'].minimum_version, None),
        ('jinja2', 'jinja', 'Jinja', (2, 6), None),
        ('zmq', 'pyzmq', 'PyZMQ', (2, 1, 4), None),
        ('IPython', None, 'IPython Python package',
         CHECKER['ipython'].minimum_version, ['jinja', 'tornado', 'pyzmq']),
        ('argparse', None, 'Argparse', None, None),
        ('numpy', None, 'NumPy', None, None),
        ('scipy', None, 'SciPy', None, None),
        ('matplotlib', None, 'Matplotlib', None, None),
        ('pandas', None, 'Pandas', (0, 8), None),
        ('sympy', None, 'SymPy', None, None),
        ('Cython', None, None, None, None),
        ('networkx', None, 'NetworkX', None, None),
        ('mayavi.mlab', None, 'MayaVi', None, None),
        ('setuptools', None, 'Setuptools', None, None),
        ]:
    if not name:
        name = package
    if not long_name:
        long_name = name
    kwargs = {}
    if and_dependencies:
        kwargs['and_dependencies'] = and_dependencies
    CHECKER[name] = PythonPackageDependency(
        package=package, name=name, long_name=long_name,
        minimum_version=minimum_version, **kwargs)
# cleanup namespace
del package, name, long_name, minimum_version, and_dependencies, kwargs


class MercurialPythonPackage (PythonPackageDependency):
    def _get_version(self):
        try:  # mercurial >= 1.2
            package = _importlib.import_module('mercurial.util')
        except ImportError as e:  # mercurial <= 1.1.2
            package = self._get_package('mercurial.version')
            return package.get_version()
        else:
            return package.version()


CHECKER['mercurial'] = MercurialPythonPackage(
    package='mercurial.util', name='mercurial',
    long_name='Mercurial Python package',
    minimum_version=CHECKER['hg'].minimum_version)


class TornadoPythonPackage (PythonPackageDependency):
    def _get_version_from_package(self, package):
        return package.version

    def _get_parsed_version(self):
        package = self._get_package(self.package)
        return package.version_info


CHECKER['tornado'] = TornadoPythonPackage(
    package='tornado', name='tornado', long_name='Tornado', minimum_version=(2, 0))


class SQLitePythonPackage (PythonPackageDependency):
    def _get_version_from_package(self, package):
        return _sys.version

    def _get_parsed_version(self):
        return _sys.version_info


CHECKER['sqlite3-python'] = SQLitePythonPackage(
    package='sqlite3', name='sqlite3-python',
    long_name='SQLite Python package',
    minimum_version=CHECKER['sqlite3'].minimum_version)


class UserTaskDependency (Dependency):
    "Prompt the user to complete a task and check for success"
    def __init__(self, prompt, **kwargs):
        super(UserTaskDependency, self).__init__(**kwargs)
        self.prompt = prompt

    def _check(self):
        if _sys.version_info >= (3, ):
            result = input(self.prompt)
        else:  # Python 2.x
            result = raw_input(self.prompt)
        return self._check_result(result)

    def _check_result(self, result):
        raise NotImplementedError()


class EditorTaskDependency (UserTaskDependency):
    def __init__(self, **kwargs):
        self.path = _os.path.expanduser(_os.path.join(
                '~', 'swc-installation-test.txt'))
        self.contents = 'Hello, world!'
        super(EditorTaskDependency, self).__init__(
            prompt=(
                'Open your favorite text editor and create the file\n'
                '  {0}\n'
                'containing the line:\n'
                '  {1}\n'
                'Press enter here after you have done this.\n'
                'You may remove the file after you have finished testing.'
                ).format(self.path, self.contents),
            **kwargs)

    def _check_result(self, result):
        message = None
        try:
            with open(self.path, 'r') as f:
                contents = f.read()
        except IOError as e:
            raise DependencyError(
                checker=self,
                message='could not open {0!r}: {1}'.format(self.path, e)
                )# from e
        if contents.strip() != self.contents:
            raise DependencyError(
                checker=self,
                message=(
                    'file contents ({0!r}) did not match the expected {1!r}'
                    ).format(contents, self.contents))


CHECKER['other-editor'] = EditorTaskDependency(
    name='other-editor', long_name='')


class VirtualDependency (Dependency):
    def _check(self):
        return '{0} {1}'.format(
            self.or_pass['dependency'].full_name(),
            self.or_pass['version'])


for name,long_name,dependencies in [
        ('virtual-shell', 'command line shell', (
            'bash',
            'dash',
            'ash',
            'zsh',
            'ksh',
            'csh',
            'tcsh',
            'sh',
            )),
        ('virtual-editor', 'text/code editor', (
            'emacs',
            'xemacs',
            'vim',
            'vi',
            'nano',
            'gedit',
            'kate',
            'notepad++',
            'sublime-text',
            'textmate',
            'textwrangler',
            'other-editor',  # last because it requires user interaction
            )),
        ('virtual-browser', 'web browser', (
            'firefox',
            'google-chrome',
            'chromium',
            'safari',
            )),
        ('virtual-pypi-installer', 'PyPI installer', (
            'easy_install',
            'pip',
            )),
        ]:
    CHECKER[name] = VirtualDependency(
        name=name, long_name=long_name, or_dependencies=dependencies)
del name, long_name, dependencies  # cleanup namespace


def _print_info(key, value, indent=19):
    print('{0}{1}: {2}'.format(key, ' '*(indent-len(key)), value))

def print_system_info():
    print("If you do not understand why the above failures occurred,")
    print("copy and send the *entire* output (all info above and summary")
    print("below) to the instructor for help.")
    print()
    print('==================')
    print('System information')
    print('==================')
    _print_info('os.name', _os.name)
    _print_info('os.uname', _platform.uname())
    _print_info('platform', _sys.platform)
    _print_info('platform+', _platform.platform())
    for pversion in (
            'linux_distribution',
            'mac_ver',
            'win32_ver',
            ):
        value = getattr(_platform, pversion)()
        if value[0]:
            _print_info(pversion, value)
    _print_info('prefix', _sys.prefix)
    _print_info('exec_prefix', _sys.exec_prefix)
    _print_info('executable', _sys.executable)
    _print_info('version_info', _sys.version_info)
    _print_info('version', _sys.version)
    _print_info('environment', '')
    for key,value in sorted(_os.environ.items()):
        print('  {0}={1}'.format(key, value))
    print('==================')

def print_suggestions(instructor_fallback=True):
    print()
    print('For suggestions on installing missing packages, see')
    print('http://software-carpentry.org/setup/')
    print('')
    print('For instructings on installing a particular package,')
    print('see the failure message for that package printed above.')
    if instructor_fallback:
        print('')
        print('For help, email the *entire* output of this script to')
        print('your instructor.')


if __name__ == '__main__':
    import optparse as _optparse

    parser = _optparse.OptionParser(usage='%prog [options] [check...]')
    epilog = __doc__
    parser.format_epilog = lambda formatter: '\n' + epilog
    parser.add_option(
        '-v', '--verbose', action='store_true',
        help=('print additional information to help troubleshoot '
              'installation issues'))
    options,args = parser.parse_args()
    try:
        passed = check(args)
    except InvalidCheck as e:
        print("I don't know how to check for {0!r}".format(e.check))
        print('I do know how to check for:')
        for key,checker in sorted(CHECKER.items()):
            if checker.long_name != checker.name:
                print('  {0} {1}({2})'.format(
                        key, ' '*(20-len(key)), checker.long_name))
            else:
                print('  {0}'.format(key))
        _sys.exit(1)
    if not passed:
        if options.verbose:
            print()
            print_system_info()
            print_suggestions(instructor_fallback=True)
        _sys.exit(1)

########NEW FILE########
__FILENAME__ = swc-windows-installer
#!/usr/bin/env python

"""Software Carpentry Windows Installer

Helps mimic a *nix environment on Windows with as little work as possible.

The script:
* Provides standard ipython operation for msysgit
* Provides standard nosetests behavior for msysgit
* Installs nano and makes it accessible from msysgit

To use:

1. Install Anaconda CE Python distribution
   http://continuum.io/anacondace.html
2. Install msysgit
   http://code.google.com/p/msysgit/downloads/list?q=full+installer+official+git
3. Run swc_windows_installer.py
   You should be able to simply double click the file in Windows
"""

try:  # Python 3
    from io import BytesIO as _BytesIO
except ImportError:  # Python 2
    from StringIO import StringIO as _BytesIO
import os.path
try:  # Python 3
    from urllib.request import urlopen as _urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen as _urlopen
import zipfile


def install_nano(install_directory):
    """Download and install the nano text editor"""
    url = "http://www.nano-editor.org/dist/v2.2/NT/nano-2.2.6.zip"
    r = _urlopen(url)
    nano_zip_content = _BytesIO(r.read())
    nano_zip = zipfile.ZipFile(nano_zip_content)
    nano_files = ['nano.exe', 'cygwin1.dll', 'cygintl-8.dll',
                  'cygiconv-2.dll', 'cyggcc_s-1.dll']
    for file_name in nano_files:
        nano_zip.extract(file_name, install_directory)

def create_ipython_entry_point(python_scripts_directory):
    """Creates a terminal-based IPython entry point for msysgit"""
    contents = '\n'.join([
            '#!/usr/bin/env python',
            'from IPython.frontend.terminal.ipapp import launch_new_instance',
            'launch_new_instance()',
            '',
            ])
    with open(os.path.join(python_scripts_directory, 'ipython'), 'w') as f:
        f.write(contents)

def create_nosetests_entry_point(python_scripts_directory):
    """Creates a terminal-based nosetests entry point for msysgit"""
    contents = '\n'.join([
            '#!/usr/bin/env/ python',
            'import sys',
            'import nose',
            "if __name__ == '__main__':",
            '    sys.exit(nose.core.main())',
            '',
            ])
    with open(os.path.join(python_scripts_directory, 'nosetests'), 'w') as f:
        f.write(contents)


def main():
    python_scripts_directory = "C:\\Anaconda\\Scripts\\"
    #python_scripts_directory = "./scripts/"
    create_ipython_entry_point(python_scripts_directory)
    create_nosetests_entry_point(python_scripts_directory)
    install_nano(python_scripts_directory)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = generate_data
import sys
import os
import math
from random import choice, randint, random
import calendar

class Person:
    maxCI = 25
    # teenagers are hereby declared to be between 11 and 20 years old
    birthyears = range(1991,2000)
    repeatFraction = 0.1
    
    names = ['john', 'paul', 'george', 'ringo',\
        'baby','scary','posh','ginger','madonna',\
        'prince','robyn','beyonce','jay'] 
    words =['Beatle','Spice','Backstreet','Sync','Jonas',\
        'Lennon','McCartney','Starr','Harrison','Z',\
        'Carrot','Broccoli','Asparagus','Beet']
    CIs=range(1,maxCI+1)
    birthmonths= range(1,13)
    #ensure unique ids
    serialNum=173
    sexes=['M','F','N']

    def age(self, curyr=2011, curmo=11):
        return curyr+(1.*curmo-1.)/12. - self.birthyear - 1.*(self.birthmonth-1.)/12.

    def __init__(self):
        self.subject = choice(Person.names)+choice(Person.words)+ ('%03d' % Person.serialNum)
        Person.serialNum = Person.serialNum + 1

        self.birthyear  = choice(Person.birthyears)
        self.birthmonth = choice(Person.birthmonths)
   
        self.sex = choice(Person.sexes)
        age = self.age(2011,11)
        self.CI = choice(Person.CIs) 

        # newer CIs have better volume, discrimination;
        # range goes down with age.  (say). 

        CInewness = (self.CI-1.)/(1.*max(Person.CIs))
        # from oldest CI to newest, gain 2 volume pts: 
        self.trueVolume = randint(0,4)+randint(1,4)+round(2.*CInewness)

        # from oldest CI to newest, gain 3 discrimination pts: 
        self.trueDiscrimination = randint(0,3)+randint(1,4)+round(3.*CInewness)
        
        # 21-year-olds would lose 3 range points over 10 year olds (say)
        self.trueRange = randint(0,4)+randint(1,6)+round((10.-(self.age()-11.))*3./10.)

        # Most people don't repeat; those that do take the test 2-5 times
        if (random() > Person.repeatFraction):
            self.repeats = 1
        else:
            self.repeats=choice(range(2,6))


from numpy import polyfit, array
def test_peopleCorrelations():
    testpeople = []
    npeople = 4000
    for pnum in xrange(1,npeople):
        testpeople.append(Person())

    data = [[p.age(), p.CI, p.trueVolume, p.trueRange, p.trueDiscrimination] for p in testpeople]
    ages, cis, vols, ranges, discs = zip(*data)

    CIVolParam, dummy   = polyfit(cis, vols, 1) 
    CIRangeParam, dummy = polyfit(cis, ranges, 1) 
    CIDiscParam, dummy  = polyfit(cis, discs, 1)

    AgeVolParam, dummy   = polyfit(ages, vols, 1) 
    AgeRangeParam, dummy = polyfit(ages, ranges, 1) 
    AgeDiscParam, dummy  = polyfit(ages, discs, 1) 

    assert CIVolParam > 0.75*(2./25.) and CIVolParam < 1.25*(2./25.)
    assert CIDiscParam > 0.75*(3./25.) and CIDiscParam < 1.25*(3./25.)
    assert AgeRangeParam < 0.75*(-3./10.) and AgeRangeParam > 1.25*(-3./10.)

    zeroTol = 0.03
    assert abs(CIRangeParam) < zeroTol
    assert abs(AgeVolParam)  < zeroTol
    assert abs(AgeDiscParam) < zeroTol



class Measurement:
    incompleteFraction = 0.05
    serialNum = 211
    def randomDate(self):
        hrs = range(8,17)
        mins = range(1,60)
        secs = range(1,60)
        months = range(5,10)

        month = choice(months)
        monthname = calendar.month_abbr[month]
        day = choice(range(1,calendar.monthrange(2011, month)[1]))
        dayname = calendar.day_abbr[calendar.weekday(2011, month, day)]
        hr = choice(hrs)
        min = choice(mins)
        sec = choice(secs)
        
        datestring = '%s %s %d %02d:%02d:%02d %s' % (dayname, monthname, day, hr, min, sec, '2011')
        return [datestring, month, day, hr, min, sec]

    def limit(self,n):
        if n < 1 :
            n = 1
        if n > 10 :
            n = 10
        return n 

    def __init__(self, p):
        """Generate a result"""
        self.person = p
        self.datestring, self.month, self.day, self.hr, self.min, self.sec = self.randomDate();

        self.serialNum = Measurement.serialNum
        Measurement.serialNum = Measurement.serialNum + 1

        # +/- 1 random measurement error
        self.volume = self.person.trueVolume + choice([-1,0,0,0,+1])
        self.range  = self.person.trueRange + choice([-1,0,0,0,+1])
        self.discrimination  = self.person.trueDiscrimination + choice([-1,0,0,0,+1])

        self.volume = self.limit(self.volume)
        self.range = self.limit(self.range)
        self.discrimination = self.limit(self.discrimination)

        # before this date, things were being recorded 0..9 rather than 1..10
        fixmonth = 8
        fixday = 18
        fixhr = 10

        fixdate = fixmonth*10000 + fixday*100 + fixhr 
        checkdate = self.month*10000 + self.day*100 + self.hr 
        if checkdate < fixdate:
            self.volume = self.volume - 1
            self.range = self.range - 1
            self.discrimination = self.discrimination - 1
    
        if (random() < Measurement.incompleteFraction):
            self.discrimination = None
        

    def __str__(self):
        text = '# ' + '\n'
        text += "%s: %s\n" % ( 'Reported', self.datestring )
        text += "%s: %s\n" % ( 'Subject',  self.person.subject )
        text += "%s: %4d/%02d\n" % ( 'Year/month of birth', self.person.birthyear,  self.person.birthmonth )
        text += "%s: %s\n" % ( 'Sex', self.person.sex )
        text += "%s: %d\n" % ( 'CI type', self.person.CI )
        text += "%s: %d\n" % ( 'Volume', self.volume )
        text += "%s: %d\n" % ( 'Range', self.range )
        if self.discrimination is None :
            text += "%s: \n" % ( 'Discrimination' )
        else:
            text += "%s: %d\n" % ( 'Discrimination', self.discrimination )
    
        return text

class Datataker:
    names = ['angela', 'JamesD', 'jamesm', 'Frank_Richard',\
        'lab183','THOMAS','alexander','Beth','Lawrence',\
        'Toni', 'gerdal', 'Bert', 'Ernie', 'olivia', 'Leandra',\
        'sonya_p', 'h_jackson'] 
    filenamestyles = ['data_%d','Data%04d','%d','%04d','audioresult-%05d']
    suffixstyles = ['.dat','.txt','','','.DATA']
    tookNotesFraction = 0.5
    notes = ['Took data on Thursday and Friday until 4pm;\nAll day saturday.\n',\
             'Contact Janice about new calibration for data in August.\n',\
             'Submission of hours last week shows only 7 hours because \none was spent cleaning the lab.\n',\
             'Had some trouble accessing data submission form on Saturday,\nso fewer submissions then.\n',\
             'Third subject had real problems with the discrimiation test, so omitted.\n',\
             'Discrimination test seems kind of flaky - had to skip in several cases\n',\
             'Fuse blew midway through this weeks data taking,\nfewer results than last week.\n']
    notefilenames = ['notes.txt','NOTES','ReadMe','misc.txt','About']

    def __init__(self):
        self.name = choice(Datataker.names)
        Datataker.names.remove(self.name)
        self.filenameprefix = choice(Datataker.filenamestyles)
        self.filenamesuffix = choice(Datataker.suffixstyles)
        self.measures = []
        self.tookNotes = False
        if (random() < Datataker.tookNotesFraction) :
            self.tookNotes = True 
            self.notes = choice(Datataker.notes)
            self.noteFilename = choice(Datataker.notefilenames)

    def addmeasurement(self,measurement):
        self.measures.append(measurement)

    def write(self):
        os.mkdir(self.name)
        os.chdir(self.name)

        if (self.tookNotes):
            fname = self.noteFilename
            file = open(fname, 'w')
            file.write(self.notes)
            file.close()

        for m in self.measures:
            fname = self.filenameprefix % m.serialNum + self.filenamesuffix
            file = open(fname, 'w')
            file.write(str(m))
            file.close()
        os.chdir('..')
            
 
def main():
    #test_peopleCorrelations()

    npeople = 300 # should generate ~ .9*300 + 3.5*.1*300 ~ 375 files
    nfiles = 351

    people = []
    for pnum in range(npeople):
        people.append(Person())

    measurements = []
    for p in people:
        for m in range(p.repeats):
            measurements.append(Measurement(p))

    nexperimenters = 7
    experimenters = []
    for i in range(nexperimenters):
        experimenters.append(Datataker())

    for fnum in xrange(min(len(measurements), nfiles)):
        ex = choice(experimenters)
        ex.addmeasurement(measurements[fnum]) 

    os.mkdir('data')
    os.chdir('data')
    for ex in experimenters:
        ex.write()
    os.chdir('..')

if __name__=='__main__':
    sys.exit(main())


########NEW FILE########
