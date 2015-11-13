__FILENAME__ = sunfish
#!/usr/bin/env pypy
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
from itertools import count
from collections import Counter, OrderedDict, namedtuple

# The table size is the maximum number of elements in the transposition table.
TABLE_SIZE = 1e6

# This constant controls how much time we spend on looking for optimal moves.
NODES_SEARCHED = 1e4

# Mate value must be greater than 8*queen + 2*(rook+knight+bishop)
# King value is set to twice this value such that if the opponent is
# 8 queens up, but we got the king, we still exceed MATE_VALUE.
MATE_VALUE = 30000

# Our board is represented as a 120 character string. The padding allows for
# fast detection of moves that don't stay within the board.
A1, H1, A8, H8 = 91, 98, 21, 28
initial = (
    '         \n'  #   0 -  9
    '         \n'  #  10 - 19
    ' rnbqkbnr\n'  #  20 - 29
    ' pppppppp\n'  #  30 - 39
    ' ........\n'  #  40 - 49
    ' ........\n'  #  50 - 59
    ' ........\n'  #  60 - 69
    ' ........\n'  #  70 - 79
    ' PPPPPPPP\n'  #  80 - 89
    ' RNBQKBNR\n'  #  90 - 99
    '         \n'  # 100 -109
    '          '   # 110 -119
)

###############################################################################
# Move and evaluation tables
###############################################################################

N, E, S, W = -10, 1, 10, -1
directions = {
    'P': (N, 2*N, N+W, N+E),
    'N': (2*N+E, N+2*E, S+2*E, 2*S+E, 2*S+W, S+2*W, N+2*W, 2*N+W),
    'B': (N+E, S+E, S+W, N+W),
    'R': (N, E, S, W),
    'Q': (N, E, S, W, N+E, S+E, S+W, N+W),
    'K': (N, E, S, W, N+E, S+E, S+W, N+W)
}

