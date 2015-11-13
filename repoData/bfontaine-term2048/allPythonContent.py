__FILENAME__ = board
# -*- coding: UTF-8 -*-
import random

# PY3 compat
try:
    xrange
except NameError:
    xrange = range


class Board(object):
    """
    A 2048 board
    """

    UP, DOWN, LEFT, RIGHT = 1, 2, 3, 4

    GOAL = 2048
    SIZE = 4

    def __init__(self, goal=GOAL, size=SIZE, **kws):
        self.__size = size
        self.__size_range = xrange(0, self.__size)
        self.__goal = goal
        self.__won = False
        self.cells = [[0]*self.__size for _ in xrange(self.__size)]
        self.addTile()
        self.addTile()

    def size(self):
        """return the board size"""
        return self.__size

    def goal(self):
        """return the board goal"""
        return self.__goal

    def won(self):
        """
        return True if the board contains at least one tile with the board goal
        """
        return self.__won

    def canMove(self):
        """
        test if a move is possible
        """
        if not self.filled():
            return True

        for y in self.__size_range:
            for x in self.__size_range:
                c = self.getCell(x, y)
                if (x < self.__size-1 and c == self.getCell(x+1, y)) \
                   or (y < self.__size-1 and c == self.getCell(x, y+1)):
                    return True

        return False

    def filled(self):
        """
        return true if the game is filled
        """
        return len(self.getEmptyCells()) == 0

    def addTile(self, value=None, choices=([2]*9+[4])):
        """
        add a random tile in an empty cell
          value: value of the tile to add.
          choices: a list of possible choices for the value of the tile.
                   default is [2, 2, 2, 2, 2, 2, 2, 2, 2, 4].
        """
        if value:
            choices = [value]

        v = random.choice(choices)
        empty = self.getEmptyCells()
        if empty:
            x, y = random.choice(empty)
            self.setCell(x, y, v)

    def getCell(self, x, y):
        """return the cell value at x,y"""
        return self.cells[y][x]

    def setCell(self, x, y, v):
        """set the cell value at x,y"""
        self.cells[y][x] = v

    def getLine(self, y):
        """return the y-th line, starting at 0"""
        return self.cells[y]

    def getCol(self, x):
        """return the x-th column, starting at 0"""
        return [self.getCell(x, i) for i in self.__size_range]

    def setLine(self, y, l):
        """set the y-th line, starting at 0"""
        self.cells[y] = l[:]

    def setCol(self, x, l):
        """set the x-th column, starting at 0"""
        for i in xrange(0, self.__size):
            self.setCell(x, i, l[i])

    def getEmptyCells(self):
        """return a (x, y) pair for each empty cell"""
        return [(x, y)
                for x in self.__size_range
                for y in self.__size_range if self.getCell(x, y) == 0]

    def __collapseLineOrCol(self, line, d):
        """
        Merge tiles in a line or column according to a direction and return a
        tuple with the new line and the score for the move on this line
        """
        if (d == Board.LEFT or d == Board.UP):
            inc = 1
            rg = xrange(0, self.__size-1, inc)
        else:
            inc = -1
            rg = xrange(self.__size-1, 0, inc)

        pts = 0
        for i in rg:
            if line[i] == 0:
                continue
            if line[i] == line[i+inc]:
                v = line[i]*2
                if v == self.__goal:
                    self.__won = True

                line[i] = v
                line[i+inc] = 0
                pts += v

        return (line, pts)

    def __moveLineOrCol(self, line, d):
        """
        Move a line or column to a given direction (d)
        """
        nl = [c for c in line if c != 0]
        if d == Board.UP or d == Board.LEFT:
            return nl + [0] * (self.__size - len(nl))
        return [0] * (self.__size - len(nl)) + nl

    def move(self, d, add_tile=True):
        """
        move and return the move score
        """
        if d == Board.LEFT or d == Board.RIGHT:
            chg, get = self.setLine, self.getLine
        elif d == Board.UP or d == Board.DOWN:
            chg, get = self.setCol, self.getCol
        else:
            return 0

        moved = False
        score = 0

        for i in self.__size_range:
            # save the original line/col
            origin = get(i)
            # move it
            line = self.__moveLineOrCol(origin, d)
            # merge adjacent tiles
            collapsed, pts = self.__collapseLineOrCol(line, d)
            # move it again (for when tiles are merged, because empty cells are
            # inserted in the middle of the line/col)
            new = self.__moveLineOrCol(collapsed, d)
            # set it back in the board
            chg(i, new)
            # did it change?
            if origin != new:
                moved = True
            score += pts

        # don't add a new tile if nothing changed
        if moved and add_tile:
            self.addTile()

        return score

########NEW FILE########
__FILENAME__ = game
# -*- coding: UTF-8 -*-
from __future__ import print_function

import os
import os.path
import math

from colorama import init, Fore, Style
init(autoreset=True)

from term2048 import keypress
from term2048.board import Board


