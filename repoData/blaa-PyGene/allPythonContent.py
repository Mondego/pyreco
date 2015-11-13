__FILENAME__ = demo_case
#! /usr/bin/env python
"""
demo that tries to show one reason why genetic algorithms are successful.

It tries to crack open a suitcase with a few locks, each with 1-5
digits.  Fitness function can only determine that the lock is open, not
the progress of opening the lock (how much the lock is opened)

Genetic algorithm can keep partial results (e.g. 1 lock open) while
trying other locks.

In general each lock represents a partial solution to the problem
described by organism.
"""

import random
from time import time
import sys

from pygene.gene import IntGene, IntGeneRandom, IntGeneExchange
from pygene.organism import Organism, GenomeSplitOrganism
from pygene.population import Population

# Parameters
locks = 8
digits_in_lock = 3

# Generate codes
codes = []
for lock in range(locks):
    code = [random.randint(0, 9) for i in range(digits_in_lock)]
    codes.append(code)


class DigitCodeGene(IntGeneRandom):
    """
    a gene which holds a single digit, and can mutate into another digit.
    Mutation randomizes gene for IntGeneRandom class.
    """
    mutProb = 0.3
    # mutAmt = 2
    randMin = 0
    randMax = 9

    def __repr__(self):
        return str(self.value)

# generate a genome, one gene for each digit in suitcase
genome = {}
for l in range(locks):
    for d in range(digits_in_lock):
        key = '%d_%d' % (l, d)
        genome[key] = DigitCodeGene

# an organism that evolves towards the required string

class CodeHacker(GenomeSplitOrganism):

    chromosome_intersections = 2
    genome = genome

    def get_code(self, lock):
        "Decode the chromosome (genome) into code for specific lock"
        code = []
        for d in range(digits_in_lock):
            key = '%d_%d' % (lock, d)
            code.append(self[key])
        return code

    def fitness(self):
        "calculate fitness - number of locks opened by genome."
        opened_locks = 0
        for l in range(locks):
            code = self.get_code(l)
            if code == codes[l]:
                opened_locks += 1

        # The lower the better
        # add 0 - 0.5 to force randomization of organisms selection
        fitness = float(locks - opened_locks) #+ random.uniform(0, 0.5)
        return fitness

    def __repr__(self):
        "Display result nicely"
        s='<CodeHacker '
        for l in range(locks):
            code = self.get_code(l)
            code_str = "".join(str(i) for i in code)
            if code == codes[l]:
                s += " %s " % code_str # space - opened lock
            else:
                s += "(%s)" % code_str # () - closed lock
        s = s.strip() + ">"
        return s


class CodeHackerPopulation(Population):
    "Configuration of population"
    species = CodeHacker

    initPopulation = 500

    # Tips: Leave a space for mutants to live.

    # cull to this many children after each generation
    childCull = 600

    # number of children to create after each generation
    childCount = 500

    # Add this many mutated organisms.
    mutants = 1.0

    # Mutate organisms after mating (better results with False)
    mutateAfterMating = False

    numNewOrganisms = 0

    # Add X best parents into new population
    # Good configuration should in general work without an incest.
    # Incest can cover up too much mutation
    incest = 2


def main():

    # Display codes
    print "CODES TO BREAK:",
    for code in codes:
        print "".join(str(digit) for digit in code),
    print

    # Display some statistics
    combinations = 10**(locks * digits_in_lock)
    operations = 10000 * 10**6
    print "Theoretical number of combinations", combinations
    print "Optimistic operations per second:", operations
    print "Direct bruteforce time:", 1.0* combinations / operations / 60.0/60/24, "days"

    # Hack the case.
    started = time()

    # Create population
    ph = CodeHackerPopulation()

    i = 0
    while True:
        b = ph.best()
        print "generation %02d: %s best=%s average=%s)" % (
            i, repr(b), b.get_fitness(), ph.fitness())

        if b.get_fitness() < 1:
            #for org in ph:
            #    print "  ", org

            print "cracked in ", i, "generations and ", time() - started, "seconds"
            break

        sys.stdout.flush()
        i += 1
        ph.gen()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_config_genome
#! /usr/bin/env python

"""
Example build on the demo_quadratic.py - understand that one first!

Program reads it's genome configuration from a config file (quadratic.ini)

Example config file:
[x1]
type = float
randMin = -100.0
randMax = 100.0
mutProb = 0.1
mutAmt = 0.1

[x2]
type = int
randMin = -50
randMax = 50
mutProb = 0.2
mutAmt = 1

[x3]
alias = x2

[x4]
type = float
value = 5.4

One section per gene.
'type' is necessary - other fields depends on the selected type
possible types (for current list see pygene/config.py):
int, int_exchange, float, float_exchange, float_random, float_max, complex
You can create a genes from previously specified ones using 'alias' field.

There might be available a special section 'population' with parameters
for population. It's never treated as a gene.
"""

from pygene.gene import FloatGene, FloatGeneMax
from pygene.organism import Organism, MendelOrganism
from pygene.population import Population
from pygene.config import ConfigLoader

# parameters for quadratic equation
# has roots 3 and 5
if 1:
    a = 2
    b = -16
    c = 30
else:
    # this alternate set has only 1 root, x=4
    a = 2.0
    b = 3.0
    c = -44.0

def quad(x):
    return a * x ** 2 + b * x + c

loader = ConfigLoader(filename="quadratic.ini", require_genes=['x1', 'x2'])

class QuadraticSolver(Organism):
    """
    Implements the organism which tries
    to solve a quadratic equation
    """
    genome = loader.load_genome()

    def fitness(self):
        """
        Implements the 'fitness function' for this species.
        Organisms try to evolve to minimise this function's value
        """
        x1 = self['x1']
        x2 = self['x2']

        # this formula punishes for roots being wrong, also for
        # roots being the same
        badness_x1 = abs(quad(x1)) # punish for incorrect first root
        badness_x2 = abs(quad(x2)) # punish for incorrect second root
        badness_equalroots = 1.0 / (abs(x1 - x2)) # punish for equal roots
        return badness_x1 + badness_x2 + badness_equalroots

    def __repr__(self):
        return "<fitness=%f x1=%s x2=%s>" % (
            self.fitness(), self['x1'], self['x2'])


QPopulation = loader.load_population("QPopulation", species=QuadraticSolver)

"""
class QPopulation(Population):

    species = QuadraticSolver
    initPopulation = 20

    # cull to this many children after each generation
    childCull = 20

    # number of children to create after each generation
    childCount = 50

    mutants = 0.5

# create a new population, with randomly created members
"""

pop = QPopulation()


# now a func to run the population
def main():
    from time import time
    s = time()
    try:
        generations = 0
        while True:
            # execute a generation
            pop.gen()
            generations += 1

            # and dump it out
            #print [("%.2f %.2f" % (o['x1'], o['x2'])) for o in pop.organisms]
            best = pop.organisms[0]
            print "fitness=%f avg=%f x1=%f x2=%f" % (best.get_fitness(), pop.fitness(),
                                                     best['x1'], best['x2'])
            if best.get_fitness() < 0.6:
                break

    except KeyboardInterrupt:
        pass
    print "Executed", generations, "generations in", time() - s, "seconds"


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = demo_converge
#! /usr/bin/env python

"""
Very simple demo in which organisms try to minimise
the output value of a function
"""

from pygene.gene import FloatGene, FloatGeneMax
from pygene.organism import Organism, MendelOrganism
from pygene.population import Population

class CvGene(FloatGeneMax):
    """
    Gene which represents the numbers used in our organism
    """
    # genes get randomly generated within this range
    randMin = -100.0
    randMax = 100.0
    
    # probability of mutation
    mutProb = 0.1
    
    # degree of mutation
    mutAmt = 0.1


class Converger(MendelOrganism):
    """
    Implements the organism which tries
    to converge a function
    """
    genome = {'x':CvGene, 'y':CvGene}
    
    def fitness(self):
        """
        Implements the 'fitness function' for this species.
        Organisms try to evolve to minimise this function's value
        """
        return self['x'] ** 2 + self['y'] ** 2

    def __repr__(self):
        return "<Converger fitness=%f x=%s y=%s>" % (
            self.fitness(), self['x'], self['y'])


# create an empty population

pop = Population(species=Converger, init=2, childCount=50, childCull=20)


# now a func to run the population

def main():
    try:
        while True:
            # execute a generation
            pop.gen()

            # get the fittest member
            best = pop.best()
            
            # and dump it out
            print best

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = demo_fractal
#! /usr/bin/env python

"""
experiment in using fractals to fit a set of values

may or may not work
"""

import math

from pygene.gene import FloatGene, ComplexGene
from pygene.gene import IntGene, OrBitGene, rndPair
from pygene.organism import Organism
from pygene.population import Population

# data set to model

targetData = [432, 444, 520, 419, 450, 540, 625]
targetDataLen = len(targetData)

# gene classes for fractals

class OrgGene(ComplexGene):
    """
    gene to use for initial value
    """
    mutProb = 0.03
    mutAmt = 0.5

    randMin = -2.0
    randMax = 2.0

class DeltaGene(ComplexGene):
    """
    gene to use for motion
    """
    mutProb = 0.03
    mutAmt = 1.0

    rndMin = -0.4
    rndMax = 0.4


class IterationsGene(IntGene):
    """
    gene that controls number of mandelbrot iterations
    """
    mutProb = 0.001
    randMin = 2
    randMax = 10

# utility func - standard deviation

def sdev(dataset):
    
    n = float(len(dataset))
    mean = sum(dataset) / n
    devs = [(x - mean) ** 2 for x in dataset]
    sd = math.sqrt(sum(devs) / n)
    return mean, sd
    
# organism class

class FracOrganism(Organism):
    """
    organism class
    """
    genome = {
        'init':OrgGene,
        'delta':DeltaGene,
        'iterations':IterationsGene,
        }

    maxIterations = 100

    def fitness(self):
        """
        fitness is the standard deviation of the ratio of
        each generated value to each target value
        """
        guessData = self.getDataSet()
        badness = 0.0
        ratios = [100000.0 * guessData[i] / targetData[i] \
            for i in xrange(targetDataLen)]
        try:
            sd, mean = sdev(ratios)
            var = sd / mean
            badness = var, sd, mean
        except:
            #raise
            badness = 10000.0, None, None
        return badness
        
    def getDataSet(self):
        """
        computes the data set resulting from genes
        """
        guessData = []
        org = self['init']
        delta = self['delta']
        niterations = self['iterations']
        for i in xrange(targetDataLen):
            #guessData.append(self.mand(org, niterations))
            guessData.append(self.mand(org))
            org += delta
        return guessData
    
    def mand_old(self, org, niterations):
        """
        performs the mandelbrot calculation on point org for
        niterations generations,
        returns final magnitude
        """
        c = complex(0,0)
        
        for i in xrange(niterations):
            c = c * c + org
        
        return abs(c)

    def mand(self, org):
        """
        returns the number of iterations needed for abs(org)
        to exceed 1.0
        """
        i = 0
        c = complex(0,0)
        while i < self.maxIterations:
            if abs(c) > 1.0:
                break
            c = c * c + org
            i += 1
        return i
            
def newOrganism(self=None):

    return FracOrganism(
        init=OrgGene,
        delta=DeltaGene,
        iterations=IterationsGene,
        )

class FracPopulation(Population):

    species = FracOrganism
    initPopulation = 100

    # cull to this many children after each generation
    childCull = 6

    # number of children to create after each generation
    childCount = 30

    # enable addition of random new organisms
    newOrganism = newOrganism
    numNewOrganisms = 5

    # keep best 5 parents    
    incest = 5


# create an initial random population

pop = FracPopulation()


# now a func to run the population
def main():
    try:
        while True:
            # execute a generation
            pop.gen()

            # and dump it out
            #print [("%.2f %.2f" % (o['x1'], o['x2'])) for o in pop.organisms]
            best = pop.organisms[0]
            print "fitness=%s" % (best.fitness(),)

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = demo_multiprocessing
#! /usr/bin/env python
"""
Parallel fitness calculation using the Python multiprocessing library.

Based on demo_string.py, but using a pool of 4 worker processes to do the fitness calculation.

Note: the fitness calculation for this GA problem is not very computationally expensive,
so the worker processes don't look very busy. However, if you add some extra CPU-intensive calculations
to the calculate_fitness() function, you'll notice the difference.

"""

from multiprocessing import Pool

from pygene.gene import FloatGene, FloatGeneMax
from pygene.gamete import Gamete
from pygene.organism import Organism
from pygene.population import Population


# Fitness function - global and unbound, for multiprocessing to be able to Pickle it
def calculate_fitness(guess, numgenes):
	diffs = 0.0
	for i in xrange(numgenes):
		x0 = teststrNums[i]
		x1 = ord(guess[i])
		diffs += (x1 - x0) ** 2
	return diffs

# this is the string that our organisms
# are trying to evolve into
teststr = "hackthis"

# convert the string into a list of floats, where
# each float is the ascii value of the corresponding
# char

teststrNums = [float(ord(c)) for c in teststr]

# derive a gene which holds a character, and can
# mutate into another character

class HackerGene(FloatGeneMax):
    
    mutProb = 0.1
    mutAmt = 0.2
    
    randMin = 0x0
    randMax = 0xff

    def __repr__(self):

        return str(chr(int(self.value)))

# generate a genome, one gene for each char in the string
genome = {}
for i in range(len(teststr)):
    genome[str(i)] = HackerGene

# an organism that evolves towards the required string

class StringHacker(Organism):
    
    genome = genome

    def __repr__(self):
        """
        Return the gene values as a string
        """
        chars = []
        for i in xrange(self.numgenes):

            #x = self[str(i)]
            #print "x=%s" % repr(x)
    
            c = chr(int(self[str(i)]))
            chars.append(c)

        return str(''.join(chars))

    # submit fitness calculation to worker process
    def prepare_fitness(self):
    	self.result = pool.apply_async(calculate_fitness, [str(self), self.numgenes])

    # block until result is ready, and retrieve it
    def fitness(self):
        return self.result.get()

