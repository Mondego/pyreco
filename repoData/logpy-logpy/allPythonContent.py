__FILENAME__ = account
class Account(object):
    def __init__(self, first, last, id, balance):
        self.first = first
        self.last = last
        self.id = id
        self.balance = balance

    def info(self):
        return (self.first, self.last, self.id, self.balance)

    def __eq__(self, other):
        return self.info() == other.info()

    def __hash__(self):
        return hash((type(self), self.info()))

    def __str__(self):
        return "Account: %s %s, id %d, balance %d" % self.info()

    __repr__ = __str__

########NEW FILE########
__FILENAME__ = commutative
from logpy import run, var, fact
from logpy.assoccomm import eq_assoccomm as eq
from logpy.assoccomm import commutative, associative

# Define some dummy Operationss
add = 'add'
mul = 'mul'
# Declare that these ops are commutative using the facts system
fact(commutative, mul)
fact(commutative, add)
fact(associative, mul)
fact(associative, add)

# Define some wild variables
x, y = var('x'), var('y')

# Two expressions to match
pattern = (mul, (add, 1, x), y)                # (1 + x) * y
expr    = (mul, 2, (add, 3, 1))                # 2 * (3 + 1)
print run(0, (x,y), eq(pattern, expr))         # prints ((3, 2),) meaning
                                               #   x matches to 3
                                               #   y matches to 2

########NEW FILE########
__FILENAME__ = corleone
# Family relationships from The Godfather
# Translated from the core.logic example found in
# "The Magical Island of Kanren - core.logic Intro Part 1"
# http://objectcommando.com/blog/2011/11/04/the-magical-island-of-kanren-core-logic-intro-part-1/

from logpy import Relation, facts, run, conde, var, eq

father = Relation()
mother = Relation()

facts(father, ('Vito', 'Michael'),
              ('Vito', 'Sonny'),
              ('Vito', 'Fredo'),
              ('Michael', 'Anthony'),
              ('Michael', 'Mary'),
              ('Sonny', 'Vicent'),
              ('Sonny', 'Francesca'),
              ('Sonny', 'Kathryn'),
              ('Sonny', 'Frank'),
              ('Sonny', 'Santino'))

facts(mother, ('Carmela', 'Michael'),
              ('Carmela', 'Sonny'),
              ('Carmela', 'Fredo'),
              ('Kay', 'Mary'),
              ('Kay', 'Anthony'),
              ('Sandra', 'Francesca'),
              ('Sandra', 'Kathryn'),
              ('Sandra', 'Frank'),
              ('Sandra', 'Santino'))

q = var()

print run(0, q, father('Vito', q))          # Vito is the father of who?
# ('Sonny', 'Michael', 'Fredo')


print run(0, q, father(q, 'Michael'))       # Who is the father of Michael?
# ('Vito',)

def parent(p, child):
    return conde([father(p, child)], [mother(p, child)])


print run(0, q, parent(q, 'Michael'))       # Who is a parent of Michael?
# ('Vito', 'Carmela')

def grandparent(gparent, child):
    p = var()
    return conde((parent(gparent, p), parent(p, child)))


print run(0, q, grandparent(q, 'Anthony'))  # Who is a grandparent of Anthony?
# ('Vito', 'Carmela')


print run(0, q, grandparent('Vito', q))     # Vito is a grandparent of whom?
# ('Vicent', 'Anthony', 'Kathryn', 'Mary', 'Frank', 'Santino', 'Francesca')

def sibling(a, b):
    p = var()
    return conde((parent(p, a), parent(p, b)))

# All spouses
x, y, z = var(), var(), var()
print run(0, (x, y), (father, x, z), (mother, y, z))
# (('Vito', 'Carmela'), ('Sonny', 'Sandra'), ('Michael', 'Kay'))

########NEW FILE########
__FILENAME__ = prime
""" Example using SymPy to construct a prime number goal """

from logpy.core import (isvar, success, fail, assoc, goaleval, var, run,
        membero, condeseq, eq)
from sympy.ntheory.generate import prime, isprime
import itertools as it

def primo(x):
    """ x is a prime number """
    if isvar(x):
        return condeseq([(eq, x, p)] for p in it.imap(prime, it.count(1)))
    else:
        return success if isprime(x) else fail

x = var()
print set(run(0, x, (membero, x, (20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30)),
                    (primo, x)))
# set([29, 33])

print run(5, x, primo(x))
# (2, 3, 5, 7, 11)

########NEW FILE########
__FILENAME__ = states
"""
An example showing how to use facts and relations to store data and query data

This example builds a small database of the US states.

The `adjacency` relation expresses which states border each other
The `coastal` relation expresses which states border the ocean
"""
from logpy import run, fact, eq, Relation, var

adjacent = Relation()
coastal  = Relation()


coastal_states = 'WA,OR,CA,TX,LA,MS,AL,GA,FL,SC,NC,VA,MD,DE,NJ,NY,CT,RI,MA,ME,NH,AK,HI'.split(',')

for state in coastal_states:        # ['NY', 'NJ', 'CT', ...]
    fact(coastal, state)            # e.g. 'NY' is coastal

with open('examples/data/adjacent-states.txt') as f: # lines like 'CA,OR,NV,AZ'
    adjlist = [line.strip().split(',') for line in f
                                       if line and line[0].isalpha()]

for L in adjlist:                   # ['CA', 'OR', 'NV', 'AZ']
    head, tail = L[0], L[1:]        # 'CA', ['OR', 'NV', 'AZ']
    for state in tail:
        fact(adjacent, head, state) # e.g. 'CA' is adjacent to 'OR',
                                    #      'CA' is adjacent to 'NV', etc...

x = var()
y = var()

print run(0, x, adjacent('CA', 'NY')) # is California adjacent to New York?
# ()

print run(0, x, adjacent('CA', x))    # all states next to California
# ('OR', 'NV', 'AZ')

print run(0, x, adjacent('TX', x),    # all coastal states next to Texas
                coastal(x))
# ('LA',)

print run(5, x, coastal(y),           # five states that border a coastal state
                adjacent(x, y))
# ('VT', 'AL', 'WV', 'DE', 'MA')

print run(0, x, adjacent('TN', x),    # all states adjacent to Tennessee
                adjacent('FL', x))    #        and adjacent to Florida
# ('GA', 'AL')

########NEW FILE########
__FILENAME__ = user-classes
from account import Account
from logpy import unifiable, run, var, eq, membero, variables
from logpy.core import lall
from logpy.arith import add, gt, sub

unifiable(Account)  # Register Account class

accounts = (Account('Adam', 'Smith', 1, 20),
            Account('Carl', 'Marx', 2, 3),
            Account('John', 'Rockefeller', 3, 1000))

# variables are arbitrary Python objects, not LogPy Var objects
first = 'FIRST'
last = 'LAST'
ident = -1111
balance = -2222
newbalance = -3333
vars = {first, last, ident, balance, newbalance}


# Describe a couple of transformations on accounts
source = Account(first, last, ident, balance)
target = Account(first, last, ident, newbalance)

theorists = ('Adam', 'Carl')
# Give $10 to theorists
theorist_bonus = lall((membero, source, accounts),
                      (membero, first, theorists),
                      (add, 10, balance, newbalance))

# Take $10 from anyone with more than $100
tax_the_rich = lall((membero, source, accounts),
                    (gt, balance, 100),
                    (sub, balance, 10, newbalance))

with variables(*vars):
    print run(0, target, tax_the_rich)
    print run(0, target, theorist_bonus)

########NEW FILE########
__FILENAME__ = arith
from logpy.core import (isvar, var, run, membero, eq, EarlyGoalError, lany)

def gt(x, y):
    """ x > y """
    if not isvar(x) and not isvar(y):
        return eq(x > y, True)
    else:
        raise EarlyGoalError()

def lt(x, y):
    """ x > y """
    if not isvar(x) and not isvar(y):
        return eq(x < y, True)
    else:
        raise EarlyGoalError()

def lor(*goalconsts):
    """ Logical or for goal constructors

    >>> from logpy.arith import lor, eq, gt
    >>> gte = lor(eq, gt)  # greater than or equal to is `eq or gt`
    """
    def goal(*args):
        return lany(*[gc(*args) for gc in goalconsts])
    return goal

gte = lor(gt, eq)
lte = lor(lt, eq)

import operator

def binop(op, revop=None):
    """ Transform binary operator into goal

    >>> from logpy.arith import binop
    >>> import operator
    >>> add = binop(operator.add, operator.sub)

    >>> from logpy import var, run
    >>> x = var('x')
    >>> next(add(1, 2, x)({}))
    {~x: 3}
    """

    def goal(x, y, z):
        if not isvar(x) and not isvar(y):
            return eq(op(x, y), z)
        if not isvar(y) and not isvar(z) and revop:
            return eq(x, revop(z, y))
        if not isvar(x) and not isvar(z) and revop:
            return eq(y, revop(z, x))
        raise EarlyGoalError()
    goal.__name__ = op.__name__
    return goal

add = binop(operator.add, operator.sub)
add.__doc__ = """ x + y == z """
mul = binop(operator.mul, operator.truediv)
mul.__doc__ = """ x * y == z """
mod = binop(operator.mod)
mod.__doc__ = """ x % y == z """

def sub(x, y, z):
    """ x - y == z """
    return add(y, z, x)

def div(x, y, z):
    """ x / y == z """
    return mul(z, y, x)

########NEW FILE########
__FILENAME__ = assoccomm
""" Associative and Commutative unification

This module provides goals for associative and commutative unification.  It
accomplishes this through naively trying all possibilities.  This was built to
be used in the computer algebra systems SymPy and Theano.

>>> from logpy import run, var, fact
>>> from logpy.assoccomm import eq_assoccomm as eq
>>> from logpy.assoccomm import commutative, associative

>>> # Define some dummy Ops
>>> add = 'add'
>>> mul = 'mul'

>>> # Declare that these ops are commutative using the facts system
>>> fact(commutative, mul)
>>> fact(commutative, add)
>>> fact(associative, mul)
>>> fact(associative, add)

>>> # Define some wild variables
>>> x, y = var('x'), var('y')

>>> # Two expressions to match
>>> pattern = (mul, (add, 1, x), y)                # (1 + x) * y
>>> expr    = (mul, 2, (add, 3, 1))                # 2 * (3 + 1)

>>> print(run(0, (x,y), eq(pattern, expr)))
((3, 2),)
"""