pst = {
    'P': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 198, 198, 198, 198, 198, 198, 198, 198, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 178, 198, 208, 218, 218, 208, 198, 178, 0,
        0, 178, 198, 218, 238, 238, 218, 198, 178, 0,
        0, 178, 198, 208, 218, 218, 208, 198, 178, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 198, 198, 198, 198, 198, 198, 198, 198, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'B': (
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 797, 824, 817, 808, 808, 817, 824, 797, 0,
        0, 814, 841, 834, 825, 825, 834, 841, 814, 0,
        0, 818, 845, 838, 829, 829, 838, 845, 818, 0,
        0, 824, 851, 844, 835, 835, 844, 851, 824, 0,
        0, 827, 854, 847, 838, 838, 847, 854, 827, 0,
        0, 826, 853, 846, 837, 837, 846, 853, 826, 0,
        0, 817, 844, 837, 828, 828, 837, 844, 817, 0,
        0, 792, 819, 812, 803, 803, 812, 819, 792, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'N': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 627, 762, 786, 798, 798, 786, 762, 627, 0,
        0, 763, 798, 822, 834, 834, 822, 798, 763, 0,
        0, 817, 852, 876, 888, 888, 876, 852, 817, 0,
        0, 797, 832, 856, 868, 868, 856, 832, 797, 0,
        0, 799, 834, 858, 870, 870, 858, 834, 799, 0,
        0, 758, 793, 817, 829, 829, 817, 793, 758, 0,
        0, 739, 774, 798, 810, 810, 798, 774, 739, 0,
        0, 683, 718, 742, 754, 754, 742, 718, 683, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'R': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'Q': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'K': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 60098, 60132, 60073, 60025, 60025, 60073, 60132, 60098, 0,
        0, 60119, 60153, 60094, 60046, 60046, 60094, 60153, 60119, 0,
        0, 60146, 60180, 60121, 60073, 60073, 60121, 60180, 60146, 0,
        0, 60173, 60207, 60148, 60100, 60100, 60148, 60207, 60173, 0,
        0, 60196, 60230, 60171, 60123, 60123, 60171, 60230, 60196, 0,
        0, 60224, 60258, 60199, 60151, 60151, 60199, 60258, 60224, 0,
        0, 60287, 60321, 60262, 60214, 60214, 60262, 60321, 60287, 0,
        0, 60298, 60332, 60273, 60225, 60225, 60273, 60332, 60298, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
}


###############################################################################
# Chess logic
###############################################################################

class Position(namedtuple('Position', 'board score wc bc ep kp')):
    """ A state of a chess game
    board -- a 120 char representation of the board
    score -- the board evaluation
    wc -- the castling rights
    bc -- the opponent castling rights
    ep - the en passant square
    kp - the king passant square
    """

    def genMoves(self):
        # For each of our pieces, iterate through each possible 'ray' of moves,
        # as defined in the 'directions' map. The rays are broken e.g. by
        # captures or immediately in case of pieces such as knights.
        for i, p in enumerate(self.board):
            if not p.isupper(): continue
            for d in directions[p]:
                for j in count(i+d, d):
                    q = self.board[j]
                    # Stay inside the board
                    if self.board[j].isspace(): break
                    # Castling
                    if i == A1 and q == 'K' and self.wc[0]: yield (j, j-2)
                    if i == H1 and q == 'K' and self.wc[1]: yield (j, j+2)
                    # No friendly captures
                    if q.isupper(): break
                    # Special pawn stuff
                    if p == 'P' and d in (N+W, N+E) and q == '.' and j not in (self.ep, self.kp): break
                    if p == 'P' and d in (N, 2*N) and q != '.': break
                    if p == 'P' and d == 2*N and (i < A1+N or self.board[i+N] != '.'): break
                    # Move it
                    yield (i, j)
                    # Stop crawlers from sliding
                    if p in ('P', 'N', 'K'): break
                    # No sliding after captures
                    if q.islower(): break

    def rotate(self):
        return Position(
            self.board[::-1].swapcase(), -self.score,
            self.bc, self.wc, 119-self.ep, 119-self.kp)

    def move(self, move):
        i, j = move
        p, q = self.board[i], self.board[j]
        put = lambda board, i, p: board[:i] + p + board[i+1:]
        # Copy variables and reset ep and kp
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        score = self.score + self.value(move)
        # Actual move
        board = put(board, j, board[i])
        board = put(board, i, '.')
        # Castling rights
        if i == A1: wc = (False, wc[1])
        if i == H1: wc = (wc[0], False)
        if j == A8: bc = (bc[0], False)
        if j == H8: bc = (False, bc[1])
        # Castling
        if p == 'K':
            wc = (False, False)
            if abs(j-i) == 2:
                kp = (i+j)//2
                board = put(board, A1 if j < i else H1, '.')
                board = put(board, kp, 'R')
        # Special pawn stuff
        if p == 'P':
            if A8 <= j <= H8:
                board = put(board, j, 'Q')
            if j - i == 2*N:
                ep = i + N
            if j - i in (N+W, N+E) and q == '.':
                board = put(board, j+S, '.')
        # We rotate the returned position, so it's ready for the next player
        return Position(board, score, wc, bc, ep, kp).rotate()

    def value(self, move):
        i, j = move
        p, q = self.board[i], self.board[j]
        # Actual move
        score = pst[p][j] - pst[p][i]
        # Capture
        if q.islower():
            score += pst[q.upper()][j]
        # Castling check detection
        if abs(j-self.kp) < 2:
            score += pst['K'][j]
        # Castling
        if p == 'K' and abs(i-j) == 2:
            score += pst['R'][(i+j)//2]
            score -= pst['R'][A1 if j < i else H1]
        # Special pawn stuff
        if p == 'P':
            if A8 <= j <= H8:
                score += pst['Q'][j] - pst['P'][j]
            if j == self.ep:
                score += pst['P'][j+S]
        return score

Entry = namedtuple('Entry', 'depth score gamma move')
tp = OrderedDict()


###############################################################################
# Search logic
###############################################################################

nodes = 0
def bound(pos, gamma, depth):
    """ returns s(pos) <= r < gamma    if s(pos) < gamma
        returns s(pos) >= r >= gamma   if s(pos) >= gamma """
    global nodes; nodes += 1

    # Look in the table if we have already searched this position before.
    # We use the table value if it was done with at least as deep a search
    # as ours, and the gamma value is compatible.
    entry = tp.get(pos)
    if entry is not None and entry.depth >= depth and (
            entry.score < entry.gamma and entry.score < gamma or
            entry.score >= entry.gamma and entry.score >= gamma):
        return entry.score

    # Stop searching if we have won/lost.
    if abs(pos.score) >= MATE_VALUE:
        return pos.score

    # Null move. Is also used for stalemate checking
    nullscore = -bound(pos.rotate(), 1-gamma, depth-3) if depth > 0 else pos.score
    #nullscore = -MATE_VALUE*3 if depth > 0 else pos.score
    if nullscore >= gamma:
        return nullscore

    # We generate all possible, pseudo legal moves and order them to provoke
    # cuts. At the next level of the tree we are going to minimize the score.
    # This can be shown equal to maximizing the negative score, with a slightly
    # adjusted gamma value.
    best, bmove = -3*MATE_VALUE, None
    for move in sorted(pos.genMoves(), key=pos.value, reverse=True):
        # We check captures with the value function, as it also contains ep and kp
        if depth <= 0 and pos.value(move) < 150:
            break
        score = -bound(pos.move(move), 1-gamma, depth-1)
        if score > best:
            best = score
            bmove = move
        if score >= gamma:
            break

    # If there are no captures, or just not any good ones, stand pat
    if depth <= 0 and best < nullscore:
        return nullscore
    # Check for stalemate. If best move loses king, but not doing anything
    # would save us. Not at all a perfect check.
    if depth > 0 and best <= -MATE_VALUE is None and nullscore > -MATE_VALUE:
        best = 0

    # We save the found move together with the score, so we can retrieve it in
    # the play loop. We also trim the transposition table in FILO order.
    # We prefer fail-high moves, as they are the ones we can build our pv from.
    if entry is None or depth >= entry.depth and best >= gamma:
        tp[pos] = Entry(depth, best, gamma, bmove)
        if len(tp) > TABLE_SIZE:
            tp.pop()
    return best


def search(pos, maxn=NODES_SEARCHED):
    """ Iterative deepening MTD-bi search """
    global nodes; nodes = 0

    # We limit the depth to some constant, so we don't get a stack overflow in
    # the end game.
    for depth in range(1, 99):
        # The inner loop is a binary search on the score of the position.
        # Inv: lower <= score <= upper
        # However this may be broken by values from the transposition table,
        # as they don't have the same concept of p(score). Hence we just use
        # 'lower < upper - margin' as the loop condition.
        lower, upper = -3*MATE_VALUE, 3*MATE_VALUE
        while lower < upper - 3:
            gamma = (lower+upper+1)//2
            score = bound(pos, gamma, depth)
            if score >= gamma:
                lower = score
            if score < gamma:
                upper = score
        
        # print("Searched %d nodes. Depth %d. Score %d(%d/%d)" % (nodes, depth, score, lower, upper))

        # We stop deepening if the global N counter shows we have spent too
        # long, or if we have already won the game.
        if nodes >= maxn or abs(score) >= MATE_VALUE:
            break

    # If the game hasn't finished we can retrieve our move from the
    # transposition table.
    entry = tp.get(pos)
    if entry is not None:
        return entry.move, score
    return None, score


###############################################################################
# User interface
###############################################################################

# Python 2 compatability
if sys.version_info[0] == 2:
    input = raw_input


def parse(c):
    fil, rank = ord(c[0]) - ord('a'), int(c[1]) - 1
    return A1 + fil - 10*rank


def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord('a')) + str(-rank + 1)


def main():
    pos = Position(initial, 0, (True,True), (True,True), 0, 0)
    while True:
        # We add some spaces to the board before we print it.
        # That makes it more readable and pleasing.
        print(' '.join(pos.board))

        # We query the user until she enters a legal move.
        move = None
        while move not in pos.genMoves():
            crdn = input("Your move: ")
            move = parse(crdn[0:2]), parse(crdn[2:4])
        pos = pos.move(move)

        # After our move we rotate the board and print it again.
        # This allows us to see the effect of our move.
        print(' '.join(pos.rotate().board))

        # Fire up the engine to look for a move.
        move, score = search(pos)
        if score <= -MATE_VALUE:
            print("You won")
            break
        if score >= MATE_VALUE:
            print("You lost")
            break

        # The black player moves from a rotated position, so we have to
        # 'back rotate' the move before printing it.
        print("My move:", render(119-move[0]) + render(119-move[1]))
        pos = pos.move(move)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env pypy
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import re
import time
import subprocess
import functools
import os
import signal

import sunfish
import xboard

###############################################################################
# Playing test
###############################################################################

def selfplay():
    """ Start a game sunfish vs. sunfish """
    pos = xboard.parseFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    for d in range(200):
        # Always print the board from the same direction
        board = pos.board if d % 2 == 0 else pos.rotate().board
        print(' '.join(board))

        m, _ = sunfish.search(pos, maxn=200)
        if m is None:
            print("Game over")
            break
        print("\nmove", xboard.mrender(d%2, pos, m))
        pos = pos.move(m)

###############################################################################
# Test Xboard
###############################################################################

class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)