class StringHackerPopulation(Population):

    initPopulation = 10
    species = StringHacker
    
    # cull to this many children after each generation
    childCull = 10
    
    # number of children to create after each generation
    childCount = 50
    
    mutants = 0.25

# start with a population of 10 random organisms
ph = StringHackerPopulation()

def main(nfittest=10, nkids=100):
    i = 0
    while True:
        b = ph.best()
        print "generation %s: %s best=%s average=%s)" % (
            i, repr(b), b.get_fitness(), ph.fitness())
        if b.get_fitness() <= 0:
            print "cracked!"
            break
        i += 1
        ph.gen()


if __name__ == '__main__':
	# create a pool of 4 worker processes (has to be declared below 'if __name....')
	pool = Pool(processes=4)

	# execute main loop
	main()

########NEW FILE########
__FILENAME__ = demo_parallel
#! /usr/bin/env python
"""
Parallel fitness calculation demo based on demo_string_char.py.
Instead of threads this could be written using Celery.

Execution time of 11 generations with 10 threads: 2.9s
With 1 thread: 12.1s
(Keep in mind that fitness here simulates processing with sleep)
"""

from pygene.gene import PrintableCharGene
from pygene.gamete import Gamete
from pygene.organism import Organism, MendelOrganism
from pygene.population import Population

from time import sleep
import threading
import Queue

# The same as in demo_string_char
teststr = "hackthis"
teststrlen = len(teststr)
geneNames = []
for i in range(len(teststr)):
    geneNames.append("%s" % i)

class HackerGene(PrintableCharGene):
    mutProb = 0.1
    mutAmt = 2

genome = {}
for i in range(len(teststr)):
    genome[str(i)] = HackerGene


##
# Worker thread / threads
##

threads_cnt = 15

# Global task queue
queue = Queue.Queue()

# Worker thread
class Worker(threading.Thread):

    def __init__(self, queue):
        super(Worker, self).__init__()
        self.queue = queue

    def fitness(self, string):
        diffs = 0
        guess = string
        # Simulate a lot of processing
        sleep(0.01)
        for i in xrange(len(teststr)):
            x0 = ord(teststr[i])
            x1 = ord(string[i])
            diffs += (2 * (x1 - x0)) ** 2
        return diffs

    def run(self):
        while True:
            task = self.queue.get()
            string, result_dict = task
            fitness = self.fitness(string)
            result_dict['fitness'] = fitness
            self.queue.task_done()

# Start threads
threads = []
for i in range(threads_cnt):
    worker = Worker(queue)
    worker.setDaemon(True)
    worker.start()
    threads.append(worker)


class StringHacker(MendelOrganism):
    genome = genome

    def __repr__(self):
        """
        Return the gene values as a string
        """
        chars = []
        for k in xrange(self.numgenes):
            c = self[str(k)]
            chars.append(c)
        return ''.join(chars)

    def prepare_fitness(self):
        """
        Here we request fitness calculation.  Prepare place for result
        and put our string into a queue.  A running worker-thread will
        pick it up from the queue and calculate.
        """
        self.result_dict = {}
        queue.put((str(self), self.result_dict))

    def fitness(self):
        # Wait until all organisms in this population have it's fitness calculated
        # Could wait only for it's fitness but it's more complicated...
        queue.join()
        return self.result_dict['fitness']

class StringHackerPopulation(Population):

    initPopulation = 10
    species = StringHacker

    # cull to this many children after each generation
    childCull = 10

    # number of children to create after each generation
    childCount = 40

# start with a population of 10 random organisms
ph = StringHackerPopulation()

def main(nfittest=10, nkids=100):
    i = 0
    while True:
        b = ph.best()
        print "generation %s: %s best=%s average=%s)" % (
            i, str(b), b.get_fitness(), ph.fitness())
        if b.get_fitness() <= 0:
            print "cracked!"
            break
        i += 1
        ph.gen()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_prog
#! /usr/bin/env python

"""
Demo of genetic programming

This gp setup seeks to breed an organism which
implements func x^2 + y

Takes an average of about 40 generations
to breed a matching program
"""

import math
from random import random, uniform
from pygene.prog import ProgOrganism
from pygene.population import Population

# a tiny batch of functions
def add(x,y):
    #print "add: x=%s y=%s" % (repr(x), repr(y))
    try:
        return x+y
    except:
        #raise
        return x

def sub(x,y):
    #print "sub: x=%s y=%s" % (repr(x), repr(y))
    try:
        return x-y
    except:
        #raise
        return x

def mul(x,y):
    #print "mul: x=%s y=%s" % (repr(x), repr(y))
    try:
        return x*y
    except:
        #raise
        return x

def div(x,y):
    #print "div: x=%s y=%s" % (repr(x), repr(y))
    try:
        return x / y
    except:
        #raise
        return x

def sqrt(x):
    #print "sqrt: x=%s" % repr(x)
    try:
        return math.sqrt(x)
    except:
        #raise
        return x

def pow(x,y):
    #print "pow: x=%s y=%s" % (repr(x), repr(y))
    try:
        return x ** y
    except:
        #raise
        return x

def log(x):
    #print "log: x=%s" % repr(x)
    try:
        return math.log(float(x))
    except:
        #raise
        return x

def sin(x):
    #print "sin: x=%s" % repr(x)
    try:
        return math.sin(float(x))
    except:
        #raise
        return x

def cos(x):
    #print "cos: x=%s" % repr(x)
    try:
        return math.cos(float(x))
    except:
        #raise
        return x

def tan(x):
    #print "tan: x=%s" % repr(x)
    try:
        return math.tan(float(x))
    except:
        #raise
        return x

# define the class comprising the program organism
class MyProg(ProgOrganism):
    """
    """
    funcs = {
        '+': add,
#        '-':sub,
        '*': mul,
#        '/':div,
#        '**': pow,
#        'sqrt': sqrt,
#        'log' : log,
#        'sin' : sin,
#        'cos' : cos,
#        'tan' : tan,
        }
    vars = ['x', 'y']
    consts = [0.0, 1.0, 2.0, 10.0]

    testVals = [{'x':uniform(-10.0, 10.0),
                 'y':uniform(-10.0, 10.0),
                 } for i in xrange(20)
                ]

    mutProb = 0.4

    def testFunc(self, **vars):
        """
        Just wanting to model x^2 + y
        """
        return vars['x'] ** 2 + vars['y']

    def fitness(self):
        # choose 10 random values
        badness = 0.0
        try:
            for vars in self.testVals:
                badness += (self.calc(**vars) - self.testFunc(**vars)) ** 2
            return badness
        except OverflowError:
            return 1.0e+255 # infinitely bad

    # maximum tree depth when generating randomly
    initDepth = 6


class ProgPop(Population):
    u"Population class for the experiment"
    species = MyProg
    initPopulation = 10

    # cull to this many children after each generation
    childCull = 20

    # number of children to create after each generation
    childCount = 20

    mutants = 0.3

def graph(orig, best):
    "Graph on -10, 10 ranges"
    print "ORIG                                  BEST:"
    for y in range(10, -11, -2):
        for x in range(-10, 11, 3):
            z = orig(x=float(x), y=float(y))
            print "%03.0f " % z,

        print "  ",
        for x in range(-10, 11, 3):
            z = best(x=float(x), y=float(y))
            print "%03.0f " % z,
        print


def main(nfittest=10, nkids=100):

    pop = ProgPop()

    ngens = 0
    i = 0
    while True:
        b = pop.best()
        print "Generation %s: %s best=%s average=%s)" % (
            i, str(b), b.fitness(), pop.fitness())
        b.dump()

        graph(b.testFunc, b.calc)

        if b.fitness() <= 0:
            print "cracked!"
            break
        i += 1
        ngens += 1

        if ngens < 100:
            pop.gen()
        else:
            print "failed after 100 generations, restarting"
            pop = ProgPop()
            ngens = 0

if __name__ == '__main__':
    main()
    pass

########NEW FILE########
__FILENAME__ = demo_quadratic
#! /usr/bin/env python

"""
Very simple demo in which organisms try to minimise
the output value of a function
"""

from pygene.gene import FloatGene, FloatGeneMax
from pygene.organism import Organism, MendelOrganism
from pygene.population import Population

# parameters for quadratic equation
# has roots 3 and 5
a = 2
b = -16
c = 30

if 0:
    # this alternate set has only 1 root, x=4
    a = 2.0
    b = 3.0
    c = -44.0

class XGene(FloatGene):
    """
    Gene which represents the numbers used in our organism
    """
    # genes get randomly generated within this range
    randMin = -100.0
    randMax = 100.0
    
    # probability of mutation
    mutProb = 0.1
    
    # degree of mutation
    mutAmt = 0.1

def quad(x):
    return a * x ** 2 + b * x + c

class QuadraticSolver(Organism):
    """
    Implements the organism which tries
    to solve a quadratic equation
    """
    genome = {'x1':XGene, 'x2':XGene}
    
    def fitness(self):
        """
        Implements the 'fitness function' for this species.
        Organisms try to evolve to minimise this function's value
        """
        x1 = self['x1']
        x2 = self['x2']
        
        # this formula punishes for roots being wrong, also for
        # roots being the same
        badness_x1 = abs(quad(x1)) # punish for incorrect first root
        badness_x2 = abs(quad(x2)) # punish for incorrect second root
        badness_equalroots = 1.0 / (abs(x1 - x2)) # punish for equal roots
        return badness_x1 + badness_x2 + badness_equalroots

    def __repr__(self):
        return "<fitness=%f x1=%s x2=%s>" % (
            self.fitness(), self['x1'], self['x2'])


class QPopulation(Population):

    species = QuadraticSolver
    initPopulation = 2
    
    # cull to this many children after each generation
    childCull = 5

    # number of children to create after each generation
    childCount = 50


# create a new population, with randomly created members

pop = QPopulation()


# now a func to run the population
def main():
    try:
        generations = 0
        while True:
            # execute a generation
            pop.gen()
            generations += 1

            # and dump it out
            #print [("%.2f %.2f" % (o['x1'], o['x2'])) for o in pop.organisms]
            best = pop.organisms[0]
            print "fitness=%f x1=%f x2=%f" % (best.get_fitness(), best['x1'], best['x2'])
            if best.get_fitness() < 0.6:
                break

    except KeyboardInterrupt:
        pass
    print "Executed", generations, "generations"


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = demo_salesman
#! /usr/bin/env python
"""
Implementation of the travelling salesman problem (TSP)
"""

from random import random
from math import sqrt

from pygene.gene import FloatGene, FloatGeneMax, FloatGeneRandom
from pygene.organism import Organism, MendelOrganism
from pygene.population import Population

width = 500
height = 500

# set the number of cities in our tour
numCities = 30

# tweak these to gen varying levels of performance

geneRandMin = 0.0
geneRandMax = 10.0
geneMutProb = 0.1
geneMutAmt = .5         # only if not using FloatGeneRandom

popInitSize = 10
popChildCull = 30
popChildCount = 200
popIncest = 10           # number of best parents to add to children
popNumMutants = 0.7     # proportion of mutants each generation
popNumRandomOrganisms = 0  # number of random organisms per generation

mutateOneOnly = False

BaseGeneClass = FloatGene
BaseGeneClass = FloatGeneMax
#BaseGeneClass = FloatGeneRandom

OrganismClass = MendelOrganism
#OrganismClass = Organism

mutateAfterMating = True

crossoverRate = 0.05

class CityPriorityGene(BaseGeneClass):
    """
    Each gene in the TSP solver represents the priority
    of travel to the corresponding city
    """
    randMin = geneRandMin
    randMax = geneRandMax

    mutProb = geneMutProb
    mutAmt = geneMutAmt