from logpy.core import (isvar, assoc, unify,
        conde, var, eq, fail, goaleval, lall, EarlyGoalError,
        condeseq, goaleval)
from .goals import heado, permuteq, conso, tailo
from .facts import Relation
from logpy import core
from .util import groupsizes, index
from .util import transitive_get as walk
from .term import term, arguments, operator


associative = Relation('associative')
commutative = Relation('commutative')

def assocunify(u, v, s, eq=core.eq, n=None):
    """ Associative Unification

    See Also:
        eq_assoccomm
    """
    uop, uargs = op_args(u)
    vop, vargs = op_args(v)

    if not uop and not vop:
        res = unify(u, v, s)
        if res is not False:
            return (res,)  # TODO: iterate through all possibilities

    if uop and vop:
        s = unify(uop, vop, s)
        if s is False:
            raise StopIteration()
        op = walk(uop, s)

        sm, lg = (uargs, vargs) if len(uargs) <= len(vargs) else (vargs, uargs)
        ops = assocsized(op, lg, len(sm))
        goal = condeseq([(eq, a, b) for a, b, in zip(sm, lg2)] for lg2 in ops)
        return goaleval(goal)(s)

    if uop:
        op, tail = uop, uargs
        b = v
    if vop:
        op, tail = vop, vargs
        b = u

    ns = [n] if n else range(2, len(tail)+1)
    knowns = (build(op, x) for n in ns for x in assocsized(op, tail, n))

    goal = condeseq([(core.eq, b, k)] for k in knowns)
    return goaleval(goal)(s)

def assocsized(op, tail, n):
    """ All associative combinations of x in n groups """
    gsizess = groupsizes(len(tail), n)
    partitions = (groupsizes_to_partition(*gsizes) for gsizes in gsizess)
    return (makeops(op, partition(tail, part)) for part in partitions)

def makeops(op, lists):
    """ Construct operations from an op and parition lists

    >>> from logpy.assoccomm import makeops
    >>> makeops('add', [(1, 2), (3, 4, 5)])
    (('add', 1, 2), ('add', 3, 4, 5))
    """
    return tuple(l[0] if len(l) == 1 else build(op, l) for l in lists)

def partition(tup, part):
    """ Partition a tuple

    >>> from logpy.assoccomm import partition
    >>> partition("abcde", [[0,1], [4,3,2]])
    [('a', 'b'), ('e', 'd', 'c')]
    """
    return [index(tup, ind) for ind in part]

def groupsizes_to_partition(*gsizes):
    """
    >>> from logpy.assoccomm import groupsizes_to_partition
    >>> groupsizes_to_partition(2, 3)
    [[0, 1], [2, 3, 4]]
    """
    idx = 0
    part = []
    for gs in gsizes:
        l = []
        for i in range(gs):
            l.append(idx)
            idx += 1
        part.append(l)
    return part

def eq_assoc(u, v, eq=core.eq, n=None):
    """ Goal for associative equality

    >>> from logpy import run, var, fact
    >>> from logpy.assoccomm import eq_assoc as eq

    >>> fact(commutative, 'add')    # declare that 'add' is commutative
    >>> fact(associative, 'add')    # declare that 'add' is associative

    >>> x = var()
    >>> run(0, x, eq(('add', 1, 2, 3), ('add', 1, x)))
    (('add', 2, 3),)
    """
    uop, uargs = op_args(u)
    vop, vargs = op_args(v)
    if uop and vop:
        return conde([(core.eq, u, v)],
                     [(eq, uop, vop), (associative, uop),
                      lambda s: assocunify(u, v, s, eq, n)])

    if uop or vop:
        if vop:
            uop, vop = vop, uop
            uargs, vargs = vargs, uargs
            v, u = u, v
        return conde([(core.eq, u, v)],
                     [(associative, uop),
                      lambda s: assocunify(u, v, s, eq, n)])

    return (core.eq, u, v)


def eq_comm(u, v, eq=None):
    """ Goal for commutative equality

    >>> from logpy import run, var, fact
    >>> from logpy.assoccomm import eq_comm as eq
    >>> from logpy.assoccomm import commutative, associative

    >>> fact(commutative, 'add')    # declare that 'add' is commutative
    >>> fact(associative, 'add')    # declare that 'add' is associative

    >>> x = var()
    >>> run(0, x, eq(('add', 1, 2, 3), ('add', 2, x, 1)))
    (3,)
    """
    eq = eq or eq_comm
    op = var()
    utail = var()
    vtail = var()
    if isvar(u) and isvar(v):
        return (core.eq, u, v)
        raise EarlyGoalError()
    uop, uargs = op_args(u)
    vop, vargs = op_args(v)
    if not uop and not vop:
        return (core.eq, u, v)
    if vop and not uop:
        uop, uargs = vop, vargs
        v, u = u, v
    return (conde, ((core.eq, u, v),),
                   ((commutative, uop),
                    (buildo, uop, vtail, v),
                    (permuteq, uargs, vtail, eq)))

def build_tuple(op, args):
    try:
        return term(op, args)
    except TypeError:
        raise EarlyGoalError()


def buildo(op, args, obj):
    """ obj is composed of op on args

    Example: in add(1,2,3) ``add`` is the op and (1,2,3) are the args

    Checks op_regsitry for functions to define op/arg relationships
    """
    if not isvar(obj):
        oop, oargs = op_args(obj)
        return lall((eq, op, oop), (eq, args, oargs))
    else:
        try:
            return eq(obj, build(op, args))
        except TypeError:
            raise EarlyGoalError()
    raise EarlyGoalError()

def build(op, args):
    try:
        return term(op, args)
    except NotImplementedError:
        raise EarlyGoalError()


def op_args(x):
    """ Break apart x into an operation and tuple of args """
    if isvar(x):
        return None, None
    try:
        return operator(x), arguments(x)
    except NotImplementedError:
        return None, None

def eq_assoccomm(u, v):
    """ Associative/Commutative eq

    Works like logic.core.eq but supports associative/commutative expr trees

    tree-format:  (op, *args)
    example:      (add, 1, 2, 3)

    State that operations are associative or commutative with relations

    >>> from logpy.assoccomm import eq_assoccomm as eq
    >>> from logpy.assoccomm import commutative, associative
    >>> from logpy import fact, run, var

    >>> fact(commutative, 'add')    # declare that 'add' is commutative
    >>> fact(associative, 'add')    # declare that 'add' is associative

    >>> x = var()
    >>> e1 = ('add', 1, 2, 3)
    >>> e2 = ('add', 1, x)
    >>> run(0, x, eq(e1, e2))
    (('add', 2, 3), ('add', 3, 2))
    """
    try:
        uop, uargs = op_args(u)
        vop, vargs = op_args(v)
    except ValueError:
        return (eq, u, v)

    if uop and not vop and not isvar(v):
        return fail
    if vop and not uop and not isvar(u):
        return fail
    if uop and vop and not uop == vop:
        return fail
    if uop and not (uop,) in associative.facts:
        return (eq, u, v)
    if vop and not (vop,) in associative.facts:
        return (eq, u, v)

    if uop and vop:
        u, v = (u, v) if len(uargs) >= len(vargs) else (v, u)
        n = min(map(len, (uargs, vargs)))  # length of shorter tail
    else:
        n = None
    if vop and not uop:
        u, v = v, u
    w = var()
    return (lall, (eq_assoc, u, w, eq_assoccomm, n),
                  (eq_comm, v, w, eq_assoccomm))

########NEW FILE########
__FILENAME__ = core
import itertools as it
from functools import partial
from .util import transitive_get as walk
from .util import deep_transitive_get as walkstar
from .util import (dicthash, interleave, take, evalt, index, multihash, unique)
from toolz import assoc, groupby

from .variable import var, isvar
from .unification import reify, unify


#########
# Goals #
#########

def fail(s):
    return ()
def success(s):
    return (s,)

def eq(u, v):
    """ Goal such that u == v

    See also:
        unify
    """
    def goal_eq(s):
        result = unify(u, v, s)
        if result is not False:
            yield result
    return goal_eq

def membero(x, coll):
    """ Goal such that x is an item of coll """
    if not isvar(x) and not isvar(coll):
        if x in coll:
            return success
        return (lany,) + tuple((eq, x, item) for item in coll)
    if isvar(x) and not isvar(coll):
        return (lany,) + tuple((eq, x, item) for item in coll)
    raise EarlyGoalError()

################################
# Logical combination of goals #
################################

def lall(*goals):
    """ Logical all

    >>> from logpy.core import lall, membero
    >>> x = var('x')
    >>> g = lall(membero(x, (1,2,3)), membero(x, (2,3,4)))
    >>> tuple(g({}))
    ({~x: 2}, {~x: 3})
    """
    if not goals:
        return success
    if len(goals) == 1:
        return goals[0]
    def allgoal(s):
        g = goaleval(reify(goals[0], s))
        return unique(interleave(
                        goaleval(reify((lall,) + tuple(goals[1:]), ss))(ss)
                        for ss in g(s)),
                      key=dicthash)
    return allgoal

