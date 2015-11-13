__FILENAME__ = guess_one
secret_number = 7

guess = input("What number am I thinking of? ")

if secret_number == guess:
    print "Yay! You got it."
else:
    print "No, that's not it."

########NEW FILE########
__FILENAME__ = guess_three
from random import randint

secret_number = randint(1, 10)

while True:
    guess = input("What number am I thinking of? ")

    if secret_number == guess:
        print "Yay! You got it."
        break
    elif secret_number > guess:
        print "No, that's too low."
    else:
        print "No, that's too high."


########NEW FILE########
__FILENAME__ = guess_two
from random import randint

secret_number = randint(1, 10)

while True:
    guess = input("What number am I thinking of? ")

    if secret_number == guess:
        print "Yay! You got it."
        break
    else:
        print "No, that's not it."



########NEW FILE########
__FILENAME__ = quizzer
"""
Concepts introduced: 
- opening and reading files
- importing a single function from a standard module
"""

from random import choice
import sys

def getquizfile():

  flashcards = []
  f = open('state_capitals.txt', 'r')
  for line in f:
    line = line.strip().split(',')
    flashcards.append(line)
  return flashcards

def playthegame(flashcards):

  while flashcards:
    x = choice(flashcards)
    question = x[0]
    answer = x[1]

    y = raw_input('%s: ' % (question) )
    if y.lower() == 'exit':
      sys.exit()
    elif y.lower() == answer.lower():
      print "Correct!"
      flashcards.remove(x)
    else:
      print "That is not correct, the answer is %s." % (answer)

if __name__ == '__main__':
  quizfile = getquizfile()
  playthegame(quizfile)


########NEW FILE########
__FILENAME__ = book
class Book:
    title = ""
    authors = []
    pages = 0

    def print_book(self):
        print self.title
        print "Authors"
        print "="*15
        for author in self.authors:
            print author
        print "Pages: ", self.pages

########NEW FILE########