class Game(object):
    """
    A 2048 game
    """

    __dirs = {
        keypress.UP:      Board.UP,
        keypress.DOWN:    Board.DOWN,
        keypress.LEFT:    Board.LEFT,
        keypress.RIGHT:   Board.RIGHT,
    }

    __clear = 'cls' if os.name == 'nt' else 'clear'

    COLORS = {
        2:    Fore.GREEN,
        4:    Fore.BLUE + Style.BRIGHT,
        8:    Fore.CYAN,
        16:   Fore.RED,
        32:   Fore.MAGENTA,
        64:   Fore.CYAN,
        128:  Fore.BLUE + Style.BRIGHT,
        256:  Fore.MAGENTA,
        512:  Fore.GREEN,
        1024: Fore.RED,
        2048: Fore.YELLOW,
        # just in case people set an higher goal they still have colors
        4096: Fore.RED,
        8192: Fore.CYAN,
    }

    # see Game#adjustColors
    # these are color replacements for various modes
    __color_modes = {
        'dark': {
            Fore.BLUE: Fore.WHITE,
            Fore.BLUE + Style.BRIGHT: Fore.WHITE,
        },
        'light': {
            Fore.YELLOW: Fore.BLACK,
        },
    }

    SCORES_FILE = '%s/.term2048.scores' % os.path.expanduser('~')

    def __init__(self, scores_file=SCORES_FILE, colors=COLORS,
                 clear_screen=True,
                 mode=None, azmode=False, **kws):
        """
        Create a new game.
            scores_file: file to use for the best score (default
                         is ~/.term2048.scores)
            colors: dictionnary with colors to use for each tile
            mode: color mode. This adjust a few colors and can be 'dark' or
                  'light'. See the adjustColors functions for more info.
            other options are passed to the underlying Board object.
        """
        self.board = Board(**kws)
        self.score = 0
        self.scores_file = scores_file
        self.clear_screen = clear_screen

        self.__colors = colors
        self.__azmode = azmode

        self.loadBestScore()
        self.adjustColors(mode)

    def adjustColors(self, mode='dark'):
        """
        Change a few colors depending on the mode to use. The default mode
        doesn't assume anything and avoid using white & black colors. The dark
        mode use white and avoid dark blue while the light mode use black and
        avoid yellow, to give a few examples.
        """
        rp = Game.__color_modes.get(mode, {})
        for k, color in self.__colors.items():
            self.__colors[k] = rp.get(color, color)

    def loadBestScore(self):
        """
        load local best score from the default file
        """
        if self.scores_file is None or not os.path.exists(self.scores_file):
            self.best_score = 0
            return
        try:
            f = open(self.scores_file, 'r')
            self.best_score = int(f.readline(), 10)
            f.close()
        except:
            pass  # fail silently

    def saveBestScore(self):
        """
        save current best score in the default file
        """
        if self.score > self.best_score:
            self.best_score = self.score
        try:
            f = open(self.scores_file, 'w')
            f.write(str(self.best_score))
            f.close()
        except:
            pass  # fail silently

    def incScore(self, pts):
        """
        update the current score by adding it the specified number of points
        """
        self.score += pts
        if self.score > self.best_score:
            self.best_score = self.score

    def readMove(self):
        """
        read and return a move to pass to a board
        """
        k = keypress.getKey()
        return Game.__dirs.get(k)

    def loop(self):
        """
        main game loop. returns the final score.
        """
        try:
            while True:
                if self.clear_screen:
                    os.system(Game.__clear)
                else:
                    print("\n")
                print(self.__str__(margins={'left': 4, 'top': 4, 'bottom': 4}))
                if self.board.won() or not self.board.canMove():
                    break
                m = self.readMove()
                self.incScore(self.board.move(m))

        except KeyboardInterrupt:
            self.saveBestScore()
            return

        self.saveBestScore()
        print('You won!' if self.board.won() else 'Game Over')
        return self.score

    def getCellStr(self, x, y):  # TODO: refactor regarding issue #11
        """
        return a string representation of the cell located at x,y.
        """
        c = self.board.getCell(x, y)

        az = {}
        for i in range(1, int(math.log(self.board.goal(), 2))):
            az[2 ** i] = chr(i + 96)

        if c == 0 and self.__azmode:
            return '.'
        elif c == 0:
            return '  .'

        elif self.__azmode:
            if c not in az:
                return '?'
            s = az[c]
        elif c == 1024:
            s = ' 1k'
        elif c == 2048:
            s = ' 2k'
        else:
            s = '%3d' % c

        return self.__colors.get(c, Fore.RESET) + s + Style.RESET_ALL

    def boardToString(self, margins={}):
        """
        return a string representation of the current board.
        """
        b = self.board
        rg = range(b.size())
        left = ' '*margins.get('left', 0)
        s = '\n'.join(
            [left + ' '.join([self.getCellStr(x, y) for x in rg]) for y in rg])
        return s

    def __str__(self, margins={}):
        b = self.boardToString(margins=margins)
        top = '\n'*margins.get('top', 0)
        bottom = '\n'*margins.get('bottom', 0)
        scores = ' \tScore: %5d  Best: %5d\n' % (self.score, self.best_score)
        return top + b.replace('\n', scores, 1) + bottom