def lallfirst(*goals):
    """ Logical all - Run goals one at a time

    >>> from logpy.core import lall, membero
    >>> x = var('x')
    >>> g = lall(membero(x, (1,2,3)), membero(x, (2,3,4)))
    >>> tuple(g({}))
    ({~x: 2}, {~x: 3})
    """
    if not goals:
        return success
    if len(goals) == 1:
        return goals[0]
    def allgoal(s):
        for i, g in enumerate(goals):
            try:
                goal = goaleval(reify(g, s))
            except EarlyGoalError:
                continue
            other_goals = tuple(goals[:i] + goals[i+1:])
            return unique(interleave(goaleval(
                reify((lallfirst,) + other_goals, ss))(ss)
                for ss in goal(s)), key=dicthash)
        else:
            raise EarlyGoalError()
    return allgoal

def lany(*goals):
    """ Logical any

    >>> from logpy.core import lany, membero
    >>> x = var('x')
    >>> g = lany(membero(x, (1,2,3)), membero(x, (2,3,4)))
    >>> tuple(g({}))
    ({~x: 1}, {~x: 2}, {~x: 3}, {~x: 4})
    """
    if len(goals) == 1:
        return goals[0]
    return lanyseq(goals)

def lallearly(*goals):
    """ Logical all with goal reordering to avoid EarlyGoalErrors

    See also:
        EarlyGoalError
        earlyorder
    """
    return (lall,) + tuple(earlyorder(*goals))

def earlysafe(goal):
    """ Call goal be evaluated without raising an EarlyGoalError """
    try:
        goaleval(goal)
        return True
    except EarlyGoalError:
        return False

def earlyorder(*goals):
    """ Reorder goals to avoid EarlyGoalErrors

    All goals are evaluated.  Those that raise EarlyGoalErrors are placed at
    the end in a lallearly

    See also:
        EarlyGoalError
    """
    groups = groupby(earlysafe, goals)
    good = groups.get(True, [])
    bad  = groups.get(False, [])

    if not good:
        raise EarlyGoalError()
    elif not bad:
        return tuple(good)
    else:
        return tuple(good) + ((lallearly,) + tuple(bad),)

def conde(*goalseqs, **kwargs):
    """ Logical cond

    Goal constructor to provides logical AND and OR

    conde((A, B, C), (D, E)) means (A and B and C) or (D and E)

    See Also:
        lall - logical all
        lany - logical any
    """
    return (lany, ) + tuple((lallearly,) + tuple(gs) for gs in goalseqs)


def lanyseq(goals):
    """ Logical any with possibly infinite number of goals

    Note:  If using lanyseq with a generator you must call lanyseq, not include
    it in a tuple
    """
    def anygoal(s):
        anygoal.goals, local_goals = it.tee(anygoal.goals)
        def f(goals):
            for goal in goals:
                try:
                    yield goaleval(reify(goal, s))(s)
                except EarlyGoalError:
                    pass

        return unique(interleave(f(local_goals), [EarlyGoalError]),
                      key=dicthash)
    anygoal.goals = goals

    return anygoal

def condeseq(goalseqs):
    """ Like conde but supports generic (possibly infinite) iterator of goals"""
    return (lanyseq, ((lallearly,) + tuple(gs) for gs in goalseqs))

########################
# User level execution #
########################

def run(n, x, *goals, **kwargs):
    """ Run a logic program.  Obtain n solutions to satisfy goals.

    n     - number of desired solutions.  See ``take``
            0 for all
            None for a lazy sequence
    x     - Output variable
    goals - a sequence of goals.  All must be true

    >>> from logpy import run, var, eq
    >>> x = var()
    >>> run(1, x, eq(x, 1))
    (1,)
    """
    results = map(partial(reify, x), goaleval(lallearly(*goals))({}))
    return take(n, unique(results, key=multihash))

###################
# Goal Evaluation #
###################

class EarlyGoalError(Exception):
    """ A Goal has been constructed prematurely

    Consider the following case

    >>> from logpy import run, eq, membero, var
    >>> x, coll = var(), var()
    >>> run(0, x, (membero, x, coll), (eq, coll, (1, 2, 3))) # doctest: +SKIP

    The first goal, membero, iterates over an infinite sequence of all possible
    collections.  This is unproductive.  Rather than proceed, membero raises an
    EarlyGoalError, stating that this goal has been called early.

    The goal constructor lallearly Logical-All-Early will reorder such goals to
    the end so that the call becomes

    >>> run(0, x, (eq, coll, (1, 2, 3)), (membero, x, coll)) # doctest: +SKIP

    In this case coll is first unified to ``(1, 2, 3)`` then x iterates over
    all elements of coll, 1, then 2, then 3.

    See Also:
        lallearly
        earlyorder
    """

def goalexpand(goalt):
    """ Expand a goal tuple until it can no longer be expanded

    >>> from logpy.core import var, membero, goalexpand
    >>> from logpy.util import pprint
    >>> x = var('x')
    >>> goal = (membero, x, (1, 2, 3))
    >>> print(pprint(goalexpand(goal)))
    (lany, (eq, ~x, 1), (eq, ~x, 2), (eq, ~x, 3))
    """
    tmp = goalt
    while isinstance(tmp, tuple) and len(tmp) >= 1 and not callable(tmp):
        goalt = tmp
        tmp = goalt[0](*goalt[1:])
    return goalt


def goaleval(goal):
    """ Expand and then evaluate a goal

    Idempotent

    See also:
       goalexpand
    """
    if callable(goal):          # goal is already a function like eq(x, 1)
        return goal
    if isinstance(goal, tuple): # goal is not yet evaluated like (eq, x, 1)
        egoal = goalexpand(goal)
        # from logpy.util import pprint
        # print(pprint(egoal))
        return egoal[0](*egoal[1:])
    raise TypeError("Expected either function or tuple")

########NEW FILE########
__FILENAME__ = dispatch
from multipledispatch import dispatch
from functools import partial

namespace = dict()

dispatch = partial(dispatch, namespace=namespace)

########NEW FILE########
__FILENAME__ = facts
from .util import intersection, index
from .core import conde, reify, isvar
from toolz import merge

class Relation(object):
    _id = 0
    def __init__(self, name=None):
        self.facts = set()
        self.index = dict()
        if not name:
            name = "_%d"%Relation._id
            Relation._id += 1
        self.name = name

    def add_fact(self, *inputs):
        """ Add a fact to the knowledgebase.

        See Also:
            fact
            facts
        """
        fact = tuple(inputs)

        self.facts.add(fact)

        for key in enumerate(inputs):
            if key not in self.index:
                self.index[key] = set()
            self.index[key].add(fact)

    def __call__(self, *args):
        def f(s):
            args2 = reify(args, s)
            subsets = [self.index[key] for key in enumerate(args)
                                       if  key in self.index]
            if subsets:     # we are able to reduce the pool early
                facts = intersection(*sorted(subsets, key=len))
            else:
                facts = self.facts
            varinds = [i for i, arg in enumerate(args2) if isvar(arg)]
            valinds = [i for i, arg in enumerate(args2) if not isvar(arg)]
            vars = index(args2, varinds)
            vals = index(args2, valinds)
            assert not any(var in s for var in vars)

            return (merge(dict(zip(vars, index(fact, varinds))), s)
                              for fact in self.facts
                              if vals == index(fact, valinds))
        return f

    def __str__(self):
        return "Rel: " + self.name
    __repr__ = __str__


def fact(rel, *args):
    """ Declare a fact

    >>> from logpy import fact, Relation, var, run
    >>> parent = Relation()
    >>> fact(parent, "Homer", "Bart")
    >>> fact(parent, "Homer", "Lisa")

    >>> x = var()
    >>> run(1, x, parent(x, "Bart"))
    ('Homer',)
    """
    rel.add_fact(*args)

def facts(rel, *lists):
    """ Declare several facts

    >>> from logpy import fact, Relation, var, run
    >>> parent = Relation()
    >>> facts(parent,  ("Homer", "Bart"),
    ...                ("Homer", "Lisa"))

    >>> x = var()
    >>> run(1, x, parent(x, "Bart"))
    ('Homer',)
    """
    for l in lists:
        fact(rel, *l)


########NEW FILE########
__FILENAME__ = goals
from .core import (var, isvar, eq, EarlyGoalError, conde, condeseq, lany, lall,
        lallearly, fail, success)
from .util import unique
import itertools as it

def heado(x, coll):
    """ x is the head of coll

    See also:
        heado
        conso
    """
    if not isinstance(coll, tuple):
        raise EarlyGoalError()
    if isinstance(coll, tuple) and len(coll) >= 1:
        return (eq, x, coll[0])
    else:
        return fail

def tailo(x, coll):
    """ x is the tail of coll

    See also:
        heado
        conso
    """
    if not isinstance(coll, tuple):
        raise EarlyGoalError()
    if isinstance(coll, tuple) and len(coll) >= 1:
        return (eq, x, coll[1:])
    else:
        return fail

def conso(h, t, l):
    """ Logical cons -- l[0], l[1:] == h, t """
    if isinstance(l, tuple):
        if len(l) == 0:
            return fail
        else:
            return (conde, [(eq, h, l[0]), (eq, t, l[1:])])
    elif isinstance(t, tuple):
        return eq((h,) + t, l)
    else:
        raise EarlyGoalError()

def permuteq(a, b, eq2=eq):
    """ Equality under permutation

    For example (1, 2, 2) equates to (2, 1, 2) under permutation
    >>> from logpy import var, run, permuteq
    >>> x = var()
    >>> run(0, x, permuteq(x, (1, 2)))
    ((1, 2), (2, 1))

    >>> run(0, x, permuteq((2, 1, x), (2, 1, 2)))
    (2,)
    """
    if isinstance(a, tuple) and isinstance(b, tuple):
        if len(a) != len(b):
            return fail
        elif set(a) == set(b) and len(set(a)) == len(a):
            return success
        else:
            c, d = a, b
            try:
                c, d = tuple(sorted(c)), tuple(sorted(d))
            except:
                pass
            if len(c) == 1:
                return (eq2, c[0], d[0])
            return condeseq((
                   ((eq2, c[i], d[0]), (permuteq, c[0:i] + c[i+1:], d[1:], eq2))
                        for i in range(len(c))))

    if isvar(a) and isvar(b):
        raise EarlyGoalError()

    if isvar(a) or isvar(b):
        if isinstance(b, tuple):
            c, d = a, b
        elif isinstance(a, tuple):
            c, d = b, a

        return (condeseq, ([eq(c, perm)]
                           for perm in unique(it.permutations(d, len(d)))))

