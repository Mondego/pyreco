__FILENAME__ = b1sol
## solutions to the breakout #1 (Day 1)
sent = ""
while True:
    newword = raw_input("Please enter a word in the sentence (enter . ! or ? to end.): ")
    if newword == "." or newword == "?" or newword == "!":
        if len(sent) > 0:
            # get rid of the nasty space we added in
            sent = sent[:-1]
        sent += newword
        break
    
    sent += newword + " "
    print "...currently: " + sent
print "--->" + sent
###  created by Josh Bloom at UC Berkeley, 2010,2012,2013 (ucbpythonclass+bootcamp@gmail.com)
########NEW FILE########
__FILENAME__ = breakout1
## solutions to the breakout #1 (Day 1)
sent = ""
while True:
    newword = raw_input("Please enter a word in the sentence (enter . ! or ? to end.): ")
    if newword == "." or newword == "?" or newword == "!":
        if len(sent) > 0:
            # get rid of the nasty space we added in
            sent = sent[:-1]
        sent += newword
        break
    
    sent += newword + " "
    print "...currently: " + sent
print "--->" + sent
###  created by Josh Bloom at UC Berkeley, 2010,2012 (ucbpythonclass+bootcamp@gmail.com)

########NEW FILE########
__FILENAME__ = breakout2
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# <p class="title">Breakout 2 Solutions</p>
# 

# ### First, copy over the airport and flight information from [airline.py](https://raw.github.com/profjsb/python-bootcamp/master/DataFiles_and_Notebooks/02_AdvancedDataStructures/airline.py). ###


airports = {"DCA": "Washington, D.C.", "IAD": "Dulles", "LHR": "London-Heathrow", \
            "SVO": "Moscow", "CDA": "Chicago-Midway", "SBA": "Santa Barbara", "LAX": "Los Angeles",\
            "JFK": "New York City", "MIA": "Miami", "AUM": "Austin, Minnesota"}


# airline, number, heading to, gate, time (decimal hours) 
flights = [("Southwest",145,"DCA",1,6.00),("United",31,"IAD",1,7.1),("United",302,"LHR",5,6.5),\
           ("Aeroflot",34,"SVO",5,9.00),("Southwest",146,"CDA",1,9.60), ("United",46,"LAX",5,6.5),\
           ("Southwest",23,"SBA",6,12.5),("United",2,"LAX",10,12.5),("Southwest",59,"LAX",11,14.5),\
           ("American", 1,"JFK",12,11.3),("USAirways", 8,"MIA",20,13.1),("United",2032,"MIA",21,15.1),\
           ("SpamAir",1,"AUM",42,14.4)]


# Sort the list of flights.
flights.sort() 

# Print out the header. the \t character prints a tab.
print "Flight    \tDestination\t\tGate\tTime"
print "-"*53 #53 instances of the "-" character

# Loop through each of the flight tuples in the sorted list
# Recall that each tuple contains the elements: (airline, number, destination lookup code, gate, time)
for flight in flights:
    # Use the dest lookup code (3rd element of the flight tuple) to get the full destination string from the airports dict
    dest = airports[flight[2]]
    dest += " "*(20 - len(dest))  # add the appropriate amount of whitespace after the Destination string
    # Print the nicely formatted string. Don't forget to convert int and float types to strings using str()
    print flight[0] + " " + str(flight[1]) + "\t" + dest + "\t" + str(flight[3]) + "\t" + str(flight[4])

# Sorting by Departure Time
# ### Sorting the information by time requires a bit more coding. ###
# First, we create a new list, time_ordered_flights, which initially just contains the first element of the list flights.


# Create a new list, time_ordered, which initially just contains the first element of the list flights
time_ordered_flights = [flights[0]]

print time_ordered_flights

# We then loop through the remaining flights and insert it into the proper 
# position in time_ordered_flights by comparing the time element in each flight 
# tuple (at the fifth index position).
# We determine where the current flight belongs by manually comparing the times 
# of the flights  already added to time_ordered_flights.  (This is really 
# trivial with lambda functions, which you'll learn later.)


# Iterate through each of the remaining elements in flights to see where it 
# should go in the sorted list
for flight in flights[1:]:
    # Does it belong in the beginning?
    # is current flight's time less than the time in the first list element?
    if flight[4] < time_ordered_flights[0][4]: 
        # insert the flight tuple at position 0 in the list
        time_ordered_flights.insert(0,flight)   
        continue
    ## ... or the end?
    # is current flight's time greater than the time in the last list element?
    if flight[4] > time_ordered_flights[-1][4]:
        # append the flight tuple to the end of the list 
        time_ordered_flights.append(flight) 
        continue
    ## Or is it in the middle? 
    # Loop through each element and see if the current flight is between two adjacent ones
    ## note that range(N) returns a list [0, 1, ... , N-1] 
    for i in range(len(time_ordered_flights) - 1): 
        if flight[4] >= time_ordered_flights[i][4] and flight[4] <= time_ordered_flights[i+1][4]:
            time_ordered_flights.insert(i+1,flight) # insert the flight tuple at position i+1 in the list
            break


print "Flight    \tDestination\t\tGate\tTime"
print "-"*53
for flight in time_ordered_flights:
    dest = airports[flight[2]]
    dest += " "*(20 - len(dest))
    print flight[0] + " " + str(flight[1]) + "\t" + dest + "\t" + str(flight[3]) + "\t" + str(flight[4])  



# ### One line sorting solution. ###
# We can use the operator.itemgetter() function as the key in sort and sort by the time (4th) element.


import operator
flights.sort(key=operator.itemgetter(4))
print "Flight    \tDestination\t\tGate\tTime"
print "-"*53
for flight in flights:
    dest = airports[flight[2]]
    dest += " "*(20 - len(dest))
    print flight[0] + " " + str(flight[1]) + "\t" + dest + "\t" + str(flight[3]) + "\t" + str(flight[4])

# Alternate printing solution 

print "%.20s %.20s %.6s %.5s" % ("Flight"+20*' ', "Destination"+20*' ', "Gate"+20*' ', "Time"+20*' ')
print "-"*53
for flight in flights:
    print "%.20s %.20s %.6s %.5s" % (flight[0] + ' ' + str(flight[1])+20*' ', airports[flight[2]]+20*' ', str(flight[3])+20*' ', str(flight[4])+20*' ')
########NEW FILE########
__FILENAME__ = talktools
"""Tools to style a talk."""

from IPython.display import HTML, display, YouTubeVideo

def prefix(url):
    prefix = '' if url.startswith('http') else 'http://'
    return prefix + url


def simple_link(url, name=None):
    name = url if name is None else name
    url = prefix(url)
    return '<a href="%s" target="_blank">%s</a>' % (url, name)


def html_link(url, name=None):
    return HTML(simple_link(url, name))


# Utility functions
def website(url, name=None, width=800, height=450):
    html = []
    if name:
        html.extend(['<div class="nb_link">',
                     simple_link(url, name),
                     '</div>'] )

    html.append('<iframe src="%s"  width="%s" height="%s">' % 
                (prefix(url), width, height))
    return HTML('\n'.join(html))


def nbviewer(url, name=None, width=800, height=450):
    return website('nbviewer.ipython.org/url/' + url, name, width, height)

# Load and publish CSS
style = HTML(open('style.css').read())

display(style)

########NEW FILE########
__FILENAME__ = age
#!/usr/bin/env python
"""
  PYTHON BOOT CAMP BREAKOUT3 SOLUTION;
      created by Josh Bloom at UC Berkeley, 2010
      (ucbpythonclass+bootcamp@gmail.com)
      modified by Katy Huff at UC Berkeley, 2013
"""

# First, we want to import datetime, which is a python module for dates
# and times and such.
import datetime

# Next, we want to use datetime.datetime() to create a variable representing 
# when John Cleese was born.
# Note that utcnow() gives the universal time, while .now() gives the
# local time. We're ignoring timezone stuff here.
born = datetime.datetime(1939, 10, 27)

# Then use datetime.datetime.now() to create a variable representing now.
now = datetime.datetime.now()

# Next, subtract the two, forming a new variable, which will be a
# datetime.timedelta() object.
cleese_age = now - born

# Finally, print that variable.
print cleese_age

# Grab just the days :
print "days John Cleese has been alive : ", cleese_age.days

# There is no hours data member, so let's multiply to find the hours :
print "hours John Cleese has been alive : ", cleese_age.days * 24

# What will be the date in 1000 days from now?
td = datetime.timedelta(days=1000)

# Print it.
print "in 1000 days it will be ", now + td  # this is a datetime object

########NEW FILE########
__FILENAME__ = age1
#!/usr/bin/env python 
"""
  PYTHON BOOT CAMP BREAKOUT3 SOLUTION; 
      created by Josh Bloom at UC Berkeley, 2010 
      (ucbpythonclass+bootcamp@gmail.com)
      modified by Katy Huff at UC Berkeley, 2013
"""

import datetime
import sys

def days_from_now(ndays):
  """Returns the date ndays from now"""
  now = datetime.datetime.now()
  new = now + datetime.timedelta(int(ndays)) 
  return "in " + str(ndays) + " days the date will be : " + str(new)

def days_since(year, month, day): 
  """Returns a string reporting the number of days since some time"""
  now = datetime.datetime.now()
  then = datetime.datetime(year, month, day)
  diff = now - then
  return "days since then . . . " + str(diff.days)

if __name__ == "__main__":
  """
  Executed only if run from the command line.
  call with
  ageI.py <year> <month> <day>
  to list the days since that date
  or

  ageI.py <days>
  to list the dat in some number of days
  """
  if len(sys.argv) == 2 :
    result = days_from_now(int(sys.argv[1]))
  elif len(sys.argv) == 4 :
    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    result = days_since(year, month, day)
  else : 
    result = "Error : don't know what to do with "+repr(sys.argv[1:])

  print result

########NEW FILE########
__FILENAME__ = Breakout6Solution
"""
  PYTHON BOOT CAMP ADVANCED STRINGS BREAKOUT SOLUTION; 
  created by Adam Morgan at UC Berkeley, 2010 (ucbpythonclass+bootcamp@gmail.com)
"""
#import regular expressions
import re
import sys

def reverse_extension(filename):
    '''Given a filename, find and reverse the extension at the end'''
    # First split the filename string by periods.  The last item in the 
    # resultant list (index -1) is assumed to be the extension.
    extension = filename.split('.')[-1]
    # Now let's strip off this old extension from the original filename
    base_name = filename.rstrip(extension)
    # And reverse the extension:
    r_extension = extension[::-1]
    # Now append the reversed extension to the base
    return base_name + r_extension

def count_occurances(filename, substring):
    ''' Count all occurances of the substring in the file'''
    my_file = open(filename,'r')
    string_file = my_file.read()
    count = string_file.count(substring)
    my_file.close()
    return count

