__FILENAME__ = Lab05
"""
Lab_Python_05
Solutions for problesm 2 -7
"""

## Problem 2 - Factorial
# we can do this recursively and iteratively

# first the iterative method:
def factorial(n):
	answer = 1

	#we want to iterate over all of the numbers from n - 1
	for i in range(n,1,-1):
		answer *= i
	
	return answer

# now recursively:
def factorial(n):
	if n < 2:
		return 1
	else:
		return n * factorial(n-1)



## Problem 3 - Fibonacci
# this one can be done iteratively or recursively too

# first the iterative method:
def fibonacci(n):
	
	if n == 0:
		return []
	elif n == 1:
		return [1]
	else:
		out = [1,1]
		
		for i in range(2,n):
			new_number = out[i - 1] + out[i - 2]
			out.append(new_number)
		
		return out

# now recursively:
def fibonacci(n):
	if n == 0:
		return []
	elif n == 1:
		return [1]
	elif n == 2:
		return [1,1]
	else:
		out = fibonacci(n - 1)
		new_number = out[-1] + out[-2]
		out.append(new_number)
		return out


## Problem 4 - Prime Numbers
def prime(n):
	if n == 1:
		return False

	for i in range(2,n):
		if not n % i:
			return False
	return True



## Problem 5 - Palindrome
def isPalindrome(string):
	
	# strategy will be to look from the right and left simultaneously
	# maintain a left_cursor, which is our position from the left
	# and a right cursor, which is our position on the right
	left_cursor = 0
	right_cursor = len(string) - 1
	
	while right_cursor >= left_cursor:
		if not string[left_cursor] == string[right_cursor]:
			return False
		
		# now moving the cursors inwards
		left_cursor += 1
		right_cursor -= 1
	
	# if we get to this point, then it is a palindrome!
	return True

## Problem 6 - isSubstring
# you can do this in one line using 'substring in string'
# but good practice to do it this way
def isSubstring(substring, string):
	# using the strategy described in the problem
	string_position = 0

	# we want to iterate through every position in the string
	# where it is possible that the substring starts
	while string_position <= len(string) - len(substring):
		
		# if our current position in the string matches the first character of the substring,
		# then we have to check that the next characters in the string also match		
		if string[string_position] == substring[0]:
			match = True
			for i in range(1,len(substring)):
				if not substring[i] == string[string_position + i]:
					match = False
					break;
			
			# if every character in the substring appeared in order in the string,
			# then we win!	
			if match:
				return True
		
		# and now lets look at the next position in the string
		string_position += 1	
	
	# if we get out of the loop, then there was no match. :(
	return False


## Problem 7 - Max test score
# confusing problem for everyone. sorry!
def maxTestScore(answers_wrong, answers_a, answers_b):
	
	score = 0

	for i in range(len(answers_wrong)):
		
		# if the two friends had the same answer
		if answers_a[i] == answers_b[i]:
			
			# then if it was not a wrong answer
			if not answers_a[i] == answers_wrong[i]:
				# we can score 2
				score += 2
		else:
			# then we will always be able to score 1
			score += 1

	return score

########NEW FILE########
__FILENAME__ = tester
import sys
import traceback

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'

	def disable(self):
		self.HEADER = ''
		self.OKBLUE = ''
		self.OKGREEN = ''
		self.WARNING = ''
		self.FAIL = ''
		self.ENDC = ''

try:
	from Lab05 import *
except ImportError:
	print bcolors.FAIL + 'ERROR: No Lab05.py file found' + bcolors.ENDC
	sys.exit(1)


def test_harness(function,*args,**kwargs):

	def inner(*args,**kwargs):
		try:
			return function(*args, **kwargs)
		except Exception as e:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			return "ERROR: \n" + traceback.format_exc()

	return inner

@test_harness
def test_factorial():
	
	try:
		factorial
	except NameError:
		return "ERROR: factorial is not defined. Did you spell it right?"
	
	bla = factorial(1)
	if bla == 1:
		pass
	else:
		return "ERROR: Ran factorial(1). Expected 1, got:"+str( bla)
	bla = factorial(5)
	if bla == 120:
		pass
	else:
		return "ERROR: Ran factorial(5). Expected 120, got:"+str( bla)
	bla = factorial(19)
	if bla == 121645100408832000:
		pass
	else:
		return "ERROR: Ran factorial(19). Expected 121645100408832000, got:" + str( bla )
	return "OK"