def seteq(a, b, eq2=eq):
    """ Set Equality

    For example (1, 2, 3) set equates to (2, 1, 3)

    >>> from logpy import var, run, seteq
    >>> x = var()
    >>> run(0, x, seteq(x, (1, 2)))
    ((1, 2), (2, 1))

    >>> run(0, x, seteq((2, 1, x), (3, 1, 2)))
    (3,)
    """
    ts = lambda x: tuple(set(x))
    if not isvar(a) and not isvar(b):
        return permuteq(ts(a), ts(b), eq2)
    elif not isvar(a):
        return permuteq(ts(a), b, eq2)
    elif not isvar(b):
        return permuteq(a, ts(b), eq2)
    else:
        return permuteq(a, b, eq2)

    raise Exception()


def goalify(func):
    """ Convert Python function into LogPy goal

    >>> from logpy import run, goalify, var, membero
    >>> typo = goalify(type)
    >>> x = var('x')
    >>> run(0, x, membero(x, (1, 'cat', 'hat', 2)), (typo, x, str))
    ('cat', 'hat')

    Goals go both ways.  Here are all of the types in the collection

    >>> typ = var('typ')
    >>> results = run(0, typ, membero(x, (1, 'cat', 'hat', 2)), (typo, x, typ))
    >>> print([result.__name__ for result in results])
    ['int', 'str']
    """
    def funco(inputs, out):
        if isvar(inputs):
            raise EarlyGoalError()
        else:
            if isinstance(inputs, (tuple, list)):
                return (eq, func(*inputs), out)
            else:
                return (eq, func(inputs), out)
    return funco

typo = goalify(type)
isinstanceo = goalify(isinstance)


"""
-This is an attempt to create appendo.  It does not currently work.
-As written in miniKanren, appendo uses LISP machinery not present in Python
-such as quoted expressions and macros for short circuiting.  I have gotten
-around some of these issues but not all.  appendo is a stress test for this
-implementation
"""

def appendo(l, s, ls):
    """ Byrd thesis pg. 247 """
    a, d, res = [var() for i in range(3)]
    return (lany, (lall, (eq, l, ()), (eq, s, ls)),
                  (lallearly, (conso, a, d, l), (conso, a, res, ls), (appendo, d, s, res)))

########NEW FILE########
__FILENAME__ = term
from .dispatch import dispatch
from .unification import unify, reify, _reify, _unify


@dispatch((tuple, list))
def arguments(seq):
    return seq[1:]


@dispatch((tuple, list))
def operator(seq):
    return seq[0]


@dispatch(object, (tuple, list))
def term(op, args):
    return (op,) + tuple(args)


def unifiable_with_term(cls):
    _reify.add((cls, dict), reify_term)
    _unify.add((cls, cls, dict), unify_term)
    return cls


def reify_term(obj, s):
    op, args = operator(obj), arguments(obj)
    op = reify(op, s)
    args = reify(args, s)
    new = term(op, args)
    return new


def unify_term(u, v, s):
    u_op, u_args = operator(u), arguments(u)
    v_op, v_args = operator(v), arguments(v)
    s = unify(u_op, v_op, s)
    if s is not False:
        s = unify(u_args, v_args, s)
    return s

########NEW FILE########
__FILENAME__ = test_arith
from logpy import var
from logpy.arith import lt, gt, lte, gte, add, sub, mul, mod

x = var('x')
y = var('y')
def results(g):
    return list(g({}))

def test_lt():
    assert results(lt(1, 2))
    assert not results(lt(2, 1))
    assert not results(lt(2, 2))

def test_gt():
    assert results(gt(2, 1))
    assert not results(gt(1, 2))
    assert not results(gt(2, 2))

def test_lte():
    assert results(lte(2, 2))

def test_gte():
    assert results(gte(2, 2))

def test_add():
    assert results(add(1, 2, 3))
    assert not results(add(1, 2, 4))
    assert results(add(1, 2, 3))

    assert results(add(1, 2, x)) == [{x: 3}]
    assert results(add(1, x, 3)) == [{x: 2}]
    assert results(add(x, 2, 3)) == [{x: 1}]

def test_sub():
    assert results(sub(3, 2, 1))
    assert not results(sub(4, 2, 1))

    assert results(sub(3, 2, x)) == [{x: 1}]
    assert results(sub(3, x, 1)) == [{x: 2}]
    assert results(sub(x, 2, 1)) == [{x: 3}]

def test_mul():
    assert results(mul(2, 3, 6))
    assert not results(mul(2, 3, 7))

    assert results(mul(2, 3, x)) == [{x: 6}]
    assert results(mul(2, x, 6)) == [{x: 3}]
    assert results(mul(x, 3, 6)) == [{x: 2}]

    assert mul.__name__ == 'mul'

def test_mod():
    assert results(mod(5, 3, 2))

def test_complex():
    from logpy import run, membero
    numbers = tuple(range(10))
    results = set(run(0, x, (sub, y, x, 1),
                            (membero, y, numbers),
                            (mod, y, 2, 0),
                            (membero, x, numbers)))
    expected = set((1, 3, 5, 7))
    print(results)
    assert results == expected

########NEW FILE########
__FILENAME__ = test_assoccomm
from logpy.core import var, run, eq, goaleval, EarlyGoalError
from logpy.facts import fact
from logpy.assoccomm import (associative, commutative, conde,
        groupsizes_to_partition, assocunify, eq_comm, eq_assoc,
        eq_assoccomm, assocsized, buildo, op_args)
from logpy.util import raises
from logpy.dispatch import dispatch

a = 'assoc_op'
c = 'comm_op'
x = var()
fact(associative, a)
fact(commutative, c)

def results(g, s={}):
    return tuple(goaleval(g)(s))

def test_eq_comm():
    assert results(eq_comm(1, 1))
    assert results(eq_comm((c, 1, 2, 3), (c, 1, 2, 3)))
    assert results(eq_comm((c, 3, 2, 1), (c, 1, 2, 3)))
    assert not results(eq_comm((a, 3, 2, 1), (a, 1, 2, 3))) # not commutative
    assert not results(eq_comm((3, c, 2, 1), (c, 1, 2, 3)))
    assert not results(eq_comm((c, 1, 2, 1), (c, 1, 2, 3)))
    assert not results(eq_comm((a, 1, 2, 3), (c, 1, 2, 3)))
    assert len(results(eq_comm((c, 3, 2, 1), x))) >= 6




def test_eq_assoc():
    assert results(eq_assoc(1, 1))
    assert results(eq_assoc((a, 1, 2, 3), (a, 1, 2, 3)))
    assert not results(eq_assoc((a, 3, 2, 1), (a, 1, 2, 3)))
    assert results(eq_assoc((a, (a, 1, 2), 3), (a, 1, 2, 3)))
    assert results(eq_assoc((a, 1, 2, 3), (a, (a, 1, 2), 3)))
    o = 'op'
    assert not results(eq_assoc((o, 1, 2, 3), (o, (o, 1, 2), 3)))

    # See TODO in assocunify
    gen = results(eq_assoc((a, 1, 2, 3), x, n=2))
    assert set(g[x] for g in gen).issuperset(set([(a,(a,1,2),3), (a,1,(a,2,3))]))

def test_eq_assoccomm():
    x, y = var(), var()
    eqac = eq_assoccomm
    ac = 'commassoc_op'
    fact(commutative, ac)
    fact(associative, ac)
    assert results(eqac(1, 1))
    assert results(eqac((1,), (1,)))
    assert results(eqac((ac, (ac, 1, x), y), (ac, 2, (ac, 3, 1))))
    assert results((eqac, 1, 1))
    assert results(eqac((a, (a, 1, 2), 3), (a, 1, 2, 3)))
    assert results(eqac((ac, (ac, 1, 2), 3), (ac, 1, 2, 3)))
    assert results(eqac((ac, 3, (ac, 1, 2)), (ac, 1, 2, 3)))
    assert run(0, x, eqac((ac, 3, (ac, 1, 2)), (ac, 1, x, 3))) == (2,)

def test_expr():
    add = 'add'
    mul = 'mul'
    fact(commutative, Add)
    fact(associative, Add)
    fact(commutative, Mul)
    fact(associative, Mul)

    x, y = var('x'), var('y')

    pattern = (mul, (add, 1, x), y)                # (1 + x) * y
    expr    = (mul, 2, (add, 3, 1))                # 2 * (3 + 1)
    assert run(0, (x,y), eq_assoccomm(pattern, expr)) == ((3, 2),)

def test_deep_commutativity():
    x, y = var('x'), var('y')

    e1 = (c, (c, 1, x), y)
    e2 = (c, 2, (c, 3, 1))
    assert run(0, (x,y), eq_comm(e1, e2)) == ((3, 2),)

def test_groupsizes_to_parition():
    assert groupsizes_to_partition(2, 3) == [[0, 1], [2, 3, 4]]

def test_assocunify():
    assert tuple(assocunify(1, 1, {}))
    assert tuple(assocunify((a, 1, 1), (a, 1, 1), {}))
    assert tuple(assocunify((a, 1, 2, 3), (a, 1, (a, 2, 3)), {}))
    assert tuple(assocunify((a, 1, (a, 2, 3)), (a, 1, 2, 3), {}))
    assert tuple(assocunify((a, 1, (a, 2, 3), 4), (a, 1, 2, 3, 4), {}))
    assert tuple(assocunify((a, 1, x, 4), (a, 1, 2, 3, 4), {})) == \
                ({x: (a, 2, 3)},)

    gen = assocunify((a, 1, 2, 3), x, {}, n=2)
    assert set(g[x] for g in gen) == set([(a,(a,1,2),3), (a,1,(a,2,3))])

    gen = assocunify((a, 1, 2, 3), x, {})
    assert set(g[x] for g in gen) == set([(a,1,2,3), (a,(a,1,2),3), (a,1,(a,2,3))])