def find_and_halve_numbers(line):
    ''' Find all occurances of numbers in a line, and divide them by 2
    
    Note! We're using regular expressions here to find the groups of numbers.  
    This is complex and you aren't expected to know how to do this.  The 
    rest of the function is straightforward, however.
    
    Another possible solution would be to split each line word by word
    with split() and test whether each "word" is a number
    '''
    split_line = re.split("(\d+)",line)    
    new_line = ''
    for item in split_line:
        if item.isdigit():
            # If the string contains only digits, convert to integer, divide by 2
            item = str(int(item)/2)
        new_line += item
    return new_line

def do_operations(filename):
    """Given a file, perform the following operations:
    1) Reverse the extension of the filename
    2) Delete every other line
    3) change occurance of words:
        love -> hate
        not -> is
        is -> not
    4) sets every number to half its original value
    5) count the number of words "astrology" and "physics"
    """
    # Open file for reading
    orig_file = open(filename,'r')
    # Get new filename for writing
    new_filename = reverse_extension(filename)
    new_file = open(new_filename,'w')
    
    index = 0
    # Loop over every line in the file
    for line in orig_file.readlines():
        index += 1
        # if we're on an odd numbered line, perform operations and write 
        # (this effectively deletes every other line)
        if index%2 == 1:
            # make the desired replacements
            newline = line.replace(' love ',' hate ')
            # make temp_is string so we don't overwrite all new instances of 'is'
            newline = newline.replace(' not ',' temp_is ')
            newline = newline.replace(' is ',' not ')
            newline = newline.replace(' temp_is ',' is ')
            
            # Divide all numbers by 2
            newline = find_and_halve_numbers(newline)
            
            # Write new line
            new_file.write(newline)
        
    print 'There are %i occurances of astrology and %i occurances of physics' % \
            (count_occurances(filename,'astrology'),count_occurances(filename,'physics'))
    orig_file.close()
    new_file.close()
    print 'Wrote %s' % (new_filename)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        do_operations(sys.argv[1])
    else:
        print "dont know what to do with", repr(sys.argv[1:])

########NEW FILE########
__FILENAME__ = Breakout7Solution
import numpy as np
from random import randint

def generate_function(X,Y, voc, max_try=1000000, max_chars=10):
    ''' find the analytic form that describes Y on X '''
    tries = []
    for n in xrange(max_try):
        ## make some random function using the vocabulary
        thefunc = "".join([voc[randint(0,len(voc)-1)] for x in range(randint(1,max_chars))])
        ## construct the python statement, declaring the lambda function and evaluating it on X
        mylam = "y = lambda x: " + thefunc + "\n"
        mylam += "rez = y(X)"
        try:
            ## this may be volitile so be warned!
            ## Couch everything in error statements, and
            ##  simply throw away functions that aren't reasonable
            exec(mylam)
        except:
            continue
        try: 
            tries.append( ( (abs(rez - Y).sum()) ,thefunc))
            if (abs(rez - Y)).sum() < 0.0001:
                ## we got something really close
                break
        except:
            pass
        del rez
        del y
        
    ### numpy arrays handle NaN and INF gracefully, so we put
    ### answer into an array before sorting
    a = np.array(tries,dtype=[('rez','f'),("func",'|S10')])
    a.sort()
    
    if a[0]["rez"] < 0.001:
        print "took us ntries = {0}, but we eventually found that '{1}' is functionally equivalent to f(X)".format(n,a[0]["func"])
    else:
        print "after ntries = {0}, we found that '{1}' is close to f(x) (metric = {2})".format(n,a[0]["func"],a[0]["rez"])
    
    return a[0]
    
    
    

voc = ["x","x"," ","+","-","*","/","1","2","3"]

x_array       = np.arange(-3,3,0.4)
real_function = x_array**2 + x_array
generate_function(x_array, real_function, voc, 100)

########NEW FILE########
__FILENAME__ = OOP_I_solutions
###
# Procedural approach
import math
def perimeter(polygon):
    """Given a list of vector vertices (in proper order), 
    returns the perimeter for the associated polygon."""
    sum = 0
    for i in range(len(polygon)):
        vertex1 = polygon[i]
        vertex2 = polygon[(i+1) % len(polygon)]
        distance = math.sqrt(pow(vertex2[0]-vertex1[0],2) + \
                             pow(vertex2[1]-vertex1[1],2))
        sum += distance
    return sum 

perimeter([[0,0],[1,0],[1,1],[0,1]])	# Returns 4.0
perimeter([[0,-2],[1,1],[3,3],[5,1],[4,0],[4,-3]])
# Returns 17.356451097651515

###
# Object-oriented approach
class Polygon:
    """A new class named Polygon."""
    def __init__(self, vertices=[]):
        self.vertices = vertices
        print "(Creating an instance of the class Polygon)"
    def perimeter(self):
        sum = 0
        for i in range(len(self.vertices)):
            vertex1 = self.vertices[i]
            vertex2 = self.vertices[(i+1) % len(self.vertices)]
            distance = math.sqrt(pow(vertex2[0]-vertex1[0],2)+\
                                 pow(vertex2[1]-vertex1[1],2))
            sum += distance
        return sum

a = Polygon([[0,-2],[1,1],[3,3],[5,1],[4,0],[4,-3]])
a.perimeter()
# Returns 17.356451097651515


########NEW FILE########
__FILENAME__ = hw2sol

"""
This is a solution to the Homework #2 of the Python Bootcamp

The basic idea is to create a simulation of the games Chutes and Ladders, 
to gain some insight into how the game works and, more importantly,
to exercise new-found skills in object oriented programming within Python.

The setup for the homework is given here:
 http://tinyurl.com/homework2-bootcamp

Usage:
  python hw2sol.py

UC Berkeley 
J. Bloom 2013 
"""
import random
import numpy as np

## here's a layout of the board
## I just made this by hand looking at the picture of the board:
##     http://i.imgur.com/Sshgk4X.jpg
## the key is the starting point, the value is the ending point
board = {1: 38, 4: 14, 9: 31, 16: 6, 21: 42, 28: 84, 36: 44, 48: 26, 49: 11,
         51: 67, 56: 53, 62: 19, 64: 60, 71: 91, 80: 100, 87: 24, 93: 73, 95: 75, 98: 78}

class Pawn(object):
	""" representation of a player in the game."""

	def __init__(self,run_at_start=False):
		## start off at the beginning
		self.loc = 0
		self.path = []
		self.n_throws = 0
		self.n_chutes = 0
		self.n_ladders = 0
		self.reached_end = False
		if run_at_start:
			self.play_till_end()

	def play_till_end(self):
		""" keep throwing new random dice rolls until the player gets to 100 """

		while not self.reached_end:
			## throw a spin
			throw = random.randint(1,6)
			self.n_throws += 1

			# if we're near the end then we have to get exactly 100
			if throw + self.loc > 100:
				## oops. Can't move.
				self.path.append(self.loc)
				continue

			self.loc += throw

			# keep track of the path is took to get there
			self.path.append(self.loc)

			if board.has_key(self.loc):
				## new location due to chute or ladder
				if self.loc > board[self.loc]:
					self.n_chutes += 1
				else:
					self.n_ladders += 1

				self.loc = board[self.loc]
				self.path.append(self.loc)

			if self.loc == 100:
				self.reached_end = True

	def __str__(self):
		""" make a nice pretty representation of the player attributes """
		s = """n_throws = %i ; n_ladders = %i  ; n_chutes = %i 
		       path = %s""" % (self.n_throws,self.n_ladders, self.n_chutes, str(self.path))
		return s      

class Game(object):
	""" simulate a game between a certain number of players """

	def __init__(self,n_players=2):
		self.n_players = n_players
		self.run()

	def run(self):
		""" actually run the Game, by making a new list of Pawns 
			we play ALL Pawns to the end...this has the advantage of 
			allowing us to run multiple simulations of Pawn movements
			and keep track of 1st, 2nd, 3rd, ... place winners.
		"""

		self.pawns = [Pawn(run_at_start=True) for i in range(self.n_players)]
		self.settle_winner()

	def settle_winner(self):
		""" go through the Game and figure out who won"""

		throws = [x.n_throws for x in self.pawns]
		self.min_throws, self.max_throws  = min(throws), max(throws)

		## if it's the same number, then make sure the Pawn that went first wins
		self.winning_order = [x for x,y in sorted(enumerate(throws), key = lambda x: (x[1],x[0]))]

		self.throws = throws

		## what's the first throw value and how long did it take to get to 100?
		self.first_throw_length = [(x.path[0],x.n_throws) for x in self.pawns ]

class Simulate(object):
	""" Play multiple games and spit out some of the answers to the homework questions,
	    basically high-level statistics
	"""
	def __init__(self,num_games = 1000, num_players = 4):
		self.num_games = num_games
		self.num_players = num_players

	def run(self):
		self.shortest_path = []
		self.longest_path  = []
		#self.winner_times  = dict( [(i,0) for i range(num_players)] )
		self.all_lengths = []
		self.first_throws = dict( [(i+1,[]) for i in range(6)])

		self.first_turn_wins = []

		# NB: I'm running these games in serial. Would be nice to make use of my
		# multicore environment to do this instead. Or even a cluster. Soon....
		# TODO: Parallelize me!
		for i in range(self.num_games):
			g = Game(n_players=self.num_players)

			# save the shortest and longest paths
			if self.shortest_path == [] or (g.min_throws < len(self.shortest_path)):
				self.shortest_path = g.pawns[g.winning_order[0]].path
			if self.longest_path == [] or (g.max_throws > len(self.longest_path)):
				self.longest_path = g.pawns[g.winning_order[-1]].path

			## save all the lengths
			self.all_lengths.extend(g.throws)

			# save the first moves
			for ft in g.first_throw_length:
				#print ft
				self.first_throws[ft[0]].append(ft[1])

			# save the winning orders:
			self.first_turn_wins.append(int(g.winning_order[0] == 0))

	def __str__(self):
		avg_throws = np.array(self.all_lengths).mean()
		s = "1. What is the average number of turns a player must take before she gets to 100?\n"
		s += "%.2f\n\n" % avg_throws

		s+= "2. What is the minimal number of turns in the simulation before getting to 100?\n"
		s+= str(len(self.shortest_path) ) + "\n"
		s+= "What was the sequence of values in the spin in each turn?\n"
		s+= str(self.shortest_path) +"\n"
		s+= "What was the longest number of turns?\n"
		s+= str(len(self.longest_path)) + "\n\n"
		s+= "3. What is the ordering of initial spins that gives, on average, the quickest path to 100?\n"
		tmp= [(np.array(self.first_throws[t]).mean(), t) for t in self.first_throws.keys()]
		tmp.sort()
		s+= str(tmp) + " \n"
		s+= "What about the median?\n"
		tmp= [(np.median(np.array(self.first_throws[t])), t) for t in self.first_throws.keys()]
		tmp.sort()
		s+= str(tmp) + " \n\n"

		s+= "4. What is the probability that someone who goes first will win in a 2 and 4 person game?\n"
		s+= str(float(np.array(self.first_turn_wins).sum())/len(self.first_turn_wins)) + "\n"
		s+= "  random expectation is %f\n" % (1.0/self.num_players)
		return s

