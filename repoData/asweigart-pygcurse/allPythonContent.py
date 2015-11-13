__FILENAME__ = demo_dodger
# Pygcurse Dodger
# By Al Sweigart al@inventwithpython.com

# This program is a demo for the Pygcurse module.
# Simplified BSD License, Copyright 2011 Al Sweigart

import pygame, random, sys, time, pygcurse
from pygame.locals import *

GREEN = (0, 255, 0)
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,0,0)

WINWIDTH = 40
WINHEIGHT = 50
TEXTCOLOR = WHITE
BACKGROUNDCOLOR = (0, 0, 0)
FPS = 40
BADDIEMINSIZE = 1
BADDIEMAXSIZE = 5
BADDIEMINSPEED = 4
BADDIEMAXSPEED = 1
ADDNEWBADDIERATE = 3

win = pygcurse.PygcurseWindow(WINWIDTH, WINHEIGHT, fullscreen=False)
pygame.display.set_caption('Pygcurse Dodger')
win.autoupdate = False

def main():
    showStartScreen()
    pygame.mouse.set_visible(False)
    mainClock = pygame.time.Clock()
    gameOver = False

    newGame = True
    while True:
        if gameOver and time.time() - 4 > gameOverTime:
            newGame = True
        if newGame:
            newGame = False
            pygame.mouse.set_pos(win.centerx * win.cellwidth, (win.bottom - 4) * win.cellheight)
            mousex, mousey = pygame.mouse.get_pos()
            cellx, celly = win.getcoordinatesatpixel(mousex, mousey)
            baddies = []
            baddieAddCounter = 0
            gameOver = False
            score = 0

        win.fill(bgcolor=BLACK)

        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                terminate()
            if event.type == MOUSEMOTION and not gameOver:
                mousex, mousey = event.pos
                cellx, celly = win.getcoordinatesatpixel(mousex, mousey)

        # add new baddies if needed
        if baddieAddCounter == ADDNEWBADDIERATE:
            speed = random.randint(BADDIEMAXSPEED, BADDIEMINSPEED)
            baddies.append({'size': random.randint(BADDIEMINSIZE, BADDIEMAXSIZE),
                            'speed': speed,
                            'x': random.randint(0, win.width),
                            'y': -BADDIEMAXSIZE,
                            'movecounter': speed})
            baddieAddCounter = 0
        else:
            baddieAddCounter += 1


        # move baddies down, remove if needed
        for i in range(len(baddies)-1, -1, -1):
            if baddies[i]['movecounter'] == 0:
                baddies[i]['y'] += 1
                baddies[i]['movecounter'] = baddies[i]['speed']
            else:
                baddies[i]['movecounter'] -= 1

            if baddies[i]['y'] > win.height:
                del baddies[i]


        # check if hit
        if not gameOver:
            for baddie in baddies:
                if cellx >= baddie['x'] and celly >= baddie['y'] and cellx < baddie['x']+baddie['size'] and celly < baddie['y']+baddie['size']:
                    gameOver = True
                    gameOverTime = time.time()
                    break
            score += 1

        # draw baddies to screen
        for baddie in baddies:
            win.fill('#', GREEN, BLACK, (baddie['x'], baddie['y'], baddie['size'], baddie['size']))

        if not gameOver:
            playercolor = WHITE
        else:
            playercolor = RED
            win.putchars('GAME OVER', win.centerx-4, win.centery, fgcolor=RED, bgcolor=BLACK)

        win.putchar('@', cellx, celly, playercolor)
        win.putchars('Score: %s' % (score), win.width - 14, 1, fgcolor=WHITE)
        win.update()
        mainClock.tick(FPS)


def showStartScreen():
    while checkForKeyPress() is None:
        win.fill(bgcolor=BLACK)
        win.putchars('Pygcurse Dodger', win.centerx-8, win.centery, fgcolor=TEXTCOLOR)
        if int(time.time() * 2) % 2 == 0: # flashing
            win.putchars('Press a key to start!', win.centerx-11, win.centery+1, fgcolor=TEXTCOLOR)
        win.update()


def checkForKeyPress():
    # Go through event queue looking for a KEYUP event.
    # Grab KEYDOWN events to remove them from the event queue.
    for event in pygame.event.get([KEYDOWN, KEYUP]):
        if event.type == KEYDOWN:
            continue
        if event.key == K_ESCAPE:
            terminate()
        return event.key
    return None


def terminate():
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = demo_maze
# Pygcurse Maze
# By Al Sweigart al@inventwithpython.com
# Maze Generation code by Joe Wingbermuehle

# This program is a demo for the Pygcurse module.
# Simplified BSD License, Copyright 2011 Al Sweigart

import pygcurse, pygame, sys, random, time
from pygame.locals import *

BLUE = (0, 0, 128)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLACK = (0,0,0)
RED = (255,0,0)

MAZE_WIDTH  = 41
MAZE_HEIGHT = 41
FPS = 40

win = pygcurse.PygcurseWindow(MAZE_WIDTH, MAZE_HEIGHT, fullscreen=False)
pygame.display.set_caption('Pygcurse Maze')
win.autowindowupdate = False
win.autoupdate = False


class JoeWingMaze():
    # Maze generator in Python
    # Joe Wingbermuehle
    # 2010-10-06
    # http://joewing.net/programs/games/python/maze.py

    def __init__(self, width=21, height=21):
        if width % 2 == 0:
            width += 1
        if height % 2 == 0:
            height += 1

        # The size of the maze (must be odd).
        self.width  = width
        self.height = height

        # The maze.
        self.maze = dict()

        # Generate and display a random maze.
        self.init_maze()
        self.generate_maze()
        #self.display_maze() # prints out the maze to stdout

    # Display the maze.
    def display_maze(self):
       for y in range(0, self.height):
          for x in range(0, self.width):
             if self.maze[x][y] == 0:
                sys.stdout.write(" ")
             else:
                sys.stdout.write("#")
          sys.stdout.write("\n")

    # Initialize the maze.
    def init_maze(self):
       for x in range(0, self.width):
          self.maze[x] = dict()
          for y in range(0, self.height):
             self.maze[x][y] = 1

    # Carve the maze starting at x, y.
    def carve_maze(self, x, y):
       dir = random.randint(0, 3)
       count = 0
       while count < 4:
          dx = 0
          dy = 0
          if   dir == 0:
             dx = 1
          elif dir == 1:
             dy = 1
          elif dir == 2:
             dx = -1
          else:
             dy = -1
          x1 = x + dx
          y1 = y + dy
          x2 = x1 + dx
          y2 = y1 + dy
          if x2 > 0 and x2 < self.width and y2 > 0 and y2 < self.height:
             if self.maze[x1][y1] == 1 and self.maze[x2][y2] == 1:
                self.maze[x1][y1] = 0
                self.maze[x2][y2] = 0
                self.carve_maze(x2, y2)
          count = count + 1
          dir = (dir + 1) % 4

    # Generate the maze.
    def generate_maze(self):
       random.seed()
       #self.maze[1][1] = 0
       self.carve_maze(1, 1)
       #self.maze[1][0] = 0
       #self.maze[self.width - 2][self.height - 1] = 0

       # maze generator modified to have randomly placed entrance/exit.
       startx = starty = endx = endy = 0
       while self.maze[startx][starty]:
           startx = random.randint(1, self.width-2)
           starty = random.randint(1, self.height-2)
       while self.maze[endx][endy] or endx == 0 or abs(startx - endx) < int(self.width / 3) or abs(starty - endy) < int(self.height / 3):
           endx = random.randint(1, self.width-2)
           endy = random.randint(1, self.height-2)

       self.maze[startx][starty] = 0
       self.maze[endx][endy] = 0

       self.startx = startx
       self.starty = starty
       self.endx = endx
       self.endy = endy





def main():
    newGame = True
    solved = False
    moveLeft = moveRight = moveUp = moveDown = False
    lastmovetime = sys.maxsize
    mainClock = pygame.time.Clock()
    while True:
        if newGame:
            newGame = False # if you want to see something cool, change the False to True
            jwmaze = JoeWingMaze(MAZE_WIDTH, MAZE_HEIGHT)
            maze = jwmaze.maze
            solved = False
            playerx, playery = jwmaze.startx, jwmaze.starty
            endx, endy = jwmaze.endx, jwmaze.endy
            breadcrumbs = {}

        if (playerx, playery) not in breadcrumbs:
            breadcrumbs[(playerx, playery)] = True

        # handle input
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == KEYDOWN:
                if solved or event.key == K_BACKSPACE:
                    newGame = True
                elif event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == K_UP:
                    moveUp = True
                    moveDown = False
                elif event.key == K_DOWN:
                    moveDown = True
                    moveUp = False
                elif event.key == K_LEFT:
                    moveLeft = True
                    moveRight = False
                elif event.key == K_RIGHT:
                    moveRight = True
                    moveLeft = False
                lastmovetime = time.time() - 1

            elif event.type == KEYUP:
                if event.key == K_UP:
                    moveUp = False
                elif event.key == K_DOWN:
                    moveDown = False
                elif event.key == K_LEFT:
                    moveLeft = False
                elif event.key == K_RIGHT:
                    moveRight = False

        # move the player (if allowed)
        if time.time() - 0.05 > lastmovetime:
            if moveUp and isOnBoard(playerx, playery-1) and maze[playerx][playery-1] == 0:
                playery -= 1
            elif moveDown and isOnBoard(playerx, playery+1) and maze[playerx][playery+1] == 0:
                playery += 1
            elif moveLeft and isOnBoard(playerx-1, playery) and maze[playerx-1][playery] == 0:
                playerx -= 1
            elif moveRight and isOnBoard(playerx+1, playery) and maze[playerx+1][playery] == 0:
                playerx += 1

            lastmovetime = time.time()
            if playerx == endx and playery == endy:
                solved = True

        # display maze
        drawMaze(win, maze, breadcrumbs)
        if solved:
            win.cursor = (win.centerx - 4, win.centery)
            win.write('Solved!', fgcolor=YELLOW, bgcolor=RED)
            moveLeft = moveRight = moveUp = moveDown = False
        win.putchar('@', playerx, playery, RED, BLACK)
        win.putchar('O', jwmaze.endx, jwmaze.endy, GREEN, BLACK)
        win.update()
        pygame.display.update()
        mainClock.tick(FPS)


def isOnBoard(x, y):
    return x >= 0 and y >= 0 and x < MAZE_WIDTH and y < MAZE_HEIGHT


def drawMaze(win, maze, breadcrumbs):
    for x in range(MAZE_WIDTH):
        for y in range(MAZE_HEIGHT):
            if maze[x][y] != 0:
                win.paint(x, y, BLUE)
            else:
                win.paint(x, y, BLACK)
            if (x, y) in breadcrumbs:
                win.putchar('.', x, y, RED, BLACK)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = demo_reversi
"""
The following five lines were added to this previously text-based stdio
program. You can play the original program by commenting out the following
five lines. This demostrates how stdio programs can be converted to Pygcurse
programs with minimal effort.

Simplified BSD License, Copyright 2011 Al Sweigart
"""
import pygcurse
win = pygcurse.PygcurseWindow(50, 25, 'Reversi')
print = win.pygprint
input = win.input
# To get this to work in Python 2, comment the previous two lines and
# uncomment the following lines: (And also modify the print() calls in the code
# to get rid of the "end" keyword argument.
#import sys
#sys.stdout = win
#input = win.raw_input
win.setscreencolors('aqua', 'black', clear=True)
#===========================================================================

# Mini Reversi (with a smaller displayed board)

import random
import sys

def drawBoard(board):
    # This function prints out the board that it was passed. Returns None.
    HLINE = ' +--------+'
    print('  12345678')
    print(HLINE)
    for y in range(8):
        print('%s|' % (y+1), end='')
        for x in range(8):
            print(board[x][y], end='')
        print('|')
    print(HLINE)


def resetBoard(board):
    # Blanks out the board it is passed, except for the original starting position.
    for x in range(8):
        for y in range(8):
            board[x][y] = ' '

    # Starting pieces:
    board[3][3] = 'X'
    board[3][4] = 'O'
    board[4][3] = 'O'
    board[4][4] = 'X'


def getNewBoard():
    # Creates a brand new, blank board data structure.
    board = []
    for i in range(8):
        board.append([' '] * 8)

    return board


def isValidMove(board, tile, xstart, ystart):
    # Returns False if the player's move on space xstart, ystart is invalid.
    # If it is a valid move, returns a list of spaces that would become the player's if they made a move here.
    if board[xstart][ystart] != ' ' or not isOnBoard(xstart, ystart):
        return False

    board[xstart][ystart] = tile # temporarily set the tile on the board.

    if tile == 'X':
        otherTile = 'O'
    else:
        otherTile = 'X'

    tilesToFlip = []
    for xdirection, ydirection in [[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]]:
        x, y = xstart, ystart
        x += xdirection # first step in the direction
        y += ydirection # first step in the direction
        if isOnBoard(x, y) and board[x][y] == otherTile:
            # There is a piece belonging to the other player next to our piece.
            x += xdirection
            y += ydirection
            if not isOnBoard(x, y):
                continue
            while board[x][y] == otherTile:
                x += xdirection
                y += ydirection
                if not isOnBoard(x, y): # break out of while loop, then continue in for loop
                    break
            if not isOnBoard(x, y):
                continue
            if board[x][y] == tile:
                # There are pieces to flip over. Go in the reverse direction until we reach the original space, noting all the tiles along the way.
                while True:
                    x -= xdirection
                    y -= ydirection
                    if x == xstart and y == ystart:
                        break
                    tilesToFlip.append([x, y])

    board[xstart][ystart] = ' ' # restore the empty space
    if len(tilesToFlip) == 0: # If no tiles were flipped, this is not a valid move.
        return False
    return tilesToFlip


def isOnBoard(x, y):
    # Returns True if the coordinates are located on the board.
    return x >= 0 and x <= 7 and y >= 0 and y <=7


def getBoardWithValidMoves(board, tile):
    # Returns a new board with . marking the valid moves the given player can make.
    dupeBoard = getBoardCopy(board)

    for x, y in getValidMoves(dupeBoard, tile):
        dupeBoard[x][y] = '.'
    return dupeBoard


def getValidMoves(board, tile):
    # Returns a list of [x,y] lists of valid moves for the given player on the given board.
    validMoves = []

    for x in range(8):
        for y in range(8):
            if isValidMove(board, tile, x, y) != False:
                validMoves.append([x, y])
    return validMoves


def getScoreOfBoard(board):
    # Determine the score by counting the tiles. Returns a dictionary with keys 'X' and 'O'.
    xscore = 0
    oscore = 0
    for x in range(8):
        for y in range(8):
            if board[x][y] == 'X':
                xscore += 1
            if board[x][y] == 'O':
                oscore += 1
    return {'X':xscore, 'O':oscore}


def enterPlayerTile():
    # Let's the player type which tile they want to be.
    # Returns a list with the player's tile as the first item, and the computer's tile as the second.
    tile = ''
    while not (tile == 'X' or tile == 'O'):
        print('Do you want to be X or O?')
        tile = input().upper()

    # the first element in the list is the player's tile, the second is the computer's tile.
    if tile == 'X':
        return ['X', 'O']
    else:
        return ['O', 'X']


def whoGoesFirst():
    # Randomly choose the player who goes first.
    if random.randint(0, 1) == 0:
        return 'computer'
    else:
        return 'player'


def playAgain():
    # This function returns True if the player wants to play again, otherwise it returns False.
    print('Do you want to play again? (yes or no)')
    return input().lower().startswith('y')


def makeMove(board, tile, xstart, ystart):
    # Place the tile on the board at xstart, ystart, and flip any of the opponent's pieces.
    # Returns False if this is an invalid move, True if it is valid.
    tilesToFlip = isValidMove(board, tile, xstart, ystart)

    if tilesToFlip == False:
        return False

    board[xstart][ystart] = tile
    for x, y in tilesToFlip:
        board[x][y] = tile
    return True


def getBoardCopy(board):
    # Make a duplicate of the board list and return the duplicate.
    dupeBoard = getNewBoard()

    for x in range(8):
        for y in range(8):
            dupeBoard[x][y] = board[x][y]

    return dupeBoard


def isOnCorner(x, y):
    # Returns True if the position is in one of the four corners.
    return (x == 0 and y == 0) or (x == 7 and y == 0) or (x == 0 and y == 7) or (x == 7 and y == 7)


def getPlayerMove(board, playerTile):
    # Let the player type in their move.
    # Returns the move as [x, y] (or returns the strings 'hints' or 'quit')
    DIGITS1TO8 = '1 2 3 4 5 6 7 8'.split()
    while True:
        print('Enter your move, or type quit to end the game, or hints to turn off/on hints.')
        move = input().lower()
        if move == 'quit':
            return 'quit'
        if move == 'hints':
            return 'hints'

        if len(move) == 2 and move[0] in DIGITS1TO8 and move[1] in DIGITS1TO8:
            x = int(move[0]) - 1
            y = int(move[1]) - 1
            if isValidMove(board, playerTile, x, y) == False:
                continue
            else:
                break
        else:
            print('That is not a valid move. Type the x digit (1-8), then the y digit (1-8).')
            print('For example, 81 will be the top-right corner.')

    return [x, y]


def getComputerMove(board, computerTile):
    # Given a board and the computer's tile, determine where to
    # move and return that move as a [x, y] list.
    possibleMoves = getValidMoves(board, computerTile)

    # randomize the order of the possible moves
    random.shuffle(possibleMoves)

    # always go for a corner if available.
    for x, y in possibleMoves:
        if isOnCorner(x, y):
            return [x, y]

    # Go through all the possible moves and remember the best scoring move
    bestScore = -1
    for x, y in possibleMoves:
        dupeBoard = getBoardCopy(board)
        makeMove(dupeBoard, computerTile, x, y)
        score = getScoreOfBoard(dupeBoard)[computerTile]
        if score > bestScore:
            bestMove = [x, y]
            bestScore = score
    return bestMove