def test_assocsized():
    add = 'add'
    assert set(assocsized(add, (1, 2, 3), 2)) == \
            set((((add, 1, 2), 3), (1, (add, 2, 3))))
    assert set(assocsized(add, (1, 2, 3), 1)) == \
            set((((add, 1, 2, 3),),))

def test_objects():
    from logpy import variables, reify, assoccomm

    fact(commutative, Add)
    fact(associative, Add)
    assert tuple(goaleval(eq_assoccomm(add(1, 2, 3), add(3, 1, 2)))({}))
    assert tuple(goaleval(eq_assoccomm(add(1, 2, 3), add(3, 1, 2)))({}))

    x = var('x')

    print(tuple(goaleval(eq_assoccomm(add(1, 2, 3), add(1, 2, x)))({})))
    assert reify(x, tuple(goaleval(eq_assoccomm(add(1, 2, 3),
                                                add(1, 2, x)))({}))[0]) == 3

    assert reify(x, next(goaleval(eq_assoccomm(add(1, 2, 3),
                                               add(x, 2, 1)))({}))) == 3

    v = add(1,2,3)
    with variables(v):
        x = add(5, 6)
        print(reify(v, next(goaleval(eq_assoccomm(v, x))({}))))
        assert reify(v, next(goaleval(eq_assoccomm(v, x))({}))) == x

"""
Failing test.  This would work if we flattened first
def test_deep_associativity():
    expr1 = (a, 1, 2, (a, x, 5, 6))
    expr2 = (a, (a, 1, 2), 3, 4, 5, 6)
    result = ({x: (a, 3, 4)})
    print(tuple(unify_assoc(expr1, expr2, {})))
    assert tuple(unify_assoc(expr1, expr2, {})) == result
"""

def test_buildo():
    x = var('x')
    assert results(buildo('add', (1,2,3), x), {}) == ({x: ('add', 1, 2, 3)},)
    assert results(buildo(x, (1,2,3), ('add', 1,2,3)), {}) == ({x: 'add'},)
    assert results(buildo('add', x, ('add', 1,2,3)), {}) == ({x: (1,2,3)},)

class Node(object):
    def __init__(self, op, args):
        self.op = op
        self.args = args
    def __eq__(self, other):
        return (type(self) == type(other)
                and self.op == other.op
                and self.args == other.args)
    def __hash__(self):
        return hash((type(self), self.op, self.args))
    def __str__(self):
        return '%s(%s)' % (self.op.name, ', '.join(map(str, self.args)))
    __repr__ = __str__

class Operator(object):
    def __init__(self, name):
        self.name = name
Add = Operator('add')
Mul = Operator('mul')

add = lambda *args: Node(Add, args)
mul = lambda *args: Node(Mul, args)

@dispatch(Operator, (tuple, list))
def term(op, args):
    return Node(op, args)

@dispatch(Node)
def arguments(n):
    return n.args

@dispatch(Node)
def operator(n):
    return n.op


def test_op_args():
    print(op_args(add(1,2,3)))
    assert op_args(add(1,2,3)) == (Add, (1,2,3))
    assert op_args('foo') == (None, None)

def test_buildo_object():
    x = var('x')
    assert results(buildo(Add, (1,2,3), x), {}) == \
            ({x: add(1, 2, 3)},)
    print(results(buildo(x, (1,2,3), add(1,2,3)), {}))
    assert results(buildo(x, (1,2,3), add(1,2,3)), {}) == \
            ({x: Add},)
    assert results(buildo(Add, x, add(1,2,3)), {}) == \
            ({x: (1,2,3)},)


def test_eq_comm_object():
    x = var('x')
    fact(commutative, Add)
    fact(associative, Add)

    assert run(0, x, eq_comm(add(1, 2, 3), add(3, 1, x))) == (2,)

    print(set(run(0, x, eq_comm(add(1, 2), x))))
    assert set(run(0, x, eq_comm(add(1, 2), x))) == set((add(1, 2), add(2, 1)))

    print(set(run(0, x, eq_assoccomm(add(1, 2, 3), add(1, x)))))
    assert set(run(0, x, eq_assoccomm(add(1, 2, 3), add(1, x)))) == \
            set((add(2, 3), add(3, 2)))

########NEW FILE########
__FILENAME__ = test_core
from logpy.core import (walk, walkstar, isvar, var, run,
        membero, evalt, fail, success, eq, conde,
        condeseq, goaleval, lany, lall, lanyseq,
        goalexpand, earlyorder, EarlyGoalError, lallearly, earlysafe)
import itertools
from logpy.util import raises

w, x, y, z = 'wxyz'

def test_walk():
    s = {1: 2, 2: 3}
    assert walk(2, s) == 3
    assert walk(1, s) == 3
    assert walk(4, s) == 4

def test_deep_walk():
    """ Page 30 of Byrd thesis """
    s = {z: 6, y: 5, x: (y, z)}
    assert walk(x, s) == (y, z)
    assert walkstar(x, s) == (5, 6)

def test_eq():
    x = var('x')
    assert tuple(eq(x, 2)({})) == ({x: 2},)
    assert tuple(eq(x, 2)({x: 3})) == ()

def test_lany():
    x = var('x')
    assert len(tuple(lany(eq(x, 2), eq(x, 3))({}))) == 2
    assert len(tuple(lany((eq, x, 2), (eq, x, 3))({}))) == 2

def test_lall():
    x = var('x')
    assert results(lall((eq, x, 2))) == ({x: 2},)
    assert results(lall((eq, x, 2), (eq, x, 3))) == ()

def test_earlysafe():
    x, y = var('x'), var('y')
    assert earlysafe((eq, 2, 2))
    assert earlysafe((eq, 2, 3))
    assert earlysafe((membero, x, (1,2,3)))
    assert not earlysafe((membero, x, y))

def test_earlyorder():
    x, y = var(), var()
    assert earlyorder((eq, 2, x)) == ((eq, 2, x),)
    assert earlyorder((eq, 2, x), (eq, 3, x)) == ((eq, 2, x), (eq, 3, x))
    assert earlyorder((membero, x, y), (eq, y, (1,2,3)))[0] == (eq, y, (1,2,3))

def test_conde():
    x = var('x')
    assert results(conde([eq(x, 2)], [eq(x, 3)])) == ({x: 2}, {x: 3})
    assert results(conde([eq(x, 2), eq(x, 3)])) == ()

"""
def test_condeseq():
    x = var('x')
    assert tuple(condeseq(([eq(x, 2)], [eq(x, 3)]))({})) == ({x: 2}, {x: 3})
    assert tuple(condeseq([[eq(x, 2), eq(x, 3)]])({})) == ()

    goals = ([eq(x, i)] for i in itertools.count()) # infinite number of goals
    assert next(condeseq(goals)({})) == {x: 0}
"""

def test_short_circuit():
    def badgoal(s):
        raise NotImplementedError()

    x = var('x')
    tuple(run(5, x, fail, badgoal)) # Does not raise exception

def test_run():
    x,y,z = map(var, 'xyz')
    assert run(1, x,  eq(x, 1)) == (1,)
    assert run(2, x,  eq(x, 1)) == (1,)
    assert run(0, x,  eq(x, 1)) == (1,)
    assert run(1, x,  eq(x, (y, z)),
                       eq(y, 3),
                       eq(z, 4)) == ((3, 4),)
    assert set(run(2, x, conde([eq(x, 1)], [eq(x, 2)]))) == set((1, 2))

def test_run_output_reify():
    x = var()
    assert run(0, (1, 2, x), eq(x, 3)) == ((1, 2, 3),)

def test_membero():
    x = var('x')
    assert set(run(5, x, membero(x, (1,2,3)),
                         membero(x, (2,3,4)))) == set((2,3))

    assert run(5, x, membero(2, (1, x, 3))) == (2,)

def test_lanyseq():
    x = var('x')
    g = lanyseq(((eq, x, i) for i in range(3)))
    assert list(goaleval(g)({})) == [{x: 0}, {x: 1}, {x: 2}]
    assert list(goaleval(g)({})) == [{x: 0}, {x: 1}, {x: 2}]

def test_membero_can_be_reused():
    x = var('x')
    g = membero(x, (0, 1, 2))
    assert list(goaleval(g)({})) == [{x: 0}, {x: 1}, {x: 2}]
    assert list(goaleval(g)({})) == [{x: 0}, {x: 1}, {x: 2}]

def test_evalt():
    add = lambda x, y: x + y
    assert evalt((add, 2, 3)) == 5
    assert evalt(add(2, 3)) == 5
    assert evalt((1,2)) == (1,2)

def test_uneval_membero():
    x, y = var('x'), var('y')
    assert set(run(100, x, (membero, y, ((1,2,3),(4,5,6))), (membero, x, y))) == \
           set((1,2,3,4,5,6))

def test_goaleval():
    x, y = var('x'), var('y')
    g = eq(x, 2)
    assert goaleval(g) == g
    assert callable(goaleval((eq, x, 2)))
    raises(EarlyGoalError, lambda: goaleval((membero, x, y)))
    assert callable(goaleval((lall, (eq, x, 2))))

def test_goalexpand():
    def growing_goal(*args):
        if len(args) < 10:
            return (growing_goal, 1) + tuple(args)
        else:
            return lambda s: (1,)

    g = (growing_goal, 2)
    assert goalexpand(g) == (growing_goal, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2)

def test_early():
    x, y = var(), var()
    assert run(0, x, lallearly((eq, y, (1, 2)), (membero, x, y)))
    assert run(0, x, lallearly((membero, x, y), (eq, y, (1, 2))))

def test_lany_is_early_safe():
    x = var()
    y = var()
    assert run(0, x, lany((membero, x, y), (eq, x, 2))) == (2,)

