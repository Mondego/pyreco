__FILENAME__ = bayes_net
from types import FloatType


class Event:
    def __init__(self, conditions, p):
        self.conditions = conditions
        self.p = p
    
    def check(self, given):
        for event, value in given.iteritems():
            if self.conditions[event] != value:
                return False
        return True
    
    def __str__(self):
        return "%s: %.4f" % (self.conditions, self.p)


class BayesNetwork:
    def __init__(self, net):
        self.events = [Event({}, 1.0)]
        for name, probabilities in net:
            new_events = []
            for e in self.events:
                if type(probabilities) is FloatType:
                    p_true = probabilities
                else:
                    for given, p in probabilities:
                        if e.check(given):
                            p_true = p
                
                et_conditions = dict(e.conditions)
                et_conditions[name] = True
                et_p = e.p * p_true
                new_events.append(Event(et_conditions, et_p))
                
                ef_conditions = dict(e.conditions)
                ef_conditions[name] = False
                ef_p = e.p * (1.0 - p_true)
                new_events.append(Event(ef_conditions, ef_p))
            self.events = new_events
    
    def P(self, event, given):
        p_true = 0.0
        p_false = 0.0
        for e in self.events:
            if e.check(given):
                if e.check(event):
                    p_true += e.p
                else:
                    p_false += e.p
        return p_true / (p_true + p_false)


# "pretty" print of probability queries
SYM = {True:"", False:"-"}
def describe(e):
    return ','.join([SYM[value]+name for name, value in e.iteritems()])

def P(n, event, given={}, expected=None):
    p = n.P(event, given)
    
    description = describe(event)
    if given:
        description += "|" + describe(given)
    
    print "P(%s) = %.4f" % (description, p)
    
    if expected is not None:
        if abs(p - expected) > 0.001:
            raise Exception("Error evaluating P(%s): %.4f != %.4f" % (description, p, expected))

########NEW FILE########
__FILENAME__ = examples
from BayesNetworks.bayes_net import BayesNetwork, P

print "\n=== Cancer Test ==="
CANCER_TEST = (
    ({"C":True}, 0.9),
    ({"C":False}, 0.2)
)
CANCER_NET = (
    ("C", 0.01),
    ("T1", CANCER_TEST),
    ("T2", CANCER_TEST),
)
n = BayesNetwork(CANCER_NET)
P(n, {"C":True}, {"T1":True})
P(n, {"C":True}, {"T1":True, "T2":True})
P(n, {"C":True}, {"T1":True, "T2":False})


print "\n=== Happiness ==="
HAPPY_NET = (
    ("S", 0.7),
    ("R", 0.01),
    ("H", (
        ({"S":True , "R":True }, 1.0),
        ({"S":False, "R":True }, 0.9),
        ({"S":True , "R":False}, 0.7),
        ({"S":False, "R":False}, 0.1),
    ))
)
n = BayesNetwork(HAPPY_NET)
P(n, {"R":True}, {"H":True, "S":True})
P(n, {"R":True}, {"H":True})
P(n, {"R":True}, {"H":True, "S":False})


print "\n=== Alarm ==="
ALARM_NET = (
    ("B", 0.001),
    ("E", 0.002),
    ("A", (
        ({"B":True , "E":True }, 0.95),
        ({"B":True , "E":False}, 0.94),
        ({"B":False, "E":True }, 0.29),
        ({"B":False, "E":False}, 0.001),
    )),
    ("J", (
        ({"A":True} , 0.90),
        ({"A":False}, 0.05)
    )),
    ("M", (
        ({"A":True }, 0.70),
        ({"A":False}, 0.01)
    )),
)
n = BayesNetwork(ALARM_NET)
P(n, {"J":True, "M":True, "A":True, "B":False, "E":False}, {})
P(n, {"B":True}, {"J":True, "M":True})


print "\n=== Wet Grass ==="
GRASS_NET = (
    ("C", 0.5),
    ("S", (
        ({"C":True} , 0.10),
        ({"C":False}, 0.50)
    )),
    ("R", (
        ({"C":True} , 0.80),
        ({"C":False}, 0.20)
    )),
    ("W", (
        ({"S":True , "R":True }, 0.99),
        ({"S":True , "R":False}, 0.90),
        ({"S":False, "R":True }, 0.90),
        ({"S":False, "R":False}, 0.00),
    )),
)
n = BayesNetwork(GRASS_NET)
P(n, {"C":True}, {})
P(n, {"S":True}, {"C":True})
P(n, {"R":True}, {"C":True})
P(n, {"W":True}, {"S":False, "R":True})
P(n, {"R":True}, {"S":True})
P(n, {"W":True}, {"C":True, "R":True, "S":False})


print "\n=== Traffic ==="
TRAFFIC_NET = (
    ("R", 0.1),
    ("T", (
        ({"R":True} , 0.8),
        ({"R":False}, 0.1)
    )),
    ("L", (
        ({"T":True} , 0.3),
        ({"T":False}, 0.1)
    )),
)
n = BayesNetwork(TRAFFIC_NET)
P(n, {"T":True}, {})
P(n, {"T":True, "L":True}, {})
P(n, {"T":True, "L":False}, {})
P(n, {"T":False, "L":True}, {})
P(n, {"T":False, "L":False}, {})
P(n, {"L":True}, {})
P(n, {"L":False}, {})

########NEW FILE########
__FILENAME__ = homework_2
from BayesNetworks.bayes_net import BayesNetwork, P


print "\n=== Homework 2.1 ==="
HOMEWORK_1 = (
    ("A", 0.5),
    ("B", (
        ({"A":True}, 0.2),
        ({"A":False}, 0.8)
    )),
)
n = BayesNetwork(HOMEWORK_1)
P(n, {"A":True}, {"B":True})


TEST = (
    ({"A":True}, 0.2),
    ({"A":False}, 0.6)
)
HOMEWORK_2 = (
    ("A", 0.5),
    ("X1", TEST),
    ("X2", TEST),
    ("X3", TEST),
)
n = BayesNetwork(HOMEWORK_2)

print "\n=== Homework 2.2 ==="
P(n, {"A":True }, {"X1":True, "X2":True, "X3":False})

print "\n=== Homework 2.3 ==="
P(n, {"X3":True}, {"X1":True})
########NEW FILE########
__FILENAME__ = examples
from numpy import array
from ComputerVision.filters import linear_filter, linear_filter_hw

image = array([
    [255,   7,   3],
    [212, 240,   4],
    [218, 216, 230],
])
print linear_filter(image, ((0,1),(-1, 1)))

image = array([
    [ 12,  18,   6],
    [  2,   1,   7],
    [100, 140, 130],
])
print linear_filter(image, ((1,0), (-1, 1)))

image = array([
    [2,   0,   2],
    [4, 100, 102],
    [2,   4,   2],
])
print linear_filter_hw(image, (-1, 0, 1))
########NEW FILE########
__FILENAME__ = filters
from numpy import zeros


def linear_filter(image, kernel):
    (shift_x, shift_y), (a, b) = kernel
    rows, columns = image.shape
    f_rows, f_columns = (rows - shift_x), (columns - shift_y)
    gi = zeros((f_rows, f_columns))
    for i in range(f_rows):
        for j in range(f_columns):
            gi[i][j] = a*image[i][j] + b*image[i+shift_x][j+shift_y]
    return gi


def linear_filter_hw(image, g):
    rows, columns = image.shape
    gl = len(g)
    offset = (gl+(gl%2))/2 - 1
    gi = zeros((rows, columns))
    for i in range(rows):
        for j in range(columns):
            for u in range(gl):
                x = (j-offset+u)
                if x < 0 or x > (columns-1):
                    pixel = 0
                else:
                    pixel = image[i][x]
                gi[i][j] += pixel * g[u]
    return gi
########NEW FILE########
__FILENAME__ = final
from Logic.logic import Proposition, implies

def A(p, g): return p
def B(p, g): return (p or g)
def C(p, g): return (p and g)
def D(p, g): return implies((not p), g)

PROPOSITIONS = [A, B, C, D]
for p1 in PROPOSITIONS:
    for p2 in PROPOSITIONS:
        print Proposition(
            lambda p, g: implies(p1(p, g), p2(p, g)),
            "%s => %s" % (p1.__name__, p2.__name__)
        ).satisfiability_report()

########NEW FILE########
__FILENAME__ = homework_6
from Markov.markov import TransProb, MarkovChain, MarkovModel

print "\n=== Homework 6.1 ==="
OBSERVATIONS = (
    ("A", "B", "C", "A", "B", "C"),
    ("A", "A", "B", "B", "C", "C"),
    ("A", "A", "A", "C", "C", "C")
)
t = TransProb(OBSERVATIONS)
t.report()

print "\n=== Homework 6.2 ==="
CHAIN = ("A", 1.0, {True: 0.9, False: 0.5})
c = MarkovChain(CHAIN)
print "stationary distribution: P(A) = %.4f" % c.stationary_distribution(True)
print "stationary distribution: P(B) = %.4f" % c.stationary_distribution(False)

print "\n=== Homework 6.3 ==="
MODEL = ("A", 0.5, {True: 0.5, False: 0.5}, "X", {True: 0.1, False: 0.8})
m = MarkovModel(MODEL)
m.p({"A0":True}, {"X0":True})
m.p({"A1":True}, {"X0":True})
m.p({"A1":True}, {"X0":True, "X1":True})

print "\n=== Homework 6.11 ==="
from Game.game import Game
HW6_11 = {
    "players": (
        ("B", "d", "e", "f"),
        ("A", "a", "b", "c")
    ),
    "matrix": (
        ((3,3), (5,0), (2,1)),
        ((2,4), (7,8), (4,6)),
        ((7,5), (8,5), (5,3)),
    )
}
g = Game(HW6_11)
print "Dominant strategy for A: %s" % g.dominant_strategy("A")
print "Dominant strategy for B: %s" % g.dominant_strategy("B")
print "Equilibrium Points: %s" % str(g.equilibrium())

########NEW FILE########
__FILENAME__ = midterm
print "\n=== Problem 2 ==="
from ProblemSolving.search import generate_state_space, AStarSearch

GRAPH = [
    ( "1",  "2", 10), ( "1",  "3", 10), ( "1",  "4", 10), ( "1",  "5", 10),
    ( "1",  "6", 10), ( "2",  "7", 10), ( "3",  "8", 10), ( "3",  "9", 10),
    ( "5", "10", 10), ( "5", "11", 10), ( "6", "12", 10), ("11", "12", 10),
]
HEURISTIC = {
     "1": 15, "2": 11,  "3": 8, "4": 7, "5": 6, "6": 10, "7": 2, "8": 3, "9": 9,
    "10": 5, "11": 20, "12": 0,
}
alg = AStarSearch(generate_state_space(GRAPH))
path, iterations = alg.search("1", "12", HEURISTIC, debug=True)
print "Found path in %d iterations: %s" % (iterations, path)

print "\n=== Problem 5 ==="
from BayesNetworks.bayes_net import BayesNetwork, P
COIN_NET = (
    ("F", 0.5),
    ("H1", (
        ({"F":True}, 0.5),
        ({"F":False}, 1.0)
    )),
    ("H2", (
        ({"F":True}, 0.5),
        ({"F":False}, 1.0)
    )),
)
n = BayesNetwork(COIN_NET)
P(n, {"F":False}, {"H1":True})
P(n, {"F":False}, {"H1":True, "H2":True})

print "\n=== Problem 7 ==="
TEST_NET = (
    ("A", 0.5),
    ("B", (
        ({"A":True}, 0.2),
        ({"A":False}, 0.2)
    )),
    ("C", (
        ({"A":True}, 0.8),
        ({"A":False}, 0.4)
    )),
)
n = BayesNetwork(TEST_NET)
P(n, {"B":True}, {"C":True})
P(n, {"C":True}, {"B":True})

print "\n=== Problem 8 ==="
from MachineLearning.bayes import NaiveBayesClassifier, result
SPAM = (
    "Top Gun",
    "Shy People",
    "Top Hat",
)
HAM = (
    "Top Gear",
    "Gun Shy",
)
c = NaiveBayesClassifier(SPAM, HAM, 1)
result("OLD", c.spam.p)
result("Top|OLD", c.spam.p_word("Top"))
result("OLD|Top", c.p_spam_given_word("Top"))


print "\n=== Problem 10 ==="
from MachineLearning.linear_regression import linear_regression, gaussian
x = [1.0, 3.0, 4.0, 5.0,  9.0]
y = [2.0, 5.2, 6.8, 8.4, 14.8]
(w0, w1), err = linear_regression(x, y)
print "(w0=%.1f, w1=%.1f) err=%.2f" % (w0, w1, err)


print "\n=== Problem 12 ==="
from Logic.logic import Proposition, implies
print Proposition(
    lambda a: not a,
             "not a"
).satisfiability_report()
print Proposition(
    lambda a: a or (not a),
             "a or (not a)"
).satisfiability_report()
print Proposition(
    lambda a, b, c: implies((a and (not a)), implies(b, c)),
                   "(a and (not a)) => (b => c)"
).satisfiability_report()
print Proposition(
    lambda a, b, c: implies(a, b) and implies(b, c) and implies(c, a),
                    "(a => b) and (b => c) and (c => a)"
).satisfiability_report()
print Proposition(
    lambda a, b, c: implies(a, b) and (not ((not a) or b)),
                    "(a => b) and (not ((not a) or b))"
).satisfiability_report()
print Proposition(
    lambda a, b, c: (implies(a, b) or implies(b, c)) == implies(a, c),
                    "((a => b) and (b => c)) == (a => c)"
).satisfiability_report()


print "\n=== Problem 14 ==="
from MDP.grid import GridWorld
GRID = [[0, 0, None, 100],
        [0, 0,    0,   0]]

PROB = {
    'S':(('S', 1.0), ),
    'N':(('N', 1.0), ),
    'E':(('E', 1.0), ),
    'W':(('W', 1.0), ),
}

STATES = ((1,3),(1,2),(1,1),(0,1),(1,0),(0,0))
g = GridWorld(GRID, PROB, STATES, 1, -5)
i = g.value_iteration(0.1)
print "Values after %d iterations:" % i
print g

print "\n=== Problem 15 ==="
from Markov.markov import TransProb
TRANSITIONS = [("A","A","A","A","B")]
t = TransProb(TRANSITIONS)
t.report(k=1)

########NEW FILE########
__FILENAME__ = example
from Game.game import Game

PRISONER_DILEMMA = {
    "players": (
        ("A", "testify", "refuse"),
        ("B", "testify", "refuse")
    ),
    "matrix": (
        ((-5, -5), (-10,0)),
        (( 0,-10), (-1,-1))
    )
}
g = Game(PRISONER_DILEMMA)
print "Dominant strategy for A: %s" % g.dominant_strategy("A")
print "Dominant strategy for B: %s" % g.dominant_strategy("B")
print "Equilibrium Points: %s" % str(g.equilibrium())


CONSOLE_GAME = {
    "players": (
        ("A", "blu", "dvd"),
        ("B", "blu", "dvd")
    ),
    "matrix": (
        (( 9, 9), (-4,-1)),
        ((-3,-1), ( 5, 5))
    )
}
g = Game(CONSOLE_GAME)
print "Dominant strategy for A: %s" % g.dominant_strategy("A")
print "Dominant strategy for B: %s" % g.dominant_strategy("B")
print "Equilibrium Points: %s" % str(g.equilibrium())
########NEW FILE########
__FILENAME__ = game
class Game:
    def __init__(self, game):
        matrix = game['matrix']
        self.n_rows = len(matrix)
        self.n_columns = len(matrix[0])
        
        best = [[None]*self.n_rows, [None]*self.n_columns]
        for row in range(self.n_rows):
            for column in range(self.n_columns):
                p0_val, p1_val = matrix[row][column]
                
                if best[0][row] is None:
                    best[0][row] = (p0_val, column)
                else:
                    p0_val_max, _ = best[0][row]
                    if p0_val > p0_val_max:
                        best[0][row] = (p0_val, column)
                
                if best[1][column] is None:
                    best[1][column] = (p1_val, row)
                else:
                    p1_val_max, _ = best[1][column]
                    if p1_val > p1_val_max:
                        best[1][column] = (p1_val, row)
        
        self.n, self.b, self.s = [], [], [] 
        self.player_names = {}
        for i, player_data in enumerate(game['players']):
            name = player_data[0]
            self.player_names[name] = i
            self.n.append(name)
            self.b.append([index for (_, index) in best[i]])
            self.s.append(player_data[1:])
    
    def dominant_strategy(self, player_name):
        i = self.player_names[player_name]
        best = self.b[i]
        if best.count(best[0]) == len(best):
            return self.s[i][best[0]]
    
    def equilibrium(self):
        equi = []
        for row in range(self.n_rows):
            for column in range(self.n_columns):
                if self.b[0][row] == column and self.b[1][column] == row:
                    equi.append(("%s: %s" % (self.n[0], self.s[0][column]),
                                 "%s: %s" % (self.n[1], self.s[1][row])))
        return equi

########NEW FILE########
__FILENAME__ = examples
from Logic.logic import Proposition, implies


print "implies(True, True)   = %s" % implies(True, True)
print "implies(False, False) = %s" % implies(False, False)

a = lambda p, q: p and implies(p, q)
print Proposition(a, "p and (p => q)").truth_table()

b = lambda p, q: not ((not p) or (not q))
print Proposition(b, "not ((not p) or (not q))").truth_table()

print Proposition(
    lambda p, q: a(p, q) == b(p, q),
                "(p and (p => q)) <=> (not ((not p) or (not q)))"
).truth_table()

print Proposition(
    lambda p: p or (not p),
             "p or (not p)"
).satisfiability_report()

print Proposition(
    lambda p: p and (not p),
             "p and (not p)"
).satisfiability_report()

print Proposition(
    lambda p, q: p or q or (p == q),
                "p or q or (p <=> q)"
).satisfiability_report()

print Proposition(
    lambda p, q: implies(p, q) or implies(q, p),
                "(p => q) or (q => p)"
).satisfiability_report()

print Proposition(
    lambda f, p, d: implies((implies(f, p) or implies(d, p)), implies(f and d, p)),
                    "((f => p) or (d => p)) => ((f and d) => p)"
).satisfiability_report()


########NEW FILE########
__FILENAME__ = homework_4
from Logic.logic import Proposition, implies

print Proposition(
    lambda s, f: implies(s, f) == (s or (not f)),
                "(s => f) <=> (s or (not f))"
).satisfiability_report()

print Proposition(
    lambda s, f: implies(s, f) == implies(not s, not f),
                "(s => f) <=> ((not s) => (not f))"
).satisfiability_report()

print Proposition(
    lambda s, f: implies(s, f) == implies(not f, not s),
                "(s => f) <=> ((not f) => (not s))"
).satisfiability_report()

print Proposition(
    lambda b, d: b or d or implies(b, d),
                "b or d or (b => d)"
).satisfiability_report()

print Proposition(
    lambda b, d: (b and d) == (not ((not b) or (not d))),
                "b and d <=> not ((not b) or (not d))"
).satisfiability_report()

########NEW FILE########
__FILENAME__ = logic
from inspect import getargspec


def num_variables(p):
    return len(getargspec(p).args)


def table(n):
    assert (n >= 1)
    c = [[True], [False]]
    for _ in range(n-1):
        new_c = []
        for e in c:
            new_c.append(e+[True])
            new_c.append(e+[False])
        c = new_c
    return c


def implies(x, y):
    return (not x) or y


class Proposition:
    def __init__(self, p, description=None):
        self.p = p
        self.n = num_variables(p)
        self.description = description
        
        self.truth_table_values = []
        self.is_valid = True
        self.is_satisfiable = False
        for case in table(self.n):
            v = p(*case)
            if v:
                self.is_satisfiable = True
            else:
                self.is_valid = False
            self.truth_table_values.append(case + [v])
        
        self.is_unsatisfiable = not self.is_satisfiable
    
    ### Pretty Print ###
    
    TRUTH_LABEL = {True:"T", False:"F"}
    def truth_table(self):
        s = ["\n" if self.description is None else "\n### %s ###" % self.description]
        h = "| %s | p  |" % ' | '.join(["x%d" % i for i in range(self.n)])
        s.append(h)
        s.append('-' * len(h))
        for row in self.truth_table_values:
            s.append("| %s  |" % '  | '.join([Proposition.TRUTH_LABEL[v]
                                              for v in row]))
        return '\n'.join(s)
    
    def satisfiability_report(self):
        if self.is_valid:
            satisfiability = 'valid'
        elif self.is_satisfiable:
            satisfiability = 'satisfiable'
        else:
            satisfiability = 'unsatisfiable'
        d = "\n" if self.description is None else '\n"%s": ' % self.description
        return d + "is %s" % satisfiability

########NEW FILE########
__FILENAME__ = bayes
from collections import Counter


class Type:
    def __init__(self, vocabulary, p, k, different_words):
        self.vocabulary = vocabulary
        self.norm = float(sum(vocabulary.values()) + k*different_words)
        self.p = p
        self.k = k
    
    def p_word(self, word):
        return float(self.vocabulary[word] + self.k) / self.norm
    
    def p_phrase(self, phrase):
        p = 1.0
        for word in phrase.split():
            p *= self.p_word(word)
        return p


class NaiveBayesClassifier:
    """
    P(spam|word) = P(word|spam) * (P(spam)/P(word))
    """
    def __init__(self, spam_data, ham_data, k=0):
        c_spam, c_ham = Counter(), Counter()
        for c, data in [(c_spam, spam_data), (c_ham, ham_data)]:
            for phrase in data:
                for word in phrase.split():
                    c[word] += 1
        
        norm = float(len(spam_data) + len(ham_data) + k*2)
        self.different_words = len((c_spam + c_ham).keys())
        
        self.spam = Type(c_spam, float(len(spam_data) + k) / norm, k, self.different_words)
        self.ham = Type(c_ham, float(len(ham_data) + k) / norm, k, self.different_words)
    
    def p_spam_given_word(self, word):
        p_spam = self.spam.p_word(word) * self.spam.p
        p_ham  = self.ham.p_word(word)  * self.ham.p
        return p_spam / (p_spam + p_ham)

    def p_spam_given_phrase(self, phrase):
        p_spam = self.spam.p_phrase(phrase) * self.spam.p
        p_ham  = self.ham.p_phrase(phrase)  * self.ham.p
        return p_spam / (p_spam + p_ham)


def result(name, value, expected=None):
    print "P(%s) = %.4f" % (name, value)
    if expected is not None:
        if abs(value - expected) > 0.0001:
            raise Exception("Expected: %.4f" % expected)

########NEW FILE########
__FILENAME__ = examples
from MachineLearning.bayes import NaiveBayesClassifier, result


SPAM = (
    "offer is secret",
    "click secret link",
    "secret sports link",
)
HAM = (
    "play sports today",
    "went play sports",
    "secret sports event",
    "sports is today",
    "sports costs money",
)

print "=== Naive Bayes CLassifier ==="
c = NaiveBayesClassifier(SPAM, HAM)
print "Size of vocabulary: %d" % c.different_words
result("SPAM", c.spam.p, 0.3750)
result("secret|SPAM", c.spam.p_word("secret"), 0.3333)
result("secret|HAM",  c.ham.p_word("secret"), 0.0667)
result("SPAM|sports", c.p_spam_given_word("sports"), 0.1667)
result("SPAM|secret is secret)", c.p_spam_given_phrase("secret is secret"), 0.9615)
result("SPAM|today is secret)", c.p_spam_given_phrase("today is secret"), 0)

print "\n=== Naive Bayes CLassifier with Laplace Smoothing ==="
c = NaiveBayesClassifier(SPAM, HAM, 1)
result("SPAM", c.spam.p, 0.4)
result("HAM", c.ham.p, 0.6)
result("today|SPAM", c.spam.p_word("today"), 0.0476)
result("today|HAM",  c.ham.p_word("today"), 0.1111)
result("SPAM|today is secret)", c.p_spam_given_phrase("today is secret"), 0.4858)


from MachineLearning.linear_regression import linear_regression, gaussian
from scipy import matrix
print "\n=== Linear Regression ==="
x = [3,  4,  5,  6]
y = [0, -1, -2, -3]
(w0, w1), err = linear_regression(x, y)
print "(w0=%.1f, w1=%.1f) err=%.2f" % (w0, w1, err)

x = [2, 4, 6, 8]
y = [2, 5, 5, 8]
(w0, w1), err = linear_regression(x, y)
print "(w0=%.1f, w1=%.1f) err=%.2f" % (w0, w1, err)

x = matrix([[3],
            [4],
            [5],
            [6],
            [7]])
m, s = gaussian(x)
print "m  = %s" % str(m)
print "s^2= %s" % str(s)

x = matrix([[3],
            [9],
            [9],
            [3]])
m, s = gaussian(x)
print "m  = %s" % str(m)
print "s^2= %s" % str(s)

x = matrix([[3, 8],
            [4, 7],
            [5, 5],
            [6, 3],
            [7, 2]])
m, s = gaussian(x)
print "m  = %s" % str(m)
print "s^2= %s" % str(s)
########NEW FILE########
__FILENAME__ = homework
from MachineLearning.bayes import NaiveBayesClassifier, result

MOVIE = (
    "a perfect world",
    "my perfect woman",
    "pretty woman"
)
SONG = (
    "a perfect day",
    "electric storm",
    "another rainy day"
)
c = NaiveBayesClassifier(MOVIE, SONG, 1)
print "Size of vocabulary: %d" % c.different_words

print "\n=== Homework 3.1 ==="
result("MOVIE", c.spam.p)
result("SONG", c.ham.p)
result("perfect|MOVIE", c.spam.p_word("perfect"))
result("perfect|SONG",  c.ham.p_word("perfect"))
result("storm|MOVIE", c.spam.p_word("storm"))
result("storm|SONG",  c.ham.p_word("storm"))

print "\n=== Homework 3.2 ==="
result("MOVIE|perfect storm)", c.p_spam_given_phrase("perfect storm"))

print "\n=== Homework 3.3 ==="
c = NaiveBayesClassifier(MOVIE, SONG)
result("MOVIE|perfect storm)", c.p_spam_given_phrase("perfect storm"))

print "\n=== Homework 3.4 ==="
from MachineLearning.linear_regression import linear_regression
x = [0, 1, 2, 3,  4]
y = [3, 6, 7, 8, 11]
(w0, w1), err = linear_regression(x, y)
print "(w0=%.1f, w1=%.1f) err=%.2f" % (w0, w1, err)

########NEW FILE########
__FILENAME__ = linear_regression
from scipy import polyfit, polyval, sqrt
from scipy import matrix, zeros, sum


def linear_regression(x, y):
    (w1, w0) = polyfit(x, y, 1)
    xr = polyval([w1, w0], y)
    err = sqrt(sum((xr - x)**2) / len(x))
    return (w0, w1), err