def test_Pawn():
	p = Pawn()
	p.play_till_end()
	print p

def test_Game():
	g = Game(4)
	g.settle_winner()


if __name__ == "__main__":
	print "HW#2 solutions"
	print "UC Berkeley Python Bootcamp 2013"

	nsim = 10000
	for n_players in [2,4]:
		print "*"*60
		print "Running a 10000 game simulation with {0} players".format(n_players)
		s = Simulate(num_games =nsim, num_players=n_players)
		s.run()
		print s



########NEW FILE########
__FILENAME__ = hello
print "Hello World!"

########NEW FILE########
__FILENAME__ = temp1
###  PYTHON BOOT CAMP EXAMPLE; 
###  created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)
###  all rights reserved 2012 (c)
###  https://github.com/profjsb/python-bootcamp

# set some initial variables. Set the initial temperature low
faren = -1000

# we dont want this going on forever, let's make sure we cannot have too many attempts
max_attempts = 6
attempt = 0

while faren < 100:
     # let's get the user to tell us what temperature it is
     newfaren = float(raw_input("Enter the temperature (in Fahrenheit): "))
     if newfaren > faren:
             print "It's getting hotter"
     elif newfaren < faren:
             print "It's getting cooler"
     else:
         # nothing has changed, just continue in the loop
         continue
     faren = newfaren # now set the current temp to the new temp just entered
     attempt += 1 # bump up the attempt number
     if attempt >= max_attempts:
         # we have to bail out
         break

if attempt >= max_attempts:
     # we bailed out because of too many attempts
     print "Too many attempts at raising the temperature."
else:
     # we got here because it's hot
     print "it's hot here, man."


########NEW FILE########
__FILENAME__ = temp2
###  PYTHON BOOT CAMP EXAMPLE; 
###  created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)
###  all rights reserved 2012 (c)
###  https://github.com/profjsb/python-bootcamp

# set some initial variables. Set the initial temperature low
faren = -1000

# we dont want this going on forever, let's make sure we cannot have too many attempts
max_attempts = 6
attempt = 0

while faren < 100 and (attempt < max_attempts):
     # let's get the user to tell us what temperature it is
     newfaren = float(raw_input("Enter the temperature (in Fahrenheit): "))
     if newfaren > faren:
             print "It's getting hotter"
     elif newfaren < faren:
             print "It's getting cooler"
     else:
         # nothing has changed, just continue in the loop
         continue

     faren = newfaren
     attempt += 1    # bump up the attempt number

if attempt >= max_attempts:
     # we bailed out because of too many attempts
     print "Too many attempts at raising the temperature."
else:
     # we got here because it's hot
     print "it's hot here, man."

########NEW FILE########
__FILENAME__ = airline
airports = {"DCA": "Washington, D.C.", "IAD": "Dulles", "LHR": "London-Heathrow", \
            "SVO": "Moscow", "CDA": "Chicago-Midway", "SBA": "Santa Barbara", "LAX": "Los Angeles",\
            "JFK": "New York City", "MIA": "Miami", "AUM": "Austin, Minnesota"}
            
# airline, number, heading to, gate, time (decimal hours) 
flights = [("Southwest",145,"DCA",1,6.00),("United",31,"IAD",1,7.1),("United",302,"LHR",5,6.5),\
           ("Aeroflot",34,"SVO",5,9.00),("Southwest",146,"CDA",1,9.60), ("United",46,"LAX",5,6.5),\
           ("Southwest",23,"SBA",6,12.5),("United",2,"LAX",10,12.5),("Southwest",59,"LAX",11,14.5),\
           ("American", 1,"JFK",12,11.3),("USAirways", 8,"MIA",20,13.1),("United",2032,"MIA",21,15.1),\
           ("SpamAir",1,"AUM",42,14.4)]

########NEW FILE########
__FILENAME__ = getinfo
"""
this is a demo of some methods used in the os and sys.
usage:
  import getinfo
  getinfo.getinfo()
  getinfo.getinfo("/tmp/")
  
 PYTHON BOOT CAMP EXAMPLE; 
   created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)

"""
import os
import sys

def getinfo(path="."):
    """
Purpose: make simple use of os and sys modules
Input: path (default = "."), the directory you want to list
    """
    print "You are using Python version ",
    print sys.version
    print "-" * 40
    print "Files in the directory " + str(os.path.abspath(path)) + ":"
    for f in os.listdir(path): print f

########NEW FILE########
__FILENAME__ = modfun
#!/usr/bin/env python
"""
Some functions written to demonstrate a bunch of concepts like modules, import
and command-line programming


 PYTHON BOOT CAMP EXAMPLE; 
    created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)

"""

import os
import sys

def getinfo(path=".",show_version=True):
    """
Purpose: make simple us of os and sys modules

Input: path (default = "."), the directory you want to list
    """
    if show_version:
        print "-" * 40
        print "You are using Python version ",
        print sys.version
        print "-" * 40

    print "Files in the directory " + str(os.path.abspath(path)) + ":"
    for f in os.listdir(path): print "  " + f
    print "*" * 40
    
def numop1(x,y,multiplier=1.0,greetings="Thank you for your inquiry."):
    """ 
Purpose: does a simple operation on two numbers. 

Input: We expect x,y are numbers 
       multiplier is also a number (a float is preferred) and is optional.  
       It defaults to 1.0. You can also specify a small greeting as a string.

Output: return x + y times the multiplier
    """
    if greetings is not None:
          print greetings
    return (x + y)*multiplier


if __name__ == "__main__":
    """
Executed only if run from the command line.
call with
  modfun.py <dirname> <dirname> ...
If no dirname is given then list the files in the current path
    """
    if len(sys.argv) == 1:
        getinfo(".",show_version=True)
    else:
        for i,dir in enumerate(sys.argv[1:]):
            if os.path.isdir(dir):
                # if we have a directory then operate on it
                # only show the version info if it's the first directory
                getinfo(dir,show_version=(i==0))
            else:
                print "Directory: " + str(dir) + " does not exist."
                print "*" * 40
                

########NEW FILE########
__FILENAME__ = numfun1
"""
small demo of modules

  PYTHON BOOT CAMP EXAMPLE; 
    created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)
"""

def numop1(x,y,multiplier=1.0,greetings="Thank you for your inquiry."):
    """ 
Purpose: does a simple operation on two numbers. 

Input: We expect x,y are numbers 
       multiplier is also a number (a float is preferred) and is optional.  
       It defaults to 1.0. You can also specify a small greeting as a string.

Output: return x + y times the multiplier
    """
    if greetings is not None:
          print greetings
    return (x + y)*multiplier



########NEW FILE########
__FILENAME__ = numfun2
"""
small demo of modules

  PYTHON BOOT CAMP EXAMPLE; 
    created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)

"""
print "numfun2 in the house"
x    = 2
s    = "spamm"

def numop1(x,y,multiplier=1.0,greetings="Thank you for your inquiry."):
    """ 
Purpose: does a simple operation on two numbers. 

Input: We expect x,y are numbers 
       multiplier is also a number (a float is preferred) and is optional.  
       It defaults to 1.0. You can also specify a small greeting as a string.

Output: return x + y times the multiplier
    """
    if greetings is not None:
          print greetings
    return (x + y)*multiplier



########NEW FILE########
__FILENAME__ = numop1
"""
Some functions written to demonstrate a bunch of concepts like modules, import
and command-line programming

 PYTHON BOOT CAMP EXAMPLE; 
    created by Josh Bloom at UC Berkeley, 2012 (ucbpythonclass+bootcamp@gmail.com)

"""

def numop1(x,y,multiplier=1.0,greetings="Thank you for your inquiry."):
    """ 
Purpose: does a simple operation on two numbers. 

Input: We expect x,y are numbers 
       multiplier is also a number (a float is preferred) and is optional.  
       It defaults to 1.0. You can also specify a small greeting as a string.

Output: return x + y times the multiplier
    """
    if greetings is not None:
          print greetings
    return (x + y)*multiplier



########NEW FILE########
__FILENAME__ = checkemail
"""
  PYTHON BOOT CAMP EXAMPLE; 
    created by Josh Bloom at UC Berkeley, 2010,2012 (ucbpythonclass+bootcamp@gmail.com)
"""
import string

## let's only allow .com, .edu, and .org email domains
allowed_domains = ["com","edu","org"]

## let's nix all the possible bad characters
disallowed = string.punctuation.replace(".","")

while True:
    res = raw_input("Enter your full email address: ")
    res = res.strip()   # get rid of extra spaces from a key-happy user
    if res.count("@") != 1:
        print "missing @ sign or too many @ signs"
        continue
    username,domain = res.split("@")

    ## let's look at the domain
    if domain.find(".") == -1:
        print "invalid domain name"
        continue
    if domain.split(".")[-1] not in allowed_domains:
        ## does this end as it should?
        print "invalid top-level domain...must be in " + ",".join(allowed_domains)
        continue
    goodtogo = True
    for s in domain:
        if s in disallowed:
            print "invalid character " + s
            ## cannot use continue here because then we only continue the for loop, not the while loop 
            goodtogo = False

        
    ## if we're here then we're good on domain. Make sure that 
    for s in username:
        if s in disallowed:
            print "invalid character " + s
            goodtogo = False

    if goodtogo:
        print "valid email. Thank you."
        break

########NEW FILE########
__FILENAME__ = tabbify_my_csv
"""
small copy program that turns a csv file into a tabbed file

  PYTHON BOOT CAMP EXAMPLE; 
    created by Josh Bloom at UC Berkeley, 2010,2012 (ucbpythonclass+bootcamp@gmail.com)

"""

import os

def tabbify(infilename,outfilename,ignore_comments=True,comment_chars="#;/"):
    """
INPUT: infilename
OUTPUT: creates a file called outfilename
    """
    if not os.path.exists(infilename):
        return  # do nothing if the file isn't there
    f = open(infilename,"r")
    o = open(outfilename,"w")
    inlines = f.readlines() ; f.close()
    outlines = []
    for l in inlines:
        if ignore_comments and (l[0] in comment_chars):
            outlines.append(l)
        else:
            outlines.append(l.replace(",","\t"))
    o.writelines(outlines) ; o.close()


########NEW FILE########
__FILENAME__ = OOP_I
# Code for Object-Oriented Programming with Python - Lesson 1
# SBC - 01/12/12

###
# Slide 9 - Bear: Our first Python class
class Bear:
    print "The bear class is now defined"

a = Bear
a
# Equates a to the class Bear.  Not very useful
a = Bear()
# Creates a new *instance* of the class Bear

###
# Slide 10 - Attributes: Access, Creation, Deletion
a.name
# name attributed has not been defined yet
a.name = "Oski"
a.color = "Brown"
# new attributes are accessed with the "." operator
del(a.name)
# attributes can be deleted as well
a.name
# Throws AttributeError Exception

###
# Slide 11 - Methods: Access, Creation, and (not) Deletion
class Bear:
    print "The bear class is now defined."
    def say_hello(self):
        print "Hello, world!  I am a bear."