########NEW FILE########
__FILENAME__ = keypress
# -*- coding: UTF-8 -*-

try:
    import termios
except ImportError:
    # Assume windows

    import msvcrt

    UP, DOWN, RIGHT, LEFT = 72, 80, 77, 75

    def getKey():
        while True:
            if msvcrt.kbhit():
                a = ord(msvcrt.getch())
                return a

else:
    # refs:
    # http://bytes.com/topic/python/answers/630206-check-keypress-linux-xterm
    # http://stackoverflow.com/a/2521032/735926

    import sys
    import tty

    __fd = sys.stdin.fileno()
    __old = termios.tcgetattr(__fd)

    # Arrow keys
    # they are preceded by 27 and 91, hence the double 'if' in getKey.
    UP, DOWN, RIGHT, LEFT = 65, 66, 67, 68

    # Vim keys
    K, J, L, H = 107, 106, 108, 104

    __key_aliases = {
        K: UP,
        J: DOWN,
        L: RIGHT,
        H: LEFT,
    }

    def __getKey():
        """Return a key pressed by the user"""
        try:
            tty.setcbreak(sys.stdin.fileno())
            termios.tcflush(sys.stdin, termios.TCIOFLUSH)
            ch = sys.stdin.read(1)
            return ord(ch) if ch else None
        finally:
            termios.tcsetattr(__fd, termios.TCSADRAIN, __old)

    def getKey():
        """
        same as __getKey, but handle arrow keys
        """
        k = __getKey()
        if k == 27:
            k = __getKey()
            if k == 91:
                k = __getKey()

        return __key_aliases.get(k, k)

# legacy support
getArrowKey = getKey

########NEW FILE########
__FILENAME__ = ui
# -*- coding: UTF-8 -*-
from __future__ import print_function

import sys
from term2048.game import Game

# set this to true when unit testing
debug = False

__has_argparse = True
try:
    import argparse
except ImportError:
    __has_argparse = False


def __print_argparse_warning():
    """print a warning for Python 2.6 users who don't have argparse"""
    print("""WARNING:
        You seems to be running Python 2.6 without 'argparse'. Please install
        the module so I can handle your options:
            [sudo] pip install argparse
        I'll continue without processing any option.""")


def print_version_and_exit():
    from term2048 import __version__
    print("term2048 v%s" % __version__)
    sys.exit(0)


def print_rules_and_exit():
    print("""Use your arrow keys to move the tiles.
When two tiles with the same value touch they merge into one with the sum of
their value! Try to reach 2048 to win.""")
    sys.exit(0)


def parse_cli_args():
    """parse args from the CLI and return a dict"""
    parser = argparse.ArgumentParser(description='2048 in your terminal')
    parser.add_argument('--mode', dest='mode', type=str,
                        default=None, help='colors mode (dark or light)')
    parser.add_argument('--az', dest='azmode', action='store_true',
                        help='Use the letters a-z instead of numbers')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--rules', action='store_true')
    return vars(parser.parse_args())


def start_game():
    """start a new game"""
    if not __has_argparse:
        __print_argparse_warning()
        args = {}
    else:
        args = parse_cli_args()

        if args['version']:
            print_version_and_exit()

        if args['rules']:
            print_rules_and_exit()

    if not debug:
        Game(**args).loop()

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: UTF-8 -*-

import platform

msvcrt_key = 42

# use this for mocking stdout
class DevNull(object):
    def __init__(self, output=None):
        """output: dict where to put the output written in this instance"""
        self.output = output

    def write(self, s):
        if self.output is not None:
            k = 'output'
            self.output[k] = self.output.get(k, '') + s

# use this for mocking msvcrt
class FakeMsvcrt(object):
    def kbhit(self):
        return True
    def getch(self):
        return chr(msvcrt_key)

# builtin (before 3.0) function 'reload(<module>)'
if platform.python_version() < '3.0':
    reload = reload
else:
    import imp
    reload = imp.reload

# used by sys.exit mocks
class FakeExit(Exception):
    pass

########NEW FILE########
__FILENAME__ = keypress_mock
# -*- coding: UTF-8 -*-

# helpers

__kp = None
__keys = []
__ctrl_c = False # flag for KeyboardInterrupt

UP, DOWN, LEFT, RIGHT = range(4)

def _setRealModule(m):
    """test helper, save the real keypress module"""
    global __kp, UP, DOWN, LEFT, RIGHT
    __kp=m
    UP = __kp.UP
    DOWN = __kp.DOWN
    LEFT = __kp.LEFT
    RIGHT = __kp.RIGHT

def _getRealModule():
    return __kp

def _setNextKeys(ks):
    """test helper, set next key to return with getKey"""
    global __keys
    __keys = ks

def _setNextKey(k):
    _setNextKeys([k])

def _setCtrlC(yes=True):
    global __ctrl_c
    __ctrl_c = yes

# mocks

def getKey():
    """mock term2048.keypress.getKey"""
    if __ctrl_c:
        raise KeyboardInterrupt()
    return __keys.pop()

