__FILENAME__ = binary_search_tests
a = []
print a

binary_insert(5.0,a)
print a

binary_insert(5.0,a)
print a

binary_insert(3.0,a)
print a

binary_insert(7.0,a)
print a

binary_insert(6.0,a)
print a

binary_insert(5.0,a)
print a

binary_insert(4.5,a)
print a

binary_insert(3.1,a)
print a

binary_insert(6.1,a)
print a

binary_insert(5.5,a)
print a

binary_insert(7.2,a)
print a

binary_insert(7.1,a)
print a

binary_insert(5.2,a)
print a

binary_insert(5.1,a)
print a

########NEW FILE########
__FILENAME__ = Lab04_4
"""
Lab_Python_04
Extra Credit
Solution to Extra Credit problem 4
"""


## Part A
# The right data structure to store the different market prices
# would be a dictionary whose keys are food items, and values
# either a list of prices, or another dictionary that maps
# the names of different stores to the price that they offer
# for example

multi_price_with_store_names  = {
					'bread' : {
							'shoprite' : 4.5,
							'maxi-mart' : 5.0,
							'r-link' : 0.5
						  },
					'water' : {
							'shoprite' : 0.9,
							'maxi-mart' : 0.8,
							'r-link' : 0.5
						  }
				}

# or...
multi_price_without_store_names = {
					'bread' : [
							4.5,
							5.0,
							0.5
						  ],
					'water' : [
							0.9,
							0.8,
							0.5
						  ]
				  }

# ultimately, what you need to do with the data will determine which data structure
# is better to use.


## Part B
# Binary Search
# Binary search insertion is very difficult to get right
# and it was awesome that some of you did it!
def binary_insert(new_float, some_list_of_floats):
	"""
	Binary Search works when inserting or searching through
	a sorted list. It works by repeatedly cutting the search
	space in half, until you find the place for which you look.

	It is similar to looking up a word in a dictionary.
	First, you open up half way, then check if the word you seek
	is before or after a word on that page. If it is after, you
	go to the middle of the second half of the dictionary,
	and if it is before, you go to the middle of the first
	half of the dictionary. This process repeats until you have
	found the definition.

	If you have questions about this algorithm or algorithms in
	general, I love to talk about them, and would definitely
	like to chat about algorithms, searching, sorts, runtime,
	et cetera!
	
	Also, this problem is notoriously hard to do correctly,
	so if you notice a bug in the code please let me know!!
	"""

	# upper and lower are variables that bound the range
	# of the list in which we are searching

	# initially, we are searching the whole list,
	# so upper is the last element, and lower is 0, the first
	upper = len(some_list_of_floats) - 1
	lower = 0
	
	# mid is the middle of the range 
	mid = (upper + lower) / 2

	# checking for corner solutions
	# if the input list is empty
	if upper == -1:
		some_list_of_floats.append(new_float)
		return

	# (when the new element is bigger or smaller than every other one)
	if new_float <= some_list_of_floats[lower]:
		# then we want to insert it before that element
		some_list_of_floats.insert(lower, new_float)
		return
	elif new_float >= some_list_of_floats[upper]:
		#then we want to insert it after that element
		some_list_of_floats.insert(upper + 1, new_float)
		return


	#while our range contains elements...
	while upper - lower > 0:
		
		if new_float < some_list_of_floats[mid]:
			# then we want to look at the left half
			upper = mid
		
		elif new_float > some_list_of_floats[mid]:
			# then we want to look at the right half
			# the plus one is important, because when
			# we find out mid, we round down
			lower = mid + 1
		
		else:
			# then new_float is equal to the middle one,
			# so we can insert it on either side
			some_list_of_floats.insert(mid,new_float)
			return
		
		mid = (upper + lower) / 2

	#ok, when we are here, we have found the spot!
	some_list_of_floats.insert(lower,new_float)
	return


## Part C
# finding the min cost
# this problem is not so tricky once you see
# the the minimum cost is the sum of the minimum costs
# for each item. The hard thing is understanding
# and working with the given data structures
def min_cost(grocery_list, item_to_price_list_dict):
	
	total_cost = 0
	
	for item in grocery_list:
		# for each item, we want to get the minimum
		# price out of all of them
		
		# first, get the list of prices for this item
		list_of_prices = item_to_price_list_dict[item]
		
		# then, find the minimum
		# python has a convenient min() function which
		# takes a list and returns the smallest element
		lowest_price_for_item = min(list_of_prices)
		
		# now we add it to our running total of cost
		total_cost += lowest_price_for_item
		
	return total_cost






########NEW FILE########
__FILENAME__ = Lab04_5
"""
Lab_Python_04
Extra Credit
Solutions for Extra Credit problem 5
"""

## Question A
# They should use a dictionary to keep track of which nodes
# have been seen. The dictionary should map the name of a
# node to a boolean indicating if that node has been seen.
# This allows for very fast and efficient lookup to check
# if a node has been seen or not, much faster than having to 
# walk through then entire list of nodes.

## Question B
# Which one will work faster depends on the structure of the
# Bus routes (the graph of nodes). This question is asking about
# The difference between breadth-first  and depth-first search.
# If you are curious, ask me or check it out on the internet to learn more.

## Question C
# A python Queue is a data structure that is highly optimized for addition
# and removal from either end, unlike a list, which is fast for additions
# and removals from only one end (the back, right side of it).
# John's strategy would benefit the most, because he uses to_visit
# As a queue, removing elements from the front, but adding them to the back.
# The Queue is a very common data structure, especially when building web
# And real-time applications that must handle many actions happening at once.
# If you ever find yourself adding elements to one end of a list, and removing
# Them from another, you may want to think about using a Queue. Again,
# please come see me, I would love to explain more or talk about other
# data structures (like a Stack, a Deque, Priority / heap queue, theres a lot!)


########NEW FILE########
__FILENAME__ = Lab04
"""
Lab_Python_04
Solutions for Questions 1 - 3
"""

## Question 1
print "Question 1:"

groceries = ['bananas', 'strawberries', 'apples', 'bread']

print "Initial list:"
print groceries

# a.
groceries.append('champagne')

print "After appending 'champagne':"
print groceries

# b.
groceries.remove('bread')

print "After removing 'bread':"
print groceries

#c.

# John should make a dictionary
# that maps each food item to the aisle in which it can be found
food_aisle_map = {}
for food_item in groceries:
	# [0] gets the first character of a string
	# and lower() converts it to lowercase
	aisle = food_item[0].lower()
	food_aisle_map[food_item] = aisle 


## Question 2
print
print "Question 2:"

#a. 
# A dictionary should be used because it provides
# a way to map from an item to its price

#b.
catalogue = {
		'apples' : 7.3,
		'bananas' : 5.5,
		'bread' : 1.0,
		'carrots' : 10.0,
		'champagne' : 20.90,
		'strawberries' : 32.6
	    }

print "The catalogue:"
print catalogue


#c.
catalogue['strawberries'] = 63.43
print "After changing price of strawberries: "
print catalogue

#d.
catalogue['chicken'] = 6.5
print "After adding chicken:"
print catalogue



## Question 3
print
print "Question 3:"

#a.
# The data structure that is best for this is a list,
# because it is a good way to keep track of multiple items

#b.
# The method .keys() returns a list of dictionaries keys
in_stock = catalogue.keys()

#c.
# Tuples are sequences that are immutable - they cannot change
# You can convert a list to a tuple using the tuple() function
always_in_stock = tuple(in_stock)

#d.
print "Come To shoprite! We always sell:"

# you can iterate through a tuple just like through a list
for item in always_in_stock:
	print item


########NEW FILE########