a = Bear()
# create a new instance of the bear class
a.say_hello
# This provides access to the method itself
a.say_hello()
# This actually executes the method

###
# Slide 12 - The __init__ method
class Bear:
    def __init__(self, name):
        self.name = name
    def say_hello(self):
        print "Hello, world!  I am a bear."
        print "My name is %s." % self.name

a = Bear()
# Now you need to specify one argument to create the Bear class
a = Bear("Yogi")
a.name
a.say_hello()
# Prints desired text

###
# Slide 13 - Scope: self and "class" variables
class Bear:
    population = 0
    def __init__(self, name):
        self.name = name
        Bear.population += 1
    def say_hello(self):
        print "Hello, world!  I am a bear."
        print "My name is %s." % self.name
        print "I am number %i." % Bear.population

a = Bear("Yogi")
# Create a new instance of the Bear class.  Needs 1 argument
a.say_hello()
# Prints name and 1st bear
b = Bear("Winnie")
b.say_hello()
# Prints name and 2nd bear
c = Bear("Fozzie")
Bear.say_hello(c)
# Need "self" argument when calling directly from class

###
# Slide 15 - A Zookeeper's Travails I
class Bear:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight

a = Bear("Yogi", 80)
b = Bear("Winnie", 100)
c = Bear("Fozzie", 115)
# Create three new Bear instances
my_bears = [a, b, c]
# Combine them into a list
total_weight = 0
for z in my_bears:
    total_weight += z.weight

# Loop over the list and add to the total weight
total_weight < 300
# The zookeeper only needs to make one trip.

###
# Slide 17 - A Zookeeper's Travails II
class Bear:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight
    def eat(self, amount):
        self.weight += amount
    def hibernate(self):
        self.weight /= 1.20

a = Bear("Yogi", 80)
b = Bear("Winnie", 100)
c = Bear("Fozzie", 115)
my_bears=[a, b, c]
a.weight
a.eat(20)
a.weight
# After eating, Yogi gains 20 kg
b.eat(10)
# Winnie eats
c.hibernate()
# Fozzie hibernates`
total_weight = 0
for z in my_bears:
    total_weight += z.weight

total_weight < 300
# Now the keeper needs two trips.

###
# Slide 19 - A Zookeeper's Travails III
class Bear:
    def __init__(self, name, fav_food, friends=[]):
        self.name = name
        self.fav_food = fav_food
        self.friends = friends
    def same_food(self):
        for friend in self.friends:
            if (friend.fav_food == self.fav_food):
                print "%s and %s both like %s" % \
                 (self.name, friend.name, self.fav_food)

a = Bear("Yogi", "Picnic baskets")
b = Bear("Winnie", "Honey")
c = Bear("Fozzie", "Frog legs")

###
# Slide 20 - A Zookeeper's Travails III
c.friends	# empty list
c.fav_food	# 'Frog legs'
c.same_food()	# Returns None since no friends
c.friends = [a, b]	# Now Fozzie has two friends
c.same_food()	# But still no overlap in food tastes
c.fav_food = "Honey"	# Fozzie now likes honey
c.same_food()	# And shares same food with Winnie





########NEW FILE########
__FILENAME__ = bear
import datetime
class Bear:
    logfile_name = "bear.log"
    bear_num     = 0
    def __init__(self,name):
        self.name = name
        print " made a bear called %s" % (name)
        self.logf  = open(Bear.logfile_name,"a")
        Bear.bear_num += 1
        self.my_num = Bear.bear_num
        self.logf.write("[%s] created bear #%i named %s\n" % \
                        (datetime.datetime.now(),Bear.bear_num,self.name))
        self.logf.flush()
    
    def growl(self,nbeep=5):
        print "\a"*nbeep

    def __del__(self):
        print "Bang! %s is no longer." % self.name
        self.logf.write("[%s] deleted bear #%i named %s\n" % \
                        (datetime.datetime.now(),self.my_num,self.name))
        self.logf.flush()
        # decrement the number of bears in the population
        Bear.bear_num -= 1
        # dont really need to close because Python will do the garbage collection
        #  for us. but it cannot hurt to be graceful here.
        self.logf.close()

    def __str__(self):
        return " name = %s bear number = %i (population %i)" % \
              (self.name, self.my_num,Bear.bear_num)
        
"""
print Bear.__doc__
print Bear.__name__
print Bear.__module__
print Bear.__bases__
print Bear.__dict__
"""

########NEW FILE########
__FILENAME__ = bear1
class Bear:
    """
    class to show off addition (and multiplication)
    """
    bear_num = 0
    def __init__(self,name):
        self.name = name
        print " made a bear called %s" % (name)
        Bear.bear_num += 1
        self.my_num = Bear.bear_num

    def __add__(self,other):
        ## spawn a little tike
        cub = Bear("progeny_of_%s_and_%s" % (self.name,other.name))
        cub.parents = (self,other)
        return cub

    def __mul__(self,other):
        ## multiply (as in "go forth and multiply") is really the same as adding
        self.__add__(other)
        
########NEW FILE########
__FILENAME__ = bear2
import datetime
class Bear:
    logfile_name = "bear.log"
    bear_num     = 0
    def __init__(self,name):
        self.name = name
        print " made a bear called %s" % (name)
        self.logf  = open(Bear.logfile_name,"a")
        Bear.bear_num += 1
        self.created = datetime.datetime.now()
        self.my_num = Bear.bear_num
        self.logf.write("[%s] created bear #%i named %s\n" % \
                        (datetime.datetime.now(),Bear.bear_num,self.name))
        self.logf.flush()
    
    def growl(self,nbeep=5):
        print "\a"*nbeep

    def __del__(self):
        print "Bang! %s is no longer." % self.name
        self.logf.write("[%s] deleted bear #%i named %s\n" % \
                        (datetime.datetime.now(),self.my_num,self.name))
        self.logf.flush()
        # decrement the number of bears in the population
        Bear.bear_num -= 1
        # dont really need to close because Python will do the garbage collection
        #  for us. but it cannot hurt to be graceful here.
        self.logf.close()

    def __str__(self):
        age = datetime.datetime.now() - self.created
        return " name = %s bear (age %s) number = %i (population %i)" % \
                (self.name, age, self.my_num,Bear.bear_num)
        
"""
print Bear.__doc__
print Bear.__name__
print Bear.__module__
print Bear.__bases__
print Bear.__dict__
"""

########NEW FILE########
__FILENAME__ = catcherr
import sys
try:
    f = open('myfile.txt')
    s = f.readline()
    i = int(s.strip())
except IOError as (errno, strerror):
    print "I/O error(%i): %s" % (errno, strerror)
except ValueError:
    print "Could not convert data to an integer."
except:
    print "Unexpected error:", sys.exc_info()[0]
    raise

########NEW FILE########
__FILENAME__ = downgradenb
"""Simple utility script for semi-gracefully downgrading v3 notebooks to v2"""

import io
import os
import sys

from IPython.nbformat import current

def heading_to_md(cell):
    """turn heading cell into corresponding markdown"""
    cell.cell_type = "markdown"
    level = cell.pop('level', 1)
    cell.source = '#'*level + ' ' + cell.source

def raw_to_md(cell):
    """let raw passthrough as markdown"""
    cell.cell_type = "markdown"

def downgrade(nb):
    """downgrade a v3 notebook to v2"""
    if nb.nbformat != 3:
        return nb
    nb.nbformat = 2
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'heading':
                heading_to_md(cell)
            elif cell.cell_type == 'raw':
                raw_to_md(cell)
    return nb

def downgrade_ipynb(fname):
    base, ext = os.path.splitext(fname)
    newname = base+'.v2'+ext
    print "downgrading %s -> %s" % (fname, newname)
    with io.open(fname, 'r', encoding='utf8') as f:
        nb = current.read(f, 'json')
    nb = downgrade(nb)
    with open(newname, 'w') as f:
        current.write(nb, f, 'json')

if __name__ == '__main__':
    map(downgrade_ipynb, sys.argv[1:])

########NEW FILE########
__FILENAME__ = subclass
class Plant:
    num_known = 0
    def __init__(self,common_name,latin_name=None):
        self.latin_name = latin_name
        self.common_name = common_name
        Plant.num_known += 1
    
    def __str__(self):
        return "I am a plant (%s)!" % self.common_name

class Flower(Plant):
    has_pedals = True

    def __init__(self,common_name,npedals=5,pedal_color="red",latin_name=None):
        ## call the __init__ of the 
        Plant.__init__(self,common_name,latin_name=latin_name)
        self.npedals=5
        self.pedal_color = pedal_color
        
    def __str__(self):
        return "I am a flower (%s)!" % self.common_name
            


class A:
    def __init__(self):
        print "A"
class B(A):
    def __init__(self):
        A.__init__(self)
        print "B"
########NEW FILE########
__FILENAME__ = animals_0
""" 
Test Driven Development using animals and Nose testing.
"""

def test_moves():
    assert Animal('owl').move() == 'fly'
    assert Animal('cat').move() == 'walk'
    assert Animal('fish').move() == 'swim'

def test_speaks():
    assert Animal('owl').speak() == 'hoot'
    assert Animal('cat').speak() == 'meow'
    assert Animal('fish').speak() == ''

########NEW FILE########
__FILENAME__ = animals_1
""" 
Test Driven Development using animals and Nose testing.
"""
class Animal:
    """ This is an animal.
    """
    animal_defs = {'owl':{'move':'fly',
                          'speak':'hoot'},
                   'cat':{'move':'walk',
                          'speak':'meow'},
                   'fish':{'move':'swim',
                          'speak':''}}
    def __init__(self, name):
        self.name = name

    def move(self):
        return self.animal_defs[self.name]['move']
        
    def speak(self):
        return self.animal_defs[self.name]['speak']


def test_moves():
    assert Animal('owl').move() == 'fly'
    assert Animal('cat').move() == 'walk'
    assert Animal('fish').move() == 'swim'

def test_speaks():
    assert Animal('owl').speak() == 'hoot'
    assert Animal('cat').speak() == 'meow'
    assert Animal('fish').speak() == ''

########NEW FILE########
__FILENAME__ = animals_2
""" 
Test Driven Development using animals and Nose testing.
"""
from random import random

class Animal:
    """ This is an animal
    """
    animal_defs = {'owl':{'move':'fly',
                          'speak':'hoot'},
                   'cat':{'move':'walk',
                          'speak':'meow'},
                   'fish':{'move':'swim',
                          'speak':''}}
    def __init__(self, name):
        self.name = name

    def move(self):
        return self.animal_defs[self.name]['move']
        
    def speak(self):
        return self.animal_defs[self.name]['speak']


def test_moves():
    assert Animal('owl').move() == 'fly'
    assert Animal('cat').move() == 'walk'
    assert Animal('fish').move() == 'swim'

def test_speaks():
    assert Animal('owl').speak() == 'hoot'
    assert Animal('cat').speak() == 'meow'
    assert Animal('fish').speak() == ''

