__FILENAME__ = better_maze
# -*- coding: utf-8 -*-

import pygame

class Maze:

	start = ( 0, 0 )
	end = ( 0, 0 )
	user = ( 0, 0 )
	maze = []
	moves = 0
	dirty = []

	user_surface = None
	maze_surface = None

	def __init__ ( self, maze_file ):
		self.load_maze( maze_file )

	def load_maze ( self, maze_file ):

		self.maze = []

		f = open( maze_file, 'r' )
		row = 0
		for line in f:
			col = 0
			self.maze.append( [] )
			for char in line:
				if char == 'S':
					self.start = ( row, col )
				elif char == 'E':
					self.end = ( row, col )
				self.maze[row].append( char )
				col = col + 1
			row = row + 1
		f.close()

		self.size = ( col * 10, row * 10 )

		self.user = self.start

	def init_window ( self ):
		self.window = pygame.display.set_mode( self.size )
		pygame.display.set_caption( 'Maze'  )
		pygame.display.update()

		self.user_surface = pygame.Surface( ( 10, 10 ) )
		self.user_surface.fill( pygame.Color( 255, 255, 255 ) )

		self.maze_surface = pygame.Surface( self.size )

	def render_maze ( self ):
		self.maze_surface.fill( pygame.Color( 0, 0, 0 ) )

		red_block = pygame.Surface( ( 10, 10 ) )
		red_block.fill( pygame.Color( 255, 0, 0 ) )

		green_block = pygame.Surface( ( 10, 10 ) )
		green_block.fill( pygame.Color( 0, 255, 0 ) )

		gray_block = pygame.Surface( ( 10, 10 ) )
		gray_block.fill( pygame.Color( 200, 200, 200 ) )

		row = 0
		for row_data in self.maze:
			col = 0
			for char in row_data:
				if 'S' == char:
					self.maze_surface.blit( red_block, ( col * 10, row * 10 ) )
				elif 'E' == char:
					self.maze_surface.blit( green_block, ( col * 10, row * 10 ) )
				elif ' ' == char:
					pass
				else:
					self.maze_surface.blit( gray_block, ( col * 10, row * 10 ) )
				col = col + 1
			row = row + 1

	def run ( self ):
		self.init_window()
		self.render_maze()

		self.window.blit( self.maze_surface, ( 0, 0, self.size[1], self.size[0] ) )
		self.dirty.append( ( 0, 0, self.size[1], self.size[0] ) )

		self.window.blit( self.user_surface, ( self.start[1] * 10, self.start[0] * 10 ) )

		self.update()

		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					exit()
				elif event.type == pygame.KEYUP:
					goto = self.user

					if event.key == pygame.K_DOWN:
						goto = ( self.user[0]+1, self.user[1] )
					elif event.key == pygame.K_UP:
						goto = ( self.user[0]-1, self.user[1] )
					elif event.key == pygame.K_LEFT:
						goto = ( self.user[0], self.user[1]-1 )
					elif event.key == pygame.K_RIGHT:
						goto = ( self.user[0], self.user[1]+1 )

					if self.maze[goto[0]][goto[1]] == 'E':
						print "You escaped in %d moves!" % self.moves
						pygame.quit()
						exit()
					elif self.maze[goto[0]][goto[1]] != ' ' and self.maze[goto[0]][goto[1]] != 'S':
						goto = self.user

					if self.user != goto:

						self.window.blit( self.user_surface, ( goto[1] * 10, goto[0] * 10 ) )
						self.window.blit( self.maze_surface, ( self.user[1] * 10, self.user[0] * 10 ), ( self.user[1] * 10, self.user[0] * 10, 10, 10 ) )

						self.dirty.append( ( self.user[1] * 10, self.user[0] * 10, 10, 10 ) )
						self.dirty.append( ( goto[1] * 10, goto[0] * 10, 10, 10 ) )

						self.user = goto
						self.moves = self.moves + 1
						pygame.display.set_caption( 'Maze - %d' % self.moves  )

			self.update()

	def update ( self ):
		if 0 != len( self.dirty ):
			pygame.display.update( self.dirty )
			self.dirty = []

