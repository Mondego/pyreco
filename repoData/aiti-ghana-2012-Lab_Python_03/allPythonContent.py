__FILENAME__ = cipher
"""
Lab_Python_03
Extra Credit
Solution for Extra Credit Question 1 - Caesar Cipher
"""


unencoded_phrase = raw_input("Enter sentence to encrypt: ")
encoding_shift = int(raw_input("Enter shift value: "))

encoded_phrase = ''

for character in unencoded_phrase:

	# converting the character into an integer
	character_ascii = ord(character)
	
	if 65 <= character_ascii <= 90:
		# then it is a uppercase letter
		ascii_shift = 65
		is_letter = True
	elif 97 <= character_ascii <= 122:
		# then it is a lowercase letter
		ascii_shift = 97
		is_letter = True
	else:
		# then it is not a letter, so we pass it through unchanged 
		new_character = character
		is_letter = False

	
	if is_letter:
		
		# ascii_shift is by how much we have to shift
		# the ascii value to bring it between 0 and 25
		letter_index = character_ascii - ascii_shift

		# here we add the encoding shift, then use the 
		# modulus operator to constrain the value to 0 - 25
		new_index = (letter_index + encoding_shift) % 26
		
		# shifting the letter index back to the proper ascii range
		# and converting it back to a character
		new_character = chr(new_index + ascii_shift)

	
	# now adding the new character to the encoded phrase we are building
	encoded_phrase += new_character

print "The encoded phrase is: %s" % encoded_phrase



########NEW FILE########
__FILENAME__ = Lab03_1
"""
Lab_Python_03
Solution for Question 1
"""

#program to get the first 50 primes

#print the first 50 primes
n = 50

print "the first 50 primes:"

#initialize the counter that keeps
#track of how many primes we have found
prime_count = 0

#possible_prime is the number that
#we are going to check to see if it's prime
#2 is the first prime number, so we start there
possible_prime = 2

#we want to keep looking for primes as long
#as we have found less than the number for which
#we are looking (which is 50 in this case)
while prime_count < n:

    #initialize a counter that will keep track of
    #the number of divisors that possible_prime will have
    divisor_count = 0

    #we want to loop over every number from
    #1 to possible_prime, checking if it is
    #a divisor of possible_prime
    for i in range(1,possible_prime+1):

        #if i is a divisor of possible_prime...
        if possible_prime % i == 0:
            #increment the divisor count by 1
            divisor_count += 1

    #now we check if possible_prime is actually a
    #prime by checking the number of divisors that it has
    #a prime number has exactly 2 divisors
    if divisor_count == 2:
        #if possible_prime is actually prime,
        #we want to print it WITHOUT a newline
        #(which is what the comma does - prevent the newline)
        print possible_prime,

        #we also have to increment the counter that
        #is keeping track of the number of primes
        #that we have seen.
        prime_count += 1

        #if the number of primes that we have seen is a
        #multiple of 10 (10,20,30,40,50...)
        #then we want to print a newline!
        if prime_count % 10 == 0:
            #'print' on a line alone will print just
            #a newline
            print

    #now we have to consider the next number to
    #be a possible prime
    possible_prime += 1



########NEW FILE########
__FILENAME__ = Lab03_2
"""
Lab_Python_03
Solutions for Question 2
"""

## Lab03_2a

print 'a:'

# 6 rows, starting with 1
for i in range(1,7):
	
	#in each row, we want to print as many numbers as
	#the row that we are on plust one
	for j in range(i):
		print j + 1,

	#and after each row, a newling
	print


## Lab03_2b
print #for space between problems
print 'b:'

#6 rows, starting with 0
for i in range(6):

	#in each row, we want to print as many numbers as
	#6 minus the row that we are on
	for j in range(6 - i):
		print j + 1,


	#and after each row, a newline
	print

## Lab03_2c
print
print 'c:'

#6 rows, starting with 1
for i in range(1,7):

	#in each row, we want to print 2 times 6 minus i spaces,
	#and then as many numbers as the row we are on, counting down
	print ' ' * 2 *(6 - i), #you can multiply strings!
	for j in range(i,0,-1):
		print j,

	#and then a newline
	print

## Lab04_2d
print
print 'd:'

#6 rows, starting with 0
for i in range(6):
	
	#in each row, we want to print (i) * 2 spaces,
	# and then count up to 6 minus i
	print ' ' * 2 * i,
	for j in range(6 - i):
		print j + 1,

	#and then a newline
	print


## Lab04_2e
print
print 'e:'

#5 rows, starting with 0
for i in range(5):
	
	#the strategy for is is a little different
	#we need to build a string for each row, and then print
	#it, to avoid the spaces that 'print j,' would output
	
	#so create a variable that will hold the row value
	row = ''
	
	#we start with (4 - i) spaces
	row += ' ' * (4 - i)
	
	#then we count down from (i + 1) to 1 (exclusive of 1)
	for j in range(i+1,1,-1):
		row += str(j) #important to use str() to turn j into a string

	#now we need to count up from 1 to i + 1 (inclusive of i+1)
	for j in range(1,i+2): #i + 2 in order to include i + 1
		row += str(j)

	#and finally print the row, without a ',' so that a newline is automatically printed
	print row

########NEW FILE########