def showPoints(playerTile, computerTile):
    # Prints out the current score.
    scores = getScoreOfBoard(mainBoard)
    print('You have %s points. The computer has %s points.' % (scores[playerTile], scores[computerTile]))



print('Welcome to Reversi!')

while True:
    # Reset the board and game.
    mainBoard = getNewBoard()
    resetBoard(mainBoard)
    playerTile, computerTile = enterPlayerTile()
    showHints = False
    turn = whoGoesFirst()
    print('The ' + turn + ' will go first.')

    while True:
        if turn == 'player':
            # Player's turn.
            if showHints:
                validMovesBoard = getBoardWithValidMoves(mainBoard, playerTile)
                drawBoard(validMovesBoard)
            else:
                drawBoard(mainBoard)
            showPoints(playerTile, computerTile)
            move = getPlayerMove(mainBoard, playerTile)
            if move == 'quit':
                print('Thanks for playing!')
                sys.exit() # terminate the program
            elif move == 'hints':
                showHints = not showHints
                continue
            else:
                makeMove(mainBoard, playerTile, move[0], move[1])

            if getValidMoves(mainBoard, computerTile) == []:
                break
            else:
                turn = 'computer'

        else:
            # Computer's turn.
            drawBoard(mainBoard)
            showPoints(playerTile, computerTile)
            input('Press Enter to see the computer\'s move.')
            x, y = getComputerMove(mainBoard, computerTile)
            makeMove(mainBoard, computerTile, x, y)

            if getValidMoves(mainBoard, playerTile) == []:
                break
            else:
                turn = 'player'

    # Display the final score.
    drawBoard(mainBoard)
    scores = getScoreOfBoard(mainBoard)
    print('X scored %s points. O scored %s points.' % (scores['X'], scores['O']))
    if scores[playerTile] > scores[computerTile]:
        print('You beat the computer by %s points! Congratulations!' % (scores[playerTile] - scores[computerTile]))
    elif scores[playerTile] < scores[computerTile]:
        print('You lost. The computer beat you by %s points.' % (scores[computerTile] - scores[playerTile]))
    else:
        print('The game was a tie!')

    if not playAgain():
        break

########NEW FILE########
__FILENAME__ = demo_shadowtest
# Simplified BSD License, Copyright 2011 Al Sweigart

import pygcurse, pygame, sys
from pygame.locals import *
win = pygcurse.PygcurseWindow(40, 25)
win.autoblit = False

xoffset = 1
yoffset = 1
mousex = mousey = 0
while True:
    for event in pygame.event.get(): # the event loop
        if event.type == QUIT or event.type == KEYDOWN and event.key == K_ESCAPE:
            pygame.quit()
            sys.exit()

        if event.type == KEYDOWN:
            if event.key == K_UP:
                yoffset -= 1
            elif event.key == K_DOWN:
                yoffset += 1
            elif event.key == K_LEFT:
                xoffset -= 1
            elif event.key == K_RIGHT:
                xoffset += 1
            elif event.key == K_p:
                win.fullscreen = not win.fullscreen
            elif event.key == K_d:
                win._debugchars()
        elif event.type == MOUSEMOTION:
            mousex, mousey = win.getcoordinatesatpixel(event.pos, onscreen=False)

    win.setscreencolors('white', 'blue', clear=True)
    win.fill(bgcolor='red', region=(15, 10, 5, 5))
    win.addshadow(51, (15, 10, 5, 5), xoffset=xoffset, yoffset=yoffset)

    #win.drawline((6,6), (mousex, mousey), bgcolor='red')
    win.drawline((6,6), (mousex, mousey), char='+', fgcolor='yellow', bgcolor='green')

    win.cursor = 0, win.height-3
    win.write('Use mouse to move line, arrow keys to move shadow, p to switch to fullscreen.')
    win.cursor = 0, win.height-1
    win.putchars('xoffset=%s, yoffset=%s    ' % (xoffset, yoffset))
    win.blittowindow()

########NEW FILE########
__FILENAME__ = demo_textboxtest
# Simplified BSD License, Copyright 2011 Al Sweigart

import pygcurse, pygame, sys
from pygame.locals import *
win = pygcurse.PygcurseWindow(40, 25)
win.autoblit = False


box = pygcurse.PygcurseTextbox(win, (4, 4, 20, 14), fgcolor='red', bgcolor='black', border='basic', wrap=True, marginleft=3, caption='Hello world!')
box.text = 'The Ojibway aboriginal people in North America used cowry shells which they called sacred Miigis Shells or whiteshells in Midewiwin ceremonies, and the Whiteshell Provincial Park in Manitoba, Canada is named after this type of shell. There is some debate about how the Ojibway traded for or found these shells, so far inland and so far north, very distant from the natural habitat. Oral stories and birch bark scrolls seem to indicate that the shells were found in the ground, or washed up on the shores of lakes or rivers. Finding the cowry shells so far inland could indicate the previous use of them by an earlier tribe or group in the area, who may have obtained them through an extensive trade network in the ancient past. Petroforms in the Whiteshell Provincial Park may be as old as 8,000 years.'
eraseBox = False
while True:
    for event in pygame.event.get(): # the event loop
        if event.type == QUIT or event.type == KEYDOWN and event.key == K_ESCAPE:
            pygame.quit()
            sys.exit()

        if event.type == KEYDOWN:
            if event.key == K_UP:
                box.height -= 1
            elif event.key == K_DOWN:
                box.height += 1
            elif event.key == K_LEFT:
                box.width -= 1
            elif event.key == K_RIGHT:
                box.width += 1
            elif event.key == K_w:
                box.y -= 1
            elif event.key == K_s:
                box.y += 1
            elif event.key == K_a:
                box.x -= 1
            elif event.key == K_d:
                box.x += 1
            elif event.key == K_r:
                box.x = 4
                box.y = 4
                box.width = 20
                box.height = 14
            elif event.key == K_p:
                win.fullscreen = not win.fullscreen
            elif event.key == K_d:
                win._debugchars()
            elif event.key == K_m:
                eraseBox = not eraseBox
            elif event.key == K_f:
                #win.font = pygame.sysfont.SysFont('freesansbold', 24, (255,0,0))
                win.height = 30
    win.setscreencolors('white', 'blue', clear=True)
    box.update()
    if eraseBox:
        box.erase()
    win.cursor = 0, win.height-3
    win.pygprint('WASD to move, arrow keys for height, p to switch to fullscreen.')
    win.cursor = 0, win.height-1
    win.putchars('x=%s, y=%s, width=%s, height=%s    ' % (box.x, box.y, box.width, box.height))
    win.blittowindow()


########NEW FILE########
__FILENAME__ = demo_textris
# Textris (a Tetris clone)
# By Al Sweigart al@inventwithpython.com
# Simplified BSD License, Copyright 2011 Al Sweigart

import random, time, pygame, sys
import pygcurse as pygcurse
from pygame.locals import *

FPS = 25
WINDOWWIDTH = 26
WINDOWHEIGHT = 27
BOARDWIDTH = 10
BOARDHEIGHT = 20
BLANK = None

LEFTMARGIN = 4
TOPMARGIN = 4

MOVESIDEWAYSFREQ = 0.15
MOVEDOWNFREQ = 0.15


#               R    G    B
WHITE       = (255, 255, 255)
GRAY        = (185, 185, 185)
BLACK       = (  0,   0,   0)
RED         = (155,   0,   0)
GREEN       = (  0, 155,   0)
BLUE        = (  0,   0, 155)
YELLOW      = (155, 155,   0)

BORDERCOLOR = BLUE
BGCOLOR = BLACK
TEXTCOLOR = WHITE
COLORS = (BLUE, GREEN, RED, YELLOW)


TEMPLATEWIDTH = 5
TEMPLATEHEIGHT = 5

S_PIECE_TEMPLATE = [['.....',
                     '.....',
                     '..OO.',
                     '.OO..',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..OO.',
                     '...O.',
                     '.....']]

Z_PIECE_TEMPLATE = [['.....',
                     '.....',
                     '.OO..',
                     '..OO.',
                     '.....'],
                    ['.....',
                     '..O..',
                     '.OO..',
                     '.O...',
                     '.....']]

I_PIECE_TEMPLATE = [['..O..',
                     '..O..',
                     '..O..',
                     '..O..',
                     '.....'],
                    ['.....',
                     '.....',
                     'OOOO.',
                     '.....',
                     '.....']]

O_PIECE_TEMPLATE = [['.....',
                     '.....',
                     '.OO..',
                     '.OO..',
                     '.....']]

J_PIECE_TEMPLATE = [['.....',
                     '.O...',
                     '.OOO.',
                     '.....',
                     '.....'],
                    ['.....',
                     '..OO.',
                     '..O..',
                     '..O..',
                     '.....'],
                    ['.....',
                     '.....',
                     '.OOO.',
                     '...O.',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..O..',
                     '.OO..',
                     '.....']]

L_PIECE_TEMPLATE = [['.....',
                     '...O.',
                     '.OOO.',
                     '.....',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..O..',
                     '..OO.',
                     '.....'],
                    ['.....',
                     '.....',
                     '.OOO.',
                     '.O...',
                     '.....'],
                    ['.....',
                     '.OO..',
                     '..O..',
                     '..O..',
                     '.....']]

T_PIECE_TEMPLATE = [['.....',
                     '..O..',
                     '.OOO.',
                     '.....',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..OO.',
                     '..O..',
                     '.....'],
                    ['.....',
                     '.....',
                     '.OOO.',
                     '..O..',
                     '.....'],
                    ['.....',
                     '..O..',
                     '.OO..',
                     '..O..',
                     '.....']]

PIECES = {'S': S_PIECE_TEMPLATE,
          'Z': Z_PIECE_TEMPLATE,
          'J': J_PIECE_TEMPLATE,
          'L': L_PIECE_TEMPLATE,
          'I': I_PIECE_TEMPLATE,
          'O': O_PIECE_TEMPLATE,
          'T': T_PIECE_TEMPLATE}

# Convert the shapes in PIECES from our text-friendly format above to a
# programmer-friendly format.
for p in PIECES: # loop through each piece
    for r in range(len(PIECES[p])): # loop through each rotation of the piece
        shapeData = []
        for x in range(TEMPLATEWIDTH): # loop through each column of the rotation of the piece
            column = []
            assert len(PIECES[p][r]) == TEMPLATEWIDTH, 'Malformed shape given for piece %s, rotation %s' % (p, r)
            for y in range(TEMPLATEHEIGHT): # loop through each character in the column of the rotation of the piece
                assert len(PIECES[p][r][y]) == TEMPLATEHEIGHT, 'Malformed shape given for piece %s, rotation %s' % (p, r)
                if PIECES[p][r][y][x] == '.':
                    column.append(BLANK)
                else:
                    column.append(1)
            shapeData.append(column)
        PIECES[p][r] = shapeData


def main():
    global FPSCLOCK, WINDOWSURF, BOARDBOX
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    WINDOWSURF = pygcurse.PygcurseWindow(WINDOWWIDTH, WINDOWHEIGHT, 'Textris', font=pygame.font.Font(None, 24))
    WINDOWSURF.autoupdate = False
    BOARDBOX = pygcurse.PygcurseTextbox(WINDOWSURF, (LEFTMARGIN-1, TOPMARGIN-1, BOARDWIDTH+2, BOARDHEIGHT+2))

    showTextScreen('Textris')
    while True: # main game loop
        if random.randint(0, 1) == 0:
            pygame.mixer.music.load('tetrisb.mid')
        else:
            pygame.mixer.music.load('tetrisc.mid')
        pygame.mixer.music.play(-1, 0.0)
        runGame()
        pygame.mixer.music.stop()
        showTextScreen('Game Over')


def showTextScreen(text):
    # This function displays large text in the
    # center of the screen until a key is pressed.
    WINDOWSURF.setscreencolors('white', 'black', True)
    WINDOWSURF.cursor = WINDOWSURF.centerx - int(len(text)/2), WINDOWSURF.centery
    WINDOWSURF.write(str(text), fgcolor=WHITE)

    WINDOWSURF.cursor = WINDOWSURF.centerx - int(len('Press a key to continue.')/2), WINDOWSURF.centery + 4
    WINDOWSURF.write('Press a key to continue.', fgcolor='gray')

    while checkForKeyPress() == None:
        WINDOWSURF.update()
        FPSCLOCK.tick()


def terminate():
    pygame.quit()
    sys.exit()


def runGame():
    # setup variables for the start of the game
    board = getNewBoard()
    lastMoveDownTime = time.time()
    lastMoveSidewaysTime = time.time()
    lastFallTime = time.time()
    movingDown = False # note: there is no movingUp variable
    movingLeft = False
    movingRight = False
    score = 0
    level, fallFreq = calculateLevelAndFallFreq(score)

    currentPiece = getNewPiece()
    nextPiece = getNewPiece()

    while True: # main game loop
        if currentPiece == None:
            # No current piece in play, so start a new piece at the top
            currentPiece = nextPiece
            nextPiece = getNewPiece()
            lastFallTime = time.time() # reset lastFallTime

            if not isValidPosition(board, currentPiece):
                return # can't fit a new piece on the board, so game over

        checkForQuit()
        for event in pygame.event.get(): # event handling loop
            if event.type == KEYUP:
                if (event.key == K_p):
                    # Pausing the game
                    WINDOWSURF.fill(BGCOLOR)
                    pygame.mixer.music.stop()
                    showTextScreen('Paused') # pause until a key press
                    pygame.mixer.music.play(-1, 0.0)
                    lastFallTime = time.time()
                    lastMoveDownTime = time.time()
                    lastMoveSidewaysTime = time.time()
                elif (event.key == K_LEFT or event.key == K_a):
                    movingLeft = False
                elif (event.key == K_RIGHT or event.key == K_d):
                    movingRight = False
                elif (event.key == K_DOWN or event.key == K_s):
                    movingDown = False

            elif event.type == KEYDOWN:
                # moving the block sideways
                if (event.key == K_LEFT or event.key == K_a) and isValidPosition(board, currentPiece, adjX=-1):
                    currentPiece['x'] -= 1
                    lastMoveSidewaysTime = time.time()
                    movingLeft = True
                    movingRight = False
                    lastMoveSidewaysTime = time.time()
                elif (event.key == K_RIGHT or event.key == K_d) and isValidPosition(board, currentPiece, adjX=1):
                    currentPiece['x'] += 1
                    movingRight = True
                    movingLeft = False
                    lastMoveSidewaysTime = time.time()

                # rotating the block (if there is room to rotate)
                elif (event.key == K_UP or event.key == K_w):
                    currentPiece['rotation'] = (currentPiece['rotation'] + 1) % len(PIECES[currentPiece['shape']])
                    if not isValidPosition(board, currentPiece):
                        currentPiece['rotation'] = (currentPiece['rotation'] - 1) % len(PIECES[currentPiece['shape']])
                elif (event.key == K_q): # rotate the other direction
                    currentPiece['rotation'] = (currentPiece['rotation'] - 1) % len(PIECES[currentPiece['shape']])
                    if not isValidPosition(board, currentPiece):
                        currentPiece['rotation'] = (currentPiece['rotation'] + 1) % len(PIECES[currentPiece['shape']])

                # making the block fall faster with the down key
                elif (event.key == K_DOWN or event.key == K_s):
                    movingDown = True
                    if isValidPosition(board, currentPiece, adjY=1):
                        currentPiece['y'] += 1
                    lastMoveDownTime = time.time()

                # move the current block all the way down
                elif event.key == K_SPACE:
                    movingDown = False
                    movingLeft = False
                    movingRight = False
                    for i in range(1, BOARDHEIGHT):
                        if not isValidPosition(board, currentPiece, adjY=i):
                            break
                    currentPiece['y'] += (i-1)

        # handle moving the block because of user input
        if (movingLeft or movingRight) and time.time() - lastMoveSidewaysTime > MOVESIDEWAYSFREQ:
            if movingLeft and isValidPosition(board, currentPiece, adjX=-1):
                currentPiece['x'] -= 1
            elif movingRight and isValidPosition(board, currentPiece, adjX=1):
                currentPiece['x'] += 1
            lastMoveSidewaysTime = time.time()

        if movingDown and time.time() - lastMoveDownTime > MOVEDOWNFREQ and isValidPosition(board, currentPiece, adjY=1):
            currentPiece['y'] += 1
            lastMoveDownTime = time.time()

        # let the piece fall if it is time to fall
        if time.time() - lastFallTime > fallFreq:
            # see if the piece has hit the bottom
            if hasHitBottom(board, currentPiece):
                # set the piece on the board, and update game info
                addToBoard(board, currentPiece)
                score += removeCompleteLines(board)
                level, fallFreq = calculateLevelAndFallFreq(score)
                currentPiece = None
            else:
                # just move the block down
                currentPiece['y'] += 1
                lastFallTime = time.time()

        # drawing everything on the screen
        WINDOWSURF.setscreencolors(clear=True)
        drawBoard(board)
        drawStatus(score, level)
        drawNextPiece(nextPiece)
        if currentPiece != None:
            drawPiece(currentPiece)

        WINDOWSURF.update()
        FPSCLOCK.tick(FPS)


def checkForQuit():
    for event in pygame.event.get(QUIT): # get all the QUIT events
        terminate() # terminate if any QUIT events are present
    for event in pygame.event.get(KEYUP): # get all the KEYUP events
        if event.key == K_ESCAPE:
            terminate() # terminate if the KEYUP event was for the Esc key
        pygame.event.post(event) # put the other KEYUP event objects back


def calculateLevelAndFallFreq(score):
    # Based on the score, return the level the player is on and
    # how many seconds pass until a falling piece falls one space.
    level = int(score / 10) + 1
    return level, 0.27 - (level * 0.02)


def getNewPiece():
    # return a random new piece in a random rotation and color
    shape = random.choice(list(PIECES.keys()))
    newPiece = {'shape': shape,
                'rotation': random.randint(0, len(PIECES[shape]) - 1),
                'x': int(BOARDWIDTH / 2) - int(TEMPLATEWIDTH / 2),
                'y': -2, # start it above the board (i.e. less than 0)
                'color': random.randint(0, len(COLORS)-1)}
    return newPiece