def test_dothings_list():
    """ Test that the animal does the same number of things as the number of hour-times given.
    """
    times = []
    for i in xrange(5):
        times.append(random() * 24.)
    for a in ['owl', 'cat', 'fish']:
        assert len(Animal(a).dothings(times)) ==\
                                         len(times)

def test_dothings_with_beyond_times():
    for a in ['owl', 'cat', 'fish']:
        assert Animal(a).dothings([-1]) == ['']
        assert Animal(a).dothings([25]) == ['']

def test_nocturnal_sleep():
    """ Test that an owl is awake at night.
    """
    night_hours = [0.1, 3.3, 23.9]
    noct_behaves = Animal('owl').dothings(night_hours)
    for behave in noct_behaves:
        assert behave != 'sleep'

########NEW FILE########
__FILENAME__ = animals_3
""" 
Test Driven Development using animals and Nose testing.
"""
from random import random

class Animal:
    """ This is an animal
    """
    animal_defs = {'owl':{'move':'fly',
                          'speak':'hoot'},
                   'cat':{'move':'walk',
                          'speak':'meow'},
                   'fish':{'move':'swim',
                          'speak':''}}
    def __init__(self, name):
        self.name = name

    def move(self):
        return self.animal_defs[self.name]['move']
        
    def speak(self):
        return self.animal_defs[self.name]['speak']

    def dothings(self, times):
        """ A method which takes a list
              of times (hours between 0 and 24) and
              returns a list of what the animal is 
              (randomly) doing.
         - Beyond hours 0 to 24: the animal does: ""
        """
        out_behaves = []
        for t in times:
            if (t < 0) or (t > 24):
                out_behaves.append('')
            elif ((self.name == 'owl') and
                (t > 6.0) and (t < 20.00)):
                out_behaves.append('sleep')
            else:
                out_behaves.append( \
                 self.animal_defs[self.name]['move'])
        return out_behaves


def test_moves():
    assert Animal('owl').move() == 'fly'
    assert Animal('cat').move() == 'walk'
    assert Animal('fish').move() == 'swim'

def test_speaks():
    assert Animal('owl').speak() == 'hoot'
    assert Animal('cat').speak() == 'meow'
    assert Animal('fish').speak() == ''

def test_dothings_list():
    """ Test that the animal does the same number of things as the number of hour-times given.
    """
    times = []
    for i in xrange(5):
        times.append(random() * 24.)
    for a in ['owl', 'cat', 'fish']:
        assert len(Animal(a).dothings(times)) ==\
                                         len(times)

def test_dothings_with_beyond_times():
    for a in ['owl', 'cat', 'fish']:
        assert Animal(a).dothings([-1]) == ['']
        assert Animal(a).dothings([25]) == ['']

def test_nocturnal_sleep():
    """ Test that an owl is awake at night.
    """
    night_hours = [0.1, 3.3, 23.9]
    noct_behaves = Animal('owl').dothings(night_hours)
    for behave in noct_behaves:
        assert behave != 'sleep'


if __name__ == '__main__':
    ### The above line is Python syntax which defines a 
    ### section that is only used when animals_?.py is either:
    #   - executed from the shell as an executable script
    #   - executed from the shell using:  python animals_?.py
    #   - executed using another program, eg: python pdb.py animals_?.py
    #
    # This section is not used when nose_example1 is imported as a module.


    c = Animal('cat')
    o = Animal('owl')
    f = Animal('fish')

    times = []
    for i in xrange(10):
        times.append(random() * 24.)
    times.sort()
    
    c_do = c.dothings(times)
    o_do = o.dothings(times)
    f_do = f.dothings(times)

    for i in xrange(len(times)):
        print "time=%3.3f cat=%s owl=%s fish=%s" % ( \
                   times[i], c_do[i], o_do[i], f_do[i])

########NEW FILE########
__FILENAME__ = doctests_example
def multiply(a, b):
  """
  'multiply' multiplies two numbers and returns the result.

  >>> multiply(0.5, 1.5)
  0.75
  >>> multiply(-1, 1)
  -1
  """
  return a*b + 1

########NEW FILE########
__FILENAME__ = nose_example1
""" Nose Example 1
"""

class Transmogrifier:
    """ An important class
    """
    def transmogrify(self, person):
        """ Transmogrify someone
        """
        transmog = {'calvin':'tiger',
                     'hobbes':'chicken'}
        new_person = transmog[person]
        return new_person


def test_transmogrify():
    TM = Transmogrifier()
    for p in ['Calvin', 'Hobbes']:
        assert TM.transmogrify(p) != None


def main():
    TM = Transmogrifier()
    for p in ['calvin', 'Hobbes']:
        print p, '->  ZAP!  ->', TM.transmogrify(p)


if __name__ == '__main__':
    ### The above line is Python syntax which defines a 
    ### section that is only used when nose_example1.py is either:
    #   - executed from the shell as an executable script
    #   - executed from the shell using:  python nose_example1.py
    #   - executed using another program, eg: python pdb.py nose_example1.py
    #
    # This section is not used when nose_example1 is imported as a module.

    main()


########NEW FILE########
__FILENAME__ = loggin1
import logging
LOG_FILENAME = 'loggin1.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.WARNING)

def make_logs():
    logging.debug('This is a debug message')
    logging.warning('This is a warning message')
    logging.error('This is an error message')

########NEW FILE########
__FILENAME__ = loggin2
import logging
logger = logging.getLogger("some_identifier")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.stream = open("loggin2.log", 'w')
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

def make_logs():
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

########NEW FILE########
__FILENAME__ = my_assertions
def do_string_stuff(val):
    assert type(val) == type("")
    print ">" + val + "< length:", len(val)
    
def do_string_stuff_better(val):
    val_type = type(val)
    assert val_type == type(""), "Given a %s" % (str(val_type))
    print ">" + val + "< length:", len(val)
    

########NEW FILE########
__FILENAME__ = test_simple
"A simple set of tests"

def testTrue():
    "Thruth-iness test"
    assert True == 1

def testFalse():
    "Fact-brication test"
    assert False == 0

########NEW FILE########
__FILENAME__ = tryexcept0
def divide_it(x, y):
    try:
        out = x / y
    except:
        print '   Divide by zero!'
        out = None
    return out

########NEW FILE########
__FILENAME__ = tryexcept1
import traceback
def example1():
    try:
        raise SyntaxError, "example"
    except:
        traceback.print_exc()
    print "...still running..."

def example2():
    """ Here we have access to the (filename, line number, function name, text)
    of each element in the Traceback stack.
    """
    try:
        raise SyntaxError
    except:
        stack_list = traceback.extract_stack()
        for (filename, linenum, functionname, text) in stack_list:
            print "%s:%d %s()" % (filename, linenum, functionname)
    print "...still running..."

########NEW FILE########
__FILENAME__ = appetite
#! /usr/bin/env python
# this file was originall written by Brad Cenko for 2012 UCB Python Bootcamp
# modified and extended by Paul Ivanov for the 2013 UCB Python Bootcamp

import sqlite3, os, smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import NothingToSeeHere # Email password stored in this (private) file
from NothingToSeeHere import username as email_addr

# Global variables
piDB = "piDB.sql"
# Need to change this to a path you can write to

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

###########################################################################

def create_friends_table(filename=piDB):

    """Creates sqlite database to store basic information on my buddies"""

    conn = sqlite3.connect(filename)
    c = conn.cursor()

    c.execute('''CREATE TABLE CYCLISTS (f_name text, l_name text,
               email text, status text)''')

    ins_tpl= 'INSERT INTO CYCLISTS VALUES ("%s", "%s", "%s", "%s")'

    l = []
    l += [ins_tpl % ( "Paul", "Ivanov", email_addr, 'committed')]
    l += [ins_tpl % ( "Dan", "Coates", email_addr, 'committed')]
    l += [ins_tpl % ( "James", "Gao", email_addr, 'casual')]
    l += [ins_tpl % ( "Sara", "Emery", email_addr, 'committed')]
    l += [ins_tpl % ( "Jonathan", "Giffard", email_addr, 'weekender')]
    l += [ins_tpl % ( "Janet", "Young", email_addr, 'weekender')]

    for s in l:
        print s
        c.execute(s)

    conn.commit()
    c.close()

    return

############################################################################

def retrieve_random_cyclist(filename=piDB, kind="committed"):

    """Returns the name and email address of a random cyclist"""

    conn = sqlite3.connect(filename)
    c = conn.cursor()

    c.execute("SELECT f_name, l_name, email FROM CYCLISTS WHERE status" + \
              " = '%s' ORDER BY RANDOM() LIMIT 1" % kind)
    row = c.fetchall()
    
    conn.commit()
    c.close()
    if len(row)== 0:
        raise ValueError("There are no people who are '%s'" % kind ) 

    return [row[0][0], row[0][1], row[0][2]]

###########################################################################

###############################################################################

def email_cyclist(address, f_name, l_name, myemail=NothingToSeeHere.username):

    """Generate and send an email to address with a request to observe
    the given supernova."""
    
    # Create the message
    msg = MIMEMultipart()
    msg["From"] = myemail
    msg["To"] = address
    msg["Subject"] = "Let's go for a ride, %s" % f_name

    # Write the body, making sure all variables are defined.
    msgstr = r"""Hey %s,

    Wanna go for a bike ride later on today?

    best,
    pi
    -- 
                       _
                      / \
                    A*   \^   -
                 ,./   _.`\\ / \
                / ,--.S    \/   \
               /  `"~,_     \    \
         __o           ?
       _ \<,_         /:\
    --(_)/-(_)----.../ | \
    --------------.......J
    Paul Ivanov
    http://pirsquared.org
    """  % f_name
    msg.attach(MIMEText(msgstr))

    # Configure the outgoing mail server
    log.info("sending out email") 
    mailServer = smtplib.SMTP("smtp.gmail.com", 587)
    mailServer.starttls()
    mailServer.login(myemail, NothingToSeeHere.password)

    # Send the message
    mailServer.sendmail(myemail, address, msg.as_string())
    mailServer.close()

    
    return

###############################################################################
    
def go_cycling(filename=piDB, myemail=NothingToSeeHere.username):
    """Script to go cycling with one of my cycling buddies.
    Grabs
    and emails that student to request follow-up observations."""

    # See if the department database exists.  If not, create it.
    if not os.path.exists(filename):
        create_friends_table(filename=filename)

    # Select a random graduate student to do our bidding
    [f_name, l_name, address] = retrieve_random_cyclist(filename=filename)

    # Email the student
    email_cyclist(address, f_name, l_name, myemail=myemail)

    print "I emailed %s %s at %s about going cycling." % (f_name, l_name,
                                                          address)

###############################################################################

########NEW FILE########
__FILENAME__ = get_tweets
# This example is taken verbatim from Chapter 1 of 
# Mining the Social Web by Matthew A. Russell (O'Reilly Publishers) 

import json

from twitter_init import twitter_api