########NEW FILE########
__FILENAME__ = test
# -*- coding: UTF-8 -*-
import sys
import platform

if platform.python_version() < '2.7':
    import unittest2 as unittest
else:
    import unittest

from os.path import dirname
import keypress_mock as kp

if __name__ == '__main__':
    here = dirname(__file__)
    sys.path.insert(0, here+'/..')
    # keypress mock
    import term2048.keypress
    _kp = term2048.keypress
    kp._setRealModule(_kp)
    term2048.keypress = kp
    # /keypress mock
    suite = unittest.defaultTestLoader.discover(here)
    t = unittest.TextTestRunner().run(suite)
    if not t.wasSuccessful():
        sys.exit(1)

########NEW FILE########
__FILENAME__ = test_board
# -*- coding: UTF-8 -*-

import platform

if platform.python_version() < '2.7':
    import unittest2 as unittest
else:
    import unittest

if platform.python_version() < '3.0':
    import __builtin__
else:
    import builtins as __builtin__

import helpers
from term2048 import board
Board = board.Board

# PY3 compat
try:
    xrange
except NameError:
    xrange = range


class TestBoard(unittest.TestCase):

    def setUp(self):
        self.b = Board()

    # == init == #
    def test_init_dimensions(self):
        self.assertEqual(len(self.b.cells), Board.SIZE)
        self.assertEqual(len(self.b.cells[0]), Board.SIZE)
        if Board.SIZE > 1:
            self.assertEqual(len(self.b.cells[1]), Board.SIZE)

    def test_init_dimensions_1(self):
        b = Board(size=1)
        c = b.cells[0][0]
        self.assertTrue(c in [2, 4])

    def test_init_dimensions_3_goal_4(self):
        b = Board(size=3, goal=4)
        self.assertEqual(b.size(), 3)

    def test_init_only_two_tiles(self):
        t = 0
        for x in xrange(Board.SIZE):
            for y in xrange(Board.SIZE):
                c = self.b.cells[y][x]
                if not c == 0:
                    t += 1
                else:
                    self.assertEqual(c, 0, 'board[%d][%d] should be 0' % (y, x))

        self.assertEqual(t, 2)

    def test_init_not_won(self):
        self.assertFalse(self.b.won())

    def test_init_not_filled(self):
        self.assertFalse(self.b.filled())

    # == .size == #
    def test_size(self):
        s = 42
        b = Board(size=s)
        self.assertEqual(b.size(), s)

    # == .goal == #
    def test_goal(self):
        g = 17
        b = Board(goal=g)
        self.assertEqual(b.goal(), g)

    # == .won == #
    def test_won(self):
        self.b._Board__won = True
        self.assertTrue(self.b.won())
        self.b._Board__won = False
        self.assertFalse(self.b.won())

    # == .canMove == #
    def test_canMove_no_empty_cell(self):
        b = Board(size=1)
        b.setCell(0, 0, 42)
        self.assertFalse(b.canMove())

    def test_canMove_empty_cell(self):
        b = Board(size=2)
        self.assertTrue(b.canMove())

    def test_canMove_no_empty_cell_can_collapse(self):
        b = Board(size=2)
        b.cells = [
            [2, 2],
            [4, 8]
        ]
        self.assertTrue(b.canMove())

    # == .filled == #
    def test_filled(self):
        self.b.cells = [[1]*Board.SIZE for _ in xrange(Board.SIZE)]
        self.assertTrue(self.b.filled())

    # == .addTile == #
    def test_addTile(self):
        b = Board(size=1)
        b.cells = [[0]]
        b.addTile(value=42)
        self.assertEqual(b.cells[0][0], 42)

    # == .getCell == #
    def test_getCell(self):
        x, y = 3, 1
        v = 42
        self.b.cells[y][x] = v
        self.assertEqual(self.b.getCell(x, y), v)

    # == .setCell == #
    def test_setCell(self):
        x, y = 2, 3
        v = 42
        self.b.setCell(x, y, v)
        self.assertEqual(self.b.cells[y][x], v)

    # == .getLine == #
    def test_getLine(self):
        b = Board(size=4)
        l = [42, 17, 12, 3]
        b.cells = [
            [0]*4,
            l,
            [0]*4,
            [0]*4
        ]
        self.assertSequenceEqual(b.getLine(1), l)

    # == .getCol == #
    def test_getCol(self):
        s = 4
        b = Board(size=s)
        l = [42, 17, 12, 3]
        b.cells = [[l[i], 4, 1, 2] for i in xrange(s)]
        self.assertSequenceEqual(b.getCol(0), l)

    # == .setLine == #
    def test_setLine(self):
        i = 2
        l = [1, 2, 3, 4]
        self.b.setLine(i, l)
        self.assertEqual(self.b.getLine(i), l)

    # == .setCol == #
    def test_setCol(self):
        i = 2
        l = [1, 2, 3, 4]
        self.b.setCol(i, l)
        self.assertEqual(self.b.getCol(i), l)

    # == .getEmptyCells == #
    def test_getEmptyCells(self):
        self.assertEqual(len(self.b.getEmptyCells()), Board.SIZE**2 - 2)

    def test_getEmptyCells_filled(self):
        b = Board(size=1)
        b.setCell(0, 0, 42)
        self.assertSequenceEqual(b.getEmptyCells(), [])

    # == .move == #
    def test_move_filled(self):
        b = Board(size=1)
        b.setCell(0, 0, 42)
        b.move(Board.UP)
        self.assertSequenceEqual(b.cells, [[42]])
        b.move(Board.LEFT)
        self.assertSequenceEqual(b.cells, [[42]])
        b.move(Board.RIGHT)
        self.assertSequenceEqual(b.cells, [[42]])
        b.move(Board.DOWN)
        self.assertSequenceEqual(b.cells, [[42]])

    def test_move_add_tile_if_collapse(self):
        b = Board(size=2)
        b.cells = [[2, 0],
                   [2, 0]]
        b.move(Board.UP)
        self.assertEqual(len([e for l in b.cells for e in l if e != 0]), 2)

    def test_move_add_tile_if_move(self):
        b = Board(size=2)
        b.cells = [[0, 0],
                   [2, 0]]
        b.move(Board.UP)
        self.assertEqual(len([e for l in b.cells for e in l if e != 0]), 2)

    def test_move_dont_add_tile_if_nothing_move(self):
        b = Board(size=2)
        b.cells = [[2, 0],
                   [0, 0]]
        b.move(Board.UP)
        self.assertEqual(len([e for l in b.cells for e in l if e != 0]), 1)

    # test for issue #1
    def test_move_dont_add_tile_if_nothing_move2(self):
        b = Board()
        b.cells = [
            [8, 4, 4, 2],
            [0, 2, 2, 0],
            [0]*4,
            [0]*4
        ]
        self.assertEqual(b.move(Board.UP), 0)
        self.assertEqual(len([e for l in b.cells for e in l if e != 0]), 6)
        self.assertEqual(b.getLine(0), [8, 4, 4, 2])
        self.assertEqual(b.getLine(1), [0, 2, 2, 0])

    def test_move_collapse(self):
        b = Board(size=2)
        b.cells = [
            [2, 2],
            [0, 0]
        ]

        b.move(Board.LEFT, add_tile=False)
        self.assertSequenceEqual(b.cells, [
            [4, 0],
            [0, 0]
        ])

    def test_move_collapse_triplet1(self):
        b = Board(size=3)
        b.setLine(0, [2, 2, 2])
        b.move(Board.LEFT, add_tile=False)
        self.assertSequenceEqual(b.getLine(0), [4, 2, 0])

    def test_move_collapse_triplet2(self):
        b = Board(size=3)
        b.setLine(0, [2, 2, 2])
        b.move(Board.RIGHT, add_tile=False)
        self.assertSequenceEqual(b.getLine(0), [0, 2, 4])

    def test_move_collapse_with_empty_cell_in_between(self):
        b = Board(size=3)
        b.setLine(0, [2, 0, 2])
        b.move(Board.RIGHT, add_tile=False)
        self.assertSequenceEqual(b.getLine(0), [0, 0, 4])

    def test_move_collapse_with_empty_cell_in_between2(self):
        b = Board(size=3)
        b.setLine(0, [2, 0, 2])
        b.move(Board.LEFT, add_tile=False)
        self.assertSequenceEqual(b.getLine(0), [4, 0, 0])

    def test_move_collapse_and_win(self):
        b = Board(size=2, goal=4)
        b.cells = [
            [2, 2],
            [0, 0]
        ]
        b.move(Board.LEFT, add_tile=False)
        self.assertTrue(b.won())

    def test_move_wrong_direction(self):
        self.assertEqual(self.b.move(42, add_tile=False), 0)
        self.assertEqual(self.b.move(None), 0)
        self.assertEqual(self.b.move("up"), 0)


    # tests for weird-collapse-bug reported on HN (issue #2)
    #   see: https://news.ycombinator.com/item?id=7398249

    def test_move_collapse_chain_col(self):
        b = Board()
        b.setCol(0, [0, 2, 2, 4])
        b.move(Board.DOWN, add_tile=False)
        self.assertSequenceEqual(b.getCol(0), [0, 0, 4, 4])

    def test_move_collapse_chain_line_right(self):
        b = Board()
        b.cells = [
            [0, 2, 2, 4],
            [0]*4,
            [0]*4,
            [0]*4
        ]
        self.assertEqual(b.move(Board.RIGHT, add_tile=False), 4)
        self.assertSequenceEqual(b.getLine(0), [0, 0, 4, 4])

    def test_move_collapse_chain_line_right2(self):
        b = Board()
        b.cells = [
            [0, 4, 2, 2],
            [0]*4,
            [0]*4,
            [0]*4
        ]
        self.assertEqual(b.move(Board.RIGHT, add_tile=False), 4)
        self.assertSequenceEqual(b.getLine(0), [0, 0, 4, 4])

    def test_move_collapse_chain_line_left(self):
        b = Board()
        b.cells = [
            [0, 2, 2, 4],
            [0]*4,
            [0]*4,
            [0]*4
        ]
        self.assertEqual(b.move(Board.LEFT, add_tile=False), 4)
        self.assertSequenceEqual(b.getLine(0), [4, 4, 0, 0])

    def test_move_collapse_chain_four_same_tiles(self):
        b = Board()
        b.cells = [
            [2, 2, 2, 2],
            [0]*4,
            [0]*4,
            [0]*4
        ]
        self.assertEqual(b.move(Board.LEFT, add_tile=False), 8)
        self.assertSequenceEqual(b.getLine(0), [4, 4, 0, 0])