def addToBoard(board, piece):
    # fill in the board based on piece's location, shape, and rotation
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            if PIECES[piece['shape']][piece['rotation']][x][y] != BLANK:
                board[x + piece['x']][y + piece['y']] = piece['color']


def checkForKeyPress():
    # Go through event queue looking for a KEYUP event.
    # Grab KEYDOWN events to remove them from the event queue.
    for event in pygame.event.get([KEYDOWN, KEYUP]):
        if event.type == KEYDOWN:
            continue
        if event.key == K_ESCAPE:
            terminate()
        return event.key
    return None


def getNewBoard():
    # create and return a new blank board data structure
    board = []
    for i in range(BOARDWIDTH):
        board.append([BLANK] * BOARDHEIGHT)
    return board


def hasHitBottom(board, piece):
    # Returns True if the piece's bottom is currently on top of something
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            if PIECES[piece['shape']][piece['rotation']][x][y] == BLANK or y + piece['y'] + 1 < 0:
                continue # box is above the board or this box is blank
            if y + piece['y'] + 1 == BOARDHEIGHT:
                return True # box is on bottom of the board
            if board[x + piece['x']][y + piece['y'] + 1] != BLANK:
                return True # box is on top of another box on the board
    return False


def isOnBoard(x, y):
    return x >= 0 and x < BOARDWIDTH and y < BOARDHEIGHT


def isValidPosition(board, piece, adjX=0, adjY=0):
    # Return True if the piece is within the board and not colliding
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            if y + piece['y'] + adjY < 0 or PIECES[piece['shape']][piece['rotation']][x][y] == BLANK:
                continue
            if not isOnBoard(x + piece['x'] + adjX, y + piece['y'] + adjY):
                return False
            if board[x + piece['x'] + adjX][y + piece['y'] + adjY] != BLANK:
                return False
    return True


def isCompleteLine(board, y):
    # Return True if the line filled with boxes with no gaps.
    for x in range(BOARDWIDTH):
        if board[x][y] == BLANK:
            return False
    return True


def removeCompleteLines(board):
    # Remove any completed lines on the board, move everything above them down, and return the number of complete lines.
    numLinesRemoved = 0
    y = BOARDHEIGHT - 1 # start y at the bottom of the board
    while y >= 0:
        if isCompleteLine(board, y):
            # Remove the line and pull boxes down by one line.
            for pullDownY in range(y, 0, -1):
                for x in range(BOARDWIDTH):
                    board[x][pullDownY] = board[x][pullDownY-1]
            # Set very top line to blank.
            for x in range(BOARDWIDTH):
                board[x][0] = BLANK
            numLinesRemoved += 1
            # Note on the next iteration of the loop, y is the same.
            # This is so that if the line that was pulled down is also
            # complete, it will be removed.
        else:
            y -= 1 # move on to check next row up
    return numLinesRemoved


def drawBoard(board):
    # draw the border around the board
    BOARDBOX.update()

    # draw the individual boxes on the board
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            drawBox(x, y, board[x][y])


def drawBox(x, y, color, cellx=None, celly=None):
    # draw a single box (each tetromino piece has four boxes)
    # at xy coordinates on the board. Or, if cellx & celly
    # are specified, draw to the pixel coordinates stored in
    # cellx & celly (this is used for the "Next" piece.)
    if color == BLANK:
        return
    if cellx is None and celly is None:
        cellx, celly = x + LEFTMARGIN, y + TOPMARGIN
    WINDOWSURF.putchar('O', x=cellx, y=celly, fgcolor=COLORS[color], bgcolor='black')


def drawStatus(score, level):
    # draw the score text
    WINDOWSURF.putchars('Score:', x=WINDOWWIDTH-8, y=2, fgcolor='gray', bgcolor='black')
    WINDOWSURF.putchars(str(score), x=WINDOWWIDTH-7, y=3, fgcolor='white', bgcolor='black')
    # draw the level text
    WINDOWSURF.putchars('Level:', x=WINDOWWIDTH-8, y=5, fgcolor='gray', bgcolor='black')
    WINDOWSURF.putchars(str(level), x=WINDOWWIDTH-7, y=6, fgcolor='white', bgcolor='black')

def drawNextPiece(piece):
    # draw the "next" text
    WINDOWSURF.putchars('Next:', x=WINDOWWIDTH-8, y=8, fgcolor='gray', bgcolor='black')

    # draw the "next" piece
    drawPiece(piece, cellx=WINDOWWIDTH-8, celly=9)


def drawPiece(piece, cellx=None, celly=None):
    shapeToDraw = PIECES[piece['shape']][piece['rotation']]
    if cellx == None and celly == None:
        # if cellx & celly hasn't been specified, use the location stored in the piece data structure
        cellx, celly = piece['x'] + LEFTMARGIN, piece['y'] + TOPMARGIN

    # draw each of the blocks that make up the piece
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            if shapeToDraw[x][y] != BLANK:
                drawBox(None, None, piece['color'], cellx + x, celly + y)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = demo_tictactoe
"""
The following five lines were added to this previously text-based stdio
program. You can play the original program by commenting out the following
five lines. This demostrates how stdio programs can be converted to Pygcurse
programs with minimal effort.

Note that this only works for Python 3, since print in Python 2
is a statement rather than a function.

Simplified BSD License, Copyright 2011 Al Sweigart
"""
import pygcurse
win = pygcurse.PygcurseWindow(40, 25, 'Tic Tac Toe')
print = win.pygprint
input = win.input
# To get this to work in Python 2, comment the previous two lines and
# uncomment the following lines:
#import sys
#sys.stdout = win
#input = win.raw_input
win.setscreencolors('lime', 'blue', clear=True)
#===========================================================================

# Tic Tac Toe

import random

def drawBoard(board):
    # This function prints out the board that it was passed.

    # "board" is a list of 10 strings representing the board (ignore index 0)
    print('   |   |')
    print(' ' + board[7] + ' | ' + board[8] + ' | ' + board[9])
    print('   |   |')
    print('-----------')
    print('   |   |')
    print(' ' + board[4] + ' | ' + board[5] + ' | ' + board[6])
    print('   |   |')
    print('-----------')
    print('   |   |')
    print(' ' + board[1] + ' | ' + board[2] + ' | ' + board[3])
    print('   |   |')

def inputPlayerLetter():
    # Let's the player type which letter they want to be.
    # Returns a list with the player's letter as the first item, and the computer's letter as the second.
    letter = ''
    while not (letter == 'X' or letter == 'O'):
        print('Do you want to be X or O?')
        letter = input('>').upper()

    # the first element in the list is the player's letter, the second is the computer's letter.
    if letter == 'X':
        return ['X', 'O']
    else:
        return ['O', 'X']

def whoGoesFirst():
    # Randomly choose the player who goes first.
    if random.randint(0, 1) == 0:
        return 'computer'
    else:
        return 'player'

def playAgain():
    # This function returns True if the player wants to play again, otherwise it returns False.
    print('Do you want to play again? (yes or no)')
    return input('>').lower().startswith('y')

def makeMove(board, letter, move):
    board[move] = letter

def isWinner(bo, le):
    # Given a board and a player's letter, this function returns True if that player has won.
    # We use bo instead of board and le instead of letter so we don't have to type as much.
    return ((bo[7] == le and bo[8] == le and bo[9] == le) or # across the top
    (bo[4] == le and bo[5] == le and bo[6] == le) or # across the middle
    (bo[1] == le and bo[2] == le and bo[3] == le) or # across the bottom
    (bo[7] == le and bo[4] == le and bo[1] == le) or # down the left side
    (bo[8] == le and bo[5] == le and bo[2] == le) or # down the middle
    (bo[9] == le and bo[6] == le and bo[3] == le) or # down the right side
    (bo[7] == le and bo[5] == le and bo[3] == le) or # diagonal
    (bo[9] == le and bo[5] == le and bo[1] == le)) # diagonal

def getBoardCopy(board):
    # Make a duplicate of the board list and return it the duplicate.
    dupeBoard = []

    for i in board:
        dupeBoard.append(i)

    return dupeBoard

def isSpaceFree(board, move):
    # Return true if the passed move is free on the passed board.
    return board[move] == ' '

def getPlayerMove(board):
    # Let the player type in his move.
    move = ' '
    while move not in '1 2 3 4 5 6 7 8 9'.split() or not isSpaceFree(board, int(move)):
        print('What is your next move? (1-9)')
        move = input('>')
    return int(move)

def chooseRandomMoveFromList(board, movesList):
    # Returns a valid move from the passed list on the passed board.
    # Returns None if there is no valid move.
    possibleMoves = []
    for i in movesList:
        if isSpaceFree(board, i):
            possibleMoves.append(i)

    if len(possibleMoves) != 0:
        return random.choice(possibleMoves)
    else:
        return None

def getComputerMove(board, computerLetter):
    # Given a board and the computer's letter, determine where to move and return that move.
    if computerLetter == 'X':
        playerLetter = 'O'
    else:
        playerLetter = 'X'

    # Here is our algorithm for our Tic Tac Toe AI:
    # First, check if we can win in the next move
    for i in range(1, 10):
        copy = getBoardCopy(board)
        if isSpaceFree(copy, i):
            makeMove(copy, computerLetter, i)
            if isWinner(copy, computerLetter):
                return i

    # Check if the player could win on his next move, and block them.
    for i in range(1, 10):
        copy = getBoardCopy(board)
        if isSpaceFree(copy, i):
            makeMove(copy, playerLetter, i)
            if isWinner(copy, playerLetter):
                return i

    # Try to take one of the corners, if they are free.
    move = chooseRandomMoveFromList(board, [1, 3, 7, 9])
    if move != None:
        return move

    # Try to take the center, if it is free.
    if isSpaceFree(board, 5):
        return 5

    # Move on one of the sides.
    return chooseRandomMoveFromList(board, [2, 4, 6, 8])

def isBoardFull(board):
    # Return True if every space on the board has been taken. Otherwise return False.
    for i in range(1, 10):
        if isSpaceFree(board, i):
            return False
    return True


print('Welcome to Tic Tac Toe!')

while True:
    # Reset the board
    theBoard = [' '] * 10
    playerLetter, computerLetter = inputPlayerLetter()
    turn = whoGoesFirst()
    print('The ' + turn + ' will go first.')
    gameIsPlaying = True

    while gameIsPlaying:
        if turn == 'player':
            # Player's turn.
            drawBoard(theBoard)
            move = getPlayerMove(theBoard)
            makeMove(theBoard, playerLetter, move)

            if isWinner(theBoard, playerLetter):
                drawBoard(theBoard)
                print('Hooray! You have won the game!')
                gameIsPlaying = False
            else:
                if isBoardFull(theBoard):
                    drawBoard(theBoard)
                    print('The game is a tie!')
                    break
                else:
                    turn = 'computer'

        else:
            # Computer's turn.
            move = getComputerMove(theBoard, computerLetter)
            makeMove(theBoard, computerLetter, move)

            if isWinner(theBoard, computerLetter):
                drawBoard(theBoard)
                print('The computer has beaten you! You lose.')
                gameIsPlaying = False
            else:
                if isBoardFull(theBoard):
                    drawBoard(theBoard)
                    print('The game is a tie!')
                    break
                else:
                    turn = 'player'

    if not playAgain():
        break

########NEW FILE########
__FILENAME__ = pygcurse
"""
Please forgive any typos or errors in the comments, I'll be cleaning them up as frequently as I can.


Pygcurse v0.1 alpha

Pygcurse (pronounced "pig curse") is a curses library emulator that runs on top of the Pygame framework. It provides an easy way to create text adventures, roguelikes, and console-style applications.

Unfortunately, the curses library that comes with the Python standard library does not work on Windows. The excellent Console module from effbot provides curses-like features, but it only runs on Windows and not Mac/Linux. By using Pygame, Pygcurse is able to run on all platforms.

Pygcurse provides several benefits over normal text-based stdio programs:

    1) Color text and background.
    2) The ability to move the cursor and print text anywhere in the console window.
    3) The ability to make console apps that make use of the mouse.
    4) The ability to have programs respond to individual key presses, instead of waiting for the user to type an entire string and press enter (as with input()/raw_input()).
    5) Since the console window that Pygcurse uses is just a Pygame surface object, additional drawing and transformations can be applied to it. Multiple consoles can also be used in the same program.

Pygcurse requires Pygame to be installed. Pygame can be downloaded from http://pygame.org

Pygcurse was developed by Al Sweigart (al@inventwithpython.com)
https://github.com/asweigart/pygcurse


Simplified BSD License:

Copyright 2011 Al Sweigart. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY Al Sweigart ''AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Al Sweigart OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of Al Sweigart.
"""

import copy
import time
import sys
import textwrap
import pygame
from pygame.locals import *

"""
Some nomenclature in this module's comments explained:

Cells:
The space for each character is called a cell in this module. Cells are all of an identical size, which is based on the font being used. (only a single font of a single size can be used in a PygcurseSurface object. Cell coordinates refer to the positions of characters on the surface. Pixel coordinates refer to the position of each pixel.

Scrolling:
The term "scrolling" refers to when a character is printed at the bottom right corner, which causes all the characters on the surface to be moved up and a blank row to be created at the bottom. The print() and write() functions causes scolls if it prints enough characters. The putchar() and putchars() functions do not.

Color parameters:
Several Pygcurse functions take colors for their parameters. These can almost always (there might be some exceptions) be:
    1) A pygame.Color object.
    2) An RGB tuple of three integers, 0 to 255 (like Pygame uses)
    3) An RGBA tuple of four integers, 0 to 255 (like Pygame uses)
    4) A string such as 'blue', 'lime', or 'gray' (or any of the strings listed in the colornames gloal dictionary. This dict can be updated with more colors if the user wants.)
    5) None, which means use whatever color the cell already uses.

Region parameters:
A "region" defines an area of the surface. It can be the following formats:
    1) Four-integer tuple (x, y, width, height)
    2) Four-integer tuple (x, y, None, None) which means x,y and extending to the right & bottom edge of the surface
    3) None or (None, None, None, None) which means the entire surface
    4) pygame.Rect object

Note about flickering: If your program is experiencing a lot of flicker, than you should disable the self._autoupdate member. By default, this is enabled and the screen is redrawn after each method call that makes a change to the screen.
"""


DEFAULTFGCOLOR = pygame.Color(164, 164, 164, 255) # default foreground color is gray (must be a pygame.Color object)
DEFAULTBGCOLOR = pygame.Color(0, 0, 0, 255) # default background color is black (must be a pygame.Color object)
ERASECOLOR = pygame.Color(0, 0, 0, 0) # erase color has 0 alpha level (must be a pygame.Color object)

# Internally used constants:
_NEW_WINDOW = 'new_window'
FULLSCREEN = 'full_screen'

# Directional constants:
NORTH = 'N'
EAST = 'E'
SOUTH = 'S'
WEST = 'W'
NORTHEAST = 'NE'
NORTHWEST = 'NW'
SOUTHEAST = 'SE'
SOUTHWEST = 'SW'

# A mapping of strings to color objects.
colornames = {'white':   pygame.Color(255, 255, 255),
              'yellow':  pygame.Color(255, 255,   0),
              'fuchsia': pygame.Color(255,   0, 255),
              'red':     pygame.Color(255,   0,   0),
              'silver':  pygame.Color(192, 192, 192),
              'gray':    pygame.Color(128, 128, 128),
              'olive':   pygame.Color(128, 128,   0),
              'purple':  pygame.Color(128,   0, 128),
              'maroon':  pygame.Color(128,   0,   0),
              'aqua':    pygame.Color(  0, 255, 255),
              'lime':    pygame.Color(  0, 255,   0),
              'teal':    pygame.Color(  0, 128, 128),
              'green':   pygame.Color(  0, 128,   0),
              'blue':    pygame.Color(  0,   0, 255),
              'navy':    pygame.Color(  0,   0, 128),
              'black':   pygame.Color(  0,   0,   0)}