def testxboard(python='python3'):
    print('Xboard test \'%s\'' % python)
    fish = subprocess.Popen([python, '-u', 'xboard.py'],
       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
       universal_newlines=True)

    def waitFor(regex):
        with timeout(20, '%s was never encountered'%regex):
            while True:
                line = fish.stdout.readline()
                # print("Saw lines", line)
                if re.search(regex, line):
                    return

    try:
        print('xboard', file=fish.stdin)
        print('protover 2', file=fish.stdin)
        waitFor('done\s*=\s*1')

        print('usermove e2e4', file=fish.stdin)
        waitFor('move ')

        print('setboard rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1', file=fish.stdin)
        print('usermove e7e5', file=fish.stdin)
        waitFor('move ')

        print('quit', file=fish.stdin)
        with timeout(5, 'quit did not terminate sunfish'):
            fish.wait()
    finally:
        if fish.poll() is None:
            fish.kill()

###############################################################################
# Perft test
###############################################################################

def allperft(path, depth=4):
    for d in range(1, depth+1):
        print("Going to depth %d" % d)
        with open(path) as f:
            for line in f:
                parts = line.split(';')
                print(parts[0])

                pos, score = xboard.parseFEN(parts[0]), int(parts[d])
                res = perft(pos, d)
                if res != score:
                    print('=========================================')
                    print("ERROR at depth %d. Gave %d rather than %d" % (d, res, score))
                    print('=========================================')
                    if d == 1:
                        print(pos)
                    perft(pos, d, divide=True)
                    return
        print('')