if __name__ == '__main__':
	import traceback, sys

	if 1 >= len( sys.argv ):
		print "You must specify a maze file!"
		exit(1)

	try:
		pygame.init()
		maze = Maze( sys.argv[1] )
		maze.run()
	except SystemExit, e:
		pass
	except:
		traceback.print_exc()
########NEW FILE########
__FILENAME__ = guess_the_number
# -*- coding: utf-8 -*-

import random

print "Guess The Number!"
print "----"

print "I can guess a number between 1 and any number you give me."

while True:
	try:
		number = raw_input( "What's the highest number I should pick? " )
		number = int( number )
		break
	except ValueError, e:
		print "\"%s\" isn't a number!" % number

print "Ok, I will guess a number between 1 and", number

computer_number =  random.randint( 0, number )

winner = False

while winner == False:
	while True:
		try:
			guess = raw_input( "Ok, guess the number! " )
			guess = int( guess )
			break
		except ValueError, e:
			print "\"%s\" isn't a number!" % guess
	if guess == computer_number:
		print "You got it!"
		winner = True
	else:
		if guess < computer_number:
			print "Too low. Try again!"
		else:
			print "Too high. Try again!"


########NEW FILE########
__FILENAME__ = hangman
# -*- coding: utf-8 -*-

from random import choice

def showHangman ( count ):

	head = ' '
	larm = ' '
	chest = ' '
	rarm = ' '
	torso = ' '
	lleg = ' '
	rleg = ' '

	if count > 0:
		head = 'O'
	if count > 1:
		chest = '|'
	if count > 2:
		larm = '\\'
	if count > 3:
		rarm = '/'
	if count > 4:
		torso = '|'
	if count > 5:
		lleg = '/'
	if count > 6:
		rleg = '\\'

	print "      .-----."
	print "      |     %s" % head
	print "      |    %s%s%s" % ( larm, chest, rarm )
	print "      |     %s" % torso
	print "      |    %s %s" % ( lleg, rleg )
	print "  ____|____"

def showState ( missed, guessed, stub ):
	print "=" * 40
	showHangman( len( missed ) )
	print
	print "  Guessed :", " ".join( guessed )
	print "   Missed :", " ".join( missed )
	print
	print "      Word:", "".join( stub )
	print

def main ():

	f = open( 'words.txt', 'r' )
	words = []
	for word in f:
		words.append( word.replace( "\n", '' ) )
	f.close()

	word = choice( words ).upper()
	found = 0
	stub = []
	for i in range( 0, len( word ) ):
		stub.append( "_" )

	guessed = []
	missed = []

	print "  Welcome To Hangman!"
	print

	while len( missed ) < 7 and len( word ) > found:
		showState( missed, guessed, stub )
		while True:
			guess = raw_input( "  Guess A Letter: " ).upper()
			print
			if len( guess ) != 1:
				print "  Oops! You can only guess one letter at a time. Try again!"
				print
			elif guess in guessed:
				print "  Oops! You already guessed that letter! Try again!"
				print
			else:
				if guess in word:
					for i in range( 0, len( word ) ):
						if guess == word[i]:
							stub[i] = guess
							found = found + 1
					print "  You guessed correct!"
				else:
					missed.append( guess )
					print "  You guessed wrong!"
				guessed.append( guess )
				break
		print

	showState( missed, guessed, stub )

	if len( missed ) >= 7:
		print "  You lost!"
		print
		print "  The word was", word
	else:
		print "  You won!"
		print "  Great job!"
	print

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = maze
# -*- coding: utf-8 -*-

import curses