class PygcurseSurface(object):

    """
    A PygcurseSurface object is the ascii-based analog of Pygame's Surface objects. It represents a 2D field of ascii characters, exactly like a console terminal. Each cell can have a different character, foreground color, background color, and RGB tint. The PygcurseSurface object also tracks the location of the cursor (where the print() and putchar() functions will output text) and the "input cursor" (the blinking cursor when the user is typing in characters.)

    Each xy position on the surface is called a "cell". A cell can hold one and only one character.

    The PygcurseSurface object contains a pygame.Surface object that it draws to. This pygame.Surface object in turn may have additional Pygame drawing functions called on it before being drawn to the screen with pygame.display.update().

    It should be noted that none of the code in the pygcurse module should at all be considered thread-safe.
    """
    _pygcurseClass = 'PygcurseSurface'

    def __init__(self, width=80, height=25, font=None, fgcolor=DEFAULTFGCOLOR, bgcolor=DEFAULTBGCOLOR, windowsurface=None):
        """
        Creates a new PygcurseSurface object.

        - width and height are the number of characters the the object can display.
        - font is a pygame.Font object used to display the characters. PygcurseSurface can only display one font of one size at a time. The size of the underlying pygame.Surface object is calculated from the font size and width/height accordingly. If None, then a default generic font is used.
        - fgcolor is the foreground color  (ie the color of the text). It is set to either a pygame.Color object, an RGB tuple, an RGBA tuple, or a string that is a key in the colornames dict.
        - bgcolor is the background color of the text.
        - windowSurface is optional. If None, than the user is responsible for calling the update() method on this object and blitting it's surface to the screen, and calling pygame.display.update(). If a pygame.Surface object is specified, then PygcurseSurface object handles updating automatically (unless disabled). (See the update() method for more details.)
        """
        pygame.init()
        self._cursorx = 0
        self._cursory = 0
        self._cursorstack = []
        self._width = width
        self._height = height

        # The self._screen* members are 2D lists that store data for each cell of the PygcurseSurface object. _screenchar[x][y] holds the character at cell x, y. _screenfgcolor and _screenbgcolor  stores the foreground/background color of the cell, etc.
        self._screenchar = [[None] * height for i in range(width)]

        # intialize the foreground and background colors of each cell
        self._fgcolor = fgcolor
        self._bgcolor = bgcolor
        # make sure the values in _screenfgcolor and _screenbgcolor are always pygame.Color objects, and not RGB/RGBA tuples or color strings like 'blue'. Use getpygamecolor().
        self._screenfgcolor = [[None] * height for i in range(width)]
        self._screenbgcolor = [[None] * height for i in range(width)]
        for x in range(width):
            for y in range(height):
                self._screenfgcolor[x][y] = fgcolor
                self._screenbgcolor[x][y] = bgcolor

        # intialize the dirty flag for each cell to True. If the cell's dirty flag is True, then update() needs to update this cell on the self._surfaceobj pygame.Surface object.
        self._screendirty = [[True] * height for i in range(width)]

        # initalize the tinting of each cell to 0. (255 is max, -255 is minimum)
        self._rdelta = 0
        self._gdelta = 0
        self._bdelta = 0
        self._screenRdelta = [[0] * height for i in range(width)]
        self._screenGdelta = [[0] * height for i in range(width)]
        self._screenBdelta = [[0] * height for i in range(width)]

        # The "input cursor" is a separate cursor used by the input() method (and PygcurseInput objects). It tracks where the typed characters should appear. This is separate from the regular cursor which tracks where print() and putchar() should output characters. The mode can be:
        # - None, meaning there is no visible cursor
        # - 'underline', meaning a generic underscore-looking cursor
        # - 'insert', meaning a small box cursor (used when the Insert key has been pressed.)
        # - 'box', which is a box that covers the entire cell, and inverts the foreground and background colors.
        # inputcursorblinking is a boolean variable that tracks if the input cursor should be blinking or stay solid.
        self._inputcursormode = None # either None, 'underline', 'insert' or 'box'
        self.inputcursorblinking = True
        self._inputcursorx = 0
        self._inputcursory = 0

        self._scrollcount = 0 # the number of times writing text to the bottom row has scrolled the screen up a line.

        if font is None:
            self._font = pygame.font.Font(None, 18)
        else:
            self._font = font

        # the width and height in pixels of each cell depends on the font used.
        self._cellwidth, self._cellheight = calcfontsize(self._font) # width and height of each cell in pixels

        self._autoupdate = True
        if windowsurface == _NEW_WINDOW:
            self._windowsurface = pygame.display.set_mode((self._cellwidth * width, self._cellheight * height))
            self._managesdisplay = True
        elif windowsurface == FULLSCREEN:
            self._windowsurface = pygame.display.set_mode((self._cellwidth * width, self._cellheight * height), pygame.FULLSCREEN)
            self._managesdisplay = True
        else:
            self._windowsurface = windowsurface
            self._managesdisplay = False
        self._autodisplayupdate = self._windowsurface is not None
        self._autoblit = self._windowsurface is not None

        self._tabsize = 8 # how many spaces a tab inserts.

        # width and height of the entire surface, in pixels.
        self._pixelwidth = self._width * self._cellwidth
        self._pixelheight = self._height * self._cellheight

        self._surfaceobj = pygame.Surface((self._pixelwidth, self._pixelheight))
        self._surfaceobj = self._surfaceobj.convert_alpha() # TODO - This is needed for erasing, but does this have a performance hit?


    def input(self, prompt='', x=None, y=None, maxlength=None, fgcolor=None, bgcolor=None, promptfgcolor=None, promptbgcolor=None, whitelistchars=None, blacklistchars=None, callbackfn=None, fps=None):
        """
        A pygcurse version of the input() and raw_input() functions. When called, it displays a cursor on the screen and lets the user type in a string. This function blocks until the user presses Enter, and it returns the string the user typed in.

        In fact, this function can be used as a drop-in replacement of Python's input() to convert a stdio text-based Python program to a graphical Pygcurse program. See the PygcurseWindow class for details.

        - prompt is a string that is displayed at the beginning of the input area
        - x and y are cell coordinates for where the beginning of the input area should be. By default it is where the cursor is.
        - maxlength is the maximum number of characters that the user can enter. By default it is 4094 characters if the keyboard input can span multiple lines, or to the end of the current row if the x value is specified.
        - fgcolor and bgcolor are the foreground and background colors of the text typed by the user.
        - promptfgcolor and promptbgcolor are the foreground and background colors of the prompt.
        - whitelistchars is a string of the characters that are allowed to be entered from the keyboard. If None, then all characters (except those in the blacklist, if one is specified) are allowed.
        - blacklistchars is a string of the characters that are prohibited to be entered from the keyboard. If None, then all characters (if they are in the whitelist, if one is specified) are allowed.
        - callbackfn is a function that is called during the input() method's loop. This can be used for any additional code that needs to be run while waiting for the user to enter text.
        - fps specifies how many times per second this function should update the screen (ie, frames per second). If left at None, then input() will simply try to update as fast as possible.
        """
        if fps is not None:
            clock = pygame.time.Clock()

        inputObj = PygcurseInput(self, prompt, x, y, maxlength, fgcolor, bgcolor, promptfgcolor, promptbgcolor, whitelistchars, blacklistchars)
        self.inputcursor = inputObj.startx, inputObj.starty

        while True: # the event loop
            self._inputcursormode = inputObj.insertMode and 'insert' or 'underline'

            for event in pygame.event.get((KEYDOWN, KEYUP, QUIT)): # TODO - handle holding down the keys
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type in (KEYDOWN, KEYUP):
                    inputObj.sendkeyevent(event)
                    if inputObj.done:
                        return ''.join(inputObj.buffer)

            if callbackfn is not None:
                callbackfn()

            inputObj.update()
            self.update()

            if fps is not None:
                clock.tick(fps)

    raw_input = input

    # This code makes my eyes (and IDEs) bleed (and maintenance a nightmare), but it's the only way to have syntactically correct code that is compatible with both Python 2 and Python 3:
    if sys.version.startswith('2.'): # for Python 2 version
        exec(r'''
def pygprint(self, *objs): # PY2
    """
    Displays text to the PygcurseSurface. The parameters work exactly the same as Python's textual print() function. It can take several arguments to display, each separated by the string in the sep parameter. The end parameter string is automatically added to the end of the displayed output.

    - fgcolor, bgcolor are colors for the text displayed by this call to print(). If None, then the PygcurseSurface object's fg and bg colors are used. These parameters only apply to the text printed by this function call, they do not change the PygcurseSurface's fg and bg color settings.

    This function can be used as a drop-in replacement of Python's print() to convert a stdio text-based Python program to a graphical Pygcurse program. See the PygcurseWindow class for details.
    """

    self.write(' '.join([str(x) for x in objs]) + '\n')
''')
    else: # for Python 3 version
        exec(r'''
def pygprint(self, obj='', *objs, sep=' ', end='\n', fgcolor=None, bgcolor=None, x=None, y=None):
    """
    Displays text to the PygcurseSurface. The parameters work exactly the same as Python's textual print() function. It can take several arguments to display, each separated by the string in the sep parameter. The end parameter string is automatically added to the end of the displayed output.

    - fgcolor, bgcolor are colors for the text displayed by this call to print(). If None, then the PygcurseSurface object's fg and bg colors are used. These parameters only apply to the text printed by this function call, they do not change the PygcurseSurface's fg and bg color settings.

    This function can be used as a drop-in replacement of Python's print() to convert a stdio text-based Python program to a graphical Pygcurse program. See the PygcurseWindow class for details.
    """

    writefgcolor = (fgcolor is not None) and getpygamecolor(fgcolor) or self._fgcolor
    writebgcolor = (bgcolor is not None) and getpygamecolor(bgcolor) or self._bgcolor
    if x is not None:
        self.cursorx = x
    if y is not None:
        self.cursory = y

    text = [str(obj)]
    if objs:
        text.append(str(sep) + str(sep).join([str(x) for x in objs]))
    text.append(str(end))

    self.write(''.join(text), writefgcolor, writebgcolor)
#print = pygprint # Actually, this line is a bad idea and only encourages non-compatibility. Leave it commented out.
''')


    def blitto(self, surfaceObj, dest=(0, 0)):
        """
        Copies this object's pygame.Surface to another surface object. (Usually, this surface object is the one returned by pygame.display.set_mode().)

        - surfaceObj is the pygame.Surface object to copy this PygcurseSurface's image to.
        - dest is a tuple of the xy pixel coordinates of the topleft corner where the image should be copied. By default, it is (0,0).
        """
        return surfaceObj.blit(self._surfaceobj, dest)


    def pushcursor(self):
        """Save the current cursor positions to a stack for them. This is useful when you need to modify the cursor position but want to restore it later."""
        self._cursorstack.append( (self._cursorx, self._cursory) )


    def popcursor(self):
        """Restore the cursor position from the cursor stack."""
        x, y = self._cursorstack.pop()
        self._cursorx = x
        self._cursory = y
        return x, y


    def getnthcellfrom(self, x, y, spaces):
        """
        Returns the xy cell coordinates of the nth cell after the position specified by the x and y parameters. This method accounts for wrapping around to the next row if it extends past the right edge of the surface. The returned coordinates can be past the bottom row of the pygcurse surface.
        """
        if x + spaces < self._width:
            return x + spaces, y
        spaces -= x
        y += 1
        return spaces % self._width, y + int(spaces / self._width)


    def update(self):
        """
        Update the encapsulated pygame.Surface object to match the state of this PygcurseSurface object. This needs to be done before the pygame.Surface object is blitted to the screen if you want the most up-to-date state displayed.

        There are three types of updating:
            1) Updating the PygcurseSurface surface object to match the backend data.
                (Enabled by default by setting self._autoupdate == True)
            2) Blitting the PygcurseSurface surface object to the main window
                (Enabled by setting self._windowsurface to the main window AND self._autoblit == True)
            3) Calling pygame.display.update()
                (Enabled by default if _windowsurface is set, self._autoblit == True, AND if _autodisplayupdate == True)
        """

        # TODO - None of this code is optimized yet.

        # "Dirty" means that the cell's state has been altered on the backend and it needs to be redrawn on pygame.Surface object (which will make the cell "clean").
        for x in range(self._width):
            for y in range(self._height):
                if self._screendirty[x][y]: # draw to surfaceobj all the dirty cells.
                    self._screendirty[x][y] = False

                    # modify the fg and bg color if there is a tint
                    cellfgcolor, cellbgcolor = self.getdisplayedcolors(x, y)

                    # fill in the entire background of the cell
                    cellrect = pygame.Rect(self._cellwidth * x, self._cellheight * y, self._cellwidth, self._cellheight)

                    if self._screenchar[x][y] is None:
                        self._surfaceobj.fill(ERASECOLOR, cellrect)
                        continue

                    self._surfaceobj.fill(cellbgcolor, cellrect)

                    if self._screenchar[x][y] == ' ':
                        continue # don't need to render anything if it is just a space character.

                    # render the character and draw it to the surface
                    charsurf = self._font.render(self._screenchar[x][y], 1, cellfgcolor, cellbgcolor)
                    charrect = charsurf.get_rect()
                    charrect.centerx = self._cellwidth * x + int(self._cellwidth / 2)
                    charrect.bottom = self._cellheight * (y + 1) # TODO - not correct, this would put stuff like g, p, q higher than normal.
                    self._surfaceobj.blit(charsurf, charrect)

        self._drawinputcursor()

        # automatically blit to "window surface" pygame.Surface object if it was set.
        if self._windowsurface is not None and self._autoblit:
            self._windowsurface.blit(self._surfaceobj, self._surfaceobj.get_rect())
            if self._autodisplayupdate:
                pygame.display.update()


    def _drawinputcursor(self):
        """Draws the input cursor directly onto the self._surfaceobj Surface object, if self._inputcursormode is not None."""
        if self._inputcursormode is not None and self._inputcursorx is not None and self._inputcursory is not None:
            x = self._inputcursorx # syntactic sugar
            y = self._inputcursory # syntactic sugar

            if not self.inputcursorblinking or int(time.time() * 2) % 2 == 0:
                cellfgcolor, cellbgcolor = self.getdisplayedcolors(x, y)

                if self._inputcursormode == 'underline':
                    # draw a simply underline cursor
                    pygame.draw.rect(self._surfaceobj, cellfgcolor, (self._cellwidth * x + 2, self._cellheight * (y+1) - 3, self._cellwidth - 4, 3))
                elif self._inputcursormode == 'insert':
                    # draw a cursor that takes up about half the cell
                    pygame.draw.rect(self._surfaceobj, cellfgcolor, (self._cellwidth * x + 2, self._cellheight * (y+1) - int(self._cellheight / 2.5), self._cellwidth - 4, int(self._cellheight / 2.5)))
                elif self._inputcursormode == 'box':
                    # draw the reverse the fg & bg colors of the cell (but don't actually modify the backend data)
                    # TODO - the following is copy pasta. Get rid of it when optimizing?
                    cellrect = pygame.Rect(self._cellwidth * x, self._cellheight * y, self._cellwidth, self._cellheight)
                    self._surfaceobj.fill(cellfgcolor, cellrect)
                    charsurf = self._font.render(self._screenchar[x][y], 1, cellbgcolor, cellfgcolor)
                    charrect = charsurf.get_rect()
                    charrect.centerx = self._cellwidth * x + int(self._cellwidth / 2)
                    charrect.bottom = self._cellheight * (y+1) # TODO - not correct, this would put stuff like g, p, q higher than normal.
                    self._surfaceobj.blit(charsurf, charrect)
            else:
                # need to blank out the cursor by simply redrawing the cell
                self._repaintcell(x, y)

    def getdisplayedcolors(self, x, y):
        """Returns the fg and bg colors of the given cell as pygame.Color objects, modified for the tint. If x and y is not on the surface, returns (None, None)"""

        if x < 0 or y < 0 or x >= self._width or y >= self._height:
            return None, None

        fgcolor = (self._screenfgcolor[x][y] is None) and (DEFAULTFGCOLOR) or (self._screenfgcolor[x][y])
        bgcolor = (self._screenbgcolor[x][y] is None) and (DEFAULTBGCOLOR) or (self._screenbgcolor[x][y])

        # NOTE - The ternary trick does work here, because the case where the wrong value of the two is used, both values are the same.
        rdelta = (self._screenRdelta[x][y] is not None) and (self._screenRdelta[x][y]) or (0)
        gdelta = (self._screenGdelta[x][y] is not None) and (self._screenGdelta[x][y]) or (0)
        bdelta = (self._screenBdelta[x][y] is not None) and (self._screenBdelta[x][y]) or (0)


        if rdelta or gdelta or bdelta:
            r, g, b, a = fgcolor.r, fgcolor.g, fgcolor.b, fgcolor.a
            r = getwithinrange(r + rdelta)
            g = getwithinrange(g + gdelta)
            b = getwithinrange(b + bdelta)
            displayedfgcolor = pygame.Color(r, g, b, a)

            r, g, b, a = self._screenbgcolor[x][y].r, self._screenbgcolor[x][y].g, self._screenbgcolor[x][y].b, self._screenbgcolor[x][y].a
            r = getwithinrange(r + rdelta)
            g = getwithinrange(g + gdelta)
            b = getwithinrange(b + bdelta)
            displayedbgcolor = pygame.Color(r, g, b, a)
        else:
            displayedfgcolor = fgcolor
            displayedbgcolor = bgcolor

        return displayedfgcolor, displayedbgcolor


    def _repaintcell(self, x, y):
        """Immediately updates the cell at xy. Use this method when you don't want to update the entire surface."""

        if x < 0 or y < 0 or x >= self._width or y >= self._height:
            return

        # modify the fg and bg color if there is a tint
        cellfgcolor, cellbgcolor = self.getdisplayedcolors(x, y)
        cellrect = pygame.Rect(self._cellwidth * x, self._cellheight * y, self._cellwidth, self._cellheight)
        self._surfaceobj.fill(cellbgcolor, cellrect)
        charsurf = self._font.render(self._screenchar[x][y], 1, cellfgcolor, cellbgcolor)
        charrect = charsurf.get_rect()
        charrect.centerx = self._cellwidth * x + int(self._cellwidth / 2)
        charrect.bottom = self._cellheight * (y+1) # TODO - not correct, this would put stuff like g, p, q higher than normal.
        self._surfaceobj.blit(charsurf, charrect)


    _debugcolorkey = {(255,0,0): 'R',
                      (0,255,0): 'G',
                      (0,0,255): 'B',
                      (0,0,0): 'b',
                      (255, 255, 255): 'w'}


    def _debug(self, returnstr=False, fn=None):
        text = ['+' + ('-' * self._width) + '+\n']
        for y in range(self._height):
            line = ['|']
            for x in range(self._width):
                line.append(fn(x, y))
            line.append('|\n')
            text.append(''.join(line))
        text.append('+' + ('-' * self._width) + '+\n')
        if returnstr:
            return ''.join(text)
        else:
            sys.stdout.write(''.join(text) + '\n')


    def _debugfgFn(self, x, y):
        r, g, b = self._screenfgcolor[x][y].r, self._screenfgcolor[x][y].g, self._screenfgcolor[x][y].b
        if (r, g, b) in PygcurseSurface._debugcolorkey:
            return PygcurseSurface._debugcolorkey[(r, g, b)]
        else:
            return'.'


    def _debugfg(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugfgFn)


    def _debugbgFn(self, x, y):
        r, g, b = self._screenbgcolor[x][y].r, self._screenbgcolor[x][y].g, self._screenbgcolor[x][y].b
        if (r, g, b) in PygcurseSurface._debugcolorkey:
            return PygcurseSurface._debugcolorkey[(r, g, b)]
        else:
            return '.'


    def _debugbg(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugbgFn)


    def _debugcharsFn(self, x, y):
        if self._screenchar[x][y] in (None, '\n', '\t'):
            return '.'
        else:
            return self._screenchar[x][y]


    def _debugchars(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugcharsFn)


    def _debugdirtyFn(self, x, y):
        if self._screendirty[x][y]:
            return 'D'
        else:
            return '.'


    def _debugdirty(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugdirtyFn)


    def gettopleftpixel(self, cellx, celly=None, onscreen=True):
        """Return a tuple of the pixel coordinates of the cell at cellx, celly."""
        if type(cellx) in (tuple, list):
            if type(celly) == bool: # shuffling around the parameters
                isonscreen = celly
            cellx, celly = cellx
        if onscreen and not self.isonscreen(cellx, celly):
            return (None, None)
        return (cellx * self._cellwidth, celly * self._cellheight)


    def gettoppixel(self, celly, onscreen=True):
        """Return the y pixel coordinate of the cells at row celly."""
        if onscreen and (celly < 0 or celly >= self.height):
            return None
        return celly * self._cellheight


    def getleftpixel(self, cellx, onscreen=True):
        """Return the x pixel coordinate of the cells at column cellx."""
        if onscreen and (cellx < 0 or cellx >= self.width):
            return None
        return cellx * self._cellwidth


    def getcoordinatesatpixel(self, pixelx, pixely=None, onscreen=True):
        """
        Given the pixel x and y coordinates relative to the PygCurse screen's origin, return the cell x and y coordinates that it is over. (Useful for finding what cell the mouse cursor is over.)

        Returns (None, None) if the pixel coordinates are not over the screen.
        """
        if type(pixelx) in (tuple, list):
            if type(pixely) == bool: # shuffling around the parameters
                onscreen = pixely
            pixelx, pixely = pixelx

        if onscreen and (pixelx < 0 or pixelx >= self._width * self._cellwidth) or (pixely < 0 or pixely >= self._height * self._cellheight):
            return (None, None)
        return int(pixelx / self._cellwidth), int(pixely / self._cellheight)


    def getcharatpixel(self, pixelx, pixely):
        """Returns the character in the cell located at the pixel coordinates pixelx, pixely."""
        x, y = self.getcoordinatesatpixel(pixelx, pixely)
        if (x, y) == (None, None):
            return (None, None)
        return self._screenchar[x][y]


    def resize(self, newwidth=None, newheight=None, fgcolor=None, bgcolor=None):
        """
        Resize the number of cells wide and tall the surface is. If we are expanding the size of the surface, specify the foreground/background colors of the new cells.
        """

        # TODO - Yipes. This function changes so many things, a lot of testing needs to be done.
        # For example, what happens if the input cursor is now off the screen?
        if newwidth == self._width and newheight == self._height:
            return
        if newwidth is None:
            newwidth = self._width
        if newheight is None:
            newheight = self._height
        if fgcolor is None:
            fgcolor = self._fgcolor
        fgcolor = getpygamecolor(fgcolor)

        if bgcolor is None:
            bgcolor = self._bgcolor
        bgcolor = getpygamecolor(bgcolor)

        # create new _screen* data structures
        newchars = [[None] * newheight for i in range(newwidth)]
        newfg = [[None] * newheight for i in range(newwidth)]
        newbg = [[None] * newheight for i in range(newwidth)]
        newdirty = [[True] * newheight for i in range(newwidth)]
        newRdelta = [[0] * newheight for i in range(newwidth)]
        newGdelta = [[0] * newheight for i in range(newwidth)]
        newBdelta = [[0] * newheight for i in range(newwidth)]
        for x in range(newwidth):
            for y in range(newheight):
                if x >= self._width or y >= self._height:
                    # Create new color objects
                    newfg[x][y] = fgcolor
                    newbg[x][y] = bgcolor
                    newRdelta[x][y] = self._rdelta
                    newGdelta[x][y] = self._gdelta
                    newBdelta[x][y] = self._bdelta
                else:
                    newchars[x][y] = self._screenchar[x][y]
                    newdirty[x][y] = self._screendirty[x][y]
                    # Copy over old color objects
                    newfg[x][y] = self._screenfgcolor[x][y]
                    newbg[x][y] = self._screenbgcolor[x][y]
                    newRdelta[x][y] = self._screenRdelta[x][y]
                    newGdelta[x][y] = self._screenGdelta[x][y]
                    newBdelta[x][y] = self._screenBdelta[x][y]

        # set new dimensions
        self._width = newwidth
        self._height = newheight
        self._pixelwidth = self._width * self._cellwidth
        self._pixelheight = self._height * self._cellheight
        self._cursorx = 0
        self._cursory = 0
        newsurf = pygame.Surface((self._pixelwidth, self._pixelheight))
        newsurf.blit(self._surfaceobj, (0, 0))
        self._surfaceobj = newsurf

        self._screenchar = newchars
        self._screenfgcolor = newfg
        self._screenbgcolor = newbg
        self._screendirty = newdirty

        if self._managesdisplay:
            # resize the pygame window itself
            self._windowsurface = pygame.display.set_mode((self._pixelwidth, self._pixelheight))
            self.update()
        elif self._autoupdate:
            self.update()


    def setfgcolor(self, fgcolor, region=None):
        """
        Sets the foreground color of a region of cells on this surface.

        - fgcolor is the color to set the foreground to.
        """
        if region == None:
            self._fgcolor = fgcolor
            return

        regionx, regiony, regionwidth, regionheight = self.getregion(region)
        if (regionx, regiony, regionwidth, regionheight) == (None, None, None, None):
            return

        for ix in range(regionx, regionx + regionwidth):
            for iy in range(regiony, regiony + regionheight):
                self._screenfgcolor[ix][iy] = fgcolor
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def setbgcolor(self, bgcolor, region=None):
        """
        Sets the background color of a region of cells on this surface.

        - bgcolor is the color to set the background to.
        """
        if region == None:
            self._fgcolor = fgcolor
            return

        regionx, regiony, regionwidth, regionheight = self.getregion(region)
        if (regionx, regiony, regionwidth, regionheight) == (None, None, None, None):
            return

        for ix in range(regionx, regionx + regionwidth):
            for iy in range(regiony, regiony + regionheight):
                self._screenbgcolor[ix][iy] = bgcolor
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def reversecolors(self, region=None):
        """
        Reverse the foreground/background colors of a region of cells on this surface with each other.
        """
        regionx, regiony, regionwidth, regionheight = self.getregion(region)
        if (regionx, regiony, regionwidth, regionheight) == (None, None, None, None):
            return

        for ix in range(regionx, regionx + regionwidth):
            for iy in range(regiony, regiony + regionheight):
                self._screenfgcolor[ix][iy], self._screenbgcolor[ix][iy] = self._screenbgcolor[ix][iy], self._screenfgcolor[ix][iy]
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def _invertfg(self, x, y):
        # NOTE - This function does not set the dirty flag.
        fgcolor = self._screenfgcolor[x][y]
        invR, invG, invB = 255 - fgcolor.r, 255 - fgcolor.g, 255 - fgcolor.b
        self._screenfgcolor[x][y] = pygame.Color(invR, invG, invB, fgcolor.a)


    def _invertbg(self, x, y):
        # NOTE - This function does not set the dirty flag.
        bgcolor = self._screenbgcolor[x][y]
        invR, invG, invB = 255 - bgcolor.r, 255 - bgcolor.g, 255 - bgcolor.b
        self._screenbgcolor[x][y] = pygame.Color(invR, invG, invB, bgcolor.a)


    def invertcolors(self, region=None):
        """
        Invert the colors of a region of cells on this surface. (For example, black and white are inverse of each other, as are blue and yellow.)
        """
        regionx, regiony, regionwidth, regionheight = self.getregion(region)
        if (regionx, regiony, regionwidth, regionheight) == (None, None, None, None):
            return

        for ix in range(regionx, regionx + regionwidth):
            for iy in range(regiony, regiony + regionheight):
                self._invertfg(ix, iy)
                self._invertbg(ix, iy)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def invertfgcolor(self, region=None):
        """
        Invert the foreground color of a region of cells on this surface. (For example, black and white are inverse of each other, as are blue and yellow.)
        """
        regionx, regiony, regionwidth, regionheight = self.getregion(region)
        if (regionx, regiony, regionwidth, regionheight) == (None, None, None, None):
            return

        for ix in range(regionx, regionx + regionwidth):
            for iy in range(regiony, regiony + regionheight):
                self._invertfg(ix, iy)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def invertbgcolor(self, region=None):
        """
        Invert the background color of a region of cells on this surface. (For example, black and white are inverse of each other, as are blue and yellow.)
        """
        regionx, regiony, regionwidth, regionheight = self.getregion(region)
        if (regionx, regiony, regionwidth, regionheight) == (None, None, None, None):
            return

        for ix in range(regionx, regionx + regionwidth):
            for iy in range(regiony, regiony + regionheight):
                self._invertbg(ix, iy)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def paste(self, srcregion=None, dstsurf=None, dstregion=None, pastechars=True, pastefgcolor=True, pastebgcolor=True, pasteredtint=True, pastegreentint=True, pastebluetint=True):
        srcx, srcy, srcwidth, srcheight = self.getregion(srcregion)
        if (srcx, srcy, srcwidth, srcheight) == (None, None, None, None):
            return

        if dstsurf is None:
            # Create a new PygcurseSurface to paste to.
            dstsurf = PygcurseSurface(srcwidth, srcheight, font=self._font, fgcolor=self._fgcolor, bgcolor=self._bgcolor)
        elif dstsurf._pygcurseClass not in ('PygcurseSurface', 'PygcurseWindow'): # TODO - is this the right way to do this?
            return

        dstx, dsty, dstwidth, dstheight = dstsurf.getregion(dstregion)
        if (dstx, dsty, dstwidth, dstheight) == (None, None, None, None):
            return

        if self == dstsurf and regionsoverlap((srcx, srcy, srcwidth, srcheight), (dstx, dsty, dstwidth, dstheight)):
            # Since we are trying to copy/paste over the same region, in order to prevent any weird side effects, paste to a new surface object first
            tempsurf = self.paste((srcx, srcy, srcwidth, srcheight))
            tempsurf.paste(None, self, (dstx, dsty, dstwidth, dstheight))
            return

        for ix in range(srcx, srcx + srcwidth):
            for iy in range(srcy, srcy + srcheight):
                finx = dstx + (ix - srcx)
                finy = dsty + (iy - srcy)

                if not dstsurf.isonscreen(finx, finy) or ix - srcx >= dstwidth or iy - srcy >= dstheight:
                    continue

                if pastechars and self._screenchar[ix][iy] is not None:
                    dstsurf._screenchar[finx][finy] = self._screenchar[ix][iy]
                if pastefgcolor and self._screenfgcolor[ix][iy] is not None:
                    dstsurf._screenfgcolor[finx][finy] = self._screenfgcolor[ix][iy]
                if pastebgcolor and self._screenbgcolor[ix][iy] is not None:
                    dstsurf._screenbgcolor[finx][finy] = self._screenbgcolor[ix][iy]
                if pasteredtint and self._screenRdelta[ix][iy] is not None:
                    dstsurf._screenRdelta[finx][finy] = self._screenRdelta[ix][iy]
                if pastegreentint and self._screenGdelta[ix][iy] is not None:
                    dstsurf._screenGdelta[finx][finy] = self._screenGdelta[ix][iy]
                if pastebluetint and self._screenBdelta[ix][iy] is not None:
                    dstsurf._screenBdelta[finx][finy] = self._screenBdelta[ix][iy]
                dstsurf._screendirty[finx][finy] = True

        if dstsurf._autoupdate:
            dstsurf.update()


    def pastechars(self, srcregion=None, dstsurf=None, dstregion=None):
        return self.paste(srcregion, dstsurf, dstregion, True, False, False, False, False, False)


    def pastecolor(self, srcregion=None, dstsurf=None, dstregion=None, pastefgcolor=True, pastebgcolor=True):
        return self.paste(srcregion, dstsurf, dstregion, False, pastefgcolor, pastebgcolor, False, False, False)


    def pastetint(self, srcregion=None, dstsurf=None, dstregion=None, pasteredtint=True, pastegreentint=True, pastebluetint=True):
        return self.paste(srcregion, dstsurf, dstregion, False, False, False, pasteredtint, pastegreentint, pastebluetint)


    def lighten(self, amount=51, region=None):
        """
        Adds a highlighting tint to the region specified.

        - amount is the amount to lighten by. When the lightening is at 255, the cell will be completely white. A negative amount argument has the same effect as calling darken().
        """

        # NOTE - I chose 51 for the default amount because 51 is a fifth of 255.
        self.tint(amount, amount, amount, region)


    def darken(self, amount=51, region=None):
        """
        Adds a darkening tint to the region specified.

        - amount is the amount to darken by. When the lightening is at -255, the cell will be completely black. A negative amount argument has the same effect as calling lighten().
        """
        self.tint(-amount, -amount, -amount, region)


    def addshadow(self, amount=51, region=None, offset=None, direction=None, xoffset=1, yoffset=1):
        """
        Creates a shadow by darkening the cells around a rectangular region. For example, if the O characters represent the rectangular region, then the S characters represent the darkend cells to form the shadow:

          OOOO
          OOOOS
          OOOOS
          OOOOS
           SSSS

        - amount is the amount to darken the cells. 255 will make the cells completely black.
        - offset is how many cells the shadow is offset from the rectangular region. The example above has an offset of 1. An offset of 0 places no shadow, since it would be directly underneath the rectangular region. Specifying the offset parameter overrides the xoffset and yoffset parameters.
        - direction is used along with offset. This controls which direction the shadow is cast from the rectangular region. Specify one of the directional constants for this parameter (i.e. NORTH, NORTHWEST, EAST, SOUTHEAST, etc.) This parameter is ignored if offset is not specified.
        - xoffset, yoffset are ways to specify the offset directly. Positive values send the shadow to the right and down, negative values to the left and up.
        """
        x, y, width, height = self.getregion(region, False)
        if (x, y, width, height) == (None, None, None, None):
            return

        if offset is not None:
            xoffset = offset
            yoffset = offset

            if direction is not None:
                if direction in (NORTH, NORTHWEST, NORTHEAST):
                    yoffset = -yoffset
                if direction in (WEST, NORTHWEST, SOUTHWEST):
                    xoffset = -xoffset
                if direction in (NORTH, SOUTH):
                    xoffset = 0
                if direction in (WEST, EAST):
                    yoffset = 0

        # north shadow
        if yoffset < 0 and (-width < xoffset < width):
            self.darken(amount, (x + getwithinrange(xoffset, 0, width),
                                 y + yoffset,
                                 width-abs(xoffset),
                                 min(abs(yoffset), height)))

        # south shadow
        if yoffset > 0 and (-width < xoffset < width):
            self.darken(amount, (x + getwithinrange(xoffset, 0, width),
                            y+max(yoffset, height),
                            width-abs(xoffset),
                            min(abs(yoffset), height)))

        # west shadow
        if xoffset < 0 and (-height < yoffset < height):
            self.darken(amount, (x + xoffset,
                                 y + getwithinrange(yoffset, 0, height),
                                 getwithinrange(abs(xoffset), 0, width),
                                 height - abs(yoffset)))

        # east shadow
        if xoffset > 0 and (-height < yoffset < height):
            self.darken(amount, (x + max(xoffset, width),
                                 y + getwithinrange(yoffset, 0, height),
                                 min(abs(xoffset), width),
                                 height - abs(yoffset)))

        # northwest shadow
        if xoffset < 0 and yoffset < 0:
            self.darken(amount, (x + xoffset,
                                 y + yoffset,
                                 min(abs(xoffset), width),
                                 min(abs(yoffset), height)))

        # northeast shadow
        if xoffset > 0 and yoffset < 0:
            self.darken(amount, (x + getwithinrange(xoffset, width, xoffset),
                                 y + yoffset,
                                 min(abs(xoffset), width),
                                 min(abs(yoffset), height)))

        # southwest shadow
        if xoffset < 0 and yoffset > 0:
            self.darken(amount, (x + xoffset,
                                 y + getwithinrange(yoffset, height, yoffset),
                                 min(abs(xoffset), width),
                                 min(abs(yoffset), height)))

        # southeast shadow
        if xoffset > 0 and yoffset > 0:
            self.darken(amount, (x + getwithinrange(xoffset, width, xoffset),
                                 y + getwithinrange(yoffset, height, yoffset),
                                 getwithinrange(abs(xoffset), 0, width),
                                 getwithinrange(abs(yoffset), 0, height)))


    def tint(self, r=0, g=0, b=0, region=None):
        """
        Adjust the red, green, and blue tint of the cells in the specified region.

        - r, g, b are the amount of tint to add/subtract. A positive integer adds tint, negative removes it. At 255, there is maximum tint of that color. At -255 there will never be any amount of that color in the cell.
        """
        x, y, width, height = self.getregion(region)
        if (x, y, width, height) == (None, None, None, None):
            return

        for ix in range(x, x + width):
            for iy in range(y, y + height):
                self._screenRdelta[ix][iy] = getwithinrange(r + self._screenRdelta[ix][iy], min=-255)
                self._screenGdelta[ix][iy] = getwithinrange(g + self._screenGdelta[ix][iy], min=-255)
                self._screenBdelta[ix][iy] = getwithinrange(b + self._screenBdelta[ix][iy], min=-255)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()

    def setbrightness(self, amount=0, region=None):
        """
        Set the brightness level of a region of cells.

        - amount is the amount of brightness. 0 means a neutral amount, and the cells will be displayed as their true colors. 255 is maximum brightness, which turns all cells completely white, and -255 is maximum darkness, turning all cells completely black.
        """
        self.settint(amount, amount, amount, region)


    def settint(self, r=0, g=0, b=0, region=None):
        """
        Set the brightness level of a region of cells. The r, g, and b parameters are the amount of red, green, and blue tint used for the region of cells. 0 is no tint at all, whereas 255 is maximum tint and -255 is maximum removal of that color.
        """
        x, y, width, height = self.getregion(region)
        if (x, y, width, height) == (None, None, None, None):
            return

        for ix in range(x, x + width):
            for iy in range(y, y + height):
                self._screenRdelta[ix][iy] = getwithinrange(r, min=-255)
                self._screenGdelta[ix][iy] = getwithinrange(g, min=-255)
                self._screenBdelta[ix][iy] = getwithinrange(b, min=-255)
                self._screendirty[ix][iy] = True

        if self._autoupdate:
            self.update()

    def getchar(self, x, y):
        """Returns the character at cell x, y."""
        if x < 0 or y < 0 or x >= self._width or y >= self._height:
            return None
        return self._screenchar[x][y]


    def getchars(self, region=None, gapChar=' '):
        """
        Returns the a list of the characters in the specified region. Each item in the list is a string of the rows of characters.

        - gapChar is used whenever None is found as a cell. By default this is set to a space character. If gapChar is set to None, then the None characters in cells will be ignored (this could cause alignment issues in between the lines.)
        """
        x, y, width, height = self.getregion(region)
        if (x, y, width, height) == (None, None, None, None):
            return

        lines = []
        for iy in range(y, y + height):
            line = []
            for ix in range(x, x + width):
                if self._screenchar[ix][iy] is None and gapChar is not None:
                    line.append(gapChar)
                else:
                    line.append(self._screenchar[ix][iy])
            lines.append(''.join(line))
        return lines


    def putchar(self, char, x=None, y=None, fgcolor=None, bgcolor=None):
        """
        Print a single character to the coordinates on the surface. This function does not move the cursor.
        """
        if type(char) != str:
            raise Exception('Argument 1 must be str, not %s' % (str(type(char))))

        if char == '':
            return

        if x is None:
            x = self._cursorx
        if y is None:
            y = self._cursory

        if x < 0 or y < 0 or x >= self._width or y >= self._height:
            return None

        if fgcolor is not None:
            self._screenfgcolor[x][y] = getpygamecolor(fgcolor)
        if bgcolor is not None:
            self._screenbgcolor[x][y] = getpygamecolor(bgcolor)

        self._screenchar[x][y] = char[0]
        self._screendirty[x][y] = True

        if self._autoupdate:
            self.update()

        return char


    def putchars(self, chars, x=None, y=None, fgcolor=None, bgcolor=None, indent=False):
        # doc - does not modify the cursor. That's how putchars is different from print() or write()
        # doc - also, putchars does wrap but doesn't cause scrolls. (if you want a single line, just put putchar() calls in a loop)
        if type(chars) != str:
            raise Exception('Argument 1 must be str, not %s' % (str(type(chars))))

        if x is None:
            x = self._cursorx
        if y is None:
            y = self._cursory

        if type(chars) in (list, tuple):
            # convert a list/tuple of strings to a single string (this is so that putchars() can work with the return value of getchars())
            chars = '\n'.join(chars)

        if fgcolor is not None:
            fgcolor = getpygamecolor(fgcolor)
        if bgcolor is not None:
            bgcolor = getpygamecolor(bgcolor)

        tempcurx = x
        tempcury = y
        for i in range(len(chars)):
            if tempcurx >= self._width or chars[i] in ('\n', '\r'): # TODO - wait, this isn't right. We should be ignoring one of these newlines.
                tempcurx = indent and x or 0
                tempcury += 1
            if tempcury >= self._height: # putchars() does not cause a scroll.
                break

            self._screenchar[tempcurx][tempcury] = chars[i]
            self._screendirty[tempcurx][tempcury] = True
            if fgcolor is not None:
                self._screenfgcolor[tempcurx][tempcury] = fgcolor
            if bgcolor is not None:
                self._screenbgcolor[tempcurx][tempcury] = bgcolor
            tempcurx += 1

        if self._autoupdate:
            self.update()


    def setscreencolors(self, fgcolor=None, bgcolor=None, clear=False):
        """
        Sets the foreground and/or background color of the entire screen to the ones specified in the fgcolor and bgcolor parameters. Also sets the PygcurseSurface's default foreground and/or background colors. The brightness of all cells is reset back to 0. This is a good "clear screen" function to use.

        fgcolor - foreground color. If None, then the foreground color isn't changed.
        bgcolor - background color. If None, then the background color isn't changed.
        clear - If set to True, then all the characters on the surface will be erased so that the screen is just a solid fill of the background color. This parameter is False by default.
        """
        if fgcolor is not None:
            self.fgcolor = getpygamecolor(fgcolor)
        if bgcolor is not None:
            self.bgcolor = getpygamecolor(bgcolor)
        char = clear and ' ' or None
        self.fill(char, fgcolor, bgcolor)
        self.setbrightness()


    def erase(self, region=None):
        self.fill(None, None, None, region)


    def paint(self, x, y, bgcolor=None):
        self.putchar(' ', x, y, None, bgcolor)


    def fill(self, char=' ', fgcolor=None, bgcolor=None, region=None):
        x, y, width, height = self.getregion(region)
        if (x, y, width, height) == (None, None, None, None):
            return

        fgcolor = (fgcolor is not None) and (getpygamecolor(fgcolor)) or (self._fgcolor)
        bgcolor = (bgcolor is not None) and (getpygamecolor(bgcolor)) or (self._bgcolor)

        for ix in range(x, x + width):
            for iy in range(y, y + height):
                if char is not None:
                    self._screenchar[ix][iy] = char
                if fgcolor is not None:
                    self._screenfgcolor[ix][iy] = fgcolor
                if bgcolor is not None:
                    self._screenbgcolor[ix][iy] = bgcolor
                self._screendirty[ix][iy] = True

        if self._autoupdate:
            self.update()


    def _scroll(self):
        """Scroll the content of the entire screen up one row. This is done when characters are printed to the screen that go past the end of the last row."""
        for x in range(self._width):
            for y in range(self._height - 1):
                self._screenchar[x][y] = self._screenchar[x][y+1]
                self._screenfgcolor[x][y] = self._screenfgcolor[x][y+1]
                self._screenbgcolor[x][y] = self._screenbgcolor[x][y+1]
                self._screenRdelta[x][y] = self._screenRdelta[x][y+1]
                self._screenGdelta[x][y] = self._screenGdelta[x][y+1]
                self._screenBdelta[x][y] = self._screenBdelta[x][y+1]
            self._screenchar[x][self._height-1] = ' ' # bottom row is blanked
            self._screenfgcolor[x][self._height-1] = self._fgcolor
            self._screenbgcolor[x][self._height-1] = self._bgcolor
            self._screenRdelta[x][self._height-1] = self._rdelta
            self._screenGdelta[x][self._height-1] = self._gdelta
            self._screenBdelta[x][self._height-1] = self._bdelta
        self._screendirty = [[True] * self._height for i in range(self._width)]
        self._scrollcount += 1


    def getregion(self, region=None, truncate=True):
        if region is None:
            return (0, 0, self._width, self._height)
        elif type(region) in (tuple, list) and len(region) == 4:
            x, y, width, height = region
            if x == y == width == height == None:
                return (0, 0, self._width, self._height)
            elif width == height == None:
                width = self._width - x
                height = self._height - y
        elif str(type(region)) in ("<class 'pygame.Color'>", "<type 'pygame.Color'>"):
            x, y, width, heigh = region.x, region.y, region.width, region.height

        if width < 1 or height < 1:
            return None, None, None, None

        if not truncate:
            return x, y, width, height

        if x + width < 0 or y + height < 0 or x >= self._width or y >= self._height:
            # If the region is entirely outside the boundaries, then return None
            return None, None, None, None

        # Truncate width or height if they extend past the boundaries
        if x + width > self._width:
            width -= (x + width) - self._width
        if y + height > self._height:
            height -= (y + height) - self._height
        if x < 0:
            width += x # subtracts, since x is negative
            x = 0
        if y < 0:
            height += y # subtracts, since y is negative
            y = 0

        return x, y, width, height


    def isonscreen(self, x, y):
        """Returns True if the given xy cell coordinates are on the PygcurseSurface object, otherwise False."""
        return x >= 0 and y >= 0 and x < self.width and y < self.height


    def writekeyevent(self, keyevent, x=None, y=None, fgcolor=None, bgcolor=None):
        """
        Writes a character to the PygcurseSurface that the Pygame key event object represents. A foreground and background color can optionally be supplied. An xy cell coordinate can also be supplied, but the current cursor position is used by default.

        - keyevent is the KEYDOWN or KEYUP event that pygame.event.get() returns. This event object contains the key information.
        """
        if x is None or y is None:
            x = self._cursorx
            y = self._cursory
        if not self.isonscreen(x, y):
            return
        char = interpretkeyevent(keyevent)
        if char is not None:
            self.putchar(char, x=x, y=y, fgcolor=fgcolor, bgcolor=bgcolor)


    # File-like Object methods:
    def write(self, text, x=None, y=None, fgcolor=None, bgcolor=None):
        if x is not None:
            self.cursorx = x
        if y is not None:
            self.cursory = y

        fgcolor = (fgcolor is None) and (self._fgcolor) or (getpygamecolor(fgcolor))
        bgcolor = (bgcolor is None) and (self._bgcolor) or (getpygamecolor(bgcolor))

        # TODO - we can calculate in advance what how many scrolls to do.


        # replace tabs with appropriate number of spaces
        i = 0
        tempcursorx = self._cursorx - 1
        while i < len(text):
            if text[i] == '\n':
                tempcursorx = 0
            elif text[i] == '\t':
                numspaces = self._tabsize - ((i+1) + tempcursorx % self._tabsize)
                if tempcursorx + numspaces >= self._width:
                    # tabbed past the edge, just go to first
                    # TODO - this doesn't work at all.
                    text = text[:i] + (' ' * (self._width - tempcursorx + 1)) + text[i+1:]
                    tempcursorx += (self._width - tempcursorx + 1)
                else:
                    text = text[:i] + (' ' * numspaces) + text[i+1:]
                    tempcursorx += numspaces
            else:
                tempcursorx += 1

            if tempcursorx >= self._width:
                tempcursorx = 0
            i += 1

        """
        # create a cache of surface objects for each letter in text
        letterSurfs = {}
        for letter in text:
            if ord(letter) in range(33, 127) and letter not in letterSurfs:
                letterSurfs[letter] = self._font.render(letter, 1, fgcolor, bgcolor)
                #letterSurfs[letter] = letterSurfs[letter].convert_alpha() # TODO - wait a sec, I don't think pygame lets fonts have transparent backgrounds.
            elif letter == ' ':
                continue
            elif letter not in letterSurfs and '?' not in letterSurfs:
                letterSurfs['?'] = self._font.render('?', 1, fgcolor, bgcolor)
                #letterSurfs['?'] = letterSurfs['?'].convert_alpha()
        """

        for i in range(len(text)):
            if text[i] in ('\n', '\r'): # TODO - wait, this isn't right. We should be ignoring one of these newlines. Otherwise \r\n shows up as two newlines.
                self._cursory += 1
                self._cursorx = 0
            else:
                # set the backend data structures that track the screen state
                self._screenchar[self._cursorx][self._cursory] = text[i]
                self._screenfgcolor[self._cursorx][self._cursory] = fgcolor
                self._screenbgcolor[self._cursorx][self._cursory] = bgcolor
                self._screendirty[self._cursorx][self._cursory] = True

                """
                r = pygame.Rect(self._cellwidth * self._cursorx, self._cellheight * self._cursory, self._cellwidth, self._cellheight)
                self._surfaceobj.fill(bgcolor, r)
                charsurf = letterSurfs[text[i]]
                charrect = charsurf.get_rect()
                charrect.centerx = self._cellwidth * self._cursorx + int(self._cellwidth / 2)
                charrect.bottom = self._cellheight * (self._cursory+1)
                self._surfaceobj.blit(charsurf, charrect)
                self._screendirty[self._cursorx][self._cursory] = False
                """

                # Move cursor over (and to next line if it moves past the right edge)
                self._cursorx += 1
                if self._cursorx >= self._width:
                    self._cursorx = 0
                    self._cursory += 1
            if self._cursory >= self._height:
                # scroll up a line if we try to print on the line after the last one
                self._scroll()
                self._cursory = self._height - 1

        if self._autoupdate:
            self.update()


    def read(self): # TODO - this isn't right.
        return '\n'.join(self.getchars())


    # Properties:
    def _propgetcursorx(self):
        return self._cursorx


    def _propsetcursorx(self, value):
        """
        Set the cursor's x coordinate.
        
        value - The new x coordinate. A negative value can be used to specify 
        the x coordinate in terms of its relative distance to the right border 
        of the surface. No operation will be performed if value is greater than 
        or equal to the width of the surface.
        """
        x = int(value)
        if x >= self._width or x <= -self._width:
            return # no-op

        if x < 0:
            x = self._width + x

        self._cursorx = x


    def _propgetcursory(self):
        return self._cursory


    def _propsetcursory(self, value):
        """
        Set the cursor's y coordinate.
        
        value - The new y coordinate. A negative value can be used to specify 
        the y coordinate in terms of its relative distance to the bottom border 
        of the surface. No operation will be performed if value is greater than 
        or equal to the height of the surface.
        """
        y = int(value)
        if y >= self._height or y <= -self._height:
            return # no-op

        if y < 0:
            y = self._height + y

        self._cursory = y


    def _propgetcursor(self):
        return (self._cursorx, self._cursory)


    def _propsetcursor(self, value):
        x = int(value[0])
        y = int(value[1])
        if not self.isonscreen(x, y):
            return
        self._cursorx = x
        self._cursory = y


    def _propgetinputcursor(self):
        return (self._inputcursorx, self._inputcursory)


    def _propsetinputcursor(self, value):
        x = int(value[0])
        y = int(value[1])
        if not self.isonscreen(x, y):
            return
        if x != self._inputcursorx or y != self._inputcursory:
            self._repaintcell(self._inputcursorx, self._inputcursory) # blank out the old cursor position
        self._inputcursorx = x
        self._inputcursory = y


    def _propgetinputcursormode(self):
        return self._inputcursormode


    def _propsetinputcursormode(self, value):
        if value in (None, 'underline', 'insert', 'box'):
            self._inputcursormode = value
        elif value is False:
            self._inputcursormode = None
        elif value is True:
            self._inputcursormode = 'underline'
        else:
            self._inputcursormode = None


    def _propgetfont(self):
        return self._font


    def _propsetfont(self, value):
        self._font = value # TODO - a lot of this code is copy/paste
        self._cellwidth, self._cellheight = calcfontsize(self._font)
        if self._managesdisplay and self._fullscreen:
            self._windowsurface = pygame.display.set_mode((self._cellwidth * self.width, self._cellheight * self.height), pygame.FULLSCREEN)
        elif self._managesdisplay:
            self._windowsurface = pygame.display.set_mode((self._cellwidth * self.width, self._cellheight * self.height))
        self._pixelwidth = self._width * self._cellwidth
        self._pixelheight = self._height * self._cellheight
        self._surfaceobj = pygame.Surface((self._pixelwidth, self._pixelheight))
        self._surfaceobj = self._surfaceobj.convert_alpha() # TODO - This is needed for erasing, but does this have a performance hit?
        self._screendirty = [[True] * self._height for i in range(self._width)]

        if self._autoupdate:
            self.update()


    def _propgetfgcolor(self):
        return self._fgcolor


    def _propsetfgcolor(self, value):
        self._fgcolor = getpygamecolor(value)


    def _propgetbgcolor(self):
        return self._bgcolor


    def _propsetbgcolor(self, value):
        self._bgcolor = getpygamecolor(value)


    def _propgetcolors(self):
        return (self._fgcolor, self._bgcolor)


    def _propsetcolors(self, value):
        self._fgcolor = getpygamecolor(value[0])
        self._bgcolor = getpygamecolor(value[1])


    def _propgetautoupdate(self):
        return self._autoupdate


    def _propsetautoupdate(self, value):
        self._autoupdate = bool(value)


    def _propgetautoblit(self):
        return self._autoblit


    def _propsetautoblit(self, value):
        self._autoblit = bool(value)


    def _propgetautodisplayupdate(self):
        return self._autodisplayupdate


    def _propsetautodisplayupdate(self, value):
        if self._windowsurface is not None:
            self._autodisplayupdate = bool(value)
        elif bool(value):
            # TODO - this should be a raised exception, not an assertion.
            assert False, 'Window Surface object must be set to a surface before autodisplayupdate can be enabled.'


    def _propgetheight(self):
        return self._height


    def _propsetheight(self, value):
        newheight = int(value)
        if newheight != self._height:
            self.resize(newheight=newheight)


    def _propgetwidth(self):
        return self._width


    def _propsetwidth(self, value):
        newwidth = int(value)
        if newwidth != self._width:
            self.resize(newwidth=newwidth)


    def _propgetsize(self):
        return (self._width, self._height)


    def _propsetsize(self, value):
        newwidth = int(value[0])
        newheight = int(value[1])
        if newwidth != self._width or newheight != self._height:
            self.resize(newwidth, newheight)


    def _propgetpixelwidth(self):
        return self._width * self._cellwidth


    def _propsetpixelwidth(self, value):
        newwidth = int(int(value) / self._cellwidth)
        if newwidth != self._width:
            self.resize(newwidth=newwidth)


    def _propgetpixelheight(self):
        return self._height * self._cellheight


    def _propsetpixelheight(self, value):
        newheight = int(int(value) / self._cellheight)
        if newheight != self._height:
            self.resize(newheight=newheight)


    def _propgetpixelsize(self):
        return (self._width * self._cellwidth, self._height * self._cellheight)


    def _propsetpixelsize(self, value):
        newwidth = int(int(value) / self._cellwidth)
        newheight = int(int(value) / self._cellheight)
        if newwidth != self._width or newheight != self._height:
            self.resize(newwidth, newheight)


    def _propgetcellwidth(self):
        return self._cellwidth


    def _propgetcellheight(self):
        return self._cellheight


    def _propgetcellsize(self):
        return (self._cellwidth, self._cellheight)


    def _propgetsurface(self):
        return self._surfaceobj


    def _propgetleft(self):
        return 0


    def _propgetright(self):
        return self._width - 1 # note: this behavior is different from pygame Rect objects, which do not have the -1.


    def _propgettop(self):
        return 0


    def _propgetbottom(self):
        return self._height - 1 # note: this behavior is different from pygame Rect objects, which do not have the -1.


    def _propgetcenterx(self):
        return int(self._width / 2)


    def _propgetcentery(self):
        return int(self._height / 2)


    def _propgetcenter(self):
        return (int(self._width / 2), int(self._height / 2))


    def _propgettopleft(self):
        return (0, 0)


    def _propgettopright(self):
        return (self._width - 1, 0)


    def _propgetbottomleft(self):
        return (0, self._height - 1)


    def _propgetbottomright(self):
        return (self._width - 1, self._height - 1)


    def _propgetmidleft(self):
        return (0, int(self._height / 2))


    def _propgetmidright(self):
        return (self._width - 1, int(self._height / 2))


    def _propgetmidtop(self):
        return (int(self._width / 2), 0)


    def _propgetmidbottom(self):
        return (int(self._width / 2), self._height - 1)


    def _propgetrect(self):
        return pygame.Rect(0, 0, self._width, self._height)


    def _propgetpixelrect(self):
        return pygame.Rect(0, 0, self._width * self._cellwidth, self._height * self._cellheight)


    def _propgettabsize(self):
        return self._fgcolor


    def _propsettabsize(self, value):
        self._tabsize = max(1, int(value))


    cursorx           = property(_propgetcursorx, _propsetcursorx)
    cursory           = property(_propgetcursory, _propsetcursory)
    cursor            = property(_propgetcursor, _propsetcursor)
    inputcursor       = property(_propgetinputcursor, _propsetinputcursor)
    inputcursormode   = property(_propgetinputcursormode, _propsetinputcursormode)
    fgcolor           = property(_propgetfgcolor, _propsetfgcolor)
    bgcolor           = property(_propgetbgcolor, _propsetbgcolor)
    colors            = property(_propgetcolors, _propsetcolors)
    autoupdate        = property(_propgetautoupdate, _propsetautoupdate)
    autoblit          = property(_propgetautoblit, _propsetautoblit)
    autodisplayupdate = property(_propgetautodisplayupdate, _propsetautodisplayupdate)
    width             = property(_propgetwidth, _propsetwidth)
    height            = property(_propgetheight, _propsetheight)
    size              = property(_propgetsize, _propsetsize)
    pixelwidth        = property(_propgetpixelwidth, _propsetpixelwidth)
    pixelheight       = property(_propgetpixelheight, _propsetpixelheight)
    pixelsize         = property(_propgetpixelsize, _propsetpixelsize)
    font              = property(_propgetfont, _propsetfont)
    cellwidth         = property(_propgetcellwidth, None) # Set func will be in VER2
    cellheight        = property(_propgetcellheight, None) # Set func will be in VER2
    cellsize          = property(_propgetcellsize, None) # Set func will be in VER2
    surface           = property(_propgetsurface, None)
    tabsize           = property(_propgettabsize, _propsettabsize)

    left        = property(_propgetleft, None)
    right       = property(_propgetright, None) # TODO - need set functions for properties that cause a resize
    top         = property(_propgettop, None)
    bottom      = property(_propgetbottom, None)
    centerx     = property(_propgetcenterx, None)
    centery     = property(_propgetcentery, None)
    center      = property(_propgetcenter, None)
    topleft     = property(_propgettopleft, None)
    topright    = property(_propgettopright, None)
    bottomleft  = property(_propgetbottomleft, None)
    bottomright = property(_propgetbottomright, None)
    midleft     = property(_propgetmidleft, None)
    midright    = property(_propgetmidright, None)
    midtop      = property(_propgetmidtop, None)
    midbottom   = property(_propgetmidbottom, None)
    rect        = property(_propgetrect, None)
    pixelrect   = property(_propgetpixelrect, None)

    """
    TODO - ideas for new properties (are these worth it?)
    leftcolumn (0), rightcolumn (which is width - 1)
    toptrow (0), bottomrow (which is height - 1)

    setting rightcolumn and bottom row will call resize, just like setting the right and bottom properties.
    """

    # Primitive Drawing Functions
    def drawline(self, start_pos, end_pos, char=' ', fgcolor=None, bgcolor=None):
        if fgcolor is None:
            fgcolor = self._fgcolor
        else:
            fgcolor = getpygamecolor(fgcolor)

        if bgcolor is None:
            bgcolor = self._bgcolor
        else:
            bgcolor = getpygamecolor(bgcolor)
        # brensenham line algorithm
        x0, y0 = start_pos
        x1, y1 = end_pos
        isSteep = abs(y1 - y0) > abs(x1 - x0)
        if isSteep:
            # swap the x's and y's
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            # swap end points so that we always go left-to-right
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        if y0 < y1:
            ystep = 1
        else:
            ystep = -1
        xdelta = x1 - x0
        ydelta = abs(y1 - y0)
        error = -xdelta / 2 # TODO - float div or int div?
        y = y0
        for x in range(x0, x1+1): # +1 to include x1 in the range
            if isSteep:
                self.putchar(char, y, x, fgcolor, bgcolor)
            else:
                self.putchar(char, x, y, fgcolor, bgcolor)

            error = error + ydelta
            if error > 0:
                y = y + ystep
                error = error - xdelta


    def drawlines(self, pointlist, closed=False, char=' ', fgcolor=None, bgcolor=None):
        if len(pointlist) < 2:
            return
        for i in range(len(pointlist) - 1):
            self.drawline(pointlist[i], pointlist[i + 1], char, fgcolor, bgcolor)
        if closed:
            self.drawline(pointlist[-1], pointlist[0], char, fgcolor, bgcolor)