def gaussian(x):
    lines, columns = x.shape
    m = zeros(columns)
    for i in range(columns):
        m[i] = sum(x[:,i]) / lines
    
    diff = matrix(zeros((lines,columns)))
    for i in range(lines):
        diff[i,:] = x[i,:] - m
    s = (diff.T * diff) / lines
    
    return m, s

########NEW FILE########
__FILENAME__ = examples
from Markov.markov import MarkovChain, TransProb, MarkovModel

print "\nWeather Example"
WEATHER_CHAIN = ("R", 1.0, {True: 0.6, False: 0.2})
c = MarkovChain(WEATHER_CHAIN, 3)
c.p({"R1":True})
c.p({"R2":True})
c.p({"R3":True})
print "stationary distribution: P(R) = %.4f" % c.stationary_distribution()

print "\nA Example"
A_CHAIN = ("A", 1.0, {True: 0.5, False: 1.0})
c = MarkovChain(A_CHAIN, 3)
c.p({"A1":True})
c.p({"A2":True})
c.p({"A3":True})
print "stationary distribution: P(A) = %.4f" % c.stationary_distribution()

print "\nTransition Probabilities 1"
TRANSITIONS = [("R","S","S","S","R","S","R")]
t = TransProb(TRANSITIONS)
t.report()

print "\nTransition Probabilities 2"
TRANSITIONS = [("S","S","S","S","S","R","S","S","S","R","R")]
t = TransProb(TRANSITIONS)
t.report()

print "\nTransition Probabilities 3"
TRANSITIONS = [("R","S","S","S","S")]
t = TransProb(TRANSITIONS)
t.report(k=1)

print "\nMarkov Model 1"
MODEL = ("R", 0.5, {True: 0.6, False: 0.2}, "H", {True: 0.4, False: 0.9})
m = MarkovModel(MODEL)
m.p({"R1":True})
m.p({"R1":True}, {"H1":True})

print "\nMarkov Model 2"
MODEL = ("R", 1.0, {True: 0.6, False: 0.2}, "H", {True: 0.4, False: 0.9})
m = MarkovModel(MODEL)
m.p({"R1":True}, {"H1":True})

########NEW FILE########
__FILENAME__ = markov
from collections import defaultdict, Counter

from BayesNetworks.bayes_net import BayesNetwork, P


class MarkovChain:
    def __init__(self, data, n_transitions=1):
        name, p0, self.p_trans = data
        
        e = "%s%%d" % name
        NET = [(e % 0, p0)]
        for i in range(n_transitions):
            NET.append((e % (i+1), (
                ({e % i:True }, self.p_trans[True]),
                ({e % i:False}, self.p_trans[False])
            )))
        
        self.net = BayesNetwork(NET)
    
    def p(self, event, given={}):
        P(self.net, event, given)
    
    def stationary_distribution(self, value=True):
        t = self.p_trans[False] / (1 - self.p_trans[True] + self.p_trans[False])
        if value:
            return t
        else:
            return (1 - t)


class TransProb:
    def __init__(self, observations):
        self.trans = defaultdict(list)
        self.states = set([])
        self.states_0 = Counter()
        self.obs_num = len(observations)
        for transitions in observations:
            self.states |= set(transitions)
            s0 = transitions[0]
            self.states_0[s0] += 1
            previous_state = s0
            for i in range(1, len(transitions)):
                new_state = transitions[i]
                self.trans[previous_state].append(new_state)
                previous_state = new_state
    
    def report(self, k=0):
        smoothing_norm = len(self.states) * k
        for s in self.states:
            p0 = float(self.states_0[s] + k) / float(self.obs_num + smoothing_norm)
            print "P(%s0) = %.4f" % (s, p0)
            for g in self.states:
                print "P(%s|%s) =" % (s, g),
                t = self.trans[g]
                if len(t) == 0 and k == 0:
                    print "Undefined"
                else:
                    p = float(t.count(s) + k) / float(len(t) + smoothing_norm)
                    print "%.4f" % p


class MarkovModel:
    def __init__(self, model, n_transitions=2):
        hidden_name, p0, p_trans, measure_name, p_measure = model
        
        h = "%s%%d" % hidden_name
        m = "%s%%d" % measure_name
        
        NET = [(h % 0, p0)]
        for i in range(n_transitions):
            NET.append((m % i, (
                ({h % i:True }, p_measure[True]),
                ({h % i:False}, p_measure[False])
            )))
            NET.append((h % (i+1), (
                ({h % i:True }, p_trans[True]),
                ({h % i:False}, p_trans[False])
            )))
        
        self.net = BayesNetwork(NET)
    
    def p(self, event, given={}):
        P(self.net, event, given)

########NEW FILE########
__FILENAME__ = example_1
from MDP.grid import GridWorld

GRID = [[0,    0, 0,  100],
        [0, None, 0, -100],
        [0,    0, 0,    0]]

PROB = {
    'S':(('S', 0.8), ('W', 0.1), ('E', 0.1)),
    'N':(('N', 0.8), ('E', 0.1), ('W', 0.1)),
    'E':(('E', 0.8), ('S', 0.1), ('N', 0.1)),
    'W':(('W', 0.8), ('N', 0.1), ('S', 0.1)),
}

STATES = ((0,2),(0,1),(1,2),(0,0),(2,2),(1,0),(2,1),(2,0),(2,3))

if __name__ == '__main__':
    g = GridWorld(GRID, PROB, STATES, 1, -3)
    v = g.value(0,2)
    print "\nValue of (0,2) after first iteration: %.1f" % v
    g.grid[0][2] = v
    print "\nValue of (1,2) after first iteration: %.1f" % g.value(1,2)
    
    print "\nInitial values:"
    g = GridWorld(GRID, PROB, STATES, 1, -3)
    print g
    
    i = g.value_iteration(0.1)
    print "\nValues after %d iterations:" % i
    print g

########NEW FILE########
__FILENAME__ = example_2
from MDP.grid import GridWorld

GRID = [[   0, 0, 0,   0],
        [-100, 0, 0, 100]]

def prob(p):
    p = float(p)
    n = 1.0 - p
    return {
        'S':(('S', p), ('N', n)),
        'N':(('N', p), ('S', n)),
        'E':(('E', p), ('W', n)),
        'W':(('W', p), ('E', n)),
    }

STATES = ((0,3),(0,2),(1,2),(0,1),(1,1),(0,0))

if __name__ == '__main__':
    print "\nInitial values:"
    g = GridWorld(GRID, prob(1), STATES, 1, -4)
    print g
    
    i = g.value_iteration(0.1)
    print "\nValues after %d iterations:" % i
    print g
    
    g = GridWorld(GRID, prob(0.8), STATES, 1, -4)
    print "\nValue of (1,2) after first iteration: %.1f" % g.value(0,3)
    
    g = GridWorld(GRID, prob(0.8), STATES, 1, -4)
    i = g.value_iteration(0.1)
    print "\nValues after %d iterations:" % i
    print g


########NEW FILE########
__FILENAME__ = grid
from copy import deepcopy


class GridWorld:
    ACTIONS = ['S', 'N', 'E', 'W']
    
    def __init__(self, grid, prob, states, gamma, r):
        self.grid = deepcopy(grid)
        self.prob = prob
        self.states = states
        
        self.gamma = gamma
        self.r = r
        
        self.max_i = len(self.grid) - 1
        self.max_j = len(self.grid[0]) - 1
    
    def action(self, i, j, direction):
        new_i, new_j = i, j
        if direction == 'S':
            new_i += 1
        elif direction == 'N':
            new_i -= 1
        elif direction == 'E':
            new_j += 1
        elif direction == 'W':
            new_j -= 1
        
        if (new_i < 0) or (new_i > self.max_i):
            new_i = i
        
        if (new_j < 0) or (new_j > self.max_j):
            new_j = j
        
        if self.grid[new_i][new_j] is None:
            new_i, new_j = i, j
        
        return (new_i, new_j)
    
    def value(self, i, j):
        new_positions = {}
        for action in GridWorld.ACTIONS:
            new_i, new_j = self.action(i, j, action)
            new_positions[action] = (new_i, new_j)
        
        values = []
        for action in GridWorld.ACTIONS:
            v = 0
            for a, p in self.prob[action]:
                (new_i, new_j) = new_positions[a]
                v += p * self.grid[new_i][new_j]
            values.append(v)
        return (self.gamma * max(values)) + self.r
    
    def value_iteration(self, delta):
        n = 0
        while True:
            n += 1
            diffs = []
            for (i, j) in self.states:
                v = self.value(i,j)
                diffs.append(abs(v - self.grid[i][j]))
                self.grid[i][j] = v
            if max(diffs) < delta:
                break
        return n
    
    def __str__(self):
        s = []
        for i in range(self.max_i+1):
            items = []
            for j in range(self.max_j+1):
                v = self.grid[i][j]
                if v is None:
                    items.append("  XX")
                else:
                    items.append('%4.0f' % v)
            s.append(' '.join(items))
        return '\n'.join(s)

########NEW FILE########
__FILENAME__ = examples
from ProblemSolving.search import *

ROMANIA_ROAD_MAP = [
    ("Arad", "Sibiu", 140),
    ("Arad", "Zerind", 75),
    ("Arad", "Timisoara", 118),
    ("Sibiu", "Fagaras", 99),
    ("Sibiu", "Rimnicu Vilcea", 80),
    ("Rimnicu Vilcea", "Craiova", 146),
    ("Rimnicu Vilcea", "Pitesti", 97),
    ("Pitesti", "Bucharest", 101),
    ("Drobeta", "Craiova", 120),
    ("Zerind", "Oradea", 71),
    ("Oradea", "Sibiu", 151),
    ("Timisoara", "Lugoj", 111),
    ("Lugoj", "Mehadia", 70),
    ("Mehadia", "Drobeta", 75),
    ("Craiova", "Pitesti", 138),
    ("Fagaras", "Bucharest", 211),
    ("Bucharest", "Giurgiu", 90),
    ("Bucharest", "Urziceni", 85),
]

ROMANIA_DISTANCES_FROM_BUCHAREST = {
    "Arad": 336,
    "Bucharest": 0,
    "Craiova": 160,
    "Drobeta": 242,
    "Fagaras": 176,
    "Giurgiu": 77,
    "Lugoj": 244,
    "Mehadia": 241,
    "Oradea": 380,
    "Pitesti": 100,
    "Rimnicu Vilcea": 193,
    "Sibiu": 253,
    "Timisoara": 329,
    "Urziceni": 80,
    "Zerind": 374,
}

if __name__ == '__main__':
    state_space = generate_state_space(ROMANIA_ROAD_MAP)
    
    for Algorithm, heuristic in [
            (BreadthFirstSearch, None),
            (DepthFirstSearch, None),
            (UniformCostSearch, None),
            (AStarSearch, ROMANIA_DISTANCES_FROM_BUCHAREST),
        ]:
        print "\n=== %s ===" % Algorithm.__name__
        alg = Algorithm(state_space)
        solution = alg.search("Arad", "Bucharest", heuristic)
        path, iterations = solution
        print "Found path in %d iterations: %s" % (iterations, path)

########NEW FILE########
__FILENAME__ = homework_1
from ProblemSolving.search import *

class BreadthFirstSearchLeftToRight(UniformCostSearch):
    def path_cost(self, path):
        return path.length * 100 + ord(path.end)

class DepthFirstSearchLeftToRight(UniformCostSearch):
    def path_cost(self, path):
        return 1.0 / float(path.length * 100 + (100 - ord(path.end)))

class BreadthFirstSearchRightToLeft(UniformCostSearch):
    def path_cost(self, path):
        return path.length * 100 + (100 - ord(path.end))

class DepthFirstSearchRightToLeft(UniformCostSearch):
    def path_cost(self, path):
        return 1.0 / float(path.length * 100 + ord(path.end))

def breadth_vs_depth(graph, start, goal):
    state_space = generate_state_space(graph)
    for Algorithm in [
            BreadthFirstSearchLeftToRight,
            DepthFirstSearchLeftToRight,
            BreadthFirstSearchRightToLeft,
            DepthFirstSearchRightToLeft,
        ]:
        alg = Algorithm(state_space)
        solution = alg.search(start, goal)
        path, iterations = solution
        print "%s: %d" % (Algorithm.__name__, iterations)


if __name__ == '__main__':
    print "\n=== Homework 1.4: Search Tree ==="
    GRAPH_1 = [
        ("A", "B", 1),
        ("A", "C", 1),
        ("A", "D", 1),
        ("B", "E", 1),
        ("B", "F", 1),
        ("C", "G", 1),
        ("C", "H", 1),
        ("D", "I", 1),
        ("D", "J", 1),
    ]
    breadth_vs_depth(GRAPH_1, "A", "F")
    
    print "\n=== Homework 1.5: Search Tree 2 ==="
    GRAPH_2 = GRAPH_1 + [
        ("G", "K", 1),
        ("G", "L", 1),
        ("H", "M", 1),
    ]
    breadth_vs_depth(GRAPH_2, "A", "M")
    
    print "\n=== Homework 1.6: Search Network ==="
    GRAPH_3 = [
        ("A", "B", 1), ("A", "C", 1),
        ("B", "D", 1), ("B", "E", 1),
        ("C", "E", 1), ("C", "F", 1),
        ("D", "G", 1), ("D", "H", 1),
        ("E", "H", 1), ("E", "I", 1),
        ("F", "I", 1), ("F", "J", 1),
        ("P", "N", 1), ("P", "O", 1),
        ("N", "K", 1), ("N", "L", 1),
        ("O", "L", 1), ("O", "M", 1),
        ("K", "G", 1), ("K", "H", 1),
        ("L", "H", 1), ("L", "I", 1),
        ("M", "I", 1), ("M", "J", 1),
    ]
    breadth_vs_depth(GRAPH_3, "A", "J")
    
    print "\n=== Homework 1.7: Astar ==="
    TABLE = []
    for x in range(1,7):
        for y in ["a", "b", "c", "d"]:
            next_x = x+1
            if next_x < 7:
                TABLE.append(("%c%d"%(y,x) ,"%c%d"%(y,x+1),1))
            next_y = ord(y)+1
            if next_y < ord("e"):
                TABLE.append(("%c%d"%(y,x) ,"%c%d"%(chr(next_y),x),1))
    HEURISTIC = {
        "a1":4, "a2":4, "a3":4, "a4":3, "a5":2, "a6":1,
        "b1":3, "b2":3, "b3":3, "b4":3, "b5":2, "b6":1,
        "c1":2, "c2":2, "c3":2, "c4":2, "c5":2, "c6":1,
        "d1":1, "d2":1, "d3":1, "d4":1, "d5":1, "d6":0,
    }
    state_space = generate_state_space(TABLE)
    alg = AStarSearch(state_space)
    solution = alg.search("a1", "d6", HEURISTIC, debug=True)
    path, iterations = solution
    print "Found path in %d iterations: %s" % (iterations, path)
########NEW FILE########
__FILENAME__ = search
from collections import defaultdict
from copy import deepcopy
from heapq import heappush, heappop


def generate_state_space(data):
    """
    Generate our state space graph given a set of possible actions:
    data = [
        (state_a, state_b, cost),
        ...
    ]
    """
    state_space = defaultdict(list)
    for state_a, state_b, cost in data:
        state_space[state_a].append((state_b, cost))
        state_space[state_b].append((state_a, cost))
    return state_space


class GraphSearch:
    """
    The state_space is a graph where each node is a state and each edge is an
    action. Each action has a cost.
    A solution to a problem is a path between two states: the initial state and
    the goal state.
    
    state_space = {
        state_a: [
            (state_b, cost)
            ...
        ]
        state_b: [
            (state_a, cost)
            ...
        ]
        ...
    }
    action = (new_state, cost)
    path = ((state_1, state_2, ...state_n), cost, length)
    """
    def __init__(self, state_space):
        self.__state_space = state_space
    
    def actions(self, state):
        return self.__state_space[state]
    
    def step(self, path, action):
        new_path = deepcopy(path)
        new_path.add(action)
        return new_path
    
    def add_frontier(self, path):
        self.frontier[path.end] = path
        self.add_path(path)
    
    def add_path(self, path):
        self.paths.append(path)
    
    def already_in_frontier(self, new_path, adjacent):
        pass
    
    def search(self, initial_state, goal, heuristic=None, debug=False):
        self.heuristic = heuristic
        self.paths = []
        self.frontier = {}
        explored = set([])
        self.add_frontier(Path(initial_state))
        
        iterations = 0
        while True:
            iterations += 1
            path = self.get_path()
            if path is None: return None
            if debug: print path
            
            s = path.end
            explored.add(s)
            del self.frontier[s]
            if s == goal:
                return (path, iterations)
            
            for a in self.actions(s):
                new_node = a[0]
                if new_node in explored: continue
                
                new_path = self.step(path, a)
                if new_node in self.frontier:
                    self.already_in_frontier(new_path, new_node)
                else:
                    self.add_frontier(new_path)


class Path:
    def __init__(self, start):
        self.states = [start]
        self.cost = 0
        self.length = 0
    
    def add(self, action):
        self.states.append(action[0])
        self.cost += action[1]
        self.length += 1
    
    @property
    def end(self):
        return self.states[-1]
    
    def __str__(self):
        return ' -> '.join(self.states)  + " (cost:%d, length:%d)" % (self.cost, self.length)


class BreadthFirstSearch(GraphSearch):
    def get_path(self):
        return self.paths.pop(0)


class DepthFirstSearch(GraphSearch):
    def get_path(self):
        return self.paths.pop()


class UniformCostSearch(GraphSearch):
    def add_path(self, path):
        heappush(self.paths, (self.path_cost(path), path))
    
    def get_path(self):
        return heappop(self.paths)[1]
    
    def path_cost(self, path):
        return path.cost
    
    def already_in_frontier(self, new_path, adjacent):
        if self.path_cost(new_path) < self.path_cost(self.frontier[adjacent]):
            del self.frontier[adjacent]
            self.add_frontier(new_path)


class AStarSearch(UniformCostSearch):
    def path_cost(self, path):
        return path.cost + self.heuristic[path.end]


########NEW FILE########
__FILENAME__ = homework
from math import pi
from motion import Position

p = Position(x=0, y=0, v=10, om=(pi/8.0), th=0, dt=4)
p.update(4)
print p

########NEW FILE########
__FILENAME__ = motion
from math import sin, cos, pi

class Position:
    def __init__(self, x, y, th, v, om, t=0, dt=1):
        self.x = float(x)
        self.y = float(y)
        self.th = float(th)
        self.v = float(v)
        self.om = float(om)
        self.dt = float(dt)
    
    def update(self, steps=1):
        for _ in range(steps):
            d = self.v * self.dt
            self.x += d * cos(self.th)
            self.y += d * sin(self.th)
            self.th += self.om * self.dt
            if self.th >= 2*pi:
                self.th -= 2*pi
    
    def __str__(self):
        return '\n'.join([
             "x : %.2f" % self.x,
             "y : %.2f" % self.y,
             "th: %.2f" % self.th,
         ])

########NEW FILE########
__FILENAME__ = hw1
from datetime import datetime, timedelta
from math import sqrt
from numpy import mean, std

import qenv
from qstkutil.DataAccess import DataAccess
from qstkutil.qsdateutil import getNYSEdays


class Equities:
    def __init__(self, values, name=None):
        self.values = values
        self.name = name
        self.returns = map(self.single_return, range(1, len(self.values)))
    
    def roi(self, start, end):
        if self.values[end] == self.values[start]: return 0
        return (self.values[end] / self.values[start]) - 1
    
    def tot_return(self):
        return self.roi(0, -1)
    
    def single_return(self, d):
        return self.roi(d-1, d)
    
    def average_return(self):
        return mean(self.returns)
    
    def stdev_return(self):
        return std(self.returns)
    
    def sharpe_ratio(self):
        return (self.average_return() / self.stdev_return()) * sqrt(len(self.values))
    
    def __str__(self):
        return '\n'.join([
            "\n[%s]" % (self.name if self.name is not None else "Equities"),
            "Sharpe Ratio     : %.6f" % self.sharpe_ratio(),
            "Total Return     : %.4f" % self.tot_return(),
            "Average Daily Ret: %.6f" % self.average_return(),
            "STDEV Daily Ret  : %.6f" % self.stdev_return(),
        ])


if __name__ == '__main__':
    # TODO: sharp ratio higher than 4?
    PORTFOLIO = (
        ('AAPL' , 0.6),
        ('GLD'  , 0.2),
        ('WMT'  , 0.1),
        ('CVX'  , 0.1)
    )
    
    YEAR = 2011
    timestamps = getNYSEdays(datetime(YEAR,  1,  1),
                             datetime(YEAR, 12, 31),
                             timedelta(hours=16))
    
    BENCHMARK = 'SPY'
    symbols = [s for s, _ in PORTFOLIO] + [BENCHMARK]
    
    close = DataAccess('Yahoo').get_data(timestamps, symbols, "close")
    
    print Equities([sum([close[s][i] for s in symbols]) for i in range(len(timestamps))], "Portfolio")
    print Equities([     close[BENCHMARK][i]            for i in range(len(timestamps))], "Benchmark")

########NEW FILE########
__FILENAME__ = hw2
import copy
from datetime import datetime, timedelta
from numpy import NAN

import qenv
from qstkutil.qsdateutil import getNYSEdays
from qstkutil.DataAccess import DataAccess
from qstkstudy.EventProfiler import EventProfiler


def below_5_dollars_event(eventmat, sym, prices, timestamps):
    for t in range(1, len(prices)):
        # The actual close of the stock price drops below $5.00
        if prices[t-1] >= 5.00 and prices[t] < 5.00:
            eventmat[sym][t] = 1.0


def findEvents(symbols_year, startday, endday, event, data_item="close"):
    dataobj = DataAccess('Yahoo')
    symbols = dataobj.get_symbols_from_list("sp500%d" % symbols_year)
    symbols.append('SPY')
    
    # Reading the Data for the list of Symbols.
    timestamps = getNYSEdays(startday, endday, timedelta(hours=16))
    
    # Reading the Data
    print "# reading data"
    close = dataobj.get_data(timestamps, symbols, data_item)
    
    # Generating the Event Matrix
    print "# finding events"
    eventmat = copy.deepcopy(close)
    for sym in symbols:
        for time in timestamps:
            eventmat[sym][time] = NAN
    
    for symbol in symbols:
        event(eventmat, symbol, close[symbol], timestamps)
    
    return eventmat


if __name__ == '__main__':
    START_DAY = datetime(2008,  1,  1)
    END_DAY   = datetime(2009, 12, 31)
    
    # Survivorship Bias
    # http://en.wikipedia.org/wiki/Survivorship_bias#In_finance
    SYMBOLS_STOCK_YEAR = 2012
    
    eventMatrix = findEvents(SYMBOLS_STOCK_YEAR, START_DAY, END_DAY,
                             below_5_dollars_event, "actual_close")
    
    print "# Event Profiler"
    eventProfiler = EventProfiler(eventMatrix, START_DAY, END_DAY,
                                     lookback_days=20, lookforward_days=20, verbose=True)
    
    print "# Plot"
    eventProfiler.study(filename="data/event.pdf",
                        plotErrorBars=True, plotMarketNeutral=True,
                        plotEvents=False, marketSymbol='SPY')

########NEW FILE########
__FILENAME__ = hw3
import csv
from datetime import date, datetime, timedelta
from collections import defaultdict

import qenv
from qstkutil.DataAccess import DataAccess
from qstkutil.qsdateutil import getNYSEdays
from hw1 import Equities


class Portfolio:
    def __init__(self, cash):
        self.cash = cash
        self.shares = defaultdict(int)
    
    def update(self, sym, num, share_cost):
        self.cash -= num * share_cost
        self.shares[sym] += num
    
    def value(self, close, d):
        return self.cash + sum([num * close[sym][d] for sym, num in self.shares.iteritems()])


def marketsim(cash, orders_file, data_item):
    # Read orders
    orders = defaultdict(list)
    symbols = set([])
    for year, month, day, sym, action, num in csv.reader(open(orders_file, "rU")):
        orders[date(int(year), int(month), int(day))].append((sym, action, int(num)))
        symbols.add(sym)
    
    days = orders.keys()
    days.sort()
    day, end = days[0], days[-1]
    
    # Reading the Data for the list of Symbols.
    timestamps = getNYSEdays(datetime(day.year,day.month,day.day),
                             datetime(end.year,end.month,end.day+1),
                             timedelta(hours=16))
    
    dataobj = DataAccess('Yahoo')
    close = dataobj.get_data(timestamps, symbols, data_item)
    
    values = []
    portfolio = Portfolio(cash)
    for i, t in enumerate(timestamps):
        for sym, action, num in orders[date(t.year, t.month, t.day)]:
            if action == 'Sell': num *= -1
            portfolio.update(sym, num, close[sym][i])
        
        entry = (t.year, t.month, t.day, portfolio.value(close, i))
        values.append(entry)
    
    return values


def analyze(values):
    print Equities([v[3] for v in values], "Portfolio")


if __name__ == "__main__":
    CASH = 1000000
    ORDERS_FILE = "data/orders.csv"
    BENCHMARK = "$SPX"
    
    analyze(marketsim(CASH, ORDERS_FILE, "close"))

########NEW FILE########
__FILENAME__ = hw4
"""
Use the actual close $5.00 event with the 2012 SP500 data.

I expect that this strategy should make money.
Use the following parameters:
  * Starting cash: $50,000
  * Start date: 1 January 2008
  * End date: 31 December 2009
  * When an event occurs, buy 100 shares of the equity on that day.
  * Sell automatically 5 trading days later.

Compute the Sharpe Ratio, total return and STDDEV of daily returns.
"""
from datetime import datetime

from hw2 import findEvents
from hw3 import marketsim, analyze


class EventStrategy:
    def __init__(self, order_file, threshold, num, hold_days):
        self.f = open(order_file, "w")
        self.threshold = threshold
        self.num = num
        self.hold_days = hold_days
        
    
    def add_order(self, timestamp, sym, action, num):
        self.f.write(",".join(map(str, [
            timestamp.year, timestamp.month, timestamp.day,
            sym, action, num
        ])) + "\n")
    
    def threshold_event(self, eventmat, sym, prices, timestamps):
        for t in range(1, len(prices)):
            # The actual close of the stock price drops below a given threshold
            if prices[t-1] >= self.threshold and prices[t] < self.threshold:
                eventmat[sym][t] = 1.0
                self.add_order(timestamps[t               ], sym, "Buy" , self.num)
                self.add_order(timestamps[t+self.hold_days], sym, "Sell", self.num)
    
    def close(self):
        self.f.close()