def search_tweets(q='#pyboot'):
    """Get twitter status based on a search string `q`"""

    count = 100

    # See https://dev.twitter.com/docs/api/1.1/get/search/tweets

    search_results = twitter_api.search.tweets(q=q, count=count)

    statuses = search_results['statuses']


    # Iterate through 5 more batches of results by following the cursor

    for _ in range(5):
        print "Length of statuses", len(statuses)
        try:
            next_results = search_results['search_metadata']['next_results']
        except KeyError, e: # No more results when next_results doesn't exist
            break
            
        # Create a dictionary from next_results, which has the following form:
        # ?max_id=313519052523986943&q=NCAA&include_entities=1
        kwargs = dict([ kv.split('=') for kv in next_results[1:].split("&") ])
        
        search_results = twitter_api.search.tweets(**kwargs)
        statuses += search_results['statuses']
    return statuses

    # Show one sample search result by slicing the list...
#print json.dumps(statuses[0], indent=1)



########NEW FILE########
__FILENAME__ = hello1
from flask import Flask
app = Flask(__name__)

run_on_public_interface = True

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    if run_on_public_interface:
        app.run(host='0.0.0.0')
    else:
        app.run()

########NEW FILE########
__FILENAME__ = hello2
from flask import Flask
app = Flask(__name__)

run_on_public_interface = True

@app.route("/")
def hello():
    return "Hello World!"

# read more about using variables here:
# http://flask.pocoo.org/docs/quickstart/#variable-rules
@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'User %s' % username

@app.route('/tweet/<int:tweet_id>')
def show_tweet(tweet_id):
    # show the tweet with the given id, the id is an integer
    return 'tweet_id %d' % tweet_id

if __name__ == "__main__":
    if run_on_public_interface:
        app.run(host='0.0.0.0')
    else:
        app.run()

########NEW FILE########
__FILENAME__ = hello3
from flask import Flask, url_for
app = Flask(__name__)

run_on_public_interface = True

@app.route("/")
def hello():
    return "Hello World!"

# read more about using variables here:
# http://flask.pocoo.org/docs/quickstart/#variable-rules
@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'User %s' % username

@app.route('/tweet/<int:tweet_id>')
def show_tweet(tweet_id):
    # show the tweet with the given id, the id is an integer
    username = 'ivanov'
    user_url = url_for('show_user_profile', username=username)
    link = '<a href="{url}">{text}</a>'
    s = link.format(url=user_url, text=username)
    return s + 'tweet_id %d' % tweet_id

if __name__ == "__main__":
    if run_on_public_interface:
        app.run(debug=True,host='0.0.0.0')
    else:
        app.run()

########NEW FILE########
__FILENAME__ = hello4
# We're going to try to add some style to our website
# but if we continue to deal with just strings, it's going to get messy

from flask import Flask, url_for
app = Flask(__name__)


import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

import os
import sys
import IPython.html as ipynb

if not os.path.exists('static') :
    if sys.platform == 'win32':
        import shutil
        shutil.copytree(ipynb.DEFAULT_STATIC_FILES_PATH, 'static')
    else:
        # the next line won't work on windows
        os.symlink(ipynb.DEFAULT_STATIC_FILES_PATH, 'static')


header = """
<head>
    <link rel="stylesheet" href="/static/components/jquery-ui/themes/smoothness/jquery-ui.min.css" type="text/css" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link rel="stylesheet" href="/static/style/style.min.css" type="text/css"/>
</head>
"""
run_on_public_interface = True

@app.route("/")
def hello():
    return "Hello World!"

# read more about using variables here:
# http://flask.pocoo.org/docs/quickstart/#variable-rules
@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'User %s' % username

@app.route('/tweet/<int:tweet_id>')
def show_tweet(tweet_id):
    # show the tweet with the given id, the id is an integer
    username = 'ivanov'
    user_url = url_for('show_user_profile', username=username)
    link = '<div class="prompt"><a href="{url}">{text}</a></div>'
    s = ''
    s += "<div class='container' id='notebook-container'>" 
    s += "<div class='cell border-box-sizing selected' >"
    s += link.format(url=user_url, text=username)
    s += "<div class='input_area' style='padding:20px'> <p>let's see how this looks</p></div>" 
    s += "</div>" 
    s += "</div>" 
    s += "</div>" 
    return header + s + 'tweet_id %d' % tweet_id

if __name__ == "__main__":
    if run_on_public_interface:
        app.run(debug=True,host='0.0.0.0')
    else:
        app.run()

########NEW FILE########
__FILENAME__ = hello5
# We're going to try to add some style to our website
# but if we continue to deal with just strings, it's going to get messy

from flask import Flask, url_for, render_template
app = Flask(__name__)


import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

import os
import sys
import IPython.html as ipynb

if not os.path.exists('static') :
    if sys.platform == 'win32':
        import shutil
        shutil.copytree(ipynb.DEFAULT_STATIC_FILES_PATH, 'static')
    else:
        # the next line won't work on windows
        os.symlink(ipynb.DEFAULT_STATIC_FILES_PATH, 'static')


run_on_public_interface = True

@app.route("/")
def hello():
    return "Hello World!"

# read more about using variables here:
# http://flask.pocoo.org/docs/quickstart/#variable-rules
@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    # Let's just hardcode some tweets for now
    tweets = ["Something awesome happened at #pyboot", 
            "The first rule of #pyboot is you must tell everyone about #pyboot",
            "The second rule of #pyboot is: you must endure memes and pop culture references" 
            ]
    return render_template('user_dummy.html', username=username, tweets=tweets)

@app.route('/tweet/<int:tweet_id>')
def show_tweet(tweet_id):
    # show the tweet with the given id, the id is an integer
    username = 'ivanov'
    user_url = url_for('show_user_profile', username=username)
    # We've hidden away the string logic in the file templates/tweet.html
    tweet_text = 'this is some test test #' + str(tweet_id) 
    return render_template('tweet.html', user_url=user_url, username=username,
                           tweet=tweet_text)

if __name__ == "__main__":
    if run_on_public_interface:
        app.run(debug=True,host='0.0.0.0')
    else:
        app.run()

########NEW FILE########
__FILENAME__ = hello6
# We're going to try to add some style to our website
# but if we continue to deal with just strings, it's going to get messy

from flask import Flask, url_for, render_template
app = Flask(__name__)


import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

import os
import sys

import get_tweets

import IPython.html as ipynb

if not os.path.exists('static') :
    if sys.platform == 'win32':
        import shutil
        shutil.copytree(ipynb.DEFAULT_STATIC_FILES_PATH, 'static')
    else:
        # the next line won't work on windows
        os.symlink(ipynb.DEFAULT_STATIC_FILES_PATH, 'static')


run_on_public_interface = True

@app.route("/")
def hello():
    return "Hello World!"

# read more about using variables here:
# http://flask.pocoo.org/docs/quickstart/#variable-rules
@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    # Let's just hardcode some tweets for now
    tweets = ["Something awesome happened at #pyboot", 
            "The first rule of #pyboot is you must tell everyone about #pyboot",
            "The second rule of #pyboot is: you must endure memes and pop culture references" 
            ]
    return render_template('user_dummy.html', username=username, tweets=tweets)

@app.route('/tweet/<int:tweet_id>')
def show_tweet(tweet_id):
    # show the tweet with the given id, the id is an integer
    username = 'ivanov'
    user_url = url_for('show_user_profile', username=username)
    # We've hidden away the string logic in the file templates/tweet.html
    tweet_text = 'this is some test test #' + str(tweet_id) 
    return render_template('tweet.html', user_url=user_url, username=username,
                           tweet=tweet_text)
@app.route('/hashtag/<hashtag>')
def show_hashtag(hashtag):
    tweets = get_tweets.search_tweets('#'+hashtag) 
    return render_template('tweets.html', username=hashtag, tweets=tweets) 


if __name__ == "__main__":
    if run_on_public_interface:
        app.run(debug=True,host='0.0.0.0')
    else:
        app.run()

########NEW FILE########
__FILENAME__ = NothingToSeeHere
# UC Berkeley users. To use the bmail (Google) smtp server, you will need to
# create a Google Key: see this website for details
# https://kb.berkeley.edu/campus-shared-services/page.php?id=27226
username = ''
password = ''

########NEW FILE########
__FILENAME__ = simple_scraper
import urllib2
import numpy.testing as npt



url_instance= urllib2.urlopen('https://twitter.com/search?q=%23pyboot&mode=realtime')
content = url_instance.read()
url_instance.close()

def scrape_usernames_quick_and_dirty(content):
    "extract @ usernames from content of a twitter search page" 
    # you can do this more elegantly with regular expressions (import re), but
    # we don't have time to go over them, and as Jamie Zawinski once said:
    #
    #    Some people, when confronted with a problem, think: "I know, I'll use
    #    regular expressions." Now they have two problems.
    #
    # Also, we should note that there are better ways of parsing out html
    # pages in Python. Have a look at 
    at_marker = '<s>@</s><b>'
    end_marker = '</b>'
    start = 0
    usernames = []
    while True:
        # find the first index of an @ marker
        hit = content.find(at_marker, start) 
        if hit == -1:
            # we hit the end and nothing was found, break out of the while
            # loop, and return what we have
            break;
        hit += len(at_marker) 
        end = content.find(end_marker, hit) 
        if hit != end:
            # twitter has some @ signs with no usernames on that page
            username = content[hit:end]
            usernames.append(username)
        start = end
    return usernames

def scrape_usernames_beautiful(content):
    try:
        import BeautifulSoup
    except ImportError:
        raise("Sorry, you'll need to install BeautifulSoup to use this" ) 
    soup = BeautifulSoup.BeautifulSoup(content)

    all_bs = [x.findParent().findNextSibling('b') for x in soup.findAll('s', text='@')]

    usernames = []
    for b in all_bs:
        if len(b.contents) > 0:
            # twitter has some @ signs with no usernames on that page
            usernames.append(b.contents[0])

    return usernames

def test_scrapers():
    "Verify that our two ways of getting usernames yields the same results" 
    url_instance= urllib2.urlopen('https://twitter.com/search?q=%23pyboot&mode=realtime')
    content = url_instance.read()
    url_instance.close()

    names_quick = scrape_usernames_quick_and_dirty(content) 
    names_beautiful = scrape_usernames_beautiful(content) 

    npt.assert_array_equal(names_quick, names_beautiful) 


########NEW FILE########
__FILENAME__ = twitter_init
# This example is taken verbatim from Chapter 1 of 
# Mining the Social Web by Matthew A. Russell (O'Reilly Publishers) 

import twitter

# XXX: Go to http://dev.twitter.com/apps/new to create an app and get values
# for these credentials that you'll need to provide in place of these
# empty string values that are defined as placeholders.
# See https://dev.twitter.com/docs/auth/oauth for more information 
# on Twitter's OAuth implementation

CONSUMER_KEY = ''
CONSUMER_SECRET = ''
OAUTH_TOKEN = ''
OAUTH_TOKEN_SECRET = ''

auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                           CONSUMER_KEY, CONSUMER_SECRET)

twitter_api = twitter.Twitter(auth=auth)

# Nothing to see by displaying twitter_api except that it's now a
# defined variable

print twitter_api