class PygcurseWindow(PygcurseSurface):
    _pygcurseClass = 'PygcurseWindow'

    def __init__(self, width=80, height=25, caption=None, font=None, fgcolor=DEFAULTFGCOLOR, bgcolor=DEFAULTBGCOLOR, fullscreen=False):
        pygame.init()
        self._fullscreen = fullscreen
        fullscreen = fullscreen and FULLSCREEN or _NEW_WINDOW
        if sys.version.startswith('2.'):
            super(PygcurseWindow, self).__init__(width, height, font, fgcolor, bgcolor, fullscreen) # for Python 2
        else:
            super().__init__(width, height, font, fgcolor, bgcolor, fullscreen) # for Python 3 and later
        if caption is not None:
            pygame.display.set_caption(caption)


    def blittowindow(self, dest=(0,0), displayupdate=True):
        retval = self._windowsurface.blit(self._surfaceobj, dest)
        if displayupdate:
            pygame.display.update()
        return retval


    def _propgetfullscreen(self):
        return self._fullscreen


    def _propsetfullscreen(self, value):
        if value and not self._fullscreen:
            self._fullscreen = True
            self._windowsurface = pygame.display.set_mode((self.pixelwidth, self.pixelheight), pygame.FULLSCREEN)
        elif not value and self._fullscreen:
            self._fullscreen = False
            self._windowsurface = pygame.display.set_mode((self.pixelwidth, self.pixelheight))

    fullscreen = property(_propgetfullscreen, _propsetfullscreen)