if __name__ == "__main__":
    START_DAY = datetime(2008,  1,  1)
    END_DAY   = datetime(2009, 12, 31)
    SYMBOLS_STOCK_YEAR = 2012
    THRESHOLD = 7
    CASH = 100000
    ORDERS_FILE = "data/orders_event.csv"
    BUY_N = 100
    HOLD_DAYS = 5
    CLOSE_TYPE = "actual_close"
    
    strategy = EventStrategy(ORDERS_FILE, THRESHOLD, BUY_N, HOLD_DAYS)
    findEvents(SYMBOLS_STOCK_YEAR, START_DAY, END_DAY,
               strategy.threshold_event, "actual_close")
    strategy.close()
    
    analyze(marketsim(CASH, ORDERS_FILE, "close"))

########NEW FILE########
__FILENAME__ = qenv
# Setup the require environmental variables for QSTK
# http://wiki.quantsoftware.org/index.php?title=QuantSoftware_ToolKit
from os import environ
from os.path import join
from sys import path

HOME = '/home/emilmont'
QS = join(HOME, 'Software/QSTK')
QSDATA = join(HOME, 'Data/QSData')

environ.update({
    'QS'             : QS,
    'QSDATA'         : QSDATA,
    'QSDATAPROCESSED': join(QSDATA, 'Processed'),
    'QSDATATMP'      : join(QSDATA, 'Tmp'),
    'QSBIN'          : join(QS, 'Bin'),
    'QSSCRATCH'      : join(QSDATA, 'Scratch'),
    'CACHESTALLTIME' : '12',
})

path.append(QS)

########NEW FILE########
__FILENAME__ = count_freqs
#! /usr/bin/python

__author__="Daniel Bauer <bauer@cs.columbia.edu>"
__date__ ="$Sep 12, 2011"

import sys
from collections import defaultdict
import math

"""
Count n-gram frequencies in a data file and write counts to
stdout. 
"""

def simple_conll_corpus_iterator(corpus_file):
    """
    Get an iterator object over the corpus file. The elements of the
    iterator contain (word, ne_tag) tuples. Blank lines, indicating
    sentence boundaries return (None, None).
    """
    l = corpus_file.readline()
    while l:
        line = l.strip()
        if line: # Nonempty line
            # Extract information from line.
            # Each line has the format
            # word pos_tag phrase_tag ne_tag
            fields = line.split(" ")
            ne_tag = fields[-1]
            #phrase_tag = fields[-2] #Unused
            #pos_tag = fields[-3] #Unused
            word = " ".join(fields[:-1])
            yield word, ne_tag
        else: # Empty line
            yield (None, None)                        
        l = corpus_file.readline()

def sentence_iterator(corpus_iterator):
    """
    Return an iterator object that yields one sentence at a time.
    Sentences are represented as lists of (word, ne_tag) tuples.
    """
    current_sentence = [] #Buffer for the current sentence
    for l in corpus_iterator:        
            if l==(None, None):
                if current_sentence:  #Reached the end of a sentence
                    yield current_sentence
                    current_sentence = [] #Reset buffer
                else: # Got empty input stream
                    sys.stderr.write("WARNING: Got empty input file/stream.\n")
                    raise StopIteration
            else:
                current_sentence.append(l) #Add token to the buffer

    if current_sentence: # If the last line was blank, we're done
        yield current_sentence  #Otherwise when there is no more token
                                # in the stream return the last sentence.

def get_ngrams(sent_iterator, n):
    """
    Get a generator that returns n-grams over the entire corpus,
    respecting sentence boundaries and inserting boundary tokens.
    Sent_iterator is a generator object whose elements are lists
    of tokens.
    """
    for sent in sent_iterator:
         #Add boundary symbols to the sentence
         w_boundary = (n-1) * [(None, "*")]
         w_boundary.extend(sent)
         w_boundary.append((None, "STOP"))
         #Then extract n-grams
         ngrams = (tuple(w_boundary[i:i+n]) for i in xrange(len(w_boundary)-n+1))
         for n_gram in ngrams: #Return one n-gram at a time
            yield n_gram        


class Hmm(object):
    """
    Stores counts for n-grams and emissions. 
    """

    def __init__(self, n=3):
        assert n>=2, "Expecting n>=2."
        self.n = n
        self.emission_counts = defaultdict(int)
        self.ngram_counts = [defaultdict(int) for i in xrange(self.n)]
        self.all_states = set()

    def train(self, corpus_file):
        """
        Count n-gram frequencies and emission probabilities from a corpus file.
        """
        ngram_iterator = \
            get_ngrams(sentence_iterator(simple_conll_corpus_iterator(corpus_file)), self.n)

        for ngram in ngram_iterator:
            #Sanity check: n-gram we get from the corpus stream needs to have the right length
            assert len(ngram) == self.n, "ngram in stream is %i, expected %i" % (len(ngram, self.n))

            tagsonly = tuple([ne_tag for word, ne_tag in ngram]) #retrieve only the tags            
            for i in xrange(2, self.n+1): #Count NE-tag 2-grams..n-grams
                self.ngram_counts[i-1][tagsonly[-i:]] += 1
            
            if ngram[-1][0] is not None: # If this is not the last word in a sentence
                self.ngram_counts[0][tagsonly[-1:]] += 1 # count 1-gram
                self.emission_counts[ngram[-1]] += 1 # and emission frequencies

            # Need to count a single n-1-gram of sentence start symbols per sentence
            if ngram[-2][0] is None: # this is the first n-gram in a sentence
                self.ngram_counts[self.n - 2][tuple((self.n - 1) * ["*"])] += 1

    def write_counts(self, output, printngrams=[1,2,3]):
        """
        Writes counts to the output file object.
        Format:

        """
        # First write counts for emissions
        for word, ne_tag in self.emission_counts:            
            output.write("%i WORDTAG %s %s\n" % (self.emission_counts[(word, ne_tag)], ne_tag, word))


        # Then write counts for all ngrams
        for n in printngrams:            
            for ngram in self.ngram_counts[n-1]:
                ngramstr = " ".join(ngram)
                output.write("%i %i-GRAM %s\n" %(self.ngram_counts[n-1][ngram], n, ngramstr))

    def read_counts(self, corpusfile):

        self.n = 3
        self.emission_counts = defaultdict(int)
        self.ngram_counts = [defaultdict(int) for i in xrange(self.n)]
        self.all_states = set()

        for line in corpusfile:
            parts = line.strip().split(" ")
            count = float(parts[0])
            if parts[1] == "WORDTAG":
                ne_tag = parts[2]
                word = parts[3]
                self.emission_counts[(word, ne_tag)] = count
                self.all_states.add(ne_tag)
            elif parts[1].endswith("GRAM"):
                n = int(parts[1].replace("-GRAM",""))
                ngram = tuple(parts[2:])
                self.ngram_counts[n-1][ngram] = count
                


def usage():
    print """
    python count_freqs.py [input_file] > [output_file]
        Read in a gene tagged training input file and produce counts.
    """

if __name__ == "__main__":

    if len(sys.argv)!=2: # Expect exactly one argument: the training data file
        usage()
        sys.exit(2)

    try:
        input = file(sys.argv[1],"r")
    except IOError:
        sys.stderr.write("ERROR: Cannot read inputfile %s.\n" % arg)
        sys.exit(1)
    
    # Initialize a trigram counter
    counter = Hmm(3)
    # Collect counts
    counter.train(input)
    # Write the counts
    counter.write_counts(sys.stdout)

########NEW FILE########
__FILENAME__ = eval_gene_tagger
#! /usr/bin/python

__author__="Daniel Bauer <bauer@cs.columbia.edu>"
__date__ ="$Sep 29, 2011"

import sys


"""
Evaluate gene tagger output by comparing it to a gold standard file.

Running the script on your tagger output like this

    python eval_gene_tagger.py gene_dev.key your_tagger_output.dat

will generate a table of results like this:

    Found 14071 GENES. Expected 5942 GENES; Correct: 3120.

		 precision 	recall 		F1-Score
    GENE:	 0.433367	0.231270	0.301593

Adopted from original named entity evaluation.

"""

def corpus_iterator(corpus_file, with_logprob = False):
    """
    Get an iterator object over the corpus file. The elements of the
    iterator contain (word, ne_tag) tuples. Blank lines, indicating
    sentence boundaries return (None, None).
    """
    l = corpus_file.readline()    
    tagfield = with_logprob and -2 or -1

    try:
        while l:
            line = l.strip()
            if line: # Nonempty line
                # Extract information from line.
                # Each line has the format
                # word ne_tag [log_prob]
                fields = line.split(" ")
                ne_tag = fields[tagfield]
                word = " ".join(fields[:tagfield])
                yield word, ne_tag
            else: # Empty line
                yield (None, None)
            l = corpus_file.readline()
    except IndexError:
        sys.stderr.write("Could not read line: \n")
        sys.stderr.write("\n%s" % line)
        if with_logprob:
            sys.stderr.write("Did you forget to output log probabilities in the prediction file?\n")
        sys.exit(1)


class NeTypeCounts(object):
    """
    Stores true/false positive/negative counts for each NE type.
    """

    def __init__(self):
        self.tp = 0
        self.fp = 0
        self.tn = 0
        self.fn = 0 

    def get_precision(self):
        return self.tp / float(self.tp + self.fp)

    def get_recall(self):
        return self.tp / float(self.tp + self.fn)

    def get_accuracy(self):
        return (self.tp + self.tn) / float(self.tp + self.tn + self.fp + self.fn)


class Evaluator(object):
    """
    Stores global true/false positive/negative counts. 
    """


    ne_classes = ["GENE"]

    def __init__(self):        
        self.tp = 0
        self.tn = 0
        self.fp = 0        
        self.fn = 0

        # Initialize an object that counts true/false positives/negatives
        # for each NE class
        self.class_counts = {}
        for c in self.ne_classes:
            self.class_counts[c] = NeTypeCounts()

    def compare(self, gold_standard, prediction):
        """
        Compare the prediction against a gold standard. Both objects must be
        generator or iterator objects that return a (word, ne_tag) tuple at a
        time.
        """

        # Define a couple of tags indicating the status of each stream
        curr_pred_type = None # prediction stream was previously in a named entity
        curr_pred_start = None # a new prediction starts at the current token
        curr_gs_type = None   # prediction stream was previously in a named entity
        curr_gs_start = None # a new prediction starts at the current token

        total = 0
        for gs_word, gs_tag in gold_standard: # Move through the gold standard stream
            pred_word, pred_tag = prediction.next() # Get the corresponding item from the prediction stream
            
            # Make sure words in both files match up
            if gs_word != pred_word:
                sys.stderr.write("Could not align gold standard and predictions in line %i.\n" % (total+1))
                sys.stderr.write("Gold standard: %s  Prediction file: %s\n" % (gs_word, pred_word))
                sys.exit(1)        

            # Split off the I and B tags
            gs_type = gs_tag==None and "O" or gs_tag.split("-")[-1]
            pred_type = pred_tag==None and "O" or pred_tag.split("-")[-1]                        

            # Check if a named entity ends here in either stream.
            # This is the case if we are currently in an entity and either
            #   - end of sentence
            #   - current word is marked O
            #   - new entity starts (B - or I with different NE type)
            pred_ends = curr_pred_type!=None and ((pred_tag==None or pred_tag[0] in "OB") or (curr_pred_type!=pred_type and pred_tag[0]=="I"))
            gs_ends = curr_gs_type!=None and ((gs_tag==None or gs_tag[0] in "OB") or (curr_gs_type!=gs_type and gs_tag[0]=="I"))
            

            # Check if a named entity starts here in either stream.
            # This is tha case if this is not the end of a sentence and
            #   - This is not the end of a sentence
            #   - New entity starts (B, I after O or at begining of sentence or
            #       I with different NE type) 
            if pred_word!=None:
                pred_start = (pred_tag!=None and pred_tag[0] == "B") or (curr_pred_type==None and pred_tag[0]=="I") or \
                    (curr_pred_type!=None and curr_pred_type!=pred_type and pred_tag.startswith("I"))
                gs_starts = (gs_tag!=None and gs_tag[0] == "B") or (curr_gs_type==None and gs_tag[0]=="I") or \
                    (curr_gs_type!=None and curr_gs_type!=gs_type and gs_tag.startswith("I"))
            else:
                pred_start = False
                gs_starts = False            

            #For debugging:
            #print pred_word, gs_tag, pred_tag, pred_ends, gs_ends, pred_start, gs_starts


            # Now try to match up named entities that end here

            if gs_ends and pred_ends: # GS and prediction contain a named entity that ends in the same place

                #If both named entities start at the same place and are of the same type
                if curr_gs_start == curr_pred_start and curr_gs_type == curr_pred_type:
                    # Count true positives
                    self.tp += 1
                    self.class_counts[curr_pred_type].tp += 1
                else: #span matches, but label doesn't match: count both a true positive and a false negative
                    self.fp += 1
                    self.fn += 1
                    self.class_counts[curr_pred_type].fp += 1
                    self.class_counts[curr_gs_type].fn += 1
            elif gs_ends: #Didn't find the named entity in the gold standard, count false negative
                self.fn += 1
                self.class_counts[curr_gs_type].fn += 1
            elif pred_ends: #Named entity in the prediction doesn't match one int he gold_standard, count false positive
                self.fp += 1
                self.class_counts[curr_pred_type].fp += 1
            elif curr_pred_type==None and curr_pred_type==None: #matching O tag or end of sentence, count true negative
                self.tn += 1
                for c in self.ne_classes:
                    self.class_counts[c].tn += 1

            # Remember that we are no longer in a named entity
            if gs_ends:
                curr_gs_type = None
            if pred_ends:
                curr_pred_type = None

            # If a named entity starts here, remember it's type and this position
            if gs_starts:
                curr_gs_start = total
                curr_gs_type = gs_type
            if pred_start:
                curr_pred_start = total
                curr_pred_type = pred_type
            total += 1

    def print_scores(self):
        """
        Output a table with accuracy, precision, recall and F1 score. 
        """

        print "Found %i GENEs. Expected %i GENEs; Correct: %i.\n" % (self.tp + self.fp, self.tp + self.fn, self.tp)


        if self.tp + self.tn + self.fp + self.fn == 0: # There was nothing to do.
            acc = 1
        else:
            acc = (self.tp + self.tn) / float(self.tp + self.tn + self.fp + self.fn)

        if self.tp+self.fp == 0:   # Prediction didn't annotate any NEs
            prec = 1
            
        else:
            prec = self.tp / float(self.tp + self.fp)
            

        if self.tp+self.fn == 0: # Prediction marked everything as a NE of the wrong type.
            rec = 1
        else:
            rec = self.tp / float(self.tp + self.fn)

        print "\t precision \trecall \t\tF1-Score"
        fscore = (2*prec*rec)/(prec+rec)
        #print "Total:\t %f\t%f\t%f" % (prec, rec, fscore)
        for c in self.ne_classes:
            c_tp = self.class_counts[c].tp
            c_tn = self.class_counts[c].tn
            c_fp = self.class_counts[c].fp
            c_fn = self.class_counts[c].fn
            #print c
            #print c_tp
            #print c_tn
            #print c_fp
            #print c_fn
            if (c_tp + c_tn + c_fp + c_fn) == 0:                
                c_acc = 1
            else:
                c_acc = (c_tp + c_tn) / float(c_tp + c_tn + c_fp + c_fn)
            
            if (c_tp + c_fn) == 0:
                sys.stderr.write("Warning: no instances for entity type %s in gold standard.\n" % c)
                c_rec = 1
            else:
                c_rec = c_tp / float(c_tp + c_fn)
            if (c_tp + c_fp) == 0:
                sys.stderr.write("Warning: prediction file does not contain any instances of entity type %s.\n" % c)
                c_prec =1
            else:
                c_prec = c_tp / float(c_tp + c_fp)

            if c_prec + c_rec == 0:
                fscore = 0
            else:    
                fscore = (2*c_prec * c_rec)/(c_prec + c_rec)
            print "%s:\t %f\t%f\t%f" % (c, c_prec, c_rec, fscore)


def usage():
    sys.stderr.write("""
    Usage: python eval_gene_tagger.py [key_file] [prediction_file]
        Evaluate the gene-tagger output in prediction_file against
        the gold standard in key_file. Output accuracy, precision,
        recall and F1-Score.\n""")

if __name__ == "__main__":

    if len(sys.argv)!=3:
        usage()
        sys.exit(1)
    gs_iterator = corpus_iterator(file(sys.argv[1]))
    pred_iterator = corpus_iterator(file(sys.argv[2]), with_logprob = False)
    evaluator = Evaluator()
    evaluator.compare(gs_iterator, pred_iterator)
    evaluator.print_scores()

########NEW FILE########
__FILENAME__ = gene_tagger
from __future__ import division
from collections import defaultdict
from os.path import exists

from count_freqs import Hmm
from eval_gene_tagger import corpus_iterator, Evaluator


def combinations(list_a, list_b):
    for a in list_a:
        for b in list_b:
            yield (a, b)


class GeneTagger:
    def __init__(self, counts_path):
        self.word_count = defaultdict(int)
        self.tag_word   = defaultdict(int)
        
        self.unigram = defaultdict(int)
        self.bigram  = defaultdict(int)
        self.trigram = defaultdict(int)
        
        for line in open(counts_path):
            t = line.strip().split()
            count, label, key = int(t[0]), t[1], tuple(t[2:])
            if   label == "1-GRAM": self.unigram[key[0]] = count
            elif label == "2-GRAM": self.bigram [key]    = count
            elif label == "3-GRAM": self.trigram[key]    = count
            elif label == "WORDTAG":
                self.word_count[key[1]] += count
                self.tag_word[key] = count
        
        self.tags = self.unigram.keys()
        
        for word, count in self.word_count.iteritems():
            if count < 5:
                for tag in self.tags:
                    self.tag_word[(tag, '_RARE_')] += self.tag_word[(tag, word)]
    
    def q(self, s, u, v):
        "Probability of the trigram (u, v, s) given the prefix bigram (u, v)"
        return self.trigram[(u,v,s)] / self.bigram[(u, v)]
    
    def e(self, word, tag):
        "Probability of the tag emitting the word"
        if tag in ["*", "STOP"]: return 0.0
        if self.word_count[word] < 5: word = '_RARE_'
        
        return self.tag_word[(tag, word)] / self.unigram[tag]
    
    def unigram_tagger(self, sentence):
        return [max([(self.e(word, tag), tag) for tag in self.tags])[1]
                for word in sentence]
    
    def K(self, k):
        if k in (-1, 0): return ["*"]
        return self.tags
    
    def viterbi_tagger(self, sentence):
        # Cleanup method calls
        K, q, e = self.K, self.q, self.e
        
        # Stores in bp the most likely tag (w) at position (k), for all the
        # possible combinations of tag bigram (u, v) at position (k+1, k+2)
        # pi is the maximum probability for any sequence of length k, ending in
        # the tag bigram (u, v)
        x, n = [""] + sentence, len(sentence)
        pi, bp = {(0,"*","*"): 1.0}, {}
        for k in range(1, n+1):
            for u, v in combinations(K(k-1), K(k)):
                pi[(k, u,v)], bp[(k, u,v)] = max([(
                        pi[(k-1, w,u)] * q(v,w,u) * e(x[k],v),
                        w
                    ) for w in K(k-2)])
        
        # Get the most likely ending tag bigram among all the possible (u, v)
        # combinations, then use these values to start following the back
        # pointers
        y = [""] * (n+1)
        _, (y[n-1], y[n]) = max([(
                pi[(n, u,v)] * q("STOP",u,v),
                (u,v)
            ) for u, v in combinations(K(n-1), K(n))])
        for k in range(n-2, 0, -1):
            y[k] = bp[(k+2, y[k+1], y[k+2])]
        return y[1:n+1]


def gen_counts(input_path, output_path):
    if exists(output_path): return
    
    print 'Generating counts from: "%s"' % input_path
    counter = Hmm(3)
    counter.train(open(input_path, 'r'))
    counter.write_counts(open(output_path, 'w'))


def read_sentence(f):
    sentence = []
    for line in f.readlines():
        if line != '\n':
            sentence.append(line.strip())
        else:
            yield sentence
            sentence = []


def write_tagged_sentence(f, tagged_sentence):
    for word, tag in tagged_sentence:
        f.write("%s %s\n" % (word, tag))
    f.write("\n")


def tag_sentences(tagger, tagger_name, input_path, output_path):
    tagger_method = getattr(tagger, tagger_name + '_tagger')
    with open(input_path, 'r') as in_f, open(output_path, 'wb') as out_f:
        for sentence in read_sentence(in_f):
            write_tagged_sentence(out_f, zip(sentence, tagger_method(sentence)))


def check_tagger(reference_path, dev_path):
    gs_iterator = corpus_iterator(file(reference_path))
    pred_iterator = corpus_iterator(file(dev_path), with_logprob = False)
    evaluator = Evaluator()
    evaluator.compare(gs_iterator, pred_iterator)
    evaluator.print_scores()


if __name__ == '__main__':
    gen_counts('gene.train', 'gene.counts')
    tagger = GeneTagger('gene.counts')
    tag_sentences(tagger, 'viterbi', 'gene.dev', 'gene.dev.out')
    check_tagger('gene.key', 'gene.dev.out')

########NEW FILE########
__FILENAME__ = eval_parser
#! /usr/bin/python
from __future__ import division
import sys, re, json
from collections import defaultdict

"""
Evaluate a set of test parses versus the gold set. 
"""

class ParseError(Exception):
  def __init__(self, value):
    self.value = value
    
  def __str__(self):
    return self.value


class TreeOperations:
  "Some basic operations on trees." 
  def __init__(self, tree): 
    self.tree = tree

  def _remove_vertical_markovization(self, nt):
    "Remove the vertical markovization." 
    return re.sub(r"\^<.*?>", '', nt)

  def _convert_to_spans(self, tree, start, set, parent = None): 
    "Convert a tree into spans (X, i, j) and add to a set." 
    if len(tree) == 3:
      # Binary rule.
      # Remove unary collapsing.
      current = self._remove_vertical_markovization(tree[0]).split("+")
      split = self._convert_to_spans(tree[1], start, set, None)
      end = self._convert_to_spans(tree[2], split + 1, set, current[-1])

      # Add phrases to set
      if current[0] != parent: 
        set.add((current[0], start, end))
      for nt in current[1:]:
        set.add((nt, start, end))
      return end
    elif len(tree) == 2:
      # Unary rule.
      
      # Can have a constituent if it is collapsed.
      current = self._remove_vertical_markovization(tree[0]).split("+")
      for nt in current[:-1]:
        set.add((nt, start, start))
      return start

  def to_spans(self):
    "Convert the tree to a set of nonterms and spans."
    s = set()
    self._convert_to_spans(self.tree, 1, s)
    return s

  def _fringe(self, node):
    if len(node) == 2: return [node[1]]
    else: return self._fringe(node[1]) + self._fringe(node[2])

  def fringe(self):
    "Return the fringe of the tree."
    return self._fringe(self.tree)

  def _well_formed(self, node):
    if len(node) not in [2, 3]:
      raise ParseError("Ill-formed tree:  %d-ary rule, only binary or unary allowed %s"%(len(node), node))
    
    if not isinstance(node[0], basestring):
      raise ParseError("Ill-formed tree: non-terminal not a string %s."%(node[0]))

    if len(node) == 2:
      if not isinstance(node[1], basestring):
        raise ParseError("Ill-formed tree: unary rule does not produce a string %s."%(node[1]))
    elif len(node) == 3:
      if isinstance(node[1], basestring):
        raise ParseError("Ill-formed tree: binary rule produces a string %s."%(node[1]))
      if isinstance(node[2], basestring):
        raise ParseError("Ill-formed tree: binary rule produces a string %s."%(node[2]))
      self._well_formed(node[1])
      self._well_formed(node[2])
      
  def check_well_formed(self):
    self._well_formed(self.tree)

class FScore:
  "Compute F1-Score based on gold set and test set."

  def __init__(self):
    self.gold = 0
    self.test = 0
    self.correct = 0

  def increment(self, gold_set, test_set):
    "Add examples from sets."
    self.gold += len(gold_set)
    self.test += len(test_set)
    self.correct += len(gold_set & test_set)

  def fscore(self): 
    pr = self.precision() + self.recall()
    if pr == 0: return 0.0
    return (2 * self.precision() * self.recall()) / pr

  def precision(self): 
    if self.test == 0: return 0.0
    return self.correct / self.test

  def recall(self): 
    if self.gold == 0: return 0.0
    return self.correct / self.gold    

  @staticmethod
  def output_header():
    "Output a scoring header."
    print "%10s  %10s  %10s  %10s   %10s"%(
      "Type", "Total", "Precision", "Recall", "F1-Score")
    print "==============================================================="

  def output_row(self, name):
    "Output a scoring row."
    print "%10s        %4d     %0.3f        %0.3f        %0.3f"%(
      name, self.gold, self.precision(), self.recall(), self.fscore())


class ParseEvaluator:
  def __init__(self):
    self.total_score = FScore()
    self.nt_score = defaultdict(FScore)
    
  def compute_fscore(self, key_trees, predicted_trees):
    for trees in zip(key_trees, predicted_trees):
      tops = map(TreeOperations, trees)
      tops[0].check_well_formed()
      tops[1].check_well_formed()
      f1, f2 = tops[0].fringe(), tops[1].fringe()

      if len(f1) != len(f2): 
        raise ParseError("Sentence length does not match. Gold sentence length %d, test sentence length %d. Sentence '%s'"%(len(f1), len(f2), " ".join(f1)))

      for gold, test in zip(f1, f2):
        if test != "_RARE_" and  gold != test:
          raise ParseError("Tree words do not match. Gold sentence '%s', test sentence '%s'."%(" ".join(f1), " ".join(f2)))
      set1, set2 = tops[0].to_spans(), tops[1].to_spans()

      # Compute non-terminal specific stats.
      for nt in set([s[0] for s in set1 | set2]):
        filter_s1 = set([s for s in set1 if s[0] == nt])
        filter_s2 = set([s for s in set2 if s[0] == nt])
        self.nt_score[nt].increment(filter_s1, filter_s2)

      # Compute total stats.
      self.total_score.increment(set1, set2)
    return self.total_score

  def output(self):
    "Print out the f-score table."
    FScore.output_header()
    nts = self.nt_score.keys()
    nts.sort()
    for nt in nts:
      self.nt_score[nt].output_row(nt)
    print
    self.total_score.output_row("total")

def main(key_file, prediction_file):
  key_trees = [json.loads(l) for l in key_file]
  predicted_trees = [json.loads(l) for l in prediction_file]
  evaluator = ParseEvaluator()
  evaluator.compute_fscore(key_trees, predicted_trees)
  evaluator.output()

if __name__ == "__main__": 
  if len(sys.argv) != 3:
    print >>sys.stderr, """
    Usage: python eval_parser.py [key_file] [output_file]
        Evalute the accuracy of a output trees compared to a key file.\n"""
    sys.exit(1)
  if sys.argv[1][-4:] != ".key":
    print >>sys.stderr, "First argument should end in '.key'."
    sys.exit(1)
  main(open(sys.argv[1]), open(sys.argv[2])) 