########NEW FILE########
__FILENAME__ = hw_2_solutions
#!/usr/bin/env python
"""
A small monte carlo code to simulate the growth of coins in a cookie jar over a 1 year period
  
  The following are assumed:
  1) you make X purchases each day with petty cash, starting out with only bills in your pocket (i.e., no change).
  2) Each purchase has a random chance of costing some dollar amount plus YY cents (where YY goes from 0-99). 
     You always get change in the smallest number of coins possible. For instance, 
      if you have a purchase of $2.34, then you assume you acquire 66 cents in change
       (2 quarters, 1 dime, 1 nickel, 1 penny). 
  3) If you have enough change to cover the YY cents of the current transaction, you use it. 
     Otherwise, you accumulate more change. For example, if you have $1.02 in loose change, 
     and you have a purchase of $10.34, then you use 34 cents (or as close to it as possible) in coins
     leaving you with 68 cents.
  4) At the end of each day you dump all your coins collected for the day in a Money Jar.

  PYTHON BOOT CAMP HOMEWORK2 SOLUTION; 
    created by Josh Bloom at UC Berkeley, 2010 (ucbpythonclass+bootcamp@gmail.com)


TO RUN:

from command line:
>> python hw_2_solutions.py

from within python, from the folder in which this file resides:
>> from hw_2_solutions import CookieJar, answer_homework_questions
>> answer_homework_questions()

"""


import random, math
import numpy

__version__ = "0.1"
__author__  = "J. Bloom (jbloom@astro.berkeley.edu)"

# define a global dictionary for values of the coins
val = {"nickels": 0.05, "quarters": 0.25, "dimes": 0.10, "pennies": 0.01}

class CookieJar:
    """
    the basic workhorse
    """
    ## set the contents upon create to nothing
    deplete_quarters_frequency=7 # remove quarters every 1 week
    num_quarters_to_deplete=8    # how many quarters to remove
    
    def __init__(self,transactions_per_day=8,number_of_days_until_fill=365,deplete_quarters=False,\
                print_summary_every_week=False,print_summary_of_every_transaction=False):
        
        self.contents = {"quarters": 0, "dimes": 0, "nickels": 0, "pennies": 0}
        self.final_value    = self._content_value(self.contents)
        self.final_contents = self.contents
        self.num_transactions_performed = 0
        self.day = 0
        self.days_to_reach_500_pennies = -1
        
        self.print_summary_of_every_transaction = print_summary_of_every_transaction
        self.print_summary_every_week = print_summary_every_week
        self.transactions_per_day = transactions_per_day
        self.number_of_days_until_fill=number_of_days_until_fill
        self.deplete_quarters = deplete_quarters
        
    def fill_er_up(self):
        """
        the main engine, it runs all the transactions and accumulates some final results for this cookie jar
        """
        while self.day < self.number_of_days_until_fill:
            if self.print_summary_every_week:
                print "Day %i" % (self.day + 1)
            self.perform_a_days_worth_of_transactions()
            self.day += 1
            if self.contents["pennies"] > 500 and self.days_to_reach_500_pennies == -1:
                self.days_to_reach_500_pennies = self.day
            if self.day % self.deplete_quarters_frequency == 0 and self.deplete_quarters:
                self.contents["quarters"] = max(0,self.contents["quarters"] - self.num_quarters_to_deplete)
       
        #print "all done after %i transactions" % self.num_transactions_performed
        self.final_value    = self._content_value(self.contents)
        self.final_contents = self.contents
        self.final_order    = self._order(self.contents)
        
    def __str__(self):
        """
        print a summary of yourself
        """
        a = "Value %.2f after %i transactions performed." % (self.final_value,self.num_transactions_performed)
        a += "  days to reach 500 pennies: %i" % self.days_to_reach_500_pennies
        return a
    
    def _order(self,purse):
        """
        determine the ordering of number of coins in the purse.
        here the purse is assumed to be a dict like 
           {"nickels": 0, "quarters": 12, "dimes": 3, "pennies": 32}
        returns
           {1: "pennies", 2: "quarters", 3: "dimes", 4: "nickels"}   
        """
        tmp = [(v,k) for k,v in purse.iteritems()]
        tmp.sort(reverse=True)
        return dict([(i+1,tmp[i][1]) for i in range(len(tmp))])
        
    def _content_value(self,purse):
        """
        determine the value of coins in the purse.
        here the purse is assumed to be a dict like 
           {"nickels": 0, "quarters": 12, "dimes": 3, "pennies": 32}
        """
        rez = 0.0
        for k in purse.keys():
            rez += val[k]*purse[k]
        return rez
    
    def best_change(self,cost,contents,verbose=False):
        """
        for given transaction cost determines the best combination of coins that
         gives as close to the exact change amount needed as possible given the contents of a purse
         
         returns a tuple where the first element is False if the contents of the purse cannot
          cover the change cost, True if it can
          
          the second element is a dict showing how much of each coin type is required to make the transaction
           as close to $x.00 as possible
         
         This is just a big ugly 4x nested for loop, trying out all combinations
          
        """
        cost_in_cents = cost % 1.0
        if cost_in_cents > self._content_value(contents):
            # there's no way we have enough...our purse value is less than the cost in cents 
            return (False,{})
        
        exact = False
        best_diff = 1.00
        best = {}
        for q in range(contents["quarters"] + 1):
            for d in range(contents["dimes"] + 1):
                for n in range(contents["nickels"] + 1):
                    for p in range(contents["pennies"] + 1):
                        v = round(q*0.25 + d*0.10 + n*0.05 + p*0.01,2)
                        if verbose:
                            print "val",p,n,d,q,v,cost_in_cents,best_diff
                        if abs(v - cost_in_cents) < 0.005:
                            ## this is within the tolerance of a floating point difference
                            best_diff = 0.0 
                            best      = {"nickels": n, "dimes": d, "pennies": p, "quarters": q}
                            exact     = True
                            break
                        elif (v - cost_in_cents) > 0.0 and (v - cost_in_cents) < best_diff:
                            best_diff = (v - cost_in_cents)
                            best      = {"nickels": n, "dimes": d, "pennies": p, "quarters": q}
                            exact     = False
                    if exact:
                        break
                if exact:
                    break
            if exact:
                break
        return (True,best)
                        
    def perform_a_days_worth_of_transactions(self):
        """
        loop over all the transactions in the day keeping track of the number of coins of each type
         in the purse.
         The random cost of a transaction is set to be:
            cost = round(random.random()*50,2)
            
         
        """
        #initialize how much booty we have in our pockets
        pocket_contents = {"nickels": 0, "quarters": 0, "dimes": 0, "pennies": 0}
        n_exact = 0
        for i in xrange(self.transactions_per_day):
            
            cost = round(random.random()*50,2)   # assume a transaction cost of $0 - $50
                                                 # round to the nearest cent
            
            if self.print_summary_of_every_transaction:
                print "Day %i, transaction %i" % (self.day + 1,i + 1)
                print "  pocket_contents = %s" % repr(pocket_contents)
                print "  cost = $%.2f" % cost
            
            ## do I have exact change?
            got_enough = self.best_change(cost,pocket_contents)            
            if got_enough[0]:
                ## we have enough change and it might just enough to get us where we need to be
                ## That is the cost + this change ends in .00. So, subtract the value to the cost
                cost -= sum([got_enough[1][x]*val[x] for x in val.keys()])
                
                ## now remove all that from our purse
                for k,v in got_enough[1].iteritems():
                    pocket_contents[k] -= v
            
            # print "...new cost", cost
            if cost % 1.0 == 0.0:
                n_exact += 1
            change = self.calc_change(cost)
            for k,v in change.iteritems():
                if v != 0:
                    pocket_contents[k] += v
            self.num_transactions_performed += 1
            
        if self.print_summary_of_every_transaction:
            print "  end the end of the day: pocket_contents = %s" % repr(pocket_contents)
            print "      we had %i exact change times out of %i transactions" % (n_exact,self.transactions_per_day)
        
        ## dump what we have into the cookie jar at the end of the day
        for k in self.contents.keys():
            self.contents[k] += pocket_contents[k]
                
    def calc_change(self,transaction_amount):
        """
        for a given transaction amount, determines how many coins of each type to return
        """
        change          = 1.0 - (transaction_amount % 1.0)  # make this a number from 0.0 - 0.99
        change_in_cents = int(round(change*100.0) % 100)        ## make from 0 - 99 as type int
        
        #print "change",change,"change_in_cents",change_in_cents
        oring_change_in_cents = change_in_cents
        n_quarters = change_in_cents / 25      ## since this is int / int we'll get back an int
        change_in_cents -= n_quarters*25
        n_dimes    = change_in_cents / 10
        change_in_cents -= n_dimes*10
        n_nickels = change_in_cents / 5
        change_in_cents -= n_nickels*5
        n_pennies = change_in_cents
        if self.print_summary_of_every_transaction:
            print "  Transaction is $%.2f (coin change was %i cents)" % (transaction_amount ,oring_change_in_cents)
            print "     %s: quarters: %i dimes: %i nickels: %i pennies: %i" % ("returned", \
                                                                               n_quarters ,n_dimes,n_nickels,n_pennies)
                                                                               
            print "*" * 40
        return {"nickels": n_nickels, "quarters": n_quarters, "dimes": n_dimes, "pennies": n_pennies}



def answer_homework_questions():
    
    """performs the monte carlo, making many instances of CookieJars under different assumptions."""
    ## a: What is the average total amount of change accumulated each year (assume X=5)? 
    #     What is the 1-sigma scatter about this quantity?

    ## let's simulate 50 cookie jars of 1 year each
    njars = 50
    
    jars = []
    for j in xrange(njars):
        jars.append(CookieJar(transactions_per_day=5,number_of_days_until_fill=365,deplete_quarters=False))
        jars[-1].fill_er_up()

    fin = numpy.array([x.final_value for x in jars])
    mn = fin.mean()
    st = numpy.std(fin)
    print "question a"
    print "-"*50
    
    print "mean value accumulated per year:",mn,"\nstandard deviation from {} trials:".format(njars), st
    print "-"*50
    # mean = $181.71
    # st   = $5.99

    ## b. What coin (quarter, dime, nickel, penny) are you most likely to accumulate 
    ##    over time? Second most likely? Does it depend on X?
    first  = {"nickels": 0, "quarters": 0, "dimes": 0, "pennies":0}
    second = {"nickels": 0, "quarters": 0, "dimes": 0, "pennies":0}
    for j in jars:
        first[j.final_order[1]] += 1
        second[j.final_order[2]] += 1

    print "\nquestion b"
    print "-"*50
    print "transactions per day:",5
    print "times each coin was the most common:\n",first
    print "times each coin was the second most common:\n",second
    # pennies always first, quarters usually second (sometimes dimes)
    
    ## now let's try # transaction changes
    for tr in [2,10,20]:
        jars = []
        for j in xrange(50):
            jars.append(CookieJar(transactions_per_day=tr,number_of_days_until_fill=365,deplete_quarters=False))
            jars[-1].fill_er_up()
        
        first  = {"nickels": 0, "quarters": 0, "dimes": 0, "pennies":0}
        second = {"nickels": 0, "quarters": 0, "dimes": 0, "pennies":0}
        for j in jars:
            first[j.final_order[1]] += 1
            second[j.final_order[2]] += 1
        print "\ntransactions per day:",tr
        print "times each coin was the most common:\n",first
        print "times each coin was the second most common:\n",second
    ## answer: no. it doesn't
    
    ## c. Let's say you need 8 quarters per week to do laundry. How many quarters do you have at the end of the year?
    ## (if you do not have enough quarters at the end of each week, use only what you have).
    jars = []
    for j in xrange(50):
        jars.append(CookieJar(transactions_per_day=5,number_of_days_until_fill=365,deplete_quarters=True))
        jars[-1].fill_er_up()
    nq = 0
    for j in jars:
        nq += j.final_contents["quarters"]
    
    print "-"*50
    print "\nquestion c"
    print "-"*50

    print "average # of quarters left after a year:",nq/len(jars)
    # answer = 28
    print "-"*50
    