class PygcurseInput():
    """
    A PygcurseInput object keeps track of the state of a string of text being entered, identical to the behavior of raw_input()/input().

    Keypress events are sent to the object, which tracks the characters entered (in self.buffer) and the position of the cursor. The update() function draws the current state of the input to the PygcurseSurface object associated with it. (This is set in the constructor with the pygsurf parameter.)

    The design of this class is that it is meant to be polled. It does not use callbacks or multithreading or an event loop.
    """


    def __init__(self, pygsurf=None, prompt='', x=None, y=None, maxlength=None, fgcolor=None, bgcolor=None, promptfgcolor=None, promptbgcolor=None, whitelistchars=None, blacklistchars=None):
        self.buffer = []
        self.prompt = prompt
        self.pygsurf = pygsurf
        if maxlength is None and pygsurf is None:
            self._maxlength = 4094 # NOTE - Python's input()/raw_input() functions let you enter at most 4094 characters. PygcurseInput has this as a default unless you specify otherwise
        elif maxlength is None and x is not None and y is not None:
            self._maxlength = pygsurf.width - x
        else:
            self._maxlength = (maxlength is not None and maxlength > 0) and (maxlength) or (4094)
        self.cursor = 0
        self.showCursor = True
        self.blinkingCursor = True
        self.eraseBufferSize = None # when set to None, nothing needs to be erased. When the buffer decreases in size, we need to remember how big it was so that we can paint blank space characters.

        self.insertMode = False
        self.done = False # when True, the enter key has been pressed.

        if pygsurf is not None:
            if x is None:
                self.startx = pygsurf.cursorx
            else:
                self.startx = x
            if y is None:
                self.starty = pygsurf.cursory
            else:
                self.starty = y
            self.lastScrollCount = pygsurf._scrollcount
        else:
            if x is None:
                self.startx = 0
            else:
                self.startx = x
            if y is None:
                self.starty = 0
            else:
                self.starty = y
            self.lastScrollCount = 0

        self._fgcolor = (fgcolor is not None) and (getpygamecolor(fgcolor)) or (None)
        self._bgcolor = (bgcolor is not None) and (getpygamecolor(bgcolor)) or (None)
        self._promptfgcolor = (promptfgcolor is not None) and (getpygamecolor(promptfgcolor)) or (None)
        self._promptbgcolor = (promptbgcolor is not None) and (getpygamecolor(promptbgcolor)) or (None)

        self.whitelistchars = whitelistchars
        self.blacklistchars = blacklistchars

        self.multiline = True # if True, then wrap to next line (scrolling the PygcurseSurface if needed.)

        self.KEYMAPPING = {K_LEFT:      self.leftarrow,
                           K_RIGHT:     self.rightarrow,
                           K_HOME:      self.home,
                           K_END:       self.end,
                           K_BACKSPACE: self.backspace,
                           K_DELETE:    self.delete,
                           K_INSERT:    self.insert}

        if pygsurf._pygcurseClass == 'PygcurseWindow': # TODO - need a better way to identify the object
            self.pygsurface = pygsurf.surface
        elif pygsurf._pygcurseClass == 'PygcurseSurface': # TODO - need a better way to identify the object
            self.pygsurface = pygsurf
        else:
            raise Exception('Invalid argument passed for pygsurf parameter.')


    def updateerasebuffersize(self):
        """
        This method must be called whenever a character is deleted from the buffer. The eraseBufferSize member tracks how many characters have been deleted so that the next time this PygcurseInput object is drawn to the PygcurseSurface, it will erase the additional leftover characters.
        """
        # NOTE - don't update if the current buffer size is smaller than the current erase buffer size (two backspaces in a row without calling update() to reset erasebuffersize)
        if self.eraseBufferSize is None or len(self.buffer) > self.eraseBufferSize:
            self.eraseBufferSize = len(self.buffer)


    def backspace(self):
        """Perform the action that happens when the backspac key is pressed."""
        if self.cursor == 0:
            return
        self.cursor -= 1
        self.updateerasebuffersize()
        del self.buffer[self.cursor]


    def insert(self):
        """Perform the action that happens when the insert key is pressed."""
        self.insertMode = not self.insertMode


    def delete(self):
        """Perform the action that happens when the delete key is pressed."""
        if self.cursor == len(self.buffer):
            return
        self.updateerasebuffersize()
        del self.buffer[self.cursor]


    def home(self):
        """Perform the action that happens when the home key is pressed."""
        self.cursor = 0


    def end(self):
        """Perform the action that happens when the end key is pressed."""
        self.cursor = len(self.buffer)


    def leftarrow(self):
        """Perform the action that happens when the left arrow key is pressed."""
        if self.cursor > 0:
            self.cursor -= 1


    def rightarrow(self):
        """Perform the action that happens when the right arrow key is pressed."""
        if self.cursor < len(self.buffer):
            self.cursor += 1


    def paste(text):
        """
        Inserts the string text into the buffer at the position of the cursor. This does not actually use the system's clipboard, it only pastes from the text parameter.
        """
        text = str(text)
        if not self.insertMode and len(text) + len(self.buffer) > self._maxlength:
            text = text[:self._maxlength - len(self.buffer)] # truncate the pasted text (this is what web browsers do, so I'm copying that behavior)

        if self.cursor == len(self.buffer):
            # append to end
            self.buffer.extend(list(text))
        elif self.cursor == 0:
            # prepend to beginning
            self.buffer = list(text) + self.buffer
        else:
            if self.insertMode:
                # Overwrite characters
                self.buffer = self.buffer[:self.cursor] + list(text) + self.buffer[self.cursor + len(text):]
            else:
                self.buffer = self.buffer[:self.cursor] + list(text) + self.buffer[self.cursor:]


    def update(self, pygsurfObj=None):
        """
        Draw the PygcurseInput object to the PygcurseSurface object associated with it (in the self.pygsurf member) or to the pygsurfObj argument.

        This method handles drawing the prompt, typed in text, and cursor of this object.
        """
        if pygsurfObj is not None and pygsurfObj._pygcurseClass in ('PygcurseWindow', 'PygcurseSurface'): # TODO - need a better way to identify the object
            pygsurfObj = pygsurfObj.surface
        elif self.pygsurf is not None:
            pygsurfObj = self.pygsurf
        else:
            raise Exception('No PygcurseSurface object specified to draw the PygcurseWindow object to.')

        if self.lastScrollCount < pygsurfObj._scrollcount:
            # pygsurf has scrolled up since the last time this was drawn, move the input up.
            self.starty -= pygsurfObj._scrollcount - self.lastScrollCount
            # TODO - need to handle the case where the starty is now negative

        if self.multiline:
            pygsurfObj.pushcursor()
            if self.eraseBufferSize is not None:
                # need to blank out the previous drawn, longer string.
                pygsurfObj.write(self.prompt + (' ' * self.eraseBufferSize))
                pygsurfObj.popcursor() # revert to the original cursor before proceeding
                pygsurfObj.pushcursor()
                self.eraseBufferSize = None
            pygsurfObj.write(self.prompt, fgcolor=self._promptfgcolor, bgcolor=self._promptbgcolor)
            pygsurfObj.write(''.join(self.buffer) + ' ', fgcolor=self._fgcolor, bgcolor=self._bgcolor) # the space at the end is to change the color of the cursor
            afterPromptX, afterPromptY = pygsurfObj.getnthcellfrom(self.startx, self.starty, len(self.prompt))
            pygsurfObj.inputcursor = pygsurfObj.getnthcellfrom(afterPromptX, afterPromptY, self.cursor)
            pygsurfObj._drawinputcursor() # TODO - there's a bug if the prompt goes past the right edge, the screen cursor is in a weird place.
            pygsurfObj.popcursor() # restore previous cursor position that print() moved.
        else:
            # all this must fit on one line, with any excess text truncated
            if self.eraseBufferSize is not None:
                # need to blank out the previous drawn, longer string.
                tempcursorx = self.startx
                while tempcursorx < pygsurfObj.width and tempcursorx < self.startx + len(self.prompt) + eraseBufferSize:
                    pygsurfObj.putchar(' ', tempcursorx, self.starty)
                    tempcursorx += 1
                self.eraseBufferSize = None
            numToPrint = self._width - self.startx - 1
            # TODO - implement prompt colors, but keep in mind that this all has to be on one line.
            pygsurfObj.putchars((self.prompt + ''.join(self.buffer))[:numToPrint], self.startx, self.starty, fgcolor=self._fgcolor, bgcolor=self._bgcolor)
            pygsurfObj.inputcursor = pygsurfObj.getnthcellfrom(self.startx, self.starty, self.cursor)
            pygsurfObj._drawinputcursor()


    def enter(self):
        """Sets self.done to True, which means that the user has intended to enter the currently typed in text as their complete response. While self.done is True, this object will no longer process additional keyboard events."""
        self.done = True


    def sendkeyevent(self, keyEvent):
        """Interpret the character that the pygame.event.Event object passed as keyEvent represents, and perform the associated action. These actions could be adding another character to the buffer, or manipulating the cursor position (such as when the arrow keys are pressed)."""

        # TODO - how should we handle tab key presses? For now, we just treat it as a space.
        if self.done:
            return

        char = interpretkeyevent(keyEvent)
        if char in ('\r', '\n') and keyEvent.type == KEYUP: # TODO - figure out which is the right one
            self.done = True
            self.pygsurf.inputcursormode = None
            x, y = self.pygsurf.getnthcellfrom(self.startx, self.starty, self.cursor)
            self.pygsurf.write('\n') # print a newline to move the pygcurse surface object's cursor.
            self.pygsurf._repaintcell(x, y)
        elif char not in ('\r', '\n') and keyEvent.type == KEYDOWN:
            if char is None and keyEvent.key in self.KEYMAPPING:
                (self.KEYMAPPING[keyEvent.key])() # call the related method
            elif char is not None:
                if (self.whitelistchars is not None and char not in self.whitelistchars) or (self.blacklistchars is not None and char in self.blacklistchars):
                    return # filter out based on white and black list

                if char == '\t':
                    char = ' '
                if (not self.insertMode and len(self.buffer) < self._maxlength) or (self.insertMode and self.cursor == len(self.buffer)):
                    self.buffer.insert(self.cursor, char)
                    self.cursor += 1
                elif len(self.buffer) < self._maxlength:
                    self.buffer[self.cursor] = char
                    self.cursor += 1
        self.pygsurf.inputcursor = self.pygsurf.getnthcellfrom(self.startx, self.starty, self.cursor)


    def _debug(self):
        """Print out the current state of the PygcurseInput object to stdout."""
        print(self.prompt + ''.join(self.buffer) + '\t(%s length)' % len(self.buffer))
        print('.' * len(self.prompt) + '.' * self.cursor + '^')


    def __len__(self):
        """Returns the length of the buffer. This does not include the length of the prompt."""
        return len(self.buffer)


    # Properties
    def _propgetfgcolor(self):
        return self._fgcolor

    def _propsetfgcolor(self, value):
        self._fgcolor = getpygamecolor(value)


    def _propgetbgcolor(self):
        return self._bgcolor

    def _propsetbgcolor(self, value):
        self._bgcolor = getpygamecolor(value)

    def _propgetcolors(self):
        return (self._fgcolor, self._bgcolor)

    def _propsetcolors(self, value):
        self._fgcolor = getpygamecolor(value[0])
        self._bgcolor = getpygamecolor(value[1])


    def _propgetpromptfgcolor(self):
        return self._promptfgcolor

    def _propsetpromptfgcolor(self, value):
        self._promptfgcolor = getpygamecolor(value)


    def _propgetpromptbgcolor(self):
        return self._promptbgcolor

    def _propsetpromptbgcolor(self, value):
        self._promptbgcolor = getpygamecolor(value)

    def _propgetpromptcolors(self):
        return (self._promptfgcolor, self._promptbgcolor)

    def _propsetpromptcolors(self, value):
        self._promptfgcolor = getpygamecolor(value[0])
        self._promptbgcolor = getpygamecolor(value[1])

    fgcolor = property(_propgetfgcolor, _propsetfgcolor)
    bgcolor = property(_propgetbgcolor, _propsetbgcolor)
    colors = property(_propgetcolors, _propsetcolors)
    promptfgcolor = property(_propgetpromptfgcolor, _propsetpromptfgcolor)
    promptbgcolor = property(_propgetpromptbgcolor, _propsetpromptbgcolor)
    promptcolors = property(_propgetpromptcolors, _propsetpromptcolors)