########NEW FILE########
__FILENAME__ = pcfg
from __future__ import division
from collections import Counter, defaultdict
from json import loads

from eval_parser import ParseEvaluator


def argmax(lst):
    return max(lst) if lst else (0.0, None)


class PCFG:
    def __init__(self, treebank):
        self.nonterminals = Counter()
        self.unary_rules = Counter()
        self.binary_rules = Counter()
        self.words = Counter()
        
        for s in open(treebank):
            self.count(loads(s))
        self.N = self.nonterminals.keys()
        
        # Set up binary rule table
        self.rules = defaultdict(list)
        for (sym, y1, y2) in self.binary_rules.keys():
            self.rules[sym].append((y1, y2))
        
        # Normalise the unary rules
        norm = Counter()
        for (sym, word), count in self.unary_rules.iteritems():
            norm[(sym, self.norm_word(word))] += count
        self.unary_rules = norm
    
    def count(self, tree):
        if isinstance(tree, basestring): return
        
        # Count the non-terminal symbols
        sym = tree[0]
        self.nonterminals[sym] += 1
        
        if len(tree) == 3:
            # Binary Rule
            y1, y2 = (tree[1][0], tree[2][0])
            self.binary_rules[(sym, y1, y2)] += 1
            
            # Recursively count the children
            self.count(tree[1])
            self.count(tree[2])
        
        elif len(tree) == 2:
            # Unary Rule
            word = tree[1]
            self.unary_rules[(sym, word)] += 1
            self.words[word] += 1
    
    def norm_word(self, word):
        return '_RARE_' if self.words[word] < 5 else word
    
    def q1(self, x, y):
        return self.unary_rules[(x, y)] / self.nonterminals[x]
    
    def q2(self, x, y1, y2):
        return self.binary_rules[(x, y1, y2)] / self.nonterminals[x]
    
    @staticmethod
    def backtrace(back, bp):
        # Extract the tree from the backpointers
        if not back: return None
        if len(back) == 6:
            (X, Y, Z, i, s, j) = back
            return [X, PCFG.backtrace(bp[i  , s, Y], bp),
                       PCFG.backtrace(bp[s+1, j, Z], bp)]
        else:
            (X, Y, i, i) = back
            return [X, Y]
    
    def CKY(self, sentence):
        x, n = [""] + sentence, len(sentence)
        
        # Charts
        pi = defaultdict(float)
        bp = {}
        for i in range(1, n+1):
            for X in self.N:
                if (X, x[i]) in self.unary_rules:
                    pi[i, i, X] = self.q1(X, x[i])
                    bp[i, i, X] = (X, x[i], i, i)
        
        # Dynamic program
        for l in range(1, n):
            for i in range(1, n-l+1):
                j = i+l
                for X in self.N:
                    # Note that we only check rules that exist in training
                    # and have non-zero probability
                    score, back = argmax([(
                            self.q2(X, Y, Z) * pi[i, s, Y] * pi[s+1, j, Z],
                            (X, Y, Z, i, s, j)
                        ) for s in range(i, j)
                            for Y, Z in self.rules[X]
                                if pi[i  , s, Y] > 0.0
                                if pi[s+1, j, Z] > 0.0
                    ])
                    
                    if score > 0.0:
                        bp[i, j, X], pi[i, j, X] = back, score
        
        return PCFG.backtrace(bp[1, n, "SBARQ"], bp)
    
    def parse(self, sentence):
        return self.CKY(map(self.norm_word, sentence.strip().split()))


def test(pcfg, dat_path, key_path):
    evaluator = ParseEvaluator()
    evaluator.compute_fscore(
        [loads(tree) for tree in open(key_path)],
        [pcfg.parse(sentence) for sentence in open(dat_path)])
    evaluator.output()


if __name__ == "__main__":
    test(PCFG("parse_train.dat"), "parse_dev.dat", "parse_dev.key")
    test(PCFG("parse_train_vert.dat"), "parse_dev.dat", "parse_dev.key")

########NEW FILE########
__FILENAME__ = gaussian
from math import sqrt, exp, pi


class Gaussian:
    def __init__(self, mu, sigma2):
        self.mu = float(mu)
        self.sigma2 = float(sigma2)
    
    def sense(self, measurement, sigma2):
        self.mu = (sigma2*self.mu + self.sigma2*measurement) / (self.sigma2 + sigma2)
        self.sigma2 = 1. / (1./self.sigma2 + 1./sigma2)
    
    def __str__(self):
        return "(mu:%.4f, sigma2:%.4f)" % (self.mu, self.sigma2)


if __name__ == '__main__':
    pos = Gaussian(1, 1)
    pos.sense(3, 1)
    print "Question 5: %s" % pos
########NEW FILE########
__FILENAME__ = localization
R, G = 'red', 'green'

class Array:
    def __init__(self, n, init=0.):
        self.data = [init]*n
        self.n = n
    
    def sum(self):
        return sum(self.data)
    
    def __str__(self):
        return str(self.data)


class UniformArray(Array):
    def __init__(self, n):
        prob = (1. / float(n))
        Array.__init__(self, n, prob)


class HistogramFilter:
    def __init__(self, world, measurement_error):
        self.world = world
        self.p = UniformArray(len(world))
        
        self.pHit  = (1. - measurement_error)
        self.pMiss = measurement_error
    
    def sense(self, Z):
        # Add sensor information
        for i in range(self.p.n):
            self.p.data[i] *= (self.pHit if self.world[i] == Z else self.pMiss)
        
        # Normalise
        s = self.p.sum()
        for i in range(self.p.n):
            self.p.data[i] /= s
    
    def move(self, i_delta):
        q = Array(self.p.n)
        for i in range(self.p.n):
            i_move = i + i_delta
            if i_move < 0: i_move = 0
            elif i_move >= self.p.n: i_move = (self.p.n - 1)
            
            q.data[i_move] += self.p.data[i]
        
        self.p = q
    
    def __str__(self):
        return str(self.p)


if __name__ == '__main__':
    WORLD = [G, G, R, G, R]
    MEASUREMENT_ERROR = 0.1
    
    f = HistogramFilter(WORLD, MEASUREMENT_ERROR)
    f.sense(R)
    print "Question 3: %s" % f
    
    f.move(1)
    
    p_red   = f.p.data[2] + f.p.data[4]
    p_green = f.p.data[0] + f.p.data[1] + f.p.data[3]
    
    pHit  = (1. - MEASUREMENT_ERROR)
    pMiss = MEASUREMENT_ERROR
    
    p_red_m = (p_red*pHit) + (p_green*pMiss)
    
    print "Question 4: %.5f" % p_red_m

########NEW FILE########
__FILENAME__ = warehouse_robot
# In this problem, you will build a planner that helps a robot
# find the shortest way in a warehouse filled with boxes
# that he has to pick up and deliver to a drop zone.
#
# For example:
#    warehouse = [[ 1, 2, 3],
#                 [ 0, 0, 0],
#                 [ 0, 0, 0]]
#    
#    dropzone = [2, 0] 
#    todo = [2, 1]
#
# Robot starts at the dropzone.
# Dropzone can be in any free corner of the warehouse map.
# todo is a list of boxes to be picked up and delivered to dropzone.
# Robot can move diagonally, but the cost of diagonal move is 1.5 
# Cost of moving one step horizontally or vertically is 1.0
# If the dropzone is at [2, 0], the cost to deliver box number 2
# would be 5.

# To pick up a box, robot has to move in the same cell with the box.
# When a robot picks up a box, that cell becomes passable (marked 0)
# Robot can pick up only one box at a time and once picked up 
# he has to return it to the dropzone by moving on to the cell.
# Once the robot has stepped on the dropzone, his box is taken away
# and he is free to continue with his todo list.
# Tasks must be executed in the order that they are given in the todo.
# You may assume that in all warehouse maps all boxes are
# reachable from beginning (robot is not boxed in).

# -------------------
# User Instructions
#
# Design a planner (any kind you like, so long as it works).
# This planner should be a function named plan() that takes
# as input three parameters: warehouse, dropzone and todo. 
# See parameter info below.
#
# Your function should RETURN the final, accumulated cost to do
# all tasks in the todo list in the given order and this cost
# must which should match with our answer).
# You may include print statements to show the optimum path,
# but that will have no effect on grading.
#
# Your solution must work for a variety of warehouse layouts and
# any length of todo list.
# 
# --------------------
# Parameter Info
#
# warehouse - a grid of values. where 0 means that the cell is passable,
# and a number between 1 and 99 shows where the boxes are.
# dropzone - determines robots start location and place to return boxes 
# todo - list of tasks, containing box numbers that have to be picked up
from math import sqrt

MOVES = [
    [-1, -1, 1.5], [-1,  0, 1.0], [-1,  1, 1.5],
    [ 0, -1, 1.0],                [ 0,  1, 1.0],
    [ 1, -1, 1.5], [ 1,  0, 1.0], [ 1,  1, 1.5],
]

class Map:
    def __init__(self, grid, gx, gy):
        self.gx, self.gy = gx, gy
        self.closed = [[0]*len(grid[0]) for _ in range(len(grid))]
        self.open = []
    
    def is_unexplored(self, x, y):
        return (self.closed[x][y] == 0)
    
    def heuristic(self, x, y):
        return sqrt((self.gx-x)**2 + (self.gy-y)**2)
    
    def add(self, cost, x, y):
        self.closed[x][y] = 1
        h = cost + self.heuristic(x, y)
        self.open.append([h, cost, x, y])
    
    def get_next(self):
        self.open.sort()
        _, cost, x, y = self.open.pop(0)
        return cost, x, y

class Warehouse:
    def __init__(self, warehouse, dropzone, todo):
        self.warehouse = warehouse
        self.dropzone = dropzone
        
        box_coordinates = {}
        for x in range(len(warehouse)):
            for y in range(len(warehouse[0])):
                n = warehouse[x][y]
                if n in ['x', 0]: continue
                else: box_coordinates[n] = [x, y]
        
        self.todo = [box_coordinates[n] for n in todo]
    
    def is_accessible(self, x, y):
        return (x >= 0 and x < len(self.warehouse)    and
                y >= 0 and y < len(self.warehouse[0]) and
                self.warehouse[x][y] == 0)
    
    def box_path_cost(self, bx, by):
        map = Map(self.warehouse, bx, by)
        map.add(0, self.dropzone[0], self.dropzone[1])
        
        while True:
            if len(map.open) == 0:
                raise Exception("No route from dropzone to box")
            
            cost, x, y = map.get_next()
            if x == bx and y == by:
                return cost
            
            for dx, dy, cm in MOVES:
                xm, ym = x+dx, y+dy
                if (self.is_accessible(xm, ym) and map.is_unexplored(xm, ym)):
                    map.add(cost+cm, xm, ym)
    
    def cost(self):
        c = 0
        for bx, by in self.todo:
            self.warehouse[bx][by] = 0
            c += self.box_path_cost(bx, by) * 2
        return c

def plan(warehouse, dropzone, todo):
    return Warehouse(warehouse, dropzone, todo).cost()

################# TESTING ##################
# ------------------------------------------
# solution check - Checks your plan function using
# data from list called test[].
def solution_check(test, epsilon = 0.00001):
    answer_list = []
    
    import time
    start = time.clock()
    correct_answers = 0
    for i in range(len(test[0])):
        user_cost = plan(test[0][i], test[1][i], test[2][i])
        true_cost = test[3][i]
        if abs(user_cost - true_cost) < epsilon:
            print "\nTest case", i+1, "passed!"
            answer_list.append(1)
            correct_answers += 1
            #print "#############################################"
        else:
            print "\nTest case ", i+1, "unsuccessful. Your answer ", user_cost, "was not within ", epsilon, "of ", true_cost 
            answer_list.append(0)
    runtime =  time.clock() - start
    if runtime > 1:
        print "Your code is too slow, try to optimize it! Running time was: ", runtime
        return False
    if correct_answers == len(answer_list):
        print "\nYou passed all test cases!"
        return True
    else:
        print "\nYou passed", correct_answers, "of", len(answer_list), "test cases. Try to get them all!"
        return False

#Testing environment
# Test Case 1 
warehouse1 = [[ 1, 2, 3],
             [ 0, 0, 0],
             [ 0, 0, 0]]
dropzone1 = [2, 0] 
todo1 = [2, 1]
true_cost1 = 9

# Test Case 2
warehouse2 = [[  1, 2, 3, 4],
             [   0, 0, 0, 0],
             [   5, 6, 7, 0],
             [ 'x', 0, 0, 8]] 
dropzone2 = [3, 0] 
todo2 = [2, 5, 1]
true_cost2 = 21

# Test Case 3
warehouse3 = [[  1, 2, 3, 4, 5, 6,  7],
             [   0, 0, 0, 0, 0, 0,  0],
             [   8, 9,10,11, 0, 0,  0],
             [ 'x', 0, 0, 0, 0, 0, 12]] 
dropzone3 = [3, 0] 
todo3 = [5, 10]
true_cost3 = 18

# Test Case 4
warehouse4 = [[  1,17, 5,18, 9,19, 13],
             [   2, 0, 6, 0,10, 0, 14],
             [   3, 0, 7, 0,11, 0, 15],
             [   4, 0, 8, 0,12, 0, 16],
             [   0, 0, 0, 0, 0, 0, 'x']] 
dropzone4 = [4, 6] 
todo4 = [13, 11, 6, 17]
true_cost4 = 41

testing_suite = [[warehouse1, warehouse2, warehouse3, warehouse4],
                 [dropzone1, dropzone2, dropzone3, dropzone4],
                 [todo1, todo2, todo3, todo4],
                 [true_cost1, true_cost2, true_cost3, true_cost4]]

solution_check(testing_suite)

########NEW FILE########
__FILENAME__ = homework
R, G = 'red', 'green'

def show(p):
    for i in range(len(p)):
        print p[i]

colors = [[R, G, G, R, R],
          [R, R, G, R, R],
          [R, R, G, G, R],
          [R, R, R, R, R]]

measurements = [G, G, G, G, G]
motions = [[0,0],[0,1],[1,0],[1,0],[0,1]]

sensor_right = 0.7
p_move = 0.8

#DO NOT USE IMPORT
#ENTER CODE BELOW HERE
#ANY CODE ABOVE WILL CAUSE
#HOMEWORK TO BE GRADED
#INCORRECT
pHit, pMiss = sensor_right, (1 - sensor_right)
pMove, pStill = p_move, (1 - p_move)

def matrix(rows, columns, init=0):
    return [[init]*columns for _ in range(rows)]

def uniform_matrix(rows, columns):
    prob = 1. / (rows * columns)
    return matrix(rows, columns, prob)

def size_matrix(world):
    return len(world), len(world[0])

def sum_matrix(m):
    s = 0.
    for row in m:
        s += sum(row) 
    return s

def sense(p, Z):
    n_rows, n_columns = size_matrix(p)
    
    # Add sensor information
    for i in range(n_rows):
        for j in range(n_columns):
            p[i][j] *= (pHit if colors[i][j] == Z else pMiss)
    
    # Normalise
    s = sum_matrix(p)
    for i in range(n_rows):
        for j in range(n_columns):
            p[i][j] /= s

def move(p, U):
    i_delta, j_delta = U
    n_rows, n_columns = size_matrix(p)
    q = matrix(n_rows, n_columns)
    
    for i in range(n_rows):
        for j in range(n_columns):
            i_move = (i - i_delta) % n_rows
            j_move = (j - j_delta) % n_columns
            q[i][j] = (pMove  * p[i_move][j_move] + pStill * p[i][j])
    
    return q

p = uniform_matrix(*size_matrix(colors))
for i in range(len(motions)):
    p = move(p, motions[i])
    sense(p, measurements[i])

#Your probability array must be printed 
#with the following code.
show(p)

########NEW FILE########
__FILENAME__ = unit_1
#Given the list motions=[1,1] which means the robot 
#moves right and then right again, compute the posterior 
#distribution if the robot first senses red, then moves 
#right one, then senses green, then moves right again, 
#starting with a uniform prior distribution.

p=[0.2, 0.2, 0.2, 0.2, 0.2]
world=['green', 'red', 'red', 'green', 'green']
measurements = ['red', 'green']
motions = [1,1]
pHit = 0.6
pMiss = 0.2
pExact = 0.8
pOvershoot = 0.1
pUndershoot = 0.1

def sense(p, Z):
    q=[]
    for i in range(len(p)):
        hit = (Z == world[i])
        q.append(p[i] * (hit * pHit + (1-hit) * pMiss))
    s = sum(q)
    for i in range(len(q)):
        q[i] = q[i] / s
    return q

def move(p, U):
    q = []
    for i in range(len(p)):
        s = pExact * p[(i-U) % len(p)]
        s = s + pOvershoot * p[(i-U-1) % len(p)]
        s = s + pUndershoot * p[(i-U+1) % len(p)]
        q.append(s)
    return q
#
# ADD CODE HERE
#
for i in range(len(motions)):
    p = sense(p, measurements[i])
    p = move(p, motions[i])

print p

########NEW FILE########
__FILENAME__ = gauss
from math import sqrt, exp, pi


class Gaussian:
    def __init__(self, mu, sigma2):
        self.mu = float(mu)
        self.sigma2 = float(sigma2)
        
        self.k1 = 1./sqrt(2.*pi*self.sigma2)
        self.k2 = -0.5/self.sigma2
    
    def value(self, x):
        return self.k1 * exp(self.k2 * (x-self.mu)**2)
    
    def sense(self, measurement, sigma2):
        self.mu = (sigma2*self.mu + self.sigma2*measurement) / (self.sigma2 + sigma2)
        self.sigma2 = 1. / (1./self.sigma2 + 1./sigma2)
    
    def move(self, motion, sigma2):
        self.mu = self.mu + motion
        self.sigma2 = self.sigma2 + sigma2
    
    def __str__(self):
        return "(mu:%.4f, sigma2:%.4f)" % (self.mu, self.sigma2)


if __name__ == '__main__':
    measurements = [5., 6., 7., 9., 10.]
    motion = [1., 1., 2., 1., 1.]
    measurement_sig = 4.
    motion_sig = 2.
    mu = 0
    sig = 10000
    pos = Gaussian(mu, sig)
    for i in range(len(measurements)):
        pos.sense(measurements[i], measurement_sig)
        pos.move(motion[i], motion_sig)
    
    print pos
########NEW FILE########
__FILENAME__ = homework
from matrix import matrix


def filter(x, P):
    for n in range(len(measurements)):
        
        # prediction
        x = (F * x) + u
        P = F * P * F.transpose()
        
        # measurement update
        Z = matrix([measurements[n]])
        y = Z.transpose() - (H * x)
        S = H * P * H.transpose() + R
        K = P * H.transpose() * S.inverse()
        x = x + (K * y)
        P = (I - (K * H)) * P
    
    print 'x= '
    x.show()
    print 'P= '
    P.show()


########################################
print "### 4-dimensional example ###"

measurements = [[5., 10.], [6., 8.], [7., 6.], [8., 4.], [9., 2.], [10., 0.]]
initial_xy = [4., 12.]

# measurements = [[1., 4.], [6., 0.], [11., -4.], [16., -8.]]
# initial_xy = [-4., 8.]

# measurements = [[1., 17.], [1., 15.], [1., 13.], [1., 11.]]
# initial_xy = [1., 19.]

# measurements = [[2., 17.], [0., 15.], [2., 13.], [0., 11.]]
# initial_xy = [1., 19.]

dt = 0.1

x = matrix([[initial_xy[0]], [initial_xy[1]], [0.], [0.]]) # initial state (location and velocity)
u = matrix([[0.], [0.], [0.], [0.]]) # external motion

P = matrix([[0., 0., 0., 0.],
            [0., 0., 0., 0.],
            [0., 0., 1000., 0.],
            [0., 0., 0., 1000.]]) # initial uncertainty
F = matrix([[1., 0., 0.1, 0. ],
            [0., 1., 0. , 0.1],
            [0., 0., 1. , 0. ],
            [0., 0., 0. , 1. ]]) # next state function
H = matrix([[1., 0., 0., 0.],
            [0., 1., 0., 0.]]) # measurement function
R = matrix([[0.1, 0. ],
            [0. , 0.1]]) # measurement uncertainty
I = matrix([[1., 0., 0., 0.],
            [0., 1., 0., 0.],
            [0., 0., 1., 0.],
            [0., 0., 0., 1.]]) # identity matrix

filter(x, P)

########NEW FILE########
__FILENAME__ = matrix
from math import *

class matrix:
    # implements basic operations of a matrix class
    
    def __init__(self, value):
        self.value = value
        self.dimx = len(value)
        self.dimy = len(value[0])
        if value == [[]]:
            self.dimx = 0
    
    def zero(self, dimx, dimy):
        # check if valid dimensions
        if dimx < 1 or dimy < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx = dimx
            self.dimy = dimy
            self.value = [[0 for row in range(dimy)] for col in range(dimx)]
    
    def identity(self, dim):
        # check if valid dimension
        if dim < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx = dim
            self.dimy = dim
            self.value = [[0 for row in range(dim)] for col in range(dim)]
            for i in range(dim):
                self.value[i][i] = 1
    
    def show(self):
        for i in range(self.dimx):
            print self.value[i]
        print ' '
    
    def __add__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimy != other.dimy:
            raise ValueError, "Matrices must be of equal dimensions to add"
        else:
            # add if correct dimensions
            res = matrix([[]])
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] + other.value[i][j]
            return res
    
    def __sub__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimy != other.dimy:
            raise ValueError, "Matrices must be of equal dimensions to subtract"
        else:
            # subtract if correct dimensions
            res = matrix([[]])
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] - other.value[i][j]
            return res
    
    def __mul__(self, other):
        # check if correct dimensions
        if self.dimy != other.dimx:
            raise ValueError, "Matrices must be m*n and n*p to multiply"
        else:
            # subtract if correct dimensions
            res = matrix([[]])
            res.zero(self.dimx, other.dimy)
            for i in range(self.dimx):
                for j in range(other.dimy):
                    for k in range(self.dimy):
                        res.value[i][j] += self.value[i][k] * other.value[k][j]
            return res
    
    def transpose(self):
        # compute transpose
        res = matrix([[]])
        res.zero(self.dimy, self.dimx)
        for i in range(self.dimx):
            for j in range(self.dimy):
                res.value[j][i] = self.value[i][j]
        return res
    
    # Thanks to Ernesto P. Adorio for use of Cholesky and CholeskyInverse functions
    
    def Cholesky(self, ztol=1.0e-5):
        # Computes the upper triangular Cholesky factorization of
        # a positive definite matrix.
        res = matrix([[]])
        res.zero(self.dimx, self.dimx)
        
        for i in range(self.dimx):
            S = sum([(res.value[k][i])**2 for k in range(i)])
            d = self.value[i][i] - S
            if abs(d) < ztol:
                res.value[i][i] = 0.0
            else:
                if d < 0.0:
                    raise ValueError, "Matrix not positive-definite"
                res.value[i][i] = sqrt(d)
            for j in range(i+1, self.dimx):
                S = sum([res.value[k][i] * res.value[k][j] for k in range(self.dimx)])
                if abs(S) < ztol:
                    S = 0.0
                res.value[i][j] = (self.value[i][j] - S)/res.value[i][i]
        return res
    
    def CholeskyInverse(self):
        # Computes inverse of matrix given its Cholesky upper Triangular
        # decomposition of matrix.
        res = matrix([[]])
        res.zero(self.dimx, self.dimx)
        
        # Backward step for inverse.
        for j in reversed(range(self.dimx)):
            tjj = self.value[j][j]
            S = sum([self.value[j][k]*res.value[j][k] for k in range(j+1, self.dimx)])
            res.value[j][j] = 1.0/tjj**2 - S/tjj
            for i in reversed(range(j)):
                res.value[j][i] = res.value[i][j] = -sum([self.value[i][k]*res.value[k][j] for k in range(i+1, self.dimx)])/self.value[i][i]
        return res
    
    def inverse(self):
        aux = self.Cholesky()
        res = aux.CholeskyInverse()
        return res
    
    def __repr__(self):
        return repr(self.value)

########NEW FILE########
__FILENAME__ = unit_2
# Write a function 'filter' that implements a multi-
# dimensional Kalman Filter for the example given
from matrix import matrix


def filter(x, P):
    for n in range(len(measurements)):
        # measurement update
        Z = matrix([[measurements[n]]])
        y = Z.transpose() - H * x
        S = H * P * H.transpose() + R
        K = P * H.transpose() * S.inverse()
        
        x = x + (K * y)
        P = (I - K * H) * P
        
        # prediction
        x = F * x + u
        P = F * P * F.transpose()
        
        print 'x= '
        x.show()
        print 'P= '
        P.show()

measurements = [1, 2, 3]

x = matrix([[0.], [0.]]) # initial state (location and velocity)
P = matrix([[1000., 0.], [0., 1000.]]) # initial uncertainty
u = matrix([[0.], [0.]]) # external motion
F = matrix([[1., 1.], [0, 1.]]) # next state function
H = matrix([[1., 0.]]) # measurement function
R = matrix([[1.]]) # measurement uncertainty
I = matrix([[1., 0.], [0., 1.]]) # identity matrix

filter(x, P)

########NEW FILE########
__FILENAME__ = homework
# --------------
# USER INSTRUCTIONS
#
# Now you will put everything together.
#
# First make sure that your sense and move functions
# work as expected for the test cases provided at the
# bottom of the previous two programming assignments.
# Once you are satisfied, copy your sense and move
# definitions into the robot class on this page, BUT
# now include noise.
#
# A good way to include noise in the sense step is to
# add Gaussian noise, centered at zero with variance
# of self.bearing_noise to each bearing. You can do this
# with the command random.gauss(0, self.bearing_noise)
#
# In the move step, you should make sure that your
# actual steering angle is chosen from a Gaussian
# distribution of steering angles. This distribution
# should be centered at the intended steering angle
# with variance of self.steering_noise.
#
# Feel free to use the included set_noise function.
#
# Please do not modify anything except where indicated
# below.

from math import *
import random



# --------
# 
# some top level parameters
#

max_steering_angle = pi / 4.0 # You do not need to use this value, but keep in mind the limitations of a real car.
bearing_noise = 0.1 # Noise parameter: should be included in sense function.
steering_noise = 0.1 # Noise parameter: should be included in move function.
distance_noise = 5.0 # Noise parameter: should be included in move function.

tolerance_xy = 15.0 # Tolerance for localization in the x and y directions.
tolerance_orientation = 0.25 # Tolerance for orientation.


# --------
# 
# the "world" has 4 landmarks.
# the robot's initial coordinates are somewhere in the square
# represented by the landmarks.
#
# NOTE: Landmark coordinates are given in (y, x) form and NOT
# in the traditional (x, y) format!