class TestBoardPy3k(unittest.TestCase):
    def setUp(self):
        try:
            self.xr = __builtin__.xrange
            delattr(__builtin__, 'xrange')
        except AttributeError:
            self.xr = None
        helpers.reload(board)

    def tearDown(self):
        __builtin__.xrange = self.xr

    def test_xrange_fallback_on_range_on_py3k(self):
        self.assertEqual(board.xrange, __builtin__.range)

########NEW FILE########
__FILENAME__ = test_game
# -*- coding: UTF-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import keypress_mock as kp
from colorama import Fore, Style
from term2048.board import Board
from term2048.game import Game

import sys
import os
from tempfile import NamedTemporaryFile
from os import remove
from helpers import DevNull

_BSIZE = Board.SIZE

class TestGame(unittest.TestCase):

    def setUp(self):
        Board.SIZE = _BSIZE
        Game.SCORES_FILE = None
        self.g = Game(scores_file=None)
        self.b = self.g.board
        # don't print anything on stdout
        self.stdout = sys.stdout
        sys.stdout = DevNull()
        # mock os.system
        self.system = os.system
        self.sys_cmd = None
        def fake_system(*cmd):
            self.sys_cmd = cmd

        os.system = fake_system

    def tearDown(self):
        sys.stdout = self.stdout
        os.system = self.system
        kp._setCtrlC(False)

    def test_init_with_size_3_goal_4(self):
        g = Game(size=3, goal=4, scores_file=None)
        self.assertEqual(g.board.size(), 3)

    # == .saveBestScore == #

    def test_save_best_score_no_file(self):
        s = 42
        self.g.score = s
        self.g.saveBestScore()
        self.assertEqual(self.g.best_score, s)

    def test_save_best_score_with_file(self):
        s = 1000
        scores_file = NamedTemporaryFile(delete=True)
        g = Game(scores_file=scores_file.name)
        g.best_score = 0
        g.score = s
        g.saveBestScore()
        self.assertEqual(g.best_score, s)

    # == .loadBestScore == #

    def test_init_with_local_scores_file(self):
        s = 4241
        scores_file = NamedTemporaryFile(delete=False)
        scores_file.write(str(s).encode())
        scores_file.close()

        g = Game(scores_file=scores_file.name)
        self.assertEqual(g.best_score, s)

        remove(scores_file.name)

    def test_init_with_local_scores_file_fail(self):
        scores_file = NamedTemporaryFile(delete=False)
        scores_file.close()

        g = Game(scores_file=scores_file.name)

        remove(scores_file.name)

    # == .incScore == #

    def test_inc_0_score(self):
        s = 3
        self.g.score = s
        self.g.best_score = s
        self.g.incScore(0)
        self.assertEqual(self.g.score, s)
        self.assertEqual(self.g.best_score, s)

    def test_inc_2_score(self):
        s = 3
        i = 2
        self.g.score = s
        self.g.best_score = s
        self.g.incScore(i)
        self.assertEqual(self.g.score, s+i)
        self.assertEqual(self.g.best_score, s+i)

    def test_inc_score_update_best_score(self):
        s = 3
        i = 2
        self.g.score = s
        self.g.best_score = 0
        self.g.incScore(i)
        self.assertEqual(self.g.score, s+i)
        self.assertEqual(self.g.best_score, s+i)

    def test_inc_score_dont_update_best_score_if_higher(self):
        s = 3
        bs = 80
        i = 2
        self.g.score = s
        self.g.best_score = bs
        self.g.incScore(i)
        self.assertEqual(self.g.score, s+i)
        self.assertEqual(self.g.best_score, bs)

    # == .readMove == #

    def test_read_unknown_move(self):
        kp._setNextKey(-1)
        self.assertEqual(self.g.readMove(), None)

    def test_read_known_move(self):
        kp._setNextKey(kp.LEFT)
        self.assertEqual(self.g.readMove(), Board.LEFT)

    # == .loop == #

    def test_simple_win_loop(self):
        kp._setNextKey(kp.UP)
        g = Game(goal=4, size=2, clear_screen=False)
        g.board.cells = [
            [2, 0],
            [2, 0]
        ]
        g.loop()

    def test_simple_win_loop_clear(self):
        kp._setNextKey(kp.UP)
        g = Game(goal=4, size=2)
        g.board.cells = [
            [2, 0],
            [2, 0]
        ]
        self.assertEqual(g.loop(), 4)
        if os.name == 'nt':
            self.assertEqual(self.sys_cmd, ('cls',))
        else:
            self.assertEqual(self.sys_cmd, ('clear',))

    def test_loop_interrupt(self):
        kp._setCtrlC(True)
        g = Game(goal=4, size=2)
        self.assertEqual(g.loop(), None)

    # == .getCellStr == #

    def test_getCellStr_0(self):
        self.b.setCell(0, 0, 0)
        self.assertEqual(self.g.getCellStr(0, 0), '  .')

    def test_getCellStr_unknown_number(self):
        self.b.setCell(0, 0, 42)
        self.assertEqual(self.g.getCellStr(0, 0),
                '%s 42%s' % (Fore.RESET, Style.RESET_ALL))

    def test_getCellStr_0_azmode(self):
        g = Game(azmode=True)
        g.board.setCell(0, 0, 0)
        self.assertEqual(g.getCellStr(0, 0), '.')

    def test_getCellStr_2(self):
        g = Game()
        g.board.setCell(0, 0, 2)
        self.assertRegexpMatches(g.getCellStr(0, 0), r'  2\x1b\[0m$')

    def test_getCellStr_1k(self):
        g = Game()
        g.board.setCell(0, 0, 1024)
        self.assertRegexpMatches(g.getCellStr(0, 0), r' 1k\x1b\[0m$')

    def test_getCellStr_2k(self):
        g = Game()
        g.board.setCell(0, 0, 2048)
        self.assertRegexpMatches(g.getCellStr(0, 0), r' 2k\x1b\[0m$')

    def test_getCellStr_2_azmode(self):
        g = Game(azmode=True)
        g.board.setCell(0, 0, 2)
        self.assertRegexpMatches(g.getCellStr(0, 0), r'a\x1b\[0m$')

    def test_getCellStr_unknown_number_azmode(self):
        g = Game(azmode=True)
        g.board.setCell(0, 0, 42)
        self.assertEqual(g.getCellStr(0, 0), '?')

    # == .boardToString == #

    def test_boardToString_height_no_margins(self):
        s = self.g.boardToString()
        self.assertEqual(len(s.split("\n")), self.b.size())

    # == .__str__ == #

    def test_str_height_no_margins(self):
        s = str(self.g)
        self.assertEqual(len(s.split("\n")), self.b.size())