class PygcurseTextbox:
    def __init__(self, pygsurf, region=None, fgcolor=None, bgcolor=None, text='', wrap=True, border='basic', caption='', margin=0, marginleft=None, marginright=None, margintop=None, marginbottom=None, shadow=None, shadowamount=51):
        self.pygsurf = pygsurf
        self.x, self.y, self.width, self.height = pygsurf.getregion(region, False)

        self.fgcolor = (fgcolor is None) and (pygsurf.fgcolor) or (getpygamecolor(fgcolor))
        self.bgcolor = (bgcolor is None) and (pygsurf.bgcolor) or (getpygamecolor(bgcolor))
        self.text = text
        self.wrap = wrap
        self.border = border # value is one of 'basic', 'rounded', or a single character
        self.caption = caption

        self.margintop = margin
        self.marginbottom = margin
        self.marginleft = margin
        self.marginright = margin
        if margintop is not None:
            self.margintop = margintop
        if marginbottom is not None:
            self.marginbottom = marginbottom
        if marginright is not None:
            self.marginright = marginright
        if marginleft is not None:
            self.marginleft = marginleft
        self.shadow = shadow # value is a None or directional constant, e.g. NORTHWEST
        self.shadowamount = shadowamount

        # not included in the parameters, because the number of parameters is getting ridiculous. The user can always change these later.
        self.shadowxoffset = 1
        self.shadowyoffset = 1

    def update(self, pygsurf=None):
        # NOTE - border of 'basic' uses +,-,| scheme. A single letter can be used to use that character for a border. None means no border. '' means an empty border (same as border of None and margin of 1)
        # NOTE - this function does not create scrollbars, any excess characters are just truncated.

        if pygsurf is None:
            pygsurf = self.pygsurf

        x, y, width, height = pygsurf.getregion((self.x, self.y, self.width, self.height))
        if (x, y, width, height) == (None, None, None, None):
            return

        fgcolor = (self.fgcolor is None) and pygsurf.fgcolor or self.fgcolor
        bgcolor = (self.bgcolor is None) and pygsurf.bgcolor or self.bgcolor

        # blank out space for box
        for ix in range(x, x + width):
            for iy in range(y, y + height):
                pygsurf._screenfgcolor[ix][iy] = fgcolor
                pygsurf._screenbgcolor[ix][iy] = bgcolor
                pygsurf._screenchar[ix][iy] = ' '
                pygsurf._screendirty[ix][iy] = True

        # Recalculate dimensions, this time including if they are off the surface.
        x, y, width, height = pygsurf.getregion((self.x, self.y, self.width, self.height), False)
        if (x, y, width, height) == (None, None, None, None):
            return

        # draw border
        if self.border in ('basic', 'rounded'):
            # corners
            if pygsurf.isonscreen(x, y):
                pygsurf._screenchar[x][y] = (self.border == 'basic') and '+' or '/'
            if pygsurf.isonscreen(x + width - 1, y):
                pygsurf._screenchar[x + width - 1][y] = (self.border == 'basic') and '+' or '\\'
            if pygsurf.isonscreen(x, y + height - 1):
                pygsurf._screenchar[x][y + height - 1] = (self.border == 'basic') and '+' or '\\'
            if pygsurf.isonscreen(x + width - 1, y + height - 1):
                pygsurf._screenchar[x + width - 1][y + height - 1] = (self.border == 'basic') and '+' or '/'

            # top/bottom side
            for ix in range(x + 1, x + width - 1):
                if pygsurf.isonscreen(ix, y):
                    pygsurf._screenchar[ix][y] = '-'
                if pygsurf.isonscreen(ix, y + height-1):
                    pygsurf._screenchar[ix][y + height-1] = '-'

            # left/right side
            for iy in range(y+1, y + height-1):
                if pygsurf.isonscreen(x, iy):
                    pygsurf._screenchar[x][iy] = '|'
                if pygsurf.isonscreen(x + width - 1, iy):
                    pygsurf._screenchar[x + width - 1][iy] = '|'
        elif self.border is not None and len(self.border) == 1:
            # use a single character to draw the entire border
            # top/bottom side
            for ix in range(x, x + width):
                if pygsurf.isonscreen(ix, y):
                    pygsurf._screenchar[ix][y] = self.border
                if pygsurf.isonscreen(ix, y + height-1):
                    pygsurf._screenchar[ix][y + height-1] = self.border

            # left/right side
            for iy in range(y+1, y + height-1):
                if pygsurf.isonscreen(x, iy):
                    pygsurf._screenchar[x][iy] = border
                if pygsurf.isonscreen(x + width - 1, iy):
                    pygsurf._screenchar[x + width - 1][iy] = border

        # draw caption:
        if self.caption:
            for i in range(len(self.caption)):
                if i + 2 > self.width - 2 or not pygsurf.isonscreen(x + i + 2, y):
                    continue
                pygsurf._screenchar[x + i + 2][y] = self.caption[i]

        # draw the textbox shadow
        if self.shadow is not None:
            pygsurf.addshadow(x=x, y=y, width=width, height=height, amount=self.shadowamount, direction=self.shadow, xoffset=self.shadowxoffset, yoffset=self.shadowyoffset)


        if self.text == '':
            return # There's no text to display, so return after drawing the background and border.
        text = self.getdisplayedtext()
        if text == '':
            return

        if self.border is not None:
            x += 1
            y += 1
            width -= 2
            height -= 2
        if not self.border and self.caption:
            y += 1
            height -= 1
        x += self.marginleft
        y += self.margintop
        width -= (self.marginleft + self.marginright)
        height -= (self.margintop + self.marginbottom)

        if y < 0: # if the top row of text is above the top edge of the surface, then truncate
            text = text[abs(y):]
            y = 0
        maxDisplayedLines = (y + height < pygsurf._height) and (height) or (max(0, pygsurf._height - y))

        truncateLeftChars = (x < 0) and abs(x) or 0
        maxDisplayedLength = (x + width < pygsurf._width) and (width) or (max(0, pygsurf._width - x))
        iy = 0
        for line in text:
            if y + iy >= pygsurf._height:
                break
            for ix in range(truncateLeftChars, min(len(line), maxDisplayedLength)):
                pygsurf._screenchar[x + ix][y + iy] = line[ix]
            iy += 1


    def getdisplayedtext(self):
    # returns the text that can be displayed given the box's current width, height, border, and margins
        margintop = self.margintop
        marginbottom = self.marginbottom
        marginright = self.marginright
        marginleft = self.marginleft

        # calculate margin & text layout
        if self.border is not None:
            margintop += 1
            marginbottom += 1
            marginleft += 1
            marginright += 1
        elif self.caption:
            margintop += 1

        width = self.width - marginleft - marginright
        height = self.height - margintop - marginbottom

        if width < 1 or height < 1:
            return '' # no room for text

        # handle word wrapping
        if self.wrap:
            text = textwrap.wrap(self.text, width=width)
        else:
            text = spitintogroupsof(width, self.text) # TODO - slight bug where if a line ends with \n, it could show an additional character. (this is the behavior of textwrap.wrap())

        return text[:height]


    def erase(self):
        # a convenience function, more than anything. Does the same thing as fill except for just the area of this text box.
        self.pygsurf.fill(x=self.x, y=self.y, width=self.width, height=self.height)

    # TODO - make properties for magins, shadowxoffset, etc.

    def _propgetleft(self):
        return self.x
    def _propgetright(self):
        return self.x + self.width - 1 # note: this behavior is different from pygame Rect objects, which do not have the -1.
    def _propgettop(self):
        return self.y
    def _propgetbottom(self):
        return self.y + self.height - 1 # note: this behavior is different from pygame Rect objects, which do not have the -1.
    def _propgetcenterx(self):
        return self.x + int(self.width / 2)
    def _propgetcentery(self):
        return self.y + int(self.height / 2)
    def _propgettopleft(self):
        return (self.x, self.y)
    def _propgettopright(self):
        return (self.x + self.width - 1, self.y)
    def _propgetbottomleft(self):
        return (self.x, self.y + self.height - 1)
    def _propgetbottomright(self):
        return (self.x + self.width - 1, self.y + self.height - 1)
    def _propgetmidleft(self):
        return (self.x, self.y + int(self.height / 2))
    def _propgetmidright(self):
        return (self.x + self.width - 1, self.y + int(self.height / 2))
    def _propgetmidtop(self):
        return (self.x + int(self.width / 2), self.y)
    def _propgetmidbottom(self):
        return (self.x + int(self.width / 2), self.y + self.height - 1)
    def _propgetcenter(self):
        return (self.x + int(self.width / 2), self.y + int(self.height / 2))
    def _propgetregion(self):
        return (self.x, self.y, self.width, self.height)

    def _propsetleft(self, value):
        self.x = value
    def _propsetright(self, value):
        self.x = value - self.width
    def _propsettop(self, value):
        self.y = value
    def _propsetbottom(self, value):
        self.y = value - self.height
    def _propsetcenterx(self, value):
        self.x = value - int(self.width / 2)
    def _propsetcentery(self, value):
        self.y = value - int(self.height / 2)
    def _propsetcenter(self, value):
        self.x = value[0] - int(self.width / 2)
        self.y = value[1] - int(self.height / 2)
    def _propsettopleft(self, value):
        self.x = value[0]
        self.y = value[1]
    def _propsettopright(self, value):
        self.x = value[0] - self.width
        self.y = value[1]
    def _propsetbottomleft(self, value):
        self.x = value[0]
        self.y = value[1] - self.height
    def _propsetbottomright(self, value):
        self.x = value[0] - self.width
        self.y = value[1] - self.height
    def _propsetmidleft(self, value):
        self.x = value[0]
        self.y = value[1] - int(self.height / 2)
    def _propsetmidright(self, value):
        self.x = value[0] - self.width
        self.y = value[1] - int(self.height / 2)
    def _propsetmidtop(self, value):
        self.x = value[0] - int(self.width / 2)
        self.y = value[1]
    def _propsetmidbottom(self, value):
        self.x = value[0] - int(self.width / 2)
        self.y = value[1] - self.height
    def _propsetcenter(self, value):
        self.x = value[0] - int(self.width / 2)
        self.y = value[1] - int(self.height / 2)
    def _propsetregion(self, value):
        self.x, self.y, self.width, self.height = pygsurf.getregion(value, False)

    def _propgetsize(self):
        return (self.width, self.height)
    def _propsetsize(self, value):
        newwidth = int(value[0])
        newheight = int(value[1])
        if newwidth != self.width or newheight != self.height:
            self.resize(newwidth, newheight)
    def _propgetpixelwidth(self):
        return self.width * self._cellwidth
    def _propsetpixelwidth(self, value):
        newwidth = int(int(value) / self._cellwidth)
        if newwidth != self.width:
            self.resize(newwidth=newwidth)
    def _propgetpixelheight(self):
        return self.height * self._cellheight
    def _propsetpixelheight(self, value):
        newheight = int(int(value) / self._cellheight)
        if newheight != self.height:
            self.resize(newheight=newheight)
    def _propgetpixelsize(self):
        return (self.width * self._cellwidth, self.height * self._cellheight)
    def _propsetpixelsize(self, value):
        newwidth = int(int(value) / self._cellwidth)
        newheight = int(int(value) / self._cellheight)
        if newwidth != self.width or newheight != self.height:
            self.resize(newwidth, newheight)

    left        = property(_propgetleft, _propsetleft)
    right       = property(_propgetright, _propsetright)
    top         = property(_propgettop, _propsettop)
    bottom      = property(_propgetbottom, _propsetbottom)
    centerx     = property(_propgetcenterx, _propsetcenterx)
    centery     = property(_propgetcentery, _propsetcentery)
    center      = property(_propgetcenter, _propsetcenter)
    topleft     = property(_propgettopleft, _propsettopleft)
    topright    = property(_propgettopright, _propsettopright)
    bottomleft  = property(_propgetbottomleft, _propsetbottomleft)
    bottomright = property(_propgetbottomright, _propsetbottomright)
    midleft     = property(_propgetmidleft, _propsetmidleft)
    midright    = property(_propgetmidright, _propsetmidright)
    midtop      = property(_propgetmidtop, _propsetmidtop)
    midbottom   = property(_propgetmidbottom, _propsetmidbottom)
    region      = property(_propgetregion, _propsetregion)

    pixelwidth  = property(_propgetsize, _propsetsize)
    pixelheight = property(_propgetsize, _propsetsize)
    pixelsize   = property(_propgetsize, _propsetsize)
    size        = property(_propgetsize, _propsetsize)

