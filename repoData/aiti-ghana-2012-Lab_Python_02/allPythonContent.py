__FILENAME__ = Lab03a_1
"""
Lab_Python_02
Extra Credit
Solutions for Extra Credit Question 1
"""


# getting input from the user
unencrypted = int(raw_input("Enter a number to encrypt: "))

encrypted = 0

while unencrypted > 0:
	
	# multiplying the encrypted number by 10
	encrypted *= 10
	
	# adding the last digit of what is left of the unencrypted number to it
	encrypted += unencrypted % 10
	
	# shortening the unencrypted number
	unencrypted //= 10


print "The encrypted number is %d" % encrypted

########NEW FILE########
__FILENAME__ = Lab03_2
"""
Lab_Python_02
Extra Credit
Solutions for Extra Credit Question 1
"""


# getting input from the user
unencrypted = int(raw_input("Enter a number to encrypt: "))

encrypted = 0
encrypted_old = 0

while unencrypted > 0:
	
	# multiplying both the encrypted numbers by 10
	encrypted *= 10
	encrypted_old *= 10
	
	#getting the last digit of what is left of the unencrypted number
	new_digit = unencrypted % 10

	#adding the new digit to the old encryption method before we transform it
	encrypted_old += new_digit

	#transforming the new digit
	new_digit = (new_digit + 7) % 10

	#adding the new digit
	encrypted += new_digit
	
	# shortening the unencrypted number
	unencrypted //= 10


print "Using the old method, the encrypted number is %d" % encrypted_old
print "Using the new method, the encrypted number is %d" % encrypted

########NEW FILE########
__FILENAME__ = UsingControlStructures
"""
Lab_Python_02
Solutions for Part II - Computer Exercises
"""



theInput = int(raw_input("Enter an integer: "))

## Question 5

# remember, 1 is True, and 0 is False
# so we can use the return value of the %
# operator directly as a condition
if theInput % 2:
	print 'odd'
else:
	print 'even'


## Question 6
print "--------"

# ages for my home
primarySchoolAge = 6
legalVotingAge = 18
presidentAge = 35
retirementAge = 65

givenAge = int(raw_input("Enter an age: "))

if givenAge < primarySchoolAge:
	print "Too young"

if givenAge >= legalVotingAge:
	print "Remember to vote!"

if givenAge >= presidentAge:
	print "Vote for me!"
else:
	print "You can't be president"

if givenAge >= retirementAge:
	print "Too old"


## Question 7
print "--------"

# with a for loop and range:
for i in range(39,-1,-3):
	print i

# with a while loop
i = 39
while i > -1:
	print i
	i -= 3


## Question 8
print "--------"

for i in range(6,31): #remember, the default step is 1, and the second argument is exclusive
	if i % 2 and i % 3 and  i % 5:
		print i	

## Question 9
print "--------"

n = 1
while True:
	if (79 * n) % 97 == 1:
		break #this statement exits the loop, without executing the next one
	n += 1
print n

########NEW FILE########