########NEW FILE########
__FILENAME__ = test_keypress
# -*- coding: UTF-8 -*-

import sys
import platform

if platform.python_version() < '3.0':
    from StringIO import StringIO
else:
    from io import StringIO

if platform.python_version() < '2.7':
    import unittest2 as unittest
else:
    import unittest

try:
    import termios as _termios
except ImportError:
    _termios = None

import helpers
from term2048 import keypress as kp
keypress = kp._getRealModule()

fno = sys.stdin.fileno()

class FakeStdin(StringIO):
    def fileno(self):
        return fno

class TestKeypress(unittest.TestCase):

    def _pushChars(self, *chars):
        """helper. Add chars in the fake stdin"""
        sys.stdin.write(''.join(map(chr, chars)))
        sys.stdin.seek(0)

    def _pushArrowKey(self, code):
        """helper. Add an arrow special key in the fake stdin"""
        self._pushChars(27, 91, code)

    def setUp(self):
        self.stdin = sys.stdin
        sys.stdin = FakeStdin()

    def tearDown(self):
        sys.stdin = self.stdin

    def test_getKey_read_stdin(self):
        x = 42
        self._pushChars(x)
        self.assertEqual(keypress.getKey(), x)

    def test_getKey_arrow_key_up(self):
        k = keypress.UP
        self._pushArrowKey(k)
        self.assertEqual(keypress.getKey(), k)

    def test_getKey_arrow_key_down(self):
        k = keypress.DOWN
        self._pushArrowKey(k)
        self.assertEqual(keypress.getKey(), k)

    def test_getKey_arrow_key_left(self):
        k = keypress.LEFT
        self._pushArrowKey(k)
        self.assertEqual(keypress.getKey(), k)

    def test_getKey_arrow_key_right(self):
        k = keypress.RIGHT
        self._pushArrowKey(k)
        self.assertEqual(keypress.getKey(), k)

    def test_getKey_vim_key_up(self):
        self._pushChars(keypress.K)
        self.assertEqual(keypress.getKey(), keypress.UP)

    def test_getKey_vim_key_down(self):
        self._pushArrowKey(keypress.J)
        self.assertEqual(keypress.getKey(), keypress.DOWN)

    def test_getKey_vim_key_left(self):
        self._pushArrowKey(keypress.H)
        self.assertEqual(keypress.getKey(), keypress.LEFT)

    def test_getKey_vim_key_right(self):
        self._pushArrowKey(keypress.L)
        self.assertEqual(keypress.getKey(), keypress.RIGHT)