def perft(pos, depth, divide=False):
    if depth == 0:
        return 1
    res = 0
    for m in pos.genMoves():
        pos1 = pos.move(m)
        # Make sure the move was legal
        if not any(pos1.value(m) >= sunfish.MATE_VALUE for m in pos1.genMoves()):
            sub = perft(pos1, depth-1, False)
            if divide:
                print(" "*depth+xboard.mrender(m), sub)
            res += sub
    return res


###############################################################################
# Find mate test
###############################################################################

def allmate(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            print(line)

            pos = xboard.parseFEN(line)
            _, score = sunfish.search(pos, maxn=1e9)
            if score < sunfish.MATE_VALUE:
                print("Unable to find mate. Only got score = %d" % score)
                break

def quickdraw(path, depth):
    with open(path) as f:
        for line in f:
            line = line.strip()
            print(line)

            pos = xboard.parseFEN(line)
            for d in range(depth, 99):
                s0 = sunfish.bound(pos, 0, d)
                s1 = sunfish.bound(pos, 1, d)
                if s0 >= 0 and s1 < 1:
                    break
                print(d, s0, s1, xboard.pv(0, pos))
            else:
                print("Fail: Unable to find draw!")
                return

def quickmate(path, depth):
    """ Similar to allmate, but uses the `bound` function directly to only
    search for moves that will win us the game """
    with open(path) as f:
        for line in f:
            line = line.strip()
            print(line)

            pos = xboard.parseFEN(line)
            for d in range(depth, 99):
                score = sunfish.bound(pos, sunfish.MATE_VALUE, d)
                if score >= sunfish.MATE_VALUE:
                    break
                print(d, score)
            else:
                print("Unable to find mate. Only got score = %d" % score)
                return

###############################################################################
# Best move test
###############################################################################

def renderSAN(pos, move):
    # TODO: How do we simply make this work for black as well?
    i, j = move
    csrc, cdst = sunfish.render(i), sunfish.render(j)
    # Check
    pos1 = pos.move(move)
    cankill = lambda p: any(p.board[b]=='k' for a,b in p.genMoves())
    check = ''
    if cankill(pos1.rotate()):
        check = '+'
        if all(cankill(pos1.move(move1)) for move1 in pos1.genMoves()):
            check = '#'
    # Castling
    if pos.board[i] == 'K' and csrc == 'e1' and cdst in ('c1','g1'):
        if cdst == 'c1':
            return 'O-O-O' + check
        return 'O-O' + check
    # Pawn moves
    if pos.board[i] == 'P':
        pro = '=Q' if cdst[1] == '8' else ''
        cap = csrc[0] + 'x' if pos.board[j] != '.' or j == pos.ep else ''
        return cap + cdst + pro + check
    # Normal moves
    p = pos.board[i]
    srcs = [a for a,b in pos.genMoves() if pos.board[a] == p and b == j]
    # TODO: We can often get away with just sending the rank or file here.
    src = csrc if len(srcs) > 1 else ''
    cap = 'x' if pos.board[j] != '.' else ''
    return p + src + cap + cdst + check

def parseSAN(pos, color, msan):
    # Normal moves
    normal = re.match('([KQRBN])([a-h])?([1-8])?x?([a-h][1-8])', msan)
    if normal:
        p, fil, rank, dst = normal.groups()
        src = (fil or '[a-h]')+(rank or '[1-8]')
    # Pawn moves
    pawn = re.match('([a-h])?x?([a-h][1-8])', msan)
    if pawn:
        p, (fil, dst) = 'P', pawn.groups()
        src = (fil or '[a-h]')+'[1-8]'
    # Castling
    if msan == "O-O-O":
        p, src, dst = 'K', 'e1|d1', 'c1|f1'
    if msan == "O-O":
        p, src, dst = 'K', 'e1|d1', 'g1|b1'
    # Find possible match
    for i, j in pos.genMoves():
        # TODO: Maybe check for check here?
        csrc, cdst = sunfish.render(i), sunfish.render(j)
        if pos.board[i] == p and re.match(dst, cdst) and re.match(src, csrc):
            return (i, j)

def parseEPD(epd):
    parts = epd.strip('\n ;').replace('"','').split(maxsplit=6)
    fen = ' '.join(parts[:6])
    opts = dict(p.split(maxsplit=1) for p in parts[6].split(';'))
    return fen, opts

def findbest(path, times):
    print('Calibrating search speed...')
    pos = xboard.parseFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    CAL_NODES = 10000
    start = time.time()
    _ = sunfish.search(pos, CAL_NODES)
    factor = CAL_NODES/(time.time()-start)

    print('Running benchmark with %.1f nodes per second...' % factor)
    print('-'*60)
    totalpoints = 0
    totaltests = 0
    with open(path) as f:
        for k, line in enumerate(f):
            fen, opts = parseEPD(line)
            pos = xboard.parseFEN(fen)
            color = 0 if fen.split()[1] == 'w' else 1
            # am -> avoid move; bm -> best move
            am = parseSAN(pos,color,opts['am']) if 'am' in opts else None
            bm = parseSAN(pos,color,opts['bm']) if 'bm' in opts else None
            points = 0
            print(opts['id'], end=' ', flush=True)
            for t in times:
                move, _ = sunfish.search(pos, factor*t)
                mark = renderSAN(pos, move)
                if am and move != am or bm and move == bm:
                    mark += '(1)'
                    points += 1
                    totalpoints += 1
                else:
                    mark += '(0)'
                print(mark, end=' ', flush=True)
                totaltests + 1
            print(points)
    print('-'*60)
    print('Total Points: %d/%d', totalpoints, totaltests)

# Python 2 compatability
if sys.version_info[0] == 2:
    input = raw_input

if __name__ == '__main__':
    allperft('tests/queen.fen', depth=3)
    quickmate('tests/mate1.fen', 3)
    quickmate('tests/mate2.fen', 5)
    quickmate('tests/mate3.fen', 7)
    testxboard('python')
    testxboard('python3')
    testxboard('pypy')
    # findbest('tests/ccr_one_hour_test.epd', [15, 30, 60, 120])
    # findbest('tests/bratko_kopec_test.epd', [15, 30, 60, 120])
    # quickdraw('tests/stalemate2.fen', 3)
    # selfplay()

########NEW FILE########
__FILENAME__ = xboard
#!/usr/bin/env pypy -u
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import division
import re
import sys
import sunfish

# Python 2 compatability
if sys.version_info[0] == 2:
	input = raw_input

# Sunfish doesn't know about colors. We hav to.
WHITE, BLACK = range(2)
FEN_INITIAL = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


def parseFEN(fen):
	""" Parses a string in Forsyth-Edwards Notation into a Position """
	board, color, castling, enpas, hclock, fclock = fen.split()
	board = re.sub('\d', (lambda m: '.'*int(m.group(0))), board)
	board = ' '*19+'\n ' + '\n '.join(board.split('/')) + ' \n'+' '*19
	wc = ('Q' in castling, 'K' in castling)
	bc = ('k' in castling, 'q' in castling)
	ep = sunfish.parse(enpas) if enpas != '-' else 0
	score = sum(sunfish.pst[p][i] for i,p in enumerate(board) if p.isupper())
	score -= sum(sunfish.pst[p.upper()][i] for i,p in enumerate(board) if p.islower())
	pos = sunfish.Position(board, score, wc, bc, ep, 0)
	return pos if color == 'w' else pos.rotate()

def mrender(color, pos, m):
	# Sunfish always assumes promotion to queen
	p = 'q' if sunfish.A8 <= m[1] <= sunfish.H8 and pos.board[m[0]] == 'P' else ''
	m = m if color == WHITE else (119-m[0], 119-m[1])
	return sunfish.render(m[0]) + sunfish.render(m[1]) + p

def mparse(color, move):
	m = (sunfish.parse(move[0:2]), sunfish.parse(move[2:4]))
	return m if color == WHITE else (119-m[0], 119-m[1])

def pv(color, pos):
	res = []
	origc = color
	res.append(str(pos.score))
	while True:
		entry = sunfish.tp.get(pos)
		if entry is None:
			break
		if entry.move is None:
			res.append('null')
			break
		move = mrender(color,pos,entry.move)
		if move in res:
			res.append(move)
			res.append('loop')
			break
		res.append(move)
		pos, color = pos.move(entry.move), 1-color
		res.append(str(pos.score if color==origc else -pos.score))
	return ' '.join(res)

def main():
	pos = parseFEN(FEN_INITIAL)
	forced = False
	color = WHITE
	time, otim = 1, 1

	stack = []
	while True:
		if stack:
			smove = stack.pop()
		else: smove = input()

		if smove == 'quit':
			break

		elif smove == 'protover 2':
			print('feature done=0')
			print('feature myname="Sunfish"')
			print('feature usermove=1')
			print('feature setboard=1')
			print('feature ping=1')
			print('feature sigint=0')
			print('feature variants="normal"')
			print('feature done=1')

		elif smove == 'new':
			stack.append('setboard ' + FEN_INITIAL)

		elif smove.startswith('setboard'):
			_, fen = smove.split(' ', 1)
			pos = parseFEN(fen)
			color = WHITE if fen.split()[1] == 'w' else BLACK

		elif smove == 'force':
			forced = True

		elif smove == 'go':
			forced = False

			# Let's follow the clock of our opponent
			nodes = 2e4
			if time > 0 and otim > 0: nodes *= time/otim
			m, s = sunfish.search(pos, maxn=nodes)
			# We don't play well once we have detected our death
			if s <= -sunfish.MATE_VALUE:
				print('resign')
			else:
				print('# %d %+d %d %d %s' % (0, s, 0, sunfish.nodes, pv(color,pos)))
				print('move', mrender(color, pos, m))
				print('score before %d after %+d' % (pos.score, pos.value(m)))
				pos = pos.move(m)
				color = 1-color

		elif smove.startswith('ping'):
			_, N = smove.split()
			print('pong', N)

		elif smove.startswith('usermove'):
			_, smove = smove.split()
			m = mparse(color, smove)
			pos = pos.move(m)
			color = 1-color
			if not forced:
				stack.append('go')

		elif smove.startswith('time'):
			time = int(smove.split()[1])
		
		elif smove.startswith('otim'):
			otim = int(smove.split()[1])

		elif any(smove.startswith(x) for x in ('xboard','post','random','hard','accepted','level')):
			pass

		else:
			print("Error (unkown command):", smove)

if __name__ == '__main__':
	main()

########NEW FILE########