@test_harness
def test_fibonacci():
	
	try:
		fibonacci
	except NameError:
		return "ERROR: fibonacci is not defined. Did you spell it right?"
	
	
	bla = fibonacci(1)
	if bla == [1]:
		pass
	else:
		return "ERROR: Ran fibonacci(1). Expected [1], got:"+str( bla)
	bla = fibonacci(2)
	if bla == [1,1]:
		pass
	else:
		return "ERROR: Ran fibonacci(2). Expected [1,1], got:"+str( bla)
	bla = fibonacci(9)
	if bla == [1, 1, 2, 3, 5, 8, 13, 21, 34]:
		pass
	else:
		return "ERROR: Ran fibonacci(9). Expected [1, 1, 2, 3, 5, 8, 13, 21, 34], got:" + str( bla )
	bla = fibonacci(15)
	if bla == [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]:
		pass
	else:
		return "ERROR: Ran fibonacci(15). Expected [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610], got:" + str( bla )
	return "OK"

@test_harness
def test_prime():
	
	try:
		prime
	except NameError:
		return "ERROR: prime is not defined. Did you spell it right?"
	
	
	bla = prime(1)
	if not bla:
		pass
	else:
		return "ERROR: Ran prime(1). Expected False, got:"+str( bla)
	bla = prime(2)
	if bla:
		pass
	else:
		return "ERROR: Ran prime(2). Expected True, got:"+str( bla)
	bla = prime(121)
	if not bla:
		pass
	else:
		return "ERROR: Ran prime(121). Expected False, got:" + str( bla )
	bla = prime(271)
	if bla:
		pass
	else:
		return "ERROR: Ran prime(271). Expected True, got:" + str( bla )
	return "OK"

@test_harness
def test_isPalindrome():
	
	try:
		isPalindrome
	except NameError:
		return "ERROR: isPalindrome is not defined. Did you spell it right?"


	bla = isPalindrome('able was I ere I saw elba')
	if bla is True:
		pass
	else:
		return "ERROR: Ran isPalindrome('able was I ere I saw elba'). Expected True, got:"+str( bla)
	
	bla = isPalindrome('Able was i ere I saw elba')
	if bla is False:
		pass
	else:
		return "ERROR: Ran isPalindrome('Able was i ere I saw elba'). Expected False, got:"+str( bla)
		
	bla = isPalindrome('amanaplanacanalpanama')
	if bla is True:
		pass
	else:
		return "ERROR: Ran isPalindrome('amanaplanacanalpanama'). Expected True, got:" + str( bla )
		
	bla = isPalindrome('a man a plan a canal panama')
	if bla is False:
		pass
	else:
		return "ERROR: Ran isPalindrome('a man a plan a canal panama'). Expected False, got:" + str( bla )
		
	bla = isPalindrome('yobananaboy')
	if bla is True:
		pass
	else:
		return "ERROR: Ran isPalindrome('yobananaboy'). Expected True, got:"+str( bla)\
		
	bla = isPalindrome('gohangasalamiimalasagnahog')
	if bla is True:
		pass
	else:
		return "ERROR: Ran isPalindrome('gohangasalamiimalasagnahog'). Expected True, got:"+str( bla)
		
	bla = isPalindrome('chicken')
	if bla is False:
		pass
	else:
		return "ERROR: Ran isPalindrom('chicken'). Expected True, got:" + str(bla)
		
	return "OK"

@test_harness
def test_isSubstring():
	
	try:
		isSubstring
	except NameError:
		return "ERROR: isSubstring is not defined. Did you spell it right?"
	
	
	bla = isSubstring('foo', 'foo')
	if bla:
		pass
	else:
		return "ERROR: Ran isSubstring('foo', 'foo'). Expected True, got:"+str( bla)
	bla = isSubstring('foo', 'barfoo')
	if	bla:
		pass
	else:
		return "ERROR: Ran isSubstring('foo', 'barfoo'). Expected True, got:"+str( bla)
	bla = isSubstring('foo', 'barbar')
	if not bla:
		pass
	else:
		return "ERROR: Ran isSubstring('foo', 'barbar'). Expected False, got:" + str( bla )
	bla = isSubstring('foo', 'fo')
	if not bla:
		pass
	else:
		return "ERROR: Ran isSubstring('foo', 'fo'). Expected False, got:" + str( bla )
	bla = isSubstring('ana', 'bananana rum')
	if bla:
		pass
	else:
		return "ERROR: Ran isSubstring('ana', 'bananana rum'). Expected True, got:"+str( bla)
	return "OK"

def tester():
	
	functions = [
				('factorial',test_factorial),
				('fibonacci',test_fibonacci),
				('prime',test_prime),
				('isPalindrome',test_isPalindrome),
				('isSubstring',test_isSubstring)
				]
				
	for name,func in functions:
		print bcolors.HEADER + 'Testing %s.......' % name + bcolors.ENDC
		result	= func()
		if result.startswith('ERROR'):
			print bcolors.FAIL + result + bcolors.ENDC
		else:
			print bcolors.OKGREEN + result + bcolors.ENDC
		print

if __name__ == '__main__':
	tester()

########NEW FILE########