landmarks  = [[0.0, 100.0], [0.0, 0.0], [100.0, 0.0], [100.0, 100.0]] # position of 4 landmarks in (y, x) format.
world_size = 100.0 # world is NOT cyclic. Robot is allowed to travel "out of bounds"

# ------------------------------------------------
# 
# this is the robot class
#

class robot:

    # --------
    # init: 
    #    creates robot and initializes location/orientation 
    #

    def __init__(self, length = 20.0):
        self.x = random.random() * world_size # initial x position
        self.y = random.random() * world_size # initial y position
        self.orientation = random.random() * 2.0 * pi # initial orientation
        self.length = length # length of robot
        self.bearing_noise  = 0.0 # initialize bearing noise to zero
        self.steering_noise = 0.0 # initialize steering noise to zero
        self.distance_noise = 0.0 # initialize distance noise to zero

    # --------
    # set: 
    #    sets a robot coordinate
    #

    def set(self, new_x, new_y, new_orientation):

        if new_orientation < 0 or new_orientation >= 2 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation)

    # --------
    # set_noise: 
    #    sets the noise parameters
    #
    def set_noise(self, new_b_noise, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.bearing_noise  = float(new_b_noise)
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)

    # --------
    # measurement_prob
    #    computes the probability of a measurement
    #  

    def measurement_prob(self, measurements):

        # calculate the correct measurement
        predicted_measurements = self.sense(0) # Our sense function took 0 as an argument to switch off noise.


        # compute errors
        error = 1.0
        for i in range(len(measurements)):
            error_bearing = abs(measurements[i] - predicted_measurements[i])
            error_bearing = (error_bearing + pi) % (2.0 * pi) - pi # truncate
            

            # update Gaussian
            error *= (exp(- (error_bearing ** 2) / (self.bearing_noise ** 2) / 2.0) /  
                      sqrt(2.0 * pi * (self.bearing_noise ** 2)))

        return error
    
    def __repr__(self): #allows us to print robot attributes.
        return '[x=%.6s y=%.6s orient=%.6s]' % (str(self.x), str(self.y), 
                                                str(self.orientation))
    
    ############# ONLY ADD/MODIFY CODE BELOW HERE ###################
       
    # --------
    # move: 
    #   
    
    # copy your code from the previous exercise
    # and modify it so that it simulates motion noise
    # according to the noise parameters
    #           self.steering_noise
    #           self.distance_noise
    def move(self, motion): # Do not change the name of this function
        a, d = motion
        
        a += random.gauss(0.0, self.steering_noise)
        d += random.gauss(0.0, self.distance_noise)
        
        new_r = robot(self.length)
        new_r.set_noise(self.bearing_noise, self.steering_noise, self.distance_noise)
        
        b = (d / self.length) * tan(a)
        if abs(b) < 0.001:
            new_r.x = self.x + d * cos(self.orientation)
            new_r.y = self.y + d * sin(self.orientation)
        else:
            r = d / b
            cx = self.x - sin(self.orientation) * r
            cy = self.y + cos(self.orientation) * r
            new_r.x = cx + sin(self.orientation + b) * r
            new_r.y = cy - cos(self.orientation + b) * r
        
        new_r.orientation = (self.orientation + b) % (2. * pi)
        
        return new_r
    
    # --------
    # sense: 
    #    

    # copy your code from the previous exercise
    # and modify it so that it simulates bearing noise
    # according to
    #           self.bearing_noise
    def sense(self, noise=1): #do not change the name of this function
        bearings = []
        
        for y, x in landmarks:
            if noise:
                b = (atan2(y - self.y, x - self.x) + random.gauss(0, self.bearing_noise) - self.orientation) % (2. * pi)
            else:
                b = (atan2(y - self.y, x - self.x) - self.orientation) % (2. * pi)
            bearings.append(b)
        
        return bearings
    ############## ONLY ADD/MODIFY CODE ABOVE HERE ####################

# --------
#
# extract position from a particle set
# 

def get_position(p):
    x = 0.0
    y = 0.0
    orientation = 0.0
    for i in range(len(p)):
        x += p[i].x
        y += p[i].y
        # orientation is tricky because it is cyclic. By normalizing
        # around the first particle we are somewhat more robust to
        # the 0=2pi problem
        orientation += (((p[i].orientation - p[0].orientation + pi) % (2.0 * pi)) 
                        + p[0].orientation - pi)
    return [x / len(p), y / len(p), orientation / len(p)]

# --------
#
# The following code generates the measurements vector
# You can use it to develop your solution.
# 


def generate_ground_truth(motions):

    myrobot = robot()
    myrobot.set_noise(bearing_noise, steering_noise, distance_noise)

    Z = []
    T = len(motions)

    for t in range(T):
        myrobot = myrobot.move(motions[t])
        Z.append(myrobot.sense())
    #print 'Robot:    ', myrobot
    return [myrobot, Z]

# --------
#
# The following code prints the measurements associated
# with generate_ground_truth
#

def print_measurements(Z):

    T = len(Z)

    print 'measurements = [[%.8s, %.8s, %.8s, %.8s],' % \
        (str(Z[0][0]), str(Z[0][1]), str(Z[0][2]), str(Z[0][3]))
    for t in range(1,T-1):
        print '                [%.8s, %.8s, %.8s, %.8s],' % \
            (str(Z[t][0]), str(Z[t][1]), str(Z[t][2]), str(Z[t][3]))
    print '                [%.8s, %.8s, %.8s, %.8s]]' % \
        (str(Z[T-1][0]), str(Z[T-1][1]), str(Z[T-1][2]), str(Z[T-1][3]))

# --------
#
# The following code checks to see if your particle filter
# localizes the robot to within the desired tolerances
# of the true position. The tolerances are defined at the top.
#

def check_output(final_robot, estimated_position):

    error_x = abs(final_robot.x - estimated_position[0])
    error_y = abs(final_robot.y - estimated_position[1])
    error_orientation = abs(final_robot.orientation - estimated_position[2])
    error_orientation = (error_orientation + pi) % (2.0 * pi) - pi
    correct = error_x < tolerance_xy and error_y < tolerance_xy \
              and error_orientation < tolerance_orientation
    return correct



def particle_filter(motions, measurements, N=500): # I know it's tempting, but don't change N!
    # --------
    #
    # Make particles
    # 

    p = []
    for i in range(N):
        r = robot()
        r.set_noise(bearing_noise, steering_noise, distance_noise)
        p.append(r)

    # --------
    #
    # Update particles
    #     

    for t in range(len(motions)):
    
        # motion update (prediction)
        p2 = []
        for i in range(N):
            p2.append(p[i].move(motions[t]))
        p = p2

        # measurement update
        w = []
        for i in range(N):
            w.append(p[i].measurement_prob(measurements[t]))

        # resampling
        p3 = []
        index = int(random.random() * N)
        beta = 0.0
        mw = max(w)
        for i in range(N):
            beta += random.random() * 2.0 * mw
            while beta > w[index]:
                beta -= w[index]
                index = (index + 1) % N
            p3.append(p[index])
        p = p3
    
    return get_position(p)

## IMPORTANT: You may uncomment the test cases below to test your code.
## But when you submit this code, your test cases MUST be commented
## out.
##
## You can test whether your particle filter works using the
## function check_output (see test case 2). We will be using a similar
## function. Note: Even for a well-implemented particle filter this
## function occasionally returns False. This is because a particle
## filter is a randomized algorithm. We will be testing your code
## multiple times. Make sure check_output returns True at least 80%
## of the time.


 
## --------
## TEST CASES:
## 
##1) Calling the particle_filter function with the following
##    motions and measurements should return a [x,y,orientation]
##    vector near [x=93.476 y=75.186 orient=5.2664], that is, the
##    robot's true location.
##
motions = [[2. * pi / 10, 20.] for row in range(8)]
measurements = [[4.746936, 3.859782, 3.045217, 2.045506],
                [3.510067, 2.916300, 2.146394, 1.598332],
                [2.972469, 2.407489, 1.588474, 1.611094],
                [1.906178, 1.193329, 0.619356, 0.807930],
                [1.352825, 0.662233, 0.144927, 0.799090],
                [0.856150, 0.214590, 5.651497, 1.062401],
                [0.194460, 5.660382, 4.761072, 2.471682],
                [5.717342, 4.736780, 3.909599, 2.342536]]
##
print particle_filter(motions, measurements)

## 2) You can generate your own test cases by generating
##    measurements using the generate_ground_truth function.
##    It will print the robot's last location when calling it.
##
##
number_of_iterations = 6
motions = [[2. * pi / 20, 12.] for row in range(number_of_iterations)]

x = generate_ground_truth(motions)
final_robot = x[0]
measurements = x[1]
estimated_position = particle_filter(motions, measurements)
print_measurements(measurements)
print 'Ground truth:    ', final_robot
print 'Particle filter: ', estimated_position
print 'Code check:      ', check_output(final_robot, estimated_position)

########NEW FILE########
__FILENAME__ = unit_3
# In this exercise, please run your previous code twice.
# Please only modify the indicated area below!

from math import *
import random



landmarks  = [[20.0, 20.0], [80.0, 80.0], [20.0, 80.0], [80.0, 20.0]]
world_size = 100.0

class robot:
    def __init__(self):
        self.x = random.random() * world_size
        self.y = random.random() * world_size
        self.orientation = random.random() * 2.0 * pi
        self.forward_noise = 0.0;
        self.turn_noise    = 0.0;
        self.sense_noise   = 0.0;
    
    def set(self, new_x, new_y, new_orientation):
        if new_x < 0 or new_x >= world_size:
            raise ValueError, 'X coordinate out of bound'
        if new_y < 0 or new_y >= world_size:
            raise ValueError, 'Y coordinate out of bound'
        if new_orientation < 0 or new_orientation >= 2 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation)
    
    
    def set_noise(self, new_f_noise, new_t_noise, new_s_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.forward_noise = float(new_f_noise);
        self.turn_noise    = float(new_t_noise);
        self.sense_noise   = float(new_s_noise);
    
    
    def sense(self):
        Z = []
        for i in range(len(landmarks)):
            dist = sqrt((self.x - landmarks[i][0]) ** 2 + (self.y - landmarks[i][1]) ** 2)
            dist += random.gauss(0.0, self.sense_noise)
            Z.append(dist)
        return Z
    
    
    def move(self, turn, forward):
        if forward < 0:
            raise ValueError, 'Robot cant move backwards'         
        
        # turn, and add randomness to the turning command
        orientation = self.orientation + float(turn) + random.gauss(0.0, self.turn_noise)
        orientation %= 2 * pi
        
        # move, and add randomness to the motion command
        dist = float(forward) + random.gauss(0.0, self.forward_noise)
        x = self.x + (cos(orientation) * dist)
        y = self.y + (sin(orientation) * dist)
        x %= world_size    # cyclic truncate
        y %= world_size
        
        # set particle
        res = robot()
        res.set(x, y, orientation)
        res.set_noise(self.forward_noise, self.turn_noise, self.sense_noise)
        return res
    
    def Gaussian(self, mu, sigma, x):
        
        # calculates the probability of x for 1-dim Gaussian with mean mu and var. sigma
        return exp(- ((mu - x) ** 2) / (sigma ** 2) / 2.0) / sqrt(2.0 * pi * (sigma ** 2))
    
    
    def measurement_prob(self, measurement):
        
        # calculates how likely a measurement should be
        
        prob = 1.0;
        for i in range(len(landmarks)):
            dist = sqrt((self.x - landmarks[i][0]) ** 2 + (self.y - landmarks[i][1]) ** 2)
            prob *= self.Gaussian(dist, self.sense_noise, measurement[i])
        return prob
    
    
    
    def __repr__(self):
        return '[x=%.6s y=%.6s orient=%.6s]' % (str(self.x), str(self.y), str(self.orientation))



def eval(r, p):
    sum = 0.0;
    for i in range(len(p)): # calculate mean error
        dx = (p[i].x - r.x + (world_size/2.0)) % world_size - (world_size/2.0)
        dy = (p[i].y - r.y + (world_size/2.0)) % world_size - (world_size/2.0)
        err = sqrt(dx * dx + dy * dy)
        sum += err
    return sum / float(len(p))

#myrobot = robot()
#myrobot.set_noise(5.0, 0.1, 5.0)
#myrobot.set(30.0, 50.0, pi/2)
#myrobot = myrobot.move(-pi/2, 15.0)
#print myrobot.sense()
#myrobot = myrobot.move(-pi/2, 10.0)
#print myrobot.sense()

####   DON'T MODIFY ANYTHING ABOVE HERE! ENTER/MODIFY CODE BELOW ####
myrobot = robot()
myrobot = myrobot.move(0.1, 5.0)
Z = myrobot.sense()
N = 1000
T = 10 #Leave this as 10 for grading purposes.

p = []
for i in range(N):
    r = robot()
    r.set_noise(0.05, 0.05, 5.0)
    p.append(r)

for t in range(T):
    myrobot = myrobot.move(0.1, 5.0)
    Z = myrobot.sense()

    p2 = []
    for i in range(N):
        p2.append(p[i].move(0.1, 5.0))
    p = p2

    w = []
    for i in range(N):
        w.append(p[i].measurement_prob(Z))

    p3 = []
    index = int(random.random() * N)
    beta = 0.0
    mw = max(w)
    for i in range(N):
        beta += random.random() * 2.0 * mw
        while beta > w[index]:
            beta -= w[index]
            index = (index + 1) % N
        p3.append(p[index])
    p = p3
    #enter code here, make sure that you output 10 print statements.
    print eval(myrobot, p)

########NEW FILE########
__FILENAME__ = cyclic_smoothing
# -------------
# User Instructions
#
# Now you will be incorporating fixed points into
# your smoother. 
#
# You will need to use the equations from gradient
# descent AND the new equations presented in the
# previous lecture to implement smoothing with
# fixed points.
#
# Your function should return the newpath that it
# calculates. 
#
# Feel free to use the provided solution_check function
# to test your code. You can find it at the bottom.
#
# --------------
# Testing Instructions
# 
# To test your code, call the solution_check function with
# two arguments. The first argument should be the result of your
# smooth function. The second should be the corresponding answer.
# For example, calling
#
# solution_check(smooth(testpath1), answer1)
#
# should return True if your answer is correct and False if
# it is not.

from math import *

# Do not modify path inside your function.
path=[[0, 0], #fix 
      [1, 0],
      [2, 0],
      [3, 0],
      [4, 0],
      [5, 0],
      [6, 0], #fix
      [6, 1],
      [6, 2],
      [6, 3], #fix
      [5, 3],
      [4, 3],
      [3, 3],
      [2, 3],
      [1, 3],
      [0, 3], #fix
      [0, 2],
      [0, 1]]

# Do not modify fix inside your function
fix = [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0]

######################## ENTER CODE BELOW HERE #########################

def smooth(path, fix, weight_data = 0.0, weight_smooth = 0.1, tolerance = 0.00001):
    from copy import deepcopy
    newpath = deepcopy(path)
    
    change = tolerance
    gamma = weight_smooth * 0.5
    while change >= tolerance:
      change = 0.0
      for i in range(len(path)):
        if fix[i] == 0:
          for j in range(len(path[0])):
            old = newpath[i][j]
            yp1 = newpath[(i+1) % len(path)][j]
            yp2 = newpath[(i+2) % len(path)][j]
            ym1 = newpath[(i-1) % len(path)][j]
            ym2 = newpath[(i-2) % len(path)][j]
            
            newpath[i][j] += weight_data * ( path[i][j] - newpath[i][j] )
            newpath[i][j] += weight_smooth * ( yp1 + ym1 - (2.0 * newpath[i][j]) )
            
            newpath[i][j] += gamma * ( (2.0*ym1) - ym2 - newpath[i][j] )
            newpath[i][j] += gamma * ( (2.0*yp1) - yp2 - newpath[i][j] )
            change += abs(old - newpath[i][j])
    
    return newpath

##newpath = smooth(path)
##for i in range(len(path)):
##    print '['+ ', '.join('%.3f'%x for x in path[i]) +'] -> ['+ ', '.join('%.3f'%x for x in newpath[i]) +']'

# --------------------------------------------------
# check if two numbers are 'close enough,'used in
# solution_check function.
#
def close_enough(user_answer, true_answer, epsilon = 0.03):
    if abs(user_answer - true_answer) > epsilon:
        return False
    return True

# --------------------------------------------------
# check your solution against our reference solution for
# a variety of test cases (given below)
#
def solution_check(newpath, answer):
    if type(newpath) != type(answer):
        print "Error. You do not return a list."
        return False
    if len(newpath) != len(answer):
        print 'Error. Your newpath is not the correct length.'
        return False
    if len(newpath[0]) != len(answer[0]):
        print 'Error. Your entries do not contain an (x, y) coordinate pair.'
        return False
    for i in range(len(newpath)): 
        for j in range(len(newpath[0])):
            if not close_enough(newpath[i][j], answer[i][j]):
                print 'Error, at least one of your entries is not correct.'
                return False
    print "Test case correct!"
    return True

# --------------
# Testing Instructions
# 
# To test your code, call the solution_check function with
# two arguments. The first argument should be the result of your
# smooth function. The second should be the corresponding answer.
# For example, calling
#
# solution_check(smooth(testpath1), answer1)
#
# should return True if your answer is correct and False if
# it is not.

testpath1=[[0, 0], #fix
      [1, 0],
      [2, 0],
      [3, 0],
      [4, 0],
      [5, 0],
      [6, 0], #fix
      [6, 1],
      [6, 2],
      [6, 3], #fix
      [5, 3],
      [4, 3],
      [3, 3],
      [2, 3],
      [1, 3],
      [0, 3], #fix
      [0, 2],
      [0, 1]]
testfix1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0]
answer1 = [[0, 0],
           [0.7938620981547201, -0.8311168821106101],
           [1.8579052986461084, -1.3834788165869276],
           [3.053905318597796, -1.5745863173084],
           [4.23141390533387, -1.3784271816058231],
           [5.250184859723701, -0.8264215958231558],
           [6, 0],
           [6.415150091996651, 0.9836951698796843],
           [6.41942442687092, 2.019512290770163],
           [6, 3],
           [5.206131365604606, 3.831104483245191],
           [4.142082497497067, 4.383455704596517],
           [2.9460804122779813, 4.5745592975708105],
           [1.768574219397359, 4.378404668718541],
           [0.7498089205417316, 3.826409771585794],
           [0, 3],
           [-0.4151464728194156, 2.016311854977891],
           [-0.4194207879552198, 0.9804948340550833]]

testpath2 = [[0, 0], # fix
             [2, 0],
             [4, 0], # fix
             [4, 2],
             [4, 4], # fix
             [2, 4],
             [0, 4], # fix
             [0, 2]]
testfix2 = [1, 0, 1, 0, 1, 0, 1, 0]
answer2 = [[0, 0],
           [2.0116767115496095, -0.7015439080661671],
           [4, 0],
           [4.701543905420104, 2.0116768147460418],
           [4, 4],
           [1.9883231877640861, 4.701543807525115],
           [0, 4],
           [-0.7015438099112995, 1.9883232808252207]]

solution_check(smooth(testpath1, testfix1), answer1)

########NEW FILE########
__FILENAME__ = parameter_optimization
# Implement twiddle as shown in the previous two videos.
# Your accumulated error should be very small!
#
# Your twiddle function should RETURN the accumulated
# error. Try adjusting the parameters p and dp to make
# this error as small as possible.
#
# Try to get your error below 1.0e-10 with as few iterations
# as possible (too many iterations will cause a timeout).
from math import pi
from robot import robot

# run - does a single control run.
def run(params, printflag = False):
    myrobot = robot()
    myrobot.set(0.0, 1.0, 0.0)
    speed = 1.0
    err = 0.0
    int_crosstrack_error = 0.0
    N = 100
    # myrobot.set_noise(0.1, 0.0)
    myrobot.set_steering_drift(10.0 / 180.0 * pi) # 10 degree steering error


    crosstrack_error = myrobot.y


    for i in range(N * 2):

        diff_crosstrack_error = myrobot.y - crosstrack_error
        crosstrack_error = myrobot.y
        int_crosstrack_error += crosstrack_error

        steer = - params[0] * crosstrack_error  \
            - params[1] * diff_crosstrack_error \
            - int_crosstrack_error * params[2]
        myrobot = myrobot.move(steer, speed)
        if i >= N:
            err += (crosstrack_error ** 2)
        if printflag:
            print myrobot, steer
    return err / float(N)


def twiddle(tol = 0.001): #Make this tolerance bigger if you are timing out!
    n_params = 3
    params  = [0.0] * n_params
    dparams = [1.0] * n_params
    
    best_error = run(params)
    n = 0
    while sum(dparams) > tol:
        for i in range(n_params):
            params[i] += dparams[i]
            err = run(params)
            if err < best_error:
                best_error = err
                dparams[i] *= 1.1
            else:
                params[i] -= 2.0 * dparams[i]
                err = run(params)
                if err < best_error:
                    best_error = err
                    dparams[i] * 1.1
                else:
                    params[i] += dparams[i]
                    dparams[i] *= 0.9
        n+= 1
        print "Twiddle #", n, params, ' -> ', best_error
    
    return run(params)

twiddle()

########NEW FILE########
__FILENAME__ = path_smoothing
# -----------
# User Instructions
#
# Define a function smooth that takes a path as its input
# (with optional parameters for weight_data, weight_smooth)
# and returns a smooth path.
#
# Smoothing should be implemented by iteratively updating
# each entry in newpath until some desired level of accuracy
# is reached. The update should be done according to the
# gradient descent equations given in the previous video:
#
# If your function isn't submitting it is possible that the
# runtime is too long. Try sacrificing accuracy for speed.
# -----------


from math import *

# Don't modify path inside your function.
path = [[0, 0],
        [0, 1],
        [0, 2],
        [1, 2],
        [2, 2],
        [3, 2],
        [4, 2],
        [4, 3],
        [4, 4]]

# ------------------------------------------------
# smooth coordinates
#

def smooth(path, weight_data = 0.5, weight_smooth = 0.1, tolerance=0.000001):
    # Make a deep copy of path into newpath
    newpath = [[0 for col in range(len(path[0]))] for row in range(len(path))]
    for i in range(len(path)):
        for j in range(len(path[0])):
            newpath[i][j] = path[i][j]
    
    #### ENTER CODE BELOW THIS LINE ###
    while True:
        change = 0.0
        for i in range(1, len(path)-1):
            for j in range(len(path[0])):
                aux = newpath[i][j]
                newpath[i][j] += weight_data   * (path[i][j] - newpath[i][j])
                newpath[i][j] += weight_smooth * (newpath[i-1][j] + newpath[i+1][j] - (2.0 * newpath[i][j]))
                change += abs(aux - newpath[i][j])
        if change < tolerance: break
    
    return newpath # Leave this line for the grader!

# feel free to leave this and the following lines if you want to print.
newpath = smooth(path, 0.0, 0.1)

# thank you - EnTerr - for posting this on our discussion forum
for i in range(len(path)):
    print '['+ ', '.join('%.3f'%x for x in path[i]) +'] -> ['+ ', '.join('%.3f'%x for x in newpath[i]) +']'

########NEW FILE########
__FILENAME__ = pd_controller
# Implement a PD controller by running 100 iterations
# of robot motion. The steering angle should be set
# by the parameter tau so that:
#
# steering = -tau_p * CTE - tau_d * diff_CTE
# where differential crosstrack error (diff_CTE)
# is given by CTE(t) - CTE(t-1)
from robot import robot

# run - does a single control run.
def run(param1, param2):
    myrobot = robot()
    myrobot.set(0.0, 1.0, 0.0)
    speed = 1.0 # motion distance is equal to speed (we assume time = 1)
    N = 100
    
    setpoint = 0.0
    P = (myrobot.y - setpoint)
    
    for _ in range(N):
        D = myrobot.y - P
        P = (myrobot.y - setpoint)
        steer = -param1 * P -param2 * D
        myrobot = myrobot.move(steer, speed)
        print myrobot, steer

# Call your function with parameters of 0.2 and 3.0 and print results
run(0.2, 3.0)

########NEW FILE########
__FILENAME__ = pid_controller
# Implement a P controller by running 100 iterations
# of robot motion. The steering angle should be set
# by the parameter tau so that:
#
# steering = -tau_p * CTE - tau_d * diff_CTE - tau_i * int_CTE
#
# where the integrated crosstrack error (int_CTE) is
# the sum of all the previous crosstrack errors.
# This term works to cancel out steering drift.
# run - does a single control run.
from math import pi
from robot import robot

def run(param1, param2, param3):
    myrobot = robot()
    myrobot.set(0.0, 1.0, 0.0)
    speed = 1.0 # motion distance is equal to speed (we assume time = 1)
    N = 100
    myrobot.set_steering_drift(10.0 / 180.0 * pi) # 10 degree bias, this will be added in by the move function, you do not need to add it below!
    
    setpoint = 0.0
    P = (myrobot.y - setpoint)
    I = 0.0
    
    for _ in range(N):
        D = myrobot.y - P
        P = (myrobot.y - setpoint)
        I += P
        steer = -param1 * P -param2 * D -param3 * I
        myrobot = myrobot.move(steer, speed)
        print myrobot, steer

# Call your function with parameters of (0.2, 3.0, and 0.004)
run(0.2, 3.0, 0.004)

########NEW FILE########
__FILENAME__ = p_controller
# Implement a P controller by running 100 iterations
# of robot motion. The steering angle should be set
# by the parameter tau so that:
#
# steering = -tau * crosstrack_error
#
# Note that tau is called "param" in the function
# run to be completed below.
#
# Your code should print output that looks like
# the output shown in the video. That is, at each step:
# print myrobot, steering
from robot import robot

# run - does a single control run
def run(param):
    myrobot = robot()
    myrobot.set(0.0, 1.0, 0.0)
    speed = 1.0 # motion distance is equal to speed (we assume time = 1)
    N = 100
    
    setpoint = 0.0
    for _ in range(N):
        P = (myrobot.y - setpoint)
        steer = -param * P
        myrobot = myrobot.move(steer, speed)
        print myrobot, steer

run(0.1) # call function with parameter tau of 0.1 and print results

########NEW FILE########
__FILENAME__ = racetrack_control
# --------------
# User Instructions
# 
# Define a function cte in the robot class that will
# compute the crosstrack error for a robot on a
# racetrack with a shape as described in the video.
#
# You will need to base your error calculation on
# the robot's location on the track. Remember that 
# the robot will be traveling to the right on the
# upper straight segment and to the left on the lower
# straight segment.
#
# --------------
# Grading Notes
#
# We will be testing your cte function directly by
# calling it with different robot locations and making
# sure that it returns the correct crosstrack error.  
 
from math import *
import random


# ------------------------------------------------
# 
# this is the robot class
#