def results(g, s={}):
    return tuple(goaleval(g)(s))

def test_dict():
    x = var()
    assert run(0, x, eq({1: x}, {1: 2})) == (2,)

########NEW FILE########
__FILENAME__ = test_facts
from logpy.facts import Relation, fact, facts
from logpy.core import var, run, conde, reify

def test_relation():
    parent = Relation()
    fact(parent, "Homer", "Bart")
    fact(parent, "Homer", "Lisa")
    fact(parent, "Marge", "Bart")
    fact(parent, "Marge", "Lisa")
    fact(parent, "Abe", "Homer")
    fact(parent, "Jackie", "Marge")

    x = var('x')
    assert set(run(5, x, parent("Homer", x))) == set(("Bart", "Lisa"))
    assert set(run(5, x, parent(x, "Bart")))  == set(("Homer", "Marge"))

    def grandparent(x, z):
        y = var()
        return conde((parent(x, y), parent(y, z)))

    assert set(run(5, x, grandparent(x, "Bart") )) == set(("Abe", "Jackie"))

    foo = Relation('foo')
    assert 'foo' in str(foo)

def test_fact():
    rel = Relation()
    fact(rel, 1, 2)
    assert (1, 2) in rel.facts
    assert (10, 10) not in rel.facts

    facts(rel, (2, 3), (3, 4))
    assert (2, 3) in rel.facts
    assert (3, 4) in rel.facts


########NEW FILE########
__FILENAME__ = test_goals
from logpy.goals import (tailo, heado, appendo, seteq, conso, typo,
        isinstanceo, permuteq)
from logpy.core import var, run, eq, EarlyGoalError, goaleval, membero
from logpy.util import raises

def results(g, s={}):
    return tuple(goaleval(g)(s))

def test_heado():
    x, y = var('x'), var('y')
    assert results(heado(x, (1,2,3))) == ({x: 1},)
    assert results(heado(1, (x,2,3))) == ({x: 1},)
    raises(EarlyGoalError, lambda: heado(x, y))

def test_tailo():
    x, y = var('x'), var('y')
    assert results((tailo, x, (1,2,3))) == ({x: (2,3)},)
    raises(EarlyGoalError, lambda: tailo(x, y))

def test_conso():
    x = var()
    y = var()
    assert not results(conso(x, y, ()))
    assert results(conso(1, (2, 3), (1, 2, 3)))
    assert results(conso(x, (2, 3), (1, 2, 3))) == ({x: 1},)
    assert results(conso(1, (2, 3), x)) == ({x: (1, 2, 3)},)
    assert results(conso(x, y, (1, 2, 3))) == ({x: 1, y: (2, 3)},)
    assert results(conso(x, (2, 3), y)) == ({y: (x, 2, 3)},)
    # assert tuple(conde((conso(x, y, z), (membero, x, z)))({}))

def test_seteq():
    x = var('x')
    y = var('y')
    abc = tuple('abc')
    bca = tuple('bca')
    assert results(seteq(abc, bca))
    assert len(results(seteq(abc, x))) == 6
    assert len(results(seteq(x, abc))) == 6
    assert bca in run(0, x, seteq(abc, x))
    assert results(seteq((1, 2, 3), (3, x, 1))) == ({x: 2},)

    assert run(0, (x, y), seteq((1, 2, x), (2, 3, y)))[0] == (3, 1)
    assert not run(0, (x, y), seteq((4, 5, x), (2, 3, y)))

def test_permuteq():
    x = var('x')
    assert results(permuteq((1,2,2), (2,1,2)))
    assert not results(permuteq((1,2), (2,1,2)))
    assert not results(permuteq((1,2,3), (2,1,2)))
    assert not results(permuteq((1,2,1), (2,1,2)))

    assert set(run(0, x, permuteq(x, (1,2,2)))) == set(
            ((1,2,2), (2,1,2), (2,2,1)))

def test_typo():
    x = var('x')
    assert results(typo(3, int))
    assert not results(typo(3.3, int))
    assert run(0, x, membero(x, (1, 'cat', 2.2, 'hat')), (typo, x, str)) ==\
            ('cat', 'hat')

def test_isinstanceo():
    assert results(isinstanceo((3, int), True))
    assert not results(isinstanceo((3, float), True))
    assert results(isinstanceo((3, float), False))


def test_conso_early():
    x, y, z = var(), var(), var()
    assert (run(0, x, (conso, x, y, z), (eq, z, (1, 2, 3)))
            == (1,))

def test_appendo():
    x = var('x')
    assert results(appendo((), (1,2), (1,2))) == ({},)
    assert results(appendo((), (1,2), (1))) == ()
    assert results(appendo((1,2), (3,4), (1,2,3,4)))
    assert run(5, x, appendo((1,2,3), x, (1,2,3,4,5))) == ((4,5),)

"""
Failing test
def test_appendo2():
    print(run(5, x, appendo((1,2,3), (4,5), x)))
    assert run(5, x, appendo(x, (4,5), (1,2,3,4,5))) == ((1,2,3),)
    assert run(5, x, appendo((1,2,3), (4,5), x)) == ((1,2,3,4,5),)
"""

########NEW FILE########
__FILENAME__ = test_term
from logpy.term import term, operator, arguments, unifiable_with_term
from logpy import var, unify, reify
from logpy.dispatch import dispatch

def test_arguments():
    assert arguments(('add', 1, 2, 3)) == (1, 2, 3)


def test_operator():
    assert operator(('add', 1, 2, 3)) == 'add'


def test_term():
    assert term('add', (1, 2, 3)) == ('add', 1, 2, 3)


class Op(object):
    def __init__(self, name):
        self.name = name

@unifiable_with_term
class MyTerm(object):
    def __init__(self, op, arguments):
        self.op = op
        self.arguments = arguments
    def __eq__(self, other):
        return self.op == other.op and self.arguments == other.arguments

@dispatch(MyTerm)
def arguments(t):
    return t.arguments

@dispatch(MyTerm)
def operator(t):
    return t.op

@dispatch(Op, (list, tuple))
def term(op, args):
    return MyTerm(op, args)

def test_unifiable_with_term():
    add = Op('add')
    t = MyTerm(add, (1, 2))
    assert arguments(t) == (1, 2)
    assert operator(t) == add
    assert term(operator(t), arguments(t)) == t

    x = var('x')
    assert unify(MyTerm(add, (1, x)), MyTerm(add, (1, 2)), {}) == {x: 2}


########NEW FILE########
__FILENAME__ = test_unification
from logpy.unification import unify, reify, _unify, _reify
from logpy import var

def test_reify():
    x, y, z = var(), var(), var()
    s = {x: 1, y: 2, z: (x, y)}
    assert reify(x, s) == 1
    assert reify(10, s) == 10
    assert reify((1, y), s) == (1, 2)
    assert reify((1, (x, (y, 2))), s) == (1, (1, (2, 2)))
    assert reify(z, s) == (1, 2)

def test_reify_dict():
    x, y = var(), var()
    s = {x: 2, y: 4}
    e = {1: x, 3: {5: y}}
    assert reify(e, s) == {1: 2, 3: {5: 4}}

def test_reify_list():
    x, y = var(), var()
    s = {x: 2, y: 4}
    e = [1, [x, 3], y]
    assert reify(e, s) == [1, [2, 3], 4]

def test_reify_complex():
    x, y = var(), var()
    s = {x: 2, y: 4}
    e = {1: [x], 3: (y, 5)}

    assert reify(e, s) == {1: [2], 3: (4, 5)}

def test_unify():
    assert unify(1, 1, {}) == {}
    assert unify(1, 2, {}) == False
    assert unify(var(1), 2, {}) == {var(1): 2}
    assert unify(2, var(1), {}) == {var(1): 2}

def test_unify_seq():
    assert unify((1, 2), (1, 2), {}) == {}
    assert unify([1, 2], [1, 2], {}) == {}
    assert unify((1, 2), (1, 2, 3), {}) == False
    assert unify((1, var(1)), (1, 2), {}) == {var(1): 2}
    assert unify((1, var(1)), (1, 2), {var(1): 3}) == False

def test_unify_dict():
    assert unify({1: 2}, {1: 2}, {}) == {}
    assert unify({1: 2}, {1: 3}, {}) == False
    assert unify({2: 2}, {1: 2}, {}) == False
    assert unify({1: var(5)}, {1: 2}, {}) == {var(5): 2}

def test_unify_complex():
    assert unify((1, {2: 3}), (1, {2: 3}), {}) == {}
    assert unify((1, {2: 3}), (1, {2: 4}), {}) == False
    assert unify((1, {2: var(5)}), (1, {2: 4}), {}) == {var(5): 4}

    assert unify({1: (2, 3)}, {1: (2, var(5))}, {}) == {var(5): 3}
    assert unify({1: [2, 3]}, {1: [2, var(5)]}, {}) == {var(5): 3}

########NEW FILE########
__FILENAME__ = test_unifymore
from logpy.unifymore import (unify_object, reify_object,
        reify_object_attrs, unify_object_attrs, unifiable)
from logpy import var, run, eq
from logpy.unification import unify, reify, _unify, _reify
from logpy import variables

class Foo(object):
        def __init__(self, a, b):
            self.a = a
            self.b = b
        def __eq__(self, other):
            return (self.a, self.b) == (other.a, other.b)


class Bar(object):
        def __init__(self, c):
            self.c = c
        def __eq__(self, other):
            return self.c == other.c


def test_run_objects_with_context_manager():
    f = Foo(1, 1234)
    g = Foo(1, 2)
    _unify.add((Foo, Foo, dict), unify_object)
    _reify.add((Foo, dict), reify_object)
    with variables(1234):
        assert unify_object(f, g, {})
        assert run(1, 1234, (eq, f, g)) == (2,)
        assert run(1, Foo(1234, 1234), (eq, f, g)) == (Foo(2, 2),)