if __name__ == "__main__":
    answer_homework_questions()
########NEW FILE########
__FILENAME__ = mknbindex
#!/usr/bin/env python
"""Simple script to auto-generate the index of notebooks in a given directory.
"""

import glob
import urllib

notebooks = sorted(glob.glob('*.ipynb'))

tpl = ( '* [{0}](http://nbviewer.ipython.org/url/raw.github.com/profjsb/python-bootcamp/master/Lectures/04_IPythonNotebookIntroduction/{1})' )


idx = [
"""Introduction to IPython
=======================

These notebooks introduce the basics of IPython, as part of the [Berkeley Python
Bootcamp](http://pythonbootcamp.info).

"""]

idx.extend(tpl.format(nb.replace('.ipynb',''), urllib.quote(nb))
           for nb in notebooks)

with open('README.md', 'w') as f:
    f.write('\n'.join(idx))
    f.write('\n')

########NEW FILE########
__FILENAME__ = talktools
"""Tools to style a talk."""

from IPython.display import HTML, display, YouTubeVideo

def prefix(url):
    prefix = '' if url.startswith('http') else 'http://'
    return prefix + url


def simple_link(url, name=None):
    name = url if name is None else name
    url = prefix(url)
    return '<a href="%s" target="_blank">%s</a>' % (url, name)


def html_link(url, name=None):
    return HTML(simple_link(url, name))


# Utility functions
def website(url, name=None, width=800, height=450):
    html = []
    if name:
        html.extend(['<div class="nb_link">',
                     simple_link(url, name),
                     '</div>'] )

    html.append('<iframe src="%s"  width="%s" height="%s">' %
                (prefix(url), width, height))
    return HTML('\n'.join(html))


def nbviewer(url, name=None, width=800, height=450):
    return website('nbviewer.ipython.org/url/' + url, name, width, height)

# Load and publish CSS
style = HTML(open('style.css').read())

display(style)

########NEW FILE########
__FILENAME__ = oop1_plots
import matplotlib.pyplot as plt
import numpy as np


data_vars = [ [0.2,0.7,'x'],
    [0.3,0.6,'y'],
    [0.22,0.5,'newx'],
    [0.21, 0.4,'coolest_y'],
    [0.19,0.24,'perimeter1' ] ]

code_vars = [ [0.2,0.7,'read_sensor()'],
    [0.20,0.5,'calculate_perimeter()'],
    [0.24,0.24,'generate_figure_for_nature_paper()' ] ]

def denude_plot():
    plt.xticks([])
    plt.yticks([])
    plt.xlim(0,1)
    plt.ylim(0,1)
    plt.xticks([])
    plt.yticks([])
    plt.xlim(0,1)
    plt.ylim(0,1)

def show_background1():
    plt.figure(figsize=(11.5,8))
    #plt.gcf().clf()
    rect_data = plt.Rectangle((0.1,0.1), 0.3, 0.7, facecolor="#e0e0f0")
    plt.gca().add_patch( rect_data ) 
    rect_code = plt.Rectangle((0.6,0.1), 0.3, 0.7, facecolor="#e0e0f0")
    plt.gca().add_patch( rect_code ) 
    plt.text(0.25, 0.85, 'Data (i.e., numbers)', style='italic', size=16, horizontalalignment='center' )
    plt.text(0.75, 0.85, 'Code', style='italic', size=16, horizontalalignment='center' )
    for n,avar in enumerate(data_vars):
        plt.text( avar[0], avar[1], avar[2], size=10, rotation=np.random.rand()*10.0-5.0, ha="center", va="center", bbox = dict(boxstyle="round", ec=(0.8, 0.1, 1.0), fc=(0.8, 0.4, 1.0),))
    for n,avar in enumerate(code_vars):
        plt.text( avar[0]+0.5, avar[1], avar[2], size=10, rotation=np.random.rand()*10.0-5.0, ha="center", va="center", bbox = dict(boxstyle="round", ec=(1.0, 0.1, 0.8), fc=(1.0, 0.4, 0.8),))
    denude_plot()

def code_to_data():
    ax=plt.gca()
    ax.arrow( data_vars[0][0]+0.5, data_vars[0][1], -0.4, 0.0, head_width=0.01, head_length=0.01,fc='k',ec='k' )
    ax.arrow( data_vars[0][0]+0.5, data_vars[0][1], -0.35,-0.1, head_width=0.01, head_length=0.01,fc='k',ec='k' )
    
def data_to_code():
    ax=plt.gca()
    ax.arrow( data_vars[0][0]+0.0, data_vars[0][1], 0.38, -0.18, head_width=0.01, head_length=0.01,fc='k',ec='k' )
    ax.arrow( data_vars[1][0]+0.0, data_vars[1][1], 0.25, -0.08, head_width=0.01, head_length=0.01,fc='k',ec='k' )
    ax.arrow( code_vars[1][0]+0.5, code_vars[1][1], -0.4, -0.26, head_width=0.01, head_length=0.01,fc='k',ec='k' )
    plt.show()

def Procedural_programming():
    show_background1()
    plt.show()

def Function1():
    show_background1()
    code_to_data()

def Function2():
    show_background1()
    data_to_code()

def Objects():
    plt.figure(figsize=(11.5,8))
    rect_obj = plt.Rectangle((0.1,0.1), 0.4, 0.7, facecolor="#101080")
    plt.gca().add_patch( rect_obj ) 
    rect_data = plt.Rectangle((0.7,0.15), 0.2, 0.2, facecolor="#e0e0f0")
    plt.gca().add_patch( rect_data ) 
    rect_code = plt.Rectangle((0.7,0.55), 0.2, 0.2, facecolor="#e0e0f0")
    plt.gca().add_patch( rect_code ) 
    plt.text(0.3, 0.85, 'Objects', size=16, style='italic', horizontalalignment='center' )
    plt.text(0.8, 0.8, '...(Data)...', size=12, style='italic', horizontalalignment='center' )
    plt.text(0.8, 0.4, '...(Code)...', size=12, style='italic',horizontalalignment='center' )
    for n,avar in enumerate([code_vars[0],code_vars[2]]):
        msg= 'Polygon Sensor %d\n---------------\n<\$$RAWDATA$\$>\n----------\n- acquire_data()\n- calculate_perimeter()\n- make_Nobel_fig()'%n
        plt.text( avar[0], avar[1], msg, size=10, rotation=np.random.rand()*10.0-5.0, ha="left", va="center", bbox = dict(boxstyle="round", ec=(1.0, 1.0, 0.1), fc=(1.0, 1.0, 0.1),))
        #plt.text( avar[0], avar[1], 'Polygon Sensor %d\n---------------\n- acquire_data()\n- calculate_perimeter()'%n, size=10, rotation=np.random.rand()*10.0-5.0, ha="left", va="center", bbox = dict(boxstyle="round", ec=(1.0, 0.1, 0.8), fc=(1.0, 0.4, 0.8),))
    denude_plot()

########NEW FILE########
__FILENAME__ = talktools
"""Tools to style a talk."""

from IPython.display import HTML, display, YouTubeVideo

def prefix(url):
    prefix = '' if url.startswith('http') else 'http://'
    return prefix + url


def simple_link(url, name=None):
    name = url if name is None else name
    url = prefix(url)
    return '<a href="%s" target="_blank">%s</a>' % (url, name)


def html_link(url, name=None):
    return HTML(simple_link(url, name))


# Utility functions
def website(url, name=None, width=800, height=450):
    html = []
    if name:
        html.extend(['<div class="nb_link">',
                     simple_link(url, name),
                     '</div>'] )

    html.append('<iframe src="%s"  width="%s" height="%s">' % 
                (prefix(url), width, height))
    return HTML('\n'.join(html))


def nbviewer(url, name=None, width=800, height=450):
    return website('nbviewer.ipython.org/url/' + url, name, width, height)

# Load and publish CSS
style = HTML(open('style.css').read())

display(style)

########NEW FILE########
__FILENAME__ = mycircle
class MyCircle(object):
    
    def _repr_html_(self):
        return "&#x25CB; (<b>html</b>)"

    def _repr_svg_(self):
        return """<svg width="100px" height="100px">
           <circle cx="50" cy="50" r="20" stroke="black" stroke-width="1" fill="blue"/>
        </svg>"""
    
    def _repr_latex_(self):
        return r"$\bigcirc \LaTeX$"

    def _repr_javascript_(self):
        return "alert('I am a circle!');"

########NEW FILE########
__FILENAME__ = mycircle2
# We first verify that indeed, `display_latex` doesn't do anything for this class:

print "Calling display_latex:"
display_latex(c2)

# Now we grab the latex formatter

latex_f = ip.display_formatter.formatters['text/latex']

# And register for our `AnotherCircle` class, the desired $\LaTeX$ format function. In this case we can use a simple lambda:

latex_f.for_type(AnotherCircle, lambda x: r"$\bigcirc \LaTeX$" )

# Calling `display_latex` once more now gives a different result:

print "Calling display_latex again:"
display_latex(c2)

########NEW FILE########
__FILENAME__ = talktools
"""Tools to style a talk."""

from IPython.display import HTML, display, YouTubeVideo

def prefix(url):
    prefix = '' if url.startswith('http') else 'http://'
    return prefix + url


def simple_link(url, name=None):
    name = url if name is None else name
    url = prefix(url)
    return '<a href="%s" target="_blank">%s</a>' % (url, name)


def html_link(url, name=None):
    return HTML(simple_link(url, name))


# Utility functions
def website(url, name=None, width=800, height=450):
    html = []
    if name:
        html.extend(['<div class="nb_link">',
                     simple_link(url, name),
                     '</div>'] )

    html.append('<iframe src="%s"  width="%s" height="%s">' % 
                (prefix(url), width, height))
    return HTML('\n'.join(html))


def nbviewer(url, name=None, width=800, height=450):
    return website('nbviewer.ipython.org/url/' + url, name, width, height)

# Load and publish CSS
style = HTML(open('style.css').read())

display(style)

########NEW FILE########