class robot:

    # --------
    # init: 
    #    creates robot and initializes location/orientation to 0, 0, 0
    #

    def __init__(self, length = 20.0):
        self.x = 0.0
        self.y = 0.0
        self.orientation = 0.0
        self.length = length
        self.steering_noise = 0.0
        self.distance_noise = 0.0
        self.steering_drift = 0.0

    # --------
    # set: 
    #    sets a robot coordinate
    #

    def set(self, new_x, new_y, new_orientation):

        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation) % (2.0 * pi)


    # --------
    # set_noise: 
    #    sets the noise parameters
    #

    def set_noise(self, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)

    # --------
    # set_steering_drift: 
    #    sets the systematical steering drift parameter
    #

    def set_steering_drift(self, drift):
        self.steering_drift = drift
        
    # --------
    # move: 
    #    steering = front wheel steering angle, limited by max_steering_angle
    #    distance = total distance driven, most be non-negative

    def move(self, steering, distance, 
             tolerance = 0.001, max_steering_angle = pi / 4.0):

        if steering > max_steering_angle:
            steering = max_steering_angle
        if steering < -max_steering_angle:
            steering = -max_steering_angle
        if distance < 0.0:
            distance = 0.0


        # make a new copy
        res = robot()
        res.length         = self.length
        res.steering_noise = self.steering_noise
        res.distance_noise = self.distance_noise
        res.steering_drift = self.steering_drift

        # apply noise
        steering2 = random.gauss(steering, self.steering_noise)
        distance2 = random.gauss(distance, self.distance_noise)

        # apply steering drift
        steering2 += self.steering_drift

        # Execute motion
        turn = tan(steering2) * distance2 / res.length

        if abs(turn) < tolerance:

            # approximate by straight line motion

            res.x = self.x + (distance2 * cos(self.orientation))
            res.y = self.y + (distance2 * sin(self.orientation))
            res.orientation = (self.orientation + turn) % (2.0 * pi)

        else:

            # approximate bicycle model for motion

            radius = distance2 / turn
            cx = self.x - (sin(self.orientation) * radius)
            cy = self.y + (cos(self.orientation) * radius)
            res.orientation = (self.orientation + turn) % (2.0 * pi)
            res.x = cx + (sin(res.orientation) * radius)
            res.y = cy - (cos(res.orientation) * radius)

        return res




    def __repr__(self):
        return '[x=%.5f y=%.5f orient=%.5f]'  % (self.x, self.y, self.orientation)


############## ONLY ADD / MODIFY CODE BELOW THIS LINE ####################
    def cte(self, radius):
        cte = 0.
        if self.y > radius and self.x <= 3 * radius and self.x >= radius:
            cte = self.y - (2*radius)
          
        elif self.y < radius and self.x <= 3 * radius and self.x >= radius:
            cte = -self.y
        
        elif self.x <= radius:
            sy = self.y - radius
            sx = self.x - radius
            theta = atan2(sy,sx)
            
            x1 = radius * cos(theta)
            y1 = radius * sin(theta)
            lrobot = sqrt(sy*sy + sx*sx)
            lpath = sqrt(x1*x1 + y1*y1)
            cte = lrobot - lpath
        
        elif self.x >= 3 * radius:
            sy = self.y-radius
            sx = self.x-(3*radius)
            theta = atan2(sy,sx)
            
            x1 = radius * cos(theta)
            y1 = radius * sin(theta)
            lrobot = sqrt(sy*sy + sx*sx)
            lpath = sqrt(x1*x1 + y1*y1)
            cte = lrobot - lpath
        
        return cte
    
############## ONLY ADD / MODIFY CODE ABOVE THIS LINE ####################




# ------------------------------------------------------------------------
#
# run - does a single control run.


def run(params, radius, printflag = False):
    myrobot = robot()
    myrobot.set(0.0, radius, pi / 2.0)
    speed = 1.0 # motion distance is equal to speed (we assume time = 1)
    err = 0.0
    int_crosstrack_error = 0.0
    N = 200

    crosstrack_error = myrobot.cte(radius) # You need to define the cte function!

    for i in range(N*2):
        diff_crosstrack_error = - crosstrack_error
        crosstrack_error = myrobot.cte(radius)
        diff_crosstrack_error += crosstrack_error
        int_crosstrack_error += crosstrack_error
        steer = - params[0] * crosstrack_error \
                - params[1] * diff_crosstrack_error \
                - params[2] * int_crosstrack_error
        myrobot = myrobot.move(steer, speed)
        if i >= N:
            err += crosstrack_error ** 2
        if printflag:
            print myrobot
    return err / float(N)

radius = 25.0
params = [10.0, 15.0, 0]
err = run(params, radius, True)
print '\nFinal paramaeters: ', params, '\n ->', err

########NEW FILE########
__FILENAME__ = robot
from math import *
import random

# this is the robot class
class robot:
    # init: 
    #    creates robot and initializes location/orientation to 0, 0, 0
    def __init__(self, length = 20.0):
        self.x = 0.0
        self.y = 0.0
        self.orientation = 0.0
        self.length = length
        self.steering_noise = 0.0
        self.distance_noise = 0.0
        self.steering_drift = 0.0
    
    # set: 
    #    sets a robot coordinate
    def set(self, new_x, new_y, new_orientation):
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation) % (2.0 * pi)
    
    # set_noise: 
    #    sets the noise parameters
    def set_noise(self, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)
    
    # set_steering_drift: 
    #    sets the systematical steering drift parameter
    def set_steering_drift(self, drift):
        self.steering_drift = drift
    
    # move: 
    #    steering = front wheel steering angle, limited by max_steering_angle
    #    distance = total distance driven, most be non-negative
    def move(self, steering, distance, 
             tolerance = 0.001, max_steering_angle = pi / 4.0):
        
        if steering > max_steering_angle:
            steering = max_steering_angle
        if steering < -max_steering_angle:
            steering = -max_steering_angle
        if distance < 0.0:
            distance = 0.0
        
        # make a new copy
        res = robot()
        res.length         = self.length
        res.steering_noise = self.steering_noise
        res.distance_noise = self.distance_noise
        res.steering_drift = self.steering_drift
        
        # apply noise
        steering2 = random.gauss(steering, self.steering_noise)
        distance2 = random.gauss(distance, self.distance_noise)
        
        # apply steering drift
        steering2 += self.steering_drift
        
        # Execute motion
        turn = tan(steering2) * distance2 / res.length
        
        if abs(turn) < tolerance:
            # approximate by straight line motion
            res.x = self.x + (distance2 * cos(self.orientation))
            res.y = self.y + (distance2 * sin(self.orientation))
            res.orientation = (self.orientation + turn) % (2.0 * pi)
        
        else:
            # approximate bicycle model for motion
            radius = distance2 / turn
            cx = self.x - (sin(self.orientation) * radius)
            cy = self.y + (cos(self.orientation) * radius)
            res.orientation = (self.orientation + turn) % (2.0 * pi)
            res.x = cx + (sin(res.orientation) * radius)
            res.y = cy - (cos(res.orientation) * radius)
        
        return res
    
    def __repr__(self):
        return '[x=%.5f y=%.5f orient=%.5f]'  % (self.x, self.y, self.orientation)

########NEW FILE########
__FILENAME__ = a_star
# -----------
# User Instructions:
#
# Modify the the search function so that it becomes
# an A* search algorithm as defined in the previous
# lectures.
#
# Your function should return the expanded grid
# which shows, for each element, the count when
# it was expanded or -1 if the element was never expanded.
# In case the obstacles prevent reaching the goal,
# the function should return "Fail"
#
# You do not need to modify the heuristic.
# ----------

grid = [[0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0]]

heuristic = [[9, 8, 7, 6, 5, 4],
            [8, 7, 6, 5, 4, 3],
            [7, 6, 5, 4, 3, 2],
            [6, 5, 4, 3, 2, 1],
            [5, 4, 3, 2, 1, 0]]

init = [0, 0]
goal = [len(grid)-1, len(grid[0])-1]

delta = [[-1, 0 ], # go up
         [ 0, -1], # go left
         [ 1, 0 ], # go down
         [ 0, 1 ]] # go right

delta_name = ['^', '<', 'v', '>']

cost = 1

# ----------------------------------------
# modify code below
# ----------------------------------------

def search():
    closed = [[0 for row in range(len(grid[0]))] for col in range(len(grid))]
    closed[init[0]][init[1]] = 1
    
    expand = [[-1 for row in range(len(grid[0]))] for col in range(len(grid))]
    action = [[-1 for row in range(len(grid[0]))] for col in range(len(grid))]
    
    x = init[0]
    y = init[1]
    g = 0
    h = heuristic[x][y]
    f = g + h
    
    open = [[f, g, h, x, y]]
    
    found = False  # flag that is set when search is complete
    resign = False # flag set if we can't find expand
    count = 0
    
    while not found and not resign:
        if len(open) == 0:
            resign = True
            return "Fail"
        else:
            open.sort()
            open.reverse()
            next = open.pop()
            x = next[3]
            y = next[4]
            g = next[1]
            expand[x][y] = count
            count += 1
            
            if x == goal[0] and y == goal[1]:
                found = True
            else:
                for i in range(len(delta)):
                    x2 = x + delta[i][0]
                    y2 = y + delta[i][1]
                    if x2 >= 0 and x2 < len(grid) and y2 >=0 and y2 < len(grid[0]):
                        if closed[x2][y2] == 0 and grid[x2][y2] == 0:
                            g2 = g + cost
                            h2 = heuristic[x2][y2]
                            f2 = g2 + h2
                            open.append([f2, g2, h2, x2, y2])
                            closed[x2][y2] = 1
    for i in range(len(expand)):
        print expand[i]
    return expand #Leave this line for grading purposes!

search()

########NEW FILE########
__FILENAME__ = dynamic_programming
# ----------
# User Instructions:
# 
# Create a function compute_value() which returns
# a grid of values. Value is defined as the minimum
# number of moves required to get from a cell to the
# goal. 
#
# If it is impossible to reach the goal from a cell
# you should assign that cell a value of 99.

# ----------

grid = [[0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0]]

init = [0, 0]
goal = [len(grid)-1, len(grid[0])-1]

delta = [[-1, 0 ], # go up
         [ 0, -1], # go left
         [ 1, 0 ], # go down
         [ 0, 1 ]] # go right

delta_name = ['^', '<', 'v', '>']

cost_step = 1 # the cost associated with moving from a cell to an adjacent one.

# ----------------------------------------
# insert code below
# ----------------------------------------
def optimum_policy():
    value  = [[99 for row in range(len(grid[0]))] for col in range(len(grid))]
    policy = [[' ' for row in range(len(grid[0]))] for col in range(len(grid))]
    change = True
    
    while change:
        change = False
        
        for x in range(len(grid)):
            for y in range(len(grid[0])):
                
                if goal[0] == x and goal[1] == y:
                    if value[x][y] > 0:
                        value[x][y] = 0
                        policy[x][y] = '*'
                        change = True
                
                elif grid[x][y] == 0:
                    for a in range(len(delta)):
                        x2 = x + delta[a][0]
                        y2 = y + delta[a][1]
                        
                        if (x2 >= 0 and x2 < len(grid)    and
                            y2 >= 0 and y2 < len(grid[0]) and
                            grid[x2][y2] == 0):
                            
                            v2 = value[x2][y2] + cost_step
                            
                            if v2 < value[x][y]:
                                change = True
                                value[x][y] = v2
                                policy[x][y] = delta_name[a]
    return policy

for row in optimum_policy():
    print row


########NEW FILE########
__FILENAME__ = first_search
# -----------
# User Instructions:
# 
# Modify the function search() so that it returns
# a table of values called expand. This table
# will keep track of which step each node was
# expanded.
#
# For grading purposes, please leave the return
# statement at the bottom.
# ----------


grid = [[0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 1, 0],
        [0, 0, 1, 0, 1, 0],
        [0, 0, 1, 0, 1, 0]]

init = [0, 0]
goal = [len(grid)-1, len(grid[0])-1]

delta = [[-1, 0 ], # go up
         [ 0, -1], # go left
         [ 1, 0 ], # go down
         [ 0, 1 ]] # go right

delta_name = ['^', '<', 'v', '>']

cost = 1


# ----------------------------------------
# modify code below
# ----------------------------------------

def search():
    closed = [[0 for row in range(len(grid[0]))] for col in range(len(grid))]
    closed[init[0]][init[1]] = 1
    expand = [[-1 for row in range(len(grid[0]))] for col in range(len(grid))]
    action = [[-1 for row in range(len(grid[0]))] for col in range(len(grid))]
    
    x = init[0]
    y = init[1]
    g = 0
    
    open = [[g, x, y]]
    
    found = False  # flag that is set when search is complete
    resign = False # flag set if we can't find expand
    count = 0
    while not found and not resign:
        if len(open) == 0:
            resign = True
        else:
            open.sort()
            open.reverse()
            next = open.pop()
            x = next[1]
            y = next[2]
            g = next[0]
            expand[x][y] = count
            count += 1
            
            if x == goal[0] and y == goal[1]:
                found = True
            else:
                for i in range(len(delta)):
                    x2 = x + delta[i][0]
                    y2 = y + delta[i][1]
                    if x2 >= 0 and x2 < len(grid) and y2 >=0 and y2 < len(grid[0]):
                        if closed[x2][y2] == 0 and grid[x2][y2] == 0:
                            g2 = g + cost
                            open.append([g2, x2, y2])
                            closed[x2][y2] = 1
                            action[x2][y2] = i
    
    policy = [[' ' for row in range(len(grid[0]))] for col in range(len(grid))]
    x, y = goal[0], goal[1]
    policy[x][y] = '*'
    while x != init[0] or y != init[1]:
        x2 = x - delta[action[x][y]][0]
        y2 = y - delta[action[x][y]][1]
        policy[x2][y2] = delta_name[action[x][y]]
        x, y = x2, y2
    
    return policy

for row in search():
    print row

########NEW FILE########
__FILENAME__ = homework
# --------------
# USER INSTRUCTIONS
#
# Write a function called stochastic_value that 
# takes no input and RETURNS two grids. The
# first grid, value, should contain the computed
# value of each cell as shown in the video. The
# second grid, policy, should contain the optimum
# policy for each cell.
#
# Stay tuned for a homework help video! This should
# be available by Thursday and will be visible
# in the course content tab.
#
# Good luck! Keep learning!
#
# --------------
# GRADING NOTES
#
# We will be calling your stochastic_value function
# with several different grids and different values
# of success_prob, collision_cost, and cost_step.
# In order to be marked correct, your function must
# RETURN (it does not have to print) two grids,
# value and policy.
#
# When grading your value grid, we will compare the
# value of each cell with the true value according
# to this model. If your answer for each cell
# is sufficiently close to the correct answer
# (within 0.001), you will be marked as correct.
#
# NOTE: Please do not modify the values of grid,
# success_prob, collision_cost, or cost_step inside
# your function. Doing so could result in your
# submission being inappropriately marked as incorrect.

# -------------
# GLOBAL VARIABLES
#
# You may modify these variables for testing
# purposes, but you should only modify them here.
# Do NOT modify them inside your stochastic_value
# function.
grid = [[0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 1, 1, 0]]

goal = [0, len(grid[0])-1] # Goal is in top right corner

delta = [[-1, 0 ], # go up
         [ 0, -1], # go left
         [ 1, 0 ], # go down
         [ 0, 1 ]] # go right

delta_name = ['^', '<', 'v', '>'] # Use these when creating your policy grid.

success_prob = 0.5
failure_prob = (1.0 - success_prob)/2.0 # Probability(stepping left) = prob(stepping right) = failure_prob
collision_cost = 100
cost_step = 1

############## INSERT/MODIFY YOUR CODE BELOW ##################
#
# You may modify the code below if you want, but remember that
# your function must...
#
# 1) ...be called stochastic_value().
# 2) ...NOT take any arguments.
# 3) ...return two grids: FIRST value and THEN policy.
def stochastic_value():
    value  = [[1000]*len(grid[0]) for _ in grid]
    policy = [[' ' ]*len(grid[0]) for _ in grid]
    
    change = True
    while change:
        change = False
        
        for x in range(len(grid)):
            for y in range(len(grid[0])):
                
                if goal[0] == x and goal[1] == y:
                    if value[x][y] > 0:
                        value[x][y] = 0
                        policy[x][y] = '*'
                        change = True
                
                elif grid[x][y] == 0:
                    for a in range(len(delta)):
                        
                        v2 = cost_step
                        
                        for i in [-1, 0, 1]:
                            a2 = (a + i) % len(delta)
                            x2 = x + delta[a2][0]
                            y2 = y + delta[a2][1]
                            
                            if i == 0:
                                p2 = success_prob
                            else:
                                p2 = failure_prob
                            
                            if (x2 >= 0 and x2 < len(grid)    and
                                y2 >= 0 and y2 < len(grid[0]) and
                                grid[x2][y2] == 0):
                                v2 += p2 * value[x2][y2]
                            else:
                                v2 += p2 * collision_cost
                        
                        if v2 < value[x][y]:
                            change = True
                            value[x][y] = v2
                            policy[x][y] = delta_name[a]
    
    return value, policy

value, policy = stochastic_value()
for row in value : print row
for row in policy: print row

########NEW FILE########
__FILENAME__ = left_turn_policy
# ----------
# User Instructions:
# 
# Implement the function optimum_policy2D() below.
#
# You are given a car in a grid with initial state
# init = [x-position, y-position, orientation]
# where x/y-position is its position in a given
# grid and orientation is 0-3 corresponding to 'up',
# 'left', 'down' or 'right'.
#
# Your task is to compute and return the car's optimal
# path to the position specified in `goal'; where
# the costs for each motion are as defined in `cost'.

# EXAMPLE INPUT:

# grid format:
#     0 = navigable space
#     1 = occupied space 
grid = [[1, 1, 1, 0, 0, 0],
        [1, 1, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0],
        [1, 1, 1, 0, 1, 1],
        [1, 1, 1, 0, 1, 1]]
goal = [2, 0] # final position
init = [4, 3, 0] # first 2 elements are coordinates, third is direction
cost = [2, 1, 20] # the cost field has 3 values: right turn, no turn, left turn

# EXAMPLE OUTPUT:
# calling optimum_policy2D() should return the array
# 
# [[' ', ' ', ' ', 'R', '#', 'R'],
#  [' ', ' ', ' ', '#', ' ', '#'],
#  ['*', '#', '#', '#', '#', 'R'],
#  [' ', ' ', ' ', '#', ' ', ' '],
#  [' ', ' ', ' ', '#', ' ', ' ']]
#
# ----------


# there are four motion directions: up/left/down/right
# increasing the index in this array corresponds to
# a left turn. Decreasing is is a right turn.

forward = [[-1,  0], # go up
           [ 0, -1], # go left
           [ 1,  0], # go down
           [ 0,  1]] # do right
forward_name = ['up', 'left', 'down', 'right']

# the cost field has 3 values: right turn, no turn, left turn
action = [-1, 0, 1]
action_name = ['R', '#', 'L']


# ----------------------------------------
# modify code below
# ----------------------------------------

def optimum_policy2D():
    value    = [[[999 for row in range(len(grid[0]))] for col in range(len(grid))],
                [[999 for row in range(len(grid[0]))] for col in range(len(grid))],
                [[999 for row in range(len(grid[0]))] for col in range(len(grid))],
                [[999 for row in range(len(grid[0]))] for col in range(len(grid))]]
    policy   = [[[' ' for row in range(len(grid[0]))] for col in range(len(grid))],
                [[' ' for row in range(len(grid[0]))] for col in range(len(grid))],
                [[' ' for row in range(len(grid[0]))] for col in range(len(grid))],
                [[' ' for row in range(len(grid[0]))] for col in range(len(grid))]]
    
    policy2D = [[' ' for row in range(len(grid[0]))] for col in range(len(grid))]
    
    change = True
    while change:
        change = False
        
        for x in range(len(grid)):
            for y in range(len(grid[0])):
                for orientation in range(4):
                    
                    if goal[0] == x and goal[1] == y:
                        if value[orientation][x][y] > 0:
                            value[orientation][x][y] = 0
                            policy[orientation][x][y] = '*'
                            change = True
                    
                    elif grid[x][y] == 0:
                        for a in range(len(action)):
                            o2 = (orientation + action[a]) % 4
                            x2 = x + forward[o2][0]
                            y2 = y + forward[o2][1]
                            
                            if (x2 >= 0 and x2 < len(grid)    and
                                y2 >= 0 and y2 < len(grid[0]) and
                                grid[x2][y2] == 0):
                                
                                v2 = value[o2][x2][y2] + cost[a]
                                
                                if v2 < value[orientation][x][y]:
                                    value[orientation][x][y] = v2
                                    policy[orientation][x][y] = action_name[a]
                                    change = True
    
    x = init[0]
    y = init[1]
    orientation = init[2]
    policy2D[x][y] = policy[orientation][x][y]
    while policy[orientation][x][y] != '*':
        if policy[orientation][x][y] == '#':
            o2 = orientation
        elif policy[orientation][x][y] == 'R':
            o2 = (orientation - 1) % 4
        elif policy[orientation][x][y] == 'L':
            o2 = (orientation + 1) % 4
        x = x + forward[o2][0]
        y = y + forward[o2][1]
        orientation = o2
        policy2D[x][y] = policy[orientation][x][y]
    
    return policy2D

for row in optimum_policy2D():
    print row


########NEW FILE########
__FILENAME__ = cte
# -----------
# User Instructions
#
# The point of this exercise is to find the optimal
# parameters! You can write a twiddle function or you
# can use any other method
# that you like. Since we don't know what the optimal
# parameters are, we will be very loose with the 
# grading. If you find parameters that work well, post 
# them in the forums!
#
# Note: when we first released this problem, we 
# included a twiddle function. But that's no fun!
# Try coding up your own parameter optimization
# and see how quickly you can get to the goal.
#
# You can find the parameters at line 581.
 
from math import *
import random


# don't change the noise paameters

steering_noise    = 0.1
distance_noise    = 0.03
measurement_noise = 0.3


class plan:

    # --------
    # init: 
    #    creates an empty plan
    #

    def __init__(self, grid, init, goal, cost = 1):
        self.cost = cost
        self.grid = grid
        self.init = init
        self.goal = goal
        self.make_heuristic(grid, goal, self.cost)
        self.path = []
        self.spath = []

    # --------
    #
    # make heuristic function for a grid
        
    def make_heuristic(self, grid, goal, cost):
        self.heuristic = [[0 for row in range(len(grid[0]))] 
                          for col in range(len(grid))]
        for i in range(len(self.grid)):    
            for j in range(len(self.grid[0])):
                self.heuristic[i][j] = abs(i - self.goal[0]) + \
                    abs(j - self.goal[1])



    # ------------------------------------------------
    # 
    # A* for searching a path to the goal
    #
    #

    def astar(self):


        if self.heuristic == []:
            raise ValueError, "Heuristic must be defined to run A*"

        # internal motion parameters
        delta = [[-1,  0], # go up
                 [ 0,  -1], # go left
                 [ 1,  0], # go down
                 [ 0,  1]] # do right


        # open list elements are of the type: [f, g, h, x, y]

        closed = [[0 for row in range(len(self.grid[0]))] 
                  for col in range(len(self.grid))]
        action = [[0 for row in range(len(self.grid[0]))] 
                  for col in range(len(self.grid))]

        closed[self.init[0]][self.init[1]] = 1


        x = self.init[0]
        y = self.init[1]
        h = self.heuristic[x][y]
        g = 0
        f = g + h

        open = [[f, g, h, x, y]]

        found  = False # flag that is set when search complete
        resign = False # flag set if we can't find expand
        count  = 0


        while not found and not resign:

            # check if we still have elements on the open list
            if len(open) == 0:
                resign = True
                print '###### Search terminated without success'
                
            else:
                # remove node from list
                open.sort()
                open.reverse()
                next = open.pop()
                x = next[3]
                y = next[4]
                g = next[1]

            # check if we are done

            if x == goal[0] and y == goal[1]:
                found = True
                # print '###### A* search successful'

            else:
                # expand winning element and add to new open list
                for i in range(len(delta)):
                    x2 = x + delta[i][0]
                    y2 = y + delta[i][1]
                    if x2 >= 0 and x2 < len(self.grid) and y2 >= 0 \
                            and y2 < len(self.grid[0]):
                        if closed[x2][y2] == 0 and self.grid[x2][y2] == 0:
                            g2 = g + self.cost
                            h2 = self.heuristic[x2][y2]
                            f2 = g2 + h2
                            open.append([f2, g2, h2, x2, y2])
                            closed[x2][y2] = 1
                            action[x2][y2] = i

            count += 1

        # extract the path



        invpath = []
        x = self.goal[0]
        y = self.goal[1]
        invpath.append([x, y])
        while x != self.init[0] or y != self.init[1]:
            x2 = x - delta[action[x][y]][0]
            y2 = y - delta[action[x][y]][1]
            x = x2
            y = y2
            invpath.append([x, y])

        self.path = []
        for i in range(len(invpath)):
            self.path.append(invpath[len(invpath) - 1 - i])




    # ------------------------------------------------
    # 
    # this is the smoothing function
    #

  


    def smooth(self, weight_data = 0.1, weight_smooth = 0.1, 
               tolerance = 0.000001):

        if self.path == []:
            raise ValueError, "Run A* first before smoothing path"

        self.spath = [[0 for row in range(len(self.path[0]))] \
                           for col in range(len(self.path))]
        for i in range(len(self.path)):
            for j in range(len(self.path[0])):
                self.spath[i][j] = self.path[i][j]

        change = tolerance
        while change >= tolerance:
            change = 0.0
            for i in range(1, len(self.path)-1):
                for j in range(len(self.path[0])):
                    aux = self.spath[i][j]
                    
                    self.spath[i][j] += weight_data * \
                        (self.path[i][j] - self.spath[i][j])
                    
                    self.spath[i][j] += weight_smooth * \
                        (self.spath[i-1][j] + self.spath[i+1][j] 
                         - (2.0 * self.spath[i][j]))
                    if i >= 2:
                        self.spath[i][j] += 0.5 * weight_smooth * \
                            (2.0 * self.spath[i-1][j] - self.spath[i-2][j] 
                             - self.spath[i][j])
                    if i <= len(self.path) - 3:
                        self.spath[i][j] += 0.5 * weight_smooth * \
                            (2.0 * self.spath[i+1][j] - self.spath[i+2][j] 
                             - self.spath[i][j])
                
            change += abs(aux - self.spath[i][j])