class City:
    """
    represents a city by name and location,
    and calculates distance from another city
    """
    def __init__(self, name, x=None, y=None):
        """
        Create city by name, randomly generating
        its co-ordinates if none given
        """
        self.name = name

        # constrain city coords so they're no closer than 50 pixels
        # to any edge, so the city names show up ok in the gui version
        if x == None:
            x = random() * (width - 100) + 50
        if y == None:
            y = random() * (height - 100) + 50

        self.x = x
        self.y = y

    def __sub__(self, other):
        """
        compute distance between this and another city
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return sqrt(dx * dx + dy * dy)

    def __repr__(self):
        return "<City %s at (%.2f, %.2f)>" % (self.name, self.x, self.y)

if 0:
    cities = [
        City("Sydney"),
        City("Melbourne"),
        City("Brisbane"),
        City("Armidale"),
        City("Woolongong"),
        City("Newcastle"),
        City("Cairns"),
        City("Darwin"),
        City("Perth"),
        City("Townsville"),
        City("Bourke"),
        City("Gosford"),
        City("Coffs Harbour"),
        City("Tamworth"),
        ]

if 1:
    cities = []
    for i in xrange(numCities):
        cities.append(City("%s" % i))

cityNames = [city.name for city in cities]

cityCount = len(cities)

cityDict = {}
for city in cities:
    cityDict[city.name] = city

priInterval = (geneRandMax - geneRandMin) / cityCount
priNormal = []
for i in xrange(cityCount):
    priNormal.append(((i+0.25)*priInterval, (i+0.75)*priInterval))

genome = {}
for name in cityNames:
    genome[name] = CityPriorityGene

class TSPSolution(OrganismClass):
    """
    Organism which represents a solution to
    the TSP
    """
    genome = genome

    mutateOneOnly = mutateOneOnly

    crossoverRate = crossoverRate

    numMutants = 0.3

    def fitness(self):
        """
        return the journey distance
        """
        distance = 0.0

        # get the city objects in order of priority
        sortedCities = self.getCitiesInOrder()

        # start at first city, compute distances to last
        for i in xrange(cityCount - 1):
            distance += sortedCities[i] - sortedCities[i+1]

        # and add in the return trip
        distance += sortedCities[0] - sortedCities[-1]

        # done
        return distance

    def getCitiesInOrder(self):
        """
        return a list of the cities, sorted in order
        of the respective priority values in this
        organism's genotype
        """
        # create a sortable list of (priority, city) tuples
        # (note that 'self[name]' extracts the city gene's phenotype,
        # being the 'priority' of that city
        sorter = [(self[name], cityDict[name]) for name in cityNames]

        # now sort them, the priority elem will determine order
        sorter.sort()

        # now extract the city objects
        sortedCities = [tup[1] for tup in sorter]

        # done
        return sortedCities

    def normalise(self):
        """
        modifies the genes to a reasonably even spacing
        """
        genes = self.genes
        for i in xrange(2):
            sorter = [(genes[name][i], name) for name in cityNames]
            sorter.sort()
            sortedGenes = [tup[1] for tup in sorter]




class TSPSolutionPopulation(Population):

    initPopulation = popInitSize
    species = TSPSolution

    # cull to this many children after each generation
    childCull = popChildCull

    # number of children to create after each generation
    childCount = popChildCount

    # number of best parents to add in with next gen
    incest = popIncest

    mutants = popNumMutants

    numNewOrganisms = popNumRandomOrganisms

    mutateAfterMating = mutateAfterMating

def main():
    from time import time
    s = time()
    # create initial population
    pop = TSPSolutionPopulation()

    # now repeatedly calculate generations
    i = 0

    try:
        while True:
            print "gen=%s best=%s avg=%s" % (i, pop.best().get_fitness(), pop.fitness())
            pop.gen()
            i += 1
    except KeyboardInterrupt:
        print


    # get the best solution
    solution = pop.best()

    # and print out the itinerary
    sortedCities = solution.getCitiesInOrder()
    print "Best solution: total distance %04.2f in %.3f seconds:" % (
        solution.fitness(), time() - s)
    for city in sortedCities:
        print "  x=%03.2f y=%03.2f %s" % (city.x, city.y, city.name)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_salesman_gui
#! /usr/bin/env python

"""
Alternative implementation of travelling salesman problem
that displays solutions in a graphical window, using the
pyFLTK widgets (http://pyfltk.sourceforge.net)
"""

try:
    from fltk import *
except ImportError:
    print "This demo requires fltk installed in order to work!"
    import sys
    sys.exit(1)

try:
    import psyco
except ImportError:
    psyco = None 

from threading import Lock
from thread import start_new_thread
from time import sleep

from random import random
from math import sqrt

from pygene.gene import FloatGene, FloatGeneMax, FloatGeneRandom
from pygene.organism import Organism, MendelOrganism
from pygene.population import Population

width = 500
height = 500

# set the number of cities in our tour
numCities = 30

# tweak these to gen varying levels of performance

geneRandMin = 0.0
geneRandMax = 10.0
geneMutProb = 0.1
geneMutAmt = .5         # only if not using FloatGeneRandom

popInitSize = 10
popChildCull = 20
popChildCount = 100
popIncest = 10           # number of best parents to add to children
popNumMutants = 0.7     # proportion of mutants each generation
popNumRandomOrganisms = 0  # number of random organisms per generation

mutateOneOnly = False

BaseGeneClass = FloatGene
BaseGeneClass = FloatGeneMax
#BaseGeneClass = FloatGeneRandom

OrganismClass = MendelOrganism
#OrganismClass = Organism

mutateAfterMating = True

crossoverRate = 0.05

class CityPriorityGene(BaseGeneClass):
    """
    Each gene in the TSP solver represents the priority
    of travel to the corresponding city
    """
    randMin = geneRandMin
    randMax = geneRandMax
    
    mutProb = geneMutProb
    mutAmt = geneMutAmt

class City:
    """
    represents a city by name and location,
    and calculates distance from another city
    """
    def __init__(self, name, x=None, y=None):
        """
        Create city by name, randomly generating
        its co-ordinates if none given
        """
        self.name = name

        # constrain city coords so they're no closer than 50 pixels
        # to any edge, so the city names show up ok in the gui version        
        if x == None:
            x = random() * (width - 100) + 50
        if y == None:
            y = random() * (height - 100) + 50
            
        self.x = x
        self.y = y
    
    def __sub__(self, other):
        """
        compute distance between this and another city
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return sqrt(dx * dx + dy * dy)

    def __repr__(self):
        return "<City %s at (%.2f, %.2f)>" % (self.name, self.x, self.y)

if 0:
    cities = [
        City("Sydney"),
        City("Melbourne"),
        City("Brisbane"),
        City("Armidale"),
        City("Woolongong"),
        City("Newcastle"),
        City("Cairns"),
        City("Darwin"),
        City("Perth"),
        City("Townsville"),
        City("Bourke"),
        City("Gosford"),
        City("Coffs Harbour"),
        City("Tamworth"),
        ]

if 1:
    cities = []
    for i in xrange(numCities):
        cities.append(City("%s" % i))

cityNames = [city.name for city in cities]

cityCount = len(cities)

cityDict = {}
for city in cities:
    cityDict[city.name] = city

priInterval = (geneRandMax - geneRandMin) / cityCount
priNormal = []
for i in xrange(cityCount):
    priNormal.append(((i+0.25)*priInterval, (i+0.75)*priInterval))

genome = {}
for name in cityNames:
    genome[name] = CityPriorityGene

class TSPSolution(OrganismClass):
    """
    Organism which represents a solution to
    the TSP
    """
    genome = genome
    
    mutateOneOnly = mutateOneOnly

    crossoverRate = crossoverRate

    numMutants = 0.3

    def fitness(self):
        """
        return the journey distance
        """
        distance = 0.0

        # get the city objects in order of priority
        sortedCities = self.getCitiesInOrder()

        # start at first city, compute distances to last
        for i in xrange(cityCount - 1):
            distance += sortedCities[i] - sortedCities[i+1]
        
        # and add in the return trip
        distance += sortedCities[0] - sortedCities[-1]

        # done
        return distance

    def getCitiesInOrder(self):
        """
        return a list of the cities, sorted in order
        of the respective priority values in this
        organism's genotype
        """
        # create a sortable list of (priority, city) tuples
        # (note that 'self[name]' extracts the city gene's phenotype,
        # being the 'priority' of that city
        sorter = [(self[name], cityDict[name]) for name in cityNames]

        # now sort them, the priority elem will determine order
        sorter.sort()
        
        # now extract the city objects
        sortedCities = [tup[1] for tup in sorter]

        # done
        return sortedCities

    def normalise(self):
        """
        modifies the genes to a reasonably even spacing
        """
        genes = self.genes
        for i in xrange(2):
            sorter = [(genes[name][i], name) for name in cityNames]
            sorter.sort()
            sortedGenes = [tup[1] for tup in sorter]
            
            


class TSPSolutionPopulation(Population):

    initPopulation = popInitSize
    species = TSPSolution
    
    # cull to this many children after each generation
    childCull = popChildCull
    
    # number of children to create after each generation
    childCount = popChildCount
    
    # number of best parents to add in with next gen
    incest = popIncest

    mutants = popNumMutants

    numNewOrganisms = popNumRandomOrganisms

    mutateAfterMating = mutateAfterMating

class TSPCanvas(Fl_Box):
    """
    Implements a custom version of box that draws the
    cities and journey
    """
    def __init__(self, gui, x, y, w, h):
        
        Fl_Box.__init__(self, x, y, w, h)
    
        # style the widget
        self.box(FL_DOWN_BOX)
        self.color(FL_WHITE)
    
        # save needed attribs
        self.gui = gui
        self.pop = gui.pop
    
        # best fitness so far
        self.bestSoFar = 10000000000000000000
    
    def draw(self):
        
        Fl_Box.draw(self)
        
        # now, show the cities and plot their journey
        self.showJourney()
    
    def showJourney(self, *ev):
        """
        Periodically display the best solution
        """
        self.gui.lock.acquire()
    
        # get the best
        best = self.gui.best
    
        fitness = self.gui.fitness
    
        # get the cities in order
        order = best.getCitiesInOrder()
    
        print "best=%s" % fitness
    
        # draw the city names
        fl_color(FL_BLACK)
        fl_font(FL_HELVETICA, 16)
        for city in order:
            fl_draw(city.name, int(city.x), int(city.y))    
    
        # choose a colour according to whether we're improving, staying the same,
        # or getting worse
        if fitness < self.bestSoFar:
            fl_color(FL_GREEN)
            self.bestSoFar = fitness
        elif fitness == self.bestSoFar:
            # equal best - plot in blue
            fl_color(FL_BLUE)
        else:
            # worse - plot in red
            fl_color(FL_RED)
    
        # now draw the journey
        for i in xrange(len(order)-1):
            city0, city1 = order[i:i+2]
            fl_line(int(city0.x), int(city0.y), int(city1.x), int(city1.y))
    
        # and don't forget the journey back home
        fl_line(int(order[0].x), int(order[0].y), int(order[-1].x), int(order[-1].y))
    
        self.gui.lock.release()
    

class TSPGui:
    """
    displays solutions graphically as we go
    """
    x = 100
    y = 100
    w = width + 10
    h = height + 50
    
    updatePeriod = 0.1
    
    def __init__(self):
        """
        Creates the graphical interface
        """
        # initial empty population
        self.pop = TSPSolutionPopulation()
        self.best = self.pop.best()
        self.updated = True
    
        # lock for drawing
        self.lock = Lock()
    
        # build the gui
        self.win = Fl_Window(
            self.x, self.y,
            self.w, self.h,
            "pygene Travelling Salesman solver")
        
        self.xdraw = 5
        self.ydraw = 5
        self.wdraw = self.w - 10
        self.hdraw = self.h - 90
    
        # bring in our custom canvas
        self.draw_canvas = TSPCanvas(
            self,
            self.xdraw, self.ydraw,
            self.wdraw, self.hdraw,
            )
    
        # add in some fields
        self.fld_numgen = Fl_Output(120, self.h-84, 50, 20, "Generations: ")
        self.fld_numimp = Fl_Output(320, self.h-84, 50, 20, "Improvements: ")
    
        # add a chart widget
        self.chart = Fl_Chart(5, self.h - 60, self.w - 10, 60)
        self.chart.color(FL_WHITE)
        self.chart.type(FL_LINE_CHART)
        self.win.end()
    
        # this flag allows for original generation to be displayed
        self.firsttime = True
        self.fitness = self.pop.best().fitness()
    
        self.ngens = 0
        self.nimp = 0
        self.bestFitness = 9999999999999999999
        
    def run(self):
        """
        Runs the population
        """
        # put up the window
        self.win.show()
    
        # start the background thread
        start_new_thread(self.threadUpdate, ())
    
        # schedule periodical updates
        Fl.add_idle(self.update)
    
        # hit the event loop
        Fl.run()
    
    def update(self, *args):
        """
        checks for updates
        """
        # and let the thread run
        sleep(0.0001)
    
        if self.updated:
    
            self.lock.acquire()
    
            # now draw the current state
            self.draw_canvas.redraw()    
            
            # plot progress on graph
            self.chart.add(self.fitness)
            
            # update status fields
            self.ngens += 1
            self.fld_numgen.value(str(self.ngens))
                
            if self.fitness < self.bestFitness:
                self.nimp += 1
                self.fld_numimp.value(str(self.nimp))
                self.bestFitness = self.fitness
    
            self.updated = False
            
            self.lock.release()
    
    def threadUpdate(self):
        """
        create and display generation
        """
        print "threadUpdate starting"
    
        while True:
    
            self.pop.gen()
    
            #print "generated"
    
            self.lock.acquire()
    
            self.best = self.pop.best()
            self.fitness = self.best.fitness()
            self.updated = True
    
            self.lock.release()
    

def main():

    # build and run the gui    
    gui = TSPGui()

    if psyco:
        print "Starting psyco"
        psyco.full()

    gui.run()

if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = demo_string
#! /usr/bin/env python
"""
demo that cracks a secret string.

the feedback is how 'close' an organism's string
is to the target string, based on the sum of the
squares of the differences in the respective chars

Compare this demo to demo_case.py - similar demo where
ordering/grouping of genes has a meaning.
"""
from pygene.gene import CharGeneExchange
from pygene.organism import Organism
from pygene.population import Population

# this is the string that our organisms
# are trying to evolve into
teststr = "hackthis"

class HackerGene(CharGeneExchange):
    """
    a gene which holds a character, and can mutate into another character
    """
    mutProb = 0.1
    mutAmt = (ord('z') - ord('a')) / 2

    def __repr__(self):
        return self.value

# generate a genome, one gene for each char in the string
# { '0': Gene, '1': Gene2... }
genome = {}
for i in range(len(teststr)):
    genome[str(i)] = HackerGene

# an organism that evolves towards the required string

class StringHacker(Organism):

    # set organism genome
    genome = genome

    def __repr__(self):
        """
        Return the gene values as a string
        """
        chars = [self[str(i)] for i in range(self.numgenes)]
        return str(''.join(chars))

    def fitness(self):
        """
        calculate fitness, as the sum of the squares
        of the distance of each char gene from the
        corresponding char of the target string
        """
        # Get our value as a string
        guess = str(self)

        # Calculate difference
        diffs = 0
        for x0, x1 in zip(teststr, guess):
            diffs += (ord(x1) - ord(x0)) ** 2
        return diffs


class StringHackerPopulation(Population):
    # set population species
    species = StringHacker

    # Number of initial random organisms
    initPopulation = 10

    # cull to this many children after each generation
    childCull = 10

    # number of children to create after each generation
    childCount = 100

    mutants = 0.25


def main():
    from time import time

    # start with a population of random organisms
    world = StringHackerPopulation()

    i = 0
    started = time()
    while True:
        b = world.best()
        print "generation %02d: %s best=%s average=%s)" % (
            i, repr(b), b.get_fitness(), world.fitness())
        if b.get_fitness() <= 0:
            print "cracked in ", i, "generations and ", time() - started, "seconds"
            break
        i += 1
        world.gen()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_string_int
#! /usr/bin/env python
"""
another demo that cracks a secret string

This one uses the discrete int gene
"""

from pygene.gene import FloatGene, IntGene, rndPair
from pygene.gamete import Gamete
from pygene.organism import Organism 
from pygene.population import Population

# this is the string that our organisms
# are trying to evolve into
teststr = "hackthis"

# convert the string into a list of ints, where
# each int is the ascii value of the corresponding
# char

teststrNums = [ord(c) for c in teststr]

# derive a gene which holds a character, and can
# mutate into another character

class HackerGene(IntGene):
    
    mutProb = 0.1
    mutAmt = 10
    
    randMin = 0
    randMax = 255

# generate a genome, one gene for each char in the string
genome = {}
for i in range(len(teststr)):
    genome[str(i)] = HackerGene

# an organism that evolves towards the required string

class StringHacker(Organism):
    
    genome = genome

    def __repr__(self):
        """
        Return the gene values as a string
        """
        chars = []
        for k in xrange(self.numgenes):

            n = self[str(k)]
            #print "n=%s" % repr(n)
            c = str(chr(n))

            chars.append(c)

        return ''.join(chars)

    def fitness(self):
        """
        calculate fitness, as the sum of the squares
        of the distance of each char gene from the
        corresponding char of the target string
        """
        diffs = 0.0
        guess = str(self)
        for i in xrange(self.numgenes):
            x0 = teststrNums[i]
            x1 = ord(guess[i])
            diffs += (x1 - x0) ** 2
        return diffs

class StringHackerPopulation(Population):
 
    # Population species
    species = StringHacker

    # start with a population of 10 random organisms
    initPopulation = 10
    
    # cull to this many children after each generation
    childCull = 10
    
    # number of children to create after each generation
    childCount = 50
    

def main():
    # Create initial population
    world = StringHackerPopulation()

    # Iterate over generations
    i = 0
    while True:
        b = world.best()
        print "generation %s: %s best=%s average=%s)" % (
            i, repr(b), b.get_fitness(), world.fitness())
        if b.get_fitness() <= 0:
            print "cracked!"
            break
        i += 1
        world.gen()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_typed_prog
#! /usr/bin/env python

"""
Demo of genetic programming with a typed language

This gp setup seeks to breed an organism which
implements if(x > 0, y, -y)

Takes an average of about X generations
to breed a matching program
"""

import math
from random import random, uniform
from pygene.prog import ProgOrganism, typed
from pygene.population import Population
import time

# @typed(Return value type, first input type, second input type)
@typed(float, float, float)
def add(x,y):
    try:
        return x+y
    except:
        #raise
        return x

@typed(float, float, float)
def sub(x,y):
    try:
        return x-y
    except:
        #raise
        return x

@typed(float, float, float)
def mul(x,y):
    try:
        return x*y
    except:
        #raise
        return x

@typed(float, bool, float, float)
def iif(x, y, z):
#    print "IIF:", x, y, z
    if x:
        return y
    else:
        return z

@typed(bool, float, float)
def greater(x,y):
    return x>y

@typed(bool, float, float)
def lesser(x,y):
    return x<y

# define the class comprising the program organism
class MyTypedProg(ProgOrganism):
    """
    """
    funcs = {
        '+': add,
        '-': sub,
        #'*': mul,
        'iif': iif,
        '>': greater,
        #'<': lesser,
        }
    vars = [('x', float), ('y', float)]
    consts = [0.0, 1.0, True]
    type = float

    testVals = [
        {
            'x': uniform(-10.0, 10.0),
            'y': uniform(-10.0, 10.0),
        } for i in xrange(20)
    ]


    mutProb = 0.4

    def testFunc(self, **vars):
        """
        Just wanting to model iif(x > 0, 2.0 * y, -y)
        """
        if vars['x'] > 0:
            return 2.0 * vars['y']
        else:
            return - vars['y']

    def fitness(self):
        # choose 10 random values
        badness = 0.0
        try:
            for vars in self.testVals:
                badness += (self.calc(**vars) - self.testFunc(**vars)) ** 2

            # Additionaly to correct solutions - promote short solutions.
            badness += self.calc_nodes() / 70.0
            return badness
        except OverflowError:
            return 1.0e+255 # infinitely bad

    # maximum tree depth when generating randomly
    initDepth = 5


class TypedProgPop(Population):
    u"""Population class for typed programming demo"""

    species = MyTypedProg
    initPopulation = 30

    # cull to this many children after each generation
    childCull = 30

    # number of children to create after each generation
    childCount = 20

    mutants = 0.3

def graph(orig, best):
    "Graph on -10, 10 ranges"
    print "ORIG                                  BEST:"
    for y in range(10, -11, -2):
        for x in range(-10, 11, 3):
            z = orig(x=float(x), y=float(y))
            print "%03.0f " % z,

        print "  ",
        for x in range(-10, 11, 3):
            z = best(x=float(x), y=float(y))
            print "%03.0f " % z,
        print

def main(nfittest=10, nkids=100):
    pop = TypedProgPop()
    origpop = pop
    ngens = 0
    i = 0
    while True:
        b = pop.best()
        print "Generation %s: %s best=%s average=%s)" % (
            ngens, str(b), b.fitness(), pop.fitness())
        b.dump(1)
        graph(b.testFunc, b.calc)
        if b.fitness() <= 0.4:
            print "Cracked!"
            break
        i += 1
        ngens += 1

        if ngens < 100:
            pop.gen()
        else:
            print "Failed after 100 generations, restarting"
            time.sleep(1)
            pop = TypedProgPop()
            ngens = 0

if __name__ == '__main__':
    main()
    pass

########NEW FILE########
__FILENAME__ = config
"""
Parse genome from config file.
Only int and float genes are supported currently.

Example config file:
[x1]
type = float
randMin = -100.0
randMax = 100.0
mutProb = 0.1
mutAmt = 0.1

[x2]
type = int
randMin = -50
randMax = 50
mutProb = 0.2
mutAmt = 1

One section per gene.
'type' is necessary - other fields depends on the selected type
"""

import ConfigParser
from ConfigParser import NoOptionError

from gene import ComplexGeneFactory
from gene import IntGeneFactory, IntGeneExchangeFactory
from gene import IntGeneAverageFactory, IntGeneRandRangeFactory
from gene import FloatGeneFactory, FloatGeneRandomFactory, FloatGeneMaxFactory
from gene import FloatGeneExchangeFactory, FloatGeneRandRangeFactory

class LoaderError(Exception):
    pass

# Casts to int and float (TODO: Add other)
def _intcast(section, key, value):
    "Parse string into int or None with correct exceptions"
    if not value: # '' and None are coerced to None
        return None

    try:
        return int(value)
    except ValueError:
        raise LoaderError("Invalid integer value '%s' in position %s / %s." % (
                          value, section, key))

def _floatcast(section, key, value):
    "Parse string into float or None with correct exceptions"
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        raise LoaderError("Invalid floating-point value '%s' in position %s / %s." % (
                          value, section, key))

class ConfigLoader(object):

    def __init__(self, filename, require_genes=[], config_contents=None):
        """
        Genome loader.
        Filename - path to configuration (alternatively you can pass the config
          contents via the config_contents and pass None as the filename).
        If require_genes are passed after the loading we ensure that
        they exist.
        """
        # Dictionary of supported types into casts and factories
        self.types = {
            'int': (_intcast, IntGeneFactory),
            'int_exchange': (_intcast, IntGeneExchangeFactory),
            'int_average': (_intcast, IntGeneAverageFactory),
            'int_randrange': (_intcast, IntGeneRandRangeFactory),

            'float': (_floatcast, FloatGeneFactory),
            'float_average': (_floatcast, FloatGeneFactory), # The same as float.
            'float_randrange': (_floatcast, FloatGeneRandRangeFactory),
            'float_exchange': (_floatcast, FloatGeneExchangeFactory),
            'float_random': (_floatcast, FloatGeneRandomFactory),
            'float_max': (_floatcast, FloatGeneMaxFactory),

            'complex': (_floatcast, ComplexGeneFactory),
            # 'char': (str, CharGeneFactory),
            # ... TODO: add other
        }

        self.genome = {}

        self.require_genes = require_genes

        self.config = ConfigParser.RawConfigParser()
        self.config.optionxform = str # Don't lower() names

        if filename is None and config_contents is not None:
            import io
            self.config.readfp(io.BytesIO(config_contents))
        else:
            self.config.read(filename)

        # Do we have a population definition also?
        self._pre_parse_population()


    def register_type(self, typename, cast, factory):
        """
        User can register his types using this method
        """
        self.types[typename] = (cast, factory)

    def _pre_parse_population(self):
        self.has_population = self.config.has_section('population')
        try:
            genes = self.config.get('population', 'genes')
            genes = [gene.strip()
                     for gene in genes.split()]
            self.genes = genes if genes else None
        except NoOptionError:
            self.genes = None

    def load_population(self, name, species):
        """
        Parse population options and return a population
        """
        import new
        from population import Population

        if not self.has_population:
            raise LoaderError("No population is defined in the config file")
        args = {
            'species': species
        }
        def parse(fun, name):
            if self.config.has_option('population', name):
                try:
                    val = fun('population', name)
                    args[name] = val
                except ValueError:
                    raise LoaderError("Invalid value for population option " + name)

        parse(self.config.getint, 'initPopulation')
        parse(self.config.getint, 'childCull')
        parse(self.config.getint, 'childCount')
        parse(self.config.getint, 'incest')
        parse(self.config.getint, 'numNewOrganisms')
        parse(self.config.getboolean, 'mutateAfterMating')
        parse(self.config.getfloat, 'mutants')

        return new.classobj(name, (Population,), args)


    def _parse_gene(self, section):
        """
        parse_gene is called by parse_genome to parse
        a single gene from a config.
        config - ConfigParser instance
        section - gene name / config section name
        """
        genename = section

        if not self.config.has_section(genename):
            raise LoaderError("Gene %s has no section in the config file" % genename)

        # FIXME: This check won't work because of configparser:
        if genename in self.genome:
            raise LoaderError("Gene %s was already defined" % section)

        try:
            clonegene = self.config.get(section, 'clone')
            if not self.config.has_section(clonegene):
                raise LoaderError("Gene %s is cloning a gene %s which is not yet defined" % (genename, clonegene))
            section = clonegene
            genename = clonegene
        except NoOptionError:
            pass

        try:
            typename = self.config.get(section, 'type')
        except NoOptionError:
            raise LoaderError(("Required field 'type' was not "
                              "found in section/gene '%s'") % section)

        try:
            cast, factory = self.types[typename]
        except KeyError:
            raise LoaderError("Unhandled type in config file: " + typename)

        args = {}
        for key, value in self.config.items(section):
            if key == "type":
                continue
            if key == "mutProb": # Always float
                converted = _floatcast(section, key, value)
            else:
                converted = cast(section, key, value)
            args[key] = converted

        if 'randMin' in args and 'randMax' in args:
            if args['randMin'] > args['randMax']:
                raise LoaderError('randMin higher than randMax in section/gene %s' % section)
            if ('value' in args and args['value'] is not None
                and (args['value'] > args['randMax']
                     or args['value'] < args['randMin'])):
                raise LoaderError('value not within randMin, randMax in section/gene %s' % section)

        gene = factory(typename + "_" + genename, **args)
        return gene

    def load_genome(self):
        """
        Load genome from config file
        """

        sections = self.genes if self.genes else self.config.sections()

        for section in sections:
            if section.lower() == 'population':
                continue
            elif self.config.has_option(section, 'alias'):
                alias = self.config.get(section, 'alias')
                if alias not in self.genome:
                    raise LoaderError(("Gene %s is an alias for non-existing gene %s. "
                                       "Order matters!") % (section, alias))
                self.genome[section] = self.genome[alias]
                continue
            else:
                gene = self._parse_gene(section)
                self.genome[section] = gene

        for gene in self.require_genes:
            if gene not in self.genome:
                raise LoaderError("Required gene '%s' was not found in the config" % gene)
        #for gene in self.genome.itervalues():
        #    print gene.__dict__
        return self.genome

########NEW FILE########
__FILENAME__ = gamete
"""
Implements gametes, which are the result of
splitting an organism's genome in two, and are
used in the organism's sexual reproduction

In our model, I don't use any concept of a chromosome.
In biology, during a cell's interphase, there are
no chromosomes as such - the genetic material
is scattered chaotically throughout the cell nucleus.

Chromosomes (from my limited knowledge of biologi)
are mostly just a device used in cell division.
Since division of cells in this model isn't
constrained by the physical structure of the cell,
we shouldn't need a construct of chromosomes.

Gametes support the python '+' operator for sexual
reproduction. Adding two gametes together produces
a whole new Organism.
"""

from xmlio import PGXmlMixin

class Gamete(PGXmlMixin):
    """
    Contains a set of genes.
    
    Two gametes can be added together to form a
    new organism
    """
    def __init__(self, orgclass, **genes):
        """
        Creates a new gamete from a set of genes
        """
        self.orgclass = orgclass
        self.genes = dict(genes)
    
    def __getitem__(self, name):
        """
        Fetch a single gene by name
        """
        return self.genes[name]
    
    def __add__(self, other):
        """
        Combines this gamete with another
        gamete to form an organism
        """
        return self.conceive(other)
    
    def conceive(self, other):
        """
        Returns a whole new Organism class
        from the combination of this gamete with another
        """
        if not isinstance(other, Gamete):
            raise Exception("Trying to mate a gamete with a non-gamete")
    
        return self.orgclass(self, other)
    



########NEW FILE########
__FILENAME__ = gene
"""
Implements a collection of gene classes

Genes support the following python operators:
    - + - calculates the phenotype resulting from the
      combination of a pair of genes

These genes work via classical Mendelian genetics
"""

import sys, new
from random import random, randint, uniform, choice
from math import sqrt

from xmlio import PGXmlMixin

class BaseGene(PGXmlMixin):
    """
    Base class from which all the gene classes are derived.

    You cannot use this class directly, because there are
    some methods that must be overridden.
    """
    # each gene should have an object in
    # which its genotype should be stored
    value = None

    # probability of a mutation occurring
    mutProb = 0.01

    # List of acceptable fields for the factory
    fields = ["value", "mutProb"]

    def __init__(self):

        # if value is not provided, it will be
        # randomly generated
        if self.__class__.value == None:
            self.value = self.randomValue()
        else:
            self.value = self.__class__.value


    def copy(self):
        """
        returns clone of this gene
        """
        cls = self.__class__()
        cls.value = self.value
        return cls


    def __add__(self, other):
        """
        Combines two genes in a gene pair, to produce an effect

        This is used to determine the gene's phenotype

        This default method computes the arithmetic mean
        of the two genes.

        Override as needed

        Must be overridden
        """
        raise Exception("Method __add__ must be overridden")

    def __repr__(self):
        return "<%s:%s>" % (self.__class__.__name__, self.value)

    # def __cmp__(this, other):
    #     return cmp(this.value, other.value)
    #
    def maybeMutate(self):
        if random() < self.mutProb:
            self.mutate()

    def mutate(self):
        """
        Perform a mutation on the gene

        You MUST override this in subclasses
        """
        raise Exception("method 'mutate' not implemented")

    def randomValue(self):
        """
        Generates a plausible random value
        for this gene.

        Must be overridden
        """
        raise Exception("Method 'randomValue' not implemented")

    def xmlDumpSelf(self, doc, parent):
        """
        dump out this gene into parent tag
        """
        genetag = doc.createElement("gene")
        parent.appendChild(genetag)

        self.xmlDumpClass(genetag)

        self.xmlDumpAttribs(genetag)

        # now dump out the value into a text tag
        ttag = doc.createTextNode(str(self.value))

        # and add it to self tag
        genetag.appendChild(ttag)

    def xmlDumpAttribs(self, tag):
        """
        sets attributes of tag
        """
        tag.setAttribute("mutProb", str(self.mutProb))


class ComplexGene(BaseGene):
    """
    A gene whose value is a complex point number
    """
    # amount by which to mutate, will change value
    # by up to +/- this amount
    mutAmtReal = 0.1
    mutAmtImag = 0.1

    # used for random gene creation
    # override in subclasses
    randMin = -1.0
    randMax = 1.0

    # Acceptable fields for factory
    fields = ["value", "mutProb", "mutAmtReal", "mutAmtImag",
              "randMin", "randMax"]

    def __add__(self, other):
        """
        Combines two genes in a gene pair, to produce an effect

        This is used to determine the gene's phenotype

        This class computes the arithmetic mean
        of the two genes' values, so is akin to incomplete
        dominance.

        Override if desired
        """
        return (self.value + other.value) / 2.0
        #return abs(complex(self.value.real, other.value.imag))


    def mutate(self):
        """
        Mutate this gene's value by a random amount
        within the range +/- self.mutAmt

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value += complex(
            uniform(-self.mutAmtReal, self.mutAmtReal),
            uniform(-self.mutAmtImag, self.mutAmtImag)
            )

        # if the gene has wandered outside the alphabet,
        # rein it back in
        real = self.value.real
        imag = self.value.imag

        if real < self.randMin:
            real = self.randMin
        elif real > self.randMax:
            real = self.randMax

        if imag < self.randMin:
            imag = self.randMin
        elif imag > self.randMax:
            imag = self.randMax

        self.value = complex(real, imag)

    def randomValue(self):
        """
        Generates a plausible random value
        for this gene.

        Override as needed
        """
        min = self.randMin
        range = self.randMax - min

        real = uniform(self.randMin, self.randMax)
        imag = uniform(self.randMin, self.randMax)

        return complex(real, imag)


class FloatGene(BaseGene):
    """
    A gene whose value is a floating point number

    Class variables to override:

        - mutAmt - default 0.1 - amount by which to mutate.
          The gene will will move this proportion towards
          its permissible extreme values

        - randMin - default -1.0 - minimum possible value
          for this gene. Mutation will never allow the gene's
          value to be less than this

        - randMax - default 1.0 - maximum possible value
          for this gene. Mutation will never allow the gene's
          value to be greater than this
    """
    # amount by which to mutate, will change value
    # by up to +/- this amount
    mutAmt = 0.1

    # used for random gene creation
    # override in subclasses
    randMin = -1.0
    randMax = 1.0

    # Acceptable fields for factory
    fields = ["value", "mutProb", "mutAmt", "randMin", "randMax"]

    def __add__(self, other):
        """
        Combines two genes in a gene pair, to produce an effect

        This is used to determine the gene's phenotype

        This class computes the arithmetic mean
        of the two genes' values, so is akin to incomplete
        dominance.

        Override if desired
        """
        return (self.value + other.value) / 2.0

    def mutate(self):
        """
        Mutate this gene's value by a random amount
        within the range, which is determined by
        multiplying self.mutAmt by the distance of the
        gene's current value from either endpoint of legal values

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        if random() < 0.5:
            # mutate downwards
            self.value -= uniform(0, self.mutAmt * (self.value-self.randMin))
        else:
            # mutate upwards:
            self.value += uniform(0, self.mutAmt * (self.randMax-self.value))


    def randomValue(self):
        """
        Generates a plausible random value
        for this gene.

        Override as needed
        """
        return uniform(self.randMin, self.randMax)



class FloatGeneRandom(FloatGene):
    """
    Variant of FloatGene where mutation always randomises the value
    """
    def mutate(self):
        """
        Randomise the gene

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value = self.randomValue()


class FloatGeneRandRange(FloatGene):
    def __add__(self, other):
        """
        A variation of float gene where during the mixing a random value
        from within range created by the two genes is selected.
        """
        start = min([self.value, other.value])
        end = max([self.value, other.value])
        return uniform(start, end)


class FloatGeneMax(FloatGene):
    """
    phenotype of this gene is the greater of the values
    in the gene pair
    """
    def __add__(self, other):
        """
        produces phenotype of gene pair, as the greater of this
        and the other gene's values
        """
        return max(self.value, other.value)

class FloatGeneExchange(FloatGene):
    """
    phenotype of this gene is the random of the values
    in the gene pair
    """
    def __add__(self, other):
        """
        produces phenotype of gene pair, as the random of this
        and the other gene's values
        """
        return choice([self.value, other.value])


class IntGene(BaseGene):
    """
    Implements a gene whose values are ints,
    constrained within the randMin,randMax range
    """
    # minimum possible value for gene
    # override in subclasses as needed
    randMin = -sys.maxint

    # maximum possible value for gene
    # override in subclasses as needed
    randMax = sys.maxint + 1

    # maximum amount by which gene can mutate
    mutAmt = 1

    # Acceptable fields for factory
    fields = ["value", "mutProb", "mutAmt", "randMin", "randMax"]

    def mutate(self):
        """
        perform gene mutation

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value += randint(-self.mutAmt, self.mutAmt)

        # if the gene has wandered outside the alphabet,
        # rein it back in
        if self.value < self.randMin:
            self.value = self.randMin
        elif self.value > self.randMax:
            self.value = self.randMax

    def randomValue(self):
        """
        return a legal random value for this gene
        which is in the range [self.randMin, self.randMax]
        """
        return randint(self.randMin, self.randMax)

    def __add__(self, other):
        """
        produces the phenotype resulting from combining
        this gene with another gene in the pair

        returns an int value, based on a formula of higher
        numbers dominating
        """
        return max(self.value, other.value)


class IntGeneRandom(IntGene):
    """
    Variant of IntGene where mutation always randomises the value
    """
    def mutate(self):
        """
        Randomise the gene

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value = self.randomValue()


class IntGeneExchange(IntGene):
    def __add__(self, other):
        """
        A variation of int gene where during the mixing a
        random gene is selected instead of max.
        """
        return choice([self.value, other.value])


class IntGeneAverage(IntGene):
    def __add__(self, other):
        """
        A variation of int gene where during the mixing a
        average of two genes is selected.
        """
        return (self.value + other.value) / 2


class IntGeneRandRange(IntGene):
    def __add__(self, other):
        """
        A variation of int gene where during the mixing a random value
        from within range created by the two genes is selected.
        """
        start = min([self.value, other.value])
        end = max([self.value, other.value])
        return randint(start, end)


class CharGene(BaseGene):
    """
    Gene that holds a single ASCII character,
    as a 1-byte string
    """
    # minimum possible value for gene
    # override in subclasses as needed
    randMin = '\x00'

    # maximum possible value for gene
    # override in subclasses as needed
    randMax = '\xff'

    def __repr__(self):
        """
        Returns safely printable value
        """
        return self.value

    def mutate(self):
        """
        perform gene mutation

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value = ord(self.value) + randint(-self.mutAmt, self.mutAmt)

        # if the gene has wandered outside the alphabet,
        # rein it back in
        if self.value < ord(self.randMin):
            self.value = self.randMin
        elif self.value > ord(self.randMax):
            self.value = self.randMax
        else:
            self.value = chr(self.value)

    def randomValue(self):
        """
        return a legal random value for this gene
        which is in the range [self.randMin, self.randMax]
        """
        return chr(randint(ord(self.randMin), ord(self.randMax)))

    def __add__(self, other):
        """
        produces the phenotype resulting from combining
        this gene with another gene in the pair

        returns an int value, based on a formula of higher
        numbers dominating
        """
        print "HERE", self.value, other.value
        return max(self.value, other.value)


class CharGeneExchange(CharGene):
    def __add__(self, other):
        """
        A variation of char gene where during the mixing a
        average of two genes is selected.
        """
        print "HERE", self.value, other.value
        return choice([self.value, other.value])


class AsciiCharGene(CharGene):
    """
    Specialisation of CharGene that can only
    hold chars in the legal ASCII range

    OBSOLETE/REMOVE: Exactly the same as chargene
    """
    # minimum possible value for gene
    # override in subclasses as needed
    randMin = chr(0)

    # maximum possible value for gene
    # override in subclasses as needed
    randMax = chr(255)

    def __repr__(self):
        """
        still need to str() the value, since the range
        includes control chars
        """
        return self.value

class PrintableCharGene(AsciiCharGene):
    """
    Specialisation of AsciiCharGene that can only
    hold printable chars
    """
    # minimum possible value for gene
    # override in subclasses as needed
    randMin = ' '

    # maximum possible value for gene
    # override in subclasses as needed
    randMax = chr(127)

    def __repr__(self):
        """
        don't need to str() the char, since
        it's already printable
        """
        return self.value

class DiscreteGene(BaseGene):
    """
    Gene type with a fixed set of possible values, typically
    strings

    Mutation behaviour is that the gene's value may
    spontaneously change into one of its alleles
    """
    # this is the set of possible values
    # override in subclasses
    alleles = []

    # the dominant allele - leave as None
    # if gene has incomplete dominance
    dominant = None

    # the co-dominant alleles - leave empty
    # if gene has simple dominance
    codominant = []

    # the recessive allele - leave as None if there's a dominant
    recessive = None

    def mutate(self):
        """
        Change the gene's value into any of the possible alleles,
        subject to mutation probability 'self.mutProb'

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value = self.randomValue()

    def randomValue(self):
        """
        returns a random allele
        """
        return choice(self.alleles)

    def __add__(self, other):
        """
        determines the phenotype, subject to dominance properties

        returns a tuple of effects
        """
        # got simple dominance?
        if self.dominant in (self.value, other.value):
            # yes
            return (self.dominant,)

        # got incomplete dominance?
        elif self.codominant:
            phenotype = []
            for val in self.value, other.value:
                if val in self.codominant and val not in phenotype:
                    phenotype.append(val)

            # apply recessive, if one exists and no codominant genes present
            if not phenotype:
                if self.recessive:
                    phenotype.append(self.recessive)

            # done
            return tuple(phenotype)

        # got recessive?
        elif self.recessive:
            return (self.recessive,)

        # nothing else
        return ()

class BitGene(BaseGene):
    """
    Implements a single-bit gene
    """
    def __add__(self, other):
        """
        Produces the 'phenotype' as xor of gene pair values
        """
        raise Exception("__add__ method not implemented")



    def mutate(self):
        """
        mutates this gene, toggling the bit
        probabilistically

        perform mutation IN-PLACE, ie don't return mutated copy
        """
        self.value ^= 1

    def randomValue(self):
        """
        Returns a legal random (boolean) value
        """
        return choice([0, 1])


class AndBitGene(BitGene):
    """
    Implements a single-bit gene, whose
    phenotype is the AND of each gene in the pair
    """
    def __add__(self, other):
        """
        Produces the 'phenotype' as xor of gene pair values
        """
        return self.value and other.value


class OrBitGene(BitGene):
    """
    Implements a single-bit gene, whose
    phenotype is the OR of each gene in the pair
    """
    def __add__(self, other):
        """
        Produces the 'phenotype' as xor of gene pair values
        """
        return self.value or other.value



class XorBitGene(BitGene):
    """
    Implements a single-bit gene, whose
    phenotype is the exclusive-or of each gene in the pair
    """
    def __add__(self, other):
        """
        Produces the 'phenotype' as xor of gene pair values
        """
        return self.value ^ other.value

##
# Gene factories
# Necessary for config loading.
##

def _new_factory(cls):
    "Creates gene factories"
    def factory(name, **kw):
        "Gene factory"
        for key in kw.iterkeys():
            if key not in cls.fields:
                raise Exception("Tried to create a gene with an invalid field: " + key)
        return new.classobj(name, (cls,), kw)
    return factory

ComplexGeneFactory  = _new_factory(ComplexGene)
DiscreteGeneFactory = _new_factory(DiscreteGene)

FloatGeneFactory         = _new_factory(FloatGene)
FloatGeneMaxFactory      = _new_factory(FloatGeneMax)
FloatGeneRandomFactory   = _new_factory(FloatGeneRandom)
FloatGeneRandRangeFactory = _new_factory(FloatGeneRandRange)
FloatGeneExchangeFactory = _new_factory(FloatGeneExchange)

IntGeneFactory          = _new_factory(IntGene)
IntGeneExchangeFactory  = _new_factory(IntGeneExchange)
IntGeneAverageFactory   = _new_factory(IntGeneAverage)
IntGeneRandRangeFactory = _new_factory(IntGeneRandRange)

CharGeneFactory          = _new_factory(CharGene)
AsciiCharGeneFactory     = _new_factory(AsciiCharGene)
PrintableCharGeneFactory = _new_factory(PrintableCharGene)


# utility functions

def rndPair(geneclass):
    """
    Returns a gene pair, comprising two random
    instances of the given gene class
    """
    return (geneclass(), geneclass())

########NEW FILE########
__FILENAME__ = organism
"""
Implements classes for entire organisms

Organisms produce Gametes (think sperm/egg) via
the .split() method.

Organisms can be mated by the '+' operator, which
produces a child organism.

Subclasses of Organism must override the following methods:
    - fitness - returns a float value representing the
      organism's fitness - a value from 0.0 to infinity, where
      lower is better

Refer to module pygene.prog for organism classes for genetic
programming.
"""

from random import random, randrange, randint, choice

from gene import BaseGene, rndPair
from gamete import Gamete

from xmlio import PGXmlMixin

class BaseOrganism(PGXmlMixin):
    """
    Base class for genetic algo and genetic programming
    organisms

    Best not use this directly, but rather use or subclass from
    one of:
        - Organism
        - MendelOrganism
        - ProgOrganism
    """
    def __add__(self, partner):
        """
        Allows '+' operator for sexual reproduction

        Returns a whole new organism object, whose
        gene pair for each gene name are taken as one
        gene randomly selected from each parent
        """
        return self.mate(partner)

    def mate(self, partner):
        """
        Mates this organism with another organism to
        produce an entirely new organism

        Override this in subclasses
        """
        raise Exception("method 'mate' not implemented")

    def fitness(self):
        """
        Return the fitness level of this organism, as a float.
        Usually instead of this method a caching method 'get_fitness'
        is used, which calls this method always only once on an
        organism.

        Should return a number from 0.0 to infinity, where
        0.0 means 'perfect'

        Organisms should evolve such that 'fitness' converges
        to zero.

        This method must be overridden
        """
        raise Exception("Method 'fitness' not implemented")

    def prepare_fitness(self):
        """
        Is called on all organisms before asking them for their
        fitness. This allows to calculate fitness using a parallel
        processing which is started by prepare_fitness, and finalized
        in 'fitness' method. By default this method does nothing.

        Organisms using this method should usually take care to call
        it themselves in case it wasn't called before hand.
        """
        pass

    def get_fitness(self):
        """
        Return fitness from the cache, and if needed - calculate it.
        """
        if self.fitness_cache is not None:
            return self.fitness_cache
        else:
            self.fitness_cache = self.fitness()
            return self.fitness_cache

    def duel(self, opponent):
        """
        Duels this organism against an opponent

        Returns -1 if this organism loses, 0 if it's
        a tie, or 1 if this organism wins
        """
        #print "BaseOrganism.duel: opponent=%s" % str(opponent)

        return cmp(self.get_fitness(), opponent.get_fitness())

    def __cmp__(self, other):
        """
        Convenience method which invokes duel

        Allows lists of organisms to be sorted
        """
        return self.duel(other)

    def __repr__(self):
        """
        Delivers a minimal string representation
        of this organism.

        Override if needed
        """
        return "<%s:%s>" % (self.__class__.__name__, self.get_fitness())

    def mutate(self):
        """
        Implement the mutation phase

        Must be overridden
        """
        raise Exception("method 'mutate' not implemented")

    def dump(self):
        """
        Produce a detailed human-readable report on
        this organism and its structure
        """
        raise Exception("method 'dump' not implemented")

    def xmlDumpSelf(self, doc, parent):
        """
        Dumps out this object's contents into an xml tree

        Arguments:
            - doc - an xml.dom.minidom.Document object
            - parent - an xml.dom.minidom.Element parent, being
              the node into which this node should be placed
        """
        raise Exception("method xmlDumpSelf not implemented")

    def xmlDumpAttribs(self, elem):
        """
        Dump out the custom attributes of this
        organism

        elem is an xml.dom.minidom.element object
        """

class Organism(BaseOrganism):
    """
    Simple genetic algorithms organism

    Contains only single genes, not pairs (ie, single-helix)

    Note - all organisms are hermaphrodites, which
    can reproduce by mating with another.
    In this implementation, there is no gender.

    Class variables (to override) are:
        - genome - a dict mapping gene names to gene classes

        - mutateOneOnly - default False - dictates whether mutation
          affects one randomly chosen gene unconditionally, or
          all genes subject to the genes' individual mutation settings

        - crossoverRate - default .5 - proportion of genes to
          split out to first child in each pair resulting from
          a mating

    Python operators supported:
        - + - mates two organism instances together, producing a child
        - [] - returns the value of the gene of a given name
        - <, <=, >, >= - compares fitness value to that of another instance
    """
    # dict which maps genotype names to gene classes
    genome = {}

    # dictates whether mutation affects one randomly chosen
    # gene unconditionally, or all genes subject to the genes'
    # own mutation settings

    mutateOneOnly = False

    # proportion of genes to split out to first
    # child
    crossoverRate = 0.5

    def __init__(self, **kw):
        """
        Initialises this organism randomly,
        or from a set of named gene keywords

        Arguments:
            - gamete1, gamete2 - a pair of gametes from which
              to take the genes comprising the new organism.
              May be omitted.

        Keywords:
            - keyword names are gene names within the organism's
              genome, and values are either:
                  - instances of a Gene subclass, or
                  - a Gene subclass (in which case the class will
                    be instantiated to form a random gene object)

        Any gene names in the genome, which aren't given in the
        constructor keywords, will be added as random instances
        of the respective gene class. (Recall that all Gene subclasses
        can be instantiated with no arguments to create a random
        valued gene).
        """
        # the set of genes which comprise this organism
        self.genes = {}

        # Cache fitness
        self.fitness_cache = None

        # remember the gene count
        self.numgenes = len(self.genome)

        # we're being fed a set of zero or more genes
        for name, cls in self.genome.items():

            # set genepair from given arg, or default to a
            # new random instance of the gene
            gene = kw.get(name, cls)

            # if we're handed a gene class instead of a gene object
            # we need to instantiate the gene class
            # to form the needed gene object
            if type(gene) == type and issubclass(gene, BaseGene):
                gene = gene()
            elif not isinstance(gene, BaseGene):
                # If it wasn't a subclass check if it's an instance
                raise Exception(
                    "object given as gene %s %s is not a gene" % (
                        name, repr(gene)))

            # all good - add in the gene to our genotype
            self.genes[name] = gene

    def copy(self):
        """
        returns a deep copy of this organism
        """
        genes = {}
        for name, gene in self.genes.items():
            genes[name] = gene.copy()
        return self.__class__(**genes)

    def mate(self, partner):
        """
        Mates this organism with another organism to
        produce two entirely new organisms via random choice
        of genes from this or the partner
        """
        genotype1 = {}
        genotype2 = {}

        # gene by gene, we assign our and partner's genes randomly
        for name, cls in self.genome.items():

            ourGene = self.genes.get(name, None)
            if not ourGene:
                ourGene = cls()

            partnerGene = partner.genes.get(name, None)
            if not partnerGene:
                partnerGene = cls()

            # randomly assign genes to first or second child
            if random() < self.crossoverRate:
                genotype1[name] = ourGene
                genotype2[name] = partnerGene
            else:
                genotype1[name] = partnerGene
                genotype2[name] = ourGene

        # got the genotypes, now create the child organisms
        child1 = self.__class__(**genotype1)
        child2 = self.__class__(**genotype2)

        # done
        return (child1, child2)

    def __getitem__(self, item):
        """
        allows shorthand for querying the phenotype
        of this organism
        """
        return self.genes[item].value

    def phenotype(self, geneName=None):
        """
        Returns the phenotype resulting from a
        given gene, OR the total phenotype resulting
        from all the genes

        tries to invoke a child class' method
        called 'phen_<name>'
        """
        # if no gene name specified, build up an entire
        # phenotype dict
        if geneName == None:
            phenotype = {}
            for name, cls in self.genome.items():
                val = self.phenotype(name)
                if not phenotype.has_key(name):
                    phenotype[name] = []
                phenotype[name].append(val)

            # got the whole phenotype now
            return phenotype

        # just getting the phenotype for one gene pair
        return self.genes[geneName]

    def mutate(self):
        """
        Implement the mutation phase, invoking
        the stochastic mutation method on each
        component gene

        Does not affect this organism, but returns a mutated
        copy of it
        """
        mutant = self.copy()

        if self.mutateOneOnly:
            # unconditionally mutate just one gene
            gene = choice(mutant.genes.values())
            gene.mutate()

        else:
            # conditionally mutate all genes
            for gene in mutant.genes.values():
                gene.maybeMutate()

        return mutant

    def dump(self):
        """
        Produce a detailed human-readable report on
        this organism, its genotype and phenotype
        """
        print "Organism %s:" % self.__class__.__name__

        print "  Fitness: %s" % self.get_fitness()
        for k,v in self.genes.items():
            print "  Gene: %s = %s" % (k, v)

    def xmlDumpSelf(self, doc, parent):
        """
        Dumps out this object's contents into an xml tree

        Arguments:
            - doc - an xml.dom.minidom.Document object
            - parent - an xml.dom.minidom.Element parent, being
              the node into which this node should be placed
        """
        orgtag = doc.createElement("organism")
        parent.appendChild(orgtag)

        self.xmlDumpClass(orgtag)

        self.xmlDumpAttribs(orgtag)

        # now dump out the constituent genes
        for name, cls in self.genome.items():

            # create a named genepair tag to contain genes
            pairtag = doc.createElement("genepair")
            orgtag.appendChild(pairtag)

            pairtag.setAttribute("name", name)

            # now write out genes
            gene = self.genes[name]
            #print "self.genes[%s] = %s" % (
            #    name,
            #    pair.__class__
            #    )
            gene.xmlDumpSelf(doc, pairtag)


class GenomeSplitOrganism(Organism):
    """
    Don't exchange genes at random - like Organism does,
    but split genome in random point and exchange halves.

    This organism can work better in situation where `connected'
    genes are located close to each other on the genome.
    """
    chromosome_intersections = 2
    
    def mate(self, partner):
        """
        Mates this organism with another organism to
        produce two entirely new organisms via random choice
        of genome intersection and splitting halves.

        Genes are sorted by keys, and the key name is what groups
        genes in this process.
        """
        genotype1 = {}
        genotype2 = {}

        # 0 1 2 3 4 5
        # G.G.G.G.G.G
        # g.g.g.g.g.g
        #  ^ - split on 0
        # g.g.g.g.g.g
        #           ^-  split in 5:
        # G.G.G.G.G.G

        # Generate two random intersections
        intersections = set(randrange(0, len(self.genome))
                            for i in range(self.chromosome_intersections))

        intersections = list(sorted(intersections))

        source_a = self.genes
        source_b = partner.genes
        # gene by gene, we assign our and partner's genes
        for i, name in enumerate(sorted(self.genome.keys())):
            if i in intersections:
                source_a, source_b = source_b, source_a

            gene_a = source_a.get(name, None)
            if not gene_a:
                gene_a = self.genome[name]()

            gene_b = source_b.get(name, None)
            if not gene_b:
                gene_b = self.genome[name]()

            # assign genes to first or second child
            genotype1[name] = gene_a
            genotype2[name] = gene_b

        # got the genotypes, now create the child organisms
        child1 = self.__class__(**genotype1)
        child2 = self.__class__(**genotype2)

        return (child1, child2)

class MendelOrganism(BaseOrganism):
    """
    Classical Mendelian genetic organism

    Contains a pair of genes for each gene in the genome

    Organisms contain a set of pairs of genes, where the
    genes of each pair must be of the same type.

    Class variables (to override) are:
        - genome - a dict mapping gene names to gene classes

        - mutateOneOnly - default False - if set, then the
          mutation phase will mutate exactly one of the genepairs
          in the genotype, randomly selected. If False, then
          apply mutation to all genes, subject to individual genes'
          mutation settings

    Python operators supported:
        - + - mates two organism instances together, producing a child
        - [] - returns the phenotype produced by the gene pair of a given name
        - <, <=, >, >= - compares fitness value to that of another instance
    """
    # dict which maps genotype names to gene classes
    genome = {}

    # dictates whether mutation affects one randomly chosen
    # gene unconditionally, or all genes subject to the genes'
    # own mutation settings

    mutateOneOnly = False

    def __init__(self, gamete1=None, gamete2=None, **kw):
        """
        Initialises this organism from either two gametes,
        or from a set of named gene keywords

        Arguments:
            - gamete1, gamete2 - a pair of gametes from which
              to take the genes comprising the new organism.
              May be omitted.

        Keywords:
            - keyword names are gene names within the organism's
              genome, and values are either:
                  - a tuple containing two instances of a Gene
                    subclass, or
                  - a Gene subclass (in which case the class will
                    be instantiated twice to form a random gene pair)

        Any gene names in the genome, which aren't given in the
        constructor keywords, will be added as random instances
        of the respective gene class. (Recall that all Gene subclasses
        can be instantiated with no arguments to create a random
        valued gene).
        """
        # the set of genes which comprise this organism
        self.genes = {}

        # Cache fitness
        self.fitness_cache = None

        # remember the gene count
        self.numgenes = len(self.genome)

        if gamete1 and gamete2:
            # create this organism from sexual reproduction
            for name, cls in self.genome.items():
                self.genes[name] = (
                    gamete1[name].copy(),
                    gamete2[name].copy(),
                    )

            # and apply mutation
            #self.mutate()

            # done, easy as that
            return

        # other case - we're being fed a set of zero or more genes
        for name, cls in self.genome.items():

            # set genepair from given arg, or default to a
            # new random instance of the gene
            genepair = kw.get(name, cls)

            # if we're handed a gene class instead of a tuple
            # of 2 genes, we need to instantiate the gene class
            # to form the needed tuple

            if type(genepair) == type and issubclass(genepair, BaseGene):
                genepair = rndPair(genepair)
            else:
                # we're given a tuple; validate the gene pair
                try:
                    gene1, gene2 = genepair
                except:
                    raise TypeError(
                        "constructor keyword values must be tuple of 2 Genes")

                if not isinstance(gene1, BaseGene):
                    raise Exception(
                        "object %s is not a gene" % repr(gene1))

                if not isinstance(gene2, BaseGene):
                    raise Exception(
                        "object %s is not a gene" % repr(gene2))

            # all good - add in the gene pair to our genotype
            self.genes[name] = genepair

    def copy(self):
        """
        returns a deep copy of this organism
        """
        genes = {}
        for name, genepair in self.genes.items():
            genes[name] = (genepair[0].copy(), genepair[1].copy())
        return self.__class__(**genes)

    def split(self):
        """
        Produces a Gamete object from random
        splitting of component gene pairs
        """
        genes1 = {}
        genes2 = {}

        for name, cls in self.genome.items():

            # fetch the pair of genes of that name
            genepair = self.genes[name]

            if randrange(0,2):
                genes1[name] = genepair[0]
                genes2[name] = genepair[1]
            else:
                genes1[name] = genepair[1]
                genes2[name] = genepair[0]

            # and pick one randomly
            #genes[name] = choice(genepair)

        gamete1 = Gamete(self.__class__, **genes1)
        gamete2 = Gamete(self.__class__, **genes2)

        return (gamete1, gamete2)

    def mate(self, partner):
        """
        Mates this organism with another organism to
        produce two entirely new organisms via mendelian crossover
        """
        #return self.split() + partner.split()
        ourGametes = self.split()
        partnerGametes = partner.split()
        child1 = self.__class__(ourGametes[0], partnerGametes[1])
        child2 = self.__class__(ourGametes[1], partnerGametes[0])
        return (child1, child2)

    def __getitem__(self, item):
        """
        allows shorthand for querying the phenotype
        of this organism
        """
        return self.phenotype(item)

    def phenotype(self, geneName=None):
        """
        Returns the phenotype resulting from a
        given gene, OR the total phenotype resulting
        from all the genes

        tries to invoke a child class' method
        called 'phen_<name>'
        """
        # if no gene name specified, build up an entire
        # phenotype dict
        if geneName == None:
            phenotype = {}
            for name, cls in self.genome.items():
                val = self.phenotype(name)
                if not phenotype.has_key(name):
                    phenotype[name] = []
                phenotype[name].append(val)

            # got the whole phenotype now
            return phenotype

        # just getting the phenotype for one gene pair

        if not isinstance(geneName, str):
            geneName = str(geneName)

        try:
            #return sum(self.genes[geneName])
            genes = self.genes[geneName]
            return genes[0] + genes[1]
        except:
            #print "self.genes[%s] = %s" % (geneName, self.genes[geneName])
            raise

        # FIXME: There's an error here for sure. The code is unreachable
        # Maybe it is supposed to be turned off.

        # get the genes in question
        gene1, gene2 = self.genes[geneName]

        # try to find a specialised phenotype
        # calculation method
        methname = 'phen_' + geneName
        meth = getattr(self, methname, None)

        if meth:
            # got the method - invoke it
            return meth(gene1, gene2)
        else:
            # no specialised methods, apply the genes'
            # combination methods
            return gene1 + gene2

    def mutate(self):
        """
        Implement the mutation phase, invoking
        the stochastic mutation method on each
        component gene

        Does not affect this organism, but returns a mutated
        copy of it
        """
        mutant = self.copy()

        if self.mutateOneOnly:
            # unconditionally mutate just one gene
            genepair = choice(mutant.genes.values())
            genepair[0].mutate()
            genepair[1].mutate()

        else:
            # conditionally mutate all genes
            for gene_a, gene_b in mutant.genes.values():
                gene_a.maybeMutate()
                gene_b.maybeMutate()

        return mutant

    def dump(self):
        """
        Produce a detailed human-readable report on
        this organism, its genotype and phenotype
        """
        print "Organism %s:" % self.__class__.__name__

        print "  Fitness: %s" % self.get_fitness()
        for k,v in self.genes.items():
            print "  Gene: %s" % k
            print "    Phenotype: %s" % self[k]
            print "    Genotype:"
            print "      %s" % v[0]
            print "      %s" % v[1]

    def xmlDumpSelf(self, doc, parent):
        """
        Dumps out this object's contents into an xml tree

        Arguments:
            - doc - an xml.dom.minidom.Document object
            - parent - an xml.dom.minidom.Element parent, being
              the node into which this node should be placed
        """
        orgtag = doc.createElement("organism")
        parent.appendChild(orgtag)

        self.xmlDumpClass(orgtag)

        self.xmlDumpAttribs(orgtag)

        # now dump out the constituent genes
        for name, cls in self.genome.items():

            # create a named genepair tag to contain genes
            pairtag = doc.createElement("genepair")
            orgtag.appendChild(pairtag)

            pairtag.setAttribute("name", name)

            # now write out genes
            pair = self.genes[name]
            #print "self.genes[%s] = %s" % (
            #    name,
            #    pair.__class__
            #    )
            for gene in pair:
                gene.xmlDumpSelf(doc, pairtag)

########NEW FILE########
__FILENAME__ = population
"""
pygene/population.py - Represents a population of organisms
"""

import random
from random import randrange, choice
from math import sqrt

from organism import Organism, BaseOrganism

from xmlio import PGXmlMixin

class Population(PGXmlMixin):
    """
    Represents a population of organisms

    You might want to subclass this

    Overridable class variables:

        - species - Organism class or subclass, being the 'species'
          of organism comprising this population

        - initPopulation - size of population to randomly create
          if no organisms are passed in to constructor

        - childCull - cull to this many children after each generation

        - childCount - number of children to create after each generation

        - incest - max number of best parents to mix amongst the
          kids for next generation, default 10

        - numNewOrganisms - number of random new orgs to add each
          generation, default 0

        - initPopulation - initial population size, default 10

        - mutants - default 0.1 - if mutateAfterMating is False,
          then this sets the percentage of mutated versions of
          children to add to the child population; children to mutate
          are selected based on fitness

    Supports the following python operators:

        - + - produces a new population instances, whose members are
          an aggregate of the members of the values being added

        - [] - int subscript - returns the ith fittest member

    """
    # cull to this many children after each generation
    childCull = 20

    # number of children to create after each generation
    childCount = 100

    # max number of best parents to mix amongst the kids for
    # next generation
    incest = 10

    # parameters governing addition of random new organisms
    numNewOrganisms = 0 # number of new orgs to add each generation

    # set to initial population size
    initPopulation = 10

    # set to species of organism
    species = Organism

    # mutate this proportion of organisms
    mutants = 0.1

    # set this to true to mutate all progeny
    mutateAfterMating = True

    def __init__(self, *items, **kw):
        """
        Create a population with zero or more members

        Arguments:
            - any number of arguments and/or sequences of args,
              where each arg is an instance of this population's
              species. If no arguments are given, organisms are
              randomly created and added automatically, according
              to self.initPopulation and self.species

        Keywords:
            - init - size of initial population to randomly create.
              Ignored if 1 or more constructor arguments are given.
              if not given, value comes from self.initPopulation
            - species - species of organism to create and add. If not
              given, value comes from self.species
        """
        self.organisms = []

        if kw.has_key('species'):
            species = self.species = kw['species']
        else:
            species = self.species

        if kw.has_key('init'):
            init = self.initPopulation = kw['init']
        else:
            init = self.initPopulation

        if not items:
            for i in xrange(init):
                self.add(species())

    def add(self, *args):
        """
        Add an organism, or a population of organisms,
        to this population

        You can also pass lists or tuples of organisms and/or
        populations, to any level of nesting
        """
        for arg in args:
            if isinstance(arg, tuple) or isinstance(arg, list):
                # got a list of things, add them one by one
                self.add(*arg)

            if isinstance(arg, BaseOrganism):
                # add single organism
                self.organisms.append(arg)

            elif isinstance(arg, Population):
                # absorb entire population
                self.organisms.extend(arg)
            else:
                raise TypeError(
                    "can only add Organism or Population objects")

        self.sorted = False

    def __add__(self, other):
        """
        Produce a whole new population consisting of an aggregate
        of this population and the other population's members
        """
        return Population(self, other)

    def getRandom(self, items=None):
        """
        randomly select one of the given items
        (or one of this population's members, if items
        not given).

        Favours fitter members
        """
        if items == None:
            items = self.organisms

        nitems = len(items)
        n2items = nitems * nitems

        # pick one parent randomly, favouring fittest
        idx = int(sqrt(randrange(n2items)))
        return items[nitems - idx - 1]

    def gen(self, nfittest=None, nchildren=None):
        """
        Executes a generation of the population.

        This consists of:
            - producing 'nchildren' children, parented by members
              randomly selected with preference for the fittest
            - culling the children to the fittest 'nfittest' members
            - killing off the parents, and replacing them with the
              children

        Read the source code to study the method of probabilistic
        selection.
        """
        if not nfittest:
            nfittest = self.childCull
        if not nchildren:
            nchildren = self.childCount

        children = []

        # add in some new random organisms, if required
        if self.numNewOrganisms:
            #print "adding %d new organisms" % self.numNewOrganisms
            for i in xrange(self.numNewOrganisms):
                self.add(self.species())


        # we use square root to skew the selection probability to
        # the fittest

        # get in order, if not already
        self.sort()
        nadults = len(self)

        n2adults = nadults * nadults

        # statistical survey
        #stats = {}
        #for j in xrange(nchildren):
        #    stats[j] = 0

        # wild orgy, have lots of children
        nchildren = 1 if nchildren == 1 else nchildren / 2
        for i in xrange(nchildren):
            # pick one parent randomly, favouring fittest
            idx1 = idx2 = int(sqrt(randrange(n2adults)))
            parent1 = self[-idx1]

            # pick another parent, distinct from the first parent
            while idx2 == idx1:
                idx2 = int(sqrt(randrange(n2adults)))
            parent2 = self[-idx2]

            #print "picking items %s, %s of %s" % (
            #    nadults - idx1 - 1,
            #    nadults - idx2 - 1,
            #    nadults)

            #stats[nadults - idx1 - 1] += 1
            #stats[nadults - idx2 - 1] += 1

            # get it on, and store the child
            child1, child2 = parent1 + parent2

            # mutate kids if required
            if self.mutateAfterMating:
                child1 = child1.mutate()
                child2 = child2.mutate()

            children.extend([child1, child2])

        # if incestuous, add in best adults
        if self.incest:
            children.extend(self[:self.incest])

        for child in children:
            child.prepare_fitness()

        children.sort()

        # and add in some mutants, a proportion of the children
        # with a bias toward the fittest
        if not self.mutateAfterMating:
            nchildren = len(children)
            n2children = nchildren * nchildren
            mutants = []
            numMutants = int(nchildren * self.mutants)

            # children[0] - fittest
            # children[-1] - worse fitness
            if 0:
                for i in xrange(numMutants):
                    # pick one parent randomly, favouring fittest
                    idx = int(sqrt(randrange(n2children)))

                    child = children[-idx]
                    mutant = child.mutate()
                    mutant.prepare_fitness()
                    mutants.append(mutant)
            else:
                for i in xrange(numMutants):
                    mutant = children[i].mutate()
                    mutant.prepare_fitness()
                    mutants.append(mutant)

            children.extend(mutants)
            children.sort()
        #print "added %s mutants" % numMutants
        # sort the children by fitness
        # take the best 'nfittest', make them the new population
        self.organisms[:] = children[:nfittest]

        self.sorted = True

        #return stats
    def __repr__(self):
        """
        crude human-readable dump of population's members
        """
        return str(self.organisms)

    def __getitem__(self, n):
        """
        Return the nth member of this population,
        which we guarantee to be sorted in order from
        fittest first
        """
        self.sort()
        return self.organisms[n]

    def __len__(self):
        """
        return the number of organisms in this population
        """
        return len(self.organisms)

    def fitness(self):
        """
        returns the average fitness value for the population
        """
        fitnesses = map(lambda org: org.get_fitness(), self.organisms)

        return sum(fitnesses)/len(fitnesses)

    def best(self):
        """
        returns the fittest member of the population
        """
        self.sort()
        return self[0]

    def sort(self):
        """
        Sorts this population in order of fitness, with
        the fittest first.

        We keep track of whether this population is in order
        of fitness, so we don't perform unnecessary and
        costly sorting
        """
        if not self.sorted:
            for organism in self.organisms:
                organism.prepare_fitness()
            self.organisms.sort()
            self.sorted = True

    # methods for loading/saving to/from xml

    def xmlDumpSelf(self, doc, parent):
        """
        Writes out the contents of this population
        into the xml tree
        """
        # create population element
        pop = doc.createElement("population")
        parent.appendChild(pop)

        # set population class details
        pop.setAttribute("class", self.__class__.__name__)
        pop.setAttribute("module", self.__class__.__module__)

        # set population params as xml tag attributes
        pop.setAttribute("childCull", str(self.childCull))
        pop.setAttribute("childCount", str(self.childCount))

        # dump out organisms
        for org in self.organisms:
            org.xmlDumpSelf(doc, pop)

########NEW FILE########
__FILENAME__ = prog
"""
Implements genetic programming organisms.
"""

from random import random, randrange, choice
from math import sqrt

from organism import BaseOrganism

from xmlio import PGXmlMixin


class TypeDoesNotExist(Exception):
    u"""Parameters does not allow to construct a tree."""
    pass

class BaseNode:
    """
    Base class for genetic programming nodes
    """
    def calc(self, **vars):
        """
        evaluates this node, plugging vars into
        the nodes
        """
        raise Exception("method 'calc' not implemented")

class FuncNode(BaseNode):
    """
    Node which holds a function and its argument nodes
    """
    def __init__(self, org, depth, name=None, children=None, type_=None):
        """
        creates this func node
        """
        self.org = org

        if org.type and type_:
            options = filter(lambda x: x[-1][0] == type_, org.funcsList)
        else:
            options = org.funcsList

        if not options:
            raise TypeDoesNotExist

        if name == None:
            # randomly choose a func
            name, func, nargs, typed = choice(options)
        else:
            # lookup func in organism
            func, nargs, typed = org.funcsDict[name]

        # and fill in the args, from given, or randomly
        if not children:
            if typed:
                children = [org.genNode(depth+1, typed[1+i]) for i in xrange(nargs)]
            else:
                children = [org.genNode(depth+1) for i in xrange(nargs)]

        self.type = org.type and typed[0] or None
        self.argtype = org.type and typed[1:] or []
        self.name = name
        self.func = func
        self.nargs = nargs
        self.children = children

        # Additional type check
        self.check_types()

    def calc_nodes(self):
        "Return number of nodes in equation"
        cnt = [0]
        def dfs(node):
            cnt[0] += 1
            if isinstance(node, FuncNode):
                for child in node.children:
                    dfs(child)

        dfs(self)
        return cnt[0]

    def calc(self, **vars):
        """
        evaluates this node, plugging vars into
        the nodes
        """
        args = []
        for child in self.children:
            #print "FuncNode.calc: child %s dump:" % (
            #    child.__class__,
            #    )
            #child.dump()
            arg = child.calc(**vars)
            #print "child returned %s" % repr(arg)
            args.append(arg)

        #print "FuncNode.calc: name=%s func=%s vars=%s args=%s" % (
        #    self.name,
        #    self.func,
        #    vars,
        #    args
        #    )
        if self.argtype:
            for i, pair in enumerate(zip(self.argtype, self.children)):
                argtype, child = pair
                if argtype != child.type:
                    msg = (
                        "\n"
                        "Genetical programming type error:\n"
                        "  Function '%s' called with arguments: %s\n"
                        "  Expected %s found %s (%s) for function argument %d\n"
                        "  Tree:"
                    )
                    print msg % (self.name, args, argtype, child.name, child.type, i + 1)
                    self.org.tree.dump(1)
                    print
                    raise TypeError

        t = self.func(*args)
        #print self.name, args, t

        if self.type and (type(t) != self.type):
            msg = (
                "\n"
                "Genetical programming type error:\n"
                "  Function '%s' returned %s (%r) instead of type %r\n"
            )
            print msg % (self.name, t, type(t), self.type)
            self.org.tree.dump(1)
            print
            raise TypeError

        return t

    def dump(self, level=0):
        indents = "  " * level
        #print indents + "func:" + self.name
        print "%s%s" % (indents, self.name)
        for child in self.children:
            child.dump(level+1)

    def check_types(self):
        u"Check if types of this function match its arguments"
        if not self.type:
            return

        for childtype, child in zip(self.argtype, self.children):
            if child.type != childtype:
                msg = (
                    "\n"
                    "Genetical programming type error:\n"
                    "  Function '%s' has children not matching it's types\n"
                    "  types: %r\n"
                    "  children: %r\n"
                    "  child types: %r\n"
                )
                print msg % (self.name,
                             self.argtype,
                             self.children,
                             [c.type for c in self.children])
                self.org.tree.dump(1)
                print
                raise TypeError

    def copy(self, doSplit=False):
        """
        Copies this node and recursively its children, returning
        the copy

        if doSplit is true, then
        cuts off a piece of the tree, to support
        the recombination phase of mating with another program

        returns a quadruple:
             - copy - a copy of this node
             - fragment - fragment to be given to mate
             - lst - list within copy tree to which fragment
               from mate should be written
             - idx - index within the lst at which the fragment
               should be written

        if doSplit is false, then the last 3 tuple items will be None
        """
        if not doSplit:
            # easy case - split has already occurred elsewhere
            # within the tree, so just clone the kids without
            # splitting
            clonedChildren = \
                [child.copy() for child in self.children]

            # now ready to instantiate clone
            copy = FuncNode(self.org, 0, self.name, clonedChildren, type_=self.type)
            return copy

        # choose a child of this node that we might split
        childIdx = randrange(0, self.nargs)
        childToSplit = self.children[childIdx]

        # if child is a terminal, we *must* split here.
        # if child is not terminal, randomly choose whether
        # to split here
        if (random() < 0.33
            or isinstance(childToSplit, TerminalNode)):

            # split at this node, and just copy the kids
            clonedChildren = [
                child.copy() for child in self.children
            ]

            # now ready to instantiate clone
            copy = FuncNode(self.org, 0, self.name, clonedChildren, type_=self.type)
            return copy, childToSplit, clonedChildren, childIdx
        else:
            # delegate the split down to selected child
            clonedChildren = []
            for i in xrange(self.nargs):
                child = self.children[i]
                if (i == childIdx):
                    # chosen child
                    (clonedChild, fragment, lst, idx) = child.copy(True)
                else:
                    # just clone without splitting
                    clonedChild = child.copy()
                clonedChildren.append(clonedChild)

            # now ready to instantiate clone
            copy = FuncNode(self.org, 0, self.name, clonedChildren, type_=self.type)
            return copy, fragment, lst, idx

    def mutate(self, depth):
        """
        randomly mutates either this tree, or a child
        """
        # 2 in 3 chance of mutating a child of this node
        if random() > 0.33:
            child = choice(self.children)
            if not isinstance(child, TerminalNode):
                child.mutate(depth+1)
                return

        # mutate this node - replace one of its children
        mutIdx = randrange(0, self.nargs)
        new_child = self.org.genNode(depth+1, type_=self.children[mutIdx].type)
        self.children[mutIdx] = new_child
        self.check_types()

        #print "mutate: depth=%s" % depth


class TerminalNode(BaseNode):
    """
    Holds a terminal value
    """

class ConstNode(TerminalNode):
    """
    Holds a constant value
    """
    def __init__(self, org, value=None, type_=None):
        """
        """
        self.org = org

        if value == None:
            if type_:
                options = filter(lambda x: type(x) == type_, org.consts)
            else:
                options = org.consts
            if options:
                value = choice(options)
            else:
                raise TypeDoesNotExist

        self.value = value
        self.type = type_ or type(value)
        self.name = str(value)


    def calc(self, **vars):
        """
        evaluates this node, returns value
        """
        # easy
        return self.value

    def dump(self, level=0):
        indents = "  " * level
        #print "%sconst: {%s}" % (indents, self.value)
        print "%s{%s}" % (indents, self.value)

    def copy(self):
        """
        clone this node
        """
        return ConstNode(self.org, self.value, type_=self.type)


class VarNode(TerminalNode):
    """
    Holds a variable
    """
    def __init__(self, org, name=None, type_=None):
        """
        Inits this node as a var placeholder
        """
        self.org = org

        if name == None:
            if org.type and type_:
                options = filter(lambda x: org.funcsVars[x] == type_, org.vars)
            else:
                options = org.vars

            if options:
                name = choice(options)
            else:
                raise TypeDoesNotExist

        self.name = name
        self.type = org.type and org.funcsVars[name] or None

    def calc(self, **vars):
        """
        Calculates val of this node
        """
        val = vars.get(self.name, 0.0)
        #print "VarNode.calc: name=%s val=%s vars=%s" % (
        #    self.name,
        #    val,
        #    vars,
        #    )
        return val

    def dump(self, level=0):

        indents = "  " * level
        #print indents + "var {" + self.name + "}"
        print "%s{%s}" % (indents, self.name)

    def copy(self):
        """
        clone this node
        """
        return VarNode(self.org, self.name, type_=self.type)

class ProgOrganismMetaclass(type):
    """
    A metaclass which analyses class attributes
    of a ProgOrganism subclass, and builds the
    list of functions and terminals
    """
    def __init__(cls, name, bases, data):
        """
        Create the ProgOrganism class object
        """
        # parent constructor
        object.__init__(cls, name, bases, data)

        # get the funcs, consts and vars class attribs
        funcs = data['funcs']
        consts = data['consts']
        vars = data['vars']

        # process the funcs
        funcsList = []
        funcsDict = {}
        funcsVars = {}
        for name, func in funcs.items():
            try:
                types = func._types
            except:
                types = None
            funcsList.append((name, func, func.func_code.co_argcount, types))
            funcsDict[name] = (func, func.func_code.co_argcount, types)
        if cls.type:
            funcsVars = dict(tuple(vars))
            vars = map(lambda x: x[0], vars)

        cls.vars = vars
        cls.funcsList = funcsList
        cls.funcsDict = funcsDict
        cls.funcsVars = funcsVars

class ProgOrganism(BaseOrganism):
    """
    Implements an organism for genetic programming

    Introspects to discover functions and terminals.

    You should add the folling class attribs:
        - funcs - a dictionary of funcs, names are func
          names, values are callable objects
        - vars - a list of variable names
        - consts - a list of constant values
    """
    __metaclass__ = ProgOrganismMetaclass

    funcs = {}
    vars = []
    consts = []
    type = None

    # maximum tree depth when generating randomly
    maxDepth = 4

    # probability of a mutation occurring
    mutProb = 0.01

    def __init__(self, root=None):
        """
        Creates this organism
        """

        # Cache fitness
        self.fitness_cache = None

        if root == None:
            root = self.genNode(type_=self.type)

        self.tree = root

    def mate(self, mate):
        """
        Perform recombination of subtree elements
        """

        # get copy of self, plus fragment and location details
        tries = 0
        while True:
            tries += 1

            if tries > 20:
                print "Warning: Failed to swap trees for", tries, "times. Continuing..."
                return self.copy(), mate.copy()

            # Get copied trees
            ourRootCopy, ourFrag, ourList, ourIdx = self.split()
            mateRootCopy, mateFrag, mateList, mateIdx = mate.split()

            # Can we swap them?
            if mateFrag.type != ourFrag.type:
                continue

            # Swap
            ourList[ourIdx] = mateFrag
            mateList[mateIdx] = ourFrag

            # Early sanity check
            mateRootCopy.check_types()
            ourRootCopy.check_types()
            break

        # and return both progeny
        child1 = self.__class__(ourRootCopy)
        child2 = self.__class__(mateRootCopy)

        return (child1, child2)

    def mutate(self):
        """
        Mutates this organism's node tree

        returns the mutant
        """
        mutant = self.copy()
        mutant.tree.mutate(1)
        return mutant

    def split(self):
        """
        support for recombination, returns a tuple
        with four values:
            - root - a copy of the tree, except for the fragment
              to be swapped
            - subtree - the subtree fragment to be swapped
            - lst - a list within the tree, containing the
              fragment
            - idx - index within the list where mate's fragment
              should be written
        """
        # otherwise, delegate the split down the tree
        copy, subtree, lst, idx = self.tree.copy(True)
        return (copy, subtree, lst, idx)

    def calc_nodes(self):
        u"Calculate nodes in equation"
        return self.tree.calc_nodes()
    
    def copy(self):
        """
        returns a deep copy of this organism
        """
        try:
            return self.__class__(self.tree.copy())
        except:
            print "self.__class__ = %s" % self.__class__
            raise

    def dump(self, node=None, level=1):
        """
        prints out this organism's node tree
        """
        self.tree.dump(1)

    def genNode(self, depth=1, type_=None):
        """
        Randomly generates a node to build in
        to this organism
        """
        cnt = 0
        while True:
            cnt += 1
            try:
                if depth > 1 and (depth >= self.initDepth or flipCoin()):
                    # not root, and either maxed depth, or 50-50 chance
                    if flipCoin():
                        # choose a var
                        v = VarNode(self, type_=type_)
                    else:
                        v = ConstNode(self, type_=type_)
                    return v
                else:
                    # either root, or not maxed, or 50-50 chance
                    f = FuncNode(self, depth, type_=type_)
                    return f
            except TypeDoesNotExist:
                if cnt > 50:
                    print "Warning, probably an infinite loop"
                    print "  your options does not allow for tree construction"
                continue


    def xmlDumpSelf(self, doc, parent):
        """
        Dumps out this object's contents into an xml tree

        Arguments:
            - doc - an xml.dom.minidom.Document object
            - parent - an xml.dom.minidom.Element parent, being
              the node into which this node should be placed
        """
        raise Exception("method xmlDumpSelf not implemented")

    def fitness(self):
        """
        Return the fitness level of this organism, as a float

        Should return a number from 0.0 to infinity, where
        0.0 means 'perfect'

        Organisms should evolve such that 'fitness' converges
        to zero.

        This method must be overridden

        In your override, you should generate a set of values,
        either deterministically or randomly, and pass each
        value to both .testFunc() and .calculate(), comparing
        the results and using this to calculate the fitness
        """
        raise Exception("Method 'fitness' not implemented")

    def testFunc(self, **kw):
        """
        this is the 'reference function' toward which
        organisms are trying to evolve

        You must override this in your organism subclass
        """
        raise Exception("method 'testFunc' not implemented")

    def calc(self, **vars):
        """
        Executes this program organism, using the given
        keyword parameters

        You shouldn't need to override this
        """
        #print "org.calc: vars=%s" % str(vars)

        return self.tree.calc(**vars)

def flipCoin():
    """
    randomly returns True/False
    """
    return choice((True, False))


def typed(*args):
    def typed_decorator(f):
        f._types = args
        return f
    return typed_decorator

########NEW FILE########
__FILENAME__ = xmlio
"""
xmlio.py

Mixin class to support pygene objects in 
loading/saving as xml
"""

import StringIO
from xml.dom.minidom import getDOMImplementation, parse, parseString

domimpl = getDOMImplementation()

class PGXmlMixin(object):
    """
    mixin class to support pygene classes
    serialising themselves to/from xml
    """
    def xmlDump(self, fileobj):
        """
        Dumps out the population to an open file in XML format.
    
        To dump to a string, use .xmlDumps() instead
        """
        doc = domimpl.createDocument(None, "pygene", None)
    
        top = doc.documentElement
        top.appendChild(doc.createComment(
            "generated by pygene - http://www.freenet.org.nz/python/pygene"))
    
        self.xmlDumpSelf(doc, top)
    
        fileobj.write(doc.toxml())
    
    
    
    
    def xmlDumps(self):
        """
        dumps out to xml, returning a string of the raw
        generated xml
        """
        s = StringIO.StringIO()
        self.xmlDump(s)
        return s.getvalue()
    
    def xmlDumpSelf(self, doc, parent):
        """
        Writes out the contents of this population
        into the xml tree
        """
        raise Exception("class %s: xmlDumpSelf not implemented" % \
            self.__class__.__name__)
    
    def xmlDumpClass(self, tag):
        """
        dumps out class information
        """
        tag.setAttribute("class", self.__class__.__name__)
        tag.setAttribute("module", self.__class__.__module__)
    
    def xmlDumpAttribs(self, tag):
        """
        """



########NEW FILE########