class Maze:

	start = ( 0, 0 )
	end = ( 0, 0 )
	user = ( 0, 0 )
	maze = []
	moves = 0

	def __init__ ( self, stdscr, maze_file=None ):
		self.scr = stdscr
		self.load_maze( maze_file )

	def load_maze ( self, maze_file ):

		self.scr.clear()
		self.maze = []

		f = open( maze_file, 'r' )
		row = 0
		for line in f:
			col = 0
			self.maze.append( [] )
			for char in line:
				if char == 'S':
					self.start = ( row, col )
				elif char == 'E':
					self.end = ( row, col )
				self.maze[row].append( char )
				col = col + 1
			row = row + 1
		f.close()

		self.user = self.start
		self.render_maze()

	def render_maze ( self ):
		row = 0
		for row_data in self.maze:
			col = 0
			for char in row_data:
				self.scr.addstr( row + 2, col, char )
				col = col + 1
			row = row + 1
		self.scr.addstr( self.user[0] + 2, self.user[1], "*" )
		self.scr.move( 0, 0 )
		self.scr.refresh()

	def main ( self ):
		self.scr.addstr( 0, 0, "Welcome To Maze!  Arrow keys move, Q to quit." )

		while True:
			goto = None
			c = self.scr.getch()
			if 0 < c < 256:
				c = chr( c )
				if c in 'Qq' : break
				else: pass
			elif c == curses.KEY_UP:
				goto = ( self.user[0]-1, self.user[1] )
			elif c == curses.KEY_DOWN:
				goto = ( self.user[0]+1, self.user[1] )
			elif c == curses.KEY_LEFT:
				goto = ( self.user[0], self.user[1]-1 )
			elif c == curses.KEY_RIGHT:
				goto = ( self.user[0], self.user[1]+1 )
			else: pass

			if self.maze[goto[0]][goto[1]] == 'E':
				self.scr.clear()
				self.scr.refresh()
				self.scr.addstr( 0, 0, "You escaped in %d moves! Hit any key to quit." % self.moves )
				c = self.scr.getch()
				break
			elif self.maze[goto[0]][goto[1]] == ' ' or self.maze[goto[0]][goto[1]] == 'S':
				self.user = goto
				self.moves = self.moves + 1

			self.render_maze()

if __name__ == '__main__':
	import traceback, sys

	if 1 >= len( sys.argv ):
		print "You must specify a maze file!"
		exit(1)

	try:
		stdscr = curses.initscr()
		curses.noecho() ; curses.cbreak()
		stdscr.keypad( 1 )
		maze = Maze( stdscr, sys.argv[1] )
		maze.main()
		# Set everything back to normal
		stdscr.keypad( 0 )
		curses.echo() ; curses.nocbreak()
		curses.endwin()
	except:
		stdscr.keypad( 0 )
		curses.echo() ; curses.nocbreak()
		curses.endwin()
		traceback.print_exc()

########NEW FILE########
__FILENAME__ = rock_paper_scissors
# -*- coding: utf-8 -*-

from random import randint

ROCK = 0
PAPER = 1
SCISSORS = 2

StringValues = ( 'Rock', 'Paper', 'Scissors' )

def compare ( a, b ):
	if a == b:
		return 0
	elif a == ROCK and b == PAPER:
		return -1
	elif a == PAPER and b == SCISSORS:
		return -1
	elif a == SCISSORS and b == ROCK:
		return -1
	return 1

def main ():

	print "Rock, Paper, Scissors"
	print

	while True:

		choice = None
		while choice == None:
			option = raw_input( "1,2,3 Shoot! [Rock, Paper, Scissors] " )
			if "rock" == option.lower():
				choice = ROCK
			elif "paper" == option.lower():
				choice = PAPER
			elif "scissors" == option.lower():
				choice = SCISSORS
			else:
				print "You can't pick %s!" % option
				print
				continue
			break

		computer_choice = randint( 0, 2 )

		print
		print "     You Chose : %s" % StringValues[choice]
		print "Computer Chose : %s" % StringValues[computer_choice]
		print

		winner = compare( choice, computer_choice )

		if 1 == winner:
			print "You Win!"
		elif -1 == winner:
			print "You Lose!"
		else:
			print "Tie!"

		print
		option = raw_input( "Pay Again? [Y/n] " )
		if 'n' == option.lower():
			break
		print

if __name__ == "__main__":
	main()
########NEW FILE########