# ------------------------------------------------
# 
# this is the robot class
#
class robot:
    # --------
    # init: 
    #    creates robot and initializes location/orientation to 0, 0, 0
    #

    def __init__(self, length = 0.5):
        self.x = 0.0
        self.y = 0.0
        self.orientation = 0.0
        self.length = length
        self.steering_noise    = 0.0
        self.distance_noise    = 0.0
        self.measurement_noise = 0.0
        self.num_collisions    = 0
        self.num_steps         = 0

    # --------
    # set: 
    #    sets a robot coordinate
    #
    def set(self, new_x, new_y, new_orientation):
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation) % (2.0 * pi)


    # --------
    # set_noise: 
    #    sets the noise parameters
    #

    def set_noise(self, new_s_noise, new_d_noise, new_m_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.steering_noise     = float(new_s_noise)
        self.distance_noise    = float(new_d_noise)
        self.measurement_noise = float(new_m_noise)

    # --------
    # check: 
    #    checks of the robot pose collides with an obstacle, or
    # is too far outside the plane

    def check_collision(self, grid):
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == 1:
                    dist = sqrt((self.x - float(i)) ** 2 + 
                                (self.y - float(j)) ** 2)
                    if dist < 0.5:
                        self.num_collisions += 1
                        return True
        return False
        
    def check_goal(self, goal, threshold = 1.0):
        dist =  sqrt((float(goal[0]) - self.x) ** 2 + (float(goal[1]) - self.y) ** 2)
        return dist < threshold
        
    # --------
    # move: 
    #    steering = front wheel steering angle, limited by max_steering_angle
    #    distance = total distance driven, most be non-negative

    def move(self, grid, steering, distance, 
             tolerance = 0.001, max_steering_angle = pi / 4.0):

        if steering > max_steering_angle:
            steering = max_steering_angle
        if steering < -max_steering_angle:
            steering = -max_steering_angle
        if distance < 0.0:
            distance = 0.0


        # make a new copy
        res = robot()
        res.length            = self.length
        res.steering_noise    = self.steering_noise
        res.distance_noise    = self.distance_noise
        res.measurement_noise = self.measurement_noise
        res.num_collisions    = self.num_collisions
        res.num_steps         = self.num_steps + 1

        # apply noise
        steering2 = random.gauss(steering, self.steering_noise)
        distance2 = random.gauss(distance, self.distance_noise)


        # Execute motion
        turn = tan(steering2) * distance2 / res.length

        if abs(turn) < tolerance:

            # approximate by straight line motion

            res.x = self.x + (distance2 * cos(self.orientation))
            res.y = self.y + (distance2 * sin(self.orientation))
            res.orientation = (self.orientation + turn) % (2.0 * pi)

        else:

            # approximate bicycle model for motion

            radius = distance2 / turn
            cx = self.x - (sin(self.orientation) * radius)
            cy = self.y + (cos(self.orientation) * radius)
            res.orientation = (self.orientation + turn) % (2.0 * pi)
            res.x = cx + (sin(res.orientation) * radius)
            res.y = cy - (cos(res.orientation) * radius)

        # check for collision
        # res.check_collision(grid)

        return res

    # --------
    # sense: 
    #    

    def sense(self):

        return [random.gauss(self.x, self.measurement_noise),
                random.gauss(self.y, self.measurement_noise)]

    # --------
    # measurement_prob
    #    computes the probability of a measurement
    # 

    def measurement_prob(self, measurement):

        # compute errors
        error_x = measurement[0] - self.x
        error_y = measurement[1] - self.y

        # calculate Gaussian
        error = exp(- (error_x ** 2) / (self.measurement_noise ** 2) / 2.0) \
            / sqrt(2.0 * pi * (self.measurement_noise ** 2))
        error *= exp(- (error_y ** 2) / (self.measurement_noise ** 2) / 2.0) \
            / sqrt(2.0 * pi * (self.measurement_noise ** 2))

        return error



    def __repr__(self):
        # return '[x=%.5f y=%.5f orient=%.5f]'  % (self.x, self.y, self.orientation)
        return '[%.5f, %.5f]'  % (self.x, self.y)






# ------------------------------------------------
# 
# this is the particle filter class
#

class particles:

    # --------
    # init: 
    #    creates particle set with given initial position
    #

    def __init__(self, x, y, theta, 
                 steering_noise, distance_noise, measurement_noise, N = 100):
        self.N = N
        self.steering_noise    = steering_noise
        self.distance_noise    = distance_noise
        self.measurement_noise = measurement_noise
        
        self.data = []
        for i in range(self.N):
            r = robot()
            r.set(x, y, theta)
            r.set_noise(steering_noise, distance_noise, measurement_noise)
            self.data.append(r)


    # --------
    #
    # extract position from a particle set
    # 
    
    def get_position(self):
        x = 0.0
        y = 0.0
        orientation = 0.0

        for i in range(self.N):
            x += self.data[i].x
            y += self.data[i].y
            # orientation is tricky because it is cyclic. By normalizing
            # around the first particle we are somewhat more robust to
            # the 0=2pi problem
            orientation += (((self.data[i].orientation
                              - self.data[0].orientation + pi) % (2.0 * pi)) 
                            + self.data[0].orientation - pi)
        return [x / self.N, y / self.N, orientation / self.N]

    # --------
    #
    # motion of the particles
    # 

    def move(self, grid, steer, speed):
        newdata = []

        for i in range(self.N):
            r = self.data[i].move(grid, steer, speed)
            newdata.append(r)
        self.data = newdata

    # --------
    #
    # sensing and resampling
    # 

    def sense(self, Z):
        w = []
        for i in range(self.N):
            w.append(self.data[i].measurement_prob(Z))

        # resampling (careful, this is using shallow copy)
        p3 = []
        index = int(random.random() * self.N)
        beta = 0.0
        mw = max(w)

        for i in range(self.N):
            beta += random.random() * 2.0 * mw
            while beta > w[index]:
                beta -= w[index]
                index = (index + 1) % self.N
            p3.append(self.data[index])
        self.data = p3

# --------
#
# run:  runs control program for the robot
#


def run(grid, goal, spath, params, printflag = False, speed = 0.1, timeout = 500):
    myrobot = robot()
    myrobot.set(0., 0., 0.)
    myrobot.set_noise(steering_noise, distance_noise, measurement_noise)
    filter = particles(myrobot.x, myrobot.y, myrobot.orientation,
                       steering_noise, distance_noise, measurement_noise)
    real_path = [[myrobot.x, myrobot.y]]
    
    cte  = 0.0
    err  = 0.0
    N    = 0
    
    index = 0 # index into the path
    
    while not myrobot.check_goal(goal) and N < timeout:
        diff_cte = - cte
        
        # ----------------------------------------
        # compute the CTE
        
        # start with the present robot estimate
        x, y, _ = filter.get_position()
        (x1, y1), (x2, y2) = spath[index], spath[index + 1]
        
        dx , dy  = (x2 - x1), (y2 - y1)
        drx, dry = (x  - x1), (y  - y1)
        
        # u is the robot estimate projectes onto the path segment
        u = (drx * dx + dry * dy) / (dx * dx + dy * dy)
        
        # the cte is the estimate projected onto the normal of the path segment
        cte = (dry * dx - drx * dy) / (dx * dx + dy * dy)
        
        # pick the next path segment
        if u > 1.0 and index < len(spath) - 1: index += 1
        # ----------------------------------------
        
        diff_cte += cte
        
        steer = - params[0] * cte - params[1] * diff_cte 
        
        myrobot = myrobot.move(grid, steer, speed)
        real_path.append([myrobot.x, myrobot.y])
        filter.move(grid, steer, speed)
        
        Z = myrobot.sense()
        filter.sense(Z)
        
        collided = myrobot.check_collision(grid)
        
        err += (cte ** 2)
        N += 1
        
        if printflag:
            if collided: print '##### Collision ####'
            print myrobot, cte, index, u

    return myrobot.check_goal(goal), myrobot.num_collisions, real_path

# ------------------------------------------------
# 
# input data and parameters
#


# grid format:
#   0 = navigable space
#   1 = occupied space

grid = [[0, 1, 0, 0, 0, 0],
        [0, 1, 0, 1, 1, 0],
        [0, 1, 0, 1, 0, 0],
        [0, 0, 0, 1, 0, 1],
        [0, 1, 0, 1, 0, 0]]


init = [0, 0]
goal = [len(grid)-1, len(grid[0])-1]

steering_noise    = 0.1
distance_noise    = 0.03
measurement_noise = 0.3

#### ADJUST THESE PARAMETERS ######
weight_data       = 0.1
weight_smooth     = 0.2
p_gain            = 2.0
d_gain            = 6.0
###################################

class Path:
    def __init__(self, grid, init, goal):
        self.grid = grid
        self.init = init
        self.goal = goal
        
        self.plan = plan(grid, init, goal)
        self.plan.astar()
    
    def run(self, weight_data, weight_smooth, p_gain, d_gain):
        self.plan.smooth(weight_data, weight_smooth)
        return run(self.grid, self.goal, self.plan.spath, [p_gain, d_gain])
    
    def error(self, params, K=5):
        # The error is stochastic. Average among K runs
        err = 0
        for _ in range(K):
            success, collisions, real_path = False, None, None
            try:
                print '~',
                success, collisions, real_path = self.run(*params)
            except Exception, e:
                print e
            
            if not success:
                err += 99999
            else:
                err += (collisions * 100 + len(real_path))
        return float(err) / float(K)

path = Path(grid, init, goal)


if __name__ == '__main__':
    success, num_collisions, real_path = path.run(weight_data, weight_smooth, p_gain, d_gain)
    print "Collisions: %d" % num_collisions
    print "Steps     : %d" % len(real_path)
    
    from visualize import GridCanvas
    g = GridCanvas(grid)
    g.show_interest_point(init)
    g.show_interest_point(goal)
    g.show_path(path.plan.path)
    g.show_path(path.plan.spath, "green4")
    g.show_path(real_path, "darkred")
    g.display()

########NEW FILE########
__FILENAME__ = matrix
from math import *

# this is the matrix class
# we use it because it makes it easier to collect constraints in GraphSLAM
# and to calculate solutions (albeit inefficiently)
# implements basic operations of a matrix class
class matrix:

    # ------------
    #
    # initialization - can be called with an initial matrix
    #
    def __init__(self, value = [[]]):
        self.value = value
        self.dimx  = len(value)
        self.dimy  = len(value[0])
        if value == [[]]:
            self.dimx = 0
    
    # -----------
    #
    # defines matrix equality - returns true if corresponding elements
    #   in two matrices are within epsilon of each other.
    #
    def __eq__(self, other):
        epsilon = 0.01
        if self.dimx != other.dimx or self.dimy != other.dimy:
            return False
        for i in range(self.dimx):
            for j in range(self.dimy):
                if abs(self.value[i][j] - other.value[i][j]) > epsilon:
                    return False
        return True
    
    def __ne__(self, other):
        return not (self == other)
    
    # ------------
    #
    # makes matrix of a certain size and sets each element to zero
    #
    def zero(self, dimx, dimy = 0):
        if dimy == 0:
            dimy = dimx
        # check if valid dimensions
        if dimx < 1 or dimy < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx  = dimx
            self.dimy  = dimy
            self.value = [[0.0 for row in range(dimy)] for col in range(dimx)]
    
    # ------------
    #
    # makes matrix of a certain (square) size and turns matrix into identity matrix
    #
    def identity(self, dim):
        # check if valid dimension
        if dim < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx  = dim
            self.dimy  = dim
            self.value = [[0.0 for row in range(dim)] for col in range(dim)]
            for i in range(dim):
                self.value[i][i] = 1.0
    
    # ------------
    #
    # prints out values of matrix
    #
    def show(self, txt = ''):
        for i in range(len(self.value)):
            print txt + '['+ ', '.join('%.3f'%x for x in self.value[i]) + ']' 
        print ' '
    
    # ------------
    #
    # defines elmement-wise matrix addition. Both matrices must be of equal dimensions
    #
    def __add__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimx != other.dimx:
            raise ValueError, "Matrices must be of equal dimension to add"
        else:
            # add if correct dimensions
            res = matrix()
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] + other.value[i][j]
            return res
    
    # ------------
    #
    # defines elmement-wise matrix subtraction. Both matrices must be of equal dimensions
    #
    def __sub__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimx != other.dimx:
            raise ValueError, "Matrices must be of equal dimension to subtract"
        else:
            # subtract if correct dimensions
            res = matrix()
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] - other.value[i][j]
            return res
    
    # ------------
    #
    # defines multiplication. Both matrices must be of fitting dimensions
    #
    def __mul__(self, other):
        # check if correct dimensions
        if self.dimy != other.dimx:
            raise ValueError, "Matrices must be m*n and n*p to multiply"
        else:
            # multiply if correct dimensions
            res = matrix()
            res.zero(self.dimx, other.dimy)
            for i in range(self.dimx):
                for j in range(other.dimy):
                    for k in range(self.dimy):
                        res.value[i][j] += self.value[i][k] * other.value[k][j]
        return res
    
    # ------------
    #
    # returns a matrix transpose
    #
    def transpose(self):
        # compute transpose
        res = matrix()
        res.zero(self.dimy, self.dimx)
        for i in range(self.dimx):
            for j in range(self.dimy):
                res.value[j][i] = self.value[i][j]
        return res
    
    # ------------
    #
    # creates a new matrix from the existing matrix elements.
    #
    # Example:
    #       l = matrix([[ 1,  2,  3,  4,  5], 
    #                   [ 6,  7,  8,  9, 10], 
    #                   [11, 12, 13, 14, 15]])
    #
    #       l.take([0, 2], [0, 2, 3])
    #
    # results in:
    #       
    #       [[1, 3, 4], 
    #        [11, 13, 14]]
    #       
    # 
    # take is used to remove rows and columns from existing matrices
    # list1/list2 define a sequence of rows/columns that shall be taken
    # is no list2 is provided, then list2 is set to list1 (good for symmetric matrices)
    #
    def take(self, list1, list2 = []):
        if list2 == []:
            list2 = list1
        if len(list1) > self.dimx or len(list2) > self.dimy:
            raise ValueError, "list invalid in take()"
        
        res = matrix()
        res.zero(len(list1), len(list2))
        for i in range(len(list1)):
            for j in range(len(list2)):
                res.value[i][j] = self.value[list1[i]][list2[j]]
        return res
    
    # ------------
    #
    # creates a new matrix from the existing matrix elements.
    #
    # Example:
    #       l = matrix([[1, 2, 3],
    #                  [4, 5, 6]])
    #
    #       l.expand(3, 5, [0, 2], [0, 2, 3])
    #
    # results in:
    #
    #       [[1, 0, 2, 3, 0], 
    #        [0, 0, 0, 0, 0], 
    #        [4, 0, 5, 6, 0]]
    # 
    # expand is used to introduce new rows and columns into an existing matrix
    # list1/list2 are the new indexes of row/columns in which the matrix
    # elements are being mapped. Elements for rows and columns 
    # that are not listed in list1/list2 
    # will be initialized by 0.0.
    #
    def expand(self, dimx, dimy, list1, list2 = []):
        if list2 == []:
            list2 = list1
        if len(list1) > self.dimx or len(list2) > self.dimy:
            raise ValueError, "list invalid in expand()"
        
        res = matrix()
        res.zero(dimx, dimy)
        for i in range(len(list1)):
            for j in range(len(list2)):
                res.value[list1[i]][list2[j]] = self.value[i][j]
        return res
    
    # ------------
    #
    # Computes the upper triangular Cholesky factorization of  
    # a positive definite matrix.
    # This code is based on http://adorio-research.org/wordpress/?p=4560
    def Cholesky(self, ztol= 1.0e-5):
        res = matrix()
        res.zero(self.dimx, self.dimx)

        for i in range(self.dimx):
            S = sum([(res.value[k][i])**2 for k in range(i)])
            d = self.value[i][i] - S
            if abs(d) < ztol:
                res.value[i][i] = 0.0
            else: 
                if d < 0.0:
                    raise ValueError, "Matrix not positive-definite"
                res.value[i][i] = sqrt(d)
            for j in range(i+1, self.dimx):
                S = sum([res.value[k][i] * res.value[k][j] for k in range(i)])
                if abs(S) < ztol:
                    S = 0.0
                res.value[i][j] = (self.value[i][j] - S)/res.value[i][i]
        return res 
    
    # ------------
    #
    # Computes inverse of matrix given its Cholesky upper Triangular
    # decomposition of matrix.
    # This code is based on http://adorio-research.org/wordpress/?p=4560
    def CholeskyInverse(self):
    # Computes inverse of matrix given its Cholesky upper Triangular
    # decomposition of matrix.
        # This code is based on http://adorio-research.org/wordpress/?p=4560
        
        res = matrix()
        res.zero(self.dimx, self.dimx)
        
        # Backward step for inverse.
        for j in reversed(range(self.dimx)):
            tjj = self.value[j][j]
            S = sum([self.value[j][k]*res.value[j][k] for k in range(j+1, self.dimx)])
            res.value[j][j] = 1.0/ tjj**2 - S/ tjj
            for i in reversed(range(j)):
                res.value[j][i] = res.value[i][j] = \
                    -sum([self.value[i][k]*res.value[k][j] for k in \
                              range(i+1,self.dimx)])/self.value[i][i]
        return res
    
    # ------------
    #
    # comutes and returns the inverse of a square matrix
    #
    def inverse(self):
        aux = self.Cholesky()
        res = aux.CholeskyInverse()
        return res
    
    # ------------
    #
    # prints matrix (needs work!)
    #
    def __repr__(self):
        return repr(self.value)

########NEW FILE########
__FILENAME__ = omega_xi
# Modify your doit function to incorporate 3
# distance measurements to a landmark(Z0, Z1, Z2).
# You should use the provided expand function to
# allow your Omega and Xi matrices to accomodate
# the new information.
#
# Each landmark measurement should modify 4
# values in your Omega matrix and 2 in your
# Xi vector.
from matrix import matrix

"""
For the following example, you would call doit(-3, 5, 3, 10, 5, 2):
3 robot positions
  initially: -3 (measure landmark to be 10 away)
  moves by 5 (measure landmark to be 5 away)
  moves by 3 (measure landmark to be 2 away)

  

which should return a mu of:
[[-3.0],
 [2.0],
 [5.0],
 [7.0]]
"""
# Including the 5 times multiplier, your returned mu should now be:
#
# [[-3.0],
#  [2.179],
#  [5.714],
#  [6.821]]

def doit(initial_pos, move1, move2, Z0, Z1, Z2):
    # initial_position:
    Omega = matrix([[1.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0]])
    Xi = matrix([[initial_pos],
                 [0.0],
                 [0.0]])
    
    # move1
    Omega += matrix([[1.0, -1.0, 0.0],
                     [-1.0, 1.0, 0.0],
                     [0.0, 0.0, 0.0]])
    Xi += matrix([[-move1],
                  [move1],
                  [0.0]])
    
    # move2
    Omega += matrix([[0.0, 0.0, 0.0],
                     [0.0, 1.0, -1.0],
                     [0.0, -1.0, 1.0]])
    Xi += matrix([[0.0],
                  [-move2],
                  [move2]])
    
    # expand
    Omega = Omega.expand(Omega.dimx + 1, Omega.dimy + 1, range(Omega.dimx))
    Xi = Xi.expand(Xi.dimx + 1, Xi.dimy, range(Xi.dimx), [0])
    
    # first measurement:
    Omega += matrix([[1.0, 0.0, 0.0, -1.0],
                     [0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0],
                     [-1.0, 0.0, 0.0, 1.0]])
    Xi    += matrix([[-Z0],
                     [0.0],
                     [0.0],
                     [Z0]])

    Omega += matrix([[0.0, 0.0, 0.0, 0.0],
                     [0.0, 1.0, 0.0, -1.0],
                     [0.0, 0.0, 0.0, 0.0],
                     [0.0, -1.0, 0.0, 1.0]])
    Xi    += matrix([[0.0],
                     [-Z1],
                     [0.0],
                     [Z1]])
    
    # third measurement:
    Omega += matrix([[0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 5.0, -5.0],
                     [0.0, 0.0, -5.0, 5.0]])
    Xi    += matrix([[0.0],
                     [0.0],
                     [-5*Z2],
                     [5*Z2]])

    Omega.show('Omega: ')
    Xi.show('Xi:    ')
    mu = Omega.inverse() * Xi
    mu.show('Mu:    ')
    
    return mu

doit(-3, 5, 3, 10, 5, 1)


def matrix_fill_in(initial_pos, move_sigma, move1, move2, measure_sigma, Z0, Z1, Z2):
    # initial position:
    Omega = matrix([[1.0, 0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0, 0.0]])
    Xi    = matrix([[initial_pos],
                    [0.0],
                    [0.0],
                    [0.0],
                    [0.0]])

    # move 1:
    Omega += matrix([[1.0/move_sigma, -1.0/move_sigma, 0.0, 0.0, 0.0],
                     [-1.0/move_sigma, 1.0/move_sigma, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0]])
    Xi    += matrix([[-move1/move_sigma],
                     [move1/move_sigma],
                     [0.0],
                     [0.0],
                     [0.0]])
    
    # move 2:
    Omega += matrix([[0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 1.0/move_sigma, -1.0/move_sigma, 0.0, 0.0],
                     [0.0, -1.0/move_sigma, 1.0/move_sigma, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0]])
    Xi    += matrix([[0.0],
                     [-move2/move_sigma],
                     [move2/move_sigma],
                     [0.0],
                     [0.0]])
    
    # measure 0
    Omega += matrix([[1.0/measure_sigma, 0.0, 0.0, -1.0/measure_sigma, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [-1.0/measure_sigma, 0.0, 0.0, 1.0/measure_sigma, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0]])
    
    Xi    += matrix([[-Z0/measure_sigma],
                     [0.0],
                     [0.0],
                     [Z0/measure_sigma],
                     [0.0]])
    
    # measure 1
    Omega += matrix([[0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 1.0/measure_sigma, 0.0, 0.0, -1.0/measure_sigma],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, -1.0/measure_sigma, 0.0, 0.0, 1.0/measure_sigma]])
    Xi    += matrix([[0.0],
                     [-Z1/measure_sigma],
                     [0.0],
                     [0.0],
                     [Z1/measure_sigma]])
    
    # measure 2
    Omega += matrix([[0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 1.0/measure_sigma, 0.0, -1.0/measure_sigma],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, -1.0/measure_sigma, 0.0, 1.0/measure_sigma]])
    Xi    += matrix([[0.0],
                     [0.0],
                     [-Z2/measure_sigma],
                     [0.0],
                     [Z2/measure_sigma]])
    
    Omega.show('Omega: ')
    Xi.show('Xi:    ')
    mu = Omega.inverse() * Xi
    mu.show('Mu:    ')
    
    return mu

initial_pos = 5
move_sigma = 1
move0 = 7
move1 = 2
measure_sigma = 0.5
measure0 = 2
measure1 = 4
measure2 = 2
matrix_fill_in(initial_pos, move_sigma, move0, move1, measure_sigma, measure0, measure1, measure2)
########NEW FILE########
__FILENAME__ = online_slam
# In this problem you will implement a more manageable
# version of graph SLAM in 2 dimensions. 
#
# Define a function, online_slam, that takes 5 inputs:
# data, N, num_landmarks, motion_noise, and
# measurement_noise--just as was done in the last 
# programming assignment of unit 6. This function
# must return TWO matrices, mu and the final Omega.
#
# Just as with the quiz, your matrices should have x
# and y interlaced, so if there were two poses and 2
# landmarks, mu would look like:
#
# mu = matrix([[Px0],
#              [Py0],
#              [Px1],
#              [Py1],
#              [Lx0],
#              [Ly0],
#              [Lx1],
#              [Ly1]])
#
# Enter your code at line 566.

# -----------
# Testing
#
# You have two methods for testing your code.
#
# 1) You can make your own data with the make_data
#    function. Then you can run it through the
#    provided slam routine and check to see that your
#    online_slam function gives the same estimated
#    final robot pose and landmark positions.
# 2) You can use the solution_check function at the
#    bottom of this document to check your code
#    for the two provided test cases. The grading
#    will be almost identical to this function, so
#    if you pass both test cases, you should be
#    marked correct on the homework.
from matrix import matrix
from robot import robot, make_data, print_result, solution_check
from slam import slam

# --------------------------------
#
# online_slam - retains all landmarks but only most recent robot pose
#
def online_slam(data, N, num_landmarks, world_size, motion_noise, measurement_noise):
    # Set the dimension of the filter
    dim = 2 * (1 + num_landmarks)
    
    # make the constraint information matrix and vector
    Omega = matrix()
    Omega.zero(dim, dim)
    Omega.value[0][0] = 1.0
    Omega.value[1][1] = 1.0
    
    Xi = matrix()
    Xi.zero(dim, 1)
    Xi.value[0][0] = world_size / 2.0
    Xi.value[1][0] = world_size / 2.0
    
    # process the data
    for k in range(len(data)):
        measurement = data[k][0]
        motion      = data[k][1]
        
        # integrate the measurements
        for i in range(len(measurement)):
            # m is the index of the landmark coordinate in the matrix/vector
            m = 2 * (1 + measurement[i][0])
            
            # update the information maxtrix/vector based on the measurement
            for b in range(2):
                Omega.value[b][b]     +=  1.0 / measurement_noise
                Omega.value[m+b][m+b] +=  1.0 / measurement_noise
                Omega.value[b][m+b]   += -1.0 / measurement_noise
                Omega.value[m+b][b]   += -1.0 / measurement_noise
                Xi.value[b][0]        += -measurement[i][1+b] / measurement_noise
                Xi.value[m+b][0]      +=  measurement[i][1+b] / measurement_noise
        
        #expand the information matrix and vector ny one new position
        list = [0, 1] + range(4, dim+2)
        Omega = Omega.expand(dim+2, dim+2, list, list)
        Xi    = Xi.expand(dim+2, 1, list, [0])
        
        # update the information maxtrix/vector based on the robot motion
        for b in range(4):
            Omega.value[b][b]     +=  1.0 / motion_noise
        for b in range(2):
            Omega.value[b  ][b+2] += -1.0 / motion_noise
            Omega.value[b+2][b  ] += -1.0 / motion_noise
            Xi.value[b  ][0]      += -motion[b] / motion_noise
            Xi.value[b+2][0]      +=  motion[b] / motion_noise
        
        # now factor out the previous pose
        newlist = range(2, len(Omega.value))
        a = Omega.take([0, 1], newlist)
        b = Omega.take([0, 1])
        c = Xi.take([0, 1], [0])
        
        Omega = Omega.take(newlist)   - a.transpose() * b.inverse() * a
        Xi    = Xi.take(newlist, [0]) - a.transpose() * b.inverse() * c
    
    # compute best estimate
    mu = Omega.inverse() * Xi
    return mu, Omega