class TestKeypressWindows(unittest.TestCase):

    def setUp(self):
        sys.modules['termios'] = None
        sys.modules['msvcrt'] = helpers.FakeMsvcrt()
        helpers.reload(keypress)

    def tearDown(self):
        sys.modules['termios'] = _termios

    def test_termios_fallback_on_msvcrt(self):
        self.assertEqual(keypress.UP, 72)

    def test_termios_fallback_on_msvcrt_getKey(self):
        self.assertEqual(keypress.getKey(), helpers.msvcrt_key)

########NEW FILE########
__FILENAME__ = test_ui
# -*- coding: UTF-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import sys
import os
import helpers
from term2048 import ui

try:
    import argparse as _argparse
except ImportError:
    _argparse = None

_argv = sys.argv
_os_system = os.system

class TestUI(unittest.TestCase):

    def setUp(self):
        self.exit_status = None
        def fake_exit(s):
            self.exit_status = s
            raise helpers.FakeExit()
        self.exit = sys.exit
        sys.exit = fake_exit
        sys.argv = _argv
        self.stdout = sys.stdout
        self.output = {}
        sys.stdout = helpers.DevNull(self.output)

    def tearDown(self):
        sys.exit = self.exit
        sys.stdout = self.stdout

    def test_print_version(self):
        try:
            ui.print_version_and_exit()
        except helpers.FakeExit:
            pass
        else:
            self.assertFalse(True, "should exit after printing the version")
        self.assertEqual(self.exit_status, 0)

    def test_print_rules(self):
        try:
            ui.print_rules_and_exit()
        except helpers.FakeExit:
            pass
        else:
            self.assertFalse(True, "should exit after printing the rules")
        self.assertEqual(self.exit_status, 0)

    def test_parse_args_no_args(self):
        sys.argv = ['term2048']
        args = ui.parse_cli_args()
        self.assertEqual(args, {
            'version': False,
            'azmode': False,
            'mode': None,
            'rules': False,
        })

    def test_parse_args_version(self):
        sys.argv = ['term2048', '--version']
        args = ui.parse_cli_args()
        self.assertTrue(args['version'])

    def test_parse_args_azmode(self):
        sys.argv = ['term2048', '--az']
        args = ui.parse_cli_args()
        self.assertTrue(args['azmode'])

    def test_parse_args_azmode_version(self):
        sys.argv = ['term2048', '--az', '--version']
        args = ui.parse_cli_args()
        self.assertTrue(args['azmode'])
        self.assertTrue(args['version'])

    def test_parse_args_rules_version(self):
        sys.argv = ['term2048', '--rules', '--version']
        args = ui.parse_cli_args()
        self.assertTrue(args['rules'])
        self.assertTrue(args['version'])

    def test_parse_args_dark_mode(self):
        m = 'dark'
        sys.argv = ['term2048', '--mode', m]
        args = ui.parse_cli_args()
        self.assertEqual(args['mode'], m)

    def test_parse_args_light_mode(self):
        m = 'light'
        sys.argv = ['term2048', '--mode', m]
        args = ui.parse_cli_args()
        self.assertEqual(args['mode'], m)

    def test_argparse_warning(self):
        getattr(ui, '__print_argparse_warning')()
        self.assertIn('output', self.output)
        self.assertRegexpMatches(self.output['output'], r'^WARNING')

    def test_start_game_print_version(self):
        sys.argv = ['term2048', '--version']
        try:
            ui.start_game()
        except helpers.FakeExit:
            pass
        else:
            self.assertFalse(True, "should exit after printing the version")
        self.assertEqual(self.exit_status, 0)
        self.assertRegexpMatches(self.output['output'],
                r'^term2048 v\d+\.\d+\.\d+$')

    def test_start_game_print_version_over_rules(self):
        sys.argv = ['term2048', '--rules', '--version']
        try:
            ui.start_game()
        except helpers.FakeExit:
            pass
        else:
            self.assertFalse(True, "should exit after printing the version")
        self.assertEqual(self.exit_status, 0)
        self.assertRegexpMatches(self.output['output'],
                r'^term2048 v\d+\.\d+\.\d+$')

    def test_start_game_print_rules(self):
        sys.argv = ['term2048', '--rules']
        try:
            ui.start_game()
        except helpers.FakeExit:
            pass
        else:
            self.assertFalse(True, "should exit after printing the version")
        self.assertEqual(self.exit_status, 0)
        self.assertRegexpMatches(self.output['output'],
                r'.+')

class TestUIPy26(unittest.TestCase):

    def setUp(self):
        self.stdout = sys.stdout
        self.output = {}
        sys.stdout = helpers.DevNull(self.output)
        sys.modules['argparse'] = None
        helpers.reload(ui)
        ui.debug = True
        def system_interrupt(*args):
            raise KeyboardInterrupt()
        os.system = system_interrupt

    def tearDown(self):
        sys.stdout = self.stdout
        sys.modules['argparse'] = _argparse
        ui.debug = False
        os.system = _os_system

    def test_no_has_argparse(self):
        self.assertFalse(getattr(ui, '__has_argparse'))

    def test_start_game_print_argparse_warning(self):
        ui.start_game()
        self.assertIn('output', self.output)
        self.assertRegexpMatches(self.output['output'], r'^WARNING')

    def test_start_game_loop(self):
        ui.debug = False
        self.assertEqual(ui.start_game(), None) # interrupted

########NEW FILE########