_shiftchars = {'`':'~', '1':'!', '2':'@', '3':'#', '4':'$', '5':'%', '6':'^', '7':'&', '8':'*', '9':'(', '0':')', '-':'_', '=':'+', '[':'{', ']':'}', '\\':'|', ';':':', "'":'"', ',':'<', '.':'>', '/':'?'}

def interpretkeyevent(keyEvent):
    """Returns the character represented by the pygame.event.Event object in keyEvent. This makes adjustments for the shift key and capslock."""
    key = keyEvent.key
    if (key >= 32 and key < 127) or key in (ord('\n'), ord('\r'), ord('\t')):
        caps = bool(keyEvent.mod & KMOD_CAPS)
        shift = bool(keyEvent.mod & KMOD_LSHIFT or keyEvent.mod & KMOD_RSHIFT)
        char = chr(key)
        if char.isalpha() and (caps ^ shift):
            char = char.upper()
        elif shift and char in _shiftchars:
            char = _shiftchars[char]
        return char
    return None # None means that there is no printable character corresponding to this keyEvent


def spitintogroupsof(groupSize, theList):
    # splits a sequence into a list of sequences, where the inner lists have at
    # most groupSize number of items.
    result = []
    for i in range(0, len(theList), groupSize):
        result.append(theList[i:i+groupSize])
    return result


def getwithinrange(value, min=0, max=255):
    """
    Returns value if it is between the min and max number arguments. If value is greater than max, then max is returned. If value is less than min, then min is returned. If min and/or max is not specified, then the value is not limited in that direction.
    """
    if min is not None and value < min:
        return min
    elif max is not None and value > max:
        return max
    else:
        return value


def calcfontsize(font):
    """Returns the maximum width and maximum height used by any character in this font. This function is used to calculate the cell size."""
    maxwidth = 0
    maxheight = 0
    for i in range(32, 127):
        surf = font.render(chr(i), True, (0,0,0))
        if surf.get_width() > maxwidth:
            maxwidth = surf.get_width()
        if surf.get_height() > maxheight:
            maxheight = surf.get_height()

    return maxwidth, maxheight


def _ismonofont(font):
    """Returns True if all the characters in the font are of the same width, indicating that this is a monospace font.

    TODO - Not sure what I was planning to use this function for. I'll leave it in here for now.
    """
    minwidth = 0
    minheight = 0
    for i in range(32, 127):
        surf = font.render(chr(i), True, (0,0,0))
        if surf.get_width() < minwidth:
            minwidth = surf.get_width()
        if surf.get_height() < minheight:
            minheight = surf.get_height()

    maxwidth, maxheight = calcfontsize(font)
    return maxwidth - minwidth <= 3 and maxheight - minheight <= 3


def getpygamecolor(value):
    """Returns a pygame.Color object of the argument passed in. The argument can be a RGB/RGBA tuple, pygame.Color object, or string in the colornames dict (such as 'blue' or 'gray')."""
    if type(value) in (tuple, list):
        alpha = len(value) > 3 and value[3] or 255
        return pygame.Color(value[0], value[1], value[2], alpha)
    elif str(type(value)) in ("<class 'pygame.Color'>", "<type 'pygame.Color'>"):
        return value
    elif value in colornames:
        return colornames[value]
    else:
        raise Exception('Color set to invalid value: %s' % (repr(value)))

    if type(color) in (tuple, list):
        return pygame.Color(*color)
    return color

def waitforkeypress(fps=None):
    # Go through event queue looking for a KEYUP event.
    # Grab KEYDOWN events to remove them from the event queue.
    if fps is not None:
        clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get([KEYDOWN, KEYUP, QUIT]):
            if event.type == KEYDOWN:
                continue
            elif event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYUP:
                return interpretkeyevent(event)
        pygame.display.update()
        if fps is not None:
            clock.tick(fps)

def regionsoverlap(region1, region2):
    return withinregion(region1[0], region1[1], region2) or \
           withinregion(region1[0] + region1[2], region1[1], region2) or \
           withinregion(region1[0], region1[1] + region1[3], region2) or \
           withinregion(region1[0] + region1[2], region1[1] + region1[3], region2) or \
           withinregion(region2[0], region2[1], region1) or \
           withinregion(region2[0] + region2[2], region2[1], region1) or \
           withinregion(region2[0], region2[1] + region2[3], region1) or \
           withinregion(region2[0] + region2[2], region2[1] + region2[3], region1)

def withinregion(x, y, region):
    return x > region[0] and x < region[0] + region[2] and y > region[1] and y < region[1] + region[3]

########NEW FILE########