# ------------------------------------------------------------------------
#
# Main routine
#
if __name__ == '__main__':
    num_landmarks      = 5        # number of landmarks
    N                  = 20       # time steps
    world_size         = 100.0    # size of world
    measurement_range  = 50.0     # range at which we can sense landmarks
    motion_noise       = 2.0      # noise in robot motion
    measurement_noise  = 2.0      # noise in the measurements
    distance           = 20.0     # distance by which robot (intends to) move each iteratation 
    
    # Run the full slam routine.
    data = make_data(N, num_landmarks, world_size, measurement_range, motion_noise, measurement_noise, distance)
    result = slam(data, N, num_landmarks, world_size, motion_noise, measurement_noise)
    print_result(N, num_landmarks, result)
    
    # Run the online_slam routine.
    data = make_data(N, num_landmarks, world_size, measurement_range, motion_noise, measurement_noise, distance)
    result = online_slam(data, N, num_landmarks, world_size, motion_noise, measurement_noise)
    print_result(1, num_landmarks, result[0])
    
    # -----------
    # Test Case 1
    testdata1          = [[[[1, 21.796713239511305, 25.32184135169971], [2, 15.067410969755826, -27.599928007267906]], [16.4522379034509, -11.372065246394495]],
                          [[[1, 6.1286996178786755, 35.70844618389858], [2, -0.7470113490937167, -17.709326161950294]], [16.4522379034509, -11.372065246394495]],
                          [[[0, 16.305692184072235, -11.72765549112342], [2, -17.49244296888888, -5.371360408288514]], [16.4522379034509, -11.372065246394495]],
                          [[[0, -0.6443452578030207, -2.542378369361001], [2, -32.17857547483552, 6.778675958806988]], [-16.66697847355152, 11.054945886894709]]]
    
    answer_mu1         = matrix([[81.63549976607898],
                                 [27.175270706192254],
                                 [98.09737507003692],
                                 [14.556272940621195],
                                 [71.97926631050574],
                                 [75.07644206765099],
                                 [65.30397603859097],
                                 [22.150809430682695]])
    
    answer_omega1      = matrix([[0.36603773584905663, 0.0, -0.169811320754717, 0.0, -0.011320754716981133, 0.0, -0.1811320754716981, 0.0],
                                 [0.0, 0.36603773584905663, 0.0, -0.169811320754717, 0.0, -0.011320754716981133, 0.0, -0.1811320754716981],
                                 [-0.169811320754717, 0.0, 0.6509433962264151, 0.0, -0.05660377358490567, 0.0, -0.40566037735849064, 0.0],
                                 [0.0, -0.169811320754717, 0.0, 0.6509433962264151, 0.0, -0.05660377358490567, 0.0, -0.40566037735849064],
                                 [-0.011320754716981133, 0.0, -0.05660377358490567, 0.0, 0.6962264150943396, 0.0, -0.360377358490566, 0.0],
                                 [0.0, -0.011320754716981133, 0.0, -0.05660377358490567, 0.0, 0.6962264150943396, 0.0, -0.360377358490566],
                                 [-0.1811320754716981, 0.0, -0.4056603773584906, 0.0, -0.360377358490566, 0.0, 1.2339622641509433, 0.0],
                                 [0.0, -0.1811320754716981, 0.0, -0.4056603773584906, 0.0, -0.360377358490566, 0.0, 1.2339622641509433]])
    
    result = online_slam(testdata1, 5, 3, world_size, 2.0, 2.0)
    solution_check(result, answer_mu1, answer_omega1)
    
    # -----------
    # Test Case 2
    testdata2          = [[[[0, 12.637647070797396, 17.45189715769647], [1, 10.432982633935133, -25.49437383412288]], [17.232472057089492, 10.150955955063045]],
                          [[[0, -4.104607680013634, 11.41471295488775], [1, -2.6421937245699176, -30.500310738397154]], [17.232472057089492, 10.150955955063045]],
                          [[[0, -27.157759429499166, -1.9907376178358271], [1, -23.19841267128686, -43.2248146183254]], [-17.10510363812527, 10.364141523975523]],
                          [[[0, -2.7880265859173763, -16.41914969572965], [1, -3.6771540967943794, -54.29943770172535]], [-17.10510363812527, 10.364141523975523]],
                          [[[0, 10.844236516370763, -27.19190207903398], [1, 14.728670653019343, -63.53743222490458]], [14.192077112147086, -14.09201714598981]]]
    
    answer_mu2         = matrix([[63.37479912250136],
                                 [78.17644539069596],
                                 [61.33207502170053],
                                 [67.10699675357239],
                                 [62.57455560221361],
                                 [27.042758786080363]])
    
    answer_omega2      = matrix([[0.22871751620895048, 0.0, -0.11351536555795691, 0.0, -0.11351536555795691, 0.0],
                                 [0.0, 0.22871751620895048, 0.0, -0.11351536555795691, 0.0, -0.11351536555795691],
                                 [-0.11351536555795691, 0.0, 0.7867205207948973, 0.0, -0.46327947920510265, 0.0],
                                 [0.0, -0.11351536555795691, 0.0, 0.7867205207948973, 0.0, -0.46327947920510265],
                                 [-0.11351536555795691, 0.0, -0.46327947920510265, 0.0, 0.7867205207948973, 0.0],
                                 [0.0, -0.11351536555795691, 0.0, -0.46327947920510265, 0.0, 0.7867205207948973]])
    
    result = online_slam(testdata2, 6, 2, world_size, 3.0, 4.0)
    solution_check(result, answer_mu2, answer_omega2)

########NEW FILE########
__FILENAME__ = robot
import random
from math import *

# ------------------------------------------------
# 
# this is the robot class
# 
# our robot lives in x-y space, and its motion is
# pointed in a random direction. It moves on a straight line
# until is comes close to a wall at which point it turns
# away from the wall and continues to move.
#
# For measurements, it simply senses the x- and y-distance
# to landmarks. This is different from range and bearing as 
# commonly studies in the literature, but this makes it much
# easier to implement the essentials of SLAM without
# cluttered math
class robot:

    # --------
    # init: 
    #   creates robot and initializes location to 0, 0
    #
    def __init__(self, world_size = 100.0, measurement_range = 30.0,
                 motion_noise = 1.0, measurement_noise = 1.0):
        self.measurement_noise = 0.0
        self.world_size = world_size
        self.measurement_range = measurement_range
        self.x = world_size / 2.0
        self.y = world_size / 2.0
        self.motion_noise = motion_noise
        self.measurement_noise = measurement_noise
        self.landmarks = []
        self.num_landmarks = 0
    
    def rand(self):
        return random.random() * 2.0 - 1.0
    
    # --------
    #
    # make random landmarks located in the world
    #
    def make_landmarks(self, num_landmarks):
        self.landmarks = []
        for i in range(num_landmarks):
            self.landmarks.append([round(random.random() * self.world_size),
                                   round(random.random() * self.world_size)])
        self.num_landmarks = num_landmarks
    
    # --------
    #
    # move: attempts to move robot by dx, dy. If outside world
    #       boundary, then the move does nothing and instead returns failure
    #
    def move(self, dx, dy):
        x = self.x + dx + self.rand() * self.motion_noise
        y = self.y + dy + self.rand() * self.motion_noise
        
        if x < 0.0 or x > self.world_size or y < 0.0 or y > self.world_size:
            return False
        else:
            self.x = x
            self.y = y
            return True
    
    # --------
    #
    # sense: returns x- and y- distances to landmarks within visibility range
    #        because not all landmarks may be in this range, the list of measurements
    #        is of variable length. Set measurement_range to -1 if you want all
    #        landmarks to be visible at all times
    #
    def sense(self):
        Z = []
        for i in range(self.num_landmarks):
            dx = self.landmarks[i][0] - self.x + self.rand() * self.measurement_noise
            dy = self.landmarks[i][1] - self.y + self.rand() * self.measurement_noise    
            if self.measurement_range < 0.0 or abs(dx) + abs(dy) <= self.measurement_range:
                Z.append([i, dx, dy])
        return Z

    # --------
    #
    # print robot location
    #
    def __repr__(self):
        return 'Robot: [x=%.5f y=%.5f]'  % (self.x, self.y)


# --------
# this routine makes the robot data
#
def make_data(N, num_landmarks, world_size, measurement_range, motion_noise, 
              measurement_noise, distance):
    complete = False
    
    while not complete:
        data = []
        
        # make robot and landmarks
        r = robot(world_size, measurement_range, motion_noise, measurement_noise)
        r.make_landmarks(num_landmarks)
        seen = [False for row in range(num_landmarks)]
        
        # guess an initial motion
        orientation = random.random() * 2.0 * pi
        dx = cos(orientation) * distance
        dy = sin(orientation) * distance
        
        for k in range(N-1):
            # sense
            Z = r.sense()
            
            # check off all landmarks that were observed 
            for i in range(len(Z)):
                seen[Z[i][0]] = True
            
            # move
            while not r.move(dx, dy):
                # if we'd be leaving the robot world, pick instead a new direction
                orientation = random.random() * 2.0 * pi
                dx = cos(orientation) * distance
                dy = sin(orientation) * distance
            
            # memorize data
            data.append([Z, [dx, dy]])
        
        # we are done when all landmarks were observed; otherwise re-run
        complete = (sum(seen) == num_landmarks)
    
    print ' '
    print 'Landmarks: ', r.landmarks
    print r
    
    return data


# --------------------------------
#
# print the result of SLAM, the robot pose(s) and the landmarks
#
def print_result(N, num_landmarks, result):
    print
    print 'Estimated Pose(s):'
    for i in range(N):
        print '    ['+ ', '.join('%.3f'%x for x in result.value[2*i]) + ', ' \
            + ', '.join('%.3f'%x for x in result.value[2*i+1]) +']'
    print
    print 'Estimated Landmarks:'
    for i in range(num_landmarks):
        print '    ['+ ', '.join('%.3f'%x for x in result.value[2*(N+i)]) + ', ' \
            + ', '.join('%.3f'%x for x in result.value[2*(N+i)+1]) +']'


def check_mu(user_mu, answer_mu):
    if user_mu.dimx != answer_mu.dimx or user_mu.dimy != answer_mu.dimy:
        print "Your mu matrix doesn't have the correct dimensions. Mu should be a", answer_mu.dimx, " x ", answer_mu.dimy, "matrix."
        return False
    else:
        print "Mu has correct dimensions."
    
    if user_mu != answer_mu:
        print "Mu has incorrect entries."
        return False
    else:
        print "Mu correct."
    
    return True


def solution_check(result, answer_mu, answer_omega):
    if len(result) != 2:
        print "Your function must return TWO matrices, mu and Omega"
        return False
    
    user_mu = result[0]
    user_omega = result[1]
    
    if not check_mu(user_mu, answer_mu): return False
    
    if user_mu.dimx == answer_omega.dimx and user_mu.dimy == answer_omega.dimy:
        print "It looks like you returned your results in the wrong order. Make sure to return mu then Omega."
        return False
    
    if user_omega.dimx != answer_omega.dimx or user_omega.dimy != answer_omega.dimy:
        print "Your Omega matrix doesn't have the correct dimensions. Omega should be a", answer_omega.dimx, " x ", answer_omega.dimy, "matrix."
        return False
    else:
        print "Omega has correct dimensions."
    
    if user_omega != answer_omega:
        print "Omega has incorrect entries."
        return False
    else:
        print "Omega correct."
    
    print "Test case passed!"
    return True

########NEW FILE########
__FILENAME__ = slam
# In this problem you will implement SLAM in a 2 dimensional
# world. Please define a function, slam, which takes five
# parameters as input and returns the vector mu. This vector
# should have x, y coordinates interlaced, so for example, 
# if there were 2 poses and 2 landmarks, mu would look like:
#
#  mu =  matrix([[Px0],
#                [Py0],
#                [Px1],
#                [Py1],
#                [Lx0],
#                [Ly0],
#                [Lx1],
#                [Ly1]])
#
# data - This is the data that is generated with the included
#        make_data function. You can also use test_data to
#        make sure your function gives the correct result.
#
# N -    The number of time steps.
#
# num_landmarks - The number of landmarks.
#
# motion_noise - The noise associated with motion. The update
#                strength for motion should be 1.0 / motion_noise.
#
# measurement_noise - The noise associated with measurement.
#                     The update strength for measurement should be
#                     1.0 / measurement_noise.
import random
from math import *

from matrix import matrix
from robot import robot, make_data, print_result, check_mu


# --------------------------------
#
# slam - retains entire path and all landmarks
#
def slam(data, N, num_landmarks, world_size, motion_noise, measurement_noise):
    # Set the dimension of the filter
    dim = 2 * (N + num_landmarks)
    
    # make the constraint information matrix and vector
    Omega = matrix()
    Omega.zero(dim, dim)
    Omega.value[0][0] = 1.0
    Omega.value[1][1] = 1.0
    
    Xi = matrix()
    Xi.zero(dim, 1)
    Xi.value[0][0] = world_size / 2.0
    Xi.value[1][0] = world_size / 2.0
    
    # process the data
    for k in range(len(data)):
        # n is the index of the robot pose in the matrix/vector
        n = k * 2 
        
        measurement = data[k][0]
        motion      = data[k][1]
        
        # integrate the measurements
        for i in range(len(measurement)):
            # m is the index of the landmark coordinate in the matrix/vector
            m = 2 * (N + measurement[i][0])
            
            # update the information maxtrix/vector based on the measurement
            for b in range(2):
                Omega.value[n+b][n+b] +=  1.0 / measurement_noise
                Omega.value[m+b][m+b] +=  1.0 / measurement_noise
                Omega.value[n+b][m+b] += -1.0 / measurement_noise
                Omega.value[m+b][n+b] += -1.0 / measurement_noise
                Xi.value[n+b][0]      += -measurement[i][1+b] / measurement_noise
                Xi.value[m+b][0]      +=  measurement[i][1+b] / measurement_noise
        
        # update the information maxtrix/vector based on the robot motion
        for b in range(4):
            Omega.value[n+b][n+b] +=  1.0 / motion_noise
        for b in range(2):
            Omega.value[n+b  ][n+b+2] += -1.0 / motion_noise
            Omega.value[n+b+2][n+b  ] += -1.0 / motion_noise
            Xi.value[n+b  ][0]        += -motion[b] / motion_noise
            Xi.value[n+b+2][0]        +=  motion[b] / motion_noise
    
    # compute best estimate
    mu = Omega.inverse() * Xi
    return mu

#
# Main routine
#
if __name__ == '__main__':
    num_landmarks      = 5        # number of landmarks
    N                  = 20       # time steps
    world_size         = 100.0    # size of world
    measurement_range  = 50.0     # range at which we can sense landmarks
    motion_noise       = 2.0      # noise in robot motion
    measurement_noise  = 2.0      # noise in the measurements
    distance           = 20.0     # distance by which robot (intends to) move each iteratation 
    
    data = make_data(N, num_landmarks, world_size, measurement_range, motion_noise, measurement_noise, distance)
    result = slam(data, N, num_landmarks, world_size, motion_noise, measurement_noise)
    
    # -------------
    # Testing
    
    ##  Test Case 1
    answer_mu = matrix([
        ##  Estimated Pose(s):
        [49.998897453299165], [49.998505706587814],
        [37.9714477943764  ], [33.64993445823509 ],
        [26.183449863995392], [18.153338459791925],
        [13.743443839776688], [2.1141193319706257],
        [28.095060682659934], [16.78089653056425 ],
        [42.382654337758865], [30.899617637854934],
        [55.82918373374959 ], [44.494287384838586],
        [70.85548928962663 ], [59.69712516287841 ],
        [85.6953531635832  ], [75.54007207500423 ],
        [74.00974406829611 ], [92.43147558585063 ],
        [53.54264788322474 ], [96.45111370814985 ],
        [34.52341231228876 ], [100.07762713840204],
        [48.621309970082486], [83.95097871134821 ],
        [60.19521941022714 ], [68.1050904555393  ],
        [73.77592978594885 ], [52.932451315943574],
        [87.12997140410576 ], [38.53576961176431 ],
        [80.3007799395094  ], [20.505859780712917],
        [72.79656231764604 ], [2.942675607797428 ],
        [55.243590482706026], [13.253021809459227],
        [37.41439688492312 ], [22.31502245240636 ],
        
        ##  Estimated Landmarks:
        [82.95425645256424 ], [13.536536707427121],
        [70.49306062345174 ], [74.13913606764582 ],
        [36.73812342335858 ], [61.2789905549488  ],
        [18.696326102039485], [66.05733561281015 ],
        [20.632945056999347], [16.87255837889543]
    ])
    test_data1 = [[[[1, 19.457599255548065, 23.8387362100849], [2, -13.195807561967236, 11.708840328458608], [3, -30.0954905279171, 15.387879242505843]], [-12.2607279422326, -15.801093326936487]], [[[2, -0.4659930049620491, 28.088559771215664], [4, -17.866382374890936, -16.384904503932]], [-12.2607279422326, -15.801093326936487]], [[[4, -6.202512900833806, -1.823403210274639]], [-12.2607279422326, -15.801093326936487]], [[[4, 7.412136480918645, 15.388585962142429]], [14.008259661173426, 14.274756084260822]], [[[4, -7.526138813444998, -0.4563942429717849]], [14.008259661173426, 14.274756084260822]], [[[2, -6.299793150150058, 29.047830407717623], [4, -21.93551130411791, -13.21956810989039]], [14.008259661173426, 14.274756084260822]], [[[1, 15.796300959032276, 30.65769689694247], [2, -18.64370821983482, 17.380022987031367]], [14.008259661173426, 14.274756084260822]], [[[1, 0.40311325410337906, 14.169429532679855], [2, -35.069349468466235, 2.4945558982439957]], [14.008259661173426, 14.274756084260822]], [[[1, -16.71340983241936, -2.777000269543834]], [-11.006096015782283, 16.699276945166858]], [[[1, -3.611096830835776, -17.954019226763958]], [-19.693482634035977, 3.488085684573048]], [[[1, 18.398273354362416, -22.705102332550947]], [-19.693482634035977, 3.488085684573048]], [[[2, 2.789312482883833, -39.73720193121324]], [12.849049222879723, -15.326510824972983]], [[[1, 21.26897046581808, -10.121029799040915], [2, -11.917698965880655, -23.17711662602097], [3, -31.81167947898398, -16.7985673023331]], [12.849049222879723, -15.326510824972983]], [[[1, 10.48157743234859, 5.692957082575485], [2, -22.31488473554935, -5.389184118551409], [3, -40.81803984305378, -2.4703329790238118]], [12.849049222879723, -15.326510824972983]], [[[0, 10.591050242096598, -39.2051798967113], [1, -3.5675572049297553, 22.849456408289125], [2, -38.39251065320351, 7.288990306029511]], [12.849049222879723, -15.326510824972983]], [[[0, -3.6225556479370766, -25.58006865235512]], [-7.8874682868419965, -18.379005523261092]], [[[0, 1.9784503557879374, -6.5025974151499]], [-7.8874682868419965, -18.379005523261092]], [[[0, 10.050665232782423, 11.026385307998742]], [-17.82919359778298, 9.062000642947142]], [[[0, 26.526838150174818, -0.22563393232425621], [4, -33.70303936886652, 2.880339841013677]], [-17.82919359778298, 9.062000642947142]]]
    result = slam(test_data1, 20, 5, world_size, 2.0, 2.0)
    print_result(20, 5, result)
    check_mu(result, answer_mu)
    
    ##  Test Case 2
    answer_mu = matrix([
        ##  Estimated Pose(s):
        [49.999477332348086], [49.99890156551778 ],
        [69.18030735650325 ], [45.66363344648087 ],
        [87.7418064828167  ], [39.7015808043011  ],
        [76.2689002984748  ], [56.308708837988604],
        [64.31595832940498 ], [72.17416433180664 ],
        [52.25593780877982 ], [88.15129488583568 ],
        [44.05788183012242 ], [69.39888197470297 ],
        [37.00060088117602 ], [49.91574097036883 ],
        [30.923168865968172], [30.953132613521404],
        [23.507016577616362], [11.417418859810084],
        [34.17904823546437 ], [27.13111103387763 ],
        [44.153991513067325], [43.8439571694372  ],
        [54.80488988167458 ], [60.918509500376814],
        [65.69693171880341 ], [78.54360707650197 ],
        [77.4671073715615  ], [95.62410423059377 ],
        [96.80062212965419 ], [98.8189438054247  ],
        [75.95566185322726 ], [99.96919845616313 ],
        [70.19856001872532 ], [81.17887019996131 ],
        [64.05274158851972 ], [61.72101680774857 ],
        [58.10609891363755 ], [42.62553459605071 ],
        
        ##  Estimated Landmarks:
        [76.7777215386166  ], [42.88538378284734 ],
        [85.06362510793153 ], [77.43622580258783 ],
        [13.546262775052924], [95.64892318002514 ],
        [59.447682292240444], [39.59345703309377 ],
        [69.26225738002688 ], [94.23786125406279 ]
    ])
    test_data2 = [[[[0, 26.543274387283322, -6.262538160312672], [3, 9.937396825799755, -9.128540360867689]], [18.92765331253674, -6.460955043986683]], [[[0, 7.706544739722961, -3.758467215445748], [1, 17.03954411948937, 31.705489938553438], [3, -11.61731288777497, -6.64964096716416]], [18.92765331253674, -6.460955043986683]], [[[0, -12.35130507136378, 2.585119104239249], [1, -2.563534536165313, 38.22159657838369], [3, -26.961236804740935, -0.4802312626141525]], [-11.167066095509824, 16.592065417497455]], [[[0, 1.4138633151721272, -13.912454837810632], [1, 8.087721200818589, 20.51845934354381], [3, -17.091723454402302, -16.521500551709707], [4, -7.414211721400232, 38.09191602674439]], [-11.167066095509824, 16.592065417497455]], [[[0, 12.886743222179561, -28.703968411636318], [1, 21.660953298391387, 3.4912891084614914], [3, -6.401401414569506, -32.321583037341625], [4, 5.034079343639034, 23.102207946092893]], [-11.167066095509824, 16.592065417497455]], [[[1, 31.126317672358578, -10.036784369535214], [2, -38.70878528420893, 7.4987265861424595], [4, 17.977218575473767, 6.150889254289742]], [-6.595520680493778, -18.88118393939265]], [[[1, 41.82460922922086, 7.847527392202475], [3, 15.711709540417502, -30.34633659912818]], [-6.595520680493778, -18.88118393939265]], [[[0, 40.18454208294434, -6.710999804403755], [3, 23.019508919299156, -10.12110867290604]], [-6.595520680493778, -18.88118393939265]], [[[3, 27.18579315312821, 8.067219022708391]], [-6.595520680493778, -18.88118393939265]], [[], [11.492663265706092, 16.36822198838621]], [[[3, 24.57154567653098, 13.461499960708197]], [11.492663265706092, 16.36822198838621]], [[[0, 31.61945290413707, 0.4272295085799329], [3, 16.97392299158991, -5.274596836133088]], [11.492663265706092, 16.36822198838621]], [[[0, 22.407381798735177, -18.03500068379259], [1, 29.642444125196995, 17.3794951934614], [3, 4.7969752441371645, -21.07505361639969], [4, 14.726069092569372, 32.75999422300078]], [11.492663265706092, 16.36822198838621]], [[[0, 10.705527984670137, -34.589764174299596], [1, 18.58772336795603, -0.20109708164787765], [3, -4.839806195049413, -39.92208742305105], [4, 4.18824810165454, 14.146847823548889]], [11.492663265706092, 16.36822198838621]], [[[1, 5.878492140223764, -19.955352450942357], [4, -7.059505455306587, -0.9740849280550585]], [19.628527845173146, 3.83678180657467]], [[[1, -11.150789592446378, -22.736641053247872], [4, -28.832815721158255, -3.9462962046291388]], [-19.841703647091965, 2.5113335861604362]], [[[1, 8.64427397916182, -20.286336970889053], [4, -5.036917727942285, -6.311739993868336]], [-5.946642674882207, -19.09548221169787]], [[[0, 7.151866679283043, -39.56103232616369], [1, 16.01535401373368, -3.780995345194027], [4, -3.04801331832137, 13.697362774960865]], [-5.946642674882207, -19.09548221169787]], [[[0, 12.872879480504395, -19.707592098123207], [1, 22.236710716903136, 16.331770792606406], [3, -4.841206109583004, -21.24604435851242], [4, 4.27111163223552, 32.25309748614184]], [-5.946642674882207, -19.09548221169787]]]
    result = slam(test_data2, 20, 5, world_size, 2.0, 2.0)
    print_result(20, 5, result)
    check_mu(result, answer_mu)

########NEW FILE########
__FILENAME__ = twiddle
from copy import deepcopy
from cte import path, weight_data, weight_smooth, p_gain, d_gain


def twiddle(init_params, error_func, tol=0.01):
    n_params = len(init_params)
    p  = deepcopy(init_params)
    dp = [1.0] * n_params
    
    best_error = float("inf")
    n = 0
    while sum(dp) >= tol:
        for i in range(n_params):
            print '.',
            p[i] += dp[i]
            err = error_func(p)
            if err < best_error:
                best_error = err
                dp[i] *= 1.1
            else:
                p[i] -= 2.0 * dp[i]
                err = error_func(p)
                if err < best_error:
                    best_error = err
                    dp[i] * 1.1
                else:
                    p[i] += dp[i]
                    dp[i] *= 0.9
        n += 1
        print "\nTwiddle #", n, p, ' -> ', best_error, '(%.4f >= %.4f)' % (sum(dp), tol)
    return p


print twiddle([weight_data, weight_smooth, p_gain, d_gain], path.error)

########NEW FILE########
__FILENAME__ = visualize
from Tkinter import *


class GridCanvas:
    UNIT = 50
    
    def __init__(self, grid):
        master = Tk()
        w, h = (len(grid[0])+1)*GridCanvas.UNIT, (len(grid)+1)*GridCanvas.UNIT
        self.c = Canvas(master, width=w, height=h)
        self.c.pack()
        
        for x in range(len(grid)):
            for y in range(len(grid[0])):
                if grid[x][y] == 1:
                    self.circle(x, y, 0.5)
    
    def show_interest_point(self, point):
        self.circle(point[0], point[1], 0.1, "blue")
    
    def show_path(self, path, color="blue"):
        for i in range(len(path)-1):
            x1, y1 = path[i]
            x2, y2 = path[i+1]
            self.line(x1, y1, x2, y2, color)
    
    def map(self, x, y):
        return (y+1)*GridCanvas.UNIT, (x+1)*GridCanvas.UNIT
    
    def line(self, x1, y1, x2, y2, color):
        x1, y1 = self.map(x1, y1)
        x2, y2 = self.map(x2, y2)
        self.c.create_line(x1, y1, x2, y2, fill=color)
    
    def circle(self, x, y, r, color="red"):
        x, y = self.map(x, y)
        r = r * GridCanvas.UNIT
        x0, y0 = x-r, y-r
        x1, y1 = x+r, y+r
        self.c.create_oval(x0, y0, x1, y1, fill=color)
    
    def display(self):
        mainloop()

########NEW FILE########