def test_unify_object():
    assert unify_object(Foo(1, 2), Foo(1, 2), {}) == {}
    assert unify_object(Foo(1, 2), Foo(1, 3), {}) == False
    assert unify_object(Foo(1, 2), Foo(1, var(3)), {}) == {var(3): 2}


def test_reify_object():
    obj = reify_object(Foo(1, var(3)), {var(3): 4})
    assert obj.a == 1
    assert obj.b == 4

    f = Foo(1, 2)
    assert reify_object(f, {}) is f


def test_objects_full():
    _unify.add((Foo, Foo, dict), unify_object)
    _unify.add((Bar, Bar, dict), unify_object)
    _reify.add((Foo, dict), reify_object)
    _reify.add((Bar, dict), reify_object)

    assert unify_object(Foo(1, Bar(2)), Foo(1, Bar(var(3))), {}) == {var(3): 2}
    assert reify(Foo(var('a'), Bar(Foo(var('b'), 3))),
                 {var('a'): 1, var('b'): 2}) == Foo(1, Bar(Foo(2, 3)))


def test_list_1():
    _unify.add((Foo, Foo, dict), unify_object)
    _reify.add((Foo, dict), reify_object)

    x = var('x')
    y = var('y')
    rval = run(0, (x, y), (eq, Foo(1, [2]), Foo(x, [y])))
    assert rval == ((1, 2),)

    rval = run(0, (x, y), (eq, Foo(1, [2]), Foo(x, y)))
    assert rval == ((1, [2]),)


def test_unify_slice():
    x = var('x')
    y = var('y')

    assert unify(slice(1), slice(1), {}) == {}
    assert unify(slice(1, 2, 3), x, {}) == {x: slice(1, 2, 3)}
    assert unify(slice(1, 2, None), slice(x, y), {}) == {x: 1, y: 2}


def test_reify_slice():
    x = var('x')
    assert reify(slice(1, var(2), 3), {var(2): 10}) == slice(1, 10, 3)


def test_unify_object_attrs():
    x, y = var('x'), var('y')
    f, g = Foo(1, 2), Foo(x, y)
    assert unify_object_attrs(f, g, {}, ['a']) == {x: 1}
    assert unify_object_attrs(f, g, {}, ['b']) == {y: 2}
    assert unify_object_attrs(f, g, {}, []) == {}


def test_reify_object_attrs():
    x, y = var('x'), var('y')
    f, g = Foo(1, 2), Foo(x, y)
    s = {x: 1, y: 2}
    assert reify_object_attrs(g, s, ['a', 'b']) == f
    assert reify_object_attrs(g, s, ['a']) ==  Foo(1, y)
    assert reify_object_attrs(g, s, ['b']) ==  Foo(x, 2)
    assert reify_object_attrs(g, s, []) is g


def test_unify_isinstance_list():
    class Foo2(Foo): pass
    x = var('x')
    y = var('y')
    f, g = Foo2(1, 2), Foo2(x, y)

    _unify.add((Foo, Foo, dict), unify_object)
    _reify.add((Foo, dict), reify_object)

    assert unify(f, g, {})
    assert reify(g, {x: 1, y: 2}) == f


@unifiable
class A(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def test_unifiable():
    x = var('x')
    f = A(1, 2)
    g = A(1, x)
    assert unify(f, g, {}) == {x: 2}
    assert reify(g, {x: 2}) == f


@unifiable
class Aslot(object):
    slots = 'a', 'b'
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def test_unifiable():
    x = var('x')
    f = Aslot(1, 2)
    g = Aslot(1, x)
    assert unify(f, g, {}) == {x: 2}
    assert reify(g, {x: 2}) == f

########NEW FILE########
__FILENAME__ = test_util
from logpy.util import (take, unique, interleave, intersection,
        groupsizes, raises, dicthash, hashable, multihash)
import itertools

def test_hashable():
    assert hashable(2)
    assert hashable((2,3))
    assert not hashable({1: 2})
    assert not hashable((1, {2: 3}))

def test_unique():
    assert tuple(unique((1,2,3))) == (1,2,3)
    assert tuple(unique((1,2,1,3))) == (1,2,3)

def test_unique_dict():
    assert tuple(unique(({1: 2}, {2: 3}), key=dicthash)) == ({1: 2}, {2: 3})
    assert tuple(unique(({1: 2}, {1: 2}), key=dicthash)) == ({1: 2},)

def test_unique_not_hashable():
    assert tuple(unique(([1], [1])))

def test_multihash():
    inputs = 2, (1, 2), [1, 2], {1: 2}, (1, [2]), slice(1, 2)
    assert all(isinstance(multihash(i), int) for i in inputs)

def test_intersection():
    a,b,c = (1,2,3,4), (2,3,4,5), (3,4,5,6)

    assert tuple(intersection(a,b,c)) == (3,4)

def test_take():
    assert take(2, range(5)) == (0, 1)
    assert take(0, range(5)) == (0, 1, 2, 3, 4)
    seq = range(5)
    assert take(None, seq) == seq

def test_interleave():
    assert ''.join(interleave(('ABC', '123'))) == 'A1B2C3'
    assert ''.join(interleave(('ABC', '1'))) == 'A1BC'

def test_groupsizes():
    assert set(groupsizes(4, 2)) == set(((1, 3), (2, 2), (3, 1)))
    assert set(groupsizes(5, 2)) == set(((1, 4), (2, 3), (3, 2), (4, 1)))
    assert set(groupsizes(4, 1)) == set([(4,)])
    assert set(groupsizes(4, 4)) == set([(1, 1, 1, 1)])

def test_raises():
    raises(ZeroDivisionError, lambda: 1/0)

########NEW FILE########
__FILENAME__ = test_variable
from logpy.variable import isvar, var, vars, variables

def test_isvar():
    assert not isvar(3)
    assert isvar(var(3))

def test_var():
    assert var(1) == var(1)
    assert var() != var()

def test_var_inputs():
    assert var(1) == var(1)
    assert var() != var()

def test_vars():
    vs = vars(3)
    assert len(vs) == 3
    assert all(map(isvar, vs))

def test_context_manager():
    with variables(1):
        assert isvar(1)
    assert not isvar(1)

########NEW FILE########
__FILENAME__ = unification
from functools import partial
from .util import transitive_get as walk
from .variable import Var, var, isvar
import itertools as it
from .dispatch import dispatch
from collections import Iterator
from toolz.compatibility import iteritems, map
from toolz import assoc

################
# Reificiation #
################

@dispatch(Iterator, dict)
def _reify(t, s):
    return map(partial(reify, s=s), t)
    # return (reify(arg, s) for arg in t)

@dispatch(tuple, dict)
def _reify(t, s):
    return tuple(reify(iter(t), s))

@dispatch(list, dict)
def _reify(t, s):
    return list(reify(iter(t), s))

@dispatch(dict, dict)
def _reify(d, s):
    return dict((k, reify(v, s)) for k, v in d.items())

@dispatch(object, dict)
def _reify(o, s):
    return o  # catch all, just return the object


def reify(e, s):
    """ Replace variables of expression with substitution

    >>> from logpy.unification import reify, var
    >>> x, y = var(), var()
    >>> e = (1, x, (3, y))
    >>> s = {x: 2, y: 4}
    >>> reify(e, s)
    (1, 2, (3, 4))

    >>> e = {1: x, 3: (y, 5)}
    >>> reify(e, s)
    {1: 2, 3: (4, 5)}
    """
    if isvar(e):
        return reify(s[e], s) if e in s else e
    return _reify(e, s)

###############
# Unification #
###############

seq = tuple, list, Iterator

@dispatch(seq, seq, dict)
def _unify(u, v, s):
    # assert isinstance(u, tuple) and isinstance(v, tuple)
    if len(u) != len(v):
        return False
    for uu, vv in zip(u, v):  # avoiding recursion
        s = unify(uu, vv, s)
        if s is False:
            return False
    return s


@dispatch(dict, dict, dict)
def _unify(u, v, s):
    # assert isinstance(u, dict) and isinstance(v, dict)
    if len(u) != len(v):
        return False
    for key, uval in iteritems(u):
        if key not in v:
            return False
        s = unify(uval, v[key], s)
        if s is False:
            return False
    return s


@dispatch(object, object, dict)
def _unify(u, v, s):
    return False  # catch all


def unify(u, v, s):  # no check at the moment
    """ Find substitution so that u == v while satisfying s

    >>> from logpy.unification import unify, var
    >>> x = var('x')
    >>> unify((1, x), (1, 2), {})
    {~x: 2}
    """
    u = walk(u, s)
    v = walk(v, s)
    if u == v:
        return s
    if isvar(u):
        return assoc(s, u, v)
    if isvar(v):
        return assoc(s, v, u)
    return _unify(u, v, s)

########NEW FILE########
__FILENAME__ = unifymore
from logpy.unification import unify, reify
from functools import partial
from .dispatch import dispatch

#########
# Reify #
#########


@dispatch(slice, dict)
def _reify(o, s):
    """ Reify a Python ``slice`` object """
    return slice(*reify((o.start, o.stop, o.step), s))


def reify_object(o, s):
    """ Reify a Python object with a substitution

    >>> from logpy.unifymore import reify_object
    >>> from logpy import var
    >>> class Foo(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))

    >>> x = var('x')
    >>> f = Foo(1, x)
    >>> print(f)
    Foo(1, ~x)
    >>> print(reify_object(f, {x: 2}))
    Foo(1, 2)
    """

    obj = object.__new__(type(o))
    d = reify(o.__dict__, s)
    if d == o.__dict__:
        return o
    obj.__dict__.update(d)
    return obj


def reify_object_slots(o, s):
    """
    >>> from logpy.unifymore import reify_object_slots
    >>> from logpy import var
    >>> class Foo(object):
    ...     __slots__ = 'a', 'b'
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))
    >>> x = var('x')
    >>> print(reify_object_slots(Foo(x, 2), {x: 1}))
    Foo(1, 2)
    """
    attrs = [getattr(o, attr) for attr in o.__slots__]
    new_attrs = reify(attrs, s)
    if attrs == new_attrs:
        return o
    else:
        newobj = object.__new__(type(o))
        for slot, attr in zip(o.__slots__, new_attrs):
            setattr(newobj, slot, attr)
        return newobj


def reify_object_attrs(o, s, attrs):
    """ Reify only certain attributes of a Python object

    >>> from logpy.unifymore import reify_object_attrs
    >>> from logpy import var
    >>> class Foo(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))

    >>> x = var('x')
    >>> y = var('y')
    >>> f = Foo(x, y)
    >>> print(f)
    Foo(~x, ~y)
    >>> print(reify_object_attrs(f, {x: 1, y: 2}, ['a', 'b']))
    Foo(1, 2)
    >>> print(reify_object_attrs(f, {x: 1, y: 2}, ['a']))
    Foo(1, ~y)

    This function is meant to be partially specialized

    >>> from functools import partial
    >>> reify_Foo_a = partial(reify_object_attrs, attrs=['a'])

    attrs contains the list of attributes which participate in reificiation
    """
    obj = object.__new__(type(o))
    d = dict(zip(attrs, [getattr(o, attr) for attr in attrs]))
    d2 = reify(d, s)                             # reified attr dict
    if d2 == d:
        return o

    obj.__dict__.update(o.__dict__)                   # old dict
    obj.__dict__.update(d2)                           # update w/ reified vals
    return obj

#########
# Unify #
#########

@dispatch(slice, slice, dict)
def _unify(u, v, s):
    """ Unify a Python ``slice`` object """
    return unify((u.start, u.stop, u.step), (v.start, v.stop, v.step), s)


def unify_object(u, v, s):
    """ Unify two Python objects

    Unifies their type and ``__dict__`` attributes

    >>> from logpy.unifymore import unify_object
    >>> from logpy import var
    >>> class Foo(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))

    >>> x = var('x')
    >>> f = Foo(1, x)
    >>> g = Foo(1, 2)
    >>> unify_object(f, g, {})
    {~x: 2}
    """
    if type(u) != type(v):
        return False
    return unify(u.__dict__, v.__dict__, s)




def unify_object_attrs(u, v, s, attrs):
    """ Unify only certain attributes of two Python objects

    >>> from logpy.unifymore import unify_object_attrs
    >>> from logpy import var
    >>> class Foo(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    ...     def __str__(self):
    ...         return "Foo(%s, %s)"%(str(self.a), str(self.b))

    >>> x = var('x')
    >>> y = var('y')
    >>> f = Foo(x, y)
    >>> g = Foo(1, 2)
    >>> print(unify_object_attrs(f, g, {}, ['a', 'b']))  #doctest: +SKIP
    {~x: 1, ~y: 2}
    >>> print(unify_object_attrs(f, g, {}, ['a']))
    {~x: 1}

    This function is meant to be partially specialized

    >>> from functools import partial
    >>> unify_Foo_a = partial(unify_object_attrs, attrs=['a'])

    attrs contains the list of attributes which participate in reificiation
    """
    return unify([getattr(u, a) for a in attrs],
                 [getattr(v, a) for a in attrs],
                 s)


# Registration

def register_reify_object_attrs(cls, attrs):
    _reify.add((cls,), partial(reify_object_attrs, attrs=attrs))


def register_unify_object(cls):
    _unify.add((cls, cls, dict), unify_object)


def register_unify_object_attrs(cls, attrs):
    _unify.add((cls, cls, dict), partial(unify_object_attrs, attrs=attrs))


def register_object_attrs(cls, attrs):
    register_unify_object_attrs(cls, attrs)
    register_reify_object_attrs(cls, attrs)


def unifiable(cls):
    """ Register standard unify and reify operations on class

    This uses the type and __dict__ or __slots__ attributes to define the
    nature of the term

    See Also:

    >>> from logpy import run, var, eq
    >>> from logpy.unifymore import unifiable
    >>> class A(object):
    ...     def __init__(self, a, b):
    ...         self.a = a
    ...         self.b = b
    >>> unifiable(A)
    <class 'logpy.unifymore.A'>

    >>> x = var('x')
    >>> a = A(1, 2)
    >>> b = A(1, x)

    >>> run(1, x, eq(a, b))
    (2,)
    """
    if hasattr(cls, '__slots__'):
        _reify.add((cls, dict), reify_object_slots)
        _unify.add((cls, cls, dict), unify_object_slots)
    else:
        _reify.add((cls, dict), reify_object)
        _unify.add((cls, cls, dict), unify_object)

    return cls

########NEW FILE########
__FILENAME__ = util
import itertools as it
from toolz.compatibility import range, map, iteritems

def hashable(x):
    try:
        hash(x)
        return True
    except TypeError:
        return False

def transitive_get(key, d):
    """ Transitive dict.get

    >>> from logpy.util import transitive_get
    >>> d = {1: 2, 2: 3, 3: 4}
    >>> d.get(1)
    2
    >>> transitive_get(1, d)
    4
    """
    while hashable(key) and key in d:
        key = d[key]
    return key

def deep_transitive_get(key, d):
    """ Transitive get that propagates within tuples

    >>> from logpy.util import transitive_get, deep_transitive_get
    >>> d = {1: (2, 3), 2: 12, 3: 13}
    >>> transitive_get(1, d)
    (2, 3)
    >>> deep_transitive_get(1, d)
    (12, 13)
    """

    key = transitive_get(key, d)
    if isinstance(key, tuple):
        return tuple(map(lambda k: deep_transitive_get(k, d), key))
    else:
        return key

def dicthash(d):
    return hash(frozenset(d.items()))

def multihash(x):
    try:
        return hash(x)
    except TypeError:
        if isinstance(x, (list, tuple, set, frozenset)):
            return hash(tuple(map(multihash, x)))
        if type(x) is dict:
            return hash(frozenset(map(multihash, x.items())))
        if type(x) is slice:
            return hash((x.start, x.stop, x.step))
        raise TypeError('Hashing not covered for ' + str(x))

def unique(seq, key=lambda x: x):
    seen = set()
    for item in seq:
        try:
            if key(item) not in seen:
                seen.add(key(item))
                yield item
        except TypeError:   # item probably isn't hashable
            yield item      # Just return it and hope for the best

def interleave(seqs, pass_exceptions=()):
    iters = map(iter, seqs)
    while iters:
        newiters = []
        for itr in iters:
            try:
                yield next(itr)
                newiters.append(itr)
            except (StopIteration,) + tuple(pass_exceptions):
                pass
        iters = newiters

def take(n, seq):
    if n is None:
        return seq
    if n == 0:
        return tuple(seq)
    return tuple(it.islice(seq, 0, n))


def evalt(t):
    """ Evaluate tuple if unevaluated

    >>> from logpy.util import evalt
    >>> add = lambda x, y: x + y
    >>> evalt((add, 2, 3))
    5
    >>> evalt(add(2, 3))
    5
    """

    if isinstance(t, tuple) and len(t) >= 1 and callable(t[0]):
        return t[0](*t[1:])
    else:
        return t

def intersection(*seqs):
    return (item for item in seqs[0]
                 if all(item in seq for seq in seqs[1:]))

def groupsizes(total, len):
    """ Groups of length len that add up to total

    >>> from logpy.util import groupsizes
    >>> tuple(groupsizes(4, 2))
    ((1, 3), (2, 2), (3, 1))
    """
    if len == 1:
        yield (total,)
    else:
        for i in range(1, total - len + 1 + 1):
            for perm in groupsizes(total - i, len - 1):
                yield (i,) + perm

def raises(err, lamda):
    try:
        lamda()
        raise Exception("Did not raise %s"%err)
    except err:
        pass

def pprint(g):
    """ Pretty print a tree of goals """
    if callable(g) and hasattr(g, '__name__'):
        return g.__name__
    if isinstance(g, type):
        return g.__name__
    if isinstance(g, tuple):
        return "(" + ', '.join(map(pprint, g)) + ")"
    return str(g)

def index(tup, ind):
    """ Fancy indexing with tuples """
    return tuple(tup[i] for i in ind)

########NEW FILE########
__FILENAME__ = variable
from contextlib import contextmanager
from .util import hashable
from .dispatch import dispatch

_global_logic_variables = set()
_glv = _global_logic_variables

class Var(object):
    """ Logic Variable """

    _id = 1
    def __new__(cls, *token):
        if len(token) == 0:
            token = "_%s" % Var._id
            Var._id += 1
        elif len(token) == 1:
            token = token[0]

        obj = object.__new__(cls)
        obj.token = token
        return obj

    def __str__(self):
        return "~" + str(self.token)
    __repr__ = __str__

    def __eq__(self, other):
        return type(self) == type(other) and self.token == other.token

    def __hash__(self):
        return hash((type(self), self.token))

var = lambda *args: Var(*args)
vars = lambda n: [var() for i in range(n)]


@dispatch(Var)
def isvar(v):
    return True


@dispatch(object)
def isvar(o):
    return not not _glv and hashable(o) and o in _glv


@contextmanager
def variables(*variables):
    """ Context manager for logic variables

    >>> from __future__ import with_statement
    >>> from logpy import variables, var, isvar
    >>> with variables(1):
    ...     print(isvar(1))
    True

    >>> print(isvar(1))
    False

    Normal approach

    >>> from logpy import run, eq
    >>> x = var('x')
    >>> run(1, x, eq(x, 2))
    (2,)

    Context Manager approach
    >>> with variables('x'):
    ...     print(run(1, 'x', eq('x', 2)))
    (2,)
    """
    old_global_logic_variables = _global_logic_variables.copy()
    _global_logic_variables.update(set(variables))
    try:
        yield
    finally:
        _global_logic_variables.clear()
        _global_logic_variables.update(old_global_logic_variables)

########NEW FILE########
